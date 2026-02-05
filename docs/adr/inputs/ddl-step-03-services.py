# ============================================================================
# DOMAIN DEVELOPMENT LIFECYCLE - SERVICE LAYER
# Step 3: Services for Business Cases, Use Cases, Inception
# ============================================================================
#
# Part of: Domain Development Lifecycle System
# Compatible with: ADR-015 Platform Governance System
# Location: platform/governance/services/domain_services.py
#
# ============================================================================

"""
Service Layer für das Domain Development Lifecycle System.

Diese Services kapseln die Geschäftslogik und werden sowohl
von der Web-UI als auch vom MCP Server verwendet.

Usage:
    from governance.services import BusinessCaseService, InceptionService
    
    # Business Case erstellen
    bc = BusinessCaseService.create(
        title="Reisekostenabrechnung",
        problem_statement="...",
        category_code="neue_domain",
        owner=request.user,
    )
    
    # Inception starten
    session = InceptionService.start_session(
        initial_input="Ich brauche eine Reisekostenabrechnung mit OCR",
        user=request.user,
    )
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from governance.models import BusinessCase, UseCase, ADR


# ============================================================================
# SECTION 1: DATA CLASSES
# ============================================================================

@dataclass
class InceptionSession:
    """Session-Daten für den Inception-Prozess."""
    session_id: str
    business_case_id: int
    turn: int = 1
    answered_questions: list[dict] = field(default_factory=list)
    pending_questions: list[str] = field(default_factory=list)
    extracted_data: dict = field(default_factory=dict)
    status: str = "in_progress"


@dataclass
class InceptionQuestion:
    """Eine Frage im Inception-Prozess."""
    question: str
    field_name: str
    required: bool = True
    validation: Optional[str] = None
    examples: list[str] = field(default_factory=list)


@dataclass
class DerivedUseCase:
    """Ein aus dem Business Case abgeleiteter Use Case."""
    title: str
    description: str
    actor: str
    priority_code: str = "medium"
    complexity_code: str = "moderate"
    main_flow_draft: list[str] = field(default_factory=list)


# ============================================================================
# SECTION 2: LOOKUP SERVICE (from ADR-015)
# ============================================================================

class LookupService:
    """
    Service für Zugriff auf Lookup-Tabellen (lkp_choice).
    Cached für Performance.
    """
    
    _cache: dict[str, dict] = {}
    
    @classmethod
    def get_choices(
        cls,
        domain: str,
        include_inactive: bool = False,
        parent_code: Optional[str] = None,
    ) -> list[dict]:
        """
        Holt alle Choices einer Domain.
        
        Args:
            domain: Domain-Code (z.B. 'bc_status')
            include_inactive: Auch inaktive Choices
            parent_code: Nur Kinder dieses Parents
            
        Returns:
            Liste von Choice-Dictionaries
        """
        from governance.models import LookupChoice
        
        cache_key = f"{domain}:{include_inactive}:{parent_code}"
        
        if cache_key not in cls._cache:
            qs = LookupChoice.objects.filter(domain__code=domain)
            
            if not include_inactive:
                qs = qs.filter(
                    Q(valid_from__isnull=True) | Q(valid_from__lte=timezone.now()),
                    Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now()),
                    is_active=True,
                )
            
            if parent_code:
                qs = qs.filter(parent__code=parent_code)
            
            cls._cache[cache_key] = list(
                qs.order_by('sort_order').values(
                    'id', 'code', 'name', 'description', 'metadata'
                )
            )
        
        return cls._cache[cache_key]
    
    @classmethod
    def get_choice(cls, domain: str, code: str) -> Optional[Any]:
        """Holt eine einzelne Choice."""
        from governance.models import LookupChoice
        
        try:
            return LookupChoice.objects.get(domain__code=domain, code=code)
        except LookupChoice.DoesNotExist:
            return None
    
    @classmethod
    def get_choice_id(cls, domain: str, code: str) -> Optional[int]:
        """Holt nur die ID einer Choice."""
        choice = cls.get_choice(domain, code)
        return choice.id if choice else None
    
    @classmethod
    def clear_cache(cls) -> None:
        """Leert den Cache."""
        cls._cache.clear()


# ============================================================================
# SECTION 3: BUSINESS CASE SERVICE
# ============================================================================

class BusinessCaseService:
    """
    Service für Business Case Operationen.
    """
    
    @classmethod
    @transaction.atomic
    def create(
        cls,
        title: str,
        problem_statement: str,
        category_code: str,
        owner: Optional['User'] = None,
        **kwargs,
    ) -> 'BusinessCase':
        """
        Erstellt einen neuen Business Case.
        
        Args:
            title: Titel des Business Cases
            problem_statement: Problembeschreibung
            category_code: Kategorie-Code (neue_domain, integration, ...)
            owner: Owner des Business Cases
            **kwargs: Weitere Felder
            
        Returns:
            Erstellter BusinessCase
        """
        from governance.models import BusinessCase
        
        # Status und Kategorie holen
        status = LookupService.get_choice('bc_status', 'draft')
        category = LookupService.get_choice('bc_category', category_code)
        
        if not status or not category:
            raise ValueError(f"Invalid status or category: {category_code}")
        
        bc = BusinessCase.objects.create(
            title=title,
            problem_statement=problem_statement,
            category=category,
            status=status,
            owner=owner,
            **kwargs,
        )
        
        return bc
    
    @classmethod
    def get_by_code(cls, code: str) -> Optional['BusinessCase']:
        """Holt Business Case by Code."""
        from governance.models import BusinessCase
        return BusinessCase.objects.filter(code=code).first()
    
    @classmethod
    def search(
        cls,
        query: str,
        status_codes: Optional[list[str]] = None,
        category_codes: Optional[list[str]] = None,
        limit: int = 20,
    ) -> QuerySet['BusinessCase']:
        """
        Sucht Business Cases.
        
        Args:
            query: Suchbegriff (Full-Text)
            status_codes: Filter nach Status
            category_codes: Filter nach Kategorie
            limit: Max. Ergebnisse
            
        Returns:
            QuerySet mit Ergebnissen
        """
        from django.contrib.postgres.search import SearchQuery, SearchRank
        from governance.models import BusinessCase
        
        qs = BusinessCase.objects.all()
        
        if query:
            search_query = SearchQuery(query, config='german')
            qs = qs.annotate(
                rank=SearchRank('search_vector', search_query)
            ).filter(
                search_vector=search_query
            ).order_by('-rank')
        
        if status_codes:
            qs = qs.filter(status__code__in=status_codes)
        
        if category_codes:
            qs = qs.filter(category__code__in=category_codes)
        
        return qs[:limit]
    
    @classmethod
    @transaction.atomic
    def submit_for_review(
        cls,
        business_case: 'BusinessCase',
        user: Optional['User'] = None,
    ) -> 'BusinessCase':
        """
        Reicht Business Case zur Prüfung ein.
        """
        business_case.transition_to('submitted', user=user, reason="Zur Prüfung eingereicht")
        return business_case
    
    @classmethod
    @transaction.atomic
    def approve(
        cls,
        business_case: 'BusinessCase',
        reviewer: 'User',
        comments: str = "",
    ) -> 'BusinessCase':
        """
        Genehmigt einen Business Case.
        """
        from governance.models import Review
        
        # Review erstellen
        Review.objects.create(
            entity_type='business_case',
            entity_id=business_case.id,
            reviewer=reviewer,
            decision='approved',
            comments=comments,
        )
        
        # Status ändern
        business_case.transition_to(
            'approved',
            user=reviewer,
            reason=f"Genehmigt von {reviewer.username}: {comments}"
        )
        
        return business_case
    
    @classmethod
    def get_statistics(cls) -> dict:
        """
        Holt Statistiken über alle Business Cases.
        """
        from django.db.models import Count
        from governance.models import BusinessCase
        
        stats = BusinessCase.objects.values(
            'status__code', 'status__name'
        ).annotate(
            count=Count('id')
        ).order_by('status__sort_order')
        
        return {
            'by_status': list(stats),
            'total': BusinessCase.objects.count(),
        }


# ============================================================================
# SECTION 4: USE CASE SERVICE
# ============================================================================

class UseCaseService:
    """
    Service für Use Case Operationen.
    """
    
    @classmethod
    @transaction.atomic
    def create(
        cls,
        business_case: 'BusinessCase',
        title: str,
        actor: str = "",
        description: str = "",
        priority_code: str = "medium",
        **kwargs,
    ) -> 'UseCase':
        """
        Erstellt einen neuen Use Case.
        """
        from governance.models import UseCase
        
        status = LookupService.get_choice('uc_status', 'draft')
        priority = LookupService.get_choice('uc_priority', priority_code)
        
        # Sort Order berechnen
        max_order = UseCase.objects.filter(
            business_case=business_case
        ).order_by('-sort_order').values_list('sort_order', flat=True).first() or 0
        
        uc = UseCase.objects.create(
            business_case=business_case,
            title=title,
            description=description,
            actor=actor,
            status=status,
            priority=priority,
            sort_order=max_order + 10,
            **kwargs,
        )
        
        return uc
    
    @classmethod
    @transaction.atomic
    def create_bulk(
        cls,
        business_case: 'BusinessCase',
        use_cases: list[DerivedUseCase],
    ) -> list['UseCase']:
        """
        Erstellt mehrere Use Cases auf einmal.
        """
        created = []
        for i, uc_data in enumerate(use_cases):
            uc = cls.create(
                business_case=business_case,
                title=uc_data.title,
                description=uc_data.description,
                actor=uc_data.actor,
                priority_code=uc_data.priority_code,
                main_flow=[
                    {"step": j+1, "type": "user_action", "description": step}
                    for j, step in enumerate(uc_data.main_flow_draft)
                ] if uc_data.main_flow_draft else [],
            )
            created.append(uc)
        return created
    
    @classmethod
    def get_by_business_case(
        cls,
        business_case: 'BusinessCase',
    ) -> QuerySet['UseCase']:
        """Holt alle Use Cases eines Business Cases."""
        from governance.models import UseCase
        return UseCase.objects.filter(
            business_case=business_case
        ).order_by('sort_order')
    
    @classmethod
    @transaction.atomic
    def update_flow(
        cls,
        use_case: 'UseCase',
        main_flow: list[dict],
        alternative_flows: Optional[list[dict]] = None,
        exception_flows: Optional[list[dict]] = None,
    ) -> 'UseCase':
        """
        Aktualisiert die Flows eines Use Cases.
        """
        use_case.main_flow = main_flow
        
        if alternative_flows is not None:
            use_case.alternative_flows = alternative_flows
        
        if exception_flows is not None:
            use_case.exception_flows = exception_flows
        
        use_case.save()
        
        # Status auf 'detailed' setzen wenn noch draft
        if use_case.status.code == 'draft':
            use_case.transition_to('detailed')
        
        return use_case


# ============================================================================
# SECTION 5: ADR SERVICE
# ============================================================================

class ADRService:
    """
    Service für ADR Operationen.
    """
    
    @classmethod
    @transaction.atomic
    def create(
        cls,
        title: str,
        context: str,
        decision: str,
        business_case: Optional['BusinessCase'] = None,
        consequences: str = "",
        alternatives: Optional[list[dict]] = None,
        **kwargs,
    ) -> 'ADR':
        """
        Erstellt einen neuen ADR.
        """
        from governance.models import ADR
        
        status = LookupService.get_choice('adr_status', 'proposed')
        
        adr = ADR.objects.create(
            title=title,
            context=context,
            decision=decision,
            consequences=consequences,
            business_case=business_case,
            status=status,
            alternatives=alternatives or [],
            **kwargs,
        )
        
        return adr
    
    @classmethod
    @transaction.atomic
    def accept(
        cls,
        adr: 'ADR',
        reviewer: 'User',
        comments: str = "",
    ) -> 'ADR':
        """
        Akzeptiert einen ADR.
        """
        from governance.models import Review
        
        Review.objects.create(
            entity_type='adr',
            entity_id=adr.id,
            reviewer=reviewer,
            decision='approved',
            comments=comments,
        )
        
        adr.status = LookupService.get_choice('adr_status', 'accepted')
        adr.decision_date = timezone.now().date()
        adr.save()
        
        return adr
    
    @classmethod
    @transaction.atomic
    def supersede(
        cls,
        old_adr: 'ADR',
        new_adr: 'ADR',
    ) -> tuple['ADR', 'ADR']:
        """
        Ersetzt einen ADR durch einen neuen.
        """
        # Neuen ADR mit Referenz versehen
        new_adr.supersedes = old_adr
        new_adr.save()
        
        # Alten ADR als ersetzt markieren
        old_adr.status = LookupService.get_choice('adr_status', 'superseded')
        old_adr.save()
        
        return old_adr, new_adr


# ============================================================================
# SECTION 6: INCEPTION SERVICE
# ============================================================================

class InceptionService:
    """
    Service für den Inception-Prozess (AI-gestützte BC-Erstellung).
    
    Dieser Service verwaltet den iterativen Dialog zur Erstellung
    eines Business Cases aus einer Freitext-Beschreibung.
    """
    
    # Session Storage (in Production: Redis)
    _sessions: dict[str, InceptionSession] = {}
    
    # Fragen-Templates nach Kategorie
    CATEGORY_QUESTIONS: dict[str, list[InceptionQuestion]] = {
        'default': [
            InceptionQuestion(
                question="Wer ist die primäre Zielgruppe für diese Lösung?",
                field_name="target_audience",
                examples=["Mitarbeiter der Buchhaltung", "Außendienstmitarbeiter"],
            ),
            InceptionQuestion(
                question="Was sind die messbaren Erfolgskriterien?",
                field_name="success_criteria",
                examples=["80% Zeitersparnis", "Fehlerquote < 1%"],
            ),
            InceptionQuestion(
                question="Was ist explizit NICHT Teil des Projekts (Out of Scope)?",
                field_name="out_of_scope",
                required=False,
            ),
            InceptionQuestion(
                question="Welche Annahmen liegen dem Projekt zugrunde?",
                field_name="assumptions",
                required=False,
            ),
            InceptionQuestion(
                question="Gibt es bekannte Risiken oder Einschränkungen?",
                field_name="risks",
                required=False,
            ),
            InceptionQuestion(
                question="Wer ist der fachliche Ansprechpartner (Owner)?",
                field_name="owner_name",
            ),
        ],
        'neue_domain': [
            InceptionQuestion(
                question="Gibt es einen Domänenexperten, der das Projekt begleiten kann?",
                field_name="domain_expert",
            ),
            InceptionQuestion(
                question="Wie grenzt sich diese Domain von bestehenden Domains ab?",
                field_name="domain_boundaries",
            ),
            InceptionQuestion(
                question="Gibt es Daten, die migriert werden müssen?",
                field_name="data_migration",
                required=False,
            ),
        ],
        'integration': [
            InceptionQuestion(
                question="Welches externe System soll integriert werden?",
                field_name="external_system",
            ),
            InceptionQuestion(
                question="Gibt es eine dokumentierte API? (URL/Dokumentation)",
                field_name="api_documentation",
            ),
            InceptionQuestion(
                question="Welche Authentifizierung wird benötigt?",
                field_name="authentication",
                examples=["OAuth2", "API Key", "Basic Auth"],
            ),
        ],
        'optimierung': [
            InceptionQuestion(
                question="Was sind die aktuellen Pain Points?",
                field_name="pain_points",
            ),
            InceptionQuestion(
                question="Wie lässt sich die Verbesserung messen?",
                field_name="measurement",
                examples=["Ladezeit in Sekunden", "Klicks bis zum Ziel"],
            ),
        ],
        'erweiterung': [
            InceptionQuestion(
                question="Welche bestehende Domain wird erweitert?",
                field_name="extended_domain",
            ),
            InceptionQuestion(
                question="Gibt es Breaking Changes für bestehende Nutzer?",
                field_name="breaking_changes",
            ),
        ],
        'produktion': [
            InceptionQuestion(
                question="Welcher Branch/Version soll deployed werden?",
                field_name="branch",
            ),
            InceptionQuestion(
                question="Was ist der Rollback-Plan?",
                field_name="rollback_plan",
            ),
        ],
    }
    
    # Architecture Basis Fragen
    ARCHITECTURE_QUESTIONS: list[InceptionQuestion] = [
        InceptionQuestion(
            question="Welche Datenbank soll verwendet werden?",
            field_name="architecture_basis.database",
            examples=["PostgreSQL (Standard)", "SQLite (für Tests)"],
        ),
        InceptionQuestion(
            question="Welches Backend-Framework?",
            field_name="architecture_basis.backend",
            examples=["Django (Standard)", "FastAPI"],
        ),
        InceptionQuestion(
            question="Welche Frontend-Technologie?",
            field_name="architecture_basis.frontend",
            examples=["HTMX (Standard)", "React", "Vue"],
        ),
        InceptionQuestion(
            question="Ist dies ein neues Projekt oder eine Erweiterung?",
            field_name="architecture_basis.extends_app",
            examples=["Neues Projekt", "Erweiterung von bfagent"],
        ),
    ]
    
    @classmethod
    def start_session(
        cls,
        initial_input: str,
        user: Optional['User'] = None,
        category_code: Optional[str] = None,
    ) -> dict:
        """
        Startet eine neue Inception-Session.
        
        Args:
            initial_input: Freitext-Beschreibung des Nutzers
            user: Aktueller Benutzer
            category_code: Optional vorgegebene Kategorie
            
        Returns:
            Session-Info mit erster Frage
        """
        session_id = str(uuid.uuid4())
        
        # Initiale Analyse des Inputs
        analysis = cls._analyze_initial_input(initial_input)
        
        # Kategorie bestimmen
        detected_category = category_code or analysis.get('detected_category', 'neue_domain')
        
        # Business Case Draft erstellen
        bc = BusinessCaseService.create(
            title=analysis.get('title', 'Neuer Business Case'),
            problem_statement=analysis.get('problem_statement', initial_input),
            category_code=detected_category,
            owner=user,
            original_input=initial_input,
            inception_session_id=session_id,
        )
        
        # Fragen zusammenstellen
        questions = cls._build_question_list(detected_category, analysis)
        
        # Session erstellen
        session = InceptionSession(
            session_id=session_id,
            business_case_id=bc.id,
            turn=1,
            extracted_data=analysis.get('extracted', {}),
            pending_questions=[q.question for q in questions],
        )
        cls._sessions[session_id] = session
        
        # Erste Conversation speichern
        cls._save_conversation(
            bc_id=bc.id,
            session_id=session_id,
            turn=0,
            role_code='user',
            message=initial_input,
        )
        
        first_question = session.pending_questions[0] if session.pending_questions else None
        
        if first_question:
            cls._save_conversation(
                bc_id=bc.id,
                session_id=session_id,
                turn=1,
                role_code='agent',
                message=cls._format_initial_response(analysis, first_question),
                extracted_data=analysis.get('extracted'),
                next_question=first_question,
            )
        
        return {
            "session_id": session_id,
            "business_case_id": bc.id,
            "business_case_code": bc.code,
            "status": "in_progress",
            "detected_category": detected_category,
            "understood": analysis.get('extracted', {}),
            "question": first_question,
            "questions_remaining": len(session.pending_questions) - 1,
        }
    
    @classmethod
    def answer_question(
        cls,
        session_id: str,
        answer: str,
    ) -> dict:
        """
        Verarbeitet eine Antwort und gibt die nächste Frage zurück.
        """
        if session_id not in cls._sessions:
            return {"error": "Session nicht gefunden", "session_id": session_id}
        
        session = cls._sessions[session_id]
        
        if not session.pending_questions:
            return {"error": "Keine offenen Fragen", "session_id": session_id}
        
        # Aktuelle Frage und Antwort verarbeiten
        current_question = session.pending_questions.pop(0)
        extracted = cls._extract_from_answer(current_question, answer)
        
        # Session updaten
        session.extracted_data.update(extracted)
        session.answered_questions.append({
            'question': current_question,
            'answer': answer,
            'extracted': extracted,
        })
        session.turn += 1
        
        # Conversation speichern
        from governance.models import BusinessCase
        bc = BusinessCase.all_objects.get(id=session.business_case_id)
        
        cls._save_conversation(
            bc_id=bc.id,
            session_id=session_id,
            turn=session.turn,
            role_code='user',
            message=answer,
        )
        
        # Business Case aktualisieren
        cls._update_business_case(bc, session.extracted_data)
        
        # Prüfen ob fertig
        if not session.pending_questions:
            session.status = "ready_for_finalization"
            summary = cls._generate_summary(bc, session.extracted_data)
            
            cls._save_conversation(
                bc_id=bc.id,
                session_id=session_id,
                turn=session.turn + 1,
                role_code='agent',
                message=summary,
                extracted_data=session.extracted_data,
            )
            
            return {
                "session_id": session_id,
                "status": "ready_for_finalization",
                "business_case_code": bc.code,
                "summary": summary,
                "extracted_data": session.extracted_data,
                "next_action": "Rufe finalize_business_case() auf um abzuschließen",
            }
        
        # Nächste Frage
        next_question = session.pending_questions[0]
        
        cls._save_conversation(
            bc_id=bc.id,
            session_id=session_id,
            turn=session.turn + 1,
            role_code='agent',
            message=next_question,
            next_question=next_question,
        )
        
        return {
            "session_id": session_id,
            "status": "in_progress",
            "understood_so_far": session.extracted_data,
            "question": next_question,
            "questions_remaining": len(session.pending_questions) - 1,
        }
    
    @classmethod
    @transaction.atomic
    def finalize(
        cls,
        session_id: str,
        adjustments: Optional[dict] = None,
        derive_use_cases: bool = True,
    ) -> dict:
        """
        Finalisiert den Business Case und leitet Use Cases ab.
        """
        if session_id not in cls._sessions:
            return {"error": "Session nicht gefunden"}
        
        session = cls._sessions[session_id]
        
        from governance.models import BusinessCase
        bc = BusinessCase.all_objects.get(id=session.business_case_id)
        
        # Adjustments anwenden
        if adjustments:
            session.extracted_data.update(adjustments)
            cls._update_business_case(bc, session.extracted_data)
        
        # Inception als abgeschlossen markieren
        bc.inception_completed_at = timezone.now()
        bc.save()
        
        # Use Cases ableiten
        derived_use_cases = []
        if derive_use_cases:
            use_case_drafts = cls._derive_use_cases(bc)
            derived_use_cases = UseCaseService.create_bulk(bc, use_case_drafts)
        
        # Session aufräumen
        del cls._sessions[session_id]
        
        return {
            "status": "finalized",
            "business_case": {
                "id": bc.id,
                "code": bc.code,
                "title": bc.title,
                "status": bc.status.code,
            },
            "derived_use_cases": [
                {"code": uc.code, "title": uc.title}
                for uc in derived_use_cases
            ],
            "next_steps": [
                f"Review in Web-UI: /governance/business-cases/{bc.code}/",
                "Use Cases detaillieren",
                "Zur Genehmigung einreichen",
            ],
        }
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional[InceptionSession]:
        """Holt aktuelle Session."""
        return cls._sessions.get(session_id)
    
    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------
    
    @classmethod
    def _analyze_initial_input(cls, text: str) -> dict:
        """
        Analysiert den initialen Freitext.
        
        In Production: LLM-Aufruf für intelligente Extraktion.
        Hier: Einfache Heuristik.
        """
        # Einfache Extraktion (in Production: LLM)
        extracted = {}
        
        # Titel aus erstem Satz
        sentences = text.split('.')
        if sentences:
            extracted['title'] = sentences[0].strip()[:100]
        
        # Kategorie-Erkennung
        text_lower = text.lower()
        if any(k in text_lower for k in ['integration', 'api', 'anbindung', 'schnittstelle']):
            detected_category = 'integration'
        elif any(k in text_lower for k in ['optimierung', 'performance', 'schneller', 'verbesser']):
            detected_category = 'optimierung'
        elif any(k in text_lower for k in ['erweiter', 'feature', 'zusätzlich', 'neu']):
            detected_category = 'erweiterung'
        elif any(k in text_lower for k in ['deploy', 'release', 'produktiv', 'live']):
            detected_category = 'produktion'
        else:
            detected_category = 'neue_domain'
        
        # Bekannte Patterns extrahieren
        if 'zielgruppe' in text_lower or 'nutzer' in text_lower:
            # Hier könnte man mit Regex extrahieren
            pass
        
        return {
            'title': extracted.get('title', 'Neuer Business Case'),
            'problem_statement': text,
            'detected_category': detected_category,
            'extracted': extracted,
            'questions': [],  # Zusätzliche Fragen basierend auf Analyse
        }
    
    @classmethod
    def _build_question_list(
        cls,
        category_code: str,
        analysis: dict,
    ) -> list[InceptionQuestion]:
        """Baut die Frageliste für die Session."""
        questions = []
        
        # Default-Fragen
        questions.extend(cls.CATEGORY_QUESTIONS.get('default', []))
        
        # Kategorie-spezifische Fragen
        if category_code in cls.CATEGORY_QUESTIONS:
            questions.extend(cls.CATEGORY_QUESTIONS[category_code])
        
        # Architecture-Fragen wenn neue Domain
        if category_code == 'neue_domain':
            questions.extend(cls.ARCHITECTURE_QUESTIONS)
        
        # Bereits beantwortete Fragen entfernen
        answered_fields = set(analysis.get('extracted', {}).keys())
        questions = [q for q in questions if q.field_name not in answered_fields]
        
        return questions
    
    @classmethod
    def _extract_from_answer(cls, question: str, answer: str) -> dict:
        """
        Extrahiert strukturierte Daten aus einer Antwort.
        
        In Production: LLM-Aufruf.
        """
        # Vereinfachte Extraktion
        return {'last_answer': answer}
    
    @classmethod
    def _update_business_case(cls, bc: 'BusinessCase', data: dict) -> None:
        """Aktualisiert den Business Case mit extrahierten Daten."""
        update_fields = []
        
        field_mapping = {
            'target_audience': 'target_audience',
            'success_criteria': 'success_criteria',
            'out_of_scope': 'out_of_scope',
            'assumptions': 'assumptions',
            'risks': 'risks',
            'expected_benefits': 'expected_benefits',
            'scope': 'scope',
        }
        
        for data_key, model_field in field_mapping.items():
            if data_key in data:
                setattr(bc, model_field, data[data_key])
                update_fields.append(model_field)
        
        # Architecture Basis
        if 'architecture_basis' in data:
            bc.architecture_basis = data['architecture_basis']
            update_fields.append('architecture_basis')
        
        if update_fields:
            bc.save(update_fields=update_fields + ['updated_at'])
    
    @classmethod
    def _generate_summary(cls, bc: 'BusinessCase', data: dict) -> str:
        """Generiert eine Zusammenfassung des Business Cases."""
        return f"""
**Zusammenfassung: {bc.code} - {bc.title}**

**Problem:**
{bc.problem_statement}

**Zielgruppe:**
{bc.target_audience or 'Nicht angegeben'}

**Erwarteter Nutzen:**
{bc.expected_benefits or 'Nicht angegeben'}

**Erfolgskriterien:**
{', '.join(bc.success_criteria) if bc.success_criteria else 'Nicht angegeben'}

**Kategorie:** {bc.category.name}

Bitte bestätige mit `finalize_business_case(session_id)` um abzuschließen
und Use Cases abzuleiten.
"""
    
    @classmethod
    def _derive_use_cases(cls, bc: 'BusinessCase') -> list[DerivedUseCase]:
        """
        Leitet Use Cases aus dem Business Case ab.
        
        In Production: LLM-Aufruf für intelligente Ableitung.
        """
        # Beispiel-Ableitung basierend auf Kategorie
        use_cases = []
        
        if bc.category.code == 'neue_domain':
            use_cases = [
                DerivedUseCase(
                    title=f"Daten anlegen",
                    description=f"Anlegen neuer Datensätze in {bc.title}",
                    actor="Benutzer",
                    priority_code="high",
                    main_flow_draft=[
                        "Benutzer öffnet Eingabemaske",
                        "System zeigt leeres Formular",
                        "Benutzer füllt Pflichtfelder aus",
                        "System validiert Eingaben",
                        "System speichert Datensatz",
                    ],
                ),
                DerivedUseCase(
                    title=f"Daten bearbeiten",
                    description=f"Bearbeiten bestehender Datensätze",
                    actor="Benutzer",
                    priority_code="high",
                ),
                DerivedUseCase(
                    title=f"Daten anzeigen",
                    description=f"Anzeige und Suche von Datensätzen",
                    actor="Benutzer",
                    priority_code="high",
                ),
                DerivedUseCase(
                    title=f"Daten exportieren",
                    description=f"Export als PDF oder Excel",
                    actor="Benutzer",
                    priority_code="medium",
                ),
            ]
        elif bc.category.code == 'integration':
            use_cases = [
                DerivedUseCase(
                    title="Verbindung herstellen",
                    description="Verbindung zum externen System herstellen",
                    actor="System",
                    priority_code="critical",
                ),
                DerivedUseCase(
                    title="Daten synchronisieren",
                    description="Daten zwischen Systemen synchronisieren",
                    actor="System",
                    priority_code="high",
                ),
                DerivedUseCase(
                    title="Fehlerbehandlung",
                    description="Umgang mit Verbindungsfehlern",
                    actor="System",
                    priority_code="high",
                ),
            ]
        
        return use_cases
    
    @classmethod
    def _format_initial_response(cls, analysis: dict, first_question: str) -> str:
        """Formatiert die initiale Antwort des Agents."""
        extracted = analysis.get('extracted', {})
        
        response = "Ich habe Folgendes verstanden:\n\n"
        
        if 'title' in extracted:
            response += f"**Titel:** {extracted['title']}\n"
        
        response += f"**Kategorie:** {analysis.get('detected_category', 'Wird ermittelt')}\n\n"
        response += f"**Nächste Frage:** {first_question}"
        
        return response
    
    @classmethod
    def _save_conversation(
        cls,
        bc_id: int,
        session_id: str,
        turn: int,
        role_code: str,
        message: str,
        extracted_data: Optional[dict] = None,
        next_question: Optional[str] = None,
    ) -> None:
        """Speichert einen Conversation-Eintrag."""
        from governance.models import Conversation
        
        role = LookupService.get_choice('conversation_role', role_code)
        
        Conversation.objects.create(
            business_case_id=bc_id,
            session_id=session_id,
            turn_number=turn,
            role=role,
            message=message,
            extracted_data=extracted_data,
            next_question=next_question or '',
        )


# ============================================================================
# SECTION 7: EXPORT SERVICE
# ============================================================================

class ExportService:
    """
    Service für Export von Dokumenten (für Sphinx, etc.).
    """
    
    @classmethod
    def export_business_case_to_rst(cls, bc: 'BusinessCase') -> str:
        """
        Exportiert einen Business Case als RST für Sphinx.
        """
        template = """
{code}: {title}
{underline}

:Status: {status}
:Kategorie: {category}
:Owner: {owner}
:Erstellt: {created}

Problem
-------
{problem}

Zielgruppe
----------
{audience}

Erwarteter Nutzen
-----------------
{benefits}

Erfolgskriterien
----------------
{criteria}

Scope
-----
{scope}

Out of Scope
------------
{out_of_scope}

Zugehörige Use Cases
--------------------
{use_cases}
"""
        
        use_cases_str = "\n".join([
            f"* :doc:`../use_cases/{uc.code}` - {uc.title}"
            for uc in bc.use_cases.all()
        ]) or "Keine Use Cases"
        
        criteria_str = "\n".join([
            f"* {c}" for c in bc.success_criteria
        ]) or "Nicht definiert"
        
        return template.format(
            code=bc.code,
            title=bc.title,
            underline="=" * (len(bc.code) + len(bc.title) + 2),
            status=bc.status.name,
            category=bc.category.name,
            owner=bc.owner.username if bc.owner else "Nicht zugewiesen",
            created=bc.created_at.strftime("%Y-%m-%d"),
            problem=bc.problem_statement,
            audience=bc.target_audience or "Nicht definiert",
            benefits=bc.expected_benefits or "Nicht definiert",
            criteria=criteria_str,
            scope=bc.scope or "Nicht definiert",
            out_of_scope=bc.out_of_scope or "Nicht definiert",
            use_cases=use_cases_str,
        )
    
    @classmethod
    def export_use_case_to_rst(cls, uc: 'UseCase') -> str:
        """
        Exportiert einen Use Case als RST.
        """
        # Analog zu business_case
        pass
    
    @classmethod
    def export_adr_to_rst(cls, adr: 'ADR') -> str:
        """
        Exportiert einen ADR als RST.
        """
        # Analog zu business_case
        pass


# ============================================================================
# SECTION 8: EXPORTS
# ============================================================================

__all__ = [
    'LookupService',
    'BusinessCaseService',
    'UseCaseService',
    'ADRService',
    'InceptionService',
    'ExportService',
    'InceptionSession',
    'InceptionQuestion',
    'DerivedUseCase',
]
