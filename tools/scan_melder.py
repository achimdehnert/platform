#!/usr/bin/env python3
"""scan_melder.py — ein Scan, der nicht ankommt, sieht aus wie ein Scan, den es nie gab.

## Anlass (2026-09-08, doc-hub#3)

Korrektur (2026-09-10): hier stand bis heute, der ScanSnap iX1600 schreibe per SFTP
direkt in den Paperless-Consume-Baum. Das war falsch und ist am 2026-09-08 widerlegt
worden (`smbstatus -b` zeigt die Sitzung, `auth.log` kennt keinen `scansnap`-Login) —
die Lieferung laeuft ueber **Samba**, siehe "Die dritte Messung" unten.

Am 2026-09-07 um 10:19 landete im Consume-Baum `achim/07092026101932.pdf` — eine abgeschnittene
PDF ohne Trailer. Paperless brach die Aufnahme ab (`InputFileError`), **liess die Datei
liegen** und meldete nach aussen nichts. Der Scan davor (10:10) ging durch. Gemerkt hat
es 23 Stunden lang niemand.

Das ist die gefaehrliche Sorte Fehler: sporadisch, still, und fuer den Menschen am
Geraet nicht von "hab ich wohl doch nicht gescannt" zu unterscheiden.

## Was gemessen wird — und warum ohne Datenbank

Paperless entfernt eine Datei aus dem Consume-Baum, sobald sie aufgenommen ist.
**Eine Datei, die noch da liegt, ist nicht aufgenommen** — das ist das ganze Signal,
und es braucht weder Container noch Datenbank. Der Melder misst deshalb nur das
Dateisystem und bleibt auch dann aussagefaehig, wenn der Stack gerade steht.

Die Umkehrung gilt NICHT: eine verschwundene Datei ist nicht automatisch ein
Dokument (jemand kann sie von Hand geloescht haben). Der Melder behauptet darum
nur die eine Richtung, die er wirklich belegt.

## Warum eine Altersschwelle und keine blosse Anwesenheit

Waehrend der Samba-Uebertragung liegt die Datei ebenfalls im Ordner. Ein Melder ohne
Schwelle wuerde jeden laufenden Scan als Befund melden — und damit binnen einer Woche
ignoriert. Paperless nimmt normal in 10-30 s auf (`PAPERLESS_CONSUMER_POLLING_INTERVAL=10`);
30 Minuten Schwelle ist reichlich Luft und trotzdem am selben Tag ein Befund.

## Warum die Ignoranz-Liste aus dem Container kommt

`PAPERLESS_CONSUMER_IGNORE_DIRS` steht auf `["schleuse", ".thumbs"]`, und in
`schleuse/` liegen absichtlich Dateien, die nie aufgenommen werden sollen (Uebergabe
zur/von der Box). Waeren sie hier hartkodiert, ginge die Liste beim naechsten
Compose-Edit auseinander und der Melder meldete auf Dauer denselben Fehlalarm —
die haeufigste Todesursache von Meldern. Er liest sie deshalb aus dem laufenden
Container. Geht das nicht, faellt er auf `IGNORE_DIRS_FALLBACK` zurueck und **sagt
das im Bericht**, statt so zu tun, als haette er gemessen.

## Warum jede haengende Datei genau einmal alarmiert

Der Workflow laeuft stuendlich. Ein taeglicher Alarm ueber dieselbe Datei waere
Rauschen (dieselbe Lehre wie bei `backup-deckung.yml` Exit 3). Statt einen Zustand
mitzuschleppen — der auf einem Runner ohnehin nicht verlaesslich ueberlebt — meldet
`--neu-seit MINUTEN` nur Dateien, deren Alter im **letzten Laufabstand** die Schwelle
ueberschritten hat. Jede Datei faellt so durch genau ein Fenster. Der Lauf selbst
bleibt rot, solange irgendetwas haengt: kein Dauerlaerm, aber auch kein Gruen ueber
einem liegengebliebenen Dokument.

## Datenschutz: die Kurzzeile nennt keine Namen

`--kurz` gibt nur Zahlen aus. Ordner- und Dateinamen stehen ausschliesslich im
Vollbericht, denn dieses Repo ist oeffentlich — und damit sind es auch die
Actions-Logs. Der Workflow ruft nur `--kurz` auf; Details holt sich der Owner lokal.

## Die zweite Haelfte: was verschwindet, ohne ein Dokument zu werden

Am 2026-09-08 verschwand genau die Datei, die den Melder ausgeloest hatte, aus dem
Consume-Baum — ohne dass ein Dokument daraus wurde und ohne eine Zeile im Log
(doc-hub#3). Der Melder oben haette das NICHT gesehen: er misst, was zu lange liegt.

Der naheliegende Weg — den Lieferweg protokollieren — ging ins Leere: die Lieferung
laeuft ueber Samba, nicht ueber SFTP, und ein Protokoll dort waere erneut ein Eingriff
in eine Dienst-Konfiguration auf prod gewesen. Der Melder loest es stattdessen ohne
jeden Host-Eingriff, indem er sich merkt, was er zuletzt gesehen hat.

Jeder Lauf legt ein Inventar der nicht-ignorierten Dateien ab. Im naechsten Lauf gilt:
was im Inventar stand und jetzt fehlt, ist entweder aufgenommen worden — dann gibt es
ein Dokument mit genau diesem `original_filename` — oder es ist **verloren**.

Zwei Dinge machen das belastbar:
  * Gefragt wird nach `original_filename`, nicht nach dem Titel. Paperless benennt
    Dokumente nach Inhalt um (aus einem Blatt wurde "2020-02-01 08092026160835");
    der Originalname bleibt daneben stehen und ist der einzige verlaessliche Schluessel.
  * Ein Verlust ist ein Ereignis, kein Zustand. Er steht nur in EINEM Lauf im Bericht
    (danach ist die Datei aus dem Inventar) — deshalb braucht er kein Alarm-Fenster
    wie die haengenden Dateien, sondern meldet immer sofort.

Grenze, frueher offen benannt, jetzt enger: eine Datei, die zwischen zwei Laeufen kommt
UND geht, faellt durch den Bestandsvergleich durch — aber nicht mehr blind, solange der
Consumer sie ueberhaupt gesehen hat: dann steht sie im Consumer-Log, und die dritte
Messung (naechster Abschnitt) sieht sie unabhaengig vom Lauf-Abstand.

## Die dritte Messung: der Consumer-Log kennt den Fehlschlag sofort

Eine haengende Datei (oben) braucht die Altersschwelle, um sicher zu sein — sie koennte
gerade erst ankommen. Der Consumer-Log weiss es sofort: zu jeder aufgenommenen Datei
schreibt Paperless eine `Consuming <dateiname>`-Zeile mit einer Task-ID in eckigen
Klammern, und zu deren Abschluss entweder `ConsumeTaskPlugin completed with:
{'document_id': N}` oder `ConsumeTaskPlugin failed: ...: <Fehlerklasse>: ` — beide mit
derselben ID. `aufnahmen()` verkettet Start und Abschluss ueber diese ID; eine Datei ohne
Abschluss im selben Log gilt als `offen`, nicht als Fehlschlag.

Der Melder holt dafuer `docker logs iil_dochub_web --since <Fenster>m` (Default siehe
`--log-fenster`, deckt den stuendlichen Takt mit Luft ab) — rein lesend, kein
Host-Eingriff. Eine gescheiterte Beschaffung zaehlt NICHT als "keine Fehlschlaege" (der
gleiche Fehler wie bei der Ignoranz-Liste oben: ein stummer Container darf nicht gruen
aussehen) und steht im Bericht ausdruecklich als nicht gemessen. `--log-fenster 0`
schaltet die Messung bewusst ab (Tests, ein Lauf ohne Docker-Zugriff).

Restluecke, offen benannt: eine Datei, die ankommt und wieder verschwindet, OHNE dass
je eine `Consuming`-Zeile fuer sie im Log erschien, sieht keine der drei Messungen. Nur
ein Schreibprotokoll der Samba-Freigabe (`vfs objects = full_audit`) wuerde das
schliessen — das ist der Eingriff in eine Dienst-Konfiguration auf prod, der am
2026-09-08 nach vier Anlaeufen gescheitert und vollstaendig zurueckgebaut wurde, und
bleibt Owner-Sache.

Exit-Codes
----------
Rangfolge, wenn mehrere Befunde gleichzeitig zutreffen (hoechster Exit-Code gewinnt —
Reihenfolge bewusst so: ein Messfehler geht vor jedem Inhalt, ein endgueltiger Verlust
vor einem noch korrigierbaren Fehlschlag, der wiederum vor dem traegsten Signal steht,
einer bloss lange liegenden Datei):
    2 = blind: eine Wurzel ist nicht lesbar, der Lauf misst nichts Verlaessliches
    4 = Verlust: etwas ist aus dem Inventar verschwunden, ohne ein Dokument zu werden
    5 = Aufnahme fehlgeschlagen: der Consumer-Log zeigt einen Fehlschlag im Fenster
    1 = haengt: mindestens eine Datei liegt laenger als die Schwelle
    0 = sauber: nichts von alledem

Usage
-----
    python3 tools/scan_melder.py                      # Vollbericht (auf prod)
    python3 tools/scan_melder.py --kurz               # eine Zeile, ohne Namen
    python3 tools/scan_melder.py --ssh hetzner-prod   # von der Dev-Maschine
    python3 tools/scan_melder.py --neu-seit 60        # nur frisch haengende melden
    python3 tools/scan_melder.py --log-fenster 0      # Aufnahme-Fehlschlaege nicht messen
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

WURZEL = "/opt/paperless-consume"
CONTAINER = "iil_dochub_web"
SCHWELLE_MIN = 30
# Muss den stuendlichen Takt sicher ueberlappen (sonst Luecke zwischen zwei Laeufen);
# 90 min laesst dem Consumer zusaetzlich Luft fuer einen verspaeteten Lauf.
LOG_FENSTER_MIN = 90
# Liegt auf dem Host, auf dem gemessen wird (prod). Der Actions-Runner checkt je
# Lauf frisch aus; ein Inventar im Arbeitsverzeichnis waere nach jedem Lauf weg.
INVENTAR = "/var/lib/scan-melder/inventar.json"

# Nur Rueckfallposition, wenn der Container nicht antwortet — die Wahrheit steht
# in der Container-Env (siehe Modul-Docstring).
IGNORE_DIRS_FALLBACK = ["schleuse", ".thumbs"]

# Ordner, die Paperless ignoriert, die aber trotzdem beaufsichtigt gehoeren.
# `schleuse/scan-eingang` ist der Eingang des Stapel-Zerlegers (doc-hub#4): dort
# legt der Scanner ab, dort arbeitet ein Timer, und was der liegen laesst,
# faellt sonst durch beide Netze - Paperless sieht den Ordner nicht, und dieser
# Melder sah ihn bis dahin auch nicht.
BEOBACHTET_TROTZ_IGNORANZ = ("schleuse/scan-eingang",)

# Ablagen ausserhalb des Consume-Baums, die trotzdem beaufsichtigt gehoeren.
# `/opt/doc-hub/unklar` nimmt die Stapel auf, die der Zerleger NICHT trennen
# konnte (doc-hub#4). Dort landet etwas genau dann, wenn ein Mensch hinsehen
# muss -- und bis 2026-09-09 sah niemand hin: eine Datei lag dort einen halben
# Tag, ohne dass ein Melder davon wusste.
ZUSATZ_WURZELN = ("/opt/doc-hub/unklar",)


def _lauf(argv: list[str], ssh: str | None) -> tuple[int, str]:
    """Kommando lokal oder ueber ssh ausfuehren. Gibt (rc, stdout+stderr) zurueck.

    Kombiniert bewusst beide Stroeme (2026-09-10, real gemessen gegen prod):
    `docker logs` spiegelt STDOUT des Containers auf sein eigenes STDOUT und
    STDERR des Containers auf sein eigenes STDERR -- Paperless schreibt seinen
    Consumer-Log aber auf STDERR. Ein Melder, der nur STDOUT liest, waere fuer
    `lies_consumer_log` blind, ohne dass rc!=0 das anzeigt (der Container laeuft
    ja, nur die Zeilen landen im falschen Topf). `find`/`docker exec ... env`
    schreiben im Erfolgsfall ohnehin nur auf STDOUT, das Zusammenlegen aendert
    dort nichts.
    """
    if ssh:
        argv = [
            "ssh",
            "-o",
            "ConnectTimeout=8",
            ssh,
            " ".join(shlex.quote(a) for a in argv),
        ]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


# --- reine Auswertung (testbar ohne Host) ----------------------------------


def ignorierte_ordner(env_text: str) -> tuple[list[str], bool]:
    """`PAPERLESS_CONSUMER_IGNORE_DIRS` aus einer `docker exec env`-Ausgabe lesen.

    Zweiter Rueckgabewert sagt, ob die Liste wirklich gemessen wurde. Ein
    Fehlschlag darf nicht wie ein Messergebnis aussehen.
    """
    m = re.search(r"^PAPERLESS_CONSUMER_IGNORE_DIRS=(.*)$", env_text, re.MULTILINE)
    if not m:
        return list(IGNORE_DIRS_FALLBACK), False
    try:
        werte = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return list(IGNORE_DIRS_FALLBACK), False
    if not isinstance(werte, list):
        return list(IGNORE_DIRS_FALLBACK), False
    return [str(w) for w in werte], True


def _ignoriert(
    relpfad: str, ignore_dirs: list[str], beobachtet_trotz: tuple[str, ...] = ()
) -> bool:
    # Ein Ordner kann fuer Paperless ignoriert und trotzdem beaufsichtigt sein:
    # im Eingang des Zerlegers arbeitet ein anderer Dienst, und was der liegen
    # laesst, ist genauso ein Befund wie eine haengende Datei im Consume-Baum
    # (doc-hub#4, A6). Deshalb sticht diese Liste die Ignoranz.
    if any(
        relpfad == p or relpfad.startswith(p.rstrip("/") + "/")
        for p in beobachtet_trotz
    ):
        return False
    teile = Path(relpfad).parts
    ordner = set(teile[:-1])
    if ordner & set(ignore_dirs):
        return True
    # Punktdateien legt kein Scanner ab; sie stammen von Editoren und Sync-Werkzeugen.
    return any(t.startswith(".") for t in teile)


def haengende(
    dateien: list[dict],
    *,
    jetzt: float,
    schwelle_min: int = SCHWELLE_MIN,
    ignore_dirs: list[str] | None = None,
    neu_seit_min: int | None = None,
    beobachtet_trotz: tuple[str, ...] = (),
) -> list[dict]:
    """Dateien, die laenger als die Schwelle im Consume-Baum liegen.

    `neu_seit_min` schneidet oben ab: nur was die Schwelle im letzten Laufabstand
    ueberschritten hat. Ohne den Parameter kommt alles Haengende zurueck.
    """
    ignore_dirs = IGNORE_DIRS_FALLBACK if ignore_dirs is None else ignore_dirs
    unten = schwelle_min * 60
    oben = (schwelle_min + neu_seit_min) * 60 if neu_seit_min is not None else None
    treffer = []
    for d in dateien:
        if _ignoriert(d["pfad"], ignore_dirs, beobachtet_trotz):
            continue
        alter = jetzt - d["mtime"]
        if alter < unten:
            continue
        if oben is not None and alter >= oben:
            continue
        treffer.append({**d, "alter_s": alter})
    return sorted(treffer, key=lambda t: -t["alter_s"])


def _stunden(sekunden: float) -> str:
    return f"{sekunden / 3600:.1f} h"


def verschwundene(vorher: list[dict], jetzt: list[dict]) -> list[dict]:
    """Was im letzten Inventar stand und jetzt fehlt — noch ohne Urteil.

    Ob das ein Verlust ist, entscheidet erst die Frage an Paperless: der Normalfall
    ist, dass eine Datei verschwindet, WEIL sie aufgenommen wurde.
    """
    da = {d["pfad"] for d in jetzt}
    return [v for v in vorher if v["pfad"] not in da]


# Consumer-Log-Zeilenmuster (real beobachtet 2026-09-10, siehe Modul-Docstring).
# Verkettet ueber die Task-ID in eckigen Klammern, die Start und Abschluss verbindet.
_CONSUMING_RE = re.compile(
    r"\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\] \[INFO\] "
    r"\[paperless\.consumer\] \[(?P<tid>[0-9a-f]+)\] Consuming (?P<datei>.+?)\s*$"
)
_ABSCHLUSS_TEXT_RE = re.compile(
    r"\[paperless\.consumer\] \[(?P<tid>[0-9a-f]+)\] Document .* consumption finished"
)
_ABSCHLUSS_ID_RE = re.compile(
    r"\[paperless\.tasks\] \[(?P<tid>[0-9a-f]+)\] ConsumeTaskPlugin completed with: "
    r"\{'document_id': (?P<doc>\d+)\}"
)
_FEHLSCHLAG_RE = re.compile(
    r"\[ERROR\] \[paperless\.tasks\] \[(?P<tid>[0-9a-f]+)\] ConsumeTaskPlugin failed: "
    r"(?P<datei>[^:]+):"
)
_FEHLERKLASSE_RE = re.compile(r"\b([A-Za-z]+Error)\b")


def aufnahmen(log_text: str) -> list[dict]:
    """Consumer-Log in Aufnahme-Datensaetze zerlegen, verkettet ueber die Task-ID.

    Reine Funktion ohne Seiteneffekte (testbar ohne Host). Ein Datensatz je Task-ID
    mit `dateiname`, `start` und `ergebnis`:
      * `fertig`        — mit `document_id`, wenn die maschinenlesbare Abschlusszeile
                           vorkam; sonst ohne (nur die Textzeile war da).
      * `fehlgeschlagen` — mit `fehlerklasse` (z.B. `InputFileError`).
      * `offen`          — `Consuming` gesehen, kein Abschluss im selben Log
                           (Fenster zu knapp oder Log rotiert; kein Fehlschlag).
    """
    eintraege: dict[str, dict] = {}
    reihenfolge: list[str] = []
    for zeile in log_text.splitlines():
        m = _CONSUMING_RE.search(zeile)
        if m:
            tid = m.group("tid")
            if tid not in eintraege:
                reihenfolge.append(tid)
            eintraege[tid] = {
                "dateiname": m.group("datei"),
                "start": m.group("ts"),
                "ergebnis": "offen",
            }
            continue
        m = _ABSCHLUSS_TEXT_RE.search(zeile)
        if m and m.group("tid") in eintraege:
            eintraege[m.group("tid")]["ergebnis"] = "fertig"
            continue
        m = _ABSCHLUSS_ID_RE.search(zeile)
        if m and m.group("tid") in eintraege:
            eintraege[m.group("tid")]["ergebnis"] = "fertig"
            eintraege[m.group("tid")]["document_id"] = int(m.group("doc"))
            continue
        m = _FEHLSCHLAG_RE.search(zeile)
        if m and m.group("tid") in eintraege:
            klassen = _FEHLERKLASSE_RE.findall(zeile)
            eintraege[m.group("tid")]["ergebnis"] = "fehlgeschlagen"
            eintraege[m.group("tid")]["fehlerklasse"] = (
                klassen[-1] if klassen else "unbekannt"
            )
    return [eintraege[tid] for tid in reihenfolge]


def kurzzeile(
    treffer: list[dict],
    *,
    geprueft: int,
    gemessene_ignoranz: bool,
    verluste: list[dict] | None = None,
    fehlgeschlagene: list[dict] | None = None,
    log_gemessen: bool | None = None,
) -> str:
    """Eine Zeile ohne Ordner- und Dateinamen (Repo und Actions-Log sind oeffentlich).

    `log_gemessen`: None = Log-Messung bewusst abgeschaltet (kein Vermerk), False =
    Beschaffung gescheitert (Vermerk), True = gemessen.
    """
    nachsatz = "" if gemessene_ignoranz else " [Ignoranz-Liste nicht gemessen]"
    if log_gemessen is False:
        nachsatz += " [Aufnahme-Log nicht gemessen]"
    vorspann = ""
    if verluste:
        vorspann += f"{len(verluste)} Datei(en) VERLOREN (verschwunden ohne Dokument), "
    if fehlgeschlagene:
        vorspann += f"{len(fehlgeschlagene)} Aufnahme(n) FEHLGESCHLAGEN, "
    if not treffer:
        return (
            f"scan-melder: {vorspann}0 haengende Dateien "
            f"({geprueft} geprueft){nachsatz}"
        )
    return (
        f"scan-melder: {vorspann}{len(treffer)} haengende Datei(en), "
        f"aeltester Eingang vor {_stunden(treffer[0]['alter_s'])} "
        f"({geprueft} geprueft) — "
        f"Details lokal: python3 tools/scan_melder.py --ssh hetzner-prod{nachsatz}"
    )


def bericht(
    treffer: list[dict],
    *,
    geprueft: int,
    gemessene_ignoranz: bool,
    verluste: list[dict] | None = None,
    fehlgeschlagene: list[dict] | None = None,
    log_gemessen: bool | None = None,
) -> str:
    zeilen = [
        kurzzeile(
            treffer,
            geprueft=geprueft,
            gemessene_ignoranz=gemessene_ignoranz,
            verluste=verluste,
            fehlgeschlagene=fehlgeschlagene,
            log_gemessen=log_gemessen,
        )
    ]
    for v in verluste or []:
        zeilen.append(f"  VERLOREN         {v['groesse']:>10} B  {v['pfad']}")
    for f in fehlgeschlagene or []:
        zeilen.append(
            f"  FEHLGESCHLAGEN   {f.get('fehlerklasse', 'unbekannt'):>10}    "
            f"{f['dateiname']}"
        )
    for t in treffer:
        zeilen.append(
            f"  {_stunden(t['alter_s']):>8}  {t['groesse']:>10} B  {t['pfad']}"
        )
    if treffer or verluste or fehlgeschlagene:
        zeilen.append("")
        zeilen.append(
            f'  Ursache je Datei: ssh hetzner-prod "docker logs {CONTAINER} --since 48h'
            ' 2>&1 | grep -i <dateiname>"'
        )
    return "\n".join(zeilen)


# --- Messung ---------------------------------------------------------------


def sammle_zusatz(
    wurzeln: tuple[str, ...], ssh: str | None
) -> tuple[list[dict], list[str]]:
    """Ablagen ausserhalb des Consume-Baums einsammeln.

    Rueckgabe: (Dateien mit absolutem Pfad, nicht lesbare Wurzeln). Der Pfad
    bleibt absolut, damit er sich nicht mit den relativen Pfaden des
    Consume-Baums vermischt und im Bericht sofort erkennbar ist.
    """
    dateien: list[dict] = []
    blind: list[str] = []
    for wurzel in wurzeln:
        teil, lesbar = sammle(wurzel, ssh)
        if not lesbar:
            blind.append(wurzel)
            continue
        for d in teil:
            dateien.append({**d, "pfad": f"{wurzel.rstrip('/')}/{d['pfad']}"})
    return dateien, blind


def sammle(wurzel: str, ssh: str | None) -> tuple[list[dict], bool]:
    """Alle Dateien unter der Wurzel mit mtime und Groesse. Zweiter Wert: lesbar?"""
    rc, out = _lauf(["find", wurzel, "-type", "f", "-printf", "%T@\\t%s\\t%P\\n"], ssh)
    if rc != 0:
        return [], False
    dateien = []
    for zeile in out.splitlines():
        felder = zeile.split("\t", 2)
        if len(felder) != 3:
            continue
        dateien.append(
            {"mtime": float(felder[0]), "groesse": int(felder[1]), "pfad": felder[2]}
        )
    return dateien, True


def lies_ignoranz(ssh: str | None) -> tuple[list[str], bool]:
    rc, out = _lauf(["docker", "exec", CONTAINER, "env"], ssh)
    if rc != 0:
        return list(IGNORE_DIRS_FALLBACK), False
    return ignorierte_ordner(out)


def lies_consumer_log(fenster_min: int, ssh: str | None) -> tuple[str, bool]:
    """Consumer-Log der letzten `fenster_min` Minuten holen. Zweiter Wert: gemessen?

    Ein Fehlschlag ist KEIN "keine Fehlschlaege im Fenster" — sonst wuerde ein
    stummer Container als sauber durchgehen (dieselbe Falle wie `lies_ignoranz`).
    """
    rc, out = _lauf(["docker", "logs", CONTAINER, "--since", f"{fenster_min}m"], ssh)
    if rc != 0:
        return "", False
    return out, True


def aufgenommene(namen: list[str], ssh: str | None) -> tuple[set[str], bool]:
    """Welche dieser Dateinamen sind in Paperless als `original_filename` bekannt?

    Zweiter Rueckgabewert: ob die Frage ueberhaupt beantwortet wurde. Ein stummer
    Container darf NICHT als "kein Dokument gefunden" durchgehen — daraus wuerde der
    Melder einen Verlust erfinden.
    """
    if not namen:
        return set(), True
    skript = (
        "from documents.models import Document\n"
        f"namen = {namen!r}\n"
        "for n in Document.objects.filter(original_filename__in=namen)"
        ".values_list('original_filename', flat=True):\n"
        "    print('TREFFER', n)\n"
    )
    argv = ["docker", "exec", "-i", CONTAINER, "python3", "manage.py", "shell"]
    if ssh:
        argv = [
            "ssh",
            "-o",
            "ConnectTimeout=8",
            ssh,
            " ".join(shlex.quote(a) for a in argv),
        ]
    p = subprocess.run(argv, input=skript, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return set(), False
    return {
        z.split(" ", 1)[1] for z in p.stdout.splitlines() if z.startswith("TREFFER ")
    }, True


def lade_inventar(pfad: Path) -> list[dict]:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))["dateien"]
    except (OSError, json.JSONDecodeError, KeyError):
        return []


def schreibe_inventar(pfad: Path, dateien: list[dict]) -> bool:
    """Inventar fortschreiben. False, wenn der Ort nicht beschreibbar ist.

    Der im Workflow dokumentierte Owner-Weg (`--ssh hetzner-prod`) laeuft auf
    einem Rechner, der `/var/lib/scan-melder` nicht anlegen darf. Bis 2026-09-10
    brach der Lauf dort mit `PermissionError` ab -- BEVOR der Bericht gedruckt
    war. Der Melder verschwieg damit genau das, wofuer er gebaut ist. Ein nicht
    beschreibbares Inventar ist ein Hinweis, kein Grund, den Befund zu verlieren.
    """
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(
            json.dumps(
                {"gemessen_am": time.time(), "dateien": dateien},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--wurzel", default=WURZEL)
    p.add_argument(
        "--ssh", default=None, help="Host-Alias, wenn nicht auf prod gelaufen wird"
    )
    p.add_argument(
        "--schwelle", type=int, default=SCHWELLE_MIN, help="Minuten (Default 30)"
    )
    p.add_argument(
        "--neu-seit",
        type=int,
        default=None,
        metavar="MINUTEN",
        help="nur Dateien melden, die die Schwelle im letzten Laufabstand ueberschritten haben",
    )
    p.add_argument(
        "--inventar",
        default=INVENTAR,
        help="Pfad des Bestandsvergleichs; leer ('') schaltet die Verlust-Erkennung ab",
    )
    p.add_argument(
        "--auch",
        action="append",
        default=None,
        metavar="RELPFAD",
        help=(
            "Ordner, der trotz PAPERLESS_CONSUMER_IGNORE_DIRS beaufsichtigt wird "
            f"(Default: {', '.join(BEOBACHTET_TROTZ_IGNORANZ)})"
        ),
    )
    p.add_argument(
        "--zusatz-wurzel",
        action="append",
        default=list(ZUSATZ_WURZELN),
        metavar="PFAD",
        help=(
            "Ablage ausserhalb des Consume-Baums, die mitbeaufsichtigt wird "
            f"(Default: {', '.join(ZUSATZ_WURZELN)})"
        ),
    )
    p.add_argument(
        "--log-fenster",
        type=int,
        default=LOG_FENSTER_MIN,
        metavar="MINUTEN",
        help=(
            "Consumer-Log der letzten MINUTEN auf Aufnahme-Fehlschlaege pruefen "
            f"(Default {LOG_FENSTER_MIN}, ueberlappt den stuendlichen Takt); "
            "0 schaltet die Messung ab"
        ),
    )
    p.add_argument("--kurz", action="store_true")
    a = p.parse_args(argv)

    dateien, lesbar = sammle(a.wurzel, a.ssh)
    zusatz, blinde_wurzeln = sammle_zusatz(tuple(a.zusatz_wurzel), a.ssh)
    dateien += zusatz
    for w in blinde_wurzeln:
        print(f"scan-melder: {w} nicht lesbar — blind, nicht gruen", file=sys.stderr)
    if not lesbar:
        print(
            f"scan-melder: {a.wurzel} nicht lesbar — blind, nicht gruen",
            file=sys.stderr,
        )
        return 2

    ignore_dirs, gemessen = lies_ignoranz(a.ssh)
    trotz = tuple(a.auch if a.auch is not None else BEOBACHTET_TROTZ_IGNORANZ)
    beobachtet = [d for d in dateien if not _ignoriert(d["pfad"], ignore_dirs, trotz)]
    treffer = haengende(
        dateien,
        jetzt=time.time(),
        schwelle_min=a.schwelle,
        ignore_dirs=ignore_dirs,
        neu_seit_min=a.neu_seit,
        beobachtet_trotz=trotz,
    )

    # Im Eingang des Zerlegers ist Verschwinden der NORMALFALL - er nimmt die
    # Stapel weg und legt statt ihrer die Einzeldokumente ab, unter anderen
    # Namen. Die Frage an Paperless ("gibt es ein Dokument dieses Namens?")
    # wuerde dort jedes Mal Nein sagen und einen Verlust melden, der keiner
    # ist. Fuer den Eingang gilt deshalb nur "liegt zu lange"; sein
    # Bestandsvergleich fuehrt der Zerleger selbst in seinem Ledger.
    bestand = [
        d
        for d in beobachtet
        if not any(d["pfad"].startswith(t.rstrip("/") + "/") for t in trotz)
        and not any(d["pfad"].startswith(w.rstrip("/") + "/") for w in a.zusatz_wurzel)
    ]

    verluste: list[dict] = []
    if a.inventar:
        pfad = Path(a.inventar)
        weg = verschwundene(lade_inventar(pfad), bestand)
        namen = [Path(v["pfad"]).name for v in weg]
        gefunden, beantwortet = aufgenommene(namen, a.ssh)
        if not beantwortet:
            print(
                "scan-melder: Paperless antwortet nicht — Verlust-Frage unbeantwortet, "
                "kein Urteil",
                file=sys.stderr,
            )
        else:
            verluste = [v for v in weg if Path(v["pfad"]).name not in gefunden]
        # Nur schreiben, wenn beurteilt wurde: sonst faellt ein unbeantworteter Lauf
        # das Inventar zurueck und der naechste Lauf haelt den Verlust fuer erledigt.
        if beantwortet and not schreibe_inventar(pfad, bestand):
            print(
                f"scan-melder: Inventar {pfad} nicht beschreibbar — der naechste "
                "Lauf kann keinen Verlust erkennen",
                file=sys.stderr,
            )

    fehlgeschlagene: list[dict] = []
    log_gemessen: bool | None = None
    if a.log_fenster:
        log_text, log_ok = lies_consumer_log(a.log_fenster, a.ssh)
        log_gemessen = log_ok
        if not log_ok:
            print(
                "scan-melder: Consumer-Log nicht erreichbar — Aufnahme-Fehlschlaege "
                "nicht gemessen, kein Urteil",
                file=sys.stderr,
            )
        else:
            fehlgeschlagene = [
                e for e in aufnahmen(log_text) if e["ergebnis"] == "fehlgeschlagen"
            ]

    if a.kurz:
        print(
            kurzzeile(
                treffer,
                geprueft=len(beobachtet),
                gemessene_ignoranz=gemessen,
                verluste=verluste,
                fehlgeschlagene=fehlgeschlagene,
                log_gemessen=log_gemessen,
            )
        )
    else:
        print(
            bericht(
                treffer,
                geprueft=len(beobachtet),
                gemessene_ignoranz=gemessen,
                verluste=verluste,
                fehlgeschlagene=fehlgeschlagene,
                log_gemessen=log_gemessen,
            )
        )
    # Rangfolge siehe Modul-Docstring: 2 (frueher return) > 4 > 5 > 1 > 0.
    if verluste:
        return 4
    if fehlgeschlagene:
        return 5
    return 1 if treffer else 0


if __name__ == "__main__":
    raise SystemExit(main())
