import os

import pytest
from cryptography.fernet import Fernet

import vellic_crypto as vc


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch, tmp_path):
    monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("VELLIC_SECRETS_DIR", str(tmp_path))
    yield


def test_auto_generates_key_on_first_call(tmp_path):
    # No env, no file -> key is generated and persisted.
    assert not (tmp_path / "llm_encryption_key").exists()
    ct = vc.encrypt("hello")
    assert vc.decrypt(ct) == "hello"
    assert (tmp_path / "llm_encryption_key").exists()


def test_reuses_key_across_calls(tmp_path):
    ct = vc.encrypt("one")
    # Second call must use the already-persisted key, not regenerate.
    assert vc.decrypt(ct) == "one"
    assert vc.decrypt(vc.encrypt("two")) == "two"


def test_env_var_overrides_file(monkeypatch, tmp_path):
    env_key = Fernet.generate_key().decode()
    monkeypatch.setenv("LLM_ENCRYPTION_KEY", env_key)
    # Write a DIFFERENT key to the file; env should win.
    file_key = Fernet.generate_key()
    (tmp_path / "llm_encryption_key").write_bytes(file_key)

    ct = vc.encrypt("secret")
    # Decrypting with env key works.
    assert Fernet(env_key.encode()).decrypt(ct.encode()).decode() == "secret"


def test_invalid_env_key_raises_keyerror(monkeypatch):
    monkeypatch.setenv("LLM_ENCRYPTION_KEY", "not-a-real-fernet-key")
    with pytest.raises(vc.KeyError):
        vc.encrypt("hi")


def test_mask_short_and_long():
    assert vc.mask("ab") == "ab****"
    assert vc.mask("sk-abcdef") == "sk-a****"


def test_key_file_permissions(tmp_path):
    vc.encrypt("x")
    mode = (tmp_path / "llm_encryption_key").stat().st_mode & 0o777
    # On POSIX should be 0o600; on non-POSIX may differ — only check it is readable.
    assert mode & 0o400, f"key file is not readable, mode={oct(mode)}"
    if os.name == "posix":
        assert mode == 0o600
