#!/usr/bin/env python3
"""Secret-Scan vor jeder Repo-Kopie in die Sandbox (platform#3685, ADR-308 §4.3).

  geheimnis_scan.py <repo>…

Scannt die volle Git-Historie jedes Repos mit gitleaks und bricht bei jedem
Fund ab. Vorher laeuft eine Positivkontrolle: ein frisch angelegtes Repo mit
einem zur Laufzeit erzeugten Kanarien-Token muss gefunden werden, sonst gilt der
Scan als blind und der Lauf startet nicht.

- Regeln: immer die gitleaks-Standardregeln (gitleaks.toml hier), nie die
  .gitleaks.toml des gescannten Repos — dessen Allowlist koennte Funde verdecken.
- Ausnahmen: nur Fingerprints aus gitleaks-ausnahmen.txt, je mit Owner-Begruendung.
- Ausgabe nennt Regel, Datei, Commit — nie den Wert.

Exit 0 sauber · 1 Fund · 2 Scan nicht verlaesslich (gitleaks fehlt, Positivkontrolle rot).
"""

from __future__ import annotations

import json
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
REGELN = HIER / "gitleaks.toml"
AUSNAHMEN = HIER / "gitleaks-ausnahmen.txt"


def kanarien_token() -> str:
    """GitHub-PAT-Form, zur Laufzeit erzeugt — steht so in keiner Datei des Repos."""
    zeichen = string.ascii_letters + string.digits
    return "ghp" + "_" + "".join(secrets.choice(zeichen) for _ in range(36))


def lege_kanarienrepo_an(ziel: Path) -> Path:
    ziel.mkdir(parents=True, exist_ok=True)
    git = [
        "git",
        "-C",
        str(ziel),
        "-c",
        "user.name=kanarie",
        "-c",
        "user.email=k@k.invalid",
    ]
    subprocess.run(["git", "init", "-q", str(ziel)], check=True)
    (ziel / "konfig.py").write_text(f'TOKEN = "{kanarien_token()}"\n')
    subprocess.run([*git, "add", "konfig.py"], check=True)
    subprocess.run([*git, "commit", "-qm", "kanarie"], check=True)
    return ziel


def scanne(repo: Path, bericht: Path) -> list[dict]:
    """Funde der vollen Historie (alle Refs), ohne Wert; wirft bei Scan-Fehler."""
    lauf = subprocess.run(
        [
            "gitleaks",
            "git",
            "--no-banner",
            "--redact",
            "--exit-code",
            "0",
            "--config",
            str(REGELN),
            "--gitleaks-ignore-path",
            str(AUSNAHMEN),
            "--report-format",
            "json",
            "--report-path",
            str(bericht),
            str(repo),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if lauf.returncode != 0 or not bericht.exists():
        raise RuntimeError(f"gitleaks auf {repo} gescheitert (Exit {lauf.returncode})")
    return [
        {
            "regel": f["RuleID"],
            "datei": f["File"],
            "zeile": f["StartLine"],
            "commit": f["Commit"][:8],
        }
        for f in json.loads(bericht.read_text() or "[]")
    ]


def main(repos: list[str]) -> int:
    if shutil.which("gitleaks") is None:
        print("Secret-Scan: gitleaks fehlt — kein Lauf ohne Scan", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        try:
            kontrolle = scanne(
                lege_kanarienrepo_an(tmp / "kanarie"), tmp / "kanarie.json"
            )
        except (RuntimeError, subprocess.CalledProcessError) as fehler:
            print(
                f"Secret-Scan: Positivkontrolle nicht ausfuehrbar: {fehler}",
                file=sys.stderr,
            )
            return 2
        if not kontrolle:
            print(
                "Secret-Scan: Positivkontrolle rot — Kanarien-Token nicht gefunden",
                file=sys.stderr,
            )
            return 2
        befunde = 0
        for i, repo in enumerate(repos):
            try:
                funde = scanne(Path(repo), tmp / f"{i}.json")
            except RuntimeError as fehler:
                print(f"Secret-Scan: {fehler}", file=sys.stderr)
                return 2
            for f in funde:
                print(
                    f"  ✗ {repo}: {f['regel']} in {f['datei']}:{f['zeile']} ({f['commit']})",
                    file=sys.stderr,
                )
            befunde += len(funde)
    if befunde:
        print(
            f"Secret-Scan: {befunde} Fund(e) — keine Kopie in die Sandbox",
            file=sys.stderr,
        )
        return 1
    print(f"Secret-Scan: Positivkontrolle gruen, {len(repos)} Repo(s) ohne Fund")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
