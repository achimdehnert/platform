"""Profil-Voreinstellungen des Print-Agents (#1297, zweiter Befund) — CI-gegatet.

Liegt hier statt in ``tools/print_agent/tests/``, weil jener Testort in keinem
Workflow läuft und seine Fälle mangels ``weasyprint``/``litellm`` ohnehin still
übersprungen würden. ``profile_policy`` kommt ohne diese Importe aus.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "print_agent"))
import llm_gate  # noqa: E402
import profile_policy  # noqa: E402

# Auszug aus design-hub/profiles/iil-extern.yaml, Stand 2026-07-23.
IIL_EXTERN = {"name": "iil-extern", "authorship": {"recipient": "extern (Kunden, Stakeholder, Konzerne)"}}
DB_INTERN = {"name": "db-intern", "authorship": {"recipient": "intern (Fachbereich)"}}


def test_should_read_audience_from_recipient():
    assert profile_policy.audience(IIL_EXTERN) == "extern"
    assert profile_policy.audience(DB_INTERN) == "intern"


def test_should_default_to_intern_when_profile_says_nothing():
    """Vorsichtige Annahme: unbekannt heißt intern, das lockert nichts nach außen."""
    assert profile_policy.audience({}) == "intern"
    assert profile_policy.audience({"authorship": {}}) == "intern"


def test_should_let_explicit_audience_win_over_recipient():
    prof = dict(IIL_EXTERN, audience="intern")
    assert profile_policy.audience(prof) == "intern"


def test_should_disable_enrichment_for_external_profiles():
    """Der Kern des zweiten Befunds: kein KI-Kasten in einem Angebot."""
    assert profile_policy.enrichment_enabled(IIL_EXTERN) is False
    assert profile_policy.enrichment_enabled(DB_INTERN) is True


def test_should_let_explicit_flag_win_over_audience():
    assert profile_policy.enrichment_enabled(dict(IIL_EXTERN, llm_enrichment=True)) is True
    assert profile_policy.enrichment_enabled(dict(DB_INTERN, llm_enrichment=False)) is False


def test_should_not_guess_doc_type_for_external_documents():
    """„Internes Dokument" auf einem Angebot war der gemeldete Fehler."""
    assert profile_policy.default_doc_type("extern", "db") == ""
    assert profile_policy.default_doc_type("extern", "iil") == ""


def test_should_keep_internal_doc_type_defaults_unchanged():
    assert profile_policy.default_doc_type("intern", "db") == "Internes Dokument"
    assert profile_policy.default_doc_type("intern", "iil") == "Angebot"
    assert profile_policy.default_doc_type("", "db") == "Internes Dokument"


def test_should_name_target_and_size_before_external_call():
    """#1297 Punkt 3: Ziel UND Zeichenzahl, sonst fällt ein Abfluss wieder nicht auf."""
    notice = llm_gate.egress_notice("groq/llama-3.1-8b-instant", 1337)
    assert notice is not None
    assert "1337" in notice
    assert "groq" in notice


def test_should_name_remote_ollama_host_as_target(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://88.99.38.75:11434")
    notice = llm_gate.egress_notice("ollama/qwen2.5:3b", 42)
    assert notice is not None
    assert "88.99.38.75" in notice


def test_should_stay_silent_when_nothing_leaves_the_machine(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    assert llm_gate.egress_target("ollama/qwen2.5:3b") is None
    assert llm_gate.egress_notice("ollama/qwen2.5:3b", 42) is None
