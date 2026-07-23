"""Datenschutz-Gate fürs LLM-Enrichment des Print-Agents (#1297).

**Warum ein eigenes Modul:** ``print_agent.py`` zieht beim Import ``litellm``,
``markdown`` und ``weasyprint``. Ein Test gegen die Kern-Invariante („ohne
Opt-in verlässt kein Dokumentinhalt die Maschine") müsste dort mit
``pytest.importorskip`` arbeiten und würde in CI — die nur ``pytest pyyaml
pydantic`` installiert — **still übersprungen** statt zu prüfen. Die Zusage
wäre ungegatet. Dieses Modul kommt mit der Standardbibliothek aus und ist
deshalb aus ``tools/tests/`` (bereits in ``make test``) prüfbar.

Die Invariante in einem Satz: an ein LLM darf ein Dokumentauszug nur gehen,
wenn das Ziel entweder **loopback-lokal** ist oder der Aufrufer externe
Anbieter ausdrücklich per ``PRINT_AGENT_ALLOW_EXTERNAL=1`` erlaubt hat.
"""

import os
from urllib.parse import urlsplit

# Datenschutz-Default (#1297): lokales Ollama, kein Dokument-Abfluss.
DEFAULT_PRIMARY = "ollama/qwen2.5:3b"
DEFAULT_FALLBACK = ""  # kein externer Fallback per Default
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"

_LOCAL_MODEL_PREFIXES = ("ollama/", "ollama_chat/")
_TRUTHY = {"1", "true", "yes", "on"}

# Nur echte Loopback-Ziele. `0.0.0.0` ist bewusst NICHT dabei: als Ziel-Adresse
# ist es unterspezifiziert, und ein Tippfehler soll nicht still als "lokal" gelten.
_LOOPBACK_HOSTS = {"localhost", "::1"}


def ollama_host() -> str:
    """Ollama-Endpunkt aus der Umgebung — **bei jedem Aufruf** gelesen.

    Bewusst keine Modul-Konstante: ein beim Import eingefrorener Wert wäre in
    Tests nur über das Modulattribut steuerbar und würde eine Änderung der
    Umgebung zur Laufzeit verschlucken.
    """
    return (
        os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).strip()
        or DEFAULT_OLLAMA_HOST
    )


def is_local_model(model: str) -> bool:
    """True für Modellstrings, die über einen Ollama-Endpunkt laufen.

    Sagt **nichts** darüber, ob dieser Endpunkt auf dieser Maschine liegt —
    dafür ist ``is_loopback_host`` zuständig.
    """
    return model.strip().lower().startswith(_LOCAL_MODEL_PREFIXES)


def is_loopback_host(url: str) -> bool:
    """True, wenn die URL auf diese Maschine zeigt (127.0.0.0/8, ::1, localhost).

    Ein entfernter Ollama (z. B. ``ollama-on-dev`` auf 88.99.38.75) ist damit
    korrekt **kein** lokales Ziel — der Dokumentauszug verließe die Maschine.
    """
    host = (urlsplit(url).hostname or "").strip().lower()
    if not host:
        return False
    if host in _LOOPBACK_HOSTS:
        return True
    return host.startswith("127.")


def external_allowed() -> bool:
    """Opt-in für Ziele außerhalb dieser Maschine (``PRINT_AGENT_ALLOW_EXTERNAL``)."""
    return os.environ.get("PRINT_AGENT_ALLOW_EXTERNAL", "").strip().lower() in _TRUTHY


def leaves_machine(model: str, host: str | None = None) -> bool:
    """True, wenn ein Aufruf dieses Modells den Inhalt von dieser Maschine wegträgt.

    Zwei Fälle: ein externer Anbieter (Cerebras/Groq/OpenAI/…) — oder ein
    Ollama-Modell gegen einen nicht-loopback Endpunkt.
    """
    if not is_local_model(model):
        return True
    return not is_loopback_host(host if host is not None else ollama_host())


def skip_reason(model: str, host: str | None = None) -> str | None:
    """``None`` = Aufruf erlaubt; sonst der Grund, warum er unterbleibt.

    Der Grund ist für die CLI-Ausgabe gedacht und benennt den konkreten Fall,
    damit „übersprungen" nicht wie ein Fehler aussieht.
    """
    if not leaves_machine(model, host):
        return None
    if external_allowed():
        return None
    target = host if host is not None else ollama_host()
    if is_local_model(model):
        return (
            f"⛔ {model} übersprungen — OLLAMA_HOST zeigt auf {target}, also NICHT auf diese "
            f"Maschine. Opt-in nötig (PRINT_AGENT_ALLOW_EXTERNAL=1)."
        )
    return (
        f"⛔ Externer LLM {model} übersprungen — Opt-in nötig "
        f"(PRINT_AGENT_ALLOW_EXTERNAL=1). Dokumentinhalt bleibt lokal."
    )
