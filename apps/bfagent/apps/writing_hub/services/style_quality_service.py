"""
Style Quality Service
=====================

Business Logic für Style DNA basierte Qualitätsanalyse.
Integriert mit QualityGateService für Gate-Entscheidungen.

Separation of Concerns:
- StyleQualityService: Style DNA Analyse + Issue Detection
- QualityGateService: Gate-Entscheidungen + Score-Persistenz
"""
import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class StyleAnalysisResult:
    """Ergebnis der Style-Analyse"""
    dimension_scores: dict[str, Decimal] = field(default_factory=dict)
    issues: list[dict] = field(default_factory=list)
    findings: dict = field(default_factory=dict)
    llm_used: str = ""
    tokens_used: int = 0
    success: bool = True
    error: str = ""


class StyleQualityService:
    """
    Service für Style DNA basierte Qualitätsanalyse.
    
    Verantwortlich für:
    - Analyse von Text gegen Style DNA
    - Erkennung von Stil-Verstößen
    - Tabu-Wort-Erkennung
    - Integration mit QualityGateService
    """
    
    def __init__(self, style_dna=None):
        """
        Args:
            style_dna: Optional AuthorStyleDNA instance
        """
        self.style_dna = style_dna
        self._quality_gate_service = None
    
    @property
    def quality_gate_service(self):
        """Lazy-load QualityGateService"""
        if self._quality_gate_service is None:
            from .quality_gate_service import QualityGateService
            self._quality_gate_service = QualityGateService()
        return self._quality_gate_service
    
    def analyze_chapter(
        self,
        chapter_id: UUID,
        use_llm: bool = True,
        user=None
    ) -> 'ChapterQualityScore':
        """
        Analysiert ein Kapitel gegen Style DNA und erstellt Score.
        
        Args:
            chapter_id: UUID des Kapitels
            use_llm: LLM für tiefe Analyse verwenden
            user: User der die Analyse triggert
            
        Returns:
            ChapterQualityScore mit Gate-Entscheidung
        """
        from apps.bfagent.models import BookChapters
        from ..models_quality import StyleIssue, StyleIssueType
        
        # Kapitel laden
        chapter = BookChapters.objects.select_related('project').get(pk=chapter_id)
        content = chapter.content or ""
        
        if not content.strip():
            logger.warning(f"Chapter {chapter_id} has no content")
            return self._create_empty_score(chapter_id, user, "Kein Kapitelinhalt")
        
        # Style DNA laden falls nicht gesetzt
        if not self.style_dna:
            self.style_dna = self._load_style_dna(chapter.project)
        
        # Analyse durchführen
        if use_llm and self.style_dna:
            result = self._analyze_with_llm(content, self.style_dna)
        else:
            result = self._analyze_rule_based(content, self.style_dna)
        
        if not result.success:
            logger.error(f"Style analysis failed: {result.error}")
            return self._create_empty_score(chapter_id, user, result.error)
        
        # Score über QualityGateService erstellen
        score = self.quality_gate_service.evaluate_chapter(
            chapter_id=str(chapter_id),
            dimension_scores=result.dimension_scores,
            findings=result.findings,
            user=user,
            notes=f"LLM: {result.llm_used}" if result.llm_used else "Rule-based"
        )
        
        # Style Issues erstellen
        self._create_style_issues(score, result.issues)
        
        logger.info(
            f"Chapter {chapter_id} analyzed: score={score.overall_score}, "
            f"issues={len(result.issues)}, decision={score.gate_decision.code}"
        )
        
        return score
    
    def _load_style_dna(self, project):
        """Lädt Style DNA für Projekt-Owner"""
        from ..models import AuthorStyleDNA
        
        owner = getattr(project, 'owner', None) or getattr(project, 'user', None)
        if not owner:
            logger.warning(f"Project {project.id} has no owner")
            return None
        
        dna = AuthorStyleDNA.objects.filter(
            author=owner,
            is_primary=True
        ).first()
        
        if dna:
            logger.debug(f"Loaded Style DNA: {dna.name}")
        
        return dna
    
    def _analyze_rule_based(self, content: str, style_dna) -> StyleAnalysisResult:
        """
        Regel-basierte Analyse ohne LLM.
        Schnell, aber weniger tiefgründig.
        """
        result = StyleAnalysisResult()
        
        # Default Scores
        result.dimension_scores = {
            'style_adherence': Decimal('7.0'),
            'taboo_compliance': Decimal('10.0'),
            'pacing': Decimal('7.5'),
            'dialogue_quality': Decimal('7.0'),
        }
        
        if not style_dna:
            result.findings['note'] = "Keine Style DNA verfügbar"
            return result
        
        # Tabu-Wörter prüfen
        taboo_issues = self._check_taboo_words(content, style_dna)
        if taboo_issues:
            result.issues.extend(taboo_issues)
            # Score reduzieren basierend auf Anzahl
            penalty = min(len(taboo_issues) * Decimal('0.5'), Decimal('5.0'))
            result.dimension_scores['taboo_compliance'] -= penalty
        
        # DON'T Patterns prüfen
        dont_issues = self._check_dont_patterns(content, style_dna)
        if dont_issues:
            result.issues.extend(dont_issues)
            penalty = min(len(dont_issues) * Decimal('0.3'), Decimal('3.0'))
            result.dimension_scores['style_adherence'] -= penalty
        
        # Passive Voice prüfen
        passive_issues = self._check_passive_voice(content)
        if passive_issues:
            result.issues.extend(passive_issues)
            penalty = min(len(passive_issues) * Decimal('0.1'), Decimal('2.0'))
            result.dimension_scores['style_adherence'] -= penalty
        
        # Findings zusammenstellen
        result.findings = {
            'taboo_count': len(taboo_issues),
            'dont_violations': len(dont_issues),
            'passive_constructions': len(passive_issues),
            'style_dna_name': style_dna.name,
        }
        
        return result
    
    def _analyze_with_llm(self, content: str, style_dna) -> StyleAnalysisResult:
        """
        LLM-basierte tiefe Analyse.
        Verwendet StyleQualityHandler für LLM-Aufrufe.
        """
        try:
            from ..handlers.quality_handler import StyleQualityHandler
            
            handler = StyleQualityHandler()
            llm_result = handler.analyze_style(
                chapter_text=content,
                style_dna=self._style_dna_to_dict(style_dna)
            )
            
            if not llm_result.get('success', False):
                # Fallback zu rule-based
                logger.warning("LLM analysis failed, falling back to rule-based")
                return self._analyze_rule_based(content, style_dna)
            
            result = StyleAnalysisResult(
                dimension_scores={
                    'style_adherence': Decimal(str(llm_result.get('style_adherence', 7.0))),
                    'signature_moves': Decimal(str(llm_result.get('signature_moves', 7.0))),
                    'taboo_compliance': Decimal(str(llm_result.get('taboo_compliance', 10.0))),
                    'pacing': Decimal(str(llm_result.get('pacing', 7.0))),
                    'dialogue_quality': Decimal(str(llm_result.get('dialogue_quality', 7.0))),
                },
                issues=llm_result.get('issues', []),
                findings=llm_result.get('findings', {}),
                llm_used=llm_result.get('llm_used', ''),
                tokens_used=llm_result.get('tokens_used', 0),
                success=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return self._analyze_rule_based(content, style_dna)
    
    def _style_dna_to_dict(self, style_dna) -> dict:
        """Konvertiert StyleDNA Model zu Dict für Handler"""
        if not style_dna:
            return {}
        
        return {
            'name': style_dna.name,
            'signature_moves': style_dna.signature_moves or [],
            'do_list': style_dna.do_list or [],
            'dont_list': style_dna.dont_list or [],
            'taboo_list': style_dna.taboo_list or [],
        }
    
    def _check_taboo_words(self, content: str, style_dna) -> list[dict]:
        """Prüft auf Tabu-Wörter"""
        issues = []
        taboo_list = style_dna.taboo_list or []
        
        if not taboo_list:
            return issues
        
        content_lower = content.lower()
        
        for taboo in taboo_list:
            if not taboo:
                continue
            
            taboo_lower = taboo.lower()
            # Wortgrenzen-basierte Suche
            pattern = r'\b' + re.escape(taboo_lower) + r'\b'
            matches = list(re.finditer(pattern, content_lower))
            
            for match in matches:
                # Kontext extrahieren (50 Zeichen vor/nach)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                excerpt = content[start:end]
                
                issues.append({
                    'issue_type_code': 'taboo_word',
                    'text_excerpt': f"...{excerpt}...",
                    'char_position': match.start(),
                    'suggestion': f"Ersetze '{taboo}' durch ein alternatives Wort",
                    'explanation': f"'{taboo}' ist auf der Tabu-Liste",
                })
        
        return issues
    
    def _check_dont_patterns(self, content: str, style_dna) -> list[dict]:
        """Prüft auf DON'T Muster"""
        issues = []
        dont_list = style_dna.dont_list or []
        
        # Einfache Keyword-basierte Prüfung
        # Erweiterte Patterns könnten hier ergänzt werden
        
        for dont in dont_list:
            if not dont:
                continue
            
            # Einfache Suche nach Keywords im DON'T
            keywords = dont.lower().split()[:3]  # Erste 3 Wörter
            
            for keyword in keywords:
                if len(keyword) < 4:  # Zu kurze Wörter ignorieren
                    continue
                
                if keyword in content.lower():
                    issues.append({
                        'issue_type_code': 'dont_violation',
                        'text_excerpt': f"Möglicher Verstoß gegen: {dont}",
                        'suggestion': f"Überprüfe: {dont}",
                        'explanation': f"DON'T Regel: {dont}",
                    })
                    break  # Nur eine Issue pro DON'T
        
        return issues
    
    def _check_passive_voice(self, content: str) -> list[dict]:
        """Prüft auf passive Konstruktionen (Deutsch)"""
        issues = []
        
        # Deutsche Passiv-Muster
        passive_patterns = [
            r'\b(wurde|wurden|wird|werden)\s+\w+t\b',
            r'\b(ist|sind|war|waren)\s+\w+t\s+worden\b',
        ]
        
        for pattern in passive_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            
            for match in matches[:5]:  # Max 5 pro Pattern
                start = max(0, match.start() - 30)
                end = min(len(content), match.end() + 30)
                excerpt = content[start:end]
                
                issues.append({
                    'issue_type_code': 'passive_voice',
                    'text_excerpt': f"...{excerpt}...",
                    'char_position': match.start(),
                    'suggestion': "Aktive Formulierung bevorzugen",
                    'explanation': "Passiv-Konstruktion gefunden",
                })
        
        return issues
    
    def _create_style_issues(self, score, issues: list[dict]):
        """Erstellt StyleIssue Records aus Issue-Liste"""
        from ..models_quality import StyleIssue, StyleIssueType
        
        if not issues:
            return
        
        # Issue Types cachen
        issue_types = {
            t.code: t 
            for t in StyleIssueType.objects.filter(is_active=True)
        }
        
        with transaction.atomic():
            for issue_data in issues:
                type_code = issue_data.get('issue_type_code', 'unknown')
                issue_type = issue_types.get(type_code)
                
                if not issue_type:
                    logger.warning(f"Unknown issue type: {type_code}")
                    continue
                
                StyleIssue.objects.create(
                    quality_score=score,
                    issue_type=issue_type,
                    text_excerpt=issue_data.get('text_excerpt', '')[:500],
                    char_position=issue_data.get('char_position'),
                    suggestion=issue_data.get('suggestion', ''),
                    explanation=issue_data.get('explanation', ''),
                )
    
    def _create_empty_score(self, chapter_id, user, error_note: str):
        """Erstellt leeren Score bei Fehler"""
        return self.quality_gate_service.evaluate_chapter(
            chapter_id=str(chapter_id),
            dimension_scores={
                'style_adherence': Decimal('0'),
                'taboo_compliance': Decimal('0'),
            },
            findings={'error': error_note},
            user=user,
            notes=f"Analyse fehlgeschlagen: {error_note}"
        )
    
    def get_open_issues(self, chapter_id: UUID) -> list:
        """Holt alle offenen Style-Issues für ein Kapitel"""
        from ..models_quality import StyleIssue
        
        return list(StyleIssue.objects.filter(
            quality_score__chapter_id=chapter_id,
            is_fixed=False,
            is_ignored=False
        ).select_related(
            'issue_type', 'quality_score'
        ).order_by('-issue_type__severity'))
    
    def fix_issue(self, issue_id: UUID, user=None) -> bool:
        """Markiert Issue als behoben"""
        from ..models_quality import StyleIssue
        
        try:
            issue = StyleIssue.objects.get(pk=issue_id)
            issue.is_fixed = True
            issue.fixed_at = timezone.now()
            issue.fixed_by = user
            issue.save()
            
            logger.info(f"Issue {issue_id} marked as fixed")
            return True
        except StyleIssue.DoesNotExist:
            logger.warning(f"Issue {issue_id} not found")
            return False
    
    def ignore_issue(self, issue_id: UUID) -> bool:
        """Markiert Issue als ignoriert (false positive)"""
        from ..models_quality import StyleIssue
        
        try:
            issue = StyleIssue.objects.get(pk=issue_id)
            issue.is_ignored = True
            issue.save()
            
            logger.info(f"Issue {issue_id} marked as ignored")
            return True
        except StyleIssue.DoesNotExist:
            return False


# Singleton-Instanz
style_quality_service = StyleQualityService()
