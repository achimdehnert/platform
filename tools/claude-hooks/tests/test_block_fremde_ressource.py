"""Drill fuer das Gate `fremde-sitzung-schreibt-externe-ressource`.

Realfall 2026-10-14: zwei Sitzungen im selben Repo auf demselben
Buchhaltungs-Mandanten und demselben Board, eine Zahlung zweimal vorbereitet.
Je Durchlass-Kriterium steht unten ein Test, der zeigt, dass der Aufruf NICHT
gesperrt wird — ein Gate, das nur Treffer zeigt, belegt nicht, dass es zielt.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import block_fremde_ressource as hook  # noqa: E402
import ressourcen_lease as rl  # noqa: E402

A = "aaaaaaaa-0000-0000-0000-000000000001"
B = "bbbbbbbb-0000-0000-0000-000000000002"
BOARD = "/home/u/.claude/boards/sevdesk-eingaenge-2026-10-14.md"
HOOK = Path(__file__).resolve().parents[1] / "block_fremde_ressource.py"


def _tote_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


@pytest.fixture(autouse=True)
def umgebung(tmp_path, monkeypatch):
    leases = tmp_path / "leases"
    sitzungen = tmp_path / "sessions"
    sitzungen.mkdir()
    monkeypatch.setenv("RESSOURCEN_LEASE_DIR", str(leases))
    monkeypatch.setenv("CLAUDE_SESSIONS_DIR", str(sitzungen))
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    return sitzungen


def _sitzung(sitzungen: Path, sid: str, name: str, lebt: bool = True) -> None:
    pid = os.getpid() if lebt else _tote_pid()
    (sitzungen / f"{sid}.json").write_text(
        json.dumps({"pid": pid, "sessionId": sid, "name": name}), encoding="utf-8"
    )


def _bash(befehl: str, sid: str, cwd: str = "/tmp") -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": befehl},
        "session_id": sid,
        "cwd": cwd,
    }


def _write(pfad: str, sid: str) -> dict:
    return {
        "tool_name": "Write",
        "tool_input": {"file_path": pfad, "content": "x"},
        "session_id": sid,
        "cwd": "/tmp",
    }


REGELN = hook.lade_regeln()


def _grund(daten: dict) -> str | None:
    return hook.entscheide(daten, REGELN)[0]


# --- faengt -----------------------------------------------------------------


def test_should_block_realfall_board_append_from_second_session(umgebung):
    """Realfall: die zweite Sitzung haengt per `cat >>` an das Board der ersten an."""
    _sitzung(umgebung, A, "platform-b0")
    _sitzung(umgebung, B, "platform-c4")
    assert _grund(_write(BOARD, A)) is None
    grund = _grund(_bash(f"cat >> {BOARD} <<'EOF'\nRE ueber sevdesk\nEOF", B))
    assert grund and "board:sevdesk-eingaenge-2026-10-14" in grund
    assert "platform-b0" in grund and "--erzwingen" in grund


def test_should_block_second_session_running_sevdesk_script(umgebung, tmp_path):
    """Realfall: Buchungsskript im Scratchpad, sevdesk nur im Skript-Inhalt sichtbar."""
    _sitzung(umgebung, A, "platform-b0")
    _sitzung(umgebung, B, "platform-c4")
    skript = tmp_path / "k3_buchen.py"
    skript.write_text('BASIS = "https://my.sevdesk.de/api/v1"\n', encoding="utf-8")
    assert _grund(_bash(f"python3 {skript}", A)) is None
    assert "`sevdesk`" in (
        _grund(_bash(f"cd {tmp_path} && python3 k3_buchen.py", B)) or ""
    )


def test_should_block_each_sevdesk_command_form(umgebung):
    _sitzung(umgebung, A, "a")
    _sitzung(umgebung, B, "b")
    rl.beanspruchen("sevdesk", A)
    for befehl in (
        "python3 tools/sevdesk/bankpositionen.py --mandant edv",
        "python3 -m tools.sevdesk.beleg_entwurf --paperless 1",
        ".venv/bin/python -c 'from tools.sevdesk import mandant'",
        "SEVDESK_MANDANT=edv make buchen",
        "curl -s https://my.sevdesk.de/api/v1/Voucher",
    ):
        assert _grund(_bash(befehl, B)), befehl


def test_should_block_write_and_sed_inplace_on_foreign_board(umgebung):
    _sitzung(umgebung, A, "a")
    _sitzung(umgebung, B, "b")
    rl.beanspruchen("board:x", A)
    assert _grund(_write("/home/u/.claude/boards/x.md", B))
    assert _grund(_bash("sed -i 's/a/b/' ~/.claude/boards/x.md", B))
    assert _grund(_bash("echo z | tee -a ~/.claude/boards/x.md", B))


def test_should_block_bypass_via_force_and_lease_files(umgebung):
    _sitzung(umgebung, A, "a")
    assert _grund(
        _bash(
            "python3 ~/.claude/hooks/ressourcen_lease.py freigeben sevdesk --erzwingen",
            A,
        )
    )
    assert _grund(_bash("rm ~/.claude/leases/ressourcen/sevdesk.json", A))
    assert _grund(_bash("echo {} > ~/.claude/leases/ressourcen/sevdesk.json", A))
    assert _grund(_write("/home/u/.claude/leases/ressourcen/sevdesk.json", A))


def test_should_fail_closed_without_session_id(umgebung):
    grund = _grund(_bash("python3 tools/sevdesk/mandant.py", ""))
    assert grund and "Sitzung ist unbekannt" in grund


# --- Lease-Lebenszyklus -------------------------------------------------------


def test_should_take_over_lease_of_ended_session(umgebung):
    _sitzung(umgebung, A, "alt", lebt=False)
    _sitzung(umgebung, B, "neu")
    rl.beanspruchen("sevdesk", A)
    grund, hinweis = hook.entscheide(
        _bash("python3 tools/sevdesk/mandant.py", B), REGELN
    )
    assert grund is None and "uebernommen" in (hinweis or "")
    assert rl.lesen("sevdesk")["claude_session"] == B


def test_should_let_owner_session_continue(umgebung):
    _sitzung(umgebung, A, "a")
    assert rl.beanspruchen("sevdesk", A).art == rl.FREI_GENOMMEN
    assert rl.beanspruchen("sevdesk", A).art == rl.EIGEN


def test_should_release_only_own_or_forced(umgebung):
    _sitzung(umgebung, A, "a")
    _sitzung(umgebung, B, "b")
    rl.beanspruchen("sevdesk", A)
    assert rl.freigeben("sevdesk", B)[0] is False
    assert rl.freigeben("sevdesk", B, erzwingen=True)[0] is True
    rl.beanspruchen("sevdesk", A)
    assert rl.freigeben("sevdesk", A)[0] is True
    assert rl.lesen("sevdesk") is None


def test_should_treat_unreadable_lease_as_taken(umgebung):
    _sitzung(umgebung, B, "b")
    ziel = rl.lease_dir()
    ziel.mkdir(parents=True)
    (ziel / "sevdesk.json").write_text("{kaputt", encoding="utf-8")
    assert rl.beanspruchen("sevdesk", B).erlaubt is False


def test_should_grant_a_free_lease_to_exactly_one_of_racing_sessions(umgebung):
    """Acht Sitzungen greifen gleichzeitig ueber die CLI zu: genau eine wird Inhaber."""
    sids = [f"{i:08d}-race" for i in range(8)]
    for sid in sids:
        _sitzung(umgebung, sid, sid)  # alle "leben" (pid dieses Tests)
    cli = Path(rl.__file__)
    prozesse = [
        subprocess.Popen(
            [sys.executable, str(cli), "nehmen", "sevdesk"],
            env={
                **os.environ,
                "CLAUDE_CODE_SESSION_ID": sid,
                "RESSOURCEN_LEASE_TESTPAUSE": "0.3",
            },
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for sid in sids
    ]
    codes = [p.wait(timeout=30) for p in prozesse]
    assert codes.count(0) == 1, codes


# --- Positivkontrolle: laeuft durch -----------------------------------------


@pytest.mark.parametrize(
    "befehl",
    [
        f"cat {BOARD}",
        f"grep -n RE {BOARD}",
        f"sed -n '1,40p' {BOARD}",
        "git add tools/sevdesk/beleg_entwurf.py && git commit -F /tmp/msg",
        "grep -rn sevdesk tools/",
        "make test",
        "echo x > /tmp/y 2>&1",
        "ls ~/.claude/leases/ressourcen",
        "python3 ~/.claude/hooks/ressourcen_lease.py status",
        "python3 tools/pr_merge_sa.py 12 achimdehnert/platform",
    ],
)
def test_should_pass_reads_and_unrelated_commands_of_foreign_session(umgebung, befehl):
    _sitzung(umgebung, A, "a")
    _sitzung(umgebung, B, "b")
    rl.beanspruchen("sevdesk", A)
    rl.beanspruchen("board:sevdesk-eingaenge-2026-10-14", A)
    assert _grund(_bash(befehl, B)) is None, befehl


def test_should_pass_own_board_of_second_session(umgebung):
    """Ausweg aus dem Realfall: die zweite Sitzung schreibt ihr EIGENES Board."""
    _sitzung(umgebung, A, "a")
    _sitzung(umgebung, B, "b")
    rl.beanspruchen("board:sevdesk-eingaenge-2026-10-14", A)
    assert _grund(_write("/home/u/.claude/boards/sevdesk-edv-c4.md", B)) is None


def test_should_pass_script_without_marker(umgebung, tmp_path):
    _sitzung(umgebung, A, "a")
    _sitzung(umgebung, B, "b")
    rl.beanspruchen("sevdesk", A)
    skript = tmp_path / "rechne.py"
    skript.write_text("print(1 + 1)\n", encoding="utf-8")
    assert _grund(_bash(f"python3 {skript}", B)) is None


def test_should_fail_open_with_warning_on_broken_rules(tmp_path, monkeypatch):
    kaputt = tmp_path / "regeln.json"
    kaputt.write_text("{", encoding="utf-8")
    monkeypatch.setattr(hook, "REGELN", kaputt)
    eingabe = json.dumps(_bash("python3 tools/sevdesk/mandant.py", A))
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(eingabe))
    assert hook.main() == 0


def test_should_deny_via_hook_process_end_to_end(umgebung):
    """Hook als Prozess wie in settings.json: JSON rein, deny-JSON raus."""
    _sitzung(umgebung, A, "a")
    _sitzung(umgebung, B, "b")
    rl.beanspruchen("sevdesk", A)
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(_bash("python3 tools/sevdesk/mandant.py", B)),
        capture_output=True,
        text=True,
        env={**os.environ},
        check=True,
    )
    antwort = json.loads(r.stdout)
    assert antwort["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_should_list_and_clean_up_via_cli(umgebung, monkeypatch, capsys):
    _sitzung(umgebung, A, "a", lebt=False)
    rl.beanspruchen("sevdesk", A)
    assert rl.main(["status"]) == 0
    assert "VERWAIST" in capsys.readouterr().out
    assert rl.main(["aufraeumen"]) == 0
    assert rl.lesen("sevdesk") is None
