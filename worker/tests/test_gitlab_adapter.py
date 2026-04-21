import pytest

from app.adapters.gitlab import _gitlab_base, normalize_mr

MR_PAYLOAD = {
    "object_kind": "merge_request",
    "object_attributes": {
        "iid": 42,
        "action": "open",
        "title": "feat: add GitLab adapter",
        "description": "Implements the adapter",
        "target_branch": "main",
        "diff_head_sha": "abc123",
    },
    "project": {
        "id": 1,
        "path_with_namespace": "group/my-repo",
    },
}

MR_PAYLOAD_LAST_COMMIT = {
    "object_kind": "merge_request",
    "object_attributes": {
        "iid": 7,
        "action": "update",
        "title": "fix: something",
        "description": "",
        "target_branch": "dev",
        "last_commit": {"id": "deadbeef"},
    },
    "project": {
        "id": 2,
        "path_with_namespace": "org/repo",
    },
}


def test_normalize_mr_basic_fields():
    event = normalize_mr("delivery-1", MR_PAYLOAD)
    assert event.platform == "gitlab"
    assert event.event_type == "merge_request"
    assert event.delivery_id == "delivery-1"
    assert event.repo == "group/my-repo"
    assert event.pr_number == 42
    assert event.action == "open"
    assert event.head_sha == "abc123"
    assert event.base_branch == "main"
    assert event.title == "feat: add GitLab adapter"
    assert event.description == "Implements the adapter"


def test_normalize_mr_diff_url_uses_encoded_path():
    event = normalize_mr("d1", MR_PAYLOAD)
    assert "group%2Fmy-repo" in event.diff_url
    assert "/merge_requests/42/changes" in event.diff_url


def test_normalize_mr_diff_url_uses_gitlab_base(monkeypatch):
    monkeypatch.setenv("GITLAB_BASE_URL", "https://gitlab.example.com")
    event = normalize_mr("d1", MR_PAYLOAD)
    assert event.diff_url.startswith("https://gitlab.example.com/api/v4")


def test_normalize_mr_head_sha_fallback_to_last_commit():
    event = normalize_mr("d2", MR_PAYLOAD_LAST_COMMIT)
    assert event.head_sha == "deadbeef"
    assert event.pr_number == 7
    assert event.action == "update"


def test_normalize_mr_base_sha_is_empty():
    event = normalize_mr("d1", MR_PAYLOAD)
    assert event.base_sha == ""


def test_gitlab_base_default():
    import os
    os.environ.pop("GITLAB_BASE_URL", None)
    assert _gitlab_base() == "https://gitlab.com"


def test_gitlab_base_custom(monkeypatch):
    monkeypatch.setenv("GITLAB_BASE_URL", "https://gitlab.corp.com/")
    assert _gitlab_base() == "https://gitlab.corp.com"
