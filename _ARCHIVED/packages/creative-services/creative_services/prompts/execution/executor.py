"""
Main PromptExecutor for orchestrating prompt executions.

The PromptExecutor is the central component that:
- Loads templates from registry
- Validates and sanitizes variables
- Renders prompts
- Executes LLM calls with retry logic
- Tracks executions with observability
- Handles caching
"""

import time
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, runtime_checkable
from uuid import uuid4

from ..schemas import (
    PromptTemplateSpec,
    PromptExecution,
    ExecutionStatus,
    LLMConfig,
)
from ..exceptions import (
    TemplateNotFoundError,
    ExecutionError,
    LLMError,
    InjectionDetectedError,
    CostLimitError,
    ContextLimitError,
)
from ..registry import TemplateRegistry, InMemoryRegistry
from ..observability import (
    PromptEvent,
    EventType,
    emit_event,
    record_execution,
)
from .cache import PromptCache, InMemoryCache, build_cache_key, hash_llm_config
from .renderer import render_template, TemplateRenderer
from .retry import with_retry, RetryStrategy


@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol for LLM client implementations.
    
    Any LLM client (OpenAI, Anthropic, etc.) must implement this interface.
    """

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> "LLMResponse":
        """
        Generate a response from the LLM.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model name
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse with content and metadata
        """
        ...


class LLMResponse:
    """
    Response from an LLM call.
    
    Provides a consistent interface regardless of provider.
    """

    def __init__(
        self,
        content: str,
        model: str,
        provider: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_dollars: float = 0.0,
        finish_reason: str = "stop",
        raw_response: Any = None,
    ):
        self.content = content
        self.model = model
        self.provider = provider
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.tokens_total = tokens_input + tokens_output
        self.cost_dollars = cost_dollars
        self.finish_reason = finish_reason
        self.raw_response = raw_response


class ExecutionResult:
    """
    Result of a prompt execution.
    
    Contains the response, execution record, and metadata.
    """

    def __init__(
        self,
        content: str,
        execution: PromptExecution,
        from_cache: bool = False,
        llm_response: LLMResponse | None = None,
    ):
        self.content = content
        self.execution = execution
        self.from_cache = from_cache
        self.llm_response = llm_response

    @property
    def success(self) -> bool:
        return self.execution.status == ExecutionStatus.SUCCESS

    @property
    def tokens_total(self) -> int:
        return self.execution.tokens_total

    @property
    def cost_dollars(self) -> float:
        return self.execution.cost_dollars

    @property
    def duration_seconds(self) -> float:
        return self.execution.execution_time_seconds


class PromptExecutor:
    """
    Main executor for prompt templates.
    
    Orchestrates the full execution flow:
    1. Load template from registry
    2. Validate variables
    3. Check cache
    4. Render prompts
    5. Execute LLM call with retry
    6. Track execution
    7. Cache result
    
    Example:
        executor = PromptExecutor(
            registry=registry,
            llm_client=openai_client,
            app_name="my_app",
        )
        
        result = await executor.execute(
            template_key="character.backstory.v1",
            variables={"name": "Alice", "genre": "fantasy"},
        )
        print(result.content)
    """

    def __init__(
        self,
        registry: TemplateRegistry,
        llm_client: LLMClient,
        app_name: str = "unknown",
        cache: PromptCache | None = None,
        renderer: TemplateRenderer | None = None,
        default_llm_config: LLMConfig | None = None,
        cost_limit_dollars: float | None = None,
        on_execution_complete: Callable[[PromptExecution], None] | None = None,
    ):
        """
        Initialize the executor.
        
        Args:
            registry: Template registry to load templates from
            llm_client: LLM client for making API calls
            app_name: Application name for observability
            cache: Optional cache for responses
            renderer: Optional custom renderer
            default_llm_config: Default LLM configuration
            cost_limit_dollars: Optional cost limit per execution
            on_execution_complete: Callback after each execution
        """
        self.registry = registry
        self.llm_client = llm_client
        self.app_name = app_name
        self.cache = cache
        self.renderer = renderer or TemplateRenderer()
        self.default_llm_config = default_llm_config or LLMConfig()
        self.cost_limit_dollars = cost_limit_dollars
        self.on_execution_complete = on_execution_complete

    async def execute(
        self,
        template_key: str,
        variables: dict[str, Any],
        user_id: str | None = None,
        llm_config_override: LLMConfig | None = None,
        use_cache: bool = True,
        cache_ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """
        Execute a prompt template.
        
        Args:
            template_key: Key of template to execute
            variables: Variables for the template
            user_id: Optional user ID for tracking
            llm_config_override: Override LLM configuration
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds
            metadata: Additional metadata to store
            
        Returns:
            ExecutionResult with content and execution record
            
        Raises:
            TemplateNotFoundError: If template not found
            InjectionDetectedError: If injection detected
            ExecutionError: If execution fails
            CostLimitError: If cost limit exceeded
        """
        execution_id = uuid4()
        start_time = time.time()
        
        # Emit start event
        emit_event(PromptEvent(
            event_type=EventType.EXECUTION_STARTED,
            execution_id=execution_id,
            template_key=template_key,
            app_name=self.app_name,
            user_id=user_id,
            data={"variables_count": len(variables)},
        ))

        try:
            # Load template
            template = self.registry.get(template_key)
            if template is None:
                raise TemplateNotFoundError(template_key, registry=self.app_name)

            # Merge LLM config
            llm_config = self._merge_llm_config(template, llm_config_override)

            # Check cache
            template_cache_enabled = getattr(template, 'cache_enabled', True)
            if use_cache and self.cache and template_cache_enabled:
                cache_key = self._build_cache_key(template, variables, llm_config)
                cached_content = self.cache.get(cache_key)
                
                if cached_content is not None:
                    # Cache hit
                    emit_event(PromptEvent(
                        event_type=EventType.CACHE_HIT,
                        execution_id=execution_id,
                        template_key=template_key,
                        app_name=self.app_name,
                    ))
                    
                    execution = self._create_execution(
                        execution_id=execution_id,
                        template=template,
                        variables=variables,
                        llm_config=llm_config,
                        content=cached_content,
                        start_time=start_time,
                        from_cache=True,
                        user_id=user_id,
                        metadata=metadata,
                    )
                    
                    return ExecutionResult(
                        content=cached_content,
                        execution=execution,
                        from_cache=True,
                    )

            # Render prompts
            system_prompt, user_prompt = self.renderer.render(
                template=template,
                variables=variables,
                sanitize=template.sanitize_user_input,
                check_injections=template.check_injection,
            )

            # Check context limits
            self._check_context_limits(system_prompt, user_prompt, llm_config)

            # Execute LLM call with retry
            llm_response = await self._execute_llm_call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_config=llm_config,
                template=template,
                execution_id=execution_id,
            )

            # Check cost limit
            if self.cost_limit_dollars and llm_response.cost_dollars > self.cost_limit_dollars:
                raise CostLimitError(
                    cost=llm_response.cost_dollars,
                    limit=self.cost_limit_dollars,
                    template_key=template_key,
                )

            # Create execution record
            execution = self._create_execution(
                execution_id=execution_id,
                template=template,
                variables=variables,
                llm_config=llm_config,
                content=llm_response.content,
                start_time=start_time,
                from_cache=False,
                user_id=user_id,
                metadata=metadata,
                llm_response=llm_response,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            # Cache result
            cache_enabled = getattr(template, 'cache_enabled', True)
            if use_cache and self.cache and cache_enabled:
                ttl = cache_ttl or getattr(template, 'cache_ttl_seconds', 3600)
                self.cache.set(cache_key, llm_response.content, ttl)
                
                emit_event(PromptEvent(
                    event_type=EventType.CACHE_SET,
                    execution_id=execution_id,
                    template_key=template_key,
                    app_name=self.app_name,
                ))

            # Record metrics
            record_execution(
                template_key=template_key,
                app_name=self.app_name,
                status="success",
                duration_seconds=execution.duration_seconds,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                cost_dollars=llm_response.cost_dollars,
                llm_provider=llm_response.provider,
            )

            # Emit completion event
            emit_event(PromptEvent(
                event_type=EventType.EXECUTION_COMPLETED,
                execution_id=execution_id,
                template_key=template_key,
                app_name=self.app_name,
                duration_ms=(time.time() - start_time) * 1000,
                data={
                    "tokens_total": llm_response.tokens_total,
                    "cost_dollars": llm_response.cost_dollars,
                },
            ))

            # Callback
            if self.on_execution_complete:
                self.on_execution_complete(execution)

            return ExecutionResult(
                content=llm_response.content,
                execution=execution,
                from_cache=False,
                llm_response=llm_response,
            )

        except (TemplateNotFoundError, InjectionDetectedError, CostLimitError, ContextLimitError):
            # Re-raise known errors
            raise

        except Exception as e:
            # Handle unexpected errors
            duration_ms = (time.time() - start_time) * 1000
            
            emit_event(PromptEvent(
                event_type=EventType.EXECUTION_FAILED,
                execution_id=execution_id,
                template_key=template_key,
                app_name=self.app_name,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
                error_message=str(e),
            ))

            record_execution(
                template_key=template_key,
                app_name=self.app_name,
                status="failed",
                duration_seconds=duration_ms / 1000,
                error_type=type(e).__name__,
            )

            raise ExecutionError(
                f"Execution failed for '{template_key}': {e}",
                context={"template_key": template_key, "original_error": type(e).__name__},
            ) from e

    async def _execute_llm_call(
        self,
        system_prompt: str,
        user_prompt: str,
        llm_config: LLMConfig,
        template: PromptTemplateSpec,
        execution_id: Any,
    ) -> LLMResponse:
        """Execute LLM call with retry logic."""
        
        emit_event(PromptEvent(
            event_type=EventType.LLM_REQUEST_STARTED,
            execution_id=execution_id,
            template_key=template.template_key,
            app_name=self.app_name,
            data={"model": llm_config.model, "provider": llm_config.provider},
        ))

        retry_count = 0

        async def on_retry(attempt: int, error: BaseException) -> None:
            nonlocal retry_count
            retry_count = attempt
            emit_event(PromptEvent(
                event_type=EventType.LLM_RETRY,
                execution_id=execution_id,
                template_key=template.template_key,
                app_name=self.app_name,
                data={"attempt": attempt, "error": str(error)},
            ))

        try:
            response = await with_retry(
                self.llm_client.generate,
                config=llm_config.retry if llm_config else None,
                on_retry=on_retry,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
            )

            emit_event(PromptEvent(
                event_type=EventType.LLM_REQUEST_COMPLETED,
                execution_id=execution_id,
                template_key=template.template_key,
                app_name=self.app_name,
                data={
                    "tokens_total": response.tokens_total,
                    "retries": retry_count,
                },
            ))

            return response

        except Exception as e:
            emit_event(PromptEvent(
                event_type=EventType.LLM_REQUEST_FAILED,
                execution_id=execution_id,
                template_key=template.template_key,
                app_name=self.app_name,
                error_type=type(e).__name__,
                error_message=str(e),
            ))
            raise

    def _merge_llm_config(
        self,
        template: PromptTemplateSpec,
        override: LLMConfig | None,
    ) -> LLMConfig:
        """Merge LLM configs: override > template > default."""
        if override:
            return override
        if template.llm_config:
            return template.llm_config
        return self.default_llm_config

    def _build_cache_key(
        self,
        template: PromptTemplateSpec,
        variables: dict[str, Any],
        llm_config: LLMConfig,
    ) -> str:
        """Build cache key for this execution."""
        config_hash = hash_llm_config(
            provider=llm_config.provider,
            model=llm_config.model,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )
        return build_cache_key(template.template_key, variables, config_hash)

    def _check_context_limits(
        self,
        system_prompt: str,
        user_prompt: str,
        llm_config: LLMConfig,
    ) -> None:
        """Check if prompts exceed context limits."""
        # Rough token estimation (4 chars per token)
        estimated_tokens = (len(system_prompt) + len(user_prompt)) // 4
        
        if llm_config.context_limit and estimated_tokens > llm_config.context_limit:
            raise ContextLimitError(
                tokens=estimated_tokens,
                limit=llm_config.context_limit,
            )

    def _create_execution(
        self,
        execution_id: Any,
        template: PromptTemplateSpec,
        variables: dict[str, Any],
        llm_config: LLMConfig,
        content: str,
        start_time: float,
        from_cache: bool,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        llm_response: LLMResponse | None = None,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
    ) -> PromptExecution:
        """Create execution record."""
        duration = time.time() - start_time
        
        return PromptExecution(
            execution_id=execution_id,
            template_key=template.template_key,
            app_name=self.app_name,
            user_id=user_id,
            variables_provided=variables,
            rendered_system_prompt=system_prompt or "",
            rendered_user_prompt=user_prompt or "",
            response_text=content,
            llm_provider=llm_response.provider if llm_response else None,
            llm_model=llm_response.model if llm_response else (llm_config.model if llm_config else None),
            tokens_input=llm_response.tokens_input if llm_response else 0,
            tokens_output=llm_response.tokens_output if llm_response else 0,
            cost_dollars=llm_response.cost_dollars if llm_response else 0.0,
            duration_seconds=duration,
            status=ExecutionStatus.SUCCESS,
            from_cache=from_cache,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )


def create_executor(
    registry: TemplateRegistry | None = None,
    llm_client: LLMClient | None = None,
    app_name: str = "default",
    enable_cache: bool = True,
) -> PromptExecutor:
    """
    Factory function to create a PromptExecutor with sensible defaults.
    
    Args:
        registry: Template registry (creates InMemoryRegistry if not provided)
        llm_client: LLM client (required for actual execution)
        app_name: Application name
        enable_cache: Whether to enable caching
        
    Returns:
        Configured PromptExecutor
    """
    if registry is None:
        registry = InMemoryRegistry()
    
    cache = InMemoryCache() if enable_cache else None
    
    return PromptExecutor(
        registry=registry,
        llm_client=llm_client,
        app_name=app_name,
        cache=cache,
    )
