"""Tests for Architecture Guardian (Agent A2)."""
from __future__ import annotations

from agents.guardian import (
    Gate,
    GuardianResult,
    analyze_diff,
    check_g001_model_without_migration,
    check_g002_api_signature_changed,
    check_g003_model_without_tenant_id,
    check_g004_pr_too_large,
    parse_diff,
)


DIFF_MODEL_NO_MIGRATION = """\
diff --git a/apps/core/models.py b/apps/core/models.py
index abc1234..def5678 100644
--- a/apps/core/models.py
+++ b/apps/core/models.py
@@ -10,6 +10,12 @@ class ExistingModel(models.Model):
     name = models.CharField(max_length=100)

+class NewModel(models.Model):
+    title = models.CharField(max_length=200)
+    description = models.TextField()
+
+    class Meta:
+        ordering = ["-created"]
"""

DIFF_MODEL_WITH_MIGRATION = """\
diff --git a/apps/core/models.py b/apps/core/models.py
index abc1234..def5678 100644
--- a/apps/core/models.py
+++ b/apps/core/models.py
@@ -10,6 +10,12 @@ class ExistingModel(models.Model):
+class NewModel(models.Model):
+    title = models.CharField(max_length=200)
diff --git a/apps/core/migrations/0002_newmodel.py b/apps/core/migrations/0002_newmodel.py
new file mode 100644
--- /dev/null
+++ b/apps/core/migrations/0002_newmodel.py
@@ -0,0 +1,5 @@
+from django.db import migrations, models
"""

DIFF_API_CHANGE = """\
diff --git a/apps/api/serializers.py b/apps/api/serializers.py
index abc1234..def5678 100644
--- a/apps/api/serializers.py
+++ b/apps/api/serializers.py
@@ -5,8 +5,6 @@ from rest_framework import serializers
-class OldSerializer(serializers.ModelSerializer):
-    class Meta:
-        model = OldModel
+class NewSerializer(serializers.ModelSerializer):
+    class Meta:
+        model = NewModel
"""

DIFF_MODEL_NO_TENANT = """\
diff --git a/apps/tenants/models.py b/apps/tenants/models.py
index abc1234..def5678 100644
--- a/apps/tenants/models.py
+++ b/apps/tenants/models.py
@@ -10,0 +11,6 @@
+class ProjectData(models.Model):
+    name = models.CharField(max_length=200)
+    created = models.DateTimeField(auto_now_add=True)
+
+    class Meta:
+        ordering = ["-created"]
"""

DIFF_LARGE_PR = (
    "diff --git a/big.py b/big.py\n"
    "--- a/big.py\n+++ b/big.py\n"
    "@@ -1 +1,500 @@\n"
    + "\n".join(f"+line {i}" for i in range(500))
)


class TestParseDiff:
    def test_should_parse_single_file(self):
        files = parse_diff(DIFF_MODEL_NO_MIGRATION)
        assert len(files) == 1
        assert files[0]["path"] == "apps/core/models.py"

    def test_should_parse_multiple_files(self):
        files = parse_diff(DIFF_MODEL_WITH_MIGRATION)
        assert len(files) == 2

    def test_should_separate_added_removed(self):
        files = parse_diff(DIFF_API_CHANGE)
        assert len(files[0]["added_lines"]) > 0
        assert len(files[0]["removed_lines"]) > 0

    def test_should_handle_empty_diff(self):
        files = parse_diff("")
        assert files == []


class TestG001ModelWithoutMigration:
    def test_should_detect_model_change_without_migration(
        self,
    ):
        files = parse_diff(DIFF_MODEL_NO_MIGRATION)
        violations = check_g001_model_without_migration(files)
        assert len(violations) == 1
        assert violations[0].rule == "G-001"
        assert violations[0].gate == Gate.AUTO_WARN

    def test_should_pass_when_migration_present(self):
        files = parse_diff(DIFF_MODEL_WITH_MIGRATION)
        violations = check_g001_model_without_migration(files)
        assert len(violations) == 0


class TestG002ApiSignatureChanged:
    def test_should_detect_serializer_removal(self):
        files = parse_diff(DIFF_API_CHANGE)
        violations = check_g002_api_signature_changed(files)
        assert len(violations) >= 1
        assert violations[0].rule == "G-002"
        assert violations[0].gate == Gate.HUMAN_APPROVAL


class TestG003ModelWithoutTenantId:
    def test_should_detect_model_without_tenant_id(self):
        files = parse_diff(DIFF_MODEL_NO_TENANT)
        violations = check_g003_model_without_tenant_id(files)
        assert len(violations) == 1
        assert violations[0].rule == "G-003"
        assert violations[0].gate == Gate.HUMAN_APPROVAL
        assert "tenant_id" in violations[0].suggestion

    def test_should_pass_when_no_new_models(self):
        files = parse_diff(DIFF_API_CHANGE)
        violations = check_g003_model_without_tenant_id(files)
        assert len(violations) == 0


class TestG004PrTooLarge:
    def test_should_detect_large_pr(self):
        files = parse_diff(DIFF_LARGE_PR)
        violations = check_g004_pr_too_large(
            files, threshold=400,
        )
        assert len(violations) == 1
        assert violations[0].rule == "G-004"

    def test_should_pass_small_pr(self):
        files = parse_diff(DIFF_MODEL_NO_MIGRATION)
        violations = check_g004_pr_too_large(
            files, threshold=400,
        )
        assert len(violations) == 0


class TestAnalyzeDiff:
    def test_should_return_passed_for_clean_diff(self):
        result = analyze_diff(DIFF_MODEL_WITH_MIGRATION)
        assert isinstance(result, GuardianResult)
        assert result.files_checked == 2

    def test_should_detect_blocking_violations(self):
        result = analyze_diff(DIFF_API_CHANGE)
        assert result.blocking is True
        assert result.max_gate >= Gate.HUMAN_APPROVAL

    def test_should_generate_markdown(self):
        result = analyze_diff(DIFF_MODEL_NO_MIGRATION)
        md = result.to_markdown()
        assert "Architecture Guardian" in md

    def test_should_generate_dict(self):
        result = analyze_diff(DIFF_MODEL_NO_MIGRATION)
        d = result.to_dict()
        assert "violations" in d
        assert "passed" in d
        assert "blocking" in d
