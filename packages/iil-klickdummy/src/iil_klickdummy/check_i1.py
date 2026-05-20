#!/usr/bin/env python3
"""I1 Spec-first — Spec gegen JSON-Schema validieren.

Aufruf:  python3 scripts/klickdummy/check_i1.py <spec_path>:<schema_path> [...]
Policy:  ~/.claude/policies/klickdummy.md · platform:ADR-211
Exit:    0 = PASS, 1 = FAIL, 2 = Setup-Fehler (fehlende Deps)
"""
from __future__ import annotations
import json, pathlib, sys

try:
    import yaml  # PyYAML
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)

try:
    import jsonschema
except ImportError:
    print("FAIL (setup): jsonschema fehlt. pip install jsonschema")
    sys.exit(2)


def load(path: str):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: check_i1.py <spec>:<schema> ...")
        return 2
    errs = 0
    print("== I1 Spec-first ==")
    for pair in argv:
        if ":" not in pair:
            print(f"  ✗ ungültiger Eintrag: {pair!r}")
            errs += 1
            continue
        spec_path, schema_path = pair.split(":", 1)
        print(f"  · {spec_path}")
        try:
            spec = load(spec_path)
            schema = load(schema_path)
            jsonschema.validate(spec, schema)
            print(f"      ✓ schema-konform ({schema_path})")
        except FileNotFoundError as e:
            print(f"      ✗ Datei fehlt: {e.filename}")
            errs += 1
        except jsonschema.ValidationError as e:
            loc = "/".join(str(p) for p in e.absolute_path) or "(root)"
            print(f"      ✗ Schema-Verletzung @ {loc}: {e.message}")
            errs += 1
        except Exception as e:  # noqa: BLE001
            print(f"      ✗ {type(e).__name__}: {e}")
            errs += 1
    print(f"I1 → {'PASS' if errs == 0 else f'FAIL ({errs})'}")
    return 0 if errs == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    import sys
    return main(sys.argv[1:])
