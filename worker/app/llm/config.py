import os

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_K_M")
_EXTERNAL_PROVIDERS = {"openai", "anthropic"}
