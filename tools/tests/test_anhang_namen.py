"""Tests: Anhangnamen direkt aus dem Postfach vor dem Löschordner (platform#3627).

Kein Postfach: Graph-HTTP und IMAP-Verbindung sind Fakes. Alle Adressen und
Dateinamen sind erfunden (example.org/.com) — dieses Repo ist öffentlich.
"""

import importlib.util
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

WERBUNG = "news@shop.example.com"

# Neutraler Betreff, kein Beleg-Absender: nur der Anhangname verrät den Beleg.
HITS = [
    ("m1", "2026-09-01", WERBUNG, "Ihre Unterlagen"),
    ("m2", "2026-09-02", WERBUNG, "Herbst-Sale"),
]


@pytest.fixture(autouse=True)
def isoliert(monkeypatch, tmp_path):
    monkeypatch.setattr(ls, "LEDGER", tmp_path / "kein-ledger.json")
    monkeypatch.setattr(ls, "ROLLEN_REGISTRY", tmp_path / "fehlt.json")
    monkeypatch.setattr(
        ls,
        "index_batch",
        lambda anfragen: [{"index": i, "treffer": []} for i, _ in enumerate(anfragen)],
    )


class TestAnhaengePruefen:
    def test_should_hold_mail_with_invoice_attachment_despite_neutral_subject(self):
        """Positivkontrolle: neutraler Betreff + Rechnung_4711.pdf bleibt liegen."""
        frei, gehalten = ls.filtere_verschiebung(
            "Zur Loeschung",
            HITS,
            eigene=set(),
            anhang_namen=lambda h: {"m1": ["Rechnung_4711.pdf"], "m2": []},
        )
        assert [h[0] for h in frei] == ["m2"]
        assert [(h[0], b.klasse) for h, b in gehalten] == [("m1", "beleg")]

    def test_should_fail_closed_when_attachments_unreadable(self):
        frei, gehalten = ls.filtere_verschiebung(
            "Zur Loeschung",
            HITS,
            eigene=set(),
            anhang_namen=lambda h: {"m1": None, "m2": ["flyer.jpg"]},
        )
        assert [h[0] for h in frei] == ["m2"]
        assert gehalten[0][1].klasse == "anhang_unlesbar"

    def test_should_hold_mail_missing_from_reader_answer(self):
        frei, gehalten = ls.filtere_verschiebung(
            "Zur Loeschung", HITS, eigene=set(), anhang_namen=lambda h: {"m2": []}
        )
        assert [h[0] for h in frei] == ["m2"]
        assert [h[0] for h, _ in gehalten] == ["m1"]

    def test_should_match_imap_uid_bytes_against_string_keys(self):
        hits = [(b"17", "2026-09-01", WERBUNG, "Hallo")]
        frei, gehalten = ls.filtere_verschiebung(
            "INBOX.Zur Loeschung",
            hits,
            eigene=set(),
            anhang_namen=lambda h: {"17": ["Quittung.pdf"]},
        )
        assert frei == [] and gehalten[0][1].klasse == "beleg"

    def test_should_not_read_attachments_outside_deletion_folder(self):
        def nie(_):
            raise AssertionError("ohne Löschordner keine Anhang-Abfrage")

        frei, _ = ls.filtere_verschiebung(
            "Archiv/2026", HITS, eigene=set(), anhang_namen=nie
        )
        assert frei == HITS


class TestImapBodystructure:
    om = _load("organize_mail")

    def test_should_read_quoted_filename(self):
        blob = (
            b'17 (UID 17 BODYSTRUCTURE (("TEXT" "PLAIN" NIL NIL NIL "7BIT" 10 1)'
            b'("APPLICATION" "PDF" ("NAME" "Rechnung_4711.pdf") NIL NIL "BASE64" 99'
            b' NIL ("ATTACHMENT" ("FILENAME" "Rechnung_4711.pdf"))) "MIXED"))'
        )
        assert self.om.namen_aus_bodystructure(blob) == ["Rechnung_4711.pdf"]

    def test_should_decode_rfc2231_filename(self):
        blob = b'("FILENAME*" "utf-8\'\'Geb%C3%BChren%20Rechnung.pdf")'
        assert self.om.namen_aus_bodystructure(blob) == ["Gebühren Rechnung.pdf"]

    def test_should_decode_rfc2047_name(self):
        blob = b'("NAME" "=?UTF-8?B?UXVpdHR1bmcucGRm?=")'
        assert self.om.namen_aus_bodystructure(blob) == ["Quittung.pdf"]

    def test_should_read_literal_name(self):
        blob = b'("NAME" {12}\r\nbeleg 1.pdf!)'
        assert self.om.namen_aus_bodystructure(blob) == ["beleg 1.pdf!"]

    def test_should_return_nothing_without_attachments(self):
        blob = b'1 (UID 1 BODYSTRUCTURE ("TEXT" "PLAIN" ("CHARSET" "UTF-8") NIL)'
        assert self.om.namen_aus_bodystructure(blob) == []

    def test_should_join_literal_parts_and_mark_failures_none(self):
        class FakeImap:
            def select(self, *a, **k):
                return "OK", [b"2"]

            def uid(self, cmd, uid, what):
                if uid == "5":
                    return "NO", [None]
                return "OK", [
                    (b'4 (UID 4 BODYSTRUCTURE ("NAME" {11}', b"Invoice.pdf"),
                    b"))",
                ]

        namen = self.om.anhang_namen(
            FakeImap(), "INBOX", [(b"4", "", WERBUNG, ""), (b"5", "", WERBUNG, "")]
        )
        assert namen == {"4": ["Invoice.pdf"], "5": None}


class TestGraphAnhaenge:
    gm = _load("graph_mail")

    def test_should_read_names_and_mark_errors_none(self, monkeypatch):
        gm = self.gm
        monkeypatch.setattr(gm, "_basis", lambda: "https://graph.example")

        def fake_http(method, url, **k):
            assert method == "GET" and url.endswith("attachments?$select=name")
            if "/messages/m1/" in url:
                return gm._Resp(200, '{"value": [{"name": "Rechnung_4711.pdf"}]}')
            return gm._Resp(404, "")

        monkeypatch.setattr(gm, "_http", fake_http)
        assert gm.anhang_namen("tok", HITS) == {
            "m1": ["Rechnung_4711.pdf"],
            "m2": None,
        }

    def test_should_keep_invoice_attachment_out_of_deletion_folder(self, monkeypatch):
        gm = self.gm
        monkeypatch.setattr(gm, "loeschschutz", ls)
        monkeypatch.setattr(gm, "_find_messages", lambda *a, **k: list(HITS))
        monkeypatch.setattr(gm, "ensure_path", lambda *a, **k: "zielid")
        monkeypatch.setattr(gm, "_basis", lambda: "https://graph.example")
        bewegt = []

        def fake_http(method, url, **k):
            mid = url.split("/messages/")[1].split("/")[0]
            if method == "GET":
                name = "Rechnung_4711.pdf" if mid == "m1" else "flyer.jpg"
                return gm._Resp(200, '{"value": [{"name": "%s"}]}' % name)
            bewegt.append(mid)
            return gm._Resp(201, "{}")

        monkeypatch.setattr(gm, "_http", fake_http)
        gm.cmd_move("tok", "example", "Zur Loeschung", "inbox", True)
        assert bewegt == ["m2"]


class TestLernordnerVerdrahtung:
    def test_should_hold_invoice_attachment_in_learned_move(self):
        lo = _load("lernordner")

        class Postfach:
            bewegt = []

            def anhang_namen(self, quelle, hits):
                assert quelle == "Posteingang"
                return {"m1": ["Rechnung_4711.pdf"], "m2": []}

            def verschiebe(self, quelle, ziel, kennungen):
                self.bewegt.extend(kennungen)
                return len(kennungen)

        pf = Postfach()
        bewegt, gehalten = lo.in_loeschordner(
            "iil", pf, "Posteingang", HITS, [WERBUNG], apply=True
        )
        assert pf.bewegt == ["m2"] and bewegt == 1
        assert [h[0] for h in gehalten] == ["m1"]
