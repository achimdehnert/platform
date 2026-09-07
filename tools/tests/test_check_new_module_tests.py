"""Drill für tools/check_new_module_tests.py (untested-tool-module-green-gate).

Kernlogik ist git-frei (befunde_fuer arbeitet auf Pfadlisten + Dateibaum) —
der Drill baut Wegwerf-Baeume in tmp_path statt echte Diffs zu brauchen.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_new_module_tests as cnm  # noqa: E402


class TestIstPruefpflichtig:
    def test_should_flag_new_tools_module(self):
        assert cnm.ist_pruefpflichtig("tools/neues_werkzeug.py") is True

    def test_should_flag_new_scripts_module(self):
        assert cnm.ist_pruefpflichtig("scripts/checks/neuer_check.py") is True

    def test_should_ignore_test_files_init_conftest_and_tests_dirs(self):
        assert cnm.ist_pruefpflichtig("tools/tests/test_x.py") is False
        assert cnm.ist_pruefpflichtig("tools/test_x.py") is False
        assert cnm.ist_pruefpflichtig("tools/pkg/__init__.py") is False
        assert cnm.ist_pruefpflichtig("tools/conftest.py") is False

    def test_should_ignore_paths_outside_tools_and_scripts(self):
        # Bewusst KEIN realer Repo-Pfad: test_ci_trigger_covers_test_inputs liest
        # Pfad-Literale aus Testdateien und wuerde einen echten (z.B.
        # orchestrator_mcp/...) als Workflow-Eingabe werten (CI-Rot auf #1941).
        assert cnm.ist_pruefpflichtig("anderswo/nicht_geprueft.py") is False
        assert cnm.ist_pruefpflichtig("docs/adr/ADR-001.md") is False

    def test_should_ignore_non_python(self):
        assert cnm.ist_pruefpflichtig("tools/deploy.sh") is False


class TestHatTestSpur:
    def _baum(self, tmp_path, testdateien):
        for rel, inhalt in testdateien.items():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(inhalt, encoding="utf-8")
        return tmp_path

    def test_should_find_dedicated_test_file(self, tmp_path):
        root = self._baum(tmp_path, {"tools/tests/test_foo.py": ""})
        assert cnm.hat_test_spur("foo", root) is True

    def test_should_find_mention_in_suite_file(self, tmp_path):
        """Deckt Suiten ab, die mehrere Module testen (block_unformatted_push_suite)."""
        root = self._baum(
            tmp_path,
            {"tools/tests/test_suite.py": "import foo_modul  # drillt foo_modul"},
        )
        assert cnm.hat_test_spur("foo_modul", root) is True

    def test_should_miss_when_no_trace(self, tmp_path):
        root = self._baum(tmp_path, {"tools/tests/test_other.py": "nichts hier"})
        assert cnm.hat_test_spur("foo", root) is False


class TestBefundeFuer:
    def test_should_report_untested_new_module_and_pass_tested_one(self, tmp_path):
        (tmp_path / "tools" / "tests").mkdir(parents=True)
        (tmp_path / "tools" / "tests" / "test_getestet.py").write_text(
            "", encoding="utf-8"
        )
        befunde = cnm.befunde_fuer(
            ["tools/getestet.py", "tools/ungetestet.py", "docs/x.md"], tmp_path
        )
        assert befunde == ["tools/ungetestet.py"]

    def test_should_be_clean_without_new_modules(self, tmp_path):
        assert (
            cnm.befunde_fuer(["docs/adr/ADR-1.md", "tools/tests/test_a.py"], tmp_path)
            == []
        )


class TestMainExitVertrag:
    """0 sauber · 1 Befund (advisory) · 2 Werkzeugfehler (nie still)."""

    def _run(self, added, tmp_path):
        with patch.object(cnm, "hinzugefuegte_dateien", return_value=added):
            with patch.object(
                sys, "argv", ["x", "--range", "a...b", "--repo-root", str(tmp_path)]
            ):
                return cnm.main()

    def test_should_exit_0_when_clean(self, tmp_path):
        assert self._run([], tmp_path) == 0

    def test_should_exit_1_on_finding(self, tmp_path):
        assert self._run(["tools/neu_ohne_test.py"], tmp_path) == 1

    def test_should_exit_2_when_git_fails(self, tmp_path):
        """Fetch-/git-Fehler ist kein sauberer Zustand."""
        assert self._run(None, tmp_path) == 2


class TestHinzugefuegteDateien:
    def test_should_return_none_on_git_error(self):
        out = subprocess.CompletedProcess([], 128, "", "fatal")
        with patch.object(cnm.subprocess, "run", return_value=out):
            assert cnm.hinzugefuegte_dateien("a...b", Path(".")) is None

    def test_should_parse_name_only_output(self):
        out = subprocess.CompletedProcess([], 0, "tools/a.py\n\nscripts/b.py\n", "")
        with patch.object(cnm.subprocess, "run", return_value=out):
            assert cnm.hinzugefuegte_dateien("a...b", Path(".")) == [
                "tools/a.py",
                "scripts/b.py",
            ]


class TestSpurZweiAlsBezug:
    """Rev 2 (platform#2374): Spur 2 verlangt einen BEZUG, keine blosse Erwaehnung.

    Positivkontrolle fuer die Verschaerfung: derselbe Baum, einmal mit dem Stem
    nur in Prosa (faellt jetzt) und einmal als Import (haelt weiter).
    """

    def _baum(self, tmp_path: Path, testinhalt: str) -> Path:
        (tmp_path / "tools" / "tests").mkdir(parents=True)
        (tmp_path / "tools" / "link_pruefen.py").write_text("x = 1\n")
        (tmp_path / "tools" / "tests" / "test_sammelsuite.py").write_text(testinhalt)
        return tmp_path

    def test_should_flag_module_only_mentioned_in_prose(self, tmp_path):
        # Realfall 4b1399 #4: link_pruefen.py ohne Test und ohne CI-Einbindung —
        # der Name stand nur in einem Docstring. Vor Rev 2 galt das als getestet.
        root = self._baum(
            tmp_path,
            '"""Suite. Siehe auch link_pruefen, das noch keinen Test hat."""\n',
        )
        assert cnm.hat_test_spur("link_pruefen", root) is False
        assert cnm.befunde_fuer(["tools/link_pruefen.py"], root) == [
            "tools/link_pruefen.py"
        ]

    def test_should_accept_import_as_reference(self, tmp_path):
        root = self._baum(tmp_path, "import link_pruefen\n")
        assert cnm.hat_test_spur("link_pruefen", root) is True

    def test_should_accept_path_literal_as_reference(self, tmp_path):
        root = self._baum(tmp_path, 'SCRIPT = "tools/link_pruefen.py"\n')
        assert cnm.hat_test_spur("link_pruefen", root) is True

    def test_should_accept_string_literal_as_reference(self, tmp_path):
        root = self._baum(tmp_path, 'MODUL = "link_pruefen"\n')
        assert cnm.hat_test_spur("link_pruefen", root) is True


class TestGateDrillOhneFalsifikation:
    """Rev 2, zweite Familie: ein neuer Gate-Drill muss seine Gegenprobe nennen.

    Realfall cc4e11 #4: das erste Klassen-Gate bestand die eigene Gegenprobe
    nicht (3000-Zeichen-Fenster griff in die Nachbarfunktion) — der Drill war
    gruen, die Gegenprobe stand nirgends.
    """

    def _drill(self, tmp_path: Path, inhalt: str) -> Path:
        (tmp_path / "tools" / "tests").mkdir(parents=True)
        (tmp_path / "tools" / "tests" / "test_klassen_gate.py").write_text(inhalt)
        return tmp_path

    def test_should_flag_gate_drill_without_falsification(self, tmp_path):
        root = self._drill(
            tmp_path,
            '"""Klassen-Gate fuer die Sperre."""\n\n'
            "def test_should_accept_valid_input():\n    assert True\n",
        )
        assert cnm.drill_befunde_fuer(["tools/tests/test_klassen_gate.py"], root) == [
            "tools/tests/test_klassen_gate.py"
        ]

    def test_should_accept_gate_drill_with_named_gegenprobe(self, tmp_path):
        root = self._drill(
            tmp_path,
            '"""Klassen-Gate fuer die Sperre."""\n\n'
            "# Gegenprobe: Sperre entfernt -> Test muss fallen.\n"
            "def test_should_accept_valid_input():\n    assert True\n",
        )
        assert cnm.drill_befunde_fuer(["tools/tests/test_klassen_gate.py"], root) == []

    def test_should_accept_gate_drill_with_flagging_testname(self, tmp_path):
        root = self._drill(
            tmp_path,
            '"""Drill fuer das Gate."""\n\n'
            "def test_should_flag_the_bad_case():\n    assert True\n",
        )
        assert cnm.drill_befunde_fuer(["tools/tests/test_klassen_gate.py"], root) == []

    def test_should_ignore_ordinary_test_file(self, tmp_path):
        # Eine Testdatei ohne Gate-Selbstauskunft ist kein Gate-Drill — sonst
        # traefe die Regel jeden Test im Repo und wuerde umgangen statt befolgt.
        root = self._drill(
            tmp_path,
            '"""Tests fuer die Rechenfunktion."""\n\n'
            "def test_should_add_two_numbers():\n    assert 1 + 1 == 2\n",
        )
        assert cnm.drill_befunde_fuer(["tools/tests/test_klassen_gate.py"], root) == []

    def test_should_ignore_modified_but_not_added_files(self, tmp_path):
        # Bestandsschutz bleibt: geprueft wird nur, was der PR HINZUFUEGT.
        root = self._drill(tmp_path, '"""Klassen-Gate."""\n')
        assert cnm.drill_befunde_fuer(["tools/irgendwas.py"], root) == []
