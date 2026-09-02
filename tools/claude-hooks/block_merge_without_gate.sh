#!/usr/bin/env bash
# PreToolUse(Bash) gate — blockt Merge und Publish, wenn gar kein CI gelaufen ist.
#
# GATE_HEADER (KONZ-038 D8):
#   "slug": "no-checks-reported-read-as-green"
#   "mode": "blocking"
#   "owner": "achim"
#   "last_drill_pass": "2026-08-25"
#   "evidence": "tools/claude-hooks/tests/test_block_merge_without_gate.py"
#
# Hintergrund: Retro 3106ae Befund #1. `gh pr checks 51` meldete
# "no checks reported"; das wurde als gruenes Licht gelesen, der PR gemergt und
# `iil-aifw==0.13.0` nach PyPI veroeffentlicht. Erst die Retro fand, dass das CI
# jenes Repos seit sechs Tagen VOR jedem Job scheiterte (Workflow-Referenz mit
# einem Pfadteil zu viel, aifw#53). Eine leere Pruefliste sieht aus wie Ruhe und
# heisst "hier prueft nichts".
#
# Warum ein eigener Slug und nicht der `claim-before-cheapest-check`-Scanner:
# jener liest die SPRACHE einer Behauptung. Hier ist nichts behauptet worden —
# es wurde gehandelt. Die Familie ist fuer einen Textscanner unsichtbar
# (Owner-Entscheid 2026-08-25 "ausweiten", umgesetzt als eigenes Gate).
#
# Verhalten:
#   - feuert auf `gh pr merge` und auf `publish-package.sh`
#   - `--admin` passiert NUR, wenn am PR ein menschlicher Freigabe-Kommentar
#     steht (s. AUSWEITUNG 2026-08-31)
#   - blockt, wenn der letzte Lauf auf dem Default-Branch `failure` ist
#   - blockt, wenn es GAR KEINEN Lauf gibt — das ist der eigentliche Fall
#   - blockt, wenn der PR SELBST null Check-Runs hat (s.u.)
#   - FAIL-OPEN: kein gh, kein Netz, Repo nicht bestimmbar -> exit 0
#
# AUSWEITUNG 2026-08-26 (writing-hub, Retro fdd368): das Gate pruefte
# ausschliesslich den Default-Branch. Ein PR, dessen eigener Head-SHA NULL
# Check-Runs hat, fiel bei gesundem `main` glatt durch — genau der Fall, der
# an dem Tag eintrat: `gh pr checks` meldete "no checks reported", meine
# Pruefschleife las das als gruen, der Merge scheiterte danach mit BLOCKED.
# Ursache war ein GitHub-Actions-Ausfall; der Hook haette es vorher sagen
# koennen und schwieg, weil er woanders hinsah. Ein Gate, das weniger prueft
# als sein Name verspricht, ist die Klasse `gate-modul-prueft-weniger-als-sein-name`.
#
# AUSWEITUNG 2026-08-31 (Gate-Deckungs-Triage, platform#2234): `--admin` war ein
# Freifahrschein — "das ist der ausdrueckliche, benannte Bypass eines Menschen".
# Vier Retro-Faelle widerlegen die Annahme: der Bypass lief auf generische
# Zustimmung ("go", "mache es autonom") ohne durables Wort am Artefakt
# (f4a546 #2, dms-hub C4, dev-hub-8f9a23 #4: 10 Dependabot-PRs per --admin auf
# "1 --admin" im Chat, 62f875 #3). Deckt damit die Slugs
# `merge-bypass-without-explicit-word` (4x) und `gate-approval-needs-pr-comment`
# (4x): --admin passiert nur noch, wenn am PR ein Kommentar eines MENSCHEN
# (Login ohne "bot") steht, der die Freigabe benennt (freigabe/--admin/bypass).
# Der Kommentar ist das durable Artefakt, das ein Auditor spaeter findet — eine
# Chat-Freigabe wird also VOR dem Merge einmal an den PR geschrieben, z.B.:
#   gh pr comment <N> --body "Freigabe --admin (Owner-Wort: '<zitat>')"
# GRENZE (fail-open, dokumentiert): ist die PR-Nummer aus dem Kommando nicht
# extrahierbar (Merge per URL/Branch), passiert --admin ungefragt wie zuvor.
set -uo pipefail

input="$(cat 2>/dev/null)" || exit 0
cmd="$(printf '%s' "$input" | tr '\n' ' ')"

printf '%s' "$cmd" | grep -qE 'gh pr merge|publish-package\.sh' || exit 0
# --admin ist erst nach dem Freigabe-Kommentar-Check unten ein Bypass.
ADMIN=0
printf '%s' "$cmd" | grep -q -- '--admin' && ADMIN=1
command -v gh >/dev/null 2>&1 || exit 0

# Repo bestimmen: explizites --repo hat Vorrang, sonst das Verzeichnis.
repo="$(printf '%s' "$cmd" | grep -oE '\-\-repo [A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' | head -1 | awk '{print $2}')"
if [ -z "$repo" ]; then
  dir="$(printf '%s' "$cmd" | grep -oE "(cd|pushd)[[:space:]]+[^;&|)\"']+" | tail -1 | sed -E 's/^(cd|pushd)[[:space:]]+//; s/[[:space:]]+$//')"
  dir="${dir:-$PWD}"; dir="${dir%\"}"; dir="${dir#\"}"
  [ -d "$dir" ] || exit 0
  repo="$(cd "$dir" 2>/dev/null && gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
fi
[ -n "$repo" ] || exit 0

melde() {
  reason="${1//\"/\\\"}"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
  exit 0
}

pr="$(printf '%s' "$cmd" | grep -oE 'gh pr merge[[:space:]]+[0-9]+' | head -1 | grep -oE '[0-9]+$')"

# AUSWEITUNG 2026-08-31: --admin nur mit durablem Freigabe-Kommentar am PR.
if [ "$ADMIN" = "1" ]; then
  [ -n "$pr" ] || exit 0  # PR-Nummer nicht extrahierbar -> fail-open (Grenze im Header)
  kommentare="$(gh pr view "$pr" --repo "$repo" --json comments \
    --jq '.comments[] | "\(.author.login)\t\(.body | gsub("\n"; " "))"' 2>/dev/null)" || exit 0
  if printf '%s\n' "$kommentare" | awk -F'\t' \
      'tolower($1) !~ /bot/ && tolower($0) ~ /freigabe|admin|bypass/ {gefunden=1} END{exit gefunden?0:1}'; then
    exit 0  # benannter, durabel abgelegter Bypass — kein Fall fuer dieses Gate
  fi
  melde "⛔ --admin-Merge geblockt: PR #${pr} (${repo}) traegt KEINEN menschlichen Freigabe-Kommentar (Gates merge-bypass-without-explicit-word + gate-approval-needs-pr-comment). Ein Bypass braucht ein benanntes Wort UND ein durables Artefakt am PR — eine Chat-Zustimmung sieht ein Auditor nie (Realfall dev-hub 2026-08-25: 10 Dependabot-PRs per --admin, Freigabe nur im Chat). Erst die Freigabe ablegen: gh pr comment ${pr} --repo ${repo} --body 'Freigabe --admin (Owner-Wort: <zitat>)' — dann erneut mergen. Liegt kein Owner-Wort fuer GENAU diesen Bypass vor, ist der naechste Schritt die Frage an den Owner, nicht die staerkere Flag."
fi

zweig="$(gh repo view "$repo" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null || true)"
[ -n "$zweig" ] || exit 0

laeufe="$(gh run list --repo "$repo" --branch "$zweig" --limit 5 --json conclusion,status --jq '[.[]|select(.status=="completed")|.conclusion] | join(",")' 2>/dev/null)" || exit 0

if [ -z "$laeufe" ]; then
  melde "⛔ Merge/Publish geblockt: ${repo} hat auf ${zweig} KEINEN abgeschlossenen CI-Lauf (Gate no-checks-reported-read-as-green). Eine leere Pruefliste heisst 'hier prueft nichts', nicht 'nichts zu beanstanden' — Realfall aifw#53: sechs Tage tote Workflow-Referenz, in dem Fenster ging 0.13.0 nach PyPI. Pruefen: gh run list --repo ${repo} --branch ${zweig} --limit 3"
fi

# Der PR selbst: hat sein Head-SHA ueberhaupt Check-Runs?
#
# Nicht der Rollup (`gh pr checks`), sondern die Zaehlung am Commit — der Rollup
# antwortet mit einer Prosa-Zeile, die sich als "0 rote, 0 offene" lesen laesst.
# `total_count` kennt diese Zweideutigkeit nicht.
if [ -n "$pr" ]; then
  sha="$(gh pr view "$pr" --repo "$repo" --json headRefOid --jq .headRefOid 2>/dev/null || true)"
  if [ -n "$sha" ]; then
    anzahl="$(gh api "repos/${repo}/commits/${sha}/check-runs" --jq .total_count 2>/dev/null || true)"
    if [ "$anzahl" = "0" ]; then
      melde "⛔ Merge geblockt: PR #${pr} (${repo}) hat auf seinem Head-Commit ${sha:0:7} NULL Check-Runs (Gate no-checks-reported-read-as-green). 'no checks reported' ist ein Befund, kein Zustand — kein Required Check ist gelaufen, der PR bleibt BLOCKED, ohne dass irgendwo etwas rot wird. Erst nachsehen, ob CI ueberhaupt laeuft: gh run list --repo ${repo} --limit 3 — und bei flaechendeckender Stille https://www.githubstatus.com pruefen, bevor im Repo gesucht wird."
    fi
  fi
fi

erster="${laeufe%%,*}"
if [ "$erster" = "failure" ]; then
  melde "⛔ Merge/Publish geblockt: der letzte abgeschlossene CI-Lauf auf ${repo}@${zweig} ist FAILURE (Gate no-checks-reported-read-as-green). Erst die Ursache ansehen — vorbestehend ist eine Feststellung, keine Freigabe: gh run list --repo ${repo} --branch ${zweig} --limit 3"
fi

exit 0
