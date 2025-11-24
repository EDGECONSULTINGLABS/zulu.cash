"""Tests for Whisper diarization pipeline."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from agent_core.pipelines import WhisperDiarizationAgent
from agent_core.inference import DiarizedSegment


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        'whisper': {
            'model_size': 'tiny',
            'device': 'cpu',
            'compute_type': 'int8',
            'model_dir': './data/models/whisper',
        },
        'diarization': {
            'enabled': True,
            'backend': 'simple',
            'min_speakers': 1,
            'max_speakers': 10,
        },
        'ollama': {
            'base_url': 'http://localhost:11434',
            'model': 'llama3.1:8b',
            'temperature': 0.1,
            'num_ctx': 8192,
            'timeout': 120,
        },
        'embeddings': {
            'model': 'sentence-transformers/all-MiniLM-L6-v2',
            'device': 'cpu',
            'batch_size': 32,
        },
        'privacy': {
            'store_audio_files': False,
            'anonymize_speakers': True,
            'cleanup_after_processing': False,
        },
        'features': {
            'extract_embeddings': True,
            'extract_attention_scores': False,
        },
    }


@pytest.fixture
def mock_segments():
    """Mock diarized segments."""
    return [
        DiarizedSegment(
            speaker="SPK_1",
            start=0.0,
            end=5.0,
            text="Hello, this is a test.",
            confidence=0.95,
        ),
        DiarizedSegment(
            speaker="SPK_2",
            start=5.0,
            end=10.0,
            text="Yes, I can hear you.",
            confidence=0.93,
        ),
        DiarizedSegment(
            speaker="SPK_1",
            start=10.0,
            end=15.0,
            text="Great, let's begin the meeting.",
            confidence=0.94,
        ),
    ]


def test_diarized_segment():
    """Test DiarizedSegment creation."""
    segment = DiarizedSegment(
        speaker="SPK_1",
        start=0.0,
        end=5.0,
        text="Hello world",
        confidence=0.95,
    )
    
    assert segment.speaker == "SPK_1"
    assert segment.start == 0.0
    assert segment.end == 5.0
    assert segment.text == "Hello world"
    assert segment.confidence == 0.95


@patch('agent_core.pipelines.whisper_diarization.LocalWhisper')
@patch('agent_core.pipelines.whisper_diarization.DiarizationPipeline')
@patch('agent_core.pipelines.whisper_diarization.SessionStore')
@patch('agent_core.pipelines.whisper_diarization.OllamaClient')
@patch('agent_core.pipelines.whisper_diarization.EmbeddingModel')
def test_agent_initialization(
    mock_embedder,
    mock_ollama,
    mock_store,
    mock_diarizer,
    mock_whisper,
    mock_config,
):
    """Test agent initialization."""
    agent = WhisperDiarizationAgent(
        db_path=":memory:",
        whisper_config=mock_config['whisper'],
        diarization_config=mock_config['diarization'],
        ollama_config=mock_config['ollama'],
        embeddings_config=mock_config['embeddings'],
        privacy_config=mock_config['privacy'],
        features_config=mock_config['features'],
    )
    
    assert agent is not None
    assert mock_whisper.called
    assert mock_diarizer.called
    assert mock_store.called


@patch('agent_core.pipelines.whisper_diarization.LocalWhisper')
@patch('agent_core.pipelines.whisper_diarization.DiarizationPipeline')
@patch('agent_core.pipelines.whisper_diarization.SessionStore')
@patch('agent_core.pipelines.whisper_diarization.CallSummarizer')
@patch('agent_core.pipelines.whisper_diarization.EmbeddingModel')
def test_process_call(
    mock_embedder,
    mock_summarizer,
    mock_store,
    mock_diarizer,
    mock_whisper,
    mock_config,
    mock_segments,
):
    """Test call processing."""
    # Setup mocks
    mock_whisper_instance = Mock()
    mock_whisper_instance.transcribe.return_value = ([], Mock(language='en', language_probability=0.99))
    mock_whisper.return_value = mock_whisper_instance
    
    mock_diarizer_instance = Mock()
    mock_diarizer_instance.diarize.return_value = mock_segments
    mock_diarizer_instance.get_speaker_stats.return_value = {
        'num_speakers': 2,
        'speakers': ['SPK_1', 'SPK_2'],
    }
    mock_diarizer.return_value = mock_diarizer_instance
    
    mock_summarizer_instance = Mock()
    mock_summarizer_instance.summarize_call.return_value = {
        'summary': 'Test summary',
        'action_items': [],
        'decisions': [],
    }
    mock_summarizer.return_value = mock_summarizer_instance
    
    mock_embedder_instance = Mock()
    mock_embedder_instance.embed_summary.return_value = [0.1] * 384
    mock_embedder.return_value = mock_embedder_instance
    
    # Initialize agent
    agent = WhisperDiarizationAgent(
        db_path=":memory:",
        whisper_config=mock_config['whisper'],
        diarization_config=mock_config['diarization'],
        ollama_config=mock_config['ollama'],
        embeddings_config=mock_config['embeddings'],
        privacy_config=mock_config['privacy'],
        features_config=mock_config['features'],
    )
    
    # Process call
    session_id = agent.process_call(
        audio_path="/tmp/test.wav",
        meta={'title': 'Test Call'},
    )
    
    assert session_id is not None
    assert len(session_id) > 0


def test_speaker_anonymization():
    """Test speaker label anonymization."""
    from agent_core.utils import anonymize_speaker_label
    
    session_id = "test-session-123"
    label1 = anonymize_speaker_label("John Doe", session_id)
    label2 = anonymize_speaker_label("Jane Smith", session_id)
    
    # Should be anonymized
    assert label1.startswith("SPK_")
    assert label2.startswith("SPK_")
    
    # Should be consistent for same input
    assert anonymize_speaker_label("John Doe", session_id) == label1
    assert anonymize_speaker_label("Jane Smith", session_id) == label2
    
    # Should be different for different speakers
    assert label1 != label2


def test_feature_hashing():
    """Test feature vector hashing."""
    from agent_core.utils import hash_vector
    
    vec1 = [0.1, 0.2, 0.3, 0.4]
    vec2 = [0.1, 0.2, 0.3, 0.4]
    vec3 = [0.1, 0.2, 0.3, 0.5]
    
    hash1 = hash_vector(vec1)
    hash2 = hash_vector(vec2)
    hash3 = hash_vector(vec3)
    
    # Same vectors should have same hash
    assert hash1 == hash2
    
    # Different vectors should have different hash
    assert hash1 != hash3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
