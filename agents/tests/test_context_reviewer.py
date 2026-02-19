"""Tests for Context Reviewer (Agent A6)."""
from __future__ import annotations

from agents.context_reviewer import (
    ContextInsight,
    ReviewResult,
    analyze_diff,
    detect_affected_adrs,
    detect_affected_principles,
    detect_affected_projects,
    generate_insights,
    parse_diff,
)


DIFF_MODEL_CHANGE = """\
diff --git a/apps/core/models.py b/apps/core/models.py
index abc1234..def5678 100644
--- a/apps/core/models.py
+++ b/apps/core/models.py
@@ -10,6 +10,12 @@
+class TenantData(models.Model):
+    tenant_id = models.UUIDField(db_index=True)
+    name = models.CharField(max_length=200)
"""

DIFF_HTMX = """\
diff --git a/templates/trips/trip_list.html b/templates/trips/trip_list.html
index abc1234..def5678 100644
--- a/templates/trips/trip_list.html
+++ b/templates/trips/trip_list.html
@@ -5,3 +5,5 @@
+<div hx-get="/trips/search/" hx-target="#results" hx-swap="innerHTML">
+  <input type="text" name="q" hx-trigger="keyup changed delay:300ms">
+</div>
"""

DIFF_HARDCODED_COLOR = """\
diff --git a/templates/base.html b/templates/base.html
index abc1234..def5678 100644
--- a/templates/base.html
+++ b/templates/base.html
@@ -10,3 +10,4 @@
+<div style="color: #ff5733; background: #333333;">
"""

DIFF_SERVICES = """\
diff --git a/apps/trips/services.py b/apps/trips/services.py
index abc1234..def5678 100644
--- a/apps/trips/services.py
+++ b/apps/trips/services.py
@@ -1,3 +1,8 @@
+def create_trip(data):
+    trip = Trip.objects.create(**data)
+    return trip
"""

DIFF_AGENT_CODE = """\
diff --git a/agents/guardian.py b/agents/guardian.py
index abc1234..def5678 100644
--- a/agents/guardian.py
+++ b/agents/guardian.py
@@ -10,3 +10,5 @@
+    agent_rule = "G-005"
+    guardian check for windsurf
"""

DIFF_LARGE = (
    "diff --git a/big.py b/big.py\n"
    "--- a/big.py\n+++ b/big.py\n"
    "@@ -1 +1,500 @@\n"
    + "\n".join(f"+line {i}" for i in range(500))
)


class TestParseDiff:
    def test_should_parse_files(self):
        files = parse_diff(DIFF_MODEL_CHANGE)
        assert len(files) == 1
        assert files[0]["path"] == "apps/core/models.py"

    def test_should_separate_added_removed(self):
        files = parse_diff(DIFF_MODEL_CHANGE)
        assert len(files[0]["added_lines"]) == 3

    def test_should_handle_empty_diff(self):
        assert parse_diff("") == []


class TestDetectAffectedAdrs:
    def test_should_detect_tenant_adr(self):
        files = parse_diff(DIFF_MODEL_CHANGE)
        adrs = detect_affected_adrs(files)
        assert "ADR-035" in adrs

    def test_should_detect_htmx_adr(self):
        files = parse_diff(DIFF_HTMX)
        adrs = detect_affected_adrs(files)
        assert "ADR-048" in adrs

    def test_should_detect_agent_adr(self):
        files = parse_diff(DIFF_AGENT_CODE)
        adrs = detect_affected_adrs(files)
        assert "ADR-054" in adrs


class TestDetectAffectedPrinciples:
    def test_should_detect_database_first(self):
        files = parse_diff(DIFF_MODEL_CHANGE)
        principles = detect_affected_principles(files)
        assert any("P-001" in p for p in principles)

    def test_should_detect_tenant_isolation(self):
        files = parse_diff(DIFF_MODEL_CHANGE)
        principles = detect_affected_principles(files)
        assert any("P-003" in p for p in principles)

    def test_should_detect_minimal_diff(self):
        files = parse_diff(DIFF_LARGE)
        principles = detect_affected_principles(files)
        assert any("P-004" in p for p in principles)

    def test_should_detect_service_layer(self):
        files = parse_diff(DIFF_SERVICES)
        principles = detect_affected_principles(files)
        assert any("P-005" in p for p in principles)


class TestDetectAffectedProjects:
    def test_should_detect_platform(self):
        files = parse_diff(DIFF_AGENT_CODE)
        projects = detect_affected_projects(files)
        assert "platform" in projects

    def test_should_detect_travel_beat(self):
        files = parse_diff(DIFF_SERVICES)
        projects = detect_affected_projects(files)
        assert "travel-beat" in projects


class TestGenerateInsights:
    def test_should_generate_adr_insights(self):
        files = parse_diff(DIFF_MODEL_CHANGE)
        insights = generate_insights(
            files, ["ADR-035"], [], [],
        )
        assert any(
            i.category == "ADR" for i in insights
        )

    def test_should_detect_htmx_patterns(self):
        files = parse_diff(DIFF_HTMX)
        insights = generate_insights(files, [], [], [])
        assert any(
            i.category == "HTMX" for i in insights
        )

    def test_should_detect_hardcoded_colors(self):
        files = parse_diff(DIFF_HARDCODED_COLOR)
        insights = generate_insights(files, [], [], [])
        assert any(
            i.category == "Design Tokens"
            for i in insights
        )

    def test_should_detect_service_layer(self):
        files = parse_diff(DIFF_SERVICES)
        insights = generate_insights(files, [], [], [])
        assert any(
            i.category == "Architecture"
            for i in insights
        )

    def test_should_detect_tenant_id_usage(self):
        files = parse_diff(DIFF_MODEL_CHANGE)
        insights = generate_insights(files, [], [], [])
        assert any(
            i.category == "Multi-Tenancy"
            for i in insights
        )


class TestAnalyzeDiff:
    def test_should_return_result(self):
        result = analyze_diff(DIFF_MODEL_CHANGE)
        assert isinstance(result, ReviewResult)
        assert result.files_checked == 1
        assert result.has_insights

    def test_should_generate_markdown(self):
        result = analyze_diff(DIFF_HTMX)
        md = result.to_markdown()
        assert "Context Reviewer" in md

    def test_should_generate_dict(self):
        result = analyze_diff(DIFF_MODEL_CHANGE)
        d = result.to_dict()
        assert "insights" in d
        assert "affected_adrs" in d
        assert "affected_principles" in d

    def test_should_handle_empty_diff(self):
        result = analyze_diff("")
        assert not result.has_insights
        md = result.to_markdown()
        assert "No additional context" in md


class TestContextInsight:
    def test_should_render_markdown_item(self):
        insight = ContextInsight(
            category="ADR",
            reference="ADR-035",
            message="Tenant-Isolation betroffen",
            file="models.py",
        )
        md = insight.to_markdown_item()
        assert "ADR" in md
        assert "ADR-035" in md
        assert "models.py" in md

    def test_should_render_without_file(self):
        insight = ContextInsight(
            category="Prinzip",
            reference="P-001",
            message="Database-First",
        )
        md = insight.to_markdown_item()
        assert "P-001" in md
        assert "(`" not in md


class TestReviewResult:
    def test_should_report_no_insights(self):
        result = ReviewResult(files_checked=5)
        assert not result.has_insights
        md = result.to_markdown()
        assert "No additional context" in md

    def test_should_report_with_insights(self):
        result = ReviewResult(
            files_checked=3,
            insights=[
                ContextInsight(
                    category="ADR",
                    reference="ADR-035",
                    message="Test",
                ),
            ],
            affected_adrs=["ADR-035"],
            affected_principles=["P-003"],
            affected_projects=["travel-beat"],
        )
        assert result.has_insights
        md = result.to_markdown()
        assert "ADR-035" in md
        assert "P-003" in md
        assert "travel-beat" in md
