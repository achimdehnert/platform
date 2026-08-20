#!/usr/bin/env python3
"""deploy_wirkung — prueft, ob der Stand HINTER dem oeffentlichen Namen dem Repo entspricht.

Warum es das gibt
-----------------
Alle bestehenden Deploy-Melder pruefen **Deklarationen** oder **Run-Ergebnisse**:
die Registry sagt `deployed: true`, der Workflow-Run sagt `success`, die
Tunnel-Route zeigt auf einen Port. Keiner davon beantwortet die einzige Frage,
die zaehlt: *laeuft hinter dem oeffentlichen Namen der Stand, der im Repo steht?*

Am 2026-08-20 kostete diese Luecke einen Abend (platform#2122): `_deploy-unified.yml`
deployt auf dem Host des self-hosted Runners. Nach der Umzugswelle vom 2026-08-04
(ADR-292) standen sechs Runner noch auf prod-a, waehrend die Anwendungen auf prod-b
liefen. Jeder Merge lieferte an eine Instanz, die niemand aufruft — **gruener Run,
Aenderung nicht live, kein einziger roter Check**. Aufgefallen ist es nur zufaellig,
weil ein Healthcheck-Fix eine im Container *sichtbare* Signatur hinterliess.

Genau diese Signatur gibt es bereits ueberall: `/opt/<repo>/.deploy-manifest.json`
mit dem deployten Commit. Dieses Werkzeug liest sie auf allen Hosts und vergleicht
sie mit `origin/main` — und zwar auf dem Host, der den oeffentlichen Namen
tatsaechlich **bedient**, nicht auf dem, wo der Runner zufaellig steht.

Zwei Befundklassen
------------------
1. RUECKSTAND — der bedienende Host hat einen aelteren Commit als `origin/main`.
2. DOPPELLAUF — dasselbe Repo hat auf mehreren Hosts ein Manifest. Das Risiko
   benennt ADR-292 selbst: divergierende Datenbanken. Nach einem Host-Umzug bleibt
   der alte Stand als Leiche stehen.

Aufruf
------
    python3 tools/deploy_wirkung.py                 # Bericht, aendert nichts
    python3 tools/deploy_wirkung.py --json          # maschinenlesbar
    python3 tools/deploy_wirkung.py --repo cad-hub  # nur ein Repo

Exit-Codes: 0 = kein Befund · 1 = Befund (kein Tool-Fehler) · 2 = Tool-/Config-Fehler.

Grenzen, ausdruecklich
----------------------
- Der Commit im Manifest belegt, was das Deploy-Skript **geschrieben** hat, nicht
  zwingend, was der Container **ausfuehrt**. Ein Manifest-Treffer bei gleichzeitig
  wochenaltem Container ist weiterhin verdaechtig — deshalb wird das Alter des
  Manifests mit ausgegeben.
- Repos ohne `.deploy-manifest.json` sind unsichtbar fuer dieses Werkzeug. Sie
  werden als `OHNE MANIFEST` gemeldet, nicht stillschweigend uebersprungen.
- Die Host-Zuordnung stammt aus den cloudflared-Configs. Wird ein Name per nginx
  oder DNS-A-Record bedient, greift die Zuordnung nicht; solche Repos landen in
  `ZUORDNUNG UNKLAR`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOSTS_YAML = REPO_ROOT / "infra" / "hosts.yaml"
CANON_YAML = REPO_ROOT / "registry" / "canonical.yaml"
SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
# Nur Hosts, auf denen Anwendungen produktiv laufen.
PROD_HOSTS = ("prod", "prod-b")


def sh(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip()
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError as exc:  # ssh fehlt o.ae.
        return 125, str(exc)


def load_yaml(path: Path) -> dict:
    import yaml

    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def hosts_aus_registry() -> dict[str, str]:
    """{'prod': 'root@1.2.3.4', ...} — nur Prod-Hosts mit ssh-Zugang."""
    data = load_yaml(HOSTS_YAML)
    roh = data.get("hosts", data)
    out = {}
    for name, cfg in (roh or {}).items():
        if name not in PROD_HOSTS or not isinstance(cfg, dict):
            continue
        ssh_ziel = cfg.get("ssh")
        if ssh_ziel and ssh_ziel != "-":
            out[name] = ssh_ziel
    return out


def manifeste(ssh_ziel: str) -> dict[str, dict]:
    """{repo: {'commit':..., 'run_id':..., 'alter_tage': int}} von einem Host."""
    # Ein Aufruf statt N, und der Host liefert JSON-Lines statt eines
    # selbstgebauten Trennzeichen-Formats: ein Manifest je Zeile, direkt parsebar.
    # (Ein frueheres "@@@"-Schema zerfiel beim Split in abwechselnd Name und Block.)
    fernbefehl = (
        "for f in /opt/*/.deploy-manifest.json; do "
        '[ -f "$f" ] || continue; '
        'printf \'{"repo":"%s","mtime":%s,"manifest":\' '
        '"$(basename "$(dirname "$f")")" "$(stat -c %Y "$f")"; '
        'cat "$f" | tr -d "\\n"; printf \'}\\n\'; done'
    )
    code, out = sh(SSH + [ssh_ziel, fernbefehl], timeout=90)
    if code != 0:
        return {}
    ergebnis: dict[str, dict] = {}
    for zeile in out.splitlines():
        zeile = zeile.strip()
        if not zeile.startswith("{"):
            continue
        try:
            satz = json.loads(zeile)
            daten = satz["manifest"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        ergebnis[str(satz.get("repo", "")).strip()] = {
            "commit": (daten.get("commit") or "")[:40],
            "run_id": daten.get("run_id"),
            "mtime": int(satz.get("mtime") or 0),
        }
    return ergebnis


def tunnel_namen(ssh_ziel: str) -> set[str]:
    """Hostnamen, die dieser Host per cloudflared bedient."""
    code, out = sh(
        SSH + [ssh_ziel, "grep -oE '^ *- *hostname: *[^ ]+' /etc/cloudflared/config.yml 2>/dev/null"],
        timeout=30,
    )
    if code != 0:
        return set()
    return {m.group(1) for m in re.finditer(r"hostname:\s*(\S+)", out)}


def repo_lifecycle() -> dict[str, str]:
    """{repo: lifecycle} — abgeschaltete Repos sind kein Rueckstands-Befund."""
    data = load_yaml(CANON_YAML)
    out = {}
    for name, eintrag in (data.get("repos") or {}).items():
        lc = (eintrag.get("rich") or {}).get("lifecycle")
        if lc:
            out[name] = str(lc)
    return out


def repo_urls() -> dict[str, list[str]]:
    """{repo: [prod_url, aliase...]} aus der kanonischen Registry."""
    data = load_yaml(CANON_YAML)
    out: dict[str, list[str]] = {}
    for name, eintrag in (data.get("repos") or {}).items():
        namen: list[str] = []
        for teil in (eintrag.get("flat") or {}, eintrag.get("rich") or {}):
            for feld in ("prod_url", "url"):
                wert = teil.get(feld)
                if wert:
                    namen.append(str(wert).replace("https://", "").replace("http://", "").rstrip("/"))
        if namen:
            out[name] = sorted(set(namen))
    return out


def main_sha(repo: str, owner: str = "achimdehnert") -> str | None:
    code, out = sh(["gh", "api", f"repos/{owner}/{repo}/commits/main", "--jq", ".sha"], timeout=30)
    return out.strip() if code == 0 and out.strip() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    ap.add_argument("--repo", help="nur dieses Repo pruefen")
    args = ap.parse_args()

    hosts = hosts_aus_registry()
    if not hosts:
        print("FEHLER: keine Prod-Hosts mit ssh-Zugang in infra/hosts.yaml", file=sys.stderr)
        return 2

    je_host: dict[str, dict[str, dict]] = {}
    je_host_namen: dict[str, set[str]] = {}
    for name, ziel in hosts.items():
        je_host[name] = manifeste(ziel)
        je_host_namen[name] = tunnel_namen(ziel)

    # Positivkontrolle: findet das Werkzeug ueberhaupt etwas? Sonst ist die Null
    # das Messgeraet und nicht die Welt.
    gesamt = sum(len(m) for m in je_host.values())
    if gesamt == 0:
        print("FEHLER: auf KEINEM Host ein Manifest gefunden — das ist ein Tool-/Zugangsfehler,", file=sys.stderr)
        print("        kein Befund. Pruefen: ssh-Zugang, /opt/*/.deploy-manifest.json", file=sys.stderr)
        return 2

    urls = repo_urls()
    lifecycles = repo_lifecycle()
    RUHEND = {"archived", "frozen"}
    alle_repos = sorted({r for m in je_host.values() for r in m})
    if args.repo:
        alle_repos = [r for r in alle_repos if r == args.repo]

    befunde: list[dict] = []
    zeilen: list[tuple] = []
    import time

    jetzt = int(time.time())

    for repo in alle_repos:
        vorhanden = {h: m[repo] for h, m in je_host.items() if repo in m}
        # Welcher Host bedient den oeffentlichen Namen?
        #  a) Steht das Manifest nur auf EINEM Host, ist die Frage beantwortet —
        #     dann braucht es keine Tunnel-Zuordnung. Das ist der Normalfall und
        #     vermeidet massenhaft "unklar" fuer Repos, die prod-a per nginx
        #     bedient (dessen cloudflared kennt nur wenige Namen einzeln).
        #  b) Erst beim Doppellauf entscheidet die Tunnel-Route, welcher Stand
        #     der oeffentlich sichtbare ist — und genau dort zaehlt es.
        if len(vorhanden) == 1:
            ziel_host = next(iter(vorhanden))
        else:
            bedient = [h for h, namen in je_host_namen.items() if any(u in namen for u in urls.get(repo, []))]
            ziel_host = bedient[0] if len(bedient) == 1 else None

        sha = main_sha(repo)
        eintrag = {
            "repo": repo,
            "hosts_mit_manifest": sorted(vorhanden),
            "bedient_von": ziel_host,
            "main": (sha or "")[:8] or None,
            "doppellauf": len(vorhanden) > 1,
        }

        if ziel_host and ziel_host in vorhanden:
            mf = vorhanden[ziel_host]
            eintrag["deployed"] = mf["commit"][:8]
            eintrag["alter_tage"] = (jetzt - mf["mtime"]) // 86400 if mf["mtime"] else None
            eintrag["rueckstand"] = bool(sha and mf["commit"] and mf["commit"] != sha)
        else:
            eintrag["deployed"] = None
            eintrag["rueckstand"] = None
            eintrag["zuordnung_unklar"] = True

        eintrag["lifecycle"] = lifecycles.get(repo)
        # Ein stillgelegtes Repo DARF hinterherhinken — das ist der gewollte Zustand,
        # kein Befund. Der Doppellauf bleibt trotzdem einer (divergierende Daten).
        if eintrag["lifecycle"] in RUHEND and eintrag.get("rueckstand"):
            eintrag["rueckstand"] = False
            eintrag["ruhend"] = True
        if eintrag.get("rueckstand") or eintrag["doppellauf"] or eintrag.get("zuordnung_unklar"):
            befunde.append(eintrag)
        zeilen.append(eintrag)

    if args.json:
        print(json.dumps({"geprueft": len(zeilen), "befunde": befunde, "alle": zeilen}, indent=2))
        return 1 if befunde else 0

    print(f"deploy_wirkung — {len(zeilen)} Repo(s) mit Manifest auf {len(hosts)} Prod-Host(s)\n")
    kopf = f"{'Repo':<20} {'bedient':<8} {'deployed':<10} {'main':<10} {'Alter':<7} Befund"
    print(kopf)
    print("-" * len(kopf))
    for e in zeilen:
        marker = []
        if e.get("rueckstand"):
            marker.append("RUECKSTAND")
        if e["doppellauf"]:
            marker.append("DOPPELLAUF:" + ",".join(e["hosts_mit_manifest"]))
        if e.get("zuordnung_unklar"):
            marker.append("ZUORDNUNG UNKLAR")
        if e.get("ruhend"):
            marker.append(f"ruhend({e['lifecycle']}) — Rueckstand gewollt")
        alter = f"{e['alter_tage']}d" if e.get("alter_tage") is not None else "-"
        print(
            f"{e['repo']:<20} {(e['bedient_von'] or '?'):<8} {(e['deployed'] or '-'):<10} "
            f"{(e['main'] or '-'):<10} {alter:<7} {' · '.join(marker) or 'ok'}"
        )

    ohne = sorted(set(urls) - set(alle_repos)) if not args.repo else []
    if ohne:
        print(f"\nOHNE MANIFEST ({len(ohne)}) — fuer dieses Werkzeug unsichtbar, nicht ueberspringen:")
        print("  " + ", ".join(ohne))

    print(f"\nZusammenfassung: {len(befunde)} Befund(e) von {len(zeilen)} geprueften Repos.")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
