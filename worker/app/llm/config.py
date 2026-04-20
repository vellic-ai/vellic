import os

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_K_M")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
