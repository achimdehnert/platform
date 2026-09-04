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


def test_should_route_blockiert_services_to_hinweise_in_pr_mode():
    data = _hosts(
        n={
            "verified": "2026-08-30",
            "auflage": {"grund": "x", "prod_container": False},
        }
    )
    ports = {
        "services": {
            "alt": {"prod_host": "n", "betriebsstatus": "blockiert"},
            "neu": {"prod_host": "n"},
        }
    }
    hinweise: list[str] = []
    befunde = ha.check_auflage(data, ports, hinweise)
    assert [b.split("'")[1] for b in befunde] == ["neu"]
    assert [h.split("'")[1] for h in hinweise] == ["alt"]


def test_should_keep_blockiert_services_as_findings_without_pr_mode():
    data = _hosts(
        n={
            "verified": "2026-08-30",
            "auflage": {"grund": "x", "prod_container": False},
        }
    )
    ports = {"services": {"alt": {"prod_host": "n", "betriebsstatus": "blockiert"}}}
    assert [b.split("'")[1] for b in ha.check_auflage(data, ports)] == ["alt"]


def test_should_pass_schema_and_auflage_on_real_repo_files():
    """Invariante statt Schnappschuss: JEDER Dienst auf einem gesperrten Knoten
    ist entweder Finding oder traegt eine gueltige, protokollierte Ausnahme.
    Lautlos durchfallen darf keiner.

    Vorher zaehlte dieser Test die vier dev-desktop-Verstoesse aus #2507 als
    feste Menge. Am 2026-09-01 wurden zwei davon zu benannten Ausnahmen — und
    der Test fiel um, obwohl die Regel eingehalten war. Dieselbe Lehre wie bei
    `test_should_keep_gx10_measured_or_under_a_deadline_in_real_repo_file`."""
    data = yaml.safe_load((WURZEL / "infra" / "hosts.yaml").read_text())
    ports = yaml.safe_load((WURZEL / "infra" / "ports.yaml").read_text())
    assert ha.check_schema(data) == []

    gesperrt = {
        name
        for name, h in data["hosts"].items()
        if (h.get("auflage") or {}).get("prod_container") is False
    }
    betroffen = {
        dienst
        for dienst, cfg in ports["services"].items()
        if isinstance(cfg, dict)
        and str(cfg.get("betriebsstatus", "aktiv")).lower() != "stillgelegt"
        and str(cfg.get("prod_host", "prod")) in gesperrt
    }
    assert betroffen, "kein Dienst auf einem gesperrten Knoten — Testaufbau kaputt"

    ha._AUSNAHME_LOG.clear()
    befunde = {b.split("'")[1] for b in ha.check_auflage(data, ports)}
    entschuldigt = {a.split("'")[1] for a in ha._AUSNAHME_LOG}

    assert befunde | entschuldigt == betroffen, (
        f"lautlos durchgefallen: {betroffen - befunde - entschuldigt}"
    )
    assert not (befunde & entschuldigt), "Dienst gleichzeitig Finding und Ausnahme"

    # PR-Modus: was `blockiert` ist, wird Hinweis — kein fremder PR wird dadurch rot.
    ha._AUSNAHME_LOG.clear()
    hinweise: list[str] = []
    assert ha.check_auflage(data, ports, hinweise) == []
    assert {h.split("'")[1] for h in hinweise} == befunde


def test_should_keep_gx10_measured_or_under_a_deadline_in_real_repo_file():
    """Der GX10 ist entweder gemessen — oder unverifiziert MIT Frist.

    Vorher pruefte dieser Test den Schnappschuss `verified is False`. Am 2026-08-31
    wurde der Knoten gemessen, und der Test fiel um, obwohl die Regel eingehalten
    war: die Ausnahme braucht eine Frist, ein gemessener Knoten braucht keine.
    Geprueft wird jetzt die Invariante, nicht der Zustand eines Tages.
    """
    data = yaml.safe_load((WURZEL / "infra" / "hosts.yaml").read_text())
    gx = data["hosts"]["gx10"]
    if gx["verified"] is False:
        assert gx["verified_bis"] >= dt.date(2026, 9, 30), (
            "unverifiziert ist nur mit Frist zulaessig (KONZ-054 E5)"
        )
    else:
        assert isinstance(gx["verified"], dt.date), "verified traegt ein Datum"
        assert "verified_bis" not in gx, "gemessen heisst: keine Frist mehr"
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


# ── Auflage-Ausnahmen (platform#2507, Owner-Entscheid 2026-09-01) ────────────
#
# Die Ausnahme ist die gefaehrlichste Erweiterung dieses Werkzeugs: sie macht
# aus einem Finding ein Schweigen. Deshalb steht zu jedem gruenen Fall hier die
# Gegenprobe — und der teuerste Fall ist die abgelaufene Frist. Eine Ausnahme,
# die niemand verlaengern muss, ist eine Auflage, die es nicht gibt.


def _ausnahme_hosts(ausnahmen=None):
    auflage = {"prod_container": False, "grund": "ADR-257"}
    if ausnahmen is not None:
        auflage["ausnahmen"] = ausnahmen
    return _hosts(
        knoten={
            "ip": "2.2.2.2",
            "ssh": "root@2.2.2.2",
            "arch": "amd64",
            "hosts_runners": [],
            "verified": "2026-08-30",
            "auflage": auflage,
        }
    )


def _ausnahme_ports(dienst="dienst-a"):
    return {"services": {dienst: {"prod_host": "knoten"}}}


def _auflage_findings(data, ports):
    ha._AUSNAHME_LOG.clear()
    return ha.check_auflage(data, ports)


def test_should_flag_service_on_locked_host_without_exception():
    """Positivkontrolle: ohne Ausnahme ist der Verstoss ein Finding."""
    treffer = _auflage_findings(_ausnahme_hosts(), _ausnahme_ports())
    assert treffer and "Prod-Container untersagt" in treffer[0]


def test_should_accept_service_with_valid_exception(monkeypatch):
    monkeypatch.setattr(ha, "_today", lambda: dt.date(2026, 9, 1))
    data = _ausnahme_hosts(
        {
            "dienst-a": {
                "grund": "Dev-Werkzeug",
                "entschieden": "2026-09-01",
                "bis": dt.date(2026, 12, 1),
            }
        }
    )
    assert not _auflage_findings(data, _ausnahme_ports())


def test_should_log_granted_exception_visibly(monkeypatch):
    """Eine Ausnahme darf nie ein Schweigen sein — sie wird immer ausgegeben,
    auch ausserhalb des PR-Modus."""
    monkeypatch.setattr(ha, "_today", lambda: dt.date(2026, 9, 1))
    data = _ausnahme_hosts(
        {
            "dienst-a": {
                "grund": "Dev-Werkzeug",
                "entschieden": "2026-09-01",
                "bis": dt.date(2026, 12, 1),
            }
        }
    )
    _auflage_findings(data, _ausnahme_ports())
    assert any("dienst-a" in z and "Dev-Werkzeug" in z for z in ha._AUSNAHME_LOG)


def test_should_flag_expired_exception():
    """Der teuerste Fall: die Frist ist durch, der Dienst laeuft weiter."""
    data = _ausnahme_hosts(
        {
            "dienst-a": {
                "grund": "Dev-Werkzeug",
                "entschieden": "2026-01-01",
                "bis": dt.date(2026, 1, 31),
            }
        }
    )
    treffer = [i for i in ha.check_schema(data) if "dienst-a" in i]
    assert treffer and "abgelaufen" in treffer[0]


def test_should_flag_exception_without_grund_datum_frist():
    data = _ausnahme_hosts({"dienst-a": {"grund": "nur ein Grund"}})
    treffer = [i for i in ha.check_schema(data) if "dienst-a" in i]
    assert treffer and "stiller Bypass" in treffer[0]


def test_should_flag_exception_with_unknown_field():
    data = _ausnahme_hosts(
        {
            "dienst-a": {
                "grund": "g",
                "entschieden": "2026-09-01",
                "bis": dt.date(2026, 12, 1),
                "dauerhaft": True,
            }
        }
    )
    assert any("unbekannte Felder" in i for i in ha.check_schema(data))


def test_should_flag_exception_with_non_date_deadline():
    data = _ausnahme_hosts(
        {"dienst-a": {"grund": "g", "entschieden": "2026-09-01", "bis": "irgendwann"}}
    )
    assert any("kein Datum" in i for i in ha.check_schema(data))


def test_should_not_let_exception_cover_a_different_service(monkeypatch):
    """Gegenprobe zur Reichweite: die Ausnahme gilt fuer EINEN Dienst, nicht
    fuer den Knoten."""
    monkeypatch.setattr(ha, "_today", lambda: dt.date(2026, 9, 1))
    data = _ausnahme_hosts(
        {
            "dienst-a": {
                "grund": "g",
                "entschieden": "2026-09-01",
                "bis": dt.date(2026, 12, 1),
            }
        }
    )
    treffer = _auflage_findings(data, _ausnahme_ports("dienst-b"))
    assert treffer and "dienst-b" in treffer[0]


def test_should_keep_echte_hosts_yaml_ausnahmen_schema_konform():
    """Der echte Stand: die beiden Ausnahmen aus #2507 sind schema-konform und
    nicht abgelaufen."""
    data = yaml.safe_load((WURZEL / "infra" / "hosts.yaml").read_text(encoding="utf-8"))
    assert not [i for i in ha.check_schema(data) if "ausnahme" in i]
