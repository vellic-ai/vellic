"""
Tests for the feature-flag framework (VEL-89 / VEL-103).

Covers:
  - Resolver priority chain: ENV < YAML < DB < UI (higher index wins)
  - Scope merge policy: global < tenant < repo < user (more specific wins)
  - `inherit` sentinel — falls through to the next-broader scope
  - Snapshot frozen in job-context for reproducibility
  - /api/features endpoint response caching (TTL + invalidation)
  - Audit log writes on every flag mutation

All imports reference the planned module layout:
  worker/app/features/registry.py   — FlagDefinition, CATALOG
  worker/app/features/resolver.py   — FlagResolver, Scope, Source
  worker/app/features/cache.py      — FeatureCache
  worker/app/features/audit.py      — write_audit_entry, AuditEntry

Tests are intentionally written first (TDD); the implementation is in VEL-96/97/98.
"""

import os
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers shared across test sections
# ---------------------------------------------------------------------------

INHERIT = "inherit"  # sentinel value meaning "fall through to broader scope"


def _fake_env(flags: dict[str, Any]) -> dict[str, str]:
    """Convert flag dict to env-var form: VELLIC_FLAG_<UPPER_NAME>=<value>."""
    return {f"VELLIC_FLAG_{k.upper()}": str(v) for k, v in flags.items()}


def _fake_yaml(flags: dict[str, Any]) -> dict[str, Any]:
    return {"feature_flags": flags}


def _fake_db_row(flag: str, value: Any, scope: str = "global", scope_id: str | None = None):
    return {
        "flag_name": flag,
        "value": value,
        "scope": scope,
        "scope_id": scope_id,
        "updated_by": "admin",
        "updated_at": "2026-04-21T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# 1. Resolver — priority chain (ENV < YAML < DB < UI)
# ---------------------------------------------------------------------------


class TestResolverPriorityChain:
    """ENV is the lowest priority; UI is the highest."""

    def test_env_used_when_no_other_source(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(
            env_flags={"github_adapter": True},
            yaml_flags={},
            db_rows=[],
        )
        assert resolver.resolve("github_adapter") is True

    def test_yaml_overrides_env(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(
            env_flags={"github_adapter": True},
            yaml_flags={"github_adapter": False},
            db_rows=[],
        )
        assert resolver.resolve("github_adapter") is False

    def test_db_overrides_yaml(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(
            env_flags={"github_adapter": False},
            yaml_flags={"github_adapter": False},
            db_rows=[_fake_db_row("github_adapter", True, scope="global")],
        )
        assert resolver.resolve("github_adapter") is True

    def test_ui_overrides_db(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(
            env_flags={"gitlab_adapter": True},
            yaml_flags={},
            db_rows=[_fake_db_row("gitlab_adapter", True, scope="global")],
            ui_overrides={"gitlab_adapter": False},
        )
        assert resolver.resolve("gitlab_adapter") is False

    def test_unknown_flag_returns_default(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=[])
        assert resolver.resolve("nonexistent_flag", default=False) is False

    def test_unknown_flag_raises_without_default(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=[])
        with pytest.raises(KeyError):
            resolver.resolve("nonexistent_flag")

    def test_all_sources_absent_uses_catalog_default(self):
        from app.features.registry import CATALOG
        from app.features.resolver import FlagResolver

        flag_name = next(iter(CATALOG))
        catalog_default = CATALOG[flag_name].default
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=[])
        assert resolver.resolve(flag_name) == catalog_default


# ---------------------------------------------------------------------------
# 2. Resolver — scope merge (global < tenant < repo < user)
# ---------------------------------------------------------------------------


class TestResolverScopeMerge:
    """More-specific scope wins; INHERIT falls through to the next broader scope."""

    def test_global_scope_used_when_no_narrower_scope(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(
            env_flags={},
            yaml_flags={},
            db_rows=[_fake_db_row("security_scan", True, scope="global")],
        )
        result = resolver.resolve("security_scan", scope="global")
        assert result is True

    def test_tenant_overrides_global(self):
        from app.features.resolver import FlagResolver

        rows = [
            _fake_db_row("security_scan", False, scope="global"),
            _fake_db_row("security_scan", True, scope="tenant", scope_id="tenant-abc"),
        ]
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=rows)
        assert resolver.resolve("security_scan", scope="tenant", scope_id="tenant-abc") is True
        assert resolver.resolve("security_scan", scope="global") is False

    def test_repo_overrides_tenant(self):
        from app.features.resolver import FlagResolver

        rows = [
            _fake_db_row("security_scan", False, scope="global"),
            _fake_db_row("security_scan", True, scope="tenant", scope_id="tenant-abc"),
            _fake_db_row("security_scan", False, scope="repo", scope_id="repo-xyz"),
        ]
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=rows)
        assert resolver.resolve("security_scan", scope="repo", scope_id="repo-xyz") is False

    def test_user_overrides_repo(self):
        from app.features.resolver import FlagResolver

        rows = [
            _fake_db_row("security_scan", False, scope="repo", scope_id="repo-xyz"),
            _fake_db_row("security_scan", True, scope="user", scope_id="user-1"),
        ]
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=rows)
        assert resolver.resolve("security_scan", scope="user", scope_id="user-1") is True

    def test_inherit_falls_through_to_parent_scope(self):
        """User row with INHERIT should resolve to repo-level value."""
        from app.features.resolver import FlagResolver

        rows = [
            _fake_db_row("coverage_hints", True, scope="repo", scope_id="repo-xyz"),
            _fake_db_row("coverage_hints", INHERIT, scope="user", scope_id="user-1"),
        ]
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=rows)
        result = resolver.resolve(
            "coverage_hints",
            scope="user",
            scope_id="user-1",
            repo_id="repo-xyz",
        )
        assert result is True

    def test_inherit_chain_falls_through_multiple_levels(self):
        """Inherit at user → inherit at repo → picks up tenant value."""
        from app.features.resolver import FlagResolver

        rows = [
            _fake_db_row("coverage_hints", False, scope="global"),
            _fake_db_row("coverage_hints", True, scope="tenant", scope_id="tenant-abc"),
            _fake_db_row("coverage_hints", INHERIT, scope="repo", scope_id="repo-xyz"),
            _fake_db_row("coverage_hints", INHERIT, scope="user", scope_id="user-1"),
        ]
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=rows)
        result = resolver.resolve(
            "coverage_hints",
            scope="user",
            scope_id="user-1",
            repo_id="repo-xyz",
            tenant_id="tenant-abc",
        )
        assert result is True

    def test_no_scope_context_resolves_global(self):
        from app.features.resolver import FlagResolver

        rows = [
            _fake_db_row("github_adapter", True, scope="global"),
        ]
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=rows)
        assert resolver.resolve("github_adapter") is True

    def test_scope_resolution_does_not_cross_tenants(self):
        """A tenant-A override must not bleed into tenant-B resolution."""
        from app.features.resolver import FlagResolver

        rows = [
            _fake_db_row("github_adapter", False, scope="global"),
            _fake_db_row("github_adapter", True, scope="tenant", scope_id="tenant-A"),
        ]
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=rows)
        assert resolver.resolve("github_adapter", scope="tenant", scope_id="tenant-B") is False


# ---------------------------------------------------------------------------
# 3. Resolver — snapshot (reproducibility)
# ---------------------------------------------------------------------------


class TestResolverSnapshot:
    """resolve_snapshot() returns a frozen dict; mutations don't affect it."""

    def test_snapshot_contains_all_catalog_flags(self):
        from app.features.registry import CATALOG
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=[])
        snapshot = resolver.resolve_snapshot()
        for flag_name in CATALOG:
            assert flag_name in snapshot

    def test_snapshot_is_immutable(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=[])
        snapshot = resolver.resolve_snapshot()
        # Snapshots must not be mutable dicts — they should be frozendict-like or copied
        original_repr = repr(snapshot)
        try:
            snapshot["github_adapter"] = not snapshot.get("github_adapter")
        except (TypeError, AttributeError):
            pass  # frozendict or similar raises — that's the correct behaviour
        # Even if assignment silently fails, external mutations must not propagate
        snapshot2 = resolver.resolve_snapshot()
        assert repr(snapshot2) == original_repr

    def test_snapshot_reflects_ui_overrides(self):
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(
            env_flags={"github_adapter": False},
            yaml_flags={},
            db_rows=[],
            ui_overrides={"github_adapter": True},
        )
        snapshot = resolver.resolve_snapshot()
        assert snapshot["github_adapter"] is True


# ---------------------------------------------------------------------------
# 4. Feature cache
# ---------------------------------------------------------------------------


class TestFeatureCache:
    """FeatureCache wraps the resolver and returns cached snapshots with TTL."""

    def test_cache_returns_same_object_within_ttl(self):
        from app.features.cache import FeatureCache
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={"github_adapter": True}, yaml_flags={}, db_rows=[])
        cache = FeatureCache(resolver=resolver, ttl_seconds=60)

        snap1 = cache.get_snapshot()
        snap2 = cache.get_snapshot()
        assert snap1 is snap2  # same cached object

    def test_cache_refreshes_after_ttl(self):
        from app.features.cache import FeatureCache
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={"github_adapter": True}, yaml_flags={}, db_rows=[])
        cache = FeatureCache(resolver=resolver, ttl_seconds=0)  # TTL=0 always expired

        snap1 = cache.get_snapshot()
        snap2 = cache.get_snapshot()
        assert snap1 is not snap2  # should have refreshed

    def test_cache_invalidation_forces_refresh(self):
        from app.features.cache import FeatureCache
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={"github_adapter": True}, yaml_flags={}, db_rows=[])
        cache = FeatureCache(resolver=resolver, ttl_seconds=3600)

        snap1 = cache.get_snapshot()
        cache.invalidate()
        snap2 = cache.get_snapshot()
        assert snap1 is not snap2

    def test_cache_invalidation_on_flag_write(self):
        """Writing a flag override should invalidate the cache automatically."""
        from app.features.cache import FeatureCache
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=[])
        cache = FeatureCache(resolver=resolver, ttl_seconds=3600)

        snap1 = cache.get_snapshot()
        cache.on_flag_written("github_adapter", True, scope="global")
        snap2 = cache.get_snapshot()
        assert snap1 is not snap2

    def test_cache_thread_safety(self):
        """Concurrent reads must not raise; one snapshot per TTL window."""
        import threading

        from app.features.cache import FeatureCache
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(env_flags={"github_adapter": True}, yaml_flags={}, db_rows=[])
        cache = FeatureCache(resolver=resolver, ttl_seconds=3600)
        results = []

        def read():
            results.append(cache.get_snapshot())

        threads = [threading.Thread(target=read) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        # All results should be the same object (cached)
        assert all(r is results[0] for r in results)


# ---------------------------------------------------------------------------
# 5. Audit log
# ---------------------------------------------------------------------------


class TestAuditLog:
    """Every flag mutation must write an entry to feature_flag_audit."""

    @pytest.mark.asyncio
    async def test_audit_entry_written_on_create(self):
        from app.features.audit import write_audit_entry

        conn = AsyncMock()
        conn.execute = AsyncMock()

        await write_audit_entry(
            conn=conn,
            flag_name="github_adapter",
            old_value=None,
            new_value=True,
            scope="global",
            scope_id=None,
            actor="admin-user-1",
        )

        conn.execute.assert_called_once()
        sql, *args = conn.execute.call_args.args
        assert "feature_flag_audit" in sql.lower()

    @pytest.mark.asyncio
    async def test_audit_entry_written_on_update(self):
        from app.features.audit import write_audit_entry

        conn = AsyncMock()
        conn.execute = AsyncMock()

        await write_audit_entry(
            conn=conn,
            flag_name="gitlab_adapter",
            old_value=False,
            new_value=True,
            scope="tenant",
            scope_id="tenant-abc",
            actor="tenant-admin",
        )

        conn.execute.assert_called_once()
        call_args = conn.execute.call_args
        # Values must appear in query args (positional or keyword)
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        flat = " ".join(str(a) for a in all_args)
        assert "gitlab_adapter" in flat
        assert "tenant-abc" in flat
        assert "tenant-admin" in flat

    @pytest.mark.asyncio
    async def test_audit_entry_written_on_delete(self):
        from app.features.audit import write_audit_entry

        conn = AsyncMock()
        conn.execute = AsyncMock()

        await write_audit_entry(
            conn=conn,
            flag_name="security_scan",
            old_value=True,
            new_value=None,  # deletion
            scope="repo",
            scope_id="repo-xyz",
            actor="repo-owner",
        )

        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_records_all_scope_levels(self):
        from app.features.audit import write_audit_entry

        conn = AsyncMock()
        conn.execute = AsyncMock()

        for scope, scope_id in [
            ("global", None),
            ("tenant", "t-1"),
            ("repo", "r-1"),
            ("user", "u-1"),
        ]:
            conn.execute.reset_mock()
            await write_audit_entry(
                conn=conn,
                flag_name="coverage_hints",
                old_value=False,
                new_value=True,
                scope=scope,
                scope_id=scope_id,
                actor="actor",
            )
            conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_entry_includes_timestamp(self):
        from app.features.audit import AuditEntry, write_audit_entry

        conn = AsyncMock()
        conn.execute = AsyncMock()

        before = time.time()
        await write_audit_entry(
            conn=conn,
            flag_name="github_adapter",
            old_value=False,
            new_value=True,
            scope="global",
            scope_id=None,
            actor="system",
        )
        after = time.time()

        call_args = conn.execute.call_args
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        # At least one arg should be a timestamp-like value
        timestamps = [a for a in all_args if isinstance(a, float) and before <= a <= after]
        # Alternatively, the implementation may pass ISO strings; accept both
        iso_like = [a for a in all_args if isinstance(a, str) and "2026" in a]
        assert timestamps or iso_like, "Expected a timestamp in audit INSERT args"


# ---------------------------------------------------------------------------
# 6. Flag catalog / registry
# ---------------------------------------------------------------------------


class TestFlagRegistry:
    """CATALOG must contain all required flags with sane defaults."""

    REQUIRED_FLAGS = [
        "github_adapter",
        "gitlab_adapter",
        "bitbucket_adapter",
        "gitea_adapter",
        "multi_tenant",
        "security_scan",
        "coverage_hints",
        "issue_triage",
        "commit_summary",
        "release_notes",
        "slack_notifier",
        "teams_notifier",
        "metrics_export",
        "tracing_export",
    ]

    def test_catalog_contains_required_flags(self):
        from app.features.registry import CATALOG

        missing = [f for f in self.REQUIRED_FLAGS if f not in CATALOG]
        assert not missing, f"Flags missing from CATALOG: {missing}"

    def test_catalog_flags_have_defaults(self):
        from app.features.registry import CATALOG

        for name, defn in CATALOG.items():
            assert hasattr(defn, "default"), f"Flag {name!r} has no default"
            assert defn.default is not None, f"Flag {name!r} default is None"

    def test_catalog_flags_have_descriptions(self):
        from app.features.registry import CATALOG

        for name, defn in CATALOG.items():
            assert hasattr(defn, "description"), f"Flag {name!r} missing description"
            assert defn.description, f"Flag {name!r} has empty description"

    def test_github_adapter_enabled_by_default(self):
        """GitHub adapter is the primary VCS; must default to enabled."""
        from app.features.registry import CATALOG

        assert CATALOG["github_adapter"].default is True

    def test_all_llm_providers_registered(self):
        from app.features.registry import CATALOG

        llm_flags = [k for k in CATALOG if "llm_provider" in k or k.endswith("_provider")]
        assert llm_flags, "No LLM provider flags found in CATALOG"


# ---------------------------------------------------------------------------
# 7. End-to-end resolver → cache flow
# ---------------------------------------------------------------------------


class TestResolverCacheIntegration:
    """Integration: resolver feeds cache; flag write invalidates & re-resolves."""

    def test_cache_reflects_db_override_after_invalidation(self):
        from app.features.cache import FeatureCache
        from app.features.resolver import FlagResolver

        resolver = FlagResolver(
            env_flags={"github_adapter": True},
            yaml_flags={},
            db_rows=[],
        )
        cache = FeatureCache(resolver=resolver, ttl_seconds=3600)

        snap1 = cache.get_snapshot()
        assert snap1["github_adapter"] is True

        # Simulate a DB write that disables the flag at global scope
        resolver.apply_db_override("github_adapter", False, scope="global")
        cache.on_flag_written("github_adapter", False, scope="global")

        snap2 = cache.get_snapshot()
        assert snap2["github_adapter"] is False

    def test_snapshot_scope_context_respected_in_cache(self):
        from app.features.cache import FeatureCache
        from app.features.resolver import FlagResolver

        rows = [
            _fake_db_row("security_scan", False, scope="global"),
            _fake_db_row("security_scan", True, scope="tenant", scope_id="t-1"),
        ]
        resolver = FlagResolver(env_flags={}, yaml_flags={}, db_rows=rows)
        cache = FeatureCache(resolver=resolver, ttl_seconds=3600)

        global_snap = cache.get_snapshot(scope="global")
        tenant_snap = cache.get_snapshot(scope="tenant", scope_id="t-1")

        assert global_snap["security_scan"] is False
        assert tenant_snap["security_scan"] is True
