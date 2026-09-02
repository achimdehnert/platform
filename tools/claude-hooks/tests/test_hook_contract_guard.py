"""Drill fuer den Auffangbogen aller Stop-Hooks (platform#2606, Stufe 1).

Der Hook-Vertrag lautet: **Exit 0 immer, ausser bewusstes Blocken.** Bis
2026-09-02 lag um `main()` in KEINEM der sieben Stop-Hook-Module ein
Auffangbogen — gepruefte Bestandsaufnahme dieses PRs: zwei Module hatten
ueberhaupt ein `except Exception` (`log_llm_call`, `evidence_claim_scanner`),
und in beiden deckte es nur einzelne Teilschritte ab. Eine unerwartete Ausnahme
(kaputte Zustandsdatei, unerwartete Transkript-Form, halb installiertes
`psycopg`) waere als Traceback mit Exit 1 aus dem Vertrag gefallen.

Der Drill prueft beide Richtungen gleichberechtigt, weil ein Auffangbogen genau
zwei Arten hat, falsch zu sein:

1. **Er faengt nicht** — dann kippt der Melder den Turn.
2. **Er faengt zu viel** — dann verschluckt er ein BEWUSSTES Blocken, und das
   Gate meldet stumm nichts mehr. Diese Richtung ist die teurere: sie sieht im
   Betrieb aus wie „alles in Ordnung".
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_DIR))

#: Alle in settings.json registrierten Stop-/SubagentStop-Hooks.
HOOK_MODULE = [
    "log_llm_call",
    "evidence_claim_scanner",
    "deferred_item_scanner",
    "scope_checkpoint_scanner",
    "artefakt_budget",
    "untested_command_scanner",
    "memory_link_guard",
]


def _lade(name: str):
    spec = importlib.util.spec_from_file_location(name, _DIR / f"{name}.py")
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture(params=HOOK_MODULE)
def hook(request):
    return _lade(request.param)


def test_should_jeder_stop_hook_einen_auffangbogen_haben(hook) -> None:
    assert hasattr(hook, "main_sicher"), (
        f"{hook.__name__} hat keinen `main_sicher` — der Hook-Vertrag "
        "(Exit 0 immer) ist damit unerzwungen."
    )


def test_should_exit_0_wenn_main_wirft(hook, monkeypatch, capsys) -> None:
    """Fehler-Injektion: der Traceback darf den Turn nicht kippen."""

    def explodiert() -> int:
        raise RuntimeError("absichtlich geworfen")

    monkeypatch.setattr(hook, "main", explodiert)

    assert hook.main_sicher() == 0
    fehler = capsys.readouterr().err
    assert "RuntimeError" in fehler and "absichtlich geworfen" in fehler, (
        "der Fehler wurde still geschluckt — dann faellt ein kaputter Hook nie auf"
    )


def test_should_ein_bewusstes_blocken_nicht_verschlucken(
    hook, monkeypatch, capsys
) -> None:
    """Gegenprobe zur Fehler-Injektion: `decision: block` muss durchkommen."""
    block = {"decision": "block", "reason": "bewusst geblockt"}

    def blockt() -> int:
        print(json.dumps(block))
        return 0

    monkeypatch.setattr(hook, "main", blockt)

    assert hook.main_sicher() == 0
    assert json.loads(capsys.readouterr().out.strip()) == block


def test_should_einen_gewollten_exit_code_durchlassen(hook, monkeypatch) -> None:
    """Exit 2 ist der zweite Blockier-Weg — `SystemExit` ist keine `Exception`."""

    def blockt_hart() -> int:
        sys.exit(2)

    monkeypatch.setattr(hook, "main", blockt_hart)

    with pytest.raises(SystemExit) as raus:
        hook.main_sicher()
    assert raus.value.code == 2


def test_should_einen_rueckgabewert_unveraendert_reichen(hook, monkeypatch) -> None:
    monkeypatch.setattr(hook, "main", lambda: 2)

    assert hook.main_sicher() == 2


# --- Echte Blockier-Pfade, ohne Attrappe ------------------------------------
#
# Die Faelle oben ersetzen `main` durch eine Attrappe; sie belegen den Bogen,
# nicht den Scanner. Der Fall hier faehrt den ECHTEN blocking-Pfad des
# untested_command_scanner durch `main_sicher` — damit die Aussage „ein
# bewusstes Blocken kommt durch" nicht nur fuer die Attrappe gilt.


def test_should_echten_blocking_pfad_durch_den_bogen_lassen(
    monkeypatch, capsys, tmp_path
) -> None:
    scanner = _lade("untested_command_scanner")
    import gate_hits  # noqa: PLC0415  (haengt am sys.path oben)

    monkeypatch.setattr(gate_hits, "HITS", tmp_path / "gate-hits.jsonl")
    monkeypatch.setattr(scanner, "_mode", lambda: "blocking")
    monkeypatch.setattr(
        scanner,
        "_last_turn",
        lambda _p: ("Auf dem Server laeuft `systemctl restart iil-worker`.", [], set()),
    )
    monkeypatch.setattr(
        scanner, "find_untested", lambda *a: (["systemctl restart iil-worker"], [])
    )
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"transcript_path": str(transcript)}))
    )

    assert scanner.main_sicher() == 0
    ausgabe = json.loads(capsys.readouterr().out.strip())
    assert ausgabe["decision"] == "block"
