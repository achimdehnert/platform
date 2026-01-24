"""
Bug Auto-Fix Handler - Detects fixable bugs
"""

from typing import Any, Dict
from apps.core.handlers.base import BaseHandler
import re


class BugAutoFixHandler(BaseHandler):
    """Detects which bugs can be auto-fixed"""
    
    def __init__(self):
        super().__init__()
        self.handler_id = "testing.bug.auto_fix"
        self.name = "Bug Auto-Fix Detector"
        
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if bug is auto-fixable"""
        url = context.get('url', '')
        actual = context.get('actual_behavior', '')
        
        fixable_bugs = self._check_fixable(url, actual)
        
        return {
            'success': True,
            'fixable': len(fixable_bugs) > 0,
            'fixes': fixable_bugs
        }
    
    def _check_fixable(self, url: str, actual: str) -> list:
        """Returns list of auto-fixable issues"""
        fixes = []
        actual_lower = actual.lower()
        
        # 404 Missing Chapter
        if '404' in actual and 'chapter' in url.lower():
            match = re.search(r'/book/(\d+)/chapter/(\d+)', url)
            if match:
                fixes.append({
                    'type': '404_missing_chapter',
                    'description': f'Create missing Chapter {match.group(2)}',
                    'book_id': match.group(1),
                    'chapter_num': match.group(2)
                })
        
        # 404 Missing Book
        elif '404' in actual and 'book' in url.lower():
            match = re.search(r'/book/(\d+)', url)
            if match:
                fixes.append({
                    'type': '404_missing_book',
                    'description': f'Create missing Book {match.group(1)}',
                    'book_id': match.group(1)
                })
        
        return fixes
