"""Drill fuer tools/deploy_wirkung.py — Wirkung statt Zettel (platform#2148).

Das Werkzeug hatte bis hierhin **keinen** Drill. Gepruft wird der Teil, der ohne
SSH auskommt und in dem der Fehler sass: die Beurteilung, ob ein Repo auf einem
Host wirklich laeuft — und was ein Manifest ohne Betrieb bedeutet.

Realfall (2026-08-20, #2148): `trading-hub` hatte auf prod-a ein 254-Byte-Manifest
vom 18.08. und **null** Container, auf prod-b fuenf laufende. Gemeldet wurde
`DOPPELLAUF:prod,prod-b` — die Meldung, die man am wenigsten abstumpfen lassen
darf, an einem Fall, in dem nichts doppelt lief.
"""

import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "deploy_wirkung", TOOLS / "deploy_wirkung.py"
)
dw = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = dw
_spec.loader.exec_module(dw)


# ── laeuft(): Namensformen, die Compose wirklich erzeugt ─────────────────────


def test_should_compose_suffix_als_lauf_erkennen():
    assert dw.laeuft("trading-hub", {"trading-hub-web-1", "trading-hub-db-1"}) is True


def test_should_unterstrich_und_bindestrich_gleich_behandeln():
    assert dw.laeuft("trading_hub", {"trading-hub-web-1"}) is True


def test_should_fremden_container_nicht_als_lauf_werten():
    assert dw.laeuft("trading-hub", {"tax-hub-web-1", "postgres"}) is False


def test_should_unbekannte_containerlage_als_unbekannt_durchreichen():
    """`None` heisst „nicht gefragt", nicht „nichts da"."""
    assert dw.laeuft("trading-hub", None) is None


# ── beurteile_hosts(): der eigentliche Befund ────────────────────────────────


def test_should_verwaistes_manifest_nicht_als_doppellauf_werten():
    """Der Realfall trading-hub: Zettel auf prod, Betrieb auf prod-b."""
    laufend, verwaist, unklar = dw.beurteile_hosts(
        ["prod", "prod-b"], {"prod": False, "prod-b": True}
    )
    assert laufend == ["prod-b"]
    assert verwaist == ["prod"]
    assert unklar is False
    assert len(laufend) <= 1, "kein Doppellauf, wenn nur ein Host bedient"


def test_should_echten_doppellauf_weiterhin_melden():
    """Positivkontrolle — ohne sie waere die Praezisierung nur eine Abschaltung."""
    laufend, verwaist, unklar = dw.beurteile_hosts(
        ["prod", "prod-b"], {"prod": True, "prod-b": True}
    )
    assert laufend == ["prod", "prod-b"]
    assert verwaist == []
    assert len(laufend) > 1


def test_should_unklare_containerlage_nicht_zu_entwarnung_machen():
    """Kein `docker ps` ⇒ die Aussage bleibt offen, nicht gruen."""
    _, _, unklar = dw.beurteile_hosts(
        ["prod", "prod-b"], {"prod": None, "prod-b": True}
    )
    assert unklar is True


def test_should_komplett_gestopptes_repo_nicht_verwaist_nennen():
    """Ueberall aus ist ein Zustand, kein Aufraeum-Auftrag.

    Ohne die Bedingung „mindestens ein Host bedient es wirklich" wuerde jedes
    stillgelegte Repo als verwaistes Manifest gemeldet — neues Rauschen an der
    Stelle, an der gerade Rauschen entfernt wird.
    """
    laufend, verwaist, _ = dw.beurteile_hosts(
        ["prod", "prod-b"], {"prod": False, "prod-b": False}
    )
    assert laufend == []
    assert verwaist == []


def test_should_einzelnen_host_unberuehrt_lassen():
    laufend, verwaist, unklar = dw.beurteile_hosts(["prod-b"], {"prod-b": True})
    assert (laufend, verwaist, unklar) == (["prod-b"], [], False)


# ── laufende_container(): Fehlschlag ist kein leeres Ergebnis ────────────────


def test_should_ssh_fehlschlag_als_unbekannt_melden(monkeypatch):
    monkeypatch.setattr(dw, "sh", lambda cmd, timeout=60: (255, ""))
    assert dw.laufende_container("root@example") is None


def test_should_leere_containerliste_von_fehlschlag_unterscheiden(monkeypatch):
    monkeypatch.setattr(dw, "sh", lambda cmd, timeout=60: (0, ""))
    assert dw.laufende_container("root@example") == set()
