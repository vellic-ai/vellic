from .models import PRContext


def gather_context(payload: dict) -> PRContext:
    """Extract PR context from a GitHub pull_request webhook payload."""
    pr = payload["pull_request"]
    return PRContext(
        repo=payload["repository"]["full_name"],
        pr_number=pr["number"],
        commit_sha=pr["head"]["sha"],
        title=pr.get("title") or "",
        body=pr.get("body") or "",
        base_branch=pr["base"]["ref"],
    )
