"""Tests fuer den memory-link-guard Stop-Hook.

Die teure Fehlrichtung ist hier ein Hook, der blockiert oder abstuerzt: er laeuft
nach JEDER Antwort. Deshalb pruefen die Faelle unten vor allem, dass er unter
jeder Stoerung mit Exit 0 endet — kaputtes stdin, fehlender Pruefer, git ohne
Antwort — und dass die Vorbedingung wirklich greift, damit er im Normalfall nach
einem git-Aufruf fertig ist.
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "memory_link_guard.py"
_spec = importlib.util.spec_from_file_location("memory_link_guard", _SRC)
guard = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = guard
_spec.loader.exec_module(guard)


class FakeLauf:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


@pytest.fixture()
def stdin_leer(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))


@pytest.fixture(autouse=True)
def _merker_isolieren(tmp_path, monkeypatch):
    """Die Entprellungs-Datei je Test eigen — sonst faerbt ein Lauf den naechsten.

    Ohne diese Naht schriebe jeder Drill in den echten Temp-Ordner des
    Entwicklers und der zweite Testlauf saehe den Abdruck des ersten.
    """
    monkeypatch.setattr(
        guard, "_abdruck_datei", lambda sid: tmp_path / f"merker_{sid or 'na'}.txt"
    )


# --- Vorbedingung ------------------------------------------------------------


def test_should_extract_the_memory_dir_from_a_porcelain_line(monkeypatch, tmp_path):
    mem = tmp_path / "projects" / "projekt-a" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: FakeLauf(" M projects/projekt-a/memory/feedback_x.md\n"),
    )

    assert guard.geaenderte_memory_dirs()[0] == [mem]


def test_should_handle_a_rename_line(monkeypatch, tmp_path):
    mem = tmp_path / "projects" / "projekt-a" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: FakeLauf(
            "R  projects/projekt-a/memory/a.md -> projects/projekt-a/memory/b.md\n"
        ),
    )

    assert guard.geaenderte_memory_dirs()[0] == [mem]


def test_should_ignore_changes_outside_memory_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: FakeLauf(
            " M projects/projekt-a/tool-results/x.txt\n M settings.json\n"
        ),
    )

    assert guard.geaenderte_memory_dirs()[0] == []


def test_should_return_empty_when_git_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess, "run", lambda *a, **k: FakeLauf("", returncode=128)
    )

    assert guard.geaenderte_memory_dirs()[0] == []


def test_should_return_empty_when_git_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)

    def explodiert(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(guard.subprocess, "run", explodiert)

    assert guard.geaenderte_memory_dirs()[0] == []


def test_should_deduplicate_several_files_of_one_dir(monkeypatch, tmp_path):
    mem = tmp_path / "projects" / "projekt-a" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: FakeLauf(
            " M projects/projekt-a/memory/a.md\n?? projects/projekt-a/memory/b.md\n"
        ),
    )

    assert guard.geaenderte_memory_dirs()[0] == [mem]


# --- Auswertung des Pruefer-Berichts ----------------------------------------


def test_should_report_only_hard_findings(monkeypatch, tmp_path):
    bericht = {
        "details": [
            {
                "verzeichnis": str(tmp_path),
                "funde": [
                    {"art": "dead-wikilink", "datei": "a.md", "detail": "[[weg]]"},
                    {"art": "forward-ref", "datei": "b.md", "detail": "[[geplant]]"},
                ],
            }
        ]
    }
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: FakeLauf(json.dumps(bericht), returncode=1),
    )

    meldungen, fremd = guard.pruefe([tmp_path], {"a.md"})

    assert len(meldungen) == 1
    assert "dead-wikilink" in meldungen[0] and "forward-ref" not in meldungen[0]


def test_should_stay_silent_on_a_tool_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        guard.subprocess, "run", lambda *a, **k: FakeLauf("", returncode=2)
    )

    assert guard.pruefe([tmp_path], {"a.md"}) == ([], 0)


def test_should_survive_unparsable_checker_output(monkeypatch, tmp_path):
    monkeypatch.setattr(
        guard.subprocess, "run", lambda *a, **k: FakeLauf("kein json", returncode=1)
    )

    assert guard.pruefe([tmp_path], {"a.md"}) == ([], 0)


# --- main(): darf unter keinen Umstaenden blockieren -------------------------


def test_should_exit_0_and_stay_silent_when_nothing_was_written(
    monkeypatch, capsys, stdin_leer
):
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: ([], set()))

    assert guard.main() == 0
    assert capsys.readouterr().out == ""


def test_should_emit_additional_context_on_a_finding(
    monkeypatch, capsys, stdin_leer, tmp_path
):
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: ([tmp_path], {"a.md"}))
    monkeypatch.setattr(
        guard, "pruefe", lambda d, g: (["  dead-wikilink   a.md   [[weg]]"], 0)
    )

    assert guard.main() == 0
    ausgabe = json.loads(capsys.readouterr().out)
    text = ausgabe["hookSpecificOutput"]["additionalContext"]
    assert "memory-link-guard" in text
    assert "[[weg]]" in text
    assert "memory_forward_refs.tsv" in text


def test_should_exit_0_on_broken_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("kein json {{{"))
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: ([], set()))

    assert guard.main() == 0


def test_should_exit_0_when_the_checker_is_absent(monkeypatch, stdin_leer, tmp_path):
    monkeypatch.setattr(guard, "PRUEFER", tmp_path / "gibtsnicht.py")

    assert guard.main() == 0


def test_should_stay_silent_when_only_forward_refs_are_found(
    monkeypatch, capsys, stdin_leer, tmp_path
):
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: ([tmp_path], {"a.md"}))
    monkeypatch.setattr(guard, "pruefe", lambda d, g: ([], 0))

    assert guard.main() == 0
    assert capsys.readouterr().out == ""


def test_should_not_call_the_checker_when_precondition_is_empty(
    monkeypatch, stdin_leer
):
    """Die Vorbedingung ist der ganze Punkt: kein Scan ohne Schreibvorgang."""
    aufrufe = []
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: ([], set()))
    monkeypatch.setattr(guard, "pruefe", lambda d, g: (aufrufe.append(d), ([], 0))[1])

    guard.main()

    assert aufrufe == []


# --- Zuschreibung: nur was dieser Zug angefasst hat --------------------------
#
# Realfall 2026-08-02: der Melder las das ganze Verzeichnis und schrieb ALLE
# harten Funde dem meldenden Zug zu — 8 Funde in 3 Dateien, die er nie geoeffnet
# hatte. Der Prueferlauf bleibt verzeichnisweit (anders geht es nicht), die
# Meldung nicht.


def _bericht(tmp_path, *dateien):
    return {
        "details": [
            {
                "verzeichnis": str(tmp_path),
                "funde": [
                    {"art": "dead-wikilink", "datei": d, "detail": "[[weg]]"}
                    for d in dateien
                ],
            }
        ]
    }


def test_should_report_only_files_this_turn_touched(monkeypatch, tmp_path):
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: FakeLauf(
            json.dumps(_bericht(tmp_path, "meine.md", "fremde.md")), returncode=1
        ),
    )

    eigene, fremd = guard.pruefe([tmp_path], {"meine.md"})

    assert len(eigene) == 1
    assert "meine.md" in eigene[0]
    assert fremd == 1


def test_should_count_foreign_findings_instead_of_dropping_them(monkeypatch, tmp_path):
    """Stillschweigen waere die naechste Unehrlichkeit — zaehlen, nicht schlucken."""
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: FakeLauf(
            json.dumps(_bericht(tmp_path, "a.md", "b.md", "c.md")), returncode=1
        ),
    )

    eigene, fremd = guard.pruefe([tmp_path], {"a.md"})

    assert (len(eigene), fremd) == (1, 2)


def test_should_stay_silent_when_only_foreign_files_have_findings(
    monkeypatch, capsys, stdin_leer, tmp_path
):
    """Kein eigener Fund heisst: dieser Zug hat nichts kaputtgemacht."""
    monkeypatch.setattr(
        guard, "geaenderte_memory_dirs", lambda: ([tmp_path], {"meine.md"})
    )
    monkeypatch.setattr(guard, "pruefe", lambda d, g: ([], 7))

    assert guard.main() == 0
    assert capsys.readouterr().out == ""


def test_should_mention_foreign_findings_as_separate_debt(
    monkeypatch, capsys, stdin_leer, tmp_path
):
    monkeypatch.setattr(
        guard, "geaenderte_memory_dirs", lambda: ([tmp_path], {"meine.md"})
    )
    monkeypatch.setattr(
        guard, "pruefe", lambda d, g: (["  dead-wikilink  meine.md"], 5)
    )

    guard.main()

    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"][
        "additionalContext"
    ]
    assert "5 harte(r) Fund(e)" in text
    assert "NICHT angefasst" in text


def test_should_not_add_the_debt_note_when_there_is_none(
    monkeypatch, capsys, stdin_leer, tmp_path
):
    """Gegenprobe: ohne fremde Funde darf der Nachsatz nicht erscheinen."""
    monkeypatch.setattr(
        guard, "geaenderte_memory_dirs", lambda: ([tmp_path], {"meine.md"})
    )
    monkeypatch.setattr(
        guard, "pruefe", lambda d, g: (["  dead-wikilink  meine.md"], 0)
    )

    guard.main()

    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"][
        "additionalContext"
    ]
    assert "NICHT angefasst" not in text


def test_should_collect_changed_filenames_next_to_dirs(monkeypatch, tmp_path):
    mem = tmp_path / "projects" / "projekt-a" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: FakeLauf(
            " M projects/projekt-a/memory/a.md\n?? projects/projekt-a/memory/b.md\n"
        ),
    )

    dirs, dateien = guard.geaenderte_memory_dirs()

    assert dirs == [mem]
    assert dateien == {"a.md", "b.md"}


# --- Entprellung gegen den Inhalt -------------------------------------------
#
# Gemessen 2026-09-02 (platform#2606): `git status` kostet 13 ms, der Pruefer
# dahinter ~685 ms — und er lief bei JEDEM Stop, solange unter memory/ ueberhaupt
# etwas offen war, auch in Zuegen ohne Schreibvorgang. Der zweite Gurt ist der
# Inhalts-Abdruck. Beide Richtungen sind gleich wichtig: er darf nicht doppelt
# laufen, aber er MUSS laufen, sobald sich ein Byte aendert.


def _fenster(monkeypatch, tmp_path, laeufe):
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: ([tmp_path], {"a.md"}))
    monkeypatch.setattr(guard, "pruefe", lambda d, g: (laeufe.append(d), ([], 0))[1])


def test_should_skip_the_checker_when_nothing_changed_since_the_last_run(
    monkeypatch, tmp_path
):
    (tmp_path / "a.md").write_text("gleich", encoding="utf-8")
    laeufe: list = []
    _fenster(monkeypatch, tmp_path, laeufe)

    for _ in range(3):
        monkeypatch.setattr(sys, "stdin", io.StringIO('{"session_id": "s1"}'))
        assert guard.main() == 0

    assert len(laeufe) == 1, "der Pruefer lief trotz unveraenderter Dateien erneut"


def test_should_run_the_checker_again_after_the_content_changed(monkeypatch, tmp_path):
    """Gegenprobe: die Entprellung darf keinen einzigen Fund verlieren."""
    ziel = tmp_path / "a.md"
    ziel.write_text("erst", encoding="utf-8")
    laeufe: list = []
    _fenster(monkeypatch, tmp_path, laeufe)

    monkeypatch.setattr(sys, "stdin", io.StringIO('{"session_id": "s1"}'))
    guard.main()
    ziel.write_text("dann", encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"session_id": "s1"}'))
    guard.main()

    assert len(laeufe) == 2


def test_should_not_let_a_touch_without_change_trigger_a_run(monkeypatch, tmp_path):
    """Gehasht wird der Inhalt, nicht die mtime (Memory `mtime_not_dirty`)."""
    ziel = tmp_path / "a.md"
    ziel.write_text("gleich", encoding="utf-8")
    laeufe: list = []
    _fenster(monkeypatch, tmp_path, laeufe)

    monkeypatch.setattr(sys, "stdin", io.StringIO('{"session_id": "s1"}'))
    guard.main()
    ziel.touch()
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"session_id": "s1"}'))
    guard.main()

    assert len(laeufe) == 1


def test_should_keep_the_fingerprint_per_session(monkeypatch, tmp_path):
    """Eine andere Sitzung darf nicht vom Merker der ersten stumm geschaltet werden."""
    (tmp_path / "a.md").write_text("gleich", encoding="utf-8")
    laeufe: list = []
    _fenster(monkeypatch, tmp_path, laeufe)

    for sid in ("s1", "s2"):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": sid})))
        guard.main()

    assert len(laeufe) == 2


# --- Ausgabe-Vertrag --------------------------------------------------------


def test_should_send_hook_event_name(monkeypatch, capsys, stdin_leer, tmp_path):
    """Ohne hookEventName verwirft Claude Code die Ausgabe — Schema-Fehler statt Hinweis."""
    monkeypatch.setattr(
        guard, "geaenderte_memory_dirs", lambda: ([tmp_path], {"meine.md"})
    )
    monkeypatch.setattr(
        guard, "pruefe", lambda d, g: (["  dead-wikilink  meine.md"], 0)
    )

    guard.main()

    ausgabe = json.loads(capsys.readouterr().out)
    assert ausgabe["hookSpecificOutput"]["hookEventName"] == "Stop"
