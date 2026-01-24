"""
Story Views - Story Generation & Reading
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods

from .models import Story, Chapter, ReadingProgress
from apps.trips.models import Trip


@login_required
def story_list(request):
    """List all stories for the current user."""
    stories = Story.objects.filter(user=request.user).select_related('trip').order_by('-created_at')
    return render(request, 'stories/list.html', {'stories': stories})


@login_required
def story_detail(request, pk):
    """Story overview with chapters."""
    story = get_object_or_404(Story.objects.select_related('trip'), pk=pk, user=request.user)
    chapters = story.chapters.all()
    
    # Get reading progress
    reading_progress = ReadingProgress.objects.filter(story=story, user=request.user).first()
    
    return render(request, 'stories/detail.html', {
        'story': story,
        'chapters': chapters,
        'reading_progress': reading_progress,
    })


@login_required
def story_read(request, pk):
    """Start reading story - redirect to current/first chapter."""
    story = get_object_or_404(Story, pk=pk, user=request.user)
    
    progress, _ = ReadingProgress.objects.get_or_create(
        user=request.user,
        story=story,
    )
    
    chapter_num = progress.last_chapter if progress.last_chapter else 1
    return redirect('stories:chapter', story_id=story.pk, chapter_num=chapter_num)


@login_required
def chapter_read(request, story_id, chapter_num):
    """Read a specific chapter."""
    story = get_object_or_404(Story.objects.select_related('trip'), pk=story_id, user=request.user)
    chapters = story.chapters.all()
    current_chapter = get_object_or_404(Chapter, story=story, chapter_number=chapter_num)
    
    # Get previous/next chapters
    prev_chapter = chapters.filter(chapter_number__lt=chapter_num).order_by('-chapter_number').first()
    next_chapter = chapters.filter(chapter_number__gt=chapter_num).order_by('chapter_number').first()
    
    # Update reading progress
    progress, _ = ReadingProgress.objects.get_or_create(
        story=story,
        user=request.user,
    )
    progress.last_chapter = chapter_num
    if chapter_num > (progress.chapters_read or 0):
        progress.chapters_read = chapter_num
    progress.save()
    
    # Get list of read chapters for sidebar
    read_chapters = list(range(1, (progress.chapters_read or 0) + 1))
    
    return render(request, 'stories/read.html', {
        'story': story,
        'chapters': chapters,
        'current_chapter': current_chapter,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'read_chapters': read_chapters,
    })


@login_required
def story_progress(request, pk):
    """Show generation progress for a story."""
    story = get_object_or_404(Story.objects.select_related('trip'), pk=pk, user=request.user)
    
    return render(request, 'stories/progress.html', {
        'story': story,
    })


@login_required
def export_markdown(request, pk):
    """Export story as Markdown."""
    story = get_object_or_404(Story, pk=pk, user=request.user)
    chapters = story.chapters.all()
    
    lines = [
        f"# {story.title}",
        "",
        f"*{story.get_genre_display()} | ~{story.total_words:,} Wörter | {story.generated_chapters} Kapitel*",
        "",
        "---",
        "",
    ]
    
    for chapter in chapters:
        lines.extend([
            f"## Kapitel {chapter.chapter_number}: {chapter.title or 'Ohne Titel'}",
            "",
            chapter.content or "",
            "",
            "---",
            "",
        ])
    
    content = "\n".join(lines)
    
    response = HttpResponse(content, content_type='text/markdown')
    response['Content-Disposition'] = f'attachment; filename="{story.title}.md"'
    return response


@login_required
def export_pdf(request, pk):
    """Export story as PDF."""
    return HttpResponse("PDF-Export wird noch implementiert.", status=501)


@login_required
def api_story_status(request, pk):
    """API: Get story generation status."""
    story = get_object_or_404(Story, pk=pk, user=request.user)
    
    return JsonResponse({
        'status': story.status,
        'progress': story.progress_percent,
        'generated_chapters': story.generated_chapters,
        'total_chapters': story.total_chapters,
        'message': f'Kapitel {story.generated_chapters} von {story.total_chapters}',
        'phase': 'chapter' if story.status == 'generating' else '',
        'chapter': story.generated_chapters,
        'total': story.total_chapters,
    })
