"""
BF Agent MCP Server - Repository Layer
=======================================

Implementiert das Repository Pattern für Data Access.

Design-Prinzipien:
- Single Responsibility: Nur Datenzugriff, keine Business Logic
- Dependency Inversion: Services hängen von Interface ab, nicht von Implementierung
- Testbarkeit: Einfach durch Mock-Repositories ersetzbar
- Caching: Optional, transparent für Consumer

Jedes Repository:
- Arbeitet mit DTOs (nicht Django Models direkt)
- Hat async Methoden für Non-Blocking I/O
- Unterstützt Pagination
- Cached häufige Queries
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from ..core import (
    DomainDTO,
    PhaseDTO,
    HandlerDTO,
    TagDTO,
    DomainStatus,
    HandlerType,
    AIProvider,
    DomainNotFoundError,
    HandlerNotFoundError,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

class CacheConfig:
    """Cache-Konfiguration."""
    DOMAIN_TTL = 300  # 5 Minuten
    HANDLER_TTL = 300
    PHASE_TTL = 600  # 10 Minuten
    TAG_TTL = 3600  # 1 Stunde


# =============================================================================
# MOCK DATA (Wird in Production durch Django ORM ersetzt)
# =============================================================================

# Diese Daten simulieren die Datenbank für Standalone-Betrieb
_MOCK_TAGS: Dict[int, TagDTO] = {
    1: TagDTO(id=1, name="creative", category="general", description="Creative content generation"),
    2: TagDTO(id=2, name="ai-powered", category="ai", description="Uses AI for processing"),
    3: TagDTO(id=3, name="bilingual", category="domain", description="Supports multiple languages"),
    4: TagDTO(id=4, name="medical", category="domain", description="Medical/healthcare domain"),
    5: TagDTO(id=5, name="translation", category="domain", description="Translation capabilities"),
    6: TagDTO(id=6, name="technical", category="domain", description="Technical/engineering content"),
    7: TagDTO(id=7, name="pdf", category="format", description="PDF file support"),
    8: TagDTO(id=8, name="pptx", category="format", description="PowerPoint support"),
    9: TagDTO(id=9, name="dxf", category="format", description="DXF/CAD file support"),
    10: TagDTO(id=10, name="compliance", category="domain", description="Regulatory compliance"),
}

_MOCK_DOMAINS: Dict[str, DomainDTO] = {
    "books": DomainDTO(
        id=1,
        domain_id="books",
        display_name="Book Writing Platform",
        description="AI-powered book creation with character generation, story structures (Save the Cat, Hero's Journey), bilingual content, and automated illustration generation.",
        status=DomainStatus.PRODUCTION,
        icon="book-open",
        color="#8B5CF6"
    ),
    "medtrans": DomainDTO(
        id=2,
        domain_id="medtrans",
        display_name="Medical Translation",
        description="Professional medical document translation with terminology database integration, context-aware translation, and quality assurance workflow.",
        status=DomainStatus.PRODUCTION,
        icon="stethoscope",
        color="#10B981"
    ),
    "cad": DomainDTO(
        id=3,
        domain_id="cad",
        display_name="CAD Analysis",
        description="Technical drawing analysis with DXF/DWG parsing (ezdxf), dimension extraction via OCR, geometry detection (OpenCV), and standards compliance checking (DIN, ISO).",
        status=DomainStatus.BETA,
        icon="ruler",
        color="#F59E0B"
    ),
    "comic": DomainDTO(
        id=4,
        domain_id="comic",
        display_name="Comic Book Creator",
        description="Comic creation pipeline with AI story generation, consistent character design via LoRA training, automated panel layout, and multiple art styles (Manga, Marvel, Franco-Belgian).",
        status=DomainStatus.DEVELOPMENT,
        icon="palette",
        color="#EC4899"
    ),
    "exschutz": DomainDTO(
        id=5,
        domain_id="exschutz",
        display_name="Explosion Protection Documents",
        description="Creation and management of explosion protection documents according to BetrSichV and ATEX regulations, with zone classification and safety measure documentation.",
        status=DomainStatus.DEVELOPMENT,
        icon="shield-alert",
        color="#EF4444"
    ),
}

_MOCK_PHASES: Dict[str, List[PhaseDTO]] = {
    "books": [
        PhaseDTO(id=1, name="planung", display_name="Planung", order=0, description="Project setup and story planning", estimated_duration_seconds=60),
        PhaseDTO(id=2, name="charaktere", display_name="Charaktere", order=1, description="Character creation and development", estimated_duration_seconds=120),
        PhaseDTO(id=3, name="weltbau", display_name="Weltbau", order=2, description="World building and setting", estimated_duration_seconds=90),
        PhaseDTO(id=4, name="kapitel", display_name="Kapitel", order=3, description="Chapter writing", estimated_duration_seconds=300),
        PhaseDTO(id=5, name="illustration", display_name="Illustration", order=4, description="Image generation", estimated_duration_seconds=180),
        PhaseDTO(id=6, name="export", display_name="Export", order=5, description="Final export to PDF/EPUB", estimated_duration_seconds=60),
    ],
    "cad": [
        PhaseDTO(id=7, name="upload", display_name="Upload", order=0, description="File upload and validation", estimated_duration_seconds=10),
        PhaseDTO(id=8, name="parsing", display_name="Parsing", order=1, description="DXF/DWG parsing", estimated_duration_seconds=30),
        PhaseDTO(id=9, name="analyse", display_name="Analyse", order=2, description="Drawing analysis", estimated_duration_seconds=60),
        PhaseDTO(id=10, name="validierung", display_name="Validierung", order=3, description="Standards compliance check", estimated_duration_seconds=30),
        PhaseDTO(id=11, name="report", display_name="Report", order=4, description="Report generation", estimated_duration_seconds=20),
    ],
    "medtrans": [
        PhaseDTO(id=12, name="upload", display_name="Upload", order=0, description="Document upload", estimated_duration_seconds=10),
        PhaseDTO(id=13, name="analyse", display_name="Analyse", order=1, description="Content analysis", estimated_duration_seconds=30),
        PhaseDTO(id=14, name="uebersetzung", display_name="Übersetzung", order=2, description="Translation", estimated_duration_seconds=120),
        PhaseDTO(id=15, name="qa", display_name="QA", order=3, description="Quality assurance", estimated_duration_seconds=60),
        PhaseDTO(id=16, name="export", display_name="Export", order=4, description="Final export", estimated_duration_seconds=20),
    ],
    "comic": [
        PhaseDTO(id=17, name="story", display_name="Story", order=0, description="Story creation", estimated_duration_seconds=120),
        PhaseDTO(id=18, name="characters", display_name="Characters", order=1, description="Character design", estimated_duration_seconds=180),
        PhaseDTO(id=19, name="panels", display_name="Panels", order=2, description="Panel layout", estimated_duration_seconds=60),
        PhaseDTO(id=20, name="art", display_name="Art", order=3, description="Art generation", estimated_duration_seconds=300),
        PhaseDTO(id=21, name="layout", display_name="Layout", order=4, description="Page layout", estimated_duration_seconds=60),
        PhaseDTO(id=22, name="export", display_name="Export", order=5, description="Export to PDF/CBZ", estimated_duration_seconds=30),
    ],
    "exschutz": [
        PhaseDTO(id=23, name="datenerfassung", display_name="Datenerfassung", order=0, description="Data collection", estimated_duration_seconds=300),
        PhaseDTO(id=24, name="zoneneinteilung", display_name="Zoneneinteilung", order=1, description="Zone classification", estimated_duration_seconds=180),
        PhaseDTO(id=25, name="massnahmen", display_name="Maßnahmen", order=2, description="Safety measures", estimated_duration_seconds=240),
        PhaseDTO(id=26, name="dokumentation", display_name="Dokumentation", order=3, description="Documentation", estimated_duration_seconds=180),
        PhaseDTO(id=27, name="pruefung", display_name="Prüfung", order=4, description="Review", estimated_duration_seconds=120),
    ],
}

_MOCK_HANDLERS: Dict[str, List[HandlerDTO]] = {
    "books": [
        HandlerDTO(
            id=1, name="CharacterGeneratorHandler", domain_id="books",
            handler_type=HandlerType.AI_POWERED, ai_provider=AIProvider.OPENAI,
            description="Generates detailed character profiles using AI with personality traits, backstory, relationships, and visual description for illustration prompts.",
            input_schema={"character_brief": "str", "genre": "str", "target_audience": "str", "language": "str"},
            output_schema={"character": "Character", "illustration_prompt": "str", "relationships": "list"},
            estimated_duration_seconds=30, tags=["creative", "ai-powered"]
        ),
        HandlerDTO(
            id=2, name="ChapterWriterHandler", domain_id="books",
            handler_type=HandlerType.AI_POWERED, ai_provider=AIProvider.OPENAI,
            description="Writes book chapters based on outline, character context, and story structure. Supports multiple narrative styles.",
            input_schema={"chapter_outline": "str", "characters": "list", "previous_context": "str", "style": "str"},
            output_schema={"chapter_text": "str", "word_count": "int", "summary": "str"},
            estimated_duration_seconds=45, tags=["creative", "ai-powered"]
        ),
        HandlerDTO(
            id=3, name="IllustrationHandler", domain_id="books",
            handler_type=HandlerType.AI_POWERED, ai_provider=AIProvider.OPENAI,
            description="Generates illustrations using DALL-E 3 or Stable Diffusion based on scene descriptions and character profiles.",
            input_schema={"prompt": "str", "style": "str", "size": "str", "character_refs": "list"},
            output_schema={"image_url": "str", "image_path": "str", "revised_prompt": "str"},
            estimated_duration_seconds=20, tags=["creative", "ai-powered"]
        ),
        HandlerDTO(
            id=4, name="StoryStructureHandler", domain_id="books",
            handler_type=HandlerType.RULE_BASED, ai_provider=AIProvider.NONE,
            description="Applies story structure templates (Save the Cat, Hero's Journey, Three-Act) to generate chapter outlines.",
            input_schema={"premise": "str", "structure_type": "str", "chapter_count": "int"},
            output_schema={"outline": "list", "beats": "list", "act_breakdown": "dict"},
            estimated_duration_seconds=5, tags=["creative"]
        ),
        HandlerDTO(
            id=5, name="PDFExportHandler", domain_id="books",
            handler_type=HandlerType.UTILITY, ai_provider=AIProvider.NONE,
            description="Exports completed book to PDF format with proper formatting, table of contents, and embedded illustrations.",
            input_schema={"book_content": "dict", "template": "str", "include_toc": "bool"},
            output_schema={"pdf_path": "str", "page_count": "int", "file_size": "int"},
            estimated_duration_seconds=30, tags=["pdf"]
        ),
    ],
    "cad": [
        HandlerDTO(
            id=6, name="DXFParserHandler", domain_id="cad",
            handler_type=HandlerType.RULE_BASED, ai_provider=AIProvider.NONE,
            description="Parses DXF files and extracts geometric entities, layers, blocks, and metadata using ezdxf library.",
            input_schema={"file_path": "str", "layer_filter": "Optional[list]", "entity_types": "Optional[list]"},
            output_schema={"entities": "list", "layers": "list", "blocks": "list", "metadata": "dict"},
            estimated_duration_seconds=5, tags=["dxf", "technical"]
        ),
        HandlerDTO(
            id=7, name="DimensionExtractorHandler", domain_id="cad",
            handler_type=HandlerType.HYBRID, ai_provider=AIProvider.TESSERACT,
            description="Extracts dimensions from technical drawings using OCR (Tesseract) and pattern matching for dimension text.",
            input_schema={"drawing_path": "str", "unit": "str", "ocr_config": "dict"},
            output_schema={"dimensions": "list", "tolerances": "list", "units": "str"},
            estimated_duration_seconds=15, tags=["dxf", "technical"]
        ),
        HandlerDTO(
            id=8, name="ComplianceCheckerHandler", domain_id="cad",
            handler_type=HandlerType.RULE_BASED, ai_provider=AIProvider.NONE,
            description="Validates technical drawings against DIN/ISO standards with configurable rule sets.",
            input_schema={"drawing_data": "dict", "standards": "list", "severity_threshold": "str"},
            output_schema={"compliant": "bool", "violations": "list", "warnings": "list", "score": "float"},
            estimated_duration_seconds=3, tags=["technical", "compliance"]
        ),
        HandlerDTO(
            id=9, name="GeometryAnalyzerHandler", domain_id="cad",
            handler_type=HandlerType.RULE_BASED, ai_provider=AIProvider.NONE,
            description="Analyzes geometric properties: area, perimeter, centroid, bounding box for CAD entities.",
            input_schema={"entities": "list", "coordinate_system": "str"},
            output_schema={"analysis": "dict", "statistics": "dict"},
            estimated_duration_seconds=2, tags=["technical"]
        ),
        HandlerDTO(
            id=10, name="ReportGeneratorHandler", domain_id="cad",
            handler_type=HandlerType.UTILITY, ai_provider=AIProvider.NONE,
            description="Generates analysis reports in PDF/DOCX format with charts and compliance summaries.",
            input_schema={"analysis_data": "dict", "template": "str", "format": "str"},
            output_schema={"report_path": "str", "sections": "list"},
            estimated_duration_seconds=10, tags=["technical", "pdf"]
        ),
    ],
    "medtrans": [
        HandlerDTO(
            id=11, name="PPTXExtractorHandler", domain_id="medtrans",
            handler_type=HandlerType.RULE_BASED, ai_provider=AIProvider.NONE,
            description="Extracts text, formatting, and speaker notes from PowerPoint presentations preserving structure.",
            input_schema={"file_path": "str", "preserve_formatting": "bool", "extract_images": "bool"},
            output_schema={"slides": "list", "speaker_notes": "list", "images": "list"},
            estimated_duration_seconds=5, tags=["pptx"]
        ),
        HandlerDTO(
            id=12, name="MedicalTranslationHandler", domain_id="medtrans",
            handler_type=HandlerType.AI_POWERED, ai_provider=AIProvider.OPENAI,
            description="Translates medical content with terminology accuracy >95% using specialized medical glossary.",
            input_schema={"text": "str", "source_lang": "str", "target_lang": "str", "specialty": "str"},
            output_schema={"translated_text": "str", "terminology_matches": "list", "confidence": "float"},
            estimated_duration_seconds=15, tags=["medical", "translation", "ai-powered"]
        ),
        HandlerDTO(
            id=13, name="TerminologyValidatorHandler", domain_id="medtrans",
            handler_type=HandlerType.RULE_BASED, ai_provider=AIProvider.NONE,
            description="Validates medical terminology against approved glossary and flags inconsistencies.",
            input_schema={"text": "str", "glossary_id": "int", "language": "str"},
            output_schema={"valid": "bool", "issues": "list", "suggestions": "list"},
            estimated_duration_seconds=3, tags=["medical"]
        ),
        HandlerDTO(
            id=14, name="PPTXReconstructorHandler", domain_id="medtrans",
            handler_type=HandlerType.RULE_BASED, ai_provider=AIProvider.NONE,
            description="Reconstructs PowerPoint with translated content preserving original formatting and layout.",
            input_schema={"original_path": "str", "translations": "list", "target_lang": "str"},
            output_schema={"output_path": "str", "slide_count": "int"},
            estimated_duration_seconds=10, tags=["pptx"]
        ),
    ],
}

_MOCK_DOMAIN_TAGS: Dict[str, List[str]] = {
    "books": ["creative", "ai-powered", "bilingual"],
    "medtrans": ["medical", "translation", "pptx"],
    "cad": ["technical", "dxf", "compliance"],
    "comic": ["creative", "ai-powered"],
    "exschutz": ["compliance", "technical"],
}


# =============================================================================
# BASE REPOSITORY
# =============================================================================

class BaseRepository:
    """
    Base Repository mit gemeinsamer Funktionalität.
    
    Kann für Django ORM oder Mock-Daten verwendet werden.
    Bei use_django=True werden alle Queries über Django ORM ausgeführt.
    """
    
    def __init__(self, use_django: bool = False):
        """
        Args:
            use_django: True für Django ORM, False für Mock-Daten
        """
        self.use_django = use_django
        self._cache: Dict[str, Any] = {}
        
        # Validate Django availability if requested
        if use_django:
            self._ensure_django()
    
    def _ensure_django(self) -> bool:
        """Ensure Django is available when needed."""
        try:
            from ..django_integration import ensure_django_setup, is_django_available
            if not is_django_available():
                ensure_django_setup()
            return is_django_available()
        except ImportError:
            import logging
            logging.warning("Django integration not available, falling back to mock data")
            self.use_django = False
            return False
    
    def _cache_key(self, *args) -> str:
        """Generiert Cache-Key aus Argumenten."""
        return ":".join(str(a) for a in args)
    
    async def _get_cached(self, key: str) -> Optional[Any]:
        """Holt Wert aus Cache."""
        return self._cache.get(key)
    
    async def _set_cached(self, key: str, value: Any) -> None:
        """Setzt Wert in Cache."""
        self._cache[key] = value
    
    def clear_cache(self) -> None:
        """Leert den Cache."""
        self._cache.clear()


# =============================================================================
# DOMAIN REPOSITORY
# =============================================================================

class DomainRepository(BaseRepository):
    """
    Repository für Domain-Zugriff.
    
    Abstrahiert den Datenzugriff von der Business Logic.
    Bei use_django=True: Nutzt Django ORM.
    Bei use_django=False: Nutzt Mock-Daten für Standalone-Betrieb.
    """
    
    async def get_by_id(self, id: int) -> Optional[DomainDTO]:
        """Findet Domain nach Datenbank-ID."""
        if self.use_django:
            from ..django_integration import async_get_all_domains
            domains = await async_get_all_domains()
            for domain in domains:
                if domain.id == id:
                    return domain
            return None
        
        # Mock data fallback
        for domain in _MOCK_DOMAINS.values():
            if domain.id == id:
                return domain
        return None
    
    async def get_by_domain_id(self, domain_id: str) -> Optional[DomainDTO]:
        """Findet Domain nach domain_id (slug)."""
        if self.use_django:
            from ..django_integration import async_get_domain_by_id
            return await async_get_domain_by_id(domain_id)
        
        return _MOCK_DOMAINS.get(domain_id)
    
    async def get_all(
        self, 
        limit: int = DEFAULT_PAGE_SIZE, 
        offset: int = 0,
        status_filter: Optional[DomainStatus] = None
    ) -> List[DomainDTO]:
        """
        Gibt alle Domains zurück (paginiert).
        
        Args:
            limit: Max. Anzahl Ergebnisse
            offset: Offset für Pagination
            status_filter: Optional Status-Filter
        """
        if self.use_django:
            from ..django_integration import async_get_all_domains
            return await async_get_all_domains(
                status_filter=status_filter,
                limit=limit,
                offset=offset
            )
        
        # Mock data fallback
        domains = list(_MOCK_DOMAINS.values())
        
        if status_filter:
            domains = [d for d in domains if d.status == status_filter]
        
        return domains[offset:offset + limit]
    
    async def count(self, status_filter: Optional[DomainStatus] = None) -> int:
        """Zählt Domains."""
        if self.use_django:
            from ..django_integration import async_count_domains
            return await async_count_domains(status_filter)
        
        # Mock data fallback
        if status_filter:
            return len([d for d in _MOCK_DOMAINS.values() if d.status == status_filter])
        return len(_MOCK_DOMAINS)
    
    async def get_by_status(self, status: DomainStatus) -> List[DomainDTO]:
        """Findet Domains nach Status."""
        if self.use_django:
            from ..django_integration import async_get_all_domains
            return await async_get_all_domains(status_filter=status, limit=100)
        
        return [d for d in _MOCK_DOMAINS.values() if d.status == status]
    
    async def get_with_details(self, domain_id: str) -> Optional[Dict[str, Any]]:
        """
        Lädt Domain mit allen zugehörigen Details.
        
        Returns:
            Dict mit domain, phases, handlers, tags
        """
        if self.use_django:
            from ..django_integration import async_get_domain_with_details
            return await async_get_domain_with_details(domain_id)
        
        # Mock data fallback
        domain = await self.get_by_domain_id(domain_id)
        if not domain:
            return None
        
        phases = await PhaseRepository(use_django=self.use_django).get_by_domain(domain_id)
        handlers = await HandlerRepository(use_django=self.use_django).get_by_domain(domain_id)
        tags = _MOCK_DOMAIN_TAGS.get(domain_id, [])
        
        return {
            "domain": domain,
            "phases": phases,
            "handlers": handlers,
            "tags": tags,
            "handler_count": len(handlers),
            "phase_count": len(phases),
        }


# =============================================================================
# PHASE REPOSITORY
# =============================================================================

class PhaseRepository(BaseRepository):
    """Repository für Phase-Zugriff."""
    
    async def get_by_id(self, id: int) -> Optional[PhaseDTO]:
        """Findet Phase nach ID."""
        # Mock data lookup (Django version would query by ID directly)
        for phases in _MOCK_PHASES.values():
            for phase in phases:
                if phase.id == id:
                    return phase
        return None
    
    async def get_by_domain(self, domain_id: str) -> List[PhaseDTO]:
        """Findet alle Phasen einer Domain (sortiert nach order)."""
        if self.use_django:
            from ..django_integration import async_get_phases_by_domain
            return await async_get_phases_by_domain(domain_id)
        
        # Mock data fallback
        phases = _MOCK_PHASES.get(domain_id, [])
        return sorted(phases, key=lambda p: p.order)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[PhaseDTO]:
        """Gibt alle Phasen zurück."""
        all_phases = []
        for phases in _MOCK_PHASES.values():
            all_phases.extend(phases)
        return all_phases[offset:offset + limit]
    
    async def count(self) -> int:
        """Zählt alle Phasen."""
        return sum(len(phases) for phases in _MOCK_PHASES.values())


# =============================================================================
# HANDLER REPOSITORY
# =============================================================================

class HandlerRepository(BaseRepository):
    """Repository für Handler-Zugriff."""
    
    async def get_by_id(self, id: int) -> Optional[HandlerDTO]:
        """Findet Handler nach ID."""
        if self.use_django:
            from ..django_integration import async_get_handler_by_id
            return await async_get_handler_by_id(id)
        
        # Mock data fallback
        for handlers in _MOCK_HANDLERS.values():
            for handler in handlers:
                if handler.id == id:
                    return handler
        return None
    
    async def get_by_domain(
        self, 
        domain_id: str,
        include_inactive: bool = False
    ) -> List[HandlerDTO]:
        """Findet alle Handler einer Domain."""
        if self.use_django:
            from ..django_integration import async_get_handlers_by_domain
            return await async_get_handlers_by_domain(domain_id, include_inactive)
        
        # Mock data fallback
        handlers = _MOCK_HANDLERS.get(domain_id, [])
        if not include_inactive:
            handlers = [h for h in handlers if h.is_active]
        return handlers
    
    async def get_all(
        self, 
        limit: int = DEFAULT_PAGE_SIZE, 
        offset: int = 0
    ) -> List[HandlerDTO]:
        """Gibt alle Handler zurück (paginiert)."""
        all_handlers = []
        for handlers in _MOCK_HANDLERS.values():
            all_handlers.extend(handlers)
        return all_handlers[offset:offset + limit]
    
    async def count(self, domain_id: Optional[str] = None) -> int:
        """Zählt Handler."""
        if self.use_django:
            from ..django_integration import async_count_handlers
            return await async_count_handlers(domain_id)
        
        # Mock data fallback
        if domain_id:
            return len(_MOCK_HANDLERS.get(domain_id, []))
        return sum(len(h) for h in _MOCK_HANDLERS.values())
    
    async def search(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        handler_type_filter: Optional[HandlerType] = None,
        tags_filter: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Tuple[HandlerDTO, float]]:
        """
        Sucht Handler nach Query mit Relevanz-Score.
        
        Bei use_django=True: Nutzt Django ORM mit Full-Text Search.
        Bei use_django=False: Nutzt Mock-Daten mit Term-Matching.
        
        Args:
            query: Suchbegriff
            domain_filter: Optional Domain-Filter
            handler_type_filter: Optional Type-Filter
            tags_filter: Optional Tags-Filter
            limit: Max. Ergebnisse
            
        Returns:
            Liste von (Handler, Score) Tupeln
        """
        if self.use_django:
            from ..django_integration import async_search_handlers
            return await async_search_handlers(
                query=query,
                domain_filter=domain_filter,
                handler_type_filter=handler_type_filter,
                tags_filter=tags_filter,
                limit=limit
            )
        
        # Mock data fallback
        query_lower = query.lower()
        query_terms = query_lower.split()
        results: List[Tuple[HandlerDTO, float]] = []
        
        for domain_id, handlers in _MOCK_HANDLERS.items():
            # Domain Filter
            if domain_filter and domain_id != domain_filter:
                continue
            
            for handler in handlers:
                # Type Filter
                if handler_type_filter and handler.handler_type != handler_type_filter:
                    continue
                
                # Tags Filter
                if tags_filter:
                    if not any(tag in handler.tags for tag in tags_filter):
                        continue
                
                # Scoring
                score = self._calculate_relevance_score(handler, query_terms)
                
                if score > 0:
                    results.append((handler, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def _calculate_relevance_score(
        self, 
        handler: HandlerDTO, 
        query_terms: List[str]
    ) -> float:
        """
        Berechnet Relevanz-Score für einen Handler.
        
        Gewichtung:
        - Name Match: 3.0
        - Description Match: 1.0
        - Tag Match: 2.0
        - Input/Output Schema Match: 0.5
        """
        score = 0.0
        
        # Searchable text
        name_lower = handler.name.lower()
        desc_lower = handler.description.lower()
        tags_lower = [t.lower() for t in handler.tags]
        schema_text = " ".join(handler.input_schema.keys()) + " " + " ".join(handler.output_schema.keys())
        schema_lower = schema_text.lower()
        
        for term in query_terms:
            # Name match (highest weight)
            if term in name_lower:
                score += 3.0
            
            # Description match
            if term in desc_lower:
                score += 1.0
            
            # Tag match
            if any(term in tag for tag in tags_lower):
                score += 2.0
            
            # Schema match
            if term in schema_lower:
                score += 0.5
        
        return score


# =============================================================================
# TAG REPOSITORY
# =============================================================================

class TagRepository(BaseRepository):
    """Repository für Tag-Zugriff."""
    
    async def get_by_id(self, id: int) -> Optional[TagDTO]:
        """Findet Tag nach ID."""
        return _MOCK_TAGS.get(id)
    
    async def get_by_name(self, name: str) -> Optional[TagDTO]:
        """Findet Tag nach Name."""
        for tag in _MOCK_TAGS.values():
            if tag.name == name.lower():
                return tag
        return None
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[TagDTO]:
        """Gibt alle Tags zurück."""
        tags = list(_MOCK_TAGS.values())
        return tags[offset:offset + limit]
    
    async def get_by_category(self, category: str) -> List[TagDTO]:
        """Findet Tags nach Kategorie."""
        return [t for t in _MOCK_TAGS.values() if t.category == category]
    
    async def count(self) -> int:
        """Zählt Tags."""
        return len(_MOCK_TAGS)


# =============================================================================
# BEST PRACTICE REPOSITORY
# =============================================================================

_MOCK_BEST_PRACTICES: Dict[str, Dict[str, Any]] = {
    "handlers": {
        "topic": "handlers",
        "display_name": "Handler Best Practices",
        "content": """# Handler Best Practices

## Three-Phase Pattern

Every handler should follow the Input → Process → Output pattern:

1. **validate()** - Validate input with Pydantic
2. **process()** - Execute business logic
3. **save_result()** - Persist results

```python
class MyHandler(BaseHandler):
    async def validate(self, context: Dict) -> MyInput:
        return MyInput(**context)
    
    async def process(self, validated: MyInput) -> MyOutput:
        # Business logic here
        return MyOutput(...)
    
    async def save_result(self, result: MyOutput, context: Dict) -> HandlerResult:
        # Persist if needed
        return HandlerResult(success=True, data=result.model_dump())
```

## Registration

Use the `@register_handler` decorator:

```python
@register_handler(
    name="MyHandler",
    domain="my_domain",
    handler_type="ai_powered"
)
class MyHandler(BaseHandler):
    ...
```

## Error Handling

- Always wrap processing in try/except
- Log errors with context
- Return HandlerResult with error details
- Use specific exception types

## Performance

- Estimate execution time in registration
- Use async/await for I/O operations
- Cache expensive computations
- Track metrics for monitoring
""",
        "related_topics": ["pydantic", "error_handling", "testing"]
    },
    "pydantic": {
        "topic": "pydantic",
        "display_name": "Pydantic Best Practices",
        "content": """# Pydantic Best Practices

## Model Configuration

```python
from pydantic import BaseModel, Field, ConfigDict

class MyInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        validate_assignment=True
    )
    
    field: str = Field(
        ...,  # Required
        description="Field description",
        min_length=1,
        max_length=100
    )
    optional_field: Optional[int] = Field(
        default=None,
        ge=0,
        le=1000
    )
```

## Validation

- Use Field() constraints (min_length, max_length, ge, le, pattern)
- Add @field_validator for complex validation
- Use Optional[T] with defaults for optional fields
- Use Enums for constrained choices

## Naming Conventions

- Input schemas: `{Handler}Input`
- Output schemas: `{Handler}Output`
- Use snake_case for field names
- Use descriptive names

## Best Practices

- Always add descriptions to fields
- Validate early, fail fast
- Return model_dump() for serialization
- Use model_config instead of class Config (Pydantic v2)
""",
        "related_topics": ["handlers", "validation"]
    },
    "ai_integration": {
        "topic": "ai_integration",
        "display_name": "AI Integration Best Practices",
        "content": """# AI Integration Best Practices

## Provider Selection

| Provider | Use Case | Strengths |
|----------|----------|-----------|
| OpenAI GPT-4 | Complex reasoning, creative content | High quality, versatile |
| Anthropic Claude | Analysis, long context | Safety, reasoning |
| Ollama (Local) | Sensitive content, offline | Privacy, no API costs |
| Stability AI | Image generation | Cost-effective images |

## Prompt Management (Zero-Hardcoding)

Store prompts in database:

```python
# Never do this:
prompt = "Generate a character..."

# Do this instead:
prompt_template = await PromptRepository().get_by_name("character_generation")
prompt = prompt_template.render(context)
```

## Error Handling

```python
async def call_ai(prompt: str) -> str:
    retries = 3
    for attempt in range(retries):
        try:
            return await ai_client.generate(prompt)
        except RateLimitError:
            await asyncio.sleep(2 ** attempt)
        except AIServiceError as e:
            logger.error(f"AI error: {e}")
            raise
    raise AIServiceError("Max retries exceeded")
```

## Content Classification

Route content appropriately:
- Safe content → Cloud APIs (OpenAI, Claude)
- Sensitive content → Local LLMs (Ollama)
- Adult content → Local LLMs with appropriate models

## Cost Optimization

- Use smaller models for simple tasks
- Cache frequent queries
- Batch similar requests
- Monitor token usage
""",
        "related_topics": ["handlers", "error_handling", "performance"]
    },
    "testing": {
        "topic": "testing",
        "display_name": "Testing Best Practices",
        "content": """# Testing Best Practices

## Test Structure

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestMyHandler:
    @pytest.fixture
    def handler(self):
        return MyHandler()
    
    @pytest.fixture
    def valid_input(self):
        return {"field": "value"}
    
    @pytest.mark.asyncio
    async def test_validate_success(self, handler, valid_input):
        result = await handler.validate(valid_input)
        assert isinstance(result, MyInput)
    
    @pytest.mark.asyncio
    async def test_validate_invalid_input(self, handler):
        with pytest.raises(ValidationError):
            await handler.validate({})
    
    @pytest.mark.asyncio
    async def test_process_success(self, handler, valid_input):
        validated = await handler.validate(valid_input)
        result = await handler.process(validated)
        assert isinstance(result, MyOutput)
```

## Coverage Requirements

- Test happy path (valid inputs)
- Test validation errors
- Test processing errors
- Test edge cases
- Target: >80% coverage

## Mocking

```python
@pytest.mark.asyncio
async def test_ai_handler(self, handler):
    with patch.object(handler.ai_service, 'generate') as mock:
        mock.return_value = "generated content"
        result = await handler.process(valid_input)
        mock.assert_called_once()
```

## CI/CD Integration

- Run tests on every commit
- Require passing tests for merge
- Generate coverage reports
- Test migrations separately
""",
        "related_topics": ["handlers", "pydantic"]
    },
    "error_handling": {
        "topic": "error_handling",
        "display_name": "Error Handling Best Practices",
        "content": """# Error Handling Best Practices

## Custom Exceptions

```python
class BFAgentError(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(message)

class HandlerExecutionError(BFAgentError):
    def __init__(self, handler: str, cause: str):
        super().__init__(
            f"Handler '{handler}' failed: {cause}",
            code="HANDLER_ERROR"
        )
```

## Handler Error Pattern

```python
async def execute(self, context: Dict) -> HandlerResult:
    try:
        validated = await self.validate(context)
        result = await self.process(validated)
        return await self.save_result(result, context)
    except ValidationError as e:
        logger.warning(f"Validation failed: {e}")
        return HandlerResult(success=False, error=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return HandlerResult(success=False, error="Internal error")
```

## Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log levels:
logger.debug("Detailed debugging info")
logger.info("Normal operation info")
logger.warning("Something unexpected but handled")
logger.error("Error that needs attention")
logger.exception("Error with stack trace")
```

## Graceful Degradation

- Provide fallback for non-critical failures
- Cache previous successful results
- Implement circuit breaker for external services
""",
        "related_topics": ["handlers", "ai_integration"]
    },
    "performance": {
        "topic": "performance",
        "display_name": "Performance Best Practices",
        "content": """# Performance Best Practices

## Async/Await

```python
# Good: Concurrent I/O
async def process_items(items: List[str]) -> List[Result]:
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)

# Bad: Sequential I/O
async def process_items_slow(items: List[str]) -> List[Result]:
    results = []
    for item in items:
        result = await process_item(item)
        results.append(result)
    return results
```

## Caching

```python
from functools import lru_cache
from cachetools import TTLCache

# Simple LRU cache
@lru_cache(maxsize=100)
def expensive_computation(key: str) -> Result:
    ...

# TTL cache for time-sensitive data
cache = TTLCache(maxsize=1000, ttl=300)
```

## Database Optimization

- Use select_related() for ForeignKey
- Use prefetch_related() for ManyToMany
- Add indexes for frequently queried fields
- Use pagination for large result sets

## Profiling

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name: str):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    logger.info(f"{name} took {elapsed:.3f}s")

with timer("process_data"):
    result = await process_data()
```
""",
        "related_topics": ["handlers", "ai_integration"]
    },
}


class BestPracticeRepository(BaseRepository):
    """Repository für Best Practices."""
    
    async def get_by_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """Findet Best Practice nach Topic."""
        return _MOCK_BEST_PRACTICES.get(topic.lower())
    
    async def get_all_topics(self) -> List[str]:
        """Gibt alle verfügbaren Topics zurück."""
        return list(_MOCK_BEST_PRACTICES.keys())
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """Gibt alle Best Practices zurück."""
        return list(_MOCK_BEST_PRACTICES.values())


# =============================================================================
# REPOSITORY FACTORY
# =============================================================================

class RepositoryFactory:
    """
    Factory für Repository-Instanzen.
    
    Ermöglicht zentrale Konfiguration und Dependency Injection.
    """
    
    _instance: Optional['RepositoryFactory'] = None
    
    def __init__(self, use_django: bool = False):
        self.use_django = use_django
        self._domain_repo: Optional[DomainRepository] = None
        self._handler_repo: Optional[HandlerRepository] = None
        self._phase_repo: Optional[PhaseRepository] = None
        self._tag_repo: Optional[TagRepository] = None
        self._best_practice_repo: Optional[BestPracticeRepository] = None
    
    @classmethod
    def get_instance(cls, use_django: bool = False) -> 'RepositoryFactory':
        """Singleton-Pattern für Factory."""
        if cls._instance is None:
            cls._instance = cls(use_django=use_django)
        return cls._instance
    
    def get_domain_repository(self) -> DomainRepository:
        if self._domain_repo is None:
            self._domain_repo = DomainRepository(use_django=self.use_django)
        return self._domain_repo
    
    def get_handler_repository(self) -> HandlerRepository:
        if self._handler_repo is None:
            self._handler_repo = HandlerRepository(use_django=self.use_django)
        return self._handler_repo
    
    def get_phase_repository(self) -> PhaseRepository:
        if self._phase_repo is None:
            self._phase_repo = PhaseRepository(use_django=self.use_django)
        return self._phase_repo
    
    def get_tag_repository(self) -> TagRepository:
        if self._tag_repo is None:
            self._tag_repo = TagRepository(use_django=self.use_django)
        return self._tag_repo
    
    def get_best_practice_repository(self) -> BestPracticeRepository:
        if self._best_practice_repo is None:
            self._best_practice_repo = BestPracticeRepository(use_django=self.use_django)
        return self._best_practice_repo
    
    def clear_all_caches(self) -> None:
        """Leert alle Repository-Caches."""
        if self._domain_repo:
            self._domain_repo.clear_cache()
        if self._handler_repo:
            self._handler_repo.clear_cache()
        if self._phase_repo:
            self._phase_repo.clear_cache()
        if self._tag_repo:
            self._tag_repo.clear_cache()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "BaseRepository",
    "DomainRepository",
    "PhaseRepository",
    "HandlerRepository",
    "TagRepository",
    "BestPracticeRepository",
    "RepositoryFactory",
]
