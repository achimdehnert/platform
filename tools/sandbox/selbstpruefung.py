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
  (c) Remotes per API aufgeloest: Umbenennung/Transfer aus der Org faellt auf
  (d) Egress nur ueber die Allowlist (ADR-308 §4.3) — mit Gegenproben: direkt und
      per DNS kommt nichts raus, ein gesperrtes Ziel bekommt 403, ein erlaubtes 200
  (d) kein Host-Kontext: Einstellungen/Hooks, Memory, Policies, gh-/Git-Zugaenge
  (e) IIL_SANDBOX=1 gesetzt

Nur Standardbibliothek: der Container soll nichts nachladen muessen.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ERLAUBTE_ZUGANGSDATEN = {"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "GH_TOKEN"}
ZUGANGSDATEN_MUSTER = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|PRIVATE|CREDENTIAL)", re.IGNORECASE
)
SCHLUESSEL_MUSTER = re.compile(r"^(id_[a-z0-9]+|.*\.pem|.*\.key)$")
DOCKER_SOCKETS = ("/var/run/docker.sock", "/run/docker.sock")
GITHUB_API = "https://api.github.com"
# Host-Kontext, der nie in den Container darf (ADR-308 §4.3): Einstellungen samt
# Hooks, Memory, Policies, Uebergabeschleuse, gespeicherte Git-/gh-Zugaenge.
HOST_KONTEXT = (
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/projects",
    ".claude/policies",
    "shared",
    ".config/gh/hosts.yml",
    ".git-credentials",
    ".netrc",
)
# Egress-Gegenproben: direkt (ohne DNS), DNS, gesperrtes und erlaubtes Ziel ueber den Proxy.
DIREKT_PROBE = ("1.1.1.1", 443)
DNS_PROBE = "example.com"
GESPERRTE_PROBE = ("example.com", 443)
OFFENE_PROBE = ("api.github.com", 443)


def pruefe_kennung(env: dict) -> list[str]:
    return (
        []
        if env.get("IIL_SANDBOX") == "1"
        else ["IIL_SANDBOX=1 fehlt — Start nur ueber sandbox.sh"]
    )


def pruefe_umgebung(env: dict) -> list[str]:
    fremde = sorted(
        k
        for k in env
        if ZUGANGSDATEN_MUSTER.search(k) and k not in ERLAUBTE_ZUGANGSDATEN
    )
    return (
        [f"fremde Zugangsdaten in der Umgebung: {', '.join(fremde)}"] if fremde else []
    )


def pruefe_dateisystem(
    home: Path, sockets: tuple[str, ...] = DOCKER_SOCKETS
) -> list[str]:
    befunde = []
    if (home / ".secrets").exists():
        befunde.append(f"{home}/.secrets ist eingehaengt")
    ssh = home / ".ssh"
    if ssh.is_dir():
        schluessel = sorted(
            p.name
            for p in ssh.iterdir()
            if SCHLUESSEL_MUSTER.match(p.name) and not p.name.endswith(".pub")
        )
        if schluessel:
            befunde.append(f"SSH-Schluessel vorhanden: {', '.join(schluessel)}")
    befunde += [f"Docker-Socket erreichbar: {s}" for s in sockets if os.path.exists(s)]
    return befunde


def pruefe_host_kontext(home: Path) -> list[str]:
    gefunden = [p for p in HOST_KONTEXT if (home / p).exists()]
    return [f"Host-Kontext im Container: {', '.join(gefunden)}"] if gefunden else []


def direkt_erreichbar(ziel: tuple[str, int], timeout: float = 5) -> bool:
    try:
        socket.create_connection(ziel, timeout=timeout).close()
        return True
    except OSError:
        return False


def dns_aufloesbar(name: str) -> bool:
    try:
        socket.getaddrinfo(name, 443)
        return True
    except OSError:
        return False


def proxy_status(proxy: str, ziel: tuple[str, int], timeout: float = 10) -> int | None:
    """HTTP-Status der CONNECT-Antwort des Proxys; None, wenn er nicht antwortet."""
    teile = urllib.parse.urlsplit(proxy)
    try:
        with socket.create_connection(
            (teile.hostname, teile.port or 3128), timeout=timeout
        ) as s:
            s.sendall(f"CONNECT {ziel[0]}:{ziel[1]} HTTP/1.1\r\n\r\n".encode())
            zeile = s.recv(256).split(b"\r\n", 1)[0].split()
        return int(zeile[1]) if len(zeile) >= 2 and zeile[1].isdigit() else None
    except OSError:
        return None


def bewerte_egress(
    proxy: str,
    direkt: bool,
    dns: bool,
    gesperrt: int | None,
    offen: int | None,
) -> list[str]:
    if not proxy:
        return ["Egress ohne Allowlist: HTTPS_PROXY fehlt"]
    befunde = []
    if direkt:
        befunde.append(f"direkter Egress offen ({DIREKT_PROBE[0]}:{DIREKT_PROBE[1]})")
    if dns:
        befunde.append(f"DNS nach aussen aufloesbar ({DNS_PROBE})")
    if gesperrt != 403:
        befunde.append(f"Proxy sperrt {GESPERRTE_PROBE[0]} nicht (Status {gesperrt})")
    if offen != 200:
        befunde.append(
            f"Gegenprobe rot: {OFFENE_PROBE[0]} ueber Proxy nicht erreichbar (Status {offen})"
        )
    return befunde


def pruefe_egress(env: dict) -> list[str]:
    proxy = env.get("HTTPS_PROXY", "")
    if not proxy:
        return bewerte_egress("", False, False, None, None)
    return bewerte_egress(
        proxy,
        direkt_erreichbar(DIREKT_PROBE),
        dns_aufloesbar(DNS_PROBE),
        proxy_status(proxy, GESPERRTE_PROBE),
        proxy_status(proxy, OFFENE_PROBE),
    )


def remote_erlaubt(url: str, org: str) -> bool:
    if not org:
        return False
    return bool(
        re.match(
            rf"^(https://github\.com/|git@github\.com:){re.escape(org)}/",
            url,
            re.IGNORECASE,
        )
    )


def pruefe_remotes(remotes: dict[str, list[str]], org: str) -> list[str]:
    """remotes: {repo-pfad: [remote-url, …]} — leer heisst rein lokal und ist erlaubt."""
    return [
        f"{repo}: Remote ausserhalb der Sandbox-Org: {url}"
        for repo, urls in sorted(remotes.items())
        for url in urls
        if not remote_erlaubt(url, org)
    ]


#: Antworten einer Probe, die belegen, dass dem Token das Recht fehlt. Alles andere
#: (auch 422 = Recht da, nur die Eingabe ungueltig) zaehlt als Recht — fail-closed.
VERWEIGERT = (403, 404)
#: Status, den probe_status() fuer eine vom Rate-Limit beantwortete Probe liefert.
#: GitHub sagt dann 403 wie bei fehlendem Recht — ohne diese Trennung belegte ein
#: erschoepftes Kontingent „Recht fehlt“, die Pruefung waere fail-open (#3724).
RATENLIMIT = 429
#: Ref auf einen Null-Commit: mit Schreibrecht 422 („Object does not exist“), ohne 403/404.
SCHREIBPROBE = {"ref": "refs/heads/schreibprobe-nie-angelegt", "sha": "0" * 40}
#: Repo ohne Namen: mit Anlegerecht 422 („name must not be blank“), ohne 403/404.
ANLEGEPROBE = {"name": ""}
#: Actions-Schalter mit Nicht-Boolean: mit Recht 422 (Schema), ohne 403/404 — aendert nie etwas.
ACTIONSPROBE = {"enabled": "schalterprobe-kein-boolean"}


def ausserhalb(voller_name: str, org: str) -> bool:
    return voller_name.split("/")[0].lower() != (org or "").lower()


def ist_ratenlimit(status: int, kopf) -> bool:
    """403/429 mit erschoepftem Kontingent oder Retry-After (sekundaeres Limit)."""
    return status in (403, 429) and (
        kopf.get("x-ratelimit-remaining") == "0" or kopf.get("retry-after") is not None
    )


def gebremst(proben: dict[str, int]) -> list[str]:
    """Vom Rate-Limit beantwortete Proben belegen nichts — weder Recht noch Fehlen."""
    namen = sorted(n for n, status in proben.items() if status == RATENLIMIT)
    if not namen:
        return []
    return [f"Probe vom Rate-Limit beantwortet, kein Beleg: {', '.join(namen)}"]


def pruefe_token_scope(proben: dict[str, int], org: str) -> list[str]:
    """proben: {owner/repo: HTTP-Status der Schreibprobe} — Schreibrecht nur in der Sandbox-Org.

    Das Feld ``permissions`` aus GET /user/repos taugt dafuer nicht: Bei einem
    fine-grained Token zeigt es die Rolle des Nutzers, nicht die des Tokens
    (gemessen 2026-10-05: Admin ja auf allen Spiegeln, obwohl der Token kein
    Administration-Recht hat).
    """
    fremd = sorted(
        n
        for n, status in proben.items()
        if ausserhalb(n, org) and status not in (*VERWEIGERT, RATENLIMIT)
    )
    befunde = gebremst(proben)
    if not fremd:
        return befunde
    zeige = ", ".join(fremd[:5]) + (f" … (+{len(fremd) - 5})" if len(fremd) > 5 else "")
    return [f"GH_TOKEN schreibt ausserhalb der Sandbox-Org: {zeige}", *befunde]


def pruefe_repo_anlegen(status: int, org: str) -> list[str]:
    """Ersatz fuer die im Free-Plan fehlende Sperre oeffentlicher Repos (ADR-308 §4.3, §8.2)."""
    if status == RATENLIMIT:
        return gebremst({f"{org} (Repo anlegen)": status})
    if status in VERWEIGERT:
        return []
    return [f"GH_TOKEN kann in {org} Repos anlegen (HTTP {status})"]


def pruefe_actions_aendern(proben: dict[str, int], org: str) -> list[str]:
    """proben: {owner/repo in der Org: HTTP-Status der Actions-Probe} (ADR-308 §4.3, §8.2).

    Actions aus ist die Grundlage des M0-Profils der Sandbox-Org — der Token darf
    sie nicht einschalten koennen. Ohne Repo keine Probe, also kein Beleg: Befund.
    """
    if not proben:
        return [f"Actions-Probe nicht moeglich: kein Repo in {org} sichtbar"]
    offen = sorted(
        n for n, status in proben.items() if status not in (*VERWEIGERT, RATENLIMIT)
    )
    befunde = gebremst(proben)
    if not offen:
        return befunde
    return [f"GH_TOKEN kann Actions-Einstellungen aendern: {', '.join(offen)}", *befunde]


def pruefe_aufgeloeste_remotes(
    aufloesung: dict[str, str | None], org: str
) -> list[str]:
    """aufloesung: {remote-url: full_name laut GitHub-API oder None}.

    Ein umbenanntes oder transferiertes Repo leitet GitHub weiter — die URL nennt
    noch die Sandbox-Org, der Push landet aber beim neuen Eigentuemer.
    """
    befunde = []
    for url, name in sorted(aufloesung.items()):
        if name is None:
            befunde.append(f"Remote nicht aufloesbar: {url}")
        elif name.split("/")[0].lower() != (org or "").lower():
            befunde.append(f"Remote {url} zeigt nach Umbenennung/Transfer auf {name}")
    return befunde


def repo_aufloesen(url: str, token: str) -> str | None:
    pfad = re.sub(r"^(https://github\.com/|git@github\.com:)", "", url)
    req = urllib.request.Request(
        f"{GITHUB_API}/repos/{pfad.removesuffix('.git')}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as antwort:
            return json.load(antwort).get("full_name")
    except OSError:
        return None


def remotes_im_arbeitsbereich(wurzel: Path) -> dict[str, list[str]]:
    ergebnis = {}
    for git in sorted(wurzel.rglob(".git")):
        repo = git.parent
        aus = subprocess.run(
            ["git", "-C", str(repo), "remote", "-v"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        ergebnis[str(repo)] = sorted(
            {z.split()[1] for z in aus.splitlines() if len(z.split()) >= 2}
        )
    return ergebnis


def probe_status(token: str, pfad: str, daten: dict, methode: str = "POST") -> int:
    """Anfrage ohne Wirkung; liefert nur den HTTP-Status. Netzfehler gehen als OSError hoch."""
    req = urllib.request.Request(
        f"{GITHUB_API}{pfad}",
        method=methode,
        data=json.dumps(daten).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as antwort:
            return antwort.status
    except urllib.error.HTTPError as fehler:
        if ist_ratenlimit(fehler.code, fehler.headers):
            return RATENLIMIT
        return fehler.code


def sichtbare_repos(token: str) -> list[dict]:
    repos, seite = [], 1
    while True:
        req = urllib.request.Request(
            f"{GITHUB_API}/user/repos?per_page=100&page={seite}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
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
    befunde = (
        pruefe_kennung(env) + pruefe_umgebung(env) + pruefe_dateisystem(Path.home())
    )
    befunde += pruefe_host_kontext(Path.home()) + pruefe_egress(env)
    remotes = remotes_im_arbeitsbereich(Path(env.get("SANDBOX_ARBEIT", "/arbeit")))
    befunde += pruefe_remotes(remotes, org)
    token = env.get("GH_TOKEN", "")
    if token:
        if not org:
            befunde.append("GH_TOKEN ohne SANDBOX_ORG")
        else:
            try:
                sichtbar = [r["full_name"] for r in sichtbare_repos(token)]
                fremde = [n for n in sichtbar if ausserhalb(n, org)]
                befunde += pruefe_token_scope(
                    {
                        n: probe_status(token, f"/repos/{n}/git/refs", SCHREIBPROBE)
                        for n in fremde
                    },
                    org,
                )
                befunde += pruefe_repo_anlegen(
                    probe_status(token, f"/orgs/{org}/repos", ANLEGEPROBE), org
                )
                befunde += pruefe_actions_aendern(
                    {
                        n: probe_status(
                            token,
                            f"/repos/{n}/actions/permissions",
                            ACTIONSPROBE,
                            "PUT",
                        )
                        for n in sichtbar
                        if not ausserhalb(n, org)
                    },
                    org,
                )
            except OSError as fehler:
                befunde.append(f"Token-Scope nicht pruefbar: {fehler}")
            urls = {u for us in remotes.values() for u in us if remote_erlaubt(u, org)}
            befunde += pruefe_aufgeloeste_remotes(
                {u: repo_aufloesen(u, token) for u in urls}, org
            )
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
