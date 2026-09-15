"""Drill für das Gate `gh-body-file-leer-ueberschrieben` (block_empty_body_file.py).

Positivkontrolle sind die beiden echten Befehle, die am 2026-09-14 den Body von
apo-hub#125 geleert haben (Retro kbiAvn-incr #6), wörtlich aus dem Transkript.
Die Durchlass-Fälle sind echte Befehle derselben Sitzung, die korrekt gekoppelt
waren — ein Guard, der sie blockt, würde abgeschaltet statt befolgt.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "block_empty_body_file.py"

# Transkript apo-hub 4d84e05f, REALFALL_OHNE_R
REALFALL_OHNE_R = 'cd /tmp/claude-1000/-home-devuser-github-apo-hub/4d84e05f-a7ee-4f38-913a-e16ff40a5956/scratchpad && gh issue view 125 --json body --jq .body > i125.md && python3 - <<\'EOF\'\np=\'i125.md\'; s=open(p).read()\ndef rep(a,b):\n    global s\n    assert s.count(a)==1, a\n    s=s.replace(a,b)\nrep("- [ ] Fehlerseiten mit `DEBUG=False` (der Lauf lief mit `DEBUG=True`)","- [x] Fehlerseiten mit `DEBUG=False` — Templates in #128; 404/CSRF im Browser geprüft (#137), 500 nur per Test")\nrep("- [ ] POST-Aktionen:","- [x] POST-Aktionen — geklickt in #137 (27 Stationen, 8 Befunde #129–#136, Fixes #138/#139):")\nrep("- [ ] E-Mail-Versand (Console-Backend)","- [x] E-Mail-Versand (Console-Backend) — #137, Platzhalter-Befund #136; SMTP in Prod nicht verifiziert")\nrep("- [ ] Django-Admin (`/admin/`, übersprungen)","- [x] Django-Admin — #137, Link-Befund #132; als Superuser nicht geprüft")\nopen(p,\'w\').write(s)\nEOF\ngh issue edit 125 -R achimdehnert/apo-hub --body-file i125.md >/dev/null && gh issue view 125 --json body --jq .body | grep -c "\\[x\\]"'

# Transkript apo-hub 4d84e05f, REALFALL_MIT_R
REALFALL_MIT_R = 'cd /tmp/claude-1000/-home-devuser-github-apo-hub/4d84e05f-a7ee-4f38-913a-e16ff40a5956/scratchpad && gh issue view 125 -R achimdehnert/apo-hub --json body --jq .body > i125.md && python3 - <<\'EOF\'\np=\'i125.md\'; s=open(p).read()\ndef rep(a,b):\n    global s\n    assert s.count(a)==1, a\n    s=s.replace(a,b)\nrep("- [ ] Fehlerseiten mit `DEBUG=False` (der Lauf lief mit `DEBUG=True`)","- [x] Fehlerseiten mit `DEBUG=False` — Templates in #128; 404/CSRF im Browser geprüft (#137), 500 nur per Test")\nrep("- [ ] POST-Aktionen:","- [x] POST-Aktionen — geklickt in #137 (27 Stationen, 8 Befunde #129–#136, Fixes #138/#139):")\nrep("- [ ] E-Mail-Versand (Console-Backend)","- [x] E-Mail-Versand (Console-Backend) — #137, Platzhalter-Befund #136; SMTP in Prod nicht verifiziert")\nrep("- [ ] Django-Admin (`/admin/`, übersprungen)","- [x] Django-Admin — #137, Link-Befund #132; als Superuser nicht geprüft")\nopen(p,\'w\').write(s)\nEOF\ngh issue edit 125 -R achimdehnert/apo-hub --body-file i125.md >/dev/null && gh issue view 125 -R achimdehnert/apo-hub --json body --jq .body | grep -c "\\[x\\]"'

# Transkript apo-hub 4d84e05f, KETTE_NUR_UND
KETTE_NUR_UND = "cd /tmp/claude-1000/-home-devuser-github-apo-hub/4d84e05f-a7ee-4f38-913a-e16ff40a5956/scratchpad && sed -i 's/| 12 Mails aus 11 Aktionen                |/| 11 Mails aus 10 Aktionen                |/' sammel.md && grep -c \"11 Mails aus 10\" sammel.md && gh issue edit 137 -R achimdehnert/apo-hub --body-file sammel.md >/dev/null && echo ok"

# Transkript apo-hub 4d84e05f, KETTE_MIT_GUARD
KETTE_MIT_GUARD = 'cd ~/.repo-session/worktrees/apo-hub/2026-09-14-achim-dehnert-fsm-bewerbung-annahme-141816 && git branch --show-current && git add -A && git commit -q -m "fix(requests): Migration 0004 schreibt den Übergang in Request.history\n\nRetro kbiAvn-incr Befund #13: die Datenmigration änderte Prod-Status per\n.update() ohne Eintrag im append-only-Verlauf und ohne updated_at.\nTest: ohne Fix rot (Verlauf leer), mit Fix grün; Anfragen des Inhabers bleiben unberührt.\n\nRefs #130\n\nCo-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01GnPBui2uXnN3KQUYkbiAvn" && git push -q 2>&1 | grep -v "^remote:"; SP=/tmp/claude-1000/-home-devuser-github-apo-hub/4d84e05f-a7ee-4f38-913a-e16ff40a5956/scratchpad; gh pr view 138 -R achimdehnert/apo-hub --json body --jq .body > $SP/pr138.md && test -s $SP/pr138.md && python3 - "$SP/pr138.md" <<\'PY\'\nimport sys, pathlib\np = pathlib.Path(sys.argv[1]); s = p.read_text()\nmarker = "**Merge-Hinweis:**"\nassert s.count(marker) == 1\nblock = """**Nachtrag Retro (platform#3182, Befund #13):** Migration `0004` schreibt je geänderter Anfrage einen System-Eintrag in `Request.history` (vorher `.update()` ohne Verlauf). Test `test_should_record_history_when_migration_lifts_applications_to_31`: ohne Fix rot, mit Fix grün; Suite 303 passed.\n\n**Nicht verifiziert:** Wie viele Prod-Anfragen `0004` ändert (Bewerbungen mit Status 30) und wie viele Vertreter:innen der Matching-Fehler #133 in Prod ausgeblendet hat — der Prod-Lesezugriff wurde nicht freigegeben. Billigster Check vor dem Merge: `Request.objects.filter(requester_role="substitute", status=30).count()`.\n\n"""\np.write_text(s.replace(marker, block + marker))\nPY\ntest -s $SP/pr138.md && grep -q "Nicht verifiziert" $SP/pr138.md && gh pr edit 138 -R achimdehnert/apo-hub --body-file $SP/pr138.md >/dev/null && gh pr view 138 -R achimdehnert/apo-hub --json body --jq \'.body|length\''


def _entscheidung(kommando: str) -> str:
    fertig = subprocess.run(
        [str(HOOK)],
        input=json.dumps({"tool_input": {"command": kommando}}),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if not fertig.stdout.strip():
        return "allow"
    return json.loads(fertig.stdout)["hookSpecificOutput"]["permissionDecision"]


def test_should_block_realfall_edit_after_heredoc_without_guard():
    assert _entscheidung(REALFALL_OHNE_R) == "deny"


def test_should_block_realfall_second_attempt_with_repo_flag():
    assert _entscheidung(REALFALL_MIT_R) == "deny"


def test_should_allow_edit_chained_only_with_and():
    assert _entscheidung(KETTE_NUR_UND) == "allow"


def test_should_allow_edit_behind_test_s_guard():
    assert _entscheidung(KETTE_MIT_GUARD) == "allow"


def test_should_allow_guard_after_heredoc():
    kommando = (
        "gh issue view 1 -R o/r --json body --jq .body > b.md && python3 - <<'EOF'\n"
        "open('b.md','a').write('x')\nEOF\ntest -s b.md && gh issue edit 1 -R o/r --body-file b.md"
    )
    assert _entscheidung(kommando) == "allow"


def test_should_block_guard_separated_by_semicolon():
    kommando = (
        "gh pr view 2 --json body > b.md; test -s b.md; gh pr edit 2 --body-file b.md"
    )
    assert _entscheidung(kommando) == "deny"


def test_should_block_existing_empty_body_file(tmp_path):
    datei = tmp_path / "leer.md"
    datei.write_text("")
    assert _entscheidung(f"gh issue edit 3 -R o/r --body-file {datei}") == "deny"


def test_should_allow_existing_filled_body_file(tmp_path):
    datei = tmp_path / "voll.md"
    datei.write_text("Ein ausreichend langer Body mit Inhalt.\n")
    assert _entscheidung(f"gh issue edit 3 -R o/r -F {datei}") == "allow"


def test_should_block_empty_inline_body():
    assert _entscheidung('gh pr edit 4 --body ""') == "deny"


def test_should_ignore_commands_without_gh_edit():
    assert _entscheidung("gh issue view 125 --json body > i125.md") == "allow"


def test_should_fail_open_on_invalid_json():
    fertig = subprocess.run(
        [str(HOOK)], input="kein json", capture_output=True, text=True
    )
    assert fertig.returncode == 0 and fertig.stdout == ""
