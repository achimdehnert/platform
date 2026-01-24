# -*- coding: utf-8 -*-
"""
MCP Tools for Common Django Error Fixes.

Provides tools to fix common Django generation errors automatically.
"""
import logging
import re
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# Common error patterns and their fixes
COMMON_ERROR_FIXES = {
    # Import errors
    "import_missing_module": {
        "pattern": r"ModuleNotFoundError: No module named '([^']+)'",
        "fix_type": "import",
        "description": "Missing module import",
        "fix_template": "pip install {module}",
    },
    "import_circular": {
        "pattern": r"ImportError: cannot import name '([^']+)' from partially initialized module",
        "fix_type": "refactor",
        "description": "Circular import detected",
        "fix_template": "Move import inside function or use lazy import",
    },
    
    # View errors
    "view_missing_return": {
        "pattern": r"The view .* didn't return an HttpResponse",
        "fix_type": "code",
        "description": "View missing return statement",
        "fix_template": "return render(request, 'template.html', context)",
    },
    "view_missing_decorator": {
        "pattern": r"AttributeError: 'AnonymousUser' object has no attribute",
        "fix_type": "decorator",
        "description": "View missing login_required decorator",
        "fix_template": "@login_required\ndef {function_name}(request):",
    },
    
    # Template errors
    "template_missing_endblock": {
        "pattern": r"TemplateSyntaxError.*(Unclosed tag|Missing.*(endblock|endif|endfor))",
        "fix_type": "template",
        "description": "Missing endblock/endif/endfor tag",
        "fix_template": "{% end{tag} %}",
    },
    "template_variable_undefined": {
        "pattern": r"VariableDoesNotExist: Failed lookup for key \[([^\]]+)\]",
        "fix_type": "context",
        "description": "Template variable not in context",
        "fix_template": "context['{variable}'] = value",
    },
    "template_missing": {
        "pattern": r"TemplateDoesNotExist: ([^\s]+)",
        "fix_type": "file",
        "description": "Template file missing",
        "fix_template": "Create template at: {template_path}",
    },
    
    # URL errors
    "url_missing_name": {
        "pattern": r"NoReverseMatch: Reverse for '([^']+)' not found",
        "fix_type": "url",
        "description": "URL name not found",
        "fix_template": "path('route/', view, name='{url_name}')",
    },
    "url_missing_args": {
        "pattern": r"NoReverseMatch.*arguments '([^']+)'.*not found",
        "fix_type": "url",
        "description": "URL arguments mismatch",
        "fix_template": "{% url 'name' arg1 arg2 %}",
    },
    
    # Model errors  
    "model_field_missing": {
        "pattern": r"FieldError: Unknown field\(s\) \(([^)]+)\)",
        "fix_type": "model",
        "description": "Model field does not exist",
        "fix_template": "Check model definition or run migrations",
    },
    "model_migration_missing": {
        "pattern": r"django.db.utils.OperationalError: no such table: ([^\s]+)",
        "fix_type": "migration",
        "description": "Database table missing",
        "fix_template": "python manage.py makemigrations && python manage.py migrate",
    },
    
    # Form errors
    "form_field_required": {
        "pattern": r"This field is required",
        "fix_type": "form",
        "description": "Required form field missing",
        "fix_template": "field = forms.CharField(required=False)  # or provide value",
    },
    
    # Syntax errors
    "syntax_indentation": {
        "pattern": r"IndentationError: (unexpected indent|expected an indented block)",
        "fix_type": "syntax",
        "description": "Indentation error",
        "fix_template": "Fix indentation (use 4 spaces)",
    },
    "syntax_missing_colon": {
        "pattern": r"SyntaxError: expected ':'",
        "fix_type": "syntax",
        "description": "Missing colon after function/class definition",
        "fix_template": "def function_name():",
    },
}


# MCP Tool Definitions
ERROR_FIXER_TOOLS = [
    {
        "name": "django_error_analyze",
        "description": "Analyze a Django error and suggest fixes",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_message": {
                    "type": "string",
                    "description": "The error message to analyze"
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to the file where error occurred"
                },
                "code_snippet": {
                    "type": "string",
                    "description": "Code snippet around the error"
                },
            },
            "required": ["error_message"]
        }
    },
    {
        "name": "django_error_list_common",
        "description": "List common Django errors and their frequencies",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back",
                    "default": 30
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of errors to return",
                    "default": 20
                },
            }
        }
    },
    {
        "name": "django_error_fix_apply",
        "description": "Apply an automatic fix for a known error pattern",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_id": {
                    "type": "integer",
                    "description": "ID of the logged error to fix"
                },
                "pattern_name": {
                    "type": "string",
                    "description": "Name of the fix pattern to apply"
                },
            },
            "required": ["error_id"]
        }
    },
    {
        "name": "django_error_log",
        "description": "Log a Django generation error for tracking",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_type": {
                    "type": "string",
                    "enum": ["template", "view", "url", "model", "form", "import", "syntax", "migration", "admin", "serializer", "handler", "other"],
                    "description": "Type of Django error"
                },
                "error_message": {
                    "type": "string",
                    "description": "The error message"
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "line_number": {
                    "type": "integer",
                    "description": "Line number of error"
                },
                "code_snippet": {
                    "type": "string",
                    "description": "Relevant code snippet"
                },
                "auto_fixable": {
                    "type": "boolean",
                    "description": "Can this be auto-fixed?",
                    "default": False
                },
                "fix_suggestion": {
                    "type": "string",
                    "description": "Suggested fix"
                },
            },
            "required": ["error_type", "error_message"]
        }
    },
    {
        "name": "tool_usage_stats",
        "description": "Get tool and agent usage statistics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze",
                    "default": 30
                },
                "group_by": {
                    "type": "string",
                    "enum": ["tool", "caller", "app"],
                    "description": "How to group statistics",
                    "default": "tool"
                },
            }
        }
    },
    {
        "name": "tool_usage_log",
        "description": "Log a tool usage for tracking",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the tool"
                },
                "caller_type": {
                    "type": "string",
                    "enum": ["user", "cascade", "mcp", "api", "scheduled", "system"],
                    "description": "Type of caller",
                    "default": "cascade"
                },
                "app_label": {
                    "type": "string",
                    "description": "Django app label"
                },
                "execution_time_ms": {
                    "type": "number",
                    "description": "Execution time in milliseconds"
                },
                "success": {
                    "type": "boolean",
                    "description": "Was the operation successful?",
                    "default": True
                },
                "result_summary": {
                    "type": "string",
                    "description": "Brief summary of result"
                },
            },
            "required": ["tool_name"]
        }
    },
]


def analyze_error(error_message: str, file_path: str = None, code_snippet: str = None) -> Dict:
    """Analyze a Django error and suggest fixes."""
    result = {
        "error_message": error_message,
        "matched_patterns": [],
        "suggestions": [],
        "auto_fixable": False,
    }
    
    for pattern_name, pattern_info in COMMON_ERROR_FIXES.items():
        match = re.search(pattern_info["pattern"], error_message, re.IGNORECASE)
        if match:
            result["matched_patterns"].append({
                "name": pattern_name,
                "description": pattern_info["description"],
                "fix_type": pattern_info["fix_type"],
                "captured_groups": match.groups(),
            })
            
            # Generate fix suggestion
            fix = pattern_info["fix_template"]
            if match.groups():
                # Replace placeholders with captured groups
                for i, group in enumerate(match.groups()):
                    fix = fix.replace(f"{{{list(pattern_info.get('placeholders', {}).keys())[i] if pattern_info.get('placeholders') else 'match'}}}", group or "")
            
            result["suggestions"].append({
                "pattern": pattern_name,
                "fix": fix,
                "description": pattern_info["description"],
            })
            
            result["auto_fixable"] = pattern_info["fix_type"] in ["import", "syntax", "decorator"]
    
    if not result["matched_patterns"]:
        result["suggestions"].append({
            "pattern": "unknown",
            "fix": "Manual investigation required",
            "description": "No known pattern matched this error",
        })
    
    return result


def get_common_errors(days: int = 30, limit: int = 20) -> List[Dict]:
    """Get common errors from the database."""
    try:
        from ..models_usage_tracking import DjangoGenerationError
        return DjangoGenerationError.get_common_errors(days, limit)
    except Exception as e:
        logger.error(f"Failed to get common errors: {e}")
        return []


def apply_fix(error_id: int, pattern_name: str = None) -> Dict:
    """Apply a fix to an error."""
    try:
        from ..models_usage_tracking import DjangoGenerationError, ErrorFixPattern
        
        error = DjangoGenerationError.objects.get(id=error_id)
        
        # Find matching pattern
        if pattern_name:
            pattern = ErrorFixPattern.objects.filter(name=pattern_name).first()
        else:
            pattern = ErrorFixPattern.find_matching_pattern(error)
        
        if not pattern:
            # Try built-in patterns
            analysis = analyze_error(error.error_message)
            if analysis["suggestions"]:
                return {
                    "success": True,
                    "source": "builtin",
                    "fix": analysis["suggestions"][0]["fix"],
                    "description": analysis["suggestions"][0]["description"],
                }
            return {
                "success": False,
                "message": "No matching fix pattern found",
            }
        
        # Apply the pattern
        result = pattern.apply_fix(error)
        return result
        
    except DjangoGenerationError.DoesNotExist:
        return {"success": False, "message": f"Error {error_id} not found"}
    except Exception as e:
        logger.error(f"Failed to apply fix: {e}")
        return {"success": False, "message": str(e)}


# MCP Tool Handlers
async def handle_django_error_analyze(params: Dict) -> Dict:
    """Handle django_error_analyze tool call."""
    return analyze_error(
        error_message=params["error_message"],
        file_path=params.get("file_path"),
        code_snippet=params.get("code_snippet"),
    )


async def handle_django_error_list_common(params: Dict) -> Dict:
    """Handle django_error_list_common tool call."""
    days = params.get("days", 30)
    limit = params.get("limit", 20)
    errors = get_common_errors(days, limit)
    return {
        "period_days": days,
        "errors": errors,
        "count": len(errors),
    }


async def handle_django_error_fix_apply(params: Dict) -> Dict:
    """Handle django_error_fix_apply tool call."""
    return apply_fix(
        error_id=params["error_id"],
        pattern_name=params.get("pattern_name"),
    )


async def handle_django_error_log(params: Dict) -> Dict:
    """Handle django_error_log tool call."""
    from .usage_tracker import get_usage_tracker
    
    tracker = get_usage_tracker()
    error_id = tracker.log_django_error(
        error_type=params["error_type"],
        error_message=params["error_message"],
        file_path=params.get("file_path"),
        line_number=params.get("line_number"),
        code_snippet=params.get("code_snippet"),
        auto_fixable=params.get("auto_fixable", False),
        fix_suggestion=params.get("fix_suggestion"),
    )
    
    return {
        "success": error_id is not None,
        "error_id": error_id,
    }


async def handle_tool_usage_stats(params: Dict) -> Dict:
    """Handle tool_usage_stats tool call."""
    from .usage_tracker import get_usage_tracker
    
    tracker = get_usage_tracker()
    return tracker.get_usage_stats(days=params.get("days", 30))


async def handle_tool_usage_log(params: Dict) -> Dict:
    """Handle tool_usage_log tool call."""
    from .usage_tracker import get_usage_tracker
    
    tracker = get_usage_tracker()
    log_id = tracker.log_tool_usage(
        tool_name=params["tool_name"],
        caller_type=params.get("caller_type", "cascade"),
        app_label=params.get("app_label"),
        execution_time_ms=params.get("execution_time_ms", 0),
        success=params.get("success", True),
        result_summary=params.get("result_summary"),
    )
    
    return {
        "success": log_id is not None,
        "log_id": log_id,
    }


# Handler mapping
TOOL_HANDLERS = {
    "django_error_analyze": handle_django_error_analyze,
    "django_error_list_common": handle_django_error_list_common,
    "django_error_fix_apply": handle_django_error_fix_apply,
    "django_error_log": handle_django_error_log,
    "tool_usage_stats": handle_tool_usage_stats,
    "tool_usage_log": handle_tool_usage_log,
}


async def handle_tool_call(tool_name: str, params: Dict) -> Dict:
    """Handle a tool call."""
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}
    
    try:
        return await handler(params)
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"error": str(e)}


def get_error_fixer_tools() -> List[Dict]:
    """Get all error fixer tool definitions."""
    return ERROR_FIXER_TOOLS
