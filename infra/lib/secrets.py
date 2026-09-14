"""Zentraler Secret-Resolver für alle Platform-Infra-Scripts.

Single Source of Truth für Secret-Auflösung. Jedes infra/scripts/*.py
importiert von hier statt eigene Token-Logik zu implementieren.

Auflösungs-Reihenfolge (First Match gewinnt):
  1. os.environ[ENV_VAR]
  2. os.environ[MCP_ENV_VAR]  (falls MCP den Token anders benennt)
  3. ~/.secrets/<canonical_file>
  4. ~/.secrets/<alternative_files>  (Legacy-Namen)
  5. MCP-Prozess-Env (liest /proc/<pid>/environ)

Nutzung:
    from infra.lib.secrets import get_secret, require_secret

    token = get_secret("cloudflare")
    token = require_secret("cloudflare")  # raises if missing

    # Alle Secrets auf einen Blick:
    python -m infra.lib.secrets

    # Eine Secret-DATEI direkt lesen (bare oder NAME=WERT):
    from infra.lib.secrets import secret_wert, secret_bytes

Referenz: ADR-157, ADR-156 §8
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

SECRETS_DIR = Path.home() / ".secrets"

# ─── Kanonisches Secret-Registry ──────────────────────────────
# Jeder Eintrag: logical_name → {
#   env: primäre Env-Var,
#   mcp_env: Env-Var im MCP-Prozess (falls anders),
#   file: kanonischer Dateiname unter ~/.secrets/,
#   alt_files: alternative/legacy Dateinamen,
#   mcp_process: MCP-Prozessname zum Env-Scan,
#   description: Beschreibung,
#   test_url: optionale URL zum Validieren,
# }

REGISTRY: dict[str, dict] = {
    "cloudflare": {
        "env": "CLOUDFLARE_API_TOKEN",
        "mcp_env": ("DEPLOYMENT_MCP_CLOUDFLARE_API_TOKEN"),
        "file": "cloudflare_api_token",
        "alt_files": [
            "cloudflare_write_token",
        ],
        "mcp_process": "deployment_mcp",
        "description": "Cloudflare DNS/Zone API",
        "test_url": ("https://api.cloudflare.com/client/v4/user/tokens/verify"),
    },
    "cloudflare_access": {
        "env": "CLOUDFLARE_ACCESS_TOKEN",
        "mcp_env": ("DEPLOYMENT_MCP_CLOUDFLARE_ACCESS_TOKEN"),
        "file": "cloudflare_access_token",
        "alt_files": [],
        "mcp_process": "deployment_mcp",
        "description": "Cloudflare Zero Trust",
    },
    "hetzner": {
        "env": "HETZNER_CLOUD_TOKEN",
        "mcp_env": ("DEPLOYMENT_MCP_HETZNER_CLOUD_TOKEN"),
        "file": "hetzner_cloud_token",
        "alt_files": [],
        "mcp_process": "deployment_mcp",
        "description": "Hetzner Cloud API",
    },
    "github": {
        "env": "GITHUB_TOKEN",
        "mcp_env": ("GITHUB_PERSONAL_ACCESS_TOKEN"),
        "file": "github_token",
        "alt_files": [],
        "mcp_process": None,
        "description": "GitHub PAT",
    },
    "ionos": {
        "env": "IONOS_API_KEY",
        "mcp_env": "DEPLOYMENT_MCP_IONOS_API_KEY",
        "file": "ionos_api_key",
        "alt_files": [],
        "mcp_process": "deployment_mcp",
        "description": "IONOS DNS API",
    },
    "openai": {
        "env": "OPENAI_API_KEY",
        "mcp_env": None,
        "file": "openai_api_key",
        "alt_files": [],
        "mcp_process": None,
        "description": "OpenAI API",
    },
    "anthropic": {
        "env": "ANTHROPIC_API_KEY",
        "mcp_env": None,
        "file": "anthropic_api_key",
        "alt_files": [],
        "mcp_process": None,
        "description": "Anthropic API",
    },
    "groq": {
        "env": "GROQ_API_KEY",
        "mcp_env": None,
        "file": "groq_api_key",
        "alt_files": ["groq_api_token"],
        "mcp_process": None,
        "description": "Groq API",
    },
    "together": {
        "env": "TOGETHER_API_KEY",
        "mcp_env": None,
        "file": "together_api_key",
        "alt_files": [],
        "mcp_process": None,
        "description": "Together AI API",
    },
    "pypi": {
        "env": "PYPI_TOKEN",
        "mcp_env": None,
        "file": "pypi_iildehnert_token",
        "alt_files": [],
        "mcp_process": None,
        "description": "PyPI Upload Token",
    },
    "dvelop": {
        "env": "DVELOP_API_KEY",
        "mcp_env": None,
        "file": "dvelop_api_key",
        "alt_files": [],
        "mcp_process": None,
        "description": "d.velop DMS API",
    },
    "paperless": {
        "env": "PAPERLESS_API_TOKEN",
        "mcp_env": "PAPERLESS_API_TOKEN",
        "file": None,
        "alt_files": [],
        "mcp_process": None,
        "description": "Paperless-ngx API",
    },
}


# ─── Toleranter Leser: bare UND NAME=WERT ─────────────────────
# Anlass (2026-09-13): eine Secret-Datei ohne ``NAME=WERT``-Form wurde per
# ``. datei`` gesourced — die Shell fuehrte den nackten Wert als Kommando aus
# und schrieb ihn in die eigene Fehlermeldung. Der Weg heraus ist die
# ``NAME=WERT``-Form fuer alle Dateien (Stufe 3). Damit die Umstellung nicht
# reihenweise Leser bricht, muss VORHER jeder Leser BEIDE Formen verstehen —
# das ist diese Funktion. Sie ist die einzige Stelle, die eine Secret-Datei
# interpretiert; niemand liest mehr selbst ``read_text().strip()``.

#: Ein Variablenname in Shell-/Env-Schreibweise. Bewusst streng: ein nackter
#: Wert mit ``=`` darin (base64-Auffuellung!) darf NICHT als ``NAME=WERT``
#: durchgehen.
_NAME_MUSTER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def _zeilen(text: str) -> list[str]:
    """Nicht-leere Zeilen ohne ``#``-Kommentare."""
    return [z for z in text.splitlines() if z.strip() and not z.strip().startswith("#")]


def _entklammere(wert: str) -> str:
    """Beidseitig gleiche Anfuehrungszeichen entfernen, sonst unveraendert."""
    wert = wert.strip()
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in ("'", '"'):
        return wert[1:-1]
    return wert


def ist_kv_zeile(name: str, wert: str) -> bool:
    """True wenn ``name=wert`` als ``NAME=WERT``-Variable zaehlt.

    Sonderregel: ein alphanumerischer nackter Wert mit ``=``-Auffuellung
    (``ABC=`` / ``ABC==``) ist KEINE leere Variable, sondern base64-Padding
    eines bare-Werts — im Zweifel bare, damit sich fuer bestehende Dateien
    nichts aendert. Einzige Stelle, die diese Entscheidung trifft: ``_kv_paare``
    hier UND ``tools/secrets_pruefen.py::erkenne_form`` verwenden sie, damit
    Leser und Melder nie auseinanderlaufen (Refs #3155).
    """
    if not _NAME_MUSTER.match(name.strip()):
        return False
    wert = _entklammere(wert)
    return bool(wert) and set(wert) != {"="}


def _kv_paare(text: str) -> list[tuple[str, str]] | None:
    """``[(NAME, WERT), …]`` wenn ALLE Inhaltszeilen KV-Form haben, sonst None.

    ``None`` heisst: bare — der ganze Inhalt ist der Wert.
    """
    zeilen = _zeilen(text)
    if not zeilen:
        return None
    paare: list[tuple[str, str]] = []
    for zeile in zeilen:
        name, trenner, wert = zeile.strip().partition("=")
        if not trenner or not ist_kv_zeile(name, wert):
            return None
        paare.append((name.strip(), _entklammere(wert)))
    return paare


def secret_wert(pfad: Path | str, name: str | None = None) -> str:
    """Wert einer Secret-Datei — versteht ``bare`` und ``NAME=WERT``.

    * ``bare`` (ganze Datei = Wert): ``inhalt.strip()``, exakt wie frueher.
    * genau EINE ``NAME=WERT``-Zeile (Kommentare/Leerzeilen davor erlaubt):
      der Teil hinter dem ersten ``=``, ohne beidseitig gleiche
      Anfuehrungszeichen.
    * mehrere Variablen: ``name=`` waehlt aus; ohne ``name`` ``ValueError``.

    Der Wert wird nie geloggt oder ausgegeben — nur zurueckgegeben.
    """
    text = Path(pfad).read_text(encoding="utf-8")
    return _waehle(_kv_paare(text), text, name, pfad)


def secret_bytes(pfad: Path | str, name: str | None = None) -> bytes:
    """Wie :func:`secret_wert`, liefert aber Bytes (Schluesselmaterial).

    Der Umweg ueber ``latin-1`` ist verlustfrei (Byte ↔ Zeichen 1:1) und
    haelt auch Werte aus, die kein gueltiges UTF-8 sind.
    """
    roh = Path(pfad).read_bytes()
    paare = _kv_paare(roh.decode("latin-1"))
    if paare is None:
        # bare: auf Byte-Ebene trimmen — ``str.strip()`` wuerde auch Zeichen
        # wie 0xA0 abschneiden, die in Schluesselmaterial Nutzlast sind.
        return roh.strip()
    return _waehle(paare, "", name, pfad).encode("latin-1")


def _waehle(
    paare: list[tuple[str, str]] | None,
    text: str,
    name: str | None,
    pfad: Path | str,
) -> str:
    if paare is None:
        return text.strip()
    if name is not None:
        for eig_name, wert in paare:
            if eig_name == name:
                return wert
        raise ValueError(f"Variable {name} steht nicht in {pfad}")
    if len(paare) > 1:
        namen = ", ".join(sorted(n for n, _ in paare))
        raise ValueError(f"mehrere Variablen — Name angeben ({pfad}: {namen})")
    return paare[0][1]


def _read_file(path: Path) -> str:
    """Read secret file, return its value (bare oder ``NAME=WERT``).

    ``ValueError`` (mehrere Variablen) wird nicht abgefangen: ein
    stilles ``""`` sieht aus wie „Secret fehlt" und schickt die Suche in die
    naechste Quelle, statt die Datei zu melden, die eine Auswahl braucht.
    """
    try:
        if path.exists():
            return secret_wert(path)
    except (OSError, PermissionError):
        pass
    return ""


def _read_mcp_env(
    process_name: str,
    env_var: str,
) -> str:
    """Read env var from running MCP process."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", process_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        pids = result.stdout.strip().splitlines()
        if not pids:
            return ""
        pid = pids[0].strip()
        env_path = Path(f"/proc/{pid}/environ")
        if not env_path.exists():
            return ""
        raw = env_path.read_bytes()
        for entry in raw.split(b"\x00"):
            decoded = entry.decode(
                "utf-8",
                errors="replace",
            )
            if decoded.startswith(f"{env_var}="):
                return decoded.split("=", 1)[1]
    except (
        subprocess.TimeoutExpired,
        OSError,
        PermissionError,
    ):
        pass
    return ""


def get_secret(
    name: str,
    default: str = "",
) -> str:
    """Resolve a secret by logical name.

    Args:
        name: Logical name from REGISTRY
              (e.g. "cloudflare", "github")
        default: Fallback value

    Returns:
        Secret value or default
    """
    entry = REGISTRY.get(name)
    if not entry:
        return default

    # 1. Primary env var
    env_var = entry.get("env", "")
    if env_var:
        val = os.environ.get(env_var, "")
        if val:
            return val

    # 2. MCP env var name
    mcp_env = entry.get("mcp_env", "")
    if mcp_env and mcp_env != env_var:
        val = os.environ.get(mcp_env, "")
        if val:
            return val

    # 3. Canonical secret file
    canonical = entry.get("file", "")
    if canonical:
        val = _read_file(SECRETS_DIR / canonical)
        if val:
            return val

    # 4. Alternative/legacy files
    for alt in entry.get("alt_files", []):
        val = _read_file(SECRETS_DIR / alt)
        if val:
            return val

    # 5. MCP process env (last resort)
    proc = entry.get("mcp_process", "")
    if proc and mcp_env:
        val = _read_mcp_env(proc, mcp_env)
        if val:
            # Cache to file for next time
            if canonical:
                _cache_secret(canonical, val)
            return val

    return default


def _cache_secret(
    filename: str,
    value: str,
) -> None:
    """Write secret to ~/.secrets/ for caching."""
    path = SECRETS_DIR / filename
    try:
        path.write_text(value + "\n")
        path.chmod(0o600)
    except OSError:
        pass


def require_secret(name: str) -> str:
    """Get secret or raise RuntimeError."""
    val = get_secret(name)
    if not val:
        entry = REGISTRY.get(name, {})
        raise RuntimeError(
            f"Secret '{name}' nicht gefunden.\n"
            f"  Env: {entry.get('env', '?')}\n"
            f"  File: ~/.secrets/"
            f"{entry.get('file', '?')}\n"
            f"  MCP: {entry.get('mcp_env', '-')}"
        )
    return val


def verify_token(name: str) -> bool:
    """Test if a token actually works."""
    import urllib.request
    import json

    entry = REGISTRY.get(name, {})
    test_url = entry.get("test_url", "")
    if not test_url:
        return bool(get_secret(name))

    token = get_secret(name)
    if not token:
        return False

    try:
        req = urllib.request.Request(test_url)
        req.add_header(
            "Authorization",
            f"Bearer {token}",
        )
        resp = urllib.request.urlopen(
            req,
            timeout=10,
        )
        data = json.loads(resp.read())
        return data.get("success", False)
    except Exception:
        return False


def _fingerprint(val: str) -> str:
    """Wiedererkennbar, aber nicht rekonstruierbar: Laenge + SHA-256-Praefix.

    Ersetzt das fruehere ``val[:8]``. Acht Zeichen sind bei manchen Anbietern
    nur der oeffentliche Praefix (``sk-proj-``), bei anderen ein Drittel eines
    kurzen Tokens — und ``print_status()`` schrieb sie fuer JEDES Secret nach
    stdout, also ins Terminal, in den Scrollback und in jedes kopierte Log.

    Der Fingerabdruck leistet, wofuer die Vorschau da war: zwei Kopien
    desselben Secrets vergleichen, ohne den Wert zu kennen. Genau so wurde am
    2026-07-29 belegt, dass Prod einen anderen Groq-Schluessel trug als
    ``~/.secrets``.
    """
    import hashlib

    return f"{len(val)}·{hashlib.sha256(val.encode()).hexdigest()[:8]}"


def status_all() -> dict[str, dict]:
    """Check status of all known secrets."""
    results = {}
    for name, entry in REGISTRY.items():
        val = get_secret(name)
        results[name] = {
            "found": bool(val),
            # KEINE Vorschau des Werts — siehe _fingerprint().
            "fingerprint": _fingerprint(val) if val else "",
            "description": entry.get(
                "description",
                "",
            ),
            "env": entry.get("env", ""),
            "file": entry.get("file", ""),
        }
    return results


def print_status() -> None:
    """Print status of all secrets to stdout — ohne Werte, nur Fingerabdruecke."""
    print("Secret-Status (infra/lib/secrets.py)")
    print("=" * 60)
    for name, info in status_all().items():
        icon = "✅" if info["found"] else "❌"
        fp = info["fingerprint"] or "MISSING"
        print(f"  {icon}  {name:20} {fp:15} {info['description']}")
    print()
    print("Fingerabdruck = Laenge·SHA-256(8). Vergleichbar, nicht rekonstruierbar.")


if __name__ == "__main__":
    print_status()

    # Validate Cloudflare token
    print("\n--- Token-Validierung ---")
    if get_secret("cloudflare"):
        ok = verify_token("cloudflare")
        icon = "✅" if ok else "❌"
        print(
            f"  {icon}  cloudflare API-Token funktioniert"
            if ok
            else f"  {icon}  cloudflare API-Token UNGÜLTIG!"
        )
    else:
        print("  ⏭  cloudflare: kein Token")

    sys.exit(0)
