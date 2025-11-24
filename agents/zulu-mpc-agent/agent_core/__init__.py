"""ZULU MPC Agent - Privacy-preserving voice AI agent."""

__version__ = "0.1.0"
__author__ = "Edge Consulting Labs"

from .pipelines import WhisperDiarizationAgent
from .utils import load_config, setup_logging

__all__ = [
    "WhisperDiarizationAgent",
    "load_config",
    "setup_logging",
]
