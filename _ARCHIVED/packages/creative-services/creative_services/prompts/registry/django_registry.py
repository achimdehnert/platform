"""
Django ORM-based template registry.

Provides database-backed storage for prompt templates.
This module is designed to be used with Django but doesn't import Django directly,
allowing the creative-services package to remain Django-agnostic.

Usage in Django project:
    from creative_services.prompts.registry import DjangoRegistry
    
    # With a Django model
    registry = DjangoRegistry(model=PromptTemplate)
    
    # Or with custom adapter
    registry = DjangoRegistry(adapter=MyCustomAdapter())
"""

from typing import Any, Protocol, runtime_checkable
from datetime import datetime

from ..schemas import PromptTemplateSpec, PromptVariable, VariableType, LLMConfig
from ..exceptions import TemplateNotFoundError, TemplateValidationError


@runtime_checkable
class DjangoModelAdapter(Protocol):
    """
    Protocol for adapting Django models to PromptTemplateSpec.
    
    Implement this protocol to connect any Django model to the registry.
    """

    def to_spec(self, instance: Any) -> PromptTemplateSpec:
        """Convert Django model instance to PromptTemplateSpec."""
        ...

    def from_spec(self, spec: PromptTemplateSpec) -> dict[str, Any]:
        """Convert PromptTemplateSpec to dict for Django model creation/update."""
        ...

    def get_queryset(self) -> Any:
        """Get the base queryset for the model."""
        ...

    def get_by_key(self, template_key: str) -> Any | None:
        """Get model instance by template_key."""
        ...

    def save_instance(self, data: dict[str, Any], template_key: str | None = None) -> Any:
        """Create or update model instance."""
        ...

    def delete_instance(self, template_key: str) -> bool:
        """Delete model instance by template_key."""
        ...


class GenericDjangoAdapter:
    """
    Generic adapter for Django models with standard field names.
    
    Expects the Django model to have these fields:
    - template_key: CharField (unique)
    - name: CharField
    - description: TextField (optional)
    - system_prompt: TextField
    - user_prompt_template: TextField (maps to user_prompt)
    - category: CharField (optional)
    - is_active: BooleanField
    - required_variables: JSONField (list of strings)
    - optional_variables: JSONField (list of strings)
    - variable_defaults: JSONField (dict)
    - max_tokens: IntegerField (optional)
    - temperature: FloatField (optional)
    - created_at: DateTimeField
    - updated_at: DateTimeField
    
    Example:
        from myapp.models import PromptTemplate
        adapter = GenericDjangoAdapter(PromptTemplate)
        registry = DjangoRegistry(adapter=adapter)
    """

    def __init__(self, model_class: Any, domain_code: str = "default"):
        """
        Initialize adapter.
        
        Args:
            model_class: Django model class
            domain_code: Default domain code for templates
        """
        self._model = model_class
        self._domain_code = domain_code

    def to_spec(self, instance: Any) -> PromptTemplateSpec:
        """Convert Django model to PromptTemplateSpec."""
        # Parse variables
        variables = []
        
        required = getattr(instance, "required_variables", []) or []
        optional = getattr(instance, "optional_variables", []) or []
        defaults = getattr(instance, "variable_defaults", {}) or {}
        
        for name in required:
            variables.append(PromptVariable(
                name=name,
                var_type=VariableType.STRING,
                required=True,
            ))
        
        for name in optional:
            variables.append(PromptVariable(
                name=name,
                var_type=VariableType.STRING,
                required=False,
                default=defaults.get(name),
            ))

        # Build LLM config if fields exist
        llm_config = None
        max_tokens = getattr(instance, "max_tokens", None)
        temperature = getattr(instance, "temperature", None)
        
        if max_tokens or temperature:
            llm_config = LLMConfig(
                max_tokens=max_tokens or 1000,
                temperature=temperature or 0.7,
            )

        # Get domain code
        domain_code = getattr(instance, "domain_code", None) or self._domain_code

        return PromptTemplateSpec(
            template_key=instance.template_key,
            domain_code=domain_code,
            name=instance.name,
            description=getattr(instance, "description", None),
            category=getattr(instance, "category", None),
            system_prompt=instance.system_prompt or "",
            user_prompt=getattr(instance, "user_prompt_template", "") or getattr(instance, "user_prompt", ""),
            variables=variables,
            llm_config=llm_config,
            is_active=getattr(instance, "is_active", True),
            tags=self._parse_tags(instance),
            created_at=getattr(instance, "created_at", datetime.now()),
            updated_at=getattr(instance, "updated_at", datetime.now()),
        )

    def from_spec(self, spec: PromptTemplateSpec) -> dict[str, Any]:
        """Convert PromptTemplateSpec to dict for model creation."""
        required_vars = [v.name for v in spec.variables if v.required]
        optional_vars = [v.name for v in spec.variables if not v.required]
        defaults = spec.get_variable_defaults()

        data = {
            "template_key": spec.template_key,
            "name": spec.name,
            "description": spec.description,
            "category": spec.category,
            "system_prompt": spec.system_prompt,
            "user_prompt_template": spec.user_prompt,
            "required_variables": required_vars,
            "optional_variables": optional_vars,
            "variable_defaults": defaults,
            "is_active": spec.is_active,
        }

        if spec.llm_config:
            data["max_tokens"] = spec.llm_config.max_tokens
            data["temperature"] = spec.llm_config.temperature

        return data

    def get_queryset(self) -> Any:
        """Get base queryset."""
        return self._model.objects.all()

    def get_by_key(self, template_key: str) -> Any | None:
        """Get instance by template_key."""
        try:
            return self._model.objects.get(template_key=template_key)
        except self._model.DoesNotExist:
            return None

    def save_instance(self, data: dict[str, Any], template_key: str | None = None) -> Any:
        """Create or update instance."""
        key = template_key or data.get("template_key")
        
        try:
            instance = self._model.objects.get(template_key=key)
            for field, value in data.items():
                if field != "template_key":
                    setattr(instance, field, value)
            instance.save()
        except self._model.DoesNotExist:
            instance = self._model.objects.create(**data)
        
        return instance

    def delete_instance(self, template_key: str) -> bool:
        """Delete instance by template_key."""
        try:
            instance = self._model.objects.get(template_key=template_key)
            instance.delete()
            return True
        except self._model.DoesNotExist:
            return False

    def _parse_tags(self, instance: Any) -> list[str]:
        """Parse tags from instance."""
        tags = []
        
        category = getattr(instance, "category", None)
        if category:
            tags.append(category.lower())
        
        explicit_tags = getattr(instance, "tags", None)
        if explicit_tags:
            if isinstance(explicit_tags, str):
                tags.extend(t.strip().lower() for t in explicit_tags.split(","))
            elif isinstance(explicit_tags, list):
                tags.extend(t.lower() for t in explicit_tags)
        
        return tags


class DjangoRegistry:
    """
    Django ORM-based template registry.
    
    Provides database-backed storage with full CRUD operations.
    Uses an adapter pattern to support different Django model structures.
    
    Example:
        # With generic adapter
        from myapp.models import PromptTemplate
        registry = DjangoRegistry.from_model(PromptTemplate)
        
        # With custom adapter
        registry = DjangoRegistry(adapter=MyCustomAdapter())
        
        # Usage
        template = registry.get("my.template.v1")
        registry.save(new_template)
    """

    def __init__(self, adapter: DjangoModelAdapter):
        """
        Initialize with adapter.
        
        Args:
            adapter: Adapter implementing DjangoModelAdapter protocol
        """
        self._adapter = adapter

    @classmethod
    def from_model(
        cls,
        model_class: Any,
        domain_code: str = "default",
    ) -> "DjangoRegistry":
        """
        Create registry from Django model class.
        
        Args:
            model_class: Django model class
            domain_code: Default domain code
            
        Returns:
            Configured DjangoRegistry
        """
        adapter = GenericDjangoAdapter(model_class, domain_code)
        return cls(adapter)

    def get(self, template_key: str) -> PromptTemplateSpec | None:
        """Get template by key."""
        instance = self._adapter.get_by_key(template_key)
        if instance is None:
            return None
        return self._adapter.to_spec(instance)

    def get_or_raise(self, template_key: str) -> PromptTemplateSpec:
        """Get template or raise TemplateNotFoundError."""
        template = self.get(template_key)
        if template is None:
            raise TemplateNotFoundError(template_key, registry="django")
        return template

    def exists(self, template_key: str) -> bool:
        """Check if template exists."""
        return self._adapter.get_by_key(template_key) is not None

    def save(self, template: PromptTemplateSpec) -> None:
        """Save template to database."""
        data = self._adapter.from_spec(template)
        self._adapter.save_instance(data, template.template_key)

    def delete(self, template_key: str) -> bool:
        """Delete template from database."""
        return self._adapter.delete_instance(template_key)

    def list_keys(self, domain_code: str | None = None) -> list[str]:
        """List all template keys."""
        qs = self._adapter.get_queryset()
        
        if domain_code:
            # Try to filter by domain_code if field exists
            try:
                qs = qs.filter(domain_code=domain_code)
            except Exception:
                pass
        
        return list(qs.values_list("template_key", flat=True))

    def list_by_domain(self, domain_code: str) -> list[PromptTemplateSpec]:
        """Get all templates for a domain."""
        qs = self._adapter.get_queryset()
        
        try:
            qs = qs.filter(domain_code=domain_code)
        except Exception:
            # domain_code field might not exist
            pass
        
        return [self._adapter.to_spec(instance) for instance in qs]

    def search(
        self,
        query: str | None = None,
        domain_code: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        active_only: bool = True,
    ) -> list[PromptTemplateSpec]:
        """Search templates with filters."""
        qs = self._adapter.get_queryset()

        if active_only:
            try:
                qs = qs.filter(is_active=True)
            except Exception:
                pass

        if domain_code:
            try:
                qs = qs.filter(domain_code=domain_code)
            except Exception:
                pass

        if category:
            try:
                qs = qs.filter(category=category)
            except Exception:
                pass

        if query:
            try:
                from django.db.models import Q
                qs = qs.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                )
            except Exception:
                pass

        results = [self._adapter.to_spec(instance) for instance in qs]

        # Filter by tags in Python (JSONField filtering varies by DB)
        if tags:
            tag_set = set(t.lower() for t in tags)
            results = [
                t for t in results
                if tag_set & set(t.tags)
            ]

        return results

    def count(self) -> int:
        """Get total number of templates."""
        return self._adapter.get_queryset().count()

    def bulk_save(self, templates: list[PromptTemplateSpec]) -> int:
        """
        Save multiple templates.
        
        Returns:
            Number of templates saved
        """
        count = 0
        for template in templates:
            try:
                self.save(template)
                count += 1
            except Exception:
                pass
        return count


class AsyncDjangoRegistry:
    """
    Async version of DjangoRegistry for use with Django async views.
    
    Uses Django's async ORM methods (aget, acreate, etc.).
    """

    def __init__(self, adapter: DjangoModelAdapter):
        """Initialize with adapter."""
        self._adapter = adapter
        self._sync_registry = DjangoRegistry(adapter)

    @classmethod
    def from_model(
        cls,
        model_class: Any,
        domain_code: str = "default",
    ) -> "AsyncDjangoRegistry":
        """Create async registry from Django model class."""
        adapter = GenericDjangoAdapter(model_class, domain_code)
        return cls(adapter)

    async def get(self, template_key: str) -> PromptTemplateSpec | None:
        """Get template by key (async)."""
        try:
            instance = await self._adapter.get_queryset().aget(template_key=template_key)
            return self._adapter.to_spec(instance)
        except Exception:
            return None

    async def get_or_raise(self, template_key: str) -> PromptTemplateSpec:
        """Get template or raise (async)."""
        template = await self.get(template_key)
        if template is None:
            raise TemplateNotFoundError(template_key, registry="django_async")
        return template

    async def exists(self, template_key: str) -> bool:
        """Check if template exists (async)."""
        return await self._adapter.get_queryset().filter(
            template_key=template_key
        ).aexists()

    async def save(self, template: PromptTemplateSpec) -> None:
        """Save template (async)."""
        data = self._adapter.from_spec(template)
        qs = self._adapter.get_queryset()
        
        try:
            instance = await qs.aget(template_key=template.template_key)
            for field, value in data.items():
                if field != "template_key":
                    setattr(instance, field, value)
            await instance.asave()
        except Exception:
            await qs.model.objects.acreate(**data)

    async def delete(self, template_key: str) -> bool:
        """Delete template (async)."""
        try:
            instance = await self._adapter.get_queryset().aget(
                template_key=template_key
            )
            await instance.adelete()
            return True
        except Exception:
            return False

    async def list_keys(self, domain_code: str | None = None) -> list[str]:
        """List template keys (async)."""
        qs = self._adapter.get_queryset()
        
        if domain_code:
            try:
                qs = qs.filter(domain_code=domain_code)
            except Exception:
                pass
        
        keys = []
        async for instance in qs:
            keys.append(instance.template_key)
        return keys

    async def search(
        self,
        query: str | None = None,
        active_only: bool = True,
    ) -> list[PromptTemplateSpec]:
        """Search templates (async)."""
        qs = self._adapter.get_queryset()

        if active_only:
            try:
                qs = qs.filter(is_active=True)
            except Exception:
                pass

        if query:
            try:
                from django.db.models import Q
                qs = qs.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                )
            except Exception:
                pass

        results = []
        async for instance in qs:
            results.append(self._adapter.to_spec(instance))
        
        return results
