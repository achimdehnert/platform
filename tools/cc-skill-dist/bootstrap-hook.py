#!/usr/bin/env python3
"""bootstrap-hook.py — Dry-Run-Aktivierungshilfe für CC-Hooks (ADR-258 Stufe B, REC-11).

Liest die bestehende ~/.claude/settings.json, validiert sie und zeigt den EXAKTEN
SessionEnd-Eintrag, der den verteilten Hook (~/.claude/hooks/reap_worktrees.sh) verdrahtet —
**schreibt aber nie automatisch** (E-2: keine Org-Automatik fasst die secret-haltige
settings.json an). Aktivierung bleibt ein bewusster, reviewbarer Akt pro Maschine.

    python3 tools/cc-skill-dist/bootstrap-hook.py            # zeigt Patch/Status, schreibt nichts
    python3 tools/cc-skill-dist/bootstrap-hook.py --print-snippet   # nur den JSON-Block

Exit: 0 = bereits verdrahtet · 1 = Patch nötig (Snippet ausgegeben) · 2 = settings kaputt/fehlt.
"""
import argparse
import json
import os
import sys

HOOK_NAME = "reap_worktrees.sh"
# managed/-Unterverzeichnis: die hooks-Lane swappt dieses Verzeichnis atomar; ~/.claude/hooks/
# selbst enthält hand-gepflegte Hooks, die nicht weggewischt werden dürfen (ADR-258 Fix).
STABLE_PATH = "~/.claude/hooks/managed/" + HOOK_NAME
SESSIONEND_ENTRY = {
    "matcher": "",
    "hooks": [
        {
            "type": "command",
            "command": os.path.expanduser(STABLE_PATH),
            "timeout": 60,
            "statusMessage": "Gemergte Worktrees reapen…",
        }
    ],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", default=os.path.expanduser("~/.claude/settings.json"))
    ap.add_argument("--print-snippet", action="store_true", help="nur den JSON-Block ausgeben")
    a = ap.parse_args()

    snippet = json.dumps({"hooks": {"SessionEnd": [SESSIONEND_ENTRY]}}, indent=2, ensure_ascii=False)
    if a.print_snippet:
        print(snippet)
        return

    if not os.path.isfile(a.settings):
        print(f"⚠️  Keine settings.json unter {a.settings} — lege eine an mit:\n{snippet}")
        sys.exit(2)
    try:
        cfg = json.load(open(a.settings, encoding="utf-8"))
    except Exception as e:
        print(f"🔴 settings.json nicht parsebar ({e}) — NICHT von Hand kaputt-mergen. Erst JSON reparieren.")
        sys.exit(2)

    existing = [
        h.get("command", "")
        for grp in cfg.get("hooks", {}).get("SessionEnd", [])
        for h in grp.get("hooks", [])
    ]
    # Pfad-PRÄZISE (konsistent zu doctor): nur der exakte managed-Pfad zählt als verdrahtet —
    # ein Verweis auf einen alten/gleichnamigen Pfad NICHT.
    want = os.path.normpath(os.path.expanduser(STABLE_PATH))
    if any(os.path.normpath(os.path.expanduser(c)) == want for c in existing):
        print(f"✅ Bereits verdrahtet: ein SessionEnd-Hook verweist auf {STABLE_PATH}. Nichts zu tun.")
        sys.exit(0)
    stale = [c for c in existing if c and os.path.basename(c) == HOOK_NAME]
    if stale:
        print(f"⚠️  Veralteter Wiring-Pfad gefunden: {stale[0]} — auf {STABLE_PATH} umhängen.")

    has_sessionend = "SessionEnd" in cfg.get("hooks", {})
    print("ℹ️  Aktivierung NÖTIG — der Hook ist verteilt, aber nicht verdrahtet (feuert nie).")
    print(f"   Stabiler Pfad: {STABLE_PATH}")
    print(f"   Datei vorhanden+ausführbar: {os.access(os.path.expanduser(STABLE_PATH), os.X_OK)}")
    print("\n--- So aktivierst du (manuell, bewusst — kein Auto-Schreiben) ---")
    if has_sessionend:
        print("   In hooks.SessionEnd ist bereits eine Gruppe — füge dort diesen hooks-Eintrag hinzu:")
        print(json.dumps(SESSIONEND_ENTRY, indent=2, ensure_ascii=False))
    else:
        print("   Füge unter \"hooks\" diesen Block ein (Komma-Trennung zu bestehenden Events beachten):")
        print(snippet)
    print("\n   Danach prüfen: python3 tools/cc-skill-dist/doctor.py --kind hooks")
    sys.exit(1)


if __name__ == "__main__":
    main()
