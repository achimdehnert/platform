"""Drill für tools/ruleset_perimeter_check.py (Gate autonomous-no-human-review).

Der Waechter bestaetigt, dass Ruleset (require_code_owner_review) und
CODEOWNERS-Perimeter noch scharf sind. Der Drill prueft die Urteilslogik mit
gemockten gh-Antworten — der ECHTE API-Lauf passiert im taeglichen Workflow
(.github/workflows/ruleset-waechter.yml), nicht hier: ein Drill, der Netz
braucht, waere in jedem Offline-Prueflauf rot und wuerde ignoriert.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ruleset_perimeter_check as rpc  # noqa: E402


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


LISTING = json.dumps(
    [
        {
            "id": 1,
            "name": "main-required-checks",
            "enforcement": "active",
            "target": "branch",
        }
    ]
)


def _detail(require_codeowner=True):
    return json.dumps(
        {
            "rules": [
                {"type": "deletion"},
                {
                    "type": "pull_request",
                    "parameters": {
                        "require_code_owner_review": require_codeowner,
                        "required_approving_review_count": 0,
                    },
                },
            ]
        }
    )


class TestCodeownersBefunde:
    def test_should_pass_when_all_perimeter_paths_present(self):
        text = "\n".join(f"{p}  @achimdehnert @wirdigital" for p in rpc.PERIMETER_PATHS)
        assert rpc.codeowners_befunde(text) == []

    def test_should_report_each_missing_perimeter_path(self):
        text = "/.github/ @achimdehnert\n# Kommentar\n\n/policies/ @achimdehnert"
        fehlend = rpc.codeowners_befunde(text)
        assert "/.github/" not in fehlend
        assert "/policies/" not in fehlend
        assert "/governance/" in fehlend
        assert "/scripts/" in fehlend

    def test_should_ignore_comments_and_blank_lines(self):
        text = "# /governance/ waere nur ein Kommentar\n\n"
        assert "/governance/" in rpc.codeowners_befunde(text)


class TestRulesetBefunde:
    def test_should_pass_when_active_ruleset_requires_codeowner_review(self):
        with patch.object(
            rpc, "gh_api", side_effect=[json.loads(LISTING), json.loads(_detail(True))]
        ):
            befunde, bewertbar = rpc.ruleset_befunde("o/r")
        assert bewertbar is True
        assert befunde == []

    def test_should_flag_when_codeowner_review_disabled(self):
        with patch.object(
            rpc, "gh_api", side_effect=[json.loads(LISTING), json.loads(_detail(False))]
        ):
            befunde, bewertbar = rpc.ruleset_befunde("o/r")
        assert bewertbar is True
        assert len(befunde) == 1

    def test_should_flag_when_no_active_branch_ruleset(self):
        listing = [{"id": 1, "enforcement": "disabled", "target": "branch"}]
        with patch.object(rpc, "gh_api", return_value=listing):
            befunde, bewertbar = rpc.ruleset_befunde("o/r")
        assert bewertbar is True
        assert len(befunde) == 1

    def test_should_be_unbewertbar_when_listing_fails(self):
        """Fetch-Fehler ist kein gruener Zustand — nicht bewertbar, kein Freispruch."""
        with patch.object(rpc, "gh_api", return_value=None):
            befunde, bewertbar = rpc.ruleset_befunde("o/r")
        assert bewertbar is False
        assert befunde == []

    def test_should_be_unbewertbar_when_detail_fails(self):
        with patch.object(rpc, "gh_api", side_effect=[json.loads(LISTING), None]):
            _, bewertbar = rpc.ruleset_befunde("o/r")
        assert bewertbar is False


class TestMainExitCodes:
    """Exit-Vertrag: 0 intakt · 1 Verletzung · 2 nicht bewertbar."""

    def _run_main(self, tmp_path, co_text, rs=([], True), slug="o/r"):
        gh_dir = tmp_path / ".github"
        gh_dir.mkdir()
        if co_text is not None:
            (gh_dir / "CODEOWNERS").write_text(co_text, encoding="utf-8")
        with (
            patch.object(rpc, "REPO_ROOT", tmp_path),
            patch.object(rpc, "repo_slug", return_value=slug),
            patch.object(rpc, "ruleset_befunde", return_value=rs),
        ):
            return rpc.main()

    def _full_codeowners(self):
        return "\n".join(f"{p} @a" for p in rpc.PERIMETER_PATHS)

    def test_should_exit_0_when_intact(self, tmp_path):
        assert self._run_main(tmp_path, self._full_codeowners()) == 0

    def test_should_exit_1_when_perimeter_path_missing(self, tmp_path):
        assert self._run_main(tmp_path, "/.github/ @a") == 1

    def test_should_exit_1_when_codeowners_missing(self, tmp_path):
        """Fehlende CODEOWNERS ist die Verletzung selbst, keine Messluecke."""
        assert self._run_main(tmp_path, None) == 1

    def test_should_exit_1_when_ruleset_loosened(self, tmp_path):
        assert (
            self._run_main(tmp_path, self._full_codeowners(), rs=(["locker"], True))
            == 1
        )

    def test_should_exit_2_when_ruleset_not_assessable(self, tmp_path):
        assert self._run_main(tmp_path, self._full_codeowners(), rs=([], False)) == 2

    def test_should_exit_2_when_repo_slug_unknown(self, tmp_path):
        assert self._run_main(tmp_path, self._full_codeowners(), slug=None) == 2


class TestRepoSlug:
    def test_should_prefer_ci_env(self, monkeypatch):
        monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
        assert rpc.repo_slug() == "org/repo"

    def test_should_parse_ssh_remote(self, monkeypatch):
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        out = _proc(stdout="git@github.com:achimdehnert/platform.git\n")
        with patch.object(rpc.subprocess, "run", return_value=out):
            assert rpc.repo_slug() == "achimdehnert/platform"

    def test_should_return_none_without_remote(self, monkeypatch):
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        with patch.object(rpc.subprocess, "run", return_value=_proc(returncode=128)):
            assert rpc.repo_slug() is None
