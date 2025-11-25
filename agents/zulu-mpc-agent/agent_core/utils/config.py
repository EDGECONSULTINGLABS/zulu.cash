"""Configuration management for ZULU MPC Agent."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class WhisperConfig(BaseModel):
    """Whisper model configuration."""
    model_size: str = "medium"
    device: str = "auto"
    compute_type: str = "auto"
    model_dir: str = "./data/models/whisper"


class DiarizationConfig(BaseModel):
    """Diarization configuration."""
    backend: str = "simple"  # pyannote, whisperx, simple
    min_speakers: int = 1
    max_speakers: int = 10
    hf_token: Optional[str] = None


class DatabaseConfig(BaseModel):
    """Database configuration."""
    path: str = "./data/zulu_agent.db"
    encryption_key_env: str = "ZULU_DB_KEY"
    backup_enabled: bool = True
    backup_dir: str = "./data/backups"
    backup_interval_hours: int = 24


class OllamaConfig(BaseModel):
    """Ollama LLM configuration."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    temperature: float = 0.1
    num_ctx: int = 8192
    timeout: int = 120


class EmbeddingsConfig(BaseModel):
    """Embeddings model configuration."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "auto"
    batch_size: int = 32
    max_seq_length: int = 512


class NillionConfig(BaseModel):
    """Nillion MPC configuration."""
    enabled: bool = False
    network_url: str = "https://nillion-testnet.example.com"
    api_key_env: str = "NILLION_API_KEY"
    cluster_id: Optional[str] = None
    programs: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 60


class AudioConfig(BaseModel):
    """Audio processing configuration."""
    sample_rate: int = 16000
    format: str = "wav"
    temp_dir: str = "./data/temp"
    cleanup_after_processing: bool = True


class PrivacyConfig(BaseModel):
    """Privacy and security configuration."""
    store_audio_files: bool = False
    anonymize_speakers: bool = True
    pii_detection_enabled: bool = True
    log_level: str = "INFO"


class FeaturesConfig(BaseModel):
    """Feature extraction configuration."""
    extract_embeddings: bool = True
    extract_attention_scores: bool = True
    extract_sentiment: bool = False
    extract_topics: bool = True


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: str = "./logs/zulu_agent.log"
    max_size_mb: int = 100
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Config(BaseModel):
    """Main configuration."""
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    diarization: DiarizationConfig = Field(default_factory=DiarizationConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    nillion: NillionConfig = Field(default_factory=NillionConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to config YAML file. If None, uses default.
        
    Returns:
        Loaded configuration object.
    """
    # Load environment variables
    load_dotenv()
    
    # Determine config file path
    if config_path is None:
        config_path = os.getenv("ZULU_CONFIG", "./config/default.yaml")
    
    config_file = Path(config_path)
    
    # Load YAML config
    if config_file.exists():
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f) or {}
    else:
        config_data = {}
    
    # Override with environment variables
    _apply_env_overrides(config_data)
    
    # Create and validate config
    return Config(**config_data)


def _apply_env_overrides(config_data: Dict[str, Any]) -> None:
    """Apply environment variable overrides to config data."""
    
    # Ollama overrides
    if "OLLAMA_BASE_URL" in os.environ:
        config_data.setdefault("ollama", {})["base_url"] = os.environ["OLLAMA_BASE_URL"]
    
    if "OLLAMA_MODEL" in os.environ:
        config_data.setdefault("ollama", {})["model"] = os.environ["OLLAMA_MODEL"]
    
    # Logging override
    if "LOG_LEVEL" in os.environ:
        config_data.setdefault("logging", {})["level"] = os.environ["LOG_LEVEL"]
    
    # Debug mode
    if os.getenv("DEBUG", "false").lower() == "true":
        config_data.setdefault("logging", {})["level"] = "DEBUG"
