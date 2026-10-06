#!/usr/bin/env bash
# repo-session — verbindlicher Entry Point fuer editierende Coding-Sessions (ADR-233).
#
# GATE_HEADER (KONZ-038 D8) — auch in Shell maschinenlesbar gehalten, damit
# tools/gate_drill_check.py Kopf und Registry gegeneinander pruefen kann:
#   "slug": "parallel-session-pr-collision"
#   "mode": "process"
#   "owner": "achim"
#   "last_drill_pass": "2026-08-12"
#   "evidence": "tools/tests/test_repo_session_pr_collision.py"
# Der Guard selbst: check_pr_collision() unten — harter Block beim `start`,
# wenn ein offener PR denselben Task-Slug traegt (ADR-233 R-6). Bestand seit
# 5cefbb0a, registriert erst 2026-08-12 (platform#1650 Nachmessung: ein echtes,
# aber unregistriertes Gate drillt niemand).
#
# Statt im geteilten Haupt-Tree den Branch zu wechseln (HEAD-Flip-Kollision), legt
# jede editierende Session hier einen isolierten git-Worktree VON origin/main an,
# mit deterministischem Branch-Schema und einer maschinenlesbaren Lease, die der
# worktree-reaper konsumiert. Der Haupt-Tree bleibt "heilig" auf main.
#
# Usage:
#   repo-session.sh start <repo-path> --task <slug> [--ziel <text>] [--base <ref>] [--ephemeral]
#                         [--befund <phase::repo>]...  # Befund-Sperre belegen; belegt -> exit 3
#   repo-session.sh befunde                    # aktive Befund-Sperren (key, Lease, Alter)
#   repo-session.sh list
#   repo-session.sh abstand [<repo>]           # Commits hinter origin/main je Lease; exit 1 ueber Schwelle
#   repo-session.sh end <worktree-path>        # Worktree entfernen (nur wenn clean), Lease schliessen
#   repo-session.sh reap [<repo-path>]         # gemergte+cleane Session-Worktrees des Repos abraeumen
#                                              # (default: Repo des cwd); Leases werden .closed
#
# Lease-Felder (ADR-233 §2.4): session_id, owner, created_at, last_touch, branch,
#   base_sha, repo, worktree, ziel, intended_pr, expires_at, ephemeral,
#   claude_session.
#
# `claude_session` (platform#2234, Retro #3543 Befunde #2/#4) = $CLAUDE_CODE_SESSION_ID
# beim Start, leer ohne diese Variable. `session_id` ist die LEASE-ID, nicht die
# Claude-Sitzung — ohne dieses Feld konnte kein Werkzeug die PRs EINER Sitzung von
# denen paralleler Sitzungen desselben Kontos trennen (tools/sitzungs_branches.py).
#
# Befund-Sperre (platform#3495 V1): Am 2026-09-24 legten zwei Sitzungen desselben
# Owners 6 s auseinander dieselben PRs an (#3465/#3466) und 17 s auseinander
# dieselben Issues (#3467/#3468) — beide bearbeiteten denselben Session-Start-
# Befund. Keiner der drei Mechanismen griff: 0.4 parallel-sessions meldet nur
# PASS (#1944 K8), check_pr_collision() blockt nur bei gleichem Task-Slug, die
# PR-Liste laeuft einmal beim Start und fail-open. Deshalb belegt
# `start --befund <phase::repo>` den Journal-Schluessel atomar als Datei
# $LEASE_DIR/befund/<key>.lock (noclobber = O_EXCL, Inhalt: key, lease_id,
# worktree, created_at, expires_at = Lease-TTL). Ein zweiter `start` auf denselben
# Schluessel bricht mit exit 3 ab, BEVOR ein Worktree entsteht. Frei wird die
# Sperre durch `end`, durch Ablauf (expires_at) oder wenn ihre Lease geschlossen
# ist (.json.closed — so schliesst auch worktree-reaper.py); `reap` raeumt solche
# Dateien ab. Der Runner (session_start_checks.sh) zeigt aktive Sperren ueber
# `befunde` als "in Arbeit von <lease>".
#
# Env:
#   REPO_SESSION_DIR   (default ~/.repo-session)  — Leases + Worktree-Wurzel
#   REPO_SESSION_TTL_DAYS (default 7)             — expires_at = created_at + TTL
#   REPO_SESSION_ABSTAND_MAX (default 25)         — Schwelle fuer 'abstand' (Commits hinter main)
set -euo pipefail

ROOT="${REPO_SESSION_DIR:-$HOME/.repo-session}"
LEASE_DIR="$ROOT/leases"
WT_ROOT="$ROOT/worktrees"
EPHEMERAL_ROOT="/tmp/repo-session"   # ADR-233 R-5: /tmp nur fuer ephemere
TTL_DAYS="${REPO_SESSION_TTL_DAYS:-7}"

die() { echo "FEHLER: $*" >&2; exit 1; }

slug() { printf '%s' "$1" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9._-'; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Reap (Retro f5e1d F-P4, Gate worktree-midsession-accumulation ×2 → Gate-Pflicht):
# gemergte+cleane Session-Worktrees eines Repos entfernen + Leases schliessen.
# Delegiert an tools/worktree-reaper.py (ADR-233) statt Logik zu duplizieren —
# der Reaper ist self-protecting: DIRTY = SKIP, offener/unbestimmbarer PR-Status
# = KEEP, un-gemergte Branches werden NIE entfernt (--include-stale hier bewusst
# NICHT gesetzt), Restore-Manifest wird geschrieben.
reap_repo() {
  local repo="$1"
  local reaper="$SCRIPT_DIR/worktree-reaper.py"
  [ -f "$reaper" ] || { echo "  ⚠ worktree-reaper.py nicht gefunden ($reaper) — reap übersprungen." >&2; return 1; }
  local rc=0
  ( cd "$repo" && python3 "$reaper" --apply ) || rc=$?
  # Der Reaper schliesst Leases (.json.closed), kennt aber keine Befund-Sperren —
  # deren Dateien hier nachziehen (#3495 V1). Best-effort, nie werfend.
  befund_aufraeumen >&2 || true
  return $rc
}

# ---------------------------------------------------------------------------
# Befund-Sperre je Journal-Schluessel (platform#3495 V1, Begruendung im Kopf)
# ---------------------------------------------------------------------------
BEFUND_DIR="$LEASE_DIR/befund"
BEFUND_EXIT=3

befund_datei() {
  # Dateiname aus dem Schluessel: alles ausser [A-Za-z0-9._-] wird '_'
  # ("0.7 deploy-scan::platform" -> "0.7_deploy-scan__platform.lock").
  # Der echte Schluessel steht im Inhalt und wird beim Belegen verglichen.
  printf '%s/%s.lock' "$BEFUND_DIR" "$(printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '_')"
}

# Zustand einer Sperr-Datei, tab-getrennt:
#   <zustand> <key> <lease_id> <created_at> <alter> <worktree>
# zustand: belegt | abgelaufen | verwaist (Lease geschlossen) | frei (Datei fehlt).
# Eine unlesbare Datei (Absturz zwischen Anlegen und Schreiben) gilt 60 s als
# belegt, danach als verwaist — sonst sperrte ein Crash den Schluessel eine Woche.
befund_zustand() {
  python3 - "$1" "$LEASE_DIR" <<'PY'
import datetime as dt, json, os, sys, time
f, lease_dir = sys.argv[1], sys.argv[2]
fmt = "%Y-%m-%dT%H:%M:%SZ"
now = dt.datetime.now(dt.timezone.utc)
def alter(ts):
    try:
        s = int((now - dt.datetime.strptime(ts, fmt).replace(tzinfo=dt.timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return "?"
    return f"{s // 3600} h {s % 3600 // 60} min" if s >= 3600 else f"{s // 60} min {s % 60} s"
try:
    d = json.load(open(f))
except FileNotFoundError:
    print("frei\t\t\t\t\t"); sys.exit(0)
except (OSError, ValueError):
    try:
        jung = time.time() - os.path.getmtime(f) < 60
    except OSError:
        jung = False
    print(("belegt" if jung else "verwaist") + "\t?\t?\t?\t?\t?"); sys.exit(0)
key, lid = d.get("key", "?"), d.get("lease_id", "")
created, wt = d.get("created_at", "?"), d.get("worktree", "?")
zustand = "belegt"
try:
    if dt.datetime.strptime(d.get("expires_at", ""), fmt).replace(tzinfo=dt.timezone.utc) <= now:
        zustand = "abgelaufen"
except ValueError:
    pass
lp = os.path.join(lease_dir, f"{lid}.json")
if zustand == "belegt" and lid and not os.path.exists(lp) and os.path.exists(lp + ".closed"):
    zustand = "verwaist"
print("\t".join([zustand, key, lid or "?", created, alter(created), wt]))
PY
}

befund_freigeben() {
  # Alle Sperren einer Lease entfernen (end, abgebrochener start).
  local lid="$1" f z k l rest
  [ -n "$lid" ] && [ -d "$BEFUND_DIR" ] || return 0
  for f in "$BEFUND_DIR"/*.lock; do
    [ -e "$f" ] || continue
    IFS=$'\t' read -r z k l rest <<<"$(befund_zustand "$f")"
    if [ "$l" = "$lid" ]; then
      rm -f "$f" && echo "Befund-Sperre freigegeben: $k"
    fi
  done
}

befund_aufraeumen() {
  # Abgelaufene + verwaiste Sperren entfernen (reap-Pfad).
  local f z k l rest
  [ -d "$BEFUND_DIR" ] || return 0
  for f in "$BEFUND_DIR"/*.lock; do
    [ -e "$f" ] || continue
    IFS=$'\t' read -r z k l rest <<<"$(befund_zustand "$f")"
    case "$z" in
      abgelaufen|verwaist) rm -f "$f" && echo "  ♻ Befund-Sperre $z entfernt: $k (Lease $l)";;
    esac
  done
}

# befund_belegen <lease_id> <worktree> <expires_at> <key>...
# Belegt alle Schluessel oder keinen: scheitert einer, werden die in diesem
# Aufruf schon belegten wieder freigegeben. Rueckgabe BEFUND_EXIT bei Belegung.
# Atomar ist das Anlegen per noclobber (O_EXCL); flock serialisiert nur die
# Uebernahme abgelaufener Sperren (rm + neu anlegen), damit zwei Uebernehmer
# sich nicht gegenseitig die frische Sperre loeschen.
befund_belegen() {
  local lid="$1" wt="$2" exp="$3"; shift 3
  [ $# -gt 0 ] || return 0
  mkdir -p "$BEFUND_DIR"
  local mutex_offen=0
  if command -v flock >/dev/null 2>&1; then
    exec 9>"$BEFUND_DIR/.mutex"
    flock -w 10 9 && mutex_offen=1
  fi
  local belegt=() key f z k l created alt owt now json rc=0
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for key in "$@"; do
    f="$(befund_datei "$key")"
    IFS=$'\t' read -r z k l created alt owt <<<"$(befund_zustand "$f")"
    case "$z" in
      belegt)
        echo "⛔ Befund $key in Arbeit von $l seit $created (Worktree $owt)." >&2
        [ "$k" != "$key" ] && echo "   (Sperr-Datei traegt Schluessel '$k' — gleicher Dateiname)" >&2
        echo "   → andere Sitzung fertig werden lassen ODER dort 'repo-session.sh end <worktree>'." >&2
        rc=$BEFUND_EXIT; break;;
      abgelaufen|verwaist)
        echo "  ↻ Befund-Sperre $key übernommen — vorige Sperre $z (Lease $l seit $created)." >&2
        rm -f "$f";;
    esac
    json="$(python3 -c 'import json,sys; print(json.dumps(dict(zip(["key","lease_id","worktree","created_at","expires_at"], sys.argv[1:])), ensure_ascii=False))' \
      "$key" "$lid" "$wt" "$now" "$exp")"
    if ( set -o noclobber; printf '%s\n' "$json" > "$f" ) 2>/dev/null; then
      belegt+=("$f")
    else
      echo "⛔ Befund $key soeben von einer anderen Sitzung belegt (Wettlauf verloren)." >&2
      rc=$BEFUND_EXIT; break
    fi
  done
  if [ "$mutex_offen" -eq 1 ]; then flock -u 9; fi
  exec 9>&- 2>/dev/null || true
  if [ "$rc" -ne 0 ] && [ "${#belegt[@]}" -gt 0 ]; then rm -f "${belegt[@]}"; fi
  return $rc
}

cmd_befunde() {
  local n=0 alt_n=0 f z k l created alt owt
  if [ -d "$BEFUND_DIR" ]; then
    for f in "$BEFUND_DIR"/*.lock; do
      [ -e "$f" ] || continue
      IFS=$'\t' read -r z k l created alt owt <<<"$(befund_zustand "$f")"
      if [ "$z" = "belegt" ]; then
        echo "⛔ in Arbeit von $l (seit $created, $alt): $k"
        n=$((n+1))
      elif [ "$z" != "frei" ]; then
        alt_n=$((alt_n+1))
      fi
    done
  fi
  if [ "$n" -eq 0 ]; then echo "keine aktiven Befund-Sperren."; else echo "$n aktive Befund-Sperre(n)."; fi
  [ "$alt_n" -eq 0 ] || echo "($alt_n abgelaufene/verwaiste Sperre(n) — 'repo-session.sh reap' raeumt ab)"
}

cmd_reap() {
  # --alle: jedes Repo abraeumen, das ueberhaupt eine Lease hat — nicht nur das
  # gerade bearbeitete. Grund (Retro 2026-08-20, Gate `worktree-midsession-accumulation`
  # als RUECKFAELLIG gemessen): der Reaper funktioniert, wird aber nur fuer das
  # Start-Repo gerufen. Worktrees entstehen mitten in der Sitzung und werden oft
  # von jemand anderem gemergt — dann sieht der naechste Start sie nie, weil er
  # ein anderes Repo betrifft. Ueber die Leases zu gehen schliesst genau diese Luecke.
  if [ "${1:-}" = "--alle" ]; then
    [ -d "$LEASE_DIR" ] || { echo "keine Leases."; return 0; }
    local repos="" name pfad
    for l in "$LEASE_DIR"/*.json; do
      [ -e "$l" ] || continue
      name="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('repo',''))" "$l" 2>/dev/null)"
      [ -n "$name" ] || continue
      pfad="${GITHUB_DIR:-$HOME/github}/$name"
      [ -d "$pfad/.git" ] || continue
      case " $repos " in *" $pfad "*) continue;; esac
      repos="$repos $pfad"
    done
    [ -n "$repos" ] || { echo "keine Repos mit Leases."; return 0; }
    local rc=0
    for pfad in $repos; do
      echo "── reap $pfad"
      reap_repo "$pfad" || rc=1
    done
    return $rc
  fi
  local repo="${1:-$PWD}"
  local common
  common="$(git -C "$repo" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" \
    || die "kein git-Repo: $repo"
  repo="${common%/.git}"   # Haupt-Tree, auch wenn aus einem Linked-Worktree aufgerufen
  reap_repo "$repo"
}

# PR-Kollisionscheck (ADR-233 R-6; Retro-Gate `parallel-session-pr-collision`, ≥2× → Gate-Pflicht).
# Billigster Check VOR dem Abzweigen: existiert für denselben Task-Slug schon ein offener PR
# (= zweite Session am selben Thema), harter Block. Sonst offene PRs zur Awareness listen.
# Fail-open NUR bei fehlendem Werkzeug/Auth (mit sichtbarem Hinweis) — nie stiller Durchlass.
# Override für bewusst parallele Arbeit: REPO_SESSION_SKIP_PR_CHECK=1.
check_pr_collision() {
  local repo="$1" task="$2"
  if [ "${REPO_SESSION_SKIP_PR_CHECK:-0}" = "1" ]; then
    echo "  ⚠ PR-Kollisionscheck übersprungen (REPO_SESSION_SKIP_PR_CHECK=1)." >&2; return 0
  fi
  command -v gh >/dev/null 2>&1 || { echo "  ⚠ gh nicht verfügbar — PR-Kollisionscheck übersprungen (ADR-233 R-6)." >&2; return 0; }
  local slug_repo; slug_repo="$(git -C "$repo" remote get-url origin 2>/dev/null | sed -E 's#\.git$##; s#.*[:/]([^/]+/[^/]+)$#\1#')"
  [ -n "$slug_repo" ] || { echo "  ⚠ Remote-Slug nicht bestimmbar — PR-Kollisionscheck übersprungen." >&2; return 0; }
  local open_prs; open_prs="$(gh pr list -R "$slug_repo" --state open --json number,headRefName,title 2>/dev/null)" \
    || { echo "  ⚠ 'gh pr list' fehlgeschlagen (Auth?) — PR-Kollisionscheck übersprungen." >&2; return 0; }
  if [ -z "$open_prs" ] || [ "$open_prs" = "[]" ]; then return 0; fi
  # Exakter Task-Slug im head-branch eines offenen PR = harter Block.
  local hit
  hit="$(printf '%s' "$open_prs" | python3 -c "import json,sys; t=sys.argv[1]; d=json.load(sys.stdin); print('\n'.join(f\"#{p['number']} {p['headRefName']} — {p['title']}\" for p in d if t and t in p['headRefName']))" "$task")"
  if [ -n "$hit" ]; then
    {
      echo "⛔ PR-Kollision (ADR-233 R-6, Retro-Gate parallel-session-pr-collision):"
      echo "   Offene PR(s) mit Task-Slug '$task':"
      printf '   %s\n' "$hit"
      echo "   → mergen/schließen ODER anderen --task-Slug wählen ODER REPO_SESSION_SKIP_PR_CHECK=1 (bewusst parallel)."
    } >&2
    die "Task '$task' hat bereits offene PR(s) — Kollisionsgefahr (siehe oben)."
  fi
  # Sonst: offene PRs zur Awareness (weich, kein Block).
  local n; n="$(printf '%s' "$open_prs" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))')"
  {
    echo "  ℹ $n offene PR(s) in $slug_repo — auf Scope-Überlappung achten:"
    printf '%s' "$open_prs" | python3 -c "import json,sys;[print(f\"     #{p['number']} {p['headRefName']}\") for p in json.load(sys.stdin)]"
  } >&2
}

cmd_start() {
  local repo="" task="" base="origin/main" ephemeral="false"
  local ziel=""
  local befunde=()
  repo="${1:-}"; shift || true
  while [ $# -gt 0 ]; do
    case "$1" in
      --task) task="$2"; shift 2;;
      --ziel) ziel="$2"; shift 2;;
      --befund)
        [ -n "${2:-}" ] || die "--befund <phase::repo> ohne Schluessel"
        case " ${befunde[*]:-} " in *" $2 "*) ;; *) befunde+=("$2");; esac
        shift 2;;
      --base) base="$2"; shift 2;;
      --ephemeral) ephemeral="true"; shift;;
      *) die "unbekannte Option: $1";;
    esac
  done
  [ -n "$repo" ] || die "repo-path fehlt"
  [ -n "$task" ] || die "--task <slug> fehlt"
  # --ziel ist bewusst OPTIONAL, kein Zwang. Ein Pflichtfeld waere eine Huerde
  # vor jeder Kleinigkeit; als Feld beantwortet es dagegen zwei Fragen, die heute
  # geraten werden muessen: "warum existiert dieser Branch" (Wildwuchs) und
  # "welche PRs gehoeren zu dieser Sitzung" (Retro-Grenze — musste am 2026-08-04
  # aus Branch-Praefixen rekonstruiert werden, wobei 7 fremde PRs auszusortieren
  # waren).
  # Immer kanonisieren (#1360): vorher nur im Fallback-Zweig, wenn "$repo/.git"
  # fehlte. Aufruf mit "." aus dem Haupt-Tree traf den Fallback NIE (".git"
  # existiert ja) und liess $repo="." stehen -> "repo": "." im Lease + "/./"
  # im Worktree-Pfad (basename "." == ".").
  repo="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || die "kein git-Repo: $repo"

  # Haupt-Tree heilig: muss auf main stehen, bevor wir abzweigen.
  local cur; cur="$(git -C "$repo" rev-parse --abbrev-ref HEAD)"
  [ "$cur" = "main" ] || die "Haupt-Tree ($repo) ist auf '$cur', nicht 'main' — heiliger Tree verletzt (ADR-233)."

  git -C "$repo" fetch --prune origin main -q
  local base_sha; base_sha="$(git -C "$repo" rev-parse "$base")" || die "base_ref '$base' nicht auflösbar"

  # Self-healing Reap (Retro f5e1d F-P4): jede neue Session räumt zuerst die
  # gemergten Orphan-Worktrees des Ziel-Repos ab — der Pflicht-Reaper lief bisher
  # nur bei /session-ende, nicht beim Merger. Leise + best-effort: ein Fehler hier
  # darf 'start' NIE scheitern lassen (Warnung statt Abbruch).
  local reap_out=""
  if reap_out="$(reap_repo "$repo" 2>&1)"; then
    local reaped
    reaped="$(printf '%s\n' "$reap_out" | grep -c '^entfernt:')" || reaped=0
    if [ "${reaped:-0}" -gt 0 ]; then
      {
        echo "  ♻ Auto-Reap: $reaped gemergte(r) Orphan-Worktree(s) entfernt (self-healing, F-P4):"
        printf '%s\n' "$reap_out" | grep '^entfernt:' | sed 's/^/    /'
      } >&2
    fi
    # Abgelaufene/verwaiste Befund-Sperren (#3495 V1) raeumt der Reap-Pfad ab —
    # die Uebernahme soll trotzdem sichtbar bleiben.
    printf '%s\n' "$reap_out" | grep '♻ Befund-Sperre' >&2 || true
  else
    echo "  ⚠ Auto-Reap fehlgeschlagen — best-effort, 'start' läuft weiter (letzte Zeile: $(printf '%s\n' "$reap_out" | tail -1))" >&2
  fi

  local owner date_s rname branch wt sid slug_repo_start
  owner="$(slug "$(git -C "$repo" config user.name 2>/dev/null || echo agent)")"; owner="${owner:-agent}"
  date_s="$(date -u +%Y-%m-%d)"
  rname="$(basename "$repo")"
  task="$(slug "$task")"
  # owner/repo-Slug fuer gh-Aufrufe (Kollisionscheck + Anzeige offener PRs unten) —
  # gleiche Ableitung wie in check_pr_collision().
  slug_repo_start="$(git -C "$repo" remote get-url origin 2>/dev/null | sed -E 's#\.git$##; s#.*[:/]([^/]+/[^/]+)$#\1#')"

  # ADR-233 R-6: vor dem Abzweigen auf offene PRs desselben Task-Slugs prüfen (Retro-Gate).
  check_pr_collision "$repo" "$task"

  branch="session/$date_s/$owner/$task"
  sid="${date_s}-${owner}-${task}-$(date -u +%H%M%S)"
  if [ "$ephemeral" = "true" ]; then
    wt="$EPHEMERAL_ROOT/$rname/$sid"
  else
    wt="$WT_ROOT/$rname/$sid"
  fi
  mkdir -p "$(dirname "$wt")" "$LEASE_DIR"

  local now exp lease ziel_json cs_json
  exp="$(date -u -d "+${TTL_DAYS} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"

  # Befund-Sperre (#3495 V1) VOR dem Worktree: eine zweite Sitzung auf denselben
  # Schluessel soll abbrechen, ohne Branch und Worktree zu hinterlassen.
  if [ "${#befunde[@]}" -gt 0 ]; then
    local brc=0
    befund_belegen "$sid" "$wt" "$exp" "${befunde[@]}" || brc=$?
    [ "$brc" -eq 0 ] || exit "$brc"
  fi

  if ! git -C "$repo" worktree add -b "$branch" "$wt" "$base" >&2; then
    befund_freigeben "$sid" >&2
    die "worktree add fehlgeschlagen (Branch '$branch' evtl. vergeben?)"
  fi

  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [ -n "$ziel" ]; then
    ziel_json="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$ziel")"
  else
    ziel_json="null"
  fi
  # JSON-kodiert wie `ziel`: der Wert kommt aus der Umgebung, nicht aus diesem Skript.
  cs_json="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${CLAUDE_CODE_SESSION_ID:-}")"
  lease="$LEASE_DIR/$sid.json"
  cat > "$lease" <<JSON
{
  "session_id": "$sid",
  "owner": "$owner",
  "repo": "$rname",
  "branch": "$branch",
  "base_sha": "$base_sha",
  "worktree": "$wt",
  "created_at": "$now",
  "last_touch": "$now",
  "expires_at": "$exp",
  "ziel": ${ziel_json},
  "intended_pr": null,
  "ephemeral": $ephemeral,
  "claude_session": ${cs_json}
}
JSON
  echo "$wt"                 # stdout = Worktree-Pfad (zum cd)
  {
    echo "✓ Session-Worktree angelegt (ADR-233):"
    echo "  Branch : $branch  (von $base @ ${base_sha:0:12})"
    echo "  Pfad   : $wt"
    [ -n "$ziel" ] && echo "  Ziel   : $ziel"
    echo "  Lease  : $lease  (expires $exp, ephemeral=$ephemeral)"
    [ "${#befunde[@]}" -eq 0 ] || echo "  Befund : ${befunde[*]}  (gesperrt bis end/expires)"
    echo "  cd \"$wt\""
  } >&2

  # Offene PRs des Tages zeigen (Retro 2026-09-10, Gate parallel-session-pr-collision):
  # #3030/#3033 kollidierten acht Minuten auseinander, weil nichts vor dem Start
  # die offenen PRs des Zieltags anzeigte — check_pr_collision() oben blockt nur
  # bei exaktem Task-Slug-Treffer, nicht bei thematischer Überlappung. Advisory,
  # daher `|| true`: darf 'start' nie scheitern lassen (fail-open, s. Skript-Kopf).
  {
    echo ""
    echo "Offene PRs heute (Kollisionen vermeiden, Gate parallel-session-pr-collision):"
    ( cd "$repo" && python3 "$SCRIPT_DIR/repo_session_offene_prs.py" ${slug_repo_start:+--repo "$slug_repo_start"} ) 2>&1 || true
  } >&2
}

cmd_list() {
  [ -d "$LEASE_DIR" ] || { echo "keine Leases."; return 0; }
  local n=0
  for l in "$LEASE_DIR"/*.json; do
    [ -e "$l" ] || continue
    n=$((n+1))
    python3 - "$l" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(f"- {d['branch']:48} {d['worktree']}  (exp {d['expires_at']}, eph={d['ephemeral']})")
PY
  done
  echo "$n Lease(s)."
}

cmd_end() {
  local wt="${1:-}"; [ -n "$wt" ] || die "worktree-path fehlt"
  local repo; repo="$(git -C "$wt" rev-parse --path-format=absolute --git-common-dir 2>/dev/null | sed 's#/\.git$##')" || true
  # Dirty-Guard: nie einen Tree mit uncommitted changes entfernen
  if [ -n "$(git -C "$wt" status --porcelain 2>/dev/null)" ]; then
    die "Worktree $wt ist DIRTY — erst committen/pushen (Guard)."
  fi
  # Kanonischer Pfad fuer den Lease-Match (#1360): wt selbst kann bereits
  # kanonisch sein (git worktree list liefert kanonische Pfade), aber der im
  # Lease gespeicherte Pfad kann eine nicht-kanonische Variante enthalten
  # (z.B. ".../worktrees/./<sid>" aus einem "start ." vor diesem Fix). Vor
  # dem Entfernen auflösen, weil "$wt" danach nicht mehr existiert und
  # realpath dann fehlschlaegt.
  local wt_canon; wt_canon="$(realpath "$wt" 2>/dev/null || readlink -f "$wt" 2>/dev/null || printf '%s' "$wt")"
  git -C "$wt" worktree remove "$wt" 2>/dev/null || git worktree remove "$wt"
  # Lease schliessen — Pfade auf beiden Seiten kanonisieren statt exaktem
  # String-Vergleich (#1360 Defekt 2): der im Lease gespeicherte Pfad kann
  # z.B. "/./" enthalten (Defekt 1, vor diesem Fix geschriebene Leases) und
  # traf den bisherigen "grep -q" nie, ohne dass das sichtbar wurde.
  local closed=0
  for l in "$LEASE_DIR"/*.json; do
    [ -e "$l" ] || continue
    local lease_wt lease_wt_canon
    lease_wt="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('worktree',''))" "$l" 2>/dev/null)" || continue
    [ -n "$lease_wt" ] || continue
    # realpath auf einen bereits entfernten Pfad schlaegt fehl -> textuell normalisieren (Doppel-Slash, "/./" raus) als Fallback.
    lease_wt_canon="$(realpath -m "$lease_wt" 2>/dev/null || readlink -f "$lease_wt" 2>/dev/null || printf '%s' "$lease_wt")"
    if [ "$lease_wt_canon" = "$wt_canon" ]; then
      mv "$l" "$l.closed" && echo "Lease geschlossen: $l.closed"
      befund_freigeben "$(basename "$l" .json)"
      closed=$((closed+1))
    fi
  done
  if [ "$closed" -eq 0 ]; then
    echo "⚠ Kein Lease geschlossen — kein Lease unter $LEASE_DIR passt auf Worktree-Pfad: $wt_canon" >&2
    echo "  Der Worktree ist bereits entfernt. Pruefe 'repo-session.sh list' und schliesse den passenden Lease manuell (mv <lease>.json <lease>.json.closed)." >&2
  fi
  echo "Worktree entfernt: $wt (Branch bleibt erhalten)"
}

# ---------------------------------------------------------------------------
# abstand — wie weit ist jede offene Lease hinter origin/main
#
# **Warum das eine eigene Schranke braucht.** Ein Branch, der lange liegt,
# kollidiert beim Merge — unabhaengig davon, ob eine FREMDE Sitzung ihn
# ueberholt hat oder die eigene. Gemessen am 2026-08-04: der einzige echte
# Konflikt des Tages entstand, weil ein Branch vier Stunden lag, waehrend main
# um zwoelf Commits weiterlief — beide Seiten von derselben Sitzung. Die
# Sichtbarkeit von Parallelsitzungen haette das nicht verhindert; der Abstand
# schon.
#
# Die Zahl steht bereits in der Lease (`base_sha`) und muss nur gerechnet werden.
# Exit 1, wenn eine Lease die Schwelle reisst — damit ein Aufrufer daran
# scheitern kann, statt es zu ueberlesen.
# ---------------------------------------------------------------------------
ABSTAND_SCHWELLE="${REPO_SESSION_ABSTAND_MAX:-25}"

cmd_abstand() {
  local nur_repo="${1:-}" ueber=0 gesamt=0 abgelaufen=0 jetzt
  [ -d "$LEASE_DIR" ] || { echo "keine Leases."; return 0; }
  jetzt="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for l in "$LEASE_DIR"/*.json; do
    [ -e "$l" ] || continue
    local repo branch base_sha pfad n expires_at
    repo="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('repo',''))" "$l" 2>/dev/null)" || continue
    [ -n "$repo" ] || continue
    [ -z "$nur_repo" ] || [ "$repo" = "$nur_repo" ] || continue
    # Abgelaufene Leases zaehlen nicht: niemand arbeitet in dem Worktree, also
    # steht auch kein Merge bevor, vor dem der Abstand warnen koennte. Der
    # Sitzungsstart meldete 18 solcher Leichen (aelteste 156 Commits hinter main,
    # Lease seit August abgelaufen) 129 Laeufe lang als "vor weiterer Arbeit
    # mergen" — ein Rat ohne Adressaten. Wer den Worktree wieder aufnimmt, holt
    # sich mit `start` eine frische Lease, und ab dann zaehlt er wieder. Liegen-
    # gebliebene Worktrees sind Sache des Hygiene-Melders und des Reapers.
    expires_at="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('expires_at',''))" "$l" 2>/dev/null)"
    if [ -n "$expires_at" ] && [[ "$expires_at" < "$jetzt" ]]; then
      abgelaufen=$((abgelaufen + 1))
      continue
    fi
    branch="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('branch',''))" "$l" 2>/dev/null)"
    base_sha="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('base_sha',''))" "$l" 2>/dev/null)"
    pfad="${GITHUB_DIR:-$HOME/github}/$repo"
    [ -d "$pfad" ] || continue
    [ -n "$base_sha" ] || continue
    n="$(git -C "$pfad" rev-list --count "$base_sha..origin/main" 2>/dev/null)" || continue
    gesamt=$((gesamt + 1))
    if [ "$n" -gt "$ABSTAND_SCHWELLE" ]; then
      ueber=$((ueber + 1))
      printf '  ⚠ %-14s %-40s %5s Commits hinter main\n' "$repo" "${branch##*/}" "$n"
    fi
  done
  local zusatz=""
  [ "$abgelaufen" -gt 0 ] && zusatz=" — $abgelaufen abgelaufene Lease(s) nicht gezaehlt (Hygiene-Melder/Reaper)"
  if [ "$ueber" -gt 0 ]; then
    echo "$ueber von $gesamt Lease(s) ueber der Schwelle ($ABSTAND_SCHWELLE)$zusatz."
    echo "Vor weiterer Arbeit im betroffenen Worktree: git merge origin/main"
    return 1
  fi
  echo "$gesamt Lease(s), keine ueber der Schwelle ($ABSTAND_SCHWELLE)$zusatz."
  return 0
}

# Nur bei DIREKTEM Aufruf dispatchen, nicht bei `source repo-session.sh` (#3495 V1
# Folgepunkt c): ein Test kann so Funktionen wie befund_belegen() isoliert aufrufen,
# ohne cmd_start()/reap_repo() zu durchlaufen — insbesondere ohne den Auto-Reap, der
# beim echten `start` abgelaufene Befund-Sperren meist schon VOR befund_belegen()
# raeumt und den Uebernahme-Zweig darin (Zeile "abgelaufen|verwaist) ... rm -f") so
# nur indirekt trifft.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  case "${1:-}" in
    start) shift; cmd_start "$@";;
    abstand) shift; cmd_abstand "${1:-}";;
    list)  cmd_list;;
    befunde) cmd_befunde;;
    end)   shift; cmd_end "$@";;
    reap)  shift; cmd_reap "$@";;
    -h|--help|help) echo "usage: repo-session.sh {start <repo> --task <slug> [--ziel <text>] [--base <ref>] [--ephemeral] [--befund <phase::repo>]... | list | befunde | abstand [<repo>] | end <wt> | reap [<repo>|--alle]}"; exit 0;;
    *) echo "usage: repo-session.sh {start <repo> --task <slug> [--ziel <text>] [--base <ref>] [--ephemeral] [--befund <phase::repo>]... | list | befunde | abstand [<repo>] | end <wt> | reap [<repo>|--alle]}" >&2; exit 2;;
  esac
fi
