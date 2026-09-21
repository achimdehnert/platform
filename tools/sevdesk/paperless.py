#!/usr/bin/env python3
"""Paperless (docs.iil.pet) als Quelle fuer sevdesk-Belege — Tags tragen Mandant
und Kostenstelle (Owner-Konvention 2026-09-21).

Warum ssh statt REST: die Paperless-API sitzt hinter Cloudflare Access (403 auch
mit gueltigem Token, verifiziert 2026-09-04); der einzige Weg ist
``ssh hetzner-prod`` + ``docker exec iil_dochub_web manage.py shell``. Das PDF
kommt per ``docker cp`` + ``scp`` — nur in ein Sitzungs-Verzeichnis, nie in eine
Ablage (Owner: „du brauchst nichts ablegen, da in Paperless").

Konvention der Tags:
- ``edv`` / ``iil``            → Mandant (:func:`mandant_aus_tags`)
- ``macan`` / ``x4`` / ``8er`` → sevdesk-Kostenstelle gleichen Namens
  (:func:`kostenstelle_aus_tags`); ein Tag darf zusaetzlich die sevdesk-ID
  tragen (``macan 338405``) — dann wird die ID genommen und der Name geprueft.
  Existiert die Kostenstelle im Mandanten nicht, wird NICHT geraten: die
  Funktion gibt ``None`` zurueck, der Aufrufer bricht ab.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

SSH_HOST = "hetzner-prod"
CONTAINER = "iil_dochub_web"

#: Tag-Namen, die einen Mandanten benennen (siehe ``mandant.SECRET_DATEIEN``).
MANDANTEN_TAGS = ("edv", "iil")

_TAG_MIT_ID = re.compile(r"^(?P<name>.+?)\s+(?P<id>\d{3,})$")


def _shell(code: str) -> str:
    """Fuehrt Python im Paperless-Container aus, gibt stdout zurueck."""
    r = subprocess.run(
        ["ssh", SSH_HOST, f"docker exec -i {CONTAINER} python3 manage.py shell"],
        input=code,
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout


def dokument(dok_id: int) -> dict:
    """Titel, Tags, Korrespondent und Original-Pfad eines Paperless-Dokuments."""
    code = f"""
import json
from documents.models import Document
d = Document.objects.get(pk={int(dok_id)})
print("JSON " + json.dumps({{
    "id": d.id,
    "title": d.title,
    "tags": [t.name for t in d.tags.all()],
    "correspondent": str(d.correspondent) if d.correspondent else None,
    "created": str(d.created),
    "source_path": str(d.source_path),
}}))
"""
    for zeile in _shell(code).splitlines():
        if zeile.startswith("JSON "):
            return json.loads(zeile[5:])
    raise RuntimeError(f"Paperless-Dokument {dok_id}: keine Antwort aus dem Container")


def pdf_holen(dok: dict, ziel_dir: Path) -> Path:
    """Kopiert das Original aus dem Container nach ``ziel_dir`` (Sitzungs-Verzeichnis)."""
    ziel_dir.mkdir(parents=True, exist_ok=True)
    ziel = ziel_dir / f"paperless-{dok['id']}.pdf"
    tmp = f"/tmp/paperless-{dok['id']}.pdf"
    subprocess.run(
        ["ssh", SSH_HOST, f"docker cp {CONTAINER}:'{dok['source_path']}' {tmp}"],
        check=True,
    )
    subprocess.run(["scp", "-q", f"{SSH_HOST}:{tmp}", str(ziel)], check=True)
    subprocess.run(["ssh", SSH_HOST, f"rm -f {tmp}"], check=True)
    return ziel


def mandant_aus_tags(tags: list[str]) -> str | None:
    """Genau ein Mandanten-Tag → Mandant; keiner oder mehrere → None (nie raten)."""
    treffer = [t for t in tags if t.strip().lower() in MANDANTEN_TAGS]
    return treffer[0].strip().lower() if len(treffer) == 1 else None


def tag_zerlegen(tag: str) -> tuple[str, str | None]:
    """``"macan 338405"`` → ``("macan", "338405")``; ``"macan"`` → ``("macan", None)``."""
    m = _TAG_MIT_ID.match(tag.strip())
    if m:
        return m.group("name").strip().lower(), m.group("id")
    return tag.strip().lower(), None


def kostenstelle_aus_tags(tags: list[str], kostenstellen: list[dict]) -> dict | None:
    """Kostenstelle, die ein Tag benennt — Name gleich (Gross/Klein egal) oder
    ``name id``-Form mit passender ID. Genau ein Treffer, sonst None.

    ``kostenstellen`` ist die Antwort von ``GET /CostCentre`` (``id``, ``name``).
    """
    nach_name = {str(k["name"]).strip().lower(): k for k in kostenstellen}
    treffer: list[dict] = []
    for tag in tags:
        name, kid = tag_zerlegen(tag)
        k = nach_name.get(name)
        if k is None:
            continue
        if kid is not None and str(k["id"]) != kid:
            # Tag nennt eine ID, die nicht zum Namen passt — lieber gar nichts
            # als das Falsche (ID-Kollision ueber Mandanten hinweg).
            continue
        treffer.append(k)
    return treffer[0] if len(treffer) == 1 else None
