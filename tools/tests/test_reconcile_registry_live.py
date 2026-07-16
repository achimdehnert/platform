"""Tests fuer tools/reconcile_registry_live.py (KONZ-platform-015 Nachtrag 2026-07-10).

Issue #1199 TEST-5a (H, SURVIVES): dieses Skript ist der taegliche Prod-Cron und
die ALLEINIGE Quelle der KONZ-015-Kill-Gate-KPI (Drift-Kennzahl <=3 gesamt),
hatte aber 0 Unit-Tests. Fixture-basiert, mit den zwei laut Issue geforderten
Faellen:

  - False-Positive-Guard: ein Zustand, in dem Registry und Live-Realitaet exakt
    uebereinstimmen, darf KEINE Drift melden (sonst wuerde die KPI faelschlich
    hochgezaehlt und ein grundloser Fund-Alarm ausgeloest).
  - False-Negative-Guard: ein Zustand mit einer ECHTEN Abweichung (C1
    port_mismatch) muss zuverlaessig erkannt werden (sonst wuerde die
    Kill-Gate-KPI eine reale Drift stillschweigend verschlucken).

subprocess-Aufrufe (docker ps, getent hosts, ssh) werden NIE ausgefuehrt — alle
IO-Grenzen (`load_declared`, `load_baseline`, `live_containers`, `live_dns`)
sind hier gemonkeypatcht. Modul heisst wie eine Datei mit Unterstrich, daher
regulaerer `import`.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "reconcile_registry_live",
    pathlib.Path(__file__).resolve().parents[1] / "reconcile_registry_live.py",
)
rrl = importlib.util.module_from_spec(_SPEC)
sys.modules["reconcile_registry_live"] = rrl
_SPEC.loader.exec_module(rrl)


def _patch_io(
    monkeypatch, canonical, ports_decl, containers, baseline=None, dns_ok=True
):
    monkeypatch.setattr(rrl, "load_declared", lambda: (canonical, ports_decl))
    monkeypatch.setattr(rrl, "load_baseline", lambda: baseline or [])
    monkeypatch.setattr(rrl, "live_containers", lambda ssh: containers)
    monkeypatch.setattr(rrl, "live_dns", lambda domain, ssh: dns_ok)


def _run(monkeypatch, argv=None):
    monkeypatch.setattr(sys, "argv", ["reconcile_registry_live.py"] + (argv or []))
    return rrl.main()


# ---------------------------------------------------------------------------
# False-Positive-Guard: Registry == Live -> keine Drift, exit 0
# ---------------------------------------------------------------------------


def test_should_report_no_drift_when_registry_matches_live(monkeypatch, capsys):
    canonical = {
        "svc-a": {
            "rich": {"deployed": True},
            "flat": {"prod_url": "svc-a.example.com"},
        }
    }
    ports_decl = {
        "svc-a": {
            "prod": 8080,
            "staging": 8080,
            "dev": 8080,
            "container_name": "svc_a_web",
        },
    }
    containers = {"svc_a_web": [8080]}
    _patch_io(monkeypatch, canonical, ports_decl, containers, dns_ok=True)

    rc = _run(monkeypatch)

    out = capsys.readouterr().out
    assert rc == 0
    assert "Drift-Kennzahl: 0 gesamt" in out
    assert "Keine neue Drift" in out


# ---------------------------------------------------------------------------
# False-Negative-Guard: echte C1 port_mismatch-Divergenz MUSS erkannt werden
# ---------------------------------------------------------------------------


def test_should_detect_real_port_mismatch_c1(monkeypatch, capsys):
    canonical = {
        "svc-a": {
            "rich": {"deployed": True},
            "flat": {"prod_url": "svc-a.example.com"},
        }
    }
    ports_decl = {
        "svc-a": {
            "prod": 8080,
            "staging": 8080,
            "dev": 8080,
            "container_name": "svc_a_web",
        },
    }
    # Container laeuft, publiziert aber Port 9090 statt der deklarierten 8080.
    containers = {"svc_a_web": [9090]}
    _patch_io(monkeypatch, canonical, ports_decl, containers, dns_ok=True)

    rc = _run(monkeypatch, argv=["--skip-dns"])

    out = capsys.readouterr().out
    assert rc == 1
    assert "C1:svc-a" in out
    assert "[NEU]" in out


def test_should_detect_missing_deployed_container_c2(monkeypatch, capsys):
    """rich.deployed=true, aber der Container laeuft gar nicht (C2)."""
    canonical = {
        "svc-b": {"rich": {"deployed": True}, "flat": {}},
    }
    ports_decl = {
        "svc-b": {"prod": 8090, "container_name": "svc_b_web"},
    }
    _patch_io(monkeypatch, canonical, ports_decl, containers={}, dns_ok=True)

    rc = _run(monkeypatch, argv=["--skip-dns"])

    out = capsys.readouterr().out
    assert rc == 1
    assert "C2:svc-b" in out


def test_should_suppress_baseline_drift_but_count_it_separately(monkeypatch, capsys):
    """Ein per Baseline triagierter Drift-Fund zaehlt in die Kennzahl, aber
    loest keinen exit-1-FUND-Alarm mehr aus (E2-Waiver-Muster)."""
    canonical = {
        "svc-a": {"rich": {"deployed": True}, "flat": {}},
    }
    ports_decl = {
        "svc-a": {"prod": 8080, "container_name": "svc_a_web"},
    }
    containers = {"svc_a_web": [9090]}
    baseline = [
        {
            "id": "C1:svc-a",
            "reason": "bekannt, Klaerung offen",
            "owner": "achim",
            "expires_at": "2099-01-01",
        }
    ]
    _patch_io(
        monkeypatch, canonical, ports_decl, containers, baseline=baseline, dns_ok=True
    )

    rc = _run(monkeypatch, argv=["--skip-dns"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "Drift-Kennzahl: 1 gesamt = 0 NEU + 1 baselined" in out
    assert "[baseline] C1:svc-a" in out


def test_should_exit_2_on_unreadable_live_state(monkeypatch, capsys):
    """live_containers() wirft RuntimeError (docker ps nicht erreichbar) ->
    das ist ein TOOL-Fehler (rc=2), keine Drift-Meldung (rc=1)."""
    canonical = {}
    ports_decl = {}

    def boom(ssh):
        raise RuntimeError("docker: connection refused")

    monkeypatch.setattr(rrl, "load_declared", lambda: (canonical, ports_decl))
    monkeypatch.setattr(rrl, "load_baseline", lambda: [])
    monkeypatch.setattr(rrl, "live_containers", boom)

    rc = _run(monkeypatch, argv=["--skip-dns"])

    err = capsys.readouterr().err
    assert rc == 2
    assert "TOOL-FEHLER" in err
