# Story Engine - Error Handling Strategy

> **Focus**: Robust Error Management, Recovery Patterns, Production Resilience  
> **Status**: Production Planning  
> **Updated**: 2025-11-09

---

## 📋 Table of Contents

1. [Error Classification](#error-classification)
2. [Error Boundaries](#error-boundaries)
3. [Retry Strategies](#retry-strategies)
4. [Fallback Mechanisms](#fallback-mechanisms)
5. [Error Recovery Patterns](#error-recovery-patterns)
6. [Monitoring & Alerting](#monitoring--alerting)

---

## 🎯 Error Classification

### Error Hierarchy

```python
# apps/story_engine/exceptions.py
class StoryEngineError(Exception):
    """Base exception for all Story Engine errors"""
    
    def __init__(self, message: str, context: dict = None):
        super().__init__(message)
        self.context = context or {}
        self.timestamp = datetime.now()

# ============ Retryable Errors ============

class RetryableError(StoryEngineError):
    """Errors that should trigger automatic retry"""
    pass

class RateLimitError(RetryableError):
    """API rate limit reached"""
    
    def __init__(self, retry_after: int, message: str = None):
        super().__init__(
            message or f"Rate limit reached. Retry after {retry_after}s",
            context={'retry_after': retry_after}
        )
        self.retry_after = retry_after

class TemporaryServiceError(RetryableError):
    """Temporary service unavailability (502, 503, 504)"""
    pass

class NetworkError(RetryableError):
    """Network connectivity issues"""
    pass

# ============ Fatal Errors ============

class FatalError(StoryEngineError):
    """Errors that should stop the workflow immediately"""
    pass

class InvalidStateError(FatalError):
    """LangGraph state validation failed"""
    pass

class ConfigurationError(FatalError):
    """Invalid configuration detected"""
    pass

class DatabaseError(FatalError):
    """Critical database errors"""
    pass

class AuthenticationError(FatalError):
    """API authentication failed"""
    pass

# ============ Validation Errors ============

class ValidationError(StoryEngineError):
    """Content validation failures"""
    
    def __init__(self, errors: List[Dict], message: str = None):
        super().__init__(
            message or f"Validation failed with {len(errors)} errors",
            context={'errors': errors}
        )
        self.errors = errors

class ConsistencyError(ValidationError):
    """Content inconsistent with story bible"""
    pass

class QualityError(ValidationError):
    """Content quality below threshold"""
    pass

# ============ Agent Errors ============

class AgentError(StoryEngineError):
    """Base class for agent-specific errors"""
    
    def __init__(self, agent_name: str, message: str, context: dict = None):
        context = context or {}
        context['agent_name'] = agent_name
        super().__init__(message, context)
        self.agent_name = agent_name

class AgentTimeoutError(AgentError, RetryableError):
    """Agent execution timeout"""
    pass

class AgentOutputError(AgentError):
    """Agent produced invalid output"""
    pass
```

---

## 🛡️ Error Boundaries

### Three-Tier Error Handling

```
Tier 1: Agent Level       → Catch & Retry LLM errors
Tier 2: Workflow Level    → Catch & Route agent errors
Tier 3: Handler Level     → Catch & Report to UI
```

### Tier 1: Agent Level

```python
# apps/story_engine/agents/base_agent.py
from typing import TypeVar, Callable
import asyncio
import structlog

logger = structlog.get_logger()

T = TypeVar('T')

class BaseStoryAgent:
    """Base agent with built-in error handling"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.agent_name = self.__class__.__name__
    
    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function with exponential backoff retry.
        
        Handles:
        - Rate limits
        - Temporary service errors
        - Network issues
        """
        
        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(
                        "retry_succeeded",
                        agent=self.agent_name,
                        attempt=attempt + 1
                    )
                
                return result
                
            except RateLimitError as e:
                # Respect rate limit
                wait_time = e.retry_after
                logger.warning(
                    "rate_limited",
                    agent=self.agent_name,
                    wait_seconds=wait_time,
                    attempt=attempt + 1
                )
                await asyncio.sleep(wait_time)
                
            except TemporaryServiceError as e:
                # Exponential backoff: 2^attempt seconds
                wait_time = 2 ** attempt
                logger.warning(
                    "temporary_error",
                    agent=self.agent_name,
                    wait_seconds=wait_time,
                    attempt=attempt + 1,
                    error=str(e)
                )
                await asyncio.sleep(wait_time)
                
            except NetworkError as e:
                # Linear backoff for network issues
                wait_time = 5 * (attempt + 1)
                logger.warning(
                    "network_error",
                    agent=self.agent_name,
                    wait_seconds=wait_time,
                    attempt=attempt + 1
                )
                await asyncio.sleep(wait_time)
                
            except FatalError:
                # Don't retry fatal errors
                logger.error(
                    "fatal_error_in_agent",
                    agent=self.agent_name,
                    exc_info=True
                )
                raise
        
        # All retries exhausted
        raise AgentError(
            self.agent_name,
            f"Failed after {self.max_retries} attempts"
        )
    
    async def safe_llm_call(self, prompt: str, **kwargs) -> str:
        """
        Wrapper for LLM calls with automatic error handling.
        
        Converts LLM-specific errors to our error hierarchy.
        """
        
        async def _call():
            try:
                response = await self.llm.ainvoke(prompt, **kwargs)
                return response.content
                
            except Exception as e:
                # Map LLM errors to our error types
                if "rate_limit" in str(e).lower():
                    # Extract retry_after if available
                    retry_after = self._extract_retry_after(e)
                    raise RateLimitError(retry_after)
                
                elif any(code in str(e) for code in ['502', '503', '504']):
                    raise TemporaryServiceError(str(e))
                
                elif "timeout" in str(e).lower():
                    raise AgentTimeoutError(self.agent_name, str(e))
                
                elif "authentication" in str(e).lower():
                    raise AuthenticationError(str(e))
                
                else:
                    # Unknown error - log and re-raise
                    logger.error(
                        "unknown_llm_error",
                        agent=self.agent_name,
                        error=str(e),
                        exc_info=True
                    )
                    raise AgentError(self.agent_name, str(e)) from e
        
        return await self.execute_with_retry(_call)
```

### Tier 2: Workflow Level

```python
# apps/story_engine/workflows/chapter_workflow.py
from apps.story_engine.state import ChapterState
from apps.story_engine.exceptions import *
import structlog

logger = structlog.get_logger()

class ChapterWorkflow:
    """Workflow with agent error handling"""
    
    def __init__(self):
        self.max_agent_failures = 3
        self.agent_failure_count = {}
    
    async def safe_agent_call(
        self,
        agent_name: str,
        agent_func: Callable,
        state: ChapterState
    ) -> ChapterState:
        """
        Wrap agent calls with workflow-level error handling.
        
        Handles:
        - Agent failures (with retry)
        - State validation
        - Graceful degradation
        """
        
        try:
            # Execute agent
            result_state = await agent_func(state)
            
            # Validate output state
            if not self._validate_state(result_state):
                raise InvalidStateError(
                    f"Agent {agent_name} produced invalid state"
                )
            
            # Reset failure count on success
            self.agent_failure_count[agent_name] = 0
            
            return result_state
            
        except AgentError as e:
            # Track failures per agent
            failures = self.agent_failure_count.get(agent_name, 0) + 1
            self.agent_failure_count[agent_name] = failures
            
            logger.error(
                "agent_failed_in_workflow",
                agent=agent_name,
                failures=failures,
                error=str(e)
            )
            
            # Check if we should give up
            if failures >= self.max_agent_failures:
                raise FatalError(
                    f"Agent {agent_name} failed {failures} times"
                ) from e
            
            # Try fallback strategy
            return await self._handle_agent_failure(
                agent_name, state, e
            )
    
    async def _handle_agent_failure(
        self,
        agent_name: str,
        state: ChapterState,
        error: AgentError
    ) -> ChapterState:
        """
        Fallback strategies for agent failures.
        
        Options:
        1. Use simpler prompt
        2. Switch to fallback model
        3. Use cached result
        4. Skip optional steps
        """
        
        if agent_name == "writer":
            # Writer is critical - try fallback model
            logger.info(
                "using_fallback_model",
                agent=agent_name,
                original_error=str(error)
            )
            
            fallback_writer = WriterAgent(model="gpt-4-turbo")
            return await fallback_writer.write_prose(state)
        
        elif agent_name == "editor":
            # Editor is optional - use unedited draft
            logger.warning(
                "skipping_optional_agent",
                agent=agent_name
            )
            
            state.final_text = state.draft
            state.quality_score = 0.6  # Lower score for unedited
            return state
        
        else:
            # No fallback available
            raise error
```

### Tier 3: Handler Level

```python
# apps/bfagent/handlers/story_handlers.py
from apps.story_engine.exceptions import *
from django.db import transaction
import structlog

logger = structlog.get_logger()

class ChapterGenerationHandler:
    """Handler with comprehensive error management"""
    
    async def generate_chapter(
        self,
        beat_id: int
    ) -> Dict[str, Any]:
        """
        Generate chapter with error reporting.
        
        Returns:
            Success: {'status': 'success', 'chapter': Chapter}
            Failure: {'status': 'error', 'error': ErrorReport}
        """
        
        try:
            # Normal execution path
            chapter = await self._generate(beat_id)
            
            return {
                'status': 'success',
                'chapter': chapter
            }
            
        except ValidationError as e:
            # Validation failures - not critical
            logger.warning(
                "validation_failed",
                beat_id=beat_id,
                errors=e.errors
            )
            
            # Save partial result for review
            chapter = await self._save_partial_chapter(
                beat_id, e.context
            )
            
            return {
                'status': 'validation_error',
                'chapter': chapter,
                'errors': e.errors,
                'message': 'Content needs manual review'
            }
        
        except FatalError as e:
            # Fatal errors - log and notify
            logger.error(
                "generation_failed",
                beat_id=beat_id,
                error=str(e),
                exc_info=True
            )
            
            # Send alert
            await self._send_alert(
                severity='critical',
                message=f"Chapter generation failed: {e}",
                context={'beat_id': beat_id}
            )
            
            return {
                'status': 'error',
                'error': {
                    'type': type(e).__name__,
                    'message': str(e),
                    'timestamp': e.timestamp.isoformat()
                }
            }
        
        except Exception as e:
            # Unexpected errors
            logger.critical(
                "unexpected_error",
                beat_id=beat_id,
                error=str(e),
                exc_info=True
            )
            
            await self._send_alert(
                severity='critical',
                message=f"Unexpected error: {e}"
            )
            
            return {
                'status': 'error',
                'error': {
                    'type': 'UnexpectedError',
                    'message': 'An unexpected error occurred'
                }
            }
    
    @transaction.atomic
    async def _save_partial_chapter(
        self,
        beat_id: int,
        context: dict
    ) -> Chapter:
        """Save partial results for manual review"""
        
        beat = await ChapterBeat.objects.aget(id=beat_id)
        
        chapter = await Chapter.objects.acreate(
            story_bible=beat.story_bible,
            strand=beat.strand,
            chapter_number=beat.beat_number,
            title=beat.title,
            content=context.get('draft', ''),
            status='needs_review',
            generation_method='partial_generation'
        )
        
        # Store validation errors
        await ChapterValidation.objects.acreate(
            chapter=chapter,
            validation_errors=context.get('errors', []),
            reviewed=False
        )
        
        return chapter
```

---

## 🔄 Retry Strategies

### Strategy 1: Exponential Backoff

```python
async def exponential_backoff_retry(
    func: Callable,
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> Any:
    """
    Exponential backoff: 1s, 2s, 4s, 8s, 16s, ...
    Capped at max_delay.
    """
    
    for attempt in range(max_attempts):
        try:
            return await func()
            
        except RetryableError as e:
            if attempt == max_attempts - 1:
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            
            # Add jitter to prevent thundering herd
            jitter = random.uniform(0, delay * 0.1)
            total_delay = delay + jitter
            
            logger.info(
                "retrying_with_backoff",
                attempt=attempt + 1,
                delay=total_delay
            )
            
            await asyncio.sleep(total_delay)
```

### Strategy 2: Rate Limit Respecting

```python
class RateLimitAwareRetry:
    """
    Respects API rate limits with intelligent retry.
    
    Features:
    - Honors Retry-After header
    - Tracks rate limit windows
    - Adjusts concurrency
    """
    
    def __init__(self):
        self.rate_limit_reset = None
        self.max_concurrent = 10
    
    async def execute(self, func: Callable) -> Any:
        # Wait if in rate limit window
        if self.rate_limit_reset:
            wait_time = (self.rate_limit_reset - datetime.now()).total_seconds()
            if wait_time > 0:
                logger.info("waiting_for_rate_limit", seconds=wait_time)
                await asyncio.sleep(wait_time)
        
        try:
            return await func()
            
        except RateLimitError as e:
            # Update rate limit window
            self.rate_limit_reset = datetime.now() + timedelta(
                seconds=e.retry_after
            )
            
            # Reduce concurrency
            self.max_concurrent = max(1, self.max_concurrent // 2)
            
            logger.warning(
                "rate_limited",
                retry_after=e.retry_after,
                new_concurrency=self.max_concurrent
            )
            
            # Wait and retry
            await asyncio.sleep(e.retry_after)
            return await self.execute(func)
```

---

## 🎯 Fallback Mechanisms

### Fallback 1: Model Switching

```python
class ModelFallbackAgent(BaseStoryAgent):
    """Agent with automatic model fallback"""
    
    PRIMARY_MODEL = "claude-sonnet-4.5"
    FALLBACK_MODELS = ["claude-sonnet-4", "gpt-4-turbo"]
    
    async def generate_with_fallback(self, prompt: str) -> str:
        """Try primary model, fall back if needed"""
        
        models = [self.PRIMARY_MODEL] + self.FALLBACK_MODELS
        
        for model in models:
            try:
                self.llm = ChatAnthropic(model=model)
                result = await self.safe_llm_call(prompt)
                
                if model != self.PRIMARY_MODEL:
                    logger.warning(
                        "used_fallback_model",
                        agent=self.agent_name,
                        model=model
                    )
                
                return result
                
            except Exception as e:
                logger.warning(
                    "model_failed",
                    model=model,
                    error=str(e)
                )
                
                if model == models[-1]:
                    # Last model failed
                    raise AgentError(
                        self.agent_name,
                        "All models failed"
                    ) from e
```

### Fallback 2: Cached Results

```python
from functools import wraps
from typing import Optional

class CachingAgent(BaseStoryAgent):
    """Agent with result caching for fallback"""
    
    def __init__(self):
        super().__init__()
        self.cache = {}  # In production: Redis
    
    def with_cache_fallback(self, cache_key_func: Callable):
        """Decorator for cached fallback"""
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = cache_key_func(*args, **kwargs)
                
                try:
                    # Try normal execution
                    result = await func(*args, **kwargs)
                    
                    # Cache successful result
                    self.cache[cache_key] = result
                    
                    return result
                    
                except AgentError as e:
                    # Try cache
                    cached = self.cache.get(cache_key)
                    
                    if cached:
                        logger.warning(
                            "using_cached_fallback",
                            agent=self.agent_name,
                            cache_key=cache_key
                        )
                        return cached
                    
                    # No cache available
                    raise
            
            return wrapper
        return decorator
```

---

## 📊 Monitoring & Alerting

### Error Metrics

```python
# apps/story_engine/monitoring.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

@dataclass
class ErrorMetrics:
    """Track error patterns"""
    
    error_type: str
    count: int
    last_occurrence: datetime
    affected_agents: List[str]
    recovery_rate: float  # % that recovered successfully

class ErrorMonitor:
    """Monitor and alert on error patterns"""
    
    def __init__(self):
        self.metrics: Dict[str, ErrorMetrics] = {}
        self.alert_thresholds = {
            'error_rate': 0.1,      # 10% error rate
            'critical_count': 5,     # 5 critical errors
            'same_error': 10         # Same error 10 times
        }
    
    async def record_error(
        self,
        error: StoryEngineError,
        agent: str,
        recovered: bool
    ):
        """Record error and check thresholds"""
        
        error_type = type(error).__name__
        
        # Update metrics
        if error_type not in self.metrics:
            self.metrics[error_type] = ErrorMetrics(
                error_type=error_type,
                count=0,
                last_occurrence=datetime.now(),
                affected_agents=[],
                recovery_rate=0.0
            )
        
        metric = self.metrics[error_type]
        metric.count += 1
        metric.last_occurrence = datetime.now()
        
        if agent not in metric.affected_agents:
            metric.affected_agents.append(agent)
        
        # Update recovery rate
        if recovered:
            metric.recovery_rate = (
                metric.recovery_rate * (metric.count - 1) + 1
            ) / metric.count
        else:
            metric.recovery_rate = (
                metric.recovery_rate * (metric.count - 1)
            ) / metric.count
        
        # Check if alerting needed
        await self._check_alert_conditions(error_type, metric)
    
    async def _check_alert_conditions(
        self,
        error_type: str,
        metric: ErrorMetrics
    ):
        """Check if error patterns warrant alerting"""
        
        # Alert 1: Same error repeating
        if metric.count >= self.alert_thresholds['same_error']:
            await self._send_alert(
                severity='warning',
                title=f"Repeated {error_type}",
                message=f"{error_type} occurred {metric.count} times",
                details={
                    'error_type': error_type,
                    'count': metric.count,
                    'affected_agents': metric.affected_agents,
                    'recovery_rate': metric.recovery_rate
                }
            )
        
        # Alert 2: Low recovery rate
        if metric.recovery_rate < 0.5 and metric.count > 5:
            await self._send_alert(
                severity='critical',
                title=f"Low recovery rate for {error_type}",
                message=f"Only {metric.recovery_rate:.0%} recovery rate",
                details={'metric': metric}
            )
        
        # Alert 3: Critical errors
        if isinstance(error_type, FatalError.__class__):
            count_24h = await self._count_recent_errors(
                error_type, hours=24
            )
            
            if count_24h >= self.alert_thresholds['critical_count']:
                await self._send_alert(
                    severity='critical',
                    title=f"Multiple critical {error_type}",
                    message=f"{count_24h} occurrences in 24h"
                )
```

### Alert Integration

```python
class AlertManager:
    """Send alerts via multiple channels"""
    
    async def send_alert(
        self,
        severity: str,  # 'info', 'warning', 'critical'
        title: str,
        message: str,
        details: dict = None
    ):
        """Send alert to configured channels"""
        
        alert = {
            'severity': severity,
            'title': title,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat(),
            'service': 'story_engine'
        }
        
        # Log always
        logger.bind(**alert).log(
            self._severity_to_level(severity),
            title
        )
        
        # Email for critical
        if severity == 'critical':
            await self._send_email(alert)
        
        # Slack for warning+
        if severity in ['warning', 'critical']:
            await self._send_slack(alert)
        
        # PagerDuty for critical only
        if severity == 'critical':
            await self._send_pagerduty(alert)
```

---

## 🎯 Best Practices Summary

### ✅ DO

1. **Classify errors properly** - Use the error hierarchy
2. **Retry intelligently** - Respect rate limits, use backoff
3. **Have fallbacks** - Multiple models, cached results
4. **Monitor patterns** - Track error trends
5. **Alert on anomalies** - Don't wait for catastrophe
6. **Save partial results** - Don't lose work
7. **Log everything** - Structured logging with context

### ❌ DON'T

1. **Catch Exception blindly** - Be specific
2. **Retry forever** - Have max attempts
3. **Ignore transient errors** - They reveal issues
4. **Silent failures** - Always log
5. **Lose context** - Include agent, state, timestamp
6. **Block on errors** - Use async error handling
7. **Alert fatigue** - Smart thresholds only

---

## 📚 See Also

- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System design
- [API_CONTRACTS.md](./API_CONTRACTS.md) - Interface definitions
- [MONITORING_LOGGING.md](./MONITORING_LOGGING.md) - Observability
- [STORY_ENGINE_IMPLEMENTATION.md](./STORY_ENGINE_IMPLEMENTATION.md) - Implementation guide

---

**Error Handling Version**: 1.0  
**Last Updated**: 2025-11-09  
**Status**: Production-Ready Strategy
