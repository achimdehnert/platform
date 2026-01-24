"""
Chapter Review Handler - Phase 6: Quality Feedback
Handler for AI-assisted chapter review and quality analysis
"""

import json
import logging
import re
from typing import Any, Dict, List

from django.conf import settings

from apps.bfagent.domains.book_writing.services.llm_service import LLMService
from apps.bfagent.models import BookChapters, BookProjects

logger = logging.getLogger(__name__)


class ChapterReviewHandler:
    """
    Review chapter and provide quality feedback using LLM

    Input:
    - chapter_id: int (BookChapters ID)
    - review_type: str (optional: 'quick', 'standard', 'deep')
    - focus_areas: list (optional: ['structure', 'prose', 'dialogue', 'pacing'])

    Output:
    - overall_score: int (1-10)
    - strengths: list of str
    - weaknesses: list of str
    - suggestions: list of dict with:
      - issue: str
      - location: str (where in chapter)
      - severity: str ('low', 'medium', 'high')
      - fix: str (how to fix it)
    - detailed_feedback: dict with:
      - structure: str
      - prose: str
      - dialogue: str
      - pacing: str
      - consistency: str
    - success: bool
    - usage: dict (LLM usage stats)
    """

    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Review chapter with LLM"""
        chapter_id = data.get("chapter_id")

        if not chapter_id:
            return {"success": False, "error": "chapter_id required"}

        try:
            chapter = BookChapters.objects.select_related("project").get(id=chapter_id)
        except BookChapters.DoesNotExist:
            return {"success": False, "error": f"Chapter {chapter_id} not found"}

        # Check if chapter has content
        if not chapter.content or len(chapter.content.strip()) < 100:
            return {
                "success": False,
                "error": "Chapter must have at least 100 characters of content to review",
            }

        # Check API key
        api_key_available = getattr(settings, "OPENAI_API_KEY", None) or getattr(
            settings, "ANTHROPIC_API_KEY", None
        )

        if not api_key_available:
            return {"success": False, "error": "No LLM API key configured"}

        # Build context
        context = {
            "chapter": {
                "number": chapter.chapter_number,
                "title": chapter.title,
                "content": chapter.content,
                "word_count": len(chapter.content.split()),
            },
            "project": {
                "title": chapter.project.title,
                "genre": chapter.project.genre or "Fiction",
            },
            "review_type": data.get("review_type", "standard"),
            "focus_areas": data.get("focus_areas", ["structure", "prose", "dialogue", "pacing"]),
        }

        # Build prompt
        prompt = ChapterReviewHandler._build_prompt(context)

        # Generate with LLM
        provider = getattr(settings, "LLM_PROVIDER", "openai")
        model = getattr(settings, "LLM_MODEL", None)
        llm = LLMService(provider=provider, model=model)

        # Use higher max_tokens for review (detailed feedback)
        max_tokens = 2000 if context["review_type"] == "deep" else 1500

        result = llm.generate_chapter_content(
            prompt=prompt, max_tokens=max_tokens, temperature=0.7, quality="best"  # Critical analysis
        )

        if not result["success"]:
            return result

        # Parse review
        parsed = ChapterReviewHandler._parse_review(result["content"])

        logger.info(f"Reviewed chapter {chapter_id}: Score {parsed.get('overall_score', 'N/A')}/10")

        return {
            "success": True,
            **parsed,
            "chapter_id": chapter_id,
            "review_type": context["review_type"],
            "raw_content": result["content"],
            "usage": result.get("usage"),
            "cost": llm.calculate_cost(result["usage"]) if result.get("usage") else 0,
        }

    @staticmethod
    def _build_prompt(context: Dict) -> str:
        """Build LLM prompt for chapter review"""
        chapter = context["chapter"]
        project = context["project"]
        review_type = context["review_type"]
        focus_areas = context["focus_areas"]

        parts = [
            "# Task: Review Chapter Quality",
            "",
            "You are an experienced editor and writing coach reviewing a chapter for publication quality.",
            "",
            "## Chapter Information:",
            f"- **Book:** {project['title']}",
            f"- **Genre:** {project['genre']}",
            f"- **Chapter:** {chapter['number']} - {chapter['title']}",
            f"- **Word Count:** {chapter['word_count']}",
            "",
            f"## Review Type: {review_type.upper()}",
        ]

        if review_type == "quick":
            parts.append("- Focus on major issues only")
            parts.append("- 2-3 minute review")
        elif review_type == "deep":
            parts.append("- Comprehensive analysis")
            parts.append("- Detailed line-by-line feedback")
        else:  # standard
            parts.append("- Balanced review of key areas")
            parts.append("- 5-7 minute review")

        parts.extend(
            [
                "",
                "## Chapter Content:",
                "```",
                chapter["content"][:4000],  # Limit to prevent token overflow
                "```",
                "",
                "## Your Task:",
                "",
                "Provide a comprehensive chapter review covering:",
            ]
        )

        # Add focus areas
        if "structure" in focus_areas:
            parts.extend(
                [
                    "",
                    "### 1. STRUCTURE",
                    "- Does the chapter have a clear beginning, middle, and end?",
                    "- Is there a narrative arc (tension → climax → resolution)?",
                    "- Are scenes well-paced and transitions smooth?",
                    "- Does it advance the plot or develop characters?",
                ]
            )

        if "prose" in focus_areas:
            parts.extend(
                [
                    "",
                    "### 2. PROSE QUALITY",
                    "- Is the writing clear and engaging?",
                    "- Are there awkward sentences or repetitive phrasing?",
                    "- Does it 'show' rather than 'tell'?",
                    "- Is the voice consistent?",
                ]
            )

        if "dialogue" in focus_areas:
            parts.extend(
                [
                    "",
                    "### 3. DIALOGUE",
                    "- Does each character have a distinct voice?",
                    "- Is dialogue natural and purposeful?",
                    "- Are dialogue tags used effectively?",
                    "- Does dialogue advance plot or reveal character?",
                ]
            )

        if "pacing" in focus_areas:
            parts.extend(
                [
                    "",
                    "### 4. PACING",
                    "- Does the chapter move at an appropriate speed?",
                    "- Are there sections that drag or rush?",
                    "- Is tension maintained throughout?",
                    "- Does the ending make readers want to continue?",
                ]
            )

        parts.extend(
            [
                "",
                "### 5. OVERALL ASSESSMENT",
                "- Rate the chapter 1-10 (1=needs major revision, 10=publication ready)",
                "- What are 3-5 key strengths?",
                "- What are 3-5 key weaknesses?",
                "- Provide 5-7 specific, actionable suggestions for improvement",
                "",
                "## Output Format:",
                "",
                "Return your response as JSON:",
                "",
                "```json",
                "{",
                '  "overall_score": 7,',
                '  "strengths": [',
                '    "Strong opening hook that grabs attention",',
                '    "Character voices are distinct and believable",',
                '    "..."',
                "  ],",
                '  "weaknesses": [',
                '    "Middle section drags with too much exposition",',
                '    "Ending feels abrupt",',
                '    "..."',
                "  ],",
                '  "suggestions": [',
                "    {",
                '      "issue": "Specific problem identified",',
                '      "location": "Where in chapter (beginning/middle/end or paragraph)",',
                '      "severity": "high/medium/low",',
                '      "fix": "Concrete suggestion for fixing the issue"',
                "    }",
                "  ],",
                '  "detailed_feedback": {',
                '    "structure": "Detailed assessment of chapter structure...",',
                '    "prose": "Analysis of prose quality...",',
                '    "dialogue": "Feedback on dialogue...",',
                '    "pacing": "Comments on pacing...",',
                '    "consistency": "Notes on consistency with story/genre..."',
                "  }",
                "}",
                "```",
                "",
                "Make your review:",
                "- Constructive and actionable",
                "- Specific (point to actual examples when possible)",
                "- Balanced (acknowledge both strengths and weaknesses)",
                f"- Appropriate for {project['genre']} genre expectations",
                "- Focused on improvement, not criticism",
            ]
        )

        return "\n".join(parts)

    @staticmethod
    def _parse_review(content: str) -> Dict:
        """Parse review from LLM response"""
        # Try JSON first
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data
            except json.JSONDecodeError:
                pass

        # Fallback: Extract sections manually
        result = {
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "detailed_feedback": {},
        }

        # Try to extract score
        score_match = re.search(r"(?:score|rating).*?(\d+)/10", content, re.IGNORECASE)
        if score_match:
            result["overall_score"] = int(score_match.group(1))

        # Extract strengths
        strengths_section = re.search(
            r"(?:strengths?|what works)[:\s]+(.*?)(?=\n\n|weaknesses?|suggestions?|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if strengths_section:
            strengths_text = strengths_section.group(1)
            result["strengths"] = re.findall(r"[-•*]\s*([^\n]+)", strengths_text)[:5]

        # Extract weaknesses
        weaknesses_section = re.search(
            r"(?:weaknesses?|areas for improvement|issues?)[:\s]+(.*?)(?=\n\n|suggestions?|detailed|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if weaknesses_section:
            weaknesses_text = weaknesses_section.group(1)
            result["weaknesses"] = re.findall(r"[-•*]\s*([^\n]+)", weaknesses_text)[:5]

        # Extract suggestions (simplified)
        suggestions_section = re.search(
            r"(?:suggestions?|recommendations?)[:\s]+(.*?)(?=\n\n|detailed|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if suggestions_section:
            suggestions_text = suggestions_section.group(1)
            suggestions_list = re.findall(r"[-•*]\s*([^\n]+)", suggestions_text)[:7]
            result["suggestions"] = [
                {"issue": sug, "location": "General", "severity": "medium", "fix": sug}
                for sug in suggestions_list
            ]

        # Extract detailed feedback sections
        for area in ["structure", "prose", "dialogue", "pacing", "consistency"]:
            pattern = (
                rf"{area}[:\s]+(.*?)(?=\n\n|(?:structure|prose|dialogue|pacing|consistency):|\Z)"
            )
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                result["detailed_feedback"][area] = match.group(1).strip()[:500]

        return result


# Convenience function
def review_chapter(chapter_id: int, review_type: str = "standard", **kwargs) -> Dict[str, Any]:
    """
    Quick helper to review a chapter

    Args:
        chapter_id: Chapter to review
        review_type: 'quick', 'standard', or 'deep'
        **kwargs: Additional parameters

    Returns:
        Review results dict

    Example:
        review = review_chapter(123, review_type='deep')
        if review['success']:
            print(f"Score: {review['overall_score']}/10")
            print(f"Strengths: {review['strengths']}")
    """
    return ChapterReviewHandler.handle(
        {"chapter_id": chapter_id, "review_type": review_type, **kwargs}
    )
