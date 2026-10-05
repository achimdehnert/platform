"""Drill fuer das Gate `stale-local-clone-as-ground-truth`, Zweig 'fremde Quelle'.

Positivkontrolle und Negativkontrolle in einem: derselbe Hook muss bei einem
zurueckliegenden fremden Klon melden und bei einem aktuellen schweigen. Ein
Drill, der nur die Stille prueft, belegt nichts (Lehre: eine Null ist erst ein
Beleg, wenn dasselbe Verfahren nachweislich auch etwas finden kann).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / "tools/hooks/foreign_clone_check.sh"


def _git(pfad: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(pfad), *args], check=True, capture_output=True, text=True
    )


def _repo_bauen(
    wurzel: Path, name: str, commits_voraus: int, inhalt_voraus: str = "stand"
) -> Path:
    """Legt <wurzel>/<name> als Klon an, dessen origin <commits_voraus> weiter ist."""
    quelle = wurzel / f"{name}.git-quelle"
    quelle.mkdir(parents=True)
    _git(quelle, "init", "--initial-branch=main", "-q")
    _git(quelle, "config", "user.email", "drill@example.invalid")
    _git(quelle, "config", "user.name", "Drill")
    (quelle / "datei.txt").write_text("start\n", encoding="utf-8")
    _git(quelle, "add", "datei.txt")
    _git(quelle, "commit", "-qm", "start")

    klon = wurzel / name
    subprocess.run(
        ["git", "clone", "-q", str(quelle), str(klon)],
        check=True,
        capture_output=True,
        text=True,
    )

    _origin_vorziehen(wurzel, name, commits_voraus, inhalt_voraus)
    return klon


def _origin_vorziehen(
    wurzel: Path, name: str, anzahl: int, inhalt: str = "stand"
) -> None:
    """Zieht den origin von <name> um <anzahl> Commits weiter; der Klon bleibt stehen."""
    quelle = wurzel / f"{name}.git-quelle"
    for i in range(anzahl):
        (quelle / "datei.txt").write_text(f"{inhalt} {i}\n", encoding="utf-8")
        _git(quelle, "add", "datei.txt")
        _git(quelle, "commit", "-qm", f"weiter {i}")


def _hook_laufen(
    wurzel: Path, kommando: str, eigenes_repo: Path, sitzung: str | None = "drill"
) -> str:
    """Ruft den Hook so auf, wie Claude Code es tut.

    Die Sitzungskennung kommt im Ereignis-JSON (`session_id`), NICHT als
    Umgebungsvariable: im echten Hook-Prozess ist CLAUDE_SESSION_ID nicht
    gesetzt. Bis 2026-10-05 setzte dieser Helfer die Variable selbst — der
    Drill lief damit in einer Umgebung, die es in Betrieb nicht gibt, und sah
    den Fehler nicht, an dem der Realfall vom 2026-09-24 scheiterte.
    """
    umgebung = dict(os.environ)
    umgebung.pop("CLAUDE_SESSION_ID", None)
    umgebung["GITHUB_DIR"] = str(wurzel)
    umgebung["CLAUDE_PROJECT_DIR"] = str(eigenes_repo)
    umgebung["TMPDIR"] = str(wurzel / "tmp")
    (wurzel / "tmp").mkdir(exist_ok=True)
    ereignis: dict = {"tool_name": "Bash", "tool_input": {"command": kommando}}
    if sitzung is not None:
        ereignis["session_id"] = sitzung
    ergebnis = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(ereignis),
        capture_output=True,
        text=True,
        env=umgebung,
        timeout=60,
    )
    assert ergebnis.returncode == 0, "Der Hook darf niemals blockieren"
    return ergebnis.stdout


@pytest.mark.parametrize("commits_voraus,soll_melden", [(3, True), (0, False)])
def test_should_melden_wenn_fremder_klon_zurueckliegt(
    tmp_path: Path, commits_voraus: int, soll_melden: bool
) -> None:
    eigenes = _repo_bauen(tmp_path, "eigenes-hub", 0)
    fremdes = _repo_bauen(tmp_path, "fremdes-hub", commits_voraus)

    ausgabe = _hook_laufen(tmp_path, f"cat {fremdes}/datei.txt", eigenes)

    if soll_melden:
        assert "FREMDER KLON VERALTET" in ausgabe
        assert "fremdes-hub" in ausgabe
        assert str(commits_voraus) in ausgabe
    else:
        assert ausgabe.strip() == ""


def test_should_melden_den_namensgebenden_realfall(tmp_path: Path) -> None:
    # Der Realfall selbst (platform#2732), nicht nur eine generische Fixture:
    # frist-hub 3 Commits hinter origin, gelesen aus einer meiki-hub-Sitzung (2026-09-03)
    # — portiert aus einem frist-hub-Klon, Spec/Bildschirme/12 Bilder/Handbuch
    # fehlten, gefunden nur durch Zufall.
    meiki_hub = _repo_bauen(tmp_path, "meiki-hub", 0)
    frist_hub = _repo_bauen(tmp_path, "frist-hub", 3)

    ausgabe = _hook_laufen(tmp_path, f"cat {frist_hub}/datei.txt", meiki_hub)

    assert "FREMDER KLON VERALTET" in ausgabe
    assert "frist-hub" in ausgabe
    assert "3" in ausgabe


def test_should_das_eigene_repo_nicht_melden(tmp_path: Path) -> None:
    """Das Sitzungs-Repo hat seinen eigenen Melder — doppelt waere Laerm."""
    eigenes = _repo_bauen(tmp_path, "eigenes-hub", 5)

    ausgabe = _hook_laufen(tmp_path, f"cat {eigenes}/datei.txt", eigenes)

    assert ausgabe.strip() == ""


def test_should_je_repo_nur_einmal_melden(tmp_path: Path) -> None:
    """Wiederholte Lesezugriffe duerfen nicht wiederholt fetchen und melden."""
    eigenes = _repo_bauen(tmp_path, "eigenes-hub", 0)
    fremdes = _repo_bauen(tmp_path, "fremdes-hub", 2)

    erste = _hook_laufen(tmp_path, f"cat {fremdes}/datei.txt", eigenes)
    zweite = _hook_laufen(tmp_path, f"grep x {fremdes}/datei.txt", eigenes)

    assert "FREMDER KLON VERALTET" in erste
    assert zweite.strip() == ""


# --- Realfall 2026-09-24 (Retro session-retro-2026-09-24-meiki-hub-2a5c44) ---
#
# Retro: "lokale Klone schreib-hub/frist-hub zeigten 0 Treffer fuer
# `verweis_hinzufuegen`, origin/main hatte sie". Zugriffsform laut Transkript
# der Sitzung: EIN Bash-Aufruf aus einer meiki-hub-Sitzung, je Klon
# `sed -n <von>,<bis>p ~/github/<repo>/<datei> | grep -n verweis_hinzufuegen`,
# mit `;` verkettet. Beide Klone hatte der Hook in frueheren Sitzungen schon
# gesehen (frist-hub seit 2026-09-03, schreib-hub seit 2026-09-12). Im echten
# Hook-Prozess fehlt CLAUDE_SESSION_ID — der Merker hiess deshalb fuer jede
# Sitzung gleich, und "einmal pro Sitzung" war "einmal ueberhaupt".
_REALFALL_KOMMANDO = (
    "sed -n 1,5p ~/github/schreib-hub/datei.txt | grep -n verweis_hinzufuegen ; "
    "sed -n 1,5p ~/github/frist-hub/datei.txt | grep -n verweis_hinzufuegen"
)


def _realfall_bauen(tmp_path: Path) -> tuple[Path, Path, Path]:
    heim = tmp_path / "heim"
    wurzel = heim / "github"
    meiki_hub = _repo_bauen(wurzel, "meiki-hub", 0)
    _repo_bauen(wurzel, "schreib-hub", 0)
    _repo_bauen(wurzel, "frist-hub", 0)
    return heim, wurzel, meiki_hub


def test_should_melden_den_realfall_vom_2026_09_24_trotz_frueherer_sitzung(
    tmp_path: Path,
) -> None:
    heim, wurzel, meiki_hub = _realfall_bauen(tmp_path)

    # Eine fruehere Sitzung las beide Klone, als sie noch aktuell waren.
    frueher = _hook_laufen(
        wurzel, _REALFALL_KOMMANDO, meiki_hub, sitzung="sitzung-frueher"
    )
    assert frueher.strip() == ""

    # Danach zieht origin weiter — die gesuchte Stelle gibt es nur dort.
    _origin_vorziehen(wurzel, "schreib-hub", 2, "verweis_hinzufuegen")
    _origin_vorziehen(wurzel, "frist-hub", 3, "verweis_hinzufuegen")

    # Fixture-Kontrolle: die Zugriffsform findet lokal nichts, origin hat die Stelle.
    lokal = subprocess.run(
        ["bash", "-c", _REALFALL_KOMMANDO],
        env={**os.environ, "HOME": str(heim)},
        capture_output=True,
        text=True,
    )
    assert lokal.stdout.strip() == ""
    for name in ("schreib-hub", "frist-hub"):
        quelle = wurzel / f"{name}.git-quelle" / "datei.txt"
        assert "verweis_hinzufuegen" in quelle.read_text(encoding="utf-8")

    ausgabe = _hook_laufen(
        wurzel, _REALFALL_KOMMANDO, meiki_hub, sitzung="sitzung-realfall"
    )

    assert "FREMDER KLON VERALTET: schreib-hub liegt 2 Commit(s)" in ausgabe
    assert "FREMDER KLON VERALTET: frist-hub liegt 3 Commit(s)" in ausgabe


def test_should_klon_auf_stand_von_origin_in_realfall_form_nicht_melden(
    tmp_path: Path,
) -> None:
    """Gegenprobe: dieselbe Zugriffsform, Klone aktuell — der Hook schweigt."""
    _, wurzel, meiki_hub = _realfall_bauen(tmp_path)

    ausgabe = _hook_laufen(
        wurzel, _REALFALL_KOMMANDO, meiki_hub, sitzung="sitzung-aktuell"
    )

    assert ausgabe.strip() == ""


def test_should_bei_fehlgeschlagenem_abruf_hinweisen_statt_blockieren(
    tmp_path: Path,
) -> None:
    """Gegenprobe: kein Netz. Exit 0 (prueft _hook_laufen), ein Hinweis, kein Urteil."""
    _, wurzel, meiki_hub = _realfall_bauen(tmp_path)
    for name in ("schreib-hub", "frist-hub"):
        _git(wurzel / name, "remote", "set-url", "origin", str(tmp_path / "nicht-da"))

    ausgabe = _hook_laufen(
        wurzel, _REALFALL_KOMMANDO, meiki_hub, sitzung="sitzung-offline"
    )

    assert "FREMDER KLON UNGEPRUEFT: schreib-hub" in ausgabe
    assert "FREMDER KLON UNGEPRUEFT: frist-hub" in ausgabe
    assert "VERALTET" not in ausgabe


def test_should_ohne_sitzungskennung_keinen_sitzungsuebergreifenden_merker_fuehren(
    tmp_path: Path,
) -> None:
    """Fehlt die Kennung, prueft der Hook jedes Mal — Stille waere der teurere Fehler."""
    eigenes = _repo_bauen(tmp_path, "eigenes-hub", 0)
    fremdes = _repo_bauen(tmp_path, "fremdes-hub", 2)

    erste = _hook_laufen(tmp_path, f"cat {fremdes}/datei.txt", eigenes, sitzung=None)
    zweite = _hook_laufen(tmp_path, f"cat {fremdes}/datei.txt", eigenes, sitzung=None)

    assert "FREMDER KLON VERALTET" in erste
    assert "FREMDER KLON VERALTET" in zweite
