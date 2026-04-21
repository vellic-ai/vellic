import asyncio
import hashlib
import hmac
import logging
import secrets
import time
from base64 import b64decode

import asyncpg
import bcrypt
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from . import db

logger = logging.getLogger("admin.auth")

router = APIRouter()

COOKIE_NAME = "vellic_session"
SESSION_TTL = 86400  # 24 hours in seconds

# Paths under /admin/* that bypass auth middleware
UNAUTHENTICATED_PATHS = frozenset({
    "/admin/auth/status",
    "/admin/auth/setup",
    "/admin/auth/login",
})


# ── DB helpers ────────────────────────────────────────────────────────────────


def _raise_db_not_ready() -> None:
    raise HTTPException(
        status_code=503,
        detail="Database migrations have not run yet. Retry shortly.",
    )


async def _get_config(conn, key: str) -> str | None:
    try:
        row = await conn.fetchrow("SELECT value FROM admin_config WHERE key = $1", key)
    except asyncpg.exceptions.UndefinedTableError:
        _raise_db_not_ready()
    return row["value"] if row else None


async def _set_config(conn, key: str, value: str) -> None:
    try:
        await conn.execute(
            """
            INSERT INTO admin_config (key, value, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
            """,
            key,
            value,
        )
    except asyncpg.exceptions.UndefinedTableError:
        _raise_db_not_ready()


async def _require_session_secret(conn) -> str:
    secret = await _get_config(conn, "session_secret")
    if secret is None:
        secret = secrets.token_hex(32)
        await _set_config(conn, "session_secret", secret)
        logger.info("generated new session_secret")
    return secret


# ── Cookie signing ────────────────────────────────────────────────────────────


def _sign_cookie(secret: str) -> str:
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), f"admin:{ts}".encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def _verify_cookie(secret: str, value: str) -> bool:
    try:
        ts_str, sig = value.split(".", 1)
        if time.time() - int(ts_str) > SESSION_TTL:
            return False
        expected = hmac.new(secret.encode(), f"admin:{ts_str}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False


def _set_session_cookie(response: Response, secret: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        _sign_cookie(secret),
        max_age=SESSION_TTL,
        httponly=True,
        samesite="lax",
    )


# ── Auth check (used by middleware and status endpoint) ───────────────────────


async def check_authenticated(request: Request) -> bool:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        secret = await _require_session_secret(conn)
        password_hash = await _get_config(conn, "admin_password_hash")

    token = request.cookies.get(COOKIE_NAME)
    if token and _verify_cookie(secret, token):
        return True

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic ") and password_hash:
        try:
            decoded = b64decode(auth[6:]).decode()
            _, _, password = decoded.partition(":")
            if bcrypt.checkpw(password.encode(), password_hash.encode()):
                return True
        except Exception:
            pass

    return False


# ── Middleware ────────────────────────────────────────────────────────────────


class AdminAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/admin/") or path in UNAUTHENTICATED_PATHS:
            return await call_next(request)
        try:
            authed = await check_authenticated(request)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if not authed:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/admin/auth/status")
async def auth_status(request: Request) -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        secret = await _require_session_secret(conn)
        password_hash = await _get_config(conn, "admin_password_hash")

    token = request.cookies.get(COOKIE_NAME)
    authenticated = bool(token and _verify_cookie(secret, token))
    return {"setup_required": password_hash is None, "authenticated": authenticated}


class _SetupBody(BaseModel):
    password: str


@router.put("/admin/auth/setup", status_code=204)
async def auth_setup(body: _SetupBody) -> Response:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        existing = await _get_config(conn, "admin_password_hash")
        if existing is not None:
            return JSONResponse({"detail": "Password already set"}, status_code=409)
        secret = await _require_session_secret(conn)
        hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        await _set_config(conn, "admin_password_hash", hashed)

    resp = Response(status_code=204)
    _set_session_cookie(resp, secret)
    return resp


class _LoginBody(BaseModel):
    password: str


@router.post("/admin/auth/login")
async def auth_login(body: _LoginBody) -> Response:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        password_hash = await _get_config(conn, "admin_password_hash")
        secret = await _require_session_secret(conn)

    ok = bool(
        password_hash and bcrypt.checkpw(body.password.encode(), password_hash.encode())
    )
    if not ok:
        await asyncio.sleep(1)  # brute-force mitigation
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    resp = JSONResponse({"authenticated": True})
    _set_session_cookie(resp, secret)
    return resp


@router.post("/admin/auth/logout", status_code=204)
async def auth_logout() -> Response:
    resp = Response(status_code=204)
    resp.delete_cookie(COOKIE_NAME)
    return resp


class _ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


@router.post("/admin/auth/change-password", status_code=204)
async def auth_change_password(body: _ChangePasswordBody) -> Response:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        password_hash = await _get_config(conn, "admin_password_hash")
        if not password_hash or not bcrypt.checkpw(
            body.current_password.encode(), password_hash.encode()
        ):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        new_hashed = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
        await _set_config(conn, "admin_password_hash", new_hashed)

    return Response(status_code=204)
