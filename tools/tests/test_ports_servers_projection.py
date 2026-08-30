"""S1 (KONZ-054 §12): `servers:` in ports.yaml ist eine Projektion von hosts.yaml.

Der teuerste Fall steht in `test_should_fail_when_projection_drifts_from_hosts`:
bis 2026-08-30 meinte `staging` in beiden Dateien verschiedene Maschinen, und
kein Werkzeug hat es gemerkt — weil keines beide Dateien gegeneinander las.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL / "infra" / "scripts"))

import server_probe as sp  # noqa: E402
import validate_ports as vp  # noqa: E402


def _real():
    return (
        yaml.safe_load((WURZEL / "infra" / "ports.yaml").read_text()),
        yaml.safe_load((WURZEL / "infra" / "hosts.yaml").read_text()),
    )


def test_should_accept_the_real_projection():
    ports, hosts = _real()
    assert vp.validate_servers(ports, hosts) == []


def test_should_require_a_host_reference_per_environment():
    ports, hosts = _real()
    for env, s in ports["servers"].items():
        assert s.get("host") in hosts["hosts"], env


def test_should_fail_when_projection_drifts_from_hosts():
    ports, hosts = _real()
    ports["servers"]["dev"]["ip"] = "10.0.0.1"
    fehler = vp.validate_servers(ports, hosts)
    assert any("servers.dev" in f and "10.0.0.1" in f for f in fehler)


def test_should_fail_when_host_reference_is_missing_or_unknown():
    ports, hosts = _real()
    ports["servers"]["dev"].pop("host")
    ports["servers"]["prod"]["host"] = "gibtsnicht"
    fehler = vp.validate_servers(ports, hosts)
    assert any("servers.dev" in f and "fehlt" in f for f in fehler)
    assert any("servers.prod" in f and "gibtsnicht" in f for f in fehler)


def test_should_have_renamed_the_dev_desktop_key():
    """`staging` als Host-Key ist weg — der Name gehoert der Umgebung, nicht der Maschine."""
    _, hosts = _real()
    assert "staging" not in hosts["hosts"]
    assert hosts["hosts"]["dev-desktop"]["ip"] == "88.99.38.75"
    assert all(r.get("host") != "staging" for r in hosts["runners"].values())


def test_should_load_server_probe_targets_from_hosts_yaml():
    """server_probe verdrahtete 2 IPs hart; jetzt kommen sie aus der SoT."""
    assert sp.SERVERS["prod"] == "88.198.191.108"
    assert sp.SERVERS["dev"] == "88.99.38.75"
    assert sp.SERVERS["staging"] == "178.104.184.168"
    assert len(sp.ALLE_HOSTS) >= 7
    assert "netcup" in sp.ALLE_HOSTS and "gpu-box" in sp.ALLE_HOSTS
