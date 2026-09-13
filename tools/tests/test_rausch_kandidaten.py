"""Tests für Rausch-Kandidaten aus 30 Tagen Index (V7, platform#3015 K4).

Kein Zugriff auf Index/Ledger: geprüft wird die Rechnung, nicht die Leitung.
Die Fixtures sind synthetisch (example.org) — dieses Repo ist öffentlich.
"""

import importlib.util
import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "rausch_kandidaten.py"
_spec = importlib.util.spec_from_file_location("rausch_kandidaten", _SRC)
rk = importlib.util.module_from_spec(_spec)
sys.modules["rausch_kandidaten"] = rk
_spec.loader.exec_module(rk)


def _treffer(von, betreff="Angebot des Tages", datum="2026-09-01", ordner=None):
    return {
        "id": f"{von}-{datum}",
        "datum": datum,
        "von": von,
        "betreff": betreff,
        "strang": von,
        "ordner": ordner or ["INBOX"],
        "anhaenge": [],
        "gefunden_in": "betreff",
    }


class TestKandidatenErmitteln:
    def test_should_surface_a_sender_with_three_hits(self):
        treffer = [
            _treffer("werbung@example.org", datum=f"2026-09-0{i}") for i in (1, 2, 3)
        ]
        kandidaten = rk.kandidaten_ermitteln(treffer, {}, [])
        assert [k.absender for k in kandidaten] == ["werbung@example.org"]
        assert kandidaten[0].treffer == 3

    def test_should_ignore_a_sender_with_only_two_hits(self):
        treffer = [_treffer("selten@example.org", datum=f"2026-09-0{i}") for i in (1, 2)]
        kandidaten = rk.kandidaten_ermitteln(treffer, {}, [])
        assert kandidaten == []

    def test_should_skip_a_sender_already_in_a_vorgang(self):
        treffer = [
            _treffer("bekannt@example.org", datum=f"2026-09-0{i}") for i in (1, 2, 3)
        ]
        vorgaenge = [{"nr": 1, "gegenueber": "Bekannt <bekannt@example.org>", "notiz": ""}]
        kandidaten = rk.kandidaten_ermitteln(treffer, {}, vorgaenge)
        assert kandidaten == []

    def test_should_skip_a_sender_already_covered_by_a_rausch_rule_address(self):
        treffer = [
            _treffer("schonrausch@example.org", datum=f"2026-09-0{i}") for i in (1, 2, 3)
        ]
        rausch_regeln = {"nach_ordner_zur_loeschung": ["schonrausch@example.org"]}
        kandidaten = rk.kandidaten_ermitteln(treffer, rausch_regeln, [])
        assert kandidaten == []

    def test_should_skip_a_sender_whose_domain_is_already_covered_by_a_rausch_rule(self):
        treffer = [
            _treffer("neu@newsletter.example.org", datum=f"2026-09-0{i}")
            for i in (1, 2, 3)
        ]
        rausch_regeln = {"nach_ordner_zur_loeschung": ["newsletter.example.org"]}
        kandidaten = rk.kandidaten_ermitteln(treffer, rausch_regeln, [])
        assert kandidaten == []

    def test_should_not_count_a_hit_that_only_sits_in_gesendet(self):
        treffer = [
            _treffer("selbst@example.org", datum="2026-09-01", ordner=["Gesendete Elemente"]),
            _treffer("selbst@example.org", datum="2026-09-02", ordner=["Gesendete Elemente"]),
            _treffer("selbst@example.org", datum="2026-09-03", ordner=["Gesendete Elemente"]),
        ]
        kandidaten = rk.kandidaten_ermitteln(treffer, {}, [])
        assert kandidaten == []

    def test_should_not_exclude_a_candidate_via_own_domain_appearing_in_a_vorgang(self):
        """Die eigene Domain im Vorgangstext (Signatur/Cc) darf einen Absender
        aus derselben Firma nicht faelschlich als 'schon im Vorgang' decken —
        sonst blockt jede Erwaehnung von hnu.de/iil.gmbh/dehnert.team jeden
        Kollegen-Absender aus derselben Domain."""
        treffer = [
            _treffer("kollege@hnu.de", datum=f"2026-09-0{i}") for i in (1, 2, 3)
        ]
        vorgaenge = [
            {"nr": 1, "notiz": "Antwort kommt laut hnu.de-Sekretariat naechste Woche"}
        ]
        kandidaten = rk.kandidaten_ermitteln(treffer, {}, vorgaenge)
        assert [k.absender for k in kandidaten] == ["kollege@hnu.de"]


class TestRegelVorschlag:
    def test_should_match_the_ledger_rule_field_names(self):
        kandidat = rk.Kandidat(
            absender="werbung@example.org", treffer=5, beispiel_betreffs=["A", "B"]
        )
        regel = rk.regel_vorschlag(kandidat, "2026-09-13")
        assert set(regel.keys()) == {
            "absender",
            "typ",
            "ziel",
            "treffer_30_tage",
            "vorschlag_stichtag",
            "quelle",
        }
        assert regel["absender"] == "werbung@example.org"
        assert regel["ziel"] == "Zur Loeschung"
        assert regel["treffer_30_tage"] == 5
        assert regel["vorschlag_stichtag"] == "2026-09-13"
