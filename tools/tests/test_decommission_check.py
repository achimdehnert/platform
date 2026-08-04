"""Decommission-Gate: tote Hostnamen und IPs in laufender Konfiguration finden.

Das Werkzeug entscheidet mit, ob ein Repo stillgelegt werden darf. Beide
Fehlrichtungen sind teuer, aber verschieden: ein Fehlalarm blockiert eine
Stilllegung, ein uebersehener Marker laesst Konfiguration zurueck, die auf einen
abgeschalteten Host zeigt.

Die Kommentarzeilen-Heuristik hat einen belegten Ursprung: beim ersten scharfen
Lauf am 2026-07-17 meldete das Werkzeug weltenhub/docker-compose.prod.yml als
Fund, obwohl der tote Name dort nur in zwei Kommentarzeilen stand. Dieser Fall
steht unten als eigener Test, damit der Fix nicht still zurueckgebaut wird.
"""

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "decommission_check.py"
_spec = importlib.util.spec_from_file_location("decommission_check", _SRC)
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)

HOSTS = ["alt-hub.example"]
IPS = ["10.9.9.9"]


@pytest.fixture()
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


def datei(d: pathlib.Path, name: str, inhalt: str) -> pathlib.Path:
    p = d / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(inhalt, encoding="utf-8")
    return p


def test_should_find_a_dead_hostname_in_a_live_line(repo):
    p = datei(repo, ".env", "DB_HOST=alt-hub.example\n")

    assert dc.scan_file(p, HOSTS, IPS) == ["alt-hub.example"]


def test_should_find_a_dead_ip(repo):
    p = datei(repo, ".env", "UPSTREAM=10.9.9.9\n")

    assert dc.scan_file(p, HOSTS, IPS) == ["10.9.9.9"]


def test_should_ignore_a_dead_marker_that_only_appears_in_a_comment(repo):
    # der Realfall vom 2026-07-17 (weltenhub) — Fehlalarm vor dem Fix
    p = datei(
        repo, "docker-compose.prod.yml", "# frueher: alt-hub.example\nservices: {}\n"
    )

    assert dc.scan_file(p, HOSTS, IPS) == []


def test_should_still_flag_a_line_where_the_comment_is_not_at_the_start(repo):
    # ein nachgestellter Kommentar macht den Runtime-Wert davor nicht harmlos
    p = datei(repo, ".env", "DB_HOST=alt-hub.example  # alt\n")

    assert dc.scan_file(p, HOSTS, IPS) == ["alt-hub.example"]


def test_should_ignore_indented_comment_lines(repo):
    p = datei(repo, "docker-compose.yml", "services:\n    # alt-hub.example war hier\n")

    assert dc.scan_file(p, HOSTS, IPS) == []


def test_should_report_each_marker_only_once_per_file(repo):
    p = datei(repo, ".env", "A=alt-hub.example\nB=alt-hub.example\n")

    assert dc.scan_file(p, HOSTS, IPS) == ["alt-hub.example"]


def test_should_return_nothing_for_an_unreadable_path(repo):
    assert dc.scan_file(repo / "gibtsnicht.env", HOSTS, IPS) == []


def test_should_return_nothing_when_no_marker_is_configured(repo):
    p = datei(repo, ".env", "DB_HOST=alt-hub.example\n")

    assert dc.scan_file(p, [], []) == []


def test_should_collect_findings_across_the_default_globs(repo):
    datei(repo, ".env.prod", "DB_HOST=alt-hub.example\n")
    datei(repo, "docker-compose.yml", "image: 10.9.9.9/app\n")
    datei(repo, "README.md", "alt-hub.example steht nur in der Doku\n")

    funde = dc.scan_repo(repo, HOSTS, IPS)

    namen = {pathlib.Path(k).name for k in funde}
    assert namen == {".env.prod", "docker-compose.yml"}
    assert "README.md" not in namen


def test_should_not_scan_a_plain_env_file(repo):
    """DEFAULT_GLOBS ist bewusst eng: `.env.prod`/`.env.staging`, nicht `.env`.

    Beim Schreiben dieser Tests bin ich darauf hereingefallen und hatte `.env`
    als gescannt angenommen. Der Fall haelt die Entscheidung fest, damit sie
    beim naechsten Umbau bewusst getroffen wird statt versehentlich zu kippen —
    wer sie aufweicht, zieht Entwickler-`.env` mit in den Scan.
    """
    datei(repo, ".env", "DB_HOST=alt-hub.example\n")

    assert dc.scan_repo(repo, HOSTS, IPS) == {}
    # explizit uebergeben wird sie sehr wohl geprueft
    assert dc.scan_repo(repo, HOSTS, IPS, extra_files=[".env"]) != {}


def test_should_scan_an_extra_file_outside_the_default_globs(repo):
    datei(repo, "deploy/custom.conf", "server alt-hub.example;\n")

    funde = dc.scan_repo(repo, HOSTS, IPS, extra_files=["deploy/custom.conf"])

    assert [pathlib.Path(k).name for k in funde] == ["custom.conf"]


def test_should_return_empty_findings_for_a_clean_repo(repo):
    datei(repo, ".env", "DB_HOST=neu-hub.example\n")

    assert dc.scan_repo(repo, HOSTS, IPS) == {}
