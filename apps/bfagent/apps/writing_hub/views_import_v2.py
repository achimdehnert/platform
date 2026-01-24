"""
Import V2 Views - Smart Import with Multi-Step LLM Pipeline

This module provides the new V2 import workflow:
1. Upload/Paste document
2. AI analyzes and extracts data
3. User reviews and selects items
4. Outline recommendations shown
5. Project created with selected data

Author: BF Agent Team
Date: 2026-01-22
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from apps.bfagent.models_main import BookProjects, Characters, Worlds, BookChapters
from apps.writing_hub.models_import_framework import (
    ImportSession,
    OutlineTemplate,
    OutlineRecommendation,
    ProjectOutline,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def create_import_session(user, filename: str, source_type: str = 'upload') -> ImportSession:
    """Create a new import session"""
    session = ImportSession.objects.create(
        session_id=str(uuid.uuid4()),
        user=user,
        source_filename=filename,
        source_type=source_type,
        status='started',
    )
    return session


def get_import_session(request) -> Optional[ImportSession]:
    """Get current import session from request"""
    session_id = request.session.get('import_v2_session_id')
    if session_id:
        try:
            return ImportSession.objects.get(session_id=session_id)
        except ImportSession.DoesNotExist:
            pass
    return None


# =============================================================================
# V2 Import Views
# =============================================================================

@login_required
def import_v2_start(request):
    """
    Step 1: Start V2 import - upload file or paste content
    """
    if request.method == 'POST':
        # Check for file upload
        uploaded_file = request.FILES.get('document')
        pasted_content = request.POST.get('pasted_content', '').strip()
        
        if not uploaded_file and not pasted_content:
            messages.error(request, "Bitte lade eine Datei hoch oder füge Text ein.")
            return redirect('writing_hub:import_v2_start')
        
        # Determine source
        if uploaded_file:
            filename = uploaded_file.name
            content = ''
            for chunk in uploaded_file.chunks():
                try:
                    content += chunk.decode('utf-8')
                except UnicodeDecodeError:
                    content += chunk.decode('latin-1')
            source_type = 'upload'
        else:
            filename = 'pasted_content.md'
            content = pasted_content
            source_type = 'paste'
        
        # Create import session
        session = create_import_session(request.user, filename, source_type)
        session.raw_content = content
        session.status = 'analyzing'
        session.save()
        
        # Store session ID
        request.session['import_v2_session_id'] = session.session_id
        
        logger.info(f"Import V2 started: {session.session_id} - {filename}")
        
        # Redirect to analysis
        return redirect('writing_hub:import_v2_analyze')
    
    # GET - show upload form
    return render(request, 'writing_hub/import_v2/start.html', {
        'page_title': 'Smart Import V2',
    })


@login_required
def import_v2_analyze(request):
    """
    Step 2: Run AI analysis on uploaded content
    """
    session = get_import_session(request)
    if not session:
        messages.error(request, "Keine Import-Session gefunden.")
        return redirect('writing_hub:import_v2_start')
    
    if request.method == 'POST':
        # Run analysis
        try:
            from apps.writing_hub.services.smart_import_service import SmartImportService
            
            service = SmartImportService()
            result = service.import_document_sync(
                session.raw_content, 
                session.source_filename
            )
            
            # Store results
            session.extracted_data = result.model_dump()
            session.document_type = result.metadata.document_type
            session.status = 'review'
            session.save()
            
            logger.info(f"Import V2 analysis complete: {session.session_id}")
            
            return redirect('writing_hub:import_v2_review')
            
        except Exception as e:
            logger.error(f"Import V2 analysis failed: {e}")
            session.status = 'failed'
            session.error_message = str(e)
            session.save()
            messages.error(request, f"Analyse fehlgeschlagen: {e}")
            return redirect('writing_hub:import_v2_start')
    
    # GET - show analysis in progress
    return render(request, 'writing_hub/import_v2/analyze.html', {
        'session': session,
        'page_title': 'Dokument analysieren',
    })


@login_required
def import_v2_review(request):
    """
    Step 3: Review extracted data and select items
    """
    session = get_import_session(request)
    if not session or not session.extracted_data:
        messages.error(request, "Keine Analyse-Daten gefunden.")
        return redirect('writing_hub:import_v2_start')
    
    data = session.extracted_data
    metadata = data.get('metadata', {})
    
    if request.method == 'POST':
        # Save selections
        selected = {
            'chapters': request.POST.getlist('chapters'),
            'characters': request.POST.getlist('characters'),
            'locations': request.POST.getlist('locations'),
            'metadata_overrides': {
                'title': request.POST.get('title', metadata.get('title', '')),
                'genre': request.POST.get('genre', metadata.get('genre_primary', '')),
                'logline': request.POST.get('logline', metadata.get('logline', '')),
            }
        }
        
        session.selected_items = selected
        session.save()
        
        return redirect('writing_hub:import_v2_outline')
    
    # GET - show review form
    return render(request, 'writing_hub/import_v2/review.html', {
        'session': session,
        'metadata': metadata,
        'characters': data.get('characters', []),
        'locations': data.get('locations', []),
        'chapters': data.get('chapters', []),
        'plot_points': data.get('plot_points', []),
        'page_title': 'Daten überprüfen',
    })


@login_required
def import_v2_outline(request):
    """
    Step 4: Show outline recommendations and let user select
    """
    session = get_import_session(request)
    if not session or not session.extracted_data:
        messages.error(request, "Keine Analyse-Daten gefunden.")
        return redirect('writing_hub:import_v2_start')
    
    # Get or generate recommendations
    recommendations = list(session.recommendations.all())
    
    if not recommendations:
        # Generate recommendations
        try:
            from apps.writing_hub.services.outline_recommender_service import OutlineRecommenderService
            from apps.writing_hub.services.smart_import_service import ImportResultV2
            
            # Reconstruct import result
            import_result = ImportResultV2(**session.extracted_data)
            
            service = OutlineRecommenderService()
            rec_results = service.recommend_outline_sync(import_result=import_result)
            
            # Save recommendations to DB
            for rec in rec_results:
                try:
                    template = OutlineTemplate.objects.get(code=rec.template_code)
                    OutlineRecommendation.objects.create(
                        import_session=session,
                        template=template,
                        rank=rec.rank,
                        match_score=rec.match_score,
                        match_reason=rec.match_reason,
                    )
                except OutlineTemplate.DoesNotExist:
                    logger.warning(f"Template not found: {rec.template_code}")
            
            recommendations = list(session.recommendations.all())
            
        except Exception as e:
            logger.error(f"Outline recommendation failed: {e}")
            messages.warning(request, f"Outline-Empfehlungen konnten nicht generiert werden: {e}")
    
    if request.method == 'POST':
        selected_template_id = request.POST.get('template_id')
        
        if selected_template_id:
            # Mark as selected
            session.recommendations.filter(template_id=selected_template_id).update(was_selected=True)
            
            # Store in selected_items
            if session.selected_items:
                session.selected_items['template_id'] = selected_template_id
            else:
                session.selected_items = {'template_id': selected_template_id}
            session.save()
        
        return redirect('writing_hub:import_v2_create')
    
    # Load templates for recommendations
    for rec in recommendations:
        rec.template_data = rec.template
    
    # Also show all templates
    all_templates = OutlineTemplate.objects.filter(is_active=True).select_related('category')
    
    return render(request, 'writing_hub/import_v2/outline.html', {
        'session': session,
        'recommendations': recommendations,
        'all_templates': all_templates,
        'metadata': session.extracted_data.get('metadata', {}),
        'page_title': 'Outline auswählen',
    })


@login_required
def import_v2_create(request):
    """
    Step 5: Create the project with selected data
    """
    session = get_import_session(request)
    if not session or not session.extracted_data:
        messages.error(request, "Keine Import-Daten gefunden.")
        return redirect('writing_hub:import_v2_start')
    
    if request.method == 'POST':
        try:
            data = session.extracted_data
            metadata = data.get('metadata', {})
            selected = session.selected_items or {}
            
            # Get overrides
            overrides = selected.get('metadata_overrides', {})
            
            # Create project
            project = BookProjects.objects.create(
                title=overrides.get('title') or metadata.get('title', 'Imported Project'),
                genre=overrides.get('genre') or metadata.get('genre_primary', ''),
                description=metadata.get('premise', ''),
                
                # V2 fields
                logline=overrides.get('logline') or metadata.get('logline'),
                central_question=metadata.get('central_question'),
                narrative_voice=metadata.get('narrative_voice'),
                prose_style=metadata.get('prose_style'),
                pacing_style=metadata.get('pacing'),
                dialogue_style=metadata.get('dialogue_style'),
                comparable_titles=json.dumps(metadata.get('comparable_titles', [])),
                spice_level=metadata.get('spice_level'),
                content_warnings=json.dumps(metadata.get('content_warnings', [])),
                series_arc=data.get('series_arc'),
                threads_to_continue=json.dumps(data.get('threads_to_continue', [])),
                
                # Meta
                target_word_count=metadata.get('target_word_count', 80000),
                status='planning',
            )
            
            # Create characters
            selected_chars = set(selected.get('characters', []))
            for char_data in data.get('characters', []):
                char_name = char_data.get('name', '')
                if not selected_chars or char_name in selected_chars:
                    # Parse age
                    age_str = char_data.get('age')
                    age = None
                    if age_str:
                        try:
                            age = int(age_str.split('-')[0].strip())
                        except (ValueError, AttributeError):
                            pass
                    
                    Characters.objects.create(
                        project=project,
                        name=char_name,
                        role=char_data.get('role', 'supporting'),
                        age=age,
                        description=char_data.get('personality', ''),
                        background=char_data.get('background'),
                        motivation=char_data.get('motivation'),
                        arc=char_data.get('arc'),
                        appearance=char_data.get('appearance'),
                        
                        # V2 fields
                        wound=char_data.get('wound'),
                        secret=char_data.get('secret'),
                        dark_trait=char_data.get('dark_trait'),
                        strengths=json.dumps(char_data.get('strengths', [])),
                        weaknesses=json.dumps(char_data.get('weaknesses', [])),
                        voice_sample=char_data.get('voice_sample'),
                        speech_patterns=char_data.get('speech_patterns'),
                        occupation=char_data.get('occupation'),
                        organization=char_data.get('organization'),
                        relationships_json=char_data.get('relationships'),
                        importance=char_data.get('importance', 3),
                        nationality=char_data.get('nationality'),
                        ethnicity=char_data.get('ethnicity'),
                    )
            
            # Create locations/worlds
            selected_locs = set(selected.get('locations', []))
            for loc_data in data.get('locations', []):
                loc_name = loc_data.get('name', '')
                if not selected_locs or loc_name in selected_locs:
                    Worlds.objects.create(
                        project=project,
                        name=loc_name,
                        description=loc_data.get('description', ''),
                        world_type=loc_data.get('type', 'location'),
                    )
            
            # Create chapters
            selected_chs = set(selected.get('chapters', []))
            for ch_data in data.get('chapters', []):
                ch_num = ch_data.get('number', 0)
                if not selected_chs or str(ch_num) in selected_chs:
                    BookChapters.objects.create(
                        project=project,
                        chapter_number=ch_num,
                        title=ch_data.get('title', f'Kapitel {ch_num}'),
                        summary=ch_data.get('summary', ''),
                        status='planned',
                    )
            
            # Create outline if template selected
            template_id = selected.get('template_id')
            if template_id:
                try:
                    template = OutlineTemplate.objects.get(id=template_id)
                    ProjectOutline.objects.create(
                        project=project,
                        template=template,
                        outline_data=template.structure_json,
                        status='draft',
                    )
                    
                    # Store template code on project
                    project.outline_template_code = template.code
                    project.save()
                    
                    # Increment usage
                    template.usage_count += 1
                    template.save()
                except OutlineTemplate.DoesNotExist:
                    pass
            
            # Update session
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.created_project = project
            session.save()
            
            # Clear session
            if 'import_v2_session_id' in request.session:
                del request.session['import_v2_session_id']
            
            messages.success(request, f"Projekt '{project.title}' erfolgreich erstellt!")
            logger.info(f"Import V2 complete: Created project {project.id}")
            
            return redirect('writing_hub:project_hub', project_id=project.id)
            
        except Exception as e:
            logger.error(f"Import V2 create failed: {e}")
            messages.error(request, f"Projekt-Erstellung fehlgeschlagen: {e}")
            return redirect('writing_hub:import_v2_review')
    
    # GET - show confirmation
    data = session.extracted_data
    selected = session.selected_items or {}
    
    # Count selected items
    counts = {
        'characters': len(selected.get('characters', [])) or len(data.get('characters', [])),
        'locations': len(selected.get('locations', [])) or len(data.get('locations', [])),
        'chapters': len(selected.get('chapters', [])) or len(data.get('chapters', [])),
    }
    
    # Get selected template
    template = None
    if selected.get('template_id'):
        try:
            template = OutlineTemplate.objects.get(id=selected['template_id'])
        except OutlineTemplate.DoesNotExist:
            pass
    
    return render(request, 'writing_hub/import_v2/create.html', {
        'session': session,
        'metadata': data.get('metadata', {}),
        'selected': selected,
        'counts': counts,
        'template': template,
        'page_title': 'Projekt erstellen',
    })


# =============================================================================
# API Endpoints
# =============================================================================

@login_required
@require_http_methods(["POST"])
def import_v2_api_analyze(request):
    """
    API endpoint to run analysis asynchronously
    """
    session = get_import_session(request)
    if not session:
        return JsonResponse({'error': 'No session found'}, status=400)
    
    try:
        from apps.writing_hub.services.smart_import_service import SmartImportService
        
        service = SmartImportService()
        result = service.import_document_sync(
            session.raw_content,
            session.source_filename
        )
        
        session.extracted_data = result.model_dump()
        session.document_type = result.metadata.document_type
        session.status = 'review'
        session.save()
        
        return JsonResponse({
            'success': True,
            'document_type': session.document_type,
            'metadata': result.metadata.model_dump(),
            'counts': {
                'characters': len(result.characters),
                'locations': len(result.locations),
                'chapters': len(result.chapters),
            }
        })
        
    except Exception as e:
        logger.error(f"API analyze failed: {e}")
        session.status = 'failed'
        session.error_message = str(e)
        session.save()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def import_v2_api_status(request):
    """
    API endpoint to check session status
    """
    session = get_import_session(request)
    if not session:
        return JsonResponse({'error': 'No session found'}, status=400)
    
    return JsonResponse({
        'session_id': session.session_id,
        'status': session.status,
        'document_type': session.document_type,
        'error_message': session.error_message,
    })
