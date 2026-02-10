"""
Tests: Docker Container + Compose Consolidated Tools
=====================================================

Testet:
1. DockerContainerTool - Actions, Schema, Dispatch
2. DockerComposeTool - Actions, Schema, Dispatch, Deploy-Workflow

pytest tests/test_docker.py -v
"""

import pytest

from tool_consolidation.docker_container import DockerContainerTool
from tool_consolidation.docker_compose import DockerComposeTool


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def container_tool():
    return DockerContainerTool()  # Demo mode


@pytest.fixture
def compose_tool():
    return DockerComposeTool()  # Demo mode


# =============================================================================
# DockerContainerTool: Action Registry
# =============================================================================


class TestContainerToolRegistry:
    """Teste Action-Registrierung."""

    def test_expected_actions(self, container_tool):
        expected = {"list", "logs", "stats", "inspect", "start", "stop", "restart", "exec", "remove"}
        assert set(container_tool.available_actions) == expected

    def test_tool_name(self, container_tool):
        assert container_tool.tool_name == "container_manage"

    def test_action_count(self, container_tool):
        assert len(container_tool.available_actions) == 9
        # VORHER: 7 separate Tools + inspect + remove = 9 actions → 1 Tool

    def test_destructive_actions(self, container_tool):
        """Nur 'remove' ist destruktiv."""
        destructive = [
            name for name, meta in container_tool._actions.items()
            if meta.destructive
        ]
        assert destructive == ["remove"]

    def test_readonly_actions(self, container_tool):
        """list, logs, stats, inspect sind read-only."""
        readonly = {
            name for name, meta in container_tool._actions.items()
            if meta.read_only
        }
        assert readonly == {"list", "logs", "stats", "inspect"}


# =============================================================================
# DockerContainerTool: Schema
# =============================================================================


class TestContainerToolSchema:
    def test_schema_action_enum(self, container_tool):
        schema = container_tool.build_input_schema()
        actions = schema["properties"]["action"]["enum"]
        assert "list" in actions
        assert "logs" in actions
        assert "exec" in actions
        assert "remove" in actions

    def test_schema_has_container_param(self, container_tool):
        schema = container_tool.build_input_schema()
        assert "container" in schema["properties"]

    def test_schema_has_server_name(self, container_tool):
        schema = container_tool.build_input_schema()
        assert "server_name" in schema["properties"]

    def test_schema_has_confirm(self, container_tool):
        schema = container_tool.build_input_schema()
        assert "confirm" in schema["properties"]


# =============================================================================
# DockerContainerTool: Dispatch
# =============================================================================


class TestContainerToolDispatch:
    @pytest.mark.asyncio
    async def test_list_demo(self, container_tool):
        result = await container_tool.dispatch({"action": "list"})
        assert "Docker Containers" in result
        assert "nginx-proxy" in result

    @pytest.mark.asyncio
    async def test_list_with_filter(self, container_tool):
        result = await container_tool.dispatch({
            "action": "list", "filter_name": "postgres"
        })
        assert "postgres" in result.lower()

    @pytest.mark.asyncio
    async def test_list_all_containers(self, container_tool):
        result = await container_tool.dispatch({
            "action": "list", "all_containers": True
        })
        assert "old-worker" in result  # Stopped container in demo

    @pytest.mark.asyncio
    async def test_logs_demo(self, container_tool):
        result = await container_tool.dispatch({
            "action": "logs", "container": "app-backend", "lines": 20
        })
        assert "Demo" in result
        assert "app-backend" in result

    @pytest.mark.asyncio
    async def test_stats_demo(self, container_tool):
        result = await container_tool.dispatch({"action": "stats"})
        assert "Container Stats" in result
        assert "CPU" in result

    @pytest.mark.asyncio
    async def test_start_demo(self, container_tool):
        result = await container_tool.dispatch({
            "action": "start", "container": "old-worker"
        })
        assert "Demo" in result
        assert "old-worker" in result

    @pytest.mark.asyncio
    async def test_stop_demo(self, container_tool):
        result = await container_tool.dispatch({
            "action": "stop", "container": "app-backend"
        })
        assert "Demo" in result

    @pytest.mark.asyncio
    async def test_restart_demo(self, container_tool):
        result = await container_tool.dispatch({
            "action": "restart", "container": "app-backend"
        })
        assert "Demo" in result
        assert "restart" in result.lower()

    @pytest.mark.asyncio
    async def test_exec_demo(self, container_tool):
        result = await container_tool.dispatch({
            "action": "exec", "container": "app-backend", "command": "ls -la"
        })
        assert "Demo" in result
        assert "ls -la" in result

    @pytest.mark.asyncio
    async def test_remove_requires_confirm(self, container_tool):
        result = await container_tool.dispatch({
            "action": "remove", "container": "old-worker"
        })
        assert "destructive" in result.lower()
        assert "confirm" in result.lower()

    @pytest.mark.asyncio
    async def test_remove_with_confirm(self, container_tool):
        result = await container_tool.dispatch({
            "action": "remove", "container": "old-worker", "confirm": True
        })
        assert "Demo" in result
        assert "remove" in result.lower()


# =============================================================================
# DockerComposeTool: Action Registry
# =============================================================================


class TestComposeToolRegistry:
    def test_expected_actions(self, compose_tool):
        expected = {"status", "logs", "up", "down", "restart", "build", "pull", "exec", "deploy"}
        assert set(compose_tool.available_actions) == expected

    def test_tool_name(self, compose_tool):
        assert compose_tool.tool_name == "compose_manage"

    def test_action_count(self, compose_tool):
        assert len(compose_tool.available_actions) == 9

    def test_destructive_actions(self, compose_tool):
        destructive = [
            name for name, meta in compose_tool._actions.items()
            if meta.destructive
        ]
        assert destructive == ["down"]

    def test_readonly_actions(self, compose_tool):
        readonly = {
            name for name, meta in compose_tool._actions.items()
            if meta.read_only
        }
        assert readonly == {"status", "logs"}


# =============================================================================
# DockerComposeTool: Schema
# =============================================================================


class TestComposeToolSchema:
    def test_schema_action_enum(self, compose_tool):
        schema = compose_tool.build_input_schema()
        actions = schema["properties"]["action"]["enum"]
        assert len(actions) == 9
        assert "deploy" in actions

    def test_schema_has_project_dir(self, compose_tool):
        schema = compose_tool.build_input_schema()
        assert "project_dir" in schema["properties"]

    def test_schema_has_service(self, compose_tool):
        schema = compose_tool.build_input_schema()
        assert "service" in schema["properties"]


# =============================================================================
# DockerComposeTool: Dispatch
# =============================================================================


class TestComposeToolDispatch:
    @pytest.mark.asyncio
    async def test_status_demo(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "status", "project_dir": "/opt/myapp"
        })
        assert "Compose Stack" in result
        assert "/opt/myapp" in result

    @pytest.mark.asyncio
    async def test_logs_demo(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "logs", "project_dir": "/opt/myapp", "service": "web"
        })
        assert "Demo" in result
        assert "web" in result

    @pytest.mark.asyncio
    async def test_up_demo(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "up", "project_dir": "/opt/myapp"
        })
        assert "Demo" in result

    @pytest.mark.asyncio
    async def test_up_with_build(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "up", "project_dir": "/opt/myapp", "build": True
        })
        assert "build" in result.lower()

    @pytest.mark.asyncio
    async def test_build_demo(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "build", "project_dir": "/opt/myapp"
        })
        assert "Demo" in result

    @pytest.mark.asyncio
    async def test_pull_demo(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "pull", "project_dir": "/opt/myapp"
        })
        assert "Demo" in result

    @pytest.mark.asyncio
    async def test_exec_demo(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "exec",
            "project_dir": "/opt/myapp",
            "service": "web",
            "command": "python manage.py shell",
        })
        assert "Demo" in result
        assert "python manage.py shell" in result

    @pytest.mark.asyncio
    async def test_deploy_demo(self, compose_tool):
        """Deploy führt pull → build → up aus."""
        result = await compose_tool.dispatch({
            "action": "deploy", "project_dir": "/opt/myapp"
        })
        assert "Deployment" in result
        assert "Pull complete" in result
        assert "Build complete" in result
        assert "Services started" in result

    @pytest.mark.asyncio
    async def test_deploy_without_build(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "deploy", "project_dir": "/opt/myapp", "build": False
        })
        assert "Pull complete" in result
        assert "Build complete" not in result
        assert "Services started" in result

    @pytest.mark.asyncio
    async def test_down_requires_confirm(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "down", "project_dir": "/opt/myapp"
        })
        assert "destructive" in result.lower()

    @pytest.mark.asyncio
    async def test_down_with_confirm(self, compose_tool):
        result = await compose_tool.dispatch({
            "action": "down", "project_dir": "/opt/myapp", "confirm": True
        })
        assert "Demo" in result


# =============================================================================
# Reduction Stats
# =============================================================================


class TestReductionStats:
    """Verifiziere die Tool-Reduktion."""

    def test_container_reduction(self, container_tool):
        """9 Actions → 1 MCP Tool."""
        assert len(container_tool.available_actions) == 9
        print(f"\n📊 Container: {len(container_tool.available_actions)} actions → 1 tool")

    def test_compose_reduction(self, compose_tool):
        """9 Actions → 1 MCP Tool."""
        assert len(compose_tool.available_actions) == 9
        print(f"📊 Compose:   {len(compose_tool.available_actions)} actions → 1 tool")

    def test_combined_reduction(self, container_tool, compose_tool):
        """18 Actions → 2 MCP Tools (statt 16 Tools vorher)."""
        total_actions = (
            len(container_tool.available_actions)
            + len(compose_tool.available_actions)
        )
        assert total_actions == 18
        print(f"📊 Docker gesamt: {total_actions} actions → 2 tools (vorher ~16 tools)")
