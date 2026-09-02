"""Tests fuer tools/claude-hooks/inject_policies.py (UserPromptSubmit-Hook).

Der Hook stand bis platform#2606 auf Volltext-Injektion: bei einem Trigger-Wort
ging die GANZE Policy-Datei in den Kontext. Gemessen am 2026-09-02 in einer
Sitzung: vier Injektionen mit 10,9 / 15,8 / 90,6 / 106,0 KB — zwei davon
ausgeloest durch Abschlussmeldungen von Hintergrund-Agenten, ohne dass ein
Mensch etwas geschrieben hatte.

Vier Eigenschaften werden hier festgeschrieben, jede mit ihrer Gegenprobe:
Kopf statt Volltext, Wortgrenze statt Substring, kein Feuern auf System-Texten,
harter Deckel. Die wichtigste ist die Gegenprobe: ein echter Treffer muss
weiterhin etwas injizieren — sonst misst eine gruene Null nur den eigenen
Filter (🌀 feedback_null_from_own_filter_needs_positive_control).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "claude-hooks"
    / "inject_policies.py"
)

LANGE_POLICY = """# Policy: Error Handling — Ursache statt Quick-Fix
<!-- rule_class: B -->

**Trigger words:** fehler, bug, root cause, nachhaltige loesung

## Rule (Owner-Weisung)

Bei jedem Fehler mit Schadens- oder Wiederholungspotenzial:

1. Ursache belegen, nicht raten.
2. Fix auf Ursachen-Ebene bevorzugen.
3. Lehre nach bestehender Taxonomie sichern.
4. Ab dem 2. Auftreten derselben Fehlerklasse: Gate bauen.

## Abgrenzung

FUELLTEXT-{n}
""" + "\n".join(
    f"Zeile {i} mit reichlich Fuelltext zur Laengenmessung." for i in range(400)
)

ZWEITE_POLICY = """# Policy: Zielzustand-first

**Trigger words:** zielzustand, akzeptanzkriterien

## Rule

Aufgaben werden gegen einen akzeptierten Zielzustand erledigt.
Fehlt er, wird er VOR Arbeitsbeginn geklaert.
""" + "\n".join(f"Auch hier Fuelltext {i}." for i in range(400))


@pytest.fixture
def policies(tmp_path: Path) -> Path:
    d = tmp_path / "policies"
    d.mkdir()
    (d / "error-handling.md").write_text(LANGE_POLICY, encoding="utf-8")
    (d / "zielzustand.md").write_text(ZWEITE_POLICY, encoding="utf-8")
    return d


def _lauf(prompt: str, policies: Path) -> str:
    """Hook als Prozess aufrufen — derselbe Pfad, den Claude Code nimmt."""
    fertig = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": prompt, "hook_event_name": "UserPromptSubmit"}),
        capture_output=True,
        text=True,
        env={
            "POLICY_DIR": str(policies),
            "PATH": "/usr/bin:/bin",
            "HOME": "/nonexistent",
        },
    )
    assert fertig.returncode == 0, f"Hook darf nie fehlschlagen: {fertig.stderr}"
    assert not fertig.stderr.strip(), f"Hook schreibt auf stderr: {fertig.stderr}"
    return fertig.stdout


# ── Gegenprobe zuerst: feuert der Hook ueberhaupt noch? ─────────────────────


class TestPositivkontrolle:
    def test_should_still_inject_something_on_a_real_hit(self, policies: Path) -> None:
        aus = _lauf("wir haben hier einen fehler im deploy", policies)
        assert aus.strip(), "ohne Positivkontrolle misst jede Null nur den Filter"
        assert "Error Handling" in aus
        assert "Ursache belegen" in aus, "der Kern der Regel muss mitkommen"

    def test_should_name_the_path_to_the_full_text(self, policies: Path) -> None:
        """Der Kopf ersetzt den Volltext nur, wenn er sagt, wo der steht."""
        aus = _lauf("ein fehler", policies)
        assert str(policies / "error-handling.md") in aus
        assert "Volltext" in aus


# ── 1. Kopf statt Volltext ─────────────────────────────────────────────────


class TestKopfStattVolltext:
    def test_should_stay_below_the_per_policy_budget(self, policies: Path) -> None:
        aus = _lauf("ein fehler", policies)
        assert len(aus.encode()) <= 1500, f"{len(aus.encode())} B statt <= 1500 B"

    def test_should_not_contain_the_tail_of_the_file(self, policies: Path) -> None:
        """Gegenprobe zur Laenge: kurz genug waere auch eine gekappte Mitte."""
        aus = _lauf("ein fehler", policies)
        assert "Abgrenzung" not in aus
        assert "Zeile 399" not in aus

    def test_should_shrink_hard_against_the_full_text(self, policies: Path) -> None:
        voll = (policies / "error-handling.md").read_text(encoding="utf-8")
        aus = _lauf("ein fehler", policies)
        assert len(aus.encode()) < len(voll.encode()) / 10

    def test_should_prefer_the_rule_section_over_the_first_lines(
        self, policies: Path
    ) -> None:
        aus = _lauf("zielzustand?", policies)
        assert "akzeptierten Zielzustand" in aus
        assert "Trigger words" not in aus, "die Trigger-Zeile ist kein Regelinhalt"


# ── 2. Wortgrenze statt Substring ──────────────────────────────────────────


class TestWortgrenze:
    def test_should_not_fire_on_a_compound_word(self, policies: Path) -> None:
        """`Fehlerbehebung` ist der gemessene Fehlalarm-Fall aus #2606."""
        assert _lauf("die Fehlerbehebung laeuft seit gestern", policies) == ""

    def test_should_not_fire_on_a_substring_inside_a_word(self, policies: Path) -> None:
        assert _lauf("debugging der pipeline", policies) == ""

    def test_should_still_fire_on_a_german_inflected_form(self, policies: Path) -> None:
        """Die Wortgrenze darf nicht am Plural scheitern — sonst tauscht sie
        nur Fehlalarm gegen Blindheit."""
        assert _lauf("mit zwei Fehlern im Lauf", policies).strip()

    def test_should_be_case_insensitive(self, policies: Path) -> None:
        assert _lauf("FEHLER im Deploy", policies).strip()

    def test_should_match_a_multi_word_trigger(self, policies: Path) -> None:
        assert _lauf("wir brauchen eine nachhaltige loesung", policies).strip()


class TestGedaempfteTrigger:
    """`done` und `claim` sind gestrichen, `mcp` an ein zweites Wort gebunden.

    Begruendung an 3 507 echten Prompts gemessen; die Zahlen stehen im Hook.
    """

    def test_should_not_fire_on_the_owners_checkoff_shorthand(
        self, tmp_path: Path
    ) -> None:
        d = tmp_path / "p"
        d.mkdir()
        (d / "evidence.md").write_text(
            "# Policy: Evidence\n\n**Trigger words:** done, claim, beweis\n\n"
            "## Rule\n\nBehauptung nur bis zur Tiefe des billigsten Checks.\n",
            encoding="utf-8",
        )
        assert _lauf("5 done 6 done 7 8 9 go", d) == ""
        assert _lauf("that is my claim", d) == ""
        assert _lauf("wo ist der beweis?", d).strip(), "Positivkontrolle"

    def test_should_bind_mcp_to_a_second_word(self, tmp_path: Path) -> None:
        d = tmp_path / "p"
        d.mkdir()
        (d / "orchestrator.md").write_text(
            "# Policy: Orchestrator MCP\n\n**Trigger words:** mcp, headless\n\n"
            "## What it is\n\nDer Orchestrator ist ein MCP-Server.\n",
            encoding="utf-8",
        )
        assert _lauf("ich pushe nach mcp-hub", d) == ""
        assert _lauf("laeuft der mcp server noch?", d).strip()

    def test_should_treat_an_uppercase_trigger_as_case_sensitive(
        self, tmp_path: Path
    ) -> None:
        """`COMPLETE` meint den Status-Marker, nicht jedes englische Wort."""
        d = tmp_path / "p"
        d.mkdir()
        (d / "evidence.md").write_text(
            "# Policy: Evidence\n\n**Trigger words:** COMPLETE\n\n"
            "## Rule\n\nStatus nur mit Beleg.\n",
            encoding="utf-8",
        )
        assert _lauf("a complete rewrite of the module", d) == ""
        assert _lauf("Status: COMPLETE", d).strip()

    def test_should_keep_a_wrapped_multi_word_trigger_together(
        self, tmp_path: Path
    ) -> None:
        """Der Umbruch trennt nicht zwingend zwei Trigger (Fix #2606).

        In `platform-agents.md` bricht "where should this live" nach "where"
        um. Die alte Komma-Verbindung machte daraus zwei Trigger; "where"
        allein traf 18-mal, ausnahmslos im Kompaktierungs-Vorspann.
        """
        d = tmp_path / "p"
        d.mkdir()
        (d / "agents.md").write_text(
            "# Policy: Platform Agents\n\n**Trigger words:** welcher hub, where\n"
            "should this live, scribe\n\n## Rule\n\nNeue Agenten nach dev-hub.\n",
            encoding="utf-8",
        )
        assert _lauf("where is the file", d) == ""
        assert _lauf("where should this live?", d).strip()


# ── 3. Keine System-Texte ──────────────────────────────────────────────────


class TestSystemTexte:
    @pytest.mark.parametrize(
        "huelle",
        [
            "<task-notification>\n<task-id>a1</task-id>\nAgent fertig — 0 Fehler\n",
            "<system-reminder>Es gab einen Fehler beim Zielzustand</system-reminder>",
            "<bash-input>rg fehler tools/</bash-input>",
            "[SYSTEM NOTIFICATION] fehler im Hintergrundlauf",
            "This session is being continued from a previous conversation. "
            "Es ging um einen fehler.",
        ],
    )
    def test_should_not_fire_on_a_machine_envelope(
        self, policies: Path, huelle: str
    ) -> None:
        assert _lauf(huelle, policies) == ""

    def test_should_still_fire_when_a_human_mentions_the_tag(
        self, policies: Path
    ) -> None:
        """Nur der ANFANG zaehlt — sonst waere jede Frage nach dem Mechanismus
        selbst stumm geschaltet."""
        aus = _lauf("warum feuert der Hook auf <task-notification>? fehler?", policies)
        assert aus.strip()


# ── 4. Deckel ──────────────────────────────────────────────────────────────


class TestDeckel:
    def test_should_cap_the_total_injection(self, policies: Path) -> None:
        aus = _lauf(
            "fehler und zielzustand",
            policies,
        )
        assert len(aus.encode()) <= 6000

    def test_should_list_what_did_not_fit_instead_of_dropping_it(
        self, tmp_path: Path
    ) -> None:
        d = tmp_path / "p"
        d.mkdir()
        for i in range(6):
            (d / f"p{i}.md").write_text(
                f"# Policy Nummer {i}\n\n**Trigger words:** sammeltrigger\n\n"
                "## Rule\n\n" + ("Ausfuehrlicher Regeltext. " * 60) + "\n",
                encoding="utf-8",
            )
        fertig = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"prompt": "sammeltrigger bitte"}),
            capture_output=True,
            text=True,
            env={
                "POLICY_DIR": str(d),
                "POLICY_INJEKTION_BYTES": "3000",
                "PATH": "/usr/bin:/bin",
                "HOME": "/nonexistent",
            },
        )
        aus = fertig.stdout
        assert fertig.returncode == 0
        assert len(aus.encode()) <= 3000, f"Deckel gerissen: {len(aus.encode())} B"
        assert "Weitere einschlaegige Policies" in aus
        assert "p5.md" in aus, "was nicht passt, muss wenigstens benannt werden"
        assert "Policy Nummer 0" in aus, "Positivkontrolle: etwas kommt durch"


# ── Fail-open ──────────────────────────────────────────────────────────────


class TestFailOpen:
    @pytest.mark.parametrize("eingabe", ["", "kein json", "[]", "null"])
    def test_should_exit_zero_on_broken_input(
        self, policies: Path, eingabe: str
    ) -> None:
        fertig = subprocess.run(
            [sys.executable, str(HOOK)],
            input=eingabe,
            capture_output=True,
            text=True,
            env={"POLICY_DIR": str(policies), "PATH": "/usr/bin:/bin"},
        )
        assert fertig.returncode == 0
        assert fertig.stdout == ""

    def test_should_stay_silent_when_the_policy_dir_is_missing(
        self, tmp_path: Path
    ) -> None:
        assert _lauf("ein fehler", tmp_path / "gibtsnicht") == ""
