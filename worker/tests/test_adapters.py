"""Fixture-based integration tests for all three VCS adapter normalizers.

Each test drives a realistic webhook payload through the adapter and asserts
that the resulting PREvent is correctly populated — covering the full
payload → PREvent normalisation path without any network I/O.
"""

from app.adapters.bitbucket import normalize_pr as bb_normalize
from app.adapters.github import normalize_pr as gh_normalize
from app.adapters.gitlab import normalize_mr as gl_normalize
from app.events import PREvent

# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

_GH_PR_OPENED = {
    "action": "opened",
    "repository": {"full_name": "acme/backend"},
    "pull_request": {
        "number": 7,
        "head": {"sha": "headsha"},
        "base": {"sha": "basesha", "ref": "main"},
        "title": "feat: add caching",
        "body": "Caches DB hits.",
        "diff_url": "https://github.com/acme/backend/pull/7.diff",
    },
}

_GH_PR_NULL_BODY = {
    **_GH_PR_OPENED,
    "pull_request": {**_GH_PR_OPENED["pull_request"], "body": None},
}


class TestGitHubAdapter:
    def test_normalize_pr_full_fields(self):
        event = gh_normalize("gh-1", _GH_PR_OPENED)
        assert isinstance(event, PREvent)
        assert event.platform == "github"
        assert event.delivery_id == "gh-1"
        assert event.repo == "acme/backend"
        assert event.pr_number == 7
        assert event.head_sha == "headsha"
        assert event.base_sha == "basesha"
        assert event.base_branch == "main"
        assert event.title == "feat: add caching"
        assert event.description == "Caches DB hits."
        assert event.diff_url == "https://api.github.com/repos/acme/backend/pulls/7/files"
        assert event.action == "opened"

    def test_normalize_pr_null_body_becomes_empty_string(self):
        event = gh_normalize("gh-2", _GH_PR_NULL_BODY)
        assert event.description == ""

    def test_diff_url_uses_github_api(self):
        event = gh_normalize("gh-3", _GH_PR_OPENED)
        assert event.diff_url.startswith("https://api.github.com/repos/")
        assert "/pulls/7/files" in event.diff_url


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------

_GL_MR_OPENED = {
    "object_kind": "merge_request",
    "project": {"id": 123, "path_with_namespace": "acme/backend"},
    "object_attributes": {
        "iid": 42,
        "action": "open",
        "title": "feat: new endpoint",
        "description": "Adds /v2/search.",
        "target_branch": "main",
        "diff_head_sha": "head222",
        "last_commit": {"id": "head222"},
    },
}

_GL_MR_NO_SHA = {
    **_GL_MR_OPENED,
    "object_attributes": {
        **_GL_MR_OPENED["object_attributes"],
        "diff_head_sha": None,
        "last_commit": None,
    },
}

_GL_MR_NULL_DESCRIPTION = {
    **_GL_MR_OPENED,
    "object_attributes": {**_GL_MR_OPENED["object_attributes"], "description": None},
}


class TestGitLabAdapter:
    def test_normalize_mr_full_fields(self):
        event = gl_normalize("gl-1", _GL_MR_OPENED)
        assert isinstance(event, PREvent)
        assert event.platform == "gitlab"
        assert event.delivery_id == "gl-1"
        assert event.repo == "acme/backend"
        assert event.pr_number == 42
        assert event.action == "open"
        assert event.title == "feat: new endpoint"
        assert event.description == "Adds /v2/search."
        assert event.base_branch == "main"
        assert event.head_sha == "head222"
        assert "merge_requests/42/changes" in event.diff_url
        assert "/api/v4/projects/" in event.diff_url

    def test_normalize_mr_missing_sha_fields(self):
        event = gl_normalize("gl-2", _GL_MR_NO_SHA)
        assert event.head_sha == ""

    def test_normalize_mr_null_description(self):
        event = gl_normalize("gl-3", _GL_MR_NULL_DESCRIPTION)
        assert event.description == ""

    def test_diff_url_encodes_repo_path(self):
        event = gl_normalize("gl-4", _GL_MR_OPENED)
        # acme/backend → acme%2Fbackend
        assert "acme%2Fbackend" in event.diff_url


# ---------------------------------------------------------------------------
# Bitbucket
# ---------------------------------------------------------------------------

_BB_PR_CREATED = {
    "event": "pullrequest:created",
    "repository": {"full_name": "acme/backend"},
    "pullrequest": {
        "id": 99,
        "title": "feat: payments",
        "description": "Stripe integration.",
        "source": {
            "commit": {"hash": "srcsha"},
            "branch": {"name": "feat/payments"},
        },
        "destination": {
            "commit": {"hash": "dstsha"},
            "branch": {"name": "main"},
        },
        "links": {
            "diff": {
                "href": "https://api.bitbucket.org/2.0/repositories/acme/backend/pullrequests/99/diff"
            }
        },
    },
}

_BB_PR_NO_DIFF_LINK = {
    **_BB_PR_CREATED,
    "pullrequest": {**_BB_PR_CREATED["pullrequest"], "links": {}},
}

_BB_PR_NULL_DESCRIPTION = {
    **_BB_PR_CREATED,
    "pullrequest": {**_BB_PR_CREATED["pullrequest"], "description": None},
}


class TestBitbucketAdapter:
    def test_normalize_pr_full_fields(self):
        event = bb_normalize("bb-1", _BB_PR_CREATED)
        assert isinstance(event, PREvent)
        assert event.platform == "bitbucket"
        assert event.delivery_id == "bb-1"
        assert event.repo == "acme/backend"
        assert event.pr_number == 99
        assert event.action == "pullrequest:created"
        assert event.title == "feat: payments"
        assert event.description == "Stripe integration."
        assert event.base_branch == "main"
        assert event.head_sha == "srcsha"
        assert event.base_sha == "dstsha"
        assert "pullrequests/99/diff" in event.diff_url

    def test_normalize_pr_falls_back_diff_url_when_no_link(self):
        event = bb_normalize("bb-2", _BB_PR_NO_DIFF_LINK)
        assert "/pullrequests/99/diff" in event.diff_url
        assert "api.bitbucket.org" in event.diff_url

    def test_normalize_pr_null_description(self):
        event = bb_normalize("bb-3", _BB_PR_NULL_DESCRIPTION)
        assert event.description == ""

    def test_pr_number_is_integer(self):
        event = bb_normalize("bb-4", _BB_PR_CREATED)
        assert isinstance(event.pr_number, int)
        assert event.pr_number == 99
