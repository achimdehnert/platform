"""Lizenz-Gate fuer Marken-Assets aus design-hub — bewusst importfrei.

Warum ein eigenes Modul: `print_agent` importiert WeasyPrint, litellm und
markdown auf Modulebene. Damit waren die Tests seines Lizenz-Gates in CI nicht
lauffaehig (dort fehlt WeasyPrint) und liefen nie. Die Entscheidung selbst
braucht nichts davon; hier liegt sie so, dass `make test` sie pruefen kann —
dasselbe Muster wie `llm_gate` und `profile_policy`.

Die Regel: ein Logo oder eine Schrift unter `assets/<bereich>/` wird nur
eingebettet, wenn das Profil `allowed_assets.<bereich>: true` setzt. Bis
2026-09-16 hing jedes Asset am Flag `db`; dadurch kamen nur DB-Logos je in ein
PDF, das freigegebene HNU-Logo (`assets/shared/`) und das IIL-Logo
(`assets/iil/`) wurden in jedem Lauf verworfen.
"""

from __future__ import annotations

#: Asset-Bereiche in design-hub; der Name ist zugleich das Flag in `allowed_assets`.
ASSET_BEREICHE = ("db", "iil", "shared")

#: Datei-Endung -> MIME-Subtyp fuer data:-URIs. `svg` ist KEIN gueltiger Subtyp;
#: `data:image/svg;base64,...` wird von WeasyPrint und Browsern still verworfen.
BILD_MIME = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "png": "png",
    "svg": "svg+xml",
    "webp": "webp",
}


def asset_freigegeben(rel_pfad: str, allowed: dict) -> tuple[bool, str]:
    """Darf die Datei unter `rel_pfad` (relativ zu design-hub) eingebettet werden?

    Entscheidet das Flag des Bereichs, in dem die Datei liegt. Liegt sie in
    keinem bekannten Bereich, gilt fail-closed das strengste Flag `db` — das
    war das Verhalten vor 2026-09-16 und bleibt fuer unklare Pfade bestehen.

    Rueckgabe: ``(freigegeben, bereich)``; den Bereich braucht die Meldung.
    """
    teile = rel_pfad.split("/")
    if len(teile) > 2 and teile[0] == "assets" and teile[1] in ASSET_BEREICHE:
        return bool(allowed.get(teile[1])), teile[1]
    return bool(allowed.get("db")), "db"


def bild_mime(endung: str) -> str:
    """MIME-Subtyp fuer eine Bild-Endung (ohne Punkt, beliebige Schreibweise)."""
    e = endung.lstrip(".").lower()
    return BILD_MIME.get(e, e)
