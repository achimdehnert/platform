"""Drill fuer das Gate `vertrauliches-verlaesst-ablage`.

Anlass 2026-10-16: Kundenmails tragen einen Vermerk am Zeilenanfang; markierte
Inhalte duerfen in den Tresor, nicht in Repos, Gedaechtnis, fremde Modelle oder
GitHub. Neben jedem Fang steht ein Durchlass-Test — ein Gate, das nur Treffer
zeigt, belegt nicht, dass es zielt. Kunde und Vermerk sind hier neutral (ACME);
die echte Regeldatei liegt ausserhalb jedes Repos.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import block_vertrauliches_verlassen as hook  # noqa: E402

HOOK = Path(__file__).resolve().parents[1] / "block_vertrauliches_verlassen.py"
BEISPIEL = Path(__file__).resolve().parents[1] / "vertraulich_regeln.beispiel.json"
MAIL = "Hallo,\n\nACME Intern\n\nUmsatz Region Sued: 4,2 Mio.\n"
PROSA = "Die Einstufung ACME Intern steht in jeder Mail des Kunden.\n"


@pytest.fixture(autouse=True)
def heim(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    regeln = tmp_path / ".claude" / "vertraulich_regeln.json"
    regeln.parent.mkdir()
    shutil.copy(BEISPIEL, regeln)
    monkeypatch.setenv(hook.REGELN_ENV, str(regeln))
    (tmp_path / "vertraulich" / "acme").mkdir(parents=True)
    (tmp_path / "github" / "platform").mkdir(parents=True)
    (tmp_path / "scratch").mkdir()
    return tmp_path


def _regeln() -> hook.Regeln:
    return hook.lade_regeln(hook.regeln_pfad())


def _entscheide(werkzeug: str, eingabe: dict, cwd: str = "/") -> str | None:
    return hook.entscheide({"tool_name": werkzeug, "tool_input": eingabe, "cwd": cwd}, _regeln())


# --- Fang 1: Datei-Werkzeuge in geschuetzte Ziele -------------------------


def test_should_block_write_of_marked_mail_into_repo(heim):
    assert _entscheide("Write", {"file_path": f"{heim}/github/platform/notiz.md", "content": MAIL})


def test_should_block_edit_and_multiedit_into_memory(heim):
    ziel = f"{heim}/.claude/projects/x/memory/m.md"
    assert _entscheide("Edit", {"file_path": ziel, "old_string": "a", "new_string": MAIL})
    assert _entscheide("MultiEdit", {"file_path": ziel, "edits": [{"new_string": "ok"}, {"new_string": MAIL}]})


def test_should_block_quoted_marker_line_in_reply(heim):
    zitat = "Danke!\n\n> ACME internal\n> Zahlen folgen\n"
    assert _entscheide("Write", {"file_path": f"{heim}/github/platform/a.md", "content": zitat})


def test_should_allow_marked_mail_into_vault_and_scratchpad(heim):
    assert _entscheide("Write", {"file_path": f"{heim}/vertraulich/acme/mail.txt", "content": MAIL}) is None
    assert _entscheide("Write", {"file_path": f"{heim}/scratch/mail.txt", "content": MAIL}) is None


def test_should_allow_prose_mention_of_marker_in_repo(heim):
    assert _entscheide("Write", {"file_path": f"{heim}/github/platform/a.md", "content": PROSA}) is None


def test_should_block_relative_path_resolved_against_cwd(heim):
    assert _entscheide("Write", {"file_path": "notiz.md", "content": MAIL}, cwd=f"{heim}/github/platform")


# --- Fang 2: Tresor plus Ausgang -------------------------------------------


@pytest.mark.parametrize(
    "befehl",
    [
        "cat ~/vertraulich/acme/mail.txt | gh issue comment 5 -F -",
        "gh api repos/x/y/issues -f body=\"$(cat $HOME/vertraulich/acme/mail.txt)\"",
        "curl -s https://api.groq.com/v1/chat -d @${HOME}/vertraulich/acme/mail.txt",
        "python3 tools/llm.py --anbieter cerebras ~/vertraulich/acme/mail.txt",
        "cd ~/vertraulich/acme && git commit -am x",
    ],
)
def test_should_block_each_vault_exit_form(heim, befehl):
    assert _entscheide("Bash", {"command": befehl}, cwd=str(heim))


def test_should_block_vault_copy_into_repo(heim):
    assert _entscheide("Bash", {"command": f"cp ~/vertraulich/acme/mail.txt {heim}/github/platform/"})


def test_should_block_vault_redirect_into_repo_from_repo_cwd(heim):
    assert _entscheide("Bash", {"command": "cat ~/vertraulich/acme/mail.txt > notiz.md"}, cwd=f"{heim}/github/platform")


def test_should_block_vault_passed_to_script_with_exit(heim):
    skript = heim / "scratch" / "zusammenfassen.py"
    skript.write_text("import requests\nrequests.post('https://api.cerebras.ai/v1', json={})\n")
    assert _entscheide("Bash", {"command": f"python3 {skript} ~/vertraulich/acme/mail.txt"})


@pytest.mark.parametrize(
    "befehl",
    [
        "cat ~/vertraulich/acme/mail.txt",
        "ls -la ~/vertraulich/acme 2>/dev/null",
        "grep -c Umsatz ~/vertraulich/acme/*.txt 2>&1",
        "curl -s http://localhost:11434/api/generate -d @$HOME/vertraulich/acme/mail.txt",
    ],
)
def test_should_allow_reading_vault_and_local_model(heim, befehl):
    """Lesen und das lokale Modell hinter einem Tunnel sind frei — auch mit Repo als cwd."""
    assert _entscheide("Bash", {"command": befehl}, cwd=f"{heim}/github/platform") is None


def test_should_allow_vault_script_without_exit(heim):
    skript = heim / "scratch" / "zaehlen.py"
    skript.write_text("import sys\nprint(len(open(sys.argv[1]).read()))\n")
    assert _entscheide("Bash", {"command": f"python3 {skript} ~/vertraulich/acme/mail.txt"}) is None


# --- Fang 3: markierte Datei oder markierter Befehl mit Ausgang ------------


def test_should_block_marked_body_file_to_github(heim):
    datei = heim / "scratch" / "body.txt"
    datei.write_text(MAIL)
    assert _entscheide("Bash", {"command": f"gh issue comment 5 --body-file {datei}"})
    assert _entscheide("Bash", {"command": f"git commit -F {datei}"}, cwd=f"{heim}/github/platform")


def test_should_block_marked_scratch_file_copied_into_repo(heim):
    datei = heim / "scratch" / "mail.txt"
    datei.write_text(MAIL)
    assert _entscheide("Bash", {"command": f"cp {datei} ~/github/platform/docs/"})


def test_should_block_marked_heredoc_to_github(heim):
    befehl = "gh issue create --title x --body-file - <<'EOF'\nACME Intern\nZahlen\nEOF"
    assert _entscheide("Bash", {"command": befehl})


def test_should_allow_unmarked_body_file_and_marked_local_copy(heim):
    sauber = heim / "scratch" / "body.txt"
    sauber.write_text(PROSA)
    assert _entscheide("Bash", {"command": f"gh issue comment 5 --body-file {sauber}"}) is None
    markiert = heim / "scratch" / "mail.txt"
    markiert.write_text(MAIL)
    assert _entscheide("Bash", {"command": f"cp {markiert} ~/vertraulich/acme/"}) is None
    assert _entscheide("Bash", {"command": f"wc -l {markiert}"}, cwd=f"{heim}/github/platform") is None


# --- Fang 4: MCP und WebFetch ---------------------------------------------


def test_should_block_mcp_github_comment_with_marker(heim):
    assert _entscheide("mcp__github__add_issue_comment", {"owner": "o", "repo": "r", "issue_number": 5, "body": MAIL})


def test_should_block_mcp_input_naming_vault(heim):
    assert _entscheide("mcp__outline-knowledge__create_lesson", {"text": f"siehe {heim}/vertraulich/acme/mail.txt"})


def test_should_allow_mcp_without_marker(heim):
    assert _entscheide("mcp__github__add_issue_comment", {"body": PROSA}) is None


def test_should_ignore_tools_outside_scope(heim):
    assert not hook.erfasst({"tool_name": "Read"})
    assert not hook.erfasst({"tool_name": "Agent"})


# --- Ausfuehrung als Hook: Deny-Form, fail-closed, Fehlerzaehlung ----------


def _lauf(daten: dict, env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK), *args],
        input=json.dumps(daten), capture_output=True, text=True, env=env, check=False,
    )


def test_should_emit_deny_json_without_leaking_content(heim):
    daten = {"tool_name": "Write", "tool_input": {"file_path": f"{heim}/github/platform/a.md", "content": MAIL}}
    aus = json.loads(_lauf(daten, dict(os.environ)).stdout)["hookSpecificOutput"]
    assert aus["permissionDecision"] == "deny"
    assert "4,2 Mio" not in aus["permissionDecisionReason"]


def test_should_fail_closed_on_broken_rules(heim):
    Path(os.environ[hook.REGELN_ENV]).write_text("{kaputt")
    daten = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    aus = json.loads(_lauf(daten, dict(os.environ)).stdout)["hookSpecificOutput"]
    assert aus["permissionDecision"] == "deny"
    assert "fail-closed" in aus["permissionDecisionReason"]


def test_should_stay_silent_without_rules_file(heim):
    env = dict(os.environ, **{hook.REGELN_ENV: str(heim / "fehlt.json")})
    daten = {"tool_name": "Write", "tool_input": {"file_path": f"{heim}/github/platform/a.md", "content": MAIL}}
    assert _lauf(daten, env).stdout == ""


def test_should_count_failures_in_gate_log(heim):
    """Fund 5 (platform#3862): ein Fehlerfall muss im Protokoll auftauchen."""
    log = heim / "hits.jsonl"
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
    env["GATE_HITS_DATEI"] = str(log)
    Path(os.environ[hook.REGELN_ENV]).write_text("{kaputt")
    _lauf({"tool_name": "Bash", "tool_input": {"command": "ls"}}, env)
    zeilen = [json.loads(z) for z in log.read_text().splitlines()]
    assert [(z.get("slug"), z.get("marker")) for z in zeilen] == [(hook.SLUG, "fehler")]


def test_should_check_text_on_stdin_for_memory_commit(heim):
    def pruefe(text: str) -> int:
        return subprocess.run(
            [sys.executable, str(HOOK), "--pruefe-text"], input=text, text=True, check=False
        ).returncode

    assert pruefe(MAIL) == 1
    assert pruefe(PROSA) == 0
