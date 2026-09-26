"""Tests fuer tools/chat_agent/vorschlaege.py (#3369, KONZ-platform-061 MVC-3).

Die Auswahl ist eine reine Funktion — Journal und Merkdatei kommen von aussen,
deshalb braucht kein Test einen Sitzungsstart. Der Aufruf ueber die
Kommandozeile wird wie beim Nachbarn `test_auftragsraum.py` als Unterprozess
geprueft.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKRIPT = Path(__file__).resolve().parents[1] / "chat_agent" / "vorschlaege.py"
_spec = importlib.util.spec_from_file_location("vorschlaege", SKRIPT)
vs = importlib.util.module_from_spec(_spec)
sys.modules["vorschlaege"] = vs
_spec.loader.exec_module(vs)


def _befund(phase, repo="platform", laeufe=5, **rest):
    eintrag = {
        "id": f"{phase}::{repo}",
        "phase": phase,
        "repo": repo,
        "laeufe": laeufe,
        "note": "3 Stueck betroffen",
        "artefakt": None,
        "verzicht": None,
    }
    eintrag.update(rest)
    return eintrag


def test_should_ask_only_for_allowed_classes():
    befunde = [
        _befund("0.4.4 basis-abstand"),
        _befund("0.7.9 gate-deckung"),  # nicht in der Erlaubnisliste
        _befund("0.7.19 melder-praezision"),  # dito
    ]
    gewaehlt = vs.waehle(befunde, {})
    assert [g["phase"] for g in gewaehlt] == ["0.4.4 basis-abstand"]


def test_should_never_ask_for_outward_effect():
    """Deploy, Secrets, Sichtbarkeit: nie per Frage — auch nicht, wenn sie
    sonst alle Bedingungen erfuellen (KONZ-061 D5)."""
    befunde = [_befund(p, laeufe=99) for p in sorted(vs.GESPERRT)]
    assert vs.waehle(befunde, {}) == []


def test_should_skip_findings_that_are_already_tracked():
    befunde = [
        _befund("0.5.2 schleuse", artefakt="https://example.org/issues/1"),
        _befund("0.7.4 prio-referenzen", verzicht="bewusst, Grund steht im Journal"),
        _befund("0.7.23 melder-register"),
    ]
    assert [g["phase"] for g in vs.waehle(befunde, {})] == ["0.7.23 melder-register"]


def test_should_ask_each_finding_only_once():
    befunde = [_befund("0.4.4 basis-abstand")]
    gefragt = {"0.4.4 basis-abstand::platform": "2026-09-22"}
    assert vs.waehle(befunde, gefragt) == []


def test_should_cap_at_three_and_prefer_the_oldest():
    befunde = [
        _befund("0.4.4 basis-abstand", laeufe=10),
        _befund("0.5.2 schleuse", laeufe=99),
        _befund("0.7.4 prio-referenzen", laeufe=50),
        _befund("0.7.23 melder-register", laeufe=1),
    ]
    gewaehlt = vs.waehle(befunde, {})
    assert len(gewaehlt) == 3
    assert [g["laeufe"] for g in gewaehlt] == [99, 50, 10]


def test_should_fill_count_and_repo_into_the_question():
    (frage,) = vs.waehle([_befund("0.4.4 basis-abstand")], {})
    assert frage["frage"].startswith("3 Arbeitskopien")
    (cert,) = vs.waehle([_befund("0.7.16 origin-tls", repo="risk-hub")], {})
    assert "risk-hub" in cert["frage"]


def test_should_say_ein_when_the_note_has_no_number():
    (frage,) = vs.waehle([_befund("0.7.23 melder-register", note="ohne Zahl")], {})
    assert frage["frage"].startswith("Ein Melder")


def test_should_render_text_with_thumb_hint_and_nothing_when_empty():
    text = vs.als_text(vs.waehle([_befund("0.5.2 schleuse")], {}))
    assert "Eine Sache" in text
    assert "Daumen hoch" in text and "Schweigen heisst nein" in text
    assert vs.als_text([]) == ""


def test_should_remember_asked_findings(tmp_path):
    datei = tmp_path / "gefragt.json"
    vs.gefragt_merken(["a::platform", "b::platform"], "2026-09-22", datei)
    vs.gefragt_merken(["b::platform", "c::platform"], "2026-09-23", datei)
    daten = vs.gefragt_lesen(datei)
    assert daten == {
        "a::platform": "2026-09-22",
        "b::platform": "2026-09-22",  # bleibt beim ersten Datum
        "c::platform": "2026-09-23",
    }


def test_should_survive_a_broken_memory_file(tmp_path):
    datei = tmp_path / "kaputt.json"
    datei.write_text("{kein json", encoding="utf-8")
    assert vs.gefragt_lesen(datei) == {}


def test_should_print_status_over_the_command_line(tmp_path):
    datei = tmp_path / "gefragt.json"
    vs.gefragt_merken(["x::platform"], "2026-09-22", datei)
    lauf = subprocess.run(
        [sys.executable, str(SKRIPT), "--status"],
        capture_output=True,
        text=True,
        timeout=30,
        env={
            "LOTSE_VORSCHLAEGE_DATEI": str(datei),
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
        },
    )
    assert lauf.returncode == 0
    assert json.loads(lauf.stdout) == {"x::platform": "2026-09-22"}


# ── #3394: Ausgabe dieses Netzes einmal durch das andere schicken ──────────
#
# Das zweite Netz ist `gesperrt_wegen()` in iilgmbh/chat-hub
# `deploy/lotse_auftrag.py` (Stand 25e9b2b). Es sperrt den Daumen-Weg fuer
# jeden Entwurf, der nach Aussenwirkung klingt. Ein Vorschlagstext, der die
# Sperre ausloest, macht die eigene Frage unbeantwortbar — der Fehler liegt
# dann in der Formulierung, nicht in der Sperre. Die Staemme sind hier
# gespiegelt, weil chat-hub in dieser CI nicht ausgecheckt ist; der
# Drift-Test darunter vergleicht mit dem Nachbar-Klon, wo er existiert.
_SPERR_STAEMME = (
    "deploy",
    "prod",
    "publish",
    "veroeffentlich",
    "pypi",
    "release",
    "merg",
    "loesch",
    "delete",
    "drop",
    "rotat",
    "secret",
    "token",
    "passwor",
    "zugangsdat",
    "schluessel",
    "ruleset",
    "permission",
    "berechtigung",
)
_SPERR_GANZ = ("tag", "tags")
_SPERRE = re.compile(
    "|".join(
        [rf"\w*{s}\w*" for s in _SPERR_STAEMME] + [rf"\b{w}\b" for w in _SPERR_GANZ]
    ),
    re.IGNORECASE,
)
_FALTUNG = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
# Ueber $GITHUB_DIR statt relativ zur Testdatei: aus einem repo-session-Worktree
# liegt chat-hub nicht neben dem platform-Klon, der Test waere dort immer SKIP.
_CHAT_HUB = (
    Path(os.environ.get("GITHUB_DIR") or Path.home() / "github")
    / "chat-hub"
    / "deploy"
    / "lotse_auftrag.py"
)


def _gesperrt(text: str) -> str | None:
    treffer = _SPERRE.search(text.lower().translate(_FALTUNG))
    return treffer.group(0) if treffer else None


def test_should_detect_blocked_word_with_mirrored_check():
    """Positivkontrolle: die gespiegelte Sperre faengt den Anlassfall von #3394."""
    assert _gesperrt("Worktrees auf origin/main mergen") == "mergen"


def test_should_phrase_every_allowed_proposal_without_blocked_words():
    for phase, (frage, tat) in vs.ERLAUBT.items():
        for text in (frage, tat):
            assert _gesperrt(text) is None, f"{phase}: {text!r}"


def test_should_render_morning_text_without_blocked_words():
    befunde = [_befund(p, laeufe=9 - i) for i, p in enumerate(vs.ERLAUBT)]
    text = vs.als_text(vs.waehle(befunde, {}, max_fragen=len(vs.ERLAUBT)))
    assert text
    assert _gesperrt(text) is None, text


@pytest.mark.skipif(
    not _CHAT_HUB.exists(), reason="chat-hub nicht als Nachbar-Klon vorhanden"
)
def test_should_mirror_chat_hub_block_list():
    """Drift-Wache: gespiegelte Staemme == chat-hub `_STAEMME`/`_GANZE_WOERTER`."""
    spec = importlib.util.spec_from_file_location("lotse_auftrag", _CHAT_HUB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert tuple(mod._STAEMME) == _SPERR_STAEMME
    assert tuple(mod._GANZE_WOERTER) == _SPERR_GANZ
