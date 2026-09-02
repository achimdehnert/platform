#!/usr/bin/env python3
"""Claude Code Stop hook — Artefakt-Budget (Scope-Checkpoint, maschinell).

Macht den meistgezaehlten Retro-Slug ausfuehrbar statt notiert:
`scope-checkpoint-not-durably-recorded` stand am 2026-08-02 bei x9 — der
hoechste Zaehler im ganzen Register (`tools/retro_kpis.py`), ohne dass je ein
Gate daraus wurde. Die Hausregel checkpointet am DRITTEN REPO; real eskalieren
Sessions aber ueber die ARTEFAKT-Zahl: Am 2026-07-31 wurde aus "analysiere
SB-Neu" eine Kette von 12 PRs in 2 Repos — der Repo-Trigger feuerte nie
(Retro 8ed6a2, Massnahme "Artefakt-Budget je Auftrag").

Der Hook zaehlt im Session-Transkript angelegte Artefakte und erinnert ab der
Schwelle an den Scope-Checkpoint: "ist das noch der Auftrag?". Er blockiert
NICHTS — der Checkpoint ist eine Frage an den Menschen, kein Verbot.

**Gezaehlt wird das Artefakt, nicht das Kommando** (Fix 2026-08-17, Prio 4 des
Handovers). Bis dahin matchte er `gh pr create` im Bash-Kommando und lag damit
in BEIDE Richtungen falsch: 8 gemeldet, 37 tatsaechlich. 17 PRs aus einer
Schleife zaehlten als eins, PRs via `gh api …/pulls -X POST` gar nicht — und
eine blosse Codesuche nach dem Muster erhoehte den Zaehler um 1. Untererfassung
und Uebererfassung heben sich nicht auf: blind bei der Massenaktion, laut bei
der harmlosen Suche. Beides derselbe Fehler, den der Tag dreimal zeigte: **die
Bedingung prueft eine Schreibweise und meint eine Sache.** Details in `sammle`.

Contract (wie evidence_claim_scanner.py): Stop-Event-JSON auf stdin, IMMER
exit 0. Bei Feuern: additionalContext-JSON auf stdout. Feuert je Schwelle
GENAU EINMAL (State-Datei), sonst wird der Reminder zum Rauschen, das er
verhindern soll.

**Jedes Feuern wird protokolliert** (`gate_hits.notiere`). Bis 2026-08-16 tat
er das nicht, und genau daran scheiterte seine eigene Kalibrierung: am
2026-08-15 loeste er achtmal aus und bekam achtmal dieselbe Antwort ("im
Auftrag") — nachlesbar aber nur im Sitzungsverlauf, nicht in Daten. Wer ueber
mehrere Sitzungen messen will, misst sonst Erinnerung. Das war am selben Tag
schon der Kernbefund bei den Welle-1-Scannern (Retro d57884).

Protokolliert wird nicht nur die PR-Zahl, sondern die drei Kandidat-Kriterien
aus dem #1640-Register — denn die offene Frage ist nicht "wie viele PRs?",
sondern "Auftrag oder ungefragt gewachsene Kette?":

- ``prs_seit_owner``  PRs seit der letzten Nachricht des Menschen. **Das** ist
  der Runaway-Indikator; die absolute PR-Zahl ist es nicht.
- ``repos``           GENANNTE Repos — traegt keine Schwelle, s.u.
- ``repos_mit_artefakt``  Repos, in denen wirklich etwas entstand.
- ``prod``            ob ein Prod-/Publish-Schritt vorkam (grobe Marker, s.u.).

**Die Schwelle liegt seit 2026-08-17 auf ``prs_seit_owner``** (Owner-Entscheid
zur Auswertung in #1640). Die absolute PR-Zahl loeste sie ab, weil sie nicht
misst, was sie vorgibt: bei 4 feuerte sie in sechs von acht echten Sitzungen,
mehrfach je Sitzung, und stieg monoton — sie misst Arbeitsmenge, nicht
Scope-Drift. ``prs_seit_owner`` dagegen lag in sieben von acht Sitzungen bei
<= 2 und erreichte genau einmal 17: in der Sitzung, in der eine einzelne
Schleife 17 PRs anlegte.

``repos`` bleibt im Protokoll, traegt aber bewusst **keine** Schwelle: es zaehlt
jedes genannte Repo, Lesezugriffe eingeschlossen, und kam in echten Sitzungen
auf 50 bzw. 26 — waehrend die Hausregel am dritten *bearbeiteten* checkpointet.
Dafuer gibt es jetzt ``repos_mit_artefakt``.

Env:
  ARTEFAKT_BUDGET_SEIT_OWNER       Schwelle (Default 5). 0 deaktiviert den Hook.
  ARTEFAKT_BUDGET_SEIT_OWNER_PROD  Gesenkte Schwelle, wenn ein Prod-/Publish-
                                   Schritt in der Kette vorkam (Default 3).
  GATE_HITS_DATEI                  Protokoll-Ziel (gate_hits.py; Tests setzen es).
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)

GATE_HEADER = {
    "slug": "artefakt-budget-schwelle-erreicht",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-16",
    "evidence": "tools/tests/test_artefakt_budget.py",
}

# --- Anlage-ABSICHT im Kommando -------------------------------------------
# Zwei Wege, ein Artefakt anzulegen. Der zweite fehlte bis 2026-08-17 komplett.
_CREATE_CLI = re.compile(r"\bgh\s+(?:pr|issue)\s+create\b")
_POST = re.compile(r"(?:-X|--method)[=\s\"',]*POST\b")
_API_ZIEL = re.compile(r"/(?:pulls|issues)\b")
# Ein Kommentar/Review am Artefakt ist kein neues Artefakt — sein html_url
# sieht aber fast genauso aus. Ohne diesen Ausschluss zaehlt jeder
# `gh api .../issues/40/comments -X POST` als neu angelegtes Issue.
_API_NICHT = re.compile(r"/(?:comments|reviews|labels|assignees)\b")

# --- Anlage-BELEG im Ergebnis ---------------------------------------------
# Die URL des Artefakts. `(?![\w#/-])` schliesst `#issuecomment-...` und
# tiefere Pfade aus — sonst waere jeder Kommentar-Link ein Artefakt.
_ARTEFAKT_URL = re.compile(
    r"https://github\.com/([\w.-]+/[\w.-]+)/(pull|issues)/(\d+)(?![\w#/-])"
)

# Repo-Bezug eines gh-Aufrufs, falls er nicht im Repo-Verzeichnis lief.
_REPO_FLAG = re.compile(r"(?:\B-R|--repo)[= ]\s*([\w.-]+/[\w.-]+)")

# Prod-/Publish-Schritt — bewusst grob und eng zugleich: nur Kommandos, die
# nach draussen wirken. `gh pr merge` steht NICHT drin (zu haeufig, und ob ein
# Merge deployt, haengt am Repo — das waere geraten, nicht gemessen).
_PROD = re.compile(
    r"\bdocker\s+push\b|\btwine\s+upload\b|\bgh\s+release\s+create\b"
    r"|\bdeploy\.sh\b|\bgh\s+workflow\s+run\b[^\n]{0,80}"
    r"(?:deploy|publish|release|ship)"
)


# Zeilen-Schluessel, die zur Messung beitragen koennen — Vorfilter in `sammle`.
# Wer hier etwas ergaenzt, ergaenzt es auch dort, und umgekehrt.
_TRAGENDE_SCHLUESSEL = (
    '"tool_use"',  # Kommando: Anlage-Absicht, --repo, Prod-Marker
    '"tool_result"',  # Beleg: Artefakt-URL
    '"user"',  # Nachricht des Menschen (setzt prs_seit_owner zurueck)
    "prRepository",  # beruehrtes Repo ohne Kommando
    '"cwd"',  # beruehrtes Repo ueber das Arbeitsverzeichnis
)


def _ist_anlage_absicht(cmd: str) -> bool:
    """Sieht dieses Kommando aus, als solle es ein Artefakt ANLEGEN?

    Absicht allein zaehlt nichts — sie qualifiziert nur das Ergebnis fuer die
    Auswertung (siehe ``sammle``). Genau deshalb darf sie grob sein.
    """
    if _CREATE_CLI.search(cmd):
        return True
    return bool(
        _POST.search(cmd) and _API_ZIEL.search(cmd) and not _API_NICHT.search(cmd)
    )


def _text_von(block: dict) -> str:
    """Ergebnistext eines tool_result — flach oder als Block-Liste."""
    inhalt = block.get("content")
    if isinstance(inhalt, list):
        return " ".join(str(t.get("text", "")) for t in inhalt if isinstance(t, dict))
    return str(inhalt or "")


def sammle(transcript_path: Path) -> dict:
    """Angelegte Artefakte + die drei Kandidat-Kriterien, in EINEM Durchlauf.

    **Gezaehlt wird das Artefakt, nicht das Kommando.** Ein Kommando mit
    Anlage-Absicht wird ueber seine ``tool_use``-Id mit seinem ``tool_result``
    verbunden; gezaehlt werden die *verschiedenen* Artefakt-URLs, die dort
    zurueckkommen. Das behebt drei gemessene Fehler der Kommando-Zaehlung
    (Stand 2026-08-17: 8 gemeldet, 37 tatsaechlich):

    1. **Schleife.** ``for r in ...; do gh pr create ...; done`` steht EINMAL
       im Kommando und legt N PRs an. Die alte Zaehlung sah 1, das Ergebnis
       zeigt N URLs.
    2. **API-Pfad.** ``gh api .../pulls -X POST`` enthaelt kein ``gh pr
       create`` und zaehlte gar nicht — der Weg, den man nimmt, wenn GraphQL
       503 wirft.
    3. **Blosse Erwaehnung.** Eine Codesuche nach dem Muster erhoehte den
       Zaehler um 1. Ihr Ergebnis enthaelt Quellzeilen, keine Artefakt-URL —
       sie zaehlt jetzt 0.

    Ein gescheiterter Anlageversuch (HTTP 503, Konflikt) liefert keine URL und
    zaehlt damit ebenfalls 0 — richtig, denn es entstand kein Artefakt.

    **Benannte Restluecke:** wird die Ausgabe eines echten ``gh pr create``
    weggeworfen (``>/dev/null``, ``| wc -l``), fehlt der Beleg und der PR
    bleibt ungezaehlt. Bewusst so: der Melder soll eine verdeckte Anlage
    untererfassen, statt sich eine aus einer Erwaehnung zu erfinden.

    ``prs_seit_owner`` zaehlt die PRs, die NACH der letzten Nachricht des
    Menschen erstmals auftauchen. Eine Nachricht ist ein ``user``-Eintrag mit
    Text-Inhalt — Tool-Ergebnisse und System-Erinnerungen (``isMeta``) sind es
    nicht, obwohl sie denselben Typ tragen.
    """
    ergebnis = {
        "prs": set(),
        "issues": set(),
        "prs_seit_owner": 0,
        "repos": 0,
        "repos_mit_artefakt": 0,
        "owner_nachrichten": 0,
        "prod": 0,
    }
    try:
        fh = transcript_path.open(encoding="utf-8", errors="replace")
    except OSError:
        return ergebnis

    absichten: set[str] = set()
    prs: set[str] = set()
    issues: set[str] = set()
    seit_owner: set[str] = set()
    repos: set[str] = set()
    # `repos` zaehlt jedes GENANNTE Repo (--repo-Flag, cwd) — auch reine
    # Lesezugriffe. Gemessen am 2026-08-17 ergab das 50 bzw. 26 Repos in echten
    # Sitzungen, waehrend die Hausregel am DRITTEN bearbeiteten checkpointet.
    # Deshalb daneben die belastbare Zahl: Repos, in denen wirklich etwas
    # entstanden ist. `repos` bleibt fuer die Vergleichbarkeit des
    # Kalibrierregisters erhalten, traegt aber keine Schwelle (#1640).
    repos_mit_artefakt: set[str] = set()
    # Wie oft der Mensch gesprochen hat. Kein Kriterium, sondern der ANKER fuer
    # die Entprellung: `prs_seit_owner` allein reicht nicht, weil der Hook nur
    # den Endstand jedes Stop sieht und den Einbruch auf 0 dazwischen nie —
    # eine zweite Kette, die wieder genau 5 erreicht, waere sonst von der
    # ersten ununterscheidbar und bliebe stumm.
    owner_nachrichten = 0
    prod = False

    with fh:
        for raw in fh:
            # Billiger Vorfilter vor dem JSON-Parse. Er muss JEDEN Beitrag
            # abdecken, den die Auswertung unten kennt — sonst ist er selbst
            # wieder eine Bedingung, die eine Schreibweise prueft statt der
            # Sache. Erster Entwurf liess `prRepository` weg und verlor damit
            # still ein Repo; `test_should_measure_repos_and_prod_step` fing es.
            if not any(k in raw for k in _TRAGENDE_SCHLUESSEL):
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if obj.get("type") == "user" and not obj.get("isMeta"):
                inhalt = (obj.get("message") or {}).get("content")
                if isinstance(inhalt, str) and inhalt.strip():
                    seit_owner.clear()  # der Mensch hat sich gemeldet — Kette neu
                    owner_nachrichten += 1

            if obj.get("prRepository"):
                repos.add(str(obj["prRepository"]).split("/")[-1])
            cwd = str(obj.get("cwd") or "")
            if "/github/" in cwd:
                repos.add(cwd.split("/github/", 1)[1].split("/")[0])

            msg = obj.get("message", obj)
            content = msg.get("content", []) if isinstance(msg, dict) else []
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue

                if c.get("type") == "tool_use":
                    cmd = str((c.get("input") or {}).get("command", ""))
                    if not cmd:
                        continue
                    repos.update(m.split("/")[-1] for m in _REPO_FLAG.findall(cmd))
                    prod = prod or bool(_PROD.search(cmd))
                    if _ist_anlage_absicht(cmd) and c.get("id"):
                        absichten.add(str(c["id"]))
                    continue

                if c.get("type") != "tool_result":
                    continue
                if str(c.get("tool_use_id", "")) not in absichten:
                    continue  # ein Ergebnis ohne Anlage-Absicht belegt nichts
                for repo, art, nr in _ARTEFAKT_URL.findall(_text_von(c)):
                    url = f"{repo}#{art}{nr}"
                    ziel = prs if art == "pull" else issues
                    if url not in ziel:
                        ziel.add(url)
                        repos.add(repo.split("/")[-1])
                        repos_mit_artefakt.add(repo.split("/")[-1])
                        if art == "pull":
                            seit_owner.add(url)

    ergebnis.update(
        prs=prs,
        issues=issues,
        prs_seit_owner=len(seit_owner),
        repos=len(repos),
        repos_mit_artefakt=len(repos_mit_artefakt),
        owner_nachrichten=owner_nachrichten,
        prod=int(prod),
    )
    return ergebnis


def zaehle_artefakte(transcript_path: Path) -> tuple[int, int]:
    """(prs, issues) — belegte Anlagen, siehe ``sammle``."""
    d = sammle(transcript_path)
    return len(d["prs"]), len(d["issues"])


def messe_kontext(transcript_path: Path) -> dict:
    """Die drei Kandidat-Kriterien aus dem #1640-Register."""
    d = sammle(transcript_path)
    return {k: d[k] for k in ("repos", "prs_seit_owner", "prod")}


def _state_file(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"artefakt_budget_{session_id or 'na'}.txt"


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0

    budget = int(os.environ.get("ARTEFAKT_BUDGET_SEIT_OWNER", "5") or 0)
    budget_prod = int(os.environ.get("ARTEFAKT_BUDGET_SEIT_OWNER_PROD", "3") or 0)
    if budget <= 0:
        return 0

    tp = event.get("transcript_path")
    if not tp:
        return 0
    gesammelt = sammle(Path(tp))
    prs, issues = len(gesammelt["prs"]), len(gesammelt["issues"])
    seit_owner = gesammelt["prs_seit_owner"]

    # Ein Prod-/Publish-Schritt in der Kette senkt die Schwelle.
    schwelle = budget_prod if (gesammelt["prod"] and budget_prod > 0) else budget
    if seit_owner < schwelle:
        return 0

    # Einmal je erreichtem Stand feuern, nicht bei jedem Stop danach.
    #
    # Entprellt wird gegen (Gespraechsrunde, Stand), nicht gegen den Stand
    # allein. Grund: der Hook sieht bei jedem Stop nur den ENDSTAND, nie den
    # Einbruch dazwischen. Meldet sich der Mensch und waechst die naechste Kette
    # erneut auf denselben Wert, waere sie am Zaehler nicht von der ersten zu
    # unterscheiden — der Melder bliebe fuer den Rest der Sitzung stumm. Ein
    # erster Entwurf verglich nur "gefallen?" und hatte genau diese Luecke;
    # `test_should_fire_again_after_owner_spoke_and_chain_regrew` fand sie.
    sf = _state_file(str(event.get("session_id", "")))
    runde = gesammelt["owner_nachrichten"]
    try:
        letzte_runde, last = (int(x) for x in sf.read_text().strip().split(":", 1))
    except (OSError, ValueError):
        letzte_runde, last = -1, 0
    if runde != letzte_runde:
        last = 0  # neue Kette — der Merker der vorigen gilt nicht mehr
    if seit_owner <= last:
        return 0
    try:
        sf.write_text(f"{runde}:{seit_owner}")
    except OSError:
        pass  # State-Verlust heisst schlimmstenfalls ein Reminder mehr — nie blocken

    ktx = gesammelt  # dieselbe Messung, kein zweiter Durchlauf

    # Treffer mitschreiben, BEVOR gemeldet wird — ohne Spur laesst sich die
    # Kalibrierung ueber mehrere Sitzungen weder belegen noch bestreiten
    # (#1640; Realfall 2026-08-15: achtmal gefeuert, null Daten).
    gate_hits.notiere(
        GATE_HEADER["slug"],
        f"prs={prs} issues={issues} schwelle={schwelle} "
        f"repos={ktx['repos']} repos_mit_artefakt={ktx['repos_mit_artefakt']} "
        f"prs_seit_owner={ktx['prs_seit_owner']} prod={ktx['prod']}",
        session=str(event.get("session_id", "")),
        modus=GATE_HEADER["mode"],
    )

    hinweis = (
        f"📦 Artefakt-Budget: {seit_owner} PRs seit deiner letzten Nachricht"
        + (
            f" (Schwelle {schwelle}, wegen Prod-Schritt gesenkt)"
            if schwelle == budget_prod and ktx["prod"]
            else f" (Schwelle {schwelle})"
        )
        + f". Insgesamt in dieser Session: {prs} PRs"
        + (f" + {issues} Issues" if issues else "")
        + f" in {ktx['repos_mit_artefakt']} Repo(s)"
        + (", Prod-/Publish-Schritt dabei" if ktx["prod"] else "")
        + ". Scope-Checkpoint: ist das noch "
        "der urspruengliche Auftrag? Wenn ja — kurz dem Menschen spiegeln, woraus "
        "die Kette entstand; wenn unklar — Zwischenstand statt weiterbauen. "
        "(scope-checkpoint x9 im Retro-Register; Schwelle via "
        "ARTEFAKT_BUDGET_SEIT_OWNER)"
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": hinweis,
                }
            }
        )
    )
    return 0


def main_sicher() -> int:
    """`main()` unter dem Hook-Vertrag: Exit 0 immer, ausser bewusstes Blocken.

    Siehe `evidence_claim_scanner.main_sicher` fuer die Begruendung; bewusst
    dupliziert statt geteilt, damit der Auffangbogen keinen Import braucht.
    """
    try:
        return main()
    except Exception as exc:  # noqa: BLE001 — Hook-Vertrag: nie blockieren
        print(f"artefakt_budget: {type(exc).__name__}: {exc}"[:400], file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
