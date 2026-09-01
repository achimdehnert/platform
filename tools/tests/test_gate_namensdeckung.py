"""Drill fuer tools/gate_namensdeckung.py — beruehrt der Drill den Slug-Fall?

Der wichtigste Test hier ist NICHT die Luecken-Erkennung, sondern die Trennung von
`ungeprueft` und `gedeckt`: ein Gate ohne `faengt`-Feld darf niemals gruen wirken.
Genau diese dritte Moeglichkeit fehlte im Loop und liess `lint-failure-no-local-gate`
drei Wochen lang die falsche Sache pruefen — Registry, Drill und Verdrahtung standen
auf gruen, weil niemand die Frage gestellt hatte.

Zweitwichtigster Test: die Grenze des Werkzeugs selbst. Es misst das BERUEHREN, nicht
das Abfangen — `test_should_not_claim_the_case_is_actually_caught` haelt fest, dass
eine blosse Erwaehnung des Falls reicht. Wer das spaeter verschaerfen will, sieht hier,
was heute versprochen wurde und was nicht.

Run: `python3 -m pytest tools/tests/test_gate_namensdeckung.py -q`
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "gate_namensdeckung.py"
_spec = importlib.util.spec_from_file_location("gate_namensdeckung", _QUELLE)
gn = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gn)


def _repo(tmp_path: Path, drill_inhalt: str, name: str = "drill.py") -> Path:
    (tmp_path / name).write_text(drill_inhalt, encoding="utf-8")
    return tmp_path


def test_should_call_a_gate_without_the_field_unchecked_not_covered(tmp_path):
    """`ungeprueft` ist kein Gruen — die Frage wurde nie gestellt."""
    stand = gn.pruefe_gate({"slug": "g", "drill": "drill.py"}, str(tmp_path))
    assert stand["zustand"] == "ungeprueft"
    assert stand["gedeckt"] == [] and stand["fehlend"] == []


def test_should_report_a_luecke_when_the_probe_is_missing(tmp_path):
    """Der Realfall: Slug verspricht Lint, der Drill kennt nur Layout."""
    repo = _repo(tmp_path, "def test_unformatiert(): pass\n")
    gate = {
        "slug": "lint",
        "drill": "drill.py",
        "faengt": [{"fall": "E402", "probe": "e402"}],
    }
    stand = gn.pruefe_gate(gate, str(repo))
    assert stand["zustand"] == "luecke"
    assert stand["fehlend"] == ["E402"]


def test_should_report_covered_when_every_probe_is_present(tmp_path):
    repo = _repo(tmp_path, "def test_e402(): pass\ndef test_unformatiert(): pass\n")
    gate = {
        "slug": "lint",
        "drill": "drill.py",
        "faengt": [
            {"fall": "E402", "probe": "e402"},
            {"fall": "Layout", "probe": "unformatiert"},
        ],
    }
    stand = gn.pruefe_gate(gate, str(repo))
    assert stand["zustand"] == "gedeckt"
    assert len(stand["gedeckt"]) == 2


def test_should_search_drill_extra_files_too(tmp_path):
    """Ein Python-Drill, der nur eine Bash-Suite aufruft, traegt den Fall dort."""
    _repo(tmp_path, "subprocess.run(['bash', SUITE])\n")
    (tmp_path / "suite.sh").write_text(
        "check 'T11 E402 blockt' deny\n", encoding="utf-8"
    )
    gate = {
        "slug": "lint",
        "drill": "drill.py",
        "drill_extra": ["suite.sh"],
        "faengt": [{"fall": "E402", "probe": "e402"}],
    }
    assert gn.pruefe_gate(gate, str(tmp_path))["zustand"] == "gedeckt"


def test_should_match_the_probe_case_insensitively(tmp_path):
    repo = _repo(tmp_path, "# Fall: ruff E402 im Koerper\n")
    gate = {
        "slug": "g",
        "drill": "drill.py",
        "faengt": [{"fall": "E402", "probe": "e402"}],
    }
    assert gn.pruefe_gate(gate, str(repo))["zustand"] == "gedeckt"


def test_should_report_a_luecke_when_the_drill_file_is_missing(tmp_path):
    """Ein Drill, den es nicht gibt, beruehrt keinen Fall — Luecke, kein Absturz."""
    gate = {
        "slug": "g",
        "drill": "gibtsnicht.py",
        "faengt": [{"fall": "X", "probe": "x"}],
    }
    stand = gn.pruefe_gate(gate, str(tmp_path))
    assert stand["zustand"] == "luecke"
    assert stand["dateien"] == 0


def test_should_not_claim_the_case_is_actually_caught(tmp_path):
    """GRENZE des Werkzeugs, ausdruecklich festgehalten.

    Eine blosse Erwaehnung des Falls im Drill genuegt fuer `gedeckt` — auch in
    einem Kommentar, der gar nichts testet. Das Werkzeug misst das Beruehren,
    nicht das Abfangen. Wer diesen Test rot macht, verschaerft das Versprechen
    und muss die Doku mitziehen.
    """
    repo = _repo(tmp_path, "# TODO: irgendwann mal E402 testen\n")
    gate = {
        "slug": "g",
        "drill": "drill.py",
        "faengt": [{"fall": "E402", "probe": "e402"}],
    }
    assert gn.pruefe_gate(gate, str(repo))["zustand"] == "gedeckt"


def test_should_stay_silent_in_kurz_mode_without_luecken():
    staende = [
        {
            "slug": "a",
            "zustand": "gedeckt",
            "gedeckt": ["x"],
            "fehlend": [],
            "dateien": 1,
        },
        {
            "slug": "b",
            "zustand": "ungeprueft",
            "gedeckt": [],
            "fehlend": [],
            "dateien": 0,
        },
    ]
    assert gn.bericht(staende, kurz=True) == ""


def test_should_speak_up_in_kurz_mode_on_a_luecke():
    staende = [
        {
            "slug": "lint",
            "zustand": "luecke",
            "gedeckt": [],
            "fehlend": ["E402"],
            "dateien": 1,
        }
    ]
    zeile = gn.bericht(staende, kurz=True)
    assert "lint" in zeile and "E402" in zeile


def test_should_name_unchecked_gates_in_the_full_report():
    staende = [
        {
            "slug": "b",
            "zustand": "ungeprueft",
            "gedeckt": [],
            "fehlend": [],
            "dateien": 0,
        }
    ]
    text = gn.bericht(staende, kurz=False)
    assert "ungeprueft : 1" in text and "die Frage wurde nie gestellt" in text


def test_should_return_zero_on_an_unreadable_registry(tmp_path):
    assert gn.main(["--registry", str(tmp_path / "weg.json")]) == 0


def test_every_gate_with_faengt_in_the_real_registry_is_wellformed():
    """Bestandsprobe: jedes gefuellte `faengt` traegt `fall` UND `probe`."""
    reg = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "governance"
            / "gate-registry.json"
        ).read_text(encoding="utf-8")
    )
    for gate in reg["gates"]:
        for fall in gate.get("faengt", []):
            assert fall.get("fall"), gate["slug"]
            assert fall.get("probe"), gate["slug"]
