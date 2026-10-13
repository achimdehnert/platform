#!/usr/bin/env python3
"""PreToolUse(Bash) Hinweis — `gh pr create` unter einem Konto, das den PR selbst freigeben muesste.

GATE_HEADER (KONZ-038 D8):
  "slug": "pr-autor-identitaet-nicht-angewandt"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-10-13"
  "evidence": "tools/claude-hooks/tests/test_pr_autor_identitaet_hinweis.py"

Hintergrund (Retro e50644, Befund 8, Gate-Kandidat §6; Owner-Wort „M4 go" 2026-10-13):
Seit platform#3916 ist der Autor von Governance- und Rechte-PRs die App (`lotse-gh`),
weil GitHub kein Selbst-Approve kennt: ein PR unter dem Konto, dessen Approve er braucht,
bleibt ohne Freigabe-Weg. 44 min nach dieser Festlegung ging chat-hub#187 (aendert
`.github/workflows/ci.yml`) trotzdem unter dem Owner-Konto auf und musste als #188 neu
eroeffnet werden. Die Regel stand im Artefakt, im Moment des Anlegens fragte sie niemand ab.

Dieser Hook fragt sie dort ab. Er meldet, wenn BEIDES gilt:

  1. das aktive gh-Konto (`gh api user`) ist ein Freigeber des Ziel-Repos — es steht
     als `@login` in dessen CODEOWNERS oder ist der Repo-Eigentuemer, und
  2. der Branch beruehrt gegen origin/main eine Datei, die ein Approve braucht:
     eine CODEOWNERS-Zeile nennt das aktive Konto als Owner der Datei, ODER die Datei
     liegt in `governance_pfade` des `sa_m`-Blocks (policies/autonomy-gates.md) —
     derselben Liste, an der tools/pr_merge_sa.py „fehlt: ein Approval
     (Governance-Pfad)" festmacht. Der Realfall #187 lag nur in dieser Liste.

CODEOWNERS wird vom Basis-Ref gelesen (origin/main), weil GitHub die Datei der
Basis anwendet. `lotse-gh … pr create` und `GH_TOKEN=… gh pr create` matchen nicht:
dort ist die Identitaet ausdruecklich gewaehlt.

Nur Hinweis, nie Sperre (Registry-Konvention: neues Gate erst advisory, Scharfschalten
per eigenem PR nach 0-FP-Kalibrierfenster).

FAIL-OPEN: Exit 0 in jedem Fall — kein JSON, anderes Kommando, kein gh, kein Git,
Timeout, Policy nicht lesbar. Ist das Konto nicht ermittelbar, obwohl ein
Approve-Pfad beruehrt ist, kommt eine Zeile "nicht pruefbar", nie ein deny.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Kommando-Zerlegung teilt sich dieser Hook mit dem Geschwister-Hinweis auf
# `gh pr create`; beide liegen im selben Hook-Verzeichnis (Repo und verteilte Kopie).
from pr_anlegen_kollision_hinweis import (  # noqa: E402
    _argumente,
    _arbeitsverzeichnis,
    _git,
    eigene_dateien,
    ist_pr_create,
)

SLUG = "pr-autor-identitaet-nicht-angewandt"
GH_TIMEOUT = 10
MAX_ZEILEN = 5
BASIS_REF = "origin/main"
#: Suchreihenfolge von GitHub fuer die CODEOWNERS-Datei.
CODEOWNERS_ORTE = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
POLICY_RELATIV = Path("policies") / "autonomy-gates.md"
APP_WERKZEUG = "lotse-gh"
REFERENZ = "platform#3916, Retro e50644 Befund 8"

_GOVERNANCE = re.compile(r"^\s*governance_pfade:\s*(\[[^\]]*\])", re.M)
_REMOTE = re.compile(r"[:/]([^/:\s]+)/([^/\s]+?)(?:\.git)?/?$")
_LOGIN = re.compile(r"^@([A-Za-z0-9-]+)$")


def _platform_wurzeln() -> list[Path]:
    """Wo policies/autonomy-gates.md liegen kann — Umgebung (Test), Repo neben dem
    Hook, Platform-Klon (verteilte Kopie unter ~/.claude/hooks)."""
    wurzeln = []
    if os.environ.get("PLATFORM_TOOLS_DIR"):
        wurzeln.append(Path(os.environ["PLATFORM_TOOLS_DIR"]).parent)
    wurzeln.append(Path(__file__).resolve().parents[2])
    wurzeln.append(Path.home() / "github" / "platform")
    return wurzeln


def governance_pfade() -> list[str]:
    """`governance_pfade` aus dem sa_m-Block (leer, wenn nicht lesbar)."""
    for wurzel in _platform_wurzeln():
        try:
            text = (wurzel / POLICY_RELATIV).read_text(encoding="utf-8")
        except OSError:
            continue
        m = _GOVERNANCE.search(text)
        if not m:
            continue
        try:
            return [str(p) for p in json.loads(m.group(1))]
        except ValueError:
            return []
    return []


def ist_governance(pfad: str, pfade: list[str]) -> bool:
    """Dieselbe Regel wie tools/pr_merge_sa.ist_governance: Praefix oder Dateiname."""
    name = pfad.rsplit("/", 1)[-1]
    return any(pfad.startswith(p) or name == p for p in pfade)


def _muster_regex(muster: str) -> re.Pattern[str]:
    """CODEOWNERS-Muster (gitignore-Stil) als Regex: `/` vorn oder in der Mitte
    verankert an der Wurzel, `/` hinten = Verzeichnis, `**` ueber Ebenen, `*` und
    `?` innerhalb einer Ebene. Ein Muster ohne `/` hinten deckt auch alles darunter."""
    kern = muster.strip("/")
    verankert = muster.startswith("/") or "/" in kern
    rx, i = "", 0
    while i < len(kern):
        if kern.startswith("**/", i):
            rx, i = rx + "(?:.*/)?", i + 3
        elif kern.startswith("**", i):
            rx, i = rx + ".*", i + 2
        elif kern[i] == "*":
            rx, i = rx + "[^/]*", i + 1
        elif kern[i] == "?":
            rx, i = rx + "[^/]", i + 1
        else:
            rx, i = rx + re.escape(kern[i]), i + 1
    praefix = "" if verankert else "(?:.*/)?"
    suffix = "/.*" if muster.endswith("/") else "(?:/.*)?"
    return re.compile(f"^{praefix}{rx}{suffix}$")


def _zeilen(codeowners: str) -> list[tuple[str, list[str]]]:
    aus = []
    for zeile in codeowners.splitlines():
        teile = zeile.split("#", 1)[0].split()
        if teile:
            aus.append((teile[0], teile[1:]))
    return aus


def owner_der_datei(pfad: str, codeowners: str) -> list[str]:
    """Logins der LETZTEN passenden Zeile (GitHub-Regel), klein, ohne Teams."""
    owner: list[str] = []
    for muster, namen in _zeilen(codeowners):
        if _muster_regex(muster).match(pfad):
            owner = [m.group(1).lower() for n in namen if (m := _LOGIN.match(n))]
    return owner


def freigeber(codeowners: str, repo_owner: str | None) -> set[str]:
    """Alle Einzel-Logins der CODEOWNERS plus Repo-Eigentuemer, klein."""
    logins = {
        m.group(1).lower()
        for _, namen in _zeilen(codeowners)
        for n in namen
        if (m := _LOGIN.match(n))
    }
    if repo_owner:
        logins.add(repo_owner.lower())
    return logins


def codeowners_der_basis(cwd: str) -> str:
    for ort in CODEOWNERS_ORTE:
        text = _git(["show", f"{BASIS_REF}:{ort}"], cwd)
        if text is not None:
            return text
    return ""


def ziel_repo(argumente: dict[str, str], cwd: str) -> tuple[str, str] | None:
    """(owner, name) aus `-R` oder aus der origin-URL."""
    repo = argumente.get("repo", "")
    if repo.count("/") == 1:
        owner, name = repo.split("/")
        return owner, name
    url = (_git(["remote", "get-url", "origin"], cwd) or "").strip()
    m = _REMOTE.search(url)
    return (m.group(1), m.group(2)) if m else None


def aktives_konto(cwd: str) -> str | None:
    try:
        p = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
            cwd=cwd or None,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    login = p.stdout.strip()
    return login.lower() if p.returncode == 0 and login else None


def approve_pfade(
    dateien: list[str], konto: str | None, codeowners: str, governance: list[str]
) -> list[tuple[str, str]]:
    """(Datei, Grund) fuer jede Datei, die ein Approve braucht. Ohne Konto zaehlt
    nur der Governance-Pfad (fuer die Zeile "nicht pruefbar")."""
    aus = []
    for d in dateien:
        if konto and konto in owner_der_datei(d, codeowners):
            aus.append((d, "Code-Owner"))
        elif ist_governance(d, governance):
            aus.append((d, "Governance-Pfad"))
    return aus


def hinweis(daten: dict) -> str | None:
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not ist_pr_create(kommando):
        return None
    cwd = _arbeitsverzeichnis(kommando, daten.get("cwd") or os.getcwd())
    dateien = eigene_dateien(cwd)
    if not dateien:
        return None
    repo = ziel_repo(_argumente(kommando), cwd)
    codeowners = codeowners_der_basis(cwd)
    governance = governance_pfade()
    konto = aktives_konto(cwd)
    if konto is None:
        if approve_pfade(dateien, None, codeowners, governance):
            return (
                f"Hinweis ({SLUG}): aktives gh-Konto nicht pruefbar, der Branch beruehrt "
                f"aber Approve-Pfade. Autor von Governance-/Rechte-PRs ist die App "
                f"(`{APP_WERKZEUG} <konto> pr create …`, {REFERENZ})."
            )
        return None
    if konto not in freigeber(codeowners, repo[0] if repo else None):
        return None
    treffer = approve_pfade(dateien, konto, codeowners, governance)
    if not treffer:
        return None
    konto_app = repo[0] if repo else "<konto>"
    zeilen = [f"  - {d} ({grund})" for d, grund in treffer[:MAX_ZEILEN]]
    if len(treffer) > MAX_ZEILEN:
        zeilen.append(f"  - … und {len(treffer) - MAX_ZEILEN} weitere")
    return "\n".join(
        [
            f"Hinweis ({SLUG}): aktives gh-Konto `{konto}` ist Freigeber dieses Repos, "
            f"und der Branch beruehrt Pfade, die ein Approve brauchen:",
            *zeilen,
            f"Unter diesem Konto kann der PR nicht freigegeben werden (kein Selbst-Approve). "
            f"Autor ist die App: `{APP_WERKZEUG} {konto_app} pr create …` "
            f"mit denselben Argumenten ({REFERENZ}).",
        ]
    )


def main() -> int:
    daten = json.load(sys.stdin)
    text = hinweis(daten)
    if not text:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "pr create hinweis",
            beleg=text[:200],
            session=str(daten.get("session_id") or ""),
            modus="advisory",
        )
    except Exception:  # noqa: BLE001 — Messung darf den Hinweis nie verhindern
        pass
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": text,
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


def main_sicher() -> int:
    try:
        return main()
    except BaseException as exc:  # noqa: BLE001 — fail-open, auch bei SystemExit
        print(f"{SLUG}: Hook-Fehler, fail-open: {exc!r}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
