#!/usr/bin/env python3
"""
Benchmark vellic LLM providers for the BYOL blog post (VEL-104).

Usage:
    # Ollama (local GPU/CPU):
    LLM_PROVIDER=ollama LLM_BASE_URL=http://localhost:11434 \
        LLM_MODEL=llama3.1:8b-instruct-q4_K_M python scripts/benchmark_llm.py

    # OpenAI BYOK:
    LLM_PROVIDER=openai LLM_API_KEY=sk-... LLM_MODEL=gpt-4o \
        python scripts/benchmark_llm.py

    # Anthropic BYOK:
    LLM_PROVIDER=anthropic LLM_API_KEY=sk-ant-... \
        LLM_MODEL=claude-3-5-sonnet-20241022 python scripts/benchmark_llm.py

Output: median review latency in seconds + quality signal notes per provider.
"""

import asyncio
import os
import statistics
import sys
import time
from pathlib import Path

# Make sure worker/app is importable when run from project root
sys.path.insert(0, str(Path(__file__).parent.parent / "worker"))

from app.llm.config import load_env_llm_config
from app.llm.providers import ollama, openai, anthropic, claude_code  # noqa: F401 – side effects
from app.llm.registry import build_provider
from app.pipeline.llm_analyzer import analyze
from app.pipeline.models import DiffChunk, PRContext

# ---------------------------------------------------------------------------
# Representative PR fixtures — Python + TypeScript, small / medium / large
# ---------------------------------------------------------------------------

_PR_SMALL = PRContext(
    repo="vellic-ai/vellic",
    pr_number=42,
    sha="abc123",
    title="fix: handle None return from llm.complete on timeout",
    body="Guard against None return value in the analyzer.",
    base_branch="main",
)

_CHUNKS_SMALL = [
    DiffChunk(
        filename="worker/app/pipeline/llm_analyzer.py",
        patch="""\
@@ -84,7 +84,10 @@ async def analyze(
     prompt = _build_prompt(context, chunks)
-    raw = await llm.complete(prompt, max_tokens=max_tokens)
+    raw = await llm.complete(prompt, max_tokens=max_tokens)
+    if raw is None:
+        logger.warning("LLM returned None for %s#%d", context.repo, context.pr_number)
+        return AnalysisResult(comments=[], summary="LLM returned no output.", generic_ratio=1.0)
     logger.debug("LLM raw response length=%d", len(raw))
""",
    )
]

_PR_MEDIUM = PRContext(
    repo="vellic-ai/vellic",
    pr_number=77,
    sha="def456",
    title="feat: add AST enrichment stage to pipeline context",
    body="Adds tree-sitter parsing for Python and TypeScript files to give the LLM "
    "richer context about function signatures and class hierarchies.",
    base_branch="main",
)

_CHUNKS_MEDIUM = [
    DiffChunk(
        filename="worker/app/pipeline/ast_enricher.py",
        patch="""\
@@ -0,0 +1,72 @@
+import logging
+from dataclasses import dataclass, field
+from pathlib import Path
+
+logger = logging.getLogger("worker.pipeline.ast_enricher")
+
+try:
+    import tree_sitter_python as tspython
+    import tree_sitter_typescript as tstypescript
+    from tree_sitter import Language, Parser
+    _HAS_TREE_SITTER = True
+except ImportError:
+    _HAS_TREE_SITTER = False
+    logger.warning("tree-sitter not available; AST enrichment disabled")
+
+
+@dataclass
+class ASTContext:
+    filename: str
+    language: str
+    functions: list[str] = field(default_factory=list)
+    classes: list[str] = field(default_factory=list)
+
+
+def enrich(filename: str, source: str) -> ASTContext | None:
+    if not _HAS_TREE_SITTER:
+        return None
+    ext = Path(filename).suffix.lower()
+    if ext == ".py":
+        lang = Language(tspython.language())
+        lang_name = "python"
+    elif ext in (".ts", ".tsx"):
+        lang = Language(tstypescript.language_typescript())
+        lang_name = "typescript"
+    else:
+        return None
+
+    parser = Parser(lang)
+    tree = parser.parse(source.encode())
+    ctx = ASTContext(filename=filename, language=lang_name)
+
+    def _walk(node):
+        if node.type in ("function_definition", "function_declaration", "method_definition"):
+            name_node = node.child_by_field_name("name")
+            if name_node:
+                ctx.functions.append(name_node.text.decode())
+        elif node.type in ("class_definition", "class_declaration"):
+            name_node = node.child_by_field_name("name")
+            if name_node:
+                ctx.classes.append(name_node.text.decode())
+        for child in node.children:
+            _walk(child)
+
+    _walk(tree.root_node)
+    return ctx
""",
    ),
    DiffChunk(
        filename="worker/app/pipeline/runner.py",
        patch="""\
@@ -12,6 +12,7 @@ from .context_gatherer import gather_context
 from .diff_fetcher import fetch_diff_chunks
+from .ast_enricher import enrich as ast_enrich
 from .llm_analyzer import analyze
 from .result_persister import persist

@@ -28,6 +29,11 @@ async def run_pipeline(event, github, pool, llm):
     chunks = await fetch_diff_chunks(context, github)
+    # Enrich chunks with AST context when source is available
+    for chunk in chunks:
+        ast_ctx = ast_enrich(chunk.filename, chunk.patch)
+        if ast_ctx:
+            chunk.ast_context = ast_ctx
     result = await analyze(context, chunks, llm)
""",
    ),
]

_PR_LARGE = PRContext(
    repo="vellic-ai/vellic",
    pr_number=99,
    sha="ghi789",
    title="refactor: migrate webhook handler to FastAPI background tasks",
    body="Replace Arq job enqueue with FastAPI BackgroundTasks for simpler local dev. "
    "Keeps the Arq path for production via feature flag.",
    base_branch="main",
)

_CHUNKS_LARGE = [
    DiffChunk(
        filename="api/app/webhook.py",
        patch="""\
@@ -1,40 +1,90 @@
+import hashlib
+import hmac
+import json
 import logging
-from fastapi import FastAPI, Request, HTTPException
+from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
+from fastapi.responses import JSONResponse

-from .queue import enqueue_job
+from .config import settings
+from .database import get_pool
+from .pipeline import run_pipeline_task

 logger = logging.getLogger("api.webhook")
 app = FastAPI()


-@app.post("/webhook/github")
-async def github_webhook(request: Request):
+def _verify_signature(body: bytes, secret: str, sig_header: str) -> bool:
+    if not sig_header or not sig_header.startswith("sha256="):
+        return False
+    expected = "sha256=" + hmac.new(
+        secret.encode(), body, hashlib.sha256
+    ).hexdigest()
+    return hmac.compare_digest(expected, sig_header)
+
+
+@app.post("/webhook/github", status_code=202)
+async def github_webhook(
+    request: Request,
+    background_tasks: BackgroundTasks,
+    x_hub_signature_256: str = Header(default=""),
+    x_github_event: str = Header(default=""),
+):
     body = await request.body()
-    payload = await request.json()
-    event_type = request.headers.get("X-GitHub-Event", "")
-    if event_type not in ("pull_request", "pull_request_review"):
-        return {"status": "ignored"}
-    job_id = await enqueue_job("process_webhook", payload=payload)
-    return {"status": "queued", "job_id": job_id}
+
+    if settings.GITHUB_WEBHOOK_SECRET:
+        if not _verify_signature(body, settings.GITHUB_WEBHOOK_SECRET, x_hub_signature_256):
+            raise HTTPException(status_code=401, detail="Invalid signature")
+
+    try:
+        payload = json.loads(body)
+    except json.JSONDecodeError as exc:
+        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
+
+    if x_github_event not in ("pull_request", "pull_request_review"):
+        return JSONResponse({"status": "ignored"})
+
+    pool = await get_pool()
+    background_tasks.add_task(run_pipeline_task, payload, pool)
+    return JSONResponse({"status": "accepted"})
""",
    ),
    DiffChunk(
        filename="api/app/pipeline.py",
        patch="""\
@@ -0,0 +1,45 @@
+import logging
+
+from .github_client import GitHubClient
+from .llm_factory import get_llm
+
+logger = logging.getLogger("api.pipeline")
+
+
+async def run_pipeline_task(payload: dict, pool) -> None:
+    try:
+        github = GitHubClient(pool)
+        llm = await get_llm(pool)
+        from worker.app.pipeline.runner import run_pipeline
+        from worker.app.adapters.github import normalize_pr
+        event = normalize_pr(payload)
+        if event is None:
+            logger.debug("webhook payload not a reviewable PR event; skipping")
+            return
+        await run_pipeline(event, github, pool, llm)
+    except Exception:
+        logger.exception("pipeline task failed for payload action=%s", payload.get("action"))
""",
    ),
    DiffChunk(
        filename="api/tests/test_webhook.py",
        patch="""\
@@ -28,6 +28,42 @@ def test_ignored_event(client):
     assert resp.json()["status"] == "ignored"

+def test_valid_pr_event_accepted(client, monkeypatch):
+    import hmac, hashlib
+    secret = "test-secret"
+    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
+    payload = json.dumps({"action": "opened", "pull_request": {"number": 1}}).encode()
+    sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
+    resp = client.post(
+        "/webhook/github",
+        content=payload,
+        headers={"X-Hub-Signature-256": sig, "X-GitHub-Event": "pull_request"},
+    )
+    assert resp.status_code == 202
+    assert resp.json()["status"] == "accepted"
+
+def test_invalid_signature_rejected(client, monkeypatch):
+    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "real-secret")
+    resp = client.post(
+        "/webhook/github",
+        content=b'{"action":"opened"}',
+        headers={"X-Hub-Signature-256": "sha256=bad", "X-GitHub-Event": "pull_request"},
+    )
+    assert resp.status_code == 401
""",
    ),
]

FIXTURES = [
    ("small (~50 lines)", _PR_SMALL, _CHUNKS_SMALL),
    ("medium (~150 lines)", _PR_MEDIUM, _CHUNKS_MEDIUM),
    ("large (~300 lines)", _PR_LARGE, _CHUNKS_LARGE),
]

RUNS_PER_FIXTURE = 3


async def benchmark_provider(provider_label: str, llm) -> dict:
    print(f"\n{'='*60}")
    print(f"Provider: {provider_label}")
    print(f"{'='*60}")

    all_latencies: list[float] = []
    quality_notes: list[str] = []

    for label, pr_ctx, chunks in FIXTURES:
        latencies = []
        last_result = None

        for run in range(RUNS_PER_FIXTURE):
            start = time.perf_counter()
            try:
                result = await analyze(pr_ctx, chunks, llm)
                elapsed = time.perf_counter() - start
                latencies.append(elapsed)
                last_result = result
                print(f"  [{label}] run {run+1}: {elapsed:.1f}s")
            except Exception as exc:
                elapsed = time.perf_counter() - start
                print(f"  [{label}] run {run+1}: ERROR after {elapsed:.1f}s — {exc}")

        if latencies:
            all_latencies.extend(latencies)
            median = statistics.median(latencies)
            print(f"  [{label}] median: {median:.1f}s")

            if last_result:
                n_comments = len(last_result.comments)
                generic = last_result.generic_ratio
                quality_notes.append(
                    f"{label}: {n_comments} comment(s), generic_ratio={generic:.2f}, "
                    f'summary="{last_result.summary[:80]}"'
                )

    summary = {}
    if all_latencies:
        summary["median_latency_s"] = round(statistics.median(all_latencies), 1)
        summary["p90_latency_s"] = round(sorted(all_latencies)[int(len(all_latencies) * 0.9)], 1)
        summary["quality_notes"] = quality_notes
        print(f"\n  Overall median latency: {summary['median_latency_s']}s")
        print(f"  Overall p90 latency:    {summary['p90_latency_s']}s")
    else:
        summary["error"] = "No successful runs"

    return summary


async def main():
    cfg = load_env_llm_config()
    provider_name = cfg["provider"]
    model = cfg.get("model", "")
    label = f"{provider_name} / {model}" if model else provider_name

    print(f"vellic LLM Benchmark — VEL-104")
    print(f"Provider config: {label}")
    print(f"Fixtures: {len(FIXTURES)} sizes × {RUNS_PER_FIXTURE} runs each")

    llm = build_provider(
        provider_name,
        base_url=cfg.get("base_url", ""),
        model=model,
        api_key=cfg.get("api_key", ""),
        bin_path=cfg.get("bin_path", "claude"),
    )

    results = await benchmark_provider(label, llm)

    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Provider:        {label}")
    if "error" in results:
        print(f"Status:          FAILED — {results['error']}")
    else:
        print(f"Median latency:  {results['median_latency_s']}s")
        print(f"P90 latency:     {results['p90_latency_s']}s")
        print("Quality notes:")
        for note in results.get("quality_notes", []):
            print(f"  {note}")


if __name__ == "__main__":
    asyncio.run(main())
