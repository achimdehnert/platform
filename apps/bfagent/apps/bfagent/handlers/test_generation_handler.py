"""
Test Generation Handler

Generates test code from requirements and acceptance criteria.
Supports Robot Framework, pytest, and Playwright test generation.

Handler Type: Processing
Domain: testing
Category: test_automation
"""

from typing import Any, Dict, List
from apps.core.handlers.base import BaseHandler
from dataclasses import dataclass
import re


@dataclass
class TestSpecification:
    """Generated test specification"""
    requirement_id: str
    scenario_name: str
    test_type: str  # robot, pytest, playwright
    test_code: str
    dependencies: List[str]
    estimated_duration: int  # seconds
    file_path: str


class TestGenerationHandler(BaseHandler):
    """
    Generates executable test code from acceptance criteria
    
    Input Context:
        - requirement: TestRequirement instance
        - criterion: Single acceptance criterion dict
        - framework: 'robot' | 'pytest' | 'playwright'
        
    Output:
        - test_code: Generated test code
        - file_path: Suggested file path
        - dependencies: Required dependencies
    """
    
    def __init__(self):
        super().__init__()
        self.handler_id = "testing.test.generate"
        self.name = "Test Generation Handler"
        self.description = "Generates test code from acceptance criteria"
        self.version = "1.0.0"
        self.domain = "testing"
        self.category = "test_automation"
    
    def validate_input(self, context: Dict[str, Any]) -> tuple[bool, str | None]:
        """Validate required context"""
        if 'requirement' not in context:
            return False, "Missing 'requirement' in context"
        
        if 'criterion' not in context:
            return False, "Missing 'criterion' in context"
        
        criterion = context['criterion']
        required_fields = ['scenario', 'given', 'when', 'then']
        missing = [f for f in required_fields if f not in criterion]
        
        if missing:
            return False, f"Criterion missing fields: {', '.join(missing)}"
        
        return True, None
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate test code from acceptance criteria
        
        Returns:
            {
                'success': bool,
                'test_specification': TestSpecification,
                'test_code': str,
                'file_path': str,
                'message': str
            }
        """
        requirement = context['requirement']
        criterion = context['criterion']
        framework = context.get('framework', 'robot')
        
        try:
            if framework == 'robot':
                spec = self._generate_robot_test(requirement, criterion)
            elif framework == 'pytest':
                spec = self._generate_pytest_test(requirement, criterion)
            elif framework == 'playwright':
                spec = self._generate_playwright_test(requirement, criterion)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported framework: {framework}',
                    'message': 'Only robot, pytest, and playwright are supported'
                }
            
            return {
                'success': True,
                'test_specification': spec,
                'test_code': spec.test_code,
                'file_path': spec.file_path,
                'dependencies': spec.dependencies,
                'estimated_duration': spec.estimated_duration,
                'message': f'Generated {framework} test for: {spec.scenario_name}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to generate test: {str(e)}'
            }
    
    def _generate_robot_test(self, requirement, criterion) -> TestSpecification:
        """Generate Robot Framework test"""
        
        scenario = criterion.get('scenario', 'Unnamed Scenario')
        given = criterion.get('given', '')
        when = criterion.get('when', '')
        then = criterion.get('then', '')
        priority = criterion.get('priority', 'medium')
        
        # Convert Gherkin to Robot Keywords
        given_keywords = self._convert_given_to_robot(given)
        when_keywords = self._convert_when_to_robot(when)
        then_keywords = self._convert_then_to_robot(then)
        
        # Generate test code
        test_code = f"""*** Settings ***
Documentation     {requirement.name} - {scenario}
Resource          ../../resources/common.robot
Library           ../../libraries/BFAgentLibrary.py
Test Tags         requirement-{str(requirement.id)[:8]}    {priority}

*** Test Cases ***
Test: {scenario}
    [Documentation]    {requirement.description or scenario}
    [Tags]    {criterion.get('test_type', 'integration')}    {requirement.category}
    
    # GIVEN: {given}
{given_keywords}
    
    # WHEN: {when}
{when_keywords}
    
    # THEN: {then}
{then_keywords}
"""
        
        # Generate file path
        safe_name = re.sub(r'[^\w\s-]', '', scenario.lower())
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        file_path = f"tests/robot/tests/requirements/req_{str(requirement.id)[:8]}_{safe_name}.robot"
        
        return TestSpecification(
            requirement_id=str(requirement.id),
            scenario_name=scenario,
            test_type='robot',
            test_code=test_code,
            dependencies=['robotframework', 'robotframework-seleniumlibrary'],
            estimated_duration=30,
            file_path=file_path
        )
    
    def _convert_given_to_robot(self, given: str) -> str:
        """Convert Given clause to Robot keywords"""
        keywords = []
        given_lower = given.lower()
        
        # Common patterns
        if 'logged in' in given_lower or 'authenticated' in given_lower:
            keywords.append("    User Is Logged In")
        
        if 'book' in given_lower or 'project' in given_lower:
            if 'exists' in given_lower or 'has' in given_lower:
                keywords.append("    User Has Book Project    project_name=Test Book")
        
        if 'chapter' in given_lower:
            match = re.search(r'chapter\s+(\d+)', given_lower)
            if match:
                chapter_num = match.group(1)
                keywords.append(f"    User Has Chapter    chapter_number={chapter_num}")
            else:
                keywords.append("    User Has Chapter    chapter_number=1")
        
        if 'page' in given_lower:
            match = re.search(r'on\s+(?:the\s+)?["\']?([^"\']+)["\']?\s+page', given_lower)
            if match:
                page_name = match.group(1)
                keywords.append(f"    User Navigates To    {page_name}")
        
        # Fallback
        if not keywords:
            keywords.append(f"    # TODO: Implement precondition: {given}")
        
        return '\n'.join(keywords)
    
    def _convert_when_to_robot(self, when: str) -> str:
        """Convert When clause to Robot keywords"""
        keywords = []
        when_lower = when.lower()
        
        # Click actions
        if 'click' in when_lower:
            match = re.search(r'click[s]?\s+(?:on\s+)?(?:the\s+)?["\']?([^"\']+)["\']?', when_lower, re.IGNORECASE)
            if match:
                element = match.group(1).strip()
                keywords.append(f'    Click Element    xpath=//*[contains(text(), "{element}")]')
        
        # Input/Enter text
        if 'enter' in when_lower or 'input' in when_lower or 'type' in when_lower:
            match = re.search(r'(?:enter|input|type)[s]?\s+["\']?([^"\']+)["\']?', when_lower)
            if match:
                text = match.group(1).strip()
                keywords.append(f'    Input Text    id=input_field    {text}')
            else:
                keywords.append('    Input Text    id=input_field    Test input')
        
        # Submit/Send
        if 'submit' in when_lower or 'send' in when_lower:
            keywords.append('    Click Button    xpath=//button[@type="submit"]')
        
        # Select/Choose
        if 'select' in when_lower or 'choose' in when_lower:
            match = re.search(r'(?:select|choose)[s]?\s+["\']?([^"\']+)["\']?', when_lower)
            if match:
                option = match.group(1).strip()
                keywords.append(f'    Select From List By Label    id=select_field    {option}')
        
        # Navigate
        if 'navigate' in when_lower or 'go to' in when_lower:
            match = re.search(r'(?:navigate to|go to)\s+["\']?([^"\']+)["\']?', when_lower)
            if match:
                url = match.group(1).strip()
                keywords.append(f'    Go To    ${{BASE_URL}}/{url}')
        
        # Fallback
        if not keywords:
            keywords.append(f"    # TODO: Implement action: {when}")
        
        return '\n'.join(keywords)
    
    def _convert_then_to_robot(self, then: str) -> str:
        """Convert Then clause to Robot keywords"""
        keywords = []
        then_lower = then.lower()
        
        # Visibility checks
        if 'should see' in then_lower or 'should be visible' in then_lower or 'appears' in then_lower:
            match = re.search(r'(?:see|visible|appears)[:\s]+["\']?([^"\']+)["\']?', then_lower)
            if match:
                text = match.group(1).strip()
                keywords.append(f'    Page Should Contain    {text}')
            else:
                keywords.append('    Page Should Contain    Expected text')
        
        # Success/Error messages
        if 'success' in then_lower:
            keywords.append('    Page Should Contain Element    css=.alert-success')
        
        if 'error' in then_lower:
            keywords.append('    Page Should Contain Element    css=.alert-error')
        
        # Redirects
        if 'redirect' in then_lower:
            match = re.search(r'redirect[ed]?\s+to\s+["\']?([^"\']+)["\']?', then_lower)
            if match:
                url = match.group(1).strip()
                keywords.append(f'    Location Should Contain    {url}')
            else:
                keywords.append('    Location Should Not Be    ${PREVIOUS_URL}')
        
        # Element presence
        if 'should contain' in then_lower or 'should have' in then_lower:
            match = re.search(r'(?:contain|have)[s]?\s+["\']?([^"\']+)["\']?', then_lower)
            if match:
                content = match.group(1).strip()
                keywords.append(f'    Page Should Contain    {content}')
        
        # Count checks
        if re.search(r'\d+\s+(?:item|element|result)', then_lower):
            match = re.search(r'(\d+)\s+(?:item|element|result)', then_lower)
            if match:
                count = match.group(1)
                keywords.append(f'    Element Count Should Be    css=.result-item    {count}')
        
        # Fallback
        if not keywords:
            keywords.append(f"    # TODO: Implement assertion: {then}")
        
        return '\n'.join(keywords)
    
    def _generate_pytest_test(self, requirement, criterion) -> TestSpecification:
        """Generate pytest test (placeholder for now)"""
        scenario = criterion.get('scenario', 'Unnamed')
        
        test_code = f"""
import pytest

def test_{scenario.lower().replace(' ', '_')}():
    \"\"\"
    Test: {scenario}
    
    Requirement: {requirement.name}
    Given: {criterion.get('given', '')}
    When: {criterion.get('when', '')}
    Then: {criterion.get('then', '')}
    \"\"\"
    # TODO: Implement test
    pass
"""
        
        safe_name = re.sub(r'[^\w\s-]', '', scenario.lower())
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        
        return TestSpecification(
            requirement_id=str(requirement.id),
            scenario_name=scenario,
            test_type='pytest',
            test_code=test_code,
            dependencies=['pytest'],
            estimated_duration=10,
            file_path=f"tests/pytest/test_{safe_name}.py"
        )
    
    def _generate_playwright_test(self, requirement, criterion) -> TestSpecification:
        """Generate Playwright test (placeholder for now)"""
        scenario = criterion.get('scenario', 'Unnamed')
        
        test_code = f"""
import {{ test, expect }} from '@playwright/test';

test('{scenario}', async ({{ page }}) => {{
  // Requirement: {requirement.name}
  // Given: {criterion.get('given', '')}
  // When: {criterion.get('when', '')}
  // Then: {criterion.get('then', '')}
  
  // TODO: Implement test
}});
"""
        
        safe_name = re.sub(r'[^\w\s-]', '', scenario.lower())
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        
        return TestSpecification(
            requirement_id=str(requirement.id),
            scenario_name=scenario,
            test_type='playwright',
            test_code=test_code,
            dependencies=['@playwright/test'],
            estimated_duration=15,
            file_path=f"tests/e2e/{safe_name}.spec.ts"
        )
