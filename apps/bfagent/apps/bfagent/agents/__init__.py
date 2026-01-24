# -*- coding: utf-8 -*-
"""
BF Agent - Spezialisierte Agents.

Diese Agents bieten Guardrail-Funktionalität und Domain-Expertise.
"""

from .django_agent import (
    DjangoAgent,
    ValidationResult,
    ValidationError,
    FixResult,
    auto_fix_code,
    validate_and_fix,
)
from .orchestrator import (
    Pipeline,
    ConditionalPipeline,
    BaseAgent,
    AgentState,
    PipelineResult,
    StepResult,
    parallel,
    LogAgent,
    TransformAgent,
    ValidateAgent,
)
from .code_quality_agent import (
    CodeQualityAgent,
    QualityReport,
    analyze_code_quality,
    quick_quality_check,
)
from .writing_agent import (
    WritingAgent,
    WritingAnalysis,
    analyze_writing,
    summarize_chapter,
)
from .research_agent import (
    ResearchAgent,
    ResearchResult,
    quick_research,
    verify_fact,
    research_world,
)


# Convenience-Funktionen
def validate_before_edit(code: str, file_path: str) -> ValidationResult:
    """Validiert Code vor dem Speichern."""
    agent = DjangoAgent()
    if file_path.endswith('.html'):
        return agent.validate_template(code, file_path)
    return agent.validate_python_file(code, file_path)


def validate_command(command: str) -> ValidationResult:
    """Validiert einen Command vor Ausführung."""
    return DjangoAgent().validate_command(command)


def validate_url(url_path: str) -> ValidationResult:
    """Validiert einen URL-Pfad gegen die URL-Konfiguration."""
    return DjangoAgent().validate_url_path(url_path)


__all__ = [
    # DjangoAgent
    "DjangoAgent",
    "ValidationResult", 
    "ValidationError",
    "FixResult",
    "validate_before_edit",
    "validate_command",
    "validate_url",
    "auto_fix_code",
    "validate_and_fix",
    # Orchestrator
    "Pipeline",
    "ConditionalPipeline",
    "BaseAgent",
    "AgentState",
    "PipelineResult",
    "StepResult",
    "parallel",
    "LogAgent",
    "TransformAgent",
    "ValidateAgent",
    # CodeQualityAgent
    "CodeQualityAgent",
    "QualityReport",
    "analyze_code_quality",
    "quick_quality_check",
    # WritingAgent
    "WritingAgent",
    "WritingAnalysis",
    "analyze_writing",
    "summarize_chapter",
    # ResearchAgent
    "ResearchAgent",
    "ResearchResult",
    "quick_research",
    "verify_fact",
    "research_world",
]
