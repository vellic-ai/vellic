import asyncio
import logging
import shutil

from ..registry import register

logger = logging.getLogger("worker.llm.claude_code")

_CLOSED_LOOP_WARNING = (
    "\u26a0\ufe0f  External LLM provider enabled (Claude Code). "
    "PR diff content will leave your infrastructure via the Anthropic API. "
    "Ollama remains the only fully closed-loop option."
)


@register("claude_code")
class ClaudeCodeProvider:
    """LLM provider backed by a local Claude Code CLI subprocess."""

    def __init__(self, bin_path: str = "claude", model: str = "", **_: object) -> None:
        self._bin = bin_path
        self._model = model
        logger.warning(_CLOSED_LOOP_WARNING)
        logger.info(
            "Claude Code provider configured: bin=%s model=%s",
            self._bin,
            self._model or "(default)",
        )

    async def complete(self, prompt: str, *, max_tokens: int) -> str:  # noqa: ARG002
        cmd = [self._bin, "--print"]
        if self._model:
            cmd += ["--model", self._model]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=prompt.encode())
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude exited with code {proc.returncode}: {stderr.decode().strip()}"
            )
        return stdout.decode().strip()

    async def health(self) -> bool:
        if not shutil.which(self._bin):
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                self._bin, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False
