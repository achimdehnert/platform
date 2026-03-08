"""
orchestrator_mcp/agent_team/tests/test_roles_and_detector.py

Fix L-4: package-relative imports (no longer CWD-dependent).

Run: pytest orchestrator_mcp/agent_team/tests/test_roles_and_detector.py -v
"""

from __future__ import annotations

import pytest

from orchestrator_mcp.agent_team.roles import (
    AgentRole,
    AgentRoleProtocol,
    DeploymentAgentConfig,
    GateLevel,
    ReviewAgentConfig,
    ReviewCheckResult,
    ShellAllowlist,
    get_role,
    route_task,
)
from orchestrator_mcp.agent_team.breaking_change_detector import (
    ChangeType,
    MigrationAnalysis,
    MigrationChange,
    _classify_sql_statement,
    get_deployment_gate_level,
)


# ---------------------------------------------------------------------------
# AgentRoleProtocol — Fix B-3
# ---------------------------------------------------------------------------


class TestAgentRoleProtocol:
    def test_deployment_config_satisfies_protocol(self):
        agent = DeploymentAgentConfig()
        assert isinstance(agent, AgentRoleProtocol)

    def test_review_config_satisfies_protocol(self):
        agent = ReviewAgentConfig()
        assert isinstance(agent, AgentRoleProtocol)

    def test_get_role_returns_protocol(self):
        role = get_role(AgentRole.DEPLOYMENT)
        assert isinstance(role, AgentRoleProtocol)

    def test_deployment_cannot_auto_execute(self):
        agent = DeploymentAgentConfig()
        assert agent.can_auto_execute() is False

    def test_review_can_auto_execute(self):
        agent = ReviewAgentConfig()
        assert agent.can_auto_execute() is True


# ---------------------------------------------------------------------------
# ShellAllowlist
# ---------------------------------------------------------------------------


class TestShellAllowlist:
    def setup_method(self):
        self.allowlist = ShellAllowlist()

    def test_allowed_docker_command(self):
        assert self.allowlist.validate_command("docker compose up -d") is True

    def test_allowed_python_command(self):
        assert self.allowlist.validate_command("python manage.py migrate") is True

    def test_blocked_rm_command(self):
        assert self.allowlist.validate_command("rm -rf /") is False

    def test_blocked_sudo_command(self):
        assert self.allowlist.validate_command("sudo reboot") is False

    def test_wrap_script_adds_preamble(self):
        script = "docker compose up"
        wrapped = self.allowlist.wrap_script(script)
        assert wrapped.startswith("set -euo pipefail\n")

    def test_wrap_script_idempotent(self):
        script = "set -euo pipefail\ndocker compose up"
        wrapped = self.allowlist.wrap_script(script)
        assert wrapped.count("set -euo pipefail") == 1


# ---------------------------------------------------------------------------
# DeploymentAgentConfig
# ---------------------------------------------------------------------------


class TestDeploymentAgentConfig:
    def setup_method(self):
        self.agent = DeploymentAgentConfig()

    def test_role_is_deployment(self):
        assert self.agent.role == AgentRole.DEPLOYMENT

    def test_gate_level_is_two(self):
        assert self.agent.gate_level == GateLevel.TWO

    def test_deployment_script_has_preamble(self):
        script = self.agent.build_deployment_script("v1.0", "web")
        assert script.startswith("set -euo pipefail")

    def test_deployment_script_has_no_deps(self):
        script = self.agent.build_deployment_script("v1.0", "web")
        assert "--no-deps" in script
        assert "--force-recreate" in script

    def test_migration_script_has_timeout(self):
        script = self.agent.build_migration_script()
        assert "timeout" in script
        assert "300" in script

    def test_migration_script_custom_timeout(self):
        script = self.agent.build_migration_script(timeout_seconds=60)
        assert "timeout 60" in script

    def test_migration_script_has_preamble(self):
        script = self.agent.build_migration_script()
        assert script.startswith("set -euo pipefail")

    def test_health_check_script_has_retries(self):
        script = self.agent.build_health_check_script("https://example.com")
        assert "for i in 1 2 3" in script

    def test_rollback_requires_previous_tag(self):
        with pytest.raises(ValueError, match="previous_image_tag is required"):
            self.agent.build_rollback_script("", "web")

    def test_rollback_script_has_preamble(self):
        script = self.agent.build_rollback_script("ghcr.io/org/app:v1.0", "web")
        assert script.startswith("set -euo pipefail")

    def test_rollback_requires_tech_lead_on_destructive(self):
        policy = self.agent.rollback_policy
        assert policy.requires_tech_lead(
            migration_is_destructive=True,
            migration_was_applied=True,
        ) is True

    def test_rollback_no_tech_lead_if_not_applied(self):
        policy = self.agent.rollback_policy
        assert policy.requires_tech_lead(
            migration_is_destructive=True,
            migration_was_applied=False,
        ) is False


# ---------------------------------------------------------------------------
# ReviewAgentConfig
# ---------------------------------------------------------------------------


class TestReviewAgentConfig:
    def setup_method(self):
        self.agent = ReviewAgentConfig()

    def test_check_pipeline_order(self):
        pipeline = self.agent.check_pipeline
        names = [c["name"] for c in pipeline]
        assert names.index("ruff_bandit") < names.index("adr_compliance")
        assert names.index("adr_compliance") < names.index("platform_patterns")

    def test_ruff_bandit_is_blocking(self):
        pipeline = self.agent.check_pipeline
        ruff = next(c for c in pipeline if c["name"] == "ruff_bandit")
        assert ruff["blocking"] is True

    def test_coverage_delta_is_not_blocking(self):
        pipeline = self.agent.check_pipeline
        cov = next(c for c in pipeline if c["name"] == "coverage_delta")
        assert cov["blocking"] is False

    def test_pr_comment_all_passed(self):
        results = [
            ReviewCheckResult("ruff_bandit", True, True, "All clean"),
            ReviewCheckResult("adr_compliance", True, True, "No violations"),
        ]
        comment = self.agent.build_pr_comment(42, results)
        assert "All checks passed" in comment

    def test_pr_comment_with_blockers(self):
        results = [
            ReviewCheckResult("ruff_bandit", False, True, "2 Ruff violations"),
        ]
        comment = self.agent.build_pr_comment(42, results)
        assert "blocking issue" in comment
        assert "Merge blocked" in comment

    def test_pr_comment_includes_override_instructions(self):
        comment = self.agent.build_pr_comment(42, [])
        assert self.agent.override_label in comment
        assert self.agent.override_comment_trigger in comment


# ---------------------------------------------------------------------------
# Task Router
# ---------------------------------------------------------------------------


class TestRouteTask:
    def test_adr_routes_to_tech_lead(self):
        assert route_task("adr") == AgentRole.TECH_LEAD

    def test_architecture_routes_to_tech_lead(self):
        assert route_task("architecture") == AgentRole.TECH_LEAD

    def test_feature_routes_to_developer(self):
        assert route_task("feature", "simple") == AgentRole.DEVELOPER

    def test_complex_feature_still_developer(self):
        assert route_task("feature", "complex") == AgentRole.DEVELOPER

    def test_test_routes_to_tester(self):
        assert route_task("test") == AgentRole.TESTER

    def test_deployment_routes_to_deployment_agent(self):
        assert route_task("deployment") == AgentRole.DEPLOYMENT

    def test_pr_review_routes_to_review_agent(self):
        assert route_task("pr_review") == AgentRole.REVIEW

    def test_refactor_routes_to_re_engineer(self):
        assert route_task("refactor") == AgentRole.RE_ENGINEER

    def test_unknown_task_raises(self):
        with pytest.raises(ValueError, match="Unknown task_type"):
            route_task("unknown_task")


# ---------------------------------------------------------------------------
# Breaking Change Detector — Fix M-4: auto_eligible return value
# ---------------------------------------------------------------------------


class TestClassifySQLStatement:
    def test_drop_table_is_breaking(self):
        result = _classify_sql_statement("DROP TABLE myapp_user;")
        assert result.change_type == ChangeType.BREAKING
        assert "DROP TABLE" in result.reason

    def test_drop_column_is_breaking(self):
        result = _classify_sql_statement(
            "ALTER TABLE myapp_user DROP COLUMN email;"
        )
        assert result.change_type == ChangeType.BREAKING

    def test_rename_is_breaking(self):
        result = _classify_sql_statement(
            "ALTER TABLE myapp_user RENAME COLUMN name TO full_name;"
        )
        assert result.change_type == ChangeType.BREAKING

    def test_set_not_null_without_default_is_breaking(self):
        result = _classify_sql_statement(
            "ALTER TABLE myapp_user ALTER COLUMN email SET NOT NULL;"
        )
        assert result.change_type == ChangeType.BREAKING

    def test_create_table_is_safe(self):
        result = _classify_sql_statement(
            "CREATE TABLE myapp_newmodel (id bigint);"
        )
        assert result.change_type == ChangeType.SAFE

    def test_add_column_is_safe(self):
        result = _classify_sql_statement(
            "ALTER TABLE myapp_user ADD COLUMN phone varchar(20) NULL;"
        )
        assert result.change_type == ChangeType.SAFE

    def test_create_index_is_safe(self):
        result = _classify_sql_statement(
            "CREATE INDEX idx_user_email ON myapp_user (email);"
        )
        assert result.change_type == ChangeType.SAFE

    def test_comment_is_safe(self):
        result = _classify_sql_statement("-- Django migration comment")
        assert result.change_type == ChangeType.SAFE

    def test_empty_statement_is_safe(self):
        result = _classify_sql_statement("")
        assert result.change_type == ChangeType.SAFE


class TestGetDeploymentGateLevel:
    def test_no_migrations_auto_eligible(self):
        level, auto_eligible, reason = get_deployment_gate_level([])
        assert level == 2
        assert auto_eligible is True
        assert "No pending migrations" in reason

    def test_breaking_changes_not_auto_eligible(self):
        analysis = MigrationAnalysis(
            app_label="myapp",
            migration_name="0001_drop_table",
            changes=[
                MigrationChange(
                    sql_statement="DROP TABLE myapp_user;",
                    change_type=ChangeType.BREAKING,
                    reason="DROP TABLE detected",
                )
            ],
        )
        level, auto_eligible, reason = get_deployment_gate_level([analysis])
        assert level == 2
        assert auto_eligible is False
        assert "Breaking changes" in reason
        assert "Gate-2-Approval required" in reason

    def test_safe_migrations_auto_eligible(self):
        analysis = MigrationAnalysis(
            app_label="myapp",
            migration_name="0002_add_column",
            changes=[
                MigrationChange(
                    sql_statement="ALTER TABLE myapp_user ADD COLUMN phone varchar(20);",
                    change_type=ChangeType.SAFE,
                    reason="ADD COLUMN (additive)",
                )
            ],
        )
        level, auto_eligible, reason = get_deployment_gate_level([analysis])
        assert level == 2
        assert auto_eligible is True
        assert "Additive" in reason

    def test_error_in_analysis_not_auto_eligible(self):
        analysis = MigrationAnalysis(
            app_label="myapp",
            migration_name="0003_broken",
            error="ImportError: module not found",
        )
        level, auto_eligible, reason = get_deployment_gate_level([analysis])
        assert level == 2
        assert auto_eligible is False
        assert "error" in reason.lower()
