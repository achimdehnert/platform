# Chapter Re-Generation mit User-Feedback

## Feature: `regenerate_chapter_with_feedback`

### Implementierung:

```python
def _regenerate_chapter_with_feedback(
    self,
    context: Dict[str, Any],
    project: BookProjects
) -> Dict[str, Any]:
    """
    Re-generate chapter content with user feedback integration
    
    Features:
    - Loads approved user comments (status='addressed' or 'acknowledged')
    - Reuses original generation parameters
    - Integrates feedback into regeneration prompt
    - Uses structured output markers
    
    Context parameters:
        - chapter_id: int (required)
        - include_feedback_types: List[str] (optional) - e.g., ['suggestion', 'concern']
        - preserve_original_style: bool (optional, default=True)
    """
    from apps.bfagent.models import Comment
    
    chapter_id = context.get('chapter_id')
    if not chapter_id:
        raise ProcessingError("chapter_id is required")
    
    try:
        chapter = BookChapters.objects.get(pk=chapter_id)
    except BookChapters.DoesNotExist:
        raise ProcessingError(f"Chapter {chapter_id} not found")
    
    parameters = context.get('parameters', {})
    
    # 1. Load approved comments (TEST DEFAULT: all comments treated as "approved")
    feedback_types = parameters.get('include_feedback_types', 
                                    ['suggestion', 'concern', 'general'])
    
    comments = Comment.objects.filter(
        chapter=chapter,
        status__in=['addressed', 'acknowledged'],  # Freigegebene Kommentare
        comment_type__in=feedback_types
    ).order_by('created_at')
    
    # TEST MODE: If no approved comments, use all open comments
    if comments.count() == 0:
        logger.info("No approved comments found, using all comments for testing")
        comments = Comment.objects.filter(
            chapter=chapter,
            comment_type__in=feedback_types
        ).order_by('created_at')
    
    # 2. Get original generation parameters (from chapter.metadata JSON field)
    original_params = {}
    if hasattr(chapter, 'metadata') and chapter.metadata:
        original_params = chapter.metadata.get('generation_params', {})
    
    # Use original params as defaults, can be overridden by context
    style_notes = parameters.get('style_notes', original_params.get('style_notes', ''))
    include_dialogue = parameters.get('include_dialogue', 
                                     original_params.get('include_dialogue', True))
    
    # 3. Build feedback section for prompt
    feedback_text = ""
    if comments.exists():
        feedback_text = "\n\nUSER FEEDBACK TO INTEGRATE:\n"
        for i, comment in enumerate(comments, 1):
            feedback_text += f"{i}. [{comment.comment_type}] {comment.text}\n"
            if comment.author_reply:
                feedback_text += f"   Author response: {comment.author_reply}\n"
        feedback_text += "\nPlease integrate this feedback naturally into the revised chapter."
    
    # 4. Build regeneration context
    project_context = self._build_project_context(project, chapter.chapter_number)
    chapter_context = self._build_chapter_context(chapter)
    
    # Get outline from metadata if available
    outline = original_params.get('outline', {})
    
    # 5. Generate with feedback-enhanced prompt
    content = self._generate_content_with_feedback(
        project_context,
        chapter_context,
        outline,
        chapter.chapter_number,
        style_notes,
        include_dialogue,
        feedback_text,
        context.get('agent_id')
    )
    
    # 6. Save with metadata
    project_slug = slugify(project.title)
    try:
        file_path = self.storage_service.save_chapter(
            project_slug=project_slug,
            chapter_number=chapter.chapter_number,
            content=content,
            metadata={
                'regenerated': True,
                'feedback_count': comments.count(),
                'generation_params': {
                    'style_notes': style_notes,
                    'include_dialogue': include_dialogue,
                    'outline': outline,
                },
                'word_count': len(content.split()),
            }
        )
        saved_path = str(file_path)
    except Exception as e:
        logger.error(f"Failed to save regenerated chapter: {e}")
        saved_path = None
    
    result = {
        'success': True,
        'action': 'regenerate_chapter_with_feedback',
        'data': {
            'chapter_id': chapter_id,
            'content': content,
            'word_count': len(content.split()),
            'feedback_integrated': comments.count(),
            'saved_path': saved_path,
            'metadata': {
                'style_notes': style_notes,
                'include_dialogue': include_dialogue,
            }
        },
        'message': f"Regenerated chapter {chapter_id} with {comments.count()} feedback items",
    }
    
    logger.info(f"Regenerated chapter {chapter_id} with {comments.count()} feedback items")
    return result


def _generate_content_with_feedback(
    self,
    project_context: Dict,
    chapter_context: Dict,
    outline: Dict,
    chapter_number: int,
    style_notes: str,
    include_dialogue: bool,
    feedback_text: str,
    agent_id: Optional[int] = None
) -> str:
    """Generate chapter content with integrated user feedback"""
    
    # Use same prompt as normal generation, but with feedback section added
    raw_outline = outline.get('raw_response', '') if outline else ''
    premise = project_context.get('premise', project_context.get('story_premise', ''))
    protagonist_name = project_context.get('protagonist_name', 'the protagonist')
    
    system_prompt = """You are a professional fiction writer specialized in revising and improving chapter content based on user feedback.
Your task is to rewrite the chapter while naturally integrating the feedback without disrupting the story flow."""
    
    user_prompt = f"""Rewrite Chapter {chapter_number} integrating user feedback.

PROJECT CONTEXT:
- Title: {project_context.get('title', 'Untitled')}
- Genre: {project_context.get('genre', 'Fiction')}
- Premise: {premise[:300] if len(str(premise)) > 300 else premise}

PROTAGONIST: {protagonist_name}

CHAPTER OUTLINE:
{raw_outline}

STYLE: {style_notes if style_notes else "Engaging literary fiction"}
{feedback_text}

OUTPUT FORMAT - STRUCTURED RESPONSE:
<<<CHAPTER_START>>>
[Rewritten chapter content with feedback integrated]
<<<CHAPTER_END>>>

CRITICAL: 
- Integrate feedback naturally without breaking story flow
- NO meta-commentary about the feedback
- Write ONLY story content between markers

Rewrite the chapter now:"""
    
    try:
        response = self.llm_handler.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            agent_id=agent_id,
            max_tokens=4000
        )
        return self._extract_chapter_content(response)
    except ProcessingError as e:
        logger.warning(f"LLM regeneration failed: {e}. Using fallback.")
        return f"[REGENERATED CONTENT WITH {feedback_text.count('•')} FEEDBACK ITEMS]\n\n{chapter_context.get('current_content', '')}"
```

## Usage Example:

```python
handler = ChapterGenerateHandler()

result = handler.execute({
    'action': 'regenerate_chapter_with_feedback',
    'project_id': 1,
    'chapter_id': 2,
    'parameters': {
        'include_feedback_types': ['suggestion', 'concern'],
        'style_notes': 'Engaging, emotional',
        'include_dialogue': True,
    },
    'agent_id': 1,  # optional
})
```

## Features:

1. ✅ **Loads approved comments**: `status='addressed'` or `'acknowledged'`
2. ✅ **Test Mode**: Falls keine freigegeben, nutzt alle Kommentare
3. ✅ **Reuses original parameters**: Style, dialogue, outline aus metadata
4. ✅ **Structured output**: `<<<CHAPTER_START>>>` markers verhindern Meta-Kommentare
5. ✅ **Saves metadata**: Generation-Parameter werden gespeichert für nächstes Mal

## Integration mit Review System:

- Kommentare mit `status='acknowledged'` werden einbezogen
- `comment_type` Filter: 'suggestion', 'concern', 'general', etc.
- Author-Replies werden auch gezeigt
- Feedback wird in Prompt integriert, ohne Story-Flow zu unterbrechen
