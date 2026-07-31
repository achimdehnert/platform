#!/usr/bin/env bash
# Policy-Zonen-Frische — deckt ALLE Dateien unter policies/ ab (ADR-291 offener Punkt 6).
#
# Warum es das gibt: `klickdummy_policy_sync.sh` (ADR-211 C6) prueft genau EINE
# Datei (policies/klickdummy.md). Am 2026-07-31 stand der gepinnte Worktree
# 17 Commits hinter origin/main, mit geaenderter llm-routing.md und
# session-routing.md — klickdummy.md war unveraendert, C6 also GRUEN. Abdeckung
# der Zone: 1 von 12. Dieser Check schliesst die Luecke; C6 bleibt daneben als
# ADR-211-Bestaetigung bestehen.
#
# ORT: die Maschine, nicht CI. `~/.claude/policies` existiert auf einem Runner
# nicht — ein CI-Lauf koennte nur skippen und waere ein Gate, das nie rot wird
# (ADR-291, Abschnitt "Abnahmekriterium").
#
# READ-ONLY: fetcht Refs, checkt nichts aus, repariert nichts. Der Refresh ist
# Sache von ~/.claude/hooks/refresh_pinned_policies.sh.
#
#   0  GRUEN  — Zone deckungsgleich mit dem KANONISCHEN Bezug
#   0  SKIP   — keine Injektions-Umgebung (kein ~/.claude/policies). --strict => 1
#   1  FAIL   — mindestens eine Policy weicht ab, oder der Pin ist stale
#   2  Setupfehler (kein Repo, policies/ fehlt)
#   3  BEZUG NICHT ERHEBBAR — `git fetch` fehlgeschlagen und kein ausdruecklicher
#      Bezug gesetzt. Der Lauf ist UNENTSCHIEDEN, nicht gruen.
#
# Warum 3 existiert (Retro 2026-07-31, Befund #1): Die erste Fassung fiel bei
# Fetch-Fehler still auf den lokalen HEAD zurueck und meldete exit 0/GRUEN — ein
# doppelt staler Zustand (lokaler HEAD alt UND Injektionsziel passend dazu alt)
# war damit von echtem Gruen nicht unterscheidbar. Der HINWEIS-Text half nur
# menschlichen Lesern; jeder automatisierte Konsument sieht nur $?. Regel:
# **Wer seinen Bezug nicht erheben kann, meldet nie 0.**
#
# Env: CLAUDE_POLICIES_DIR  Injektions-Ziel (Default ~/.claude/policies) — ueber-
#      schreibbar, damit die Rot-Faehigkeit an Fixtures beweisbar ist, ohne die
#      Live-Umgebung anzufassen.
#      POLICY_ZONE_REF     ausdruecklicher Bezug statt origin/main. AUSDRUECKLICH
#      heisst: der Aufrufer uebernimmt die Verantwortung fuer die Kanonizitaet —
#      deshalb ist damit exit 0 moeglich, beim STILLEN Fallback dagegen nicht.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INJECT_DIR="${CLAUDE_POLICIES_DIR:-$HOME/.claude/policies}"
SRC_DIR="$REPO_ROOT/policies"
STRICT=0; [[ "${1:-}" == "--strict" ]] && STRICT=1

die() { echo "SETUP: $*" >&2; exit 2; }

[[ -d "$SRC_DIR" ]] || die "SSoT fehlt — $SRC_DIR"
git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1 || die "kein git-Repo — $REPO_ROOT"

# origin/main als kanonischer Bezug.
# POLICY_ZONE_REF ist die Testbarkeits-Naht: ein AUSDRUECKLICH gesetzter Bezug.
# Ein STILLER Fallback auf HEAD ist dagegen kein Bezug, sondern dessen Fehlen.
if [[ -n "${POLICY_ZONE_REF:-}" ]]; then
  REF="$POLICY_ZONE_REF"; REMOTE_OK=1
else
  REMOTE_OK=1
  git -C "$REPO_ROOT" fetch --quiet origin main 2>/dev/null || REMOTE_OK=0
  REF="origin/main"
  if [[ $REMOTE_OK -eq 0 ]]; then
    echo "UNENTSCHIEDEN: 'git fetch origin main' fehlgeschlagen — kanonischer Bezug"
    echo "  nicht erhebbar. Ein Vergleich gegen den lokalen HEAD wuerde einen doppelt"
    echo "  stalen Zustand als GRUEN ausweisen; deshalb wird hier NICHT verglichen."
    echo "  Rueckgabewert 3 (unentschieden, NICHT gruen). Fix: Netz/Remote pruefen,"
    echo "  oder den Bezug ausdruecklich setzen: POLICY_ZONE_REF=<ref> $0"
    exit 3
  fi
fi

# 1) Injektions-Schicht vorhanden?
if [[ ! -e "$INJECT_DIR" ]]; then
  echo "SKIP: $INJECT_DIR existiert nicht — keine Injektions-Umgebung (z. B. CI-Runner)."
  if [[ $STRICT -eq 1 ]]; then echo "  --strict => FAIL"; exit 1; fi
  echo "✓ Policy-Zone (SKIP, exit 0) — off-machine nicht pruefbar."
  exit 0
fi

pinned="$(readlink -f "$INJECT_DIR" 2>/dev/null || echo "$INJECT_DIR")"

# 2) Commit-Ebene: liegt das Ziel in einem git-Worktree, wie weit ist er zurueck?
behind=""
if git -C "$pinned" rev-parse --git-dir >/dev/null 2>&1; then
  pin_head="$(git -C "$pinned" rev-parse --short HEAD 2>/dev/null || echo '?')"
  behind="$(git -C "$REPO_ROOT" rev-list --count "$(git -C "$pinned" rev-parse HEAD)".."$REF" 2>/dev/null || echo '?')"
fi

# 3) Inhalts-Ebene: JEDE Policy einzeln gegen den kanonischen Stand.
#    Subprocess-Substitution statt $(git show) — command substitution strippt
#    Trailing-Newlines und erzeugt false-FAIL (Drift-Lehre 2026-05-20, C6).
abw=(); fehlt=(); extra=()
mapfile -t soll < <(git -C "$REPO_ROOT" ls-tree --name-only "$REF" -- policies/ 2>/dev/null | sed 's|^policies/||' | grep -E '\.md$' | sort)
[[ ${#soll[@]} -gt 0 ]] || die "keine policies/*.md unter $REF gefunden"

for f in "${soll[@]}"; do
  if [[ ! -f "$INJECT_DIR/$f" ]]; then fehlt+=("$f"); continue; fi
  if ! diff -q <(git -C "$REPO_ROOT" show "$REF:policies/$f" 2>/dev/null) "$INJECT_DIR/$f" >/dev/null 2>&1; then
    abw+=("$f")
  fi
done

# Verwaiste Dateien im Ziel, die es unter REF nicht (mehr) gibt
while IFS= read -r f; do
  printf '%s\n' "${soll[@]}" | grep -qxF "$f" || extra+=("$f")
done < <(cd "$INJECT_DIR" && ls -1 ./*.md 2>/dev/null | sed 's|^\./||' | sort)

# 4) Urteil — jede Lage einzeln aufgezaehlt, keine verdeckt eine andere.
echo "Policy-Zone: ${#soll[@]} Dateien unter $REF · Ziel $INJECT_DIR"
[[ -n "$behind" ]] && echo "  gepinnter Worktree: ${pin_head:-?} · $behind Commit(s) hinter $REF"
[[ "$REF" != "origin/main" ]] && echo "  HINWEIS: Bezug ist ausdruecklich gesetzt ($REF), nicht origin/main."

rc=0
if [[ ${#abw[@]} -gt 0 ]]; then
  echo "FAIL: ${#abw[@]} Policy/Policies weichen ab: ${abw[*]}"; rc=1
fi
if [[ ${#fehlt[@]} -gt 0 ]]; then
  echo "FAIL: ${#fehlt[@]} Policy/Policies fehlen im Ziel: ${fehlt[*]}"; rc=1
fi
if [[ ${#extra[@]} -gt 0 ]]; then
  echo "FAIL: ${#extra[@]} verwaiste Datei(en) im Ziel: ${extra[*]}"; rc=1
fi

if [[ $rc -eq 1 ]]; then
  echo "  Fix: bash ~/.claude/hooks/refresh_pinned_policies.sh"
  echo "       (bei DIRTY erst 'git -C $pinned status' klaeren — der Hook ueberspringt dann)"
  exit 1
fi

echo "✓ Policy-Zone GRUEN — alle ${#soll[@]} Dateien deckungsgleich mit $REF."
exit 0
