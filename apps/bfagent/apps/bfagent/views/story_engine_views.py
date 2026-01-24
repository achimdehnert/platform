"""
Story Engine Views
Chapter generation, beat management, and story bible operations
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.bfagent.handlers.processing_handlers.story_chapter_generate_handler import (
    StoryChapterGenerateHandler,
)
from apps.bfagent.models import ChapterBeat, StoryBible, StoryChapter, StoryCharacter, StoryStrand

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def beat_detail(request, pk):
    """
    Display beat details with chapter generation interface
    """
    beat = get_object_or_404(
        ChapterBeat.objects.select_related("story_bible", "strand").prefetch_related(
            "character_focus", "generated_chapters"
        ),
        pk=pk,
    )
    # Get existing chapters for this beat
    chapters = beat.generated_chapters.order_by("-version", "-created_at")
    context = {
        "beat": beat,
        "chapters": chapters,
        "has_chapters": chapters.exists(),
        "latest_chapter": chapters.first() if chapters.exists() else None,
    }
    return render(request, "bfagent/story_engine/beat_detail.html", context)


@login_required
@require_http_methods(["POST"])
def generate_chapter(request, beat_id):
    """
    Generate chapter from beat using AI
    HTMX endpoint - returns partial HTML
    """
    beat = get_object_or_404(ChapterBeat, pk=beat_id)
    # Get parameters from POST
    temperature = float(request.POST.get("temperature", 0.7))
    agent_id = request.POST.get("agent_id")
    try:
        # Initialize handler
        handler = StoryChapterGenerateHandler()
        # Generate chapter
        result = handler.execute(
            {
                "beat_id": beat_id,
                "temperature": temperature,
                "agent_id": int(agent_id) if agent_id else None,
            }
        )
        chapter = result["chapter"]
        # Return success partial
        context = {
            "success": True,
            "chapter": chapter,
            "word_count": result["word_count"],
            "quality_score": result["quality_score"],
            "message": result["message"],
        }
        return render(request, "bfagent/story_engine/partials/chapter_result.html", context)
    except Exception as e:
        logger.error(f"Chapter generation failed: {e}", exc_info=True)
        # Return error partial
        context = {
            "success": False,
            "error": str(e),
            "beat": beat,
        }
        return render(request, "bfagent/story_engine/partials/chapter_result.html", context)


@login_required
@require_http_methods(["GET"])
def chapter_preview(request, pk):
    """
    Display chapter preview
    """
    chapter = get_object_or_404(
        StoryChapter.objects.select_related("story_bible", "strand", "beat"), pk=pk
    )
    context = {
        "chapter": chapter,
    }
    return render(request, "bfagent/story_engine/chapter_preview.html", context)


@login_required
@require_http_methods(["GET"])
def story_bible_dashboard(request, pk):
    """
    Story Bible dashboard with strands, characters, and progress
    """
    bible = get_object_or_404(
        StoryBible.objects.prefetch_related("strands", "characters", "beats", "chapters"), pk=pk
    )
    # Calculate statistics
    total_beats = bible.beats.count()
    total_chapters = bible.chapters.count()
    total_words = sum(ch.word_count for ch in bible.chapters.all())
    # Get strands with chapter counts
    strands_data = []
    for strand in bible.strands.all():
        strands_data.append(
            {
                "strand": strand,
                "beat_count": strand.beats.count(),
                "chapter_count": strand.chapters.count(),
                "progress": (
                    (strand.chapters.count() / strand.beats.count() * 100)
                    if strand.beats.count() > 0
                    else 0
                ),
            }
        )
    context = {
        "bible": bible,
        "total_beats": total_beats,
        "total_chapters": total_chapters,
        "total_words": total_words,
        "strands_data": strands_data,
        "characters": bible.characters.all()[:10],
    }
    return render(request, "bfagent/story_engine/bible_dashboard.html", context)


@login_required
@require_http_methods(["GET"])
def beats_list(request):
    """
    List all beats with generation status
    """
    # Filter by story bible if specified
    bible_id = request.GET.get("bible_id")
    beats = ChapterBeat.objects.select_related("story_bible", "strand").prefetch_related(
        "generated_chapters"
    )
    if bible_id:
        beats = beats.filter(story_bible_id=bible_id)
    beats = beats.order_by("story_bible", "strand", "order")
    # Add generation status
    beats_data = []
    for beat in beats:
        chapters = beat.generated_chapters.all()
        beats_data.append(
            {
                "beat": beat,
                "has_chapters": chapters.exists(),
                "chapter_count": chapters.count(),
                "latest_version": (
                    chapters.order_by("-version").first().version if chapters.exists() else 0
                ),
            }
        )
    context = {
        "beats_data": beats_data,
        "bible_id": bible_id,
    }
    return render(request, "bfagent/story_engine/beats_list.html", context)
