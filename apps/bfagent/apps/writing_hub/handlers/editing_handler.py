"""
Editing Handler
===============

AI-powered text improvement and editing suggestions for chapters.
MVP implementation for the Redaktionsphase.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from django.utils import timezone

from apps.bfagent.models import BookChapters, Llms
from apps.bfagent.services.llm_client import LlmRequest, generate_text
from apps.writing_hub.models import EditingSuggestion, WorkflowPhaseLLMConfig

logger = logging.getLogger(__name__)


@dataclass
class EditingResult:
    """Result of an editing analysis"""
    success: bool
    suggestions: List[Dict]
    total_issues: int
    message: str
    error: Optional[str] = None


class EditingHandler:
    """
    Handler for AI-powered text editing and improvement suggestions.
    
    Features:
    - Analyze chapter text for improvements
    - Generate style, grammar, and consistency suggestions
    - Apply suggestions to text
    - Track suggestion acceptance/rejection
    
    Usage:
        handler = EditingHandler()
        result = handler.analyze_chapter(chapter_id)
        handler.apply_suggestion(suggestion_id)
    """
    
    ANALYSIS_PROMPT = {
        'system': """Du bist ein erfahrener Lektor für deutschsprachige Literatur.
Analysiere den Text und finde Verbesserungsmöglichkeiten in folgenden Kategorien:
- grammar: Grammatik- und Rechtschreibfehler
- style: Stilistische Verbesserungen (lebendigere Sprache, Show don't Tell)
- repetition: Wortwiederholungen oder redundante Phrasen
- clarity: Unklare oder verwirrende Stellen
- dialogue: Verbesserungen für Dialoge (natürlicher, charakteristischer)
- pacing: Tempo-Probleme (zu schnell, zu langsam)

Antworte NUR mit einem JSON-Array von Vorschlägen. Kein zusätzlicher Text!""",
        
        'user': """Analysiere diesen Kapiteltext und finde Verbesserungsmöglichkeiten:

---
{content}
---

Antworte mit einem JSON-Array in diesem Format:
[
  {{
    "type": "style|grammar|repetition|clarity|dialogue|pacing",
    "original": "Originaltext (exakt wie im Text)",
    "suggestion": "Verbesserter Text",
    "explanation": "Kurze Begründung"
  }}
]

Finde 5-15 Verbesserungen. Fokussiere auf die wichtigsten Probleme.
NUR das JSON-Array ausgeben, keine Erklärungen drumherum!""",

        'user_with_feedback': """Analysiere diesen Kapiteltext und finde Verbesserungsmöglichkeiten.

WICHTIG: Berücksichtige dabei das folgende Feedback von Reviewern:
{feedback_context}

---
KAPITELTEXT:
{content}
---

Antworte mit einem JSON-Array in diesem Format:
[
  {{
    "type": "style|grammar|repetition|clarity|dialogue|pacing",
    "original": "Originaltext (exakt wie im Text)",
    "suggestion": "Verbesserter Text",
    "explanation": "Kurze Begründung"
  }}
]

Finde 5-15 Verbesserungen. Fokussiere besonders auf Punkte aus dem Reviewer-Feedback!
NUR das JSON-Array ausgeben, keine Erklärungen drumherum!"""
    }
    
    def __init__(self, llm_id: Optional[int] = None):
        """Initialize with optional specific LLM."""
        self.llm_id = llm_id
        self._llm = None
    
    def get_llm(self) -> Optional[Llms]:
        """Get the LLM to use for editing."""
        if self._llm:
            return self._llm
        
        # Try workflow phase config first
        self._llm = WorkflowPhaseLLMConfig.get_llm_for_phase('editing')
        if self._llm:
            return self._llm
        
        # Try specific LLM ID
        if self.llm_id:
            try:
                self._llm = Llms.objects.get(id=self.llm_id, is_active=True)
                return self._llm
            except Llms.DoesNotExist:
                pass
        
        # Fallback to any active LLM
        self._llm = Llms.objects.filter(is_active=True).first()
        return self._llm
    
    def analyze_chapter(self, chapter_id: int, feedback_context: Optional[str] = None) -> EditingResult:
        """
        Analyze a chapter and generate improvement suggestions.
        
        Args:
            chapter_id: ID of the chapter to analyze
            feedback_context: Optional feedback from reviewers to consider
            
        Returns:
            EditingResult with suggestions
        """
        try:
            chapter = BookChapters.objects.get(id=chapter_id)
        except BookChapters.DoesNotExist:
            return EditingResult(
                success=False,
                suggestions=[],
                total_issues=0,
                message="Kapitel nicht gefunden",
                error="Chapter not found"
            )
        
        if not chapter.content or len(chapter.content.strip()) < 100:
            return EditingResult(
                success=False,
                suggestions=[],
                total_issues=0,
                message="Kapitel hat zu wenig Inhalt für Analyse",
                error="Insufficient content"
            )
        
        llm = self.get_llm()
        if not llm:
            return EditingResult(
                success=False,
                suggestions=[],
                total_issues=0,
                message="Kein LLM konfiguriert",
                error="No LLM available"
            )
        
        # Truncate content if too long (keep first ~8000 chars)
        content = chapter.content[:8000]
        if len(chapter.content) > 8000:
            content += "\n\n[... Text gekürzt für Analyse ...]"
        
        # Choose prompt based on whether feedback is provided
        if feedback_context and feedback_context.strip():
            prompt = self.ANALYSIS_PROMPT['user_with_feedback'].format(
                content=content,
                feedback_context=feedback_context
            )
        else:
            prompt = self.ANALYSIS_PROMPT['user'].format(content=content)
        
        # Build request
        request = LlmRequest(
            provider=llm.provider,
            api_endpoint=llm.api_endpoint,
            api_key=llm.api_key,
            model=llm.llm_name,
            system=self.ANALYSIS_PROMPT['system'],
            prompt=prompt,
            temperature=0.3,  # Lower for more consistent analysis
            max_tokens=4000,
        )
        
        try:
            response = generate_text(request)
            
            if not response or not response.get('ok'):
                error_msg = response.get('error', 'Unknown error') if response else 'No response'
                return EditingResult(
                    success=False,
                    suggestions=[],
                    total_issues=0,
                    message=f"LLM-Fehler: {error_msg}",
                    error=error_msg
                )
            
            # Parse JSON response
            text = response.get('text', '')
            suggestions = self._parse_suggestions(text, chapter)
            
            return EditingResult(
                success=True,
                suggestions=suggestions,
                total_issues=len(suggestions),
                message=f"{len(suggestions)} Verbesserungsvorschläge gefunden"
            )
            
        except Exception as e:
            logger.exception(f"Error analyzing chapter {chapter_id}")
            return EditingResult(
                success=False,
                suggestions=[],
                total_issues=0,
                message=f"Analysefehler: {str(e)}",
                error=str(e)
            )
    
    def _parse_suggestions(self, text: str, chapter: BookChapters) -> List[Dict]:
        """Parse LLM response and create EditingSuggestion objects."""
        suggestions = []
        
        # Try to extract JSON from response
        try:
            # Find JSON array in response
            json_match = re.search(r'\[[\s\S]*\]', text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning(f"No JSON array found in response: {text[:200]}")
                return []
            
            for item in data:
                if not isinstance(item, dict):
                    continue
                
                suggestion_type = item.get('type', 'style')
                original = item.get('original', '')
                suggested = item.get('suggestion', '')
                explanation = item.get('explanation', '')
                
                if not original or not suggested:
                    continue
                
                # Map type to our choices
                type_map = {
                    'grammar': 'grammar',
                    'style': 'style',
                    'repetition': 'repetition',
                    'clarity': 'clarity',
                    'dialogue': 'dialogue',
                    'pacing': 'pacing',
                }
                mapped_type = type_map.get(suggestion_type, 'style')
                
                # Find position in text
                pos_start = chapter.content.find(original) if chapter.content else 0
                pos_end = pos_start + len(original) if pos_start >= 0 else 0
                
                # Create suggestion in DB
                suggestion = EditingSuggestion.objects.create(
                    chapter=chapter,
                    suggestion_type=mapped_type,
                    original_text=original[:1000],  # Limit length
                    suggested_text=suggested[:1000],
                    explanation=explanation[:500],
                    position_start=max(0, pos_start),
                    position_end=max(0, pos_end),
                    status='pending'
                )
                
                suggestions.append({
                    'id': suggestion.id,
                    'type': mapped_type,
                    'type_display': suggestion.get_suggestion_type_display(),
                    'original': original,
                    'suggested': suggested,
                    'explanation': explanation,
                    'status': 'pending'
                })
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}, text: {text[:500]}")
        except Exception as e:
            logger.exception(f"Error parsing suggestions: {e}")
        
        return suggestions
    
    def apply_suggestion(self, suggestion_id: int) -> Dict:
        """
        Apply a suggestion to the chapter text.
        
        Args:
            suggestion_id: ID of the EditingSuggestion
            
        Returns:
            Dict with success status and updated content
        """
        try:
            suggestion = EditingSuggestion.objects.select_related('chapter').get(id=suggestion_id)
        except EditingSuggestion.DoesNotExist:
            return {'success': False, 'error': 'Vorschlag nicht gefunden'}
        
        chapter = suggestion.chapter
        if not chapter.content:
            return {'success': False, 'error': 'Kapitel hat keinen Inhalt'}
        
        # Replace text
        new_content = chapter.content.replace(
            suggestion.original_text,
            suggestion.suggested_text,
            1  # Only replace first occurrence
        )
        
        if new_content == chapter.content:
            # Text not found - might have been changed already
            suggestion.status = 'rejected'
            suggestion.resolved_at = timezone.now()
            suggestion.save()
            return {'success': False, 'error': 'Originaltext nicht mehr im Kapitel gefunden'}
        
        # Update chapter
        chapter.content = new_content
        chapter.word_count = len(new_content.split())
        chapter.save()
        
        # Update suggestion
        suggestion.status = 'accepted'
        suggestion.resolved_at = timezone.now()
        suggestion.save()
        
        return {
            'success': True,
            'message': 'Vorschlag angewendet',
            'new_content': new_content,
            'word_count': chapter.word_count
        }
    
    def reject_suggestion(self, suggestion_id: int) -> Dict:
        """Mark a suggestion as rejected."""
        try:
            suggestion = EditingSuggestion.objects.get(id=suggestion_id)
            suggestion.status = 'rejected'
            suggestion.resolved_at = timezone.now()
            suggestion.save()
            return {'success': True, 'message': 'Vorschlag abgelehnt'}
        except EditingSuggestion.DoesNotExist:
            return {'success': False, 'error': 'Vorschlag nicht gefunden'}
    
    def apply_all_suggestions(self, chapter_id: int) -> Dict:
        """Apply all pending suggestions for a chapter."""
        suggestions = EditingSuggestion.objects.filter(
            chapter_id=chapter_id,
            status='pending'
        ).order_by('-position_start')  # Apply from end to start to preserve positions
        
        applied = 0
        failed = 0
        
        for suggestion in suggestions:
            result = self.apply_suggestion(suggestion.id)
            if result['success']:
                applied += 1
            else:
                failed += 1
        
        return {
            'success': True,
            'applied': applied,
            'failed': failed,
            'message': f'{applied} Vorschläge angewendet, {failed} fehlgeschlagen'
        }
    
    def get_pending_suggestions(self, chapter_id: int) -> List[Dict]:
        """Get all pending suggestions for a chapter."""
        suggestions = EditingSuggestion.objects.filter(
            chapter_id=chapter_id,
            status='pending'
        ).order_by('position_start')
        
        return [
            {
                'id': s.id,
                'type': s.suggestion_type,
                'type_display': s.get_suggestion_type_display(),
                'original': s.original_text,
                'suggested': s.suggested_text,
                'explanation': s.explanation,
                'status': s.status,
                'created_at': s.created_at.isoformat()
            }
            for s in suggestions
        ]
    
    def clear_suggestions(self, chapter_id: int) -> Dict:
        """Clear all pending suggestions for a chapter."""
        count = EditingSuggestion.objects.filter(
            chapter_id=chapter_id,
            status='pending'
        ).delete()[0]
        
        return {
            'success': True,
            'deleted': count,
            'message': f'{count} Vorschläge gelöscht'
        }
    
    def analyze_all_chapters(self, project_id: int, feedback_context: Optional[str] = None) -> Dict:
        """
        Analyze all chapters of a project and generate improvement suggestions.
        
        Args:
            project_id: ID of the project
            feedback_context: Optional feedback from reviewers to consider
            
        Returns:
            Dict with results per chapter and summary
        """
        from apps.bfagent.models import BookProjects
        
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {
                'success': False,
                'error': 'Projekt nicht gefunden',
                'chapters': [],
                'total_suggestions': 0
            }
        
        chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
        
        if not chapters.exists():
            return {
                'success': False,
                'error': 'Keine Kapitel vorhanden',
                'chapters': [],
                'total_suggestions': 0
            }
        
        results = []
        total_suggestions = 0
        analyzed = 0
        skipped = 0
        errors = 0
        
        for chapter in chapters:
            # Skip chapters without content
            if not chapter.content or len(chapter.content.strip()) < 100:
                results.append({
                    'chapter_id': chapter.id,
                    'chapter_number': chapter.chapter_number,
                    'title': chapter.title,
                    'status': 'skipped',
                    'message': 'Zu wenig Inhalt',
                    'suggestions_count': 0
                })
                skipped += 1
                continue
            
            # Analyze chapter
            try:
                result = self.analyze_chapter(chapter.id, feedback_context)
                
                if result.success:
                    results.append({
                        'chapter_id': chapter.id,
                        'chapter_number': chapter.chapter_number,
                        'title': chapter.title,
                        'status': 'success',
                        'message': result.message,
                        'suggestions_count': result.total_issues
                    })
                    total_suggestions += result.total_issues
                    analyzed += 1
                else:
                    results.append({
                        'chapter_id': chapter.id,
                        'chapter_number': chapter.chapter_number,
                        'title': chapter.title,
                        'status': 'error',
                        'message': result.message,
                        'suggestions_count': 0
                    })
                    errors += 1
                    
            except Exception as e:
                logger.exception(f"Error analyzing chapter {chapter.id}")
                results.append({
                    'chapter_id': chapter.id,
                    'chapter_number': chapter.chapter_number,
                    'title': chapter.title,
                    'status': 'error',
                    'message': str(e),
                    'suggestions_count': 0
                })
                errors += 1
        
        return {
            'success': True,
            'chapters': results,
            'total_suggestions': total_suggestions,
            'summary': {
                'analyzed': analyzed,
                'skipped': skipped,
                'errors': errors,
                'total': len(chapters)
            },
            'message': f'{analyzed} Kapitel analysiert, {total_suggestions} Vorschläge gefunden'
        }
