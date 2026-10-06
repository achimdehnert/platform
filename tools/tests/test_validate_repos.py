"""Tests fuer infra/scripts/validate_repos.py::check_ports_consistency.

platform#3477: 8 Inkonsistenzen zwischen infra/ports.yaml und der Registry,
u.a. weil der Check archivierte Hubs wie aktive behandelte und Infra-Dienste
(ohne eigenes GitHub-Repo) wie Repo-Dienste forderte. Owner-Entscheide
(#3471, #3477):

  1. Ein archiviertes Repo mit ports.yaml-Eintrag ist KEIN Befund mehr, wird
     aber gezaehlt (Info-Zeile) — der ports.yaml-Eintrag selbst bleibt stehen.
  2. Der Check unterscheidet Repo-Dienste (services:-Eintrag MIT `repo:`,
     nicht-leer) von Infra-Diensten (kein `repo:`-Schluessel oder
     `repo: null`). Nur Repo-Dienste MUESSEN in der Registry stehen.

Rein lokal mit synthetischen Registry-/ports-Dicts — kein echtes ports.yaml,
kein echter Registry-Load noetig.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parents[2] / "infra" / "scripts" / "validate_repos.py"
)
_spec = importlib.util.spec_from_file_location("validate_repos", _SCRIPT)
vr = importlib.util.module_from_spec(_spec)
sys.modules["validate_repos"] = vr
_spec.loader.exec_module(vr)


def _registry(**over):
    """Ein minimaler Registry-Eintrag im Shape von get_all_registry_repos()."""
    basis = {
        "github": "achimdehnert/beispiel-hub",
        "deployed": True,
        "port_prod": 8080,
        "_type": "django",
        "_lifecycle": "production",
        "_archived": False,
    }
    basis.update(over)
    return basis


# --- Entscheid 1: archiviert -> uebersprungen, nicht gemeldet --------------


def test_should_skip_an_archived_repo_still_present_in_ports_yaml():
    registry = {"alt-hub": _registry(_archived=True, _lifecycle="archived")}
    ports = {"alt-hub": {"repo": "achimdehnert/alt-hub", "prod": 8080}}

    issues, archived_skipped = vr.check_ports_consistency(registry, ports)

    assert issues == []
    assert archived_skipped == 1


# --- Entscheid 2: Infra-Dienst ohne Registry -> kein Befund ----------------


def test_should_not_flag_an_infra_service_with_explicit_repo_null():
    registry: dict = {}
    ports = {"doc-hub": {"repo": None, "prod": 8102}}

    issues, archived_skipped = vr.check_ports_consistency(registry, ports)

    assert issues == []
    assert archived_skipped == 0


def test_should_not_flag_an_infra_service_missing_the_repo_key_entirely():
    registry: dict = {}
    ports = {"grafana": {"prod": 3000}}

    issues, archived_skipped = vr.check_ports_consistency(registry, ports)

    assert issues == []


# --- Positivkontrolle: Repo-Dienst ohne Registry bleibt ein Befund ---------


def test_should_flag_a_repo_service_without_a_registry_entry():
    registry: dict = {}
    ports = {"chat-hub": {"repo": "iilgmbh/chat-hub", "prod": 8008}}

    issues, archived_skipped = vr.check_ports_consistency(registry, ports)

    assert issues == ["ports.yaml 'chat-hub' nicht in Registry"]
    assert archived_skipped == 0


def test_should_resolve_a_repo_service_via_the_repo_name_fallback():
    # lotse-raum/chathub-rtc-livekit-* tragen alle repo: iilgmbh/chat-hub,
    # obwohl der Service-Name selbst nicht "chat-hub" heisst — der Fallback
    # ueber den Repo-Namen darf sie nicht als fehlend melden, sobald das
    # Repo selbst registriert ist.
    registry = {"chat-hub": _registry(github="iilgmbh/chat-hub", _type="other")}
    ports = {"lotse-raum": {"repo": "iilgmbh/chat-hub", "prod": None}}

    issues, archived_skipped = vr.check_ports_consistency(registry, ports)

    assert issues == []


def test_should_still_flag_a_real_port_mismatch():
    registry = {"beispiel-hub": _registry(port_prod=8080)}
    ports = {"beispiel-hub": {"repo": "achimdehnert/beispiel-hub", "prod": 9999}}

    issues, archived_skipped = vr.check_ports_consistency(registry, ports)

    assert issues == ["'beispiel-hub' port_prod: ports.yaml=9999 registry=8080"]
