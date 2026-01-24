"""
Context Enrichment Validators

Validation logic for schemas, sources, and parameters.
"""

import re
from typing import List, Dict, Set
from django.apps import apps
import logging

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates ContextSchema configuration"""

    def validate(self, schema) -> List[str]:
        """
        Validate schema and all its sources.

        Args:
            schema: ContextSchema instance

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check if schema has active sources
        active_sources = schema.get_active_sources()
        if not active_sources:
            errors.append("Schema has no active sources")
            return errors

        # Validate each source
        source_validator = SourceValidator()
        for source in active_sources:
            source_errors = source_validator.validate(source)
            errors.extend([
                f"Source '{source.name}': {err}"
                for err in source_errors
            ])

        return errors


class SourceValidator:
    """Validates individual ContextSource configuration"""

    def validate(self, source) -> List[str]:
        """
        Validate source configuration.

        Returns:
            List of error messages
        """
        errors = []

        # Validate based on source type
        validators = {
            'model': self._validate_model_source,
            'related_query': self._validate_query_source,
            'computed': self._validate_computed_source,
            'beat_sheet': self._validate_beat_sheet_source,
        }

        validator = validators.get(source.source_type)
        if not validator:
            errors.append(f"Unknown source type: {source.source_type}")
            return errors

        errors.extend(validator(source))

        # Validate timeout
        if source.timeout_seconds <= 0:
            errors.append("timeout_seconds must be positive")

        return errors

    def _validate_model_source(self, source) -> List[str]:
        """Validate model-based source"""
        errors = []

        # Check model_name is provided
        if not source.model_name:
            errors.append("model_name is required for model source")
            return errors

        # Check model exists
        try:
            apps.get_model('bfagent', source.model_name)
        except LookupError:
            errors.append(f"Model '{source.model_name}' not found")

        # Check filter_config has pk field
        if not source.filter_config or 'pk' not in source.filter_config:
            errors.append("filter_config must include 'pk' field for model source")

        return errors

    def _validate_query_source(self, source) -> List[str]:
        """Validate query-based source"""
        errors = []

        # Check model_name
        if not source.model_name:
            errors.append("model_name is required for related_query source")
            return errors

        # Check model exists
        try:
            model = apps.get_model('bfagent', source.model_name)
        except LookupError:
            errors.append(f"Model '{source.model_name}' not found")
            return errors

        # Check filter_config is provided
        if not source.filter_config:
            errors.append("filter_config is required for related_query source")

        # Validate aggregate_type
        valid_aggregates = ['first', 'last', 'all', 'list', 'count', 'exists']
        if source.aggregate_type not in valid_aggregates:
            errors.append(
                f"Invalid aggregate_type: {source.aggregate_type}. "
                f"Must be one of: {', '.join(valid_aggregates)}"
            )

        return errors

    def _validate_computed_source(self, source) -> List[str]:
        """Validate computed source"""
        errors = []

        # Check function_name is provided
        if not source.function_name:
            errors.append("function_name is required for computed source")

        # Note: We can't validate if function exists here without importing
        # the computed_functions module (circular dependency risk)
        # This will be checked at runtime

        return errors

    def _validate_beat_sheet_source(self, source) -> List[str]:
        """Validate beat sheet source"""
        errors = []

        # Check function_name
        if not source.function_name:
            errors.append("function_name is required for beat_sheet source")

        # Check function_params has beat_type
        if not source.function_params or 'beat_type' not in source.function_params:
            errors.append("function_params must include 'beat_type' for beat_sheet source")

        return errors


class ParamValidator:
    """Validates runtime parameters against schema requirements"""

    def validate(self, schema, params: Dict) -> None:
        """
        Validate that all required parameters are provided.

        Args:
            schema: ContextSchema instance
            params: Runtime parameters dict

        Raises:
            ValidationError: If required parameters are missing
        """
        required_params = self._extract_required_params(schema)
        provided_params = set(params.keys())

        missing = required_params - provided_params

        if missing:
            raise ValidationError(
                f"Missing required parameters for schema '{schema.name}'",
                errors=list(missing)
            )

    def _extract_required_params(self, schema) -> Set[str]:
        """Extract all parameter placeholders from schema sources"""
        required = set()

        for source in schema.get_active_sources():
            # Extract from filter_config
            if source.filter_config:
                placeholders = self._find_placeholders(source.filter_config)
                required.update(placeholders)

            # Extract from function_params
            if source.function_params:
                placeholders = self._find_placeholders(source.function_params)
                required.update(placeholders)

        return required

    def _find_placeholders(self, data) -> Set[str]:
        """
        Recursively find all {placeholder} patterns in data structure.

        Args:
            data: Dict, list, or string to search

        Returns:
            Set of placeholder names (without braces)
        """
        placeholders = set()

        if isinstance(data, dict):
            for value in data.values():
                placeholders.update(self._find_placeholders(value))

        elif isinstance(data, list):
            for item in data:
                placeholders.update(self._find_placeholders(item))

        elif isinstance(data, str):
            # Find all {param_name} patterns
            matches = re.findall(r'\{(\w+)\}', data)
            placeholders.update(matches)

        return placeholders
