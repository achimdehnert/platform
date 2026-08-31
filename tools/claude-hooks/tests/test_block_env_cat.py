"""Drill für das Gate `secret-leak-via-safe-pattern` (block_env_cat.sh v4).

Jeder Block-Fall ist ein realer Leak aus einem Retro: `cat .env` (2026-07-03 F1),
`cut -d= -f1` auf Nicht-KV-Datei + Glob-Loop (f4a546 #1, 2026-07-10),
`bash -x` auf ein Passphrase-Skript (b62038 #4, 2026-08-21). Die Allow-Fälle
sind die dokumentierten Falsch-Positiv-Klassen der v3-Historie — ein Guard,
der legitime Arbeit blockt, wird abgeschaltet statt befolgt.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "block_env_cat.sh"


def _entscheidung(kommando: str) -> str:
    """'deny' oder 'allow' — der Hook schreibt nur im deny-Fall JSON auf stdout."""
    hook_input = json.dumps({"tool_input": {"command": kommando}})
    fertig = subprocess.run(
        ["bash", str(HOOK)],
        input=hook_input,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if not fertig.stdout.strip():
        return "allow"
    antwort = json.loads(fertig.stdout)
    return antwort["hookSpecificOutput"]["permissionDecision"]


# --- v3-Bestand: Reader / cut / Glob-Loop -----------------------------------


def test_should_block_a_raw_reader_on_a_secret_file():
    assert _entscheidung("cat /srv/app/.env") == "deny"


def test_should_let_an_example_file_pass():
    assert _entscheidung("cat /srv/app/.env.example") == "allow"


def test_should_block_cut_on_a_secret_file_without_kv_structure(tmp_path):
    datei = tmp_path / "token.secrets"
    datei.write_text("nur-ein-roher-tokenwert\n", encoding="utf-8")
    assert _entscheidung(f"cut -d= -f1 {datei}") == "deny"


def test_should_block_the_glob_loop_over_the_secrets_dir():
    """Der Incident vom 2026-07-10: Loop-Variablen sind nicht verifizierbar."""
    assert (
        _entscheidung('for f in ~/.secrets/*; do cut -d= -f1 "$f"; done') == "deny"
    )


def test_should_not_fire_on_an_unrelated_command():
    assert _entscheidung("git status && ls -la") == "allow"


# --- v4: bash -x auf Secret-erzeugende/-lesende Skripte (retro b62038 #4) ----


def test_should_block_xtrace_on_a_script_that_generates_a_secret(tmp_path):
    skript = tmp_path / "gen_passphrase.sh"
    skript.write_text(
        "#!/usr/bin/env bash\nPASS=$(openssl rand -base64 32)\n", encoding="utf-8"
    )
    assert _entscheidung(f"bash -x {skript}") == "deny"


def test_should_block_xtrace_on_a_script_that_reads_a_secret_file(tmp_path):
    skript = tmp_path / "lies_env.sh"
    skript.write_text(
        '#!/usr/bin/env bash\nsource /srv/app/.env\necho "$DB_HOST"\n',
        encoding="utf-8",
    )
    assert _entscheidung(f"bash -x {skript}") == "deny"


def test_should_let_xtrace_on_a_harmless_script_pass(tmp_path):
    skript = tmp_path / "harmlos.sh"
    skript.write_text("#!/usr/bin/env bash\necho hallo\n", encoding="utf-8")
    assert _entscheidung(f"bash -x {skript}") == "allow"


def test_should_let_the_secret_script_pass_without_xtrace(tmp_path):
    """Ohne -x kein Trace — das Skript selbst auszuführen ist legitim."""
    skript = tmp_path / "gen_passphrase.sh"
    skript.write_text(
        "#!/usr/bin/env bash\nPASS=$(openssl rand -base64 32)\n", encoding="utf-8"
    )
    assert _entscheidung(f"bash {skript}") == "allow"
