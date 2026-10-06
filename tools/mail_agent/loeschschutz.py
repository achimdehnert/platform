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
   Firmen-Domains ``EIGENE_KONTO_DOMAENEN``. Die Hochschul-Domain zählt
   nicht dazu (Owner-Entscheid 2026-09-14, Refs #3176): dort schreiben auch
   System-Absender, die im Löschordner bleiben sollen („drin lassen").
2. **Beleg** — Betreff oder Anhangname trifft ``BELEG_MUSTER`` (Rechnung,
   Invoice, Receipt, Gutschrift, Zahlung, Sicherheitscode, …). Ein Beleg
   gehört zur Aufbewahrung, nie zum Rauschen.
3. **Gesendet-Historie** — der Owner hat dieser Adresse je geschrieben (ein
   Treffer mit ``--an <adresse>`` in einem Gesendet-Ordner des Index).

**Fail-closed.** Ist der Index für die Gesendet-Prüfung nicht erreichbar, wirft
`gesendet_an` — der Aufrufer verschiebt dann nichts in den Löschordner. Liegen
lassen ist reversibel und billig; eine Personenmail im Löschordner nicht.

**Owner-Übersteuerung (Lernordner).** Hat der Owner einen Absender oder eine
Domain selbst in einen Lernordner gezogen (``lernordner.py``), steht der
Eintrag unter ``rausch_regeln.owner_gelernt`` im Ledger. Für diese Absender
entfällt die Gesendet-Prüfung — sein Zug ist die Entscheidung, auch wenn er
ihnen einmal geschrieben hat. Eigene Adressen und Belege bleiben geschützt.

**Owner-Behalten (platform#3637).** Was der Owner ausdrücklich behalten will,
steht unter ``rausch_regeln.bewusst_NICHT_aufgenommen``. Ein solcher Absender
kommt nie in den Löschordner — auch nicht über eine gelernte Domain-Regel,
denn „behalten" ist die engere und damit maßgebliche Owner-Entscheidung.
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

#: Freemail-Domains schicken Menschen, keine Newsletter — weder als Kandidat
#: (``rausch_kandidaten.plausibel``) noch als gelernte Domain-Regel.
FREEMAIL_DOMAENEN = (
    "gmail.com", "googlemail.com", "gmx.de", "gmx.net", "gmx.at", "web.de",
    "t-online.de", "yahoo.com", "yahoo.de", "outlook.com", "outlook.de",
    "hotmail.com", "hotmail.de", "live.com", "icloud.com", "me.com",
    "posteo.de", "mailbox.org", "freenet.de", "aol.com", "proton.me",
    "protonmail.com",
)  # fmt: skip

#: Vorgangs-Ledger (lokal, nie im Repo) mit den Rauschregeln.
LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"

#: Schlüssel unter ``rausch_regeln``: Einträge, die der Owner per Lernordner
#: selbst bestimmt hat (``lernordner.py``).
GELERNT_SCHLUESSEL = "owner_gelernt"

#: Schlüssel unter ``rausch_regeln``: Adresse oder Domain → Grund, die der Owner
#: behalten will (platform#3637). Ein Wert mit ``absender``-Liste (Sammel-
#: korrektur eines Tages) zählt mit seinen Adressen.
BEHALTEN_SCHLUESSEL = "bewusst_NICHT_aufgenommen"

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

    klasse: str  # "owner_behalten" | "eigene_adresse" | "beleg" | "gesendet" | …
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


def trifft_eintrag(adresse: str, eintrag: str) -> bool:
    """Regel-Eintrag gegen eine Adresse: mit "@" exakt, sonst Domain samt Subdomains."""
    eintrag = (eintrag or "").strip().lower()
    if not eintrag or not adresse:
        return False
    if "@" in eintrag:
        return adresse == eintrag
    domain = adresse.rsplit("@", 1)[-1]
    return domain == eintrag or domain.endswith("." + eintrag)


def owner_gelernt(ledger: Path | None = None) -> list[str]:
    """Die per Lernordner gelernten Einträge. Fehlt das Ledger, gibt es keine —
    das nimmt nur die Übersteuerung weg, nie einen Schutz."""
    try:
        daten = json.loads((ledger or LEDGER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    zeilen = (daten.get("rausch_regeln") or {}).get(GELERNT_SCHLUESSEL) or []
    return [z["eintrag"] for z in zeilen if isinstance(z, dict) and z.get("eintrag")]


def _ist_eintrag(text: str) -> bool:
    """Adresse oder Domain — nicht ein Meta-Schlüssel wie ``owner_korrektur_…``."""
    return "." in text and " " not in text


def owner_behalten(ledger: Path | None = None) -> list[str]:
    """Die Einträge, die der Owner behalten will (platform#3637).

    Fehlt das Ledger, gibt es keine — dann fehlen auch die Rauschregeln, die sie
    überstimmen könnten. Ein ausdrücklicher ``--from`` ohne Ledger ist die
    Entscheidung des Aufrufers; Belege, eigene Adressen und Gesendet-Historie
    schützen weiter.
    """
    try:
        daten = json.loads((ledger or LEDGER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    tabelle = (daten.get("rausch_regeln") or {}).get(BEHALTEN_SCHLUESSEL) or {}
    eintraege: list[str] = []
    for schluessel, wert in tabelle.items():
        if _ist_eintrag(schluessel):
            eintraege.append(schluessel.strip().lower())
        if isinstance(wert, dict):
            eintraege += [
                a.strip().lower()
                for a in wert.get("absender") or []
                if isinstance(a, str) and _ist_eintrag(a)
            ]
    return list(dict.fromkeys(eintraege))


def trifft_einen(adresse: str, eintraege: Iterable[str]) -> bool:
    return any(trifft_eintrag(adresse, e) for e in eintraege)


def behalten_kollision(eintrag: str, behalten: Iterable[str]) -> str | None:
    """Der Behalten-Eintrag, den eine neue Löschregel träfe — sonst ``None``.

    Eine Domain-Regel kollidiert mit jeder behaltenen Adresse darunter, mit
    einer behaltenen Subdomain und mit einer behaltenen Eltern-Domain.
    """
    eintrag = (eintrag or "").strip().lower()
    for b in behalten:
        if "@" in eintrag:
            treffer = trifft_eintrag(eintrag, b)
        elif "@" in b:
            treffer = trifft_eintrag(b, eintrag)
        else:
            treffer = (
                b == eintrag or b.endswith("." + eintrag) or eintrag.endswith("." + b)
            )
        if treffer:
            return b
    return None


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
    owner_entschieden: bool = False,
    behalten: Iterable[str] = (),
) -> Befund | None:
    """Schutz-Befund für eine Mail — ``None`` heißt: darf in den Löschordner.

    ``owner_entschieden``: der Absender steht in ``owner_gelernt`` — dann
    zählt die Gesendet-Historie nicht, eigene Adresse und Beleg schon.
    ``behalten``: Owner-Behalten-Einträge; ein Treffer schlägt ``owner_entschieden``.
    """
    adresse = adresse_von(absender)
    if not adresse:
        return Befund("unbekannt", "Absenderadresse nicht lesbar")
    if trifft_einen(adresse, behalten):
        return Befund("owner_behalten", adresse)
    if ist_eigene_adresse(adresse, eigene):
        return Befund("eigene_adresse", adresse)
    if ist_beleg(betreff, anhaenge):
        return Befund("beleg", (betreff or "")[:60])
    if adresse in gesendet and not owner_entschieden:
        return Befund("gesendet", adresse)
    return None


def filtere_verschiebung(
    ziel: str,
    hits: list[tuple],
    *,
    eigene: set[str] | None = None,
    abfrage: Callable[[list[dict]], list[dict]] | None = None,
    gelernt: Iterable[str] | None = None,
    anhang_namen: AnhangLeser | None = None,
    behalten: Iterable[str] | None = None,
) -> tuple[list[tuple], list[tuple[tuple, Befund]]]:
    """K3: vor dem Verschieben die geschützten Mails aussortieren.

    ``hits`` sind die Tupel beider Werkzeuge: ``(id, datum, absender, betreff)``.
    Ist ``ziel`` nicht der Löschordner, geht alles unverändert durch.
    ``gelernt`` und ``behalten`` sind Owner-Einträge (Default: aus dem Ledger).
    ``anhang_namen`` liest die Anhangnamen direkt aus dem Postfach (platform#3627);
    gefragt werden nur die Mails, die nach Adresse und Betreff frei wären.
    Rückgabe: (verschiebbar, zurückgehalten mit Befund).
    """
    if not ist_loeschordner(ziel):
        return list(hits), []
    eigene = eigene_adressen() if eigene is None else eigene
    gelernt = list(owner_gelernt() if gelernt is None else gelernt)
    behalten = list(owner_behalten() if behalten is None else behalten)
    gesendet = gesendet_an((adresse_von(h[2]) for h in hits), abfrage)
    frei: list[tuple] = []
    gehalten: list[tuple[tuple, Befund]] = []
    for h in hits:
        befund = pruefe(
            h[2],
            h[3],
            eigene=eigene,
            gesendet=gesendet,
            owner_entschieden=trifft_einen(adresse_von(h[2]), gelernt),
            behalten=behalten,
        )
        if befund:
            gehalten.append((h, befund))
        else:
            frei.append(h)
    if anhang_namen and frei:
        frei, per_anhang = anhaenge_pruefen(frei, anhang_namen)
        gehalten += per_anhang
    return frei, gehalten


#: Liest je Mail-Kennung die Anhangnamen; ``None`` = nicht lesbar.
AnhangLeser = Callable[[list[tuple]], dict[str, "list[str] | None"]]


def anhaenge_pruefen(
    hits: list[tuple], anhang_namen: AnhangLeser
) -> tuple[list[tuple], list[tuple[tuple, Befund]]]:
    """Beleg-Schutz über die Anhangnamen aus dem Postfach (platform#3627).

    Fail-closed wie die Gesendet-Prüfung: sind die Anhänge einer Mail nicht
    lesbar, bleibt sie liegen.
    """
    namen = anhang_namen(hits)
    frei: list[tuple] = []
    gehalten: list[tuple[tuple, Befund]] = []
    for h in hits:
        liste = namen.get(_kennung(h[0]))
        if liste is None:
            gehalten.append((h, Befund("anhang_unlesbar", "Anhänge nicht lesbar")))
        elif ist_beleg("", liste):
            treffer = next(a for a in liste if BELEG_MUSTER.search(a or ""))
            gehalten.append((h, Befund("beleg", f"Anhang {treffer[:50]}")))
        else:
            frei.append(h)
    return frei, gehalten


def _kennung(roh) -> str:
    """Graph-messageId (str) und IMAP-UID (bytes) als ein Schlüssel."""
    return roh.decode() if isinstance(roh, (bytes, bytearray)) else str(roh)


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
