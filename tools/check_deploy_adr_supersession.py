#!/usr/bin/env python3
"""Deploy-ADR-Supersession-Gate (KONZ-platform-011 / ADR-261).

Verhindert Deployment-ADR-Sprawl: Ein **neues** ADR (ID >= GATE_FROM_ID), dessen
Titel/Dateiname es als Deployment-Strategie-ADR ausweist, MUSS seine Vorgänger via
nicht-leerem `supersedes:` ablösen — sonst wird es Sprawl-Beitrag #N+1.

Realfall, der den Gate motiviert: ADR-021 (`unified-deployment-pattern`) und ADR-120
(`unified-deployment-pipeline`) sind beide `accepted`, beide mit `supersedes: []` —
zwei „Vereinheitlichungen", von denen keine die andere ablöst. Der Gate hätte den
zweiten „unified"-Anlauf ohne Supersession-Eintrag geblockt.

Grandfathering per Nummer: alle ADRs mit ID < GATE_FROM_ID existierten vor der Regel
und werden nicht rückwirkend geflaggt. ADR-261 selbst führt die Regel ein und erfüllt
sie (nicht-leeres `supersedes:`).

Ausnahme (bewusst, begründet): ein neues Deploy-ADR, das legitim nichts ablöst (enge
Ergänzung), setzt `supersedes_waiver: <Begründung>` im Frontmatter ODER einen
`<!-- supersedes-waiver: <Begründung> -->`-Marker im Body.

Stdlib-only (Repo-Konvention für tools/). Exit 1 bei Verstoß.

Usage:
    python tools/check_deploy_adr_supersession.py [ADR-Datei ...]
    # ohne Argumente: alle docs/adr/ADR-*.md (muss auf heutigem Baum grün sein)
"""
from __future__ import annotations

import glob
import os
import re
import sys

GATE_FROM_ID = 261

# Fokussierte Deploy-Strategie-Marker — bewusst NICHT das nackte "pipeline"
# (sonst würden Content-/Research-„pipelines" wie ADR-160 falsch getroffen).
DEPLOY_TITLE_RE = re.compile(
    r"(deployment|deploy-pipeline|deploy-strategy|staging.*prod|prod.*staging"
    r"|promotion.*pipeline|unified-deploy|reliable-deploy)",
    re.IGNORECASE,
)


def adr_id(path: str) -> int | None:
    m = re.search(r"ADR-(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else None


def split_frontmatter(text: str) -> tuple[str, str]:
    """Trennt YAML-Frontmatter-Rohtext vom Body (kein yaml-Import nötig)."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not m:
        return "", text
    return m.group(1), m.group(2)


def _fm_value(fm: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", fm, re.MULTILINE)
    return m.group(1).strip() if m else ""


def title_of(fm: str) -> str:
    return _fm_value(fm, "title")


def status_of(fm: str) -> str:
    return _fm_value(fm, "status").lower()


def has_supersession(fm: str) -> bool:
    """True, wenn `supersedes:` einen nicht-leeren Wert trägt (Inline-Liste oder Block)."""
    m = re.search(r"^supersedes:\s*(.*)$", fm, re.MULTILINE)
    if not m:
        return False
    inline = m.group(1).strip()
    if inline and inline not in ("[]", "~", "null"):
        return True
    # Block-Form: nachfolgende `  - ADR-xxx`-Zeilen
    tail = fm[m.end():]
    for line in tail.splitlines():
        if re.match(r"\s*-\s+\S", line):
            return True
        if line.strip() and not line.startswith((" ", "\t")):
            break
    return False


def has_waiver(fm: str, body: str) -> bool:
    if _fm_value(fm, "supersedes_waiver"):
        return True
    return bool(re.search(r"<!--\s*supersedes-waiver:", body, re.IGNORECASE))


def is_deploy_strategy_adr(fm: str, path: str) -> bool:
    return bool(
        DEPLOY_TITLE_RE.search(os.path.basename(path))
        or DEPLOY_TITLE_RE.search(title_of(fm))
    )


def violation_for(path: str) -> str | None:
    """Gibt eine Verstoß-Meldung zurück, oder None wenn konform."""
    aid = adr_id(path)
    if aid is None or aid < GATE_FROM_ID:
        return None  # grandfathered / kein ADR
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    fm, body = split_frontmatter(text)
    if status_of(fm) not in ("proposed", "accepted"):
        return None  # draft/rejected/superseded interessiert nicht
    if not is_deploy_strategy_adr(fm, path):
        return None
    if has_supersession(fm) or has_waiver(fm, body):
        return None
    return (
        f"{os.path.basename(path)}: Deployment-Strategie-ADR (ID {aid} >= {GATE_FROM_ID}) "
        f"ohne `supersedes:`-Eintrag und ohne `supersedes_waiver:`. "
        f"Ein neues Deploy-ADR muss seine Vorgänger ablösen (KONZ-011/ADR-261) — "
        f"sonst wächst der Sprawl. Setze `supersedes: [...]` oder begründe mit `supersedes_waiver:`."
    )


def main(argv: list[str]) -> int:
    paths = argv[1:] or sorted(
        glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "adr", "ADR-*.md"))
    )
    violations = [v for p in paths if (v := violation_for(p))]
    for v in violations:
        print(f"::error title=Deploy-ADR-Supersession-Gate::{v}", file=sys.stderr)
    if violations:
        print(f"\n{len(violations)} Verstoß/Verstöße gegen den Deploy-ADR-Supersession-Gate.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
