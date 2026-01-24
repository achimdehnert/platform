"""
Writing Hub - World Building Views
===================================

Projektunabhängige Weltenbau-Views mit Projekt-Zuordnung.

Created: 2026-01-09
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .models_world import World, ProjectWorld, WorldLocation, WorldRule
from .models_lookups import WorldType
from apps.bfagent.models import BookProjects


@login_required
def world_dashboard(request):
    """
    Übersicht aller eigenen Welten (projektunabhängig).
    
    Unterstützt ?project=<id> Parameter für Projekt-Kontext:
    - Zeigt welche Welten dem Projekt zugeordnet sind
    - Ermöglicht Zuordnung/Entfernung von Welten
    """
    worlds = World.objects.filter(owner=request.user).prefetch_related(
        'project_links__project',
        'locations',
        'rules',
        'world_type'
    )
    
    world_types = WorldType.objects.filter(is_active=True)
    
    # Projekt-Kontext (optional, für Zuordnung)
    project = None
    project_world_ids = []
    project_id = request.GET.get('project')
    if project_id:
        project = BookProjects.objects.filter(id=project_id).first()
        if project:
            project_world_ids = list(
                ProjectWorld.objects.filter(project=project)
                .values_list('world_id', flat=True)
            )
    
    # Stats
    stats = {
        'total_worlds': worlds.count(),
        'total_locations': WorldLocation.objects.filter(world__owner=request.user).count(),
        'total_rules': WorldRule.objects.filter(world__owner=request.user).count(),
    }
    
    context = {
        'worlds': worlds,
        'world_types': world_types,
        'stats': stats,
        'project': project,
        'project_world_ids': project_world_ids,
    }
    
    return render(request, 'writing_hub/world/dashboard.html', context)


@login_required
def world_detail(request, world_id):
    """
    Detail-Ansicht einer Welt mit Locations und Rules.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    locations = world.locations.filter(parent__isnull=True).prefetch_related('children')
    rules = world.rules.all()
    project_links = world.project_links.select_related('project')
    
    context = {
        'world': world,
        'locations': locations,
        'rules': rules,
        'project_links': project_links,
    }
    
    return render(request, 'writing_hub/world/detail.html', context)


@login_required
def world_create(request):
    """
    Neue Welt erstellen.
    
    Unterstützt ?project=<id> Parameter:
    - Zeigt Projekt-Kontext im Formular
    - Ordnet neue Welt automatisch dem Projekt zu
    """
    # Projekt-Kontext (optional)
    project = None
    project_id = request.GET.get('project') or request.POST.get('project')
    if project_id:
        project = BookProjects.objects.filter(id=project_id).first()
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        world_type_id = request.POST.get('world_type')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Name ist erforderlich.')
            redirect_url = 'writing_hub:world-dashboard'
            if project:
                return redirect(f"{redirect_url}?project={project.id}")
            return redirect(redirect_url)
        
        world_type = None
        if world_type_id:
            world_type = WorldType.objects.filter(id=world_type_id).first()
        
        world = World.objects.create(
            owner=request.user,
            name=name,
            world_type=world_type,
            description=description,
        )
        
        # Auto-Zuordnung zum Projekt wenn Kontext vorhanden
        if project:
            ProjectWorld.objects.get_or_create(
                project=project,
                world=world,
                defaults={'role': 'primary'}
            )
            messages.success(request, f'Welt "{world.name}" erstellt und Projekt "{project.title}" zugeordnet.')
            return redirect('writing_hub:project_hub', project_id=project.id)
        
        messages.success(request, f'Welt "{world.name}" erstellt.')
        return redirect('writing_hub:world-detail', world_id=world.id)
    
    # GET: Formular anzeigen
    world_types = WorldType.objects.filter(is_active=True)
    return render(request, 'writing_hub/world/create.html', {
        'world_types': world_types,
        'project': project,
    })


@login_required
def world_edit(request, world_id):
    """
    Welt bearbeiten.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    if request.method == 'POST':
        world.name = request.POST.get('name', world.name).strip()
        world.description = request.POST.get('description', '')
        world.setting_era = request.POST.get('setting_era', '')
        world.geography = request.POST.get('geography', '')
        world.climate = request.POST.get('climate', '')
        world.inhabitants = request.POST.get('inhabitants', '')
        world.culture = request.POST.get('culture', '')
        world.religion = request.POST.get('religion', '')
        world.technology_level = request.POST.get('technology_level', '')
        world.magic_system = request.POST.get('magic_system', '')
        world.politics = request.POST.get('politics', '')
        world.economy = request.POST.get('economy', '')
        world.history = request.POST.get('history', '')
        
        world_type_id = request.POST.get('world_type')
        if world_type_id:
            world.world_type = WorldType.objects.filter(id=world_type_id).first()
        else:
            world.world_type = None
        
        world.version += 1
        world.save()
        
        messages.success(request, f'Welt "{world.name}" aktualisiert (v{world.version}).')
        return redirect('writing_hub:world-detail', world_id=world.id)
    
    world_types = WorldType.objects.filter(is_active=True)
    return render(request, 'writing_hub/world/edit.html', {
        'world': world,
        'world_types': world_types,
    })


@login_required
def world_delete(request, world_id):
    """
    Welt löschen.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    if request.method == 'POST':
        name = world.name
        world.delete()
        messages.success(request, f'Welt "{name}" gelöscht.')
        return redirect('writing_hub:world-dashboard')
    
    return redirect('writing_hub:world-detail', world_id=world_id)


@login_required
def world_duplicate(request, world_id):
    """
    Welt duplizieren.
    """
    original = get_object_or_404(World, id=world_id, owner=request.user)
    
    # Kopie erstellen
    duplicate = World.objects.create(
        owner=request.user,
        name=f"{original.name} (Kopie)",
        world_type=original.world_type,
        description=original.description,
        setting_era=original.setting_era,
        geography=original.geography,
        climate=original.climate,
        inhabitants=original.inhabitants,
        culture=original.culture,
        religion=original.religion,
        technology_level=original.technology_level,
        magic_system=original.magic_system,
        politics=original.politics,
        economy=original.economy,
        history=original.history,
        tags=original.tags.copy() if original.tags else [],
    )
    
    # Locations kopieren (nur Top-Level, rekursiv wäre komplexer)
    for loc in original.locations.filter(parent__isnull=True):
        WorldLocation.objects.create(
            world=duplicate,
            name=loc.name,
            location_type=loc.location_type,
            description=loc.description,
            significance=loc.significance,
        )
    
    # Rules kopieren
    for rule in original.rules.all():
        WorldRule.objects.create(
            world=duplicate,
            category=rule.category,
            rule=rule.rule,
            explanation=rule.explanation,
            importance=rule.importance,
        )
    
    messages.success(request, f'Welt "{original.name}" dupliziert.')
    return redirect('writing_hub:world-detail', world_id=duplicate.id)


# =============================================================================
# AJAX Endpoints
# =============================================================================

@login_required
@require_http_methods(["POST"])
def world_save_ajax(request):
    """
    AJAX: Welt speichern oder erstellen.
    """
    try:
        data = json.loads(request.body)
        world_id = data.get('id')
        
        if world_id:
            world = get_object_or_404(World, id=world_id, owner=request.user)
        else:
            world = World(owner=request.user)
        
        world.name = data.get('name', 'Neue Welt')
        world.description = data.get('description', '')
        world.setting_era = data.get('setting_era', '')
        world.geography = data.get('geography', '')
        world.climate = data.get('climate', '')
        world.inhabitants = data.get('inhabitants', '')
        world.culture = data.get('culture', '')
        world.religion = data.get('religion', '')
        world.technology_level = data.get('technology_level', '')
        world.magic_system = data.get('magic_system', '')
        world.politics = data.get('politics', '')
        world.economy = data.get('economy', '')
        world.history = data.get('history', '')
        
        world_type_id = data.get('world_type_id')
        if world_type_id:
            world.world_type = WorldType.objects.filter(id=world_type_id).first()
        
        if world_id:
            world.version += 1
        
        world.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Welt "{world.name}" gespeichert',
            'world': {
                'id': str(world.id),
                'name': world.name,
                'version': world.version,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def location_save_ajax(request, world_id):
    """
    AJAX: Location speichern oder erstellen.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        data = json.loads(request.body)
        location_id = data.get('id')
        
        if location_id:
            location = get_object_or_404(WorldLocation, id=location_id, world=world)
        else:
            location = WorldLocation(world=world)
        
        location.name = data.get('name', 'Neuer Ort')
        location.location_type = data.get('location_type', 'city')
        location.description = data.get('description', '')
        location.significance = data.get('significance', '')
        
        parent_id = data.get('parent_id')
        if parent_id:
            location.parent = WorldLocation.objects.filter(id=parent_id, world=world).first()
        else:
            location.parent = None
        
        location.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Ort "{location.name}" gespeichert',
            'location': {
                'id': str(location.id),
                'name': location.name,
                'location_type': location.location_type,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def location_delete_ajax(request, world_id, location_id):
    """
    AJAX: Location löschen.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    location = get_object_or_404(WorldLocation, id=location_id, world=world)
    
    try:
        name = location.name
        location.delete()
        return JsonResponse({'success': True, 'message': f'Ort "{name}" gelöscht'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def rule_save_ajax(request, world_id):
    """
    AJAX: Rule speichern oder erstellen.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        data = json.loads(request.body)
        rule_id = data.get('id')
        
        if rule_id:
            rule = get_object_or_404(WorldRule, id=rule_id, world=world)
        else:
            rule = WorldRule(world=world)
        
        rule.category = data.get('category', 'physics')
        rule.rule = data.get('rule', '')
        rule.explanation = data.get('explanation', '')
        rule.importance = data.get('importance', 'strong')
        
        rule.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Regel gespeichert',
            'rule': {
                'id': str(rule.id),
                'category': rule.category,
                'rule': rule.rule,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def rule_delete_ajax(request, world_id, rule_id):
    """
    AJAX: Rule löschen.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    rule = get_object_or_404(WorldRule, id=rule_id, world=world)
    
    try:
        rule.delete()
        return JsonResponse({'success': True, 'message': 'Regel gelöscht'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# Project-World Linking
# =============================================================================

@login_required
@require_http_methods(["POST"])
def project_world_assign(request, project_id, world_id):
    """
    AJAX: Welt einem Projekt zuordnen.
    """
    project = get_object_or_404(BookProjects, id=project_id)
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        data = json.loads(request.body) if request.body else {}
        role = data.get('role', 'primary')
        
        link, created = ProjectWorld.objects.get_or_create(
            project=project,
            world=world,
            defaults={'role': role}
        )
        
        if not created:
            link.role = role
            link.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Welt "{world.name}" zu Projekt "{project.title}" zugeordnet',
            'created': created,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def project_world_unassign(request, project_id, world_id):
    """
    AJAX: Welt von Projekt entfernen.
    """
    project = get_object_or_404(BookProjects, id=project_id)
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        deleted, _ = ProjectWorld.objects.filter(
            project=project,
            world=world
        ).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Welt "{world.name}" von Projekt "{project.title}" entfernt',
            'deleted': deleted > 0,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def project_worlds_list(request, project_id):
    """
    Liste aller Welten eines Projekts (für Planning Editor).
    """
    project = get_object_or_404(BookProjects, id=project_id)
    
    project_worlds = ProjectWorld.objects.filter(project=project).select_related(
        'world', 'world__world_type'
    )
    
    worlds_data = []
    for pw in project_worlds:
        w = pw.world
        worlds_data.append({
            'id': str(w.id),
            'name': w.name,
            'role': pw.role,
            'world_type': w.world_type.name if w.world_type else None,
            'description': w.description[:200] if w.description else '',
            'geography': w.geography[:200] if w.geography else '',
            'culture': w.culture[:200] if w.culture else '',
            'magic_system': w.magic_system[:200] if w.magic_system else '',
        })
    
    return JsonResponse({
        'success': True,
        'project_id': project_id,
        'project_title': project.title,
        'worlds': worlds_data,
    })


# =============================================================================
# AI-Powered World Generation (via LLMAgent)
# =============================================================================

@login_required
@require_http_methods(["POST"])
def world_generate_ai(request):
    """
    AJAX: Generate world foundation using AI.
    
    POST body:
    - name: str (required)
    - world_type: str (fantasy, scifi, etc.)
    - genre: str (optional)
    - seed_idea: str (optional)
    """
    try:
        data = json.loads(request.body)
        
        from .handlers.world_handlers import WorldGeneratorHandler
        result = WorldGeneratorHandler.handle(data)
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def world_expand_aspect_ai(request, world_id):
    """
    AJAX: Expand a specific aspect of a world using AI.
    
    POST body:
    - aspect: str (magic_system, politics, economy, history, religion)
    - direction: str (optional, specific direction)
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        data = json.loads(request.body)
        
        # Build world data context
        world_data = {
            'name': world.name,
            'world_type': world.world_type.code if world.world_type else 'fantasy',
            'description': world.description,
            'geography': world.geography,
            'climate': world.climate,
            'inhabitants': world.inhabitants,
            'culture': world.culture,
            'technology_level': world.technology_level,
            'magic_system': world.magic_system,
            'politics': world.politics,
            'economy': world.economy,
            'religion': world.religion,
            'history': world.history,
        }
        
        # Get existing content for the aspect
        aspect = data.get('aspect', '')
        existing_content = getattr(world, aspect, '') if hasattr(world, aspect) else ''
        
        from .handlers.world_handlers import WorldExpanderHandler
        result = WorldExpanderHandler.handle({
            'world_data': world_data,
            'aspect': aspect,
            'existing_content': existing_content,
            'direction': data.get('direction', ''),
        })
        
        # Auto-save if successful and requested
        if result.get('success') and data.get('auto_save') and result.get('content'):
            if hasattr(world, aspect):
                setattr(world, aspect, result['content'])
                world.version += 1
                world.save()
                result['saved'] = True
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def world_generate_locations_ai(request, world_id):
    """
    AJAX: Generate locations for a world using AI.
    
    POST body:
    - location_type: str (continent, country, city, etc.)
    - count: int (default 3, max 10)
    - parent_location: str (optional)
    - auto_save: bool (optional, save to DB)
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        data = json.loads(request.body)
        
        world_data = {
            'name': world.name,
            'world_type': world.world_type.code if world.world_type else 'fantasy',
            'geography': world.geography,
            'culture': world.culture,
            'inhabitants': world.inhabitants,
        }
        
        from .handlers.world_handlers import LocationGeneratorHandler
        result = LocationGeneratorHandler.handle({
            'world_data': world_data,
            'location_type': data.get('location_type', 'city'),
            'count': data.get('count', 3),
            'parent_location': data.get('parent_location', ''),
        })
        
        # Auto-save locations if requested
        if result.get('success') and data.get('auto_save'):
            saved_locations = []
            for loc in result.get('locations', []):
                new_loc = WorldLocation.objects.create(
                    world=world,
                    name=loc.get('name', 'Unknown'),
                    location_type=data.get('location_type', 'city'),
                    description=loc.get('description', ''),
                    significance=loc.get('significance', ''),
                )
                saved_locations.append({
                    'id': str(new_loc.id),
                    'name': new_loc.name,
                })
            result['saved_locations'] = saved_locations
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def world_generate_rules_ai(request, world_id):
    """
    AJAX: Generate rules for a world using AI.
    
    POST body:
    - category: str (physics, magic, social, technology, biology, economy)
    - count: int (default 5, max 10)
    - auto_save: bool (optional)
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        data = json.loads(request.body)
        
        world_data = {
            'name': world.name,
            'world_type': world.world_type.code if world.world_type else 'fantasy',
            'magic_system': world.magic_system,
            'technology_level': world.technology_level,
            'culture': world.culture,
        }
        
        from .handlers.world_handlers import WorldRuleGeneratorHandler
        result = WorldRuleGeneratorHandler.handle({
            'world_data': world_data,
            'category': data.get('category', 'physics'),
            'count': data.get('count', 5),
        })
        
        # Auto-save rules if requested
        if result.get('success') and data.get('auto_save'):
            saved_rules = []
            for rule in result.get('rules', []):
                new_rule = WorldRule.objects.create(
                    world=world,
                    category=data.get('category', 'physics'),
                    rule=rule.get('rule', ''),
                    explanation=rule.get('explanation', ''),
                    importance=rule.get('importance', 'strong'),
                )
                saved_rules.append({
                    'id': str(new_rule.id),
                    'rule': new_rule.rule[:50],
                })
            result['saved_rules'] = saved_rules
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def world_check_consistency_ai(request, world_id):
    """
    AJAX: Check world consistency using AI.
    
    Returns issues, suggestions, and consistency score.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        world_data = {
            'name': world.name,
            'world_type': world.world_type.code if world.world_type else 'fantasy',
            'description': world.description,
            'setting_era': world.setting_era,
            'geography': world.geography,
            'climate': world.climate,
            'inhabitants': world.inhabitants,
            'culture': world.culture,
            'religion': world.religion,
            'technology_level': world.technology_level,
            'magic_system': world.magic_system,
            'politics': world.politics,
            'economy': world.economy,
            'history': world.history,
        }
        
        from .handlers.world_handlers import WorldConsistencyCheckerHandler
        result = WorldConsistencyCheckerHandler.handle({
            'world_data': world_data,
        })
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def world_apply_suggestions_ai(request, world_id):
    """
    AJAX: Apply AI suggestions to improve world consistency.
    
    Takes the suggestions from consistency check and uses AI to 
    expand/improve the world description accordingly.
    """
    world = get_object_or_404(World, id=world_id, owner=request.user)
    
    try:
        data = json.loads(request.body)
        suggestions = data.get('suggestions', [])
        issues = data.get('issues', [])
        
        if not suggestions:
            return JsonResponse({'success': False, 'error': 'Keine Vorschläge vorhanden'})
        
        from .handlers.world_handlers import WorldSuggestionApplierHandler
        result = WorldSuggestionApplierHandler.handle({
            'world': world,
            'suggestions': suggestions,
            'issues': issues,
        })
        
        if result.get('success'):
            # Save the updated world
            changes = result.get('changes', [])
            updated_fields = result.get('updated_fields', {})
            
            for field, value in updated_fields.items():
                if hasattr(world, field) and value:
                    setattr(world, field, value)
            
            world.version += 1
            world.save()
            
            return JsonResponse({
                'success': True,
                'changes': changes,
                'message': f'{len(changes)} Änderungen wurden angewendet'
            })
        else:
            return JsonResponse(result)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
