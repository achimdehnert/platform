"""Drill fuer die Kette ``rotate.py lauf`` und den Melder ``faellig`` (#2813).

Die Kette wird komplett mit Attrappen gefahren — kein Netz, kein Token, kein
echter Wert. Vier Ausgaenge sind die eigentliche Abnahme:

* Beleg gruen  -> Log-Zeile ``abgeschlossen`` **und** Schleuse geleert
* Beleg rot    -> Lauf ``offen``, Schleuse bleibt gefuellt (kein Rollback)
* ohne proof   -> nicht gesetzt, gezaehlt, im Log als ``ohne_beleg``
* Gov-Org      -> abgelehnt, im Log als ``abgelehnt``, Lauf endet als ``offen``

Der dritte und der vierte Fall sind die, die man in einem Werkzeug ohne Drill
"aus Gruenden" still ueberspringt — genau davor warnt AD-3.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rotation import cli  # noqa: E402
from rotation import treiber_github as tg  # noqa: E402
from rotation.treiber_github import Belegergebnis, GovOrgAbgelehnt  # noqa: E402

SCHLUESSEL = "ATTRAPPE-hmac-schluessel-fuer-den-drill\n"

INVENTAR = {
    "shared": {
        "ATTRAPPE_TOKEN": {
            "description": "Attrappe fuer den Drill",
            "rotation": "yearly",
            "consumers": [
                {
                    "kind": "github_repo_secret",
                    "ref": "iilgmbh/risk-hub",
                    "name": "ATTRAPPE_TOKEN",
                    "proof": {
                        "workflow": "secret-probe.yml",
                        "log_marker": "✓ ATTRAPPE_TOKEN gueltig",
                    },
                },
                {
                    "kind": "github_repo_secret",
                    "ref": "achimdehnert/apo-hub",
                    "name": "ATTRAPPE_TOKEN",
                },
                {
                    "kind": "github_repo_secret",
                    "ref": "meiki-lra/meiki-hub",
                    "name": "ATTRAPPE_TOKEN",
                    "proof": {"workflow": "secret-probe.yml", "log_marker": "✓ x"},
                },
            ],
        }
    }
}


class AttrappenTreiber:
    """Zaehlt, was gesetzt wurde, und liefert ein vorgegebenes Beleg-Ergebnis."""

    kind = "github_repo_secret"

    def __init__(self, ergebnis="ok", negativprobe=True):
        self.gesetzt: list[tuple[str, str]] = []
        self.belegt: list[str] = []
        self.ergebnis = ergebnis
        self.negativprobe = negativprobe

    def setze(self, ref, name, wert):
        if ref.split("/", 1)[0] in tg.GOV_ORGS:
            raise GovOrgAbgelehnt(f"'{ref}' liegt in einer Souveraenitaets-Org")
        assert isinstance(wert, bytes)
        self.gesetzt.append((ref, name))

    def belege(self, ref, proof, secret_name=""):
        self.belegt.append(ref)
        return Belegergebnis(
            self.ergebnis, self.negativprobe, "https://example.invalid/lauf"
        )


@pytest.fixture
def umgebung(tmp_path):
    inv = tmp_path / "inv.yaml"
    inv.write_text(yaml.safe_dump(INVENTAR, allow_unicode=True), encoding="utf-8")
    log = tmp_path / "rotation-log.jsonl"
    hmac = tmp_path / "hmac"
    hmac.write_text(SCHLUESSEL, encoding="utf-8")
    quelle = tmp_path / "shared" / "attrappe-token.txt"
    quelle.parent.mkdir()
    quelle.write_text("ATTRAPPE-1234\n", encoding="utf-8")
    return (
        argparse.Namespace(
            inventar=inv,
            log=log,
            hmac_schluessel=hmac,
            quelle=str(quelle),
            secret="ATTRAPPE_TOKEN",
            nur=None,
            ausgefuehrt_von="drill",
        ),
        quelle,
        log,
    )


def _zeilen(log: Path) -> list[dict]:
    return [
        json.loads(z) for z in log.read_text(encoding="utf-8").splitlines() if z.strip()
    ]


# --------------------------------------------------------------------------
def test_should_close_the_run_and_empty_the_sluice_when_every_proof_is_green(umgebung):
    a, quelle, log = umgebung
    a.nur = "iilgmbh/risk-hub"
    treiber = AttrappenTreiber("ok")
    assert cli.cmd_lauf(a, treiber) == 0

    zeile = _zeilen(log)[-1]
    assert zeile["status"] == "abgeschlossen"
    assert zeile["schleuse_geleert"] is True
    assert not quelle.exists(), "Schleuse wird nach dem letzten Beleg geleert"
    assert zeile["konsumenten"][0]["ergebnis"] == "ok"
    assert zeile["fingerprint_alg"] == "hmac-sha256/v1"
    assert len(zeile["fingerprint_prefix16"]) == 16
    assert "ATTRAPPE-1234" not in log.read_text(encoding="utf-8")


def test_should_keep_the_run_open_and_the_sluice_full_when_the_proof_is_red(umgebung):
    a, quelle, log = umgebung
    a.nur = "iilgmbh/risk-hub"
    assert cli.cmd_lauf(a, AttrappenTreiber("rot")) == 1

    zeile = _zeilen(log)[-1]
    assert zeile["status"] == "offen"
    assert zeile["schleuse_geleert"] is False
    assert quelle.exists(), "kein Rollback — der Wert bleibt greifbar"


def test_should_count_a_consumer_without_proof_instead_of_skipping_it(umgebung):
    a, _quelle, log = umgebung
    a.nur = "achimdehnert/apo-hub"
    treiber = AttrappenTreiber("ok")
    assert cli.cmd_lauf(a, treiber) == 1

    zeile = _zeilen(log)[-1]
    assert treiber.gesetzt == [], "ohne Beleg wird NICHT gesetzt"
    assert zeile["konsumenten"][0]["ergebnis"] == "ohne_beleg"
    assert zeile["konsumenten"][0]["hinweis"] == "ohne proof"
    assert zeile["status"] == "offen"


def test_should_refuse_a_sovereign_org(umgebung):
    a, _quelle, log = umgebung
    a.nur = "meiki-lra/meiki-hub"
    treiber = AttrappenTreiber("ok")
    assert cli.cmd_lauf(a, treiber) == 1

    zeile = _zeilen(log)[-1]
    assert zeile["konsumenten"][0]["ergebnis"] == "abgelehnt"
    assert treiber.gesetzt == []


def test_should_record_whether_a_negative_control_existed(umgebung):
    """Ein gruener Beleg ohne roten Vorlauf ist schwaecher — und wird nicht
    verschwiegen, sondern als negativprobe=false protokolliert (AD-4)."""
    a, _quelle, log = umgebung
    a.nur = "iilgmbh/risk-hub"
    cli.cmd_lauf(a, AttrappenTreiber("ok", negativprobe=False))
    assert _zeilen(log)[-1]["konsumenten"][0]["negativprobe"] is False


def test_should_abort_without_the_hmac_key(umgebung, tmp_path):
    a, quelle, log = umgebung
    a.hmac_schluessel = tmp_path / "fehlt"
    assert cli.cmd_lauf(a, AttrappenTreiber("ok")) == 3
    assert quelle.exists() and not log.exists(), "kein Lauf, keine Zeile, keine Leerung"


def test_should_reject_an_unknown_target(umgebung):
    a, _quelle, _log = umgebung
    a.nur = "achimdehnert/gibt-es-nicht"
    assert cli.cmd_lauf(a, AttrappenTreiber("ok")) == 2


def test_should_run_all_three_consumers_without_nur(umgebung):
    a, quelle, log = umgebung
    treiber = AttrappenTreiber("ok")
    cli.cmd_lauf(a, treiber)
    zeile = _zeilen(log)[-1]
    assert [k["ergebnis"] for k in zeile["konsumenten"]] == [
        "ok",
        "ohne_beleg",
        "abgelehnt",
    ]
    assert zeile["status"] == "offen"
    assert quelle.exists()


def test_should_use_the_given_operator_name(umgebung):
    a, _quelle, log = umgebung
    a.nur = "iilgmbh/risk-hub"
    a.ausgefuehrt_von = "owner"
    cli.cmd_lauf(a, AttrappenTreiber("ok"))
    assert _zeilen(log)[-1]["ausgefuehrt_von"] == "owner"


# --------------------------------------------------------------------------
# faellig
# --------------------------------------------------------------------------
def test_should_count_due_without_beleg_and_stale_files(tmp_path):
    inv = tmp_path / "inv.yaml"
    inv.write_text(yaml.safe_dump(INVENTAR, allow_unicode=True), encoding="utf-8")
    schleuse = tmp_path / "shared"
    schleuse.mkdir()
    alt = schleuse / "irgendein-token.txt"
    alt.write_text("ATTRAPPE", encoding="utf-8")
    import os
    import time

    os.utime(alt, (time.time() - 30 * 86400, time.time() - 30 * 86400))
    (schleuse / "notizen.md").write_text("kein Schluesselmaterial", encoding="utf-8")

    b = cli.sammle_faelligkeit(inv, tmp_path / "leer.jsonl", schleuse, date(2026, 9, 4))
    assert b["secrets"] == 1
    assert b["faellig"] == ["ATTRAPPE_TOKEN"]
    # 1 von 3 ohne proof: der Gov-Org-Konsument HAT einen Beleg — abgelehnt wird
    # er erst im Treiber. Das Inventar zaehlt Belege, nicht Berechtigungen.
    assert b["ohne_beleg"] == ["ATTRAPPE_TOKEN (1/3)"]
    assert b["ohne_konsumenten"] == []
    assert len(b["altlasten"]) == 1 and "irgendein-token.txt" in b["altlasten"][0]
    assert "notizen" not in " ".join(b["altlasten"]), "nur Schluesselmaterial-Namen"


def test_should_say_ok_when_there_is_nothing_to_report(tmp_path):
    inv = tmp_path / "inv.yaml"
    inv.write_text(
        yaml.safe_dump(
            {
                "shared": {
                    "A": {
                        "description": "d",
                        "rotation": "on_demand",
                        "consumers": [
                            {
                                "kind": "github_repo_secret",
                                "ref": "a/b",
                                "name": "A",
                                "proof": {"workflow": "w.yml", "log_marker": "m"},
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    leer = tmp_path / "leer"
    leer.mkdir()
    b = cli.sammle_faelligkeit(inv, tmp_path / "leer.jsonl", leer, date(2026, 9, 4))
    assert cli.kurzzeile(b).startswith("OK:"), "der Melder redet auch, wenn nichts ist"


def test_should_shout_when_a_value_reached_the_log(tmp_path):
    inv = tmp_path / "inv.yaml"
    inv.write_text(yaml.safe_dump({"shared": {}}), encoding="utf-8")
    log = tmp_path / "rotation-log.jsonl"
    log.write_text('{"x": "%s"}\n' % ("ol" + "_api_" + "ATTRAPPE"), encoding="utf-8")
    leer = tmp_path / "leer"
    leer.mkdir()
    b = cli.sammle_faelligkeit(inv, log, leer, date(2026, 9, 4))
    assert cli.kurzzeile(b).startswith("WERT IM LOG")


def test_should_report_the_real_repository_state():
    """Der Melder muss auf dem ECHTEN Inventar laufen — ein Melder, der nur
    gegen Attrappen gruen ist, faellt beim ersten Session-Start um."""
    b = cli.sammle_faelligkeit()
    assert b["secrets"] > 40
    assert b["log_befunde"] == []
    assert cli.kurzzeile(b)
