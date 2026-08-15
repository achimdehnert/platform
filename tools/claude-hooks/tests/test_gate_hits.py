"""Tests für tools/claude-hooks/gate_hits.py — Treffer-Protokoll der Gate-Scanner.

Der Zweck des Protokolls ist die FP-Kalibrierung (KONZ-038 D2). Entsprechend
prüfen die Tests zwei Dinge härter als den Rest: dass ein Schreibfehler den Hook
niemals stört, und dass ein leeres Protokoll nicht als „0 Fehlalarme" durchgeht.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

gate_hits = pytest.importorskip("gate_hits")


class TestNotieren:
    def test_should_append_one_json_line_per_hit(self, tmp_path):
        ziel = tmp_path / "hits.jsonl"
        gate_hits.notiere("gate-a", "später", turn="mache ich später", pfad=ziel)
        gate_hits.notiere("gate-b", "vertagt", turn="ist vertagt", pfad=ziel)
        zeilen = ziel.read_text(encoding="utf-8").strip().splitlines()
        assert [json.loads(z)["slug"] for z in zeilen] == ["gate-a", "gate-b"]

    def test_should_record_what_is_needed_to_judge_the_hit(self, tmp_path):
        ziel = tmp_path / "hits.jsonl"
        gate_hits.notiere("g", "später", turn="das ziehe ich später nach", pfad=ziel)
        eintrag = json.loads(ziel.read_text(encoding="utf-8"))
        assert eintrag["marker"] == "später"
        assert "ziehe ich später nach" in eintrag["ausschnitt"]
        assert eintrag["zeit"].startswith("20")

    def test_should_not_carry_a_verdict(self, tmp_path):
        """Das Urteil entsteht beim Ritual-Lauf von Hand, nicht beim Feuern."""
        ziel = tmp_path / "hits.jsonl"
        gate_hits.notiere("g", "x", turn="x", pfad=ziel)
        assert "bewertung" not in json.loads(ziel.read_text(encoding="utf-8"))

    def test_should_create_the_directory_if_missing(self, tmp_path):
        ziel = tmp_path / "tief" / "drin" / "hits.jsonl"
        assert gate_hits.notiere("g", "x", turn="x", pfad=ziel) is True
        assert ziel.exists()

    def test_should_never_raise_when_the_path_is_unusable(self, tmp_path):
        """Ein Scanner, der am Protokoll stirbt, ist schlimmer als kein Protokoll."""
        blockiert = tmp_path / "datei"
        blockiert.write_text("ich bin eine Datei, kein Verzeichnis", encoding="utf-8")
        assert (
            gate_hits.notiere("g", "x", turn="x", pfad=blockiert / "hits.jsonl")
            is False
        )

    def test_should_cap_the_excerpt_around_the_marker(self, tmp_path):
        ziel = tmp_path / "hits.jsonl"
        turn = "A" * 5000 + "MARKER" + "B" * 5000
        gate_hits.notiere("g", "MARKER", turn=turn, pfad=ziel)
        ausschnitt = json.loads(ziel.read_text(encoding="utf-8"))["ausschnitt"]
        assert len(ausschnitt) <= 2 * gate_hits.KONTEXT + len("MARKER")
        assert "MARKER" in ausschnitt

    def test_should_survive_a_marker_that_is_not_in_the_turn(self, tmp_path):
        ziel = tmp_path / "hits.jsonl"
        assert gate_hits.notiere("g", "fehlt", turn="ganz anderer Text", pfad=ziel)


class TestLesen:
    def test_should_skip_broken_lines_instead_of_failing(self, tmp_path):
        ziel = tmp_path / "hits.jsonl"
        ziel.write_text('{"slug":"a"}\nkaputt{\n{"slug":"b"}\n', encoding="utf-8")
        assert [t["slug"] for t in gate_hits.lies(ziel)] == ["a", "b"]

    def test_should_return_nothing_for_a_missing_file(self, tmp_path):
        assert gate_hits.lies(tmp_path / "gibtsnicht.jsonl") == []


class TestBericht:
    def test_should_not_let_an_empty_log_pass_as_zero_false_positives(self, tmp_path):
        """Kein Treffer ist kein Beleg — genau diese Verwechslung soll der Text verhindern."""
        text = gate_hits.bericht([])
        assert "KEIN Beleg" in text

    def test_should_count_hits_per_gate(self, tmp_path):
        treffer = [
            {"zeit": "2026-08-10T10:00:00+00:00", "slug": "a", "modus": "advisory"},
            {"zeit": "2026-08-10T11:00:00+00:00", "slug": "a", "modus": "advisory"},
            {"zeit": "2026-08-11T10:00:00+00:00", "slug": "b", "modus": "advisory"},
        ]
        text = gate_hits.bericht(treffer)
        assert "Treffer gesamt: 3" in text
        assert "2  a" in text
        assert "1  b" in text

    def test_should_honour_the_since_filter(self, tmp_path):
        treffer = [
            {"zeit": "2026-08-01T10:00:00+00:00", "slug": "alt", "modus": "advisory"},
            {"zeit": "2026-08-10T10:00:00+00:00", "slug": "neu", "modus": "advisory"},
        ]
        text = gate_hits.bericht(treffer, seit="2026-08-05")
        assert "neu" in text
        assert "alt" not in text

    def test_should_refuse_to_derive_a_rate_from_the_count(self, tmp_path):
        treffer = [{"zeit": "2026-08-10T10:00:00+00:00", "slug": "a", "modus": "x"}]
        assert "NICHT ableitbar" in gate_hits.bericht(treffer)


class TestKeinTestrauschen:
    """Der Drill darf das echte Protokoll nicht fuellen.

    Realfall 2026-08-15: 212 von 212 Zeilen im Protokoll stammten aus pytest —
    die Scanner-Drills rufen `scanner.main()`, und `main()` schreibt ohne `pfad`.
    Die FP-Auswertung nach KONZ-038 D2 haette ueber ihr eigenes Rauschen geurteilt.
    """

    def test_should_not_write_to_the_real_log_during_a_test(
        self, tmp_path, monkeypatch
    ):
        echt = tmp_path / "echt.jsonl"
        monkeypatch.setattr(gate_hits, "HITS", echt)
        assert gate_hits.notiere("g", "später", turn="mache ich später") is False
        assert not echt.exists()

    def test_should_still_write_when_a_path_is_given_on_purpose(self, tmp_path):
        ziel = tmp_path / "absicht.jsonl"
        assert (
            gate_hits.notiere("g", "später", turn="mache ich später", pfad=ziel) is True
        )
        assert ziel.exists()


class TestHerkunft:
    def test_should_flag_lines_without_a_session_id(self):
        treffer = [
            {"zeit": "2026-08-10T10:00:00+00:00", "slug": "a", "modus": "advisory"},
            {
                "zeit": "2026-08-10T11:00:00+00:00",
                "slug": "a",
                "modus": "advisory",
                "session": "abc",
            },
        ]
        text = gate_hits.bericht(treffer)
        assert "1 von 2" in text
        assert "kein Beleg fuer irgendeine FP-Quote" in text

    def test_should_confirm_when_every_line_is_attributable(self):
        treffer = [
            {
                "zeit": "2026-08-10T10:00:00+00:00",
                "slug": "a",
                "modus": "advisory",
                "session": "abc",
            },
        ]
        assert "alle 1 Zeile(n) tragen eine session_id" in gate_hits.bericht(treffer)
