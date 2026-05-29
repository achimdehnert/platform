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

# Kanonische SSoT = `origin/main:policies/klickdummy.md`. Wir vergleichen den
# Injektions-Ziel-Inhalt gegen den remote main, nicht nur gegen das lokale
# Working-Tree — sonst ist der Check blind, wenn lokales Repo UND pinned
# Worktree am selben staleren Stand sind (Drift-Lehre 2026-05-20: S6 grün
# obwohl origin/main durch #252 vorausgezogen war).
REMOTE_FETCH_OK=0
if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  if git -C "$REPO_ROOT" fetch --quiet origin main 2>/dev/null; then
    REMOTE_FETCH_OK=1
  fi
fi

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

# 4a) Deckungsgleich Working-Tree vs Injektions-Ziel?
if ! diff -q "$SRC" "$TGT" >/dev/null 2>&1; then
  echo "FAIL: SSoT (lokal) und Injektions-Ziel weichen ab (staler gepinnter Worktree)"
  echo "  SSoT  : $SRC"
  echo "  Ziel  : $TGT  (→ $pinned)"
  echo "  Fix: gepinnten platform-Worktree refreshen (policies/README.md)."
  exit 1
fi

# 4b) Kanonisch: TGT vs origin/main (sonst Doppel-Stale-Blind-Spot).
# Direkter Subprocess-Substitution-Vergleich — `$(git show)` würde Trailing-
# Newline strippen (bash command-substitution) und liefert false-FAIL gegen
# eine Datei mit Trailing-Newline (Drift-Lehre 2026-05-20).
if [[ $REMOTE_FETCH_OK -eq 1 ]]; then
  if ! diff -q <(git -C "$REPO_ROOT" show origin/main:policies/klickdummy.md) "$TGT" >/dev/null 2>&1; then
    echo "FAIL: Injektions-Ziel weicht von origin/main ab (lokales Repo UND pinned"
    echo "      Worktree sind beide stale — Doppel-Drift)."
    echo "  origin/main:policies/klickdummy.md"
    echo "  Ziel       : $TGT  (→ $pinned)"
    echo "  Fix: 'git -C $REPO_ROOT pull --ff-only origin main' UND"
    echo "       'git -C \$(dirname $pinned) pull --ff-only origin main'."
    exit 1
  fi
  echo "✓ ADR-211 C6 GRÜN — SSoT == Injektions-Ziel ($pinned) UND == origin/main."
else
  echo "✓ ADR-211 C6 GRÜN (lokal) — SSoT == Injektions-Ziel ($pinned)."
  echo "  HINWEIS: origin/main nicht erreichbar (kein git/Netzwerk) → kein"
  echo "  Doppel-Stale-Check. In strikter CI sicherstellen, dass dieser Check"
  echo "  auf einem Runner mit Netzwerk-Zugang läuft."
fi
exit 0
