import os

CLAUDE_CODE_BIN = os.getenv("CLAUDE_CODE_BIN", "claude")
CLAUDE_CODE_MODEL = os.getenv("CLAUDE_CODE_MODEL", "")

_EXTERNAL_PROVIDERS = {"openai", "anthropic", "claude_code"}
