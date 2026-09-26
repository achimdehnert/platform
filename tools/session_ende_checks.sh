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
trap 'rm -f "$TMP_ERR"; if [ -z "${VORLAUF_BEHALTEN:-}" ]; then rm -rf "${VORLAUF_DIR:-}"; fi' EXIT

HEUTE="$(date +%Y-%m-%d)"
# Zeitbudget der Zusagen-Prüfung (E.5) je PR. 80 s je Segment sind gemessen
# (#2469) — ohne Deckel hält diese eine Phase die ganze Sitzung auf.
ZUSAGEN_BUDGET="${SESSION_ENDE_ZUSAGEN_BUDGET:-120}"
ZUSAGEN_MAX_PRS="${SESSION_ENDE_ZUSAGEN_MAX_PRS:-3}"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

declare -a P_NAME P_STATUS P_NOTE P_REPO P_DAUER
FAILED=0

# ── Laufzeit-Messung + Vorlauf (platform#3373, gleiche Mechanik wie der ──────
#    Start-Runner; Begruendung dort ausfuehrlich im Kopf des Vorlauf-Blocks)
_uhr() { local s="${EPOCHREALTIME:-$(date +%s).0}"; printf '%s' "${s/,/.}"; }
_spanne() { awk -v a="$1" -v b="$2" 'BEGIN{printf "%.1f", b-a}'; }
T_START="$(_uhr)"; T_LETZT="$T_START"

VORLAUF_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sec-vorlauf.XXXXXX")"
# Mit SESSION_CHECKS_VORLAUF_BEHALTEN=1 bleibt das Verzeichnis stehen (je Auftrag
# .out/.err/.rc) — ohne die Fehlerstroeme ist ein Melder, der nur im Vorlauf
# ausfaellt, nicht diagnostizierbar.
VORLAUF_BEHALTEN="${SESSION_CHECKS_VORLAUF_BEHALTEN:-}"
[ -n "$VORLAUF_BEHALTEN" ] && echo "hinweis: Vorlauf-Ausgaben bleiben in $VORLAUF_DIR" >&2
VORLAUF_MAX="${SESSION_CHECKS_PARALLEL:-8}"
declare -A VORLAUF_PID VORLAUF_CMD VORLAUF_MERGE
declare -a VORLAUF_Q=()
ERNTE_RC=0

# Gleiche Mechanik wie im Start-Runner, nur mit EINER Spur: `vorlauf*` sammelt
# ein, `_vorlauf_loslegen` startet so viele Arbeiter, wie die Spur breit ist,
# und jeder geht seine Auftraege der Reihe nach durch. Der Hauptlauf blockiert
# dabei nie — eine Drossel am Startpunkt haette sonst den Start der spaeteren
# Auftraege aufgehalten (im Start-Runner gemessen: 157 s statt 104 s).
_vorlauf_start() { # _vorlauf_start <merge 0|1> <schluessel> <befehl...>
  local merge="$1" key="$2"; shift 2
  if [ "$VORLAUF_MAX" -le 1 ]; then
    VORLAUF_CMD["$key"]="$(printf '%q ' "$@")"
    VORLAUF_MERGE["$key"]="$merge"
    return 0
  fi
  VORLAUF_Q+=("$(printf '%q ' "$merge" "$key" "$@")")
  return 0
}

_auftrag_ausfuehren() { # _auftrag_ausfuehren <merge 0|1> <schluessel> <befehl...>
  local merge="$1" key="$2"; shift 2
  # `</dev/null`: ein Hintergrund-Auftrag darf nicht an derselben
  # Standardeingabe haengen wie alle anderen.
  if [ "$merge" = 1 ]; then
    "$@" </dev/null >"$VORLAUF_DIR/$key.out" 2>&1
  else
    "$@" </dev/null >"$VORLAUF_DIR/$key.out" 2>"$VORLAUF_DIR/$key.err"
  fi
  echo $? >"$VORLAUF_DIR/$key.rc"
}

_vorlauf_loslegen() {
  [ "$VORLAUF_MAX" -le 1 ] && return 0
  local n=${#VORLAUF_Q[@]} max="$VORLAUF_MAX" i w pid k
  [ "$n" -eq 0 ] && return 0
  [ "$max" -gt "$n" ] && max="$n"
  for (( w = 0; w < max; w++ )); do
    (
      for (( i = w; i < n; i += max )); do
        eval "_auftrag_ausfuehren ${VORLAUF_Q[$i]}"
      done
    ) &
    pid=$!
    # Der Schluessel ist das zweite Feld; alle Schluessel hier sind schlichte
    # Woerter, `printf %q` laesst sie unveraendert.
    for (( i = w; i < n; i += max )); do
      read -r _ k _ <<<"${VORLAUF_Q[$i]}"
      VORLAUF_PID["$k"]=$pid
    done
  done
  VORLAUF_Q=()   # geleert, damit Nachschub (E.5) nicht noch einmal startet
  return 0
}
vorlauf()  { _vorlauf_start 0 "$@"; }  # Phase las mit 2>/dev/null bzw. 2>$TMP_ERR
vorlauf2() { _vorlauf_start 1 "$@"; }  # Phase las mit 2>&1
# Anders als der Start-Runner braucht dieser hier KEINE zweite, engere Spur fuer
# ssh: keines der Werkzeuge dieses Laufs oeffnet eine Verbindung zu den Prod-
# Hosts (geprueft per grep ueber drift_check.py, session_abgleich.py,
# verankerung_pruefer.py, agent_handover_freshness_check.py, doctor.py,
# befund_journal.py — die zwei Treffer im Pruefer stehen in Doku-Texten).
# Faellt das eines Tages um, gehoert die Spur aus dem Start-Runner hierher.

warte_auf() { # warte_auf <schluessel> — blockiert bis fertig, setzt ERNTE_RC
  local key="$1"
  if [ -n "${VORLAUF_CMD[$key]:-}" ]; then
    if [ "${VORLAUF_MERGE[$key]:-0}" = 1 ]; then
      ( eval "${VORLAUF_CMD[$key]}" >"$VORLAUF_DIR/$key.out" 2>&1 )
    else
      ( eval "${VORLAUF_CMD[$key]}" >"$VORLAUF_DIR/$key.out" 2>"$VORLAUF_DIR/$key.err" )
    fi
    echo $? >"$VORLAUF_DIR/$key.rc"
    unset "VORLAUF_CMD[$key]"
  elif [ -n "${VORLAUF_PID[$key]:-}" ]; then
    local p="${VORLAUF_PID[$key]}"
    wait "$p" 2>/dev/null
    # `wait` allein genuegt nicht: als `VAR=$(ernte k)` laeuft das in einer
    # Kommandosubstitution, und dort ist der Auftrag kein eigenes Kind — `wait`
    # kehrt sofort zurueck. Die rc-Datei schreibt der Auftrag als Letztes und ist
    # von jeder Shell aus sichtbar (Herleitung im Start-Runner).
    while [ ! -s "$VORLAUF_DIR/$key.rc" ]; do
      kill -0 "$p" 2>/dev/null || { sleep 0.1; break; }
      sleep 0.1
    done
  fi
  ERNTE_RC="$(cat "$VORLAUF_DIR/$key.rc" 2>/dev/null || echo 1)"
}
ernte() { warte_auf "$1"; cat "$VORLAUF_DIR/$1.out" 2>/dev/null; }
# Die gh-Phasen lasen ihre Fehlerausgabe bisher aus $TMP_ERR (#2794). Im Vorlauf
# hat jeder Auftrag seine eigene — sonst wuerde die Meldung des einen Auftrags
# im Text des anderen landen.
fehler_datei() { printf '%s' "$VORLAUF_DIR/$1.err"; }

# record <phase> <PASS|WARN|FAIL|SKIP> <note> [ziel-repo]
#   Pipes raus, sonst bricht die Summary-Tabelle.
#   Das 4. Argument nennt das Repo, um das es in dieser Zeile GEHT — nicht das
#   Repo, in dem die Sitzung läuft (Lehre aus dem Start-Runner: ein wanderndes
#   Etikett zerstört das Alter im Befund-Journal).
record() {
  P_NAME+=("$1"); P_STATUS+=("$2"); P_NOTE+=("$(echo "$3" | tr '|' '/')")
  P_REPO+=("${4:-$PLATTFORM_REPO}")
  local _jetzt; _jetzt="$(_uhr)"
  P_DAUER+=("$(_spanne "$T_LETZT" "$_jetzt")")
  T_LETZT="$_jetzt"
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

# ══ VORLAUF-SCHNITT (platform#3373) ═════════════════════════════════════════
# Ab hier bis E.7 ist jede Phase ein reiner Leser, und fast jede wartet auf
# GitHub (E.1/E.2/E.3/E.5/E.6/E.10) oder auf lokale Repo-Scans (E.7/E.9).
# Keine wartet auf das Ergebnis einer anderen — die einzige Kopplung ist
# E.3, das die ZAHL aus E.2 braucht, und die entsteht erst beim Ernten.
# Gestartet wird hier, geerntet unten an der angestammten Phasenstelle.
#
# Sequenziell bleibt E.8: `git worktree prune` veraendert den Baum. Die
# LLM-Laeufe in E.5 koennen erst starten, wenn die PR-Liste da ist — sie laufen
# dort untereinander nebeneinander.
_dirty_scan() { # E.7: ein `git status` je Repo unter $GITHUB_DIR
  for d in "$GITHUB_DIR"/*/; do
    [ -e "${d}.git" ] || continue
    [ -n "$(git -C "$d" status --porcelain 2>/dev/null)" ] || continue
    basename "$d"
  done
}
_dist_doctor() { # E.9: je Lane eine Zeile "<lane> <score|->"
  # Die drei Lanes laufen in EINEM Auftrag nacheinander, nicht in dreien
  # nebeneinander: `doctor.py` macht je Lane ein `git fetch` in $PLATFORM_DIR,
  # und zwei gleichzeitige Fetches im selben Repo streiten um dieselbe
  # Ref-Sperre — im Start-Runner gemessen (0.7.13 meldete `commands:UNGEPRUEFT`).
  local lane out score
  for lane in skills commands hooks; do
    out=$(timeout 120 python3 "$PLATFORM_DIR/tools/cc-skill-dist/doctor.py" --kind "$lane" 2>/dev/null || true)
    score=$(printf '%s' "$out" | grep -o 'DRIFT-SCORE: [0-9]*' | head -1 | grep -o '[0-9]*')
    printf '%s %s\n' "$lane" "${score:--}"
  done
}
_handover_freshness() { # E.3 im Nicht-Fragment-Modus
  cd "$TARGET_DIR" || return 2
  timeout 60 python3 "$HO_CHECK" --commits-schwelle "$HO_SCHWELLE" \
    --basis "$HO_BASIS" --beruehrung-auf-basis "$HO_FILE"
}

if command -v gh >/dev/null 2>&1 && [ -n "$OWNER" ]; then
  for r in $TOUCHED; do
    vorlauf "deploy:$r" timeout 60 gh run list -R "$OWNER/$r" --workflow Deploy --limit 1 \
      --json conclusion,status,databaseId \
      --jq '"\(.[0].conclusion // "none") \(.[0].status // "none") \(.[0].databaseId // "none")"'
  done
  vorlauf handover-pr-body timeout 60 gh pr list --repo "$OWNER/$TARGET_REPO" \
    --search "AGENT_HANDOVER.md in:body" --state open \
    --json number,updatedAt --jq '.[] | "#\(.number)@\(.updatedAt[0:10])"'
  # Der Datei-Fallback lief bisher nur, wenn die Body-Suche leer blieb. Er
  # laeuft jetzt immer mit — ein gh-Aufruf mehr pro Sitzung, dafuer faellt im
  # Fallback-Fall keine zweite Wartezeit von bis zu 90 s an. Ausgewertet wird
  # er unveraendert nur dann, wenn die Body-Suche leer war.
  vorlauf handover-pr-datei timeout 90 gh pr list --repo "$OWNER/$TARGET_REPO" --state open \
    --json number,files \
    --jq '.[] | select(.files[]?.path == "AGENT_HANDOVER.md") | "#\(.number)"'
  vorlauf zusagen-prs timeout 60 gh pr list --repo "$OWNER/$TARGET_REPO" --author @me --state all \
    --search "created:>=$HEUTE" --json number --jq '.[].number'
  if [ -f "$PLATFORM_DIR/tools/session_abgleich.py" ]; then
    # Mit --session-id nur die PRs DIESER Sitzung (#2234, Retro #3543 Befund #2):
    # Konto-weit waren es am 2026-09-24 35 Befunde, das eigene Issue ging unter.
    SAB_SITZUNG=()
    [ -n "$SESSION_ID" ] && SAB_SITZUNG=(--sitzung "$SESSION_ID" --lease-dir "$LEASE_DIR")
    vorlauf2 session-abgleich timeout "${SESSION_ENDE_ABGLEICH_BUDGET:-180}" \
      python3 "$PLATFORM_DIR/tools/session_abgleich.py" --repo "$OWNER/$TARGET_REPO" --seit "$HEUTE" \
      "${SAB_SITZUNG[@]}"
  fi
fi

# E.3: Fragment-Modus sucht per gh, sonst laeuft der Frische-Pruefer. Welcher
# Zweig greift, entscheidet ein Verzeichnis-Test — der steht hier schon fest.
HO_CHECK="$PLATFORM_DIR/scripts/checks/agent_handover_freshness_check.py"
HO_FILE="$TARGET_DIR/AGENT_HANDOVER.md"
FRAG_DIR_REL="docs/handover.d"
FRAG_RE=""
if [ -d "$TARGET_DIR/$FRAG_DIR_REL" ] && [ -n "$SESSION_ID" ]; then
  FRAG_RE="Z-${SESSION_ID}(-[0-9]+)?[.]md\$"
  if command -v gh >/dev/null 2>&1 && [ -n "$OWNER" ]; then
    # Je Treffer "#<nr> <pfad>": der Pfad traegt den Zeitstempel, den der
    # Nachlauf-Check (#2234) als juengstes Fragment braucht.
    vorlauf frag-pr timeout 90 gh pr list --repo "$OWNER/$TARGET_REPO" --state open \
      --json number,files \
      --jq ".[] | .number as \$n | .files[]? | select(.path | test(\"^docs/handover[.]d/.*$FRAG_RE\")) | \"#\\(\$n) \\(.path)\""
  fi
fi
if [ ! -d "$TARGET_DIR/$FRAG_DIR_REL" ] && [ -f "$HO_CHECK" ] && [ -f "$HO_FILE" ]; then
  HO_BASIS="HEAD"
  git -C "$TARGET_DIR" rev-parse --verify -q origin/main >/dev/null 2>&1 && HO_BASIS="origin/main"
  HO_SCHWELLE="${SESSION_ENDE_HANDOVER_SCHWELLE:-0}"
  vorlauf2 handover-frische _handover_freshness
fi

if [ -f "$PLATFORM_DIR/scripts/drift_check.py" ]; then
  vorlauf2 template-drift timeout "${SESSION_ENDE_DRIFT_TIMEOUT:-480}" \
    python3 "$PLATFORM_DIR/scripts/drift_check.py" --severity=error --skip-pypi --fail-on-error
fi
if [ -f "$PLATFORM_DIR/tools/befund_journal.py" ]; then
  vorlauf cross-repo timeout 90 python3 "$PLATFORM_DIR/tools/befund_journal.py" --offen-cross-repo
fi
if [ -f "$PLATFORM_DIR/tools/cc-skill-dist/doctor.py" ]; then
  vorlauf dist-doctor _dist_doctor
fi
vorlauf dirty-scan _dirty_scan

_vorlauf_loslegen
# ══ Ende Vorlauf-Start ══════════════════════════════════════════════════════

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
    OUT=$(ernte "deploy:$r")
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
  warte_auf handover-pr-body; RC=$ERNTE_RC; HPR=$(ernte handover-pr-body)
  if [ "$RC" -ne 0 ]; then
    record "E.2 handover-prs" "SKIP" \
      "gh scheiterte (rc=$RC): $(head -c 120 "$(fehler_datei handover-pr-body)")" "$TARGET_REPO"
    E2_DONE=1
  fi
  # Fallback, wenn die Body-Suche leer ist (keine gh-relevante Aenderung —
  # ebenfalls rc-geprueft, statt der zweite blinde Fleck zu werden).
  if [ "$E2_DONE" -eq 0 ] && [ -z "$HPR" ]; then
    warte_auf handover-pr-datei; RC=$ERNTE_RC; HPR=$(ernte handover-pr-datei)
    if [ "$RC" -ne 0 ]; then
      record "E.2 handover-prs" "SKIP" \
        "gh scheiterte (rc=$RC): $(head -c 120 "$(fehler_datei handover-pr-datei)")" "$TARGET_REPO"
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
# HO_CHECK/HO_FILE/FRAG_DIR_REL stehen am Vorlauf-Schnitt, weil dort schon
# feststeht, welcher der beiden Zweige laeuft (Verzeichnis-Test).
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
    # FRAG_RE ist am Vorlauf-Schnitt gesetzt (die PR-Suche braucht es dort).
    # Namen beginnen mit dem Zeitstempel — `tail -1` ist das JUENGSTE Fragment.
    FRAG_MAIN=$(git -C "$TARGET_DIR" ls-tree --name-only "origin/main:$FRAG_DIR_REL" 2>/dev/null \
      | grep -E -- "$FRAG_RE" | sort | tail -1)
    FRAG_PR=""; FRAG_PR_ROH=""
    if command -v gh >/dev/null 2>&1 && [ -n "$OWNER" ]; then
      FRAG_PR_ROH=$(ernte frag-pr)
      FRAG_PR=$(printf '%s\n' "$FRAG_PR_ROH" | awk 'NF{print $1}' | sort -u | head -3 | tr '\n' ' ')
    fi
    if [ -n "$FRAG_MAIN" ] || [ -n "$FRAG_PR" ]; then
      if [ -n "$FRAG_MAIN" ]; then
        FRAG_TEXT="Fragment der Sitzung liegt auf main: $FRAG_MAIN"
      else
        FRAG_TEXT="Fragment der Sitzung offen als PR ${FRAG_PR% }"
      fi
      # Nachlauf (#2234, Retro #3543 Befund #4): ein Fragment belegt nur den Stand
      # zu SEINER Zeit. Sitzung e911bf49 schrieb es 13:01Z und arbeitete danach
      # drei Stunden weiter — E.3 war trotzdem gruen. Massgeblich ist das juengste
      # eigene Fragment (main: `erstellt:` aus dem Kopf; PR: Zeitstempel im Namen).
      FRAG_ZEIT=""
      if [ -n "$FRAG_MAIN" ]; then
        FRAG_ZEIT=$(git -C "$TARGET_DIR" show "origin/main:$FRAG_DIR_REL/$FRAG_MAIN" 2>/dev/null \
          | sed -n 's/^erstellt:[[:space:]]*//p' | head -1 | tr -d "\"' \r")
        # Nur die Form, die fragments.py schreibt; sonst zaehlt der Dateiname.
        [[ "$FRAG_ZEIT" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || FRAG_ZEIT=""
      fi
      for f in $FRAG_MAIN $(printf '%s\n' "$FRAG_PR_ROH" | awk 'NF>1{print $2}'); do
        z=$(basename "$f" | sed -nE 's/^([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2})-([0-9]{2})-([0-9]{2})Z.*/\1T\2:\3:\4Z/p')
        # ISO-Zeitstempel gleicher Form sind lexikografisch vergleichbar.
        if [ -n "$z" ] && { [ -z "$FRAG_ZEIT" ] || [[ "$z" > "$FRAG_ZEIT" ]]; }; then FRAG_ZEIT="$z"; fi
      done
      SB="$PLATFORM_DIR/tools/sitzungs_branches.py"
      if [ ! -f "$SB" ]; then
        record "E.3 handover-frische" "SKIP" \
          "$FRAG_TEXT — Nachlauf nicht pruefbar: Werkzeug fehlt (tools/sitzungs_branches.py), keine Entwarnung" "$TARGET_REPO"
      elif [ -z "$FRAG_ZEIT" ]; then
        record "E.3 handover-frische" "SKIP" \
          "$FRAG_TEXT — Nachlauf nicht pruefbar: Fragment-Zeitpunkt nicht lesbar, keine Entwarnung" "$TARGET_REPO"
      else
        NL_OUT=$(timeout "${SESSION_ENDE_NACHLAUF_BUDGET:-90}" python3 "$SB" nachlauf \
          --sitzung "$SESSION_ID" --owner "$OWNER" --lease-dir "$LEASE_DIR" \
          --fragment-zeit "$FRAG_ZEIT" --fragment-muster "$FRAG_RE" 2>&1)
        NL_RC=$?
        NL_RES=$(printf '%s' "$NL_OUT" | grep -m1 '^RESULT:' || true)
        case "$NL_RES" in
          "RESULT: NACHLAUF"*)
            record "E.3 handover-frische" "FAIL" \
              "Fragment von $FRAG_ZEIT veraltet — danach angelegt: $(printf '%s' "$NL_RES" | sed -E 's/^RESULT: NACHLAUF ([0-9]+) /\1 PR(s) /' | cut -c1-160) — fragments.py neu --session-id $SESSION_ID" "$TARGET_REPO" ;;
          "RESULT: OK"*)
            record "E.3 handover-frische" "PASS" \
              "$FRAG_TEXT; kein Sitzungs-PR nach $FRAG_ZEIT (${NL_RES#RESULT: OK })" "$TARGET_REPO" ;;
          *)
            [ "$NL_RC" -eq 124 ] && NL_RES="Zeitbudget erschoepft"
            record "E.3 handover-frische" "SKIP" \
              "$FRAG_TEXT — Nachlauf nicht pruefbar: $(printf '%s' "${NL_RES#RESULT: }" | cut -c1-140), keine Entwarnung" "$TARGET_REPO" ;;
        esac
      fi
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
  # HO_BASIS/HO_SCHWELLE stehen am Vorlauf-Schnitt (der Pruefer braucht sie dort).
  warte_auf handover-frische; HO_RC=$ERNTE_RC; HO_OUT=$(ernte handover-frische)
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
  BJ_OUT=$(ernte cross-repo)
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
  warte_auf zusagen-prs; RC=$ERNTE_RC; PRS=$(ernte zusagen-prs)
  PRS=$(printf '%s' "$PRS" | head -n "$ZUSAGEN_MAX_PRS")
  if [ "$RC" -ne 0 ]; then
    record "E.5 zusagen" "SKIP" \
      "◌ gh scheiterte (rc=$RC): $(head -c 120 "$(fehler_datei zusagen-prs)")" "$TARGET_REPO"
  elif [ -z "$PRS" ]; then
    record "E.5 zusagen" "PASS" "keine eigenen PRs von heute in $OWNER/$TARGET_REPO" "$TARGET_REPO"
  else
    Z_OK=""; Z_WARN=""; Z_UNKLAR=""
    # Welche PRs zu pruefen sind, steht erst jetzt fest — deshalb kein Vorlauf,
    # sondern hier: bis zu drei Pruefungen mit je bis zu 120 s Budget liefen
    # nacheinander, obwohl keine auf die andere wartet (platform#3373).
    # Der Schluessel bleibt eine Zuweisung VOR dem Befehl und wandert nicht als
    # `env KEY=…`-Argument in die Prozessliste — deshalb die Funktion statt eines
    # direkten vorlauf2-Aufrufs.
    _zusage_probe() { # _zusage_probe <pr-nummer>
      GROQ_API_KEY="$ZUSAGEN_GROQ_KEY" timeout "$((ZUSAGEN_BUDGET + 60))" \
        python3 "$VP" --pr "$1" --repo "$OWNER/$TARGET_REPO" \
        --budget-sekunden "$ZUSAGEN_BUDGET" --provider "$ZUSAGEN_PROVIDER"
    }
    for nr in $PRS; do
      vorlauf2 "zusage:$nr" _zusage_probe "$nr"
    done
    _vorlauf_loslegen
    for nr in $PRS; do
      Z_OUT=$(ernte "zusage:$nr")
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
  warte_auf template-drift; DC_RC=$ERNTE_RC; DC_OUT=$(ernte template-drift)
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
# Der Scan (ein `git status` je Repo) laeuft im Vorlauf; hier wird nur sortiert.
while read -r n; do
  [ -n "$n" ] || continue
  case " $TOUCHED " in
    *" $n "*) DIRTY_EIGEN="$DIRTY_EIGEN $n" ;;
    *)        DIRTY_FREMD="$DIRTY_FREMD $n" ;;
  esac
done < <(ernte dirty-scan)
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
  declare -A DD_GESEHEN=()
  while read -r LANE LANE_SCORE; do
    [ -n "$LANE" ] || continue
    DD_GESEHEN["$LANE"]=1
    [ "$LANE_SCORE" = "-" ] && LANE_SCORE=""
    if [ -z "$LANE_SCORE" ]; then
      DD_STATUS="WARN"; DD_NOTE="${DD_NOTE}${LANE}:UNGEPRUEFT "
    elif [ "$LANE_SCORE" -gt 0 ]; then
      DD_STATUS="WARN"; DD_NOTE="${DD_NOTE}${LANE}:${LANE_SCORE} "
    else
      DD_NOTE="${DD_NOTE}${LANE}:0 "
    fi
  done < <(ernte dist-doctor)
  # Eine Lane, von der gar keine Zeile kam, ist ungeprueft — und ungeprueft ist
  # kein Gruen (KONZ-platform-050). Ohne diese Schleife saehe ein komplett
  # ausgefallener Auftrag wie "alle Lanes synchron ()" aus.
  for LANE in skills commands hooks; do
    [ -n "${DD_GESEHEN[$LANE]:-}" ] && continue
    DD_STATUS="WARN"; DD_NOTE="${DD_NOTE}${LANE}:UNGEPRUEFT "
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
  warte_auf session-abgleich; SAB_RC=$ERNTE_RC; SAB_OUT=$(ernte session-abgleich)
  SAB_RES=$(printf '%s' "$SAB_OUT" | grep -m1 '^RESULT:' || true)
  if [ "$SAB_RC" -eq 124 ]; then
    record "E.10 session-abgleich" "SKIP" \
      "Zeitbudget ${SAB_BUDGET}s erschöpft — keine Entwarnung" "$TARGET_REPO"
  else
    # Anzahl + kompakte Refs statt einer abgeschnittenen Zeile (#2234, Retro #3543
    # Befund #2: von 35 Befunden war genau einer sichtbar, das eigene #3469 nicht).
    SAB_N=$(printf '%s' "$SAB_RES" | sed -nE 's/.*RESULT: BEFUND ([0-9]+).*/\1/p')
    SAB_REFS=$(printf '%s' "$SAB_OUT" | sed -n 's/^KURZ: //p' | head -1)
    if [ -n "$SESSION_ID" ]; then SAB_WEITE="dieser Sitzung"; else SAB_WEITE="kontoweit, ohne --session-id nicht sitzungsgenau"; fi
    case "$SAB_RES" in
      *"RESULT: BEFUND"*)
        record "E.10 session-abgleich" "WARN" \
          "${SAB_N:-?} Befund(e) ${SAB_WEITE}: $(printf '%s' "$SAB_REFS" | cut -c1-200) — je Ref Issue nachziehen ODER Fehlalarm notieren (advisory)" \
          "$TARGET_REPO" ;;
      *"sitzung-nicht-zuordenbar"*)
        record "E.10 session-abgleich" "SKIP" \
          "◌ Sitzung $SESSION_ID nicht zuordenbar: $(printf '%s' "$SAB_RES" | sed -E 's/.*sitzung-nicht-zuordenbar: //; s/\)$//' | cut -c1-140) — keine Entwarnung" "$TARGET_REPO" ;;
      *"RESULT: HINWEIS"*)
        record "E.10 session-abgleich" "SKIP" \
          "◌ $(printf '%s' "$SAB_RES" | cut -c1-60) — nicht falsifizierbar, keine Entwarnung" "$TARGET_REPO" ;;
      *"RESULT: OK"*)
        record "E.10 session-abgleich" "PASS" \
          "keine offenen Issues/Belege/Serien (${SAB_WEITE})" "$TARGET_REPO" ;;
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

# ── Laufzeit (platform#3373, gleiche Form wie im Start-Runner) ──────────────
T_ENDE="$(_uhr)"
LAUF_TOP=$(for i in "${!P_NAME[@]}"; do
             printf '%s\t%s\n' "${P_DAUER[$i]:-0}" "${P_NAME[$i]}"
           done | sort -rn | head -5 | awk -F'\t' '{printf "%s %ss · ", $2, $1}')
if [ "$VORLAUF_MAX" -le 1 ]; then LAUF_MODUS="sequenziell"; else LAUF_MODUS="Vorlauf ${VORLAUF_MAX}-fach"; fi
echo "LAUFZEIT: $(_spanne "$T_START" "$T_ENDE")s gesamt (${LAUF_MODUS}) · langsamste: ${LAUF_TOP% · }"
if [ "${SESSION_CHECKS_TIMING:-}" = "voll" ]; then
  echo ""
  echo "| Phase | Dauer (s) |"
  echo "|---|---|"
  for i in "${!P_NAME[@]}"; do printf '| %s | %s |\n' "${P_NAME[$i]}" "${P_DAUER[$i]:-0}"; done
fi
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
