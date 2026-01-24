"""
Chapter Regeneration Handler V2.0
==================================

Production-ready handler with Pydantic validation and transaction safety.

Integrates user feedback into chapter regeneration using the BaseHandler framework.

Features:
- Three-phase processing (Input → Process → Output)
- Pydantic validation for type safety
- Transaction safety with automatic rollback
- Structured output extraction (prevents LLM meta-commentary)
- Original parameter preservation
- Comprehensive error handling

Author: BF Agent Framework
Date: 2025-11-02
"""

import logging
from typing import Any, Dict, List, Optional

from django.template.defaultfilters import slugify
from django.utils import timezone
from pydantic import BaseModel, Field, validator

from apps.bfagent.handlers.base_handler_v2 import BaseHandler, ProcessingError
from apps.bfagent.handlers.processing_handlers.llm_call_handler import LLMCallHandler
from apps.bfagent.models import BookChapters, BookProjects, Comment
from apps.core.services.storage import StorageService

logger = logging.getLogger(__name__)


class ChapterRegenerateHandlerV2(BaseHandler):
    """
    Handler for regenerating chapters with user feedback

    INPUT PHASE:
    - Validates chapter exists and accessible
    - Validates feedback types are valid
    - Validates optional override parameters

    PROCESSING PHASE:
    - Loads approved comments (status='addressed' or 'acknowledged')
    - Loads original generation parameters from metadata
    - Builds feedback-enhanced prompt with structured markers
    - Calls LLM to generate new content
    - Extracts clean content (removes meta-commentary)
    - Updates chapter with new content and metadata

    OUTPUT PHASE:
    - Returns structured response with metrics
    - Includes word count, feedback count, saved path
    - Preserves generation parameters for future regeneration
    """

    handler_name = "chapter_regenerate_with_feedback"
    handler_version = "2.0.0"
    domain = "bookwriting"
    category = "content_generation"

    # ==================== INPUT SCHEMA ====================

    class InputSchema(BaseModel):
        """Input validation schema"""

        project_id: int = Field(gt=0, description="Book project ID")
        chapter_id: int = Field(gt=0, description="Chapter to regenerate")

        include_feedback_types: List[str] = Field(
            default=["suggestion", "concern", "general"],
            description="Types of comments to integrate (e.g., 'suggestion', 'concern')",
        )

        # Optional parameter overrides
        style_notes: Optional[str] = Field(
            None, max_length=500, description="Override style notes (e.g., 'More suspenseful')"
        )
        include_dialogue: Optional[bool] = Field(
            None, description="Override dialogue inclusion setting"
        )
        target_word_count: Optional[int] = Field(
            None, ge=100, le=10000, description="Target word count for regenerated chapter"
        )

        agent_id: Optional[int] = Field(
            None, description="LLM agent ID to use (default: project default)"
        )

        # Advanced options
        detect_conflicts: bool = Field(
            False, description="Run conflict detection on feedback (experimental)"
        )
        force_regenerate: bool = Field(
            False, description="Regenerate even if no approved feedback available"
        )
        test_mode: bool = Field(
            False, description="Use all comments regardless of status (for testing)"
        )

        @validator("include_feedback_types")
        def validate_feedback_types(cls, v):
            """Ensure feedback types are valid"""
            valid_types = {"general", "suggestion", "question", "praise", "concern", "typo"}

            if not v:
                raise ValueError("Must include at least one feedback type")

            invalid = set(v) - valid_types
            if invalid:
                raise ValueError(
                    f"Invalid feedback types: {invalid}. " f"Valid types: {valid_types}"
                )

            return v

        class Config:
            schema_extra = {
                "example": {
                    "project_id": 1,
                    "chapter_id": 2,
                    "include_feedback_types": ["suggestion", "concern"],
                    "style_notes": "More suspenseful and fast-paced",
                    "agent_id": 1,
                    "detect_conflicts": False,
                    "force_regenerate": False,
                }
            }

    # ==================== OUTPUT SCHEMA ====================

    class OutputSchema(BaseModel):
        """Output validation schema"""

        success: bool = True
        action: str = "regenerate_chapter_with_feedback"

        data: Dict[str, Any] = Field(..., description="Regeneration results and metadata")

        message: str = Field(..., description="Human-readable result message")

        warnings: List[str] = Field(
            default_factory=list,
            description="Non-fatal warnings (e.g., no approved feedback found)",
        )

        @validator("data")
        def validate_data_fields(cls, v):
            """Ensure required fields are present in data"""
            required = {"chapter_id", "content", "word_count", "feedback_integrated", "saved_path"}
            missing = required - set(v.keys())
            if missing:
                raise ValueError(f"Missing required data fields: {missing}")
            return v

        class Config:
            schema_extra = {
                "example": {
                    "success": True,
                    "action": "regenerate_chapter_with_feedback",
                    "data": {
                        "chapter_id": 2,
                        "content": "Hugo stepped into the café...",
                        "word_count": 2847,
                        "feedback_integrated": 5,
                        "saved_path": "storage/chapters/chapter_2.txt",
                        "metadata": {
                            "style_notes": "Engaging, emotional",
                            "include_dialogue": True,
                        },
                    },
                    "message": "Regenerated chapter 2 with 5 feedback items",
                    "warnings": [],
                }
            }

    # ==================== INITIALIZATION ====================

    def __init__(self):
        super().__init__()
        self.storage_service = StorageService()
        self.llm_handler = LLMCallHandler()

    # ==================== PROCESSING ====================

    def process(self, validated_input: InputSchema) -> Dict[str, Any]:
        """
        Main processing logic with transaction safety

        All database operations are wrapped in transaction.atomic()
        by the base handler, so any exception will rollback changes.
        """
        warnings = []

        # 1. Load chapter and project
        chapter = self._load_chapter(validated_input.chapter_id)
        project = chapter.project

        # Verify project access
        if project.id != validated_input.project_id:
            raise ProcessingError(
                f"Chapter {chapter.id} does not belong to project {validated_input.project_id}"
            )

        # 2. Load approved comments
        comments = self._load_approved_comments(
            chapter,
            validated_input.include_feedback_types,
            validated_input.test_mode,
            validated_input.force_regenerate,
        )

        # Warn if no comments found
        if not comments:
            if validated_input.force_regenerate:
                warnings.append("No feedback available, regenerating without feedback")
            else:
                warnings.append(
                    "No approved feedback found. Using test mode (all comments). "
                    "Set test_mode=True or force_regenerate=True to suppress this warning."
                )
                # Fallback to test mode
                comments = self._load_all_comments(chapter, validated_input.include_feedback_types)

        # 3. Detect conflicts if enabled (experimental)
        if validated_input.detect_conflicts and len(comments) > 1:
            conflicts = self._detect_feedback_conflicts(comments)
            if conflicts:
                warnings.extend([f"Conflict detected: {c['description']}" for c in conflicts])

        # 4. Load original generation parameters
        params = self._load_generation_params(chapter)

        # 5. Apply user overrides
        if validated_input.style_notes:
            params["style_notes"] = validated_input.style_notes
        if validated_input.include_dialogue is not None:
            params["include_dialogue"] = validated_input.include_dialogue
        if validated_input.target_word_count:
            params["target_word_count"] = validated_input.target_word_count

        # 6. Build feedback-enhanced prompt
        feedback_text = self._build_feedback_section(comments)

        # 7. Generate with LLM
        content = self._generate_content_with_feedback(
            project, chapter, params, feedback_text, validated_input.agent_id
        )

        # 8. Save chapter content
        project_slug = slugify(project.title)
        try:
            file_path = self.storage_service.save_chapter(
                project_slug=project_slug,
                chapter_number=chapter.chapter_number,
                content=content,
                metadata={
                    "regenerated": True,
                    "regenerated_at": timezone.now().isoformat(),
                    "feedback_count": len(comments),
                    "generation_params": params,
                    "word_count": len(content.split()),
                    "handler_version": self.handler_version,
                },
            )
            saved_path = str(file_path)
        except Exception as e:
            logger.error(f"Failed to save regenerated chapter: {e}")
            saved_path = None
            warnings.append(f"Failed to save to file: {e}")

        # 9. Update chapter model (within transaction)
        chapter.content = content
        if not chapter.metadata:
            chapter.metadata = {}
        chapter.metadata["generation_params"] = params
        chapter.metadata["feedback_integrated"] = len(comments)
        chapter.metadata["regenerated_at"] = timezone.now().isoformat()
        chapter.metadata["handler_version"] = self.handler_version
        chapter.save()

        # 10. Return results
        return {
            "chapter_id": chapter.id,
            "content": content,
            "word_count": len(content.split()),
            "feedback_integrated": len(comments),
            "conflicts_detected": len([w for w in warnings if "Conflict" in w]),
            "saved_path": saved_path,
            "metadata": params,
            "warnings": warnings,
            "message": f"Regenerated chapter {chapter.id} with {len(comments)} feedback items",
        }

    # ==================== HELPER METHODS ====================

    def _load_chapter(self, chapter_id: int) -> BookChapters:
        """Load chapter with error handling"""
        try:
            return BookChapters.objects.select_related("project").get(id=chapter_id)
        except BookChapters.DoesNotExist:
            raise ProcessingError(f"Chapter {chapter_id} not found")

    def _load_approved_comments(
        self,
        chapter: BookChapters,
        feedback_types: List[str],
        test_mode: bool = False,
        force: bool = False,
    ) -> List[Comment]:
        """Load approved comments for regeneration"""

        query = Comment.objects.filter(chapter=chapter, comment_type__in=feedback_types)

        if not test_mode and not force:
            # Only approved comments
            query = query.filter(status__in=["acknowledged", "addressed"])

        comments = list(query.select_related("author").order_by("created_at"))

        self.logger.info(
            f"Loaded {len(comments)} comments for chapter {chapter.id} "
            f"(types: {feedback_types}, test_mode: {test_mode})"
        )

        return comments

    def _load_all_comments(self, chapter: BookChapters, feedback_types: List[str]) -> List[Comment]:
        """Load all comments (test mode fallback)"""
        comments = list(
            Comment.objects.filter(chapter=chapter, comment_type__in=feedback_types)
            .select_related("author")
            .order_by("created_at")
        )

        self.logger.warning(
            f"Test mode: Loaded all {len(comments)} comments for chapter {chapter.id}"
        )

        return comments

    def _load_generation_params(self, chapter: BookChapters) -> Dict[str, Any]:
        """Load original generation parameters from metadata"""
        if not chapter.metadata:
            self.logger.warning(
                f"No generation parameters found for chapter {chapter.id}, using defaults"
            )
            return {
                "style_notes": "Engaging and compelling",
                "include_dialogue": True,
                "target_word_count": 3000,
            }

        params = chapter.metadata.get("generation_params", {})

        # Ensure defaults
        params.setdefault("style_notes", "Engaging and compelling")
        params.setdefault("include_dialogue", True)
        params.setdefault("target_word_count", 3000)

        self.logger.info(
            f"Loaded generation params for chapter {chapter.id}: {list(params.keys())}"
        )

        return params

    def _build_feedback_section(self, comments: List[Comment]) -> str:
        """Build feedback section for prompt"""
        if not comments:
            return ""

        feedback_text = "\n\nUSER FEEDBACK TO INTEGRATE:\n"
        for i, comment in enumerate(comments, 1):
            feedback_text += f"{i}. [{comment.comment_type.upper()}] {comment.text}\n"
            if comment.author_reply:
                feedback_text += f"   Author response: {comment.author_reply}\n"

        feedback_text += "\nPlease integrate this feedback naturally into the revised chapter."

        return feedback_text

    def _generate_content_with_feedback(
        self,
        project: BookProjects,
        chapter: BookChapters,
        params: Dict[str, Any],
        feedback_text: str,
        agent_id: Optional[int] = None,
    ) -> str:
        """
        Generate chapter content with integrated user feedback

        Uses structured output markers to extract clean content.
        """

        # Build prompt
        system_prompt = """You are a professional fiction writer specialized in revising and improving chapter content based on user feedback.
Your task is to rewrite the chapter while naturally integrating the feedback without disrupting the story flow."""

        user_prompt = f"""Rewrite Chapter {chapter.chapter_number} integrating user feedback.

PROJECT CONTEXT:
- Title: {project.title}
- Genre: {project.genre or 'Fiction'}
- Premise: {(project.premise or 'N/A')[:300]}

CHAPTER OUTLINE:
{chapter.title}
{chapter.summary or 'N/A'}

STYLE PARAMETERS:
- Style Notes: {params.get('style_notes', 'Engaging and compelling')}
- Include Dialogue: {params.get('include_dialogue', True)}
- Target Word Count: {params.get('target_word_count', 3000)} words
{feedback_text}

OUTPUT FORMAT - STRUCTURED RESPONSE:
<<<CHAPTER_START>>>
[Rewritten chapter content with feedback integrated]
<<<CHAPTER_END>>>

CRITICAL INSTRUCTIONS:
1. Integrate feedback naturally into the narrative
2. Maintain consistency with project context
3. Preserve the chapter's core purpose and beats
4. Do NOT break story flow or character consistency
5. Write ONLY the story content (no meta-commentary about feedback)

IMPORTANT:
- Everything between <<<CHAPTER_START>>> and <<<CHAPTER_END>>> must be pure story content
- NO explanations, NO meta-commentary, NO analysis
- Just the chapter text itself

Rewrite the chapter now:"""

        # Call LLM
        try:
            response = self.llm_handler.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_id=agent_id,
                max_tokens=8000,  # Long-form content
                temperature=0.7,  # Creative but consistent
            )

            self.logger.info(
                f"LLM generation completed for chapter {chapter.id}, "
                f"response length: {len(response)}"
            )

            # Extract clean content
            content = self._extract_chapter_content(response)

            return content

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise ProcessingError(f"LLM generation failed: {e}")

    def _extract_chapter_content(self, response: str) -> str:
        """
        Extract clean chapter content from LLM response

        INNOVATION: This prevents LLM meta-commentary pollution!

        LLMs often add unwanted analysis like:
        "This chapter demonstrates character growth..."

        By using structured markers, we extract ONLY the story content.
        """
        start_marker = "<<<CHAPTER_START>>>"
        end_marker = "<<<CHAPTER_END>>>"

        start_idx = response.find(start_marker)
        end_idx = response.find(end_marker)

        if start_idx == -1 or end_idx == -1:
            self.logger.warning(
                "Structured markers not found in response. "
                f"Has start: {start_idx != -1}, Has end: {end_idx != -1}. "
                "Using full response (may contain meta-commentary)"
            )
            # Fallback: use entire response
            return response.strip()

        start_idx += len(start_marker)
        content = response[start_idx:end_idx].strip()

        self.logger.info(
            f"Extracted chapter content using structured markers, "
            f"content length: {len(content)}"
        )

        return content

    def _detect_feedback_conflicts(self, comments: List[Comment]) -> List[Dict[str, Any]]:
        """
        Detect conflicting feedback suggestions (experimental)

        Uses simple heuristics for MVP. Could be enhanced with LLM analysis.
        """
        conflicts = []

        # Simple keyword-based conflict detection
        conflict_patterns = [
            (["aggressive", "violent", "dark"], ["gentle", "compassionate", "peaceful", "light"]),
            (["fast", "quick", "rapid", "rushed"], ["slow", "gradual", "measured", "deliberate"]),
            (["add", "expand", "elaborate", "more"], ["remove", "reduce", "simplify", "less"]),
            (["darker", "serious", "grim"], ["lighter", "humorous", "funny", "cheerful"]),
        ]

        for pattern_a, pattern_b in conflict_patterns:
            comments_with_a = [
                c for c in comments if any(keyword in c.text.lower() for keyword in pattern_a)
            ]
            comments_with_b = [
                c for c in comments if any(keyword in c.text.lower() for keyword in pattern_b)
            ]

            if comments_with_a and comments_with_b:
                conflicts.append(
                    {
                        "comment_ids": [c.id for c in comments_with_a + comments_with_b],
                        "description": f"Conflicting suggestions: {'/'.join(pattern_a)} vs {'/'.join(pattern_b)}",
                        "severity": "medium",
                    }
                )

        if conflicts:
            self.logger.warning(f"Detected {len(conflicts)} potential feedback conflicts")

        return conflicts
