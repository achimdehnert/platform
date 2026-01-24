#!/usr/bin/env python
"""Test Agent Orchestrator - Pipeline and Parallel Execution."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.bfagent.agents.orchestrator import (
    Pipeline, ConditionalPipeline, BaseAgent, AgentState,
    parallel, LogAgent, TransformAgent, ValidateAgent
)


# =============================================================================
# CUSTOM TEST AGENTS
# =============================================================================

class AddNumberAgent(BaseAgent):
    """Adds a number to state."""
    name = "AddNumberAgent"
    
    def __init__(self, key: str, value: int):
        self.key = key
        self.value = value
    
    async def execute(self, state: AgentState) -> AgentState:
        current = state.get(self.key, 0)
        return state.with_data(**{self.key: current + self.value})


class MultiplyAgent(BaseAgent):
    """Multiplies a value in state."""
    name = "MultiplyAgent"
    
    def __init__(self, key: str, factor: int):
        self.key = key
        self.factor = factor
    
    async def execute(self, state: AgentState) -> AgentState:
        current = state.get(self.key, 1)
        return state.with_data(**{self.key: current * self.factor})


class FailingAgent(BaseAgent):
    """Agent that always fails (for testing error handling)."""
    name = "FailingAgent"
    
    async def execute(self, state: AgentState) -> AgentState:
        raise ValueError("Intentional failure!")


class ConditionalAgent(BaseAgent):
    """Agent that only runs if condition is met."""
    name = "ConditionalAgent"
    
    def __init__(self, condition_key: str):
        self.condition_key = condition_key
    
    def should_run(self, state: AgentState) -> bool:
        return state.get(self.condition_key, False)
    
    async def execute(self, state: AgentState) -> AgentState:
        return state.with_data(conditional_ran=True)


# =============================================================================
# TESTS
# =============================================================================

async def test_sequential_pipeline():
    """Test sequential agent execution."""
    print("\n" + "=" * 50)
    print("TEST: Sequential Pipeline")
    print("=" * 50)
    
    pipeline = Pipeline([
        AddNumberAgent("count", 10),
        AddNumberAgent("count", 5),
        MultiplyAgent("count", 2),
    ])
    
    result = await pipeline.run()
    
    print(f"Success: {result.success}")
    print(f"Final count: {result.final_state.get('count')}")
    print(f"Expected: (10 + 5) * 2 = 30")
    print(f"Steps: {len(result.steps)}")
    
    assert result.success
    assert result.final_state.get('count') == 30
    print("✅ PASSED")


async def test_parallel_execution():
    """Test parallel agent execution."""
    print("\n" + "=" * 50)
    print("TEST: Parallel Execution")
    print("=" * 50)
    
    pipeline = Pipeline([
        parallel(
            AddNumberAgent("a", 10),
            AddNumberAgent("b", 20),
            AddNumberAgent("c", 30),
        ),
    ])
    
    result = await pipeline.run()
    
    print(f"Success: {result.success}")
    print(f"a={result.final_state.get('a')}, b={result.final_state.get('b')}, c={result.final_state.get('c')}")
    print(f"Steps: {len(result.steps)}")
    
    assert result.success
    assert result.final_state.get('a') == 10
    assert result.final_state.get('b') == 20
    assert result.final_state.get('c') == 30
    print("✅ PASSED")


async def test_error_handling():
    """Test error handling in pipeline."""
    print("\n" + "=" * 50)
    print("TEST: Error Handling")
    print("=" * 50)
    
    pipeline = Pipeline([
        AddNumberAgent("count", 10),
        FailingAgent(),
        AddNumberAgent("count", 5),  # Should not run
    ], stop_on_error=True)
    
    result = await pipeline.run()
    
    print(f"Success: {result.success}")
    print(f"Errors: {result.final_state.errors}")
    print(f"Failed steps: {[s.agent_name for s in result.failed_steps]}")
    
    assert not result.success
    assert len(result.final_state.errors) > 0
    print("✅ PASSED")


async def test_conditional_execution():
    """Test conditional agent execution."""
    print("\n" + "=" * 50)
    print("TEST: Conditional Execution")
    print("=" * 50)
    
    # With condition = True
    pipeline = Pipeline([
        ConditionalAgent("run_me"),
    ])
    
    initial = AgentState(data={"run_me": True})
    result = await pipeline.run(initial)
    
    print(f"With condition=True: ran={result.final_state.get('conditional_ran')}")
    assert result.final_state.get('conditional_ran') == True
    
    # With condition = False
    initial = AgentState(data={"run_me": False})
    result = await pipeline.run(initial)
    
    print(f"With condition=False: ran={result.final_state.get('conditional_ran')}")
    assert result.final_state.get('conditional_ran') is None
    print("✅ PASSED")


async def test_conditional_pipeline():
    """Test ConditionalPipeline."""
    print("\n" + "=" * 50)
    print("TEST: Conditional Pipeline")
    print("=" * 50)
    
    pipeline = ConditionalPipeline(
        condition=lambda s: s.get("needs_review", False),
        if_true=[AddNumberAgent("path", 1)],  # Review path
        if_false=[AddNumberAgent("path", 2)], # Auto path
    )
    
    # Needs review
    result = await pipeline.run(AgentState(data={"needs_review": True}))
    print(f"With needs_review=True: path={result.final_state.get('path')}")
    assert result.final_state.get('path') == 1
    
    # Auto approve
    result = await pipeline.run(AgentState(data={"needs_review": False}))
    print(f"With needs_review=False: path={result.final_state.get('path')}")
    assert result.final_state.get('path') == 2
    
    print("✅ PASSED")


async def test_retry():
    """Test retry logic."""
    print("\n" + "=" * 50)
    print("TEST: Retry Logic")
    print("=" * 50)
    
    class FailOnceAgent(BaseAgent):
        name = "FailOnceAgent"
        attempts = 0
        
        async def execute(self, state: AgentState) -> AgentState:
            FailOnceAgent.attempts += 1
            if FailOnceAgent.attempts < 2:
                raise ValueError("First attempt fails")
            return state.with_data(succeeded=True)
    
    FailOnceAgent.attempts = 0
    pipeline = Pipeline([FailOnceAgent()], max_retries=2)
    result = await pipeline.run()
    
    print(f"Success: {result.success}")
    print(f"Attempts: {FailOnceAgent.attempts}")
    
    assert result.success
    assert FailOnceAgent.attempts == 2
    print("✅ PASSED")


async def test_built_in_agents():
    """Test built-in utility agents."""
    print("\n" + "=" * 50)
    print("TEST: Built-in Agents")
    print("=" * 50)
    
    # TransformAgent
    pipeline = Pipeline([
        TransformAgent(lambda d: {**d, "transformed": True}),
    ])
    result = await pipeline.run(AgentState(data={"original": True}))
    print(f"TransformAgent: {result.final_state.data}")
    assert result.final_state.get("transformed") == True
    
    # ValidateAgent
    pipeline = Pipeline([
        ValidateAgent([
            lambda d: "Missing name" if "name" not in d else None,
        ]),
    ])
    result = await pipeline.run(AgentState(data={}))
    print(f"ValidateAgent (no name): errors={result.final_state.errors}")
    assert "Missing name" in result.final_state.errors
    
    result = await pipeline.run(AgentState(data={"name": "Test"}))
    print(f"ValidateAgent (with name): errors={result.final_state.errors}")
    assert len(result.final_state.errors) == 0
    
    print("✅ PASSED")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("AGENT ORCHESTRATOR TESTS")
    print("=" * 60)
    
    await test_sequential_pipeline()
    await test_parallel_execution()
    await test_error_handling()
    await test_conditional_execution()
    await test_conditional_pipeline()
    await test_retry()
    await test_built_in_agents()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
