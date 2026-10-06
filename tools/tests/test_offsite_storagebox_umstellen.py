"""Gate: Umstellskript Offsite-Ziel -> Hetzner Storage Box (ADR-289 §3.1b Revision 3,
Owner-Wort "Storage Box go", achimdehnert/platform#3475 E3/E4).

deployment/scripts/offsite-auf-storagebox-umstellen.sh stellt das restic-Offsite-Ziel
vom toten netcup-rest-server auf eine vorhandene Hetzner Storage Box (SFTP, Port 23,
Unterkonto je Host) um. Das Skript selbst wird in dieser Session NICHT gegen einen
echten Host ausgefuehrt (Prod-Eingriff = Owner-Wort je Host, E3/E4) — diese Tests
laufen es end-to-end via subprocess gegen einen `ssh`-PATH-Shim, der jeden Aufruf in
eine Log-Datei protokolliert und anhand des uebergebenen Remote-Kommandos eine
kanonische Antwort simuliert (Host-Key-Pruefung, SFTP-Login, restic snapshots/init,
prod-offsite-daily.sh). Kein echtes Netzwerk, kein echter Host.

Fuenf Tore, in der Reihenfolge, in der das Skript sie durchlaeuft:
  A. Env-Datei vollstaendig (SB_HOST/SB_USER gesetzt)
  B. Host-Key von SB_HOST:23 schon in known_hosts auf dem Ziel-Host
  C. SFTP-Login des Unterkontos gelingt
  D. SB_SNAPSHOTS_BESTAETIGT=1 (Unveraenderlichkeits-Nachweis, ADR-289 §3.1b Nr. 2)
Bricht eines davon ab, darf NICHTS geschrieben werden — kein `cp`, `sed`, `mkdir` auf
dem Host. `restic init` laeuft nur mit ausdruecklichem SB_INIT_ERLAUBT=1.

Run: python3 -m pytest tools/tests/test_offsite_storagebox_umstellen.py -q
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "deployment" / "scripts" / "offsite-auf-storagebox-umstellen.sh"

# Protokolliert jeden Aufruf (Argumente, \x1f-getrennt) nach $SSH_SHIM_LOG und
# antwortet je nach im Remote-Kommando enthaltenem Muster — ohne es auszufuehren.
_SSH_SHIM = r"""#!/usr/bin/env bash
{
  printf 'CALL'
  for a in "$@"; do printf '\x1f%s' "$a"; done
  printf '\n'
} >> "$SSH_SHIM_LOG"
if [ ! -t 0 ]; then cat >/dev/null 2>&1 || true; fi

cmd="${2:-}"

case "$cmd" in
  *"ssh-keygen -F"*)
    [ "${SSH_SHIM_HOSTKEY_OK:-1}" = "1" ] && exit 0 || exit 1
    ;;
  *"sftp -b -"*)
    [ "${SSH_SHIM_SFTP_OK:-1}" = "1" ] && exit 0 || exit 1
    ;;
  *"prod-offsite-daily.sh"*)
    echo "[fake] offsite lauf ok"
    exit 0
    ;;
  *"restic snapshots"*)
    if [ "${SSH_SHIM_RESTIC_MISSING:-0}" = "1" ]; then
      echo "Fatal: unable to open repository: unable to open config file: sftp: repository does not exist"
      exit 1
    fi
    echo "fake123  2026-09-24 03:00:00  prod  pgdump"
    exit 0
    ;;
  *"restic init"*)
    echo "created restic repository fake123 at sftp:storagebox-offsite:/"
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
"""

_DEFAULT_WERTE = {
    "SB_HOST": "box123.your-storagebox.de",
    "SB_USER": "u123-sub1",
    "SB_SNAPSHOTS_BESTAETIGT": "1",
}


def _make_env_file(tmp_path: Path, **overrides: str | None) -> Path:
    werte = dict(_DEFAULT_WERTE)
    werte.update(overrides)
    pfad = tmp_path / "hetzner-storagebox.env"
    zeilen = [f"{k}={v}" for k, v in werte.items() if v is not None]
    pfad.write_text("\n".join(zeilen) + "\n")
    return pfad


def _make_shim(tmp_path: Path) -> Path:
    shim_dir = tmp_path / "shimbin"
    shim_dir.mkdir(exist_ok=True)
    ssh_path = shim_dir / "ssh"
    ssh_path.write_text(_SSH_SHIM)
    ssh_path.chmod(0o755)
    return shim_dir


def _run_script(
    tmp_path: Path, env_file: Path, extra_env: dict[str, str] | None = None
) -> tuple[subprocess.CompletedProcess, str]:
    shim_dir = _make_shim(tmp_path)
    log = tmp_path / "ssh-calls.log"
    log.write_text("")
    env = dict(os.environ)
    env["PATH"] = f"{shim_dir}:{env['PATH']}"
    env["SB_ENV_FILE"] = str(env_file)
    env["SSH_SHIM_LOG"] = str(log)
    env["PROD_HOST"] = "hetzner-prod-test"
    for key in ("TROCKEN", "SB_INIT_ERLAUBT"):
        env.pop(key, None)
    if extra_env:
        env.update(extra_env)
    bash_bin = shutil.which("bash")
    res = subprocess.run(
        [bash_bin, str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    calls = log.read_text() if log.exists() else ""
    return res, calls


class TestOffsiteStorageboxUmstellen:
    def test_should_abort_naming_missing_env_var(self, tmp_path):
        """Tor A: SB_USER fehlt -> Abbruch mit Namen, kein einziger ssh-Aufruf."""
        env_file = _make_env_file(tmp_path, SB_USER=None)

        res, calls = _run_script(tmp_path, env_file)

        assert res.returncode != 0
        assert "SB_USER" in res.stderr
        assert calls == "", f"Skript hat vor Tor A schon ssh aufgerufen: {calls}"

    def test_should_abort_with_keyscan_hint_when_hostkey_missing(self, tmp_path):
        """Tor B: kein Host-Key -> Abbruch mit ssh-keyscan-Anleitung, kein Schreibzugriff."""
        env_file = _make_env_file(tmp_path)

        res, calls = _run_script(
            tmp_path, env_file, extra_env={"SSH_SHIM_HOSTKEY_OK": "0"}
        )

        assert res.returncode != 0
        assert "ssh-keyscan -p 23" in res.stderr
        assert "cp -a" not in calls
        assert "sed -i" not in calls
        assert "mkdir -p" not in calls

    def test_should_abort_when_snapshot_plan_not_confirmed(self, tmp_path):
        """Tor D: SB_SNAPSHOTS_BESTAETIGT fehlt -> Abbruch, kein Schreibzugriff."""
        env_file = _make_env_file(tmp_path, SB_SNAPSHOTS_BESTAETIGT="0")

        res, calls = _run_script(tmp_path, env_file)

        assert res.returncode != 0
        assert "SB_SNAPSHOTS_BESTAETIGT" in res.stderr
        assert "cp -a" not in calls
        assert "sed -i" not in calls

    def test_should_change_nothing_in_dry_run(self, tmp_path):
        """TROCKEN=1: alle vier Tore laufen (auch die ssh-Checks), nichts wird geschrieben."""
        env_file = _make_env_file(tmp_path)

        res, calls = _run_script(tmp_path, env_file, extra_env={"TROCKEN": "1"})

        assert res.returncode == 0, f"stdout={res.stdout}\nstderr={res.stderr}"
        assert "TROCKEN" in res.stdout
        assert "cp -a" not in calls
        assert "sed -i" not in calls
        assert "restic init" not in calls
        assert "prod-offsite-daily.sh" not in calls
        # Die lesenden Tor-Checks (B/C) muessen trotzdem gelaufen sein.
        assert "ssh-keygen -F" in calls
        assert "sftp -b -" in calls

    def test_should_abort_restic_init_without_explicit_permission(self, tmp_path):
        """Fehlt das Repository am Ziel, initialisiert das Skript nicht blind."""
        env_file = _make_env_file(tmp_path)

        res, calls = _run_script(
            tmp_path, env_file, extra_env={"SSH_SHIM_RESTIC_MISSING": "1"}
        )

        assert res.returncode != 0
        assert "SB_INIT_ERLAUBT" in res.stderr
        assert "restic init" not in calls

    def test_should_complete_full_run_when_all_gates_pass(self, tmp_path):
        """Gegenprobe: mit allen Toren gruen und vorhandenem Repository laeuft der
        volle Weg bis zum ersten Sicherungslauf durch (kein Abbruch, restic init
        NICHT gebraucht, weil das Repository laut Shim schon existiert)."""
        env_file = _make_env_file(tmp_path)

        res, calls = _run_script(tmp_path, env_file)

        assert res.returncode == 0, f"stdout={res.stdout}\nstderr={res.stderr}"
        assert "prod-offsite-daily.sh" in calls
        assert "restic init" not in calls
        assert "storagebox-offsite" in res.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash nicht verfuegbar")
def test_should_have_valid_bash_syntax():
    """Gegen den in dieser Session nie ausgefuehrten Live-Pfad: `bash -n` allein
    prueft keine Semantik, faengt aber jeden Quoting-/Klammerfehler ab."""
    res = subprocess.run(
        ["bash", "-n", str(SCRIPT)], capture_output=True, text=True, timeout=10
    )
    assert res.returncode == 0, res.stderr
