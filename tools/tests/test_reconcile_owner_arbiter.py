"""Drill fuer den Registry-Schiedsrichter in agent_handover_reconcile.py (#2006).

Der Anlass ist eine Messung, nicht eine Idee: der Report vom 2026-08-16 trug 20
Eintraege, davon 12 `UNKNOWN` mit `gh: Not Found (HTTP 404)`. Sie sahen alle
gleich aus, waren es aber nicht. **Vier** davon (`risk-hub#596`, `tax-hub#119`,
`ttz-hub#28`, `frist-hub#117`) fragten ein Repo ab, das es nicht gibt — der
Parser hatte mangels Owner im Text `achimdehnert` angenommen, real liegen sie in
`iilgmbh`, `ttz-lif` bzw. `meiki-lra`. Die uebrigen sind private Repos ohne
Token-Zugriff. Die API antwortet in beiden Faellen 404, und genau daran waren sie
nicht auseinanderzuhalten.

Zwei Tests halten die teuersten Fehlformen fest:

- `test_should_correct_an_assumed_owner_instead_of_blaming_the_document` — der
  erste Entwurf meldete alle vier als „Adressfehler im Handover". Falsch: bei
  `frist-hub#117` stand die richtige URL auf derselben Zeile, gelesen wurde nur
  der Label-Text. Ein Werkzeug, das seine eigene Annahme dem Dokument als Fehler
  vorhaelt, ist schlimmer als eines, das schweigt.
- `test_should_stay_silent_when_the_registry_is_missing` — ohne Registry liefert
  der Aufloeser fuer JEDES Repo `None`. Ein naiver Schiedsrichter wuerde dann die
  komplette Flotte als „unbekanntes Repo" melden: maximal laut bei fehlender
  Datenbasis.

`gh` wird nie ausgefuehrt: die Owner-Pruefung liegt bewusst VOR dem API-Aufruf.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "agent_handover_reconcile",
    _ROOT / "scripts" / "checks" / "agent_handover_reconcile.py",
)


@pytest.fixture
def rec():
    mod = importlib.util.module_from_spec(_SPEC)
    sys.modules[_SPEC.name] = mod
    _SPEC.loader.exec_module(mod)
    return mod


def _ref(rec, owner: str, repo: str, number: int = 1, explizit: bool = True):
    return rec.Ref(
        owner=owner,
        repo=repo,
        number=number,
        line_no=1,
        line="egal",
        owner_explizit=explizit,
    )


def test_should_flag_an_explicit_link_with_the_wrong_org(rec, monkeypatch) -> None:
    """Nur ein im TEXT stehender Owner kann falsch sein."""
    monkeypatch.setattr(rec, "registry_verfuegbar", lambda: True)
    monkeypatch.setattr(rec._reg, "owner", lambda name: "ttz-lif")
    _, urteil = rec.schiedsrichter(_ref(rec, "achimdehnert", "ttz-hub", 28))
    assert urteil is not None
    klass, detail = urteil
    assert klass == "FALSCHE_ORG"
    assert "ttz-lif/ttz-hub" in detail and "achimdehnert/ttz-hub" in detail


def test_should_correct_an_assumed_owner_instead_of_blaming_the_document(
    rec, monkeypatch
) -> None:
    """Der teuerste Fehler des ersten Entwurfs — hier als Test festgenagelt.

    `frist-hub#117` traegt keinen Owner im Text; der Parser nahm `achimdehnert` an.
    Der erste Entwurf meldete das als „Adressfehler im Handover" — obwohl auf
    derselben Zeile die RICHTIGE URL (`meiki-lra/frist-hub`) stand. Eine eigene
    Annahme dem Dokument als Fehler vorzuhalten ist schlimmer als Schweigen.
    """
    monkeypatch.setattr(rec, "registry_verfuegbar", lambda: True)
    monkeypatch.setattr(rec._reg, "owner", lambda name: "meiki-lra")
    ref, urteil = rec.schiedsrichter(
        _ref(rec, "achimdehnert", "frist-hub", 117, explizit=False)
    )
    assert urteil is None, "eine Annahme ist kein Befund"
    assert ref.owner == "meiki-lra", "und sie wird korrigiert, nicht nur geschluckt"


def test_should_flag_a_repo_the_registry_does_not_know(rec, monkeypatch) -> None:
    monkeypatch.setattr(rec, "registry_verfuegbar", lambda: True)
    monkeypatch.setattr(rec._reg, "owner", lambda name: None)
    _, urteil = rec.schiedsrichter(_ref(rec, "achimdehnert", "gibt-es-nicht"))
    assert urteil and urteil[0] == "UNBEKANNTES_REPO"


def test_should_not_blame_an_unknown_repo_when_the_owner_was_only_assumed(
    rec, monkeypatch
) -> None:
    monkeypatch.setattr(rec, "registry_verfuegbar", lambda: True)
    monkeypatch.setattr(rec._reg, "owner", lambda name: None)
    _, urteil = rec.schiedsrichter(_ref(rec, "achimdehnert", "neu-hub", explizit=False))
    assert urteil is None


def test_should_pass_through_a_correctly_addressed_reference(rec, monkeypatch) -> None:
    """Kein Urteil = der API-Aufruf entscheidet. Sonst waere jede Zeile ein Befund."""
    monkeypatch.setattr(rec, "registry_verfuegbar", lambda: True)
    monkeypatch.setattr(rec._reg, "owner", lambda name: "achimdehnert")
    assert rec.schiedsrichter(_ref(rec, "achimdehnert", "platform", 2006))[1] is None


def test_should_stay_silent_when_the_registry_is_missing(rec, monkeypatch) -> None:
    """Ohne Datenbasis wird NICHT geurteilt — nicht „alles unbekannt" gemeldet."""
    monkeypatch.setattr(rec, "registry_verfuegbar", lambda: False)
    ref, urteil = rec.schiedsrichter(_ref(rec, "wer-auch-immer", "was-auch-immer"))
    assert urteil is None and ref.owner == "wer-auch-immer"


def test_should_call_the_real_registry_and_resolve_the_known_overrides(rec) -> None:
    """Gegen die ECHTE Registry, nicht gegen eine Attrappe.

    Die drei Overrides sind der Grund, warum der Schiedsrichter ueberhaupt urteilen
    kann. Waeren sie eines Tages weg, meldete er die Referenzen als korrekt und
    dieser Drill waere die einzige Stelle, die es merkt.
    """
    assert rec.registry_verfuegbar()
    assert rec._reg.owner("frist-hub") == "meiki-lra"
    assert rec._reg.owner("ttz-hub") == "ttz-lif"
    assert rec._reg.owner("tax-hub") == "iilgmbh"
    assert rec._reg.owner("platform") == "achimdehnert"


def test_should_separate_a_404_from_a_real_api_error(rec, monkeypatch) -> None:
    """404 bei korrektem Owner ist eine Luecke; ein anderer Fehler bleibt UNKNOWN."""

    class _Proc:
        def __init__(self, rc, err):
            self.returncode, self.stderr, self.stdout = rc, err, ""

    monkeypatch.setattr(
        rec.subprocess, "run", lambda *a, **k: _Proc(1, "gh: Not Found (HTTP 404)")
    )
    klass, detail = rec.query_state(_ref(rec, "achimdehnert", "risk-hub", 596))
    assert klass == "NICHT_PRUEFBAR"
    assert "privat oder geloescht" in detail

    monkeypatch.setattr(
        rec.subprocess, "run", lambda *a, **k: _Proc(1, "gh: API rate limit exceeded")
    )
    klass, _ = rec.query_state(_ref(rec, "achimdehnert", "risk-hub", 596))
    assert klass == "UNKNOWN"


# ── Owner-spezifische Tokens (platform#2006, GitHub App) ─────────────────────
# Gemessen 2026-08-16: derselbe Handover ergab mit dem Repo-Token
# `DISKREPANZ 8 · nicht pruefbar 12`, mit Flotten-Sicht `DISKREPANZ 18 · 0`.
# Zehn echte veraltete Referenzen waren unsichtbar.


def test_should_derive_the_env_name_from_the_owner(rec) -> None:
    assert rec.token_env_name("iilgmbh") == "RECONCILE_TOKEN_IILGMBH"
    assert rec.token_env_name("meiki-lra") == "RECONCILE_TOKEN_MEIKI_LRA"
    assert rec.token_env_name("ttz-lif") == "RECONCILE_TOKEN_TTZ_LIF"


def test_should_fall_back_when_no_org_token_is_set(rec, monkeypatch) -> None:
    """Fehlende App-Installation darf den Lauf NICHT rot faerben.

    Ein dauerrot laufender Nightly wird abgeschaltet und meldet danach gar nichts
    mehr (#1508). Fehlt der Token, bleibt es beim Default — die betroffenen
    Referenzen landen wie bisher unter „nicht pruefbar".
    """
    monkeypatch.delenv("RECONCILE_TOKEN_IILGMBH", raising=False)
    assert rec.token_fuer("iilgmbh") is None


def test_should_treat_an_empty_token_as_absent(rec, monkeypatch) -> None:
    """`steps.x.outputs.token` ist ein LEERER String, wenn der Schritt uebersprungen
    wurde — nicht unset. Ohne diese Behandlung liefe `gh` mit GH_TOKEN='' und
    schluege fuer jede Referenz fehl."""
    monkeypatch.setenv("RECONCILE_TOKEN_IILGMBH", "")
    assert rec.token_fuer("iilgmbh") is None
    monkeypatch.setenv("RECONCILE_TOKEN_IILGMBH", "   ")
    assert rec.token_fuer("iilgmbh") is None


def test_should_use_the_org_token_for_that_owner_only(rec, monkeypatch) -> None:
    gesehen = {}

    class _Proc:
        returncode, stderr, stdout = 0, "", '{"state": "open"}'

    def _fake_run(cmd, **kw):
        gesehen[cmd[2]] = (kw.get("env") or {}).get("GH_TOKEN")
        return _Proc()

    monkeypatch.setenv("RECONCILE_TOKEN_IILGMBH", "ghs_org_token")
    monkeypatch.delenv("RECONCILE_TOKEN_ACHIMDEHNERT", raising=False)
    monkeypatch.setenv("GH_TOKEN", "default_token")
    monkeypatch.setattr(rec.subprocess, "run", _fake_run)

    rec.query_state(_ref(rec, "iilgmbh", "risk-hub", 596))
    rec.query_state(_ref(rec, "achimdehnert", "platform", 1))

    assert gesehen["repos/iilgmbh/risk-hub/issues/596"] == "ghs_org_token"
    assert gesehen["repos/achimdehnert/platform/issues/1"] == "default_token"


def test_should_say_deleted_not_private_when_an_org_token_was_used(
    rec, monkeypatch
) -> None:
    """Mit Org-Token ist 404 eine andere Aussage — das gehoert in den Text."""

    class _Proc:
        returncode, stderr, stdout = 1, "gh: Not Found (HTTP 404)", ""

    monkeypatch.setattr(rec.subprocess, "run", lambda *a, **k: _Proc())
    monkeypatch.setenv("RECONCILE_TOKEN_IILGMBH", "ghs_org_token")
    _, detail = rec.query_state(_ref(rec, "iilgmbh", "risk-hub", 596))
    assert "geloescht/umbenannt" in detail
    monkeypatch.delenv("RECONCILE_TOKEN_IILGMBH")
    _, detail = rec.query_state(_ref(rec, "iilgmbh", "risk-hub", 596))
    assert "privat oder geloescht" in detail
