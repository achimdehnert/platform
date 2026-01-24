"""
Django Shell Tool for BF Agent MCP.

Executes Django shell commands cleanly without hanging.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..server import mcp, logger


def _get_project_root() -> Path:
    """Find Django project root."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "manage.py").exists():
            return parent
    return Path.cwd()


@mcp.tool()
def django_shell_exec(
    code: str,
    timeout: int = 30,
) -> dict:
    """
    Führt Python-Code in der Django Shell aus.
    
    Nutzt Pipe statt -c für saubere Terminierung.
    
    Args:
        code: Python-Code zum Ausführen (kann mehrzeilig sein)
        timeout: Timeout in Sekunden (default: 30)
        
    Returns:
        Dict mit stdout, stderr, success
        
    Example:
        django_shell_exec("from apps.bfagent.models import LLMUsageLog; print(LLMUsageLog.objects.count())")
    """
    logger.info(f"Executing Django shell code ({len(code)} chars)")
    
    root = _get_project_root()
    
    # Ensure code ends with newline
    if not code.endswith("\n"):
        code += "\n"
    
    try:
        # Use echo pipe for clean execution
        result = subprocess.run(
            [sys.executable, "manage.py", "shell"],
            input=code,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(root),
            env={
                **dict(subprocess.os.environ),
                "PYTHONIOENCODING": "utf-8",
            }
        )
        
        # Clean output (remove Django shell noise)
        stdout = result.stdout
        stderr = result.stderr
        
        # Remove common Django startup messages
        noise_patterns = [
            "Using PostgreSQL",
            "Loaded DEVELOPMENT",
            "Core services registered",
            "Registered InputHandlerRegistry",
            "Registered ProcessingHandlerRegistry", 
            "Registered OutputHandlerRegistry",
            "Registered tool:",
            "Tool registry initialized",
            "GenAgent handlers registered",
            "Registered handler",
            "Initialized HandlerRegistry",
            "objects imported automatically",
            "Connecting to PostgreSQL",
            "LEKTORAT VIEWS LOADED",
            "Registry initialized",
        ]
        
        clean_lines = []
        for line in stdout.split("\n"):
            if not any(p in line for p in noise_patterns):
                # Also skip SQL debug output
                if not line.strip().startswith("(0."):
                    clean_lines.append(line)
        
        clean_stdout = "\n".join(clean_lines).strip()
        
        return {
            "success": result.returncode == 0,
            "output": clean_stdout,
            "errors": stderr.strip() if stderr.strip() else None,
            "return_code": result.returncode,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": None,
            "errors": f"Timeout nach {timeout} Sekunden",
            "return_code": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "errors": str(e),
            "return_code": -1,
        }


@mcp.tool()
def django_query(
    model: str,
    action: str = "count",
    filter_kwargs: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Führt eine Django ORM Query aus.
    
    Args:
        model: Model-Pfad (z.B. "apps.bfagent.models_controlling.LLMUsageLog")
        action: "count", "first", "last", "all", "filter"
        filter_kwargs: Filter-Argumente als Dict (z.B. {"task__contains": "code"})
        limit: Limit für "all" und "filter" (default: 10)
        
    Returns:
        Dict mit Ergebnis
        
    Example:
        django_query("apps.bfagent.models_controlling.LLMUsageLog", "count")
        django_query("apps.bfagent.models_controlling.LLMUsageLog", "filter", {"success": False}, 5)
    """
    logger.info(f"Django query: {model}.{action}")
    
    # Build code
    module_path, model_name = model.rsplit(".", 1)
    
    code = f"from {module_path} import {model_name}\n"
    
    if action == "count":
        code += f"print({model_name}.objects.count())"
    elif action == "first":
        code += f"obj = {model_name}.objects.first()\nprint(repr(obj))"
    elif action == "last":
        code += f"obj = {model_name}.objects.last()\nprint(repr(obj))"
    elif action == "all":
        code += f"for obj in {model_name}.objects.all()[:{limit}]: print(repr(obj))"
    elif action == "filter" and filter_kwargs:
        filter_str = ", ".join(f"{k}={repr(v)}" for k, v in filter_kwargs.items())
        code += f"for obj in {model_name}.objects.filter({filter_str})[:{limit}]: print(repr(obj))"
    else:
        return {"success": False, "error": f"Unknown action: {action}"}
    
    return django_shell_exec(code)
