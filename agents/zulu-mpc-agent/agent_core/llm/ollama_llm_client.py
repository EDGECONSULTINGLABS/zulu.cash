"""
Wrapper for OllamaClient to match LLMClient protocol.
"""

import ollama


class OllamaLLMClient:
    """
    Adapter to make Ollama compatible with LLMClient protocol.
    Uses ollama library directly for model flexibility.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120):
        self.client = ollama.Client(host=base_url)
        self.timeout = timeout
    
    def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> str:
        """
        Generate text using Ollama.
        
        Args:
            model: Model name (e.g., "qwen2.5:1.5b", "llama3.1:8b")
            prompt: Text prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        options = {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 40,
            "num_ctx": 8192,
        }
        
        response = self.client.generate(
            model=model,
            prompt=prompt,
            options=options,
        )
        
        return response.get("response", "")
