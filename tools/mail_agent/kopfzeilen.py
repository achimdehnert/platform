"""Kopfzeilen fuer ausgehende Mails — eine Stelle fuer draft_mail und send_mail.

Warum es das gibt: ``EmailMessage()`` faltet jede Kopfzeile bei 78 Zeichen. Passt
ein einzelnes Wort nicht in die Zeile, kodiert die Standardbibliothek es als
MIME-Encoded-Word (``=?utf-8?q?...?=``). Eine Message-ID von Outlook/Exchange hat
leicht ueber 80 Zeichen — ``In-Reply-To`` und ``References`` kamen dann kodiert
heraus. RFC 2047 §5 verbietet Encoded-Words in einer msg-id; ein Client, der die
Kennung woertlich vergleicht, haengt die Antwort an keinen Strang. Gefunden am
2026-09-16 an einem Entwurf an einen Exchange-Absender.

Die Regel hier: diese zwei Felder werden **nie** kodiert und nur zwischen zwei
Kennungen umbrochen. Eine einzelne Kennung bleibt ganz auf ihrer Zeile — das ist
bis 998 Zeichen zulaessig (RFC 5322 §2.1.1). Alle anderen Kopfzeilen falten und
kodieren wie bisher; ein langer Betreff mit Umlauten bleibt RFC-2047-konform.
"""

from __future__ import annotations

from email import headerregistry, policy
from email.message import EmailMessage

#: Kopfzeilen, deren Inhalt eine Liste von msg-ids ist (RFC 5322 §3.6.4).
MSG_ID_LISTEN = ("in-reply-to", "references")


class MsgIdListeHeader(headerregistry.UnstructuredHeader):
    """Liste von msg-ids: faltet nur zwischen Kennungen, kodiert nie."""

    def fold(self, *, policy):  # noqa: D102 — Signatur der Standardbibliothek
        kopf = f"{self.name}:"
        zeilen: list[str] = []
        aktuell = kopf
        for kennung in str(self).split():
            passt = len(aktuell) + 1 + len(kennung) <= (policy.max_line_length or 998)
            if aktuell == kopf or passt:
                aktuell += " " + kennung
            else:
                zeilen.append(aktuell)
                aktuell = " " + kennung
        zeilen.append(aktuell)
        return policy.linesep.join(zeilen) + policy.linesep


def _registry() -> headerregistry.HeaderRegistry:
    registry = headerregistry.HeaderRegistry()
    for name in MSG_ID_LISTEN:
        registry.map_to_type(name, MsgIdListeHeader)
    return registry


#: Richtlinie fuer alle Mails, die wir bauen.
NACHRICHT_POLICY = policy.default.clone(header_factory=_registry())


def neue_nachricht() -> EmailMessage:
    """Leere Nachricht mit der Richtlinie oben — statt ``EmailMessage()``."""
    return EmailMessage(policy=NACHRICHT_POLICY)
