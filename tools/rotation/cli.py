"""Unterbefehle von ``tools/rotate.py``.

Die Kette (§5.5) ist fest verdrahtet und hat keine Verzweigung:

    lesen → je Konsument setzen → je Konsument belegen → Log-Zeile → Schleuse leeren

Vier Dinge sind daran wichtiger als sie aussehen:

* **Schleuse zuletzt.** Erst wenn der letzte Beleg vorliegt und die Quelldatei
  noch byte-gleich zu dem ist, was gesetzt wurde, wird sie geloescht (MT-1).
  Ein frueh geleerter Ordner nimmt dem Menschen den einzigen Rueckweg.
* **Kein Rollback.** Werte sind nicht zurueckzulesen; ein roter Beleg laesst den
  Lauf ``offen`` und sagt das.
* **Ohne Beleg = nicht gesetzt.** Ein Konsument ohne ``proof`` wird gezaehlt und
  genannt, nicht uebersprungen (AD-3).
* **Kein Wert.** Weder ``pruefen`` noch ``lauf`` geben je den Wert aus; jede
  Log-Zeile laeuft vorher durch den Filter.
"""

from __future__ import annotations

import argparse
import getpass
import json
from datetime import date, datetime, timezone
from pathlib import Path

from . import fingerprint, inventar
from . import log as rotlog
from .treiber_github import GithubTreiber, GovOrgAbgelehnt, TreiberFehler


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# pruefen — Pflicht-Vorstufe, liest nur
# --------------------------------------------------------------------------
def cmd_pruefen(a: argparse.Namespace) -> int:
    inv = inventar.lade(a.inventar)
    try:
        secret = inventar.finde(inv, a.secret)
    except KeyError as fehler:
        print(f"✗ {fehler}")
        return 2
    eintraege = rotlog.lies(a.log)
    letzter = rotlog.letzter_lauf(secret.name, eintraege)

    print(f"{secret.sektion}.{secret.name}")
    print(f"  {secret.eintrag.get('description', '(ohne Beschreibung)')}")
    print()
    print(f"Konsumenten          : {len(secret.konsumenten)}")
    print(f"davon ohne Beleg     : {len(secret.ohne_beleg)}")
    print(f"Rotationsfrist       : {inventar.naechste_frist(secret, letzter)}")
    if letzter:
        print(
            f"letzter Lauf         : {letzter.get('lauf_id')} "
            f"({letzter.get('status')}, {letzter.get('gestartet')})"
        )
    else:
        print("letzter Lauf         : keiner im Log")
    print(
        "HMAC-Schluessel      : "
        + ("vorhanden" if fingerprint.schluessel_vorhanden() else "FEHLT — `lauf` bricht ab")
    )
    print()
    for zeile in inventar.formatiere_konsumenten(secret.konsumenten):
        print(zeile)
    if secret.ohne_beleg:
        print()
        print(
            f"! {len(secret.ohne_beleg)} von {len(secret.konsumenten)} Konsumenten haben keinen "
            "Beleg. Sie werden NICHT gesetzt — Setzen ohne Beleg gilt als nicht gesetzt."
        )
    return 0


# --------------------------------------------------------------------------
# lauf — die Kette
# --------------------------------------------------------------------------
def cmd_lauf(a: argparse.Namespace, treiber=None) -> int:
    inv = inventar.lade(a.inventar)
    try:
        secret = inventar.finde(inv, a.secret)
    except KeyError as fehler:
        print(f"✗ {fehler}")
        return 2

    try:
        schluessel = fingerprint.lade_schluessel(a.hmac_schluessel)
    except fingerprint.SchluesselFehlt as fehler:
        print(f"✗ {fehler}")
        return 3

    quelle = Path(a.quelle).expanduser()
    if not quelle.is_file():
        print(f"✗ Quelldatei nicht gefunden: {quelle}")
        return 2
    wert = inventar.quelle_lesen(quelle)
    pruefsumme_start = fingerprint.datei_pruefsumme(quelle)
    abdruck = fingerprint.fingerabdruck(wert, schluessel)

    ziele = [k for k in secret.konsumenten if not a.nur or k.ref == a.nur]
    if a.nur and not ziele:
        print(f"✗ --nur {a.nur} passt auf keinen Konsumenten von {secret.name}")
        return 2

    treiber = treiber or GithubTreiber()
    eintraege = rotlog.lies(a.log)
    heute = date.today().isoformat()
    lauf_id = rotlog.naechste_lauf_id(secret.name, eintraege, heute)
    gestartet = _jetzt()

    print(f"Lauf {lauf_id} — {len(ziele)} Konsument(en), Fingerabdruck {abdruck}")
    ergebnisse: list[dict] = []
    for konsument in ziele:
        zeile = {"ref": konsument.ref, "kind": konsument.kind}
        if not konsument.rotierbar:
            grund = "alte String-Form" if konsument.unvollstaendig else "ohne proof"
            zeile.update(ergebnis="ohne_beleg", negativprobe=False, hinweis=grund)
            print(f"  – {konsument.ref}: nicht gesetzt ({grund})")
            ergebnisse.append(zeile)
            continue
        if konsument.kind != treiber.kind:
            zeile.update(
                ergebnis="ohne_beleg",
                negativprobe=False,
                hinweis=f"kein Treiber fuer {konsument.kind} (Stufe 2)",
            )
            print(f"  – {konsument.ref}: kein Treiber fuer {konsument.kind} — Stufe 2")
            ergebnisse.append(zeile)
            continue
        try:
            treiber.setze(konsument.ref, konsument.name or secret.name, wert)
            beleg = treiber.belege(
                konsument.ref, konsument.proof or {}, konsument.name or secret.name
            )
        except GovOrgAbgelehnt as fehler:
            zeile.update(ergebnis="abgelehnt", negativprobe=False, hinweis=str(fehler)[:160])
            print(f"  ⛔ {konsument.ref}: {fehler}")
            ergebnisse.append(zeile)
            continue
        except TreiberFehler as fehler:
            zeile.update(ergebnis="rot", negativprobe=False, hinweis=str(fehler)[:160])
            print(f"  ✗ {konsument.ref}: {fehler}")
            ergebnisse.append(zeile)
            continue
        zeile.update(
            ergebnis=beleg.ergebnis,
            negativprobe=beleg.negativprobe,
            lauf_url=beleg.lauf_url,
            hinweis=beleg.hinweis,
        )
        zeichen = {"ok": "✓", "rot": "✗", "ohne_beleg": "–"}.get(beleg.ergebnis, "?")
        negativ = "mit Negativprobe" if beleg.negativprobe else "OHNE Negativprobe"
        print(f"  {zeichen} {konsument.ref}: {beleg.ergebnis} ({negativ})")
        ergebnisse.append(zeile)

    status = (
        "abgeschlossen"
        if ergebnisse and all(e["ergebnis"] == "ok" for e in ergebnisse)
        else "offen"
    )

    # Schleuse zuletzt — und nur bei Gleichheit: hat sich die Datei seit dem
    # Lesen geaendert, wurde etwas anderes gesetzt als das, was jetzt daliegt.
    schleuse_geleert = False
    if status == "abgeschlossen":
        if fingerprint.datei_pruefsumme(quelle) == pruefsumme_start:
            quelle.unlink()
            schleuse_geleert = True
            print(f"  Schleuse geleert: {quelle}")
        else:
            print(f"  ! {quelle} hat sich waehrend des Laufs geaendert — NICHT geloescht.")

    zeile = {
        "lauf_id": lauf_id,
        "secret": secret.name,
        "sektion": secret.sektion,
        "gestartet": gestartet,
        "beendet": _jetzt(),
        "ausgefuehrt_von": a.ausgefuehrt_von or getpass.getuser(),
        "kind": "werkzeug",
        "status": status,
        "fingerprint_alg": fingerprint.ALGORITHMUS,
        "fingerprint_prefix16": abdruck,
        "konsumenten": ergebnisse,
        "schleuse_geleert": schleuse_geleert,
    }
    rotlog.schreibe(zeile, a.log)
    print(f"\nStatus: {status} — Log-Zeile geschrieben ({a.log or rotlog.LOG_PFAD}).")
    if status != "abgeschlossen":
        print(
            "Kein Rollback: Werte sind nicht zurueckzulesen. Der Lauf bleibt offen, "
            "die Schleuse bleibt gefuellt."
        )
    return 0 if status == "abgeschlossen" else 1


# --------------------------------------------------------------------------
# widerruf-geprueft — Negativprobe NACH dem menschlichen Widerruf
# --------------------------------------------------------------------------
def cmd_widerruf_geprueft(a: argparse.Namespace, treiber=None) -> int:
    eintraege = rotlog.lies(a.log)
    passend = [e for e in eintraege if e.get("lauf_id") == a.lauf_id]
    if not passend:
        print(f"✗ Lauf {a.lauf_id} steht nicht im Log.")
        return 2
    lauf = passend[-1]
    treiber = treiber or GithubTreiber()

    print(f"Negativprobe zu {a.lauf_id} ({lauf.get('secret')})")
    print("Der Widerruf des alten Werts ist ein Mensch-Schritt (Gate 1) — hier wird")
    print("nur geprueft, ob er stattgefunden hat. Es wird keine Delete-API gerufen.")
    inv = inventar.lade(a.inventar)
    try:
        secret = inventar.finde(inv, lauf.get("secret", ""))
    except KeyError as fehler:
        print(f"✗ {fehler}")
        return 2

    befunde = []
    for konsument in secret.konsumenten:
        if not konsument.rotierbar or konsument.kind != treiber.kind:
            continue
        try:
            beleg = treiber.belege(
                konsument.ref, konsument.proof or {}, konsument.name or secret.name
            )
        except (TreiberFehler, GovOrgAbgelehnt) as fehler:
            befunde.append({"ref": konsument.ref, "ergebnis": "unpruefbar", "hinweis": str(fehler)[:160]})
            print(f"  ? {konsument.ref}: {fehler}")
            continue
        befunde.append({"ref": konsument.ref, "ergebnis": beleg.ergebnis})
        print(f"  {'✓' if beleg.ergebnis == 'ok' else '✗'} {konsument.ref}: {beleg.ergebnis}")

    rotlog.schreibe(
        {
            "lauf_id": f"{a.lauf_id}-widerruf",
            "secret": lauf.get("secret"),
            "gestartet": _jetzt(),
            "beendet": _jetzt(),
            "ausgefuehrt_von": a.ausgefuehrt_von or getpass.getuser(),
            "kind": "werkzeug",
            "status": "abgeschlossen" if befunde and all(b["ergebnis"] == "ok" for b in befunde) else "offen",
            "bezug_lauf_id": a.lauf_id,
            "konsumenten": befunde,
            "schleuse_geleert": True,
        },
        a.log,
    )
    return 0


# --------------------------------------------------------------------------
# faellig — der Melder
# --------------------------------------------------------------------------
def sammle_faelligkeit(
    inventar_pfad: Path | None = None,
    log_pfad: Path | None = None,
    schleuse: Path | None = None,
    heute: date | None = None,
) -> dict:
    heute = heute or date.today()
    inv = inventar.lade(inventar_pfad)
    eintraege = rotlog.lies(log_pfad)
    alle = inventar.secrets(inv)

    faellig, ohne_beleg, ohne_konsumenten = [], [], []
    for secret in alle:
        letzter = rotlog.letzter_lauf(secret.name, eintraege)
        if not secret.konsumenten:
            ohne_konsumenten.append(secret.name)
        elif secret.ohne_beleg:
            ohne_beleg.append(f"{secret.name} ({len(secret.ohne_beleg)}/{len(secret.konsumenten)})")
        if inventar.faellig_seit(secret, letzter, heute) is not None:
            faellig.append(secret.name)

    return {
        "secrets": len(alle),
        "faellig": faellig,
        "ohne_beleg": ohne_beleg,
        "ohne_konsumenten": ohne_konsumenten,
        "altlasten": inventar.altlasten(schleuse, heute),
        "laeufe": len(eintraege),
        "laeufe_offen": sum(1 for e in eintraege if e.get("status") == "offen"),
        "log_befunde": rotlog.pruefe_datei(log_pfad),
    }


def kurzzeile(b: dict) -> str:
    if b["log_befunde"]:
        return f"WERT IM LOG — {b['log_befunde'][0]}"
    teile = []
    if b["faellig"]:
        teile.append(f"{len(b['faellig'])} faellig")
    if b["ohne_beleg"]:
        teile.append(f"{len(b['ohne_beleg'])} ohne Beleg")
    if b["ohne_konsumenten"]:
        teile.append(f"{len(b['ohne_konsumenten'])} ohne Konsumenten")
    if b["altlasten"]:
        teile.append(f"{len(b['altlasten'])} Altlasten in ~/shared")
    if not teile:
        return f"OK: {b['secrets']} Secrets, nichts faellig, {b['laeufe']} Laeufe im Log"
    kopf = ", ".join(teile)
    namen = ", ".join((b["faellig"] or b["ohne_beleg"] or b["altlasten"])[:3])
    return f"{kopf} (von {b['secrets']} Secrets) — {namen}"


def cmd_faellig(a: argparse.Namespace) -> int:
    b = sammle_faelligkeit(a.inventar, a.log, getattr(a, "schleuse", None))
    if a.als_json:
        print(json.dumps(b, ensure_ascii=False, indent=2))
    elif a.kurz:
        print(kurzzeile(b))
    else:
        print(f"Secrets im Inventar   : {b['secrets']}")
        print(f"faellig               : {len(b['faellig'])}")
        for n in b["faellig"]:
            print(f"    {n}")
        print(f"mit Konsumenten ohne Beleg : {len(b['ohne_beleg'])}")
        for n in b["ohne_beleg"]:
            print(f"    {n}")
        print(f"ohne Konsumenten      : {len(b['ohne_konsumenten'])}")
        print(f"Altlasten in ~/shared : {len(b['altlasten'])}")
        for n in b["altlasten"]:
            print(f"    {n}")
        print(f"Laeufe im Log         : {b['laeufe']} ({b['laeufe_offen']} offen)")
        if b["log_befunde"]:
            print("WERT IM LOG:")
            for n in b["log_befunde"]:
                print(f"    {n}")
    return 1 if b["log_befunde"] else 0


# --------------------------------------------------------------------------
# log-pruefen — der Filter als eigener Check (Leser: PR-Gate)
# --------------------------------------------------------------------------
def cmd_log_pruefen(a: argparse.Namespace) -> int:
    befunde = rotlog.pruefe_datei(a.log)
    if befunde:
        print(f"✗ {len(befunde)} Zeile(n) mit Token-Muster:")
        for b in befunde:
            print(f"    {b}")
        return 1
    anzahl = len(rotlog.lies(a.log))
    print(f"✓ {anzahl} Log-Zeile(n) wertfrei (Muster: {', '.join(n for n, _ in rotlog.MUSTER)})")
    return 0


# --------------------------------------------------------------------------
def baue_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rotate.py",
        description="Rotationswerkzeug Stufe 1 — belegter Lauf ueber bekannte Konsumenten.",
    )
    p.add_argument("--inventar", type=Path, default=None, help=argparse.SUPPRESS)
    p.add_argument("--log", type=Path, default=None, help=argparse.SUPPRESS)
    unter = p.add_subparsers(dest="befehl", required=True)

    pr = unter.add_parser("pruefen", help="nur lesen — Pflicht-Vorstufe vor jedem Lauf")
    pr.add_argument("secret")
    pr.set_defaults(funktion=cmd_pruefen)

    la = unter.add_parser("lauf", help="die Kette: setzen, belegen, protokollieren, Schleuse leeren")
    la.add_argument("secret")
    la.add_argument("--quelle", required=True, help="Datei in der Schleuse mit dem neuen Wert")
    la.add_argument("--nur", help="nur diesen Konsumenten (ref)")
    la.add_argument("--ausgefuehrt-von", dest="ausgefuehrt_von")
    la.add_argument("--hmac-schluessel", type=Path, default=None, help=argparse.SUPPRESS)
    la.set_defaults(funktion=cmd_lauf)

    wi = unter.add_parser("widerruf-geprueft", help="Negativprobe nach dem menschlichen Widerruf")
    wi.add_argument("lauf_id")
    wi.add_argument("--ausgefuehrt-von", dest="ausgefuehrt_von")
    wi.set_defaults(funktion=cmd_widerruf_geprueft)

    fa = unter.add_parser("faellig", help="was ist faellig, ohne Beleg, ohne Konsumenten, Altlast")
    fa.add_argument("--kurz", action="store_true")
    fa.add_argument("--json", action="store_true", dest="als_json")
    fa.add_argument("--schleuse", type=Path, default=None, help=argparse.SUPPRESS)
    fa.set_defaults(funktion=cmd_faellig)

    lp = unter.add_parser("log-pruefen", help="Ausgabefilter ueber das Log (Leser: PR-Gate)")
    lp.set_defaults(funktion=cmd_log_pruefen)

    return p


def main(argv: list[str] | None = None) -> int:
    a = baue_parser().parse_args(argv)
    try:
        return a.funktion(a)
    except rotlog.WertGefunden as fehler:
        print(f"✗ {fehler}")
        return 4
