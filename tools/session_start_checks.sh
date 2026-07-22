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
PLATFORM_DIR="$GITHUB_DIR/platform"
TARGET_REPO="${1:-platform}"
PROD_HOST="88.198.191.108"
STAGING_HOST="88.99.38.75"

declare -a P_NAME P_STATUS P_NOTE
FAILED=0

record() { # record <phase> <PASS|WARN|FAIL> <note> — Pipes raus, sonst bricht die Summary-Tabelle
  P_NAME+=("$1"); P_STATUS+=("$2"); P_NOTE+=("$(echo "$3" | tr '|' '/')")
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
  record "0.4 repo-sync" "WARN" "${GUARD_NOTE}${SYNC_RESULTS# } (GUARD = nicht angefasst, fremde Session möglich)"
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
  record "0.4.1 reflex" "PASS" "v${REFLEX_VER}, $TARGET_REPO ohne reflex.yaml — Review übersprungen (by design)"
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
if [ -n "$DEPLOY_WAITING" ]; then
  record "0.7 deploy-scan" "WARN" "waiting>24h:${DEPLOY_WAITING} — Gate blockiert die Concurrency-Group, Folge-Deploys erreichen Prod NICHT; altes Gate mit state=rejected beantworten${DEPLOY_FAILS:+ · failure:$DEPLOY_FAILS} (${COVERAGE})"
elif [ -n "$DEPLOY_FAILS" ]; then
  record "0.7 deploy-scan" "WARN" "failure:${DEPLOY_FAILS} — Logs lesen + User informieren (run-conclusion ≠ Änderung live) (${COVERAGE})"
elif [ -z "$WAIT_CUTOFF" ]; then
  # F3: ohne Cutoff lief die waiting-Pruefung gar nicht — kein PASS behaupten.
  record "0.7 deploy-scan" "WARN" "degraded: WAIT_CUTOFF leer (kein GNU-date?) — haengende Approval-Gates wurden NICHT geprueft; kein failure in ${COVERAGE}"
elif [ -n "$DEPLOY_SKIPPED" ]; then
  record "0.7 deploy-scan" "WARN" "unvollstaendig: ${COVERAGE} — kein failure/waiting in den geprueften, die uebrigen sind ungeprueft${DEPLOY_REJECTED:+ · bewusst abgelehnte Freigabe (kein Befund):$DEPLOY_REJECTED}"
else
  record "0.7 deploy-scan" "PASS" "kein failure, kein haengendes Approval-Gate (${COVERAGE})${DEPLOY_REJECTED:+ · bewusst abgelehnte Freigabe (kein Befund):$DEPLOY_REJECTED}"
fi

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
echo "| Phase | Status | Note |"
echo "|---|---|---|"
for i in "${!P_NAME[@]}"; do
  case "${P_STATUS[$i]}" in
    PASS) ICON="✅" ;;
    WARN) ICON="⚠️" ;;
    FAIL) ICON="❌" ;;
  esac
  printf '| %s | %s %s | %s |\n' "${P_NAME[$i]}" "$ICON" "${P_STATUS[$i]}" "${P_NOTE[$i]}"
done
echo ""
if [ "$FAILED" -eq 1 ]; then
  echo "RESULT: FAIL — Session NICHT fortsetzen, bis alle ❌ behoben sind."
  exit 1
fi
echo "RESULT: OK — mechanische Phasen komplett; weiter mit 0.4.3 (Worktree), 0.8 (Modell-Tier), Phase 1–3."
