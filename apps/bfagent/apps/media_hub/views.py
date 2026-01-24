"""
Media Hub Views
===============

API and UI views for the Media Hub.
"""
import json
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.utils import timezone
import structlog

logger = structlog.get_logger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def submit_render_job(request):
    """
    Submit a new render job.
    
    POST /media-hub/api/jobs/submit/
    
    Body:
    {
        "job_type": "illustration",
        "prompt": "A magical forest...",
        "style_preset": "cinematic",
        "format_preset": "square-1-1",
        "quality_preset": "standard",
        "ref_table": "scenes",
        "ref_id": 123,
        "project_id": 1,
        "priority": 5
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    job_type = data.get('job_type', 'illustration')
    prompt = data.get('prompt', '')
    
    # Validate job type
    valid_types = ['illustration', 'comic_panel', 'book_cover', 'audio_chapter', 'audio_full']
    if job_type not in valid_types:
        return JsonResponse({'error': f'Invalid job_type. Must be one of: {valid_types}'}, status=400)
    
    # Get preset IDs from slugs
    style_id = format_id = quality_id = voice_id = None
    
    with connection.cursor() as cursor:
        if data.get('style_preset'):
            cursor.execute(
                "SELECT id FROM media_hub_style_preset WHERE slug = %s AND is_active = true",
                [data['style_preset']]
            )
            row = cursor.fetchone()
            style_id = row[0] if row else None
        
        if data.get('format_preset'):
            cursor.execute(
                "SELECT id FROM media_hub_format_preset WHERE slug = %s AND is_active = true",
                [data['format_preset']]
            )
            row = cursor.fetchone()
            format_id = row[0] if row else None
        
        if data.get('quality_preset'):
            cursor.execute(
                "SELECT id FROM media_hub_quality_preset WHERE slug = %s AND is_active = true",
                [data['quality_preset']]
            )
            row = cursor.fetchone()
            quality_id = row[0] if row else None
        
        if data.get('voice_preset'):
            cursor.execute(
                "SELECT id FROM media_hub_voice_preset WHERE slug = %s AND is_active = true",
                [data['voice_preset']]
            )
            row = cursor.fetchone()
            voice_id = row[0] if row else None
    
    # Build input snapshot
    input_snapshot = {
        'prompt': {
            'positive': prompt,
        },
        'render': {
            'width': data.get('width', 1024),
            'height': data.get('height', 1024),
        },
        'sampler': {
            'steps': data.get('steps', 25),
            'cfg_scale': data.get('cfg_scale', 7.5),
        }
    }
    
    # Create job
    job_uuid = str(uuid.uuid4())
    
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO media_hub_render_job 
            (uuid, job_type, status, priority, ref_table, ref_id, input_snapshot, 
             error_message, attempt_count, max_attempts, created_at, updated_at,
             org_id, project_id, created_by_id, 
             style_preset_id, format_preset_id, quality_preset_id, voice_preset_id, workflow_id)
            VALUES (%s, %s, 'pending', %s, %s, %s, %s, 
                    '', 0, 3, NOW(), NOW(),
                    %s, %s, %s,
                    %s, %s, %s, %s, NULL)
            RETURNING id
        """, [
            job_uuid, 
            job_type, 
            data.get('priority', 5),
            data.get('ref_table', ''),
            data.get('ref_id'),
            json.dumps(input_snapshot),
            data.get('org_id'),
            data.get('project_id'),
            request.user.id if request.user.is_authenticated else None,
            style_id, format_id, quality_id, voice_id
        ])
        
        job_id = cursor.fetchone()[0]
    
    logger.info("render_job_submitted", job_id=job_id, job_type=job_type)
    
    return JsonResponse({
        'success': True,
        'job_id': job_id,
        'uuid': job_uuid,
        'status': 'pending',
    })


@require_http_methods(["GET"])
def get_job_status(request, job_id):
    """
    Get render job status.
    
    GET /media-hub/api/jobs/<job_id>/status/
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, uuid, job_type, status, priority, 
                   attempt_count, max_attempts, error_message,
                   created_at, started_at, completed_at
            FROM media_hub_render_job
            WHERE id = %s
        """, [job_id])
        
        row = cursor.fetchone()
        if not row:
            return JsonResponse({'error': 'Job not found'}, status=404)
        
        columns = ['id', 'uuid', 'job_type', 'status', 'priority',
                   'attempt_count', 'max_attempts', 'error_message',
                   'created_at', 'started_at', 'completed_at']
        job = dict(zip(columns, row))
        
        # Convert datetimes to ISO format
        for key in ['created_at', 'started_at', 'completed_at']:
            if job[key]:
                job[key] = job[key].isoformat()
        
        # Get asset if completed
        if job['status'] == 'completed':
            cursor.execute("""
                SELECT a.id, a.uuid, af.storage_path
                FROM media_hub_asset a
                LEFT JOIN media_hub_asset_file af ON af.asset_id = a.id AND af.file_type = 'original'
                WHERE a.job_id = %s
                LIMIT 1
            """, [job_id])
            asset_row = cursor.fetchone()
            if asset_row:
                job['asset'] = {
                    'id': asset_row[0],
                    'uuid': str(asset_row[1]),
                    'file_path': asset_row[2],
                }
    
    return JsonResponse(job)


@require_http_methods(["GET"])
def list_presets(request):
    """
    List available presets.
    
    GET /media-hub/api/presets/
    """
    presets = {
        'style': [],
        'format': [],
        'quality': [],
        'voice': [],
    }
    
    with connection.cursor() as cursor:
        # Style presets
        cursor.execute("""
            SELECT slug, name, description, category
            FROM media_hub_style_preset WHERE is_active = true
            ORDER BY name
        """)
        presets['style'] = [
            {'slug': r[0], 'name': r[1], 'description': r[2], 'category': r[3]}
            for r in cursor.fetchall()
        ]
        
        # Format presets
        cursor.execute("""
            SELECT slug, name, width, height, aspect_ratio, use_case
            FROM media_hub_format_preset WHERE is_active = true
            ORDER BY name
        """)
        presets['format'] = [
            {'slug': r[0], 'name': r[1], 'width': r[2], 'height': r[3], 
             'aspect_ratio': r[4], 'use_case': r[5]}
            for r in cursor.fetchall()
        ]
        
        # Quality presets
        cursor.execute("""
            SELECT slug, name, level
            FROM media_hub_quality_preset WHERE is_active = true
            ORDER BY name
        """)
        presets['quality'] = [
            {'slug': r[0], 'name': r[1], 'level': r[2]}
            for r in cursor.fetchall()
        ]
        
        # Voice presets
        cursor.execute("""
            SELECT slug, name, language, gender
            FROM media_hub_voice_preset WHERE is_active = true
            ORDER BY name
        """)
        presets['voice'] = [
            {'slug': r[0], 'name': r[1], 'language': r[2], 'gender': r[3]}
            for r in cursor.fetchall()
        ]
    
    return JsonResponse(presets)


@require_http_methods(["GET"])
def list_jobs(request):
    """
    List render jobs with optional filtering.
    
    GET /media-hub/api/jobs/?status=pending&limit=20
    """
    status = request.GET.get('status')
    job_type = request.GET.get('job_type')
    limit = min(int(request.GET.get('limit', 20)), 100)
    
    query = """
        SELECT id, uuid, job_type, status, priority, 
               attempt_count, created_at, completed_at
        FROM media_hub_render_job
        WHERE 1=1
    """
    params = []
    
    if status:
        query += " AND status = %s"
        params.append(status)
    
    if job_type:
        query += " AND job_type = %s"
        params.append(job_type)
    
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = ['id', 'uuid', 'job_type', 'status', 'priority',
                   'attempt_count', 'created_at', 'completed_at']
        jobs = []
        for row in cursor.fetchall():
            job = dict(zip(columns, row))
            for key in ['created_at', 'completed_at']:
                if job[key]:
                    job[key] = job[key].isoformat()
            jobs.append(job)
    
    return JsonResponse({'jobs': jobs, 'count': len(jobs)})


# ============================================
# UI Views (Dashboard, Asset Browser)
# ============================================

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):
    """Media Hub Dashboard."""
    stats = {}
    
    with connection.cursor() as cursor:
        # Job stats
        cursor.execute("""
            SELECT status, COUNT(*) FROM media_hub_render_job 
            GROUP BY status
        """)
        status_counts = dict(cursor.fetchall())
        stats['pending'] = status_counts.get('pending', 0) + status_counts.get('queued', 0)
        stats['running'] = status_counts.get('running', 0)
        stats['completed'] = status_counts.get('completed', 0)
        
        # Asset count
        cursor.execute("SELECT COUNT(*) FROM media_hub_asset")
        stats['assets'] = cursor.fetchone()[0]
    
    return render(request, 'media_hub/dashboard.html', {'stats': stats})


@login_required
def job_queue_partial(request):
    """HTMX partial for job queue table."""
    status_filter = request.GET.get('status')
    
    query = """
        SELECT j.id, j.job_type, j.status, j.priority, j.created_at,
               (SELECT a.id FROM media_hub_asset a WHERE a.job_id = j.id LIMIT 1) as asset_id
        FROM media_hub_render_job j
        WHERE 1=1
    """
    params = []
    
    if status_filter and status_filter != 'all':
        query += " AND j.status = %s"
        params.append(status_filter)
    
    query += " ORDER BY j.created_at DESC LIMIT 20"
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = ['id', 'job_type', 'status', 'priority', 'created_at', 'asset_id']
        jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return render(request, 'media_hub/partials/job_queue.html', {'jobs': jobs})


@login_required
def recent_assets_partial(request):
    """HTMX partial for recent assets."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT a.id, a.title, a.asset_type, a.created_at,
                   (SELECT af.storage_path FROM media_hub_asset_file af 
                    WHERE af.asset_id = a.id AND af.file_type = 'thumbnail' LIMIT 1) as thumbnail_url
            FROM media_hub_asset a
            ORDER BY a.created_at DESC
            LIMIT 9
        """)
        columns = ['id', 'title', 'asset_type', 'created_at', 'thumbnail_url']
        assets = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return render(request, 'media_hub/partials/recent_assets.html', {'assets': assets})


@login_required
def asset_browser(request):
    """Asset browser view."""
    return render(request, 'media_hub/asset_browser.html', {
        'filter_type': request.GET.get('asset_type', ''),
        'search_query': request.GET.get('q', ''),
    })


@login_required
def asset_grid_partial(request):
    """HTMX partial for asset grid."""
    asset_type = request.GET.get('asset_type')
    job_type = request.GET.get('job_type')
    sort = request.GET.get('sort', '-created_at')
    search = request.GET.get('q', '')
    
    query = """
        SELECT a.id, a.title, a.asset_type, a.created_at, j.job_type,
               (SELECT af.storage_path FROM media_hub_asset_file af 
                WHERE af.asset_id = a.id AND af.file_type = 'thumbnail' LIMIT 1) as thumbnail_url,
               (SELECT af.storage_path FROM media_hub_asset_file af 
                WHERE af.asset_id = a.id AND af.file_type = 'original' LIMIT 1) as file_url
        FROM media_hub_asset a
        LEFT JOIN media_hub_render_job j ON j.id = a.job_id
        WHERE 1=1
    """
    params = []
    
    if asset_type:
        query += " AND a.asset_type = %s"
        params.append(asset_type)
    
    if job_type:
        query += " AND j.job_type = %s"
        params.append(job_type)
    
    if search:
        query += " AND (a.title ILIKE %s OR a.description ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    # Sorting
    if sort == 'created_at':
        query += " ORDER BY a.created_at ASC"
    elif sort == 'title':
        query += " ORDER BY a.title ASC"
    else:
        query += " ORDER BY a.created_at DESC"
    
    query += " LIMIT 50"
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = ['id', 'title', 'asset_type', 'created_at', 'job_type', 'thumbnail_url', 'file_url']
        assets = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return render(request, 'media_hub/partials/asset_grid.html', {'assets': assets})


@login_required
def asset_detail(request, asset_id):
    """Asset detail view."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT a.id, a.uuid, a.title, a.description, a.asset_type, 
                   a.metadata, a.created_at, a.is_approved, a.is_featured,
                   j.id as job_id, j.job_type, j.input_snapshot
            FROM media_hub_asset a
            LEFT JOIN media_hub_render_job j ON j.id = a.job_id
            WHERE a.id = %s
        """, [asset_id])
        row = cursor.fetchone()
        
        if not row:
            return JsonResponse({'error': 'Asset not found'}, status=404)
        
        columns = ['id', 'uuid', 'title', 'description', 'asset_type',
                   'metadata', 'created_at', 'is_approved', 'is_featured',
                   'job_id', 'job_type', 'input_snapshot']
        asset = dict(zip(columns, row))
        
        # Get files
        cursor.execute("""
            SELECT file_type, storage_path, mime_type, file_size
            FROM media_hub_asset_file WHERE asset_id = %s
        """, [asset_id])
        asset['files'] = [
            dict(zip(['file_type', 'storage_path', 'mime_type', 'file_size'], r))
            for r in cursor.fetchall()
        ]
    
    return render(request, 'media_hub/asset_detail.html', {'asset': asset})


@login_required
def asset_detail_partial(request, asset_id):
    """HTMX partial for asset detail modal."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT a.id, a.uuid, a.title, a.description, a.asset_type, 
                   a.metadata, a.created_at, j.job_type, j.input_snapshot,
                   (SELECT af.storage_path FROM media_hub_asset_file af 
                    WHERE af.asset_id = a.id AND af.file_type = 'original' LIMIT 1) as file_url
            FROM media_hub_asset a
            LEFT JOIN media_hub_render_job j ON j.id = a.job_id
            WHERE a.id = %s
        """, [asset_id])
        row = cursor.fetchone()
        
        if not row:
            return JsonResponse({'error': 'Asset not found'}, status=404)
        
        columns = ['id', 'uuid', 'title', 'description', 'asset_type',
                   'metadata', 'created_at', 'job_type', 'input_snapshot', 'file_url']
        asset = dict(zip(columns, row))
    
    return render(request, 'media_hub/partials/asset_detail.html', {'asset': asset})


@login_required
def job_detail_partial(request, job_id):
    """HTMX partial for job detail modal."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, uuid, job_type, status, priority, input_snapshot,
                   error_message, attempt_count, max_attempts,
                   created_at, started_at, completed_at
            FROM media_hub_render_job WHERE id = %s
        """, [job_id])
        row = cursor.fetchone()
        
        if not row:
            return JsonResponse({'error': 'Job not found'}, status=404)
        
        columns = ['id', 'uuid', 'job_type', 'status', 'priority', 'input_snapshot',
                   'error_message', 'attempt_count', 'max_attempts',
                   'created_at', 'started_at', 'completed_at']
        job = dict(zip(columns, row))
        
        # Get attempts
        cursor.execute("""
            SELECT attempt_no, status, started_at, completed_at, duration_ms, error_message
            FROM media_hub_render_attempt WHERE job_id = %s ORDER BY attempt_no
        """, [job_id])
        job['attempts'] = [
            dict(zip(['attempt_no', 'status', 'started_at', 'completed_at', 'duration_ms', 'error_message'], r))
            for r in cursor.fetchall()
        ]
    
    return render(request, 'media_hub/partials/job_detail.html', {'job': job})


@csrf_exempt
@require_http_methods(["POST"])
def submit_job_form(request):
    """Handle form submission for new job (HTMX)."""
    job_type = request.POST.get('job_type', 'illustration')
    prompt = request.POST.get('prompt', '')
    priority = int(request.POST.get('priority', 5))
    style_preset = request.POST.get('style_preset')
    format_preset = request.POST.get('format_preset')
    quality_preset = request.POST.get('quality_preset')
    
    # Get preset IDs
    style_id = format_id = quality_id = None
    
    with connection.cursor() as cursor:
        if style_preset:
            cursor.execute("SELECT id FROM media_hub_style_preset WHERE slug = %s", [style_preset])
            row = cursor.fetchone()
            style_id = row[0] if row else None
        
        if format_preset:
            cursor.execute("SELECT id FROM media_hub_format_preset WHERE slug = %s", [format_preset])
            row = cursor.fetchone()
            format_id = row[0] if row else None
        
        if quality_preset:
            cursor.execute("SELECT id FROM media_hub_quality_preset WHERE slug = %s", [quality_preset])
            row = cursor.fetchone()
            quality_id = row[0] if row else None
    
    # Build input snapshot
    input_snapshot = json.dumps({
        'prompt': {'positive': prompt},
        'render': {'width': 1024, 'height': 1024},
        'sampler': {'steps': 25, 'cfg_scale': 7.5}
    })
    
    # Create job
    job_uuid = str(uuid.uuid4())
    
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO media_hub_render_job 
            (uuid, job_type, status, priority, ref_table, ref_id, input_snapshot, 
             error_message, attempt_count, max_attempts, created_at, updated_at,
             org_id, project_id, created_by_id, 
             style_preset_id, format_preset_id, quality_preset_id, voice_preset_id, workflow_id)
            VALUES (%s, %s, 'pending', %s, '', NULL, %s, 
                    '', 0, 3, NOW(), NOW(),
                    NULL, NULL, %s,
                    %s, %s, %s, NULL, NULL)
            RETURNING id
        """, [
            job_uuid, job_type, priority, input_snapshot,
            request.user.id if request.user.is_authenticated else None,
            style_id, format_id, quality_id
        ])
        job_id = cursor.fetchone()[0]
    
    return JsonResponse({'success': True, 'job_id': job_id, 'uuid': job_uuid})


@csrf_exempt
@require_http_methods(["POST"])
def cancel_job(request, job_id):
    """Cancel a pending job."""
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE media_hub_render_job 
            SET status = 'cancelled', updated_at = NOW()
            WHERE id = %s AND status IN ('pending', 'queued')
            RETURNING id
        """, [job_id])
        result = cursor.fetchone()
    
    if result:
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Job not found or cannot be cancelled'}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def retry_job(request, job_id):
    """Retry a failed job."""
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE media_hub_render_job 
            SET status = 'pending', error_message = '', updated_at = NOW()
            WHERE id = %s AND status = 'failed'
            RETURNING id
        """, [job_id])
        result = cursor.fetchone()
    
    if result:
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Job not found or cannot be retried'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_asset(request, asset_id):
    """Delete an asset and its files."""
    with connection.cursor() as cursor:
        # Delete files first (FK constraint)
        cursor.execute("DELETE FROM media_hub_asset_file WHERE asset_id = %s", [asset_id])
        # Delete asset
        cursor.execute("DELETE FROM media_hub_asset WHERE id = %s RETURNING id", [asset_id])
        result = cursor.fetchone()
    
    if result:
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Asset not found'}, status=404)


# ============================================
# Audio / TTS Views
# ============================================

@csrf_exempt
@require_http_methods(["POST"])
def submit_audio_job(request):
    """
    Submit an audio generation job.
    
    POST /media-hub/api/audio/generate/
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    text = data.get('text', '')
    chapter_id = data.get('chapter_id')
    
    if not text and not chapter_id:
        return JsonResponse({'error': 'Either text or chapter_id is required'}, status=400)
    
    job_type = 'audio_chapter' if chapter_id else 'audio_full'
    
    # Get voice preset ID
    voice_id = None
    if data.get('voice_preset'):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM media_hub_voice_preset WHERE slug = %s AND is_active = true",
                [data['voice_preset']]
            )
            row = cursor.fetchone()
            voice_id = row[0] if row else None
    
    input_snapshot = json.dumps({
        'text': text,
        'chapter_id': chapter_id,
        'voice_preset': data.get('voice_preset'),
        'engine': data.get('engine', 'xtts'),
    })
    
    job_uuid = str(uuid.uuid4())
    
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO media_hub_render_job 
            (uuid, job_type, status, priority, ref_table, ref_id, input_snapshot, 
             error_message, attempt_count, max_attempts, created_at, updated_at,
             org_id, project_id, created_by_id, 
             style_preset_id, format_preset_id, quality_preset_id, voice_preset_id, workflow_id)
            VALUES (%s, %s, 'pending', %s, %s, %s, %s, 
                    '', 0, 3, NOW(), NOW(),
                    %s, %s, %s,
                    NULL, NULL, NULL, %s, NULL)
            RETURNING id
        """, [
            job_uuid, job_type, data.get('priority', 5),
            'chapters_v2' if chapter_id else '', chapter_id, input_snapshot,
            data.get('org_id'), data.get('project_id'),
            request.user.id if request.user.is_authenticated else None,
            voice_id
        ])
        job_id = cursor.fetchone()[0]
    
    return JsonResponse({
        'success': True,
        'job_id': job_id,
        'uuid': job_uuid,
        'job_type': job_type,
        'status': 'pending',
    })


@require_http_methods(["GET"])
def list_voice_presets(request):
    """List available voice presets."""
    language = request.GET.get('language')
    
    query = """
        SELECT slug, name, description, engine, voice_id, language, gender
        FROM media_hub_voice_preset WHERE is_active = true
    """
    params = []
    
    if language:
        query += " AND language = %s"
        params.append(language)
    
    query += " ORDER BY language, name"
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = ['slug', 'name', 'description', 'engine', 'voice_id', 'language', 'gender']
        presets = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return JsonResponse({'presets': presets, 'count': len(presets)})


@require_http_methods(["GET"])
def tts_status(request):
    """Get TTS engine availability status."""
    from apps.media_hub.services.tts_service import TTSService
    
    tts = TTSService()
    available = tts.get_available_engines()
    
    engines = {}
    for name in ['xtts', 'openai', 'elevenlabs', 'mock']:
        engines[name] = name in available
    
    return JsonResponse({
        'available_engines': available,
        'engines': engines,
        'default_engine': tts.default_engine,
    })
