"""Dateien nur für den eigenen Nutzer schreiben — Rechte 600, atomar (#3642).

Warum ein eigener Schreibweg: ``Path.write_text`` legt eine neue Datei mit der
umask des Prozesses an. Bei umask 002 entsteht 664, die Datei ist dann für
andere Nutzer des Rechners lesbar. Ledger, Archiv, Anker und Link-Listen
enthalten Mail-Metadaten (Absender, Betreffe) und gehören nur dem Owner.

``mkstemp`` legt die Zwischendatei unabhängig von der umask mit 600 an,
``os.replace`` setzt sie an die Stelle des Ziels. Damit wird auch eine schon
bestehende 664-Datei beim nächsten Schreiben wieder 600, und ein Abbruch
mitten im Schreiben hinterlässt nie eine halbe Datei.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def schreibe_privat(pfad: Path | str, text: str) -> None:
    """Schreibt ``text`` nach ``pfad`` mit Rechten 600, über Zwischendatei + replace."""
    pfad = Path(pfad)
    fd, zwischen = tempfile.mkstemp(
        dir=pfad.parent, prefix=f".{pfad.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as datei:
            datei.write(text)
            datei.flush()
            os.fsync(datei.fileno())
        os.replace(zwischen, pfad)
    except BaseException:
        Path(zwischen).unlink(missing_ok=True)
        raise
