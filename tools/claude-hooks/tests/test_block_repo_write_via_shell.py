"""Drill + Positivkontrolle fuer block_repo_write_via_shell.

Die Positivkontrolle ist hier die haelfte, auf die es ankommt: der Hook ist nur
brauchbar, wenn er die legitimen Formen NICHT anfasst. Ein Hook, der jeden
`git commit -F - <<'MSG'` blockt, wird am selben Tag abgeschaltet — genau deshalb
haengt der Ausloeser am Schreibziel und nicht am Heredoc.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import block_repo_write_via_shell as modul  # noqa: E402

REPO = str(Path.home() / "github" / "platform")
WORKTREE = str(Path.home() / ".repo-session" / "worktrees" / "platform" / "abc")


# --- Drill: was gefangen werden muss ---------------------------------------


def test_should_warn_on_redirect_into_repo():
    grund = modul.entscheide(f"echo hallo > {REPO}/docs/x.md", REPO)
    assert grund is not None
    assert "Edit/Write" in grund


def test_should_warn_on_append_into_repo():
    assert modul.entscheide(f"cat y >> {REPO}/CHANGELOG.md", REPO) is not None


def test_should_warn_on_sed_in_place_in_repo():
    assert modul.entscheide(f"sed -i 's/a/b/' {REPO}/tools/x.py", REPO) is not None


def test_should_warn_on_tee_into_repo():
    assert modul.entscheide(f"echo x | tee {REPO}/infra/hosts.yaml", REPO) is not None


def test_should_warn_on_relative_path_resolved_against_cwd():
    # Der Realfall dieser Sitzung: `sed -i ... docs/retros/<report>.md` aus dem
    # Worktree heraus — ohne cwd-Aufloesung faellt genau der durch.
    assert modul.entscheide("sed -i 's/a/b/' docs/retros/r.md", WORKTREE) is not None


def test_should_warn_on_write_hidden_in_a_chain():
    assert modul.entscheide(f"make test && echo ok > {REPO}/out.txt", REPO) is not None


def test_should_warn_on_heredoc_that_writes_a_repo_file():
    # Die namensgebende Form: Heredoc MIT Schreibziel im Repo.
    kommando = f"cat <<'EOF' > {REPO}/docs/x.md\ninhalt\nEOF"
    assert modul.entscheide(kommando, REPO) is not None


def test_should_warn_on_worktree_path():
    assert modul.entscheide(f"echo x > {WORKTREE}/infra/hosts.yaml", REPO) is not None


# --- Positivkontrolle: was ausdruecklich durchlaufen muss -------------------


def test_should_stay_silent_on_heredoc_to_stdin():
    # Vier dieser Commits liefen allein am 2026-09-23. Ein Hook, der sie blockt,
    # ist unbrauchbar.
    kommando = "git commit -q -F - <<'MSG'\ndocs(x): etwas\nMSG"
    assert modul.entscheide(kommando, REPO) is None


def test_should_stay_silent_on_scratchpad_write():
    p = "/tmp/claude-1000/sess/scratchpad/pr-body.md"
    assert modul.entscheide(f"cat <<'EOF' > {p}\ntext\nEOF", REPO) is None


def test_should_stay_silent_outside_repo_roots():
    assert modul.entscheide("echo x > /tmp/irgendwas.json", REPO) is None


def test_should_stay_silent_on_variable_path():
    # Fail-open: der Pfad ist zur Pruefzeit unbekannt. Bewusste Grenze.
    assert modul.entscheide('gh api repos/x/y > "$S/ruleset.json"', REPO) is None


def test_should_stay_silent_on_fd_redirect():
    assert modul.entscheide("make test 2>&1 | tail -5", REPO) is None
    assert modul.entscheide("echo fehler >&2", REPO) is None


def test_should_stay_silent_on_dev_null():
    assert modul.entscheide(f"cd {REPO} && gh pr view 1 > /dev/null", REPO) is None


def test_should_stay_silent_on_angle_bracket_inside_quotes():
    # Ein `>` im PR-Text ist keine Umleitung — sonst feuert der Hook bei jedem
    # zweiten Markdown-Blockzitat.
    kommando = f'gh pr comment 1 --body "Messung: 5 > 3, Datei in {REPO}/x.md"'
    assert modul.entscheide(kommando, REPO) is None


def test_should_stay_silent_on_read_redirect():
    assert modul.entscheide(f"python3 x.py < {REPO}/eingabe.txt", REPO) is None


@pytest.mark.parametrize("modus", ["advisory", "blocking"])
def test_should_default_to_advisory_when_state_file_missing(
    monkeypatch, tmp_path, modus
):
    # Umgekehrt zum Evidenz-Scanner: fehlende Datei heisst hier advisory. Das ist
    # Absicht und wird gemessen, damit es nicht still zur Dauerregel wird.
    monkeypatch.setenv("REPO_WRITE_HOOK_STATE_DIR", str(tmp_path))
    assert modul._modus() == "advisory"
    (tmp_path / "repo_write_hook_mode").write_text(modus, encoding="utf-8")
    assert modul._modus() == modus


# --- Positivkontrolle durch main(): der Realfall dieser Sitzung -------------

#: Wortlaut des Befehls, mit dem am 2026-09-23 die Massnahmen-Zeile im gerade
#: gemergten Retro-Bericht geaendert wurde — das vierte Vorkommen des Slugs an
#: einem Tag und der Anlass fuer dieses Gate.
REALFALL = (
    "sed -i 's/| 7 | `gate_wirkung.py` ausweiten |/| 7 | Gate |/' "
    "docs/retros/session-retro-2026-09-23-platform-3bdc4e.md"
)


def _lauf(monkeypatch, capsys, kommando, cwd, modus=None, tmp_path=None):
    import io
    import json

    if tmp_path is not None:
        monkeypatch.setenv("REPO_WRITE_HOOK_STATE_DIR", str(tmp_path))
        if modus:
            (tmp_path / "repo_write_hook_mode").write_text(modus, encoding="utf-8")
    nutzlast = {"tool_input": {"command": kommando}, "cwd": cwd, "session_id": "t"}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(nutzlast)))
    code = modul.main()
    return code, capsys.readouterr().err


def test_should_fire_on_the_real_case_through_main(monkeypatch, capsys, tmp_path):
    code, err = _lauf(monkeypatch, capsys, REALFALL, WORKTREE, tmp_path=tmp_path)
    assert code == 0, "advisory blockt nicht"
    assert "⚠️" in err and "Edit/Write" in err


def test_should_block_the_real_case_when_switched_to_blocking(
    monkeypatch, capsys, tmp_path
):
    code, err = _lauf(
        monkeypatch, capsys, REALFALL, WORKTREE, modus="blocking", tmp_path=tmp_path
    )
    assert code == 2
    assert "⛔" in err


# --- Skript-Heredoc: der zweite Realfall, eine Stunde nach dem ersten --------

#: Wortlaut des Befehls, mit dem am 2026-09-23 der Registry-Eintrag dieses Gates
#: selbst geschrieben wurde — per Python-Heredoc, also ohne jede Umleitung. Der
#: Hook war zu dem Zeitpunkt zwanzig Minuten alt und sah ihn nicht.
SKRIPT_REALFALL = (
    "python3 - <<'PY'\n"
    "import json, pathlib\n"
    "p = pathlib.Path('docs/governance/gates/gates/claim-before-cheapest-check.json')\n"
    "d = json.loads(p.read_text())\n"
    "d['revised'] = '2026-09-23'\n"
    "p.write_text(json.dumps(d))\n"
    "PY"
)


def test_should_fire_on_a_python_heredoc_writing_a_repo_file():
    assert modul.entscheide(SKRIPT_REALFALL, WORKTREE) is not None


def test_should_fire_on_python_dash_c_writing_a_repo_file():
    kommando = "python3 -c \"open('tools/x.py','w').write('a')\""
    assert modul.entscheide(kommando, WORKTREE) is not None


def test_should_stay_silent_on_a_python_heredoc_that_only_reads():
    kommando = (
        "python3 - <<'PY'\n"
        "import pathlib\n"
        "print(pathlib.Path('infra/hosts.yaml').read_text()[:50])\n"
        "PY"
    )
    assert modul.entscheide(kommando, WORKTREE) is None


def test_should_stay_silent_on_a_python_heredoc_writing_to_the_scratchpad():
    kommando = (
        "python3 - <<'PY'\n"
        "open('/tmp/claude-1000/s/scratchpad/out.json','w').write('{}')\n"
        "PY"
    )
    assert modul.entscheide(kommando, WORKTREE) is None


def test_should_stay_silent_on_git_commit_with_stdin_heredoc():
    # Die Abgrenzung, an der der ganze Zuschnitt haengt: git ist kein Interpreter.
    kommando = "git commit -q -F - <<'MSG'\nfix(x): etwas\nMSG"
    assert modul.entscheide(kommando, WORKTREE) is None


def test_should_stay_silent_through_main_on_commit_heredoc(
    monkeypatch, capsys, tmp_path
):
    kommando = "git commit -q -F - <<'MSG'\ndocs(x): etwas\nMSG"
    code, err = _lauf(monkeypatch, capsys, kommando, WORKTREE, tmp_path=tmp_path)
    assert code == 0
    assert err == ""


# --- Ausweitung 2026-09-24: Inline-Text mit „…" (Retro 02b7f5, platform#3545) ---
# Die beiden Realfaelle des Tages, woertlich verkuerzt.


def test_should_warn_on_inline_body_with_ascii_closing_quote():
    kommando = (
        'gh issue comment 382 -R achimdehnert/dev-hub --body "Stand nach Owner-Wort '
        '„25 go 26 go": - **25 (Merge #383):** gesperrt"'
    )
    assert "Inline-Text" in (modul.entscheide(kommando, REPO) or "")


def test_should_warn_on_commit_message_with_ascii_closing_quote():
    kommando = 'git commit -q -m "ci(deploy): Owner-Wort („26 go", „32 erlaubt")."'
    assert "Inline-Text" in (modul.entscheide(kommando, WORKTREE) or "")


def test_should_stay_silent_on_correctly_closed_german_quotes():
    kommando = 'gh pr comment 1 --body "Owner-Wort „25 go“ liegt vor."'
    assert modul.entscheide(kommando, REPO) is None


def test_should_stay_silent_on_body_file():
    kommando = "gh issue comment 382 --body-file /tmp/x/scratchpad/c.md"
    assert modul.entscheide(kommando, REPO) is None


def test_should_stay_silent_on_german_quotes_inside_commit_heredoc():
    kommando = "git commit -q -F - <<'MSG'\nfix(x): Owner-Wort „go\" im Body\nMSG"
    assert modul.entscheide(kommando, WORKTREE) is None


def test_should_stay_silent_on_inline_text_without_german_quotes():
    kommando = 'git commit -q -m "fix(x): \\"zitiert\\" ohne deutsche Quotes"'
    assert modul.entscheide(kommando, WORKTREE) is None
