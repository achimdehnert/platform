#!/usr/bin/env python3
"""Auswahl der PRs, die der Review-Bot freigeben darf.

Bis 2026-09-02 stand diese Logik als Heredoc in `.github/workflows/bot-review.yml`
und war damit **nicht testbar** — ein Fehler darin fiel erst auf, wenn ein PR
unerklaerlich ohne Freigabe liegenblieb. Genau das passierte in #2674 (siehe
`juengste_je_name`). Der Job checkt das Repo jetzt aus und ruft dieses Modul auf;
die Regeln selbst sind unveraendert uebernommen.

Aufruf im Workflow:

    python3 tools/bot_review_kandidaten.py /tmp/prs.json /tmp/kandidaten

Eingabe ist die Ausgabe von `gh pr list --json number,isDraft,author,
mergeStateStatus,reviewDecision,reviews,files,statusCheckRollup,url`.
Ausgabe ist eine Zeile je Kandidat, plus ein Protokoll auf stdout: **jeder
uebersprungene PR nennt seinen Grund** — ein stummer Skip ist dieselbe Klasse wie
ein stummer Melder (Lehre aus dem Erstlauf 32869088343).
"""

from __future__ import annotations

import json
import os
import sys

#: Pfade, bei denen der Bot ausdruecklich nicht urteilt — sie bleiben Menschen
#: vorbehalten. `bot-review.yml` steht selbst darin: der Bot gibt seine eigene
#: Regel nicht frei.
TABU = (
    "policies/",
    "docs/adr/",
    ".github/CODEOWNERS",
    ".github/workflows/bot-review.yml",
    "tools/bot_review_kandidaten.py",
)

#: Ergebnisse, die als "gruen" durchgehen. NEUTRAL zaehlt dazu, SKIPPED auch.
GRUEN = ("SUCCESS", "SKIPPED", "NEUTRAL")

#: Merge-Zustaende, in denen ein Approve ueberhaupt etwas bewirkt. UNKNOWN ist
#: kein Zustand, sondern "noch nicht berechnet": GitHub liefert ihn dem Bot-Token
#: beim ersten Aufruf fuer JEDEN PR (Lauf 32871455115: acht PRs, alle UNKNOWN,
#: waehrend der Owner-Token BLOCKED sah).
REVIEW_BLOCKIERT = ("BLOCKED", "BEHIND", "UNKNOWN")


def juengste_je_name(checks: list[dict]) -> list[dict]:
    """Je Check-Name nur den juengsten Lauf zurueckgeben.

    **Warum das noetig ist (Realfall #2674, 2026-09-02):** Ein Gate-Workflow mit
    `concurrency: cancel-in-progress` und `types: [..., edited]` erzeugt zwei
    Laeufe, wenn kurz nacheinander gepusht und der PR-Text bearbeitet wird. Der
    erste wird abgebrochen, der zweite ist gruen — und **beide** stehen im
    `statusCheckRollup`. Die alte Fassung bewertete alle Eintraege und sah damit
    dauerhaft "nicht komplett gruen".

    Verschaerfend: `gh run rerun` auf den abgebrochenen Lauf spielt die
    URSPRUENGLICHE Ereignis-Nutzlast ab, bewertet also den PR-Text von vor der
    Korrektur. Aus `CANCELLED` wird dann `FAILURE`, und dieser Eintrag klebt am
    Commit. Der PR war so nur noch ueber einen neuen Commit freizubekommen.

    **Nicht** unterdrueckt wird der Fall, dass der juengste Lauf selbst rot oder
    abgebrochen ist — dann bleibt der PR zu Recht liegen. Ignoriert wird
    ausschliesslich ein ueberholter Zwilling.
    """
    neuste: dict[str, tuple[str, dict]] = {}
    for c in checks:
        name = c.get("name") or c.get("context") or "?"
        stempel = c.get("completedAt") or c.get("startedAt") or ""
        if name not in neuste or stempel >= neuste[name][0]:
            neuste[name] = (stempel, c)
    return [eintrag for _, eintrag in neuste.values()]


def nicht_gruene_checks(checks: list[dict]) -> list[str]:
    """Namen der Checks, die nach der Zwillings-Bereinigung nicht gruen sind."""
    return [
        c.get("name") or c.get("context") or "?"
        for c in juengste_je_name(checks)
        if c.get("conclusion") not in GRUEN
    ]


def waehle_kandidaten(
    prs: list[dict], bot_login: str, owner_login: str
) -> tuple[list[int], list[str]]:
    """(Kandidaten, Protokollzeilen) — reine Funktion, keine Seiteneffekte."""
    kandidaten: list[int] = []
    protokoll: list[str] = []

    def skip(nr: int, grund: str) -> None:
        protokoll.append(f"#{nr}: {grund}")

    for p in prs:
        nr = p["number"]
        if p.get("isDraft"):
            skip(nr, "Draft — kein Approve")
            continue
        if (p.get("author") or {}).get("login") != owner_login:
            skip(nr, f"Autor {(p.get('author') or {}).get('login')} — nur Owner-PRs")
            continue
        if p.get("reviewDecision") == "APPROVED":
            skip(nr, "bereits approved")
            continue
        # Wiederholungs-Sperre (#2612 bekam am 2026-09-02 elf Approves): fuer das
        # Bot-Token bleibt `reviewDecision` leer, solange ein CODEOWNERS-Review
        # aussteht, das der Bot nicht geben darf. Massgeblich ist die eigene
        # Review-Liste, nicht das aggregierte Urteil.
        eigene = [
            r
            for r in (p.get("reviews") or [])
            if (r.get("author") or {}).get("login") == bot_login
            and r.get("state") == "APPROVED"
        ]
        if eigene:
            skip(nr, f"bereits von {bot_login} approved ({len(eigene)}x) — kein weiteres")
            continue
        if p.get("mergeStateStatus") not in REVIEW_BLOCKIERT:
            skip(nr, f"mergeState {p.get('mergeStateStatus')} — nicht review-blockiert")
            continue
        pfade = [f["path"] for f in (p.get("files") or [])]
        if any(pf.startswith(t) or pf == t for pf in pfade for t in TABU):
            skip(nr, "Tabu-Pfad — bleibt Mensch")
            continue
        checks = p.get("statusCheckRollup") or []
        if not checks:
            skip(nr, "keine Checks — kein Approve")
            continue
        offen = nicht_gruene_checks(checks)
        if offen:
            skip(nr, f"Checks nicht komplett gruen ({offen[:3]}) — kein Approve")
            continue
        kandidaten.append(nr)
    return kandidaten, protokoll


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Aufruf: {argv[0]} <prs.json> <kandidaten-datei>", file=sys.stderr)
        return 64
    prs = json.load(open(argv[1]))
    bot_login = os.environ["BOT_LOGIN"]
    owner_login = os.environ.get("OWNER_LOGIN", "achimdehnert")
    print(f"{len(prs)} offene PRs: {[p['number'] for p in prs]}")
    kandidaten, protokoll = waehle_kandidaten(prs, bot_login, owner_login)
    for zeile in protokoll:
        print(zeile)
    print(f"Kandidaten: {kandidaten}")
    # Zeilenende PFLICHT: `while read` gibt bei EOF ohne Trenner 1 zurueck — die
    # Schleife laeuft dann NICHT. Bei genau einem Kandidaten fiel der dadurch
    # lautlos aus (#2442, #2441 am 2026-08-29).
    with open(argv[2], "w") as fh:
        fh.write("".join(f"{n}\n" for n in kandidaten))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
