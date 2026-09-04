"""Drill fuer das Inventar-Schema und tools/secrets_inventory_check.py (#2813).

Der wichtigste Test ist ``test_should_count_string_consumers_as_incomplete``:
die alte Form bleibt GUELTIG (sonst waere die Migration ein Big-Bang), darf aber
nicht als vollqualifiziert durchgehen. Genau an dieser Stelle wuerde die
Inventar-Deckung des Kill-Gates sonst still zu hoch gemeldet.

Alle Attrappen-Werte heissen ``ATTRAPPE-...`` — nichts in dieser Datei sieht
aus wie ein Token, damit gitleaks nicht auf den Drill anschlaegt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import secrets_inventory_check as check  # noqa: E402
from rotation import inventar  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
ECHTES_INVENTAR = WURZEL / "infra" / "secrets-inventory.yaml"
SCHEMA = WURZEL / "infra" / "schemas" / "secrets-inventory.schema.json"


def _schreibe(tmp_path: Path, daten: dict) -> Path:
    pfad = tmp_path / "inv.yaml"
    pfad.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    return pfad


ALT = {
    "shared": {
        "ALTFORM": {
            "description": "Attrappe alte Form",
            "consumers": ["platform", "risk-hub"],
        }
    }
}

NEU = {
    "shared": {
        "NEUFORM": {
            "description": "Attrappe neue Form",
            "rotation": "yearly",
            "consumers": [
                {
                    "kind": "github_repo_secret",
                    "ref": "iilgmbh/risk-hub",
                    "name": "NEUFORM",
                    "proof": {"workflow": "secret-probe.yml", "log_marker": "✓ NEUFORM gueltig"},
                }
            ],
        }
    }
}


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------
def test_should_accept_the_old_string_form():
    assert check.schema_verstoesse(ALT, SCHEMA) == []


def test_should_accept_the_new_object_form():
    assert check.schema_verstoesse(NEU, SCHEMA) == []


def test_should_reject_a_github_ref_without_org():
    kaputt = {
        "shared": {
            "X": {
                "description": "d",
                "consumers": [{"kind": "github_repo_secret", "ref": "risk-hub", "name": "X"}],
            }
        }
    }
    assert check.schema_verstoesse(kaputt, SCHEMA)


def test_should_reject_a_host_ref_without_path():
    kaputt = {
        "shared": {
            "X": {
                "description": "d",
                "consumers": [{"kind": "host_env_file", "ref": "prod", "name": "X"}],
            }
        }
    }
    assert check.schema_verstoesse(kaputt, SCHEMA)


def test_should_reject_an_unknown_consumer_kind():
    kaputt = {
        "shared": {
            "X": {
                "description": "d",
                "consumers": [{"kind": "smoke_signal", "ref": "a/b", "name": "X"}],
            }
        }
    }
    assert check.schema_verstoesse(kaputt, SCHEMA)


def test_should_reject_a_proof_that_is_only_half_a_proof():
    """`workflow` ohne `log_marker` ist ein Beleg ohne Aussage — genau die Form,
    die man aus Bequemlichkeit einträgt."""
    kaputt = {
        "shared": {
            "X": {
                "description": "d",
                "consumers": [
                    {
                        "kind": "github_repo_secret",
                        "ref": "a/b",
                        "name": "X",
                        "proof": {"workflow": "probe.yml"},
                    }
                ],
            }
        }
    }
    assert check.schema_verstoesse(kaputt, SCHEMA)


def test_should_pass_the_real_inventory():
    """Das echte Inventar ist der eigentliche Drill — ein Schema, das nur gegen
    Attrappen gruen ist, sagt ueber die SSoT nichts aus."""
    assert check.schema_verstoesse(check.lade(ECHTES_INVENTAR), SCHEMA) == []


# --------------------------------------------------------------------------
# Zaehlungen
# --------------------------------------------------------------------------
def test_should_count_string_consumers_as_incomplete():
    z = check.zaehle(ALT)
    assert z["mit_konsumenten"] == 1
    assert z["vollqualifiziert"] == 0
    assert z["unvollstaendig"] == 1
    assert z["mit_proof"] == 0


def test_should_count_object_consumers_with_proof():
    z = check.zaehle(NEU)
    assert (z["vollqualifiziert"], z["mit_proof"], z["konsumenten_ohne_proof"]) == (1, 1, 0)


def test_should_not_count_the_shaped_sections_as_entries():
    """`local`/`server_side`/`sops` haben eine andere Gestalt. Wuerden sie
    mitgezaehlt, sähe die Inventar-Deckung besser aus, als sie ist."""
    z = check.zaehle({**NEU, "local": {"files": {"a": {"env": "A"}}}, "sops": {"status": "planned"}})
    assert z["eintraege"] == 1


def test_should_exit_nonzero_on_schema_violation(tmp_path):
    pfad = _schreibe(tmp_path, {"shared": {"X": {"description": "d", "rotation": "taeglich"}}})
    assert check.main(["--inventar", str(pfad), "--schema", str(SCHEMA), "--kurz"]) == 1


def test_should_exit_zero_on_the_real_inventory():
    assert check.main(["--kurz"]) == 0


# --------------------------------------------------------------------------
# Inventar-Lesemodul
# --------------------------------------------------------------------------
def test_should_mark_string_consumers_as_not_rotatable():
    secret = inventar.finde(ALT, "ALTFORM")
    assert len(secret.konsumenten) == 2
    assert all(k.unvollstaendig and not k.rotierbar for k in secret.konsumenten)
    assert len(secret.ohne_beleg) == 2


def test_should_mark_a_consumer_without_proof_as_not_rotatable():
    daten = {
        "shared": {
            "X": {
                "description": "d",
                "consumers": [{"kind": "github_repo_secret", "ref": "a/b", "name": "X"}],
            }
        }
    }
    assert not inventar.finde(daten, "X").konsumenten[0].rotierbar


def test_should_refuse_an_ambiguous_secret_name():
    daten = {
        "shared": {"X": {"description": "a"}},
        "platform": {"X": {"description": "b"}},
    }
    with pytest.raises(KeyError, match="mehrdeutig"):
        inventar.finde(daten, "X")


def test_should_resolve_orgs_from_the_canonical_registry():
    org = inventar.org_aufloesung()
    assert org("risk-hub") == "iilgmbh"
    assert org("platform") == "achimdehnert"
    assert org("frist-hub") == "meiki-lra"


def test_should_read_the_real_genesor_entry_with_one_proof():
    """REC-6-Kandidat: drei Konsumenten, genau EINER hat einen Beleg. Wird das
    stiller (z. B. proof aus Versehen entfernt), faellt dieser Drill."""
    secret = inventar.finde(inventar.lade(ECHTES_INVENTAR), "GENESOR_PROJECT_TOKEN")
    assert len(secret.konsumenten) == 3
    assert sum(1 for k in secret.konsumenten if k.rotierbar) == 1
    assert len(secret.ohne_beleg) == 2
