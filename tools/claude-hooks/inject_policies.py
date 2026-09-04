#!/usr/bin/env python3
"""UserPromptSubmit-Hook — schiebt bei Trigger-Woertern den KOPF einer
Org-Policy aus ``~/.claude/policies/`` in den Kontext, nicht mehr den Volltext.

Warum die Umstellung (platform#2606, Stufe 1 "Kontext-Diaet"):
In einer einzigen Sitzung am 2026-09-02 feuerte die Volltext-Fassung viermal
mit 10,9 / 15,8 / 90,6 / **106,0 KB**. Zwei dieser vier Injektionen gingen auf
System-Benachrichtigungen (Abschlussmeldungen von Hintergrund-Agenten), ohne
dass ein Mensch etwas geschrieben hatte. Der Agent kann jede Policy jederzeit
selbst lesen — der Hook muss ihn nur darauf stossen. Also: Titel + Kern +
Pfad, gedeckelt, statt der ganzen Datei.

Vier Aenderungen gegenueber der Volltext-Fassung:

1. **Kopf statt Volltext.** Je Treffer Titel, Pfad und die ersten Zeilen des
   ``## Rule``-Abschnitts (fehlt der: erster ``##``-Abschnitt), gedeckelt auf
   ``POLICY_KOPF_BYTES`` (Default 1500), plus der Satz, wo der Volltext steht.
2. **Wortgrenzen statt Substring.** ``fehler`` traf bisher jedes ``Fehler``
   irgendwo im Wort. Jetzt ``\\b``-verankert (unicode, case-insensitiv), mit
   einem eng gefassten deutschen Flexionsschwanz (siehe ``_muster``), damit
   "Fehlern" trifft und "Fehlerbehebung" nicht. Ein in der Policy-Datei
   GROSS geschriebener Trigger (``COMPLETE``) wird case-SENSITIV geprueft —
   er meint den Status-Marker, nicht das englische Adjektiv.
3. **Keine System-Texte.** Beginnt der Prompt mit einer Maschinen-Huelle
   (``<task-notification>``, ``<system-reminder>``, ``<bash-input>``, der
   Kompaktierungs-Vorspann …), wird nichts injiziert. Das ist mit den
   vorhandenen Feldern loesbar: das ``UserPromptSubmit``-Event traegt zwar nur
   ``prompt``, aber diese Huellen stehen dort am Textanfang — nachgemessen in
   den Transkripten (2 370 von 5 877 ``user``-Eintraegen tragen so eine
   Huelle).
4. **Obergrenze.** Insgesamt hoechstens ``POLICY_INJEKTION_BYTES`` (Default
   6000). Was darueber laege, erscheint nur noch als Pfadliste.

Trigger-Entscheidungen (gemessen an 3 507 echten Prompts aus den lokalen
Transkripten, siehe ``_GEDAEMPFT``): ``done`` und ``claim`` sind gestrichen,
``mcp`` ist an ein zweites Wort gebunden.

Contract (wie die uebrigen Hooks hier): Event-JSON auf stdin, IMMER exit 0,
niemals eine Exception nach aussen. Bei einem Treffer freier Text auf stdout —
den sieht Claude als Kontext-Vorspann dieser Runde. Ohne Treffer: still.

Env:
  POLICY_DIR               Policy-Verzeichnis (Default ~/.claude/policies).
  POLICY_KOPF_BYTES        Deckel je Policy (Default 1500). 0 deaktiviert.
  POLICY_INJEKTION_BYTES   Deckel gesamt (Default 6000).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

TRIGGER_LINE_RE = re.compile(r"\*\*Trigger words:\*\*\s*(.+)", re.IGNORECASE)
TITEL_RE = re.compile(r"^#\s+(.+)")
ABSCHNITT_RE = re.compile(r"^##\s+(.+)")
REGEL_RE = re.compile(r"^(rule|regel)\b", re.IGNORECASE)

KOPF_BYTES_DEFAULT = 1500
GESAMT_BYTES_DEFAULT = 6000
KERN_ZEILEN = 5

# Maschinen-Huellen am Prompt-Anfang. Ein Mensch beginnt seine Nachricht nicht
# so; die Abschlussmeldung eines Hintergrund-Agenten und der Kompaktierungs-
# Vorspann tun es immer. Gemessen 2026-09-02 ueber alle lokalen Transkripte.
SYSTEM_PRAEFIXE = (
    "<task-notification>",
    "<system-reminder>",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<command-name>",
    "<command-message>",
    "<bash-input>",
    "<bash-stdout>",
    "<bash-stderr>",
    "[SYSTEM NOTIFICATION",
    "This session is being continued from a previous conversation",
)

# Deutscher Flexionsschwanz. Ohne ihn verliert die Wortgrenze jede gebeugte
# Form ("Agenten", "Fehlern", "ADRs") — gemessen: `agent` faellt von 80 auf 35
# Treffer. Mit ihm bleibt der eigentliche Gewinn erhalten: das Kompositum
# ("Fehlerbehebung") trifft weiterhin nicht, weil danach keine Wortgrenze
# steht. Bewusst eine geschlossene, kurze Liste — jede Erweiterung naehert
# sich wieder dem Substring an.
_FLEXION = r"(?:e?[nrms]|en|es|er|em|innen)?"


def _muster(wort: str) -> re.Pattern[str]:
    """Trigger als Wortmuster. Nur alphanumerische Raender bekommen ``\\b``.

    Trigger wie ``#nolimits``, ``/command`` oder ``?demo=`` haben einen
    nicht-alphanumerischen Rand; ein ``\\b`` davor wuerde dort das Gegenteil
    bedeuten und den Trigger tot machen.

    Ein GROSS geschriebener Trigger wird case-sensitiv geprueft: ``COMPLETE``
    in ``evidence-discipline.md`` meint den Status-Marker "COMPLETE", nicht
    jedes englische "complete" in einem eingefuegten Text (gemessen: 14
    Treffer, davon keiner eine echte Nutzer-Behauptung).
    """
    roh = wort.strip()
    sensitiv = roh.isupper() and any(c.isalpha() for c in roh)
    p = re.escape(roh)
    if roh[:1].isalnum():
        p = r"\b" + p
    if roh[-1:].isalnum():
        p = p + _FLEXION + r"\b"
    return re.compile(p, 0 if sensitiv else re.IGNORECASE)


# Gedaempfte Trigger. Schluessel = Trigger-Wort (klein), Wert = Menge zweiter
# Woerter, von denen eines im Prompt stehen muss; eine LEERE Menge streicht den
# Trigger. Gemessen an 3 507 echten Prompts der lokalen Transkripte:
#
#   done   182 Treffer — durchweg die Abhak-Kurzschrift des Owners
#                        ("5 done 6 go 7 go"). Das ist keine Behauptung des
#                        Agenten, sondern der Mensch, der Punkte abhakt.
#                        Genau der Fall, den evidence-discipline NICHT meint.
#   claim    8 Treffer — 6 davon im automatisch erzeugten Kompaktierungs-
#                        Vorspann, der Rest eingefuegter Fremdtext. Null echte
#                        Nutzung.
#   mcp     12 Treffer — ueberwiegend der Repo-Name "mcp-hub" oder Fremdtext;
#                        die Policy meint den Orchestrator-Dienst. Deshalb
#                        gebunden statt gestrichen.
#
# Die Daempfung sitzt hier und nicht in den Policy-Dateien: die Dateien liegen
# nur maschinenlokal, der Hook wird verteilt — eine Aenderung dort waere fuer
# die Drift-Pruefung unsichtbar (🌀 "aktive Kopie ohne Quelle").
_GEDAEMPFT: dict[str, frozenset[str]] = {
    "done": frozenset(),
    "claim": frozenset(),
    "mcp": frozenset(
        {"orchestrator", "server", "memory", "headless", "routing", "sse", "tool"}
    ),
}


def policies_dir() -> Path:
    return Path(os.environ.get("POLICY_DIR") or (Path.home() / ".claude" / "policies"))


def ist_system_text(prompt: str) -> bool:
    """Kommt dieser Prompt von der Maschine statt von einem Menschen?"""
    kopf = prompt.lstrip()
    return kopf.startswith(SYSTEM_PRAEFIXE)


def load_triggers(verzeichnis: Path | None = None) -> list[tuple[Path, list[str]]]:
    """``(policy_pfad, trigger_woerter)`` je Policy-Datei."""
    verzeichnis = verzeichnis or policies_dir()
    triggers: list[tuple[Path, list[str]]] = []
    if not verzeichnis.is_dir():
        return triggers
    for md in sorted(verzeichnis.glob("*.md")):
        if md.name == "README.md":
            continue
        try:
            head = md.read_text(encoding="utf-8", errors="replace").splitlines()[:10]
        except OSError:
            continue
        for i, line in enumerate(head):
            m = TRIGGER_LINE_RE.search(line)
            if not m:
                continue
            # Umgebrochene Listen: Fortsetzungszeilen bis zur Leerzeile/naechsten
            # Auszeichnung gehoeren noch zur Trigger-Liste (Baseline-Befund
            # 2026-07-10: 4/13 Goldset-Misses durch abgeschnittene Zeile 2).
            #
            # Verbunden wird mit LEERZEICHEN, nicht mit Komma (Fix #2606): der
            # Umbruch trennt nicht zwingend zwei Trigger. In
            # `platform-agents.md` bricht "where should this live" nach "where"
            # um — die Komma-Fassung machte daraus zwei Trigger, und "where"
            # allein traf 18-mal, ausnahmslos im Kompaktierungs-Vorspann.
            parts = [m.group(1)]
            for cont in head[i + 1 :]:
                cont = cont.strip()
                if not cont or cont.startswith(("**", "#", "-", ">")):
                    break
                parts.append(cont)
            words = [w.strip() for w in " ".join(parts).split(",") if w.strip()]
            triggers.append((md, words))
            break
    return triggers


def _trifft(prompt: str, wort: str) -> bool:
    klein = wort.strip().lower()
    if klein in _GEDAEMPFT:
        partner = _GEDAEMPFT[klein]
        if not partner:
            return False
        if not any(_muster(p).search(prompt) for p in partner):
            return False
    return bool(_muster(wort).search(prompt))


def find_matches(prompt: str, triggers: list[tuple[Path, list[str]]]) -> list[Path]:
    """Policy-Dateien, deren Trigger im Prompt als ganzes Wort vorkommen."""
    return [p for p, woerter in triggers if any(_trifft(prompt, w) for w in woerter)]


def _kern_zeilen(zeilen: list[str]) -> list[str]:
    """Die ersten inhaltlichen Zeilen des ``## Rule``-Abschnitts.

    Ohne ``## Rule`` (z. B. ``orchestrator.md`` beginnt mit ``## What it is``)
    der erste ``##``-Abschnitt ueberhaupt. Ohne jeden ``##``-Abschnitt die
    ersten inhaltlichen Zeilen nach dem Kopf — dann ist die Datei so kurz, dass
    der Deckel ohnehin greift.
    """
    start = None
    erste = None
    for i, z in enumerate(zeilen):
        m = ABSCHNITT_RE.match(z)
        if not m:
            continue
        if erste is None:
            erste = i
        if REGEL_RE.match(m.group(1).strip()):
            start = i
            break
    if start is None:
        start = erste
    ab = zeilen[start + 1 :] if start is not None else zeilen

    kern: list[str] = []
    for z in ab:
        if ABSCHNITT_RE.match(z):
            break
        if not z.strip():
            if kern:
                kern.append("")
            continue
        if z.lstrip().startswith(("<!--", "**Trigger words:")):
            continue
        kern.append(z.rstrip())
        if sum(1 for k in kern if k.strip()) >= KERN_ZEILEN:
            break
    while kern and not kern[-1].strip():
        kern.pop()
    return kern


def _kuerzen(text: str, budget: int) -> str:
    """Auf ``budget`` Bytes an einer Zeilengrenze kappen."""
    roh = text.encode("utf-8")
    if len(roh) <= budget:
        return text
    zeilen = text.splitlines()
    behalten: list[str] = []
    verbraucht = 0
    for z in zeilen:
        n = len(z.encode("utf-8")) + 1
        if verbraucht + n > budget:
            break
        behalten.append(z)
        verbraucht += n
    if not behalten:
        return roh[:budget].decode("utf-8", errors="ignore").rstrip() + " …"
    return "\n".join(behalten).rstrip() + "\n…"


def kopf(pfad: Path, budget: int = KOPF_BYTES_DEFAULT) -> str:
    """Titel + Kern + Zeiger auf den Volltext — nie mehr als ``budget`` Bytes."""
    try:
        zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    titel = next(
        (TITEL_RE.match(z).group(1).strip() for z in zeilen if TITEL_RE.match(z)),
        pfad.stem,
    )
    kopfzeile = f"### {titel} — `{pfad}`"
    fuss = f"_Volltext bei Bedarf: `{pfad}` lesen._"
    rest = budget - len(kopfzeile.encode()) - len(fuss.encode()) - 4
    kern = _kuerzen("\n".join(_kern_zeilen(zeilen)).strip(), max(rest, 0))
    return "\n".join(x for x in (kopfzeile, "", kern, "", fuss) if x is not None)


EINLEITUNG = (
    "📋 **Org-Policy-Kopf** (auto-injiziert aus `~/.claude/policies/`, "
    "gekuerzt — Volltext auf Anforderung lesen):"
)


def _zusammensetzen(teile: list[str], uebrig: list[Path], gesamt_budget: int) -> str:
    out = [EINLEITUNG, ""]
    for block in teile:
        out += ["---", block, ""]
    if uebrig:
        pfade = " · ".join(f"`{p}`" for p in uebrig)
        out += [
            "---",
            "_Weitere einschlaegige Policies (nicht injiziert, Deckel "
            f"{gesamt_budget} B): {pfade}_",
            "",
        ]
    out.append("_Ende Policy-Kopf. Vor Defaults anwenden; bei Zweifel Volltext lesen._")
    return "\n".join(out) + "\n"


def baue_ausgabe(
    matched: list[Path],
    kopf_budget: int = KOPF_BYTES_DEFAULT,
    gesamt_budget: int = GESAMT_BYTES_DEFAULT,
) -> str:
    """Der ganze Injektionstext (leer, wenn nichts zu sagen ist).

    Der Deckel wird nicht geschaetzt, sondern GEMESSEN: es werden so lange
    Bloecke vom Ende in die Pfadliste verschoben, bis der fertige Text unter
    ``gesamt_budget`` liegt. Eine Vorab-Rechnung war um 48 Bytes daneben,
    weil der Ueberlauf-Hinweis selbst Platz braucht — und ein Deckel, der um
    ein bisschen reisst, ist kein Deckel.
    """
    bloecke = [(p, kopf(p, kopf_budget)) for p in matched]
    bloecke = [(p, b) for p, b in bloecke if b]
    if not bloecke:
        return ""
    for n in range(len(bloecke), -1, -1):
        text = _zusammensetzen(
            [b for _, b in bloecke[:n]], [p for p, _ in bloecke[n:]], gesamt_budget
        )
        if len(text.encode()) <= gesamt_budget or n == 0:
            return text
    return ""  # pragma: no cover — die Schleife endet immer bei n == 0


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(event, dict):
        return 0
    prompt = (event.get("prompt") or "").strip()
    if not prompt or ist_system_text(prompt):
        return 0

    kopf_budget = int(os.environ.get("POLICY_KOPF_BYTES") or KOPF_BYTES_DEFAULT)
    if kopf_budget <= 0:
        return 0
    gesamt = int(os.environ.get("POLICY_INJEKTION_BYTES") or GESAMT_BYTES_DEFAULT)

    text = baue_ausgabe(find_matches(prompt, load_triggers()), kopf_budget, gesamt)
    if text:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — fail-open: ein Hook blockiert nie
        sys.exit(0)
