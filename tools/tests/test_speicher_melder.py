"""Drill fuer tools/speicher_melder.py — #2284 K3: Vorlaufzeit statt Schwelle.

Der wichtigste Test ist `test_should_warn_seven_days_before_full_not_at_ninety_percent`:
eine Platte mit 23 % frei, die 7 GB am Tag verliert, ist in fuenf Tagen voll —
eine Schwelle bei 90 % haette dazu geschwiegen. Genau das war die Lage auf prod
am 2026-08-25 (infra-deploy#5).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import speicher_melder as sm  # noqa: E402

GB = 1_000_000_000
HEUTE = date(2026, 8, 25)


def _punkte(host: str, mount: str, *avail_gb_by_day: tuple[str, float]) -> list[dict]:
    return [
        {
            "datum": d,
            "host": host,
            "mount": mount,
            "size": 150 * GB,
            "avail": int(a * GB),
        }
        for d, a in avail_gb_by_day
    ]


def _messung(host: str, mount: str, size_gb: float, avail_gb: float) -> dict:
    return {
        host: [{"mount": mount, "size": int(size_gb * GB), "avail": int(avail_gb * GB)}]
    }


# --- Prognose ----------------------------------------------------------------


def test_should_warn_seven_days_before_full_not_at_ninety_percent():
    """23 % frei, minus 7 GB/Tag: Schwelle schweigt, Vorlauf ruft."""
    journal = _punkte(
        "prod",
        "/",
        ("2026-08-22", 57),
        ("2026-08-23", 50),
        ("2026-08-24", 43),
        ("2026-08-25", 36),
    )
    e = sm.bewerte(_messung("prod", "/", 150, 36), journal, HEUTE)
    p = e["platten"][0]
    assert p["prozent_frei"] > sm.WARN_PROZENT_FREI, (
        "die Schwelle allein haette geschwiegen"
    )
    assert p["stand"] == "belastbar" and p["warn"]
    assert 4.5 < p["tage"] < 5.5


def test_should_use_the_median_so_one_big_dump_does_not_carry_the_forecast():
    """Ein einmaliger 30-GB-Tag ist keine Rate; der Median haelt die Prognose ruhig."""
    journal = _punkte(
        "prod",
        "/",
        ("2026-08-21", 100),
        ("2026-08-22", 99),
        ("2026-08-23", 69),
        ("2026-08-24", 68),
        ("2026-08-25", 67),
    )
    p = sm.bewerte(_messung("prod", "/", 150, 67), journal, HEUTE)["platten"][0]
    assert abs(p["rate"] / GB + 1.0) < 0.01  # Median -1 GB/d, nicht Mittel -8,25
    assert not p["warn"]


def test_should_call_two_points_provisional_but_still_warn():
    """Zwei Punkte sind duenn — aber am zweiten Tag zu schweigen, waere der alte Fehler."""
    journal = _punkte("prod", "/", ("2026-08-24", 43), ("2026-08-25", 36))
    p = sm.bewerte(_messung("prod", "/", 150, 36), journal, HEUTE)["platten"][0]
    assert p["stand"] == "vorlaeufig" and p["warn"]
    assert "vorlaeufig" in sm.kurzzeile(
        sm.bewerte(_messung("prod", "/", 150, 36), journal, HEUTE)
    )


def test_should_stay_in_sammelphase_with_one_point_and_say_so():
    journal = _punkte("prod", "/", ("2026-08-25", 36))
    e = sm.bewerte(_messung("prod", "/", 150, 36), journal, HEUTE)
    assert e["platten"][0]["stand"] == "SAMMELPHASE"
    zeile = sm.kurzzeile(e)
    assert zeile.startswith("SAMMELPHASE") and "keine Vorlaufzeit" in zeile


def test_should_still_apply_the_floor_during_sammelphase():
    journal = _punkte("prod", "/", ("2026-08-25", 5))
    e = sm.bewerte(_messung("prod", "/", 150, 5), journal, HEUTE)
    assert e["platten"][0]["warn"]
    assert sm.kurzzeile(e).startswith("WARN:")


def test_should_normalise_the_rate_per_calendar_day():
    """Zwei Punkte drei Tage auseinander ergeben eine Tagesrate, keine Dreitagesrate."""
    journal = _punkte("prod", "/", ("2026-08-22", 45), ("2026-08-25", 36))
    p = sm.bewerte(_messung("prod", "/", 150, 36), journal, HEUTE)["platten"][0]
    assert abs(p["rate"] / GB + 3.0) < 0.01


def test_should_report_growing_free_space_as_stable():
    journal = _punkte(
        "prod", "/", ("2026-08-23", 30), ("2026-08-24", 33), ("2026-08-25", 36)
    )
    p = sm.bewerte(_messung("prod", "/", 150, 36), journal, HEUTE)["platten"][0]
    assert p["tage"] is None and not p["warn"]


def test_should_ignore_points_older_than_the_window():
    journal = _punkte(
        "prod", "/", ("2026-07-01", 140), ("2026-08-24", 37), ("2026-08-25", 36)
    )
    p = sm.bewerte(_messung("prod", "/", 150, 36), journal, HEUTE)["platten"][0]
    assert p["punkte"] == 2


# --- Journal -----------------------------------------------------------------


def test_should_replace_todays_point_instead_of_stacking_runs(tmp_path):
    j = tmp_path / "j.jsonl"
    sm.schreibe_journal(j, [], HEUTE, _messung("prod", "/", 150, 40))
    eintraege = sm.schreibe_journal(
        j, sm.lies_journal(j), HEUTE, _messung("prod", "/", 150, 36)
    )
    assert len(eintraege) == 1 and eintraege[0]["avail"] == 36 * GB


def test_should_keep_older_days_when_writing_today(tmp_path):
    j = tmp_path / "j.jsonl"
    sm.schreibe_journal(j, [], date(2026, 8, 24), _messung("prod", "/", 150, 43))
    eintraege = sm.schreibe_journal(
        j, sm.lies_journal(j), HEUTE, _messung("prod", "/", 150, 36)
    )
    assert sorted(e["datum"] for e in eintraege) == ["2026-08-24", "2026-08-25"]


def test_should_survive_a_corrupt_journal_line(tmp_path):
    j = tmp_path / "j.jsonl"
    j.write_text(
        '{"datum":"2026-08-24","host":"prod","mount":"/","size":1,"avail":1}\nkaputt\n',
        encoding="utf-8",
    )
    assert len(sm.lies_journal(j)) == 1


# --- Blind ist nicht gruen ---------------------------------------------------


def test_should_name_an_unreachable_host_and_not_call_it_green():
    e = sm.bewerte(
        {"prod": None, "prod-b": _messung("prod-b", "/", 300, 270)["prod-b"]}, [], HEUTE
    )
    assert e["unerreichbar"] == ["prod"] and not e["blind"]
    assert "nicht erreichbar: prod" in sm.kurzzeile(e)


def test_should_be_blind_when_no_host_answers():
    e = sm.bewerte({"prod": None, "prod-b": None}, [], HEUTE)
    assert e["blind"] and "NICHT messbar" in sm.kurzzeile(e)


def test_should_exit_2_when_blind(tmp_path, capsys):
    hosts = tmp_path / "hosts.yaml"
    hosts.write_text("hosts:\n  prod:\n    ssh: root@1.1.1.1\n", encoding="utf-8")
    leer = tmp_path / "fx"
    leer.mkdir()
    rc = sm.main(
        [
            "--hosts",
            str(hosts),
            "--df-fixtures",
            str(leer),
            "--journal",
            str(tmp_path / "j.jsonl"),
            "--kurz",
        ]
    )
    assert rc == 2 and "NICHT messbar" in capsys.readouterr().out


# --- Eingaben ----------------------------------------------------------------


def test_should_drop_boot_partitions_and_keep_data_disks():
    text = "/ 150000000000 37000000000\n/boot/efi 500000000 0\n/boot 1000000000 200000000\n/mnt/data 344000000000 224000000000\n"
    assert [p["mount"] for p in sm.parse_df(text)] == ["/", "/mnt/data"]


def test_should_read_ssh_targets_with_trailing_comments(tmp_path):
    """hosts.yaml traegt hinter `ssh:` Kommentare — der Wert endet am Leerzeichen."""
    p = tmp_path / "hosts.yaml"
    p.write_text(
        "hosts:\n  staging:\n    ssh: root@2.2.2.2              # Admin\n  x:\n    ssh: '-'\n",
        encoding="utf-8",
    )
    assert sm.lade_hosts(p) == {"staging": "root@2.2.2.2"}


def test_should_never_print_an_empty_line_for_the_runner():
    for e in (
        sm.bewerte({"prod": None}, [], HEUTE),
        sm.bewerte(_messung("prod", "/", 150, 36), [], HEUTE),
        sm.bewerte(
            _messung("prod", "/", 150, 36),
            _punkte("prod", "/", ("2026-08-24", 43), ("2026-08-25", 36)),
            HEUTE,
        ),
    ):
        assert sm.kurzzeile(e).strip()


def test_should_run_locally_for_the_host_it_is_on():
    gesehen = []

    def laeufer(cmd):
        gesehen.append(cmd[0])
        return 0, "/ 100 50\n"

    sm.messe({"prod": "root@1", "prod-b": "root@2"}, laeufer, lokal={"prod"})
    assert gesehen == ["bash", "ssh"]


def test_should_name_hosts_outside_the_scope():
    e = sm.bewerte(_messung("prod", "/", 150, 36), [], HEUTE)
    e["ausserhalb"] = ["prod-b", "netcup"]
    assert "nicht im Scope: prod-b, netcup" in sm.kurzzeile(e)


def test_should_exit_3_when_hosts_were_left_out(tmp_path):
    hosts = tmp_path / "hosts.yaml"
    hosts.write_text(
        "hosts:\n  prod:\n    ssh: root@1.1.1.1\n  prod-b:\n    ssh: root@2.2.2.2\n",
        encoding="utf-8",
    )
    fx = tmp_path / "fx"
    fx.mkdir()
    (fx / "prod.txt").write_text("/ 150000000000 100000000000\n", encoding="utf-8")
    rc = sm.main(
        [
            "--hosts",
            str(hosts),
            "--df-fixtures",
            str(fx),
            "--nur",
            "prod",
            "--journal",
            str(tmp_path / "j.jsonl"),
            "--kurz",
        ]
    )
    assert rc == 3


def test_should_ssh_ueber_den_hop_wenn_ssh_via_gesetzt_ist():
    """Knoten hinter wg0 (gpu-box, gx10) sind nur vom Hop aus erreichbar.

    Ohne diesen Weg meldete das Werkzeug fuer sie "kein Host erreichbar" und
    liess sie still aus der Zeitreihe fallen — gemessen am 2026-08-31.
    """
    gesehen: list[list[str]] = []

    def laeufer(cmd):
        gesehen.append(cmd)
        return 0, ""

    sm.messe(
        {"gx10": "adehnert@10.99.0.4"},
        laeufer,
        hops={"gx10": "root@88.198.191.108"},
    )
    assert gesehen[0][-2] == "root@88.198.191.108"
    assert gesehen[0][-1].startswith("ssh -o BatchMode=yes")
    assert "adehnert@10.99.0.4" in gesehen[0][-1]


def test_should_ohne_ssh_via_direkt_verbinden():
    """Gegenprobe: ohne Hop bleibt der Aufruf der alte, einfache."""
    gesehen: list[list[str]] = []
    sm.messe({"prod": "root@1.2.3.4"}, lambda cmd: (gesehen.append(cmd), (0, ""))[1])
    assert gesehen[0][-2] == "root@1.2.3.4"
    assert not gesehen[0][-1].startswith("ssh ")


def test_should_send_command_over_stdin_for_windows_hosts():
    """Windows-Knoten (gpu-box) bekommen den Befehl ueber stdin, nicht als Argument.

    Als Argument landet er in `cmd`, und die Pipe im df wird dort ausgefuehrt statt
    durchgereicht — deshalb meldete das Werkzeug fuer die gpu-box monatelang
    "kein Host erreichbar" (platform#2541).
    """
    gesehen = []

    def laeufer(cmd, stdin=None):
        gesehen.append((cmd, stdin))
        return 0, ""

    sm.messe(
        {"gpu-box": "achim@10.99.0.2"},
        laeufer,
        hops={"gpu-box": "root@prod"},
        shells={"gpu-box": "wsl -d Ubuntu -u root -e bash -s"},
    )
    cmd, stdin = gesehen[0]
    assert cmd[-2] == "root@prod"
    assert "wsl -d Ubuntu -u root -e bash -s" in cmd[-1]
    assert stdin is not None and "df -B1" in stdin, "der Befehl geht ueber stdin"
    assert "df -B1" not in cmd[-1], "und NICHT als Argument"


def test_should_keep_single_argument_call_for_plain_hosts():
    """Gegenprobe: ohne ssh_shell bleibt der Aufruf einargumentig.

    Ohne diesen Test waere jedes vorhandene Test-Double kaputtgegangen, ohne dass
    es auffaellt — die Aenderung darf die Aufrufkonvention nicht verschieben.
    """
    gesehen = []
    sm.messe({"prod": "root@1.2.3.4"}, lambda cmd: (gesehen.append(cmd), (0, ""))[1])
    assert "df -B1" in gesehen[0][-1]
