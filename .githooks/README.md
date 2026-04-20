# Git hooks

Tracked hooks for this repo. Activate them once after clone:

```
make hooks
```

That runs `git config core.hooksPath .githooks`. Re-run after a fresh clone.

## commit-msg

Rejects commit messages that fingerprint AI-assisted authoring (AI co-author
trailers, "Generated with <tool>" footers, robot emoji). Commits should read
as if written by a human maintainer.
