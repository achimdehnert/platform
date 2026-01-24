"""
World Building Views - Book Writing Domain
CRUD operations for WorldSetting, Location, and WorldRule
"""
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from apps.bfagent.models import BookProjects, Agents, Worlds
# TODO: Re-enable when world_models is created
# from ..models.world_models import WorldSetting, Location, WorldRule
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)


@login_required
def project_worlds_list(request, pk):
    """
    Display worlds list for a specific project
    Shows all worlds associated with the project with filtering and pagination
    """
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    
    # Get all worlds for this project
    worlds = Worlds.objects.filter(project=project).order_by("-created_at")
    
    # Apply filters
    world_type_filter = request.GET.get('type', '')
    if world_type_filter:
        worlds = worlds.filter(world_type=world_type_filter)
    
    # Pagination
    paginator = Paginator(worlds, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "project": project,
        "page_obj": page_obj,
        "type_filter": world_type_filter,
        "world_count": worlds.count(),
    }
    
    return render(request, 'bfagent/project_worlds_list.html', context)


@login_required
def world_detail(request, pk):
    """
    Display world details for a project
    Shows world setting, locations, and rules
    """
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    
    try:
        world = project.world
    except WorldSetting.DoesNotExist:
        world = None
    
    locations = world.locations.all() if world else []
    rules = world.rules.all() if world else []
    
    context = {
        'project': project,
        'world': world,
        'locations': locations,
        'rules': rules,
    }
    
    return render(request, 'bfagent/world/world_detail.html', context)


@login_required
def world_create_or_edit(request, pk):
    """
    Create or edit world setting for a project
    """
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    
    try:
        world = project.world
        is_create = False
    except WorldSetting.DoesNotExist:
        world = None
        is_create = True
    
    if request.method == 'POST':
        try:
            if is_create:
                world = WorldSetting.objects.create(
                    project=project,
                    name=request.POST.get('name', f"{project.title} World"),
                    description=request.POST.get('description', ''),
                    time_period=request.POST.get('time_period', ''),
                    geography=request.POST.get('geography', ''),
                    culture=request.POST.get('culture', ''),
                    technology_level=request.POST.get('technology_level', ''),
                    magic_system=request.POST.get('magic_system', ''),
                    political_system=request.POST.get('political_system', ''),
                    economy=request.POST.get('economy', ''),
                    history=request.POST.get('history', ''),
                    atmosphere=request.POST.get('atmosphere', '')
                )
                messages.success(request, f'World "{world.name}" erfolgreich erstellt!')
                logger.info(f"Created world {world.id} for project {pk}")
            else:
                world.name = request.POST.get('name', world.name)
                world.description = request.POST.get('description', '')
                world.time_period = request.POST.get('time_period', '')
                world.geography = request.POST.get('geography', '')
                world.culture = request.POST.get('culture', '')
                world.technology_level = request.POST.get('technology_level', '')
                world.magic_system = request.POST.get('magic_system', '')
                world.political_system = request.POST.get('political_system', '')
                world.economy = request.POST.get('economy', '')
                world.history = request.POST.get('history', '')
                world.atmosphere = request.POST.get('atmosphere', '')
                world.save()
                messages.success(request, f'World "{world.name}" erfolgreich aktualisiert!')
                logger.info(f"Updated world {world.id}")
            
            return redirect('bfagent:world-detail', pk=pk)
            
        except Exception as e:
            logger.error(f"Error saving world: {e}", exc_info=True)
            messages.error(request, f'Fehler beim Speichern: {str(e)}')
    
    context = {
        'project': project,
        'world': world,
        'is_create': is_create
    }
    
    return render(request, 'bfagent/world/world_form.html', context)


@login_required
def location_create(request, pk):
    """Create new location"""
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    world = get_object_or_404(WorldSetting, project=project)
    
    if request.method == 'POST':
        try:
            location = Location.objects.create(
                world=world,
                name=request.POST.get('name', ''),
                location_type=request.POST.get('location_type', ''),
                description=request.POST.get('description', ''),
                atmosphere=request.POST.get('atmosphere', ''),
                importance=request.POST.get('importance', 'minor'),
                notes=request.POST.get('notes', '')
            )
            messages.success(request, f'Location "{location.name}" erstellt!')
            return redirect('bfagent:world-detail', pk=pk)
        except Exception as e:
            logger.error(f"Error creating location: {e}", exc_info=True)
            messages.error(request, f'Fehler: {str(e)}')
    
    context = {'project': project, 'world': world, 'is_create': True}
    return render(request, 'bfagent/world/location_form.html', context)


@login_required
def location_edit(request, pk, location_pk):
    """Edit existing location"""
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    world = get_object_or_404(WorldSetting, project=project)
    location = get_object_or_404(Location, pk=location_pk, world=world)
    
    if request.method == 'POST':
        try:
            location.name = request.POST.get('name', location.name)
            location.location_type = request.POST.get('location_type', '')
            location.description = request.POST.get('description', '')
            location.atmosphere = request.POST.get('atmosphere', '')
            location.importance = request.POST.get('importance', 'minor')
            location.notes = request.POST.get('notes', '')
            location.save()
            messages.success(request, f'Location "{location.name}" aktualisiert!')
            return redirect('bfagent:world-detail', pk=pk)
        except Exception as e:
            logger.error(f"Error updating location: {e}", exc_info=True)
            messages.error(request, f'Fehler: {str(e)}')
    
    context = {'project': project, 'world': world, 'location': location, 'is_create': False}
    return render(request, 'bfagent/world/location_form.html', context)


@require_http_methods(["POST"])
@login_required
def location_delete(request, pk, location_pk):
    """Delete location"""
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    world = get_object_or_404(WorldSetting, project=project)
    location = get_object_or_404(Location, pk=location_pk, world=world)
    
    name = location.name
    location.delete()
    messages.success(request, f'Location "{name}" gelöscht!')
    return redirect('bfagent:world-detail', pk=pk)


@login_required
def rule_create(request, pk):
    """Create new world rule"""
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    world = get_object_or_404(WorldSetting, project=project)
    
    if request.method == 'POST':
        try:
            rule = WorldRule.objects.create(
                world=world,
                category=request.POST.get('category', 'other'),
                title=request.POST.get('title', ''),
                description=request.POST.get('description', ''),
                importance=request.POST.get('importance', 'important')
            )
            messages.success(request, f'Rule "{rule.title}" erstellt!')
            return redirect('bfagent:world-detail', pk=pk)
        except Exception as e:
            logger.error(f"Error creating rule: {e}", exc_info=True)
            messages.error(request, f'Fehler: {str(e)}')
    
    context = {'project': project, 'world': world, 'is_create': True}
    return render(request, 'bfagent/world/rule_form.html', context)


@login_required
def rule_edit(request, pk, rule_pk):
    """Edit existing world rule"""
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    world = get_object_or_404(WorldSetting, project=project)
    rule = get_object_or_404(WorldRule, pk=rule_pk, world=world)
    
    if request.method == 'POST':
        try:
            rule.category = request.POST.get('category', 'other')
            rule.title = request.POST.get('title', rule.title)
            rule.description = request.POST.get('description', '')
            rule.importance = request.POST.get('importance', 'important')
            rule.save()
            messages.success(request, f'Rule "{rule.title}" aktualisiert!')
            return redirect('bfagent:world-detail', pk=pk)
        except Exception as e:
            logger.error(f"Error updating rule: {e}", exc_info=True)
            messages.error(request, f'Fehler: {str(e)}')
    
    context = {'project': project, 'world': world, 'rule': rule, 'is_create': False}
    return render(request, 'bfagent/world/rule_form.html', context)


@require_http_methods(["POST"])
@login_required
def rule_delete(request, pk, rule_pk):
    """Delete world rule"""
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    world = get_object_or_404(WorldSetting, project=project)
    rule = get_object_or_404(WorldRule, pk=rule_pk, world=world)
    
    title = rule.title
    rule.delete()
    messages.success(request, f'Rule "{title}" gelöscht!')
    return redirect('bfagent:world-detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def world_generate(request, pk):
    """
    Generate world(s) using WorldCreationHandler
    
    Uses AI to generate rich world definitions from project data.
    """
    project = get_object_or_404(BookProjects, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            from apps.core.handlers.domains.bookwriting import WorldCreationHandler
            
            # Get parameters from request
            world_count = int(request.POST.get('world_count', 1))
            world_names_str = request.POST.get('world_names', '')
            world_names = [n.strip() for n in world_names_str.split(',') if n.strip()] if world_names_str else []
            
            # Get active agent
            agent = Agents.objects.filter(status='active').first()
            if not agent:
                messages.error(request, 'Kein aktiver Agent gefunden!')
                return redirect('bfagent:world-list')
            
            # Execute handler
            handler = WorldCreationHandler()
            result = handler.execute({
                'project': project,
                'agent': agent,
                'world_count': world_count,
                'world_names': world_names,
                'user': request.user,
            })
            
            if result['success']:
                worlds_created = len(result['worlds'])
                messages.success(
                    request,
                    f'{worlds_created} Welt(en) erfolgreich mit AI erstellt!'
                )
                logger.info(f"Created {worlds_created} worlds for project {pk} using handler")
            else:
                error_msg = result.get('error', 'Unbekannter Fehler')
                messages.error(request, f'Fehler beim Erstellen: {error_msg}')
                logger.error(f"World creation failed: {error_msg}")
            
            # Redirect to worlds list
            return redirect('bfagent:world-list')
        
        except Exception as e:
            logger.error(f"Error in world_generate: {e}", exc_info=True)
            messages.error(request, f'Fehler: {str(e)}')
            return redirect('bfagent:world-list')
