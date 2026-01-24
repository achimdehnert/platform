"""
Dynamic CRUD Views using CRUDConfig System
SAFE: Parallel implementation - doesn't affect existing views
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..decorators import bookwriting_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from ..forms import BookProjectsForm, CharactersForm, WorldsForm
from ..models import (
    AgentExecutions,
    Agents,
    BookChapters,
    BookProjects,
    BookTypes,
    Characters,
    EnrichmentResponse,
    FieldDefinition,
    FieldGroup,
    Genre,
    Llms,
    PlotPoint,
    PromptTemplate,
    Worlds,
)
from ..utils.crud_config import BFAgentTheme

# ============================================================================
# DASHBOARD & LIST VIEWS (TODO: Replace with generated CBVs)
# ============================================================================


def dashboard(request):
    """Main dashboard with real DB stats"""

    # Get stats
    stats = {
        "projects_count": BookProjects.objects.count(),
        "agents_count": Agents.objects.count(),
        "llms_count": Llms.objects.count(),
        "chapters_count": BookChapters.objects.count(),
        "characters_count": Characters.objects.count(),
        "plotpoints_count": PlotPoint.objects.count(),
        "templates_count": PromptTemplate.objects.count(),
        "genres_count": Genre.objects.count(),
        "field_definitions_count": FieldDefinition.objects.filter(is_active=True).count(),
        "field_groups_count": FieldGroup.objects.filter(is_active=True).count(),
        "book_types_count": BookTypes.objects.count(),
    }

    # Get recent items
    recent_projects = BookProjects.objects.all().order_by("-updated_at")[:5]
    recent_executions = AgentExecutions.objects.select_related("agent").order_by("-started_at")[:5]

    context = {
        "stats": stats,
        "recent_projects": recent_projects,
        "recent_executions": recent_executions,
    }
    return render(request, "bfagent/dashboard.html", context)


def control_center_health(request):
    """Health check for control center integration"""
    context = {
        "health_score": 100,
        "status": "healthy",
        "tool_count": 7,
    }
    return render(request, "bfagent/partials/control_center_health.html", context)


# TODO: Replace these with generated CBVs (ProjectListView, etc.)
@login_required
@bookwriting_required
def project_list(request):
    """Books list with database-driven BookType filter"""
    from ..models import BookTypes

    # Get only user's projects
    projects = BookProjects.objects.filter(user=request.user).select_related('book_type').order_by("-created_at")

    # Filter by BookType (database-driven)
    booktype_filter = request.GET.get("booktype", "")
    if booktype_filter:
        projects = projects.filter(book_type_id=booktype_filter)

    # Filter by status
    status_filter = request.GET.get("status", "")
    if status_filter:
        projects = projects.filter(status=status_filter)

    # Filter by genre
    genre_filter = request.GET.get("genre", "")
    if genre_filter:
        projects = projects.filter(genre=genre_filter)

    # Search
    search_query = request.GET.get("search", "")
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(tagline__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(projects, 12)  # 12 books per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Get database-driven filter choices
    booktype_choices = BookTypes.objects.filter(is_active=True).order_by('name')
    status_choices = BookProjects.objects.values_list("status", flat=True).distinct()
    genre_choices = BookProjects.objects.values_list("genre", flat=True).distinct()

    context = {
        "page_obj": page_obj,
        "booktype_choices": booktype_choices,
        "status_choices": status_choices,
        "genre_choices": genre_choices,
        "booktype_filter": booktype_filter,
        "status_filter": status_filter,
        "genre_filter": genre_filter,
        "search_query": search_query,
    }

    return render(request, "bfagent/project_list.html", context)


@login_required
@bookwriting_required
def project_detail(request, pk):
    """Project detail - TODO: Use ProjectDetailView"""
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    return render(request, "bfagent/project_detail.html", {"project": project})


def project_agent_base_panel(request, pk):
    """Agent base panel - TODO: Implement"""
    return HttpResponse("Agent Base Panel - TODO")


def project_agent_base_save(request, pk):
    """Save agent base - TODO: Implement"""
    return HttpResponse("Saved")


def project_enrich_panel(request, pk):
    """Display enrichment panel - ACTION-FIRST approach (user-centric!)"""
    from apps.bfagent.models import PhaseActionConfig, WorkflowPhase

    project = get_object_or_404(BookProjects, pk=pk)

    # Get current phase from URL parameter or project's current phase
    phase_id = request.GET.get("phase")
    current_phase = None

    if phase_id:
        current_phase = WorkflowPhase.objects.filter(id=phase_id).first()
    elif project.current_phase_step:
        current_phase = project.current_phase_step.phase

    # Get ACTIONS from PhaseActionConfig (user thinks in ACTIONS, not agents!)
    available_actions = []

    if current_phase:
        # Get all action configurations for this phase
        action_configs = (
            PhaseActionConfig.objects.filter(phase=current_phase)
            .select_related("action", "action__agent")
            .order_by("order", "action__order")
        )

        print(f"\n{'='*80}")
        print(
            f"🔍 DEBUG: Loading actions for phase '{current_phase.name}' (ID: {current_phase.id})"
        )
        print(f"{'='*80}")
        print(f"Found {action_configs.count()} PhaseActionConfigs in database")

        for config in action_configs:
            action = config.action
            agent = action.agent
            print(f"\n📋 Config #{config.id}:")
            print(f"   Action: {action.display_name} (name={action.name})")
            print(f"   Agent: {agent.name} (ID={agent.id}, type={agent.agent_type})")
            print(f"   Required: {config.is_required}")
            print(f"   Order: {config.order}")
            print(f"   Action Active: {action.is_active}")

            # SIMPLIFIED: Only check action.is_active (not agent.status)
            if action.is_active:
                print(f"   ✅ INCLUDED in available_actions")
                available_actions.append(
                    {
                        "action": action,
                        "agent": agent,
                        "is_required": config.is_required,
                        "order": config.order,
                    }
                )
            else:
                print(f"   ❌ FILTERED OUT - Action is_active = False")

        print(f"\n{'='*80}")
        print(f"✅ Total available actions: {len(available_actions)}")
        print(f"{'='*80}\n")

    return render(
        request,
        "bfagent/project_enrich_panel.html",
        {
            "project": project,
            "available_actions": available_actions,
            "current_phase": current_phase,
        },
    )


def project_enrich_actions(request, pk):
    """Return available actions for selected agent (HTMX endpoint)"""
    from apps.bfagent.models import AgentAction

    agent_id = request.GET.get("agent_id")

    # DEBUG: Log what we receive
    print(f"🔍 project_enrich_actions called: agent_id={agent_id}, GET params={dict(request.GET)}")

    if not agent_id:
        return HttpResponse("<option value=''>Select an agent first</option>")

    try:
        agent = Agents.objects.get(pk=agent_id)
    except Agents.DoesNotExist:
        return HttpResponse("<option value=''>Agent not found</option>")

    # Get actions from database using new AgentAction model
    actions = AgentAction.objects.filter(agent=agent, is_active=True).order_by("order", "name")

    if not actions.exists():
        return HttpResponse(f"<option value=''>No actions available for {agent.name}</option>")

    # Build HTML options dynamically from database
    html = "<option value=''>Choose an action...</option>"
    for action in actions:
        html += f"<option value='{action.name}'>{action.display_name}</option>"

    print(f"✅ Loaded {actions.count()} actions for {agent.name}")

    return HttpResponse(html)


def project_enrich_run(request, pk):
    """
    STEP 1: Preview filled prompt before execution
    Shows user the filled template and allows editing before LLM call
    """
    print("\n" + "=" * 80)
    print("🚀 project_enrich_run() - STEP 1: PREVIEW")
    print(f"   Method: {request.method}")
    print(f"   Project PK: {pk}")
    print("=" * 80)

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    project = get_object_or_404(BookProjects, pk=pk)
    agent_id = request.POST.get("agent_id")
    action_name = request.POST.get("action")
    user_context = request.POST.get("context", "")
    
    print(f"🔍 Building preview for action: {action_name}")

    if not agent_id or not action_name:
        return HttpResponse(
            "<div class='alert alert-danger'>Missing agent or action</div>", status=400
        )

    try:
        agent = Agents.objects.get(pk=agent_id)
    except Agents.DoesNotExist:
        return HttpResponse("<div class='alert alert-danger'>Agent not found</div>", status=404)

    # Get action and template
    from ..models import AgentAction
    import json
    
    try:
        action = AgentAction.objects.filter(
            agent=agent, name=action_name
        ).select_related('prompt_template').first()
        
        if not action:
            return HttpResponse(
                f"<div class='alert alert-danger'>Action '{action_name}' not found for agent</div>",
                status=404
            )
    except Exception as e:
        return HttpResponse(
            f"<div class='alert alert-danger'>Error loading action: {str(e)}</div>",
            status=500
        )
    
    # Build context data
    from ..services.context_providers import get_context_for_action
    
    context_data = get_context_for_action(
        action=action,
        project=project,
        context=user_context,
        requirements=request.POST.get("requirements", "")
    )
    
    print(f"✅ Context built with {len(context_data)} fields")
    
    # Special handling for outline_agent actions (no template needed)
    if agent.agent_type == 'outline_agent':
        print(f"🎯 Outline agent detected - executing framework action directly")
        
        # Import and execute outline action
        from ..services.outline_actions import handle_outline_action
        import traceback
        
        try:
            print(f"📋 Executing action: {action_name}")
            print(f"📦 Context: {context_data}")
            
            results = handle_outline_action(
                action=action_name,
                project=project,
                context={
                    'num_chapters': context_data.get('num_chapters', 12),
                    'requirements': user_context
                }
            )
            
            print(f"✅ Results generated: {len(results)} suggestions")
            
            # Return results directly (skip preview step for framework actions)
            return render(request, 'bfagent/partials/project_enrich_results.html', {
                'project': project,
                'agent': agent,
                'action': action,
                'suggestions': results,
                'append_mode': False
            })
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"❌ ERROR executing framework action:")
            print(error_traceback)
            return HttpResponse(
                f"<div class='alert alert-danger'><strong>Error executing framework action:</strong><br>{str(e)}<br><pre>{error_traceback}</pre></div>",
                status=500
            )
    
    # Regular template-based actions
    template = action.prompt_template
    if not template:
        return HttpResponse(
            "<div class='alert alert-warning'>No template assigned to this action</div>",
            status=400
        )
    
    # Simple mustache-style replacement
    filled_template = template.template_text
    system_prompt = ""
    
    # Extract system prompt from template description (if JSON)
    if template.description:
        try:
            metadata = json.loads(template.description)
            system_prompt = metadata.get("system_prompt", "")
        except (json.JSONDecodeError, AttributeError):
            system_prompt = ""
    
    # Replace template variables (mustache-style: {{ key }})
    for key, value in context_data.items():
        placeholder = "{{" + f" {key} " + "}}"  # Builds: {{ key }}
        filled_template = filled_template.replace(placeholder, str(value))
    
    print(f"✅ Template filled. Length: {len(filled_template)} chars")
    
    # Get previous action outputs for context builder
    previous_outputs = EnrichmentResponse.objects.filter(
        project=project,
        status='applied'
    ).select_related('agent').order_by('-applied_at')[:10]
    
    # Render preview template
    return render(request, 'bfagent/partials/prompt_preview.html', {
        'project': project,
        'agent': agent,
        'action_name': action_name,
        'filled_template': filled_template,
        'system_prompt': system_prompt,
        'context_data': context_data,
        'user_context': user_context,
        'previous_outputs': previous_outputs,
        'selected_fields_json': json.dumps(list(context_data.keys())),
    })


def project_enrich_execute(request, pk):
    """
    STEP 2: Execute enrichment with (edited) prompt
    Actually calls the LLM and returns results
    """
    print("\n" + "=" * 80)
    print("🚀 project_enrich_execute() - STEP 2: EXECUTE")
    print(f"   Method: {request.method}")
    print(f"   Project PK: {pk}")
    print("=" * 80)

    # DEBUG: Print ALL POST data
    print("\n📦 POST DATA:")
    for key, value in request.POST.items():
        print(f"   {key}: {value}")
    print("=" * 80 + "\n")

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    project = get_object_or_404(BookProjects, pk=pk)
    agent_id = request.POST.get("agent_id")
    action_name = request.POST.get("action")
    
    # Get EDITED prompts from preview step
    edited_system_prompt = request.POST.get("system_prompt", "")
    edited_user_prompt = request.POST.get("user_prompt", "")

    print(f"🔍 EXTRACTED VALUES:")
    print(f"   agent_id: {agent_id}")
    print(f"   action: {action_name}")
    print(f"   edited_system_prompt length: {len(edited_system_prompt)}")
    print(f"   edited_user_prompt length: {len(edited_user_prompt)}")

    if not agent_id or not action_name:
        return HttpResponse(
            "<div class='alert alert-danger'>Missing agent or action</div>", status=400
        )

    try:
        agent = Agents.objects.get(pk=agent_id)
    except Agents.DoesNotExist:
        return HttpResponse("<div class='alert alert-danger'>Agent not found</div>", status=404)

    # Call LLM with edited prompts directly
    from ..services.project_enrichment import _choose_llm, _call_openai_chat
    
    try:
        llm = _choose_llm(agent)
        if not llm or not llm.is_active:
            return HttpResponse(
                "<div class='alert alert-danger'>No active LLM configured for this agent</div>",
                status=400
            )
        
        print(f"🤖 Calling LLM with edited prompt...")
        print(f"   Endpoint: {llm.api_endpoint}")
        print(f"   Model: {llm.llm_name}")
        print(f"   System prompt length: {len(edited_system_prompt)}")
        print(f"   User prompt length: {len(edited_user_prompt)}")
        
        # Call LLM with edited prompts
        response_text = _call_openai_chat(
            api_endpoint=llm.api_endpoint,
            api_key=llm.api_key,
            model=llm.llm_name,
            system=edited_system_prompt if edited_system_prompt else "You are a helpful writing assistant.",
            user=edited_user_prompt,
            temperature=llm.temperature or 0.7,
        )
        
        print(f"✅ LLM Response received. Length: {len(response_text) if response_text else 0} chars")
        
        # Parse response based on action type
        # TODO: Implement proper response parsing per action type
        result = {
            "suggestions": [{
                "field_name": "ai_generated_content",
                "new_value": response_text,
                "confidence": 0.9,
                "rationale": f"Generated by {agent.name} with custom prompt"
            }]
        }

        suggestions = result.get("suggestions", [])

        print(f"\n🎯 ENRICHMENT COMPLETED!")
        print(f"   Suggestions count: {len(suggestions)}")
        if suggestions:
            print(f"   First suggestion: {suggestions[0].get('field_name', 'N/A')}")

        # Create EnrichmentResponse records for tracking and editing
        enrichment_responses = []
        for suggestion in suggestions:
            # Skip if creates_object or creates_multiple (those are handled differently)
            if suggestion.get("creates_object") or suggestion.get("creates_multiple"):
                continue

            enrichment_response = EnrichmentResponse.objects.create(
                project=project,
                agent=agent,
                action_name=action_name,
                field_name=suggestion.get("field_name", "unknown"),
                suggested_value=suggestion.get("new_value", ""),
                confidence=float(suggestion.get("confidence", 0)),
                rationale=suggestion.get("rationale", ""),
                target_model=suggestion.get("target_model", "project"),
                target_id=suggestion.get("target_id"),
                status="pending",
            )
            enrichment_responses.append(enrichment_response)

        # Handle creates_multiple for character cast generation
        for suggestion in suggestions:
            if (
                suggestion.get("creates_multiple")
                and suggestion.get("target_model") == "characters"
            ):
                from ..models import Characters
                from ..utils.character_parser_v2 import parse_character_cast

                print("\n🎭 CHARACTER CAST GENERATION DEBUG:")

                content = suggestion.get("new_value", "")
                print(f"   📄 Content length: {len(content)} chars")
                print(f"   📄 Content preview: {content[:200]}...")

                characters_data = parse_character_cast(content, project)
                print(f"   🔍 Parser found: {len(characters_data)} characters")

                if characters_data:
                    print(f"   📋 Character names: {[c['name'] for c in characters_data]}")
                else:
                    print("   ⚠️  Parser returned empty list!")
                    print(f"   🔍 Checking content format...")
                    if "###" in content:
                        print("   ✅ Found ### markers")
                    if "####" in content:
                        print("   ✅ Found #### markers")
                    if "Protagonist" in content:
                        print("   ✅ Found 'Protagonist' keyword")

                created_count = 0
                for char_data in characters_data:
                    try:
                        # Debug: Show what fields we have
                        has_desc = bool(char_data.get("description"))
                        has_bg = bool(char_data.get("background"))
                        has_motiv = bool(char_data.get("motivation"))
                        has_pers = bool(char_data.get("personality"))

                        character = Characters.objects.create(
                            project=project,
                            name=char_data.get("name", "Unknown"),
                            role=char_data.get("role", "Supporting Character"),
                            description=char_data.get("description", ""),
                            background=char_data.get("background", ""),
                            motivation=char_data.get("motivation", ""),
                            personality=char_data.get("personality", ""),
                            arc=char_data.get("arc", ""),
                            age=char_data.get("age"),
                        )
                        created_count += 1

                        # Show which fields have content
                        fields_filled = []
                        if has_desc:
                            fields_filled.append("desc")
                        if has_bg:
                            fields_filled.append("bg")
                        if has_motiv:
                            fields_filled.append("motiv")
                        if has_pers:
                            fields_filled.append("pers")
                        fields_str = (
                            f" [{', '.join(fields_filled)}]" if fields_filled else " [NO CONTENT]"
                        )

                        age_str = f", age {character.age}" if character.age else ""
                        print(
                            f"   ✅ Created: {character.name} ({character.role}{age_str}){fields_str}"
                        )
                    except Exception as e:
                        print(
                            f"   ⚠️  Failed to create character {char_data.get('name', 'UNKNOWN')}: {e}"
                        )

                print(f"   🎉 Total created: {created_count} characters\n")

                # Update suggestion to show success
                suggestion["created_objects_count"] = created_count
                suggestion["rationale"] = (
                    f"Successfully created {created_count} characters from cast generation"
                )

        # Handle creates_multiple for complete book generation
        for suggestion in suggestions:
            if suggestion.get("creates_multiple") and suggestion.get("target_model") == "chapters":
                from ..models import BookChapters
                from ..utils.book_parser import parse_complete_book

                print("\n📖 COMPLETE BOOK GENERATION DEBUG:")

                content = suggestion.get("new_value", "")
                print(f"   📄 Content length: {len(content)} chars")
                print(f"   📄 Content preview: {content[:200]}...")

                chapters_data = parse_complete_book(content, project)
                print(f"   🔍 Parser found: {len(chapters_data)} chapters")

                if chapters_data:
                    print(f"   📋 Chapter titles: {[c['title'] for c in chapters_data]}")
                else:
                    print("   ⚠️  Parser returned empty list!")

                created_count = 0
                for chapter_data in chapters_data:
                    try:
                        chapter = BookChapters.objects.create(**chapter_data)
                        created_count += 1
                        print(
                            f"   ✅ Created: Chapter {chapter.chapter_number}: {chapter.title} ({chapter.word_count} words)"
                        )
                    except Exception as e:
                        print(
                            f"   ⚠️  Failed to create chapter {chapter_data.get('chapter_number', 'UNKNOWN')}: {e}"
                        )

                print(f"   🎉 Total created: {created_count} chapters\n")

                # Update suggestion to show success
                suggestion["created_objects_count"] = created_count
                suggestion["rationale"] = (
                    f"Successfully created {created_count} chapters from complete book generation"
                )

        if not suggestions:
            return HttpResponse("<div class='alert alert-warning'>No suggestions generated</div>")

        # Enhance suggestions with additional data for template
        from ..models import PromptTemplate

        for suggestion in suggestions:
            # Add confidence percentage
            confidence = float(suggestion.get("confidence", 0))
            suggestion["confidence_percent"] = int(confidence * 100)

            # If template was created, load full details
            if suggestion.get("creates_object") and suggestion.get("template_id"):
                try:
                    template = PromptTemplate.objects.get(pk=suggestion["template_id"])
                    suggestion["template_name"] = template.name
                    suggestion["template_text"] = template.template_text
                    suggestion["system_prompt"] = ""  # PromptTemplate doesn't have system_prompt
                except PromptTemplate.DoesNotExist:
                    pass

        # Render using template
        return render(
            request,
            "bfagent/partials/enrich_result_editable.html",
            {
                "agent_name": agent.name,
                "suggestions": suggestions,
                "enrichment_responses": enrichment_responses,
                "project": project,
            },
        )

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        print("\n" + "=" * 80)
        print("❌ EXCEPTION IN project_enrich_run:")
        print(error_trace)
        print("=" * 80 + "\n")

        return HttpResponse(
            f"<div class='alert alert-danger'><strong>Error:</strong> {str(e)}<br><pre style='font-size: 0.8em; max-height: 300px; overflow: auto;'>{error_trace}</pre></div>",
            status=500,
        )


def enrichment_response_edit(request, pk, response_id):
    """Edit an enrichment response before applying"""
    from ..models import EnrichmentResponse

    project = get_object_or_404(BookProjects, pk=pk)
    enrichment = get_object_or_404(EnrichmentResponse, id=response_id, project=project)

    if request.method == "POST":
        # Update edited value
        edited_value = request.POST.get("edited_value", "")
        enrichment.edited_value = edited_value
        enrichment.status = "edited"
        enrichment.save()

        # Return updated view (HTMX partial)
        return render(
            request, "bfagent/partials/enrichment_response_item.html", {"enrichment": enrichment}
        )

    # GET: Show edit form
    return render(
        request,
        "bfagent/enrichment_response_edit.html",
        {"project": project, "enrichment": enrichment},
    )


def project_enrich_apply(request, pk, response_id):
    """Apply enrichment response to target model"""
    from ..models import EnrichmentResponse

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    project = get_object_or_404(BookProjects, pk=pk)
    enrichment = get_object_or_404(EnrichmentResponse, id=response_id, project=project)

    # Check if already applied
    if enrichment.status == "applied":
        return HttpResponse("<div class='alert alert-warning'>Already applied</div>", status=400)

    # Apply to target model
    try:
        enrichment.apply_to_target(user=request.user)

        # HX-Redirect back to project edit page
        response = HttpResponse(
            f"<div class='alert alert-success'>" f"✅ Applied to {enrichment.field_name}!" f"</div>"
        )
        response["HX-Redirect"] = reverse("bfagent:project-edit", args=[project.id])
        return response
    except ValueError as e:
        return HttpResponse(
            f"<div class='alert alert-danger'>Validation error: {str(e)}</div>", status=400
        )
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        print(f"❌ Error applying enrichment: {error_trace}")
        return HttpResponse(f"<div class='alert alert-danger'>Error: {str(e)}</div>", status=500)


def project_update_field(request, pk):
    """Update a single project field (for framework outlines, etc.)"""
    from django.http import JsonResponse
    
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
    
    project = get_object_or_404(BookProjects, pk=pk)
    
    # Get field name and value from POST
    field_name = request.POST.get('field_name')
    field_value = request.POST.get('field_value')
    
    if not field_name or field_value is None:
        return JsonResponse({"success": False, "error": "Missing field_name or field_value"}, status=400)
    
    # Validate field exists
    if not hasattr(project, field_name):
        return JsonResponse({"success": False, "error": f"Field '{field_name}' does not exist"}, status=400)
    
    try:
        # Update the field
        setattr(project, field_name, field_value)
        project.save(update_fields=[field_name])
        
        return JsonResponse({
            "success": True,
            "message": f"Field '{field_name}' updated successfully",
            "field_name": field_name
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error updating field: {error_trace}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def enrichment_response_reject(request, pk, response_id):
    """Reject an enrichment response"""
    from ..models import EnrichmentResponse

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    project = get_object_or_404(BookProjects, pk=pk)
    enrichment = get_object_or_404(EnrichmentResponse, id=response_id, project=project)

    enrichment.status = "rejected"
    enrichment.save()

    return HttpResponse("<div class='alert alert-info'>Suggestion rejected</div>")


def agent_api(request, agent_id):
    """API endpoint for agent details (JSON)"""
    try:
        agent = Agents.objects.select_related("active_prompt").get(pk=agent_id)

        data = {
            "id": agent.id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "status": agent.status,
            "active_prompt": None,
        }

        if agent.active_prompt:
            data["active_prompt"] = {
                "id": agent.active_prompt.id,
                "name": agent.active_prompt.name,
                "template_text": agent.active_prompt.template_text,
                "version": agent.active_prompt.version,
            }

        return JsonResponse(data)

    except Agents.DoesNotExist:
        return JsonResponse({"error": "Agent not found"}, status=404)


def templates_api(request):
    """API endpoint for templates list (JSON)"""
    from ..models import PromptTemplate

    templates = PromptTemplate.objects.select_related("agent").order_by("-created_at")

    # Check if full details are requested
    include_details = request.GET.get("details", "false").lower() == "true"

    data = [
        {
            "id": t.id,
            "name": t.name,
            "version": t.version,
            "agent_id": t.agent_id,
            "agent_name": t.agent.name,
            "template_text": t.template_text if include_details else None,
            "description": t.description if include_details else None,
        }
        for t in templates
    ]

    return JsonResponse(data, safe=False)


def template_quick_save(request, template_id):
    """Quick save endpoint for template edits (HTMX)"""
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    import json

    from ..models import PromptTemplate

    try:
        template = PromptTemplate.objects.get(pk=template_id)

        # Update fields (only those that exist in model)
        template.name = request.POST.get("name", template.name)
        template.template_text = request.POST.get("template_text", template.template_text)

        # Store system_prompt in description if provided
        system_prompt = request.POST.get("system_prompt", "")
        if system_prompt:
            try:
                desc_data = json.loads(template.description) if template.description else {}
            except json.JSONDecodeError:
                desc_data = {}
            desc_data["system_prompt"] = system_prompt
            template.description = json.dumps(desc_data, indent=2)

        template.save()

        return HttpResponse(
            "<div class='alert alert-success'><i class='bi bi-check-circle'></i> Template saved successfully!</div>"
        )

    except PromptTemplate.DoesNotExist:
        return HttpResponse("<div class='alert alert-danger'>Template not found</div>", status=404)
    except Exception as e:
        return HttpResponse(
            f"<div class='alert alert-danger'>Error saving: {str(e)}</div>", status=500
        )


def agent_list(request):
    """Agent list - TODO: Use AgentsListView"""
    agents = Agents.objects.all().order_by("-created_at")
    return render(request, "bfagent/agent_list.html", {"agents": agents})


def agent_detail(request, pk):
    """Agent detail - TODO: Use AgentsDetailView"""
    agent = get_object_or_404(Agents, pk=pk)
    return render(request, "bfagent/agent_detail.html", {"agent": agent})


def chapter_list(request):
    """Chapter list - TODO: Use ChaptersListView"""
    chapters = BookChapters.objects.all().order_by("-created_at")
    return render(request, "bfagent/chapter_list.html", {"chapters": chapters})


def chapter_detail(request, pk):
    """Chapter detail - TODO: Use ChaptersDetailView"""
    chapter = get_object_or_404(BookChapters, pk=pk)
    return render(request, "bfagent/chapter_detail.html", {"chapter": chapter})


def chapter_edit(request, pk):
    """Chapter edit - TODO: Use ChaptersEditView"""
    chapter = get_object_or_404(BookChapters, pk=pk)
    return render(request, "bfagent/chapter_form.html", {"chapter": chapter})


def chapter_delete(request, pk):
    """Chapter delete - TODO: Use ChaptersDeleteView"""
    if request.method == "POST":
        chapter = get_object_or_404(BookChapters, pk=pk)
        chapter.delete()
        messages.success(request, "Chapter deleted successfully")
        return redirect("bfagent:chapter-list")
    return HttpResponse("Method not allowed", status=405)


def character_list(request):
    """Character list"""
    characters = Characters.objects.all().order_by("-created_at")
    return render(request, "bfagent/character_list.html", {"characters": characters})


def execution_list(request):
    """Execution list - TODO: Implement"""
    return render(request, "bfagent/execution_list.html", {})


def llm_list(request):
    """LLM list - TODO: Use LlmsListView"""
    llms = Llms.objects.all().order_by("-created_at")
    return render(request, "bfagent/llm_list.html", {"llms": llms})


def llm_detail(request, pk):
    """LLM detail - TODO: Use LlmsDetailView"""
    llm = get_object_or_404(Llms, pk=pk)
    return render(request, "bfagent/llm_detail.html", {"llm": llm})


def projects_api(request):
    """Projects API - TODO: Implement properly"""
    projects = BookProjects.objects.all().values("id", "title", "status")
    return JsonResponse(list(projects), safe=False)


# ============================================================================
# DYNAMIC CRUD VIEWS (CRUDConfig System)
# ============================================================================


@require_http_methods(["GET"])
def dynamic_project_list(request):
    """Dynamic project list using CRUDConfig - DEMO/TEST View"""

    # Get CRUDConfig
    crud_config = BookProjects.get_crud_config()

    # Get projects
    projects = BookProjects.objects.all()

    # Apply search
    search_query = request.GET.get("search", "")
    if search_query:
        search_fields = crud_config.get_search_fields()
        search_q = Q()
        for field in search_fields:
            search_q |= Q(**{f"{field}__icontains": search_query})
        projects = projects.filter(search_q)

    # Apply filters
    for filter_field in crud_config.list_filters:
        filter_value = request.GET.get(filter_field)
        if filter_value:
            projects = projects.filter(**{filter_field: filter_value})

    # Apply ordering
    projects = projects.order_by(*crud_config.ordering)

    # Pagination
    paginator = Paginator(projects, crud_config.per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get unique values for filters
    filter_options = {}
    for filter_field in crud_config.list_filters:
        filter_options[filter_field] = (
            BookProjects.objects.values_list(filter_field, flat=True)
            .distinct()
            .exclude(**{f"{filter_field}__isnull": True})
            .exclude(**{filter_field: ""})
        )

    context = {
        "page_obj": page_obj,
        "crud_config": crud_config,
        "search_query": search_query,
        "filter_options": filter_options,
        "theme": BFAgentTheme,
        "current_filters": {k: v for k, v in request.GET.items() if k != "page"},
        "view_type": request.GET.get("view", crud_config.ui_config.get("default_view", "card")),
    }

    # HTMX partial response
    if request.htmx:
        return render(request, "bfagent/dynamic/project_list_partial.html", context)

    return render(request, "bfagent/dynamic/project_list.html", context)


@require_http_methods(["GET"])
def dynamic_project_detail(request, pk):
    """Dynamic project detail using CRUDConfig"""
    project = get_object_or_404(BookProjects, pk=pk)
    crud_config = project.get_crud_config()

    context = {
        "project": project,
        "crud_config": crud_config,
        "theme": BFAgentTheme,
        "form_layout": crud_config.get_form_layout(),
    }

    return render(request, "bfagent/dynamic/project_detail.html", context)


@require_http_methods(["GET"])
def crud_config_api(request, model_name):
    """API endpoint to get CRUDConfig for a model - for debugging"""

    model_map = {
        "bookprojects": BookProjects,
        "projects": BookProjects,
    }

    model_class = model_map.get(model_name.lower())
    if not model_class:
        return JsonResponse({"error": "Model not found"}, status=404)

    crud_config = model_class.get_crud_config()

    config_data = {
        "list_display": crud_config.get_list_display(),
        "search_fields": crud_config.get_search_fields(),
        "list_filters": crud_config.list_filters,
        "form_layout": crud_config.get_form_layout(),
        "htmx_config": crud_config.htmx_config,
        "ui_config": crud_config.ui_config,
        "per_page": crud_config.per_page,
        "ordering": crud_config.ordering,
    }

    return JsonResponse(config_data, json_dumps_params={"indent": 2})


@login_required
@bookwriting_required
@require_http_methods(["GET", "POST"])
def project_create(request):
    """Create a new project with HTMX support"""
    if request.method == "POST":
        form = BookProjectsForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, f'Project "{project.title}" created successfully!')
            if request.htmx:
                # HTMX Success: Redirect to project detail via HX-Redirect header
                response = HttpResponse(status=204)  # No Content
                response["HX-Redirect"] = reverse(
                    "bfagent:project-detail", kwargs={"pk": project.pk}
                )
                return response
            return redirect("bfagent:project-detail", pk=project.pk)
        else:
            messages.error(request, "Please correct the highlighted errors and try again.")
            # For HTMX validation errors, return the form with errors
            if request.htmx:
                context = {
                    "form": form,
                    "project": None,
                    "title": "Create New Project",
                }
                return render(request, "bfagent/partials/project_form.html", context)
    else:
        form = BookProjectsForm()

    context = {
        "form": form,
        "project": None,
        "title": "Create New Project",
    }

    if request.htmx:
        return render(request, "bfagent/partials/project_form.html", context)

    return render(request, "bfagent/project_form.html", context)


@login_required
@bookwriting_required
@require_http_methods(["GET", "POST"])
def project_edit(request, pk):
    """Edit a project with HTMX support"""
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)

    if request.method == "POST":
        form = BookProjectsForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project "{project.title}" updated successfully!')
            if request.htmx:
                # HTMX Success: Redirect to project detail via HX-Redirect header
                response = HttpResponse(status=204)  # No Content
                response["HX-Redirect"] = reverse(
                    "bfagent:project-detail", kwargs={"pk": project.pk}
                )
                return response
            return redirect("bfagent:project-detail", pk=project.pk)
        else:
            # DEBUG: Print form errors to console
            print("🔍 FORM VALIDATION ERRORS:")
            for field, errors in form.errors.items():
                print(f"   • {field}: {errors}")
            if form.non_field_errors():
                print(f"   • Non-field errors: {form.non_field_errors()}")
            print(f"   • POST data: {request.POST}")

            messages.error(request, "Please correct the highlighted errors and try again.")
            # For HTMX validation errors, return the form with errors
            if request.htmx:
                context = {
                    "form": form,
                    "project": project,
                    "title": f"Edit {project.title}",
                }
                return render(request, "bfagent/partials/project_form.html", context)
    else:
        form = BookProjectsForm(instance=project)

    context = {
        "form": form,
        "project": project,
        "title": f"Edit {project.title}",
    }

    if request.htmx:
        return render(request, "bfagent/partials/project_form.html", context)

    return render(request, "bfagent/project_form.html", context)


@require_http_methods(["POST"])
def project_delete(request, pk):
    """Delete a project with HTMX support"""
    project = get_object_or_404(BookProjects, pk=pk)
    project_title = project.title

    project.delete()
    messages.success(request, f'Project "{project_title}" deleted successfully!')

    if request.htmx:
        # Return updated project list
        projects = BookProjects.objects.all().order_by("-created_at")
        paginator = Paginator(projects, 12)
        page_obj = paginator.get_page(1)
        return render(request, "bfagent/partials/project_list.html", {"page_obj": page_obj})

    return redirect("bfagent:project-list")


# ============================================================================
# CHARACTER CRUD VIEWS
# ============================================================================


@require_http_methods(["GET", "POST"])
def character_create(request):
    """Create a new character with HTMX support"""
    if request.method == "POST":
        form = CharactersForm(request.POST)
        if form.is_valid():
            character = form.save()
            messages.success(request, f'Character "{character.name}" created successfully!')
            if request.htmx:
                # HTMX Success: Return updated character list
                characters = (
                    Characters.objects.select_related("project").all().order_by("-created_at")
                )
                paginator = Paginator(characters, 20)
                page_obj = paginator.get_page(1)
                return render(
                    request, "bfagent/partials/character_list.html", {"page_obj": page_obj}
                )
            return redirect("bfagent:character-list")
        else:
            messages.error(request, "Please correct the highlighted errors and try again.")
            if request.htmx:
                context = {
                    "form": form,
                    "character": None,
                    "title": "Create New Character",
                }
                return render(request, "bfagent/partials/character_form.html", context)
    else:
        form = CharactersForm()

    context = {
        "form": form,
        "character": None,
        "title": "Create New Character",
    }

    if request.htmx:
        return render(request, "bfagent/partials/character_form.html", context)

    return render(request, "bfagent/character_form.html", context)


@require_http_methods(["GET", "POST"])
def character_edit(request, pk):
    """Edit a character with HTMX support"""
    character = get_object_or_404(Characters, pk=pk)

    if request.method == "POST":
        form = CharactersForm(request.POST, instance=character)
        if form.is_valid():
            form.save()
            messages.success(request, f'Character "{character.name}" updated successfully!')
            if request.htmx:
                # HTMX Success: Return updated character list
                characters = (
                    Characters.objects.select_related("project").all().order_by("-created_at")
                )
                paginator = Paginator(characters, 20)
                page_obj = paginator.get_page(1)
                return render(
                    request, "bfagent/partials/character_list.html", {"page_obj": page_obj}
                )
            return redirect("bfagent:character-list")
        else:
            messages.error(request, "Please correct the highlighted errors and try again.")
            if request.htmx:
                context = {
                    "form": form,
                    "character": character,
                    "title": f"Edit {character.name}",
                }
                return render(request, "bfagent/partials/character_form.html", context)
    else:
        form = CharactersForm(instance=character)

    context = {
        "form": form,
        "character": character,
        "title": f"Edit {character.name}",
    }

    if request.htmx:
        return render(request, "bfagent/partials/character_form.html", context)

    return render(request, "bfagent/character_form.html", context)


@require_http_methods(["POST"])
def character_delete(request, pk):
    """Delete a character with HTMX support"""
    character = get_object_or_404(Characters, pk=pk)
    character_name = character.name

    character.delete()
    messages.success(request, f'Character "{character_name}" deleted successfully!')

    if request.htmx:
        # Return updated character list
        characters = Characters.objects.select_related("project").all().order_by("-created_at")
        paginator = Paginator(characters, 20)
        page_obj = paginator.get_page(1)
        return render(request, "bfagent/partials/character_list.html", {"page_obj": page_obj})

    return redirect("bfagent:character-list")


# ============================================================================
# WORLDS CRUD VIEWS
# ============================================================================


@require_http_methods(["GET", "POST"])
def world_create(request):
    """Create a new world with HTMX support"""
    if request.method == "POST":
        form = WorldsForm(request.POST)
        if form.is_valid():
            world = form.save()
            messages.success(request, f'World "{world.name}" created successfully!')
            if request.htmx:
                # HTMX Success: Return updated world list
                worlds = Worlds.objects.select_related("project").all().order_by("name")
                paginator = Paginator(worlds, 20)
                page_obj = paginator.get_page(1)
                return render(request, "bfagent/partials/world_list.html", {"page_obj": page_obj})
            return redirect("bfagent:world-list")
        else:
            messages.error(request, "Please correct the highlighted errors and try again.")
            if request.htmx:
                context = {
                    "form": form,
                    "world": None,
                    "title": "Create New World",
                }
                return render(request, "bfagent/partials/world_form.html", context)
    else:
        form = WorldsForm()

    context = {
        "form": form,
        "world": None,
        "title": "Create New World",
    }

    if request.htmx:
        return render(request, "bfagent/partials/world_form.html", context)

    return render(request, "bfagent/world_form.html", context)


@require_http_methods(["GET", "POST"])
def world_edit(request, pk):
    """Edit a world with HTMX support"""
    world = get_object_or_404(Worlds, pk=pk)

    if request.method == "POST":
        form = WorldsForm(request.POST, instance=world)
        if form.is_valid():
            form.save()
            messages.success(request, f'World "{world.name}" updated successfully!')
            if request.htmx:
                # HTMX Success: Return updated world list
                worlds = Worlds.objects.select_related("project").all().order_by("name")
                paginator = Paginator(worlds, 20)
                page_obj = paginator.get_page(1)
                return render(request, "bfagent/partials/world_list.html", {"page_obj": page_obj})
            return redirect("bfagent:world-list")
        else:
            messages.error(request, "Please correct the highlighted errors and try again.")
            if request.htmx:
                context = {
                    "form": form,
                    "world": world,
                    "title": f"Edit {world.name}",
                }
                return render(request, "bfagent/partials/world_form.html", context)
    else:
        form = WorldsForm(instance=world)

    context = {
        "form": form,
        "world": world,
        "title": f"Edit {world.name}",
    }

    if request.htmx:
        return render(request, "bfagent/partials/world_form.html", context)

    return render(request, "bfagent/world_form.html", context)


@require_http_methods(["POST"])
def world_delete(request, pk):
    """Delete a world with HTMX support"""
    world = get_object_or_404(Worlds, pk=pk)
    world_name = world.name

    world.delete()
    messages.success(request, f'World "{world_name}" deleted successfully!')

    if request.htmx:
        # Return updated world list
        worlds = Worlds.objects.select_related("project").all().order_by("name")
        paginator = Paginator(worlds, 20)
        page_obj = paginator.get_page(1)
        context = {
            "page_obj": page_obj,
            "project_filter": None,
            "type_filter": None,
        }
        return render(request, "bfagent/partials/world_list.html", context)

    return redirect("bfagent:world-list")


# ============================================================================
# WORLDS LIST VIEW (Generated by Enhanced Consistency Framework)
# ============================================================================


@require_http_methods(["GET"])
def worlds_list(request):
    """List all Worlds with pagination and filtering"""
    worlds = Worlds.objects.select_related("project").all()

    # Apply filters
    project_filter = request.GET.get("project")
    world_type_filter = request.GET.get("world_type")

    if project_filter:
        worlds = worlds.filter(project_id=project_filter)
    if world_type_filter:
        worlds = worlds.filter(world_type=world_type_filter)

    # ordering
    worlds = worlds.order_by("name")

    # Pagination
    paginator = Paginator(worlds, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get all projects for modal dropdown
    projects = BookProjects.objects.all().order_by("-created_at")
    print(f"DEBUG: Found {projects.count()} projects for modal dropdown")
    for p in projects:
        print(f"  - Project ID: {p.id}, Title: {p.title}")
    
    context = {
        "page_obj": page_obj,
        "project_filter": project_filter,
        "type_filter": world_type_filter,
        "projects": projects,
    }
    print(f"DEBUG: Context keys: {context.keys()}")
    print(f"DEBUG: Projects in context: {context['projects'].count()}")

    if request.htmx:
        return render(request, "bfagent/partials/worlds_list.html", context)

    return render(request, "bfagent/worlds_list.html", context)


@require_http_methods(["GET", "POST"])
def worlds_create(request):
    """Create a new Worlds with HTMX support"""
    if request.method == "POST":
        form = WorldsForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Worlds "{obj}" created successfully!')
            if request.htmx:
                # HTMX Success: Return updated list
                items = Worlds.objects.all().order_by("-created_at")
                paginator = Paginator(items, 20)
                page_obj = paginator.get_page(1)
                return render(request, "bfagent/partials/worlds_list.html", {"page_obj": page_obj})
            return redirect("bfagent:worlds-list")
        else:
            messages.error(request, "Please correct the highlighted errors.")
            if request.htmx:
                context = {"form": form, "worlds": None, "title": "Create New Worlds"}
                return render(request, "bfagent/partials/worlds_form.html", context)
    else:
        form = WorldsForm()

    context = {"form": form, "worlds": None, "title": "Create New Worlds"}

    if request.htmx:
        return render(request, "bfagent/partials/worlds_form.html", context)

    return render(request, "bfagent/worlds_form.html", context)


@require_http_methods(["GET", "POST"])
def worlds_edit(request, pk):
    """Edit a Worlds with HTMX support"""
    worlds = get_object_or_404(Worlds, pk=pk)

    if request.method == "POST":
        form = WorldsForm(request.POST, instance=worlds)
        if form.is_valid():
            form.save()
            messages.success(request, f'Worlds "{worlds}" updated successfully!')
            if request.htmx:
                # HTMX Success: Return updated list
                items = Worlds.objects.all().order_by("-created_at")
                paginator = Paginator(items, 20)
                page_obj = paginator.get_page(1)
                return render(request, "bfagent/partials/worlds_list.html", {"page_obj": page_obj})
            return redirect("bfagent:worlds-list")
        else:
            messages.error(request, "Please correct the highlighted errors.")
            if request.htmx:
                context = {"form": form, "worlds": worlds, "title": f"Edit {worlds}"}
                return render(request, "bfagent/partials/worlds_form.html", context)
    else:
        form = WorldsForm(instance=worlds)

    context = {"form": form, "worlds": worlds, "title": f"Edit {worlds}"}

    if request.htmx:
        return render(request, "bfagent/partials/worlds_form.html", context)

    return render(request, "bfagent/worlds_form.html", context)


@require_http_methods(["POST"])
def worlds_delete(request, pk):
    """Delete a Worlds with HTMX support"""
    worlds = get_object_or_404(Worlds, pk=pk)
    worlds_name = str(worlds)

    worlds.delete()
    messages.success(request, f'Worlds "{worlds_name}" deleted successfully!')

    if request.htmx:
        # Return updated list
        items = Worlds.objects.all().order_by("-created_at")
        paginator = Paginator(items, 20)
        page_obj = paginator.get_page(1)
        return render(request, "bfagent/partials/worlds_list.html", {"page_obj": page_obj})

    return redirect("bfagent:worlds-list")
