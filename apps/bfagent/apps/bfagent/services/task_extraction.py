"""
Task Extraction Service
========================

Extrahiert strukturierte Tasks aus LLM-Responses für das Autorouting-System.

Kernfunktion:
    LLM Response → [ExtractedTask, ...] → CodeRefactorSessions

Unterstützte Formate:
    1. JSON-Array mit Tasks (strukturiert)
    2. Markdown mit ```code``` Blöcken
    3. Inline-Code mit Datei-Referenzen

Usage:
    from apps.bfagent.services.task_extraction import TaskExtractionService
    
    extractor = TaskExtractionService()
    tasks = extractor.extract_tasks(llm_response, requirement)
    sessions = extractor.create_refactor_sessions(tasks, requirement, user)
"""

import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CodeBlock:
    """Ein extrahierter Code-Block aus LLM-Response."""
    language: str
    content: str
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    context: str = ""  # Umgebender Text/Instruktion


@dataclass
class ExtractedTask:
    """Ein extrahierter Task aus LLM-Response."""
    
    class TaskType:
        CODE_CHANGE = 'code_change'
        FILE_CREATE = 'file_create'
        FILE_DELETE = 'file_delete'
        COMMAND = 'command'
        ANALYSIS = 'analysis'
        DOCUMENTATION = 'documentation'
    
    type: str
    instruction: str
    file_path: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    complexity: str = 'low'  # low, medium, high
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Ergebnis der Task-Extraktion."""
    tasks: List[ExtractedTask]
    code_blocks: List[CodeBlock]
    raw_response: str
    extraction_method: str  # 'json', 'markdown', 'heuristic'
    confidence: float  # 0.0 - 1.0


# =============================================================================
# Task Extraction Service
# =============================================================================

class TaskExtractionService:
    """
    Haupt-Service für Task-Extraktion aus LLM-Responses.
    
    Brücke zwischen:
    - LLM-Antworten (unstrukturiert oder semi-strukturiert)
    - CodeRefactorSession (strukturierte Code-Änderungen)
    """
    
    # Regex-Patterns für Code-Block-Erkennung
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)?\s*\n(.*?)```',
        re.DOTALL
    )
    
    # Pattern für Datei-Referenzen
    FILE_REF_PATTERNS = [
        # # filename.py oder // filename.py am Anfang des Blocks
        re.compile(r'^[#/]+\s*(\S+\.\w+)\s*$', re.MULTILINE),
        # File: path/to/file.py
        re.compile(r'[Ff]ile:\s*[`"]?(\S+\.\w+)[`"]?'),
        # path/to/file.py: am Anfang
        re.compile(r'^(\S+/\S+\.\w+):?\s*$', re.MULTILINE),
        # In file `path/to/file.py`
        re.compile(r'[Ii]n\s+(?:file\s+)?[`"](\S+\.\w+)[`"]'),
    ]
    
    # Language → Extension Mapping
    LANG_EXTENSIONS = {
        'python': '.py',
        'py': '.py',
        'javascript': '.js',
        'js': '.js',
        'typescript': '.ts',
        'ts': '.ts',
        'html': '.html',
        'css': '.css',
        'json': '.json',
        'yaml': '.yaml',
        'yml': '.yml',
        'sql': '.sql',
        'bash': '.sh',
        'shell': '.sh',
        'dockerfile': 'Dockerfile',
    }
    
    def __init__(self):
        self.project_root = Path.cwd()
    
    # =========================================================================
    # Main Extraction Methods
    # =========================================================================
    
    def extract_tasks(
        self, 
        llm_response: str, 
        requirement=None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extrahiert Tasks aus einer LLM-Response.
        
        Args:
            llm_response: Die rohe LLM-Antwort
            requirement: Optional - das zugehörige TestRequirement
            context: Optional - zusätzlicher Kontext (z.B. Datei-Hints)
            
        Returns:
            ExtractionResult mit Tasks und Code-Blöcken
        """
        logger.info("[TASK-EXTRACT] Starte Extraktion aus LLM-Response")
        
        tasks = []
        code_blocks = []
        extraction_method = 'heuristic'
        confidence = 0.5
        
        # 1. Versuche JSON-Format zu parsen
        json_tasks = self._extract_json_tasks(llm_response)
        if json_tasks:
            tasks.extend(json_tasks)
            extraction_method = 'json'
            confidence = 0.9
            logger.info(f"[TASK-EXTRACT] {len(json_tasks)} Tasks aus JSON extrahiert")
        
        # 2. Extrahiere Code-Blöcke
        code_blocks = self._extract_code_blocks(llm_response, context)
        logger.info(f"[TASK-EXTRACT] {len(code_blocks)} Code-Blöcke gefunden")
        
        # 3. Konvertiere Code-Blöcke zu Tasks (wenn nicht schon aus JSON)
        if not json_tasks:
            for block in code_blocks:
                task = self._code_block_to_task(block)
                if task:
                    tasks.append(task)
            if tasks:
                extraction_method = 'markdown'
                confidence = 0.7
        
        # 4. Dedupliziere Tasks
        tasks = self._deduplicate_tasks(tasks)
        
        logger.info(f"[TASK-EXTRACT] Ergebnis: {len(tasks)} Tasks, Methode: {extraction_method}")
        
        return ExtractionResult(
            tasks=tasks,
            code_blocks=code_blocks,
            raw_response=llm_response,
            extraction_method=extraction_method,
            confidence=confidence
        )
    
    # =========================================================================
    # JSON Task Extraction
    # =========================================================================
    
    def _extract_json_tasks(self, text: str) -> List[ExtractedTask]:
        """
        Extrahiert Tasks aus JSON-Format.
        
        Unterstützte Formate:
        1. {"tasks": [...]}
        2. [{"name": ..., "file": ...}, ...]
        3. JSON in ```json ... ``` Block
        """
        tasks = []
        
        # Suche nach JSON-Block
        json_match = re.search(r'```json\s*\n(.*?)```', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1).strip()
        else:
            # Versuche direkt JSON zu finden
            json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                return []
        
        try:
            data = json.loads(json_text)
            
            # Format 1: {"tasks": [...]}
            if isinstance(data, dict) and 'tasks' in data:
                task_list = data['tasks']
            # Format 2: [...]
            elif isinstance(data, list):
                task_list = data
            else:
                return []
            
            for item in task_list:
                if not isinstance(item, dict):
                    continue
                
                task = ExtractedTask(
                    type=item.get('type', ExtractedTask.TaskType.CODE_CHANGE),
                    instruction=item.get('instruction', item.get('description', item.get('name', ''))),
                    file_path=item.get('file_path', item.get('file', item.get('path'))),
                    content=item.get('content', item.get('code')),
                    language=item.get('language', item.get('lang', 'python')),
                    complexity=item.get('complexity', 'low'),
                    priority=item.get('priority', 0),
                    metadata=item.get('metadata', {})
                )
                tasks.append(task)
            
        except json.JSONDecodeError as e:
            logger.debug(f"[TASK-EXTRACT] Kein valides JSON: {e}")
        
        return tasks
    
    # =========================================================================
    # Code Block Extraction
    # =========================================================================
    
    def _extract_code_blocks(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> List[CodeBlock]:
        """
        Extrahiert Code-Blöcke aus Markdown-formatiertem Text.
        """
        blocks = []
        
        # Finde alle ```...``` Blöcke
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or 'text'
            content = match.group(2).strip()
            
            if not content:
                continue
            
            # Extrahiere Datei-Pfad
            file_path = self._infer_file_path(content, language, text, match.start())
            
            # Extrahiere Kontext (Text vor dem Code-Block)
            context_text = self._extract_context(text, match.start())
            
            blocks.append(CodeBlock(
                language=language.lower(),
                content=content,
                file_path=file_path,
                context=context_text
            ))
        
        return blocks
    
    def _infer_file_path(
        self, 
        content: str, 
        language: str, 
        full_text: str,
        block_pos: int
    ) -> Optional[str]:
        """
        Versucht den Datei-Pfad aus verschiedenen Quellen zu ermitteln.
        """
        # 1. Suche im Code-Block selbst (erste Zeile als Kommentar)
        first_line = content.split('\n')[0].strip()
        for pattern in self.FILE_REF_PATTERNS:
            match = pattern.search(first_line)
            if match:
                return match.group(1)
        
        # 2. Suche im Text vor dem Code-Block
        text_before = full_text[max(0, block_pos - 500):block_pos]
        for pattern in self.FILE_REF_PATTERNS:
            matches = list(pattern.finditer(text_before))
            if matches:
                return matches[-1].group(1)  # Letzter Match vor dem Block
        
        # 3. Suche nach spezifischen Datei-Mustern im Content
        file_patterns = [
            # Django/Python patterns
            re.compile(r'class\s+(\w+)\(.*Model.*\)'),  # Django Model
            re.compile(r'def\s+(\w+)\s*\('),  # Funktion
        ]
        
        for pattern in file_patterns:
            match = pattern.search(content)
            if match:
                # Konnte keine Datei ableiten, aber haben Hinweis
                break
        
        return None
    
    def _extract_context(self, text: str, block_pos: int, max_chars: int = 200) -> str:
        """
        Extrahiert den Kontext-Text vor einem Code-Block.
        """
        text_before = text[max(0, block_pos - max_chars):block_pos]
        
        # Finde letzten Absatz
        paragraphs = text_before.split('\n\n')
        if paragraphs:
            return paragraphs[-1].strip()
        
        return text_before.strip()
    
    # =========================================================================
    # Task Conversion
    # =========================================================================
    
    def _code_block_to_task(self, block: CodeBlock) -> Optional[ExtractedTask]:
        """
        Konvertiert einen CodeBlock zu einem ExtractedTask.
        """
        # Nur wenn wir einen Datei-Pfad haben oder ableiten können
        if not block.file_path and not self._is_complete_file(block.content):
            # Kein Datei-Pfad und kein vollständiger File-Content
            return ExtractedTask(
                type=ExtractedTask.TaskType.CODE_CHANGE,
                instruction=block.context or f"Code-Änderung ({block.language})",
                content=block.content,
                language=block.language,
                complexity=self._estimate_complexity(block.content)
            )
        
        return ExtractedTask(
            type=ExtractedTask.TaskType.CODE_CHANGE if block.file_path else ExtractedTask.TaskType.FILE_CREATE,
            instruction=block.context or f"Änderung in {block.file_path or 'neue Datei'}",
            file_path=block.file_path,
            content=block.content,
            language=block.language,
            complexity=self._estimate_complexity(block.content)
        )
    
    def _is_complete_file(self, content: str) -> bool:
        """
        Prüft ob der Content eine vollständige Datei zu sein scheint.
        """
        # Heuristiken für vollständige Dateien
        indicators = [
            content.startswith('"""'),  # Docstring
            content.startswith('#!'),   # Shebang
            'import ' in content[:200],  # Imports am Anfang
            content.startswith('from '),
            'class ' in content and 'def ' in content,  # Klasse mit Methoden
        ]
        return any(indicators)
    
    def _estimate_complexity(self, content: str) -> str:
        """
        Schätzt die Komplexität basierend auf Code-Eigenschaften.
        """
        lines = content.count('\n') + 1
        
        if lines < 20:
            return 'low'
        elif lines < 100:
            return 'medium'
        else:
            return 'high'
    
    def _deduplicate_tasks(self, tasks: List[ExtractedTask]) -> List[ExtractedTask]:
        """
        Entfernt doppelte Tasks basierend auf file_path.
        """
        seen_paths = set()
        unique_tasks = []
        
        for task in tasks:
            key = task.file_path or hash(task.content or '')
            if key not in seen_paths:
                seen_paths.add(key)
                unique_tasks.append(task)
        
        return unique_tasks
    
    # =========================================================================
    # Integration mit CodeRefactorSession
    # =========================================================================
    
    def create_refactor_sessions(
        self, 
        tasks: List[ExtractedTask], 
        requirement,
        user,
        auto_generate: bool = False
    ) -> List:
        """
        Erstellt CodeRefactorSessions aus extrahierten Tasks.
        
        Args:
            tasks: Liste von ExtractedTask
            requirement: TestRequirement
            user: Django User
            auto_generate: Wenn True, wird sofort LLM aufgerufen
            
        Returns:
            Liste von CodeRefactorSession
        """
        from .code_refactor import CodeRefactorService
        from ..models_testing import CodeRefactorSession
        
        sessions = []
        refactor_service = CodeRefactorService()
        
        for task in tasks:
            if task.type != ExtractedTask.TaskType.CODE_CHANGE:
                continue
            
            if not task.file_path:
                logger.warning(f"[TASK-EXTRACT] Task ohne file_path übersprungen: {task.instruction[:50]}")
                continue
            
            try:
                # Session erstellen
                session = refactor_service.create_session(
                    requirement=requirement,
                    file_path=task.file_path,
                    instruction=task.instruction,
                    user=user
                )
                
                # Wenn Content vorhanden, direkt setzen (kein LLM-Call nötig)
                if task.content:
                    session.proposed_content = task.content
                    session.unified_diff = refactor_service._create_diff(
                        session.original_content,
                        task.content,
                        task.file_path
                    )
                    session.status = CodeRefactorSession.Status.PENDING_REVIEW
                    session.save()
                    logger.info(f"[TASK-EXTRACT] Session erstellt mit Content: {task.file_path}")
                
                elif auto_generate:
                    # LLM aufrufen
                    session = refactor_service.generate(session)
                    logger.info(f"[TASK-EXTRACT] Session generiert: {task.file_path}")
                
                sessions.append(session)
                
            except Exception as e:
                logger.error(f"[TASK-EXTRACT] Fehler bei Session-Erstellung: {e}")
                continue
        
        logger.info(f"[TASK-EXTRACT] {len(sessions)} CodeRefactorSessions erstellt")
        return sessions
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def analyze_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Analysiert eine LLM-Response und gibt Statistiken zurück.
        """
        result = self.extract_tasks(llm_response)
        
        return {
            'total_tasks': len(result.tasks),
            'code_blocks': len(result.code_blocks),
            'extraction_method': result.extraction_method,
            'confidence': result.confidence,
            'tasks_by_type': self._group_by_type(result.tasks),
            'tasks_by_complexity': self._group_by_complexity(result.tasks),
            'files_affected': [t.file_path for t in result.tasks if t.file_path]
        }
    
    def _group_by_type(self, tasks: List[ExtractedTask]) -> Dict[str, int]:
        """Gruppiert Tasks nach Typ."""
        groups = {}
        for task in tasks:
            groups[task.type] = groups.get(task.type, 0) + 1
        return groups
    
    def _group_by_complexity(self, tasks: List[ExtractedTask]) -> Dict[str, int]:
        """Gruppiert Tasks nach Komplexität."""
        groups = {}
        for task in tasks:
            groups[task.complexity] = groups.get(task.complexity, 0) + 1
        return groups
