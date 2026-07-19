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
