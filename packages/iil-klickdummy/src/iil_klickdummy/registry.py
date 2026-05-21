"""Klickdummy Registry — Discovery von Klickdummies + Versionen (v1.1.0).

Scannt ein Repo (oder Cross-Repo) nach `klickdummy/<name>/screens-spec.yaml`
oder `*.yaml`-Specs, extrahiert Metadaten (name, class, title, spec_version,
ADR-Bezug), liest Versions-Historie aus Git und generiert eine statische
Browser-HTML.

Aufruf-Pfade:

    klickdummy-browser                     # repo-lokal, alle Klickdummies
    klickdummy-browser --output X.html     # eigenes Ausgabe-Ziel
    klickdummy-browser --repo <path>       # bestimmtes Repo scannen
    klickdummy-browser --cross-repo --base ~/github  # alle Repos

Pro platform:ADR-211 Rev 14 §Browser. Cross-Repo-Modus folgt in v1.2.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field
from importlib.resources import files

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)


@dataclass
class KlickdummyMeta:
    name: str
    path: str                  # relative Pfad zur Spec
    shell_path: str | None     # relative Pfad zur shell.html (oder None)
    spec_id: str
    spec_version: str
    klickdummy_class: str
    title: str
    adr_local: str | None
    sister_of: list[str] = field(default_factory=list)
    status: str = "active"     # aus ADR-Frontmatter, falls erreichbar
    sunset_after: str | None = None


@dataclass
class VersionInfo:
    spec_version: str          # aus Spec-File auf dem Commit
    commit_sha: str
    commit_date: str           # ISO


def _load_spec(path: pathlib.Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def discover_klickdummies(repo_root: pathlib.Path) -> list[KlickdummyMeta]:
    """Sucht klickdummy/<name>/screens-spec.yaml (Default-Konvention).

    Fallback: docs/01-architektur/mockups/<name>/screens-spec.yaml (meiki-hub).
    """
    out: list[KlickdummyMeta] = []
    candidates: list[pathlib.Path] = []
    for base in ("klickdummy", "docs/01-architektur/mockups"):
        d = repo_root / base
        if d.exists():
            candidates.extend(d.rglob("screens-spec.yaml"))
            candidates.extend(d.rglob("spec.yaml"))   # alt: writing-hub-Variante
    seen: set[pathlib.Path] = set()
    for spec_path in candidates:
        if spec_path in seen:
            continue
        seen.add(spec_path)
        spec = _load_spec(spec_path)
        if not spec or "spec_id" not in spec:
            continue
        rel = spec_path.relative_to(repo_root)
        name = rel.parent.name
        # shell.html im gleichen Verzeichnis?
        shell_candidate = spec_path.parent / "shell.html"
        shell_rel = (
            str(shell_candidate.relative_to(repo_root))
            if shell_candidate.exists() else None
        )
        adr = spec.get("adr", {}) or {}
        out.append(KlickdummyMeta(
            name=name,
            path=str(rel),
            shell_path=shell_rel,
            spec_id=spec.get("spec_id", "?"),
            spec_version=str(spec.get("spec_version", "0.0")),
            klickdummy_class=spec.get("class", spec.get("klickdummy_class", "?")),
            title=spec.get("title", name),
            adr_local=adr.get("local"),
            sister_of=adr.get("sister_of", []) or [],
        ))
    return sorted(out, key=lambda k: k.name)


def discover_versions(spec_path: pathlib.Path, repo_root: pathlib.Path) -> list[VersionInfo]:
    """Liest Git-History der Spec-Datei und extrahiert spec_version pro Commit.

    Nur Commits, die spec_version GEÄNDERT haben, kommen in die Liste.
    Sortiert: neueste zuerst.
    """
    if not (repo_root / ".git").exists():
        return []
    try:
        rel = spec_path.relative_to(repo_root)
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log", "--pretty=%H|%cI", "--", str(rel)],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    versions: list[VersionInfo] = []
    seen_versions: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) != 2:
            continue
        sha, date = parts
        try:
            blob = subprocess.run(
                ["git", "-C", str(repo_root), "show", f"{sha}:{rel}"],
                capture_output=True, text=True, timeout=5,
            )
            if blob.returncode != 0:
                continue
            data = yaml.safe_load(blob.stdout) or {}
        except (OSError, subprocess.SubprocessError, yaml.YAMLError):
            continue
        v = str(data.get("spec_version", ""))
        if v and v not in seen_versions:
            versions.append(VersionInfo(spec_version=v, commit_sha=sha, commit_date=date))
            seen_versions.add(v)
    return versions


def render_browser_html(
    klickdummies: list[KlickdummyMeta],
    output: pathlib.Path,
    repo_label: str = "(current repo)",
) -> None:
    """Schreibt statische Browser-HTML mit Listbox + iframe."""
    template = files("iil_klickdummy.snippets") / "browser" / "browser.html.tmpl"
    tmpl_text = template.read_text(encoding="utf-8")
    # Klickdummy-Daten als JSON inline embedden (kein externer fetch nötig)
    data = [
        {
            "name": k.name,
            "path": k.path,
            "shell_path": k.shell_path,
            "spec_id": k.spec_id,
            "spec_version": k.spec_version,
            "class": k.klickdummy_class,
            "title": k.title,
            "adr_local": k.adr_local,
            "sister_of": k.sister_of,
        }
        for k in klickdummies
    ]
    html = tmpl_text.replace("__KLICKDUMMIES_JSON__", json.dumps(data, ensure_ascii=False, indent=2))
    html = html.replace("__REPO_LABEL__", repo_label)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


# -- CLI ---------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repo-Root (Default: .)")
    parser.add_argument("--output", default="./klickdummy-browser.html",
                        help="Output-Pfad für Browser-HTML")
    parser.add_argument("--cross-repo", action="store_true",
                        help="(v1.2 — noch nicht implementiert) alle Repos unter --base scannen")
    parser.add_argument("--base", default="~/github",
                        help="Cross-Repo Base (default ~/github)")
    parser.add_argument("--json", action="store_true",
                        help="Statt HTML JSON-Inventory auf stdout")
    args = parser.parse_args(argv)

    if args.cross_repo:
        print("WARN: --cross-repo ist v1.2-Feature, hier noch nicht implementiert.")
        print("      Aktuell wird --repo verwendet.")

    repo_root = pathlib.Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        print(f"FAIL: Repo-Root nicht gefunden: {repo_root}")
        return 2

    print(f"== Klickdummy-Registry (v1.1.0) ==")
    print(f"  Repo : {repo_root}")
    klickdummies = discover_klickdummies(repo_root)
    print(f"  Gefunden: {len(klickdummies)} Klickdummy(ies)")
    for k in klickdummies:
        # Versions-Discovery ist teuer; nur in non-JSON-Modus
        if not args.json:
            print(f"    · {k.name:35s}  v{k.spec_version}  [{k.klickdummy_class}]  ({k.adr_local or 'kein ADR-Ref'})")

    if args.json:
        out = [
            {"name": k.name, "path": k.path, "shell_path": k.shell_path,
             "spec_id": k.spec_id, "spec_version": k.spec_version,
             "class": k.klickdummy_class, "title": k.title,
             "adr_local": k.adr_local, "sister_of": k.sister_of}
            for k in klickdummies
        ]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if not klickdummies:
        print(f"  → keine Klickdummies — keine Browser-HTML generiert.")
        return 0

    out_path = pathlib.Path(args.output).expanduser().resolve()
    render_browser_html(klickdummies, out_path, repo_label=repo_root.name)
    print(f"  → Browser geschrieben: {out_path}")
    return 0


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())
