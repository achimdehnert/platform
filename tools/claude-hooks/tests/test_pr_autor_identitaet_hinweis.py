"""Drill fuer den Hinweis-Hook `pr_autor_identitaet_hinweis.py` (Gate pr-autor-identitaet-nicht-angewandt).

Anlass: Retro e50644, Befund 8. chat-hub#187 aenderte `.github/workflows/ci.yml` und ging
unter dem Owner-Konto auf, 44 min nachdem platform#3916 die App als Autor solcher PRs
festgelegt hatte. Der Realfall-Test bildet genau diese Form nach (Workflow-Datei,
Owner-Konto als Freigeber, Org-Repo) — mit Platzhalter-Logins statt echter Konten.

`gh` ist ein Fake-Skript im PATH, das fuer `gh api user` einen Login druckt (oder
scheitert); die Policy mit `governance_pfade` liegt in einem Wegwerf-Verzeichnis,
auf das PLATFORM_TOOLS_DIR zeigt. Kein Netz, kein echtes GitHub.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "pr_autor_identitaet_hinweis.py"
OWNER = "owner-login"
FREMD = "anderes-konto"
ORG = "example-org"
ANLEGEN = "gh pr create --title 'feat(x): y' --body-file /tmp/x.md"
GOVERNANCE = '[".github/", "policies/", "CODEOWNERS"]'
#: Form der chat-hub-CODEOWNERS zum Realfall-Zeitpunkt nach #186: Einzeldateien unter
#: deploy/ und die CODEOWNERS selbst — die Workflow-Datei steht NICHT darin.
CODEOWNERS_REALFALL = f"/deploy/raum_grenze.py @{OWNER}\n/.github/CODEOWNERS @{OWNER}\n"


def _modul():
    spec = importlib.util.spec_from_file_location("pr_autor_identitaet_hinweis", HOOK)
    modul = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HOOK.parent))
    spec.loader.exec_module(modul)
    return modul


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def _repo(
    tmp_path: Path, dateien: list[str], codeowners: str | None, remote_owner: str = ORG
) -> Path:
    """Repo mit origin/main (samt CODEOWNERS) und einem Branch, der `dateien` anlegt."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "remote", "add", "origin", f"git@github.com:{remote_owner}/chat-hub.git")
    (repo / "basis.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "basis.txt")
    if codeowners is not None:
        (repo / ".github").mkdir()
        (repo / ".github" / "CODEOWNERS").write_text(codeowners, encoding="utf-8")
        _git(repo, "add", ".github/CODEOWNERS")
    _git(repo, "commit", "-q", "-m", "basis")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "switch", "-q", "-c", "feature/eigener-branch")
    for d in dateien:
        pfad = repo / d
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text("neu", encoding="utf-8")
        _git(repo, "add", d)
    _git(repo, "commit", "-q", "-m", "arbeit")
    return repo


def _umgebung(tmp_path: Path, login: str | None) -> dict[str, str]:
    """PATH mit Fake-`gh` (Login oder Fehlschlag) und PLATFORM_TOOLS_DIR mit Policy."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    skript = bin_dir / "gh"
    antwort = (
        f"echo {login}" if login else 'echo "HTTP 401: Bad credentials" >&2; exit 1'
    )
    skript.write_text(
        f'#!/bin/sh\n[ "$1" = api ] && [ "$2" = user ] || exit 3\n{antwort}\n',
        encoding="utf-8",
    )
    skript.chmod(skript.stat().st_mode | stat.S_IXUSR)
    platform = tmp_path / "platform"
    (platform / "tools").mkdir(parents=True)
    (platform / "policies").mkdir()
    (platform / "policies" / "autonomy-gates.md").write_text(
        f"```yaml\nsa_m:\n  governance_pfade: {GOVERNANCE}   # Kommentar\n```\n",
        encoding="utf-8",
    )
    return {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PLATFORM_TOOLS_DIR": str(platform / "tools"),
    }


def _lauf(repo: Path, env: dict[str, str], kommando: str = ANLEGEN):
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_input": {"command": kommando}, "cwd": str(repo)}),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def _kontext(res) -> str:
    if not res.stdout.strip():
        return ""
    return json.loads(res.stdout)["hookSpecificOutput"]["additionalContext"]


# --- Positivkontrollen ------------------------------------------------------


def test_should_hinweis_zeigen_beim_realfall_workflow_datei_unter_owner_konto(tmp_path):
    repo = _repo(tmp_path, [".github/workflows/ci.yml"], CODEOWNERS_REALFALL)
    res = _lauf(repo, _umgebung(tmp_path, OWNER))
    assert res.returncode == 0, res.stderr
    text = _kontext(res)
    assert ".github/workflows/ci.yml (Governance-Pfad)" in text
    assert f"lotse-gh {ORG} pr create" in text
    assert OWNER in text


def test_should_hinweis_zeigen_wenn_konto_code_owner_der_datei_ist(tmp_path):
    repo = _repo(tmp_path, ["deploy/raum_grenze.py"], CODEOWNERS_REALFALL)
    res = _lauf(repo, _umgebung(tmp_path, OWNER))
    assert "deploy/raum_grenze.py (Code-Owner)" in _kontext(res)


def test_should_repo_eigentuemer_als_freigeber_zaehlen_ohne_codeowners(tmp_path):
    repo = _repo(tmp_path, ["policies/x.md"], None, remote_owner=OWNER)
    res = _lauf(repo, _umgebung(tmp_path, OWNER))
    text = _kontext(res)
    assert "policies/x.md (Governance-Pfad)" in text
    assert f"lotse-gh {OWNER} pr create" in text


def test_should_repo_aus_r_argument_fuer_app_konto_nehmen(tmp_path):
    repo = _repo(tmp_path, [".github/workflows/ci.yml"], CODEOWNERS_REALFALL)
    res = _lauf(repo, _umgebung(tmp_path, OWNER), ANLEGEN + " -R andere-org/chat-hub")
    assert "lotse-gh andere-org pr create" in _kontext(res)


def test_should_nicht_pruefbar_melden_wenn_konto_unbekannt_und_governance_pfad(
    tmp_path,
):
    repo = _repo(tmp_path, [".github/workflows/ci.yml"], CODEOWNERS_REALFALL)
    res = _lauf(repo, _umgebung(tmp_path, None))
    assert res.returncode == 0, res.stderr
    assert "nicht pruefbar" in _kontext(res)


# --- Gegenproben ------------------------------------------------------------


def test_should_keinen_hinweis_zeigen_ohne_approve_pfad(tmp_path):
    repo = _repo(tmp_path, ["docs/retros/r.md", "tools/a.py"], CODEOWNERS_REALFALL)
    res = _lauf(repo, _umgebung(tmp_path, OWNER))
    assert res.returncode == 0, res.stderr
    assert _kontext(res) == ""


def test_should_keinen_hinweis_zeigen_wenn_konto_kein_freigeber(tmp_path):
    repo = _repo(tmp_path, [".github/workflows/ci.yml"], CODEOWNERS_REALFALL)
    res = _lauf(repo, _umgebung(tmp_path, FREMD))
    assert _kontext(res) == ""


def test_should_lotse_gh_kommando_nicht_pruefen(tmp_path):
    repo = _repo(tmp_path, [".github/workflows/ci.yml"], CODEOWNERS_REALFALL)
    res = _lauf(
        repo, _umgebung(tmp_path, OWNER), f"lotse-gh {ORG} pr create --title t --body b"
    )
    assert _kontext(res) == ""


def test_should_anderes_kommando_nicht_pruefen(tmp_path):
    repo = _repo(tmp_path, [".github/workflows/ci.yml"], CODEOWNERS_REALFALL)
    res = _lauf(repo, _umgebung(tmp_path, OWNER), "gh pr list")
    assert _kontext(res) == ""


def test_should_bei_kaputtem_json_nicht_blockieren():
    res = subprocess.run(
        [sys.executable, str(HOOK)], input="kein json", capture_output=True, text=True
    )
    assert res.returncode == 0
    assert res.stdout == ""


# --- CODEOWNERS-Semantik ----------------------------------------------------


def test_should_letzte_passende_codeowners_zeile_gewinnen():
    m = _modul()
    text = f"/deploy/ @{OWNER}\n/deploy/frei.sh @{FREMD}\n"
    assert m.owner_der_datei("deploy/frei.sh", text) == [FREMD]
    assert m.owner_der_datei("deploy/anderes.sh", text) == [OWNER]


def test_should_wildcards_und_unverankerte_muster_verstehen():
    m = _modul()
    text = f"*.yaml @{OWNER}\ndocs/**/geheim.md @{OWNER}\n"
    assert m.owner_der_datei("tief/liegt/x.yaml", text) == [OWNER]
    assert m.owner_der_datei("docs/a/b/geheim.md", text) == [OWNER]
    assert m.owner_der_datei("docs/geheim.md", text) == [OWNER]
    assert m.owner_der_datei("x.yml", text) == []


def test_should_teams_nicht_als_freigeber_zaehlen():
    m = _modul()
    text = f"/policies/ @{ORG}/governance @{OWNER}\n"
    assert m.owner_der_datei("policies/a.md", text) == [OWNER]
    assert m.freigeber(text, None) == {OWNER}
