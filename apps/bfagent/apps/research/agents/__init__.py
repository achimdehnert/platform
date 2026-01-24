"""
Research Agents
===============

AI agents for research tasks.
"""

from .outline_agents import (
    BaseOutlineAgent,
    OutlineStructureAgent,
    OutlineBeatAgent,
    OutlineGuidanceAgent,
    OutlineTemplateAnalyzer,
    get_outline_agents,
    AgentInput,
    AgentOutput
)

__all__ = [
    'BaseOutlineAgent',
    'OutlineStructureAgent',
    'OutlineBeatAgent',
    'OutlineGuidanceAgent',
    'OutlineTemplateAnalyzer',
    'get_outline_agents',
    'AgentInput',
    'AgentOutput',
]
