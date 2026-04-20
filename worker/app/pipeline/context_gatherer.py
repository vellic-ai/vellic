from ..events import PREvent
from .models import PRContext


def gather_context(event: PREvent) -> PRContext:
    return PRContext(
        repo=event.repo,
        pr_number=event.pr_number,
        commit_sha=event.head_sha,
        title=event.title,
        body=event.description,
        base_branch=event.base_branch,
    )
