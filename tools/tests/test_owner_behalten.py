"""Tests: die Owner-Behalten-Liste wird durchgesetzt (platform#3637).

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

BEHALTEN_ADRESSE = "autorin@letters.example.com"
BEHALTEN_DOMAIN = "wissen.example.org"
WERBUNG = "promo@letters.example.com"
FREMD = "angebot@shop.example.net"


def _ledger(pfad, behalten, gelernt=()):
    pfad.write_text(
        json.dumps(
            {
                "rausch_regeln": {
                    "nach_ordner_zur_loeschung": list(gelernt),
                    "owner_gelernt": [{"eintrag": g} for g in gelernt],
                    "bewusst_NICHT_aufgenommen": behalten,
                }
            }
        )
    )
    return pfad


def _kein_index(anfragen):
    return [{"index": i, "treffer": []} for i, _ in enumerate(anfragen)]


@pytest.fixture(autouse=True)
def isoliert(monkeypatch, tmp_path):
    monkeypatch.setattr(ls, "LEDGER", tmp_path / "kein-ledger.json")
    monkeypatch.setattr(ls, "ROLLEN_REGISTRY", tmp_path / "fehlt.json")
    monkeypatch.setattr(ls, "index_batch", _kein_index)


class TestOwnerBehaltenLesen:
    def test_should_read_keys_and_meta_sender_list_but_not_meta_key(self, tmp_path):
        ledger = _ledger(
            tmp_path / "l.json",
            {
                BEHALTEN_ADRESSE.upper(): "Owner 2026-09-30",
                BEHALTEN_DOMAIN: "Owner 2026-09-30",
                "owner_korrektur_2026_09_14": {
                    "absender": ["kurs@lehre.example.org", "kein eintrag"],
                    "grund": "Owner-Korrektur",
                },
            },
        )
        assert ls.owner_behalten(ledger) == [
            BEHALTEN_ADRESSE,
            BEHALTEN_DOMAIN,
            "kurs@lehre.example.org",
        ]

    def test_should_read_nothing_without_ledger(self, tmp_path):
        assert ls.owner_behalten(tmp_path / "fehlt.json") == []


class TestKollision:
    @pytest.mark.parametrize(
        "eintrag, erwartet",
        [
            (BEHALTEN_ADRESSE, BEHALTEN_ADRESSE),  # Adressregel, exakt
            ("letters.example.com", BEHALTEN_ADRESSE),  # Domain über Adresse
            ("example.com", BEHALTEN_ADRESSE),  # Eltern-Domain über Adresse
            ("x@news.wissen.example.org", BEHALTEN_DOMAIN),  # Adresse unter Domain
            ("news.wissen.example.org", BEHALTEN_DOMAIN),  # Subdomain
            ("example.org", BEHALTEN_DOMAIN),  # Eltern-Domain
        ],
    )
    def test_should_detect_collision(self, eintrag, erwartet):
        behalten = [BEHALTEN_ADRESSE, BEHALTEN_DOMAIN]
        assert ls.behalten_kollision(eintrag, behalten) == erwartet

    @pytest.mark.parametrize(
        "eintrag", [WERBUNG, "shop.example.com", "notwissen.example.org"]
    )
    def test_should_pass_unrelated_entry(self, eintrag):
        assert (
            ls.behalten_kollision(eintrag, [BEHALTEN_ADRESSE, BEHALTEN_DOMAIN]) is None
        )


class TestFiltereVerschiebung:
    HITS = [
        ("m1", "2026-09-29", BEHALTEN_ADRESSE, "Neue Ausgabe"),
        ("m2", "2026-09-29", WERBUNG, "Sale"),
    ]

    def test_should_hold_kept_address_under_learned_domain(self, tmp_path):
        """Positivkontrolle: der Owner-Zug auf die Domain hebt „behalten" nicht auf."""
        frei, gehalten = ls.filtere_verschiebung(
            "Zur Loeschung", self.HITS, eigene=set(), abfrage=_kein_index,
            gelernt=["letters.example.com"], behalten=[BEHALTEN_ADRESSE],
        )  # fmt: skip
        assert [h[0] for h in frei] == ["m2"]
        assert [(h[0], b.klasse) for h, b in gehalten] == [("m1", "owner_behalten")]

    def test_should_read_kept_entries_from_ledger_by_default(
        self, monkeypatch, tmp_path
    ):
        ledger = _ledger(tmp_path / "l.json", {BEHALTEN_ADRESSE: "Owner"})
        monkeypatch.setattr(ls, "LEDGER", ledger)
        frei, gehalten = ls.filtere_verschiebung(
            "Zur Loeschung", self.HITS, eigene=set(), abfrage=_kein_index
        )
        assert [h[0] for h in frei] == ["m2"]
        assert gehalten[0][1].klasse == "owner_behalten"

    @pytest.mark.parametrize(
        "ziel", ["INBOX.Zur Loeschung", "INBOX/Zur Löschung", "zur_loeschung"]
    )
    def test_should_hold_kept_address_in_imap_spelling(self, ziel):
        """platform#3644: der Behalten-Schutz greift in jeder Schreibweise des Ordners."""
        frei, gehalten = ls.filtere_verschiebung(
            ziel, self.HITS, eigene=set(), abfrage=_kein_index,
            gelernt=["letters.example.com"], behalten=[BEHALTEN_ADRESSE],
        )  # fmt: skip
        assert [h[0] for h in frei] == ["m2"]
        assert [(h[0], b.klasse) for h, b in gehalten] == [("m1", "owner_behalten")]

    def test_should_not_hold_outside_deletion_folder(self):
        frei, _ = ls.filtere_verschiebung(
            "Archiv/2026", self.HITS, eigene=set(), behalten=[BEHALTEN_ADRESSE]
        )
        assert frei == self.HITS


class _Postfach:
    """Ein Konto mit den Lernordnern; zeichnet jede Verschiebung auf."""

    def __init__(self, lernen_domain):
        self.inhalt = {
            "inbox": [],
            "Zur Löschung": [],
            "Lernen Absender loeschen": [],
            "Lernen Domain loeschen": list(lernen_domain),
        }
        self.bewegungen = []

    def ordner(self):
        return list(self.inhalt)

    def liste(self, pfad):
        return list(self.inhalt.get(pfad, []))

    def verschiebe(self, quelle, ziel, kennungen):
        self.bewegungen.append((quelle, ziel, list(kennungen)))
        return len(kennungen)

    def schliessen(self):
        pass


class TestVerdrahtung:
    """platform#3644: beide Verschiebe-Werkzeuge lesen „behalten" aus dem Ledger."""

    HITS = TestFiltereVerschiebung.HITS

    @pytest.fixture
    def ledger(self, monkeypatch, tmp_path):
        pfad = _ledger(
            tmp_path / "l.json", {BEHALTEN_ADRESSE: "Owner"}, ["letters.example.com"]
        )
        monkeypatch.setattr(ls, "LEDGER", pfad)
        return pfad

    def test_should_not_move_kept_sender_via_imap(self, monkeypatch, ledger):
        om = _load("organize_mail")
        monkeypatch.setattr(om, "loeschschutz", ls)
        monkeypatch.setattr(
            om, "list_folders", lambda _i: ["INBOX", "INBOX.Zur Loeschung"]
        )
        monkeypatch.setattr(om, "_matches", lambda *a, **k: list(self.HITS))
        monkeypatch.setattr(
            om, "anhang_namen", lambda _i, _s, hits: {h[0]: [] for h in hits}
        )
        bewegt = []
        monkeypatch.setattr(om, "_move", lambda _i, _s, _t, uids: bewegt.extend(uids))

        om.cmd_move(object(), "INBOX", "INBOX.Zur Loeschung", "", None, True)

        assert bewegt == ["m2"]

    def test_should_not_move_kept_sender_via_graph(self, monkeypatch, ledger):
        gm = _load("graph_mail")
        monkeypatch.setattr(gm, "loeschschutz", ls)
        monkeypatch.setattr(gm, "_find_messages", lambda *a, **k: list(self.HITS))
        monkeypatch.setattr(gm, "ensure_path", lambda *a, **k: "zielid")
        monkeypatch.setattr(gm, "_basis", lambda: "https://graph.example")
        bewegt = []

        def fake_http(method, url, **k):
            if method == "GET":
                return gm._Resp(200, '{"value": []}')
            bewegt.append(url.split("/messages/")[1].split("/")[0])
            return gm._Resp(201, "{}")

        monkeypatch.setattr(gm, "_http", fake_http)

        gm.cmd_move("tok", "example", "Zur Loeschung", "inbox", True)

        assert bewegt == ["m2"]


class TestLernordner:
    def _lo(self, monkeypatch):
        lo = _load("lernordner")
        # Andere Testdateien laden loeschschutz neu — fest auf das isolierte Modul.
        monkeypatch.setattr(lo, "loeschschutz", ls)
        return lo

    def test_should_refuse_domain_rule_over_kept_address(self, monkeypatch):
        lo = self._lo(monkeypatch)
        eintrag, grund = lo.eintrag_fuer(
            "domain", f"Promo <{WERBUNG}>", set(), [BEHALTEN_ADRESSE]
        )
        assert eintrag is None and grund == f"Owner behält {BEHALTEN_ADRESSE}"

    def test_should_return_kept_sender_to_inbox_and_learn_nothing(
        self, monkeypatch, tmp_path
    ):
        lo = self._lo(monkeypatch)
        ledger = _ledger(tmp_path / "l.json", {BEHALTEN_ADRESSE: "Owner"})
        pf = _Postfach([("l1", "2026-09-28", WERBUNG, "Sale")])
        lo.lauf(["iil"], apply=True, oeffnen=lambda _k: pf, ledger_pfad=ledger)
        regeln = json.loads(ledger.read_text())["rausch_regeln"]
        assert regeln["nach_ordner_zur_loeschung"] == []
        assert pf.bewegungen == [("Lernen Domain loeschen", "inbox", ["l1"])]

    def test_should_learn_unrelated_sender_in_same_run_as_kept_one(
        self, monkeypatch, tmp_path
    ):
        """platform#3644: Gegenstück — der Behalten-Treffer blockiert den Rest nicht."""
        lo = self._lo(monkeypatch)
        ledger = _ledger(tmp_path / "l.json", {BEHALTEN_ADRESSE: "Owner"})
        pf = _Postfach(
            [
                ("l1", "2026-09-28", WERBUNG, "Sale"),
                ("l2", "2026-09-28", FREMD, "Angebot"),
            ]
        )
        lo.lauf(["iil"], apply=True, oeffnen=lambda _k: pf, ledger_pfad=ledger)
        regeln = json.loads(ledger.read_text())["rausch_regeln"]
        assert regeln["nach_ordner_zur_loeschung"] == ["shop.example.net"]
        assert sorted(pf.bewegungen) == [
            ("Lernen Domain loeschen", "Zur Löschung", ["l2"]),
            ("Lernen Domain loeschen", "inbox", ["l1"]),
        ]


class TestRauschKandidaten:
    def test_should_never_propose_kept_sender(self, monkeypatch):
        rk = _load("rausch_kandidaten")
        monkeypatch.setattr(rk, "loeschschutz", ls)
        kandidaten = [
            rk.Kandidat(absender=a, treffer=3, betreffs=["Neu", "Sale", "Tipps"])
            for a in (BEHALTEN_ADRESSE, WERBUNG)
        ]
        frei, raus = rk.schutz_filtern(
            kandidaten,
            eigene=set(),
            gesendet=set(),
            behalten=[BEHALTEN_DOMAIN, BEHALTEN_ADRESSE],
        )
        assert [k.absender for k in frei] == [WERBUNG]
        assert [(r.absender, r.grund) for r in raus] == [
            (BEHALTEN_ADRESSE, "schutz:owner_behalten")
        ]
