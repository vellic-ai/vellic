from ..events import PREvent

_BITBUCKET_API_BASE = "https://api.bitbucket.org/2.0"


def normalize_pr(delivery_id: str, payload: dict) -> PREvent:
    """Map a Bitbucket pullrequest webhook payload to a platform-agnostic PREvent."""
    pr = payload["pullrequest"]
    repo = payload["repository"]["full_name"]
    pr_number = int(pr["id"])
    source = pr.get("source") or {}
    destination = pr.get("destination") or {}
    links = pr.get("links") or {}
    diff_href = (links.get("diff") or {}).get("href", "")
    if not diff_href:
        owner, _, slug = repo.partition("/")
        diff_href = (
            f"{_BITBUCKET_API_BASE}/repositories/{owner}/{slug}/pullrequests/{pr_number}/diff"
        )
    return PREvent(
        platform="bitbucket",
        event_type="pullrequest",
        delivery_id=delivery_id,
        repo=repo,
        pr_number=pr_number,
        action=payload.get("event", ""),
        diff_url=diff_href,
        base_sha=(destination.get("commit") or {}).get("hash", ""),
        head_sha=(source.get("commit") or {}).get("hash", ""),
        base_branch=(destination.get("branch") or {}).get("name", "main"),
        title=pr.get("title") or "",
        description=pr.get("description") or "",
    )
