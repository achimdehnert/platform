"""
URL Reference Audit — reusable across all platform Django repos.

Ensures every {% url 'namespace:name' %} in templates has a matching
registered URL pattern. Prevents NoReverseMatch 500 errors caused by:
- URLs registered in API namespace but missing from HTML namespace
- Typos in URL names
- Deleted views whose URL names remain in templates

Usage in any repo's test suite:
    # tests/test_url_audit.py
    from platform_context.checks.test_url_audit import TemplateUrlAuditMixin
    from django.test import TestCase

    class TestUrls(TemplateUrlAuditMixin, TestCase):
        templates_dir = "src/templates"  # relative to repo root
"""

import re
from pathlib import Path

from django.urls import NoReverseMatch, reverse


class TemplateUrlAuditMixin:
    """Mixin for Django TestCase — scans templates for broken URL refs."""

    # Override in subclass if templates are elsewhere
    templates_dir = "templates"

    def _find_templates_dir(self):
        """Walk up from test file to find the templates directory."""
        current = Path(__file__).resolve().parent
        for _ in range(10):
            candidate = current / self.templates_dir
            if candidate.is_dir():
                return candidate
            # Try src/templates (risk-hub pattern)
            candidate = current / "src" / "templates"
            if candidate.is_dir():
                return candidate
            current = current.parent
        return None

    def test_all_template_url_references_resolve(self):
        """Every {% url 'ns:name' %} in templates must be resolvable."""
        tpl_dir = self._find_templates_dir()
        if tpl_dir is None:
            self.skipTest("templates/ directory not found")

        url_re = re.compile(
            r"""{%\s*url\s+['"]"""
            r"""([a-zA-Z_][a-zA-Z0-9_]*"""
            r""":[a-zA-Z0-9_-]+)['"]"""
        )

        missing = []
        checked = 0

        for html_file in tpl_dir.rglob("*.html"):
            content = html_file.read_text(errors="ignore")
            for match in url_re.finditer(content):
                url_name = match.group(1)
                checked += 1
                try:
                    reverse(url_name)
                except NoReverseMatch as e:
                    msg = str(e)
                    if "is not a valid view" in msg:
                        rel = html_file.relative_to(tpl_dir)
                        ln = content[: match.start()].count("\n") + 1
                        missing.append(f"  {rel}:{ln} → {url_name}")

        self.assertGreater(checked, 0, "No URL references found")
        self.assertEqual(
            missing,
            [],
            f"\n{len(missing)} broken URL reference(s):\n"
            + "\n".join(missing)
            + "\n\nFix: register URL in the correct "
            + "html_urls.py (not just API urls.py)",
        )
