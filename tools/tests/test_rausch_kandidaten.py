"""Tests für Rausch-Kandidaten aus 30 Tagen Index (V7, platform#3015 K4).

Kein Zugriff auf Index/Ledger: geprüft wird die Rechnung, nicht die Leitung.
Die Fixtures sind synthetisch (example.org) — dieses Repo ist öffentlich.
"""

import importlib.util
import pathlib
import sys

_SRC = (
    pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "rausch_kandidaten.py"
)
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
        treffer = [
            _treffer("selten@example.org", datum=f"2026-09-0{i}") for i in (1, 2)
        ]
        kandidaten = rk.kandidaten_ermitteln(treffer, {}, [])
        assert kandidaten == []

    def test_should_skip_a_sender_already_in_a_vorgang(self):
        treffer = [
            _treffer("bekannt@example.org", datum=f"2026-09-0{i}") for i in (1, 2, 3)
        ]
        vorgaenge = [
            {"nr": 1, "gegenueber": "Bekannt <bekannt@example.org>", "notiz": ""}
        ]
        kandidaten = rk.kandidaten_ermitteln(treffer, {}, vorgaenge)
        assert kandidaten == []

    def test_should_skip_a_sender_already_covered_by_a_rausch_rule_address(self):
        treffer = [
            _treffer("schonrausch@example.org", datum=f"2026-09-0{i}")
            for i in (1, 2, 3)
        ]
        rausch_regeln = {"nach_ordner_zur_loeschung": ["schonrausch@example.org"]}
        kandidaten = rk.kandidaten_ermitteln(treffer, rausch_regeln, [])
        assert kandidaten == []

    def test_should_skip_a_sender_whose_domain_is_already_covered_by_a_rausch_rule(
        self,
    ):
        treffer = [
            _treffer("neu@newsletter.example.org", datum=f"2026-09-0{i}")
            for i in (1, 2, 3)
        ]
        rausch_regeln = {"nach_ordner_zur_loeschung": ["newsletter.example.org"]}
        kandidaten = rk.kandidaten_ermitteln(treffer, rausch_regeln, [])
        assert kandidaten == []

    def test_should_not_count_a_hit_that_only_sits_in_gesendet(self):
        treffer = [
            _treffer(
                "selbst@example.org", datum="2026-09-01", ordner=["Gesendete Elemente"]
            ),
            _treffer(
                "selbst@example.org", datum="2026-09-02", ordner=["Gesendete Elemente"]
            ),
            _treffer(
                "selbst@example.org", datum="2026-09-03", ordner=["Gesendete Elemente"]
            ),
        ]
        kandidaten = rk.kandidaten_ermitteln(treffer, {}, [])
        assert kandidaten == []

    def test_should_not_exclude_a_candidate_via_own_domain_appearing_in_a_vorgang(self):
        """Die eigene Domain im Vorgangstext (Signatur/Cc) darf einen Absender
        aus derselben Firma nicht faelschlich als 'schon im Vorgang' decken —
        sonst blockt jede Erwaehnung von hnu.de/iil.gmbh/dehnert.team jeden
        Kollegen-Absender aus derselben Domain."""
        treffer = [_treffer("kollege@hnu.de", datum=f"2026-09-0{i}") for i in (1, 2, 3)]
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


# --- platform#3176: Schutzklassen (K1), Modell-Einordnung (K2), Bestand (K4) ---

PERSON = "erika.muster@partner.example.org"
RECHNUNG = "billing@cloud.example.com"
WERBUNG = "news@shop.example.com"


def _kandidat(adresse, betreffs=("Angebot",)):
    return rk.Kandidat(absender=adresse, treffer=len(betreffs), betreffs=list(betreffs))


def test_should_accept_attachment_flag_from_real_index():
    """Regression 2026-09-30: der Index liefert ``anhaenge`` als Bool, nicht als Liste."""
    assert rk._anhang_namen({"anhaenge": True}) == []
    assert rk._anhang_namen({"anhaenge": ["Rechnung.pdf"]}) == ["Rechnung.pdf"]


def test_should_read_attachment_names_from_index_field():
    """#3627: der Index liefert ``anhang_namen`` neben dem Bool ``anhaenge``."""
    treffer = {"anhaenge": True, "anhang_namen": ["AGB.pdf", "Rechnung_4711.pdf"]}
    assert rk._anhang_namen(treffer) == ["AGB.pdf", "Rechnung_4711.pdf"]


def test_should_protect_sender_whose_invoice_hides_in_the_attachment_name():
    """#3627: neutraler Betreff, Beleg nur im Anhangnamen — Absender bleibt draußen."""
    k = rk.Kandidat(
        absender=RECHNUNG,
        treffer=3,
        betreffs=["Ihre Unterlagen", "Neuigkeiten", "Tipps"],
        anhaenge=rk._anhang_namen(
            {"anhaenge": True, "anhang_namen": ["Rechnung_4711.pdf"]}
        ),
    )
    frei, raus = rk.schutz_filtern([k], eigene=set(), gesendet=set())
    assert frei == [] and raus[0].grund == "schutz:beleg"


class TestSchutzFiltern:
    def test_should_drop_sender_if_any_hit_is_an_invoice(self):
        """K1: ein Rechnungs-Betreff unter vielen reicht."""
        k = _kandidat(RECHNUNG, ["Newsletter", "Tipps", "Invoice #42"])
        frei, raus = rk.schutz_filtern([k], eigene=set(), gesendet=set())
        assert frei == [] and raus[0].grund == "schutz:beleg"

    def test_should_drop_sender_owner_wrote_to(self):
        k = _kandidat(PERSON, ["Hallo", "Rückfrage", "Termin"])
        frei, raus = rk.schutz_filtern([k], eigene=set(), gesendet={PERSON})
        assert frei == [] and raus[0].grund == "schutz:gesendet"

    def test_should_keep_plain_newsletter(self):
        k = _kandidat(WERBUNG, ["Sale", "Neu im Shop", "Nur heute"])
        frei, _ = rk.schutz_filtern([k], eigene=set(), gesendet=set())
        assert [f.absender for f in frei] == [WERBUNG]


class TestLlmEinordnen:
    def test_should_keep_only_newsletter_and_werbung(self):
        ks = [_kandidat(WERBUNG), _kandidat("info@verband.example.org")]
        behalten, raus = rk.llm_einordnen(
            ks, lambda _k: {"klassen": {"0": "werbung", "1": "partner"}}
        )
        assert [k.absender for k in behalten] == [WERBUNG]
        assert raus[0].grund == "klasse:partner"

    def test_should_overrule_model_for_person_address(self):
        """K5-Positivkontrolle: Modell sagt newsletter, Adressmuster sagt Person."""
        behalten, raus = rk.llm_einordnen(
            [_kandidat(PERSON)], lambda _k: {"klassen": {"0": "newsletter"}}
        )
        assert behalten == [] and raus[0].grund == "klasse:person"

    def test_should_overrule_model_for_freemail_domain(self):
        assert rk.plausibel("shopdeals@gmail.com", "werbung") == "person"

    def test_should_not_mistake_role_address_for_person(self):
        assert (
            rk.plausibel("news.letter@shop.example.com", "newsletter") == "newsletter"
        )

    def test_should_treat_unknown_class_as_unclear(self):
        behalten, raus = rk.llm_einordnen(
            [_kandidat(WERBUNG)], lambda _k: {"klassen": {"0": "spam?"}}
        )
        assert behalten == [] and raus[0].grund == "klasse:unklar"

    def test_should_fail_closed_when_model_unavailable(self):
        def kaputt(_k):
            raise RuntimeError("GROQ_API_KEY nicht gesetzt")

        behalten, raus = rk.llm_einordnen([_kandidat(WERBUNG)], kaputt)
        assert behalten == []
        assert raus[0].grund.startswith("einordnung_fehlgeschlagen")


class TestBestandEinordnen:
    def test_should_flag_person_and_invoice_entries_and_keep_newsletter(self):
        """K4: Vorlage markiert Person/Rechnung als fraglich, schreibt nichts."""
        im_ordner = {
            PERSON: ["Termin", "Rückfrage"],
            RECHNUNG: ["Your receipt"],
            WERBUNG: ["Sale", "Neu"],
        }

        def abfrage(anfragen):
            aus = []
            for i, a in enumerate(anfragen):
                if "von" in a:
                    t = [
                        {"betreff": b, "ordner": ["Zur Loeschung"]}
                        for b in im_ordner[a["von"]]
                    ]
                else:
                    t = (
                        [{"ordner": ["Gesendete Elemente"]}]
                        if a["an"] == PERSON
                        else []
                    )
                aus.append({"index": i, "treffer": t})
            return aus

        zeilen = rk.bestand_einordnen(
            [PERSON, RECHNUNG, WERBUNG],
            eigene=set(),
            abfrage=abfrage,
            klassifikator=lambda ks: {
                "klassen": {str(i): "newsletter" for i, _ in enumerate(ks)}
            },
        )
        nach = {z["eintrag"]: z for z in zeilen}
        assert nach[PERSON]["bleibt"] is False
        assert nach[PERSON]["im_loeschordner"] == 2
        assert nach[RECHNUNG]["einordnung"] == "schutz:beleg"
        assert nach[WERBUNG]["bleibt"] is True
