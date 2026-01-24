"""
BF Agent MCP Server - Service Layer
====================================

Business Logic Layer zwischen Repository und MCP Server.

Design-Prinzipien:
- Single Responsibility: Jeder Service hat eine klare Aufgabe
- Dependency Injection: Repositories werden injiziert
- Testbarkeit: Services sind durch Mock-Repos testbar
- Orchestration: Services koordinieren Repository-Aufrufe

Service-Hierarchie:
- DomainService: Domain-Operationen
- HandlerService: Handler-Operationen
- CodeGenerationService: Code-Generierung (Template + AI)
- ValidationService: Code-Validierung
- BestPracticeService: Best Practices
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core import (
    DomainDTO,
    PhaseDTO,
    HandlerDTO,
    DomainStatus,
    HandlerType,
    AIProvider,
    ResponseFormat,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    GeneratedCode,
    DomainScaffold,
    DomainNotFoundError,
    HandlerNotFoundError,
    DEFAULT_PAGE_SIZE,
)
from ..repositories import (
    RepositoryFactory,
    DomainRepository,
    HandlerRepository,
    PhaseRepository,
    BestPracticeRepository,
)


# =============================================================================
# FORMATTERS (Presentation Logic)
# =============================================================================

class MarkdownFormatter:
    """Formatiert Daten als Markdown."""
    
    STATUS_EMOJI = {
        DomainStatus.PRODUCTION: "✅",
        DomainStatus.BETA: "🟡",
        DomainStatus.DEVELOPMENT: "🟢",
        DomainStatus.PLANNED: "📋",
        DomainStatus.DEPRECATED: "⚠️",
    }
    
    HANDLER_TYPE_EMOJI = {
        HandlerType.AI_POWERED: "🤖",
        HandlerType.RULE_BASED: "⚙️",
        HandlerType.HYBRID: "🔄",
        HandlerType.UTILITY: "🔧",
    }
    
    @classmethod
    def format_domain(
        cls, 
        domain: DomainDTO, 
        phases: List[PhaseDTO] = None,
        handlers: List[HandlerDTO] = None,
        tags: List[str] = None,
    ) -> str:
        """Formatiert Domain als Markdown."""
        emoji = cls.STATUS_EMOJI.get(domain.status, "")
        
        md = f"## {domain.display_name} {emoji}\n\n"
        md += f"**Domain ID:** `{domain.domain_id}`  \n"
        md += f"**Status:** {domain.status.value.title()}  \n"
        
        if handlers:
            md += f"**Handlers:** {len(handlers)}  \n"
        
        md += f"\n### Description\n\n{domain.description}\n\n"
        
        if phases:
            phase_names = [p.display_name for p in sorted(phases, key=lambda x: x.order)]
            md += f"### Workflow Phases\n\n{' → '.join(phase_names)}\n\n"
        
        if tags:
            md += f"### Tags\n\n{', '.join(f'`{tag}`' for tag in tags)}\n\n"
        
        if handlers:
            md += "### Handlers\n\n"
            for h in handlers:
                type_emoji = cls.HANDLER_TYPE_EMOJI.get(h.handler_type, "")
                ai_info = f" ({h.ai_provider.value})" if h.ai_provider != AIProvider.NONE else ""
                md += f"- **{h.name}** {type_emoji}{ai_info}: {h.description[:100]}...\n"
        
        return md
    
    @classmethod
    def format_handler(cls, handler: HandlerDTO) -> str:
        """Formatiert Handler als Markdown."""
        type_emoji = cls.HANDLER_TYPE_EMOJI.get(handler.handler_type, "")
        ai_info = f"**AI Provider:** {handler.ai_provider.value}" if handler.ai_provider != AIProvider.NONE else "**Type:** Rule-based"
        
        md = f"### {handler.name} {type_emoji}\n\n"
        md += f"**Domain:** {handler.domain_id}  \n"
        md += f"**Handler Type:** {handler.handler_type.value}  \n"
        md += f"{ai_info}  \n"
        md += f"**Est. Duration:** {handler.estimated_duration_seconds}s  \n"
        
        if handler.tags:
            md += f"**Tags:** {', '.join(f'`{t}`' for t in handler.tags)}  \n"
        
        md += f"\n#### Description\n\n{handler.description}\n\n"
        
        md += "#### Input Schema\n\n```python\n"
        md += json.dumps(handler.input_schema, indent=2)
        md += "\n```\n\n"
        
        md += "#### Output Schema\n\n```python\n"
        md += json.dumps(handler.output_schema, indent=2)
        md += "\n```\n"
        
        return md
    
    @classmethod
    def format_search_results(
        cls, 
        query: str, 
        results: List[Tuple[HandlerDTO, float]],
        total: int,
        has_more: bool
    ) -> str:
        """Formatiert Suchergebnisse als Markdown."""
        md = "# Handler Search Results\n\n"
        md += f"**Query:** {query}  \n"
        md += f"**Found:** {total} handlers  \n"
        
        if has_more:
            md += f"**Showing:** {len(results)} (more available)\n"
        
        md += "\n"
        
        if not results:
            md += "_No handlers found matching your query._\n\n"
            md += "**Suggestions:**\n"
            md += "- Try broader search terms\n"
            md += "- Check available domains with `bfagent_list_domains`\n"
            md += "- Remove filters\n"
            return md
        
        for handler, score in results:
            type_emoji = cls.HANDLER_TYPE_EMOJI.get(handler.handler_type, "")
            md += f"### {handler.name} {type_emoji} (Score: {score:.1f})\n\n"
            md += f"**Domain:** `{handler.domain_id}` | "
            md += f"**Type:** {handler.handler_type.value}"
            
            if handler.ai_provider != AIProvider.NONE:
                md += f" | **AI:** {handler.ai_provider.value}"
            
            md += f"\n\n{handler.description}\n\n"
        
        return md
    
    @classmethod
    def format_validation_result(cls, result: ValidationResult) -> str:
        """Formatiert Validierungsergebnis als Markdown."""
        status = "✅ PASSED" if result.is_valid else "❌ FAILED"
        
        md = "# Handler Validation Report\n\n"
        md += f"**Status:** {status}  \n"
        md += f"**Score:** {result.score}/100\n\n"
        
        if result.errors:
            md += "## ❌ Errors (Must Fix)\n\n"
            for issue in result.errors:
                md += f"- **{issue.category}:** {issue.message}\n"
                if issue.suggestion:
                    md += f"  - _Suggestion: {issue.suggestion}_\n"
            md += "\n"
        
        if result.warnings:
            md += "## ⚠️ Warnings\n\n"
            for issue in result.warnings:
                md += f"- **{issue.category}:** {issue.message}\n"
            md += "\n"
        
        suggestions = [i for i in result.issues if i.severity == ValidationSeverity.INFO]
        if suggestions:
            md += "## 💡 Suggestions\n\n"
            for issue in suggestions:
                md += f"- {issue.message}\n"
            md += "\n"
        
        return md


class JsonFormatter:
    """Formatiert Daten als JSON."""
    
    @classmethod
    def format_domain(
        cls,
        domain: DomainDTO,
        phases: List[PhaseDTO] = None,
        handlers: List[HandlerDTO] = None,
        tags: List[str] = None,
    ) -> str:
        """Formatiert Domain als JSON."""
        data = {
            "id": domain.id,
            "domain_id": domain.domain_id,
            "display_name": domain.display_name,
            "description": domain.description,
            "status": domain.status.value,
            "icon": domain.icon,
            "color": domain.color,
        }
        
        if phases:
            data["phases"] = [
                {
                    "name": p.name,
                    "display_name": p.display_name,
                    "order": p.order,
                    "estimated_duration_seconds": p.estimated_duration_seconds,
                }
                for p in sorted(phases, key=lambda x: x.order)
            ]
        
        if handlers:
            data["handlers"] = [
                {
                    "id": h.id,
                    "name": h.name,
                    "handler_type": h.handler_type.value,
                    "ai_provider": h.ai_provider.value,
                    "description": h.description,
                }
                for h in handlers
            ]
            data["handler_count"] = len(handlers)
        
        if tags:
            data["tags"] = tags
        
        return json.dumps(data, indent=2)


# =============================================================================
# DOMAIN SERVICE
# =============================================================================

class DomainService:
    """
    Service für Domain-Operationen.
    
    Koordiniert Repository-Aufrufe und Formatierung.
    """
    
    def __init__(
        self,
        domain_repo: DomainRepository = None,
        phase_repo: PhaseRepository = None,
        handler_repo: HandlerRepository = None,
    ):
        factory = RepositoryFactory.get_instance()
        self.domain_repo = domain_repo or factory.get_domain_repository()
        self.phase_repo = phase_repo or factory.get_phase_repository()
        self.handler_repo = handler_repo or factory.get_handler_repository()
    
    async def list_domains(
        self,
        status_filter: Optional[DomainStatus] = None,
        include_handler_count: bool = True,
        include_phases: bool = True,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """
        Listet alle Domains auf.
        
        Args:
            status_filter: Optional Status-Filter
            include_handler_count: Handler-Anzahl inkludieren
            include_phases: Phasen inkludieren
            response_format: Ausgabeformat
            
        Returns:
            Formatierte Domain-Liste
        """
        domains = await self.domain_repo.get_all(status_filter=status_filter)
        total = await self.domain_repo.count(status_filter=status_filter)
        
        if response_format == ResponseFormat.JSON:
            data = {
                "total": total,
                "domains": []
            }
            
            for domain in domains:
                domain_data = {
                    "id": domain.id,
                    "domain_id": domain.domain_id,
                    "display_name": domain.display_name,
                    "status": domain.status.value,
                }
                
                if include_handler_count:
                    handlers = await self.handler_repo.get_by_domain(domain.domain_id)
                    domain_data["handler_count"] = len(handlers)
                
                if include_phases:
                    phases = await self.phase_repo.get_by_domain(domain.domain_id)
                    domain_data["phases"] = [p.display_name for p in phases]
                
                data["domains"].append(domain_data)
            
            return json.dumps(data, indent=2)
        
        # Markdown format
        md = "# BF Agent Domains\n\n"
        md += f"**Total Domains:** {total}\n\n"
        
        for domain in domains:
            phases = await self.phase_repo.get_by_domain(domain.domain_id) if include_phases else []
            handlers = await self.handler_repo.get_by_domain(domain.domain_id) if include_handler_count else []
            
            md += MarkdownFormatter.format_domain(domain, phases=phases, handlers=handlers)
            md += "\n---\n\n"
        
        return md
    
    async def get_domain(
        self,
        domain_id: str,
        include_handlers: bool = True,
        include_phases: bool = True,
        include_statistics: bool = False,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """
        Gibt Details einer Domain zurück.
        
        Args:
            domain_id: Domain-Identifier
            include_handlers: Handler inkludieren
            include_phases: Phasen inkludieren
            include_statistics: Statistiken inkludieren (TODO)
            response_format: Ausgabeformat
            
        Returns:
            Formatierte Domain-Details
            
        Raises:
            DomainNotFoundError: Domain nicht gefunden
        """
        domain = await self.domain_repo.get_by_domain_id(domain_id)
        
        if not domain:
            raise DomainNotFoundError(domain_id)
        
        phases = await self.phase_repo.get_by_domain(domain_id) if include_phases else []
        handlers = await self.handler_repo.get_by_domain(domain_id) if include_handlers else []
        
        # TODO: Tags aus Repository laden
        tags = []
        
        if response_format == ResponseFormat.JSON:
            return JsonFormatter.format_domain(domain, phases, handlers, tags)
        
        return MarkdownFormatter.format_domain(domain, phases, handlers, tags)


# =============================================================================
# HANDLER SERVICE
# =============================================================================

class HandlerService:
    """
    Service für Handler-Operationen.
    """
    
    def __init__(
        self,
        handler_repo: HandlerRepository = None,
        domain_repo: DomainRepository = None,
    ):
        factory = RepositoryFactory.get_instance()
        self.handler_repo = handler_repo or factory.get_handler_repository()
        self.domain_repo = domain_repo or factory.get_domain_repository()
    
    async def search_handlers(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        handler_type_filter: Optional[HandlerType] = None,
        tags_filter: Optional[List[str]] = None,
        include_inactive: bool = False,
        limit: int = 10,
        offset: int = 0,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """
        Sucht Handler nach Funktionalität.
        
        Args:
            query: Suchbegriff
            domain_filter: Domain-Filter
            handler_type_filter: Handler-Type-Filter
            tags_filter: Tags-Filter
            include_inactive: Inaktive Handler inkludieren
            limit: Max. Ergebnisse
            offset: Offset für Pagination
            response_format: Ausgabeformat
            
        Returns:
            Formatierte Suchergebnisse
        """
        results = await self.handler_repo.search(
            query=query,
            domain_filter=domain_filter,
            handler_type_filter=handler_type_filter,
            tags_filter=tags_filter,
            limit=limit + 1,  # +1 to check if more available
        )
        
        has_more = len(results) > limit
        results = results[:limit]
        total = len(results)  # In production: separate count query
        
        if response_format == ResponseFormat.JSON:
            return json.dumps({
                "query": query,
                "total": total,
                "has_more": has_more,
                "results": [
                    {
                        "handler": {
                            "id": h.id,
                            "name": h.name,
                            "domain_id": h.domain_id,
                            "handler_type": h.handler_type.value,
                            "ai_provider": h.ai_provider.value,
                            "description": h.description,
                            "tags": h.tags,
                        },
                        "score": score
                    }
                    for h, score in results
                ]
            }, indent=2)
        
        return MarkdownFormatter.format_search_results(query, results, total, has_more)
    
    async def get_handler(
        self,
        handler_id: int,
        include_schema: bool = True,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """
        Gibt Handler-Details zurück.
        
        Args:
            handler_id: Handler-ID
            include_schema: Schemas inkludieren
            response_format: Ausgabeformat
            
        Returns:
            Formatierte Handler-Details
            
        Raises:
            HandlerNotFoundError: Handler nicht gefunden
        """
        handler = await self.handler_repo.get_by_id(handler_id)
        
        if not handler:
            raise HandlerNotFoundError(handler_id)
        
        if response_format == ResponseFormat.JSON:
            data = {
                "id": handler.id,
                "name": handler.name,
                "domain_id": handler.domain_id,
                "handler_type": handler.handler_type.value,
                "ai_provider": handler.ai_provider.value,
                "description": handler.description,
                "estimated_duration_seconds": handler.estimated_duration_seconds,
                "tags": handler.tags,
            }
            
            if include_schema:
                data["input_schema"] = handler.input_schema
                data["output_schema"] = handler.output_schema
            
            return json.dumps(data, indent=2)
        
        return MarkdownFormatter.format_handler(handler)


# =============================================================================
# VALIDATION SERVICE
# =============================================================================

class ValidationService:
    """
    Service für Code-Validierung.
    
    Prüft Python-Code gegen BF Agent Standards.
    """
    
    async def validate_handler(
        self,
        code: str,
        check_inheritance: bool = True,
        check_pydantic: bool = True,
        check_docstrings: bool = True,
        check_error_handling: bool = True,
        check_three_phase: bool = True,
        check_type_hints: bool = True,
        check_logging: bool = True,
        strict_mode: bool = False,
    ) -> ValidationResult:
        """
        Validiert Handler-Code.
        
        Args:
            code: Python-Code
            check_*: Welche Prüfungen durchführen
            strict_mode: Warnings als Errors behandeln
            
        Returns:
            ValidationResult mit Issues und Score
        """
        issues: List[ValidationIssue] = []
        
        # Check: BaseHandler Inheritance
        if check_inheritance:
            if 'BaseHandler' not in code and 'class ' in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="inheritance",
                    message="Handler should inherit from BaseHandler",
                    suggestion="Add 'from apps.core.handlers.base import BaseHandler' and inherit from it"
                ))
        
        # Check: Pydantic Usage
        if check_pydantic:
            if 'BaseModel' not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="pydantic",
                    message="Handler should use Pydantic BaseModel for input/output schemas",
                    suggestion="Define input_schema and output_schema classes using Pydantic"
                ))
            
            if 'Field(' not in code and 'BaseModel' in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="pydantic",
                    message="Consider using Field() for better validation and documentation"
                ))
            
            if 'ConfigDict' not in code and 'model_config' not in code and 'BaseModel' in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="pydantic",
                    message="Consider adding model_config with ConfigDict for Pydantic v2"
                ))
        
        # Check: Docstrings
        if check_docstrings:
            if '"""' not in code and "'''" not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="docstring",
                    message="Handler should have docstrings",
                    suggestion="Add docstrings to class and methods"
                ))
        
        # Check: Error Handling
        if check_error_handling:
            if 'try:' not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="error_handling",
                    message="Consider adding try/except blocks for error handling"
                ))
            
            if 'except Exception' in code and 'except Exception as' not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="error_handling",
                    message="Bare 'except Exception' - consider capturing the exception"
                ))
        
        # Check: Three-Phase Pattern
        if check_three_phase:
            if 'async def validate' not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="three_phase",
                    message="Consider adding validate() method for input validation (Phase 1)"
                ))
            
            if 'async def process' not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="three_phase",
                    message="Consider adding process() method for business logic (Phase 2)"
                ))
            
            if 'async def save_result' not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="three_phase",
                    message="Consider adding save_result() method for persistence (Phase 3)"
                ))
        
        # Check: Type Hints
        if check_type_hints:
            # Simple check: functions should have return type hints
            if 'def ' in code and ') ->' not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="type_hints",
                    message="Add return type hints to methods",
                    suggestion="Use -> ReturnType after function parameters"
                ))
        
        # Check: Logging
        if check_logging:
            if 'logger' not in code.lower() and 'logging' not in code:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="logging",
                    message="Consider adding logging for debugging and monitoring"
                ))
        
        # Calculate score
        error_count = len([i for i in issues if i.severity == ValidationSeverity.ERROR])
        warning_count = len([i for i in issues if i.severity == ValidationSeverity.WARNING])
        
        score = max(0, 100 - (error_count * 20) - (warning_count * 5))
        
        # Determine validity
        is_valid = error_count == 0
        if strict_mode:
            is_valid = is_valid and warning_count == 0
        
        return ValidationResult(
            is_valid=is_valid,
            score=score,
            issues=issues
        )
    
    async def validate_handler_formatted(
        self,
        code: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        **kwargs
    ) -> str:
        """
        Validiert Handler-Code und formatiert das Ergebnis.
        
        Returns:
            Formatierte Validierungsergebnis
        """
        result = await self.validate_handler(code, **kwargs)
        
        if response_format == ResponseFormat.JSON:
            return json.dumps({
                "is_valid": result.is_valid,
                "score": result.score,
                "errors": [
                    {"category": i.category, "message": i.message, "suggestion": i.suggestion}
                    for i in result.errors
                ],
                "warnings": [
                    {"category": i.category, "message": i.message}
                    for i in result.warnings
                ],
                "suggestions": [i.message for i in result.issues if i.severity == ValidationSeverity.INFO]
            }, indent=2)
        
        return MarkdownFormatter.format_validation_result(result)


# =============================================================================
# BEST PRACTICE SERVICE
# =============================================================================

class BestPracticeService:
    """
    Service für Best Practices.
    """
    
    def __init__(self, repo: BestPracticeRepository = None):
        factory = RepositoryFactory.get_instance()
        self.repo = repo or factory.get_best_practice_repository()
    
    async def get_best_practices(
        self,
        topic: str,
        include_examples: bool = True,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """
        Gibt Best Practices für ein Topic zurück.
        
        Args:
            topic: Topic-Name
            include_examples: Code-Beispiele inkludieren
            response_format: Ausgabeformat
            
        Returns:
            Formatierte Best Practices
        """
        practice = await self.repo.get_by_topic(topic)
        
        if not practice:
            available = await self.repo.get_all_topics()
            return f"No best practices found for topic: '{topic}'.\n\nAvailable topics: {', '.join(available)}"
        
        if response_format == ResponseFormat.JSON:
            return json.dumps({
                "topic": practice["topic"],
                "display_name": practice["display_name"],
                "content": practice["content"],
                "related_topics": practice.get("related_topics", [])
            }, indent=2)
        
        return practice["content"]
    
    async def list_topics(self) -> List[str]:
        """Gibt alle verfügbaren Topics zurück."""
        return await self.repo.get_all_topics()


# =============================================================================
# SERVICE FACTORY
# =============================================================================

class ServiceFactory:
    """
    Factory für Service-Instanzen.
    
    Ermöglicht zentrale Konfiguration und Dependency Injection.
    """
    
    _instance: Optional['ServiceFactory'] = None
    
    def __init__(self):
        self._domain_service: Optional[DomainService] = None
        self._handler_service: Optional[HandlerService] = None
        self._validation_service: Optional[ValidationService] = None
        self._best_practice_service: Optional[BestPracticeService] = None
    
    @classmethod
    def get_instance(cls) -> 'ServiceFactory':
        """Singleton-Pattern."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_domain_service(self) -> DomainService:
        if self._domain_service is None:
            self._domain_service = DomainService()
        return self._domain_service
    
    def get_handler_service(self) -> HandlerService:
        if self._handler_service is None:
            self._handler_service = HandlerService()
        return self._handler_service
    
    def get_validation_service(self) -> ValidationService:
        if self._validation_service is None:
            self._validation_service = ValidationService()
        return self._validation_service
    
    def get_best_practice_service(self) -> BestPracticeService:
        if self._best_practice_service is None:
            self._best_practice_service = BestPracticeService()
        return self._best_practice_service


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Formatters
    "MarkdownFormatter",
    "JsonFormatter",
    # Services
    "DomainService",
    "HandlerService",
    "ValidationService",
    "BestPracticeService",
    # Factory
    "ServiceFactory",
]
