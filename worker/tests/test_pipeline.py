import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.github import normalize_pr
from app.events import PREvent
from app.pipeline.context_gatherer import gather_context
from app.pipeline.diff_fetcher import _chunk_patch, _is_generated, fetch_diff_chunks
from app.pipeline.llm_analyzer import _build_prompt, _extract_json, analyze
from app.pipeline.models import AnalysisResult, DiffChunk, PRContext, ReviewComment
from app.pipeline.result_persister import persist


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


def test_diff_chunk_patch_property():
    chunk = DiffChunk(filename="app.py", patch_lines=["+foo", "-bar"])
    assert chunk.patch == "+foo\n-bar"


# ---------------------------------------------------------------------------
# adapters/github — normalize_pr
# ---------------------------------------------------------------------------

_SAMPLE_PAYLOAD = {
    "action": "opened",
    "repository": {"full_name": "acme/backend"},
    "pull_request": {
        "number": 42,
        "head": {"sha": "abc123"},
        "base": {"sha": "def456", "ref": "main"},
        "title": "Add caching layer",
        "body": "Caches DB results in Redis.",
        "diff_url": "https://github.com/acme/backend/pull/42.diff",
    },
}


def test_normalize_pr_fields():
    event = normalize_pr("delivery-1", _SAMPLE_PAYLOAD)
    assert isinstance(event, PREvent)
    assert event.platform == "github"
    assert event.delivery_id == "delivery-1"
    assert event.repo == "acme/backend"
    assert event.pr_number == 42
    assert event.head_sha == "abc123"
    assert event.base_sha == "def456"
    assert event.base_branch == "main"
    assert event.title == "Add caching layer"
    assert event.description == "Caches DB results in Redis."
    assert event.diff_url == "https://api.github.com/repos/acme/backend/pulls/42/files"


def test_normalize_pr_null_body():
    payload = {**_SAMPLE_PAYLOAD, "pull_request": {**_SAMPLE_PAYLOAD["pull_request"], "body": None}}
    event = normalize_pr("delivery-2", payload)
    assert event.description == ""


# ---------------------------------------------------------------------------
# context_gatherer
# ---------------------------------------------------------------------------

_SAMPLE_EVENT = PREvent(
    platform="github",
    event_type="pull_request",
    delivery_id="delivery-1",
    repo="acme/backend",
    pr_number=42,
    action="opened",
    diff_url="https://api.github.com/repos/acme/backend/pulls/42/files",
    base_sha="def456",
    head_sha="abc123",
    base_branch="main",
    title="Add caching layer",
    description="Caches DB results in Redis.",
)


def test_gather_context_from_event():
    ctx = gather_context(_SAMPLE_EVENT)
    assert ctx.repo == "acme/backend"
    assert ctx.pr_number == 42
    assert ctx.commit_sha == "abc123"
    assert ctx.title == "Add caching layer"
    assert ctx.body == "Caches DB results in Redis."
    assert ctx.base_branch == "main"


def test_gather_context_empty_description():
    event = PREvent(
        platform="github",
        event_type="pull_request",
        delivery_id="d",
        repo="acme/backend",
        pr_number=1,
        action="opened",
        diff_url="https://api.github.com/repos/acme/backend/pulls/1/files",
        base_sha="s",
        head_sha="h",
        base_branch="main",
        title="t",
        description="",
    )
    ctx = gather_context(event)
    assert ctx.body == ""


# ---------------------------------------------------------------------------
# diff_fetcher — _is_generated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("poetry.lock", True),
        ("package-lock.json", True),
        ("dist/bundle.js", True),
        ("src/dist/output.css", True),
        ("app.min.js", True),
        ("styles.min.css", True),
        ("node_modules/lodash/index.js", True),
        ("vendor/lib.py", True),
        ("src/app.py", False),
        ("README.md", False),
        ("tests/test_cache.py", False),
    ],
)
def test_is_generated(filename, expected):
    assert _is_generated(filename) is expected


def test_chunk_patch_splits_at_500_lines():
    patch = "\n".join(f"+line{i}" for i in range(1050))
    chunks = _chunk_patch("big.py", patch)
    assert len(chunks) == 3
    assert len(chunks[0].patch_lines) == 500
    assert len(chunks[1].patch_lines) == 500
    assert len(chunks[2].patch_lines) == 50


def test_chunk_patch_small_file():
    patch = "+single line"
    chunks = _chunk_patch("small.py", patch)
    assert len(chunks) == 1
    assert chunks[0].filename == "small.py"


@pytest.mark.asyncio
async def test_fetch_diff_chunks_filters_binary_and_generated():
    files = [
        {"filename": "src/app.py", "patch": "+foo"},
        {"filename": "dist/bundle.js", "patch": "+bar"},
        {"filename": "image.png"},  # no patch — binary
    ]
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = files

    with patch("app.pipeline.diff_fetcher.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)
        chunks = await fetch_diff_chunks(
            "https://api.github.com/repos/acme/backend/pulls/42/files",
            token="tok",
        )

    assert len(chunks) == 1
    assert chunks[0].filename == "src/app.py"


# ---------------------------------------------------------------------------
# llm_analyzer — _extract_json
# ---------------------------------------------------------------------------


def test_extract_json_raw():
    data = '{"comments": [], "summary": "ok", "generic_ratio": 0.0}'
    assert _extract_json(data) == {"comments": [], "summary": "ok", "generic_ratio": 0.0}


def test_extract_json_fenced_block():
    data = '```json\n{"comments": [], "summary": "ok", "generic_ratio": 0.1}\n```'
    assert _extract_json(data)["summary"] == "ok"


def test_extract_json_embedded():
    data = 'Here is my answer:\n{"comments": [], "summary": "lgtm", "generic_ratio": 0.0}\nDone.'
    assert _extract_json(data)["summary"] == "lgtm"


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError):
        _extract_json("no json here at all")


@pytest.mark.asyncio
async def test_analyze_empty_chunks():
    ctx = PRContext("acme/x", 1, "sha", "title", "", "main")
    llm = MagicMock()
    result = await analyze(ctx, [], llm)
    assert result.comments == []
    assert "No reviewable" in result.summary


@pytest.mark.asyncio
async def test_analyze_parses_llm_response():
    ctx = PRContext("acme/x", 1, "sha", "title", "", "main")
    chunks = [DiffChunk("app.py", ["+foo = 1"])]

    llm_response = json.dumps(
        {
            "comments": [
                {"file": "app.py", "line": 1, "body": "Use const", "confidence": 0.9, "rationale": "immutability"}
            ],
            "summary": "Minor style issue.",
            "generic_ratio": 0.0,
        }
    )
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=llm_response)

    result = await analyze(ctx, chunks, llm)
    assert len(result.comments) == 1
    assert result.comments[0].file == "app.py"
    assert result.summary == "Minor style issue."


@pytest.mark.asyncio
async def test_analyze_handles_bad_json():
    ctx = PRContext("acme/x", 1, "sha", "title", "", "main")
    chunks = [DiffChunk("app.py", ["+x = 1"])]
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="sorry I cannot do that")

    result = await analyze(ctx, chunks, llm)
    assert result.comments == []
    assert result.generic_ratio == 1.0


# ---------------------------------------------------------------------------
# result_persister
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_inserts_and_enqueues():
    context = PRContext("acme/backend", 42, "abc123", "title", "", "main")
    result = AnalysisResult(
        comments=[ReviewComment("app.py", 10, "nice", 0.8, "rationale")],
        summary="Looks good.",
        generic_ratio=0.0,
    )
    job_id = uuid.uuid4()
    pr_review_id = uuid.uuid4()

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"id": pr_review_id})
    mock_conn.execute = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    mock_arq = AsyncMock()

    returned = await persist(mock_pool, context, result, job_id, mock_arq)

    assert returned == str(pr_review_id)
    mock_arq.enqueue_job.assert_called_once_with("post_feedback", str(pr_review_id))
