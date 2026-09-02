"""Tests für den Sendeabgleich — Zuordnungslogik ohne Postfach.

Die Postfach-Zugriffe (`_imap_gesendet`, `_graph_gesendet`) sind hier bewusst
nicht gemockt, sondern gar nicht beteiligt: geprüft wird die Entscheidung, die
das Werkzeug aus vorhandenen Mails trifft. Genau dort sitzt das Risiko einer
Fehlzuordnung.
"""

import importlib.util
import json
import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "sendeabgleich.py"
_spec = importlib.util.spec_from_file_location("sendeabgleich", _SRC)
sa = importlib.util.module_from_spec(_spec)
# Vor exec_module registrieren: `dataclasses` schlaegt beim Verarbeiten von
# `Gesendet` das Modul in sys.modules nach; fehlt es dort, bricht schon die
# Sammelphase mit "'NoneType' object has no attribute '__dict__'".
sys.modules["sendeabgleich"] = sa
_spec.loader.exec_module(sa)


def _vorgang(**kv):
    basis = {
        "nr": 1,
        "konto": "iil",
        "bucket": "owner",
        "kurz": "Entwurf senden",
        "next_trigger": "Owner sendet Entwurf",
        "zustand": "entwurf-liegt",
        "thread_key": "NIS2 (Beispiel Recycling)",
        "gegenueber": "Beispiel Recycling / Sabine Muster",
        "letzte_pruefung": "2026-08-19",
        "notiz": "",
    }
    basis.update(kv)
    return basis


def _mail(betreff, datum="2026-08-20", empfaenger=""):
    return sa.Gesendet(datum, betreff, empfaenger)


class TestWartetAufVersand:
    def test_should_detect_vorgang_waiting_for_send(self):
        assert sa.wartet_auf_versand(_vorgang()) is True

    def test_should_ignore_vorgang_in_other_bucket(self):
        assert sa.wartet_auf_versand(_vorgang(bucket="warten")) is False

    def test_should_ignore_vorgang_without_send_wording(self):
        v = _vorgang(
            kurz="Rechnung buchen", next_trigger="im sevdesk buchen", zustand="offen"
        )
        assert sa.wartet_auf_versand(v) is False


class TestZuordnung:
    def test_should_match_on_subject_token(self):
        assert sa.passt_zusammen(
            _vorgang(), _mail("AW: Container-Service NIS2 Einstufung")
        )

    def test_should_match_on_recipient_domain(self):
        mail = _mail("Unterlagen", empfaenger="s.muster@beispiel-recycling.example")
        assert sa.passt_zusammen(_vorgang(), mail)

    def test_should_not_match_unrelated_mail(self):
        assert not sa.passt_zusammen(_vorgang(), _mail("Rechnung August, Hosting"))

    def test_should_not_match_on_stopwords_alone(self):
        """'AW'/'GmbH' stehen in jedem zweiten Betreff und dürfen nichts tragen."""
        v = _vorgang(thread_key="AW GmbH", gegenueber="GmbH")
        assert not sa.passt_zusammen(v, _mail("AW: irgendwas, GmbH"))

    def test_should_ignore_mail_sent_before_last_check(self):
        assert not sa.nach_letzter_pruefung(
            _vorgang(), _mail("NIS2", datum="2026-08-18")
        )


class TestVorschlaege:
    def test_should_propose_flip_on_single_match(self):
        ledger = {"vorgaenge": [_vorgang()]}
        b = sa.vorschlaege(ledger, {"iil": [_mail("AW: NIS2 Einstufung")]})
        assert [x["lage"] for x in b] == ["treffer"]

    def test_should_take_the_newest_when_several_mails_match(self):
        """Ein laufender Strang hat mehrere passende Mails — der Wechsel ist derselbe.

        Bis 2026-08-21 brach der Abgleich hier ab. Die Positivkontrolle am echten
        Ledger zeigte, dass genau das den Normalfall traf: zwei Mails desselben
        Vorgangs, Ergebnis 'mehrdeutig' statt einer Umstellung.
        """
        ledger = {"vorgaenge": [_vorgang()]}
        mails = [
            _mail("AW: NIS2 Einstufung", datum="2026-08-20"),
            _mail("WG: NIS2 Nachtrag", datum="2026-08-21"),
        ]
        b = sa.vorschlaege(ledger, {"iil": mails})
        assert b[0]["lage"] == "treffer"
        assert b[0]["mails"][0].datum == "2026-08-21", "juengste Mail ist der Beleg"

    def test_should_report_open_when_nothing_matches(self):
        ledger = {"vorgaenge": [_vorgang()]}
        b = sa.vorschlaege(ledger, {"iil": [_mail("Newsletter")]})
        assert b[0]["lage"] == "offen"

    def test_should_only_consider_the_own_account(self):
        """Eine Mail im HNU-Sendeordner trägt keinen IIL-Vorgang."""
        ledger = {"vorgaenge": [_vorgang(konto="iil")]}
        b = sa.vorschlaege(ledger, {"hnu": [_mail("AW: NIS2 Einstufung")]})
        assert b[0]["lage"] == "offen"


class TestUebernahme:
    def test_should_flip_bucket_and_keep_evidence(self):
        v = _vorgang()
        sa.uebernehmen(v, _mail("AW: NIS2 Einstufung"), "2026-08-20")
        assert v["bucket"] == "warten"
        assert v["letzte_pruefung"] == "2026-08-20"
        assert "Sendeabgleich" in v["notiz"]
        assert "NIS2" in v["notiz"]

    def test_should_not_lose_existing_notes(self):
        v = _vorgang(notiz="alter Stand")
        sa.uebernehmen(v, _mail("AW: NIS2"), "2026-08-20")
        assert v["notiz"].startswith("alter Stand")


def test_should_survive_ledger_roundtrip(tmp_path):
    """Der geschriebene Ledger bleibt gültiges JSON mit echten Umlauten."""
    v = _vorgang(gegenueber="Größe & Söhne (Testdaten)")
    sa.uebernehmen(v, _mail("AW: Angebot für Söhne"), "2026-08-20")
    ziel = tmp_path / "l.json"
    ziel.write_text(
        json.dumps({"vorgaenge": [v]}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    zurueck = json.loads(ziel.read_text(encoding="utf-8"))
    assert zurueck["vorgaenge"][0]["gegenueber"] == "Größe & Söhne (Testdaten)"
