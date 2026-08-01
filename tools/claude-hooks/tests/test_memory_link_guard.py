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
import subprocess
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


# --- Vorbedingung ------------------------------------------------------------


def test_should_extract_the_memory_dir_from_a_porcelain_line(monkeypatch, tmp_path):
    mem = tmp_path / "projects" / "projekt-a" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess, "run",
        lambda *a, **k: FakeLauf(" M projects/projekt-a/memory/feedback_x.md\n"),
    )

    assert guard.geaenderte_memory_dirs() == [mem]


def test_should_handle_a_rename_line(monkeypatch, tmp_path):
    mem = tmp_path / "projects" / "projekt-a" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess, "run",
        lambda *a, **k: FakeLauf("R  projects/projekt-a/memory/a.md -> projects/projekt-a/memory/b.md\n"),
    )

    assert guard.geaenderte_memory_dirs() == [mem]


def test_should_ignore_changes_outside_memory_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess, "run",
        lambda *a, **k: FakeLauf(" M projects/projekt-a/tool-results/x.txt\n M settings.json\n"),
    )

    assert guard.geaenderte_memory_dirs() == []


def test_should_return_empty_when_git_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(guard.subprocess, "run", lambda *a, **k: FakeLauf("", returncode=128))

    assert guard.geaenderte_memory_dirs() == []


def test_should_return_empty_when_git_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)

    def explodiert(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(guard.subprocess, "run", explodiert)

    assert guard.geaenderte_memory_dirs() == []


def test_should_deduplicate_several_files_of_one_dir(monkeypatch, tmp_path):
    mem = tmp_path / "projects" / "projekt-a" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setattr(guard, "CLAUDE_REPO", tmp_path)
    monkeypatch.setattr(
        guard.subprocess, "run",
        lambda *a, **k: FakeLauf(
            " M projects/projekt-a/memory/a.md\n?? projects/projekt-a/memory/b.md\n"
        ),
    )

    assert guard.geaenderte_memory_dirs() == [mem]


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
        guard.subprocess, "run", lambda *a, **k: FakeLauf(json.dumps(bericht), returncode=1)
    )

    meldungen = guard.pruefe([tmp_path])

    assert len(meldungen) == 1
    assert "dead-wikilink" in meldungen[0] and "forward-ref" not in meldungen[0]


def test_should_stay_silent_on_a_tool_error(monkeypatch, tmp_path):
    monkeypatch.setattr(guard.subprocess, "run", lambda *a, **k: FakeLauf("", returncode=2))

    assert guard.pruefe([tmp_path]) == []


def test_should_survive_unparsable_checker_output(monkeypatch, tmp_path):
    monkeypatch.setattr(guard.subprocess, "run", lambda *a, **k: FakeLauf("kein json", returncode=1))

    assert guard.pruefe([tmp_path]) == []


# --- main(): darf unter keinen Umstaenden blockieren -------------------------


def test_should_exit_0_and_stay_silent_when_nothing_was_written(monkeypatch, capsys, stdin_leer):
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: [])

    assert guard.main() == 0
    assert capsys.readouterr().out == ""


def test_should_emit_additional_context_on_a_finding(monkeypatch, capsys, stdin_leer, tmp_path):
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: [tmp_path])
    monkeypatch.setattr(guard, "pruefe", lambda d: ["  dead-wikilink   a.md   [[weg]]"])

    assert guard.main() == 0
    ausgabe = json.loads(capsys.readouterr().out)
    text = ausgabe["hookSpecificOutput"]["additionalContext"]
    assert "memory-link-guard" in text
    assert "[[weg]]" in text
    assert "memory_forward_refs.tsv" in text


def test_should_exit_0_on_broken_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("kein json {{{"))
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: [])

    assert guard.main() == 0


def test_should_exit_0_when_the_checker_is_absent(monkeypatch, stdin_leer, tmp_path):
    monkeypatch.setattr(guard, "PRUEFER", tmp_path / "gibtsnicht.py")

    assert guard.main() == 0


def test_should_stay_silent_when_only_forward_refs_are_found(monkeypatch, capsys, stdin_leer, tmp_path):
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: [tmp_path])
    monkeypatch.setattr(guard, "pruefe", lambda d: [])

    assert guard.main() == 0
    assert capsys.readouterr().out == ""


def test_should_not_call_the_checker_when_precondition_is_empty(monkeypatch, stdin_leer):
    """Die Vorbedingung ist der ganze Punkt: kein Scan ohne Schreibvorgang."""
    aufrufe = []
    monkeypatch.setattr(guard, "geaenderte_memory_dirs", lambda: [])
    monkeypatch.setattr(guard, "pruefe", lambda d: aufrufe.append(d) or [])

    guard.main()

    assert aufrufe == []
