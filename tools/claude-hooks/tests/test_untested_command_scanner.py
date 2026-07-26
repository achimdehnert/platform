"""Tests für den untested-command-Scanner (Stop hook).

Deckt die drei Fehlschläge ab, die den Hook ausgelöst haben (2026-07-26):
Platzhalter im Befehl, Token-Name statt Wert, und ein Handover-Skript, das
der Assistent selbst nie ausgeführt hatte. Dazu die Stillhalte-Fälle, damit
der Hook nicht bei jedem Code-Beispiel anschlägt.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HOOK_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_HOOK_DIR))

from untested_command_scanner import (  # noqa: E402
    build_reminder,
    find_untested,
)


def test_should_flag_command_never_run_in_turn():
    text = "Führ das aus:\n\n```\nbash ~/shared/fix-devhub-token.sh\n```"
    untested, placeholders = find_untested(text, bash_commands=["git status"])
    assert untested == ["bash ~/shared/fix-devhub-token.sh"]
    assert placeholders == []


def test_should_stay_silent_when_same_command_ran_in_turn():
    text = "Getestet:\n\n```\nbash ~/shared/fix-devhub-token.sh\n```"
    ran = ["bash /home/devuser/shared/fix-devhub-token.sh < /dev/null"]
    untested, placeholders = find_untested(text, bash_commands=ran)
    assert untested == []
    assert placeholders == []


def test_should_flag_angle_bracket_placeholder():
    """Fehlschlag 1: bash las < als Umleitung."""
    text = "```\nGH_TOKEN=<dieser PAT> gh api /users/x/settings/billing/actions\n```"
    untested, placeholders = find_untested(text, bash_commands=[])
    assert placeholders and "<dieser PAT>" in placeholders[0]
    assert untested == []


def test_should_flag_uppercase_placeholder():
    text = "```\ncurl -H \"Authorization: Bearer DEIN_TOKEN\" https://api.github.com\n```"
    _, placeholders = find_untested(text, bash_commands=[])
    assert len(placeholders) == 1


def test_should_ignore_output_and_log_blocks():
    """Ausgabe-Beispiele dürfen nicht feuern — sonst nervt der Hook."""
    text = (
        "Ergebnis:\n\n```\n1/4 Token pruefen...\nFEHLER: HTTP 401\nexit=1\n```\n"
        "Und JSON:\n\n```json\n{\"status\": \"queued\"}\n```"
    )
    untested, placeholders = find_untested(text, bash_commands=[])
    assert untested == []
    assert placeholders == []


def test_should_ignore_comments_and_shell_prompt_prefix():
    text = "```\n# nur zur Erklärung\ndevuser@host:~$ git status\n```"
    untested, _ = find_untested(text, bash_commands=["git status -sb"])
    assert untested == []


def test_should_match_despite_env_prefix_and_path_difference():
    text = "```\nDEVHUB_HOST=hetzner-prod bash /home/devuser/bin/x.sh\n```"
    untested, _ = find_untested(text, bash_commands=["bash ~/bin/x.sh --scan"])
    assert untested == []


def test_should_flag_script_by_bare_name():
    text = "```\nfix-devhub-token.sh --scan\n```"
    untested, _ = find_untested(text, bash_commands=["ls ~/bin"])
    assert untested == ["fix-devhub-token.sh --scan"]


def test_should_return_empty_reminder_without_findings():
    assert build_reminder([], []) == ""


def test_should_name_both_finding_classes_in_reminder():
    msg = build_reminder(["bash x.sh"], ["gh api <TOKEN>"])
    assert "Platzhalter" in msg
    assert "ohne ihn in diesem Turn selbst" in msg
    assert msg.startswith("[untested-command-scanner]")
