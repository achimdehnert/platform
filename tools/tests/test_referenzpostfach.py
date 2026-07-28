"""Tests für das Referenzpostfach (KONZ-platform-035 REC-10).

Geprüft wird der **Plan**, nicht der Server: dass die Grundgesamtheit aus der
Fall-Tabelle korrekt abgeleitet wird, dass die erzeugten Nachrichten die Formen
tragen, an denen Suchen scheitern, und dass die Ordner-Reihenfolge beim Aufbau
Eltern vor Kindern setzt.

Der Lauf gegen das echte Postfach ist `referenzpostfach.py --recall` — der braucht
Zugangsdaten und läuft deshalb nicht in der CI.
"""

import importlib.util
import pathlib

_SRC = (
    pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "referenzpostfach.py"
)
_spec = importlib.util.spec_from_file_location("referenzpostfach", _SRC)
ref = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ref)


def test_should_derive_ground_truth_from_the_plan_not_from_a_search():
    erw = ref.erwartung()
    assert "Postsortierung" in erw
    # Jeder Fall mit diesem Begriff muss enthalten sein — die Zahl ist die Wahrheit,
    # gegen die KG-RECALL misst.
    soll = {ref.nachricht_id(f) for f in ref.FAELLE if "Postsortierung" in f.begriffe}
    assert erw["Postsortierung"] == soll


def test_should_keep_counter_examples_out_of_every_expectation():
    """Die Gegenprobe-Nachrichten dürfen bei keinem Begriff auftauchen."""
    gegen = ref.gegenprobe()
    assert gegen
    for ids in ref.erwartung().values():
        assert not (ids & gegen)


def test_should_cover_the_folders_where_messages_actually_hide():
    """Gesendet und Papierkorb sind der Kern von R-1 — am 27.07. lagen 8 von 11 dort."""
    ordner = {f.ordner for f in ref.FAELLE}
    assert "Gesendet" in ordner
    assert "Papierkorb" in ordner


def test_should_include_a_sender_without_an_at_sign():
    """Der X.500-Absender ist die Form, an der der Platzhalter-Filter scheiterte."""
    ohne_at = [f for f in ref.FAELLE if "@" not in f.absender]
    assert ohne_at
    assert all(f.begriffe for f in ohne_at), "sonst misst der Fall nichts"


def test_should_include_a_message_without_any_subject():
    assert any(f.betreff is None for f in ref.FAELLE)


def test_should_include_a_term_that_only_appears_in_the_body():
    nur_text = [
        f
        for f in ref.FAELLE
        for b in f.begriffe
        if b in f.text and (f.betreff is None or b not in f.betreff)
    ]
    assert nur_text, "ohne diesen Fall sieht ein Betreff-Filter fehlerfrei aus"


def test_should_create_parents_before_children():
    ordner = ref.alle_ordner(".")
    gesehen = set()
    for name in ordner:
        eltern = name.rsplit(".", 1)[0]
        if eltern != name and eltern.startswith(ref.WURZEL):
            assert eltern in gesehen, f"{eltern} muss vor {name} kommen"
        gesehen.add(name)


def test_should_map_folders_through_the_servers_separator():
    """Der Trenner wird vom Server gelesen, nicht geraten — hier beide Varianten."""
    assert ref.ordnerpfad(".", "Projekte.Ablage") == "INBOX.REF.Projekte.Ablage"
    assert ref.ordnerpfad("/", "Projekte.Ablage") == "INBOX.REF/Projekte/Ablage"
    assert ref.ordnerpfad(".", "") == ref.WURZEL


def test_should_encode_umlauts_in_the_subject_as_a_real_client_would():
    fall = next(f for f in ref.FAELLE if f.betreff and "ö" in f.betreff)
    roh = ref.nachricht_bauen(fall)
    assert b"Subject: =?utf-8?" in roh, "Betreff muss MIME-kodiert sein, nicht Klartext"
    assert "ö".encode() not in roh.split(b"\r\n\r\n")[0]


def test_should_give_every_message_a_stable_identifier():
    ids = [ref.nachricht_id(f) for f in ref.FAELLE]
    assert len(ids) == len(set(ids))
    for fall in ref.FAELLE:
        assert (
            f"Message-ID: <{ref.nachricht_id(fall)}>".encode()
            in ref.nachricht_bauen(fall)
        )


def test_should_write_only_below_its_own_root():
    """Ein Aufbau darf nie an einem echten Postfach vorbeischreiben."""
    for name in ref.alle_ordner("."):
        assert name.startswith(ref.WURZEL)


def test_should_not_delete_folders_that_merely_share_the_name_prefix():
    """Retro-Befund 2026-07-27: der Aufbau loeschte per startswith(WURZEL).

    `INBOX.REFERAT.Wichtig` erfuellt diesen Praefix, ist aber ein fremder Ordner. Bei
    einer loeschenden Operation muss die Grenze der Namensraum-Trenner sein, nicht die
    Zeichenkette.
    """
    assert ref.gehoert_zur_wurzel("INBOX.REF", ".")
    assert ref.gehoert_zur_wurzel("INBOX.REF.Gesendet", ".")
    assert ref.gehoert_zur_wurzel("INBOX.REF.Projekte.Ablage.Alt", ".")

    for fremd in ("INBOX.REFERENZ", "INBOX.REFacct", "INBOX.REFERAT.Wichtig", "INBOX"):
        assert not ref.gehoert_zur_wurzel(fremd, "."), fremd


def test_should_respect_a_different_namespace_separator():
    assert ref.gehoert_zur_wurzel("INBOX.REF/Gesendet", "/")
    assert not ref.gehoert_zur_wurzel("INBOX.REFERENZ/Alt", "/")
