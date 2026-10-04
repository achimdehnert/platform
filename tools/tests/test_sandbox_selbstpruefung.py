"""Tests fuer tools/sandbox/selbstpruefung.py (platform#3685) — keine Netz-Calls."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "sandbox" / "selbstpruefung.py"
_spec = importlib.util.spec_from_file_location("selbstpruefung", _SCRIPT)
sp = importlib.util.module_from_spec(_spec)
sys.modules["selbstpruefung"] = sp
_spec.loader.exec_module(sp)

ORG = "iil-sandbox"


def test_should_require_sandbox_marker():
    assert sp.pruefe_kennung({"IIL_SANDBOX": "1"}) == []
    assert sp.pruefe_kennung({}) != []


def test_should_reject_foreign_credentials_but_allow_model_and_sandbox_token():
    assert sp.pruefe_umgebung({"ANTHROPIC_API_KEY": "x", "GH_TOKEN": "y", "PATH": "/bin"}) == []
    befund = sp.pruefe_umgebung({"CF_ACCESS_CLIENT_SECRET": "x", "LIVE_TOKEN": "y"})
    assert "CF_ACCESS_CLIENT_SECRET" in befund[0] and "LIVE_TOKEN" in befund[0]


def test_should_reject_secrets_dir_ssh_keys_and_docker_socket(tmp_path):
    assert sp.pruefe_dateisystem(tmp_path, sockets=()) == []
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "known_hosts").write_text("")
    (tmp_path / ".ssh" / "id_ed25519.pub").write_text("")
    assert sp.pruefe_dateisystem(tmp_path, sockets=()) == [], "nur oeffentliche Dateien"
    (tmp_path / ".ssh" / "id_ed25519").write_text("")
    (tmp_path / ".secrets").mkdir()
    sock = tmp_path / "docker.sock"
    sock.write_text("")
    befunde = sp.pruefe_dateisystem(tmp_path, sockets=(str(sock),))
    assert len(befunde) == 3


def test_should_allow_only_local_repos_or_sandbox_org_remotes():
    remotes = {
        "/arbeit/a": [],
        "/arbeit/b": [f"https://github.com/{ORG}/b.git", f"git@github.com:{ORG}/b.git"],
        "/arbeit/c": ["https://github.com/achimdehnert/platform.git"],
        "/arbeit/d": [f"https://github.com/{ORG}-fake/d.git"],
    }
    befunde = sp.pruefe_remotes(remotes, ORG)
    assert len(befunde) == 2 and "/arbeit/c" in befunde[0] and "/arbeit/d" in befunde[1]
    assert sp.pruefe_remotes({"/arbeit/b": [f"https://github.com/{ORG}/b.git"]}, "") != [], "ohne Org kein Remote"


def test_should_reject_token_with_push_outside_sandbox_org():
    repos = [
        {"full_name": f"{ORG}/spielwiese", "permissions": {"push": True}},
        {"full_name": "achimdehnert/platform", "permissions": {"push": False, "pull": True}},
    ]
    assert sp.pruefe_token_scope(repos, ORG) == []
    repos.append({"full_name": "achimdehnert/decks-hub", "permissions": {"push": True}})
    assert "achimdehnert/decks-hub" in sp.pruefe_token_scope(repos, ORG)[0]


def test_should_read_remotes_from_real_git_repos(tmp_path):
    for name, url in (("lokal", None), ("fremd", "https://github.com/achimdehnert/x.git")):
        repo = tmp_path / "eingang" / name
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        if url:
            subprocess.run(["git", "remote", "add", "origin", url], cwd=repo, check=True)
    remotes = sp.remotes_im_arbeitsbereich(tmp_path)
    assert remotes[str(tmp_path / "eingang" / "lokal")] == []
    assert sp.pruefe_remotes(remotes, ORG) == [f"{tmp_path / 'eingang' / 'fremd'}: Remote ausserhalb der Sandbox-Org: https://github.com/achimdehnert/x.git"]
