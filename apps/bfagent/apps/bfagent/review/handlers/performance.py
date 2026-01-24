"""
Performance Review Handler

Checks for performance anti-patterns.
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


class PerformanceReviewHandler(BaseReviewHandler):
    """Handler for performance checks"""

    def __init__(self):
        super().__init__("PerformanceReviewHandler")

        # Performance anti-patterns
        self.patterns = {
            'string_concat_loop': (
                r'for\s+\w+\s+in\s+.*:\s*\n\s*\w+\s*\+=\s*["\']',
                "String concatenation in loop - use list and join()"
            ),
            'repeated_db_query': (
                r'for\s+\w+\s+in\s+.*:\s*\n.*\.objects\.(?:get|filter)',
                "Possible N+1 query - use select_related() or prefetch_related()"
            ),
            'no_db_index': (
                r'class\s+\w+\(.*Model.*\):.*\n(?:.*\n)*?\s+class Meta:(?:(?!db_index).)*$',
                "Consider adding db_index=True for frequently queried fields"
            ),
        }

    def _review(self, target: Path, context: Dict[str, Any], result: ReviewResult) -> ReviewResult:
        """Perform performance review"""
        if not target.suffix == '.py':
            return result

        try:
            content = target.read_text(encoding='utf-8')

            # Check string concatenation in loops
            if 'for ' in content and '+=' in content:
                matches = re.finditer(self.patterns['string_concat_loop'][0], content, re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1

                    self.add_finding(
                        result=result,
                        category=ReviewCategory.PERFORMANCE,
                        severity=ReviewSeverity.WARNING,
                        title="String concatenation in loop",
                        description=self.patterns['string_concat_loop'][1],
                        file_path=target,
                        line_number=line_num,
                        suggestion="Use: items = []; items.append(x); result = ''.join(items)",
                        auto_fixable=False,
                    )

            # Check for N+1 queries
            if 'for ' in content and '.objects.' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'for ' in line and i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if '.objects.get(' in next_line or '.objects.filter(' in next_line:
                            self.add_finding(
                                result=result,
                                category=ReviewCategory.PERFORMANCE,
                                severity=ReviewSeverity.ERROR,
                                title="Possible N+1 query detected",
                                description="Database query inside loop causes N+1 problem",
                                file_path=target,
                                line_number=i + 1,
                                code_snippet=line.strip(),
                                suggestion="Use select_related() or prefetch_related() before loop",
                                auto_fixable=False,
                            )

        except Exception as e:
            self.log.error("review_failed", file=str(target), error=str(e))

        return result
