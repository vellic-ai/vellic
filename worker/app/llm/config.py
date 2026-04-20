import os

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_K_M")

CLAUDE_CODE_BIN = os.getenv("CLAUDE_CODE_BIN", "claude")
CLAUDE_CODE_MODEL = os.getenv("CLAUDE_CODE_MODEL", "")

_EXTERNAL_PROVIDERS = {"openai", "anthropic", "claude_code"}
