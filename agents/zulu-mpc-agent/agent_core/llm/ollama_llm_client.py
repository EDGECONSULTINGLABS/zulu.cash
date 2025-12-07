"""
Wrapper for OllamaClient to match LLMClient protocol.
"""

from agent_core.llm.ollama_client import OllamaClient as BaseOllamaClient


class OllamaLLMClient:
    """
    Adapter to make OllamaClient compatible with LLMClient protocol.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120):
        self.client = BaseOllamaClient(base_url=base_url, timeout=timeout)
    
    def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> str:
        """
        Generate text using Ollama.
        
        Maps to OllamaClient.generate() method.
        """
        response = self.client.generate(
            model=model,
            prompt=prompt,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 40,
            }
        )
        
        return response.get("response", "")
