import json
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from ..models import Agents, BookChapters, BookProjects, Llms, PlotPoint, PromptTemplate, StoryArc
from .chapter_actions import handle_chapter_action
from .chapter_context import build_enrichment_context
from .outline_actions import handle_outline_action, OUTLINE_ACTIONS


def _choose_llm(agent: Agents) -> Optional[Llms]:
    """Pick the configured LLM for the agent or fallback to any active one."""
    if agent.llm_model_id:
        try:
            return Llms.objects.get(pk=agent.llm_model_id)
        except Llms.DoesNotExist:
            pass
    # Fallback: any active provider
    return Llms.objects.filter(is_active=True).order_by("id").first()


def _build_prompt(
    project: BookProjects, agent: Agents, action: str, chapter: Optional[BookChapters] = None
) -> Dict[str, str]:
    """Compose system and user messages from project base fields for the action."""
    system = agent.system_prompt or "You are a helpful writing assistant."
    base = {
        "title": project.title,
        "genre": project.genre,
        "audience": project.target_audience,
        "premise": project.story_premise,
        "themes": project.story_themes,
        "tone": project.atmosphere_tone,
        "time": project.setting_time,
        "location": project.setting_location,
        "conflict": project.main_conflict,
        "stakes": project.stakes,
        "protagonist": project.protagonist_concept,
        "antagonist": project.antagonist_concept,
        "unique": project.unique_elements,
        "inspiration": project.inspiration_sources,
        "genre_settings": project.genre_settings,
    }
    if chapter is not None:
        base.update(
            {
                "chapter": {
                    "id": chapter.pk,
                    "number": chapter.chapter_number,
                    "title": chapter.title,
                    "summary": chapter.summary,
                    "outline": chapter.outline,
                    "notes": chapter.notes,
                    "content": chapter.content,
                }
            }
        )

    instructions = {
        "outline_from_fundamentals": "Create a concise 3-act outline using premise, themes, tone, audience and genre_settings.",
        "outline_from_world_conflict": "Draft a 3-act outline driven by world & conflict (time, location, conflict, stakes) consistent with genre_settings.",
        "outline_from_characters": "Produce a character-driven 3-act outline using protagonist and antagonist with themes and genre_settings.",
        "concepts_brainstorm": "Brainstorm unique elements and motifs; present as bullet list.",
        "expand_world_from_outline": "Expand a world bible draft referencing time, location and genre conventions.",
        "escalate_conflict_from_outline": "Create a conflict escalation ladder referencing current stakes.",
        "derive_characters_from_outline": "List cast sheet entries based on protagonist/antagonist and premise.",
        "deepen_arcs_from_outline": "Sketch character arcs for protagonist and antagonist.",
        "premise": "Improve the story premise succinctly.",
        "themes": "Suggest 3-5 thematic threads.",
        "outline": "Create a concise story outline with 3-5 chapters. Each chapter should have a clear title and 2-3 sentence summary of what happens. Focus on beginning, middle, and end structure.",
        "write_short_content": "Write a complete short story (1500-2500 words) based on the premise and outline provided. Include clear beginning, middle, and end. Use descriptive prose and maintain consistent tone. Format as a single cohesive narrative.",
        "write_everything": """Write a complete work based on the provided outline. Create a cohesive, engaging narrative with:

STRUCTURE:
- Generate 3-8 chapters based on outline
- Each chapter 800-1500 words
- Clear chapter titles
- Smooth transitions between chapters

CONTENT:
- Beginning: Introduce characters, setting, conflict
- Middle: Build tension, develop characters, advance plot
- End: Resolve conflict, satisfying conclusion
- Use vivid descriptions and authentic dialogue
- Show, don't tell
- Maintain consistent POV and tense

OUTPUT FORMAT:
#### Chapter 1: [Title]
[800-1500 words content]

#### Chapter 2: [Title]
[800-1500 words content]

Continue for all chapters. Focus on publication-ready quality.""",
        "stakes": "Clarify narrative stakes.",
        "characters": "Propose protagonist and antagonist concepts.",
        "write_chapter_draft": "Write a focused chapter draft in clean prose. Respect genre_settings, themes, tone, world constraints, and continuity. Use the provided chapter outline and prior summary if present. Aim for 800-1200 words and structured paragraphs.",
        "summarize_chapter": "Summarize the given chapter content into 5-8 bullet points capturing events, beats, and continuity hooks.",
        # PHASE 2: Chapter Agent Actions with Storyline Context
        "generate_outline": "Generate a detailed chapter outline based on the story arc, plot points, and character development. Include scene structure, key events, and emotional beats. Consider the chapter's position in the overall story progression.",
        "write_draft": "Write a complete chapter draft (800-1200 words) using the provided outline, story arc context, and character information. Maintain consistency with established tone, setting, and character voices. Include dialogue and narrative description.",
        "expand_scene": "Expand a specific scene within the chapter, adding sensory details, character emotions, and dialogue. Focus on showing rather than telling, and maintain the established mood and pacing.",
        "summarize": "Create a concise summary of the chapter content, highlighting key plot developments, character growth, and story progression. Include important dialogue or revelations.",
        "improve_prose": "Enhance the chapter's prose style, improving sentence flow, word choice, and narrative voice. Maintain the established tone while elevating the writing quality.",
        "add_dialogue": "Add or improve dialogue in the chapter, ensuring each character has a distinct voice and the conversations advance plot or character development. Include appropriate dialogue tags and action beats.",
        # Story Agent Actions
        "generate_plot_points": "Generate key plot points for the story arc, including inciting incidents, rising action beats, climax, and resolution. Consider pacing and emotional impact.",
        "analyze_pacing": "Analyze the pacing of the story arc across chapters, identifying areas that may need acceleration or deceleration. Provide specific recommendations.",
        "check_arc_consistency": "Check the story arc for consistency in character development, plot progression, and thematic elements. Identify any contradictions or gaps.",
        "suggest_arc_improvements": "Suggest improvements to the story arc structure, character development, or plot progression. Focus on enhancing dramatic tension and reader engagement.",
        "identify_plot_holes": "Identify potential plot holes or logical inconsistencies in the story arc. Provide suggestions for resolution.",
        # Book Agent Actions
        "write_complete_book": """Write a complete book based on the outline provided. Create structured chapters with the following:
- Generate 5-8 chapters with clear titles
- Each chapter should be 800-1200 words
- Follow the outline structure: beginning (setup), middle (conflict), end (resolution)
- Maintain consistent tone, style, and character voices throughout
- Include proper chapter transitions and story progression
- Ensure each chapter advances the plot and develops characters
- Use the provided genre settings, themes, and atmosphere

Output Format:
#### Chapter 1: [Title]
[Chapter content 800-1200 words]

#### Chapter 2: [Title]
[Chapter content 800-1200 words]

...""",
        # Consistency Agent Actions
        "check_consistency": "Perform a comprehensive consistency check across characters, setting, timeline, and plot elements. Identify discrepancies and provide correction suggestions.",
        "check_character_voice": "Analyze character voice consistency across chapters, ensuring each character maintains their distinct speaking patterns and personality traits.",
        "check_timeline": "Verify timeline consistency across chapters, checking for chronological errors or impossible time sequences.",
        "check_setting": "Check setting consistency, ensuring locations, descriptions, and world-building elements remain coherent across chapters.",
        "calculate_score": "Calculate an overall consistency score based on character voice, timeline, setting, and plot coherence. Provide a detailed breakdown.",
        # Character Agent Actions
        "generate_character_cast": """Generate a complete character cast for the story. Create EXACTLY 9 characters with the following distribution:
- 2 Protagonists (main heroes driving the story)
- 1 Antagonist (main villain or opposing force)
- 4 Supporting Characters (important secondary characters)
- 2 Minor Characters (smaller roles but memorable)

For each character provide:
- Full name (first and last name, appropriate to genre/setting)
- Age (specific number, not range)
- Detailed description of personality and appearance
- Rich background/backstory
- Clear motivation
- Personality traits
- Character development arc

Ensure characters are diverse, well-developed, and fit the story's genre, tone, and setting.""",
        # Prompt Agent Actions (Meta-Agent for Template Generation)
        "generate_prompt_template": "You are a prompt engineering expert. Generate an optimal, reusable prompt template in JSON format with: template_text (with {{variables}}), system_prompt, user_prompt_template, variables array, usage_guidelines, and quality_checklist. Consider the target agent type, purpose, and specific requirements.",
        "optimize_existing_template": "Analyze and improve an existing prompt template. Enhance clarity, effectiveness, and specificity. Provide the optimized template in JSON format with improvement rationale.",
        "analyze_template_quality": "Evaluate a prompt template's quality, clarity, and effectiveness. Provide a detailed quality score (0-10) and specific improvement recommendations.",
        "generate_template_variations": "Create 3-5 variations of a prompt template for A/B testing. Each variation should have different approaches or emphasis while maintaining the core purpose.",
    }.get(action, "Provide helpful narrative suggestions.")

    user = json.dumps({"action": action, "context": base}, ensure_ascii=False)
    return {"system": system, "user": f"{instructions}\n\nContext JSON:\n{user}"}


def _target_field_for_action(action: str) -> str:
    mapping = {
        "premise": "story_premise",
        "themes": "story_themes",
        "outline": "description",  # Story outline goes to description
        "write_short_content": "description",  # Short story content goes to description
        "write_everything": "description",  # Complete work - but creates chapters
        "stakes": "stakes",
        "characters": "description",
        "outline_from_fundamentals": "description",
        "outline_from_world_conflict": "description",
        "outline_from_characters": "description",
        "concepts_brainstorm": "unique_elements",
        "expand_world_from_outline": "description",
        "escalate_conflict_from_outline": "stakes",
        "derive_characters_from_outline": "description",
        "deepen_arcs_from_outline": "description",
        # PHASE 2: Chapter Agent Actions - Target chapter fields
        "generate_outline": "outline",  # BookChapters.outline
        "write_draft": "content",  # BookChapters.content
        "expand_scene": "content",  # BookChapters.content
        "summarize": "summary",  # BookChapters.summary
        "improve_prose": "content",  # BookChapters.content
        "add_dialogue": "content",  # BookChapters.content
        # Story Agent Actions - Target story arc fields
        "generate_plot_points": "description",  # StoryArc.description
        "analyze_pacing": "description",  # StoryArc.description
        "check_arc_consistency": "description",  # StoryArc.description
        "suggest_arc_improvements": "description",  # StoryArc.description
        "identify_plot_holes": "description",  # StoryArc.description
        # Consistency Agent Actions - Target metadata fields
        "check_consistency": "ai_suggestions",  # BookChapters.ai_suggestions
        "check_character_voice": "ai_suggestions",  # BookChapters.ai_suggestions
        "check_timeline": "ai_suggestions",  # BookChapters.ai_suggestions
        "check_setting": "ai_suggestions",  # BookChapters.ai_suggestions
        "calculate_score": "consistency_score",  # BookChapters.consistency_score
        # Prompt Agent Actions - Create PromptTemplate objects
        "generate_prompt_template": "prompt_template",  # Creates PromptTemplate
        "optimize_existing_template": "prompt_template",  # Updates PromptTemplate
        "analyze_template_quality": "description",  # Returns analysis
        "generate_template_variations": "prompt_template",  # Creates multiple PromptTemplates
    }
    return mapping.get(action, "unique_elements")


class LLMServiceWrapper:
    """Wrapper for LLM service to work with chapter_actions handlers"""

    def __init__(self, llm: Llms):
        self.llm = llm

    def generate(self, prompt: str, max_tokens: int = 800) -> str:
        """Generate text from prompt"""
        return _call_openai_chat(
            api_endpoint=self.llm.api_endpoint,
            api_key=self.llm.api_key,
            model=self.llm.llm_name,
            system="You are an expert creative writing assistant.",
            user=prompt,
            temperature=self.llm.temperature or 0.7,
            max_tokens=max_tokens,
        )


def _call_openai_chat_structured(
    api_endpoint: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    json_schema: dict,
    max_tokens: int = 2000,
) -> str:
    """Call OpenAI-compatible API with structured output (JSON Schema).
    Uses response_format to enforce JSON schema compliance.
    """
    url = api_endpoint.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/v1/chat/completions" if "/v1/" not in url else f"{url}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": float(temperature or 0.7),
        "max_tokens": max_tokens,
        "response_format": {"type": "json_schema", "json_schema": json_schema},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
            obj = json.loads(body)
            choices = obj.get("choices") or []
            if not choices:
                print("⚠️  LLM returned no choices")
                return ""
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            print(f"✅ LLM STRUCTURED OUTPUT: {len(content)} chars returned")
            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        print(f"❌ LLM HTTPError {e.code}: {error_body}")
        raise


def _call_openai_chat(
    api_endpoint: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int = 800,
) -> str:
    """Minimal HTTP call to OpenAI-compatible Chat Completions API.
    Supports standard v1 endpoints or proxies with same contract.
    """
    url = api_endpoint.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/v1/chat/completions" if "/v1/" not in url else f"{url}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": float(temperature or 0.7),
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            obj = json.loads(body)
            choices = obj.get("choices") or []
            if not choices:
                print("⚠️  LLM returned no choices")
                return ""
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            print(f"✅ LLM SUCCESS: {len(content)} chars returned")
            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        print(f"❌ LLM HTTPError {e.code}: {error_body}")
        raise  # Re-raise instead of silent return
    except urllib.error.URLError as e:
        print(f"❌ LLM URLError: {str(e)}")
        raise
    except TimeoutError as e:
        print(f"❌ LLM Timeout after 60s")
        raise
    except Exception as e:
        print(f"❌ LLM Unexpected error: {str(e)}")
        raise


def _call_llm(
    llm: Llms,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """
    Wrapper function to call LLM with simplified interface.
    
    Args:
        llm: Llms model instance
        system_prompt: System message
        user_message: User message
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
    
    Returns:
        LLM response text
    """
    return _call_openai_chat(
        api_endpoint=llm.api_endpoint,
        api_key=llm.api_key,
        model=llm.llm_name,
        system=system_prompt,
        user=user_message,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _build_enhanced_context(
    project: BookProjects,
    chapter: Optional[BookChapters] = None,
    story_arc: Optional[StoryArc] = None,
    plot_point: Optional[PlotPoint] = None,
) -> Dict[str, any]:
    """Build enhanced context with storyline data for Chapter/Story agents"""
    context = {
        "project": {
            "title": project.title,
            "genre": project.genre,
            "audience": project.target_audience,
            "premise": project.story_premise,
            "themes": project.story_themes,
            "tone": project.atmosphere_tone,
            "setting_time": project.setting_time,
            "setting_location": project.setting_location,
            "conflict": project.main_conflict,
            "stakes": project.stakes,
            "protagonist": project.protagonist_concept,
            "antagonist": project.antagonist_concept,
        }
    }

    if chapter:
        context["chapter"] = {
            "id": chapter.pk,
            "number": chapter.chapter_number,
            "title": chapter.title,
            "summary": chapter.summary,
            "outline": chapter.outline,
            "content": chapter.content,
            "writing_stage": chapter.writing_stage,
            "mood_tone": chapter.mood_tone,
            "setting_location": chapter.setting_location,
            "time_period": chapter.time_period,
            "character_arcs": chapter.character_arcs,
            "word_count": chapter.word_count,
            "target_word_count": chapter.target_word_count,
        }

        # Add story arc context if chapter has one
        if chapter.story_arc:
            context["story_arc"] = {
                "name": chapter.story_arc.name,
                "description": chapter.story_arc.description,
                "arc_type": chapter.story_arc.arc_type,
                "central_conflict": chapter.story_arc.central_conflict,
                "importance_level": chapter.story_arc.importance_level,
            }

        # Add plot points if chapter has them
        if chapter.plot_points.exists():
            context["plot_points"] = [
                {
                    "name": pp.name,
                    "description": pp.description,
                    "point_type": pp.point_type,
                    "emotional_impact": pp.emotional_impact,
                    "sequence_order": pp.sequence_order,
                }
                for pp in chapter.plot_points.all()
            ]

        # Add featured characters if chapter has them
        if chapter.featured_characters.exists():
            context["featured_characters"] = [
                {
                    "name": char.name,
                    "description": char.description,
                    "character_type": getattr(char, "character_type", "main"),
                }
                for char in chapter.featured_characters.all()
            ]

    if story_arc:
        context["story_arc"] = {
            "name": story_arc.name,
            "description": story_arc.description,
            "arc_type": story_arc.arc_type,
            "start_chapter": story_arc.start_chapter,
            "end_chapter": story_arc.end_chapter,
            "central_conflict": story_arc.central_conflict,
            "resolution": story_arc.resolution,
            "importance_level": story_arc.importance_level,
        }

    if plot_point:
        context["plot_point"] = {
            "name": plot_point.name,
            "description": plot_point.description,
            "point_type": plot_point.point_type,
            "emotional_impact": plot_point.emotional_impact,
            "chapter_number": plot_point.chapter_number,
            "sequence_order": plot_point.sequence_order,
        }

    return context


def run_enrichment(
    project: BookProjects,
    agent: Agents,
    action: str,
    chapter: Optional[BookChapters] = None,
    plot_point: Optional[PlotPoint] = None,
    story_arc: Optional[StoryArc] = None,
    template_id: Optional[int] = None,
    edited_template_text: Optional[str] = None,
    edited_system_prompt: Optional[str] = None,
    context: Optional[str] = None,
    requirements: Optional[str] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """Run enrichment with enhanced storyline context for Chapter/Story agents.

    PHASE 2: Enhanced with storyline-aware context building for:
    - Chapter Agent: Uses chapter, story_arc, plot_points, featured_characters
    - Story Agent: Uses story_arc, related chapters, plot progression
    - Consistency Agent: Cross-references multiple chapters and arcs

    Returns enrichment results with proper field targeting for each agent type.

    PHASE 2: Enhanced with Chapter Writing System AI Integration
    - Supports chapter_agent, story_agent, consistency_agent actions
    - Uses comprehensive context from storyline integration

    Returns: {"suggestions": [{field_name, new_value, confidence, rationale}]}
    """
    base_rationale = f"Suggested by {agent.name} ({agent.agent_type}) for action '{action}'."

    # PHASE 2A: Handle Outline Actions (Story Frameworks)
    outline_action_names = list(OUTLINE_ACTIONS.keys())
    
    if action in outline_action_names and agent.agent_type == "outline_agent":
        try:
            results = handle_outline_action(
                action=action,
                project=project,
                context={
                    'num_chapters': context.get('num_chapters', 12) if context else 12,
                    'requirements': requirements
                }
            )
            return {"suggestions": results}
        except Exception as e:
            print(f"❌ ERROR in outline action: {str(e)}")
            # Continue to fallback enrichment
    
    # PHASE 2B: Handle Chapter Writing System actions
    chapter_actions = [
        "generate_outline",
        "write_draft",
        "expand_scene",
        "summarize",
        "improve_prose",
        "add_dialogue",
    ]

    if action in chapter_actions and agent.agent_type == "chapter_agent":
        # Build comprehensive context
        context = build_enrichment_context(
            project=project, chapter=chapter, plot_point=plot_point, story_arc=story_arc
        )

        # Get LLM service (wrapped for compatibility)
        llm = _choose_llm(agent)
        if llm and llm.is_active:
            llm_service = LLMServiceWrapper(llm)
            try:
                results = handle_chapter_action(action, context, llm_service)
                # Convert to standard format
                for result in results:
                    result["rationale"] = result.get("rationale", base_rationale)
                    if chapter:
                        result["target_model"] = "chapter"
                        result["target_id"] = chapter.pk
                return {"suggestions": results}
            except Exception:
                # Fallback on error - continue to standard enrichment
                print(f"❌ ERROR: {str(e)}")
                print(f"   Falling back to standard enrichment for action '{action}'")

    # PHASE 3: Prompt Agent - Meta-prompting capabilities
    prompt_agent_actions = [
        "generate_prompt_template",
        "optimize_existing_template",
        "analyze_template_quality",
        "generate_template_variations",
    ]

    print(f"\n{'#'*70}")
    print(f"🔍 run_enrichment() START")
    print(f"   Agent: {agent.name} (type={agent.agent_type})")
    print(f"   Action: {action}")
    print(f"   Template ID: {template_id}")
    print(f"   Is prompt_agent action? {action in prompt_agent_actions}")
    print(f"   Is prompt_agent type? {agent.agent_type == 'prompt_agent'}")
    print(
        f"   Will enter prompt_agent block? {action in prompt_agent_actions and agent.agent_type == 'prompt_agent'}"
    )
    print(f"{'#'*70}\n")

    if action in prompt_agent_actions and agent.agent_type == "prompt_agent":
        print("✅ ENTERING Prompt Agent block...")
        llm = _choose_llm(agent)
        if llm and llm.is_active and llm.api_key and llm.api_endpoint and llm.llm_name:
            # Build enhanced context for prompt generation
            meta_context = {
                "action": action,
                "project": {
                    "title": project.title,
                    "genre": project.genre,
                    "premise": project.story_premise,
                },
            }

            msgs = _build_prompt(project, agent, action, chapter=None)

            # If optimizing/analyzing an existing template, include it in the prompt
            # PRIORITY: Use user-edited values if available, otherwise DB values
            if template_id and action in ["optimize_existing_template", "analyze_template_quality"]:
                try:
                    original_template = PromptTemplate.objects.get(pk=template_id)

                    # Use edited values if provided by user, otherwise use DB values
                    template_text_to_use = (
                        edited_template_text
                        if edited_template_text
                        else original_template.template_text
                    )
                    system_prompt_to_use = edited_system_prompt if edited_system_prompt else ""

                    # If no edited system prompt, try to extract from DB
                    if not system_prompt_to_use and original_template.description:
                        try:
                            metadata = json.loads(original_template.description)
                            system_prompt_to_use = metadata.get("system_prompt", "")
                        except json.JSONDecodeError:
                            pass

                    msgs["user"] += f"\n\n**ORIGINAL TEMPLATE TO OPTIMIZE:**\n"
                    msgs["user"] += f"Name: {original_template.name}\n"
                    msgs["user"] += f"Version: {original_template.version}\n"
                    if system_prompt_to_use:
                        msgs["user"] += f"System Prompt:\n{system_prompt_to_use}\n\n"
                    msgs["user"] += f"Template Text:\n{template_text_to_use}\n"

                    print(
                        f"📝 DEBUG: Using template_text={'EDITED' if edited_template_text else 'DB'}, system_prompt={'EDITED' if edited_system_prompt else 'DB'}"
                    )
                except PromptTemplate.DoesNotExist:
                    print("⚠️  Original template not found!")
                    pass

            print(f"\n🔄 Calling LLM...")
            print(f"   Endpoint: {llm.api_endpoint}")
            print(f"   Model: {llm.llm_name}")
            print(f"   System prompt length: {len(msgs['system'])}")
            print(f"   User prompt length: {len(msgs['user'])}")

            try:
                content = _call_openai_chat(
                    api_endpoint=llm.api_endpoint,
                    api_key=llm.api_key,
                    model=llm.llm_name,
                    system=msgs["system"],
                    user=msgs["user"],
                    temperature=0.3,  # Lower temperature for more focused/structured output
                    max_tokens=1500,  # More tokens for detailed templates
                )
                print(f"✅ LLM returned {len(content) if content else 0} characters")
            except Exception as llm_error:
                print(f"❌ LLM Call failed: {str(llm_error)}")
                import traceback

                traceback.print_exc()
                raise

            if content:
                # Try to parse JSON response
                # LLM often wraps JSON in markdown code blocks or adds explanations
                import re

                # Try to extract JSON from markdown code blocks
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
                if not json_match:
                    json_match = re.search(r"```\s*(\{.*?\})\s*```", content, re.DOTALL)

                if json_match:
                    json_str = json_match.group(1)
                    print(f"✅ Extracted JSON from markdown code block")
                else:
                    # Try to find JSON object in text
                    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        print(f"✅ Extracted JSON object from text")
                    else:
                        json_str = content
                        print(f"⚠️  Using full content as JSON")

                try:
                    template_data = json.loads(json_str)

                    # DEBUG: Log which action we're handling
                    print(f"\n{'='*60}")
                    print(f"🔍 DEBUG: Parsed JSON successfully")
                    print(f"   Action: '{action}'")
                    print(f"   Template ID: {template_id}")
                    print(f"   Agent Type: {agent.agent_type}")
                    print(f"{'='*60}\n")

                    if action == "generate_prompt_template":
                        print("➡️  ENTERING: generate_prompt_template block")
                        # Create new PromptTemplate
                        # Extract data from LLM response
                        name = template_data.get("name", "Generated Template")
                        template_text = template_data.get("template_text", content)

                        # Store additional metadata in description as JSON
                        metadata = {
                            "system_prompt": template_data.get("system_prompt", ""),
                            "variables": template_data.get("variables", []),
                            "usage_guidelines": template_data.get("usage_guidelines", ""),
                        }

                        # Create the template (only use fields that exist in model)
                        prompt_template = PromptTemplate.objects.create(
                            name=name,
                            agent=agent,
                            template_text=template_text,
                            description=json.dumps(metadata, indent=2),
                            version=1,
                        )

                        return {
                            "suggestions": [
                                {
                                    "field_name": "prompt_template",
                                    "new_value": f"Created PromptTemplate: {prompt_template.name} (ID: {prompt_template.id})",
                                    "confidence": "0.85",
                                    "rationale": f"Generated new prompt template via {agent.name}",
                                    "template_id": prompt_template.id,
                                    "creates_object": True,
                                    "target_model": "prompttemplate",
                                }
                            ]
                        }

                    elif action == "optimize_existing_template":
                        print("➡️  ENTERING: optimize_existing_template block")
                        # Optimize an existing template - create new version
                        # Get the original template from template_id parameter
                        original_template_id = template_id

                        # Extract optimized template data
                        optimized_name = template_data.get("name", "Optimized Template")

                        # Try multiple keys where LLM might put the optimized template
                        optimized_text = (
                            template_data.get("optimized_prompt_template")
                            or template_data.get("template_text")
                            or template_data.get("prompt", {}).get("template_text")
                            or template_data.get("template", {}).get("prompt")
                        )

                        # If we got a dict/object, try to serialize it as readable text
                        if isinstance(optimized_text, dict):
                            optimized_text = json.dumps(optimized_text, indent=2)
                        elif not optimized_text:
                            optimized_text = content  # Fallback to full content

                        # Get original template version and find next available version
                        original_version = 1
                        orig_template_name = "Template"
                        next_version = 2  # Default for first optimization

                        if original_template_id:
                            try:
                                orig_template = PromptTemplate.objects.get(pk=original_template_id)
                                original_version = orig_template.version
                                orig_template_name = orig_template.name

                                # Find the highest existing version for this agent+name combo
                                from django.db.models import Max

                                base_name = f"{orig_template.name} (Optimized"
                                existing_templates = PromptTemplate.objects.filter(
                                    agent=agent, name__startswith=base_name
                                )
                                max_version = existing_templates.aggregate(Max("version"))[
                                    "version__max"
                                ]

                                # Next version is either max_version + 1, or original_version + 1 if no optimized versions exist
                                if max_version is not None:
                                    next_version = max_version + 1
                                else:
                                    next_version = original_version + 1

                                optimized_name = f"{orig_template.name} (Optimized v{next_version})"
                                print(
                                    f"📊 Version calc: orig={original_version}, max_existing={max_version}, next={next_version}"
                                )
                            except PromptTemplate.DoesNotExist:
                                print("⚠️  Original template not found, using defaults")
                                pass

                        # Store optimization metadata
                        metadata = {
                            "system_prompt": template_data.get("system_prompt", ""),
                            "variables": template_data.get("variables", []),
                            "improvements": template_data.get("improvements", ""),
                            "original_version": original_version,
                        }

                        # Create new optimized version with calculated next_version
                        optimized_template = PromptTemplate.objects.create(
                            name=optimized_name,
                            agent=agent,
                            template_text=optimized_text,
                            description=json.dumps(metadata, indent=2),
                            version=next_version,
                        )

                        return {
                            "suggestions": [
                                {
                                    "field_name": "prompt_template",
                                    "new_value": f"Optimized Template: {optimized_template.name} (v{optimized_template.version})",
                                    "confidence": "0.88",
                                    "rationale": f"Optimized existing template via {agent.name}",
                                    "template_id": optimized_template.id,
                                    "creates_object": True,
                                    "target_model": "prompttemplate",
                                }
                            ]
                        }

                    elif action == "analyze_template_quality":
                        print("➡️  ENTERING: analyze_template_quality block")
                        # Return quality analysis
                        return {
                            "suggestions": [
                                {
                                    "field_name": "description",
                                    "new_value": content,
                                    "confidence": "0.90",
                                    "rationale": f"Template quality analysis by {agent.name}",
                                }
                            ]
                        }

                    # If we got here with valid JSON but unknown action, return raw
                    # This ensures we return something instead of falling through
                    print(f"⚠️  FALLBACK: Unknown action '{action}' with valid JSON - returning raw")
                    return {
                        "suggestions": [
                            {
                                "field_name": "description",
                                "new_value": content,
                                "confidence": "0.80",
                                "rationale": f"Prompt Agent output for {action}",
                            }
                        ]
                    }

                except json.JSONDecodeError as e:
                    # If JSON parsing fails, return raw content
                    print(f"❌ JSONDecodeError: {str(e)}")
                    print(f"   Content preview: {content[:200]}...")
                    return {
                        "suggestions": [
                            {
                                "field_name": "description",
                                "new_value": content,
                                "confidence": "0.75",
                                "rationale": f"Prompt template suggestion by {agent.name} (raw output)",
                            }
                        ]
                    }

    # Try real LLM call first
    llm = _choose_llm(agent)
    if llm and llm.is_active and llm.api_key and llm.api_endpoint and llm.llm_name:
        msgs = _build_prompt(project, agent, action, chapter=chapter)

        # Use structured output for character cast generation
        if action == "generate_character_cast":
            from ..schemas.character_json_schema import CHARACTER_CAST_JSON_SCHEMA

            print("🎯 Using STRUCTURED OUTPUT for character_cast")
            content = _call_openai_chat_structured(
                api_endpoint=llm.api_endpoint,
                api_key=llm.api_key,
                model=llm.llm_name,
                system=msgs["system"],
                user=msgs["user"],
                temperature=llm.temperature or 0.7,
                json_schema=CHARACTER_CAST_JSON_SCHEMA,
                max_tokens=3000,
            )
        else:
            content = _call_openai_chat(
                api_endpoint=llm.api_endpoint,
                api_key=llm.api_key,
                model=llm.llm_name,
                system=msgs["system"],
                user=msgs["user"],
                temperature=llm.temperature or 0.7,
            )

        if content:
            # Chapter-targeted actions
            if action in ("write_chapter_draft", "summarize_chapter") and chapter is not None:
                field = "content" if action == "write_chapter_draft" else "summary"
                return {
                    "suggestions": [
                        {
                            "field_name": field,
                            "new_value": content,
                            "confidence": "0.80",
                            "rationale": base_rationale,
                            "target_model": "chapter",
                            "target_id": chapter.pk,
                        }
                    ]
                }
            # Special handling for character cast generation
            if action == "generate_character_cast":
                return {
                    "suggestions": [
                        {
                            "field_name": "character_cast",
                            "new_value": content,
                            "confidence": "0.80",
                            "rationale": base_rationale,
                            "creates_multiple": True,
                            "target_model": "characters",
                        }
                    ]
                }

            # Special handling for world collection generation
            if action == "generate_world_collection":
                return {
                    "suggestions": [
                        {
                            "field_name": "world_collection",
                            "new_value": content,
                            "confidence": "0.85",
                            "rationale": "World collection generation creates multiple interconnected worlds with detailed settings",
                            "creates_multiple": True,
                            "target_model": "worlds",
                        }
                    ]
                }

            # Special handling for complete book generation
            if action == "write_complete_book" or action == "write_everything":
                return {
                    "suggestions": [
                        {
                            "field_name": "complete_book",
                            "new_value": content,
                            "confidence": "0.90",
                            "rationale": "Complete work generation - creates multiple chapters based on the outline",
                            "creates_multiple": True,
                            "target_model": "chapters",
                        }
                    ]
                }

            # Project-targeted actions
            field = _target_field_for_action(action)
            return {
                "suggestions": [
                    {
                        "field_name": field,
                        "new_value": content,
                        "confidence": "0.80",
                        "rationale": base_rationale,
                    }
                ]
            }

    # Fallback to deterministic suggestions (previous stub)
    # --- Begin fallback logic (unchanged patterns) ---
    suggestions: List[Dict[str, str]] = []

    # Special handling for character cast generation (fallback only)
    if action == "generate_character_cast":
        # This creates multiple characters, so we return a special format
        suggestions.append(
            {
                "field_name": "character_cast",
                "new_value": "Generate 3-8 main characters based on story premise and genre",
                "confidence": "0.85",
                "rationale": "Character cast generation creates multiple characters with relationships and roles",
                "creates_multiple": True,
                "target_model": "characters",
            }
        )
    # Special handling for world collection generation (fallback only)
    elif action == "generate_world_collection":
        suggestions.append(
            {
                "field_name": "world_collection",
                "new_value": "Generate 4-6 interconnected worlds based on story genre and themes",
                "confidence": "0.85",
                "rationale": "World collection generation creates multiple worlds with detailed settings and connections",
                "creates_multiple": True,
                "target_model": "worlds",
            }
        )
    # reuse simplified cases
    elif action in ("premise", "themes", "outline", "stakes", "characters"):
        field = _target_field_for_action(action)
        defaults = {
            "premise": "A determined protagonist must overcome escalating obstacles to achieve a deeply personal goal.",
            "themes": "redemption, resilience, identity",
            "outline": "Act I: Setup; Act II: Rising stakes; Act III: Resolution.",
            "stakes": "If the protagonist fails, they lose the last chance to repair a critical relationship.",
            "characters": "Protagonist vs Antagonist cast outline.",
        }
        suggestions.append(
            {
                "field_name": field,
                "new_value": defaults.get(action, ""),
                "confidence": "0.65",
                "rationale": base_rationale,
            }
        )
    else:
        # Generic fallback
        if action in ("write_chapter_draft", "summarize_chapter") and chapter is not None:
            field = "content" if action == "write_chapter_draft" else "summary"
            suggestions.append(
                {
                    "field_name": field,
                    "new_value": (
                        "Draft stub for chapter"
                        if action == "write_chapter_draft"
                        else "Summary stub for chapter"
                    ),
                    "confidence": "0.62",
                    "rationale": base_rationale,
                    "target_model": "chapter",
                    "target_id": chapter.pk,
                }
            )
        else:
            suggestions.append(
                {
                    "field_name": _target_field_for_action(action),
                    "new_value": "Outline stub based on current project fields.",
                    "confidence": "0.62",
                    "rationale": base_rationale,
                }
            )
    return {"suggestions": suggestions}
