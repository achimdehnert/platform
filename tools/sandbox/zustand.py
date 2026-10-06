#!/usr/bin/env python3
"""Zustand der Sandbox-Werkstatt (platform#3784 SB5, ADR-308 §4.5 Punkt 7).

Laeuft auf dem Host, nie im Container, und liest nur. Eine Ausgabe fuer drei
Zwecke: Wochenstand fuer platform#3685, Warnsignale vor einem Ausfall und der
Einstieg fuer eine Sitzung, die den Stand nicht kennt.

  Spiegel    je Pilot-Repo: privat, Actions aus, nur Standard-Branch, offene PRs,
             Rueckstand zum Original in Commits
  Token      Tage bis zum Ablauf des Sandbox-Tokens
  CLI        Alter der im Dockerfile festgeschriebenen Claude-Code-Version
  Pruefung   Selbstpruefung im Container (--mit-selbstpruefung, braucht Docker)
  Laeufe     B2 und B6 aus benchmark.py

Der Rueckstand ist kein Warnsignal: Spiegel werden vor jedem Lauf aufgefrischt
(sandbox.sh). Was nicht messbar war, steht als `nicht messbar` in der Ausgabe
und zaehlt als Warnung — eine fehlende Messung ist kein gruener Befund.

Exit 1 bei mindestens einer Warnung, sonst 0. Ausgabe: Markdown oder --json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import benchmark  # noqa: E402 — erst nach dem Pfad-Einschub ladbar

ORG = "iilsandbox"  # Spiegel von ORG in sandbox.sh und spiegeln.sh
PILOT_DATEI = HIER / "pilot-repos.txt"
DOCKERFILE = HIER / "Dockerfile"
SECRET_LESEN = HIER.parent / "secret_lesen.sh"
TOKEN_DATEI = Path.home() / ".secrets" / "iilsandbox_github_token"
NPM_PAKET = "@anthropic-ai/claude-code"
TOKEN_WARN_TAGE = 30
CLI_WARN_TAGE = 30
ABLAUF_KOPF = "github-authentication-token-expiration"
NICHT_MESSBAR = "nicht messbar"

Aufruf = Callable[..., str]


def _aufruf(*befehl: str, env: dict | None = None) -> str:
    return subprocess.run(
        befehl, capture_output=True, text=True, check=True, timeout=120, env=env
    ).stdout


def pilot_repos(datei: Path = PILOT_DATEI) -> list[str]:
    zeilen = (z.strip() for z in datei.read_text(encoding="utf-8").splitlines())
    return [z for z in zeilen if z and not z.startswith("#")]


def spiegel_zustand(quelle: str, aufruf: Aufruf = _aufruf) -> dict:
    name = quelle.split("/", 1)[1]
    ziel = f"{ORG}/{name}"
    try:
        repo = json.loads(aufruf("gh", "api", f"repos/{ziel}"))
        branch = repo["default_branch"]
        actions = json.loads(aufruf("gh", "api", f"repos/{ziel}/actions/permissions"))
        branches = json.loads(aufruf("gh", "api", f"repos/{ziel}/branches"))
        prs = json.loads(aufruf("gh", "api", f"repos/{ziel}/pulls?state=open"))
        kopf = json.loads(aufruf("gh", "api", f"repos/{ziel}/commits/{branch}"))["sha"]
    except (subprocess.SubprocessError, OSError, ValueError, KeyError) as fehler:
        return {
            "spiegel": ziel,
            "warnungen": [f"{NICHT_MESSBAR}: {type(fehler).__name__}"],
        }
    warnungen = []
    if repo.get("visibility") != "private":
        warnungen.append("nicht privat")
    if actions.get("enabled") is not False:
        warnungen.append("Actions an")
    weitere = [b["name"] for b in branches if b["name"] != branch]
    if weitere:
        warnungen.append(f"weitere Branches: {', '.join(weitere)}")
    if prs:
        warnungen.append(f"offene PRs: {len(prs)}")
    try:
        vergleich = json.loads(
            aufruf("gh", "api", f"repos/{quelle}/compare/{kopf}...HEAD")
        )
        rueckstand = vergleich["ahead_by"]
    except (subprocess.SubprocessError, OSError, ValueError, KeyError):
        # Der Spiegel traegt Commits, die das Original nicht kennt (etwa ein Testmerge).
        rueckstand = None
        warnungen.append("Spiegel weicht vom Original ab")
    return {
        "spiegel": ziel,
        "kopf": kopf[:8],
        "rueckstand_commits": rueckstand,
        "warnungen": warnungen,
    }


def token_zustand(kopfzeilen: str, heute: datetime) -> dict:
    """Wertet die Antwortkoepfe eines API-Aufrufs mit dem Sandbox-Token aus."""
    for zeile in kopfzeilen.splitlines():
        name, _, wert = zeile.partition(":")
        if name.strip().lower() != ABLAUF_KOPF:
            continue
        try:
            ablauf = datetime.strptime(wert.strip(), "%Y-%m-%d %H:%M:%S %Z").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            break
        tage = (ablauf - heute).days
        warnungen = (
            [f"Token laeuft in {tage} Tagen ab"] if tage < TOKEN_WARN_TAGE else []
        )
        return {
            "ablauf": ablauf.date().isoformat(),
            "tage": tage,
            "warnungen": warnungen,
        }
    return {"warnungen": [f"{NICHT_MESSBAR}: kein Ablaufdatum in der Antwort"]}


def token_koepfe(aufruf: Aufruf = _aufruf) -> str:
    try:
        wert = aufruf(str(SECRET_LESEN), str(TOKEN_DATEI)).strip()
        return aufruf(
            "gh", "api", "-i", "rate_limit", env={**os.environ, "GH_TOKEN": wert}
        )
    except (subprocess.SubprocessError, OSError):
        return ""


def cli_pin(dockerfile: Path = DOCKERFILE) -> str | None:
    treffer = re.search(
        r"^ARG CLAUDE_CODE_VERSION=(\S+)", dockerfile.read_text(encoding="utf-8"), re.M
    )
    return treffer.group(1) if treffer else None


def cli_zustand(
    pin: str | None, zeiten: dict, neueste: str | None, heute: datetime
) -> dict:
    """`zeiten` ist die Ausgabe von `npm view <paket> time`: Version -> Zeitpunkt."""
    if not pin or pin not in zeiten:
        return {"pin": pin, "warnungen": [f"{NICHT_MESSBAR}: Version {pin} unbekannt"]}
    alter = (heute - datetime.fromisoformat(zeiten[pin].replace("Z", "+00:00"))).days
    warnungen = []
    if neueste and neueste != pin and alter > CLI_WARN_TAGE:
        warnungen.append(f"CLI {pin} ist {alter} Tage alt, aktuell {neueste}")
    return {"pin": pin, "alter_tage": alter, "neueste": neueste, "warnungen": warnungen}


def cli_daten(aufruf: Aufruf = _aufruf) -> tuple[dict, str | None]:
    try:
        zeiten = json.loads(aufruf("npm", "view", NPM_PAKET, "time", "--json"))
        neueste = json.loads(aufruf("npm", "view", NPM_PAKET, "version", "--json"))
        return zeiten, neueste
    except (subprocess.SubprocessError, OSError, ValueError):
        return {}, None


def selbstpruefung() -> dict:
    lauf = subprocess.run(
        [str(HIER / "sandbox.sh"), "--nur-pruefen"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    warnungen = (
        [] if lauf.returncode == 0 else [f"Selbstpruefung rot (Exit {lauf.returncode})"]
    )
    return {"exit": lauf.returncode, "warnungen": warnungen}


def messen(mit_selbstpruefung: bool, laeufe_wurzel: Path, heute: datetime) -> dict:
    laeufe_ = benchmark.laeufe(laeufe_wurzel)
    zeiten, neueste = cli_daten()
    return {
        "stand": heute.isoformat(timespec="minutes"),
        "spiegel": [spiegel_zustand(quelle) for quelle in pilot_repos()],
        "token": token_zustand(token_koepfe(), heute),
        "cli": cli_zustand(cli_pin(), zeiten, neueste, heute),
        "selbstpruefung": selbstpruefung()
        if mit_selbstpruefung
        else {
            "ausstehend": "ohne --mit-selbstpruefung nicht gemessen",
            "warnungen": [],
        },
        "laeufe": {
            "B2": benchmark.b2_durchlauf(laeufe_),
            "B6": benchmark.b6_kosten(laeufe_),
        },
    }


def warnungen(ergebnis: dict) -> list[str]:
    liste = [
        f"{s['spiegel']}: {w}" for s in ergebnis["spiegel"] for w in s["warnungen"]
    ]
    for teil in ("token", "cli", "selbstpruefung"):
        liste += ergebnis[teil]["warnungen"]
    return liste


def als_markdown(ergebnis: dict) -> str:
    zeilen = [
        f"**Sandbox-Zustand {ergebnis['stand']}**",
        "",
        "| Spiegel | Kopf | Rückstand |",
        "|---|---|---|",
    ]
    for s in ergebnis["spiegel"]:
        rueckstand = s.get("rueckstand_commits")
        zeilen.append(
            f"| {s['spiegel']} | {s.get('kopf', '–')} | {'–' if rueckstand is None else rueckstand} |"
        )
    token, cli, laeufe_ = ergebnis["token"], ergebnis["cli"], ergebnis["laeufe"]
    zeilen += [
        "",
        f"- Token: Ablauf {token.get('ablauf', NICHT_MESSBAR)}, {token.get('tage', '–')} Tage",
        f"- CLI: {cli.get('pin')}, {cli.get('alter_tage', '–')} Tage alt, aktuell {cli.get('neueste', '–')}",
        f"- Selbstprüfung: {ergebnis['selbstpruefung'].get('exit', 'nicht gemessen')}",
        f"- Läufe: {laeufe_['B2']['laeufe']}, fertig {laeufe_['B2']['fertig']}, "
        f"Kosten {laeufe_['B6']['summe_usd']} USD",
        "",
    ]
    liste = warnungen(ergebnis)
    zeilen += (
        ["**Warnungen:**"] + [f"- {w}" for w in liste]
        if liste
        else ["Keine Warnungen."]
    )
    return "\n".join(zeilen)


def main() -> int:
    ap = argparse.ArgumentParser(description="Zustand der Sandbox-Werkstatt messen")
    ap.add_argument("--laeufe", type=Path, default=benchmark.LAEUFE)
    ap.add_argument(
        "--mit-selbstpruefung",
        action="store_true",
        help="Selbstpruefung im Container ausfuehren (braucht Docker)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ergebnis = messen(args.mit_selbstpruefung, args.laeufe, datetime.now(timezone.utc))
    print(
        json.dumps(ergebnis, ensure_ascii=False, indent=2)
        if args.json
        else als_markdown(ergebnis)
    )
    return 1 if warnungen(ergebnis) else 0


if __name__ == "__main__":
    sys.exit(main())
