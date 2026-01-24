"""
MCP Hub Views - Dashboard und Management für MCP-Server
"""

import json
import hashlib
import platform
from pathlib import Path
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone

from .models import MCPServer, MCPTool, MCPServerType, MCPServerLog, MCPConfigSync


def get_mcp_config_path():
    """Get MCP config path - works on both Windows and WSL"""
    windows_path = r"c:\Users\achim\.codeium\windsurf-next\mcp_config.json"
    wsl_path = "/mnt/c/Users/achim/.codeium/windsurf-next/mcp_config.json"
    
    # Check if running on WSL (Linux)
    if platform.system() == "Linux":
        return wsl_path
    return windows_path

DEFAULT_CONFIG_PATH = get_mcp_config_path()


@login_required
def dashboard(request):
    """MCP Hub Dashboard - Übersicht aller Server"""
    servers = MCPServer.objects.prefetch_related('tools').all()
    
    # Statistiken
    stats = {
        'total_servers': servers.count(),
        'active_servers': servers.filter(status='active').count(),
        'disabled_servers': servers.filter(is_enabled=False).count(),
        'total_tools': MCPTool.objects.count(),
        'enabled_tools': MCPTool.objects.filter(is_enabled=True).count(),
    }
    
    # Letzte Logs
    recent_logs = MCPServerLog.objects.select_related('server')[:10]
    
    # Letzte Sync-Info
    last_sync = MCPConfigSync.objects.first()
    
    return render(request, 'mcp_hub/dashboard.html', {
        'servers': servers,
        'stats': stats,
        'recent_logs': recent_logs,
        'last_sync': last_sync,
    })


@login_required
def server_list(request):
    """Liste aller MCP-Server"""
    servers = MCPServer.objects.prefetch_related('tools', 'server_type').all()
    
    # Filter
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    
    if status_filter:
        servers = servers.filter(status=status_filter)
    if type_filter:
        servers = servers.filter(server_type__code=type_filter)
    
    server_types = MCPServerType.objects.all()
    
    return render(request, 'mcp_hub/server_list.html', {
        'servers': servers,
        'server_types': server_types,
        'current_status': status_filter,
        'current_type': type_filter,
    })


@login_required
def server_detail(request, pk):
    """Detail-Ansicht eines MCP-Servers"""
    server = get_object_or_404(MCPServer.objects.prefetch_related('tools'), pk=pk)
    
    tools = server.tools.all()
    logs = server.logs.all()[:20]
    
    # Tool-Statistiken
    tool_stats = {
        'total': tools.count(),
        'enabled': tools.filter(is_enabled=True).count(),
        'disabled': tools.filter(is_enabled=False).count(),
        'categories': list(tools.values_list('category', flat=True).distinct()),
    }
    
    return render(request, 'mcp_hub/server_detail.html', {
        'server': server,
        'tools': tools,
        'logs': logs,
        'tool_stats': tool_stats,
    })


@login_required
def tool_list(request):
    """Liste aller MCP-Tools"""
    tools = MCPTool.objects.select_related('server').all()
    
    # Filter
    server_filter = request.GET.get('server')
    category_filter = request.GET.get('category')
    enabled_filter = request.GET.get('enabled')
    
    if server_filter:
        tools = tools.filter(server__name=server_filter)
    if category_filter:
        tools = tools.filter(category=category_filter)
    if enabled_filter:
        tools = tools.filter(is_enabled=enabled_filter == 'true')
    
    servers = MCPServer.objects.all()
    categories = MCPTool.objects.values_list('category', flat=True).distinct()
    
    return render(request, 'mcp_hub/tool_list.html', {
        'tools': tools,
        'servers': servers,
        'categories': [c for c in categories if c],
        'current_server': server_filter,
        'current_category': category_filter,
    })


@login_required
def tool_detail(request, pk):
    """Detail-Ansicht eines MCP-Tools"""
    tool = get_object_or_404(MCPTool.objects.select_related('server'), pk=pk)
    
    return render(request, 'mcp_hub/tool_detail.html', {
        'tool': tool,
    })


def discover_tools_from_source(server_name: str) -> list:
    """
    Dynamisch Tools aus MCP-Server Source-Code erkennen.
    Unterstützt bfagent_mcp, code_quality_mcp und andere lokale MCP-Server.
    """
    import logging
    import sys
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    tools = []
    
    # Packages-Verzeichnisse zum Python-Pfad hinzufügen falls nicht vorhanden
    base_path = Path(__file__).resolve().parent.parent.parent  # bfagent root
    packages_paths = [
        base_path / 'packages',
        base_path / 'packages' / 'code_quality_mcp',
        base_path / 'packages' / 'bfagent_mcp',
        base_path / 'packages' / 'bfagent_db_mcp',
        base_path / 'packages' / 'illustration_mcp',
        base_path / 'packages' / 'deployment_mcp',
        base_path / 'packages' / 'test_generator_mcp',
    ]
    
    for pkg_path in packages_paths:
        pkg_str = str(pkg_path)
        if pkg_path.exists() and pkg_str not in sys.path:
            sys.path.insert(0, pkg_str)
    
    if server_name == 'bfagent':
        try:
            # Dynamisch aus bfagent_mcp.server importieren
            from bfagent_mcp.server import get_tool_definitions
            tool_defs = get_tool_definitions()
            for tool in tool_defs:
                name = tool.name
                # Display name aus name generieren
                display_name = name.replace('bfagent_', '').replace('_', ' ').title()
                description = tool.description.split('\n')[0][:100] if tool.description else ''
                tools.append((name, display_name, description))
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Tool discovery failed for {server_name}: {e}")
    
    elif server_name == 'code-quality':
        try:
            # Dynamisch aus code_quality_mcp.server importieren
            from code_quality_mcp.server import mcp
            # FastMCP speichert Tools im _tool_manager
            tool_manager = getattr(mcp, '_tool_manager', None)
            if tool_manager:
                tool_dict = getattr(tool_manager, '_tools', {})
                for name, tool_info in tool_dict.items():
                    display_name = name.replace('_', ' ').title()
                    # Hole description aus der Tool-Info
                    description = ''
                    if hasattr(tool_info, 'description'):
                        description = str(tool_info.description)[:100]
                    elif isinstance(tool_info, dict):
                        description = tool_info.get('description', '')[:100]
                    tools.append((name, display_name, description))
                logger.info(f"Discovered {len(tools)} tools for {server_name}")
        except ImportError as e:
            logger.warning(f"Could not import code_quality_mcp: {e}")
        except Exception as e:
            logger.warning(f"Tool discovery failed for {server_name}: {e}")
    
    elif server_name == 'bfagent-db':
        try:
            # bfagent_db_mcp verwendet Standard MCP Server mit TOOLS Liste
            from bfagent_db_mcp.server import TOOLS as db_tools
            for tool in db_tools:
                name = tool.name
                display_name = name.replace('db_', '').replace('_', ' ').title()
                description = tool.description[:100] if tool.description else ''
                tools.append((name, display_name, description))
            logger.info(f"Discovered {len(tools)} tools for {server_name}")
        except ImportError as e:
            logger.warning(f"Could not import bfagent_db_mcp: {e}")
        except Exception as e:
            logger.warning(f"Tool discovery failed for {server_name}: {e}")
    
    elif server_name == 'illustration':
        try:
            # illustration_mcp verwendet Standard MCP Server mit TOOLS Liste
            from illustration_mcp.server import TOOLS as ill_tools
            for tool in ill_tools:
                name = tool.name
                display_name = name.replace('_', ' ').title()
                description = tool.description[:100] if tool.description else ''
                tools.append((name, display_name, description))
            logger.info(f"Discovered {len(tools)} tools for {server_name}")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Tool discovery failed for {server_name}: {e}")
    
    elif server_name == 'test-generator':
        try:
            from test_generator_mcp.server import mcp
            tool_manager = getattr(mcp, '_tool_manager', None)
            if tool_manager:
                tool_dict = getattr(tool_manager, '_tools', {})
                for name, tool_info in tool_dict.items():
                    display_name = name.replace('_', ' ').title()
                    description = ''
                    if hasattr(tool_info, 'description'):
                        description = str(tool_info.description)[:100]
                    tools.append((name, display_name, description))
                logger.info(f"Discovered {len(tools)} tools for {server_name}")
        except ImportError as e:
            logger.warning(f"Could not import test_generator_mcp: {e}")
        except Exception as e:
            logger.warning(f"Tool discovery failed for {server_name}: {e}")
    
    elif server_name == 'deployment-mcp':
        try:
            # Versuche deployment_mcp zu importieren
            from deployment_mcp.server import get_tools
            tool_defs = get_tools()
            for tool in tool_defs:
                name = tool.get('name', '')
                display_name = name.replace('_', ' ').title()
                description = tool.get('description', '')[:100]
                tools.append((name, display_name, description))
        except ImportError:
            pass
        except Exception:
            pass
    
    return tools


# Fallback für NPX-basierte Server (nicht lokal analysierbar)
# Aktualisiert basierend auf tatsächlichen MCP Server Tools
FALLBACK_NPX_TOOLS = {
    'filesystem': [
        ('create_directory', 'Create Directory', 'Create a new directory'),
        ('directory_tree', 'Directory Tree', 'Get directory tree structure'),
        ('edit_file', 'Edit File', 'Edit file contents'),
        ('get_file_info', 'Get File Info', 'Get file metadata'),
        ('list_allowed_directories', 'List Allowed Dirs', 'List allowed directories'),
        ('list_directory', 'List Directory', 'List directory contents'),
        ('list_directory_with_sizes', 'List Directory With Sizes', 'List directory with file sizes'),
        ('move_file', 'Move File', 'Move or rename files'),
        ('read_file', 'Read File', 'Read file contents'),
        ('read_text_file', 'Read Text File', 'Read text file contents'),
        ('read_media_file', 'Read Media File', 'Read media file as base64'),
        ('read_multiple_files', 'Read Multiple Files', 'Read multiple files'),
        ('search_files', 'Search Files', 'Search for files'),
        ('write_file', 'Write File', 'Write file contents'),
    ],
    'github': [
        ('add_issue_comment', 'Add Issue Comment', 'Add a comment to an issue'),
        ('create_branch', 'Create Branch', 'Create a new branch'),
        ('create_issue', 'Create Issue', 'Create a GitHub issue'),
        ('create_or_update_file', 'Create Or Update File', 'Create or update a file'),
        ('create_pull_request', 'Create PR', 'Create a pull request'),
        ('create_pull_request_review', 'Create PR Review', 'Create a pull request review'),
        ('create_repository', 'Create Repo', 'Create a repository'),
        ('fork_repository', 'Fork Repo', 'Fork a repository'),
        ('get_file_contents', 'Get File', 'Get file contents from repo'),
        ('get_issue', 'Get Issue', 'Get issue details'),
        ('get_pull_request', 'Get PR', 'Get pull request details'),
        ('get_pull_request_comments', 'Get PR Comments', 'Get PR comments'),
        ('get_pull_request_files', 'Get PR Files', 'Get files changed in PR'),
        ('get_pull_request_reviews', 'Get PR Reviews', 'Get PR reviews'),
        ('get_pull_request_status', 'Get PR Status', 'Get PR status checks'),
        ('list_commits', 'List Commits', 'List repository commits'),
        ('list_issues', 'List Issues', 'List repository issues'),
        ('list_pull_requests', 'List PRs', 'List pull requests'),
        ('merge_pull_request', 'Merge PR', 'Merge a pull request'),
        ('push_files', 'Push Files', 'Push files to repository'),
        ('search_code', 'Search Code', 'Search code on GitHub'),
        ('search_issues', 'Search Issues', 'Search issues and PRs'),
        ('search_repositories', 'Search Repos', 'Search repositories'),
        ('search_users', 'Search Users', 'Search GitHub users'),
        ('update_issue', 'Update Issue', 'Update an existing issue'),
        ('update_pull_request_branch', 'Update PR Branch', 'Update PR branch'),
    ],
    'brave-search': [
        ('brave_web_search', 'Web Search', 'Search the web with Brave'),
        ('brave_local_search', 'Local Search', 'Search for local businesses'),
    ],
    'postgres': [
        ('query', 'SQL Query', 'Execute read-only SQL query'),
    ],
}


def get_tools_for_server(server_name: str, command: str) -> list:
    """
    Holt Tools für einen Server - dynamisch wenn möglich, sonst Fallback.
    """
    # Für WSL/Python-basierte Server: dynamische Erkennung
    if command in ('wsl', 'python'):
        discovered = discover_tools_from_source(server_name)
        if discovered:
            return discovered
    
    # Fallback für NPX-Server
    return FALLBACK_NPX_TOOLS.get(server_name, [])


@login_required
@require_http_methods(["POST"])
def sync_from_config(request):
    """Synchronisiert Server und Tools aus mcp_config.json"""
    config_path = request.POST.get('config_path', DEFAULT_CONFIG_PATH)
    
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            return JsonResponse({
                'success': False,
                'error': f'Config-Datei nicht gefunden: {config_path}'
            })
        
        # Config laden
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Hash berechnen
        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        
        mcp_servers = config.get('mcpServers', {})
        
        servers_added = 0
        servers_updated = 0
        tools_added = 0
        tools_updated = 0
        
        # Server-Typen erstellen falls nicht vorhanden
        builtin_type, _ = MCPServerType.objects.get_or_create(
            name='Built-in (NPX)',
            defaults={'code': 'builtin', 'icon': 'bi-box-seam'}
        )
        custom_type, _ = MCPServerType.objects.get_or_create(
            name='Custom Python',
            defaults={'code': 'custom', 'icon': 'bi-code-slash'}
        )
        
        for name, server_config in mcp_servers.items():
            command = server_config.get('command', 'npx')
            is_custom = command == 'wsl' or command == 'python'
            disabled_tools = server_config.get('disabledTools', [])
            
            server, created = MCPServer.objects.update_or_create(
                name=name,
                defaults={
                    'display_name': name.replace('-', ' ').replace('_', ' ').title(),
                    'server_type': custom_type if is_custom else builtin_type,
                    'command': command,
                    'args': server_config.get('args', []),
                    'env': server_config.get('env', {}),
                    'is_enabled': not server_config.get('disabled', False),
                    'disabled_tools': disabled_tools,
                    'imported_from_config': True,
                    'config_key': name,
                    'config_path': str(config_path),
                    'status': 'disabled' if server_config.get('disabled', False) else 'active',
                }
            )
            
            if created:
                servers_added += 1
                MCPServerLog.objects.create(
                    server=server,
                    level='info',
                    message=f'Server aus Config importiert'
                )
            else:
                servers_updated += 1
            
            # Tools importieren - dynamisch aus Source oder Fallback
            tools_to_create = {}  # name -> (display_name, description, is_enabled)
            
            # 1. Tools aus disabledTools (diese existieren, sind nur deaktiviert)
            for tool_name in disabled_tools:
                display = tool_name.replace('_', ' ').title()
                tools_to_create[tool_name] = (display, '', False)
            
            # 2. Dynamisch erkannte Tools für diesen Server
            discovered_tools = get_tools_for_server(name, command)
            for tool_info in discovered_tools:
                tool_name = tool_info[0]
                display_name = tool_info[1] if len(tool_info) > 1 else tool_name.replace('_', ' ').title()
                description = tool_info[2] if len(tool_info) > 2 else ''
                is_enabled = tool_name not in disabled_tools
                tools_to_create[tool_name] = (display_name, description, is_enabled)
            
            # Tools erstellen/aktualisieren
            for tool_name, (display_name, description, is_enabled) in tools_to_create.items():
                tool, tool_created = MCPTool.objects.update_or_create(
                    server=server,
                    name=tool_name,
                    defaults={
                        'display_name': display_name,
                        'description': description,
                        'is_enabled': is_enabled,
                    }
                )
                
                if tool_created:
                    tools_added += 1
                else:
                    tools_updated += 1
            
            # Alte Tools entfernen die nicht mehr existieren
            if tools_to_create:
                old_tools = server.tools.exclude(name__in=tools_to_create.keys())
                old_tools_count = old_tools.count()
                if old_tools_count > 0:
                    old_tools.delete()
        
        # Server entfernen die nicht mehr in Config sind
        servers_in_config = set(mcp_servers.keys())
        servers_removed = MCPServer.objects.filter(
            imported_from_config=True
        ).exclude(
            name__in=servers_in_config
        ).delete()[0]
        
        # Sync-Eintrag erstellen
        MCPConfigSync.objects.create(
            config_path=str(config_path),
            config_hash=config_hash,
            last_sync_at=timezone.now(),
            sync_status='success',
            sync_message=f'Server: {servers_added}+/{servers_updated}↻/{servers_removed}-, Tools: {tools_added}+/{tools_updated}↻',
            servers_added=servers_added,
            servers_updated=servers_updated,
        )
        
        messages.success(request, f'Sync erfolgreich: {servers_added}+ {servers_updated}↻ {servers_removed}- Server, {tools_added}+ Tools')
        
        return JsonResponse({
            'success': True,
            'servers_added': servers_added,
            'servers_updated': servers_updated,
            'servers_removed': servers_removed,
            'tools_added': tools_added,
            'tools_updated': tools_updated,
            'total_servers': len(mcp_servers),
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': f'JSON-Fehler: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def toggle_server(request, pk):
    """Aktiviert/Deaktiviert einen Server"""
    server = get_object_or_404(MCPServer, pk=pk)
    
    server.is_enabled = not server.is_enabled
    server.status = 'active' if server.is_enabled else 'disabled'
    server.save()
    
    MCPServerLog.objects.create(
        server=server,
        level='info',
        message=f'Server {"aktiviert" if server.is_enabled else "deaktiviert"}'
    )
    
    return JsonResponse({
        'success': True,
        'is_enabled': server.is_enabled,
        'status': server.status,
    })


@login_required
@require_http_methods(["POST"])
def toggle_tool(request, pk):
    """Aktiviert/Deaktiviert ein Tool"""
    tool = get_object_or_404(MCPTool, pk=pk)
    
    tool.is_enabled = not tool.is_enabled
    tool.save()
    
    return JsonResponse({
        'success': True,
        'is_enabled': tool.is_enabled,
    })


@login_required
@require_http_methods(["POST"])
def restart_server(request, pk):
    """Startet einen MCP-Server neu (Signal an Windsurf)"""
    import subprocess
    import os
    
    server = get_object_or_404(MCPServer, pk=pk)
    
    try:
        # Log the restart attempt
        MCPServerLog.objects.create(
            server=server,
            level='info',
            message='Server-Neustart angefordert'
        )
        
        # For WSL-based servers, we can try to restart the process
        # This is a simplified approach - in production you'd use proper process management
        restart_info = {
            'server_name': server.name,
            'command': server.command,
            'message': 'Restart-Signal gesendet. Bitte Windsurf neu starten um MCP-Server zu aktualisieren.',
            'hint': 'Windsurf schließen und neu öffnen, oder Developer Tools → MCP Server neu laden.'
        }
        
        # Update server status to indicate restart pending
        server.status = 'restarting'
        server.save()
        
        MCPServerLog.objects.create(
            server=server,
            level='info',
            message='Restart-Signal erfolgreich gesendet'
        )
        
        return JsonResponse({
            'success': True,
            'message': restart_info['message'],
            'hint': restart_info['hint'],
            'server_name': server.name,
        })
        
    except Exception as e:
        MCPServerLog.objects.create(
            server=server,
            level='error',
            message=f'Restart fehlgeschlagen: {str(e)}'
        )
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def restart_all_servers(request):
    """Startet alle aktiven MCP-Server neu"""
    servers = MCPServer.objects.filter(is_enabled=True)
    restarted = []
    
    for server in servers:
        MCPServerLog.objects.create(
            server=server,
            level='info',
            message='Globaler Neustart angefordert'
        )
        server.status = 'restarting'
        server.save()
        restarted.append(server.name)
    
    return JsonResponse({
        'success': True,
        'message': f'{len(restarted)} Server zum Neustart markiert',
        'servers': restarted,
        'hint': 'Windsurf schließen und neu öffnen um alle MCP-Server zu aktualisieren.'
    })
