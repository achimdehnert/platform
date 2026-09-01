"""Drill für deferred_item_scanner.py (KONZ-038 K4, Slug deferred-item-no-tracking-issue).

Treffer und Nicht-Treffer gleichberechtigt: ein Scanner, der bei „das können wir
später diskutieren" feuert, wird abgeschaltet und schützt dann gar nichts.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location(
    "deferred_item_scanner", _DIR / "deferred_item_scanner.py"
)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

import gate_hits  # noqa: E402  (haengt am sys.path oben)


@pytest.fixture(autouse=True)
def _protokoll_isolieren(tmp_path, monkeypatch):
    """Zweiter Gurt neben der pytest-Sperre in `gate_hits.notiere`.

    `scanner.main()` protokolliert jeden Treffer ohne `pfad` — ohne Isolation
    landen die Fixture-Saetze dieses Drills im echten Protokoll des Entwicklers
    und verfaelschen die FP-Auswertung (Realfall 2026-08-15).
    """
    monkeypatch.setattr(gate_hits, "HITS", tmp_path / "gate-hits.jsonl")


def _transcript(tmp_path, assistant_text: str, extra_records=()):
    p = tmp_path / "t.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "mach mal"}},
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": assistant_text}]},
        },
        *extra_records,
    ]
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def _run(monkeypatch, capsys, path, **event_extra):
    ev = {"transcript_path": str(path), **event_extra}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ev)))
    rc = scanner.main()
    out = capsys.readouterr().out.strip()
    return rc, (json.loads(out) if out else {})


def _bash_record(cmd: str):
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]
        },
    }


@pytest.mark.parametrize(
    "satz",
    [
        "Den Backfill habe ich bewusst ausgelassen.",
        "Das Migration-Cleanup ist nicht Teil dieses PRs.",
        "Den Refactor ziehe ich später nach.",
        "Die Härtung kommt in einem separaten PR.",
        "The cache fix is out of scope for this change.",
    ],
)
def test_should_vertagung_ohne_tracking_melden(monkeypatch, capsys, tmp_path, satz):
    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, satz))
    assert rc == 0
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "deferred-item" in ctx, f"Drill fehlgeschlagen für: {satz!r}"


@pytest.mark.parametrize(
    "satz",
    [
        "Das können wir später diskutieren.",
        "Der Punkt bleibt offen und steht im Board.",  # Status-Prosa, bewusst kein Treffer
        "Vielleicht später.",
        "Follow-up-Fragen beantworte ich gern.",
        "Die Tests laufen jetzt durch.",
    ],
)
def test_should_alltagsprosa_in_ruhe_lassen(monkeypatch, capsys, tmp_path, satz):
    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, satz))
    assert rc == 0
    assert out == {}, f"False Positive auf: {satz!r} → {out}"


def test_should_bei_issue_create_im_turn_still_sein(monkeypatch, capsys, tmp_path):
    p = _transcript(
        tmp_path,
        "Den Backfill habe ich bewusst ausgelassen und getrackt.",
        extra_records=[_bash_record("gh issue create --title 'Backfill nachziehen'")],
    )
    rc, out = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert out == {}, f"Tracking-Artefakt nicht erkannt: {out}"


def test_should_bei_konz_write_im_turn_still_sein(monkeypatch, capsys, tmp_path):
    write_rec = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {
                        "file_path": "docs/konzepte/KONZ-platform-038-x.md",
                        "content": "Ledger-Zeile",
                    },
                }
            ]
        },
    }
    p = _transcript(
        tmp_path, "Der Fleet-Rollout ist vertagt.", extra_records=[write_rec]
    )
    rc, out = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert out == {}


def test_should_im_continuation_turn_schweigen(monkeypatch, capsys, tmp_path):
    p = _transcript(tmp_path, "Der Backfill ist bewusst ausgelassen.")
    rc, out = _run(monkeypatch, capsys, p, stop_hook_active=True)
    assert rc == 0
    assert out == {}


# --- Retro 287b23 #6: verschieben-FN + MCP-Tracking-Kanal ------------------------


def test_should_verschieben_in_ich_form_melden(monkeypatch, capsys, tmp_path):
    rc, out = _run(
        monkeypatch,
        capsys,
        _transcript(tmp_path, "Das Cleanup verschiebe ich auf morgen."),
    )
    assert rc == 0
    assert "deferred-item" in out.get("hookSpecificOutput", {}).get(
        "additionalContext", ""
    )


def test_should_termin_verschiebung_in_ruhe_lassen(monkeypatch, capsys, tmp_path):
    rc, out = _run(
        monkeypatch,
        capsys,
        _transcript(tmp_path, "Der Termin wurde auf Dienstag verschoben."),
    )
    assert rc == 0
    assert out == {}, f"False Positive auf Termin-Prosa: {out}"


def test_should_mcp_issue_tool_als_tracking_erkennen(monkeypatch, capsys, tmp_path):
    mcp_rec = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "mcp__github__create_issue",
                    "input": {"title": "Backfill nachziehen"},
                }
            ]
        },
    }
    p = _transcript(
        tmp_path, "Den Backfill habe ich bewusst ausgelassen.", extra_records=[mcp_rec]
    )
    rc, out = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert out == {}, f"MCP-Tracking-Kanal nicht erkannt: {out}"


class TestTrefferProtokoll:
    """Die Verdrahtung an gate_hits — ohne sie hat die FP-Kalibrierung keine Daten."""

    def test_should_record_the_hit_it_reports(self, tmp_path, monkeypatch, capsys):
        ziel = tmp_path / "gate-hits.jsonl"
        monkeypatch.setenv("GATE_HITS_DATEI", str(ziel))
        import gate_hits

        monkeypatch.setattr(gate_hits, "HITS", ziel)
        # Dieser Test prueft genau den Schreibpfad, den die pytest-Sperre sonst
        # stilllegt — also hier bewusst abschalten. Das Ziel bleibt tmp_path.
        monkeypatch.setattr(gate_hits, "_unter_test", lambda: False)

        pfad = _transcript(tmp_path, "Den Backfill ziehe ich später nach.")
        rc, ausgabe = _run(monkeypatch, capsys, pfad, session_id="sitzung-1")

        assert rc == 0
        assert (
            "deferred-item check" in ausgabe["hookSpecificOutput"]["additionalContext"]
        )
        zeilen = ziel.read_text(encoding="utf-8").strip().splitlines()
        assert len(zeilen) == 1
        eintrag = json.loads(zeilen[0])
        assert eintrag["slug"] == "deferred-item-no-tracking-issue"
        assert eintrag["session"] == "sitzung-1"
        assert "später" in eintrag["ausschnitt"]

    def test_should_write_nothing_when_it_does_not_report(
        self, tmp_path, monkeypatch, capsys
    ):
        ziel = tmp_path / "gate-hits.jsonl"
        import gate_hits

        monkeypatch.setattr(gate_hits, "HITS", ziel)
        # Ohne dieses Abschalten waere der Test leer: die pytest-Sperre allein
        # liesse ihn auch dann gruen, wenn der Scanner faelschlich protokolliert.
        monkeypatch.setattr(gate_hits, "_unter_test", lambda: False)
        pfad = _transcript(tmp_path, "Alles erledigt, nichts offen.")
        rc, ausgabe = _run(monkeypatch, capsys, pfad)
        assert (rc, ausgabe) == (0, {})
        assert not ziel.exists()


# --- FN-Klasse Verneinungsform (Retro 9d861a #2, 2026-08-16) ------------------
#
# Zweite Instanz derselben Klasse wie Retro 287b23 #6 ("verschieben" fehlte).
# Realer Wortlaut, der durchrutschte: "ist hier bewusst nicht mitgemacht" —
# ein Aufschub in Verneinungsform. Der Befund blieb dadurch ohne Tracking,
# obwohl genau dieser Scanner dafuer existiert.


def test_should_catch_deferral_in_negated_form():
    import deferred_item_scanner as d

    realer_wortlaut = (
        "Verschiedene Quellen, verschiedene Lebenszyklen — eine Zusammenlegung "
        "waere ein eigener Umbau und ist hier bewusst nicht mitgemacht."
    )
    assert d.DEFERRAL_PATTERNS.search(realer_wortlaut), (
        "Der Wortlaut, der am 2026-08-16 durchrutschte, muss treffen"
    )


def test_should_catch_negated_variants():
    import deferred_item_scanner as d

    for satz in (
        "Das habe ich absichtlich nicht mitgezogen.",
        "Die Migration ist bewusst nicht mitgeliefert.",
        "Den Rest habe ich hier nicht angefasst.",
    ):
        assert d.DEFERRAL_PATTERNS.search(satz), satz


def test_should_not_fire_on_a_report_about_others():
    """Eng gehalten: ohne 'bewusst|absichtlich|hier' kein Treffer.

    Sonst feuert jeder Bericht ueber fremdes Verhalten — und ein Scanner mit
    hoher Fehlalarmquote wird abgeschaltet und meldet dann gar nichts mehr.
    """
    import deferred_item_scanner as d

    for satz in (
        "Die anderen haben das nicht mitgemacht.",
        "Der Nachbar-PR hat den Test nicht mitgeliefert.",
    ):
        assert not d.DEFERRAL_PATTERNS.search(satz), satz


# --- Zweite Trefferklasse: die Board-Zeile (Retro e70d11) --------------------
#
# Der reale Rueckfall vom 2026-08-28: drei in Prod gemessene Defekte standen als
# offene Board-Zeilen ohne Anker und blieben ungetrackt. Kein Vertagungs-Verb war
# im Turn -- der Scanner schwieg nach damaligem Wortlaut zu Recht.

BOARD_ECHT = """### 📌 Was der Prod-Lauf zeigte

| # | Befund | Beleg |
|---|---|---|
| 7 | 3 Dateien doppelt | gleiche `sha256`, einmal `upload://` |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 4 | Dubletten zusammenführen | a-hub | — | 🟢 Befund | fixen (ich) |
| 5 | Zwei PDFs ohne Text | a-hub | — | 🟢 Befund | prüfen (ich) |
"""


def test_should_offenen_board_befund_ohne_anker_melden(monkeypatch, capsys, tmp_path):
    """Der Realfall, gegen den diese Klasse geschrieben ist."""
    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, BOARD_ECHT))

    assert rc == 0
    assert "deferred-item check" in out.get("hookSpecificOutput", {}).get(
        "additionalContext", ""
    )
    assert "Board" in out["hookSpecificOutput"]["additionalContext"]


def test_should_schweigen_wenn_die_zeile_einen_anker_traegt(
    monkeypatch, capsys, tmp_path
):
    """Gegenprobe: mit Issue-Nummer ist der Befund verankert."""
    text = BOARD_ECHT.replace(
        "| a-hub | — | 🟢 Befund | fixen (ich) |",
        "| a-hub | #275 | 🟢 Befund | fixen (ich) |",
    )
    text = text.replace(
        "| a-hub | — | 🟢 Befund | prüfen (ich) |",
        "| a-hub | #276 | 🟢 Befund | prüfen (ich) |",
    )

    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, text))

    assert rc == 0 and out == {}


@pytest.mark.parametrize(
    "zeile",
    [
        "| 2 | Deploy `08b24aa` | a-hub | — | ⛔ wartet am Gate | freigeben (du) |",
        "| 1 | Portal-Abruf per Knopf | a-hub | — | 🟡 CI läuft | warten (CI) |",
        "| 3 | Retro-Report | platform | — | ✅ gemergt | — |",
        "| 9 | Konzept-Schritt | a-hub | — | ✅ fehlt nicht mehr | — |",
    ],
)
def test_should_bei_gewoehnlichen_boardzeilen_schweigen(
    monkeypatch, capsys, tmp_path, zeile
):
    """Ein Scanner, der bei jedem Statusboard feuert, wird abgeschaltet."""
    rc, out = _run(
        monkeypatch, capsys, _transcript(tmp_path, f"### Stand\n\n{zeile}\n")
    )

    assert rc == 0 and out == {}


def test_should_schweigen_wenn_im_selben_turn_ein_issue_entstand(
    monkeypatch, capsys, tmp_path
):
    """Der Anker darf auch als Handlung kommen, nicht nur als Text."""
    pfad = _transcript(
        tmp_path,
        BOARD_ECHT,
        extra_records=[_bash_record("gh issue create -R o/r --title x")],
    )

    rc, out = _run(monkeypatch, capsys, pfad)

    assert rc == 0 and out == {}


def test_should_auch_die_nummerierte_boardform_sehen(monkeypatch, capsys, tmp_path):
    """Sobald volle URLs noetig sind, ist das Board eine Liste — dieselbe Pflicht."""
    text = "### 🟢 Offen\n\n- **[4]** 🟢 Dublette in der Analyse — noch kein Issue\n"

    rc, out = _run(monkeypatch, capsys, _transcript(tmp_path, text))

    assert rc == 0
    assert "deferred-item check" in out.get("hookSpecificOutput", {}).get(
        "additionalContext", ""
    )
