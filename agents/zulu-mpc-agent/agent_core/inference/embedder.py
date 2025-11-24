"""Local embedding model for feature extraction."""

from typing import List, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from agent_core.utils import LoggerMixin


class EmbeddingModel(LoggerMixin):
    """
    Local embedding model for generating feature vectors.
    Uses sentence-transformers for high-quality embeddings.
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "auto",
        batch_size: int = 32,
        max_seq_length: int = 512,
    ):
        """
        Initialize embedding model.
        
        Args:
            model_name: HuggingFace model name or local path.
            device: Device to use (auto, cuda, cpu).
            batch_size: Batch size for encoding.
            max_seq_length: Maximum sequence length.
        """
        # Auto-detect device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.device = device
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        
        self.logger.info(f"Loading embedding model: {model_name} on {device}")
        
        # Load model
        self.model = SentenceTransformer(model_name, device=device)
        self.model.max_seq_length = max_seq_length
        
        self.logger.info(
            f"Embedding model loaded: dim={self.get_dimension()}, "
            f"max_seq={max_seq_length}"
        )
    
    def embed(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text or list of texts.
            normalize: Normalize embeddings to unit length.
            show_progress: Show progress bar.
            
        Returns:
            Numpy array of embeddings.
        """
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        
        return embeddings
    
    def embed_summary(
        self,
        summary: str,
        normalize: bool = True,
    ) -> List[float]:
        """
        Generate embedding for a call summary.
        
        Args:
            summary: Text summary.
            normalize: Normalize to unit length.
            
        Returns:
            Embedding vector as list.
        """
        embedding = self.embed(summary, normalize=normalize)
        return embedding[0].tolist()
    
    def embed_utterances(
        self,
        utterances: List[dict],
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Generate embeddings for multiple utterances.
        
        Args:
            utterances: List of utterance dicts with 'text' field.
            normalize: Normalize embeddings.
            
        Returns:
            Numpy array of embeddings.
        """
        texts = [u['text'] for u in utterances]
        return self.embed(texts, normalize=normalize)
    
    def similarity(
        self,
        emb1: Union[np.ndarray, List[float]],
        emb2: Union[np.ndarray, List[float]],
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            emb1: First embedding.
            emb2: Second embedding.
            
        Returns:
            Cosine similarity score.
        """
        if isinstance(emb1, list):
            emb1 = np.array(emb1)
        if isinstance(emb2, list):
            emb2 = np.array(emb2)
        
        # Cosine similarity
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()
    
    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "model_name": self.model._model_config.get('model_name', 'unknown'),
            "dimension": self.get_dimension(),
            "max_seq_length": self.max_seq_length,
            "device": str(self.device),
        }


# Convenience function for quick embeddings
def embed_summary(
    summary: str,
    model: EmbeddingModel = None,
) -> List[float]:
    """
    Quick function to embed a summary.
    
    Args:
        summary: Text summary.
        model: Optional pre-loaded model.
        
    Returns:
        Embedding vector.
    """
    if model is None:
        model = EmbeddingModel()
    
    return model.embed_summary(summary)
