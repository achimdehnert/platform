# -*- coding: utf-8 -*-
"""
Git Operations MCP Tool.

Automatisiert Git-Operationen mit Tracking und Feedback.
"""
import os
import subprocess
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class GitOperationsTool:
    """MCP Tool für Git-Operationen mit Tracking."""
    
    TOOL_NAME = "git_operations"
    VERSION = "1.0.0"
    
    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or os.getcwd()
        self.operations_log: List[Dict] = []
    
    async def execute(self, action: str, **params) -> Dict[str, Any]:
        """Haupteinstiegspunkt für Git-Operationen."""
        actions = {
            'commit': self._commit,
            'push': self._push,
            'commit_and_push': self._commit_and_push,
            'status': self._status,
            'pull': self._pull,
            'branch': self._branch,
            'diff': self._diff,
            'log': self._log,
        }
        
        handler = actions.get(action)
        if not handler:
            return {
                'success': False,
                'error': f"Unknown action: {action}. Available: {list(actions.keys())}"
            }
        
        start_time = time.time()
        operation_id = f"git_{action}_{int(start_time * 1000)}"
        
        try:
            result = await handler(**params)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log operation
            log_entry = {
                'operation_id': operation_id,
                'action': action,
                'params': params,
                'success': result.get('success', False),
                'duration_ms': duration_ms,
                'timestamp': datetime.now().isoformat(),
                'repo_path': self.repo_path,
            }
            self.operations_log.append(log_entry)
            
            # Track to Django if available
            await self._track_to_django(log_entry)
            
            result['operation_id'] = operation_id
            result['duration_ms'] = duration_ms
            return result
            
        except Exception as e:
            logger.error(f"Git operation {action} failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation_id': operation_id,
                'duration_ms': int((time.time() - start_time) * 1000),
            }
    
    async def _commit(
        self,
        message: str,
        add_all: bool = True,
        files: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Git add + commit."""
        results = []
        
        # Stage files
        if add_all:
            add_result = self._run_git(['add', '-A'])
            results.append(('add -A', add_result))
        elif files:
            for f in files:
                add_result = self._run_git(['add', f])
                results.append((f'add {f}', add_result))
        
        # Check if there's anything to commit
        status = self._run_git(['status', '--porcelain'])
        if not status.get('output', '').strip():
            return {
                'success': True,
                'message': 'Nothing to commit',
                'committed': False,
            }
        
        # Commit
        commit_result = self._run_git(['commit', '-m', message])
        results.append(('commit', commit_result))
        
        if commit_result.get('returncode') != 0:
            return {
                'success': False,
                'error': commit_result.get('error', 'Commit failed'),
                'details': results,
            }
        
        # Extract commit hash
        commit_hash = self._get_last_commit_hash()
        
        return {
            'success': True,
            'message': 'Committed successfully',
            'committed': True,
            'commit_hash': commit_hash,
            'commit_message': message,
            'details': results,
        }
    
    async def _push(
        self,
        remote: str = 'origin',
        branch: str = None,
        force: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Git push."""
        cmd = ['push', remote]
        
        if branch:
            cmd.append(branch)
        
        if force:
            cmd.append('--force')
        
        result = self._run_git(cmd)
        
        if result.get('returncode') != 0:
            return {
                'success': False,
                'error': result.get('error', 'Push failed'),
                'output': result.get('output'),
            }
        
        return {
            'success': True,
            'message': f'Pushed to {remote}',
            'remote': remote,
            'branch': branch or self._get_current_branch(),
            'output': result.get('output'),
        }
    
    async def _commit_and_push(
        self,
        message: str,
        add_all: bool = True,
        files: List[str] = None,
        remote: str = 'origin',
        branch: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Kombiniert commit + push in einer Operation."""
        # Commit
        commit_result = await self._commit(
            message=message,
            add_all=add_all,
            files=files
        )
        
        if not commit_result.get('success'):
            return commit_result
        
        # Wenn nichts committed wurde, auch nicht pushen
        if not commit_result.get('committed'):
            return commit_result
        
        # Push
        push_result = await self._push(remote=remote, branch=branch)
        
        return {
            'success': push_result.get('success'),
            'commit': commit_result,
            'push': push_result,
            'commit_hash': commit_result.get('commit_hash'),
            'message': f"Committed and pushed: {commit_result.get('commit_hash', '')[:8]}",
        }
    
    async def _status(self, **kwargs) -> Dict[str, Any]:
        """Git status."""
        result = self._run_git(['status', '--short'])
        
        # Parse status
        lines = result.get('output', '').strip().split('\n')
        files = []
        for line in lines:
            if line.strip():
                status_code = line[:2]
                filename = line[3:]
                files.append({
                    'status': status_code.strip(),
                    'file': filename,
                })
        
        return {
            'success': True,
            'files': files,
            'file_count': len(files),
            'has_changes': len(files) > 0,
            'raw': result.get('output'),
        }
    
    async def _pull(
        self,
        remote: str = 'origin',
        branch: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Git pull."""
        cmd = ['pull', remote]
        if branch:
            cmd.append(branch)
        
        result = self._run_git(cmd)
        
        return {
            'success': result.get('returncode') == 0,
            'output': result.get('output'),
            'error': result.get('error') if result.get('returncode') != 0 else None,
        }
    
    async def _branch(
        self,
        action: str = 'list',  # list, create, delete, switch
        name: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Branch-Operationen."""
        if action == 'list':
            result = self._run_git(['branch', '-a'])
            branches = [b.strip().replace('* ', '') for b in result.get('output', '').split('\n') if b.strip()]
            current = self._get_current_branch()
            return {
                'success': True,
                'branches': branches,
                'current': current,
            }
        
        elif action == 'create' and name:
            result = self._run_git(['checkout', '-b', name])
            return {
                'success': result.get('returncode') == 0,
                'branch': name,
                'output': result.get('output'),
            }
        
        elif action == 'switch' and name:
            result = self._run_git(['checkout', name])
            return {
                'success': result.get('returncode') == 0,
                'branch': name,
                'output': result.get('output'),
            }
        
        return {'success': False, 'error': f'Invalid branch action: {action}'}
    
    async def _diff(
        self,
        staged: bool = False,
        file: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Git diff."""
        cmd = ['diff']
        if staged:
            cmd.append('--staged')
        if file:
            cmd.append(file)
        
        result = self._run_git(cmd)
        
        return {
            'success': True,
            'diff': result.get('output', ''),
            'has_changes': bool(result.get('output', '').strip()),
        }
    
    async def _log(
        self,
        count: int = 10,
        oneline: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Git log."""
        cmd = ['log', f'-{count}']
        if oneline:
            cmd.append('--oneline')
        
        result = self._run_git(cmd)
        
        commits = []
        for line in result.get('output', '').strip().split('\n'):
            if line.strip():
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    commits.append({
                        'hash': parts[0],
                        'message': parts[1],
                    })
        
        return {
            'success': True,
            'commits': commits,
            'count': len(commits),
        }
    
    def _run_git(self, args: List[str]) -> Dict[str, Any]:
        """Führt Git-Befehl aus."""
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                'returncode': result.returncode,
                'output': result.stdout,
                'error': result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                'returncode': -1,
                'output': '',
                'error': 'Command timed out',
            }
        except Exception as e:
            return {
                'returncode': -1,
                'output': '',
                'error': str(e),
            }
    
    def _get_current_branch(self) -> str:
        """Gibt aktuellen Branch-Namen zurück."""
        result = self._run_git(['rev-parse', '--abbrev-ref', 'HEAD'])
        return result.get('output', '').strip()
    
    def _get_last_commit_hash(self) -> str:
        """Gibt Hash des letzten Commits zurück."""
        result = self._run_git(['rev-parse', 'HEAD'])
        return result.get('output', '').strip()
    
    async def _track_to_django(self, log_entry: Dict) -> None:
        """Sendet Operation an Django für Tracking."""
        import os
        import aiohttp
        
        # Skip wenn tracking deaktiviert
        if os.environ.get('MCP_TRACKING_ENABLED', 'true').lower() == 'false':
            return
        
        api_url = os.environ.get(
            'MCP_TRACKING_URL',
            'http://localhost:8000/control-center/usage-tracking/api/log-tool/'
        )
        
        try:
            payload = {
                'tool_name': f"git_{log_entry['action']}",
                'caller_type': 'cascade',
                'caller_id': 'mcp_git_tool',
                'input_params': log_entry.get('params', {}),
                'execution_time_ms': log_entry.get('duration_ms', 0),
                'success': log_entry.get('success', False),
                'result_summary': log_entry.get('operation_id'),
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=5) as response:
                    pass  # Fire and forget
        except Exception as e:
            logger.debug(f"Could not track git operation: {e}")


# Tool-Registrierung für MCP Server
TOOL_DEFINITION = {
    "name": "bfagent_git",
    "description": """Git-Operationen mit automatischem Tracking.
    
Actions:
- commit: Stage und commit Änderungen
- push: Push zu Remote
- commit_and_push: Beides kombiniert
- status: Zeigt geänderte Dateien
- pull: Pull von Remote
- branch: Branch-Operationen (list, create, switch)
- diff: Zeigt Änderungen
- log: Zeigt Commit-Historie""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["commit", "push", "commit_and_push", "status", "pull", "branch", "diff", "log"],
                "description": "Git-Operation"
            },
            "message": {
                "type": "string",
                "description": "Commit-Message (für commit/commit_and_push)"
            },
            "add_all": {
                "type": "boolean",
                "default": True,
                "description": "Alle Änderungen stagen"
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Spezifische Dateien stagen"
            },
            "remote": {
                "type": "string",
                "default": "origin",
                "description": "Remote-Name"
            },
            "branch": {
                "type": "string",
                "description": "Branch-Name"
            },
            "repo_path": {
                "type": "string",
                "description": "Pfad zum Repository (optional)"
            }
        },
        "required": ["action"]
    }
}


async def handle_git_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handler für MCP Tool-Aufrufe."""
    action = params.pop('action', None)
    repo_path = params.pop('repo_path', None)
    
    if not action:
        return {'success': False, 'error': 'action is required'}
    
    tool = GitOperationsTool(repo_path=repo_path)
    return await tool.execute(action, **params)
