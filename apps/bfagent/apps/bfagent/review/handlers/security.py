"""
Security Review Handler

Checks for common security issues and vulnerabilities.
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


class SecurityReviewHandler(BaseReviewHandler):
    """Handler for security checks"""
    
    def __init__(self):
        super().__init__("SecurityReviewHandler")
        
        # Patterns for security issues
        self.patterns = {
            'hardcoded_secret': [
                (r'(?i)(password|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']', 
                 "Possible hardcoded secret detected"),
                (r'(?i)SECRET_KEY\s*=\s*["\'][^"\']+["\']',
                 "Django SECRET_KEY should be in environment variable"),
            ],
            'sql_injection': [
                (r'\.raw\([^)]*%s', "Possible SQL injection via raw() with string formatting"),
                (r'\.execute\([^)]*%', "Possible SQL injection via execute() with % formatting"),
                (r'f"SELECT.*{', "F-string in SQL query is dangerous"),
            ],
            'unsafe_functions': [
                (r'\bexec\s*\(', "Use of exec() is dangerous"),
                (r'\beval\s*\(', "Use of eval() is dangerous"),
                (r'pickle\.loads?\(', "Pickle can execute arbitrary code"),
                (r'yaml\.load\((?!.*Loader=)', "yaml.load() without safe loader"),
            ],
            'debug_left_on': [
                (r'DEBUG\s*=\s*True', "DEBUG should be False in production"),
                (r'print\s*\(.*password', "Printing passwords/secrets"),
            ],
        }
    
    def _review(self, target: Path, context: Dict[str, Any], result: ReviewResult) -> ReviewResult:
        """Perform security review"""
        if not target.suffix == '.py':
            return result
        
        try:
            content = target.read_text(encoding='utf-8')
            
            # Check all security patterns
            for issue_type, patterns in self.patterns.items():
                for pattern, description in patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Extract code snippet
                        lines = content.split('\n')
                        snippet = lines[line_num - 1] if line_num <= len(lines) else ""
                        
                        # Determine severity
                        severity = self._get_severity(issue_type)
                        
                        self.add_finding(
                            result=result,
                            category=ReviewCategory.SECURITY,
                            severity=severity,
                            title=description,
                            description=f"{description} at line {line_num}",
                            file_path=target,
                            line_number=line_num,
                            code_snippet=snippet.strip(),
                            suggestion=self._get_suggestion(issue_type),
                            auto_fixable=False,
                            issue_type=issue_type,
                        )
        
        except Exception as e:
            self.log.error("review_failed", file=str(target), error=str(e))
        
        return result
    
    def _get_severity(self, issue_type: str) -> ReviewSeverity:
        """Get severity for issue type"""
        critical_issues = ['hardcoded_secret', 'sql_injection']
        error_issues = ['unsafe_functions']
        
        if issue_type in critical_issues:
            return ReviewSeverity.CRITICAL
        elif issue_type in error_issues:
            return ReviewSeverity.ERROR
        else:
            return ReviewSeverity.WARNING
    
    def _get_suggestion(self, issue_type: str) -> str:
        """Get fix suggestion for issue type"""
        suggestions = {
            'hardcoded_secret': "Use environment variables: os.environ.get('SECRET_NAME')",
            'sql_injection': "Use parameterized queries or ORM methods",
            'unsafe_functions': "Avoid exec()/eval(), use safer alternatives",
            'debug_left_on': "Set DEBUG=False and use environment variable",
        }
        return suggestions.get(issue_type, "Review and fix security issue")
