"""Drill für `block_unbelegte_bescheinigung.py` (Gate `claim-before-cheapest-check`, PreToolUse).

Positivkontrolle sind die beiden Realfälle aus platform#3656, neutral als Text
nachgebaut (keine Namen, keine echten Links):

  1. „Freigabe Merge … nach Vier-Augen-Review durch den Owner“ — belegt war nur
     ein knappes „go“.
  2. „K1 ist erfüllt“ — ohne Kriterien-Abgleich.

Beide stehen zuerst und müssen auf jedem Body-Weg (inline, Datei, Heredoc)
geblockt werden. Die Gegenproben müssen durchgehen: eine Bescheinigung MIT Beleg
und ein neutraler Kommentar — ein Guard, der sie blockt, würde abgeschaltet statt
befolgt. Der Aufruf läuft wie in settings.json: Datei direkt, Event auf stdin.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "block_unbelegte_bescheinigung.py"

REALFALL_FREIGABE = "Freigabe Merge von #12 nach Vier-Augen-Review durch den Owner."
REALFALL_K1 = "K1 ist erfüllt."
KOMMENTAR_LINK = "https://github.com/beispiel/repo/issues/12#issuecomment-1234567"


def _entscheidung(kommando: str) -> str:
    fertig = subprocess.run(
        [str(HOOK)],
        input=json.dumps({"tool_input": {"command": kommando}}),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert fertig.returncode == 0, fertig.stderr
    if not fertig.stdout.strip():
        return "allow"
    ausgabe = json.loads(fertig.stdout)["hookSpecificOutput"]
    assert ausgabe["hookEventName"] == "PreToolUse"
    assert ausgabe["permissionDecisionReason"].strip()
    return ausgabe["permissionDecision"]


# --- Positivkontrolle: die beiden Realfälle ----------------------------------


def test_should_block_realfall_freigabe_inline_body():
    kommando = f'gh pr comment 12 -R beispiel/repo --body "{REALFALL_FREIGABE}"'
    assert _entscheidung(kommando) == "deny"


def test_should_block_realfall_k1_inline_body():
    kommando = f'gh issue comment 34 -R beispiel/repo -b "{REALFALL_K1} Danke."'
    assert _entscheidung(kommando) == "deny"


def test_should_block_realfall_freigabe_via_body_file(tmp_path):
    datei = tmp_path / "kommentar.md"
    datei.write_text(f"Zwischenstand.\n\n{REALFALL_FREIGABE}\n", encoding="utf-8")
    assert _entscheidung(f"gh pr comment 12 --body-file {datei}") == "deny"


def test_should_block_realfall_k1_via_short_flag_file(tmp_path):
    datei = tmp_path / "k1.md"
    datei.write_text(f"## Stand\n\n{REALFALL_K1}\n", encoding="utf-8")
    assert _entscheidung(f"gh issue comment 34 -F {datei}") == "deny"


def test_should_block_realfall_k1_via_stdin_heredoc():
    kommando = f"gh issue comment 34 --body-file - <<'EOF'\n{REALFALL_K1}\nEOF"
    assert _entscheidung(kommando) == "deny"


def test_should_block_realfall_freigabe_via_cat_heredoc_substitution():
    kommando = (
        "gh pr comment 12 --body \"$(cat <<'EOF'\n"
        f"{REALFALL_FREIGABE}\nEOF\n)\""
    )
    assert _entscheidung(kommando) == "deny"


def test_should_block_body_file_written_in_same_command(tmp_path):
    datei = tmp_path / "neu.md"  # existiert zum PreToolUse-Zeitpunkt noch nicht
    kommando = (
        f"cat > {datei} <<'EOF'\n{REALFALL_K1}\nEOF\n"
        f"gh issue comment 34 --body-file {datei}"
    )
    assert _entscheidung(kommando) == "deny"


def test_should_block_when_shell_text_not_splittable():
    # Apostroph im Heredoc: shlex scheitert, der Rückfall liest den Rohtext.
    kommando = (
        f"gh pr comment 12 --body-file - <<EOF\nGibt's Neues: {REALFALL_FREIGABE}\nEOF"
    )
    assert _entscheidung(kommando) == "deny"


def test_should_block_approve_without_beleg():
    assert _entscheidung("gh pr review 12 --approve") == "deny"


def test_should_block_review_claim_in_pr_review_body():
    kommando = 'gh pr review 12 --comment -b "Review abgeschlossen, alles geprüft."'
    assert _entscheidung(kommando) == "deny"


def test_should_block_when_only_one_of_two_criteria_has_abgleich():
    body = "K1 und K2 sind erfüllt.\n\n- K1 → Beleg: `make test` 12 passed\n"
    assert _entscheidung(f"gh issue comment 34 -b '{body}'") == "deny"


# --- Gegenproben: müssen durchgehen ------------------------------------------


def test_should_allow_freigabe_with_comment_link():
    kommando = f'gh pr comment 12 --body "{REALFALL_FREIGABE} Beleg: {KOMMENTAR_LINK}"'
    assert _entscheidung(kommando) == "allow"


def test_should_allow_neutral_comment():
    kommando = 'gh pr comment 12 --body "Fix gepusht, CI läuft. Nächster Schritt: Doku."'
    assert _entscheidung(kommando) == "allow"


def test_should_allow_open_or_requesting_sentences():
    body = "Review steht noch aus. Bitte um Freigabe. Ist K1 damit erfüllt?"
    assert _entscheidung(f'gh issue comment 34 --body "{body}"') == "allow"


def test_should_allow_k1_with_kriterien_abgleich_line():
    body = "K1 ist erfüllt.\n\n- K1 „Hook blockt vor dem Post“ → Beleg: `make test` 12 passed\n"
    assert _entscheidung(f"gh issue comment 34 -b '{body}'") == "allow"


def test_should_allow_kriterien_tabelle(tmp_path):
    datei = tmp_path / "abgleich.md"
    datei.write_text(
        "Alle Kriterien erfüllt.\n\n| Kriterium | Beleg |\n|---|---|\n| K1 | #3656 |\n",
        encoding="utf-8",
    )
    assert _entscheidung(f"gh issue comment 34 --body-file {datei}") == "allow"


def test_should_allow_review_id():
    kommando = 'gh pr comment 12 -b "Review durch den Owner, Review-ID 987654."'
    assert _entscheidung(kommando) == "allow"


def test_should_allow_owner_message_link_outside_github():
    kommando = (
        'gh pr comment 12 -b "Freigabe durch den Owner: https://chat.example.org/msg/42"'
    )
    assert _entscheidung(kommando) == "allow"


def test_should_allow_geprueft_with_ci_run_link():
    kommando = (
        'gh pr comment 12 -b "Lokal und in CI geprüft: '
        'https://github.com/beispiel/repo/actions/runs/123456"'
    )
    assert _entscheidung(kommando) == "allow"


def test_should_allow_approve_with_comment_link():
    kommando = f'gh pr review 12 --approve -b "Gegenlesen dokumentiert: {KOMMENTAR_LINK}"'
    assert _entscheidung(kommando) == "allow"


def test_should_not_treat_bare_pr_link_as_beleg():
    kommando = (
        f'gh pr comment 12 -b "{REALFALL_FREIGABE} https://github.com/beispiel/repo/pull/12"'
    )
    assert _entscheidung(kommando) == "deny"


# --- Nicht zuständig / fail-open --------------------------------------------


def test_should_ignore_gh_text_inside_commit_message():
    kommando = f'git commit -m "Doku: gh pr comment mit {REALFALL_FREIGABE}"'
    assert _entscheidung(kommando) == "allow"


def test_should_ignore_other_gh_commands():
    assert _entscheidung(f'gh pr create --title x --body "{REALFALL_K1}"') == "allow"


def test_should_fail_open_on_invalid_json():
    fertig = subprocess.run(
        [str(HOOK)], input="kein json", capture_output=True, text=True, timeout=30
    )
    assert fertig.returncode == 0
    assert fertig.stdout == ""


def test_should_fail_open_on_unreadable_body_file():
    kommando = "gh issue comment 34 --body-file /nicht/vorhanden/kommentar.md"
    assert _entscheidung(kommando) == "allow"
