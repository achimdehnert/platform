#!/usr/bin/env python
"""
Screen Documentation & Testing Framework for BF Agent v2.0.0
Automatically documents UI screens, generates tests, and maintains consistency
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import django
from bs4 import BeautifulSoup
from django.urls import get_resolver

# Setup Django
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")


django.setup()


class ScreenElement:
    """Represents a UI element on a screen"""

    def __init__(self, element_id: str, element_type: str, name: str, **kwargs):
        """Function description."""
        self.element_id = element_id
        self.element_type = element_type  # input, button, output, form, link
        self.name = name
        self.description = kwargs.get("description", "")
        self.is_required = kwargs.get("is_required", False)
        self.validation_rules = kwargs.get("validation_rules", {})
        self.default_value = kwargs.get("default_value", "")

        # For buttons
        self.action_target = kwargs.get("action_target", "")
        self.htmx_attributes = kwargs.get("htmx_attributes", {})
        self.expected_outcome = kwargs.get("expected_outcome", "")

        # For inputs/outputs
        self.data_source = kwargs.get("data_source", "")
        self.field_mapping = kwargs.get("field_mapping", "")


class ScreenDocumentation:
    """Represents a complete screen documentation"""

    def __init__(self, screen_id: str, name: str, url_pattern: str, template_path: str):
        """Function description."""
        self.screen_id = screen_id
        self.name = name
        self.url_pattern = url_pattern
        self.template_path = template_path
        self.description = ""
        self.screen_type = "unknown"  # edit, list, detail, dashboard, form
        self.requires_auth = True
        self.crud_operations = []
        self.elements: List[ScreenElement] = []
        self.flows = []

    def add_element(self, element: ScreenElement):
        """Add a UI element to this screen"""
        self.elements.append(element)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "screen_id": self.screen_id,
            "name": self.name,
            "url_pattern": self.url_pattern,
            "template_path": self.template_path,
            "description": self.description,
            "screen_type": self.screen_type,
            "requires_auth": self.requires_auth,
            "crud_operations": self.crud_operations,
            "elements": [
                {
                    "element_id": elem.element_id,
                    "element_type": elem.element_type,
                    "name": elem.name,
                    "description": elem.description,
                    "is_required": elem.is_required,
                    "validation_rules": elem.validation_rules,
                    "default_value": elem.default_value,
                    "action_target": elem.action_target,
                    "htmx_attributes": elem.htmx_attributes,
                    "expected_outcome": elem.expected_outcome,
                    "data_source": elem.data_source,
                    "field_mapping": elem.field_mapping,
                }
                for elem in self.elements
            ],
        }


class ScreenDiscoveryTool:
    """Automatically discovers and documents UI screens"""

    def __init__(self):
        """Function description."""
        self.screens: Dict[str, ScreenDocumentation] = {}
        self.templates_dir = project_root / "templates"

    def discover_all_screens(self) -> Dict[str, ScreenDocumentation]:
        """Discover all screens in the application"""
        print("🔍 Discovering all screens...")

        # Scan templates
        self._scan_templates()

        # Analyze URLs
        self._analyze_url_patterns()

        return self.screens

    def _scan_templates(self):
        """Scan all HTML templates"""
        if not self.templates_dir.exists():
            print(f"❌ Templates directory not found: {self.templates_dir}")
            return

        for template_file in self.templates_dir.rglob("*.html"):
            try:
                self._analyze_template(template_file)
            except Exception as e:
                print(f"⚠️ Error analyzing template {template_file}: {e}")

    def _analyze_template(self, template_path: Path):
        """Analyze a single template file"""
        relative_path = template_path.relative_to(project_root)
        screen_id = str(relative_path).replace("/", "_").replace("\\", "_").replace(".html", "")

        # Skip base templates and partials
        if "base" in template_path.name or "partial" in str(template_path):
            return

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️ Could not read {template_path}: {e}")
            return

        # Parse HTML
        soup = BeautifulSoup(content, "html.parser")

        # Create screen documentation
        screen_name = self._extract_screen_name(soup, template_path)
        screen = ScreenDocumentation(
            screen_id=screen_id,
            name=screen_name,
            url_pattern="",  # Will be filled by URL analysis
            template_path=str(relative_path),
        )

        # Determine screen type
        screen.screen_type = self._determine_screen_type(soup, template_path)
        screen.description = self._extract_description(soup)

        # Extract UI elements
        self._extract_form_elements(soup, screen)
        self._extract_buttons(soup, screen)
        self._extract_links(soup, screen)
        self._extract_htmx_elements(soup, screen)

        self.screens[screen_id] = screen
        print(f"📄 Documented screen: {screen.name} ({len(screen.elements)} elements)")

    def _extract_screen_name(self, soup: BeautifulSoup, template_path: Path) -> str:
        """Extract screen name from template"""
        # Try title tag
        title = soup.find("title")
        if title:
            return title.get_text().strip()

        # Try h1 tag
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()

        # Fallback to filename
        return template_path.stem.replace("_", " ").title()

    def _determine_screen_type(self, soup: BeautifulSoup, template_path: Path) -> str:
        """Determine the type of screen"""
        path_str = str(template_path).lower()

        if "edit" in path_str or "form" in path_str:
            return "edit"
        elif "list" in path_str or "index" in path_str:
            return "list"
        elif "detail" in path_str or "view" in path_str:
            return "detail"
        elif "dashboard" in path_str:
            return "dashboard"
        elif soup.find("form"):
            return "form"
        else:
            return "page"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract description from meta tags or content"""
        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            return meta_desc.get("content", "")

        # Try first paragraph
        first_p = soup.find("p")
        if first_p:
            return first_p.get_text().strip()[:200]

        return ""

    def _extract_form_elements(self, soup: BeautifulSoup, screen: ScreenDocumentation):
        """Extract form input elements"""
        inputs = soup.find_all(["input", "textarea", "select"])

        for input_elem in inputs:
            element_id = input_elem.get("id", input_elem.get("name", ""))
            if not element_id:
                continue

            element_type = input_elem.get("type", input_elem.name)
            name = input_elem.get("name", element_id)

            # Extract validation rules
            validation_rules = {}
            if input_elem.get("required"):
                validation_rules["required"] = True
            if input_elem.get("maxlength"):
                validation_rules["max_length"] = input_elem.get("maxlength")
            if input_elem.get("pattern"):
                validation_rules["pattern"] = input_elem.get("pattern")

            element = ScreenElement(
                element_id=element_id,
                element_type=f"input_{element_type}",
                name=name,
                is_required=bool(input_elem.get("required")),
                validation_rules=validation_rules,
                default_value=input_elem.get("value", ""),
                field_mapping=input_elem.get("name", ""),
            )

            screen.add_element(element)

    def _extract_buttons(self, soup: BeautifulSoup, screen: ScreenDocumentation):
        """Extract button elements"""
        buttons = soup.find_all(["button", "input"])

        for button in buttons:
            if button.name == "input" and button.get("type") not in ["submit", "button"]:
                continue

            element_id = button.get("id", "")
            if not element_id:
                # Generate ID from text content
                text = button.get_text().strip()
                element_id = re.sub(r"[^\w]", "_", text.lower()) if text else "unnamed_button"

            name = button.get_text().strip() or button.get("value", "")

            # Extract HTMX attributes
            htmx_attrs = {}
            for attr_name, attr_value in button.attrs.items():
                if attr_name.startswith("hx-"):
                    htmx_attrs[attr_name] = attr_value

            # Determine action target
            action_target = ""
            if button.get("hx-post"):
                action_target = button.get("hx-post")
            elif button.get("hx-get"):
                action_target = button.get("hx-get")
            elif button.get("onclick"):
                action_target = button.get("onclick")

            element = ScreenElement(
                element_id=element_id,
                element_type="button",
                name=name,
                action_target=action_target,
                htmx_attributes=htmx_attrs,
                expected_outcome=self._infer_button_outcome(button),
            )

            screen.add_element(element)

    def _extract_links(self, soup: BeautifulSoup, screen: ScreenDocumentation):
        """Extract navigation links"""
        links = soup.find_all("a", href=True)

        for link in links:
            href = link.get("hre")
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            element_id = link.get("id", "")
            if not element_id:
                text = link.get_text().strip()
                element_id = re.sub(r"[^\w]", "_", text.lower()) if text else "unnamed_link"

            name = link.get_text().strip()

            element = ScreenElement(
                element_id=element_id,
                element_type="link",
                name=name,
                action_target=href,
                expected_outcome=f"Navigate to {href}",
            )

            screen.add_element(element)

    def _extract_htmx_elements(self, soup: BeautifulSoup, screen: ScreenDocumentation):
        """Extract elements with HTMX attributes"""
        htmx_elements = soup.find_all(
            attrs=lambda x: x and any(attr.startswith("hx-") for attr in x)
        )

        for elem in htmx_elements:
            if elem.name in ["button", "input", "a"]:
                continue  # Already processed

            element_id = elem.get("id", "")
            if not element_id:
                continue

            htmx_attrs = {}
            for attr_name, attr_value in elem.attrs.items():
                if attr_name.startswith("hx-"):
                    htmx_attrs[attr_name] = attr_value

            element = ScreenElement(
                element_id=element_id,
                element_type="htmx_element",
                name=elem.get_text().strip()[:50] or element_id,
                htmx_attributes=htmx_attrs,
            )

            screen.add_element(element)

    def _infer_button_outcome(self, button) -> str:
        """Infer what a button does based on its attributes"""
        text = button.get_text().strip().lower()

        if "save" in text or "submit" in text:
            return "Save form data"
        elif "delete" in text:
            return "Delete item"
        elif "edit" in text:
            return "Navigate to edit form"
        elif "cancel" in text:
            return "Cancel operation and return"
        elif "apply" in text:
            return "Apply changes"
        elif "generate" in text:
            return "Generate content"
        else:
            return f"Execute action: {text}"

    def _analyze_url_patterns(self):
        """Analyze URL patterns and match them to screens"""
        try:
            resolver = get_resolver()
            url_patterns = self._extract_url_patterns(resolver.url_patterns)

            for pattern_info in url_patterns:
                # Try to match URL pattern to screen
                self._match_url_to_screen(pattern_info)

        except Exception as e:
            print(f"⚠️ Error analyzing URL patterns: {e}")

    def _extract_url_patterns(self, patterns, namespace=""):
        """Recursively extract URL patterns"""
        url_patterns = []

        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                # URLconf include
                sub_namespace = (
                    f"{namespace}:{pattern.namespace}" if pattern.namespace else namespace
                )
                url_patterns.extend(self._extract_url_patterns(pattern.url_patterns, sub_namespace))
            else:
                # Regular URL pattern
                pattern_str = str(pattern.pattern)
                view_name = getattr(pattern, "name", "")
                full_name = f"{namespace}:{view_name}" if namespace and view_name else view_name

                url_patterns.append(
                    {"pattern": pattern_str, "name": full_name, "view_name": view_name}
                )

        return url_patterns

    def _match_url_to_screen(self, pattern_info):
        """Match URL pattern to existing screen documentation"""
        view_name = pattern_info["view_name"]
        pattern = pattern_info["pattern"]

        # Try to find matching screen by name similarity
        for screen_id, screen in self.screens.items():
            if view_name and (view_name in screen_id or screen_id in view_name):
                screen.url_pattern = pattern
                break


class ScreenTestGenerator:
    """Generates automated tests from screen documentation"""

    def __init__(self):
        """Function description."""
        self.output_dir = project_root / "tests" / "generated"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_robot_framework_tests(self, screen: ScreenDocumentation) -> str:
        """Generate Robot Framework test suite for a screen"""
        test_content = """*** Settings ***
Documentation    Automated tests for {screen.name}
Library          SeleniumLibrary
Library          Collections
Test Setup       Open Browser And Navigate To Screen
Test Teardown    Close Browser

*** Variables ***
${{BASE_URL}}     http://127.0.0.1:8000
${{SCREEN_URL}}   {screen.url_pattern}

*** Test Cases ***
Test {screen.name.replace(' ', '_')}_Screen_Loads
    [Documentation]    Verify that the {screen.name} screen loads correctly
    [Tags]    smoke    {screen.screen_type}
    Page Should Contain    {screen.name}

"""

        # Generate tests for each element
        for element in screen.elements:
            if element.element_type.startswith("input_"):
                test_content += self._generate_input_test(element, screen)
            elif element.element_type == "button":
                test_content += self._generate_button_test(element, screen)

        test_content += """
*** Keywords ***
Open Browser And Navigate To Screen
    Open Browser    ${BASE_URL}${SCREEN_URL}    chrome
    Maximize Browser Window

"""

        # Save test file
        test_file = self.output_dir / f"{screen.screen_id}_tests.robot"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        return str(test_file)

    def _generate_input_test(self, element: ScreenElement, screen: ScreenDocumentation) -> str:
        """Generate test for input element"""
        return """
Test_{element.element_id}_Input_Validation
    [Documentation]    Test input validation for {element.name}
    [Tags]    input    validation
    Element Should Be Visible    id={element.element_id}
    {"Element Should Be Enabled" if not element.is_required else "Element Should Be Visible"}    id={element.element_id}

"""

    def _generate_button_test(self, element: ScreenElement, screen: ScreenDocumentation) -> str:
        """Generate test for button element"""
        return """
Test_{element.element_id}_Button_Action
    [Documentation]    Test {element.name} button functionality
    [Tags]    button    action
    Element Should Be Visible    id={element.element_id}
    Click Element    id={element.element_id}
    # Expected outcome: {element.expected_outcome}

"""

    def generate_selenium_tests(self, screen: ScreenDocumentation) -> str:
        """Generate Selenium Python tests for a screen"""
        test_content = '''"""
Automated tests for {screen.name}
Generated by Screen Documentation Framework
"""
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Test{screen.name.replace(" ", "")}Screen(unittest.TestCase):
    """Test suite for {screen.name}"""

    def setUp(self):
        """Function description."""
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.base_url = "http://127.0.0.1:8000"

    def tearDown(self):
        """Function description."""
        self.driver.quit()

    def test_screen_loads(self):
        """Test that the screen loads correctly"""
        self.driver.get(f"{{self.base_url}}{screen.url_pattern}")
        self.assertIn("{screen.name}", self.driver.title)

'''

        # Generate tests for elements
        for element in screen.elements:
            if element.element_type == "button":
                test_content += '''
    def test_{element.element_id}_button(self):
        """Test {element.name} button"""
        self.driver.get(f"{{self.base_url}}{screen.url_pattern}")
        button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "{element.element_id}"))
        )
        self.assertTrue(button.is_displayed())
        # Expected outcome: {element.expected_outcome}

'''

        test_content += """
if __name__ == "__main__":
    unittest.main()
"""

        # Save test file
        test_file = self.output_dir / f"test_{screen.screen_id}.py"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        return str(test_file)


def main():
    """Main function to run screen documentation"""
    import argparse

    parser = argparse.ArgumentParser(description="Screen Documentation & Testing Framework")
    parser.add_argument(
        "command", choices=["discover", "generate-tests", "report"], help="Command to execute"
    )
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument(
        "--format", choices=["json", "markdown"], default="json", help="Output format"
    )

    args = parser.parse_args()

    if args.command == "discover":
        print("🔍 Starting screen discovery...")
        discovery = ScreenDiscoveryTool()
        screens = discovery.discover_all_screens()

        print("\n📊 Discovery Summary:")
        print(f"- Total screens found: {len(screens)}")

        screen_types = {}
        total_elements = 0

        for screen in screens.values():
            screen_types[screen.screen_type] = screen_types.get(screen.screen_type, 0) + 1
            total_elements += len(screen.elements)

        print(f"- Total UI elements: {total_elements}")
        print(f"- Screen types: {dict(screen_types)}")

        # Save results
        if args.output:
            output_data = {screen_id: screen.to_dict() for screen_id, screen in screens.items()}

            if args.format == "json":
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
            else:
                # Generate markdown report
                markdown_content = generate_markdown_report(screens)
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

            print(f"📄 Results saved to: {args.output}")

    elif args.command == "generate-tests":
        print("🧪 Generating automated tests...")
        discovery = ScreenDiscoveryTool()
        screens = discovery.discover_all_screens()

        test_generator = ScreenTestGenerator()
        generated_files = []

        for screen in screens.values():
            if len(screen.elements) > 0:  # Only generate tests for screens with elements
                robot_file = test_generator.generate_robot_framework_tests(screen)
                selenium_file = test_generator.generate_selenium_tests(screen)
                generated_files.extend([robot_file, selenium_file])

        print(f"✅ Generated {len(generated_files)} test files")
        for file_path in generated_files:
            print(f"   📄 {file_path}")


def generate_markdown_report(screens: Dict[str, ScreenDocumentation]) -> str:
    """Generate a markdown report of all screens"""
    content = """# Screen Documentation Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Total Screens**: {len(screens)}
- **Total Elements**: {sum(len(screen.elements) for screen in screens.values())}

## Screens Overview

"""

    for screen in screens.values():
        content += """### {screen.name}
- **Screen ID**: `{screen.screen_id}`
- **Type**: {screen.screen_type}
- **Template**: `{screen.template_path}`
- **URL Pattern**: `{screen.url_pattern}`
- **Elements**: {len(screen.elements)}

{screen.description}

#### UI Elements:
"""

        for element in screen.elements:
            content += f"- **{element.name}** ({element.element_type})"
            if element.is_required:
                content += " *[Required]*"
            content += f"\n  - ID: `{element.element_id}`\n"
            if element.expected_outcome:
                content += f"  - Expected Outcome: {element.expected_outcome}\n"
            content += "\n"

        content += "\n---\n\n"

    return content


if __name__ == "__main__":
    main()
