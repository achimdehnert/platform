"""
Writing Hub Views
Complete Book Writing Workflow: Idea → Finished Book
"""
import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from django.db.models import Q, Max
from apps.bfagent.models import BookProjects, BookChapters, Characters, Worlds, Llms
from .models import OutlineVersion, ContentType, StructureFramework, FrameworkBeat

# Import lookups for project creation
try:
    from apps.bfagent.models import Genres, TargetAudiences
except ImportError:
    Genres = None
    TargetAudiences = None

logger = logging.getLogger(__name__)


def dashboard(request):
    """Writing Hub Dashboard with stats"""
    from apps.writing_hub.models_style import AuthorStyleDNA
    from apps.writing_hub.models import BookSeries
    
    # Get counts
    projects_count = BookProjects.objects.count()
    characters_count = Characters.objects.count()
    worlds_count = Worlds.objects.count()
    
    # Series count
    if request.user.is_authenticated:
        series_count = BookSeries.objects.filter(created_by=request.user).count()
        series_list = BookSeries.objects.filter(created_by=request.user).order_by('-created_at')[:5]
    else:
        series_count = BookSeries.objects.count()
        series_list = BookSeries.objects.order_by('-created_at')[:5]
    
    # Style DNAs count (user's own if logged in, otherwise all)
    if request.user.is_authenticated:
        styles_count = AuthorStyleDNA.objects.filter(author=request.user).count()
    else:
        styles_count = AuthorStyleDNA.objects.count()
    
    # Get recent projects
    recent_projects = BookProjects.objects.order_by('-created_at')[:5]
    
    context = {
        'projects_count': projects_count,
        'styles_count': styles_count,
        'characters_count': characters_count,
        'worlds_count': worlds_count,
        'series_count': series_count,
        'series_list': series_list,
        'recent_projects': recent_projects,
    }
    
    return render(request, 'writing_hub/dashboard.html', context)


def outline_editor(request, project_id):
    """Interactive Outline Editor for a project"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Parse content type from project settings
    content_type = 'novel'
    if project.genre_settings:
        try:
            settings = json.loads(project.genre_settings)
            content_type = settings.get('content_type', 'novel')
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Get existing chapters for this project
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    # Convert chapters to JSON-serializable format
    chapters_data = []
    for ch in chapters:
        # Try to extract structured data from notes
        beat = ''
        act = 1
        emotional_arc = ''
        raw_outline = ch.outline or ''
        
        if ch.notes:
            try:
                notes_data = json.loads(ch.notes) if isinstance(ch.notes, str) else ch.notes
                beat = notes_data.get('beat', '')
                act = notes_data.get('act', 1)
                emotional_arc = notes_data.get('emotional_arc', '')
                raw_outline = notes_data.get('raw_outline', ch.outline or '')
            except (json.JSONDecodeError, TypeError):
                pass
        
        chapters_data.append({
            'id': ch.id,
            'number': ch.chapter_number,
            'title': ch.title,
            'beat': beat,
            'act': act,
            'outline': raw_outline,
            'emotional_arc': emotional_arc,
            'target_words': ch.target_word_count or 2000,
        })
    
    # Try to get content type config from DB, fall back to defaults
    db_content_type = None
    db_frameworks = []
    default_framework = None
    
    try:
        db_content_type = ContentType.objects.filter(slug=content_type, is_active=True).first()
        if db_content_type:
            db_frameworks = list(StructureFramework.objects.filter(
                content_type=db_content_type, 
                is_active=True
            ).prefetch_related('beats').order_by('sort_order'))
            default_framework = next((f for f in db_frameworks if f.is_default), db_frameworks[0] if db_frameworks else None)
    except Exception:
        pass  # Fall back to hardcoded defaults
    
    # Determine selected framework
    framework_slug = 'save_the_cat'  # Default
    if default_framework:
        framework_slug = default_framework.slug
    
    if hasattr(project, 'metadata') and project.metadata:
        try:
            meta = json.loads(project.metadata) if isinstance(project.metadata, str) else project.metadata
            framework_slug = meta.get('outline_framework', framework_slug)
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Build frameworks data for JavaScript
    frameworks_json = []
    if db_frameworks:
        for fw in db_frameworks:
            beats_list = []
            for beat in fw.beats.all().order_by('sort_order'):
                beats_list.append({
                    'name': beat.name,
                    'name_de': beat.name_de or beat.name,
                    'position': beat.position,
                    'part': beat.part,
                    'description': beat.description_de or beat.description,
                    'llm_prompt': beat.llm_prompt_template,
                })
            frameworks_json.append({
                'slug': fw.slug,
                'name': fw.name,
                'name_de': fw.name_de or fw.name,
                'icon': fw.icon,
                'description': fw.description,
                'is_default': fw.is_default,
                'default_section_count': fw.default_section_count,
                'llm_system_prompt': fw.llm_system_prompt,
                'llm_user_template': fw.llm_user_template,
                'beats': beats_list,
            })
    
    # Content type config from DB or defaults
    if db_content_type:
        content_type_name = db_content_type.name_de or db_content_type.name
        section_label = db_content_type.section_label
        content_type_icon = db_content_type.icon
        llm_system_prompt = db_content_type.llm_system_prompt
    else:
        # Fallback defaults
        fallback_config = {
            'novel': {'name': 'Roman', 'section_label': 'Kapitel', 'icon': 'bi-book'},
            'essay': {'name': 'Essay', 'section_label': 'Abschnitt', 'icon': 'bi-file-text'},
            'scientific': {'name': 'Wissenschaftliche Arbeit', 'section_label': 'Abschnitt', 'icon': 'bi-mortarboard'},
        }
        config = fallback_config.get(content_type, fallback_config['novel'])
        content_type_name = config['name']
        section_label = config['section_label']
        content_type_icon = config['icon']
        llm_system_prompt = ''
    
    context = {
        'project': project,
        'chapters': chapters,
        'chapters_json': json.dumps(chapters_data),
        'framework': framework_slug,
        'content_type': content_type,
        'content_type_name': content_type_name,
        'section_label': section_label,
        'content_type_icon': content_type_icon,
        'db_frameworks': db_frameworks,  # For template rendering
        'frameworks_json': json.dumps(frameworks_json),  # For JavaScript
        'has_db_frameworks': len(db_frameworks) > 0,
    }
    
    return render(request, 'writing_hub/outline_editor.html', context)


@require_http_methods(["POST"])
def save_outline(request, project_id):
    """Save outline chapters for a project"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        framework = data.get('framework', 'save_the_cat')
        chapters_data = data.get('chapters', [])
        
        # Update project metadata with framework
        if hasattr(project, 'metadata'):
            try:
                meta = json.loads(project.metadata) if isinstance(project.metadata, str) else (project.metadata or {})
            except (json.JSONDecodeError, TypeError):
                meta = {}
            meta['outline_framework'] = framework
            project.metadata = json.dumps(meta)
            project.save()
        
        # Process chapters - use update_or_create to avoid duplicate key errors
        saved_chapters = []
        processed_numbers = set()
        
        for idx, ch_data in enumerate(chapters_data):
            chapter_id = ch_data.get('id')
            chapter_number = ch_data.get('number', idx + 1)
            
            # Track processed chapter numbers to avoid duplicates
            if chapter_number in processed_numbers:
                continue
            processed_numbers.add(chapter_number)
            
            # Use update_or_create to handle existing chapters properly
            chapter, created = BookChapters.objects.update_or_create(
                project=project,
                chapter_number=chapter_number,
                defaults={}  # Will be updated below
            )
            
            # Update chapter fields
            chapter.chapter_number = ch_data.get('number', idx + 1)
            chapter.title = ch_data.get('title', f'Kapitel {idx + 1}')
            chapter.target_word_count = ch_data.get('target_words', 2000)
            
            # Build comprehensive outline that includes beat info for Chapter Writer
            beat = ch_data.get('beat', '')
            act = ch_data.get('act', 1)
            emotional_arc = ch_data.get('emotional_arc', '')
            raw_outline = ch_data.get('outline', '')
            
            # Combine into structured outline for downstream processing
            outline_parts = []
            if beat:
                outline_parts.append(f"**Beat:** {beat}")
            if act:
                outline_parts.append(f"**Akt:** {act}")
            if emotional_arc:
                outline_parts.append(f"**Emotionaler Bogen:** {emotional_arc}")
            if raw_outline:
                outline_parts.append(f"\n**Handlung:**\n{raw_outline}")
            
            chapter.outline = "\n".join(outline_parts) if outline_parts else raw_outline
            
            # Also store structured data in notes for UI to read back
            extra_data = {
                'beat': beat,
                'act': act,
                'emotional_arc': emotional_arc,
                'raw_outline': raw_outline,
            }
            chapter.notes = json.dumps(extra_data)
            
            chapter.save()
            
            saved_chapters.append({
                'id': chapter.id,
                'number': chapter.chapter_number,
                'title': chapter.title,
                'beat': extra_data['beat'],
                'act': extra_data['act'],
                'outline': chapter.outline,
                'emotional_arc': extra_data['emotional_arc'],
                'target_words': chapter.target_word_count,
            })
        
        # Delete chapters that were removed
        saved_ids = {ch['id'] for ch in saved_chapters}
        BookChapters.objects.filter(project=project).exclude(id__in=saved_ids).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{len(saved_chapters)} Kapitel gespeichert',
            'chapters': saved_chapters
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def projects_list(request):
    """List all book projects for outline editing"""
    projects = BookProjects.objects.all().order_by('-created_at')
    
    # Add chapter count to each project
    for project in projects:
        project.chapter_count = BookChapters.objects.filter(project=project).count()
    
    context = {
        'projects': projects,
    }
    
    return render(request, 'writing_hub/projects_list.html', context)


@require_http_methods(["POST", "DELETE"])
def delete_project(request, project_id):
    """Delete a project and all related data"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        title = project.title
        # Delete related data first (cascade should handle this, but be explicit)
        BookChapters.objects.filter(project=project).delete()
        Characters.objects.filter(project=project).delete()
        Worlds.objects.filter(project=project).delete()
        OutlineVersion.objects.filter(project=project).delete()
        project.delete()
        return JsonResponse({'success': True, 'message': f'Projekt "{title}" gelöscht'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_versions(request, project_id):
    """Get all outline versions for a project"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    versions = OutlineVersion.objects.filter(project=project).order_by('-version_number')
    
    versions_data = [{
        'id': v.id,
        'version_number': v.version_number,
        'version_name': v.version_name or f'Version {v.version_number}',
        'framework': v.framework,
        'framework_display': v.get_framework_display(),
        'status': v.status,
        'status_display': v.get_status_display(),
        'chapter_count': v.chapter_count,
        'is_active': v.is_active,
        'is_locked': v.is_locked,
        'created_at': v.created_at.isoformat(),
        'updated_at': v.updated_at.isoformat(),
        'can_proceed': v.can_proceed_to_writing(),
        'project_feedback': v.project_feedback or '',
        'chapter_feedback': v.chapter_feedback or {},
    } for v in versions]
    
    return JsonResponse({
        'success': True,
        'versions': versions_data,
        'total': len(versions_data)
    })


@require_http_methods(["POST"])
def save_version(request, project_id):
    """Save current outline as a new version"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        framework = data.get('framework', 'save_the_cat')
        chapters_data = data.get('chapters', [])
        version_name = data.get('version_name', '')
        notes = data.get('notes', '')
        
        # Deactivate all previous versions
        OutlineVersion.objects.filter(project=project).update(is_active=False)
        
        # Create new version as active
        version = OutlineVersion(
            project=project,
            framework=framework,
            version_name=version_name,
            notes=notes,
            chapters_snapshot=chapters_data,
            status=OutlineVersion.Status.DRAFT,
            is_active=True,
            created_by=request.user if request.user.is_authenticated else None
        )
        version.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Version {version.version_number} gespeichert',
            'version': {
                'id': version.id,
                'version_number': version.version_number,
                'version_name': version.version_name,
                'framework': version.framework,
                'status': version.status,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def restore_version(request, project_id, version_id):
    """Restore a specific version to the active chapters"""
    project = get_object_or_404(BookProjects, id=project_id)
    version = get_object_or_404(OutlineVersion, id=version_id, project=project)
    
    try:
        # Restore chapters from snapshot
        version.restore_to_chapters()
        
        # Mark this version as active
        OutlineVersion.objects.filter(project=project).update(is_active=False)
        version.is_active = True
        version.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Version {version.version_number} wiederhergestellt',
            'chapters': version.chapters_snapshot,
            'framework': version.framework
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def update_version_status(request, project_id, version_id):
    """Update status of a version (draft -> review -> approved -> finalized)"""
    project = get_object_or_404(BookProjects, id=project_id)
    version = get_object_or_404(OutlineVersion, id=version_id, project=project)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        unlock_requested = data.get('unlock', False)
        
        if new_status not in [s[0] for s in OutlineVersion.Status.choices]:
            return JsonResponse({'success': False, 'error': 'Ungültiger Status'}, status=400)
        
        # Handle locked versions
        if version.is_locked and new_status != 'finalized':
            if not unlock_requested:
                # Return special response asking for unlock confirmation
                return JsonResponse({
                    'success': False, 
                    'error': 'Version ist gesperrt',
                    'requires_unlock': True,
                    'message': 'Diese Version ist finalisiert und gesperrt. Möchtest du sie entsperren und zurücksetzen?'
                }, status=400)
            else:
                # Unlock the version
                version.is_locked = False
                version.finalized_at = None
        
        version.status = new_status
        
        # If finalizing, lock the version
        if new_status == 'finalized':
            version.is_locked = True
            version.finalized_at = timezone.now()
        
        version.save()
        
        unlock_msg = " (Version entsperrt)" if unlock_requested else ""
        return JsonResponse({
            'success': True,
            'message': f'Status auf "{version.get_status_display()}" geändert{unlock_msg}',
            'status': version.status,
            'status_display': version.get_status_display(),
            'is_locked': version.is_locked,
            'can_proceed': version.can_proceed_to_writing()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def save_feedback(request, project_id, version_id):
    """Save feedback for a version (project-level and/or chapter-level)"""
    project = get_object_or_404(BookProjects, id=project_id)
    version = get_object_or_404(OutlineVersion, id=version_id, project=project)
    
    try:
        data = json.loads(request.body)
        
        # Update project-level feedback
        if 'project_feedback' in data:
            version.project_feedback = data['project_feedback']
        
        # Update chapter-level feedback
        if 'chapter_feedback' in data:
            # Merge with existing chapter feedback
            existing = version.chapter_feedback or {}
            existing.update(data['chapter_feedback'])
            version.chapter_feedback = existing
        
        version.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Feedback gespeichert',
            'project_feedback': version.project_feedback,
            'chapter_feedback': version.chapter_feedback
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def apply_feedback_revision(request, project_id, version_id):
    """Apply AI revision based on feedback to chapters"""
    project = get_object_or_404(BookProjects, id=project_id)
    version = get_object_or_404(OutlineVersion, id=version_id, project=project)
    
    try:
        data = json.loads(request.body)
        chapter_number = data.get('chapter_number')  # None = all chapters
        
        # Get project context
        project_context = {
            'title': project.title,
            'genre': project.genre,
            'target_audience': project.target_audience,
            'style': project.style,
            'project_feedback': version.project_feedback or '',
        }
        
        # Get chapters to revise
        chapters_snapshot = version.chapters_snapshot or []
        revised_chapters = []
        
        for ch in chapters_snapshot:
            ch_num = str(ch.get('number', ch.get('chapter_number', 0)))
            ch_feedback = (version.chapter_feedback or {}).get(ch_num, '')
            
            # Skip if specific chapter requested and this isn't it
            if chapter_number and str(chapter_number) != ch_num:
                revised_chapters.append(ch)
                continue
            
            # Skip if no feedback for this chapter and no project feedback
            if not ch_feedback and not version.project_feedback:
                revised_chapters.append(ch)
                continue
            
            # Prepare revision prompt
            revision_prompt = f"""Überarbeite den folgenden Kapitelentwurf basierend auf dem Feedback.

PROJEKT: {project_context['title']}
GENRE: {project_context['genre']}

KAPITEL {ch_num}: {ch.get('title', 'Unbenannt')}

AKTUELLER INHALT:
Beat/Phase: {ch.get('beat', '')}
Emotionaler Bogen: {ch.get('emotional_arc', '')}
Handlung: {ch.get('outline', '')}

PROJEKT-FEEDBACK:
{version.project_feedback or 'Kein allgemeines Feedback'}

KAPITEL-FEEDBACK:
{ch_feedback or 'Kein spezifisches Feedback'}

Bitte überarbeite den Kapitelinhalt und berücksichtige das Feedback. 
Gib die überarbeitete Version im gleichen Format zurück."""

            # Try to use AI for revision
            try:
                from apps.bfagent.services.llm_client import generate_text
                
                revised_content = generate_text(
                    prompt=revision_prompt,
                    max_tokens=2000,
                    temperature=0.7
                )
                
                # Parse response and update chapter
                ch['outline'] = revised_content.get('outline', ch.get('outline', ''))
                ch['revised'] = True
                ch['revision_note'] = f"Überarbeitet basierend auf Feedback"
                
            except Exception as ai_error:
                # Fallback: Mark for manual revision
                ch['revision_note'] = f"AI-Revision fehlgeschlagen: {str(ai_error)[:100]}. Manuelle Überarbeitung empfohlen."
                ch['needs_manual_revision'] = True
            
            revised_chapters.append(ch)
        
        # Save revised chapters
        version.chapters_snapshot = revised_chapters
        version.save()
        
        # Count revisions
        revision_count = sum(1 for ch in revised_chapters if ch.get('revised') or ch.get('needs_manual_revision'))
        
        return JsonResponse({
            'success': True,
            'message': f'{revision_count} Kapitel überarbeitet',
            'revised_chapters': revised_chapters,
            'revision_count': revision_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def convert_framework(request, project_id):
    """Convert outline chapters from one framework to another with optional AI assistance"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        source_framework = data.get('source_framework', 'save_the_cat')
        target_framework = data.get('target_framework', 'heros_journey')
        chapters_data = data.get('chapters', [])
        use_ai = data.get('use_ai', False)
        
        # Framework beat mappings
        FRAMEWORK_BEATS = {
            'save_the_cat': [
                {'name': 'Opening Image', 'act': 1, 'position': 0.0},
                {'name': 'Theme Stated', 'act': 1, 'position': 0.05},
                {'name': 'Set-Up', 'act': 1, 'position': 0.08},
                {'name': 'Catalyst', 'act': 1, 'position': 0.10},
                {'name': 'Debate', 'act': 1, 'position': 0.17},
                {'name': 'Break into Two', 'act': 2, 'position': 0.25},
                {'name': 'B Story', 'act': 2, 'position': 0.30},
                {'name': 'Fun and Games', 'act': 2, 'position': 0.40},
                {'name': 'Midpoint', 'act': 2, 'position': 0.50},
                {'name': 'Bad Guys Close In', 'act': 2, 'position': 0.60},
                {'name': 'All Is Lost', 'act': 2, 'position': 0.75},
                {'name': 'Dark Night of Soul', 'act': 2, 'position': 0.80},
                {'name': 'Break into Three', 'act': 3, 'position': 0.83},
                {'name': 'Finale', 'act': 3, 'position': 0.92},
                {'name': 'Final Image', 'act': 3, 'position': 1.0},
            ],
            'heros_journey': [
                {'name': 'Ordinary World', 'act': 1, 'position': 0.0},
                {'name': 'Call to Adventure', 'act': 1, 'position': 0.08},
                {'name': 'Refusal of the Call', 'act': 1, 'position': 0.12},
                {'name': 'Meeting the Mentor', 'act': 1, 'position': 0.17},
                {'name': 'Crossing the Threshold', 'act': 2, 'position': 0.25},
                {'name': 'Tests, Allies, Enemies', 'act': 2, 'position': 0.35},
                {'name': 'Approach to Inmost Cave', 'act': 2, 'position': 0.50},
                {'name': 'Ordeal', 'act': 2, 'position': 0.55},
                {'name': 'Reward', 'act': 2, 'position': 0.65},
                {'name': 'The Road Back', 'act': 3, 'position': 0.75},
                {'name': 'Resurrection', 'act': 3, 'position': 0.90},
                {'name': 'Return with Elixir', 'act': 3, 'position': 1.0},
            ],
            'three_act': [
                {'name': 'Hook', 'act': 1, 'position': 0.0},
                {'name': 'Introduction', 'act': 1, 'position': 0.05},
                {'name': 'Inciting Incident', 'act': 1, 'position': 0.10},
                {'name': 'First Plot Point', 'act': 1, 'position': 0.25},
                {'name': 'Rising Action', 'act': 2, 'position': 0.30},
                {'name': 'Midpoint', 'act': 2, 'position': 0.50},
                {'name': 'Escalation', 'act': 2, 'position': 0.60},
                {'name': 'Crisis', 'act': 2, 'position': 0.75},
                {'name': 'Climax Build', 'act': 3, 'position': 0.80},
                {'name': 'Climax', 'act': 3, 'position': 0.85},
                {'name': 'Falling Action', 'act': 3, 'position': 0.92},
                {'name': 'Resolution', 'act': 3, 'position': 1.0},
            ]
        }
        
        target_beats = FRAMEWORK_BEATS.get(target_framework, FRAMEWORK_BEATS['save_the_cat'])
        
        converted_chapters = []
        total_chapters = len(chapters_data)
        
        for idx, ch in enumerate(chapters_data):
            # Calculate position (0.0 to 1.0)
            position = idx / max(total_chapters - 1, 1) if total_chapters > 1 else 0
            
            # Find closest beat in target framework
            closest_beat = target_beats[0]
            min_distance = abs(position - closest_beat['position'])
            
            for beat in target_beats:
                distance = abs(position - beat['position'])
                if distance < min_distance:
                    min_distance = distance
                    closest_beat = beat
            
            converted_chapter = {
                'id': ch.get('id'),
                'number': ch.get('number', idx + 1),
                'title': ch.get('title', f'Kapitel {idx + 1}'),
                'beat': closest_beat['name'],
                'act': closest_beat['act'],
                'outline': ch.get('outline', ''),
                'emotional_arc': ch.get('emotional_arc', ''),
                'target_words': ch.get('target_words', 2000),
            }
            
            converted_chapters.append(converted_chapter)
        
        # Update project metadata with new framework
        if hasattr(project, 'metadata'):
            try:
                meta = json.loads(project.metadata) if isinstance(project.metadata, str) else (project.metadata or {})
            except (json.JSONDecodeError, TypeError):
                meta = {}
            meta['outline_framework'] = target_framework
            meta['framework_converted_from'] = source_framework
            project.metadata = json.dumps(meta)
            project.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Framework von {source_framework} zu {target_framework} konvertiert',
            'chapters': converted_chapters,
            'framework': target_framework
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# AI GENERATION API - Generate content for outline fields
# =============================================================================

@require_http_methods(["POST"])
def generate_ai_content(request, project_id):
    """
    Generate AI content for outline fields.
    
    Supports:
    - outline: Generate chapter/section outline
    - beat: Suggest appropriate beat for position
    - emotional_arc: Generate emotional arc description
    - title: Generate chapter/section title
    - full_chapter: Generate complete chapter outline from beat
    """
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        field_type = data.get('field_type', 'outline')  # outline, beat, emotional_arc, title, full_chapter, enrich_outline
        chapter_number = data.get('chapter_number', 1)
        framework_slug = data.get('framework', 'save_the_cat')
        beat_name = data.get('beat_name', '') or data.get('beat', '')
        existing_content = data.get('existing_content', '')
        custom_prompt = data.get('custom_prompt', '')  # Additional user instructions
        context_data = data.get('context', {})
        beat_llm_prompt = data.get('beat_llm_prompt', '')  # Framework-specific beat prompt
        
        # Get content type from project
        content_type = 'novel'
        llm_id = None
        if project.genre_settings:
            try:
                settings = json.loads(project.genre_settings)
                content_type = settings.get('content_type', 'novel')
                llm_id = settings.get('llm_id')
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Try to get framework and beat from DB
        db_framework = None
        db_beat = None
        try:
            db_content_type = ContentType.objects.filter(slug=content_type, is_active=True).first()
            if db_content_type:
                db_framework = StructureFramework.objects.filter(
                    content_type=db_content_type,
                    slug=framework_slug,
                    is_active=True
                ).first()
                if db_framework and beat_name:
                    db_beat = FrameworkBeat.objects.filter(
                        framework=db_framework,
                        name=beat_name
                    ).first() or FrameworkBeat.objects.filter(
                        framework=db_framework,
                        name_de=beat_name
                    ).first()
        except Exception:
            pass
        
        # Build prompt based on field type and DB data
        # For scientific content, use ScientificWritingHandler
        if content_type == 'scientific':
            from .handlers.scientific_writing_handler import generate_scientific_section
            
            # Map beat_name to section_type
            section_type_map = {
                'Abstract': 'abstract',
                'Introduction': 'introduction',
                'Einleitung': 'introduction',
                'Research Question': 'introduction',
                'Forschungsfrage': 'introduction',
                'Literature Review': 'literature_review',
                'Forschungsstand': 'literature_review',
                'Methods': 'methodology',
                'Methodik': 'methodology',
                'Results': 'results',
                'Ergebnisse': 'results',
                'Discussion': 'discussion',
                'Diskussion': 'discussion',
                'Conclusion': 'conclusion',
                'Fazit': 'conclusion',
            }
            section_type = section_type_map.get(beat_name, 'introduction')
            
            result = generate_scientific_section(
                project_id=project_id,
                section_id=chapter_number,
                context_data={
                    'title': project.title,
                    'research_field': context_data.get('field', project.genre or ''),
                    'paper_type': 'empirical',
                    'research_question': context_data.get('research_question', ''),
                    'section_number': chapter_number,
                    'section_title': beat_name,
                    'section_type': section_type,
                    'section_outline': existing_content,
                    'target_word_count': 1500,
                    'citation_style': 'APA',
                }
            )
            
            if result.get('success'):
                return JsonResponse({
                    'success': True,
                    'content': result['content'],
                    'model': result.get('model_used', 'scientific_handler'),
                    'field_type': field_type,
                    'word_count': result.get('word_count', 0)
                })
        
        system_prompt, user_prompt = _build_ai_prompt(
            field_type=field_type,
            project=project,
            content_type=content_type,
            chapter_number=chapter_number,
            beat_name=beat_name,
            existing_content=existing_content,
            custom_prompt=custom_prompt,
            context_data=context_data,
            db_framework=db_framework,
            db_beat=db_beat
        )
        
        # Use OutlineGenerationHandler for better context integration
        from .handlers import OutlineGenerationHandler, OutlineContext
        
        # Map field types to handler methods
        field_type_map = {
            'outline': 'chapter_outline',
            'enrich_outline': 'enrich_outline',
            'complete_outline': 'complete_outline',  # Full detailed outline generation
            'title': 'chapter_title',
            'emotional_arc': 'emotional_arc',
        }
        
        outline_ctx = OutlineContext.from_project(project_id)
        handler = OutlineGenerationHandler(llm_id=llm_id)
        
        if handler.get_llm() and field_type in field_type_map:
            # Use OutlineHandler for better context
            result = handler.generate_field(
                context=outline_ctx,
                field_type=field_type_map[field_type],
                chapter_number=chapter_number,
                beat_name=beat_name,
                existing_content=existing_content,
                beat_llm_prompt=beat_llm_prompt
            )
            
            if result.get('success'):
                return JsonResponse({
                    'success': True,
                    'content': result['content'],
                    'model': result.get('llm_used', 'unknown'),
                    'field_type': field_type,
                    'latency_ms': result.get('latency_ms')
                })
        
        # Fallback to WritingLLMHandler or mock
        from .handlers.writing_llm_handler import WritingLLMHandler, LLMResponse
        writing_handler = WritingLLMHandler(llm_id=llm_id)
        
        if writing_handler.llm:
            if writing_handler.llm.provider.lower() == 'openai':
                response = writing_handler._call_openai(system_prompt, user_prompt)
            elif writing_handler.llm.provider.lower() == 'anthropic':
                response = writing_handler._call_anthropic(system_prompt, user_prompt)
            else:
                response = _generate_mock_content(field_type, project, beat_name, chapter_number, content_type)
        else:
            response = _generate_mock_content(field_type, project, beat_name, chapter_number, content_type)
        
        if response.success:
            return JsonResponse({
                'success': True,
                'content': response.content.get('generated_text', ''),
                'tokens_used': response.tokens_used,
                'model': response.model_used,
                'field_type': field_type
            })
        else:
            return JsonResponse({
                'success': False,
                'error': response.error or 'Generation failed'
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _build_ai_prompt(field_type, project, content_type, chapter_number, beat_name, 
                     existing_content, custom_prompt, context_data, db_framework, db_beat):
    """Build system and user prompts for AI generation"""
    
    # Base system prompt
    content_type_prompts = {
        'novel': 'Du bist ein erfahrener Romanautor und Schreibcoach. Antworte auf Deutsch.',
        'essay': 'Du bist ein erfahrener Essayist und Rhetorik-Experte. Antworte auf Deutsch.',
        'scientific': 'Du bist ein wissenschaftlicher Schreibcoach. Antworte auf Deutsch und achte auf akademische Standards.',
    }
    
    system_prompt = content_type_prompts.get(content_type, content_type_prompts['novel'])
    
    # Add framework-specific system prompt if available
    if db_framework and db_framework.llm_system_prompt:
        system_prompt += f"\n\n{db_framework.llm_system_prompt}"
    
    # Add custom user instructions to system prompt
    if custom_prompt:
        system_prompt += f"\n\nZUSÄTZLICHE ANWEISUNGEN VOM BENUTZER:\n{custom_prompt}"
    
    # Build user prompt based on field type
    project_context = f"""
Projekt: "{project.title}"
Genre: {project.genre}
Beschreibung: {project.description or 'Keine Beschreibung'}
Zielgruppe: {project.target_audience or 'Allgemein'}
Prämisse: {project.story_premise or 'Noch nicht definiert'}
"""

    if field_type == 'outline':
        # Use beat-specific prompt if available
        if db_beat and db_beat.llm_prompt_template:
            user_prompt = db_beat.llm_prompt_template.format(
                title=project.title,
                genre=project.genre,
                chapter_number=chapter_number,
                beat_name=beat_name,
                context=project_context,
                existing=existing_content,
                **context_data
            )
        else:
            user_prompt = f"""{project_context}
Schreibe einen detaillierten Outline für Kapitel {chapter_number}.
Beat/Abschnitt: {beat_name or 'Nicht spezifiziert'}

Der Outline sollte enthalten:
- Was passiert in diesem Kapitel
- Wichtige Ereignisse und Wendepunkte
- Charakterentwicklung
- Emotionale Höhepunkte

{f'Bisheriger Inhalt zum Erweitern: {existing_content}' if existing_content else ''}

Antworte nur mit dem Outline-Text (ca. 150-300 Wörter)."""

    elif field_type == 'beat':
        user_prompt = f"""{project_context}
Kapitel {chapter_number} im Story-Framework.

Schlage einen passenden Beat/Abschnitt vor basierend auf der Position im Buch.
Bei einem {db_framework.name if db_framework else 'Standard'}-Framework.

Antworte nur mit dem Beat-Namen."""

    elif field_type == 'emotional_arc':
        user_prompt = f"""{project_context}
Kapitel {chapter_number}: {beat_name or 'Unbekannter Beat'}

Beschreibe den emotionalen Bogen dieses Kapitels.
Format: "Emotion A → Emotion B → Emotion C"

Beispiele:
- "Hoffnung → Zweifel → Entschlossenheit"
- "Spannung → Überraschung → Erleichterung"

Antworte nur mit dem emotionalen Bogen."""

    elif field_type == 'title':
        user_prompt = f"""{project_context}
Kapitel {chapter_number}
Beat: {beat_name or 'Nicht spezifiziert'}
Outline: {existing_content or 'Noch kein Outline'}

Schlage einen passenden, fesselnden Kapiteltitel vor.
Der Titel sollte neugierig machen ohne zu spoilern.

Antworte nur mit dem Titel (ohne "Kapitel X:")."""

    elif field_type == 'full_chapter':
        user_prompt = f"""{project_context}
Erstelle einen vollständigen Kapitel-Outline für Kapitel {chapter_number}.

Beat: {beat_name}
Position: {db_beat.position if db_beat else 'Unbekannt'}

{db_beat.description_de or db_beat.description if db_beat else ''}

Liefere:
1. Einen passenden Kapiteltitel
2. Einen detaillierten Outline (200-400 Wörter)
3. Den emotionalen Bogen

Format:
TITEL: [Kapiteltitel]
OUTLINE: [Detaillierter Outline]
EMOTION: [Emotionaler Bogen]"""

    else:
        user_prompt = f"{project_context}\nGeneriere Inhalt für: {field_type}"
    
    return system_prompt, user_prompt


def _generate_mock_content(field_type, project, beat_name, chapter_number, content_type):
    """Generate mock content when no LLM is available - content-type aware"""
    from .handlers.writing_llm_handler import LLMResponse
    
    # Content-type specific mock content
    if content_type == 'scientific':
        # Scientific paper mock content based on beat/section
        section_outlines = {
            'Abstract': """## Abstract

Diese Studie untersucht [Forschungsthema]. Mittels [Methodik] wurden [Stichprobe] analysiert. Die Ergebnisse zeigen [Hauptergebnis]. Diese Erkenntnisse haben Implikationen für [Praxisfeld].

**Schlüsselwörter:** [Keyword 1], [Keyword 2], [Keyword 3]

*[Mock-Inhalt - Aktiviere LLM für echte KI-Generierung]*""",
            'Introduction': """## 1. Einleitung

### 1.1 Problemhintergrund
Das Thema [Forschungsthema] gewinnt in der aktuellen Forschung zunehmend an Bedeutung (vgl. Autor, 2024).

### 1.2 Forschungslücke
Trotz umfangreicher Forschung besteht weiterhin Forschungsbedarf bezüglich [Lücke].

### 1.3 Forschungsfrage und Zielsetzung
Daraus ergibt sich folgende Forschungsfrage: [RQ]

### 1.4 Aufbau der Arbeit
Die Arbeit gliedert sich in [X] Abschnitte...

*[Mock-Inhalt - Aktiviere LLM für echte KI-Generierung]*""",
            'Methods': """## 3. Methodik

### 3.1 Forschungsdesign
Die vorliegende Studie verwendet ein [quantitatives/qualitatives] Forschungsdesign.

### 3.2 Stichprobe
Die Stichprobe umfasst N = [Anzahl] Teilnehmer.

### 3.3 Datenerhebung
Die Datenerhebung erfolgte mittels [Instrument].

### 3.4 Datenanalyse
Zur Analyse wurden [statistische Verfahren] eingesetzt.

*[Mock-Inhalt - Aktiviere LLM für echte KI-Generierung]*""",
            'Results': """## 4. Ergebnisse

### 4.1 Deskriptive Statistik
Die deskriptive Analyse zeigt [Befunde].

### 4.2 Hypothesenprüfung
H1 konnte [bestätigt/nicht bestätigt] werden (p < .05).

### 4.3 Weitere Analysen
Zusätzliche Analysen ergaben [Erkenntnisse].

*[Mock-Inhalt - Aktiviere LLM für echte KI-Generierung]*""",
            'Discussion': """## 5. Diskussion

### 5.1 Interpretation der Ergebnisse
Die Ergebnisse legen nahe, dass [Interpretation].

### 5.2 Einordnung in den Forschungsstand
Diese Befunde stehen im Einklang mit [Autor, Jahr].

### 5.3 Limitationen
Die Studie unterliegt folgenden Einschränkungen: [Limitationen].

### 5.4 Implikationen
Für die Praxis ergeben sich folgende Handlungsempfehlungen: [Implikationen].

*[Mock-Inhalt - Aktiviere LLM für echte KI-Generierung]*""",
            'Conclusion': """## 6. Fazit

Die vorliegende Arbeit untersuchte [Forschungsfrage]. Die zentralen Erkenntnisse lassen sich wie folgt zusammenfassen:

1. [Hauptergebnis 1]
2. [Hauptergebnis 2]
3. [Hauptergebnis 3]

Zukünftige Forschung sollte [Ausblick].

*[Mock-Inhalt - Aktiviere LLM für echte KI-Generierung]*"""
        }
        
        # Find matching section or use default
        outline = section_outlines.get(beat_name, section_outlines.get('Introduction'))
        for key in section_outlines:
            if key.lower() in (beat_name or '').lower():
                outline = section_outlines[key]
                break
        
        mock_content = {
            'outline': outline,
            'beat': beat_name or 'Einleitung',
            'emotional_arc': 'Problemdarstellung → Analyse → Erkenntnis',
            'title': f'Abschnitt {chapter_number}: {beat_name or "Einleitung"}',
            'full_chapter': f"""TITEL: {beat_name or 'Einleitung'}

OUTLINE: {outline}

EMOTION: Sachlich → Analytisch → Erkenntnisgewinn"""
        }
    else:
        # Novel/Essay mock content (original)
        mock_content = {
            'outline': f"""In diesem Kapitel entwickelt sich die Handlung weiter. 
        
Der Protagonist steht vor einer wichtigen Entscheidung, die den weiteren Verlauf der Geschichte prägen wird. Spannung baut sich auf, während verborgene Wahrheiten ans Licht kommen.

**Schlüsselszenen:**
- Konfrontation mit einem Hindernis
- Enthüllung wichtiger Information
- Emotionaler Wendepunkt

*[Mock-Inhalt - Aktiviere LLM für echte KI-Generierung]*""",
            
            'beat': beat_name or 'Rising Action',
            
            'emotional_arc': 'Neugier → Spannung → Überraschung',
            
            'title': f'Kapitel {chapter_number}: Der Wendepunkt',
            
            'full_chapter': f"""TITEL: Schatten der Vergangenheit

OUTLINE: Die Szene beginnt mit einer unerwarteten Begegnung. Der Protagonist wird mit Informationen konfrontiert, die sein bisheriges Weltbild in Frage stellen. In einem emotionalen Gespräch werden alte Wunden aufgerissen und neue Allianzen geschmiedet. Das Kapitel endet mit einer Entscheidung, die keine Rückkehr mehr erlaubt.

EMOTION: Überraschung → Konfrontation → Entschlossenheit

*[Mock-Inhalt - Aktiviere LLM für echte KI-Generierung]*"""
        }
    
    return LLMResponse(
        success=True,
        content={'generated_text': mock_content.get(field_type, 'Mock content')},
        tokens_used=0,
        model_used='mock'
    )


@require_http_methods(["POST"])
def generate_full_outline(request, project_id):
    """Generate a complete outline for all chapters using AI with full project context"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        framework_slug = data.get('framework', 'save_the_cat')
        chapter_count = data.get('chapter_count', 15)
        use_ai = data.get('use_ai', True)  # Default to AI generation
        
        # Use OutlineGenerationHandler for AI generation
        from .handlers import OutlineGenerationHandler, OutlineContext
        
        # Build context from project
        outline_ctx = OutlineContext.from_project(project_id)
        outline_ctx.framework = framework_slug
        outline_ctx.chapter_count = chapter_count
        
        handler = OutlineGenerationHandler()
        
        if use_ai and handler.get_llm():
            # Generate with AI
            result = handler.generate_full_outline(outline_ctx)
            
            if result.get('success'):
                return JsonResponse({
                    'success': True,
                    'chapters': result['chapters'],
                    'framework': framework_slug,
                    'llm_used': result.get('llm_used'),
                    'latency_ms': result.get('latency_ms'),
                    'beats_from_db': False,
                    'ai_generated': True
                })
            else:
                # Fall back to DB beats if AI fails
                pass
        
        # Fallback: Use DB framework beats
        content_type = 'novel'
        if project.genre_settings:
            try:
                settings = json.loads(project.genre_settings)
                content_type = settings.get('content_type', 'novel')
            except (json.JSONDecodeError, TypeError):
                pass
        
        chapters = []
        db_content_type = ContentType.objects.filter(slug=content_type, is_active=True).first()
        beats = []
        
        if db_content_type:
            db_framework = StructureFramework.objects.filter(
                content_type=db_content_type,
                slug=framework_slug,
                is_active=True
            ).prefetch_related('beats').first()
            
            if db_framework:
                beats = list(db_framework.beats.all().order_by('sort_order'))
        
        if beats:
            for i, beat in enumerate(beats[:chapter_count]):
                chapters.append({
                    'number': i + 1,
                    'title': f'Kapitel {i + 1}',
                    'beat': beat.name_de or beat.name,
                    'act': beat.part,
                    'outline': beat.description_de or beat.description or '',
                    'emotional_arc': '',
                    'target_words': int(project.target_word_count / chapter_count) if project.target_word_count else 2000,
                })
        else:
            for i in range(chapter_count):
                act = 1 if i < chapter_count * 0.25 else (2 if i < chapter_count * 0.75 else 3)
                chapters.append({
                    'number': i + 1,
                    'title': f'Kapitel {i + 1}',
                    'beat': '',
                    'act': act,
                    'outline': '',
                    'emotional_arc': '',
                    'target_words': int(project.target_word_count / chapter_count) if project.target_word_count else 2000,
                })
        
        return JsonResponse({
            'success': True,
            'chapters': chapters,
            'framework': framework_slug,
            'beats_from_db': len(beats) > 0,
            'ai_generated': False
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# PHASE 1: PROJECT WIZARD
# =============================================================================

def project_wizard(request):
    """Create a new book project with guided wizard"""
    # Check if coming from idea session
    idea_session_id = request.GET.get('idea_session') or request.POST.get('idea_session')
    idea_session = None
    idea_responses = {}
    
    if idea_session_id:
        from .models import IdeaSession, IdeaResponse
        try:
            idea_session = IdeaSession.objects.get(pk=idea_session_id, user=request.user)
            # Load all accepted responses as context
            for resp in idea_session.responses.filter(is_accepted=True).select_related('step'):
                idea_responses[resp.step.name] = resp.content
        except IdeaSession.DoesNotExist:
            pass
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        genre = request.POST.get('genre', '')
        description = request.POST.get('description', '')
        target_audience = request.POST.get('target_audience', '')
        content_type = request.POST.get('content_type', 'novel')
        field = request.POST.get('field', '')  # For scientific papers
        llm_id = request.POST.get('llm_id', '')
        author_id = request.POST.get('author_id', '')
        writing_style_id = request.POST.get('writing_style_id', '')
        target_word_count = int(request.POST.get('target_word_count', 50000))
        
        if not title:
            messages.error(request, 'Titel ist erforderlich')
            return redirect('writing_hub:project_wizard')
        
        # Get or create a default book type
        from apps.bfagent.models import BookTypes
        default_book_type = BookTypes.objects.first()
        
        # Store content_type, author/style, and idea_session in genre_settings as JSON
        project_settings = {
            'content_type': content_type,
            'llm_id': int(llm_id) if llm_id else None,
            'author_id': author_id if author_id else None,
            'writing_style_id': writing_style_id if writing_style_id else None,
            'field': field if content_type == 'scientific' else None,
            'idea_session_id': int(idea_session_id) if idea_session_id else None,
        }
        
        # Build description from idea responses if available
        if idea_responses and not description:
            desc_parts = []
            if 'premise' in idea_responses:
                desc_parts.append(idea_responses['premise'])
            elif 'core_conflict' in idea_responses:
                desc_parts.append(idea_responses['core_conflict'])
            elif 'moral' in idea_responses:
                desc_parts.append(f"Moral: {idea_responses['moral']}")
            description = ' '.join(desc_parts)[:500] if desc_parts else ''
        
        project = BookProjects.objects.create(
            title=title,
            genre=genre if content_type == 'novel' else content_type,
            description=description,
            target_word_count=target_word_count,
            target_audience=target_audience,
            status='planning',
            content_rating='General',
            book_type=default_book_type,
            genre_settings=json.dumps(project_settings),  # Store content type config
        )
        
        # Link idea session to project
        if idea_session:
            idea_session.project = project
            idea_session.save()
        
        # Create ProjectAuthor relationship if author was selected
        if author_id:
            from .models import Author, WritingStyle, ProjectAuthor
            try:
                author = Author.objects.get(id=author_id)
                writing_style = None
                if writing_style_id:
                    writing_style = WritingStyle.objects.filter(id=writing_style_id, author=author).first()
                
                ProjectAuthor.objects.create(
                    project=project,
                    author=author,
                    writing_style=writing_style,
                    is_primary=True
                )
            except Author.DoesNotExist:
                pass
        
        messages.success(request, f'Projekt "{title}" erstellt!')
        return redirect('writing_hub:project_hub', project_id=project.id)
    
    # Get available LLMs for selection (fallback)
    available_llms = list(Llms.objects.filter(is_active=True).values('id', 'name', 'provider'))
    
    # Get available Authors with their Writing Styles
    from .models import Author, WritingStyle
    authors_with_styles = []
    for author in Author.objects.filter(is_active=True).prefetch_related('writing_styles'):
        styles = list(author.writing_styles.filter(is_active=True).values(
            'id', 'name', 'is_default', 'default_pov', 'default_tense'
        ))
        if styles:  # Only include authors with at least one style
            authors_with_styles.append({
                'id': str(author.id),
                'name': author.name,
                'genres': author.genres,
                'styles': styles
            })
    
    genres = ['Fantasy', 'Science Fiction', 'Romance', 'Thriller', 'Mystery', 
              'Horror', 'Literary Fiction', 'Young Adult', 'Non-Fiction']
    
    context = {
        'genres': genres,
        'available_llms': available_llms,
        'authors_with_styles': authors_with_styles,
        'authors_json': json.dumps(authors_with_styles, default=str),
        'idea_session': idea_session,
        'idea_responses': idea_responses,
    }
    return render(request, 'writing_hub/project_wizard.html', context)


# =============================================================================
# PROJECT HUB - Central Navigation
# =============================================================================

def project_hub(request, project_id):
    """Central hub for a book project - shows all phases and progress"""
    from apps.writing_hub.models_lektorat import LektoratsSession, LektoratsFehler
    from apps.writing_hub.models import ChapterIllustration, EditingSuggestion
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Parse content type settings from genre_settings JSON
    content_type = 'novel'  # Default
    llm_id = None
    field = None
    if project.genre_settings:
        try:
            settings = json.loads(project.genre_settings)
            content_type = settings.get('content_type', 'novel')
            llm_id = settings.get('llm_id')
            field = settings.get('field')
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Use actual model fields instead of metadata
    has_premise = bool(project.story_premise)
    has_themes = bool(project.story_themes)
    book_type_name = project.book_type.name if hasattr(project, 'book_type') and project.book_type else 'Roman'
    
    chapters = BookChapters.objects.filter(project=project)
    characters = Characters.objects.filter(project=project)
    worlds = Worlds.objects.filter(project=project)
    
    # Calculate Lektorat progress
    lektorat_sessions = LektoratsSession.objects.filter(project=project)
    lektorat_progress = 0
    lektorat_complete = False
    if lektorat_sessions.exists():
        latest_session = lektorat_sessions.first()
        if latest_session.status == 'abgeschlossen':
            lektorat_progress = 100
            lektorat_complete = True
        elif latest_session.status == 'in_bearbeitung':
            # Calculate based on module status
            modul_status = latest_session.modul_status or {}
            completed_modules = sum(1 for s in modul_status.values() if s == 'completed')
            lektorat_progress = int(completed_modules / 5 * 100) if modul_status else 20
        else:
            lektorat_progress = 0
    
    # Calculate Illustration progress
    try:
        total_chapters_count = chapters.count()
        # Count chapters that have at least one completed illustration
        chapters_with_images = ChapterIllustration.objects.filter(
            chapter__project_id=project_id,
            status='completed'
        ).values('chapter_id').distinct().count()
        
        # Also count total completed images for the project
        total_images = ChapterIllustration.objects.filter(
            chapter__project_id=project_id,
            status='completed'
        ).count()
        
        if total_chapters_count > 0:
            illustration_progress = int(chapters_with_images / total_chapters_count * 100)
        elif total_images > 0:
            # Has images but no chapters assigned - show some progress
            illustration_progress = 50
        else:
            illustration_progress = 0
            
        illustration_complete = chapters_with_images >= total_chapters_count and total_chapters_count > 0
    except Exception:
        illustration_progress = 0
        illustration_complete = False
    
    chapters_with_outline = chapters.exclude(outline__isnull=True).exclude(outline='').count()
    chapters_with_content = chapters.exclude(content__isnull=True).exclude(content='').count()
    total_chapters = chapters.count()
    total_words = sum(ch.word_count or 0 for ch in chapters)
    target_words = project.target_word_count or 50000
    
    # Calculate Editing/Redaktion progress based on suggestions
    editing_total = EditingSuggestion.objects.filter(chapter__project=project).count()
    editing_accepted = EditingSuggestion.objects.filter(chapter__project=project, status='accepted').count()
    editing_pending = EditingSuggestion.objects.filter(chapter__project=project, status='pending').count()
    editing_progress = int(editing_accepted / editing_total * 100) if editing_total > 0 else 0
    editing_complete = editing_total > 0 and editing_pending == 0
    
    # Content-type specific phase configurations
    content_type_configs = {
        'novel': {
            'type_name': 'Roman',
            'type_icon': 'bi-book',
            'phases': [
                {'id': 'planning', 'name': 'Konzept', 'icon': 'bi-lightbulb', 'description': 'Prämisse & Themen',
                 'url': f'/writing-hub/project/{project_id}/planning/', 'complete': has_premise,
                 'progress': 100 if has_premise else 0},
                {'id': 'characters', 'name': 'Charaktere', 'icon': 'bi-people', 'description': f'{characters.count()} Charaktere',
                 'url': f'/writing-hub/project/{project_id}/characters/', 'complete': characters.count() >= 2,
                 'progress': min(100, characters.count() * 25)},
                {'id': 'world', 'name': 'Weltenbau', 'icon': 'bi-globe2', 'description': f'{worlds.count()} Welten',
                 'url': f'/writing-hub/project/{project_id}/world/', 'complete': worlds.count() >= 1,
                 'progress': 100 if worlds.count() >= 1 else 0},
                {'id': 'outline', 'name': 'Outline', 'icon': 'bi-list-ol', 'description': f'{chapters_with_outline}/{total_chapters} Kapitel',
                 'url': f'/writing-hub/outline/{project_id}/', 'complete': total_chapters > 0 and chapters_with_outline == total_chapters,
                 'progress': int(chapters_with_outline / total_chapters * 100) if total_chapters > 0 else 0},
                {'id': 'writing', 'name': 'Schreiben', 'icon': 'bi-pencil', 'description': f'{chapters_with_content}/{total_chapters} geschrieben',
                 'url': f'/writing-hub/project/{project_id}/write/', 'complete': total_chapters > 0 and chapters_with_content == total_chapters,
                 'progress': int(chapters_with_content / total_chapters * 100) if total_chapters > 0 else 0},
                {'id': 'editing', 'name': 'Redaktion', 'icon': 'bi-pencil-square', 
                 'description': f'{editing_accepted}/{editing_total} angenommen' if editing_total > 0 else 'Textverbesserungen',
                 'url': f'/writing-hub/project/{project_id}/editing/', 'complete': editing_complete, 
                 'progress': editing_progress},
                {'id': 'lektorat', 'name': 'Lektorat', 'icon': 'bi-check2-all', 
                 'description': f'{lektorat_progress}% geprüft' if lektorat_progress > 0 else 'Konsistenzprüfung',
                 'url': f'/writing-hub/project/{project_id}/lektorat/', 'complete': lektorat_complete, 'progress': lektorat_progress},
                {'id': 'review', 'name': 'Review', 'icon': 'bi-check2-circle', 'description': 'Qualitätsprüfung',
                 'url': f'/writing-hub/project/{project_id}/review/', 'complete': False, 'progress': 0},
                {'id': 'illustration', 'name': 'Illustration', 'icon': 'bi-images', 
                 'description': f'{chapters_with_images}/{total_chapters_count} Kapitel' if total_chapters_count > 0 else 'Bilder generieren',
                 'url': f'/writing-hub/project/{project_id}/illustration/', 'complete': illustration_complete, 'progress': illustration_progress},
                {'id': 'publishing', 'name': 'Publishing', 'icon': 'bi-bookmark-star', 'description': 'Metadaten & Cover',
                 'url': f'/writing-hub/project/{project_id}/publishing/', 'complete': False, 'progress': 0},
                {'id': 'export', 'name': 'Export', 'icon': 'bi-download', 'description': 'Manuskript exportieren',
                 'url': f'/writing-hub/project/{project_id}/export/', 'complete': False, 'progress': 0},
            ]
        },
        'essay': {
            'type_name': 'Essay',
            'type_icon': 'bi-file-text',
            'phases': [
                {'id': 'planning', 'name': 'These', 'icon': 'bi-lightbulb', 'description': 'Zentrale These entwickeln',
                 'url': f'/writing-hub/project/{project_id}/planning/', 'complete': has_premise,
                 'progress': 100 if has_premise else 0},
                {'id': 'outline', 'name': 'Gliederung', 'icon': 'bi-list-ol', 'description': 'Argumentstruktur',
                 'url': f'/writing-hub/outline/{project_id}/', 'complete': total_chapters > 0,
                 'progress': 100 if total_chapters > 0 else 0},
                {'id': 'writing', 'name': 'Schreiben', 'icon': 'bi-pencil', 'description': f'{chapters_with_content}/{total_chapters} Abschnitte',
                 'url': f'/writing-hub/project/{project_id}/write/', 'complete': total_chapters > 0 and chapters_with_content == total_chapters,
                 'progress': int(chapters_with_content / total_chapters * 100) if total_chapters > 0 else 0},
                {'id': 'review', 'name': 'Review', 'icon': 'bi-check2-circle', 'description': 'Argumentation prüfen',
                 'url': f'/writing-hub/project/{project_id}/review/', 'complete': False, 'progress': 0},
                {'id': 'publishing', 'name': 'Publishing', 'icon': 'bi-bookmark-star', 'description': 'Metadaten & Cover',
                 'url': f'/writing-hub/project/{project_id}/publishing/', 'complete': False, 'progress': 0},
                {'id': 'export', 'name': 'Export', 'icon': 'bi-download', 'description': 'Essay exportieren',
                 'url': f'/writing-hub/project/{project_id}/export/', 'complete': False, 'progress': 0},
            ]
        },
        'scientific': {
            'type_name': 'Wissenschaftliche Arbeit',
            'type_icon': 'bi-mortarboard',
            'phases': [
                {'id': 'planning', 'name': 'Forschungsfrage', 'icon': 'bi-question-circle', 'description': 'Hypothese & Ziele',
                 'url': f'/writing-hub/project/{project_id}/planning/', 'complete': has_premise,
                 'progress': 100 if has_premise else 0},
                {'id': 'research', 'name': 'Literatur', 'icon': 'bi-journal-text', 'description': 'Literaturrecherche',
                 'url': f'/writing-hub/project/{project_id}/planning/', 'complete': False,
                 'progress': 0},
                {'id': 'outline', 'name': 'Gliederung', 'icon': 'bi-list-ol', 'description': 'IMRaD Struktur',
                 'url': f'/writing-hub/outline/{project_id}/', 'complete': total_chapters > 0,
                 'progress': 100 if total_chapters > 0 else 0},
                {'id': 'writing', 'name': 'Schreiben', 'icon': 'bi-pencil', 'description': f'{chapters_with_content}/{total_chapters} Abschnitte',
                 'url': f'/writing-hub/project/{project_id}/write/', 'complete': total_chapters > 0 and chapters_with_content == total_chapters,
                 'progress': int(chapters_with_content / total_chapters * 100) if total_chapters > 0 else 0},
                {'id': 'citations', 'name': 'Zitation', 'icon': 'bi-quote', 'description': 'Quellenverzeichnis',
                 'url': f'/writing-hub/project/{project_id}/review/', 'complete': False, 'progress': 0},
                {'id': 'review', 'name': 'Review', 'icon': 'bi-check2-circle', 'description': 'Wissenschaftliche Prüfung',
                 'url': f'/writing-hub/project/{project_id}/review/', 'complete': False, 'progress': 0},
                {'id': 'publishing', 'name': 'Publishing', 'icon': 'bi-bookmark-star', 'description': 'Metadaten & Cover',
                 'url': f'/writing-hub/project/{project_id}/publishing/', 'complete': False, 'progress': 0},
                {'id': 'export', 'name': 'Export', 'icon': 'bi-download', 'description': 'PDF/LaTeX Export',
                 'url': f'/writing-hub/project/{project_id}/export/', 'complete': False, 'progress': 0},
            ]
        },
    }
    
    config = content_type_configs.get(content_type, content_type_configs['novel'])
    phases = config['phases']
    
    overall_progress = sum(p['progress'] for p in phases) // len(phases)
    
    context = {
        'project': project, 
        'content_type': content_type,
        'content_type_name': config['type_name'],
        'content_type_icon': config['type_icon'],
        'llm_id': llm_id,
        'field': field,
        'meta': {'book_type': book_type_name},
        'phases': phases, 'overall_progress': overall_progress,
        'total_words': total_words, 'target_words': target_words,
        'word_progress': int(total_words / target_words * 100) if target_words > 0 else 0,
        'chapter_count': total_chapters, 'character_count': characters.count(),
    }
    return render(request, 'writing_hub/project_hub.html', context)


# =============================================================================
# PHASE 2: PLANNING
# =============================================================================

def planning_editor(request, project_id):
    """Planning phase: Premise, Themes, Logline"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Get content type from project settings
    content_type = 'novel'
    if project.genre_settings:
        try:
            settings = json.loads(project.genre_settings)
            content_type = settings.get('content_type', 'novel')
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Parse themes from comma-separated string
    themes = []
    if project.story_themes:
        themes = [t.strip() for t in project.story_themes.split(',') if t.strip()]
    
    # Load idea session data if available
    idea_session = None
    idea_responses = {}
    try:
        project_settings = json.loads(project.genre_settings) if project.genre_settings else {}
        idea_session_id = project_settings.get('idea_session_id')
        if idea_session_id:
            from .models import IdeaSession
            idea_session = IdeaSession.objects.filter(pk=idea_session_id).first()
            if idea_session:
                for resp in idea_session.responses.filter(is_accepted=True).select_related('step'):
                    idea_responses[resp.step.name] = resp.content
    except (json.JSONDecodeError, Exception):
        pass
    
    # If no premise yet but we have idea responses, suggest using them
    suggested_premise = ''
    suggested_themes = []
    suggested_logline = ''
    suggested_tone = ''
    
    if idea_responses:
        # Build suggested premise from idea responses
        if 'premise' in idea_responses:
            suggested_premise = idea_responses['premise']
        elif 'core_conflict' in idea_responses:
            suggested_premise = idea_responses['core_conflict']
        elif 'moral' in idea_responses:
            suggested_premise = f"Eine Geschichte über: {idea_responses['moral']}"
        
        # Extract themes
        if 'themes' in idea_responses:
            suggested_themes = [t.strip() for t in idea_responses['themes'].split(',')]
        
        # Build logline from protagonist + conflict
        logline_parts = []
        if 'protagonist' in idea_responses:
            logline_parts.append(idea_responses['protagonist'][:100])
        if 'core_conflict' in idea_responses:
            logline_parts.append(idea_responses['core_conflict'][:150])
        if logline_parts:
            suggested_logline = ' - '.join(logline_parts)
        
        # Tone/atmosphere
        if 'tone' in idea_responses:
            suggested_tone = idea_responses['tone']
        elif 'atmosphere' in idea_responses:
            suggested_tone = idea_responses['atmosphere']
    
    # Build project context from existing project data (even without idea session)
    project_context = {}
    if project.description:
        project_context['description'] = project.description
    if project.genre:
        project_context['genre'] = project.genre
    if project.target_audience:
        project_context['target_audience'] = project.target_audience
    
    # Merge idea responses with project context (idea responses take precedence)
    all_context = {**project_context, **idea_responses}
    
    # Get assigned worlds for this project (V2 World system)
    from .models_world import World, ProjectWorld
    project_worlds = ProjectWorld.objects.filter(project=project).select_related(
        'world', 'world__world_type'
    )
    available_worlds = World.objects.filter(owner=request.user) if request.user.is_authenticated else World.objects.none()
    
    # Get illustration style templates (from writing_hub)
    from django.db.models import Q
    from .models import IllustrationStyleTemplate, IllustrationStyle
    style_templates = IllustrationStyleTemplate.objects.filter(
        Q(is_public=True) | Q(created_by=request.user)
    ).order_by('name')
    
    # Get ImageStyleProfiles from Illustration-System
    from apps.bfagent.models_illustration import ImageStyleProfile
    illustration_system_styles = ImageStyleProfile.objects.filter(
        user=request.user
    ).order_by('display_name') if request.user.is_authenticated else []
    
    # Get current project illustration style
    current_style = None
    try:
        current_style = project.illustration_style
    except IllustrationStyle.DoesNotExist:
        pass
    
    context = {
        'project': project, 
        'premise': project.story_premise or '', 
        'themes': themes,
        'logline': project.tagline or '', 
        'target_audience': project.target_audience or '', 
        'tone': project.atmosphere_tone or '',
        'content_type': content_type,
        # Idea session context
        'idea_session': idea_session,
        'idea_responses': all_context,  # Now includes project data too!
        'suggested_premise': suggested_premise or project.description,
        'suggested_themes': suggested_themes,
        'suggested_logline': suggested_logline,
        'suggested_tone': suggested_tone,
        # Extra project context
        'has_project_context': bool(project_context),
        # World Building V2
        'project_worlds': project_worlds,
        'available_worlds': available_worlds,
        # Illustration Style
        'style_templates': style_templates,
        'illustration_system_styles': illustration_system_styles,
        'current_style': current_style,
    }
    return render(request, 'writing_hub/planning_editor.html', context)


@require_http_methods(["POST"])
def save_planning(request, project_id):
    """Save planning data"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        data = json.loads(request.body)
        
        # Save to actual model fields
        project.story_premise = data.get('premise', '')
        themes = data.get('themes', [])
        project.story_themes = ', '.join(themes) if isinstance(themes, list) else themes
        project.tagline = data.get('logline', '')
        project.target_audience = data.get('target_audience', '')
        project.atmosphere_tone = data.get('tone', '')
        project.save()
        
        return JsonResponse({'success': True, 'message': 'Planung gespeichert'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_planning(request, project_id):
    """AI-generate planning elements using PlanningGenerationHandler"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        data = json.loads(request.body)
        element = data.get('element', 'premise')
        custom_context = data.get('context', {})  # From sidebar
        
        # Load full project context
        from .services import project_context_service
        ctx = project_context_service.get_context(project_id, 'planning')
        
        # Get world context from V2 World system
        from .models_world import ProjectWorld
        worlds_data = []
        for pw in ProjectWorld.objects.filter(project=project).select_related('world', 'world__world_type'):
            w = pw.world
            worlds_data.append({
                'name': w.name,
                'world_type': w.world_type.name if w.world_type else None,
                'description': w.description or '',
                'geography': w.geography or '',
                'culture': w.culture or '',
                'magic_system': w.magic_system or '',
                'technology_level': w.technology_level or '',
            })
        
        # Use the PlanningGenerationHandler
        from .handlers import PlanningGenerationHandler, PlanningContext
        
        planning_ctx = PlanningContext(
            project_id=project_id,
            title=ctx.title or project.title or '',
            genre=ctx.genre or project.genre or 'Fiction',
            description=ctx.description or project.description or custom_context.get('description', ''),
            target_audience=ctx.target_audience or project.target_audience or '',
            custom_context=custom_context,
            worlds=worlds_data  # Include world context
        )
        
        handler = PlanningGenerationHandler()
        result = handler.generate(element, planning_ctx)
        
        return JsonResponse(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def apply_style_template(request, project_id):
    """Apply an illustration style (template or profile) to a project"""
    from .models import IllustrationStyleTemplate, IllustrationStyle
    from .models_prompt_system import PromptMasterStyle
    from apps.bfagent.models_illustration import ImageStyleProfile
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        source = data.get('source')  # 'profile' or 'template'
        style_id = data.get('id')
        
        # Backward compatibility: handle old format
        if not source and data.get('template_id'):
            source = 'template'
            style_id = data.get('template_id')
        
        if not style_id:
            return JsonResponse({'success': False, 'error': 'Kein Stil ausgewählt'}, status=400)
        
        if source == 'profile':
            # Apply from ImageStyleProfile (Illustration-System)
            profile = get_object_or_404(ImageStyleProfile, id=style_id, user=request.user)
            
            # Create or update IllustrationStyle for the project
            style, created = IllustrationStyle.objects.get_or_create(project=project)
            style.style_type = profile.art_style
            style.style_name = profile.display_name
            style.base_prompt = profile.base_prompt
            style.negative_prompt = profile.negative_prompt or ''
            style.provider = profile.preferred_provider
            style.quality = profile.default_quality
            style.image_size = profile.default_resolution
            style.save()
            
            style_name = profile.display_name
            base_prompt = profile.base_prompt
            negative_prompt = profile.negative_prompt or ''
        else:
            # Apply from IllustrationStyleTemplate
            template = get_object_or_404(IllustrationStyleTemplate, id=style_id)
            template.apply_to_project(project)
            style_name = template.name
            base_prompt = template.base_prompt
            negative_prompt = template.negative_prompt or ''
        
        # IMPORTANT: Also create/update PromptMasterStyle for illustration generation
        master_style, _ = PromptMasterStyle.objects.update_or_create(
            project=project,
            defaults={
                'name': style_name,
                'preset': 'custom',
                'style_base_prompt': base_prompt,
                'master_prompt': base_prompt,
                'negative_prompt': negative_prompt,
            }
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Stil "{style_name}" wurde angewendet'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# PHASE 3: CHARACTERS
# =============================================================================

def character_editor(request, project_id):
    """Character management for a project"""
    project = get_object_or_404(BookProjects, id=project_id)
    characters = Characters.objects.filter(project=project).order_by('id')
    context = {'project': project, 'characters': characters}
    return render(request, 'writing_hub/character_editor.html', context)


def get_character(request, project_id, character_id):
    """Get character details as JSON"""
    project = get_object_or_404(BookProjects, id=project_id)
    character = get_object_or_404(Characters, id=character_id, project=project)
    return JsonResponse({
        'id': character.id,
        'name': character.name,
        'age': character.age,
        'role': character.role,
        'description': character.description or '',
        'appearance': character.appearance or '',
        'personality': character.personality or '',
        'motivation': character.motivation or '',
        'conflict': character.conflict or '',
        'background': character.background or '',
        'arc': character.arc or '',
    })


@require_http_methods(["POST"])
def save_character(request, project_id):
    """Save or update a character with all fields"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        data = json.loads(request.body)
        char_id = data.get('id')
        if char_id:
            character = get_object_or_404(Characters, id=char_id, project=project)
        else:
            character = Characters(project=project)
        
        # Basic fields
        character.name = data.get('name', 'Unbenannt')
        character.role = data.get('role', 'supporting')
        age = data.get('age')
        character.age = int(age) if age else None
        
        # All text fields
        character.description = data.get('description', '')
        character.appearance = data.get('appearance', '')
        character.personality = data.get('personality', '')
        character.motivation = data.get('motivation', '')
        character.conflict = data.get('conflict', '')
        character.background = data.get('background', '')
        character.arc = data.get('arc', '')
        
        character.save()
        return JsonResponse({'success': True, 'message': f'Charakter "{character.name}" gespeichert',
                           'character': {'id': character.id, 'name': character.name, 'role': character.role}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_character_details(request, project_id):
    """AI-generate detailed character attributes using CharacterGenerationHandler"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        data = json.loads(request.body)
        name = data.get('name', 'Unbekannt')
        role = data.get('role', 'supporting')
        
        # Load project context
        from .services import project_context_service
        ctx = project_context_service.get_context(project_id, 'characters')
        
        # Use CharacterGenerationHandler
        from .handlers import CharacterGenerationHandler, CharacterContext
        
        char_ctx = CharacterContext(
            project_id=project_id,
            title=ctx.title or project.title or '',
            genre=ctx.genre or project.genre or 'Fiction',
            premise=ctx.idea_responses.get('premise', '') or project.description or '',
            themes=ctx.idea_responses.get('themes', ''),
            target_audience=ctx.target_audience or project.target_audience or '',
        )
        
        handler = CharacterGenerationHandler()
        result = handler.generate_character_details(char_ctx, name, role)
        
        if result.get('success'):
            return JsonResponse({
                'success': True, 
                'data': result['data'],
                'llm_used': result.get('llm_used')
            })
        else:
            return JsonResponse({'success': False, 'error': result.get('error', 'Unbekannter Fehler')}, status=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def delete_character(request, project_id, character_id):
    """Delete a character"""
    project = get_object_or_404(BookProjects, id=project_id)
    character = get_object_or_404(Characters, id=character_id, project=project)
    name = character.name
    character.delete()
    return JsonResponse({'success': True, 'message': f'Charakter "{name}" gelöscht'})


@require_http_methods(["POST"])
def generate_characters(request, project_id):
    """AI-generate characters with project context using CharacterGenerationHandler"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        data = json.loads(request.body)
        count = min(data.get('count', 3), 5)
        
        # Load project context
        from .services import project_context_service
        ctx = project_context_service.get_context(project_id, 'characters')
        
        # Get existing characters
        existing = list(Characters.objects.filter(project=project).values('name', 'role'))
        
        # Use CharacterGenerationHandler
        from .handlers import CharacterGenerationHandler, CharacterContext
        
        char_ctx = CharacterContext(
            project_id=project_id,
            title=ctx.title or project.title or '',
            genre=ctx.genre or project.genre or 'Fiction',
            premise=ctx.idea_responses.get('premise', '') or project.description or '',
            themes=ctx.idea_responses.get('themes', ''),
            target_audience=ctx.target_audience or project.target_audience or '',
            existing_characters=existing,
        )
        
        handler = CharacterGenerationHandler()
        result = handler.generate_characters(char_ctx, count)
        
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': result.get('error', 'Unbekannter Fehler')}, status=500)
        
        # Create characters in database
        created = []
        for char_data in result.get('characters', []):
            char = Characters.objects.create(
                project=project,
                name=char_data.get('name', 'Unbekannt'),
                role=char_data.get('role', 'supporting'),
                description=char_data.get('description', ''),
                age=char_data.get('age', ''),
                motivation=char_data.get('motivation', ''),
            )
            created.append({'id': char.id, 'name': char.name, 'role': char.role})
        
        return JsonResponse({
            'success': True, 
            'message': f'{len(created)} Charaktere mit KI generiert', 
            'characters': created,
            'llm_used': result.get('llm_used'),
            'latency_ms': result.get('latency_ms')
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# PHASE 4: WORLD BUILDING (V2 - Redirects to new project-independent system)
# =============================================================================

def world_editor(request, project_id):
    """World building editor - redirects to new World Dashboard with project context"""
    from django.shortcuts import redirect
    # Redirect to new World Dashboard with project filter
    return redirect(f'/writing-hub/worlds/?project={project_id}')


def get_world(request, project_id, world_id):
    """Get world details as JSON"""
    project = get_object_or_404(BookProjects, id=project_id)
    world = get_object_or_404(Worlds, id=world_id, project=project)
    return JsonResponse({
        'id': world.id,
        'name': world.name,
        'world_type': world.world_type or 'primary',
        'description': world.description or '',
        'setting_details': world.setting_details or '',
        'geography': world.geography or '',
        'culture': world.culture or '',
        'technology_level': world.technology_level or '',
        'magic_system': world.magic_system or '',
        'politics': world.politics or '',
        'history': world.history or '',
        'inhabitants': world.inhabitants or '',
        'connections': world.connections or '',
    })


@require_http_methods(["POST"])
def save_world(request, project_id):
    """Save or update a world with all fields"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        data = json.loads(request.body)
        world_id = data.get('id')
        if world_id:
            world = get_object_or_404(Worlds, id=world_id, project=project)
        else:
            world = Worlds(project=project)
        
        # All fields
        world.name = data.get('name', 'Unbenannte Welt')
        world.world_type = data.get('world_type', 'primary')
        world.description = data.get('description', '')
        world.setting_details = data.get('setting_details', '')
        world.geography = data.get('geography', '')
        world.culture = data.get('culture', '')
        world.technology_level = data.get('technology_level', '')
        world.magic_system = data.get('magic_system', '')
        world.politics = data.get('politics', '')
        world.history = data.get('history', '')
        world.inhabitants = data.get('inhabitants', '')
        world.connections = data.get('connections', '')
        
        world.save()
        return JsonResponse({'success': True, 'message': f'Welt "{world.name}" gespeichert', 'world': {'id': world.id, 'name': world.name}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST", "DELETE"])
def delete_world(request, project_id, world_id):
    """Delete a world"""
    project = get_object_or_404(BookProjects, id=project_id)
    world = get_object_or_404(Worlds, id=world_id, project=project)
    try:
        name = world.name
        world.delete()
        return JsonResponse({'success': True, 'message': f'Welt "{name}" gelöscht'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_world_details(request, project_id):
    """AI-generate detailed world attributes using LLM client service"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        data = json.loads(request.body)
        name = data.get('name', 'Unbekannt')
        world_type = data.get('world_type', 'primary')
        custom_prompt = data.get('custom_prompt', '')
        genre = project.genre or 'Fantasy'
        
        # Get LLM from project settings or use default active LLM
        llm = None
        llm_id = None
        if project.genre_settings:
            try:
                settings_data = json.loads(project.genre_settings)
                llm_id = settings_data.get('llm_id')
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Get LLM configuration
        from apps.bfagent.models import Llms
        if llm_id:
            llm = Llms.objects.filter(id=llm_id, is_active=True).first()
        if not llm:
            llm = Llms.objects.filter(is_active=True).first()
        
        result_data = None
        used_llm = False
        llm_error = None
        
        if llm and llm.api_key:
            # Build prompts for LLM
            system_prompt = f"""Du bist ein kreativer Weltenbauer für {genre}-Geschichten.
Generiere detaillierte, atmosphärische Beschreibungen für eine fiktive Welt.
Antworte auf Deutsch und im JSON-Format."""
            
            if custom_prompt:
                system_prompt += f"\n\nBESONDERE ANWEISUNGEN VOM BENUTZER:\n{custom_prompt}"
            
            user_prompt = f"""Erstelle eine detaillierte Weltbeschreibung für "{name}" (Typ: {world_type}).
Projekt: {project.title}
Genre: {genre}
Beschreibung: {project.description or 'Keine'}

Antworte NUR mit einem JSON-Objekt (ohne Markdown-Code-Blöcke) mit diesen Feldern:
{{
    "description": "Kurze, atmosphärische Beschreibung der Welt (2-3 Sätze)",
    "setting_details": "Zeitliche Epoche und allgemeine Stimmung",
    "geography": "Landschaften, Klima, wichtige Orte",
    "inhabitants": "Völker, Rassen, Bewohner",
    "culture": "Traditionen, Religion, Werte",
    "politics": "Machtverhältnisse, Konflikte, Regierungsformen",
    "history": "Wichtige historische Ereignisse",
    "technology_level": "Technologiestufe der Zivilisation",
    "magic_system": "Magiesystem falls vorhanden, sonst leer"
}}"""
            
            try:
                # Use the existing LLM client service
                from apps.bfagent.services.llm_client import LlmRequest, generate_text
                
                llm_request = LlmRequest(
                    provider=llm.provider,
                    api_endpoint=llm.api_endpoint,
                    api_key=llm.api_key,
                    model=llm.llm_name,
                    system=system_prompt,
                    prompt=user_prompt,
                    temperature=llm.temperature or 0.7,
                    max_tokens=llm.max_tokens or 2000,
                )
                
                response_data = generate_text(llm_request)
                
                if response_data.get("ok"):
                    content = response_data.get("text", "")
                    
                    # Check for empty response
                    if not content or not content.strip():
                        llm_error = f"LLM returned empty response (Model: {llm.llm_name})"
                    else:
                        # Parse JSON from response
                        try:
                            # Remove markdown code blocks if present
                            if '```json' in content:
                                content = content.split('```json')[1].split('```')[0]
                            elif '```' in content:
                                content = content.split('```')[1].split('```')[0]
                            result_data = json.loads(content.strip())
                            used_llm = True
                        except json.JSONDecodeError as e:
                            llm_error = f"LLM response not valid JSON: {str(e)[:50]}"
                else:
                    llm_error = response_data.get("error", "Unknown LLM error")
            except Exception as e:
                llm_error = str(e)
        else:
            llm_error = "No active LLM with API key configured"
        
        # Fallback to templates if LLM failed
        if not result_data:
            templates = {
                'Fantasy': {
                    'description': f'{name} ist ein magisches Reich voller Geheimnisse und uralter Kräfte.',
                    'setting_details': 'Eine Welt im Zeitalter der Legenden.',
                    'geography': 'Ausgedehnte Wälder, nebelverhangene Berge und mystische Ruinen.',
                    'inhabitants': 'Menschen, Elfen, Zwerge und magische Wesen.',
                    'culture': 'Alte Traditionen werden von Generation zu Generation weitergegeben.',
                    'politics': 'Königreiche ringen um Macht und Einfluss.',
                    'history': 'Vor Jahrhunderten endete ein großer Krieg.',
                    'technology_level': 'Mittelalterlich mit magischen Elementen',
                    'magic_system': 'Magie fließt durch ley-Linien im Land.',
                },
                'Science Fiction': {
                    'description': f'{name} ist eine hochtechnologische Zivilisation am Rande der Galaxis.',
                    'setting_details': 'Das 25. Jahrhundert - Ära der interstellaren Reisen.',
                    'geography': 'Orbitale Stationen, terraformte Monde, Megacities.',
                    'inhabitants': 'Menschen, KI-Entitäten, außerirdische Spezies.',
                    'culture': 'Technologie-Verehrung und Sehnsucht nach der alten Erde.',
                    'politics': 'Konzerne und Föderationen konkurrieren um Ressourcen.',
                    'history': 'Die große Expansion nach dem Kollaps des Erdsystems.',
                    'technology_level': 'Hochentwickelt: FTL, KI, Nanotechnologie',
                    'magic_system': '',
                },
            }
            result_data = templates.get(genre, templates['Fantasy'])
        
        return JsonResponse({
            'success': True, 
            'data': result_data, 
            'used_llm': used_llm,
            'llm_name': llm.llm_name if llm else None,
            'llm_error': llm_error if not used_llm else None,
            'custom_prompt_applied': bool(custom_prompt)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_world(request, project_id):
    """AI-generate world with project context"""
    project = get_object_or_404(BookProjects, id=project_id)
    try:
        # Load project context for world generation
        from .services import project_context_service
        context = project_context_service.get_context(project_id, 'world')
        ideas = context.idea_responses
        genre = context.genre or 'Fantasy'
        
        # Build world from idea session or defaults
        world_name = f'{genre}-Welt'
        description = f'Eine {genre}-Welt voller Abenteuer.'
        magic_system = ''
        
        if ideas.get('setting'):
            description = ideas['setting'][:500]
        if ideas.get('magic'):
            magic_system = ideas['magic'][:500]
        
        world = Worlds.objects.create(
            project=project, 
            name=world_name, 
            description=description,
            magic_system=magic_system
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Welt "{world.name}" generiert', 
            'world': {'id': world.id, 'name': world.name},
            'context_used': bool(ideas)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# PHASE 5: CHAPTER WRITER
# =============================================================================

def chapter_writer(request, project_id):
    """Write chapters with AI assistance"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    characters = Characters.objects.filter(project=project)
    worlds = Worlds.objects.filter(project=project)
    
    # Get project's primary author and style
    from .models import ProjectAuthor
    project_author = ProjectAuthor.objects.filter(project=project, is_primary=True).select_related('author', 'writing_style').first()
    author_info = None
    if project_author:
        style = project_author.get_effective_style()
        author_info = {
            'author_name': project_author.author.name,
            'style_name': style.name if style else 'Standard',
            'style_id': str(style.id) if style else None,
            'llm_id': style.llm_id if style and style.llm else None,
        }
    
    # Get all active LLMs for selection dropdown (fallback)
    from apps.bfagent.models import Llms
    available_llms = Llms.objects.filter(is_active=True).order_by('provider', 'name')
    llms_data = [{'id': llm.id, 'name': llm.name, 'provider': llm.provider, 
                  'model': llm.llm_name} for llm in available_llms]
    
    selected_chapter_id = request.GET.get('chapter')
    selected_chapter = None
    if selected_chapter_id:
        selected_chapter = chapters.filter(id=selected_chapter_id).first()
    elif chapters.exists():
        selected_chapter = chapters.first()
    
    chapters_data = [{'id': ch.id, 'number': ch.chapter_number, 'title': ch.title, 'outline': ch.outline or '',
                      'content': ch.content or '', 'word_count': ch.word_count or 0, 'target_words': ch.target_word_count or 2000,
                      'status': 'complete' if ch.content else ('outlined' if ch.outline else 'empty')} for ch in chapters]
    
    context = {'project': project, 'chapters': chapters, 'chapters_json': json.dumps(chapters_data),
               'selected_chapter': selected_chapter, 'characters': characters, 'worlds': worlds,
               'available_llms': available_llms, 'llms_json': json.dumps(llms_data),
               'project_author': project_author, 'author_info': author_info,
               'author_info_json': json.dumps(author_info) if author_info else 'null'}
    return render(request, 'writing_hub/chapter_writer.html', context)


@require_http_methods(["POST"])
def save_chapter_content(request, project_id, chapter_id):
    """Save chapter content"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    try:
        data = json.loads(request.body)
        content = data.get('content', '')
        chapter.content = content
        chapter.word_count = len(content.split()) if content else 0
        chapter.save()
        return JsonResponse({'success': True, 'message': f'Kapitel {chapter.chapter_number} gespeichert', 'word_count': chapter.word_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_chapter_content(request, project_id, chapter_id):
    """AI-generate chapter content using ChapterWriterHandler with full context"""
    print(f"[DEBUG] generate_chapter_content called for project={project_id}, chapter={chapter_id}")
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    try:
        data = json.loads(request.body) if request.body else {}
        instruction = data.get('instruction', '')  # Optional refinement instruction
        test_mode = data.get('test', False)  # Quick test mode
        
        # Quick test mode - return immediately without LLM
        if test_mode:
            test_content = f"# Test Kapitel {chapter.chapter_number}\n\nDies ist ein Test-Inhalt für Kapitel '{chapter.title}'.\n\nDer Test war erfolgreich!"
            chapter.content = test_content
            chapter.word_count = len(test_content.split())
            chapter.save()
            return JsonResponse({
                'success': True,
                'message': f'Test erfolgreich ({chapter.word_count} Wörter)',
                'content': test_content,
                'word_count': chapter.word_count,
                'llm_used': 'test-mode'
            })
        
        from .handlers import ChapterWriterHandler, ChapterContext
        
        # Get selected LLM ID from request
        llm_id = data.get('llm_id')
        if llm_id:
            try:
                llm_id = int(llm_id)
            except (ValueError, TypeError):
                llm_id = None
        
        # Build context from chapter with all related data
        context = ChapterContext.from_chapter(project_id, chapter_id)
        handler = ChapterWriterHandler(llm_id=llm_id)
        
        if handler.get_llm():
            if instruction and context.existing_content:
                # Refine existing content
                result = handler.refine_chapter(context, instruction)
            elif context.existing_content:
                # Continue incomplete chapter
                result = handler.continue_chapter(context)
            else:
                # Write new chapter
                result = handler.write_chapter(context)
            
            if result.get('success'):
                chapter.content = result['content']
                chapter.word_count = result['word_count']
                chapter.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Kapitel generiert ({result["word_count"]} Wörter)',
                    'content': result['content'],
                    'word_count': result['word_count'],
                    'llm_used': result.get('llm_used'),
                    'latency_ms': result.get('latency_ms')
                })
            else:
                return JsonResponse({'success': False, 'error': result.get('error')}, status=500)
        
        # Fallback: Mock content
        outline = chapter.outline or 'Die Geschichte entwickelt sich weiter.'
        content = f"# Kapitel {chapter.chapter_number}: {chapter.title}\n\n{outline}\n\n---\n\n[Kein aktives LLM. Bitte im Control Center ein LLM aktivieren.]\n\n*Platzhalter-Kapitel*"
        word_count = len(content.split())
        chapter.content = content
        chapter.word_count = word_count
        chapter.save()
        return JsonResponse({'success': True, 'message': f'Kapitel erstellt (Mock)', 'content': content, 'word_count': word_count, 'llm_used': 'mock'})
        
    except Exception as e:
        import traceback
        import sys
        exc_type, exc_value, exc_tb = sys.exc_info()
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        print("".join(tb_lines))
        # Include more detail in the error response
        error_detail = f"{exc_type.__name__}: {str(e)}"
        return JsonResponse({'success': False, 'error': error_detail}, status=500)


@require_http_methods(["POST"])
def generate_all_chapters(request, project_id):
    """AI-generate content for all chapters at once"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        from .handlers import ChapterWriterHandler
        
        handler = ChapterWriterHandler()
        
        if not handler.get_llm():
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM konfiguriert.'}, status=400)
        
        result = handler.write_all_chapters(project_id)
        
        return JsonResponse({
            'success': result['success'],
            'chapters_written': result['chapters_written'],
            'total_words': result['total_words'],
            'errors': result.get('errors', []),
            'chapters': result.get('chapters', [])
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# PHASE 6: REVIEW
# =============================================================================

def review_dashboard(request, project_id):
    """Review dashboard with feedback management"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    from .models import ChapterFeedback, ProjectFeedback
    
    # Get chapter feedback stats
    chapters_data = []
    for ch in chapters:
        open_count = ChapterFeedback.objects.filter(chapter=ch, status='open').count()
        resolved_count = ChapterFeedback.objects.filter(chapter=ch, status='resolved').count()
        chapters_data.append({
            'chapter': ch,
            'open': open_count,
            'resolved': resolved_count,
            'total': open_count + resolved_count
        })
    
    total_open = sum(c['open'] for c in chapters_data)
    total_resolved = sum(c['resolved'] for c in chapters_data)
    
    # Get project-level feedback
    project_feedbacks = ProjectFeedback.objects.filter(project=project).order_by('-created_at')
    project_open = project_feedbacks.filter(status='open').count()
    project_resolved = project_feedbacks.filter(status='resolved').count()
    
    context = {
        'project': project,
        'chapters': chapters,
        'chapters_data': chapters_data,
        'total_open': total_open,
        'total_resolved': total_resolved,
        'project_feedbacks': project_feedbacks,
        'project_open': project_open,
        'project_resolved': project_resolved,
        'feedback_scopes': ProjectFeedback.FeedbackScope.choices,
    }
    return render(request, 'writing_hub/review_dashboard.html', context)


def review_chapter(request, project_id, chapter_id):
    """Review a specific chapter with feedback"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    from .models import ChapterFeedback
    
    feedbacks = ChapterFeedback.objects.filter(chapter=chapter).order_by('-created_at')
    
    context = {
        'project': project,
        'chapter': chapter,
        'feedbacks': feedbacks,
        'feedback_types': ChapterFeedback.FeedbackType.choices,
    }
    return render(request, 'writing_hub/review_chapter.html', context)


@require_http_methods(["POST"])
def add_feedback(request, project_id, chapter_id):
    """Add feedback to a chapter"""
    from .models import ChapterFeedback
    
    chapter = get_object_or_404(BookChapters, id=chapter_id, project_id=project_id)
    
    try:
        data = json.loads(request.body)
        feedback = ChapterFeedback.objects.create(
            chapter=chapter,
            feedback_type=data.get('type', 'suggestion'),
            content=data.get('content', ''),
            text_selection=data.get('text_reference', '') or data.get('text_selection', ''),
            reviewer_name=data.get('reviewer_name', 'Autor'),
        )
        return JsonResponse({
            'success': True,
            'id': feedback.id,
            'message': 'Feedback hinzugefügt'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def resolve_feedback(request, project_id, feedback_id):
    """Mark feedback as resolved"""
    from .models import ChapterFeedback
    from django.utils import timezone
    
    try:
        feedback = ChapterFeedback.objects.get(id=feedback_id, chapter__project_id=project_id)
        data = json.loads(request.body) if request.body else {}
        
        feedback.status = 'resolved'
        feedback.resolution_note = data.get('note', '')
        feedback.resolved_at = timezone.now()
        feedback.save()
        
        return JsonResponse({'success': True, 'message': 'Feedback erledigt'})
    except ChapterFeedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Feedback nicht gefunden'}, status=404)


@require_http_methods(["POST"])
def delete_feedback(request, project_id, feedback_id):
    """Delete feedback"""
    from .models import ChapterFeedback
    
    try:
        feedback = ChapterFeedback.objects.get(id=feedback_id, chapter__project_id=project_id)
        feedback.delete()
        return JsonResponse({'success': True, 'message': 'Feedback gelöscht'})
    except ChapterFeedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Feedback nicht gefunden'}, status=404)


# -----------------------------------------------------------------------------
# Project-Level Feedback (Buch-Ebene)
# -----------------------------------------------------------------------------

@require_http_methods(["POST"])
def add_project_feedback(request, project_id):
    """Add project-level feedback"""
    from .models import ProjectFeedback
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        feedback = ProjectFeedback.objects.create(
            project=project,
            scope=data.get('scope', 'other'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            reviewer_name=data.get('reviewer_name', 'Autor'),
        )
        
        # Add affected chapters if provided
        chapter_ids = data.get('affected_chapters', [])
        if chapter_ids:
            chapters = BookChapters.objects.filter(id__in=chapter_ids, project=project)
            feedback.affected_chapters.set(chapters)
        
        return JsonResponse({
            'success': True,
            'id': feedback.id,
            'message': 'Projekt-Feedback hinzugefügt'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def resolve_project_feedback(request, project_id, feedback_id):
    """Mark project feedback as resolved"""
    from .models import ProjectFeedback
    from django.utils import timezone
    
    try:
        feedback = ProjectFeedback.objects.get(id=feedback_id, project_id=project_id)
        data = json.loads(request.body) if request.body else {}
        
        feedback.status = 'resolved'
        feedback.resolution_note = data.get('note', '')
        feedback.resolved_at = timezone.now()
        feedback.save()
        
        return JsonResponse({'success': True, 'message': 'Projekt-Feedback erledigt'})
    except ProjectFeedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Feedback nicht gefunden'}, status=404)


@require_http_methods(["POST"])
def delete_project_feedback(request, project_id, feedback_id):
    """Delete project feedback"""
    from .models import ProjectFeedback
    
    try:
        feedback = ProjectFeedback.objects.get(id=feedback_id, project_id=project_id)
        feedback.delete()
        return JsonResponse({'success': True, 'message': 'Projekt-Feedback gelöscht'})
    except ProjectFeedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Feedback nicht gefunden'}, status=404)


# =============================================================================
# PHASE 6.7: VERSIONING (MVP)
# =============================================================================

def versions_dashboard(request, project_id):
    """Version management dashboard"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    from .models import ProjectVersion
    
    versions = ProjectVersion.objects.filter(project=project).order_by('-version_number')
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    total_words = sum(ch.word_count or 0 for ch in chapters)
    
    context = {
        'project': project,
        'versions': versions,
        'current_words': total_words,
        'current_chapters': chapters.count(),
    }
    return render(request, 'writing_hub/versions_dashboard.html', context)


@require_http_methods(["POST"])
def create_version(request, project_id):
    """Create a new version snapshot"""
    from .models import ProjectVersion, ChapterSnapshot
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    try:
        data = json.loads(request.body)
        version_name = data.get('name', 'Unbenannt')
        description = data.get('description', '')
        
        # Get next version number
        last_version = ProjectVersion.objects.filter(project=project).order_by('-version_number').first()
        next_number = (last_version.version_number + 1) if last_version else 1
        
        # Check max versions (10)
        version_count = ProjectVersion.objects.filter(project=project).count()
        if version_count >= 10:
            # Delete oldest
            oldest = ProjectVersion.objects.filter(project=project).order_by('version_number').first()
            if oldest:
                oldest.delete()
        
        # Create version
        total_words = sum(ch.word_count or 0 for ch in chapters)
        version = ProjectVersion.objects.create(
            project=project,
            version_name=version_name,
            version_number=next_number,
            description=description,
            total_words=total_words,
            total_chapters=chapters.count(),
        )
        
        # Create snapshots for each chapter
        for ch in chapters:
            ChapterSnapshot.objects.create(
                version=version,
                chapter=ch,
                chapter_number=ch.chapter_number,
                title=ch.title or f'Kapitel {ch.chapter_number}',
                content=ch.content or '',
                outline=ch.outline or '',
                word_count=ch.word_count or 0,
            )
        
        return JsonResponse({
            'success': True,
            'version_id': version.id,
            'version_number': version.version_number,
            'message': f'Version {next_number} erstellt'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def restore_version(request, project_id, version_id):
    """Restore a version snapshot"""
    from .models import ProjectVersion, ChapterSnapshot
    
    project = get_object_or_404(BookProjects, id=project_id)
    version = get_object_or_404(ProjectVersion, id=version_id, project=project)
    
    try:
        snapshots = ChapterSnapshot.objects.filter(version=version)
        restored = 0
        
        for snapshot in snapshots:
            try:
                chapter = snapshot.chapter
                chapter.content = snapshot.content
                chapter.outline = snapshot.outline
                chapter.word_count = snapshot.word_count
                chapter.save()
                restored += 1
            except BookChapters.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'restored': restored,
            'message': f'Version {version.version_number} wiederhergestellt ({restored} Kapitel)'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def compare_versions(request, project_id, version_id):
    """Compare a version with current state"""
    from .models import ProjectVersion, ChapterSnapshot
    
    project = get_object_or_404(BookProjects, id=project_id)
    version = get_object_or_404(ProjectVersion, id=version_id, project=project)
    
    snapshots = ChapterSnapshot.objects.filter(version=version).order_by('chapter_number')
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    # Build comparison data
    comparisons = []
    for snapshot in snapshots:
        try:
            current_chapter = chapters.get(id=snapshot.chapter_id)
            old_content = snapshot.content or ''
            new_content = current_chapter.content or ''
            
            # Simple word diff count
            old_words = len(old_content.split())
            new_words = len(new_content.split())
            word_diff = new_words - old_words
            
            comparisons.append({
                'chapter_number': snapshot.chapter_number,
                'title': snapshot.title,
                'old_words': old_words,
                'new_words': new_words,
                'word_diff': word_diff,
                'changed': old_content != new_content,
                'old_preview': old_content[:300] if old_content else '',
                'new_preview': new_content[:300] if new_content else '',
            })
        except BookChapters.DoesNotExist:
            comparisons.append({
                'chapter_number': snapshot.chapter_number,
                'title': snapshot.title,
                'deleted': True,
            })
    
    context = {
        'project': project,
        'version': version,
        'comparisons': comparisons,
    }
    return render(request, 'writing_hub/version_compare.html', context)


# =============================================================================
# PHASE 6.5: REDAKTION (Editing) - MVP
# =============================================================================

def editing_dashboard(request, project_id):
    """Editing dashboard - AI-powered text improvement"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    from .models import EditingSuggestion, ProjectFeedback, ChapterFeedback
    
    # Get suggestion stats per chapter
    chapters_data = []
    for ch in chapters:
        pending = EditingSuggestion.objects.filter(chapter=ch, status='pending').count()
        accepted = EditingSuggestion.objects.filter(chapter=ch, status='accepted').count()
        rejected = EditingSuggestion.objects.filter(chapter=ch, status='rejected').count()
        
        chapters_data.append({
            'chapter': ch,
            'pending': pending,
            'accepted': accepted,
            'rejected': rejected,
            'total': pending + accepted + rejected
        })
    
    total_pending = sum(c['pending'] for c in chapters_data)
    
    # Get ALL pending suggestions across all chapters
    all_suggestions = EditingSuggestion.objects.filter(
        chapter__project=project,
        status='pending'
    ).select_related('chapter').order_by('chapter__chapter_number', '-created_at')[:50]
    
    # Get project-level feedback (for cross-chapter context)
    project_feedbacks = ProjectFeedback.objects.filter(
        project=project, status='open'
    ).order_by('-created_at')[:10]
    
    # Count open chapter feedbacks
    chapter_feedback_count = ChapterFeedback.objects.filter(
        chapter__project=project, status='open'
    ).count()
    
    context = {
        'project': project,
        'chapters_data': chapters_data,
        'total_pending': total_pending,
        'all_suggestions': all_suggestions,
        'project_feedbacks': project_feedbacks,
        'chapter_feedback_count': chapter_feedback_count,
    }
    return render(request, 'writing_hub/editing_dashboard.html', context)


def editing_chapter(request, project_id, chapter_id):
    """Edit a specific chapter with AI suggestions"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    from .models import EditingSuggestion, ChapterFeedback, ProjectFeedback
    
    suggestions = EditingSuggestion.objects.filter(
        chapter=chapter,
        status='pending'
    ).order_by('position_start')
    
    # Get feedback for context
    chapter_feedbacks = ChapterFeedback.objects.filter(
        chapter=chapter, status='open'
    ).order_by('-created_at')[:10]
    
    project_feedbacks = ProjectFeedback.objects.filter(
        project=project, status='open'
    ).filter(
        Q(affected_chapters=chapter) | Q(affected_chapters__isnull=True)
    ).distinct().order_by('-created_at')[:5]
    
    # Build feedback context string for AI
    feedback_items = []
    for fb in chapter_feedbacks:
        feedback_items.append(f"[Kapitel] {fb.get_feedback_type_display()}: {fb.content}")
    for pf in project_feedbacks:
        feedback_items.append(f"[Projekt/{pf.get_scope_display()}] {pf.title}: {pf.content}")
    
    feedback_context = "\n".join(feedback_items) if feedback_items else ""
    
    context = {
        'project': project,
        'chapter': chapter,
        'suggestions': suggestions,
        'chapter_feedbacks': chapter_feedbacks,
        'project_feedbacks': project_feedbacks,
        'feedback_context': feedback_context,
        'has_feedback': bool(feedback_items),
        'suggestions_json': json.dumps([
            {
                'id': s.id,
                'type': s.suggestion_type,
                'type_display': s.get_suggestion_type_display(),
                'original': s.original_text,
                'suggested': s.suggested_text,
                'explanation': s.explanation,
            }
            for s in suggestions
        ]),
    }
    return render(request, 'writing_hub/editing_chapter.html', context)


@require_http_methods(["POST"])
def analyze_chapter(request, project_id, chapter_id):
    """Analyze chapter and generate AI suggestions"""
    from .handlers.editing_handler import EditingHandler
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    # Get feedback context from request body
    feedback_context = None
    try:
        data = json.loads(request.body) if request.body else {}
        feedback_context = data.get('feedback_context', '')
    except:
        pass
    
    handler = EditingHandler()
    result = handler.analyze_chapter(chapter_id, feedback_context=feedback_context)
    
    return JsonResponse({
        'success': result.success,
        'message': result.message,
        'suggestions': result.suggestions,
        'total_issues': result.total_issues,
        'error': result.error,
        'used_feedback': bool(feedback_context)
    })


@require_http_methods(["POST"])
def apply_suggestion(request, project_id, suggestion_id):
    """Apply a single editing suggestion"""
    from .handlers.editing_handler import EditingHandler
    
    handler = EditingHandler()
    result = handler.apply_suggestion(suggestion_id)
    
    return JsonResponse(result)


@require_http_methods(["POST"])
def reject_suggestion(request, project_id, suggestion_id):
    """Reject a single editing suggestion"""
    from .handlers.editing_handler import EditingHandler
    
    handler = EditingHandler()
    result = handler.reject_suggestion(suggestion_id)
    
    return JsonResponse(result)


@require_http_methods(["POST"])
def apply_all_suggestions(request, project_id, chapter_id):
    """Apply all pending suggestions for a chapter"""
    from .handlers.editing_handler import EditingHandler
    
    handler = EditingHandler()
    result = handler.apply_all_suggestions(chapter_id)
    
    return JsonResponse(result)


@require_http_methods(["POST"])
def analyze_all_chapters(request, project_id):
    """Analyze all chapters of a project and generate AI suggestions"""
    from .handlers.editing_handler import EditingHandler
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Get feedback context from request body
    feedback_context = None
    try:
        data = json.loads(request.body) if request.body else {}
        feedback_context = data.get('feedback_context', '')
    except:
        pass
    
    handler = EditingHandler()
    result = handler.analyze_all_chapters(project_id, feedback_context=feedback_context)
    
    return JsonResponse(result)


# =============================================================================
# PHASE 7: EXPORT
# =============================================================================

def export_dialog(request, project_id):
    """Export dialog for manuscript"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    total_words = sum(ch.word_count or 0 for ch in chapters)
    
    # Check which export formats are available
    export_formats = [
        ('pdf', 'PDF', 'bi-file-pdf', True),
        ('epub', 'EPUB', 'bi-book', True),
        ('markdown', 'Markdown', 'bi-markdown', True),
        ('html', 'HTML', 'bi-filetype-html', True),
        ('txt', 'Text', 'bi-file-text', True),
    ]
    
    context = {
        'project': project,
        'chapters': chapters,
        'total_words': total_words,
        'export_formats': export_formats,
        'estimated_pages': total_words // 250 if total_words else 0,
    }
    return render(request, 'writing_hub/export_dialog.html', context)


@require_http_methods(["POST"])
def export_manuscript(request, project_id):
    """Export manuscript using BookExporter service"""
    from django.http import HttpResponse
    from .services.book_exporter import BookExporter
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        format_type = data.get('format', 'markdown')
        include_outline = data.get('include_outline', False)
        include_images = data.get('include_images', True)
        include_figure_index = data.get('include_figure_index', False)
        
        exporter = BookExporter(project)
        result = exporter.export(
            format_type, 
            include_outline,
            include_images=include_images,
            include_figure_index=include_figure_index
        )
        
        response = HttpResponse(result['content'], content_type=result['content_type'])
        response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
        return response
        
    except ImportError as e:
        return JsonResponse({
            'success': False, 
            'error': f'Export-Format nicht verfügbar: {str(e)}'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def manuscript_preview(request, project_id):
    """Full manuscript preview - read the complete work"""
    import markdown
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = list(BookChapters.objects.filter(project=project).order_by('chapter_number'))
    
    # Convert markdown to HTML for each chapter
    for ch in chapters:
        if ch.content:
            ch.content_html = markdown.markdown(ch.content, extensions=['extra', 'nl2br'])
        else:
            ch.content_html = ''
    
    total_words = sum(ch.word_count or 0 for ch in chapters)
    chapters_with_content = [ch for ch in chapters if ch.content]
    
    context = {
        'project': project,
        'chapters': chapters,
        'total_words': total_words,
        'chapters_with_content': len(chapters_with_content),
        'estimated_pages': total_words // 250 if total_words else 0,
        'estimated_read_time': total_words // 200 if total_words else 0,  # ~200 words/min
    }
    return render(request, 'writing_hub/manuscript_preview.html', context)


# =============================================================================
# ILLUSTRATION PHASE
# =============================================================================

@login_required
def illustration_dashboard(request, project_id):
    """Illustration dashboard with style management and image generation"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    from .models import IllustrationStyle, ChapterIllustration, ChapterSceneAnalysis
    
    # Get or check for illustration style
    try:
        style = project.illustration_style
    except IllustrationStyle.DoesNotExist:
        style = None
    
    # Get illustration stats per chapter
    chapters_data = []
    for ch in chapters:
        illustrations = ChapterIllustration.objects.filter(chapter=ch)
        completed_illustrations = illustrations.filter(status='completed')
        completed = completed_illustrations.count()
        pending = illustrations.filter(status__in=['pending', 'generating']).count()
        
        # Get preview image (first completed illustration)
        preview_image = None
        first_completed = completed_illustrations.first()
        if first_completed and first_completed.image_url:
            preview_image = first_completed.image_url
        
        # Get scene analysis status
        scene_count = 0
        scenes_with_images = 0
        scenes_with_selected = 0
        try:
            analysis = ChapterSceneAnalysis.objects.get(chapter=ch)
            scenes = analysis.scenes if isinstance(analysis.scenes, list) else []
            scene_count = len(scenes)
            # Count scenes that have at least one completed image
            scene_illustrations = illustrations.filter(position='scene', status='completed')
            scenes_with_images = scene_illustrations.values('position_index').distinct().count()
            # Count scenes that have a SELECTED image
            scenes_with_selected = scene_illustrations.filter(is_selected=True).values('position_index').distinct().count()
        except ChapterSceneAnalysis.DoesNotExist:
            pass
        
        chapters_data.append({
            'chapter': ch,
            'completed': completed,
            'pending': pending,
            'total': illustrations.count(),
            'has_content': bool(ch.content and len(ch.content) > 100),
            'preview_image': preview_image,
            'scene_count': scene_count,
            'scenes_with_images': scenes_with_images,
            'scenes_with_selected': scenes_with_selected,
            'all_scenes_done': scene_count > 0 and scenes_with_selected >= scene_count,
        })
    
    total_completed = sum(c['completed'] for c in chapters_data)
    total_pending = sum(c['pending'] for c in chapters_data)
    
    # Cost estimation (DALL-E 3: ~$0.04 per image)
    estimated_cost = len([c for c in chapters_data if c['has_content']]) * 0.04
    
    # Style presets for genre
    genre = getattr(project, 'genre', None)
    # genre can be a string or an object with .name attribute
    if genre:
        genre_name = genre.name.lower() if hasattr(genre, 'name') else str(genre).lower()
    else:
        genre_name = 'fantasy'
    preset = IllustrationStyle.get_preset_for_genre(genre_name)
    
    context = {
        'project': project,
        'chapters_data': chapters_data,
        'style': style,
        'has_style': style is not None,
        'total_completed': total_completed,
        'total_pending': total_pending,
        'estimated_cost': f"${estimated_cost:.2f}",
        'style_types': IllustrationStyle.StyleType.choices,
        'providers': IllustrationStyle.Provider.choices,
        'preset': preset,
    }
    return render(request, 'writing_hub/illustration_dashboard.html', context)


@require_http_methods(["POST"])
def save_illustration_style(request, project_id):
    """Save or update the illustration style for a project"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    from .models import IllustrationStyle
    
    try:
        data = json.loads(request.body)
        
        style, created = IllustrationStyle.objects.update_or_create(
            project=project,
            defaults={
                'style_type': data.get('style_type', 'watercolor'),
                'style_name': data.get('style_name', 'Benutzerdefiniert'),
                'base_prompt': data.get('base_prompt', ''),
                'negative_prompt': data.get('negative_prompt', ''),
                'color_palette': data.get('color_palette', []),
                'provider': data.get('provider', 'dalle3'),
                'quality': data.get('quality', 'hd'),
                'image_size': data.get('image_size', '1024x1024'),
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Stil gespeichert' if created else 'Stil aktualisiert',
            'style_id': style.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def generate_chapter_illustration(request, project_id, chapter_id):
    """Generate illustration for a specific chapter using local ComfyUI (Stable Diffusion)"""
    import asyncio
    from decimal import Decimal
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    from .models import IllustrationStyle, ChapterIllustration
    from .models_prompt_system import PromptMasterStyle
    from .handlers.prompt_builder_handler import PromptBuilderHandler
    
    # Check if new prompt system exists (preferred)
    prompt_result = None
    try:
        master_style = PromptMasterStyle.objects.get(project=project)
        handler = PromptBuilderHandler(project_id=project_id)
        
        data = json.loads(request.body) if request.body else {}
        scene_type = data.get('scene_type', 'establishing')
        time_of_day = data.get('time_of_day', 'day')
        
        prompt_result = handler.build_chapter_prompt(
            chapter=chapter,
            scene_type=scene_type,
            time_of_day=time_of_day
        )
        
        if not prompt_result.success:
            return JsonResponse({
                'success': False,
                'error': prompt_result.error
            }, status=400)
            
    except PromptMasterStyle.DoesNotExist:
        # Fallback to legacy IllustrationStyle
        pass
    
    # Fallback: Check legacy style exists
    if not prompt_result:
        try:
            style = project.illustration_style
        except IllustrationStyle.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Bitte zuerst einen Illustrations-Stil festlegen (Admin → Illustration-System)'
            }, status=400)
    
    # Check if chapter has content
    if not chapter.content or len(chapter.content) < 100:
        return JsonResponse({
            'success': False,
            'error': 'Kapitel hat zu wenig Inhalt'
        }, status=400)
    
    try:
        data = json.loads(request.body) if request.body else {}
        scene_description = data.get('scene_description', '')
        
        # Default scene description from chapter if not provided
        if not scene_description:
            paragraphs = [p.strip() for p in chapter.content.split('\n\n') if p.strip()]
            first_para = paragraphs[0][:200] if paragraphs else chapter.content[:200]
            scene_description = f"{chapter.title}: {first_para}"
        
        # Use new prompt system if available
        if prompt_result and prompt_result.success:
            full_prompt = prompt_result.prompt
            negative_prompt = prompt_result.negative_prompt
            width = prompt_result.width
            height = prompt_result.height
            steps = prompt_result.steps
            guidance = prompt_result.guidance_scale
        else:
            # Fallback to legacy system
            if not scene_description:
                paragraphs = [p.strip() for p in chapter.content.split('\n\n') if p.strip()]
                first_para = paragraphs[0][:200] if paragraphs else chapter.content[:200]
                scene_description = f"{chapter.title}: {first_para}"
            
            full_prompt = style.get_full_prompt(scene_description)
            negative_prompt = style.negative_prompt or "blurry, low quality, text, watermark"
            width = 1024
            height = 1024
            steps = 25
            guidance = 7.5
        
        # Create illustration record
        illustration = ChapterIllustration.objects.create(
            chapter=chapter,
            position='header',
            scene_description=scene_description,
            scene_text_excerpt=chapter.content[:300],
            full_prompt=full_prompt,
            status='generating'
        )
        
        # Determine ComfyUI preset based on style
        if prompt_result and prompt_result.success:
            # Use preset from master style
            comfy_preset = 'fantasy_digital'  # Default for new system
        else:
            style_preset_map = {
                'watercolor': 'fantasy_watercolor',
                'digital_art': 'fantasy_digital',
                'oil_painting': 'fantasy_digital',
                'pencil_sketch': 'childrens_book',
                'anime': 'manga',
                'realistic': 'realistic',
            }
            comfy_preset = style_preset_map.get(style.style_type, 'fantasy_watercolor')
        
        # Generate image with ComfyUI (local Stable Diffusion)
        try:
            from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
            
            comfy_handler = ComfyUIHandler()
            
            # Run async generation
            async def generate():
                # Check if ComfyUI is running
                if not await comfy_handler.check_connection():
                    raise Exception("ComfyUI nicht erreichbar. Bitte starten: cd ~/ai-tools/ComfyUI && python main.py --listen 0.0.0.0 --port 8181")
                
                return await comfy_handler.generate_image(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    steps=steps,
                    cfg=guidance,
                    style_preset=comfy_preset
                )
            
            result = asyncio.run(generate())
            
            if result and result.get('success'):
                illustration.image_url = result.get('image_url', '')
                illustration.generation_cost = Decimal(str(result.get('cost_usd', 0)))
                illustration.generation_time_seconds = int(result.get('generation_time_seconds', 0))
                illustration.status = 'completed'
                illustration.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Bild generiert in {illustration.generation_time_seconds}s (lokal, kostenlos!)',
                    'illustration_id': illustration.id,
                    'image_url': illustration.image_url,
                    'cost': '€0 (lokal)'
                })
            else:
                illustration.status = 'failed'
                illustration.error_message = 'Keine Bilder zurückgegeben'
                illustration.save()
                return JsonResponse({
                    'success': False,
                    'error': 'Keine Bilder generiert'
                }, status=500)
                
        except Exception as gen_error:
            illustration.status = 'failed'
            illustration.error_message = str(gen_error)
            illustration.save()
            return JsonResponse({
                'success': False,
                'error': f'Bildgenerierung fehlgeschlagen: {str(gen_error)}'
            }, status=500)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def analyze_chapter_scenes(request, project_id, chapter_id):
    """Analyze chapter to find optimal illustration positions"""
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    if not chapter.content or len(chapter.content) < 100:
        return JsonResponse({
            'success': False,
            'error': 'Kapitel hat zu wenig Inhalt'
        }, status=400)
    
    # Simple scene extraction (MVP - can be enhanced with LLM later)
    scenes = []
    
    # Extract chapter opening
    scenes.append({
        'position': 'header',
        'description': f"Kapitel-Header: {chapter.title}",
        'excerpt': chapter.content[:200]
    })
    
    # Look for scene breaks (double newlines, "***", etc.)
    paragraphs = chapter.content.split('\n\n')
    if len(paragraphs) > 3:
        mid_point = len(paragraphs) // 2
        scenes.append({
            'position': 'scene',
            'description': 'Szene in der Mitte des Kapitels',
            'excerpt': paragraphs[mid_point][:200] if paragraphs[mid_point] else ''
        })
    
    return JsonResponse({
        'success': True,
        'scenes': scenes,
        'chapter_id': chapter_id
    })


def chapter_images_gallery(request, project_id, chapter_id):
    """Display all images for a specific chapter."""
    from .models import ChapterIllustration
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    illustrations = ChapterIllustration.objects.filter(
        chapter=chapter
    ).order_by('position', 'position_index', '-created_at')
    
    # Group by position
    by_position = {}
    for ill in illustrations:
        pos = ill.get_position_display()
        if pos not in by_position:
            by_position[pos] = []
        by_position[pos].append(ill)
    
    # Get prev/next chapters for navigation
    prev_chapter = BookChapters.objects.filter(
        project=project, 
        chapter_number__lt=chapter.chapter_number
    ).order_by('-chapter_number').first()
    
    next_chapter = BookChapters.objects.filter(
        project=project, 
        chapter_number__gt=chapter.chapter_number
    ).order_by('chapter_number').first()
    
    context = {
        'project': project,
        'chapter': chapter,
        'illustrations': illustrations,
        'by_position': by_position,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'total_count': illustrations.count(),
        'completed_count': illustrations.filter(status='completed').count(),
    }
    return render(request, 'writing_hub/chapter_images_gallery.html', context)


@login_required
@require_http_methods(["POST"])
def analyze_chapter_content(request, project_id, chapter_id):
    """Analyze chapter content with LLM to extract visual scenes."""
    from .services.chapter_analyzer_service import ChapterAnalyzerService
    
    logger.info(f"[analyze_chapter_content] Called for project={project_id}, chapter={chapter_id}")
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    force = request.POST.get('force', 'false').lower() == 'true'
    logger.info(f"[analyze_chapter_content] Chapter: {chapter.title}, force={force}")
    
    try:
        service = ChapterAnalyzerService()
        analysis = service.analyze_chapter(chapter, force_reanalyze=force)
        
        # Debug logging
        logger.info(f"Analysis created: {analysis.id}, scenes: {len(analysis.scenes)}, type: {type(analysis.scenes)}")
        logger.debug(f"Scenes: {analysis.scenes}")
        
        return JsonResponse({
            'success': True,
            'analysis': {
                'id': analysis.id,
                'scenes': analysis.scenes,
                'best_scene_index': analysis.best_scene_index,
                'best_scene_reason': analysis.best_scene_reason,
                'overall_color_mood': analysis.overall_color_mood,
                'chapter_atmosphere': analysis.chapter_atmosphere,
                'scene_count': len(analysis.scenes),
            }
        })
    except Exception as e:
        logger.error(f"Chapter analysis failed: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def analyze_all_chapters_scenes(request, project_id):
    """Analyze all chapters of a project to extract visual scenes for illustration."""
    from .services.chapter_analyzer_service import ChapterAnalyzerService
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    results = []
    analyzed = 0
    skipped = 0
    errors = []
    
    service = ChapterAnalyzerService()
    
    for chapter in chapters:
        if not chapter.content or len(chapter.content) < 100:
            skipped += 1
            results.append({
                'chapter_id': chapter.id,
                'chapter_number': chapter.chapter_number,
                'title': chapter.title,
                'status': 'skipped',
                'reason': 'Kein Inhalt'
            })
            continue
        
        try:
            analysis = service.analyze_chapter(chapter, force_reanalyze=False)
            analyzed += 1
            results.append({
                'chapter_id': chapter.id,
                'chapter_number': chapter.chapter_number,
                'title': chapter.title,
                'status': 'success',
                'scene_count': len(analysis.scenes) if analysis.scenes else 0
            })
        except Exception as e:
            errors.append(f"Kapitel {chapter.chapter_number}: {str(e)}")
            results.append({
                'chapter_id': chapter.id,
                'chapter_number': chapter.chapter_number,
                'title': chapter.title,
                'status': 'error',
                'error': str(e)
            })
    
    return JsonResponse({
        'success': True,
        'analyzed': analyzed,
        'skipped': skipped,
        'errors': errors,
        'results': results,
        'message': f'{analyzed} Kapitel analysiert, {skipped} übersprungen'
    })


@login_required
def get_chapter_scenes(request, project_id, chapter_id):
    """Get analyzed scenes for a chapter (for UI display)."""
    from .models import ChapterSceneAnalysis, ChapterIllustration
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    try:
        analysis = ChapterSceneAnalysis.objects.get(chapter=chapter)
        
        # Check if analysis is still valid
        is_valid = analysis.is_valid()
        
        # Ensure scenes is a list
        scenes = analysis.scenes if isinstance(analysis.scenes, list) else []
        
        # Get existing illustrations for each scene
        illustrations = ChapterIllustration.objects.filter(
            chapter=chapter, position='scene'
        ).order_by('position_index')
        
        # Map illustrations by scene index
        illust_by_index = {}
        for illust in illustrations:
            idx = illust.position_index or 0
            if idx not in illust_by_index:
                illust_by_index[idx] = []
            illust_by_index[idx].append({
                'id': illust.id,
                'image_url': illust.image_url,
                'status': illust.status,
                'is_selected': illust.is_selected,
                'caption': illust.caption or '',
                'created_at': illust.created_at.isoformat() if illust.created_at else None,
            })
        
        # Add illustrations to scenes and check for selected image
        for i, scene in enumerate(scenes):
            scene_illustrations = illust_by_index.get(i, [])
            scene['illustrations'] = scene_illustrations
            scene['has_selected'] = any(img.get('is_selected') for img in scene_illustrations)
        
        logger.info(f"[get_chapter_scenes] chapter={chapter_id}, scenes={len(scenes)}, illustrations={len(illustrations)}")
        
        return JsonResponse({
            'success': True,
            'has_analysis': True,
            'is_valid': is_valid,
            'scenes': scenes,
            'best_scene_index': analysis.best_scene_index,
            'best_scene_reason': analysis.best_scene_reason,
            'overall_color_mood': analysis.overall_color_mood,
            'chapter_atmosphere': analysis.chapter_atmosphere,
        })
    except ChapterSceneAnalysis.DoesNotExist:
        logger.info(f"[get_chapter_scenes] No analysis for chapter {chapter_id}")
        return JsonResponse({
            'success': True,
            'has_analysis': False,
            'scenes': [],
        })


@require_http_methods(["POST"])
def generate_scene_illustration(request, project_id, chapter_id):
    """Generate illustration for a specific scene from analysis."""
    from .models import ChapterIllustration, ChapterSceneAnalysis
    from .services.scene_prompt_builder import ScenePromptBuilder
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapter = get_object_or_404(BookChapters, id=chapter_id, project=project)
    
    try:
        data = json.loads(request.body) if request.body else {}
        scene_index = data.get('scene_index', 0)
        
        # Get analysis
        try:
            analysis = ChapterSceneAnalysis.objects.get(chapter=chapter)
        except ChapterSceneAnalysis.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Kapitel wurde noch nicht analysiert. Bitte zuerst "Szenen analysieren" klicken.'
            }, status=400)
        
        # Get the scene
        scene = analysis.get_scene(scene_index)
        if not scene:
            return JsonResponse({
                'success': False,
                'error': f'Szene {scene_index} nicht gefunden'
            }, status=400)
        
        # Build optimized prompt (uses LLM to improve prompt quality)
        builder = ScenePromptBuilder(project_id)
        prompt_result = builder.build_optimized(
            scene_data=scene,
            overall_mood=analysis.chapter_atmosphere,
            color_mood=analysis.overall_color_mood,
            use_llm=True  # Use ImagePromptOptimizer for better prompts
        )
        
        if not prompt_result.success:
            return JsonResponse({
                'success': False,
                'error': prompt_result.error
            }, status=400)
        
        # Create illustration record
        illustration = ChapterIllustration.objects.create(
            chapter=chapter,
            position='scene',
            position_index=scene_index,
            scene_description=scene.get('description', ''),
            full_prompt=prompt_result.prompt,
            status='generating',
        )
        
        # Generate image with ComfyUI
        import asyncio
        from decimal import Decimal
        
        try:
            from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
            
            comfy_handler = ComfyUIHandler()
            
            async def generate():
                if not await comfy_handler.check_connection():
                    raise Exception("ComfyUI nicht erreichbar. Bitte starten: cd ~/ai-tools/ComfyUI && python main.py --listen 0.0.0.0 --port 8181")
                
                return await comfy_handler.generate_image(
                    prompt=prompt_result.prompt,
                    negative_prompt=prompt_result.negative_prompt,
                    width=prompt_result.width,
                    height=prompt_result.height,
                    steps=prompt_result.steps,
                    cfg=prompt_result.guidance_scale,
                    style_preset='fantasy_digital'
                )
            
            result = asyncio.run(generate())
            
            if result and result.get('success'):
                illustration.image_url = result.get('image_url', '')
                illustration.generation_cost = Decimal(str(result.get('cost_usd', 0)))
                illustration.generation_time_seconds = int(result.get('generation_time_seconds', 0))
                illustration.status = 'completed'
                illustration.save()
                
                return JsonResponse({
                    'success': True,
                    'illustration_id': illustration.id,
                    'image_url': illustration.image_url,
                    'prompt': prompt_result.prompt,
                    'scene_title': prompt_result.scene_title,
                    'message': f'Bild generiert in {illustration.generation_time_seconds}s'
                })
            else:
                illustration.status = 'failed'
                illustration.error_message = 'Keine Bilder zurückgegeben'
                illustration.save()
                return JsonResponse({
                    'success': False,
                    'error': 'Keine Bilder generiert'
                }, status=500)
                
        except Exception as gen_error:
            illustration.status = 'failed'
            illustration.error_message = str(gen_error)
            illustration.save()
            return JsonResponse({
                'success': False,
                'error': f'Bildgenerierung fehlgeschlagen: {str(gen_error)}'
            }, status=500)
        
    except Exception as e:
        logger.error(f"Scene illustration generation failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def delete_illustration(request, illustration_id):
    """Delete an illustration."""
    from .models import ChapterIllustration
    
    try:
        illustration = get_object_or_404(ChapterIllustration, id=illustration_id)
        illustration.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Delete illustration failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def select_illustration(request, illustration_id):
    """Select an illustration for use in the book (deselects others for same scene)."""
    from .models import ChapterIllustration
    
    try:
        illustration = get_object_or_404(ChapterIllustration, id=illustration_id)
        
        # Deselect all other illustrations for the same scene
        ChapterIllustration.objects.filter(
            chapter=illustration.chapter,
            position=illustration.position,
            position_index=illustration.position_index
        ).update(is_selected=False)
        
        # Select this one
        illustration.is_selected = True
        illustration.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Bild ausgewählt für Verwendung im Buch'
        })
    except Exception as e:
        logger.error(f"Select illustration failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_all_chapter_scenes(request, project_id, chapter_id):
    """Generate images for all scenes in a chapter that don't have images yet."""
    from .models import ChapterSceneAnalysis, ChapterIllustration
    from .services.scene_prompt_builder import ScenePromptBuilder
    
    chapter = get_object_or_404(BookChapters, id=chapter_id, project_id=project_id)
    
    try:
        analysis = ChapterSceneAnalysis.objects.get(chapter=chapter)
        scenes = analysis.scenes if isinstance(analysis.scenes, list) else []
        
        if not scenes:
            return JsonResponse({
                'success': False,
                'error': 'Keine Szenen gefunden. Bitte zuerst analysieren.'
            }, status=400)
        
        builder = ScenePromptBuilder(project_id)
        generated = []
        errors = []
        
        import asyncio
        from decimal import Decimal
        from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
        
        comfy_handler = ComfyUIHandler()
        
        async def check_comfy():
            return await comfy_handler.check_connection()
        
        if not asyncio.run(check_comfy()):
            return JsonResponse({
                'success': False,
                'error': 'ComfyUI nicht erreichbar. Bitte starten.'
            }, status=500)
        
        for scene_index, scene in enumerate(scenes):
            # Check if scene already has a completed image
            existing = ChapterIllustration.objects.filter(
                chapter=chapter,
                position='scene',
                position_index=scene_index,
                status='completed'
            ).exists()
            
            if existing:
                continue  # Skip scenes that already have images
            
            try:
                # Build prompt
                prompt_result = builder.build_optimized(
                    scene_data=scene,
                    overall_mood=analysis.chapter_atmosphere,
                    color_mood=analysis.overall_color_mood,
                    use_llm=True
                )
                
                if not prompt_result.success:
                    errors.append(f"Szene {scene_index + 1}: Prompt-Fehler")
                    continue
                
                # Create illustration record
                illustration = ChapterIllustration.objects.create(
                    chapter=chapter,
                    position='scene',
                    position_index=scene_index,
                    scene_description=scene.get('description', ''),
                    full_prompt=prompt_result.prompt,
                    status='generating',
                )
                
                # Generate image
                async def generate():
                    return await comfy_handler.generate_image(
                        prompt=prompt_result.prompt,
                        negative_prompt=prompt_result.negative_prompt,
                        width=prompt_result.width,
                        height=prompt_result.height,
                        steps=prompt_result.steps,
                        cfg=prompt_result.guidance_scale,
                        style_preset='fantasy_digital'
                    )
                
                result = asyncio.run(generate())
                
                if result and result.get('success'):
                    illustration.image_url = result.get('image_url', '')
                    illustration.generation_cost = Decimal(str(result.get('cost_usd', 0)))
                    illustration.generation_time_seconds = int(result.get('generation_time_seconds', 0))
                    illustration.status = 'completed'
                    illustration.is_selected = True  # Auto-select first image
                    illustration.save()
                    generated.append(scene_index + 1)
                else:
                    illustration.status = 'failed'
                    illustration.save()
                    errors.append(f"Szene {scene_index + 1}: Generierung fehlgeschlagen")
                    
            except Exception as e:
                errors.append(f"Szene {scene_index + 1}: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'generated_scenes': generated,
            'errors': errors,
            'message': f'{len(generated)} Bilder generiert' + (f', {len(errors)} Fehler' if errors else '')
        })
        
    except ChapterSceneAnalysis.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Keine Szenenanalyse gefunden. Bitte zuerst analysieren.'
        }, status=400)
    except Exception as e:
        logger.error(f"Generate all chapter scenes failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_all_project_chapters(request, project_id):
    """Generate images for all chapters in a project that don't have complete scene images."""
    from .models import ChapterSceneAnalysis, ChapterIllustration
    from .services.scene_prompt_builder import ScenePromptBuilder
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    try:
        import asyncio
        from decimal import Decimal
        from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
        
        comfy_handler = ComfyUIHandler()
        
        async def check_comfy():
            return await comfy_handler.check_connection()
        
        if not asyncio.run(check_comfy()):
            return JsonResponse({
                'success': False,
                'error': 'ComfyUI nicht erreichbar. Bitte starten.'
            }, status=500)
        
        builder = ScenePromptBuilder(project_id)
        total_generated = 0
        chapters_processed = 0
        errors = []
        
        for chapter in chapters:
            if not chapter.content or len(chapter.content) < 100:
                continue
            
            try:
                analysis = ChapterSceneAnalysis.objects.get(chapter=chapter)
                scenes = analysis.scenes if isinstance(analysis.scenes, list) else []
            except ChapterSceneAnalysis.DoesNotExist:
                continue
            
            for scene_index, scene in enumerate(scenes):
                # Skip scenes that already have completed images
                existing = ChapterIllustration.objects.filter(
                    chapter=chapter,
                    position='scene',
                    position_index=scene_index,
                    status='completed'
                ).exists()
                
                if existing:
                    continue
                
                try:
                    prompt_result = builder.build_optimized(
                        scene_data=scene,
                        overall_mood=analysis.chapter_atmosphere,
                        color_mood=analysis.overall_color_mood,
                        use_llm=True
                    )
                    
                    if not prompt_result.success:
                        continue
                    
                    illustration = ChapterIllustration.objects.create(
                        chapter=chapter,
                        position='scene',
                        position_index=scene_index,
                        scene_description=scene.get('description', ''),
                        full_prompt=prompt_result.prompt,
                        status='generating',
                    )
                    
                    async def generate():
                        return await comfy_handler.generate_image(
                            prompt=prompt_result.prompt,
                            negative_prompt=prompt_result.negative_prompt,
                            width=prompt_result.width,
                            height=prompt_result.height,
                            steps=prompt_result.steps,
                            cfg=prompt_result.guidance_scale,
                            style_preset='fantasy_digital'
                        )
                    
                    result = asyncio.run(generate())
                    
                    if result and result.get('success'):
                        illustration.image_url = result.get('image_url', '')
                        illustration.generation_cost = Decimal(str(result.get('cost_usd', 0)))
                        illustration.generation_time_seconds = int(result.get('generation_time_seconds', 0))
                        illustration.status = 'completed'
                        illustration.is_selected = True
                        illustration.save()
                        total_generated += 1
                    else:
                        illustration.status = 'failed'
                        illustration.save()
                        
                except Exception as e:
                    errors.append(f"Kap. {chapter.chapter_number}, Szene {scene_index + 1}: {str(e)}")
            
            chapters_processed += 1
        
        return JsonResponse({
            'success': True,
            'chapters_processed': chapters_processed,
            'images_generated': total_generated,
            'errors': errors[:5],  # Limit error messages
            'message': f'{total_generated} Bilder in {chapters_processed} Kapiteln generiert'
        })
        
    except Exception as e:
        logger.error(f"Generate all project chapters failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def illustrate_all_chapters(request, project_id):
    """Generate images for all chapters and insert them into chapter text.
    
    This function:
    1. Iterates through all chapters
    2. For each chapter, generates images for scenes that don't have images yet
    3. Automatically inserts all completed images into the chapter text
    """
    import re
    import asyncio
    from decimal import Decimal
    from .models import ChapterSceneAnalysis, ChapterIllustration
    from .services.scene_prompt_builder import ScenePromptBuilder
    from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    try:
        comfy_handler = ComfyUIHandler()
        
        async def check_comfy():
            return await comfy_handler.check_connection()
        
        if not asyncio.run(check_comfy()):
            return JsonResponse({
                'success': False,
                'error': 'ComfyUI nicht erreichbar. Bitte starten.'
            }, status=500)
        
        builder = ScenePromptBuilder(project_id)
        total_generated = 0
        total_inserted = 0
        chapters_processed = 0
        errors = []
        
        # Get figure numbering style from project
        numbering_style = getattr(project, 'figure_numbering_style', 'global')
        global_figure_counter = 0
        
        for chapter in chapters:
            if not chapter.content or len(chapter.content) < 100:
                continue
            
            try:
                analysis = ChapterSceneAnalysis.objects.get(chapter=chapter)
                scenes = analysis.scenes if isinstance(analysis.scenes, list) else []
            except ChapterSceneAnalysis.DoesNotExist:
                continue
            
            chapter_images_generated = 0
            
            # PHASE 1: Generate missing images
            for scene_index, scene in enumerate(scenes):
                existing = ChapterIllustration.objects.filter(
                    chapter=chapter,
                    position='scene',
                    position_index=scene_index,
                    status='completed'
                ).exists()
                
                if existing:
                    continue
                
                try:
                    prompt_result = builder.build_optimized(
                        scene_data=scene,
                        overall_mood=analysis.chapter_atmosphere,
                        color_mood=analysis.overall_color_mood,
                        use_llm=True
                    )
                    
                    if not prompt_result.success:
                        continue
                    
                    illustration = ChapterIllustration.objects.create(
                        chapter=chapter,
                        position='scene',
                        position_index=scene_index,
                        scene_description=scene.get('description', ''),
                        full_prompt=prompt_result.prompt,
                        status='generating',
                    )
                    
                    async def generate():
                        return await comfy_handler.generate_image(
                            prompt=prompt_result.prompt,
                            negative_prompt=prompt_result.negative_prompt,
                            width=prompt_result.width,
                            height=prompt_result.height,
                            steps=prompt_result.steps,
                            cfg=prompt_result.guidance_scale,
                            style_preset='fantasy_digital'
                        )
                    
                    result = asyncio.run(generate())
                    
                    if result and result.get('success'):
                        illustration.image_url = result.get('image_url', '')
                        illustration.generation_cost = Decimal(str(result.get('cost_usd', 0)))
                        illustration.generation_time_seconds = int(result.get('generation_time_seconds', 0))
                        illustration.status = 'completed'
                        illustration.is_selected = True
                        # Auto-set caption from scene title
                        illustration.caption = scene.get('title', f'Szene {scene_index + 1}')
                        illustration.save()
                        total_generated += 1
                        chapter_images_generated += 1
                    else:
                        illustration.status = 'failed'
                        illustration.save()
                        
                except Exception as e:
                    errors.append(f"Kap. {chapter.chapter_number}, Szene {scene_index + 1}: {str(e)}")
            
            # PHASE 2: Insert all completed images into chapter text
            selected_images = ChapterIllustration.objects.filter(
                chapter=chapter,
                position='scene',
                status='completed',
                is_selected=True
            ).order_by('position_index')
            
            if selected_images.exists():
                content = chapter.content or ''
                
                # Remove existing images first
                image_pattern = r'\n*!\[.*?\]\(.*?\)\n*'
                caption_pattern = r'\n*\*Abb\. [^*]+\*\n*'
                content = re.sub(image_pattern, '\n\n', content)
                content = re.sub(caption_pattern, '', content)
                content = re.sub(r'\n{3,}', '\n\n', content)
                content = content.strip()
                
                # Build insertions
                paragraphs = content.split('\n\n')
                total_paragraphs = len(paragraphs)
                total_images_count = selected_images.count()
                
                insertions = []
                used_positions = set()
                figure_counter = 0
                
                for img in selected_images:
                    figure_counter += 1
                    global_figure_counter += 1
                    scene_index = img.position_index
                    scene_title = f'Szene {scene_index + 1}'
                    insert_pos = None
                    
                    if scene_index < len(scenes):
                        scene = scenes[scene_index]
                        scene_title = scene.get('title', scene_title)
                        text_excerpt = scene.get('text_excerpt', '')
                        if text_excerpt and len(text_excerpt) > 20:
                            if text_excerpt in content:
                                insert_pos = content.find(text_excerpt) + len(text_excerpt)
                            else:
                                short_excerpt = text_excerpt[:50]
                                if short_excerpt in content:
                                    insert_pos = content.find(short_excerpt) + len(short_excerpt)
                    
                    if insert_pos is None and total_paragraphs > 1:
                        para_index = int((scene_index + 1) * total_paragraphs / (total_images_count + 1))
                        para_index = min(para_index, total_paragraphs - 1)
                        current_pos = 0
                        for i, para in enumerate(paragraphs[:para_index + 1]):
                            current_pos += len(para) + 2
                        insert_pos = current_pos - 2
                    
                    if insert_pos is None:
                        insert_pos = len(content)
                    
                    while insert_pos in used_positions:
                        insert_pos += 1
                    used_positions.add(insert_pos)
                    
                    if numbering_style == 'per_chapter':
                        figure_num = f"{chapter.chapter_number}.{figure_counter}"
                    else:
                        figure_num = str(global_figure_counter)
                    
                    caption = img.caption if img.caption else scene_title
                    if not img.caption:
                        img.caption = scene_title
                        img.save(update_fields=['caption'])
                    
                    image_md = f"\n\n![Abb. {figure_num}: {caption}]({img.image_url})\n*Abb. {figure_num}: {caption}*\n"
                    insertions.append((insert_pos, image_md))
                
                # Apply insertions (reverse order to maintain positions)
                insertions.sort(key=lambda x: x[0], reverse=True)
                for pos, img_md in insertions:
                    content = content[:pos] + img_md + content[pos:]
                    total_inserted += 1
                
                chapter.content = content
                chapter.save()
            
            chapters_processed += 1
            logger.info(f"[illustrate_all_chapters] Chapter {chapter.chapter_number}: {chapter_images_generated} generated, {selected_images.count()} inserted")
        
        return JsonResponse({
            'success': True,
            'chapters_processed': chapters_processed,
            'images_generated': total_generated,
            'images_inserted': total_inserted,
            'errors': errors[:5],
            'message': f'{total_generated} Bilder generiert, {total_inserted} Bilder in {chapters_processed} Kapiteln eingefügt'
        })
        
    except Exception as e:
        logger.error(f"Illustrate all chapters failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def reillustrate_all_chapters(request, project_id):
    """Delete all existing images, generate new ones, and insert them into chapter text.
    
    This function:
    1. Deletes all existing ChapterIllustration objects for the project
    2. Removes all image markdown from chapter content
    3. Generates new images for all scenes
    4. Inserts the new images into chapter text
    """
    import re
    from .models import ChapterIllustration
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project)
    
    try:
        # PHASE 1: Delete all existing illustrations for this project
        deleted_count = 0
        for chapter in chapters:
            deleted = ChapterIllustration.objects.filter(chapter=chapter).delete()
            deleted_count += deleted[0] if deleted[0] else 0
            
            # Remove existing image markdown from chapter content
            if chapter.content:
                # Remove markdown images: ![...](...)
                cleaned = re.sub(r'\n*!\[.*?\]\(.*?\)\n*\*.*?\*\n*', '\n\n', chapter.content)
                # Also remove standalone figure captions
                cleaned = re.sub(r'\n*\*Abb\.\s*\d+:.*?\*\n*', '\n\n', cleaned)
                # Clean up multiple newlines
                cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
                chapter.content = cleaned.strip()
                chapter.save()
        
        logger.info(f"[reillustrate] Deleted {deleted_count} illustrations, cleaned chapter content")
        
        # PHASE 2: Use illustrate_all_chapters logic to generate and insert
        # Create a mock request and call the function
        from django.test import RequestFactory
        factory = RequestFactory()
        mock_request = factory.post(f'/writing-hub/project/{project_id}/illustration/illustrate-all-chapters/')
        mock_request.user = request.user
        
        # Call the existing function
        response = illustrate_all_chapters(mock_request, project_id)
        result = json.loads(response.content)
        
        if result.get('success'):
            result['deleted_count'] = deleted_count
            result['message'] = f'{deleted_count} alte Bilder gelöscht. {result.get("message", "")}'
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Reillustrate all chapters failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def insert_chapter_images(request, project_id, chapter_id):
    """Insert selected images into chapter text at the correct positions."""
    from .models import ChapterIllustration, ChapterSceneAnalysis
    
    chapter = get_object_or_404(BookChapters, id=chapter_id, project_id=project_id)
    
    try:
        # Get all selected illustrations for this chapter
        selected_images = ChapterIllustration.objects.filter(
            chapter=chapter,
            position='scene',
            status='completed',
            is_selected=True
        ).order_by('position_index')
        
        if not selected_images.exists():
            return JsonResponse({
                'success': False,
                'error': 'Keine ausgewählten Bilder gefunden.'
            }, status=400)
        
        # Get scene analysis to find text positions
        try:
            analysis = ChapterSceneAnalysis.objects.get(chapter=chapter)
            scenes = analysis.scenes if isinstance(analysis.scenes, list) else []
        except ChapterSceneAnalysis.DoesNotExist:
            scenes = []
        
        # Build image markdown insertions
        content = chapter.content or ''
        images_inserted = 0
        project = chapter.project
        
        # FIRST: Remove any existing images from chapter content
        import re
        image_pattern = r'\n*!\[.*?\]\(.*?\)\n*'
        caption_pattern = r'\n*\*Abb\. [^*]+\*\n*'
        content = re.sub(image_pattern, '\n\n', content)
        content = re.sub(caption_pattern, '', content)
        # Clean up extra blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        logger.info(f"[insert_chapter_images] Removed existing images from chapter {chapter_id}")
        
        # Get figure numbering style from project
        numbering_style = getattr(project, 'figure_numbering_style', 'global')
        
        # Calculate global figure offset (count images in previous chapters)
        global_figure_offset = 0
        if numbering_style == 'global':
            from .models import ChapterIllustration
            previous_chapters = BookChapters.objects.filter(
                project=project,
                chapter_number__lt=chapter.chapter_number
            )
            for prev_ch in previous_chapters:
                global_figure_offset += ChapterIllustration.objects.filter(
                    chapter=prev_ch,
                    is_selected=True,
                    status='completed'
                ).count()
        
        # Strategy: Insert images at end of chapter if no text_excerpt match
        # Split content into paragraphs to distribute images
        paragraphs = content.split('\n\n')
        total_paragraphs = len(paragraphs)
        total_images = selected_images.count()
        
        # Create a list of (position, image_markdown, img_obj) tuples
        insertions = []
        used_positions = set()
        figure_counter = 0
        
        for img in selected_images:
            figure_counter += 1
            scene_index = img.position_index
            scene_title = f'Szene {scene_index + 1}'
            insert_pos = None
            
            if scene_index < len(scenes):
                scene = scenes[scene_index]
                scene_title = scene.get('title', scene_title)
                
                # Try to find text_excerpt in content
                text_excerpt = scene.get('text_excerpt', '')
                if text_excerpt and len(text_excerpt) > 20:
                    # Try exact match first
                    if text_excerpt in content:
                        insert_pos = content.find(text_excerpt) + len(text_excerpt)
                    else:
                        # Try first 50 chars as fuzzy match
                        short_excerpt = text_excerpt[:50]
                        if short_excerpt in content:
                            insert_pos = content.find(short_excerpt) + len(short_excerpt)
            
            # Fallback: distribute evenly across paragraphs
            if insert_pos is None and total_paragraphs > 1:
                # Calculate paragraph index based on scene position
                para_index = int((scene_index + 1) * total_paragraphs / (total_images + 1))
                para_index = min(para_index, total_paragraphs - 1)
                
                # Find position after this paragraph
                current_pos = 0
                for i, para in enumerate(paragraphs[:para_index + 1]):
                    current_pos += len(para) + 2  # +2 for \n\n
                insert_pos = current_pos - 2  # Before the next \n\n
            
            # Last fallback: append at end
            if insert_pos is None:
                insert_pos = len(content)
            
            # Avoid duplicate positions
            while insert_pos in used_positions:
                insert_pos += 1
            used_positions.add(insert_pos)
            
            # Generate figure number based on style
            if numbering_style == 'per_chapter':
                figure_num = f"{chapter.chapter_number}.{figure_counter}"
            else:
                figure_num = str(global_figure_offset + figure_counter)
            
            # Use existing caption or auto-generate from scene title
            caption = img.caption if img.caption else scene_title
            
            # Auto-save caption if not set
            if not img.caption:
                img.caption = scene_title
                img.save(update_fields=['caption'])
            
            # Use local image URL if available, fallback to external URL
            if img.image and hasattr(img.image, 'url'):
                img_src = img.image.url
            else:
                img_src = img.image_url
            
            # Build markdown with figure caption
            image_md = f"\n\n![Abb. {figure_num}: {caption}]({img_src})\n*Abb. {figure_num}: {caption}*\n"
            insertions.append((insert_pos, image_md, scene_title, img))
            logger.info(f"[insert_chapter_images] Scheduling Abb. {figure_num}: '{caption}' at position {insert_pos}")
        
        # Sort insertions by position (reverse to maintain positions)
        insertions.sort(key=lambda x: x[0], reverse=True)
        
        # Apply insertions
        for pos, img_md, title, _ in insertions:
            content = content[:pos] + img_md + content[pos:]
            images_inserted += 1
            logger.info(f"[insert_chapter_images] Inserted image for '{title}'")
        
        if images_inserted > 0:
            chapter.content = content
            chapter.save()
        
        return JsonResponse({
            'success': True,
            'images_inserted': images_inserted,
            'message': f'{images_inserted} Bilder in Kapitel eingefügt'
        })
        
    except Exception as e:
        logger.error(f"Insert chapter images failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def update_illustration_caption(request, illustration_id):
    """Update the caption of an illustration."""
    from .models import ChapterIllustration
    import json
    
    illustration = get_object_or_404(ChapterIllustration, id=illustration_id)
    
    try:
        data = json.loads(request.body)
        caption = data.get('caption', '').strip()
        
        illustration.caption = caption
        illustration.save(update_fields=['caption'])
        
        return JsonResponse({
            'success': True,
            'caption': caption,
            'message': 'Abbildungstext gespeichert'
        })
        
    except Exception as e:
        logger.error(f"Update caption failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def remove_chapter_images(request, project_id, chapter_id):
    """Remove all image markdown from chapter text."""
    import re
    
    chapter = get_object_or_404(BookChapters, id=chapter_id, project_id=project_id)
    
    try:
        content = chapter.content or ''
        
        # Count existing images
        image_pattern = r'!\[.*?\]\(.*?\)'
        existing_images = re.findall(image_pattern, content)
        
        if not existing_images:
            return JsonResponse({
                'success': False,
                'error': 'Keine Bilder im Kapitel gefunden.'
            }, status=400)
        
        # Remove all image markdown
        content = re.sub(image_pattern, '', content)
        # Clean up extra blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        chapter.content = content
        chapter.save()
        
        return JsonResponse({
            'success': True,
            'images_removed': len(existing_images),
            'message': f'{len(existing_images)} Bilder aus Kapitel entfernt'
        })
        
    except Exception as e:
        logger.error(f"Remove chapter images failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
def chapter_preview_with_images(request, project_id, chapter_id):
    """Render chapter content with images as HTML preview."""
    import markdown
    
    chapter = get_object_or_404(BookChapters, id=chapter_id, project_id=project_id)
    project = chapter.project
    
    content = chapter.content or ''
    
    # Convert markdown to HTML
    html_content = markdown.markdown(content, extensions=['extra', 'nl2br'])
    
    return render(request, 'writing_hub/chapter_preview.html', {
        'project': project,
        'chapter': chapter,
        'html_content': html_content,
    })


@require_http_methods(["GET"])
def generate_figure_index(request, project_id):
    """Generate figure index (Abbildungsverzeichnis) for a project."""
    from .models import ChapterIllustration
    
    project = get_object_or_404(BookProjects, id=project_id)
    chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
    
    numbering_style = getattr(project, 'figure_numbering_style', 'global')
    
    figures = []
    global_counter = 0
    
    for chapter in chapters:
        chapter_counter = 0
        illustrations = ChapterIllustration.objects.filter(
            chapter=chapter,
            is_selected=True,
            status='completed'
        ).order_by('position_index')
        
        for illust in illustrations:
            global_counter += 1
            chapter_counter += 1
            
            if numbering_style == 'per_chapter':
                figure_num = f"{chapter.chapter_number}.{chapter_counter}"
            else:
                figure_num = str(global_counter)
            
            caption = illust.caption or f"Szene {illust.position_index + 1}"
            
            figures.append({
                'number': figure_num,
                'caption': caption,
                'chapter_title': chapter.title,
                'chapter_number': chapter.chapter_number,
                'image_url': illust.image_url,
            })
    
    # Generate markdown for figure index
    index_md = "# Abbildungsverzeichnis\n\n"
    for fig in figures:
        index_md += f"**Abb. {fig['number']}:** {fig['caption']} (Kapitel {fig['chapter_number']})\n\n"
    
    return JsonResponse({
        'success': True,
        'figures': figures,
        'total': len(figures),
        'markdown': index_md,
    })


# =============================================================================
# LLM MANAGEMENT
# =============================================================================

def llm_setup(request):
    """LLM Setup page with presets for local LLMs"""
    from apps.bfagent.models import Llms
    
    llms = Llms.objects.all().order_by('-is_active', 'provider', 'name')
    
    # Presets for quick setup
    presets = [
        {
            'name': 'Ollama - Llama 3.1 8B',
            'provider': 'ollama',
            'endpoint': 'http://localhost:11434',
            'model': 'llama3.1',
            'description': 'Schnelles lokales Modell, gut für Tests'
        },
        {
            'name': 'Ollama - Mistral 7B',
            'provider': 'ollama',
            'endpoint': 'http://localhost:11434',
            'model': 'mistral',
            'description': 'Schnell, gute Qualität für kreatives Schreiben'
        },
        {
            'name': 'Ollama - Dolphin Mixtral (NSFW)',
            'provider': 'ollama',
            'endpoint': 'http://localhost:11434',
            'model': 'dolphin-mixtral',
            'description': 'Uncensored Modell für erwachsene Inhalte'
        },
        {
            'name': 'Ollama - Nous Hermes 2 (NSFW)',
            'provider': 'ollama',
            'endpoint': 'http://localhost:11434',
            'model': 'nous-hermes2',
            'description': 'Uncensored, gut für Storytelling'
        },
        {
            'name': 'Ollama - Mythomist (NSFW)',
            'provider': 'ollama',
            'endpoint': 'http://localhost:11434',
            'model': 'mythomist',
            'description': 'Spezialisiert auf Fantasy & kreatives Schreiben'
        },
        {
            'name': 'vLLM Server',
            'provider': 'vllm',
            'endpoint': 'http://localhost:8000',
            'model': '',
            'description': 'Schneller Inference-Server (Model-Name eintragen)'
        },
    ]
    
    context = {
        'llms': llms,
        'presets': presets,
    }
    return render(request, 'writing_hub/llm_setup.html', context)


@require_http_methods(["POST"])
def llm_add(request):
    """Add a new LLM from preset or custom"""
    from apps.bfagent.models import Llms
    
    try:
        data = json.loads(request.body)
        
        # Check if name already exists
        name = data.get('name', '').strip()
        if Llms.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'error': f'LLM mit Namen "{name}" existiert bereits'})
        
        llm = Llms.objects.create(
            name=name,
            provider=data.get('provider', 'ollama'),
            api_endpoint=data.get('endpoint', 'http://localhost:11434'),
            llm_name=data.get('model', ''),
            api_key=data.get('api_key', ''),
            is_active=True,
        )
        
        return JsonResponse({
            'success': True,
            'message': f'LLM "{llm.name}" erstellt',
            'llm_id': llm.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def llm_test(request, llm_id):
    """Test an LLM connection"""
    from apps.bfagent.models import Llms
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    
    llm = get_object_or_404(Llms, id=llm_id)
    
    try:
        req = LlmRequest(
            provider=llm.provider or 'ollama',
            api_endpoint=llm.api_endpoint or 'http://localhost:11434',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'llama3.1',
            system='Du bist ein hilfreicher Assistent.',
            prompt='Antworte mit genau einem Wort: Hallo',
            temperature=0.1,
            max_tokens=50,
        )
        
        response = generate_text(req)
        
        if response.get('ok'):
            return JsonResponse({
                'success': True,
                'message': 'Verbindung erfolgreich!',
                'response': response.get('text', '')[:100],
                'latency_ms': response.get('latency_ms')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': response.get('error', 'Unbekannter Fehler')
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# PROMPT SYSTEM VIEWS
# =============================================================================

def prompt_system_setup(request, project_id):
    """Prompt system setup page with AI assistance"""
    from .models_prompt_system import (
        PromptMasterStyle, PromptCharacter, PromptLocation,
        PromptCulturalElement, PromptSceneTemplate
    )
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        master_style = PromptMasterStyle.objects.get(project=project)
    except PromptMasterStyle.DoesNotExist:
        master_style = None
    
    context = {
        'project': project,
        'master_style': master_style,
        'has_master_style': master_style is not None,
        'characters': PromptCharacter.objects.filter(project=project, is_active=True),
        'locations': PromptLocation.objects.filter(project=project, is_active=True),
        'cultural_elements': PromptCulturalElement.objects.filter(project=project, is_active=True),
        'scene_templates': PromptSceneTemplate.objects.filter(project=project, is_active=True),
    }
    
    return render(request, 'writing_hub/prompt_system_setup.html', context)


@require_http_methods(["POST"])
def save_master_style(request, project_id):
    """Save or update master style"""
    from .models_prompt_system import PromptMasterStyle
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        
        master_style, created = PromptMasterStyle.objects.update_or_create(
            project=project,
            defaults={
                'name': data.get('name', 'Unbenannt'),
                'preset': data.get('preset', 'custom'),
                'style_base_prompt': data.get('style_base_prompt', ''),
                'cultural_context': data.get('cultural_context', ''),
                'artistic_references': data.get('artistic_references', ''),
                'master_prompt': data.get('master_prompt', ''),
                'negative_prompt': data.get('negative_prompt', ''),
                'default_width': int(data.get('default_width', 1024)),
                'default_height': int(data.get('default_height', 768)),
                'guidance_scale': float(data.get('guidance_scale', 7.5)),
                'inference_steps': int(data.get('inference_steps', 28)),
            }
        )
        
        # Return the current master prompt for display
        return JsonResponse({
            'success': True,
            'message': 'Master-Stil gespeichert',
            'id': master_style.id,
            'master_prompt': master_style.get_full_style_prompt()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def generate_master_style_preview(request, project_id):
    """Generate a preview image for the master style using ComfyUI"""
    from .models_prompt_system import PromptMasterStyle
    from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
    from django.core.files.base import ContentFile
    from django.utils import timezone
    import base64
    import asyncio
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        master_style = PromptMasterStyle.objects.get(project=project)
    except PromptMasterStyle.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Kein Master-Stil für dieses Projekt definiert. Bitte zuerst speichern.'
        }, status=400)
    
    try:
        # Build preview prompt
        preview_prompt = master_style.get_preview_prompt()
        
        # Initialize ComfyUI handler
        handler = ComfyUIHandler()
        
        # Check if ComfyUI is available
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            is_available = loop.run_until_complete(handler.check_connection())
            if not is_available:
                return JsonResponse({
                    'success': False,
                    'error': 'ComfyUI ist nicht erreichbar. Bitte starten Sie ComfyUI auf localhost:8181.'
                }, status=503)
            
            # Generate preview image
            result = loop.run_until_complete(handler.generate_image(
                prompt=preview_prompt,
                negative_prompt=master_style.negative_prompt,
                width=master_style.default_width,
                height=master_style.default_height,
                steps=master_style.inference_steps,
                cfg=master_style.guidance_scale,
            ))
        finally:
            loop.close()
        
        if result.get('success'):
            # Save the generated image
            image_data = base64.b64decode(result['image_base64'])
            filename = f"preview_{project_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # Delete old preview if exists
            if master_style.preview_image:
                master_style.preview_image.delete(save=False)
            
            master_style.preview_image.save(filename, ContentFile(image_data), save=False)
            master_style.preview_generated_at = timezone.now()
            master_style.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Vorschaubild erfolgreich generiert',
                'preview_url': master_style.preview_image.url,
                'generated_at': master_style.preview_generated_at.isoformat(),
                'generation_time': result.get('generation_time_seconds', 0)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Bildgenerierung fehlgeschlagen')
            }, status=500)
            
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False, 
            'error': f'Fehler bei der Vorschau-Generierung: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def save_prompt_character(request, project_id):
    """Save or update a character"""
    from .models_prompt_system import PromptCharacter
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        char_id = data.get('id')
        
        if char_id:
            character = get_object_or_404(PromptCharacter, id=char_id, project=project)
            for key, value in data.items():
                if key != 'id' and hasattr(character, key):
                    setattr(character, key, value)
            character.save()
        else:
            character = PromptCharacter.objects.create(
                project=project,
                name=data.get('name', ''),
                role=data.get('role', 'supporting'),
                appearance_prompt=data.get('appearance_prompt', ''),
                clothing_prompt=data.get('clothing_prompt', ''),
                props_prompt=data.get('props_prompt', ''),
                expression_default=data.get('expression_default', ''),
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Charakter gespeichert',
            'id': character.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def delete_prompt_character(request, project_id, character_id):
    """Delete a character"""
    from .models_prompt_system import PromptCharacter
    
    project = get_object_or_404(BookProjects, id=project_id)
    character = get_object_or_404(PromptCharacter, id=character_id, project=project)
    character.delete()
    
    return JsonResponse({'success': True})


@require_http_methods(["GET"])
def get_prompt_character(request, project_id, character_id):
    """Get character data for editing"""
    from .models_prompt_system import PromptCharacter
    
    project = get_object_or_404(BookProjects, id=project_id)
    character = get_object_or_404(PromptCharacter, id=character_id, project=project)
    
    return JsonResponse({
        'success': True,
        'character': {
            'id': character.id,
            'name': character.name,
            'role': character.role,
            'appearance_prompt': character.appearance_prompt,
            'clothing_prompt': character.clothing_prompt,
            'props_prompt': character.props_prompt,
            'expression_default': character.expression_default,
        }
    })


@require_http_methods(["GET"])
def get_prompt_location(request, project_id, location_id):
    """Get location data for editing"""
    from .models_prompt_system import PromptLocation
    
    project = get_object_or_404(BookProjects, id=project_id)
    location = get_object_or_404(PromptLocation, id=location_id, project=project)
    
    return JsonResponse({
        'success': True,
        'location': {
            'id': location.id,
            'name': location.name,
            'location_type': location.location_type,
            'environment_prompt': location.environment_prompt,
            'lighting_default': location.lighting_default,
            'atmosphere_prompt': location.atmosphere_prompt,
        }
    })


@require_http_methods(["POST"])
def optimize_location_with_ai(request, project_id):
    """Optimize location prompts using AI"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    from apps.bfagent.models import Llms
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '')
        location_type = data.get('location_type', '')
        environment = data.get('environment_prompt', '')
        lighting = data.get('lighting_default', '')
        atmosphere = data.get('atmosphere_prompt', '')
        
        # Get active LLM
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({
                'success': False, 
                'error': 'Kein aktives LLM konfiguriert.'
            }, status=400)
        
        system_prompt = """Du bist ein Experte für Bildgenerierung und Stable Diffusion Prompts.
Optimiere die Ort-Beschreibungen für konsistente, hochwertige Illustrationen.

WICHTIGE REGELN:
1. Alle Prompts müssen auf ENGLISCH sein (für Stable Diffusion)
2. Verwende beschreibende, visuelle Begriffe für Umgebung, Licht und Atmosphäre
3. Füge Details hinzu die für konsistente Darstellung wichtig sind
4. Behalte den Kern des Ortes bei, aber verbessere die Formulierung
5. Halte jeden Prompt fokussiert und prägnant (max 2-3 Sätze)

Antworte NUR mit einem JSON-Objekt:
{
    "environment_prompt": "Optimierte Umgebungsbeschreibung (Englisch)",
    "lighting_default": "Optimierte Beleuchtung (Englisch)",
    "atmosphere_prompt": "Optimierte Atmosphäre (Englisch)",
    "explanation": "Kurze Erklärung der Änderungen (Deutsch)"
}"""

        user_prompt = f"""Ort: {name}
Typ: {location_type}

Aktuelle Beschreibungen:
- Umgebung: {environment}
- Beleuchtung: {lighting}
- Atmosphäre: {atmosphere}

Bitte optimiere diese Prompts für Stable Diffusion Bildgenerierung."""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=user_prompt,
            temperature=0.7,
            max_tokens=1000,
        )
        
        response = generate_text(req)
        
        if not response.get('ok'):
            return JsonResponse({
                'success': False, 
                'error': f"LLM-Fehler: {response.get('error', 'Unbekannter Fehler')}"
            }, status=500)
        
        text = response.get('text', '')
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return JsonResponse({
                'success': False, 
                'error': 'KI-Antwort konnte nicht verarbeitet werden'
            }, status=500)
        
        ai_result = json.loads(json_match.group())
        
        return JsonResponse({
            'success': True,
            'optimized': {
                'environment_prompt': ai_result.get('environment_prompt', environment),
                'lighting_default': ai_result.get('lighting_default', lighting),
                'atmosphere_prompt': ai_result.get('atmosphere_prompt', atmosphere),
            },
            'explanation': ai_result.get('explanation', 'Prompts wurden optimiert.')
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False, 
            'error': f'JSON-Parsing-Fehler: {str(e)}'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def generate_location_preview(request, project_id, location_id):
    """Generate a preview image for a location using ComfyUI"""
    from .models_prompt_system import PromptLocation, PromptMasterStyle
    from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
    from django.core.files.base import ContentFile
    from django.utils import timezone
    import base64
    import asyncio
    
    project = get_object_or_404(BookProjects, id=project_id)
    location = get_object_or_404(PromptLocation, id=location_id, project=project)
    
    try:
        # Get master style for consistent styling
        try:
            master_style = PromptMasterStyle.objects.get(project=project)
            style_prompt = master_style.style_base_prompt or ''
            negative_prompt = master_style.negative_prompt or 'blurry, low quality, text, watermark'
            width = master_style.default_width or 1024
            height = master_style.default_height or 768  # Landscape format for locations
            steps = master_style.inference_steps or 28
            cfg = master_style.guidance_scale or 7.5
        except PromptMasterStyle.DoesNotExist:
            style_prompt = 'highly detailed, masterpiece, best quality'
            negative_prompt = 'blurry, low quality, text, watermark, ugly, deformed'
            width = 1024
            height = 768
            steps = 28
            cfg = 7.5
        
        # Build location preview prompt
        preview_parts = [
            location.environment_prompt,
        ]
        
        if location.lighting_default:
            preview_parts.append(location.lighting_default)
        if location.atmosphere_prompt:
            preview_parts.append(location.atmosphere_prompt)
        
        # Add style and quality
        preview_parts.append(style_prompt)
        preview_parts.append("scenic view, detailed environment, cinematic composition")
        
        preview_prompt = ", ".join(filter(None, preview_parts))
        
        # Initialize ComfyUI handler
        handler = ComfyUIHandler()
        
        # Check if ComfyUI is available
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            is_available = loop.run_until_complete(handler.check_connection())
            if not is_available:
                return JsonResponse({
                    'success': False,
                    'error': 'ComfyUI ist nicht erreichbar. Bitte starten Sie ComfyUI auf localhost:8181.'
                }, status=503)
            
            # Generate preview image (landscape format)
            result = loop.run_until_complete(handler.generate_image(
                prompt=preview_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
            ))
        finally:
            loop.close()
        
        if result.get('success'):
            # Save the generated image
            image_data = base64.b64decode(result['image_base64'])
            filename = f"location_{location_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # Delete old preview if exists
            if location.preview_image:
                location.preview_image.delete(save=False)
            
            location.preview_image.save(filename, ContentFile(image_data), save=False)
            location.preview_generated_at = timezone.now()
            location.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Vorschau für {location.name} erfolgreich generiert',
                'preview_url': location.preview_image.url,
                'generated_at': location.preview_generated_at.isoformat(),
                'generation_time': result.get('generation_time_seconds', 0)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Vorschau-Generierung fehlgeschlagen')
            }, status=500)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': f'Fehler bei der Vorschau-Generierung: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def optimize_character_with_ai(request, project_id):
    """Optimize character prompts using AI"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    from apps.bfagent.models import Llms
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '')
        role = data.get('role', '')
        appearance = data.get('appearance_prompt', '')
        clothing = data.get('clothing_prompt', '')
        props = data.get('props_prompt', '')
        expression = data.get('expression_default', '')
        
        # Get active LLM
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({
                'success': False, 
                'error': 'Kein aktives LLM konfiguriert.'
            }, status=400)
        
        system_prompt = """Du bist ein Experte für Bildgenerierung und Stable Diffusion Prompts.
Optimiere die Charakter-Beschreibungen für konsistente, hochwertige Illustrationen.

WICHTIGE REGELN:
1. Alle Prompts müssen auf ENGLISCH sein (für Stable Diffusion)
2. Verwende beschreibende, visuelle Begriffe
3. Füge Details hinzu die für konsistente Darstellung wichtig sind
4. Behalte den Kern des Charakters bei, aber verbessere die Formulierung
5. Halte jeden Prompt fokussiert und prägnant (max 2-3 Sätze)

Antworte NUR mit einem JSON-Objekt:
{
    "appearance_prompt": "Optimierte Erscheinungsbeschreibung (Englisch)",
    "clothing_prompt": "Optimierte Kleidungsbeschreibung (Englisch)",
    "props_prompt": "Optimierte Props (Englisch, kurz)",
    "expression_default": "Optimierter Ausdruck (Englisch, 2-4 Wörter)",
    "explanation": "Kurze Erklärung der Änderungen (Deutsch)"
}"""

        user_prompt = f"""Charakter: {name}
Rolle: {role}

Aktuelle Beschreibungen:
- Erscheinung: {appearance}
- Kleidung: {clothing}
- Gegenstände: {props}
- Ausdruck: {expression}

Bitte optimiere diese Prompts für Stable Diffusion Bildgenerierung."""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=user_prompt,
            temperature=0.7,
            max_tokens=1000,
        )
        
        response = generate_text(req)
        
        if not response.get('ok'):
            return JsonResponse({
                'success': False, 
                'error': f"LLM-Fehler: {response.get('error', 'Unbekannter Fehler')}"
            }, status=500)
        
        text = response.get('text', '')
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return JsonResponse({
                'success': False, 
                'error': 'KI-Antwort konnte nicht verarbeitet werden'
            }, status=500)
        
        ai_result = json.loads(json_match.group())
        
        return JsonResponse({
            'success': True,
            'optimized': {
                'appearance_prompt': ai_result.get('appearance_prompt', appearance),
                'clothing_prompt': ai_result.get('clothing_prompt', clothing),
                'props_prompt': ai_result.get('props_prompt', props),
                'expression_default': ai_result.get('expression_default', expression),
            },
            'explanation': ai_result.get('explanation', 'Prompts wurden optimiert.')
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False, 
            'error': f'JSON-Parsing-Fehler: {str(e)}'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def generate_character_portrait(request, project_id, character_id):
    """Generate a portrait image for a character using ComfyUI"""
    from .models_prompt_system import PromptCharacter, PromptMasterStyle
    from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
    from django.core.files.base import ContentFile
    from django.utils import timezone
    import base64
    import asyncio
    
    project = get_object_or_404(BookProjects, id=project_id)
    character = get_object_or_404(PromptCharacter, id=character_id, project=project)
    
    try:
        # Get master style for consistent styling
        try:
            master_style = PromptMasterStyle.objects.get(project=project)
            style_prompt = master_style.style_base_prompt or ''
            negative_prompt = master_style.negative_prompt or 'blurry, low quality, text, watermark'
            width = master_style.default_width or 768
            height = master_style.default_height or 1024  # Portrait format
            steps = master_style.inference_steps or 28
            cfg = master_style.guidance_scale or 7.5
        except PromptMasterStyle.DoesNotExist:
            style_prompt = 'highly detailed, masterpiece, best quality'
            negative_prompt = 'blurry, low quality, text, watermark, ugly, deformed'
            width = 768
            height = 1024
            steps = 28
            cfg = 7.5
        
        # Build character portrait prompt
        portrait_parts = [
            "portrait of a character",
            character.appearance_prompt,
        ]
        
        if character.clothing_prompt:
            portrait_parts.append(character.clothing_prompt)
        if character.expression_default:
            portrait_parts.append(character.expression_default)
        if character.props_prompt:
            portrait_parts.append(character.props_prompt)
        
        # Add style and quality
        portrait_parts.append(style_prompt)
        portrait_parts.append("portrait photography, upper body, looking at viewer, detailed face")
        
        portrait_prompt = ", ".join(filter(None, portrait_parts))
        
        # Initialize ComfyUI handler
        handler = ComfyUIHandler()
        
        # Check if ComfyUI is available
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            is_available = loop.run_until_complete(handler.check_connection())
            if not is_available:
                return JsonResponse({
                    'success': False,
                    'error': 'ComfyUI ist nicht erreichbar. Bitte starten Sie ComfyUI auf localhost:8181.'
                }, status=503)
            
            # Generate portrait image (portrait format)
            result = loop.run_until_complete(handler.generate_image(
                prompt=portrait_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                seed=character.reference_seed if character.reference_seed else None,  # Handler will generate random if None
            ))
        finally:
            loop.close()
        
        if result.get('success'):
            # Save the generated image
            image_data = base64.b64decode(result['image_base64'])
            filename = f"portrait_{character_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # Delete old portrait if exists
            if character.portrait_image:
                character.portrait_image.delete(save=False)
            
            character.portrait_image.save(filename, ContentFile(image_data), save=False)
            character.portrait_generated_at = timezone.now()
            
            # Save the seed for consistency in future generations
            if result.get('seed') and not character.reference_seed:
                character.reference_seed = result.get('seed')
            
            character.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Portrait für {character.name} erfolgreich generiert',
                'portrait_url': character.portrait_image.url,
                'generated_at': character.portrait_generated_at.isoformat(),
                'generation_time': result.get('generation_time_seconds', 0)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Portrait-Generierung fehlgeschlagen')
            }, status=500)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': f'Fehler bei der Portrait-Generierung: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def save_prompt_location(request, project_id):
    """Save or update a location"""
    from .models_prompt_system import PromptLocation
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        loc_id = data.get('id')
        
        if loc_id:
            location = get_object_or_404(PromptLocation, id=loc_id, project=project)
            for key, value in data.items():
                if key != 'id' and hasattr(location, key):
                    setattr(location, key, value)
            location.save()
        else:
            location = PromptLocation.objects.create(
                project=project,
                name=data.get('name', ''),
                location_type=data.get('location_type', 'exterior'),
                environment_prompt=data.get('environment_prompt', ''),
                lighting_default=data.get('lighting_default', ''),
                atmosphere_prompt=data.get('atmosphere_prompt', ''),
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Ort gespeichert',
            'id': location.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def delete_prompt_location(request, project_id, location_id):
    """Delete a location"""
    from .models_prompt_system import PromptLocation
    
    project = get_object_or_404(BookProjects, id=project_id)
    location = get_object_or_404(PromptLocation, id=location_id, project=project)
    location.delete()
    
    return JsonResponse({'success': True})


@require_http_methods(["POST"])
def load_prompt_preset(request, project_id):
    """Load a predefined preset"""
    from .handlers.prompt_builder_handler import PromptPresetFactory
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        preset = data.get('preset', '')
        
        if preset == 'kazakh_fairytale':
            result = PromptPresetFactory.create_kazakh_fairytale_preset(project_id)
            return JsonResponse({
                'success': True,
                'message': f"Preset '{preset}' geladen",
                'created': {
                    'master_style': result['master_style'].name,
                    'characters': len(result['characters']),
                    'locations': len(result['locations']),
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f"Preset '{preset}' noch nicht implementiert"
            }, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def generate_prompt_system_with_ai(request, project_id):
    """Generate prompt system using AI based on description"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    from apps.bfagent.models import Llms
    from .models_prompt_system import PromptMasterStyle, PromptCharacter, PromptLocation
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        description = data.get('description', '')
        
        if not description:
            return JsonResponse({'success': False, 'error': 'Beschreibung fehlt'}, status=400)
        
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM konfiguriert'}, status=400)
        
        system_prompt = """Du bist ein Experte für Bildgenerierungs-Prompts. 
Basierend auf der Buchbeschreibung, erstelle ein JSON-Objekt mit:
1. master_style: {name, style_base_prompt, cultural_context, artistic_references, negative_prompt}
2. characters: [{name, role (protagonist/antagonist/mentor/supporting), appearance_prompt, clothing_prompt}]
3. locations: [{name, location_type (interior/exterior/landscape), environment_prompt, atmosphere_prompt}]

Antworte NUR mit validem JSON, keine Erklärungen."""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=f"Buchbeschreibung:\n{description}",
            temperature=0.7,
            max_tokens=2000,
        )
        
        response = generate_text(req)
        
        if not response.get('ok'):
            return JsonResponse({'success': False, 'error': response.get('error', 'LLM-Fehler')}, status=500)
        
        text = response.get('text', '')
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return JsonResponse({'success': False, 'error': 'Keine gültige JSON-Antwort'}, status=500)
        
        ai_data = json.loads(json_match.group())
        
        if 'master_style' in ai_data:
            ms = ai_data['master_style']
            PromptMasterStyle.objects.update_or_create(
                project=project,
                defaults={
                    'name': ms.get('name', 'KI-generiert'),
                    'preset': 'custom',
                    'style_base_prompt': ms.get('style_base_prompt', ''),
                    'cultural_context': ms.get('cultural_context', ''),
                    'artistic_references': ms.get('artistic_references', ''),
                    'negative_prompt': ms.get('negative_prompt', 'blurry, low quality'),
                }
            )
        
        chars_created = 0
        for char in ai_data.get('characters', []):
            PromptCharacter.objects.update_or_create(
                project=project,
                name=char.get('name', ''),
                defaults={
                    'role': char.get('role', 'supporting'),
                    'appearance_prompt': char.get('appearance_prompt', ''),
                    'clothing_prompt': char.get('clothing_prompt', ''),
                }
            )
            chars_created += 1
        
        locs_created = 0
        for loc in ai_data.get('locations', []):
            PromptLocation.objects.update_or_create(
                project=project,
                name=loc.get('name', ''),
                defaults={
                    'location_type': loc.get('location_type', 'exterior'),
                    'environment_prompt': loc.get('environment_prompt', ''),
                    'atmosphere_prompt': loc.get('atmosphere_prompt', ''),
                }
            )
            locs_created += 1
        
        return JsonResponse({
            'success': True,
            'message': 'Illustration-System mit KI generiert',
            'created': {'characters': chars_created, 'locations': locs_created}
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'JSON-Fehler: {e}'}, status=500)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def extract_characters_from_book(request, project_id):
    """Extract characters from book content using AI"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    from apps.bfagent.models import Llms
    from .models_prompt_system import PromptCharacter
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
        content = "\n\n".join([
            f"Kapitel {ch.chapter_number}: {ch.title}\n{ch.content[:1000] if ch.content else ''}"
            for ch in chapters[:5]
        ])
        
        if len(content) < 100:
            return JsonResponse({'success': False, 'error': 'Zu wenig Buchinhalt'}, status=400)
        
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM'}, status=400)
        
        system_prompt = """Extrahiere Charaktere aus dem Text. Antworte NUR mit JSON-Array:
[{"name": "...", "role": "protagonist/antagonist/mentor/supporting", "appearance_prompt": "...", "clothing_prompt": "..."}]"""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=f"Buchinhalt:\n{content[:3000]}",
            temperature=0.5,
            max_tokens=1500,
        )
        
        response = generate_text(req)
        if not response.get('ok'):
            return JsonResponse({'success': False, 'error': response.get('error')}, status=500)
        
        text = response.get('text', '')
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if not json_match:
            return JsonResponse({'success': False, 'error': 'Keine Charaktere gefunden'}, status=400)
        
        characters = json.loads(json_match.group())
        created = 0
        for char in characters:
            _, was_created = PromptCharacter.objects.update_or_create(
                project=project, name=char.get('name', ''),
                defaults={
                    'role': char.get('role', 'supporting'),
                    'appearance_prompt': char.get('appearance_prompt', ''),
                    'clothing_prompt': char.get('clothing_prompt', ''),
                }
            )
            if was_created:
                created += 1
        
        return JsonResponse({'success': True, 'count': created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def extract_elements_from_book(request, project_id):
    """Extract cultural elements from book content using AI"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    from apps.bfagent.models import Llms
    from .models_prompt_system import PromptCulturalElement
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
        content = "\n\n".join([
            f"Kapitel {ch.chapter_number}: {ch.title}\n{ch.content[:1000] if ch.content else ''}"
            for ch in chapters[:5]
        ])
        
        if len(content) < 100:
            return JsonResponse({'success': False, 'error': 'Zu wenig Buchinhalt'}, status=400)
        
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM'}, status=400)
        
        system_prompt = """Extrahiere kulturelle Elemente aus dem Text (Kleidung, Architektur, Gegenstände, Tiere, Natur, Symbole, Essen, Musik).
Antworte NUR mit JSON-Array:
[{
    "term_local": "Lokaler Begriff",
    "term_english": "English term",
    "term_german": "Deutscher Begriff",
    "category": "clothing/architecture/objects/animals/nature/symbols/food/music",
    "description": "Beschreibung",
    "visual_prompt": "Visual description for image generation (English)"
}]"""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=f"Buchinhalt:\n{content[:3000]}",
            temperature=0.5,
            max_tokens=2000,
        )
        
        response = generate_text(req)
        if not response.get('ok'):
            return JsonResponse({'success': False, 'error': response.get('error')}, status=500)
        
        text = response.get('text', '')
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if not json_match:
            return JsonResponse({'success': False, 'error': 'Keine Elemente gefunden'}, status=400)
        
        elements = json.loads(json_match.group())
        created = 0
        for elem in elements:
            _, was_created = PromptCulturalElement.objects.update_or_create(
                project=project, term_local=elem.get('term_local', ''),
                defaults={
                    'term_english': elem.get('term_english', ''),
                    'term_german': elem.get('term_german', ''),
                    'category': elem.get('category', 'objects'),
                    'description': elem.get('description', ''),
                    'visual_prompt': elem.get('visual_prompt', ''),
                }
            )
            if was_created:
                created += 1
        
        return JsonResponse({'success': True, 'count': created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def suggest_style_from_book(request, project_id):
    """Auto-generate style suggestion based on existing book data"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    from apps.bfagent.models import Llms
    from .models_prompt_system import PromptMasterStyle, PromptCharacter, PromptLocation
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        # Gather all available book data
        book_info = {
            'title': project.title or '',
            'genre': project.genre or '',
            'description': project.description or '',
            'tagline': project.tagline or '',
            'target_audience': project.target_audience or '',
            'story_themes': project.story_themes or '',
            'setting_time': project.setting_time or '',
            'setting_location': project.setting_location or '',
            'atmosphere_tone': project.atmosphere_tone or '',
            'protagonist_concept': project.protagonist_concept or '',
            'antagonist_concept': project.antagonist_concept or '',
            'inspiration_sources': project.inspiration_sources or '',
            'unique_elements': project.unique_elements or '',
        }
        
        # Get chapters content for more context
        chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')[:3]
        chapter_excerpts = "\n".join([
            f"Kapitel {ch.chapter_number}: {ch.title}\n{(ch.content or '')[:500]}"
            for ch in chapters if ch.content
        ])
        
        # Get existing characters
        from .models import Character
        characters = Character.objects.filter(project=project)[:5]
        char_info = ", ".join([c.name for c in characters]) if characters else ""
        
        # Build context string
        context_parts = []
        if book_info['title']:
            context_parts.append(f"Titel: {book_info['title']}")
        if book_info['genre']:
            context_parts.append(f"Genre: {book_info['genre']}")
        if book_info['description']:
            context_parts.append(f"Beschreibung: {book_info['description']}")
        if book_info['target_audience']:
            context_parts.append(f"Zielgruppe: {book_info['target_audience']}")
        if book_info['atmosphere_tone']:
            context_parts.append(f"Atmosphäre: {book_info['atmosphere_tone']}")
        if book_info['setting_time']:
            context_parts.append(f"Zeitraum: {book_info['setting_time']}")
        if book_info['setting_location']:
            context_parts.append(f"Ort: {book_info['setting_location']}")
        if book_info['story_themes']:
            context_parts.append(f"Themen: {book_info['story_themes']}")
        if book_info['protagonist_concept']:
            context_parts.append(f"Protagonist: {book_info['protagonist_concept']}")
        if book_info['inspiration_sources']:
            context_parts.append(f"Inspirationen: {book_info['inspiration_sources']}")
        if char_info:
            context_parts.append(f"Charaktere: {char_info}")
        if chapter_excerpts:
            context_parts.append(f"Kapitelausschnitte:\n{chapter_excerpts[:1000]}")
        
        book_context = "\n".join(context_parts)
        
        if len(book_context) < 50:
            return JsonResponse({
                'success': False,
                'error': 'Zu wenig Buchinformationen vorhanden. Bitte fülle zuerst Titel, Genre und Beschreibung aus.'
            }, status=400)
        
        # Get active LLM
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            # Fallback: Generate without AI based on genre
            return _generate_style_suggestion_without_ai(project, book_info)
        
        # Generate with AI
        system_prompt = """Du bist ein Experte für Buchillustrationen und Bildgenerierung.
Basierend auf den Buchinformationen, erstelle einen passenden visuellen Stil.

Antworte mit einem JSON-Objekt:
{
    "name": "Stilname (kurz, prägnant)",
    "style_base_prompt": "Detaillierter Bildstil-Prompt auf Englisch (Kunststil, Technik, Qualität)",
    "cultural_context": "Kultureller/historischer Kontext für authentische Darstellung (Englisch)",
    "artistic_references": "Künstlerische Referenzen, Stile (z.B. 'inspired by ...')",
    "negative_prompt": "Was vermieden werden soll (Englisch)",
    "preset": "fairy_tale/cinematic/watercolor/manga/realistic/custom",
    "characters": [{"name": "...", "role": "protagonist/antagonist/mentor/supporting", "appearance_prompt": "...", "clothing_prompt": "..."}],
    "locations": [{"name": "...", "location_type": "interior/exterior/landscape", "environment_prompt": "...", "atmosphere_prompt": "..."}]
}

Wähle den Stil passend zu Genre, Zielgruppe und Atmosphäre des Buches."""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=f"Buchinformationen:\n{book_context}",
            temperature=0.7,
            max_tokens=2000,
        )
        
        response = generate_text(req)
        
        if not response.get('ok'):
            # Fallback to non-AI suggestion
            return _generate_style_suggestion_without_ai(project, book_info)
        
        text = response.get('text', '')
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return _generate_style_suggestion_without_ai(project, book_info)
        
        ai_data = json.loads(json_match.group())
        
        # Save master style
        master_style, _ = PromptMasterStyle.objects.update_or_create(
            project=project,
            defaults={
                'name': ai_data.get('name', f'{project.title} Style'),
                'preset': ai_data.get('preset', 'custom'),
                'style_base_prompt': ai_data.get('style_base_prompt', ''),
                'cultural_context': ai_data.get('cultural_context', ''),
                'artistic_references': ai_data.get('artistic_references', ''),
                'negative_prompt': ai_data.get('negative_prompt', 'blurry, low quality, text, watermark'),
            }
        )
        
        # Save characters
        chars_created = 0
        for char in ai_data.get('characters', []):
            if char.get('name'):
                PromptCharacter.objects.update_or_create(
                    project=project,
                    name=char.get('name', ''),
                    defaults={
                        'role': char.get('role', 'supporting'),
                        'appearance_prompt': char.get('appearance_prompt', ''),
                        'clothing_prompt': char.get('clothing_prompt', ''),
                    }
                )
                chars_created += 1
        
        # Save locations
        locs_created = 0
        for loc in ai_data.get('locations', []):
            if loc.get('name'):
                PromptLocation.objects.update_or_create(
                    project=project,
                    name=loc.get('name', ''),
                    defaults={
                        'location_type': loc.get('location_type', 'exterior'),
                        'environment_prompt': loc.get('environment_prompt', ''),
                        'atmosphere_prompt': loc.get('atmosphere_prompt', ''),
                    }
                )
                locs_created += 1
        
        return JsonResponse({
            'success': True,
            'message': 'Stil-Vorschlag aus Buchdaten generiert',
            'data': {
                'master_style': {
                    'name': master_style.name,
                    'preset': master_style.preset,
                    'style_base_prompt': master_style.style_base_prompt,
                    'cultural_context': master_style.cultural_context,
                    'artistic_references': master_style.artistic_references,
                    'negative_prompt': master_style.negative_prompt,
                },
                'characters_created': chars_created,
                'locations_created': locs_created,
            }
        })
        
    except json.JSONDecodeError:
        return _generate_style_suggestion_without_ai(project, book_info)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _generate_style_suggestion_without_ai(project, book_info):
    """Fallback: Generate style suggestion based on genre patterns without AI"""
    from .models_prompt_system import PromptMasterStyle
    
    genre = (book_info.get('genre', '') or '').lower()
    audience = (book_info.get('target_audience', '') or '').lower()
    atmosphere = (book_info.get('atmosphere_tone', '') or '').lower()
    
    # Genre-based style mapping
    style_mappings = {
        'fantasy': {
            'name': 'Fantasy Illustration',
            'preset': 'fairy_tale',
            'style_base_prompt': 'Digital fantasy illustration, rich jewel tones, magical atmosphere, detailed backgrounds, cinematic lighting, 4K quality',
            'negative_prompt': 'blurry, low quality, text, watermark, modern elements, technology',
        },
        'märchen': {
            'name': 'Märchen-Illustration',
            'preset': 'fairy_tale',
            'style_base_prompt': 'Classic fairy tale illustration, watercolor style, soft colors, magical realism, storybook aesthetic, ornate borders',
            'negative_prompt': 'blurry, low quality, text, watermark, photorealistic, dark themes',
        },
        'sci-fi': {
            'name': 'Sci-Fi Cinematic',
            'preset': 'cinematic',
            'style_base_prompt': 'Cinematic science fiction art, futuristic technology, dramatic lighting, sleek design, high contrast, volumetric lighting',
            'negative_prompt': 'blurry, low quality, text, watermark, medieval, fantasy elements',
        },
        'romance': {
            'name': 'Romance Soft',
            'preset': 'watercolor',
            'style_base_prompt': 'Soft romantic illustration, warm pastel colors, dreamy atmosphere, gentle lighting, emotional expressions',
            'negative_prompt': 'blurry, low quality, text, watermark, violence, dark themes',
        },
        'thriller': {
            'name': 'Thriller Noir',
            'preset': 'cinematic',
            'style_base_prompt': 'Film noir style, high contrast, dramatic shadows, moody atmosphere, tension, urban settings',
            'negative_prompt': 'blurry, low quality, text, watermark, bright colors, cheerful',
        },
        'kinder': {
            'name': 'Kinderbuch-Stil',
            'preset': 'watercolor',
            'style_base_prompt': 'Children book illustration, bright cheerful colors, friendly characters, simple shapes, playful style, warm atmosphere',
            'negative_prompt': 'blurry, low quality, text, watermark, scary, violent, adult themes',
        },
        'horror': {
            'name': 'Dark Horror',
            'preset': 'cinematic',
            'style_base_prompt': 'Dark horror illustration, eerie atmosphere, muted colors, dramatic shadows, unsettling details, gothic style',
            'negative_prompt': 'blurry, low quality, text, watermark, cheerful, bright, cute',
        },
    }
    
    # Find matching style
    selected_style = None
    for key, style in style_mappings.items():
        if key in genre:
            selected_style = style
            break
    
    # Check audience for children's books
    if 'kind' in audience or 'jugend' in audience:
        selected_style = style_mappings['kinder']
    
    # Default style
    if not selected_style:
        selected_style = {
            'name': f'{project.title} Style',
            'preset': 'custom',
            'style_base_prompt': 'Professional book illustration, detailed artwork, consistent style, high quality, cinematic composition',
            'negative_prompt': 'blurry, low quality, text, watermark, ugly, deformed',
        }
    
    # Add cultural context from book data
    cultural_context = ''
    if book_info.get('setting_location'):
        cultural_context += book_info['setting_location']
    if book_info.get('setting_time'):
        cultural_context += f", {book_info['setting_time']}"
    
    # Save to database
    master_style, _ = PromptMasterStyle.objects.update_or_create(
        project=project,
        defaults={
            'name': selected_style['name'],
            'preset': selected_style['preset'],
            'style_base_prompt': selected_style['style_base_prompt'],
            'cultural_context': cultural_context,
            'artistic_references': book_info.get('inspiration_sources', ''),
            'negative_prompt': selected_style['negative_prompt'],
        }
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Stil-Vorschlag aus Genre-Vorlage generiert (ohne KI)',
        'data': {
            'master_style': {
                'name': master_style.name,
                'preset': master_style.preset,
                'style_base_prompt': master_style.style_base_prompt,
                'cultural_context': master_style.cultural_context,
                'artistic_references': master_style.artistic_references,
                'negative_prompt': master_style.negative_prompt,
            },
            'ai_used': False,
        }
    })


@require_http_methods(["POST"])
def extract_locations_from_book(request, project_id):
    """Extract locations from book content using AI"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    from apps.bfagent.models import Llms
    from .models_prompt_system import PromptLocation
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        chapters = BookChapters.objects.filter(project=project).order_by('chapter_number')
        content = "\n\n".join([
            f"Kapitel {ch.chapter_number}: {ch.title}\n{ch.content[:1000] if ch.content else ''}"
            for ch in chapters[:5]
        ])
        
        if len(content) < 100:
            return JsonResponse({'success': False, 'error': 'Zu wenig Buchinhalt'}, status=400)
        
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM'}, status=400)
        
        system_prompt = """Extrahiere Orte aus dem Text. Antworte NUR mit JSON-Array:
[{"name": "...", "location_type": "interior/exterior/landscape", "environment_prompt": "...", "atmosphere_prompt": "..."}]"""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=f"Buchinhalt:\n{content[:3000]}",
            temperature=0.5,
            max_tokens=1500,
        )
        
        response = generate_text(req)
        if not response.get('ok'):
            return JsonResponse({'success': False, 'error': response.get('error')}, status=500)
        
        text = response.get('text', '')
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if not json_match:
            return JsonResponse({'success': False, 'error': 'Keine Orte gefunden'}, status=400)
        
        locations = json.loads(json_match.group())
        created = 0
        for loc in locations:
            _, was_created = PromptLocation.objects.update_or_create(
                project=project, name=loc.get('name', ''),
                defaults={
                    'location_type': loc.get('location_type', 'exterior'),
                    'environment_prompt': loc.get('environment_prompt', ''),
                    'atmosphere_prompt': loc.get('atmosphere_prompt', ''),
                }
            )
            if was_created:
                created += 1
        
        return JsonResponse({'success': True, 'count': created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def optimize_master_style_with_ai(request, project_id):
    """Optimize master style prompt using AI based on current form values"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    from apps.bfagent.models import Llms
    from .models_prompt_system import PromptMasterStyle
    import re
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        
        # Get current form values
        style_name = data.get('name', '')
        preset = data.get('preset', 'custom')
        base_prompt = data.get('style_base_prompt', '')
        cultural_context = data.get('cultural_context', '')
        artistic_references = data.get('artistic_references', '')
        negative_prompt = data.get('negative_prompt', '')
        
        # Get active LLM
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({
                'success': False, 
                'error': 'Kein aktives LLM konfiguriert. Bitte LLM in den Einstellungen aktivieren.'
            }, status=400)
        
        # Get book context for better optimization
        book_context = f"""
Buchtitel: {project.title or 'Unbekannt'}
Genre: {project.genre or 'Nicht angegeben'}
Zielgruppe: {project.target_audience or 'Nicht angegeben'}
Atmosphäre: {project.atmosphere_tone or 'Nicht angegeben'}
Setting: {project.setting_location or ''} {project.setting_time or ''}
"""
        
        # Build optimization prompt
        system_prompt = """Du bist ein Experte für Bildgenerierung und Stable Diffusion/ComfyUI Prompts.
Deine Aufgabe: Optimiere den Master-Prompt für konsistente, hochwertige Buchillustrationen.

WICHTIGE REGELN:
1. Der Prompt muss auf ENGLISCH sein (für Stable Diffusion)
2. Kombiniere Stilname, Preset und alle Eingaben zu einem kohärenten Prompt
3. Füge technische Qualitätsmerkmale hinzu (highly detailed, masterpiece, etc.)
4. Berücksichtige das Preset für den Grundstil
5. Integriere kulturellen Kontext und künstlerische Referenzen nahtlos
6. Der Prompt sollte für JEDE Szene des Buches als Basis funktionieren

Antworte NUR mit einem JSON-Objekt:
{
    "optimized_base_prompt": "Verbesserter Basis-Stil-Prompt (Englisch, 50-100 Wörter)",
    "optimized_cultural_context": "Verbesserter kultureller Kontext (Englisch, kurz)",
    "optimized_artistic_references": "Verbesserte Referenzen (Englisch, kurz)",
    "optimized_negative_prompt": "Verbesserter Negative Prompt (Englisch)",
    "master_prompt": "KOMPLETTER kombinierter Master-Prompt aus allen Teilen (Englisch, 100-150 Wörter)",
    "explanation": "Kurze Erklärung der Änderungen (Deutsch)"
}"""

        user_prompt = f"""Buchkontext:
{book_context}

Aktueller Stil:
- Stilname: {style_name}
- Preset: {preset}
- Basis-Prompt: {base_prompt}
- Kultureller Kontext: {cultural_context}
- Künstlerische Referenzen: {artistic_references}
- Negative Prompt: {negative_prompt}

Bitte optimiere diesen Stil für professionelle Buchillustrationen."""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=user_prompt,
            temperature=0.7,
            max_tokens=1500,
        )
        
        response = generate_text(req)
        
        if not response.get('ok'):
            return JsonResponse({
                'success': False, 
                'error': f"LLM-Fehler: {response.get('error', 'Unbekannter Fehler')}"
            }, status=500)
        
        text = response.get('text', '')
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return JsonResponse({
                'success': False, 
                'error': 'KI-Antwort konnte nicht verarbeitet werden'
            }, status=500)
        
        ai_result = json.loads(json_match.group())
        
        return JsonResponse({
            'success': True,
            'optimized': {
                'style_base_prompt': ai_result.get('optimized_base_prompt', base_prompt),
                'cultural_context': ai_result.get('optimized_cultural_context', cultural_context),
                'artistic_references': ai_result.get('optimized_artistic_references', artistic_references),
                'negative_prompt': ai_result.get('optimized_negative_prompt', negative_prompt),
                'master_prompt': ai_result.get('master_prompt', ''),
            },
            'explanation': ai_result.get('explanation', 'Prompt wurde optimiert.')
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False, 
            'error': f'JSON-Parsing-Fehler: {str(e)}'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)


# =============================================================================
# PUBLISHING VIEWS
# =============================================================================

def publishing_setup(request, project_id):
    """Publishing setup page with metadata, cover, front/backmatter"""
    from .models_publishing import (
        PublishingMetadata, BookCover, FrontMatter, BackMatter, AuthorProfile
    )
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Get or create publishing metadata
    metadata, _ = PublishingMetadata.objects.get_or_create(
        project=project,
        defaults={'copyright_holder': request.user.get_full_name() or request.user.username}
    )
    
    # Get covers
    covers = BookCover.objects.filter(project=project)
    primary_cover = covers.filter(is_primary=True, cover_type='ebook').first()
    
    # Get author profile
    author_profile = None
    if request.user.is_authenticated:
        author_profile, _ = AuthorProfile.objects.get_or_create(user=request.user)
    
    # Front matter as dict for inline editing
    front_matter = {}
    for choice in FrontMatter.PageType.choices:
        fm = FrontMatter.objects.filter(project=project, page_type=choice[0]).first()
        front_matter[choice[0]] = {
            'content': fm.content if fm else '',
            'title': fm.title if fm else '',
            'is_active': fm.is_active if fm else False,
            'auto_generate': fm.auto_generate if fm else True,
        }
    
    # Back matter as dict for inline editing
    back_matter = {}
    for choice in BackMatter.PageType.choices:
        bm = BackMatter.objects.filter(project=project, page_type=choice[0]).first()
        back_matter[choice[0]] = {
            'content': bm.content if bm else '',
            'title': bm.title if bm else '',
            'is_active': bm.is_active if bm else False,
        }
    
    # Check completeness
    chapters = BookChapters.objects.filter(project=project)
    chapters_total = chapters.count()
    chapters_done = chapters.filter(status='complete').count()
    
    context = {
        'project': project,
        'metadata': metadata,
        'covers': covers,
        'primary_cover': primary_cover,
        'author_profile': author_profile,
        'front_matter': front_matter,
        'back_matter': back_matter,
        'metadata_complete': bool(metadata.isbn or metadata.publisher_name),
        'has_copyright': bool(metadata.copyright_holder and metadata.copyright_year),
        'chapters_complete': chapters_done == chapters_total and chapters_total > 0,
        'chapters_done': chapters_done,
        'chapters_total': chapters_total,
    }
    
    return render(request, 'writing_hub/publishing_setup.html', context)


@require_http_methods(["POST"])
def save_publishing_metadata(request, project_id):
    """Save publishing metadata"""
    from .models_publishing import PublishingMetadata
    
    project = get_object_or_404(BookProjects, id=project_id)
    metadata, _ = PublishingMetadata.objects.get_or_create(project=project)
    
    # Update fields from POST data
    metadata.isbn = request.POST.get('isbn', '')
    metadata.asin = request.POST.get('asin', '')
    metadata.publisher_name = request.POST.get('publisher_name', 'Selbstverlag')
    metadata.imprint = request.POST.get('imprint', '')
    metadata.copyright_year = request.POST.get('copyright_year') or None
    metadata.copyright_holder = request.POST.get('copyright_holder', '')
    metadata.language = request.POST.get('language', 'de')
    metadata.primary_bisac = request.POST.get('primary_bisac', '')
    metadata.secondary_bisac = request.POST.get('secondary_bisac', '')
    metadata.keywords = request.POST.get('keywords', '')
    metadata.content_rating = request.POST.get('content_rating', 'general')
    metadata.status = request.POST.get('status', 'draft')
    
    # Handle dates
    first_published = request.POST.get('first_published')
    if first_published:
        metadata.first_published = first_published
    this_edition = request.POST.get('this_edition')
    if this_edition:
        metadata.this_edition = this_edition
    
    metadata.save()
    
    messages.success(request, 'Metadaten gespeichert!')
    return redirect('writing_hub:publishing_setup', project_id=project_id)


@require_http_methods(["POST"])
def save_author_profile(request, project_id):
    """Save author profile"""
    from .models_publishing import AuthorProfile
    
    project = get_object_or_404(BookProjects, id=project_id)
    profile, _ = AuthorProfile.objects.get_or_create(user=request.user)
    
    profile.pen_name = request.POST.get('pen_name', '')
    profile.bio_short = request.POST.get('bio_short', '')
    profile.bio_long = request.POST.get('bio_long', '')
    profile.website = request.POST.get('website', '')
    profile.save()
    
    messages.success(request, 'Autorenprofil gespeichert!')
    return redirect('writing_hub:publishing_setup', project_id=project_id)


@require_http_methods(["POST"])
def generate_publishing_keywords(request, project_id):
    """Generate keywords using AI"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM'}, status=400)
        
        system_prompt = """Generate 7 relevant keywords for book discoverability.
Return ONLY a comma-separated list of keywords in German."""

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=f"Titel: {project.title}\nGenre: {project.genre}\nBeschreibung: {project.description or ''}",
            temperature=0.7,
            max_tokens=100,
        )
        
        response = generate_text(req)
        if response.get('ok'):
            return JsonResponse({'success': True, 'keywords': response.get('text', '')})
        else:
            return JsonResponse({'success': False, 'error': response.get('error')}, status=500)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_book_cover(request, project_id):
    """Generate book cover using ComfyUI"""
    from .models_publishing import BookCover
    from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
    from django.core.files.base import ContentFile
    from asgiref.sync import async_to_sync
    import base64
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        prompt = data.get('prompt', '')
        style = data.get('style', 'illustrated')
        
        style_prompts = {
            'realistic': 'photorealistic book cover, cinematic lighting',
            'illustrated': 'illustrated book cover, digital painting, vibrant colors',
            'fantasy': 'fantasy art book cover, epic, magical, detailed illustration',
            'minimalist': 'minimalist book cover design, clean, modern',
            'vintage': 'vintage book cover, retro style, classic typography',
        }
        
        full_prompt = f"{prompt}, {style_prompts.get(style, style_prompts['illustrated'])}, book cover, vertical portrait"
        
        handler = ComfyUIHandler()
        # Use async_to_sync since generate_image is async
        result = async_to_sync(handler.generate_image)(
            prompt=full_prompt,
            negative_prompt="text, letters, words, title, blurry, low quality",
            width=1024,
            height=1536,
        )
        
        if result.get('success') and result.get('image_base64'):
            image_data = base64.b64decode(result['image_base64'])
            
            cover = BookCover.objects.create(
                project=project,
                cover_type='ebook',
                prompt_used=full_prompt,
                is_ai_generated=True,
                is_primary=not BookCover.objects.filter(project=project, is_primary=True).exists(),
                width=1024,
                height=1536,
            )
            cover.image.save(f'cover_{project.id}_{cover.id}.png', ContentFile(image_data))
            
            return JsonResponse({'success': True, 'cover_id': cover.id})
        else:
            return JsonResponse({'success': False, 'error': result.get('error', 'Generierung fehlgeschlagen')}, status=500)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def upload_book_cover(request, project_id):
    """Upload book cover image"""
    from .models_publishing import BookCover
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    if 'cover' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'Keine Datei'}, status=400)
    
    cover_file = request.FILES['cover']
    
    cover = BookCover.objects.create(
        project=project,
        cover_type='ebook',
        is_ai_generated=False,
        is_primary=not BookCover.objects.filter(project=project, is_primary=True).exists(),
    )
    cover.image.save(cover_file.name, cover_file)
    
    return JsonResponse({'success': True, 'cover_id': cover.id})


def get_matter_content(request, project_id, position, page_type):
    """Get front/back matter content"""
    from .models_publishing import FrontMatter, BackMatter
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    Model = FrontMatter if position == 'front' else BackMatter
    matter = Model.objects.filter(project=project, page_type=page_type).first()
    
    return JsonResponse({
        'title': matter.title if matter else '',
        'content': matter.content if matter else '',
        'auto_generate': matter.auto_generate if matter else (position == 'front'),
    })


@require_http_methods(["POST"])
def save_matter_content(request, project_id, position, page_type):
    """Save front/back matter content"""
    from .models_publishing import FrontMatter, BackMatter
    
    project = get_object_or_404(BookProjects, id=project_id)
    data = json.loads(request.body)
    
    Model = FrontMatter if position == 'front' else BackMatter
    
    Model.objects.update_or_create(
        project=project,
        page_type=page_type,
        defaults={
            'title': data.get('title', ''),
            'content': data.get('content', ''),
            'auto_generate': data.get('auto_generate', False),
            'is_active': True,
        }
    )
    
    return JsonResponse({'success': True})


@require_http_methods(["POST"])
def toggle_matter(request, project_id, position, page_type):
    """Toggle front/back matter active status"""
    from .models_publishing import FrontMatter, BackMatter
    
    project = get_object_or_404(BookProjects, id=project_id)
    data = json.loads(request.body)
    
    Model = FrontMatter if position == 'front' else BackMatter
    
    Model.objects.update_or_create(
        project=project,
        page_type=page_type,
        defaults={'is_active': data.get('is_active', True)}
    )
    
    return JsonResponse({'success': True})


@require_http_methods(["POST"])
def generate_matter_content(request, project_id):
    """Generate front/back matter content using AI"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        position = data.get('position', 'front')
        page_type = data.get('type', '')
        
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM'}, status=400)
        
        # Type-specific prompts
        prompts = {
            'dedication': f'Schreibe eine kurze, herzliche Widmung für das Buch "{project.title}". Maximal 2-3 Sätze.',
            'epigraph': f'Wähle oder erfinde ein passendes Zitat/Motto für ein {project.genre}-Buch namens "{project.title}". Nur das Zitat mit Autor.',
            'preface': f'Schreibe ein kurzes Vorwort (ca. 150 Wörter) für "{project.title}" - ein {project.genre}-Buch. Beschreibung: {project.description or ""}',
            'acknowledgments': f'Schreibe Danksagungen für das Buch "{project.title}". Danke fiktiven Unterstützern, Familie, Lektoren etc. Ca. 100 Wörter.',
            'prologue': f'Schreibe einen atmosphärischen Prolog (ca. 200 Wörter) für "{project.title}" im Genre {project.genre}.',
            'epilogue': f'Schreibe einen abschließenden Epilog (ca. 150 Wörter) für "{project.title}".',
            'afterword': f'Schreibe ein Nachwort des Autors (ca. 150 Wörter) für "{project.title}". Erkläre die Inspiration.',
            'about_author': f'Schreibe einen "Über den Autor"-Text für den Autor von "{project.title}". Ca. 100 Wörter, in dritter Person.',
            'also_by': f'Liste 3-5 fiktive andere Werke des Autors von "{project.title}" im Genre {project.genre}.',
            'glossary': f'Erstelle ein kurzes Glossar mit 5-8 wichtigen Begriffen für "{project.title}" ({project.genre}).',
        }
        
        prompt = prompts.get(page_type, f'Schreibe einen kurzen Text für die Seite "{page_type}" des Buches "{project.title}".')
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system='Du bist ein erfahrener Buchautor. Schreibe authentische, professionelle Buchtexte auf Deutsch.',
            prompt=prompt,
            temperature=0.7,
            max_tokens=500,
        )
        
        response = generate_text(req)
        if response.get('ok'):
            return JsonResponse({
                'success': True,
                'content': response.get('text', ''),
                'title': page_type.replace('_', ' ').title() if page_type else ''
            })
        else:
            return JsonResponse({'success': False, 'error': response.get('error')}, status=500)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def generate_author_bio(request, project_id):
    """Generate author bio using AI"""
    from apps.bfagent.services.llm_client import LlmRequest, generate_text
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM'}, status=400)
        
        author_name = request.user.get_full_name() or request.user.username
        
        system_prompt = 'Du bist ein erfahrener Autor. Schreibe professionelle Autorenbiografien auf Deutsch.'
        
        prompt = f'''Schreibe zwei Versionen einer Autorenbiografie für {author_name}, Autor von "{project.title}" (Genre: {project.genre}).

1. KURZ (50-70 Wörter): Kompakte Bio für Buchrückseite
2. LANG (150-200 Wörter): Ausführliche Bio für Autorenseite

Antworte im Format:
KURZ:
[kurze Bio]

LANG:
[lange Bio]'''

        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4',
            system=system_prompt,
            prompt=prompt,
            temperature=0.7,
            max_tokens=500,
        )
        
        response = generate_text(req)
        if response.get('ok'):
            text = response.get('text', '')
            # Parse response
            bio_short = ''
            bio_long = ''
            if 'KURZ:' in text and 'LANG:' in text:
                parts = text.split('LANG:')
                bio_short = parts[0].replace('KURZ:', '').strip()
                bio_long = parts[1].strip() if len(parts) > 1 else ''
            else:
                bio_short = text[:200]
                bio_long = text
            
            return JsonResponse({
                'success': True,
                'bio_short': bio_short,
                'bio_long': bio_long
            })
        else:
            return JsonResponse({'success': False, 'error': response.get('error')}, status=500)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# ILLUSTRATION STYLE TEMPLATES
# =============================================================================

def list_style_templates(request):
    """List all available illustration style templates"""
    from .models import IllustrationStyleTemplate
    
    templates = IllustrationStyleTemplate.objects.filter(
        Q(is_public=True) | Q(created_by=request.user)
    ).order_by('-updated_at')
    
    return JsonResponse({
        'success': True,
        'templates': [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'style_type': t.style_type,
                'style_type_display': t.get_style_type_display(),
                'is_public': t.is_public,
                'is_mine': t.created_by == request.user,
            }
            for t in templates
        ]
    })


@require_http_methods(["POST"])
def save_style_template(request, project_id):
    """Save current project style as a reusable template"""
    from .models import IllustrationStyle, IllustrationStyleTemplate
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        template_name = data.get('name', '').strip()
        
        if not template_name:
            return JsonResponse({'success': False, 'error': 'Name erforderlich'}, status=400)
        
        # Get current project style
        try:
            style = project.illustration_style
        except IllustrationStyle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Kein Stil für Projekt definiert'}, status=400)
        
        # Create or update template
        template, created = IllustrationStyleTemplate.objects.update_or_create(
            name=template_name,
            defaults={
                'description': data.get('description', ''),
                'style_type': style.style_type,
                'base_prompt': style.base_prompt,
                'negative_prompt': style.negative_prompt,
                'color_palette': style.color_palette,
                'provider': style.provider,
                'quality': style.quality,
                'image_size': style.image_size,
                'created_by': request.user,
                'is_public': data.get('is_public', False),
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Vorlage gespeichert' if created else 'Vorlage aktualisiert',
            'template_id': template.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def apply_style_template_legacy(request, project_id):
    """Apply a style template to a project (legacy endpoint)"""
    from .models import IllustrationStyleTemplate, IllustrationStyle
    from .models_prompt_system import PromptMasterStyle
    from apps.bfagent.models_illustration import ImageStyleProfile
    
    project = get_object_or_404(BookProjects, id=project_id)
    
    try:
        data = json.loads(request.body)
        source = data.get('source')  # 'profile' or 'template'
        style_id = data.get('id')
        
        # Backward compatibility: handle old format
        if not source and data.get('template_id'):
            source = 'template'
            style_id = data.get('template_id')
        
        if not style_id:
            return JsonResponse({'success': False, 'error': 'Kein Stil ausgewählt'}, status=400)
        
        if source == 'profile':
            # Apply from ImageStyleProfile (Illustration-System)
            profile = get_object_or_404(ImageStyleProfile, id=style_id, user=request.user)
            
            style, created = IllustrationStyle.objects.get_or_create(project=project)
            style.style_type = profile.art_style
            style.style_name = profile.display_name
            style.base_prompt = profile.base_prompt
            style.negative_prompt = profile.negative_prompt or ''
            style.provider = profile.preferred_provider
            style.quality = profile.default_quality
            style.image_size = profile.default_resolution
            style.save()
            
            style_name = profile.display_name
            base_prompt = profile.base_prompt
            negative_prompt = profile.negative_prompt or ''
        else:
            # Apply from IllustrationStyleTemplate
            template = get_object_or_404(IllustrationStyleTemplate, id=style_id)
            
            # Check permission
            if not template.is_public and template.created_by != request.user:
                return JsonResponse({'success': False, 'error': 'Keine Berechtigung'}, status=403)
            
            style = template.apply_to_project(project)
            style_name = template.name
            base_prompt = template.base_prompt
            negative_prompt = template.negative_prompt or ''
        
        # IMPORTANT: Also create/update PromptMasterStyle for illustration generation
        master_style, _ = PromptMasterStyle.objects.update_or_create(
            project=project,
            defaults={
                'name': style_name,
                'preset': 'custom',
                'style_base_prompt': base_prompt,
                'master_prompt': base_prompt,
                'negative_prompt': negative_prompt,
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Stil "{style_name}" angewendet',
            'style': {
                'style_type': style.style_type,
                'style_name': style.style_name,
                'base_prompt': style.base_prompt,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["DELETE"])
def delete_style_template(request, template_id):
    """Delete a style template"""
    from .models import IllustrationStyleTemplate
    
    template = get_object_or_404(IllustrationStyleTemplate, id=template_id)
    
    # Check permission
    if template.created_by != request.user:
        return JsonResponse({'success': False, 'error': 'Keine Berechtigung'}, status=403)
    
    template.delete()
    return JsonResponse({'success': True, 'message': 'Vorlage gelöscht'})


# =============================================================================
# BOOK SERIES (Buchreihen / Universes)
# =============================================================================

@login_required
def series_dashboard(request):
    """Dashboard für alle Buchreihen des Benutzers"""
    from .models import BookSeries
    
    series_list = BookSeries.objects.filter(
        created_by=request.user,
        is_active=True
    ).prefetch_related('projects', 'characters', 'worlds')
    
    return render(request, 'writing_hub/series/dashboard.html', {
        'series_list': series_list,
    })


@login_required
def series_detail(request, series_id):
    """Detailansicht einer Buchreihe"""
    from .models import BookSeries
    from apps.bfagent.models import BookProjects
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    
    # Projekte der Reihe
    projects = series.projects.all().order_by('series_order', 'title')
    
    # Verfügbare Projekte zum Hinzufügen (alle außer bereits in dieser Reihe)
    available_projects = BookProjects.objects.filter(
        user=request.user
    ).exclude(
        series=series
    ).order_by('-created_at')
    
    return render(request, 'writing_hub/series/detail.html', {
        'series': series,
        'projects': projects,
        'characters': series.characters.all(),
        'worlds': series.worlds.all(),
        'available_projects': available_projects,
    })


@login_required
@require_http_methods(["GET", "POST"])
def series_create(request):
    """Neue Buchreihe erstellen"""
    from .models import BookSeries
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            series = BookSeries.objects.create(
                name=data.get('name', '').strip(),
                description=data.get('description', ''),
                genre=data.get('genre', ''),
                created_by=request.user
            )
            
            if request.content_type == 'application/json':
                return JsonResponse({
                    'success': True,
                    'series_id': str(series.id),
                    'redirect_url': f'/writing-hub/series/{series.id}/'
                })
            return redirect('writing_hub:series_detail', series_id=series.id)
            
        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            messages.error(request, f'Fehler: {str(e)}')
    
    return render(request, 'writing_hub/series/create.html', {})


@login_required
@require_http_methods(["POST"])
def series_update(request, series_id):
    """Buchreihe aktualisieren"""
    from .models import BookSeries
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        
        # Basis-Felder
        if 'name' in data:
            series.name = data['name'].strip()
        if 'description' in data:
            series.description = data['description']
        if 'genre' in data:
            series.genre = data['genre']
        if 'illustration_style_template_id' in data:
            from .models import IllustrationStyleTemplate
            if data['illustration_style_template_id']:
                series.illustration_style_template = get_object_or_404(
                    IllustrationStyleTemplate, id=data['illustration_style_template_id']
                )
            else:
                series.illustration_style_template = None
        
        # Neue Konsistenz-Felder
        if 'series_timeline' in data:
            series.series_timeline = data['series_timeline']
        if 'narrative_voice' in data:
            series.narrative_voice = data['narrative_voice']
        if 'target_audience' in data:
            series.target_audience = data['target_audience']
        if 'tone_guidelines' in data:
            series.tone_guidelines = data['tone_guidelines']
        if 'consistency_rules' in data:
            series.consistency_rules = data['consistency_rules']
        if 'required_elements' in data:
            series.required_elements = data['required_elements']
        if 'forbidden_elements' in data:
            series.forbidden_elements = data['forbidden_elements']
        if 'spice_level' in data:
            series.spice_level = data['spice_level']
        if 'content_warnings' in data:
            series.content_warnings = data['content_warnings']
        
        series.save()
        
        return JsonResponse({'success': True, 'message': 'Reihe aktualisiert'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def series_ai_enhance(request, series_id):
    """KI-Verbesserung für Serien-Felder"""
    from .models import BookSeries
    from apps.bfagent.models import Llms
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        field_name = data.get('field_name')
        field_label = data.get('field_label')
        current_value = data.get('current_value', '')
        series_name = data.get('series_name', series.name)
        genre = data.get('genre', series.genre or '')
        
        # Build prompt based on field
        prompts = {
            'description': f"Verbessere und erweitere diese Beschreibung für die Buchreihe '{series_name}' (Genre: {genre}). Mache sie ansprechend und professionell. Aktuelle Beschreibung: {current_value or 'Keine vorhanden'}",
            'tone_guidelines': f"Erstelle detaillierte Ton/Stimmungs-Richtlinien für die Buchreihe '{series_name}' (Genre: {genre}). Beschreibe den emotionalen Ton, die Atmosphäre und Stimmung. Aktuell: {current_value or 'Keine vorhanden'}",
            'consistency_rules': f"Erstelle Konsistenz-Regeln für die Buchreihe '{series_name}' (Genre: {genre}). Diese Regeln sollen sicherstellen, dass alle Bücher der Reihe stimmig sind. Aktuell: {current_value or 'Keine vorhanden'}",
            'required_elements': f"Schlage Pflicht-Elemente vor, die in jedem Buch der Reihe '{series_name}' (Genre: {genre}) vorkommen sollten. Aktuell: {current_value or 'Keine vorhanden'}",
            'forbidden_elements': f"Schlage Elemente vor, die in der Buchreihe '{series_name}' (Genre: {genre}) NICHT vorkommen sollten, um die Konsistenz zu wahren. Aktuell: {current_value or 'Keine vorhanden'}",
            'content_warnings': f"Erstelle passende Content Warnings für die Buchreihe '{series_name}' (Genre: {genre}) basierend auf typischen Elementen dieses Genres. Aktuell: {current_value or 'Keine vorhanden'}",
        }
        
        prompt = prompts.get(field_name, f"Verbessere diesen Text für '{field_label}': {current_value}")
        system_prompt = "Du bist ein erfahrener Buchautor und Lektor. Antworte nur mit dem verbesserten/erweiterten Text, ohne Erklärungen oder Einleitungen. Schreibe auf Deutsch."
        
        # Get active LLM
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return JsonResponse({'success': False, 'error': 'Kein aktives LLM konfiguriert'}, status=400)
        
        # Use the existing LLM client service
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        llm_request = LlmRequest(
            provider=llm.provider,
            model=llm.llm_name,
            base_url=llm.endpoint_url,
            api_key=llm.api_key,
            system_prompt=system_prompt,
            prompt=prompt,
            temperature=0.7,
            max_tokens=500,
        )
        
        response_data = generate_text(llm_request)
        
        if response_data.get("ok"):
            enhanced_text = response_data.get("text", "").strip()
            return JsonResponse({
                'success': True,
                'enhanced_text': enhanced_text
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': response_data.get("error", "LLM-Fehler")
            }, status=400)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def series_add_project(request, series_id):
    """Projekt zur Buchreihe hinzufügen"""
    from .models import BookSeries
    from apps.bfagent.models import BookProjects
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        
        project = get_object_or_404(BookProjects, id=project_id, user=request.user)
        
        # Nächste Position in der Reihe
        max_order = series.projects.aggregate(Max('series_order'))['series_order__max'] or 0
        
        project.series = series
        project.series_order = max_order + 1
        project.save()
        
        return JsonResponse({
            'success': True,
            'message': f'"{project.title}" zur Reihe hinzugefügt'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def series_remove_project(request, series_id, project_id):
    """Projekt aus Buchreihe entfernen"""
    from .models import BookSeries
    from apps.bfagent.models import BookProjects
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    project = get_object_or_404(BookProjects, id=project_id, series=series)
    
    project.series = None
    project.series_order = None
    project.save()
    
    return JsonResponse({
        'success': True,
        'message': f'"{project.title}" aus Reihe entfernt'
    })


@login_required
@require_http_methods(["POST"])
def series_reorder_projects(request, series_id):
    """Reihenfolge der Projekte in der Reihe ändern"""
    from .models import BookSeries
    from apps.bfagent.models import BookProjects
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        order = data.get('order', [])  # List of project IDs in new order
        
        for idx, project_id in enumerate(order, start=1):
            BookProjects.objects.filter(
                id=project_id,
                series=series
            ).update(series_order=idx)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# =============================================================================
# SHARED CHARACTERS (Gemeinsame Charaktere)
# =============================================================================

@login_required
@require_http_methods(["POST"])
def series_add_character(request, series_id):
    """Neuen gemeinsamen Charakter zur Reihe hinzufügen"""
    from .models import BookSeries, SharedCharacter
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        
        character = SharedCharacter.objects.create(
            series=series,
            name=data.get('name', '').strip(),
            role=data.get('role', 'supporting'),
            description=data.get('description', ''),
            age_at_series_start=data.get('age_at_series_start'),
            background=data.get('background', ''),
            personality=data.get('personality', ''),
            appearance=data.get('appearance', ''),
            motivation=data.get('motivation', ''),
        )
        
        return JsonResponse({
            'success': True,
            'character_id': str(character.id),
            'message': f'Charakter "{character.name}" erstellt'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def series_update_character(request, series_id, character_id):
    """Gemeinsamen Charakter aktualisieren"""
    from .models import BookSeries, SharedCharacter
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    character = get_object_or_404(SharedCharacter, id=character_id, series=series)
    
    try:
        data = json.loads(request.body)
        
        for field in ['name', 'role', 'description', 'age_at_series_start', 
                      'background', 'personality', 'appearance', 'motivation', 'arc']:
            if field in data:
                setattr(character, field, data[field])
        
        character.save()
        
        return JsonResponse({'success': True, 'message': 'Charakter aktualisiert'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def series_delete_character(request, series_id, character_id):
    """Gemeinsamen Charakter löschen"""
    from .models import BookSeries, SharedCharacter
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    character = get_object_or_404(SharedCharacter, id=character_id, series=series)
    
    character.delete()
    
    return JsonResponse({'success': True, 'message': 'Charakter gelöscht'})


# =============================================================================
# SHARED WORLDS (Gemeinsame Welten)
# =============================================================================

@login_required
@require_http_methods(["POST"])
def series_add_world(request, series_id):
    """Neue gemeinsame Welt zur Reihe hinzufügen"""
    from .models import BookSeries, SharedWorld
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        
        world = SharedWorld.objects.create(
            series=series,
            name=data.get('name', '').strip(),
            world_type=data.get('world_type', 'primary'),
            description=data.get('description', ''),
            geography=data.get('geography', ''),
            culture=data.get('culture', ''),
            technology_level=data.get('technology_level', ''),
            magic_system=data.get('magic_system', ''),
            politics=data.get('politics', ''),
            history=data.get('history', ''),
        )
        
        return JsonResponse({
            'success': True,
            'world_id': str(world.id),
            'message': f'Welt "{world.name}" erstellt'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def series_update_world(request, series_id, world_id):
    """Gemeinsame Welt aktualisieren"""
    from .models import BookSeries, SharedWorld
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    world = get_object_or_404(SharedWorld, id=world_id, series=series)
    
    try:
        data = json.loads(request.body)
        
        for field in ['name', 'world_type', 'description', 'geography', 
                      'culture', 'technology_level', 'magic_system', 'politics', 'history']:
            if field in data:
                setattr(world, field, data[field])
        
        world.save()
        
        return JsonResponse({'success': True, 'message': 'Welt aktualisiert'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def series_delete_world(request, series_id, world_id):
    """Gemeinsame Welt löschen"""
    from .models import BookSeries, SharedWorld
    
    series = get_object_or_404(BookSeries, id=series_id, created_by=request.user)
    world = get_object_or_404(SharedWorld, id=world_id, series=series)
    
    world.delete()
    
    return JsonResponse({'success': True, 'message': 'Welt gelöscht'})

