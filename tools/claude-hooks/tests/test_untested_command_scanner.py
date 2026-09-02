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
    text = '```\ncurl -H "Authorization: Bearer DEIN_TOKEN" https://api.github.com\n```'
    _, placeholders = find_untested(text, bash_commands=[])
    assert len(placeholders) == 1


def test_should_ignore_output_and_log_blocks():
    """Ausgabe-Beispiele dürfen nicht feuern — sonst nervt der Hook."""
    text = (
        "Ergebnis:\n\n```\n1/4 Token pruefen...\nFEHLER: HTTP 401\nexit=1\n```\n"
        'Und JSON:\n\n```json\n{"status": "queued"}\n```'
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


# --- Entprellung: derselbe Befund darf nicht in jedem Turn erneut kommen ----
#
# Realfall 2026-07-31: `_last_turn` endet bei der letzten ECHTEN Nutzernachricht.
# Hintergrund-Benachrichtigungen und Hook-Injektionen zaehlen nicht als solche.
# Arbeitet der Agent laenger ohne Zwischenruf, waechst das Fenster unbegrenzt —
# gemessen 166 Records mit 27 Vorkommen desselben Befehls, siebenmal hintereinander
# gemeldet.


def _lauf(tmp_path, monkeypatch, session, text, bash=()):
    """Ruft main() mit einem synthetischen Transkript und faengt die Ausgabe."""
    import io
    import json as _json

    import untested_command_scanner as ucs

    monkeypatch.setattr(ucs, "STATE_DIR", tmp_path / "state")
    inhalt = []
    inhalt.append(_json.dumps({"type": "user", "message": {"content": "los"}}))
    blocks = [{"type": "text", "text": text}]
    for b in bash:
        blocks.append({"type": "tool_use", "name": "Bash", "input": {"command": b}})
    inhalt.append(_json.dumps({"type": "assistant", "message": {"content": blocks}}))
    tp = tmp_path / f"{session}.jsonl"
    tp.write_text("\n".join(inhalt), encoding="utf-8")

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(_json.dumps({"transcript_path": str(tp), "session_id": session})),
    )
    aus = io.StringIO()
    monkeypatch.setattr("sys.stdout", aus)
    ucs.main()
    return aus.getvalue()


TEXT = "Bitte ausfuehren:\n```bash\nssh root@example.invalid 'systemctl restart foo'\n```\n"


def test_should_report_an_untested_command_the_first_time(tmp_path, monkeypatch):
    assert "systemctl" in _lauf(tmp_path, monkeypatch, "s1", TEXT)


def test_should_not_report_the_same_command_again(tmp_path, monkeypatch):
    """Der zweite Lauf ueber dasselbe Fenster muss still bleiben."""
    _lauf(tmp_path, monkeypatch, "s2", TEXT)
    assert _lauf(tmp_path, monkeypatch, "s2", TEXT) == ""


def test_should_still_report_a_different_command(tmp_path, monkeypatch):
    """Die Entprellung darf nicht den ganzen Waechter abschalten."""
    _lauf(tmp_path, monkeypatch, "s3", TEXT)
    anderer = "Und noch:\n```bash\nssh root@example.invalid 'docker restart bar'\n```\n"
    assert "docker" in _lauf(tmp_path, monkeypatch, "s3", anderer)


def test_should_keep_reporting_per_session(tmp_path, monkeypatch):
    """Eine andere Sitzung faengt bei null an."""
    _lauf(tmp_path, monkeypatch, "s4", TEXT)
    assert "systemctl" in _lauf(tmp_path, monkeypatch, "s5", TEXT)


# --- Entprellung gilt auch fuer Platzhalter (platform#2006, 2026-08-16) -------
#
# Die Entprellung oben filterte nur `untested`, und `_merken` speicherte nur die.
# Ein Platzhalter-Befund kam deshalb bei JEDEM weiteren Stop erneut — auch nach
# der Korrektur, weil `_last_turn` bis zur letzten echten Nutzernachricht
# zurueckreicht. Real gemessen: derselbe Ausschnitt dreimal, zweimal davon nach
# dem Fix. Genau die Klasse, gegen die die Entprellung gebaut wurde; einer ihrer
# beiden Zweige fehlte.

PLATZHALTER = (
    'Setze das:\n```bash\ngh variable set FOO --repo o/r --body "<App ID>"\n```\n'
)


def test_should_report_a_placeholder_the_first_time(tmp_path, monkeypatch):
    assert "Platzhalter" in _lauf(tmp_path, monkeypatch, "p1", PLATZHALTER)


def test_should_not_report_the_same_placeholder_again(tmp_path, monkeypatch):
    """Der eigentliche Fix: zweimal dasselbe ist einmal zu viel."""
    _lauf(tmp_path, monkeypatch, "p2", PLATZHALTER)
    assert _lauf(tmp_path, monkeypatch, "p2", PLATZHALTER) == ""


def test_should_still_report_a_new_placeholder(tmp_path, monkeypatch):
    """Entprellt wird die Wiederholung, nicht der Befund.

    Ohne diesen Test waere „nie wieder melden" die billige Loesung — und der
    Waechter waere ab dem ersten Treffer taub.
    """
    _lauf(tmp_path, monkeypatch, "p3", PLATZHALTER)
    neuer = "Und noch:\n```bash\ngh secret set BAR --repo o/r < <pem-datei>\n```\n"
    assert "Platzhalter" in _lauf(tmp_path, monkeypatch, "p3", neuer)


def test_should_start_fresh_in_another_session_for_placeholders(tmp_path, monkeypatch):
    _lauf(tmp_path, monkeypatch, "p4", PLATZHALTER)
    assert "Platzhalter" in _lauf(tmp_path, monkeypatch, "p5", PLATZHALTER)


# ── Uebergabe-Praefix `!` (platform#2230, Antwort "ausweiten") ──────────────
# In Claude Code bedeutet `! <befehl>`, dass der OWNER ihn ausfuehrt. Das ist die
# Uebergabe-Konvention — und machte den Scanner bis 2026-08-23 blind: derselbe
# Befehl feuerte ohne `!` und nicht mit. Realfall ausschreibungs-hub 2026-08-23:
# ein nie ausgefuehrtes Skript ging so an den Owner und schrieb seine eigenen
# Zeilen in eine Prod-Credential-Datei.


def test_should_fire_on_a_handed_over_script_with_bang_prefix():
    text = "```bash\n! bash /root/install-certbot-token.sh\n```\n"
    untested, _ = find_untested(text, [])
    assert untested == ["bash /root/install-certbot-token.sh"]


def test_should_fire_on_a_handed_over_ssh_command_with_bang_prefix():
    text = "```bash\n! ssh root@host 'systemctl restart nginx'\n```\n"
    untested, _ = find_untested(text, [])
    assert untested and "ssh root@host" in untested[0]


def test_should_still_fire_without_the_bang_prefix():
    """Regressionsschutz: die alte, funktionierende Richtung bleibt."""
    untested, _ = find_untested("```bash\nbash /root/x.sh\n```\n", [])
    assert untested == ["bash /root/x.sh"]


def test_should_stay_silent_when_the_bang_command_was_actually_run():
    untested, _ = find_untested(
        "```bash\n! bash /root/x.sh\n```\n", ["bash /root/x.sh"]
    )
    assert untested == []


def test_should_not_treat_prose_starting_with_bang_as_a_command():
    """`!` allein macht keine Zeile zum Befehl — der Starter muss folgen."""
    untested, _ = find_untested("```\n! das ist Prosa, kein Befehl\n```\n", [])
    assert untested == []


# --- Verweigerte Ausfuehrung (2026-09-01) ------------------------------------
#
# Ein Befehl, dessen Ausfuehrung der Permission-Classifier sperrt, ist nicht
# ungetestet, sondern unausfuehrbar. Der Melder feuerte am 2026-09-01 dreimal
# auf denselben gesperrten Befehl (Retro meiki-hub 33616e, Befund #8).


def test_should_stay_silent_when_execution_was_denied():
    text = "Fuehr du das aus:\n\n```\ndocker exec risk_hub_web python manage.py onboard_tenant --slug x\n```"
    untested, _ = find_untested(
        text,
        bash_commands=["docker exec risk_hub_staging_web python manage.py onboard_tenant --dry-run"],
        abgelehnte_kerne={"docker exec"},
    )
    assert untested == []


def test_should_still_flag_when_a_different_command_was_denied():
    """Die Abdeckung gilt nur fuer den gesperrten Kern, nicht pauschal.

    Realfall: `docker exec` war gesperrt, weitergegeben wurde spaeter
    `ssh hetzner-prod 'docker exec …'` — anderer Kern, anderes Risiko. Genau
    dieser Lauf fand ein kaputtes Quoting, das sonst beim User gelandet waere.
    """
    text = "```\nssh hetzner-prod 'docker exec risk_hub_web python manage.py onboard_tenant'\n```"
    untested, _ = find_untested(
        text, bash_commands=["git status"], abgelehnte_kerne={"docker exec"}
    )
    assert untested and untested[0].startswith("ssh hetzner-prod")


def test_should_detect_denial_marker_in_tool_result():
    from untested_command_scanner import _ist_ablehnung

    assert _ist_ablehnung(
        "Permission for this action was denied by the Claude Code auto mode classifier."
    )
    assert _ist_ablehnung([{"type": "text", "text": "Reason: Blocked by classifier."}])
    assert not _ist_ablehnung("bash: docker: command not found")
