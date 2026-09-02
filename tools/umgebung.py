#!/usr/bin/env python3
"""Wo stehe ich, was laeuft hier, und wer antwortet unter den deklarierten Namen.

**Warum es das gibt.** Am 2026-08-30 hielt eine Sitzung ihre eigene Maschine fuer
einen Entwicklungsrechner und arbeitete stundenlang mit dem Wort »lokal«. Sie
stand die ganze Zeit auf dem **Staging-Host** `88.99.38.75`. Aus derselben Sitzung
stammen drei weitere Fehlschluesse derselben Familie:

- »writing-hub hat kein Staging« — geprueft waren zwei von acht Hosts aus
  `infra/hosts.yaml`, und `docker ps` zeigt nur Laufendes.
- »staging-writing.iil.pet ist writing-hub« — der Name loest auf, antwortet 200
  und liefert eine **fremde Anwendung** aus.
- »Cloudflare Access bietet E-Mail-Login« — das Wort stand in einer OAuth-URL.

Keiner dieser Irrtuemer war Nachlaessigkeit im Einzelnen; jeder war eine Antwort
auf eine Frage, die niemand gestellt hatte, weil sie zu selbstverstaendlich schien.

**Was dieses Werkzeug beantwortet — und was nicht.** Es fragt vier Dinge, die
keine andere Phase fragt, und beantwortet sie am Artefakt:

1. **Auf welchem Host stehe ich?** Nicht »localhost«, sondern der Name aus
   `infra/hosts.yaml`. Steht die Maschine nicht darin, sagt es genau das.
2. **Was laeuft hier von diesem Dienst?** Ueber `docker ps -a`, also inklusive
   gestoppter Container — ein gestoppter ist eine andere Aussage als keiner.
3. **Wer antwortet unter den deklarierten Namen?** Fuer `domain_prod` UND
   `domain_staging`: Statuscode **und ausgelieferter Seitentitel**. Ein Name, der
   200 liefert, ist noch kein Beleg, dass die richtige Anwendung dahintersteht —
   genau daran ist der Staging-Irrtum entstanden.
4. **Wo laeuft der Dienst sonst?** Ueber alle erreichbaren Hosts, nicht nur den
   eigenen.

Es beurteilt **nicht**, ob eine Abweichung schlimm ist. Es zeigt, was da ist, und
benennt, was es nicht pruefen konnte — eine nicht erreichbare Maschine ist eine
Luecke, kein stilles Nein.

    python3 tools/umgebung.py                  # Repo aus dem Arbeitsverzeichnis
    python3 tools/umgebung.py --repo weltenhub
    python3 tools/umgebung.py --kurz           # eine Zeile, fuer den Session-Start
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request

#: Das platform-Repo, aus dem die Deklarationen kommen — abgeleitet aus dem
#: eigenen Ort, NICHT fest verdrahtet. Ein fester Pfad las in einem Worktree
#: still die Datei des Hauptbaums: das Werkzeug sah woanders hin als der, der es
#: aufrief, und meldete eine Aenderung als wirkungslos, die es gar nicht kannte.
#: Genau die Fehlerklasse, gegen die dieses Werkzeug gebaut ist.
PLATFORM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 12
UA = "iil-umgebung/1.0 (+platform/tools)"
TITEL = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def _yaml(pfad: str) -> dict:
    import yaml

    with open(pfad, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def eigene_ip() -> str:
    """Die oeffentliche IP dieser Maschine — der einzige verlaessliche Selbstbezug.

    `hostname` sagt bei Cloud-Maschinen wenig (`ubuntu-32gb-fsn1-1`), und
    `hostname -I` liefert private Adressen. Gefragt ist, unter welcher Adresse
    diese Maschine in `hosts.yaml` steht.
    """
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=8) as a:
                ip = a.read().decode().strip()
                if re.fullmatch(r"[0-9.]{7,15}", ip):
                    return ip
        except Exception:  # noqa: BLE001 — der zweite Anbieter ist der Rueckfall
            continue
    return ""


def wo_bin_ich(hosts: dict) -> tuple[str, str]:
    """(Host-Name aus hosts.yaml, Begruendung). Leerer Name = nicht eingetragen."""
    ip = eigene_ip()
    eintraege = hosts.get("hosts") or hosts
    if not isinstance(eintraege, dict):
        return "", "hosts.yaml nicht lesbar"
    for name, v in eintraege.items():
        v = v or {}
        if ip and str(v.get("ip", "")).strip() == ip:
            return str(name), f"oeffentliche IP {ip}"
    lokal = socket.gethostname()
    if not ip:
        return "", f"oeffentliche IP nicht ermittelbar (hostname={lokal})"
    return "", f"IP {ip} steht in keinem hosts.yaml-Eintrag (hostname={lokal})"


def dienst_aus_ports(repo: str, ports: dict) -> dict:
    d = (ports.get("services") or ports).get(repo)
    return d if isinstance(d, dict) else {}


def container_hier(muster: str) -> list[str]:
    """Alle Container mit diesem Namensteil — auch gestoppte (`-a`)."""
    try:
        roh = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=25,
        ).stdout
    except Exception:  # noqa: BLE001
        return []
    return [z for z in roh.splitlines() if muster and muster.split("_")[0] in z]


def wer_antwortet(domain: str) -> tuple[str, str]:
    """(Status, Seitentitel). Der Titel ist der Punkt: ein 200 sagt nichts darueber,
    WELCHE Anwendung antwortet."""
    if not domain:
        return "-", ""
    try:
        req = urllib.request.Request(f"https://{domain}/", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as a:
            roh = a.read(200_000).decode("utf-8", "replace")
            t = TITEL.search(roh)
            return str(a.status), (t.group(1).strip()[:60] if t else "(kein Titel)")
    except urllib.error.HTTPError as e:
        return str(e.code), "(Fehlerseite)"
    except Exception as e:  # noqa: BLE001
        return "n/a", f"({type(e).__name__})"


def _marker(repo: str, dienst: dict) -> list[str]:
    """Woran man erkennt, dass die richtige Anwendung antwortet.

    Der Repo-Name allein reicht nicht: `weltenhub` liegt unter `weltenforger.com`
    und heisst dort »Weltenforger« — ein Abgleich gegen den Repo-Namen wuerde das
    faelschlich anschlagen. Deshalb darf `ports.yaml` je Dienst einen
    `titel_marker` fuehren; ohne ihn gilt der Repo-Name als beste Vermutung.
    """
    erklaert = dienst.get("titel_marker")
    if erklaert:
        return [str(erklaert).lower()]
    return [repo.split("-")[0].lower(), repo.replace("-", " ").lower()]


def _hinweis(repo: str, dienst: dict, status: str, titel: str) -> str:
    """Ein HINWEIS, kein Urteil.

    Dieses Werkzeug kann nicht wissen, wie eine Anwendung sich nennt. Es kann nur
    sagen: »der Titel bestaetigt es nicht, sieh hin«. Ein Fehlalarm ist hier
    billiger als ein stilles Ja — der Irrtum, gegen den es gebaut ist, sah aus wie
    ein sauberes 200.
    """
    if status != "200":
        return ""
    tief = titel.lower()
    if any(m in tief for m in _marker(repo, dienst)):
        return ""
    if "cloudflare access" in tief or "sign in" in tief:
        return "   ◌ Auth-Wand — was dahinter liegt, ist von hier nicht pruefbar"
    return "   ⚠ Titel bestaetigt dieses Repo nicht — nachsehen"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=os.path.basename(os.getcwd()))
    ap.add_argument("--kurz", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    hosts = _yaml(os.path.join(PLATFORM, "infra", "hosts.yaml"))
    ports = _yaml(os.path.join(PLATFORM, "infra", "ports.yaml"))
    host, warum = wo_bin_ich(hosts)
    d = dienst_aus_ports(a.repo, ports)

    befund = {
        "host": host or "UNBEKANNT",
        "host_begruendung": warum,
        "repo": a.repo,
        "deklariert": {
            k: d.get(k)
            for k in (
                "prod_host",
                "domain_prod",
                "domain_staging",
                "container_name",
                "prod",
                "staging",
            )
        },
        "container_hier": container_hier(
            str(d.get("container_name", a.repo.replace("-", "_")))
        ),
        "namen": {},
        "nicht_geprueft": [],
    }
    for feld in ("domain_prod", "domain_staging"):
        dom = d.get(feld)
        if not dom:
            befund["nicht_geprueft"].append(f"{feld}: nicht deklariert")
            continue
        status, titel = wer_antwortet(str(dom))
        befund["namen"][str(dom)] = {
            "feld": feld,
            "status": status,
            "titel": titel,
            "hinweis": _hinweis(a.repo, d, status, titel),
        }

    if a.json:
        print(json.dumps(befund, ensure_ascii=False, indent=1))
        return 0

    if a.kurz:
        n = " · ".join(
            f"{k}→{v['status']} {v['titel'][:24]}" for k, v in befund["namen"].items()
        )
        print(
            f"Host {befund['host']} ({warum}) · {a.repo}: {len(befund['container_hier'])} Container · {n or 'keine Namen deklariert'}"
        )
        return 0

    print(f"== Umgebung · {a.repo} ==")
    print(f"  Ich stehe auf : {befund['host']}   ({warum})")
    dh = befund["deklariert"]
    print(
        f"  Deklariert    : prod_host={dh.get('prod_host')} port_prod={dh.get('prod')} port_staging={dh.get('staging')}"
    )
    print("  Container hier:")
    for c in befund["container_hier"] or ["    (keine)"]:
        print(f"    {c}")
    print("  Wer antwortet unter dem Namen:")
    for dom, v in befund["namen"].items():
        print(
            f"    {v['feld']:15} {dom:34} {v['status']:>4}  {v['titel']}{v['hinweis']}"
        )
    for z in befund["nicht_geprueft"]:
        print(f"  Nicht geprueft: {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
