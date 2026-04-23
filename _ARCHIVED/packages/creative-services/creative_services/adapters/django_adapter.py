"""
Django ORM Adapters for creative-services.

These adapters allow Django apps (BFAgent, TravelBeat) to use the
creative-services LLM Registry and Usage Tracker with their existing
Django models.

Usage in BFAgent:
    from creative_services.adapters.django_adapter import DjangoLLMRegistry
    
    # Create registry backed by Django Llms model
    registry = DjangoLLMRegistry(model_class=Llms)
    
    # Use with DynamicLLMClient
    client = DynamicLLMClient(registry)
    response = await client.generate("Hello", tier=LLMTier.STANDARD)

Usage in TravelBeat (without Llms model):
    from creative_services.core import DictRegistry, DynamicLLMClient
    
    # Use simple dict registry from env
    registry = DictRegistry.from_env()
    client = DynamicLLMClient(registry)

IMPORTANT: This module does NOT import Django directly to keep
creative-services Django-agnostic. The Django model class is passed
as a parameter.
"""

from typing import Any, Optional, Type
from creative_services.core.llm_registry import LLMEntry, LLMTier, LLMRegistry
from creative_services.core.usage_tracker import UsageRecord, UsageStats, UsageTracker


# Tier mapping for common models
TIER_MAPPING = {
    # OpenAI
    "gpt-3.5-turbo": LLMTier.ECONOMY,
    "gpt-4o-mini": LLMTier.STANDARD,
    "gpt-4o": LLMTier.PREMIUM,
    "gpt-4-turbo": LLMTier.PREMIUM,
    "gpt-4": LLMTier.PREMIUM,
    # Anthropic
    "claude-3-haiku-20240307": LLMTier.ECONOMY,
    "claude-3-5-sonnet-20241022": LLMTier.STANDARD,
    "claude-3-sonnet-20240229": LLMTier.STANDARD,
    "claude-3-opus-20240229": LLMTier.PREMIUM,
    # Groq
    "llama-3.3-70b-versatile": LLMTier.ECONOMY,
    "mixtral-8x7b-32768": LLMTier.ECONOMY,
    # Local
    "llama3.2": LLMTier.LOCAL,
    "mistral": LLMTier.LOCAL,
}


def _model_to_entry(llm_model: Any) -> LLMEntry:
    """Convert Django Llms model instance to LLMEntry."""
    model_name = getattr(llm_model, 'llm_name', '') or getattr(llm_model, 'model', '')
    tier = TIER_MAPPING.get(model_name, LLMTier.STANDARD)
    
    return LLMEntry(
        id=llm_model.id,
        name=llm_model.name,
        provider=llm_model.provider,
        model=model_name,
        tier=tier,
        api_key=getattr(llm_model, 'api_key', None),
        api_endpoint=getattr(llm_model, 'api_endpoint', None),
        max_tokens=getattr(llm_model, 'max_tokens', 4096),
        temperature=getattr(llm_model, 'temperature', 0.7),
        cost_per_1k_input=getattr(llm_model, 'cost_per_1k_tokens', 0.0) / 2,  # Approximate split
        cost_per_1k_output=getattr(llm_model, 'cost_per_1k_tokens', 0.0) / 2,
        is_active=getattr(llm_model, 'is_active', True),
    )


class DjangoLLMRegistry:
    """
    LLM Registry backed by Django ORM.
    
    Works with BFAgent's Llms model or any Django model with compatible fields.
    
    Required model fields:
    - id: int
    - name: str
    - provider: str
    - llm_name or model: str
    - is_active: bool
    
    Optional fields:
    - api_key: str
    - api_endpoint: str
    - max_tokens: int
    - temperature: float
    - cost_per_1k_tokens: float
    """
    
    def __init__(self, model_class: Type[Any]):
        """
        Initialize with Django model class.
        
        Args:
            model_class: Django model class (e.g., Llms from BFAgent)
        """
        self._model_class = model_class
    
    def get_by_id(self, llm_id: int) -> Optional[LLMEntry]:
        """Get LLM by database ID."""
        try:
            llm = self._model_class.objects.get(id=llm_id, is_active=True)
            return _model_to_entry(llm)
        except self._model_class.DoesNotExist:
            return None
    
    def get_by_name(self, name: str) -> Optional[LLMEntry]:
        """Get LLM by name."""
        try:
            llm = self._model_class.objects.get(name=name, is_active=True)
            return _model_to_entry(llm)
        except self._model_class.DoesNotExist:
            return None
    
    def get_by_tier(self, tier: LLMTier) -> Optional[LLMEntry]:
        """Get cheapest active LLM in tier."""
        tier_models = [k for k, v in TIER_MAPPING.items() if v == tier]
        
        # Try to find by llm_name field first
        try:
            llm = self._model_class.objects.filter(
                llm_name__in=tier_models,
                is_active=True
            ).order_by('cost_per_1k_tokens').first()
        except Exception:
            # Fallback: try model field
            llm = self._model_class.objects.filter(
                model__in=tier_models,
                is_active=True
            ).order_by('cost_per_1k_tokens').first()
        
        return _model_to_entry(llm) if llm else None
    
    def get_default(self) -> LLMEntry:
        """Get default LLM (cheapest active, prefer STANDARD tier)."""
        # Try STANDARD tier first
        entry = self.get_by_tier(LLMTier.STANDARD)
        if entry:
            return entry
        
        # Fall back to any active
        llm = self._model_class.objects.filter(
            is_active=True
        ).order_by('cost_per_1k_tokens').first()
        
        if llm:
            return _model_to_entry(llm)
        
        # Ultimate fallback
        import os
        return LLMEntry(
            name="Fallback GPT-4o-mini",
            provider="openai",
            model="gpt-4o-mini",
            tier=LLMTier.STANDARD,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    
    def list_active(self) -> list[LLMEntry]:
        """List all active LLMs."""
        llms = self._model_class.objects.filter(is_active=True)
        return [_model_to_entry(llm) for llm in llms]


class DjangoUsageTracker:
    """
    Usage Tracker backed by Django ORM.
    
    Works with BFAgent's LLMUsageLog model or any Django model with compatible fields.
    
    Required model fields:
    - llm_id or llm: FK to LLM
    - tokens_input or input_tokens: int
    - tokens_output or output_tokens: int
    - cost: Decimal/float
    - created_at: datetime
    
    Optional fields:
    - app_name: str
    - service_name: str
    - latency_ms: int
    - success: bool
    - error_message: str
    """
    
    def __init__(self, model_class: Type[Any], llm_model_class: Optional[Type[Any]] = None):
        """
        Initialize with Django model classes.
        
        Args:
            model_class: Usage log model class (e.g., LLMUsageLog)
            llm_model_class: LLM model class for FK (optional)
        """
        self._model_class = model_class
        self._llm_model_class = llm_model_class
    
    def track(
        self,
        llm_id: int,
        app_name: str,
        service_name: str,
        tokens_input: int,
        tokens_output: int,
        cost: float,
        latency_ms: int,
        success: bool = True,
        error_message: Optional[str] = None,
        llm_name: str = "",
    ) -> UsageRecord:
        """Track a single LLM usage."""
        # Build kwargs based on available fields
        kwargs = {
            'cost': cost,
        }
        
        # Handle LLM reference
        if self._llm_model_class:
            try:
                llm = self._llm_model_class.objects.get(id=llm_id)
                kwargs['llm'] = llm
            except Exception:
                kwargs['llm_id'] = llm_id
        else:
            kwargs['llm_id'] = llm_id
        
        # Handle token fields (different naming conventions)
        if hasattr(self._model_class, 'tokens_input'):
            kwargs['tokens_input'] = tokens_input
            kwargs['tokens_output'] = tokens_output
        else:
            kwargs['input_tokens'] = tokens_input
            kwargs['output_tokens'] = tokens_output
        
        # Optional fields
        for field, value in [
            ('app_name', app_name),
            ('service_name', service_name),
            ('latency_ms', latency_ms),
            ('success', success),
            ('error_message', error_message),
        ]:
            if hasattr(self._model_class, field):
                kwargs[field] = value
        
        record = self._model_class.objects.create(**kwargs)
        
        return UsageRecord(
            id=record.id,
            llm_id=llm_id,
            llm_name=llm_name,
            app_name=app_name,
            service_name=service_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=float(cost),
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            created_at=record.created_at,
        )
    
    def get_stats(
        self,
        app_name: Optional[str] = None,
        service_name: Optional[str] = None,
        llm_id: Optional[int] = None,
        since: Optional[Any] = None,  # datetime
    ) -> UsageStats:
        """Get aggregated usage statistics."""
        from django.db.models import Sum, Avg, Count, Q
        
        queryset = self._model_class.objects.all()
        
        if app_name and hasattr(self._model_class, 'app_name'):
            queryset = queryset.filter(app_name=app_name)
        if service_name and hasattr(self._model_class, 'service_name'):
            queryset = queryset.filter(service_name=service_name)
        if llm_id:
            queryset = queryset.filter(llm_id=llm_id)
        if since:
            queryset = queryset.filter(created_at__gte=since)
        
        # Determine field names
        input_field = 'tokens_input' if hasattr(self._model_class, 'tokens_input') else 'input_tokens'
        output_field = 'tokens_output' if hasattr(self._model_class, 'tokens_output') else 'output_tokens'
        
        agg = queryset.aggregate(
            total=Count('id'),
            total_input=Sum(input_field),
            total_output=Sum(output_field),
            total_cost=Sum('cost'),
            avg_latency=Avg('latency_ms') if hasattr(self._model_class, 'latency_ms') else None,
        )
        
        success_count = 0
        if hasattr(self._model_class, 'success'):
            success_count = queryset.filter(success=True).count()
        else:
            success_count = agg['total'] or 0
        
        return UsageStats(
            total_requests=agg['total'] or 0,
            successful_requests=success_count,
            failed_requests=(agg['total'] or 0) - success_count,
            total_tokens_input=agg['total_input'] or 0,
            total_tokens_output=agg['total_output'] or 0,
            total_cost=float(agg['total_cost'] or 0),
            avg_latency_ms=float(agg['avg_latency'] or 0),
        )
    
    def get_recent(
        self,
        limit: int = 100,
        app_name: Optional[str] = None,
    ) -> list[UsageRecord]:
        """Get recent usage records."""
        queryset = self._model_class.objects.all().order_by('-created_at')
        
        if app_name and hasattr(self._model_class, 'app_name'):
            queryset = queryset.filter(app_name=app_name)
        
        records = []
        for r in queryset[:limit]:
            input_field = 'tokens_input' if hasattr(r, 'tokens_input') else 'input_tokens'
            output_field = 'tokens_output' if hasattr(r, 'tokens_output') else 'output_tokens'
            
            records.append(UsageRecord(
                id=r.id,
                llm_id=getattr(r, 'llm_id', 0),
                tokens_input=getattr(r, input_field, 0),
                tokens_output=getattr(r, output_field, 0),
                cost=float(r.cost),
                latency_ms=getattr(r, 'latency_ms', 0),
                success=getattr(r, 'success', True),
                error_message=getattr(r, 'error_message', None),
                created_at=r.created_at,
            ))
        
        return records
