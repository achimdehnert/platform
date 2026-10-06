"""Drill für das Gate `push-to-merged-branch-silently-lost`
(block_push_to_merged_branch.py).

Der Hook wird über seinen echten Aufrufpfad gefahren (Direktaufruf via Shebang,
JSON auf stdin) — so ruft ihn settings.json. `git` läuft ECHT gegen ein
Wegwerf-Repo in `tmp_path` (kein Netz nötig: `git remote get-url` liest nur die
lokale Config). `gh` ist eine Attrappe auf dem PATH, deren Antwort über
`GH_MODE`/`GH_PR_NUMBER` gesteuert wird.

Positivkontrolle: die drei Realfälle aus dem Gate-Hintergrund — `git push` (kein
Refspec, aktueller Branch), `git push origin <branch>` (explizites Refspec) und
`git -C <pfad> push` — je auf einen Branch, dessen PR laut `gh` gemergt ist
(platform#3488→#3514, cad-hub#81→#82-Muster). Negativkontrolle: kein `git push`
im Befehlstext, Push auf den Default-Branch, kein gemergter PR (offen oder gar
keiner) und ein `gh`-Fehler — alle vier müssen durchlassen.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "block_push_to_merged_branch.py"

GH_ATTRAPPE = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$GH_AUFRUFE"
case "${GH_MODE:-EMPTY}" in
  KAPUTT) echo "HTTP 502" >&2; exit 1 ;;
  MERGED) printf '[{"number": %s}]\\n' "${GH_PR_NUMBER:-99}" ;;
  *) printf '[]\\n' ;;
esac
"""

FEATURE_BRANCH = "feature/gate-test"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "T")
    (root / "f.txt").write_text("x")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    _git(root, "branch", "-M", "main")
    _git(
        root, "remote", "add", "origin", "https://github.com/achimdehnert/testrepo.git"
    )
    _git(root, "checkout", "-q", "-b", FEATURE_BRANCH)
    return root


@pytest.fixture
def umgebung(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(GH_ATTRAPPE, encoding="utf-8")
    gh.chmod(0o755)
    return {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "GH_AUFRUFE": str(tmp_path / "gh-aufrufe.txt"),
    }


def _lauf(
    kommando: str, cwd: str, umgebung: dict, mode: str = "EMPTY", nr: str = ""
) -> dict:
    env = {**os.environ, **umgebung, "GH_MODE": mode}
    if nr:
        env["GH_PR_NUMBER"] = nr
    fertig = subprocess.run(
        [str(HOOK)],
        input=json.dumps(
            {
                "session_id": "sess-probe",
                "cwd": cwd,
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
        return {"decision": "allow", "reason": "", "stderr": fertig.stderr}
    out = json.loads(fertig.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    return {
        "decision": out["permissionDecision"],
        "reason": out["permissionDecisionReason"],
        "stderr": fertig.stderr,
    }


def _gh_aufrufe(umgebung: dict) -> list[str]:
    pfad = Path(umgebung["GH_AUFRUFE"])
    return pfad.read_text().splitlines() if pfad.exists() else []


# --- Positivkontrolle: muss blocken --------------------------------------------


def test_should_deny_bare_push_on_merged_branch(repo, umgebung):
    ergebnis = _lauf("git push", str(repo), umgebung, mode="MERGED", nr="3514")
    assert ergebnis["decision"] == "deny"
    assert "PR #3514" in ergebnis["reason"]
    assert "cherry-pick" in ergebnis["reason"]
    assert _gh_aufrufe(umgebung) == [
        f"pr list --repo achimdehnert/testrepo --head {FEATURE_BRANCH} "
        "--state merged --json number --limit 1"
    ]


def test_should_deny_push_with_explicit_refspec(repo, umgebung):
    kommando = f"git push origin {FEATURE_BRANCH}"
    ergebnis = _lauf(kommando, str(repo), umgebung, mode="MERGED", nr="82")
    assert ergebnis["decision"] == "deny"
    assert "PR #82" in ergebnis["reason"]


def test_should_deny_git_dash_c_variant(repo, umgebung, tmp_path):
    """cwd der Sitzung ist NICHT das Repo — `-C` muss trotzdem greifen."""
    anderswo = tmp_path / "woanders"
    anderswo.mkdir()
    kommando = f"git -C {repo} push"
    ergebnis = _lauf(kommando, str(anderswo), umgebung, mode="MERGED", nr="3488")
    assert ergebnis["decision"] == "deny"
    assert "PR #3488" in ergebnis["reason"]


def test_should_deny_after_cd_tracking(repo, umgebung, tmp_path):
    kommando = f"cd {repo} && git push"
    ergebnis = _lauf(kommando, str(tmp_path), umgebung, mode="MERGED", nr="1")
    assert ergebnis["decision"] == "deny"


# --- Negativkontrolle: muss durchlassen ----------------------------------------


def test_should_allow_open_pr(repo, umgebung):
    """`gh pr list --state merged` liefert fuer einen offenen PR keinen Treffer —
    ununterscheidbar von 'kein PR' auf dieser Ebene, beides ALLOW."""
    ergebnis = _lauf("git push", str(repo), umgebung, mode="EMPTY")
    assert ergebnis["decision"] == "allow"
    assert "kein gemergter PR" in ergebnis["stderr"]


def test_should_allow_no_pr_at_all(repo, umgebung):
    ergebnis = _lauf(
        f"git push origin {FEATURE_BRANCH}", str(repo), umgebung, mode="EMPTY"
    )
    assert ergebnis["decision"] == "allow"


def test_should_allow_gh_error(repo, umgebung):
    ergebnis = _lauf("git push", str(repo), umgebung, mode="KAPUTT")
    assert ergebnis["decision"] == "allow"
    assert "fail-open" in ergebnis["stderr"]


def test_should_allow_non_push_command(repo, umgebung):
    ergebnis = _lauf("git status", str(repo), umgebung)
    assert ergebnis["decision"] == "allow"
    assert ergebnis["stderr"] == ""
    assert _gh_aufrufe(umgebung) == []


def test_should_allow_push_to_default_branch(repo, umgebung):
    ergebnis = _lauf("git push origin main", str(repo), umgebung, mode="MERGED", nr="1")
    assert ergebnis["decision"] == "allow"
    assert _gh_aufrufe(umgebung) == []  # main wird nie nachgefragt


def test_should_ignore_non_json_input():
    fertig = subprocess.run(
        [str(HOOK)], input="kein json", capture_output=True, text=True, timeout=30
    )
    assert fertig.returncode == 0 and fertig.stdout == ""
