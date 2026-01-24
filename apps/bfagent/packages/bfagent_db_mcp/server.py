"""
BF Agent Database MCP Server
============================

Extended PostgreSQL MCP Server with Django integration.

Tools:
- db_list_tables: List all tables with row counts
- db_describe_table: Show columns, types, FKs, indexes
- db_django_models: List Django models with fields
- db_migration_status: Show Django migration status
- db_analyze_query: EXPLAIN ANALYZE for query optimization
- db_table_stats: Row count, size, vacuum info
- db_execute_query: Safe parameterized query execution
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bfagent_db_mcp")

# Django setup
def setup_django():
    """Initialize Django settings"""
    project_root = os.environ.get("BFAGENT_PROJECT_ROOT", "/home/dehnert/github/bfagent")
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    
    import django
    django.setup()

# Initialize Django
try:
    setup_django()
    DJANGO_AVAILABLE = True
except Exception as e:
    logger.warning(f"Django setup failed: {e}")
    DJANGO_AVAILABLE = False


def get_db_connection():
    """Get database connection from Django"""
    from django.db import connection
    return connection


# =============================================================================
# DATABASE TOOLS
# =============================================================================

def db_list_tables(schema: str = "public") -> Dict[str, Any]:
    """List all tables with row counts"""
    conn = get_db_connection()
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                t.table_name,
                COALESCE(s.n_live_tup, 0) as row_count,
                pg_size_pretty(pg_total_relation_size(quote_ident(t.table_name))) as total_size
            FROM information_schema.tables t
            LEFT JOIN pg_stat_user_tables s ON t.table_name = s.relname
            WHERE t.table_schema = %s
            AND t.table_type = 'BASE TABLE'
            ORDER BY COALESCE(s.n_live_tup, 0) DESC
        """, [schema])
        
        tables = []
        for row in cursor.fetchall():
            tables.append({
                "name": row[0],
                "row_count": row[1],
                "size": row[2]
            })
    
    return {
        "schema": schema,
        "table_count": len(tables),
        "tables": tables
    }


def db_describe_table(table_name: str) -> Dict[str, Any]:
    """Show columns, types, FKs, indexes for a table"""
    conn = get_db_connection()
    
    result = {
        "table": table_name,
        "columns": [],
        "indexes": [],
        "foreign_keys": [],
        "primary_key": None
    }
    
    with conn.cursor() as cursor:
        # Get columns
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, [table_name])
        
        for row in cursor.fetchall():
            col_type = row[1]
            if row[4]:  # max length
                col_type = f"{col_type}({row[4]})"
            
            result["columns"].append({
                "name": row[0],
                "type": col_type,
                "nullable": row[2] == "YES",
                "default": row[3]
            })
        
        # Get indexes
        cursor.execute("""
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = %s
        """, [table_name])
        
        for row in cursor.fetchall():
            result["indexes"].append({
                "name": row[0],
                "definition": row[1]
            })
        
        # Get foreign keys
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = %s
        """, [table_name])
        
        for row in cursor.fetchall():
            result["foreign_keys"].append({
                "column": row[0],
                "references": f"{row[1]}.{row[2]}"
            })
        
        # Get primary key
        cursor.execute("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
            AND tc.table_name = %s
        """, [table_name])
        
        pk_row = cursor.fetchone()
        if pk_row:
            result["primary_key"] = pk_row[0]
    
    return result


def db_django_models(app_label: Optional[str] = None) -> Dict[str, Any]:
    """List Django models with fields and relations"""
    from django.apps import apps
    
    result = {"apps": []}
    
    app_configs = apps.get_app_configs()
    
    for app_config in app_configs:
        # Filter by app_label if specified
        if app_label and app_config.label != app_label:
            continue
        
        # Skip Django internal apps unless explicitly requested
        if not app_label and app_config.name.startswith(('django.', 'rest_framework', 'corsheaders')):
            continue
        
        app_data = {
            "label": app_config.label,
            "name": app_config.name,
            "models": []
        }
        
        for model in app_config.get_models():
            model_data = {
                "name": model.__name__,
                "db_table": model._meta.db_table,
                "fields": [],
                "relations": []
            }
            
            for field in model._meta.get_fields():
                field_info = {
                    "name": field.name,
                    "type": field.__class__.__name__,
                }
                
                if hasattr(field, 'related_model') and field.related_model:
                    field_info["related_to"] = field.related_model.__name__
                    model_data["relations"].append(field_info)
                else:
                    model_data["fields"].append(field_info)
            
            app_data["models"].append(model_data)
        
        if app_data["models"]:  # Only include apps with models
            result["apps"].append(app_data)
    
    return result


def db_migration_status(app_label: Optional[str] = None) -> Dict[str, Any]:
    """Show Django migration status per app"""
    from django.db.migrations.recorder import MigrationRecorder
    from django.db import connection
    
    recorder = MigrationRecorder(connection)
    applied = recorder.applied_migrations()
    
    # Group by app
    apps_status = {}
    for (app, name) in applied:
        if app_label and app != app_label:
            continue
        if app not in apps_status:
            apps_status[app] = []
        apps_status[app].append(name)
    
    result = {
        "total_migrations": len(applied),
        "apps": []
    }
    
    for app, migrations in sorted(apps_status.items()):
        result["apps"].append({
            "app": app,
            "migration_count": len(migrations),
            "latest": migrations[-1] if migrations else None
        })
    
    return result


def db_analyze_query(sql: str) -> Dict[str, Any]:
    """EXPLAIN ANALYZE for query optimization"""
    conn = get_db_connection()
    
    # Only allow SELECT queries for safety
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return {"error": "Only SELECT queries can be analyzed"}
    
    with conn.cursor() as cursor:
        cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
        result = cursor.fetchone()[0]
    
    plan = result[0] if result else {}
    
    return {
        "query": sql,
        "execution_time_ms": plan.get("Execution Time", 0),
        "planning_time_ms": plan.get("Planning Time", 0),
        "plan": plan.get("Plan", {})
    }


def db_table_stats(table_name: str) -> Dict[str, Any]:
    """Get detailed statistics for a table"""
    conn = get_db_connection()
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                relname as table_name,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze,
                pg_size_pretty(pg_total_relation_size(quote_ident(relname))) as total_size,
                pg_size_pretty(pg_table_size(quote_ident(relname))) as table_size,
                pg_size_pretty(pg_indexes_size(quote_ident(relname))) as index_size
            FROM pg_stat_user_tables
            WHERE relname = %s
        """, [table_name])
        
        row = cursor.fetchone()
        if not row:
            return {"error": f"Table '{table_name}' not found"}
        
        return {
            "table": row[0],
            "live_rows": row[1],
            "dead_rows": row[2],
            "last_vacuum": str(row[3]) if row[3] else None,
            "last_autovacuum": str(row[4]) if row[4] else None,
            "last_analyze": str(row[5]) if row[5] else None,
            "last_autoanalyze": str(row[6]) if row[6] else None,
            "total_size": row[7],
            "table_size": row[8],
            "index_size": row[9]
        }


def db_execute_query(sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Execute a safe parameterized query (SELECT only)"""
    conn = get_db_connection()
    
    # Only allow SELECT queries for safety
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed. Use Django admin for modifications."}
    
    with conn.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    
    # Limit results
    max_rows = 100
    truncated = len(rows) > max_rows
    
    return {
        "columns": columns,
        "rows": [dict(zip(columns, row)) for row in rows[:max_rows]],
        "row_count": len(rows),
        "truncated": truncated,
        "max_rows": max_rows if truncated else None
    }


def db_search_tables(pattern: str) -> Dict[str, Any]:
    """Search for tables by name pattern"""
    conn = get_db_connection()
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                table_name,
                COALESCE(
                    (SELECT n_live_tup FROM pg_stat_user_tables WHERE relname = table_name),
                    0
                ) as row_count
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            AND table_name ILIKE %s
            ORDER BY table_name
        """, [f"%{pattern}%"])
        
        tables = [{"name": row[0], "row_count": row[1]} for row in cursor.fetchall()]
    
    return {
        "pattern": pattern,
        "matches": len(tables),
        "tables": tables
    }


# =============================================================================
# MCP SERVER SETUP
# =============================================================================

server = Server("bfagent-db-mcp")

TOOLS = [
    Tool(
        name="db_list_tables",
        description="List all database tables with row counts and sizes. Use schema parameter to filter (default: public).",
        inputSchema={
            "type": "object",
            "properties": {
                "schema": {
                    "type": "string",
                    "description": "Database schema (default: public)",
                    "default": "public"
                }
            }
        }
    ),
    Tool(
        name="db_describe_table",
        description="Show detailed table structure: columns, types, indexes, foreign keys, primary key.",
        inputSchema={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table to describe"
                }
            },
            "required": ["table_name"]
        }
    ),
    Tool(
        name="db_django_models",
        description="List Django models with fields and relations. Filter by app_label or get all apps.",
        inputSchema={
            "type": "object",
            "properties": {
                "app_label": {
                    "type": "string",
                    "description": "Django app label to filter (e.g., 'bfagent', 'writing_hub')"
                }
            }
        }
    ),
    Tool(
        name="db_migration_status",
        description="Show Django migration status for all apps or a specific app.",
        inputSchema={
            "type": "object",
            "properties": {
                "app_label": {
                    "type": "string",
                    "description": "Django app label to filter"
                }
            }
        }
    ),
    Tool(
        name="db_analyze_query",
        description="Run EXPLAIN ANALYZE on a SELECT query to understand performance. Returns execution plan and timing.",
        inputSchema={
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SELECT query to analyze"
                }
            },
            "required": ["sql"]
        }
    ),
    Tool(
        name="db_table_stats",
        description="Get detailed statistics for a table: row counts, dead tuples, vacuum info, sizes.",
        inputSchema={
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table"
                }
            },
            "required": ["table_name"]
        }
    ),
    Tool(
        name="db_execute_query",
        description="Execute a safe parameterized SELECT query. Limited to 100 rows.",
        inputSchema={
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SELECT query to execute"
                },
                "params": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Query parameters for safe interpolation"
                }
            },
            "required": ["sql"]
        }
    ),
    Tool(
        name="db_search_tables",
        description="Search for tables by name pattern (case-insensitive LIKE search).",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (e.g., 'book', 'user', 'workflow')"
                }
            },
            "required": ["pattern"]
        }
    ),
]


@server.list_tools()
async def list_tools():
    """List available database tools"""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "db_list_tables":
            result = db_list_tables(arguments.get("schema", "public"))
        elif name == "db_describe_table":
            result = db_describe_table(arguments["table_name"])
        elif name == "db_django_models":
            result = db_django_models(arguments.get("app_label"))
        elif name == "db_migration_status":
            result = db_migration_status(arguments.get("app_label"))
        elif name == "db_analyze_query":
            result = db_analyze_query(arguments["sql"])
        elif name == "db_table_stats":
            result = db_table_stats(arguments["table_name"])
        elif name == "db_execute_query":
            result = db_execute_query(arguments["sql"], arguments.get("params"))
        elif name == "db_search_tables":
            result = db_search_tables(arguments["pattern"])
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
    
    except Exception as e:
        logger.exception(f"Error in tool {name}")
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


async def run_server():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point"""
    logger.info("Starting BF Agent Database MCP Server...")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
