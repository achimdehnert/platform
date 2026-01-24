"""
Creative Agent Views
====================

Views for the Kreativ-Phase - interactive book idea brainstorming.
"""

import json
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .models import CreativeSession, BookIdea, CreativeMessage, AuthorStyleDNA
from .services.creative_agent_service import CreativeAgentService

logger = logging.getLogger(__name__)


@login_required
def creative_dashboard(request):
    """Dashboard for creative sessions."""
    sessions = CreativeSession.objects.filter(author=request.user).order_by('-created_at')[:10]
    
    # Get user's Style DNAs for selection
    style_dnas = AuthorStyleDNA.objects.filter(author=request.user)
    
    # Separate query for active session (can't filter after slice)
    active_session = CreativeSession.objects.filter(
        author=request.user,
        current_phase__in=['brainstorm', 'refining', 'premise']
    ).first()
    
    context = {
        'sessions': sessions,
        'style_dnas': style_dnas,
        'active_session': active_session,
    }
    return render(request, 'writing_hub/creative/dashboard.html', context)


@login_required
def creative_session_create(request):
    """Create a new creative session."""
    from apps.bfagent.models import Llms
    
    if request.method == 'POST':
        name = request.POST.get('name', 'Neue Kreativ-Session')
        initial_input = request.POST.get('initial_input', '')
        genres = request.POST.getlist('genres', [])
        style_dna_id = request.POST.get('style_dna')
        llm_id = request.POST.get('llm')
        
        style_dna = None
        if style_dna_id:
            style_dna = AuthorStyleDNA.objects.filter(id=style_dna_id, author=request.user).first()
        
        llm = None
        if llm_id:
            llm = Llms.objects.filter(id=llm_id, is_active=True).first()
        
        session = CreativeSession.objects.create(
            author=request.user,
            name=name,
            initial_input=initial_input,
            preferred_genres=genres,
            style_dna=style_dna,
            llm=llm,
        )
        
        # Add system message
        llm_info = f" mit {llm.name}" if llm else ""
        CreativeMessage.objects.create(
            session=session,
            sender=CreativeMessage.Sender.SYSTEM,
            content=f"Kreativ-Session '{name}' gestartet{llm_info}.",
            message_type=CreativeMessage.MessageType.TEXT
        )
        
        # If initial input provided, auto-generate ideas
        if initial_input:
            _generate_initial_ideas(session)
        
        return redirect('writing_hub:creative-session', session_id=session.id)
    
    # GET: Show create form
    style_dnas = AuthorStyleDNA.objects.filter(author=request.user)
    genres = ['Fantasy', 'SciFi', 'Thriller', 'Krimi', 'Romance', 'Horror', 'Drama', 'Abenteuer', 'Historisch']
    llms = Llms.objects.filter(is_active=True).order_by('name')
    
    context = {
        'style_dnas': style_dnas,
        'genres': genres,
        'llms': llms,
    }
    return render(request, 'writing_hub/creative/session_create.html', context)


@login_required
def creative_session_detail(request, session_id):
    """View a creative session with chat interface."""
    from django.db.models import Q
    
    session = get_object_or_404(CreativeSession, id=session_id, author=request.user)
    ideas = session.ideas.all().order_by('generation_order')
    
    # Filter messages: if idea is selected, show only messages for that idea
    if session.selected_idea:
        # Show messages linked to selected idea OR system messages without linked ideas
        messages_list = session.messages.filter(
            Q(linked_ideas=session.selected_idea) | 
            Q(linked_ideas__isnull=True, sender='system')
        ).distinct().order_by('created_at')
    else:
        messages_list = session.messages.all().order_by('created_at')
    
    context = {
        'session': session,
        'messages': messages_list,
        'ideas': ideas,
        'can_generate': session.current_phase not in ['completed', 'cancelled'],
    }
    return render(request, 'writing_hub/creative/session_detail.html', context)


@login_required
@require_POST
def creative_send_message(request, session_id):
    """Handle user message in creative session."""
    session = get_object_or_404(CreativeSession, id=session_id, author=request.user)
    
    user_message = request.POST.get('message', '').strip()
    action = request.POST.get('action', 'chat')
    
    if not user_message and action == 'chat':
        return JsonResponse({'error': 'Bitte gib eine Nachricht ein.'}, status=400)
    
    # Save user message
    if user_message:
        CreativeMessage.objects.create(
            session=session,
            sender=CreativeMessage.Sender.USER,
            content=user_message,
            message_type=CreativeMessage.MessageType.TEXT
        )
    
    # Handle different actions
    if action == 'generate_ideas':
        return _handle_generate_ideas(request, session, user_message)
    elif action == 'refine_idea':
        idea_id = request.POST.get('idea_id')
        return _handle_refine_idea(request, session, idea_id, user_message)
    elif action == 'generate_premise':
        idea_id = request.POST.get('idea_id')
        return _handle_generate_premise(request, session, idea_id)
    elif action == 'save_idea':
        idea_id = request.POST.get('idea_id')
        idea_data = request.POST.get('idea_data')
        return _handle_save_idea(request, session, idea_id, idea_data)
    elif action == 'ai_refine':
        idea_id = request.POST.get('idea_id')
        idea_data = request.POST.get('idea_data')
        return _handle_ai_refine(request, session, idea_id, idea_data)
    else:
        # Default: treat as refinement input or general chat
        return _handle_chat(request, session, user_message)
    

@login_required
@require_POST
def creative_rate_idea(request, session_id, idea_id):
    """Rate a book idea."""
    session = get_object_or_404(CreativeSession, id=session_id, author=request.user)
    idea = get_object_or_404(BookIdea, id=idea_id, session=session)
    
    rating = request.POST.get('rating', 'unrated')
    notes = request.POST.get('notes', '')
    
    idea.user_rating = rating
    if notes:
        idea.user_notes = notes
    idea.save()
    
    return JsonResponse({
        'success': True,
        'rating': rating,
        'idea_id': str(idea.id)
    })


@login_required
@require_POST
def creative_select_idea(request, session_id, idea_id):
    """Select an idea for project creation."""
    session = get_object_or_404(CreativeSession, id=session_id, author=request.user)
    idea = get_object_or_404(BookIdea, id=idea_id, session=session)
    
    session.selected_idea = idea
    session.current_phase = CreativeSession.Phase.PREMISE
    session.save()
    
    # If no full premise yet, generate it
    if not idea.has_full_premise:
        _generate_premise_for_idea(session, idea)
    
    messages.success(request, f'Idee "{idea.title_sketch}" ausgewählt!')
    return redirect('writing_hub:creative-session', session_id=session.id)


@login_required
@require_POST
def creative_delete_idea(request, session_id, idea_id):
    """Delete an idea from the session."""
    session = get_object_or_404(CreativeSession, id=session_id, author=request.user)
    idea = get_object_or_404(BookIdea, id=idea_id, session=session)
    
    # Don't allow deleting the selected idea
    if session.selected_idea == idea:
        return JsonResponse({'success': False, 'error': 'Ausgewählte Idee kann nicht gelöscht werden.'}, status=400)
    
    title = idea.title_sketch
    idea.delete()
    
    messages.success(request, f'Idee "{title}" gelöscht.')
    return JsonResponse({'success': True})


@login_required
@require_POST
def creative_create_project(request, session_id):
    """Create a book project from the selected idea."""
    session = get_object_or_404(CreativeSession, id=session_id, author=request.user)
    
    if not session.selected_idea:
        messages.error(request, 'Bitte wähle zuerst eine Idee aus.')
        return redirect('writing_hub:creative-session', session_id=session.id)
    
    idea = session.selected_idea
    
    # Create the project
    from apps.bfagent.models import BookProjects, BookTypes
    
    # Get or create default book type
    book_type, _ = BookTypes.objects.get_or_create(
        name='Roman',
        defaults={
            'description': 'Standard-Roman',
            'complexity': 'medium'
        }
    )
    
    project = BookProjects.objects.create(
        user=request.user,
        owner=request.user,
        title=idea.title_sketch or 'Untitled',
        description=idea.full_premise or idea.hook,
        genre=idea.genre or 'Fiction',
        content_rating='general',
        target_word_count=80000,
        status='planning',
        story_premise=idea.full_premise or idea.hook,
        story_themes=', '.join(idea.themes) if idea.themes else '',
        tagline=idea.hook or '',
        book_type=book_type,
        protagonist_concept=idea.protagonist_sketch or '',
        main_conflict=idea.conflict_sketch or '',
        setting_location=idea.setting_sketch or '',
        unique_elements=', '.join(idea.unique_selling_points) if idea.unique_selling_points else '',
    )
    
    # Create characters and worlds with full content
    from apps.bfagent.models import Characters, Worlds
    
    created_chars = []
    created_worlds = []
    
    # Create protagonist with full details
    if idea.protagonist_sketch:
        char = _create_character_from_idea(
            project=project,
            idea=idea,
            role='Protagonist',
            sketch=idea.protagonist_sketch
        )
        created_chars.append(char.name)
    
    # Extract and create secondary characters (e.g., "und Kael, ein brillanter Physiker")
    secondary_chars = _extract_secondary_characters(idea)
    for sec_char in secondary_chars:
        char = _create_character_from_idea(
            project=project,
            idea=idea,
            role=sec_char['role'],
            sketch=sec_char['description']
        )
        created_chars.append(char.name)
    
    # Create antagonist only if explicitly named in premise
    antagonist_info = _extract_antagonist_info(idea)
    if antagonist_info:
        char = _create_character_from_idea(
            project=project,
            idea=idea,
            role='Antagonist',
            sketch=antagonist_info
        )
        created_chars.append(char.name)
    
    # Create world with full details
    if idea.setting_sketch:
        world = _create_world_from_idea(project=project, idea=idea)
        created_worlds.append(world.name)
    
    # Update session
    session.created_project = project
    session.complete()
    
    # Build completion message
    created_items = ['Projekt']
    if created_chars:
        created_items.append(f'{len(created_chars)} Charaktere ({", ".join(created_chars)})')
    if created_worlds:
        created_items.append(f'{len(created_worlds)} Welt(en)')
    
    CreativeMessage.objects.create(
        session=session,
        sender=CreativeMessage.Sender.SYSTEM,
        content=f'{", ".join(created_items)} erfolgreich erstellt!',
        message_type=CreativeMessage.MessageType.ACTION
    )
    
    messages.success(request, f'Projekt "{project.title}" mit Charakter und Welt erstellt!')
    return redirect('writing_hub:project_hub', project_id=project.id)


def _extract_character_name(description: str) -> str:
    """Extract a character name from description or return empty."""
    import re
    # Try to find a name pattern (capitalized words)
    match = re.search(r'\b([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)\b', description)
    if match:
        return match.group(1)
    return ''


def _extract_world_name(setting: str, title: str) -> str:
    """Extract a world name from setting or generate from title."""
    import re
    # Try to find a location name
    match = re.search(r'\b([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)\b', setting)
    if match and len(match.group(1)) > 3:
        return match.group(1)
    # Fallback: use title-based name
    return f"Welt von {title[:30]}"


def _extract_antagonist_info(idea) -> str:
    """Extract antagonist information from premise or conflict - only if explicitly named."""
    import re
    
    premise = idea.full_premise or ''
    
    # Only extract if there's a clearly named antagonist
    patterns = [
        r'(?:Antagonist|Gegner|Widersacher|Feind|Bösewicht)[:\s]+([A-ZÄÖÜ][a-zäöüß]+)',
        r'(?:der böse|die böse|der dunkle|die dunkle)\s+([A-ZÄÖÜ][a-zäöüß]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, premise, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Filter out common non-name words
            skip_words = ['Bedrohung', 'Gefahr', 'Konflikt', 'Problem', 'Macht', 'Kraft', 'Die', 'Der', 'Das']
            if name not in skip_words and len(name) > 2:
                return name
    
    return ''


def _extract_secondary_characters(idea) -> list:
    """Extract additional named characters from descriptions."""
    import re
    
    characters = []
    protagonist = idea.protagonist_sketch or ''
    premise = idea.full_premise or ''
    combined = f"{protagonist} {premise}"
    
    # Pattern: "und [Name], ein/eine [description]"
    pattern = r'und\s+([A-ZÄÖÜ][a-zäöüß]+),\s+(?:ein|eine)\s+([^,\.]+)'
    matches = re.findall(pattern, combined)
    
    for name, description in matches:
        # Skip if it's the same as protagonist
        protagonist_name = _extract_character_name(protagonist)
        if name != protagonist_name and len(name) > 2:
            characters.append({
                'name': name,
                'description': f"{name}, {description.strip()}",
                'role': 'Nebencharakter'
            })
    
    return characters


def _create_character_from_idea(project, idea, role: str, sketch: str):
    """Create a character with full content derived from idea."""
    from apps.bfagent.models import Characters
    
    name = _extract_character_name(sketch) or role
    genre = idea.genre or 'Fiction'
    themes = idea.themes or []
    
    # Derive personality from role and genre
    personality = _derive_personality(role, genre, sketch)
    
    # Derive motivation from conflict and role
    motivation = _derive_motivation(role, idea.conflict_sketch, sketch)
    
    # Derive background from setting and themes
    background = _derive_background(role, idea.setting_sketch, themes, sketch)
    
    # Derive character arc from conflict
    arc = _derive_character_arc(role, idea.conflict_sketch, themes)
    
    # Derive appearance hints from genre
    appearance = _derive_appearance(role, genre, sketch)
    
    return Characters.objects.create(
        project=project,
        name=name,
        role=role,
        description=sketch,
        personality=personality,
        motivation=motivation,
        background=background,
        arc=arc,
        appearance=appearance,
        conflict=idea.conflict_sketch if role == 'Protagonist' else f"Steht im Konflikt mit dem Protagonisten: {idea.conflict_sketch}" if role == 'Antagonist' else '',
    )


def _derive_personality(role: str, genre: str, sketch: str) -> str:
    """Derive personality traits from role and genre."""
    base_traits = {
        'Protagonist': {
            'Fantasy': 'Mutig, neugierig, mit einem starken Sinn für Gerechtigkeit',
            'SciFi': 'Analytisch, anpassungsfähig, technisch versiert',
            'Romance': 'Emotional offen, verletzlich aber stark, hoffnungsvoll',
            'Thriller': 'Aufmerksam, entschlossen, unter Druck belastbar',
            'Horror': 'Skeptisch zunächst, dann zunehmend entschlossen zu überleben',
            'default': 'Entschlossen, mit inneren Konflikten kämpfend, entwicklungsfähig'
        },
        'Antagonist': {
            'Fantasy': 'Machthungrig, charismatisch, mit eigener verdrehter Logik',
            'SciFi': 'Kalt kalkulierend, visionär aber rücksichtslos',
            'Romance': 'Charmant aber manipulativ, eigene Verletzungen verbergend',
            'Thriller': 'Methodisch, gefährlich intelligent, ohne Empathie',
            'Horror': 'Unheimlich, unberechenbar, von dunklen Motiven getrieben',
            'default': 'Komplex motiviert, glaubt an die Richtigkeit seiner Handlungen'
        }
    }
    
    role_traits = base_traits.get(role, base_traits.get('Protagonist'))
    
    # Find matching genre
    for genre_key in role_traits:
        if genre_key.lower() in genre.lower():
            return role_traits[genre_key]
    
    return role_traits.get('default', 'Vielschichtig und durch die Geschichte geformt')


def _derive_motivation(role: str, conflict: str, sketch: str) -> str:
    """Derive character motivation from conflict and sketch."""
    if role == 'Protagonist':
        if conflict:
            return f"Getrieben von dem Wunsch, {conflict.lower()} zu überwinden und dabei über sich hinauszuwachsen."
        return "Sucht nach Sinn und Erfüllung in einer Welt voller Herausforderungen."
    elif role == 'Antagonist':
        if conflict:
            return f"Verfolgt eigene Ziele, die direkt mit dem Protagonisten kollidieren. Der Konflikt entsteht durch: {conflict}"
        return "Verfolgt einen Plan, der fundamentale Werte des Protagonisten bedroht."
    return sketch[:200] if sketch else "Motivation noch zu entwickeln."


def _derive_background(role: str, setting: str, themes: list, sketch: str) -> str:
    """Derive character background from setting and themes."""
    parts = []
    
    if setting:
        parts.append(f"Aufgewachsen in {setting}.")
    
    if themes:
        theme_influences = {
            'Liebe': 'geprägt von früheren Beziehungserfahrungen',
            'Macht': 'mit dem Streben nach Einfluss vertraut',
            'Familie': 'durch familiäre Bindungen definiert',
            'Identität': 'auf der Suche nach dem eigenen Platz in der Welt',
            'Verlust': 'von Verlusten gezeichnet, die das Leben verändert haben',
            'Freiheit': 'mit dem Wunsch nach Unabhängigkeit aufgewachsen',
            'Vertrauen': 'durch Erfahrungen mit Verrat oder Loyalität geprägt',
        }
        
        for theme in themes[:2]:
            for key, influence in theme_influences.items():
                if key.lower() in theme.lower():
                    parts.append(f"Persönlich {influence}.")
                    break
    
    if not parts:
        parts.append("Hintergrundgeschichte entwickelt sich im Laufe der Handlung.")
    
    return ' '.join(parts)


def _derive_character_arc(role: str, conflict: str, themes: list) -> str:
    """Derive character arc from conflict and themes."""
    if role == 'Protagonist':
        arc_template = "Beginnt als jemand, der {start}. Durch die Ereignisse der Geschichte {middle}. Am Ende {end}."
        
        if 'Liebe' in str(themes):
            return arc_template.format(
                start="emotional verschlossen oder verletzt ist",
                middle="lernt wieder zu vertrauen und sich zu öffnen",
                end="findet wahre Verbindung und emotionale Erfüllung"
            )
        elif conflict:
            return arc_template.format(
                start="mit dem Konflikt hadert",
                middle="wächst an den Herausforderungen",
                end="hat sich fundamental verändert und den Konflikt auf seine Weise gelöst"
            )
        return "Durchläuft eine Transformation von Unsicherheit zu Selbstvertrauen."
    
    elif role == 'Antagonist':
        return "Beginnt als scheinbar unüberwindliche Kraft. Im Verlauf werden Schwächen und die Tragik der eigenen Geschichte sichtbar. Das Ende zeigt die Konsequenzen der gewählten Wege."
    
    return "Charakterentwicklung eng mit der Haupthandlung verwoben."


def _derive_appearance(role: str, genre: str, sketch: str) -> str:
    """Derive appearance hints from role and genre."""
    # Check if sketch already contains appearance info
    appearance_keywords = ['aussehen', 'trägt', 'kleidung', 'haar', 'augen', 'groß', 'klein']
    for keyword in appearance_keywords:
        if keyword in sketch.lower():
            return f"Basierend auf der Beschreibung: {sketch[:150]}..."
    
    # Genre-based defaults
    genre_appearances = {
        'Fantasy': 'Kleidung und Erscheinung passend zur Fantasy-Welt, mit Details die Status und Herkunft zeigen.',
        'SciFi': 'Futuristische oder funktionale Kleidung, möglicherweise mit technischen Elementen.',
        'Romance': 'Attraktive, zum Setting passende Erscheinung, mit Fokus auf emotionalen Ausdruck.',
        'Thriller': 'Unauffällig aber praktisch gekleidet, mit scharfem, aufmerksamem Blick.',
        'Horror': 'Zunächst normal, mit zunehmend sichtbaren Zeichen der durchlebten Ereignisse.',
    }
    
    for genre_key, appearance in genre_appearances.items():
        if genre_key.lower() in genre.lower():
            return appearance
    
    return "Erscheinung passend zum Setting und zur sozialen Stellung des Charakters."


def _create_world_from_idea(project, idea):
    """Create a world with full content derived from idea."""
    from apps.bfagent.models import Worlds
    
    name = _extract_world_name(idea.setting_sketch, idea.title_sketch)
    genre = idea.genre or 'Fiction'
    themes = idea.themes or []
    setting = idea.setting_sketch or ''
    
    # Derive world type from genre
    world_type = _derive_world_type(genre)
    
    # Derive culture from themes
    culture = _derive_culture(themes, genre)
    
    # Derive technology/magic level
    tech_or_magic = _derive_tech_magic(genre, setting)
    
    # Derive atmosphere
    atmosphere = _derive_atmosphere(genre, themes, idea.conflict_sketch)
    
    return Worlds.objects.create(
        project=project,
        name=name,
        world_type=world_type,
        description=setting,
        setting_details=f"{setting}\n\nAtmosphäre: {atmosphere}",
        culture=culture,
        technology_level=tech_or_magic.get('technology', ''),
        magic_system=tech_or_magic.get('magic', ''),
        geography=_derive_geography(setting, genre),
        history=f"Die Geschichte dieser Welt ist eng mit den Themen {', '.join(themes[:3]) if themes else 'der Erzählung'} verwoben.",
        inhabitants=_derive_inhabitants(genre, setting),
    )


def _derive_world_type(genre: str) -> str:
    """Derive world type from genre."""
    if 'fantasy' in genre.lower():
        return 'fantasy'
    elif 'sci' in genre.lower() or 'zukunft' in genre.lower():
        return 'scifi'
    elif 'histor' in genre.lower():
        return 'historical'
    elif 'horror' in genre.lower():
        return 'dark'
    return 'primary'


def _derive_culture(themes: list, genre: str) -> str:
    """Derive cultural aspects from themes."""
    cultural_aspects = []
    
    theme_cultures = {
        'Macht': 'Hierarchische Strukturen mit klaren Machtverhältnissen',
        'Familie': 'Starke Familienbande und Clan-Strukturen prägen die Gesellschaft',
        'Tradition': 'Alte Bräuche und Rituale bestimmen den Alltag',
        'Freiheit': 'Individualismus und persönliche Freiheit werden hoch geschätzt',
        'Liebe': 'Romantik und emotionale Verbindungen haben kulturellen Stellenwert',
        'Konflikt': 'Eine Gesellschaft geprägt von Spannungen und Gegensätzen',
    }
    
    for theme in themes[:3]:
        for key, culture in theme_cultures.items():
            if key.lower() in theme.lower():
                cultural_aspects.append(culture)
                break
    
    if not cultural_aspects:
        cultural_aspects.append(f"Kultur passend zum {genre}-Genre mit eigenen Sitten und Gebräuchen")
    
    return '. '.join(cultural_aspects) + '.'


def _derive_tech_magic(genre: str, setting: str) -> dict:
    """Derive technology or magic level from genre and setting."""
    result = {'technology': '', 'magic': ''}
    
    if 'fantasy' in genre.lower():
        result['magic'] = 'Magie existiert und beeinflusst den Alltag. Die Regeln und Grenzen des magischen Systems sind noch zu definieren.'
        result['technology'] = 'Vorindustriell, mit handwerklicher Tradition.'
    elif 'sci' in genre.lower():
        result['technology'] = 'Fortschrittliche Technologie prägt alle Lebensbereiche. Raumfahrt, KI oder andere Zukunftstechnologien sind möglich.'
        result['magic'] = ''
    elif 'histor' in genre.lower():
        result['technology'] = 'Technologiestand entsprechend der historischen Epoche.'
        result['magic'] = ''
    else:
        result['technology'] = 'Zeitgenössische Technologie entsprechend dem Setting.'
    
    return result


def _derive_atmosphere(genre: str, themes: list, conflict: str) -> str:
    """Derive world atmosphere from genre and themes."""
    base_atmospheres = {
        'Fantasy': 'Wunderbar und geheimnisvoll, mit dem Gefühl endloser Möglichkeiten',
        'SciFi': 'Zukunftsweisend, zwischen technologischer Faszination und Unbehagen',
        'Romance': 'Emotional aufgeladen, romantisch und hoffnungsvoll',
        'Thriller': 'Angespannt und bedrohlich, mit konstantem Gefühl der Gefahr',
        'Horror': 'Unheimlich und bedrückend, das Grauen lauert unter der Oberfläche',
    }
    
    for genre_key, atmosphere in base_atmospheres.items():
        if genre_key.lower() in genre.lower():
            return atmosphere
    
    return 'Eine Atmosphäre, die die Themen der Geschichte unterstreicht.'


def _derive_geography(setting: str, genre: str) -> str:
    """Derive geographical features from setting description."""
    if not setting:
        return 'Geographie noch zu definieren.'
    
    # Extract location hints
    location_keywords = {
        'stadt': 'Urbane Landschaft mit dicht besiedelten Gebieten',
        'dorf': 'Ländliche Gegend mit kleinen Siedlungen',
        'wald': 'Bewaldete Regionen mit natürlicher Wildnis',
        'berg': 'Gebirgige Landschaft mit dramatischen Höhen',
        'meer': 'Küstenregion mit Zugang zum Meer',
        'wüste': 'Karge, trockene Landschaft',
        'insel': 'Isolierte Inselwelt, umgeben von Wasser',
    }
    
    for keyword, geography in location_keywords.items():
        if keyword in setting.lower():
            return geography
    
    return f'Landschaft passend zum Setting: {setting[:100]}'


def _derive_inhabitants(genre: str, setting: str) -> str:
    """Derive inhabitant description from genre and setting."""
    if 'fantasy' in genre.lower():
        return 'Möglicherweise verschiedene Völker und Spezies neben Menschen. Die genaue Zusammensetzung hängt vom Worldbuilding ab.'
    elif 'sci' in genre.lower():
        return 'Menschen und möglicherweise andere intelligente Spezies. Die Gesellschaft ist durch Technologie geprägt.'
    else:
        return 'Menschen verschiedener Kulturen und sozialer Schichten, passend zum Setting.'


# ===== HELPER FUNCTIONS =====

def _build_premise_from_idea(idea) -> str:
    """Build a structured premise from idea content including characters and world."""
    parts = []
    
    # Hook/Main premise
    if idea.hook:
        parts.append(idea.hook)
    
    # Setting
    if idea.setting_sketch:
        parts.append(f"\n\n**Setting:** {idea.setting_sketch}")
    
    # Characters section
    if idea.characters_data:
        chars_text = "\n\n**Charaktere:**\n"
        for char in idea.characters_data:
            if isinstance(char, dict):
                name = char.get('name', 'Unbekannt')
                role = char.get('role', '')
                desc = char.get('description', '')
                motivation = char.get('motivation', '')
                chars_text += f"- **{name}** ({role}): {desc}"
                if motivation:
                    chars_text += f" *Motivation: {motivation}*"
                chars_text += "\n"
        parts.append(chars_text)
    elif idea.protagonist_sketch:
        parts.append(f"\n\n**Protagonist:** {idea.protagonist_sketch}")
    
    # World section
    if idea.world_data and isinstance(idea.world_data, dict) and idea.world_data.get('name'):
        world = idea.world_data
        world_text = f"\n\n**Welt:** {world.get('name', '')}"
        if world.get('description'):
            world_text += f" - {world['description']}"
        if world.get('atmosphere'):
            world_text += f" *({world['atmosphere']})*"
        if world.get('key_features'):
            features = world['key_features']
            if isinstance(features, list) and features:
                world_text += f"\nBesonderheiten: {', '.join(features)}"
        parts.append(world_text)
    
    # Conflict
    if idea.conflict_sketch:
        parts.append(f"\n\n**Konflikt:** {idea.conflict_sketch}")
    
    return ''.join(parts)


def _generate_initial_ideas(session):
    """Generate initial ideas for a session."""
    service = CreativeAgentService(llm=session.llm)
    
    result = service.brainstorm_ideas(
        initial_input=session.initial_input,
        genres=session.preferred_genres,
        style_dna=session.style_dna,
        constraints=session.constraints
    )
    
    if result.success:
        # Create BookIdea objects
        for i, idea_sketch in enumerate(result.ideas):
            BookIdea.objects.create(
                session=session,
                title_sketch=idea_sketch.title_sketch,
                hook=idea_sketch.hook,
                genre=idea_sketch.genre,
                setting_sketch=idea_sketch.setting_sketch,
                protagonist_sketch=idea_sketch.protagonist_sketch,
                conflict_sketch=idea_sketch.conflict_sketch,
                generation_order=i
            )
        
        # Add agent message
        CreativeMessage.objects.create(
            session=session,
            sender=CreativeMessage.Sender.AGENT,
            content=result.agent_message,
            message_type=CreativeMessage.MessageType.IDEAS,
            metadata={'usage': result.usage} if result.usage else {}
        )


def _handle_generate_ideas(request, session, user_input):
    """Handle generate ideas action."""
    service = CreativeAgentService(llm=session.llm)
    
    result = service.brainstorm_ideas(
        initial_input=user_input or session.initial_input,
        genres=session.preferred_genres,
        style_dna=session.style_dna
    )
    
    ideas_created = []
    if result.success:
        existing_count = session.ideas.count()
        for i, idea_sketch in enumerate(result.ideas):
            idea = BookIdea.objects.create(
                session=session,
                title_sketch=idea_sketch.title_sketch,
                hook=idea_sketch.hook,
                genre=idea_sketch.genre,
                setting_sketch=idea_sketch.setting_sketch,
                protagonist_sketch=idea_sketch.protagonist_sketch,
                conflict_sketch=idea_sketch.conflict_sketch,
                generation_order=existing_count + i
            )
            ideas_created.append({
                'id': str(idea.id),
                'title': idea.title_sketch,
                'hook': idea.hook,
                'genre': idea.genre
            })
        
        CreativeMessage.objects.create(
            session=session,
            sender=CreativeMessage.Sender.AGENT,
            content=result.agent_message,
            message_type=CreativeMessage.MessageType.IDEAS
        )
    
    return JsonResponse({
        'success': result.success,
        'ideas': ideas_created,
        'message': result.agent_message,
        'error': result.error
    })


def _handle_refine_idea(request, session, idea_id, feedback):
    """Handle refine idea action."""
    idea = get_object_or_404(BookIdea, id=idea_id, session=session)
    
    service = CreativeAgentService(llm=session.llm)
    
    from .services.creative_agent_service import IdeaSketch
    idea_sketch = IdeaSketch(
        title_sketch=idea.title_sketch,
        hook=idea.hook,
        genre=idea.genre,
        setting_sketch=idea.setting_sketch,
        protagonist_sketch=idea.protagonist_sketch,
        conflict_sketch=idea.conflict_sketch
    )
    
    result = service.refine_idea(idea_sketch, feedback)
    
    if result.success and result.ideas:
        refined = result.ideas[0]
        
        # Store history
        idea.refinement_history.append({
            'before': {
                'title': idea.title_sketch,
                'hook': idea.hook
            },
            'feedback': feedback,
            'after': {
                'title': refined.title_sketch,
                'hook': refined.hook
            }
        })
        
        # Update idea
        idea.title_sketch = refined.title_sketch
        idea.hook = refined.hook
        idea.genre = refined.genre or idea.genre
        idea.setting_sketch = refined.setting_sketch or idea.setting_sketch
        idea.protagonist_sketch = refined.protagonist_sketch or idea.protagonist_sketch
        idea.conflict_sketch = refined.conflict_sketch or idea.conflict_sketch
        idea.refinement_count += 1
        idea.save()
        
        session.current_phase = CreativeSession.Phase.REFINING
        session.save()
        
        CreativeMessage.objects.create(
            session=session,
            sender=CreativeMessage.Sender.AGENT,
            content=result.agent_message,
            message_type=CreativeMessage.MessageType.TEXT
        )
    
    # Build detailed response message for iterative refinement
    if result.success:
        response_message = f"""**Idee verfeinert:** "{idea.title_sketch}"

**Hook:** {idea.hook}

{result.agent_message}

💡 *Möchtest du weitere Änderungen? Schreib einfach, was du anpassen möchtest.*"""
    else:
        response_message = result.error or "Fehler bei der Verfeinerung."
    
    return JsonResponse({
        'success': result.success,
        'idea': {
            'id': str(idea.id),
            'title': idea.title_sketch,
            'hook': idea.hook,
            'genre': idea.genre,
            'setting': idea.setting_sketch,
            'protagonist': idea.protagonist_sketch,
            'conflict': idea.conflict_sketch
        } if result.success else None,
        'message': response_message,
        'error': result.error
    })


def _handle_generate_premise(request, session, idea_id):
    """Handle generate premise action."""
    idea = get_object_or_404(BookIdea, id=idea_id, session=session)
    
    _generate_premise_for_idea(session, idea)
    
    return JsonResponse({
        'success': True,
        'premise': idea.full_premise,
        'themes': idea.themes,
        'idea_id': str(idea.id)
    })


def _generate_premise_for_idea(session, idea):
    """Generate full premise for an idea."""
    service = CreativeAgentService(llm=session.llm)
    
    from .services.creative_agent_service import IdeaSketch
    idea_sketch = IdeaSketch(
        title_sketch=idea.title_sketch,
        hook=idea.hook,
        genre=idea.genre,
        setting_sketch=idea.setting_sketch,
        protagonist_sketch=idea.protagonist_sketch,
        conflict_sketch=idea.conflict_sketch
    )
    
    result = service.generate_full_premise(idea_sketch, session.style_dna)
    
    if result.success and result.premise:
        idea.has_full_premise = True
        idea.full_premise = result.premise.premise
        idea.themes = result.premise.themes
        idea.unique_selling_points = result.premise.unique_selling_points
        idea.save()
        
        # Build full premise message
        premise_text = f"""Hier ist die ausführliche Premise für deine Geschichte:

**{idea.title_sketch}**

{result.premise.premise}

**Themen:** {', '.join(result.premise.themes) if result.premise.themes else 'Nicht definiert'}

**Besonderheiten:** {', '.join(result.premise.unique_selling_points) if result.premise.unique_selling_points else 'Nicht definiert'}

💡 *Klicke auf "Auswählen" um diese Idee für dein Buchprojekt zu verwenden.*"""
        
        CreativeMessage.objects.create(
            session=session,
            sender=CreativeMessage.Sender.AGENT,
            content=premise_text,
            message_type=CreativeMessage.MessageType.PREMISE
        )


def _handle_save_idea(request, session, idea_id, idea_data_json):
    """Handle direct save of edited idea including characters and world."""
    import json
    idea = get_object_or_404(BookIdea, id=idea_id, session=session)
    
    try:
        data = json.loads(idea_data_json)
        
        # Update idea fields
        idea.title_sketch = data.get('title_sketch', idea.title_sketch)
        idea.hook = data.get('hook', idea.hook)
        idea.genre = data.get('genre', idea.genre)
        idea.setting_sketch = data.get('setting_sketch', idea.setting_sketch)
        idea.protagonist_sketch = data.get('protagonist_sketch', idea.protagonist_sketch)
        idea.conflict_sketch = data.get('conflict_sketch', idea.conflict_sketch)
        
        # Save characters and world data
        if 'characters' in data:
            idea.characters_data = data['characters']
        if 'world' in data:
            idea.world_data = data['world']
        
        # Update full_premise based on current content
        idea.full_premise = _build_premise_from_idea(idea)
        idea.has_full_premise = True
        
        idea.save()
        
        return JsonResponse({
            'success': True,
            'idea': {
                'id': str(idea.id),
                'title': idea.title_sketch,
                'hook': idea.hook,
                'genre': idea.genre,
                'setting': idea.setting_sketch,
                'protagonist': idea.protagonist_sketch,
                'conflict': idea.conflict_sketch
            },
            'characters': idea.characters_data,
            'world': idea.world_data,
            'message': 'Idee mit Charakteren und Welt gespeichert!'
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Ungültige Daten'}, status=400)


def _handle_ai_refine(request, session, idea_id, idea_data_json):
    """Handle AI-assisted refinement of idea."""
    import json
    import logging
    from apps.bfagent.models import Llms
    logger = logging.getLogger(__name__)
    
    logger.info(f"=== AI REFINE START ===")
    logger.info(f"idea_id={idea_id}, idea_data_json type={type(idea_data_json)}, len={len(idea_data_json) if idea_data_json else 0}")
    if idea_data_json:
        logger.info(f"idea_data_json[:200]={idea_data_json[:200]}")
    
    idea = get_object_or_404(BookIdea, id=idea_id, session=session)
    
    try:
        data = json.loads(idea_data_json)
        logger.info(f"AI Refine: Starting for idea {idea_id}")
        logger.info(f"AI Refine: Input data: {data}")
        
        # Use session's LLM or fall back to first active LLM
        llm = session.llm
        if not llm or not llm.is_active:
            llm = Llms.objects.filter(is_active=True).first()
            if llm:
                logger.info(f"AI Refine: Session had no LLM, using fallback: {llm.name}")
                # Optionally update session for future use
                session.llm = llm
                session.save(update_fields=['llm'])
            else:
                logger.error("AI Refine: No active LLM found in database")
                return JsonResponse({
                    'success': False,
                    'error': 'Kein aktives LLM konfiguriert. Bitte unter AI-Config ein LLM aktivieren.'
                })
        
        logger.info(f"AI Refine: Using LLM {llm.name} (provider={llm.provider}, model={llm.llm_name})")
        service = CreativeAgentService(llm=llm)
        
        from .services.creative_agent_service import IdeaSketch
        idea_sketch = IdeaSketch(
            title_sketch=data.get('title_sketch', idea.title_sketch),
            hook=data.get('hook', idea.hook),
            genre=data.get('genre', idea.genre),
            setting_sketch=data.get('setting_sketch', idea.setting_sketch),
            protagonist_sketch=data.get('protagonist_sketch', idea.protagonist_sketch),
            conflict_sketch=data.get('conflict_sketch', idea.conflict_sketch)
        )
        
        # Ask AI to improve the idea
        result = service.refine_idea(idea_sketch, "Verbessere und verfeinere diese Buchidee. Mache sie packender und origineller.")
        
        logger.info(f"AI Refine: Result success={result.success}, error={result.error}, ideas_count={len(result.ideas) if result.ideas else 0}")
        
        if result.success and result.ideas:
            refined = result.ideas[0]
            logger.info(f"AI Refine: Refined title: {refined.title_sketch}")
            logger.info(f"AI Refine: Characters: {len(refined.characters)}, World: {refined.world is not None}")
            
            # Validate that we actually have meaningful content
            # Use original values as fallback for empty fields
            final_title = refined.title_sketch if refined.title_sketch and refined.title_sketch != 'Untitled' else data.get('title_sketch', idea.title_sketch)
            final_hook = refined.hook if refined.hook else data.get('hook', idea.hook)
            final_genre = refined.genre if refined.genre else data.get('genre', idea.genre)
            final_setting = refined.setting_sketch if refined.setting_sketch else data.get('setting_sketch', idea.setting_sketch)
            final_protagonist = refined.protagonist_sketch if refined.protagonist_sketch else data.get('protagonist_sketch', idea.protagonist_sketch)
            final_conflict = refined.conflict_sketch if refined.conflict_sketch else data.get('conflict_sketch', idea.conflict_sketch)
            
            # Check if we got any real improvement
            has_improvement = (
                (refined.title_sketch and refined.title_sketch != 'Untitled') or
                refined.hook or refined.genre or refined.setting_sketch or
                refined.protagonist_sketch or refined.conflict_sketch or
                refined.characters or refined.world
            )
            
            if not has_improvement:
                logger.warning("AI Refine: No meaningful improvements received from LLM")
                return JsonResponse({
                    'success': False,
                    'error': 'KI konnte keine Verbesserungen generieren. Bitte erneut versuchen.'
                })
            
            # Build response with characters and world
            response_data = {
                'success': True,
                'idea': {
                    'id': str(idea.id),
                    'title': final_title,
                    'hook': final_hook,
                    'genre': final_genre,
                    'setting': final_setting,
                    'protagonist': final_protagonist,
                    'conflict': final_conflict
                },
                'characters': [
                    {
                        'name': c.name,
                        'role': c.role,
                        'description': c.description,
                        'motivation': c.motivation
                    } for c in refined.characters
                ] if refined.characters else [],
                'world': {
                    'name': refined.world.name,
                    'description': refined.world.description,
                    'key_features': refined.world.key_features,
                    'atmosphere': refined.world.atmosphere
                } if refined.world else None,
                'message': 'KI hat die Idee verbessert!'
            }
            return JsonResponse(response_data)
        else:
            logger.warning(f"AI Refine failed: {result.error}")
            return JsonResponse({
                'success': False,
                'error': result.error or 'KI-Verbesserung fehlgeschlagen'
            })
    except json.JSONDecodeError as e:
        logger.error(f"AI Refine JSON error: {e}")
        return JsonResponse({'success': False, 'error': 'Ungültige Daten'}, status=400)


def _handle_chat(request, session, message):
    """Handle general chat message."""
    # For now, treat as refinement request if there are ideas
    ideas = session.ideas.filter(user_rating__in=['love', 'like']).first()
    
    if ideas:
        return _handle_refine_idea(request, session, ideas.id, message)
    
    # Otherwise, generate new ideas
    return _handle_generate_ideas(request, session, message)
