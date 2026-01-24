"""
Chapter Edit Views - Book Writing Domain
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden

from apps.bfagent.models import BookProjects, BookChapters

import logging

logger = logging.getLogger(__name__)


@login_required
def chapter_edit(request, project_id, chapter_id):
    """
    Edit a single chapter
    
    GET: Show editor form
    POST: Save chapter changes
    """
    # Get project and verify ownership
    project = get_object_or_404(
        BookProjects,
        id=project_id,
        user=request.user
    )
    
    # Get chapter
    chapter = get_object_or_404(
        BookChapters,
        id=chapter_id,
        project=project
    )
    
    if request.method == 'POST':
        # Update chapter fields
        chapter.title = request.POST.get('title', chapter.title)
        chapter.outline = request.POST.get('outline', chapter.outline)
        chapter.content = request.POST.get('content', chapter.content)
        chapter.notes = request.POST.get('notes', chapter.notes)
        chapter.target_word_count = int(request.POST.get('target_word_count', chapter.target_word_count))
        
        # Update writing stage if provided
        writing_stage = request.POST.get('writing_stage')
        if writing_stage in ['planning', 'drafting', 'revising', 'completed']:
            chapter.writing_stage = writing_stage
        
        # Calculate word count from content
        if chapter.content:
            chapter.word_count = len(chapter.content.split())
        
        chapter.save()
        
        logger.info(f"Chapter {chapter.id} updated by user {request.user.id}")
        messages.success(request, f'Chapter "{chapter.title}" erfolgreich gespeichert!')
        
        return redirect('bfagent:project-detail', pk=project.id)
    
    # GET: Show form
    context = {
        'project': project,
        'chapter': chapter,
    }
    
    return render(request, 'bfagent/chapter_edit.html', context)
