"""Stapelverarbeitung des Jahrgangs-Einsortierers (Graph /$batch).

Anfragebau und Antwortauswertung sind bewusst **reine** Funktionen — der Fehler
vom 2026-07-28 (falsches Schlüsselwort im Schreibpfad) blieb unentdeckt, weil der
Trockenlauf die schreibende Zeile nie ausführt. Was ohne Netz prüfbar ist, wird
hier ohne Netz geprüft.

Der teuerste Fehler dieser Klasse wäre die **Zuordnung über die Position**: Graph
liefert Teilantworten in beliebiger Reihenfolge zurück. Wer positionsweise liest,
schreibt Ergebnisse der falschen Nachricht zu und meldet Erfolge, die es nicht gab.
"""

import importlib.util
import pathlib

_SRC = (
    pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "archiv_einsortieren.py"
)
_spec = importlib.util.spec_from_file_location("archiv_einsortieren_stapel", _SRC)
ae = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ae)

POSTEN = [("m0", "z2016"), ("m1", "z2017"), ("m2", "z2018")]


def _antwort(*paare):
    return {"responses": [{"id": i, "status": s} for i, s in paare]}


# --- Anfragebau -----------------------------------------------------------


def test_should_build_one_subrequest_per_message():
    rumpf = ae.stapel_anfrage(POSTEN)
    assert len(rumpf["requests"]) == 3
    erste = rumpf["requests"][0]
    assert erste["method"] == "POST"
    assert erste["url"] == "/me/messages/m0/move"
    assert erste["body"] == {"destinationId": "z2016"}


def test_should_give_every_subrequest_a_distinct_id():
    ids = [r["id"] for r in ae.stapel_anfrage(POSTEN)["requests"]]
    assert len(set(ids)) == len(ids)


def test_should_respect_the_graph_batch_limit():
    assert ae.BATCH_GROESSE <= 20


# --- Antwortauswertung ----------------------------------------------------


def test_should_count_successes():
    ok, erneut, fehler = ae.stapel_auswerten(
        _antwort(("0", 200), ("1", 201), ("2", 204)), POSTEN
    )
    assert (ok, erneut, fehler) == (3, [], [])


def test_should_map_responses_by_id_not_by_position():
    """Vertauschte Reihenfolge darf das Ergebnis nicht verschieben."""
    ok, erneut, fehler = ae.stapel_auswerten(
        _antwort(("2", 200), ("0", 429), ("1", 200)), POSTEN
    )
    assert ok == 2
    assert erneut == [("m0", "z2016")]  # die 429 gehoert zu m0, nicht zu m2
    assert fehler == []


def test_should_retry_throttling_and_not_treat_it_as_failure():
    for status in (429, 503, 504):
        ok, erneut, fehler = ae.stapel_auswerten(_antwort(("0", status)), POSTEN[:1])
        assert (ok, erneut, fehler) == (0, [("m0", "z2016")], []), status


def test_should_report_permanent_errors():
    ok, erneut, fehler = ae.stapel_auswerten(_antwort(("0", 403)), POSTEN[:1])
    assert ok == 0
    assert erneut == []
    assert fehler and "403" in fehler[0]


def test_should_retry_missing_subresponses_instead_of_assuming_success():
    """Eine Teilantwort, die gar nicht kam, ist offen — nicht stillschweigend ok.

    Ohne diese Regel meldete ein unvollstaendiger Stapel Erfolg fuer Nachrichten,
    ueber die der Server nichts gesagt hat.
    """
    ok, erneut, fehler = ae.stapel_auswerten(_antwort(("0", 200)), POSTEN)
    assert ok == 1
    assert erneut == [("m1", "z2017"), ("m2", "z2018")]


def test_should_flag_unknown_subresponse_ids():
    ok, erneut, fehler = ae.stapel_auswerten(_antwort(("99", 200)), POSTEN[:1])
    assert ok == 0
    assert any("unbekannte Teilantwort" in f for f in fehler)


def test_should_lose_no_message_between_the_three_buckets():
    ok, erneut, fehler = ae.stapel_auswerten(
        _antwort(("0", 200), ("1", 429), ("2", 403)), POSTEN
    )
    assert ok + len(erneut) + len(fehler) == len(POSTEN)
