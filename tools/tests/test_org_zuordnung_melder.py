"""Tests fuer den ADR-297-Org-Zuordnungs-Melder.

Der wichtigste Test ist `test_should_detect_drift_behind_redirect`: GitHub
beantwortet `repos/<falscher-owner>/<name>` mit 200 und leitet still um. Ein
Melder, der den angefragten Pfad zurueckliest, bestaetigt seine eigene Behauptung
und meldet nie etwas — genau die Blindstelle, aus der ADR-297 entstanden ist.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from org_zuordnung_melder import (  # noqa: E402
    Registry,
    check_a,
    check_b,
    check_c,
    main,
    real_owner,
)

STICHTAG = "2026-08-24"


def _registry(repos: dict, repo_owner: dict | None = None) -> Registry:
    return Registry(
        repos=repos,
        repo_owner=repo_owner or {},
        prefix_rules=[
            {"prefix": "meiki-", "owner": "meiki-lra"},
            {"prefix": "ttz-", "owner": "ttz-lif"},
        ],
        default_owner="achimdehnert",
    )


def _antwort(owner: str, angelegt: str = "2020-01-01T00:00:00Z") -> dict:
    return {"owner": {"login": owner}, "created_at": angelegt}


# --- Owner-Aufloesung ---------------------------------------------------------


def test_should_prefer_override_over_prefix_rule():
    reg = _registry({"meiki-dms": {}}, repo_owner={"meiki-dms": "iilgmbh"})
    assert reg.deklarierter_owner("meiki-dms") == "iilgmbh"


def test_should_apply_prefix_rule_when_no_override():
    assert _registry({"ttz-hub": {}}).deklarierter_owner("ttz-hub") == "ttz-lif"


def test_should_fall_back_to_default_owner():
    assert _registry({"dev-hub": {}}).deklarierter_owner("dev-hub") == "achimdehnert"


# --- Check A: zwei Wahrheitsstaende in einer Datei ----------------------------


def test_should_flag_registry_internal_disagreement():
    reg = _registry(
        {"risk-hub": {"rich": {"github": "achimdehnert/risk-hub"}}},
        repo_owner={"risk-hub": "iilgmbh"},
    )
    funde = check_a(reg)
    assert [f.check for f in funde] == ["A"]
    assert funde[0].erwartet == "iilgmbh"
    assert funde[0].gefunden == "achimdehnert"


def test_should_stay_silent_when_registry_agrees_with_itself():
    reg = _registry(
        {"risk-hub": {"rich": {"github": "iilgmbh/risk-hub"}}},
        repo_owner={"risk-hub": "iilgmbh"},
    )
    assert check_a(reg) == []


# --- Check B: die Redirect-Falle ---------------------------------------------


def test_should_detect_drift_behind_redirect():
    """Die Antwort kommt mit 200 — aber unter einem anderen Owner.

    Der Melder darf den angefragten Pfad NICHT als Bestaetigung lesen.
    """
    reg = _registry({"risk-hub": {}})  # Registry behauptet achimdehnert (Default)
    angefragt: list[tuple[str, str]] = []

    def fetch(owner, name):
        angefragt.append((owner, name))
        return _antwort("iilgmbh")  # GitHub leitet still um

    funde, unerreichbar = check_b(reg, fetch)
    assert angefragt == [("achimdehnert", "risk-hub")]
    assert unerreichbar == []
    assert len(funde) == 1
    assert (funde[0].erwartet, funde[0].gefunden) == ("achimdehnert", "iilgmbh")


def test_should_stay_silent_when_owner_matches():
    """Positivkontrolle: ohne sie belegt ein leeres Ergebnis nichts."""
    reg = _registry({"dev-hub": {}})
    funde, unerreichbar = check_b(reg, lambda o, n: _antwort("achimdehnert"))
    assert funde == [] and unerreichbar == []


def test_should_report_unreachable_repo_as_unchecked_not_as_clean():
    reg = _registry({"geheim-hub": {}})
    funde, unerreichbar = check_b(reg, lambda o, n: None)
    assert funde == []
    assert unerreichbar == ["geheim-hub"]


def test_should_treat_missing_payload_as_unknown_owner():
    assert real_owner(None) is None
    assert real_owner({}) is None


# --- Check C: Leitsatz nur fuer Neuzugaenge ----------------------------------


PROD = {"rich": {"github": "achimdehnert/neu-hub", "lifecycle": "production"}}


def test_should_flag_new_productive_repo_on_personal_account():
    reg = _registry({"neu-hub": PROD})
    funde = check_c(
        reg,
        lambda o, n: _antwort("achimdehnert", "2026-08-25T09:00:00Z"),
        lambda login: "User",
        STICHTAG,
    )
    assert len(funde) == 1 and funde[0].check == "C"


def test_should_not_flag_existing_repo_before_stichtag():
    """ADR-297 Ebene 2: Bestand wandert nicht pauschal — sonst 50 Zeilen beim ersten Lauf."""
    reg = _registry({"neu-hub": PROD})
    funde = check_c(
        reg,
        lambda o, n: _antwort("achimdehnert", "2026-08-23T23:59:59Z"),
        lambda login: "User",
        STICHTAG,
    )
    assert funde == []


def test_should_not_flag_new_repo_inside_an_organisation():
    reg = _registry({"neu-hub": PROD})
    funde = check_c(
        reg,
        lambda o, n: _antwort("iilgmbh", "2026-08-25T09:00:00Z"),
        lambda login: "Organization",
        STICHTAG,
    )
    assert funde == []


def test_should_not_flag_new_sandbox_repo():
    """Klasse 5 hat keine Betriebsverantwortung — der Leitsatz erlaubt sie ausdruecklich."""
    reg = _registry({"spiel-hub": {"rich": {"github": "achimdehnert/spiel-hub"}}})
    funde = check_c(
        reg,
        lambda o, n: _antwort("achimdehnert", "2026-08-25T09:00:00Z"),
        lambda login: "User",
        STICHTAG,
    )
    assert funde == []


# --- CLI ----------------------------------------------------------------------


def test_should_exit_1_on_finding_and_0_when_clean(tmp_path, capsys):
    def schreibe(rich_owner: str) -> Path:
        pfad = tmp_path / f"{rich_owner}.yaml"
        pfad.write_text(
            yaml.safe_dump(
                {
                    "meta": {
                        "server": {"github_org": "achimdehnert"},
                        "repo_owner": {"risk-hub": "iilgmbh"},
                    },
                    "repos": {
                        "risk-hub": {"rich": {"github": f"{rich_owner}/risk-hub"}}
                    },
                }
            ),
            encoding="utf-8",
        )
        return pfad

    assert main(["--registry", str(schreibe("achimdehnert")), "--offline"]) == 1
    assert "[A] risk-hub" in capsys.readouterr().out
    assert main(["--registry", str(schreibe("iilgmbh")), "--offline"]) == 0
    assert "Kein Fund" in capsys.readouterr().out


def test_should_exit_2_when_registry_is_unreadable(tmp_path, capsys):
    assert main(["--registry", str(tmp_path / "gibt-es-nicht.yaml"), "--offline"]) == 2


def test_should_find_repo_under_another_owner_when_declaration_points_nowhere():
    """Realfall bahn-hub: die Praefix-Regel zeigt ins Leere (404).

    Ohne Gegenprobe landet ausgerechnet die schwerste Drift — die Deklaration ist
    selbst falsch — als harmloses "nicht pruefbar" im Bericht.
    """
    reg = _registry({"bahn-hub": {}})
    reg.prefix_rules = [{"prefix": "bahn-", "owner": "bahn-sqf"}]
    reg.bekannte_konten = ["achimdehnert", "iilgmbh", "bahn-sqf"]

    def fetch(owner, name):
        return _antwort("achimdehnert") if owner == "achimdehnert" else None

    funde, unerreichbar = check_b(reg, fetch)
    assert unerreichbar == []
    assert len(funde) == 1
    assert (funde[0].erwartet, funde[0].gefunden) == ("bahn-sqf", "achimdehnert")


def test_should_still_report_unreachable_when_no_account_has_it():
    reg = _registry({"geheim-hub": {}})
    reg.bekannte_konten = ["achimdehnert", "iilgmbh"]
    funde, unerreichbar = check_b(reg, lambda o, n: None)
    assert funde == [] and unerreichbar == ["geheim-hub"]


def test_should_load_known_accounts_from_registry(tmp_path):
    """Regression: `bekannte_konten` blieb leer, weil der Loader das Feld nicht setzte.

    Der Fallback aus `check_b` lief damit ueber eine leere Liste und war wirkungslos —
    sichtbar nur daran, dass bahn-hub weiterhin als "nicht pruefbar" gemeldet wurde.
    Ein Feld, das die Tests nur ueber ihren eigenen Konstruktor befuellen, beweist
    nichts ueber den Ladepfad.
    """
    pfad = tmp_path / "canonical.yaml"
    pfad.write_text(
        yaml.safe_dump(
            {
                "meta": {
                    "server": {"github_org": "achimdehnert"},
                    "enterprise_owners": ["achimdehnert", "iilgmbh", "bahn-sqf"],
                },
                "repos": {"bahn-hub": {}},
            }
        ),
        encoding="utf-8",
    )
    reg = Registry.laden(pfad)
    assert reg.bekannte_konten == ["achimdehnert", "iilgmbh", "bahn-sqf"]
