"""Drill fuer tools/policy_frische.py — Frische der ausgelieferten Policies.

Der wichtigste Test hier ist der Vergleich am INHALT statt an der mtime: die
ausgelieferten Dateien trugen am 2026-08-23 alle den 3. August und waren trotzdem
aktuell. Ein mtime-Melder haette 16 Fehlalarme erzeugt und waere abgeschaltet
worden — die Fehlrichtung, die einen Melder toetet.

Zweiter Punkt, aus einem eigenen Fehler beim Bauen: `~/.claude/policies/*.md` sind
SYMLINKS in den Pin-Worktree. Eine Probe, die dort anhaengt, veraendert das Original
(passiert am 2026-08-23, zurueckgenommen). Diese Tests bauen deshalb ein echtes
Temp-Repo mit echten Dateien und fassen die Live-Umgebung nicht an.

Run: `python3 -m pytest tools/tests/test_policy_frische.py -q`
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "policy_frische.py"
_spec = importlib.util.spec_from_file_location("policy_frische", _QUELLE)
pf = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(pf)


def _repo_mit_policies(tmp_path: Path, inhalte: dict[str, str]) -> Path:
    """Repo, dessen `origin/main` die genannten Policies traegt."""
    repo = tmp_path / "platform"
    (repo / "policies").mkdir(parents=True)
    for name, text in inhalte.items():
        (repo / "policies" / name).write_text(text, encoding="utf-8")
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["add", "-A"],
        ["commit", "-q", "-m", "policies"],
        # Ein lokaler Zweig `origin/main` genuegt: `git show origin/main:<pfad>`
        # fragt nicht, ob dahinter ein echtes Remote steht.
        ["branch", "-q", "origin/main"],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    return repo


def _ausgeliefert(tmp_path: Path, inhalte: dict[str, str]) -> Path:
    ziel = tmp_path / "policies-live"
    ziel.mkdir()
    for name, text in inhalte.items():
        (ziel / name).write_text(text, encoding="utf-8")
    return ziel


def test_should_report_nothing_when_delivered_matches_main(tmp_path):
    inhalt = {"a.md": "Regel A\n", "b.md": "Regel B\n"}
    repo = _repo_mit_policies(tmp_path, inhalt)
    live = _ausgeliefert(tmp_path, inhalt)
    stand = pf.vergleiche(live, repo)
    assert stand["abweichend"] == []
    assert stand["geprueft"] == 2
    assert pf.bericht(stand, None, kurz=True) == ""


def test_should_detect_a_stale_delivered_policy(tmp_path):
    repo = _repo_mit_policies(tmp_path, {"a.md": "Regel A neu\n"})
    live = _ausgeliefert(tmp_path, {"a.md": "Regel A alt\n"})
    stand = pf.vergleiche(live, repo)
    assert stand["abweichend"] == ["a.md"]
    assert "a.md" in pf.bericht(stand, None, kurz=True)


def test_should_not_judge_by_mtime(tmp_path):
    """Gleicher Inhalt, uraltes Datum — kein Befund. 16 von 16 waren so."""
    inhalt = {"a.md": "Regel A\n"}
    repo = _repo_mit_policies(tmp_path, inhalt)
    live = _ausgeliefert(tmp_path, inhalt)
    import os

    os.utime(live / "a.md", (0, 0))
    assert pf.vergleiche(live, repo)["abweichend"] == []


def test_should_tolerate_a_trailing_newline_difference(tmp_path):
    repo = _repo_mit_policies(tmp_path, {"a.md": "Regel A\n"})
    live = _ausgeliefert(tmp_path, {"a.md": "Regel A"})
    assert pf.vergleiche(live, repo)["abweichend"] == []


def test_should_list_a_policy_that_does_not_exist_in_main_separately(tmp_path):
    """Eine lokale Zusatzdatei ist keine Drift — aber auch keine Entwarnung."""
    repo = _repo_mit_policies(tmp_path, {"a.md": "Regel A\n"})
    live = _ausgeliefert(tmp_path, {"a.md": "Regel A\n", "lokal.md": "nur hier\n"})
    stand = pf.vergleiche(live, repo)
    assert stand["abweichend"] == []
    assert stand["unbekannt"] == ["lokal.md"]


def test_should_name_the_dirty_pin_as_the_cause(tmp_path):
    """Die Meldung soll sagen, was zu tun ist — nicht nur, dass etwas ist."""
    repo = _repo_mit_policies(tmp_path, {"a.md": "neu\n"})
    live = _ausgeliefert(tmp_path, {"a.md": "alt\n"})
    text = pf.bericht(pf.vergleiche(live, repo), True, kurz=True)
    assert "DIRTY" in text and "platform-pinned" in text


def test_should_say_when_the_pin_is_clean_but_delivery_differs(tmp_path):
    """Andere Ursache, andere Empfehlung — nicht dieselbe Zeile fuer beides."""
    repo = _repo_mit_policies(tmp_path, {"a.md": "neu\n"})
    live = _ausgeliefert(tmp_path, {"a.md": "alt\n"})
    text = pf.bericht(pf.vergleiche(live, repo), False, kurz=True)
    assert "clean" in text


def test_should_survive_a_missing_policy_directory(tmp_path):
    repo = _repo_mit_policies(tmp_path, {"a.md": "x\n"})
    stand = pf.vergleiche(tmp_path / "gibtsnicht", repo)
    assert stand["geprueft"] == 0
    assert pf.bericht(stand, None, kurz=True) == ""


def test_should_return_zero_even_when_everything_is_missing(tmp_path):
    assert (
        pf.main(["--policies", str(tmp_path / "x"), "--repo", str(tmp_path / "y")]) == 0
    )
