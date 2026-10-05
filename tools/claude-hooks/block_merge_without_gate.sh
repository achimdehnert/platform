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
#
# AUSWEITUNG 2026-10-05 (Retro 8a0235 #24, Massnahme R12): zwei Luecken, beide am
# Realfall mcp-hub#302 belegt. (1) Das Repo wurde nur aus `--repo` gelesen, nicht
# aus `-R`; der Rueckfall aufs Verzeichnis scheiterte an `cd ~/...` (Tilde nicht
# expandiert) -> exit 0, der Hook pruefte an jenem Merge NICHTS. Jetzt: `-R`,
# `--repo=`, PR-URL und Tilde. Die PR-Nummer wird per shlex aus den Argumenten
# von `gh pr merge` gelesen, auch hinter Flags. Ein --admin ohne Nummer/URL wird
# geblockt statt durchgewunken (die fruehere GRENZE "Merge per URL/Branch").
# (2) Der Freigabe-Kommentar wurde nur am Login erkannt — die Sitzung postet
# unter dem Owner-Login und stellte sich den Kommentar 21 s vor dem Merge selbst
# aus. Jetzt gilt ein Kommentar, der NACH Sitzungsbeginn entstand, nur, wenn er
# ein Owner-Wort zitiert, das im Transkript als GETIPPTE Nutzer-Nachricht vor
# dem Kommentar steht (nicht Tool-Ausgabe, nicht Zusammenfassung, nicht
# system-reminder/pasted_content) und die PR-Nummer oder "admin" enthaelt.
# GRENZE (dokumentiert): ein Kommentar von VOR Sitzungsbeginn gilt ohne Zitat —
# woher er stammt, ist aus dieser Sitzung nicht pruefbar. Ohne lesbares
# Transkript (Altaufruf, Drill mit Rohtext) gilt die Regel von 2026-08-31.
set -uo pipefail

input="$(cat 2>/dev/null)" || exit 0
cmd="$(printf '%s' "$input" | tr '\n' ' ')"

printf '%s' "$cmd" | grep -qE 'gh pr merge|publish-package\.sh' || exit 0
# --admin ist erst nach dem Freigabe-Kommentar-Check unten ein Bypass.
ADMIN=0
printf '%s' "$cmd" | grep -q -- '--admin' && ADMIN=1
command -v gh >/dev/null 2>&1 || exit 0

# Ziel aus den Argumenten von `gh pr merge` (shlex, Flags mit Wert ueberspringen):
# Zeile "<repo>US<pr>US<transkript>" — US = \x1f, weil Tab als IFS leere Felder
# verschmilzt. pr ist "?", wenn ein Ziel steht, das keine Nummer/URL ist
# (Branch), leer, wenn gar keins steht.
ziel="$(EINGABE="$input" python3 - <<'PY' 2>/dev/null
import json, os, re, shlex
roh, transkript = os.environ.get("EINGABE", ""), ""
kommando = roh
try:
    d = json.loads(roh)
    if isinstance(d, dict):
        kommando = (d.get("tool_input") or {}).get("command") or ""
        transkript = d.get("transcript_path") or ""
except ValueError:
    pass
MIT_WERT = {"-R", "--repo", "-t", "--subject", "-b", "--body", "-F", "--body-file",
            "-A", "--author-email", "--match-head-commit"}
repo = pr = ""
for teil in re.split(r"&&|\|\||[;|\n]", kommando):
    try:
        w = shlex.split(teil)
    except ValueError:
        w = teil.split()
    for i in range(len(w) - 2):
        if w[i:i + 3] != ["gh", "pr", "merge"]:
            continue
        args, j = w[i + 3:], 0
        while j < len(args):
            a = args[j]
            if a in MIT_WERT:
                if a in ("-R", "--repo") and j + 1 < len(args):
                    repo = repo or args[j + 1]
                j += 2
                continue
            if a.startswith("--repo="):
                repo = repo or a.split("=", 1)[1]
            elif a.startswith("-R") and len(a) > 2:
                repo = repo or a[2:]
            elif not a.startswith("-") and not pr:
                m = re.search(r"github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)", a)
                if m:
                    repo, pr = repo or m.group(1), m.group(2)
                else:
                    pr = a.lstrip("#") if re.fullmatch(r"#?\d+", a) else "?"
            j += 1
        break
    if pr or repo:
        break
print(f"{repo}\x1f{pr}\x1f{transkript}")
PY
)"
IFS=$'\x1f' read -r repo pr transkript <<<"$ziel"

# Repo bestimmen: explizites -R/--repo/URL hat Vorrang, sonst das Verzeichnis.
if [ -z "$repo" ]; then
  dir="$(printf '%s' "$cmd" | grep -oE "(cd|pushd)[[:space:]]+[^;&|)\"']+" | tail -1 | sed -E 's/^(cd|pushd)[[:space:]]+//; s/[[:space:]]+$//')"
  dir="${dir:-$PWD}"; dir="${dir%\"}"; dir="${dir#\"}"; dir="${dir/#\~/$HOME}"
  [ -d "$dir" ] || exit 0
  repo="$(cd "$dir" 2>/dev/null && gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
fi
[ -n "$repo" ] || exit 0

melde() {
  reason="${1//\"/\\\"}"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
  exit 0
}

case "$pr" in *[!0-9]*) pr_benannt="$pr"; pr="" ;; *) pr_benannt="" ;; esac

# AUSWEITUNG 2026-08-31: --admin nur mit durablem Freigabe-Kommentar am PR.
if [ "$ADMIN" = "1" ]; then
  if [ -z "$pr" ]; then
    printf '%s' "$cmd" | grep -q 'gh pr merge' || exit 0  # publish-package.sh --admin: kein PR
    melde "⛔ --admin-Merge geblockt: kein PR-Nummer/URL im Kommando${pr_benannt:+ (Ziel '${pr_benannt}' ist ein Branch)} — ohne Nummer kann das Gate den Freigabe-Kommentar nicht pruefen. Mit Nummer erneut: gh pr merge <N> --repo ${repo} --admin"
  fi
  kommentare="$(gh pr view "$pr" --repo "$repo" --json comments \
    --jq '[.comments[] | {login: .author.login, createdAt, body}]' 2>/dev/null)" || exit 0
  urteil="$(KOMMENTARE="$kommentare" TRANSKRIPT="$transkript" PR="$pr" python3 - <<'PY' 2>/dev/null
import json, os, re
from datetime import datetime

def zeit(s):
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None

def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()

try:
    kommentare = json.loads(os.environ.get("KOMMENTARE") or "[]")
except ValueError:
    kommentare = []
kandidaten = [k for k in kommentare
              if "bot" not in (k.get("login") or "").lower()
              and re.search(r"freigabe|admin|bypass", k.get("body") or "", re.I)]
if not kandidaten:
    print("kein-kommentar"); raise SystemExit

eintraege = []
try:
    with open(os.environ.get("TRANSKRIPT") or "", encoding="utf-8") as f:
        for z in f:
            try:
                eintraege.append(json.loads(z))
            except ValueError:
                pass
except OSError:
    print("ok"); raise SystemExit  # GRENZE: kein Transkript -> Regel 2026-08-31
beginne = [t for t in (zeit(e.get("timestamp")) for e in eintraege) if t]
if not beginne:
    print("ok"); raise SystemExit
beginn = min(beginne)

# Getippte Owner-Nachrichten: nur Nutzer-Eintraege mit origin.kind == human
# (aeltere Transkripte ohne origin: jeder Nutzer-Text ohne tool_result).
mit_herkunft = any("origin" in e for e in eintraege if e.get("type") == "user")
owner = []
for e in eintraege:
    if e.get("type") != "user" or e.get("isMeta") or e.get("isCompactSummary"):
        continue
    if mit_herkunft and (e.get("origin") or {}).get("kind") != "human":
        continue
    c = (e.get("message") or {}).get("content")
    if isinstance(c, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            continue
        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(c, str):
        continue
    c = re.sub(r"<(system-reminder|pasted_content)\b[^>]*>.*?</\1[^>]*>", " ", c, flags=re.S)
    owner.append((zeit(e.get("timestamp")), norm(c)))

ZITAT = re.compile(r"'([^']{3,})'|\"([^\"]{3,})\"|„([^“”\"]{3,})[“”\"]|‚([^‘’']{3,})[‘’']|«([^»]{3,})»|»([^«]{3,})«")
pr = os.environ.get("PR", "")
for k in kandidaten:
    t = zeit(k.get("createdAt"))
    if t is None:
        continue
    if t < beginn:
        print("ok"); raise SystemExit  # GRENZE: vor dieser Sitzung entstanden
    for m in ZITAT.finditer(k.get("body") or ""):
        q = norm(next(g for g in m.groups() if g))
        if not (re.search(rf"(?<!\d){re.escape(pr)}(?!\d)", q) or "admin" in q):
            continue
        if any(ts and ts < t and q in text for ts, text in owner):
            print("ok"); raise SystemExit
print("unbelegt")
PY
)"
  case "$urteil" in
    ok) exit 0 ;;  # benannter, durabel abgelegter und an ein Owner-Wort gebundener Bypass
    unbelegt) melde "⛔ --admin-Merge geblockt: der Freigabe-Kommentar an PR #${pr} (${repo}) entstand in DIESER Sitzung und zitiert kein Owner-Wort, das im Transkript als getippte Nachricht VOR dem Kommentar steht (Gate gate-approval-needs-pr-comment, Ausweitung 2026-10-05; Realfall mcp-hub#302: Kommentar 21 s vor dem Merge selbst ausgestellt). Das Zitat muss die PR-Nummer oder 'admin' enthalten und woertlich aus der Owner-Nachricht stammen: gh pr comment ${pr} --repo ${repo} --body \"Freigabe --admin (Owner-Wort: '<woertliches Zitat>')\". Liegt kein solches Wort vor, ist der naechste Schritt die Frage an den Owner." ;;
    kein-kommentar) ;;
    *) exit 0 ;;  # python3 fehlt oder Antwort unlesbar -> fail-open wie der Rest des Hooks
  esac
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
