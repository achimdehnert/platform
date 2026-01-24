"""
Sandbox Executor für sichere Code-Ausführung
=============================================

Führt Code-Operationen in isolierten Docker-Containern aus.
Unterstützt: Build, Test, Lint, Format, Custom Commands.
"""

import os
import json
import uuid
import logging
import tempfile
import subprocess
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

SANDBOX_CONFIG = {
    'docker_image': 'python:3.11-slim',
    'timeout_seconds': 300,
    'memory_limit': '512m',
    'cpu_limit': '1.0',
    'network_mode': 'none',  # Kein Netzwerk für Sicherheit
    'workspace_mount': '/workspace',
    'allowed_commands': [
        'python', 'pip', 'pytest', 'black', 'ruff', 'mypy',
        'flake8', 'isort', 'pylint', 'coverage'
    ],
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ExecutionResult:
    """Ergebnis einer Sandbox-Ausführung."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    stdout_sha256: str = ''
    stderr_sha256: str = ''
    artifacts: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SandboxContext:
    """Kontext für Sandbox-Ausführung."""
    workspace_path: str
    run_id: str
    files_to_copy: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    timeout: int = 300
    memory_limit: str = '512m'


# =============================================================================
# Sandbox Executor
# =============================================================================

class SandboxExecutor:
    """
    Führt Befehle sicher in Docker-Containern aus.
    
    Features:
    - Isolierte Ausführung ohne Netzwerk
    - Resource-Limits (CPU, Memory)
    - Timeout-Handling
    - Artifact-Collection
    - SHA256 Hashes für Audit
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {**SANDBOX_CONFIG, **(config or {})}
        self._check_docker_available()
    
    def _check_docker_available(self):
        """Prüft ob Docker verfügbar ist."""
        try:
            result = subprocess.run(
                ['docker', 'version', '--format', '{{.Server.Version}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.warning("[SANDBOX] Docker nicht verfügbar")
                self._docker_available = False
            else:
                self._docker_available = True
                logger.info(f"[SANDBOX] Docker Version: {result.stdout.strip()}")
        except Exception as e:
            logger.warning(f"[SANDBOX] Docker Check fehlgeschlagen: {e}")
            self._docker_available = False
    
    @property
    def is_available(self) -> bool:
        """Ob Docker verfügbar ist."""
        return self._docker_available
    
    def execute(
        self,
        command: str,
        context: SandboxContext,
        capture_artifacts: bool = True
    ) -> ExecutionResult:
        """
        Führt einen Befehl in der Sandbox aus.
        
        Args:
            command: Auszuführender Befehl
            context: Sandbox-Kontext
            capture_artifacts: Ob Artifacts gesammelt werden sollen
            
        Returns:
            ExecutionResult
        """
        if not self._docker_available:
            return self._execute_local_fallback(command, context)
        
        start_time = datetime.now()
        
        try:
            # Validiere Command
            if not self._is_command_allowed(command):
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout='',
                    stderr=f'Befehl nicht erlaubt: {command.split()[0]}',
                    duration_ms=0,
                    error='Command not allowed'
                )
            
            # Docker Run Command bauen
            docker_cmd = self._build_docker_command(command, context)
            
            logger.info(f"[SANDBOX] Ausführen: {command[:100]}...")
            
            # Ausführen
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=context.timeout,
                cwd=context.workspace_path
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Artifacts sammeln
            artifacts = []
            if capture_artifacts:
                artifacts = self._collect_artifacts(context)
            
            return ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=duration_ms,
                stdout_sha256=self._sha256(result.stdout),
                stderr_sha256=self._sha256(result.stderr),
                artifacts=artifacts
            )
            
        except subprocess.TimeoutExpired:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout='',
                stderr='Timeout expired',
                duration_ms=duration_ms,
                error=f'Timeout nach {context.timeout}s'
            )
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.exception(f"[SANDBOX] Fehler: {e}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout='',
                stderr=str(e),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    def run_tests(self, context: SandboxContext, test_path: str = '') -> ExecutionResult:
        """Führt pytest in der Sandbox aus."""
        cmd = f"pytest {test_path} -v --tb=short" if test_path else "pytest -v --tb=short"
        return self.execute(cmd, context)
    
    def run_linter(self, context: SandboxContext, file_path: str = '.') -> ExecutionResult:
        """Führt Ruff Linter aus."""
        return self.execute(f"ruff check {file_path}", context)
    
    def run_formatter(self, context: SandboxContext, file_path: str = '.') -> ExecutionResult:
        """Führt Black Formatter aus (check mode)."""
        return self.execute(f"black --check {file_path}", context)
    
    def run_type_check(self, context: SandboxContext, file_path: str = '.') -> ExecutionResult:
        """Führt MyPy Type-Check aus."""
        return self.execute(f"mypy {file_path}", context)
    
    def _build_docker_command(self, command: str, context: SandboxContext) -> List[str]:
        """Baut den Docker-Befehl."""
        docker_cmd = [
            'docker', 'run',
            '--rm',
            '--network', self.config['network_mode'],
            '--memory', context.memory_limit or self.config['memory_limit'],
            '--cpus', self.config['cpu_limit'],
            '-v', f"{context.workspace_path}:{self.config['workspace_mount']}:rw",
            '-w', self.config['workspace_mount'],
        ]
        
        # Environment Variables
        for key, value in context.env_vars.items():
            docker_cmd.extend(['-e', f'{key}={value}'])
        
        # Image und Command
        docker_cmd.append(self.config['docker_image'])
        docker_cmd.extend(['sh', '-c', command])
        
        return docker_cmd
    
    def _is_command_allowed(self, command: str) -> bool:
        """Prüft ob der Befehl erlaubt ist."""
        if not command:
            return False
        
        first_word = command.split()[0]
        return first_word in self.config['allowed_commands']
    
    def _collect_artifacts(self, context: SandboxContext) -> List[str]:
        """Sammelt generierte Artifacts."""
        artifacts = []
        workspace = Path(context.workspace_path)
        
        # Coverage Reports
        coverage_file = workspace / '.coverage'
        if coverage_file.exists():
            artifacts.append(str(coverage_file))
        
        # Pytest Reports
        for report in workspace.glob('*.xml'):
            artifacts.append(str(report))
        
        return artifacts
    
    def _execute_local_fallback(self, command: str, context: SandboxContext) -> ExecutionResult:
        """Fallback für lokale Ausführung wenn Docker nicht verfügbar."""
        logger.warning("[SANDBOX] Docker nicht verfügbar, lokaler Fallback")
        
        if not self._is_command_allowed(command):
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout='',
                stderr=f'Befehl nicht erlaubt: {command.split()[0]}',
                duration_ms=0,
                error='Command not allowed'
            )
        
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=context.timeout,
                cwd=context.workspace_path,
                env={**os.environ, **context.env_vars}
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=duration_ms,
                stdout_sha256=self._sha256(result.stdout),
                stderr_sha256=self._sha256(result.stderr)
            )
            
        except subprocess.TimeoutExpired:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout='',
                stderr='Timeout expired',
                duration_ms=duration_ms,
                error=f'Timeout nach {context.timeout}s'
            )
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout='',
                stderr=str(e),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    @staticmethod
    def _sha256(content: str) -> str:
        """Berechnet SHA256 Hash."""
        return hashlib.sha256(content.encode()).hexdigest()


# =============================================================================
# Convenience Functions
# =============================================================================

def run_in_sandbox(
    command: str,
    workspace: str,
    timeout: int = 300
) -> ExecutionResult:
    """
    Convenience-Funktion für schnelle Sandbox-Ausführung.
    
    Example:
        result = run_in_sandbox("pytest tests/", "/path/to/project")
        if result.success:
            print("Tests passed!")
    """
    executor = SandboxExecutor()
    context = SandboxContext(
        workspace_path=workspace,
        run_id=str(uuid.uuid4()),
        timeout=timeout
    )
    return executor.execute(command, context)
