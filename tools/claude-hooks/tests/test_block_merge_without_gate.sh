#!/usr/bin/env bash
# Drill fuer das Gate `no-checks-reported-read-as-green`.
#
# Ein Gate, das nicht scheitern kann, ist keins. Jeder Fall hier ist der reale
# Fall aus Retro 3106ae Befund #1 oder seine Abgrenzung.
set -uo pipefail
HOOK="$(dirname "$0")/../block_merge_without_gate.sh"
bin="$(mktemp -d)"; trap 'rm -rf "$bin"' EXIT
fehler=0

# gh-Attrappe: das Verhalten steuert GH_FALL.
cat > "$bin/gh" <<'GH'
#!/usr/bin/env bash
args="$*"
case "$args" in
  *"repo view"*defaultBranchRef*) echo "main" ;;
  *"repo view"*nameWithOwner*)    echo "achimdehnert/probe" ;;
  *"run list"*)
    case "${GH_FALL:-}" in
      leer)     echo "" ;;
      rot)      echo "failure,success" ;;
      gruen)    echo "success,success" ;;
      laufend)  echo "" ;;
      *)        echo "success" ;;
    esac ;;
esac
GH
chmod +x "$bin/gh"; PATH="$bin:$PATH"

pruefe() {  # name, GH_FALL, kommando, erwartet(block|durch)
  local name="$1" fall="$2" kmd="$3" erwartet="$4"
  local aus
  aus="$(GH_FALL="$fall" printf '%s' "$kmd" | GH_FALL="$fall" bash "$HOOK" 2>/dev/null)"
  local ist="durch"
  printf '%s' "$aus" | grep -q '"permissionDecision":"deny"' && ist="block"
  if [ "$ist" = "$erwartet" ]; then
    echo "  ok   $name"
  else
    echo "  FAIL $name — erwartet $erwartet, war $ist"; fehler=1
  fi
}

echo "Drill: no-checks-reported-read-as-green"
pruefe "kein Lauf vorhanden -> block"        leer  "gh pr merge 51 --repo achimdehnert/probe --squash" block
pruefe "letzter Lauf failure -> block"       rot   "gh pr merge 51 --repo achimdehnert/probe --squash" block
pruefe "letzter Lauf gruen -> durch"         gruen "gh pr merge 51 --repo achimdehnert/probe --squash" durch
pruefe "--admin ist der benannte Bypass"     leer  "gh pr merge 51 --repo achimdehnert/probe --admin"  durch
probe_dir="$(mktemp -d)"
pruefe "publish ohne Lauf -> block"          leer  "cd $probe_dir && bash publish-package.sh $probe_dir" block
pruefe "publish, Lauf gruen -> durch"        gruen "cd $probe_dir && bash publish-package.sh $probe_dir" durch
pruefe "fremdes Kommando -> gar nicht feuern" leer  "git status"                                       durch

[ "$fehler" = 0 ] && echo "Drill bestanden." || echo "Drill GESCHEITERT."
exit "$fehler"
