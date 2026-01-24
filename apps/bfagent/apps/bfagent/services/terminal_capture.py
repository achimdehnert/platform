# -*- coding: utf-8 -*-
"""
Terminal Capture Service.

Erfasst Terminal-Output in Dateien und parsed Fehler.
"""
import re
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Singleton
_capture_service = None


def get_terminal_capture_service() -> 'TerminalCaptureService':
    """Gibt Singleton-Instanz zurück."""
    global _capture_service
    if _capture_service is None:
        _capture_service = TerminalCaptureService()
    return _capture_service


class ErrorParser:
    """Parst Terminal-Output und erkennt Fehler."""
    
    # Python Exception Patterns
    PYTHON_EXCEPTION_START = re.compile(r'^Traceback \(most recent call last\):')
    PYTHON_EXCEPTION_LINE = re.compile(r'^\s+File "([^"]+)", line (\d+), in (\w+)')
    PYTHON_EXCEPTION_ERROR = re.compile(r'^(\w+Error|\w+Exception|KeyError|ValueError|TypeError|AttributeError|ImportError|ModuleNotFoundError): (.+)$')
    
    # Django-spezifische Patterns
    DJANGO_TEMPLATE_ERROR = re.compile(r'(TemplateDoesNotExist|TemplateSyntaxError): (.+)')
    DJANGO_URL_ERROR = re.compile(r'(NoReverseMatch|Resolver404): (.+)')
    DJANGO_DB_ERROR = re.compile(r'(OperationalError|ProgrammingError|IntegrityError): (.+)')
    DJANGO_MIGRATION_ERROR = re.compile(r'(MigrationError|InconsistentMigrationHistory): (.+)')
    
    # NPM/Node Patterns
    NPM_ERROR = re.compile(r'^npm ERR! (.+)$')
    NODE_ERROR = re.compile(r'^Error: (.+)$')
    
    # Browser Console Patterns (wenn via Log-Forwarding)
    BROWSER_ERROR = re.compile(r'\[BROWSER\] (Error|TypeError|ReferenceError): (.+)')
    
    # File:Line Pattern
    FILE_LINE = re.compile(r'([a-zA-Z0-9_/\\.]+\.(?:py|js|ts|html|css)):(\d+)')
    
    ERROR_TYPE_MAPPING = {
        'ImportError': 'import_error',
        'ModuleNotFoundError': 'import_error',
        'TemplateDoesNotExist': 'template_error',
        'TemplateSyntaxError': 'template_error',
        'SyntaxError': 'syntax_error',
        'IndentationError': 'syntax_error',
        'OperationalError': 'database_error',
        'ProgrammingError': 'database_error',
        'IntegrityError': 'database_error',
        'NoReverseMatch': 'url_error',
        'Resolver404': 'url_error',
        'AttributeError': 'attribute_error',
        'TypeError': 'type_error',
        'ValueError': 'value_error',
        'KeyError': 'key_error',
        'RuntimeError': 'runtime_error',
    }
    
    SEVERITY_MAPPING = {
        'import_error': 'high',
        'template_error': 'medium',
        'syntax_error': 'critical',
        'database_error': 'critical',
        'url_error': 'medium',
        'attribute_error': 'medium',
        'type_error': 'medium',
        'value_error': 'low',
        'key_error': 'low',
        'runtime_error': 'high',
        'npm_error': 'medium',
        'browser_error': 'low',
        'other': 'medium',
    }
    
    def __init__(self):
        self._traceback_buffer = []
        self._in_traceback = False
    
    def parse_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Parst mehrere Zeilen und gibt erkannte Fehler zurück."""
        errors = []
        
        for i, line in enumerate(lines):
            result = self.parse_line(line, context_lines=lines[max(0, i-5):i+5])
            if result:
                errors.append(result)
        
        return errors
    
    def parse_line(self, line: str, context_lines: List[str] = None) -> Optional[Dict[str, Any]]:
        """Parst eine einzelne Zeile."""
        line = line.rstrip()
        
        # Traceback Start
        if self.PYTHON_EXCEPTION_START.match(line):
            self._in_traceback = True
            self._traceback_buffer = [line]
            return None
        
        # Im Traceback
        if self._in_traceback:
            self._traceback_buffer.append(line)
            
            # Traceback Ende (Error-Zeile)
            error_match = self.PYTHON_EXCEPTION_ERROR.match(line)
            if error_match:
                self._in_traceback = False
                error_class = error_match.group(1)
                message = error_match.group(2)
                
                # File/Line aus Traceback extrahieren
                file_path, line_number, function_name = self._extract_location_from_traceback()
                
                return {
                    'error_class': error_class,
                    'error_type': self.ERROR_TYPE_MAPPING.get(error_class, 'other'),
                    'severity': self.SEVERITY_MAPPING.get(
                        self.ERROR_TYPE_MAPPING.get(error_class, 'other'), 'medium'
                    ),
                    'message': f"{error_class}: {message}",
                    'file_path': file_path,
                    'line_number': line_number,
                    'function_name': function_name,
                    'stack_trace': '\n'.join(self._traceback_buffer),
                    'source': 'python',
                    'raw_output': '\n'.join(self._traceback_buffer),
                }
        
        # Django Template Error
        match = self.DJANGO_TEMPLATE_ERROR.search(line)
        if match:
            return self._create_error_dict(
                error_class=match.group(1),
                message=f"{match.group(1)}: {match.group(2)}",
                error_type='template_error',
                source='django',
                raw_output=line,
            )
        
        # Django URL Error
        match = self.DJANGO_URL_ERROR.search(line)
        if match:
            return self._create_error_dict(
                error_class=match.group(1),
                message=f"{match.group(1)}: {match.group(2)}",
                error_type='url_error',
                source='django',
                raw_output=line,
            )
        
        # Django DB Error
        match = self.DJANGO_DB_ERROR.search(line)
        if match:
            return self._create_error_dict(
                error_class=match.group(1),
                message=f"{match.group(1)}: {match.group(2)}",
                error_type='database_error',
                source='django',
                raw_output=line,
            )
        
        # NPM Error
        match = self.NPM_ERROR.match(line)
        if match:
            return self._create_error_dict(
                error_class='NPMError',
                message=f"npm ERR! {match.group(1)}",
                error_type='npm_error',
                source='npm',
                raw_output=line,
            )
        
        # Browser Error
        match = self.BROWSER_ERROR.search(line)
        if match:
            return self._create_error_dict(
                error_class=match.group(1),
                message=f"[Browser] {match.group(1)}: {match.group(2)}",
                error_type='browser_error',
                source='browser',
                raw_output=line,
            )
        
        return None
    
    def _extract_location_from_traceback(self) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Extrahiert File/Line/Function aus Traceback-Buffer."""
        # Letzte relevante Zeile finden (nicht in site-packages)
        for line in reversed(self._traceback_buffer):
            match = self.PYTHON_EXCEPTION_LINE.match(line)
            if match:
                file_path = match.group(1)
                # Eigenen Code priorisieren
                if 'site-packages' not in file_path and '.venv' not in file_path:
                    return file_path, int(match.group(2)), match.group(3)
        
        # Fallback: Erste Zeile mit File-Info
        for line in self._traceback_buffer:
            match = self.PYTHON_EXCEPTION_LINE.match(line)
            if match:
                return match.group(1), int(match.group(2)), match.group(3)
        
        return None, None, None
    
    def _create_error_dict(
        self,
        error_class: str,
        message: str,
        error_type: str,
        source: str,
        raw_output: str,
        file_path: str = None,
        line_number: int = None,
        function_name: str = None,
        stack_trace: str = None,
    ) -> Dict[str, Any]:
        """Erstellt standardisiertes Error-Dict."""
        return {
            'error_class': error_class,
            'error_type': error_type,
            'severity': self.SEVERITY_MAPPING.get(error_type, 'medium'),
            'message': message,
            'file_path': file_path,
            'line_number': line_number,
            'function_name': function_name,
            'stack_trace': stack_trace,
            'source': source,
            'raw_output': raw_output,
        }


class TerminalCaptureService:
    """Service für Terminal-Output-Erfassung."""
    
    LOG_DIR = Path(getattr(settings, 'TERMINAL_LOG_DIR', 'logs/terminal'))
    
    def __init__(self):
        self.parser = ErrorParser()
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    def process_log_file(self, log_file_path: str, session_id: str = None) -> List[Dict]:
        """Verarbeitet eine Log-Datei und extrahiert Fehler."""
        from ..models_terminal import TerminalError, TerminalSession
        
        log_path = Path(log_file_path)
        if not log_path.exists():
            logger.warning(f"Log file not found: {log_file_path}")
            return []
        
        # Session finden oder erstellen
        session = None
        if session_id:
            try:
                session = TerminalSession.objects.get(id=session_id)
            except TerminalSession.DoesNotExist:
                pass
        
        # Datei lesen
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        # Fehler parsen
        parsed_errors = self.parser.parse_lines(lines)
        
        # In DB speichern
        saved_errors = []
        for error_data in parsed_errors:
            error_data['session'] = session
            error = TerminalError.get_or_increment(error_data)
            saved_errors.append({
                'id': str(error.id),
                'error_type': error.error_type,
                'message': error.message,
                'occurrence_count': error.occurrence_count,
                'is_new': error.occurrence_count == 1,
            })
        
        # Session-Stats aktualisieren
        if session:
            session.total_lines = len(lines)
            session.error_count = len([e for e in saved_errors if e['is_new']])
            session.save(update_fields=['total_lines', 'error_count'])
        
        return saved_errors
    
    def process_text_input(self, text: str, source: str = 'manual') -> List[Dict]:
        """Verarbeitet Text-Input (z.B. aus Clipboard)."""
        from ..models_terminal import TerminalError
        
        lines = text.split('\n')
        parsed_errors = self.parser.parse_lines(lines)
        
        saved_errors = []
        for error_data in parsed_errors:
            error_data['source'] = source
            error = TerminalError.get_or_increment(error_data)
            saved_errors.append({
                'id': str(error.id),
                'error_type': error.error_type,
                'message': error.message,
                'occurrence_count': error.occurrence_count,
                'is_new': error.occurrence_count == 1,
            })
        
        return saved_errors
    
    def get_ai_solution(self, error_id: str) -> Dict[str, Any]:
        """Generiert KI-Lösungsvorschlag für einen Fehler."""
        from ..models_terminal import TerminalError
        from .llm_client import generate_text
        
        try:
            error = TerminalError.objects.get(id=error_id)
        except TerminalError.DoesNotExist:
            return {'success': False, 'error': 'Error not found'}
        
        # Bereits analysiert?
        if error.ai_solution_steps and error.ai_analyzed_at:
            # Nicht älter als 1 Stunde
            age = timezone.now() - error.ai_analyzed_at
            if age.total_seconds() < 3600:
                return {
                    'success': True,
                    'analysis': error.ai_analysis,
                    'solution_steps': error.ai_solution_steps,
                    'confidence': error.ai_confidence,
                    'cached': True,
                }
        
        # KI-Analyse durchführen
        prompt = self._build_analysis_prompt(error)
        
        try:
            response = generate_text(
                prompt=prompt,
                system_prompt=self._get_system_prompt(),
                max_tokens=2000,
            )
            
            # Response parsen
            analysis, steps, confidence = self._parse_ai_response(response)
            
            # In DB speichern
            error.ai_analysis = analysis
            error.ai_solution_steps = steps
            error.ai_confidence = confidence
            error.ai_analyzed_at = timezone.now()
            error.status = 'ready'
            error.save()
            
            return {
                'success': True,
                'analysis': analysis,
                'solution_steps': steps,
                'confidence': confidence,
                'cached': False,
            }
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def _get_system_prompt(self) -> str:
        """System-Prompt für KI-Analyse."""
        return """Du bist ein erfahrener Django/Python-Entwickler und hilfst bei der Fehlerbehebung.

Analysiere den Fehler und gib eine strukturierte Lösung:

1. **Analyse**: Kurze Erklärung was der Fehler bedeutet
2. **Ursache**: Warum tritt der Fehler auf
3. **Lösungsschritte**: Nummerierte Liste der konkreten Schritte zur Behebung
4. **Konfidenz**: Wie sicher bist du (0.0-1.0)

Antworte im folgenden JSON-Format:
{
    "analysis": "Kurze Analyse des Fehlers",
    "cause": "Ursache des Fehlers",
    "steps": [
        {"step": 1, "action": "Beschreibung", "code": "optional: code snippet"},
        {"step": 2, "action": "Beschreibung", "code": "optional: code snippet"}
    ],
    "confidence": 0.85
}"""
    
    def _build_analysis_prompt(self, error) -> str:
        """Baut Prompt für Fehleranalyse."""
        prompt = f"""Analysiere diesen Fehler:

**Fehlertyp:** {error.error_type}
**Fehlerklasse:** {error.error_class}
**Nachricht:** {error.message}

**Datei:** {error.file_path or 'Unbekannt'}
**Zeile:** {error.line_number or 'Unbekannt'}
**Funktion:** {error.function_name or 'Unbekannt'}
"""
        
        if error.code_snippet:
            prompt += f"\n**Code-Snippet:**\n```python\n{error.code_snippet}\n```\n"
        
        if error.stack_trace:
            prompt += f"\n**Stack Trace:**\n```\n{error.stack_trace}\n```\n"
        
        prompt += "\nGib eine strukturierte Lösung mit konkreten Schritten."
        
        return prompt
    
    def _parse_ai_response(self, response: str) -> Tuple[str, List[Dict], float]:
        """Parst KI-Response."""
        try:
            # JSON extrahieren
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                analysis = f"{data.get('analysis', '')}\n\nUrsache: {data.get('cause', '')}"
                steps = data.get('steps', [])
                confidence = float(data.get('confidence', 0.5))
                return analysis, steps, confidence
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
        
        # Fallback: Plain text
        return response, [], 0.3
