"""
Lektorats-Framework Views
=========================

Views für das systematische Qualitätssicherungs-System.
"""
import sys
print("\n" + "!"*60, file=sys.stderr, flush=True)
print("! LEKTORAT VIEWS LOADED !", file=sys.stderr, flush=True)
print("!"*60 + "\n", file=sys.stderr, flush=True)

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.db.models import Count, Q

from apps.bfagent.models import BookProjects, BookChapters
from .models_lektorat import (
    LektoratsSession,
    LektoratsFehler,
    FigurenRegister,
    ZeitlinienEintrag,
    StilProfil,
    WiederholungsAnalyse,
)


# =============================================================================
# Lektorats-Dashboard
# =============================================================================

@login_required
def lektorat_dashboard(request, project_id):
    """
    Hauptdashboard für das Lektorats-System.
    Zeigt Übersicht über alle Module und deren Status.
    """
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Aktive oder letzte Session holen
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    # Kapitel für Kontext
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    # Modul-Status berechnen
    module = [
        {
            'id': 'figuren',
            'name': 'Figurenkonsistenz',
            'icon': '👤',
            'description': 'Prüft Charaktere auf Konsistenz (Namen, Attribute, Beziehungen)',
            'status': 'pending',
            'fehler_count': 0,
            'color': 'primary',
        },
        {
            'id': 'zeitlinien',
            'name': 'Zeitlinien-Analyse',
            'icon': '📅',
            'description': 'Validiert chronologische Konsistenz und Zeitmarker',
            'status': 'pending',
            'fehler_count': 0,
            'color': 'info',
        },
        {
            'id': 'logik',
            'name': 'Handlungslogik',
            'icon': '🧠',
            'description': 'Findet Plotlöcher und logische Widersprüche',
            'status': 'pending',
            'fehler_count': 0,
            'color': 'warning',
        },
        {
            'id': 'stil',
            'name': 'Stilkonsistenz',
            'icon': '✍️',
            'description': 'Prüft Perspektive, Tempus und Tonalität',
            'status': 'pending',
            'fehler_count': 0,
            'color': 'secondary',
        },
        {
            'id': 'wiederholungen',
            'name': 'Wiederholungen',
            'icon': '🔄',
            'description': 'Findet Wort-, Phrasen- und Backstory-Wiederholungen',
            'status': 'pending',
            'fehler_count': 0,
            'color': 'danger',
        },
    ]
    
    # Stats aus Session holen wenn vorhanden
    if session:
        for modul in module:
            modul['status'] = session.modul_status.get(modul['id'], 'pending')
            modul['fehler_count'] = session.fehler.filter(modul=modul['id']).count()
            modul['fehler_offen'] = session.fehler.filter(modul=modul['id'], status='offen').count()
            modul['fehler_korrigiert'] = session.fehler.filter(modul=modul['id'], status='korrigiert').count()
            modul['fehler_ignoriert'] = session.fehler.filter(modul=modul['id'], status='ignoriert').count()
            modul['fehler_behoben'] = modul['fehler_korrigiert'] + modul['fehler_ignoriert']
            modul['progress'] = int(modul['fehler_behoben'] / modul['fehler_count'] * 100) if modul['fehler_count'] > 0 else 0
    
    # Gesamtstatistik
    stats = {
        'total_fehler': session.total_fehler if session else 0,
        'kritisch': session.fehler_kritisch if session else 0,
        'schwer': session.fehler_schwer if session else 0,
        'mittel': session.fehler_mittel if session else 0,
        'leicht': session.fehler_leicht if session else 0,
        'marginal': session.fehler_marginal if session else 0,
        'offen': session.fehler.filter(status='offen').count() if session else 0,
        'korrigiert': session.fehler.filter(status='korrigiert').count() if session else 0,
    }
    
    context = {
        'project': project,
        'session': session,
        'chapters': chapters,
        'module': module,
        'stats': stats,
    }
    
    return render(request, 'writing_hub/lektorat/dashboard.html', context)


@login_required
@require_POST
def lektorat_create_session(request, project_id):
    """Erstellt eine neue Lektorats-Session."""
    project = get_object_or_404(BookProjects, id=project_id)
    
    version_name = request.POST.get('version_name', 'Neue Prüfung')
    
    session = LektoratsSession.objects.create(
        project=project,
        created_by=request.user,
        version_name=version_name,
        status=LektoratsSession.Status.IN_BEARBEITUNG,
        modul_status={
            'figuren': 'pending',
            'zeitlinien': 'pending',
            'logik': 'pending',
            'stil': 'pending',
            'wiederholungen': 'pending',
        }
    )
    
    # Stil-Profil erstellen
    StilProfil.objects.create(session=session)
    
    return redirect('writing_hub:lektorat_dashboard', project_id=project_id)


# =============================================================================
# Modul 1: Figurenkonsistenz
# =============================================================================

@login_required
def lektorat_figuren(request, project_id):
    """Figuren-Modul: Zeigt und verwaltet Figuren-Register."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return redirect('writing_hub:lektorat_dashboard', project_id=project_id)
    
    figuren = session.figuren.all().order_by('rolle', 'name')
    fehler = session.fehler.filter(modul='figuren').order_by('severity', '-created_at')
    
    context = {
        'project': project,
        'session': session,
        'figuren': figuren,
        'fehler': fehler,
        'modul': 'figuren',
    }
    
    return render(request, 'writing_hub/lektorat/figuren.html', context)


@login_required
@require_POST
def lektorat_figuren_analyze(request, project_id):
    """Startet AI-Analyse für Figurenkonsistenz."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    # Import des Services (wird in Phase 3 implementiert)
    try:
        from .services.lektorat_service import LektoratService
        service = LektoratService(session)
        result = service.analyze_figuren()
        
        # Status aktualisieren
        session.modul_status['figuren'] = 'completed'
        session.save()
        session.update_statistics()
        
        return JsonResponse({
            'success': True,
            'figuren_count': result.get('figuren_count', 0),
            'fehler_count': result.get('fehler_count', 0),
            'redirect': f'/writing-hub/project/{project_id}/lektorat/ergebnisse/figuren/',
        })
    except ImportError:
        # Service noch nicht implementiert - Demo-Modus
        return JsonResponse({
            'success': True,
            'message': 'Demo-Modus: Service wird in Phase 3 implementiert',
            'figuren_count': 0,
            'fehler_count': 0,
            'redirect': f'/writing-hub/project/{project_id}/lektorat/ergebnisse/figuren/',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def lektorat_figur_save(request, project_id):
    """Speichert eine Figur im Register."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    try:
        data = json.loads(request.body)
        figur_id = data.get('id')
        
        if figur_id:
            figur = get_object_or_404(FigurenRegister, id=figur_id, session=session)
        else:
            figur = FigurenRegister(session=session)
        
        # Felder aktualisieren
        figur.name = data.get('name', figur.name)
        figur.name_varianten = data.get('name_varianten', figur.name_varianten)
        figur.rolle = data.get('rolle', figur.rolle)
        figur.alter = data.get('alter', figur.alter)
        figur.geschlecht = data.get('geschlecht', figur.geschlecht)
        figur.haarfarbe = data.get('haarfarbe', figur.haarfarbe)
        figur.augenfarbe = data.get('augenfarbe', figur.augenfarbe)
        figur.groesse = data.get('groesse', figur.groesse)
        figur.besondere_merkmale = data.get('besondere_merkmale', figur.besondere_merkmale)
        figur.herkunft = data.get('herkunft', figur.herkunft)
        figur.beruf = data.get('beruf', figur.beruf)
        figur.familie = data.get('familie', figur.familie)
        figur.charakterzuege = data.get('charakterzuege', figur.charakterzuege)
        figur.sprechweise = data.get('sprechweise', figur.sprechweise)
        figur.motivation = data.get('motivation', figur.motivation)
        figur.beziehungen = data.get('beziehungen', figur.beziehungen)
        
        figur.save()
        
        return JsonResponse({
            'success': True,
            'figur_id': figur.id,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def lektorat_figur_delete(request, project_id, figur_id):
    """Löscht eine Figur aus dem Register."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    figur = get_object_or_404(FigurenRegister, id=figur_id, session=session)
    figur.delete()
    
    return JsonResponse({'success': True})


# =============================================================================
# Fehler-Management
# =============================================================================

@login_required
def lektorat_fehler_list(request, project_id):
    """Zeigt alle Fehler für ein Projekt."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return redirect('writing_hub:lektorat_dashboard', project_id=project_id)
    
    # Filter
    modul_filter = request.GET.get('modul', '')
    severity_filter = request.GET.get('severity', '')
    status_filter = request.GET.get('status', '')
    
    fehler = session.fehler.all()
    
    if modul_filter:
        fehler = fehler.filter(modul=modul_filter)
    if severity_filter:
        fehler = fehler.filter(severity=severity_filter)
    if status_filter:
        fehler = fehler.filter(status=status_filter)
    
    fehler = fehler.order_by('severity', '-created_at')
    
    context = {
        'project': project,
        'session': session,
        'fehler': fehler,
        'modul_filter': modul_filter,
        'severity_filter': severity_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'writing_hub/lektorat/fehler_list.html', context)


@login_required
@require_POST
def lektorat_fehler_update(request, project_id, fehler_id):
    """Aktualisiert einen Fehler (Status, Korrektur)."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    fehler = get_object_or_404(LektoratsFehler, id=fehler_id, session=session)
    
    try:
        data = json.loads(request.body)
        
        if 'status' in data:
            fehler.status = data['status']
            if data['status'] == 'korrigiert':
                fehler.korrigiert_at = timezone.now()
        
        if 'korrektur_notiz' in data:
            fehler.korrektur_notiz = data['korrektur_notiz']
        
        fehler.save()
        session.update_statistics()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def lektorat_fehler_ai_correct(request, project_id, fehler_id):
    """Korrigiert einen Fehler automatisch mit KI."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    fehler = get_object_or_404(LektoratsFehler, id=fehler_id, session=session)
    
    if not fehler.chapter:
        return JsonResponse({'success': False, 'error': 'Kein Kapitel zugeordnet'})
    
    try:
        from .services.lektorat_service import LektoratService
        service = LektoratService(session)
        result = service.ai_correct_error(fehler)
        
        if result.get('success'):
            # Mark error as corrected
            fehler.status = 'korrigiert'
            fehler.korrigiert_at = timezone.now()
            fehler.korrektur_notiz = f"Automatisch korrigiert durch KI: {result.get('summary', '')}"
            fehler.save()
            session.update_statistics()
            
            return JsonResponse({
                'success': True,
                'diff_html': result.get('diff_html', ''),
                'summary': result.get('summary', ''),
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Korrektur fehlgeschlagen')
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def lektorat_fehler_create(request, project_id):
    """Erstellt einen neuen Fehler manuell."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    try:
        data = json.loads(request.body)
        
        fehler = LektoratsFehler.objects.create(
            session=session,
            chapter_id=data.get('chapter_id'),
            modul=data.get('modul', 'figuren'),
            severity=data.get('severity', 'C'),
            fehler_typ=data.get('fehler_typ', ''),
            beschreibung=data.get('beschreibung', ''),
            originaltext=data.get('originaltext', ''),
            korrekturvorschlag=data.get('korrekturvorschlag', ''),
            erklaerung=data.get('erklaerung', ''),
            ai_erkannt=False,
        )
        
        session.update_statistics()
        
        return JsonResponse({
            'success': True,
            'fehler_id': fehler.id,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# API Endpoints für HTMX
# =============================================================================

@login_required
@require_GET
def lektorat_stats_partial(request, project_id):
    """HTMX-Partial für Statistiken."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    stats = {
        'total_fehler': session.total_fehler if session else 0,
        'kritisch': session.fehler_kritisch if session else 0,
        'schwer': session.fehler_schwer if session else 0,
        'mittel': session.fehler_mittel if session else 0,
        'leicht': session.fehler_leicht if session else 0,
        'marginal': session.fehler_marginal if session else 0,
        'offen': session.fehler.filter(status='offen').count() if session else 0,
        'korrigiert': session.fehler.filter(status='korrigiert').count() if session else 0,
    }
    
    return render(request, 'writing_hub/lektorat/partials/_stats.html', {
        'stats': stats,
        'session': session,
    })


@login_required
@require_GET
def lektorat_modul_status_partial(request, project_id, modul_id):
    """HTMX-Partial für Modul-Status."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    status = session.modul_status.get(modul_id, 'pending') if session else 'pending'
    fehler_count = session.fehler.filter(modul=modul_id).count() if session else 0
    
    return render(request, 'writing_hub/lektorat/partials/_modul_status.html', {
        'modul_id': modul_id,
        'status': status,
        'fehler_count': fehler_count,
    })


# =============================================================================
# Modul 2: Stilkonsistenz
# =============================================================================

@login_required
@require_POST
def lektorat_stil_analyze(request, project_id):
    """Startet Stilkonsistenz-Analyse."""
    import logging
    logger = logging.getLogger(__name__)
    
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    try:
        from .services.lektorat_service import LektoratService
        service = LektoratService(session)
        result = service.analyze_stil()
        
        return JsonResponse({
            'success': True,
            'fehler_count': result.get('fehler_count', 0),
            'redirect': f'/writing-hub/project/{project_id}/lektorat/ergebnisse/stil/',
        })
    except Exception as e:
        logger.exception(f"Stil-Analyse Fehler: {e}")
        return JsonResponse({'success': False, 'error': str(e), 'redirect': f'/writing-hub/project/{project_id}/lektorat/ergebnisse/stil/'})


# =============================================================================
# Modul 3: Handlungslogik
# =============================================================================

@login_required
@require_POST
def lektorat_logik_analyze(request, project_id):
    """Startet Handlungslogik-Analyse."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    try:
        from .services.lektorat_service import LektoratService
        service = LektoratService(session)
        result = service.analyze_logik()
        
        return JsonResponse({
            'success': True,
            'fehler_count': result.get('fehler_count', 0),
            'redirect': f'/writing-hub/project/{project_id}/lektorat/ergebnisse/logik/',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# Modul 4: Wiederholungen
# =============================================================================

@login_required
@require_POST
def lektorat_wiederholungen_analyze(request, project_id):
    """Startet Wiederholungs-Analyse."""
    import logging
    logger = logging.getLogger(__name__)
    
    print(f"\n{'='*60}", file=sys.stderr, flush=True)
    print(f"[VIEW] lektorat_wiederholungen_analyze called for project {project_id}", file=sys.stderr, flush=True)
    print(f"{'='*60}\n", file=sys.stderr, flush=True)
    
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
        return redirect('writing_hub:lektorat_dashboard', project_id=project_id)
    
    try:
        from .services.lektorat_service import LektoratService
        print(f"[VIEW] Creating LektoratService for session {session.id}")
        service = LektoratService(session)
        print(f"[VIEW] Calling analyze_wiederholungen...")
        result = service.analyze_wiederholungen()
        print(f"[VIEW] Analysis complete: {result}")
        
        # Form POST: Redirect direkt
        if not request.headers.get('HX-Request'):
            return redirect('writing_hub:lektorat_ergebnisse', project_id=project_id, modul_id='wiederholungen')
        
        # HTMX: JSON Response
        return JsonResponse({
            'success': True,
            'fehler_count': result.get('fehler_count', 0),
            'redirect': f'/writing-hub/project/{project_id}/lektorat/ergebnisse/wiederholungen/',
        })
    except Exception as e:
        import traceback
        print(f"[VIEW ERROR] Exception: {e}")
        print(traceback.format_exc())
        logger.exception(f"Wiederholungen-Analyse Fehler: {e}")
        if not request.headers.get('HX-Request'):
            return redirect('writing_hub:lektorat_ergebnisse', project_id=project_id, modul_id='wiederholungen')
        return JsonResponse({'success': False, 'error': str(e), 'redirect': f'/writing-hub/project/{project_id}/lektorat/ergebnisse/wiederholungen/'})


# =============================================================================
# Modul 5: Zeitlinien
# =============================================================================

@login_required
@require_POST
def lektorat_zeitlinien_analyze(request, project_id):
    """Startet Zeitlinien-Analyse."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    try:
        from .services.lektorat_service import LektoratService
        service = LektoratService(session)
        result = service.analyze_zeitlinien()
        
        return JsonResponse({
            'success': True,
            'fehler_count': result.get('fehler_count', 0),
            'entries_count': result.get('entries_count', 0),
            'redirect': f'/writing-hub/project/{project_id}/lektorat/ergebnisse/zeitlinien/',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# Ergebnis-Ansichten
# =============================================================================

@login_required
def lektorat_ergebnisse(request, project_id, modul_id):
    """Zeigt Ergebnisse eines Analyse-Moduls."""
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return redirect('writing_hub:lektorat_dashboard', project_id=project_id)
    
    # Modul-spezifische Daten laden
    modul_config = {
        'figuren': {
            'name': 'Figurenkonsistenz',
            'icon': '👤',
            'description': 'Prüft Charaktere auf Konsistenz',
        },
        'stil': {
            'name': 'Stilkonsistenz', 
            'icon': '✍️',
            'description': 'Prüft Perspektive, Tempus und Tonalität',
        },
        'logik': {
            'name': 'Handlungslogik',
            'icon': '🧠', 
            'description': 'Findet Plotlöcher und logische Widersprüche',
        },
        'wiederholungen': {
            'name': 'Wiederholungen',
            'icon': '🔄',
            'description': 'Findet Wort- und Phrasenwiederholungen',
        },
        'zeitlinien': {
            'name': 'Zeitlinien-Analyse',
            'icon': '📅',
            'description': 'Validiert chronologische Konsistenz',
        },
    }
    
    config = modul_config.get(modul_id, {'name': modul_id, 'icon': '📋', 'description': ''})
    
    # Fehler für dieses Modul
    fehler = session.fehler.filter(modul=modul_id).order_by('severity', '-created_at')
    
    # Modul-spezifische Zusatzdaten
    extra_data = {}
    if modul_id == 'figuren':
        extra_data['figuren'] = session.figuren.all().order_by('rolle', 'name')
    elif modul_id == 'stil':
        extra_data['stil_profil'] = getattr(session, 'stil_profil', None)
    elif modul_id == 'wiederholungen':
        extra_data['analysen'] = session.wiederholungen.all().order_by('-anzahl')[:20]
    elif modul_id == 'zeitlinien':
        extra_data['eintraege'] = session.zeitlinien.all().order_by('chapter__chapter_number', 'reihenfolge')
    
    context = {
        'project': project,
        'session': session,
        'modul_id': modul_id,
        'modul': config,
        'fehler': fehler,
        'fehler_count': fehler.count(),
        **extra_data,
    }
    
    return render(request, 'writing_hub/lektorat/ergebnisse.html', context)


# =============================================================================
# Korrektur-System Views
# =============================================================================

@login_required
def correction_dashboard(request, project_id):
    """
    Korrektur-Dashboard für ein Projekt.
    Zeigt alle Fehler mit Korrektur-Vorschlägen.
    """
    from .models_lektorat import CorrectionSuggestion, GenreStyleProfile
    
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return redirect('writing_hub:lektorat_dashboard', project_id=project_id)
    
    # Fehler mit correction_status
    fehler_new = session.fehler.filter(
        modul='wiederholungen',
        correction_status='new'
    ).select_related('chapter')
    
    fehler_reviewing = session.fehler.filter(
        modul='wiederholungen',
        correction_status='reviewing'
    ).select_related('chapter')
    
    fehler_corrected = session.fehler.filter(
        modul='wiederholungen',
        correction_status='corrected'
    ).select_related('chapter')
    
    # Vorschläge
    pending_suggestions = CorrectionSuggestion.objects.filter(
        fehler__session=session,
        status='pending'
    ).select_related('fehler', 'fehler__chapter').order_by('-confidence')
    
    # Genre-Profil
    genre = (project.genre or 'default').lower()
    genre_profile = GenreStyleProfile.objects.filter(genre__icontains=genre.split()[0]).first()
    if not genre_profile:
        genre_profile = GenreStyleProfile.objects.filter(genre='default').first()
    
    # Statistiken
    stats = {
        'total': session.fehler.filter(modul='wiederholungen').count(),
        'new': fehler_new.count(),
        'reviewing': fehler_reviewing.count(),
        'corrected': fehler_corrected.count(),
        'ignored': session.fehler.filter(modul='wiederholungen', correction_status='ignored').count(),
        'accepted': session.fehler.filter(modul='wiederholungen', correction_status='accepted').count(),
        'pending_suggestions': pending_suggestions.count(),
    }
    
    context = {
        'project': project,
        'session': session,
        'fehler_new': fehler_new[:20],
        'fehler_reviewing': fehler_reviewing[:10],
        'pending_suggestions': pending_suggestions[:20],
        'genre_profile': genre_profile,
        'stats': stats,
    }
    
    return render(request, 'writing_hub/lektorat/correction_dashboard.html', context)


@login_required
@require_POST
def correction_generate(request, project_id):
    """Generiert Korrekturvorschläge für alle neuen Fehler."""
    from .services.correction_service import CorrectionService
    
    project = get_object_or_404(BookProjects, id=project_id)
    session = LektoratsSession.objects.filter(project=project).order_by('-created_at').first()
    
    if not session:
        return JsonResponse({'success': False, 'error': 'Keine Session gefunden'})
    
    try:
        use_llm = request.POST.get('use_llm', 'true').lower() == 'true'
        auto_threshold = float(request.POST.get('auto_threshold', '0.9'))
        
        service = CorrectionService(project)
        
        # Nur Wiederholungs-Fehler mit Status 'new'
        fehler_qs = session.fehler.filter(
            modul='wiederholungen',
            correction_status='new'
        )
        
        stats = service.process_all_fehler(
            fehler_qs=fehler_qs,
            auto_apply_threshold=auto_threshold,
            use_llm=use_llm
        )
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'message': f"Verarbeitet: {stats['processed']}, Auto-angewendet: {stats['auto_applied']}, Manuell: {stats['manual']}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def correction_detail(request, project_id, fehler_id):
    """Detail-Ansicht für einen Fehler mit Korrektur-Vorschlägen."""
    from .models_lektorat import CorrectionSuggestion
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    fehler = get_object_or_404(LektoratsFehler, id=fehler_id, session__project=project)
    
    suggestions = fehler.corrections.all().order_by('-confidence')
    
    # Kontext aus Kapitel
    context_text = ""
    if fehler.chapter and fehler.chapter.content:
        content = fehler.chapter.content
        if fehler.position_start and fehler.position_end:
            start = max(0, fehler.position_start - 300)
            end = min(len(content), fehler.position_end + 300)
            context_text = content[start:end]
    
    # Alle Vorkommen finden (Variante 2: Detail-View mit Vorkommen)
    occurrences = []
    search_term = fehler.originaltext.strip() if fehler.originaltext else None
    
    # Fallback: Suchbegriff aus Beschreibung extrahieren für Wiederholungen
    # Pattern: "'WORD' erscheint Nx in kurzem Abstand"
    if not search_term and fehler.beschreibung:
        match = re.search(r"'([^']+)'", fehler.beschreibung)
        if match:
            search_term = match.group(1)
    
    if search_term and len(search_term) >= 2:
        # Suche in allen Kapiteln des Projekts
        chapters = project.chapters.all().order_by('chapter_number')
        for chapter in chapters:
            if not chapter.content:
                continue
            
            # Finde alle Vorkommen
            content = chapter.content
            pattern = re.escape(search_term)
            for match in re.finditer(pattern, content, re.IGNORECASE):
                start_pos = match.start()
                end_pos = match.end()
                
                # Kontext extrahieren (50 Zeichen vor/nach)
                ctx_start = max(0, start_pos - 50)
                ctx_end = min(len(content), end_pos + 50)
                
                # Zeilennummer berechnen
                line_num = content[:start_pos].count('\n') + 1
                
                occurrences.append({
                    'chapter_id': chapter.id,
                    'chapter_number': chapter.chapter_number,
                    'chapter_title': chapter.title,
                    'line': line_num,
                    'position_start': start_pos,
                    'position_end': end_pos,
                    'text': match.group(),
                    'context_before': content[ctx_start:start_pos].replace('\n', ' '),
                    'context_after': content[end_pos:ctx_end].replace('\n', ' '),
                })
    
    context = {
        'project': project,
        'fehler': fehler,
        'suggestions': suggestions,
        'context_text': context_text,
        'occurrences': occurrences,
    }
    
    return render(request, 'writing_hub/lektorat/correction_detail.html', context)


@login_required
@require_POST
def correction_apply(request, project_id, suggestion_id):
    """Wendet eine Korrektur an."""
    from .models_lektorat import CorrectionSuggestion
    from .services.correction_service import CorrectionService
    
    project = get_object_or_404(BookProjects, id=project_id)
    suggestion = get_object_or_404(
        CorrectionSuggestion, 
        id=suggestion_id,
        fehler__session__project=project
    )
    
    action = request.POST.get('action', 'accept')
    final_text = request.POST.get('final_text', '')
    user_note = request.POST.get('user_note', '')
    mark_intentional = request.POST.get('mark_intentional', 'false').lower() == 'true'
    
    service = CorrectionService(project)
    
    if action == 'accept':
        success = service.apply_correction(suggestion, user_note=user_note)
    elif action == 'modify':
        success = service.apply_correction(suggestion, final_text=final_text, user_note=user_note)
    elif action == 'reject':
        success = service.reject_correction(suggestion, user_note=user_note, mark_as_intentional=mark_intentional)
    else:
        success = False
    
    if request.headers.get('HX-Request'):
        return JsonResponse({'success': success})
    
    return redirect('writing_hub:correction_dashboard', project_id=project_id)


@login_required
@require_POST  
def correction_regenerate(request, project_id, fehler_id):
    """Löscht alte Korrekturen und generiert neue."""
    from .services.correction_service import CorrectionService
    from .models_lektorat import CorrectionSuggestion
    
    project = get_object_or_404(BookProjects, id=project_id)
    fehler = get_object_or_404(LektoratsFehler, id=fehler_id, session__project=project)
    
    try:
        # Alte Korrekturen löschen
        deleted_count = fehler.corrections.all().delete()[0]
        
        # Fehler-Status zurücksetzen
        fehler.correction_status = 'new'
        fehler.save()
        
        # Neue Korrektur generieren
        use_llm = request.POST.get('use_llm', 'false').lower() == 'true'
        service = CorrectionService(project)
        suggestion = service.process_fehler(fehler, use_llm=use_llm)
        
        if request.headers.get('HX-Request') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if suggestion:
                return JsonResponse({
                    'success': True,
                    'deleted': deleted_count,
                    'suggestion': {
                        'id': suggestion.id,
                        'strategy': suggestion.strategy,
                        'original': suggestion.original_text,
                        'suggested': suggestion.suggested_text,
                        'alternatives': suggestion.alternatives,
                        'confidence': suggestion.confidence,
                    }
                })
            return JsonResponse({'success': True, 'deleted': deleted_count, 'message': 'Keine Korrektur möglich'})
        
        return redirect('writing_hub:correction_detail', project_id=project_id, fehler_id=fehler_id)
        
    except Exception as e:
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': False, 'error': str(e)})
        return redirect('writing_hub:correction_detail', project_id=project_id, fehler_id=fehler_id)


@login_required
@require_POST  
def correction_generate_single(request, project_id, fehler_id):
    """Generiert Korrekturvorschlag für einen einzelnen Fehler."""
    from .services.correction_service import CorrectionService
    
    project = get_object_or_404(BookProjects, id=project_id)
    fehler = get_object_or_404(LektoratsFehler, id=fehler_id, session__project=project)
    
    try:
        use_llm = request.POST.get('use_llm', 'false').lower() == 'true'
        
        service = CorrectionService(project)
        suggestion = service.process_fehler(fehler, use_llm=use_llm)
        
        # HTMX: Return JSON
        if request.headers.get('HX-Request'):
            if suggestion:
                return JsonResponse({
                    'success': True,
                    'suggestion': {
                        'id': suggestion.id,
                        'strategy': suggestion.strategy,
                        'original': suggestion.original_text,
                        'suggested': suggestion.suggested_text,
                        'alternatives': suggestion.alternatives,
                        'confidence': suggestion.confidence,
                    }
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Fehler als Stilmittel markiert'
                })
        
        # Regular form: Redirect back to detail page
        return redirect('writing_hub:correction_detail', project_id=project_id, fehler_id=fehler_id)
        
    except Exception as e:
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': False, 'error': str(e)})
        return redirect('writing_hub:correction_detail', project_id=project_id, fehler_id=fehler_id)
