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

ORG = "iilsandbox"


def test_should_require_sandbox_marker():
    assert sp.pruefe_kennung({"IIL_SANDBOX": "1"}) == []
    assert sp.pruefe_kennung({}) != []


def test_should_reject_foreign_credentials_but_allow_model_and_sandbox_token():
    assert (
        sp.pruefe_umgebung(
            {
                "ANTHROPIC_API_KEY": "x",
                "CLAUDE_CODE_OAUTH_TOKEN": "z",
                "GH_TOKEN": "y",
                "PATH": "/bin",
            }
        )
        == []
    )
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
    assert (
        sp.pruefe_remotes({"/arbeit/b": [f"https://github.com/{ORG}/b.git"]}, "") != []
    ), "ohne Org kein Remote"


def test_should_reject_token_with_push_outside_sandbox_org():
    proben = {f"{ORG}/spielwiese": 422, "achimdehnert/platform": 404, "fremd/x": 403}
    assert sp.pruefe_token_scope(proben, ORG) == []
    proben["achimdehnert/decks-hub"] = 422
    assert "achimdehnert/decks-hub" in sp.pruefe_token_scope(proben, ORG)[0]


def test_should_fail_closed_on_unexpected_probe_status():
    assert sp.pruefe_token_scope({"achimdehnert/platform": 500}, ORG) != []


def test_should_reject_token_that_can_create_repos():
    assert sp.pruefe_repo_anlegen(403, ORG) == []
    assert sp.pruefe_repo_anlegen(404, ORG) == []
    assert "Repos anlegen" in sp.pruefe_repo_anlegen(422, ORG)[0]


def test_should_read_remotes_from_real_git_repos(tmp_path):
    for name, url in (
        ("lokal", None),
        ("fremd", "https://github.com/achimdehnert/x.git"),
    ):
        repo = tmp_path / "eingang" / name
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        if url:
            subprocess.run(
                ["git", "remote", "add", "origin", url], cwd=repo, check=True
            )
    remotes = sp.remotes_im_arbeitsbereich(tmp_path)
    assert remotes[str(tmp_path / "eingang" / "lokal")] == []
    assert sp.pruefe_remotes(remotes, ORG) == [
        f"{tmp_path / 'eingang' / 'fremd'}: Remote ausserhalb der Sandbox-Org: https://github.com/achimdehnert/x.git"
    ]


def test_should_reject_host_context_in_container(tmp_path):
    assert sp.pruefe_host_kontext(tmp_path) == []
    for pfad in sp.HOST_KONTEXT:
        ziel = tmp_path / pfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text("x")
        befund = sp.pruefe_host_kontext(tmp_path)
        assert len(befund) == 1 and pfad in befund[0]
        ziel.unlink()


def test_should_accept_egress_only_when_all_counter_probes_hold():
    assert sp.bewerte_egress("http://egress:3128", False, False, 403, 200) == []


def test_should_reject_each_open_egress_path_separately():
    assert sp.bewerte_egress("", False, False, 403, 200) == [
        "Egress ohne Allowlist: HTTPS_PROXY fehlt"
    ]
    for argumente, wort in (
        ((True, False, 403, 200), "direkter Egress"),
        ((False, True, 403, 200), "DNS"),
        ((False, False, 200, 200), "sperrt"),
        ((False, False, None, 200), "sperrt"),
        ((False, False, 403, 403), "Gegenprobe"),
        ((False, False, 403, None), "Gegenprobe"),
    ):
        befund = sp.bewerte_egress("http://egress:3128", *argumente)
        assert len(befund) == 1 and wort in befund[0], argumente


def test_should_read_connect_status_from_a_real_proxy_socket():
    import socket
    import threading

    server = socket.create_server(("127.0.0.1", 0))

    def antworten():
        verbindung, _ = server.accept()
        with verbindung:
            verbindung.recv(1024)
            verbindung.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")

    threading.Thread(target=antworten, daemon=True).start()
    port = server.getsockname()[1]
    assert sp.proxy_status(f"http://127.0.0.1:{port}", ("example.com", 443)) == 403
    server.close()
    assert sp.proxy_status(f"http://127.0.0.1:{port}", ("example.com", 443)) is None


def test_should_reject_renamed_transferred_or_unresolvable_remotes():
    url = "https://github.com/iilsandbox/platform.git"
    assert sp.pruefe_aufgeloeste_remotes({url: "iilsandbox/platform"}, ORG) == []
    assert (
        "achimdehnert/platform"
        in sp.pruefe_aufgeloeste_remotes({url: "achimdehnert/platform"}, ORG)[0]
    )
    assert "nicht aufloesbar" in sp.pruefe_aufgeloeste_remotes({url: None}, ORG)[0]
    assert sp.pruefe_aufgeloeste_remotes({url: "iilsandbox/x"}, "") != []
