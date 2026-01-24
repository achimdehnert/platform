"""
Django ORM Integration
======================

Verbindet MCP Server mit echten Django Handler-Daten.
Kann standalone (Mock) oder mit Django (echte Daten) laufen.

Usage:
    # Standalone (Mock-Daten)
    from bfagent_mcp.django_orm import DjangoORM
    orm = DjangoORM()
    
    # Mit Django
    import django
    django.setup()
    from bfagent_mcp.django_orm import DjangoORM
    orm = DjangoORM()
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES (Django-unabhängig)
# ═══════════════════════════════════════════════════════════════════════════════

class HandlerCategory(Enum):
    INPUT = "input"
    PROCESSING = "processing"
    OUTPUT = "output"
    AI_GENERATION = "ai_generation"
    AI_ANALYSIS = "ai_analysis"


@dataclass
class DomainInfo:
    """Domain Informationen"""
    id: str
    name: str
    description: str
    handler_count: int
    status: str  # production, beta, development


@dataclass
class HandlerInfo:
    """Handler Informationen"""
    id: int
    name: str
    slug: str
    description: str
    domain: str
    category: HandlerCategory
    version: str
    is_active: bool
    ai_powered: bool
    handler_class: str
    input_schema: Optional[Dict] = None
    output_schema: Optional[Dict] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DJANGO ORM WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class DjangoORM:
    """
    Django ORM Wrapper für MCP Server.
    
    Versucht Django zu nutzen, fällt auf Mock-Daten zurück.
    """
    
    def __init__(self):
        self._django_available = self._check_django()
        
        if self._django_available:
            print("✅ Django ORM verfügbar - nutze echte Daten")
        else:
            print("ℹ️ Django nicht verfügbar - nutze Mock-Daten")
    
    def _check_django(self) -> bool:
        """Prüft ob Django verfügbar ist"""
        try:
            import django
            from django.conf import settings
            return settings.configured
        except (ImportError, Exception):
            return False
    
    # ─────────────────────────────────────────────────────────────────────────
    # DOMAINS
    # ─────────────────────────────────────────────────────────────────────────
    
    def list_domains(self) -> List[DomainInfo]:
        """Listet alle Domains"""
        if self._django_available:
            return self._list_domains_django()
        return self._list_domains_mock()
    
    def _list_domains_django(self) -> List[DomainInfo]:
        """Echte Domains aus Django"""
        try:
            # ✅ KORRIGIERT: Nutze echte DomainArt Tabelle
            from apps.bfagent.models_domains import DomainArt
            
            domains = []
            for d in DomainArt.objects.filter(is_active=True).order_by('id'):
                # Status mapping
                status = "production"
                if d.is_experimental:
                    status = "development"
                
                # Handler count (falls verfügbar)
                handler_count = 0
                try:
                    if hasattr(d, 'handlers'):
                        handler_count = d.handlers.filter(is_active=True).count()
                except Exception:
                    pass
                
                domains.append(DomainInfo(
                    id=d.slug,
                    name=d.display_name,  # ✅ Korrigiert: display_name statt name
                    description=d.description or "",
                    handler_count=handler_count,
                    status=status,
                ))
            return domains
        except Exception as e:
            print(f"⚠️ Django Error: {e}")
            print(f"   Fallback zu Mock-Daten")
            return self._list_domains_mock()
    
    def _list_domains_mock(self) -> List[DomainInfo]:
        """Mock Domains"""
        return [
            DomainInfo("book_writing", "Book Writing", "Buchprojekte & Kreatives Schreiben", 20, "production"),
            DomainInfo("cad_analysis", "CAD Analysis", "CAD/IFC/DXF Analyse", 12, "beta"),
            DomainInfo("medical_translation", "Medical Translation", "Medizinische Übersetzungen", 8, "production"),
            DomainInfo("comic_creation", "Comic Creation", "Comic/Manga Erstellung", 15, "development"),
            DomainInfo("exschutz_forensics", "ExSchutz Forensics", "Explosionsschutz-Dokumentation", 10, "beta"),
            DomainInfo("dsgvo_compliance", "DSGVO Compliance", "DSGVO/GDPR Compliance", 6, "development"),
        ]
    
    # ─────────────────────────────────────────────────────────────────────────
    # HANDLERS
    # ─────────────────────────────────────────────────────────────────────────
    
    def list_handlers(self, domain: Optional[str] = None) -> List[HandlerInfo]:
        """Listet Handler, optional gefiltert nach Domain"""
        if self._django_available:
            return self._list_handlers_django(domain)
        return self._list_handlers_mock(domain)
    
    def _list_handlers_django(self, domain: Optional[str]) -> List[HandlerInfo]:
        """Echte Handler aus Django"""
        try:
            # ✅ KORRIGIERT: Nutze echte Handler Tabelle
            from apps.bfagent.models_handlers import Handler
            
            qs = Handler.objects.filter(is_active=True)
            if domain:
                # Domain-Filter über domain_id (slug)
                qs = qs.filter(domain_id=domain)
            
            handlers = []
            for h in qs[:50]:  # Limit
                # Category Mapping
                category = HandlerCategory.PROCESSING
                if hasattr(h, 'handler_type'):
                    handler_type = getattr(h, 'handler_type', '').lower()
                    if 'input' in handler_type:
                        category = HandlerCategory.INPUT
                    elif 'output' in handler_type:
                        category = HandlerCategory.OUTPUT
                    elif 'ai' in handler_type or 'llm' in handler_type:
                        category = HandlerCategory.AI_GENERATION
                
                handlers.append(HandlerInfo(
                    id=h.id,
                    name=h.name,
                    slug=h.slug,
                    description=h.description or "",
                    domain=h.domain_id or "unknown",
                    category=category,
                    version=h.version or "1.0.0",
                    is_active=h.is_active,
                    ai_powered=getattr(h, 'ai_powered', False),
                    handler_class=h.handler_class or "",
                    input_schema=h.input_schema if hasattr(h, 'input_schema') else None,
                    output_schema=h.output_schema if hasattr(h, 'output_schema') else None,
                ))
            return handlers
        except Exception as e:
            print(f"⚠️ Django Error beim Laden der Handler: {e}")
            print(f"   Fallback zu Mock-Daten")
            return self._list_handlers_mock(domain)
    
    def _list_handlers_mock(self, domain: Optional[str]) -> List[HandlerInfo]:
        """Mock Handler"""
        all_handlers = [
            # CAD Analysis
            HandlerInfo(1, "IFC Room Parser", "ifc_room_parser", "Parst Räume aus IFC", "cad_analysis", 
                       HandlerCategory.PROCESSING, "1.0.0", True, False, "apps.cad_analysis.handlers.IFCRoomParserHandler"),
            HandlerInfo(2, "DXF Dimension Extractor", "dxf_dimension_extractor", "Extrahiert Maße aus DXF", "cad_analysis",
                       HandlerCategory.PROCESSING, "1.0.0", True, False, "apps.cad_analysis.handlers.DXFDimensionHandler"),
            HandlerInfo(3, "CAD Quality Analyzer", "cad_quality_analyzer", "Analysiert CAD Qualität", "cad_analysis",
                       HandlerCategory.AI_ANALYSIS, "1.0.0", True, True, "apps.cad_analysis.handlers.QualityAnalyzerHandler"),
            
            # Book Writing
            HandlerInfo(10, "Chapter Generator", "chapter_generator", "Generiert Kapitel", "book_writing",
                       HandlerCategory.AI_GENERATION, "2.0.0", True, True, "apps.book_writing.handlers.ChapterGeneratorHandler"),
            HandlerInfo(11, "Character Creator", "character_creator", "Erstellt Charaktere", "book_writing",
                       HandlerCategory.AI_GENERATION, "1.5.0", True, True, "apps.book_writing.handlers.CharacterCreatorHandler"),
            
            # ExSchutz
            HandlerInfo(20, "Zone Classifier", "zone_classifier", "Klassifiziert Ex-Zonen", "exschutz_forensics",
                       HandlerCategory.AI_ANALYSIS, "1.0.0", True, True, "apps.exschutz.handlers.ZoneClassifierHandler"),
        ]
        
        if domain:
            return [h for h in all_handlers if h.domain == domain]
        return all_handlers
    
    def get_handler(self, handler_id: int) -> Optional[HandlerInfo]:
        """Holt einzelnen Handler"""
        handlers = self.list_handlers()
        for h in handlers:
            if h.id == handler_id:
                return h
        return None
    
    def search_handlers(self, query: str) -> List[HandlerInfo]:
        """Sucht Handler nach Name/Beschreibung"""
        query_lower = query.lower()
        handlers = self.list_handlers()
        return [
            h for h in handlers 
            if query_lower in h.name.lower() or query_lower in h.description.lower()
        ]
    
    # ─────────────────────────────────────────────────────────────────────────
    # STATISTICS
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück"""
        domains = self.list_domains()
        handlers = self.list_handlers()
        
        ai_handlers = [h for h in handlers if h.ai_powered]
        
        return {
            "total_domains": len(domains),
            "total_handlers": len(handlers),
            "ai_powered_handlers": len(ai_handlers),
            "ai_percentage": round(len(ai_handlers) / len(handlers) * 100, 1) if handlers else 0,
            "domains_by_status": {
                "production": len([d for d in domains if d.status == "production"]),
                "beta": len([d for d in domains if d.status == "beta"]),
                "development": len([d for d in domains if d.status == "development"]),
            },
            "handlers_by_category": {
                cat.value: len([h for h in handlers if h.category == cat])
                for cat in HandlerCategory
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_orm_instance: Optional[DjangoORM] = None


def get_orm() -> DjangoORM:
    """Gibt Singleton ORM Instanz zurück"""
    global _orm_instance
    if _orm_instance is None:
        _orm_instance = DjangoORM()
    return _orm_instance


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    orm = DjangoORM()
    
    print("\n=== Domains ===")
    for d in orm.list_domains():
        print(f"  {d.id}: {d.name} ({d.handler_count} handlers, {d.status})")
    
    print("\n=== CAD Handlers ===")
    for h in orm.list_handlers("cad_analysis"):
        ai = "🤖" if h.ai_powered else "⚙️"
        print(f"  {ai} {h.name}: {h.description}")
    
    print("\n=== Statistics ===")
    stats = orm.get_statistics()
    print(f"  Domains: {stats['total_domains']}")
    print(f"  Handlers: {stats['total_handlers']}")
    print(f"  AI-Powered: {stats['ai_percentage']}%")
