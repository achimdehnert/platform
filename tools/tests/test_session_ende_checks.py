"""Tests fuer `tools/session_ende_checks.sh` (Ende-Runner, #2690 K1/K5).

Der Runner ersetzt den mechanischen Bash-Code, der bis hierhin im Fliesstext von
`.windsurf/workflows/session-ende.md` stand. Getestet wird die **ausgelieferte**
Datei, nicht eine Kopie: `bash -n` als Syntaxnetz und ein echter Lauf gegen ein
tmp_path-Fixture mit zwei git-Repos (eines dirty), einem Lease-Verzeichnis und
einem `gh`-Stub auf dem PATH.

Die drei Invarianten, die dieser Test haelt:

1. **Vollstaendigkeit** — die Summary nennt E.0 bis E.9. Eine Phase, die still
   ausfaellt, waere genau der Zustand, gegen den der Runner gebaut ist.
2. **Positivkontrolle** — ein dirty Repo MIT eigenem Lease wird als WARN
   erkannt. Ohne diese Zeile bestuende der Test auch, wenn E.7 nie etwas faende.
3. **SKIP ist kein Gruen** — fehlt ein Werkzeug, steht `SKIP` in der Zeile,
   nicht `PASS`. „NICHT messbar" als Entwarnung zu verbuchen war die teuerste
   Fehlklasse des Start-Runners (KONZ-platform-050).
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess

import pytest

_SKRIPT = pathlib.Path(__file__).resolve().parents[1] / "session_ende_checks.sh"
_HEUTE = subprocess.run(
    ["date", "+%Y-%m-%d"], capture_output=True, text=True, check=True
).stdout.strip()

# Der Stub antwortet auf genau die drei Aufrufformen, die der Runner kennt.
# `run list` liefert einen erfolgreichen Deploy, `pr list` liefert nichts —
# damit haengt kein Test an echten GitHub-Daten oder an Netz.
_GH_STUB = """#!/usr/bin/env bash
args="$*"
case "$args" in
  *"run list"*)  echo "success completed 12345" ;;
  *"pr list"*)   : ;;
  *)             : ;;
esac
exit 0
"""


def _git(cwd: pathlib.Path, *args: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


def _repo(basis: pathlib.Path, name: str, *, dirty: bool) -> pathlib.Path:
    pfad = basis / name
    pfad.mkdir(parents=True)
    _git(pfad, "init", "-q", "-b", "main")
    (pfad / "README.md").write_text("x\n", encoding="utf-8")
    _git(pfad, "add", "README.md")
    _git(pfad, "commit", "-q", "-m", "init")
    if dirty:
        (pfad / "offen.txt").write_text("uncommitted\n", encoding="utf-8")
    return pfad


@pytest.fixture()
def umgebung(tmp_path: pathlib.Path) -> dict:
    """GITHUB_DIR mit zwei Repos, LEASE_DIR mit einem heutigen Lease auf `beta`.

    `PLATFORM_DIR` zeigt bewusst auf ein Attrappen-Repo OHNE die Python-Werkzeuge:
    so ist der Fehlt-Fall (SKIP) im selben Lauf mitgeprueft.
    """
    github = tmp_path / "github"
    github.mkdir()
    _repo(github, "alpha", dirty=False)
    _repo(github, "beta", dirty=True)

    platform = github / "alpha"  # Attrappe: git-Repo, aber ohne tools/-Baum
    (platform / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    _git(platform, "add", "VERSION")
    _git(platform, "commit", "-q", "-m", "version")
    _git(platform, "remote", "add", "origin", "https://github.com/testorg/alpha.git")

    leases = tmp_path / "leases"
    leases.mkdir()
    (leases / f"{_HEUTE}-test-beta-120000.json").write_text(
        '{"session_id": "x", "repo": "beta", "branch": "b"}\n', encoding="utf-8"
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(_GH_STUB, encoding="utf-8")
    gh.chmod(0o755)

    return {"github": github, "platform": platform, "leases": leases, "bin": bin_dir}


def _lauf(umgebung: dict, ziel: str = "alpha") -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_DIR": str(umgebung["github"]),
            "PLATFORM_DIR": str(umgebung["platform"]),
            "LEASE_DIR": str(umgebung["leases"]),
            "PATH": f"{umgebung['bin']}{os.pathsep}{env['PATH']}",
            # Kein Netz, kein Modell: E.5 darf nicht in einen echten
            # Ollama-Aufruf laufen.
            "OLLAMA_HOST": "http://127.0.0.1:1",
        }
    )
    return subprocess.run(
        ["bash", str(_SKRIPT), ziel],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _summary_zeilen(stdout: str) -> dict[str, str]:
    """Phasen-ID -> Statuswort aus der Summary-Tabelle."""
    zeilen = {}
    for m in re.finditer(
        r"^\| (E\.\d[^|]*?) \| \S+ (PASS|WARN|FAIL|SKIP) \|", stdout, re.M
    ):
        zeilen[m.group(1).split()[0]] = m.group(2)
    return zeilen


def test_should_pass_bash_syntax_check():
    """`bash -n` faengt genau die Klasse, die ein Runner am teuersten bezahlt."""
    ergebnis = subprocess.run(
        ["bash", "-n", str(_SKRIPT)], capture_output=True, text=True
    )
    assert ergebnis.returncode == 0, ergebnis.stderr


def test_should_be_executable():
    assert os.access(_SKRIPT, os.X_OK), "Runner muss ohne `bash` davor startbar sein"


def test_should_report_every_phase_from_e0_to_e9(umgebung):
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    fehlend = [f"E.{i}" for i in range(10) if f"E.{i}" not in phasen]
    assert not fehlend, f"Phasen fehlen in der Summary: {fehlend}\n{ergebnis.stdout}"


def test_should_end_with_result_ok_and_judgment_line(umgebung):
    ergebnis = _lauf(umgebung)
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
    assert "RESULT: OK" in ergebnis.stdout
    assert "JUDGMENT: 0a 0b 0c 0d 0e 2 3.5 — im Skill abarbeiten" in ergebnis.stdout


def test_should_warn_about_a_dirty_repo_of_this_session(umgebung):
    """Positivkontrolle fuer E.7: `beta` ist dirty UND traegt ein heutiges Lease."""
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    assert phasen["E.7"] == "WARN", ergebnis.stdout
    assert "eigene dirty: beta" in ergebnis.stdout


def test_should_not_warn_when_no_own_repo_is_dirty(tmp_path, umgebung):
    """Gegenprobe: ohne Lease auf `beta` ist dasselbe dirty Repo nur ein Hinweis."""
    for lease in umgebung["leases"].glob("*.json"):
        lease.unlink()
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    assert phasen["E.7"] == "PASS", ergebnis.stdout
    assert "fremd (nur Hinweis): beta" in ergebnis.stdout


def test_should_skip_not_pass_when_a_tool_is_missing(umgebung):
    """`NICHT messbar` ist kein Gruen — die Werkzeug-Phasen muessen SKIP sein."""
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    for phase in ("E.3", "E.4", "E.5", "E.6", "E.9"):
        assert phasen[phase] == "SKIP", (
            f"{phase} ist {phasen[phase]}\n{ergebnis.stdout}"
        )
    assert "Werkzeug fehlt" in ergebnis.stdout
    assert "HINWEIS:" in ergebnis.stdout, "SKIP-Zahl muss unter der Tabelle stehen"


def test_should_mark_worktree_reaping_as_deliberately_skipped(umgebung):
    """E.8 ist ein Streichkandidat mit Begruendung, kein vergessener Schritt."""
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.8"] == "SKIP"
    assert "0.4.5" in ergebnis.stdout


def test_should_read_touched_repos_from_todays_leases(umgebung):
    ergebnis = _lauf(umgebung)
    assert "quelle=leases" in ergebnis.stdout
    assert _summary_zeilen(ergebnis.stdout)["E.1"] == "PASS", ergebnis.stdout


def test_should_warn_when_the_last_deploy_failed(umgebung):
    """E.1-Positivkontrolle ueber den gh-Stub: `failure` darf nicht PASS werden."""
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace(
            'echo "success completed 12345"', 'echo "failure completed 999"'
        ),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    assert phasen["E.1"] == "WARN", ergebnis.stdout
    assert "nicht als fertig melden" in ergebnis.stdout.lower()


def test_should_warn_when_a_deploy_run_is_waiting(umgebung):
    """Die zweite Klasse: ein wartender Run haelt die Concurrency-Group.

    Sein `conclusion` ist null — ohne eigene Klasse zaehlt er als „kein Befund".
    """
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace('echo "success completed 12345"', 'echo "none waiting 4242"'),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.1"] == "WARN"
    assert "waiting: beta(4242)" in ergebnis.stdout


def test_should_warn_about_more_than_one_open_handover_pr(umgebung):
    """Lehre c494a2: zwei offene Handover-PRs sind konkurrierende Staende."""
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace(
            '*"pr list"*)   : ;;',
            "*\"pr list\"*)   printf '#11@2026-09-02\\n#12@2026-09-02\\n' ;;",
        ),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.2"] == "WARN", ergebnis.stdout
    assert "2 offene Handover-PRs" in ergebnis.stdout


def test_should_accept_a_single_open_handover_pr(umgebung):
    """Gegenprobe zur vorigen Zeile: einer ist der Normalfall, kein Befund."""
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace(
            '*"pr list"*)   : ;;', "*\"pr list\"*)   printf '#11@2026-09-02\\n' ;;"
        ),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.2"] == "PASS", ergebnis.stdout


def test_should_accept_a_session_id_argument(umgebung):
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_DIR": str(umgebung["github"]),
            "PLATFORM_DIR": str(umgebung["platform"]),
            "LEASE_DIR": str(umgebung["leases"]),
            "PATH": f"{umgebung['bin']}{os.pathsep}{env['PATH']}",
            "OLLAMA_HOST": "http://127.0.0.1:1",
        }
    )
    ergebnis = subprocess.run(
        ["bash", str(_SKRIPT), "alpha", "--session-id", "sitzung-42"],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
    assert "session=sitzung-42" in ergebnis.stdout
