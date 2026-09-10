#!/usr/bin/env python3
"""Sitzungs-Abgleich: was gemergt wurde und welche Baeume danach noch stehen.

Dieses eine Modul traegt DREI registrierte Slugs. `tools/gate_drill_check.py`
liest den maschinenlesbaren Kopf (GATE_HEADER) und findet dort den ERSTEN;
`docs/governance/gate-registry.json` nennt das Modul dreimal — einmal je Slug.
Zuordnung Slug → Funktion (die Registry-Zeilen zeigen auf dieselbe Datei):

  1. `issue-offen-nach-gemergtem-fix`   → befunde_issues()
  2. `beleg-pr-nicht-gemergt`           → befunde_belege()
  3. `serielle-prs-auf-derselben-datei` → befunde_serien()

WARUM ES DAS GIBT (belegte Realfaelle, nicht ausgedacht)
--------------------------------------------------------
(1) Befund-Slug `issue-not-reconciled-after-cross-repo-fix` 8x, deckt mit
    `issue-open-after-its-fix-merged` 3x und `dod-reinterpreted-only-in-pr-body`
    2x. chat-hub #27 blieb OPEN, obwohl "alle fuenf Punkte erledigt" darunter
    kommentiert stand; ausschreibungs-hub #184 war inhaltlich durch #195
    erfuellt und blieb offen; in writing-hub schrieben 9 von 10 PR-Texten
    `Refs #N` statt `Closes #N` — fuenf geloeste Issues blieben OPEN. Die
    zweite Haelfte desselben Musters ist die DoD-Umdeutung: das Issue wird
    geschlossen, aber sein Body traegt weiter unangehakte Kaestchen; die
    "erledigt"-Begruendung steht nur im PR-Text.
(2) Befund-Slug `proof-artifact-left-unmerged` 3x: ein PR-/Issue-Text nennt
    einen anderen PR als Beleg ("Nachweis: #123"), und genau dieser Beleg-PR
    ist nie gemergt worden. Der Beleg zeigt dann auf nichts; CLOSED-ohne-Merge
    ist der schlimmere Fall, weil der Beleg aktiv verworfen wurde.
(3) Befund-Slug `same-file-serial-prs` 9x: dieselbe Datei in kurzer Folge
    mehrfach angefasst — ein Zeichen dafuer, dass der erste PR die Sache nicht
    zu Ende gebracht hat.

WAS ES NICHT SIEHT
------------------
- Issues, die in keinem PR-Text referenziert sind (kein Text = kein Signal).
- Erledigung, die ausserhalb von GitHub belegt ist (Outline, Mail, Chat).
- Ob eine Referenz auf einen PR oder ein Issue zeigt: GitHub teilt sich den
  Nummernraum. Ist ein Beleg-Ref nicht als PR aufloesbar, wird das als HINWEIS
  ausgewiesen — nicht als Entwarnung und nicht als Befund.
- Semantik: ob PR #195 das Issue #184 inhaltlich wirklich erfuellt, entscheidet
  dieses Modul nicht. Es meldet die offene Buchung, nicht die Wahrheit.

WARUM DIE FALSIFIKATION BEI (3) PFLICHT IST
-------------------------------------------
Zwei PRs auf derselben Datei sind der Normalfall einer aktiven Datei, nicht per
se ein Befund. Ohne Gegenprobe wirft dieses Gate an einem normalen Arbeitstag
eine Fehlalarm-Flut — und ein Gate, das taub gelesen wird, ist schlechter als
keines (repo-health-Disziplin: 0-FP-Baseline zuerst). Die Gegenprobe ist der
beruehrte ZEILENBEREICH: sind die Hunks disjunkt, haben die beiden PRs nicht
dieselbe Stelle zweimal angefasst → kein Befund. Steht die Hunk-Information
nicht zur Verfuegung (kein Patch abrufbar), ist der Fall NICHT falsifizierbar
und wird ausdruecklich als HINWEIS gefuehrt, nie als Befund und nie als sauber.
Ausserdem sind gate-erzwungene Serien legitim (der zweite PR korrigiert, was
ein Gate am ersten beanstandet hat) — deshalb ist dieses Gate advisory.

`--pr N` (Retro 2026-09-10): der Sitzungs-Lauf oben kommt erst NACH allen
Merges — #3034 und #3042 gingen nacheinander auf `test_todo_board.py`
(ueberlappende Hunks), ohne dass das Gate vorher lief. `--pr` prueft
`befunde_serien_fuer_pr()` GENAU EINEN PR gegen offene + heute gemergte PRs
desselben Autors und laeuft als Advisory-Kommentar beim PR selbst (Workflow
`.github/workflows/serielle-prs-advisory.yml`), nicht erst am Sitzungsende.

BAUFORM
-------
Jede Kernlogik ist eine REINE Funktion ueber einfachen Python-Datenstrukturen
(Listen von dicts in der Form, die `gh ... --json` liefert). Kein Netzzugriff in
den Kernfunktionen; der `gh`-Abruf lebt in der duennen Schicht unter
"gh-Schicht". Nur so ist das drillbar — und mit `--eingabe <datei>` ist der
ganze Weg auch ohne Netz nachvollziehbar.

Exit: 0 = sauber (auch: nur HINWEISe, dann sagt die RESULT-Zeile HINWEIS)
    · 1 = Befund (advisory) · 2 = Werkzeugfehler (gh fehlt / Abruf gescheitert)
      — ein Melder, der beim Ausfall schweigt, ist schlimmer als keiner.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gegen
# docs/governance/gate-registry.json abgeglichen. Der Kopf traegt den ERSTEN
# der drei Slugs; die beiden anderen stehen im Docstring oben.
GATE_HEADER = {
    "slug": "issue-offen-nach-gemergtem-fix",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-09-07",
    "evidence": "tools/tests/test_session_abgleich.py",
}

SLUG_ISSUES = "issue-offen-nach-gemergtem-fix"
SLUG_BELEGE = "beleg-pr-nicht-gemergt"
SLUG_SERIEN = "serielle-prs-auf-derselben-datei"

# Schluesselwoerter, die eine Referenz einleiten. Die ersten drei schliessen das
# Issue automatisch, die letzten drei NICHT — genau darin lag der writing-hub-
# Fall (9 von 10 PR-Texten schrieben `Refs` statt `Closes`).
SCHLUESSEL_SCHLIESSEND = ("closes", "fixes", "resolves")
SCHLUESSEL_LOSE = ("refs", "bezug", "siehe")
ALLE_SCHLUESSEL = SCHLUESSEL_SCHLIESSEND + SCHLUESSEL_LOSE

_SCHLUESSEL_RE = re.compile(
    r"\b(" + "|".join(ALLE_SCHLUESSEL) + r")\b\s*:?\s*", re.IGNORECASE
)
# Kette hinter einem Schluesselwort: `Closes #1, owner/repo#2 und #3`.
_KETTE_RE = re.compile(
    r"\s*(?:(?:und|and)\s+|,\s*)?(?:(?P<repo>[A-Za-z0-9._-]+/[A-Za-z0-9._-]+))?"
    r"#(?P<nummer>\d+)"
)
# Freie Referenz in einer Beleg-Zeile (ohne Schluesselwort-Zwang).
_FREIE_REF_RE = re.compile(
    r"(?:(?P<repo>[A-Za-z0-9._-]+/[A-Za-z0-9._-]+))?#(?P<nummer>\d+)"
)
# Unangehaktes Kaestchen im Issue-Body (Markdown-Task-Liste).
_OFFENES_KAESTCHEN_RE = re.compile(r"^\s*[-*+]\s+\[ \]\s+", re.MULTILINE)
# Unified-Diff-Kopfzeilen.
_DATEI_RE = re.compile(r"^\+\+\+ b/(.+)$")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

# Woerter, die eine Zeile zur BELEG-Zeile machen (klein geschrieben verglichen).
BELEG_WOERTER = (
    "beleg",  # deckt Beleg/belegt/Belegt
    "nachweis",
    "verifiziert",
    "positivkontrolle",
    "drill",
    "siehe pr",
)

# Deckel fuer Detail-Abrufe in der gh-Schicht (ein Gate darf eine Sitzung nicht
# aufhalten). Was darueber liegt, wird als HINWEIS ausgewiesen, nicht verschwiegen.
MAX_DETAIL_ABRUFE = 30


# ─────────────────────────── Hilfen (rein) ──────────────────────────────────


def _befund(slug: str, ref: str, text: str) -> dict:
    return {"slug": slug, "art": "befund", "ref": ref, "text": text}


def _hinweis(slug: str, ref: str, text: str) -> dict:
    return {"slug": slug, "art": "hinweis", "ref": ref, "text": text}


def _sauber(slug: str, ref: str, text: str) -> dict:
    """Informations-Zeile fuer eine gepruefte, aber falsifizierte Stelle.

    Kein Befund und kein Hinweis: die Falsifikation LIEF und war erfolgreich
    (Hunks disjunkt) — das gehoert in die Zusammenfassung, sonst wirkt ein
    sauberer --pr-Lauf ununterscheidbar von einem, der nichts geprueft hat.
    """
    return {"slug": slug, "art": "sauber", "ref": ref, "text": text}


def _autor_von(pr: dict) -> str:
    """Login aus `pr["author"]` (dict `{"login": ...}` oder bereits String)."""
    autor = pr.get("author")
    if isinstance(autor, dict):
        autor = autor.get("login") or ""
    return str(autor or "")


def _repo_von(eintrag: dict) -> str:
    """Repo-Etikett eines PR-/Issue-dicts; leer, wenn keins mitgeliefert wurde."""
    return str(eintrag.get("repo") or "")


def _ref_text(repo: str, nummer: int) -> str:
    return f"{repo}#{nummer}" if repo else f"#{nummer}"


def ist_gemergt(pr: dict) -> bool:
    """MERGED gilt als gemergt — `state` ODER ein gesetztes `mergedAt`.

    `gh pr list --json state` liefert MERGED; `gh pr view` fuellt zusaetzlich
    `mergedAt`. Beide Spuren zaehlen, damit die Kernlogik nicht an der Form der
    Abfrage haengt.
    """
    if str(pr.get("state") or "").upper() == "MERGED":
        return True
    return bool(pr.get("mergedAt"))


def referenzierte_issues(body: str) -> list[dict]:
    """Alle `<Schluesselwort> #<n>`-Referenzen eines Textes (rein, regex-only).

    Liefert je Treffer `{"schluessel": "closes", "repo": "" | "owner/repo",
    "nummer": 27, "schliessend": bool}`. Ketten (`Closes #1, #2`) werden
    aufgeloest; Duplikate bleiben erhalten (der Aufrufer entscheidet).
    """
    treffer: list[dict] = []
    if not body:
        return treffer
    for m in _SCHLUESSEL_RE.finditer(body):
        schluessel = m.group(1).lower()
        pos = m.end()
        while True:
            k = _KETTE_RE.match(body, pos)
            if not k:
                break
            treffer.append(
                {
                    "schluessel": schluessel,
                    "repo": k.group("repo") or "",
                    "nummer": int(k.group("nummer")),
                    "schliessend": schluessel in SCHLUESSEL_SCHLIESSEND,
                }
            )
            pos = k.end()
    return treffer


def hat_offene_kaestchen(body: str) -> bool:
    """`- [ ]` irgendwo im Body — die DoD-Haelfte des Musters."""
    return bool(body) and bool(_OFFENES_KAESTCHEN_RE.search(body))


def beleg_referenzen(body: str, eigene_nummer: int | None = None) -> list[dict]:
    """PR-Nummern, die in einer BELEG-Zeile genannt werden (rein).

    Eine Zeile zaehlt, wenn sie eines der BELEG_WOERTER traegt. Die eigene
    Nummer wird uebersprungen — ein PR, der sich selbst nennt, ist kein Beleg
    auf ein fremdes Artefakt.
    """
    treffer: list[dict] = []
    if not body:
        return treffer
    for zeile in body.splitlines():
        klein = zeile.lower()
        if not any(w in klein for w in BELEG_WOERTER):
            continue
        for m in _FREIE_REF_RE.finditer(zeile):
            nummer = int(m.group("nummer"))
            repo = m.group("repo") or ""
            if eigene_nummer is not None and not repo and nummer == eigene_nummer:
                continue
            treffer.append({"repo": repo, "nummer": nummer, "zeile": zeile.strip()})
    return treffer


def hunks_aus_patch(patch: str) -> dict[str, list[tuple[int, int]]]:
    """Unified-Diff → {Pfad: [(erste_zeile, letzte_zeile), ...]} der NEUEN Seite.

    Rein und netzfrei: die gh-Schicht liefert den Patch-Text, geparst wird hier.
    Ein Hunk mit Laenge 0 (reine Loeschung) wird als Punktbereich gefuehrt.
    """
    ergebnis: dict[str, list[tuple[int, int]]] = {}
    pfad = ""
    for zeile in (patch or "").splitlines():
        md = _DATEI_RE.match(zeile)
        if md:
            pfad = md.group(1).strip()
            ergebnis.setdefault(pfad, [])
            continue
        mh = _HUNK_RE.match(zeile)
        if mh and pfad:
            start = int(mh.group(1))
            laenge = int(mh.group(2)) if mh.group(2) is not None else 1
            ende = start + laenge - 1 if laenge > 0 else start
            ergebnis[pfad].append((start, ende))
    return ergebnis


def _zeitpunkt(wert) -> datetime | None:
    """ISO-8601 (auch mit `Z`) → aware datetime; None, wenn unlesbar."""
    if not wert:
        return None
    text = str(wert).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def bereiche_ueberlappen(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> bool:
    """Schneidet sich mindestens ein Zeilenbereich aus a mit einem aus b?"""
    for a1, a2 in a:
        for b1, b2 in b:
            if a1 <= b2 and b1 <= a2:
                return True
    return False


# ───────────────────── (1) issue-offen-nach-gemergtem-fix ───────────────────


def befunde_issues(prs: list[dict], issues: list[dict]) -> list[dict]:
    """Gemergte PRs gegen den Zustand der von ihnen referenzierten Issues.

    Rein: `prs` ist die Liste, die `gh pr list --json number,body,state,repo`
    liefert; `issues` die Liste aus `gh issue view --json number,state,body`
    (plus optional `repo`).

    Befund A: ein referenziertes Issue ist noch OPEN, obwohl seine PR gemergt
              ist (chat-hub #27, ausschreibungs-hub #184, writing-hub `Refs`).
    Befund B: ein durch die PR geschlossenes Issue traegt im Body noch
              unangehakte Kaestchen `- [ ]` (DoD nur im PR-Text umgedeutet).
    Unbekannter Issue-Zustand → HINWEIS, nie Entwarnung.
    """
    genau: dict[tuple[str, int], dict] = {}
    nach_nummer: dict[int, list[dict]] = {}
    for iss in issues or []:
        nummer = int(iss.get("number"))
        genau[(_repo_von(iss), nummer)] = iss
        nach_nummer.setdefault(nummer, []).append(iss)

    ergebnisse: list[dict] = []
    gesehen: set[tuple[str, int, str]] = set()
    for pr in prs or []:
        if not ist_gemergt(pr):
            continue
        pr_repo = _repo_von(pr)
        pr_ref = _ref_text(pr_repo, int(pr.get("number")))
        for ref in referenzierte_issues(str(pr.get("body") or "")):
            ziel_repo = ref["repo"] or pr_repo
            nummer = ref["nummer"]
            issue = genau.get((ziel_repo, nummer)) or genau.get(("", nummer))
            if issue is None:
                kandidaten = nach_nummer.get(nummer, [])
                issue = kandidaten[0] if len(kandidaten) == 1 else None
            ziel_ref = _ref_text(ziel_repo, nummer)
            if issue is None:
                schluessel = ("hinweis", ziel_repo, nummer)
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                ergebnisse.append(
                    _hinweis(
                        SLUG_ISSUES,
                        ziel_ref,
                        f"Zustand nicht abrufbar (referenziert von {pr_ref}) — "
                        "keine Entwarnung, Issue selbst nachsehen",
                    )
                )
                continue
            zustand = str(issue.get("state") or "").upper()
            if zustand == "OPEN":
                schluessel = ("A", ziel_repo, nummer)
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                wort = ref["schluessel"]
                zusatz = (
                    f"`{wort}` schliesst nicht automatisch"
                    if not ref["schliessend"]
                    else f"`{wort}` griff nicht (cross-repo oder manuell wieder geoeffnet)"
                )
                ergebnisse.append(
                    _befund(
                        SLUG_ISSUES,
                        ziel_ref,
                        f"noch OPEN, obwohl {pr_ref} gemergt ist — {zusatz}",
                    )
                )
            elif zustand == "CLOSED" and hat_offene_kaestchen(
                str(issue.get("body") or "")
            ):
                schluessel = ("B", ziel_repo, nummer)
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                ergebnisse.append(
                    _befund(
                        SLUG_ISSUES,
                        ziel_ref,
                        f"geschlossen durch {pr_ref}, aber der Issue-Body traegt "
                        "noch unangehakte `- [ ]`-Kaestchen — DoD nur im PR-Text "
                        "umgedeutet",
                    )
                )
    return ergebnisse


# ───────────────────────── (2) beleg-pr-nicht-gemergt ───────────────────────


def befunde_belege(texte: list[dict], pr_zustaende: dict) -> list[dict]:
    """Als BELEG genannte PRs, die nicht gemergt sind.

    Rein: `texte` ist eine Liste `{"quelle": "#123", "repo": "owner/repo",
    "nummer": 123, "body": "..."}`; `pr_zustaende` bildet `"#195"` bzw.
    `"owner/repo#195"` auf `"MERGED" | "OPEN" | "CLOSED"` ab.

    CLOSED-ohne-Merge wird eigens benannt: der Beleg wurde aktiv verworfen.
    Unbekannter Zustand → HINWEIS (GitHub teilt sich den Nummernraum zwischen
    PRs und Issues; eine nicht aufloesbare Referenz ist kein Freispruch).
    """
    ergebnisse: list[dict] = []
    gesehen: set[tuple[str, str]] = set()
    for eintrag in texte or []:
        quell_repo = _repo_von(eintrag)
        eigene = eintrag.get("nummer")
        eigene_nummer = int(eigene) if eigene is not None else None
        quelle = str(eintrag.get("quelle") or "")
        if not quelle:
            quelle = (
                _ref_text(quell_repo, eigene_nummer)
                if eigene_nummer is not None
                else "?"
            )
        for ref in beleg_referenzen(str(eintrag.get("body") or ""), eigene_nummer):
            ziel_repo = ref["repo"] or quell_repo
            ziel_ref = _ref_text(ziel_repo, ref["nummer"])
            zustand = pr_zustaende.get(ziel_ref)
            if zustand is None:
                zustand = pr_zustaende.get(f"#{ref['nummer']}")
            schluessel = (quelle, ziel_ref)
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            if zustand is None:
                ergebnisse.append(
                    _hinweis(
                        SLUG_BELEGE,
                        ziel_ref,
                        f"als Beleg in {quelle} genannt, Zustand nicht aufloesbar "
                        "(PR oder Issue?) — keine Entwarnung",
                    )
                )
                continue
            zustand = str(zustand).upper()
            if zustand == "MERGED":
                continue
            if zustand == "CLOSED":
                ergebnisse.append(
                    _befund(
                        SLUG_BELEGE,
                        ziel_ref,
                        f"als Beleg in {quelle} genannt, aber CLOSED OHNE MERGE — "
                        "der schlimmere Fall: der Beleg wurde verworfen",
                    )
                )
            else:
                ergebnisse.append(
                    _befund(
                        SLUG_BELEGE,
                        ziel_ref,
                        f"als Beleg in {quelle} genannt, aber {zustand} statt "
                        "MERGED — der Beleg zeigt auf nichts Wirksames",
                    )
                )
    return ergebnisse


# ──────────────────── (3) serielle-prs-auf-derselben-datei ──────────────────


def befunde_serien(prs: list[dict], stunden: int = 24) -> list[dict]:
    """>= 2 gemergte PRs desselben Autors auf derselben Datei binnen `stunden`.

    Rein: `prs` in der Form von `gh pr list --json
    number,author,mergedAt,files` (+ optional `repo`), wobei jeder `files`-
    Eintrag `{"path": ..., "hunks": [[von, bis], ...]}` tragen KANN.

    FALSIFIKATION ist Pflicht (sonst Fehlalarm-Flut):
      - Hunks auf beiden Seiten bekannt und disjunkt → KEIN Befund.
      - Hunks auf beiden Seiten bekannt und ueberlappend → Befund.
      - Hunks fehlen → NICHT falsifizierbar → HINWEIS, nie Befund.
    Gate-erzwungene Serien (PR 2 korrigiert, was ein Gate an PR 1 beanstandet
    hat) sind legitim — deshalb ist dieses Gate advisory.
    """
    gruppen: dict[tuple[str, str, str], list[dict]] = {}
    for pr in prs or []:
        if not ist_gemergt(pr):
            continue
        autor = _autor_von(pr)
        repo = _repo_von(pr)
        zeit = _zeitpunkt(pr.get("mergedAt"))
        for datei in pr.get("files") or []:
            pfad = str(datei.get("path") or "")
            if not pfad:
                continue
            hunks = datei.get("hunks")
            bereiche = (
                [(int(h[0]), int(h[1])) for h in hunks] if hunks is not None else None
            )
            gruppen.setdefault((repo, autor, pfad), []).append(
                {
                    "nummer": int(pr.get("number")),
                    "ref": _ref_text(repo, int(pr.get("number"))),
                    "zeit": zeit,
                    "bereiche": bereiche,
                }
            )

    fenster = timedelta(hours=stunden)
    ergebnisse: list[dict] = []
    for (repo, autor, pfad), eintraege in sorted(gruppen.items()):
        if len(eintraege) < 2:
            continue
        ueberlappend: list[tuple[dict, dict]] = []
        unklar: list[tuple[dict, dict]] = []
        for i in range(len(eintraege)):
            for j in range(i + 1, len(eintraege)):
                a, b = eintraege[i], eintraege[j]
                if a["nummer"] == b["nummer"]:
                    continue
                if a["zeit"] is None or b["zeit"] is None:
                    unklar.append((a, b))
                    continue
                if abs(a["zeit"] - b["zeit"]) > fenster:
                    continue
                if a["bereiche"] is None or b["bereiche"] is None:
                    unklar.append((a, b))
                elif bereiche_ueberlappen(a["bereiche"], b["bereiche"]):
                    ueberlappend.append((a, b))
        etikett = f"{repo}:{pfad}" if repo else pfad
        if ueberlappend:
            refs = sorted({p["ref"] for paar in ueberlappend for p in paar})
            ergebnisse.append(
                _befund(
                    SLUG_SERIEN,
                    etikett,
                    f"{' + '.join(refs)} (Autor {autor or '?'}) beruehren dieselbe "
                    f"Datei binnen {stunden} h an ueberlappenden Zeilen — "
                    "Falsifikation gescheitert",
                )
            )
        elif unklar:
            refs = sorted({p["ref"] for paar in unklar for p in paar})
            ergebnisse.append(
                _hinweis(
                    SLUG_SERIEN,
                    etikett,
                    f"{' + '.join(refs)} (Autor {autor or '?'}) beruehren dieselbe "
                    "Datei, aber Hunk-/Zeitangabe fehlt — NICHT falsifizierbar, "
                    "daher Hinweis statt Befund",
                )
            )
    return ergebnisse


def befunde_serien_fuer_pr(
    ziel_nummer: int, prs: list[dict], heute: str | None = None
) -> list[dict]:
    """--pr-Modus: EIN PR gegen offene + heute gemergte PRs desselben Autors.

    Retro 2026-09-10: der Sitzungs-Lauf von befunde_serien() kommt erst NACH
    allen Merges — #3034 und #3042 liefen nacheinander auf `test_todo_board.py`
    (Hunks 467-531 vs 526-542, ueberlappend), ohne dass das Gate vorher lief.
    Dieser Modus soll beim PR selbst laufen (Advisory-Kommentar), also VOR dem
    Merge — die Population ist deshalb nicht "gemergt binnen X Stunden",
    sondern "offen ODER heute gemergt" (Autor + Repo wie beim Ziel-PR).

    Rein: `prs` in der Form von `gh pr list --json
    number,author,state,mergedAt,files,repo`, Hunks je Datei optional unter
    `files[].hunks`. `heute` ist ein YYYY-MM-DD-Stichtag (Default: UTC-heute).

    Dieselbe Falsifikationsregel wie befunde_serien():
      - Hunks auf beiden Seiten bekannt und ueberlappend → Befund.
      - Hunks auf beiden Seiten bekannt und disjunkt → "sauber"-Zeile
        ("gleiche Datei, disjunkte Bereiche — kein Befund"), NIE ein Befund.
      - Hunks fehlen → Hinweis, nie Befund und nie Entwarnung.
    Kein zweiter PR desselben Autors/Repos auf einer gemeinsamen Datei →
    leere Liste (kein Ballast im PR-Kommentar).
    """
    heute = heute or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ziel = next(
        (p for p in prs or [] if int(p.get("number") or -1) == ziel_nummer), None
    )
    if ziel is None:
        return []

    ziel_autor = _autor_von(ziel)
    ziel_repo = _repo_von(ziel)
    ziel_ref = _ref_text(ziel_repo, ziel_nummer)

    ziel_dateien: dict[str, list[tuple[int, int]] | None] = {}
    for datei in ziel.get("files") or []:
        pfad = str(datei.get("path") or "")
        if not pfad:
            continue
        hunks = datei.get("hunks")
        ziel_dateien[pfad] = (
            [(int(h[0]), int(h[1])) for h in hunks] if hunks is not None else None
        )

    def ist_population(pr: dict) -> bool:
        if int(pr.get("number") or -1) == ziel_nummer:
            return False
        if _autor_von(pr) != ziel_autor or _repo_von(pr) != ziel_repo:
            return False
        zustand = str(pr.get("state") or "").upper()
        if zustand == "OPEN":
            return True
        if zustand == "MERGED":
            zeit = _zeitpunkt(pr.get("mergedAt"))
            return bool(zeit) and zeit.strftime("%Y-%m-%d") == heute
        return False

    ueberlappend: list[tuple[str, str]] = []
    unklar: list[tuple[str, str]] = []
    disjunkt: list[tuple[str, str]] = []
    for pr in prs or []:
        if not ist_population(pr):
            continue
        ref = _ref_text(_repo_von(pr), int(pr.get("number")))
        for datei in pr.get("files") or []:
            pfad = str(datei.get("path") or "")
            if pfad not in ziel_dateien:
                continue
            ziel_bereich = ziel_dateien[pfad]
            hunks = datei.get("hunks")
            andere_bereich = (
                [(int(h[0]), int(h[1])) for h in hunks] if hunks is not None else None
            )
            if ziel_bereich is None or andere_bereich is None:
                unklar.append((ref, pfad))
            elif bereiche_ueberlappen(ziel_bereich, andere_bereich):
                ueberlappend.append((ref, pfad))
            else:
                disjunkt.append((ref, pfad))

    ergebnisse: list[dict] = []
    for ref, pfad in sorted(set(ueberlappend)):
        ergebnisse.append(
            _befund(
                SLUG_SERIEN,
                pfad,
                f"{ziel_ref} + {ref} (Autor {ziel_autor or '?'}) beruehren "
                f"`{pfad}` an ueberlappenden Zeilen — Falsifikation gescheitert",
            )
        )
    for ref, pfad in sorted(set(unklar)):
        ergebnisse.append(
            _hinweis(
                SLUG_SERIEN,
                pfad,
                f"{ziel_ref} + {ref} beruehren `{pfad}`, aber Hunk-Angabe fehlt "
                "— NICHT falsifizierbar",
            )
        )
    for ref, pfad in sorted(set(disjunkt)):
        ergebnisse.append(
            _sauber(
                SLUG_SERIEN,
                pfad,
                f"{ziel_ref} + {ref} beruehren `{pfad}` — gleiche Datei, "
                "disjunkte Bereiche — kein Befund",
            )
        )
    return ergebnisse


# ─────────────────────────── gh-Schicht (duenn) ─────────────────────────────
# Alles ab hier fasst das Netz an und enthaelt bewusst KEINE Bewertungslogik.


class GhFehler(RuntimeError):
    """gh fehlt oder ein Abruf ist gescheitert — Exit 2, nie 'sauber'."""


def _gh(argumente: list[str], timeout: int = 60) -> str:
    try:
        lauf = subprocess.run(
            ["gh", *argumente], capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise GhFehler("gh nicht verfuegbar") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GhFehler(f"gh-Abruf gescheitert: {exc}") from exc
    if lauf.returncode != 0:
        raise GhFehler(
            f"gh {' '.join(argumente[:3])} rc={lauf.returncode}: "
            f"{lauf.stderr.strip()[:160]}"
        )
    return lauf.stdout


def gh_sitzungs_prs(repo: str, autor: str, seit: str) -> list[dict]:
    """Eigene PRs der Sitzung (alle Zustaende) — EIN Abruf."""
    roh = _gh(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--author",
            autor,
            "--state",
            "all",
            "--search",
            f"updated:>={seit}",
            "--limit",
            "50",
            "--json",
            "number,author,body,state,mergedAt,files",
        ]
    )
    try:
        daten = json.loads(roh or "[]")
    except json.JSONDecodeError as exc:
        raise GhFehler(f"gh pr list lieferte kein JSON: {exc}") from exc
    for pr in daten:
        pr["repo"] = repo
    return daten


def gh_issue(repo: str, nummer: int) -> dict | None:
    """Ein Issue; None, wenn die Nummer kein Issue ist (dann bleibt es HINWEIS)."""
    try:
        roh = _gh(
            [
                "issue",
                "view",
                str(nummer),
                "--repo",
                repo,
                "--json",
                "number,state,body",
            ]
        )
    except GhFehler:
        return None
    try:
        daten = json.loads(roh)
    except json.JSONDecodeError:
        return None
    daten["repo"] = repo
    return daten


def gh_pr_zustand(repo: str, nummer: int) -> str | None:
    """MERGED/OPEN/CLOSED; None, wenn die Nummer kein PR ist."""
    try:
        roh = _gh(["pr", "view", str(nummer), "--repo", repo, "--json", "state"])
    except GhFehler:
        return None
    try:
        return str(json.loads(roh).get("state") or "").upper() or None
    except json.JSONDecodeError:
        return None


def gh_hunks(repo: str, nummer: int) -> dict[str, list[tuple[int, int]]] | None:
    """Hunks eines PRs aus seinem Patch; None = nicht falsifizierbar."""
    try:
        patch = _gh(["pr", "diff", str(nummer), "--repo", repo, "--patch"], timeout=90)
    except GhFehler:
        return None
    return hunks_aus_patch(patch)


def sammle_via_gh(repo: str, autor: str, seit: str, mit_hunks: bool) -> dict:
    """Baut genau die Datenstruktur, die `--eingabe` auch aus einer Datei liest."""
    prs = gh_sitzungs_prs(repo, autor, seit)
    gemergt = [p for p in prs if ist_gemergt(p)]

    issues: list[dict] = []
    gesucht: set[tuple[str, int]] = set()
    for pr in gemergt:
        for ref in referenzierte_issues(str(pr.get("body") or "")):
            ziel = (ref["repo"] or repo, ref["nummer"])
            if ziel in gesucht or len(gesucht) >= MAX_DETAIL_ABRUFE:
                continue
            gesucht.add(ziel)
            iss = gh_issue(ziel[0], ziel[1])
            if iss is not None:
                issues.append(iss)

    texte = [
        {
            "quelle": _ref_text(repo, int(p.get("number"))),
            "repo": repo,
            "nummer": int(p.get("number")),
            "body": p.get("body") or "",
        }
        for p in prs
    ]
    pr_zustaende: dict[str, str] = {}
    for eintrag in texte:
        for ref in beleg_referenzen(eintrag["body"], eintrag["nummer"]):
            ziel_repo = ref["repo"] or repo
            ziel_ref = _ref_text(ziel_repo, ref["nummer"])
            if ziel_ref in pr_zustaende or len(pr_zustaende) >= MAX_DETAIL_ABRUFE:
                continue
            zustand = gh_pr_zustand(ziel_repo, ref["nummer"])
            if zustand:
                pr_zustaende[ziel_ref] = zustand

    if mit_hunks:
        for pr in gemergt[:MAX_DETAIL_ABRUFE]:
            hunks = gh_hunks(repo, int(pr.get("number")))
            if hunks is None:
                continue
            for datei in pr.get("files") or []:
                pfad = str(datei.get("path") or "")
                if pfad in hunks:
                    datei["hunks"] = [list(h) for h in hunks[pfad]]

    return {
        "prs": prs,
        "issues": issues,
        "texte": texte,
        "pr_zustaende": pr_zustaende,
    }


def gh_pr_einzel(repo: str, nummer: int) -> dict | None:
    """Ein einzelner PR — Fallback, falls `gh_sitzungs_prs` ihn nicht erfasst
    (z.B. `--seit` liegt nach seinem letzten `updated`-Zeitpunkt)."""
    try:
        roh = _gh(
            [
                "pr",
                "view",
                str(nummer),
                "--repo",
                repo,
                "--json",
                "number,author,body,state,mergedAt,files",
            ]
        )
    except GhFehler:
        return None
    try:
        daten = json.loads(roh)
    except json.JSONDecodeError:
        return None
    daten["repo"] = repo
    return daten


def sammle_serien_fuer_pr_via_gh(
    repo: str, ziel_nummer: int, autor: str, seit: str
) -> list[dict]:
    """Population fuer den --pr-Modus, mit Hunks fuer alle relevanten PRs.

    Holt die Sitzungs-PRs des Autors (Fallback: Einzelabruf, falls der Ziel-PR
    darin fehlt) und laedt Hunks NUR fuer den Ziel-PR sowie fuer offene bzw.
    heute gemergte PRs desselben Autors (Deckel MAX_DETAIL_ABRUFE) — genau die
    Population, die befunde_serien_fuer_pr() auch bewertet.
    """
    prs = gh_sitzungs_prs(repo, autor, seit)
    if not any(int(p.get("number") or -1) == ziel_nummer for p in prs):
        einzel = gh_pr_einzel(repo, ziel_nummer)
        if einzel is not None:
            prs.append(einzel)

    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    abgerufen = 0
    for pr in prs:
        if abgerufen >= MAX_DETAIL_ABRUFE:
            break
        nummer = int(pr.get("number") or -1)
        zustand = str(pr.get("state") or "").upper()
        if nummer == ziel_nummer:
            relevant = True
        elif zustand == "OPEN":
            relevant = True
        elif zustand == "MERGED":
            zeit = _zeitpunkt(pr.get("mergedAt"))
            relevant = bool(zeit) and zeit.strftime("%Y-%m-%d") == heute
        else:
            relevant = False
        if not relevant:
            continue
        hunks = gh_hunks(repo, nummer)
        abgerufen += 1
        if hunks is None:
            continue
        for datei in pr.get("files") or []:
            pfad = str(datei.get("path") or "")
            if pfad in hunks:
                datei["hunks"] = [list(h) for h in hunks[pfad]]
    return prs


def lade_eingabe(pfad: str) -> dict:
    daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    if not isinstance(daten, dict):
        raise ValueError("Eingabe muss ein JSON-Objekt sein")
    daten.setdefault("prs", [])
    daten.setdefault("issues", [])
    daten.setdefault("texte", [])
    daten.setdefault("pr_zustaende", {})
    return daten


# ──────────────────────────────── CLI ───────────────────────────────────────


def _ausgabe_zeile(eintrag: dict) -> str:
    marke = {"befund": "⚠", "hinweis": "◌", "sauber": "✓"}.get(eintrag["art"], "◌")
    return f"   {marke} [{eintrag['slug']}] {eintrag['ref']}: {eintrag['text']}"


def _lauf_pr_modus(args) -> int:
    """--pr-Modus: kurze, Markdown-taugliche Ausgabe fuer einen PR-Kommentar."""
    if args.eingabe:
        try:
            daten = lade_eingabe(args.eingabe)
        except (OSError, ValueError) as exc:
            print(f"⚠ Eingabe nicht lesbar: {exc}", file=sys.stderr)
            print("RESULT: FEHLER")
            return 2
        prs = daten["prs"]
    else:
        if not args.repo:
            print("⚠ ohne --eingabe wird --repo owner/repo gebraucht.", file=sys.stderr)
            print("RESULT: FEHLER")
            return 2
        try:
            prs = sammle_serien_fuer_pr_via_gh(
                args.repo, args.pr, args.autor, args.seit
            )
        except GhFehler as exc:
            print(
                f"⚠ {exc} — NICHT bewertbar (nie als sauber werten).", file=sys.stderr
            )
            print("RESULT: FEHLER")
            return 2

    ergebnisse = befunde_serien_fuer_pr(args.pr, prs, heute=args.heute)
    befunde = [e for e in ergebnisse if e["art"] == "befund"]
    hinweise = [e for e in ergebnisse if e["art"] == "hinweis"]
    sauber = [e for e in ergebnisse if e["art"] == "sauber"]

    if args.json:
        print(
            json.dumps(
                {
                    "befunde": befunde,
                    "hinweise": hinweise,
                    "sauber": sauber,
                    "result": "BEFUND"
                    if befunde
                    else ("HINWEIS" if hinweise else "OK"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"**Serielle-PRs-Abgleich fuer #{args.pr}** ({SLUG_SERIEN}, advisory)")
        if befunde:
            for e in befunde:
                print(_ausgabe_zeile(e))
        if hinweise:
            for e in hinweise:
                print(_ausgabe_zeile(e))
        if sauber:
            for e in sauber:
                print(_ausgabe_zeile(e))
        if not befunde and not hinweise and not sauber:
            print(
                "   ✅ kein weiterer offener/heute gemergter PR desselben Autors "
                "auf denselben Dateien."
            )

    if befunde:
        print(f"RESULT: BEFUND {len(befunde)} (hinweise={len(hinweise)})")
        return 1
    if hinweise:
        print(f"RESULT: HINWEIS {len(hinweise)}")
        return 0
    print("RESULT: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Sitzungs-Abgleich: offene Issues nach gemergtem Fix, nicht gemergte "
            "Belege, serielle PRs auf derselben Datei (drei advisory Gates)"
        )
    )
    ap.add_argument("--repo", help="owner/repo fuer den gh-Abruf")
    ap.add_argument("--autor", default="@me", help="PR-Autor (Default: @me)")
    ap.add_argument(
        "--seit",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Stichtag YYYY-MM-DD (Default: heute)",
    )
    ap.add_argument(
        "--eingabe",
        help=(
            "JSON-Datei statt gh-Abruf (Schluessel: prs, issues, texte, "
            "pr_zustaende) — macht jeden Lauf ohne Netz nachvollziehbar"
        ),
    )
    ap.add_argument("--issues", action="store_true", help=f"nur {SLUG_ISSUES}")
    ap.add_argument("--belege", action="store_true", help=f"nur {SLUG_BELEGE}")
    ap.add_argument("--serien", action="store_true", help=f"nur {SLUG_SERIEN}")
    ap.add_argument(
        "--stunden",
        type=int,
        default=24,
        help="Zeitfenster fuer serielle PRs in Stunden (Default: 24)",
    )
    ap.add_argument(
        "--ohne-hunks",
        action="store_true",
        help="keine Patches abrufen — die Serien-Pruefung wird dann nicht falsifizierbar",
    )
    ap.add_argument(
        "--pr",
        type=int,
        help=(
            f"Nur DIESEN PR gegen offene + heute gemergte PRs desselben Autors "
            f"vergleichen ({SLUG_SERIEN}, kurze Ausgabe fuer einen PR-Kommentar) "
            "— ersetzt den Drei-Gates-Lauf, ignoriert --issues/--belege/--serien"
        ),
    )
    ap.add_argument(
        "--heute",
        help=(
            "Stichtag YYYY-MM-DD fuer 'heute gemergt' im --pr-Modus "
            "(Default: UTC-heute)"
        ),
    )
    ap.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    args = ap.parse_args(argv)

    if args.pr is not None:
        return _lauf_pr_modus(args)

    keiner_gewaehlt = not (args.issues or args.belege or args.serien)
    will_issues = args.issues or keiner_gewaehlt
    will_belege = args.belege or keiner_gewaehlt
    will_serien = args.serien or keiner_gewaehlt

    if args.eingabe:
        try:
            daten = lade_eingabe(args.eingabe)
        except (OSError, ValueError) as exc:
            print(f"⚠ Eingabe nicht lesbar: {exc}", file=sys.stderr)
            print("RESULT: FEHLER")
            return 2
    else:
        if not args.repo:
            print("⚠ ohne --eingabe wird --repo owner/repo gebraucht.", file=sys.stderr)
            print("RESULT: FEHLER")
            return 2
        try:
            daten = sammle_via_gh(
                args.repo, args.autor, args.seit, mit_hunks=not args.ohne_hunks
            )
        except GhFehler as exc:
            print(
                f"⚠ {exc} — NICHT bewertbar (nie als sauber werten).", file=sys.stderr
            )
            print("RESULT: FEHLER")
            return 2

    ergebnisse: list[dict] = []
    if will_issues:
        ergebnisse += befunde_issues(daten["prs"], daten["issues"])
    if will_belege:
        ergebnisse += befunde_belege(daten["texte"], daten["pr_zustaende"])
    if will_serien:
        ergebnisse += befunde_serien(daten["prs"], stunden=args.stunden)

    befunde = [e for e in ergebnisse if e["art"] == "befund"]
    hinweise = [e for e in ergebnisse if e["art"] == "hinweis"]

    if args.json:
        print(
            json.dumps(
                {
                    "befunde": befunde,
                    "hinweise": hinweise,
                    "result": "BEFUND"
                    if befunde
                    else ("HINWEIS" if hinweise else "OK"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if befunde:
            print("⚠ Sitzungs-Abgleich — Befunde (advisory):")
            for e in befunde:
                print(_ausgabe_zeile(e))
        if hinweise:
            print("◌ NICHT falsifizierbar / nicht abrufbar — keine Entwarnung:")
            for e in hinweise:
                print(_ausgabe_zeile(e))
        if not befunde and not hinweise:
            print("✅ Sitzungs-Abgleich sauber (Issues, Belege, Serien).")

    if befunde:
        print(f"RESULT: BEFUND {len(befunde)} (hinweise={len(hinweise)})")
        return 1
    if hinweise:
        print(f"RESULT: HINWEIS {len(hinweise)}")
        return 0
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
