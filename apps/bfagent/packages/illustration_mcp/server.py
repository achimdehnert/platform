"""
Illustration MCP Server
=======================

MCP Server for AI-powered book illustration generation using ComfyUI.

Tools:
- generate_chapter_illustration: Generate illustration for a chapter scene
- generate_character_portrait: Generate character portrait with consistent style
- batch_generate_chapter: Generate all illustrations for a chapter
- get_project_style: Get illustration style settings for a project
- check_comfyui_status: Check ComfyUI connection and GPU status
- list_available_styles: List all available style presets
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from decimal import Decimal

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("illustration_mcp")

# Django setup
def setup_django():
    """Initialize Django settings"""
    project_root = os.environ.get("BFAGENT_PROJECT_ROOT", "/home/dehnert/github/bfagent")
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    
    import django
    django.setup()

# Initialize Django
try:
    setup_django()
    DJANGO_AVAILABLE = True
except Exception as e:
    logger.warning(f"Django setup failed: {e}")
    DJANGO_AVAILABLE = False


# =============================================================================
# ILLUSTRATION TOOLS
# =============================================================================

async def check_comfyui_status() -> Dict[str, Any]:
    """Check ComfyUI connection and system status"""
    try:
        from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
        
        handler = ComfyUIHandler()
        is_connected = await handler.check_connection()
        
        if not is_connected:
            return {
                "connected": False,
                "error": "ComfyUI nicht erreichbar. Bitte starten: cd ~/ai-tools/ComfyUI && python main.py --listen 0.0.0.0 --port 8181",
                "url": handler.base_url
            }
        
        stats = await handler.get_system_stats()
        models = handler.get_installed_models()
        
        return {
            "connected": True,
            "url": handler.base_url,
            "models_installed": models,
            "model_count": len(models),
            "system_stats": stats,
            "style_presets": list(handler.STYLE_PRESETS.keys())
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


def list_available_styles() -> Dict[str, Any]:
    """List all available illustration style presets"""
    try:
        from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
        from apps.writing_hub.models import IllustrationStyle
        
        handler = ComfyUIHandler()
        
        # ComfyUI presets
        comfy_presets = []
        for name, preset in handler.STYLE_PRESETS.items():
            comfy_presets.append({
                "name": name,
                "cfg": preset.get("cfg", 7.5),
                "steps": preset.get("steps", 25),
                "description": preset.get("positive_suffix", "")[:100]
            })
        
        # Genre presets from model
        genre_presets = []
        for genre in ["fantasy", "sci-fi", "krimi", "kinderbuch", "roman", "horror"]:
            preset = IllustrationStyle.get_preset_for_genre(genre)
            genre_presets.append({
                "genre": genre,
                "style_type": preset["style_type"],
                "style_name": preset["style_name"],
                "base_prompt": preset["base_prompt"][:100] + "..."
            })
        
        return {
            "comfy_presets": comfy_presets,
            "genre_presets": genre_presets,
            "style_types": [
                {"value": choice[0], "label": choice[1]} 
                for choice in IllustrationStyle.StyleType.choices
            ]
        }
    except Exception as e:
        return {"error": str(e)}


def get_project_style(project_id: int) -> Dict[str, Any]:
    """Get illustration style settings for a book project"""
    try:
        from apps.bfagent.models import BookProjects
        from apps.writing_hub.models import IllustrationStyle
        
        project = BookProjects.objects.get(id=project_id)
        
        try:
            style = project.illustration_style
            return {
                "project_id": project_id,
                "project_title": project.title,
                "has_style": True,
                "style": {
                    "id": style.id,
                    "style_type": style.style_type,
                    "style_name": style.style_name,
                    "base_prompt": style.base_prompt,
                    "negative_prompt": style.negative_prompt,
                    "color_palette": style.color_palette,
                    "provider": style.provider,
                    "quality": style.quality,
                    "image_size": style.image_size,
                    "reference_seed": style.reference_seed
                }
            }
        except IllustrationStyle.DoesNotExist:
            # Return preset based on genre
            genre = project.genre.name if hasattr(project, 'genre') and project.genre else 'fantasy'
            preset = IllustrationStyle.get_preset_for_genre(genre)
            return {
                "project_id": project_id,
                "project_title": project.title,
                "has_style": False,
                "suggested_preset": preset,
                "message": f"Kein Stil definiert. Vorschlag basierend auf Genre '{genre}'"
            }
    except Exception as e:
        return {"error": str(e)}


async def generate_chapter_illustration(
    chapter_id: int,
    scene_index: int = 0,
    scene_description: Optional[str] = None,
    style_preset: Optional[str] = None,
    width: int = 1024,
    height: int = 768
) -> Dict[str, Any]:
    """Generate illustration for a specific chapter scene"""
    try:
        from apps.bfagent.models import BookChapters
        from apps.writing_hub.models import IllustrationStyle, ChapterIllustration, ChapterSceneAnalysis
        from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
        
        chapter = BookChapters.objects.select_related('project').get(id=chapter_id)
        project = chapter.project
        
        # Get or create style
        try:
            style = project.illustration_style
        except IllustrationStyle.DoesNotExist:
            return {"error": f"Projekt {project.title} hat keinen Illustrations-Stil definiert"}
        
        # Get scene description
        if not scene_description:
            try:
                analysis = chapter.scene_analysis
                if analysis.visual_scenes and len(analysis.visual_scenes) > scene_index:
                    scene_data = analysis.visual_scenes[scene_index]
                    scene_description = scene_data.get("visual_description", "")
                else:
                    scene_description = f"Illustration for chapter {chapter.chapter_number}: {chapter.title}"
            except ChapterSceneAnalysis.DoesNotExist:
                scene_description = f"Illustration for chapter {chapter.chapter_number}: {chapter.title}"
        
        # Build full prompt
        full_prompt = style.get_full_prompt(scene_description)
        negative_prompt = style.negative_prompt
        
        # Determine ComfyUI preset
        if not style_preset:
            style_preset_map = {
                'watercolor': 'fantasy_watercolor',
                'digital_art': 'fantasy_digital',
                'manga': 'manga',
                'realistic': 'realistic',
                'cartoon': 'childrens_book',
                'oil_painting': 'fantasy_digital',
            }
            style_preset = style_preset_map.get(style.style_type, 'fantasy_watercolor')
        
        # Generate with ComfyUI
        handler = ComfyUIHandler()
        
        if not await handler.check_connection():
            return {"error": "ComfyUI nicht erreichbar. Bitte starten."}
        
        result = await handler.generate_image(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            style_preset=style_preset
        )
        
        if result.get("success"):
            # Create ChapterIllustration record
            illustration = ChapterIllustration.objects.create(
                chapter=chapter,
                position='scene',
                position_index=scene_index,
                scene_description=scene_description,
                full_prompt=full_prompt,
                seed_used=result.get("seed_used"),
                image_url=result.get("image_url", ""),
                status='completed',
                generation_time_seconds=int(result.get("generation_time", 0))
            )
            
            return {
                "success": True,
                "illustration_id": illustration.id,
                "chapter": f"Kapitel {chapter.chapter_number}: {chapter.title}",
                "scene_index": scene_index,
                "prompt_used": full_prompt[:200] + "...",
                "seed_used": result.get("seed_used"),
                "generation_time": result.get("generation_time"),
                "image_url": result.get("image_url")
            }
        else:
            return {"success": False, "error": result.get("error", "Unbekannter Fehler")}
            
    except Exception as e:
        logger.exception("Error generating illustration")
        return {"error": str(e)}


async def generate_character_portrait(
    project_id: int,
    character_name: str,
    character_description: str,
    style_preset: Optional[str] = None,
    pose: str = "portrait"
) -> Dict[str, Any]:
    """Generate a character portrait with project style"""
    try:
        from apps.bfagent.models import BookProjects
        from apps.writing_hub.models import IllustrationStyle
        from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
        
        project = BookProjects.objects.get(id=project_id)
        
        try:
            style = project.illustration_style
        except IllustrationStyle.DoesNotExist:
            return {"error": "Projekt hat keinen Illustrations-Stil"}
        
        # Build character prompt
        pose_prompts = {
            "portrait": "portrait, face close-up, detailed facial features",
            "full_body": "full body shot, standing pose, detailed clothing",
            "action": "dynamic action pose, movement, dramatic angle",
            "profile": "side profile, elegant pose"
        }
        
        pose_prompt = pose_prompts.get(pose, pose_prompts["portrait"])
        
        character_prompt = f"{character_description}, {pose_prompt}"
        full_prompt = style.get_full_prompt(character_prompt)
        
        # Determine style preset
        if not style_preset:
            style_preset_map = {
                'watercolor': 'fantasy_watercolor',
                'digital_art': 'fantasy_digital',
                'manga': 'manga',
                'realistic': 'realistic',
            }
            style_preset = style_preset_map.get(style.style_type, 'fantasy_digital')
        
        handler = ComfyUIHandler()
        
        if not await handler.check_connection():
            return {"error": "ComfyUI nicht erreichbar"}
        
        result = await handler.generate_image(
            prompt=full_prompt,
            negative_prompt=style.negative_prompt,
            width=768,
            height=1024,  # Portrait orientation
            style_preset=style_preset
        )
        
        return {
            "success": result.get("success", False),
            "character_name": character_name,
            "pose": pose,
            "prompt_used": full_prompt[:200] + "...",
            "seed_used": result.get("seed_used"),
            "generation_time": result.get("generation_time"),
            "image_url": result.get("image_url"),
            "error": result.get("error")
        }
        
    except Exception as e:
        return {"error": str(e)}


async def batch_generate_chapter(
    chapter_id: int,
    max_illustrations: int = 3
) -> Dict[str, Any]:
    """Generate multiple illustrations for a chapter based on scene analysis"""
    try:
        from apps.bfagent.models import BookChapters
        from apps.writing_hub.models import ChapterSceneAnalysis
        
        chapter = BookChapters.objects.get(id=chapter_id)
        
        try:
            analysis = chapter.scene_analysis
            scenes = analysis.visual_scenes or []
        except ChapterSceneAnalysis.DoesNotExist:
            return {
                "error": "Keine Szenen-Analyse vorhanden. Bitte zuerst Kapitel analysieren.",
                "hint": "Nutze die Illustration-Dashboard oder LLM-Analyse"
            }
        
        if not scenes:
            return {"error": "Keine visuellen Szenen in der Analyse gefunden"}
        
        # Limit scenes
        scenes_to_generate = scenes[:max_illustrations]
        
        results = []
        for i, scene in enumerate(scenes_to_generate):
            scene_desc = scene.get("visual_description", f"Scene {i+1}")
            
            result = await generate_chapter_illustration(
                chapter_id=chapter_id,
                scene_index=i,
                scene_description=scene_desc
            )
            
            results.append({
                "scene_index": i,
                "scene_title": scene.get("title", f"Szene {i+1}"),
                "success": result.get("success", False),
                "illustration_id": result.get("illustration_id"),
                "error": result.get("error")
            })
        
        successful = sum(1 for r in results if r.get("success"))
        
        return {
            "chapter": f"Kapitel {chapter.chapter_number}: {chapter.title}",
            "total_scenes": len(scenes),
            "generated": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results
        }
        
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# MCP SERVER SETUP
# =============================================================================

server = Server("illustration-mcp")

TOOLS = [
    Tool(
        name="check_comfyui_status",
        description="Check if ComfyUI is running and get system status including GPU info and installed models.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="list_available_styles",
        description="List all available illustration style presets (ComfyUI presets and genre-based presets).",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="get_project_style",
        description="Get the illustration style configuration for a book project.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Book project ID"
                }
            },
            "required": ["project_id"]
        }
    ),
    Tool(
        name="generate_chapter_illustration",
        description="Generate an illustration for a specific chapter scene using ComfyUI and the project's style settings.",
        inputSchema={
            "type": "object",
            "properties": {
                "chapter_id": {
                    "type": "integer",
                    "description": "Chapter ID"
                },
                "scene_index": {
                    "type": "integer",
                    "description": "Scene index from chapter analysis (default: 0)",
                    "default": 0
                },
                "scene_description": {
                    "type": "string",
                    "description": "Optional custom scene description (overrides analysis)"
                },
                "style_preset": {
                    "type": "string",
                    "description": "Optional ComfyUI style preset override"
                },
                "width": {
                    "type": "integer",
                    "description": "Image width (default: 1024)",
                    "default": 1024
                },
                "height": {
                    "type": "integer",
                    "description": "Image height (default: 768)",
                    "default": 768
                }
            },
            "required": ["chapter_id"]
        }
    ),
    Tool(
        name="generate_character_portrait",
        description="Generate a character portrait with the project's illustration style.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Book project ID"
                },
                "character_name": {
                    "type": "string",
                    "description": "Character name"
                },
                "character_description": {
                    "type": "string",
                    "description": "Visual description of the character"
                },
                "style_preset": {
                    "type": "string",
                    "description": "Optional style preset override"
                },
                "pose": {
                    "type": "string",
                    "description": "Pose type: portrait, full_body, action, profile",
                    "default": "portrait"
                }
            },
            "required": ["project_id", "character_name", "character_description"]
        }
    ),
    Tool(
        name="batch_generate_chapter",
        description="Generate multiple illustrations for a chapter based on its scene analysis.",
        inputSchema={
            "type": "object",
            "properties": {
                "chapter_id": {
                    "type": "integer",
                    "description": "Chapter ID"
                },
                "max_illustrations": {
                    "type": "integer",
                    "description": "Maximum number of illustrations to generate (default: 3)",
                    "default": 3
                }
            },
            "required": ["chapter_id"]
        }
    ),
]


@server.list_tools()
async def list_tools():
    """List available illustration tools"""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "check_comfyui_status":
            result = await check_comfyui_status()
        elif name == "list_available_styles":
            result = list_available_styles()
        elif name == "get_project_style":
            result = get_project_style(arguments["project_id"])
        elif name == "generate_chapter_illustration":
            result = await generate_chapter_illustration(
                chapter_id=arguments["chapter_id"],
                scene_index=arguments.get("scene_index", 0),
                scene_description=arguments.get("scene_description"),
                style_preset=arguments.get("style_preset"),
                width=arguments.get("width", 1024),
                height=arguments.get("height", 768)
            )
        elif name == "generate_character_portrait":
            result = await generate_character_portrait(
                project_id=arguments["project_id"],
                character_name=arguments["character_name"],
                character_description=arguments["character_description"],
                style_preset=arguments.get("style_preset"),
                pose=arguments.get("pose", "portrait")
            )
        elif name == "batch_generate_chapter":
            result = await batch_generate_chapter(
                chapter_id=arguments["chapter_id"],
                max_illustrations=arguments.get("max_illustrations", 3)
            )
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
    
    except Exception as e:
        logger.exception(f"Error in tool {name}")
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


async def run_server():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point"""
    logger.info("Starting Illustration MCP Server...")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
