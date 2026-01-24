"""
Character Management Views
Handler-first architecture for character CRUD and enrichment
"""

import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from pydantic import ValidationError as PydanticValidationError

from apps.bfagent.handlers import (
    CharacterOutputHandler,
    EnrichmentHandler,
    ProcessingError,
    ValidationError,
)
from apps.bfagent.handlers.base_models import EnrichmentInput
from apps.bfagent.models import BookProjects, Characters

logger = logging.getLogger(__name__)


def project_characters(request, pk):
    """
    Display all characters for a project
    
    Args:
        pk: Project ID
    
    Returns:
        Rendered character list template
    """
    project = get_object_or_404(BookProjects, pk=pk)
    characters = Characters.objects.filter(project=project).order_by('name')
    
    context = {
        'project': project,
        'characters': characters,
        'character_count': characters.count(),
    }
    
    return render(request, 'bfagent/characters/character_list.html', context)


def character_detail(request, pk, character_pk):
    """
    Display character detail view
    
    Args:
        pk: Project ID
        character_pk: Character ID
    """
    project = get_object_or_404(BookProjects, pk=pk)
    character = get_object_or_404(Characters, pk=character_pk, project=project)
    
    context = {
        'project': project,
        'character': character,
    }
    
    return render(request, 'bfagent/characters/character_detail.html', context)


@require_http_methods(["POST"])
def generate_character_cast(request, pk):
    """
    Generate multiple characters for a project using the EnrichmentHandler
    
    POST Parameters:
        - action: 'generate_character_cast'
        - agent_id: Agent to use (optional, defaults to character agent)
        - requirements: User requirements/instructions (optional)
    """
    logger.info("Executing enrichment action: generate_character_cast")
    
    # Get project
    project = get_object_or_404(BookProjects, pk=pk)
    
    # SECURITY: Check ownership
    if hasattr(project, 'owner') and project.owner and project.owner != request.user:
        logger.warning(f"User {request.user.id} attempted to access project {pk} owned by {project.owner.id}")
        return HttpResponse(
            "<div class='alert alert-danger'><strong>Permission Denied:</strong> You don't have permission to modify this project.</div>",
            status=403
        )
    
    try:
        
        # Validate input with Pydantic
        try:
            input_data = EnrichmentInput(
                project_id=pk,
                action='generate_character_cast',
                agent_id=request.POST.get('agent_id', 1),
                requirements=request.POST.get('requirements', '')
            )
            logger.info(f"✅ Generating character cast for project {pk}")
        except PydanticValidationError as e:
            logger.warning(f"❌ Validation failed: {e}")
            errors = []
            for error in e.errors():
                field = error['loc'][0]
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            return HttpResponse(
                f"<div class='alert alert-danger'><strong>Validation Error:</strong><br>{'<br>'.join(errors)}</div>",
                status=400
            )
        
        # Generate characters using handler
        enrichment_handler = EnrichmentHandler()
        result = enrichment_handler.execute(input_data.dict())
        
        # Persist characters using output handler
        output_handler = CharacterOutputHandler()
        
        # Parse result and prepare character data
        # Valid fields for Characters model
        valid_fields = {
            'name', 'description', 'role', 'age', 'background',
            'personality', 'appearance', 'motivation', 'conflict', 'arc',
            'project_id'
        }
        
        characters_data = []
        if isinstance(result, dict) and 'characters' in result:
            for char_data in result['characters']:
                # Filter to only valid fields and add project_id
                filtered_data = {
                    k: v for k, v in char_data.items() 
                    if k in valid_fields
                }
                filtered_data['project_id'] = pk
                characters_data.append(filtered_data)
        elif isinstance(result, list):
            for char_data in result:
                # Filter to only valid fields and add project_id
                filtered_data = {
                    k: v for k, v in char_data.items() 
                    if k in valid_fields
                }
                filtered_data['project_id'] = pk
                characters_data.append(filtered_data)
        
        # Bulk create characters
        saved_characters = output_handler.bulk_create(characters_data)
        
        logger.info(f"✅ Generated {len(saved_characters)} characters")
        
        # Return success response
        character_list = '<ul class="list-group">'
        for char in saved_characters:
            character_list += f'''
                <li class="list-group-item">
                    <strong>{char.name}</strong> - {char.role}
                    <br><small class="text-muted">{char.description[:100]}...</small>
                </li>
            '''
        character_list += '</ul>'
        
        return HttpResponse(f"""
            <div class='alert alert-success'>
                <h4>✅ Character Cast Generated!</h4>
                <p><strong>Project:</strong> {project.title}</p>
                <p><strong>Characters Created:</strong> {len(saved_characters)}</p>
                <hr>
                <h5>Generated Characters:</h5>
                {character_list}
                <hr>
                <a href="/projects/projects/{pk}/" class="btn btn-primary">
                    <i class="bi bi-arrow-left"></i> Back to Project
                </a>
            </div>
        """)
        
    except ValidationError as e:
        logger.error(f"❌ Validation error: {e}")
        return HttpResponse(
            f"<div class='alert alert-danger'>Validation Error: {e}</div>",
            status=400
        )
    
    except ProcessingError as e:
        logger.error(f"❌ Processing error: {e}")
        return HttpResponse(
            f"<div class='alert alert-danger'>Processing Error: {e}</div>",
            status=500
        )
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return HttpResponse(
            f"<div class='alert alert-danger'>Error: {str(e)}</div>",
            status=500
        )


@require_http_methods(["POST"])
def enrich_character(request, pk, character_pk):
    """
    Enrich a specific character using handlers
    
    Args:
        pk: Project ID
        character_pk: Character ID
    """
    try:
        project = get_object_or_404(BookProjects, pk=pk)
        character = get_object_or_404(Characters, pk=character_pk, project=project)
        
        action = request.POST.get('action', 'enhance_description')
        
        # Build context with character data
        context = {
            'project_id': pk,
            'action': action,
            'character_id': character_pk,
            'character_name': character.name,
            'character_role': character.role,
            'character_description': character.description,
            'requirements': request.POST.get('requirements', ''),
        }
        
        # Execute handler
        handler = EnrichmentHandler()
        result = handler.execute(context)
        
        logger.info(f"✅ Character {character.name} enriched with action: {action}")
        
        # Build suggestions HTML
        suggestions_html = ""
        if result.get('suggestions'):
            suggestions_html = "<h5>AI Suggestions:</h5>"
            for suggestion in result['suggestions']:
                field = suggestion.get('field_name', 'unknown')
                value = suggestion.get('new_value', '')
                confidence = suggestion.get('confidence', 0) * 100
                rationale = suggestion.get('rationale', '')
                
                suggestions_html += f"""
                <div class="card mb-2">
                    <div class="card-body">
                        <h6 class="card-title">
                            <i class="bi bi-lightbulb"></i> {field.replace('_', ' ').title()}
                            <span class="badge bg-info">{confidence:.0f}% confidence</span>
                        </h6>
                        <p class="card-text">{value}</p>
                        <small class="text-muted">{rationale}</small>
                    </div>
                </div>
                """
        
        return HttpResponse(f"""
            <div class='alert alert-success'>
                <h4>✅ Character Enriched!</h4>
                <p><strong>Character:</strong> {character.name}</p>
                <p><strong>Action:</strong> {action}</p>
                <hr>
                {suggestions_html}
            </div>
        """)
        
    except Exception as e:
        logger.error(f"❌ Error enriching character: {e}", exc_info=True)
        return HttpResponse(
            f"<div class='alert alert-danger'>Error: {str(e)}</div>",
            status=500
        )


def character_create(request, pk):
    """
    Create a new character for a project
    
    GET: Show creation form
    POST: Create character and redirect
    """
    project = get_object_or_404(BookProjects, pk=pk)
    
    if request.method == 'POST':
        try:
            character = Characters.objects.create(
                project=project,
                name=request.POST.get('name', ''),
                role=request.POST.get('role', ''),
                age=request.POST.get('age') or None,
                description=request.POST.get('description', ''),
                background=request.POST.get('background', ''),
                personality=request.POST.get('personality', ''),
                appearance=request.POST.get('appearance', ''),
                motivation=request.POST.get('motivation', ''),
                conflict=request.POST.get('conflict', ''),
                arc=request.POST.get('arc', '')
            )
            
            messages.success(request, f'Character "{character.name}" erfolgreich erstellt!')
            logger.info(f"Created character {character.id} for project {pk}")
            
            return redirect('bfagent:project-characters', pk=pk)
            
        except Exception as e:
            logger.error(f"Error creating character: {e}", exc_info=True)
            messages.error(request, f'Fehler beim Erstellen: {str(e)}')
    
    context = {
        'project': project,
        'is_create': True
    }
    
    return render(request, 'bfagent/characters/character_form.html', context)


def character_edit(request, pk, character_pk):
    """
    Edit an existing character
    
    GET: Show edit form
    POST: Update character and redirect
    """
    project = get_object_or_404(BookProjects, pk=pk)
    character = get_object_or_404(Characters, pk=character_pk, project=project)
    
    if request.method == 'POST':
        try:
            character.name = request.POST.get('name', character.name)
            character.role = request.POST.get('role', character.role)
            
            age_value = request.POST.get('age')
            character.age = int(age_value) if age_value else None
            
            character.description = request.POST.get('description', '')
            character.background = request.POST.get('background', '')
            character.personality = request.POST.get('personality', '')
            character.appearance = request.POST.get('appearance', '')
            character.motivation = request.POST.get('motivation', '')
            character.conflict = request.POST.get('conflict', '')
            character.arc = request.POST.get('arc', '')
            
            character.save()
            
            messages.success(request, f'Character "{character.name}" erfolgreich aktualisiert!')
            logger.info(f"Updated character {character.id}")
            
            return redirect('bfagent:character-detail', pk=pk, character_pk=character_pk)
            
        except Exception as e:
            logger.error(f"Error updating character: {e}", exc_info=True)
            messages.error(request, f'Fehler beim Aktualisieren: {str(e)}')
    
    context = {
        'project': project,
        'character': character,
        'is_create': False
    }
    
    return render(request, 'bfagent/characters/character_form.html', context)


@require_http_methods(["POST"])
def character_delete(request, pk, character_pk):
    """
    Delete a character
    
    POST: Delete character and redirect
    """
    project = get_object_or_404(BookProjects, pk=pk)
    character = get_object_or_404(Characters, pk=character_pk, project=project)
    
    character_name = character.name
    character.delete()
    
    messages.success(request, f'Character "{character_name}" erfolgreich gelöscht!')
    logger.info(f"Deleted character {character_pk} from project {pk}")
    
    return redirect('bfagent:project-characters', pk=pk)
