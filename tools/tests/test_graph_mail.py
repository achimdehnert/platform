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
    page = {"value": [
        {"id": "m1", "subject": "Re: Owner-Block Digest",
         "receivedDateTime": "2026-07-16T08:00:00Z",
         "from": {"emailAddress": {"address": "pg@dehnert.team", "name": "Achim"}}},
        {"id": "m2", "subject": "Newsletter KW29",
         "receivedDateTime": "2026-07-16T07:00:00Z",
         "from": {"emailAddress": {"address": "noreply@shop.example", "name": "Shop"}}},
        {"id": "m3", "subject": "Owner-Block Nachtrag",
         "receivedDateTime": "2026-07-15T09:00:00Z",
         "from": {"emailAddress": {"address": "achim.dehnert@iil.gmbh", "name": ""}}},
    ]}
    monkeypatch.setattr(mod, "_http", lambda *a, **k: mod._Resp(200, _json.dumps(page)))

    hits = mod._match_messages("tok", from_sub="dehnert.team", subject_sub="owner-block",
                               days=7, source_path="inbox")
    assert [m["id"] for m in hits] == ["m1"]

    # Name-Match zählt wie Adress-Match; ohne subject-Filter beide dehnert.team-Treffer
    hits = mod._match_messages("tok", from_sub="achim", days=7, source_path="inbox")
    assert [m["id"] for m in hits] == ["m1", "m3"]


def test_should_strip_html_to_readable_text():
    mod = _load()
    html = ("<html><style>p{color:red}</style><body><p>Zeile&nbsp;1</p>"
            "<div>Zeile 2 &amp; mehr</div><script>alert(1)</script></body></html>")
    text = mod._strip_html(html)
    assert "Zeile\xa01" in text and "Zeile 2 & mehr" in text
    assert "alert" not in text and "color" not in text
