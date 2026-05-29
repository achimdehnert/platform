#!/usr/bin/env bash
# ADR-211 Confirmation C5 / I4 — Cross-Repo-ADR-Referenz-Format (SF5, Issue #239)
#
# Vertrag (ADR-211 C5, wörtlich): qualifizierte Cross-Repo-ADR-Referenzen
# MÜSSEN exakt matchen:  ^[a-z][a-z0-9-]+:ADR-[0-9]{3}$
# (z. B. platform:ADR-211, risk-hub:ADR-046, meiki-hub:ADR-020).
#
# Prüft alle ADR-Markdown-Dateien im Verzeichnis (Default: platform/docs/adr;
# andere Repos rufen das Script via eigener CI auf ihrem docs/adr-Pfad).
# Findet Tokens der Form <wort>:ADR-<ziffern> und FAILt, wenn die strikte
# Form verletzt ist (Großbuchstabe, Unterstrich, Punkt, != 3 Ziffern, Space).
#
#   Exit 0 ok · 1 Verstoß · 2 Setupfehler.  Reine bash + grep.
#
# BEWUSST AUSSER SCOPE: das Erkennen *unqualifizierter* Cross-Repo-Refs
# (bare `ADR-NNN`, das eigentlich `<repo>:ADR-NNN` sein müsste). Es gibt
# dafür keine false-positive-freie Heuristik (ADR-Nummern-Lücken,
# Vorwärts-/Supersede-Refs). Das ist durch Review + I4-Kultur abgesichert,
# nicht durch diesen Check — bewusst kein verrauschtes WARN (ehrlicher
# Grün-Status statt Alarm-Müdigkeit).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCAN_DIR="${1:-$REPO_ROOT/docs/adr}"
[[ -d "$SCAN_DIR" ]] || { echo "FATAL: Scan-Verzeichnis $SCAN_DIR fehlt"; exit 2; }

STRICT_RE='^[a-z][a-z0-9-]+:ADR-[0-9]{3}$'
fail=0 files=0

mapfile -t ADRS < <(find "$SCAN_DIR" -maxdepth 1 -type f -name 'ADR-*.md' | sort)
[[ ${#ADRS[@]} -gt 0 ]] || { echo "FATAL: keine ADR-*.md in $SCAN_DIR"; exit 2; }

for f in "${ADRS[@]}"; do
  files=$((files+1)); rel="${f#"$REPO_ROOT"/}"
  while IFS= read -r tok; do
    [[ -z "$tok" ]] && continue
    if ! [[ "$tok" =~ $STRICT_RE ]]; then
      echo "FAIL $rel : '$tok' verletzt I4 ($STRICT_RE)"
      fail=$((fail+1))
    fi
  done < <(grep -ohE '[A-Za-z0-9_.-]+:ADR-[0-9]+' "$f" 2>/dev/null | sort -u || true)
done

echo
echo "Geprüft: $files ADR-Dateien in ${SCAN_DIR#"$REPO_ROOT"/} · FAIL: $fail"
if [[ $fail -gt 0 ]]; then
  echo "✗ ADR-211 C5/I4 ROT — Cross-Repo-Refs müssen ^[a-z][a-z0-9-]+:ADR-[0-9]{3}\$ matchen."
  exit 1
fi
echo "✓ ADR-211 C5/I4 GRÜN — alle qualifizierten Cross-Repo-Referenzen I4-konform."
exit 0
