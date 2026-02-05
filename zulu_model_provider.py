"""
zulu_model_provider.py
======================
Model provider abstraction layer for Zulu.

Thin interface for LLM calls with provider-specific implementations.
Anthropic is the primary/default. Others are optional for open-source users.

DESIGN PRINCIPLES:
- Interface is minimal: complete() and complete_json()
- Implementations handle provider quirks internally
- Structured output is an optimization, not a requirement
- Graceful degradation if optional SDKs not installed

CONFIGURATION:
    # Provider selection
    ZULU_LLM_PROVIDER=anthropic    # or: ollama, openai, groq, gemini
    
    # API keys (provider-specific)
    ANTHROPIC_API_KEY=sk-ant-...
    OPENAI_API_KEY=sk-...
    GOOGLE_API_KEY=AIza...
    GROQ_API_KEY=gsk_...
    
    # Optional base URL (for self-hosted)
    ZULU_LLM_BASE_URL=
    
    # Per-role model selection
    ZULU_INTENT_MODEL=claude-haiku-4-5-20251001
    ZULU_PLANNING_MODEL=claude-sonnet-4-5-20250929
    ZULU_EXTRACTION_MODEL=claude-haiku-4-5-20251001

USAGE:
    from zulu_model_provider import get_provider, ModelConfig
    
    config = ModelConfig.from_env()
    provider = get_provider()
    
    # Simple completion
    response = await provider.complete(
        messages=[{"role": "user", "content": "Hello"}],
        model=config.intent_model,
    )
    
    # Structured JSON output
    data = await provider.complete_json(
        messages=[{"role": "user", "content": "Classify this intent"}],
        model=config.intent_model,
        schema={"type": "object", "properties": {...}},
    )
"""

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any

import aiohttp

log = logging.getLogger("zulu.provider")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class ModelConfig:
    """Per-role model configuration."""
    
    intent_model: str = "claude-haiku-4-5-20251001"
    planning_model: str = "claude-sonnet-4-5-20250929"
    extraction_model: str = "claude-haiku-4-5-20251001"
    
    @classmethod
    def from_env(cls) -> "ModelConfig":
        """Load config from environment variables."""
        return cls(
            intent_model=os.getenv("ZULU_INTENT_MODEL", cls.intent_model),
            planning_model=os.getenv("ZULU_PLANNING_MODEL", cls.planning_model),
            extraction_model=os.getenv("ZULU_EXTRACTION_MODEL", cls.extraction_model),
        )


# Known providers and their API key env vars
KNOWN_PROVIDERS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "ollama": None,  # No key needed
}


@dataclass
class ProviderConfig:
    """Provider connection configuration."""
    
    provider: str = "anthropic"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "ProviderConfig":
        """Load config from environment variables."""
        provider = os.getenv("ZULU_LLM_PROVIDER", "anthropic")
        
        # Validate provider is known
        if provider not in KNOWN_PROVIDERS:
            available = ", ".join(KNOWN_PROVIDERS.keys())
            raise ValueError(
                f"Unknown provider '{provider}' in ZULU_LLM_PROVIDER. "
                f"Available: {available}"
            )
        
        api_key_env = KNOWN_PROVIDERS.get(provider)
        api_key = os.getenv(api_key_env) if api_key_env else None
        
        return cls(
            provider=provider,
            api_key=api_key,
            base_url=os.getenv("ZULU_LLM_BASE_URL"),
        )


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------
class ModelProvider(ABC):
    """
    Abstract interface for LLM providers.
    
    Implementations handle provider-specific quirks internally.
    The interface stays clean.
    
    NOTE: Session management uses a simple None check without locking.
    This is safe for sequential use but would need asyncio.Lock if
    the same provider instance is used concurrently. The planner
    currently uses providers sequentially, so this is acceptable.
    """
    
    def _extract_json(self, text: str) -> dict:
        """
        Extract JSON from text response.
        
        Shared helper for providers that don't have native JSON mode
        or need fallback parsing.
        """
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in response
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON array
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                result = json.loads(match.group())
                return {"items": result} if isinstance(result, list) else result
            except json.JSONDecodeError:
                pass
        
        log.warning(f"Failed to extract JSON from response: {text[:200]}")
        return {}
    
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """
        Send messages, get text response.
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            model: Model identifier (provider-specific)
            system: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
            
        Returns:
            Response text
        """
        pass
    
    @abstractmethod
    async def complete_json(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        schema: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict:
        """
        Send messages, get parsed JSON response.
        
        Providers that support native JSON mode use it.
        Others fall back to text completion + parsing.
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            model: Model identifier
            system: Optional system prompt (should instruct JSON output)
            schema: Optional JSON schema for structured output
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            
        Returns:
            Parsed JSON as dict
        """
        pass
    
    async def close(self):
        """Clean up resources. Override if needed."""
        pass


# ---------------------------------------------------------------------------
# Anthropic Provider (Primary)
# ---------------------------------------------------------------------------
class AnthropicProvider(ModelProvider):
    """
    Anthropic Claude provider.
    
    Uses native tool use for structured JSON output when schema provided.
    Falls back to text + parse otherwise.
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("Anthropic API key required")
        
        self.api_key = api_key
        self.base_url = base_url or "https://api.anthropic.com"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
            )
        return self._session
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        session = await self._get_session()
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if system:
            payload["system"] = system
        
        async with session.post(
            f"{self.base_url}/v1/messages",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"Anthropic API error {resp.status}: {error_text}")
            
            data = await resp.json()
            
            # Extract text from content blocks
            content = data.get("content", [])
            text_parts = [
                block.get("text", "")
                for block in content
                if block.get("type") == "text"
            ]
            return "".join(text_parts)
    
    async def complete_json(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        schema: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict:
        # If schema provided, use tool use for structured output
        if schema:
            return await self._complete_with_tool(
                messages, model, system, schema, temperature, max_tokens
            )
        
        # Otherwise, complete and parse
        text = await self.complete(messages, model, system, temperature, max_tokens)
        return self._extract_json(text)
    
    async def _complete_with_tool(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str],
        schema: dict,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """Use Anthropic tool use for structured output."""
        session = await self._get_session()
        
        # Define a tool that matches the schema
        tool = {
            "name": "structured_output",
            "description": "Return structured data matching the schema",
            "input_schema": schema,
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": "structured_output"},
        }
        
        if system:
            payload["system"] = system
        
        async with session.post(
            f"{self.base_url}/v1/messages",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"Anthropic API error {resp.status}: {error_text}")
            
            data = await resp.json()
            
            # Extract tool use result
            content = data.get("content", [])
            for block in content:
                if block.get("type") == "tool_use" and block.get("name") == "structured_output":
                    return block.get("input", {})
            
            # Fallback: try to parse any text content
            for block in content:
                if block.get("type") == "text":
                    return self._extract_json(block.get("text", ""))
            
            return {}
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ---------------------------------------------------------------------------
# Ollama Provider (Open Source Default)
# ---------------------------------------------------------------------------
class OllamaProvider(ModelProvider):
    """
    Ollama provider for local LLM inference.
    
    No API key required. Uses text + parse for JSON output.
    """
    
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        session = await self._get_session()
        
        # Build messages with system prompt
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        
        payload = {
            "model": model,
            "messages": all_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        async with session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"Ollama error {resp.status}: {error_text}")
            
            data = await resp.json()
            return data.get("message", {}).get("content", "")
    
    async def complete_json(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        schema: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict:
        # Ollama doesn't have native JSON mode, so we instruct via prompt
        json_system = system or ""
        if json_system:
            json_system += "\n\n"
        json_system += "Respond ONLY with valid JSON. No other text."
        
        text = await self.complete(messages, model, json_system, temperature, max_tokens)
        return self._extract_json(text)
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ---------------------------------------------------------------------------
# OpenAI Provider (Optional)
# ---------------------------------------------------------------------------
class OpenAIProvider(ModelProvider):
    """
    OpenAI provider.
    
    Uses JSON mode when available (gpt-4-turbo, gpt-4o, etc.).
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("OpenAI API key required")
        
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._session
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        session = await self._get_session()
        
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        
        payload = {
            "model": model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"OpenAI API error {resp.status}: {error_text}")
            
            data = await resp.json()
            return data["choices"][0]["message"]["content"]
    
    async def complete_json(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        schema: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict:
        session = await self._get_session()
        
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        
        payload = {
            "model": model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"OpenAI API error {resp.status}: {error_text}")
            
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback to regex extraction
                return self._extract_json(content)
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ---------------------------------------------------------------------------
# Groq Provider (Optional)
# ---------------------------------------------------------------------------
class GroqProvider(ModelProvider):
    """
    Groq provider (OpenAI-compatible API).
    
    Fast inference for supported models.
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("Groq API key required")
        
        self.api_key = api_key
        self.base_url = base_url or "https://api.groq.com/openai/v1"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._session
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        session = await self._get_session()
        
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        
        payload = {
            "model": model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"Groq API error {resp.status}: {error_text}")
            
            data = await resp.json()
            return data["choices"][0]["message"]["content"]
    
    async def complete_json(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        schema: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict:
        session = await self._get_session()
        
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        
        payload = {
            "model": model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"Groq API error {resp.status}: {error_text}")
            
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback to regex extraction
                return self._extract_json(content)
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ---------------------------------------------------------------------------
# Gemini Provider (Optional)
# ---------------------------------------------------------------------------
class GeminiProvider(ModelProvider):
    """
    Google Gemini provider.
    
    Uses native JSON mode via response_mime_type.
    API key passed via header (x-goog-api-key) not URL query string.
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("Google API key required")
        
        self.api_key = api_key
        self.base_url = base_url or "https://generativelanguage.googleapis.com/v1beta"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"x-goog-api-key": self.api_key}
            )
        return self._session
    
    def _convert_messages(self, messages: list[dict], system: Optional[str]) -> tuple[list[dict], Optional[str]]:
        """Convert to Gemini format."""
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}],
            })
        return contents, system
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        session = await self._get_session()
        contents, system_instruction = self._convert_messages(messages, system)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        url = f"{self.base_url}/models/{model}:generateContent"
        
        async with session.post(
            url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"Gemini API error {resp.status}: {error_text}")
            
            data = await resp.json()
            
            # Extract text from response
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            
            return ""
    
    async def complete_json(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        schema: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict:
        session = await self._get_session()
        contents, system_instruction = self._convert_messages(messages, system)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        if schema:
            payload["generationConfig"]["responseSchema"] = schema
        
        url = f"{self.base_url}/models/{model}:generateContent"
        
        async with session.post(
            url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if not resp.ok:
                error_text = await resp.text()
                raise Exception(f"Gemini API error {resp.status}: {error_text}")
            
            data = await resp.json()
            
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        # Fallback to regex extraction
                        return self._extract_json(text)
            
            return {}
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------
PROVIDER_REGISTRY: dict[str, type[ModelProvider]] = {
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "gemini": GeminiProvider,
}


def get_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ModelProvider:
    """
    Get a model provider instance.
    
    Args:
        provider_name: Provider name (default: from ZULU_LLM_PROVIDER env)
        api_key: API key (default: from provider-specific env var)
        base_url: Base URL override (default: from ZULU_LLM_BASE_URL env)
    
    Returns:
        Configured ModelProvider instance
    """
    config = ProviderConfig.from_env()
    
    name = provider_name or config.provider
    key = api_key or config.api_key
    url = base_url or config.base_url
    
    provider_cls = PROVIDER_REGISTRY.get(name)
    if not provider_cls:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")
    
    # Ollama doesn't need an API key
    if name == "ollama":
        return provider_cls(base_url=url)
    
    if not key:
        raise ValueError(f"API key required for provider '{name}'")
    
    return provider_cls(api_key=key, base_url=url)


def register_provider(name: str, provider_cls: type[ModelProvider]):
    """Register a custom provider."""
    PROVIDER_REGISTRY[name] = provider_cls


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------
async def quick_complete(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    provider: Optional[ModelProvider] = None,
) -> str:
    """Quick one-shot completion."""
    p = provider or get_provider()
    config = ModelConfig.from_env()
    m = model or config.intent_model
    
    try:
        return await p.complete(
            messages=[{"role": "user", "content": prompt}],
            model=m,
            system=system,
        )
    finally:
        if not provider:
            await p.close()


async def quick_json(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    schema: Optional[dict] = None,
    provider: Optional[ModelProvider] = None,
) -> dict:
    """Quick one-shot JSON completion."""
    p = provider or get_provider()
    config = ModelConfig.from_env()
    m = model or config.intent_model
    
    try:
        return await p.complete_json(
            messages=[{"role": "user", "content": prompt}],
            model=m,
            system=system,
            schema=schema,
        )
    finally:
        if not provider:
            await p.close()
