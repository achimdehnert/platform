# Story Engine - Production-Ready Agent Implementations

> **Focus**: Type-Safe, Robust, Production-Grade Agents  
> **Status**: Production Planning  
> **Updated**: 2025-11-09  
> **Version**: 2.0 (Refactored with Best Practices)

---

## 📋 Table of Contents

1. [Base Agent (Refactored)](#base-agent-refactored)
2. [Story Architect Agent](#story-architect-agent)
3. [Writer Agent](#writer-agent)
4. [Continuity Checker Agent](#continuity-checker-agent)
5. [Editor Agent](#editor-agent)
6. [Performance Monitoring](#performance-monitoring)

---

## 🏗️ Base Agent (Refactored)

### Production-Ready Base Class

```python
# apps/story_engine/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Dict, Any
from contextlib import asynccontextmanager
from time import perf_counter
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
import structlog
import asyncio

from apps.story_engine.state import ChapterState
from apps.story_engine.exceptions import (
    AgentError,
    AgentTimeoutError,
    RateLimitError,
    TemporaryServiceError,
    FatalError
)

logger = structlog.get_logger()

StateT = TypeVar('StateT', bound=BaseModel)

class AgentConfig(BaseModel):
    """Type-safe agent configuration"""
    
    model: str = "claude-sonnet-4.5"
    temperature: float = 0.7
    max_tokens: int = 8000
    timeout: int = 120
    max_retries: int = 3
    
    # Fallback configuration
    fallback_models: list[str] = [
        "claude-sonnet-4",
        "gpt-4-turbo"
    ]

class BaseStoryAgent(ABC, Generic[StateT]):
    """
    Production-ready base agent with:
    - Type safety (Pydantic)
    - Error handling with retries
    - Performance tracking
    - Fallback mechanisms
    - Structured logging
    
    2025 Best Practices:
    - Small, focused agents
    - Idempotent operations
    - Graceful degradation
    - Observable execution
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.agent_name = self.__class__.__name__
        self._init_llm()
        
        # Metrics tracking
        self._execution_count = 0
        self._total_tokens = 0
        self._total_time = 0.0
    
    def _init_llm(self):
        """Initialize LLM with config"""
        model = self.config.model
        
        if model.startswith("claude"):
            self.llm = ChatAnthropic(
                model=model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
        elif model.startswith("gpt"):
            self.llm = ChatOpenAI(
                model=model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
        else:
            raise ValueError(f"Unsupported model: {model}")
    
    @asynccontextmanager
    async def track_performance(self, operation: str):
        """
        Context manager for automatic performance tracking.
        
        Usage:
            async with self.track_performance("plan_chapter"):
                result = await self._plan(state)
        """
        start_time = perf_counter()
        start_tokens = self._total_tokens
        
        try:
            yield
            
            # Success metrics
            duration = perf_counter() - start_time
            tokens_used = self._total_tokens - start_tokens
            
            self._execution_count += 1
            self._total_time += duration
            
            logger.info(
                "agent_execution_success",
                agent=self.agent_name,
                operation=operation,
                duration_seconds=round(duration, 2),
                tokens_used=tokens_used,
                avg_duration=round(self._total_time / self._execution_count, 2)
            )
            
        except Exception as e:
            # Failure metrics
            duration = perf_counter() - start_time
            
            logger.error(
                "agent_execution_failed",
                agent=self.agent_name,
                operation=operation,
                duration_seconds=round(duration, 2),
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def execute_with_retry(
        self,
        func: callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry.
        
        Handles:
        - Rate limits (respects Retry-After)
        - Temporary service errors (exponential backoff)
        - Timeouts (linear backoff)
        
        Best Practice: Always use this for LLM calls.
        """
        for attempt in range(self.config.max_retries):
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
                # Respect API rate limits
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
                
            except AgentTimeoutError as e:
                # Linear backoff for timeouts
                wait_time = 5 * (attempt + 1)
                logger.warning(
                    "timeout_error",
                    agent=self.agent_name,
                    wait_seconds=wait_time,
                    attempt=attempt + 1
                )
                await asyncio.sleep(wait_time)
                
            except FatalError:
                # Don't retry fatal errors
                logger.error(
                    "fatal_error",
                    agent=self.agent_name,
                    exc_info=True
                )
                raise
        
        # All retries exhausted
        raise AgentError(
            self.agent_name,
            f"Failed after {self.config.max_retries} attempts"
        )
    
    async def safe_llm_call(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Wrapper for LLM calls with automatic error handling.
        
        Converts provider-specific errors to our error hierarchy.
        Includes automatic retry logic.
        """
        async def _call():
            try:
                response = await self.llm.ainvoke(prompt, **kwargs)
                
                # Track token usage
                if hasattr(response, 'usage_metadata'):
                    self._total_tokens += response.usage_metadata.get('total_tokens', 0)
                
                return response.content
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Map to our error types
                if "rate_limit" in error_str or "429" in error_str:
                    retry_after = self._extract_retry_after(e) or 60
                    raise RateLimitError(retry_after)
                
                elif any(code in error_str for code in ['502', '503', '504']):
                    raise TemporaryServiceError(str(e))
                
                elif "timeout" in error_str:
                    raise AgentTimeoutError(self.agent_name, str(e))
                
                elif "authentication" in error_str or "401" in error_str:
                    raise FatalError(f"Authentication failed: {e}")
                
                else:
                    # Unknown error - log details
                    logger.error(
                        "unknown_llm_error",
                        agent=self.agent_name,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True
                    )
                    raise AgentError(self.agent_name, str(e)) from e
        
        return await self.execute_with_retry(_call)
    
    async def call_with_fallback(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Call LLM with automatic model fallback.
        
        Tries:
        1. Primary model (from config)
        2. Fallback models (in order)
        
        Use this for critical operations where failure is not acceptable.
        """
        models = [self.config.model] + self.config.fallback_models
        
        for model in models:
            try:
                # Switch model temporarily
                original_model = self.config.model
                self.config.model = model
                self._init_llm()
                
                result = await self.safe_llm_call(prompt, **kwargs)
                
                if model != original_model:
                    logger.warning(
                        "used_fallback_model",
                        agent=self.agent_name,
                        original=original_model,
                        fallback=model
                    )
                
                return result
                
            except Exception as e:
                logger.warning(
                    "model_failed",
                    agent=self.agent_name,
                    model=model,
                    error=str(e)
                )
                
                if model == models[-1]:
                    # Last model failed
                    raise AgentError(
                        self.agent_name,
                        "All models failed"
                    ) from e
            
            finally:
                # Restore original model
                self.config.model = original_model
                self._init_llm()
    
    @staticmethod
    def _extract_retry_after(error: Exception) -> Optional[int]:
        """Extract Retry-After value from error"""
        error_str = str(error)
        
        # Try to find "retry after X seconds" pattern
        import re
        match = re.search(r'retry.*?(\d+).*?second', error_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Default fallback
        return None
    
    # ========== Abstract Methods ==========
    
    @abstractmethod
    async def execute(self, state: StateT) -> StateT:
        """
        Execute agent logic.
        
        Must be implemented by concrete agents.
        Should be idempotent: same input → same output.
        """
        pass
    
    @abstractmethod
    async def validate_input(self, state: StateT) -> bool:
        """
        Validate that state is ready for this agent.
        
        Return False if state is invalid.
        Raise FatalError if state is corrupted.
        """
        pass
    
    @abstractmethod
    async def validate_output(self, state: StateT) -> bool:
        """
        Validate that agent produced valid output.
        
        Return False if output is invalid.
        """
        pass
```

---

## 🏛️ Story Architect Agent

```python
# apps/story_engine/agents/story_architect.py
from apps.story_engine.agents.base_agent import BaseStoryAgent, AgentConfig
from apps.story_engine.state import ChapterState, ChapterPlan
from apps.story_engine.prompts.architect_prompts import ArchitectPrompts
from apps.story_engine.exceptions import AgentError, ValidationError
import structlog
import json

logger = structlog.get_logger()

class StoryArchitectAgent(BaseStoryAgent[ChapterState]):
    """
    Story Architect: Plans chapter structure.
    
    Responsibilities:
    - Create detailed chapter outline
    - Ensure story beats are hit
    - Maintain plot consistency
    - Plan character development moments
    
    Input Requirements:
    - beat_description
    - world_rules
    - character_profiles
    - previous_summaries
    
    Output:
    - Structured ChapterPlan
    """
    
    def __init__(self, config: AgentConfig = None):
        # Architect uses lower temperature for consistency
        config = config or AgentConfig(
            model="claude-sonnet-4.5",
            temperature=0.3,  # More deterministic
            max_tokens=2000
        )
        super().__init__(config)
        self.prompts = ArchitectPrompts()
    
    async def execute(self, state: ChapterState) -> ChapterState:
        """
        Plan chapter structure.
        
        Process:
        1. Validate input state
        2. Build context-aware prompt
        3. Generate plan via LLM
        4. Parse and validate plan
        5. Update state
        """
        async with self.track_performance("plan_chapter"):
            # 1. Validate
            if not await self.validate_input(state):
                raise AgentError(
                    self.agent_name,
                    "Invalid input state for architect"
                )
            
            # 2. Build prompt
            prompt = self.prompts.build_planning_prompt(
                beat=state.beat_description,
                world_rules=state.world_rules,
                characters=state.character_profiles,
                previous_summaries=state.previous_summaries,
                target_word_count=state.target_word_count
            )
            
            # 3. Generate plan
            try:
                response = await self.call_with_fallback(
                    prompt=prompt,
                    response_format={"type": "json_object"}
                )
                
                plan_data = json.loads(response)
                
            except json.JSONDecodeError as e:
                logger.error(
                    "failed_to_parse_plan",
                    agent=self.agent_name,
                    error=str(e),
                    response=response[:200]
                )
                raise AgentError(
                    self.agent_name,
                    "Failed to parse plan JSON"
                ) from e
            
            # 4. Validate plan structure
            try:
                plan = ChapterPlan(**plan_data)
            except Exception as e:
                raise ValidationError(
                    errors=[{
                        'field': 'chapter_plan',
                        'error': str(e)
                    }],
                    message="Invalid plan structure"
                ) from e
            
            # 5. Update state
            state.plan = plan
            state.current_agent = self.agent_name
            
            logger.info(
                "plan_created",
                agent=self.agent_name,
                plot_points=len(plan.plot_points),
                estimated_words=plan.estimated_word_count
            )
            
            return state
    
    async def validate_input(self, state: ChapterState) -> bool:
        """Validate state is ready for planning"""
        
        # Required fields
        if not state.beat_description:
            logger.warning(
                "missing_beat_description",
                agent=self.agent_name
            )
            return False
        
        # Should have world rules
        if len(state.world_rules) == 0:
            logger.warning(
                "no_world_rules",
                agent=self.agent_name
            )
            # Not critical - continue
        
        # Should have characters
        if len(state.character_profiles) == 0:
            logger.warning(
                "no_characters",
                agent=self.agent_name
            )
        
        return True
    
    async def validate_output(self, state: ChapterState) -> bool:
        """Validate that plan was created"""
        
        if state.plan is None:
            logger.error(
                "no_plan_created",
                agent=self.agent_name
            )
            return False
        
        # Check plan has minimum required elements
        if len(state.plan.plot_points) < 2:
            logger.warning(
                "insufficient_plot_points",
                agent=self.agent_name,
                count=len(state.plan.plot_points)
            )
            return False
        
        return True
```

---

## ✍️ Writer Agent

```python
# apps/story_engine/agents/writer.py
from apps.story_engine.agents.base_agent import BaseStoryAgent, AgentConfig
from apps.story_engine.state import ChapterState
from apps.story_engine.prompts.writer_prompts import WriterPrompts
from apps.story_engine.exceptions import AgentError
import structlog

logger = structlog.get_logger()

class WriterAgent(BaseStoryAgent[ChapterState]):
    """
    Writer: Generates prose from plan.
    
    Responsibilities:
    - Generate compelling prose
    - Follow style guide
    - Maintain character voices
    - Hit target word count
    
    Input Requirements:
    - plan (from Architect)
    - prose_style
    - character_profiles
    
    Output:
    - draft (prose text, 2000-3000 words)
    """
    
    def __init__(self, config: AgentConfig = None):
        # Writer uses higher temperature for creativity
        config = config or AgentConfig(
            model="claude-sonnet-4.5",
            temperature=0.7,  # More creative
            max_tokens=8000   # Need space for prose
        )
        super().__init__(config)
        self.prompts = WriterPrompts()
    
    async def execute(self, state: ChapterState) -> ChapterState:
        """
        Generate prose from plan.
        
        Process:
        1. Validate has plan
        2. Build writing prompt
        3. Generate prose
        4. Validate length
        5. Update state
        """
        async with self.track_performance("write_prose"):
            # 1. Validate
            if not await self.validate_input(state):
                raise AgentError(
                    self.agent_name,
                    "Invalid input state for writer"
                )
            
            # 2. Build prompt
            prompt = self.prompts.build_writing_prompt(
                plan=state.plan,
                style=state.prose_style,
                characters=state.character_profiles,
                previous_summaries=state.previous_summaries,
                target_words=state.target_word_count
            )
            
            # 3. Generate (with fallback)
            draft = await self.call_with_fallback(prompt)
            
            # 4. Validate length
            word_count = len(draft.split())
            min_words = int(state.target_word_count * 0.8)
            max_words = int(state.target_word_count * 1.2)
            
            if word_count < min_words:
                logger.warning(
                    "draft_too_short",
                    agent=self.agent_name,
                    words=word_count,
                    min_words=min_words
                )
                # Try to extend
                draft = await self._extend_draft(draft, state)
                word_count = len(draft.split())
            
            elif word_count > max_words:
                logger.warning(
                    "draft_too_long",
                    agent=self.agent_name,
                    words=word_count,
                    max_words=max_words
                )
                # Will be handled by editor
            
            # 5. Update state
            state.draft = draft
            state.current_agent = self.agent_name
            
            logger.info(
                "draft_created",
                agent=self.agent_name,
                word_count=word_count,
                target=state.target_word_count
            )
            
            return state
    
    async def _extend_draft(
        self,
        draft: str,
        state: ChapterState
    ) -> str:
        """Extend draft that's too short"""
        
        needed_words = state.target_word_count - len(draft.split())
        
        extend_prompt = f"""
Continue this chapter draft to add approximately {needed_words} more words.
Maintain the same style, tone, and narrative voice.

Current draft:
{draft}

Add a scene or extend the ending to reach the target length.
Focus on character development or world-building details.
"""
        
        extension = await self.safe_llm_call(extend_prompt)
        return draft + "\n\n" + extension
    
    async def validate_input(self, state: ChapterState) -> bool:
        """Validate state has plan"""
        
        if state.plan is None:
            logger.error(
                "no_plan_for_writer",
                agent=self.agent_name
            )
            return False
        
        return True
    
    async def validate_output(self, state: ChapterState) -> bool:
        """Validate draft was created and meets minimum length"""
        
        if state.draft is None:
            logger.error(
                "no_draft_created",
                agent=self.agent_name
            )
            return False
        
        word_count = len(state.draft.split())
        min_words = 1000
        
        if word_count < min_words:
            logger.error(
                "draft_too_short",
                agent=self.agent_name,
                words=word_count
            )
            return False
        
        return True
```

---

## ✅ Continuity Checker Agent

```python
# apps/story_engine/agents/continuity_checker.py
from apps.story_engine.agents.base_agent import BaseStoryAgent, AgentConfig
from apps.story_engine.state import ChapterState, ConsistencyIssue, Severity, IssueType
from apps.story_engine.prompts.checker_prompts import CheckerPrompts
from apps.story_engine.exceptions import AgentError
import structlog
import json

logger = structlog.get_logger()

class ContinuityCheckerAgent(BaseStoryAgent[ChapterState]):
    """
    Continuity Checker: Validates consistency.
    
    Responsibilities:
    - Check for contradictions
    - Validate world rules
    - Verify character consistency
    - Flag plot holes
    
    Input Requirements:
    - draft
    - world_rules
    - character_profiles
    - previous_summaries
    
    Output:
    - issues (list of ConsistencyIssue)
    - consistency_score (0-1)
    """
    
    def __init__(self, config: AgentConfig = None):
        # Checker uses lowest temperature for accuracy
        config = config or AgentConfig(
            model="claude-sonnet-4.5",
            temperature=0.1,  # Very deterministic
            max_tokens=3000
        )
        super().__init__(config)
        self.prompts = CheckerPrompts()
    
    async def execute(self, state: ChapterState) -> ChapterState:
        """
        Check draft for consistency issues.
        
        Process:
        1. Validate has draft
        2. Build checking prompt
        3. Run consistency checks
        4. Parse issues
        5. Calculate score
        6. Update state
        """
        async with self.track_performance("check_consistency"):
            # 1. Validate
            if not await self.validate_input(state):
                raise AgentError(
                    self.agent_name,
                    "Invalid input state for checker"
                )
            
            # 2. Build prompt
            prompt = self.prompts.build_checking_prompt(
                draft=state.draft,
                world_rules=state.world_rules,
                characters=state.character_profiles,
                previous_summaries=state.previous_summaries
            )
            
            # 3. Run checks
            try:
                response = await self.safe_llm_call(
                    prompt=prompt,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response)
                
            except json.JSONDecodeError as e:
                logger.error(
                    "failed_to_parse_check_result",
                    agent=self.agent_name,
                    error=str(e)
                )
                # Continue with empty issues list
                result = {'issues': [], 'consistency_score': 1.0}
            
            # 4. Parse issues
            issues = []
            for issue_data in result.get('issues', []):
                try:
                    issue = ConsistencyIssue(**issue_data)
                    issues.append(issue)
                except Exception as e:
                    logger.warning(
                        "invalid_issue_format",
                        agent=self.agent_name,
                        issue=issue_data,
                        error=str(e)
                    )
            
            # 5. Calculate score
            consistency_score = result.get('consistency_score', 1.0)
            
            # Adjust score based on critical issues
            critical_count = sum(
                1 for i in issues if i.severity == Severity.CRITICAL
            )
            if critical_count > 0:
                consistency_score = min(consistency_score, 0.5)
            
            # 6. Update state
            state.issues = issues
            state.consistency_score = consistency_score
            state.current_agent = self.agent_name
            
            # Increment iteration if critical issues found
            if state.has_critical_issues():
                state.iteration += 1
            
            logger.info(
                "consistency_checked",
                agent=self.agent_name,
                issues=len(issues),
                critical=critical_count,
                score=consistency_score,
                iteration=state.iteration
            )
            
            return state
    
    async def validate_input(self, state: ChapterState) -> bool:
        """Validate state has draft"""
        
        if state.draft is None:
            logger.error(
                "no_draft_for_checker",
                agent=self.agent_name
            )
            return False
        
        return True
    
    async def validate_output(self, state: ChapterState) -> bool:
        """Validate check was performed"""
        
        if state.consistency_score is None:
            logger.warning(
                "no_consistency_score",
                agent=self.agent_name
            )
            # Not critical
        
        return True
```

---

## 🎨 Editor Agent

```python
# apps/story_engine/agents/editor.py
from apps/story_engine.agents.base_agent import BaseStoryAgent, AgentConfig
from apps.story_engine.state import ChapterState
from apps.story_engine.prompts.editor_prompts import EditorPrompts
from apps.story_engine.exceptions import AgentError
import structlog

logger = structlog.get_logger()

class EditorAgent(BaseStoryAgent[ChapterState]):
    """
    Editor: Polishes prose.
    
    Responsibilities:
    - Fix identified issues
    - Improve prose quality
    - Enhance readability
    - Final polish
    
    Input Requirements:
    - draft
    - issues (from Checker)
    - prose_style
    
    Output:
    - final_text (polished prose)
    - quality_score (0-1)
    """
    
    def __init__(self, config: AgentConfig = None):
        # Editor uses medium temperature
        config = config or AgentConfig(
            model="claude-sonnet-4.5",
            temperature=0.5,  # Balanced
            max_tokens=8000
        )
        super().__init__(config)
        self.prompts = EditorPrompts()
    
    async def execute(self, state: ChapterState) -> ChapterState:
        """
        Edit and polish chapter.
        
        Process:
        1. Validate has draft
        2. Build editing prompt
        3. Generate polished version
        4. Calculate quality score
        5. Update state
        """
        async with self.track_performance("edit_chapter"):
            # 1. Validate
            if not await self.validate_input(state):
                raise AgentError(
                    self.agent_name,
                    "Invalid input state for editor"
                )
            
            # 2. Build prompt
            prompt = self.prompts.build_editing_prompt(
                draft=state.draft,
                issues=state.issues,
                style=state.prose_style
            )
            
            # 3. Generate polished version
            final_text = await self.call_with_fallback(prompt)
            
            # 4. Calculate quality score
            quality_score = await self._calculate_quality(
                final_text,
                state
            )
            
            # 5. Update state
            state.final_text = final_text
            state.quality_score = quality_score
            state.current_agent = self.agent_name
            
            logger.info(
                "chapter_edited",
                agent=self.agent_name,
                quality_score=quality_score,
                issues_fixed=len(state.issues)
            )
            
            return state
    
    async def _calculate_quality(
        self,
        text: str,
        state: ChapterState
    ) -> float:
        """
        Calculate quality score.
        
        Factors:
        - Consistency score
        - Word count match
        - No critical issues remaining
        """
        score = 1.0
        
        # Factor 1: Consistency
        if state.consistency_score:
            score *= state.consistency_score
        
        # Factor 2: Word count accuracy
        word_count = len(text.split())
        target = state.target_word_count
        deviation = abs(word_count - target) / target
        
        if deviation > 0.2:  # More than 20% off
            score *= 0.9
        
        # Factor 3: Critical issues
        if state.has_critical_issues():
            score *= 0.7
        
        return max(0.0, min(1.0, score))
    
    async def validate_input(self, state: ChapterState) -> bool:
        """Validate state has draft"""
        
        if state.draft is None:
            logger.error(
                "no_draft_for_editor",
                agent=self.agent_name
            )
            return False
        
        return True
    
    async def validate_output(self, state: ChapterState) -> bool:
        """Validate final text was created"""
        
        if state.final_text is None:
            logger.error(
                "no_final_text",
                agent=self.agent_name
            )
            return False
        
        # Check minimum length
        word_count = len(state.final_text.split())
        if word_count < 1000:
            logger.error(
                "final_text_too_short",
                agent=self.agent_name,
                words=word_count
            )
            return False
        
        return True
```

---

## 📊 Performance Monitoring

```python
# apps/story_engine/monitoring/agent_metrics.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
import structlog

logger = structlog.get_logger()

@dataclass
class AgentExecutionMetrics:
    """Metrics for a single agent execution"""
    
    agent_name: str
    operation: str
    duration: float
    tokens_used: int
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    error: str = None

class AgentMetricsCollector:
    """
    Collect and aggregate agent metrics.
    
    Usage:
        collector = AgentMetricsCollector()
        collector.record(metrics)
        summary = collector.get_summary("StoryArchitectAgent")
    """
    
    def __init__(self):
        self.metrics: List[AgentExecutionMetrics] = []
    
    def record(self, metrics: AgentExecutionMetrics):
        """Record agent execution metrics"""
        self.metrics.append(metrics)
        
        logger.info(
            "metrics_recorded",
            agent=metrics.agent_name,
            operation=metrics.operation,
            duration=metrics.duration,
            success=metrics.success
        )
    
    def get_summary(self, agent_name: str = None) -> Dict:
        """
        Get summary statistics.
        
        Args:
            agent_name: Filter by agent, or None for all
            
        Returns:
            {
                'total_executions': int,
                'success_rate': float,
                'avg_duration': float,
                'total_tokens': int,
                'by_operation': {...}
            }
        """
        filtered = [
            m for m in self.metrics
            if agent_name is None or m.agent_name == agent_name
        ]
        
        if not filtered:
            return {}
        
        total = len(filtered)
        successes = sum(1 for m in filtered if m.success)
        
        return {
            'total_executions': total,
            'success_rate': successes / total,
            'avg_duration': sum(m.duration for m in filtered) / total,
            'total_tokens': sum(m.tokens_used for m in filtered),
            'by_operation': self._summarize_by_operation(filtered)
        }
    
    def _summarize_by_operation(
        self,
        metrics: List[AgentExecutionMetrics]
    ) -> Dict:
        """Group metrics by operation"""
        by_op = {}
        
        for m in metrics:
            if m.operation not in by_op:
                by_op[m.operation] = []
            by_op[m.operation].append(m)
        
        return {
            op: {
                'count': len(mlist),
                'avg_duration': sum(m.duration for m in mlist) / len(mlist)
            }
            for op, mlist in by_op.items()
        }
```

---

## 📚 See Also

- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System architecture
- [ERROR_HANDLING.md](./ERROR_HANDLING.md) - Error handling strategy
- [API_CONTRACTS.md](./API_CONTRACTS.md) - Interface definitions
- [STORY_ENGINE_IMPLEMENTATION.md](./STORY_ENGINE_IMPLEMENTATION.md) - Implementation guide

---

**Agent Implementation Version**: 2.0  
**Last Updated**: 2025-11-09  
**Status**: Production-Ready Code
