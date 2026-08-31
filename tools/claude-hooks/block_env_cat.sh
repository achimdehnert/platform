#!/usr/bin/env bash
# PreToolUse(Bash)-Hook: verhindert ungefiltertes Ausgeben von Secret-Dateien.
#
# GATE_HEADER (KONZ-038 D8):
#   "slug": "secret-leak-via-safe-pattern"
#   "mode": "blocking"
#   "owner": "achim"
#   "last_drill_pass": "2026-08-31"
#   "evidence": "tools/claude-hooks/tests/test_block_env_cat.py"
#
# Anlass: session-retro 2026-07-03 F1 (`cat .env` leakte DB_PASSWORD) +
# retro f4a546 #1 2026-07-10 (`cut -d= -f1` auf Nicht-KV-Datei leakte Token).
#
# v3 (2026-07-11, error:platform:20260710-guardfp): ARGUMENT-basierte Erkennung.
# Der alte String-Match über den GESAMTEN Befehl produzierte 3 Falsch-Positive an
# einem Tag (Reader wie `| tail -1` in unbeteiligter Pipe + bloße ERWÄHNUNG eines
# Secret-Pfads in PR-Body-Prosa/Argumenten). Jetzt gilt: Ein Reader/cut/awk ist nur
# dann verdächtig, wenn der Secret-Pfad als ARGUMENT (oder <-Redirect) DESSEN
# Segments auftaucht — Erwähnungen in anderen Segmenten/Strings sind frei.
#
# v4 (2026-08-31, Gate-Bau secret-leak-via-safe-pattern, platform#2234): (1) Datei
# erstmals im Repo versioniert — bis dahin lief der Guard NUR als unversionierte
# Kopie in ~/.claude/hooks/ und war fuer die 0.7.5-Drift-Messung unsichtbar (die
# Lane misst Quelldateien, nicht Kopien ohne Quelle). (2) Neuer Vektor `bash -x`:
# retro b62038 #4 2026-08-21 — `bash -x` auf ein Skript mit Passphrase-Erzeugung
# schreibt jede expandierte Variable (also das Geheimnis) auf stdout. Erkannt wird
# `bash|sh|dash|zsh -x <skript>`, wenn das Skript Secret-Pfade referenziert ODER
# Geheimnisse erzeugt (openssl rand, pwgen, mkpasswd, /dev/urandom).
#
# Doktrin: bei Parse-Zweifel (JSON/Quoting) ALLOW — Hook darf Arbeit nicht fälschlich
# blocken. BEWUSSTE AUSNAHME (Risiko-Umkehr, retro f4a546 #1/incr #5): (a) Globs über
# das Secrets-Verzeichnis (`.secrets/*`) kombiniert mit Reader/cut/awk → deny (Loop-
# Variablen sind nicht verifizierbar; genau der Leak-Vektor); (b) cut/awk auf eine
# Secret-Datei ohne verifizierbare KV-Struktur → deny.
#
# Dokumentierte GRENZEN (kein Vollständigkeits-Claim, incr #5): sed, python -c open(...),
# Umkopieren (cp) und Var-Indirektion außerhalb von Globs werden NICHT erkannt —
# bewusst, weil sed -i auf .env-Dateien ein legitimer Fix-Pfad ist (weltenhub 07-09).
# `set -x` als eigenes Kommando (Trace fuer den Rest der Zeile) wird NICHT erkannt —
# nur die Form `bash -x <skript>`. .env.example/.sample/.template/.dist/.schema sind
# ausgenommen (keine echten Secrets).
set -euo pipefail

INPUT="$(cat)"
DECISION="$(HOOK_INPUT="$INPUT" python3 - 2>/dev/null <<'PYEOF'
import json, os, re, shlex, sys

try:
    d = json.loads(os.environ.get("HOOK_INPUT", "") or "{}")
    cmd = d.get("tool_input", {}).get("command", "") or ""
except Exception:
    print("allow"); sys.exit(0)
if not cmd.strip():
    print("allow"); sys.exit(0)

READERS = {"cat", "less", "more", "head", "tail", "bat", "xxd", "od", "strings"}
FILTERS = {"cut", "grep", "awk", "wc", "sort", "uniq", "sed"}
SHELLS = {"bash", "sh", "dash", "zsh"}
KEYWORDS = {"for", "do", "done", "then", "if", "fi", "elif", "else", "while",
            "until", "time", "exec", "sudo", "command", "nohup", "builtin", "env"}
SECRET = re.compile(r'(\.env($|[^.a-zA-Z])|\.env\.(prod|local|bak|rotation)'
                    r'|\.pem($|[^a-zA-Z])|[._-]secrets?($|[/.]))')
EXAMPLE = re.compile(r'\.env\.(example|sample|template|dist|schema)')
# Erzeugt ein Skript Geheimnisse? (retro b62038 #4: Passphrase via openssl)
ERZEUGER = re.compile(r'(openssl\s+rand|pwgen|mkpasswd|/dev/urandom)')

def is_secret(tok: str) -> bool:
    return bool(SECRET.search(tok)) and not EXAMPLE.search(tok)

# (a) Glob über Secrets-Dir + Reader/cut/awk irgendwo -> Loop-Leak-Vektor (Incident 07-10)
if re.search(r'\.secrets/\*', cmd) and re.search(
        r'(^|[;&|\s])(cat|less|more|head|tail|bat|xxd|od|strings|cut|awk)(\s|$)', cmd):
    print("deny:cut"); sys.exit(0)

try:
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    toks = list(lex)
except ValueError:
    print("allow"); sys.exit(0)  # Parse-Zweifel -> ALLOW (Doktrin)

SEPS = {"|", "||", "&&", ";", "&", "|&"}
segments, cur, seps = [], [], []
for t in toks:
    if t in SEPS:
        segments.append(cur); seps.append(t); cur = []
    else:
        cur.append(t)
segments.append(cur); seps.append(None)

def seg_parts(seg):
    """(cmd_word, args) — Env-Zuweisungen/Shell-Keywords überspringen, <-Redirect-Ziel als Arg."""
    i = 0
    while i < len(seg) and (re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', seg[i]) or seg[i] in KEYWORDS):
        i += 1
    if i >= len(seg):
        return "", []
    cmdw = os.path.basename(seg[i])
    args = []
    j = i + 1
    while j < len(seg):
        if seg[j] in {"<", "<<", "<<<"} and j + 1 < len(seg):
            args.append(seg[j + 1]); j += 2; continue
        args.append(seg[j]); j += 1
    return cmdw, args

def kv_ok(path: str):
    """True=KV-Struktur verifiziert, False=verifiziert OHNE '=', None=nicht verifizierbar."""
    p = os.path.expanduser(path)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "rb") as fh:
            return b"=" in fh.read(1_000_000)
    except OSError:
        return None

def skript_leakt(path: str):
    """True, wenn das Skript Secret-Pfade referenziert oder Geheimnisse erzeugt."""
    p = os.path.expanduser(path)
    if not os.path.isfile(p):
        return False  # nicht lesbar -> ALLOW (Doktrin); Grenze im Header dokumentiert
    try:
        with open(p, "r", errors="replace") as fh:
            inhalt = fh.read(1_000_000)
    except OSError:
        return False
    return bool(SECRET.search(inhalt) and not EXAMPLE.search(inhalt)) or bool(
        ERZEUGER.search(inhalt))

for idx, seg in enumerate(segments):
    cmdw, args = seg_parts(seg)
    if not cmdw:
        continue
    # (v4) bash|sh -x <skript>: xtrace schreibt jede expandierte Variable ins
    # Transkript — bei Secret-Bezug oder Geheimnis-Erzeugung im Skript deny.
    if cmdw in SHELLS and any(re.match(r'^-[A-Za-z]*x', a) for a in args):
        ziele = [a for a in args if not a.startswith("-")]
        if any(is_secret(a) for a in ziele) or any(skript_leakt(a) for a in ziele):
            print("deny:trace"); sys.exit(0)
    args = [a for a in args
            if not re.match(r'^--(include|exclude|exclude-dir)=', a)]
    secret_args = [a for a in args if is_secret(a)]
    if not secret_args:
        continue
    if cmdw == "grep":
        # Leak 2026-08-19: `grep -rhiE '^[A-Za-z0-9_]+' <secretdatei>` gab die
        # ganze Zeile aus. grep stand nur in FILTERS und wurde daher als harmlos
        # behandelt — die Pruefung sah den Befehlsnamen, nicht seine Wirkung.
        # Key-only ist beweisbar, wenn -o gesetzt ist UND das Muster ein '=' fuehrt.
        keyonly = any(re.match(r'^-[A-Za-z]*o', a) for a in args) and any(
            "=" in a and not a.startswith("-") and not is_secret(a) for a in args)
        if not keyonly:
            print("deny:raw"); sys.exit(0)
    if cmdw in READERS:
        nxt_cmd = ""
        if seps[idx] in {"|", "|&"} and idx + 1 < len(segments):
            nxt_cmd, _ = seg_parts(segments[idx + 1])
        if nxt_cmd in FILTERS:
            continue  # Key-only-Filter direkt dahinter -> Werte erreichen das Transkript nicht
        print("deny:raw"); sys.exit(0)
    if cmdw in {"cut", "awk"}:
        for a in secret_args:
            if kv_ok(a) is not True:
                print("deny:cut"); sys.exit(0)

print("allow")
PYEOF
)" || DECISION="allow"
[ -z "$DECISION" ] && DECISION="allow"

case "$DECISION" in
  deny:raw)
    cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Secret-Leak-Guard (retro F1, v3 argument-basiert): ein Reader (cat/head/tail/...) hat eine Secret-Datei als ARGUMENT — rohes Ausgeben schreibt Werte ins Transkript. Key-Namen sicher: grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' <datei> (gibt bei Nicht-KV-Dateien nichts aus) oder direkt hinter den Reader einen Key-Filter pipen. Wenn ein Wert wirklich gebraucht wird: gezielt EINE Variable extrahieren."}}
JSON
    ;;
  deny:cut)
    cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Secret-Leak-Guard (retro f4a546 #1, v3): cut/awk auf einer Secret-Datei OHNE verifizierbare KV-Struktur (oder Glob/Loop ueber ~/.secrets/*) gibt den Inhalt aus — so ist am 2026-07-10 ein Token ins Transkript geleakt. Erst Struktur pruefen (grep -c '=' <datei>), dann gezielt EINE bekannte KV-Datei anfassen; nie ueber ~/.secrets/* loopen. Key-Namen sicher: grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' <datei>."}}
JSON
    ;;
  deny:trace)
    cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Secret-Leak-Guard (retro b62038 #4, v4): bash -x auf ein Skript, das Secrets liest oder erzeugt, schreibt jede expandierte Variable — also das Geheimnis — auf stdout und damit ins Transkript. So stand am 2026-08-21 eine Passphrase-Erzeugung im Klartext im Trace. Ohne -x laufen lassen; zum Debuggen gezielte echo-Marker ohne Secret-Werte setzen oder den Trace in eine Datei ausserhalb des Transkripts umleiten (PS4 + exec 2>trace.log) und dort nur die Struktur pruefen."}}
JSON
    ;;
esac
exit 0
