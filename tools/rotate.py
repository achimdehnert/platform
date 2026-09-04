#!/usr/bin/env python3
"""Rotationswerkzeug Stufe 1 — KONZ-dev-hub-005, platform#2813.

    python3 tools/rotate.py pruefen GENESOR_PROJECT_TOKEN
    python3 tools/rotate.py lauf GENESOR_PROJECT_TOKEN --quelle ~/shared/<datei>
    python3 tools/rotate.py widerruf-geprueft <LAUF-ID>
    python3 tools/rotate.py faellig [--kurz]
    python3 tools/rotate.py log-pruefen

**Wer startet was:** ``pruefen``, ``faellig`` und ``log-pruefen`` lesen nur und
laufen im Agenten. ``lauf`` beruehrt einen Wert und wird vom Owner gestartet
(Auto-Mode-Classifier, §5.2 "Ausfuehrung") — das Werkzeug aendert daran nichts.

Der Wert wird nie ausgegeben, nie protokolliert und lebt nur so lange im
Prozess, wie das Setzen dauert.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rotation.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
