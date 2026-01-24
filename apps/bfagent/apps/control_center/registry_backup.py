"""
BF Agent Tool Registry for BF Agent Control Center
Manages registration and execution of development tools
"""

import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolStatus:
    """Status information for a tool"""

    name: str
    status: str  # 'ready', 'running', 'error', 'disabled'
    last_run: Optional[datetime] = None
    last_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_count: int = 0
    average_duration: float = 0.0
    success_rate: float = 0.0


@dataclass
class ToolInfo:
    """Information about a registered tool"""

    name: str
    description: str
    version: str
    category: str  # 'quality', 'database', 'ai', 'frontend', 'git'
    executable_path: Optional[str] = None
    make_command: Optional[str] = None
    api_endpoint: Optional[str] = None
    parameters: Optional[List[str]] = None
    status: ToolStatus = field(default_factory=lambda: ToolStatus("unknown", "unknown"))


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolInfo] = {}

    def _initialize_core_tools(self):
        """Initialize core BF Agent tools"""
        core_tools = [
            # Quality Assurance Tools
            ToolInfo(
                name="htmx_scanner",
                description="BF Agent Optimized HTMX Scanner v3",
                category="database",
                executable_path="scripts/fix_migrations.py",
                make_command="fix-migrations",
            ),
            ToolInfo(
                name="chapter_writing_system",
                description="AI-Powered Chapter Writing System Phase 2",
                version="2.0.0",
                category="ai",
                api_endpoint="/chapters/",
            ),
            ToolInfo(
                name="quality_assurance",
                description="Comprehensive Quality Assurance Scanner",
                version="1.0.0",
                category="quality",
                make_command="quick",
            ),
            ToolInfo(
                name="v2_validator",
                description="BF Agent v2.0.0 System Validator",
                version="2.0.0",
                category="quality",
                make_command="v2-check",
            ),
            ToolInfo(
                name="csrf_auto_setup",
                description="HTMX CSRF Auto-Configuration System",
                version="1.0.0",
                category="frontend",
                executable_path="scripts/setup_htmx_csrf.py",
                make_command="htmx-csrf-setup",
            ),
            ToolInfo(
                name="code_formatter",
                description="BF Agent Code Formatter - Comprehensive formatting tool",
                version="1.0.0",
                category="quality",
                executable_path="scripts/code_formatter.py",
            ),
            ToolInfo(
                name="git_sync",
                description="Intelligent Git Sync with auto-generated commit messages",
                version="1.0.0",
                category="tools",
                executable_path="scripts/git_sync_tool.py",
            ),
            ToolInfo(
                name="git_sync_autofix_v3",
                description="🚀 Git Sync Tool V3 - Advanced Conflict Resolution & Pre-commit Integration",
                version="3.0.0",
                category="git",
                executable_path="scripts/git-sync-tool-v3.py",
                parameters=["sync", "--verbose"],
            ),
            ToolInfo(
                name="git_sync_autofix",
                description="Enhanced Git Sync with Auto-Fix (Legacy V2)",
                version="2.0.0",
                category="git",
                executable_path="scripts/git-sync-tool-enhanced_V2.py",
                make_command="sync-autofix",
                parameters=["sync", "--verbose"],
            ),
            ToolInfo(
                name="template_url_validator",
                description="Enterprise Template URL Pattern Validator",
                version="1.0.0",
                category="quality",
                executable_path="scripts/template_url_validator.py",
            ),
            ToolInfo(
                name="model_consistency_checker",
                description="Database-Model-Template-Form Consistency Checker & Repair Tool",
                version="1.0.0",
                category="database",
                executable_path="scripts/model_consistency_checker.py",
            ),
            ToolInfo(
                name="model_consistency_checker_v2",
                description="Enhanced Model Consistency Checker for BF Agent v2.0.0 with CRUDConfig validation",
                version="2.0.0",
                category="database",
                executable_path="scripts/model_consistency_checker_V2.py",
            ),
            ToolInfo(
                name="model_consistency_checker_v3",
                description="Advanced Model Consistency Checker V3 with Rich Console Output and Cross-Component Analysis",
                version="3.0.0",
                category="database",
                executable_path="scripts/model_consistency_checker_v3.py",
            ),
            ToolInfo(
                name="screen_documentation_framework",
                description="Screen Documentation & Testing Framework - Automatic UI documentation and test generation",
                version="1.0.0",
                category="testing",
                executable_path="scripts/screen_documentation_framework.py",
            ),
            ToolInfo(
                name="visual_model_explorer",
                description="Interactive Visual Model Explorer with D3.js visualization and CRUDConfig editor",
                version="1.0.0",
                category="development",
                executable_path="scripts/visual_model_explorer.py",
            ),
            ToolInfo(
                name="api_endpoint_checker_v4",
                description="🎯 Enterprise API Checker V4 - Intelligent model processing, advanced pluralization, Rich UI",
                version="4.0.0",
                category="api",
                executable_path="scripts/api_endpoint_checker_v4.py",
            ),
            ToolInfo(
                name="api_endpoint_checker_v3",
                description="🚀 Performance-Optimized API Checker V3 - 6.46x faster with dataclasses and OpenAPI 3.1",
                version="3.0.0",
                category="api",
                executable_path="scripts/api_endpoint_checker_v3.py",
            ),
            ToolInfo(
                name="api_endpoint_checker",
                description="Legacy API Checker V1 - Basic validation (use V4 for production)",
                version="1.0.0",
                category="api",
                executable_path="scripts/api_endpoint_checker.py",
            ),
            ToolInfo(
                name="graphql_schema_generator",
                description="Automatic GraphQL schema generation from Django models with resolver templates",
                version="1.0.0",
                category="api",
                executable_path="scripts/graphql_schema_generator.py",
            ),
            ToolInfo(
                name="graphql_schema_generator_v3",
                description="🚀 Performance-Optimized GraphQL Generator V3 - Modern Python with async detection",
                version="3.0.0",
                category="api",
                executable_path="scripts/graphql_schema_generator_v3.py",
            ),
            ToolInfo(
                name="css_theme_switcher",
                description="🎨 Dynamic CSS Theme Switcher - Multiple themes with live preview and persistence",
                version="1.0.0",
                category="ui",
                executable_path="scripts/css_theme_switcher.py",
            ),
            ToolInfo(
                name="css_theme_switcher_v3",
                description="🚀 Optimized CSS Theme Switcher V3.0 - Modern CSS features, async operations, performance optimized",
                version="3.0.0",
                category="ui",
                executable_path="scripts/optimized-css-theme-switcher.py",
            ),
        ]

        for tool in core_tools:
            self.register_tool(tool)

    def register_tool(self, tool_info: ToolInfo):
        """Register a new tool"""
        self.tools[tool_info.name] = tool_info
        logger.info(f"Registered tool: {tool_info.name} v{tool_info.version}")

    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """Get tool information by name"""
        return self.tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolInfo]:
        """List all registered tools, optionally filtered by category"""
        tools = list(self.tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return sorted(tools, key=lambda t: t.name)

    def get_tool_status(self, name: str) -> Optional[ToolStatus]:
        """Get current status of a tool"""
        tool = self.get_tool(name)
        if not tool:
            return None

        # Update status by checking tool availability
        self._update_tool_status(tool)
        return tool.status

    def _update_tool_status(self, tool: ToolInfo):
        """Update tool status by checking availability"""
        try:
            if tool.executable_path:
                # Check if script exists and is executable
                script_path = Path(tool.executable_path)
                if script_path.exists():
                    tool.status.status = "ready"
                else:
                    tool.status.status = "error"
                    tool.status.error_message = f"Script not found: {tool.executable_path}"

            elif tool.make_command:
                # Check if make command is available
                try:
                    result = subprocess.run(
                        ["make", "-n", tool.make_command], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        tool.status.status = "ready"
                    else:
                        tool.status.status = "error"
                        tool.status.error_message = (
                            f"Make command not available: {tool.make_command}"
                        )
                except subprocess.TimeoutExpired:
                    tool.status.status = "error"
                    tool.status.error_message = "Make command check timed out"
                except FileNotFoundError:
                    tool.status.status = "error"
                    tool.status.error_message = "Make not available"

            elif tool.api_endpoint:
                # For API endpoints, assume ready (would need actual health check)
                tool.status.status = "ready"

            else:
                tool.status.status = "unknown"

        except Exception as e:
            tool.status.status = "error"
            tool.status.error_message = str(e)

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool and return results"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        start_time = datetime.now(timezone.utc)

        try:
            if tool.executable_path and os.path.exists(tool.executable_path):
                # Build command with parameters - use relative path
                cmd = [sys.executable, tool.executable_path]

                # Add tool-specific parameters if defined
                if tool.parameters:
                    cmd.extend(tool.parameters)

                # Execute Python script directly with UTF-8 encoding
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",  # Replace problematic characters
                    timeout=300,  # 5 minute timeout
                    cwd=None,  # Use current working directory
                )

                # Convert CompletedProcess to dictionary
                result_dict = {
                    "success": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "command": " ".join(cmd),
                    "duration": (datetime.now(timezone.utc) - start_time).total_seconds(),
                }

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._update_tool_statistics(tool, duration, success=result.returncode == 0)

                tool.status.last_run = start_time
                tool.status.last_result = result_dict
                tool.status.status = "ready" if result.returncode == 0 else "error"

                if result.returncode != 0:
                    tool.status.error_message = result.stderr or "Command failed"

                return result_dict
            else:
                raise FileNotFoundError(f"Tool script not found: {tool.executable_path}")

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._update_tool_statistics(tool, duration, success=False)

            tool.status.status = "error"
            tool.status.error_message = str(e)
            tool.status.last_run = start_time

            raise

    def _execute_script(self, tool: ToolInfo, **kwargs) -> Dict[str, Any]:
        """Execute a Python script"""
        cmd = ["python", tool.executable_path]

        # Special handling for code_formatter
        if tool.name == "code_formatter":
            # Add formatter-specific arguments
            command = kwargs.get("command", "all")
            cmd.append(command)

            if kwargs.get("verbose"):
                cmd.append("--verbose")
            if kwargs.get("skip_templates"):
                cmd.append("--skip-templates")
            if kwargs.get("files"):
                cmd.extend(["--files"] + kwargs["files"])

        # Special handling for git_sync
        elif tool.name == "git_sync":
            # Add git sync specific arguments
            command = kwargs.get("command", "sync")
            cmd.append(command)

            if kwargs.get("message"):
                cmd.extend(["--message", kwargs["message"]])
            if kwargs.get("verbose"):
                cmd.append("--verbose")
            if kwargs.get("no_push"):
                cmd.append("--no-push")
            if kwargs.get("branch"):
                cmd.extend(["--branch", kwargs["branch"]])

        # Special handling for git_sync_autofix (Enhanced version)
        elif tool.name == "git_sync_autofix":
            # Add enhanced git sync specific arguments
            command = kwargs.get("command", "sync")
            cmd.append(command)

            if kwargs.get("message"):
                cmd.extend(["--message", kwargs["message"]])
            if kwargs.get("verbose"):
                cmd.append("--verbose")
            if kwargs.get("no_push"):
                cmd.append("--no-push")
            if kwargs.get("no_fix"):
                cmd.append("--no-fix")

        else:
            # Add common arguments for other tools
            if kwargs.get("format"):
                cmd.extend(["--format", kwargs["format"]])
            if kwargs.get("fix"):
                cmd.append("--fix")
            if kwargs.get("dry_run"):
                cmd.append("--dry-run")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }

    def _execute_make_command(self, tool: ToolInfo, **kwargs) -> Dict[str, Any]:
        """Execute a make command"""
        cmd = ["make", tool.make_command]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }

    def _update_tool_statistics(self, tool: ToolInfo, duration: float, success: bool):
        """Update tool execution statistics"""
        tool.status.execution_count += 1

        # Update average duration
        if tool.status.execution_count == 1:
            tool.status.average_duration = duration
        else:
            tool.status.average_duration = (
                tool.status.average_duration * (tool.status.execution_count - 1) + duration
            ) / tool.status.execution_count

        # Update success rate
        if success:
            success_count = tool.status.success_rate * (tool.status.execution_count - 1) + 1
        else:
            success_count = tool.status.success_rate * (tool.status.execution_count - 1)

        tool.status.success_rate = success_count / tool.status.execution_count

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        tools = list(self.tools.values())

        # Update all tool statuses
        for tool in tools:
            self._update_tool_status(tool)

        total_tools = len(tools)
        ready_tools = len([t for t in tools if t.status.status == "ready"])
        error_tools = len([t for t in tools if t.status.status == "error"])

        health_score = (ready_tools / total_tools * 100) if total_tools > 0 else 0

        return {
            "overall_status": (
                "healthy"
                if health_score >= 80
                else "degraded" if health_score >= 50 else "critical"
            ),
            "health_score": health_score,
            "total_tools": total_tools,
            "ready_tools": ready_tools,
            "error_tools": error_tools,
            "tools": {
                tool.name: {
                    "status": tool.status.status,
                    "last_run": tool.status.last_run.isoformat() if tool.status.last_run else None,
                    "execution_count": tool.status.execution_count,
                    "success_rate": tool.status.success_rate,
                    "average_duration": tool.status.average_duration,
                    "error_message": tool.status.error_message,
                }
                for tool in tools
            },
        }

    def discover_tools(self):
        """Auto-discover tools in the project"""
        logger.info("Tool registry initialized with core BF Agent v2.0.0 tools")


# Global registry instance
tool_registry = ToolRegistry()
