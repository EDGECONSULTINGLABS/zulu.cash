"""Cryptographic utilities for ZULU MPC Agent."""

import base64
import hashlib
import os
from typing import List, Union

import numpy as np
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def sha256_hex(data: Union[str, bytes]) -> str:
    """
    Compute SHA256 hash and return as hex string.
    
    Args:
        data: Input data (string or bytes).
        
    Returns:
        Hex-encoded SHA256 hash.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def sha256_b64(data: Union[str, bytes, np.ndarray]) -> str:
    """
    Compute SHA256 hash and return as base64 string.
    
    Args:
        data: Input data (string, bytes, or numpy array).
        
    Returns:
        Base64-encoded SHA256 hash.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    elif isinstance(data, np.ndarray):
        data = data.tobytes()
    
    digest = hashlib.sha256(data).digest()
    return base64.b64encode(digest).decode('utf-8')


def hash_vector(vec: List[float]) -> str:
    """
    Hash a feature vector for local verification.
    
    Args:
        vec: Feature vector.
        
    Returns:
        Base64-encoded hash.
    """
    arr = np.array(vec, dtype=np.float32)
    return sha256_b64(arr)


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded encryption key.
    """
    return Fernet.generate_key().decode('utf-8')


def derive_key_from_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """
    Derive an encryption key from a password using PBKDF2.
    
    Args:
        password: User password.
        salt: Salt for key derivation. Generated if None.
        
    Returns:
        Tuple of (key, salt).
    """
    if salt is None:
        salt = os.urandom(32)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,  # OWASP recommended minimum
    )
    key = kdf.derive(password.encode('utf-8'))
    return key, salt


class SecureRandom:
    """Cryptographically secure random number generator."""
    
    @staticmethod
    def token_hex(nbytes: int = 32) -> str:
        """Generate a random token as hex string."""
        return os.urandom(nbytes).hex()
    
    @staticmethod
    def token_urlsafe(nbytes: int = 32) -> str:
        """Generate a URL-safe random token."""
        return base64.urlsafe_b64encode(os.urandom(nbytes)).decode('utf-8')
    
    @staticmethod
    def uuid() -> str:
        """Generate a UUID-like random identifier."""
        import uuid
        return str(uuid.uuid4())


def sanitize_pii(text: str) -> str:
    """
    Basic PII sanitization (placeholder - extend with NER models).
    
    Args:
        text: Input text.
        
    Returns:
        Sanitized text.
    """
    # TODO: Implement proper PII detection using spaCy or similar
    # For now, just a placeholder that returns the original text
    # In production, you'd want to:
    # 1. Detect emails, phone numbers, SSNs
    # 2. Detect names, addresses
    # 3. Replace with generic tokens
    return text


def anonymize_speaker_label(label: str, session_id: str) -> str:
    """
    Create an anonymized but consistent speaker label.
    
    Args:
        label: Original speaker label.
        session_id: Session ID for consistency.
        
    Returns:
        Anonymized label (e.g., SPK_1, SPK_2).
    """
    # Create a deterministic hash for consistent labeling within a session
    combined = f"{session_id}:{label}"
    hash_val = int(hashlib.sha256(combined.encode()).hexdigest()[:8], 16)
    speaker_num = (hash_val % 10) + 1  # SPK_1 to SPK_10
    return f"SPK_{speaker_num}"
