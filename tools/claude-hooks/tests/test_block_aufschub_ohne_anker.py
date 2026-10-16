"""Drill fuer block_aufschub_ohne_anker.py (Gate aufschub-anker, platform#3859 M7).

Realfall: Retro 767d40-incr Befund #2. Ein Kommentar in meiki-lra/meiki-hub#582
fuehrte unter „Bewusst ausgelassen“ sechs Posten, fuenf ohne Issue; gepostet per
`gh issue comment 582 --repo meiki-lra/meiki-hub -F <datei>`. Der Text hier ist
nachgebaut, nicht zitiert.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

_HOOK = Path(__file__).resolve().parent.parent / "block_aufschub_ohne_anker.py"
_spec = importlib.util.spec_from_file_location("block_aufschub_ohne_anker", _HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

WERKZEUG = hook.lade_werkzeug()

OHNE_ANKER = "\n".join(
    [
        "## Bewusst ausgelassen, mit Folgeschritt",
        "",
        "- Gate in den uebrigen Repos: je ein PR nach shared-ci#108.",
        "- Wortlisten zusammenfuehren: bleiben vorerst getrennt.",
        "- Bestand (145): der Abbau ist eine eigene Entscheidung.",
    ]
)
MIT_ANKER = OHNE_ANKER.replace("getrennt.", "getrennt, #110.").replace(
    "Entscheidung.", "Entscheidung, #590."
)


def _daten(kommando: str, cwd: str = "/tmp") -> dict:
    return {"tool_input": {"command": kommando}, "cwd": cwd}


def test_should_find_the_checkout_tool():
    assert WERKZEUG is not None


def test_should_block_the_real_comment_from_body_file(tmp_path):
    """Positivkontrolle: Realfall-Befehl mit relativer Body-Datei."""
    (tmp_path / "c582.md").write_text(OHNE_ANKER)
    grund = hook.entscheide(
        _daten("gh issue comment 582 --repo meiki-lra/meiki-hub -F c582.md", str(tmp_path)),
        WERKZEUG,
    )
    assert grund is not None
    assert "2 Stelle(n)" in grund
    assert "Wortlisten" in grund and "Bestand" in grund


def test_should_block_pr_create_with_inline_body():
    kommando = f"gh pr create --title t --body {shlex.quote(OHNE_ANKER)}"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is not None


def test_should_block_body_with_equals_sign(tmp_path):
    (tmp_path / "b.md").write_text(OHNE_ANKER)
    kommando = f"gh pr edit 5 --body-file={tmp_path / 'b.md'}"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is not None


def test_should_check_second_gh_command_in_chain(tmp_path):
    (tmp_path / "ok.md").write_text(MIT_ANKER)
    (tmp_path / "nok.md").write_text(OHNE_ANKER)
    kommando = (
        f"gh issue comment 1 -F {tmp_path / 'ok.md'} && "
        f"gh pr comment 2 -F {tmp_path / 'nok.md'}"
    )
    assert hook.entscheide(_daten(kommando), WERKZEUG) is not None


def test_should_pass_text_with_anchor_per_item(tmp_path):
    """Negativprobe: jeder Posten mit eigenem Issue."""
    (tmp_path / "c.md").write_text(MIT_ANKER)
    kommando = f"gh issue comment 582 -F {tmp_path / 'c.md'}"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is None


def test_should_pass_other_gh_commands():
    """Negativprobe: lesende oder schliessende gh-Befehle prueft dieser Hook nicht."""
    for kommando in (
        "gh issue view 582 --json body",
        "gh pr list --search 'Bewusst ausgelassen'",
        "gh issue close 5 --comment 'folgt separat'",
    ):
        assert hook.entscheide(_daten(kommando), WERKZEUG) is None, kommando


def test_should_pass_stdin_body_file_without_source_but_count_it():
    """`-F -` ohne erkennbare Quelle: fail-open, aber als ungeprueft gemeldet (#3862 Punkt 5)."""
    grund, ungeprueft = hook.befund(_daten("gh pr comment 1 -F -"), WERKZEUG)
    assert grund is None
    assert ungeprueft == ["gh pr comment -F -"]


def test_should_pass_missing_body_file(tmp_path):
    """Negativprobe: nicht lesbare Datei -> fail-open, gh meldet den Fehler selbst."""
    kommando = f"gh issue comment 1 -F {tmp_path / 'fehlt.md'}"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is None


def test_should_pass_without_tool(monkeypatch):
    """Negativprobe: Werkzeug nicht ladbar -> fail-open."""
    monkeypatch.setattr(hook, "lade_werkzeug", lambda: None)
    kommando = f"gh pr comment 1 --body {shlex.quote(OHNE_ANKER)}"
    assert hook.entscheide(_daten(kommando)) is None


def test_should_emit_deny_json_end_to_end(tmp_path):
    """Echter Prozess: JSON auf stdin, deny auf stdout, Exit 0."""
    (tmp_path / "c.md").write_text(OHNE_ANKER)
    eingabe = json.dumps(_daten(f"gh issue comment 1 -F {tmp_path / 'c.md'}"))
    res = subprocess.run(
        [sys.executable, str(_HOOK)], input=eingabe, capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0
    assert json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_should_stay_silent_on_garbage_input():
    res = subprocess.run(
        [sys.executable, str(_HOOK)], input="kein json", capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0 and res.stdout == ""


# --- platform#3862 Punkt 2: GitHub-MCP ---------------------------------------


def _mcp(name: str, **eingabe) -> dict:
    return {"tool_name": f"mcp__github__{name}", "tool_input": eingabe}


def test_should_block_mcp_issue_comment_without_anchor():
    """Positivkontrolle: derselbe Realfall-Text, gepostet ueber das GitHub-MCP."""
    daten = _mcp("add_issue_comment", owner="o", repo="r", issue_number=582, body=OHNE_ANKER)
    assert "2 Stelle(n)" in hook.entscheide(daten, WERKZEUG)


def test_should_block_mcp_review_line_comment_without_anchor():
    daten = _mcp(
        "create_pull_request_review", body="ok", event="COMMENT", comments=[{"path": "a", "body": OHNE_ANKER}]
    )
    assert "Zeilenkommentar" in hook.entscheide(daten, WERKZEUG)


def test_should_pass_mcp_text_with_anchor_and_reading_tools():
    """Gegenproben: verankerter Text, lesendes Werkzeug, fremder MCP-Server."""
    assert hook.entscheide(_mcp("create_pull_request", title="t", body=MIT_ANKER), WERKZEUG) is None
    assert hook.entscheide(_mcp("get_issue", owner="o", repo="r", issue_number=1), WERKZEUG) is None
    fremd = {"tool_name": "mcp__orchestrator__log_action", "tool_input": {"body": OHNE_ANKER}}
    assert hook.entscheide(fremd, WERKZEUG) is None


# --- platform#3862 Punkt 4: Text ausserhalb des Befehls ----------------------


def test_should_read_heredoc_for_stdin_body():
    kommando = f"gh issue comment 582 -F - <<'EOF'\n{OHNE_ANKER}\nEOF"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is not None
    gegen = f"gh issue comment 582 -F - <<'EOF'\n{MIT_ANKER}\nEOF"
    assert hook.entscheide(_daten(gegen), WERKZEUG) is None


def test_should_read_piped_and_redirected_file_for_stdin_body(tmp_path):
    (tmp_path / "c.md").write_text(OHNE_ANKER)
    for kommando in ("cat c.md | gh issue comment 1 -F -", "gh issue comment 1 -F - < c.md"):
        assert hook.entscheide(_daten(kommando, str(tmp_path)), WERKZEUG) is not None, kommando


def test_should_read_command_substitution_in_body(tmp_path):
    (tmp_path / "c.md").write_text(OHNE_ANKER)
    for kommando in (
        'gh pr create --title t --body "$(cat c.md)"',
        'gh pr comment 1 --body "$(< c.md)"',
        "gh pr comment 1 --body \"`cat c.md`\"",
    ):
        assert hook.entscheide(_daten(kommando, str(tmp_path)), WERKZEUG) is not None, kommando
    (tmp_path / "ok.md").write_text(MIT_ANKER)
    assert hook.entscheide(_daten('gh pr comment 1 --body "$(cat ok.md)"', str(tmp_path)), WERKZEUG) is None


# --- platform#3862 Punkt 5: Fehlerfaelle zaehlen ------------------------------


def test_should_raise_without_tool_so_main_can_count_it(monkeypatch):
    monkeypatch.setattr(hook, "lade_werkzeug", lambda: None)
    kommando = f"gh pr comment 1 --body {shlex.quote(OHNE_ANKER)}"
    try:
        hook.befund(_daten(kommando))
    except RuntimeError:
        return
    raise AssertionError("fehlendes Werkzeug darf nicht wie 'kein Treffer' aussehen")


def test_should_log_failures_and_unchecked_text_separately(tmp_path):
    """Echter Prozess: Parse-Fehler -> `fehler`, `-F -` ohne Quelle -> `ungeprueft`, Treffer getrennt."""
    log = tmp_path / "hits.jsonl"
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
    env["GATE_HITS_DATEI"] = str(log)
    (tmp_path / "c.md").write_text(OHNE_ANKER)
    for eingabe in (
        "kein json",
        json.dumps(_daten("gh pr comment 1 -F -")),
        json.dumps(_daten(f"gh issue comment 1 -F {tmp_path / 'c.md'}")),
    ):
        subprocess.run([sys.executable, str(_HOOK)], input=eingabe, text=True, env=env, timeout=30, check=True)
    zeilen = [json.loads(z) for z in log.read_text().splitlines()]
    assert [z.get("marker") for z in zeilen] == ["fehler", "ungeprueft", "gh issue/pr Text"]
    assert all(z.get("slug") == hook.SLUG for z in zeilen)
