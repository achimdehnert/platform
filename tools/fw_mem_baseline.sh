#!/usr/bin/env bash
# fw_mem_baseline.sh — RAM-Baseline der iil-Frameworks ueber Prod-Container
# (platform#1899, Kriterium 1: reproduzierbares Einstiegskommando)
#
# Usage:   bash tools/fw_mem_baseline.sh [SSH_HOST]     # default: hetzner-prod
# Ausgabe: Markdown auf stdout — Host-Summary, Container-RSS-Ranking,
#          Import-Kosten der fw-Pakete je App-Container (frischer Python-Prozess).
#
# Reproduzierbarkeit: zweimal ausfuehren; die aifw-Spalte soll < 10 % abweichen.
# Die Probe ist read-only (docker stats + docker exec python -c auf Wegwerf-Prozess).
set -euo pipefail

HOST="${1:-hetzner-prod}"

PROBE='
import importlib, resource
def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
base = rss()
out = []
for m in ("aifw", "promptfw", "authoringfw"):
    try:
        importlib.import_module(m)
        cur = rss()
        out.append(f"{m}=+{cur - base:.0f}")
        base = cur
    except Exception:
        out.append(f"{m}=n/a")
print(" ".join(out))
'

echo "# FW-RAM-Baseline — Host: ${HOST} — $(date -u +%FT%TZ)"
echo
echo "## Host-Speicher (MB)"
echo
echo '```'
ssh "$HOST" 'free -m | sed -n "1,2p"'
echo '```'
echo
echo "## Container-RSS-Ranking (docker stats)"
echo
echo '| RSS | Limit | Container |'
echo '|---|---|---|'
ssh "$HOST" 'docker stats --no-stream --format "{{.MemUsage}}\t{{.Name}}"' \
  | sort -rh \
  | awk -F'\t' '{n = split($1, a, " / "); printf "| %s | %s | %s |\n", a[1], (n > 1 ? a[2] : "-"), $2}'
echo
echo "## Import-Kosten je App-Container (MiB, frischer Python-Prozess)"
echo
echo '| Container | aifw | promptfw | authoringfw |'
echo '|---|---|---|---|'
for c in $(ssh "$HOST" 'docker ps --format "{{.Names}}"' | grep -E '(web|worker|beat|celery)' | sort); do
  if line=$(echo "$PROBE" | ssh "$HOST" "docker exec -i $c python -" 2>/dev/null); then
    aifw=$(echo "$line" | grep -oE 'aifw=[^ ]+' | head -1 | cut -d= -f2)
    pfw=$(echo "$line" | grep -oE 'promptfw=[^ ]+' | cut -d= -f2)
    afw=$(echo "$line" | grep -oE 'authoringfw=[^ ]+' | cut -d= -f2)
    echo "| $c | ${aifw:-?} | ${pfw:-?} | ${afw:-?} |"
  else
    echo "| $c | kein python | — | — |"
  fi
done

# Optional: App-Boot-Analyse fuer EINEN Container — deckt Nicht-fw-Schwergewichte
# auf (platform#1899, Option "Top-Importe je App-Boot").
# Usage: bash tools/fw_mem_baseline.sh <host> <container>
if [ $# -ge 2 ]; then
  C="$2"
  echo
  echo "## App-Boot-Analyse: $C"
  echo
  echo "### RSS des vollen App-Imports (config.wsgi)"
  echo '```'
  echo '
import resource
base = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
try:
    import config.wsgi  # noqa: F401
    cur = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    print(f"config.wsgi: +{cur - base:.1f} MiB")
except Exception as exc:
    print(f"config.wsgi nicht importierbar: {type(exc).__name__}")
' | ssh "$HOST" "docker exec -i $C python -" 2>&1
  echo '```'
  echo
  echo "### Top-15 Importe nach kumulierter Zeit (Proxy fuer Schwergewichte)"
  echo '```'
  ssh "$HOST" "docker exec $C python -X importtime -c 'import config.wsgi' 2>&1 | sort -t'|' -k2 -rn | head -15"
  echo '```'
fi
