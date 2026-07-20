#!/usr/bin/env python3
"""decommission_check — KONZ-platform-015 REC-3 (Dead-Reference-Gate, Vorbereitung).

Prüft, ob ein Repo git-getrackte Env-/Compose-Dateien referenziert, die in
registry/canonical.yaml `decommissioned:` als tot gemeldet sind (dead_hostnames,
dead_ips) — die Fehlerklasse, die den weltenhub-Redis-500er verursachte
(`.env.prod` referenzierte den toten Container `bfagent_redis`).

Zwei Modi:

  --repo NAME [--env-file PATH ...]   Gate-Modus: EIN Repo, EXIT 1 bei Treffer.
                                       Gedacht als CI-Step vor `compose up`
                                       (Consumer: _deploy-unified.yml, REC-3 —
                                       noch NICHT verdrahtet, s. u.).

  --sweep [--root DIR]                Sweep-Modus: alle lokalen Repo-Checkouts
                                       unter --root (Default ~/github) scannen.

⚠️ Scope-Ehrlichkeit (wire-before-extend, KONZ-015-Lehre): dieses Tool prüft
GIT-GETRACKTE Dateien (.env.prod, .env.staging, docker-compose*.yml) auf dem
lokalen Checkout — das ist eine STATISCHE Annäherung an "aufgelöste
Runtime-Referenzen", nicht deren Ersatz. Ein Wert, der erst zur Laufzeit über
Secrets-Manager/Templating eingespielt wird, entgeht diesem Scan (R4 aus
KONZ-015 §11: "Env-Indirektionen könnten tote Werte vor dem Check verstecken").
Echte Runtime-Auflösung (SSH auf den Host, `docker exec env`) ist ein späterer
Ausbauschritt, kein Teil dieses MVC.

Noch NICHT geschehen (bewusst, "nur vorbereiten" laut Session-Scope):
  - Verdrahtung als CI-Step in _deploy-unified.yml (anderes Repo, shared-ci)
  - Shadow-Mode-Lauf auf weltenhub
  - Scharfschaltung fail-closed

Exit-Codes: 0 = keine Treffer, 1 = Treffer (FUND, kein Tool-Fehler), 2 = Tool-/Config-Fehler.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CANON_PATH = REPO_ROOT / "registry" / "canonical.yaml"

# Dateien, die typischerweise resolved Runtime-Werte tragen (Env/Compose).
# Bewusst eng: keine Test-Fixtures, keine Doku, kein CI-YAML.
DEFAULT_GLOBS = (
    ".env.prod",
    ".env.prod.*",
    ".env.staging",
    ".env.staging.*",
    "docker-compose.prod.yml",
    "docker-compose.staging.yml",
    "docker-compose.yml",
)


def load_dead_markers() -> tuple[list[str], list[str]]:
    canon = yaml.safe_load(CANON_PATH.read_text())
    hostnames: list[str] = []
    ips: list[str] = []
    for entry in canon.get("decommissioned") or []:
        hostnames.extend(entry.get("dead_hostnames") or [])
        ips.extend(entry.get("dead_ips") or [])
    return hostnames, ips


def scan_file(path: Path, hostnames: list[str], ips: list[str]) -> list[str]:
    """Scannt Zeilen, die keine reinen Kommentarzeilen sind.

    Bewusst einfache Heuristik (kein YAML-/dotenv-Parser): eine Zeile, deren
    getrimmter Anfang '#' ist, zählt nicht — sonst schlägt jede Doku-Erwähnung
    eines toten Hostnamens (z.B. "# Uses: bfagent_db via ...") als FUND auf,
    obwohl kein Runtime-Wert betroffen ist. Realbeleg beim ersten Testlauf
    dieses Tools (2026-07-17): weltenhub/docker-compose.prod.yml hatte genau
    diese Reinform (Kommentarzeilen 5+12) — false positive vor diesem Fix.
    Kein Ersatz für echte Runtime-Auflösung (s. Modul-Docstring, R4).
    """
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return []
    hits: list[str] = []
    for line in lines:
        if line.strip().startswith("#"):
            continue
        for marker in hostnames + ips:
            if marker and marker in line and marker not in hits:
                hits.append(marker)
    return hits


def scan_repo(repo_dir: Path, hostnames: list[str], ips: list[str], extra_files: list[str] | None = None) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {}
    candidates = list(extra_files or [])
    for pattern in DEFAULT_GLOBS:
        candidates.extend(str(p) for p in repo_dir.glob(pattern))
    for rel_or_abs in candidates:
        p = Path(rel_or_abs)
        if not p.is_absolute():
            p = repo_dir / p
        if not p.is_file():
            continue
        hits = scan_file(p, hostnames, ips)
        if hits:
            findings[str(p)] = hits
    return findings


def cmd_gate(args: argparse.Namespace) -> int:
    hostnames, ips = load_dead_markers()
    if not hostnames and not ips:
        print("INFO: keine decommissioned-Einträge in registry/canonical.yaml — nichts zu prüfen.")
        return 0
    repo_dir = Path.home() / "github" / args.repo
    if not repo_dir.is_dir():
        print(f"FEHLER: Repo-Checkout nicht gefunden: {repo_dir}", file=sys.stderr)
        return 2
    findings = scan_repo(repo_dir, hostnames, ips, extra_files=args.env_file)
    if findings:
        print(f"🔴 FUND: {args.repo} referenziert dekommissionierte Werte:")
        for path, hits in findings.items():
            print(f"  {path}: {', '.join(hits)}")
        return 1
    print(f"✅ {args.repo}: keine toten Referenzen in den geprüften Dateien.")
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    canon = yaml.safe_load(CANON_PATH.read_text())
    entries = canon.get("decommissioned") or []
    hostnames = [h for e in entries for h in (e.get("dead_hostnames") or [])]
    ips = [i for e in entries for i in (e.get("dead_ips") or [])]
    decommissioned_names = {e.get("name") for e in entries if e.get("name")}
    if not hostnames and not ips:
        print("INFO: keine decommissioned-Einträge in registry/canonical.yaml — nichts zu prüfen.")
        return 0
    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"FEHLER: --root nicht gefunden: {root}", file=sys.stderr)
        return 2
    total_findings: dict[str, dict[str, list[str]]] = {}
    for repo_dir in sorted(p for p in root.iterdir() if p.is_dir() and (p / ".git").exists()):
        if repo_dir.name in decommissioned_names:
            # Ein dekommissioniertes Repo, das in seiner EIGENEN Compose-Datei
            # seine eigenen (jetzt toten) Container-Namen definiert, ist kein
            # Fund — das ist die Definition, nicht eine dangling Referenz von
            # AUSSEN. Realbeleg: bfagent selbst matcht sich sonst immer.
            continue
        findings = scan_repo(repo_dir, hostnames, ips)
        if findings:
            total_findings[repo_dir.name] = findings
    if total_findings:
        print(f"🔴 Sweep-FUND in {len(total_findings)} Repo(s):")
        for repo, findings in total_findings.items():
            for path, hits in findings.items():
                print(f"  {repo}: {path}: {', '.join(hits)}")
        return 1
    print(f"✅ Sweep sauber — {sum(1 for p in root.iterdir() if p.is_dir() and (p / '.git').exists())} Repos geprüft, keine toten Referenzen in getrackten Dateien.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    gate = sub.add_parser("gate", help="Ein Repo gegen decommissioned: prüfen")
    gate.add_argument("--repo", required=True, help="Repo-Name unter ~/github/")
    gate.add_argument("--env-file", action="append", default=[], help="Zusätzliche Datei(en) prüfen (Pfad relativ zum Repo oder absolut)")
    gate.set_defaults(func=cmd_gate)

    sweep = sub.add_parser("sweep", help="Alle lokalen Repo-Checkouts scannen")
    sweep.add_argument("--root", default="~/github", help="Wurzelverzeichnis der Checkouts (Default ~/github)")
    sweep.set_defaults(func=cmd_sweep)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
