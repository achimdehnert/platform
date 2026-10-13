"""Drill für tools/tracking_doc_nachzug.py (Gate tracking-doc-stale-after-new-occurrence).

Fixture: ein Wegwerf-Repo mit einem Konzept und einem ADR. Die Realfälle stehen
im Kopf des Moduls; hier ist jeder Fall nachgebaut, auch die Gegenrichtungen.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tracking_doc_nachzug as tdn  # noqa: E402

KONZ = "docs/konzepte/KONZ-platform-071-raum-rechte.md"
ADR = "docs/adr/ADR-308-sandbox.md"
KONZ_OFFEN = (
    "## 13 Kill-Gate\n\n| Kriterium | Status | Beleg |\n|---|---|---|\n"
    "| (a) Stufe 1 gemergt | offen | — |\n| O1 entschieden | erfüllt | x |\n"
)
ADR_ERLEDIGT = "# ADR-308\n\n| Punkt | Status |\n|---|---|\n| Tests | erfüllt |\n"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _commit(repo: Path, nachricht: str, dateien: dict[str, str] | None = None) -> str:
    for pfad, inhalt in (dateien or {"notiz.txt": nachricht}).items():
        ziel = repo / pfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")
        _git(repo, "add", pfad)
    _git(repo, "commit", "-q", "-m", nachricht)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "platform"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "test@example.invalid")
    _git(r, "config", "user.name", "Test")
    _commit(r, "docs: Grundstand", {KONZ: KONZ_OFFEN, ADR: ADR_ERLEDIGT})
    return r


def _lauf(repo: Path, *argv: str) -> tuple[int, str]:
    import contextlib
    import io

    puffer = io.StringIO()
    with contextlib.redirect_stdout(puffer):
        rc = tdn.main(["--repo", str(repo), *argv])
    return rc, puffer.getvalue()


def test_should_melden_wenn_commit_konzept_erwaehnt_ohne_es_nachzuziehen(repo):
    """Realfall e50644: „Fund aus KONZ-071", §13 bleibt „offen"."""
    sha = _commit(repo, "docs(adr): Nachtrag\n\nFund aus KONZ-071.")
    rc, out = _lauf(repo, "--commit", sha)
    assert rc == 0
    assert "BEFUND KONZ-071" in out
    assert "| (a) Stufe 1 gemergt | offen | — |" in out
    assert "RESULT: BEFUND 1" in out


def test_should_schweigen_wenn_derselbe_commit_das_doc_aendert(repo):
    sha = _commit(
        repo, "docs: KONZ-071 §13 nachgezogen", {KONZ: KONZ_OFFEN + "\nneu\n"}
    )
    rc, out = _lauf(repo, "--commit", sha)
    assert "RESULT: OK" in out


def test_should_schweigen_wenn_ein_spaeterer_commit_das_doc_nachzieht(repo):
    basis = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "feat: baut Stufe 1 (KONZ-platform-071)")
    _commit(
        repo, "docs: §13 nachgezogen", {KONZ: KONZ_OFFEN.replace("offen", "erfüllt")}
    )
    rc, out = _lauf(repo, "--basis", basis, "--kopf", "HEAD")
    assert "RESULT: OK" in out


def test_should_melden_wenn_die_aenderung_vor_der_erwaehnung_lag(repo):
    """Reihenfolge zählt: erst nachgezogen, dann neues Vorkommen ohne Nachzug."""
    basis = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "docs: §13 Tippfehler", {KONZ: KONZ_OFFEN + "\n"})
    _commit(repo, "feat: neues Vorkommen zu KONZ-071")
    rc, out = _lauf(repo, "--basis", basis, "--kopf", "HEAD")
    assert "BEFUND KONZ-071" in out


def test_should_schweigen_wenn_das_erwaehnte_doc_keine_offenen_posten_hat(repo):
    sha = _commit(repo, "fix: ADR-308 umgesetzt")
    rc, out = _lauf(repo, "--commit", sha)
    assert "RESULT: OK" in out


def test_should_unbekannte_doc_nummern_ignorieren(repo):
    sha = _commit(repo, "fix: bezieht sich auf ADR-999 und KONZ-001")
    rc, out = _lauf(repo, "--commit", sha)
    assert "RESULT: OK" in out


def test_should_mit_strict_exit_eins_liefern(repo):
    sha = _commit(repo, "feat: KONZ-071 Stufe 1")
    rc, _ = _lauf(repo, "--commit", sha, "--strict")
    assert rc == 1


def test_should_nicht_lesbaren_ref_als_hinweis_statt_ok_melden(repo):
    rc, out = _lauf(repo, "--seit", "2026-01-01", "--ref", "origin/main")
    assert rc == 0
    assert "RESULT: HINWEIS" in out
    assert "RESULT: OK" not in out


def test_should_kurz_und_langform_der_konzeptnummer_gleich_behandeln():
    assert tdn.doc_ids("KONZ-071 und KONZ-platform-071, ADR-308") == {
        "KONZ-071",
        "ADR-308",
    }


@pytest.mark.parametrize(
    "zeile",
    [
        "| (a) Stufe 1 gemergt | offen | — |",
        "| 1a Rückschau | ⬜ Ausstehend | – |",
        "| Review | steht aus | |",
        "- [ ] Drill nachziehen",
        "**Noch offen vor Phase 3:** Profil-Negativtests",
    ],
)
def test_should_offene_posten_erkennen(zeile):
    assert tdn.offene_zeilen(zeile) == [(1, zeile)]


@pytest.mark.parametrize(
    "zeile",
    [
        "| O1 entschieden | erfüllt | Owner-Wort |",
        "- [x] Drill nachgezogen",
        "Die Tür steht offen für Vorschläge.",
    ],
)
def test_should_erledigte_posten_nicht_melden(zeile):
    assert tdn.offene_zeilen(zeile) == []
