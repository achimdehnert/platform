"""GitHub-Referenzen in Freitext erkennen — und Herkunft von Zustaendigkeit trennen.

Zwei Gates stellen dieselbe Frage („traegt diese Stelle einen Anker?") und
brauchen dieselbe Antwort. Der Unterschied, um den es geht, ist gemessen
(2026-08-23, PR platform#2007, Retro 9d861a Befund #3):

    … befund_journal.py (Runner-WARN-Zeilen, aus [#2005](…/pull/2005)) …
      … eine Zusammenlegung … ist hier bewusst **nicht** mitgemacht.

``#2005`` steht im selben Satz wie die aufgeschobene Arbeit und besteht jeden
Naehe-Test — es zeigt aber auf einen **Pull Request** und belegt eine Herkunft
(„aus #2005"). Verfolgt wird damit nichts. Die Hausregel verlangt ein
Tracking-**Issue**; ein PR ist keines.

``pr_nummern`` loest den Fall ohne jede Rueckfrage bei GitHub, weil die
Markdown-Form die Ziel-URL mitliefert.
"""

from __future__ import annotations

import re

ISSUE_URL = re.compile(r"https?://github\.com/[\w.-]+/[\w.-]+/issues/(\d+)")
PR_URL = re.compile(r"https?://github\.com/[\w.-]+/[\w.-]+/pull/(\d+)")
KURZ_REF = re.compile(r"(?<![\w/])(?:([\w.-]+/[\w.-]+))?#(\d+)\b")


def pr_nummern(text: str) -> set[str]:
    """Nummern, die im Text als ``/pull/N``-Link ausgeschrieben stehen."""
    return set(PR_URL.findall(text))


def ohne_pr_referenzen(text: str) -> str:
    """Text ohne alles, was nachweislich auf einen Pull Request zeigt.

    Gedacht als Vorstufe fuer eine Anker-Suche: was danach noch an Referenzen
    uebrig ist, kann ein Tracking-Issue sein. Was verschwindet, konnte nie eines
    sein. Bewusst konservativ — eine blosse ``#N`` ohne ausgeschriebene URL
    bleibt stehen, weil sie ohne GitHub nicht zu unterscheiden ist.
    """
    nummern = pr_nummern(text)
    text = PR_URL.sub("", text)
    if not nummern:
        return text
    return KURZ_REF.sub(lambda m: "" if m.group(2) in nummern else m.group(0), text)
