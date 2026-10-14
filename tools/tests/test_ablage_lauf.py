"""Tests für den Ablage-Lauf (platform#3970, tools/mail_agent/ablage_lauf.py).

Gegenstand ist der Schutz: eine Regel sagt, wohin eine Mail gehört, aber nicht,
ob sie erledigt ist. Unbeantwortetes bleibt im Posteingang.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "ablage_lauf.py"
_spec = importlib.util.spec_from_file_location("ablage_lauf", _SRC)
ablage_lauf = importlib.util.module_from_spec(_spec)
sys.modules["ablage_lauf"] = ablage_lauf
_spec.loader.exec_module(ablage_lauf)
regeln = ablage_lauf.regeln


def _regel(**kw):
    basis = {
        "regel_id": "r1",
        "quelle": "ansage",
        "aktion": "verschieben",
        "ziel": "Verwaltung",
        "kriterium": {"absender_domain": "hochschule.example"},
        "zustand": "aktiv",
    }
    basis.update(kw)
    return regeln.Regel(**basis)


def _mail(i, absender="a@hochschule.example", **kw):
    basis = {
        "id": str(i),
        "absender": absender,
        "betreff": f"Betreff {i}",
        "datum": "Wed, 14 Oct 2026 08:00:00 +0200",
        "ordner": "INBOX",
        "message_id": f"<m{i}@example>",
        "beantwortet": False,
    }
    basis.update(kw)
    return basis


def _ids(liste):
    return [b["id"] for b in liste]


def test_should_keep_unanswered_mail_with_matching_rule_in_inbox():
    """#3970: Regel trifft, aber keine Antwort → bleibt, wird als geschützt gezählt."""
    e = ablage_lauf.lauf_planen([_regel()], [_mail(1)], set())
    assert e["bewegungen"] == []
    assert _ids(e["geschuetzt"]) == ["1"]
    assert e["geschuetzt"][0]["grund"] == "unbeantwortet"


def test_should_move_mail_flagged_as_answered():
    e = ablage_lauf.lauf_planen([_regel()], [_mail(1, beantwortet=True)], set())
    assert _ids(e["bewegungen"]) == ["1"]
    assert e["bewegungen"][0]["zielordner"] == "Verwaltung"


def test_should_move_mail_answered_from_sent_folder():
    """Antwort im Gesendet-Ordner zählt auch ohne \\Answered (anderer Client)."""
    e = ablage_lauf.lauf_planen([_regel()], [_mail(1)], {"<m1@example>"})
    assert _ids(e["bewegungen"]) == ["1"]
    assert e["bewegungen"][0]["message_id"] == "<m1@example>"


def test_should_move_machine_sent_mail_without_answer():
    e = ablage_lauf.lauf_planen(
        [_regel()], [_mail(1, list_unsubscribe="<https://x.example/u>")], set()
    )
    assert _ids(e["bewegungen"]) == ["1"]


def test_should_treat_auto_submitted_no_as_personal_mail():
    """RFC 3834: `Auto-Submitted: no` heißt ausdrücklich „von Hand"."""
    e = ablage_lauf.lauf_planen([_regel()], [_mail(1, auto_submitted="no")], set())
    assert _ids(e["geschuetzt"]) == ["1"]


def test_should_ignore_rules_that_are_not_active():
    vorschlag = _regel(zustand="vorschlag")
    e = ablage_lauf.lauf_planen([vorschlag], [_mail(1, beantwortet=True)], set())
    assert e["bewegungen"] == []
    assert e["restmenge"] == 1


def test_should_never_trash_even_with_active_delete_rule():
    loeschen = _regel(aktion="loeschen", ziel="")
    e = ablage_lauf.lauf_planen([loeschen], [_mail(1, beantwortet=True)], set())
    assert e["bewegungen"] == []
    assert _ids(e["ausgelassen"]) == ["1"]


def test_should_report_restmenge_of_unmatched_mails():
    bestand = [_mail(1, beantwortet=True), _mail(2, absender="b@anders.example")]
    e = ablage_lauf.lauf_planen([_regel()], bestand, set())
    assert e["bestand"] == 2
    assert e["restmenge"] == 1


def test_should_keep_message_id_for_rollback(tmp_path):
    """Die UID ist nach dem Umzug wertlos — die Rücknahme braucht die Message-ID."""
    e = ablage_lauf.lauf_planen([_regel()], [_mail(1, beantwortet=True)], set())
    pfad = tmp_path / "protokoll.jsonl"
    regeln.protokollieren(e["bewegungen"], pfad, "lauf-1")
    zurueck = regeln.ruecknahme(pfad, "lauf-1")
    assert zurueck[0]["message_id"] == "<m1@example>"
    assert (zurueck[0]["quellordner"], zurueck[0]["zielordner"]) == ("Verwaltung", "INBOX")
    assert json.loads(pfad.read_text().splitlines()[0])["lauf_id"] == "lauf-1"


class _FakeImap:
    """Ordner → {Message-ID: UID}; zeichnet MOVE-Aufrufe auf."""

    def __init__(self, ordner):
        self.ordner = ordner
        self.aktuell = None
        self.moves = []

    def select(self, name, readonly=False):
        self.aktuell = name.strip('"')
        return "OK", [b"1"]

    def capability(self):
        return "OK", [b"IMAP4rev1 MOVE UIDPLUS"]

    def uid(self, cmd, *args):
        if cmd == "SEARCH":
            uid = self.ordner.get(self.aktuell, {}).get(args[-1])
            return "OK", [uid.encode() if uid else b""]
        if cmd == "MOVE":
            self.moves.append((self.aktuell, args[0], args[1].strip('"')))
            return "OK", [b""]
        raise AssertionError(cmd)


def test_should_rollback_by_resolving_message_id_at_target():
    imap = _FakeImap({"Verwaltung": {"<m1@example>": "77"}})
    eintraege = [
        {"quellordner": "Verwaltung", "zielordner": "INBOX", "message_id": "<m1@example>"},
        {"quellordner": "Verwaltung", "zielordner": "INBOX", "message_id": "<weg@example>"},
    ]
    zurueck, fehlt = ablage_lauf.zuruecknehmen(imap, eintraege, apply=True)
    assert (zurueck, fehlt) == (1, 1)
    assert imap.moves == [("Verwaltung", b"77", "INBOX")]


def test_should_not_move_anything_in_rollback_dry_run():
    imap = _FakeImap({"Verwaltung": {"<m1@example>": "77"}})
    eintraege = [{"quellordner": "Verwaltung", "zielordner": "INBOX", "message_id": "<m1@example>"}]
    assert ablage_lauf.zuruecknehmen(imap, eintraege, apply=False) == (1, 0)
    assert imap.moves == []
