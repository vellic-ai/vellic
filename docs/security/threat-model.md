# Vellic Security Threat Model

**Version:** 0.2  
**Date:** 2026-04-21  
**Methodology:** STRIDE

---

## 1. System Overview

Vellic is a SaaS AI code-review tool. It receives webhook events from VCS platforms (GitHub, GitLab, Bitbucket), fetches PR diffs, runs LLM analysis, and posts review comments back to the platform.

### Components

| Component | Purpose | Public-facing |
|-----------|---------|--------------|
| `api` service (port 8000) | Receives VCS webhooks, validates signatures, enqueues jobs | Yes (webhook endpoints) |
| `admin` service (port 8001) | Configuration UI + settings API | Internal / operator only |
| `worker` service | Fetches diffs, calls LLM, posts review comments | No (outbound only) |
| PostgreSQL | Webhook deliveries, job state, pipeline results | No |
| Redis | Arq job queue | No |

### Trust Boundaries

```
[GitHub / GitLab / Bitbucket]
        │  HTTPS webhook POST
        ▼
   ┌─────────────┐
   │  api service │  ← public internet
   └──────┬──────┘
          │ enqueue job (Redis)
          ▼
   ┌─────────────┐
   │   worker    │  ← internal only
   └──────┬──────┘
          │ outbound HTTPS to VCS APIs
          ▼
   [GitHub / GitLab / Bitbucket APIs]
          │
          ▼ post review comments

   ┌──────────────┐
   │  admin UI    │  ← operator/internal only
   └──────────────┘
```

---

## 2. Assets

| Asset | Sensitivity | Notes |
|-------|-------------|-------|
| GitHub App private key | Critical | Used to generate installation tokens |
| GitLab access token | Critical | Full API access to configured repos |
| Bitbucket app password | Critical | PR read + comment write |
| LLM API key | High | Paid service; abuse costs money |
| Webhook secrets (HMAC) | High | Controls who can trigger jobs |
| Fernet encryption key (`FERNET_KEY`) | Critical | Decrypts all stored secrets |
| PR diffs and code content | Medium | Potentially proprietary source code |
| Review comments | Low | Derived from diffs, sent to VCS |
| Admin session cookie | High | Full admin UI access |

---

## 3. Threats (STRIDE)

### 3.1 Spoofing

| ID | Threat | Component | Mitigation |
|----|--------|-----------|------------|
| S-01 | Attacker sends fake GitHub webhook (no HMAC) | `api/webhook/github` | HMAC-SHA256 via `X-Hub-Signature-256`; missing/wrong sig → 401 |
| S-02 | Attacker sends fake GitLab webhook | `api/webhook/gitlab` | `X-Gitlab-Token` plain secret via `hmac.compare_digest`; missing/wrong → 401 |
| S-03 | Attacker sends fake Bitbucket webhook | `api/webhook/bitbucket` | `X-Hub-Signature` HMAC-SHA256; missing/wrong → 401 |
| S-04 | Attacker replays a valid webhook delivery | All webhook endpoints | `ON CONFLICT (delivery_id) DO NOTHING` idempotency; duplicates → 200 no-op |
| S-05 | Session fixation / cookie theft on admin UI | `admin` service | `HttpOnly` session cookie; bcrypt password storage |

**Residual risk:** GitLab token comparison is constant-time but token is transmitted in plaintext header (not HMAC). This is GitLab's spec; mitigate by enforcing HTTPS at the ingress layer.

### 3.2 Tampering

| ID | Threat | Component | Mitigation |
|----|--------|-----------|------------|
| T-01 | Attacker modifies webhook payload in transit | All webhook endpoints | TLS at ingress; HMAC covers full body |
| T-02 | Attacker replaces diff_url in DB after insertion | worker / PostgreSQL | DB write is idempotent on delivery_id; no update path for payloads |
| T-03 | Malicious PR diff content to poison LLM prompt | worker pipeline | Diff content is passed as data, not instructions; LLM system prompt is hardcoded |

### 3.3 Repudiation

| ID | Threat | Component | Mitigation |
|----|--------|-----------|------------|
| R-01 | No audit trail for admin config changes | `admin` service | Structured logging on all PUT endpoints (`settings upserted`) |
| R-02 | Webhook deliveries not linked to IP | `api` service | `received_at` timestamp stored; add `source_ip` column in future migration |

**Gap:** Admin config changes are logged but not stored in an immutable audit table. Tracked for v0.3.

### 3.4 Information Disclosure

| ID | Threat | Component | Mitigation |
|----|--------|-----------|------------|
| I-01 | Secrets logged in plaintext | All services | Secrets encrypted before DB storage; `mask()` on API responses |
| I-02 | LLM API key leaked via error response | worker | Exception handlers catch and re-raise without including key values |
| I-03 | PR diff content sent to untrusted LLM endpoint | worker | LLM base_url configured by operator; no third-party relay |
| I-04 | Stack traces exposed via 500 responses | `api` / `admin` | FastAPI default — returns `{"detail": "Internal Server Error"}` without trace |
| I-05 | Fernet key rotation compromises past data | DB / admin | Fernet is authenticated encryption; key rotation requires re-encrypt migration |

### 3.5 Denial of Service

| ID | Threat | Component | Mitigation |
|----|--------|-----------|------------|
| D-01 | Flood of webhook requests exhausts worker queue | `api/webhook/*` | Per-IP sliding-window rate limiter (default 60 req/min, configurable via `RATE_LIMIT_WEBHOOK`) |
| D-02 | Huge PR diff exhausts worker memory | worker / diff_fetcher | `_MAX_LINES_PER_CHUNK = 500`; chunked processing |
| D-03 | Slow outbound VCS API stalls worker | worker / diff_fetcher | `httpx.AsyncClient(timeout=30.0)` hard limit |
| D-04 | Redis queue grows unbounded | worker / arq | 3-attempt retry with DLQ; `pipeline_failures` table for dead letters |

### 3.6 Elevation of Privilege

| ID | Threat | Component | Mitigation |
|----|--------|-----------|------------|
| E-01 | Webhook payload controls what URL the worker fetches (SSRF) | worker / diff_fetcher | `validate_outbound_url()` checks hostname allowlist + pre-flight DNS IP check against private ranges |
| E-02 | Admin UI accessible without auth | `admin` service | `AdminAuthMiddleware` on all `/admin/*` routes |
| E-03 | Operator sets `GITLAB_BASE_URL` to internal service | admin / settings_router | Env var control is operator responsibility; document that this must point to the real GitLab |

---

## 4. Attack Vectors Summary

### High Priority (must block before GA)

| Vector | Status |
|--------|--------|
| Unsigned webhook accepted | Mitigated — 401 on all three adapters |
| SSRF via diff_url | Mitigated — allowlist + IP pre-flight check |
| Rate-limiting bypass via webhook flood | Mitigated — per-IP sliding window |
| Secrets stored in plaintext | Mitigated — Fernet AES-128 |

### Medium Priority (track for v0.3)

| Vector | Status |
|--------|--------|
| Admin config tampering audit trail | Gap — logs only, no immutable audit table |
| Session fixation on admin UI | Partial — `HttpOnly` cookie; no `SameSite=Strict` enforcement verified |
| LLM prompt injection via diff content | Accepted risk — diff is data, not instruction |

### Low Priority

| Vector | Status |
|--------|--------|
| DNS rebinding on VCS API hosts | Mitigated — pre-flight DNS IP check |
| Replay of valid webhook | Mitigated — idempotency key in DB |

---

## 5. Security Controls Inventory

| Control | Implementation |
|---------|---------------|
| Webhook signature verification | `api/app/webhook.py` — HMAC-SHA256 (GitHub, Bitbucket), token (GitLab) |
| Rate limiting | `api/app/rate_limit.py` — sliding window, configurable via env |
| SSRF protection | `worker/app/security/ssrf.py` — allowlist + DNS pre-flight |
| Secret encryption | `admin/app/crypto.py` — Fernet |
| Admin authentication | `admin/app/auth_router.py` — bcrypt + session cookie |
| Input validation | Pydantic models on all admin API inputs; webhook URL validated |
| Idempotency | `ON CONFLICT (delivery_id) DO NOTHING` |
| TLS | Enforced at ingress (Kubernetes / reverse proxy) — not in app |
| Dependency scanning | TODO — add Dependabot or `pip-audit` to CI |

---

## 6. Out of Scope (v0.2)

- Multi-tenant isolation (single-org deployment)
- Penetration testing (planned for v1.0)
- SOC 2 / ISO 27001 compliance
- End-to-end encryption of PR diff content at rest
