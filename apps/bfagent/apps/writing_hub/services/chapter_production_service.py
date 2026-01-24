"""
Chapter Production Service
===========================

Unified pipeline for chapter production:
1. Brief    → Generate chapter brief from outline
2. Write    → LLM writes chapter content
3. Analyze  → Quality analysis with QualityGateService
4. Gate     → Decision (approve/review/revise/reject)
5. Commit   → Save or loop back

Integrates: ChapterWriterHandler + QualityGateService
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class ProductionStage(str, Enum):
    """Stages in chapter production pipeline"""
    BRIEF = "brief"
    WRITE = "write"
    ANALYZE = "analyze"
    GATE = "gate"
    REVISE = "revise"
    COMMIT = "commit"


@dataclass
class BriefResult:
    """Result of brief generation"""
    success: bool
    brief: str = ""
    production_goals: List[str] = field(default_factory=list)
    tone_notes: str = ""
    continuity_notes: str = ""
    error: str = ""


@dataclass
class WriteResult:
    """Result of chapter writing"""
    success: bool
    content: str = ""
    word_count: int = 0
    tokens_used: int = 0
    cost: Decimal = Decimal("0")
    error: str = ""


@dataclass
class AnalyzeResult:
    """Result of quality analysis"""
    success: bool
    overall_score: Decimal = Decimal("0")
    dimension_scores: Dict[str, Decimal] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    issues: List[Dict] = field(default_factory=list)
    error: str = ""


@dataclass
class GateResult:
    """Result of gate decision"""
    decision: str = "review"  # approve, review, revise, reject
    allows_commit: bool = False
    reason: str = ""
    required_fixes: List[str] = field(default_factory=list)


@dataclass
class ProductionResult:
    """Complete production pipeline result"""
    success: bool
    stage: ProductionStage
    chapter_id: Optional[UUID] = None
    
    brief: Optional[BriefResult] = None
    write: Optional[WriteResult] = None
    analyze: Optional[AnalyzeResult] = None
    gate: Optional[GateResult] = None
    
    iterations: int = 1
    total_tokens: int = 0
    total_cost: Decimal = Decimal("0")
    duration_seconds: float = 0.0
    error: str = ""


class ChapterProductionService:
    """
    Orchestrates the complete chapter production pipeline.
    
    Usage:
        service = ChapterProductionService(project_id, user)
        
        # Full pipeline
        result = service.produce_chapter(chapter_id)
        
        # Individual stages
        brief = service.generate_brief(chapter_id)
        write = service.write_chapter(chapter_id, brief)
        analyze = service.analyze_chapter(chapter_id)
        gate = service.evaluate_gate(chapter_id, analyze)
    """
    
    def __init__(self, project_id: UUID, user=None):
        from apps.writing_hub.models import BookProject, Chapter
        
        self.project = BookProject.objects.get(project_id=project_id)
        self.user = user
        self._quality_service = None
    
    @property
    def quality_service(self):
        """Lazy load quality gate service"""
        if self._quality_service is None:
            from apps.writing_hub.services.quality_gate_service import quality_gate_service
            self._quality_service = quality_gate_service
        return self._quality_service
    
    def produce_chapter(
        self,
        chapter_id: UUID,
        max_iterations: int = 3,
        auto_commit: bool = False
    ) -> ProductionResult:
        """
        Run complete production pipeline for a chapter.
        
        Args:
            chapter_id: UUID of the chapter to produce
            max_iterations: Max revision cycles before requiring manual review
            auto_commit: If True, auto-commit on approval
            
        Returns:
            ProductionResult with all stage results
        """
        import time
        start_time = time.time()
        
        from apps.writing_hub.models import Chapter
        
        try:
            chapter = Chapter.objects.get(chapter_id=chapter_id)
        except Chapter.DoesNotExist:
            return ProductionResult(
                success=False,
                stage=ProductionStage.BRIEF,
                error=f"Chapter {chapter_id} not found"
            )
        
        result = ProductionResult(
            success=False,
            stage=ProductionStage.BRIEF,
            chapter_id=chapter_id
        )
        
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            result.iterations = iteration
            
            # Stage 1: BRIEF
            if not result.brief or iteration > 1:
                result.brief = self.generate_brief(chapter)
                result.stage = ProductionStage.BRIEF
                
                if not result.brief.success:
                    result.error = result.brief.error
                    break
            
            # Stage 2: WRITE
            result.write = self.write_chapter(chapter, result.brief)
            result.stage = ProductionStage.WRITE
            
            if not result.write.success:
                result.error = result.write.error
                break
            
            result.total_tokens += result.write.tokens_used
            result.total_cost += result.write.cost
            
            # Stage 3: ANALYZE
            result.analyze = self.analyze_chapter(chapter, result.write.content)
            result.stage = ProductionStage.ANALYZE
            
            if not result.analyze.success:
                result.error = result.analyze.error
                break
            
            # Stage 4: GATE
            result.gate = self.evaluate_gate(chapter, result.analyze)
            result.stage = ProductionStage.GATE
            
            # Check gate decision
            if result.gate.decision == "approve":
                result.success = True
                if auto_commit:
                    self._commit_chapter(chapter, result)
                    result.stage = ProductionStage.COMMIT
                break
            
            elif result.gate.decision == "review":
                # Needs manual review - stop pipeline
                result.success = True  # Pipeline succeeded, needs human
                break
            
            elif result.gate.decision == "revise":
                # Auto-revise if iterations remaining
                if iteration < max_iterations:
                    result.stage = ProductionStage.REVISE
                    logger.info(f"Chapter {chapter_id} needs revision (iteration {iteration})")
                    continue
                else:
                    # Max iterations reached
                    result.success = True
                    result.gate.reason += f" (max {max_iterations} iterations reached)"
                    break
            
            elif result.gate.decision == "reject":
                # Hard reject - needs major rework
                result.success = False
                result.error = "Chapter rejected by quality gate"
                break
        
        result.duration_seconds = time.time() - start_time
        return result
    
    def generate_brief(self, chapter) -> BriefResult:
        """
        Generate production brief for a chapter.
        
        Extracts from outline:
        - 5-7 production goals
        - Tone and style notes
        - Continuity requirements
        """
        from apps.writing_hub.models import Chapter
        
        # Get chapter context
        outline = chapter.outline or ""
        notes = chapter.notes or ""
        
        # Get previous chapter for continuity
        prev_chapter = Chapter.objects.filter(
            project=self.project,
            chapter_number=chapter.chapter_number - 1
        ).first()
        
        prev_summary = ""
        if prev_chapter and prev_chapter.content:
            prev_summary = prev_chapter.content[-500:]
        
        # Build production goals from outline
        production_goals = self._extract_production_goals(outline, notes)
        
        # Tone notes from project style
        tone_notes = self._get_tone_notes()
        
        # Continuity notes
        continuity_notes = self._get_continuity_notes(chapter, prev_summary)
        
        # Combine into brief
        brief_parts = [
            f"# Kapitel {chapter.chapter_number}: {chapter.title or 'Untitled'}",
            "",
            "## Produktionsziele:",
            *[f"- {goal}" for goal in production_goals],
            "",
            f"## Stil & Ton:\n{tone_notes}",
            "",
            f"## Kontinuität:\n{continuity_notes}",
            "",
            f"## Outline:\n{outline}" if outline else "## Outline: (Kein Outline vorhanden)",
        ]
        
        return BriefResult(
            success=True,
            brief="\n".join(brief_parts),
            production_goals=production_goals,
            tone_notes=tone_notes,
            continuity_notes=continuity_notes
        )
    
    def write_chapter(self, chapter, brief: BriefResult) -> WriteResult:
        """
        Write chapter content using LLM.
        """
        from apps.writing_hub.handlers.chapter_writer_handler import (
            ChapterWriterHandler,
            ChapterContext
        )
        
        # Build context
        context = ChapterContext.from_chapter(
            project_id=self.project.project_id,
            chapter_id=chapter.chapter_id
        )
        
        # Add brief to context
        context.chapter_outline = brief.brief
        
        # Get handler
        handler = ChapterWriterHandler()
        
        try:
            # Write chapter
            result = handler.write_chapter(context)
            
            if result.get('success'):
                content = result.get('content', '')
                return WriteResult(
                    success=True,
                    content=content,
                    word_count=len(content.split()),
                    tokens_used=result.get('tokens_used', 0),
                    cost=Decimal(str(result.get('cost', 0)))
                )
            else:
                return WriteResult(
                    success=False,
                    error=result.get('error', 'Unknown write error')
                )
                
        except Exception as e:
            logger.exception(f"Chapter write failed: {e}")
            return WriteResult(success=False, error=str(e))
    
    def analyze_chapter(self, chapter, content: str) -> AnalyzeResult:
        """
        Analyze chapter quality using LLM and QualityGateService.
        """
        # Use LLM to get dimension scores
        dimension_scores = self._analyze_with_llm(chapter, content)
        
        if not dimension_scores:
            # Fallback: mock scores for testing
            dimension_scores = {
                'style': Decimal('7.5'),
                'genre': Decimal('8.0'),
                'scene': Decimal('7.0'),
                'serial_logic': Decimal('8.5'),
            }
        
        # Calculate overall score (weighted)
        total_weight = Decimal('0')
        weighted_sum = Decimal('0')
        
        from apps.writing_hub.models_quality import QualityDimension
        dimensions = QualityDimension.objects.filter(is_active=True)
        
        for dim in dimensions:
            if dim.code in dimension_scores:
                weighted_sum += dimension_scores[dim.code] * dim.weight
                total_weight += dim.weight
        
        overall_score = weighted_sum / total_weight if total_weight > 0 else Decimal('0')
        
        # Get strengths and issues
        strengths = []
        issues = []
        
        for code, score in dimension_scores.items():
            if score >= Decimal('8.0'):
                strengths.append(f"{code}: {score}/10")
            elif score < Decimal('7.0'):
                issues.append({
                    'dimension': code,
                    'score': float(score),
                    'severity': 3 if score < Decimal('6.0') else 2
                })
        
        return AnalyzeResult(
            success=True,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            strengths=strengths,
            issues=issues
        )
    
    def evaluate_gate(self, chapter, analyze: AnalyzeResult) -> GateResult:
        """
        Evaluate quality gate for chapter.
        """
        from apps.writing_hub.models_quality import (
            ProjectQualityConfig,
            GateDecisionType
        )
        
        # Get project config or use defaults
        try:
            config = ProjectQualityConfig.objects.get(project=self.project)
        except ProjectQualityConfig.DoesNotExist:
            config = None
        
        min_overall = config.min_overall_score if config else Decimal('7.5')
        auto_approve = config.auto_approve_threshold if config else Decimal('8.5')
        auto_reject = config.auto_reject_threshold if config else Decimal('5.0')
        
        score = analyze.overall_score
        
        # Determine decision
        if score >= auto_approve:
            decision = "approve"
            reason = f"Score {score:.1f} >= {auto_approve:.1f} (auto-approve threshold)"
            allows_commit = True
        elif score >= min_overall:
            decision = "review"
            reason = f"Score {score:.1f} >= {min_overall:.1f} but < {auto_approve:.1f} (needs review)"
            allows_commit = False
        elif score >= auto_reject:
            decision = "revise"
            reason = f"Score {score:.1f} < {min_overall:.1f} (needs revision)"
            allows_commit = False
        else:
            decision = "reject"
            reason = f"Score {score:.1f} < {auto_reject:.1f} (rejected)"
            allows_commit = False
        
        # Get required fixes from issues
        required_fixes = []
        for issue in analyze.issues:
            required_fixes.append(f"Fix {issue['dimension']}: score {issue['score']}/10")
        
        return GateResult(
            decision=decision,
            allows_commit=allows_commit,
            reason=reason,
            required_fixes=required_fixes
        )
    
    def _commit_chapter(self, chapter, result: ProductionResult):
        """Save chapter content to database"""
        with transaction.atomic():
            chapter.content = result.write.content
            chapter.word_count = result.write.word_count
            chapter.status = 'draft'
            chapter.save()
            
            # Create quality score record
            if result.analyze:
                self.quality_service.evaluate_chapter(
                    chapter_id=chapter.chapter_id,
                    dimension_scores=result.analyze.dimension_scores,
                    user=self.user
                )
            
            logger.info(f"Chapter {chapter.chapter_id} committed")
    
    def _extract_production_goals(self, outline: str, notes: str) -> List[str]:
        """Extract 5-7 production goals from outline"""
        goals = []
        
        if outline:
            # Split outline into sentences/bullets
            lines = [l.strip() for l in outline.split('\n') if l.strip()]
            goals.extend(lines[:5])
        
        # Add standard goals if needed
        if len(goals) < 5:
            standard_goals = [
                "Szene mit lebendigem Dialog eröffnen",
                "Charakter-Entwicklung zeigen",
                "Setting atmosphärisch beschreiben",
                "Konflikt oder Spannung aufbauen",
                "Mit Hook zum nächsten Kapitel enden",
            ]
            for g in standard_goals:
                if len(goals) < 7 and g not in goals:
                    goals.append(g)
        
        return goals[:7]
    
    def _get_tone_notes(self) -> str:
        """Get tone/style notes for project"""
        parts = []
        
        if self.project.genre:
            parts.append(f"Genre: {self.project.genre}")
        
        if hasattr(self.project, 'content_rating') and self.project.content_rating:
            parts.append(f"Content Rating: {self.project.content_rating}")
        
        # Add default style notes
        parts.append("Stil: Lebhaft, literarisch, Show don't Tell")
        
        return "\n".join(parts) if parts else "Standard literarischer Stil"
    
    def _get_continuity_notes(self, chapter, prev_summary: str) -> str:
        """Get continuity notes for chapter"""
        notes = []
        
        if prev_summary:
            notes.append(f"Vorheriges Kapitel endete mit:\n{prev_summary[:300]}...")
        
        if chapter.chapter_number == 1:
            notes.append("Erstes Kapitel - Einführung der Hauptfiguren und Setting")
        
        return "\n".join(notes) if notes else "Keine besonderen Kontinuitäts-Anforderungen"
    
    def _analyze_with_llm(self, chapter, content: str) -> Dict[str, Decimal]:
        """Analyze chapter with LLM to get dimension scores"""
        # TODO: Implement LLM-based analysis
        # For now, return mock scores based on content length
        word_count = len(content.split())
        
        # Simple heuristic scoring
        base_score = Decimal('7.0')
        
        # Bonus for word count target
        target = chapter.target_word_count or 2000
        word_ratio = min(word_count / target, 1.5)
        length_bonus = Decimal(str(min(word_ratio * 0.5, 1.0)))
        
        return {
            'style': base_score + length_bonus,
            'genre': base_score + Decimal('0.5'),
            'scene': base_score + length_bonus - Decimal('0.5'),
            'serial_logic': base_score + Decimal('1.0'),
        }


# Singleton instance
chapter_production_service = None


def get_chapter_production_service(project_id: UUID, user=None) -> ChapterProductionService:
    """Get or create chapter production service instance"""
    return ChapterProductionService(project_id, user)
