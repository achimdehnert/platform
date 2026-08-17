"""Tests fuer tools/claude-hooks/artefakt_budget.py (Stop-Hook, Retro 8ed6a2).

Der Hook macht `scope-checkpoint-not-durably-recorded` (x9, hoechster Zaehler
im Retro-Register) ausfuehrbar: ab N per `gh pr create` angelegten PRs erinnert
er an den Scope-Checkpoint. Beide Richtungen gedeckt — ein Reminder, der immer
oder nie feuert, waere dasselbe Nichts wie die unverdrahtete Notiz.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HOOK = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "claude-hooks"
    / "artefakt_budget.py"
)


def _aufruf(tid: str, cmd: str) -> str:
    """assistant-Zeile mit einem Bash-tool_use."""
    return json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": tid,
                        "input": {"command": cmd},
                    }
                ]
            },
        }
    )


def _ergebnis(tid: str, text: str) -> str:
    """user-Zeile mit dem tool_result zu `tid` — der BELEG der Anlage.

    Ohne diese Zeile gibt es kein Artefakt: der Hook zaehlt seit 2026-08-17
    die zurueckgemeldete URL, nicht das Kommando (Prio 4 — 8 gemeldet vs. 37
    tatsaechlich). Ein Transkript aus lauter Kommandos ohne Ergebnisse ist
    deshalb kein gueltiger Drill mehr, sondern die alte Fehlmessung selbst.
    """
    return json.dumps(
        {
            "type": "user",
            "isMeta": True,
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": tid, "content": text}
                ]
            },
        }
    )


def _pr_url(nr: int, repo: str = "achimdehnert/platform") -> str:
    return f"https://github.com/{repo}/pull/{nr}"


def _issue_url(nr: int, repo: str = "achimdehnert/platform") -> str:
    return f"https://github.com/{repo}/issues/{nr}"


def _transcript(tmp_path: Path, pr_creates: int, issue_creates: int = 0) -> Path:
    """Synthetisches Transkript: N belegte PR-Anlagen, M belegte Issue-Anlagen."""
    p = tmp_path / "session.jsonl"
    zeilen = []
    for i in range(pr_creates):
        zeilen.append(_aufruf(f"t{i}", f'gh pr create --title "x{i}"'))
        zeilen.append(_ergebnis(f"t{i}", _pr_url(100 + i)))
    for i in range(issue_creates):
        zeilen.append(_aufruf(f"i{i}", "gh issue create --title y"))
        zeilen.append(_ergebnis(f"i{i}", _issue_url(900 + i)))
    # Rauschen, das NICHT zaehlen darf: view/merge/list + Text, der create
    # erwaehnt. Das view-Ergebnis traegt bewusst eine echte PR-URL — genau
    # daran wuerde eine reine URL-Zaehlung ohne Absichts-Bindung scheitern.
    zeilen.append(_aufruf("n1", "gh pr view 7 && gh pr merge 7"))
    zeilen.append(_ergebnis("n1", f"state OPEN {_pr_url(7)}"))
    zeilen.append(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "wir koennten gh pr create nutzen"}
                    ]
                },
            }
        )
    )
    p.write_text("\n".join(zeilen) + "\n")
    return p


def _fahre(
    tmp_path: Path,
    transcript: Path,
    *,
    budget: str = "4",
    session: str = "test",
) -> subprocess.CompletedProcess[str]:
    event = {"transcript_path": str(transcript), "session_id": session}
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "ARTEFAKT_BUDGET_PRS": budget,
            "TMPDIR": str(tmp_path),
            # PFLICHT, nicht Kosmetik: der Hook laeuft hier als Subprozess mit
            # ersetzter Umgebung — `PYTEST_CURRENT_TEST` kommt dort nie an, die
            # pytest-Sperre in gate_hits greift also NICHT. Ohne diese Zeile
            # schreibt jeder Drill in das echte Protokoll und die FP-Auswertung
            # urteilt wieder ueber sich selbst (Realfall 2026-08-15: 212 von
            # 212 Treffern stammten aus pytest). HOME ist der zweite Riegel.
            "GATE_HITS_DATEI": str(tmp_path / "gate-hits.jsonl"),
            "HOME": str(tmp_path),
        },
    )


def _hits(tmp_path: Path) -> list[dict]:
    p = tmp_path / "gate-hits.jsonl"
    if not p.exists():
        return []
    return [json.loads(z) for z in p.read_text().splitlines() if z.strip()]


def _owner_nachricht(text: str = "mach weiter") -> str:
    return json.dumps({"type": "user", "message": {"content": text}})


def _modul():
    """Hook als Modul laden — fuer die Messfunktionen, die kein Subprozess braucht.

    Import erst hier, damit die Subprozess-Tests oben unabhaengig davon bleiben.
    """
    import sys

    sys.path.insert(0, str(HOOK.parent))
    import artefakt_budget

    return artefakt_budget


def test_should_stay_silent_below_budget(tmp_path: Path) -> None:
    e = _fahre(tmp_path, _transcript(tmp_path, pr_creates=3))
    assert e.returncode == 0
    assert e.stdout.strip() == "", e.stdout


def test_should_fire_at_budget(tmp_path: Path) -> None:
    """DER Zielfall — 4 PRs erreichen die Schwelle."""
    e = _fahre(tmp_path, _transcript(tmp_path, pr_creates=4, issue_creates=2))
    assert e.returncode == 0
    out = json.loads(e.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "4 PRs" in ctx
    assert "2 Issues" in ctx
    assert "Scope-Checkpoint" in ctx


def test_should_fire_once_per_count_not_every_stop(tmp_path: Path) -> None:
    """Ein Reminder, der bei jedem Stop feuert, ist das Rauschen, das er
    verhindern soll (Realfall Scanner 2026-07-03: 9 Blocks in Folge)."""
    t = _transcript(tmp_path, pr_creates=4)
    first = _fahre(tmp_path, t, session="einmal")
    second = _fahre(tmp_path, t, session="einmal")
    assert first.stdout.strip() != ""
    assert second.stdout.strip() == "", second.stdout


def test_should_fire_again_when_count_grows(tmp_path: Path) -> None:
    t4 = _transcript(tmp_path, pr_creates=4)
    _fahre(tmp_path, t4, session="wachs")
    t5 = _transcript(tmp_path, pr_creates=5)
    e = _fahre(tmp_path, t5, session="wachs")
    assert "5 PRs" in e.stdout


def test_should_not_count_view_merge_or_prose(tmp_path: Path) -> None:
    """Nur echte create-Kommandos zaehlen — nicht view/merge/list und nicht
    Prosa, die das Kommando erwaehnt (die Fixture enthaelt beides)."""
    e = _fahre(tmp_path, _transcript(tmp_path, pr_creates=0, issue_creates=0))
    assert e.stdout.strip() == ""


def test_should_disable_on_zero_budget(tmp_path: Path) -> None:
    e = _fahre(tmp_path, _transcript(tmp_path, pr_creates=9), budget="0")
    assert e.returncode == 0
    assert e.stdout.strip() == ""


def test_should_record_hit_when_firing(tmp_path: Path) -> None:
    """Ohne Spur auf Platte laesst sich der Melder nicht kalibrieren.

    Realfall 2026-08-15: er loeste neunmal aus, und die Bilanz musste aus dem
    Sitzungsverlauf rekonstruiert werden, weil er nichts schrieb.
    """
    _fahre(tmp_path, _transcript(tmp_path, pr_creates=4, issue_creates=2))
    treffer = _hits(tmp_path)
    assert len(treffer) == 1, treffer
    assert treffer[0]["slug"] == "artefakt-budget-schwelle-erreicht"
    assert treffer[0]["modus"] == "advisory"
    assert "prs=4" in treffer[0]["marker"]
    assert "prs_seit_owner=" in treffer[0]["marker"]


def test_should_not_record_below_budget(tmp_path: Path) -> None:
    _fahre(tmp_path, _transcript(tmp_path, pr_creates=3))
    assert _hits(tmp_path) == []


def test_should_isolate_drill_from_real_protocol() -> None:
    """Der Drill darf das echte Protokoll nie erreichen — die pytest-Sperre in
    gate_hits greift bei diesem Hook NICHT, weil er als Subprozess mit
    ersetzter Umgebung laeuft. Diese Pruefung haelt die Isolation fest, damit
    sie nicht bei der naechsten Umbau-Runde still verschwindet."""
    import inspect

    quelle = inspect.getsource(_fahre)
    assert '"GATE_HITS_DATEI"' in quelle
    assert '"HOME"' in quelle


def test_should_count_prs_since_last_owner_message(tmp_path: Path) -> None:
    """Der Runaway-Indikator: PRs seit der letzten Nachricht des Menschen.

    Die absolute PR-Zahl unterscheidet Auftrag und Kette nicht — am 2026-08-15
    stand sie an allen neun Ausloesepunkten hoch, waehrend `prs_seit_owner`
    konstant 1 war (jede Eskalation einzeln freigegeben).
    """
    ab = _modul()
    t = tmp_path / "mit_owner.jsonl"
    basis = _transcript(tmp_path, pr_creates=5).read_text().splitlines()
    # Owner meldet sich nach dem dritten PR -> nur die letzten zwei zaehlen.
    # Je PR zwei Zeilen (Aufruf + Ergebnis), der Schnitt liegt also bei 6 —
    # bei 3 fiele der Beleg des dritten PR hinter die Owner-Nachricht.
    t.write_text("\n".join(basis[:6] + [_owner_nachricht()] + basis[6:]) + "\n")
    assert ab.messe_kontext(t)["prs_seit_owner"] == 2


def test_should_ignore_tool_results_as_owner_messages(tmp_path: Path) -> None:
    """`user`-Eintraege tragen auch Tool-Ergebnisse und System-Erinnerungen.
    Zaehlte man die mit, waere der Wert immer 0 und der Melder wieder blind."""
    ab = _modul()
    t = tmp_path / "nur_tool.jsonl"
    basis = _transcript(tmp_path, pr_creates=5).read_text().splitlines()
    rauschen = [
        json.dumps({"type": "user", "message": {"content": [{"type": "tool_result"}]}}),
        json.dumps(
            {"type": "user", "isMeta": True, "message": {"content": "erinnerung"}}
        ),
    ]
    t.write_text("\n".join(basis[:6] + rauschen + basis[6:]) + "\n")
    assert ab.messe_kontext(t)["prs_seit_owner"] == 5


def test_should_measure_repos_and_prod_step(tmp_path: Path) -> None:
    ab = _modul()
    t = tmp_path / "kontext.jsonl"
    t.write_text(
        "\n".join(
            [
                json.dumps(
                    {"type": "pr-link", "prRepository": "achimdehnert/risk-hub"}
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "cwd": "/home/devuser/github/platform/tools",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "input": {"command": "bash deploy.sh prod"},
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "input": {
                                        "command": "gh pr view 1 -R ttz-lif/ttz-hub"
                                    },
                                }
                            ]
                        },
                    }
                ),
            ]
        )
        + "\n"
    )
    k = ab.messe_kontext(t)
    assert k["repos"] == 3, k
    assert k["prod"] == 1


def test_should_not_flag_merge_as_prod_step(tmp_path: Path) -> None:
    """`gh pr merge` ist KEIN Prod-Marker — ob ein Merge deployt, haengt am
    Repo. Das waere geraten, nicht gemessen."""
    ab = _modul()
    t = _transcript(tmp_path, pr_creates=4)  # enthaelt `gh pr merge 7`
    assert ab.messe_kontext(t)["prod"] == 0


# --------------------------------------------------------------------------
# Die drei gemessenen Fehlmessungen der Kommando-Zaehlung (Prio 4, 2026-08-17).
# Am 17.08. meldete der Melder 8 PRs, tatsaechlich waren es 37. Jeder Test hier
# ist einer der drei Wege, auf denen die Zahl entstand — plus zwei Faelle, die
# der neue Weg nicht neu kaputt machen darf.
# --------------------------------------------------------------------------


def test_should_count_every_pr_from_a_single_loop_command(tmp_path: Path) -> None:
    """Eine Schleife legt N PRs an und steht EINMAL im Kommando.

    Der teuerste der drei Fehler: 17 PRs aus einer Schleife zaehlten als eins —
    der Melder war genau bei der Massenaktion blind, wegen der es ihn gibt.
    """
    ab = _modul()
    t = tmp_path / "schleife.jsonl"
    urls = " ".join(_pr_url(n) for n in (11, 12, 13, 14, 15))
    t.write_text(
        "\n".join(
            [
                _aufruf("s1", "for r in a b c d e; do gh pr create -R o/$r -t x; done"),
                _ergebnis("s1", urls),
            ]
        )
        + "\n"
    )
    assert ab.zaehle_artefakte(t) == (5, 0)


def test_should_count_prs_created_via_rest_api(tmp_path: Path) -> None:
    """`gh api .../pulls -X POST` enthaelt kein `gh pr create` und zaehlte gar
    nicht — der Weg, den man nimmt, wenn GraphQL 503 wirft (Realfall 17.08.)."""
    ab = _modul()
    t = tmp_path / "api.jsonl"
    t.write_text(
        "\n".join(
            [
                _aufruf("a1", "gh api repos/o/r/pulls -X POST --input -"),
                _ergebnis("a1", json.dumps({"html_url": _pr_url(57, "o/r")})),
            ]
        )
        + "\n"
    )
    assert ab.zaehle_artefakte(t) == (1, 0)


def test_should_not_count_a_code_search_for_the_pattern(tmp_path: Path) -> None:
    """Die Gegenrichtung: eine blosse Codesuche nach dem Muster erhoehte den
    Zaehler um 1. Ihr Ergebnis traegt Quellzeilen, keine Artefakt-URL."""
    ab = _modul()
    t = tmp_path / "suche.jsonl"
    t.write_text(
        "\n".join(
            [
                _aufruf("g1", "grep -rn 'gh pr create' tools/"),
                _ergebnis(
                    "g1", "tools/claude-hooks/artefakt_budget.py:70: gh pr create"
                ),
            ]
        )
        + "\n"
    )
    assert ab.zaehle_artefakte(t) == (0, 0)


def test_should_not_count_a_failed_creation_attempt(tmp_path: Path) -> None:
    """Ein gescheiterter Versuch legt nichts an. In dieser Sitzung liefen zwei
    `gh pr create` in HTTP 503 — die alte Zaehlung haette beide als PR gebucht."""
    ab = _modul()
    t = tmp_path / "fehl.jsonl"
    t.write_text(
        "\n".join(
            [
                _aufruf("f1", "gh pr create --title x"),
                _ergebnis("f1", "HTTP 503: No server is currently available"),
            ]
        )
        + "\n"
    )
    assert ab.zaehle_artefakte(t) == (0, 0)


def test_should_not_count_a_comment_as_a_new_issue(tmp_path: Path) -> None:
    """`gh api .../issues/40/comments -X POST` ist ein Kommentar, kein Issue —
    und sein html_url sieht dem eines Issues zum Verwechseln aehnlich."""
    ab = _modul()
    t = tmp_path / "kommentar.jsonl"
    t.write_text(
        "\n".join(
            [
                _aufruf("k1", "gh api repos/o/r/issues/40/comments -X POST -f body=x"),
                _ergebnis(
                    "k1",
                    "https://github.com/o/r/issues/40#issuecomment-5301524622",
                ),
            ]
        )
        + "\n"
    )
    assert ab.zaehle_artefakte(t) == (0, 0)


def test_should_count_the_same_pr_url_only_once(tmp_path: Path) -> None:
    """Idempotenz: derselbe PR, zweimal belegt, bleibt ein Artefakt. Sonst
    zaehlt ein Wiederholungslauf nach einem Teilfehlschlag doppelt."""
    ab = _modul()
    t = tmp_path / "doppelt.jsonl"
    t.write_text(
        "\n".join(
            [
                _aufruf("d1", "gh pr create -t x"),
                _ergebnis("d1", _pr_url(42)),
                _aufruf("d2", "gh pr create -t x"),
                _ergebnis("d2", f"a pull request already exists {_pr_url(42)}"),
            ]
        )
        + "\n"
    )
    assert ab.zaehle_artefakte(t) == (1, 0)


def test_should_never_fail_on_garbage_stdin(tmp_path: Path) -> None:
    """Vertrag: ein Hook-Fehler darf Claude NIE blocken — immer exit 0."""
    e = subprocess.run(
        ["python3", str(HOOK)],
        input="kein json {",
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp_path)},
    )
    assert e.returncode == 0
