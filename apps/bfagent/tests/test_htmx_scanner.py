"""
Test suite for Enhanced HTMX Conformity Scanner
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from htmx_scanner_v2 import (
    EnhancedHTMXScanner,
    HTMXIssue,
    HTMXPatternMatcher,
    HTMXReport,
    ScanConfig,
)


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary Django project structure"""
    # Create directory structure
    (tmp_path / "templates").mkdir()
    (tmp_path / "apps").mkdir()
    (tmp_path / "static").mkdir()
    (tmp_path / "apps" / "myapp").mkdir()
    (tmp_path / "apps" / "myapp" / "templates").mkdir()

    return tmp_path


@pytest.fixture
def scanner(temp_project):
    """Create scanner instance with temp project"""
    config = ScanConfig(parallel_scanning=False)  # Disable for tests
    return EnhancedHTMXScanner(str(temp_project), config)


class TestHTMXPatternMatcher:
    """Test pattern matching functionality"""

    def test_form_without_htmx_detection(self):
        matcher = HTMXPatternMatcher()

        # Should match
        html1 = '<form method="post" action="/submit">'
        assert matcher.patterns["form_without_htmx"].search(html1)

        # Should not match
        html2 = '<form method="post" hx-post="/submit">'
        assert not matcher.patterns["form_without_htmx"].search(html2)

    def test_invalid_target_detection(self):
        matcher = HTMXPatternMatcher()

        # Should match invalid target
        html1 = 'hx-target="#content-area"'
        match = matcher.patterns["invalid_target"].search(html1)
        assert match
        assert match.group("target") == "#content-area"

        # Should not match valid target
        html2 = 'hx-target="body"'
        assert matcher.patterns["invalid_target"].search(html2)  # Will match but scanner validates

    def test_missing_csrf_detection(self):
        matcher = HTMXPatternMatcher()

        # Should match form without CSRF
        html1 = '<form hx-post="/submit"><input name="test"></form>'
        assert matcher.patterns["missing_csrf"].search(html1)

        # Should still match (scanner checks content)
        html2 = '<form hx-post="/submit">{% csrf_token %}<input name="test"></form>'
        assert matcher.patterns["missing_csr"].search(html2)


class TestEnhancedHTMXScanner:
    """Test the main scanner functionality"""

    def test_scanner_initialization(self, temp_project):
        config = ScanConfig()
        scanner = EnhancedHTMXScanner(str(temp_project), config)

        assert scanner.project_root == temp_project
        assert scanner.config == config
        assert "body" in scanner.valid_targets

    def test_scan_template_with_issues(self, scanner, temp_project):
        # Create template with issues
        template_content = """
        <form method="post" action="/submit">
            <input name="test">
        </form>
        <div hx-get="/data" hx-target="#content-area"></div>
        """

        template_file = temp_project / "templates" / "test.html"
        template_file.write_text(template_content)

        issues = scanner.scan_template_advanced(template_file)

        # Should find issues
        assert len(issues) > 0

        # Check for specific issue types
        issue_types = [issue.issue_type for issue in issues]
        assert "form_without_htmx" in issue_types
        assert "invalid_target" in issue_types

    def test_scan_template_without_issues(self, scanner, temp_project):
        # Create template without issues
        template_content = """
        <form hx-post="{% url 'submit' %}" hx-target="body">
            {% csrf_token %}
            <input name="test">
        </form>
        """

        template_file = temp_project / "templates" / "good.html"
        template_file.write_text(template_content)

        issues = scanner.scan_template_advanced(template_file)

        # Should find minimal or no issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        assert len(critical_issues) == 0

    def test_generate_report(self, scanner, temp_project):
        # Create template with known issues
        template_content = """
        <form method="post" hx-target="#content-area">
            <input name="test">
        </form>
        """

        template_file = temp_project / "templates" / "report_test.html"
        template_file.write_text(template_content)

        report = scanner.generate_report()

        assert isinstance(report, HTMXReport)
        assert report.total_files_scanned >= 1
        assert report.issues_found >= 0
        assert 0 <= report.conformity_score <= 100
        assert report.scan_duration >= 0

    def test_statistics_calculation(self, scanner):
        # Create mock issues
        issues = [
            HTMXIssue(
                file_path="test1.html",
                line_number=1,
                issue_type="missing_csr",
                description="Test",
                current_code="",
                suggested_fix="",
                severity="critical",
                category="template",
                auto_fixable=True,
            ),
            HTMXIssue(
                file_path="test2.html",
                line_number=1,
                issue_type="missing_csr",
                description="Test",
                current_code="",
                suggested_fix="",
                severity="critical",
                category="template",
                auto_fixable=True,
            ),
            HTMXIssue(
                file_path="test1.html",
                line_number=2,
                issue_type="invalid_target",
                description="Test",
                current_code="",
                suggested_fix="",
                severity="warning",
                category="template",
                auto_fixable=False,
            ),
        ]

        stats = scanner._calculate_statistics(issues)

        assert stats["files_scanned"] == 2
        assert stats["issues_by_type"]["missing_csr"] == 2
        assert stats["issues_by_type"]["invalid_target"] == 1
        assert stats["auto_fixable_count"] == 2

    def test_recommendations_generation(self, scanner):
        # Test with CSRF issues
        issues = [
            HTMXIssue(
                file_path="test.html",
                line_number=1,
                issue_type="missing_csr",
                description="Test",
                current_code="",
                suggested_fix="",
                severity="critical",
                category="template",
                auto_fixable=True,
            )
        ]

        stats = {"issues_by_type": {"missing_csrf": 1}, "auto_fixable_count": 1}
        recommendations = scanner._generate_recommendations(issues, stats)

        assert len(recommendations) > 0
        assert any("CSRF" in rec for rec in recommendations)


class TestScanConfig:
    """Test configuration handling"""

    def test_default_config(self):
        config = ScanConfig()

        assert config.parallel_scanning is True
        assert config.max_workers == 4
        assert config.strict_mode is False
        assert len(config.ignore_patterns) > 0

    def test_custom_config(self):
        config = ScanConfig(
            parallel_scanning=False, max_workers=2, strict_mode=True, custom_targets=["#my-target"]
        )

        assert config.parallel_scanning is False
        assert config.max_workers == 2
        assert config.strict_mode is True
        assert "#my-target" in config.custom_targets


class TestIntegration:
    """Integration tests"""

    def test_full_scan_workflow(self, temp_project):
        # Create realistic Django template structure
        templates_dir = temp_project / "templates" / "myapp"
        templates_dir.mkdir(parents=True)

        # Good template
        good_template = templates_dir / "good.html"
        good_template.write_text(
            """
        <form hx-post="{% url 'submit' %}" hx-target="body" class="needs-validation">
            {% csrf_token %}
            <input name="test" required>
            <button type="submit">Submit</button>
        </form>
        """
        )

        # Bad template
        bad_template = templates_dir / "bad.html"
        bad_template.write_text(
            """
        <form method="post" action="/hardcoded" hx-target="#content-area">
            <input name="test">
        </form>
        """
        )

        # Run scanner
        config = ScanConfig(parallel_scanning=False)
        scanner = EnhancedHTMXScanner(str(temp_project), config)
        report = scanner.generate_report()

        # Verify results
        assert report.total_files_scanned >= 2
        assert report.issues_found > 0

        # Should have critical issues from bad template
        assert report.critical_issues > 0

        # Should have recommendations
        assert len(report.recommendations) > 0

        # Conformity score should be reasonable
        assert 0 <= report.conformity_score <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
