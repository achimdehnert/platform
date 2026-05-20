#!/usr/bin/env python3
"""I3 Off-Ramp — Doppelquell-Grenze + Status je Screen.

Anforderungen (platform:ADR-211):
  - Spec hat `off_ramp`-Block mit `doppelquell_grenze: prod-release`
  - Falls Screens definiert: jeder Screen hat `off_ramp_status` aus
    {static, parity-staging, parity-green, removed}

Phase 0 ist ein Berichts-Runner, keine echte Parity-Maschinerie — die entsteht,
sobald der Produkt-Repo Staging hat.

Aufruf:  python3 scripts/klickdummy/check_i3.py <spec>:<schema> [...]
Exit:    0 = PASS, 1 = FAIL, 2 = Setup-Fehler
"""
from __future__ import annotations
import json, pathlib, sys

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)

STATUS = ("static", "parity-staging", "parity-green", "removed")


def load(path: str):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: check_i3.py <spec>:<schema> ...")
        return 2
    errs = 0
    print("== I3 Off-Ramp ==")
    for pair in argv:
        spec_path = pair.split(":", 1)[0]
        print(f"  · {spec_path}")
        try:
            spec = load(spec_path) or {}
            off = spec.get("off_ramp")
            if not off:
                print("      ✗ kein 'off_ramp'-Block deklariert")
                errs += 1
                continue
            if off.get("doppelquell_grenze") != "prod-release":
                print(
                    f"      ✗ doppelquell_grenze={off.get('doppelquell_grenze')!r} "
                    "— erwartet 'prod-release'"
                )
                errs += 1
            screens = spec.get("screens") or []
            if screens:
                counts: dict[str, int] = {s: 0 for s in STATUS}
                bad = []
                for sc in screens:
                    st = sc.get("off_ramp_status", "static")
                    if st not in STATUS:
                        bad.append((sc.get("id", "?"), st))
                    counts[st] = counts.get(st, 0) + 1
                if bad:
                    for sid, st in bad:
                        print(f"      ✗ screen {sid!r}: off_ramp_status={st!r} unzulässig")
                    errs += len(bad)
                summary = ", ".join(f"{k}={v}" for k, v in counts.items() if v)
                print(f"      ✓ {len(screens)} Screen(s) — {summary}")
            else:
                print(f"      ✓ off_ramp-Policy: {off.get('policy', '(unbenannt)')}")
        except FileNotFoundError as e:
            print(f"      ✗ Datei fehlt: {e.filename}")
            errs += 1
        except Exception as e:  # noqa: BLE001
            print(f"      ✗ {type(e).__name__}: {e}")
            errs += 1
    print(f"I3 → {'PASS' if errs == 0 else f'FAIL ({errs})'}")
    return 0 if errs == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    import sys
    return main(sys.argv[1:])
