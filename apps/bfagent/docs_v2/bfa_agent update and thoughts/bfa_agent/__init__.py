"""BFA Agent - Explosionsschutz mit OpenAI Agents SDK + OpenRouter."""

from .config import setup_openrouter, Models, ModelWithFallback
from .models import (
    ExZoneClassification,
    EquipmentCheckResult,
    VentilationAnalysis,
    BFAReport,
    ZoneType,
    RiskLevel,
)
from .agents import (
    triage_agent,
    cad_reader_agent,
    zone_analyzer_agent,
    equipment_checker_agent,
    report_writer_agent,
)
from .runner import run_bfa_agent, main

# Presets
from .presets import (
    BFA_PRESETS,
    PresetConfig,
    PresetManager,
    ProviderSort,
    get_preset,
    get_preset_model,
    export_presets_for_openrouter,
    list_presets,
)

# Preset-basierte Agents
from .agents_presets import (
    triage_preset,
    cad_reader_preset,
    zone_analyzer_preset,
    equipment_checker_preset,
    report_writer_preset,
    create_agent_with_preset,
)

# MCP Integration
from .mcp_integration import (
    MCPServers,
    MCPServerSets,
    create_bfa_mcp_server,
    create_external_mcp_server,
)

# Research Agents
from .agents_research import (
    research_agent,
    research_agent_preset,
    research_triage_agent,
    create_research_agent,
    create_bfa_research_agent,
)

# MCP-basierte Agents (optional)
try:
    from .agents_mcp import (
        create_triage_agent,
        create_cad_reader_agent,
        create_zone_analyzer_agent,
        create_equipment_checker_agent,
        create_report_writer_agent,
        get_bfa_mcp_server,
        triage_agent as triage_agent_mcp,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

__version__ = "0.3.0"

__all__ = [
    # Config
    "setup_openrouter",
    "Models",
    "ModelWithFallback",
    # Pydantic Models
    "ExZoneClassification",
    "EquipmentCheckResult", 
    "VentilationAnalysis",
    "BFAReport",
    "ZoneType",
    "RiskLevel",
    # Agents (Function Tools - direkte Models)
    "triage_agent",
    "cad_reader_agent",
    "zone_analyzer_agent",
    "equipment_checker_agent",
    "report_writer_agent",
    # Agents (Presets)
    "triage_preset",
    "cad_reader_preset",
    "zone_analyzer_preset",
    "equipment_checker_preset",
    "report_writer_preset",
    "create_agent_with_preset",
    # Research Agents
    "research_agent",
    "research_agent_preset",
    "research_triage_agent",
    "create_research_agent",
    "create_bfa_research_agent",
    # Presets
    "BFA_PRESETS",
    "PresetConfig",
    "PresetManager",
    "ProviderSort",
    "get_preset",
    "get_preset_model",
    "export_presets_for_openrouter",
    "list_presets",
    # MCP Integration
    "MCPServers",
    "MCPServerSets",
    "create_bfa_mcp_server",
    "create_external_mcp_server",
    # Runner
    "run_bfa_agent",
    "main",
    # MCP Flag
    "MCP_AVAILABLE",
]

# MCP Agent exports hinzufügen wenn verfügbar
if MCP_AVAILABLE:
    __all__.extend([
        "create_triage_agent",
        "create_cad_reader_agent",
        "create_zone_analyzer_agent",
        "create_equipment_checker_agent",
        "create_report_writer_agent",
        "get_bfa_mcp_server",
        "triage_agent_mcp",
    ])
