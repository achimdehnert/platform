#!/usr/bin/env python3
"""origin_tls_melder.py — misst das Zertifikat, das der Origin wirklich ausliefert.

## Warum es das gibt

`0.7.11 erreichbarkeit` fragt die Prod-Domains am **Edge** an. Eine 200 von dort
belegt, dass jemand antwortet — sie belegt **nicht**, dass die TLS-Kette am Origin
gesund ist. Cloudflare steht in dieser Flotte auf `full`, nicht `full (strict)`:
der Edge akzeptiert ein **abgelaufenes** Origin-Zertifikat und liefert davor eine
tadellose 200 aus. Von aussen wird nichts rot.

Realfall ausschreibungs-hub, 2026-08-23: der certbot-Cloudflare-Token auf dem
Prod-Host war seit spaetestens dem 08.08. ungueltig. **10 von 15 Origin-Zertifikaten
waren abgelaufen** — zwei Wochen lang, ohne einen einzigen roten Melder. Gefunden
wurde es beiher, bei einer ganz anderen Aufgabe.

Das ist dieselbe Krankheit wie beim Erreichbarkeits-Melder, nur eine Schicht tiefer:
Die Zusagen (Registry, Tunnel-Route, Deploy-Lauf, jetzt auch der Edge-Statuscode)
stimmen alle miteinander ueberein, und trotzdem ist der Zustand faul. Nur eine
Messung **am Origin** kann das sehen.

## Was gemessen wird

Je Host, der TLS terminiert, ein TLS-Handshake **auf dem Host selbst** gegen
`127.0.0.1:443` mit dem Domainnamen als SNI — also genau das Zertifikat, das nginx
fuer diese Domain ausliefert. Nicht `certbot certificates`: das ist wieder eine
Zusage (was certbot zu haben glaubt), nicht das, was der Server herausgibt. Ein
korrekt erneuertes Zertifikat, das mangels Reload nie ausgeliefert wird, faellt nur
in der Messung auf.

Welche Hosts TLS terminieren, wird **gemessen statt deklariert**: ein Host mit null
Eintraegen unter `/etc/letsencrypt/live` terminiert kein TLS. `prod-b` ist so ein
Host (ADR-292 Long-Tail-Umzug: Ingress per Cloudflare-Tunnel auf HTTP, `nginx` dort
haelt null Zertifikate). Seine Domains sind hier kein Befund, sondern nicht
zutreffend — und das steht im Report, statt still zu fehlen.

## Warum der Aussteller mitgemessen wird

Der Erstlauf am 2026-08-24 zeigte drei verschiedene Realitaeten hinter derselben
gruenen 200 — und eine reine Ablaufdatums-Pruefung haette zwei davon verwechselt:

1. **Let's Encrypt** (`bieterpilot.de`, `schutztat.de`, …) — kurzlebig, muss erneuert
   werden. Nur hier ist eine Restlaufzeit ueberhaupt eine Aussage.
2. **Cloudflare Origin CA** (`tax.iil.pet`, `dev-hub.iil.pet`, …) — gueltig bis 2041,
   nur vom Cloudflare-Edge vertraut. Voellig in Ordnung, aber ein Ablaufdatum in
   fuenfzehn Jahren ist kein Gesundheitsbeleg, sondern eine andere Betriebsart.
3. **`CN=invalid.localhost`** (`docs.iil.pet`, `schulungspass.de`) — das ist der
   **Fallback-vhost von nginx**: fuer diesen Namen existiert gar kein Zertifikat,
   der Server gibt sein Platzhalter-Zertifikat heraus. Das Ablaufdatum liegt 2036,
   eine reine Datums-Pruefung meldet also „gruen" — obwohl die Domain am Origin
   ungeschuetzt ist und nur Cloudflares `full`-Modus sie am Leben haelt.

Klasse 3 ist genau der Fehler, den dieses Werkzeug finden soll. Ohne den Aussteller
ist sie von Klasse 2 nicht zu unterscheiden.

## Klassen

- `gueltig`         — echtes Zertifikat, Restlaufzeit ueber der Warnschwelle.
- `laeuft-ab`       — unter `--warn-tage` (Vorgabe 21). Befund: certbot erneuert bei
                      30 Tagen Rest; wer darunter faellt, hat ein kaputtes Renewal.
- `abgelaufen`      — notAfter liegt in der Vergangenheit. Der Realfall oben.
- `fallback-zertifikat` — nginx antwortet mit seinem Platzhalter; fuer diesen Namen
                      existiert am Origin kein Zertifikat. Befund.
- `cloudflare-origin-ca` — langlebiges Origin-Zertifikat. Kein Befund.
- `kein-zertifikat` — Host terminiert TLS, gibt aber fuer diese Domain keins heraus.
- `nicht-messbar`   — Handshake/ssh gescheitert; ausdruecklich KEIN "gruen".
- `kein-tls-am-origin` — Host terminiert generell kein TLS. Kein Befund.

## Aufruf

    python3 tools/origin_tls_melder.py            # voller Report
    python3 tools/origin_tls_melder.py --kurz     # eine Zeile fuer den Session-Start
    python3 tools/origin_tls_melder.py --json     # maschinenlesbar
    python3 tools/origin_tls_melder.py --offline  # ohne ssh, nur Deklarations-Pruefung

Exit-Code 0 immer — Report-Werkzeug, kein Enforcer (Hausform wie `gate_deckung.py`).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import yaml

# Maschinenlesbarer Kopf (KONZ-038 D8)
GATE_HEADER = {
    "slug": "edge-200-als-tls-beleg-gelesen",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-24",
    "evidence": "tools/tests/test_origin_tls_melder.py",
}

STATUS_ERLAUBT = ("aktiv", "stillgelegt", "blockiert")
PROD_HOSTS = ("prod", "prod-b")
SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
SSH_TIMEOUT_S = 120
WARN_TAGE = 21
PARALLEL = 4

# `befund` sagt, ob die Klasse eine Meldung wert ist.
KLASSEN = {
    "gueltig": (False, "Origin-Zertifikat gueltig"),
    "cloudflare-origin-ca": (
        False,
        "Cloudflare Origin CA — langlebig, vom Edge vertraut",
    ),
    "fallback-zertifikat": (
        True,
        "nginx-Platzhalter: fuer diesen Namen existiert kein Zertifikat",
    ),
    "laeuft-ab": (
        True,
        "Restlaufzeit unter der Warnschwelle — Renewal prueft sich nicht selbst",
    ),
    "abgelaufen": (True, "Origin liefert ein abgelaufenes Zertifikat aus"),
    "kein-zertifikat": (
        True,
        "Host terminiert TLS, gibt fuer diese Domain aber keins heraus",
    ),
    "nicht-messbar": (
        True,
        "Handshake nicht zustande gekommen — keine Aussage moeglich",
    ),
    "kein-tls-am-origin": (False, "Host terminiert kein TLS (Tunnel-Ingress)"),
    "nicht-geprueft": (False, "offline-Lauf"),
}


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ports_yaml_pfad() -> str:
    return os.path.join(_repo_root(), "infra", "ports.yaml")


def _hosts_yaml_pfad() -> str:
    return os.path.join(_repo_root(), "infra", "hosts.yaml")


def lade_dienste(pfad: str) -> list[dict]:
    """Dienste mit deklarierter Prod-Domain, inklusive Lebenszyklus-Angabe."""
    daten = yaml.safe_load(open(pfad, encoding="utf-8")) or {}
    raus = []
    for name, v in (daten.get("services") or {}).items():
        if not isinstance(v, dict) or not v.get("domain_prod"):
            continue
        raus.append(
            {
                "name": name,
                "domain": str(v["domain_prod"]),
                "host": str(v.get("prod_host", "prod")),
                "betriebsstatus": str(v.get("betriebsstatus", "aktiv")),
                "grund": v.get("betriebsstatus_grund"),
            }
        )
    return sorted(raus, key=lambda d: d["name"])


def lade_hosts(pfad: str) -> dict[str, str]:
    """{'prod': 'root@1.2.3.4', ...} — nur Prod-Hosts mit ssh-Zugang."""
    daten = yaml.safe_load(open(pfad, encoding="utf-8")) or {}
    roh = daten.get("hosts", daten) or {}
    raus = {}
    for name, cfg in roh.items():
        if name not in PROD_HOSTS or not isinstance(cfg, dict):
            continue
        ziel = cfg.get("ssh")
        if ziel and ziel != "-":
            raus[name] = str(ziel)
    return raus


def _sh(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:
        return 127, ""


def fernbefehl(domains: list[str]) -> str:
    """Skript, das je Domain eine Zeile 'domain<TAB>notAfter<TAB>issuer' schreibt.

    Ein Aufruf je HOST statt je Domain: 26 einzelne ssh-Verbindungen waeren die
    teuerste Art, dieselbe Frage zu stellen.
    """
    liste = " ".join(f"'{d}'" for d in domains)
    return (
        "n=$(ls /etc/letsencrypt/live 2>/dev/null | grep -vc README || echo 0); "
        'printf "TLS_TERMINIERT\\t%s\\t-\\n" "$n"; '
        f"for d in {liste}; do "
        '  c=$(echo | openssl s_client -connect 127.0.0.1:443 -servername "$d" 2>/dev/null '
        "      | openssl x509 -noout -enddate -issuer 2>/dev/null); "
        '  e=$(printf "%s" "$c" | sed -n "s/^notAfter=//p"); '
        '  i=$(printf "%s" "$c" | sed -n "s/^issuer=//p"); '
        '  printf "%s\\t%s\\t%s\\n" "$d" "${e:-KEINS}" "${i:-KEINS}"; '
        "done"
    )


def _parse_notafter(text: str) -> datetime | None:
    """'Nov 21 09:15:53 2026 GMT' -> datetime (UTC). None, wenn unlesbar."""
    try:
        return datetime.strptime(text.strip(), "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=timezone.utc
        )
    except (ValueError, AttributeError):
        return None


def klassifiziere(
    notafter: datetime | None, issuer: str, jetzt: datetime, warn_tage: int
) -> tuple[str, int | None]:
    """Reine Funktion: (Ablaufzeitpunkt, Aussteller) -> (Klasse, Resttage).

    Die Reihenfolge der Pruefungen ist bewusst: der **Aussteller** entscheidet, ob
    das Ablaufdatum ueberhaupt etwas bedeutet. Ein Platzhalter-Zertifikat mit
    Laufzeit bis 2036 ist kein gesunder Zustand, sondern eine fehlende Konfiguration.
    """
    if notafter is None:
        return "kein-zertifikat", None
    rest = (notafter - jetzt).days
    if "invalid.localhost" in issuer or "snakeoil" in issuer.lower():
        return "fallback-zertifikat", rest
    if "cloudflare" in issuer.lower():
        return "cloudflare-origin-ca", rest
    if rest < 0:
        return "abgelaufen", rest
    if rest < warn_tage:
        return "laeuft-ab", rest
    return "gueltig", rest


def messe_host(ssh_ziel: str, domains: list[str], laeufer=None) -> dict:
    """{domain: (notAfter-Text|None, issuer)} + Sonderschluessel '_tls_terminiert'.

    Der Sonderschluessel traegt die Unterscheidung, die den halben Wert ausmacht:
    'keine Zertifikate gefunden' heisst auf einem Tunnel-Host 'nicht zustaendig',
    auf einem TLS-Host aber 'kaputt'. Ohne ihn waeren beide dieselbe leere Antwort.
    """
    laeufer = laeufer or (lambda cmd: _sh(cmd, SSH_TIMEOUT_S))
    code, out = laeufer(SSH + [ssh_ziel, fernbefehl(domains)])
    if code != 0 and not out.strip():
        return {"_tls_terminiert": None}
    ergebnis: dict = {"_tls_terminiert": None}
    for zeile in out.splitlines():
        teile = zeile.split("\t")
        if len(teile) < 2:
            continue
        name, ende = teile[0], teile[1].strip()
        issuer = teile[2].strip() if len(teile) > 2 else ""
        if name == "TLS_TERMINIERT":
            ergebnis["_tls_terminiert"] = ende not in ("", "0")
            continue
        ergebnis[name] = (None if ende in ("", "KEINS") else ende, issuer)
    return ergebnis


def messe(
    dienste: list[dict],
    hosts: dict[str, str],
    offline: bool = False,
    laeufer=None,
    jetzt: datetime | None = None,
    warn_tage: int = WARN_TAGE,
) -> dict[str, tuple[str, int | None]]:
    """{dienstname: (Klasse, Resttage)} — nur aktive Dienste werden angefasst."""
    if offline:
        return {d["name"]: ("nicht-geprueft", None) for d in dienste}
    jetzt = jetzt or datetime.now(timezone.utc)
    aktive = [d for d in dienste if d["betriebsstatus"] == "aktiv"]

    nach_host: dict[str, list[dict]] = {}
    for d in aktive:
        nach_host.setdefault(d["host"], []).append(d)

    def eine_gruppe(item):
        host, gruppe = item
        ziel = hosts.get(host)
        if not ziel:
            return host, {"_tls_terminiert": None}
        return host, messe_host(ziel, [d["domain"] for d in gruppe], laeufer)

    with cf.ThreadPoolExecutor(max_workers=PARALLEL) as ex:
        roh = dict(ex.map(eine_gruppe, nach_host.items()))

    raus: dict[str, tuple[str, int | None]] = {}
    for host, gruppe in nach_host.items():
        antwort = roh.get(host, {"_tls_terminiert": None})
        terminiert = antwort.get("_tls_terminiert")
        for d in gruppe:
            if terminiert is None:
                raus[d["name"]] = ("nicht-messbar", None)
            elif terminiert is False:
                raus[d["name"]] = ("kein-tls-am-origin", None)
            else:
                ende, issuer = antwort.get(d["domain"], (None, ""))
                raus[d["name"]] = klassifiziere(
                    _parse_notafter(ende or ""), issuer, jetzt, warn_tage
                )
    return raus


def bewerte(dienste: list[dict], messung: dict[str, tuple[str, int | None]]) -> dict:
    """Klasse + Lebenszyklus ergeben das Urteil. Reine Funktion, ohne Netz."""
    befunde, geparkt, stumme_ausnahme, ok = [], [], [], []
    for d in dienste:
        klasse, rest = messung.get(d["name"], ("nicht-geprueft", None))
        zeile = dict(d, klasse=klasse, resttage=rest)
        if d["betriebsstatus"] not in STATUS_ERLAUBT:
            zeile["warum"] = f"unbekannter betriebsstatus {d['betriebsstatus']!r}"
            stumme_ausnahme.append(zeile)
            continue
        if d["betriebsstatus"] != "aktiv":
            if not d["grund"]:
                zeile["warum"] = "betriebsstatus ohne betriebsstatus_grund"
                stumme_ausnahme.append(zeile)
            else:
                geparkt.append(zeile)
            continue
        if KLASSEN.get(klasse, (True, ""))[0]:
            befunde.append(zeile)
        else:
            ok.append(zeile)
    return {
        "geprueft": len(dienste),
        "befunde": sorted(
            befunde, key=lambda z: (z["resttage"] is None, z["resttage"])
        ),
        "geparkt": geparkt,
        "stumme_ausnahme": stumme_ausnahme,
        "ok": ok,
    }


def _kurzzeile(e: dict) -> str:
    # Ein Offline-Lauf hat NICHTS gemessen. Ihn als "alles gruen" zu melden waere
    # genau die Falle, die dieses Werkzeug schliessen soll.
    ungeprueft = [z for z in e["ok"] if z["klasse"] == "nicht-geprueft"]
    if ungeprueft and not e["befunde"]:
        return f"{len(ungeprueft)} Origin-Ziel(e) NICHT geprueft (offline) — keine Aussage zur TLS-Lage"
    if e["stumme_ausnahme"]:
        n = len(e["stumme_ausnahme"])
        return f"{n} Ausnahme(n) ohne Grund — betriebsstatus gesetzt, betriebsstatus_grund fehlt"
    if not e["befunde"]:
        n = {
            k: len([z for z in e["ok"] if z["klasse"] == k])
            for k in ("gueltig", "cloudflare-origin-ca", "kein-tls-am-origin")
        }
        return (
            f"{n['gueltig']} Zertifikat(e) gueltig, {n['cloudflare-origin-ca']} Cloudflare-Origin-CA, "
            f"{n['kein-tls-am-origin']} ohne TLS am Origin"
        )
    teile = []
    for b in e["befunde"]:
        rest = "" if b["resttage"] is None else f", {b['resttage']}d"
        teile.append(f"{b['name']} ({b['klasse']}{rest})")
    return f"{len(e['befunde'])} Origin-Zertifikat(e) auffaellig — " + ", ".join(teile)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--kurz", action="store_true", help="eine Zeile fuer den Session-Start"
    )
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument(
        "--offline", action="store_true", help="ohne ssh, nur Deklarations-Pruefung"
    )
    p.add_argument(
        "--warn-tage",
        type=int,
        default=WARN_TAGE,
        help=f"Warnschwelle (Vorgabe {WARN_TAGE})",
    )
    p.add_argument("--ports", default=None, help="Pfad zu ports.yaml")
    p.add_argument("--hosts", default=None, help="Pfad zu hosts.yaml")
    a = p.parse_args()

    dienste = lade_dienste(a.ports or _ports_yaml_pfad())
    hosts = lade_hosts(a.hosts or _hosts_yaml_pfad())
    ergebnis = bewerte(
        dienste, messe(dienste, hosts, offline=a.offline, warn_tage=a.warn_tage)
    )

    if a.als_json:
        json.dump(ergebnis, sys.stdout, ensure_ascii=False, indent=2, default=str)
        print()
        return 0
    if a.kurz:
        print(_kurzzeile(ergebnis))
        return 0

    print(
        f"# Origin-TLS der deklarierten Prod-Ziele ({ergebnis['geprueft']} Dienste)\n"
    )
    for titel, schluessel, hinweis in (
        ("🚨 Befunde", "befunde", "am Origin gemessen — der Edge sagt dazu nichts"),
        (
            "⚠️  Ausnahme ohne Grund",
            "stumme_ausnahme",
            "betriebsstatus gesetzt, Begruendung fehlt",
        ),
        ("⏸  Bewusst geparkt", "geparkt", "kein Befund — Grund hinterlegt"),
        ("✅ Unauffaellig", "ok", ""),
    ):
        zeilen = ergebnis[schluessel]
        if not zeilen:
            continue
        print(f"## {titel} ({len(zeilen)}){' — ' + hinweis if hinweis else ''}\n")
        for z in zeilen:
            rest = "" if z.get("resttage") is None else f"  {z['resttage']}d"
            extra = f"  [{z['warum']}]" if z.get("warum") else ""
            print(f"  {z['name']:22} {z['domain']:32} {z['klasse']:20}{rest}{extra}")
        print()

    print(_kurzzeile(ergebnis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
