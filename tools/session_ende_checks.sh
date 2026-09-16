#!/usr/bin/env bash
# session_ende_checks.sh — deterministischer Runner für die mechanischen
# /session-ende-Phasen (E.0–E.10). Gegenstück zu `session_start_checks.sh`.
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
# keine Issues an; Schreiboperationen sind der Journal-Eintrag am Ende
# (Gedächtnis, kein Eingriff) und — seit 2026-09-14 — `git worktree prune` in E.8:
# er entfernt nur Verwaltungseinträge, deren Verzeichnis schon fehlt (Git selbst
# etikettiert sie `prunable`), nie einen Baum mit Inhalt.
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

# Normalisierung (#2773): der Skill ruft den Runner mit einem PFAD auf
# (`session_ende_checks.sh /home/devuser/github/platform`). Ohne diesen Schritt
# landete der Pfad selbst als Repo-NAME in `$OWNER/$TARGET_REPO` (E.2/E.5) und
# als Pfadsegment in `$GITHUB_DIR/$TARGET_REPO/...` (E.3) — beides falsch.
# Ab hier: `$TARGET_DIR` fuer Pfade, `$TARGET_REPO` nur noch als Name.
case "$TARGET_REPO" in
  */*)
    if [ ! -d "$TARGET_REPO" ]; then
      echo "Pfad nicht gefunden: $TARGET_REPO" >&2
      exit 2
    fi
    TARGET_DIR="$(cd "$TARGET_REPO" && pwd -P)"
    TARGET_REPO="$(basename "$TARGET_DIR")"
    # Session-Worktree (ADR-233): der Ordnername ist ein Zeitstempel-Slug, das
    # Repo heisst wie der Haupt-Tree, dem das gemeinsame .git gehoert.
    COMMON_GIT="$(git -C "$TARGET_DIR" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
    case "$COMMON_GIT" in
      */.git) TARGET_REPO="$(basename "$(dirname "$COMMON_GIT")")" ;;
    esac
    ;;
  *)
    TARGET_DIR="$GITHUB_DIR/$TARGET_REPO"
    ;;
esac

# Fehlerausgaben von `gh` nicht mehr per `2>/dev/null` verschlucken (#2794):
# ein rate-limitiertes/fehlerhaftes `gh` lieferte bisher eine leere Liste, die
# wie „keine offenen PRs" aussah (PASS statt SKIP).
TMP_ERR="$(mktemp)"
trap 'rm -f "$TMP_ERR"' EXIT

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

echo "┌─ session-ende Runner · $(date '+%Y-%m-%d %H:%M') · target=$TARGET_REPO ($TARGET_DIR) ─┐"

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
  # Der Fallback steht und faellt mit dem Autorenfilter. Ohne ihn heisst
  # `--since=heute` nur „irgendwer hat heute committet" — dann erklaert der
  # Runner fremde Arbeit zur eigenen, und E.7 meldet eine fremde Baustelle als
  # Befund dieser Sitzung. Gemessen in CI (Lauf 33644319863): dort ist
  # `git config user.name` leer, der Filter fiel ersatzlos weg, und ein
  # Fixture-Repo ohne Lease stand als „eigen dirty" in der Tabelle.
  # Kein Name ermittelbar ⇒ kein Fallback, und die Note sagt das auch.
  # `-` statt `:-`: ein ausdruecklich LEER gesetztes SESSION_ENDE_GIT_USER soll
  # den Fallback abschalten, nicht in die git-config zurueckfallen.
  GIT_USER="${SESSION_ENDE_GIT_USER-$(git -C "$PLATFORM_DIR" config user.name 2>/dev/null || echo "")}"
  if [ -z "$GIT_USER" ]; then
    TOUCHED_QUELLE="unbestimmt(kein git user.name)"
  else
    TOUCHED_QUELLE="commits-heute"
    for d in "$GITHUB_DIR"/*/; do
      [ -e "${d}.git" ] || continue
      n=$(git -C "$d" log --since="$HEUTE 00:00" --author="$GIT_USER" \
          --oneline 2>/dev/null | wc -l)
      [ "${n:-0}" -gt 0 ] && _add_touched "$(basename "$d")"
    done
  fi
fi
_add_touched "$TARGET_REPO"
TOUCHED="${TOUCHED# }"

# Owner je ZIEL-Repo, nicht per Platform-Remote geraten (#2794): bei
# `iilgmbh/iil-voice-agent` prüfte E.5 sonst unter `achimdehnert/...` und
# meldete PASS, weil die falsche Repo-URL leer zurückkam.
OWNER=$(git -C "$TARGET_DIR" remote get-url origin 2>/dev/null \
        | sed -E 's#.*[:/]([^/]+)/[^/]+$#\1#; s#\.git$##')
if [ -z "$OWNER" ]; then
  # Fallback nur ohne Remote im Ziel-Repo: bisheriges Verhalten (Platform-Remote).
  OWNER=$(git -C "$PLATFORM_DIR" remote get-url origin 2>/dev/null \
          | sed -E 's#.*[:/]([^/]+)/[^/]+$#\1#; s#\.git$##')
  [ -n "$OWNER" ] && echo "hinweis: Owner geraten aus $PLATFORM_DIR (kein origin-Remote in $TARGET_DIR)" >&2
fi

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

# E.3 braucht das Ergebnis von E.2: leer = nicht beurteilbar, sonst Anzahl.
HO_PR_ANZAHL=""

# ── E.2 Offene AGENT_HANDOVER.md-PRs (Skill-Phase 0a-handover-pr) ───────────
# Lehre c494a2/2026-07-14: eine Sitzung ließ ihren Handover-PR offen, die
# nächste schrieb einen zweiten — drei konkurrierende Stände. Der Suchlauf
# selbst ist reine Mechanik; die Entscheidung (übernehmen vs. schließen)
# bleibt im Skill.
if ! command -v gh >/dev/null 2>&1 || [ -z "$OWNER" ]; then
  record "E.2 handover-prs" "SKIP" "gh oder Owner nicht verfügbar" "$TARGET_REPO"
else
  E2_DONE=0
  HPR=$(timeout 60 gh pr list --repo "$OWNER/$TARGET_REPO" \
        --search "AGENT_HANDOVER.md in:body" --state open \
        --json number,updatedAt --jq '.[] | "#\(.number)@\(.updatedAt[0:10])"' 2>"$TMP_ERR")
  RC=$?
  if [ "$RC" -ne 0 ]; then
    record "E.2 handover-prs" "SKIP" \
      "gh scheiterte (rc=$RC): $(head -c 120 "$TMP_ERR")" "$TARGET_REPO"
    E2_DONE=1
  fi
  # Fallback, wenn die Body-Suche leer ist (keine gh-relevante Aenderung —
  # ebenfalls rc-geprueft, statt der zweite blinde Fleck zu werden).
  if [ "$E2_DONE" -eq 0 ] && [ -z "$HPR" ]; then
    HPR=$(timeout 90 gh pr list --repo "$OWNER/$TARGET_REPO" --state open \
          --json number,files \
          --jq '.[] | select(.files[]?.path == "AGENT_HANDOVER.md") | "#\(.number)"' 2>"$TMP_ERR")
    RC=$?
    if [ "$RC" -ne 0 ]; then
      record "E.2 handover-prs" "SKIP" \
        "gh scheiterte (rc=$RC): $(head -c 120 "$TMP_ERR")" "$TARGET_REPO"
      E2_DONE=1
    fi
  fi
  if [ "$E2_DONE" -eq 0 ]; then
    HPR_N=$(printf '%s' "$HPR" | grep -c . || true)
    HO_PR_ANZAHL="${HPR_N:-0}"
    if [ "${HPR_N:-0}" -gt 1 ]; then
      record "E.2 handover-prs" "WARN" \
        "$HPR_N offene Handover-PRs ($(echo "$HPR" | tr '\n' ' ')) — konkurrierende Stände, vor 0b auflösen" \
        "$TARGET_REPO"
    else
      record "E.2 handover-prs" "PASS" \
        "${HPR_N:-0} offene(r) Handover-PR ($(echo "${HPR:--}" | tr '\n' ' '))" "$TARGET_REPO"
    fi
  fi
fi

# ── E.3 Handover-Frische (Skill-Phase 0a-freshness, Gate handover-stale-vor-merge) ──
HO_CHECK="$PLATFORM_DIR/scripts/checks/agent_handover_freshness_check.py"
HO_FILE="$TARGET_DIR/AGENT_HANDOVER.md"
FRAG_DIR_REL="docs/handover.d"
if [ -d "$TARGET_DIR/$FRAG_DIR_REL" ]; then
  # Fragment-Modus (#1944 K6, KONZ-027): die Sitzung schreibt ihr EIGENES Fragment,
  # die geteilte Datei bleibt unberuehrt. Frisch ist die Sitzung, wenn ihr Fragment
  # auf main liegt oder in einem offenen PR steckt — Commits anderer Sitzungen
  # zaehlen nicht mehr.
  if [ -z "$SESSION_ID" ]; then
    record "E.3 handover-frische" "WARN" \
      "Fragment-Modus: ohne --session-id nicht pruefbar — Runner mit --session-id aufrufen" "$TARGET_REPO"
  else
    # [.] statt \. — jq (gh --jq) kennt die Escape-Sequenz \. nicht.
    # Am Zeitstempel verankert: sonst gaelte "auf-main" als Fragment der Sitzung "main".
    FRAG_RE="Z-${SESSION_ID}(-[0-9]+)?[.]md\$"
    FRAG_MAIN=$(git -C "$TARGET_DIR" ls-tree --name-only "origin/main:$FRAG_DIR_REL" 2>/dev/null \
      | grep -E -- "$FRAG_RE" | head -1)
    FRAG_PR=""
    if [ -z "$FRAG_MAIN" ] && command -v gh >/dev/null 2>&1 && [ -n "$OWNER" ]; then
      FRAG_PR=$(timeout 90 gh pr list --repo "$OWNER/$TARGET_REPO" --state open \
        --json number,files \
        --jq ".[] | select(any(.files[]?; .path | test(\"^docs/handover[.]d/.*$FRAG_RE\"))) | \"#\\(.number)\"" \
        2>/dev/null | head -3 | tr '\n' ' ')
    fi
    if [ -n "$FRAG_MAIN" ]; then
      record "E.3 handover-frische" "PASS" "Fragment der Sitzung liegt auf main: $FRAG_MAIN" "$TARGET_REPO"
    elif [ -n "$FRAG_PR" ]; then
      record "E.3 handover-frische" "PASS" "Fragment der Sitzung offen als PR ${FRAG_PR% }" "$TARGET_REPO"
    else
      record "E.3 handover-frische" "FAIL" \
        "kein Fragment fuer Sitzung $SESSION_ID auf main oder in offenem PR — fragments.py neu --session-id $SESSION_ID" "$TARGET_REPO"
    fi
  fi
elif [ ! -f "$HO_CHECK" ]; then
  record "E.3 handover-frische" "SKIP" "Werkzeug fehlt: scripts/checks/agent_handover_freshness_check.py" "$TARGET_REPO"
elif [ ! -f "$HO_FILE" ]; then
  record "E.3 handover-frische" "SKIP" "keine AGENT_HANDOVER.md in $TARGET_REPO" "$TARGET_REPO"
else
  # Umbau 2026-09-14 (Retro oqu6Z6 §5a / Befund #22, Gate handover-stale-vor-merge
  # Rev 3): die Frage gehoert an das Sitzungsende, nicht an einen Handover-PR, der
  # fehlen kann. Realfall: am Ende beruehrte KEIN PR die Datei — der letzte Nachtrag
  # stammte von der Parallelsitzung des Vortags, danach landeten 10 Commits. Der
  # Aufruf ohne Schwelle sah das nie (Rezenz-Check allein, Datum = letzter Commit).
  # Jetzt: jeder Sitzungs-Commit seit der letzten Beruehrung auf der Basis zaehlt,
  # und ohne offenen Handover-PR (E.2) ist das ein FAIL — der Nachtrag ist der
  # letzte Schritt vor dem Sitzungsende. Aufruf im Ziel-Repo, sonst liefe `git log`
  # im falschen Arbeitsbaum und degradierte still zu PASS.
  HO_BASIS="HEAD"
  git -C "$TARGET_DIR" rev-parse --verify -q origin/main >/dev/null 2>&1 && HO_BASIS="origin/main"
  HO_SCHWELLE="${SESSION_ENDE_HANDOVER_SCHWELLE:-0}"
  HO_OUT=$(cd "$TARGET_DIR" && timeout 60 python3 "$HO_CHECK" \
    --commits-schwelle "$HO_SCHWELLE" --basis "$HO_BASIS" --beruehrung-auf-basis \
    "$HO_FILE" 2>&1)
  HO_RC=$?
  HO_COMMITS=$(printf '%s' "$HO_OUT" | grep -o 'sind [0-9]* Commits' | grep -o '[0-9]*' | head -1)
  if [ "$HO_RC" -eq 0 ]; then
    record "E.3 handover-frische" "PASS" "$(printf '%s' "$HO_OUT" | head -1 | cut -c1-120)" "$TARGET_REPO"
  elif [ "$HO_RC" -eq 1 ] && [ -n "$HO_COMMITS" ]; then
    if [ -z "$HO_PR_ANZAHL" ]; then
      record "E.3 handover-frische" "WARN" \
        "$HO_COMMITS Commits seit dem letzten Nachtrag ($HO_BASIS); ob ein Handover-PR offen ist, bleibt offen (E.2 nicht beurteilbar)" "$TARGET_REPO"
    elif [ "$HO_PR_ANZAHL" -gt 0 ]; then
      record "E.3 handover-frische" "PASS" \
        "$HO_COMMITS Commits seit dem letzten Nachtrag, Nachtrag offen als PR (E.2: $HO_PR_ANZAHL)" "$TARGET_REPO"
    else
      record "E.3 handover-frische" "FAIL" \
        "$HO_COMMITS Commits seit dem letzten Nachtrag ($HO_BASIS), kein offener Handover-PR — Stand nachziehen, bevor die Sitzung endet" "$TARGET_REPO"
    fi
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
# Provider (2026-09-14): Groq, wenn der Schluessel lesbar ist — PR-Texte dieses
# Repos sind oeffentlich, Groq ist fuer Klassifikation freigegeben. Das lokale
# qwen2.5:7b auf dev-desktop brauchte fuer EIN Segment laenger als das 80-s-Budget
# (gemessen an #3179: "Zeitueberschreitung nach 80 s"), Groq 3 s fuer 6 Segmente.
# Ohne Schluessel bleibt der bisherige Ollama-Weg.
ZUSAGEN_PROVIDER="ollama"
ZUSAGEN_GROQ_KEY="$("$PLATFORM_DIR/tools/secret_lesen.sh" groq_api_key 2>/dev/null || true)"
if [ -n "$ZUSAGEN_GROQ_KEY" ]; then
  ZUSAGEN_PROVIDER="groq"
fi
if [ ! -f "$VP" ]; then
  record "E.5 zusagen" "SKIP" "Werkzeug fehlt: tools/verankerung_pruefer.py" "$TARGET_REPO"
elif ! command -v gh >/dev/null 2>&1 || [ -z "$OWNER" ]; then
  record "E.5 zusagen" "SKIP" "gh oder Owner nicht verfügbar" "$TARGET_REPO"
elif [ "$ZUSAGEN_PROVIDER" = "ollama" ] && ! curl -sf -m 5 "$OLLAMA_HOST/api/tags" >/dev/null 2>&1; then
  record "E.5 zusagen" "SKIP" "◌ NICHT PRUEFBAR — kein Klassifikator unter $OLLAMA_HOST" "$TARGET_REPO"
else
  PRS=$(timeout 60 gh pr list --repo "$OWNER/$TARGET_REPO" --author @me --state all \
        --search "created:>=$HEUTE" --json number --jq '.[].number' 2>"$TMP_ERR")
  RC=$?
  PRS=$(printf '%s' "$PRS" | head -n "$ZUSAGEN_MAX_PRS")
  if [ "$RC" -ne 0 ]; then
    record "E.5 zusagen" "SKIP" \
      "◌ gh scheiterte (rc=$RC): $(head -c 120 "$TMP_ERR")" "$TARGET_REPO"
  elif [ -z "$PRS" ]; then
    record "E.5 zusagen" "PASS" "keine eigenen PRs von heute in $OWNER/$TARGET_REPO" "$TARGET_REPO"
  else
    Z_OK=""; Z_WARN=""; Z_UNKLAR=""
    for nr in $PRS; do
      Z_OUT=$(GROQ_API_KEY="$ZUSAGEN_GROQ_KEY" timeout "$((ZUSAGEN_BUDGET + 60))" \
              python3 "$VP" --pr "$nr" --repo "$OWNER/$TARGET_REPO" \
              --budget-sekunden "$ZUSAGEN_BUDGET" --provider "$ZUSAGEN_PROVIDER" 2>&1)
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
    2) record "E.6 template-drift" "SKIP" \
         "kein Repo erreichbar — Werkzeugfehler, KEIN drift-freier Stand (meist GitHub-Drosselung; echte Probe: gh api repos/<owner>/<einRepo>)" ;;
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

# ── E.8 Worktree-Hygiene: prune + Altersgrenze (Skill-Phase 3.1c) ───────────
# Umbau 2026-09-14 (Retro oqu6Z6 §5a / Befund #21, Gate
# worktree-midsession-accumulation): bis hierhin stand E.8 auf SKIP mit Verweis auf
# den naechsten Sitzungsstart. Der raeumt gemergte Baeume — aber `git worktree list`
# zeigte 13 Baeume, zwei davon mit dem Git-eigenen Etikett `prunable`, einige
# Wochen alt, und gehandelt hat niemand. Eine Anzeige ist keine Schranke. Jetzt:
# (1) `git worktree prune` wird AUSGEFUEHRT (nur Eintraege ohne Verzeichnis);
# (2) jeder verknuepfte Baum, dessen letzter Commit UND dessen Anlage (HEAD-Datei
# im Verwaltungsverzeichnis) aelter als die Altersgrenze sind, ist ein FAIL —
# entfernen oder mit Grund behalten: `echo "<Grund>" > "$(git -C <baum>
# rev-parse --absolute-git-dir)/behalten"` (liegt ausserhalb des Baums, kann
# nicht versehentlich committet werden).
WT_MAX_TAGE="${SESSION_ENDE_WORKTREE_MAX_TAGE:-14}"
if ! git -C "$TARGET_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  record "E.8 worktree-hygiene" "SKIP" "kein git-Repo: $TARGET_DIR" "$TARGET_REPO"
else
  WT_PRUNABLE=$(git -C "$TARGET_DIR" worktree list --porcelain 2>/dev/null | grep -c '^prunable' || true)
  git -C "$TARGET_DIR" worktree prune 2>"$TMP_ERR"
  WT_PRUNE_RC=$?
  WT_JETZT=$(date +%s)
  WT_GRENZE=$((WT_JETZT - WT_MAX_TAGE * 86400))
  WT_ALT=""; WT_BEHALTEN=0; WT_N=0
  while IFS= read -r WT_PFAD; do
    [ -d "$WT_PFAD" ] || continue
    WT_N=$((WT_N + 1))
    WT_GITDIR=$(git -C "$WT_PFAD" rev-parse --absolute-git-dir 2>/dev/null) || continue
    if [ -s "$WT_GITDIR/behalten" ]; then
      WT_BEHALTEN=$((WT_BEHALTEN + 1)); continue
    fi
    WT_T_COMMIT=$(git -C "$WT_PFAD" log -1 --format=%ct 2>/dev/null || echo 0)
    WT_T_ANLAGE=$(stat -c %Y "$WT_GITDIR/HEAD" 2>/dev/null || echo 0)
    WT_T=$(( ${WT_T_COMMIT:-0} > ${WT_T_ANLAGE:-0} ? ${WT_T_COMMIT:-0} : ${WT_T_ANLAGE:-0} ))
    if [ "$WT_T" -lt "$WT_GRENZE" ]; then
      WT_ALT="$WT_ALT $(basename "$WT_PFAD")($(( (WT_JETZT - WT_T) / 86400 ))d)"
    fi
  done < <(git -C "$TARGET_DIR" worktree list --porcelain 2>/dev/null \
             | awk '/^worktree /{print substr($0, 10)}' | tail -n +2)
  if [ "$WT_PRUNE_RC" -ne 0 ]; then
    record "E.8 worktree-hygiene" "WARN" \
      "git worktree prune scheiterte (rc=$WT_PRUNE_RC): $(head -c 100 "$TMP_ERR")" "$TARGET_REPO"
  elif [ -n "$WT_ALT" ]; then
    record "E.8 worktree-hygiene" "FAIL" \
      "aelter als $WT_MAX_TAGE Tage:$WT_ALT — entfernen (repo-session.sh reap / git worktree remove) oder mit Grund behalten (<gitdir>/behalten); prunable bereinigt: $WT_PRUNABLE" \
      "$TARGET_REPO"
  else
    record "E.8 worktree-hygiene" "PASS" \
      "$WT_N verknuepfte(r) Baum/Baeume, keiner aelter als $WT_MAX_TAGE Tage (behalten mit Grund: $WT_BEHALTEN); prunable bereinigt: $WT_PRUNABLE" \
      "$TARGET_REPO"
  fi
fi

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

# ── E.10 Sitzungs-Abgleich (Issues / Belege / serielle PRs) ─────────────────
# Drei registrierte Slugs in EINEM Werkzeug, alle advisory:
#   issue-offen-nach-gemergtem-fix · beleg-pr-nicht-gemergt ·
#   serielle-prs-auf-derselben-datei
# Belegte Muster: chat-hub #27 blieb OPEN trotz "alle fuenf Punkte erledigt",
# ausschreibungs-hub #184 war durch #195 erfuellt und blieb offen, writing-hub
# schrieb 9 von 10 mal `Refs` statt `Closes`. Der Runner reicht die RESULT-Zeile
# durch, er deutet sie nicht: HINWEIS = nicht falsifizierbar, also kein Gruen.
SAB="$PLATFORM_DIR/tools/session_abgleich.py"
SAB_BUDGET="${SESSION_ENDE_ABGLEICH_BUDGET:-180}"
if [ ! -f "$SAB" ]; then
  record "E.10 session-abgleich" "SKIP" "Werkzeug fehlt: tools/session_abgleich.py" "$TARGET_REPO"
elif ! command -v gh >/dev/null 2>&1 || [ -z "$OWNER" ]; then
  record "E.10 session-abgleich" "SKIP" "gh oder Owner nicht verfügbar" "$TARGET_REPO"
else
  SAB_OUT=$(timeout "$SAB_BUDGET" python3 "$SAB" --repo "$OWNER/$TARGET_REPO" \
            --seit "$HEUTE" 2>&1)
  SAB_RC=$?
  SAB_RES=$(printf '%s' "$SAB_OUT" | grep -m1 '^RESULT:' || true)
  if [ "$SAB_RC" -eq 124 ]; then
    record "E.10 session-abgleich" "SKIP" \
      "Zeitbudget ${SAB_BUDGET}s erschöpft — keine Entwarnung" "$TARGET_REPO"
  else
    case "$SAB_RES" in
      *"RESULT: BEFUND"*)
        record "E.10 session-abgleich" "WARN" \
          "$(printf '%s' "$SAB_OUT" | grep -m2 '^   ⚠' | tr '\n' ' ' | cut -c1-160) — Issue nachziehen ODER Fehlalarm notieren (advisory)" \
          "$TARGET_REPO" ;;
      *"RESULT: HINWEIS"*)
        record "E.10 session-abgleich" "SKIP" \
          "◌ $(printf '%s' "$SAB_RES" | cut -c1-60) — nicht falsifizierbar, keine Entwarnung" "$TARGET_REPO" ;;
      *"RESULT: OK"*)
        record "E.10 session-abgleich" "PASS" \
          "keine offenen Issues/Belege/Serien aus dieser Sitzung" "$TARGET_REPO" ;;
      *)
        record "E.10 session-abgleich" "SKIP" \
          "session_abgleich.py ohne verwertbare RESULT-Zeile (rc=$SAB_RC): $(printf '%s' "$SAB_OUT" | head -1 | cut -c1-120)" "$TARGET_REPO" ;;
    esac
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
