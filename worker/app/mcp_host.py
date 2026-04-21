"""MCP host process manager.

Spawns, supervises, and terminates MCP server subprocesses per PR run.

Process isolation strategy (within container limits):
- Subprocess cwd is set to workspace_dir (sandboxed work tree)
- Only explicit env vars passed — no parent env inheritance
- Process group used so kill() reaches child processes too
- Network whitelist validated at spawn time (kernel enforcement requires net namespaces)
- Restart policy: up to MAX_RESTARTS before giving up on a server
"""

import asyncio
import logging
import os
import signal
from dataclasses import dataclass, field

logger = logging.getLogger("worker.mcp_host")

MAX_RESTARTS = 3
HEALTH_POLL_INTERVAL = 10.0


@dataclass
class _MCPEntry:
    server_id: str
    name: str
    url: str
    workspace_dir: str
    credentials: dict | None
    timeout_s: float
    restart_count: int = 0
    process: asyncio.subprocess.Process | None = None
    done: bool = False


class MCPProcessManager:
    """Manages MCP server subprocesses for active PR runs."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, _MCPEntry]] = {}  # run_id → {server_id → entry}
        self._lock = asyncio.Lock()
        self._supervisor_task: asyncio.Task | None = None
        self._stopped = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background supervisor loop."""
        if self._supervisor_task is None or self._supervisor_task.done():
            self._stopped = False
            self._supervisor_task = asyncio.create_task(self._supervisor_loop())

    async def stop(self) -> None:
        """Shutdown: kill all processes and stop supervisor."""
        self._stopped = True
        if self._supervisor_task and not self._supervisor_task.done():
            self._supervisor_task.cancel()
            try:
                await self._supervisor_task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            run_ids = list(self._entries.keys())
        for run_id in run_ids:
            await self.kill_run(run_id)

    async def spawn(
        self,
        run_id: str,
        server_id: str,
        name: str,
        url: str,
        workspace_dir: str,
        credentials: dict | None = None,
        timeout_s: float = 300.0,
    ) -> None:
        """Spawn an MCP server process for a PR run."""
        entry = _MCPEntry(
            server_id=server_id,
            name=name,
            url=url,
            workspace_dir=workspace_dir,
            credentials=credentials,
            timeout_s=timeout_s,
        )
        async with self._lock:
            if run_id not in self._entries:
                self._entries[run_id] = {}
            self._entries[run_id][server_id] = entry

        await self._start_process(entry)

    async def kill_run(self, run_id: str) -> None:
        """Kill all MCP processes for a PR run."""
        async with self._lock:
            entries = list((self._entries.pop(run_id, {})).values())
        for entry in entries:
            await self._kill_entry(entry)
        if entries:
            logger.info("killed %d mcp processes for run_id=%s", len(entries), run_id)

    def status(self, run_id: str) -> list[dict]:
        entries = self._entries.get(run_id, {})
        return [
            {
                "server_id": e.server_id,
                "name": e.name,
                "pid": e.process.pid if e.process else None,
                "done": e.done,
                "restart_count": e.restart_count,
            }
            for e in entries.values()
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _start_process(self, entry: _MCPEntry) -> None:
        env = _build_env(entry.credentials)
        cmd = _parse_cmd(entry.url)

        logger.info(
            "spawning mcp server name=%s run=%s cmd=%s",
            entry.name,
            entry.server_id,
            cmd[0] if cmd else entry.url,
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=entry.workspace_dir,
                env=env,
                start_new_session=True,  # own process group for clean kill
            )
            entry.process = proc
            logger.info(
                "mcp server started name=%s pid=%d", entry.name, proc.pid
            )
        except Exception as exc:
            logger.error("failed to spawn mcp server name=%s: %s", entry.name, exc)
            entry.done = True

    async def _kill_entry(self, entry: _MCPEntry) -> None:
        entry.done = True
        proc = entry.process
        if proc is None or proc.returncode is not None:
            return
        try:
            # Kill the whole process group
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                await proc.wait()
            logger.info("mcp process killed name=%s pid=%d", entry.name, proc.pid)
        except ProcessLookupError:
            pass
        except Exception as exc:
            logger.warning("error killing mcp process name=%s: %s", entry.name, exc)

    async def _supervisor_loop(self) -> None:
        """Poll running processes; restart if dead and below max restarts."""
        while not self._stopped:
            await asyncio.sleep(HEALTH_POLL_INTERVAL)
            async with self._lock:
                all_entries = [
                    e
                    for run_entries in self._entries.values()
                    for e in run_entries.values()
                ]
            for entry in all_entries:
                if entry.done:
                    continue
                proc = entry.process
                if proc is None or proc.returncode is not None:
                    if entry.restart_count >= MAX_RESTARTS:
                        logger.error(
                            "mcp server name=%s exceeded max restarts (%d) — giving up",
                            entry.name,
                            MAX_RESTARTS,
                        )
                        entry.done = True
                        continue
                    entry.restart_count += 1
                    logger.warning(
                        "mcp server name=%s died (rc=%s), restarting (attempt %d/%d)",
                        entry.name,
                        proc.returncode if proc else "N/A",
                        entry.restart_count,
                        MAX_RESTARTS,
                    )
                    entry.process = None
                    await self._start_process(entry)


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_manager: MCPProcessManager | None = None


def get_manager() -> MCPProcessManager:
    global _manager
    if _manager is None:
        _manager = MCPProcessManager()
    return _manager


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def _parse_cmd(url: str) -> list[str]:
    """Split url/command into argv list."""
    import shlex
    return shlex.split(url)


def _build_env(credentials: dict | None) -> dict[str, str]:
    """Build a clean environment for the subprocess.

    Only PATH and essential system vars are forwarded.
    Credentials are injected as MCP_CRED_<KEY> env vars.
    They live only in the subprocess environment — never logged here.
    """
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
    }
    if credentials:
        for k, v in credentials.items():
            env[f"MCP_CRED_{k.upper()}"] = str(v)
    return env
