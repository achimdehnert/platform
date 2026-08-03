"""Tests fuer tools/fleet_checkout.py (platform#1508-Triage).

Der Melder war aus zwei Gruenden unzuverlaessig: veraltete Klone erzeugten
Fehlalarme, und Fremd-Org-Repos fielen still aus der Erhebung. Beide Zustaende
sind hier festgenagelt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

import fleet_checkout as fc  # noqa: E402


@pytest.fixture
def canon():
    """Minimal-Registry mit genau den Faellen, die real vorkommen."""
    return {
        "meta": {
            "server": {"github_org": "achimdehnert"},
            "repo_owner": {"iil-klickdummy": "iilgmbh", "frist-hub": "meiki-lra"},
            "owner_prefix_rules": [
                {"prefix": "meiki-", "owner": "meiki-lra"},
                {"prefix": "ttz-", "owner": "ttz-lif"},
            ],
        },
        "repos": {
            "dev-hub": {"flat": {}},
            "design-hub": {"flat": {}},
            "meiki-hub": {"flat": {}},
            "ttz-hub": {"flat": {}},
            "frist-hub": {"flat": {}},
            "iil-klickdummy": {"flat": {}},
        },
    }


def test_should_trennen_eigene_von_fremden_orgs(canon):
    plan = fc.plane(
        [
            "dev-hub",
            "design-hub",
            "meiki-hub",
            "ttz-hub",
            "frist-hub",
            "iil-klickdummy",
        ],
        canon,
    )
    assert sorted(r for r, _ in plan["eigene"]) == [
        "design-hub",
        "dev-hub",
        "iil-klickdummy",
    ]
    assert sorted(plan["fremd"]) == [
        ("frist-hub", "meiki-lra"),
        ("meiki-hub", "meiki-lra"),
        ("ttz-hub", "ttz-lif"),
    ]
    assert plan["unbekannt"] == []


def test_should_unbekanntes_repo_nicht_der_default_org_zuschlagen(canon):
    """Ein Name ohne Registry-Eintrag darf nicht still bei achimdehnert landen."""
    plan = fc.plane(["voellig-unbekannt-hub"], canon)
    assert plan["unbekannt"] == ["voellig-unbekannt-hub"]
    assert plan["eigene"] == []


def test_should_echte_registry_nur_ttzlif_und_meikilra_ausschliessen():
    """Ohne Test-Naht: gegen die echte registry/canonical.yaml.

    Die Grenze verlaeuft NICHT zwischen `achimdehnert` und allem anderen,
    sondern zwischen der eigenen Governance-Domaene (`achimdehnert` +
    `iilgmbh`, ADR-255-Migrationsziel) und fremden Orgs. Ein erster Entwurf
    schloss `iilgmbh` mit aus und haette risk-hub, tax-hub,
    ausschreibungs-hub und vier `iil-*`-Bibliotheken ungescannt gelassen.
    """
    plan = fc.plane(
        [
            "frist-hub",
            "meiki-hub",
            "ttz-hub",
            "iil-klickdummy",
            "iil-voice-agent",
            "risk-hub",
            "tax-hub",
            "dev-hub",
        ]
    )
    fremd = dict(plan["fremd"])
    assert fremd == {
        "frist-hub": "meiki-lra",
        "meiki-hub": "meiki-lra",
        "ttz-hub": "ttz-lif",
    }
    eigene = dict(plan["eigene"])
    assert eigene["risk-hub"] == "iilgmbh"
    assert eigene["tax-hub"] == "iilgmbh"
    assert eigene["iil-klickdummy"] == "iilgmbh"
    assert eigene["iil-voice-agent"] == "iilgmbh"
    assert eigene["dev-hub"] == "achimdehnert"


def test_should_abdeckung_fremde_repos_namentlich_nennen(canon):
    plan = fc.plane(["dev-hub", "meiki-hub", "ttz-hub"], canon)
    bericht = fc.render_coverage(plan, {"dev-hub": "aktualisiert"}, {})
    assert "1 von 3 Fleet-Repos gescannt" in bericht
    assert "`meiki-hub` → `meiki-lra`" in bericht
    assert "`ttz-hub` → `ttz-lif`" in bericht
    assert fc.FREMD_ORG_GRUND in bericht


def test_should_fehlschlag_der_eigenen_org_als_ausfall_ausweisen(canon):
    plan = fc.plane(["dev-hub", "design-hub"], canon)
    bericht = fc.render_coverage(
        plan, {"dev-hub": "aktualisiert"}, {"design-hub": "fatal: 404"}
    )
    assert "1 fehlgeschlagen" in bericht
    assert "echter Ausfall" in bericht
    assert "`design-hub`: fatal: 404" in bericht


def test_should_registry_luecke_sichtbar_machen(canon):
    plan = fc.plane(["dev-hub", "neues-hub"], canon)
    bericht = fc.render_coverage(plan, {"dev-hub": "geklont"}, {})
    assert "Registry-Luecke" in bericht
    assert "`neues-hub`" in bericht


def test_should_token_niemals_in_der_ausgabe_stehen():
    geheim = "ghs_ATTRAPPE_nur_fuer_den_test"
    url = fc.klon_url("achimdehnert", "dev-hub", geheim)
    assert geheim in url  # geht an git, nicht in den Log
    fehlertext = f"fatal: could not read from '{url}'"
    assert geheim not in fc._ohne_token(fehlertext, geheim)
    assert "***" in fc._ohne_token(fehlertext, geheim)


def test_should_ohne_token_unveraendert_durchreichen():
    assert fc._ohne_token("fatal: repo not found", None) == "fatal: repo not found"


def test_should_klon_url_ohne_token_kein_platzhalter():
    assert fc.klon_url("achimdehnert", "dev-hub", None) == (
        "https://github.com/achimdehnert/dev-hub.git"
    )


def test_should_dry_run_kein_git_aufrufen(monkeypatch, tmp_path, capsys):
    """--dry-run darf weder klonen noch fetchen."""

    def explodiere(*a, **k):  # pragma: no cover - darf nie laufen
        raise AssertionError("git wurde trotz --dry-run aufgerufen")

    monkeypatch.setattr(fc, "_git", explodiere)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fleet_checkout.py",
            "--base",
            str(tmp_path),
            "--repos",
            "dev-hub",
            "--dry-run",
        ],
    )
    assert fc.main() == 0
    assert "Abdeckung des Scans" in capsys.readouterr().out


def test_should_exit_1_bei_fehlschlag_der_eigenen_org(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "herstellen", lambda *a, **k: (False, "fatal: 404"))
    monkeypatch.setattr(
        sys,
        "argv",
        ["fleet_checkout.py", "--base", str(tmp_path), "--repos", "dev-hub"],
    )
    assert fc.main() == 1


def test_should_exit_0_wenn_nur_fremde_orgs_uebrig_bleiben(monkeypatch, tmp_path):
    """Eine benannte Grenze ist kein Ausfall — sonst waere der Melder dauerrot."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fleet_checkout.py",
            "--base",
            str(tmp_path),
            "--repos",
            "meiki-hub",
            "ttz-hub",
        ],
    )
    assert fc.main() == 0


def test_should_vorhandenen_klon_aktualisieren_statt_zu_ueberspringen(
    monkeypatch, tmp_path
):
    """Kern-Regression: der Vorzustand liess vorhandene Klone unberuehrt."""
    ziel = tmp_path / "dev-hub"
    (ziel / ".git").mkdir(parents=True)
    gerufen: list[list[str]] = []

    def fake_git(args, cwd=None, timeout=120):
        gerufen.append(args)
        return 0, ""

    monkeypatch.setattr(fc, "_git", fake_git)
    monkeypatch.setattr(
        sys,
        "argv",
        ["fleet_checkout.py", "--base", str(tmp_path), "--repos", "dev-hub"],
    )
    assert fc.main() == 0
    assert ["fetch", "--depth=1", "origin", "HEAD"] in gerufen
    assert ["reset", "--hard", "FETCH_HEAD"] in gerufen
