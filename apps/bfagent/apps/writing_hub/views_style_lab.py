"""
Style Lab Views
===============

Web interface for the Style Generation & Adoption System (SGAS).

Workflow:
1. Dashboard - Übersicht aller Stile und Sessions
2. New Session - Neue Stil-Entwicklung starten
3. Extraction - Beispieltexte analysieren
4. Synthesis - Test-Szenen generieren
5. Feedback - Autor bewertet
6. Fixation - Stil finalisieren
"""

import json
import logging
from typing import Optional
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .models_style import (
    AuthorStyleDNA,
    StyleLabSession,
    StyleObservation,
    StyleCandidate,
    SentenceFeedback,
    StyleFeedback,
    StyleAcceptanceTest,
    StyleAdoption,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DASHBOARD
# =============================================================================

@login_required
def style_lab_dashboard(request):
    """
    Style Lab Dashboard - Übersicht aller Stile und Sessions.
    """
    user = request.user
    
    # Eigene Style DNAs
    my_styles = AuthorStyleDNA.objects.filter(author=user).order_by('-is_primary', 'name')
    
    # Get user's Authors with their WritingStyles
    from .models import Author
    my_authors = Author.objects.filter(
        created_by=user, is_active=True
    ).prefetch_related('writing_styles').order_by('name')
    
    # Primary style
    primary_style = my_styles.filter(is_primary=True).first()
    
    # Stats (simplified)
    stats = {
        'total_styles': my_styles.count(),
    }
    
    context = {
        'my_styles': my_styles,
        'my_authors': my_authors,
        'primary_style': primary_style,
        'stats': stats,
    }
    
    return render(request, 'writing_hub/style_lab/dashboard.html', context)


# =============================================================================
# STYLE BUILDER (NEW - Iterative Style Creation)
# =============================================================================

@login_required
def style_builder(request, dna_id=None):
    """
    Neuer iterativer Style Builder.
    
    Workflow:
    1. Beispieltext eingeben → LLM extrahiert DO/DON'T/Signature/Taboo
    2. Regeln anzeigen und manuell anpassen
    3. Testtext generieren
    4. Bewerten: Akzeptieren oder mehr Texte hinzufügen
    5. Bei Akzeptanz: Style DNA speichern
    
    Optional: dna_id um bestehende DNA zu laden und zu verfeinern.
    """
    from apps.bfagent.models import Llms
    from apps.writing_hub.services.style_lab_service import StyleLabService
    
    existing_dna = None
    
    # Wenn DNA-ID übergeben: Bestehende DNA laden
    if dna_id:
        try:
            existing_dna = AuthorStyleDNA.objects.get(id=dna_id, author=request.user)
            # Session mit DNA-Daten initialisieren
            request.session['style_builder'] = {
                'example_texts': [],  # Keine alten Texte - nur neue hinzufügen
                'do_list': existing_dna.do_list or [],
                'dont_list': existing_dna.dont_list or [],
                'signature_moves': existing_dna.signature_moves or [],
                'taboo_list': existing_dna.taboo_list or [],
                'style_summary': '',  # AuthorStyleDNA hat kein description-Feld
                'test_results': [],
                'preferred_llm_id': str(existing_dna.preferred_llm_id) if existing_dna.preferred_llm_id else None,
                'editing_dna_id': str(dna_id),  # Merken, dass wir bearbeiten
                'editing_dna_name': existing_dna.name,
            }
            request.session.modified = True
        except AuthorStyleDNA.DoesNotExist:
            pass
    
    # Session-Daten für den Builder
    builder_data = request.session.get('style_builder', {
        'example_texts': [],
        'do_list': [],
        'dont_list': [],
        'signature_moves': [],
        'taboo_list': [],
        'style_summary': '',
        'test_results': [],
        'preferred_llm_id': None,
        'editing_dna_id': None,
        'editing_dna_name': None,
    })
    
    available_llms = Llms.objects.filter(is_active=True).order_by('provider', 'name')
    
    context = {
        'builder_data': builder_data,
        'available_llms': available_llms,
        'example_count': len(builder_data.get('example_texts', [])),
        'existing_dna': existing_dna,
        'editing_mode': bool(builder_data.get('editing_dna_id')),
    }
    
    return render(request, 'writing_hub/style_lab/style_builder.html', context)


@login_required
@require_POST
def style_builder_extract(request):
    """AJAX: Extrahiert Stilregeln aus Beispieltext."""
    import json
    from apps.bfagent.models import Llms
    from apps.writing_hub.services.style_lab_service import StyleLabService
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    example_text = data.get('example_text', '').strip()
    llm_id = data.get('llm_id')
    
    if not example_text:
        return JsonResponse({'ok': False, 'error': 'Kein Text angegeben'})
    
    if len(example_text) < 100:
        return JsonResponse({'ok': False, 'error': 'Text zu kurz (min. 100 Zeichen)'})
    
    # LLM holen
    preferred_llm = None
    if llm_id:
        try:
            preferred_llm = Llms.objects.get(id=int(llm_id), is_active=True)
        except (Llms.DoesNotExist, ValueError):
            pass
    
    service = StyleLabService(llm=preferred_llm)
    
    # Builder-Daten aus Session
    builder_data = request.session.get('style_builder', {
        'example_texts': [],
        'do_list': [],
        'dont_list': [],
        'signature_moves': [],
        'taboo_list': [],
        'style_summary': '',
    })
    
    # Wenn bereits Regeln existieren: Refinement, sonst Extraktion
    if builder_data.get('do_list') or builder_data.get('dont_list'):
        result = service.refine_style_rules(
            new_text=example_text,
            existing_do=builder_data.get('do_list', []),
            existing_dont=builder_data.get('dont_list', []),
            existing_signature=builder_data.get('signature_moves', []),
            existing_taboo=builder_data.get('taboo_list', []),
        )
    else:
        result = service.extract_style_rules(example_text)
    
    if result.get('ok'):
        # Session aktualisieren
        builder_data['example_texts'].append(example_text[:500] + '...' if len(example_text) > 500 else example_text)
        builder_data['do_list'] = result.get('do_list', [])
        builder_data['dont_list'] = result.get('dont_list', [])
        builder_data['signature_moves'] = result.get('signature_moves', [])
        builder_data['taboo_list'] = result.get('taboo_list', [])
        builder_data['style_summary'] = result.get('style_summary', '')
        builder_data['preferred_llm_id'] = llm_id
        
        request.session['style_builder'] = builder_data
        request.session.modified = True
        
        return JsonResponse({
            'ok': True,
            'do_list': result.get('do_list', []),
            'dont_list': result.get('dont_list', []),
            'signature_moves': result.get('signature_moves', []),
            'taboo_list': result.get('taboo_list', []),
            'style_summary': result.get('style_summary', ''),
            'changes_made': result.get('changes_made', []),
            'llm_used': result.get('llm_used', 'Unbekannt'),
            'example_count': len(builder_data['example_texts']),
        })
    else:
        return JsonResponse({
            'ok': False,
            'error': result.get('error', 'Extraktion fehlgeschlagen'),
        })


@login_required
@require_POST
def style_builder_test(request):
    """AJAX: Generiert Testtext mit aktuellen Stilregeln."""
    import json
    from apps.bfagent.models import Llms
    from apps.writing_hub.services.style_lab_service import StyleLabService
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    scene_type = data.get('scene_type', 'dialogue')
    context_text = data.get('context', '')
    llm_id = data.get('llm_id')
    
    # Aktuelle Regeln aus Request (können vom User angepasst sein)
    do_list = data.get('do_list', [])
    dont_list = data.get('dont_list', [])
    signature_moves = data.get('signature_moves', [])
    taboo_list = data.get('taboo_list', [])
    
    # LLM holen
    preferred_llm = None
    if llm_id:
        try:
            preferred_llm = Llms.objects.get(id=int(llm_id), is_active=True)
        except (Llms.DoesNotExist, ValueError):
            pass
    
    service = StyleLabService(llm=preferred_llm)
    
    # Style-Profil aufbauen
    style_profile = {
        'signature_moves': signature_moves,
        'do_list': do_list,
        'dont_list': dont_list,
        'taboo_list': taboo_list,
    }
    
    # DEBUG: Log what we're passing
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== STYLE BUILDER TEST ===")
    logger.info(f"Scene Type: {scene_type}")
    logger.info(f"Context/Theme: {context_text}")
    logger.info(f"LLM ID: {llm_id}, LLM Object: {preferred_llm}")
    logger.info(f"DO List ({len(do_list)}): {do_list[:3]}...")
    logger.info(f"DON'T List ({len(dont_list)}): {dont_list[:3]}...")
    logger.info(f"Signature Moves: {signature_moves[:3]}...")
    logger.info(f"Taboo List: {taboo_list[:3]}...")
    
    result = service.generate_scene(
        scene_type=scene_type,
        style_profile=style_profile,
        do_patterns=do_list,
        dont_patterns=dont_list + taboo_list,
        original_text=context_text if context_text else None,
    )
    
    logger.info(f"Result: success={result.success}, llm_used={result.llm_used}")
    
    if result.success:
        return JsonResponse({
            'ok': True,
            'text': result.text,
            'llm_used': result.llm_used or 'Unbekannt',
            'scene_type': scene_type,
        })
    else:
        return JsonResponse({
            'ok': False,
            'error': result.error or 'Generierung fehlgeschlagen',
        })


@login_required
@require_POST
def style_builder_save(request):
    """Speichert den finalen Style als DNA (neu oder Update)."""
    import json
    from apps.bfagent.models import Llms
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Name ist erforderlich'})
    
    do_list = data.get('do_list', [])
    dont_list = data.get('dont_list', [])
    signature_moves = data.get('signature_moves', [])
    taboo_list = data.get('taboo_list', [])
    is_primary = data.get('is_primary', False)
    llm_id = data.get('llm_id')
    editing_dna_id = data.get('editing_dna_id')  # ID wenn wir updaten
    
    # Preferred LLM
    preferred_llm = None
    if llm_id:
        try:
            preferred_llm = Llms.objects.get(id=int(llm_id), is_active=True)
        except (Llms.DoesNotExist, ValueError):
            pass
    
    with transaction.atomic():
        if is_primary:
            AuthorStyleDNA.objects.filter(
                author=request.user, is_primary=True
            ).update(is_primary=False)
        
        # Update oder Create?
        if editing_dna_id:
            # Bestehende DNA updaten
            try:
                dna = AuthorStyleDNA.objects.get(id=editing_dna_id, author=request.user)
                dna.name = name
                dna.signature_moves = signature_moves
                dna.do_list = do_list
                dna.dont_list = dont_list
                dna.taboo_list = taboo_list
                dna.preferred_llm = preferred_llm
                dna.is_primary = is_primary
                dna.version = dna.version + 1  # Version erhöhen
                dna.save()
                message = f'Style DNA "{name}" erfolgreich aktualisiert (v{dna.version})!'
            except AuthorStyleDNA.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'DNA nicht gefunden'})
        else:
            # Neue DNA erstellen
            dna = AuthorStyleDNA.objects.create(
                author=request.user,
                name=name,
                is_primary=is_primary,
                signature_moves=signature_moves,
                do_list=do_list,
                dont_list=dont_list,
                taboo_list=taboo_list,
                preferred_llm=preferred_llm,
                status=AuthorStyleDNA.Status.PRODUCTION_READY,
            )
            message = f'Style DNA "{name}" erfolgreich erstellt!'
    
    # Session löschen
    if 'style_builder' in request.session:
        del request.session['style_builder']
        request.session.modified = True
    
    return JsonResponse({
        'ok': True,
        'dna_id': str(dna.id),
        'message': message,
        'updated': bool(editing_dna_id),
    })


@login_required
@require_POST
def style_builder_reset(request):
    """Setzt den Style Builder zurück."""
    if 'style_builder' in request.session:
        del request.session['style_builder']
        request.session.modified = True
    
    return JsonResponse({'ok': True, 'message': 'Builder zurückgesetzt'})


# =============================================================================
# STYLE DNA VIEWS
# =============================================================================

@login_required
def style_dna_list(request):
    """Liste aller eigenen Style DNAs - Redirect zum Dashboard."""
    return redirect('writing_hub:style-lab-dashboard')


@login_required
def style_dna_detail(request, dna_id):
    """Detail-Ansicht einer Style DNA - Redirect zu Style Builder."""
    return redirect('writing_hub:style-builder-refine', dna_id=dna_id)


@login_required
def style_dna_edit(request, dna_id):
    """Style DNA bearbeiten und optimieren."""
    from apps.bfagent.models import Llms
    
    dna = get_object_or_404(AuthorStyleDNA, id=dna_id, author=request.user)
    
    if request.method == 'POST':
        # Grunddaten
        dna.name = request.POST.get('name', dna.name).strip()
        dna.is_primary = request.POST.get('is_primary') == 'on'
        
        # Preferred LLM
        llm_id = request.POST.get('preferred_llm')
        if llm_id:
            try:
                dna.preferred_llm = Llms.objects.get(id=llm_id)
            except Llms.DoesNotExist:
                dna.preferred_llm = None
        else:
            dna.preferred_llm = None
        
        # DO Liste (Textarea, eine Zeile pro Eintrag)
        do_text = request.POST.get('do_list', '')
        dna.do_list = [x.strip() for x in do_text.split('\n') if x.strip()]
        
        # DON'T Liste
        dont_text = request.POST.get('dont_list', '')
        dna.dont_list = [x.strip() for x in dont_text.split('\n') if x.strip()]
        
        # Signature Moves
        sig_text = request.POST.get('signature_moves', '')
        dna.signature_moves = [x.strip() for x in sig_text.split('\n') if x.strip()]
        
        # Taboo Liste
        taboo_text = request.POST.get('taboo_list', '')
        dna.taboo_list = [x.strip() for x in taboo_text.split('\n') if x.strip()]
        
        # Wenn primary, andere auf False setzen
        if dna.is_primary:
            AuthorStyleDNA.objects.filter(
                author=request.user, is_primary=True
            ).exclude(id=dna.id).update(is_primary=False)
        
        dna.save()
        messages.success(request, f'Style DNA "{dna.name}" aktualisiert.')
        return redirect('writing_hub:style-dna-detail', dna_id=dna.id)
    
    # Verfügbare LLMs für Dropdown
    available_llms = Llms.objects.filter(is_active=True).order_by('provider', 'name')
    
    context = {
        'dna': dna,
        'available_llms': available_llms,
        'do_list_text': '\n'.join(dna.do_list or []),
        'dont_list_text': '\n'.join(dna.dont_list or []),
        'signature_moves_text': '\n'.join(dna.signature_moves or []),
        'taboo_list_text': '\n'.join(dna.taboo_list or []),
    }
    return render(request, 'writing_hub/style_lab/dna_edit.html', context)


@login_required
def style_dna_delete(request, dna_id):
    """Style DNA löschen."""
    dna = get_object_or_404(AuthorStyleDNA, id=dna_id, author=request.user)
    
    if request.method == 'POST':
        name = dna.name
        dna.delete()
        messages.success(request, f'Style DNA "{name}" wurde gelöscht.')
        return redirect('writing_hub:style-dna-list')
    
    # GET request - redirect to edit page
    return redirect('writing_hub:style-dna-edit', dna_id=dna_id)


@login_required
def style_dna_duplicate(request, dna_id):
    """Style DNA duplizieren."""
    original = get_object_or_404(AuthorStyleDNA, id=dna_id, author=request.user)
    
    # Neuen Namen generieren
    new_name = f"{original.name} (Kopie)"
    
    # Kopie erstellen
    duplicate = AuthorStyleDNA.objects.create(
        author=request.user,
        name=new_name,
        signature_moves=original.signature_moves or [],
        do_list=original.do_list or [],
        dont_list=original.dont_list or [],
        taboo_list=original.taboo_list or [],
        rhythm_profile=original.rhythm_profile or {},
        dialogue_profile=original.dialogue_profile or {},
        imagery_profile=original.imagery_profile or {},
        lens_profile=original.lens_profile or {},
        preferred_llm=original.preferred_llm,
        is_primary=False,  # Kopie ist nie primär
        version=1,  # Neue Version startet bei 1
    )
    
    messages.success(request, f'Style DNA "{original.name}" wurde dupliziert als "{new_name}".')
    return redirect('writing_hub:style-builder-refine', dna_id=duplicate.id)


@login_required
def style_dna_test(request, dna_id):
    """
    AJAX Endpoint: Style DNA testen mit aktuellen Formular-Daten.
    Generiert einen Testtext basierend auf den übergebenen Stil-Parametern.
    """
    import json
    from django.http import JsonResponse
    from apps.writing_hub.services.style_lab_service import StyleLabService
    from apps.bfagent.models import Llms
    
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    # Extract form data
    do_list = data.get('do_list', [])
    dont_list = data.get('dont_list', [])
    signature_moves = data.get('signature_moves', [])
    taboo_list = data.get('taboo_list', [])
    scene_type = data.get('scene_type', 'dialogue')
    context = data.get('context', '')
    preferred_llm_id = data.get('preferred_llm_id')
    
    # Build style profile from form data
    style_profile = {
        'signature_moves': signature_moves,
        'do_list': do_list,
        'dont_list': dont_list,
        'taboo_list': taboo_list,
    }
    
    # Get preferred LLM if specified
    preferred_llm = None
    if preferred_llm_id and str(preferred_llm_id).strip():
        try:
            preferred_llm = Llms.objects.get(id=int(preferred_llm_id), is_active=True)
            import logging
            logging.getLogger(__name__).info(f"Style Test: Verwende ausgewähltes LLM: {preferred_llm.llm_name} ({preferred_llm.provider})")
        except (Llms.DoesNotExist, ValueError) as e:
            import logging
            logging.getLogger(__name__).warning(f"Style Test: LLM mit ID {preferred_llm_id} nicht gefunden: {e}")
    
    # Initialize service with preferred LLM
    service = StyleLabService(llm=preferred_llm)
    
    # Generate test scene
    result = service.generate_scene(
        scene_type=scene_type,
        style_profile=style_profile,
        do_patterns=do_list,
        dont_patterns=dont_list + taboo_list,
        original_text=context if context else None,
    )
    
    if result.success:
        return JsonResponse({
            'ok': True,
            'text': result.text,
            'llm_used': result.llm_used or 'Unbekannt',
        })
    else:
        return JsonResponse({
            'ok': False,
            'error': result.error_message or 'Generierung fehlgeschlagen',
        })


@login_required
def style_dna_generate_sample(request, dna_id):
    """Beispieltext basierend auf Style DNA und Original-Texten generieren."""
    dna = get_object_or_404(AuthorStyleDNA, id=dna_id, author=request.user)
    
    from apps.writing_hub.services.style_lab_service import StyleLabService
    
    # Verbundene Session finden für thematischen Kontext
    connected_session = StyleLabSession.objects.filter(
        author=request.user,
        target_dna=dna
    ).first()
    
    # Original-Texte und Themen aus Session extrahieren
    original_excerpts = []
    theme_hints = []
    
    if connected_session:
        for obs in connected_session.observations.all()[:3]:  # Max 3 Texte
            if obs.source_text:
                # Kurzen Ausschnitt für Kontext
                excerpt = obs.source_text[:500]
                original_excerpts.append(excerpt)
            if obs.observations:
                # Thematische Hinweise aus Analyse
                for key, value in obs.observations.items():
                    theme_hints.append(f"{key}: {value}")
    
    # Ollama-Modell aus Session oder Fallback
    ollama_model = 'dolphin-llama3:8b'
    if connected_session and connected_session.selected_ollama_model:
        ollama_model = connected_session.selected_ollama_model
    
    service = StyleLabService(ollama_model=ollama_model)
    
    # Stil-Profil aus DNA aufbauen
    style_profile = {
        'signature_moves': dna.signature_moves or [],
        'do_list': dna.do_list or [],
        'dont_list': dna.dont_list or [],
        'original_excerpts': original_excerpts,  # Thematischer Kontext
        'theme_hints': theme_hints[:10],  # Top 10 Themen
    }
    
    # Szene generieren mit thematischem Kontext
    result = service.generate_scene_from_dna(
        dna=dna,
        style_profile=style_profile,
        original_excerpts=original_excerpts,
    )
    
    return render(request, 'writing_hub/style_lab/dna_sample.html', {
        'dna': dna,
        'generated_text': result.text,
        'llm_used': result.llm_used,
        'success': result.success,
        'connected_session': connected_session,
    })


@login_required
def style_dna_create(request):
    """Neue Style DNA erstellen - Redirect zu Style Builder."""
    return redirect('writing_hub:style-builder')


@login_required
def _style_dna_create_legacy(request):
    """DEPRECATED: Alte manuelle Erstellung."""
    from .models import Author, WritingStyle
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        is_primary = request.POST.get('is_primary') == 'on'
        author_id = request.POST.get('author_id', '').strip()
        
        if not name:
            messages.error(request, 'Name ist erforderlich.')
            return redirect('writing_hub:style-lab-dashboard')
        
        # Wenn primary, andere auf False setzen
        if is_primary:
            AuthorStyleDNA.objects.filter(
                author=request.user, is_primary=True
            ).update(is_primary=False)
        
        dna = AuthorStyleDNA.objects.create(
            author=request.user,
            name=name,
            is_primary=is_primary,
            status=AuthorStyleDNA.Status.DRAFT
        )
        
        # If author_id provided, also create a WritingStyle linked to the Author
        if author_id:
            try:
                author = Author.objects.get(id=author_id, created_by=request.user)
                WritingStyle.objects.create(
                    author=author,
                    name=name,
                    description=request.POST.get('description', ''),
                    is_default=not author.writing_styles.exists()  # First style becomes default
                )
                messages.success(request, f'Style DNA "{name}" erstellt und Autor "{author.name}" zugeordnet.')
            except Author.DoesNotExist:
                messages.success(request, f'Style DNA "{name}" erstellt.')
        else:
            messages.success(request, f'Style DNA "{name}" erstellt.')
        
        return redirect('writing_hub:style-dna-detail', dna_id=dna.id)
    
    # Get user's authors for the dropdown
    authors = Author.objects.filter(created_by=request.user, is_active=True).order_by('name')
    
    return render(request, 'writing_hub/style_lab/dna_create.html', {
        'authors': authors
    })


# =============================================================================
# LAB SESSION VIEWS
# =============================================================================

@login_required
def session_list(request):
    """Liste aller Lab Sessions."""
    sessions = StyleLabSession.objects.filter(
        author=request.user
    ).order_by('-started_at')
    
    return render(request, 'writing_hub/style_lab/session_list.html', {
        'sessions': sessions
    })


@login_required
def session_create(request):
    """Neue Lab Session starten."""
    from apps.writing_hub.services.style_lab_service import StyleLabService
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        purpose = request.POST.get('purpose', 'new_style')
        target_dna_id = request.POST.get('target_dna')
        llm_id = request.POST.get('llm')
        genres = request.POST.getlist('genres')
        
        if not name:
            messages.error(request, 'Name ist erforderlich.')
            return redirect('writing_hub:session-create')
        
        target_dna = None
        if target_dna_id:
            target_dna = get_object_or_404(
                AuthorStyleDNA, id=target_dna_id, author=request.user
            )
        
        # LLM auswählen (optional) - unterstützt DB-LLMs und lokale Ollama-Modelle
        selected_llm = None
        selected_llm_name = None
        if llm_id:
            if str(llm_id).startswith('ollama:'):
                # Lokales Ollama-Modell
                selected_llm_name = llm_id.replace('ollama:', '')
            else:
                try:
                    from apps.bfagent.models import Llms
                    selected_llm = Llms.objects.get(id=llm_id, is_active=True)
                    selected_llm_name = selected_llm.llm_name
                except Exception:
                    pass
        
        session = StyleLabSession.objects.create(
            author=request.user,
            name=name,
            purpose=purpose,
            target_dna=target_dna,
            target_genres=genres,
            current_phase=StyleLabSession.Phase.INIT
        )
        
        # LLM-Info in Session-Name speichern falls Ollama gewählt
        if selected_llm_name and not selected_llm:
            # Lokales Ollama-Modell - speichere Info für späteren Zugriff
            session.name = f"{name} [{selected_llm_name}]"
            session.save()
        
        llm_info = f" mit {selected_llm_name}" if selected_llm_name else " (System-Default LLM)"
        messages.success(request, f'Session "{name}" gestartet{llm_info}.')
        return redirect('writing_hub:session-detail', session_id=session.id)
    
    # Für das Formular: eigene DNAs
    my_dnas = AuthorStyleDNA.objects.filter(author=request.user)
    
    genres = ['Roman', 'Thriller', 'SciFi', 'Fantasy', 'Krimi', 'Historisch', 'Sachbuch']
    
    # Verfügbare LLMs
    available_llms = StyleLabService.get_available_llms()
    ollama_available, ollama_status = StyleLabService.check_ollama_available()
    nsfw_llms = StyleLabService.get_recommended_nsfw_llms()
    
    return render(request, 'writing_hub/style_lab/session_create.html', {
        'my_dnas': my_dnas,
        'genres': genres,
        'purposes': StyleLabSession._meta.get_field('purpose').choices,
        'available_llms': available_llms,
        'ollama_available': ollama_available,
        'ollama_status': ollama_status,
        'nsfw_llms': nsfw_llms,
    })


@login_required
def session_detail(request, session_id):
    """Detail-Ansicht einer Session mit Phasen-Navigation."""
    session = get_object_or_404(
        StyleLabSession, id=session_id, author=request.user
    )
    
    # Phase-spezifische Daten laden
    observations = session.observations.order_by('analyzed_at')
    candidates = session.candidates.order_by('scene_type')
    
    # Feedback-Stats
    feedback_stats = {
        'total': 0,
        'accepted': 0,
        'rejected': 0,
        'partial': 0,
    }
    for candidate in candidates:
        for fb in candidate.feedbacks.all():
            feedback_stats['total'] += 1
            if fb.rating == 'accepted':
                feedback_stats['accepted'] += 1
            elif fb.rating == 'rejected':
                feedback_stats['rejected'] += 1
            else:
                feedback_stats['partial'] += 1
    
    # Phasen-Status
    phases = [
        ('init', 'Initialisierung', 'bi-play-circle'),
        ('extraction', 'Extraktion', 'bi-search'),
        ('synthesis', 'Synthese', 'bi-magic'),
        ('feedback', 'Feedback', 'bi-chat-quote'),
        ('fixation', 'Fixierung', 'bi-lock'),
        ('completed', 'Abgeschlossen', 'bi-check-circle'),
    ]
    
    current_idx = [p[0] for p in phases].index(session.current_phase)
    
    context = {
        'session': session,
        'observations': observations,
        'candidates': candidates,
        'feedback_stats': feedback_stats,
        'phases': phases,
        'current_phase_idx': current_idx,
    }
    
    return render(request, 'writing_hub/style_lab/session_detail.html', context)


@login_required
@require_POST
def session_advance_phase(request, session_id):
    """Session zur nächsten Phase führen."""
    session = get_object_or_404(
        StyleLabSession, id=session_id, author=request.user
    )
    
    phase_order = ['init', 'extraction', 'synthesis', 'feedback', 'fixation', 'completed']
    current_idx = phase_order.index(session.current_phase)
    
    if current_idx < len(phase_order) - 1:
        session.current_phase = phase_order[current_idx + 1]
        if session.current_phase == 'completed':
            session.completed_at = timezone.now()
        session.save()
        messages.success(request, f'Phase geändert zu: {session.get_current_phase_display()}')
    else:
        messages.warning(request, 'Session ist bereits abgeschlossen.')
    
    return redirect('writing_hub:session-detail', session_id=session.id)


@login_required
@require_POST
def session_previous_phase(request, session_id):
    """Session zur vorherigen Phase zurückführen (für Testing)."""
    session = get_object_or_404(
        StyleLabSession, id=session_id, author=request.user
    )
    
    phase_order = ['init', 'extraction', 'synthesis', 'feedback', 'fixation', 'completed']
    current_idx = phase_order.index(session.current_phase)
    
    if current_idx > 0:
        # Bei completed: completed_at zurücksetzen
        if session.current_phase == 'completed':
            session.completed_at = None
        session.current_phase = phase_order[current_idx - 1]
        session.save()
        messages.info(request, f'Phase zurückgesetzt zu: {session.get_current_phase_display()}')
    else:
        messages.warning(request, 'Bereits in der ersten Phase.')
    
    return redirect('writing_hub:session-detail', session_id=session.id)


# =============================================================================
# EXTRACTION PHASE
# =============================================================================

@login_required
def extraction_add_text(request, session_id):
    """Text zur Analyse hinzufügen."""
    session = get_object_or_404(
        StyleLabSession, id=session_id, author=request.user
    )
    
    if request.method == 'POST':
        source_text = request.POST.get('source_text', '').strip()
        source_type = request.POST.get('source_type', 'author_sample')
        source_name = request.POST.get('source_name', '').strip()
        
        if not source_text:
            messages.error(request, 'Text ist erforderlich.')
            return redirect('writing_hub:session-detail', session_id=session.id)
        
        if len(source_text) < 200:
            messages.warning(request, 'Text sollte mindestens 200 Zeichen haben.')
        
        observation = StyleObservation.objects.create(
            session=session,
            source_text=source_text,
            source_type=source_type,
            source_name=source_name or f'Text {session.observations.count() + 1}',
        )
        
        messages.success(request, 'Text hinzugefügt. Analyse wird durchgeführt...')
        
        # TODO: Hier später LLM-Analyse triggern
        # service.analyze_text(observation)
        
        return redirect('writing_hub:session-detail', session_id=session.id)
    
    return render(request, 'writing_hub/style_lab/extraction_add.html', {
        'session': session,
        'source_types': StyleObservation._meta.get_field('source_type').choices,
    })


@login_required
def extraction_analyze(request, session_id):
    """Alle Texte analysieren (HTMX)."""
    session = get_object_or_404(
        StyleLabSession, id=session_id, author=request.user
    )
    
    # StyleLabService mit Session-LLM initialisieren
    from apps.writing_hub.services.style_lab_service import StyleLabService
    service = StyleLabService(llm=session.llm, ollama_model=session.selected_ollama_model)
    
    # Texte ohne Analyse finden (observations ist leer oder None)
    unanalyzed = []
    for obs in session.observations.all():
        if not obs.observations or obs.observations == {}:
            unanalyzed.append(obs)
    
    if not unanalyzed:
        messages.info(request, 'Alle Texte wurden bereits analysiert.')
        return redirect('writing_hub:session-detail', session_id=session.id)
    
    analyzed_count = 0
    last_llm_used = None
    
    for obs in unanalyzed:
        result = service.analyze_style(obs.source_text)
        
        obs.observations = result.observations
        obs.metrics = result.metrics
        obs.llm_used = result.llm_used or 'unknown'
        obs.save()
        analyzed_count += 1
        last_llm_used = result.llm_used
    
    # LLM-Info: Ollama-Modell oder DB-LLM oder Fallback
    if last_llm_used:
        llm_info = f" mit {last_llm_used}"
    elif session.selected_ollama_model:
        llm_info = f" mit {session.selected_ollama_model}"
    elif session.llm:
        llm_info = f" mit {session.llm.llm_name}"
    else:
        llm_info = " (System-Default)"
    
    messages.success(request, f'{analyzed_count} Text(e) analysiert{llm_info}.')
    return redirect('writing_hub:session-detail', session_id=session.id)


# =============================================================================
# SYNTHESIS PHASE
# =============================================================================

@login_required
def synthesis_generate(request, session_id):
    """Test-Szenen generieren."""
    session = get_object_or_404(
        StyleLabSession, id=session_id, author=request.user
    )
    
    if request.method == 'POST':
        scene_types = request.POST.getlist('scene_types')
        
        if not scene_types:
            scene_types = ['arrival', 'dialogue', 'introspection']
        
        # StyleLabService mit Session-LLM initialisieren
        from apps.writing_hub.services.style_lab_service import StyleLabService
        service = StyleLabService(llm=session.llm, ollama_model=session.selected_ollama_model)
        
        # Original-Text aus Observations holen (wichtig für Stil-Imitation!)
        # Nimm den ersten author_sample Text als Referenz
        first_observation = session.observations.filter(source_type='author_sample').first()
        original_text = first_observation.source_text if first_observation else ''
        
        # Stil-Profil aus Observations aufbauen
        style_profile = {}
        do_patterns = []
        dont_patterns = []
        
        for obs in session.observations.all():
            if obs.observations:
                style_profile.update(obs.observations)
        
        # Patterns aus bisherigem Feedback sammeln
        for feedback in StyleFeedback.objects.filter(candidate__session=session):
            do_patterns.extend(feedback.accepted_patterns or [])
            dont_patterns.extend(feedback.rejected_patterns or [])
        
        generated_count = 0
        for scene_type in scene_types:
            # Generiere Szene mit Original-Text als Referenz
            result = service.generate_scene(
                scene_type=scene_type,
                style_profile=style_profile,
                do_patterns=list(set(do_patterns)),
                dont_patterns=list(set(dont_patterns)),
                original_text=original_text,
            )
            
            StyleCandidate.objects.create(
                session=session,
                scene_type=scene_type,
                scene_prompt=f'Schreibe eine {scene_type}-Szene im extrahierten Stil.',
                generated_text=result.text,
                used_features=result.used_features,
                llm_used=result.llm_used or 'unknown',
                tokens_used=result.tokens_used,
            )
            generated_count += 1
        
        llm_info = f" (LLM: {session.llm.llm_name})" if session.llm else " (System-Default)"
        messages.success(request, f'{generated_count} Szene(n) generiert{llm_info}.')
        return redirect('writing_hub:session-detail', session_id=session.id)
    
    scene_type_choices = StyleCandidate._meta.get_field('scene_type').choices
    existing = list(session.candidates.values_list('scene_type', flat=True))
    existing_candidates = session.candidates.all().order_by('scene_type', '-generated_at')
    
    return render(request, 'writing_hub/style_lab/synthesis_generate.html', {
        'session': session,
        'scene_types': scene_type_choices,
        'existing_types': existing,
        'existing_candidates': existing_candidates,
    })


@login_required
@require_POST
def synthesis_delete_candidate(request, candidate_id):
    """Szenen-Candidate löschen."""
    candidate = get_object_or_404(StyleCandidate, id=candidate_id)
    session = candidate.session
    
    if session.author != request.user:
        messages.error(request, 'Keine Berechtigung.')
        return redirect('writing_hub:style-lab-dashboard')
    
    scene_type = candidate.get_scene_type_display()
    candidate.delete()
    messages.success(request, f'Szene "{scene_type}" gelöscht.')
    
    return redirect('writing_hub:synthesis-generate', session_id=session.id)


# =============================================================================
# FEEDBACK PHASE
# =============================================================================

@login_required
def feedback_candidate(request, candidate_id):
    """Feedback zu einem Candidate geben."""
    candidate = get_object_or_404(StyleCandidate, id=candidate_id)
    session = candidate.session
    
    if session.author != request.user:
        messages.error(request, 'Keine Berechtigung.')
        return redirect('writing_hub:style-lab-dashboard')
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        accepted_patterns = request.POST.getlist('accepted_patterns')
        rejected_patterns = request.POST.getlist('rejected_patterns')
        general_comment = request.POST.get('general_comment', '').strip()
        
        # Author edits als JSON
        edits_json = request.POST.get('author_edits', '[]')
        try:
            author_edits = json.loads(edits_json)
        except json.JSONDecodeError:
            author_edits = []
        
        StyleFeedback.objects.create(
            candidate=candidate,
            rating=rating,
            accepted_patterns=accepted_patterns,
            rejected_patterns=rejected_patterns,
            author_edits=author_edits,
            general_comment=general_comment,
            given_by=request.user,
        )
        
        messages.success(request, 'Feedback gespeichert.')
        return redirect('writing_hub:session-detail', session_id=session.id)
    
    # Vorschläge für Patterns aus Observations
    suggested_patterns = []
    for obs in session.observations.all():
        if obs.observations:
            for key, value in obs.observations.items():
                suggested_patterns.append(f'{key}: {value}')
    
    return render(request, 'writing_hub/style_lab/feedback_form.html', {
        'candidate': candidate,
        'session': session,
        'ratings': StyleFeedback.Rating.choices,
        'suggested_patterns': suggested_patterns,
    })


# =============================================================================
# FIXATION PHASE
# =============================================================================

@login_required
def fixation_create_dna(request, session_id):
    """Style DNA aus Session erstellen."""
    session = get_object_or_404(
        StyleLabSession, id=session_id, author=request.user
    )
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        is_primary = request.POST.get('is_primary') == 'on'
        
        if not name:
            messages.error(request, 'Name ist erforderlich.')
            return redirect('writing_hub:session-detail', session_id=session.id)
        
        # Patterns aus Feedback sammeln
        all_accepted = []
        all_rejected = []
        
        for candidate in session.candidates.all():
            for fb in candidate.feedbacks.filter(rating__in=['accepted', 'partial']):
                all_accepted.extend(fb.accepted_patterns)
                all_rejected.extend(fb.rejected_patterns)
        
        # Deduplizieren
        do_list = list(set(all_accepted))
        dont_list = list(set(all_rejected))
        
        # Signature Moves aus stark akzeptierten Patterns
        signature_moves = do_list[:5] if len(do_list) >= 5 else do_list
        
        with transaction.atomic():
            if is_primary:
                AuthorStyleDNA.objects.filter(
                    author=request.user, is_primary=True
                ).update(is_primary=False)
            
            dna = AuthorStyleDNA.objects.create(
                author=request.user,
                name=name,
                is_primary=is_primary,
                signature_moves=signature_moves,
                do_list=do_list,
                dont_list=dont_list,
                status=AuthorStyleDNA.Status.PRODUCTION_READY,
            )
            
            # Session mit DNA verknüpfen
            session.target_dna = dna
            session.current_phase = StyleLabSession.Phase.COMPLETED
            session.completed_at = timezone.now()
            session.save()
        
        messages.success(request, f'Style DNA "{name}" erstellt und Session abgeschlossen.')
        return redirect('writing_hub:style-dna-detail', dna_id=dna.id)
    
    # Feedback-Zusammenfassung für Preview
    accepted_patterns = []
    rejected_patterns = []
    
    for candidate in session.candidates.all():
        for fb in candidate.feedbacks.all():
            accepted_patterns.extend(fb.accepted_patterns)
            rejected_patterns.extend(fb.rejected_patterns)
    
    return render(request, 'writing_hub/style_lab/fixation_create.html', {
        'session': session,
        'accepted_patterns': list(set(accepted_patterns)),
        'rejected_patterns': list(set(rejected_patterns)),
    })


# =============================================================================
# HTMX PARTIALS
# =============================================================================

@login_required
def htmx_observation_card(request, observation_id):
    """HTMX: Einzelne Observation-Karte."""
    observation = get_object_or_404(StyleObservation, id=observation_id)
    return render(request, 'writing_hub/style_lab/partials/observation_card.html', {
        'observation': observation
    })


@login_required
def htmx_candidate_card(request, candidate_id):
    """HTMX: Einzelne Candidate-Karte."""
    candidate = get_object_or_404(StyleCandidate, id=candidate_id)
    return render(request, 'writing_hub/style_lab/partials/candidate_card.html', {
        'candidate': candidate
    })


@login_required
def htmx_phase_progress(request, session_id):
    """HTMX: Phasen-Fortschritt aktualisieren."""
    session = get_object_or_404(StyleLabSession, id=session_id)
    
    phases = [
        ('init', 'Initialisierung'),
        ('extraction', 'Extraktion'),
        ('synthesis', 'Synthese'),
        ('feedback', 'Feedback'),
        ('fixation', 'Fixierung'),
        ('completed', 'Abgeschlossen'),
    ]
    
    current_idx = [p[0] for p in phases].index(session.current_phase)
    
    return render(request, 'writing_hub/style_lab/partials/phase_progress.html', {
        'session': session,
        'phases': phases,
        'current_phase_idx': current_idx,
    })


# =============================================================================
# SPRINT 1: SATZ-BASIERTES HTMX FEEDBACK
# =============================================================================

def split_into_sentences(text):
    """Text in Sätze aufteilen."""
    import re
    # Einfache Satz-Trennung (kann verbessert werden)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


@login_required
def synthesis_interactive(request, candidate_id):
    """Interaktive Synthese-Ansicht mit Satz-Level Feedback."""
    candidate = get_object_or_404(StyleCandidate, id=candidate_id)
    session = candidate.session
    
    if session.author != request.user:
        messages.error(request, 'Keine Berechtigung.')
        return redirect('writing_hub:style-lab-dashboard')
    
    # Text in Sätze aufteilen
    sentences = split_into_sentences(candidate.generated_text)
    
    # Bestehendes Feedback laden
    existing_feedback = {
        fb.sentence_index: fb 
        for fb in candidate.sentence_feedbacks.all()
    }
    
    # Sätze mit Feedback-Status
    sentences_with_feedback = []
    for idx, sentence in enumerate(sentences):
        fb = existing_feedback.get(idx)
        sentences_with_feedback.append({
            'index': idx,
            'text': sentence,
            'feedback': fb,
            'rating': fb.rating if fb else None,
        })
    
    # Statistiken
    stats = {
        'total': len(sentences),
        'accepted': sum(1 for s in sentences_with_feedback if s['rating'] == 'accepted'),
        'partial': sum(1 for s in sentences_with_feedback if s['rating'] == 'partial'),
        'rejected': sum(1 for s in sentences_with_feedback if s['rating'] == 'rejected'),
        'pending': sum(1 for s in sentences_with_feedback if s['rating'] is None),
    }
    
    context = {
        'candidate': candidate,
        'session': session,
        'sentences': sentences_with_feedback,
        'stats': stats,
    }
    
    return render(request, 'writing_hub/style_lab/synthesis_interactive.html', context)


@login_required
@require_POST
def htmx_sentence_feedback(request, candidate_id, sentence_index):
    """HTMX: Einzelnes Satz-Feedback speichern."""
    candidate = get_object_or_404(StyleCandidate, id=candidate_id)
    
    if candidate.session.author != request.user:
        return HttpResponse("Keine Berechtigung", status=403)
    
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')
    pattern_tag = request.POST.get('pattern_tag', '')
    
    # Satz-Text holen
    sentences = split_into_sentences(candidate.generated_text)
    if sentence_index >= len(sentences):
        return HttpResponse("Ungültiger Satz-Index", status=400)
    
    sentence_text = sentences[sentence_index]
    
    # Feedback erstellen oder aktualisieren
    feedback, created = SentenceFeedback.objects.update_or_create(
        candidate=candidate,
        sentence_index=sentence_index,
        defaults={
            'sentence_text': sentence_text,
            'rating': rating,
            'comment': comment,
            'pattern_tag': pattern_tag,
            'given_by': request.user,
        }
    )
    
    return render(request, 'writing_hub/style_lab/partials/sentence_row.html', {
        'sentence': {
            'index': sentence_index,
            'text': sentence_text,
            'feedback': feedback,
            'rating': rating,
        },
        'candidate': candidate,
    })


@login_required
def htmx_feedback_stats(request, candidate_id):
    """HTMX: Feedback-Statistiken aktualisieren."""
    candidate = get_object_or_404(StyleCandidate, id=candidate_id)
    
    sentences = split_into_sentences(candidate.generated_text)
    feedbacks = {fb.sentence_index: fb for fb in candidate.sentence_feedbacks.all()}
    
    stats = {
        'total': len(sentences),
        'accepted': sum(1 for i in range(len(sentences)) if feedbacks.get(i) and feedbacks[i].rating == 'accepted'),
        'partial': sum(1 for i in range(len(sentences)) if feedbacks.get(i) and feedbacks[i].rating == 'partial'),
        'rejected': sum(1 for i in range(len(sentences)) if feedbacks.get(i) and feedbacks[i].rating == 'rejected'),
        'pending': sum(1 for i in range(len(sentences)) if i not in feedbacks),
    }
    
    return render(request, 'writing_hub/style_lab/partials/feedback_stats.html', {
        'stats': stats,
        'candidate': candidate,
    })


# =============================================================================
# SPRINT 2: CONSOLIDATION PHASE
# =============================================================================

@login_required
def consolidation_view(request, session_id):
    """Phase C: Feedback-Konsolidierung (3-Spalten-Ansicht)."""
    session = get_object_or_404(StyleLabSession, id=session_id, author=request.user)
    
    # Alle Sentence-Feedbacks sammeln
    all_feedbacks = SentenceFeedback.objects.filter(
        candidate__session=session
    ).select_related('candidate')
    
    accepted = []
    rejected = []
    ambiguous = []
    
    for fb in all_feedbacks:
        item = {
            'text': fb.sentence_text,
            'pattern': fb.pattern_tag,
            'scene': fb.candidate.get_scene_type_display(),
            'comment': fb.comment,
            'id': fb.id,
        }
        if fb.rating == 'accepted':
            accepted.append(item)
        elif fb.rating == 'rejected':
            rejected.append(item)
        else:  # partial
            ambiguous.append(item)
    
    # Pattern-Extraktion (Gruppierung)
    accepted_patterns = {}
    rejected_patterns = {}
    
    for item in accepted:
        tag = item['pattern'] or 'Ungekennzeichnet'
        if tag not in accepted_patterns:
            accepted_patterns[tag] = []
        accepted_patterns[tag].append(item)
    
    for item in rejected:
        tag = item['pattern'] or 'Ungekennzeichnet'
        if tag not in rejected_patterns:
            rejected_patterns[tag] = []
        rejected_patterns[tag].append(item)
    
    context = {
        'session': session,
        'accepted': accepted,
        'rejected': rejected,
        'ambiguous': ambiguous,
        'accepted_patterns': accepted_patterns,
        'rejected_patterns': rejected_patterns,
        'stats': {
            'accepted': len(accepted),
            'rejected': len(rejected),
            'ambiguous': len(ambiguous),
        }
    }
    
    return render(request, 'writing_hub/style_lab/consolidation.html', context)


# =============================================================================
# SPRINT 3: LIVE PREVIEW (FIXATION)
# =============================================================================

@login_required
def fixation_view(request, session_id):
    """Phase D: Fixation mit Live Preview."""
    session = get_object_or_404(StyleLabSession, id=session_id, author=request.user)
    
    # Feedback-Konsolidierung
    all_feedbacks = SentenceFeedback.objects.filter(candidate__session=session)
    
    # DO-Liste: Akzeptierte Patterns
    do_patterns = list(
        all_feedbacks.filter(rating='accepted', pattern_tag__isnull=False)
        .exclude(pattern_tag='')
        .values_list('pattern_tag', flat=True)
        .distinct()
    )
    
    # DON'T-Liste: Abgelehnte Patterns
    dont_patterns = list(
        all_feedbacks.filter(rating='rejected', pattern_tag__isnull=False)
        .exclude(pattern_tag='')
        .values_list('pattern_tag', flat=True)
        .distinct()
    )
    
    # Beispiel-Sätze für Preview
    accepted_examples = list(
        all_feedbacks.filter(rating='accepted')
        .values_list('sentence_text', flat=True)[:3]
    )
    
    rejected_examples = list(
        all_feedbacks.filter(rating='rejected')
        .values_list('sentence_text', flat=True)[:3]
    )
    
    context = {
        'session': session,
        'do_patterns': do_patterns,
        'dont_patterns': dont_patterns,
        'accepted_examples': accepted_examples,
        'rejected_examples': rejected_examples,
    }
    
    return render(request, 'writing_hub/style_lab/fixation.html', context)


# =============================================================================
# AUTHOR API (for Style Lab)
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def author_api(request):
    """
    API endpoint for Author CRUD (list/create).
    GET: List all authors for current user
    POST: Create new author
    """
    from .models import Author
    
    if request.method == 'GET':
        authors = Author.objects.filter(
            created_by=request.user, is_active=True
        ).order_by('name')
        
        authors_data = [{
            'id': str(a.id),
            'name': a.name,
            'bio': a.bio,
            'genres': a.genres,
            'styles_count': a.writing_styles.count()
        } for a in authors]
        
        return JsonResponse({'success': True, 'authors': authors_data})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            bio = data.get('bio', '').strip()
            genres = data.get('genres', [])
            
            if not name:
                return JsonResponse({'success': False, 'error': 'Name ist erforderlich'}, status=400)
            
            author = Author.objects.create(
                name=name,
                bio=bio,
                genres=genres if isinstance(genres, list) else [],
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'author': {
                    'id': str(author.id),
                    'name': author.name,
                    'bio': author.bio,
                    'genres': author.genres
                }
            })
        except Exception as e:
            logger.error(f"Error creating author: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def author_api_detail(request, author_id):
    """
    API endpoint for Author detail/update/delete.
    GET: Get author details
    PUT: Update author
    DELETE: Soft delete author
    """
    from .models import Author, WritingStyle
    
    author = get_object_or_404(Author, id=author_id, created_by=request.user)
    
    if request.method == 'GET':
        # Get WritingStyle names assigned to this author
        assigned_style_names = list(author.writing_styles.filter(is_active=True).values_list('name', flat=True))
        
        # Find AuthorStyleDNA IDs that match these names (for checkbox selection)
        assigned_dna_ids = list(
            AuthorStyleDNA.objects.filter(
                author=request.user,
                name__in=assigned_style_names
            ).values_list('id', flat=True)
        )
        
        return JsonResponse({
            'success': True,
            'author': {
                'id': str(author.id),
                'name': author.name,
                'bio': author.bio,
                'genres': author.genres,
                'styles': [{'id': str(dna_id), 'name': name} for dna_id, name in zip(assigned_dna_ids, assigned_style_names)]
            }
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            
            if not name:
                return JsonResponse({'success': False, 'error': 'Name ist erforderlich'}, status=400)
            
            author.name = name
            author.bio = data.get('bio', '').strip()
            author.genres = data.get('genres', []) if isinstance(data.get('genres'), list) else []
            author.save()
            
            # Handle style assignments
            style_ids = data.get('style_ids', [])
            if isinstance(style_ids, list):
                # Get current assigned styles
                current_style_names = set(author.writing_styles.values_list('name', flat=True))
                
                # Get selected AuthorStyleDNA names
                selected_dnas = AuthorStyleDNA.objects.filter(
                    id__in=style_ids,
                    author=request.user
                )
                selected_names = set(selected_dnas.values_list('name', flat=True))
                
                # Remove styles that are no longer selected
                for style_name in current_style_names - selected_names:
                    WritingStyle.objects.filter(author=author, name=style_name).delete()
                
                # Add newly selected styles
                for dna in selected_dnas:
                    if dna.name not in current_style_names:
                        description = ', '.join(dna.do_list[:3]) if dna.do_list else ''
                        WritingStyle.objects.create(
                            author=author,
                            name=dna.name,
                            description=description,
                            is_default=not author.writing_styles.exists()
                        )
            
            return JsonResponse({
                'success': True,
                'author': {
                    'id': str(author.id),
                    'name': author.name,
                    'bio': author.bio,
                    'genres': author.genres
                }
            })
        except Exception as e:
            logger.error(f"Error updating author: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        try:
            author.is_active = False
            author.save()
            return JsonResponse({'success': True, 'message': 'Autor gelöscht'})
        except Exception as e:
            logger.error(f"Error deleting author: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def style_dna_assign_author(request, dna_id):
    """
    API endpoint to assign/remove an author to/from a Style DNA.
    POST: Assign author (creates WritingStyle linked to author)
    DELETE: Remove author assignment
    """
    from .models import Author, WritingStyle
    
    dna = get_object_or_404(AuthorStyleDNA, id=dna_id, author=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            author_id = data.get('author_id')
            
            if not author_id:
                return JsonResponse({'success': False, 'error': 'author_id erforderlich'}, status=400)
            
            author = get_object_or_404(Author, id=author_id, created_by=request.user)
            
            # Check if already assigned
            existing = WritingStyle.objects.filter(name=dna.name, author=author).first()
            if existing:
                return JsonResponse({'success': False, 'error': 'Stil bereits diesem Autor zugeordnet'}, status=400)
            
            # Create WritingStyle linked to author
            # Build description from DNA's do_list if available
            description = ''
            if dna.do_list:
                description = ', '.join(dna.do_list[:3])  # First 3 items
            
            WritingStyle.objects.create(
                author=author,
                name=dna.name,
                description=description,
                is_default=not author.writing_styles.exists()
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Stil "{dna.name}" wurde {author.name} zugeordnet'
            })
        except Exception as e:
            logger.error(f"Error assigning author to DNA: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        try:
            # Find and delete the WritingStyle with matching name
            deleted, _ = WritingStyle.objects.filter(
                name=dna.name,
                author__created_by=request.user
            ).delete()
            
            if deleted:
                return JsonResponse({'success': True, 'message': 'Autor-Zuordnung entfernt'})
            else:
                return JsonResponse({'success': False, 'error': 'Keine Zuordnung gefunden'}, status=404)
        except Exception as e:
            logger.error(f"Error removing author assignment: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
