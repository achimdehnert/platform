"""Tests für registry-canonical.py — flip-Idempotenz der GEN_NOTICE-Behandlung (REC-5/REC-6).

Der flip-Doppel-Header-Bug (jeder Roundtrip akkumulierte einen weiteren GENERATED-Header) wird
durch `_strip_gen_notice` (exakte Zeilen-Identität, nicht Box-Char-Heuristik) verhindert. Dieser
Test pinnt die Idempotenz — er läuft im generischen tools-tests.yml Gate (#494).

Run: `python3 -m pytest tools/tests/test_registry_canonical.py -q`
(registry-canonical.py hat einen Bindestrich → via importlib geladen.)
"""
import importlib.util
import pathlib
import sys

_TOOLS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TOOLS))  # registry-canonical.py macht modul-level `from registry_api import …`

_SRC = _TOOLS / "registry-canonical.py"
_spec = importlib.util.spec_from_file_location("registry_canonical", _SRC)
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

DOCS = "# Schema-Doc Zeile 1\n# Schema-Doc Zeile 2\n"


def test_should_strip_single_gen_notice_keep_docs():
    out = rc._strip_gen_notice(rc.GEN_NOTICE + "\n" + DOCS)
    assert out.strip() == DOCS.strip()


def test_should_strip_accumulated_gen_notice_idempotently():
    # Doppel-Header (der frühere Bug) → trotzdem nur Schema-Docs übrig
    doubled = rc.GEN_NOTICE + rc.GEN_NOTICE + "\n" + DOCS
    assert rc._strip_gen_notice(doubled).strip() == DOCS.strip()


def test_should_leave_text_without_notice_unchanged():
    assert rc._strip_gen_notice(DOCS).strip() == DOCS.strip()


def test_should_not_strip_docs_that_merely_resemble_notice():
    # Eine Schema-Doc-Zeile, die KEINE exakte GEN_NOTICE-Zeile ist, bleibt erhalten
    text = "# GENERATED irgendwas anderes (kein exakter Match)\n" + DOCS
    out = rc._strip_gen_notice(text)
    assert "kein exakter Match" in out  # nicht versehentlich gestrippt (REC-5 Determinismus)
