"""Test fuer .github/workflows/serielle-prs-advisory.yml (Retro b7822e B14).

Der Gate-Ausgang war seit dem Bau (2026-09-07) blind: der PR-Kommentar-Schritt
postete `gh api ... -f body=@"$BODY_FILE"`. `-f/--raw-field` haengt den Wert
IMMER woertlich an — inklusive des literalen `@/tmp/tmp.XXXXXX`-Pfads, statt
ihn als Datei zu lesen. 46 PR-Kommentare trugen dadurch den Dateipfad statt
des Befundtexts. Nur `-F/--field` interpretiert das `@<path>`-Praefix als
"Wert aus Datei lesen" (`gh api --help`, Zeile zu `-F`: '(use "@<path>" or
"@-" to read value from file or stdin)').

Dieser Test ist die Echtprobe fuer den Ausgang: eine Invariante ueber ALLE
Workflow-Dateien, nicht nur die eine, die den Befund ausgeloest hat — ein
neuer Workflow mit demselben Tippfehler faellt sofort auf.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"

# `-f key=@datei` / `--raw-field key=@datei` haengt den Wert woertlich an
# (der literale String "@datei" landet im Request) — fuer einen Dateiinhalt
# ist ausschliesslich `-F`/`--field` richtig (liest "@<path>" aus einer Datei).
_F_MIT_AT = re.compile(r"(?<!-)-f\s+\S+=@|--raw-field(?:\s+|=)\S+=@")


def _workflow_dateien() -> list[Path]:
    assert WORKFLOWS_DIR.is_dir(), WORKFLOWS_DIR
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


def test_should_have_at_least_one_workflow_file_to_check():
    # Trivialer Schutz gegen einen falschen Pfad (0 Dateien waere ein stiller
    # Erfolg ohne jede Pruefung).
    assert len(_workflow_dateien()) > 0


def test_should_never_use_f_field_with_at_file_reference_in_any_workflow():
    """Invariante ueber .github/workflows/*.yml: kein `-f key=@datei`.

    `gh api -f body=@"$BODY_FILE"` postet den Pfad als Text statt den
    Dateiinhalt zu lesen (Retro b7822e B14, 46 betroffene PR-Kommentare in
    serielle-prs-advisory.yml:107,110). Richtig ist `-F body=@"$BODY_FILE"`.
    """
    verstoesse: list[str] = []
    for pfad in _workflow_dateien():
        text = pfad.read_text(encoding="utf-8")
        for zeilennr, zeile in enumerate(text.splitlines(), start=1):
            if _F_MIT_AT.search(zeile):
                verstoesse.append(
                    f"{pfad.relative_to(WORKFLOWS_DIR.parents[1])}:{zeilennr}: {zeile.strip()}"
                )
    assert not verstoesse, (
        "gh api -f key=@datei postet den Dateipfad statt des Inhalts, "
        "-F verwenden:\n" + "\n".join(verstoesse)
    )


def test_should_use_capital_f_field_for_the_pr_comment_body_in_serielle_prs_advisory():
    """Gegenprobe direkt an der Fundstelle: beide `gh api`-Aufrufe fuer den
    PR-Kommentar (PATCH und POST) verwenden `-F body=@"$BODY_FILE"`."""
    datei = WORKFLOWS_DIR / "serielle-prs-advisory.yml"
    text = datei.read_text(encoding="utf-8")
    treffer = re.findall(r'-F\s+body=@"?\$BODY_FILE"?', text)
    assert len(treffer) == 2, (
        f'erwartet 2 Aufrufe (PATCH + POST) mit -F body=@"$BODY_FILE", gefunden: {treffer}'
    )
    assert "-f body=@" not in text
