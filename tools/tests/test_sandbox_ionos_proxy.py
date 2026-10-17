"""Tests fuer tools/sandbox/ionos_proxy.py (ADR-308) — IONOS wird durch eine Attrappe ersetzt."""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "sandbox" / "ionos_proxy.py"
_spec = importlib.util.spec_from_file_location("ionos_proxy", _SCRIPT)
ip = importlib.util.module_from_spec(_spec)
sys.modules["ionos_proxy"] = ip
_spec.loader.exec_module(ip)

KONFIG = {
    "datacenter": "dc",
    "server": "srv",
    "volume": "vol",
    "benutzer": "agent@example.invalid",
    "passwort_datei": "/nicht/benutzt",
    "snapshot_praefix": "agent-",
    "max_eigene_snapshots": 1,
    "geschuetzte_snapshots": ["erst"],
    "mindestabstand_s": {"/neustart": 300, "/snapshot": 3600},
}


def _snap(sid: str, name: str, angelegt: str) -> dict:
    return {
        "id": sid,
        "properties": {"name": name, "size": 480.0},
        "metadata": {"createdDate": angelegt, "state": "AVAILABLE"},
    }


class Attrappe:
    """Spielt die Cloud API v6 nach und merkt sich jeden Aufruf."""

    def __init__(self, snapshots: list[dict] | None = None):
        self.aufrufe: list[tuple[str, str, dict | None]] = []
        self.snapshots = snapshots if snapshots is not None else []

    def anfrage(self, methode, pfad, form=None):
        self.aufrufe.append((methode, pfad, form))
        if pfad.startswith("/snapshots?"):
            return 200, {"items": self.snapshots}
        if methode == "GET" and pfad.endswith("/servers/srv"):
            return 200, {"properties": {"name": "s1", "vmState": "RUNNING"}, "metadata": {"state": "AVAILABLE"}}
        if methode == "GET" and pfad.endswith("/volumes/vol"):
            return 200, {"properties": {"size": 480}}
        if pfad.endswith("/remoteconsole"):
            return 200, {"url": "https://konsole.example.invalid/x"}
        if pfad.endswith("/create-snapshot"):
            return 202, {"id": "neu"}
        return 202, {}

    def schreibende(self):
        return [(m, p) for m, p, _ in self.aufrufe if m != "GET"]


class Uhr:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_should_allow_only_listed_actions():
    assert ip.aktion_erlaubt("GET", "/zustand")
    assert ip.aktion_erlaubt("POST", "/snapshot/")
    assert not ip.aktion_erlaubt("GET", "/snapshot")
    assert not ip.aktion_erlaubt("DELETE", "/zustand")
    assert not ip.aktion_erlaubt("POST", "/datacenters/dc/servers")
    assert not ip.aktion_erlaubt("POST", "/neustart/../servers")


def test_should_refuse_unlisted_action_without_calling_ionos():
    attrappe = Attrappe()
    proxy = ip.Proxy(KONFIG, attrappe)
    with pytest.raises(ip.Verweigert) as fehler:
        proxy.fuehre_aus("POST", "/datacenters/dc/servers", {})
    assert fehler.value.status == 403
    assert attrappe.aufrufe == []


def test_should_delete_oldest_own_snapshot_before_creating_new_one():
    attrappe = Attrappe(
        [
            _snap("erst", "agent-schutz", "2026-10-17T09:00:00Z"),
            _snap("a1", "agent-20261017-1000", "2026-10-17T10:00:00Z"),
            _snap("fremd", "manuell", "2026-10-16T10:00:00Z"),
        ]
    )
    antwort = ip.Proxy(KONFIG, attrappe).fuehre_aus("POST", "/snapshot", {})
    assert antwort["geloescht"] == ["a1"]
    assert attrappe.schreibende() == [
        ("DELETE", "/snapshots/a1"),
        ("POST", "/datacenters/dc/volumes/vol/create-snapshot"),
    ]


def test_should_never_delete_protected_or_foreign_snapshots():
    snapshots = [
        {"id": "erst", "name": "agent-x", "angelegt": "1"},
        {"id": "fremd", "name": "manuell", "angelegt": "0"},
    ]
    assert ip.zu_loeschen(snapshots, KONFIG) == []


def test_should_restore_only_own_or_protected_snapshots():
    attrappe = Attrappe([_snap("a1", "agent-1", "1"), _snap("fremd", "manuell", "0")])
    proxy = ip.Proxy(KONFIG, attrappe)
    with pytest.raises(ip.Verweigert) as fehler:
        proxy.fuehre_aus("POST", "/zurueckspielen", {"snapshot": "fremd"})
    assert fehler.value.status == 403
    proxy.fuehre_aus("POST", "/zurueckspielen", {"snapshot": "erst"})
    assert attrappe.aufrufe[-1] == (
        "POST",
        "/datacenters/dc/volumes/vol/restore-snapshot",
        {"snapshotId": "erst"},
    )


def test_should_enforce_minimum_interval_per_action():
    uhr = Uhr()
    proxy = ip.Proxy(KONFIG, Attrappe(), uhr=uhr)
    proxy.fuehre_aus("POST", "/neustart", {})
    uhr.t += 299
    with pytest.raises(ip.Verweigert) as fehler:
        proxy.fuehre_aus("POST", "/neustart", {})
    assert fehler.value.status == 429
    uhr.t += 2
    assert proxy.fuehre_aus("POST", "/neustart", {}) == {"angestossen": "neustart"}


def test_should_report_state_with_history_for_next_model():
    attrappe = Attrappe([_snap("a1", "agent-1", "1")])
    proxy = ip.Proxy(KONFIG, attrappe)
    proxy.protokolliere(entscheidung="erlaubt", aktion="/neustart", methode="POST")
    zustand = proxy.fuehre_aus("GET", "/zustand", {})
    assert zustand["server"]["vm_status"] == "RUNNING"
    assert [s["id"] for s in zustand["snapshots"]] == ["a1"]
    assert zustand["verlauf"][0]["aktion"] == "/neustart"


def test_should_answer_403_over_http_for_unlisted_paths():
    proxy = ip.Proxy(KONFIG, Attrappe())
    server = ip.starte(("127.0.0.1", 0), proxy)
    basis = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anfrage = urllib.request.Request(basis + "/datacenters", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as fehler:
            urllib.request.urlopen(anfrage)
        assert fehler.value.code == 403
        with urllib.request.urlopen(basis + "/zustand") as antwort:
            assert json.loads(antwort.read())["volume"]["groesse_gb"] == 480
    finally:
        server.shutdown()


def test_should_reject_config_missing_required_fields(tmp_path):
    datei = tmp_path / "k.json"
    datei.write_text(json.dumps({"datacenter": "dc"}))
    with pytest.raises(ValueError, match="es fehlen"):
        ip.lade_konfig(datei)


def test_should_keep_example_config_complete():
    beispiel = _SCRIPT.parent / "ionos_proxy.beispiel.json"
    assert set(ip.PFLICHTFELDER) <= set(json.loads(beispiel.read_text()))
