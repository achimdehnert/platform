"""Lesezugriff auf ``infra/secrets-inventory.yaml`` — der SSoT des Laufs.

Das Werkzeug schreibt **nie** ins Inventar (§5.4: "Inventar ist SSoT"). Es liest
daraus, welche Konsumenten ein Secret hat, wie man die Wirkung belegt und wann
der naechste Lauf faellig ist.

Die alte String-Form von ``consumers[]`` bleibt lesbar und wird als
:class:`Konsument` mit ``kind=None`` gefuehrt: nicht rotierbar, aber **sichtbar
und gezaehlt**. Genau das ist AD-3 — wer einen Konsumenten weglassen kann, um
sich ``proof`` zu sparen, tut es.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import yaml

WURZEL = Path(__file__).resolve().parent.parent.parent
INVENTAR_PFAD = WURZEL / "infra" / "secrets-inventory.yaml"
CANONICAL_PFAD = WURZEL / "registry" / "canonical.yaml"
SCHLEUSE = Path.home() / "shared"

#: Sektionen mit eigener Gestalt — Stufe 2 (host_env_file) holt sie dazu.
KEINE_EINTRAEGE = {"server_side", "local", "sops"}

#: Aus ``rotation:`` abgeleitete Frist. ``on_demand`` wird nie von allein faellig.
FRIST_TAGE: dict[str, int | None] = {
    "monthly": 30,
    "quarterly": 91,
    "yearly": 365,
    "on_demand": None,
}

#: Dateien in der Schleuse mit einem dieser Woerter im Namen sind Kandidaten
#: fuer Altlasten (AD-9). Der Melder nennt NUR Namen und Alter, nie Inhalte.
ALTLAST_WOERTER = re.compile(r"token|secret|key|passwor|pat\b", re.IGNORECASE)
ALTLAST_TAGE = 7


@dataclass(frozen=True)
class Konsument:
    kind: str | None
    ref: str
    name: str | None = None
    proof: dict[str, Any] | None = None
    #: True, wenn der Eintrag noch die alte String-Form ist.
    unvollstaendig: bool = False

    @property
    def rotierbar(self) -> bool:
        """Ohne ``proof`` wird nicht gesetzt — Setzen ohne Beleg ist nicht gesetzt."""
        return bool(self.kind and self.proof)


@dataclass(frozen=True)
class Secret:
    sektion: str
    name: str
    eintrag: dict[str, Any] = field(repr=False)
    konsumenten: tuple[Konsument, ...] = ()

    @property
    def rotation(self) -> str | None:
        return self.eintrag.get("rotation")

    @property
    def ohne_beleg(self) -> tuple[Konsument, ...]:
        return tuple(k for k in self.konsumenten if not k.rotierbar)


def _iso(wert: Any) -> Any:
    if isinstance(wert, (date, datetime)):
        return wert.isoformat()
    if isinstance(wert, dict):
        return {k: _iso(v) for k, v in wert.items()}
    if isinstance(wert, list):
        return [_iso(v) for v in wert]
    return wert


def lade(pfad: Path | None = None) -> dict[str, Any]:
    pfad = pfad or INVENTAR_PFAD
    return _iso(yaml.safe_load(pfad.read_text(encoding="utf-8")) or {})


def _konsument(roh: Any) -> Konsument:
    if isinstance(roh, str):
        return Konsument(kind=None, ref=roh, unvollstaendig=True)
    return Konsument(
        kind=roh.get("kind"),
        ref=roh.get("ref", ""),
        name=roh.get("name"),
        proof=roh.get("proof"),
    )


def secrets(inv: dict[str, Any]) -> list[Secret]:
    raus: list[Secret] = []
    for sektion, gruppe in inv.items():
        if sektion in KEINE_EINTRAEGE or not isinstance(gruppe, dict):
            continue
        for name, eintrag in gruppe.items():
            if not isinstance(eintrag, dict):
                continue
            raus.append(
                Secret(
                    sektion=sektion,
                    name=name,
                    eintrag=eintrag,
                    konsumenten=tuple(
                        _konsument(k) for k in (eintrag.get("consumers") or [])
                    ),
                )
            )
    return raus


def finde(inv: dict[str, Any], secret_name: str) -> Secret:
    """Genau ein Treffer, sonst Fehler.

    Mehrdeutigkeit wird nicht aufgeloest, sondern gemeldet: derselbe Name in
    zwei Sektionen kann zwei verschiedene Geheimnisse meinen (``DISCORD_WEBHOOK``
    vs. ``DISCORD_WEBHOOK_URL`` war schon ein solcher Fall), und ein Werkzeug,
    das hier raet, setzt den Wert im falschen Repo.
    """
    treffer = [s for s in secrets(inv) if s.name == secret_name]
    if not treffer:
        bekannt = ", ".join(sorted(s.name for s in secrets(inv))[:8])
        raise KeyError(
            f"{secret_name} steht nicht im Inventar. Bekannt u.a.: {bekannt} …"
        )
    if len(treffer) > 1:
        wo = ", ".join(f"{s.sektion}.{s.name}" for s in treffer)
        raise KeyError(f"{secret_name} ist mehrdeutig: {wo}. Sektion angeben.")
    return treffer[0]


# --------------------------------------------------------------------------
# Org-Aufloesung — geraten wird nichts
# --------------------------------------------------------------------------
def org_aufloesung(canonical_pfad: Path | None = None):
    """Liefert ``repo -> org``-Funktion aus ``registry/canonical.yaml``.

    Reihenfolge wie im Registry-Generator: expliziter ``rich.github``-Eintrag,
    dann ``meta.repo_owner``-Override, dann ``owner_prefix_rules``, dann der
    Default. Der Default steht bewusst zuletzt — er war die Quelle der
    404-Klasse (frist-hub/bahn-hub, ADR-297).
    """
    canon = yaml.safe_load(
        (canonical_pfad or CANONICAL_PFAD).read_text(encoding="utf-8")
    )
    meta = canon.get("meta", {})
    repos = canon.get("repos", {})

    def org(repo: str) -> str | None:
        eintrag = repos.get(repo) or {}
        github = (eintrag.get("rich") or {}).get("github")
        if github and "/" in github:
            return github.split("/", 1)[0]
        if repo in meta.get("repo_owner", {}):
            return meta["repo_owner"][repo]
        for regel in meta.get("owner_prefix_rules", []):
            if repo.startswith(regel["prefix"]):
                return regel["owner"]
        return (meta.get("server") or {}).get("github_org")

    return org


# --------------------------------------------------------------------------
# Faelligkeit + Altlasten
# --------------------------------------------------------------------------
def faellig_seit(
    secret: Secret, letzter: dict[str, Any] | None, heute: date
) -> int | None:
    """Tage ueberfaellig, oder ``None`` wenn nicht faellig / keine Frist.

    Ein Lauf mit ``status: offen`` zaehlt NICHT als Lauf — sonst setzte ein
    gescheiterter Versuch die Uhr zurueck und das Secret verschwaende aus dem
    Melder, obwohl nichts belegt ist.
    """
    tage = FRIST_TAGE.get(secret.rotation or "")
    if tage is None:
        return None
    if letzter and letzter.get("status") == "abgeschlossen":
        basis_roh = letzter.get("beendet") or letzter.get("gestartet") or ""
        try:
            basis = datetime.fromisoformat(str(basis_roh).replace("Z", "+00:00")).date()
        except ValueError:
            basis = None
        if basis:
            ueber = (heute - basis).days - tage
            return ueber if ueber > 0 else None
    # nie belegt gelaufen -> faellig, Ueberfaelligkeit unbekannt (0 = "faellig")
    return 0


def altlasten(schleuse: Path | None = None, heute: date | None = None) -> list[str]:
    """Namen (nie Inhalte) von Dateien in ``~/shared/``, die nach Schluesselmaterial
    aussehen und aelter als eine Woche sind. AD-9: die Leerung des Werkzeugs
    trifft nur die Dateien, die es selbst verarbeitet hat."""
    schleuse = schleuse or SCHLEUSE
    heute = heute or date.today()
    if not schleuse.is_dir():
        return []
    raus = []
    for pfad in sorted(schleuse.iterdir()):
        if not pfad.is_file() or not ALTLAST_WOERTER.search(pfad.name):
            continue
        try:
            alter = (heute - date.fromtimestamp(pfad.stat().st_mtime)).days
        except OSError:
            continue
        if alter > ALTLAST_TAGE:
            raus.append(f"{pfad.name} ({alter}d)")
    return raus


def quelle_lesen(pfad: Path) -> bytes:
    """Wert aus der Schleuse lesen — mit Rechte-Warnung, ohne Ausgabe.

    Kein ``strip()`` auf dem gesamten Inhalt: bei PEM-Dateien ist das
    Zeilenende bedeutungstragend. Nur ein abschliessender Zeilenumbruch faellt,
    weil ``echo`` ihn anhaengt und GitHub ihn als Teil des Werts speichern wuerde.
    """
    roh = pfad.read_bytes()
    modus = pfad.stat().st_mode & 0o777
    if modus & 0o077 and os.name == "posix":
        # Kein Abbruch: die Schleuse ist per Definition transient. Aber es wird gesagt.
        print(f"  ! {pfad.name} hat Rechte {modus:o} — nach dem Lauf wird sie geleert.")
    if roh.endswith(b"\n"):
        roh = roh[:-1]
    if not roh:
        raise ValueError(f"{pfad} ist leer — kein Wert zu uebernehmen.")
    return roh


def formatiere_konsumenten(konsumenten: Iterable[Konsument]) -> list[str]:
    zeilen = []
    for k in konsumenten:
        if k.unvollstaendig:
            zeilen.append(
                f"  ? {k.ref:<40} alte String-Form — Org unbekannt, nicht rotierbar"
            )
        elif not k.proof:
            zeilen.append(f"  – {k.ref:<40} {k.kind}, ohne Beleg — wird NICHT gesetzt")
        else:
            art = "workflow" if "workflow" in k.proof else "command"
            zeilen.append(f"  ✓ {k.ref:<40} {k.kind}, Beleg per {art}")
    return zeilen


def naechste_frist(secret: Secret, letzter: dict[str, Any] | None) -> str:
    tage = FRIST_TAGE.get(secret.rotation or "")
    if tage is None:
        return f"keine Frist (rotation: {secret.rotation or 'nicht gesetzt'})"
    if not letzter or letzter.get("status") != "abgeschlossen":
        return f"faellig (alle {tage} Tage, kein abgeschlossener Lauf im Log)"
    basis_roh = letzter.get("beendet") or letzter.get("gestartet") or ""
    try:
        basis = datetime.fromisoformat(str(basis_roh).replace("Z", "+00:00")).date()
    except ValueError:
        return f"faellig (alle {tage} Tage, Datum des letzten Laufs unlesbar)"
    return f"{(basis + timedelta(days=tage)).isoformat()} (alle {tage} Tage)"
