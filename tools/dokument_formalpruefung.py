#!/usr/bin/env python3
"""dokument_formalpruefung.py — mechanische Formalprüfung eines eingereichten PDF.

Konsument: `/arbeit-pruefen`. Bewusst ein **Werkzeug**, nicht Skill-Prosa: eine
Prüfliste in einem langen Markdown-Dokument wird beim vierten Durchlauf
überflogen — ein Skript, das `Tabelle 7 fehlt` ausgibt, nicht. Gleiche Lehre wie
KONZ-platform-038 D6 (eine Regel ohne maschinellen Konsumenten ist Prosa).

Dreizehn Prüfungen, alle deterministisch aus dem Dokument selbst:

  F01 PDF-Erzeugungsweg + verlorene ff/fi-Ligaturen
  F02 Titel-Konsistenz (Deckblatt vs. PDF-Metadaten vs. Dateiname)
  F03 leere Deckblatt-Felder
  F04 Verzeichnisse, die es gibt, aber die im Inhaltsverzeichnis fehlen
  F05 Tabellen-Nummerierung (Lücken + Dubletten)
  F06 Abbildungs-Nummerierung (Lücken + Dubletten)
  F07 Unterschriften, die Dateinamen sind
  F08 Pflichtabschnitte, die nur aus der Überschrift bestehen
  F09 fehlende Standardteile (Abstract, Abkürzungsverzeichnis, ...)
  F10 Belegdichte gesamt und je Kapitel
  F11 Verzeichnis als nummeriertes Kapitel geführt
  F12 Literatureinträge extrahieren + formale Verdachtsmarker je Eintrag
  F13 Beleg im Text ohne Verzeichniseintrag / widersprüchliches Jahr

**F12 liefert Verdacht, keinen Befund.** Ob ein Autorenfeld wirklich falsch ist,
entscheidet nur der Abgleich mit der Originalquelle — den macht der Skill mit
einem Abruf je Eintrag. Das Werkzeug sagt deshalb "zu prüfen", nie "falsch":
Eine erfundene Korrektur in einer Rückmeldung an eine:n Studierende:n ist der
teuerste denkbare Fehler, weil sie autoritativ aussieht und falsifizierbar ist.

Aufruf:
    python3 tools/dokument_formalpruefung.py <datei.pdf>
    python3 tools/dokument_formalpruefung.py <datei.pdf> --json
    python3 tools/dokument_formalpruefung.py <datei.txt> --seiten-aus-text

Exit 0 auch bei Befunden (Report-Werkzeug, kein Gate). Exit 2 nur, wenn das
Dokument nicht lesbar ist — eine leere Befundliste aus einem ungelesenen
Dokument wäre eine Null, die der Filter erzeugt hat und nicht das Dokument.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# --- F01: Wörter, in denen eine ff/fi/fl-Ligatur beim PDF-Export verloren ging.
# "E ects" statt "Effects". Muster: Wortrest, der ohne die Ligatur entsteht.
LIGATUR_REST = re.compile(
    r"\b\w+ (?:ekt|ekte|ekten|ektiv|ects|ect|izient|izientes|erenz|erenzen|"
    r"erenzierung|erenziert|erenzieren|erenzierte|erenzierten|nden|nition|"
    r"nitionen|niert)\w*\b"
)
DATEI_ENDUNGEN = re.compile(r"\.(png|jpe?g|csv|xlsx?|pdf|svg|docx?|pptx?)\b", re.I)
HARVARD = re.compile(r"\([A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-& ]{1,40},\s*(?:S\.\s*)?\d{4}")
VERZEICHNIS_NAMEN = [
    "Inhaltsverzeichnis",
    "Abbildungsverzeichnis",
    "Tabellenverzeichnis",
    "Abkürzungsverzeichnis",
    "Symbolverzeichnis",
    "Literaturverzeichnis",
    "Anhangsverzeichnis",
]
# Abschnitte, die vorhanden UND gefüllt sein müssen.
PFLICHT_ABSCHNITTE = [
    "Eidesstattliche Erklärung",
    "Sperrvermerk",
    "Abstract",
    "Zusammenfassung",
]
# Standardteile, deren Fehlen einen Hinweis wert ist (kein harter Fehler).
ERWARTETE_TEILE = ["Abstract", "Abkürzungsverzeichnis", "Tabellenverzeichnis"]
BLOG_MUSTER = re.compile(
    r"linkedin\.com|geeksforgeeks|medium\.com|towardsdatascience|substack|"
    r"\bblog\b|stxnext|metricgate|truegeometry|genpact|apxml|/insight|"
    r"/think/topics|quora|stackoverflow|reddit",
    re.I,
)


class Befund:
    """Ein Prüfergebnis. `zu_pruefen=True` heißt Verdacht, nicht Fehler."""

    def __init__(self, code, titel, details, zu_pruefen=False, nutzlast=None):
        self.code = code
        self.titel = titel
        self.details = details
        self.zu_pruefen = zu_pruefen
        # Strukturierte Rohdaten für Konsumenten. Die Marker dürfen NICHT aus der
        # Textzeile zurückgeparst werden: Quellenangaben enthalten selbst eckige
        # Klammern ("arXiv:1905.11744v1 [cs.LG]") und erzeugen Phantom-Marker.
        self.nutzlast = nutzlast

    def as_dict(self):
        d = {
            "code": self.code,
            "titel": self.titel,
            "details": self.details,
            "zu_pruefen": self.zu_pruefen,
        }
        if self.nutzlast is not None:
            d["nutzlast"] = self.nutzlast
        return d


def _werkzeug_fehlt(name: str) -> bool:
    return shutil.which(name) is None


def lade_dokument(pfad: str, seiten_aus_text: bool) -> tuple[list[str], dict]:
    """Liefert (Seitenliste, PDF-Metadaten). Exit 2, wenn nichts gelesen werden kann."""
    meta: dict = {}
    if seiten_aus_text or pfad.lower().endswith(".txt"):
        try:
            text = open(pfad, encoding="utf-8").read()
        except OSError as exc:
            print(f"FEHLER: {pfad} nicht lesbar ({exc})", file=sys.stderr)
            sys.exit(2)
        return text.split("\f"), meta

    if _werkzeug_fehlt("pdftotext") or _werkzeug_fehlt("pdfinfo"):
        print(
            "FEHLER: poppler-utils fehlen (pdftotext/pdfinfo). Ohne sie ist die "
            "Prüfung nicht durchführbar — eine leere Befundliste waere hier das "
            "Werkzeug, nicht das Dokument.",
            file=sys.stderr,
        )
        sys.exit(2)

    info = subprocess.run(
        ["pdfinfo", pfad], capture_output=True, text=True, timeout=120
    )
    if info.returncode != 0:
        print(f"FEHLER: pdfinfo scheiterte an {pfad}", file=sys.stderr)
        sys.exit(2)
    for line in info.stdout.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()

    aus = subprocess.run(
        ["pdftotext", "-layout", pfad, "-"], capture_output=True, text=True, timeout=300
    )
    if aus.returncode != 0 or not aus.stdout.strip():
        print(f"FEHLER: pdftotext lieferte keinen Text aus {pfad}", file=sys.stderr)
        sys.exit(2)
    return aus.stdout.split("\f"), meta


def _verzeichnis_block(seiten: list[str], name: str) -> str:
    """Alle Seiten, deren Kopfzeile das genannte Verzeichnis trägt, als ein String."""
    teile = []
    for s in seiten:
        kopf = "\n".join(s.splitlines()[:2])
        if name in kopf:
            teile.append(s)
    return " ".join(" ".join(t.split()) for t in teile)


def _nummern(block: str, wort: str) -> list[int]:
    return [int(n) for n in re.findall(rf"{wort}\s+(\d+)\s*[-–]", block)]


def _verzeichnis_eintraege(seiten: list[str], wort: str, verz: str) -> list[str]:
    """Einträge eines Abbildungs-/Tabellenverzeichnisses, je Eintrag ein String.

    Getrennt wird am nächsten "<Wort> N -", nicht an einer Zeichengrenze — sonst
    werden umbrochene Unterschriften abgeschnitten und Treffer gehen still verloren.
    """
    block = _verzeichnis_block(seiten, verz)
    if not block:
        return []
    teile = re.split(rf"(?={wort}\s+\d+\s*[-–])", block)
    return [t.strip() for t in teile if re.match(rf"{wort}\s+\d+\s*[-–]", t.strip())]


def belege_im_text(roh: str) -> list[tuple[str, str]]:
    """Alle Klammerbelege als (Autorschlüssel, Jahr).

    Mehrfachbelege werden am Semikolon getrennt: "(Fleming & Koppelman, 2016;
    PMI, 2021)" sind ZWEI Belege. Ein Muster, das nur am "(" ansetzt, sieht den
    zweiten nie — genau so blieb ein Beleg ohne Verzeichniseintrag unentdeckt.
    """
    belege: list[tuple[str, str]] = []
    for klammer in re.findall(r"\(([^()]{3,140}?\d{4}[a-z]?)\)", roh):
        for teil in klammer.split(";"):
            m = re.match(
                r"\s*([A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-& ]{1,45}?),?\s*(?:S\.\s*)?(\d{4})",
                teil.strip(),
            )
            if m:
                belege.append((m.group(1).strip(), m.group(2)))
    return belege


def pruefe(seiten: list[str], meta: dict, pfad: str) -> list[Befund]:
    roh = "\n".join(seiten)
    befunde: list[Befund] = []

    # --- F01 Erzeugungsweg + Ligaturverlust
    producer = meta.get("Producer", "")
    verloren = sorted(set(LIGATUR_REST.findall(roh)))
    if verloren:
        befunde.append(
            Befund(
                "F01",
                f"{len(verloren)} Wörter mit verlorener ff/fi-Ligatur",
                [f"Producer: {producer or 'unbekannt'}"]
                + [f"„{w}“" for w in verloren[:12]]
                + (["..."] if len(verloren) > 12 else []),
            )
        )
    elif "Print To PDF" in producer:
        befunde.append(
            Befund(
                "F01",
                "PDF über einen Druck-Treiber erzeugt",
                [f"Producer: {producer}", "Ligaturverlust hier nicht nachweisbar."],
            )
        )

    # --- F02 Titel-Konsistenz
    deckblatt = seiten[0] if seiten else ""
    meta_titel = meta.get("Title", "")
    datei_titel = os.path.splitext(os.path.basename(pfad))[0]
    quellen = {"Metadaten": meta_titel, "Dateiname": datei_titel}
    stichworte = {
        q: set(re.findall(r"[A-Za-zÄÖÜäöüß]{6,}", v.lower()))
        for q, v in quellen.items()
        if v
    }
    deck_worte = set(re.findall(r"[A-Za-zÄÖÜäöüß]{6,}", deckblatt.lower()))
    abweichend = {
        q: sorted(w - deck_worte) for q, w in stichworte.items() if (w - deck_worte)
    }
    if abweichend:
        befunde.append(
            Befund(
                "F02",
                "Titel weicht zwischen Deckblatt und Metadaten/Dateiname ab",
                [
                    f"{q}: nicht auf dem Deckblatt: {', '.join(w[:6])}"
                    for q, w in abweichend.items()
                ],
                zu_pruefen=True,
            )
        )

    # --- F03 leere Deckblatt-Felder
    leer = [
        line.strip()
        for line in deckblatt.splitlines()
        if re.match(r"^\s*[A-ZÄÖÜ][A-Za-zÄÖÜäöüß .]{2,40}:\s*$", line)
    ]
    if leer:
        befunde.append(Befund("F03", f"{len(leer)} leere Deckblatt-Felder", leer))

    # --- F04 Verzeichnisse vorhanden, aber nicht im Inhaltsverzeichnis
    inhalt = _verzeichnis_block(seiten, "Inhaltsverzeichnis")
    fehlend = []
    for name in VERZEICHNIS_NAMEN:
        if name == "Inhaltsverzeichnis":
            continue
        existiert = bool(_verzeichnis_block(seiten, name))
        gelistet = name in inhalt
        if existiert and not gelistet:
            fehlend.append(name)
    if fehlend:
        befunde.append(
            Befund(
                "F04",
                "Verzeichnis existiert, fehlt aber im Inhaltsverzeichnis",
                fehlend,
            )
        )

    # --- F05/F06 Nummerierung
    for code, wort, verz in (
        ("F05", "Tabelle", "Tabellenverzeichnis"),
        ("F06", "Abbildung", "Abbildungsverzeichnis"),
    ):
        nums = _nummern(_verzeichnis_block(seiten, verz), wort)
        if not nums:
            continue
        dubletten = sorted({n for n in nums if nums.count(n) > 1})
        luecken = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
        details = []
        if luecken:
            details.append(f"fehlende Nummern: {luecken}")
        if dubletten:
            details.append(f"doppelt vergeben: {dubletten}")
        if details:
            befunde.append(Befund(code, f"{wort}n-Nummerierung fehlerhaft", details))

    # --- F07 Unterschriften, die Dateinamen sind
    # Der Eintrag geht bis zum NÄCHSTEN "Abbildung N -", nicht bis zu einer festen
    # Zeichenzahl: eine Fenstergrenze schneidet lange Unterschriften ab und zählt
    # dadurch zu WENIG (erster Wurf meldete 16 statt 32 — die Null bzw. die zu
    # kleine Zahl war das Messgerät, nicht das Dokument).
    for wort, verz in (
        ("Abbildung", "Abbildungsverzeichnis"),
        ("Tabelle", "Tabellenverzeichnis"),
    ):
        eintraege = _verzeichnis_eintraege(seiten, wort, verz)
        mit_datei = [e for e in eintraege if DATEI_ENDUNGEN.search(e)]
        if mit_datei:
            befunde.append(
                Befund(
                    "F07",
                    f"{len(mit_datei)} von {len(eintraege)} {wort}sunterschriften "
                    "nennen einen Dateinamen statt des Inhalts",
                    [e[:78] for e in mit_datei[:8]]
                    + (["..."] if len(mit_datei) > 8 else []),
                )
            )

    # --- F08 Pflichtabschnitte, die nur aus der Überschrift bestehen
    leere_abschnitte = []
    for name in PFLICHT_ABSCHNITTE:
        for i, s in enumerate(seiten):
            kopf = "\n".join(s.splitlines()[:2])
            if name not in kopf:
                continue
            rest = s
            for teil in (name, str(i + 1)):
                rest = rest.replace(teil, " ")
            if len(rest.split()) <= 3:
                leere_abschnitte.append(f"{name} (Textseite {i + 1}) — nur Überschrift")
            break
    if leere_abschnitte:
        befunde.append(Befund("F08", "Pflichtabschnitt ohne Inhalt", leere_abschnitte))

    # --- F09 fehlende Standardteile
    fehlt = [t for t in ERWARTETE_TEILE if t not in roh]
    if fehlt:
        befunde.append(
            Befund(
                "F09",
                "Standardteil kommt im Dokument nicht vor",
                fehlt,
                zu_pruefen=True,
            )
        )

    # --- F10 Belegdichte
    alle_belege = belege_im_text(roh)
    je_kapitel: dict[str, int] = {}
    for s in seiten:
        kopf = " ".join(s.splitlines()[:1])
        m = re.search(r"Kapitel\s+(\d+)", kopf)
        schl = f"Kapitel {m.group(1)}" if m else "ohne Kapitelkopf"
        je_kapitel[schl] = je_kapitel.get(schl, 0) + len(belege_im_text(s))
    befunde.append(
        Befund(
            "F10",
            f"{len(alle_belege)} Klammerbelege, {len(set(alle_belege))} verschiedene Quellen",
            [f"{k}: {v}" for k, v in sorted(je_kapitel.items())],
            zu_pruefen=True,
        )
    )

    # --- F13 Beleg ohne Verzeichniseintrag / widersprüchliches Jahr
    lit_block = " ".join(
        " ".join(s.split())
        for s in seiten
        if "Literaturverzeichnis" in "\n".join(s.splitlines()[:2])
    )
    if lit_block:
        # Gegen die AUTORENFELDER der Einträge prüfen, nicht gegen den rohen Block:
        # sonst gilt ein Beleg als belegt, weil sein Kürzel zufällig als Verlag in
        # einem fremden Eintrag steht ("PMI" als Verlag von Fleming 2010) — der
        # Treffer waere dann das Messgerät, nicht das Verzeichnis.
        autorfelder = [e["autor"] for e in literatur_eintraege(seiten)]
        ohne_eintrag, jahr_konflikt = [], []
        for autor, jahr in sorted(set(alle_belege)):
            nachname = autor.replace("&", " ").split()[-1]
            passende = [a for a in autorfelder if nachname.lower() in a.lower()]
            if not passende:
                ohne_eintrag.append(
                    f"({autor}, {jahr}) — „{nachname}“ fehlt im Verzeichnis"
                )
                continue
            eintrag_texte = [
                e["text"]
                for e in literatur_eintraege(seiten)
                if nachname.lower() in e["autor"].lower()
            ]
            if not any(jahr in t for t in eintrag_texte):
                jahr_konflikt.append(
                    f"({autor}, {jahr}) — „{nachname}“ steht im Verzeichnis mit anderem Jahr"
                )
        if ohne_eintrag:
            befunde.append(
                Befund(
                    "F13",
                    "Beleg im Text ohne Eintrag im Literaturverzeichnis",
                    ohne_eintrag,
                )
            )
        if jahr_konflikt:
            befunde.append(
                Befund(
                    "F13",
                    "Beleg und Verzeichniseintrag nennen verschiedene Jahre",
                    jahr_konflikt,
                )
            )

    # --- F11 Verzeichnis als nummeriertes Kapitel
    kapitel_verz = re.findall(
        r"^\s*(\d+)\.\s+((?:Literatur|Abbildungs|Tabellen|Abkürzungs)verzeichnis[^\n]{0,40})",
        roh,
        re.M,
    )
    if kapitel_verz:
        befunde.append(
            Befund(
                "F11",
                "Verzeichnis wird als nummeriertes Kapitel geführt",
                [f"{n}. {t.strip()}" for n, t in dict(kapitel_verz).items()][:5],
            )
        )

    # --- F12 Literatureinträge
    eintraege = literatur_eintraege(seiten)
    if eintraege:
        ohne_marker = sum(1 for e in eintraege if not e["marker"])
        befunde.append(
            Befund(
                "F12",
                f"{len(eintraege)} Literatureinträge extrahiert — jeder ist gegen "
                "die Originalquelle zu prüfen",
                [_eintrag_zeile(e) for e in eintraege]
                + [
                    f"({ohne_marker} Einträge ohne Verdachtsmarker — das heißt NICHT "
                    "'korrekt'. Ein formal sauber gesetzter, aber falsch "
                    "zugeschriebener Autor traegt keinen Marker.)"
                ],
                zu_pruefen=True,
                nutzlast=eintraege,
            )
        )
    return befunde


def literatur_eintraege(seiten: list[str]) -> list[dict]:
    """Extrahiert die Einträge des Literaturverzeichnisses mit Verdachtsmarkern."""
    block = ""
    for s in seiten:
        kopf = "\n".join(s.splitlines()[:2])
        if "Literaturverzeichnis" in kopf:
            block += s + "\n"
    if not block:
        return []
    roh_eintraege: list[str] = []
    akt: list[str] = []
    for line in block.splitlines():
        if not line.strip():
            continue
        if re.match(r"^\s*Literaturverzeichnis", line):
            continue
        einzug = len(line) - len(line.lstrip())
        if einzug <= 2:
            if akt:
                roh_eintraege.append(" ".join(akt))
            akt = [line.strip()]
        else:
            akt.append(line.strip())
    if akt:
        roh_eintraege.append(" ".join(akt))

    eintraege = []
    for text in roh_eintraege:
        if "(" not in text:
            continue
        marker = []
        # Bis zur Klammer schneiden, die das DATUM traegt — nicht bis zur ersten
        # Klammer ueberhaupt: "Institute For the Future (IFF), U. o. (11. 05 2026)"
        # verlöre sonst den halben Autorschluessel an das Kuerzel.
        m_datum = re.search(r"\((?:\s*kein Datum\s*|[^()]*\d{4}[a-z]?\s*)\)", text)
        autor = text[: m_datum.start()] if m_datum else text.split("(", 1)[0]
        autor = autor.strip().rstrip(".").strip()
        # Ausgeschriebener Vorname neben blossen Initialen => Word-Quellenmanager.
        # Zwei Realfaelle haben das Muster nacheinander gesprengt:
        #   "Quentin W. Fleming, J. M." — mittlerer Initial => `(?:\s+[A-Z]\.)?`
        #   "Léo Grinsztajn, E. O."     — Akzent im Vornamen => volle Latin-1-Klasse
        # Namen sind der Ort, an dem eine ASCII-Annahme am zuverlaessigsten bricht.
        gross = r"[A-ZÀ-ÖØ-Þ]"
        klein = r"[a-zß-öø-ÿ]"
        if re.search(
            rf"{gross}{klein}{{2,}}(?:\s+{gross}\.)?\s+{gross}{klein}{{2,}}", autor
        ) and re.search(rf"\b{gross}\.\s*{gross}?\.?\s*$", autor):
            marker.append("autorenfeld-gemischt")
        if re.match(r"^(arXiv|doi|https?|www\.)", autor, re.I):
            marker.append("quellen-id-statt-autor")
        if re.search(r"\b(Institute|University|GmbH|Inc\.|Ltd|Universit)", autor):
            marker.append("einrichtung-statt-autor")
        if re.search(r"\(\s*\d{1,2}\.\s*\d{1,2}\s+\d{4}\s*\)", text):
            marker.append("datum-statt-jahr")
        if re.search(r"\(kein Datum\)", text):
            marker.append("ohne-datum")
        if re.search(
            r"(Springer Nature|Springer|Elsevier|Wiley|Emerald),\s*\d+\s*[-–]\s*\d+",
            text,
        ):
            marker.append("verlag-statt-zeitschrift")
        if BLOG_MUSTER.search(text):
            marker.append("blog-oder-anbieterseite")
        eintraege.append({"autor": autor, "text": text, "marker": marker})
    return eintraege


def _eintrag_zeile(e: dict) -> str:
    m = f"  [{', '.join(e['marker'])}]" if e["marker"] else ""
    return f"{e['text'][:96]}{m}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datei", help="PDF (oder bereits extrahierter Text)")
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    ap.add_argument(
        "--seiten-aus-text",
        action="store_true",
        help="Eingabe ist bereits extrahierter Text mit Seitenumbrüchen (\\f)",
    )
    args = ap.parse_args()

    seiten, meta = lade_dokument(args.datei, args.seiten_aus_text)
    befunde = pruefe(seiten, meta, args.datei)

    if args.json:
        print(
            json.dumps(
                {
                    "datei": os.path.basename(args.datei),
                    "seiten": len(seiten),
                    "metadaten": meta,
                    "befunde": [b.as_dict() for b in befunde],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"# Formalprüfung — {os.path.basename(args.datei)} ({len(seiten)} Seiten)")
    if meta.get("Producer"):
        print(f"  Producer: {meta['Producer']}")
    print()
    for b in befunde:
        marke = "?" if b.zu_pruefen else "!"
        print(f"[{marke}] {b.code}  {b.titel}")
        for d in b.details:
            print(f"       · {d}")
        print()
    print(
        "Legende: [!] = Befund aus dem Dokument · [?] = Verdacht, braucht eine "
        "eigene Prüfung.\n"
        "F12 nennt NIE einen Fehler — welcher Eintrag falsch ist, entscheidet "
        "allein der Abgleich\nmit der Originalquelle (ein Abruf je Eintrag)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
