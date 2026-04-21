import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm import LLMProvider, build_provider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.claude_code import ClaudeCodeProvider
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.vllm import VLLMProvider
from app.llm.registry import _REGISTRY

# --- registry ---

def test_registry_contains_all_providers():
    assert set(_REGISTRY) >= {"ollama", "vllm", "openai", "anthropic", "claude_code"}


def test_build_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_provider("nonexistent")


def test_build_provider_returns_ollama():
    provider = build_provider("ollama", base_url="http://localhost:11434", model="llama3.1:8b")
    assert isinstance(provider, OllamaProvider)


# --- protocol conformance ---

def test_ollama_conforms_to_protocol():
    provider = build_provider("ollama", base_url="http://localhost:11434", model="test")
    assert isinstance(provider, LLMProvider)


def test_vllm_conforms_to_protocol():
    assert isinstance(VLLMProvider(), LLMProvider)


def test_openai_conforms_to_protocol():
    assert isinstance(OpenAIProvider(api_key="test-key"), LLMProvider)


def test_anthropic_conforms_to_protocol():
    assert isinstance(AnthropicProvider(api_key="test-key"), LLMProvider)


# --- Ollama adapter ---

@pytest.mark.asyncio
async def test_ollama_complete_success():
    provider = OllamaProvider(base_url="http://ollama:11434", model="llama3.1:8b")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "looks good"}

    with patch.object(provider._client, "post", new=AsyncMock(return_value=mock_response)):
        result = await provider.complete("review this diff", max_tokens=512)

    assert result == "looks good"


@pytest.mark.asyncio
async def test_ollama_complete_passes_max_tokens():
    provider = OllamaProvider(base_url="http://ollama:11434", model="llama3.1:8b")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "ok"}

    with patch.object(
        provider._client, "post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        await provider.complete("prompt", max_tokens=256)

    call_kwargs = mock_post.call_args
    body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
    assert body["options"]["num_predict"] == 256
    assert body["stream"] is False


@pytest.mark.asyncio
async def test_ollama_health_true_on_200():
    provider = OllamaProvider(base_url="http://ollama:11434", model="llama3.1:8b")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(provider._client, "get", new=AsyncMock(return_value=mock_response)):
        assert await provider.health() is True


@pytest.mark.asyncio
async def test_ollama_health_false_on_connection_error():
    provider = OllamaProvider(base_url="http://ollama:11434", model="llama3.1:8b")

    with patch.object(
        provider._client, "get", new=AsyncMock(side_effect=Exception("connection refused"))
    ):
        assert await provider.health() is False


# --- vLLM stub ---

@pytest.mark.asyncio
async def test_vllm_complete_raises_not_implemented():
    provider = VLLMProvider()
    with pytest.raises(NotImplementedError, match="vLLM"):
        await provider.complete("prompt", max_tokens=100)


@pytest.mark.asyncio
async def test_vllm_health_returns_false():
    assert await VLLMProvider().health() is False


# --- OpenAI provider ---

def test_openai_logs_closed_loop_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="worker.llm.openai"):
        OpenAIProvider(api_key="test-key")
    assert "PR diff content will leave your infrastructure" in caplog.text


@pytest.mark.asyncio
async def test_openai_complete_success():
    provider = OpenAIProvider(api_key="test-key")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "looks good"}}]
    }

    with patch.object(provider._client, "post", new=AsyncMock(return_value=mock_response)):
        result = await provider.complete("review this diff", max_tokens=512)

    assert result == "looks good"


# --- Anthropic provider ---

def test_anthropic_logs_closed_loop_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="worker.llm.anthropic"):
        AnthropicProvider(api_key="test-key")
    assert "PR diff content will leave your infrastructure" in caplog.text


@pytest.mark.asyncio
async def test_anthropic_complete_success():
    provider = AnthropicProvider(api_key="test-key")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"content": [{"text": "lgtm"}]}

    with patch.object(provider._client, "post", new=AsyncMock(return_value=mock_response)):
        result = await provider.complete("review this diff", max_tokens=512)

    assert result == "lgtm"


# --- Claude Code adapter ---

def test_claude_code_conforms_to_protocol():
    provider = ClaudeCodeProvider()
    assert isinstance(provider, LLMProvider)


def test_claude_code_logs_closed_loop_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="worker.llm.claude_code"):
        ClaudeCodeProvider()
    assert "PR diff content will leave your infrastructure" in caplog.text


def _make_fake_process(returncode: int, stdout: bytes = b"", stderr: bytes = b""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.mark.asyncio
async def test_claude_code_complete_returns_stdout():
    provider = ClaudeCodeProvider(bin_path="claude")
    fake_proc = _make_fake_process(0, stdout=b"  review result\n")

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc) as mock_exec:
        result = await provider.complete("review this diff", max_tokens=512)

    assert result == "review result"
    call_args = mock_exec.call_args[0]
    assert call_args[0] == "claude"
    assert "--print" in call_args


@pytest.mark.asyncio
async def test_claude_code_complete_passes_model():
    provider = ClaudeCodeProvider(bin_path="claude", model="claude-opus-4-7")
    fake_proc = _make_fake_process(0, stdout=b"ok")

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc) as mock_exec:
        await provider.complete("prompt", max_tokens=256)

    cmd = list(mock_exec.call_args[0])
    assert "--model" in cmd
    assert "claude-opus-4-7" in cmd


@pytest.mark.asyncio
async def test_claude_code_complete_no_model_flag_when_unset():
    provider = ClaudeCodeProvider(bin_path="claude", model="")
    fake_proc = _make_fake_process(0, stdout=b"ok")

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc) as mock_exec:
        await provider.complete("prompt", max_tokens=256)

    cmd = list(mock_exec.call_args[0])
    assert "--model" not in cmd


@pytest.mark.asyncio
async def test_claude_code_complete_raises_on_nonzero_exit():
    provider = ClaudeCodeProvider(bin_path="claude")
    fake_proc = _make_fake_process(1, stderr=b"authentication required")

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        with pytest.raises(RuntimeError, match="authentication required"):
            await provider.complete("prompt", max_tokens=512)


@pytest.mark.asyncio
async def test_claude_code_health_true_when_binary_found_and_version_ok():
    provider = ClaudeCodeProvider(bin_path="claude")
    fake_proc = _make_fake_process(0)

    with patch("shutil.which", return_value="/usr/local/bin/claude"), \
         patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        assert await provider.health() is True


@pytest.mark.asyncio
async def test_claude_code_health_false_when_binary_missing():
    provider = ClaudeCodeProvider(bin_path="claude")

    with patch("shutil.which", return_value=None):
        assert await provider.health() is False


@pytest.mark.asyncio
async def test_claude_code_health_false_on_subprocess_exception():
    provider = ClaudeCodeProvider(bin_path="claude")

    with patch("shutil.which", return_value="/usr/local/bin/claude"), \
         patch("asyncio.create_subprocess_exec", side_effect=OSError("not found")):
        assert await provider.health() is False
