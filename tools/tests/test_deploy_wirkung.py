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
import json
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


def test_should_fail_repo_name_match_when_container_omits_hub_suffix():
    """Realfall illustration-hub (#2853 K2): kein Container traegt "hub" im Namen —
    der Repo-Name-Praefix trifft nichts, ohne dass das Werkzeug es kennzeichnet."""
    assert dw.laeuft("illustration-hub", {"illustration_web"}) is False


def test_should_use_declared_container_name_over_repo_name():
    """Dieselbe Lage wie oben, jetzt mit der `container_name`-Deklaration aus
    ports.yaml — das ist der Fix fuer #2853 K2."""
    assert (
        dw.laeuft(
            "illustration-hub",
            {"illustration_web", "illustration_worker"},
            container_name="illustration_web",
        )
        is True
    )


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


# ── ist_nur_doku(): Rueckstand nur aus Doku-Pfaden (#2148) ───────────────────


def test_should_recognize_a_pure_docs_backlog():
    assert dw.ist_nur_doku(
        ["docs/a.md", "AGENT_HANDOVER.md", "klickdummy/x.html", ".gitignore"]
    )


def test_should_reject_a_mixed_backlog():
    assert not dw.ist_nur_doku(["docs/a.md", "app/views.py"])


def test_should_treat_an_empty_file_list_as_not_docs_only():
    assert not dw.ist_nur_doku([])


def test_should_match_markdown_in_a_subdirectory():
    """Belegt das fnmatch-Verhalten: '*.md' matcht auch 'a/b/README.md'."""
    assert dw.ist_nur_doku(["a/b/README.md"])


# ── rueckstand_dateien(): fail-open bei jedem Werkzeugfehler ─────────────────


def test_should_treat_a_gh_failure_as_unknown(monkeypatch):
    monkeypatch.setattr(dw, "sh", lambda cmd, timeout=30: (1, ""))
    assert dw.rueckstand_dateien("writing-hub", "achimdehnert", "abc", "def") is None


def test_should_treat_a_capped_compare_result_as_unknown(monkeypatch):
    viele = json.dumps([f"f{i}.py" for i in range(300)])
    monkeypatch.setattr(dw, "sh", lambda cmd, timeout=30: (0, viele))
    assert dw.rueckstand_dateien("writing-hub", "achimdehnert", "abc", "def") is None


def test_should_return_the_file_list_on_a_normal_compare(monkeypatch):
    normal = json.dumps(["AGENT_HANDOVER.md", "AGENT_HANDOVER_ARCHIVE.md"])
    monkeypatch.setattr(dw, "sh", lambda cmd, timeout=30: (0, normal))
    assert dw.rueckstand_dateien("writing-hub", "achimdehnert", "abc", "def") == [
        "AGENT_HANDOVER.md",
        "AGENT_HANDOVER_ARCHIVE.md",
    ]


# ── rueckstand_gewollt(): stillgelegt/ruhend/blockiert ist kein Befund (#2853) ─


def test_should_treat_stillgelegt_betriebsstatus_as_intended_backlog():
    """Realfall travel-beat: `betriebsstatus: stillgelegt`, kein GitHub-lifecycle."""
    assert dw.rueckstand_gewollt(None, "stillgelegt") == "stillgelegt"


def test_should_treat_frozen_lifecycle_as_intended_backlog():
    """Die bestehende Ausnahme (coach-hub, research-hub) bleibt unveraendert gruen."""
    assert dw.rueckstand_gewollt("frozen", None) == "ruhend(frozen)"


def test_should_treat_ruhend_and_blockiert_betriebsstatus_as_intended_backlog():
    assert dw.rueckstand_gewollt(None, "ruhend") == "ruhend"
    assert dw.rueckstand_gewollt(None, "blockiert") == "blockiert"


def test_should_leave_a_normal_repo_as_a_real_backlog():
    """Positivkontrolle: ohne Status/Lifecycle bleibt ein Rueckstand ein Befund."""
    assert dw.rueckstand_gewollt(None, None) is None
    assert dw.rueckstand_gewollt("production", "aktiv") is None


# ── repo_betriebsstatus()/container_namen_aus_ports(): echte ports.yaml ──────


def test_should_find_travel_beat_as_stillgelegt_in_real_ports_yaml():
    """Ohne Naht gegen die reale Datei — sonst kann eine Attrappe alles zusagen."""
    assert dw.repo_betriebsstatus().get("travel-beat") == "stillgelegt"


def test_should_find_illustration_hub_container_name_in_real_ports_yaml():
    assert dw.container_namen_aus_ports().get("illustration-hub") == "illustration_web"
