import os

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.environ.get("LLM_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("LLM_ENCRYPTION_KEY env var is not set")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def mask(plaintext: str) -> str:
    """Return first 4 chars (or fewer) followed by ****."""
    prefix = plaintext[:4] if len(plaintext) >= 4 else plaintext
    return f"{prefix}****"
