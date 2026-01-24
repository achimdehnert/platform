"""
BF Agent Tool Registry for BF Agent Control Center - OPTIMIZED VERSION
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
    category: str  # 'quality', 'development', 'api', 'ui'
    executable_path: Optional[str] = None
    make_command: Optional[str] = None
    api_endpoint: Optional[str] = None
    parameters: Optional[List[str]] = None
    status: ToolStatus = field(default_factory=lambda: ToolStatus("unknown", "unknown"))


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolInfo] = {}
        self._initialize_core_tools()

    def _initialize_core_tools(self):
        """Initialize core BF Agent tools - Optimized & Cleaned"""
        core_tools = [
            # Quality Assurance Tools
            ToolInfo(
                name="htmx_scanner",
                description="🔍 HTMX Conformity Scanner - BF Agent Optimized",
                version="3.0.0",
                category="quality",
                executable_path="scripts/htmx_scanner_v2.py",
                make_command="htmx-scan",
            ),
            ToolInfo(
                name="template_validator",
                description="🎯 Enterprise Template URL Pattern Validator",
                version="1.0.0",
                category="quality",
                executable_path="scripts/template_url_validator.py",
            ),
            ToolInfo(
                name="system_validator",
                description="✅ BF Agent v2.0.0 System Validator",
                version="2.0.0",
                category="quality",
                make_command="v2-check",
            ),
            ToolInfo(
                name="code_formatter",
                description="🎨 BF Agent Code Formatter - Comprehensive formatting tool",
                version="1.0.0",
                category="quality",
                executable_path="scripts/code_formatter.py",
            ),
            # Development Tools
            ToolInfo(
                name="git_sync",
                description="🚀 Git Sync Tool - Advanced Conflict Resolution & Pre-commit Integration",
                version="3.0.0",
                category="development",
                executable_path="scripts/git-sync-tool-v3.py",
                parameters=["sync", "--verbose"],
            ),
            ToolInfo(
                name="model_checker",
                description="🔧 Model Consistency Checker - Cross-Component Analysis & Rich Console Output",
                version="3.0.0",
                category="development",
                executable_path="scripts/model_consistency_checker_v3.py",
            ),
            ToolInfo(
                name="migration_fixer",
                description="🗄️ Database Migration Safety Fixer",
                version="1.0.0",
                category="development",
                executable_path="scripts/fix_migrations.py",
                make_command="fix-migrations",
            ),
            ToolInfo(
                name="phase_agent_manager",
                description="🎯 Phase-Agent-Template Manager - Enterprise Configuration Tool",
                version="1.0.0",
                category="development",
                executable_path="scripts/phase_agent_template_manager.py",
                make_command="phase-sync",
                parameters=["check"],
            ),
            ToolInfo(
                name="screen_documentation",
                description="📋 Screen Documentation & Testing Framework",
                version="1.0.0",
                category="development",
                executable_path="scripts/screen_documentation_framework.py",
            ),
            ToolInfo(
                name="visual_explorer",
                description="🎯 Interactive Visual Model Explorer with D3.js visualization",
                version="1.0.0",
                category="development",
                executable_path="scripts/visual_model_explorer.py",
            ),
            # API Tools
            ToolInfo(
                name="api_checker",
                description="🎯 Enterprise API Checker - Intelligent model processing & Rich UI",
                version="4.0.0",
                category="api",
                executable_path="scripts/api_endpoint_checker_v4.py",
            ),
            ToolInfo(
                name="graphql_generator",
                description="⚡ GraphQL Schema Generator - Performance-Optimized with async detection",
                version="3.0.0",
                category="api",
                executable_path="scripts/graphql_schema_generator_v3.py",
            ),
            ToolInfo(
                name="graphql_analyzer",
                description="🔍 GraphQL Resource Analyzer - Unused Resource Detection & Cleanup",
                version="1.0.0",
                category="api",
                executable_path="scripts/graphql_resource_analyzer.py",
                parameters=["analyze", "--apps", "bfagent"],
            ),
            ToolInfo(
                name="graphql_monitor",
                description="📊 GraphQL Monitoring System - Apollo Studio Alternative",
                version="1.0.0",
                category="api",
                executable_path="scripts/graphql_monitor_setup.py",
                make_command="graphql-monitor",
            ),
            # UI Tools
            ToolInfo(
                name="theme_switcher",
                description="🎨 CSS Theme Switcher - Modern CSS features & performance optimized",
                version="3.0.0",
                category="ui",
                executable_path="scripts/optimized-css-theme-switcher.py",
            ),
            ToolInfo(
                name="csrf_setup",
                description="🛡️ HTMX CSRF Auto-Configuration System",
                version="1.0.0",
                category="ui",
                executable_path="scripts/setup_htmx_csrf.py",
                make_command="htmx-csrf-setup",
            ),
            # Advanced Analysis Tools
            ToolInfo(
                name="enhanced_analyzer",
                description="🔬 Enhanced Tool Analyzer - Deep AST Analysis with Custom Metrics",
                version="1.0.0",
                category="quality",
                executable_path="scripts/enhanced_tool_analyzer.py",
            ),
            ToolInfo(
                name="integrated_analyzer",
                description="🔧 Integrated Analyzer - External Tools (Pylint, Bandit, Radon)",
                version="1.0.0",
                category="quality",
                executable_path="scripts/integrated_analyzer.py",
            ),
            ToolInfo(
                name="hybrid_analyzer",
                description="🚀 Hybrid Analyzer - Best of Both Worlds (Custom + External)",
                version="1.0.0",
                category="quality",
                executable_path="scripts/hybrid_analyzer.py",
                make_command="quality-gate",
            ),
            ToolInfo(
                name="tool_docs_enhanced",
                description="📋 Enhanced Tool Documentation - Function-Level Analysis",
                version="1.0.0",
                category="development",
                executable_path="scripts/generate_tool_docs_enhanced.py",
                make_command="tool-analyze",
            ),
            # Enterprise Quality Analysis
            ToolInfo(
                name="optimized_analyzer",
                description="🏆 Optimized Hybrid Analyzer - Enterprise-Grade Performance",
                version="2.0.0",
                category="quality",
                executable_path="scripts/optimized_hybrid_analyzer.py",
                make_command="quality-enterprise",
                parameters=["--mode", "standard", "--config", "scripts/analyzer_config.txt"],
            ),
            ToolInfo(
                name="unicode_safe_analyzer",
                description="🛡️ Unicode-Safe Analyzer - Windows Compatible Quality Analysis",
                version="1.0.0",
                category="quality",
                executable_path="scripts/unicode_safe_analyzer.py",
                make_command="quality-safe",
            ),
            # Enhanced Auto-Fix System
            ToolInfo(
                name="enhanced_unicode_analyzer",
                description="🔧 Enhanced Unicode Analyzer - Auto-Fix Capabilities",
                version="2.0.0",
                category="quality",
                executable_path="scripts/enhanced_unicode_analyzer.py",
            ),
            ToolInfo(
                name="code_repair_tool",
                description="🛠️ Code Repair Tool - Advanced Automatic Fixes",
                version="1.0.0",
                category="quality",
                executable_path="scripts/code_repair_tool.py",
            ),
            ToolInfo(
                name="enhanced_cli_analyzer",
                description="🎯 Enhanced CLI Analyzer - Complete Quality Solution",
                version="1.0.0",
                category="quality",
                executable_path="scripts/enhanced_cli_analyzer.py",
                make_command="quality-fix",
                parameters=["analyze", "scripts/", "--fix", "--fix-level", "safe"],
            ),
            ToolInfo(
                name="safe_auto_fixer",
                description="🛡️ Safe Auto-Fixer - Syntax Validation & Auto-Restore",
                version="1.0.0",
                category="quality",
                executable_path="scripts/safe_auto_fixer.py",
                make_command="quality-fix-safe",
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
        logger.info("Tool registry initialized with optimized BF Agent tools")


# Global registry instance
tool_registry = ToolRegistry()
