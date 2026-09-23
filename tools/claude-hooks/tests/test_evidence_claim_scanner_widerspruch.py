"""Drill + Positivkontrolle fuer Rev 10 des Gates `claim-before-cheapest-check`.

Realfall: Retro `session-retro-2026-09-22-platform-8946e8.md` Befund #14 —
chat-hub#127 wurde mit „Damit ist auch UDP 7882 belegt" geschlossen, waehrend §8
desselben Berichts genau diesen Punkt als nicht verifizierbar fuehrte.

Der Fall ist deshalb besonders: der Traeger war gedeckt (`gh issue close` steht
seit Rev 5 im Carrier) und der Turn war VOLL von Belegen. Es fehlte kein Beleg —
einer sagte das Gegenteil. Der erste Test misst genau das und steht bewusst an
erster Stelle: faellt er spaeter weg, weil eine andere Art den Fall deckt, soll
das auffallen.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence_claim_scanner import (  # noqa: E402
    _widerspruch_im_zug,
)

REALFALL_BODY = (
    "Der Port ist am Host gegengeprueft. Damit ist auch UDP 7882 belegt. "
    "Das Issue kann geschlossen werden."
)
REALFALL_BERICHT = (
    "## 8. Nicht verifiziert (Restluecken)\n"
    "- Nicht verifizierbar: ob UDP 7882 tatsaechlich durchgereicht wird "
    "(billigster Check: ein Paket von aussen)."
)


# --- Die Messung, aus der Rev 10 folgt --------------------------------------


def test_should_fire_on_the_chat_hub_127_case():
    beleg = _widerspruch_im_zug([REALFALL_BODY], REALFALL_BERICHT)
    assert beleg, "Rev 10 muss den namensgebenden Realfall fangen"
    assert "7882" in beleg or "UDP" in beleg


# --- Drill ------------------------------------------------------------------


def test_should_fire_when_the_shared_marker_is_a_number():
    body = "Damit ist Run 29425428695 belegt."
    text = "Nicht verifizierbar: Run 29425428695 wurde nie gelesen."
    assert _widerspruch_im_zug([body], text)


def test_should_fire_when_two_long_words_are_shared():
    body = "Die Rangfusion ist damit verifiziert, die Trefferquote steht."
    text = "Offen geblieben: Rangfusion und Trefferquote hat kein Pruefer nachgerechnet."
    assert _widerspruch_im_zug([body], text)


# --- Positivkontrolle: was still bleiben MUSS -------------------------------


def test_should_stay_silent_when_subjects_differ():
    # Die ehrliche Normalform: etwas ist belegt, etwas anderes ist offen. Ein
    # Gate, das hier feuert, feuert in jedem zweiten Bericht.
    body = "Damit ist der Melder MELD 4711 belegt."
    text = "Nicht verifizierbar: ob die 20 Eintraege neu eingebettet wurden."
    assert not _widerspruch_im_zug([body], text)


def test_should_stay_silent_on_a_single_shared_long_word():
    # Eine einzige Wortueberschneidung reicht nicht — sonst genuegt ein
    # gemeinsames Fachwort wie „Einbettung" fuer einen Fehlalarm.
    body = "Damit ist die Einbettung verifiziert."
    text = "Nicht verifizierbar: wie schnell die Einbettung auf dem Host laeuft."
    assert not _widerspruch_im_zug([body], text)


def test_should_stay_silent_without_any_negation():
    body = "Damit ist auch UDP 7882 belegt."
    assert not _widerspruch_im_zug([body], "Alles gemessen, nichts offen.")


def test_should_stay_silent_without_any_claim():
    assert not _widerspruch_im_zug(
        ["Das Issue bleibt offen."], REALFALL_BERICHT
    )


def test_should_stay_silent_on_empty_input():
    assert not _widerspruch_im_zug([], REALFALL_BERICHT)
    assert not _widerspruch_im_zug([REALFALL_BODY], "")


def test_should_not_raise_on_odd_input():
    # Der Scanner darf nie werfen — ein Hook, der den Zug mit einem Traceback
    # beendet, wird abgeschaltet.
    assert not _widerspruch_im_zug([None], REALFALL_BERICHT)  # type: ignore[list-item]
