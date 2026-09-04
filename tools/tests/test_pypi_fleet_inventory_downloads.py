"""Downloads-Erhebung des PyPI-Fleet-Inventars unter pypistats-Drosselung (#2591 K1).

Befund 2026-09-01: pypistats.org antwortete für 20/23 Pakete HTTP 429; das Tool
schluckte das als generischen URLError und ließ `downloads_30d` still weg — ein Regen
hätte 16 Vorwerte gelöscht und M5 (earlywarn) blind gemacht. Kontrakt jetzt:
429 wird sichtbar, Vorwert wird mit `downloads_30d_stale_from` übernommen.
"""

import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypi_fleet_inventory as inv  # noqa: E402


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://pypistats.org/x", code, "x", {}, io.BytesIO(b"")
    )


def test_should_raise_rate_limited_on_http_429(monkeypatch):
    def boom(*_a, **_k):
        raise _http_error(429)

    monkeypatch.setattr(inv.urllib.request, "urlopen", boom)
    with pytest.raises(inv.PypistatsRateLimited):
        inv.pypistats_recent("iil-aifw")


def test_should_stay_fail_soft_on_other_http_errors(monkeypatch):
    def boom(*_a, **_k):
        raise _http_error(404)

    monkeypatch.setattr(inv.urllib.request, "urlopen", boom)
    assert inv.pypistats_recent("iil-aifw") == {}


def test_should_carry_over_prior_downloads_when_rate_limited(monkeypatch):
    monkeypatch.setattr(
        inv,
        "pypistats_recent",
        lambda d: (_ for _ in ()).throw(inv.PypistatsRateLimited(d)),
    )
    limited: list[str] = []
    prior = {"downloads_30d": 393}
    out = inv.downloads_or_carryover("iil-aifw", prior, "2026-08-27T10:00:00Z", limited)
    assert out == {
        "downloads_30d": 393,
        "downloads_30d_stale_from": "2026-08-27T10:00:00Z",
    }
    assert limited == ["iil-aifw"]


def test_should_keep_oldest_stale_marker_across_repeated_throttling(monkeypatch):
    monkeypatch.setattr(
        inv,
        "pypistats_recent",
        lambda d: (_ for _ in ()).throw(inv.PypistatsRateLimited(d)),
    )
    prior = {"downloads_30d": 393, "downloads_30d_stale_from": "2026-08-27T10:00:00Z"}
    out = inv.downloads_or_carryover("iil-aifw", prior, "2026-09-01T20:00:00Z", [])
    assert out["downloads_30d_stale_from"] == "2026-08-27T10:00:00Z"


def test_should_omit_downloads_when_rate_limited_without_prior(monkeypatch):
    monkeypatch.setattr(
        inv,
        "pypistats_recent",
        lambda d: (_ for _ in ()).throw(inv.PypistatsRateLimited(d)),
    )
    limited: list[str] = []
    assert inv.downloads_or_carryover("iil-neu", {}, None, limited) == {}
    assert limited == ["iil-neu"]


def test_should_return_fresh_value_without_stale_marker_when_not_limited(monkeypatch):
    monkeypatch.setattr(inv, "pypistats_recent", lambda d: {"downloads_30d": 7})
    limited: list[str] = []
    out = inv.downloads_or_carryover(
        "iil-aifw", {"downloads_30d": 393}, "2026-08-27", limited
    )
    assert out == {"downloads_30d": 7}
    assert limited == []


def test_should_read_prior_inventory_from_fleet_file(tmp_path):
    f = tmp_path / "pypi-fleet.yaml"
    f.write_text(
        yaml.safe_dump(
            {
                "_meta": {"generated_at": "2026-08-27T10:00:00Z"},
                "packages": {"aifw": {"pypi": {"downloads_30d": 1}}, "leer": {}},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    assert inv.prior_inventory(f) == (
        "2026-08-27T10:00:00Z",
        {"aifw": {"downloads_30d": 1}, "leer": {}},
    )
    assert inv.prior_inventory(tmp_path / "fehlt.yaml") == (None, {})


def test_should_parse_last_month_from_pypistats_payload(monkeypatch):
    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    payload = json.dumps({"data": {"last_month": 42}}).encode()
    monkeypatch.setattr(inv.urllib.request, "urlopen", lambda *_a, **_k: Resp(payload))
    assert inv.pypistats_recent("iil-aifw") == {"downloads_30d": 42}
