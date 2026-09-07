"""Tests für tools/kosten_qualitaet.py (Kosten-/Qualitäts-Auswertung je Sitzung).

Alle Fixtures sind synthetisch (kein echtes Mitschrift-/Ledger-/Retro-Material —
platform ist ein öffentliches Repo, s. CLAUDE.md). Deckt die im Auftrag
geforderten Fälle 1-8 ab: Kostenrechnung, Subagenten-Token, Präfix-Verbindung
(eindeutig + mehrdeutig), Nachbesserungs-Erkennung, Deckungs-Untergrenze
(Positivkontrolle: KEINE stille 0-Quote), kaputte JSONL-Zeilen, fehlendes
Ledger.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "claude-hooks"))

from kosten_qualitaet import (  # noqa: E402
    _accumulate_session,
    build_zeilen,
    discover_sessions,
    load_ledger,
    nachbesserungsquote,
    normalize_retro_session_id,
    resolve_prefix,
    retro_qualitaet,
    run,
)
from llm_pricing import PRICING_USD_PER_MTOK  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture-Helfer
# ---------------------------------------------------------------------------


def _assistant(
    model: str,
    usage: dict | None = None,
    content: list | None = None,
    timestamp: str = "2026-09-05T10:00:00.000Z",
) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "timestamp": timestamp,
            "message": {
                "model": model,
                "usage": usage or {},
                "content": content or [],
            },
        }
    )


def _write_block(name: str, file_path: str | None) -> dict:
    tool_input = {"file_path": file_path} if file_path else {}
    return {"type": "tool_use", "name": name, "input": tool_input}


def _bash_block(command: str) -> dict:
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def _make_session(
    tmp_path: Path,
    slug: str,
    session_id: str,
    main_lines: list[str],
    subagents: dict[str, list[str]] | None = None,
) -> Path:
    """Legt `<tmp_path>/projects/<slug>/<session_id>.jsonl` (+ Subagenten) an."""
    proj_dir = tmp_path / "projects" / slug
    proj_dir.mkdir(parents=True, exist_ok=True)
    main_path = proj_dir / f"{session_id}.jsonl"
    main_path.write_text("\n".join(main_lines) + "\n", encoding="utf-8")
    if subagents:
        sub_dir = proj_dir / session_id / "subagents"
        sub_dir.mkdir(parents=True, exist_ok=True)
        for name, lines in subagents.items():
            (sub_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return main_path


# ---------------------------------------------------------------------------
# 1. Kostenrechnung stimmt für eine bekannte Token-Zahl gegen die Preistabelle.
# ---------------------------------------------------------------------------


def test_should_kostenrechnung_stimmt_gegen_preistabelle(tmp_path: Path) -> None:
    model = "claude-sonnet-5"
    preis = PRICING_USD_PER_MTOK[model]
    assert preis == {"input": 2.0, "output": 10.0}

    usage = {
        "input_tokens": 1000,
        "output_tokens": 500,
        "cache_read_input_tokens": 200,
        "cache_creation_input_tokens": 100,
    }
    main_lines = [_assistant(model, usage)]
    main_path = _make_session(tmp_path, "proj", "sess00001", main_lines)

    agg = _accumulate_session(main_path, "sess00001", "proj")

    erwartet = (
        1000 * 2.0 + 100 * 2.0 * 1.25 + 200 * 2.0 * 0.1 + 500 * 10.0
    ) / 1_000_000.0
    assert agg.gesamt_kosten_usd() == pytest.approx(erwartet, abs=1e-9)


# ---------------------------------------------------------------------------
# 2. Subagenten-Token werden mitgezählt (Verzeichnis vorhanden).
# ---------------------------------------------------------------------------


def test_should_subagenten_tokens_mitzaehlen(tmp_path: Path) -> None:
    main_lines = [
        _assistant("claude-sonnet-5", {"input_tokens": 100, "output_tokens": 50})
    ]
    sub_lines = [
        _assistant("claude-haiku-4-5", {"input_tokens": 200, "output_tokens": 100})
    ]
    main_path = _make_session(
        tmp_path,
        "proj",
        "sess00002",
        main_lines,
        subagents={"agent-xyz.jsonl": sub_lines},
    )

    agg = _accumulate_session(main_path, "sess00002", "proj")

    assert agg.n_subagenten == 1
    assert "claude-haiku-4-5" in agg.modelle
    assert agg.modelle["claude-haiku-4-5"].input_tokens == 200
    # Kosten schliessen den Subagenten-Anteil ein (nicht nur das Hauptmodell).
    assert agg.gesamt_kosten_usd() > agg.haupt_kosten_usd()


# ---------------------------------------------------------------------------
# 3. Präfix-Verbindung Ledger/Retro/Mitschrift trifft die richtige Sitzung.
# ---------------------------------------------------------------------------


def test_should_praefix_verbindung_richtige_sitzung_treffen(tmp_path: Path) -> None:
    id_a = "a1a1a1a1-0000-0000-0000-000000000001"
    id_b = "b2b2b2b2-0000-0000-0000-000000000002"

    agg_a = _accumulate_session(
        _make_session(
            tmp_path,
            "proj",
            id_a,
            [_assistant("claude-sonnet-5", {"input_tokens": 10, "output_tokens": 5})],
        ),
        id_a,
        "proj",
    )
    agg_b = _accumulate_session(
        _make_session(
            tmp_path,
            "proj",
            id_b,
            [_assistant("claude-opus-5", {"input_tokens": 10, "output_tokens": 5})],
        ),
        id_b,
        "proj",
    )

    ledger_rows = [
        {
            "session_id": id_a[:8],
            "anteil_tokens_nicht_hauptmodell": "42.0",
        }
    ]
    retro_reports = [{"session_id": id_b[:6], "scores": {"zielerreichung": 4}}]

    zeilen, warnungen = build_zeilen([agg_a, agg_b], ledger_rows, retro_reports)
    assert warnungen == {"mehrdeutig_ledger": 0, "mehrdeutig_retro": 0}

    by_session = {z.session_kurz: z for z in zeilen}
    assert by_session[id_a[:8]].delegation_pct == 42.0
    assert by_session[id_a[:8]].qualitaet is None
    assert by_session[id_b[:8]].qualitaet == 4.0
    assert by_session[id_b[:8]].delegation_pct is None


# ---------------------------------------------------------------------------
# 4. Mehrdeutiges Präfix wird als `mehrdeutig` gemeldet, nicht zugeordnet.
# ---------------------------------------------------------------------------


def test_should_mehrdeutiges_praefix_nicht_zuordnen(tmp_path: Path) -> None:
    id_a = "abcdef12-0000-0000-0000-000000000001"
    id_b = "abcdef12-0000-0000-0000-000000000002"  # gleiches 8er-Präfix wie id_a

    agg_a = _accumulate_session(
        _make_session(tmp_path, "proj", id_a, [_assistant("claude-sonnet-5")]),
        id_a,
        "proj",
    )
    agg_b = _accumulate_session(
        _make_session(tmp_path, "proj", id_b, [_assistant("claude-sonnet-5")]),
        id_b,
        "proj",
    )

    ledger_rows = [
        {"session_id": "abcdef12", "anteil_tokens_nicht_hauptmodell": "99.0"}
    ]

    zeilen, warnungen = build_zeilen([agg_a, agg_b], ledger_rows, [])

    assert warnungen["mehrdeutig_ledger"] == 1
    for z in zeilen:
        assert z.delegation_pct is None


def test_should_resolve_prefix_mehrdeutigkeit_melden() -> None:
    full_ids = ["abcdef120001", "abcdef120002", "112233445566"]
    treffer, mehrdeutig = resolve_prefix("abcdef12", full_ids)
    assert treffer is None
    assert mehrdeutig is True

    treffer, mehrdeutig = resolve_prefix("112233", full_ids)
    assert treffer == "112233445566"
    assert mehrdeutig is False

    treffer, mehrdeutig = resolve_prefix("ffffff", full_ids)
    assert treffer is None
    assert mehrdeutig is False


def test_should_normalize_retro_session_id_incr_suffix_schneiden() -> None:
    assert normalize_retro_session_id("0181a7-incr") == "0181a7"
    assert normalize_retro_session_id("2d7cd9") == "2d7cd9"


# ---------------------------------------------------------------------------
# 5. Nachbesserung wird erkannt, wenn Subagent und Hauptmodell dieselbe Datei
#    schreiben.
# ---------------------------------------------------------------------------


def test_should_nachbesserung_erkennen_wenn_subagent_und_haupt_dieselbe_datei_schreiben(
    tmp_path: Path,
) -> None:
    main_lines = [
        _assistant(
            "claude-sonnet-5",
            content=[_write_block("Edit", "/repo/foo.py")],
            timestamp="2026-09-05T11:00:00.000Z",
        )
    ]
    sub_lines = [
        _assistant(
            "claude-haiku-4-5",
            content=[_write_block("Write", "/repo/foo.py")],
            timestamp="2026-09-05T10:00:00.000Z",
        )
    ]
    main_path = _make_session(
        tmp_path,
        "proj",
        "sess00005",
        main_lines,
        subagents={"agent-a.jsonl": sub_lines},
    )
    agg = _accumulate_session(main_path, "sess00005", "proj")

    quote, deckung = nachbesserungsquote(agg)
    assert deckung == 100.0
    assert quote == 100.0


def test_should_keine_nachbesserung_melden_wenn_datei_nicht_erneut_geschrieben_wird(
    tmp_path: Path,
) -> None:
    main_lines = [
        _assistant(
            "claude-sonnet-5",
            content=[_write_block("Edit", "/repo/andere_datei.py")],
            timestamp="2026-09-05T11:00:00.000Z",
        )
    ]
    sub_lines = [
        _assistant(
            "claude-haiku-4-5",
            content=[_write_block("Write", "/repo/foo.py")],
            timestamp="2026-09-05T10:00:00.000Z",
        )
    ]
    main_path = _make_session(
        tmp_path,
        "proj",
        "sess00006",
        main_lines,
        subagents={"agent-a.jsonl": sub_lines},
    )
    agg = _accumulate_session(main_path, "sess00006", "proj")

    quote, deckung = nachbesserungsquote(agg)
    assert deckung == 100.0
    assert quote == 0.0


# ---------------------------------------------------------------------------
# 6. Deckungs-Test: Sitzung ohne `file_path` liefert `ungedeckt`, nicht `0`.
#    Das ist die Positivkontrolle — ohne sie ist die Kennzahl wertlos.
# ---------------------------------------------------------------------------


def test_should_sitzung_ohne_file_path_ungedeckt_melden_nicht_null(
    tmp_path: Path,
) -> None:
    main_lines = [
        _assistant(
            "claude-sonnet-5",
            content=[_bash_block("sed -i 's/a/b/' foo.py")],
            timestamp="2026-09-05T11:00:00.000Z",
        )
    ]
    sub_lines = [
        _assistant(
            "claude-haiku-4-5",
            content=[_bash_block("cat > bar.py <<'EOF'\nprint(1)\nEOF")],
            timestamp="2026-09-05T10:00:00.000Z",
        ),
        _assistant(
            "claude-haiku-4-5",
            content=[_bash_block("cat > baz.py <<'EOF'\nprint(2)\nEOF")],
            timestamp="2026-09-05T10:05:00.000Z",
        ),
        _assistant(
            "claude-haiku-4-5",
            content=[_bash_block("mv baz.py qux.py")],
            timestamp="2026-09-05T10:06:00.000Z",
        ),
        _assistant(
            "claude-haiku-4-5",
            content=[_bash_block("cp qux.py quux.py")],
            timestamp="2026-09-05T10:07:00.000Z",
        ),
    ]
    main_path = _make_session(
        tmp_path,
        "proj",
        "sess00007",
        main_lines,
        subagents={"agent-a.jsonl": sub_lines},
    )
    agg = _accumulate_session(main_path, "sess00007", "proj")

    # Realfall aus dem Auftrag: 4 Subagenten-Schreibaufrufe (per Bash), aber
    # KEIN einziger tool_use mit file_path -> Deckung 0%, NICHT Quote 0%.
    assert agg.schreibaufrufe_mit_pfad == 0
    assert agg.schreibaufrufe_gesamt >= 4

    quote, deckung = nachbesserungsquote(agg)
    assert deckung < 50.0
    assert quote is None  # NIEMALS 0 — das ist die Positivkontrolle.


def test_should_deckung_100_prozent_liefern_wenn_keine_schreibaufrufe(
    tmp_path: Path,
) -> None:
    """Keine Schreibaufrufe ueberhaupt -> Deckung ist trivial vollstaendig."""
    main_lines = [_assistant("claude-sonnet-5", {"input_tokens": 5})]
    main_path = _make_session(tmp_path, "proj", "sess00008", main_lines)
    agg = _accumulate_session(main_path, "sess00008", "proj")

    quote, deckung = nachbesserungsquote(agg)
    assert deckung == 100.0
    assert quote == 0.0


# ---------------------------------------------------------------------------
# 7. Kaputte JSONL-Zeile bricht nichts ab und wird gezählt.
# ---------------------------------------------------------------------------


def test_should_kaputte_jsonl_zeile_zaehlen_ohne_abbruch(
    tmp_path: Path,
) -> None:
    main_lines = [
        _assistant("claude-sonnet-5", {"input_tokens": 10, "output_tokens": 5}),
        "{das ist kein json",
        _assistant("claude-sonnet-5", {"input_tokens": 20, "output_tokens": 10}),
    ]
    main_path = _make_session(tmp_path, "proj", "sess00009", main_lines)

    agg = _accumulate_session(main_path, "sess00009", "proj")

    assert agg.kaputte_zeilen == 1
    # Die zwei gueltigen Zeilen wurden trotzdem eingerechnet.
    assert agg.modelle["claude-sonnet-5"].input_tokens == 30


# ---------------------------------------------------------------------------
# 8. Fehlendes Ledger führt nicht zum Absturz.
# ---------------------------------------------------------------------------


def test_should_fehlendes_ledger_nicht_zum_absturz_fuehren(tmp_path: Path) -> None:
    rows = load_ledger(tmp_path / "gibt-es-nicht.tsv")
    assert rows == []

    main_lines = [
        _assistant("claude-sonnet-5", {"input_tokens": 10, "output_tokens": 5})
    ]
    _make_session(tmp_path, "proj", "sess00010", main_lines)

    args = argparse.Namespace(
        seit=None,
        projekt=None,
        json=True,
        projects_dir=str(tmp_path / "projects"),
        ledger=str(tmp_path / "gibt-es-nicht.tsv"),
        retros_dir=[str(tmp_path / "keine-retros")],
    )
    exit_code = run(args)
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Zusatz: discover_sessions, retro_qualitaet, JSON-Ausgabe-Struktur.
# ---------------------------------------------------------------------------


def test_should_discover_sessions_haupttranskripte_finden(tmp_path: Path) -> None:
    _make_session(
        tmp_path,
        "proj-a",
        "sessA",
        [_assistant("claude-sonnet-5")],
    )
    _make_session(
        tmp_path,
        "proj-b",
        "sessB",
        [_assistant("claude-sonnet-5")],
    )

    alle = discover_sessions(tmp_path / "projects", None)
    assert {s[1] for s in alle} == {"sessA", "sessB"}

    nur_a = discover_sessions(tmp_path / "projects", "proj-a")
    assert {s[1] for s in nur_a} == {"sessA"}


def test_should_retro_qualitaet_sechs_noten_mitteln() -> None:
    fm = {
        "scores": {
            "zielerreichung": 4,
            "architektur_design": 3,
            "code_konventionstreue": 3,
            "risiko_debt": 2,
            "prozess_effizienz": 2,
            "entscheidungsqualitaet": 4,
        }
    }
    assert retro_qualitaet(fm) == 3.0
    assert retro_qualitaet({"scores": {}}) is None
    assert retro_qualitaet({}) is None


def test_should_run_json_ausgabe_gueltiges_json_liefern(tmp_path: Path, capsys) -> None:
    main_lines = [
        _assistant(
            "claude-sonnet-5",
            {"input_tokens": 100, "output_tokens": 50},
            timestamp="2026-09-05T09:00:00.000Z",
        )
    ]
    _make_session(tmp_path, "proj", "sess00011", main_lines)

    args = argparse.Namespace(
        seit=None,
        projekt=None,
        json=True,
        projects_dir=str(tmp_path / "projects"),
        ledger=str(tmp_path / "kein-ledger.tsv"),
        retros_dir=[str(tmp_path / "keine-retros")],
    )
    exit_code = run(args)
    assert exit_code == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["zeilen"][0]["session"] == "sess00011"[:8]
    assert payload["zeilen"][0]["kosten_usd"] > 0
    assert payload["warnungen"]["kaputte_jsonl_zeilen"] == 0
