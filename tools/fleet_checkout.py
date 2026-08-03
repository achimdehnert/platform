#!/usr/bin/env python3
"""Fleet-Checkouts unter `$GITHUB_DIR` herstellen UND aktuell halten.

Ersetzt die Inline-Klon-Schleife aus `sync-drift-meter.yml`, die zwei
belegte Defekte hatte (platform#1508-Triage, 2026-08-03):

1. **Klon-einmal-nie-wieder.** Die Schleife war mit `if [ ! -d "$dir" ]`
   bewacht — ein einmal angelegter Klon wurde nie wieder gezogen. Der
   Drift-Melder urteilte damit ueber den Stand, den ein Repo beim allerersten
   Lauf hatte. Belegt an `design-hub`: der Melder meldete am 2026-08-03
   "`.windsurf/` fehlt in `.gitignore`", obwohl die Zeile dort seit
   2026-06-01 committet ist (`8a0ee9ca`) — ein **Fehlalarm aus einem
   veralteten Klon**, zwei Monate lang.

2. **Owner hartkodiert.** Die Klon-URL stand fest auf `achimdehnert/<repo>`.
   Der Lauf 30798160184 meldete deshalb fuenf Repos als `WARN: <repo> not
   found` auf stdout und ging **still** ueber sie hinweg — der Melder sah aus
   wie eine Vollerhebung. Zwei davon (`iilgmbh/iil-klickdummy`,
   `iilgmbh/iil-voice-agent`) gehoeren zur eigenen Fleet und werden mit
   aufgeloestem Owner jetzt wieder mitgescannt; drei liegen in fremden Orgs
   (`meiki-lra/frist-hub`, `meiki-lra/meiki-hub`, `ttz-lif/ttz-hub`) und
   bleiben bewusst draussen, siehe unten. Der Owner steht seit ADR-234 in
   `registry/canonical.yaml`; hier wird er ueber
   `tools/registry_api.owner()` aufgeloest statt geraten.

**Fremd-Org-Repos werden bewusst NICHT geklont.** Ihre Funde gehoeren in ihr
eigenes Governance-Repo, nicht in ein platform-Issue (`meiki-lra` = LRA,
buergernah; `ttz-lif` = Schulung; `bahn-sqf` = DBAG). Sie erscheinen deshalb
als eigene Kategorie im Abdeckungs-Bericht — als *benannte Grenze*, nicht als
stiller Ausfall. Das ist der Unterschied zum Vorzustand: die Luecke bleibt,
sie ist nur nicht mehr unsichtbar. Gemessen am 2026-08-03: 49 von 52
Fleet-Repos im Scan, 3 benannt draussen.

Aufruf:

    python3 tools/fleet_checkout.py --base ~/github --coverage /tmp/cov.md

Exit-Code: 0 wenn jedes Repo entweder frisch ist oder als Fremd-Org benannt
wurde; 1 wenn ein Repo der **eigenen** Org nicht hergestellt werden konnte
(ein Fetch-Fehler ist kein gruener Zustand — vgl.
`feedback_fetch_failure_is_not_a_green_state`).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import registry_api  # noqa: E402

#: Orgs, deren Repos dieser Melder abdeckt: die eigene Governance-Domaene.
#: `iilgmbh` gehoert dazu — dorthin sind risk-hub/tax-hub/ausschreibungs-hub und
#: die `iil-*`-Bibliotheken migriert (ADR-255); sie sind fachlich dieselbe Fleet,
#: nur unter anderem Org-Namen. Ein erster Entwurf dieses Werkzeugs teilte binaer
#: nach `achimdehnert` und haette 7 eigene Repos aus dem Scan geworfen — im
#: scharfen Trockenlauf vor dem Merge aufgefallen, nicht im Test.
EIGENE_ORGS = ("achimdehnert", "iilgmbh")

#: Grund, warum Fremd-Org-Repos nicht mitgescannt werden — erscheint im Bericht.
#: Betrifft `ttz-lif` (Schulung), `meiki-lra` (LRA, buergernah) und `bahn-sqf`
#: (DBAG): eigene Governance, eigene Issue-Ablage.
FREMD_ORG_GRUND = (
    "Funde gehoeren in das Governance-Repo der jeweiligen Org, "
    "nicht in ein platform-Issue"
)


def _git(
    args: list[str], cwd: Path | None = None, timeout: int = 120
) -> tuple[int, str]:
    """git aufrufen; (returncode, kombinierte Ausgabe)."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def klon_url(owner: str, repo: str, token: str | None) -> str:
    """HTTPS-URL, optional mit Actions-Token.

    Der Token wird NIE zurueckgegeben oder geloggt — Aufrufer geben ihn direkt
    an git weiter. Fehlerausgaben von git werden vor der Ausgabe bereinigt
    (`_ohne_token`), weil ein 404 sonst die komplette URL samt Token in den
    Job-Log schreibt (vgl. `feedback_credentials_in_url_leak_via_error_output`).
    """
    if token:
        return f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
    return f"https://github.com/{owner}/{repo}.git"


def _ohne_token(text: str, token: str | None) -> str:
    return text.replace(token, "***") if token else text


def aktualisieren(ziel: Path, token: str | None) -> tuple[bool, str]:
    """Vorhandenen Klon auf den Remote-Kopf ziehen (shallow)."""
    rc, aus = _git(["fetch", "--depth=1", "origin", "HEAD"], cwd=ziel)
    if rc != 0:
        return False, _ohne_token(aus, token)
    rc, aus = _git(["reset", "--hard", "FETCH_HEAD"], cwd=ziel)
    if rc != 0:
        return False, _ohne_token(aus, token)
    return True, "aktualisiert"


def herstellen(
    ziel: Path, owner: str, repo: str, token: str | None
) -> tuple[bool, str]:
    """Fehlenden Klon anlegen (shallow)."""
    rc, aus = _git(["clone", "--depth=1", klon_url(owner, repo, token), str(ziel)])
    if rc != 0:
        return False, _ohne_token(aus, token)
    return True, "geklont"


def plane(repos: list[str], canon: dict | None = None) -> dict[str, list]:
    """Repos nach Owner einteilen — ohne jedes Netz/Dateisystem.

    Rueckgabe-Schluessel: ``eigene`` (Liste (repo, owner)), ``fremd``
    (Liste (repo, owner)), ``unbekannt`` (Liste repo — kein Owner aufloesbar).
    """
    eigene: list[tuple[str, str]] = []
    fremd: list[tuple[str, str]] = []
    unbekannt: list[str] = []
    for repo in repos:
        besitzer = registry_api.owner(repo, canon)
        if not besitzer:
            unbekannt.append(repo)
        elif besitzer in EIGENE_ORGS:
            eigene.append((repo, besitzer))
        else:
            fremd.append((repo, besitzer))
    return {"eigene": eigene, "fremd": fremd, "unbekannt": unbekannt}


def render_coverage(
    plan: dict, ergebnisse: dict[str, str], fehler: dict[str, str]
) -> str:
    """Abdeckungs-Bericht als Markdown.

    Zweck: die Grenze der Erhebung steht IM Bericht, nicht nur im Job-Log.
    Ein Melder, der 5 von 26 Repos nicht ansieht, darf nicht wie eine
    Vollerhebung aussehen.
    """
    eigene = plan["eigene"]
    fremd = plan["fremd"]
    unbekannt = plan["unbekannt"]
    gesamt = len(eigene) + len(fremd) + len(unbekannt)
    gescannt = len(eigene) - len(fehler)

    lines = ["## Abdeckung des Scans", ""]
    lines.append(
        f"**{gescannt} von {gesamt} Fleet-Repos gescannt** "
        f"({len(fremd)} Fremd-Org, {len(unbekannt)} ohne Owner, "
        f"{len(fehler)} fehlgeschlagen)."
    )

    if fremd:
        lines += ["", f"### Fremd-Org — bewusst nicht gescannt ({FREMD_ORG_GRUND})", ""]
        for repo, besitzer in sorted(fremd):
            lines.append(f"- `{repo}` → `{besitzer}`")

    if unbekannt:
        lines += ["", "### Ohne aufloesbaren Owner (Registry-Luecke)", ""]
        for repo in sorted(unbekannt):
            lines.append(f"- `{repo}` — in `registry/canonical.yaml` ergaenzen")

    if fehler:
        lines += ["", "### Fehlgeschlagen (eigene Org — echter Ausfall)", ""]
        for repo, grund in sorted(fehler.items()):
            lines.append(f"- `{repo}`: {grund.splitlines()[0][:200]}")

    frisch = [r for r, z in ergebnisse.items() if z == "aktualisiert"]
    neu = [r for r, z in ergebnisse.items() if z == "geklont"]
    lines += [
        "",
        f"Klon-Zustand: {len(frisch)} aktualisiert, {len(neu)} neu geklont. "
        "Vor 2026-08-03 wurden vorhandene Klone NIE gezogen — Funde aus "
        "diesem Melder waren bis dahin potenziell Monate alt.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=os.environ.get("GITHUB_DIR", str(Path.home() / "github")),
        help="Wurzel der Fleet-Checkouts (default $GITHUB_DIR oder ~/github)",
    )
    parser.add_argument(
        "--repos", nargs="*", help="Repo-Namen (default: list_megatest_repos)"
    )
    parser.add_argument(
        "--coverage", help="Abdeckungs-Bericht als Markdown hierhin schreiben"
    )
    parser.add_argument("--dry-run", action="store_true", help="nur planen, kein git")
    args = parser.parse_args()

    if args.repos:
        repos = list(args.repos)
    else:
        hier = Path(__file__).resolve().parent.parent
        proc = subprocess.run(
            [sys.executable, str(hier / "scripts" / "list_megatest_repos.py")],
            capture_output=True,
            text=True,
            check=True,
        )
        repos = proc.stdout.split()

    plan = plane(repos)
    basis = Path(args.base)
    token = os.environ.get("GH_FLEET_TOKEN") or os.environ.get("GITHUB_TOKEN")

    ergebnisse: dict[str, str] = {}
    fehler: dict[str, str] = {}

    if not args.dry_run:
        basis.mkdir(parents=True, exist_ok=True)
        for repo, besitzer in plan["eigene"]:
            ziel = basis / repo
            if (ziel / ".git").is_dir():
                ok, info = aktualisieren(ziel, token)
            else:
                ok, info = herstellen(ziel, besitzer, repo, token)
            if ok:
                ergebnisse[repo] = info
            else:
                fehler[repo] = info

    bericht = render_coverage(plan, ergebnisse, fehler)
    print(bericht)
    if args.coverage:
        Path(args.coverage).write_text(bericht)

    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
