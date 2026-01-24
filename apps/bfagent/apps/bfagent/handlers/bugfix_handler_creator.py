"""
BugFix Handler Creator

Meta-handler that generates specialized fix handlers for specific bug types.
Creates executable handler code that can be reviewed and approved before execution.
"""

from typing import Any, Dict
from apps.core.handlers.base import BaseHandler
from apps.bfagent.models import BugFixPlan
import textwrap


class BugFixHandlerCreator(BaseHandler):
    """
    Creates specialized handlers for bug fixes
    
    Generates handler code that can fix specific bug types.
    Handler code is stored in BugFixPlan for review before execution.
    """
    
    def __init__(self):
        super().__init__()
        self.handler_id = "testing.bugfix.handler_creator"
        self.name = "BugFix Handler Creator"
        self.description = "Generates specialized fix handlers"
        
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fix plan with generated handler"""
        requirement = context.get('requirement')
        fix_type = context.get('fix_type')
        fix_params = context.get('fix_params', {})
        
        # Generate handler code
        handler_code = self._generate_handler_code(fix_type, fix_params)
        
        # Create fix plan
        fix_plan = BugFixPlan.objects.create(
            requirement=requirement,
            fix_type=fix_type,
            fix_description=self._generate_description(fix_type, fix_params),
            fix_actions=fix_params,
            handler_id=f"bugfix.{fix_type}.{requirement.id}",
            handler_code=handler_code,
            rollback_possible=self._is_rollback_possible(fix_type),
            created_by=context.get('user'),
            status='pending'
        )
        
        return {
            'success': True,
            'fix_plan_id': str(fix_plan.id),
            'handler_code': handler_code,
            'requires_approval': True
        }
    
    def _generate_handler_code(self, fix_type: str, params: Dict) -> str:
        """Generate executable handler code"""
        templates = {
            '404_missing_chapter': self._template_create_chapter,
            '404_missing_book': self._template_create_book,
        }
        
        template_func = templates.get(fix_type)
        if not template_func:
            return f"# No template for fix_type: {fix_type}"
        
        return template_func(params)
    
    def _template_create_chapter(self, params: Dict) -> str:
        """Template for creating missing chapter"""
        return textwrap.dedent(f'''
        """Auto-generated handler to create missing chapter"""
        from apps.bfagent.models import Chapter, Book
        
        def execute_fix():
            """Create Chapter {params.get("chapter_num")} for Book {params.get("book_id")}"""
            try:
                book = Book.objects.get(id={params.get("book_id")})
                chapter = Chapter.objects.create(
                    book=book,
                    chapter_number={params.get("chapter_num")},
                    title="Chapter {params.get("chapter_num")}",
                    content="Auto-generated chapter content. Please update.",
                    status="draft"
                )
                return {{
                    "success": True,
                    "chapter_id": chapter.id,
                    "rollback_id": chapter.id
                }}
            except Book.DoesNotExist:
                return {{
                    "success": False,
                    "error": "Book {params.get("book_id")} not found"
                }}
            except Exception as e:
                return {{
                    "success": False,
                    "error": str(e)
                }}
        
        def rollback_fix(rollback_data):
            """Remove created chapter"""
            try:
                chapter_id = rollback_data.get("rollback_id")
                Chapter.objects.filter(id=chapter_id).delete()
                return {{"success": True}}
            except Exception as e:
                return {{"success": False, "error": str(e)}}
        ''')
    
    def _template_create_book(self, params: Dict) -> str:
        """Template for creating missing book"""
        return textwrap.dedent(f'''
        """Auto-generated handler to create missing book"""
        from apps.bfagent.models import Book, Project
        
        def execute_fix():
            """Create Book {params.get("book_id")}"""
            try:
                # Get default project or create
                project = Project.objects.first()
                if not project:
                    return {{
                        "success": False,
                        "error": "No project available"
                    }}
                
                book = Book.objects.create(
                    project=project,
                    title="Auto-generated Book {params.get("book_id")}",
                    description="This book was auto-generated to fix a 404 error.",
                    status="draft"
                )
                return {{
                    "success": True,
                    "book_id": book.id,
                    "rollback_id": book.id
                }}
            except Exception as e:
                return {{
                    "success": False,
                    "error": str(e)
                }}
        
        def rollback_fix(rollback_data):
            """Remove created book"""
            try:
                book_id = rollback_data.get("rollback_id")
                Book.objects.filter(id=book_id).delete()
                return {{"success": True}}
            except Exception as e:
                return {{"success": False, "error": str(e)}}
        ''')
    
    def _generate_description(self, fix_type: str, params: Dict) -> str:
        """Generate human-readable description"""
        descriptions = {
            '404_missing_chapter': f"Create Chapter {params.get('chapter_num')} for Book {params.get('book_id')}",
            '404_missing_book': f"Create Book {params.get('book_id')}",
        }
        return descriptions.get(fix_type, f"Fix for {fix_type}")
    
    def _is_rollback_possible(self, fix_type: str) -> bool:
        """Check if fix type supports rollback"""
        rollback_supported = [
            '404_missing_chapter',
            '404_missing_book',
        ]
        return fix_type in rollback_supported
