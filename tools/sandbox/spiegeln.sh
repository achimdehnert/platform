#!/usr/bin/env bash
# spiegeln.sh — Pilot-Repo nach iilsandbox spiegeln oder auffrischen (ADR-308 §4.3, platform#3685).
#
#   tools/sandbox/spiegeln.sh <owner/repo>…
#
# Je Repo, in dieser Reihenfolge, Abbruch beim ersten Fehler:
#   1. Kopie nur des Standard-Branches (bare, ohne Tags)
#   2. Secret-Scan ueber die volle Historie dieser Kopie (geheimnis_scan.py)
#   3. Spiegel privat anlegen, falls er fehlt; Actions aus, privat pruefen
#   4. Standard-Branch pushen; der Spiegel folgt dem Original (Auffrischen ueberschreibt)
#   5. Dependabot-PRs schliessen und ihre Branches loeschen (Owner-Entscheid D1 a, 2026-10-05):
#      Versions-Updates laufen trotz Actions aus, ausgeloest von der dependabot.yml des Originals
#   6. Pruefen, dass nur der Standard-Branch bleibt
# Der Owner-Auftrag (2026-10-05): nur Standard-Branch, nur nach gruenem Secret-Scan, Actions vorher aus.
set -euo pipefail

HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORG="iilsandbox"  # vom Owner angelegt 2026-10-04
DEPENDABOT="app/dependabot"
SCHLIESSEN_TEXT="Sandbox-Spiegel: nur Standard-Branch (ADR-308 §4.3)"

case "${1:-}" in
  ""|-h|--help) sed -n '2,15p' "$0"; exit 0 ;;
esac

ARBEIT="$(mktemp -d)"
trap 'rm -rf "$ARBEIT"' EXIT

spiegeln() {
  local quelle="$1" name="${1#*/}" kopie branch
  kopie="$ARBEIT/$name.git"
  git clone -q --bare --single-branch --no-tags "https://github.com/$quelle.git" "$kopie"
  branch="$(git -C "$kopie" symbolic-ref --short HEAD)"
  python3 "$HIER/geheimnis_scan.py" "$kopie"

  gh repo view "$ORG/$name" >/dev/null 2>&1 || gh repo create "$ORG/$name" --private \
    --description "Sandbox-Spiegel von $quelle (ADR-308) — nur Sandbox-Schreibziel" \
    --disable-wiki --disable-issues >/dev/null
  gh api -X PUT "repos/$ORG/$name/actions/permissions" -F enabled=false
  [ "$(gh api "repos/$ORG/$name/actions/permissions" -q .enabled)" = "false" ] \
    || { echo "$ORG/$name: Actions nicht aus" >&2; return 1; }
  [ "$(gh repo view "$ORG/$name" --json visibility -q .visibility)" = "PRIVATE" ] \
    || { echo "$ORG/$name: nicht privat" >&2; return 1; }

  git -C "$kopie" push -q --force "https://github.com/$ORG/$name.git" "$branch:refs/heads/$branch"
  gh api -X PATCH "repos/$ORG/$name" -f default_branch="$branch" >/dev/null

  local pr
  for pr in $(gh pr list -R "$ORG/$name" --state open --author "$DEPENDABOT" --json number -q '.[].number'); do
    gh pr close "$pr" -R "$ORG/$name" --delete-branch -c "$SCHLIESSEN_TEXT" >/dev/null
  done
  local andere
  andere="$(gh api "repos/$ORG/$name/branches" -q ".[].name | select(. != \"$branch\")")"
  [ -z "$andere" ] || { echo "$ORG/$name: weitere Branches: $andere" >&2; return 1; }

  echo "$ORG/$name ← $quelle ($branch @ $(git -C "$kopie" rev-parse --short HEAD)) privat, Actions aus, nur $branch"
}

for quelle in "$@"; do
  spiegeln "$quelle"
done
