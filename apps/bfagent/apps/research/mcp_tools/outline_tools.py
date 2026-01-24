"""
MCP Tools for Outline Generation
=================================

Tools for generating and managing outlines via MCP.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# =============================================================================
# MCP Tool Definitions
# =============================================================================

OUTLINE_TOOLS = [
    {
        "name": "outline_generate",
        "description": "Generate a complete outline for a book or paper",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_type": {
                    "type": "string",
                    "enum": ["book", "paper", "article", "report"],
                    "description": "Type of project"
                },
                "title": {
                    "type": "string",
                    "description": "Project title"
                },
                "framework": {
                    "type": "string",
                    "description": "Framework to use (e.g., 'imrad', 'heros_journey', 'save_the_cat')"
                },
                "genre": {
                    "type": "string",
                    "description": "Genre for creative writing (fantasy, thriller, romance, etc.)"
                },
                "word_count": {
                    "type": "integer",
                    "description": "Target word count"
                },
                "context": {
                    "type": "object",
                    "description": "Additional context (topic, characters, research_question, etc.)"
                },
                "rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Rules to apply (genre rules, journal format, etc.)"
                },
                "use_ai": {
                    "type": "boolean",
                    "description": "Whether to use AI for enhancement (default: true)"
                }
            },
            "required": ["project_type", "title"]
        }
    },
    {
        "name": "outline_list_frameworks",
        "description": "List all available outline frameworks",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_type": {
                    "type": "string",
                    "enum": ["book", "paper", "all"],
                    "description": "Filter by project type"
                }
            }
        }
    },
    {
        "name": "outline_apply_rules",
        "description": "Apply rules to an existing outline",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outline": {
                    "type": "object",
                    "description": "The outline to modify"
                },
                "rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Rules to apply"
                }
            },
            "required": ["outline", "rules"]
        }
    },
    {
        "name": "outline_analyze_source",
        "description": "Analyze a source text to create an outline template",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Source text to analyze"
                },
                "source_type": {
                    "type": "string",
                    "enum": ["book", "paper", "article"],
                    "description": "Type of source"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "outline_export",
        "description": "Export outline to different formats",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outline": {
                    "type": "object",
                    "description": "The outline to export"
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "json", "yaml", "html"],
                    "description": "Export format"
                }
            },
            "required": ["outline", "format"]
        }
    }
]


# =============================================================================
# Tool Handlers
# =============================================================================

async def handle_outline_generate(params: Dict) -> Dict:
    """Generate a complete outline."""
    from ..services.outline_generator import get_outline_generator
    
    generator = get_outline_generator()
    
    context = params.get("context", {})
    if params.get("genre"):
        context["genre"] = params["genre"]
    
    constraints = {}
    if params.get("word_count"):
        constraints["word_count"] = params["word_count"]
    
    outline = await generator.generate(
        project_type=params.get("project_type", "book"),
        title=params.get("title", "Untitled"),
        framework=params.get("framework"),
        context=context,
        constraints=constraints,
        rules=params.get("rules", []),
        use_ai=params.get("use_ai", True)
    )
    
    return {
        "success": True,
        "outline": outline.to_dict(),
        "markdown": outline.to_markdown()
    }


async def handle_outline_list_frameworks(params: Dict) -> Dict:
    """List available frameworks."""
    from ..services.paper_frameworks import list_paper_frameworks
    from apps.bfagent.services.story_frameworks import list_frameworks
    
    project_type = params.get("project_type", "all")
    
    frameworks = []
    
    if project_type in ["book", "all"]:
        story_fws = list_frameworks()
        for fw in story_fws:
            fw["category"] = "creative_writing"
        frameworks.extend(story_fws)
    
    if project_type in ["paper", "all"]:
        paper_fws = list_paper_frameworks()
        for fw in paper_fws:
            fw["category"] = "scientific_writing"
        frameworks.extend(paper_fws)
    
    return {
        "success": True,
        "frameworks": frameworks,
        "count": len(frameworks)
    }


async def handle_outline_apply_rules(params: Dict) -> Dict:
    """Apply rules to an outline."""
    from ..services.outline_generator import get_outline_generator, OutlineSection
    
    outline_data = params.get("outline", {})
    rules = params.get("rules", [])
    
    if not outline_data.get("sections"):
        return {
            "success": False,
            "error": "No sections in outline"
        }
    
    generator = get_outline_generator()
    
    # Convert dict sections to OutlineSection objects
    sections = []
    for s in outline_data["sections"]:
        sections.append(OutlineSection(**s))
    
    # Apply each rule
    for rule in rules:
        sections = await generator._apply_rule(sections, rule, {})
    
    # Convert back to dict
    outline_data["sections"] = [s.to_dict() for s in sections]
    outline_data["rules_applied"] = outline_data.get("rules_applied", []) + rules
    
    return {
        "success": True,
        "outline": outline_data
    }


async def handle_outline_analyze_source(params: Dict) -> Dict:
    """Analyze source text for template."""
    from ..agents.outline_agents import OutlineTemplateAnalyzer
    
    analyzer = OutlineTemplateAnalyzer()
    
    result = await analyzer.analyze_text(
        text=params.get("text", ""),
        source_type=params.get("source_type", "book")
    )
    
    if result.success:
        return {
            "success": True,
            "template": result.data
        }
    else:
        return {
            "success": False,
            "errors": result.errors
        }


async def handle_outline_export(params: Dict) -> Dict:
    """Export outline to format."""
    from ..services.outline_generator import GeneratedOutline, OutlineSection
    import yaml
    import json
    
    outline_data = params.get("outline", {})
    export_format = params.get("format", "markdown")
    
    # Reconstruct outline object
    sections = [OutlineSection(**s) for s in outline_data.get("sections", [])]
    outline = GeneratedOutline(
        sections=sections,
        **{k: v for k, v in outline_data.items() if k != "sections"}
    )
    
    if export_format == "markdown":
        return {
            "success": True,
            "content": outline.to_markdown(),
            "format": "markdown"
        }
    elif export_format == "json":
        return {
            "success": True,
            "content": json.dumps(outline.to_dict(), indent=2),
            "format": "json"
        }
    elif export_format == "yaml":
        return {
            "success": True,
            "content": yaml.dump(outline.to_dict(), default_flow_style=False),
            "format": "yaml"
        }
    elif export_format == "html":
        # Convert markdown to basic HTML
        md = outline.to_markdown()
        html = f"<html><body><pre>{md}</pre></body></html>"
        return {
            "success": True,
            "content": html,
            "format": "html"
        }
    
    return {
        "success": False,
        "error": f"Unknown format: {export_format}"
    }


# =============================================================================
# Tool Router
# =============================================================================

TOOL_HANDLERS = {
    "outline_generate": handle_outline_generate,
    "outline_list_frameworks": handle_outline_list_frameworks,
    "outline_apply_rules": handle_outline_apply_rules,
    "outline_analyze_source": handle_outline_analyze_source,
    "outline_export": handle_outline_export,
}


async def handle_tool_call(name: str, params: Dict) -> Dict:
    """Route tool call to appropriate handler."""
    handler = TOOL_HANDLERS.get(name)
    if handler:
        try:
            return await handler(params)
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    return {
        "success": False,
        "error": f"Unknown tool: {name}"
    }


def get_outline_tools() -> List[Dict]:
    """Get list of available outline tools."""
    return OUTLINE_TOOLS
