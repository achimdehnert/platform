"""Drill für das Gate `direct-gh-pr-merge-bypasses-sa-m` (block_direct_pr_merge.py).

Der Hook wird über seinen echten Aufrufpfad gefahren (Direktaufruf via Shebang,
JSON auf stdin) — so ruft ihn settings.json. `gh` ist eine Attrappe auf dem PATH,
deren PR-Zustand über `GH_STATE` gesteuert wird; `HOME` zeigt auf ein tmp-
Verzeichnis, damit das Journal geprüft werden kann, ohne das echte zu berühren.

Positivkontrolle: die Befehlsformen aus den drei Retro-Vorkommen — `gh pr merge
--admin` direkt, eine Merge-Schleife der Bump-Welle, und ein Merge-Kommando auf
einen bereits gemergten PR (platform#3343, MERGED). Negativkontrolle: der
sanktionierte Weg `pr_merge_sa.py`, ein lesendes `gh pr view`, und ein Merge mit
Owner-Wort auf einen offenen PR.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "block_direct_pr_merge.py"

GH_ATTRAPPE = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$GH_AUFRUFE"
case "${GH_STATE:-OPEN}" in
  KAPUTT) echo "HTTP 502" >&2; exit 1 ;;
  *) printf '{"state":"%s","url":"https://github.com/%s/pull/12"}\\n' \\
       "${GH_STATE:-OPEN}" "${GH_URL_REPO:-o/r}" ;;
esac
"""


@pytest.fixture
def umgebung(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(GH_ATTRAPPE, encoding="utf-8")
    gh.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    return {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "HOME": str(home),
        "GH_AUFRUFE": str(tmp_path / "gh-aufrufe.txt"),
    }


def _lauf(kommando: str, umgebung: dict, state: str = "OPEN") -> dict:
    env = {**os.environ, **umgebung, "GH_STATE": state}
    fertig = subprocess.run(
        [str(HOOK)],
        input=json.dumps(
            {
                "session_id": "sess-probe",
                "cwd": umgebung["HOME"],
                "tool_input": {"command": kommando},
            }
        ),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert fertig.returncode == 0, fertig.stderr
    if not fertig.stdout.strip():
        return {"decision": "allow", "reason": ""}
    out = json.loads(fertig.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    return {
        "decision": out["permissionDecision"],
        "reason": out["permissionDecisionReason"],
    }


def _journal(umgebung: dict) -> list[dict]:
    pfad = Path(umgebung["HOME"]) / ".claude" / "pr-merge-sa.jsonl"
    if not pfad.exists():
        return []
    return [json.loads(z) for z in pfad.read_text().splitlines()]


def _gh_aufrufe(umgebung: dict) -> list[str]:
    pfad = Path(umgebung["GH_AUFRUFE"])
    return pfad.read_text().splitlines() if pfad.exists() else []


# --- Positivkontrolle: muss blocken -------------------------------------------


def test_should_block_direct_admin_merge(umgebung):
    ergebnis = _lauf("gh pr merge 12 --admin", umgebung)
    assert ergebnis["decision"] == "deny"
    assert "python3 tools/pr_merge_sa.py" in ergebnis["reason"]
    assert _gh_aufrufe(umgebung) == []  # ohne Marker wird nichts nachgefragt


def test_should_block_merge_loop(umgebung):
    kommando = (
        "for r in a:1 b:2; do gh pr merge ${r#*:} -R achimdehnert/${r%%:*} "
        "--squash --admin; done"
    )
    assert _lauf(kommando, umgebung)["decision"] == "deny"


def test_should_block_merge_chained_behind_sanctioned_tool(umgebung):
    kommando = "python3 tools/pr_merge_sa.py 12 && gh pr merge 13 --squash"
    assert _lauf(kommando, umgebung)["decision"] == "deny"


def test_should_block_realfall_merge_on_already_merged_pr(umgebung):
    """platform#3343: Merge-Kommando 72 Min nach dem Owner-Merge — mit Marker
    geht es nur noch, wenn der Live-Zustand OPEN ist."""
    kommando = "OWNER_WORT=69 gh pr merge 3343 -R achimdehnert/platform --squash"
    ergebnis = _lauf(kommando, umgebung, state="MERGED")
    assert ergebnis["decision"] == "deny"
    assert "MERGED" in ergebnis["reason"]
    zeilen = _journal(umgebung)
    assert len(zeilen) == 1 and zeilen[0]["erlaubt"] is False


def test_should_block_marker_with_non_literal_pr_number(umgebung):
    kommando = "OWNER_WORT=69; for n in 1 2; do gh pr merge $n -R o/r; done"
    ergebnis = _lauf(kommando, umgebung)
    assert ergebnis["decision"] == "deny"
    assert "LITERALE" in ergebnis["reason"]


def test_should_block_when_state_unreadable(umgebung):
    ergebnis = _lauf("OWNER_WORT=69 gh pr merge 12 -R o/r", umgebung, state="KAPUTT")
    assert ergebnis["decision"] == "deny"
    assert "fail-closed" in ergebnis["reason"]


def test_should_block_empty_marker(umgebung):
    assert _lauf("OWNER_WORT= gh pr merge 12 -R o/r", umgebung)["decision"] == "deny"


# --- Negativkontrolle: muss durchlassen ----------------------------------------


def test_should_allow_sanctioned_tool(umgebung):
    assert _lauf("python3 tools/pr_merge_sa.py 12", umgebung)["decision"] == "allow"
    assert (
        _lauf(
            "python3 tools/pr_merge_sa.py 12 achimdehnert/platform --dry-run", umgebung
        )["decision"]
        == "allow"
    )


def test_should_allow_read_only_pr_view(umgebung):
    assert _lauf("gh pr view 12", umgebung)["decision"] == "allow"
    assert _journal(umgebung) == []


def test_should_allow_owner_word_on_open_pr_and_write_journal(umgebung):
    ergebnis = _lauf("OWNER_WORT=69 gh pr merge 12 -R o/r --squash", umgebung)
    assert ergebnis["decision"] == "allow"
    assert _gh_aufrufe(umgebung) == ["pr view 12 --json state,url -R o/r"]
    zeilen = _journal(umgebung)
    assert len(zeilen) == 1
    zeile = zeilen[0]
    assert zeile["quelle"] == "hook:owner-wort"
    assert zeile["repo"] == "o/r"
    assert zeile["pr"] == 12
    assert zeile["owner_wort"] == "69"
    assert zeile["session"] == "sess-probe"
    assert zeile["state"] == "OPEN"
    assert zeile["erlaubt"] is True
    assert zeile["ts"]


def test_should_allow_exported_marker(umgebung):
    kommando = "export OWNER_WORT=69 && gh pr merge 12 --repo=o/r --squash"
    assert _lauf(kommando, umgebung)["decision"] == "allow"


def test_should_take_repo_from_pr_url(umgebung):
    kommando = "OWNER_WORT=69 gh pr merge https://github.com/o/r/pull/12 --squash"
    assert _lauf(kommando, umgebung)["decision"] == "allow"
    assert _gh_aufrufe(umgebung) == ["pr view 12 --json state,url -R o/r"]
    assert _journal(umgebung)[0]["repo"] == "o/r"


def test_should_ignore_non_json_input():
    fertig = subprocess.run(
        [str(HOOK)], input="kein json", capture_output=True, text=True, timeout=30
    )
    assert fertig.returncode == 0 and fertig.stdout == ""
