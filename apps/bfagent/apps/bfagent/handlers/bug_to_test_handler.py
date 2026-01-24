"""
Bug-to-Test Handler

Converts bug reports into test requirements and test cases.
Automatically generates Gherkin acceptance criteria from bug descriptions.
"""

from typing import Any, Dict
from apps.core.handlers.base import BaseHandler
from apps.bfagent.models import TestRequirement, TestCase, RequirementTestLink
import re
import base64
import uuid
from django.core.files.base import ContentFile


class BugToTestHandler(BaseHandler):
    """
    Converts bug reports to automated test requirements
    
    Input Context:
        - url: Current page URL
        - actual_behavior: What went wrong
        - expected_behavior: What should happen
        - screenshot: Base64 screenshot (optional)
        - console_logs: Browser console logs (optional)
        - network_logs: Failed network requests (optional)
        - user_journey: Last actions (optional)
        
    Output:
        - requirement: Created TestRequirement
        - test_case: Generated TestCase
        - gherkin: Generated acceptance criteria
    """
    
    def __init__(self):
        super().__init__()
        self.handler_id = "testing.bug.to_test"
        self.name = "Bug to Test Converter"
        self.description = "Converts bug reports into test requirements"
        self.version = "1.0.0"
        self.domain = "testing"
        self.category = "bug_tracking"
    
    def validate_input(self, context: Dict[str, Any]) -> tuple[bool, str | None]:
        """Validate bug report data"""
        required = ['url', 'actual_behavior', 'expected_behavior']
        missing = [f for f in required if f not in context or not context[f]]
        
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        return True, None
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert bug report to test requirement"""
        try:
            # Extract bug info
            url = context['url']
            actual = context['actual_behavior']
            expected = context['expected_behavior']
            user = context.get('user')
            
            # Get domain and priority from form (with fallback to auto-detect)
            domain = context.get('domain', 'core')
            priority = context.get('priority') or self._determine_priority(actual, context)
            
            # Generate requirement name
            req_name = self._generate_requirement_name(url, actual)
            
            # Generate Gherkin
            gherkin = self._generate_gherkin(url, actual, expected, context)
            
            # Category is always bug_fix for bug reports
            category = 'bug_fix'
            
            # Create test requirement
            requirement = TestRequirement.objects.create(
                name=req_name,
                description=f"Bug Report: {actual}\n\nExpected: {expected}\n\nURL: {url}",
                category=category,
                priority=priority,
                domain=domain,
                acceptance_criteria=gherkin,
                tags=['bug', 'regression', 'auto-generated'],
                created_by=user,
                status='ready',
                url=url,
                actual_behavior=actual,
                expected_behavior=expected
            )
            
            # Save screenshot if provided (base64)
            screenshot_data = context.get('screenshot', '')
            if screenshot_data and screenshot_data.startswith('data:image'):
                self._save_screenshot(requirement, screenshot_data)
            
            # Generate test case
            test_case = self._generate_test_case(requirement, gherkin[0], context)
            
            # Link requirement to test
            link = RequirementTestLink.objects.create(
                requirement=requirement,
                test_case=test_case,
                criterion_id=gherkin[0]['id'],
                link_type='auto',
                status='implemented'
            )
            
            # Auto-create Fix Plan if bug is fixable
            fix_plan_id = None
            try:
                from apps.bfagent.handlers.bug_auto_fix_handler import BugAutoFixHandler
                from apps.bfagent.handlers.bugfix_handler_creator import BugFixHandlerCreator
                
                # Check if fixable
                auto_fix = BugAutoFixHandler()
                fix_result = auto_fix.execute({
                    'url': url,
                    'actual_behavior': actual
                })
                
                if fix_result.get('fixable') and fix_result.get('fixes'):
                    # Create fix plan for first fixable issue
                    fix_info = fix_result['fixes'][0]
                    
                    creator = BugFixHandlerCreator()
                    plan_result = creator.execute({
                        'requirement': requirement,
                        'fix_type': fix_info['type'],
                        'fix_params': fix_info,
                        'user': context.get('user')
                    })
                    
                    if plan_result.get('success'):
                        fix_plan_id = plan_result['fix_plan_id']
            except Exception as e:
                # Don't fail the whole process if fix plan creation fails
                pass
            
            # Return success
            return {
                'success': True,
                'requirement_id': str(requirement.id),
                'test_case_id': str(test_case.id),
                'fix_plan_id': fix_plan_id,
                'message': f'Created test requirement and {len(gherkin)} test case(s)' + (' + fix plan' if fix_plan_id else ''),
                'redirect_url': f'/bookwriting/test-studio/requirements/{requirement.id}/'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to convert bug to test: {str(e)}'
            }
    
    def _generate_requirement_name(self, url: str, actual: str) -> str:
        """Generate a descriptive requirement name"""
        from urllib.parse import urlparse
        
        # Parse URL and strip query parameters
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        
        # Extract page name from path (without query params)
        page_parts = [p for p in path.split('/') if p and p not in ['bookwriting', 'control-center', 'test-studio', 'requirements']]
        page_name = page_parts[-1] if page_parts else 'Page'
        
        # Skip UUIDs - use second-to-last part if last part looks like UUID
        if len(page_name) == 36 and page_name.count('-') == 4:
            page_name = page_parts[-2] if len(page_parts) > 1 else 'Page'
        
        page_name = page_name.replace('-', ' ').replace('_', ' ').title()
        
        # Shorten actual behavior
        short_actual = actual[:50] + '...' if len(actual) > 50 else actual
        
        return f"Bug: {page_name} - {short_actual}"
    
    def _generate_gherkin(self, url: str, actual: str, expected: str, context: Dict) -> list:
        """Generate Gherkin acceptance criteria from bug description"""
        # Extract action from actual behavior
        action = self._extract_action(actual)
        
        # Generate GIVEN clause
        given = self._generate_given(url, context)
        
        # Generate WHEN clause
        when = self._generate_when(actual, action)
        
        # Generate THEN clause
        then = self._generate_then(expected, actual)
        
        # Determine priority (string for requirement, will convert to int for test case)
        priority_str = self._determine_priority(actual, context)
        
        return [{
            'id': 'ac_1',
            'scenario': f'Verify {expected[:60]}',
            'given': given,
            'when': when,
            'then': then,
            'test_type': self._determine_test_type(url, actual),
            'priority': priority_str  # String: 'critical', 'high', 'medium', 'low'
        }]
    
    def _extract_action(self, actual: str) -> str:
        """Extract the main action from bug description"""
        # Common action patterns
        patterns = [
            r'clicks?\s+(?:on\s+)?(?:the\s+)?(.+?)(?:\s+button|\s+link|\s+and|$)',
            r'submits?\s+(.+?)(?:\s+form|\s+and|$)',
            r'enters?\s+(.+?)(?:\s+in|\s+and|$)',
            r'navigates?\s+to\s+(.+?)(?:\s+and|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, actual.lower())
            if match:
                return match.group(1).strip()
        
        return 'performs action'
    
    def _generate_given(self, url: str, context: Dict) -> str:
        """Generate GIVEN clause"""
        page_name = url.split('/')[-1].replace('-', ' ').replace('_', ' ')
        
        # Check if user was authenticated
        user_journey = context.get('user_journey', [])
        auth_required = any('login' in step.lower() for step in user_journey)
        
        given_parts = []
        if auth_required:
            given_parts.append("User is logged in")
        given_parts.append(f"User is on {page_name} page")
        
        return ' and '.join(given_parts)
    
    def _generate_when(self, actual: str, action: str) -> str:
        """Generate WHEN clause"""
        # Try to extract specific action
        if 'click' in actual.lower():
            return f"User clicks {action}"
        elif 'submit' in actual.lower():
            return f"User submits {action}"
        elif 'enter' in actual.lower() or 'input' in actual.lower():
            return f"User enters {action}"
        else:
            return f"User {actual[:80]}"
    
    def _generate_then(self, expected: str, actual: str) -> str:
        """Generate THEN clause with negative check"""
        then_parts = [expected]
        
        # Add negative assertion based on actual error
        if '404' in actual:
            then_parts.append("Page should not return 404 error")
        elif '500' in actual:
            then_parts.append("Page should not return server error")
        elif 'error' in actual.lower():
            then_parts.append("No error should be displayed")
        
        return ' and '.join(then_parts)
    
    def _determine_category(self, actual: str, url: str) -> str:
        """Determine requirement category from bug description.
        Since this handler is specifically for BUG reports, default is always bug_fix.
        """
        # Everything from Bug Reporter is a bug by default
        return 'bug_fix'
    
    def _determine_priority(self, actual: str, context: Dict) -> str:
        """Determine priority based on severity"""
        actual_lower = actual.lower()
        
        # Critical: 500 errors, crashes
        if '500' in actual or 'crash' in actual_lower or 'broken' in actual_lower:
            return 'critical'
        
        # High: 404, data loss
        if '404' in actual or 'lost' in actual_lower or 'delete' in actual_lower:
            return 'high'
        
        # Medium: UI issues, minor bugs
        if 'button' in actual_lower or 'display' in actual_lower:
            return 'medium'
        
        return 'low'
    
    def _determine_test_type(self, url: str, actual: str) -> str:
        """Determine test type"""
        if 'api' in url.lower() or 'ajax' in actual.lower():
            return 'api'
        return 'ui'
    
    def _generate_test_case(self, requirement, criterion: Dict, context: Dict) -> TestCase:
        """Generate test case from criterion"""
        from apps.bfagent.handlers.test_generation_handler import TestGenerationHandler
        
        handler = TestGenerationHandler()
        result = handler.execute({
            'requirement': requirement,
            'criterion': criterion,
            'framework': 'robot'
        })
        
        if result['success']:
            # Convert string priority to int (for TestCase model)
            priority_map = {
                'critical': 1,
                'high': 2,
                'medium': 3,
                'low': 4
            }
            priority_int = priority_map.get(criterion.get('priority', 'medium'), 3)
            
            # Create test case
            test_case = TestCase.objects.create(
                test_id=f"BUG_{requirement.id.hex[:8]}_{criterion['id']}",
                name=criterion['scenario'],
                description=f"Regression test for bug: {requirement.name}",
                framework='robot',
                test_type=criterion['test_type'],
                priority=priority_int,  # INT not STRING!
                test_code=result['test_code'],
                file_path=result['file_path'],
                is_auto_generated=True,
                tags=['bug', 'regression', 'auto-generated'],
                status='pending'
            )
            return test_case
        else:
            raise Exception(f"Failed to generate test case: {result.get('error')}")
    
    def _save_screenshot(self, requirement, screenshot_data: str):
        """
        Save base64 screenshot to requirement.
        
        Args:
            requirement: TestRequirement instance
            screenshot_data: Base64 encoded image (data:image/png;base64,...)
        """
        try:
            # Parse base64 data
            if ';base64,' in screenshot_data:
                header, data = screenshot_data.split(';base64,')
                # Determine file extension from header
                if 'png' in header:
                    ext = 'png'
                elif 'jpeg' in header or 'jpg' in header:
                    ext = 'jpg'
                else:
                    ext = 'png'
            else:
                data = screenshot_data
                ext = 'png'
            
            # Decode base64
            image_data = base64.b64decode(data)
            
            # Create filename
            filename = f"bug_{requirement.id.hex[:8]}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Save to ImageField
            requirement.screenshot.save(filename, ContentFile(image_data), save=True)
            
        except Exception as e:
            # Don't fail the whole process if screenshot save fails
            print(f"Warning: Failed to save screenshot: {e}")
