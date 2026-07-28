"""Deckungsausweis — was eine Mail-Antwort abgedeckt hat (KONZ-platform-035, REC-1/REC-2).

Eine Antwort aus dem Postfach sagt heute, *was* gefunden wurde. Sie sagt nicht, *worin*
gesucht wurde. Genau daran sind am 2026-07-27 drei Darstellungen gescheitert: ein
Absender-Platzhalter verwarf 21 von 34 gesendeten Nachrichten still, ein Sachverhalt wurde
aus dem Posteingang allein dargelegt (3 von 11 Nachrichten), und eine Liste nannte einen
Zähler ohne Nenner.

Dieses Modul erzeugt den Ausweis als **versioniertes Objekt** und rendert ihn sekundär als
Text. Der Grund für diese Reihenfolge steht in KONZ-035 §5.2: ein Textblock, den fünf Skills
je selbst formulieren, ist die Doppelquelle, die die SSoT-Konvention verbietet.

Das Modul weiß nichts über IMAP oder Graph. Es zählt nicht selbst — es nimmt entgegen, was
ein Aufrufer gezählt hat, und entscheidet daraus, ob eine Vollständigkeitsaussage zulässig
ist. Deshalb ist es ohne Postfach testbar.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import NamedTuple

FORMAT_VERSION = "deckungsausweis.v1"

#: Wortlaut aus KONZ-035 §5.3 R-5. Steht hier einmal, nicht in fünf Skills.
SPERRSATZ = "Dieser Ausweis erlaubt keine Vollständigkeitsaussage."

#: KONZ-035 §7.2 (K6). Muss im Ausweis stehen, nicht nur im Konzept — sonst liest sich
#: „Deckung vollständig" als „alles Relevante gefunden". Garantiert wird der untersuchte
#: Bereich; ob ein Treffer zur Frage gehört, entscheidet der Mensch.
GARANTIEGRENZE = (
    "Gedeckt ist der ausgewiesene Suchraum — nicht die Relevanz. "
    "Ob eine Nachricht zur Frage gehört, entscheidet der Mensch."
)


class Ausweis(NamedTuple):
    """Ein Deckungsausweis nach KONZ-035 §5.2.

    NamedTuple statt dataclass, weil die Testsuite die Module über
    ``spec_from_file_location`` lädt — dabei ist ``__module__`` nicht importierbar,
    woran der dataclass-Decorator scheitert.
    """

    frage: str
    anlass: str

    # L1 — Suchraum, zwei Ebenen (§5.3 R-1)
    konten_vorhanden: int
    konten_durchsucht: int
    ordner_vorhanden: int
    ordner_durchsucht: int

    # L3 — Erfassungs-Konsistenz: der Postfachzustand ist ein Intervall, kein Punkt
    scan_started_at: str
    scan_finished_at: str
    source_watermark: str

    # L2 — Retrieval: ein Pfad mit 0 Treffern ist ein Befund (§5.3 R-2)
    retrievalpfade: tuple[tuple[str, int], ...]
    kalibriert: tuple[str, ...]

    # L3 — ohne diese Felder ist "durchsucht" semantisch unbestimmt
    ordner_fehlgeschlagen: int = 0
    timeouts: int = 0
    berechtigungsfehler: int = 0
    seiten_unvollstaendig: int = 0

    # Trunkierung
    geprueft: int = 0
    vorhanden: int = 0

    nicht_gedeckt: tuple[tuple[str, str], ...] = ()

    #: REC-9 — Ordner, in denen die eigene Aufzählung und die Server-Zählung
    #: auseinanderlaufen: (ordner, server_sagt, selbst_gezaehlt).
    nenner_divergenz: tuple[tuple[str, int, int], ...] = ()

    query_fingerprint: str = ""
    tool_version: str = ""
    format_version: str = FORMAT_VERSION

    erzeuger: str = "maschinell"
    fallback_grund: str | None = None


def fingerprint(*teile: object) -> str:
    """Stabile Kurz-Kennung der Abfrage.

    Zwei Ausweise sind nur vergleichbar, wenn dieselbe Frage dieselbe Kennung ergibt —
    deshalb kanonisch serialisieren statt ``str()`` über eine Menge, deren Reihenfolge
    zwischen Läufen wechselt.
    """
    roh = json.dumps([_kanonisch(t) for t in teile], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()[:16]


def _kanonisch(wert: object) -> object:
    if isinstance(wert, (set, frozenset)):
        return sorted(str(w) for w in wert)
    if isinstance(wert, dict):
        return {str(k): _kanonisch(v) for k, v in wert.items()}
    if isinstance(wert, (list, tuple)):
        return [_kanonisch(w) for w in wert]
    return wert


def leere_pfade(ausweis: Ausweis) -> list[str]:
    """Retrievalpfade ohne Treffer — **und ohne bestandene Kalibrierung**.

    Im Gesamtergebnis sind sie unsichtbar: ein Pfad, der nichts liefert, während ein
    anderer trifft, sieht aus wie "es gab eben nicht mehr". Er ist aber meistens eine
    kaputte Abfrage.

    Ein *kalibrierter* Pfad mit null Treffern ist dagegen ein belegtes Ergebnis: er hat
    gerade gezeigt, dass er findet, was da ist. Ihn trotzdem zu melden, erzeugt eine
    Warnung ohne Inhalt — und Warnungen ohne Inhalt sind der Weg, auf dem die mit Inhalt
    übersehen werden. Aufgetreten im ersten Pilotlauf gegen das AD-Konto, wo die
    Leermenge echt war.
    """
    kalibriert = set(ausweis.kalibriert)
    return [
        name
        for name, treffer in ausweis.retrievalpfade
        if treffer == 0 and name not in kalibriert
    ]


def unkalibrierte_pfade(ausweis: Ausweis) -> list[str]:
    """Verwendete Pfade, für die keine bekannte Nachricht wiedergefunden wurde (§5.3 R-3)."""
    kal = set(ausweis.kalibriert)
    return [name for name, _ in ausweis.retrievalpfade if name not in kal]


def divergenz(treffer: dict[str, set]) -> list[tuple[str, str, int]]:
    """Was ein Pfad fand und ein anderer nicht (KONZ-035 §5.3 R-2).

    Genau hier liegt der Wert zweier verschiedenartiger Pfade: nicht in der größeren
    Gesamtmenge, sondern in der Differenz. Findet ein Pfad nichts, wo ein anderer
    trifft, ist das eine Aussage über die Abfrage — nicht über den Bestand.

    Rückgabe je Paar: (pfad_mit_treffern, pfad_ohne, anzahl_der_differenz). Nur
    Richtungen mit echter Differenz erscheinen.
    """
    raus: list[tuple[str, str, int]] = []
    for a, menge_a in sorted(treffer.items()):
        for b, menge_b in sorted(treffer.items()):
            if a == b:
                continue
            if nur_a := menge_a - menge_b:
                raus.append((a, b, len(nur_a)))
    return raus


def nenner_pruefen(
    selbst: dict[str, int], server: dict[str, int]
) -> list[tuple[str, int, int]]:
    """Eigene Aufzählung gegen die Zählung des Servers (KONZ-035 REC-9).

    Der Nenner eines Deckungsausweises war bisher selbstreferenziell: er entstand aus
    derselben Aufzählung, deren Vollständigkeit er belegen sollte. Eine zweite,
    unabhängig erhobene Zahl (``STATUS (MESSAGES)`` bzw. ``totalItemCount``) bricht
    diesen Zirkel.

    Ordner, für die der Server keine Zahl liefert, sind **keine** Divergenz — nur eine
    fehlende Gegenprobe; sie erscheinen nicht in der Liste.
    """
    return [
        (ordner, server[ordner], anzahl)
        for ordner, anzahl in sorted(selbst.items())
        if ordner in server and server[ordner] != anzahl
    ]


def vollstaendigkeitsaussage_zulaessig(ausweis: Ausweis) -> tuple[bool, list[str]]:
    """Darf auf Basis dieses Ausweises "vollständig" behauptet werden?

    Gibt neben dem Urteil die **Gründe** zurück, damit der Aufrufer sie ausgeben kann,
    statt ein nacktes ``False`` zu interpretieren. Die Bedingungen stammen aus §5.3:
    R-1 (Scope vollständig), R-3 (jeder verwendete Pfad kalibriert), R-5 (maschinell)
    plus die L3-Felder, ohne die "durchsucht" nichts bedeutet.
    """
    gruende: list[str] = []

    if ausweis.erzeuger != "maschinell":
        gruende.append(f"Handbetrieb ({ausweis.fallback_grund or 'ohne Grund'}) — R-5")
    if not ausweis.retrievalpfade:
        gruende.append("kein Retrievalpfad ausgewiesen")
    if fehlend := unkalibrierte_pfade(ausweis):
        gruende.append("nicht kalibriert: " + ", ".join(fehlend) + " — R-3")
    if ausweis.konten_durchsucht < ausweis.konten_vorhanden:
        gruende.append(
            f"Konten {ausweis.konten_durchsucht}/{ausweis.konten_vorhanden} — R-1"
        )
    if ausweis.ordner_durchsucht < ausweis.ordner_vorhanden:
        gruende.append(
            f"Ordner {ausweis.ordner_durchsucht}/{ausweis.ordner_vorhanden} — R-1"
        )
    if ausweis.ordner_fehlgeschlagen or ausweis.timeouts or ausweis.berechtigungsfehler:
        gruende.append(
            f"unvollständig gelesen: {ausweis.ordner_fehlgeschlagen} Ordner, "
            f"{ausweis.timeouts} Timeouts, {ausweis.berechtigungsfehler} Rechte-Fehler"
        )
    if ausweis.seiten_unvollstaendig:
        gruende.append(f"{ausweis.seiten_unvollstaendig} Seite(n) abgeschnitten")
    if ausweis.vorhanden and ausweis.geprueft < ausweis.vorhanden:
        gruende.append(f"geprüft {ausweis.geprueft}/{ausweis.vorhanden}")
    if ausweis.nenner_divergenz:
        gruende.append(
            f"Nenner uneinig in {len(ausweis.nenner_divergenz)} Ordner(n) — REC-9"
        )

    return (not gruende), gruende


def pruefkette(ausweis: Ausweis) -> tuple[bool, list[str]]:
    """Die maschinell prüfbare Bedingungskette aus KONZ-035 §6.1 (K8/REC-8).

    Bewusst enger als :func:`vollstaendigkeitsaussage_zulaessig`: geprüft wird das
    **Verfahren**, nicht das Ergebnis. Ein knapper Scope ist zulässig — aber nur, wenn
    die Verengung benannt und begründet dasteht. Genau das ist der Unterschied zwischen
    „ich habe wenig durchsucht und sage es" und „ich habe wenig durchsucht".

    Nicht prüfbar bleiben Angemessenheit der Frage und Relevanz der Treffer; beide liegen
    ohnehin beim Menschen. Der ehrliche Satz lautet: **Exit-Code für das Verfahren,
    Urteil für den Inhalt.**
    """
    fehler: list[str] = []
    begruendet = bool(ausweis.nicht_gedeckt)

    if ausweis.erzeuger != "maschinell":
        fehler.append("erzeuger ist nicht 'maschinell'")
    if ausweis.ordner_durchsucht < ausweis.ordner_vorhanden and not begruendet:
        fehler.append(
            f"Ordner {ausweis.ordner_durchsucht}/{ausweis.ordner_vorhanden} "
            "ohne Eintrag in nicht_gedeckt"
        )
    if ausweis.konten_durchsucht < ausweis.konten_vorhanden and not begruendet:
        fehler.append(
            f"Konten {ausweis.konten_durchsucht}/{ausweis.konten_vorhanden} "
            "ohne Eintrag in nicht_gedeckt"
        )
    if ausweis.ordner_fehlgeschlagen and not begruendet:
        fehler.append(
            f"{ausweis.ordner_fehlgeschlagen} unlesbare Ordner ohne Eintrag in nicht_gedeckt"
        )
    if offen := unkalibrierte_pfade(ausweis):
        fehler.append("unkalibrierte Pfade: " + ", ".join(offen))
    if fehlend := [
        name
        for name, wert in (
            ("frage", ausweis.frage),
            ("source_watermark", ausweis.source_watermark),
            ("query_fingerprint", ausweis.query_fingerprint),
            ("tool_version", ausweis.tool_version),
        )
        if not wert
    ]:
        fehler.append("Pflichtfelder leer: " + ", ".join(fehlend))

    return (not fehler), fehler


def aus_dict(daten: dict) -> Ausweis:
    """Ein serialisierter Ausweis zurück in das Objekt — Gegenstück zu :func:`als_dict`.

    Nötig, damit die Prüfkette gegen einen Ausweis laufen kann, den ein anderer Prozess
    erzeugt hat (Hook, CI, archivierte Antwort).
    """
    felder = {k: daten[k] for k in Ausweis._fields if k in daten}
    felder["retrievalpfade"] = tuple(
        (k, v) for k, v in sorted(daten.get("retrievalpfade", {}).items())
    )
    felder["kalibriert"] = tuple(daten.get("kalibriert", ()))
    felder["nicht_gedeckt"] = tuple(
        (e["was"], e["grund"]) for e in daten.get("nicht_gedeckt", ())
    )
    felder["nenner_divergenz"] = tuple(
        (e["ordner"], e["server"], e["selbst"])
        for e in daten.get("nenner_divergenz", ())
    )
    return Ausweis(**felder)


def als_dict(ausweis: Ausweis) -> dict:
    """Das versionierte Objekt. Primär — der Text unten ist sein Rendering."""
    d = ausweis._asdict()
    d["retrievalpfade"] = dict(ausweis.retrievalpfade)
    d["kalibriert"] = list(ausweis.kalibriert)
    d["nicht_gedeckt"] = [{"was": w, "grund": g} for w, g in ausweis.nicht_gedeckt]
    d["nenner_divergenz"] = [
        {"ordner": o, "server": s, "selbst": e} for o, s, e in ausweis.nenner_divergenz
    ]
    zulaessig, gruende = vollstaendigkeitsaussage_zulaessig(ausweis)
    d["vollstaendigkeitsaussage_zulaessig"] = zulaessig
    d["einschraenkungen"] = gruende
    return d


def rendern(ausweis: Ausweis) -> str:
    """Sekundäres Text-Rendering — ein Renderer für alle Skills (§5.2)."""
    zulaessig, gruende = vollstaendigkeitsaussage_zulaessig(ausweis)
    pfade = ", ".join(f"{n}: {t}" for n, t in ausweis.retrievalpfade) or "—"

    zeilen = [
        f"Deckungsausweis ({ausweis.format_version})",
        f"  Frage      {ausweis.frage}",
        f"  Anlass     {ausweis.anlass}",
        (
            f"  Konten     {ausweis.konten_durchsucht}/{ausweis.konten_vorhanden}"
            f"   Ordner {ausweis.ordner_durchsucht}/{ausweis.ordner_vorhanden}"
        ),
        (
            f"  Zeitraum   {ausweis.scan_started_at} → {ausweis.scan_finished_at}"
            f"  (Stand {ausweis.source_watermark})"
        ),
        f"  Pfade      {pfade}",
    ]

    if unauffaellig := leere_pfade(ausweis):
        zeilen.append(
            "  ⚠ ohne Treffer: "
            + ", ".join(unauffaellig)
            + " — eher kaputte Abfrage als leere Menge"
        )

    stoerungen = (
        ausweis.ordner_fehlgeschlagen
        + ausweis.timeouts
        + ausweis.berechtigungsfehler
        + ausweis.seiten_unvollstaendig
    )
    if stoerungen:
        zeilen.append(
            f"  Störungen  {ausweis.ordner_fehlgeschlagen} Ordner unlesbar, "
            f"{ausweis.timeouts} Timeouts, {ausweis.berechtigungsfehler} Rechte-Fehler, "
            f"{ausweis.seiten_unvollstaendig} Seiten abgeschnitten"
        )

    for ordner, server, selbst in ausweis.nenner_divergenz:
        zeilen.append(
            f"  ⚠ Nenner uneinig [{ordner}]: Server {server}, selbst gezählt {selbst}"
        )

    for was, grund in ausweis.nicht_gedeckt:
        zeilen.append(f"  nicht gedeckt: {was} — {grund}")

    if zulaessig:
        zeilen.append("  ✓ Deckung vollständig im ausgewiesenen Scope.")
    else:
        zeilen.append("  ✗ Keine Vollständigkeitsaussage:")
        zeilen.extend(f"      · {g}" for g in gruende)

    if ausweis.erzeuger != "maschinell":
        zeilen.append(f"  {SPERRSATZ}")

    zeilen.append(f"  {GARANTIEGRENZE}")
    zeilen.append(
        f"  Kennung    {ausweis.query_fingerprint}  Werkzeug {ausweis.tool_version}"
    )
    return "\n".join(zeilen)


def main() -> int:
    """Prüfkette gegen einen serialisierten Ausweis — Exit 1 bei Verstoß (K8).

    Liest den Ausweis als JSON von der Standardeingabe, damit ein Hook oder ein
    CI-Schritt ihn prüfen kann, ohne dieses Modul zu importieren.
    """
    import argparse

    ap = argparse.ArgumentParser(
        description="Deckungsausweis gegen KONZ-035 §6.1 prüfen"
    )
    ap.add_argument(
        "--pruefen",
        action="store_true",
        required=True,
        help="Ausweis als JSON von stdin lesen und die Bedingungskette prüfen",
    )
    ap.parse_args()

    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"✗ kein lesbarer Ausweis auf stdin: {exc}", file=sys.stderr)
        return 2

    if daten.get("format_version") != FORMAT_VERSION:
        print(
            f"✗ unbekanntes Format: {daten.get('format_version')!r} "
            f"(erwartet {FORMAT_VERSION})",
            file=sys.stderr,
        )
        return 2

    try:
        ausweis = aus_dict(daten)
    except (KeyError, TypeError) as exc:
        print(f"✗ Ausweis unvollständig: {exc}", file=sys.stderr)
        return 2

    ok, fehler = pruefkette(ausweis)
    for f in fehler:
        print(f"✗ {f}", file=sys.stderr)
    print("Verfahren eingehalten" if ok else "Verfahren verletzt")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
