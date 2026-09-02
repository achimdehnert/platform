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
    """Der Vertragspartner-D-Fall: 3 von 11 Nachrichten, weil nur der Posteingang gelesen wurde."""
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
    """Der Platzhalter-Fall: ein Pfad findet nichts, während der andere trifft.

    Ohne bestandene Kalibrierung — mit ihr wäre die Leermenge belegt statt verdächtig,
    siehe `test_should_not_warn_about_an_empty_path_that_passed_calibration`.
    """
    a = _vollstaendig(
        retrievalpfade=(("client-filter", 0), ("imap-search", 9)),
        kalibriert=("imap-search",),
    )
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


def test_should_report_which_path_found_what_the_other_missed():
    """R-2: der Wert zweier Pfade liegt in der Differenz, nicht in der Summe."""
    d = da.divergenz(
        {
            "server-suche": {("INBOX", b"1"), ("INBOX", b"2")},
            "client-filter": {("INBOX", b"1")},
        }
    )
    assert d == [("server-suche", "client-filter", 1)]


def test_should_report_no_divergence_when_both_paths_agree():
    gleich = {("INBOX", b"1")}
    assert da.divergenz({"a": set(gleich), "b": set(gleich)}) == []


def test_should_report_divergence_in_both_directions():
    d = da.divergenz({"a": {1, 2}, "b": {2, 3}})
    assert ("a", "b", 1) in d
    assert ("b", "a", 1) in d


def test_should_flag_folders_where_own_count_differs_from_the_server():
    """REC-9: der Nenner war bisher selbstreferenziell."""
    abweichend = da.nenner_pruefen(
        {"INBOX": 500, "Archiv": 12}, {"INBOX": 46065, "Archiv": 12}
    )
    assert abweichend == [("INBOX", 46065, 500)]


def test_should_not_treat_a_missing_server_count_as_divergence():
    """Ein Ordner ohne STATUS-Antwort ist eine fehlende Gegenprobe, kein Widerspruch."""
    assert da.nenner_pruefen({"Seltsam": 3}, {}) == []


def test_should_block_completeness_claim_when_the_denominator_is_disputed():
    a = _vollstaendig(nenner_divergenz=(("INBOX", 46065, 500),))
    zulaessig, gruende = da.vollstaendigkeitsaussage_zulaessig(a)
    assert not zulaessig
    assert any("REC-9" in g for g in gruende)
    assert "Server 46065" in da.rendern(a)


def test_should_state_the_guarantee_limit_in_the_certificate_itself():
    """K6: sonst liest sich 'Deckung vollständig' als 'alles Relevante gefunden'."""
    text = da.rendern(_vollstaendig())
    assert da.GARANTIEGRENZE in text
    assert "nicht die Relevanz" in text


def test_should_state_the_guarantee_limit_even_when_coverage_is_complete():
    """Gerade im grünen Fall ist die Grenze nötig — dort liegt die Verwechslung nahe."""
    zulaessig, _ = da.vollstaendigkeitsaussage_zulaessig(_vollstaendig())
    assert zulaessig
    assert da.GARANTIEGRENZE in da.rendern(_vollstaendig())


def test_should_pass_the_procedure_check_for_a_complete_certificate():
    ok, fehler = da.pruefkette(_vollstaendig())
    assert ok
    assert fehler == []


def test_should_accept_a_narrow_scope_when_it_is_declared():
    """Ein knapper Scope ist zulässig — aber nur benannt und begründet (§6.1)."""
    a = _vollstaendig(
        konten_durchsucht=1,
        nicht_gedeckt=(("Konto hnu", "Owner-Entscheid: nichts speichern"),),
    )
    ok, fehler = da.pruefkette(a)
    assert ok, fehler


def test_should_reject_a_narrow_scope_that_is_not_declared():
    """Derselbe Scope ohne Eintrag — genau diesen Unterschied misst K8."""
    ok, fehler = da.pruefkette(_vollstaendig(konten_durchsucht=1))
    assert not ok
    assert any("Konten 1/3" in f for f in fehler)


def test_should_reject_unreadable_folders_that_are_not_declared():
    ok, fehler = da.pruefkette(_vollstaendig(ordner_fehlgeschlagen=3))
    assert not ok
    assert any("unlesbare Ordner" in f for f in fehler)


def test_should_reject_a_certificate_produced_by_hand():
    ok, _ = da.pruefkette(_vollstaendig(erzeuger="manuell"))
    assert not ok


def test_should_reject_missing_mandatory_fields():
    ok, fehler = da.pruefkette(_vollstaendig(source_watermark="", query_fingerprint=""))
    assert not ok
    assert any("source_watermark" in f and "query_fingerprint" in f for f in fehler)


def test_should_survive_a_round_trip_through_the_serialised_form():
    """Der Hook prüft, was ein anderer Prozess geschrieben hat — das muss zurückgehen."""
    original = _vollstaendig(
        konten_durchsucht=2,
        nicht_gedeckt=(("Konto hnu", "nicht abgefragt"),),
        nenner_divergenz=(("INBOX", 46065, 500),),
    )
    zurueck = da.aus_dict(da.als_dict(original))
    assert zurueck.nicht_gedeckt == original.nicht_gedeckt
    assert zurueck.nenner_divergenz == original.nenner_divergenz
    assert zurueck.retrievalpfade == original.retrievalpfade
    assert da.pruefkette(zurueck) == da.pruefkette(original)


def test_should_produce_a_stable_fingerprint_regardless_of_set_order():
    a = da.fingerprint("postsortierung", {"INBOX", "Gesendete Objekte"})
    b = da.fingerprint("postsortierung", {"Gesendete Objekte", "INBOX"})
    assert a == b
    assert a != da.fingerprint("postsortierung", {"INBOX"})


def test_should_not_warn_about_an_empty_path_that_passed_calibration():
    """Pilotbefund 2026-07-27: die Warnung feuerte auch bei belegter Leermenge.

    Ein Pfad, der gerade bewiesen hat, dass er findet, was da ist, und dann nichts
    findet, hat ein Ergebnis geliefert — keinen Fehler.
    """
    a = _vollstaendig(
        retrievalpfade=(("client-filter", 0), ("server-suche", 0)),
        kalibriert=("client-filter", "server-suche"),
    )
    assert da.leere_pfade(a) == []
    assert "kaputte Abfrage" not in da.rendern(a)


def test_should_still_warn_about_an_empty_path_without_calibration():
    a = _vollstaendig(
        retrievalpfade=(("client-filter", 0), ("server-suche", 9)),
        kalibriert=("server-suche",),
    )
    assert da.leere_pfade(a) == ["client-filter"]
