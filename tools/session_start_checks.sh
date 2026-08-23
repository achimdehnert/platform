#!/usr/bin/env bash
# session_start_checks.sh — deterministischer Runner für die mechanischen
# /session-start-Phasen (0.0–0.9 ohne 0.3*/0.4.3/0.8 — *0.3 existiert nicht,
# 0.4.3/0.8 sind Judgment-Phasen und bleiben im Skill-Text).
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
PROD_HOST="88.198.191.108"
STAGING_HOST="88.99.38.75"

declare -a P_NAME P_STATUS P_NOTE P_REPO P_UNGEPRUEFT
FAILED=0

# record <phase> <PASS|WARN|FAIL> <note> [ziel-repos] [ungeprueft-repos]
#   Pipes raus, sonst bricht die Summary-Tabelle.
#   Das 4. Argument nennt die Repos, um die es in dieser Zeile GEHT — nicht das
#   Repo, in dem die Sitzung laeuft. Ohne Angabe ist es $TARGET_REPO, denn die
#   meisten Phasen pruefen die eigene Umgebung. Genau diese Unterscheidung fehlte
#   bis 2026-08-16 (platform#2004): ein roter Deploy in `cad-hub` war eine WARN-Zeile
#   in einer platform-Sitzung, und der Befund blieb dort liegen — fuenf offene
#   `[deploy-health]`-Issues, alle in platform, alle ueber andere Repos, keins gefixt.
#
#   Das 5. Argument nennt Repos, die diese Phase NICHT beurteilen konnte. Ohne das
#   sieht eine Abdeckungsluecke im Journal aus wie eine Heilung: `trading-hub` ist
#   fuer 0.7 regelmaessig nicht abfragbar — der Befund waere jedes Mal still
#   verschwunden und beim naechsten erfolgreichen Scan als neu wieder aufgetaucht,
#   ewig jung. Der teuerste Fehler, den ein Melder-Gedaechtnis machen kann.
record() {
  P_NAME+=("$1"); P_STATUS+=("$2"); P_NOTE+=("$(echo "$3" | tr '|' '/')")
  P_REPO+=("${4:-$TARGET_REPO}")
  P_UNGEPRUEFT+=("${5:-}")
  [ "$2" = "FAIL" ] && FAILED=1
  printf '  [%s] %s — %s\n' "$2" "$1" "$3"
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
  LINKS=$(bash "$PLATFORM_DIR/scripts/sync-workflows.sh" 2>&1 | grep -cE "LINK|REPLACE")
  FACTS=$(python3 "$PLATFORM_DIR/scripts/gen_project_facts.py" 2>&1 | grep -cE "✅|⚠️|SKIP")
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
for repo in "$TARGET_REPO" mcp-hub risk-hub; do
  [ -d "$GITHUB_DIR/$repo" ] || continue
  SYNC_RESULTS="$SYNC_RESULTS $(sync_repo "$GITHUB_DIR/$repo")"
done
if echo "$SYNC_RESULTS" | grep -q "GUARD\|pull-fail"; then
  # Nur die Repos, die tatsaechlich GUARD/pull-fail tragen — nicht die geprueften.
  SYNC_BETROFFEN=$(echo "$SYNC_RESULTS" | tr ' ' '\n' \
    | grep -E "GUARD|pull-fail" | cut -d: -f1 | sort -u | tr '\n' ' ')
  record "0.4 repo-sync" "WARN" "${GUARD_NOTE}${SYNC_RESULTS# } (GUARD = nicht angefasst, fremde Session möglich)" "${SYNC_BETROFFEN% }"
else
  record "0.4 repo-sync" "PASS" "${GUARD_NOTE}${SYNC_RESULTS# }"
fi

if [ -n "$PARALLEL_SESSIONS" ]; then
  n=$(printf '%s\n' "$PARALLEL_SESSIONS" | grep -c .)
  record "0.4 parallel-sessions" "WARN" "$n aktive Session(s) auf $TARGET_REPO — vor Merge/Deploy abgleichen"
  printf '%s\n' "$PARALLEL_SESSIONS"
else
  record "0.4 parallel-sessions" "PASS" "keine andere aktive Session auf $TARGET_REPO"
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
    record "0.4.1 reflex" "PASS" "v${REFLEX_VER}, review ohne BLOCK"
  else
    record "0.4.1 reflex" "WARN" "v${REFLEX_VER}, BLOCK-Findings — vor Weiterarbeit fixen (Log: reflex review all $TARGET_REPO)"
  fi
  rm -f /tmp/ssc_reflex.$$
else
  record "0.4.1 reflex" "SKIP" "v${REFLEX_VER}, $TARGET_REPO ohne reflex.yaml — Review übersprungen (by design)"
fi

# ── 0.4.2 ADR-Schema-Validierung ────────────────────────────────────────────
if command -v iil-adrfw >/dev/null 2>&1; then
  ADR_OUT=$(iil-adrfw validate "$PLATFORM_DIR/docs/adr/" 2>&1 | tail -3 | tr '\n' ' ')
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
  N_SEC=$(ls -A ~/shared/inbox/secrets 2>/dev/null | wc -l)
  record "0.5.1 secret-zone" "WARN" "${N_SEC} Secret(s) in ~/shared/inbox/secrets — nach ~/.secrets reconcilen (KONZ-010)"
else
  record "0.5.1 secret-zone" "PASS" "Drop-Zone leer"
fi

# ── 0.5.2 Schleuse: was liegt zu lange? (KONZ-045, warn) ────────────────────
# Die Schleuse ist ein Foerderband, kein Regal. Ohne diese Zeile faellt erst auf,
# dass sie ein Lager geworden ist, wenn jemand hinsieht -- gemessen 2026-08-18:
# 247 Eintraege, 3,8 GB, der aelteste 119 Tage alt.
SCHLEUSE_OUT=$(python3 "$GITHUB_DIR/platform/tools/schleuse.py" 2>/dev/null | tail -1)
SCHLEUSE_N=$(echo "$SCHLEUSE_OUT" | grep -oE '^Zusammenfassung: [0-9]+' | grep -oE '[0-9]+' || echo 0)
if [ "${SCHLEUSE_N:-0}" -gt 0 ]; then
  record "0.5.2 schleuse" "WARN" "$SCHLEUSE_OUT — Bericht: platform/tools/schleuse.py (KONZ-045)"
else
  record "0.5.2 schleuse" "PASS" "nichts ueberfaellig"
fi

# ── 0.6 Deploy-Infrastruktur (ADR-156) ──────────────────────────────────────
ADR156_OUT=$(bash "$GITHUB_DIR/mcp-hub/scripts/verify-adr156.sh" 2>&1 | tail -2 | tr '\n' ' ')
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
OWNER=$(git -C "$PLATFORM_DIR" remote get-url origin | sed -E 's#.*[:/]([^/]+)/.*#\1#')
# ausschreibungs-hub fehlte hier (2026-07-21 ergaenzt) — iilgmbh-Repos loesen
# ueber den Transfer-Redirect auch unter $OWNER auf, geprueft fuer risk-hub.
DEPLOY_REPOS="risk-hub billing-hub cad-hub coach-hub trading-hub travel-beat weltenhub wedding-hub pptx-hub ausschreibungs-hub"
DEPLOY_FAILS=""; DEPLOY_WAITING=""; DEPLOY_REJECTED=""; DEPLOY_SKIPPED=""; N_SCANNED=0
# Leerer Cutoff (kein GNU-date) wuerde die waiting-Erkennung still abschalten —
# das Ergebnis waere ein PASS, das eine nie gelaufene Pruefung als bestanden
# ausgibt. Deshalb wird der Zustand unten als degraded gemeldet, nicht verschluckt.
WAIT_CUTOFF=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "")
for r in $DEPLOY_REPOS; do
  # (1) Letzter Run: conclusion + id. `--limit 1` genuegt, seit die waiting-Suche
  #     nicht mehr aus diesem Fenster gesiebt wird.
  OUT=$(gh run list -R "$OWNER/$r" --workflow Deploy --limit 1 --json databaseId,conclusion \
        --jq '"\(.[0].conclusion // "none") \(.[0].databaseId // "none")"' 2>/dev/null)
  # Leere Antwort = Repo nicht abfragbar (umbenannt, uebertragen ohne Redirect,
  # Token-Scope, API-Fehler). Frueher wurde still weitergesprungen, waehrend die
  # Erfolgsmeldung weiter die volle Repo-Zahl nannte — ein Repo konnte damit aus
  # der Abdeckung fallen, ohne dass die Ausgabe sich aenderte. Jetzt namentlich.
  if [ -z "$OUT" ]; then
    DEPLOY_SKIPPED="$DEPLOY_SKIPPED $r"
    continue
  fi
  N_SCANNED=$((N_SCANNED + 1))
  read -r C ID <<EOF
$OUT
EOF
  # (2) Haengende Gates server-seitig, fenster- und frequenzunabhaengig.
  #     `waiting` ist ein von gh validierter --status-Wert (geprueft 2026-07-22:
  #     ein ungueltiger Wert bricht mit "invalid argument ... valid values are
  #     {...|waiting|...}" ab). Leeres Ergebnis -> "none".
  W=$(gh run list -R "$OWNER/$r" --workflow Deploy --status waiting --limit 100 \
      --json createdAt --jq '[.[].createdAt]|min // "none"' 2>/dev/null)
  [ -z "$W" ] && W="none"
  if [ "$C" = "failure" ] && [ "$ID" != "none" ]; then
    # Zweiter Call nur im failure-Fall (nicht pro Repo) — abgelehnte Freigabe
    # vom echten Fehlschlag trennen, s. Kommentar oben.
    REJ=$(gh api "repos/$OWNER/$r/actions/runs/$ID/approvals" \
          --jq '[.[]|select(.state=="rejected")]|length' 2>/dev/null)
    if [ "${REJ:-0}" -gt 0 ] 2>/dev/null; then
      DEPLOY_REJECTED="$DEPLOY_REJECTED $r"
    else
      DEPLOY_FAILS="$DEPLOY_FAILS $r"
    fi
  fi
  # erst ab 24h melden: ein frisches Gate ist der Normalfall, kein Befund
  if [ "$W" != "none" ] && [ -n "$WAIT_CUTOFF" ] && [[ "$W" < "$WAIT_CUTOFF" ]]; then
    DEPLOY_WAITING="$DEPLOY_WAITING $r"
  fi
done
N_DEPLOY_REPOS=$(echo $DEPLOY_REPOS | wc -w)
# Abdeckung immer mitschreiben (gescannt/gesamt) statt nur die Soll-Zahl zu nennen.
COVERAGE="${N_SCANNED}/${N_DEPLOY_REPOS} Repos${DEPLOY_SKIPPED:+ · NICHT abfragbar:$DEPLOY_SKIPPED}"
# Betroffene Repos maschinenlesbar mitgeben (K1, platform#2004): failure UND waiting
# sind Befunde ueber ein FREMDES Repo — sie gehoeren dorthin, nicht in die
# platform-Prosa. Die nicht abfragbaren stehen getrennt, damit das Journal eine
# Abdeckungsluecke nicht als Heilung verbucht.
DEPLOY_BETROFFEN=$(echo "$DEPLOY_WAITING $DEPLOY_FAILS" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' ')
if [ -n "$DEPLOY_WAITING" ]; then
  record "0.7 deploy-scan" "WARN" "waiting>24h:${DEPLOY_WAITING} — Gate blockiert die Concurrency-Group, Folge-Deploys erreichen Prod NICHT; altes Gate mit state=rejected beantworten${DEPLOY_FAILS:+ · failure:$DEPLOY_FAILS} (${COVERAGE})" "${DEPLOY_BETROFFEN% }" "$DEPLOY_SKIPPED"
elif [ -n "$DEPLOY_FAILS" ]; then
  record "0.7 deploy-scan" "WARN" "failure:${DEPLOY_FAILS} — Logs lesen + User informieren (run-conclusion ≠ Änderung live) (${COVERAGE})" "${DEPLOY_BETROFFEN% }" "$DEPLOY_SKIPPED"
elif [ -z "$WAIT_CUTOFF" ]; then
  # F3: ohne Cutoff lief die waiting-Pruefung gar nicht — kein PASS behaupten.
  record "0.7 deploy-scan" "WARN" "degraded: WAIT_CUTOFF leer (kein GNU-date?) — haengende Approval-Gates wurden NICHT geprueft; kein failure in ${COVERAGE}" "$TARGET_REPO" "$DEPLOY_REPOS"
elif [ -n "$DEPLOY_SKIPPED" ]; then
  record "0.7 deploy-scan" "WARN" "unvollstaendig: ${COVERAGE} — kein failure/waiting in den geprueften, die uebrigen sind ungeprueft${DEPLOY_REJECTED:+ · bewusst abgelehnte Freigabe (kein Befund):$DEPLOY_REJECTED}" "$TARGET_REPO" "$DEPLOY_SKIPPED"
else
  record "0.7 deploy-scan" "PASS" "kein failure, kein haengendes Approval-Gate (${COVERAGE})${DEPLOY_REJECTED:+ · bewusst abgelehnte Freigabe (kein Befund):$DEPLOY_REJECTED}"
fi

# ── 0.7.1 deploy.sh Git↔Host-Drift ──────────────────────────────────────────
# Die Host-Kopie /opt/scripts/deploy.sh wird von Hand verteilt und lief messbar
# auseinander (2026-07-25: prod eine Revision hinter Git+Staging, u.a. ohne den
# override-Fix aus platform#1075). Ein grüner Deploy beweist NICHT, dass der Host
# das aktuelle Skript ausführt — und das Skript kann sich nicht selbst prüfen,
# der Check muss von außen kommen. Deshalb hier, wo er jede Session einmal läuft.
DRIFT_OUT=$("$PLATFORM_DIR/tools/deploy-script-drift.sh" --quiet 2>/dev/null | tail -1 || true)
case "$DRIFT_OUT" in
  "RESULT: OK"*)         record "0.7.1 deploy-script" "PASS" "${DRIFT_OUT#RESULT: OK — }" ;;
  "RESULT: DRIFT"*)      record "0.7.1 deploy-script" "WARN" "${DRIFT_OUT#RESULT: DRIFT — }" ;;
  "RESULT: UNGEPRUEFT"*) record "0.7.1 deploy-script" "WARN" "${DRIFT_OUT#RESULT: UNGEPRUEFT — }" ;;
  *)                     record "0.7.1 deploy-script" "WARN" "Drift-Check nicht auswertbar — manuell: platform/tools/deploy-script-drift.sh" ;;
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
CRON_OUT=$(python3 "$PLATFORM_DIR/tools/cron_melder_check.py" --quiet 2>/dev/null | tail -1 || true)
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
  STALE_OUT=$(cd "$STALE_REPO_DIR" && python3 "$PLATFORM_DIR/tools/handover_stale_reference_check.py" AGENT_HANDOVER.md 2>/dev/null || true)
  STALE_N=$(echo "$STALE_OUT" | grep -c '^STALE' || true)
  case "$STALE_OUT" in
    PASS*)  record "0.7.4 prio-referenzen" "PASS" "$(echo "$STALE_OUT" | head -1 | cut -c1-120)" ;;
    SKIP*)  record "0.7.4 prio-referenzen" "SKIP" "keine Prio-Liste im Handover — nichts geprueft" ;;
    STALE*) record "0.7.4 prio-referenzen" "WARN" "$STALE_N Prio-Referenz(en) zeigen auf Erledigtes — Prio nachziehen VOR Arbeitsbeginn: $(echo "$STALE_OUT" | grep '^STALE' | head -3 | awk '{print $2}' | tr '\n' ' ')" ;;
    *)      record "0.7.4 prio-referenzen" "WARN" "Prio-Referenz-Check nicht auswertbar — manuell: platform/tools/handover_stale_reference_check.py" ;;
  esac
else
  record "0.7.4 prio-referenzen" "SKIP" "$TARGET_REPO ohne AGENT_HANDOVER.md — nichts geprueft"
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
OPTDRIFT_OUT=$("$PLATFORM_DIR/tools/opt-platform-drift.sh" --quiet 2>/dev/null | tail -1 || true)
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
HOOKDRIFT_OUT=$("$PLATFORM_DIR/tools/hook-dist-drift.sh" --quiet 2>/dev/null | tail -1 || true)
case "$HOOKDRIFT_OUT" in
  "RESULT: OK"*)         record "0.7.5 hook-dist" "PASS" "${HOOKDRIFT_OUT#RESULT: OK — }" ;;
  "RESULT: DRIFT"*)      record "0.7.5 hook-dist" "WARN" "${HOOKDRIFT_OUT#RESULT: DRIFT — }" ;;
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
LESEFLAECHE_OUT=$(python3 "$PLATFORM_DIR/tools/hooks/befund_leseflaeche.py" 2>/dev/null || true)
if [ -n "$LESEFLAECHE_OUT" ]; then
  record "0.7.6 leseflaeche" "WARN" "$(echo "$LESEFLAECHE_OUT" | head -1 | tr '|' '/')"
  echo "$LESEFLAECHE_OUT" | tail -n +2
else
  record "0.7.6 leseflaeche" "PASS" "keine unbestaetigten Melder-Befunde"
fi

# ── 0.7.7 Gate-Wirkung: Rueckfaelle nach dem Bau (platform, 2026-08-20) ─────
# Der Loop hatte drei Messpunkte und eine Luecke: die Registry sagt "gebaut",
# der Drill sagt "feuert", `retro_kpis.py` zaehlt Slugs INSGESAMT. Keiner davon
# trennt am Bau-Datum — und damit sah ein Gate mit 16 Rueckfaellen seit dem Bau
# aus wie eines, das gestern entstand. Gemessen am 2026-08-20 ueber 82 Retros:
# 8 von 20 Gates sind rueckfaellig, `claim-before-cheapest-check` 16x seit dem
# 2026-08-02 — verdrahtet als Stop-Hook, Drill gruen, Verhalten unveraendert.
#
# Ein Rueckfall ist ein Befund UEBER das Gate, nicht die N-te Wiederholung des
# Slugs. Er steht hier, weil der Sitzungsstart der einzige Ort ist, den jede
# Sitzung durchlaeuft — die Retro laeuft seltener als der Rueckfall passiert.
#
# FAIL-OPEN wie 0.7.6: `|| true`, damit ein kaputter Melder nicht den Start blockt.
WIRKUNG_OUT=$(python3 "$PLATFORM_DIR/tools/gate_wirkung.py" --kurz 2>/dev/null || true)
if [ -n "$WIRKUNG_OUT" ]; then
  record "0.7.7 gate-wirkung" "WARN" "$(echo "$WIRKUNG_OUT" | head -1 | tr '|' '/')"
  echo "$WIRKUNG_OUT" | tail -n +2
else
  record "0.7.7 gate-wirkung" "PASS" "kein Gate rueckfaellig"
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
WACH_OUT=$(timeout 120 python3 "$PLATFORM_DIR/tools/zeitplan_wach.py" --kurz 2>/dev/null || true)
if [ -n "$WACH_OUT" ]; then
  record "0.7.8 zeitplan-wache" "WARN" "$(echo "$WACH_OUT" | head -1 | tr '|' '/')"
  echo "$WACH_OUT" | tail -n +2
else
  record "0.7.8 zeitplan-wache" "PASS" "kein Zeitplan still abgeschaltet"
fi

# ── 0.7.9 Gate-Deckung: GATE-PFLICHT gezaehlt, nie eingeloest ───────────────
# retro_kpis eskaliert jeden Slug >=2 zur GATE-PFLICHT. Die Pflicht wird gezaehlt,
# ihre Einloesung nirgends — 16 Slugs sind mehrfach aufgetreten und tragen weder
# Gate noch declined-Eintrag. Das ist die stille Schwester des Rueckfalls (0.7.7):
# dort versagt ein gebautes Gate, hier entstand nie eines.
DECKUNG_OUT=$(python3 "$PLATFORM_DIR/tools/gate_deckung.py" --kurz 2>/dev/null || true)
if [ -n "$DECKUNG_OUT" ]; then
  record "0.7.9 gate-deckung" "WARN" "$(echo "$DECKUNG_OUT" | head -1 | tr '|' '/')"
  echo "$DECKUNG_OUT" | tail -n +2
else
  record "0.7.9 gate-deckung" "PASS" "keine offene Gate-Pflicht"
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
KZ_OUT=$(timeout 300 python3 "$PLATFORM_DIR/tools/kennzahl_verfall.py" --kurz 2>/dev/null || true)
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
ERR_OUT=$(timeout 120 python3 "$PLATFORM_DIR/tools/erreichbarkeit_melder.py" --kurz 2>/dev/null || true)
case "$ERR_OUT" in
  ""|*"alle antworten"*) record "0.7.11 erreichbarkeit" "PASS" "${ERR_OUT:-nicht ausgefuehrt}" ;;
  *) record "0.7.11 erreichbarkeit" "WARN" "$ERR_OUT" ;;
esac

# ── 0.9 Staging-Health (informativ) ─────────────────────────────────────────
STAGING=$(python3 - "$STAGING_HOST" <<'PYEOF'
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
)
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
