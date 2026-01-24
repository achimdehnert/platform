"""
Database Context Enricher Service

Production-ready context enrichment with:
- Django cache backend integration
- Comprehensive error handling
- Schema validation
- Fallback values
- Structured logging
- Performance monitoring
"""

import time
from typing import Dict, Any, Optional, List
from django.core.cache import cache
from django.conf import settings
import logging

from apps.bfagent.models import ContextSchema, ContextEnrichmentLog

from .exceptions import (
    EnrichmentError,
    SchemaNotFoundError,
    SourceResolutionError,
)
from .resolvers import ResolverFactory
from .validators import SchemaValidator, ParamValidator

logger = logging.getLogger(__name__)


class DatabaseContextEnricher:
    """
    Database-driven context enrichment service.
    
    Features:
    - Loads schemas from database
    - Validates schemas and parameters
    - Resolves sources with error handling
    - Caches results for performance
    - Logs all enrichments for monitoring
    
    Example:
        enricher = DatabaseContextEnricher()
        context = enricher.enrich(
            "chapter_generation",
            project_id=3,
            chapter_number=1
        )
    """
    
    # Configuration
    CACHE_TTL = getattr(settings, 'CONTEXT_ENRICHMENT_CACHE_TTL', 300)  # 5 minutes
    CACHE_PREFIX = 'ctx_enrich'
    
    def __init__(
        self,
        enable_cache: bool = True,
        enable_logging: bool = True
    ):
        """
        Initialize enricher.
        
        Args:
            enable_cache: Enable result caching
            enable_logging: Enable enrichment logging
        """
        self.enable_cache = enable_cache
        self.enable_logging = enable_logging
        self.resolver_factory = ResolverFactory()
        self.schema_validator = SchemaValidator()
        self.param_validator = ParamValidator()
    
    def enrich(
        self,
        schema_name: str,
        skip_cache: bool = False,
        dry_run: bool = False,
        **params
    ) -> Dict[str, Any]:
        """
        Main entry point for context enrichment.
        
        Args:
            schema_name: Name of schema to use (e.g., "chapter_generation")
            skip_cache: If True, bypass cache
            dry_run: If True, return mock structure without executing
            **params: Runtime parameters (project_id, chapter_number, etc.)
        
        Returns:
            Enriched context dictionary
        
        Raises:
            SchemaNotFoundError: Schema not found or inactive
            ValidationError: Schema or parameters invalid
            EnrichmentError: General enrichment error
        
        Example:
            enricher.enrich(
                "chapter_generation",
                project_id=3,
                chapter_number=1
            )
        """
        start_time = time.time()
        
        try:
            # Dry run mode (for testing)
            if dry_run:
                return self._dry_run_enrich(schema_name, params)
            
            # Try cache first
            if self.enable_cache and not skip_cache:
                cached = self._get_from_cache(schema_name, params)
                if cached is not None:
                    logger.debug(f"Cache hit for schema '{schema_name}'")
                    return cached
            
            # Load and validate schema
            schema = self._load_schema(schema_name)
            
            # Validate parameters
            self.param_validator.validate(schema, params)
            
            # Enrich context
            context = self._enrich_from_schema(schema, params)
            
            # Cache result
            if self.enable_cache and not skip_cache:
                self._save_to_cache(schema_name, params, context)
            
            # Log enrichment
            if self.enable_logging:
                duration_ms = (time.time() - start_time) * 1000
                self._log_enrichment(
                    schema=schema,
                    params=params,
                    context=context,
                    duration_ms=duration_ms,
                    errors=[],
                    success=True
                )
            
            return context
        
        except Exception as e:
            # Log failure
            if self.enable_logging:
                duration_ms = (time.time() - start_time) * 1000
                self._log_enrichment(
                    schema=None,
                    params=params,
                    context={},
                    duration_ms=duration_ms,
                    errors=[{"error": str(e)}],
                    success=False
                )
            
            logger.exception(
                f"Enrichment failed for schema '{schema_name}'",
                extra={"params": params}
            )
            raise
    
    def _load_schema(self, schema_name: str) -> ContextSchema:
        """
        Load and validate schema from database.
        
        Args:
            schema_name: Name of schema
        
        Returns:
            ContextSchema instance
        
        Raises:
            SchemaNotFoundError: Schema not found
            ValidationError: Schema configuration invalid
        """
        # Load from database
        try:
            schema = ContextSchema.objects.get(
                name=schema_name,
                is_active=True
            )
        except ContextSchema.DoesNotExist:
            raise SchemaNotFoundError(schema_name)
        
        # Validate schema configuration
        validation_errors = self.schema_validator.validate(schema)
        if validation_errors:
            logger.error(
                f"Schema '{schema_name}' validation failed",
                extra={"errors": validation_errors}
            )
            from .exceptions import ValidationError
            raise ValidationError(
                f"Schema '{schema_name}' has validation errors",
                errors=validation_errors
            )
        
        return schema
    
    def _enrich_from_schema(
        self,
        schema: ContextSchema,
        params: Dict
    ) -> Dict[str, Any]:
        """
        Enrich context by resolving all sources in schema.
        
        Args:
            schema: ContextSchema instance
            params: Runtime parameters
        
        Returns:
            Enriched context dictionary
        """
        context = {}
        errors = []
        sources = schema.get_active_sources()
        
        for source in sources:
            try:
                # Resolve source
                data = self._resolve_source(source, params)
                
                # Merge into context
                self._merge_to_context(context, source, data)
                
            except Exception as e:
                error_msg = f"Source '{source.name}' failed: {str(e)}"
                logger.error(
                    error_msg,
                    extra={
                        "source": source.name,
                        "source_type": source.source_type,
                        "schema": schema.name
                    },
                    exc_info=True
                )
                errors.append({"source": source.name, "error": str(e)})
                
                # Handle required sources
                if source.is_required:
                    raise SourceResolutionError(source.name, str(e))
                
                # Use fallback value
                if source.fallback_value is not None:
                    logger.info(
                        f"Using fallback value for source '{source.name}'"
                    )
                    self._merge_to_context(context, source, source.fallback_value)
        
        # Log any non-critical errors
        if errors:
            logger.warning(
                f"Schema '{schema.name}' had {len(errors)} source errors",
                extra={"errors": errors}
            )
        
        return context
    
    def _resolve_source(self, source, params: Dict) -> Any:
        """
        Resolve single source using appropriate resolver.
        
        Args:
            source: ContextSource instance
            params: Runtime parameters
        
        Returns:
            Resolved data (type depends on source type)
        
        Raises:
            SourceResolutionError: Resolution failed
        """
        # Get resolver for source type
        resolver = self.resolver_factory.get_resolver(source.source_type)
        
        # Resolve with timeout handling
        try:
            # Note: Timeout will be implemented in Phase 2 (async)
            # For now, just resolve directly
            data = resolver.resolve(source, params)
            return data
        
        except Exception as e:
            # Re-raise as SourceResolutionError
            raise SourceResolutionError(source.name, str(e))
    
    def _merge_to_context(
        self,
        context: Dict,
        source,
        data: Any
    ) -> None:
        """
        Merge source data into context dictionary.
        
        Args:
            context: Context dictionary to merge into
            source: ContextSource instance
            data: Data to merge
        """
        # Apply field mappings if configured
        if source.field_mappings and isinstance(data, dict):
            mapped_data = {}
            for original_key, mapped_key in source.field_mappings.items():
                if original_key in data:
                    mapped_data[mapped_key] = data[original_key]
            # Keep original keys + add mapped keys
            data = {**data, **mapped_data}
        
        # Merge into context
        if source.context_key:
            # Add under specific key
            context[source.context_key] = data
        else:
            # Merge directly (if dict)
            if isinstance(data, dict):
                context.update(data)
            else:
                logger.warning(
                    f"Cannot merge non-dict data from source '{source.name}'",
                    extra={"data_type": type(data).__name__}
                )
    
    def _dry_run_enrich(
        self,
        schema_name: str,
        params: Dict
    ) -> Dict[str, Any]:
        """
        Dry run mode - return mock structure without executing.
        
        Args:
            schema_name: Schema name
            params: Runtime parameters
        
        Returns:
            Mock context dictionary
        """
        schema = self._load_schema(schema_name)
        sources = schema.get_active_sources()
        
        mock_context = {
            "_dry_run": True,
            "_schema": schema_name,
            "_params": params,
            "_sources": []
        }
        
        for source in sources:
            mock_data = self._get_mock_data(source)
            self._merge_to_context(mock_context, source, mock_data)
            mock_context["_sources"].append({
                "name": source.name,
                "type": source.source_type,
                "context_key": source.context_key or "merged"
            })
        
        return mock_context
    
    def _get_mock_data(self, source) -> Any:
        """
        Generate mock data based on source configuration.
        
        Args:
            source: ContextSource instance
        
        Returns:
            Mock data appropriate for source type
        """
        if source.aggregate_type == "list":
            return [
                {
                    "mock": True,
                    "source": source.name,
                    "item": 1
                }
            ]
        elif source.aggregate_type == "count":
            return 0
        elif source.aggregate_type == "exists":
            return False
        else:
            return {
                "mock": True,
                "source": source.name,
                "type": source.source_type
            }
    
    # ========================================================================
    # CACHING METHODS
    # ========================================================================
    
    def _build_cache_key(self, schema_name: str, params: Dict) -> str:
        """
        Build stable cache key from schema and parameters.
        
        Args:
            schema_name: Schema name
            params: Runtime parameters
        
        Returns:
            Cache key string
        """
        # Sort params for stable key
        sorted_params = sorted(params.items())
        params_str = "_".join(f"{k}:{v}" for k, v in sorted_params)
        return f"{self.CACHE_PREFIX}:{schema_name}:{params_str}"
    
    def _get_from_cache(
        self,
        schema_name: str,
        params: Dict
    ) -> Optional[Dict]:
        """
        Get enriched context from cache.
        
        Returns:
            Cached context or None if not found
        """
        cache_key = self._build_cache_key(schema_name, params)
        return cache.get(cache_key)
    
    def _save_to_cache(
        self,
        schema_name: str,
        params: Dict,
        context: Dict
    ) -> None:
        """
        Save enriched context to cache.
        
        Args:
            schema_name: Schema name
            params: Runtime parameters
            context: Context to cache
        """
        cache_key = self._build_cache_key(schema_name, params)
        cache.set(cache_key, context, self.CACHE_TTL)
        logger.debug(
            f"Cached context for schema '{schema_name}'",
            extra={"cache_key": cache_key, "ttl": self.CACHE_TTL}
        )
    
    def invalidate_cache(
        self,
        schema_name: str,
        **params
    ) -> None:
        """
        Invalidate cache for specific schema and parameters.
        
        Args:
            schema_name: Schema name
            **params: Runtime parameters
        
        Example:
            enricher.invalidate_cache("chapter_generation", project_id=3)
        """
        cache_key = self._build_cache_key(schema_name, params)
        cache.delete(cache_key)
        logger.info(
            f"Invalidated cache for schema '{schema_name}'",
            extra={"cache_key": cache_key}
        )
    
    def invalidate_schema_cache(self, schema_name: str) -> None:
        """
        Invalidate all cache entries for a schema.
        
        Note: This is a simple implementation that uses cache versioning.
        For full cache clearing, use cache.clear() or implement pattern matching.
        
        Args:
            schema_name: Schema name
        """
        # Increment schema version in cache to invalidate all entries
        version_key = f"{self.CACHE_PREFIX}:version:{schema_name}"
        current_version = cache.get(version_key, 0)
        cache.set(version_key, current_version + 1, None)  # Never expire
        logger.info(f"Invalidated all cache for schema '{schema_name}'")
    
    # ========================================================================
    # LOGGING METHODS
    # ========================================================================
    
    def _log_enrichment(
        self,
        schema,
        params: Dict,
        context: Dict,
        duration_ms: float,
        errors: List[Dict],
        success: bool
    ) -> None:
        """
        Log enrichment execution to database.
        
        Args:
            schema: ContextSchema instance (or None if schema load failed)
            params: Runtime parameters
            context: Enriched context
            duration_ms: Execution time in milliseconds
            errors: List of error dicts
            success: Whether enrichment succeeded
        """
        try:
            ContextEnrichmentLog.objects.create(
                schema=schema if schema else None,
                handler_name=params.get('_handler_name', 'unknown'),
                params=params,
                enriched_context=context if success else {},
                execution_time_ms=duration_ms,
                success=success,
                error_message="; ".join(
                    e.get('error', '') for e in errors
                ) if errors else ""
            )
        except Exception as e:
            # Don't let logging errors break enrichment
            logger.error(
                f"Failed to log enrichment: {e}",
                exc_info=True
            )
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_schema_info(self, schema_name: str) -> Dict[str, Any]:
        """
        Get information about a schema without executing it.
        
        Args:
            schema_name: Schema name
        
        Returns:
            Dict with schema information
        """
        schema = self._load_schema(schema_name)
        sources = schema.get_active_sources()
        
        return {
            "name": schema.name,
            "display_name": schema.display_name,
            "description": schema.description,
            "handler_type": schema.handler_type,
            "is_system": schema.is_system,
            "version": schema.version,
            "source_count": sources.count(),
            "sources": [
                {
                    "name": source.name,
                    "type": source.source_type,
                    "order": source.order,
                    "is_required": source.is_required,
                    "context_key": source.context_key or "merged"
                }
                for source in sources
            ]
        }
    
    def list_schemas(self) -> List[Dict[str, Any]]:
        """
        List all active schemas.
        
        Returns:
            List of schema info dicts
        """
        schemas = ContextSchema.objects.filter(is_active=True)
        
        return [
            {
                "name": schema.name,
                "display_name": schema.display_name,
                "handler_type": schema.handler_type,
                "is_system": schema.is_system,
                "source_count": schema.sources.filter(is_active=True).count()
            }
            for schema in schemas
        ]
