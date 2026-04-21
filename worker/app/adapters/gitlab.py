import os
from urllib.parse import quote

from ..events import PREvent


def _gitlab_base() -> str:
    return os.getenv("GITLAB_BASE_URL", "https://gitlab.com").rstrip("/")


def normalize_mr(delivery_id: str, payload: dict) -> PREvent:
    """Map a GitLab merge_request webhook payload to a platform-agnostic PREvent."""
    attrs = payload["object_attributes"]
    project = payload["project"]
    repo = project["path_with_namespace"]
    mr_iid = int(attrs["iid"])
    encoded_path = quote(repo, safe="")
    base_url = _gitlab_base()
    diff_url = f"{base_url}/api/v4/projects/{encoded_path}/merge_requests/{mr_iid}/changes"
    head_sha = attrs.get("diff_head_sha") or (attrs.get("last_commit") or {}).get("id", "")
    return PREvent(
        platform="gitlab",
        event_type="merge_request",
        delivery_id=delivery_id,
        repo=repo,
        pr_number=mr_iid,
        action=attrs.get("action", ""),
        diff_url=diff_url,
        base_sha="",
        head_sha=head_sha,
        base_branch=attrs.get("target_branch", ""),
        title=attrs.get("title") or "",
        description=attrs.get("description") or "",
    )
