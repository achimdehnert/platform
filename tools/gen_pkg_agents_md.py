#!/usr/bin/env python3
"""AGENTS.md-Generator für PyPI-Fleet-Pakete (#2075 K2, Schema pkg-agents-v1).

Erzeugt aus einem Paket-Checkout eine schema-konforme AGENTS.md — generiert,
nicht handgepflegt (Drift-Lehre „hand-verteilte Kopie"). Quelle der Fakten:
pyproject.toml (Name, Beschreibung, Extras, requires-python), Verzeichnis-
Layout (Public-API-Module), .github/workflows (Publish-Pfad).

    python3 tools/gen_pkg_agents_md.py <checkout-dir> [--write]

Ohne --write: Ausgabe auf stdout. Konformität prüft tools/check_agents_md.py.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MARKER = "Schema: pkg-agents-v1"


def _pyproject(text: str) -> dict:
    out = {}
    for key in ("name", "description", "requires-python"):
        m = re.search(rf'^\s*{key}\s*=\s*"([^"]*)"', text, re.MULTILINE)
        if m:
            out[key] = m.group(1)
    m = re.search(
        r"\[project\.optional-dependencies\](.*?)(?=^\[|\Z)", text, re.M | re.S
    )
    out["extras"] = (
        sorted(set(re.findall(r"^(\w[\w.-]*)\s*=", m.group(1), re.M))) if m else []
    )
    return out


def _public_modules(root: Path) -> list[str]:
    mods: list[str] = []
    for base in (root / "src", root):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                mods.append(child.name)
        if mods:
            break
    return mods


def _publish_info(root: Path) -> str:
    wf_dir = root / ".github" / "workflows"
    pubs = (
        sorted(p.name for p in wf_dir.glob("publish*.yml")) if wf_dir.is_dir() else []
    )
    if not pubs:
        return (
            "Kein publish-Workflow im Repo — Release-Pfad siehe "
            "platform `registry/pypi-fleet.yaml` (ADR-266)."
        )
    modes = []
    for p in pubs:
        text = (wf_dir / p).read_text(encoding="utf-8", errors="replace")
        mode = "OIDC" if re.search(r"id-token:\s*write", text) else "Token (Alt-Pfad)"
        modes.append(f"`{p}` ({mode})")
    return (
        "Publish via "
        + ", ".join(modes)
        + " — nie manuell (ADR-226/266; Release nur über CI)."
    )


def generate(root: Path) -> str:
    meta = _pyproject(
        (root / "pyproject.toml").read_text(encoding="utf-8", errors="replace")
    )
    dist = meta.get("name", root.name)
    desc = (
        meta.get("description", "").strip()
        or "(keine description in pyproject.toml — nachtragen)"
    )
    reqpy = meta.get("requires-python", "?")
    mods = _public_modules(root)
    mod_lines = (
        "\n".join(f"- `{m}`" for m in mods)
        or "- (keine Top-Level-Module erkannt — prüfen)"
    )
    extras = meta.get("extras") or []
    extra_line = (
        "\n\nExtras: " + ", ".join(f"`{dist}[{e}]`" for e in extras) if extras else ""
    )
    return f"""# {dist} — Agent-Kontext

> Schema: pkg-agents-v1 · geprüft von `platform/tools/check_agents_md.py` ·
> GENERIERT von `platform/tools/gen_pkg_agents_md.py` (#2075 K2, ADR-266) —
> nicht von Hand pflegen; Fakten-Drift → Generator erneut laufen lassen.

## Zweck

{desc}

Details und Nutzungsbeispiele: `README.md`. Dieses Paket ist Teil der
iil-PyPI-Fleet (Programm: platform ADR-266 / #2075).

## Setup & Test (Einstiegskommando)

Ein Kommando, frischer Clone, Python {reqpy}:

```bash
make setup && make test
```

Keine weiteren Vorbedingungen (kein Postgres, keine Env-Variablen) — wäre das
falsch, ist es ein Schema-Verstoß und gehört hier dokumentiert.

## Public API

Top-Level-Module:

{mod_lines}{extra_line}

## Architektur-Constraints

- Library, kein App-Code: keine Deploy-/Prod-Kopplung.
- Änderungen an der Public API sind Semver-relevant (Frühwarn-Metrik #2075 K3).
- CI-Kontrakt: reusable `_ci-pypi.yml` (ADR-226); `make test` muss dem
  CI-Testlauf entsprechen.

## Release

{_publish_info(root)}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkout", type=Path)
    ap.add_argument(
        "--write", action="store_true", help="nach <checkout>/AGENTS.md schreiben"
    )
    args = ap.parse_args()
    text = generate(args.checkout)
    if args.write:
        (args.checkout / "AGENTS.md").write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.checkout / 'AGENTS.md'}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
