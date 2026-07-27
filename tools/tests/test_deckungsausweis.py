"""Tests für den Deckungsausweis (KONZ-platform-035 §5.2/§5.3).

Die Prüffälle sind keine erfundenen Randfälle — jeder bildet einen der drei belegten
Fehlschläge vom 2026-07-27 nach:

* der Absender-Platzhalter, der 21 von 34 Nachrichten still verwarf → ein Retrievalpfad
  ohne Treffer muss sichtbar werden, statt als "leere Menge" durchzugehen,
* der Sachverhalt aus dem Posteingang allein (3 von 11) → unvollständiger Ordner-Scope
  muss die Vollständigkeitsaussage sperren,
* die Liste ohne Nenner → der Ausweis trägt Zähler UND Nenner.
"""

import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "deckungsausweis.py"
_spec = importlib.util.spec_from_file_location("deckungsausweis", _SRC)
da = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(da)


def _vollstaendig(**abweichungen):
    """Ein Ausweis, der alle Bedingungen erfüllt — Basis für gezielte Verschlechterung."""
    felder = {
        "frage": "Postsortierung",
        "anlass": "Sachstand für Rückmeldung",
        "konten_vorhanden": 3,
        "konten_durchsucht": 3,
        "ordner_vorhanden": 110,
        "ordner_durchsucht": 110,
        "scan_started_at": "2026-07-27T14:00:00Z",
        "scan_finished_at": "2026-07-27T14:01:17Z",
        "source_watermark": "2026-07-27T14:01:17Z",
        "retrievalpfade": (("client-filter", 7), ("imap-search", 9)),
        "kalibriert": ("client-filter", "imap-search"),
        "geprueft": 46065,
        "vorhanden": 46065,
        "query_fingerprint": "abc123",
        "tool_version": "vorgang.py@1",
    }
    felder.update(abweichungen)
    return da.Ausweis(**felder)


def test_should_allow_completeness_claim_when_every_condition_holds():
    zulaessig, gruende = da.vollstaendigkeitsaussage_zulaessig(_vollstaendig())
    assert zulaessig
    assert gruende == []


def test_should_block_completeness_claim_when_folders_were_skipped():
    """Der Zeiner-Fall: 3 von 11 Nachrichten, weil nur der Posteingang gelesen wurde."""
    a = _vollstaendig(ordner_durchsucht=1)
    zulaessig, gruende = da.vollstaendigkeitsaussage_zulaessig(a)
    assert not zulaessig
    assert any("Ordner 1/110" in g for g in gruende)


def test_should_block_completeness_claim_when_an_account_was_skipped():
    a = _vollstaendig(konten_durchsucht=2)
    zulaessig, gruende = da.vollstaendigkeitsaussage_zulaessig(a)
    assert not zulaessig
    assert any("Konten 2/3" in g for g in gruende)


def test_should_report_a_retrieval_path_without_hits_as_a_finding():
    """Der Platzhalter-Fall: ein Pfad findet nichts, während der andere trifft."""
    a = _vollstaendig(retrievalpfade=(("client-filter", 0), ("imap-search", 9)))
    assert da.leere_pfade(a) == ["client-filter"]
    assert "client-filter" in da.rendern(a)
    assert "kaputte Abfrage" in da.rendern(a)


def test_should_block_completeness_claim_for_an_uncalibrated_path():
    """R-3: eine bekannte Nachricht belegt EINEN Pfad, nicht das Verfahren."""
    a = _vollstaendig(kalibriert=("client-filter",))
    zulaessig, gruende = da.vollstaendigkeitsaussage_zulaessig(a)
    assert not zulaessig
    assert da.unkalibrierte_pfade(a) == ["imap-search"]
    assert any("imap-search" in g and "R-3" in g for g in gruende)


def test_should_block_completeness_claim_when_produced_by_hand():
    a = _vollstaendig(erzeuger="manuell", fallback_grund="Graph-Zugang gestört")
    zulaessig, gruende = da.vollstaendigkeitsaussage_zulaessig(a)
    assert not zulaessig
    assert any("Handbetrieb" in g for g in gruende)
    assert da.SPERRSATZ in da.rendern(a)


def test_should_block_completeness_claim_when_folders_failed_to_read():
    a = _vollstaendig(ordner_fehlgeschlagen=2, timeouts=1)
    zulaessig, gruende = da.vollstaendigkeitsaussage_zulaessig(a)
    assert not zulaessig
    assert any("unvollständig gelesen" in g for g in gruende)


def test_should_block_completeness_claim_when_results_were_truncated():
    a = _vollstaendig(geprueft=500, vorhanden=46065)
    zulaessig, gruende = da.vollstaendigkeitsaussage_zulaessig(a)
    assert not zulaessig
    assert any("500/46065" in g for g in gruende)


def test_should_carry_numerator_and_denominator_in_the_rendering():
    """Der --list-Fall: eine Zahl ohne Nenner ist keine Aussage."""
    text = da.rendern(_vollstaendig())
    assert "3/3" in text
    assert "110/110" in text


def test_should_expose_the_verdict_in_the_versioned_object():
    d = da.als_dict(_vollstaendig(ordner_durchsucht=1))
    assert d["format_version"] == da.FORMAT_VERSION
    assert d["vollstaendigkeitsaussage_zulaessig"] is False
    assert d["einschraenkungen"]
    assert d["retrievalpfade"] == {"client-filter": 7, "imap-search": 9}


def test_should_render_uncovered_items_structured_not_as_free_text():
    a = _vollstaendig(
        konten_durchsucht=2,
        nicht_gedeckt=(
            ("HNU-Postfach", "Owner-Entscheid: live lesen, nichts speichern"),
        ),
    )
    d = da.als_dict(a)
    assert d["nicht_gedeckt"] == [
        {
            "was": "HNU-Postfach",
            "grund": "Owner-Entscheid: live lesen, nichts speichern",
        }
    ]
    assert "HNU-Postfach" in da.rendern(a)


def test_should_produce_a_stable_fingerprint_regardless_of_set_order():
    a = da.fingerprint("postsortierung", {"INBOX", "Gesendete Objekte"})
    b = da.fingerprint("postsortierung", {"Gesendete Objekte", "INBOX"})
    assert a == b
    assert a != da.fingerprint("postsortierung", {"INBOX"})
