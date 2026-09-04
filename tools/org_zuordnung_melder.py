#!/usr/bin/env python3
"""org_zuordnung_melder.py — ADR-297: Org-Zuordnung, Deklaration gegen Realitaet.

ADR-297 (Abschnitt „Durchsetzung", Offener Punkt 4 — platform#2264): der Leitsatz
„die Organisation ist der Standard" wirkt nur, solange ihn jemand anwendet. Die
Org-Konfiguration erzwingt ihn nicht (`members_can_create_repositories: true`,
gemessen 2026-08-24). Eine Regel ohne Melder ist derselbe Fehler eine Ebene hoeher
als der, aus dem ADR-297 ueberhaupt entstanden ist.

Read-only und idempotent — dieses Werkzeug transferiert nichts und aendert nichts.

Drei Checks
-----------
A  registry-intern    `rich.github` nennt einen anderen Owner als der aus
                      `meta.repo_owner` / `meta.owner_prefix_rules` aufgeloeste.
                      Kostet keinen API-Call: zwei Wahrheitsstaende in EINER Datei.
B  Deklaration/real   aufgeloester Owner != tatsaechlicher Owner bei GitHub. Das ist
                      die Fehlerklasse, die ADR-297 ausgeloest hat (die CLAUDE.md-
                      Tabelle sagte `achimdehnert/risk-hub`, real ist Org `iilgmbh`).
C  Leitsatz-Verstoss  ein NACH dem Stichtag angelegtes Repo der Klassen 1-4 (Proxy:
                      `lifecycle: production` oder `deployed: true`) liegt auf einem
                      persoenlichen Konto statt in einer Organisation.

Warum C einen Stichtag braucht
------------------------------
ADR-297 trennt zwei Ebenen: der Leitsatz gilt fuer **Neuzugaenge**, Bestandsrepos
wandern ausdruecklich nicht pauschal. Ohne Stichtag meldete C die gewachsenen
achimdehnert-Repos allesamt als Verstoss — ein Melder, der beim ersten Lauf 50 Zeilen
ausgibt, wird abgeschaltet statt gelesen. Der Stichtag ist das Annahmedatum von
ADR-297; er ist die Grenze zwischen Ebene 1 und Ebene 2, nicht ein Bequemlichkeitsfilter.

Die Redirect-Falle
------------------
`gh api repos/<falscher-owner>/<repo>` antwortet mit **200**, weil GitHub still
umleitet. Der wahre Owner steht in `.owner.login` der **Antwort**, nie im angefragten
Pfad. Wer den Pfad zurueckliest, bekommt seine eigene Behauptung bestaetigt — genau so
entstand die Fehlklassifikation, die ADR-297 dokumentiert. `real_owner()` liest
deshalb ausschliesslich das Antwortfeld; `test_should_detect_drift_behind_redirect`
haelt das fest.

Exit-Codes
----------
0 = kein Fund · 1 = Fund (ROT IST BEFUND, kein Defekt) · 2 = Werkzeugfehler.

Werkzeugfehler ist dabei nicht nur die unlesbare Registry, sondern auch der blinde
Lauf: war **kein einziges** Repo abrufbar, meldet der Melder 2 statt 0. Sonst waere
ausgerechnet der Totalausfall des Zugangs das gruenste Ergebnis, das dieses Werkzeug
kennt.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

import yaml

# Stichtag = Annahmedatum ADR-297. Aendert sich nur, wenn der ADR neu angenommen wird.
STICHTAG_DEFAULT = "2026-08-24"

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = REPO_ROOT / "registry" / "canonical.yaml"


@dataclass(frozen=True)
class Finding:
    check: str  # "A" | "B" | "C"
    repo: str
    erwartet: str
    gefunden: str
    hinweis: str

    def zeile(self) -> str:
        return f"[{self.check}] {self.repo}: erwartet {self.erwartet}, gefunden {self.gefunden} — {self.hinweis}"


@dataclass
class Registry:
    repos: dict
    repo_owner: dict = field(default_factory=dict)
    prefix_rules: list = field(default_factory=list)
    default_owner: str = "achimdehnert"
    bekannte_konten: list = field(default_factory=list)

    @classmethod
    def laden(cls, pfad: Path) -> "Registry":
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
        meta = daten.get("meta", {})
        return cls(
            repos=daten.get("repos", {}) or {},
            repo_owner=meta.get("repo_owner", {}) or {},
            prefix_rules=meta.get("owner_prefix_rules", []) or [],
            default_owner=(meta.get("server", {}) or {}).get(
                "github_org", "achimdehnert"
            ),
            bekannte_konten=meta.get("enterprise_owners", []) or [],
        )

    def deklarierter_owner(self, repo: str) -> str:
        """Aufloesung in der Reihenfolge, die die Registry selbst vorgibt.

        Explizites Override schlaegt Praefix-Regel schlaegt Default. Die Reihenfolge
        ist nicht beliebig: die Overrides in canonical.yaml existieren gerade fuer die
        Faelle, in denen der Name KEINE Praefix-Regel trifft (`frist-hub` unter
        meiki-lra, `iil-voice-agent` unter iilgmbh) — waere der Default zuerst, waeren
        genau diese Eintraege wirkungslos.
        """
        if repo in self.repo_owner:
            return self.repo_owner[repo]
        for regel in self.prefix_rules:
            if repo.startswith(regel.get("prefix", "\0")):
                return regel["owner"]
        return self.default_owner


def owner_aus_rich(eintrag: dict) -> str | None:
    """Owner aus dem `rich.github`-Feld (`owner/name`), falls vorhanden."""
    github = ((eintrag or {}).get("rich") or {}).get("github")
    if isinstance(github, str) and "/" in github:
        return github.split("/", 1)[0]
    return None


def ist_klasse_1_bis_4(eintrag: dict) -> bool:
    """Proxy fuer die ADR-297-Klassen 1-4 (alles ausser Experiment/Sandbox).

    Bewusst konservativ: gemeldet wird nur, was die Registry selbst als produktiv
    fuehrt. Ein Repo mit Kundenbezug ohne Deploy (Klasse 4) erkennt kein Feld — das
    bleibt Handarbeit und steht als Grenze im ADR.
    """
    rich = (eintrag or {}).get("rich") or {}
    return bool(rich.get("deployed")) or rich.get("lifecycle") == "production"


# --- GitHub-Zugriff (injizierbar, damit die Tests ohne Netz laufen) ------------


def _gh_json(pfad: str) -> dict | None:
    ergebnis = subprocess.run(
        ["gh", "api", pfad], capture_output=True, text=True, timeout=30
    )
    if ergebnis.returncode != 0:
        return None
    try:
        return json.loads(ergebnis.stdout)
    except json.JSONDecodeError:
        return None


def repo_abrufen(owner: str, name: str) -> dict | None:
    """Repo-Metadaten. Der angefragte Owner ist eine Vermutung, keine Aussage."""
    return _gh_json(f"repos/{owner}/{name}")


def konto_typ(login: str) -> str | None:
    daten = _gh_json(f"users/{login}")
    return (daten or {}).get("type")


def real_owner(antwort: dict | None) -> str | None:
    """Der wahre Owner steht in der ANTWORT, nie im angefragten Pfad (Redirect)."""
    if not antwort:
        return None
    return ((antwort.get("owner") or {}).get("login")) or None


# --- Checks -------------------------------------------------------------------


def check_a(reg: Registry) -> list[Finding]:
    funde = []
    for repo, eintrag in sorted(reg.repos.items()):
        aus_rich = owner_aus_rich(eintrag)
        if aus_rich is None:
            continue
        aufgeloest = reg.deklarierter_owner(repo)
        if aus_rich != aufgeloest:
            funde.append(
                Finding(
                    "A",
                    repo,
                    aufgeloest,
                    aus_rich,
                    "registry-intern uneins: rich.github gegen repo_owner/prefix-Regel",
                )
            )
    return funde


def antwort_holen(
    reg: Registry,
    fetch: Callable[[str, str], dict | None],
    repo: str,
) -> dict | None:
    """Repo-Metadaten holen — erst beim deklarierten Owner, dann bei den uebrigen.

    Die Deklaration kann selbst der Fehler sein. Dann fuehrt der angefragte Pfad ins
    Leere, und der Fund versteckt sich als "nicht pruefbar" — der Melder wuerde
    ausgerechnet die schwerste Drift verschweigen. Realfall bahn-hub (2026-08-24):
    die Regel `bahn-` -> bahn-sqf schickte die Anfrage nach bahn-sqf/bahn-hub (404),
    waehrend das Repo unter achimdehnert liegt.

    Gemeinsam fuer B und C, nicht zweimal geschrieben: der Fallback entstand zuerst
    nur in `check_b`. `check_c` uebersprang dadurch stillschweigend genau die Repos,
    deren Deklaration falsch ist — also die, fuer die er gebaut wurde (platform#2264).
    """
    erwartet = reg.deklarierter_owner(repo)
    antwort = fetch(erwartet, repo)
    if antwort is not None:
        return antwort
    for kandidat in reg.bekannte_konten:
        if kandidat == erwartet:
            continue
        antwort = fetch(kandidat, repo)
        if antwort is not None:
            return antwort
    return None


def mit_zwischenspeicher(
    fetch: Callable[[str, str], dict | None],
) -> Callable[[str, str], dict | None]:
    """Jede (owner, repo)-Anfrage hoechstens einmal — B und C fragen dieselben Repos."""
    cache: dict[tuple[str, str], dict | None] = {}

    def geholt(owner: str, name: str) -> dict | None:
        schluessel = (owner, name)
        if schluessel not in cache:
            cache[schluessel] = fetch(owner, name)
        return cache[schluessel]

    return geholt


def check_b(
    reg: Registry,
    fetch: Callable[[str, str], dict | None],
    nur: Iterable[str] | None = None,
) -> tuple[list[Finding], list[str]]:
    funde, unerreichbar = [], []
    namen = sorted(nur) if nur is not None else sorted(reg.repos)
    for repo in namen:
        erwartet = reg.deklarierter_owner(repo)
        tatsaechlich = real_owner(antwort_holen(reg, fetch, repo))
        if tatsaechlich is None:
            unerreichbar.append(repo)
            continue
        if tatsaechlich != erwartet:
            funde.append(
                Finding(
                    "B",
                    repo,
                    erwartet,
                    tatsaechlich,
                    "Registry behauptet einen Owner, den GitHub nicht bestaetigt",
                )
            )
    return funde, unerreichbar


def check_c(
    reg: Registry,
    fetch: Callable[[str, str], dict | None],
    typ: Callable[[str], str | None],
    stichtag: str,
    nur: Iterable[str] | None = None,
) -> tuple[list[Finding], list[str]]:
    """Leitsatz-Verstoesse — Rueckgabe: (Funde, nicht pruefbar).

    Die zweite Liste ist kein Beiwerk. Ein produktives Repo, das der Melder nicht
    abrufen kann, ist **ungeprueft**, nicht regelkonform; frueher fiel es hier ohne
    jede Zaehlung heraus und der einzige Zweck dieses Checks verschwand lautlos.
    """
    funde: list[Finding] = []
    unerreichbar: list[str] = []
    typ_cache: dict[str, str | None] = {}
    namen = sorted(nur) if nur is not None else sorted(reg.repos)
    for repo in namen:
        eintrag = reg.repos.get(repo) or {}
        if not ist_klasse_1_bis_4(eintrag):
            continue
        antwort = antwort_holen(reg, fetch, repo)
        besitzer = real_owner(antwort)
        if besitzer is None:
            unerreichbar.append(repo)
            continue
        angelegt = (antwort.get("created_at") or "")[:10]
        if not angelegt:
            # Ohne Anlagedatum ist die Grenze Ebene 1 / Ebene 2 nicht entscheidbar.
            # Dasselbe stille `continue` wie oben, nur eine Zeile spaeter.
            unerreichbar.append(repo)
            continue
        if angelegt < stichtag:
            continue  # Bestand — Ebene 2, wandert nur mit Anlass
        if besitzer not in typ_cache:
            typ_cache[besitzer] = typ(besitzer)
        if typ_cache[besitzer] == "User":
            funde.append(
                Finding(
                    "C",
                    repo,
                    "Organisation",
                    f"{besitzer} (User)",
                    f"nach dem Stichtag {stichtag} angelegt, produktiv, aber auf einem persoenlichen Konto",
                )
            )
    return funde, unerreichbar


# --- CLI ----------------------------------------------------------------------


def bericht(
    funde: list[Finding],
    unerreichbar: list[str],
    stichtag: str,
    blind: bool = False,
) -> str:
    zeilen = [f"ADR-297 Org-Zuordnungs-Melder — Stichtag Leitsatz: {stichtag}", ""]
    if blind:
        zeilen.append("Werkzeugfehler: kein einziges Repo war abrufbar.")
        zeilen.append(
            "  Dieser Lauf misst nichts. Ein Schweigen aus dem eigenen Messgeraet "
            "ist keine Entwarnung."
        )
        zeilen.append("")
    if not funde and not blind:
        zeilen.append("Kein Fund: Deklaration und Realitaet stimmen ueberein.")
    elif funde:
        for check, titel in (
            ("A", "Registry-intern uneins"),
            ("B", "Deklaration weicht von GitHub ab"),
            ("C", "Leitsatz-Verstoss (Neuzugang auf persoenlichem Konto)"),
        ):
            teil = [f for f in funde if f.check == check]
            if teil:
                zeilen.append(f"{titel} ({len(teil)}):")
                zeilen += [f"  {f.zeile()}" for f in teil]
                zeilen.append("")
    if unerreichbar:
        zeilen.append(
            f"Nicht pruefbar ({len(unerreichbar)}): {', '.join(unerreichbar)}"
        )
        zeilen.append(
            "  Das ist KEINE Entwarnung — ein Repo, das der Token nicht sieht, "
            "ist ungeprueft, nicht in Ordnung."
        )
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--registry", type=Path, default=CANONICAL)
    p.add_argument(
        "--stichtag",
        default=STICHTAG_DEFAULT,
        help="Annahmedatum ADR-297; Check C gilt nur fuer spaeter angelegte Repos",
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="nur Check A (registry-intern), kein GitHub-Zugriff",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        reg = Registry.laden(args.registry)
    except (OSError, yaml.YAMLError) as fehler:
        print(f"Registry nicht lesbar: {fehler}", file=sys.stderr)
        return 2

    funde = check_a(reg)
    unerreichbar: list[str] = []
    blind = False
    if not args.offline:
        geholt = mit_zwischenspeicher(repo_abrufen)
        b, unerreichbar_b = check_b(reg, geholt)
        c, unerreichbar_c = check_c(reg, geholt, konto_typ, args.stichtag)
        funde += b + c
        unerreichbar = sorted(set(unerreichbar_b) | set(unerreichbar_c))
        # check_b fragt JEDES Repo. Ist keines abrufbar, hat nicht die Flotte
        # bestanden — dann fehlt der Zugang (gh nicht angemeldet, Token ohne
        # Sichtbarkeit, kein Netz). Ohne diesen Zweig endet genau dieser Fall
        # mit Exit 0 und der Zeile "Kein Fund": ein gruener Bericht aus einem
        # blinden Werkzeug.
        blind = bool(reg.repos) and len(unerreichbar_b) == len(reg.repos)

    if args.json:
        print(
            json.dumps(
                {
                    "stichtag": args.stichtag,
                    "funde": [f.__dict__ for f in funde],
                    "nicht_pruefbar": unerreichbar,
                    "blind": blind,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(bericht(funde, unerreichbar, args.stichtag, blind))
    if blind:
        return 2
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
