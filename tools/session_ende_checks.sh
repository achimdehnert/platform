#!/usr/bin/env bash
# session_ende_checks.sh — deterministischer Runner für die mechanischen
# /session-ende-Phasen (E.0–E.9). Gegenstück zu `session_start_checks.sh`.
#
# Motiv (#2690 K1 + K5): `/session-ende` ist 965 Zeilen lang und trägt den
# mechanischen Bash-Code im Fliesstext — genau die Form, die ein Modell beim
# Ausführen überfliegt (Retro c494a2: eine neue Pflicht-Phase lag in der
# verteilten Skill-Kopie vor und wurde in derselben Sitzung nicht ausgeführt).
# `/session-start` hat diesen Code seit platform#1167 in einem Runner; für das
# Sitzungsende gab es bis hierhin keinen. Ein Runner ist nicht überspringbar:
# EIN Aufruf führt ALLE mechanischen Phasen aus und endet mit einer Tabelle.
#
# Was hier NICHT hineingehört: alles mit Judgment. Die Phasen 0a (blockierte
# Arbeit), 0b (Handover-Text), 0c (Prios), 0d (Abnahme), 0e (Clear-Härte),
# 2 (Memory-Text) und 3.5 (Clear-Freigabe) bleiben im Skill — der Runner nennt
# sie am Ende namentlich, damit ihr Ausbleiben auffällt.
#
# Aufruf:  session_ende_checks.sh [TARGET_REPO] [--session-id <id>]
# Exit 0 = kein FAIL · Exit 1 = mind. 1 FAIL.
#
# Read-only. Der Runner committet nichts, pusht nichts, merged nichts und legt
# keine Issues an; die einzige Schreiboperation ist der Journal-Eintrag am Ende
# (Gedächtnis, kein Eingriff) — analog zum Start-Runner.
#
# Kein `set -e`: einzelne Phasen dürfen scheitern, der Runner läuft immer bis
# zur Summary durch.
set -u

export GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
# Überschreibbar, damit eine Änderung an den Werkzeugen VOR dem Merge prüfbar
# ist (gleiche Begründung wie im Start-Runner).
PLATFORM_DIR="${PLATFORM_DIR:-$GITHUB_DIR/platform}"
LEASE_DIR="${LEASE_DIR:-$HOME/.repo-session/leases}"
PLATTFORM_REPO="platform"

TARGET_REPO=""
SESSION_ID=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-id) SESSION_ID="${2:-}"; shift 2 ;;
    --session-id=*) SESSION_ID="${1#*=}"; shift ;;
    -*) echo "unbekannte Option: $1" >&2; exit 2 ;;
    *) [ -z "$TARGET_REPO" ] && TARGET_REPO="$1"; shift ;;
  esac
done
TARGET_REPO="${TARGET_REPO:-platform}"

HEUTE="$(date +%Y-%m-%d)"
# Zeitbudget der Zusagen-Prüfung (E.5) je PR. 80 s je Segment sind gemessen
# (#2469) — ohne Deckel hält diese eine Phase die ganze Sitzung auf.
ZUSAGEN_BUDGET="${SESSION_ENDE_ZUSAGEN_BUDGET:-120}"
ZUSAGEN_MAX_PRS="${SESSION_ENDE_ZUSAGEN_MAX_PRS:-3}"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

declare -a P_NAME P_STATUS P_NOTE P_REPO
FAILED=0

# record <phase> <PASS|WARN|FAIL|SKIP> <note> [ziel-repo]
#   Pipes raus, sonst bricht die Summary-Tabelle.
#   Das 4. Argument nennt das Repo, um das es in dieser Zeile GEHT — nicht das
#   Repo, in dem die Sitzung läuft (Lehre aus dem Start-Runner: ein wanderndes
#   Etikett zerstört das Alter im Befund-Journal).
record() {
  P_NAME+=("$1"); P_STATUS+=("$2"); P_NOTE+=("$(echo "$3" | tr '|' '/')")
  P_REPO+=("${4:-$PLATTFORM_REPO}")
  [ "$2" = "FAIL" ] && FAILED=1
  printf '  [%s] %s — %s\n' "$2" "$1" "$3"
}

echo "┌─ session-ende Runner · $(date '+%Y-%m-%d %H:%M') · target=$TARGET_REPO ─┐"

# ── E.0 Version-Banner (Skill-Phase −0.1) ───────────────────────────────────
# Bewusst OHNE die `.bashrc`-Schreiberei der Skill-Phase: `GITHUB_DIR` setzt der
# Start-Runner (0.0). Zweimal dieselbe Zeile anhängen ist kein zweiter Schutz.
VERSION_NOW=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT_NOW=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
record "E.0 banner" "PASS" \
  "Platform v${VERSION_NOW} (${COMMIT_NOW})${SESSION_ID:+, session=$SESSION_ID}"

# ── Repos dieser Sitzung ermitteln ──────────────────────────────────────────
# Erste Quelle: die Leases von `repo-session.sh` mit heutigem Datum (das ist die
# Buchführung, die ADR-233 ohnehin führt). Fallback, falls ohne Worktree
# gearbeitet wurde: Repos mit Commits von heute vom aktuellen git-User.
TOUCHED=""
_add_touched() {
  case " $TOUCHED " in *" $1 "*) : ;; *) TOUCHED="$TOUCHED $1" ;; esac
}
TOUCHED_QUELLE="leases"
if [ -d "$LEASE_DIR" ]; then
  for f in "$LEASE_DIR/$HEUTE"-*.json; do
    [ -f "$f" ] || continue
    r=$(grep -o '"repo"[[:space:]]*:[[:space:]]*"[^"]*"' "$f" 2>/dev/null \
        | head -1 | sed -E 's/.*"([^"]*)"$/\1/')
    [ -n "$r" ] && _add_touched "$r"
  done
fi
if [ -z "$TOUCHED" ]; then
  TOUCHED_QUELLE="commits-heute"
  GIT_USER=$(git -C "$PLATFORM_DIR" config user.name 2>/dev/null || echo "")
  for d in "$GITHUB_DIR"/*/; do
    [ -e "${d}.git" ] || continue
    n=$(git -C "$d" log --since="$HEUTE 00:00" ${GIT_USER:+--author="$GIT_USER"} \
        --oneline 2>/dev/null | wc -l)
    [ "${n:-0}" -gt 0 ] && _add_touched "$(basename "$d")"
  done
fi
_add_touched "$TARGET_REPO"
TOUCHED="${TOUCHED# }"

OWNER=$(git -C "$PLATFORM_DIR" remote get-url origin 2>/dev/null \
        | sed -E 's#.*[:/]([^/]+)/[^/]+$#\1#; s#\.git$##')

# ── E.1 Deploy-Status je berührtem Repo (Skill-Phase 0a-deploy) ─────────────
# „main grün" ≠ „Prod aktuell" (Lesson 2026-06-22, trading-hub). Zwei Klassen,
# nicht eine: `failure` UND `waiting` — ein Run, der auf ein Environment-Gate
# wartet, belegt die Concurrency-Group und lässt jeden späteren Deploy als
# `pending` hängen, ohne dass irgendein Check rot wird (Realfall: 9 Tage nicht
# live, der Start-Runner meldete PASS, weil `conclusion` eines waiting-Runs
# null ist).
if [ -z "$OWNER" ]; then
  record "E.1 deploy-status" "SKIP" "Owner nicht ermittelbar (kein origin-Remote in $PLATFORM_DIR)"
elif ! command -v gh >/dev/null 2>&1; then
  record "E.1 deploy-status" "SKIP" "gh nicht verfügbar"
else
  D_OK=""; D_FAIL=""; D_WAIT=""; D_NONE=""; D_SKIP=""
  for r in $TOUCHED; do
    OUT=$(timeout 60 gh run list -R "$OWNER/$r" --workflow Deploy --limit 1 \
          --json conclusion,status,databaseId \
          --jq '"\(.[0].conclusion // "none") \(.[0].status // "none") \(.[0].databaseId // "none")"' \
          2>/dev/null)
    if [ -z "$OUT" ] || [ "$OUT" = "none none none" ]; then
      D_NONE="$D_NONE $r"
      continue
    fi
    read -r C S ID <<EOF
$OUT
EOF
    case "$S" in
      waiting|queued) D_WAIT="$D_WAIT $r($ID)"; continue ;;
    esac
    case "$C" in
      success) D_OK="$D_OK $r" ;;
      failure|timed_out) D_FAIL="$D_FAIL $r($ID)" ;;
      none|"") D_SKIP="$D_SKIP $r" ;;
      *) D_OK="$D_OK $r:$C" ;;
    esac
  done
  D_NOTE="quelle=$TOUCHED_QUELLE; ok:${D_OK:- -}; kein-Deploy:${D_NONE:- -}"
  [ -n "$D_SKIP" ] && D_NOTE="$D_NOTE; unklar:$D_SKIP"
  if [ -n "$D_FAIL" ] || [ -n "$D_WAIT" ]; then
    record "E.1 deploy-status" "WARN" \
      "failure:${D_FAIL:- -} waiting:${D_WAIT:- -} — NICHT als fertig melden (rerun --failed oder als offenes To-do ins Handover); $D_NOTE" \
      "$(echo "$D_FAIL $D_WAIT" | tr -s ' ' | sed -E 's/\([0-9]*\)//g; s/^ //; s/ $//' | tr ' ' ',')"
  else
    record "E.1 deploy-status" "PASS" "$D_NOTE"
  fi
fi

# ── E.2 Offene AGENT_HANDOVER.md-PRs (Skill-Phase 0a-handover-pr) ───────────
# Lehre c494a2/2026-07-14: eine Sitzung ließ ihren Handover-PR offen, die
# nächste schrieb einen zweiten — drei konkurrierende Stände. Der Suchlauf
# selbst ist reine Mechanik; die Entscheidung (übernehmen vs. schließen)
# bleibt im Skill.
if ! command -v gh >/dev/null 2>&1 || [ -z "$OWNER" ]; then
  record "E.2 handover-prs" "SKIP" "gh oder Owner nicht verfügbar" "$TARGET_REPO"
else
  HPR=$(timeout 60 gh pr list --repo "$OWNER/$TARGET_REPO" \
        --search "AGENT_HANDOVER.md in:body" --state open \
        --json number,updatedAt --jq '.[] | "#\(.number)@\(.updatedAt[0:10])"' 2>/dev/null)
  if [ -z "$HPR" ]; then
    HPR=$(timeout 90 gh pr list --repo "$OWNER/$TARGET_REPO" --state open \
          --json number,files \
          --jq '.[] | select(.files[]?.path == "AGENT_HANDOVER.md") | "#\(.number)"' 2>/dev/null)
  fi
  HPR_N=$(printf '%s' "$HPR" | grep -c . || true)
  if [ "${HPR_N:-0}" -gt 1 ]; then
    record "E.2 handover-prs" "WARN" \
      "$HPR_N offene Handover-PRs ($(echo "$HPR" | tr '\n' ' ')) — konkurrierende Stände, vor 0b auflösen" \
      "$TARGET_REPO"
  else
    record "E.2 handover-prs" "PASS" \
      "${HPR_N:-0} offene(r) Handover-PR ($(echo "${HPR:--}" | tr '\n' ' '))" "$TARGET_REPO"
  fi
fi

# ── E.3 Handover-Frische (Skill-Phase 0a-freshness, Gate handover-stale-vor-merge) ──
HO_CHECK="$PLATFORM_DIR/scripts/checks/agent_handover_freshness_check.py"
HO_FILE="$GITHUB_DIR/$TARGET_REPO/AGENT_HANDOVER.md"
if [ ! -f "$HO_CHECK" ]; then
  record "E.3 handover-frische" "SKIP" "Werkzeug fehlt: scripts/checks/agent_handover_freshness_check.py" "$TARGET_REPO"
elif [ ! -f "$HO_FILE" ]; then
  record "E.3 handover-frische" "SKIP" "keine AGENT_HANDOVER.md in $TARGET_REPO" "$TARGET_REPO"
else
  HO_OUT=$(timeout 60 python3 "$HO_CHECK" "$HO_FILE" 2>&1)
  HO_RC=$?
  if [ "$HO_RC" -eq 0 ]; then
    record "E.3 handover-frische" "PASS" "$(printf '%s' "$HO_OUT" | head -1 | cut -c1-120)" "$TARGET_REPO"
  elif [ "$HO_RC" -eq 1 ]; then
    record "E.3 handover-frische" "WARN" \
      "$(printf '%s' "$HO_OUT" | grep -m1 FAIL | cut -c1-140) — Stand vor dem Merge nachziehen" "$TARGET_REPO"
  else
    record "E.3 handover-frische" "SKIP" "Prüfer brach ab (rc=$HO_RC)" "$TARGET_REPO"
  fi
fi

# ── E.4 Offene Cross-Repo-Befunde (Skill-Phase 0f) ──────────────────────────
# Nur die Zahl. Die Deutung — verankern oder begründet verzichten — bleibt im
# Skill (0f), samt Scope-Checkpoint.
BJ="$PLATFORM_DIR/tools/befund_journal.py"
if [ ! -f "$BJ" ]; then
  record "E.4 cross-repo-befunde" "SKIP" "Werkzeug fehlt: tools/befund_journal.py"
else
  # Das Werkzeug meldet seine Klasse selbst als `RESULT:`-Zeile — die wird
  # gelesen, nicht der Exit-Code allein: `--offen-cross-repo` beendet mit 1,
  # wenn etwas offen ist, aber auch `UNGEPRUEFT` (kein Journal) ist kein PASS.
  BJ_OUT=$(timeout 90 python3 "$BJ" --offen-cross-repo 2>/dev/null)
  BJ_RES=$(printf '%s' "$BJ_OUT" | grep -m1 '^RESULT:' || true)
  case "$BJ_RES" in
    *"RESULT: OFFEN"*)
      BJ_N=$(printf '%s' "$BJ_RES" | grep -o '[0-9]\+' | head -1)
      record "E.4 cross-repo-befunde" "WARN" \
        "${BJ_N:-?} offene(r) Fremd-Repo-Befund(e) ohne Artefakt/Verzicht — Deutung in Skill-Phase 0f" ;;
    *"RESULT: OK"*)
      record "E.4 cross-repo-befunde" "PASS" "keine offenen Fremd-Repo-Befunde" ;;
    *)
      record "E.4 cross-repo-befunde" "SKIP" \
        "befund_journal.py --offen-cross-repo ohne verwertbare RESULT-Zeile (${BJ_RES:-keine Ausgabe})" ;;
  esac
fi

# ── E.5 Zusagen dieser Sitzung (Skill-Phase 0g) ─────────────────────────────
# Vier Ausgabeklassen, und drei davon sind kein Grün: `⚠️` (Zusage ohne
# Tracking), `◌ NICHT PRUEFBAR` (kein Modell erreichbar) und `◌ … UNGEPRUEFT`
# (Zeitbudget erschöpft). Der Runner reicht sie durch, er deutet sie nicht.
VP="$PLATFORM_DIR/tools/verankerung_pruefer.py"
if [ ! -f "$VP" ]; then
  record "E.5 zusagen" "SKIP" "Werkzeug fehlt: tools/verankerung_pruefer.py" "$TARGET_REPO"
elif ! command -v gh >/dev/null 2>&1 || [ -z "$OWNER" ]; then
  record "E.5 zusagen" "SKIP" "gh oder Owner nicht verfügbar" "$TARGET_REPO"
elif ! curl -sf -m 5 "$OLLAMA_HOST/api/tags" >/dev/null 2>&1; then
  record "E.5 zusagen" "SKIP" "◌ NICHT PRUEFBAR — kein Klassifikator unter $OLLAMA_HOST" "$TARGET_REPO"
else
  PRS=$(timeout 60 gh pr list --repo "$OWNER/$TARGET_REPO" --author @me --state all \
        --search "created:>=$HEUTE" --json number --jq '.[].number' 2>/dev/null | head -n "$ZUSAGEN_MAX_PRS")
  if [ -z "$PRS" ]; then
    record "E.5 zusagen" "PASS" "keine eigenen PRs von heute in $OWNER/$TARGET_REPO" "$TARGET_REPO"
  else
    Z_OK=""; Z_WARN=""; Z_UNKLAR=""
    for nr in $PRS; do
      Z_OUT=$(timeout "$((ZUSAGEN_BUDGET + 60))" python3 "$VP" --pr "$nr" \
              --repo "$OWNER/$TARGET_REPO" --budget-sekunden "$ZUSAGEN_BUDGET" 2>&1)
      case "$Z_OUT" in
        *"NICHT PRUEFBAR"*) Z_UNKLAR="$Z_UNKLAR #$nr:nicht-pruefbar" ;;
        *UNGEPRUEFT*)       Z_UNKLAR="$Z_UNKLAR #$nr:ungeprueft" ;;
        *"⚠️"*|*"❌"*)      Z_WARN="$Z_WARN #$nr" ;;
        *"✅"*)             Z_OK="$Z_OK #$nr" ;;
        *)                  Z_UNKLAR="$Z_UNKLAR #$nr:ohne-klasse" ;;
      esac
    done
    if [ -n "$Z_WARN" ]; then
      record "E.5 zusagen" "WARN" \
        "Zusage ohne Tracking in:$Z_WARN — Issue anlegen ODER Fehlalarm in der Kalibrier-Datei notieren (advisory, Präzision 0,50)" \
        "$TARGET_REPO"
    elif [ -n "$Z_UNKLAR" ]; then
      record "E.5 zusagen" "SKIP" "◌$Z_UNKLAR — keine Entwarnung; ok:${Z_OK:- -}" "$TARGET_REPO"
    else
      record "E.5 zusagen" "PASS" "✅ jede erkannte Zusage verankert:$Z_OK" "$TARGET_REPO"
    fi
  fi
fi

# ── E.6 Template-Drift (Skill-Phase 1c) ─────────────────────────────────────
DC="$PLATFORM_DIR/scripts/drift_check.py"
if [ ! -f "$DC" ]; then
  record "E.6 template-drift" "SKIP" "Werkzeug fehlt: scripts/drift_check.py"
else
  # Gemessen 2026-09-02: 411 s fuer die ganze Flotte (mit --skip-pypi). Der
  # erste Deckel stand bei 180 s und machte aus einer Phase, die 19 Errors
  # findet, ein SKIP — ein Timeout, der immer feuert, ist kein Schutz, sondern
  # eine abgeschaltete Pruefung.
  DC_OUT=$(timeout "${SESSION_ENDE_DRIFT_TIMEOUT:-480}" python3 "$DC" \
           --severity=error --skip-pypi --fail-on-error 2>&1)
  DC_RC=$?
  case "$DC_RC" in
    0) record "E.6 template-drift" "PASS" "keine Error-Drifts" ;;
    1) DC_ZEILE=$(printf '%s' "$DC_OUT" | grep -m1 -E '^Exit 1:' \
                  || printf '%s' "$DC_OUT" | grep -iE 'error|drift' | tail -1)
       record "E.6 template-drift" "WARN" "$(printf '%s' "$DC_ZEILE" | cut -c1-140)" ;;
    124) record "E.6 template-drift" "SKIP" \
           "drift_check.py in ${SESSION_ENDE_DRIFT_TIMEOUT:-480}s nicht fertig (SESSION_ENDE_DRIFT_TIMEOUT erhoehen)" ;;
    *) record "E.6 template-drift" "SKIP" "drift_check.py brach ab (rc=$DC_RC)" ;;
  esac
fi

# ── E.7 Dirty-Repos (Skill-Phase 3.3) ───────────────────────────────────────
# Eigene vs. fremde Repos getrennt: ein dirty Repo, an dem diese Sitzung nie
# gearbeitet hat, ist nicht ihr Befund — sonst meldet jede Sitzung dieselbe
# fremde Baustelle und der Melder wird taub gelesen.
DIRTY_EIGEN=""; DIRTY_FREMD=""
for d in "$GITHUB_DIR"/*/; do
  [ -e "${d}.git" ] || continue
  n=$(basename "$d")
  [ -n "$(git -C "$d" status --porcelain 2>/dev/null)" ] || continue
  case " $TOUCHED " in
    *" $n "*) DIRTY_EIGEN="$DIRTY_EIGEN $n" ;;
    *)        DIRTY_FREMD="$DIRTY_FREMD $n" ;;
  esac
done
if [ -n "$DIRTY_EIGEN" ]; then
  record "E.7 dirty-repos" "WARN" \
    "eigene dirty:$DIRTY_EIGEN — committen/pushen oder User fragen; fremd (nur Hinweis):${DIRTY_FREMD:- -}" \
    "$(echo "$DIRTY_EIGEN" | sed -E 's/^ //' | tr ' ' ',')"
else
  record "E.7 dirty-repos" "PASS" "keine eigenen dirty Repos; fremd (nur Hinweis):${DIRTY_FREMD:- -}"
fi

# ── E.8 Worktree-Reaper (Skill-Phase 3.1c) — bewusst NICHT ausgeführt ───────
# Das Gate `worktree-midsession-accumulation` wurde am 2026-08-20 umgebaut:
# `repo-session.sh reap --alle` läuft seither in `session_start_checks.sh`
# Phase 0.4.5 über ALLE Repos mit Lease. Ein zweiter Lauf am Sitzungsende ist
# dieselbe Mechanik ein zweites Mal — der nächste Start räumt ohnehin.
record "E.8 worktree-reap" "SKIP" \
  "bewusst nicht ausgeführt — Phase 0.4.5 des nächsten session-start räumt über alle Leases (Gate worktree-midsession-accumulation, Revision 2026-08-20)"

# ── E.9 Skill-Verteilungs-Drift (dist-drift) ────────────────────────────────
# Gleicher Aufruf wie Start-Phase 0.7.13, aber OHNE Selbstheilung: am
# Sitzungsende soll nichts mehr am ausgelieferten Stand verändert werden.
DOC="$PLATFORM_DIR/tools/cc-skill-dist/doctor.py"
if [ ! -f "$DOC" ]; then
  record "E.9 dist-drift" "SKIP" "Werkzeug fehlt: tools/cc-skill-dist/doctor.py"
else
  DD_NOTE=""; DD_STATUS="PASS"
  for LANE in skills commands hooks; do
    LANE_OUT=$(timeout 120 python3 "$DOC" --kind "$LANE" 2>/dev/null || true)
    LANE_SCORE=$(printf '%s' "$LANE_OUT" | grep -o 'DRIFT-SCORE: [0-9]*' | head -1 | grep -o '[0-9]*')
    if [ -z "$LANE_SCORE" ]; then
      DD_STATUS="WARN"; DD_NOTE="${DD_NOTE}${LANE}:UNGEPRUEFT "
    elif [ "$LANE_SCORE" -gt 0 ]; then
      DD_STATUS="WARN"; DD_NOTE="${DD_NOTE}${LANE}:${LANE_SCORE} "
    else
      DD_NOTE="${DD_NOTE}${LANE}:0 "
    fi
  done
  if [ "$DD_STATUS" = "WARN" ]; then
    record "E.9 dist-drift" "WARN" \
      "${DD_NOTE% } — verteilte Skills weichen von .windsurf/workflows/ ab (Heilung: session-start 0.7.13)"
  else
    record "E.9 dist-drift" "PASS" "alle Lanes synchron (${DD_NOTE% })"
  fi
fi

# ── Summary (maschinenlesbar, gleiche Form wie der Start-Runner) ────────────
echo ""
echo "| Phase | Status | Repo | Note |"
echo "|---|---|---|---|"
for i in "${!P_NAME[@]}"; do
  case "${P_STATUS[$i]}" in
    PASS) ICON="✅" ;;
    WARN) ICON="⚠️" ;;
    FAIL) ICON="❌" ;;
    # SKIP ist KEIN Grün. Die Phase konnte nicht prüfen — das ist weder ein
    # Befund noch eine Entwarnung. „NICHT messbar" als PASS zu verbuchen war
    # die teuerste Fehlklasse des Start-Runners (KONZ-platform-050).
    SKIP) ICON="◌" ;;
    *) ICON="?" ;;
  esac
  printf '| %s | %s %s | %s | %s |\n' \
    "${P_NAME[$i]}" "$ICON" "${P_STATUS[$i]}" "${P_REPO[$i]:-$TARGET_REPO}" "${P_NOTE[$i]}"
done
echo ""

if [ "$FAILED" -eq 1 ]; then
  echo "RESULT: FAIL — Sitzung NICHT abschließen, bis alle ❌ behoben sind."
  echo "JUDGMENT: 0a 0b 0c 0d 0e 2 3.5 — im Skill abarbeiten"
  exit 1
fi
SKIP_N=0
for s in "${P_STATUS[@]}"; do [ "$s" = "SKIP" ] && SKIP_N=$((SKIP_N+1)); done
if [ "$SKIP_N" -gt 0 ]; then
  echo "HINWEIS: $SKIP_N Phase(n) konnten nicht prüfen (◌ SKIP) — kein Befund, aber auch keine Entwarnung."
fi
echo "RESULT: OK — mechanische Phasen komplett."
echo "JUDGMENT: 0a 0b 0c 0d 0e 2 3.5 — im Skill abarbeiten"
