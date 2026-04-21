"""Property-based tests for diff parsing using Hypothesis.

These tests verify invariants that should hold for all inputs, not just
hand-crafted examples.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.pipeline.diff_fetcher import _chunk_patch, _is_generated


# ---------------------------------------------------------------------------
# _is_generated — should always return bool, never raise
# ---------------------------------------------------------------------------


@given(st.text(min_size=0, max_size=200))
def test_is_generated_always_returns_bool(filename: str):
    result = _is_generated(filename)
    assert isinstance(result, bool)


@given(st.just("poetry.lock"))
def test_is_generated_lock_file(filename: str):
    assert _is_generated(filename) is True


@given(st.just("src/app.py"))
def test_is_generated_source_file(filename: str):
    assert _is_generated(filename) is False


# ---------------------------------------------------------------------------
# _chunk_patch — invariants
# ---------------------------------------------------------------------------


@given(
    filename=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="./_ -")),
    lines=st.lists(st.text(max_size=100, alphabet=st.characters(blacklist_characters="\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029")), min_size=0, max_size=2000),
)
@settings(max_examples=50)
def test_chunk_patch_total_lines_preserved(filename: str, lines: list):
    patch = "\n".join(f"+{line}" for line in lines)
    chunks = _chunk_patch(filename, patch)

    if not lines:
        # Empty patch should produce one chunk with no lines or no chunks
        total = sum(len(c.patch_lines) for c in chunks)
        assert total == 0 or (len(chunks) == 1 and chunks[0].patch_lines == [""])
    else:
        total = sum(len(c.patch_lines) for c in chunks)
        assert total == len(lines)


@given(
    filename=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="./_ -")),
    lines=st.lists(st.just("+x"), min_size=1, max_size=2000),
)
@settings(max_examples=50)
def test_chunk_patch_max_chunk_size_is_500(filename: str, lines: list):
    patch = "\n".join(lines)
    chunks = _chunk_patch(filename, patch)
    for chunk in chunks:
        assert len(chunk.patch_lines) <= 500


@given(
    filename=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="./_ -")),
    lines=st.lists(st.just("+x"), min_size=1, max_size=2000),
)
@settings(max_examples=50)
def test_chunk_patch_filename_preserved(filename: str, lines: list):
    patch = "\n".join(lines)
    chunks = _chunk_patch(filename, patch)
    for chunk in chunks:
        assert chunk.filename == filename


@given(
    filename=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll"), whitelist_characters="./_ -")),
)
@settings(max_examples=30)
def test_chunk_patch_single_line_gives_one_chunk(filename: str):
    chunks = _chunk_patch(filename, "+single line")
    assert len(chunks) == 1
    assert chunks[0].filename == filename
