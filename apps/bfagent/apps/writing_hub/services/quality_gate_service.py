"""
Quality Gate Service
====================

Business Logic für Quality Gate Evaluation.
Separation of Concerns: Keine Business Logic in Models oder Views.

Alle Gate-Entscheidungen werden hier berechnet, nicht in SQL Triggers.
"""
import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction

logger = logging.getLogger(__name__)


class QualityGateService:
    """
    Service für Quality Gate Evaluation.
    
    Verantwortlich für:
    - Berechnung gewichteter Scores
    - Gate-Entscheidungen basierend auf Konfiguration
    - Erstellen von ChapterQualityScore Records
    """
    
    def evaluate_chapter(
        self,
        chapter_id: str,
        dimension_scores: dict[str, Decimal],
        findings: Optional[dict] = None,
        pipeline_execution_id: Optional[str] = None,
        user=None,
        notes: str = ""
    ):
        """
        Bewertet ein Kapitel und erstellt Score + Gate-Entscheidung.
        
        Args:
            chapter_id: UUID des Kapitels
            dimension_scores: {'style': Decimal('8.5'), 'genre': Decimal('7.2'), ...}
            findings: Optionale strukturierte Findings
            pipeline_execution_id: Optional LLM Run ID
            user: Bewerter (User instance)
            notes: Optionale Notizen
            
        Returns:
            ChapterQualityScore mit Gate-Entscheidung
        """
        from apps.bfagent.models import BookChapters
        from ..models_quality import (
            ChapterQualityScore,
            ChapterDimensionScore,
            QualityDimension,
            GateDecisionType,
        )
        
        chapter = BookChapters.objects.select_related('project').get(pk=chapter_id)
        config = self._get_or_create_config(chapter.project_id)
        
        # Berechne Overall Score (gewichtet)
        overall = self._compute_weighted_score(dimension_scores)
        
        # Bestimme Gate-Entscheidung
        decision = self._compute_gate_decision(overall, dimension_scores, config)
        
        logger.info(
            f"Evaluating chapter {chapter_id}: overall={overall}, decision={decision.code}"
        )
        
        # Erstelle Score mit allen Dimensionen
        with transaction.atomic():
            score = ChapterQualityScore.objects.create(
                chapter=chapter,
                scored_by=user,
                gate_decision=decision,
                overall_score=overall,
                findings=findings or {},
                pipeline_execution_id=pipeline_execution_id,
                notes=notes,
            )
            
            # Erstelle Dimension-Scores
            dimensions = {
                d.code: d 
                for d in QualityDimension.objects.filter(
                    code__in=dimension_scores.keys(),
                    is_active=True
                )
            }
            
            for code, value in dimension_scores.items():
                if code in dimensions:
                    ChapterDimensionScore.objects.create(
                        quality_score=score,
                        dimension=dimensions[code],
                        score=value
                    )
                else:
                    logger.warning(f"Unknown dimension code: {code}")
        
        return score
    
    def _compute_weighted_score(self, scores: dict[str, Decimal]) -> Decimal:
        """
        Berechnet gewichteten Durchschnitt basierend auf Dimension-Gewichten.
        """
        from ..models_quality import QualityDimension
        
        dimensions = QualityDimension.objects.filter(
            code__in=scores.keys(),
            is_active=True
        )
        
        total_weight = Decimal('0')
        weighted_sum = Decimal('0')
        
        for dim in dimensions:
            if dim.code in scores:
                weighted_sum += Decimal(str(scores[dim.code])) * dim.weight
                total_weight += dim.weight
        
        if total_weight == 0:
            return Decimal('0')
        
        return (weighted_sum / total_weight).quantize(Decimal('0.01'))
    
    def _compute_gate_decision(
        self,
        overall: Decimal,
        scores: dict[str, Decimal],
        config
    ):
        """
        Bestimmt Gate-Entscheidung basierend auf Konfiguration.
        
        Logik:
        1. Unter auto_reject_threshold → reject
        2. Über auto_approve_threshold + alle Dimensionen OK → approve
        3. Unter min_overall_score → revise
        4. Sonst → review
        """
        from ..models_quality import GateDecisionType
        
        # Auto-Reject wenn unter Schwelle
        if overall < config.auto_reject_threshold:
            logger.debug(f"Auto-reject: {overall} < {config.auto_reject_threshold}")
            return GateDecisionType.objects.get(code='reject')
        
        # Unter Minimum → revise
        if overall < config.min_overall_score:
            logger.debug(f"Revise: {overall} < {config.min_overall_score}")
            return GateDecisionType.objects.get(code='revise')
        
        # Prüfe ob alle Dimensionen über Minimum (wenn config.require_manual_approval=False)
        if overall >= config.auto_approve_threshold and not config.require_manual_approval:
            thresholds = {
                t.dimension.code: t.min_score
                for t in config.dimension_thresholds.select_related('dimension').all()
            }
            
            all_pass = True
            for code, min_score in thresholds.items():
                if code in scores and Decimal(str(scores[code])) < min_score:
                    all_pass = False
                    logger.debug(f"Dimension {code} failed: {scores[code]} < {min_score}")
                    break
            
            if all_pass:
                logger.debug(f"Auto-approve: {overall} >= {config.auto_approve_threshold}")
                return GateDecisionType.objects.get(code='approve')
        
        # Sonst Review
        logger.debug(f"Review: {overall} (manual approval required or dimension failed)")
        return GateDecisionType.objects.get(code='review')
    
    def _get_or_create_config(self, project_id: str):
        """
        Holt oder erstellt Default-Config für ein Projekt.
        """
        from ..models_quality import ProjectQualityConfig
        
        config, created = ProjectQualityConfig.objects.get_or_create(
            project_id=project_id
        )
        
        if created:
            logger.info(f"Created default quality config for project {project_id}")
        
        return config
    
    def get_latest_score(self, chapter_id: str):
        """
        Holt den neuesten Score für ein Kapitel.
        """
        from ..models_quality import ChapterQualityScore
        
        return ChapterQualityScore.objects.filter(
            chapter_id=chapter_id
        ).select_related(
            'gate_decision'
        ).prefetch_related(
            'dimension_scores__dimension'
        ).order_by('-scored_at').first()
    
    def get_chapter_history(self, chapter_id: str, limit: int = 10):
        """
        Holt Score-Historie für ein Kapitel.
        """
        from ..models_quality import ChapterQualityScore
        
        return ChapterQualityScore.objects.filter(
            chapter_id=chapter_id
        ).select_related(
            'gate_decision', 'scored_by'
        ).order_by('-scored_at')[:limit]
    
    def can_commit_chapter(self, chapter_id: str) -> tuple[bool, str]:
        """
        Prüft ob ein Kapitel committed/locked werden kann.
        
        Returns:
            (can_commit, reason)
        """
        latest = self.get_latest_score(chapter_id)
        
        if not latest:
            return False, "Kein Quality Score vorhanden"
        
        if not latest.gate_decision.allows_commit:
            return False, f"Gate-Entscheidung '{latest.gate_decision.name_de}' erlaubt keinen Commit"
        
        return True, "OK"


# Singleton-Instanz für einfachen Import
quality_gate_service = QualityGateService()
