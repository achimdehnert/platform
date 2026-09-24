#!/usr/bin/env bash
# session_start_checks.sh — deterministischer Runner für die mechanischen
# /session-start-Phasen (0.0–0.9 ohne 0.4.3/0.8 — die sind Judgment-Phasen und
# bleiben im Skill-Text).
#
# Motiv (Ausführungstreue-Programm, platform#1167 + Retro c494a2): ein langes
# Multi-Phasen-Dokument wird beim Ausführen überflogen — einzelne Phasen sind
# strukturell überspringbar. Dieser Runner macht Skip unmöglich: EIN Aufruf
# führt ALLE mechanischen Phasen aus und endet mit einer Checklisten-Tabelle.
#
# Aufruf:  session_start_checks.sh [TARGET_REPO]   (Default: platform)
# Exit 0 = kein FAIL · Exit 1 = mind. 1 FAIL (pgvector-Tunnel ist der einzige
# Hard-FAIL laut Skill; alles andere degradiert zu WARN, Session darf weiter).
#
# Kein set -e: einzelne Phasen dürfen scheitern, der Runner läuft immer bis zur
# Summary durch (und ein `echo` als letzter Befehl in einer if-Funktion würde
# unter set -e Exit-Codes verschlucken — bekannte Drift-Klasse).
set -u

export GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
# Ueberschreibbar, damit eine Aenderung an den Werkzeugen VOR dem Merge
# pruefbar ist: sonst ruft der Lauf immer den Haupt-Tree und testet die
# alte Fassung. Genau daran scheiterte der erste Test von 0.4.4.
PLATFORM_DIR="${PLATFORM_DIR:-$GITHUB_DIR/platform}"
TARGET_REPO="${1:-platform}"
# Repo, dem die plattformweiten Phasen GEHOEREN (Default des 4. record-Arguments).
# Literal, NICHT `basename "$PLATFORM_DIR"`: $PLATFORM_DIR ist ueberschreibbar,
# damit eine Aenderung vor dem Merge pruefbar ist — der Basisname waere dann der
# Worktree-Name. Genau daran scheiterte der erste Testlauf dieser Zeile am
# 2026-08-23: 20 Phasen standen unter "2026-08-23-achim-dehnert-gate-...-122530".
# Der Name des Repos steht ohnehin schon als Literal in TARGET_REPO's Default.
PLATTFORM_REPO="platform"
PROD_HOST="88.198.191.108"
STAGING_HOST="88.99.38.75"

declare -a P_NAME P_STATUS P_NOTE P_REPO P_UNGEPRUEFT P_DAUER
FAILED=0

# ── Laufzeit-Messung (platform#3373) ────────────────────────────────────────
# Jede Phase bekommt ihre Wanduhr-Zeit, ohne dass irgendwo ein Zeitstempel von
# Hand gesetzt werden muss: `record` misst den Abstand zum vorigen `record`.
# Motiv: ohne Messung ist "der Runner ist langsam" eine Meinung, und optimiert
# wird dann die Phase, die am lautesten aussieht, nicht die, die die Zeit
# frisst. Die Zahl bleibt dauerhaft im Lauf (Regressionswache), nicht nur fuer
# die eine Messung — ohne sie faellt eine neue teure Phase erst auf, wenn
# jemand den Start subjektiv "zaeh" findet.
# EPOCHREALTIME haengt an der Locale (de_DE liefert Komma); ohne das Ersetzen
# rechnet awk mit abgeschnittenen Sekunden weiter.
_uhr() { local s="${EPOCHREALTIME:-$(date +%s).0}"; printf '%s' "${s/,/.}"; }
_spanne() { awk -v a="$1" -v b="$2" 'BEGIN{printf "%.1f", b-a}'; }
T_START="$(_uhr)"; T_LETZT="$T_START"

# record <phase> <PASS|WARN|FAIL> <note> [ziel-repos] [ungeprueft-repos]
#   Pipes raus, sonst bricht die Summary-Tabelle.
#   Das 4. Argument nennt die Repos, um die es in dieser Zeile GEHT — nicht das
#   Repo, in dem die Sitzung laeuft. Ohne Angabe ist es $PLATTFORM_REPO, denn die
#   meisten Phasen messen platform-eigene Daten (Gate-Registry, Schleuse, Leases,
#   Cron-Melder, ports.yaml); die vier Phasen, die wirklich das Sitzungs-Repo
#   pruefen, geben "$TARGET_REPO" ausdruecklich an.
#
#   Der Default war bis 2026-08-23 $TARGET_REPO, und das war die teurere Fehl-
#   richtung: der Fingerabdruck im Befund-Journal lautet `phase::repo`, also
#   wanderte ein plattformweiter Befund mit jeder Sitzung in einen anderen Eimer.
#   Die naechste Sitzung mit anderem Ziel HEILTE den Eintrag der vorigen und legte
#   ihn neu an — ewig jung. Gemessen am 2026-08-23: der Gate-Wirkung-Befund (`tools/gate_wirkung.py`, damals als Phase 0.7.7 gefuehrt) stand mit
#   `laeufe=1, erstmals=2026-08-23` im Journal, obwohl das Gate seit dem 2026-08-20
#   rueckfaellig ist; sieben weitere plattformweite Phasen lagen unter `writing-hub`.
#   Genau das Alter (K3) war damit zerstoert, fuer das das Journal existiert.
#   Ein vergessenes 4. Argument ist jetzt hoechstens ein falsches, aber STABILES
#   Etikett — vorher war es ein wanderndes.
#
#   Diese Unterscheidung fehlte
#   bis 2026-08-16 (platform#2004): ein roter Deploy in `cad-hub` war eine WARN-Zeile
#   in einer platform-Sitzung, und der Befund blieb dort liegen — fuenf offene
#   `[deploy-health]`-Issues, alle in platform, alle ueber andere Repos, keins gefixt.
#
#   Das 5. Argument nennt Repos, die diese Phase NICHT beurteilen konnte. Ohne das
#   sieht eine Abdeckungsluecke im Journal aus wie eine Heilung: `trading-hub` ist
#   fuer 0.7 regelmaessig nicht abfragbar — der Befund waere jedes Mal still
#   verschwunden und beim naechsten erfolgreichen Scan als neu wieder aufgetaucht,
#   ewig jung. Der teuerste Fehler, den ein Melder-Gedaechtnis machen kann.
# ── Melder-Register: Herabstufungsdatei aus dem VORIGEN Lauf lesen (#2690 K3) ──
# Phase 0.7.19 misst die Trefferquote SPAET im Lauf und Phase 0.7.23 (weiter
# unten) schreibt `melder-herabgestuft.tsv` erst danach — die Datei, die HIER
# gelesen wird, ist also immer der Stand des VORIGEN Laufs, nie des laufenden.
# Das ist gewollt: ein Melder, der GERADE jetzt unter die Schwelle faellt, bleibt
# fuer genau einen Lauf noch WARN-laut; erst ab dem naechsten Lauf wird er leiser
# (HINWEIS). Alles andere waere ein Melder, der sich selbst herabstuft, bevor die
# Herabstufung ueberhaupt geschrieben ist — ein zirkulaerer Lauf in einer Zeile.
declare -A MELDER_HERABGESTUFT
HERABSTUFUNG_DATEI="${MELDER_HERABSTUFUNG_DATEI:-$HOME/.claude/hooks/state/melder-herabgestuft.tsv}"
if [ -f "$HERABSTUFUNG_DATEI" ]; then
  while IFS=$'\t' read -r hphase hquote hlaeufe _hdatum; do
    [ -z "$hphase" ] && continue
    MELDER_HERABGESTUFT["$hphase"]="${hquote}|${hlaeufe}"
  done < "$HERABSTUFUNG_DATEI"
fi

record() {
  local phase="$1" status="$2" note="$3"
  # Ein herabgestufter Melder (governance/melder-register.yaml, Trefferquote
  # < praezision_min über >= mindest_laeufe Läufe) wird gelesen, aber nicht als
  # WARN ins Board gezwungen — solange die Trefferquote unter der Schwelle
  # liegt, ist der Melder selbst der Befund, nicht jede einzelne seiner Zeilen.
  if [ "$status" = "WARN" ] && [ -n "${MELDER_HERABGESTUFT[$phase]:-}" ]; then
    local hq="${MELDER_HERABGESTUFT[$phase]%%|*}" hl="${MELDER_HERABGESTUFT[$phase]##*|}"
    local hq_pct; hq_pct=$(awk -v q="$hq" 'BEGIN{printf "%.0f", q*100}' 2>/dev/null || echo "?")
    status="HINWEIS"
    note="(herabgestuft: Trefferquote ${hq_pct} % über ${hl} Läufe) ${note}"
  fi
  P_NAME+=("$phase"); P_STATUS+=("$status"); P_NOTE+=("$(echo "$note" | tr '|' '/')")
  P_REPO+=("${4:-$PLATTFORM_REPO}")
  P_UNGEPRUEFT+=("${5:-}")
  local _jetzt; _jetzt="$(_uhr)"
  P_DAUER+=("$(_spanne "$T_LETZT" "$_jetzt")")
  T_LETZT="$_jetzt"
  [ "$status" = "FAIL" ] && FAILED=1
  printf '  [%s] %s — %s\n' "$status" "$phase" "$note"
}

# ── Vorlauf: teure Melder nebenlaeufig starten, in Phasen-Reihenfolge ernten ──
# Fast alle Melder ab 0.4.2 sind reine Leser, die auf Netz warten (gh-API, ssh,
# TLS-Handshakes, HTTP). Nacheinander ausgefuehrt addiert sich diese Wartezeit,
# obwohl keiner auf das Ergebnis eines anderen wartet. `vorlauf` startet sie in
# einem Rutsch, `ernte` holt das Ergebnis an genau der Stelle ab, an der die
# Phase ohnehin stand: Reihenfolge der Summary, Wortlaut der Notizen und die
# record-Aufrufe bleiben unveraendert — nur die Wartezeit laeuft jetzt
# uebereinander statt hintereinander.
#
# Sequenziell bleiben zwei Gruppen, und zwar aus demselben Grund: dort bewegt
# jemand Dateien, und ein Leser, der nebenher misst, saehe Zwischenstaende —
# ein Melder, der sich selbst belaugt.
#   * alles vor 0.4.2 — 0.2/0.4/0.4.1 ziehen `git pull`, 0.4.5 raeumt Worktrees
#     ab, 0.5 startet den Tunnel. Damit bleibt ein Boden von rund 62 s; ob der
#     teuerste Posten darin (0.4.5, 25 s) diesen Schutz wert ist, entscheidet
#     der Owner — Refs #3379.
#   * die Selbstheilungen in 0.7.5/0.7.13 und der Schreibschritt in 0.7.19 —
#     nur die VORmessung wird vorgezogen, geheilt und nachgemessen wird
#     weiterhin sequenziell an Ort und Stelle.
#
# SESSION_CHECKS_PARALLEL=1 schaltet den Vorlauf ab: `ernte` fuehrt den Befehl
# dann an seiner Phasenstelle aus, also exakt im alten Ablauf. Das ist der
# Vergleichsmassstab fuer die Laufzeitmessung — gleicher Code, ein Schalter.
VORLAUF_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ssc-vorlauf.XXXXXX")"
# Ohne die Fehlerstroeme der Auftraege ist ein Melder, der im Vorlauf anders
# ausfaellt als einzeln aufgerufen, nicht diagnostizierbar — und genau das kam
# beim Bau zweimal vor. Mit SESSION_CHECKS_VORLAUF_BEHALTEN=1 bleibt das
# Verzeichnis (je Auftrag .out/.err/.rc) stehen.
if [ -n "${SESSION_CHECKS_VORLAUF_BEHALTEN:-}" ]; then
  echo "hinweis: Vorlauf-Ausgaben bleiben in $VORLAUF_DIR" >&2
else
  trap 'rm -rf "$VORLAUF_DIR"' EXIT
fi
VORLAUF_MAX="${SESSION_CHECKS_PARALLEL:-8}"
# Zweite, viel engere Spur fuer alles, was `ssh` zu den Prod-Hosts oeffnet
# (neun Werkzeuge, per grep bestimmt, nicht geschaetzt). Grund, gemessen am
# 2026-09-22 im ersten Vorlauf-Lauf: bei einer einzigen Spur mit 8 Auftraegen
# meldete 0.7.12 "Melder nicht auswertbar" und 0.7.18 "Melder nicht gelaufen",
# 0.7.1/0.7.1b brachen mit einem Dekodierfehler ab — sshd nimmt nur eine
# begrenzte Zahl gleichzeitiger Anmeldungen an (MaxStartups) und wirft darueber
# hinaus zufaellig ab. Jedes dieser Werkzeuge oeffnet mehrere Verbindungen, acht
# davon nebeneinander sind schnell zwanzig.
#
# Ein Melder, der unter Last leiser wird, ist genau die Regression, die eine
# Laufzeit-Optimierung nicht haben darf: die Zeile bleibt gelb, der Inhalt
# verschwindet. Deshalb ist diese Spur bewusst schmal — sie kostet Sekunden und
# rettet die Aussage.
VORLAUF_MAX_SSH="${SESSION_CHECKS_PARALLEL_SSH:-3}"
# Dritte Spur, Breite 1: Werkzeuge, die `git fetch` in $PLATFORM_DIR ausfuehren
# (`cc-skill-dist/doctor.py` je Lane, `sichtbarkeits_drift_melder.py`). Zwei
# gleichzeitige Fetches im selben Repo streiten um dieselbe Ref-Sperre; gemessen
# am 2026-09-22: 0.7.13 meldete `commands:UNGEPRUEFT`, weil ein Fetch der drei
# parallelen Doctor-Laeufe abbrach und das Werkzeug ohne DRIFT-SCORE endete.
# Sequenziell ist hier billiger als jede Abwaegung — der Fetch dauert nach dem
# Pull aus 0.2 ohnehin Bruchteile einer Sekunde.
VORLAUF_MAX_GIT="${SESSION_CHECKS_PARALLEL_GIT:-1}"
declare -A VORLAUF_PID VORLAUF_CMD VORLAUF_MERGE
declare -A SPUR_MAX=( [frei]="$VORLAUF_MAX" [ssh]="$VORLAUF_MAX_SSH" [git]="$VORLAUF_MAX_GIT" )
# shellcheck disable=SC2034  # ueber `local -n q="Q_$spur"` benutzt, das shellcheck nicht aufloest
declare -a Q_frei=() Q_ssh=() Q_git=()
ERNTE_RC=0

# Warteschlange statt Drossel am Startpunkt. Ein erster Entwurf liess `vorlauf`
# blockieren, solange die Spur voll war — mit dem Ergebnis, dass die schmale
# ssh-Spur (3 Plaetze, 9 Auftraege) den Start ALLER anderen Auftraege aufhielt:
# gemessen am 2026-09-22 lief 0.7.4 danach immer noch seine vollen 33,5 s allein,
# weil es erst startete, als die ssh-Spur fast durch war (157 s gesamt).
# Jetzt sammeln die `vorlauf*`-Funktionen nur ein; `_vorlauf_loslegen` startet je
# Spur so viele Arbeiter, wie sie breit ist, und jeder Arbeiter geht seine
# Auftraege der Reihe nach durch. Der Hauptlauf blockiert dabei nie.
_auftrag_ausfuehren() { # _auftrag_ausfuehren <merge 0|1> <schluessel> <befehl...>
  local merge="$1" key="$2"; shift 2
  # `</dev/null`: ein Hintergrund-Auftrag darf nicht an derselben
  # Standardeingabe haengen wie alle anderen — `ssh` liest von dort.
  if [ "$merge" = 1 ]; then
    "$@" </dev/null >"$VORLAUF_DIR/$key.out" 2>&1
  else
    "$@" </dev/null >"$VORLAUF_DIR/$key.out" 2>"$VORLAUF_DIR/$key.err"
  fi
  echo $? >"$VORLAUF_DIR/$key.rc"
}

_spur_starten() { # _spur_starten <spur>
  # Zwei `local`-Zeilen, nicht eine: in `local a="$1" b="${M[$a]}"` wertet bash
  # den Index aus, bevor `a` gesetzt ist — unter `set -u` bricht die Funktion
  # dann mit "a ist nicht gesetzt" ab.
  local spur="$1"
  local max="${SPUR_MAX[$spur]}"
  # shellcheck disable=SC2178  # Nameref auf ein Array; shellcheck sieht nur die Zuweisung
  local -n q="Q_$spur"
  local n=${#q[@]} i w pid k
  [ "$n" -eq 0 ] && return 0
  [ "$max" -gt "$n" ] && max="$n"
  for (( w = 0; w < max; w++ )); do
    (
      for (( i = w; i < n; i += max )); do
        eval "_auftrag_ausfuehren ${q[$i]}"
      done
    ) &
    pid=$!
    # Reihum verteilt, und die Warteschlange steht nach erwarteten Kosten —
    # so faengt jeder Arbeiter mit einem der teuersten Auftraege an.
    # Der Schluessel ist das zweite Feld; alle Schluessel hier sind schlichte
    # Woerter aus [a-z0-9:-], `printf %q` laesst sie unveraendert.
    for (( i = w; i < n; i += max )); do
      read -r _ k _ <<<"${q[$i]}"
      VORLAUF_PID["$k"]=$pid
    done
  done
  q=()   # geleert, damit ein spaeterer Nachschub nicht noch einmal startet
  return 0
}

_vorlauf_loslegen() { # schmale Spuren zuerst — sie bestimmen die Gesamtdauer
  [ "$VORLAUF_MAX" -le 1 ] && return 0
  _spur_starten ssh
  _spur_starten git
  _spur_starten frei
}

# `merge=1` entspricht dem `2>&1` der urspruenglichen Phase: wer beide Stroeme
# gelesen hat, liest sie weiterhin beide — und zwar in der Reihenfolge, in der
# sie entstanden sind. Zwei getrennte Dateien hintereinander auszugeben waere
# nicht dasselbe, sobald `tail -1` darauf zugreift.
_vorlauf_start() { # _vorlauf_start <merge 0|1> <spur frei|ssh|git> <schluessel> <befehl...>
  local merge="$1" spur="$2" key="$3"; shift 3
  if [ "$VORLAUF_MAX" -le 1 ]; then
    # printf %q + eval: die Argumente ueberleben die Zwischenlagerung in einer
    # assoziativen Variable unveraendert (bash kann keine Arrays in Arrays).
    VORLAUF_CMD["$key"]="$(printf '%q ' "$@")"
    VORLAUF_MERGE["$key"]="$merge"
    return 0
  fi
  # shellcheck disable=SC2178  # Nameref auf ein Array; shellcheck sieht nur die Zuweisung
  local -n q="Q_$spur"
  q+=("$(printf '%q ' "$merge" "$key" "$@")")
  return 0
}
vorlauf()      { _vorlauf_start 0 frei "$@"; }  # Phase las mit 2>/dev/null
vorlauf2()     { _vorlauf_start 1 frei "$@"; }  # Phase las mit 2>&1
vorlauf_ssh()  { _vorlauf_start 0 ssh  "$@"; }  # Werkzeug oeffnet ssh zu Prod
vorlauf2_ssh() { _vorlauf_start 1 ssh  "$@"; }
vorlauf_git()  { _vorlauf_start 0 git  "$@"; }  # Werkzeug macht `git fetch` in $PLATFORM_DIR

# Zwei Funktionen statt einer, weil `VAR=$(ernte k)` in einer Subshell laeuft:
# ein dort gesetztes ERNTE_RC kaeme nie in der aufrufenden Shell an. Phasen, die
# den Exit-Code brauchen (0.7.21, 0.7.28), rufen erst `warte_auf`, dann `ernte`.
warte_auf() { # warte_auf <schluessel> — blockiert bis fertig, setzt ERNTE_RC
  local key="$1"
  if [ -n "${VORLAUF_CMD[$key]:-}" ]; then
    if [ "${VORLAUF_MERGE[$key]:-0}" = 1 ]; then
      ( eval "${VORLAUF_CMD[$key]}" >"$VORLAUF_DIR/$key.out" 2>&1 )
    else
      ( eval "${VORLAUF_CMD[$key]}" >"$VORLAUF_DIR/$key.out" 2>"$VORLAUF_DIR/$key.err" )
    fi
    echo $? >"$VORLAUF_DIR/$key.rc"
    unset "VORLAUF_CMD[$key]"   # ein zweiter Aufruf darf nicht erneut ausfuehren
  elif [ -n "${VORLAUF_PID[$key]:-}" ]; then
    local p="${VORLAUF_PID[$key]}"
    wait "$p" 2>/dev/null
    # `wait` allein genuegt NICHT: die meisten Phasen ernten als `VAR=$(ernte k)`,
    # und in dieser Kommandosubstitution ist der Auftrag kein eigenes Kind — `wait`
    # kehrt dort sofort zurueck, ohne gewartet zu haben. Die Phase las dann die
    # noch leere Ausgabe und meldete "Melder nicht gelaufen", waehrend das Werkzeug
    # daneben weiterlief und Sekunden spaeter sein Ergebnis hinschrieb. Gemessen am
    # 2026-09-22 an 0.7.4 und 0.7.27; die rc-Datei traegt die Uhrzeit NACH dem Ende
    # des Runners. Deshalb zusaetzlich auf die rc-Datei warten — die schreibt der
    # Auftrag als Letztes, und sie ist von jeder Shell aus sichtbar.
    while [ ! -s "$VORLAUF_DIR/$key.rc" ]; do
      kill -0 "$p" 2>/dev/null || { sleep 0.1; break; }
      sleep 0.1
    done
  fi
  ERNTE_RC="$(cat "$VORLAUF_DIR/$key.rc" 2>/dev/null || echo 1)"
}

ernte() { # ernte <schluessel> — wartet und gibt stdout aus
  warte_auf "$1"
  cat "$VORLAUF_DIR/$1.out" 2>/dev/null
}

echo "┌─ session-start Runner · $(date '+%Y-%m-%d %H:%M') · target=$TARGET_REPO ─┐"

# ── 0.0 GITHUB_DIR + Version-Banner ─────────────────────────────────────────
if ! grep -q "GITHUB_DIR" ~/.bashrc 2>/dev/null; then
  {
    echo ""
    echo "# Platform: Repo-Basisverzeichnis (Single Source of Truth)"
    echo "export GITHUB_DIR=\"\$HOME/github\""
  } >> ~/.bashrc
fi
VERSION_BEFORE=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT_BEFORE=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
record "0.0 env+banner" "PASS" "Platform v${VERSION_BEFORE} (${COMMIT_BEFORE}), shell-alive-$(date +%s)"

# ── 0.1 Server-Erreichbarkeit (TCP-Probe, NIE ping — Hetzner blockt ICMP) ───
if python3 "$PLATFORM_DIR/infra/scripts/server_probe.py" --host "$PROD_HOST" >/tmp/ssc_probe.$$ 2>&1; then
  record "0.1 server-probe" "PASS" "$(grep -o 'Ergebnis:.*' /tmp/ssc_probe.$$ | head -1)"
else
  record "0.1 server-probe" "WARN" "Probe fehlgeschlagen — MCP/SSH-Calls können hängen (Log: server_probe direkt ausführen)"
fi
rm -f /tmp/ssc_probe.$$

# ── 0.2 Platform Sync Loop: GitHub → lokal → alle Repos ─────────────────────
if git -C "$PLATFORM_DIR" pull --rebase --quiet 2>/dev/null; then
  # Symlinks und project-facts haengen beide nur am frisch gezogenen Stand, nicht
  # aneinander — sie schreiben in verschiedene Dateien und laufen deshalb
  # nebeneinander (platform#3373).
  SYNC_TMP="$(mktemp -d "${TMPDIR:-/tmp}/ssc-sync.XXXXXX")"
  bash "$PLATFORM_DIR/scripts/sync-workflows.sh" >"$SYNC_TMP/links" 2>&1 &
  SYNC_PID=$!
  python3 "$PLATFORM_DIR/scripts/gen_project_facts.py" >"$SYNC_TMP/facts" 2>&1 &
  FACTS_PID=$!
  wait "$SYNC_PID" 2>/dev/null; wait "$FACTS_PID" 2>/dev/null
  LINKS=$(grep -cE "LINK|REPLACE" "$SYNC_TMP/links")
  FACTS=$(grep -cE "✅|⚠️|SKIP" "$SYNC_TMP/facts")
  rm -rf "$SYNC_TMP"
  VERSION_AFTER=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
  COMMIT_AFTER=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
  if [ "$COMMIT_BEFORE" != "$COMMIT_AFTER" ] || [ "$VERSION_BEFORE" != "$VERSION_AFTER" ]; then
    record "0.2 platform-sync" "PASS" "v${VERSION_BEFORE}→v${VERSION_AFTER} (${COMMIT_BEFORE}→${COMMIT_AFTER}), ${LINKS} Symlinks, ${FACTS} project-facts"
  else
    record "0.2 platform-sync" "PASS" "bereits aktuell v${VERSION_AFTER} (${COMMIT_AFTER}), ${LINKS} Symlinks, ${FACTS} project-facts"
  fi
else
  record "0.2 platform-sync" "WARN" "platform-Pull fehlgeschlagen (dirty/Netz?) — Sync Loop unvollständig"
fi

# ── 0.3 Modellwechsel: bewertet ↔ läuft (K2 platform#2690) ──────────────────
# Maßstab ist "assessed_with (Policies) ↔ neu (model-changes.log)", nicht
# Vorgänger↔Nachfolger — siehe tools/modellwechsel_check.py Kopf-Docstring.
MW_KURZ="$(python3 "$PLATFORM_DIR/tools/modellwechsel_check.py" --kurz 2>&1)"
MW_RC=$?
if [ "$MW_RC" -eq 0 ]; then
  record "0.3 modellwechsel" "PASS" "$MW_KURZ"
else
  SMOKE_OUT="$(cd "$PLATFORM_DIR" && python3 -m pytest tools/tests/test_retro_kpis.py tools/claude-hooks/tests/ -q 2>&1)"
  SMOKE_RC=$?
  SMOKE_SUMMARY="$(echo "$SMOKE_OUT" | tail -1)"
  (cd "$PLATFORM_DIR" && python3 tools/gate_drill_check.py) >/dev/null 2>&1
  DRILL_RC=$?
  if [ "$SMOKE_RC" -eq 0 ] && [ "$DRILL_RC" -eq 0 ]; then
    python3 "$PLATFORM_DIR/tools/modellwechsel_check.py" --behandelt >/dev/null 2>&1
    record "0.3 modellwechsel" "WARN" "${MW_KURZ} — Smoke: ${SMOKE_SUMMARY} — Drill grün — behandelt markiert"
  else
    record "0.3 modellwechsel" "WARN" "${MW_KURZ} — Smoke: ${SMOKE_SUMMARY} (rc=${SMOKE_RC}) — Drill rc=${DRILL_RC} — NICHT behandelt markiert, bleibt fällig"
  fi
fi

# ── 0.4 Parallel-Session-Guard + Target/Kern-Repos syncen ───────────────────
GUARD_NOTE=""
sync_repo() { # sync_repo <pfad> — pullt nur, wenn kein Guard greift; meldet Grund
  local dir="$1" name; name=$(basename "$1")
  local br; br=$(git -C "$dir" branch --show-current 2>/dev/null)
  if [ -n "$br" ] && [ "$br" != "main" ]; then
    echo "$name:GUARD(branch=$br)"; return
  fi
  if ! git -C "$dir" diff --quiet HEAD 2>/dev/null; then
    # Tracked-Änderungen: NICHT stashen (fremde Session?) — Skill-Guard 0.4
    echo "$name:GUARD(dirty)"; return
  fi
  if git -C "$dir" pull --rebase --quiet 2>/dev/null; then
    echo "$name:ok"
  else
    echo "$name:pull-fail"
  fi
}
FOREIGN_WT=$(git -C "$PLATFORM_DIR" worktree list 2>/dev/null | grep -c "session/$(date +%Y-%m-%d)")
[ "$FOREIGN_WT" -gt 0 ] && GUARD_NOTE="${FOREIGN_WT} Session-Worktree(s) heute aktiv · "

# C1 (2026-07-20): WER arbeitet gerade parallel — nicht nur WIE VIELE.
# Der Worktree-Zähler oben sagt "3 Worktrees", beantwortet aber nicht die Frage,
# die beim Start einer zweiten Session zählt: welches Thema hält die andere
# Session? Die Leases (ADR-233 §2.4) enthalten das längst, wurden nur nie gezeigt.
# Reine Sichtbarkeit, kein Lock — blockiert nichts, entscheidet nichts.
PARALLEL_SESSIONS=$(python3 "$PLATFORM_DIR/tools/session-leases" \
  --repo "$TARGET_REPO" --brief 2>/dev/null)
SYNC_RESULTS=""
SYNC_GEPRUEFT=""
for repo in "$TARGET_REPO" mcp-hub risk-hub; do
  [ -d "$GITHUB_DIR/$repo" ] || continue
  SYNC_RESULTS="$SYNC_RESULTS $(sync_repo "$GITHUB_DIR/$repo")"
  SYNC_GEPRUEFT="$SYNC_GEPRUEFT$repo "
done
if echo "$SYNC_RESULTS" | grep -q "GUARD\|pull-fail"; then
  # Nur die Repos, die tatsaechlich GUARD/pull-fail tragen — nicht die geprueften.
  SYNC_BETROFFEN=$(echo "$SYNC_RESULTS" | tr ' ' '\n' \
    | grep -E "GUARD|pull-fail" | cut -d: -f1 | sort -u | tr '\n' ' ')
  record "0.4 repo-sync" "WARN" "${GUARD_NOTE}${SYNC_RESULTS# } (GUARD = nicht angefasst, fremde Session möglich)" "${SYNC_BETROFFEN% }"
else
  # Auch der Gruen-Fall nennt die geprueften Repos: der Default ist `platform`,
  # und diese Phase synct TARGET_REPO + mcp-hub + risk-hub (Retro a84f71 #1 —
  # der Default-Flip war nur an den WARN-Zweigen nachgezogen worden).
  record "0.4 repo-sync" "PASS" "${GUARD_NOTE}${SYNC_RESULTS# }" "${SYNC_GEPRUEFT% }"
fi

# Parallele Sessions sind in Querschnitt-Repos (platform, dev-hub, mcp-hub)
# der Normalfall und kein Befund (#1944 K8): jede Session arbeitet in ihrem
# eigenen Worktree und braucht keinen Abgleich mit den anderen. Die Zahl bleibt
# sichtbar, die Liste nicht — sie hatte keinen Leser, der etwas damit tat.
if [ -n "$PARALLEL_SESSIONS" ]; then
  n=$(printf '%s\n' "$PARALLEL_SESSIONS" | grep -c .)
  record "0.4 parallel-sessions" "PASS" "$n weitere Session(s) auf $TARGET_REPO — Normalfall, kein Befund (#1944 K8)" "$TARGET_REPO"
else
  record "0.4 parallel-sessions" "PASS" "keine andere aktive Session auf $TARGET_REPO" "$TARGET_REPO"
fi

# ── 0.4.4 Basis-Abstand der offenen Leases ─────────────────────────────────
# Die Sichtbarkeit von Parallelsitzungen (0.4) beantwortet "wer arbeitet noch",
# nicht "welcher Branch kollidiert beim Merge". Gemessen am 2026-08-04: der
# einzige echte Konflikt des Tages entstand, weil ein Branch vier Stunden lag,
# waehrend main um zwoelf Commits weiterlief — BEIDE Seiten von derselben
# Sitzung. Kein Parallel-Check haette das gefangen; der Abstand schon.
ABSTAND_OUT="$(bash "$PLATFORM_DIR/tools/repo-session.sh" abstand 2>/dev/null)" && ABSTAND_RC=0 || ABSTAND_RC=$?
ABSTAND_ZEILE="$(printf '%s\n' "$ABSTAND_OUT" | tail -3 | head -1)"
ABSTAND_N="$(printf '%s\n' "$ABSTAND_OUT" | grep -c '^  ⚠' || true)"
# Bewusst OHNE Repo-Aufschluesselung, obwohl die ⚠-Zeilen sie hergaeben (Feld 2,
# gemessen: 12 Repos): die Note ist eine Summe ("57 Lease(s) ueber der Schwelle"),
# und 12 wandernde Journal-Eintraege pro Lauf wuerden genau die Flaeche zumuellen,
# die alte Befunde sichtbar machen soll. Aggregat bleibt Aggregat.
if [ "${ABSTAND_RC:-0}" -ne 0 ] && [ "${ABSTAND_N:-0}" -eq 0 ]; then
  # Exit ungleich 0 OHNE Befundzeilen heisst nicht "alles ueber der Schwelle",
  # sondern "das Unterkommando gibt es hier nicht" (alte Skript-Fassung, exit 2).
  # Diese Unterscheidung ist der Unterschied zwischen einem Befund und einem
  # Werkzeugfehler — und ohne sie meldete der Lauf "0 Lease(s) ueber der
  # Schwelle" als WARN, was beim ersten Test genau so passierte.
  record "0.4.4 basis-abstand" "WARN" "Unterkommando 'abstand' nicht verfuegbar — platform-Haupt-Tree veraltet? (git -C \"$PLATFORM_DIR\" pull)"
elif [ "${ABSTAND_RC:-0}" -ne 0 ]; then
  record "0.4.4 basis-abstand" "WARN" "$ABSTAND_N Lease(s) ueber der Schwelle — vor weiterer Arbeit im Worktree: git merge origin/main"
  printf '%s\n' "$ABSTAND_OUT" | grep '^  ⚠' | head -5
else
  record "0.4.4 basis-abstand" "PASS" "${ABSTAND_ZEILE:-keine Lease ueber der Schwelle}"
fi

# ── 0.4.5 Auto-Reap der abgeraeumten Woche (nur das Ziel-Repo) ─────────────
# Freigabe Owner 2026-08-10 (#1866). Bewusst eng geschnitten:
#
#   nur das TARGET_REPO   Ein Lauf ueber die ganze Flotte kostet einen
#                         gh-Aufruf je Branch (gemessen: ~1 min). Wer in einem
#                         Repo arbeitet, raeumt dessen Baeume auf — ueber die
#                         Sitzungen konvergiert das, ohne je zu bremsen.
#   nur REAP_MERGED       Kein --include-stale. Un-gemergte Baeume bleiben.
#   Session-Start         Eine natuerliche Grenze, kein Timer. Ein Reaper, der
#                         mitten in eine Sitzung faellt, zieht ihr den Boden weg.
#
# Voraussetzung war die Reihenfolge-Korrektur in worktree-reaper.py: bis zum
# 2026-08-10 entschied der Merge-Zustand VOR dem Lease, und alle drei
# REAP_MERGED-Kandidaten der Flotte waren Baeume einer laufenden Sitzung. Ohne
# sie waere dieser Schritt nicht verantwortbar.
# Seit 2026-08-20 ueber ALLE Repos mit Lease, nicht nur $TARGET_REPO: Worktrees
# entstehen mitten in der Sitzung und werden haeufig fremd gemergt — der naechste
# Start betrifft dann ein anderes Repo und sah sie nie (Gate-Rueckfall, Retro 8d6869).
REAP_OUT="$(bash "$PLATFORM_DIR/tools/repo-session.sh" reap --alle 2>&1 || true)"
REAP_N="$(printf '%s\n' "$REAP_OUT" | grep -c '^entfernt:' || true)"
if [ "${REAP_N:-0}" -gt 0 ]; then
  record "0.4.5 auto-reap" "PASS" "$REAP_N gemergte(r) Worktree(s) ueber alle Repos mit Lease abgeraeumt (Restore-Zeilen im Manifest)"
  printf '%s\n' "$REAP_OUT" | grep '^entfernt:' | head -5
else
  record "0.4.5 auto-reap" "PASS" "nichts abzuraeumen (alle Repos mit Lease geprueft)"
fi

# ── 0.4.1 REFLEX aktualisieren + Review (nur wenn reflex.yaml im Target) ────
git -C "$GITHUB_DIR/iil-reflex" pull --rebase --quiet 2>/dev/null
REFLEX_VER=$(cd "$GITHUB_DIR/iil-reflex" 2>/dev/null && .venv/bin/python -c "import reflex; print(reflex.__version__)" 2>/dev/null || echo "?")
if [ -f "$GITHUB_DIR/$TARGET_REPO/reflex.yaml" ]; then
  if (cd "$GITHUB_DIR/iil-reflex" && .venv/bin/python -m reflex review all "$TARGET_REPO" --fail-on block --emit-metrics >/tmp/ssc_reflex.$$ 2>&1); then
    record "0.4.1 reflex" "PASS" "v${REFLEX_VER}, review ohne BLOCK" "$TARGET_REPO"
  else
    record "0.4.1 reflex" "WARN" "v${REFLEX_VER}, BLOCK-Findings — vor Weiterarbeit fixen (Log: reflex review all $TARGET_REPO)" "$TARGET_REPO"
  fi
  rm -f /tmp/ssc_reflex.$$
else
  # Ohne reflex.yaml ist die Frage: fehlt es, oder gibt es nichts zu reviewen?
  # REFLEX prueft Use-Case-Dokumente einer App. Ein Repo, das laut Registry nicht
  # deployt wird (platform: type=library, deployed=false — Meta-Repo ohne
  # App-Code), hat keine Use Cases und braucht kein reflex.yaml: das ist PASS
  # by design. Bei einem deployten Repo ohne reflex.yaml bleibt es SKIP, denn
  # dort waere die Datei der fehlende Teil (Session-Start 2026-09-24, #3471:
  # ein SKIP, der "by design" sagt und trotzdem als Luecke gezaehlt wird, ist
  # keins von beidem).
  REFLEX_DEPLOYED=$(cd "$PLATFORM_DIR/tools" && python3 -c "
import sys
from registry_api import repo
try:
    r = repo(sys.argv[1])
except Exception:
    print('?'); raise SystemExit
print('ja' if r.get('deployed') else 'nein')
" "$TARGET_REPO" 2>/dev/null || echo "?")
  if [ "$REFLEX_DEPLOYED" = "nein" ]; then
    record "0.4.1 reflex" "PASS" "v${REFLEX_VER}, $TARGET_REPO ohne reflex.yaml — nicht deployt (Registry), kein Use-Case-Review noetig (by design)" "$TARGET_REPO"
  else
    record "0.4.1 reflex" "SKIP" "v${REFLEX_VER}, $TARGET_REPO ohne reflex.yaml — Review übersprungen (deployed=${REFLEX_DEPLOYED}: Datei fehlt oder Registry unlesbar)" "$TARGET_REPO"
  fi
fi

# ══ VORLAUF-SCHNITT (platform#3373) ═════════════════════════════════════════
# Ab hier ist jeder Melder ein reiner Leser — davor wird gezogen, abgeraeumt
# und getunnelt. Deshalb starten die teuren Leser genau an dieser Stelle alle
# zusammen; geerntet werden sie unten an ihrer angestammten Phasenstelle.
#
# Was hier noch sequenziell steht, sind die drei Angaben, die die Auftraege als
# Argument brauchen (Owner, Melder-Ablage, Stillgelegt-Liste) — lokale Aufrufe
# im Sekundenbruchteil, die das Bild nicht verschieben.
OWNER=$(git -C "$PLATFORM_DIR" remote get-url origin | sed -E 's#.*[:/]([^/]+)/.*#\1#')
# platform#2944: Ergebnis zusaetzlich maschinenlesbar ablegen (0.7.11/0.7.27).
# Ziel liegt ABSICHTLICH ausserhalb des Repos — ein Sitzungsstart darf keinen
# Arbeitsbaum schmutzig machen.
MELDER_DIR="${MELDER_DIR:-$HOME/.repo-session/melder}"
mkdir -p "$MELDER_DIR" 2>/dev/null || true
# ausschreibungs-hub fehlte hier (2026-07-21 ergaenzt) — iilgmbh-Repos loesen
# ueber den Transfer-Redirect auch unter $OWNER auf, geprueft fuer risk-hub.
DEPLOY_REPOS="risk-hub billing-hub cad-hub coach-hub trading-hub travel-beat weltenhub wedding-hub pptx-hub ausschreibungs-hub"
# Stillgelegte/ruhende Repos (Owner-Entscheid in infra/ports.yaml) deployen nicht
# mehr und bleiben es auch nach `git log` nie wieder tun — ihr letzter Run bleibt
# fuer immer `failure`/`waiting`. Kein Befund, analog zur bewusst abgelehnten
# Freigabe in 0.7 (DEPLOY_REJECTED). `blockiert` gehoert NICHT dazu — das soll
# noch laufen und wartet nur auf eine Entscheidung (infra/ports.yaml §Lebenszyklus).
# Vokabular + Zuordnung Repo->betriebsstatus kommen aus tools/waisen_melder.py
# (erklaerte_repos, selbst auf tools/betriebsstatus.py gestuetzt) — keine zweite
# Kopie der Zuordnung hier.
DEPLOY_STILLGELEGT_REPOS=$(cd "$PLATFORM_DIR" && python3 -c "
import sys
sys.path.insert(0, 'tools')
import yaml
from waisen_melder import erklaerte_repos
ports = yaml.safe_load(open('infra/ports.yaml', encoding='utf-8')) or {}
erklaert = erklaerte_repos(ports)
erlaubt = {'stillgelegt', 'ruhend'}
print(' '.join(sorted(r for r, s in erklaert.items() if s in erlaubt)))
" 2>/dev/null || true)

# Ein Repo, drei gh-Aufrufe — und zehn Repos nacheinander waren der einzelne
# teuerste Block des Runners. Die Klassifikation bleibt unten in 0.7; hier wird
# nur die Netz-Wartezeit erhoben. Leere Antwort = Repo nicht abfragbar, und das
# muss sich von "alles gruen" unterscheiden lassen (sonst faellt ein Repo
# lautlos aus der Abdeckung) — deshalb das eigene Wort UNABFRAGBAR.
_deploy_probe() { # _deploy_probe <owner> <repo> → "<conclusion> <id> <waiting-min> <rejected>"
  local owner="$1" r="$2" out c id w rej=0
  out=$(gh run list -R "$owner/$r" --workflow Deploy --limit 1 --json databaseId,conclusion \
        --jq '"\(.[0].conclusion // "none") \(.[0].databaseId // "none")"' 2>/dev/null)
  if [ -z "$out" ]; then echo "UNABFRAGBAR"; return; fi
  read -r c id <<EOF
$out
EOF
  # `waiting` server-seitig, fenster- und frequenzunabhaengig (Begruendung 0.7).
  w=$(gh run list -R "$owner/$r" --workflow Deploy --status waiting --limit 100 \
      --json createdAt --jq '[.[].createdAt]|min // "none"' 2>/dev/null)
  [ -z "$w" ] && w="none"
  # Dritter Call nur im failure-Fall (nicht pro Repo) — abgelehnte Freigabe vom
  # echten Fehlschlag trennen, s. Kommentar in 0.7.
  if [ "$c" = "failure" ] && [ "$id" != "none" ]; then
    rej=$(gh api "repos/$owner/$r/actions/runs/$id/approvals" \
          --jq '[.[]|select(.state=="rejected")]|length' 2>/dev/null)
  fi
  printf '%s %s %s %s\n' "$c" "$id" "$w" "${rej:-0}"
}

# 0.7.4 prueft jede Prio-Referenz des Handovers gegen GitHub — gemessen
# 33,8 s, der zweitteuerste Einzelposten des Laufs. Als Funktion, weil das
# Werkzeug aus dem Repo-Verzeichnis heraus laufen will.
_prio_ref_probe() {
  cd "$GITHUB_DIR/$TARGET_REPO" || return 1
  python3 "$PLATFORM_DIR/tools/handover_stale_reference_check.py" AGENT_HANDOVER.md
}

# Die Staging-Sonde als Funktion, damit sie in den Vorlauf passt (ein Heredoc
# laesst sich nicht als Argumentliste weiterreichen).
_staging_probe() {
  python3 - "$STAGING_HOST" <<'PYEOF'
import yaml, socket, os, sys
gh = os.environ.get('GITHUB_DIR') or f"{os.environ['HOME']}/github"
try:
    from pathlib import Path
    d = yaml.safe_load(Path(f'{gh}/platform/infra/ports.yaml').read_text())
except Exception as e:
    print(f"ports.yaml nicht lesbar: {e}"); sys.exit(0)
ok = skip = 0
for name, cfg in sorted(d.get('services', {}).items()):
    if not cfg or not cfg.get('staging'):
        continue
    try:
        s = socket.create_connection((sys.argv[1], cfg['staging']), timeout=2); s.close(); ok += 1
    except OSError:
        skip += 1
print(f'{ok} up, {skip} nicht erreichbar (normal wenn nicht deployed)')
PYEOF
}

# Reihenfolge der Starts, in dieser Rangfolge:
#   1. die schmalen Spuren zuerst (ssh mit 3, git mit 1) — sie bestimmen, wann
#      der Vorlauf insgesamt fertig ist, und dort die teuersten Auftraege zuerst;
#   2. die freie Spur danach in der Reihenfolge, in der die Phasen sie ERNTEN.
# Punkt 2 aendert die Gesamtdauer nicht (die freie Spur ist nirgends der Engpass),
# macht aber die Phasen-Zeiten der `LAUFZEIT:`-Zeile wieder lesbar: sonst schluckt
# die erste erntende Phase die gesamte Wartezeit der Warteschlange und sieht als
# teuerste Phase des Laufs aus, obwohl sie nichts tut. Gemessen am 2026-09-22:
# 0.4.2 stand mit 63,9 s an der Spitze, sein Werkzeug braucht 1,9 s.
vorlauf_ssh  prod-wirkung timeout 150 python3 "$PLATFORM_DIR/tools/deploy_wirkung.py" --json
vorlauf_ssh  speicher     timeout 120 python3 "$PLATFORM_DIR/tools/speicher_melder.py" --kurz
vorlauf_ssh  deploy-skript "$PLATFORM_DIR/tools/deploy-script-drift.sh" --quiet
vorlauf_ssh  origin-tls   timeout 240 python3 "$PLATFORM_DIR/tools/origin_tls_melder.py" --kurz
vorlauf_ssh  backup-vol   timeout 180 python3 "$PLATFORM_DIR/tools/backup_deckung.py" --kurz
vorlauf2_ssh gpu-leerlauf timeout 180 python3 "$PLATFORM_DIR/tools/gpu_leerlauf.py" --kurz
vorlauf_ssh  host-kopien  python3 "$PLATFORM_DIR/tools/host_datei_drift.py" --quiet
vorlauf_ssh  opt-platform "$PLATFORM_DIR/tools/opt-platform-drift.sh" --quiet
vorlauf2_ssh registry-err timeout 120 python3 "$PLATFORM_DIR/tools/registry_erreichbarkeit_melder.py" --quiet

# git-Spur (Breite 1), teuerster zuerst
vorlauf_git sicht-drift timeout 120 python3 "$PLATFORM_DIR/tools/sichtbarkeits_drift_melder.py" --kurz \
                       --ergebnis-datei "$MELDER_DIR/sichtbarkeit.json"
for LANE in skills commands hooks; do
  vorlauf_git "skill-doctor:$LANE" timeout 120 python3 "$PLATFORM_DIR/tools/cc-skill-dist/doctor.py" --kind "$LANE"
done

# Freie Spur, in Ernte-Reihenfolge (0.4.2 → 0.9)
if command -v iil-adrfw >/dev/null 2>&1; then
  vorlauf2 adr-schema iil-adrfw validate "$PLATFORM_DIR/docs/adr/"
fi
vorlauf schleuse     python3 "$GITHUB_DIR/platform/tools/schleuse.py"
vorlauf2 adr156      bash "$GITHUB_DIR/mcp-hub/scripts/verify-adr156.sh"
for r in $DEPLOY_REPOS; do
  case " $DEPLOY_STILLGELEGT_REPOS " in *" $r "*) continue ;; esac
  vorlauf "deploy:$r" _deploy_probe "$OWNER" "$r"
done
vorlauf cron-melder  python3 "$PLATFORM_DIR/tools/cron_melder_check.py" --quiet
if [ -f "$GITHUB_DIR/$TARGET_REPO/AGENT_HANDOVER.md" ]; then
  vorlauf prio-ref _prio_ref_probe
fi
vorlauf hook-drift   "$PLATFORM_DIR/tools/hook-dist-drift.sh" --quiet
vorlauf leseflaeche  python3 "$PLATFORM_DIR/tools/hooks/befund_leseflaeche.py"
vorlauf zeitplan     timeout 120 python3 "$PLATFORM_DIR/tools/zeitplan_wach.py" --kurz
vorlauf gate-deckung python3 "$PLATFORM_DIR/tools/gate_deckung.py" --kurz
vorlauf gate-liege   python3 "$PLATFORM_DIR/tools/gate_deckung.py" --liegezeit --kurz
vorlauf kennzahl     timeout 300 python3 "$PLATFORM_DIR/tools/kennzahl_verfall.py" --kurz
vorlauf erreichbar   timeout 120 python3 "$PLATFORM_DIR/tools/erreichbarkeit_melder.py" --kurz \
                       --ergebnis-datei "$MELDER_DIR/erreichbarkeit.json"
vorlauf policy-frische timeout 60 python3 "$PLATFORM_DIR/tools/policy_frische.py" --kurz
vorlauf namdeck-kurz timeout 60 python3 "$PLATFORM_DIR/tools/gate_namensdeckung.py" --kurz
vorlauf namdeck-voll timeout 60 python3 "$PLATFORM_DIR/tools/gate_namensdeckung.py"
vorlauf praezision   python3 "$PLATFORM_DIR/tools/befund_journal.py" --praezision --kurz
vorlauf melder-reg   python3 "$PLATFORM_DIR/tools/melder_register_check.py" --kurz
vorlauf alarmweg     python3 "$PLATFORM_DIR/tools/alarmweg_probe.py" --pruefen --kurz
vorlauf rotation     timeout 60 python3 "$PLATFORM_DIR/tools/rotate.py" faellig --kurz
vorlauf ci-deckung   python3 "$PLATFORM_DIR/tools/ci_deckung.py" --repo "$GITHUB_DIR/$TARGET_REPO" --kurz
vorlauf umgebung     timeout 90  python3 "$PLATFORM_DIR/tools/umgebung.py" --repo "$TARGET_REPO" --kurz
vorlauf staging      _staging_probe

_vorlauf_loslegen
# ══ Ende Vorlauf-Start ══════════════════════════════════════════════════════

# ── 0.4.2 ADR-Schema-Validierung ────────────────────────────────────────────
if command -v iil-adrfw >/dev/null 2>&1; then
  ADR_OUT=$(ernte adr-schema | tail -3 | tr '\n' ' ')
  record "0.4.2 adr-schema" "PASS" "${ADR_OUT:0:160}"
else
  record "0.4.2 adr-schema" "WARN" "iil-adrfw nicht installiert — pip install iil-adrfw>=0.4.0"
fi

# ── 0.5 pgvector-Tunnel (PFLICHT, einziger Hard-FAIL) ───────────────────────
if ! ss -tlnp 2>/dev/null | grep -q 15435; then
  if ! sudo -n systemctl start ssh-tunnel-postgres 2>/dev/null; then
    (ssh -f -N -L 15435:localhost:15435 -o BatchMode=yes -o ConnectTimeout=5 \
       -i ~/.ssh/id_ed25519 "root@$PROD_HOST" 2>/dev/null)
  fi
  sleep 2
fi
if ss -tlnp 2>/dev/null | grep -q 15435; then
  record "0.5 pgvector-tunnel" "PASS" "localhost:15435 aktiv"
else
  record "0.5 pgvector-tunnel" "FAIL" "Tunnel nicht erreichbar — Memory tot, KEIN Fallback erlaubt (Fix: sudo systemctl start ssh-tunnel-postgres)"
fi

# ── 0.5.1 Secret-Drop-Zone-Guard (KONZ-010, warn) ───────────────────────────
if [ -d ~/shared/inbox/secrets ] && [ -n "$(ls -A ~/shared/inbox/secrets 2>/dev/null)" ]; then
  # shellcheck disable=SC2012  # ls -A statt find: nur Zaehlung, kein Name-Parsing
  N_SEC=$(ls -A ~/shared/inbox/secrets 2>/dev/null | wc -l)
  record "0.5.1 secret-zone" "WARN" "${N_SEC} Secret(s) in ~/shared/inbox/secrets — nach ~/.secrets reconcilen (KONZ-010)"
else
  record "0.5.1 secret-zone" "PASS" "Drop-Zone leer"
fi

# ── 0.5.2 Schleuse: was liegt zu lange? (KONZ-045, warn) ────────────────────
# Die Schleuse ist ein Foerderband, kein Regal. Ohne diese Zeile faellt erst auf,
# dass sie ein Lager geworden ist, wenn jemand hinsieht -- gemessen 2026-08-18:
# 247 Eintraege, 3,8 GB, der aelteste 119 Tage alt.
SCHLEUSE_OUT=$(ernte schleuse | tail -1)
SCHLEUSE_N=$(echo "$SCHLEUSE_OUT" | grep -oE '^Zusammenfassung: [0-9]+' | grep -oE '[0-9]+' || echo 0)
if [ "${SCHLEUSE_N:-0}" -gt 0 ]; then
  record "0.5.2 schleuse" "WARN" "$SCHLEUSE_OUT — Bericht: platform/tools/schleuse.py (KONZ-045)"
else
  record "0.5.2 schleuse" "PASS" "nichts ueberfaellig"
fi

# ── 0.6 Deploy-Infrastruktur (ADR-156) ──────────────────────────────────────
ADR156_OUT=$(ernte adr156 | tail -2 | tr '\n' ' ')
if echo "$ADR156_OUT" | grep -q "ALL .* PASSED"; then
  record "0.6 adr156" "PASS" "$(echo "$ADR156_OUT" | grep -o 'ALL [0-9]* CHECKS PASSED.*' | head -c 80)"
else
  record "0.6 adr156" "WARN" "nicht alle Checks grün — MCP-Server neustarten, dann verify-adr156.sh erneut"
fi

# ── 0.7 Deploy-Status aller Prod-Apps (gh, CC-Standard-Weg) ─────────────────
# Zwei Befund-Klassen pro Repo, nicht nur eine (Lehre 2026-07-21, ausschreibungs-hub):
#   a) letzter Run `conclusion: failure` — der offensichtliche Fall. ABER: eine
#      bewusst abgelehnte Environment-Freigabe zaehlt GitHub ebenfalls als
#      `failure` (eigenen Status dafuer gibt es nicht). Genau das ist hier der
#      Normalbetrieb: docs-only-Merges bekommen das Prod-Gate mit `rejected`
#      geschlossen, damit die Concurrency-Group frei bleibt (siehe b). Ohne
#      Unterscheidung meldet dieser Scan jede solche Ablehnung als Ausfall —
#      Alarm-Muedigkeit, gegen die advisory_scanner_reactivation_needs_baseline
#      steht. Unterscheidungsmerkmal: der Run traegt einen Approval-Eintrag mit
#      state=rejected; echte Fehlschlaege haben gar keinen. Gemessen 2026-07-22
#      an einem Positiv- (ausschreibungs-hub 29872512109: 1 rejected) und drei
#      Negativbeispielen (trading-hub 29507615298, risk-hub 29185036817,
#      coach-hub 28778482259: je 0 Approval-Eintraege).
#   b) IRGENDEIN Run auf `status: waiting` — haengt an einem Environment-
#      Approval-Gate und belegt die Concurrency-Group `deploy-<app>-<ref>`
#      weiter. `cancel-in-progress` greift dort NICHT, `gh run cancel` ebenso
#      wenig. Folge: jeder spaetere Deploy steht als `pending` mit 0 Jobs und
#      erreicht Prod nie — ohne dass irgendein Check rot wird. Realfall: Merge
#      #159 (ausschreibungs-hub) war 9 Tage nicht live, 0.7 meldete PASS, weil
#      `conclusion` eines waiting-Runs null ist. Aufloesung: pending_deployments
#      des ALTEN Runs mit state=rejected beantworten, nicht den neuen anfassen.
#      WICHTIG: die waiting-Suche laeuft server-seitig ueber `--status waiting`,
#      NICHT durch Sieben eines Fensters der letzten N Runs. Ein Fenster ist an
#      die Deploy-Frequenz gekoppelt, der zu findende Zustand aber an Kalender-
#      zeit — gemessen 2026-07-22: risk-hub >=100, trading-hub 81 Deploy-Runs in
#      30 Tagen, d.h. 20 Runs decken dort nur ~6-7 Tage ab, waehrend der Realfall
#      9 Tage hing. Ein Fenster-Filter haette den eigenen Anlassfall auf genau
#      den aktivsten Repos verfehlt und wieder PASS gemeldet.
DEPLOY_FAILS=""; DEPLOY_WAITING=""; DEPLOY_REJECTED=""; DEPLOY_SKIPPED=""; DEPLOY_CANCELLED=""; DEPLOY_STILLGELEGT=""; N_SCANNED=0
# Leerer Cutoff (kein GNU-date) wuerde die waiting-Erkennung still abschalten —
# das Ergebnis waere ein PASS, das eine nie gelaufene Pruefung als bestanden
# ausgibt. Deshalb wird der Zustand unten als degraded gemeldet, nicht verschluckt.
WAIT_CUTOFF=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "")
# OWNER, DEPLOY_REPOS und die Stillgelegt-Liste stehen oben am Vorlauf-Schnitt,
# weil die Sonden sie als Argument brauchen. Die Abfragen selbst laufen dort seit
# platform#3373 nebeneinander; hier wird nur noch geerntet und eingeordnet.
for r in $DEPLOY_REPOS; do
  case " $DEPLOY_STILLGELEGT_REPOS " in
    *" $r "*)
      # Owner-Entscheid steht in infra/ports.yaml, nicht hier — kein Deploy
      # erwartet, kein gh-Aufruf noetig, kein Befund.
      DEPLOY_STILLGELEGT="$DEPLOY_STILLGELEGT $r"
      continue
      ;;
  esac
  PROBE=$(ernte "deploy:$r")
  # UNABFRAGBAR = leere gh-Antwort (umbenannt, uebertragen ohne Redirect,
  # Token-Scope, API-Fehler). Frueher wurde still weitergesprungen, waehrend die
  # Erfolgsmeldung weiter die volle Repo-Zahl nannte — ein Repo konnte damit aus
  # der Abdeckung fallen, ohne dass die Ausgabe sich aenderte. Jetzt namentlich.
  if [ -z "$PROBE" ] || [ "$PROBE" = "UNABFRAGBAR" ]; then
    DEPLOY_SKIPPED="$DEPLOY_SKIPPED $r"
    continue
  fi
  N_SCANNED=$((N_SCANNED + 1))
  read -r C ID W REJ <<EOF
$PROBE
EOF
  if [ "$C" = "failure" ] && [ "$ID" != "none" ]; then
    if [ "${REJ:-0}" -gt 0 ] 2>/dev/null; then
      DEPLOY_REJECTED="$DEPLOY_REJECTED $r"
    else
      DEPLOY_FAILS="$DEPLOY_FAILS $r"
    fi
  fi
  # (2b) `cancelled` ist weder gruen noch rot — und faellt deshalb bis heute
  #      durch jedes Netz (platform#2148, Weg c). Realfall 2026-08-20 risk-hub:
  #      ein Prod-Dispatch wurde von einem gleichzeitigen Staging-Push ueber die
  #      Concurrency-Group abgeraeumt. Kein Check wurde rot, der Stand erreichte
  #      Prod nie. Was hier NICHT versucht wird: zwischen Handabbruch und
  #      Concurrency zu unterscheiden — dafuer gibt es keinen billigen Check, und
  #      die Frage, die zaehlt, ist ohnehin eine andere: ist der Stand live?
  #      Die beantwortet Phase 0.7.11 an der Wirkung.
  if [ "$C" = "cancelled" ]; then
    DEPLOY_CANCELLED="$DEPLOY_CANCELLED $r"
  fi
  # erst ab 24h melden: ein frisches Gate ist der Normalfall, kein Befund
  if [ "$W" != "none" ] && [ -n "$WAIT_CUTOFF" ] && [[ "$W" < "$WAIT_CUTOFF" ]]; then
    DEPLOY_WAITING="$DEPLOY_WAITING $r"
  fi
done
N_DEPLOY_REPOS=$(echo "$DEPLOY_REPOS" | wc -w)
# Abdeckung immer mitschreiben (gescannt/gesamt) statt nur die Soll-Zahl zu nennen.
# Stillgelegte Repos gehen nicht in N_SCANNED ein (kein gh-Aufruf, s.o.) —
# ohne den Zusatz saehe das wie eine Abdeckungsluecke aus.
COVERAGE="${N_SCANNED}/${N_DEPLOY_REPOS} Repos${DEPLOY_SKIPPED:+ · NICHT abfragbar:$DEPLOY_SKIPPED}${DEPLOY_STILLGELEGT:+ · stillgelegt (kein Befund):$DEPLOY_STILLGELEGT}"
# Betroffene Repos maschinenlesbar mitgeben (K1, platform#2004): failure UND waiting
# sind Befunde ueber ein FREMDES Repo — sie gehoeren dorthin, nicht in die
# platform-Prosa. Die nicht abfragbaren stehen getrennt, damit das Journal eine
# Abdeckungsluecke nicht als Heilung verbucht.
DEPLOY_BETROFFEN=$(echo "$DEPLOY_WAITING $DEPLOY_FAILS $DEPLOY_CANCELLED" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' ')
CANCEL_ZUSATZ="${DEPLOY_CANCELLED:+ · cancelled:$DEPLOY_CANCELLED — weder gruen noch rot; Wirkung pruefen (0.7.11)}"
if [ -n "$DEPLOY_WAITING" ]; then
  record "0.7 deploy-scan" "WARN" "waiting>24h:${DEPLOY_WAITING} — Gate blockiert die Concurrency-Group, Folge-Deploys erreichen Prod NICHT; altes Gate mit state=rejected beantworten${DEPLOY_FAILS:+ · failure:$DEPLOY_FAILS}${CANCEL_ZUSATZ} (${COVERAGE})" "${DEPLOY_BETROFFEN% }" "$DEPLOY_SKIPPED"
elif [ -n "$DEPLOY_FAILS" ]; then
  record "0.7 deploy-scan" "WARN" "failure:${DEPLOY_FAILS} — Logs lesen + User informieren (run-conclusion ≠ Änderung live)${CANCEL_ZUSATZ} (${COVERAGE})" "${DEPLOY_BETROFFEN% }" "$DEPLOY_SKIPPED"
elif [ -n "$DEPLOY_CANCELLED" ]; then
  record "0.7 deploy-scan" "WARN" "cancelled:${DEPLOY_CANCELLED} — letzter Deploy-Lauf wurde abgeraeumt (Concurrency-Group oder Handabbruch); kein Check wird davon rot. Wirkung pruefen: platform/tools/deploy_wirkung.py --repo <r> (${COVERAGE})" "${DEPLOY_BETROFFEN% }" "$DEPLOY_SKIPPED"
elif [ -z "$WAIT_CUTOFF" ]; then
  # F3: ohne Cutoff lief die waiting-Pruefung gar nicht — kein PASS behaupten.
  record "0.7 deploy-scan" "WARN" "degraded: WAIT_CUTOFF leer (kein GNU-date?) — haengende Approval-Gates wurden NICHT geprueft; kein failure in ${COVERAGE}" "$TARGET_REPO" "$DEPLOY_REPOS"
elif [ -n "$DEPLOY_SKIPPED" ]; then
  record "0.7 deploy-scan" "WARN" "unvollstaendig: ${COVERAGE} — kein failure/waiting in den geprueften, die uebrigen sind ungeprueft${DEPLOY_REJECTED:+ · bewusst abgelehnte Freigabe (kein Befund):$DEPLOY_REJECTED}" "$TARGET_REPO" "$DEPLOY_SKIPPED"
else
  # dito (Retro a84f71 #1): diese Phase scannt AUSSCHLIESSLICH Fremd-Repos —
  # `platform` steht in DEPLOY_REPOS gar nicht drin.
  record "0.7 deploy-scan" "PASS" "kein failure, kein haengendes Approval-Gate (${COVERAGE})${DEPLOY_REJECTED:+ · bewusst abgelehnte Freigabe (kein Befund):$DEPLOY_REJECTED}" "$DEPLOY_REPOS"
fi

# ── 0.7.1 deploy.sh Git↔Host-Drift ──────────────────────────────────────────
# Die Host-Kopie /opt/scripts/deploy.sh wird von Hand verteilt und lief messbar
# auseinander (2026-07-25: prod eine Revision hinter Git+Staging, u.a. ohne den
# override-Fix aus platform#1075). Ein grüner Deploy beweist NICHT, dass der Host
# das aktuelle Skript ausführt — und das Skript kann sich nicht selbst prüfen,
# der Check muss von außen kommen. Deshalb hier, wo er jede Session einmal läuft.
DRIFT_OUT=$(ernte deploy-skript | tail -1 || true)
case "$DRIFT_OUT" in
  "RESULT: OK"*)         record "0.7.1 deploy-script" "PASS" "${DRIFT_OUT#RESULT: OK — }" ;;
  "RESULT: DRIFT"*)      record "0.7.1 deploy-script" "WARN" "${DRIFT_OUT#RESULT: DRIFT — }" ;;
  "RESULT: UNGEPRUEFT"*) record "0.7.1 deploy-script" "WARN" "${DRIFT_OUT#RESULT: UNGEPRUEFT — }" ;;
  *)                     record "0.7.1 deploy-script" "WARN" "Drift-Check nicht auswertbar — manuell: platform/tools/deploy-script-drift.sh" ;;
esac

# ── 0.7.1b Verteilte Host-Kopien aus infra/host-maintenance/ (platform#2529) ──
# 0.7.1 deckt genau EINE Datei ab: scripts/deploy.sh. Die uebrigen verteilten
# Dateien — das Offsite-Skript, die systemd-Units der Timer — hatten keinen
# Melder. Am 2026-08-31 fiel beim Ausrollen eines Backup-Fixes auf, dass die
# prod-Kopie einen Tag alt war; /opt/platform stand da laengst auf dem neuen
# Commit. Ein gemergter Fix an einer Datei aus diesem Verzeichnis ist ohne
# diesen Check KEIN Beleg, dass er auf dem Host wirkt
# (🌀 feedback_hand_distributed_copy_merge_is_not_effect).
# Erstlauf 2026-08-31: 12 Kopien ueber 7 Hosts, davon 2 driftend.
HDD_OUT=$(ernte host-kopien | tail -1 || true)
case "$HDD_OUT" in
  "RESULT: OK"*)         record "0.7.1b host-kopien" "PASS" "${HDD_OUT#RESULT: OK — }" ;;
  "RESULT: DRIFT"*)      record "0.7.1b host-kopien" "WARN" "${HDD_OUT#RESULT: DRIFT — }" ;;
  "RESULT: UNGEPRUEFT"*) record "0.7.1b host-kopien" "WARN" "${HDD_OUT#RESULT: UNGEPRUEFT — }" ;;
  *)                     record "0.7.1b host-kopien" "WARN" "Host-Kopien-Check nicht auswertbar — manuell: platform/tools/host_datei_drift.py" ;;
esac

# ── 0.7.2 Blinde Cron-Melder (platform#1508) ────────────────────────────────
# 0.7 prüft Deploy-Läufe, aber NICHT den Zustand der Cron-Workflows auf main.
# Deshalb liefen `Runner Health Check` und `Deploy Failure Monitor` sechs Tage
# rot (HTTP 401 Bad credentials), ohne dass es in einer Session auffiel — beides
# Melder, die währenddessen nichts mehr meldeten und Abdeckung nur vortäuschten.
# Ein dauerhaft roter Melder ist schlimmer als kein Melder.
# Workflows mit dem Marker `# ROT-IST-BEFUND` zaehlen NICHT als blinde Melder:
# dort ist rot ein FUND, kein Defekt (🌀 feedback_run_conclusion_not_tool_health).
# Sie verschwinden aber auch nicht aus dem Bericht — sie kommen als TRIAGE
# zurueck. Beide Fehlrichtungen waren real: der Canary trug den Marker nicht und
# galt faelschlich als blind; die Funde des markierten Registry-Live-Reconcile
# waren umgekehrt gar nicht mehr sichtbar (2026-07-31).
CRON_OUT=$(ernte cron-melder | tail -1 || true)
case "$CRON_OUT" in
  "RESULT: OK"*)         record "0.7.2 cron-melder" "PASS" "${CRON_OUT#RESULT: OK — }" ;;
  "RESULT: BEFUND"*)     record "0.7.2 cron-melder" "WARN" "${CRON_OUT#RESULT: BEFUND — }" ;;
  "RESULT: TRIAGE"*)     record "0.7.2 cron-melder" "WARN" "${CRON_OUT#RESULT: TRIAGE — }" ;;
  "RESULT: UNGEPRUEFT"*) record "0.7.2 cron-melder" "WARN" "${CRON_OUT#RESULT: UNGEPRUEFT — }" ;;
  *)                     record "0.7.2 cron-melder" "WARN" "Cron-Melder-Check nicht auswertbar — manuell: platform/tools/cron_melder_check.py" ;;
esac

# ── 0.7.4 Prio zeigt auf Erledigtes (platform#1945 K3) ──────────────────────
# Phase 2.6 des Skills verlangt denselben Abgleich von HAND ("Handover ↔ Memory
# Reconciliation"). Genau daran haengt er: am 2026-08-12 zeigte die platform-Prio
# ZWEIMAL an einem Tag auf Ueberholtes, gefangen hat es nur ein Mensch, der daran
# dachte. Der Melder nimmt die Pflicht nicht weg, aber er faellt nicht aus, wenn
# jemand die Phase ueberliest (🌀 execution_fidelity_long_documents).
# Bewusst NUR das Ziel-Repo: ein Flotten-Lauf waere ein Netz-Call je Referenz und
# gehoert nicht in den Sitzungsstart.
STALE_REPO_DIR="$GITHUB_DIR/$TARGET_REPO"
if [ -f "$STALE_REPO_DIR/AGENT_HANDOVER.md" ]; then
  STALE_OUT=$(ernte prio-ref || true)
  STALE_N=$(echo "$STALE_OUT" | grep -c '^STALE' || true)
  case "$STALE_OUT" in
    PASS*)  record "0.7.4 prio-referenzen" "PASS" "$(echo "$STALE_OUT" | head -1 | cut -c1-120)" "$TARGET_REPO" ;;
    SKIP*)  record "0.7.4 prio-referenzen" "SKIP" "keine Prio-Liste im Handover — nichts geprueft" "$TARGET_REPO" ;;
    STALE*) record "0.7.4 prio-referenzen" "WARN" "$STALE_N Prio-Referenz(en) zeigen auf Erledigtes — Prio nachziehen VOR Arbeitsbeginn: $(echo "$STALE_OUT" | grep '^STALE' | head -3 | awk '{print $2}' | tr '\n' ' ')" "$TARGET_REPO" ;;
    *)      record "0.7.4 prio-referenzen" "WARN" "Prio-Referenz-Check nicht auswertbar — manuell: platform/tools/handover_stale_reference_check.py" "$TARGET_REPO" ;;
  esac
else
  record "0.7.4 prio-referenzen" "SKIP" "$TARGET_REPO ohne AGENT_HANDOVER.md — nichts geprueft" "$TARGET_REPO"
fi

# ── 0.7.3 /opt/platform Git↔Prod-Drift (platform#1585) ──────────────────────
# Der Prod-Klon /opt/platform haengt read-only im Mail-Container; gezogen wird er
# von Hand. Nichts meldet, wenn das unterbleibt — zwischen 2026-07-02 und
# 2026-07-29 lagen 27 Tage ohne Pull, und ein Merge nach main wirkte dort nicht,
# sah aber so aus. Wie bei 0.7.1 kann sich der Klon nicht selbst pruefen.
# Zwei getrennte WARN-Stufen mit Absicht: "HINTERHER" (Klon dahinter, aber
# tools/mail_agent identisch) ist Hygiene, "DRIFT" (Mail-Werkzeuge weichen ab)
# ist ein Prod-Befund. Eine einzige Stufe haette am 2026-08-03 einen harmlosen
# 28-Commit-Rueckstand wie einen Mail-Ausfall aussehen lassen.
OPTDRIFT_OUT=$(ernte opt-platform | tail -1 || true)
case "$OPTDRIFT_OUT" in
  "RESULT: OK"*)         record "0.7.3 opt-platform" "PASS" "${OPTDRIFT_OUT#RESULT: OK — }" ;;
  "RESULT: DRIFT"*)      record "0.7.3 opt-platform" "WARN" "${OPTDRIFT_OUT#RESULT: DRIFT — }" ;;
  "RESULT: HINTERHER"*)  record "0.7.3 opt-platform" "WARN" "${OPTDRIFT_OUT#RESULT: HINTERHER — }" ;;
  "RESULT: UNGEPRUEFT"*) record "0.7.3 opt-platform" "WARN" "${OPTDRIFT_OUT#RESULT: UNGEPRUEFT — }" ;;
  *)                     record "0.7.3 opt-platform" "WARN" "Drift-Check nicht auswertbar — manuell: platform/tools/opt-platform-drift.sh" ;;
esac

# ── 0.7.5 Hook-Verteil-Drift (platform#1989) ────────────────────────────────
# Dritter Fall derselben Klasse wie 0.7.1 und 0.7.3: die Welle-1-Scanner liegen
# DIREKT in ~/.claude/hooks/ und werden von settings.json von dort ausgefuehrt —
# eine Verteil-Lane gibt es fuer sie nicht (cc-skill-dist bespielt nur managed/).
# Am 2026-08-15 wichen alle drei von main ab; im aktiven gate_hits.py fehlte die
# pytest-Sperre aus #1986, also genau die Aenderung, die das neu gestartete
# Kalibrierfenster (#1640) vor Testrauschen schuetzen sollte. Merge gruen, Sperre
# im Repo vorhanden, Wirkung null. Die Kopie kann sich nicht selbst pruefen.
HOOKDRIFT_OUT=$(ernte hook-drift | tail -1 || true)
case "$HOOKDRIFT_OUT" in
  "RESULT: OK"*)         record "0.7.5 hook-dist" "PASS" "${HOOKDRIFT_OUT#RESULT: OK — }" ;;
  "RESULT: DRIFT"*)
    # Selbstheilung statt Meldung (platform#2143, Gate rueckfaellig).
    #
    # Das Gate war nie stumm — es meldete korrekt, und der Rueckfall passierte
    # trotzdem zweimal. Retro 9d861a hatte die Diagnose schon: „Die Luecke ist
    # nicht der Melder, sondern sein Ausloesezeitpunkt." Zwischen dem Merge und
    # dem naechsten Sitzungsstart liegt die Zeit, in der die aktive Kopie alt ist,
    # und eine Meldung, auf deren Befolgung man sich verlaesst, ist wieder Disziplin.
    #
    # Vertretbar, weil die Lane `claude-hooks` im `merge`-Modus arbeitet: kein
    # Verzeichnis-Swap, Datei fuer Datei, mit Backup des Vorstands. Die Quelle ist
    # `origin/main` — kanonisch, nicht der lokale Arbeitsbaum, der veraltet sein kann.
    #
    # Bewusst NICHT `hook-dist-drift.sh --sync`, obwohl es das gibt: es kopiert aus
    # `$PLATFORM_DIR/tools/claude-hooks`, also aus dem Arbeitsbaum. Genau der ist
    # beim Sitzungsstart regelmaessig Commits hinter `origin/main` — die Heilung
    # wuerde dann einen alten Stand als „synchron" festschreiben. `--sync` bleibt
    # der Handgriff fuer den Fall, dass man bewusst den lokalen Stand verteilen will.
    #
    # Positivkontrolle vor dem Verdrahten gefahren (2026-08-23, HOME-Sandkasten):
    # kuenstliche Drift in gate_hits.py -> DRIFT -> Heilung -> OK, 13 Dateien,
    # Backup angelegt. Ohne diesen Beleg waere „heilt sich selbst" eine Behauptung.
    HEIL_OUT=$(python3 "$PLATFORM_DIR/tools/cc-skill-dist/generate.py" \
                 --ref origin/main --kind claude-hooks \
                 --target "$HOME/.claude/hooks" --allow-live 2>&1 | tail -2 || true)
    NACHHER=$("$PLATFORM_DIR/tools/hook-dist-drift.sh" --quiet 2>/dev/null | tail -1 || true)
    case "$NACHHER" in
      "RESULT: OK"*) record "0.7.5 hook-dist" "PASS" "Drift selbst geheilt — ${NACHHER#RESULT: OK — } (vorher: ${HOOKDRIFT_OUT#RESULT: DRIFT — })" ;;
      # Heilung versucht und NICHT gelungen ist der interessantere Fall: dann ist
      # die Annahme falsch, dass die Lane diesen Pfad bespielt. Das gehoert gesagt.
      *)             record "0.7.5 hook-dist" "WARN" "Drift NICHT heilbar — ${HOOKDRIFT_OUT#RESULT: DRIFT — } · Verteil-Versuch: ${HEIL_OUT}" ;;
    esac
    ;;
  "RESULT: UNGEPRUEFT"*) record "0.7.5 hook-dist" "WARN" "${HOOKDRIFT_OUT#RESULT: UNGEPRUEFT — }" ;;
  *)                     record "0.7.5 hook-dist" "WARN" "Drift-Check nicht auswertbar — manuell: platform/tools/hook-dist-drift.sh" ;;
esac

# ── 0.7.6 Leseflaeche fuer die Melder-Befunde (platform#2006) ───────────────
# `tools/hooks/befund_leseflaeche.py` war als Gate `melder-ohne-leser` registriert,
# hatte einen gruenen Drill — und NULL Aufrufer: kein Treffer in settings.json, in
# keinem Skill, nirgends im Repo ausser Modul, Drill und Registry; die Zustandsdatei
# ~/.claude/hooks/state/leseflaeche.json war nie angelegt worden. Es war selbst der
# Fehlermodus, gegen den es gebaut wurde, und zaehlte im Drill-Pruefstand trotzdem
# als gebaut — die Drill-Pfad-≠-Aufruf-Pfad-Falle im Realfall.
#
# Hier, weil dieser Runner der Ort ist, an dem alle anderen Melder gelesen werden.
# Vor dem Verdrahten geprueft statt angenommen: der naechtliche `handover-reconcile`
# laeuft (Lauf 31927075538, success) und liefert sein Artefakt.
#
# FAIL-OPEN: das Werkzeug schluckt jeden eigenen Fehler; `|| true` stellt nur sicher,
# dass ein Fehlschlag den Runner nicht aufhaelt — ein Melder, der den Sitzungsstart
# kaputtmacht, wird abgeschaltet und meldet danach gar nichts mehr.
LESEFLAECHE_OUT=$(ernte leseflaeche || true)
if [ -n "$LESEFLAECHE_OUT" ]; then
  record "0.7.6 leseflaeche" "WARN" "$(echo "$LESEFLAECHE_OUT" | head -1 | tr '|' '/')"
  echo "$LESEFLAECHE_OUT" | tail -n +2
else
  record "0.7.6 leseflaeche" "PASS" "keine unbestaetigten Melder-Befunde"
fi

# ── 0.7.8 Zeitplan-Wache: von GitHub still abgeschaltete Workflows ──────────
# GitHub schaltet `schedule`-Trigger nach 60 Tagen ohne Repo-Aktivitaet ab. Der
# Workflow verschwindet dann nicht, er laeuft nur nie wieder — kein roter Lauf,
# keine Meldung, nur eine Luecke in der Historie. Realfall 2026-08-20:
# `infra-deploy` hatte `Database Backup` und `Health Check` seit dem 2026-07-30
# in `disabled_inactivity`. Drei Wochen ohne Datenbank-Backup, und das offene
# Issue dazu (#2114) vermutete eine ganz andere Ursache.
#
# Besonders betroffen sind Repos, die NUR Zeitplaene fahren: je verlaesslicher der
# Automatismus, desto weniger Grund, ins Repo zu pushen — sie schalten sich
# zwangslaeufig selbst ab.
#
# Repo-Liste kommt aus den ORGS, nicht nur aus der Registry: der erste Lauf meldete
# null, weil ausgerechnet `infra-deploy` dort kein `rich.github`-Feld traegt.
WACH_OUT=$(ernte zeitplan || true)
if [ -n "$WACH_OUT" ]; then
  record "0.7.8 zeitplan-wache" "WARN" "$(echo "$WACH_OUT" | head -1 | tr '|' '/')"
  echo "$WACH_OUT" | tail -n +2
else
  record "0.7.8 zeitplan-wache" "PASS" "kein Zeitplan still abgeschaltet"
fi

# ── 0.7.9 Gate-Deckung: GATE-PFLICHT gezaehlt, nie eingeloest ───────────────
# retro_kpis eskaliert jeden Slug >=2 zur GATE-PFLICHT. Die Pflicht wird gezaehlt,
# ihre Einloesung nirgends — 16 Slugs sind mehrfach aufgetreten und tragen weder
# Gate noch declined-Eintrag. Das ist die stille Schwester des Rueckfalls, den `tools/gate_wirkung.py` misst (Rueckfall-Pruefung seit 2026-09-17 in `/session-retro` Phase 0.0/5a):
# dort versagt ein gebautes Gate, hier entstand nie eines.
DECKUNG_OUT=$(ernte gate-deckung || true)
# Liegezeit in einem ZWEITEN Aufruf, nicht als Anhaengsel an `--kurz`: der Zweig
# unten entscheidet PASS/WARN allein an der Laenge von $DECKUNG_OUT. Liefe die
# Liegezeit dort mit, waere 0.7.9 dauerhaft gelb — und ein Melder, der jede
# Sitzung warnt, wird nicht gelesen. Dieselbe Zweitabfrage nutzt 0.7.15 schon.
#
# Sie steht in BEIDEN Zweigen, weil gerade der PASS-Fall sie braucht: "keine
# offene Gate-Pflicht" heisst nur, dass kein Slug ZWEIMAL ungedeckt auftrat.
# Die Einmal-Slugs liegen trotzdem, und der Bestand allein sagt nicht, ob der
# Loop schneller entscheidet als er findet (platform#2278 K3).
DECKUNG_LIEGE=$(ernte gate-liege || true)
if [ -n "$DECKUNG_OUT" ]; then
  record "0.7.9 gate-deckung" "WARN" "$(echo "$DECKUNG_OUT" | head -1 | tr '|' '/')${DECKUNG_LIEGE:+ · $DECKUNG_LIEGE}"
  echo "$DECKUNG_OUT" | tail -n +2
else
  record "0.7.9 gate-deckung" "PASS" "keine offene Gate-Pflicht${DECKUNG_LIEGE:+ · $DECKUNG_LIEGE}"
fi

# ── 0.7.10 Kennzahl-Verfall: nachrechenbare Zahlen in durablen Dokumenten ───
# Am 2026-08-20 stand dieselbe Kennzahl binnen zwei Stunden bei 16, dann 14, dann
# 15 — jedes Mal korrekt gemessen, jedes Mal aus anderem Grund. Zu dem Zeitpunkt
# stand sie bereits in einem Issue-Titel, einem Handover, einem Memory-Eintrag und
# zwei PR-Texten. Wer eine Kennzahl in ein durables Dokument schreibt, schreibt ein
# Verfallsdatum mit — und niemand merkt sich, es zu pruefen.
#
# OPT-IN: geprueft wird nur, was ausdruecklich mit <!--kz:NAME--> markiert ist. Ein
# Stand-Block SOLL altern duerfen; eine Prio-Zeile behauptet Gegenwart.
KZ_OUT=$(ernte kennzahl || true)
if [ -n "$KZ_OUT" ]; then
  record "0.7.10 kennzahl-verfall" "WARN" "$(echo "$KZ_OUT" | head -1 | tr '|' '/')"
  echo "$KZ_OUT" | tail -n +2
else
  record "0.7.10 kennzahl-verfall" "PASS" "alle markierten Kennzahlen aktuell"
fi

# ── 0.7.11 Erreichbarkeit der deklarierten Prod-Ziele ───────────────────────
# Fragt jedes AKTIVE `domain_prod` aus infra/ports.yaml einmal an. Alle anderen
# Phasen hier vergleichen Zusagen miteinander (Registry, Route, run-conclusion);
# diese ist die einzige, die das Ziel selbst befragt. wedding-hub war sechs bis
# sieben Tage tot, waehrend Registry und Tunnel-Route uebereinstimmten.
# platform#2944: Ergebnis zusaetzlich maschinenlesbar ablegen. Ziel liegt
# ABSICHTLICH ausserhalb des Repos -- ein Sitzungsstart darf keinen
# Arbeitsbaum schmutzig machen. Der Erheber liest von dort; fehlt die Datei
# oder ist sie aelter als sieben Tage, faellt er auf "unverified" zurueck,
# nicht auf rot.
# MELDER_DIR steht am Vorlauf-Schnitt, weil beide Melder es als Argument brauchen.
ERR_OUT=$(ernte erreichbar || true)
# "1 von 26 Prod-Zielen antworten nicht — bahn-hub (route-ohne-backend)":
# hinter dem Gedankenstrich stehen die Repos, in denen repariert wird.
ERR_REPOS="$(printf '%s' "$ERR_OUT" | sed 's/.*— //' | tr ',' '\n' \
            | sed 's/(.*//; s/^ *//; s/ *$//' | grep -E '^[a-z0-9._-]+$' | sort -u | tr '\n' ' ')"
case "$ERR_OUT" in
  ""|*"alle antworten"*) record "0.7.11 erreichbarkeit" "PASS" "${ERR_OUT:-nicht ausgefuehrt}" ;;
  *) record "0.7.11 erreichbarkeit" "WARN" "$ERR_OUT" "${ERR_REPOS% }" ;;
esac

# ── 0.7.16 Origin-TLS: was liefert der Server WIRKLICH aus? ────────────────
# 0.7.11 fragt am Edge. Eine 200 von dort ist KEIN TLS-Beleg: Cloudflare steht
# auf `full`, nicht `full (strict)`, und akzeptiert ein abgelaufenes oder gar
# kein Origin-Zertifikat, ohne dass von aussen etwas rot wird. Realfall
# ausschreibungs-hub 2026-08-23: der certbot-Cloudflare-Token war seit dem 08.08.
# ungueltig, 10 von 15 Origin-Zertifikaten abgelaufen — zwei Wochen unbemerkt,
# gefunden beiher bei einer anderen Aufgabe. Diese Phase misst auf dem Host.
# Kosten: rund 30 s (1 ssh je Prod-Host, Handshakes lokal), fail-open.
TLS_OUT=$(ernte origin-tls || true)
# "2 Origin-Zertifikat(e) auffaellig — doc-hub (fallback-zertifikat, 3453d), …":
# hinter dem Gedankenstrich stehen die Repos, in denen repariert wird.
TLS_REPOS="$(printf '%s' "$TLS_OUT" | sed 's/.*— //' | tr ',' '\n' \
            | sed 's/(.*//; s/^ *//; s/ *$//' | grep -E '^[a-z0-9._-]+$' | sort -u | tr '\n' ' ')"
case "$TLS_OUT" in
  ""|*"Zertifikat(e) gueltig,"*) record "0.7.16 origin-tls" "PASS" "${TLS_OUT:-nicht ausgefuehrt}" ;;
  *) record "0.7.16 origin-tls" "WARN" "$TLS_OUT" "${TLS_REPOS% }" ;;
esac

# ── 0.7.17 Backup-Deckung: jedes Prod-Volume gedeckt, verzichtet oder rot ────
# backup-meter (ADR-241 §4) prueft die Apps einer gepflegten Soll-Liste. Was in
# keiner Liste steht, sieht er nicht — so lagen acht Volumes mit 2,1 GB ohne
# einen einzigen Snapshot da (#2086), waehrend der Meter jeden Morgen gruen war.
# Diese Phase geht vom Host aus (`docker volume ls`) und verlangt fuer JEDES
# Volume eine Antwort. Erstlauf 2026-08-25: 46 ungedeckt, 7,2 GB, darunter drei
# doc-hub-Volumes in Nutzung. Kosten: 3 ssh (2 Hosts + restic), ~20 s.
#
# Kein `""`-Zweig auf PASS: die Werkzeuge reden IMMER (#2280). Leere Ausgabe
# heisst hier "nicht gelaufen" und ist ein WARN, kein Gruen.
DECKUNG_VOL_OUT=$(ernte backup-vol || true)
case "$DECKUNG_VOL_OUT" in
  OK:*) record "0.7.17 backup-deckung" "PASS" "$DECKUNG_VOL_OUT" ;;
  "")   record "0.7.17 backup-deckung" "WARN" "Melder nicht gelaufen — keine Aussage zur Deckung" ;;
  *)    record "0.7.17 backup-deckung" "WARN" "$DECKUNG_VOL_OUT" ;;
esac

# ── 0.7.18 Speicher-Vorlauf: Platten melden VORHER, nicht bei 90 % ──────────
# Am 2026-08-24 begann das reparierte dev-hub-Backup, 6,3 GB pro Tag auf die
# Root-Platte von prod zu schreiben — sieben Tage bis voll, und kein Melder
# haette es gesagt, weil keiner Platten misst. Eine Schwelle bei 90 % ruft am
# sechsten Tag; ein Wochenende dazwischen, und die Platte ist voll. Diese Phase
# fuehrt je (Host, Mount) ein Tagesjournal (~/.claude/speicher-journal.jsonl)
# und rechnet aus dem Median der Tagesdifferenzen die Tage bis voll — WARN
# unter 7 Tagen oder unter 10 % frei. SAMMELPHASE ist ausdruecklich KEINE
# Entwarnung, nur "noch keine Rate". Alle Hosts mit ssh, auch Offsite: eine
# volle Offsite-Platte beendet das Backup lautlos.
SPEICHER_OUT=$(ernte speicher || true)
case "$SPEICHER_OUT" in
  OK:*|SAMMELPHASE*) record "0.7.18 speicher" "PASS" "$SPEICHER_OUT" ;;
  "")   record "0.7.18 speicher" "WARN" "Melder nicht gelaufen — keine Aussage zur Speicherlage" ;;
  *)    record "0.7.18 speicher" "WARN" "$SPEICHER_OUT" ;;
esac

# ── 0.7.12 Prod-Wirkung: was liegt WIRKLICH auf den Hosts? (platform#2148) ──
# `tools/deploy_wirkung.py` existiert seit dem 2026-08-20 und hatte bis hierhin
# NULL Aufrufer — es stand nur in Handover, Log und Archiv. Genau die Klasse
# `melder-ohne-leser`: gebaut, gruen gedrillt, nie gelesen. Dabei ist es das
# einzige Werkzeug, das den Stand HINTER dem oeffentlichen Namen mit origin/main
# vergleicht; die Wege (b) und (c) aus #2148 werden nur hier sichtbar — ein
# `staging`-Default und ein abgeraeumter Dispatch machen keinen Check rot.
# Kosten: rund 20 s (2x ssh + je Repo eine API-Abfrage), fail-open.
WIRK_JSON=$(ernte prod-wirkung || true)
if [ -z "$WIRK_JSON" ]; then
  record "0.7.12 prod-wirkung" "WARN" "Melder nicht auswertbar (ssh/timeout) — manuell: platform/tools/deploy_wirkung.py"
else
  # Zusammenfassen in Python: der JSON-Baum ist zu verschachtelt fuer jq-Akrobatik
  # in einer Zeile, und ein halb geparster Melder ist schlimmer als keiner.
  # shellcheck disable=SC2016  # Single Quotes gewollt: Python-Code, kein Bash-Expand
  WIRK_OUT=$(printf '%s' "$WIRK_JSON" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    print("STATUS=WARN|Melder-Ausgabe nicht parsebar|"); raise SystemExit(0)
b = d.get("befunde", [])
# Ruhende Repos duerfen hinterherhinken — das ist der gewollte Zustand.
def na(e, k): return bool(e.get(k)) and not e.get("ruhend")
# Ein Repo mit Prod-Gate deployt bei push nur nach staging; Prod verlangt eine
# bewusste Freigabe. Sein Rueckstand ist bis zu einer Frist der NORMALFALL und
# darf nicht dieselbe Lautstaerke haben wie ein vergessener Deploy — risk-hub
# stand so 23 Laeufe lang als WARN, worin ein echter Fund untergegangen waere.
# Unterdrueckt wird er trotzdem nicht (deploy_wirkung.hat_prod_gate begruendet
# das am tax-hub-Fall: Prod-Gate UND roter Build): er bleibt in der Zeile
# sichtbar, nur eben als Wartestand — und wird nach der Frist laut, denn dann
# ist "wartet auf Freigabe" nicht mehr von "vergessen" zu unterscheiden.
FREIGABE_FRIST_TAGE = 14
def wartet(e):
    return (na(e, "rueckstand") and e.get("prod_gate")
            and (e.get("alter_tage") or 0) < FREIGABE_FRIST_TAGE)
dop  = [e["repo"] for e in b if e.get("doppellauf")]
warte= ["%s(%sd)" % (e["repo"], e.get("alter_tage", "?")) for e in b if wartet(e) and not e.get("nur_doku")]
# Rueckstand nur aus Doku-Pfaden (writing-hub deployt Doku-Merges per
# Cosmetic-Gate #1009 bewusst nicht): kein Befund, `nur_doku` schlaegt daher
# `wartet` (ein Doku-Rueckstand ist auch mit Prod-Gate ein Doku-Rueckstand).
# Faellt der Doku-Check aus (gh-Fehler, >=300 Dateien), fehlt `nur_doku` —
# dann bleibt der Eintrag ganz normal in `rueck`/`warte`, also laut.
doku = [e["repo"] for e in b if na(e, "rueckstand") and e.get("nur_doku")]
rueck= [e["repo"] for e in b if na(e, "rueckstand") and not wartet(e) and not e.get("nur_doku")]
verw = [e["repo"] for e in b if e.get("verwaiste_manifeste")]
unk  = [e["repo"] for e in b if e.get("zuordnung_unklar") or e.get("container_unklar")]
teile, betroffen = [], sorted(set(dop + rueck))
if dop:   teile.append("DOPPELLAUF:" + ",".join(dop))
if rueck: teile.append("RUECKSTAND:" + ",".join(rueck))
if warte: teile.append("wartet auf Prod-Freigabe (kein Befund):" + ",".join(warte))
if doku:  teile.append("nur Doku hinter main (kein Befund):" + ",".join(doku))
if verw:  teile.append("verwaistes Manifest:" + ",".join(verw))
if unk:   teile.append("Zuordnung/Container unklar:" + ",".join(unk))
status = "WARN" if (dop or rueck) else "PASS"
note = " · ".join(teile) if teile else f"{d.get("geprueft", 0)} Repo(s): deployter Stand == origin/main"
print(f"STATUS={status}|{note}|{" ".join(betroffen)}")
' 2>/dev/null || echo "STATUS=WARN|Melder-Ausgabe nicht parsebar|")
  WIRK_STATUS=$(printf '%s' "$WIRK_OUT" | sed -n 's/^STATUS=\([A-Z]*\)|.*/\1/p')
  WIRK_NOTE=$(printf '%s' "$WIRK_OUT" | cut -d'|' -f2)
  WIRK_REPOS=$(printf '%s' "$WIRK_OUT" | cut -d'|' -f3)
  # Rueckstand und Doppellauf sind Befunde ueber FREMDE Repos (K1, platform#2004):
  # die Repo-Liste geht mit, sonst landet der Befund als platform-Prosa im Nichts.
  record "0.7.12 prod-wirkung" "${WIRK_STATUS:-WARN}" "${WIRK_NOTE:-nicht auswertbar}" "$WIRK_REPOS"
fi

# ── 0.7.14 Policy-Frische (Slug `platform-pinned-perma-dirty-loop`) ────────
# `inject_policies.py` schiebt bei JEDEM Prompt Policies in den Kontext und prueft
# dabei keine Frische. Der Refresh dahinter hat eine stille Bremse:
# `refresh_pinned_policies.sh` ueberspringt ihn, wenn `~/github/platform-pinned`
# DIRTY ist — sein Hinweis erscheint einmal beim Sitzungsstart und verschwindet,
# injiziert wird stundenlang weiter. Gemessen am 2026-07-31: ein Pin lag 17 Commits
# zurueck, darunter PR #1601, der genau zwei der injizierten Policies aenderte.
#
# Geurteilt wird am INHALT gegen origin/main, nicht an der mtime: am 2026-08-23
# trugen 16 von 16 ausgelieferten Dateien den 3. August und waren trotzdem aktuell.
POLFRISCHE_OUT=$(ernte policy-frische || true)
if [ -n "$POLFRISCHE_OUT" ]; then
  record "0.7.14 policy-frische" "WARN" "$(echo "$POLFRISCHE_OUT" | head -1 | tr '|' '/')"
else
  record "0.7.14 policy-frische" "PASS" "ausgelieferte Policies inhaltsgleich mit origin/main"
fi

# ── 0.7.15 Namensdeckung der Gates (Slug `gate-modul-prueft-weniger-als-sein-name`) ──
# Drei Messpunkte des Loops sagen "gebaut" (Registry), "feuert" (Drill) und
# "rueckfaellig" (`tools/gate_wirkung.py`, geprueft in `/session-retro` Phase 0.0/5a). Keiner fragt, ob der Drill den Fall beruehrt, der im
# SLUG-NAMEN steht. Realfall 2026-08-23: `lint-failure-no-local-gate` ist
# `blocking`, heisst "lint" und fuehrt `ruff format --check` aus — E402 lag seit
# dem Bau am 04.08. ausserhalb seiner Reichweite, und PR #2236 wurde daran
# zweimal rot, waehrend alle drei Messpunkte gruen standen.
#
# Laut wird die Phase nur bei einer LUECKE (Fall benannt, Drill beruehrt ihn
# nicht). Die Zahl der `ungeprueft`-Gates steht in der PASS-Note statt in einer
# WARN-Zeile: sie ist Bestandsarbeit, keine Stoerung — aber sie verschwindet
# auch nicht, sonst waere aus "nie gefragt" wieder ein stilles Gruen.
NAMDECK_OUT=$(ernte namdeck-kurz || true)
NAMDECK_ZAHLEN=$(ernte namdeck-voll \
                  | grep -oE "(gedeckt|ungeprueft) +: +[0-9]+" | tr -s ' ' | tr '\n' ' ' || true)
if [ -n "$NAMDECK_OUT" ]; then
  record "0.7.15 namensdeckung" "WARN" "$(echo "$NAMDECK_OUT" | head -1 | tr '|' '/')"
  echo "$NAMDECK_OUT" | tail -n +2
else
  record "0.7.15 namensdeckung" "PASS" "kein Gate nennt einen ungedrillten Fall (${NAMDECK_ZAHLEN:-keine Zahlen})"
fi

# ── 0.7.13 Skill-Verteil-Drift (Slug `skill-copy-not-redistributed`) ────────
# Schwester von 0.7.5, und zwar die unbeaufsichtigte: 0.7.5 deckt AUSSCHLIESSLICH
# die Lane `claude-hooks` (~/.claude/hooks). Skills und Commands haben eine
# eigene Verteil-Lane (cc-skill-dist) — und `doctor.py` prueft sie seit Monaten
# read-only, mit Drill (tools/tests/test_doctor.py) und Exit-Code-Vertrag.
# Aufgerufen hat es im Sitzungs-Loop nie jemand: der Slug
# `skill-copy-not-redistributed` steht 3x in den Retros und hatte kein Gate,
# waehrend das Werkzeug dafuer fertig danebenlag. Genau die Klasse
# `melder-ohne-leser` — dieselbe, in der `deploy_wirkung.py` bis zum 2026-08-23
# stand (0.7.12).
#
# Geurteilt wird am DRIFT-SCORE, nicht am Exit-Code: `doctor.py` beendet auch mit
# 0, wenn es Hinweise ausgibt, und ein Aufruf in einer Pipeline liefert ohnehin
# den Status des letzten Glieds. Fehlt die Score-Zeile, ist das UNGEPRUEFT und
# nicht gruen (die SKIP-ist-kein-PASS-Lehre aus KONZ-platform-050).
SKILLDRIFT_NOTE=""
SKILLDRIFT_STATUS="PASS"
# `hooks` steht bewusst mit in der Liste, obwohl 0.7.5 schon "Hooks" im Namen traegt:
# das sind ZWEI Lanes. 0.7.5 deckt `claude-hooks` (~/.claude/hooks, flach), die Lane
# `hooks` liegt darunter in managed/ und war von KEINER Phase beaufsichtigt. Beim
# Aufnehmen am 2026-08-23 war sie sofort rot: `stale_clone_check.sh` lag als Kopie vom
# 2026-07-26 live, waehrend die Quelle am 2026-08-06 ihren GATE_HEADER bekam — vier
# Wochen Drift, die niemand meldete.
# HEILEN STATT MELDEN (2026-08-26). Bis hierhin endete diese Phase mit einer
# WARN-Zeile und dem Kommando im Text — und niemand fuehrte es aus. Realfall vom
# selben Tag: `/ux-review` existierte seit dem Vorabend in origin/main, die Lane
# `commands` war acht Stunden hinterher, der Skill stand nicht zur Auswahl. Die
# Sitzung schrieb die Drift-Zeile brav ins Board und arbeitete dann einen ganzen
# GUI-Durchlauf lang ohne den Skill, der genau dafuer gebaut ist. Drei Fehler,
# gegen die er geschrieben ist, passierten dabei erneut.
#
# Das ist dieselbe Klasse `melder-ohne-leser`, die im Kommentar oben schon steht —
# nur eine Ebene hoeher: der Melder wurde gelesen, und trotzdem geschah nichts.
# Ein Hinweis, dessen Behebung ein Kommando im Fliesstext ist, wird nicht
# ausgefuehrt; er wird zitiert.
#
# Vertretbar wie bei 0.7.5: Quelle ist `origin/main` (kanonisch, nicht der
# Arbeitsbaum), `generate.py` legt ein Backup an und ist idempotent.
for LANE in skills commands hooks; do
  # Nur die VORmessung kommt aus dem Vorlauf; geheilt und nachgemessen wird
  # weiterhin sequenziell (eine Heilung darf nicht neben ihrer eigenen Messung
  # laufen).
  LANE_OUT=$(ernte "skill-doctor:$LANE" || true)
  LANE_SCORE=$(printf '%s' "$LANE_OUT" | grep -o 'DRIFT-SCORE: [0-9]*' | head -1 | grep -o '[0-9]*')

  if [ -n "$LANE_SCORE" ] && [ "$LANE_SCORE" -gt 0 ]; then
    # Ziel je Lane: `skills`/`commands` liegen flach unter ~/.claude, die Lane
    # `hooks` darunter in managed/ (siehe Kommentar oben — zwei Lanes, ein Name).
    case "$LANE" in
      skills)   LANE_TARGET="$HOME/.claude/skills" ;;
      commands) LANE_TARGET="$HOME/.claude/commands" ;;
      hooks)    LANE_TARGET="$HOME/.claude/hooks/managed" ;;
    esac
    # Die letzte Zeile des Heilers wird aufgehoben: scheitert er, sagt sie den
    # Grund (2026-09-24: "traegt ein MANAGED_BY, aber kein manifest.json"), waehrend
    # die WARN-Zeile bis dahin nur einen falschen Ziel-Pfad VERMUTETE — drei Laeufe
    # lang, weil stdout/stderr hier verworfen wurden (platform#3468).
    LANE_HEIL="$(timeout 180 python3 "$PLATFORM_DIR/tools/cc-skill-dist/generate.py" \
      --ref origin/main --kind "$LANE" --target "$LANE_TARGET" --allow-live 2>&1 | tail -1 || true)"
    # Nachmessen, nicht annehmen: die Heilung gilt erst, wenn doctor sie bestaetigt.
    NACH_OUT=$(timeout 120 python3 "$PLATFORM_DIR/tools/cc-skill-dist/doctor.py" --kind "$LANE" 2>/dev/null || true)
    NACH_SCORE=$(printf '%s' "$NACH_OUT" | grep -o 'DRIFT-SCORE: [0-9]*' | head -1 | grep -o '[0-9]*')
    if [ "${NACH_SCORE:-1}" = "0" ]; then
      SKILLDRIFT_NOTE="${SKILLDRIFT_NOTE}${LANE}:geheilt(${LANE_SCORE}->0) "
      continue
    fi
    # Heilung versucht und nicht gelungen ist der interessantere Fall: dann stimmt
    # die Annahme ueber den Ziel-Pfad nicht. Das gehoert gesagt, nicht verschwiegen.
    LANE_SCORE="${NACH_SCORE:-}"
    if [ -z "$LANE_SCORE" ]; then
      SKILLDRIFT_STATUS="WARN"
      SKILLDRIFT_NOTE="${SKILLDRIFT_NOTE}${LANE}:NICHT-HEILBAR(ungeprueft) "
      continue
    fi
    SKILLDRIFT_STATUS="WARN"
    SKILLDRIFT_NOTE="${SKILLDRIFT_NOTE}${LANE}:NICHT-HEILBAR(Score ${LANE_SCORE}; Heiler: ${LANE_HEIL:-ohne Ausgabe}) "
    continue
  fi

  if [ -z "$LANE_SCORE" ]; then
    SKILLDRIFT_STATUS="WARN"
    SKILLDRIFT_NOTE="${SKILLDRIFT_NOTE}${LANE}:UNGEPRUEFT "
  else
    SKILLDRIFT_NOTE="${SKILLDRIFT_NOTE}${LANE}:0 "
  fi
done
if [ "$SKILLDRIFT_STATUS" = "WARN" ]; then
  # Zwei sehr unterschiedliche Ursachen fuehren zu NICHT-HEILBAR — beide gehoeren in
  # den Hinweis, nicht nur die erste geratene (platform#3467, Realfall 2026-09-23):
  # (a) der Ziel-Pfad der Lane stimmt nicht (klassischer Tippfehler), ODER
  # (b) eine SWAP-Lane (`commands`/`hooks`) trifft auf ein Mischverzeichnis mit
  #     Fremdinhalt (z.B. ein anderes Werkzeug schreibt eigenmaechtig ins selbe Ziel,
  #     wie der claude.ai-Skill-Sync das bis #3467 fuer `skills` tat) — der Swap-Guard
  #     `pruefe_swap_ziel` bricht dann zu Recht ab, weil ein Swap den Fremdinhalt
  #     wegwischen wuerde. Fix in dem Fall ist NICHT der Ziel-Pfad, sondern die Lane auf
  #     `mode: merge` umzustellen (Vorbild `claude-hooks`, s. generate.py LANES).
  record "0.7.13 skill-dist" "WARN" "${SKILLDRIFT_NOTE% } — Selbstheilung versucht und NICHT gelungen; entweder stimmt der Ziel-Pfad der Lane nicht, oder das Ziel ist ein Mischverzeichnis mit Fremdinhalt, das der Swap-Guard zu Recht blockiert (dann hilft kein Pfad-Fix, sondern mode:merge fuer die Lane) — manuell: tools/cc-skill-dist/doctor.py --kind <lane> / tools/cc-skill-dist/generate.py --kind <lane> --target ... (Fehlertext lesen)"
else
  record "0.7.13 skill-dist" "PASS" "alle Lanes synchron (${SKILLDRIFT_NOTE% })"
fi

# ── 0.7.19 Melder-Praezision: wer haeufiger irrt als trifft ─────────────────
# Am 2026-08-20 waren in EINER Sitzung vier Melder-Befunde falsch: ein DOPPELLAUF
# ohne laufende Container, drei required-file-Errors fuer Dateien, die es gibt (nur
# woanders), ein Footer-Hash, der jede korrekte Kopie als Drift meldet, und zwei
# Melder, die gemergte PRs als offene Referenz lesen. Vier Melder, vier Fehlalarme,
# null Messung.
#
# Ein Melder, der oefter irrt als trifft, erzieht zum Wegsehen — und das trifft dann
# auch seine RICHTIGEN Befunde. Dieselbe Klasse wie ein rueckfaelliges Gate (`tools/gate_wirkung.py`, geprueft in `/session-retro` Phase 0.0/5a),
# nur auf der Erkennungsseite.
#
# Die Urteile kommen aus /session-ende (--echt / --falsch). Ohne Urteile bleibt die
# Zeile still: eine Praezision unter drei Urteilen ist Rauschen, kein Befund.
PRAEZ_OUT=$(ernte praezision || true)
if [ -n "$PRAEZ_OUT" ]; then
  record "0.7.19 melder-praezision" "WARN" "$(echo "$PRAEZ_OUT" | head -1 | tr '|' '/')"
  echo "$PRAEZ_OUT" | tail -n +2
else
  record "0.7.19 melder-praezision" "PASS" "kein Melder unter der Trefferquote"
fi
# Schreibt/leert governance-gestuetzt ~/.claude/hooks/state/melder-herabgestuft.tsv
# (mindest_laeufe/praezision_min je Phase aus governance/melder-register.yaml) —
# gelesen wird die Datei oben in record(), also erst im NAECHSTEN Lauf wirksam.
python3 "$PLATFORM_DIR/tools/melder_register_check.py" --herabstufung >/dev/null 2>&1 || true

# ── 0.7.23 Melder-Register: hat jeder Melder einen Leser, eine Frist? (#2690 K3) ──
# Ergaenzt 0.7.19 (Trefferquote) um die anderen beiden K3-Dinge: benannter Leser
# und Wiedervorlage-Frist. `governance/melder-register.yaml` traegt einen Eintrag
# je Runner-Phase; ohne Eintrag oder mit `leser: UNBENANNT` ist die Phase ein
# Melder, der niemanden erreicht — dieselbe Klasse wie ein Melder mit schlechter
# Trefferquote, nur auf der Zustell- statt der Erkennungsseite. Erstlauf
# 2026-09-02 (#2690): 26 von 39 Phasen ohne Leser, ehrlich als UNBENANNT geführt.
REGISTER_OUT=$(ernte melder-reg || true)
if [ -n "$REGISTER_OUT" ]; then
  record "0.7.23 melder-register" "WARN" "$(echo "$REGISTER_OUT" | head -1 | tr '|' '/')"
  echo "$REGISTER_OUT" | tail -n +2
else
  record "0.7.23 melder-register" "PASS" "kein Melder ohne Leser, keine Karteileiche"
fi

# ── 0.7.21 Alarmweg: erreicht ein Alarm ueberhaupt einen Menschen? ─────────
# KONZ-054 E4. Ein Kanal gilt erst, wenn er in den letzten Tagen einmal
# nachweislich benutzt wurde (woechentliche Probe, .github/workflows/alarmweg-
# probe.yml). Gemessen 2026-08-30: 177 Tage `| mail` ohne MTA, ein Discord-Secret,
# das drei Workflows nennen und das nicht existiert. Exit 2 = blind, kein PASS.
warte_auf alarmweg; ALARM_RC=$ERNTE_RC; ALARM_OUT=$(ernte alarmweg)
case "$ALARM_RC" in
  0) record "0.7.21 alarmweg" "PASS" "${ALARM_OUT:-belegt}" ;;
  1) record "0.7.21 alarmweg" "WARN" "${ALARM_OUT:-Alarmweg fehlt}" ;;
  *) record "0.7.21 alarmweg" "SKIP" "${ALARM_OUT:-blind: Probe-Laeufe nicht lesbar}" ;;
esac

# ── 0.7.22 Flottenbild: liegt ein frisches Systembild vor, und was sagt es? ──
# KONZ-054, 189. Das Bild rendert ein Timer taeglich (infra/host-maintenance/
# flottenbild.timer) nach ~/.claude/flottenbild/latest.json; hier wird nur gelesen —
# ein Volllauf dauert Minuten und gehoert nicht in den Sitzungsstart. Aelter als
# 30 h oder nicht alle Knoten gemessen = WARN; keine Datei = SKIP (nie PASS).
FB="$HOME/.claude/flottenbild/latest.json"
if [ -f "$FB" ]; then
  FB_OUT=$(python3 - "$FB" <<'PYEOF' 2>/dev/null
import json, sys, time, os
p = sys.argv[1]; d = json.load(open(p))
alter_h = (time.time() - os.stat(p).st_mtime) / 3600
kn = d.get("knoten", []); gem = [k for k in kn if k["zustand"] == "gemessen"]
fehlt = [k["knoten"] for k in kn if k["zustand"] not in ("gemessen", "geplant")]
prom = d.get("prometheus", {}); feuern = [a for a in prom.get("alerts", []) if a.get("state") == "firing"]
j = d.get("melder", {}).get("journal", {}); aw = d.get("melder", {}).get("alarmwege", {}).get("kanaele", [])
status = "PASS"
# Lauf-2-Kritik 2026-08-30: die Phase sagte PASS bei 4 unhealthy Containern und 98 % Swap —
# ein Bild, das nicht kippt, ist kein Melder. Jetzt kippen auch Knotenwerte.
unh = [f"{k['knoten']}:{u}" for k in gem for u in k.get("unhealthy", [])]
rst = [f"{k['knoten']}:{r}" for k in gem for r in k.get("restarting", [])]
heiss = [k["knoten"] for k in gem if (k.get("swap_pct") or 0) >= 90 or (k.get("disk_pct") or 0) >= 90]
if alter_h > 30 or fehlt or feuern or unh or rst or heiss: status = "WARN"
print(status)
print(f"{len(gem)}/{len(kn)} Knoten · {len(feuern)} Alerts · Journal {j.get('im_gate','?')}/{j.get('gesamt','?')} im Gate · Alarmwege {sum(1 for k in aw if k.get('ok'))}/{len(aw)} · Stand {d.get('stand','?')}"
      + (f" · FEHLT: {','.join(fehlt)}" if fehlt else "") + (f" · {alter_h:.0f} h alt" if alter_h > 30 else "")
      + (f" · unhealthy {','.join(unh)}" if unh else "") + (f" · restart {','.join(rst)}" if rst else "")
      + (f" · Swap/Platte>=90% {','.join(heiss)}" if heiss else ""))
PYEOF
)
  record "0.7.22 flottenbild" "$(echo "$FB_OUT" | head -1)" "$(echo "$FB_OUT" | tail -1)"
else
  record "0.7.22 flottenbild" "SKIP" "kein Flottenbild unter ~/.claude/flottenbild/ — Timer flottenbild.timer aktivieren (infra/host-maintenance)"
fi

# ── 0.7.28 GPU-Leerlauf: haelt ein Dienst Speicher, ohne gerufen zu werden? ──
# Anlass (platform#3352): auf der gx10 hielt vLLM 37,5 GB und hatte seit dem
# Hochfahren sechs Tage zuvor KEINE Anfrage gesehen. Aufgefallen ist das nicht
# im Betrieb, sondern weil der Owner nachfragte, als ein weiterer Dienst dazukam.
# Ein Bereitschaftsdienst haelt Speicher mit Absicht — sechs Tage Stille sind
# keine Bereitschaft mehr, sondern eine vergessene Sitzung.
#
# Der Melder redet ueber ssh mit zwei Knoten; das dauert. Deshalb kurzes
# Zeitlimit, und ein Abbruch ist eine LUECKE (SKIP), nie ein PASS.
if [ -f "$PLATFORM_DIR/tools/gpu_leerlauf.py" ]; then
  # Der Exit-Code kommt jetzt vom Melder selbst. Bis platform#3373 stand hier
  # `$(… | tail -1)` und `GL_RC=$?` las den Status von `tail` — also immer 0,
  # und damit fiel JEDE Lage in den PASS-Zweig: ein Zeitlimit (124) sah aus wie
  # "kein Dienst ueber der Schwelle". Die drei Zweige unten waren tot.
  warte_auf gpu-leerlauf; GL_RC=$ERNTE_RC
  GL_OUT=$(ernte gpu-leerlauf | tail -1)
  case "$GL_RC" in
    124) record "0.7.28 gpu-leerlauf" "SKIP" "Zeitlimit — Knoten nicht befragt, KEINE Entwarnung" ;;
    2)   record "0.7.28 gpu-leerlauf" "SKIP" "$GL_OUT" ;;
    1)   record "0.7.28 gpu-leerlauf" "WARN" "$GL_OUT" ;;
    *)   record "0.7.28 gpu-leerlauf" "PASS" "$GL_OUT" ;;
  esac
else
  record "0.7.28 gpu-leerlauf" "SKIP" "tools/gpu_leerlauf.py fehlt"
fi

# ── 0.7.29 Container-Speicher: OOM-Kill, anon-Anteil, Limit-Treffer je cgroup ──
# platform#3400: `docker stats` zeigte gotenberg bei 92 %, die cgroup bei 42 % anon —
# gemessen wird deshalb die cgroup (memory.stat/memory.events). Der Timer
# container-speicher.timer misst alle 15 min per ssh; hier wird NUR das abgelegte
# Ergebnis gelesen (kein ssh, keine Laufzeit). Ein stehender Timer ist ein Befund
# (Exit 2 -> WARN), nie ein PASS.
if [ -f "$PLATFORM_DIR/tools/container_speicher_melder.py" ]; then
  # Ohne Pipe: `$(… | tail -1)` liefert den Exit von tail (Lehre platform#3373).
  # `--lesen` gibt genau eine Zeile aus.
  CS_OUT=$(python3 "$PLATFORM_DIR/tools/container_speicher_melder.py" --lesen \
             --ergebnis-datei "$MELDER_DIR/container-speicher.json" 2>&1)
  CS_RC=$?
  case "$CS_RC" in
    0) record "0.7.29 container-speicher" "PASS" "$CS_OUT" ;;
    *) record "0.7.29 container-speicher" "WARN" "$CS_OUT" ;;
  esac
else
  record "0.7.29 container-speicher" "SKIP" "tools/container_speicher_melder.py fehlt"
fi

# ── 0.7.24 Registry-Erreichbarkeit: die Strecke, an der vier Deploys starben ──
# Am 2026-09-02 erreichte prod ghcr.io nur in 4 von 10 Versuchen, bei 10 von 10
# gegen github.com. Vier Deploys scheiterten; zwei Stunden spaeter war der Zustand
# von selbst vorbei und die Ursache nicht mehr bestimmbar, weil der entscheidende
# Schritt — ein Mitschnitt WAEHREND eines Fehlschlags — nichts mehr zu fassen hatte.
# Kein Melder sah diese Strecke: 0.7.11 fragt unsere eigenen Domains ab, keine
# Registry. registry-probe.sh misst sie jetzt dauerhaft auf prod und prod-b; hier
# wird nur gelesen. Ein STUMMER Rekorder ist selbst ein Befund — er meldet sonst nie
# ein Fenster und waere genau der blinde Melder, gegen den er gebaut wurde.
# Belegt: platform#2685, Kill-Gate-Messung fuer ADR-301.
if [[ -f "$PLATFORM_DIR/tools/registry_erreichbarkeit_melder.py" ]]; then
  RE_OUT=$(ernte registry-err | tail -1)
  RE_STATUS=$(sed -n 's/^RESULT: \([A-Z]*\).*/\1/p' <<< "$RE_OUT")
  # shellcheck disable=SC2001  # Regex-Klasse [A-Z]*, kein 1:1-Ersatz durch Parameter-Expansion
  record "0.7.24 registry-erreichbarkeit" "${RE_STATUS:-SKIP}" "$(sed 's/^RESULT: [A-Z]* — //' <<< "$RE_OUT")"
fi

# ── 0.7.25 Rotations-Faelligkeit: wann lief das zuletzt, und wer weiss es? ──
# Bis zum 2026-09-04 kannte das Inventar (47 Eintraege) fuer KEINEN davon einen
# letzten Rotationslauf — "quarterly" stand in der Tabelle, gemessen hat es nie
# jemand. Die Outline-Rotation lag seit dem 2026-08-26 offen (#2353), ohne dass
# irgendein Melder sie genannt haette. Diese Phase liest Inventar + Lauf-Log und
# gibt IMMER eine Zahl aus, auch bei "nichts zu tun" (MT-5): faellig / ohne
# Beleg / ohne Konsumenten / Altlasten in ~/shared.
#
# Zwei bewusste Entscheidungen: ein Lauf mit Status `offen` zaehlt NICHT als
# Lauf (sonst setzte ein Fehlschlag die Uhr zurueck), und die Altlasten-Zeile
# nennt nur DATEINAMEN und Alter aus der Schleuse — nie Inhalte (AD-9).
# Konzept: KONZ-dev-hub-005 REC-7, Umsetzung platform#2813.
if [[ -f "$PLATFORM_DIR/tools/rotate.py" ]]; then
  ROT_OUT=$(ernte rotation || true)
  case "$ROT_OUT" in
    OK:*)            record "0.7.25 rotation-faelligkeit" "PASS" "$ROT_OUT" ;;
    "WERT IM LOG"*)  record "0.7.25 rotation-faelligkeit" "WARN" "$ROT_OUT" "platform" ;;
    "")              record "0.7.25 rotation-faelligkeit" "SKIP" "Melder nicht gelaufen — keine Aussage zur Rotationslage" ;;
    *)               record "0.7.25 rotation-faelligkeit" "WARN" "$ROT_OUT" "platform" ;;
  esac
else
  record "0.7.25 rotation-faelligkeit" "SKIP" "tools/rotate.py fehlt in $PLATFORM_DIR"
fi

# ── 0.7.26 CI-Deckung: laeuft eine lokale Pruefung auch im CI, oder nie? ────
# Slug `ci-gate-narrower-than-local-test`, dreimal aufgetreten (robo-lab x2,
# chat-hub #79) und bis 2026-09-09 ohne Gate. Vergleicht die Makefile-Ziele des
# TARGET_REPO mit den Workflows: laeuft ein Ziel, das lokal ein Pruefwerkzeug
# ausfuehrt, niemals im CI, ist das der Befund. Advisory, Report-Werkzeug —
# Exit 0 immer, siehe tools/ci_deckung.py.
DECKUNG_CI_DIR="$GITHUB_DIR/$TARGET_REPO"
DECKUNG_CI_OUT=$(ernte ci-deckung || true)
case "$DECKUNG_CI_OUT" in
  "keine offene Deckungsluecke"*) record "0.7.26 ci-deckung" "PASS" "$DECKUNG_CI_OUT" "$TARGET_REPO" ;;
  "") record "0.7.26 ci-deckung" "WARN" "Melder nicht auswertbar — manuell: platform/tools/ci_deckung.py --repo $DECKUNG_CI_DIR" "$TARGET_REPO" ;;
  *) record "0.7.26 ci-deckung" "WARN" "$DECKUNG_CI_OUT" "$TARGET_REPO" ;;
esac

# ── 0.7.27 Sichtbarkeits-Drift: was haengt noch an achimdehnert/platform? ────
# platform ist PUBLIC und soll privat werden (KONZ-039, Auftrag #3234). Der Flip
# ist erst frei, wenn dieser Melder 7 Tage in Folge 0/0/1/0 zeigt (K5) — Aufrufer,
# Raw-Downloads (Laufzeit gesondert), Bausteine-Kopien, abgelaufene Konzept-Fristen.
# Zaehlt lokale Klone UND Code-Suche vereinigt: jede Methode allein lag im August
# zweimal daneben. Offline = "nicht messbar", nie Entwarnung.
SD_OUT=$(ernte sicht-drift || true)
case "$SD_OUT" in
  *"erreicht"*) record "0.7.27 sichtbarkeits-drift" "PASS" "$SD_OUT" "platform" ;;
  "") record "0.7.27 sichtbarkeits-drift" "WARN" "Melder nicht auswertbar — manuell: platform/tools/sichtbarkeits_drift_melder.py" "platform" ;;
  *) record "0.7.27 sichtbarkeits-drift" "WARN" "$SD_OUT" "platform" ;;
esac

# ── 0.7.20 Umgebung: wo stehe ich, und wer antwortet unter den Namen? ─────
# Alle anderen Phasen vergleichen Zusagen miteinander. Diese sagt der Sitzung,
# WO sie steht — und ob hinter einem deklarierten Namen die richtige Anwendung
# antwortet. Beides klang zu selbstverstaendlich, um gefragt zu werden, und war
# am 2026-08-30 viermal falsch: eine Sitzung hielt den Staging-Host fuer einen
# Entwicklungsrechner, meldete ein vorhandenes Staging als nicht existent, hielt
# eine fremde App hinter einem 200 fuer writing-hub und las ein E-Mail-Login aus
# einer OAuth-URL. Ein Statuscode belegt nicht, WER antwortet — der Titel schon.
UMG_OUT=$(ernte umgebung || true)
case "$UMG_OUT" in
  "")            record "0.7.20 umgebung" "WARN" "nicht ausgefuehrt — Standort ungeprueft" ;;
  *"UNBEKANNT"*) record "0.7.20 umgebung" "WARN" "$UMG_OUT" ;;
  *)             record "0.7.20 umgebung" "PASS" "$UMG_OUT" ;;
esac

# ── 0.9 Staging-Health (informativ) ─────────────────────────────────────────
# Sonde: `_staging_probe` am Vorlauf-Schnitt (dort als Funktion, weil ein
# Heredoc sich nicht als Argumentliste weiterreichen laesst).
STAGING=$(ernte staging)
record "0.9 staging" "PASS" "$STAGING"

# ── Summary (maschinenlesbar, Basis der Startklar-Checkliste Rows 1–7) ──────
echo ""
echo "| Phase | Status | Repo | Note |"
echo "|---|---|---|---|"
for i in "${!P_NAME[@]}"; do
  case "${P_STATUS[$i]}" in
    PASS) ICON="✅" ;;
    WARN) ICON="⚠️" ;;
    FAIL) ICON="❌" ;;
    # HINWEIS = ein herabgestufter Melder (#2690 K3): lesen, aber keine WARN-
    # Lautstaerke — solange die Trefferquote unter der Schwelle liegt, ist der
    # Melder selbst der Befund, nicht jede einzelne seiner Zeilen. Zaehlt NICHT
    # als WARN in dieser Tabelle.
    HINWEIS) ICON="ℹ️" ;;
    # SKIP ist KEIN Gruen. Die Phase konnte nicht pruefen — das ist weder ein
    # Befund noch eine Entwarnung, und genau diese dritte Moeglichkeit fehlte:
    # ein SKIP wurde als PASS verbucht und war in der Tabelle von einer echten
    # Pruefung nicht zu unterscheiden. Realfall 2026-08-23: `0.7.4` meldete
    # "keine Prio-Liste im Handover" gegen eine Datei mit sieben Prio-Zeilen,
    # eine seit 19 Tagen erledigte Prio blieb dadurch stehen (KONZ-platform-050).
    SKIP) ICON="◌" ;;
  esac
  printf '| %s | %s %s | %s | %s |\n' \
    "${P_NAME[$i]}" "$ICON" "${P_STATUS[$i]}" "${P_REPO[$i]:-$TARGET_REPO}" "${P_NOTE[$i]}"
done
echo ""

# ── Laufzeit: gesamt + die Phasen, die die Zeit fressen (platform#3373) ─────
# Bewusst eine eigene Zeile UNTER der Tabelle, nicht eine fuenfte Spalte darin:
# die Spalten `| Phase | Status | Repo | Note |` sind der Vertrag mit dem Skill-
# Text und dem Befund-Journal. Eine Sekundenzahl je Zeile waere ausserdem genau
# die Sorte Zweitinfo, die eine Tabelle im 80-Spalten-Terminal zerlegt.
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

# ── Befund-Journal: Alter je Befund + Fremd-Repo-Wecker (K1/K3, platform#2004) ──
# Der Runner meldete jede Sitzung dieselben Zeilen in derselben Lautstaerke. Ein
# Befund am zehnten Tag klang wie einer am ersten — und blieb entsprechend liegen
# (Messung: fuenf `[deploy-health]`-Issues, bis zu 10 Tage alt, keins bearbeitet).
# Das Journal ist bewusst NUR Gedaechtnis: es zaehlt und erinnert, es handelt nicht.
# Nie werfend — ein Melder, der die Sitzung aufhaelt, wird abgeschaltet.
if [ -f "$PLATFORM_DIR/tools/befund_journal.py" ]; then
  JOURNAL_OUT=$(
    for i in "${!P_NAME[@]}"; do
      printf '%s\t%s\t%s\t%s\t%s\n' "${P_NAME[$i]}" "${P_STATUS[$i]}" \
        "${P_REPO[$i]:-$TARGET_REPO}" "${P_NOTE[$i]}" "${P_UNGEPRUEFT[$i]:-}"
    done | python3 "$PLATFORM_DIR/tools/befund_journal.py" --aufnehmen \
             --repo "$TARGET_REPO" 2>/dev/null || true
  )
  if [ -n "$JOURNAL_OUT" ]; then
    echo "Befund-Journal (Alter je Befund · tools/befund_journal.py --bericht):"
    echo "$JOURNAL_OUT"
    echo ""
  fi
fi

# ── Befund-Sperren: welcher Befund ist schon in Arbeit (#3495 V1) ─────────────
# Zwei Sitzungen desselben Owners bearbeiteten am 2026-09-24 denselben Befund
# (#3465/#3466, #3467/#3468). `repo-session.sh start --befund <phase::repo>`
# sperrt den Schluessel; hier steht, welche Schluessel belegt sind. Nur Anzeige,
# keine Phase, kein WARN — nie werfend.
BEFUND_SPERREN=$(bash "$PLATFORM_DIR/tools/repo-session.sh" befunde 2>/dev/null | grep '^⛔' || true)
if [ -n "$BEFUND_SPERREN" ]; then
  echo "Befund-Sperren (repo-session.sh befunde):"
  echo "$BEFUND_SPERREN"
  echo ""
fi

# ── Ohne Entscheidung > 14 d: eigener Block (#2690 K3) ───────────────────────
# Ein Befund ohne Artefakt/Verzicht altert im Journal oben leise mit — hier
# steht er noch einmal separat, weil eine Liegezeit über der Frist ein anderer
# Befund ist als ein frischer: der Melder hat funktioniert, es fehlt an einer
# Entscheidung, nicht an einer Erkennung.
if [ -f "$PLATFORM_DIR/tools/melder_register_check.py" ]; then
  OHNE_ENTSCHEIDUNG_OUT=$(python3 "$PLATFORM_DIR/tools/melder_register_check.py" \
    --ohne-entscheidung --tage 14 --repo "$TARGET_REPO" 2>/dev/null || true)
  if [ -n "$OHNE_ENTSCHEIDUNG_OUT" ]; then
    echo "$OHNE_ENTSCHEIDUNG_OUT"
    echo ""
  fi
fi
if [ "$FAILED" -eq 1 ]; then
  echo "RESULT: FAIL — Session NICHT fortsetzen, bis alle ❌ behoben sind."
  exit 1
fi
SKIP_N=0
for s in "${P_STATUS[@]}"; do [ "$s" = "SKIP" ] && SKIP_N=$((SKIP_N+1)); done
if [ "$SKIP_N" -gt 0 ]; then
  echo "HINWEIS: $SKIP_N Phase(n) konnten nicht pruefen (◌ SKIP) — kein Befund, aber auch keine Entwarnung."
fi
echo "RESULT: OK — mechanische Phasen komplett; weiter mit 0.4.3 (Worktree), 0.8 (Modell-Tier), Phase 1–3."
