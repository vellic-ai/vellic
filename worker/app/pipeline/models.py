from dataclasses import dataclass, field


@dataclass
class PRContext:
    repo: str          # "owner/repo"
    pr_number: int
    commit_sha: str
    title: str
    body: str
    base_branch: str
    platform: str = "github"


@dataclass
class DiffChunk:
    filename: str
    patch_lines: list[str]

    @property
    def patch(self) -> str:
        return "\n".join(self.patch_lines)


@dataclass
class ReviewComment:
    file: str
    line: int
    body: str
    confidence: float
    rationale: str


@dataclass
class AnalysisResult:
    comments: list[ReviewComment] = field(default_factory=list)
    summary: str = ""
    generic_ratio: float = 0.0
