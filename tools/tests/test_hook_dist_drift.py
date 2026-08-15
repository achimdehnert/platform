"""Drill für tools/hook-dist-drift.sh (platform#1989 Schritt 1).

Der Melder existiert, weil eine hand-verteilte Kopie stumm von ihrer Quelle
abdriftet: am 2026-08-15 fehlte im aktiven `gate_hits.py` die pytest-Sperre aus
#1986 — der ganze Zweck jenes PRs — ohne dass irgendein Check rot wurde.

Treffer und Nicht-Treffer gleichberechtigt: ein Melder, der jede nicht verteilte
Quelldatei als Befund meldet, wird als Lärm abgeschaltet und schützt dann nichts.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

_SKRIPT = pathlib.Path(__file__).resolve().parents[2] / "tools" / "hook-dist-drift.sh"


def _lauf(tmp_path, *args, quelle: dict, aktiv: dict | None):
    src = tmp_path / "quelle"
    src.mkdir()
    for name, inhalt in quelle.items():
        (src / name).write_text(inhalt, encoding="utf-8")

    env = {"HOOK_SRC_DIR": str(src), "PATH": "/usr/bin:/bin"}
    if aktiv is None:
        env["CLAUDE_HOOKS_DIR"] = str(tmp_path / "gibtsnicht")
    else:
        dst = tmp_path / "aktiv"
        dst.mkdir()
        for name, inhalt in aktiv.items():
            (dst / name).write_text(inhalt, encoding="utf-8")
        env["CLAUDE_HOOKS_DIR"] = str(dst)

    fertig = subprocess.run(
        ["bash", str(_SKRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    return fertig.returncode, fertig.stdout, env.get("CLAUDE_HOOKS_DIR")


class TestBefund:
    def test_should_report_drift_when_the_active_copy_differs(self, tmp_path):
        rc, aus, _ = _lauf(
            tmp_path,
            "--quiet",
            quelle={"a.py": "neu\n"},
            aktiv={"a.py": "alt\n"},
        )
        assert "RESULT: DRIFT" in aus
        assert "a.py" in aus
        assert rc == 1, "Drift muss einen Fehl-Exit tragen, sonst uebersieht ihn jeder Aufrufer"

    def test_should_name_every_drifted_file_not_just_count_them(self, tmp_path):
        """Eine Zahl allein faellt niemandem auf, wenn sie waechst (Lehre 0.7.1)."""
        _, aus, _ = _lauf(
            tmp_path,
            "--quiet",
            quelle={"a.py": "neu\n", "b.sh": "neu\n"},
            aktiv={"a.py": "alt\n", "b.sh": "auch alt\n"},
        )
        assert "a.py" in aus and "b.sh" in aus


class TestKeinFehlalarm:
    def test_should_pass_when_every_active_copy_matches(self, tmp_path):
        rc, aus, _ = _lauf(
            tmp_path,
            "--quiet",
            quelle={"a.py": "gleich\n"},
            aktiv={"a.py": "gleich\n"},
        )
        assert "RESULT: OK" in aus
        assert rc == 0

    def test_should_not_treat_an_undistributed_source_file_as_drift(self, tmp_path):
        """Nicht jeder Hook im Repo gehoert in den aktiven Pfad — manche sind
        Bibliothek, manche laufen nur in CI. Wuerde das als Befund zaehlen, waere
        der Melder ab Tag 1 dauerrot und damit wertlos."""
        rc, aus, _ = _lauf(
            tmp_path,
            "--quiet",
            quelle={"a.py": "gleich\n", "nur_im_repo.py": "x\n"},
            aktiv={"a.py": "gleich\n"},
        )
        assert "RESULT: OK" in aus
        assert rc == 0

    def test_should_still_count_undistributed_files_so_they_stay_visible(self, tmp_path):
        """Kein Befund heisst nicht unsichtbar — sonst waere 'gebaut, aber nie
        verteilt' genau die Luecke, die dieser Melder schliessen soll."""
        _, aus, _ = _lauf(
            tmp_path,
            "--quiet",
            quelle={"a.py": "gleich\n", "nur_im_repo.py": "x\n"},
            aktiv={"a.py": "gleich\n"},
        )
        assert "1 Quelldatei(en) nicht verteilt" in aus

    def test_should_ignore_tests_and_pycache(self, tmp_path):
        """Nur die oberste Ebene zaehlt; tests/ gehoert nie in den aktiven Pfad."""
        src = tmp_path / "quelle"
        (src / "tests").mkdir(parents=True)
        (src / "a.py").write_text("gleich\n", encoding="utf-8")
        (src / "tests" / "test_a.py").write_text("egal\n", encoding="utf-8")
        dst = tmp_path / "aktiv"
        dst.mkdir()
        (dst / "a.py").write_text("gleich\n", encoding="utf-8")

        fertig = subprocess.run(
            ["bash", str(_SKRIPT), "--quiet"],
            capture_output=True,
            text=True,
            env={
                "HOOK_SRC_DIR": str(src),
                "CLAUDE_HOOKS_DIR": str(dst),
                "PATH": "/usr/bin:/bin",
            },
        )
        assert "RESULT: OK" in fertig.stdout
        assert "test_a.py" not in fertig.stdout


class TestUngeprueft:
    def test_should_say_ungeprueft_when_the_active_path_is_missing(self, tmp_path):
        """Ein fehlendes Zielverzeichnis ist kein gruener Zustand — aber auch kein
        Drift-Befund. Beides zu verwechseln waere die Falle aus
        🌀 feedback_fetch_failure_is_not_a_green_state."""
        rc, aus, _ = _lauf(tmp_path, "--quiet", quelle={"a.py": "x\n"}, aktiv=None)
        assert "RESULT: UNGEPRUEFT" in aus
        assert "RESULT: OK" not in aus
        assert rc == 0


class TestSync:
    def test_should_repair_drift_and_keep_a_backup_of_what_ran(self, tmp_path):
        rc, aus, dst = _lauf(
            tmp_path,
            "--sync",
            "--quiet",
            quelle={"a.py": "neu\n"},
            aktiv={"a.py": "alt\n"},
        )
        ziel = pathlib.Path(dst)
        assert (ziel / "a.py").read_text(encoding="utf-8") == "neu\n"
        assert "RESULT: OK" in aus
        assert rc == 0
        sicherungen = list(ziel.glob("a.py.bak-*"))
        assert sicherungen, "die alte Kopie ist der einzige Zeuge dessen, was lief"
        assert sicherungen[0].read_text(encoding="utf-8") == "alt\n"


@pytest.mark.parametrize("arg", ["--kaputt", "-x"])
def test_should_refuse_unknown_arguments(tmp_path, arg):
    rc, _, _ = _lauf(tmp_path, arg, quelle={"a.py": "x\n"}, aktiv={"a.py": "x\n"})
    assert rc == 64
