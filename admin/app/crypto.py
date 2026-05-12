"""Thin wrapper around :mod:`vellic_crypto` that surfaces a 503 for this FastAPI app."""

import vellic_crypto
from fastapi import HTTPException
from vellic_crypto import mask

__all__ = ["encrypt", "decrypt", "mask"]


def encrypt(plaintext: str) -> str:
    try:
        return vellic_crypto.encrypt(plaintext)
    except vellic_crypto.KeyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Server is not configured: {exc}",
        ) from exc


def decrypt(ciphertext: str) -> str:
    try:
        return vellic_crypto.decrypt(ciphertext)
    except vellic_crypto.KeyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Server is not configured: {exc}",
        ) from exc
