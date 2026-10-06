"""Tests fuer tools/preflight_spiegel.py (platform#3596).

Der Spiegel darf zwei Dinge nie: anders entscheiden als der volle Stand, und mehr
veroeffentlichen, als der Preflight braucht. Beides wird gegen die echten
infra-Dateien geprueft, nicht gegen eine Stichprobe.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deploy_preflight import KNOTEN_KENNUNGEN, knoten_kennungen, pruefe  # noqa: E402
from preflight_spiegel import (  # noqa: E402
    DIENST_FELDER,
    HOSTS,
    PORTS,
    PREFLIGHT,
    dienst_auszug,
    erzeuge,
    knoten_auszug,
)

VOLL_PORTS = yaml.safe_load(PORTS.read_text(encoding="utf-8"))
VOLL_HOSTS = yaml.safe_load(HOSTS.read_text(encoding="utf-8"))


def _ziele() -> set[str | None]:
    ziele: set[str | None] = {None, "", "203.0.113.7"}
    for eintrag in VOLL_HOSTS["hosts"].values():
        ziele |= knoten_kennungen(eintrag or {})
    return ziele


def test_should_decide_like_the_full_files_for_every_app_environment_and_target():
    ports, hosts = dienst_auszug(VOLL_PORTS), knoten_auszug(VOLL_HOSTS)
    apps = [*VOLL_PORTS["services"], "gibt-es-nicht-hub"]
    abweichungen = [
        (app, env, ziel)
        for app in apps
        for env in ("production", "staging")
        for ziel in _ziele()
        if pruefe(app, env, ziel, VOLL_PORTS, VOLL_HOSTS)
        != pruefe(app, env, ziel, ports, hosts)
    ]
    assert abweichungen == []


def test_should_publish_only_the_fields_the_preflight_reads():
    erlaubt = set(KNOTEN_KENNUNGEN) | {"ssh"}
    for eintrag in dienst_auszug(VOLL_PORTS)["services"].values():
        assert set(eintrag) <= set(DIENST_FELDER)
    for eintrag in knoten_auszug(VOLL_HOSTS)["hosts"].values():
        assert set(eintrag) <= erlaubt


def test_should_drop_top_level_sections_and_ssh_users():
    hosts = knoten_auszug(VOLL_HOSTS)
    assert set(hosts) == {"hosts"}
    assert set(dienst_auszug(VOLL_PORTS)) == {"services"}
    assert not any("@" in str(e.get("ssh", "")) for e in hosts["hosts"].values())


def test_should_write_three_files_with_the_unchanged_preflight(tmp_path):
    dateien = erzeuge(tmp_path)
    assert [p.name for p in dateien] == [
        "deploy_preflight.py",
        "ports.yaml",
        "hosts.yaml",
    ]
    assert (tmp_path / "deploy_preflight.py").read_bytes() == PREFLIGHT.read_bytes()
    assert yaml.safe_load((tmp_path / "ports.yaml").read_text()) == dienst_auszug(
        VOLL_PORTS
    )
    assert yaml.safe_load((tmp_path / "hosts.yaml").read_text()) == knoten_auszug(
        VOLL_HOSTS
    )
