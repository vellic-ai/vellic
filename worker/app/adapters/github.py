from ..events import PREvent

_GITHUB_API_BASE = "https://api.github.com"


def normalize_pr(delivery_id: str, payload: dict) -> PREvent:
    """Map a GitHub pull_request webhook payload to a platform-agnostic PREvent."""
    pr = payload["pull_request"]
    repo = payload["repository"]["full_name"]
    pr_number = int(pr["number"])
    return PREvent(
        platform="github",
        event_type="pull_request",
        delivery_id=delivery_id,
        repo=repo,
        pr_number=pr_number,
        action=payload.get("action", ""),
        diff_url=f"{_GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}/files",
        base_sha=pr["base"]["sha"],
        head_sha=pr["head"]["sha"],
        base_branch=pr["base"]["ref"],
        title=pr.get("title") or "",
        description=pr.get("body") or "",
        labels=[lbl["name"] for lbl in pr.get("labels", []) if isinstance(lbl, dict)],
    )
