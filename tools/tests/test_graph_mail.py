"""Tests für tools/mail_agent/graph_mail.py — netzfreie Teile:
stdlib-only-Import (kein requests), _http-Body-Aufbau, Config-Parsing.
Graph-Aufrufe (login/move/draft/folders) bleiben Dogfood/Integration.
"""

import importlib.util
import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "graph_mail.py"


def _load(monkeypatch=None):
    spec = importlib.util.spec_from_file_location("graph_mail", _SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_should_import_without_requests():
    # Repo-Ethos: Tools stdlib-only. Import darf 'requests' nicht brauchen.
    saved = sys.modules.get("requests")
    sys.modules["requests"] = None
    try:
        mod = _load()
        assert mod.SCOPES.startswith("Mail.ReadWrite")
    finally:
        if saved is not None:
            sys.modules["requests"] = saved
        else:
            sys.modules.pop("requests", None)


def test_should_build_json_and_form_bodies(monkeypatch):
    mod = _load()
    captured = {}

    class _FakeConn:
        status = 200

        def read(self):
            return b'{"ok": true}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=30):
        captured["method"] = req.method
        captured["ctype"] = req.headers.get("Content-type")
        captured["data"] = req.data
        return _FakeConn()

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)

    r = mod._http("POST", "https://x", json_body={"a": 1})
    assert r.json() == {"ok": True}
    assert captured["ctype"] == "application/json"
    assert b'"a": 1' in captured["data"]

    mod._http("POST", "https://x", data={"grant": "y"})
    assert captured["ctype"] == "application/x-www-form-urlencoded"
    assert captured["data"] == b"grant=y"


def test_should_parse_env_ignoring_comments_and_quotes(tmp_path):
    mod = _load()
    f = tmp_path / "c.env"
    f.write_text("# k\nGRAPH_ACCOUNTS='a@b.c,d@e.f'\nGRAPH_TENANT=organizations\n")
    v = mod.parse_env(f)
    assert v["GRAPH_ACCOUNTS"] == "a@b.c,d@e.f"
    assert v["GRAPH_TENANT"] == "organizations"


def test_should_filter_find_hits_by_from_and_subject(monkeypatch):
    import json as _json

    mod = _load()
    page = {
        "value": [
            {
                "id": "m1",
                "subject": "Re: Owner-Block Digest",
                "receivedDateTime": "2026-07-16T08:00:00Z",
                "from": {
                    "emailAddress": {"address": "pg@dehnert.team", "name": "Achim"}
                },
            },
            {
                "id": "m2",
                "subject": "Newsletter KW29",
                "receivedDateTime": "2026-07-16T07:00:00Z",
                "from": {
                    "emailAddress": {"address": "noreply@shop.example", "name": "Shop"}
                },
            },
            {
                "id": "m3",
                "subject": "Owner-Block Nachtrag",
                "receivedDateTime": "2026-07-15T09:00:00Z",
                "from": {
                    "emailAddress": {"address": "achim.dehnert@iil.gmbh", "name": ""}
                },
            },
        ]
    }
    monkeypatch.setattr(mod, "_http", lambda *a, **k: mod._Resp(200, _json.dumps(page)))

    hits = mod._match_messages(
        "tok",
        from_sub="dehnert.team",
        subject_sub="owner-block",
        days=7,
        source_path="inbox",
    )
    assert [m["id"] for m in hits] == ["m1"]

    # Name-Match zählt wie Adress-Match; ohne subject-Filter beide dehnert.team-Treffer
    hits = mod._match_messages("tok", from_sub="achim", days=7, source_path="inbox")
    assert [m["id"] for m in hits] == ["m1", "m3"]


# --- #1281: --move braucht denselben UND-Filter wie --find/--flag --------------
# Realfall IIL-Postfach: microsoft-noreply@microsoft.com liefert Rechnungen UND
# Abo-/Lizenzmails unter EINER Adresse — eine reine Absender-Regel wirft beides
# in denselben Ordner.


def _ms_page():
    def _m(mid, subject, addr):
        return {
            "id": mid,
            "subject": subject,
            "receivedDateTime": "2026-07-20T08:00:00Z",
            "from": {"emailAddress": {"address": addr, "name": "Microsoft"}},
        }

    return {
        "value": [
            _m(
                "r1",
                "Ihre Microsoft-Rechnung G012 ist bereit",
                "microsoft-noreply@microsoft.com",
            ),
            _m(
                "a1",
                "Ihr Abonnement wurde verlängert",
                "microsoft-noreply@microsoft.com",
            ),
            _m(
                "r2",
                "Ihre Microsoft-Rechnung G013 ist bereit",
                "microsoft-noreply@microsoft.com",
            ),
            _m("x1", "Rechnung", "billing@other.example"),
        ]
    }


def test_should_move_only_messages_matching_from_and_subject(monkeypatch):
    import json as _json

    mod = _load()
    monkeypatch.setattr(
        mod, "_http", lambda *a, **k: mod._Resp(200, _json.dumps(_ms_page()))
    )
    monkeypatch.setattr(mod, "find_folder", lambda *a, **k: "srcid")

    hits = mod._find_messages(
        "tok", "microsoft-noreply", "inbox", subject_sub="Rechnung"
    )
    assert [h[0] for h in hits] == ["r1", "r2"]  # Abo-Mail bleibt liegen


def test_should_keep_move_behaviour_unchanged_without_subject(monkeypatch):
    import json as _json

    mod = _load()
    monkeypatch.setattr(
        mod, "_http", lambda *a, **k: mod._Resp(200, _json.dumps(_ms_page()))
    )
    monkeypatch.setattr(mod, "find_folder", lambda *a, **k: "srcid")

    hits = mod._find_messages("tok", "microsoft-noreply", "inbox")
    assert [h[0] for h in hits] == ["r1", "a1", "r2"]


def test_should_build_file_attachment_payload(tmp_path):
    import base64 as _b64

    mod = _load()
    f = tmp_path / "Anhang.pdf"
    f.write_bytes(b"%PDF-1.4 fake bytes")
    payload = mod._file_attachment_payload(str(f))
    assert payload["@odata.type"] == "#microsoft.graph.fileAttachment"
    assert payload["name"] == "Anhang.pdf"
    assert payload["contentType"] == "application/pdf"
    assert _b64.b64decode(payload["contentBytes"]) == b"%PDF-1.4 fake bytes"


def test_should_attach_files_posts_to_attachments_endpoint(monkeypatch):
    mod = _load()
    calls = []
    monkeypatch.setattr(
        mod,
        "_file_attachment_payload",
        lambda p: {"name": "x.pdf", "contentType": "application/pdf"},
    )

    def fake_http(method, url, **k):
        calls.append((method, url))
        return mod._Resp(201, "{}")

    monkeypatch.setattr(mod, "_http", fake_http)
    mod._attach_files("tok", "MSG123", ["/tmp/x.pdf"])
    assert calls == [("POST", f"{mod.GRAPH}/me/messages/MSG123/attachments")]


def test_should_strip_html_to_readable_text():
    mod = _load()
    html = (
        "<html><style>p{color:red}</style><body><p>Zeile&nbsp;1</p>"
        "<div>Zeile 2 &amp; mehr</div><script>alert(1)</script></body></html>"
    )
    text = mod._strip_html(html)
    assert "Zeile\xa01" in text and "Zeile 2 & mehr" in text
    assert "alert" not in text and "color" not in text


# --- Anhänge herunterladen (--save-attachments) ------------------------------
# Netzfrei: nur die reinen Teile (Namens-Entschärfung, base64-Dekodierung).
# download_attachments selbst bleibt Dogfood/Integration wie die übrigen Graph-Calls.


def test_should_strip_directory_traversal_from_attachment_name():
    mod = _load()
    assert mod._safe_filename("../../.ssh/authorized_keys") == "authorized_keys"
    assert mod._safe_filename("C:\\temp\\rechnung.pdf") == "rechnung.pdf"


def test_should_fall_back_when_attachment_name_is_empty_or_dots():
    mod = _load()
    assert mod._safe_filename("") == "anhang.bin"
    assert mod._safe_filename("   ") == "anhang.bin"
    assert mod._safe_filename("..") == "anhang.bin"


def test_should_decode_file_attachment_to_name_and_bytes():
    mod = _load()
    att = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": "Zahlungsaufforderung.pdf",
        "contentBytes": "SGFsbG8=",  # "Hallo"
    }
    assert mod._decode_attachment(att) == ("Zahlungsaufforderung.pdf", b"Hallo")


def test_should_skip_non_file_attachments():
    mod = _load()
    assert (
        mod._decode_attachment({"@odata.type": "#microsoft.graph.itemAttachment"})
        is None
    )
    assert (
        mod._decode_attachment(
            {
                "@odata.type": "#microsoft.graph.referenceAttachment",
                "name": "cloud.docx",
            }
        )
        is None
    )


def test_should_skip_file_attachment_without_content():
    mod = _load()
    att = {"@odata.type": "#microsoft.graph.fileAttachment", "name": "leer.pdf"}
    assert mod._decode_attachment(att) is None


# --- cmd_mark: Flag / Wichtigkeit (PATCH-Body + Auswahl-Gate) ----------------


def _mark_capture(monkeypatch, mod, hits):
    """cmd_mark verdrahten: _match_messages liefert `hits`, _http fängt PATCHes."""
    calls = []
    monkeypatch.setattr(mod, "_match_messages", lambda *a, **k: hits)

    def fake_http(method, url, *, headers=None, json_body=None, **kw):
        calls.append({"method": method, "url": url, "json": json_body})
        return mod._Resp(200, '{"ok": true}')

    monkeypatch.setattr(mod, "_http", fake_http)
    return calls


def test_should_patch_followup_flag_on_matched_messages(monkeypatch):
    mod = _load()
    hits = [{"id": "AAA", "from": {"emailAddress": {"address": "a@x.de"}}}]
    calls = _mark_capture(monkeypatch, mod, hits)
    mod.cmd_mark(
        "tok",
        from_sub="a@x",
        subject_sub="",
        source_path="inbox",
        days=30,
        yes=True,
        patch={"flag": {"flagStatus": "flagged"}},
        label="Zur Nachverfolgung markieren",
    )
    assert len(calls) == 1
    assert calls[0]["method"] == "PATCH"
    assert calls[0]["url"].endswith("/me/messages/AAA")
    assert calls[0]["json"] == {"flag": {"flagStatus": "flagged"}}


def test_should_patch_importance_on_each_matched_message(monkeypatch):
    mod = _load()
    hits = [
        {"id": "M1", "from": {"emailAddress": {"address": "a@x.de"}}},
        {"id": "M2", "from": {"emailAddress": {"address": "b@x.de"}}},
    ]
    calls = _mark_capture(monkeypatch, mod, hits)
    mod.cmd_mark(
        "tok",
        from_sub="",
        subject_sub="Rechnung",
        source_path="inbox",
        days=30,
        yes=True,
        patch={"importance": "high"},
        label="Wichtigkeit=high setzen",
    )
    assert [c["json"] for c in calls] == [
        {"importance": "high"},
        {"importance": "high"},
    ]


def test_should_not_patch_when_no_matches(monkeypatch):
    mod = _load()
    calls = _mark_capture(monkeypatch, mod, [])
    mod.cmd_mark(
        "tok",
        from_sub="niemand",
        subject_sub="",
        source_path="inbox",
        days=30,
        yes=True,
        patch={"flag": {"flagStatus": "flagged"}},
        label="Zur Nachverfolgung markieren",
    )
    assert calls == []


# --- #1480: Ordner filterfrei aufzählen + stille Verwerfung melden -------------
# Realfall 2026-07-27: `--from "@"` als Platzhalter für "alles" verwarf auf
# "Gesendete Elemente" 21 von 31 Mails — Exchange liefert den Absender dort teils
# als X.500-DN (/o=ExchangeLabs/…) OHNE @. Die so entstandene Teilmenge wurde für
# eine Vollerhebung gehalten und erzeugte einen falschen "nie gesendet"-Befund.


def _sent_page():
    """Gesendete Elemente: gemischt SMTP-Adresse und Exchange-X.500-DN."""
    x500 = (
        "/O=EXCHANGELABS/OU=EXCHANGE ADMINISTRATIVE GROUP (FYDIBOHF23SPDLT)"
        "/CN=RECIPIENTS/CN=DF982E46-ACHIM.DEHNE"
    )
    return {
        "value": [
            {
                "id": "s1",
                "subject": "Bitte um Authentifizierung",
                "receivedDateTime": "2026-07-23T08:16:00Z",
                "from": {"emailAddress": {"address": x500, "name": "Achim Dehnert"}},
            },
            {
                "id": "s2",
                "subject": "RE: Angebot",
                "receivedDateTime": "2026-07-23T08:56:00Z",
                "from": {
                    "emailAddress": {"address": "achim.dehnert@iil.gmbh", "name": "AD"}
                },
            },
            {
                "id": "s3",
                "subject": "Zugesagt: PG",
                "receivedDateTime": "2026-07-24T10:40:00Z",
                "from": {"emailAddress": {"address": x500, "name": "Achim Dehnert"}},
            },
        ]
    }


def _patch_page(monkeypatch, mod, page):
    import json as _json

    monkeypatch.setattr(mod, "_http", lambda *a, **k: mod._Resp(200, _json.dumps(page)))
    monkeypatch.setattr(mod, "find_folder", lambda *a, **k: "sentid")


def test_should_enumerate_folder_completely_without_any_filter(monkeypatch):
    mod = _load()
    _patch_page(monkeypatch, mod, _sent_page())
    hits = mod._match_messages(
        "tok", from_sub="", subject_sub="", days=30, source_path="Gesendete Elemente"
    )
    assert [m["id"] for m in hits] == ["s1", "s2", "s3"]


def test_should_warn_when_sender_filter_drops_non_smtp_senders(monkeypatch, capsys):
    mod = _load()
    _patch_page(monkeypatch, mod, _sent_page())
    hits = mod._match_messages(
        "tok", from_sub="@", subject_sub="", days=30, source_path="Gesendete Elemente"
    )
    # der Platzhalter trifft nur die eine echte SMTP-Adresse
    assert [m["id"] for m in hits] == ["s2"]
    warn = capsys.readouterr().err
    assert "2 von 3" in warn
    assert "--all" in warn


def test_should_not_warn_when_no_message_was_dropped(monkeypatch, capsys):
    mod = _load()
    _patch_page(monkeypatch, mod, _sent_page())
    mod._match_messages(
        "tok", from_sub="", subject_sub="", days=30, source_path="Gesendete Elemente"
    )
    assert capsys.readouterr().err == ""


# --- #1480 Teil 2: --draft kann Cc -------------------------------------------


def test_should_put_cc_recipients_into_new_draft(monkeypatch):
    mod = _load()
    erfasst = {}

    def fake_http(method, url, **k):
        if method == "POST" and url.endswith("/me/messages"):
            erfasst["body"] = k.get("json_body")
            return mod._Resp(201, '{"id": "neu"}')
        return mod._Resp(200, "{}")

    monkeypatch.setattr(mod, "_http", fake_http)
    mod.cmd_draft("tok", "a@b.c", "Betreff", "Text", None, cc=["x@y.z", "q@r.s"])
    assert [r["emailAddress"]["address"] for r in erfasst["body"]["toRecipients"]] == [
        "a@b.c"
    ]
    assert [r["emailAddress"]["address"] for r in erfasst["body"]["ccRecipients"]] == [
        "x@y.z",
        "q@r.s",
    ]


def test_should_omit_cc_key_when_no_cc_given(monkeypatch):
    mod = _load()
    erfasst = {}

    def fake_http(method, url, **k):
        if method == "POST" and url.endswith("/me/messages"):
            erfasst["body"] = k.get("json_body")
            return mod._Resp(201, '{"id": "neu"}')
        return mod._Resp(200, "{}")

    monkeypatch.setattr(mod, "_http", fake_http)
    mod.cmd_draft("tok", "a@b.c", "Betreff", "Text", None)
    assert "ccRecipients" not in erfasst["body"]


# --- ADR-286 §4.9 Stufe 1: Vorgangs-Zuordnung über Kategorien -----------------
# Kernpunkt: ADDITIV. Eine Nachricht kann zu mehreren Vorgängen gehören — die
# Antwort in Thread A beantwortet zugleich einen Punkt aus Thread B. Wer die
# Kategorienliste ersetzt statt sie zu ergänzen, baut die Ordner-Beschränkung
# nach, deren Überwindung der ganze Zweck war.


def test_should_add_category_without_dropping_existing_ones():
    mod = _load()
    neu = mod.kategorie_setzen(["Postsortierung"], "OZG-Cloud")
    assert neu == ["Postsortierung", "OZG-Cloud"]


def test_should_be_idempotent_when_category_already_present():
    mod = _load()
    assert mod.kategorie_setzen(["OZG-Cloud"], "OZG-Cloud") == ["OZG-Cloud"]
    # auch bei abweichender Schreibweise — sonst entstehen Dubletten-Vorgänge
    assert mod.kategorie_setzen(["OZG-Cloud"], "ozg-cloud") == ["OZG-Cloud"]


def test_should_remove_only_the_named_category():
    mod = _load()
    rest = mod.kategorie_setzen(
        ["Postsortierung", "OZG-Cloud", "Pentest"], "OZG-Cloud", entfernen=True
    )
    assert rest == ["Postsortierung", "Pentest"]


def test_should_start_from_empty_and_tolerate_missing_field():
    mod = _load()
    assert mod.kategorie_setzen([], "Neuer Vorgang") == ["Neuer Vorgang"]
    assert mod._kategorien({}) == []
    assert mod._kategorien({"categories": None}) == []
    assert mod._kategorien({"categories": ["A", "", "B"]}) == ["A", "B"]


def test_should_filter_messages_by_category(monkeypatch):
    import json as _json

    mod = _load()
    page = {
        "value": [
            {
                "id": "a",
                "subject": "RE: Postsortierung",
                "receivedDateTime": "2026-07-24T15:26:00Z",
                "from": {
                    "emailAddress": {"address": "partner@example.com", "name": ""}
                },
                "categories": ["Postsortierung", "OZG-Cloud"],
            },
            {
                "id": "b",
                "subject": "Angebot",
                "receivedDateTime": "2026-07-24T10:00:00Z",
                "from": {
                    "emailAddress": {"address": "partner@example.com", "name": ""}
                },
                "categories": ["Postsortierung"],
            },
            {
                "id": "c",
                "subject": "Ohne Zuordnung",
                "receivedDateTime": "2026-07-24T09:00:00Z",
                "from": {"emailAddress": {"address": "x@example.com", "name": ""}},
            },
        ]
    }
    monkeypatch.setattr(mod, "_http", lambda *a, **k: mod._Resp(200, _json.dumps(page)))
    monkeypatch.setattr(mod, "find_folder", lambda *a, **k: "fid")

    # Prüffall B: dieselbe Nachricht wird über BEIDE Vorgänge gefunden
    assert [m["id"] for m in mod._match_messages("tok", category="OZG-Cloud")] == ["a"]
    assert [m["id"] for m in mod._match_messages("tok", category="Postsortierung")] == [
        "a",
        "b",
    ]
    # ohne Filter bleibt alles sichtbar
    assert len(mod._match_messages("tok")) == 3


# --- Genau eine Nachricht verschieben (--id) ---------------------------------
#
# Bis 2026-08-18 verlangte `--move` einen Absender-Filter. Wer eine einzelne Mail
# bewegen wollte, musste über einen Betreff-Filter gehen — der trifft auch fremde
# Mails mit demselben Wort. Der Weg zu einer einzelnen Nachricht war über
# `--trash <messageId>` längst da, für `--move` nur nicht freigelegt.


def test_should_move_exactly_the_named_message(monkeypatch):
    import json as _json

    mod = _load()
    gerufen = []

    def fake_http(method, url, **kw):
        gerufen.append((method, url))
        if method == "GET":
            return mod._Resp(
                200,
                _json.dumps(
                    {
                        "id": "m1",
                        "subject": "Vorgang",
                        "receivedDateTime": "2026-08-18T07:00:00Z",
                        "from": {"emailAddress": {"address": "a@b.de"}},
                    }
                ),
            )
        return mod._Resp(200, "{}")

    monkeypatch.setattr(mod, "_http", fake_http)
    monkeypatch.setattr(mod, "ensure_path", lambda *a, **k: "zielid")

    mod.cmd_move("tok", "", "Archiv/2026", "inbox", True, "", ["m1"])

    bewegungen = [u for m, u in gerufen if m == "POST" and u.endswith("/move")]
    assert len(bewegungen) == 1
    assert "/me/messages/m1/move" in bewegungen[0]


def test_should_not_search_by_sender_when_an_id_is_given(monkeypatch):
    """Mit --id darf kein Absender-Suchlauf stattfinden — sonst träfe er Fremdes."""
    mod = _load()
    monkeypatch.setattr(
        mod,
        "_find_messages",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("Absender-Suche trotz --id")
        ),
    )
    monkeypatch.setattr(
        mod,
        "_http",
        lambda method, url, **kw: mod._Resp(
            200,
            '{"id":"m1","subject":"x","receivedDateTime":"2026-08-18T07:00:00Z",'
            '"from":{"emailAddress":{"address":"a@b.de"}}}',
        ),
    )
    monkeypatch.setattr(mod, "ensure_path", lambda *a, **k: "zielid")
    mod.cmd_move("tok", "", "Archiv/2026", "inbox", True, "", ["m1"])


def test_should_report_an_unreadable_message_instead_of_moving_nothing(monkeypatch, capsys):
    mod = _load()
    monkeypatch.setattr(mod, "_http", lambda *a, **k: mod._Resp(404, "{}"))
    monkeypatch.setattr(mod, "ensure_path", lambda *a, **k: "zielid")
    mod.cmd_move("tok", "", "Archiv/2026", "inbox", True, "", ["fehlt"])
    aus = capsys.readouterr()
    assert "nicht lesbar" in aus.err


def test_should_reject_a_message_id_with_whitespace_instead_of_crashing(monkeypatch, capsys):
    """Eine ID aus einer Pipeline trägt gern Zeilenreste mit sich.

    Ungeprüft landete das in der URL und endete in
    `URL can't contain control characters` — ein Stacktrace statt einer Meldung.
    Gemessen am 2026-08-18 beim eigenen Testlauf.
    """
    import pytest as _pytest

    mod = _load()
    monkeypatch.setattr(mod, "ensure_path", lambda *a, **k: "zielid")
    with _pytest.raises(SystemExit):
        mod.cmd_move("tok", "", "Archiv/2026", "inbox", True, "", ["AAMk=\nzeile2"])
    assert "Keine brauchbare messageId" in capsys.readouterr().err


def test_should_still_accept_an_id_with_surrounding_spaces(monkeypatch):
    mod = _load()
    bewegt = []

    def fake_http(method, url, **kw):
        if method == "GET":
            return mod._Resp(
                200,
                '{"id":"m1","subject":"x","receivedDateTime":"2026-08-18T07:00:00Z",'
                '"from":{"emailAddress":{"address":"a@b.de"}}}',
            )
        bewegt.append(url)
        return mod._Resp(200, "{}")

    monkeypatch.setattr(mod, "_http", fake_http)
    monkeypatch.setattr(mod, "ensure_path", lambda *a, **k: "zielid")
    mod.cmd_move("tok", "", "Archiv/2026", "inbox", True, "", ["  m1  "])
    assert any("/me/messages/m1/move" in u for u in bewegt)
