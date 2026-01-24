"""
Illustration System Review Handler

Checks specific to the BF Agent Illustration System.
"""

import re
from pathlib import Path
from typing import Dict, Any

from ..core import (
    BaseReviewHandler,
    ReviewResult,
    ReviewCategory,
    ReviewSeverity,
)


class IllustrationReviewHandler(BaseReviewHandler):
    """Handler for illustration-specific checks"""

    def __init__(self):
        super().__init__("IllustrationReviewHandler")

    def _review(self, target: Path, context: Dict[str, Any], result: ReviewResult) -> ReviewResult:
        """Perform illustration system review"""
        if not target.suffix == '.py':
            return result

        # Only review illustration-related files
        if 'illustration' not in str(target).lower():
            return result

        try:
            content = target.read_text(encoding='utf-8')

            # Check 1: LLM API keys not hardcoded
            if re.search(r'(?i)(openai|anthropic).*api.*key\s*=\s*["\'][^"\']+["\']', content):
                matches = re.finditer(r'api.*key\s*=', content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    self.add_finding(
                        result=result,
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.CRITICAL,
                        title="LLM API key hardcoded",
                        description="API keys should be in environment variables",
                        file_path=target,
                        line_number=line_num,
                        suggestion="Use: os.environ.get('ANTHROPIC_API_KEY') or settings.ANTHROPIC_API_KEY",
                        auto_fixable=False,
                    )

            # Check 2: User input sanitization for LLM calls
            if 'llm_call' in content or 'generate_' in content:
                if not re.search(r'(escape|sanitize|clean|validate).*prompt', content, re.IGNORECASE):
                    self.add_finding(
                        result=result,
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.WARNING,
                        title="Missing prompt sanitization",
                        description="User input should be sanitized before LLM calls",
                        file_path=target,
                        suggestion="Add prompt validation/sanitization before LLM calls",
                        auto_fixable=False,
                    )

            # Check 3: Cost limits enforcement
            if 'auto_illustrate' in content or 'generate_images' in content:
                if not re.search(r'(cost_limit|max_cost|budget)', content, re.IGNORECASE):
                    self.add_finding(
                        result=result,
                        category=ReviewCategory.BEST_PRACTICES,
                        severity=ReviewSeverity.WARNING,
                        title="Missing cost limit enforcement",
                        description="Auto-illustration should enforce cost limits",
                        file_path=target,
                        suggestion="Add max_cost parameter and enforcement logic",
                        auto_fixable=False,
                    )

            # Check 4: Proper permission checks
            if 'IllustrationOwnerMixin' in content or 'chapter' in content.lower():
                if 'def get_queryset' in content and 'user' not in content:
                    self.add_finding(
                        result=result,
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.ERROR,
                        title="Missing user ownership check",
                        description="Queryset should filter by user ownership",
                        file_path=target,
                        suggestion="Add: .filter(user=self.request.user) or use IllustrationOwnerMixin",
                        auto_fixable=False,
                    )

            # Check 5: Mock mode handling
            if 'ImageGenerationHandler' in content or 'generate_image' in content:
                if 'mock_mode' in content:
                    # Good - mock mode is considered
                    pass
                else:
                    self.add_finding(
                        result=result,
                        category=ReviewCategory.BEST_PRACTICES,
                        severity=ReviewSeverity.INFO,
                        title="Consider adding mock mode",
                        description="Mock mode allows free testing without API costs",
                        file_path=target,
                        suggestion="Add mock_mode parameter for testing",
                        auto_fixable=False,
                    )

            # Check 6: Error handling for LLM calls
            if re.search(r'(llm_call|generate_|anthropic|openai)', content, re.IGNORECASE):
                if not re.search(r'try:.*llm.*except', content, re.DOTALL):
                    self.add_finding(
                        result=result,
                        category=ReviewCategory.BEST_PRACTICES,
                        severity=ReviewSeverity.WARNING,
                        title="Missing error handling for LLM calls",
                        description="LLM calls should have proper error handling",
                        file_path=target,
                        suggestion="Wrap LLM calls in try/except with specific exception handling",
                        auto_fixable=False,
                    )

            # Check 7: Async/parallel processing for multiple images
            if re.search(r'for.*in.*images|for.*prompt', content):
                if 'generate_image' in content and 'async' not in content and 'parallel' not in content:
                    self.add_finding(
                        result=result,
                        category=ReviewCategory.PERFORMANCE,
                        severity=ReviewSeverity.WARNING,
                        title="Sequential image generation",
                        description="Consider async/parallel processing for multiple images",
                        file_path=target,
                        suggestion="Use asyncio or ThreadPoolExecutor for parallel generation",
                        auto_fixable=False,
                    )

        except Exception as e:
            self.log.error("review_failed", file=str(target), error=str(e))

        return result
