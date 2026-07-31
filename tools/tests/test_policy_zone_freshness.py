"""Mutationstest fuer scripts/checks/policy_zone_freshness.sh (ADR-291).

Warum dieser Test existiert
---------------------------
ADR-291 verlangt: **kein Gate ohne bewiesene Rot-Faehigkeit** — "gruen beweist
nichts ueber die Faehigkeit, rot zu werden". Der Anlass ist konkret: Der
vorhandene Check `klickdummy_policy_sync.sh` (ADR-211 C6) prueft genau EINE
Datei. Am 2026-07-31 stand der gepinnte Worktree 17 Commits zurueck, mit
geaenderter `llm-routing.md` und `session-routing.md` — `klickdummy.md` war
unveraendert, C6 also gruen. Ein Mutationstest haette das vor dem Verdrahten
gezeigt; er existierte nicht.

Der gepruefte Check gehoert auf die Maschine (sein Gegenstand `~/.claude/policies`
existiert auf einem CI-Runner nicht). **Sein Beweis gehoert trotzdem in CI:** Die
Fixtures hier setzen `CLAUDE_POLICIES_DIR`, damit die Rot-Faehigkeit auch dort
nachweisbar ist, wo der Check selbst nur skippen wuerde.

`POLICY_ZONE_REF=HEAD` pinnt den Bezug — kein Netz, kein bestimmter
Verlaufs-Commit noetig.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "scripts" / "checks" / "policy_zone_freshness.sh"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_SETUP = 2


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    ).stdout


def _policies_at_head() -> list[str]:
    out = _git("ls-tree", "--name-only", "HEAD", "--", "policies/")
    return sorted(
        line.removeprefix("policies/")
        for line in out.splitlines()
        if line.endswith(".md")
    )


def _run(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CHECK), *extra],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(target.parent),
            "CLAUDE_POLICIES_DIR": str(target),
            "POLICY_ZONE_REF": "HEAD",
        },
    )


@pytest.fixture
def gruene_zone(tmp_path: Path) -> Path:
    """Deckungsgleiches Injektions-Ziel — die Kontrollgruppe."""
    ziel = tmp_path / "policies"
    ziel.mkdir()
    for name in _policies_at_head():
        (ziel / name).write_text(_git("show", f"HEAD:policies/{name}"))
    return ziel


def test_should_report_green_for_identical_zone(gruene_zone: Path) -> None:
    """Ohne Kontrollgruppe sagt kein einziger Rot-Fall etwas aus."""
    ergebnis = _run(gruene_zone)
    assert ergebnis.returncode == EXIT_OK, ergebnis.stdout + ergebnis.stderr
    assert "GRUEN" in ergebnis.stdout


def test_should_skip_when_no_injection_environment(tmp_path: Path) -> None:
    ergebnis = _run(tmp_path / "existiert-nicht")
    assert ergebnis.returncode == EXIT_OK
    assert "SKIP" in ergebnis.stdout


def test_should_fail_on_missing_environment_when_strict(tmp_path: Path) -> None:
    ergebnis = _run(tmp_path / "existiert-nicht", "--strict")
    assert ergebnis.returncode == EXIT_FAIL


def test_should_detect_stale_pin(gruene_zone: Path) -> None:
    """DER Zielfall — genau hier faellt ADR-211 C6 durch.

    Eine Policy traegt einen aelteren Inhalt, die uebrigen sind aktuell. C6
    wuerde das nur bemerken, wenn ausgerechnet `klickdummy.md` betroffen waere.
    """
    (gruene_zone / "llm-routing.md").write_text("# veralteter Stand\n")
    ergebnis = _run(gruene_zone)
    assert ergebnis.returncode == EXIT_FAIL, ergebnis.stdout
    assert "llm-routing.md" in ergebnis.stdout


def test_should_detect_stale_pin_in_any_file_not_only_klickdummy(
    gruene_zone: Path,
) -> None:
    """Regression gegen die C6-Luecke: die Abdeckung gilt fuer JEDE Policy."""
    namen = _policies_at_head()
    assert len(namen) > 1, "Zone mit nur einer Datei — Test waere gegenstandslos"
    for name in namen:
        inhalt = (gruene_zone / name).read_text()
        (gruene_zone / name).write_text(inhalt + "\nDRIFT\n")
        ergebnis = _run(gruene_zone)
        assert ergebnis.returncode == EXIT_FAIL, f"{name} blieb unbemerkt"
        assert name in ergebnis.stdout, f"{name} nicht namentlich gemeldet"
        (gruene_zone / name).write_text(inhalt)


def test_should_detect_missing_policy(gruene_zone: Path) -> None:
    (gruene_zone / "adr-threshold.md").unlink()
    ergebnis = _run(gruene_zone)
    assert ergebnis.returncode == EXIT_FAIL
    assert "fehlen" in ergebnis.stdout
    assert "adr-threshold.md" in ergebnis.stdout


def test_should_detect_orphan_file(gruene_zone: Path) -> None:
    """Eine untergeschobene Datei im Injektions-Ziel ist ein Zonen-Verstoss."""
    (gruene_zone / "zombie-policy.md").write_text("# nicht aus der Quelle\n")
    ergebnis = _run(gruene_zone)
    assert ergebnis.returncode == EXIT_FAIL
    assert "zombie-policy.md" in ergebnis.stdout


def test_should_report_setup_error_without_repo(tmp_path: Path) -> None:
    """Setupfehler bekommt einen EIGENEN Wert — er darf nicht als FAIL gelten."""
    ziel = tmp_path / "policies"
    ziel.mkdir()
    kopie = tmp_path / "kein_repo"
    (kopie / "scripts" / "checks").mkdir(parents=True)
    (kopie / "scripts" / "checks" / "policy_zone_freshness.sh").write_text(
        CHECK.read_text()
    )
    ergebnis = subprocess.run(
        ["bash", str(kopie / "scripts" / "checks" / "policy_zone_freshness.sh")],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "CLAUDE_POLICIES_DIR": str(ziel),
        },
    )
    assert ergebnis.returncode == EXIT_SETUP, ergebnis.stdout + ergebnis.stderr
