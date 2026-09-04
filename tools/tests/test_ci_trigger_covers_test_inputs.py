"""Ein Test, dessen Eingabe ausserhalb seines Triggers liegt, ist strukturell blind.

`tools-tests.yml` traegt einen `on.push.paths`-Filter. Liest ein Test unter
`tools/tests/` einen real existierenden Repo-Pfad, den dieser Filter NICHT abdeckt,
dann laeuft der Gate bei einer Aenderung genau dieses Pfades nicht — die Deckung ist
still weg, der Gate-Name bleibt gruen.

Realfall 2026-08-03: `test_check_deploy_adr_supersession` prueft den gesamten ADR-Baum,
`docs/adr/**` stand aber nicht im Trigger. `ADR-292` machte `main` am 02.08. rot und
blieb unsichtbar, bis ein fremder PR (#1702) zufaellig `tools/**` anfasste. Der eigene
Retro-PR lief in derselben Zeit gruen durch.

Verfahren, bewusst konservativ (Messung 2026-08-03: 4 Treffer, 0 Fehlalarme):
Pfad-Literale aus den Testdateien ziehen, auf **real existierende** Repo-Pfade filtern
(sonst schlagen synthetische Fixture-Strings wie "apps/foo/settings.py" durch) und
gegen den Trigger halten. Ein neuer Treffer ist entweder eine echte Luecke — dann
gehoert der Pfad in den Filter — oder ein Fixture-Pfad, der zufaellig existiert; dann
in ALLOWLIST mit Begruendung.

Run: `python3 -m pytest tools/tests/test_ci_trigger_covers_test_inputs.py -q`
"""

import importlib.util
import pathlib
import re

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_WF = _REPO_ROOT / ".github" / "workflows" / "tools-tests.yml"
_TESTS = _REPO_ROOT / "tools" / "tests"

_spec = importlib.util.spec_from_file_location(
    "crp", _REPO_ROOT / "tools" / "ci_relevant_paths.py"
)
crp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crp)

# Pfad-artige String-Literale: mindestens ein "/" , keine Platzhalter/Globs.
_LITERAL = re.compile(r"""["']([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)["']""")

# Real existierende Pfade, die trotzdem KEINE Trigger-Deckung brauchen.
# Schluessel = exakter Literal-Treffer, Wert = Begruendung (wird nie geprueft,
# steht fuer den naechsten Leser da).
ALLOWLIST: dict[str, str] = {
    # Fixture-Schluessel im synthetischen Evidenzpaket (test_future_readiness_score.py) — der Test liest die
    # Datei nicht, er nennt nur ihren Namen als Dateiexistenz-Marker.
    ".github/CODEOWNERS": "Fixture-Schluessel, keine Testeingabe (future_readiness_score)",
}


def _uncovered() -> dict[str, set[str]]:
    patterns = crp.load_workflow_paths(_WF)
    assert patterns, "tools-tests.yml traegt keine on.push.paths — Filter unlesbar"
    gaps: dict[str, set[str]] = {}
    for test_file in sorted(_TESTS.glob("*.py")):
        text = test_file.read_text(encoding="utf-8", errors="replace")
        for literal in set(_LITERAL.findall(text)):
            if literal in ALLOWLIST:
                continue
            ziel = (_REPO_ROOT / literal).resolve()
            if not ziel.is_relative_to(_REPO_ROOT):
                continue  # ".."-Traversal-Fixture — liest nicht aus dem Repo
            if not ziel.exists():
                continue  # Fixture-String, kein Repo-Read
            if crp.is_relevant([literal], patterns):
                continue
            gaps.setdefault(literal, set()).add(test_file.name)
    return gaps


def test_should_cover_every_real_input_path_of_tools_tests():
    gaps = _uncovered()
    lines = [
        f"  {path}  <- {', '.join(sorted(files))}"
        for path, files in sorted(gaps.items())
    ]
    assert not gaps, (
        "Diese Testeingaben liegen ausserhalb des on.push.paths-Filters von "
        "tools-tests.yml — bei einer Aenderung dort laeuft der Gate NICHT:\n"
        + "\n".join(lines)
        + "\n\nEntweder den Pfad in .github/workflows/tools-tests.yml ergaenzen "
        "(Regelfall) oder — wenn es ein Fixture-Pfad ist, der nur zufaellig "
        "existiert — mit Begruendung in ALLOWLIST aufnehmen."
    )


def test_should_detect_an_uncovered_path_when_one_exists():
    """Rot-Beweis: ohne ihn koennte die Erkennung kaputt sein und der Gate
    dauerhaft gruen bleiben, ohne je etwas zu pruefen."""
    patterns = ["tools/**"]
    assert crp.is_relevant(["tools/x.py"], patterns) is True
    assert crp.is_relevant(["docs/adr/ADR-1.md"], patterns) is False


def test_should_ignore_traversal_literals_that_escape_the_repo():
    """Realfall 2026-08-05 (platform#1775): '../../.ssh/authorized_keys'.

    Der Fixture-String des Path-Traversal-Tests in test_graph_mail.py machte den
    Guard NUR auf Dev-Maschinen rot: Repo-Root/../../.ssh/authorized_keys ist
    $HOME/.ssh/authorized_keys und existiert dort — in CI nicht. Ein Literal,
    das per ".." aus dem Repo hinausfuehrt, ist nie eine Testeingabe dieses
    Repos und darf den Filter-Abgleich gar nicht erst erreichen.
    """
    assert not any(pfad.startswith("..") for pfad in _uncovered()), _uncovered()
