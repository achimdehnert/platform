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
        hdd,
        "host_hashes",
        lambda ziel, namen, ssh_via=None, ssh_shell=None: {
            "/usr/local/bin/skript.sh": "abweichend"
        },
    )
    drift, unpruefbar, schlaeft, gezaehlt = hdd.pruefe(pd)
    assert drift == ["prod:/usr/local/bin/skript.sh"]
    assert (unpruefbar, schlaeft, gezaehlt) == ([], [], 1)


def test_should_stay_silent_when_host_copy_matches(tmp_path, monkeypatch):
    pd = _platform(tmp_path)
    soll = hdd.md5(pd / "infra/host-maintenance/skript.sh")
    monkeypatch.setattr(
        hdd,
        "host_hashes",
        lambda ziel, namen, ssh_via=None, ssh_shell=None: {
            "/usr/local/bin/skript.sh": soll
        },
    )
    drift, unpruefbar, schlaeft, gezaehlt = hdd.pruefe(pd)
    assert (drift, unpruefbar, schlaeft, gezaehlt) == ([], [], [], 1)


def test_should_treat_unreadable_host_as_gap_not_as_green(tmp_path, monkeypatch):
    # Ein Host, den wir nicht lesen konnten, ist kein Beleg für "synchron".
    pd = _platform(tmp_path)
    monkeypatch.setattr(
        hdd, "host_hashes", lambda ziel, namen, ssh_via=None, ssh_shell=None: None
    )
    drift, unpruefbar, schlaeft, gezaehlt = hdd.pruefe(pd)
    assert (drift, unpruefbar, schlaeft, gezaehlt) == ([], ["prod"], [], 0)


# ── ssh_via / ssh_shell / auf_zuruf (platform#2774) ──────────────────────────
# Die beiden Melder bauten das ssh-Kommando bisher nur aus `ssh` und erklärten
# GPU-Box/GX10 (Zugang nur über den prod-Hop) fälschlich für "nicht lesbar".
def test_should_route_command_through_hop_when_ssh_via_is_set(monkeypatch):
    erfasst = {}

    def fake_run(cmd, **kwargs):
        erfasst["cmd"] = cmd
        erfasst["kwargs"] = kwargs

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(hdd.subprocess, "run", fake_run)
    hdd.host_hashes(
        "achim@10.99.0.2",
        ["skript.sh"],
        ssh_via="root@88.198.191.108",
        ssh_shell="wsl -d Ubuntu -u root -e bash -s",
    )
    cmd = erfasst["cmd"]
    assert cmd[-2] == "root@88.198.191.108"
    assert "achim@10.99.0.2" in cmd[-1]
    assert "wsl -d Ubuntu -u root -e bash -s" in cmd[-1]
    # Das Skript geht per stdin durch beide Verbindungen, nicht als
    # Kommandozeilen-Argument durch zwei Shells hindurch zitiert.
    assert "input" in erfasst["kwargs"]


def test_should_call_host_directly_without_ssh_via(monkeypatch):
    erfasst = {}

    def fake_run(cmd, **kwargs):
        erfasst["cmd"] = cmd
        erfasst["kwargs"] = kwargs

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(hdd.subprocess, "run", fake_run)
    hdd.host_hashes("root@1.2.3.4", ["skript.sh"])
    cmd = erfasst["cmd"]
    assert cmd[-2] == "root@1.2.3.4"
    assert "input" not in erfasst["kwargs"]


def test_should_mark_unresponsive_auf_zuruf_host_as_sleeping_not_as_gap(
    tmp_path, monkeypatch
):
    pd = _platform(tmp_path)
    (pd / "infra/hosts.yaml").write_text(
        "hosts:\n"
        "  prod:\n    ssh: root@1.2.3.4\n"
        "  gpu-box:\n    ssh: achim@10.99.0.2\n"
        "    ssh_via: root@88.198.191.108\n"
        "    betrieb: auf_zuruf\n"
    )
    soll = hdd.md5(pd / "infra/host-maintenance/skript.sh")

    def fake(ziel, namen, ssh_via=None, ssh_shell=None):
        if ziel == "root@1.2.3.4":
            return {"/usr/local/bin/skript.sh": soll}
        return None  # gpu-box antwortet nicht — schläft, kein Ausfall

    monkeypatch.setattr(hdd, "host_hashes", fake)
    drift, unpruefbar, schlaeft, gezaehlt = hdd.pruefe(pd)
    assert drift == []
    assert unpruefbar == []
    assert schlaeft == ["gpu-box"]
    assert gezaehlt == 1


# ── Versionsmarker (platform#2529) ───────────────────────────────────────────
# Ein Hash sagt "weicht ab". Erst der Marker sagt, WIE weit: prod-b lief am
# 2026-08-31 sechs Tage zurueck und hatte deshalb nie einen config-Snapshot —
# aus einem blossen Hash-Unterschied war das nicht ablesbar.
def _mit_marker(tmp_path, repo_version):
    d = tmp_path / "infra/host-maintenance"
    d.mkdir(parents=True)
    (d / "skript.sh").write_text(f'#!/bin/sh\nOFFSITE_SH_VERSION="{repo_version}"\n')
    (tmp_path / "infra/hosts.yaml").write_text(
        "hosts:\n  prod:\n    ssh: root@1.2.3.4\n"
    )
    return tmp_path


def test_should_name_both_versions_when_a_marked_file_drifts(tmp_path, monkeypatch):
    pd = _mit_marker(tmp_path, "2026-08-31.1")
    pfad = "/usr/local/bin/skript.sh"

    def fake(ziel, namen, ssh_via=None, ssh_shell=None):
        hdd.VERSIONEN[pfad] = "2026-08-25.0"
        return {pfad: "abweichend"}

    monkeypatch.setattr(hdd, "host_hashes", fake)
    drift, _, _, _ = hdd.pruefe(pd)
    assert drift == [f"prod:{pfad} (Host 2026-08-25.0 / Repo 2026-08-31.1)"]


def test_should_stay_plain_when_the_file_carries_no_marker(tmp_path, monkeypatch):
    # Ohne Marker bleibt die Meldung wie bisher — kein leeres Klammerpaar.
    d = tmp_path / "infra/host-maintenance"
    d.mkdir(parents=True)
    (d / "ohne.sh").write_text("#!/bin/sh\necho hi\n")
    (tmp_path / "infra/hosts.yaml").write_text(
        "hosts:\n  prod:\n    ssh: root@1.2.3.4\n"
    )
    monkeypatch.setattr(
        hdd,
        "host_hashes",
        lambda z, n, ssh_via=None, ssh_shell=None: {
            "/usr/local/bin/ohne.sh": "abweichend"
        },
    )
    drift, _, _, _ = hdd.pruefe(tmp_path)
    assert drift == ["prod:/usr/local/bin/ohne.sh"]


def test_should_not_leak_versions_between_runs(tmp_path, monkeypatch):
    # VERSIONEN ist Modulzustand. Ohne Ruecksetzung faerbte ein alter Lauf den
    # naechsten ein — eine Klasse Fehler, die nur bei Mehrfachlaeufen auftritt.
    pd = _mit_marker(tmp_path, "2026-08-31.1")
    hdd.VERSIONEN["/usr/local/bin/skript.sh"] = "uralt"
    monkeypatch.setattr(
        hdd, "host_hashes", lambda z, n, ssh_via=None, ssh_shell=None: {}
    )
    hdd.pruefe(pd)
    assert hdd.VERSIONEN == {}
