"""
BFAgent integration for the Prompt Template System.

Provides adapters to use BFAgent's existing PromptTemplate model
and LLM infrastructure with the new prompt system.

Usage in BFAgent:
    from creative_services.prompts.integration import (
        BFAgentRegistry,
        BFAgentLLMClient,
        create_bfagent_executor,
    )
    
    # Create executor with BFAgent's infrastructure
    executor = create_bfagent_executor()
    
    # Execute a template
    result = await executor.execute(
        template_key="character.backstory.v1",
        variables={"name": "Alice", "genre": "fantasy"},
    )
"""

from typing import Any, Callable
from datetime import datetime, timezone

from ..schemas import PromptTemplateSpec, PromptVariable, VariableType, LLMConfig
from ..registry import DjangoRegistry, GenericDjangoAdapter
from ..execution import PromptExecutor, LLMResponse, InMemoryCache
from ..exceptions import LLMError


class BFAgentModelAdapter(GenericDjangoAdapter):
    """
    Adapter specifically for BFAgent's PromptTemplate model.
    
    Handles BFAgent-specific field mappings and conventions.
    """

    # BFAgent category to domain mapping
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

    def __init__(self, model_class: Any = None):
        """
        Initialize adapter.
        
        Args:
            model_class: BFAgent PromptTemplate model (lazy import if None)
        """
        if model_class is None:
            # Lazy import to avoid Django dependency at module level
            try:
                from apps.bfagent.models import PromptTemplate
                model_class = PromptTemplate
            except ImportError:
                raise ImportError(
                    "Could not import BFAgent PromptTemplate model. "
                    "Make sure you're running within the BFAgent Django project."
                )
        
        super().__init__(model_class, domain_code="writing")

    def to_spec(self, instance: Any) -> PromptTemplateSpec:
        """Convert BFAgent PromptTemplate to PromptTemplateSpec."""
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

        # Build LLM config from BFAgent fields
        llm_config = self._build_llm_config(instance)

        # Map category to domain
        category = getattr(instance, "category", "general")
        domain_code = self.CATEGORY_TO_DOMAIN.get(category, "writing")

        return PromptTemplateSpec(
            template_key=instance.template_key,
            domain_code=domain_code,
            name=instance.name,
            description=getattr(instance, "description", None),
            category=category,
            schema_version=getattr(instance, "version", 1),
            system_prompt=instance.system_prompt or "",
            user_prompt=getattr(instance, "user_prompt_template", "") or "",
            variables=variables,
            llm_config=llm_config,
            is_active=getattr(instance, "is_active", True),
            tags=self._parse_tags(instance),
            created_at=getattr(instance, "created_at", datetime.now(timezone.utc)),
            updated_at=getattr(instance, "updated_at", datetime.now(timezone.utc)),
        )

    def _build_llm_config(self, instance: Any) -> LLMConfig | None:
        """Build LLMConfig from BFAgent template fields."""
        max_tokens = getattr(instance, "max_tokens", None)
        temperature = getattr(instance, "temperature", None)
        
        if max_tokens is None and temperature is None:
            return None

        # Get preferred LLM info
        preferred_llm = getattr(instance, "preferred_llm", None)
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
            top_p=getattr(instance, "top_p", 1.0),
        )


class BFAgentRegistry(DjangoRegistry):
    """
    Registry using BFAgent's PromptTemplate model.
    
    Example:
        registry = BFAgentRegistry()
        template = registry.get("character.backstory.v1")
    """

    def __init__(self, model_class: Any = None):
        """
        Initialize BFAgent registry.
        
        Args:
            model_class: Optional PromptTemplate model class
        """
        adapter = BFAgentModelAdapter(model_class)
        super().__init__(adapter)


class BFAgentLLMClient:
    """
    LLM client using BFAgent's generate_text function.
    
    Wraps BFAgent's existing LLM infrastructure to work with PromptExecutor.
    
    Example:
        client = BFAgentLLMClient()
        response = await client.generate(
            system_prompt="You are helpful.",
            user_prompt="Hello!",
            model="gpt-4",
        )
    """

    def __init__(
        self,
        generate_func: Callable | None = None,
        default_llm_id: int | None = None,
    ):
        """
        Initialize client.
        
        Args:
            generate_func: Custom generate function (uses BFAgent's if None)
            default_llm_id: Default LLM ID to use
        """
        self._generate_func = generate_func
        self._default_llm_id = default_llm_id
        self._llm_cache: dict[str, Any] = {}

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate response using BFAgent's LLM infrastructure.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model name
            temperature: Temperature
            max_tokens: Max tokens
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with content and metadata
        """
        # Get or import generate function
        generate_func = self._get_generate_func()
        
        # Get LLM configuration
        llm = self._get_llm(model, kwargs.get("provider", "openai"))
        
        # Build request
        try:
            from apps.bfagent.services.llm_client import LlmRequest
            
            request = LlmRequest(
                provider=llm.provider if llm else "openai",
                api_endpoint=llm.api_endpoint if llm else None,
                api_key=llm.api_key if llm else None,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            # Execute (sync function, run in thread)
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, generate_func, request)
            
        except ImportError:
            # Fallback: direct call without LlmRequest
            result = await self._fallback_generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Parse result
        if not result.get("ok", False):
            raise LLMError(
                message=result.get("error", "Unknown error"),
                provider=llm.provider if llm else "unknown",
                retryable=True,
            )

        # Extract token counts (estimate if not provided)
        text = result.get("text", "")
        raw = result.get("raw", {})
        
        tokens_input = 0
        tokens_output = 0
        
        if isinstance(raw, dict):
            usage = raw.get("usage", {})
            tokens_input = usage.get("prompt_tokens", len(system_prompt + user_prompt) // 4)
            tokens_output = usage.get("completion_tokens", len(text) // 4)

        # Calculate cost (rough estimate)
        cost = self._estimate_cost(model, tokens_input, tokens_output)

        return LLMResponse(
            content=text,
            model=model,
            provider=llm.provider if llm else "openai",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_dollars=cost,
            raw_response=raw,
        )

    def _get_generate_func(self) -> Callable:
        """Get the generate function."""
        if self._generate_func:
            return self._generate_func
        
        try:
            from apps.bfagent.services.llm_client import generate_text
            return generate_text
        except ImportError:
            raise ImportError(
                "Could not import BFAgent generate_text. "
                "Make sure you're running within the BFAgent Django project."
            )

    def _get_llm(self, model: str, provider: str) -> Any:
        """Get LLM configuration from database."""
        cache_key = f"{provider}:{model}"
        
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        
        try:
            from apps.bfagent.models import Llms
            
            # Try to find matching LLM
            llm = Llms.objects.filter(
                llm_name=model,
                provider=provider,
                is_active=True,
            ).first()
            
            if llm is None and self._default_llm_id:
                llm = Llms.objects.filter(id=self._default_llm_id).first()
            
            if llm is None:
                llm = Llms.objects.filter(is_active=True).first()
            
            self._llm_cache[cache_key] = llm
            return llm
            
        except ImportError:
            return None

    async def _fallback_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Fallback generation without BFAgent infrastructure."""
        # Try OpenAI directly
        try:
            import openai
            
            client = openai.AsyncOpenAI()
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return {
                "ok": True,
                "text": response.choices[0].message.content,
                "raw": response.model_dump(),
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def _estimate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Estimate cost based on model and tokens."""
        # Rough pricing per 1K tokens (as of 2024)
        pricing = {
            "gpt-4": (0.03, 0.06),
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-4o": (0.005, 0.015),
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "claude-3-opus": (0.015, 0.075),
            "claude-3-sonnet": (0.003, 0.015),
        }
        
        input_rate, output_rate = pricing.get(model, (0.01, 0.03))
        
        return (tokens_input / 1000 * input_rate) + (tokens_output / 1000 * output_rate)


def create_bfagent_executor(
    app_name: str = "bfagent",
    enable_cache: bool = True,
    cache_ttl: int = 3600,
) -> PromptExecutor:
    """
    Create a PromptExecutor configured for BFAgent.
    
    Args:
        app_name: Application name for observability
        enable_cache: Whether to enable response caching
        cache_ttl: Cache TTL in seconds
        
    Returns:
        Configured PromptExecutor
        
    Example:
        executor = create_bfagent_executor()
        
        result = await executor.execute(
            template_key="character.backstory.v1",
            variables={"name": "Alice"},
        )
        print(result.content)
    """
    registry = BFAgentRegistry()
    llm_client = BFAgentLLMClient()
    cache = InMemoryCache(default_ttl=cache_ttl) if enable_cache else None
    
    return PromptExecutor(
        registry=registry,
        llm_client=llm_client,
        app_name=app_name,
        cache=cache,
    )
