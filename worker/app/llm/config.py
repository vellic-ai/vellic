import os

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_K_M")

CLAUDE_CODE_BIN = os.getenv("CLAUDE_CODE_BIN", "claude")
CLAUDE_CODE_MODEL = os.getenv("CLAUDE_CODE_MODEL", "")

_EXTERNAL_PROVIDERS = {"openai", "anthropic", "claude_code"}


def load_env_llm_config() -> dict:
    """Return LLM config dict built from environment variables (fallback path)."""
    provider = os.getenv("LLM_PROVIDER", "ollama")
    base_url = os.getenv("LLM_BASE_URL", "http://ollama:11434")
    llm_model = os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_K_M")
    cc_model = os.getenv("CLAUDE_CODE_MODEL", "")
    cc_bin = os.getenv("CLAUDE_CODE_BIN", "claude")
    model = cc_model if provider == "claude_code" and cc_model else llm_model
    api_key = os.getenv("LLM_API_KEY", "") if provider in _EXTERNAL_PROVIDERS else ""
    return {
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "api_key": api_key,
        "bin_path": cc_bin,
        "extra": {},
    }
