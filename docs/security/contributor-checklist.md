# Security Checklist for Contributors

Use this checklist before opening a PR that touches any of the following areas.
It is not exhaustive — when in doubt, ask the Security Engineer.

---

## New Webhook Endpoint

- [ ] Signature verification implemented before any business logic
  - GitHub: `X-Hub-Signature-256` HMAC-SHA256 via `hmac.compare_digest()`
  - GitLab: `X-Gitlab-Token` plain-secret constant-time comparison
  - Bitbucket: `X-Hub-Signature` HMAC-SHA256
- [ ] Secret read from environment variable, not hardcoded
- [ ] Returns **401** (not 400 or 403) on missing or invalid signature
- [ ] `delivery_id` stored with `ON CONFLICT DO NOTHING` for idempotency
- [ ] Rate-limiting applied (`check_rate_limit` in `api/app/rate_limit.py`)
- [ ] Event type filtered before payload is parsed
- [ ] Payload passed through Pydantic validation before DB write

## Outbound HTTP Requests

- [ ] URL validated with `validate_outbound_url()` from `worker/app/security/ssrf.py`
  - URL must be `http` or `https`
  - Hostname must appear in `ALLOWED_DIFF_HOSTS` or the default allowlist
  - Pre-flight DNS check passes (no private/loopback/link-local IPs)
- [ ] `httpx.AsyncClient(timeout=N)` set — never use an unbounded client
- [ ] Auth token read from env var or decrypted from DB, never from webhook payload

## Secrets and Configuration

- [ ] New credentials encrypted with `encrypt()` from `admin/app/crypto.py` before DB storage
- [ ] API responses mask secrets with `mask()` — never return plaintext credentials
- [ ] New env vars documented in `docs/configuration.md`
- [ ] Secrets never appear in log output (no `logger.info("token=%s", token)`)
- [ ] Fernet key (`FERNET_KEY`) rotation considered if new secret type is added

## Input Validation

- [ ] All API request bodies use Pydantic models with explicit field types
- [ ] String fields with constrained values validated against an allowlist (e.g., `VALID_PROVIDERS`)
- [ ] URL fields validated for scheme and hostname (use `field_validator`)
- [ ] Integer fields that control resource allocation have upper bounds
- [ ] No direct interpolation of user-supplied strings into SQL (use asyncpg `$N` params)

## Authentication and Authorization

- [ ] New admin routes are covered by `AdminAuthMiddleware`
- [ ] Any bypass paths explicitly allowlisted in `AdminAuthMiddleware._SKIP_PATHS`
- [ ] New public routes (non-admin, non-webhook) evaluated for whether they require auth

## Dependencies

- [ ] New Python packages checked against known CVEs via `pip-audit` before adding
- [ ] Minimum version pinned in `pyproject.toml`; no `*` or `latest` version specs
- [ ] No package that bundles a bundled CA store unless pinned to a recent release

## Logging and Observability

- [ ] No secrets, tokens, PII, or raw diffs in log lines
- [ ] Errors logged at `logger.warning` or `logger.error` with context (not silently swallowed)
- [ ] New failure modes result in an entry in `pipeline_failures` or equivalent audit table

## Tests

- [ ] Signature validation tested: valid sig → 2xx, wrong sig → 401, missing sig → 401, no env secret → 401
- [ ] Rate limit tested: N+1 request to the same endpoint returns 429
- [ ] SSRF protection tested: private IP and non-allowlisted host both raise `ValueError`
- [ ] Idempotency tested: duplicate delivery_id returns 200 without re-enqueuing

---

## Quick Reference: Rejection Status Codes

| Condition | HTTP Status |
|-----------|-------------|
| Missing or invalid signature | 401 |
| Rate limit exceeded | 429 |
| Malformed request (missing required header) | 400 |
| Unsupported event type | 200 (ignored) |
| Duplicate delivery | 200 (duplicate) |
| Auth required but not provided (admin) | 401 |
