#!/usr/bin/env python3
"""sichtbarkeits_drift_melder.py — zaehlt, was noch an `achimdehnert/platform` haengt.

## Warum es das gibt

`platform` ist oeffentlich und soll privat werden (KONZ-039, Umsetzung platform#3234).
Der Schalter selbst ist eine Sekunde Arbeit — das Problem ist, was danach bricht:
Reusable Workflows und Composite Actions aus fremden Orgs koennen einen privaten
Baustein nicht aufrufen (G1-Experiment 2026-08-02, auch privat→privat), unauthenti-
fizierte Raw-Downloads liefern 404, ein Klon in fremder CI scheitert. Die
Konsumentenzahl wurde im August zweimal falsch ermittelt (20 → 34 → 26), weil jede
Methode allein Luecken hat: lokale Klone kennen nur, was je ausgecheckt war, die
Code-Suche nur, was der Index traegt. Dieser Melder vereinigt beide und zaehlt vier
Dinge, die vor dem Flip auf ihren Zielwert muessen:

| Zaehler  | was                                                         | Ziel |
|----------|-------------------------------------------------------------|------|
| aufrufer | Repos mit `uses: achimdehnert/platform/.github/…` oder Klon | 0    |
| raw      | Repos mit `raw.githubusercontent.com/achimdehnert/platform` | 0    |
| laufzeit | davon Code ausserhalb CI/Klickdummy/Doku, plus `_deploy-*.yml` | 0  |
| kopien   | Repos, die `_*.yml`-Bausteine halten (Kanon: iilgmbh/shared-ci) | 1 |
| fristen  | aktive Konzepte mit abgelaufenem `review_by`                | 0    |

`laufzeit` steht gesondert, weil ein Raw-Treffer in `dev-hub/apps/core/…` beim Flip
eine laufende App trifft, ein Schema-Verweis in einer Klickdummy-Spec nicht — in der
Summe von 26 ginge der eine unter. `fristen` steht hier, weil KONZ-039 selbst am
2026-09-15 stumm verfiel: kein Werkzeug las `review_by`. Ein Umbau, der an Fristen
haengt, braucht den Fristen-Melder im selben Werkzeug.

## Lebenszyklus

Zielzustand (Owner-Entscheid 2026-10-04, #3234): platform zieht in die Org iilgmbh
und wird DORT privat — nicht privat im Privatkonto, das kostet Secret-Scanning,
Push-Schutz und freie Actions-Minuten (Wache unten). Ablauf:

1. WARN, solange ein Zaehler ueber Ziel liegt; die Ausgabe nennt je Restposten den
   naechsten Zug, die Messreihe das prognostizierte Null-Datum.
2. PASS bei 0 / 0 / 1 / 0; eine PASS-Serie ueber sieben Kalendertage (K5) gibt den
   Umzug frei. Der Umzug bricht verbliebene Reusable-Workflow-Aufrufer genau wie ein
   Flip (G2-Probe 2026-10-05) — darum K5 VOR dem Transfer, nicht danach.
3. Owner uebertraegt, dann privat. Ab da ist jeder neue Treffer Rueckfall, und die
   Wache meldet fehlenden Schutz oder bezahlte Minuten.

Sunset, wenn platform PRIVATE ist und der Melder 30 Tage nichts meldet.

## Fuer die naechste Sitzung

`--kurz` ist der Stand, `--json` der Stand mit `naechster_zug`. Kein Dokument muss
nachgezogen werden: Issue, Konzept und Board verweisen hierher. In oeffentliche Texte
(platform ist bis zum Umzug public) nur `--oeffentlich` — die volle Ausgabe nennt
Kunden-Repos und Betraege.

Grenzen: `gh search code` ist eine untere Schranke (Index, 100 Treffer je Abfrage).
`--offline` laesst die Netz-Zaehler als `nicht messbar` stehen, statt sie mit 0 zu
faelschen — ein Melder, der ohne Netz Entwarnung gibt, waere der blinde Melder, gegen
den er gebaut wurde. Kosten brauchen den Billing-Scope des Tokens; fehlt er, bleibt
die Wache vor dem Umzug still und macht den Status danach UNKLAR.

    python3 tools/sichtbarkeits_drift_melder.py --kurz
    python3 tools/sichtbarkeits_drift_melder.py --json --messreihe <hostlokal>.jsonl
    python3 tools/sichtbarkeits_drift_melder.py --kurz --oeffentlich   # fuer Issues/PRs
    python3 tools/sichtbarkeits_drift_melder.py --offline   # nur lokale Klone + Fristen
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import melder_ergebnis  # noqa: E402

WERKZEUG_VERSION = "2"
MELDER = "sichtbarkeits_drift_melder"
SELBST = "achimdehnert/platform"
# Zielort nach dem Umzug (Owner-Entscheid 2026-10-04, #3234): Die API leitet den
# alten Namen weiter, Verweise auf den neuen zaehlen nach dem Umzug genauso —
# ein `uses: iilgmbh/platform/…` in einem oeffentlichen Repo bricht beim Flip wie
# der alte.
ZIELORT = "iilgmbh/platform"
SELBST_NAMEN = frozenset({SELBST, ZIELORT})
# Normale Gruppe, kein (?:…): die Muster laufen auch durch `git grep -E` (POSIX-ERE).
BESITZER_RE = r"(achimdehnert|iilgmbh)"
KANON = "iilgmbh/shared-ci"
KOPIEN_KANDIDATEN = (SELBST, "achimdehnert/shared-ci", KANON)
ZIEL = {"aufrufer": 0, "raw": 0, "laufzeit": 0, "kopien": 1, "fristen": 0}
AUFTRAG = "#3234"
# K5: so viele Kalendertage muss die PASS-Serie ueberspannen, bevor der Umzug frei ist.
K5_TAGE = 7
# Prognose nur aus dem juengsten Fenster: der Abbau verlaeuft in Schueben, eine
# Gerade ueber Monate unterschaetzt das Tempo nach einem Schub.
PROGNOSE_FENSTER_TAGE = 30

# Was beim Flip bricht. `uses:` faengt Reusable Workflows UND Composite Actions
# (`.github/actions/…`) — Letztere waren im Konzept nicht gezaehlt (11 lokale Caller).
AUFRUF_MUSTER = rf"uses: *{BESITZER_RE}/platform/\.github/"
KLON_MUSTER = rf"git clone[^\n]*github\.com[:/]{BESITZER_RE}/platform"
# actions/checkout mit `repository: achimdehnert/platform` in fremder CI — die
# Flotten-Workflows receive-windsurf-rules.yml (ADR-263) und silent-failure-lint.yml
# holen platform so; mit GITHUB_TOKEN scheitert das nach dem Flip (23 Klone, 2026-09-16).
CHECKOUT_MUSTER = rf"repository: *{BESITZER_RE}/platform\b"
# Ein Checkout mit eigenem Secret als Token (PAT) uebersteht den Flip, solange das
# Secret platform lesen darf — Realfall mcp-hub ci.yml (PROJECT_PAT, #3234). Er
# wird gelistet, zaehlt aber nicht; GITHUB_TOKEN bleibt ein Aufrufer.
TOKEN_ZEILE_RE = re.compile(
    r"^(?P<einzug> *)token: *['\"]?\$\{\{ *secrets\.(?!GITHUB_TOKEN\b)\w+ *\}\}"
)
RAW_MUSTER = rf"raw\.githubusercontent\.com/{BESITZER_RE}/platform"
# Raw-Treffer, die NICHT zur Laufzeit brechen: CI (eigene Klasse), Klickdummy-
# Schema-Verweise, Doku.
NICHT_LAUFZEIT = re.compile(r"(^|/)(\.github/|klickdummy/|docs/)|\.md$")
# Ausnahme von der CI-Klasse: Deploy-Bausteine laden zur Deploy-Zeit, ein Abbruch
# dort stoppt jeden Deploy jedes Callers (shared-ci _deploy-*.yml, #3596).
DEPLOY_BAUSTEIN = re.compile(r"(^|/)\.github/workflows/_deploy-[^/]*\.ya?ml$")
# Konzepte, deren Frist niemanden mehr bindet.
INAKTIV = {"sunset", "stale", "done", "superseded", "archived", "rejected"}
ORIGIN_RE = re.compile(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?\s*$")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.S)
# Fetch-Alter je lokalem Klon (Tage) — gefuellt von scanne_lokal, gemeldet im JSON.
FETCH_ALTER: dict[str, int] = {}


# ── lokale Klone ─────────────────────────────────────────────────────────────


def _origin(repo_dir: Path) -> str | None:
    """`owner/name` aus .git/config — ohne git-Aufruf, damit Tests Verzeichnisse
    faelschen koennen. Worktrees (.git ist eine Datei) zaehlen nicht: Duplikate."""
    cfg = repo_dir / ".git" / "config"
    if not cfg.is_file():
        return None
    in_origin = False
    for zeile in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
        s = zeile.strip()
        if s.startswith("["):
            in_origin = s == '[remote "origin"]'
        elif in_origin and s.startswith("url"):
            m = ORIGIN_RE.search(s.split("=", 1)[1])
            return f"{m.group(1)}/{m.group(2)}" if m else None
    return None


def _grep(repo_dir: Path, muster: str) -> list[str]:
    """Pfade mit Treffer in `origin/main` — nicht in der Arbeitskopie.

    Die Arbeitskopie kann Wochen hinter dem Remote liegen (Realfall 2026-09-16:
    gaeb-toolkit war umgehaengt und gemergt, der lokale Klon zaehlte weiter als
    Aufrufer). `git grep` auf dem Remote-Tracking-Ref sieht nur Getracktes — .venv,
    build/ und Co. fallen damit von selbst weg — und ist so aktuell wie der letzte
    Fetch; dessen Alter meldet `fetch_alter_tage`."""
    try:
        p = subprocess.run(
            ["git", "grep", "-l", "-E", muster, "origin/main", "--", "."],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return sorted(z.split(":", 1)[1] for z in p.stdout.split() if ":" in z)


def _zeige(repo_dir: Path, pfad: str) -> str | None:
    """Inhalt von `origin/main:<pfad>` — None, wenn nicht lesbar."""
    try:
        p = subprocess.run(
            ["git", "show", f"origin/main:{pfad}"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def nur_token_checkouts(text: str | None) -> bool:
    """True, wenn jeder platform-Checkout der Datei ein eigenes Secret als Token
    setzt und die Datei sonst nichts von platform holt (`uses:`, `git clone`).

    Der Token muss im selben `with:`-Block stehen wie `repository:` — gleicher
    Einzug, ohne dass ein flacherer Schluessel dazwischen den Block beendet. Im
    Zweifel False: ein unlesbarer oder unklarer Checkout zaehlt als Aufrufer."""
    if not text or re.search(AUFRUF_MUSTER, text) or re.search(KLON_MUSTER, text):
        return False
    zeilen = text.splitlines()
    gefunden = False
    for i, z in enumerate(zeilen):
        m = re.match(r"^( *)" + CHECKOUT_MUSTER, z)
        if not m:
            if re.search(CHECKOUT_MUSTER, z):
                return False  # z. B. Flow-Mapping `with: {repository: …}`
            continue
        gefunden = True
        einzug = len(m.group(1))
        block = []
        for richtung in (range(i - 1, -1, -1), range(i + 1, len(zeilen))):
            for j in richtung:
                s = zeilen[j]
                if not s.strip() or s.lstrip().startswith("#"):
                    continue
                if len(s) - len(s.lstrip(" ")) < einzug:
                    break
                block.append(s)
        if not any(
            (t := TOKEN_ZEILE_RE.match(s)) and len(t.group("einzug")) == einzug
            for s in block
        ):
            return False
    return gefunden


def fetch_alter_tage(repo_dir: Path, jetzt: float | None = None) -> int | None:
    """Tage seit dem letzten Fetch — None, wenn nie gefetcht."""
    fh = repo_dir / ".git" / "FETCH_HEAD"
    if not fh.is_file():
        return None
    jetzt = time.time() if jetzt is None else jetzt
    return int((jetzt - fh.stat().st_mtime) // 86400)


def scanne_lokal(
    github_dir: Path, fetch: bool = False
) -> dict[str, dict[str, list[str]]]:
    """Je Repo (owner/name) die Trefferpfade je Klasse. platform selbst ist kein
    Konsument: eigene Aufrufe ueberleben den Flip."""
    treffer: dict[str, dict[str, list[str]]] = {}
    if not github_dir.is_dir():
        return treffer
    for d in sorted(github_dir.iterdir()):
        repo = _origin(d) if d.is_dir() else None
        if not repo or repo in SELBST_NAMEN:
            continue
        if fetch:
            subprocess.run(
                ["git", "fetch", "-q", "origin", "main"],
                cwd=d,
                capture_output=True,
                timeout=60,
                check=False,
            )
        alter = fetch_alter_tage(d)
        if alter is not None:
            FETCH_ALTER[repo] = max(FETCH_ALTER.get(repo, 0), alter)
        aufruf = [p for p in _grep(d, AUFRUF_MUSTER) if p.startswith(".github/")]
        mit_token = []
        for p in _grep(d, CHECKOUT_MUSTER):
            if not p.startswith(".github/"):
                continue
            if nur_token_checkouts(_zeige(d, p)):
                mit_token.append(p)
            else:
                aufruf.append(p)
        aufruf += _grep(d, KLON_MUSTER)
        raw = _grep(d, RAW_MUSTER)
        if aufruf or raw or mit_token:
            eintrag = treffer.setdefault(repo, {"aufruf": [], "raw": []})
            eintrag["aufruf"] = sorted(set(eintrag["aufruf"]) | set(aufruf))
            eintrag["raw"] = sorted(set(eintrag["raw"]) | set(raw))
            if mit_token:
                eintrag["mit_token"] = sorted(
                    set(eintrag.get("mit_token", [])) | set(mit_token)
                )
    return treffer


# ── Netz: Code-Suche, Kopien, Sichtbarkeit ───────────────────────────────────


def _gh(*args: str) -> str | None:
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def suche_code(abfrage: str) -> list[tuple[str, str]]:
    out = _gh("search", "code", abfrage, "--limit", "100", "--json", "repository,path")
    if not out:
        return []
    try:
        return [(t["repository"]["nameWithOwner"], t["path"]) for t in json.loads(out)]
    except (ValueError, KeyError, TypeError):
        return []


def lies_datei_netz(repo: str, pfad: str) -> str | None:
    """Dateiinhalt im Default-Branch per Contents-API — None, wenn nicht lesbar."""
    out = _gh("api", f"repos/{repo}/contents/{pfad}", "--jq", ".content")
    if not out:
        return None
    try:
        return base64.b64decode(out).decode("utf-8", errors="replace")
    except ValueError:
        return None


def scanne_netz() -> dict[str, dict[str, list[str]]]:
    treffer: dict[str, dict[str, list[str]]] = {}
    abfragen = [
        (klasse, abfrage.format(ort=ort))
        for ort in sorted(SELBST_NAMEN)
        for klasse, abfrage in (
            ("aufruf", "uses: {ort}/.github"),
            ("checkout", "repository: {ort}"),
            ("raw", "raw.githubusercontent.com/{ort}"),
        )
    ]
    for klasse, abfrage in abfragen:
        for repo, pfad in suche_code(abfrage):
            if repo in SELBST_NAMEN:
                continue
            # Ein `uses:` in Doku (Realfall mcp-hub docs/ADR-160) ist kein Aufrufer.
            if klasse != "raw" and not pfad.startswith(".github/"):
                continue
            if klasse == "checkout":
                klasse_hier = (
                    "mit_token"
                    if nur_token_checkouts(lies_datei_netz(repo, pfad))
                    else "aufruf"
                )
            else:
                klasse_hier = klasse
            e = treffer.setdefault(repo, {"aufruf": [], "raw": []})
            liste = e.setdefault(klasse_hier, [])
            if pfad not in liste:
                liste.append(pfad)
    return treffer


def ist_archiviert(repo: str) -> bool | None:
    """None = nicht messbar (offline)."""
    out = _gh("repo", "view", repo, "--json", "isArchived", "--jq", ".isArchived")
    return None if out is None else out.strip() == "true"


def ohne_archivierte(
    konsumenten: dict[str, dict[str, list[str]]],
) -> tuple[dict[str, dict[str, list[str]]], list[str]]:
    """Archivierte Repos sind read-only: ihre CI laeuft nicht mehr, ihr Verweis
    kann nicht mehr umgehaengt werden (Realfall research-hub 2026-09-16)."""
    lebend, archiviert = {}, []
    for repo, e in konsumenten.items():
        if ist_archiviert(repo):
            archiviert.append(repo)
        else:
            lebend[repo] = e
    return lebend, sorted(archiviert)


def zaehle_kopien() -> list[str] | None:
    """Repos, die mindestens einen `_*.yml`-Baustein halten. None = nicht messbar.

    Archivierte Repos zaehlen nicht: ein eingefrorenes Duplikat kann nicht mehr
    divergieren, und genau die Divergenz misst K3. achimdehnert/shared-ci wurde am
    2026-09-16 mit Tombstone archiviert (#2113) — ohne diese Regel bliebe Kopien = 3.
    """
    halter = []
    for repo in KOPIEN_KANDIDATEN:
        archiviert = _gh(
            "repo", "view", repo, "--json", "isArchived", "--jq", ".isArchived"
        )
        if archiviert is None:
            return None
        if archiviert.strip() == "true":
            continue
        out = _gh("api", f"repos/{repo}/contents/.github/workflows", "--jq", ".[].name")
        if out is None:
            return None
        if any(re.match(r"_.*\.ya?ml$", n) for n in out.split()):
            halter.append(repo)
    return halter


def sichtbarkeit() -> str | None:
    out = _gh("repo", "view", SELBST, "--json", "visibility", "--jq", ".visibility")
    return out.strip() if out else None


# ── Wache: was der Flip selbst verschlechtern kann ───────────────────────────
#
# Die Zaehler oben messen, was beim Flip BRICHT. Die Wache misst, was er
# VERSCHLECHTERT, ohne dass etwas bricht — gemessen 2026-10-04 (#3234):
# - Secret-Scanning und Push-Schutz gibt es fuer private Repos eines Privatkontos
#   nicht; in der Enterprise-Org iilgmbh bleiben sie an (G2-Probe 2026-10-05).
# - Oeffentliche Repos rechnen Actions-Minuten nicht ab. platform verbraucht so
#   viele, dass ein Flip ohne Kontingent laufende Kosten erzeugt.
# Beides faellt erst nach dem Flip auf, und dann nur auf der Rechnung bzw. beim
# naechsten durchgerutschten Secret — deshalb misst der Melder es vorher und danach.

SCHUTZ_MERKMALE = ("secret_scanning", "secret_scanning_push_protection")


def plattform_lage() -> dict | None:
    """Besitzer (nach Weiterleitung), Sichtbarkeit und fehlende Schutzmerkmale.

    Liest NUR diese Felder (Whitelist) — die Repo-Antwort ist harmlos, aber die
    Regel gilt fuer jede API-Antwort, die in ein Protokoll laufen kann."""
    out = _gh(
        "api",
        f"repos/{SELBST}",
        "--jq",
        "{full_name, visibility, s: (.security_and_analysis // {})}",
    )
    if not out:
        return None
    try:
        d = json.loads(out)
        return {
            "besitzer": d["full_name"],
            "sichtbarkeit": str(d["visibility"]).upper(),
            "schutz_fehlt": [
                m
                for m in SCHUTZ_MERKMALE
                if (d["s"].get(m) or {}).get("status") != "enabled"
            ],
        }
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def actions_kosten(besitzer: str, heute: date) -> dict | None:
    """Actions-Kosten von platform im laufenden Monat (USD, brutto/netto).

    Konto oder Org je nach Besitzer — die Billing-API trennt beide Pfade. None =
    nicht messbar (fehlender Billing-Scope); das ist vor dem Flip unkritisch,
    danach UNKLAR. Brutto ist, was ein privates Repo ohne Kontingent kostete:
    der Fruehindikator. Netto > 0 heisst, die Minuten werden bezahlt."""
    eigentuemer, name = besitzer.split("/", 1)
    basis = (
        f"organizations/{eigentuemer}"
        if eigentuemer != SELBST.split("/")[0]
        else f"users/{eigentuemer}"
    )
    out = _gh(
        "api",
        f"{basis}/settings/billing/usage?year={heute.year}&month={heute.month}",
        "--jq",
        f'[.usageItems[] | select(.product == "actions" and .repositoryName == "{name}")'
        " | {grossAmount, netAmount}]",
    )
    if out is None:
        return None
    try:
        posten = json.loads(out)
        return {
            "brutto": round(sum(p["grossAmount"] for p in posten), 2),
            "netto": round(sum(p["netAmount"] for p in posten), 2),
        }
    except (ValueError, KeyError, TypeError):
        return None


def wache(lage: dict | None, kosten: dict | None) -> dict:
    """Alarm, wenn der Schutz fehlt oder Minuten bezahlt werden. Nicht messbar
    zaehlt erst nach dem Flip als Luecke — davor ist beides gratis und an."""
    privat = bool(lage) and lage["sichtbarkeit"] != "PUBLIC"
    alarm, luecke = [], []
    if lage is None:
        luecke.append("lage")
    elif lage["schutz_fehlt"]:
        alarm.append("schutz")
    if kosten is None:
        if privat:
            luecke.append("kosten")
    elif kosten["netto"] > 0:
        alarm.append("kosten")
    return {
        "besitzer": lage["besitzer"] if lage else None,
        "schutz_fehlt": lage["schutz_fehlt"] if lage else None,
        "kosten_usd": kosten,
        "alarm": alarm,
        "luecke": luecke,
    }


# ── Messreihe und Prognose ───────────────────────────────────────────────────
#
# Der Melder lief bis 2026-10-04 nur als Momentaufnahme: K5 verlangt sieben Tage
# in Folge, aber nichts hielt die Tage fest — die Serie war unpruefbar. Die
# Messreihe liegt hostlokal (Repo-Namen aus Kunden-Orgs gehoeren nicht in das
# oeffentliche platform-Repo), ein Eintrag je Kalendertag, der letzte Lauf gewinnt.


def rest(zaehler: dict) -> int | None:
    """Summe der Ueberschreitungen ueber Ziel — 0 heisst K5-tauglich."""
    if any(zaehler.get(k) is None for k in ZIEL):
        return None
    return sum(max(0, zaehler[k] - ZIEL[k]) for k in ZIEL)


def lade_reihe(pfad: Path) -> list[dict]:
    if not pfad.is_file():
        return []
    reihe = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        try:
            reihe.append(json.loads(zeile))
        except ValueError:
            continue  # eine kaputte Zeile kostet einen Tag, nicht die Reihe
    return sorted(reihe, key=lambda e: e["datum"])


def eintrag_aus(ergebnis: dict, heute: date) -> dict:
    return {
        "datum": heute.isoformat(),
        "status": ergebnis["status"],
        "sichtbarkeit": ergebnis["sichtbarkeit"],
        "besitzer": ergebnis["wache"]["besitzer"],
        "zaehler": ergebnis["zaehler"],
        "rest": rest(ergebnis["zaehler"]),
        "repos": sorted(set(ergebnis["aufrufer"]) | set(ergebnis["raw"])),
    }


def schreibe_reihe(pfad: Path, reihe: list[dict], eintrag: dict) -> list[dict]:
    neu = [e for e in reihe if e["datum"] != eintrag["datum"]] + [eintrag]
    neu.sort(key=lambda e: e["datum"])
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in neu),
        encoding="utf-8",
    )
    tmp.replace(pfad)
    return neu


def prognose(reihe: list[dict], heute: date) -> dict:
    """Trend, Null-Datum, PASS-Serie (K5) und Rueckfall aus der Messreihe.

    - Null-Datum: lineare Regression des Rests ueber die juengsten
      PROGNOSE_FENSTER_TAGE. Steigt oder stagniert der Rest, gibt es kein Datum —
      eine Prognose, die immer ein Datum nennt, waere Beruhigung, keine Messung.
    - PASS-Serie: PASS-Messungen in Folge vom juengsten Eintrag rueckwaerts; K5
      gilt, wenn sie mindestens K5_TAGE Kalendertage ueberspannt. Luecken ohne
      Messung brechen die Serie nicht (kein Lauf ist kein Rueckfall), eine
      WARN-Messung schon.
    - Rueckfall: Repos im juengsten Eintrag, die im vorigen fehlten."""
    gemessen = [e for e in reihe if e.get("rest") is not None]
    p: dict = {"messungen": len(gemessen), "null_am": None, "steigung_pro_tag": None}
    fenster = [
        e
        for e in gemessen
        if (heute - date.fromisoformat(e["datum"])).days <= PROGNOSE_FENSTER_TAGE
    ]
    if fenster and fenster[-1]["rest"] == 0:
        p["null_am"] = fenster[-1]["datum"]
    elif len(fenster) >= 2:
        xs = [(date.fromisoformat(e["datum"]) - heute).days for e in fenster]
        ys = [e["rest"] for e in fenster]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        nenner = sum((x - mx) ** 2 for x in xs)
        if nenner:
            m = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / nenner
            p["steigung_pro_tag"] = round(m, 3)
            if m < 0:
                tage = int(-ys[-1] / m + 0.999)
                p["null_am"] = date.fromordinal(heute.toordinal() + tage).isoformat()
    serie = []
    for e in reversed(gemessen):
        if e["status"] != "PASS":
            break
        serie.append(e)
    spanne = (
        (date.fromisoformat(serie[0]["datum"]) - date.fromisoformat(serie[-1]["datum"])).days
        + 1
        if serie
        else 0
    )
    p["pass_serie_tage"] = spanne
    p["k5"] = spanne >= K5_TAGE
    p["rueckfall"] = (
        sorted(set(gemessen[-1]["repos"]) - set(gemessen[-2]["repos"]))
        if len(gemessen) >= 2
        else []
    )
    return p


# ── Naechster Zug: der Wiedereinstieg steht in der Ausgabe, nicht in einem Dokument ──

ZUG = {
    "aufrufer": "Aufrufer auf {kanon}@<Tag> umhaengen (Reusable Workflows folgen "
    "keiner Umzugs-Weiterleitung, G2)",
    "raw": "Direkt-Downloads auf ein Release aus {kanon} oder einen lokalen Klon "
    "umstellen",
    "laufzeit": "Laufzeit-Pfade zuerst umstellen — sie treffen beim Umzug laufende "
    "Dienste, nicht nur CI",
    "kopien": "Bausteine `_*.yml` in platform loeschen, sobald Aufrufer = 0 "
    "(Kanon {kanon})",
    "fristen": "review_by erneuern oder Konzept-Status setzen",
    "schutz": "Secret-Scanning/Push-Schutz fehlt: platform gehoert in die Org "
    "{zielorg}, nicht privat ins Privatkonto",
    "kosten": "Actions-Minuten werden bezahlt: Kontingent der Org pruefen oder "
    "Workflows auf self-hosted",
}


def naechster_zug(e: dict) -> list[str]:
    fmt = {"kanon": KANON, "zielorg": ZIELORT.split("/")[0]}
    zuege = [ZUG[k].format(**fmt) for k in e["ueber_ziel"]]
    zuege += [ZUG[k].format(**fmt) for k in e["wache"]["alarm"]]
    if e["status"] == "PASS" and e["sichtbarkeit"] == "PUBLIC":
        p = e.get("prognose") or {}
        zuege.append(
            f"K5 erfuellt: Owner uebertraegt platform nach {ZIELORT} und schaltet "
            "dort privat — nicht waehrend eines Deploys (Deploy-Keys ~1 min gesperrt, G2)"
            if p.get("k5")
            else f"PASS-Serie {p.get('pass_serie_tage', 0)}/{K5_TAGE} Tage abwarten (K5)"
        )
    return zuege


def oeffentlich(e: dict) -> dict:
    """Fassung fuer oeffentliche Texte (platform-Issues, PRs): nur Zahlen.

    Die volle Ausgabe nennt Repos aus Kunden-Orgs und Betraege — in einem Issue
    von platform waere beides veroeffentlicht (Befund D5, 2026-10-04)."""
    p = e.get("prognose") or {}
    return {
        "status": e["status"],
        "sichtbarkeit": e["sichtbarkeit"],
        "zaehler": e["zaehler"],
        "ziel": e["ziel"],
        "wache_alarm": e["wache"]["alarm"],
        "prognose": {k: p.get(k) for k in ("null_am", "pass_serie_tage", "k5")}
        | {"rueckfall": len(p.get("rueckfall") or [])},
    }


# ── Fristen ──────────────────────────────────────────────────────────────────


def abgelaufene_fristen(konzepte_dir: Path, heute: date) -> list[str]:
    """Konzept-IDs mit `review_by` < heute, deren Status noch bindet."""
    faellig = []
    for p in sorted(konzepte_dir.glob("KONZ-*.md")):
        m = FRONTMATTER_RE.match(p.read_text(encoding="utf-8", errors="replace"))
        if not m:
            continue
        fm = m.group(1)
        status = re.search(r"^pipeline_status:\s*([\w-]+)", fm, re.M)
        frist = re.search(r"^review_by:\s*(\d{4}-\d{2}-\d{2})", fm, re.M)
        if not frist or (status and status.group(1) in INAKTIV):
            continue
        if date.fromisoformat(frist.group(1)) < heute:
            cid = re.search(r"^concept_id:\s*(\S+)", fm, re.M)
            faellig.append(cid.group(1) if cid else p.stem)
    return faellig


# ── Bewertung ────────────────────────────────────────────────────────────────


def vereinige(
    *quellen: dict[str, dict[str, list[str]]],
) -> dict[str, dict[str, list[str]]]:
    """Vereinigt je Klasse. Nennt eine Quelle einen Pfad Aufrufer, die andere
    Token-Checkout, gewinnt Aufrufer — die Entwarnung braucht beide Seiten."""
    ges: dict[str, dict[str, list[str]]] = {}
    for q in quellen:
        for repo, e in q.items():
            z = ges.setdefault(repo, {"aufruf": [], "raw": []})
            for k in ("aufruf", "raw", "mit_token"):
                if k in e:
                    z[k] = sorted(set(z.get(k, [])) | set(e[k]))
    for z in ges.values():
        if "mit_token" in z:
            z["mit_token"] = sorted(set(z["mit_token"]) - set(z["aufruf"]))
            if not z["mit_token"]:
                del z["mit_token"]
    return ges


def bewerte(
    konsumenten: dict[str, dict[str, list[str]]],
    kopien: list[str] | None,
    fristen: list[str],
    sichtbar: str | None,
    wache_: dict | None = None,
) -> dict:
    if wache_ is None:
        wache_ = {
            "besitzer": None,
            "schutz_fehlt": None,
            "kosten_usd": None,
            "alarm": [],
            "luecke": [],
        }
    aufrufer = sorted(r for r, e in konsumenten.items() if e["aufruf"])
    raw = sorted(r for r, e in konsumenten.items() if e["raw"])
    laufzeit = {
        r: [
            p
            for p in e["raw"]
            if DEPLOY_BAUSTEIN.search(p) or not NICHT_LAUFZEIT.search(p)
        ]
        for r, e in konsumenten.items()
    }
    laufzeit = {r: p for r, p in laufzeit.items() if p}
    mit_token = {r: e["mit_token"] for r, e in konsumenten.items() if e.get("mit_token")}
    zaehler = {
        "aufrufer": len(aufrufer),
        "raw": len(raw),
        "laufzeit": len(laufzeit),
        "kopien": None if kopien is None else len(kopien),
        "fristen": len(fristen),
    }
    ueber_ziel = [k for k, v in zaehler.items() if v is not None and v > ZIEL[k]]
    messbar = kopien is not None and sichtbar is not None and not wache_["luecke"]
    status = (
        "WARN"
        if ueber_ziel or wache_["alarm"]
        else ("PASS" if messbar else "UNKLAR")
    )
    return {
        "status": status,
        "sichtbarkeit": sichtbar,
        "zaehler": zaehler,
        "ziel": ZIEL,
        "ueber_ziel": ueber_ziel,
        "wache": wache_,
        "aufrufer": aufrufer,
        "raw": raw,
        "laufzeit": laufzeit,
        # Gelistet, nicht gezaehlt: ob das Secret platform lesen darf, zeigt erst
        # ein Lauf nach dem Flip (Flip-Checkliste #3234).
        "mit_token": mit_token,
        "kopien": kopien,
        "fristen": fristen,
    }


def _trend(e: dict) -> str:
    p = e.get("prognose")
    if not p or not p.get("messungen"):
        return ""
    teile = []
    if e["status"] == "PASS":
        teile.append(f"Serie {p['pass_serie_tage']}/{K5_TAGE} Tage")
    elif p.get("null_am"):
        teile.append(f"Prognose 0 am {p['null_am']}")
    elif p.get("steigung_pro_tag") is not None:
        teile.append("kein Abbau-Trend")
    if p.get("rueckfall"):
        teile.append(f"RUECKFALL {len(p['rueckfall'])} neu")
    return f" [{'; '.join(teile)}]" if teile else ""


def kurzzeile(e: dict, oeffentlich_: bool = False) -> str:
    z = e["zaehler"]
    kop = "◌" if z["kopien"] is None else str(z["kopien"])
    sicht = e["sichtbarkeit"] or "◌"
    stand = (
        f"Aufrufer {z['aufrufer']} · Raw {z['raw']} (Laufzeit {z['laufzeit']}) · "
        f"Kopien {kop} · Fristen {z['fristen']}"
    )
    trend = _trend(e)
    alarm = e["wache"]["alarm"]
    if e["status"] == "PASS":
        rolle = (
            "kein Rueckfall"
            if sicht == "PRIVATE"
            else f"Umzug-Freigabe nach {K5_TAGE} Tagen (K5)"
        )
        return f"Sichtbarkeits-Drift: 0/0/1/0 erreicht — platform {sicht}, {rolle}{trend}"
    if e["status"] == "UNKLAR":
        luecke = ", ".join(e["wache"]["luecke"]) or "offline"
        return f"Sichtbarkeits-Drift: {stand} — Teile nicht messbar ({luecke}){trend}"
    wach = f"; Wache: {', '.join(alarm)}" if alarm else ""
    if oeffentlich_:
        return f"Sichtbarkeits-Drift: {stand} — platform {sicht}{wach}{trend}"
    laufzeit = ", ".join(sorted(e["laufzeit"])) or "–"
    return (
        f"Sichtbarkeits-Drift: {stand} — platform {sicht}, Ziel 0/0/1/0 ({AUFTRAG}); "
        f"Laufzeit: {laufzeit}{wach}{trend}"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--kurz", action="store_true", help="eine Zeile fuer den Session-Start"
    )
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument(
        "--offline", action="store_true", help="ohne Netz: nur lokale Klone + Fristen"
    )
    p.add_argument(
        "--github-dir",
        default=os.environ.get("GITHUB_DIR", str(Path.home() / "github")),
    )
    p.add_argument(
        "--konzepte-dir",
        default=str(Path(__file__).resolve().parent.parent / "docs" / "konzepte"),
    )
    p.add_argument("--heute", default=None, help="YYYY-MM-DD (Tests)")
    p.add_argument(
        "--fetch",
        action="store_true",
        help="vor dem Scan `git fetch origin main` je Klon (langsam, fuer den Tageslauf)",
    )
    p.add_argument(
        "--ergebnis-datei",
        default=None,
        help="Ergebnis zusaetzlich in der gemeinsamen Melder-Huelle ablegen "
        "(tools/melder_ergebnis.py) — die Sieben-Tage-Reihe fuer K5 liest von dort.",
    )
    p.add_argument(
        "--messreihe",
        default=None,
        help="hostlokale JSONL-Messreihe (ein Eintrag je Tag) — Grundlage fuer "
        "Prognose, PASS-Serie (K5) und Rueckfall; nie ins Repo legen",
    )
    p.add_argument(
        "--oeffentlich",
        action="store_true",
        help="nur Zahlen, keine Repo-Namen/Betraege — fuer Issues und PRs in platform",
    )
    a = p.parse_args(argv)
    heute = date.fromisoformat(a.heute) if a.heute else date.today()

    lokal = scanne_lokal(Path(a.github_dir), fetch=a.fetch)
    netz = {} if a.offline else scanne_netz()
    kopien = None if a.offline else zaehle_kopien()
    lage = None if a.offline else plattform_lage()
    kosten = actions_kosten(lage["besitzer"], heute) if lage else None
    konsumenten = vereinige(lokal, netz)
    archiviert: list[str] = []
    if not a.offline:
        konsumenten, archiviert = ohne_archivierte(konsumenten)
    ergebnis = bewerte(
        konsumenten,
        kopien,
        abgelaufene_fristen(Path(a.konzepte_dir), heute),
        lage["sichtbarkeit"] if lage else None,
        None if a.offline else wache(lage, kosten),
    )
    if a.messreihe:
        reihe = lade_reihe(Path(a.messreihe))
        # Nur vollstaendige Messungen zaehlen: ein Offline-Lauf mit Rest 0 waere
        # sonst ein PASS-Tag, den niemand gemessen hat, und ein Offline-WARN
        # ueberschriebe die volle Messung desselben Tages.
        if ergebnis["status"] != "UNKLAR" and rest(ergebnis["zaehler"]) is not None:
            reihe = schreibe_reihe(
                Path(a.messreihe), reihe, eintrag_aus(ergebnis, heute)
            )
        ergebnis["prognose"] = prognose(reihe, heute)
    ergebnis["naechster_zug"] = naechster_zug(ergebnis)
    ergebnis["quellen"] = {"lokal": len(lokal), "netz": len(netz)}
    ergebnis["archiviert_ignoriert"] = archiviert
    ergebnis["fetch_alter_tage_max"] = max(FETCH_ALTER.values(), default=None)
    ergebnis["klone_ohne_fetch_7d"] = sorted(
        r for r, t in FETCH_ALTER.items() if t >= 7
    )

    if a.ergebnis_datei:
        melder_ergebnis.schreibe(
            a.ergebnis_datei,
            melder=MELDER,
            ergebnis=ergebnis,
            werkzeug_version=WERKZEUG_VERSION,
        )
    if a.als_json:
        json.dump(
            oeffentlich(ergebnis) if a.oeffentlich else ergebnis,
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        print()
        return 0
    if a.kurz:
        print(kurzzeile(ergebnis, a.oeffentlich))
        return 0

    print(f"# Sichtbarkeits-Drift platform ({ergebnis['sichtbarkeit'] or 'offline'})\n")
    print(kurzzeile(ergebnis, a.oeffentlich) + "\n")
    if ergebnis["naechster_zug"]:
        print("## Naechster Zug")
        for z in ergebnis["naechster_zug"]:
            print(f"- {z}")
        print()
    if a.oeffentlich:
        return 0
    w = ergebnis["wache"]
    if w["besitzer"]:
        k = w["kosten_usd"]
        print("## Wache")
        print(f"- Besitzer: {w['besitzer']}")
        print(f"- Secret-Schutz fehlt: {', '.join(w['schutz_fehlt']) or 'nichts'}")
        print(
            "- Actions-Kosten platform, laufender Monat: "
            + (f"brutto {k['brutto']} USD, netto {k['netto']} USD" if k else "nicht messbar")
        )
        print()
    if ergebnis.get("prognose"):
        print("## Prognose (Messreihe)")
        for schluessel, wert in ergebnis["prognose"].items():
            print(f"- {schluessel}: {wert}")
        print()
    for titel, schluessel in (
        ("Aufrufer (uses:/clone)", "aufrufer"),
        ("Raw-Downloads", "raw"),
        ("Fristen", "fristen"),
    ):
        if ergebnis[schluessel]:
            print(f"## {titel} ({len(ergebnis[schluessel])})")
            for r in ergebnis[schluessel]:
                print(f"- {r}")
            print()
    if ergebnis["laufzeit"]:
        print("## Laufzeit-Pfade (brechen beim Flip in laufenden Diensten)")
        for r, pfade in sorted(ergebnis["laufzeit"].items()):
            print(f"- {r}: {', '.join(pfade)}")
        print()
    if ergebnis["mit_token"]:
        print(
            "## Checkouts mit eigenem Token (zaehlen nicht; nach dem Flip "
            "einmal echt laufen lassen)"
        )
        for r, pfade in sorted(ergebnis["mit_token"].items()):
            print(f"- {r}: {', '.join(pfade)}")
        print()
    if ergebnis["kopien"]:
        print(f"## Kopien der Bausteine ({len(ergebnis['kopien'])}, Kanon {KANON})")
        for r in ergebnis["kopien"]:
            print(f"- {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
