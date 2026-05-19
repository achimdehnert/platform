#!/usr/bin/env bash
# ADR-211 Confirmation C1 — Klickdummy-Registry-Konformität (SF1, Issue #235)
#
# Invariante: Jedes in registry/repos.yaml gelistete Repo, das einen
# `klickdummy`-Pfad enthält, MUSS ein repo-lokales ADR mit
# `conforms_to: ADR-211` führen (ADR-211 I1–I4 / Enforcement-Pfad).
#
# Exit 0 = alle klickdummy-Repos konform.  Exit 1 = mindestens ein Verstoß.
# Exit 2 = Setup-/Parsefehler.  Nicht ausgecheckte Repos → WARN (Exit-neutral),
#          mit --strict zu FAIL.  Reine bash + python3/pyyaml (kein yq).
#
# Grenze (bewusst, dokumentiert): erkennt Klickdummies über ein Verzeichnis
# namens `klickdummy`. Demo-Render ohne solches Verzeichnis (z. B. nur
# `?demo=`-View) wird hier NICHT erfasst — separater Check (ADR-211 C3/SF3).
set -euo pipefail

GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGISTRY="$REPO_ROOT/registry/repos.yaml"
STRICT=0
[[ "${1:-}" == "--strict" ]] && STRICT=1

[[ -f "$REGISTRY" ]] || { echo "FATAL: $REGISTRY fehlt"; exit 2; }
command -v python3 >/dev/null || { echo "FATAL: python3 nötig"; exit 2; }

# Repo-Namen aus der Registry (domains[].systems[].repo) — robust via pyyaml.
mapfile -t REPOS < <(python3 - "$REGISTRY" <<'PY'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
seen = set()
for d in doc.get("domains", []) or []:
    for s in d.get("systems", []) or []:
        r = s.get("repo")
        if r and r not in seen:
            seen.add(r); print(r)
PY
) || { echo "FATAL: registry/repos.yaml nicht parsebar"; exit 2; }

fail=0 warn=0 checked=0 conform=0
printf '%-22s %-7s %-40s %s\n' "REPO" "KD?" "KONFORMES ADR (conforms_to: ADR-211)" "STATUS"
printf '%s\n' "--------------------------------------------------------------------------------------------"

for repo in "${REPOS[@]}"; do
  dir="$GITHUB_DIR/$repo"
  if [[ ! -d "$dir" ]]; then
    printf '%-22s %-7s %-40s %s\n' "$repo" "-" "-" "WARN (nicht ausgecheckt)"
    warn=$((warn+1)); [[ $STRICT -eq 1 ]] && fail=$((fail+1))
    continue
  fi
  # Klickdummy-Verzeichnis (exakt Basename 'klickdummy', .git ausgeschlossen)
  kd="$(find "$dir" -type d -name klickdummy -not -path '*/.git/*' 2>/dev/null | head -1 || true)"
  if [[ -z "$kd" ]]; then
    printf '%-22s %-7s %-40s %s\n' "$repo" "nein" "n/a" "OK (kein Klickdummy)"
    continue
  fi
  checked=$((checked+1))
  # Konformes ADR: irgendein ADR im Repo mit Frontmatter/Body `conforms_to: ADR-211`
  adr="$(grep -rIl -E '^[[:space:]]*conforms_to:[[:space:]]*ADR-211([^0-9]|$)' \
           "$dir" --include='ADR-*.md' 2>/dev/null | head -1 || true)"
  if [[ -n "$adr" ]]; then
    printf '%-22s %-7s %-40s %s\n' "$repo" "ja" "$(basename "$adr")" "OK"
    conform=$((conform+1))
  else
    printf '%-22s %-7s %-40s %s\n' "$repo" "ja" "— FEHLT —" "FAIL"
    fail=$((fail+1))
  fi
done

echo
echo "Klickdummy-Repos: $checked · konform: $conform · Verstöße: $fail · Warnungen: $warn"
if [[ $fail -gt 0 ]]; then
  echo "✗ ADR-211 C1 ROT — siehe FAIL-Zeilen. Konformität erklärt ein Repo, indem"
  echo "  sein Klickdummy-ADR im Frontmatter 'conforms_to: ADR-211' führt"
  echo "  (meiki-hub:ADR-020, risk-hub:ADR-046, writing-hub:ADR-180)."
  exit 1
fi
echo "✓ ADR-211 C1 GRÜN — alle Klickdummy-Repos konform."
exit 0
