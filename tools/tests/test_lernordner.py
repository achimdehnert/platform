"""Tests für die Lernordner (platform#3629).

Kein Postfach, kein Index, kein echtes Ledger: Postfach und Index-Abfrage sind
Fakes, das Ledger liegt in ``tmp_path``. Alle Adressen sind erfunden
(example.org/.com) — dieses Repo ist öffentlich.
"""

import importlib.util
import json
import pathlib
import sys

import pytest

_DIR = pathlib.Path(__file__).resolve().parents[1] / "mail_agent"
sys.path.insert(0, str(_DIR))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ls = _load("loeschschutz")
lo = _load("lernordner")

WERBUNG = "news@shop.example.com"
PARTNER = "erika.muster@partner.example.org"
RECHNUNG = "billing@cloud.example.com"


def _index(gesendet_an=()):
    def abfrage(anfragen):
        return [
            {
                "index": i,
                "treffer": [{"ordner": ["Gesendete Elemente"]}]
                if a.get("an") in gesendet_an
                else [],
            }
            for i, a in enumerate(anfragen)
        ]

    return abfrage


class FakePostfach:
    def __init__(self, ordner):
        self.inhalt = {k: list(v) for k, v in ordner.items()}
        self.bewegungen = []

    def ordner(self):
        return list(self.inhalt)

    def anlegen(self, pfad):
        self.inhalt.setdefault(pfad, [])

    def liste(self, pfad):
        return list(self.inhalt.get(pfad, []))

    def verschiebe(self, quelle, ziel, kennungen):
        self.bewegungen.append((quelle, ziel, list(kennungen)))
        return len(kennungen)

    def schliessen(self):
        pass


class TestEintragFuer:
    def test_should_learn_the_address_from_absender_folder(self):
        assert lo.eintrag_fuer("absender", f"Shop <{WERBUNG}>", set()) == (WERBUNG, "")

    def test_should_learn_the_domain_from_domain_folder(self):
        assert lo.eintrag_fuer("domain", WERBUNG, set())[0] == "shop.example.com"

    @pytest.mark.parametrize(
        "adresse", ["jemand@gmail.com", "kollege@hnu.de", "sys@mail.hnu.de"]
    )
    def test_should_never_learn_freemail_or_university_domain(self, adresse):
        eintrag, grund = lo.eintrag_fuer("domain", adresse, set())
        assert eintrag is None and "nie als Ganzes" in grund

    def test_should_refuse_own_address_in_either_folder(self):
        for typ in lo.LERNORDNER:
            assert lo.eintrag_fuer(typ, "ich@iil.gmbh", set())[0] is None


class TestLedgerErgaenzen:
    def test_should_add_rule_and_owner_entry_once(self):
        ledger = {"rausch_regeln": {"nach_ordner_zur_loeschung": ["alt@example.org"]}}
        lernungen = [(WERBUNG, "absender", "iil"), (WERBUNG, "absender", "hnu")]
        neu = lo.ledger_ergaenzen(ledger, lernungen, "2026-09-30")
        regeln = ledger["rausch_regeln"]
        assert neu == [WERBUNG]
        assert regeln["nach_ordner_zur_loeschung"] == ["alt@example.org", WERBUNG]
        assert regeln["owner_gelernt"] == [
            {
                "eintrag": WERBUNG,
                "typ": "absender",
                "konto": "iil",
                "am": "2026-09-30",
                "quelle": "lernordner.py",
            }
        ]

    def test_should_promote_existing_rule_to_owner_entry(self):
        ledger = {"rausch_regeln": {"nach_ordner_zur_loeschung": [WERBUNG]}}
        lo.ledger_ergaenzen(ledger, [(WERBUNG, "absender", "iil")], "2026-09-30")
        regeln = ledger["rausch_regeln"]
        assert regeln["nach_ordner_zur_loeschung"] == [WERBUNG]
        assert [z["eintrag"] for z in regeln["owner_gelernt"]] == [WERBUNG]


class TestOwnerUebersteuerung:
    HITS = [
        ("m1", "2026-09-01", PARTNER, "Einladung Sommerfest"),
        ("m2", "2026-09-02", RECHNUNG, "Invoice #7"),
    ]

    def test_should_hold_sent_history_without_owner_entry(self):
        _, gehalten = ls.filtere_verschiebung(
            "Zur Loeschung", self.HITS[:1], eigene=set(),
            abfrage=_index({PARTNER}), gelernt=[],
        )  # fmt: skip
        assert [b.klasse for _, b in gehalten] == ["gesendet"]

    def test_should_override_sent_history_for_learned_domain(self):
        frei, _ = ls.filtere_verschiebung(
            "Zur Loeschung", self.HITS[:1], eigene=set(),
            abfrage=_index({PARTNER}), gelernt=["partner.example.org"],
        )  # fmt: skip
        assert [h[0] for h in frei] == ["m1"]

    def test_should_keep_invoice_even_for_learned_sender(self):
        """K4-Positivkontrolle: der Owner-Zug hebt den Beleg-Schutz nicht auf."""
        frei, gehalten = ls.filtere_verschiebung(
            "Zur Loeschung", self.HITS[1:], eigene=set(),
            abfrage=_index(), gelernt=[RECHNUNG],
        )  # fmt: skip
        assert frei == [] and gehalten[0][1].klasse == "beleg"

    def test_should_match_subdomain_but_not_lookalike(self):
        assert ls.trifft_eintrag("a@news.shop.example.com", "shop.example.com")
        assert not ls.trifft_eintrag("a@notshop.example.com", "shop.example.com")

    def test_should_read_no_owner_entries_without_ledger(self, tmp_path):
        assert ls.owner_gelernt(tmp_path / "fehlt.json") == []


@pytest.fixture
def umgebung(monkeypatch, tmp_path):
    monkeypatch.setattr(ls, "ROLLEN_REGISTRY", tmp_path / "fehlt.json")
    monkeypatch.setattr(ls, "index_batch", _index({PARTNER}))
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"rausch_regeln": {"nach_ordner_zur_loeschung": []}}))
    return ledger


class TestLauf:
    def _postfach(self):
        return FakePostfach(
            {
                "inbox": [
                    ("e1", "2026-09-29", PARTNER, "Neue Einladung"),
                    ("e2", "2026-09-29", "ok@elsewhere.example.org", "Frage"),
                ],
                "Zur Löschung": [],
                "Lernen Absender loeschen": [
                    ("l1", "2026-09-28", RECHNUNG, "Invoice #7"),
                    ("l2", "2026-09-28", "ich@iil.gmbh", "Notiz"),
                ],
                "Lernen Domain loeschen": [
                    ("l3", "2026-09-27", PARTNER, "Sommerfest"),
                ],
            }
        )

    def test_should_learn_move_and_return_protected(self, umgebung):
        pf = self._postfach()
        bilanz = lo.lauf(
            ["iil"], apply=True, oeffnen=lambda _k: pf, ledger_pfad=umgebung
        )
        regeln = json.loads(umgebung.read_text())["rausch_regeln"]
        assert sorted(regeln["nach_ordner_zur_loeschung"]) == [
            RECHNUNG,
            "partner.example.org",
        ]
        assert (
            "Lernen Domain loeschen", "Zur Löschung", ["l3"]
        ) in pf.bewegungen  # fmt: skip
        # Beleg (Schutz) und eigene Adresse (abgewiesen) gehen zurück.
        assert ("Lernen Absender loeschen", "inbox", ["l1", "l2"]) in pf.bewegungen
        # Künftige Post des gelernten Partners trotz Gesendet-Historie.
        assert ("inbox", "Zur Löschung", ["e1"]) in pf.bewegungen
        assert bilanz["iil"] == {"geloescht": 1, "zurueck": 2, "posteingang": 1}

    def test_should_neither_write_nor_move_in_dry_run(self, umgebung):
        vorher = umgebung.read_text()
        pf = self._postfach()
        lo.lauf(["iil"], apply=False, oeffnen=lambda _k: pf, ledger_pfad=umgebung)
        assert umgebung.read_text() == vorher and pf.bewegungen == []

    def test_should_move_nothing_to_deletion_folder_when_index_down(
        self, umgebung, monkeypatch
    ):
        def kaputt(_):
            raise RuntimeError("Mail-Index nicht erreichbar")

        monkeypatch.setattr(ls, "index_batch", kaputt)
        pf = self._postfach()
        bilanz = lo.lauf(
            ["iil"], apply=True, oeffnen=lambda _k: pf, ledger_pfad=umgebung
        )
        assert not any(z == "Zur Löschung" for _, z, _ in pf.bewegungen)
        assert "Löschschutz nicht prüfbar" in bilanz["iil"]["fehler"]

    def test_should_report_unreachable_account(self, umgebung):
        def nie(_k):
            raise lo.KontoNichtErreichbar("nicht freigegeben")

        bilanz = lo.lauf(["ad"], apply=True, oeffnen=nie, ledger_pfad=umgebung)
        assert bilanz == {"ad": {"nicht_erreichbar": "nicht freigegeben"}}

    def test_should_create_missing_learning_folders_with_prefix(self):
        pf = FakePostfach({"INBOX": []})
        lo.anlegen(["ad"], oeffnen=lambda _k: pf)
        assert set(pf.ordner()) == {
            "INBOX",
            "INBOX.Lernen Absender loeschen",
            "INBOX.Lernen Domain loeschen",
        }
