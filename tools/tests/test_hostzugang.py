"""Tests für tools/hostzugang.py + tools/hostzugang.sh (platform#2783).

Der Helfer ersetzt die dreifache Hop-Konstruktion (ssh_via/ssh_shell) aus
flottenbild.py, host_datei_drift.py und deploy-script-drift.sh. Ziel ist
Verhaltens-Erhaltung: dieselbe argv-Liste wie vorher je Host — deshalb prüfen
die Tests unten die konkreten, historisch bekannten Kommandos (nicht nur die
Struktur), und ein Test vergleicht Python- gegen Bash-Ausgabe direkt.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hostzugang  # noqa: E402

TOOLS_DIR = Path(__file__).resolve().parents[1]
HOSTZUGANG_SH = TOOLS_DIR / "hostzugang.sh"

FB_SSH_OPTS = [
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=8",
    "-o",
    "StrictHostKeyChecking=accept-new",
]
HDD_SSH_OPTS = ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]


# ── Direkt-Host ───────────────────────────────────────────────────────────────


def test_should_build_flottenbild_style_command_for_direct_host():
    host = {"ssh": "root@88.198.191.108"}
    cmd = hostzugang.ssh_kommando(host, ssh_opts=FB_SSH_OPTS)
    assert cmd == [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "root@88.198.191.108",
        "bash -s",
    ]


def test_should_build_host_datei_drift_style_command_for_direct_host():
    host = {"ssh": "root@88.198.191.108"}
    befehl = "md5sum /usr/local/bin/x.sh"
    cmd = hostzugang.ssh_kommando(host, ssh_opts=HDD_SSH_OPTS, kommando_direkt=befehl)
    # Direkt-Zweig von host_datei_drift.py: das Kommando geht als eigenes
    # argv-Element durch, NICHT als Shell — der historische Unterschied zu
    # flottenbild.py bleibt erhalten.
    assert cmd == [
        "ssh",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "BatchMode=yes",
        "root@88.198.191.108",
        befehl,
    ]


# ── Hop-Host (ssh_via) ────────────────────────────────────────────────────────


def test_should_nest_ssh_via_hop_with_default_shell():
    host = {"ssh": "adehnert@10.99.0.4", "ssh_via": "root@88.198.191.108"}
    cmd = hostzugang.ssh_kommando(host, ssh_opts=FB_SSH_OPTS)
    assert cmd == [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "root@88.198.191.108",
        'ssh -o BatchMode=yes -o ConnectTimeout=8 adehnert@10.99.0.4 "bash -s"',
    ]


def test_should_use_kommando_direkt_only_for_the_non_via_branch():
    # host_datei_drift.py: kommando_direkt wirkt NUR ohne ssh_via — mit
    # ssh_via wird immer die Shell genestet (Nutzlast geht dann per stdin).
    host = {"ssh": "adehnert@10.99.0.4", "ssh_via": "root@88.198.191.108"}
    cmd = hostzugang.ssh_kommando(
        host, ssh_opts=HDD_SSH_OPTS, kommando_direkt="ignoriert im Hop-Zweig"
    )
    assert cmd == [
        "ssh",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "BatchMode=yes",
        "root@88.198.191.108",
        'ssh -o BatchMode=yes -o ConnectTimeout=8 adehnert@10.99.0.4 "bash -s"',
    ]


def test_should_use_hosts_own_ssh_shell_when_hopping():
    # GPU-Box: WSL statt bash -s als Remote-Shell.
    host = {
        "ssh": "achim@10.99.0.2",
        "ssh_via": "root@88.198.191.108",
        "ssh_shell": "wsl -d Ubuntu -u root -e bash -s",
    }
    cmd = hostzugang.ssh_kommando(host, ssh_opts=FB_SSH_OPTS)
    assert cmd[-1] == (
        'ssh -o BatchMode=yes -o ConnectTimeout=8 achim@10.99.0.2 '
        '"wsl -d Ubuntu -u root -e bash -s"'
    )


# ── betrieb: auf_zuruf — betrifft NUR die Klassifikation nach dem Aufruf ─────


def test_should_ignore_betrieb_auf_zuruf_when_building_the_command():
    """`betrieb` steht im selben hosts.yaml-Eintrag, ändert aber nichts an der
    argv-Liste — nur die Aufrufer klassifizieren einen Fehlschlag danach
    unterschiedlich (schläft vs. unerreichbar). Dieses Verhalten bleibt
    unverändert bei den Aufrufern, nicht im Helfer."""
    ohne_betrieb = {"ssh": "achim@10.99.0.2", "ssh_via": "root@88.198.191.108"}
    mit_betrieb = {**ohne_betrieb, "betrieb": "auf_zuruf"}
    assert hostzugang.ssh_kommando(ohne_betrieb) == hostzugang.ssh_kommando(mit_betrieb)


# ── Fehlende Felder ───────────────────────────────────────────────────────────


def test_should_require_ssh_key_in_host_dict():
    import pytest

    with pytest.raises(KeyError):
        hostzugang.ssh_kommando({"ssh_via": "root@88.198.191.108"})


def test_should_default_shell_to_bash_dash_s_when_ssh_shell_missing():
    host = {"ssh": "root@88.198.191.108"}
    cmd = hostzugang.ssh_kommando(host)
    assert cmd[-1] == "bash -s"


def test_should_honor_custom_shell_default_argument():
    host = {"ssh": "root@88.198.191.108"}
    cmd = hostzugang.ssh_kommando(host, shell_default="sh -c bash")
    assert cmd[-1] == "sh -c bash"


# ── Bash-Gegenstück: Erhaltungstest gegen die Python-Variante ────────────────


_BASH_SCRIPT = """
set -euo pipefail
source "$0"
hostzugang_ssh_kommando "$@"
printf '%s\\n' "${HOSTZUGANG_CMD[@]}"
"""


def _bash_kommando(ssh_target: str, ssh_via: str, kommando: str, *ssh_opts: str) -> list[str]:
    """Ruft hostzugang_ssh_kommando() in bash auf und liest HOSTZUGANG_CMD zurück
    (ein Wort pro Zeile) — Argumente gehen als echte argv-Elemente durch `bash -c
    ... "$0" "$@"`, kein manuelles Quoting fürs Zusammensetzen des Scripts."""
    r = subprocess.run(
        ["bash", "-c", _BASH_SCRIPT, str(HOSTZUGANG_SH), ssh_target, ssh_via, kommando, *ssh_opts],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def test_should_match_python_helper_for_direct_host():
    # Einwortiges Kommando: hier stimmen beide Direkt-Zweige ueberein (kein
    # word-splitting-Unterschied moeglich). Der Mehrwort-Fall mit bewusst
    # abweichendem Verhalten steht in test_should_match_deploy_script_drift_...
    ssh_opts = ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
    py = hostzugang.ssh_kommando(
        {"ssh": "root@88.198.191.108"}, ssh_opts=ssh_opts, kommando_direkt="true"
    )
    bash_out = _bash_kommando("root@88.198.191.108", "", "true", *ssh_opts)
    assert bash_out == py


def test_should_match_python_helper_for_hop_host_with_shell():
    ssh_opts = ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
    host = {
        "ssh": "achim@10.99.0.2",
        "ssh_via": "root@88.198.191.108",
        "ssh_shell": "wsl -d Ubuntu -u root -e bash -s",
    }
    shell = host["ssh_shell"]
    py = hostzugang.ssh_kommando(host, ssh_opts=ssh_opts)
    bash_out = _bash_kommando(
        host["ssh"], host["ssh_via"], shell, *ssh_opts
    )
    assert bash_out == py


def test_should_match_deploy_script_drift_probe_invocation_across_python_and_bash():
    """Erhaltungstest für den dritten Aufrufstil: deploy-script-drift.sh baut
    `"$shell -- $REMOTE_PATH"` und übergibt es UNGEQUOTET im Direkt-Zweig
    (word-splitting), GEQUOTET als ein Wort im Hop-Zweig — beides muss mit der
    Python-Formel übereinstimmen, wenn man denselben kommando_direkt-Wert für
    den Direkt-Zweig nutzt bzw. dieselbe Shell für den Hop-Zweig."""
    ssh_opts = ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
    remote_path = "/opt/scripts/deploy.sh"

    # Direkt-Host: bash zerlegt "$shell -- $REMOTE_PATH" unquoted in Wörter.
    py_direkt = hostzugang.ssh_kommando(
        {"ssh": "root@88.198.191.108"},
        ssh_opts=ssh_opts,
        kommando_direkt=" ".join(["bash", "-s", "--", remote_path]),
    )
    bash_direkt = _bash_kommando(
        "root@88.198.191.108", "", f"bash -s -- {remote_path}", *ssh_opts
    )
    assert bash_direkt == [
        "ssh", *ssh_opts, "root@88.198.191.108", "bash", "-s", "--", remote_path
    ]
    # Python-Variante haengt den String als EIN Element an (kommando_direkt ist
    # kein word-splitting) — das ist der bereits bekannte, bewusst erhaltene
    # Unterschied zwischen den drei Aufrufstilen, kein Fehler.
    assert py_direkt[-1] == f"bash -s -- {remote_path}"

    # Hop-Host: beide betten dieselbe gequotete Zeichenkette ins innere ssh ein.
    host = {"ssh": "adehnert@10.99.0.4", "ssh_via": "root@88.198.191.108"}
    py_hop = hostzugang.ssh_kommando(host, ssh_opts=ssh_opts, shell_default="bash -s -- " + remote_path)
    bash_hop = _bash_kommando(
        host["ssh"], host["ssh_via"], f"bash -s -- {remote_path}", *ssh_opts
    )
    assert bash_hop == py_hop
