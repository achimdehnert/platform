"""Ein Modellstring aus dem ADR-208-Resolver — statt eines Pins im Skript.

ADR-208 hält fest, dass Modell-Identität an **einer** versionierten Stelle steht
und ein Retirement genau einen PR an dieser Datei kostet. Für die
Plattform-Skripte war das bis 2026-08-25 Theorie: `run_prompt.py` trug
`groq/llama-3.3-70b-versatile` hart im Code, Groq listete es längst nicht mehr,
und der Aufruf fiel still auf die Template-Variante zurück. Der Prompt wurde
schlechter, ohne dass irgendwo etwas rot wurde.

Der Resolver liegt in `mcp-hub` (dort ist ADR-208 implementiert). Diese Datei
liest ihn, wenn er erreichbar ist, und sagt sonst laut, worauf sie
zurückgefallen ist — ein stiller Rückfall ist genau der Fehler, den sie behebt.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Fällt nur, wenn der Resolver gar nicht lesbar ist. Gemessen am 2026-08-25 bei
#: Cerebras gelistet; wird der auch abgemeldet, meldet es die nächtliche
#: Liveness-Prüfung in mcp-hub — und dann ist das hier die zweite Stelle, die
#: nachgezogen werden muss. Deshalb ist der Resolver-Pfad der Normalfall.
NOTNAGEL = "cerebras/gpt-oss-120b"


def resolver_pfad() -> Path:
    if os.environ.get("IIL_MODEL_RESOLVER"):
        return Path(os.environ["IIL_MODEL_RESOLVER"])
    basis = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
    return (
        basis / "mcp-hub" / "orchestrator_mcp" / "iil_routing" / "model_resolver.yaml"
    )


def modell_fuer(alias: str = "iil/fast-current", *, still: bool = False) -> str:
    """Der aufgelöste Pin — oder der Notnagel, dann aber mit Ansage."""
    pfad = resolver_pfad()
    try:
        import yaml  # noqa: PLC0415 — optionale Abhängigkeit, nur hier gebraucht

        aliasse = yaml.safe_load(pfad.read_text(encoding="utf-8"))["aliases"]
        return str(aliasse[alias]["model"])
    except Exception as exc:  # noqa: BLE001 — jeder Grund führt zur selben Antwort
        if not still:
            print(
                f"[iil_modell] Resolver nicht lesbar ({type(exc).__name__}: {exc}) — "
                f"nutze {NOTNAGEL}. Quelle wäre {pfad}",
                file=sys.stderr,
            )
        return NOTNAGEL
