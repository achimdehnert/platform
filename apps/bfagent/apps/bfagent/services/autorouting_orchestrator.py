"""
Autorouting Orchestrator
========================

Haupt-Koordinator für das Autorouting/Autocoding-System.

Workflow:
    1. Requirement → AutocodingRun erstellen
    2. LLM analysiert den Task
    3. TaskExtractionService extrahiert Tasks
    4. LLMRouter entscheidet über Routing
    5. Tasks werden ausgeführt (Code → RefactorSessions)
    6. Ergebnisse werden zusammengeführt

Usage:
    from apps.bfagent.services.autorouting_orchestrator import AutoroutingOrchestrator
    
    orchestrator = AutoroutingOrchestrator()
    result = orchestrator.process_requirement(requirement, user)
    
    # Oder async
    result = await orchestrator.process_requirement_async(requirement, user)
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from django.utils import timezone

from .task_extraction import TaskExtractionService, ExtractedTask, ExtractionResult
from .llm_router import LLMRouter, RoutingDecision
from .code_refactor import CodeRefactorService
from .llm_client import LlmRequest, generate_text
from ..models_autocoding import AutocodingRun, ToolCall, Artifact

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AutoroutingResult:
    """Ergebnis eines Autorouting-Durchlaufs."""
    run: AutocodingRun
    sessions: List = field(default_factory=list)  # CodeRefactorSessions
    tasks_extracted: int = 0
    tasks_executed: int = 0
    success: bool = False
    error: str = ""
    
    @property
    def summary(self) -> Dict[str, Any]:
        return {
            'run_id': str(self.run.id),
            'status': self.run.status,
            'tasks_extracted': self.tasks_extracted,
            'tasks_executed': self.tasks_executed,
            'sessions_created': len(self.sessions),
            'success': self.success,
            'error': self.error,
            'total_tokens': self.run.total_tokens,
            'total_cost': float(self.run.total_cost),
        }


@dataclass
class AnalysisResult:
    """Ergebnis der LLM-Analyse."""
    response: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0
    llm_id: Optional[int] = None


# =============================================================================
# Autorouting Orchestrator
# =============================================================================

class AutoroutingOrchestrator:
    """
    Haupt-Koordinator für das Autorouting-System.
    
    Verbindet:
    - LLMRouter für intelligentes Routing
    - TaskExtractionService für Task-Parsing
    - CodeRefactorService für Code-Änderungen
    """
    
    # Prompt-Templates
    ANALYSIS_PROMPT = """Du bist ein erfahrener Software-Entwickler. Analysiere die folgende Anforderung und schlage konkrete Code-Änderungen vor.

## Anforderung
{requirement_text}

## Kontext
{context}

## Aufgabe
1. Analysiere die Anforderung
2. Identifiziere betroffene Dateien
3. Schlage konkrete Code-Änderungen vor

## Output-Format
Für jede Datei-Änderung:
```python
# apps/path/to/file.py
<vollständiger neuer Code>
```

Wichtig:
- Gib vollständige, lauffähige Code-Blöcke
- Beginne jeden Block mit dem Datei-Pfad als Kommentar
- Erkläre kurz vor jedem Block, was geändert wird
"""

    def __init__(self):
        self.router = LLMRouter()
        self.extractor = TaskExtractionService()
        self.refactor = CodeRefactorService()
    
    # =========================================================================
    # Main Entry Points
    # =========================================================================
    
    def process_requirement(
        self,
        requirement,
        user,
        llm_id: Optional[int] = None,
        max_iterations: int = 6
    ) -> AutoroutingResult:
        """
        Synchroner Haupteinstiegspunkt für Autorouting.
        
        Args:
            requirement: TestRequirement
            user: Django User
            llm_id: Optional - spezifisches LLM
            max_iterations: Max Iterationen
            
        Returns:
            AutoroutingResult
        """
        logger.info(f"[AUTOROUTING] Start für Requirement: {requirement.id}")
        
        # 1. Run erstellen
        run = self._create_run(requirement, user, max_iterations)
        
        try:
            # 2. Analyse Phase
            run.status = AutocodingRun.Status.ANALYZING
            run.save()
            
            analysis = self._analyze_requirement(requirement, run, llm_id)
            run.analysis_result = {'response': analysis.response[:5000]}
            run.add_tokens(analysis.tokens_input, analysis.tokens_output, analysis.cost)
            
            # 3. Planning Phase - Tasks extrahieren
            run.status = AutocodingRun.Status.PLANNING
            run.save()
            
            extraction = self.extractor.extract_tasks(analysis.response, requirement)
            tasks = extraction.tasks
            run.tasks_extracted = [
                {'type': t.type, 'file_path': t.file_path, 'complexity': t.complexity}
                for t in tasks
            ]
            run.save()
            
            logger.info(f"[AUTOROUTING] {len(tasks)} Tasks extrahiert")
            
            # 4. Execution Phase - RefactorSessions erstellen
            run.status = AutocodingRun.Status.EXECUTING
            run.save()
            
            sessions = self._execute_tasks(tasks, requirement, user, run)
            
            # 5. Review Phase
            run.status = AutocodingRun.Status.REVIEWING
            run.completed_at = timezone.now()
            run.save()
            
            logger.info(f"[AUTOROUTING] Erfolgreich: {len(sessions)} Sessions erstellt")
            
            return AutoroutingResult(
                run=run,
                sessions=sessions,
                tasks_extracted=len(tasks),
                tasks_executed=len(sessions),
                success=True
            )
            
        except Exception as e:
            logger.exception(f"[AUTOROUTING] Fehler: {e}")
            run.complete(success=False, error=str(e))
            
            return AutoroutingResult(
                run=run,
                success=False,
                error=str(e)
            )
    
    async def process_requirement_async(
        self,
        requirement,
        user,
        llm_id: Optional[int] = None,
        max_iterations: int = 6
    ) -> AutoroutingResult:
        """
        Asynchroner Haupteinstiegspunkt (für Celery/Background Tasks).
        """
        # TODO: Async LLM calls implementieren
        return self.process_requirement(requirement, user, llm_id, max_iterations)
    
    # =========================================================================
    # Internal Methods
    # =========================================================================
    
    def _create_run(
        self,
        requirement,
        user,
        max_iterations: int
    ) -> AutocodingRun:
        """Erstellt einen neuen AutocodingRun."""
        
        # Task-Text zusammenstellen
        task_text = self._build_task_text(requirement)
        
        # Komplexität schätzen
        complexity = self._estimate_complexity(requirement)
        
        run = AutocodingRun.objects.create(
            requirement=requirement,
            created_by=user,
            task_text=task_text,
            complexity=complexity,
            max_iterations=max_iterations,
            status=AutocodingRun.Status.CREATED,
            started_at=timezone.now()
        )
        
        logger.info(f"[AUTOROUTING] Run erstellt: {run.id}")
        return run
    
    def _build_task_text(self, requirement) -> str:
        """Baut den vollständigen Task-Text."""
        parts = [requirement.name]
        
        if requirement.description:
            parts.append(requirement.description)
        
        if hasattr(requirement, 'acceptance_criteria') and requirement.acceptance_criteria:
            parts.append(f"Akzeptanzkriterien:\n{requirement.acceptance_criteria}")
        
        return "\n\n".join(parts)
    
    def _estimate_complexity(self, requirement) -> str:
        """Schätzt die Komplexität basierend auf Requirement."""
        text_length = len(requirement.description or '') + len(requirement.name)
        
        if text_length < 200:
            return AutocodingRun.Complexity.SMALL
        elif text_length < 1000:
            return AutocodingRun.Complexity.MEDIUM
        else:
            return AutocodingRun.Complexity.LARGE
    
    def _analyze_requirement(
        self,
        requirement,
        run: AutocodingRun,
        llm_id: Optional[int] = None
    ) -> AnalysisResult:
        """
        Analysiert das Requirement mit LLM.
        """
        from ..models import Llms
        
        # Routing Decision
        if not llm_id:
            routing = self.router.get_routing_decision(
                complexity=run.complexity,
                task_type='code_generation'
            )
            llm_id = routing.llm_id
            run.routing_reason = routing.reason
            run.save()
        
        # LLM laden
        try:
            llm = Llms.objects.get(id=llm_id)
            run.llm = llm
            run.save()
        except Llms.DoesNotExist:
            llm = Llms.objects.filter(is_active=True).first()
            if llm:
                run.llm = llm
                run.save()
        
        # Kontext bauen
        context = self._build_context(requirement)
        
        # Prompt
        prompt = self.ANALYSIS_PROMPT.format(
            requirement_text=run.task_text,
            context=context
        )
        
        # LLM aufrufen
        logger.info(f"[AUTOROUTING] Rufe LLM auf: {llm.name if llm else 'default'}")
        
        result = generate_text(LlmRequest(
            provider=llm.provider or 'openai' if llm else 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com/v1/chat/completions' if llm else 'https://api.openai.com/v1/chat/completions',
            api_key=llm.api_key or '' if llm else '',
            model=llm.llm_name if llm else 'gpt-4o-mini',
            prompt=prompt,
            system="Du bist ein erfahrener Software-Entwickler. Analysiere das folgende Requirement und extrahiere konkrete Aufgaben.",
            max_tokens=4000,
            temperature=0.3
        ))
        
        response = result.get('text', '') if result.get('ok') else ''
        
        # ToolCall loggen
        ToolCall.objects.create(
            run=run,
            tool_name='llm.analyze',
            args_redacted={'llm_id': llm_id, 'prompt_length': len(prompt)},
            started_at=timezone.now(),
            ended_at=timezone.now(),
            ok=bool(response),
            stdout_redacted=response[:1000] if response else ''
        )
        
        return AnalysisResult(
            response=response or '',
            llm_id=llm_id
        )
    
    def _build_context(self, requirement) -> str:
        """Baut Kontext-Informationen für das LLM."""
        context_parts = []
        
        # Feature/Bug Info
        if hasattr(requirement, 'category') and requirement.category:
            context_parts.append(f"Kategorie: {requirement.category}")
        
        if hasattr(requirement, 'priority'):
            context_parts.append(f"Priorität: {requirement.priority}")
        
        # Projekt-Info
        context_parts.append("Projekt: BF Agent (Django)")
        context_parts.append("Python 3.11+, Django 5.x")
        
        return "\n".join(context_parts) if context_parts else "Keine zusätzlichen Kontext-Infos"
    
    def _execute_tasks(
        self,
        tasks: List[ExtractedTask],
        requirement,
        user,
        run: AutocodingRun
    ) -> List:
        """
        Führt die extrahierten Tasks aus.
        
        Für Code-Tasks: Erstellt CodeRefactorSessions
        """
        sessions = []
        
        for i, task in enumerate(tasks):
            logger.info(f"[AUTOROUTING] Task {i+1}/{len(tasks)}: {task.type} - {task.file_path}")
            
            if task.type in [ExtractedTask.TaskType.CODE_CHANGE, ExtractedTask.TaskType.FILE_CREATE]:
                session = self._execute_code_task(task, requirement, user, run)
                if session:
                    sessions.append(session)
                    
                    # Artifact erstellen
                    Artifact.objects.create(
                        run=run,
                        kind=Artifact.Kind.CODE_BLOCK,
                        file_path=task.file_path or 'unknown',
                        content=task.content or '',
                        refactor_session=session
                    )
            
            run.current_iteration = i + 1
            run.save()
        
        return sessions
    
    def _execute_code_task(
        self,
        task: ExtractedTask,
        requirement,
        user,
        run: AutocodingRun
    ):
        """
        Führt einen Code-Task aus.
        
        Erstellt eine CodeRefactorSession mit dem vorgeschlagenen Code.
        """
        from ..models_testing import CodeRefactorSession
        
        if not task.file_path:
            logger.warning(f"[AUTOROUTING] Task ohne file_path übersprungen")
            return None
        
        try:
            # Session erstellen
            session = self.refactor.create_session(
                requirement=requirement,
                file_path=task.file_path,
                instruction=task.instruction,
                user=user
            )
            
            # Wenn Content vorhanden, direkt setzen
            if task.content:
                session.proposed_content = task.content
                session.unified_diff = self.refactor._create_diff(
                    session.original_content,
                    task.content,
                    task.file_path
                )
                session.status = CodeRefactorSession.Status.PENDING_REVIEW
                session.save()
                
                logger.info(f"[AUTOROUTING] Session erstellt: {task.file_path}")
            
            return session
            
        except Exception as e:
            logger.error(f"[AUTOROUTING] Fehler bei Code-Task: {e}")
            return None
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Gibt den Status eines Runs zurück."""
        try:
            run = AutocodingRun.objects.get(id=run_id)
            return {
                'id': str(run.id),
                'status': run.status,
                'status_display': run.get_status_display(),
                'iteration': run.current_iteration,
                'max_iterations': run.max_iterations,
                'tokens': run.total_tokens,
                'cost': float(run.total_cost),
                'tool_calls': run.tool_calls.count(),
                'artifacts': run.artifacts.count(),
            }
        except AutocodingRun.DoesNotExist:
            return {'error': 'Run nicht gefunden'}
    
    def cancel_run(self, run_id: str) -> bool:
        """Bricht einen laufenden Run ab."""
        try:
            run = AutocodingRun.objects.get(id=run_id)
            if run.status in [AutocodingRun.Status.ANALYZING, 
                             AutocodingRun.Status.PLANNING,
                             AutocodingRun.Status.EXECUTING]:
                run.status = AutocodingRun.Status.CANCELLED
                run.completed_at = timezone.now()
                run.save()
                return True
            return False
        except AutocodingRun.DoesNotExist:
            return False


# =============================================================================
# Helper Functions
# =============================================================================

def start_autorouting(requirement_id: int, user_id: int, llm_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience-Funktion zum Starten eines Autorouting-Runs.
    
    Usage:
        from apps.bfagent.services.autorouting_orchestrator import start_autorouting
        result = start_autorouting(requirement_id=123, user_id=1)
    """
    from ..models_testing import TestRequirement
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        requirement = TestRequirement.objects.get(id=requirement_id)
        user = User.objects.get(id=user_id)
    except (TestRequirement.DoesNotExist, User.DoesNotExist) as e:
        return {'success': False, 'error': str(e)}
    
    orchestrator = AutoroutingOrchestrator()
    result = orchestrator.process_requirement(requirement, user, llm_id)
    
    return result.summary
