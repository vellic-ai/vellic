import logging
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm import LLMProvider, build_provider
from app.llm.registry import _REGISTRY
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.vllm import VLLMProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.anthropic import AnthropicProvider


# --- registry ---

def test_registry_contains_all_providers():
    assert set(_REGISTRY) >= {"ollama", "vllm", "openai", "anthropic"}


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
    assert isinstance(OpenAIProvider(), LLMProvider)


def test_anthropic_conforms_to_protocol():
    assert isinstance(AnthropicProvider(), LLMProvider)


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

    with patch.object(provider._client, "post", new=AsyncMock(return_value=mock_response)) as mock_post:
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

    with patch.object(provider._client, "get", new=AsyncMock(side_effect=Exception("connection refused"))):
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


# --- OpenAI stub ---

def test_openai_logs_closed_loop_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="worker.llm.openai"):
        OpenAIProvider()
    assert "PR diff content will leave your infrastructure" in caplog.text


@pytest.mark.asyncio
async def test_openai_complete_raises_not_implemented():
    provider = OpenAIProvider()
    with pytest.raises(NotImplementedError, match="OpenAI"):
        await provider.complete("prompt", max_tokens=100)


# --- Anthropic stub ---

def test_anthropic_logs_closed_loop_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="worker.llm.anthropic"):
        AnthropicProvider()
    assert "PR diff content will leave your infrastructure" in caplog.text


@pytest.mark.asyncio
async def test_anthropic_complete_raises_not_implemented():
    provider = AnthropicProvider()
    with pytest.raises(NotImplementedError, match="Anthropic"):
        await provider.complete("prompt", max_tokens=100)
