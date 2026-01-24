"""
Code Refactoring Service

LLM-gestütztes Code-Refactoring mit Review-Workflow.
"""

import hashlib
import difflib
import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from apps.bfagent.models_testing import CodeRefactorSession, TestRequirement
from apps.bfagent.models import Llms
from apps.bfagent.services.llm_client import LlmRequest, generate_text

logger = logging.getLogger(__name__)


def _get_llm_by_id(llm_id: int = None):
    """Holt ein LLM per ID oder das Standard-LLM (ID=8)."""
    if llm_id:
        try:
            return Llms.objects.get(id=llm_id, is_active=True)
        except Llms.DoesNotExist:
            raise ValueError(f"LLM mit ID {llm_id} nicht gefunden oder nicht aktiv")
    
    # Default: ID=8 (GPT-4o Mini) oder erstes aktives
    try:
        return Llms.objects.get(id=8, is_active=True)
    except Llms.DoesNotExist:
        return Llms.objects.filter(is_active=True).first()

# Projekt-Root für relative Pfade
PROJECT_ROOT = Path(settings.BASE_DIR)


class CodeRefactorService:
    """
    Service für LLM-gestütztes Code-Refactoring.
    
    Workflow:
    1. create_session() - Session erstellen mit Datei + Instruktion
    2. generate() - LLM generiert Vorschlag
    3. approve() / reject() - User entscheidet
    4. apply() - Änderung anwenden
    5. revert() - Bei Bedarf zurücksetzen
    """
    
    # LLM-Konfiguration
    DEFAULT_MODEL = 'gpt-4o-mini'
    DEFAULT_MAX_TOKENS = 8000
    DEFAULT_TEMPERATURE = 0.3  # Niedriger für Code-Präzision
    
    # Sicherheits-Einschränkungen
    PROTECTED_PATTERNS = [
        'config/settings',
        'manage.py',
        '*/migrations/*.py',
        '.env',
        '*.pyc',
        '__pycache__',
    ]
    MAX_FILE_SIZE = 100 * 1024  # 100 KB
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def create_session(
        self,
        requirement: TestRequirement,
        file_path: str,
        instruction: str,
        user=None
    ) -> CodeRefactorSession:
        """
        Erstellt eine neue Refactoring-Session.
        
        Args:
            requirement: Das zugehörige Requirement
            file_path: Relativer Pfad zur Datei
            instruction: Was soll refactored werden
            user: Der erstellende User
            
        Returns:
            CodeRefactorSession im Status DRAFT
        """
        # Validiere Pfad
        if not self._is_valid_path(file_path):
            raise ValueError(f"Ungültiger oder geschützter Pfad: {file_path}")
        
        # Lade Original
        full_path = self.project_root / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
        
        original_content = full_path.read_text(encoding='utf-8')
        
        # Größen-Check
        if len(original_content) > self.MAX_FILE_SIZE:
            raise ValueError(f"Datei zu groß: {len(original_content)} bytes (max {self.MAX_FILE_SIZE})")
        
        # Hash für Konflikt-Erkennung
        original_hash = hashlib.sha256(original_content.encode('utf-8')).hexdigest()
        
        # Session erstellen
        session = CodeRefactorSession.objects.create(
            requirement=requirement,
            file_path=file_path,
            instruction=instruction,
            original_content=original_content,
            original_hash=original_hash,
            status=CodeRefactorSession.Status.DRAFT,
            created_by=user
        )
        
        logger.info(f"[REFACTOR] Session erstellt: {session.id} für {file_path}")
        return session
    
    # =========================================================================
    # LLM Generation
    # =========================================================================
    
    def generate(
        self,
        session: CodeRefactorSession,
        llm_id: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> CodeRefactorSession:
        """
        Generiert Refactoring-Vorschlag mit LLM.
        
        Args:
            session: Die Session
            llm_id: ID des zu verwendenden LLMs (default: 8)
            model: LLM-Model Override (optional)
            temperature: Temperatur (default: 0.3)
            
        Returns:
            Session mit proposed_content und unified_diff
        """
        if session.status not in [CodeRefactorSession.Status.DRAFT, CodeRefactorSession.Status.ERROR]:
            raise ValueError(f"Session Status muss DRAFT sein, ist: {session.status}")
        
        model = model or self.DEFAULT_MODEL
        temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        
        # Status update
        session.status = CodeRefactorSession.Status.GENERATING
        session.save()
        
        try:
            # Prompt bauen
            prompt = self._build_prompt(session)
            
            # LLM aus DB holen (per ID oder Default)
            llm = _get_llm_by_id(llm_id)
            if not llm:
                raise Exception("Kein aktives LLM konfiguriert. Bitte LLM im Admin einrichten.")
            
            # LLM-Call
            start_time = timezone.now()
            
            result = generate_text(LlmRequest(
                provider=llm.provider or 'openai',
                api_endpoint=llm.api_endpoint or 'https://api.openai.com/v1/chat/completions',
                api_key=llm.api_key or '',
                model=model or llm.llm_name,
                prompt=prompt,
                system=self._get_system_prompt(),
                max_tokens=self.DEFAULT_MAX_TOKENS,
                temperature=temperature
            ))
            
            duration_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            
            if not result.get('ok'):
                raise Exception(result.get('error', 'LLM-Fehler'))
            
            # Token-Tracking
            usage = result.get('raw', {}).get('usage', {})
            session.llm_tokens_input = usage.get('prompt_tokens', 0)
            session.llm_tokens_output = usage.get('completion_tokens', 0)
            session.llm_duration_ms = duration_ms
            session.llm_model = model
            
            # Code extrahieren
            proposed_content = self._extract_code(result['text'])
            
            if not proposed_content.strip():
                raise Exception("LLM hat keinen Code zurückgegeben")
            
            # Diff generieren
            unified_diff = self._create_diff(
                session.original_content,
                proposed_content,
                session.file_path
            )
            
            # Session aktualisieren
            session.proposed_content = proposed_content
            session.unified_diff = unified_diff
            session.status = CodeRefactorSession.Status.PENDING_REVIEW
            session.error_message = ''
            session.save()
            
            logger.info(f"[REFACTOR] Vorschlag generiert: {session.id} ({session.llm_tokens_input + session.llm_tokens_output} tokens)")
            
        except Exception as e:
            session.status = CodeRefactorSession.Status.ERROR
            session.error_message = str(e)
            session.save()
            logger.error(f"[REFACTOR] Generierung fehlgeschlagen: {session.id} - {e}")
            raise
        
        return session
    
    def _build_prompt(self, session: CodeRefactorSession) -> str:
        """Baut den LLM-Prompt."""
        return f"""Refactore die folgende Python-Datei gemäß der Instruktion.

## INSTRUKTION:
{session.instruction}

## AKTUELLE DATEI ({session.file_path}):
```python
{session.original_content}
```

## ANFORDERUNGEN:
- Gib die VOLLSTÄNDIGE refactored Datei zurück
- Behalte alle Imports bei (füge neue hinzu falls nötig)
- Behalte alle Docstrings und Kommentare bei
- Behalte die Code-Struktur und Formatierung konsistent
- Führe NUR die angeforderten Änderungen durch

## ANTWORT:
Gib NUR den vollständigen Python-Code zurück, ohne Erklärungen.
Beginne mit den Imports und ende mit dem letzten Code-Block.
"""
    
    def _get_system_prompt(self) -> str:
        """System-Prompt für Code-Refactoring."""
        return """Du bist ein erfahrener Python-Entwickler spezialisiert auf Code-Refactoring.

Deine Aufgabe:
- Führe die angeforderten Änderungen präzise durch
- Behalte die existierende Code-Struktur bei
- Verbessere Code-Qualität ohne unnötige Änderungen
- Antworte NUR mit dem vollständigen Code, keine Erklärungen

Regeln:
- Keine Markdown-Codeblöcke (```) in der Antwort - nur reiner Python-Code
- Alle Imports müssen am Anfang stehen
- Docstrings und Kommentare beibehalten
- PEP 8 Style einhalten"""
    
    def _extract_code(self, text: str) -> str:
        """Extrahiert Python-Code aus LLM-Antwort."""
        if not text:
            return ''
        
        # Entferne Markdown Code-Blöcke falls vorhanden
        text = text.strip()
        
        # ```python ... ``` Format
        if text.startswith('```'):
            lines = text.split('\n')
            # Entferne erste Zeile (```python)
            lines = lines[1:]
            # Finde Ende (```)
            for i, line in enumerate(lines):
                if line.strip() == '```':
                    lines = lines[:i]
                    break
            text = '\n'.join(lines)
        
        return text.strip()
    
    def _create_diff(self, original: str, proposed: str, file_path: str) -> str:
        """Erstellt Unified Diff."""
        original_lines = original.splitlines(keepends=True)
        proposed_lines = proposed.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            proposed_lines,
            fromfile=f'a/{file_path}',
            tofile=f'b/{file_path}'
        )
        
        return ''.join(diff)
    
    # =========================================================================
    # Review Actions
    # =========================================================================
    
    def approve(self, session: CodeRefactorSession, user=None, notes: str = '') -> CodeRefactorSession:
        """Genehmigt einen Vorschlag."""
        if session.status != CodeRefactorSession.Status.PENDING_REVIEW:
            raise ValueError(f"Session muss PENDING_REVIEW sein, ist: {session.status}")
        
        session.status = CodeRefactorSession.Status.APPROVED
        session.reviewed_by = user
        session.reviewed_at = timezone.now()
        session.review_notes = notes
        session.save()
        
        logger.info(f"[REFACTOR] Vorschlag genehmigt: {session.id}")
        return session
    
    def reject(self, session: CodeRefactorSession, user=None, notes: str = '') -> CodeRefactorSession:
        """Lehnt einen Vorschlag ab."""
        if session.status != CodeRefactorSession.Status.PENDING_REVIEW:
            raise ValueError(f"Session muss PENDING_REVIEW sein, ist: {session.status}")
        
        session.status = CodeRefactorSession.Status.REJECTED
        session.reviewed_by = user
        session.reviewed_at = timezone.now()
        session.review_notes = notes
        session.save()
        
        logger.info(f"[REFACTOR] Vorschlag abgelehnt: {session.id}")
        return session
    
    # =========================================================================
    # Apply / Revert
    # =========================================================================
    
    def apply(self, session: CodeRefactorSession, user=None) -> CodeRefactorSession:
        """
        Wendet die Änderung an.
        
        Args:
            session: Die genehmigte Session
            user: Der ausführende User
            
        Returns:
            Session im Status APPLIED
        """
        if session.status != CodeRefactorSession.Status.APPROVED:
            raise ValueError(f"Session muss APPROVED sein, ist: {session.status}")
        
        full_path = self.project_root / session.file_path
        
        # Konflikt-Check: Hat sich die Datei geändert?
        if full_path.exists():
            current_content = full_path.read_text(encoding='utf-8')
            current_hash = hashlib.sha256(current_content.encode('utf-8')).hexdigest()
            
            if current_hash != session.original_hash:
                session.status = CodeRefactorSession.Status.ERROR
                session.error_message = "Datei wurde seit Session-Erstellung geändert (Konflikt)"
                session.save()
                raise ValueError(session.error_message)
            
            # Backup speichern
            session.backup_content = current_content
        
        try:
            # Änderung schreiben
            full_path.write_text(session.proposed_content, encoding='utf-8')
            
            # Status aktualisieren
            session.status = CodeRefactorSession.Status.APPLIED
            session.applied_at = timezone.now()
            session.applied_by = user
            session.save()
            
            logger.info(f"[REFACTOR] Änderung angewendet: {session.id} auf {session.file_path}")
            
        except Exception as e:
            # Rollback bei Fehler
            if session.backup_content:
                full_path.write_text(session.backup_content, encoding='utf-8')
            
            session.status = CodeRefactorSession.Status.ERROR
            session.error_message = str(e)
            session.save()
            raise
        
        return session
    
    def revert(self, session: CodeRefactorSession, user=None) -> CodeRefactorSession:
        """
        Setzt die Änderung zurück.
        
        Args:
            session: Die angewendete Session
            user: Der ausführende User
            
        Returns:
            Session im Status REVERTED
        """
        if session.status != CodeRefactorSession.Status.APPLIED:
            raise ValueError(f"Session muss APPLIED sein, ist: {session.status}")
        
        if not session.backup_content:
            raise ValueError("Kein Backup vorhanden für Rollback")
        
        full_path = self.project_root / session.file_path
        
        try:
            # Backup wiederherstellen
            full_path.write_text(session.backup_content, encoding='utf-8')
            
            # Status aktualisieren
            session.status = CodeRefactorSession.Status.REVERTED
            session.reverted_at = timezone.now()
            session.save()
            
            logger.info(f"[REFACTOR] Änderung zurückgesetzt: {session.id}")
            
        except Exception as e:
            session.error_message = f"Revert fehlgeschlagen: {e}"
            session.save()
            raise
        
        return session
    
    # =========================================================================
    # Validation
    # =========================================================================
    
    def _is_valid_path(self, file_path: str) -> bool:
        """Prüft ob Pfad gültig und nicht geschützt ist."""
        # Normalisiere Pfad
        file_path = file_path.replace('\\', '/')
        
        # Prüfe geschützte Patterns
        import fnmatch
        for pattern in self.PROTECTED_PATTERNS:
            if fnmatch.fnmatch(file_path, pattern):
                return False
        
        # Nur Python-Dateien erlaubt
        if not file_path.endswith('.py'):
            return False
        
        # Keine Pfade außerhalb des Projekts
        if '..' in file_path:
            return False
        
        return True
    
    def check_conflict(self, session: CodeRefactorSession) -> bool:
        """
        Prüft ob es einen Konflikt gibt.
        
        Returns:
            True wenn Konflikt, False wenn OK
        """
        full_path = self.project_root / session.file_path
        
        if not full_path.exists():
            return True  # Datei wurde gelöscht
        
        current_content = full_path.read_text(encoding='utf-8')
        current_hash = hashlib.sha256(current_content.encode('utf-8')).hexdigest()
        
        return current_hash != session.original_hash
