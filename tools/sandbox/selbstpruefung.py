#!/usr/bin/env python3
"""Selbstpruefung der Sandbox (platform#3685) — laeuft im Container VOR dem Agenten.

Eine Umgebung ist nur dann Sandbox, wenn die Technik es erzwingt, nicht weil
jemand es behauptet. Dieses Skript prueft die Bedingungen (a)–(e) aus dem
Vorschlag und bricht mit Exit 1 ab, sobald eine verletzt ist. Der Waechter
startet den Agenten nur nach Exit 0.

  (b) kein Prod-Zugang: keine SSH-Schluessel, kein ~/.secrets, kein Docker-Socket
  (b) keine fremden Zugangsdaten in der Umgebung (Allowlist)
  (c) jedes Repo im Arbeitsbereich ohne Remote oder nur mit Remote in der Sandbox-Org
  (c) GH_TOKEN darf in KEINEM Repo ausserhalb der Sandbox-Org schreiben —
      geprueft gegen die GitHub-API ueber alle sichtbaren Repos (Invariante,
      keine Stichprobe)
  (e) IIL_SANDBOX=1 gesetzt

Nur Standardbibliothek: der Container soll nichts nachladen muessen.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ERLAUBTE_ZUGANGSDATEN = {"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "GH_TOKEN"}
ZUGANGSDATEN_MUSTER = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|PRIVATE|CREDENTIAL)", re.IGNORECASE)
SCHLUESSEL_MUSTER = re.compile(r"^(id_[a-z0-9]+|.*\.pem|.*\.key)$")
DOCKER_SOCKETS = ("/var/run/docker.sock", "/run/docker.sock")
GITHUB_API = "https://api.github.com"


def pruefe_kennung(env: dict) -> list[str]:
    return [] if env.get("IIL_SANDBOX") == "1" else ["IIL_SANDBOX=1 fehlt — Start nur ueber sandbox.sh"]


def pruefe_umgebung(env: dict) -> list[str]:
    fremde = sorted(k for k in env if ZUGANGSDATEN_MUSTER.search(k) and k not in ERLAUBTE_ZUGANGSDATEN)
    return [f"fremde Zugangsdaten in der Umgebung: {', '.join(fremde)}"] if fremde else []


def pruefe_dateisystem(home: Path, sockets: tuple[str, ...] = DOCKER_SOCKETS) -> list[str]:
    befunde = []
    if (home / ".secrets").exists():
        befunde.append(f"{home}/.secrets ist eingehaengt")
    ssh = home / ".ssh"
    if ssh.is_dir():
        schluessel = sorted(p.name for p in ssh.iterdir() if SCHLUESSEL_MUSTER.match(p.name) and not p.name.endswith(".pub"))
        if schluessel:
            befunde.append(f"SSH-Schluessel vorhanden: {', '.join(schluessel)}")
    befunde += [f"Docker-Socket erreichbar: {s}" for s in sockets if os.path.exists(s)]
    return befunde


def remote_erlaubt(url: str, org: str) -> bool:
    if not org:
        return False
    return bool(re.match(rf"^(https://github\.com/|git@github\.com:){re.escape(org)}/", url, re.IGNORECASE))


def pruefe_remotes(remotes: dict[str, list[str]], org: str) -> list[str]:
    """remotes: {repo-pfad: [remote-url, …]} — leer heisst rein lokal und ist erlaubt."""
    return [
        f"{repo}: Remote ausserhalb der Sandbox-Org: {url}"
        for repo, urls in sorted(remotes.items())
        for url in urls
        if not remote_erlaubt(url, org)
    ]


def pruefe_token_scope(repos: list[dict], org: str) -> list[str]:
    """repos: Eintraege aus GET /user/repos — Schreibrecht nur innerhalb der Sandbox-Org."""
    fremd = sorted(
        r["full_name"]
        for r in repos
        if (r.get("permissions") or {}).get("push") and r["full_name"].split("/")[0].lower() != (org or "").lower()
    )
    if not fremd:
        return []
    zeige = ", ".join(fremd[:5]) + (f" … (+{len(fremd) - 5})" if len(fremd) > 5 else "")
    return [f"GH_TOKEN schreibt ausserhalb der Sandbox-Org: {zeige}"]


def remotes_im_arbeitsbereich(wurzel: Path) -> dict[str, list[str]]:
    ergebnis = {}
    for git in sorted(wurzel.rglob(".git")):
        repo = git.parent
        aus = subprocess.run(["git", "-C", str(repo), "remote", "-v"], capture_output=True, text=True, check=False).stdout
        ergebnis[str(repo)] = sorted({z.split()[1] for z in aus.splitlines() if len(z.split()) >= 2})
    return ergebnis


def sichtbare_repos(token: str) -> list[dict]:
    repos, seite = [], 1
    while True:
        req = urllib.request.Request(
            f"{GITHUB_API}/user/repos?per_page=100&page={seite}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=30) as antwort:
            teil = json.load(antwort)
        repos += teil
        if len(teil) < 100:
            return repos
        seite += 1


def main() -> int:
    env = dict(os.environ)
    org = env.get("SANDBOX_ORG", "")
    befunde = pruefe_kennung(env) + pruefe_umgebung(env) + pruefe_dateisystem(Path.home())
    befunde += pruefe_remotes(remotes_im_arbeitsbereich(Path(env.get("SANDBOX_ARBEIT", "/arbeit"))), org)
    token = env.get("GH_TOKEN", "")
    if token:
        if not org:
            befunde.append("GH_TOKEN ohne SANDBOX_ORG")
        else:
            try:
                befunde += pruefe_token_scope(sichtbare_repos(token), org)
            except OSError as fehler:
                befunde.append(f"Token-Scope nicht pruefbar: {fehler}")
    if befunde:
        print("Selbstpruefung: KEINE Sandbox", file=sys.stderr)
        for b in befunde:
            print(f"  ✗ {b}", file=sys.stderr)
        return 1
    modus = f"GitHub-Org {org}" if token else "lokal (ohne GitHub)"
    print(f"Selbstpruefung: Sandbox bestaetigt — {modus}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
