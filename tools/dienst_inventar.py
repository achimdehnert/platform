#!/usr/bin/env python3
"""Dienst-Inventar ueber alle Hub-Repos (platform#3011, Kriterium 1).

Zaehlt, was heute als Dienst-Kandidat im Bestand liegt — je Fundstelle eine
Zeile, damit ein Konzept darauf aufsetzen kann, statt zu raten. Fuenf Quellen:

    toolkit   Klassen nach ADR-034/036 (``class XToolkit(DomainToolkit)``)
    mgmt      Django-Management-Commands (``management/commands/<name>.py``)
    mcp       MCP-Werkzeuge (``@mcp.tool`` / ``@server.tool`` / ``Tool(name=…)``)
    service   oeffentliche Modulfunktionen in ``services.py`` / ``services/``
    modell    Modelle aus ``iil-assist-core`` (nur dort — der Kern der Familie)

Reproduzierbar: keine Zeitstempel in der Ausgabe, alle Listen sortiert; zwei
Laeufe auf demselben Stand ergeben byte-gleiche Dateien (``--json``, ``--md``).
Repo-Menge = kanonische Registry (``registry_api``, ohne ``lifecycle: archived``)
plus ``ZUSATZ`` (Repos anderer Orgs, die zur Familie gehoeren, aber nicht in
der Registry stehen). Nicht ausgecheckte Repos werden als ``fehlt`` gemeldet,
nicht still uebersprungen — eine Null aus einem fehlenden Klon ist kein Befund.

Mandantendaten: platform ist oeffentlich. Namen, Pfade und Hinweise werden
gegen die Schutzbegriffe des Push-Gates (``tools/checks/mandantendaten_gate.py``)
maskiert, bevor sie in eine Datei gelangen. Fehlt der lokale Begriffs-Cache,
sagt die Ausgabe das (``schutz.cache = false``) — dann gehoert das Ergebnis
nicht ins Repo.

Aufruf:
    python3 tools/dienst_inventar.py --json out.json --md out.md
    python3 tools/dienst_inventar.py --repo risk-hub --kurz
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER / "checks"))
import registry_api as reg  # noqa: E402
from mandantendaten_gate import CACHE as SCHUTZ_CACHE  # noqa: E402
from mandantendaten_gate import lade_cache  # noqa: E402

GITHUB_DIR = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))

# Repos ausserhalb der Registry, die zur iil-assist-Familie gehoeren.
ZUSATZ = ("chat-hub", "iil-assist-core", "doc-hub", "meiki-dms", "bahn-hub")

# Verzeichnisse, die nie Dienst-Kandidaten tragen (Archiv, Fremdcode, Tests).
AUSSCHLUSS = {
    ".git", ".venv", "venv", "site-packages", "node_modules", "_ARCHIVED",
    "_archive", "archive", "tests", "test", "vendor", "migrations", "dist",
    "build", "static", ".mypy_cache", ".ruff_cache", "__pycache__",
}

MASKE = "[mandant]"

RE_TOOLKIT = re.compile(r"^class\s+(\w+)\((?:[\w.]+\.)?(DomainToolkit|\w+Toolkit)\)")
RE_HELP = re.compile(r"^\s*help\s*=\s*(?:_\()?[rf]?[\"']([^\"']{1,120})")
RE_MCP_DEKOR = re.compile(r"^\s*@(?:mcp|server|app)\.tool\b")
RE_MCP_TOOL = re.compile(r"Tool\(\s*name\s*=\s*[\"']([\w.-]+)[\"']")
RE_DEF = re.compile(r"^(?:async\s+)?def\s+([a-zA-Z]\w*)\(")
RE_MODELL = re.compile(r"^class\s+(\w+)\((?:[\w.]*\.)?Model\)")
RE_DOC = re.compile(r"^\s*[rf]?[\"']{3}\s*(.+?)\s*(?:[\"']{3})?\s*$")


def registry_repos() -> list[str]:
    """Kanonische Registry ohne archivierte Repos, plus ZUSATZ."""
    canon = reg.load_canonical()["repos"]
    return sorted((set(canon) - archivierte_repos()) | set(ZUSATZ))


def archivierte_repos() -> set[str]:
    """Registry-Repos mit ``lifecycle: archived`` — bewusst nicht gescannt, aber genannt."""
    canon = reg.load_canonical()["repos"]
    return {
        n for n, e in canon.items()
        if (e.get("lifecycle") or (e.get("rich") or {}).get("lifecycle")) == "archived"
    }


def schutzbegriffe() -> set[str] | None:
    """Begriffe des Mandantendaten-Gates; None, wenn der lokale Cache fehlt."""
    if not SCHUTZ_CACHE.exists():
        return None
    return lade_cache()


def maskiere(text: str, begriffe: set[str]) -> str:
    klein = text.lower()
    for b in begriffe:
        if b in klein:
            text = re.sub(re.escape(b), MASKE, text, flags=re.IGNORECASE)
            klein = text.lower()
    return text


def py_dateien(wurzel: Path):
    for verz, unter, dateien in os.walk(wurzel):
        unter[:] = sorted(u for u in unter if u not in AUSSCHLUSS)
        for name in sorted(dateien):
            if name.endswith(".py") and name != "__init__.py":
                yield Path(verz) / name


def zeilen(pfad: Path) -> list[str]:
    try:
        return pfad.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def erste_docstring_zeile(ls: list[str], ab: int) -> str:
    for z in ls[ab : ab + 3]:
        m = RE_DOC.match(z)
        if m:
            return m.group(1).strip("\"' ")[:120]
        if z.strip() and not z.strip().startswith(("#", "\"\"\"", "'''")):
            break
    return ""


def eintrag(repo: str, quelle: str, name: str, pfad: Path, zeile: int, hinweis: str, wurzel: Path) -> dict:
    return {
        "repo": repo,
        "quelle": quelle,
        "name": name,
        "pfad": str(pfad.relative_to(wurzel)),
        "zeile": zeile,
        "hinweis": hinweis,
    }


def scanne_repo(repo: str, wurzel: Path) -> list[dict]:
    funde: list[dict] = []
    nur_modelle = repo == "iil-assist-core"
    for pfad in py_dateien(wurzel):
        rel = pfad.relative_to(wurzel)
        ls = zeilen(pfad)
        ist_mgmt = "management" in rel.parts and "commands" in rel.parts
        ist_service = pfad.name == "services.py" or "services" in rel.parts[:-1]
        if ist_mgmt:
            hilfe = next((m.group(1) for z in ls if (m := RE_HELP.match(z))), "")
            funde.append(eintrag(repo, "mgmt", pfad.stem, pfad, 1, hilfe, wurzel))
        for nr, z in enumerate(ls, 1):
            if m := RE_TOOLKIT.match(z):
                funde.append(eintrag(repo, "toolkit", m.group(1), pfad, nr, m.group(2), wurzel))
            if nur_modelle:
                if m := RE_MODELL.match(z):
                    funde.append(eintrag(repo, "modell", m.group(1), pfad, nr, erste_docstring_zeile(ls, nr), wurzel))
                continue
            if RE_MCP_DEKOR.match(z):
                name = next((d.group(1) for d in map(RE_DEF.match, ls[nr : nr + 4]) if d), "?")
                funde.append(eintrag(repo, "mcp", name, pfad, nr, "", wurzel))
            elif m := RE_MCP_TOOL.search(z):
                funde.append(eintrag(repo, "mcp", m.group(1), pfad, nr, "", wurzel))
            if ist_service and (m := RE_DEF.match(z)) and not m.group(1).startswith("_"):
                funde.append(eintrag(repo, "service", m.group(1), pfad, nr, erste_docstring_zeile(ls, nr), wurzel))
    return funde


def inventar(repos: list[str], begriffe: set[str] | None = None) -> dict:
    funde: list[dict] = []
    fehlt: list[str] = []
    for repo in repos:
        wurzel = GITHUB_DIR / repo
        if not (wurzel / ".git").exists():
            fehlt.append(repo)
            continue
        funde.extend(scanne_repo(repo, wurzel))
    maskiert = 0
    if begriffe:
        for f in funde:
            for feld in ("name", "pfad", "hinweis"):
                neu = maskiere(f[feld], begriffe)
                if neu != f[feld]:
                    f[feld] = neu
                    maskiert += 1
    funde.sort(key=lambda f: (f["repo"], f["quelle"], f["pfad"], f["zeile"], f["name"]))
    return {
        "schema": "dienst-inventar/1",
        "repos_geprueft": [r for r in repos if r not in fehlt],
        "repos_fehlt": fehlt,
        "repos_archiviert": sorted(archivierte_repos() - set(repos)),
        "summe": len(funde),
        "je_quelle": dict(sorted(Counter(f["quelle"] for f in funde).items())),
        "je_repo": dict(sorted(Counter(f["repo"] for f in funde).items())),
        "schutz": {"cache": begriffe is not None, "maskiert": maskiert},
        "funde": funde,
    }


def als_markdown(inv: dict) -> str:
    quellen = ["toolkit", "mgmt", "mcp", "service", "modell"]
    schutz = inv["schutz"]
    zl = ["# Dienst-Inventar (platform#3011, Kriterium 1)", ""]
    zl.append(f"Repos geprueft: {len(inv['repos_geprueft'])} · fehlt (nicht ausgecheckt): "
              f"{', '.join(inv['repos_fehlt']) or '—'} · archiviert (nicht gescannt): "
              f"{', '.join(inv['repos_archiviert']) or '—'} · Funde: {inv['summe']} · "
              f"Schutzbegriffe: {'maskiert (' + str(schutz['maskiert']) + ' Felder)' if schutz['cache'] else 'OHNE CACHE — nicht veroeffentlichen'}")
    zl += ["", "| Repo | " + " | ".join(quellen) + " | Summe |", "|---|" + "---|" * (len(quellen) + 1)]
    je = Counter()
    for f in inv["funde"]:
        je[(f["repo"], f["quelle"])] += 1
    for repo in inv["repos_geprueft"]:
        werte = [je[(repo, q)] for q in quellen]
        if sum(werte) == 0:
            continue
        zl.append(f"| {repo} | " + " | ".join(str(w) for w in werte) + f" | {sum(werte)} |")
    zl += ["", "## Toolkits, MCP-Werkzeuge, Modelle (vollstaendig)", "",
           "| Repo | Quelle | Name | Fundstelle | Hinweis |", "|---|---|---|---|---|"]
    for f in inv["funde"]:
        if f["quelle"] in ("toolkit", "mcp", "modell"):
            zl.append(f"| {f['repo']} | {f['quelle']} | `{f['name']}` | `{f['pfad']}:{f['zeile']}` | {f['hinweis']} |")
    zl += ["", "## Management-Commands (vollstaendig)", "", "| Repo | Name | Hilfe |", "|---|---|---|"]
    for f in inv["funde"]:
        if f["quelle"] == "mgmt":
            zl.append(f"| {f['repo']} | `{f['name']}` | {f['hinweis']} |")
    zl += ["", "Service-Funktionen stehen nur in der JSON-Ausgabe (Menge)."]
    return "\n".join(zl) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", action="append", help="nur dieses Repo (mehrfach moeglich)")
    ap.add_argument("--json", type=Path, help="Inventar als JSON schreiben")
    ap.add_argument("--md", type=Path, help="Inventar als Markdown schreiben")
    ap.add_argument("--kurz", action="store_true", help="nur die Summenzeile")
    args = ap.parse_args()

    repos = sorted(args.repo) if args.repo else registry_repos()
    inv = inventar(repos, schutzbegriffe())
    if args.json:
        args.json.write_text(json.dumps(inv, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.md:
        args.md.write_text(als_markdown(inv), encoding="utf-8")
    schutz = inv["schutz"]
    print(f"dienst-inventar: {inv['summe']} Funde in {len(inv['repos_geprueft'])} Repos "
          f"({', '.join(f'{q}={n}' for q, n in inv['je_quelle'].items())})"
          + (f" · fehlt: {', '.join(inv['repos_fehlt'])}" if inv["repos_fehlt"] else "")
          + (f" · maskiert: {schutz['maskiert']}" if schutz["cache"] else " · WARN: Schutzbegriffe ohne Cache"))
    if not args.kurz and not args.json and not args.md:
        for repo, n in inv["je_repo"].items():
            print(f"  {repo:24s} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
