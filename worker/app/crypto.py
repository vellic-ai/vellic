"""Worker-side crypto wrapper. Delegates to :mod:`vellic_crypto`."""

from vellic_crypto import decrypt, encrypt

__all__ = ["encrypt", "decrypt"]
