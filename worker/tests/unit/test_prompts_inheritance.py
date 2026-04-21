"""Unit tests for prompt inheritance resolution and cascading merger (VEL-112)."""

import pytest
from app.prompts.models import PromptFile, PromptFrontmatter

from app.prompts.inheritance import (
    CircularInheritanceError,
    cascade_merge,
    resolve_all,
    resolve_single,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(
    name: str,
    body: str = "",
    *,
    inherits: str | None = None,
    priority: int = 0,
    scope: list[str] | None = None,
    triggers: list[str] | None = None,
    variables: dict[str, str] | None = None,
) -> PromptFile:
    fm = PromptFrontmatter(
        scope=scope or [],
        triggers=triggers or [],
        priority=priority,
        inherits=inherits,
        variables=variables or {},
    )
    return PromptFile(name=name, path="", frontmatter=fm, body=body, source="repo")


# ---------------------------------------------------------------------------
# resolve_single — basic inheritance
# ---------------------------------------------------------------------------

class TestResolveSingle:
    def test_no_inherits_returns_unchanged(self):
        p = _make("standalone", body="Hello world")
        result = resolve_single(p, {"standalone": p})
        assert result is p

    def test_inherits_prepends_parent_body(self):
        parent = _make("base", body="Base instructions.")
        child = _make("child", body="Extra instructions.", inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.body == "Base instructions.\n\nExtra instructions."

    def test_child_body_only_when_parent_empty(self):
        parent = _make("base", body="")
        child = _make("child", body="Only child.", inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.body == "Only child."

    def test_parent_body_only_when_child_empty(self):
        parent = _make("base", body="Only parent.")
        child = _make("child", body="", inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.body == "Only parent."

    def test_child_scope_overrides_parent(self):
        parent = _make("base", scope=["api/**"])
        child = _make("child", scope=["frontend/**"], inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.frontmatter.scope == ["frontend/**"]

    def test_child_inherits_parent_scope_when_empty(self):
        parent = _make("base", scope=["api/**"])
        child = _make("child", inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.frontmatter.scope == ["api/**"]

    def test_child_priority_overrides_parent(self):
        parent = _make("base", priority=3)
        child = _make("child", priority=7, inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.frontmatter.priority == 7

    def test_child_inherits_parent_priority_when_zero(self):
        parent = _make("base", priority=5)
        child = _make("child", priority=0, inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.frontmatter.priority == 5

    def test_variables_deep_merged_child_wins(self):
        parent = _make("base", variables={"style": "lenient", "focus": "security"})
        child = _make("child", variables={"style": "strict"}, inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.frontmatter.variables == {"style": "strict", "focus": "security"}

    def test_inherits_field_consumed_in_result(self):
        parent = _make("base")
        child = _make("child", inherits="base")
        result = resolve_single(child, {"base": parent, "child": child})
        assert result.frontmatter.inherits is None

    def test_result_preserves_child_name_and_source(self):
        parent = _make("base")
        child = _make("child", inherits="base")
        child_db = PromptFile(
            name="child", path="/db", frontmatter=child.frontmatter, body="body", source="db"
        )
        result = resolve_single(child_db, {"base": parent, "child": child_db})
        assert result.name == "child"
        assert result.source == "db"

    def test_missing_parent_raises_value_error(self):
        child = _make("child", inherits="nonexistent")
        with pytest.raises(ValueError, match="unknown prompt 'nonexistent'"):
            resolve_single(child, {"child": child})


# ---------------------------------------------------------------------------
# resolve_single — multi-level chains
# ---------------------------------------------------------------------------

class TestResolveSingleChain:
    def test_two_level_chain(self):
        grandparent = _make("root", body="Root.")
        parent = _make("middle", body="Middle.", inherits="root")
        child = _make("leaf", body="Leaf.", inherits="middle")
        registry = {"root": grandparent, "middle": parent, "leaf": child}
        result = resolve_single(child, registry)
        assert result.body == "Root.\n\nMiddle.\n\nLeaf."

    def test_three_level_variable_precedence(self):
        gp = _make("root", variables={"x": "1", "y": "2", "z": "3"})
        p = _make("middle", variables={"x": "10", "y": "20"}, inherits="root")
        c = _make("leaf", variables={"x": "100"}, inherits="middle")
        registry = {"root": gp, "middle": p, "leaf": c}
        result = resolve_single(c, registry)
        assert result.frontmatter.variables == {"x": "100", "y": "20", "z": "3"}


# ---------------------------------------------------------------------------
# Circular inheritance detection
# ---------------------------------------------------------------------------

class TestCircularInheritance:
    def test_self_loop(self):
        p = _make("loop", inherits="loop")
        with pytest.raises(CircularInheritanceError, match="loop"):
            resolve_single(p, {"loop": p})

    def test_two_node_cycle(self):
        a = _make("a", inherits="b")
        b = _make("b", inherits="a")
        with pytest.raises(CircularInheritanceError):
            resolve_single(a, {"a": a, "b": b})

    def test_three_node_cycle(self):
        a = _make("a", inherits="b")
        b = _make("b", inherits="c")
        c = _make("c", inherits="a")
        with pytest.raises(CircularInheritanceError):
            resolve_single(a, {"a": a, "b": b, "c": c})

    def test_error_message_includes_cycle_path(self):
        a = _make("a", inherits="b")
        b = _make("b", inherits="a")
        with pytest.raises(CircularInheritanceError, match="a") as exc_info:
            resolve_single(a, {"a": a, "b": b})
        assert "b" in str(exc_info.value)


# ---------------------------------------------------------------------------
# resolve_all
# ---------------------------------------------------------------------------

class TestResolveAll:
    def test_resolves_every_prompt(self):
        base = _make("base", body="Base.")
        child = _make("child", body="Child.", inherits="base")
        standalone = _make("standalone", body="Alone.")
        results = resolve_all([base, child, standalone])
        by_name = {r.name: r for r in results}
        assert by_name["base"].body == "Base."
        assert by_name["child"].body == "Base.\n\nChild."
        assert by_name["standalone"].body == "Alone."

    def test_empty_list(self):
        assert resolve_all([]) == []

    def test_propagates_circular_error(self):
        a = _make("a", inherits="b")
        b = _make("b", inherits="a")
        with pytest.raises(CircularInheritanceError):
            resolve_all([a, b])


# ---------------------------------------------------------------------------
# cascade_merge
# ---------------------------------------------------------------------------

class TestCascadeMerge:
    def test_sorts_highest_priority_first(self):
        low = _make("low", priority=1)
        mid = _make("mid", priority=5)
        high = _make("high", priority=10)
        result = cascade_merge([low, high, mid])
        assert [p.name for p in result] == ["high", "mid", "low"]

    def test_stable_sort_preserves_equal_priority_order(self):
        a = _make("a", priority=3)
        b = _make("b", priority=3)
        c = _make("c", priority=3)
        result = cascade_merge([a, b, c])
        assert [p.name for p in result] == ["a", "b", "c"]

    def test_single_prompt_unchanged(self):
        p = _make("only", priority=5)
        assert cascade_merge([p]) == [p]

    def test_empty_list(self):
        assert cascade_merge([]) == []

    def test_zero_and_positive_priority(self):
        zero = _make("zero", priority=0)
        positive = _make("pos", priority=1)
        result = cascade_merge([zero, positive])
        assert result[0].name == "pos"
        assert result[1].name == "zero"
