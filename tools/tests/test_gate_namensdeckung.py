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


def test_should_call_a_probe_only_the_test_own_example_set_gedeckt_too(tmp_path):
    """Fall `namensanspruch_ohne_gegenprobe` (chat-hub#125 -> #132): eine
    Pruefung, deren Name/Titel Haerte behauptet, deckte real nur die eigene
    Beispielmenge — die Sperrliste aus chat-hub#125 hiess im PR-Titel 'harte
    Sperrliste' und liess 7 von 10 alltaeglichen Formulierungen durch, weil ihr
    Test nur die Woerter aus der eigenen Liste zurueckspielte, nie eine
    adversariale Gegenprobe. Behoben in chat-hub#132: 5 -> 15 Faelle, davon 10
    adversarial und 5 Negativkontrollen.

    Dieselbe Familie wie `test_should_not_claim_the_case_is_actually_caught`,
    hier auf den benannten Realfall zugespitzt: ein Drill, der die Probe nur in
    IHREM EIGENEN Beispiel wiederholt (keine unabhaengige, adversariale
    Formulierung daneben), gilt hier ebenso `gedeckt` — genau die Namensanspruch-
    ohne-Gegenprobe-Luecke, die dieses Werkzeug selbst NICHT mechanisch von
    einem echten adversarialen Test unterscheiden kann (Mutationstest waere
    noetig, s. Modulkopf). Die echte Gegenprobe lebt deshalb nicht hier, sondern
    an der Quelle: iilgmbh/chat-hub tests/test_lotse_auftrag.py::
    test_should_refuse_reaction_for_outward_effect (Positivkontrolle der
    Registry, 0 von 11 nach dem Fix, vorher 7 von 10 falsch).
    """
    repo = _repo(
        tmp_path,
        "WOERTER = ['deployment']\n"
        "def test_sperrt_bekannte_woerter():\n"
        "    assert pruefe('deployment') is False\n",
    )
    gate = {
        "slug": "harte-sperrliste",
        "drill": "drill.py",
        "faengt": [{"fall": "sperrt Deployment", "probe": "deployment"}],
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
    reg = gn.gate_registry.laden()
    for gate in reg["gates"]:
        for fall in gate.get("faengt", []):
            assert fall.get("fall"), gate["slug"]
            assert fall.get("probe"), gate["slug"]


# --- `drill` als Liste (Fix 2026-09-07, platform#2908) ----------------------
#
# Ein Gate darf mehr als einen Erzwingungspunkt haben; `gate_verankerung_check`
# erlaubt String, Komma-Liste und JSON-Liste. Dieses Werkzeug kannte nur die
# erste Form und reichte die Liste an `os.path.isabs` durch — TypeError beim
# ERSTEN solchen Gate, also fuer den ganzen Lauf, und zwar unbemerkt auf `main`.


def test_should_read_a_drill_given_as_a_json_list(tmp_path):
    # POSITIVKONTROLLE: vor dem Fix warf genau dieser Aufruf TypeError.
    (tmp_path / "a.py").write_text("hier steht der erster_fall\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("und hier der zweiter_fall\n", encoding="utf-8")
    stand = gn.pruefe_gate(
        {
            "slug": "g",
            "drill": ["a.py", "b.py"],
            "faengt": [
                {"fall": "eins", "probe": "erster_fall"},
                {"fall": "zwei", "probe": "zweiter_fall"},
            ],
        },
        str(tmp_path),
    )
    assert stand["zustand"] == "gedeckt"
    assert stand["dateien"] == 2


def test_should_read_a_drill_given_as_a_comma_list(tmp_path):
    _repo(tmp_path, "erster_fall\n", "a.py")
    (tmp_path / "b.py").write_text("zweiter_fall\n", encoding="utf-8")
    stand = gn.pruefe_gate(
        {
            "slug": "g",
            "drill": "a.py, b.py",
            "faengt": [{"fall": "zwei", "probe": "zweiter_fall"}],
        },
        str(tmp_path),
    )
    assert stand["zustand"] == "gedeckt"


def test_should_still_read_a_plain_string_drill(tmp_path):
    # Gegenprobe: die bisherige Form bleibt unveraendert gueltig.
    _repo(tmp_path, "erster_fall\n")
    stand = gn.pruefe_gate(
        {
            "slug": "g",
            "drill": "drill.py",
            "faengt": [{"fall": "eins", "probe": "erster_fall"}],
        },
        str(tmp_path),
    )
    assert stand["zustand"] == "gedeckt" and stand["dateien"] == 1


def test_should_not_crash_on_the_real_registry():
    # Der Fall, der das Werkzeug stillgelegt hat: ein Lauf ueber den ECHTEN
    # Bestand. Ein Pruefer, der nur an Fixtures laeuft, beweist wenig.
    registry = gn.gate_registry.laden(gn.DEFAULT_REGISTRY)
    staende = [gn.pruefe_gate(g) for g in registry["gates"]]
    assert len(staende) == len(registry["gates"])


def test_should_read_the_drill_from_the_target_repo_clone(tmp_path, monkeypatch):
    """`repo: owner/name` → Drill liegt unter $GITHUB_DIR/name, nicht in platform."""
    ziel = tmp_path / "gh" / "apo-hub"
    ziel.mkdir(parents=True)
    (ziel / "drill.py").write_text("def test_localdate(): pass\n")
    monkeypatch.setenv("GITHUB_DIR", str(tmp_path / "gh"))
    gate = {
        "slug": "cutoff",
        "repo": "achimdehnert/apo-hub",
        "drill": "drill.py",
        "faengt": [{"fall": "UTC-Datum", "probe": "localdate"}],
    }
    stand = gn.pruefe_gate(gate, str(tmp_path / "platform"))
    assert stand["zustand"] == "gedeckt"


def test_should_keep_the_luecke_when_the_target_clone_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_DIR", str(tmp_path / "leer"))
    gate = {
        "slug": "cutoff",
        "repo": "achimdehnert/apo-hub",
        "drill": "drill.py",
        "faengt": [{"fall": "UTC-Datum", "probe": "localdate"}],
    }
    stand = gn.pruefe_gate(gate, str(tmp_path / "platform"))
    assert stand["zustand"] == "luecke"


# --- `platform:`-Praefix je Drill-Eintrag (Fix platform#3471) ---------------
#
# Realfall `built-but-never-called`: das Gate traegt `repo: iilgmbh/
# ausschreibungs-hub` fuer Fall 1, Rev 2 zog Fall 2 aber bewusst OHNE zweiten
# Registry-Eintrag in platform selbst nach ("ein Gate, zwei Proben, kein
# zweiter Eintrag"). Ohne ein Signal je Eintrag gilt die Wurzel gate-weit —
# der platform-seitige Drill wurde nie gelesen, unabhaengig von seinem Inhalt.


def test_should_resolve_a_platform_prefixed_entry_against_this_clone_even_when_the_gate_is_foreign(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GITHUB_DIR", str(tmp_path / "gh"))
    fremd = tmp_path / "gh" / "apo-hub"
    fremd.mkdir(parents=True)
    (fremd / "drill_dort.py").write_text("def test_fall_eins(): pass  # erster_fall\n")
    hier = tmp_path / "platform" / "tools" / "tests"
    hier.mkdir(parents=True)
    (hier / "drill_hier.py").write_text("def test_fall_zwei(): pass  # zweiter_fall\n")
    gate = {
        "slug": "cutoff",
        "repo": "achimdehnert/apo-hub",
        "drill": ["drill_dort.py", "platform:tools/tests/drill_hier.py"],
        "faengt": [
            {"fall": "eins", "probe": "erster_fall"},
            {"fall": "zwei", "probe": "zweiter_fall"},
        ],
    }
    stand = gn.pruefe_gate(gate, str(tmp_path / "platform"))
    assert stand["zustand"] == "gedeckt"


def test_should_keep_the_luecke_without_the_platform_prefix_even_if_the_file_exists_locally(
    tmp_path, monkeypatch
):
    """Gegenprobe: ohne Praefix bleibt es bei der Gate-Wurzel — sonst waere das
    Praefix Deko und der urspruengliche Realfall (Datei existiert nur in
    platform, wird aber gegen den fremden Klon aufgeloest) bliebe unerklaert."""
    monkeypatch.setenv("GITHUB_DIR", str(tmp_path / "gh"))
    (tmp_path / "gh" / "apo-hub").mkdir(parents=True)
    hier = tmp_path / "platform" / "tools" / "tests"
    hier.mkdir(parents=True)
    (hier / "drill_hier.py").write_text("zweiter_fall\n")
    gate = {
        "slug": "cutoff",
        "repo": "achimdehnert/apo-hub",
        "drill": ["tools/tests/drill_hier.py"],
        "faengt": [{"fall": "zwei", "probe": "zweiter_fall"}],
    }
    stand = gn.pruefe_gate(gate, str(tmp_path / "platform"))
    assert stand["zustand"] == "luecke"
