"""Tests fuer infra/scripts/hosts_audit.py — Auflage, verified-Frist, arch (KONZ-054 E5).

Vorher gab es keinen Test fuer dieses Werkzeug. Der teuerste Fall steht in
`test_should_flag_verified_false_without_deadline`: ein nacktes `verified: false`
war jahrelang ein Freifahrtschein — der Audit uebersprang den Eintrag kommentarlos.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "infra" / "scripts"))

import hosts_audit as ha  # noqa: E402

WURZEL = Path(__file__).resolve().parents[2]


def _hosts(**extra):
    basis = {
        "hosts": {
            "prod": {
                "ip": "1.1.1.1",
                "ssh": "root@1.1.1.1",
                "arch": "amd64",
                "hosts_runners": [],
                "verified": "2026-08-30",
            },
        },
        "runners": {},
    }
    basis["hosts"].update(extra)
    return basis


# ── verified-Frist ───────────────────────────────────────────────────────────


def test_should_flag_verified_false_without_deadline():
    data = _hosts(neu={"verified": False})
    treffer = [i for i in ha.check_staleness(data, 120) if "neu" in i]
    assert treffer and "verified_bis" in treffer[0]


def test_should_accept_verified_false_with_future_deadline(monkeypatch):
    monkeypatch.setattr(ha, "_today", lambda: dt.date(2026, 8, 30))
    data = _hosts(neu={"verified": False, "verified_bis": "2026-09-30"})
    assert not [i for i in ha.check_staleness(data, 120) if "neu" in i]


def test_should_flag_verified_false_with_expired_deadline(monkeypatch):
    monkeypatch.setattr(ha, "_today", lambda: dt.date(2026, 10, 15))
    data = _hosts(neu={"verified": False, "verified_bis": "2026-09-30"})
    treffer = [i for i in ha.check_staleness(data, 120) if "neu" in i]
    assert treffer and "ueberschritten" in treffer[0]


def test_should_flag_verified_false_without_deadline_in_schema_too():
    data = _hosts(neu={"verified": False})
    assert any("verified_bis" in i for i in ha.check_schema(data))


# ── arch ─────────────────────────────────────────────────────────────────────


def test_should_flag_runner_on_non_amd64_host():
    data = _hosts(
        gx10={"arch": "aarch64", "hosts_runners": ["r1"], "verified": "2026-08-30"}
    )
    data["runners"]["r1"] = {"labels": ["ci-gx10"], "status": "online", "host": "gx10"}
    assert any(i.startswith("arch:") and "gx10" in i for i in ha.check_schema(data))


def test_should_not_flag_non_amd64_host_without_runner():
    data = _hosts(
        gx10={"arch": "aarch64", "hosts_runners": [], "verified": "2026-08-30"}
    )
    assert not any(i.startswith("arch:") for i in ha.check_schema(data))


def test_should_reject_unknown_arch_value():
    data = _hosts(x={"arch": "riscv", "verified": "2026-08-30"})
    assert any("arch='riscv'" in i for i in ha.check_schema(data))


# ── Auflage-Block (Form) ─────────────────────────────────────────────────────


def test_should_require_grund_in_auflage():
    data = _hosts(n={"verified": "2026-08-30", "auflage": {"runner": False}})
    assert any("ohne 'grund'" in i for i in ha.check_schema(data))


def test_should_reject_unknown_auflage_field():
    data = _hosts(
        n={"verified": "2026-08-30", "auflage": {"grund": "x", "tippfehler": True}}
    )
    assert any("unbekannte Felder" in i for i in ha.check_schema(data))


def test_should_reject_unknown_datenklasse():
    data = _hosts(
        n={
            "verified": "2026-08-30",
            "auflage": {"grund": "x", "datenklassen_verboten": ["geheim"]},
        }
    )
    assert any("unbekannte Datenklasse 'geheim'" in i for i in ha.check_schema(data))


def test_should_flag_self_contradiction_runner_forbidden_but_declared():
    data = _hosts(
        n={
            "verified": "2026-08-30",
            "hosts_runners": ["r1"],
            "auflage": {"grund": "x", "runner": False},
        }
    )
    data["runners"]["r1"] = {"labels": ["a"], "status": "online", "host": "n"}
    assert any("widerspricht sich selbst" in i for i in ha.check_schema(data))


# ── Auflage gegen ports.yaml (Klasse f, Deklarationsebene) ───────────────────


def _ports(**dienste):
    return {"services": dienste}


def test_should_flag_service_declared_on_host_that_forbids_prod_containers():
    data = _hosts(
        dev={
            "verified": "2026-08-30",
            "auflage": {"grund": "x", "prod_container": False},
        }
    )
    ports = _ports(foo={"prod_host": "dev"})
    assert any(
        "foo" in i and "Prod-Container untersagt" in i
        for i in ha.check_auflage(data, ports)
    )


def test_should_flag_service_outside_whitelist():
    data = _hosts(
        lane={
            "verified": "2026-08-30",
            "auflage": {"grund": "x", "nur_dienste": ["risk-hub"]},
        }
    )
    ports = _ports(fremd={"prod_host": "lane"}, **{"risk-hub": {"prod_host": "lane"}})
    treffer = ha.check_auflage(data, ports)
    assert any("fremd" in i for i in treffer)
    assert not any(i.startswith("auflage: dienst 'risk-hub'") for i in treffer)


def test_should_flag_forbidden_data_class_on_host():
    data = _hosts(
        hel={
            "verified": "2026-08-30",
            "auflage": {"grund": "x", "datenklassen_verboten": ["gov-sozialdaten"]},
        }
    )
    ports = _ports(frist={"prod_host": "hel", "datenklasse": "gov-sozialdaten"})
    assert any("gov-sozialdaten" in i for i in ha.check_auflage(data, ports))


def test_should_ignore_decommissioned_services_in_auflage_check():
    data = _hosts(
        dev={
            "verified": "2026-08-30",
            "auflage": {"grund": "x", "prod_container": False},
        }
    )
    ports = _ports(alt={"prod_host": "dev", "betriebsstatus": "stillgelegt"})
    assert ha.check_auflage(data, ports) == []


def test_should_flag_service_pointing_at_unknown_host():
    ports = _ports(foo={"prod_host": "gibtsnicht"})
    assert any("gibtsnicht" in i for i in ha.check_auflage(_hosts(), ports))


# ── Positivkontrolle an den echten Dateien ───────────────────────────────────


def test_should_pass_schema_and_auflage_on_real_repo_files():
    data = yaml.safe_load((WURZEL / "infra" / "hosts.yaml").read_text())
    ports = yaml.safe_load((WURZEL / "infra" / "ports.yaml").read_text())
    assert ha.check_schema(data) == []
    # Seit 2026-08-30 (164/Lauf-2-Kritik) sind vier dev-desktop-Dienste als `blockiert`
    # deklariert und verstossen gegen auflage.prod_container=false — der Check MUSS das
    # zeigen, bis platform#2507 entschieden ist. Jeder andere Befund waere neu.
    befunde = ha.check_auflage(data, ports)
    erwartet = {"praes-iil-ai", "chat-hub", "robo-twin", "mail-links"}
    assert {b.split("'")[1] for b in befunde} == erwartet, befunde


def test_should_find_gx10_deadline_in_real_repo_file():
    data = yaml.safe_load((WURZEL / "infra" / "hosts.yaml").read_text())
    gx = data["hosts"]["gx10"]
    assert gx["verified"] is False
    assert gx["verified_bis"] >= dt.date(2026, 9, 30)
    assert gx["auflage"]["runner"] is False


def test_should_expose_every_known_host_with_ssh_and_arch_except_planned_ones():
    """Der Diabolus-Befund: 2 von 8 Knoten hatten kein ssh-Feld. Nach E5 darf das nur
    noch ein Knoten mit status: geplant."""
    data = yaml.safe_load((WURZEL / "infra" / "hosts.yaml").read_text())
    ohne = [
        n
        for n, h in data["hosts"].items()
        if not h.get("ssh") and h.get("status") != "geplant"
    ]
    assert ohne == []
    ohne_arch = [n for n, h in data["hosts"].items() if not h.get("arch")]
    assert ohne_arch == []


def test_should_flag_blocked_service_on_host_that_forbids_prod_containers():
    """Lauf-2-Kritik: `blockiert` war uebersprungen — der Check war gruen auf genau
    dem Fall, fuer den er gebaut wurde."""
    data = _hosts(
        dev={
            "verified": "2026-08-30",
            "auflage": {"grund": "x", "prod_container": False},
        }
    )
    ports = _ports(foo={"prod_host": "dev", "betriebsstatus": "blockiert"})
    assert any("foo" in i for i in ha.check_auflage(data, ports))
