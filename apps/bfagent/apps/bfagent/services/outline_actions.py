"""
Outline Generation Actions using Story Frameworks

Provides actions for generating structured outlines based on proven story frameworks.
These actions are used by the Outline Agent in the enrichment system.
"""

from typing import Dict, List, Any, Optional
from .story_frameworks import (
    get_framework,
    list_frameworks,
    STORY_FRAMEWORKS
)


def handle_outline_action(
    action: str,
    project: Any,
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Handle outline generation actions
    
    Args:
        action: Action name (e.g., 'generate_heros_journey_outline')
        project: BookProjects instance
        context: Additional context
        
    Returns:
        List of enrichment results
    """
    
    # Map actions to handlers
    action_handlers = {
        'generate_heros_journey_outline': _generate_heros_journey,
        'generate_save_the_cat_outline': _generate_save_the_cat,
        'generate_three_act_outline': _generate_three_act,
        'analyze_story_structure': _analyze_structure,
        'suggest_story_beats': _suggest_beats,
    }
    
    handler = action_handlers.get(action)
    if handler:
        return handler(project, context)
    
    return [{
        'field_name': 'outline',
        'new_value': f"Unknown outline action: {action}",
        'confidence': 0.0,
        'rationale': f"Action '{action}' not found"
    }]


def _generate_heros_journey(project: Any, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate outline based on Hero's Journey"""
    framework = get_framework('heros_journey')
    
    # Determine number of chapters (default 12 for Hero's Journey)
    num_chapters = context.get('num_chapters', 12)
    
    outline_lines = []
    outline_lines.append(f"# {project.title} - Story Outline")
    outline_lines.append(f"**Framework:** Hero's Journey (Heldenreise)")
    outline_lines.append(f"**Genre:** {project.genre or 'Not specified'}")
    outline_lines.append("")
    outline_lines.append("---")
    outline_lines.append("")
    
    for i in range(1, num_chapters + 1):
        position = i / num_chapters
        beat = framework.get_beat_for_position(position)
        
        outline_lines.append(f"## Chapter {i}: {beat.name}")
        outline_lines.append(f"**Story Position:** {position:.0%} through the story")
        outline_lines.append(f"**Beat Description:** {beat.description}")
        outline_lines.append(f"**Chapter Focus:** {beat.chapter_guidance}")
        outline_lines.append(f"**Emotional Arc:** {beat.emotional_arc}")
        outline_lines.append("")
        
        # Add brief suggestion based on project info
        if project.story_premise:
            outline_lines.append(f"*Suggestion: Connect '{beat.name}' to your premise: {project.story_premise[:100]}...*")
            outline_lines.append("")
    
    outline = "\n".join(outline_lines)
    
    return [{
        'field_name': 'description',  # Using description field until outline field is added
        'new_value': outline,
        'confidence': 0.95,
        'rationale': f"Generated structured outline using Hero's Journey framework with {num_chapters} chapters",
        'metadata': {
            'framework': 'heros_journey',
            'num_chapters': num_chapters,
            'beats_used': len(framework.beats),
            'target_field': 'description'  # Track which field we're targeting
        }
    }]


def _generate_save_the_cat(project: Any, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate outline based on Save the Cat Beat Sheet"""
    framework = get_framework('save_the_cat')
    
    num_chapters = context.get('num_chapters', 15)
    
    outline_lines = []
    outline_lines.append(f"# {project.title} - Story Outline")
    outline_lines.append(f"**Framework:** Save the Cat Beat Sheet")
    outline_lines.append(f"**Genre:** {project.genre or 'Not specified'}")
    outline_lines.append("")
    outline_lines.append("---")
    outline_lines.append("")
    
    for i in range(1, num_chapters + 1):
        position = i / num_chapters
        beat = framework.get_beat_for_position(position)
        
        # Add act markers
        if position <= 0.25:
            act = "ACT 1 - Setup"
        elif position <= 0.75:
            act = "ACT 2 - Confrontation"
        else:
            act = "ACT 3 - Resolution"
        
        outline_lines.append(f"## Chapter {i}: {beat.name} ({act})")
        outline_lines.append(f"**Story Position:** {position:.0%}")
        outline_lines.append(f"**Beat Description:** {beat.description}")
        outline_lines.append(f"**Chapter Focus:** {beat.chapter_guidance}")
        outline_lines.append(f"**Emotional Arc:** {beat.emotional_arc}")
        outline_lines.append("")
    
    outline = "\n".join(outline_lines)
    
    return [{
        'field_name': 'description',  # Using description field until outline field is added
        'new_value': outline,
        'confidence': 0.95,
        'rationale': f"Generated structured outline using Save the Cat framework with {num_chapters} chapters",
        'metadata': {
            'framework': 'save_the_cat',
            'num_chapters': num_chapters,
            'beats_used': len(framework.beats),
            'target_field': 'description'
        }
    }]


def _generate_three_act(project: Any, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate outline based on Three-Act Structure"""
    framework = get_framework('three_act')
    
    num_chapters = context.get('num_chapters', 9)
    
    outline_lines = []
    outline_lines.append(f"# {project.title} - Story Outline")
    outline_lines.append(f"**Framework:** Drei-Akt-Struktur")
    outline_lines.append(f"**Genre:** {project.genre or 'Not specified'}")
    outline_lines.append("")
    outline_lines.append("---")
    outline_lines.append("")
    
    # Three-Act percentages
    act1_end = int(num_chapters * 0.25)
    act2_end = int(num_chapters * 0.75)
    
    for i in range(1, num_chapters + 1):
        position = i / num_chapters
        beat = framework.get_beat_for_position(position)
        
        # Determine act
        if i <= act1_end:
            act = "AKT 1: Setup"
        elif i <= act2_end:
            act = "AKT 2: Konfrontation"
        else:
            act = "AKT 3: Auflösung"
        
        outline_lines.append(f"## Chapter {i}: {beat.name}")
        outline_lines.append(f"**Act:** {act}")
        outline_lines.append(f"**Story Position:** {position:.0%}")
        outline_lines.append(f"**Beat Description:** {beat.description}")
        outline_lines.append(f"**Chapter Focus:** {beat.chapter_guidance}")
        outline_lines.append(f"**Emotional Arc:** {beat.emotional_arc}")
        outline_lines.append("")
    
    outline = "\n".join(outline_lines)
    
    return [{
        'field_name': 'description',  # Using description field until outline field is added
        'new_value': outline,
        'confidence': 0.95,
        'rationale': f"Generated structured outline using Three-Act Structure with {num_chapters} chapters",
        'metadata': {
            'framework': 'three_act',
            'num_chapters': num_chapters,
            'beats_used': len(framework.beats),
            'target_field': 'description'
        }
    }]


def _analyze_structure(project: Any, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze existing story structure"""
    
    analysis_lines = []
    analysis_lines.append(f"# Story Structure Analysis: {project.title}")
    analysis_lines.append("")
    analysis_lines.append("## Available Frameworks")
    analysis_lines.append("")
    
    for fw_id, framework in STORY_FRAMEWORKS.items():
        analysis_lines.append(f"### {framework.name}")
        analysis_lines.append(f"- **Description:** {framework.description}")
        analysis_lines.append(f"- **Number of Beats:** {len(framework.beats)}")
        analysis_lines.append(f"- **Best For:** {_get_framework_recommendation(fw_id, project.genre)}")
        analysis_lines.append("")
    
    analysis_lines.append("## Recommendation")
    analysis_lines.append("")
    recommendation = _recommend_framework(project)
    analysis_lines.append(recommendation)
    
    analysis = "\n".join(analysis_lines)
    
    return [{
        'field_name': 'story_structure_analysis',
        'new_value': analysis,
        'confidence': 0.90,
        'rationale': "Analyzed story structure and recommended best framework",
        'metadata': {
            'frameworks_analyzed': len(STORY_FRAMEWORKS)
        }
    }]


def _suggest_beats(project: Any, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Suggest key story beats based on project"""
    
    # Use Hero's Journey as default for suggestions
    framework = get_framework('heros_journey')
    
    suggestions = []
    suggestions.append(f"# Key Story Beats for {project.title}")
    suggestions.append("")
    suggestions.append("Based on your project details, here are suggested key beats:")
    suggestions.append("")
    
    # Key beats every story should have
    key_positions = [0.0, 0.25, 0.50, 0.75, 1.0]
    
    for pos in key_positions:
        beat = framework.get_beat_for_position(pos)
        suggestions.append(f"## {beat.name} (at {pos:.0%})")
        suggestions.append(f"**Focus:** {beat.chapter_guidance}")
        suggestions.append(f"**Emotional Arc:** {beat.emotional_arc}")
        suggestions.append("")
        
        # Add specific suggestions based on project
        if pos == 0.0 and project.protagonist_concept:
            suggestions.append(f"*For your protagonist ({project.protagonist_concept}): Establish their normal world and what they want/need.*")
        elif pos == 0.50 and project.main_conflict:
            suggestions.append(f"*For your main conflict ({project.main_conflict}): This is the midpoint - escalate everything!*")
        elif pos == 1.0 and project.stakes:
            suggestions.append(f"*For your stakes ({project.stakes}): Show how the hero's journey has changed them.*")
        suggestions.append("")
    
    result = "\n".join(suggestions)
    
    return [{
        'field_name': 'story_beats_suggestion',
        'new_value': result,
        'confidence': 0.85,
        'rationale': "Suggested key story beats based on proven framework",
        'metadata': {
            'framework_used': 'heros_journey',
            'key_beats': len(key_positions)
        }
    }]


def _get_framework_recommendation(framework_id: str, genre: Optional[str]) -> str:
    """Get recommendation for when to use a framework"""
    recommendations = {
        'heros_journey': "Fantasy, Adventure, Coming-of-Age, Quest Stories",
        'save_the_cat': "Thrillers, Rom-Coms, Action, Commercial Fiction",
        'three_act': "Literary Fiction, Drama, Any Genre (versatile)"
    }
    return recommendations.get(framework_id, "All genres")


def _recommend_framework(project: Any) -> str:
    """Recommend best framework for project"""
    genre = (project.genre or '').lower()
    
    if any(g in genre for g in ['fantasy', 'adventure', 'sci-fi', 'science fiction']):
        return """**Recommended: Hero's Journey**

Your genre suggests an adventure or quest narrative. Hero's Journey provides excellent structure for:
- Character transformation arcs
- Quest narratives
- World-building integration
- Epic scope stories

Ideal for 12-15 chapters."""
    
    elif any(g in genre for g in ['thriller', 'mystery', 'romance', 'contemporary']):
        return """**Recommended: Save the Cat**

Your genre benefits from tight pacing and clear emotional beats. Save the Cat excels at:
- Page-turner pacing
- Clear character arcs
- Commercial appeal
- Emotional resonance

Ideal for 15 chapters."""
    
    else:
        return """**Recommended: Three-Act Structure**

A versatile choice that works for all genres. Three-Act Structure provides:
- Classic dramatic structure
- Clear beginning, middle, end
- Flexible beat timing
- Literary respectability

Ideal for 9-12 chapters."""


# Export available actions
OUTLINE_ACTIONS = {
    'generate_heros_journey_outline': {
        'label': "Generate Hero's Journey Outline",
        'description': "Create structured 12-chapter outline using Hero's Journey framework",
        'icon': 'compass'
    },
    'generate_save_the_cat_outline': {
        'label': "Generate Save the Cat Outline",
        'description': "Create structured 15-chapter outline using Save the Cat Beat Sheet",
        'icon': 'film'
    },
    'generate_three_act_outline': {
        'label': "Generate Three-Act Outline",
        'description': "Create structured outline using classic Three-Act Structure",
        'icon': 'layout-three-columns'
    },
    'analyze_story_structure': {
        'label': "Analyze Story Structure",
        'description': "Analyze project and recommend best framework",
        'icon': 'search'
    },
    'suggest_story_beats': {
        'label': "Suggest Key Story Beats",
        'description': "Get suggestions for key story beats based on project",
        'icon': 'lightbulb'
    },
}
