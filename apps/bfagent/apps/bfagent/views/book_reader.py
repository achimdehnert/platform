"""
Book Reader View
Dynamic web interface for reading generated book chapters
"""

import markdown
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify

from apps.bfagent.models import BookProjects
from apps.core.services.export import BookExporter
from apps.core.services.storage import ContentStorageService


def book_reader(request, project_id=None):
    """
    Main book reader view
    Shows list of projects or specific book chapters
    """
    if project_id:
        # Show specific book
        project = get_object_or_404(BookProjects, id=project_id)
        project_slug = slugify(project.title)
        storage = ContentStorageService(project_slug)

        # Get chapters
        chapter_path = storage.get_chapter_path()
        chapters = sorted(chapter_path.glob("chapter_*.md")) if chapter_path.exists() else []

        chapter_list = []
        for chapter_file in chapters:
            # Extract chapter number from filename
            filename = chapter_file.stem
            if filename.startswith("chapter_"):
                try:
                    num = int(filename.split("_")[1])
                    chapter_list.append(
                        {
                            "number": num,
                            "filename": chapter_file.name,
                            "path": str(chapter_file),
                            "size": chapter_file.stat().st_size,
                        }
                    )
                except (ValueError, IndexError):
                    continue

        # Get project stats
        stats = storage.get_project_stats()

        context = {
            "project": project,
            "project_slug": project_slug,
            "chapters": chapter_list,
            "stats": stats,
            "total_chapters": len(chapter_list),
        }

        return render(request, "bfagent/book_reader.html", context)

    else:
        # Show all projects from database
        projects = BookProjects.objects.all().order_by("-updated_at")

        project_list = []
        for project in projects:
            project_slug = slugify(project.title)
            try:
                storage = ContentStorageService(project_slug)
                stats = storage.get_project_stats()
                has_content = stats.get("exists", False)
            except Exception:
                has_content = False
                stats = {}

            project_list.append(
                {
                    "id": project.id,
                    "title": project.title,
                    "genre": project.genre,
                    "slug": project_slug,
                    "chapters": stats.get("chapter_count", 0) if has_content else 0,
                    "words": stats.get("total_words", 0) if has_content else 0,
                    "has_content": has_content,
                }
            )

        context = {
            "projects": project_list,
        }

        return render(request, "bfagent/book_list.html", context)


def chapter_view(request, project_id, chapter_number):
    """
    View for reading a specific chapter
    """
    project = get_object_or_404(BookProjects, id=project_id)
    project_slug = slugify(project.title)

    storage = ContentStorageService(project_slug)
    chapter_path = storage.get_chapter_path()

    # Find chapter file
    chapter_file = chapter_path / f"chapter_{chapter_number:02d}.md"

    if not chapter_file.exists():
        raise Http404(f"Chapter {chapter_number} not found")

    # Read chapter content
    content = chapter_file.read_text(encoding="utf-8")

    # Convert markdown to HTML
    md = markdown.Markdown(extensions=["extra", "meta", "toc"])
    html_content = md.convert(content)

    # Get metadata
    metadata = getattr(md, "Meta", {})

    # Get all chapters for navigation
    chapters = sorted(chapter_path.glob("chapter_*.md"))
    chapter_numbers = []
    for ch in chapters:
        try:
            num = int(ch.stem.split("_")[1])
            chapter_numbers.append(num)
        except (ValueError, IndexError):
            continue

    # Determine prev/next
    prev_chapter = chapter_number - 1 if chapter_number > 1 else None
    next_chapter = chapter_number + 1 if chapter_number < max(chapter_numbers) else None

    # Get chapter object from database for comments
    try:
        from ..models import BookChapters

        chapter_obj = (
            BookChapters.objects.prefetch_related("comments", "comments__author")
            .filter(project=project, chapter_number=chapter_number)
            .first()
        )
    except Exception:
        chapter_obj = None

    context = {
        "project": project,
        "project_slug": project_slug,
        "chapter_number": chapter_number,
        "content": html_content,
        "raw_content": content,
        "metadata": metadata,
        "prev_chapter": prev_chapter,
        "next_chapter": next_chapter,
        "all_chapters": sorted(chapter_numbers),
        "word_count": len(content.split()),
        "chapter": chapter_obj,  # Add chapter object for comments
    }

    return render(request, "bfagent/chapter_reader.html", context)


def chapter_api(request, project_id, chapter_number):
    """
    API endpoint for chapter content (JSON)
    """
    project = get_object_or_404(BookProjects, id=project_id)
    project_slug = slugify(project.title)

    storage = ContentStorageService(project_slug)
    chapter_path = storage.get_chapter_path()
    chapter_file = chapter_path / f"chapter_{chapter_number:02d}.md"

    if not chapter_file.exists():
        return JsonResponse({"error": "Chapter not found"}, status=404)

    content = chapter_file.read_text(encoding="utf-8")

    # Convert to HTML
    md = markdown.Markdown(extensions=["extra", "meta"])
    html_content = md.convert(content)

    return JsonResponse(
        {
            "project_id": project_id,
            "chapter_number": chapter_number,
            "content_markdown": content,
            "content_html": html_content,
            "metadata": getattr(md, "Meta", {}),
            "word_count": len(content.split()),
        }
    )


def export_docx(request, project_id):
    """
    Export book to DOCX format
    """
    project = get_object_or_404(BookProjects, id=project_id)
    export_service = BookExporter()

    try:
        file_path = export_service.export_to_docx(project)
        response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=file_path.name)
        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def export_pdf(request, project_id):
    """
    Export book to PDF format
    """
    project = get_object_or_404(BookProjects, id=project_id)
    export_service = BookExporter()

    try:
        file_path = export_service.export_to_pdf(project)
        response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=file_path.name)
        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def export_epub(request, project_id):
    """
    Export book to EPUB format
    """
    project = get_object_or_404(BookProjects, id=project_id)
    export_service = BookExporter()

    try:
        file_path = export_service.export_to_epub(project)
        response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=file_path.name)
        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def chapter_edit(request, project_id, chapter_number):
    """
    Edit chapter with WYSIWYG editor (TipTap)
    """
    project = get_object_or_404(BookProjects, id=project_id)
    project_slug = slugify(project.title)

    storage = ContentStorageService(project_slug)
    chapter_path = storage.get_chapter_path()
    chapter_file = chapter_path / f"chapter_{chapter_number:02d}.md"

    if not chapter_file.exists():
        raise Http404(f"Chapter {chapter_number} not found")

    # Read chapter content
    content = chapter_file.read_text(encoding="utf-8")

    # Remove YAML frontmatter/metadata if present
    import re

    # Match YAML frontmatter pattern: --- at start, content, ---
    content_clean = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)

    # Convert markdown to HTML for editor
    md = markdown.Markdown(extensions=["extra"])
    html_content = md.convert(content_clean)

    # Get chapter object from database for comments
    try:
        from ..models import BookChapters

        chapter_obj = (
            BookChapters.objects.prefetch_related("comments", "comments__author")
            .filter(project=project, chapter_number=chapter_number)
            .first()
        )
    except Exception:
        chapter_obj = None

    context = {
        "project": project,
        "project_slug": project_slug,
        "chapter_number": chapter_number,
        "raw_content": html_content,
        "word_count": len(content_clean.split()),
        "chapter": chapter_obj,
    }

    return render(request, "bfagent/chapter_editor.html", context)


def save_chapter(request, project_id, chapter_number):
    """
    Save edited chapter content (AJAX endpoint)
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    import json
    import logging

    logger = logging.getLogger(__name__)

    project = get_object_or_404(BookProjects, id=project_id)
    project_slug = slugify(project.title)

    storage = ContentStorageService(project_slug)
    chapter_path = storage.get_chapter_path()
    chapter_file = chapter_path / f"chapter_{chapter_number:02d}.md"

    if not chapter_file.exists():
        return JsonResponse({"error": "Chapter not found"}, status=404)

    try:
        data = json.loads(request.body)
        html_content = data.get("content", "")

        # Convert HTML back to Markdown
        try:
            from markdownify import markdownify as md_convert

            markdown_content = md_convert(html_content)
        except ImportError:
            # Fallback: simple HTML tag removal
            import re

            markdown_content = re.sub("<[^<]+?>", "", html_content)

        # Save to file
        chapter_file.write_text(markdown_content, encoding="utf-8")

        logger.info(f"Saved chapter {chapter_number} for project {project_id}")

        return JsonResponse(
            {
                "success": True,
                "message": "Chapter saved successfully",
                "word_count": len(markdown_content.split()),
            }
        )

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return JsonResponse({"success": False, "error": f"Invalid JSON: {str(e)}"}, status=400)
    except Exception as e:
        logger.error(f"Error saving chapter: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def chapter_comment_add_reader(request, project_id, chapter_number):
    """
    Add comment to chapter (Reader-style URL)
    Wrapper that converts project_id + chapter_number to chapter_id
    """
    from ..models import BookChapters
    from . import chapter_comment_views

    # Get chapter by project and number
    try:
        chapter = BookChapters.objects.get(project_id=project_id, chapter_number=chapter_number)
        # Forward to the actual comment view using chapter_id
        return chapter_comment_views.chapter_comment_add(request, chapter.pk)
    except BookChapters.DoesNotExist:
        raise Http404(f"Chapter {chapter_number} not found in project {project_id}")


def chapter_comments_reader(request, project_id, chapter_number):
    """
    List comments for chapter (Reader-style URL)
    Wrapper that converts project_id + chapter_number to chapter_id
    """
    from ..models import BookChapters
    from . import chapter_comment_views

    # Get chapter by project and number
    try:
        chapter = BookChapters.objects.get(project_id=project_id, chapter_number=chapter_number)
        # Forward to the actual comments list view
        return chapter_comment_views.chapter_comments_list(request, chapter.pk)
    except BookChapters.DoesNotExist:
        raise Http404(f"Chapter {chapter_number} not found in project {project_id}")
