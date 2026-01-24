"""
World Views - User Personalization
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from .models import UserWorld, Character, PersonalPlace


@login_required
def world_detail(request):
    """User world overview."""
    world = UserWorld.get_or_create_for_user(request.user)
    characters = world.characters.filter(is_active=True)
    places = world.personal_places.all()
    
    context = {
        'world': world,
        'characters': characters,
        'places': places,
    }
    return render(request, 'worlds/world_detail.html', context)


@login_required
def world_settings(request):
    """Edit world settings."""
    world = UserWorld.get_or_create_for_user(request.user)
    
    if request.method == 'POST':
        world.name = request.POST.get('name', world.name)
        world.description = request.POST.get('description', '')
        world.default_genre = request.POST.get('default_genre', '')
        world.default_spice_level = request.POST.get('default_spice_level', 'mild')
        world.save()
        messages.success(request, 'Einstellungen gespeichert!')
        return redirect('worlds:detail')
    
    return render(request, 'worlds/world_settings.html', {'world': world})


# ============================================================================
# CHARACTERS
# ============================================================================

@login_required
def character_list(request):
    """List all characters."""
    world = UserWorld.get_or_create_for_user(request.user)
    characters = world.characters.all()
    return render(request, 'worlds/character_list.html', {
        'world': world,
        'characters': characters,
    })


@login_required
def character_add(request):
    """Add new character."""
    world = UserWorld.get_or_create_for_user(request.user)
    
    if request.method == 'POST':
        character = Character.objects.create(
            user_world=world,
            name=request.POST.get('name', ''),
            role=request.POST.get('role', 'protagonist'),
            gender=request.POST.get('gender', 'female'),
            age=request.POST.get('age') or None,
            appearance=request.POST.get('appearance', ''),
            personality=request.POST.get('personality', ''),
            background=request.POST.get('background', ''),
        )
        messages.success(request, f'Charakter "{character.name}" erstellt!')
        
        if request.headers.get('HX-Request'):
            return render(request, 'worlds/partials/character_card.html', {'character': character})
        
        return redirect('worlds:character_list')
    
    return render(request, 'worlds/character_form.html', {'world': world})


@login_required
def character_edit(request, pk):
    """Edit character."""
    world = UserWorld.get_or_create_for_user(request.user)
    character = get_object_or_404(Character, pk=pk, user_world=world)
    
    if request.method == 'POST':
        character.name = request.POST.get('name', character.name)
        character.role = request.POST.get('role', character.role)
        character.gender = request.POST.get('gender', character.gender)
        character.age = request.POST.get('age') or None
        character.appearance = request.POST.get('appearance', '')
        character.personality = request.POST.get('personality', '')
        character.background = request.POST.get('background', '')
        character.save()
        messages.success(request, f'Charakter "{character.name}" aktualisiert!')
        return redirect('worlds:character_list')
    
    return render(request, 'worlds/character_form.html', {
        'world': world,
        'character': character,
    })


@login_required
def character_delete(request, pk):
    """Delete character."""
    world = UserWorld.get_or_create_for_user(request.user)
    character = get_object_or_404(Character, pk=pk, user_world=world)
    
    if request.method == 'POST':
        name = character.name
        character.delete()
        messages.success(request, f'Charakter "{name}" gelöscht.')
        
        if request.headers.get('HX-Request'):
            return HttpResponse('')
        
        return redirect('worlds:character_list')
    
    return render(request, 'worlds/character_confirm_delete.html', {'character': character})


# ============================================================================
# PLACES
# ============================================================================

@login_required
def place_list(request):
    """List all personal places."""
    world = UserWorld.get_or_create_for_user(request.user)
    places = world.personal_places.all()
    return render(request, 'worlds/place_list.html', {
        'world': world,
        'places': places,
    })


@login_required
def place_add(request):
    """Add new personal place."""
    world = UserWorld.get_or_create_for_user(request.user)
    
    if request.method == 'POST':
        place = PersonalPlace.objects.create(
            user_world=world,
            name=request.POST.get('name', ''),
            city=request.POST.get('city', ''),
            country=request.POST.get('country', ''),
            place_type=request.POST.get('place_type', 'include'),
            description=request.POST.get('description', ''),
            personal_memory=request.POST.get('personal_memory', ''),
        )
        messages.success(request, f'Ort "{place.name}" hinzugefügt!')
        
        if request.headers.get('HX-Request'):
            return render(request, 'worlds/partials/place_card.html', {'place': place})
        
        return redirect('worlds:place_list')
    
    return render(request, 'worlds/place_form.html', {'world': world})


@login_required
def place_edit(request, pk):
    """Edit personal place."""
    world = UserWorld.get_or_create_for_user(request.user)
    place = get_object_or_404(PersonalPlace, pk=pk, user_world=world)
    
    if request.method == 'POST':
        place.name = request.POST.get('name', place.name)
        place.city = request.POST.get('city', place.city)
        place.country = request.POST.get('country', place.country)
        place.place_type = request.POST.get('place_type', place.place_type)
        place.description = request.POST.get('description', '')
        place.personal_memory = request.POST.get('personal_memory', '')
        place.save()
        messages.success(request, f'Ort "{place.name}" aktualisiert!')
        return redirect('worlds:place_list')
    
    return render(request, 'worlds/place_form.html', {
        'world': world,
        'place': place,
    })


@login_required
def place_delete(request, pk):
    """Delete personal place."""
    world = UserWorld.get_or_create_for_user(request.user)
    place = get_object_or_404(PersonalPlace, pk=pk, user_world=world)
    
    if request.method == 'POST':
        name = place.name
        place.delete()
        messages.success(request, f'Ort "{name}" gelöscht.')
        
        if request.headers.get('HX-Request'):
            return HttpResponse('')
        
        return redirect('worlds:place_list')
    
    return render(request, 'worlds/place_confirm_delete.html', {'place': place})
