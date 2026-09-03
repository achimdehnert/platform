#!/usr/bin/env python3
"""Future-Readiness Zug A (platform#2787): SECURITY.md + THIRD_PARTY_NOTICES.md je Repo.

CLI:
    python3 tools/welle_security_notices.py <owner/repo> <lokale-arbeitskopie> \
        [--pypi-cache DIR] [--dry-run]

Erzeugt in der Arbeitskopie:
  1. SECURITY.md aus docs/templates/SECURITY.md (Platzhalter je Repo gefuellt).
     Existiert bereits eine SECURITY.md, wird sie NICHT ueberschrieben.
  2. THIRD_PARTY_NOTICES.md aus requirements*.txt (Wurzel, -r-Includes aufgeloest)
     und pyproject.toml [project].dependencies / optional-dependencies.
     Kein Manifest -> keine Datei.

Reine Doku-Erzeugung, kein Netzwerk-Zwang: --pypi-cache macht Laeufe wiederholbar.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

TEMPLATE_REL_PATH = "docs/templates/SECURITY.md"

MELDEWEG_PVR = (
    "Bitte über GitHubs **Private vulnerability reporting** dieses Repos melden "
    "(Reiter *Security* → *Report a vulnerability*)."
)

RELEASE_HINWEIS_TEXT = " und auf die jeweils letzte veröffentlichte Version"

MAX_SHORT_LICENSE_LEN = 60

_REQ_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$")


# --------------------------------------------------------------------------
# Datentypen
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    name: str  # normalisiert, PEP 503
    raw_name: str  # wie im Manifest geschrieben
    extras: str
    spec: str  # wörtlich aus dem Manifest (Version + ggf. Marker)
    source: str  # Manifestdatei


# --------------------------------------------------------------------------
# SECURITY.md
# --------------------------------------------------------------------------


def meldeweg_text(owner: str, pvr_enabled: bool) -> str:
    """K1: Meldeweg-Text je PVR-Zustand. Keine erfundenen Adressen, keine Fristen."""
    if pvr_enabled:
        return MELDEWEG_PVR
    return (
        f"Bitte den Repo-Owner direkt über GitHub anschreiben (Profil `{owner}`) "
        "oder ein Issue **nur mit dem Label `security` und ohne technische Details** "
        "anlegen — die Details werden dann vertraulich nachgefragt."
    )


def render_security_md(
    template_text: str,
    owner: str,
    pvr_enabled: bool,
    default_branch: str,
    release_hinweis: str,
) -> str:
    text = template_text.replace("{{MELDEWEG}}", meldeweg_text(owner, pvr_enabled))
    text = text.replace("{{DEFAULT_BRANCH}}", default_branch)
    text = text.replace("{{RELEASE_HINWEIS}}", release_hinweis)
    return text


def determine_release_hinweis(has_version_tags: bool) -> str:
    return RELEASE_HINWEIS_TEXT if has_version_tags else ""


# --------------------------------------------------------------------------
# gh/git Zugriffe (impure — bei Bedarf in Tests per monkeypatch ersetzen)
# --------------------------------------------------------------------------


def gh_api(path: str) -> tuple[int, dict | None]:
    proc = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if proc.returncode == 0:
        stdout = proc.stdout.strip()
        return 200, json.loads(stdout) if stdout else None
    stderr = proc.stderr or ""
    if "HTTP 404" in stderr or "Not Found" in stderr:
        return 404, None
    raise RuntimeError(f"gh api {path} fehlgeschlagen: {stderr.strip()}")


def fetch_repo_meta(owner_repo: str) -> dict:
    status, data = gh_api(f"repos/{owner_repo}")
    if status != 200 or data is None:
        raise RuntimeError(f"repos/{owner_repo} nicht lesbar (Status {status})")
    return data


def fetch_pvr_enabled(owner_repo: str) -> bool:
    status, data = gh_api(f"repos/{owner_repo}/private-vulnerability-reporting")
    if status == 404 or data is None:
        return False
    return bool(data.get("enabled", False))


def fetch_has_version_tags(workdir: Path) -> bool:
    subprocess.run(
        ["git", "-C", str(workdir), "fetch", "--tags", "--quiet"],
        capture_output=True,
        check=False,
    )
    proc = subprocess.run(
        ["git", "-C", str(workdir), "tag", "-l", "v*"],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(proc.stdout.strip())


# --------------------------------------------------------------------------
# THIRD_PARTY_NOTICES.md — Manifest-Parser
# --------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """PEP 503: Läufe von -_. zu einem Bindestrich, klein geschrieben."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirement_line(line: str, source: str) -> Requirement | None:
    match = _REQ_RE.match(line)
    if not match:
        return None
    raw_name, extras, spec = match.groups()
    return Requirement(
        name=normalize_name(raw_name),
        raw_name=raw_name,
        extras=extras or "",
        spec=spec.strip(),
        source=source,
    )


def _is_option_or_local(line: str) -> bool:
    if line.startswith(("-e ", "--editable ", "-e", "--editable")):
        return True
    if line.startswith("-"):
        return True  # sonstige Optionen: -i, --index-url, --extra-index-url, --find-links, ...
    if line.startswith((".", "/", "~")):
        return True  # lokale Pfade
    if "://" in line:
        return True  # URL-/VCS-Requirements (git+https://, file://, ...)
    return False


def parse_requirements_file(
    path: Path, base_dir: Path, _seen: set[Path] | None = None
) -> list[Requirement]:
    """Parst eine requirements*.txt, loest -r/--requirement Includes rekursiv auf."""
    seen = _seen if _seen is not None else set()
    resolved = path.resolve()
    if resolved in seen or not path.exists():
        return []
    seen.add(resolved)

    try:
        source_name = str(path.relative_to(base_dir))
    except ValueError:
        source_name = path.name

    results: list[Requirement] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-r ", "--requirement ")):
            include = line.split(None, 1)[1].strip()
            include_path = (path.parent / include).resolve()
            results.extend(parse_requirements_file(include_path, base_dir, seen))
            continue
        if _is_option_or_local(line):
            continue
        req = parse_requirement_line(line, source_name)
        if req:
            results.append(req)
    return results


def parse_pyproject(path: Path) -> list[Requirement]:
    with path.open("rb") as f:
        data = tomllib.load(f)
    project = data.get("project", {})
    source = "pyproject.toml"
    results: list[Requirement] = []
    for line in project.get("dependencies", []) or []:
        req = parse_requirement_line(line.strip(), source)
        if req:
            results.append(req)
    optional = project.get("optional-dependencies", {}) or {}
    for dep_list in optional.values():
        for line in dep_list or []:
            req = parse_requirement_line(line.strip(), source)
            if req:
                results.append(req)
    return results


def collect_requirements(workdir: Path) -> tuple[list[Requirement], list[str]]:
    requirements: list[Requirement] = []
    manifest_files: list[str] = []
    for req_file in sorted(workdir.glob("requirements*.txt")):
        manifest_files.append(req_file.name)
        requirements.extend(parse_requirements_file(req_file, workdir))
    pyproject_path = workdir / "pyproject.toml"
    if pyproject_path.exists():
        pyproject_reqs = parse_pyproject(pyproject_path)
        if pyproject_reqs:
            manifest_files.append("pyproject.toml")
            requirements.extend(pyproject_reqs)
    return requirements, manifest_files


# --------------------------------------------------------------------------
# THIRD_PARTY_NOTICES.md — PyPI-Metadaten
# --------------------------------------------------------------------------


class PypiLookup:
    """Injectable PyPI-Metadaten-Quelle mit optionalem Platten-Cache (K2: Determinismus)."""

    def __init__(self, cache_dir: Path | None = None, fetcher=None):
        self.cache_dir = cache_dir
        self.fetcher = fetcher or self._http_fetch
        self._mem: dict[str, dict | None] = {}

    def get(self, raw_name: str) -> dict | None:
        norm = normalize_name(raw_name)
        if norm in self._mem:
            return self._mem[norm]
        cache_path = self._cache_path(norm)
        if cache_path and cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            info = payload["info"] if payload.get("found") else None
            self._mem[norm] = info
            return info
        info = self.fetcher(raw_name)
        self._mem[norm] = info
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(
                    {"found": info is not None, "info": info},
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        return info

    def _cache_path(self, norm_name: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / f"{norm_name}.json"

    @staticmethod
    def _http_fetch(raw_name: str) -> dict | None:
        url = f"https://pypi.org/pypi/{raw_name}/json"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise
        info = data.get("info", {}) or {}
        return {
            "license_expression": info.get("license_expression"),
            "license": info.get("license"),
            "classifiers": info.get("classifiers") or [],
            "project_urls": info.get("project_urls") or {},
            "home_page": info.get("home_page"),
        }


def resolve_license(info: dict | None) -> str:
    if info is None:
        return "nicht auf PyPI"
    expr = info.get("license_expression")
    if expr:
        return expr
    lic = info.get("license")
    if lic and len(lic) <= MAX_SHORT_LICENSE_LEN and "\n" not in lic:
        return lic
    for classifier in info.get("classifiers") or []:
        if classifier.startswith("License ::"):
            segments = [seg.strip() for seg in classifier.split("::")]
            if segments and segments[-1]:
                return segments[-1]
    return "unbekannt"


def resolve_url(name: str, info: dict | None, spec: str = "") -> str:
    # Direkt-URL-Abhängigkeit (`pkg @ git+https://…`): das Projekt IST die URL —
    # ein PyPI-Link daneben behauptete sonst einen Ort, an dem das Paket nicht liegt
    # (Pilot trading-hub#202: bfagent-core aus dem platform-Monorepo).
    if spec.startswith("@"):
        return spec.lstrip("@").strip().split(";", 1)[0].strip()
    fallback = f"https://pypi.org/project/{name}/"
    if info is None:
        return fallback
    project_urls = info.get("project_urls") or {}
    for key in ("Homepage", "homepage"):
        if project_urls.get(key):
            return project_urls[key]
    for key in ("Source", "Repository", "source", "repository"):
        if project_urls.get(key):
            return project_urls[key]
    if info.get("home_page"):
        return info["home_page"]
    return fallback


def build_notices_table(
    requirements: list[Requirement], manifest_files: list[str], lookup: PypiLookup
) -> str:
    dedup: dict[tuple[str, str, str], Requirement] = {}
    for req in requirements:
        dedup[(req.name, req.spec, req.source)] = req
    unique_reqs = sorted(dedup.values(), key=lambda r: (r.name, r.source))

    rows = []
    for req in unique_reqs:
        info = lookup.get(req.raw_name)
        license_ = resolve_license(info)
        url = resolve_url(req.name, info, req.spec)
        rows.append(f"| {req.name} | {req.spec} | {license_} | {url} | {req.source} |")

    files_str = ", ".join(manifest_files)
    header = (
        "<!-- erzeugt von achimdehnert/platform tools/welle_security_notices.py "
        f"aus {files_str} — nicht von Hand pflegen -->\n\n"
        "# Third-Party Notices\n\n"
        "| Paket | Spezifikation | Lizenz | Projekt | Quelle |\n"
        "| --- | --- | --- | --- | --- |\n"
    )
    footer = (
        "\n\nLizenztexte: siehe die jeweiligen Projekte; dieses Repo bündelt "
        "keine fremden Lizenztexte.\n"
    )
    return header + "\n".join(rows) + footer


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def run(
    owner_repo: str,
    workdir: Path,
    template_path: Path,
    pypi_cache: Path | None,
    dry_run: bool,
) -> int:
    owner = owner_repo.split("/", 1)[0]

    repo_meta = fetch_repo_meta(owner_repo)
    default_branch = repo_meta.get("default_branch", "main")
    pvr_enabled = fetch_pvr_enabled(owner_repo)
    has_tags = fetch_has_version_tags(workdir)
    release_hinweis = determine_release_hinweis(has_tags)

    security_path = workdir / "SECURITY.md"
    if security_path.exists():
        print(f"SECURITY.md existiert bereits in {workdir} — nicht überschrieben.")
    else:
        template_text = template_path.read_text(encoding="utf-8")
        rendered = render_security_md(
            template_text, owner, pvr_enabled, default_branch, release_hinweis
        )
        if dry_run:
            print(f"[dry-run] würde SECURITY.md schreiben ({len(rendered)} Zeichen).")
        else:
            security_path.write_text(rendered, encoding="utf-8")
            print(f"SECURITY.md geschrieben: {security_path}")

    requirements, manifest_files = collect_requirements(workdir)
    if not requirements:
        print(
            "Kein Abhängigkeits-Manifest gefunden — keine THIRD_PARTY_NOTICES.md erzeugt."
        )
    else:
        lookup = PypiLookup(cache_dir=pypi_cache)
        table = build_notices_table(requirements, manifest_files, lookup)
        notices_path = workdir / "THIRD_PARTY_NOTICES.md"
        if dry_run:
            print(
                f"[dry-run] würde THIRD_PARTY_NOTICES.md schreiben "
                f"({len(requirements)} Pakete aus {', '.join(manifest_files)})."
            )
        else:
            notices_path.write_text(table, encoding="utf-8")
            print(
                f"THIRD_PARTY_NOTICES.md geschrieben: {notices_path} ({len(requirements)} Pakete)"
            )

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="owner/repo, z. B. achimdehnert/coach-hub")
    parser.add_argument("workdir", type=Path, help="lokale Arbeitskopie des Repos")
    parser.add_argument(
        "--pypi-cache", type=Path, default=None, help="Cache-Verzeichnis fuer PyPI-JSON"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="nur ausgeben, was entstuende"
    )
    args = parser.parse_args(argv)

    workdir = args.workdir.resolve()
    if not workdir.is_dir():
        print(f"Arbeitskopie nicht gefunden: {workdir}", file=sys.stderr)
        return 1

    template_path = Path(__file__).resolve().parent.parent / TEMPLATE_REL_PATH
    if not template_path.is_file():
        print(f"Vorlage nicht gefunden: {template_path}", file=sys.stderr)
        return 1

    return run(args.repo, workdir, template_path, args.pypi_cache, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
