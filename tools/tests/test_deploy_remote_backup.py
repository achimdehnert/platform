"""Gate: das Pre-Deploy-Backup in deploy-remote.sh dumpt mit dem DB-User des Containers.

Befund platform#3159: `pg_dumpall -U "${POSTGRES_USER:-postgres}"` stand ausserhalb des
Containers. Das Host-Skript kennt POSTGRES_USER nicht, also galt immer `postgres` —
in apo-hub (POSTGRES_USER=apo_hub) scheiterten 12 von 12 Deploys ohne sichtbaren Fehler.

Zwei Ebenen:
- lexikalisch (immer): kein pg_dump/pg_dumpall bekommt `-U "${POSTGRES_USER...` vom Host.
- echt (nur mit Docker): die Backup-Zeile aus dem Skript laeuft gegen einen Postgres-Container,
  dessen Superuser NICHT `postgres` heisst, und erzeugt einen nicht leeren Dump.
"""

import gzip
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / "deployment" / "scripts" / "deploy-remote.sh"
)
POSTGRES_IMAGE = "postgres:16-alpine"
GATE_USER = "gate_user"

# Host-seitige Expansion: -U "${POSTGRES_USER..." direkt am pg_dump-Aufruf, nicht in sh -c '...'
_HOST_EXPANSION = re.compile(r'pg_dump(?:all)?\s+-U\s+"\$\{?POSTGRES_USER')


def _backup_condition() -> str:
    """Die Bedingung des `if … ; then` um das Backup, Zeilenfortsetzungen zusammengezogen."""
    text = SCRIPT.read_text().replace("\\\n", " ")
    match = re.search(r"if (docker exec \"\$DB_CONTAINER\".*?pg_dump.*?); then", text)
    assert match, "Backup-Aufruf in deploy-remote.sh nicht gefunden"
    return match.group(1)


def _outside_single_quotes(command: str) -> str:
    """Einfach gequotete Teile (laufen per sh -c im Container) ausblenden."""
    return re.sub(r"'[^']*'", "''", command)


@pytest.mark.f1
def test_should_not_expand_postgres_user_on_host():
    condition = _backup_condition()
    assert not _HOST_EXPANSION.search(_outside_single_quotes(condition)), (
        "pg_dump bekommt POSTGRES_USER aus dem Host-Skript — dort ist er nie gesetzt "
        f"(platform#3159): {condition}"
    )


@pytest.mark.f1
def test_should_flag_host_expansion_in_old_backup_line():
    """Gegenprobe: das Muster trifft die alte Zeile aus platform#3159, die neue nicht."""
    old = (
        'docker exec "$DB_CONTAINER" pg_dumpall -U "${POSTGRES_USER:-postgres}" '
        '2>/dev/null | gzip > "$BACKUP_FILE"'
    )
    new = (
        'docker exec "$DB_CONTAINER" sh -c \'pg_dumpall -U "${POSTGRES_USER:-postgres}"\' '
        '2>"$BACKUP_ERR" | gzip > "$BACKUP_FILE"'
    )
    assert _HOST_EXPANSION.search(_outside_single_quotes(old))
    assert not _HOST_EXPANSION.search(_outside_single_quotes(new))


@pytest.mark.f1
@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker nicht verfuegbar")
def test_should_dump_with_container_postgres_user(tmp_path):
    name = f"gate-deploy-backup-{uuid.uuid4().hex[:8]}"
    run = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-e",
            f"POSTGRES_USER={GATE_USER}",
            "-e",
            "POSTGRES_PASSWORD=gate",
            POSTGRES_IMAGE,
        ],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        pytest.skip(f"Postgres-Container nicht startbar: {run.stderr.strip()[:200]}")
    try:
        # pg_isready allein genuegt nicht: das Image startet erst einen Init-Server und
        # beendet ihn wieder ("terminating connection due to administrator command").
        for _ in range(90):
            logs = subprocess.run(
                ["docker", "logs", name], capture_output=True, text=True
            )
            init_done = "PostgreSQL init process complete" in logs.stdout + logs.stderr
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", GATE_USER],
                capture_output=True,
            )
            if init_done and ready.returncode == 0:
                break
            time.sleep(1)
        else:
            pytest.fail("Postgres wurde nicht bereit")

        backup_file = tmp_path / "pre_deploy_gate.sql.gz"
        script = (
            "set -euo pipefail\n"
            "unset POSTGRES_USER\n"  # wie im Deploy-Skript auf dem Host
            f'DB_CONTAINER="{name}"\n'
            f'BACKUP_FILE="{backup_file}"\n'
            'BACKUP_ERR="${BACKUP_FILE%.sql.gz}.err"\n'
            f"if {_backup_condition()}; then exit 0; else exit 1; fi\n"
        )
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        err = backup_file.with_suffix("").with_suffix(".err")
        detail = err.read_text()[:300] if err.exists() else result.stderr[:300]
        assert result.returncode == 0, f"Backup-Aufruf scheitert: {detail}"
        dump = gzip.decompress(backup_file.read_bytes()).decode()
        assert "PostgreSQL database cluster dump" in dump
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
