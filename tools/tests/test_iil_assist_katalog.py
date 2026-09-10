"""Tests fuer tools/iil_assist_katalog.py (platform#3011, Kriterien 6 und 7)."""

import copy
import datetime as dt
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import iil_assist_katalog as ik  # noqa: E402


@pytest.fixture
def katalog():
    return ik.lade(ik.KATALOG)


def test_should_accept_the_shipped_catalog(katalog):
    assert ik.pruefe(katalog) == []


def test_should_reject_missing_field_and_bad_enum(katalog):
    d = copy.deepcopy(katalog)
    del d["dienste"][0]["gate"]
    d["dienste"][1]["datenklasse"] = "geheim"
    fehler = ik.pruefe(d)
    assert any("Feld fehlt: gate" in f for f in fehler)
    assert any("datenklasse='geheim'" in f for f in fehler)


def test_should_reject_personal_data_open_in_chat(katalog):
    d = copy.deepcopy(katalog)
    x = next(x for x in d["dienste"] if x["datenklasse"] == "personenbezogen")
    x["chat_eignung"] = "ja"
    x["gate"] = "keins"
    fehler = ik.pruefe(d)
    assert any("Charta Art. 2" in f for f in fehler)
    assert any("braucht ein Gate" in f for f in fehler)


def test_should_require_exactly_five_mvps_over_three_repos(katalog):
    d = copy.deepcopy(katalog)
    for x in d["dienste"]:
        x["mvp"] = x["repo"] == "dev-hub"
    fehler = ik.pruefe(d)
    assert any("genau 5 MVPs" in f for f in fehler)
    assert any("mindestens 3 Repos" in f for f in fehler)


def test_should_derive_next_step_from_state_not_history(katalog):
    d = copy.deepcopy(katalog)
    d["phase"] = "konzept"
    assert ik.naechster_schritt(d)[0] == "owner"
    d["phase"] = "bau"
    for x in d["dienste"]:
        if x["mvp"]:
            x["status"] = "vorgeschlagen"
    wer, was = ik.naechster_schritt(d)
    assert wer == "ich" and "Plattform-Status" in was and "bauen" in was
    next(x for x in d["dienste"] if x["id"] == "plattform-status")["status"] = "gebaut"
    assert "Staging" in ik.naechster_schritt(d)[1]
    for x in d["dienste"]:
        if x["mvp"]:
            x["status"] = "staging"
    assert "Bilanz" in ik.naechster_schritt(d)[1]


def test_should_render_briefing_with_top3_and_mvps(katalog):
    text = ik.briefing(katalog)
    assert "## Top 3" in text and "## Die fuenf MVPs" in text
    assert text.count("\n- ") >= 8
    assert "iil-assist-hub" in text


def test_should_rank_blocked_repo_first_in_wartung(katalog, monkeypatch):
    monkeypatch.setattr(ik, "_betriebsstatus", lambda: {"frist-hub": "blockiert"})
    monkeypatch.setattr(ik, "_commit_alter_tage", lambda repo, heute: 5)
    monkeypatch.setattr(ik.reg, "repo", lambda n: {"lifecycle": "production"})
    lauf = ik.bahn_wartung(katalog, dt.date(2026, 9, 10))
    assert lauf["kippt_als_naechstes"][0]["dienst"] == "fristen-auskunft"
    assert "betriebsstatus=blockiert" in lauf["kippt_als_naechstes"][0]["gruende"]
    assert lauf["datum"] == "2026-09-10"


def test_should_write_run_into_catalog_and_keep_header(katalog, tmp_path):
    ziel = tmp_path / "k.yaml"
    ziel.write_text(ik.KATALOG.read_text(encoding="utf-8"), encoding="utf-8")
    d = ik.lade(ziel)
    d["bahnen"]["wartung"]["laeufe"].append({"datum": "2026-09-10", "gemessen": 1})
    ik.speichere(d, ziel)
    text = ziel.read_text(encoding="utf-8")
    assert text.startswith("# iil-assist")
    assert yaml.safe_load(text)["bahnen"]["wartung"]["laeufe"][0]["gemessen"] == 1
    assert ik.pruefe(yaml.safe_load(text)) == []
