"""Drill fuer tools/mail_agent/kev_vorfilter.py (platform#3337).

Kein Netz, kein SSH: Graph (`_http`/`_daten`) und der gx10-Transport (`_ssh`)
werden in jedem Test ersetzt. Fixtures sind synthetisch ("Beispiel GmbH",
rechnung@example.com) — dieses Repo ist oeffentlich.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "kev_vorfilter.py"
_spec = importlib.util.spec_from_file_location("kev_vorfilter", _SRC)
kv = importlib.util.module_from_spec(_spec)
sys.modules["kev_vorfilter"] = kv
_spec.loader.exec_module(kv)


# ── Zustandstext ────────────────────────────────────────────────────────────


def test_should_build_exact_state_text_format():
    text = kv.zustandstext(
        "Beispiel GmbH",
        "rechnung@example.com",
        "Ihre Rechnung 2026-09",
        True,
        "Sehr geehrte Damen  und Herren,\n\nanbei die Rechnung.",
    )
    assert text == (
        "Absender: Beispiel GmbH rechnung@example.com\n"
        "Betreff: Ihre Rechnung 2026-09\n"
        "Anhang: ja\n"
        "Text: Sehr geehrte Damen und Herren, anbei die Rechnung."
    )


def test_should_mark_no_attachment_as_nein():
    text = kv.zustandstext("Absender", "a@example.com", "Betreff", False, "Text")
    assert "Anhang: nein" in text


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _mail(mid, wert, *, betreff="Rechnung", tage_alt=1, anhang=True):
    return {
        "id": mid,
        "subject": betreff,
        "from": {
            "emailAddress": {"name": "Beispiel GmbH", "address": f"{mid}@example.com"}
        },
        "bodyPreview": "Anbei die Rechnung.",
        "hasAttachments": anhang,
        "receivedDateTime": f"2026-09-{max(1, 22 - tage_alt):02d}T08:00:00Z",
        "_wert": wert,
    }


class _FakeResp:
    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


def _patch_graph(monkeypatch, mails: list[dict]) -> None:
    """`_http`/`_daten` durch eine einzige Graph-Seite ohne @odata.nextLink ersetzen."""

    def fake_http(method, url, **kwargs):
        return _FakeResp({"value": mails})

    def fake_daten(r, kontext):
        return r.json()

    monkeypatch.setattr(kv, "_http", fake_http)
    monkeypatch.setattr(kv, "_daten", fake_daten)
    monkeypatch.setattr(kv, "_auth", lambda tok: {})
    monkeypatch.setattr(kv, "_basis", lambda: "https://graph.example/me")


def _patch_ssh_ok(monkeypatch, mails: list[dict]) -> None:
    """`_ssh` durch ein Fake ersetzen, das je Mail den in der Fixture hinterlegten
    Wert als kev-Antwort zurueckgibt — kein Netz, kein Subprocess."""
    werte_je_id = {m["id"]: m["_wert"] for m in mails}
    aufrufe: list[str] = []

    def fake_ssh(inneres: str, eingabe: str | None = None):
        aufrufe.append(inneres)
        cp = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        if inneres.startswith("python3"):
            zeilen = []
            for zeile in (eingabe or "").splitlines():
                if not zeile.strip():
                    continue
                anfrage = json.loads(zeile)
                wert = werte_je_id[anfrage["id"]]
                zeilen.append(
                    json.dumps(
                        {
                            "id": anfrage["id"],
                            "antwort": {
                                "answers": {"rechnung": {"noul": wert}},
                                "latency_ms": 42.0,
                            },
                        }
                    )
                )
            cp.stdout = "\n".join(zeilen) + "\n"
        return cp

    monkeypatch.setattr(kv, "_ssh", fake_ssh)
    return aufrufe


def _patch_ssh_unreachable(monkeypatch) -> None:
    def fake_ssh(inneres: str, eingabe: str | None = None):
        return types.SimpleNamespace(
            returncode=255, stdout="", stderr="ssh: connect timeout"
        )

    monkeypatch.setattr(kv, "_ssh", fake_ssh)


# ── Schwellen-Filter + Sortierung ────────────────────────────────────────────


def test_should_filter_by_threshold_and_sort_descending(monkeypatch):
    mails = [
        _mail("m1", wert=0.95, betreff="Rechnung Nr. 1"),
        _mail("m2", wert=0.4, betreff="Newsletter"),
        _mail("m3", wert=0.71, betreff="Zahlungsbeleg"),
    ]
    _patch_graph(monkeypatch, mails)
    _patch_ssh_ok(monkeypatch, mails)

    ergebnis = kv.vorfilter_lauf(
        tok="fake-token", ordner="Posteingang", tage=60, schwelle=0.7
    )

    assert ergebnis["geprueft"] == 3
    assert [k["id"] for k in ergebnis["kandidaten"]] == ["m1", "m3"]
    assert ergebnis["kandidaten"][0]["wert"] == 0.95
    assert ergebnis["median_latenz_ms"] == 42.0


def test_should_return_no_candidates_below_threshold(monkeypatch):
    mails = [_mail("m1", wert=0.3)]
    _patch_graph(monkeypatch, mails)
    _patch_ssh_ok(monkeypatch, mails)

    ergebnis = kv.vorfilter_lauf(
        tok="fake-token", ordner="Posteingang", tage=60, schwelle=0.7
    )
    assert ergebnis["kandidaten"] == []
    assert ergebnis["geprueft"] == 1


# ── Fehler bei kev-Ausfall ───────────────────────────────────────────────────


def test_should_exit_nonzero_and_report_nothing_when_kev_unreachable(
    monkeypatch, capsys
):
    mails = [_mail("m1", wert=0.95)]
    _patch_graph(monkeypatch, mails)
    _patch_ssh_unreachable(monkeypatch)

    with __import__("pytest").raises(SystemExit) as exc:
        kv.vorfilter_lauf(tok="fake-token", ordner="Posteingang", tage=60, schwelle=0.7)

    assert exc.value.code != 0
    ausgegeben = capsys.readouterr()
    assert "m1" not in ausgegeben.out
    assert "kandidaten" not in ausgegeben.out.lower() or ausgegeben.out == ""


def test_should_exit_nonzero_when_kev_response_missing_answer(monkeypatch):
    """Zeilenzahl stimmt, aber die Antwort traegt keinen Wert -> kein Teilergebnis."""
    mails = [_mail("m1", wert=0.95)]
    _patch_graph(monkeypatch, mails)

    def fake_ssh(inneres: str, eingabe: str | None = None):
        cp = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        if inneres.startswith("python3"):
            cp.stdout = json.dumps({"id": "m1", "antwort": {"answers": {}}}) + "\n"
        return cp

    monkeypatch.setattr(kv, "_ssh", fake_ssh)

    with __import__("pytest").raises(SystemExit) as exc:
        kv.vorfilter_lauf(tok="fake-token", ordner="Posteingang", tage=60, schwelle=0.7)
    assert exc.value.code != 0


# ── Tage-Filter ──────────────────────────────────────────────────────────────


def test_should_apply_days_filter_to_graph_query(monkeypatch):
    aufgerufene_urls = []

    def fake_http(method, url, **kwargs):
        aufgerufene_urls.append(url)
        return _FakeResp({"value": []})

    monkeypatch.setattr(kv, "_http", fake_http)
    monkeypatch.setattr(kv, "_daten", lambda r, kontext: r.json())
    monkeypatch.setattr(kv, "_auth", lambda tok: {})
    monkeypatch.setattr(kv, "_basis", lambda: "https://graph.example/me")
    monkeypatch.setattr(
        kv.time, "time", lambda: 1_800_000_000
    )  # fixer "jetzt"-Zeitpunkt

    kv.mails_holen("fake-token", "inbox", 7)

    erwartetes_datum = kv.time.strftime(
        "%Y-%m-%dT00:00:00Z", kv.time.gmtime(1_800_000_000 - 7 * 86400)
    )
    assert len(aufgerufene_urls) == 1
    assert f"receivedDateTime ge {erwartetes_datum}" in aufgerufene_urls[0]


def test_should_return_empty_result_without_calling_kev_when_no_mails(monkeypatch):
    """Leerer Ordner ist ein echtes leeres Ergebnis, kein maskierter Fehler —
    darf aber auch keinen SSH-Aufruf ausloesen."""
    _patch_graph(monkeypatch, [])
    aufrufe = []
    monkeypatch.setattr(
        kv,
        "_ssh",
        lambda *a, **k: (
            aufrufe.append(a) or types.SimpleNamespace(returncode=0, stdout="")
        ),
    )

    ergebnis = kv.vorfilter_lauf(
        tok="fake-token", ordner="Posteingang", tage=60, schwelle=0.7
    )
    assert ergebnis == {"kandidaten": [], "geprueft": 0, "median_latenz_ms": None}
    assert aufrufe == []


def test_should_exit_when_folder_not_found(monkeypatch):
    monkeypatch.setattr(kv, "find_folder", lambda tok, pfad: None)
    with __import__("pytest").raises(SystemExit):
        kv.vorfilter_lauf(
            tok="fake-token", ordner="Unbekannt/Ordner", tage=60, schwelle=0.7
        )
