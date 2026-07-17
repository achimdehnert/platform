#!/usr/bin/env python3
"""validate_registry — Schema-Gate für registry/canonical.yaml (KONZ-platform-015 REC-2).

Prüft die zwei in dieser Konzept-Welle neuen Top-Level-Abschnitte:

  decommissioned:  [{name, date, dead_hostnames[], dead_ips[], note?}, ...]
                    dead_hostnames + dead_ips zusammen dürfen nicht beide leer sein
                    (sonst ein Eintrag ohne jede Wirkung fürs Gate, REC-3).

  overrides:        [{repo, path, reason, owner, expires_at}, ...]
                    Pflichtfelder vollständig; expires_at Pflicht UND darf nicht in
                    der Vergangenheit liegen (D1-Waiver-Vorbild: "ohne Ablaufdatum ->
                    blockiert"; abgelaufen -> ebenfalls blockiert, fail-closed statt
                    Erinnerungs-Mail).

Bewusst NICHT geprüft: `repos:`/`meta:` (das erledigt registry-canonical.py verify
gegen die generierten Views). Dieses Tool ist additiv, kein Ersatz.

Exit-Codes: 0 = sauber, 1 = Schema-Verstoß (blockierend), 2 = Datei nicht lesbar/kein YAML.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CANON_PATH = REPO_ROOT / "registry" / "canonical.yaml"


def _err(msgs: list[str], msg: str) -> None:
    msgs.append(msg)


def validate_decommissioned(entries: list, errors: list[str]) -> None:
    seen_names = set()
    for i, e in enumerate(entries):
        loc = f"decommissioned[{i}]"
        if not isinstance(e, dict):
            _err(errors, f"{loc}: kein Mapping")
            continue
        name = e.get("name")
        if not name:
            _err(errors, f"{loc}: 'name' fehlt")
        elif name in seen_names:
            _err(errors, f"{loc}: doppelter name '{name}'")
        else:
            seen_names.add(name)
        if not e.get("date"):
            _err(errors, f"{loc} ({name}): 'date' fehlt")
        hostnames = e.get("dead_hostnames") or []
        ips = e.get("dead_ips") or []
        if not hostnames and not ips:
            _err(errors, f"{loc} ({name}): weder dead_hostnames noch dead_ips gesetzt — Eintrag ohne Gate-Wirkung")


def validate_overrides(entries: list, errors: list[str]) -> None:
    today = dt.date.today()
    required = ("repo", "path", "reason", "owner", "expires_at")
    for i, e in enumerate(entries):
        loc = f"overrides[{i}]"
        if not isinstance(e, dict):
            _err(errors, f"{loc}: kein Mapping")
            continue
        missing = [f for f in required if not e.get(f)]
        if missing:
            _err(errors, f"{loc}: Pflichtfelder fehlen: {', '.join(missing)} (D1-Waiver-Vorbild: ohne expires_at -> blockiert)")
            continue
        try:
            expires = dt.date.fromisoformat(str(e["expires_at"]))
        except ValueError:
            _err(errors, f"{loc}: expires_at '{e['expires_at']}' ist kein ISO-Datum (YYYY-MM-DD)")
            continue
        if expires < today:
            _err(errors, f"{loc} ({e.get('repo')}/{e.get('path')}): expires_at {expires} ist abgelaufen (heute {today}) — fail-closed, verlängern oder Override entfernen")


def main() -> int:
    try:
        canon = yaml.safe_load(CANON_PATH.read_text())
    except (OSError, yaml.YAMLError) as exc:
        print(f"FEHLER: {CANON_PATH} nicht lesbar/kein valides YAML: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    validate_decommissioned(canon.get("decommissioned") or [], errors)
    validate_overrides(canon.get("overrides") or [], errors)

    if errors:
        print(f"🔴 registry/canonical.yaml Schema-Verstoß ({len(errors)}):")
        for msg in errors:
            print(f"  - {msg}")
        return 1

    n_decom = len(canon.get("decommissioned") or [])
    n_over = len(canon.get("overrides") or [])
    print(f"✅ registry/canonical.yaml Schema OK ({n_decom} decommissioned, {n_over} overrides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
