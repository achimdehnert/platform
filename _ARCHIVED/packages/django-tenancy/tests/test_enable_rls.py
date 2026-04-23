"""Tests for enable_rls management command (ADR-137 Phase 2)."""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from django_tenancy.management.commands.enable_rls import (
    CAST_MAP,
    _get_tenant_models,
    _safe_name,
)


class TestCastMap:
    def test_should_map_uuid(self):
        assert CAST_MAP["UUIDField"] == "uuid"

    def test_should_map_bigint(self):
        assert CAST_MAP["BigIntegerField"] == "bigint"

    def test_should_map_autofield(self):
        assert CAST_MAP["BigAutoField"] == "bigint"


class TestSafeName:
    def test_should_replace_dots(self):
        assert _safe_name("app.table") == "app_table"

    def test_should_replace_dashes(self):
        assert _safe_name("my-table") == "my_table"

    def test_should_handle_clean_name(self):
        assert _safe_name("risk_assessment") == "risk_assessment"


class TestGetTenantModels:
    def test_should_find_tenant_models(self):
        """Models with tenant_id should be discovered."""
        models = list(_get_tenant_models())
        tables = [t for _, t, _ in models]
        assert len(tables) > 0
        # Membership has tenant_id
        assert "tenancy_membership" in tables

    def test_should_detect_uuid_cast(self):
        models = list(_get_tenant_models())
        for _, table, cast in models:
            assert cast in ("uuid", "bigint")


@pytest.mark.django_db
class TestEnableRlsCommand:
    def test_should_fail_on_sqlite(self):
        """SQLite backend should abort with error."""
        out = StringIO()
        err = StringIO()
        call_command(
            "enable_rls", "--dry-run",
            stdout=out, stderr=err,
        )
        output = err.getvalue()
        assert "PostgreSQL" in output or "sqlite" in output.lower()

    def test_should_show_dry_run_sql_on_postgres(self):
        """On PostgreSQL, --dry-run shows SQL."""
        with patch(
            "django_tenancy.management.commands.enable_rls"
            ".connection"
        ) as mock_conn:
            mock_conn.vendor = "postgresql"
            out = StringIO()
            call_command(
                "enable_rls", "--dry-run",
                stdout=out, stderr=StringIO(),
            )
            output = out.getvalue()
            assert "Enable RLS" in output
            assert "ENABLE ROW LEVEL SECURITY" in output

    def test_should_show_disable_sql_on_postgres(self):
        with patch(
            "django_tenancy.management.commands.enable_rls"
            ".connection"
        ) as mock_conn:
            mock_conn.vendor = "postgresql"
            out = StringIO()
            call_command(
                "enable_rls", "--dry-run", "--disable",
                stdout=out, stderr=StringIO(),
            )
            output = out.getvalue()
            assert "Disable RLS" in output
            assert "DISABLE ROW LEVEL SECURITY" in output

    def test_should_filter_by_table(self):
        with patch(
            "django_tenancy.management.commands.enable_rls"
            ".connection"
        ) as mock_conn:
            mock_conn.vendor = "postgresql"
            out = StringIO()
            err = StringIO()
            call_command(
                "enable_rls",
                "--dry-run",
                "--table=nonexistent_table",
                stdout=out, stderr=err,
            )
            assert "not found" in err.getvalue()
