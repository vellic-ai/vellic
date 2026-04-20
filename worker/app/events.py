from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class WebhookEvent(Protocol):
    platform: str   # "github" | "gitlab"
    event_type: str
    delivery_id: str


@dataclass
class PREvent:
    platform: str
    event_type: str
    delivery_id: str
    repo: str
    pr_number: int
    action: str       # "opened" | "synchronize" | "reopened"
    diff_url: str     # platform files API URL; fetcher uses this directly
    base_sha: str
    head_sha: str
    base_branch: str
    title: str
    description: str
