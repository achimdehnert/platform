#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Regress-Waechter (#1845): keine Docker-Actions in den Deploy-Reusables.
#
# Warum: GitHub baut das Image einer Docker-Action (`runs.using: docker`) bereits
# im JOB-SETUP — auch wenn der Step per `if:` nie ausgefuehrt wird. Auf einem
# self-hosted Runner mit abgelaufener GHCR-Credential in ~/.docker/config.json
# scheitert dieser Build, und der Job stirbt vor dem ersten echten Step.
#
# Zweimal passiert, beide Male derselbe Pin:
#   2026-07-10  travel-beat            (Run 29090717744) -> Fix shared-ci#22
#   2026-08-09  ausschreibungs-hub     (Run 31313918205) -> Fix verloren beim
#                                       Sprung auf v1.1.0, platform#1845
#
# Bestandsaufnahme vor Scharfschalten (2026-08-10, alle Refs aufgeloest):
#   actions/checkout@v7                      node24
#   appleboy/ssh-action@0ff4204d…  v1.2.5    composite
#   appleboy/scp-action@ff85246a…  v1.0.0    composite
#   docker/setup-buildx-action@v4            node24
#   docker/login-action@v4.6.0               node24
#   docker/build-push-action@v7              node24
#   appleboy/scp-action@917f8b81…  v0.1.7    docker   <- der Befund, hier behoben
# => nach dem Fix 0 Treffer, also 0 Fehlalarme. Der Waechter ist blockierend.
#
# Ein Fetch-Fehler ist KEIN gruener Zustand: laesst sich ein Ref nicht aufloesen,
# faellt der Check rot aus, nicht durch.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")/../.."

FILES=(.github/workflows/_deploy-*.yml)
RAW="https://raw.githubusercontent.com"
rc=0
checked=0

fetch_using() {
  # $1=owner/repo  $2=ref  -> gibt den Wert von runs.using aus, leer bei Fehler
  local repo="$1" ref="$2" body="" f
  for f in action.yml action.yaml; do
    for attempt in 1 2 3; do
      if body=$(curl -sfL --max-time 20 "$RAW/$repo/$ref/$f" 2>/dev/null); then
        printf '%s\n' "$body" \
          | grep -m1 -E '^[[:space:]]*using:' \
          | sed -E 's/.*using:[[:space:]]*//; s/["'"'"']//g; s/[[:space:]]*$//'
        return 0
      fi
      sleep $((attempt * 2))
    done
  done
  return 1
}

for file in "${FILES[@]}"; do
  [ -f "$file" ] || continue
  # nur echte Step-Referenzen auf Drittanbieter-Actions (kein ./, kein reusable
  # workflow mit /.github/workflows/, keine auskommentierten Beispielzeilen)
  while IFS= read -r ref; do
    case "$ref" in
      ./*|.\/*) continue ;;
      */.github/workflows/*) continue ;;
    esac
    repo="${ref%@*}"
    rev="${ref#*@}"
    [ "$repo" = "$ref" ] && continue   # kein @ref -> nicht pruefbar

    if ! using=$(fetch_using "$repo" "$rev"); then
      echo "::error file=$file::$ref — action.yml nicht abrufbar; ein Fetch-Fehler zaehlt als rot, nicht als gruen."
      rc=1
      continue
    fi
    checked=$((checked + 1))
    if [ "$using" = "docker" ]; then
      echo "::error file=$file::$ref ist eine Docker-Action (runs.using: docker). GitHub baut ihr Image im Job-Setup; auf self-hosted Runnern stirbt der Deploy dort. Composite-/Node-Variante pinnen (platform#1845)."
      rc=1
    else
      echo "  ok  $ref -> using=$using"
    fi
  done < <(grep -hoE 'uses:[[:space:]]+[A-Za-z0-9._/-]+@[A-Za-z0-9._-]+' "$file" \
             | sed -E 's/uses:[[:space:]]+//' | sort -u)
done

if [ "$rc" -eq 0 ]; then
  echo "✅ $checked Action-Referenz(en) geprueft, keine Docker-Action in den Deploy-Reusables."
else
  echo "❌ Docker-Action (oder nicht aufloesbarer Ref) in den Deploy-Reusables."
fi
exit "$rc"
