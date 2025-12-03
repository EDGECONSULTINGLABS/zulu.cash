"""Ollama client for local LLM operations."""

import json
from typing import Any, Dict, List, Optional

import ollama

from agent_core.utils import LoggerMixin


class OllamaClient(LoggerMixin):
    """
    Client for Ollama local LLM server.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        temperature: float = 0.1,
        num_ctx: int = 8192,
        timeout: int = 120,
    ):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama server URL.
            model: Model name.
            temperature: Sampling temperature.
            num_ctx: Context window size.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.timeout = timeout
        
        # Initialize client
        self.client = ollama.Client(host=base_url)
        
        self.logger.info(
            f"Ollama client initialized: {model} at {base_url}"
        )
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        format: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """
        Generate completion.
        
        Args:
            prompt: User prompt.
            system: System prompt.
            temperature: Override temperature.
            format: Response format (json, etc.).
            stream: Enable streaming.
            
        Returns:
            Generated text.
        """
        options = {
            "temperature": temperature or self.temperature,
            "num_ctx": self.num_ctx,
        }
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                system=system,
                options=options,
                format=format,
                stream=stream,
            )
            
            if stream:
                # Return generator for streaming
                return response
            else:
                return response['response']
                
        except Exception as e:
            self.logger.error(f"Ollama generation failed: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        format: Optional[str] = None,
    ) -> str:
        """
        Chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Override temperature.
            format: Response format.
            
        Returns:
            Assistant response.
        """
        options = {
            "temperature": temperature or self.temperature,
            "num_ctx": self.num_ctx,
        }
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options=options,
                format=format,
            )
            
            return response['message']['content']
            
        except Exception as e:
            self.logger.error(f"Ollama chat failed: {e}")
            raise
    
    def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> dict:
        """
        Generate JSON response with robust parsing.
        
        Args:
            prompt: User prompt.
            system: System prompt.
            temperature: Override temperature.
            
        Returns:
            Parsed JSON response.
        """
        response = self.generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
            format="json",
        )
        
        # Try multiple parsing strategies
        return self._parse_json_response(response)
    
    def _parse_json_response(self, response: str) -> dict:
        """
        Robust JSON parsing with multiple fallback strategies.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON dict
        """
        import re
        
        # Strategy 1: Direct parse (clean JSON)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Strip whitespace and try again
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Extract JSON from markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Extract JSON object from text (find first { to last })
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Strategy 5: Try to find JSON array
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # All strategies failed
        self.logger.error(f"Failed to parse JSON response with all strategies")
        self.logger.error(f"Raw response (first 500 chars): {response[:500]}")
        # Raise a more informative error
        raise ValueError(
            f"Could not extract valid JSON from Ollama response. "
            f"Response preview: {response[:200]}..."
        )
    
    def check_model(self) -> bool:
        """
        Check if model is available.
        
        Returns:
            True if model exists.
        """
        try:
            response = self.client.list()
            model_names = [m.model for m in response.models]
            return self.model in model_names
        except Exception as e:
            self.logger.error(f"Failed to check model: {e}")
            return False
    
    def pull_model(self) -> None:
        """Pull model if not available."""
        self.logger.info(f"Pulling model: {self.model}")
        try:
            self.client.pull(self.model)
            self.logger.info(f"Model {self.model} pulled successfully")
        except Exception as e:
            self.logger.error(f"Failed to pull model: {e}")
            raise
    
    def get_model_info(self) -> dict:
        """Get model information."""
        try:
            info = self.client.show(self.model)
            return info
        except Exception as e:
            self.logger.error(f"Failed to get model info: {e}")
            return {}
