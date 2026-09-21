"""Drill fuer tools/schliess_bezug_check.py (platform#3226).

Der teuerste Fall steht in `test_should_not_flag_a_closed_issue_cited_as_evidence`:
Ein Melder, der verlangt, geschlossene Vorgaenge zu schliessen, ist eine Plage —
und eine Plage schaltet man ab. Realfall am Tag des Baus: platform#3332 zitierte
drei CLOSED-Nummern als Beleg in einer Tabelle.

Der zweitteuerste ist `test_should_flag_german_closing_word`: Deutsch wirkt bei
GitHub nicht. Das kostete #3333 vier Stunden unnoetige Offenheit, obwohl der Fix
gemergt war.

Kein Netz: `offene_nummern` ist die einzige Funktion mit Aussenkontakt und wird
ersetzt, wo sie stoert.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import schliess_bezug_check as sb  # noqa: E402


# ── Was geschlossen wird, gilt ──────────────────────────────────────────────


@pytest.mark.parametrize("wort", ["Closes", "closes", "Fixes", "fixed", "Resolves"])
def test_should_accept_every_github_closing_keyword(wort: str) -> None:
    e = sb.pruefe(f"{wort} #42")

    assert e["schliesst"] == [42]
    assert e["unbegleitet"] == []


def test_should_flag_german_closing_word() -> None:
    """„Schliesst #N" bewirkt bei GitHub nichts — genau das kostete #3333."""
    e = sb.pruefe("Schließt #3333.")

    assert e["schliesst"] == []
    assert e["unbegleitet"] == [3333]


def test_should_flag_bare_number() -> None:
    """53 % der gemergten PRs nannten die Nummer nackt — der Hauptfall."""
    e = sb.pruefe("Setzt den Melder um, siehe #3337.")

    assert e["unbegleitet"] == [3337]


# ── Was offen bleiben darf, braucht einen Grund ─────────────────────────────


def test_should_accept_refs_with_a_reason_in_the_same_line() -> None:
    e = sb.pruefe("Refs #3337 — Teil von; der Rest haengt an der Datenlage.")

    assert e["begruendet"] == [3337]
    assert e["unbegleitet"] == []


def test_should_flag_refs_without_any_reason() -> None:
    """Nacktes `Refs` ist keine Begruendung, sondern eine Abkuerzung."""
    e = sb.pruefe("Refs #3337")

    assert e["unbegleitet"] == [3337]


def test_should_not_let_one_reason_excuse_every_other_number() -> None:
    """Der Satz um die Nummer entscheidet, nicht das ganze Dokument.

    Sonst entschuldigt ein einziges „bleibt offen" jede weitere Erwaehnung —
    und der Melder waere durch Beifuegen eines Satzes abschaltbar.
    """
    e = sb.pruefe("Refs #100 — bleibt offen, Rest folgt.\nAusserdem betrifft es #200.")

    assert e["begruendet"] == [100]
    assert e["unbegleitet"] == [200]


# ── Was keine Absicht ist, zaehlt nicht ─────────────────────────────────────


def test_should_ignore_numbers_inside_code_blocks() -> None:
    """Im Codeblock stehen Beispiele, keine Absichtserklaerungen."""
    e = sb.pruefe("Beispielaufruf:\n\n```\ngh issue view 5 # siehe #999\n```\n")

    assert e["unbegleitet"] == []


def test_should_ignore_numbers_inside_html_comments() -> None:
    """Die Vorlage selbst traegt `Closes #<!-- N -->` als Kommentar."""
    e = sb.pruefe("<!-- Beispiel: Refs #123 -->\n\nEchter Text ohne Bezug.")

    assert e["unbegleitet"] == []


def test_should_ignore_numbers_that_are_part_of_a_url() -> None:
    """Ein Link auf einen fremden Vorgang ist ein Beleg, keine Zusage."""
    e = sb.pruefe("Beleg: https://github.com/achimdehnert/platform/issues/2054")

    assert e["unbegleitet"] == []


# ── Zustandsfilter ──────────────────────────────────────────────────────────


def test_should_not_flag_a_closed_issue_cited_as_evidence(monkeypatch) -> None:
    """Geschlossenes kann man nicht schliessen — die Forderung waere sinnlos.

    Realfall platform#3332: drei CLOSED-Nummern als Beleg in einer Tabelle.
    """
    monkeypatch.setattr(sb, "offene_nummern", lambda nummern, repo: set())

    e = sb.pruefe("Beide Zeilen zeigen auf #1904 und #2380.", zustand_pruefen=True)

    assert e["unbegleitet"] == []
    assert e["bereits_geschlossen"] == [1904, 2380]


def test_should_keep_flagging_the_open_ones_when_mixed(monkeypatch) -> None:
    monkeypatch.setattr(sb, "offene_nummern", lambda nummern, repo: {3337})

    e = sb.pruefe("Betrifft #1904 und #3337.", zustand_pruefen=True)

    assert e["unbegleitet"] == [3337]
    assert e["bereits_geschlossen"] == [1904]


def test_should_assume_open_when_state_cannot_be_determined(monkeypatch) -> None:
    """Bei Netzfehlern lieber fragen als schweigen.

    Ein Melder, der genau dann verstummt, wenn er nichts weiss, meldet
    irgendwann gar nichts mehr — und niemand merkt es.
    """

    def kaputt(nummern, repo):
        raise OSError("kein Netz")

    monkeypatch.setattr(sb, "offene_nummern", kaputt)

    with pytest.raises(OSError):
        sb.pruefe("Betrifft #3337.", zustand_pruefen=True)


# ── Rueckgabewert ───────────────────────────────────────────────────────────


def test_should_exit_nonzero_only_when_something_is_unaccompanied(tmp_path) -> None:
    gut = tmp_path / "gut.md"
    gut.write_text("Closes #1", encoding="utf-8")
    schlecht = tmp_path / "schlecht.md"
    schlecht.write_text("Betrifft #1", encoding="utf-8")

    assert sb.main(["--text-datei", str(gut), "--kurz", "--ohne-zustand"]) == 0
    assert sb.main(["--text-datei", str(schlecht), "--kurz", "--ohne-zustand"]) == 1
