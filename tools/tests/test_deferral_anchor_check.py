"""Tests fuer den Aufschub-Anker-Check.

Die teure Fehlrichtung ist hier der Fehlalarm: ein Gate, das bei jedem "offen"
im Fliesstext feuert, wird nach zwei PRs umgangen statt befolgt. Deshalb pruefen
die Faelle unten in beide Richtungen — die Aufschub-Wendung MUSS greifen, und
harmloser Text darf es NICHT.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "deferral_anchor_check.py"
_spec = importlib.util.spec_from_file_location("deferral_anchor_check", _SRC)
dac = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = dac
_spec.loader.exec_module(dac)


def stellen(text: str):
    return dac.finde_ankerlose_stellen(text)


# --- greift die Erkennung? ---------------------------------------------------


@pytest.mark.parametrize(
    "wendung",
    [
        "Nicht enthalten: die Verdrahtung als Hook.",
        "Das ist bewusst nicht Teil dieses PR.",
        "Die Namensangleichung folgt separat.",
        "Der Rest bleibt offen.",
        "Das entscheidet der Owner separat.",
        "Bekannte Restschuld: die Kopien koennen abdriften.",
    ],
)
def test_should_flag_a_deferral_without_an_anchor(wendung):
    assert len(stellen(f"Titel\n\n{wendung}\n")) == 1


def test_should_accept_a_deferral_with_an_issue_reference_nearby():
    text = "Nicht enthalten: die Verdrahtung.\n\nGetrackt in #1618.\n"

    assert stellen(text) == []


def test_should_accept_an_anchor_that_precedes_the_deferral():
    text = "Refs #1618\n\nDer Rest bleibt offen.\n"

    assert stellen(text) == []


def test_should_accept_a_full_issue_url_as_anchor():
    text = (
        "Bewusst nicht enthalten.\nhttps://github.com/achimdehnert/platform/issues/7\n"
    )

    assert stellen(text) == []


def test_should_flag_when_the_anchor_is_too_far_away():
    text = "Nicht enthalten: X.\n" + "\n".join(["Fuellzeile"] * 8) + "\nRefs #1\n"

    assert len(stellen(text)) == 1


# --- Fehlalarme: der eigentliche Testgegenstand -----------------------------


@pytest.mark.parametrize(
    "harmlos",
    [
        "Der Dialog ist jetzt offen gestaltet.",
        "Wir haben die Datei geoeffnet und geprueft.",
        "Die Schnittstelle ist offengelegt.",
        "Alles erledigt, nichts steht aus.",
    ],
)
def test_should_not_flag_harmless_prose(harmlos):
    assert stellen(f"Titel\n\n{harmlos}\n") == []


def test_should_not_flag_an_empty_body():
    assert stellen("") == []


def test_should_report_every_unanchored_spot_separately():
    text = "Nicht enthalten: A.\n\nZwischentext.\n\nBewusst ausgelassen: B.\n"

    assert len(stellen(text)) == 2


def test_should_report_the_line_number_of_the_finding():
    text = "Titel\n\nBewusst ausgelassen: X.\n"

    nr, zeile = stellen(text)[0]
    assert nr == 3
    assert "Bewusst ausgelassen" in zeile


def test_should_widen_the_window_on_request():
    text = "Nicht enthalten: X.\n" + "\n".join(["Fuell"] * 6) + "\nRefs #1\n"

    assert len(dac.finde_ankerlose_stellen(text, fenster=10)) == 0


# --- main() ------------------------------------------------------------------


def test_should_exit_0_for_a_clean_body(tmp_path, capsys):
    p = tmp_path / "body.md"
    p.write_text("Alles erledigt.\n", encoding="utf-8")

    assert dac.main([str(p), "--block"]) == 0
    assert "✅" in capsys.readouterr().out


def test_should_exit_1_only_in_block_mode(tmp_path):
    p = tmp_path / "body.md"
    p.write_text("Nicht enthalten: die Verdrahtung.\n", encoding="utf-8")

    assert dac.main([str(p)]) == 0
    assert dac.main([str(p), "--block"]) == 1


def test_should_exit_2_for_an_unreadable_file(tmp_path):
    assert dac.main([str(tmp_path / "gibtsnicht.md"), "--block"]) == 2


def test_should_read_from_stdin_without_a_file(monkeypatch, capsys):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO("Bewusst ausgelassen: X.\n"))

    assert dac.main(["--block"]) == 1
    assert "ohne Anker" in capsys.readouterr().out


# --- Ueberschriften-Fenster (Live-Fehlalarm auf PR #1897) --------------------


def test_should_ueberschrift_mit_anker_im_abschnitt_nicht_melden():
    """Der erste echte Fehlalarm des Gates, als Test festgehalten.

    "## Bewusst nicht in diesem PR" ist eine ABSCHNITTS-Ankuendigung; der Anker
    steht bei den Punkten darunter. Mit dem engen +-4-Fenster lag `#1650` knapp
    ausserhalb und das Gate meldete einen Fund auf seinem eigenen PR.
    """
    text = "\n".join(
        [
            "## Bewusst nicht in diesem PR",
            "",
            "- Der eine Punkt braucht noch einen GATE_HEADER und einen Drill,",
            "  das ist hier nicht drin.",
            "  Weitere Zeile ohne Anker.",
            "  Und noch eine, damit der Anker jenseits von +4 liegt; getrackt in #1650.",
        ]
    )
    assert stellen(text) == []


def test_should_ueberschrift_ohne_anker_im_abschnitt_melden():
    """Gegenprobe: das groessere Fenster darf das Gate nicht zahnlos machen."""
    text = "\n".join(
        [
            "## Bewusst nicht in diesem PR",
            "",
            "- Der Rest folgt separat, irgendwann.",
            "- Niemand nennt hier ein Issue.",
        ]
    )
    assert [z for z, _ in stellen(text)] == [1, 3]


def test_should_anker_hinter_naechster_ueberschrift_nicht_einsammeln():
    """Das Abschnitts-Fenster endet an der naechsten Ueberschrift.

    Sonst wuerde ein Anker aus einem voellig anderen Abschnitt den Fund
    stillstellen — das Gate waere ueber lange PR-Texte praktisch blind.
    """
    text = "\n".join(
        [
            "## Bewusst nicht in diesem PR",
            "",
            "- Kein Anker in diesem Abschnitt.",
            "",
            "## Ganz anderes Thema",
            "",
            "Hier steht #1650, gehoert aber nicht dazu.",
        ]
    )
    assert [z for z, _ in stellen(text)] == [1]


# ── Fehlermodus „Auszeichnung" (2026-08-23, platform#2211) ───────────────────


def test_should_aufschub_trotz_fettschrift_im_wortlaut_finden():
    """Der reale Rueckfall aus PR #2007 — vorher unsichtbar.

    `bewusst **nicht** mitgemacht`: die vier Sternchen stehen zwischen den
    beiden Woertern, auf die `AUFSCHUB` wartet. Vor der Normalisierung meldete
    das Gate auf dem echten PR-Text `✅ jede angekuendigte Auslassung hat eine
    Issue-Referenz` — auf genau dem Text, den Retro 9d861a als Befund #3 fuehrt.
    """
    text = (
        "## Bewusste Restueberschneidung\n\n"
        "Eine Zusammenlegung waere ein eigener Umbau und ist hier bewusst "
        "**nicht** mitgemacht.\n"
    )
    funde = dac.finde_ankerlose_stellen(text)
    assert funde, "Aufschub mit Fettschrift wurde nicht gefunden"


def test_should_ohne_normalisierung_blind_gewesen_sein():
    """Gegenprobe: derselbe Satz, roh gematcht, trifft nicht.

    Ohne diesen Test waere „die Fettschrift war die Ursache" eine Behauptung
    ueber den eigenen Fix statt eine Messung.
    """
    roh = "ist hier bewusst **nicht** mitgemacht"
    assert dac.AUFSCHUB.search(roh) is None
    assert dac.AUFSCHUB.search(roh.replace("**", "")) is not None


def test_should_pr_referenz_nicht_mehr_als_anker_gelten_lassen():
    """`#2005` als /pull/-Link belegt Herkunft, nicht Zustaendigkeit."""
    text = (
        "Zwei Gedaechtnisse, aus [#2005](https://github.com/a/b/pull/2005) — "
        "eine Zusammenlegung ist hier bewusst **nicht** mitgemacht.\n"
    )
    assert dac.finde_ankerlose_stellen(text), "PR-Link darf keinen Fund abraeumen"


def test_should_die_grenze_der_naehe_festhalten():
    """**Bekannte Grenze, absichtlich als Test festgehalten.**

    Eine fremde Issue-Nummer im Naehe-Fenster raeumt den Fund ab, auch wenn sie
    mit der aufgeschobenen Arbeit nichts zu tun hat. Am Realfall gemessen: im
    PR-Text von #2007 ist es `#1953` aus einer Beleg-Aufzaehlung vier Zeilen
    darueber — die Stelle bleibt fuer dieses Gate unsichtbar, auch nach
    Normalisierung und PR-Ausschluss.

    Genau deshalb prueft `tools/verankerung_pruefer.py` den Anker **im Segment**
    statt in einem Zeilenfenster. Dieser Test faellt, sobald jemand die Naehe
    doch enger zieht — dann gehoert die Grenze neu bewertet, nicht der Test
    stillschweigend angepasst.
    """
    text = (
        "- Die 8 Befunde decken sich mit Phase 0.7.4 (u.a. #1953).\n"
        "\n"
        "## Bewusste Restueberschneidung\n"
        "\n"
        "Eine Zusammenlegung ist hier bewusst **nicht** mitgemacht.\n"
    )
    assert dac.finde_ankerlose_stellen(text) == []


# ── Ausweitung 2026-08-29: Vertagung im Code, und der fehlende Wortschatz ──
#
# Anlass ist ein gemessener Rueckfall, kein Gedankenspiel. `gate_wirkung.py`
# fuehrte `deferred-item-no-tracking-issue` als RUECKFAELLIG (24 Vorkommen vor
# dem Gate-Bau, 6 danach). Der konkrete Fall: writing-hub#851, Datei
# `apps/core/langlauf.py`. Die Vertagung stand woertlich als
#
#     »`FigurenVertiefenLauf` bleibt vorerst eigenstaendig — Owner-Konvention
#      2026-08-28: nachziehen nur, wenn wir es ohnehin anfassen.«
#
# Zwei Dinge waren daran neu, und die Reihenfolge der Erkenntnis zaehlt:
#
# 1. Der Satz stand in einem **Docstring im Code**, nicht im PR-Text. Ein
#    PR-Text-Scanner kann ihn per Konstruktion nicht sehen.
# 2. Wichtiger: er haette auch dann NICHT gefeuert, wenn man ihn dem Gate
#    direkt eingespeist haette — **kein einziges** Wort der Positivliste kam
#    darin vor. Das wurde vor dem Bau gemessen; die naheliegende Fix-Idee
#    (»das Gate muss auch Docstrings lesen«) waere allein wirkungslos geblieben.

DER_REALE_SATZ = (
    "Gemeinsame Basis fuer lange Laeufe.\n"
    "\n"
    "`FigurenVertiefenLauf` bleibt vorerst eigenstaendig — Owner-Konvention\n"
    "2026-08-28: »nachziehen nur, wenn wir es ohnehin anfassen«.\n"
)

DIFF_NEUE_DATEI = """diff --git a/apps/core/langlauf.py b/apps/core/langlauf.py
new file mode 100644
--- /dev/null
+++ b/apps/core/langlauf.py
@@ -0,0 +1,7 @@
+\"\"\"Gemeinsame Basis fuer lange Laeufe mit Fortschritt und Teilergebnis.
+
+`FigurenVertiefenLauf` bleibt vorerst eigenstaendig — Owner-Konvention
+2026-08-28: »nachziehen nur, wenn wir es ohnehin anfassen«.
+\"\"\"
+
+from django.db import models
"""


def test_should_catch_the_wording_that_slipped_through():
    """Positivkontrolle am echten Rueckfall — vorher lieferte dieser Satz null Funde."""
    from tools.deferral_anchor_check import finde_ankerlose_stellen

    funde = finde_ankerlose_stellen(DER_REALE_SATZ)
    assert funde, "Der Satz, der das Gate ueberlistet hat, faellt immer noch durch"


def test_should_read_added_docstring_lines_from_a_diff():
    """Eine Vertagung im Code zaehlt so wenig als Tracking wie eine im PR-Text."""
    from tools.deferral_anchor_check import finde_ankerlose_stellen, prosa_aus_diff

    prosa = prosa_aus_diff(DIFF_NEUE_DATEI)
    assert "bleibt vorerst eigenstaendig" in prosa, "Der Docstring wurde nicht aus dem Diff gelesen"
    assert finde_ankerlose_stellen(prosa), "Die Vertagung im Code bleibt unbemerkt"


def test_should_accept_an_anchor_inside_the_code_comment():
    """Wer das Issue im Docstring nennt, hat getrackt — das Gate muss schweigen."""
    from tools.deferral_anchor_check import finde_ankerlose_stellen, prosa_aus_diff

    mit_anker = DIFF_NEUE_DATEI.replace("anfassen«.", "anfassen«. Refs #851")
    assert not finde_ankerlose_stellen(prosa_aus_diff(mit_anker))


def test_should_not_fire_on_ordinary_code():
    """Negativkontrolle: ohne Vertagung kein Fund — sonst wird das Gate umgangen."""
    from tools.deferral_anchor_check import finde_ankerlose_stellen, prosa_aus_diff

    harmlos = (
        "--- /dev/null\n"
        "+++ b/apps/core/klein.py\n"
        "@@ -0,0 +1,3 @@\n"
        '+"""Eine ganz normale Hilfsfunktion ohne jede Vertagung."""\n'
        "+# Das hier rechnet nur.\n"
        "+def f(): return 1\n"
    )
    assert not finde_ankerlose_stellen(prosa_aus_diff(harmlos))


def test_should_ignore_removed_lines_and_foreign_file_types():
    """Nur HINZUGEFUEGTE Zeilen aus Quelldateien zaehlen.

    Eine geloeschte Vertagung ist erledigt, keine offene; und eine Textdatei
    ohne Code-Endung ist der PR-Text-Pfad, nicht dieser.
    """
    from tools.deferral_anchor_check import prosa_aus_diff

    geloescht = (
        "--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,1 @@\n"
        "-# bleibt vorerst so\n"
        "+# jetzt erledigt\n"
    )
    assert "bleibt vorerst" not in prosa_aus_diff(geloescht)

    fremd = "--- /dev/null\n+++ b/notizen.rst\n@@ -0,0 +1 @@\n+.. bleibt vorerst offen\n"
    assert prosa_aus_diff(fremd) == ""
