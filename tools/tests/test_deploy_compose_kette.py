"""Tests fuer die -f-Kette in scripts/deploy.sh (platform#2586 K2).

Diese Kette entscheidet, welche compose-Dateien der Deploy kennt. Was nicht
drinsteht, behandelt `up --remove-orphans` als Waise und LOESCHT es — am
2026-09-01 traf das `mcp_hub_rag`, `llm_gateway` und `mcp_hub_grafana`.

Der Test EXTRAHIERT den Block zwischen den Markern aus deploy.sh und fuehrt ihn
aus. Eine Kopie der Logik im Test wuerde vom Skript wegdriften und dann nichts
mehr ueber den echten Deploy belegen.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent.parent
DEPLOY = WURZEL / "scripts/deploy.sh"


def kettenblock() -> str:
    """Der Block zwischen den Markern — die einzige Quelle der Kette."""
    zeilen = DEPLOY.read_text().splitlines()
    try:
        a = next(i for i, s in enumerate(zeilen) if "# --- KETTE-ANFANG" in s)
        e = next(i for i, s in enumerate(zeilen) if "# --- KETTE-ENDE" in s)
    except StopIteration:  # pragma: no cover — waere ein Befund, kein Testfehler
        pytest.fail(
            "Marker KETTE-ANFANG/-ENDE fehlen in scripts/deploy.sh — "
            "ohne sie prueft dieser Test nichts."
        )
    return "\n".join(zeilen[a : e + 1])


def kette(
    tmp_path: Path, compose_file: str, dateien: list[str], manifest: dict | None
) -> str:
    """Fuehrt den Block gegen ein praepariertes APP_PATH aus; gibt die -f-Kette."""
    for name in dateien:
        (tmp_path / name).write_text("services: {}\n")
    if manifest is not None:
        (tmp_path / ".deploy-manifest.json").write_text(json.dumps(manifest))

    skript = (
        "set -u\n"
        f'APP_PATH="{tmp_path}"\n'
        f'COMPOSE_FILE="{compose_file}"\n'
        'ENVIRONMENT="production"\n'
        f"{kettenblock()}\n"
        'printf "%s\\n" "${COMPOSE_ARGS[@]}"\n'
    )
    aus = subprocess.run(
        ["bash", "-c", skript], capture_output=True, text=True, timeout=30
    )
    assert aus.returncode == 0, f"Block scheiterte: {aus.stdout}\n{aus.stderr}"
    # Nur die -f-Argumente, auf Dateinamen gekuerzt.
    return " ".join(
        Path(z).name
        for z in aus.stdout.splitlines()
        if z.startswith(str(tmp_path)) and z.endswith((".yml", ".yaml"))
    )


def test_should_take_every_declared_file_into_the_chain(tmp_path):
    # Der Anlass: die Overlay-Datei muss mitfahren.
    ergebnis = kette(
        tmp_path,
        "docker-compose.prod.yml",
        ["docker-compose.prod.yml", "docker-compose.llm-mcp.yml"],
        {
            "compose_files": {
                "docker-compose.prod.yml": "x",
                "docker-compose.llm-mcp.yml": "y",
            }
        },
    )

    assert ergebnis == "docker-compose.prod.yml docker-compose.llm-mcp.yml"


def test_should_put_the_base_file_first_regardless_of_manifest_order(tmp_path):
    # Spaetere -f gewinnen. Die Manifest-Reihenfolge ist alphabetisch, und
    # docker-compose.llm-mcp.yml sortiert VOR docker-compose.prod.yml — wuerde
    # man sie uebernehmen, ueberschriebe das Overlay die Basis nicht, sondern
    # umgekehrt.
    ergebnis = kette(
        tmp_path,
        "docker-compose.prod.yml",
        ["docker-compose.prod.yml", "docker-compose.aaa.yml"],
        {
            "compose_files": {
                "docker-compose.aaa.yml": "x",
                "docker-compose.prod.yml": "y",
            }
        },
    )

    assert ergebnis.split()[0] == "docker-compose.prod.yml"


def test_should_not_take_a_host_file_that_no_manifest_declares(tmp_path):
    # Am 2026-09-01 lagen in /opt/mcp-hub eine rag.yml, die das Repo nicht mehr
    # kennt, und eine .bak. Ein Glob haette beide mitgenommen.
    ergebnis = kette(
        tmp_path,
        "docker-compose.prod.yml",
        ["docker-compose.prod.yml", "docker-compose.verwaist.yml"],
        {"compose_files": {"docker-compose.prod.yml": "x"}},
    )

    assert "verwaist" not in ergebnis


def test_should_fall_back_to_the_override_file_when_the_manifest_is_old(tmp_path):
    # Hubs mit aelterem shared-ci-Pin haben kein compose_files im Manifest.
    ergebnis = kette(
        tmp_path,
        "docker-compose.prod.yml",
        ["docker-compose.prod.yml", "docker-compose.override.yml"],
        {"compose_sha": "x"},
    )

    assert ergebnis == "docker-compose.prod.yml docker-compose.override.yml"


def test_should_work_without_any_manifest_at_all(tmp_path):
    # Gegenprobe zum Rueckfall: ohne Manifest bleibt die Basis-Datei uebrig,
    # der Block bricht nicht ab.
    ergebnis = kette(
        tmp_path, "docker-compose.prod.yml", ["docker-compose.prod.yml"], None
    )

    assert ergebnis == "docker-compose.prod.yml"


def test_should_abort_when_a_declared_file_is_missing_on_the_host(tmp_path):
    # Ein halb angekommener Sync ist gefaehrlicher als ein Abbruch: die
    # fehlende Datei waere genau die, deren Container geraeumt wuerden.
    (tmp_path / "docker-compose.prod.yml").write_text("services: {}\n")
    (tmp_path / ".deploy-manifest.json").write_text(
        json.dumps(
            {
                "compose_files": {
                    "docker-compose.prod.yml": "x",
                    "docker-compose.fehlt.yml": "y",
                }
            }
        )
    )
    skript = (
        "set -u\n"
        f'APP_PATH="{tmp_path}"\n'
        'COMPOSE_FILE="docker-compose.prod.yml"\n'
        'ENVIRONMENT="production"\n'
        f"{kettenblock()}\n"
    )
    aus = subprocess.run(
        ["bash", "-c", skript], capture_output=True, text=True, timeout=30
    )

    assert aus.returncode == 8
    assert "fehlt aber am Host" in aus.stdout


def test_should_warn_about_undeclared_host_files(tmp_path):
    # Der Melder darf nicht schweigen — sonst bleibt die Datei unbemerkt liegen.
    (tmp_path / "docker-compose.prod.yml").write_text("services: {}\n")
    (tmp_path / "docker-compose.verwaist.yml").write_text("services: {}\n")
    (tmp_path / ".deploy-manifest.json").write_text(
        json.dumps({"compose_files": {"docker-compose.prod.yml": "x"}})
    )
    skript = (
        "set -u\n"
        f'APP_PATH="{tmp_path}"\n'
        'COMPOSE_FILE="docker-compose.prod.yml"\n'
        'ENVIRONMENT="production"\n'
        f"{kettenblock()}\n"
    )

    aus = subprocess.run(
        ["bash", "-c", skript], capture_output=True, text=True, timeout=30
    )

    assert aus.returncode == 0
    assert "docker-compose.verwaist.yml" in aus.stdout
    assert "faehrt NICHT mit" in aus.stdout
