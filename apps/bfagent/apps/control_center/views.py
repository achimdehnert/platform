"""
BF Agent Control Center Views
Dashboard and API endpoints for tool management
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.genagent.core.handler_registry import HandlerRegistry

from .registry import tool_registry


def dashboard_home(request):
    """Main dashboard view - clean, organized Control Center"""
    from apps.bfagent.models import Llms, Agents
    
    # Get counts for dashboard
    try:
        llm_count = Llms.objects.filter(is_active=True).count()
        agent_count = Agents.objects.filter(status='active').count()
    except Exception:
        llm_count = 0
        agent_count = 0
    
    # MCP Server count
    try:
        from apps.mcp_hub.models import MCPServer
        mcp_server_count = MCPServer.objects.filter(is_enabled=True).count()
    except Exception:
        mcp_server_count = 0
    
    tool_count = len(tool_registry.tools)
    
    context = {
        "llm_count": llm_count,
        "agent_count": agent_count,
        "mcp_server_count": mcp_server_count,
        "tool_count": tool_count,
        "workflow_count": 0,
        "page_title": "Control Center",
    }

    return render(request, "control_center/dashboard_new.html", context)


def api_status(request):
    """API endpoint for system status"""
    return JsonResponse(tool_registry.get_system_health())


def api_tools(request):
    """API endpoint for tool listing"""
    category = request.GET.get("category")
    tools = tool_registry.list_tools(category=category)

    tools_data = []
    for tool in tools:
        tool_data = {
            "name": tool.name,
            "description": tool.description,
            "version": tool.version,
            "category": tool.category,
            "status": {
                "status": tool.status.status,
                "last_run": tool.status.last_run.isoformat() if tool.status.last_run else None,
                "execution_count": tool.status.execution_count,
                "success_rate": tool.status.success_rate,
                "average_duration": tool.status.average_duration,
                "error_message": tool.status.error_message,
            },
        }
        tools_data.append(tool_data)

    return JsonResponse({"tools": tools_data})


def api_tool_detail(request, tool_name):
    """API endpoint for individual tool details"""
    tool = tool_registry.get_tool(tool_name)
    if not tool:
        return JsonResponse({"error": "Tool not found"}, status=404)

    tool_data = {
        "name": tool.name,
        "description": tool.description,
        "version": tool.version,
        "category": tool.category,
        "executable_path": tool.executable_path,
        "make_command": tool.make_command,
        "api_endpoint": tool.api_endpoint,
        "status": {
            "status": tool.status.status,
            "last_run": tool.status.last_run.isoformat() if tool.status.last_run else None,
            "last_result": tool.status.last_result,
            "execution_count": tool.status.execution_count,
            "success_rate": tool.status.success_rate,
            "average_duration": tool.status.average_duration,
            "error_message": tool.status.error_message,
        },
    }

    return JsonResponse(tool_data)


@csrf_exempt
@require_http_methods(["POST"])
def api_tool_execute(request, tool_name):
    """API endpoint to execute a tool"""
    tool = tool_registry.get_tool(tool_name)
    if not tool:
        return JsonResponse({"error": "Tool not found"}, status=404)

    try:
        # Parse request parameters
        if request.content_type == "application/json":
            params = json.loads(request.body.decode("utf-8"))
        else:
            params = dict(request.POST.items())

        # Execute tool
        result = tool_registry.execute_tool(tool_name, **params)

        return JsonResponse(
            {
                "success": True,
                "tool": tool_name,
                "result": result,
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e), "tool": tool_name}, status=500)


def api_workflows(request):
    """API endpoint for workflow management"""
    # Placeholder for workflow system
    workflows = [
        {
            "id": "daily-quality-check",
            "name": "Daily Quality Check",
            "description": "Run all quality tools daily",
            "schedule": "0 9 * * *",
            "steps": [
                {"tool": "htmx_scanner_v2", "params": {"format": "json"}},
                {"tool": "migration_fixer", "params": {"diagnose": True}},
                {"tool": "v2_validator", "params": {}},
            ],
            "last_run": None,
            "status": "scheduled",
        },
        {
            "id": "auto-fix-workflow",
            "name": "Auto-Fix Critical Issues",
            "description": "Automatically fix critical issues when detected",
            "trigger": "event:critical_issue_detected",
            "steps": [
                {"tool": "htmx_scanner_v2", "params": {"fix": True}},
                {"tool": "csrf_auto_setup", "params": {}},
            ],
            "last_run": None,
            "status": "active",
        },
    ]

    return JsonResponse({"workflows": workflows})


class ToolExecutionView(View):
    """HTMX-enabled tool execution view"""

    def post(self, request, tool_name):
        """Execute tool and return HTMX partial"""
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            return HttpResponse('<div class="alert alert-danger">Tool not found</div>', status=404)

        try:
            # Get parameters from form
            params = {}
            if request.POST.get("format"):
                params["format"] = request.POST.get("format")
            if request.POST.get("fix") == "on":
                params["fix"] = True
            if request.POST.get("dry_run") == "on":
                params["dry_run"] = True

            # Execute tool
            result = tool_registry.execute_tool(tool_name, **params)

            # Return success partial
            context = {
                "tool": tool,
                "result": result,
                "success": result.get("success", True),
                "executed_at": datetime.now(timezone.utc),
            }

            return render(request, "control_center/partials/tool_result.html", context)

        except Exception as e:
            # Return error partial
            context = {"tool": tool, "error": str(e), "executed_at": datetime.now(timezone.utc)}

            return render(request, "control_center/partials/tool_error.html", context)


def system_metrics(request):
    """System metrics view for monitoring"""
    system_health = tool_registry.get_system_health()

    # Calculate additional metrics
    tools = list(tool_registry.tools.values())
    total_executions = sum(t.status.execution_count for t in tools)
    avg_success_rate = sum(t.status.success_rate for t in tools) / len(tools) if tools else 0

    metrics = {
        "system_health": system_health,
        "total_executions": total_executions,
        "average_success_rate": avg_success_rate,
        "tools_by_category": {
            "quality": len([t for t in tools if t.category == "quality"]),
            "database": len([t for t in tools if t.category == "database"]),
            "ai": len([t for t in tools if t.category == "ai"]),
            "frontend": len([t for t in tools if t.category == "frontend"]),
        },
    }

    if request.headers.get("Accept") == "application/json":
        return JsonResponse(metrics)

    return render(request, "control_center/metrics.html", {"metrics": metrics})


def tool_logs(request, tool_name):
    """View tool execution logs"""
    tool = tool_registry.get_tool(tool_name)
    if not tool:
        return JsonResponse({"error": "Tool not found"}, status=404)

    # Placeholder for log system
    logs = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "message": f"{tool_name} executed successfully",
            "duration": tool.status.average_duration,
        }
    ]

    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"logs": logs})

    context = {"tool": tool, "logs": logs}

    return render(request, "control_center/tool_logs.html", context)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def model_consistency_dashboard(request):
    """Model Consistency Checker Dashboard"""
    if request.method == "POST":
        # Execute model consistency check
        action = request.POST.get("action", "analyze")
        app_name = request.POST.get("app", "bfagent")

        try:
            # Run the enhanced model consistency checker
            cmd = ["python", "scripts/model_consistency_checker_V2.py", action, "--app", app_name]

            if action == "report":
                output_file = (
                    f"reports/model_consistency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                )
                cmd.extend(["--output", output_file])

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent
            )

            return JsonResponse(
                {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr,
                    "action": action,
                    "app": app_name,
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": str(e), "action": action, "app": app_name}
            )

    # GET request - show dashboard
    context = {
        "page_title": "Model Consistency Dashboard",
        "available_apps": ["bfagent"],  # Could be dynamic
        "available_actions": [
            {
                "value": "analyze",
                "label": "Analyze Consistency",
                "description": "Check model-template-form consistency",
            },
            {
                "value": "report",
                "label": "Generate Report",
                "description": "Create detailed consistency report",
            },
            {
                "value": "fix",
                "label": "Auto-Fix Issues",
                "description": "Automatically fix detected issues",
            },
        ],
    }

    return render(request, "control_center/model_consistency_dashboard.html", context)


@require_http_methods(["GET"])
def screen_documentation_dashboard(request):
    """Sphinx Documentation Dashboard - Redirects to built Sphinx docs"""
    from django.conf import settings
    
    # Sphinx docs location - check both possible paths
    docs_dir = Path(settings.BASE_DIR) / "docs" / "build" / "html"
    if not docs_dir.exists():
        docs_dir = Path(settings.BASE_DIR) / "docs" / "_build" / "html"
    docs_available = docs_dir.exists() and (docs_dir / "index.html").exists()
    
    # Documentation sections for quick access
    doc_sections = [
        {
            "title": "MCP Server",
            "icon": "bi-plug",
            "color": "primary",
            "items": [
                {"name": "Übersicht", "path": "mcp/index.html"},
                {"name": "BFAgent MCP", "path": "mcp/bfagent_mcp.html"},
                {"name": "Database MCP", "path": "mcp/bfagent_db_mcp.html"},
                {"name": "Code Quality MCP", "path": "mcp/code_quality_mcp.html"},
                {"name": "Test Generator MCP", "path": "mcp/test_generator_mcp.html"},
                {"name": "Deployment MCP", "path": "mcp/deployment_mcp.html"},
            ]
        },
        {
            "title": "Hubs",
            "icon": "bi-grid-3x3-gap",
            "color": "success",
            "items": [
                {"name": "Hub Übersicht", "path": "hubs/index.html"},
                {"name": "Writing Hub", "path": "hubs/writing_hub.html"},
                {"name": "CAD Hub", "path": "hubs/cad_hub.html"},
                {"name": "Control Center", "path": "hubs/control_center.html"},
                {"name": "DLM Hub", "path": "hubs/dlm_hub.html"},
            ]
        },
        {
            "title": "Guides",
            "icon": "bi-book",
            "color": "info",
            "items": [
                {"name": "Session Handling", "path": "guides/session_handling_controlling.html"},
                {"name": "AI Integration", "path": "guides/ai-integration.html"},
                {"name": "Quickstart", "path": "guides/quickstart.html"},
            ]
        },
    ]
    
    context = {
        "page_title": "Sphinx Documentation",
        "docs_available": docs_available,
        "docs_path": "/static/docs/" if docs_available else None,
        "doc_sections": doc_sections,
        "build_command": "cd docs && make html",
    }
    
    return render(request, "control_center/sphinx_documentation_dashboard.html", context)


# ============================================================================
# GENAGENT VIEWS
# ============================================================================


def genagent_dashboard(request):
    """GenAgent implementation dashboard"""

    # Get handler registry stats
    registry_stats = HandlerRegistry.get_registry_stats()

    # Phase 1 features status
    phase1_features = [
        {
            "name": "Handler Registry",
            "status": "complete",
            "progress": 100,
            "tests_passed": 23,
            "tests_total": 23,
            "time_spent": "4h",
            "completion_date": "2025-01-19",
        },
        {
            "name": "ACID Transactions",
            "status": "todo",
            "progress": 0,
            "tests_passed": 0,
            "tests_total": 0,
            "time_spent": "0h",
            "estimated_time": "20h",
        },
        {
            "name": "Context Isolation",
            "status": "todo",
            "progress": 0,
            "tests_passed": 0,
            "tests_total": 0,
            "time_spent": "0h",
            "estimated_time": "16h",
        },
        {
            "name": "Pydantic Schemas",
            "status": "todo",
            "progress": 0,
            "tests_passed": 0,
            "tests_total": 0,
            "time_spent": "0h",
            "estimated_time": "24h",
        },
        {
            "name": "Migration System",
            "status": "todo",
            "progress": 0,
            "tests_passed": 0,
            "tests_total": 0,
            "time_spent": "0h",
            "estimated_time": "20h",
        },
    ]

    # Calculate overall progress
    total_features = len(phase1_features)
    completed_features = sum(1 for f in phase1_features if f["status"] == "complete")
    overall_progress = int((completed_features / total_features) * 100)

    context = {
        "registry_stats": registry_stats,
        "phase1_features": phase1_features,
        "overall_progress": overall_progress,
        "completed_features": completed_features,
        "total_features": total_features,
        "page_title": "GenAgent Implementation Dashboard",
    }

    return render(request, "control_center/genagent_dashboard.html", context)


def genagent_status_api(request):
    """API endpoint for GenAgent status"""

    registry_stats = HandlerRegistry.get_registry_stats()

    return JsonResponse(
        {
            "phase1_progress": 20,  # 1/5 features complete
            "features_complete": 1,
            "features_total": 5,
            "tests_passed": 23,
            "tests_total": 23,
            "registry_stats": registry_stats,
            "status": "in_progress",
        }
    )


def genagent_feature_status(request):
    """HTMX partial for feature status widget"""

    phase1_features = [
        {
            "id": 1,
            "name": "Handler Registry",
            "status": "complete",
            "icon": "check-circle-fill",
            "color": "success",
        },
        {
            "id": 2,
            "name": "ACID Transactions",
            "status": "in_progress",
            "icon": "hourglass-split",
            "color": "warning",
        },
        {
            "id": 3,
            "name": "Context Isolation",
            "status": "todo",
            "icon": "circle",
            "color": "secondary",
        },
        {
            "id": 4,
            "name": "Pydantic Schemas",
            "status": "todo",
            "icon": "circle",
            "color": "secondary",
        },
        {
            "id": 5,
            "name": "Migration System",
            "status": "todo",
            "icon": "circle",
            "color": "secondary",
        },
    ]

    context = {"features": phase1_features, "progress": 20}

    return render(request, "control_center/partials/genagent_status.html", context)


# ============================================================================
# NAVIGATION API
# ============================================================================


@require_http_methods(["POST"])
@csrf_exempt
def toggle_section_collapse(request):
    """
    Toggle navigation section collapse state for user.

    This is a placeholder API endpoint that returns success.
    The actual collapse state can be stored in user session or database.
    """
    section_code = request.POST.get("section_code")

    # For now, just return success
    # TODO: Store collapse state in UserNavigationPreference model

    return JsonResponse(
        {
            "success": True,
            "section_code": section_code,
            "message": "Section toggle recorded (placeholder)",
        }
    )


@login_required
def data_sources_config(request):
    """
    Data Sources Configuration page.

    Placeholder view for data sources management.
    TODO: Implement actual data sources configuration.
    """
    return render(
        request,
        "control_center/data_sources_config.html",
        {
            "title": "Data Sources Configuration",
            "message": "Data sources configuration coming soon...",
        },
    )


# =============================================================================
# N8N WORKFLOW INTEGRATION
# =============================================================================

@login_required
def n8n_workflows(request):
    """n8n Workflow Designer embedded view."""
    from django.conf import settings
    import requests
    
    n8n_base_url = getattr(settings, 'N8N_BASE_URL', 'https://n8n.srv1154685.hstgr.cloud')
    n8n_api_key = getattr(settings, 'N8N_API_KEY', '')
    
    # Try to fetch workflows from n8n API
    workflows = []
    if n8n_api_key:
        try:
            headers = {'X-N8N-API-KEY': n8n_api_key}
            response = requests.get(
                f"{n8n_base_url}/api/v1/workflows",
                headers=headers,
                timeout=5
            )
            if response.ok:
                data = response.json()
                workflows = data.get('data', [])
        except Exception:
            pass
    
    return render(request, 'control_center/n8n_workflows.html', {
        'n8n_base_url': n8n_base_url,
        'workflows': workflows,
    })


@login_required
@require_http_methods(["POST"])
def n8n_execute_workflow(request):
    """Execute an n8n workflow via API."""
    from django.conf import settings
    import requests
    
    try:
        data = json.loads(request.body)
        workflow_id = data.get('workflow_id')
        
        if not workflow_id:
            return JsonResponse({'success': False, 'error': 'workflow_id required'}, status=400)
        
        n8n_base_url = getattr(settings, 'N8N_BASE_URL', '')
        n8n_api_key = getattr(settings, 'N8N_API_KEY', '')
        
        if not n8n_api_key:
            return JsonResponse({'success': False, 'error': 'N8N_API_KEY not configured'}, status=500)
        
        headers = {'X-N8N-API-KEY': n8n_api_key}
        response = requests.post(
            f"{n8n_base_url}/api/v1/workflows/{workflow_id}/execute",
            headers=headers,
            timeout=30
        )
        
        if response.ok:
            result = response.json()
            return JsonResponse({
                'success': True,
                'execution_id': result.get('data', {}).get('executionId'),
                'status': result.get('data', {}).get('status')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f"n8n API error: {response.status_code}"
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def progress_dashboard(request):
    """Progress Dashboard - Live-Status aller Requirements und MCP Nutzung"""
    from django.db.models import Count, Q
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        from apps.bfagent.models_testing import TestRequirement, RequirementFeedback, MCPUsageLog
        
        # Stats by status
        status_counts = TestRequirement.objects.values('status').annotate(count=Count('id'))
        stats = {
            'draft': 0,
            'ready': 0,
            'in_progress': 0,
            'blocked': 0,
            'done': 0,
            'completed': 0,
            'total': 0
        }
        for item in status_counts:
            if item['status'] in stats:
                stats[item['status']] = item['count']
            stats['total'] += item['count']
        
        # Active requirements (not done/archived)
        active_requirements = TestRequirement.objects.exclude(
            status__in=['done', 'completed', 'archived', 'obsolete']
        ).select_related('initiative', 'depends_on').order_by('-updated_at')[:15]
        
        # Recent feedback
        recent_feedback = RequirementFeedback.objects.select_related(
            'requirement'
        ).order_by('-created_at')[:10]
        
        # MCP Stats (last 24h)
        last_24h = timezone.now() - timedelta(hours=24)
        mcp_logs_24h = MCPUsageLog.objects.filter(created_at__gte=last_24h)
        
        total_calls = mcp_logs_24h.count()
        success_count = mcp_logs_24h.filter(status='success').count()
        error_count = mcp_logs_24h.filter(status='error').count()
        
        mcp_stats = {
            'total_calls': total_calls,
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': (success_count / total_calls * 100) if total_calls > 0 else 0
        }
        
        # Recent MCP logs
        mcp_logs = MCPUsageLog.objects.order_by('-created_at')[:10]
        
    except Exception as e:
        # Fallback if models don't exist
        stats = {'draft': 0, 'ready': 0, 'in_progress': 0, 'blocked': 0, 'done': 0, 'completed': 0, 'total': 0}
        active_requirements = []
        recent_feedback = []
        mcp_stats = None
        mcp_logs = []
    
    context = {
        'stats': stats,
        'active_requirements': active_requirements,
        'recent_feedback': recent_feedback,
        'mcp_stats': mcp_stats,
        'mcp_logs': mcp_logs,
        'page_title': 'Progress Dashboard',
    }
    
    return render(request, 'control_center/progress_dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def ki_auto_loesen(request):
    """
    KI Auto-Lösen Endpoint für Control Center.
    Delegiert an den Autorouting-Service.
    """
    import json
    from apps.bfagent.services.autorouting_orchestrator import AutoroutingOrchestrator
    from apps.bfagent.models_testing import TestRequirement
    
    try:
        data = json.loads(request.body) if request.body else {}
        requirement_id = data.get('requirement_id')
        llm_id = data.get('llm_id')
        
        if not requirement_id:
            return JsonResponse({
                'success': False,
                'error': 'requirement_id ist erforderlich'
            }, status=400)
        
        requirement = TestRequirement.objects.get(pk=requirement_id)
        
        orchestrator = AutoroutingOrchestrator()
        result = orchestrator.process_requirement(
            requirement=requirement,
            user=request.user,
            llm_id=llm_id
        )
        
        return JsonResponse({
            'success': result.success,
            'run_id': str(result.run.id) if result.run else None,
            'tasks_extracted': result.tasks_extracted,
            'sessions_created': len(result.sessions),
            'status': result.run.status if result.run else 'failed',
            'error': result.error
        })
        
    except TestRequirement.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Requirement {requirement_id} nicht gefunden'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
