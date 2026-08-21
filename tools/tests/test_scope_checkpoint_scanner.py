"""Tests für tools/claude-hooks/scope_checkpoint_scanner.py — Repo-Erkennung.

Das Modul hatte bis 2026-08-21 keine Tests. Aufgefallen ist das nicht durch eine
Lücke im Testlauf, sondern durch den Melder selbst: er schlug am Ende einer
Sitzung an, die **ein** Repo berührt hatte, und nannte als Begründung

    3 beschriebene Repos (platform, 'platform && cat > ',
                          'platform && git remote get-url origin && S=')

Drei Schreibweisen desselben Repos. `_repo_aus_pfad` schnitt am nächsten
Schrägstrich ab — auf einem Pfad richtig, auf einem Bash-Kommandostring falsch,
und die zweite Aufrufstelle übergibt genau so einen String.

Die Fälle hier sind darum keine erfundenen Beispiele, sondern die Kommandos,
die den Fehlalarm ausgelöst haben.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "claude-hooks"))

sc = pytest.importorskip("scope_checkpoint_scanner")


class TestRepoAusPfad:
    def test_should_read_the_repo_from_a_plain_path(self):
        assert sc._repo_aus_pfad("/home/x/github/platform/tools/a.py") == "platform"

    def test_should_read_the_repo_from_a_session_worktree(self):
        """ADR-233: editiert wird im Worktree, nicht im Haupt-Tree."""
        pfad = "/home/x/.repo-session/worktrees/risk-hub/2026-08-21-slug/manage.py"
        assert sc._repo_aus_pfad(pfad) == "risk-hub"

    def test_should_stop_the_name_at_shell_syntax(self):
        """Der Realfall: aus dem Kommando wurde 'platform && cat > ' als Repo."""
        assert sc._repo_aus_pfad("cd ~/github/platform && cat > /tmp/x") == "platform"

    def test_should_stop_the_name_at_an_assignment(self):
        cmd = "cd ~/github/platform && git remote get-url origin && S=/tmp/s"
        assert sc._repo_aus_pfad(cmd) == "platform"

    def test_should_count_three_spellings_as_one_repo(self):
        """Die eigentliche Zusicherung: `repos_beschrieben` ist ein Set von
        Strings. Solange drei Schreibweisen drei Einträge ergeben, feuert das
        Gate in Ein-Repo-Sitzungen — und gewöhnt das Weghören an."""
        kommandos = [
            "cd ~/github/platform",
            "cd ~/github/platform && cat > /tmp/x",
            "cd ~/github/platform && git remote get-url origin && S=/tmp/s",
        ]
        assert {sc._repo_aus_pfad(k) for k in kommandos} == {"platform"}

    def test_should_ignore_a_hidden_directory(self):
        assert sc._repo_aus_pfad("/home/x/github/.cache/foo") == ""

    def test_should_return_empty_without_a_marker(self):
        assert sc._repo_aus_pfad("/tmp/irgendwo/platform/x.py") == ""

    def test_should_keep_a_hyphen_in_the_repo_name(self):
        assert sc._repo_aus_pfad("cd ~/github/meiki-hub && ls") == "meiki-hub"


class TestReposAusKommando:
    def test_should_find_every_repo_a_command_touches(self):
        """Untertreiben ist hier die gefährlichere Richtung: das Gate zählt Repos,
        und ein Cross-Repo-Sprung ist genau das, was es sichtbar machen soll."""
        cmd = "cp ~/github/platform/x ~/github/dev-hub/y"
        assert sc._repos_aus_kommando(cmd) == {"platform", "dev-hub"}

    def test_should_not_inflate_one_repo_into_several(self):
        cmd = "cd ~/github/platform && cp ~/github/platform/a ~/github/platform/b"
        assert sc._repos_aus_kommando(cmd) == {"platform"}

    def test_should_mix_worktree_and_main_tree(self):
        cmd = "diff ~/github/platform/a ~/.repo-session/worktrees/platform/s/a"
        assert sc._repos_aus_kommando(cmd) == {"platform"}

    def test_should_return_an_empty_set_without_a_marker(self):
        assert sc._repos_aus_kommando("echo hallo") == set()
