"""Tests fuer tools/pypi_fleet_sections.py — reine Merge-Logik (KONZ-052 V5).

Deckt genau das ab, was drei Melder-Issues (#968/#373/#752) zu einem
konsolidiert (KONZ-018 §5.4: kein neuer Meter, kein neues Rolling-Issue):
jede Sektion wird unabhaengig ersetzt, andere Sektionen bleiben unberuehrt.
"""

from __future__ import annotations

import importlib.util
import pathlib
import urllib.error

_SPEC = importlib.util.spec_from_file_location(
    "pypi_fleet_sections",
    pathlib.Path(__file__).resolve().parents[1] / "pypi_fleet_sections.py",
)
m = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m)


def test_should_wrap_body_in_named_markers():
    rendered = m.render_section("health", "Fleet-Health", "Alles gruen.")
    assert rendered.startswith("<!-- section:health -->")
    assert rendered.endswith("<!-- /section:health -->")
    assert "## Fleet-Health" in rendered
    assert "Alles gruen." in rendered


def test_should_append_section_to_empty_body():
    rendered = m.render_section("adoption", "Adoption", "18/19")
    merged = m.merge_section("", "adoption", rendered)
    assert merged.strip() == rendered


def test_should_append_new_section_after_existing_one():
    existing = m.render_section("health", "Health", "ok")
    new_section = m.render_section("adoption", "Adoption", "18/19")
    merged = m.merge_section(existing, "adoption", new_section)
    assert "<!-- section:health -->" in merged
    assert "<!-- section:adoption -->" in merged
    assert merged.index("section:health") < merged.index("section:adoption")


def test_should_replace_only_the_named_section():
    health = m.render_section("health", "Health", "stale-report")
    adoption = m.render_section("adoption", "Adoption", "18/19")
    existing = m.merge_section(health, "adoption", adoption)

    new_health = m.render_section("health", "Health", "fresh-report")
    merged = m.merge_section(existing, "health", new_health)

    assert "fresh-report" in merged
    assert "stale-report" not in merged
    assert "<!-- section:adoption -->" in merged
    assert "18/19" in merged


def test_should_be_idempotent_on_repeated_merge():
    section = m.render_section("gate-meter", "Gate-Meter", "leer")
    once = m.merge_section("", "gate-meter", section)
    twice = m.merge_section(once, "gate-meter", section)
    assert once == twice


def test_should_not_update_issue_when_title_and_body_unchanged():
    existing = {"title": "T", "body": "B"}
    assert m.issue_needs_update(existing, "T", "B") is False


def test_should_update_issue_when_body_changed():
    existing = {"title": "T", "body": "alt"}
    assert m.issue_needs_update(existing, "T", "neu") is True


def test_should_update_issue_when_title_changed():
    existing = {"title": "alt", "body": "B"}
    assert m.issue_needs_update(existing, "neu", "B") is True


def test_should_update_issue_when_existing_body_is_none():
    # GitHub liefert body=None für leere Issues → muss als Änderung gelten, wenn neuer Body da ist.
    assert m.issue_needs_update({"title": "T", "body": None}, "T", "B") is True
    assert m.issue_needs_update({"title": "T", "body": None}, "T", "") is False


def test_should_preview_update_on_dry_run_when_issue_exists(monkeypatch):
    monkeypatch.setattr(
        m, "fetch_issue", lambda owner, repo, token, label=m.ISSUE_LABEL: {"number": 968}
    )
    url = m.upsert_section(
        "achimdehnert", "platform", "tok", "health", "Health", "ok", dry_run=True
    )
    assert "#968" in url
    assert "wuerde" in url


def test_should_preview_create_on_dry_run_when_no_issue_exists(monkeypatch):
    monkeypatch.setattr(
        m, "fetch_issue", lambda owner, repo, token, label=m.ISSUE_LABEL: None
    )
    url = m.upsert_section(
        "achimdehnert", "platform", "tok", "health", "Health", "ok", dry_run=True
    )
    assert "neues Fleet-Issue" in url


def test_should_not_crash_dry_run_when_fetch_fails(monkeypatch):
    # Kein Token / Rate-Limit im Dry-Run darf den Wiring-Beweis (PR-Dry-Run)
    # nicht sprengen — Fallback auf die generische Vorschau statt Exception.
    def boom(*a, **kw):
        raise urllib.error.URLError("kein Netz")

    monkeypatch.setattr(m, "fetch_issue", boom)
    url = m.upsert_section(
        "achimdehnert", "platform", "", "health", "Health", "ok", dry_run=True
    )
    assert "DRY-RUN" in url


def test_should_omit_authorization_header_when_token_empty(monkeypatch):
    # Ein leerer Bearer-Header wird von GitHub als 401 behandelt, nicht als
    # anonymer Request — deshalb darf der Header ohne Token gar nicht gesetzt sein.
    captured = {}

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"[]"

    def fake_urlopen(request):
        captured["has_auth"] = request.has_header("Authorization")
        return _FakeResp()

    monkeypatch.setattr(m.urllib.request, "urlopen", fake_urlopen)
    m._api("/x", "")
    assert captured["has_auth"] is False
