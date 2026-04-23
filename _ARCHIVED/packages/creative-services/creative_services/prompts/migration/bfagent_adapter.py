"""
BFAgent compatibility adapter.

Converts between BFAgent's PromptTemplate Django model and
the new PromptTemplateSpec Pydantic schema.
"""

from typing import Any
from datetime import datetime, timezone

from ..schemas import (
    PromptTemplateSpec,
    PromptVariable,
    VariableType,
    LLMConfig,
    RetryConfig,
)


class BFAgentTemplateAdapter:
    """
    Adapter for converting BFAgent templates to PromptTemplateSpec.
    
    Usage:
        adapter = BFAgentTemplateAdapter()
        spec = adapter.from_django_model(bfagent_template)
        
        # Or convert back
        data = adapter.to_django_dict(spec)
    """

    # Mapping from BFAgent category to domain_code
    CATEGORY_TO_DOMAIN = {
        "character": "writing",
        "chapter": "writing",
        "world": "writing",
        "plot": "writing",
        "dialogue": "writing",
        "description": "writing",
        "analysis": "writing",
        "revision": "writing",
    }

    def from_django_model(self, template: Any) -> PromptTemplateSpec:
        """
        Convert a BFAgent PromptTemplate Django model to PromptTemplateSpec.
        
        Args:
            template: BFAgent PromptTemplate instance
            
        Returns:
            PromptTemplateSpec
        """
        # Parse variables from required_variables and optional_variables
        variables = self._parse_variables(
            required=getattr(template, "required_variables", []) or [],
            optional=getattr(template, "optional_variables", []) or [],
            defaults=getattr(template, "variable_defaults", {}) or {},
        )

        # Build LLM config from template fields
        llm_config = self._build_llm_config(template)

        # Map category to domain
        category = getattr(template, "category", "general")
        domain_code = self.CATEGORY_TO_DOMAIN.get(category, "general")

        return PromptTemplateSpec(
            template_key=template.template_key,
            domain_code=domain_code,
            name=template.name,
            description=getattr(template, "description", None),
            category=category,
            schema_version=getattr(template, "version", 1),
            system_prompt=template.system_prompt or "",
            user_prompt=template.user_prompt_template or "",
            variables=variables,
            llm_config=llm_config,
            is_active=getattr(template, "is_active", True),
            tags=self._parse_tags(template),
            created_at=getattr(template, "created_at", datetime.now(timezone.utc)),
            updated_at=getattr(template, "updated_at", datetime.now(timezone.utc)),
            metadata={
                "bfagent_id": getattr(template, "id", None),
                "bfagent_category": category,
                "migrated_from": "bfagent",
            },
        )

    def to_django_dict(self, spec: PromptTemplateSpec) -> dict[str, Any]:
        """
        Convert a PromptTemplateSpec to a dict suitable for BFAgent PromptTemplate.
        
        Args:
            spec: PromptTemplateSpec instance
            
        Returns:
            Dict with BFAgent PromptTemplate fields
        """
        # Extract required and optional variables
        required_vars = [v.name for v in spec.variables if v.required]
        optional_vars = [v.name for v in spec.variables if not v.required]
        defaults = spec.get_variable_defaults()

        result = {
            "template_key": spec.template_key,
            "name": spec.name,
            "description": spec.description,
            "category": spec.category or "general",
            "version": spec.schema_version,
            "system_prompt": spec.system_prompt,
            "user_prompt_template": spec.user_prompt,
            "required_variables": required_vars,
            "optional_variables": optional_vars,
            "variable_defaults": defaults,
            "is_active": spec.is_active,
        }

        # Add LLM config fields
        if spec.llm_config:
            result.update({
                "max_tokens": spec.llm_config.max_tokens,
                "temperature": spec.llm_config.temperature,
                "top_p": spec.llm_config.top_p,
            })

        return result

    def _parse_variables(
        self,
        required: list[str],
        optional: list[str],
        defaults: dict[str, Any],
    ) -> list[PromptVariable]:
        """Parse BFAgent variable lists into PromptVariable objects."""
        variables = []

        # Required variables
        for name in required:
            variables.append(PromptVariable(
                name=name,
                var_type=VariableType.STRING,
                required=True,
                default=defaults.get(name),
                description=f"Required variable: {name}",
            ))

        # Optional variables
        for name in optional:
            variables.append(PromptVariable(
                name=name,
                var_type=VariableType.STRING,
                required=False,
                default=defaults.get(name),
                description=f"Optional variable: {name}",
            ))

        return variables

    def _build_llm_config(self, template: Any) -> LLMConfig | None:
        """Build LLMConfig from BFAgent template fields."""
        # Check if template has LLM-related fields
        max_tokens = getattr(template, "max_tokens", None)
        temperature = getattr(template, "temperature", None)
        
        if max_tokens is None and temperature is None:
            return None

        # Get preferred LLM info if available
        preferred_llm = getattr(template, "preferred_llm", None)
        provider = "openai"
        model = "gpt-4"
        
        if preferred_llm:
            provider = getattr(preferred_llm, "provider", "openai")
            model = getattr(preferred_llm, "llm_name", "gpt-4")

        return LLMConfig(
            provider=provider,
            model=model,
            max_tokens=max_tokens or 1000,
            temperature=temperature or 0.7,
            top_p=getattr(template, "top_p", 1.0),
        )

    def _parse_tags(self, template: Any) -> list[str]:
        """Extract tags from template."""
        tags = []
        
        # Add category as tag
        category = getattr(template, "category", None)
        if category:
            tags.append(category)
        
        # Add any explicit tags
        explicit_tags = getattr(template, "tags", None)
        if explicit_tags:
            if isinstance(explicit_tags, str):
                tags.extend(explicit_tags.split(","))
            elif isinstance(explicit_tags, list):
                tags.extend(explicit_tags)
        
        return [t.strip().lower() for t in tags if t]


def convert_bfagent_template(template: Any) -> PromptTemplateSpec:
    """
    Convenience function to convert a BFAgent template.
    
    Args:
        template: BFAgent PromptTemplate instance
        
    Returns:
        PromptTemplateSpec
    """
    adapter = BFAgentTemplateAdapter()
    return adapter.from_django_model(template)


def convert_to_bfagent_format(spec: PromptTemplateSpec) -> dict[str, Any]:
    """
    Convenience function to convert to BFAgent format.
    
    Args:
        spec: PromptTemplateSpec instance
        
    Returns:
        Dict suitable for BFAgent PromptTemplate
    """
    adapter = BFAgentTemplateAdapter()
    return adapter.to_django_dict(spec)
