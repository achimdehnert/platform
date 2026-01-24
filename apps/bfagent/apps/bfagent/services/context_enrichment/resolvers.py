"""
Context Source Resolvers

Resolvers for different source types (model, query, computed, etc).
Each resolver is responsible for fetching data from a specific source type.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from django.apps import apps
from django.db.models import Q
import logging
import re

from .exceptions import ModelNotFoundError, FunctionNotFoundError
from . import computed_functions

logger = logging.getLogger(__name__)


class BaseResolver(ABC):
    """Abstract base class for all resolvers"""

    @abstractmethod
    def resolve(self, source, params: Dict) -> Any:
        """
        Resolve data from source.

        Args:
            source: ContextSource instance
            params: Runtime parameters

        Returns:
            Resolved data (type depends on source)

        Raises:
            SourceResolutionError: If resolution fails
        """
        pass

    def _resolve_placeholders(self, config: Any, params: Dict) -> Any:
        """
        Recursively replace {placeholder} patterns with actual values.

        Args:
            config: Configuration (can be dict, list, str, or primitive)
            params: Runtime parameters

        Returns:
            Configuration with placeholders replaced
        """
        if isinstance(config, dict):
            return {
                key: self._resolve_placeholders(value, params)
                for key, value in config.items()
            }

        elif isinstance(config, list):
            return [
                self._resolve_placeholders(item, params)
                for item in config
            ]

        elif isinstance(config, str):
            # Replace {param_name} with actual value
            def replacer(match):
                param_name = match.group(1)
                value = params.get(param_name)
                if value is None:
                    logger.warning(f"Placeholder {{  {param_name}}} not found in params")
                    return match.group(0)  # Keep original if not found
                return str(value)

            return re.sub(r'\{(\w+)\}', replacer, config)

        else:
            # Primitive value, return as-is
            return config


class ModelResolver(BaseResolver):
    """Resolver for 'model' source type - fetch by primary key"""

    def resolve(self, source, params: Dict) -> Dict:
        """
        Fetch model instance by primary key.

        Returns:
            Dictionary with requested fields
        """
        # Get model class
        try:
            model = apps.get_model('bfagent', source.model_name)
        except LookupError:
            raise ModelNotFoundError(source.name, source.model_name)

        # Resolve filter config (replace placeholders)
        filter_config = self._resolve_placeholders(source.filter_config, params)

        # Fetch instance
        try:
            instance = model.objects.get(**filter_config)
        except model.DoesNotExist:
            logger.warning(
                f"Model instance not found: {source.model_name} with {filter_config}"
            )
            return source.default_value or {}
        except model.MultipleObjectsReturned:
            logger.error(
                f"Multiple instances found for {source.model_name} with {filter_config}"
            )
            instance = model.objects.filter(**filter_config).first()

        # Extract requested fields
        return self._extract_fields(instance, source.fields or [])

    def _extract_fields(self, instance, field_names: List[str]) -> Dict:
        """Extract specified fields from model instance"""
        if not field_names:
            # No specific fields requested, extract all non-relation fields
            field_names = [
                f.name for f in instance._meta.fields
                if not f.is_relation
            ]

        result = {}
        for field_name in field_names:
            try:
                value = getattr(instance, field_name, None)
                result[field_name] = value
            except AttributeError:
                logger.warning(
                    f"Field '{field_name}' not found on {instance._meta.model_name}"
                )

        return result


class QueryResolver(BaseResolver):
    """Resolver for 'related_query' source type - query with filters"""

    def resolve(self, source, params: Dict) -> Any:
        """
        Execute query with filters.

        Returns:
            Depends on aggregate_type:
            - 'first'/'last': Single dict
            - 'list': List of dicts
            - 'all': QuerySet
            - 'count': Integer
            - 'exists': Boolean
        """
        # Get model class
        try:
            model = apps.get_model('bfagent', source.model_name)
        except LookupError:
            raise ModelNotFoundError(source.name, source.model_name)

        # Resolve filter config
        filter_config = self._resolve_placeholders(source.filter_config, params)

        # Build queryset
        queryset = model.objects.filter(**filter_config)

        # Apply ordering if specified
        if source.order_by:
            queryset = queryset.order_by(source.order_by)

        # Apply aggregation
        aggregate_type = source.aggregate_type or 'first'

        if aggregate_type == 'first':
            instance = queryset.first()
            if instance is None:
                return source.default_value
            return self._extract_fields(instance, source.fields or [])

        elif aggregate_type == 'last':
            instance = queryset.last()
            if instance is None:
                return source.default_value
            return self._extract_fields(instance, source.fields or [])

        elif aggregate_type == 'list':
            return [
                self._extract_fields(instance, source.fields or [])
                for instance in queryset
            ]

        elif aggregate_type == 'all':
            return queryset

        elif aggregate_type == 'count':
            return queryset.count()

        elif aggregate_type == 'exists':
            return queryset.exists()

        else:
            logger.error(f"Unknown aggregate_type: {aggregate_type}")
            return source.default_value

    def _extract_fields(self, instance, field_names: List[str]) -> Dict:
        """Extract specified fields from model instance"""
        if not field_names:
            # Extract all non-relation fields
            field_names = [
                f.name for f in instance._meta.fields
                if not f.is_relation
            ]

        result = {}
        for field_name in field_names:
            try:
                value = getattr(instance, field_name, None)
                result[field_name] = value
            except AttributeError:
                logger.warning(
                    f"Field '{field_name}' not found on {instance._meta.model_name}"
                )

        return result


class ComputedResolver(BaseResolver):
    """Resolver for 'computed' source type - call Python function"""

    def resolve(self, source, params: Dict) -> Any:
        """
        Call computed function.

        Returns:
            Whatever the function returns
        """
        function_name = source.function_name

        # Get function from computed_functions module
        if not hasattr(computed_functions, function_name):
            raise FunctionNotFoundError(source.name, function_name)

        func = getattr(computed_functions, function_name)

        # Resolve function parameters
        func_params = self._resolve_placeholders(source.function_params or {}, params)

        # Call function
        try:
            result = func(**func_params)
            return result
        except Exception as e:
            logger.error(
                f"Computed function '{function_name}' failed: {e}",
                exc_info=True
            )
            return source.default_value


class BeatSheetResolver(BaseResolver):
    """Resolver for 'beat_sheet' source type - get beat sheet info"""

    def resolve(self, source, params: Dict) -> Dict:
        """
        Get beat sheet information.

        Returns:
            Dict with beat information
        """
        function_name = source.function_name or 'get_beat_info'

        # Get function
        if not hasattr(computed_functions, function_name):
            raise FunctionNotFoundError(source.name, function_name)

        func = getattr(computed_functions, function_name)

        # Resolve parameters
        func_params = self._resolve_placeholders(source.function_params or {}, params)

        # Call function
        try:
            result = func(**func_params)
            return result or source.default_value or {}
        except Exception as e:
            logger.error(
                f"Beat sheet function '{function_name}' failed: {e}",
                exc_info=True
            )
            return source.default_value or {}


class ResolverFactory:
    """Factory for creating resolvers based on source type"""

    def __init__(self):
        self._resolvers = {
            'model': ModelResolver(),
            'related_query': QueryResolver(),
            'computed': ComputedResolver(),
            'beat_sheet': BeatSheetResolver(),
        }

    def get_resolver(self, source_type: str) -> BaseResolver:
        """Get resolver for source type"""
        resolver = self._resolvers.get(source_type)

        if resolver is None:
            raise ValueError(f"Unknown source type: {source_type}")

        return resolver

    def register_resolver(self, source_type: str, resolver: BaseResolver) -> None:
        """Register custom resolver"""
        self._resolvers[source_type] = resolver
