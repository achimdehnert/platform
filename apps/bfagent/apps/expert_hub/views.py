"""
Expert Hub Views - Explosionsschutz Analyse System

BFA Agent Integration für:
- Ex-Zonen Klassifizierung (TRGS 720ff, ATEX)
- Equipment-Eignungsprüfung
- Stoffdatenbank
- CAD-Integration
"""

import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone

from .models import (
    ExAnalysisSession, ExZoneResult, ExEquipmentCheck, ExSubstance, 
    ExSessionDocument, ExWorkflowPhase, ExSessionPhaseStatus
)
from .agents.tools import (
    get_substance_properties,
    calculate_zone_extent,
    check_equipment_suitability,
    analyze_ventilation_effectiveness,
    read_cad_file,
    extract_ex_zones_from_cad,
    SUPPORTED_CAD_FORMATS,
)
from .agents.schemas import ZoneType, RiskLevel


# =============================================================================
# DASHBOARD
# =============================================================================

@login_required
def dashboard(request):
    """Expert Hub Dashboard - Explosionsschutz Übersicht"""
    
    # Statistiken
    sessions_count = ExAnalysisSession.objects.filter(created_by=request.user).count()
    active_sessions = ExAnalysisSession.objects.filter(
        created_by=request.user, 
        status__in=['draft', 'in_progress']
    ).count()
    completed_sessions = ExAnalysisSession.objects.filter(
        created_by=request.user, 
        status='completed'
    ).count()
    
    # Letzte Sessions mit Fortschrittsberechnung
    recent_sessions_qs = ExAnalysisSession.objects.filter(
        created_by=request.user
    ).order_by('-updated_at')[:5]
    
    # Fortschritt für jede Session berechnen
    total_phases = ExWorkflowPhase.objects.filter(parent__isnull=True).count()
    recent_sessions = []
    for session in recent_sessions_qs:
        completed_phases = ExSessionPhaseStatus.objects.filter(
            session=session
        ).exclude(content='').exclude(content__isnull=True).count()
        progress = int((completed_phases / total_phases) * 100) if total_phases > 0 else 0
        recent_sessions.append({
            'session': session,
            'progress': progress,
            'completed_phases': completed_phases,
            'total_phases': total_phases,
        })
    
    # Substanzen in DB
    substances_count = ExSubstance.objects.count()
    
    context = {
        "page_title": "Expert Hub - Explosionsschutz",
        "page_description": "Ex-Zonen Analyse nach TRGS 720ff und ATEX",
        "stats": {
            "sessions_total": sessions_count,
            "sessions_active": active_sessions,
            "sessions_completed": completed_sessions,
            "substances": substances_count,
        },
        "recent_sessions": recent_sessions,
        "total_phases": total_phases,
        "quick_actions": [
            {"name": "Neue Analyse", "url": "expert_hub:session_create", "icon": "bi-plus-circle", "color": "primary"},
            {"name": "Stoffsuche", "url": "expert_hub:substance_search", "icon": "bi-search", "color": "info"},
            {"name": "Equipment prüfen", "url": "expert_hub:equipment_check", "icon": "bi-shield-check", "color": "warning"},
            {"name": "CAD importieren", "url": "expert_hub:cad_import", "icon": "bi-file-earmark-binary", "color": "secondary"},
        ]
    }
    return render(request, "expert_hub/dashboard.html", context)


# =============================================================================
# ANALYSE SESSIONS
# =============================================================================

@login_required
def session_list(request):
    """Liste aller Analyse-Sessions"""
    sessions = ExAnalysisSession.objects.filter(
        created_by=request.user
    ).order_by('-updated_at')
    
    # Filter
    status_filter = request.GET.get('status')
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    context = {
        "page_title": "Meine Analysen",
        "sessions": sessions,
        "status_choices": ExAnalysisSession.STATUS_CHOICES,
        "current_filter": status_filter,
    }
    return render(request, "expert_hub/session_list.html", context)


@login_required
def session_create(request):
    """Neue Analyse-Session erstellen mit optionalem Dokument-Upload"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '')
        project_name = request.POST.get('project_name', '')
        project_location = request.POST.get('project_location', '')
        
        if not name:
            messages.error(request, "Name ist erforderlich")
            return redirect('expert_hub:session_create')
        
        session = ExAnalysisSession.objects.create(
            name=name,
            description=description,
            project_name=project_name,
            project_location=project_location,
            created_by=request.user,
            status='draft'
        )
        
        # Dateien verarbeiten
        files = request.FILES.getlist('documents')
        doc_types = request.POST.getlist('document_types')
        uploaded_count = 0
        
        for i, uploaded_file in enumerate(files):
            doc_type = doc_types[i] if i < len(doc_types) else 'other'
            
            ExSessionDocument.objects.create(
                session=session,
                file=uploaded_file,
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size,
                file_type=uploaded_file.content_type or '',
                document_type=doc_type,
                uploaded_by=request.user,
                analysis_status='pending'
            )
            uploaded_count += 1
        
        if uploaded_count > 0:
            messages.success(request, f'Analyse "{name}" erstellt mit {uploaded_count} Dokument(en)!')
        else:
            messages.success(request, f'Analyse "{name}" erstellt!')
        
        return redirect('expert_hub:session_detail', session_id=session.id)
    
    # Dokumenttypen für Dropdown
    doc_type_choices = ExSessionDocument.DOC_TYPE_CHOICES
    
    context = {
        "page_title": "Neue Analyse erstellen",
        "doc_type_choices": doc_type_choices,
    }
    return render(request, "expert_hub/session_create.html", context)


@login_required
def session_detail(request, session_id):
    """Analyse-Session Detail mit Ergebnissen, Dokumenten und Workflow"""
    session = get_object_or_404(ExAnalysisSession, id=session_id, created_by=request.user)
    
    zone_results = session.zone_results.all()
    equipment_checks = session.equipment_checks.all()
    documents = session.documents.all()
    
    # Workflow-Phasen mit Status für diese Session
    phases = ExWorkflowPhase.objects.filter(is_active=True).prefetch_related('children', 'children__children')
    
    # Session-Phasen-Status initialisieren falls nicht vorhanden
    for phase in ExWorkflowPhase.objects.filter(is_active=True):
        ExSessionPhaseStatus.objects.get_or_create(
            session=session,
            phase=phase,
            defaults={'status': 'not_started'}
        )
    
    # Workflow-Fortschritt berechnen (basierend auf Inhalt, nicht nur Status)
    phase_statuses = session.phase_statuses.select_related('phase')
    main_phases = phase_statuses.filter(phase__parent__isnull=True)
    total_phases = main_phases.count()
    
    # Zähle Phasen mit Inhalt
    phases_with_content = 0
    phase_content_map = {}  # Für Template: {phase_id: has_content}
    
    for ps in phase_statuses:
        has_content = ps.content and ps.content.strip()
        phase_content_map[ps.phase_id] = has_content
        if has_content and ps.phase.parent is None:
            phases_with_content += 1
    
    overall_progress = int((phases_with_content / total_phases * 100)) if total_phases > 0 else 0
    
    # Statistiken
    zones_by_type = {}
    for result in zone_results:
        zone_type = result.get_zone_type_display()
        zones_by_type[zone_type] = zones_by_type.get(zone_type, 0) + 1
    
    equipment_ok = equipment_checks.filter(is_suitable=True).count()
    equipment_issues = equipment_checks.filter(is_suitable=False).count()
    docs_pending = documents.filter(analysis_status='pending').count()
    docs_analyzed = documents.filter(analysis_status='completed').count()
    
    context = {
        "page_title": session.name,
        "session": session,
        "zone_results": zone_results,
        "equipment_checks": equipment_checks,
        "documents": documents,
        "phases": phases,
        "overall_progress": overall_progress,
        "phases_with_content": phases_with_content,
        "total_phases": total_phases,
        "phase_content_map": phase_content_map,
        "stats": {
            "zones_by_type": zones_by_type,
            "equipment_ok": equipment_ok,
            "equipment_issues": equipment_issues,
            "docs_total": documents.count(),
            "docs_pending": docs_pending,
            "docs_analyzed": docs_analyzed,
        }
    }
    return render(request, "expert_hub/session_detail.html", context)


# =============================================================================
# ZONEN-ANALYSE
# =============================================================================

@login_required
def zone_analysis(request, session_id=None):
    """Ex-Zonen Berechnung"""
    session = None
    if session_id:
        session = get_object_or_404(ExAnalysisSession, id=session_id, created_by=request.user)
    
    result = None
    if request.method == 'POST':
        # Parameter aus Formular
        room_name = request.POST.get('room_name', 'Raum')
        substance = request.POST.get('substance', '')
        release_rate = float(request.POST.get('release_rate', 0.001))
        ventilation_rate = float(request.POST.get('ventilation_rate', 0.5))
        room_volume = float(request.POST.get('room_volume', 100))
        release_type = request.POST.get('release_type', 'jet')
        
        # Berechnung
        result = calculate_zone_extent(
            release_rate_kg_s=release_rate,
            ventilation_rate_m3_s=ventilation_rate,
            substance_name=substance if substance else None,
            room_volume_m3=room_volume,
            release_type=release_type
        )
        
        # Speichern wenn Session vorhanden
        if session and result.get('success') and request.POST.get('save'):
            zone_type_map = {
                'Zone 0': 'zone_0', 'Zone 1': 'zone_1', 'Zone 2': 'zone_2',
                'Zone 20': 'zone_20', 'Zone 21': 'zone_21', 'Zone 22': 'zone_22',
            }
            
            ExZoneResult.objects.create(
                session=session,
                room_name=room_name,
                room_volume_m3=room_volume,
                zone_type=zone_type_map.get(result['zone_type'], 'zone_1'),
                zone_category='gas',
                zone_extent_m=result['zone_radius_m'] if isinstance(result['zone_radius_m'], (int, float)) else None,
                zone_volume_m3=result['zone_volume_m3'] if isinstance(result['zone_volume_m3'], (int, float)) else None,
                risk_level='medium',
                justification=result['zone_description'],
                input_parameters=result['input_parameters']
            )
            messages.success(request, f"Zonenergebnis für '{room_name}' gespeichert")
    
    context = {
        "page_title": "Ex-Zonen Berechnung",
        "session": session,
        "result": result,
        "release_types": [
            ('jet', 'Strahl/Spray'),
            ('pool', 'Verdunstung (Pfütze)'),
            ('diffuse', 'Diffuse Freisetzung'),
        ],
    }
    return render(request, "expert_hub/zone_analysis.html", context)


# =============================================================================
# STOFFSUCHE
# =============================================================================

@login_required
def substance_search(request):
    """Stoffdatenbank durchsuchen"""
    result = None
    query = request.GET.get('q', '').strip()
    
    if query:
        result = get_substance_properties(query)
    
    # Alle verfügbaren Stoffe für Autocomplete
    from .agents.tools import SUBSTANCE_DATABASE
    available_substances = list(SUBSTANCE_DATABASE.keys())
    
    context = {
        "page_title": "Stoffdatenbank",
        "query": query,
        "result": result,
        "available_substances": available_substances,
    }
    return render(request, "expert_hub/substance_search.html", context)


@login_required
@require_http_methods(["GET"])
def substance_api(request):
    """API für Stoffdaten (AJAX)"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({"success": False, "error": "Kein Suchbegriff"})
    
    result = get_substance_properties(query)
    return JsonResponse(result)


# =============================================================================
# EQUIPMENT-PRÜFUNG
# =============================================================================

@login_required
def equipment_check(request, session_id=None):
    """Equipment auf Ex-Schutz Eignung prüfen"""
    session = None
    if session_id:
        session = get_object_or_404(ExAnalysisSession, id=session_id, created_by=request.user)
    
    result = None
    if request.method == 'POST':
        equipment_name = request.POST.get('equipment_name', 'Equipment')
        ex_marking = request.POST.get('ex_marking', '')
        target_zone = request.POST.get('target_zone', 'Zone 1')
        
        if ex_marking:
            result = check_equipment_suitability(ex_marking, target_zone)
            
            # Speichern wenn Session vorhanden
            if session and result.get('success') and request.POST.get('save'):
                detected = result.get('detected', {})
                ExEquipmentCheck.objects.create(
                    session=session,
                    equipment_name=equipment_name,
                    ex_marking=ex_marking,
                    detected_category=detected.get('category', ''),
                    detected_temp_class=detected.get('temperature_class', ''),
                    detected_exp_group=detected.get('explosion_group', ''),
                    target_zone=target_zone,
                    required_category=result['requirements']['min_category'],
                    is_suitable=result['is_suitable'],
                    issues=result.get('issues', []),
                    recommendations=result.get('recommendations', [])
                )
                messages.success(request, f"Prüfung für '{equipment_name}' gespeichert")
    
    zones = ['Zone 0', 'Zone 1', 'Zone 2', 'Zone 20', 'Zone 21', 'Zone 22']
    
    context = {
        "page_title": "Equipment-Prüfung",
        "session": session,
        "result": result,
        "zones": zones,
    }
    return render(request, "expert_hub/equipment_check.html", context)


# =============================================================================
# LÜFTUNGSANALYSE
# =============================================================================

@login_required
def ventilation_analysis(request):
    """Lüftungseffektivität analysieren"""
    result = None
    
    if request.method == 'POST':
        room_volume = float(request.POST.get('room_volume', 100))
        air_flow = float(request.POST.get('air_flow', 1000))
        ventilation_type = request.POST.get('ventilation_type', 'technisch')
        
        result = analyze_ventilation_effectiveness(
            room_volume_m3=room_volume,
            air_flow_m3_h=air_flow,
            ventilation_type=ventilation_type
        )
    
    context = {
        "page_title": "Lüftungsanalyse",
        "result": result,
        "ventilation_types": [
            ('technisch', 'Technische Lüftung'),
            ('natürlich', 'Natürliche Lüftung'),
            ('keine', 'Keine Lüftung'),
        ],
    }
    return render(request, "expert_hub/ventilation_analysis.html", context)


# =============================================================================
# CAD IMPORT
# =============================================================================

@login_required
def cad_import(request, session_id=None):
    """CAD-Datei importieren und analysieren"""
    session = None
    if session_id:
        session = get_object_or_404(ExAnalysisSession, id=session_id, created_by=request.user)
    
    result = None
    zones = None
    
    if request.method == 'POST':
        file_path = request.POST.get('file_path', '')
        
        if file_path:
            result = read_cad_file(file_path)
            if result.get('success'):
                zones = extract_ex_zones_from_cad(result)
    
    context = {
        "page_title": "CAD Import",
        "session": session,
        "result": result,
        "zones": zones,
        "supported_formats": SUPPORTED_CAD_FORMATS,
    }
    return render(request, "expert_hub/cad_import.html", context)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@login_required
@require_http_methods(["POST"])
def session_upload_document(request, session_id):
    """Dokument zu bestehender Session hochladen"""
    session = get_object_or_404(ExAnalysisSession, id=session_id, created_by=request.user)
    
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        messages.error(request, "Keine Datei ausgewählt")
        return redirect('expert_hub:session_detail', session_id=session.id)
    
    doc_type = request.POST.get('document_type', 'other')
    description = request.POST.get('description', '')
    
    ExSessionDocument.objects.create(
        session=session,
        file=uploaded_file,
        original_filename=uploaded_file.name,
        file_size=uploaded_file.size,
        file_type=uploaded_file.content_type or '',
        document_type=doc_type,
        description=description,
        uploaded_by=request.user,
        analysis_status='pending'
    )
    
    messages.success(request, f'Dokument "{uploaded_file.name}" hochgeladen!')
    return redirect('expert_hub:session_detail', session_id=session.id)


# =============================================================================
# PHASE DETAIL & CONTENT
# =============================================================================

@login_required
def phase_detail(request, session_id, phase_id):
    """Phase-Detail: Inhalte bearbeiten, Dokumente zuordnen, KI-Aufbereitung"""
    session = get_object_or_404(ExAnalysisSession, id=session_id, created_by=request.user)
    phase = get_object_or_404(ExWorkflowPhase, id=phase_id)
    
    # Phase-Status für diese Session holen/erstellen
    phase_status, created = ExSessionPhaseStatus.objects.get_or_create(
        session=session,
        phase=phase,
        defaults={'status': 'not_started'}
    )
    
    # Dokumente für diese Phase
    phase_documents = session.documents.filter(phase=phase)
    unassigned_documents = session.documents.filter(phase__isnull=True)
    
    # Unter-Phasen
    child_phases = phase.children.all()
    
    # Alle Haupt-Phasen für Navigation (nur Top-Level)
    all_phases = ExWorkflowPhase.objects.filter(parent__isnull=True).order_by('order')
    
    # Vorherige und nächste Phase für Navigation
    prev_phase = ExWorkflowPhase.objects.filter(
        parent__isnull=True, order__lt=phase.order
    ).order_by('-order').first()
    next_phase = ExWorkflowPhase.objects.filter(
        parent__isnull=True, order__gt=phase.order
    ).order_by('order').first()
    
    # Falls aktuelle Phase eine Sub-Phase ist, Navigation auf Parent-Ebene
    if phase.parent:
        siblings = ExWorkflowPhase.objects.filter(parent=phase.parent).order_by('order')
        prev_phase = siblings.filter(order__lt=phase.order).order_by('-order').first()
        next_phase = siblings.filter(order__gt=phase.order).order_by('order').first()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        print(f">>> POST ACTION: {action} <<<")
        
        if action == 'save_content':
            # Inhalt speichern
            phase_status.content = request.POST.get('content', '')
            phase_status.notes = request.POST.get('notes', '')
            new_status = request.POST.get('status', phase_status.status)
            
            if new_status != phase_status.status:
                phase_status.status = new_status
                if new_status == 'in_progress' and not phase_status.started_at:
                    phase_status.started_at = timezone.now()
                elif new_status == 'completed':
                    phase_status.completed_at = timezone.now()
                    phase_status.progress_percent = 100
            
            phase_status.save()
            messages.success(request, f'Phase "{phase.title}" gespeichert!')
            
        elif action == 'assign_document':
            # Dokument dieser Phase zuordnen
            doc_id = request.POST.get('document_id')
            if doc_id:
                doc = get_object_or_404(ExSessionDocument, id=doc_id, session=session)
                doc.phase = phase
                doc.save()
                messages.success(request, f'Dokument "{doc.original_filename}" zugeordnet!')
                
        elif action == 'unassign_document':
            # Dokument von Phase entfernen
            doc_id = request.POST.get('document_id')
            if doc_id:
                doc = get_object_or_404(ExSessionDocument, id=doc_id, session=session)
                doc.phase = None
                doc.save()
                messages.info(request, f'Dokument "{doc.original_filename}" entfernt!')
                
        elif action == 'ai_generate':
            print(f">>> AI GENERATE ACTION für Phase {phase.number} <<<")
            
            # Erst Inhalt speichern (damit nichts verloren geht)
            phase_status.content = request.POST.get('content', '')
            phase_status.notes = request.POST.get('notes', '')
            phase_status.status = request.POST.get('status', phase_status.status)
            
            # Dokumente neu laden (nach möglichem Upload)
            phase_documents = ExSessionDocument.objects.filter(session=session, phase=phase)
            print(f">>> Dokumente für Phase: {phase_documents.count()}")
            
            # KI-Aufbereitung mit bestehendem Inhalt (echte LLM-Generierung)
            print(">>> Starte LLM-Generierung...")
            ai_content, ai_hints = generate_phase_content_ai(
                session, phase, phase_status, phase_documents,
                use_llm=True  # Echte LLM-Generierung über MCP Gateway
            )
            print(f">>> LLM fertig. Content: {len(ai_content)} chars, Hints: {ai_hints}")
            
            phase_status.ai_generated_content = ai_content
            # Hints in Session speichern für Anzeige im Template
            request.session['ai_hints'] = ai_hints
            phase_status.save()
            messages.success(request, 'KI-Inhalt generiert!')
            
        elif action == 'upload_document':
            # Inhalt mitspeichern beim Upload (damit nichts verloren geht)
            phase_status.content = request.POST.get('content', '')
            phase_status.notes = request.POST.get('notes', '')
            phase_status.status = request.POST.get('status', phase_status.status)
            phase_status.save()
            
            # Direkter Upload in der Phase
            uploaded_file = request.FILES.get('file')
            if uploaded_file:
                doc_type = request.POST.get('document_type', 'other')
                ExSessionDocument.objects.create(
                    session=session,
                    phase=phase,  # Direkt der Phase zugeordnet
                    file=uploaded_file,
                    original_filename=uploaded_file.name,
                    file_size=uploaded_file.size,
                    file_type=uploaded_file.content_type or '',
                    document_type=doc_type,
                    uploaded_by=request.user,
                    analysis_status='pending'
                )
                messages.success(request, f'Dokument hochgeladen und Inhalt gespeichert!')
            else:
                messages.error(request, 'Keine Datei ausgewählt')
        
        return redirect('expert_hub:phase_detail', session_id=session.id, phase_id=phase.id)
    
    # Hints aus Session holen und löschen
    ai_hints = request.session.pop('ai_hints', [])
    
    context = {
        "page_title": f"{phase.number} {phase.title}",
        "session": session,
        "phase": phase,
        "phase_status": phase_status,
        "phase_documents": phase_documents,
        "unassigned_documents": unassigned_documents,
        "child_phases": child_phases,
        "status_choices": ExSessionPhaseStatus.STATUS_CHOICES,
        "ai_hints": ai_hints,
        "all_phases": all_phases,
        "prev_phase": prev_phase,
        "next_phase": next_phase,
    }
    return render(request, "expert_hub/phase_detail.html", context)


def generate_phase_content_ai(session, phase, phase_status, documents, use_llm: bool = False):
    """
    KI-generierter Inhalt für eine Phase basierend auf Dokumenten und bestehendem Inhalt.
    
    Verwendet das Prompt-Template-System aus apps.expert_hub.prompts.
    
    Returns:
        Tuple[str, List[str]]: (Generierter Inhalt, Liste von Hinweisen/Tipps)
    """
    from apps.expert_hub.prompts import generate_phase_content
    return generate_phase_content(session, phase, phase_status, documents, use_llm=use_llm)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@login_required
@require_http_methods(["POST"])
def api_zone_calculate(request):
    """API: Zonenberechnung"""
    try:
        data = json.loads(request.body)
        result = calculate_zone_extent(
            release_rate_kg_s=float(data.get('release_rate', 0.001)),
            ventilation_rate_m3_s=float(data.get('ventilation_rate', 0.5)),
            substance_name=data.get('substance'),
            room_volume_m3=float(data.get('room_volume', 100)),
            release_type=data.get('release_type', 'jet')
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_http_methods(["POST"])
def api_equipment_check(request):
    """API: Equipment-Prüfung"""
    try:
        data = json.loads(request.body)
        result = check_equipment_suitability(
            ex_marking=data.get('ex_marking', ''),
            zone=data.get('zone', 'Zone 1')
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# =============================================================================
# DOCUMENT EXPORT
# =============================================================================

@login_required
def document_preview(request, session_id):
    """HTML-Vorschau des Explosionsschutzdokuments."""
    session = get_object_or_404(ExAnalysisSession, id=session_id)
    
    from .services.document_generator import ExSchutzDocumentGenerator
    
    generator = ExSchutzDocumentGenerator(session)
    html_preview = generator.get_html_preview()
    
    # Dokumente für Anhang-Auswahl
    documents = ExSessionDocument.objects.filter(session=session)
    
    # Pflichtphasen definieren (kritisch für Explosionsschutzdokument)
    REQUIRED_PHASES = ['1', '5', '6', '7', '8']  # Betriebsbereich, Stoffe, Gefährdung, Zonen, Schutzkonzept
    
    # Vollständigkeitsprüfung
    phases = ExWorkflowPhase.objects.filter(parent__isnull=True).order_by('order')
    phase_stats = []
    completed_count = 0
    total_count = phases.count()
    warnings = []
    errors = []
    
    for phase in phases:
        status = ExSessionPhaseStatus.objects.filter(session=session, phase=phase).first()
        has_content = status and status.content and status.content.strip()
        is_required = phase.number in REQUIRED_PHASES
        
        if has_content:
            completed_count += 1
        elif is_required:
            errors.append(f"Phase {phase.number} ({phase.title}) ist Pflicht und noch leer")
        
        # Prüfe auf Platzhalter-Text
        if has_content and status:
            content_lower = status.content.lower()
            if '[todo' in content_lower or '[name eintragen]' in content_lower or '[zu ergänzen]' in content_lower:
                warnings.append(f"Phase {phase.number}: Enthält noch Platzhalter-Text")
        
        phase_stats.append({
            'phase': phase,
            'status': status,
            'has_content': has_content,
            'is_required': is_required,
        })
    
    # Stoffdaten-Prüfung (Phase 5)
    phase5_status = ExSessionPhaseStatus.objects.filter(
        session=session, 
        phase__number='5'
    ).first()
    if phase5_status and phase5_status.content:
        if 'ueg' not in phase5_status.content.lower() and 'untere explosionsgrenze' not in phase5_status.content.lower():
            warnings.append("Phase 5: UEG (Untere Explosionsgrenze) fehlt")
    
    # Dokument-Prüfung
    if not documents.exists():
        warnings.append("Keine Dokumente hochgeladen (z.B. Sicherheitsdatenblätter)")
    
    completeness_percent = int((completed_count / total_count) * 100) if total_count > 0 else 0
    can_export = len(errors) == 0  # Export nur wenn keine Pflichtfeld-Fehler
    
    context = {
        'page_title': 'Dokument-Vorschau',
        'session': session,
        'html_preview': html_preview,
        'documents': documents,
        'phase_stats': phase_stats,
        'completed_count': completed_count,
        'total_count': total_count,
        'completeness_percent': completeness_percent,
        'warnings': warnings,
        'errors': errors,
        'can_export': can_export,
    }
    return render(request, 'expert_hub/document_preview.html', context)


@login_required
def document_export(request, session_id):
    """Word-Dokument herunterladen."""
    from django.http import HttpResponse
    from .services.document_generator import ExSchutzDocumentGenerator
    
    session = get_object_or_404(ExAnalysisSession, id=session_id)
    
    try:
        generator = ExSchutzDocumentGenerator(session)
        generator.create_document()
        
        buffer = generator.save_to_buffer()
        filename = generator.get_filename()
        
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except ImportError as e:
        messages.error(request, f'python-docx nicht installiert: {e}')
        return redirect('expert_hub:document_preview', session_id=session_id)
    except Exception as e:
        messages.error(request, f'Fehler beim Export: {e}')
        return redirect('expert_hub:document_preview', session_id=session_id)


@login_required
def api_ai_generate(request, session_id, phase_id):
    """HTMX API: KI-Inhalt generieren."""
    from django.http import HttpResponse
    
    print(f">>> API AI GENERATE: session={session_id}, phase={phase_id}")
    
    session = get_object_or_404(ExAnalysisSession, id=session_id)
    phase = get_object_or_404(ExWorkflowPhase, id=phase_id)
    phase_status, _ = ExSessionPhaseStatus.objects.get_or_create(
        session=session, phase=phase
    )
    phase_documents = ExSessionDocument.objects.filter(session=session, phase=phase)
    
    print(f">>> Starte LLM-Generierung für Phase {phase.number}...")
    
    try:
        ai_content, ai_hints = generate_phase_content_ai(
            session, phase, phase_status, phase_documents,
            use_llm=True
        )
        print(f">>> LLM fertig. Content: {len(ai_content)} chars")
        
        # Speichern
        phase_status.ai_generated_content = ai_content
        phase_status.save()
        
        # HTML Response
        hints_html = ""
        if ai_hints:
            hints_html = "<ul class='small text-muted mt-2 mb-0'>"
            for hint in ai_hints:
                hints_html += f"<li>{hint}</li>"
            hints_html += "</ul>"
        
        html = f'''
        <div class="alert alert-success mt-3">
            <i class="bi bi-check-circle me-1"></i> KI-Inhalt generiert!
            {hints_html}
        </div>
        <div class="card mt-2">
            <div class="card-header bg-light d-flex justify-content-between">
                <span><i class="bi bi-robot me-1"></i> Generierter Inhalt</span>
                <button class="btn btn-sm btn-primary" onclick="document.getElementById('content').value = document.getElementById('ai-content-text').innerText; alert('Inhalt übernommen!');">
                    <i class="bi bi-clipboard me-1"></i>Übernehmen
                </button>
            </div>
            <div class="card-body">
                <pre id="ai-content-text" style="white-space: pre-wrap; font-family: inherit; margin: 0;">{ai_content}</pre>
            </div>
        </div>
        '''
        return HttpResponse(html)
        
    except Exception as e:
        print(f">>> FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f'''
        <div class="alert alert-danger mt-3">
            <i class="bi bi-exclamation-triangle me-1"></i> Fehler: {str(e)}
        </div>
        ''')


@login_required
def upload_template(request, session_id):
    """Corporate Design Template hochladen."""
    session = get_object_or_404(ExAnalysisSession, id=session_id, created_by=request.user)
    
    if request.method == 'POST':
        template_file = request.FILES.get('template_file')
        company_logo = request.FILES.get('company_logo')
        
        if template_file:
            # Validiere Dateiendung
            if not template_file.name.lower().endswith(('.docx', '.doc')):
                messages.error(request, 'Bitte eine Word-Datei (.docx) hochladen.')
            else:
                session.template_file = template_file
                messages.success(request, f'Vorlage "{template_file.name}" hochgeladen.')
        
        if company_logo:
            # Validiere Bildformat
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml']
            if company_logo.content_type not in allowed_types:
                messages.error(request, 'Bitte ein gültiges Bildformat hochladen (JPG, PNG, GIF, SVG).')
            else:
                session.company_logo = company_logo
                messages.success(request, 'Logo hochgeladen.')
        
        session.save()
    
    return redirect('expert_hub:session_detail', session_id=session_id)


@login_required
def remove_template(request, session_id):
    """Corporate Design Template entfernen."""
    session = get_object_or_404(ExAnalysisSession, id=session_id, created_by=request.user)
    
    if request.method == 'POST':
        if session.template_file:
            session.template_file.delete(save=False)
            session.template_file = None
        if session.company_logo:
            session.company_logo.delete(save=False)
            session.company_logo = None
        session.save()
        messages.success(request, 'Corporate Design Vorlage entfernt.')
    
    return redirect('expert_hub:session_detail', session_id=session_id)
