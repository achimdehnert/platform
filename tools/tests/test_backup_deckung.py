"""Drill fuer tools/backup_deckung.py — #2284 K1: Deckung vom Host aus.

Die Fixtures unter fixtures/backup_deckung/ sind aus dem Echtlauf vom 2026-08-25
geschnitten (Auswahl je Host, Image-Namen neutralisiert, keine Adressen). Sie
tragen den Erstbefund: doc-hub-Volumes in Nutzung ohne Snapshot, verwaiste
pgdata-Volumes, ein pgdata-Volume auf prod-b, dessen Dump nicht frisch ist.

Der wichtigste Test ist die Positivkontrolle `test_should_flag_a_new_unknown_volume`:
ein Volume, das in keiner Liste steht, muss ROT sein — das ist der Unterschied zu
`backup_meter.py`, fuer den es unsichtbar waere.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backup_deckung as bd  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "backup_deckung"
NOW = datetime(2026, 8, 25, 6, 34, tzinfo=timezone.utc)
TRENNER = bd.CONTAINER_TRENNER


def _echt() -> dict:
    roh, snaps = bd.lade_fixtures(FIXTURES)
    return bd.bewerte(roh, snaps, {}, NOW)


def _host(volumes: list[dict], container: list[str]) -> str:
    return json.dumps(volumes) + "\n" + TRENNER + "\n" + "\n".join(container) + "\n"


def _vol(name: str, links: int = 1, size: str = "10MB", anonym: bool = False) -> dict:
    return {
        "Name": name,
        "Links": str(links),
        "Size": size,
        "Labels": "com.docker.volume.anonymous=" if anonym else "",
    }


def _snap(
    host: str, tags: list[str], paths: list[str], time: str = "2026-08-25T02:35:00Z"
) -> dict:
    return {"hostname": host, "tags": tags, "paths": paths, "time": time}


# --- Echtdaten: Invarianten, keine Zahlen -------------------------------------


def test_should_give_every_real_volume_exactly_one_class():
    e = _echt()
    assert e["blind"] == []
    assert all(
        v["klasse"] in ("pgdump", "volumes", "verzicht", "anonym", "UNGEDECKT")
        for v in e["volumes"]
    )
    assert sum(e["klassen"].values()) == len(e["volumes"])


def test_should_reproduce_the_first_finding_from_2026_08_25():
    """doc-hub-Volumes IN NUTZUNG ohne Snapshot — der Befund, den #2086 nicht sah."""
    rot = {v["volume"]: v for v in _echt()["volumes"] if v["klasse"] == "UNGEDECKT"}
    assert (
        "doc-hub-stack_dochub_export" in rot
        and rot["doc-hub-stack_dochub_export"]["laeuft"]
    )
    coach = rot["coach-hub_coach_hub_pgdata"]
    assert coach["links"] == 1 and not coach["laeuft"], (
        "Links zaehlt gestoppte Container mit"
    )
    assert bd._lage(coach) == "Container steht"


def test_should_cover_pgdata_by_dump_not_by_file_snapshot():
    e = _echt()
    klasse = {v["volume"]: v["klasse"] for v in e["volumes"]}
    assert klasse["risk-hub_risk_hub_pgdata"] == "pgdump"
    assert klasse["risk-hub_risk_hub_media"] == "volumes"


def test_should_exit_1_on_the_real_fixtures(capsys):
    assert (
        bd.main(["--fixtures", str(FIXTURES), "--now", NOW.isoformat(), "--kurz"]) == 1
    )
    assert "ungedeckt" in capsys.readouterr().out


# --- Positivkontrollen -------------------------------------------------------


def test_should_flag_a_new_unknown_volume():
    """Ein Volume, das nirgends steht, ist rot — nicht unsichtbar."""
    roh = {"prod": _host([_vol("neu_hub_data", links=0)], [])}
    e = bd.bewerte(roh, [], {}, NOW)
    assert e["klassen"] == {"UNGEDECKT": 1}


def test_should_accept_a_waiver_only_with_a_reason():
    roh = {"prod": _host([_vol("cache_x")], [])}
    mit = bd.bewerte(
        roh, [], {("prod", "cache_x"): {"grund": "Cache, regenerierbar"}}, NOW
    )
    ohne = bd.bewerte(roh, [], {("prod", "cache_x"): {}}, NOW)
    assert mit["klassen"] == {"verzicht": 1}
    assert ohne["klassen"] == {"UNGEDECKT": 1}
    assert ohne["volumes"][0]["durch"] == "Verzicht OHNE Grund"


def test_should_not_let_a_waiver_on_another_host_cover_this_one():
    roh = {"prod-b": _host([_vol("cache_x")], [])}
    e = bd.bewerte(roh, [], {("prod", "cache_x"): {"grund": "nur prod"}}, NOW)
    assert e["klassen"] == {"UNGEDECKT": 1}


def test_should_count_anonymous_volumes_without_judging_them():
    roh = {"prod": _host([_vol("abc123", anonym=True)], [])}
    e = bd.bewerte(roh, [], {}, NOW)
    assert e["klassen"] == {"anonym": 1}
    assert bd.kurzzeile(e).startswith("OK:")


def test_should_require_the_dump_to_be_fresh():
    """Ein Dump von vorgestern deckt nichts — das ist ADR-241 §4."""
    roh = {"prod": _host([_vol("app_pgdata")], ["/app_db|postgres:16|app|app_pgdata,"])}
    frisch = [_snap("prod", ["pgdump", "app_db"], ["/app_db.sql"])]
    alt = [
        _snap(
            "prod", ["pgdump", "app_db"], ["/app_db.sql"], time="2026-08-23T02:35:00Z"
        )
    ]
    assert bd.bewerte(roh, frisch, {}, NOW)["klassen"] == {"pgdump": 1}
    assert bd.bewerte(roh, alt, {}, NOW)["klassen"] == {"UNGEDECKT": 1}


def test_should_match_dump_by_container_name_not_by_image():
    """Das Backup-Skript sichert Container, nicht Images — der Melder auch."""
    roh = {
        "prod": _host(
            [_vol("app_pgdata")], ["/anders_benannt|postgres:16|app|app_pgdata,"]
        )
    }
    snaps = [_snap("prod", ["pgdump", "app_db"], ["/app_db.sql"])]
    assert bd.bewerte(roh, snaps, {}, NOW)["klassen"] == {"UNGEDECKT": 1}


def test_should_not_let_prod_snapshots_cover_prod_b():
    roh = {"prod-b": _host([_vol("x_media")], [])}
    snaps = [_snap("prod", ["volumes"], ["/mnt/v/docker/volumes/x_media/_data"])]
    assert bd.bewerte(roh, snaps, {}, NOW)["klassen"] == {"UNGEDECKT": 1}


# --- Blind ist nicht gruen ---------------------------------------------------


def test_should_report_unreachable_host_as_blind_not_clean():
    e = bd.bewerte(
        {"prod": None, "prod-b": _host([_vol("a", anonym=True)], [])}, [], {}, NOW
    )
    assert e["blind"] == ["prod"]
    assert "NICHT messbar" in bd.kurzzeile(e)


def test_should_report_missing_snapshots_as_blind():
    e = bd.bewerte({"prod": _host([_vol("a")], [])}, None, {}, NOW)
    assert "restic" in e["blind"]


def test_should_exit_2_when_blind(tmp_path, capsys):
    (tmp_path / "host_prod.txt").write_text("", encoding="utf-8")
    assert bd.main(["--fixtures", str(tmp_path), "--kurz"]) == 2
    assert "NICHT messbar" in capsys.readouterr().out


def test_should_treat_garbled_host_output_as_unread_not_as_empty():
    e = bd.bewerte({"prod": "ssh: connection refused"}, [], {}, NOW)
    assert e["blind"] == ["prod"]


# --- Eingaben ----------------------------------------------------------------


def test_should_read_only_prod_hosts_with_ssh(tmp_path):
    p = tmp_path / "hosts.yaml"
    p.write_text(
        "hosts:\n  prod:\n    ssh: root@1.1.1.1\n  prod-b:\n    ssh: '-'\n  staging:\n    ssh: root@2.2.2.2\n",
        encoding="utf-8",
    )
    assert bd.lade_hosts(p) == {"prod": "root@1.1.1.1"}


def test_should_load_the_real_waiver_file_without_error():
    """Die Datei ist Teil des Vertrags — sie muss parsen, auch wenn sie leer ist."""
    assert isinstance(bd.lade_verzicht(bd.VERZICHT_YAML), dict)


def test_should_never_print_an_empty_line_for_the_runner():
    """Der Sitzungsstart liest die Laenge der Ausgabe (#2280) — leer waere gruen."""
    for e in (
        _echt(),
        bd.bewerte({"prod": None}, None, {}, NOW),
        bd.bewerte({"prod": _host([], [])}, [], {}, NOW),
    ):
        assert bd.kurzzeile(e).strip()


@pytest.mark.parametrize(
    "size,mb", [("2.464GB", 2464.0), ("74.3MB", 74.3), ("0B", 0.0), ("955.8MB", 955.8)]
)
def test_should_parse_docker_sizes(size, mb):
    assert abs(bd._mb(size) - mb) < 0.01


# --- Workflow-Modus: lokal statt ssh, Scope-Luecke benannt ------------------


def test_should_run_locally_for_the_host_it_is_on_and_ssh_for_the_rest():
    """Der prod-server-Runner (root auf prod) hat keinen ssh zu sich selbst."""
    gesehen = []

    def laeufer(cmd):
        gesehen.append(cmd[0])
        return 0, ""

    bd.erhebe_live({"prod": "root@1", "prod-b": "root@2"}, laeufer, lokal={"prod"})
    assert gesehen[0] == "bash" and "ssh" in gesehen[1:]


def test_should_name_hosts_outside_the_scope_instead_of_calling_them_green(tmp_path):
    roh = {"prod": _host([_vol("a", anonym=True)], [])}
    e = bd.bewerte(roh, [], {}, NOW)
    e["ausserhalb"] = ["prod-b"]
    zeile = bd.kurzzeile(e)
    assert zeile.startswith("OK:") and "nicht im Scope: prod-b" in zeile
    assert "prod-b" in bd.bericht(e)


def test_should_exit_3_when_hosts_were_left_out_but_everything_measured_is_clean(
    tmp_path,
):
    """Retro aa58f9 #3: ohne diesen Zustand war prod-b im Workflow ein Host ohne
    Leser, der wie ein Host ohne Befund aussah. Befund (1) und blind (2) haben
    Vorrang — die Luecke ist der schwaechste, nicht der lauteste Zustand."""
    hosts = tmp_path / "hosts.yaml"
    hosts.write_text(
        "hosts:\n  prod:\n    ssh: root@1.1.1.1\n  prod-b:\n    ssh: root@2.2.2.2\n",
        encoding="utf-8",
    )
    fx = tmp_path / "fx"
    fx.mkdir()
    (fx / "host_prod.txt").write_text(
        _host([_vol("a", anonym=True)], []), encoding="utf-8"
    )
    (fx / "snapshots.json").write_text("[]", encoding="utf-8")
    rc = bd.main(
        ["--fixtures", str(fx), "--hosts", str(hosts), "--nur", "prod", "--kurz"]
    )
    assert rc == 3
