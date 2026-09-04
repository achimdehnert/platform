#!/usr/bin/env python3
"""Enforcement-Gate für ADR-278: PyPI-Publish muss OIDC Trusted Publishing sein.

Lehnt jede `*publish*.yml` ab, die token-basiertes PyPI-Publishing nutzt statt
OIDC Trusted Publishing. Drei Erkennungswege, jeder für sich ein Fund:

1. **pypa-Action mit password-Input**: `pypa/gh-action-pypi-publish` trägt einen
   `password:`-Input — das deaktiviert Trusted Publishing (pypa-Action-Warnung
   "disabling Trusted Publishing").
2. **Publish-Kommando in einem run:-Block**: `twine upload`, `uv publish`,
   `hatch publish`, `flit publish` oder `poetry publish` — jedes davon ist ein
   Token-Upload, den die pypa-Action (OIDC) ersetzen soll.
3. **Token-Env gesetzt**: `TWINE_PASSWORD`, `TWINE_USERNAME`, `UV_PUBLISH_TOKEN`,
   `HATCH_INDEX_AUTH` oder `POETRY_PYPI_TOKEN_*` in einem `env:`-Block (Workflow-,
   Job- oder Step-Ebene) — unabhängig davon, ob im selben Step ein Publish-Kommando
   steht (das Secret allein ist schon der Bruch mit "kein Token-Secret mehr nötig").

TestPyPI bleibt in allen drei Fällen unberührt (ADR-278: "TestPyPI bleibt unberührt").

Der Check prüft den **Workflow-Input/-Text**, nicht die Existenz eines Secrets — ein
Repo darf seinen Token-Secret behalten, bis die Trusted-Publisher-Bindung bewiesen ist
(ADR-266: nie Token ohne Binding-Beweis raus), solange der Workflow-Input/-Aufruf weg ist.

Befristete Ausnahmen laufen über eine generische, git-getrackte Allowlist-Datei
(Default: `tools/oidc_allowlist.txt`, überschreibbar via `ADR278_ALLOWLIST_FILE`),
NICHT über einen Sonderfall im Guard-Code selbst — siehe `load_allowlist()`.

Nutzung:
  python3 tools/check_publish_oidc_auth.py                 # scannt .github/workflows/*publish*.yml (warn)
  python3 tools/check_publish_oidc_auth.py --block         # Exit 1 bei Fund (abzgl. Allowlist)
  python3 tools/check_publish_oidc_auth.py path/to/publish.yml [...]

Exit: 0 = sauber (oder warn-Modus / vollständig allowlisted), 1 = Fund im
--block-Modus / Parse-Fehler im --block-Modus.
"""

from __future__ import annotations

import glob
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("check_publish_oidc_auth: PyYAML fehlt (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

PYPA_ACTION = "pypa/gh-action-pypi-publish"

DEFAULT_ALLOWLIST_FILE = "tools/oidc_allowlist.txt"

# (Anzeigename, Regex) — jede dieser Zeilen in einem run:-Block ist ein
# Token-basierter Publish-Aufruf, den die pypa-Action (OIDC) ersetzen soll.
# "python -m twine upload" matcht über dieselbe Regex mit ("twine upload" ist
# darin als Teilstring enthalten).
TOKEN_PUBLISH_COMMANDS: list[tuple[str, re.Pattern[str]]] = [
    ("twine upload", re.compile(r"\btwine upload\b")),
    ("uv publish", re.compile(r"\buv publish\b")),
    ("hatch publish", re.compile(r"\bhatch publish\b")),
    ("flit publish", re.compile(r"\bflit publish\b")),
    ("poetry publish", re.compile(r"\bpoetry publish\b")),
]

TOKEN_ENV_VAR_NAMES = {
    "TWINE_PASSWORD",
    "TWINE_USERNAME",
    "UV_PUBLISH_TOKEN",
    "HATCH_INDEX_AUTH",
}
POETRY_TOKEN_ENV_RE = re.compile(r"^POETRY_PYPI_TOKEN_")


def _is_token_env_var(key: str) -> bool:
    return key in TOKEN_ENV_VAR_NAMES or bool(POETRY_TOKEN_ENV_RE.match(key))


def _is_testpypi(with_block: dict) -> bool:
    url = str(
        with_block.get("repository-url") or with_block.get("repository_url") or ""
    )
    return "test.pypi.org" in url


def _targets_testpypi(*texts: str) -> bool:
    """TestPyPI bleibt unberührt (ADR-278) — auch für run:/env:-Funde."""
    haystack = " ".join(texts).lower()
    return "test.pypi.org" in haystack or "testpypi" in haystack


def _env_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _scan_env_block(env: dict, path: Path, job_name: str, scope: str) -> list[str]:
    if not env:
        return []
    context = " ".join(str(v) for v in env.values())
    violations: list[str] = []
    for key in env:
        if not _is_token_env_var(str(key)):
            continue
        if _targets_testpypi(context):
            continue
        violations.append(
            f"{path}: Job '{job_name}' {scope} setzt Token-Env '{key}' → OIDC "
            f"deaktiviert (ADR-278). Env-Variable/Secret entfernen, OIDC Trusted "
            f"Publishing (pypa/gh-action-pypi-publish, id-token: write) nutzen."
        )
    return violations


def scan_file(path: Path) -> list[str]:
    """Return list of violation messages for one workflow file."""
    violations: list[str] = []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - Parse-Fehler ist selbst ein Befund
        return [f"{path}: YAML nicht parsebar ({exc})"]
    if not isinstance(doc, dict):
        return violations

    violations.extend(
        _scan_env_block(_env_dict(doc.get("env")), path, "*", "(Workflow-level env)")
    )

    for job_name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        job_env = _env_dict(job.get("env"))
        violations.extend(_scan_env_block(job_env, path, job_name, "(Job-level env)"))

        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            step_name = str(
                step.get("name") or step.get("uses") or step.get("run") or "?"
            )

            uses = str(step.get("uses") or "")
            if PYPA_ACTION in uses:
                with_block = step.get("with") or {}
                if (
                    isinstance(with_block, dict)
                    and "password" in with_block
                    and not _is_testpypi(with_block)
                ):
                    violations.append(
                        f"{path}: Job '{job_name}' Step '{step_name}' nutzt password-Input "
                        f"im PyPI-Upload → OIDC deaktiviert (ADR-278). password-Zeile entfernen."
                    )

            step_env = _env_dict(step.get("env"))
            violations.extend(
                _scan_env_block(step_env, path, job_name, f"Step '{step_name}' env")
            )

            run = step.get("run")
            if isinstance(run, str):
                context = " ".join(
                    [
                        run,
                        *[str(v) for v in step_env.values()],
                        *[str(v) for v in job_env.values()],
                    ]
                )
                if not _targets_testpypi(context):
                    for label, pattern in TOKEN_PUBLISH_COMMANDS:
                        if pattern.search(run):
                            violations.append(
                                f"{path}: Job '{job_name}' Step '{step_name}' führt "
                                f"'{label}' in einem run:-Block aus → Token-basiertes "
                                f"Publishing erkannt (ADR-278). Auf "
                                f"pypa/gh-action-pypi-publish mit OIDC (id-token: write, "
                                f"kein Token/Secret) umstellen."
                            )
    return violations


@dataclass(frozen=True)
class AllowlistEntry:
    """Ein befristeter, git-getrackter Ausnahme-Eintrag — kein Code-Sonderfall."""

    file_path: str
    until: date
    reference: str


def load_allowlist(path: Path) -> list[AllowlistEntry]:
    """Parst `tools/oidc_allowlist.txt`-artige Dateien.

    Zeilenformat: `<workflow-pfad> | <ablauf YYYY-MM-DD> | <referenz>`.
    Leere Zeilen und `#`-Kommentare werden übersprungen. Zeilen ohne gültiges
    Datum oder ohne Pfad-Feld werden ignoriert (kein Crash auf einer kaputten
    Allowlist-Zeile — das wäre selbst ein Fail-open-Risiko).
    """
    if not path.exists():
        return []
    entries: list[AllowlistEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2 or not parts[0]:
            continue
        try:
            until = datetime.strptime(parts[1], "%Y-%m-%d").date()
        except ValueError:
            continue
        reference = parts[2] if len(parts) > 2 else ""
        entries.append(
            AllowlistEntry(file_path=parts[0], until=until, reference=reference)
        )
    return entries


def active_allowlist(
    entries: list[AllowlistEntry], today: date
) -> dict[str, AllowlistEntry]:
    """Nur nicht-abgelaufene Einträge zählen — ein abgelaufener Eintrag wird
    vom Guard ignoriert, der Fund zählt dann wieder (KONZ-052 V4)."""
    return {e.file_path: e for e in entries if e.until >= today}


def collect_targets(argv: list[str]) -> list[Path]:
    files = [a for a in argv if not a.startswith("-")]
    if files:
        return [Path(f) for f in files]
    return [
        Path(p)
        for p in glob.glob(".github/workflows/*publish*.yml")
        + glob.glob(".github/workflows/*publish*.yaml")
    ]


def main(argv: list[str]) -> int:
    block = "--block" in argv
    targets = collect_targets(argv)
    if not targets:
        print("check_publish_oidc_auth: keine publish-Workflows gefunden (ok).")
        return 0

    allowlist_file = Path(
        os.environ.get("ADR278_ALLOWLIST_FILE", DEFAULT_ALLOWLIST_FILE)
    )
    active = active_allowlist(load_allowlist(allowlist_file), date.today())

    blocking_violations: list[str] = []
    allowlisted: list[tuple[str, AllowlistEntry]] = []
    for path in targets:
        if not path.exists():
            continue
        violations = scan_file(path)
        if not violations:
            continue
        entry = active.get(str(path))
        if entry is not None:
            for v in violations:
                allowlisted.append((v, entry))
        else:
            blocking_violations.extend(violations)

    if allowlisted:
        print(f"ℹ️  Befristet allowlisted ({allowlist_file}):")
        for v, entry in allowlisted:
            print(f"  - {v}  [bis {entry.until.isoformat()}, {entry.reference}]")

    if blocking_violations:
        header = "❌ ADR-278-Verstoß" if block else "⚠️  ADR-278-Warnung"
        print(f"{header}: token-basiertes PyPI-Publishing gefunden:")
        for v in blocking_violations:
            print(f"  - {v}")
        return 1 if block else 0
    print(
        f"✅ ADR-278: {len(targets)} publish-Workflow(s) sind OIDC-only "
        f"(kein password-Input, kein Token-Publish-Kommando, kein Token-Env)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
