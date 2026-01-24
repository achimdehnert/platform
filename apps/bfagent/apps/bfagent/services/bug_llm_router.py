"""
Bug LLM Router Service
======================

Intelligente Zuweisung von Bugs zu LLMs basierend auf Komplexität.
Implementiert das 3-Tier-System für Kosten-Optimierung.

Usage:
    from apps.bfagent.services.bug_llm_router import BugLLMRouter
    
    router = BugLLMRouter()
    assignment = router.create_assignment(requirement)
    llm = router.get_llm_for_tier(assignment.current_tier)
"""

import logging
from typing import Optional, Tuple
from decimal import Decimal
from django.utils import timezone

from apps.bfagent.models_testing import TestRequirement, BugLLMAssignment
from apps.bfagent.models_main import Llms

logger = logging.getLogger(__name__)


class BugLLMRouter:
    """
    Haupt-Service für LLM-Routing bei Bug-Resolution.
    
    Workflow:
    1. Bug klassifizieren → Tier zuweisen
    2. LLM für Tier auswählen
    3. Versuch tracken
    4. Bei Fehler: Eskalieren
    """
    
    # LLM-Mapping pro Tier (in Präferenz-Reihenfolge)
    TIER_LLM_MAPPING = {
        'tier_1': [
            ('gpt-3.5-turbo', 0.5),      # $0.50/1M tokens
            ('claude-3-haiku', 0.25),     # $0.25/1M tokens
            ('gpt-4o-mini', 0.15),        # $0.15/1M tokens
        ],
        'tier_2': [
            ('gpt-4o-mini', 0.15),        # Günstigste Option zuerst
            ('claude-3-5-sonnet', 3.0),   # $3/1M tokens
            ('gpt-4o', 2.5),              # $2.50/1M tokens
        ],
        'tier_3': [
            ('claude-3-5-sonnet', 3.0),   # Günstigste zuerst
            ('gpt-4-turbo', 10.0),        # $10/1M tokens
            ('claude-3-opus', 15.0),      # $15/1M tokens
            ('gpt-4', 30.0),              # $30/1M tokens
        ],
    }
    
    # Eskalations-Trigger
    ESCALATION_TRIGGERS = {
        'compile_error': True,
        'test_failure': True,
        'confidence_low': True,  # < 70%
        'timeout': True,
        'max_attempts': 2,
    }
    
    def __init__(self):
        self.available_llms = self._load_available_llms()
    
    def _load_available_llms(self) -> dict:
        """Lädt verfügbare LLMs aus der Datenbank."""
        llms = {}
        for llm in Llms.objects.filter(is_active=True):
            llms[llm.name.lower()] = llm
        return llms
    
    def create_assignment(self, requirement: TestRequirement) -> BugLLMAssignment:
        """
        Erstellt eine neue LLM-Zuweisung für ein Requirement/Bug.
        
        Args:
            requirement: Das zu bearbeitende Requirement
            
        Returns:
            BugLLMAssignment mit initialem Tier
        """
        # Komplexität bestimmen
        complexity = requirement.get_effective_complexity()
        
        # Tier-Mapping
        tier_mapping = {
            'low': BugLLMAssignment.Tier.TIER_1,
            'medium': BugLLMAssignment.Tier.TIER_2,
            'high': BugLLMAssignment.Tier.TIER_3,
        }
        initial_tier = tier_mapping.get(complexity, BugLLMAssignment.Tier.TIER_1)
        
        # Complexity Score berechnen
        complexity_score = self._calculate_complexity_score(requirement)
        
        # Assignment erstellen
        assignment = BugLLMAssignment.objects.create(
            requirement=requirement,
            initial_tier=initial_tier,
            current_tier=initial_tier,
            complexity_score=complexity_score,
            status=BugLLMAssignment.Status.PENDING,
        )
        
        logger.info(f"[BUG-ROUTER] Created assignment {assignment.id} "
                   f"for '{requirement.name}' with tier={initial_tier}")
        
        return assignment
    
    def _calculate_complexity_score(self, requirement: TestRequirement) -> int:
        """Berechnet einen numerischen Complexity-Score."""
        score = 0
        
        # Kategorie
        category_scores = {
            'bug_fix': 1,
            'feature': 2,
            'enhancement': 2,
            'refactor': 3,
            'performance': 3,
            'security': 4,
        }
        score += category_scores.get(requirement.category, 2)
        
        # Keywords
        desc = (requirement.description or '').lower()
        complex_keywords = ['migration', 'database', 'api', 'auth', 'refactor']
        simple_keywords = ['typo', 'text', 'label', 'css', 'color']
        
        score += sum(2 for kw in complex_keywords if kw in desc)
        score -= sum(1 for kw in simple_keywords if kw in desc)
        
        # Domain
        domain_scores = {
            'core': 3,
            'control_center': 2,
            'writing_hub': 1,
            'genagent': 2,
            'medtrans': 1,
        }
        score += domain_scores.get(requirement.domain, 1)
        
        # Acceptance Criteria
        criteria_count = len(requirement.acceptance_criteria or [])
        if criteria_count >= 4:
            score += 2
        elif criteria_count >= 2:
            score += 1
        
        return max(0, score)
    
    def get_llm_for_tier(self, tier: str) -> Tuple[Optional[Llms], float]:
        """
        Gibt das beste verfügbare LLM für einen Tier zurück.
        
        Args:
            tier: 'tier_1', 'tier_2', oder 'tier_3'
            
        Returns:
            Tuple (LLM-Objekt, Kosten pro 1M Tokens)
        """
        tier_llms = self.TIER_LLM_MAPPING.get(tier, self.TIER_LLM_MAPPING['tier_2'])
        
        for model_name, cost_per_1m in tier_llms:
            # Suche nach passendem LLM
            for llm_key, llm in self.available_llms.items():
                if model_name.lower() in llm_key:
                    return llm, cost_per_1m
        
        # Fallback: Erstes verfügbares LLM
        if self.available_llms:
            first_llm = next(iter(self.available_llms.values()))
            return first_llm, 1.0
        
        return None, 0.0
    
    def record_attempt(
        self,
        assignment: BugLLMAssignment,
        llm: Llms,
        tokens_used: int,
        success: bool,
        error: str = None,
        confidence: float = None
    ) -> bool:
        """
        Zeichnet einen LLM-Versuch auf.
        
        Args:
            assignment: Die LLM-Zuweisung
            llm: Das verwendete LLM
            tokens_used: Anzahl verbrauchter Tokens
            success: War der Versuch erfolgreich?
            error: Fehlermeldung (falls vorhanden)
            confidence: Konfidenz der Lösung (0-1)
            
        Returns:
            True wenn eskaliert wurde, False sonst
        """
        # Kosten berechnen
        _, cost_per_1m = self.get_llm_for_tier(assignment.current_tier)
        cost = Decimal(str((tokens_used / 1_000_000) * cost_per_1m))
        
        # Versuch aufzeichnen
        assignment.record_attempt(
            llm_name=llm.name,
            tokens=tokens_used,
            cost=float(cost),
            success=success,
            error=error
        )
        
        if success:
            assignment.resolution_confidence = confidence
            assignment.llm_used = llm
            assignment.save()
            logger.info(f"[BUG-ROUTER] Assignment {assignment.id} resolved "
                       f"with {llm.name} (confidence={confidence})")
            return False
        
        # Prüfe Eskalation
        should_escalate = self._should_escalate(assignment, error, confidence)
        
        if should_escalate:
            escalated = assignment.escalate(error)
            if escalated:
                logger.info(f"[BUG-ROUTER] Assignment {assignment.id} "
                           f"escalated to {assignment.current_tier}")
            return escalated
        
        return False
    
    def _should_escalate(
        self,
        assignment: BugLLMAssignment,
        error: str = None,
        confidence: float = None
    ) -> bool:
        """Prüft ob eskaliert werden soll."""
        
        # Max Versuche pro Tier erreicht?
        tier_attempts = sum(
            1 for a in assignment.attempt_history 
            if a.get('tier') == assignment.current_tier
        )
        if tier_attempts >= self.ESCALATION_TRIGGERS['max_attempts']:
            return True
        
        # Compile Error?
        if error and 'compile' in error.lower():
            return True
        
        # Test Failure?
        if error and ('test' in error.lower() or 'assert' in error.lower()):
            return True
        
        # Niedrige Konfidenz?
        if confidence is not None and confidence < 0.7:
            return True
        
        return False
    
    def get_assignment_stats(self, assignment: BugLLMAssignment) -> dict:
        """Gibt Statistiken für eine Zuweisung zurück."""
        return {
            'id': str(assignment.id),
            'requirement': assignment.requirement.name,
            'initial_tier': assignment.initial_tier,
            'current_tier': assignment.current_tier,
            'escalations': assignment.escalation_count,
            'attempts': assignment.attempts,
            'tokens_total': assignment.total_tokens,
            'cost_usd': float(assignment.cost_usd),
            'savings_usd': assignment.calculate_savings(),
            'status': assignment.status,
            'duration_seconds': assignment.duration_seconds,
        }


class BugLLMRouterService:
    """
    High-Level Service für Bug-Resolution mit LLM-Routing.
    
    Usage:
        service = BugLLMRouterService()
        result = service.resolve_bug(requirement)
    """
    
    def __init__(self):
        self.router = BugLLMRouter()
    
    def resolve_bug(
        self,
        requirement: TestRequirement,
        max_tiers: int = 3
    ) -> dict:
        """
        Versucht einen Bug zu lösen mit automatischer Eskalation.
        
        Args:
            requirement: Das zu lösende Requirement/Bug
            max_tiers: Maximale Anzahl an Tier-Eskalationen
            
        Returns:
            Dict mit Ergebnis und Statistiken
        """
        # Assignment erstellen
        assignment = self.router.create_assignment(requirement)
        assignment.status = BugLLMAssignment.Status.IN_PROGRESS
        assignment.started_at = timezone.now()
        assignment.save()
        
        tiers_tried = 0
        
        while tiers_tried < max_tiers:
            # LLM für aktuellen Tier holen
            llm, cost = self.router.get_llm_for_tier(assignment.current_tier)
            
            if not llm:
                logger.error("[BUG-ROUTER] No LLM available!")
                assignment.status = BugLLMAssignment.Status.FAILED
                assignment.save()
                break
            
            # Hier würde der eigentliche LLM-Aufruf stattfinden
            # Für jetzt: Placeholder
            logger.info(f"[BUG-ROUTER] Would call {llm.name} for tier {assignment.current_tier}")
            
            # In der echten Implementierung:
            # result = self._call_llm(llm, requirement)
            # success = result.get('success', False)
            # ...
            
            tiers_tried += 1
            
            # Für Demo: Nach einem Versuch abbrechen
            break
        
        return self.router.get_assignment_stats(assignment)
