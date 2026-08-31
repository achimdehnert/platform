"""Tests für tools/host_datei_drift.py (platform#2529 Befund 3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import host_datei_drift as hdd  # noqa: E402


# ── Die Glob-Invariante ──────────────────────────────────────────────────────
# Der erste Entwurf quotete jeden Ablageort. Damit expandierte die Remote-Shell
# `/home/*/.config/systemd/user/...` nicht, und acht von zwölf Kopien wurden
# stillschweigend übersehen — der Melder meldete "synchron" über Gebiet, das er
# nie angesehen hatte. Geprüft wird deshalb die Regel, nicht das Beispiel.
def test_should_leave_glob_paths_unquoted_so_remote_shell_expands_them():
    for ort in hdd.ABLAGEORTE:
        wort = hdd._remote_pfad(ort, "flottenbild.timer")
        if "*" in ort:
            assert not wort.startswith("'"), f"Glob gequotet, expandiert nie: {ort}"
        else:
            assert wort.startswith("'") and wort.endswith("'"), ort


def test_should_quote_every_non_glob_path():
    assert hdd._remote_pfad("/usr/local/bin/{name}", "a.sh") == "'/usr/local/bin/a.sh'"


def test_should_reject_names_the_remote_shell_would_interpret():
    for boese in ("a b.sh", "a;rm -rf /", "$(id).sh", "a|b", "../etc/passwd"):
        assert not hdd.SICHER.match(boese), boese
    for gut in ("prod-offsite-daily.sh", "flottenbild.timer", "daemon.json"):
        assert hdd.SICHER.match(gut), gut


# ── Quellenauswahl ───────────────────────────────────────────────────────────
def test_should_ignore_docs_that_are_never_distributed(tmp_path):
    d = tmp_path / "infra/host-maintenance"
    d.mkdir(parents=True)
    (d / "echt.sh").write_text("#!/bin/sh\n")
    (d / "README.md").write_text("# doc\n")
    (d / "runbook.md").write_text("# doc\n")
    (d / "daemon.json.recommended").write_text("{}\n")
    assert set(hdd.quelldateien(tmp_path)) == {"echt.sh"}


# ── Urteil ───────────────────────────────────────────────────────────────────
def _platform(tmp_path, inhalt="original\n"):
    d = tmp_path / "infra/host-maintenance"
    d.mkdir(parents=True)
    (d / "skript.sh").write_text(inhalt)
    (tmp_path / "infra/hosts.yaml").write_text(
        "hosts:\n  prod:\n    ssh: root@1.2.3.4\n"
    )
    return tmp_path


def test_should_report_drift_when_host_copy_differs(tmp_path, monkeypatch):
    pd = _platform(tmp_path)
    monkeypatch.setattr(
        hdd, "host_hashes", lambda ziel, namen: {"/usr/local/bin/skript.sh": "abweichend"}
    )
    drift, unpruefbar, gezaehlt = hdd.pruefe(pd)
    assert drift == ["prod:/usr/local/bin/skript.sh"]
    assert (unpruefbar, gezaehlt) == ([], 1)


def test_should_stay_silent_when_host_copy_matches(tmp_path, monkeypatch):
    pd = _platform(tmp_path)
    soll = hdd.md5(pd / "infra/host-maintenance/skript.sh")
    monkeypatch.setattr(
        hdd, "host_hashes", lambda ziel, namen: {"/usr/local/bin/skript.sh": soll}
    )
    drift, unpruefbar, gezaehlt = hdd.pruefe(pd)
    assert (drift, unpruefbar, gezaehlt) == ([], [], 1)


def test_should_treat_unreadable_host_as_gap_not_as_green(tmp_path, monkeypatch):
    # Ein Host, den wir nicht lesen konnten, ist kein Beleg für "synchron".
    pd = _platform(tmp_path)
    monkeypatch.setattr(hdd, "host_hashes", lambda ziel, namen: None)
    drift, unpruefbar, gezaehlt = hdd.pruefe(pd)
    assert (drift, unpruefbar, gezaehlt) == ([], ["prod"], 0)
