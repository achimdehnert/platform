"""Tests für den Regel-Interpreter (ADR-284 §7a, tools/mail_agent/regeln.py).

Jeder Test benennt die Zeile aus §7a, die er festhält — die Regeln des
Lebenszyklus sind der Testgegenstand, nicht die Implementierung.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "regeln.py"
_spec = importlib.util.spec_from_file_location("regeln", _SRC)
regeln = importlib.util.module_from_spec(_spec)
sys.modules["regeln"] = regeln  # @dataclass braucht das Modul in sys.modules
_spec.loader.exec_module(regeln)


def _nachricht(i, absender, betreff, ordner="Posteingang"):
    return {
        "id": f"m{i}",
        "absender": absender,
        "betreff": betreff,
        "datum": "2026-07-01T08:00:00Z",
        "ordner": ordner,
    }


def _bewegung(i, absender, betreff, ziel="IIL.Finanzen"):
    return {
        "id": f"m{i}",
        "absender": absender,
        "betreff": betreff,
        "ziel": ziel,
        "zeit": "2026-07-01T09:00:00Z",
    }


def _regel(**kw):
    basis = {
        "regel_id": "r1",
        "quelle": "ansage",
        "aktion": "verschieben",
        "ziel": "IIL.Finanzen",
        "kriterium": {"absender_domain": "hoster.de"},
    }
    basis.update(kw)
    return regeln.Regel(**basis)


# --- Zwei Quellen, unterschiedlich stark ------------------------------------


def test_should_not_derive_rule_from_single_observation():
    """§7a: nie aus einem Einzelfall — ein Verschieben kann eine Ausnahme sein."""
    kandidaten = regeln.kandidaten_aus_bewegungen(
        [_bewegung(1, "a@hoster.de", "Rechnung")]
    )
    assert kandidaten == []


def test_should_derive_candidate_from_two_aligned_observations():
    kandidaten = regeln.kandidaten_aus_bewegungen(
        [
            _bewegung(1, "a@hoster.de", "Rechnung 1"),
            _bewegung(2, "b@hoster.de", "Rechnung 2"),
        ]
    )
    assert len(kandidaten) == 1
    assert kandidaten[0]["kriterium"] == {"absender_domain": "hoster.de"}
    assert kandidaten[0]["ziel"] == "IIL.Finanzen"


def test_should_not_group_observations_into_different_targets():
    """Gleichgerichtet heißt: dieselbe Domain in DENSELBEN Ordner."""
    kandidaten = regeln.kandidaten_aus_bewegungen(
        [
            _bewegung(1, "a@hoster.de", "x", ziel="IIL.Finanzen"),
            _bewegung(2, "b@hoster.de", "y", ziel="IIL.Technik"),
        ]
    )
    assert kandidaten == []


def test_should_accept_explicit_instruction_without_threshold():
    """Eine Ansage des Owners gilt sofort, ohne Schwellwert."""
    r = _regel(quelle="ansage", belege=[])
    assert r.zustand == "vorschlag"


def test_should_reject_observation_rule_below_threshold():
    with pytest.raises(regeln.RegelFehler, match="Beleg"):
        _regel(quelle="beobachtung", belege=[_bewegung(1, "a@hoster.de", "x")])


# --- Verschieben und Löschen sind nicht symmetrisch --------------------------


def test_should_never_derive_trash_rule_from_observation():
    """§7a: aus einem Löschvorgang wird NIE automatisch eine Trash-Regel."""
    with pytest.raises(regeln.RegelFehler, match="loeschen"):
        _regel(
            quelle="beobachtung",
            aktion="loeschen",
            belege=[_bewegung(1, "a@x.de", "1"), _bewegung(2, "b@x.de", "2")],
        )


def test_should_allow_trash_rule_on_explicit_instruction():
    r = _regel(quelle="ansage", aktion="loeschen", ziel="Papierkorb")
    assert r.aktion == "loeschen"


def test_should_reject_empty_criterion():
    with pytest.raises(regeln.RegelFehler, match="leeres Kriterium"):
        _regel(kriterium={})


# --- Vorschlag: vier Pflichtteile -------------------------------------------


def test_should_refuse_proposal_without_backtest():
    """§7a: 'Ohne diesen Schritt kein Vorschlag.'"""
    kandidat = {
        "kriterium": {"absender_domain": "hoster.de"},
        "aktion": "verschieben",
        "ziel": "IIL.Finanzen",
        "belege": [
            _bewegung(1, "a@hoster.de", "R1"),
            _bewegung(2, "b@hoster.de", "R2"),
        ],
    }
    with pytest.raises(regeln.RegelFehler, match="Trockenlauf"):
        regeln.vorschlag_bauen(kandidat, [], regel_id="r1")


def test_should_build_proposal_with_all_four_parts():
    bestand = [
        _nachricht(1, "a@hoster.de", "Rechnung Juli"),
        _nachricht(2, "b@hoster.de", "Rechnung August"),
        _nachricht(3, "c@hoster.de", "Wartungsfenster Sonntag"),
    ]
    kandidat = {
        "kriterium": {"absender_domain": "hoster.de"},
        "aktion": "verschieben",
        "ziel": "IIL.Finanzen",
        "belege": [
            _bewegung(1, "a@hoster.de", "Rechnung Juli"),
            _bewegung(2, "b@hoster.de", "Rechnung August"),
        ],
    }
    v = regeln.vorschlag_bauen(kandidat, bestand, regel_id="r1")
    assert v["beobachtung"] and len(v["beobachtung"]) == 2  # 1) Beleg
    assert "hoster.de" in v["regel_text"]  # 2) Klartext
    assert v["trockenlauf"]["treffer"] == 3  # 3) Trockenlauf
    assert v["gegenprobe"]["nicht_von_hand_bewegt"] == 1  # 4) Gegenprobe
    assert v["regel"].zustand == "vorschlag"


def test_should_surface_collateral_in_counter_check():
    """Realfall 2026-07-27: eine Hoster-Regel hätte 52 Sicherheitshinweise im
    Rechnungsordner begraben — sichtbar erst durch die Stichprobe."""
    bestand = [
        _nachricht(1, "a@hoster.de", "Rechnung Juli"),
        _nachricht(2, "b@hoster.de", "Rechnung August"),
    ]
    bestand += [
        _nachricht(10 + i, "sec@hoster.de", "Sicherheitshinweis Zertifikat")
        for i in range(52)
    ]
    r = _regel(quelle="ansage")
    g = regeln.gegenprobe(
        r,
        bestand,
        [
            _bewegung(1, "a@hoster.de", "Rechnung Juli"),
            _bewegung(2, "b@hoster.de", "Rechnung August"),
        ],
    )
    assert g["treffer"] == 54
    assert g["nicht_von_hand_bewegt"] == 52
    assert g["anteil_fremd"] > 0.9
    assert g["gruppen"][0]["anzahl"] == 52
    assert "sicherheitshinweis" in g["gruppen"][0]["signatur"]


# --- Lebenszyklus ------------------------------------------------------------


def test_should_not_activate_without_explicit_confirmation():
    """§7a: kein Pfad, auf dem eine Beobachtung unmittelbar zu einer wirkenden Regel wird."""
    r = _regel()
    with pytest.raises(regeln.RegelFehler, match="Bestätigung"):
        regeln.aktivieren(r, bestaetigt=False)
    assert r.zustand == "vorschlag"


def test_should_activate_on_confirmation():
    r = regeln.aktivieren(_regel(), bestaetigt=True)
    assert r.zustand == "aktiv"
    assert r.historie[-1]["zustand"] == "aktiv"


def test_should_pause_rule_on_counter_example_instead_of_narrowing():
    """§7a: Widerspruch pausiert die Regel, statt sie still zu verengen."""
    r = regeln.aktivieren(_regel(), bestaetigt=True)
    kriterium_vorher = dict(r.kriterium)
    regeln.gegenbeispiel(r, {"betreff": "Rechnung Juli", "ziel": "Posteingang"})
    assert r.zustand == "strittig"
    assert r.kriterium == kriterium_vorher  # KEINE automatische Verengung
    assert regeln.wirksam([r]) == []  # wirkt nicht weiter


def test_should_keep_rule_after_retirement():
    """§7a: Regeln werden nicht gelöscht — sonst ist der Bestand unerklärlich."""
    r = regeln.stilllegen(regeln.aktivieren(_regel(), bestaetigt=True), "überholt")
    assert r.zustand == "stillgelegt"
    assert [h["zustand"] for h in r.historie] == ["aktiv", "stillgelegt"]


def test_should_only_apply_active_rules():
    bestand = [_nachricht(1, "a@hoster.de", "Rechnung")]
    for zustand in ("vorschlag", "strittig", "stillgelegt"):
        r = _regel(zustand=zustand)
        bewegungen, rest = regeln.plan([r], bestand)
        assert bewegungen == [] and len(rest) == 1, zustand


# --- Kennzahl: Restmenge -----------------------------------------------------


def test_should_measure_remainder_not_hit_count():
    """§7a: Kennzahl ist die Restmenge, nicht die Trefferzahl."""
    bestand = [
        _nachricht(1, "a@hoster.de", "Rechnung"),
        _nachricht(2, "b@hoster.de", "Rechnung"),
        _nachricht(3, "chef@kunde.de", "Angebot"),
        _nachricht(4, "chef@kunde.de", "Rückfrage"),
    ]
    r = regeln.aktivieren(_regel(), bestaetigt=True)
    k = regeln.restmenge([r], bestand)
    assert k["bestand"] == 4
    assert k["von_regeln_getroffen"] == 2
    assert k["restmenge"] == 2
    assert k["anteil_rest"] == 0.5
    assert k["top_absender_im_rest"][0] == {"absender": "chef@kunde.de", "anzahl": 2}


def test_should_report_full_remainder_without_rules():
    bestand = [_nachricht(1, "a@x.de", "y")]
    assert regeln.restmenge([], bestand)["restmenge"] == 1


# --- Protokoll und Rücknahme -------------------------------------------------


def test_should_log_every_move_with_source_target_and_rule(tmp_path):
    """§7a: ohne dieses Protokoll ist ein Rollback nicht möglich."""
    bestand = [_nachricht(1, "a@hoster.de", "Rechnung", ordner="Posteingang")]
    r = regeln.aktivieren(_regel(), bestaetigt=True)
    bewegungen, _ = regeln.plan([r], bestand)
    p = regeln.protokollieren(bewegungen, tmp_path / "p.jsonl", "lauf-1")
    eintrag = json.loads(p.read_text().splitlines()[0])
    assert eintrag["quellordner"] == "Posteingang"
    assert eintrag["zielordner"] == "IIL.Finanzen"
    assert eintrag["regel_id"] == "r1"
    assert eintrag["lauf_id"] == "lauf-1"


def test_should_invert_a_logged_run(tmp_path):
    bestand = [_nachricht(1, "a@hoster.de", "Rechnung", ordner="Posteingang")]
    r = regeln.aktivieren(_regel(), bestaetigt=True)
    bewegungen, _ = regeln.plan([r], bestand)
    regeln.protokollieren(bewegungen, tmp_path / "p.jsonl", "lauf-1")
    zurueck = regeln.ruecknahme(tmp_path / "p.jsonl", "lauf-1")
    assert zurueck[0]["quellordner"] == "IIL.Finanzen"
    assert zurueck[0]["zielordner"] == "Posteingang"


def test_should_refuse_rollback_without_protocol(tmp_path):
    with pytest.raises(regeln.RegelFehler, match="Protokoll"):
        regeln.ruecknahme(tmp_path / "fehlt.jsonl", "lauf-1")


# --- Persistenz und Normalisierung -------------------------------------------


def test_should_roundtrip_rules_through_disk(tmp_path):
    r = regeln.aktivieren(_regel(), bestaetigt=True)
    p = regeln.speichern([r], tmp_path / "mail-regeln.json")
    wieder = regeln.laden(p)
    assert len(wieder) == 1
    assert wieder[0].zustand == "aktiv"
    assert wieder[0].als_text() == r.als_text()


def test_should_prefer_header_date_over_arrival_stamp():
    """Lesson 2026-07-28: der Ankunftsstempel wird beim Umsortieren neu gesetzt."""
    m = regeln.aus_graph(
        {
            "id": "x",
            "subject": "Rechnung",
            "from": {"emailAddress": {"address": "A@Hoster.de"}},
            "sentDateTime": "2026-01-05T10:00:00Z",
            "receivedDateTime": "2026-07-28T09:00:00Z",
        },
        ordner="Archiv/2026",
    )
    assert m["datum"] == "2026-01-05T10:00:00Z"
    assert m["ordner"] == "Archiv/2026"


def test_should_match_sender_case_insensitively():
    r = _regel(kriterium={"absender": "A@Hoster.de"})
    assert regeln.trifft(r, _nachricht(1, "a@hoster.de", "x"))


def test_should_require_all_criteria_to_match():
    r = _regel(
        kriterium={"absender_domain": "hoster.de", "betreff_enthaelt": "Rechnung"}
    )
    assert regeln.trifft(r, _nachricht(1, "a@hoster.de", "Rechnung Juli"))
    assert not regeln.trifft(r, _nachricht(2, "a@hoster.de", "Wartungsfenster"))


def test_should_not_match_domain_suffix_of_other_domain():
    """'hoster.de' darf nicht 'boeser-hoster.de' … oder 'x@nichthoster.de' fangen."""
    r = _regel(kriterium={"absender_domain": "hoster.de"})
    assert not regeln.trifft(r, _nachricht(1, "a@nichthoster.de", "x"))
