#!/usr/bin/env python3
"""Schutzklassen vor dem Ordner „Zur Loeschung" (platform#3176 K1/K3).

**Warum es das gibt.** Die Rauschregel `nach_ordner_zur_loeschung` im Ledger ist
eine reine Absenderliste. Am 2026-09-14 lagen dadurch Rechnungen von vier
Anbietern im Löschordner, und unter den bestätigten Kandidaten standen
Einzelpersonen, Partner und die eigene Adresse des Owners. Das Kriterium
„häufig und in keinem Vorgang" trennt Mensch und Maschine nicht.

Dieses Modul ist der eine Ort, an dem feststeht, was NIE in den Löschordner
gehört. Zwei Stellen fragen es:

* ``rausch_kandidaten.py`` (K1) — ein geschützter Absender wird gar nicht erst
  als Regel vorgeschlagen.
* ``graph_mail.py --move`` und ``organize_mail.py --move`` (K3) — vor jedem
  Verschieben in den Löschordner bleibt eine geschützte Mail liegen und wird
  gemeldet. Das ist ein Werkzeug-Schritt, keine Modell-Disziplin: wer den
  Befehl aufruft, kommt an der Prüfung nicht vorbei.

**Die drei Schutzklassen** (Reihenfolge = Reihenfolge der Prüfung):

1. **Eigene Adresse** — die ``from``-Adressen aus der Rollen-Registry
   (``~/.claude/mail-roles.json``, nicht im Repo) und alles unter den eigenen
   Firmen-Domains ``EIGENE_KONTO_DOMAENEN``. Die Hochschul-Domain gehört
   bewusst NICHT dazu: dort schreiben auch System-Absender, die der Owner am
   2026-09-14 ausdrücklich im Löschordner lassen wollte („drin lassen").
2. **Beleg** — Betreff oder Anhangname trifft ``BELEG_MUSTER`` (Rechnung,
   Invoice, Receipt, Gutschrift, Zahlung, Sicherheitscode, …). Ein Beleg
   gehört zur Aufbewahrung, nie zum Rauschen.
3. **Gesendet-Historie** — der Owner hat dieser Adresse je geschrieben (ein
   Treffer mit ``--an <adresse>`` in einem Gesendet-Ordner des Index).

**Fail-closed.** Ist der Index für die Gesendet-Prüfung nicht erreichbar, wirft
`gesendet_an` — der Aufrufer verschiebt dann nichts in den Löschordner. Liegen
lassen ist reversibel und billig; eine Personenmail im Löschordner nicht.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path
from typing import Callable, Iterable

HIER = Path(__file__).resolve().parent

#: Der seit 2026-08-07 einzige Zielordner für Rauschregeln (`rausch_regeln._hinweis`).
ZIELORDNER_LOESCHUNG = "Zur Loeschung"

#: Rollen-Registry mit den echten Absenderadressen (KONZ-platform-033) — liegt
#: personenbezogen außerhalb des Repos, siehe ``mail-roles.example.json``.
ROLLEN_REGISTRY = Path.home() / ".claude" / "mail-roles.json"

#: Domains, unter denen JEDE Adresse eine eigene ist (Firma, Familie).
#: Bereits unredigiert im Repo, siehe ``rausch_kandidaten.EIGENE_DOMAENEN``.
EIGENE_KONTO_DOMAENEN = ("iil.gmbh", "dehnert.team")

#: Beleg-Betreffe und -Anhangnamen (K1/K3). Lieber einmal zu viel liegen lassen:
#: "zahlung" trifft auch "Zahlungserinnerung", "rechnung" auch "Abrechnung".
BELEG_MUSTER = re.compile(
    r"rechnung|invoice|receipt|quittung|\bbeleg|gutschrift|zahlung|payment"
    r"|\bbilling\b|\bbill\b|sicherheitscode|security code|verification code"
    r"|verifizierungscode|bestaetigungscode|bestätigungscode|einmalcode"
    r"|one-time|\btoken\b|\botp\b|\btan\b",
    re.IGNORECASE,
)

#: Ordner-Teilstrings, an denen ein Gesendet-Ordner im Index erkennbar ist
#: (IIL/Graph "Gesendete Elemente", HNU "Gesendete Objekte", AD "Sent").
GESENDET_ORDNER_TEILE = ("esendet", "sent")


@dataclass(frozen=True)
class Befund:
    """Warum eine Mail/ein Absender nicht in den Löschordner darf."""

    klasse: str  # "eigene_adresse" | "beleg" | "gesendet"
    detail: str


def _normalisiert(text: str) -> str:
    """Kleinbuchstaben, Umlaute als Digraph — "Zur Löschung" == "zur_loeschung"."""
    text = unicodedata.normalize("NFC", text or "").casefold()
    for umlaut, ersatz in (("ö", "oe"), ("ä", "ae"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(umlaut, ersatz)
    return text.replace("_", " ")


def ist_loeschordner(pfad: str) -> bool:
    """Trifft den Löschordner in jeder Schreibweise und unter jedem Elternpfad
    (Graph "Zur Loeschung", IMAP "INBOX.Zur Loeschung", "INBOX/Zur Löschung")."""
    letzter = re.split(r"[./\\]", pfad or "")[-1]
    return _normalisiert(letzter).strip() == _normalisiert(ZIELORDNER_LOESCHUNG)


def adresse_von(absender: str) -> str:
    """Nackte Adresse aus "Name <a@b>" oder "a@b", klein geschrieben."""
    return parseaddr(absender or "")[1].strip().lower()


def eigene_adressen(registry: Path | None = None) -> set[str]:
    """``from``-Adressen aller Rollen. Fehlt die Registry, bleibt nur der
    Domain-Schutz — das ist gewollt tolerant, der Aufrufer bricht daran nicht."""
    pfad = registry or ROLLEN_REGISTRY
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    rollen = daten.get("roles") or {}
    return {
        adresse_von(r.get("from") or "")
        for r in rollen.values()
        if isinstance(r, dict) and "@" in (r.get("from") or "")
    }


def ist_eigene_adresse(adresse: str, eigene: set[str]) -> bool:
    if adresse in eigene:
        return True
    domain = adresse.rsplit("@", 1)[-1]
    return any(domain == d or domain.endswith("." + d) for d in EIGENE_KONTO_DOMAENEN)


def ist_beleg(betreff: str, anhaenge: Iterable[str] = ()) -> bool:
    return bool(BELEG_MUSTER.search(betreff or "")) or any(
        BELEG_MUSTER.search(a or "") for a in anhaenge
    )


def index_batch(anfragen: list[dict]) -> list[dict]:
    """Mehrere Index-Abfragen über EINE Verbindung (``suche.py --batch``)."""
    lauf = subprocess.run(
        [sys.executable, str(HIER / "suche.py"), "--batch", "-"],
        input=json.dumps(anfragen, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if lauf.returncode != 0:
        raise RuntimeError(f"Mail-Index nicht erreichbar: {lauf.stderr[:200]}")
    return json.loads(lauf.stdout)


def gesendet_an(
    adressen: Iterable[str],
    abfrage: Callable[[list[dict]], list[dict]] | None = None,
) -> set[str]:
    """Die Adressen, an die der Owner laut Index je geschrieben hat.

    EINE Index-Verbindung für alle Adressen (``suche.py --batch``). Wirft bei
    nicht erreichbarem Index — siehe Modul-Docstring „Fail-closed".
    """
    liste = sorted({a for a in adressen if "@" in a})
    if not liste:
        return set()
    ergebnisse = (abfrage or index_batch)([{"an": a, "limit": 20} for a in liste])
    treffer_je_index = {e.get("index", i): e for i, e in enumerate(ergebnisse)}
    gesendet: set[str] = set()
    for i, adresse in enumerate(liste):
        for t in (treffer_je_index.get(i) or {}).get("treffer") or []:
            ordner = " ".join(t.get("ordner") or []).lower()
            if any(teil in ordner for teil in GESENDET_ORDNER_TEILE):
                gesendet.add(adresse)
                break
    return gesendet


def pruefe(
    absender: str,
    betreff: str,
    *,
    eigene: set[str],
    gesendet: set[str],
    anhaenge: Iterable[str] = (),
) -> Befund | None:
    """Schutz-Befund für eine Mail — ``None`` heißt: darf in den Löschordner."""
    adresse = adresse_von(absender)
    if not adresse:
        return Befund("unbekannt", "Absenderadresse nicht lesbar")
    if ist_eigene_adresse(adresse, eigene):
        return Befund("eigene_adresse", adresse)
    if ist_beleg(betreff, anhaenge):
        return Befund("beleg", (betreff or "")[:60])
    if adresse in gesendet:
        return Befund("gesendet", adresse)
    return None


def filtere_verschiebung(
    ziel: str,
    hits: list[tuple],
    *,
    eigene: set[str] | None = None,
    abfrage: Callable[[list[dict]], list[dict]] | None = None,
) -> tuple[list[tuple], list[tuple[tuple, Befund]]]:
    """K3: vor dem Verschieben die geschützten Mails aussortieren.

    ``hits`` sind die Tupel beider Werkzeuge: ``(id, datum, absender, betreff)``.
    Ist ``ziel`` nicht der Löschordner, geht alles unverändert durch.
    Rückgabe: (verschiebbar, zurückgehalten mit Befund).
    """
    if not ist_loeschordner(ziel):
        return list(hits), []
    eigene = eigene_adressen() if eigene is None else eigene
    gesendet = gesendet_an((adresse_von(h[2]) for h in hits), abfrage)
    frei: list[tuple] = []
    gehalten: list[tuple[tuple, Befund]] = []
    for h in hits:
        befund = pruefe(h[2], h[3], eigene=eigene, gesendet=gesendet)
        if befund:
            gehalten.append((h, befund))
        else:
            frei.append(h)
    return frei, gehalten


def melde_zurueckgehalten(gehalten: list[tuple[tuple, Befund]]) -> None:
    """Auf stdout UND stderr — eine Meldung nur auf stderr geht in jeder
    Pipeline verloren (vgl. organize_mail._move, 2026-08-18)."""
    if not gehalten:
        return
    kopf = f"  ! Löschschutz (platform#3176): {len(gehalten)} Mail(s) bleiben liegen"
    print(kopf)
    print(kopf, file=sys.stderr)
    for (_, datum, frm, betreff), befund in gehalten:
        print(f"    · [{befund.klasse}] {datum}  {frm[:38]:<38} {(betreff or '')[:50]}")
