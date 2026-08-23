"""Markdown-Auszeichnung entfernen, damit Muster wieder auf Saetze treffen.

Eigenes Modul, weil zwei Gates dieselbe Normalisierung brauchen und eine Kopie
in beiden genau die Drift erzeugt, die `shared-constant-duplicated-across-tools`
beschreibt.

Der Anlass ist gemessen (2026-08-23, PR platform#2007): der reale Wortlaut einer
aufgeschobenen Arbeit war ``bewusst **nicht** mitgemacht``. Beide Muster-Scanner
des Hauses erwarten ``bewusst nicht`` und sehen daran vorbei — die vier Sternchen
stehen mitten im Satz. Nach dieser Normalisierung treffen beide.

Bewusst klein gehalten: nur Betonung, Inline-Code und Link-Syntax. Kein
Markdown-Parser — die Aufgabe ist, einen Satz wieder lesbar zu machen, nicht
HTML zu erzeugen. Die Zeilenstruktur bleibt erhalten, wenn zeilenweise
aufgerufen wird (``normalisiere_zeilen``); zeilenuebergreifende Betonung loest
nur der Aufruf auf dem ganzen Text.
"""

from __future__ import annotations

import re

_INLINE_CODE = re.compile(r"`{1,3}([^`]*)`{1,3}")
_BETONUNG = re.compile(r"(\*{1,3}|_{1,3})(?=\S)(.+?)(?<=\S)\1", re.S)
_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


def normalisiere(text: str) -> str:
    """Auszeichnung entfernen; Link-Ziele bleiben als Klartext in Klammern stehen.

    Die Ziel-URL wird gebraucht: eine Anker-Pruefung muss ``/issues/`` von
    ``/pull/`` unterscheiden koennen, und beides steht nur im Ziel.
    """
    text = _INLINE_CODE.sub(r"\1", text)
    text = _LINK.sub(r"\1 (\2)", text)
    # Zweimal, damit verschachtelte Auszeichnung (``**_x_**``) in Schichten faellt.
    for _ in range(2):
        text = _BETONUNG.sub(r"\2", text)
    return text


def normalisiere_zeilen(text: str) -> str:
    """Wie ``normalisiere``, aber garantiert zeilentreu.

    Fuer zeilenbasierte Werkzeuge (Fundstellen mit Zeilennummer): eine
    zeilenuebergreifende Betonung darf dort nichts verschieben.
    """
    return "\n".join(normalisiere(z) for z in text.splitlines())
