#!/usr/bin/env python3
"""I2 Prod-Sicherheit — genau EINE Klasse explizit deklariert.

Mock-Prototyp (kein Backend, Target-Mock) ODER Demo-Render (env-gated, in Prod
unerreichbar). Keine Klasse = Verstoß (kein vacuous pass).

Akzeptierte Felder im Spec-Root:
  - `class`              (YAML/JSON, neue Specs)
  - `klickdummy_class`   (additive Variante für Bestands-Manifeste)

Aufruf:  python3 scripts/klickdummy/check_i2.py <spec>:<schema> [...]
Exit:    0 = PASS, 1 = FAIL, 2 = Setup-Fehler
"""
from __future__ import annotations
import json, pathlib, sys

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)

ALLOWED = {"mock", "stub-demo", "story", "spec-demo"}
# Strict-Mode aktiv seit 2026-05-20 (platform:ADR-211 Rev 12 §Migration
# Scoreboard S11 erfüllt: 0 echte Drift-Treffer cross-repo nach Migrations-
# Runde — meiki-hub#23, writing-hub#21, risk-hub#125 alle gemerged). F12
# damit endgültig geschlossen, lange vor Hard-Deadline 2026-08-20.
LEGACY = {}  # Soft-Migrate vorbei
CLASS_KEYS = ("class", "klickdummy_class")


def load(path: str):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: check_i2.py <spec>:<schema> ...")
        return 2
    errs = 0
    print("== I2 Prod-Sicherheit ==")
    for pair in argv:
        spec_path = pair.split(":", 1)[0]
        print(f"  · {spec_path}")
        try:
            spec = load(spec_path) or {}
            cls = None
            for k in CLASS_KEYS:
                if k in spec:
                    cls = spec[k]
                    break
            if cls is None:
                print(
                    f"      ✗ keine Klasse deklariert "
                    f"(erwartet eines von {CLASS_KEYS}, z. B. 'mock')"
                )
                errs += 1
            elif cls in LEGACY:
                # weich, mit Migrations-Hinweis (kein FAIL — sonst CI-Bruch
                # vor abgeschlossener Migration in allen Schwester-Repos)
                print(f"      ⚠ class={cls!r} (Rev-10-Begriff) — bitte auf "
                      f"{LEGACY[cls]!r} migrieren (platform:ADR-211 Rev 11, 4-Pattern)")
            elif cls not in ALLOWED:
                print(f"      ✗ class={cls!r} nicht in {sorted(ALLOWED)}")
                errs += 1
            else:
                print(f"      ✓ class={cls}")
        except FileNotFoundError as e:
            print(f"      ✗ Datei fehlt: {e.filename}")
            errs += 1
        except Exception as e:  # noqa: BLE001
            print(f"      ✗ {type(e).__name__}: {e}")
            errs += 1
    print(f"I2 → {'PASS' if errs == 0 else f'FAIL ({errs})'}")
    return 0 if errs == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    import sys
    return main(sys.argv[1:])
