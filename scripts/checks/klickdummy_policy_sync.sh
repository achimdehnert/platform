#!/usr/bin/env bash
# ADR-211 Confirmation C6 — Klickdummy-Policy SSoT ↔ Injektion (SF6, Issue #240)
#
# Invariante (ADR-211 Rev 5/6, policies/README.md): `platform/policies/
# klickdummy.md` ist die versionierte SSoT. `~/.claude/policies` ist ein
# SYMLINK in den gepinnten platform-Worktree (kein Kopier-Sync). C6 erkennt
# einen STALEN gepinnten Worktree — Policy in der Quelle vorhanden/geändert,
# aber im Injektions-Ziel noch nicht (z. B. Policy gemerged, Pinned-Refresh
# fehlt; oder Policy erst auf PR-Branch, noch nicht gemerged).
#
#   FAIL (exit 1) — SSoT fehlt; ODER Ziel fehlt/weicht ab (stale Pinned).
#   SKIP (exit 0) — kein ~/.claude/policies (keine Session-/Dev-Umgebung,
#                   z. B. sauberer CI-Runner). Mit --strict → FAIL.
#   exit 2 — Setupfehler.  Reine bash.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$REPO_ROOT/policies/klickdummy.md"
INJECT_DIR="${CLAUDE_POLICIES_DIR:-$HOME/.claude/policies}"
TGT="$INJECT_DIR/klickdummy.md"
STRICT=0; [[ "${1:-}" == "--strict" ]] && STRICT=1

# 1) SSoT MUSS im Repo versioniert sein.
if [[ ! -f "$SRC" ]]; then
  echo "FAIL: SSoT fehlt — $SRC (Policy muss im platform-Repo versioniert sein)"
  exit 1
fi

# 2) Injektions-Schicht vorhanden? Sonst keine Session-/Dev-Umgebung.
if [[ ! -e "$INJECT_DIR" ]]; then
  echo "SKIP: $INJECT_DIR existiert nicht — keine Injektions-Umgebung"
  echo "      (sauberer CI-Runner). SSoT ok: $SRC"
  [[ $STRICT -eq 1 ]] && { echo "  --strict ⇒ FAIL"; exit 1; }
  echo "✓ C6 (SKIP, exit 0) — SSoT vorhanden, Injektion off-machine nicht prüfbar."
  exit 0
fi

pinned="$(readlink -f "$INJECT_DIR" 2>/dev/null || echo "$INJECT_DIR")"

# 3) Ziel-Datei im gepinnten Worktree vorhanden?
if [[ ! -f "$TGT" ]]; then
  echo "FAIL: Ziel fehlt — $TGT"
  echo "  Gepinnter Worktree: $pinned"
  echo "  SSoT vorhanden ($SRC), aber im Injektions-Ziel nicht: Policy noch"
  echo "  nicht gemerged ODER Pinned-Refresh ausstehend (ADR-211 C6)."
  exit 1
fi

# 4) Deckungsgleich? Abweichung = staler Pinned-Worktree.
if ! diff -q "$SRC" "$TGT" >/dev/null 2>&1; then
  echo "FAIL: SSoT und Injektions-Ziel weichen ab (staler gepinnter Worktree)"
  echo "  SSoT  : $SRC"
  echo "  Ziel  : $TGT  (→ $pinned)"
  echo "  Fix: gepinnten platform-Worktree refreshen (policies/README.md)."
  exit 1
fi

echo "✓ ADR-211 C6 GRÜN — SSoT == Injektions-Ziel ($pinned), Pinned aktuell."
exit 0
