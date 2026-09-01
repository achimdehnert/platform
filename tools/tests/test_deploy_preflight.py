"""Tests fuer tools/deploy_preflight.py (KONZ-platform-054, E1).

Der Praezedenzfall ist echt: coach-hub war stillgelegt deklariert, lag laut
ports.yaml auf prod-b und wurde trotzdem auf prod deployt. Jeder Test hier
beschreibt einen Zustand, den der Preflight unterscheiden koennen muss —
insbesondere die Scope-Luecke, die kein Erfolg sein darf.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deploy_preflight import (  # noqa: E402
    EXIT_DATENFEHLER,
    EXIT_OK,
    EXIT_SCOPE,
    EXIT_VERSTOSS,
    main,
    pruefe,
)

PORTS = {
    "services": {
        "aktiv-hub": {"prod_host": "prod"},
        "wander-hub": {"prod_host": "prod-b"},
        "stillgelegt-hub": {
            "prod_host": "prod",
            "betriebsstatus": "stillgelegt",
            "betriebsstatus_grund": "Owner-Entscheid",
        },
        "blockiert-hub": {"prod_host": "prod", "betriebsstatus": "blockiert"},
        "geisterknoten-hub": {"prod_host": "gibtsnicht"},
        "knoten-ohne-adresse-hub": {"prod_host": "gx10"},
    }
}

HOSTS = {
    "hosts": {
        "prod": {
            "ip": "88.198.191.108",
            "ssh": "root@88.198.191.108",
            "ssh_alias": "hetzner-prod",
            "hostname": "ubuntu-8gb-nbg1-1",
        },
        "prod-b": {"ip": "89.167.43.30", "ssh": "root@89.167.43.30"},
        "gx10": {"hostname": None},
    }
}


def test_should_pass_when_service_is_active_and_target_is_declared_host():
    code, meldungen = pruefe("aktiv-hub", "production", "88.198.191.108", PORTS, HOSTS)
    assert code == EXIT_OK
    assert "aktiv-hub" in meldungen[0]


def test_should_block_when_service_is_decommissioned():
    code, meldungen = pruefe(
        "stillgelegt-hub", "production", "88.198.191.108", PORTS, HOSTS
    )
    assert code == EXIT_VERSTOSS
    assert "stillgelegt" in meldungen[0]
    assert "Owner-Entscheid" in meldungen[0]


def test_should_block_every_status_that_is_not_aktiv():
    code, _ = pruefe("blockiert-hub", "production", "88.198.191.108", PORTS, HOSTS)
    assert code == EXIT_VERSTOSS


def test_should_block_when_target_host_is_a_different_declared_node():
    code, meldungen = pruefe("wander-hub", "production", "88.198.191.108", PORTS, HOSTS)
    assert code == EXIT_VERSTOSS
    assert "prod-b" in meldungen[0]
    assert "prod" in meldungen[0]


def test_should_pass_when_target_is_written_as_ssh_user_at_host():
    code, _ = pruefe("wander-hub", "production", "root@89.167.43.30", PORTS, HOSTS)
    assert code == EXIT_OK


def test_should_pass_when_target_is_written_as_ssh_alias():
    code, _ = pruefe("aktiv-hub", "production", "hetzner-prod", PORTS, HOSTS)
    assert code == EXIT_OK


def test_should_report_scope_gap_when_service_is_not_declared():
    code, meldungen = pruefe(
        "unbekannt-hub", "production", "88.198.191.108", PORTS, HOSTS
    )
    assert code == EXIT_SCOPE
    assert code != EXIT_OK
    assert "Scope-Luecke" in meldungen[0]


def test_should_report_scope_gap_when_declared_node_is_unknown():
    code, meldungen = pruefe(
        "geisterknoten-hub", "production", "88.198.191.108", PORTS, HOSTS
    )
    assert code == EXIT_SCOPE
    assert "gibtsnicht" in meldungen[0]


def test_should_report_scope_gap_when_node_has_no_address_at_all():
    code, meldungen = pruefe(
        "knoten-ohne-adresse-hub", "production", "88.198.191.108", PORTS, HOSTS
    )
    assert code == EXIT_SCOPE
    assert "gx10" in meldungen[0]


def test_should_report_scope_gap_when_target_matches_no_known_node():
    code, meldungen = pruefe("aktiv-hub", "production", "10.0.0.1", PORTS, HOSTS)
    assert code == EXIT_SCOPE
    assert "10.0.0.1" in meldungen[0]


def test_should_report_scope_gap_when_target_is_empty():
    code, _ = pruefe("aktiv-hub", "production", "", PORTS, HOSTS)
    assert code == EXIT_SCOPE


def test_should_skip_host_check_for_staging_but_keep_status_check():
    code_aktiv, _ = pruefe("wander-hub", "staging", "irgendwas", PORTS, HOSTS)
    code_still, _ = pruefe("stillgelegt-hub", "staging", "irgendwas", PORTS, HOSTS)
    assert code_aktiv == EXIT_OK
    assert code_still == EXIT_VERSTOSS


def test_should_exit_with_data_error_when_source_is_unreadable(tmp_path):
    fehlt = tmp_path / "gibtsnicht.yaml"
    code = main(["--app", "aktiv-hub", "--ports", str(fehlt), "--hosts", str(fehlt)])
    assert code == EXIT_DATENFEHLER


def test_should_block_the_real_coach_hub_case_from_the_repos_own_declaration():
    """Positivkontrolle an echten Daten: findet der Preflight den Realfall wieder?"""
    wurzel = Path(__file__).resolve().parents[2]
    code = main(
        [
            "--app",
            "coach-hub",
            "--environment",
            "production",
            "--deploy-host",
            "88.198.191.108",
            "--ports",
            str(wurzel / "infra" / "ports.yaml"),
            "--hosts",
            str(wurzel / "infra" / "hosts.yaml"),
        ]
    )
    assert code == EXIT_VERSTOSS


@pytest.mark.parametrize(
    "app,ziel,erwartet",
    [("aktiv-hub", "88.198.191.108", EXIT_OK), ("wander-hub", "89.167.43.30", EXIT_OK)],
)
def test_should_not_block_correctly_routed_deploys(app, ziel, erwartet):
    code, _ = pruefe(app, "production", ziel, PORTS, HOSTS)
    assert code == erwartet
