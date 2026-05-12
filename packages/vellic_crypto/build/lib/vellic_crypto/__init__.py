"""Shared Fernet-based encryption used by admin, worker, and api.

Key resolution (first match wins):
  1. ``LLM_ENCRYPTION_KEY`` env var.
  2. File at ``$VELLIC_SECRETS_DIR/llm_encryption_key``
     (default ``/data/secrets/llm_encryption_key``).
  3. Auto-generate a new Fernet key and persist it to that file.

The file lives on a shared Docker volume so all services read the same key,
and the key survives container restarts. Users can still override by setting
``LLM_ENCRYPTION_KEY`` in the environment.
"""

from __future__ import annotations

import binascii
import os
from pathlib import Path

from cryptography.fernet import Fernet

__all__ = ["encrypt", "decrypt", "mask", "get_fernet", "KeyError"]


class KeyError(RuntimeError):  # noqa: A001 — domain-specific error name
    """Raised when the Fernet key is missing or malformed."""


def _secrets_dir() -> Path:
    return Path(os.environ.get("VELLIC_SECRETS_DIR", "/data/secrets"))


def _key_file() -> Path:
    return _secrets_dir() / "llm_encryption_key"


def _load_or_generate() -> bytes:
    path = _key_file()
    if path.exists():
        data = path.read_bytes().strip()
        if not data:
            raise KeyError(f"Key file {path} is empty")
        return data

    # Generate, persist atomically (write to tmp, rename).
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(key)
    try:
        tmp.chmod(0o600)
    except OSError:
        pass  # best-effort on filesystems that don't support chmod
    os.replace(tmp, path)
    return key


def get_fernet() -> Fernet:
    env = os.environ.get("LLM_ENCRYPTION_KEY")
    raw = env.encode() if env else _load_or_generate()
    try:
        return Fernet(raw)
    except (ValueError, binascii.Error) as exc:
        raise KeyError(
            "Invalid Fernet key: must be 32 url-safe base64-encoded bytes"
        ) from exc


def encrypt(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return get_fernet().decrypt(ciphertext.encode()).decode()


def mask(plaintext: str) -> str:
    """Return first 4 chars (or fewer) followed by ****."""
    prefix = plaintext[:4] if len(plaintext) >= 4 else plaintext
    return f"{prefix}****"
