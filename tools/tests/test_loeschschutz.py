"""Tests für den Löschschutz vor „Zur Loeschung" (platform#3176 K1/K3/K5).

Kein Zugriff auf Index, Postfach oder Rollen-Registry: die Index-Abfrage wird
als Funktion hereingereicht. Alle Adressen sind erfunden (example.org/.com) —
dieses Repo ist öffentlich.
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

PERSON = "erika.muster@partner.example.org"
RECHNUNG = "billing@cloud.example.com"
WERBUNG = "news@shop.example.com"


@pytest.fixture(autouse=True)
def ohne_ledger(monkeypatch, tmp_path):
    """Owner-Einträge (``owner_gelernt``) nie aus dem echten Ledger lesen."""
    monkeypatch.setattr(ls, "LEDGER", tmp_path / "kein-ledger.json")


def _index(gesendet_an=()):
    """Fake für ``suche.py --batch``: ``an``-Abfragen treffen Gesendet-Ordner."""

    def abfrage(anfragen):
        aus = []
        for i, a in enumerate(anfragen):
            treffer = []
            if a.get("an") in gesendet_an:
                treffer = [{"ordner": ["Gesendete Elemente"], "von": "ich@x"}]
            aus.append({"index": i, "treffer": treffer, "deckung": {}})
        return aus

    return abfrage


class TestLoeschordner:
    @pytest.mark.parametrize(
        "pfad",
        ["Zur Loeschung", "INBOX.Zur Loeschung", "INBOX/Zur Löschung", "zur_loeschung"],
    )
    def test_should_recognise_deletion_folder_in_every_spelling(self, pfad):
        assert ls.ist_loeschordner(pfad)

    def test_should_not_treat_archive_as_deletion_folder(self):
        assert not ls.ist_loeschordner("Archiv/2026")


class TestPruefe:
    def test_should_protect_invoice_subject(self):
        befund = ls.pruefe(
            f"Cloud Billing <{RECHNUNG}>",
            "Your invoice for September",
            eigene=set(),
            gesendet=set(),
        )
        assert befund.klasse == "beleg"

    def test_should_protect_security_code_subject(self):
        befund = ls.pruefe(WERBUNG, "Ihr Sicherheitscode", eigene=set(), gesendet=set())
        assert befund.klasse == "beleg"

    def test_should_protect_invoice_attachment(self):
        befund = ls.pruefe(
            WERBUNG, "Ihre Unterlagen", eigene=set(), gesendet=set(),
            anhaenge=["Rechnung_2026-09.pdf"],
        )  # fmt: skip
        assert befund.klasse == "beleg"

    def test_should_protect_sender_owner_wrote_to(self):
        befund = ls.pruefe(PERSON, "Kurze Frage", eigene=set(), gesendet={PERSON})
        assert befund.klasse == "gesendet"

    def test_should_protect_own_address_from_registry(self, tmp_path):
        reg = tmp_path / "roles.json"
        reg.write_text(
            json.dumps({"roles": {"x": {"from": "Ich <ich@hochschule.example>"}}})
        )
        eigene = ls.eigene_adressen(reg)
        befund = ls.pruefe(
            "ich@hochschule.example", "Notiz", eigene=eigene, gesendet=set()
        )
        assert befund.klasse == "eigene_adresse"

    def test_should_protect_every_address_under_own_company_domain(self):
        befund = ls.pruefe("kollege@iil.gmbh", "Hallo", eigene=set(), gesendet=set())
        assert befund.klasse == "eigene_adresse"

    def test_should_let_plain_newsletter_through(self):
        assert (
            ls.pruefe(WERBUNG, "Nur heute: 20 %", eigene=set(), gesendet=set()) is None
        )

    def test_should_tolerate_missing_registry(self, tmp_path):
        assert ls.eigene_adressen(tmp_path / "fehlt.json") == set()


class TestFiltereVerschiebung:
    HITS = [
        ("m1", "2026-09-01", f"Erika Muster <{PERSON}>", "Termin nächste Woche"),
        ("m2", "2026-09-02", RECHNUNG, "Invoice #123"),
        ("m3", "2026-09-03", WERBUNG, "Herbst-Sale"),
    ]

    def test_should_hold_person_and_invoice_and_move_only_newsletter(self):
        """K5-Positivkontrolle: Person und Rechnung bleiben liegen."""
        frei, gehalten = ls.filtere_verschiebung(
            "Zur Loeschung", self.HITS, eigene=set(), abfrage=_index({PERSON})
        )
        assert [h[0] for h in frei] == ["m3"]
        assert {h[0]: b.klasse for h, b in gehalten} == {
            "m1": "gesendet",
            "m2": "beleg",
        }

    def test_should_pass_everything_when_target_is_not_deletion_folder(self):
        def nie(_):
            raise AssertionError("Index darf ohne Löschordner nicht gefragt werden")

        frei, gehalten = ls.filtere_verschiebung(
            "Archiv/2026", self.HITS, eigene=set(), abfrage=nie
        )
        assert frei == self.HITS and gehalten == []

    def test_should_fail_closed_when_index_unreachable(self):
        def kaputt(_):
            raise RuntimeError("Mail-Index nicht erreichbar")

        with pytest.raises(RuntimeError):
            ls.filtere_verschiebung(
                "Zur Loeschung", self.HITS, eigene=set(), abfrage=kaputt
            )

    def test_should_only_count_sent_folders_as_history(self):
        def eingang(anfragen):
            return [
                {"index": i, "treffer": [{"ordner": ["INBOX"]}]}
                for i, _ in enumerate(anfragen)
            ]

        assert ls.gesendet_an([PERSON], eingang) == set()


# --- Verdrahtung in beiden Verschiebe-Werkzeugen (K3) -------------------------


@pytest.fixture
def ohne_registry(monkeypatch, tmp_path):
    monkeypatch.setattr(ls, "ROLLEN_REGISTRY", tmp_path / "fehlt.json")


def test_should_not_move_person_or_invoice_via_imap(monkeypatch, ohne_registry):
    om = _load("organize_mail")
    monkeypatch.setattr(om, "loeschschutz", ls)
    monkeypatch.setattr(ls, "index_batch", _index({PERSON}))
    monkeypatch.setattr(om, "list_folders", lambda _i: ["INBOX", "INBOX.Zur Loeschung"])
    monkeypatch.setattr(
        om, "_matches", lambda *a, **k: list(TestFiltereVerschiebung.HITS)
    )
    bewegt = []
    monkeypatch.setattr(om, "_move", lambda _i, _s, _t, uids: bewegt.extend(uids))

    om.cmd_move(object(), "INBOX", "INBOX.Zur Loeschung", "", None, True)

    assert bewegt == ["m3"]


def test_should_not_move_person_or_invoice_via_graph(monkeypatch, ohne_registry):
    gm = _load("graph_mail")
    monkeypatch.setattr(gm, "loeschschutz", ls)
    monkeypatch.setattr(ls, "index_batch", _index({PERSON}))
    monkeypatch.setattr(
        gm, "_find_messages", lambda *a, **k: list(TestFiltereVerschiebung.HITS)
    )
    monkeypatch.setattr(gm, "ensure_path", lambda *a, **k: "zielid")
    bewegt = []

    def fake_http(method, url, **k):
        bewegt.append(url.split("/messages/")[1].split("/")[0])
        return gm._Resp(201, "{}")

    monkeypatch.setattr(gm, "_http", fake_http)
    monkeypatch.setattr(gm, "_basis", lambda: "https://graph.example")

    gm.cmd_move("tok", "example", "Zur Loeschung", "inbox", True)

    assert bewegt == ["m3"]


def test_should_move_nothing_to_deletion_folder_when_index_down(
    monkeypatch, ohne_registry
):
    gm = _load("graph_mail")
    monkeypatch.setattr(gm, "loeschschutz", ls)

    def kaputt(_):
        raise RuntimeError("Mail-Index nicht erreichbar")

    monkeypatch.setattr(ls, "index_batch", kaputt)
    monkeypatch.setattr(
        gm, "_find_messages", lambda *a, **k: list(TestFiltereVerschiebung.HITS)
    )
    monkeypatch.setattr(
        gm, "_http", lambda *a, **k: pytest.fail("darf nicht verschieben")
    )
    with pytest.raises(SystemExit):
        gm.cmd_move("tok", "example", "Zur Loeschung", "inbox", True)
