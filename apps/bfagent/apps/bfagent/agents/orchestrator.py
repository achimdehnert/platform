# -*- coding: utf-8 -*-
"""
Agent Orchestrator - Multi-Agent Workflows.

Ermöglicht die Verkettung und parallele Ausführung von Agents.

Features:
- Sequential Pipeline: Agent1 → Agent2 → Agent3
- Parallel Execution: [Agent1, Agent2] → Agent3
- Conditional Branching: if condition → AgentA else → AgentB
- Shared State Management
- Error Handling & Retry

Usage:
    from apps.bfagent.agents.orchestrator import Pipeline, parallel

    # Sequential
    pipeline = Pipeline([
        ValidateAgent(),
        TransformAgent(),
        SaveAgent(),
    ])
    result = await pipeline.run(initial_state)

    # Parallel then Sequential
    pipeline = Pipeline([
        parallel(AnalyzeAgent(), SecurityAgent()),
        MergeAgent(),
    ])
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Optional, Callable, Union, 
    TypeVar, Generic, Tuple, Awaitable
)
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

class StepStatus(Enum):
    """Status eines Pipeline-Schritts."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentState:
    """
    Gemeinsamer State für alle Agents in einer Pipeline.
    
    Immutable by convention - Agents sollten neue States erzeugen.
    """
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def with_data(self, **kwargs) -> 'AgentState':
        """Erzeugt neuen State mit zusätzlichen Daten."""
        new_data = {**self.data, **kwargs}
        return AgentState(
            data=new_data,
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            metadata=self.metadata.copy(),
        )
    
    def with_error(self, error: str) -> 'AgentState':
        """Erzeugt neuen State mit Fehler."""
        return AgentState(
            data=self.data.copy(),
            errors=[*self.errors, error],
            warnings=self.warnings.copy(),
            metadata=self.metadata.copy(),
        )
    
    def with_warning(self, warning: str) -> 'AgentState':
        """Erzeugt neuen State mit Warnung."""
        return AgentState(
            data=self.data.copy(),
            errors=self.errors.copy(),
            warnings=[*self.warnings, warning],
            metadata=self.metadata.copy(),
        )
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


@dataclass
class StepResult:
    """Ergebnis eines Pipeline-Schritts."""
    status: StepStatus
    state: AgentState
    agent_name: str
    duration_ms: float = 0
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Ergebnis einer gesamten Pipeline."""
    success: bool
    final_state: AgentState
    steps: List[StepResult] = field(default_factory=list)
    total_duration_ms: float = 0
    
    @property
    def failed_steps(self) -> List[StepResult]:
        return [s for s in self.steps if s.status == StepStatus.FAILED]
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "total_duration_ms": self.total_duration_ms,
            "steps": [
                {
                    "agent": s.agent_name,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                }
                for s in self.steps
            ],
            "errors": self.final_state.errors,
            "warnings": self.final_state.warnings,
        }


# =============================================================================
# BASE AGENT
# =============================================================================

class BaseAgent(ABC):
    """
    Basis-Klasse für alle orchestrierbaren Agents.
    
    Agents sind zustandslos - State kommt rein, State geht raus.
    """
    
    name: str = "BaseAgent"
    
    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """
        Führt den Agent aus.
        
        Args:
            state: Aktueller Pipeline-State
            
        Returns:
            Neuer State (nicht mutieren!)
        """
        pass
    
    def should_run(self, state: AgentState) -> bool:
        """
        Prüft ob Agent ausgeführt werden soll.
        
        Override für conditional execution.
        """
        return True
    
    async def on_error(self, state: AgentState, error: Exception) -> AgentState:
        """
        Error Handler - override für custom error handling.
        """
        return state.with_error(f"{self.name}: {str(error)}")


# =============================================================================
# PARALLEL WRAPPER
# =============================================================================

@dataclass
class ParallelAgents:
    """Wrapper für parallel auszuführende Agents."""
    agents: List[BaseAgent]
    merge_strategy: str = "merge"  # merge, first, last
    
    @property
    def name(self) -> str:
        names = [a.name for a in self.agents]
        return f"Parallel({', '.join(names)})"


def parallel(*agents: BaseAgent, merge: str = "merge") -> ParallelAgents:
    """
    Markiert Agents für parallele Ausführung.
    
    Args:
        *agents: Agents die parallel laufen sollen
        merge: Wie Results gemerged werden (merge, first, last)
        
    Usage:
        pipeline = Pipeline([
            parallel(AgentA(), AgentB()),
            AgentC(),
        ])
    """
    return ParallelAgents(agents=list(agents), merge_strategy=merge)


# =============================================================================
# PIPELINE
# =============================================================================

class Pipeline:
    """
    Orchestriert mehrere Agents in einer Pipeline.
    
    Features:
    - Sequential execution
    - Parallel execution via parallel()
    - Conditional execution via should_run()
    - Error handling mit on_error()
    - Retry-Logik
    """
    
    def __init__(
        self,
        steps: List[Union[BaseAgent, ParallelAgents]],
        name: str = "Pipeline",
        stop_on_error: bool = True,
        max_retries: int = 0,
    ):
        self.steps = steps
        self.name = name
        self.stop_on_error = stop_on_error
        self.max_retries = max_retries
    
    async def run(self, initial_state: Optional[AgentState] = None) -> PipelineResult:
        """
        Führt die Pipeline aus.
        
        Args:
            initial_state: Start-State (default: leerer State)
            
        Returns:
            PipelineResult mit final State und Step-Results
        """
        state = initial_state or AgentState()
        step_results: List[StepResult] = []
        start_time = datetime.now()
        
        for step in self.steps:
            if isinstance(step, ParallelAgents):
                # Parallel execution
                step_result, state = await self._run_parallel(step, state)
                step_results.extend(step_result)
            else:
                # Sequential execution
                step_result, state = await self._run_agent(step, state)
                step_results.append(step_result)
            
            # Stop on error if configured
            if self.stop_on_error and state.has_errors:
                logger.warning(f"Pipeline {self.name} stopped due to errors")
                break
        
        total_duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return PipelineResult(
            success=not state.has_errors,
            final_state=state,
            steps=step_results,
            total_duration_ms=total_duration,
        )
    
    async def _run_agent(
        self, 
        agent: BaseAgent, 
        state: AgentState
    ) -> Tuple[StepResult, AgentState]:
        """Führt einen einzelnen Agent aus."""
        
        # Check if should run
        if not agent.should_run(state):
            return StepResult(
                status=StepStatus.SKIPPED,
                state=state,
                agent_name=agent.name,
            ), state
        
        start_time = datetime.now()
        
        for attempt in range(self.max_retries + 1):
            try:
                new_state = await agent.execute(state)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                return StepResult(
                    status=StepStatus.SUCCESS,
                    state=new_state,
                    agent_name=agent.name,
                    duration_ms=duration,
                ), new_state
                
            except Exception as e:
                logger.error(f"Agent {agent.name} failed (attempt {attempt + 1}): {e}")
                
                if attempt == self.max_retries:
                    # Final failure
                    error_state = await agent.on_error(state, e)
                    duration = (datetime.now() - start_time).total_seconds() * 1000
                    
                    return StepResult(
                        status=StepStatus.FAILED,
                        state=error_state,
                        agent_name=agent.name,
                        duration_ms=duration,
                        error=str(e),
                    ), error_state
                
                # Retry with backoff
                await asyncio.sleep(0.1 * (attempt + 1))
        
        # Should not reach here
        return StepResult(
            status=StepStatus.FAILED,
            state=state,
            agent_name=agent.name,
        ), state
    
    async def _run_parallel(
        self,
        parallel_agents: ParallelAgents,
        state: AgentState,
    ) -> Tuple[List[StepResult], AgentState]:
        """Führt Agents parallel aus."""
        
        # Create tasks for all agents
        tasks = [
            self._run_agent(agent, state)
            for agent in parallel_agents.agents
        ]
        
        # Run in parallel
        results = await asyncio.gather(*tasks)
        
        # Collect step results
        step_results = [r[0] for r in results]
        new_states = [r[1] for r in results]
        
        # Merge states based on strategy
        merged_state = self._merge_states(
            new_states, 
            parallel_agents.merge_strategy
        )
        
        return step_results, merged_state
    
    def _merge_states(
        self, 
        states: List[AgentState], 
        strategy: str
    ) -> AgentState:
        """Merged mehrere States."""
        
        if strategy == "first":
            return states[0]
        elif strategy == "last":
            return states[-1]
        else:  # merge
            merged_data = {}
            all_errors = []
            all_warnings = []
            
            for s in states:
                merged_data.update(s.data)
                all_errors.extend(s.errors)
                all_warnings.extend(s.warnings)
            
            return AgentState(
                data=merged_data,
                errors=all_errors,
                warnings=all_warnings,
            )


# =============================================================================
# CONDITIONAL PIPELINE
# =============================================================================

class ConditionalPipeline(Pipeline):
    """
    Pipeline mit Bedingungen.
    
    Usage:
        pipeline = ConditionalPipeline(
            condition=lambda s: s.get("needs_review"),
            if_true=[ReviewAgent()],
            if_false=[AutoApproveAgent()],
        )
    """
    
    def __init__(
        self,
        condition: Callable[[AgentState], bool],
        if_true: List[BaseAgent],
        if_false: List[BaseAgent],
        name: str = "ConditionalPipeline",
    ):
        self.condition = condition
        self.if_true_steps = if_true
        self.if_false_steps = if_false
        super().__init__(steps=[], name=name)
    
    async def run(self, initial_state: Optional[AgentState] = None) -> PipelineResult:
        state = initial_state or AgentState()
        
        # Evaluate condition
        if self.condition(state):
            self.steps = self.if_true_steps
        else:
            self.steps = self.if_false_steps
        
        return await super().run(state)


# =============================================================================
# BUILT-IN AGENTS
# =============================================================================

class LogAgent(BaseAgent):
    """Einfacher Agent zum Loggen des States."""
    
    name = "LogAgent"
    
    def __init__(self, message: str = "State"):
        self.message = message
    
    async def execute(self, state: AgentState) -> AgentState:
        logger.info(f"{self.message}: {state.data}")
        return state


class TransformAgent(BaseAgent):
    """Agent der Daten transformiert."""
    
    name = "TransformAgent"
    
    def __init__(self, transform: Callable[[Dict], Dict]):
        self.transform = transform
    
    async def execute(self, state: AgentState) -> AgentState:
        new_data = self.transform(state.data)
        return AgentState(
            data=new_data,
            errors=state.errors,
            warnings=state.warnings,
            metadata=state.metadata,
        )


class ValidateAgent(BaseAgent):
    """Agent der Daten validiert."""
    
    name = "ValidateAgent"
    
    def __init__(self, validators: List[Callable[[Dict], Optional[str]]]):
        self.validators = validators
    
    async def execute(self, state: AgentState) -> AgentState:
        errors = []
        for validator in self.validators:
            error = validator(state.data)
            if error:
                errors.append(error)
        
        if errors:
            new_state = state
            for e in errors:
                new_state = new_state.with_error(e)
            return new_state
        
        return state


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Data Classes
    "AgentState",
    "StepResult",
    "PipelineResult",
    "StepStatus",
    # Base
    "BaseAgent",
    # Pipeline
    "Pipeline",
    "ConditionalPipeline",
    "parallel",
    "ParallelAgents",
    # Built-in Agents
    "LogAgent",
    "TransformAgent",
    "ValidateAgent",
]
