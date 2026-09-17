#!/usr/bin/env python3
"""PreToolUse(Agent) gate — Delegations-Briefe paralleler Umsetzungs-Subagenten.

GATE_HEADER (KONZ-038 D8):
  "slug": "parallel-subagents-brief-overlap"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-17"
  "evidence": "tools/claude-hooks/tests/test_subagent_brief_gate.py"

Hintergrund: Retro `session-retro-2026-09-14-apo-hub-40c069.md` Befunde #4–#6,
platform#3167 (Gate-Pflicht, Owner-„go" 2026-09-17). Acht Fix-Subagenten liefen
parallel auf demselben Repo. Zwei schrieben ihren PR-Body in DIESELBE
Scratchpad-Datei (#5, apo-hub#117 bekam den falschen Body), drei Import-
Konflikte entstanden in `views.py`/`forms.py`, weil die Briefs Funktionen
eingrenzten, aber nicht den Dateikopf (#6). Die erste Hälfte des Slugs —
blankes `git stash pop` — deckt `block_bare_stash_pop.py` auf Befehlsebene.

Dieser Hook liest den BRIEF, nicht den Befehl: zum Zeitpunkt der Delegation
ist der Overlap zwischen den Briefs die einzige Stelle, an der man ihn noch
vor dem Konflikt sieht. Er verlangt von jedem Umsetzungs-Brief, der Dateien
nennt:

1. **kein `git stash`** — der Brief darf es nicht empfehlen (nur verneint);
2. **eigenes Scratch-Unterverzeichnis** (`…/scratchpad/<agent-slug>/`), das
   kein früherer Brief derselben Sitzung benutzt;
3. **Datei-Overlap mit Zuordnung**: nennt ein früherer Brief derselben Sitzung
   dieselbe Datei, muss GENAU EIN Brief deren Importblock per
   `Importe: <datei>` beanspruchen — sonst wird seriell gemergt, nicht parallel.

Die Overlap-Matrix entsteht inkrementell: jeder durchgelassene Brief wird in
`~/.claude/state/subagent-briefs/<session_id>.json` eingetragen, der nächste
Brief wird gegen alle Einträge der letzten drei Stunden geprüft.

FAIL-OPEN (bewusste Grenze): kein JSON, kein Brief, Lese-Agenten (`Explore`,
`Plan`, `claude-code-guide`), Briefe ohne Dateinennung, Zustandsdatei nicht
schreibbar. Der Hook fängt die Familie „zwei Briefs, eine Datei, keine
Zuordnung"; er sieht NICHT, welche Dateien ein Subagent tatsächlich anfasst,
wenn der Brief sie verschweigt — das steht hier, nicht im Gate-Anspruch.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "parallel-subagents-brief-overlap"

#: Tool-Namen, unter denen Claude Code Subagenten startet (alt: Task).
TOOL_NAMEN = {"Agent", "Task"}
#: Subagent-Typen, die nicht schreiben — kein Umsetzungs-Brief.
LESE_TYPEN = {"explore", "plan", "claude-code-guide"}
#: Einträge älter als das gelten nicht mehr als parallel.
FENSTER_S = 3 * 3600

STATE_DIR = Path(
    os.environ.get("SUBAGENT_BRIEF_STATE", "~/.claude/state/subagent-briefs")
).expanduser()

#: Pfad-Token mit Verzeichnisanteil und Quell-/Doku-Endung.
_DATEI = re.compile(
    r"(?<![\w/])((?:[\w.-]+/)+[\w.-]+\.(?:py|html|md|ya?ml|js|ts|css|json|toml|txt|sh|sql))\b"
)
#: `Importe: a/b.py, c/d.py` — Zuordnung des Importblocks an diesen Brief.
_IMPORTE = re.compile(r"^\s*Importe?\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
#: Scratch-Unterverzeichnis: `…/scratchpad/<slug>` oder `$SCRATCHPAD/<slug>`.
_SCRATCH = re.compile(r"(?:\$SCRATCHPAD|\$\{SCRATCHPAD\}|/scratchpad)/([\w.-]+)/?")
_STASH = re.compile(r"git\s+stash")
_STASH_VERNEINT = re.compile(
    r"\b(kein|keine|nicht|ohne|no|never|nie)\b[^\n]{0,20}`?git\s+stash", re.IGNORECASE
)


def lies_brief(prompt: str) -> dict:
    """Ansprüche eines Briefs: Dateien, Importzuordnung, Scratch-Slug."""
    importe: set[str] = set()
    for m in _IMPORTE.finditer(prompt):
        importe.update(_DATEI.findall(m.group(1)))
    dateien = set(_DATEI.findall(prompt))
    # Der Scratch-Pfad selbst ist keine Repo-Datei.
    dateien = {d for d in dateien if "scratchpad" not in d}
    scratch = _SCRATCH.search(prompt)
    return {
        "dateien": sorted(dateien),
        "importe": sorted(importe),
        "scratch": scratch.group(1) if scratch else "",
    }


def entscheide(prompt: str, fruehere: list[dict]) -> str | None:
    """Grund für ein deny oder None. `fruehere` = Briefe derselben Sitzung."""
    brief = lies_brief(prompt)
    if not brief["dateien"]:
        return None  # kein Umsetzungs-Brief mit Dateinennung — fail-open

    if _STASH.search(prompt) and not _STASH_VERNEINT.search(prompt):
        return (
            "Der Brief empfiehlt `git stash`. `refs/stash` ist über alle Worktrees "
            "geteilt (Realfall apo-hub 2026-09-14, Befund #4) — Rot-Messung per "
            "`git show HEAD:<datei> > <datei>` und zurück; `git stash` nur verneint nennen."
        )

    if not brief["scratch"]:
        return (
            "Der Brief nennt Dateien, aber kein eigenes Scratch-Unterverzeichnis. "
            "Parallele Subagenten teilen das Scratchpad (Realfall apo-hub#117: fremder "
            "PR-Body). Vorschreiben: „Schreibe nur unter $SCRATCHPAD/<agent-slug>/“."
        )

    for alt in fruehere:
        if alt.get("scratch") == brief["scratch"]:
            return (
                f"Scratch-Unterverzeichnis `{brief['scratch']}/` benutzt schon der Brief "
                f"`{alt.get('slug', '?')}` dieser Sitzung — je Subagent ein eigenes."
            )
        gemeinsam = set(alt.get("dateien", [])) & set(brief["dateien"])
        for datei in sorted(gemeinsam):
            bei_alt = datei in alt.get("importe", [])
            bei_neu = datei in brief["importe"]
            if bei_alt and bei_neu:
                return (
                    f"`{datei}` — beide Briefs beanspruchen den Importblock "
                    f"(`{alt.get('slug', '?')}` und dieser). Genau einer darf; sonst seriell mergen."
                )
            if not bei_alt and not bei_neu:
                return (
                    f"`{datei}` steht in diesem Brief UND in `{alt.get('slug', '?')}`, "
                    "ohne dass einer den Importblock zugeordnet bekommt (Realfall apo-hub "
                    "2026-09-14: drei Import-Konflikte in views.py/forms.py). Entweder "
                    f"`Importe: {datei}` in genau einen Brief, oder seriell statt parallel."
                )
    return None


# ── Zustand je Sitzung ───────────────────────────────────────────────────────


def _zustandsdatei(session: str) -> Path:
    sicher = re.sub(r"[^\w.-]", "_", session or "ohne-session")
    return STATE_DIR / f"{sicher}.json"


def lade_fruehere(session: str, cwd: str, jetzt: float | None = None) -> list[dict]:
    jetzt = time.time() if jetzt is None else jetzt
    try:
        eintraege = json.loads(_zustandsdatei(session).read_text())
    except (OSError, ValueError):
        return []
    return [
        e
        for e in eintraege
        if jetzt - float(e.get("ts", 0)) <= FENSTER_S and e.get("cwd", cwd) == cwd
    ]


def merke(
    session: str, cwd: str, brief: dict, slug: str, jetzt: float | None = None
) -> None:
    jetzt = time.time() if jetzt is None else jetzt
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        pfad = _zustandsdatei(session)
        try:
            eintraege = json.loads(pfad.read_text())
        except (OSError, ValueError):
            eintraege = []
        eintraege = [e for e in eintraege if jetzt - float(e.get("ts", 0)) <= FENSTER_S]
        eintraege.append({**brief, "slug": slug, "cwd": cwd, "ts": jetzt})
        pfad.write_text(json.dumps(eintraege, ensure_ascii=False, indent=1))
    except OSError:
        pass  # Zustand ist Komfort, nie Grund für ein deny


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if daten.get("tool_name") not in TOOL_NAMEN:
        return 0
    eingabe = daten.get("tool_input") or {}
    if str(eingabe.get("subagent_type") or "").lower() in LESE_TYPEN:
        return 0
    prompt = eingabe.get("prompt") or ""
    session = daten.get("session_id", "")
    cwd = daten.get("cwd", "")

    fruehere = lade_fruehere(session, cwd)
    grund = entscheide(prompt, fruehere)
    if grund is None:
        brief = lies_brief(prompt)
        if brief["dateien"]:
            slug = (
                brief["scratch"]
                or re.sub(r"\W+", "-", str(eingabe.get("description") or "brief"))[:40]
            )
            merke(session, cwd, brief, slug)
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "Brief ohne Isolation",
            beleg=grund[:200],
            session=session,
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    print(f"⛔ {grund}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
