import pytest

from app.adapters.bitbucket import normalize_pr
from app.pipeline.diff_fetcher import _parse_unified_diff


# ---------------------------------------------------------------------------
# normalize_pr
# ---------------------------------------------------------------------------

_FULL_PAYLOAD = {
    "pullrequest": {
        "id": 7,
        "title": "Add feature",
        "description": "Some work",
        "source": {
            "commit": {"hash": "aabbccdd"},
            "branch": {"name": "feat/work"},
        },
        "destination": {
            "commit": {"hash": "11223344"},
            "branch": {"name": "main"},
        },
        "links": {
            "diff": {"href": "https://api.bitbucket.org/2.0/repositories/org/repo/pullrequests/7/diff"},
        },
    },
    "repository": {"full_name": "org/repo"},
    "event": "pullrequest:created",
}


def test_normalize_pr_basic():
    event = normalize_pr("del-1", _FULL_PAYLOAD)
    assert event.platform == "bitbucket"
    assert event.repo == "org/repo"
    assert event.pr_number == 7
    assert event.head_sha == "aabbccdd"
    assert event.base_sha == "11223344"
    assert event.base_branch == "main"
    assert event.title == "Add feature"
    assert event.description == "Some work"
    assert event.delivery_id == "del-1"
    assert "pullrequests/7/diff" in event.diff_url


def test_normalize_pr_fallback_diff_url():
    payload = {
        **_FULL_PAYLOAD,
        "pullrequest": {**_FULL_PAYLOAD["pullrequest"], "links": {}},
    }
    event = normalize_pr("del-2", payload)
    assert event.diff_url == (
        "https://api.bitbucket.org/2.0/repositories/org/repo/pullrequests/7/diff"
    )


def test_normalize_pr_missing_diff_link_key():
    payload = {
        **_FULL_PAYLOAD,
        "pullrequest": {**_FULL_PAYLOAD["pullrequest"], "links": {"diff": {}}},
    }
    event = normalize_pr("del-3", payload)
    assert "pullrequests/7/diff" in event.diff_url


def test_normalize_pr_null_destination_branch_defaults_to_main():
    payload = {
        **_FULL_PAYLOAD,
        "pullrequest": {
            **_FULL_PAYLOAD["pullrequest"],
            "destination": {"commit": {"hash": "abc"}, "branch": None},
        },
    }
    event = normalize_pr("del-4", payload)
    assert event.base_branch == "main"


def test_normalize_pr_null_shas_fallback_to_empty():
    payload = {
        **_FULL_PAYLOAD,
        "pullrequest": {
            **_FULL_PAYLOAD["pullrequest"],
            "source": {},
            "destination": {},
        },
    }
    event = normalize_pr("del-5", payload)
    assert event.head_sha == ""
    assert event.base_sha == ""


def test_normalize_pr_action_from_event_key():
    event = normalize_pr("del-6", _FULL_PAYLOAD)
    assert event.action == "pullrequest:created"


# ---------------------------------------------------------------------------
# _parse_unified_diff
# ---------------------------------------------------------------------------

_UNIFIED_DIFF = """\
diff --git a/worker/app/foo.py b/worker/app/foo.py
index abc..def 100644
--- a/worker/app/foo.py
+++ b/worker/app/foo.py
@@ -1,3 +1,4 @@
 import os
+import sys

 def main():
diff --git a/worker/app/bar.py b/worker/app/bar.py
new file mode 100644
--- /dev/null
+++ b/worker/app/bar.py
@@ -0,0 +1,2 @@
+def helper():
+    pass
"""


def test_parse_unified_diff_extracts_two_files():
    pairs = _parse_unified_diff(_UNIFIED_DIFF)
    filenames = [f for f, _ in pairs]
    assert "worker/app/foo.py" in filenames
    assert "worker/app/bar.py" in filenames


def test_parse_unified_diff_preserves_patch_lines():
    pairs = dict(_parse_unified_diff(_UNIFIED_DIFF))
    assert "+import sys" in pairs["worker/app/foo.py"]
    assert "+def helper():" in pairs["worker/app/bar.py"]


def test_parse_unified_diff_empty_input():
    assert _parse_unified_diff("") == []


def test_parse_unified_diff_single_file():
    diff = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1,2 @@
 x = 1
+y = 2
"""
    pairs = _parse_unified_diff(diff)
    assert len(pairs) == 1
    assert pairs[0][0] == "app.py"
    assert "+y = 2" in pairs[0][1]
