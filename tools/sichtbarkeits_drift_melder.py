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
| laufzeit | davon Treffer in Code ausserhalb CI/Klickdummy/Doku          | 0    |
| kopien   | Repos, die `_*.yml`-Bausteine halten (Kanon: iilgmbh/shared-ci) | 1 |
| fristen  | aktive Konzepte mit abgelaufenem `review_by`                | 0    |

`laufzeit` steht gesondert, weil ein Raw-Treffer in `dev-hub/apps/core/…` beim Flip
eine laufende App trifft, ein Schema-Verweis in einer Klickdummy-Spec nicht — in der
Summe von 26 ginge der eine unter. `fristen` steht hier, weil KONZ-039 selbst am
2026-09-15 stumm verfiel: kein Werkzeug las `review_by`. Ein Umbau, der an Fristen
haengt, braucht den Fristen-Melder im selben Werkzeug.

## Lebenszyklus

Vor dem Flip: WARN, solange ein Zaehler ueber Ziel liegt; PASS bei 0 / 0 / 1 / 0 —
sieben PASS in Folge geben den Flip frei (K5 in KONZ-039). Nach dem Flip dreht sich
die Rolle: jeder neue Treffer ist Rueckfall. Sunset, wenn platform PRIVATE ist und
der Melder 30 Tage nichts meldet — dann ist die Frage beantwortet.

Grenzen: `gh search code` ist eine untere Schranke (Index, 100 Treffer je Abfrage).
`--offline` laesst die Netz-Zaehler als `nicht messbar` stehen, statt sie mit 0 zu
faelschen — ein Melder, der ohne Netz Entwarnung gibt, waere der blinde Melder, gegen
den er gebaut wurde.

    python3 tools/sichtbarkeits_drift_melder.py --kurz
    python3 tools/sichtbarkeits_drift_melder.py --json
    python3 tools/sichtbarkeits_drift_melder.py --offline   # nur lokale Klone + Fristen
"""

from __future__ import annotations

import argparse
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

WERKZEUG_VERSION = "1"
MELDER = "sichtbarkeits_drift_melder"
SELBST = "achimdehnert/platform"
KANON = "iilgmbh/shared-ci"
KOPIEN_KANDIDATEN = (SELBST, "achimdehnert/shared-ci", KANON)
ZIEL = {"aufrufer": 0, "raw": 0, "laufzeit": 0, "kopien": 1, "fristen": 0}
AUFTRAG = "#3234"

# Was beim Flip bricht. `uses:` faengt Reusable Workflows UND Composite Actions
# (`.github/actions/…`) — Letztere waren im Konzept nicht gezaehlt (11 lokale Caller).
AUFRUF_MUSTER = r"uses: *achimdehnert/platform/\.github/"
KLON_MUSTER = r"git clone[^\n]*github\.com[:/]achimdehnert/platform"
# actions/checkout mit `repository: achimdehnert/platform` in fremder CI — die
# Flotten-Workflows receive-windsurf-rules.yml (ADR-263) und silent-failure-lint.yml
# holen platform so; mit GITHUB_TOKEN scheitert das nach dem Flip (23 Klone, 2026-09-16).
CHECKOUT_MUSTER = r"repository: *achimdehnert/platform\b"
RAW_MUSTER = r"raw\.githubusercontent\.com/achimdehnert/platform"
# Raw-Treffer, die NICHT zur Laufzeit brechen: CI (eigene Klasse), Klickdummy-
# Schema-Verweise, Doku.
NICHT_LAUFZEIT = re.compile(r"(^|/)(\.github/|klickdummy/|docs/)|\.md$")
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
        if not repo or repo == SELBST:
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
        aufruf = [
            p
            for p in _grep(d, AUFRUF_MUSTER) + _grep(d, CHECKOUT_MUSTER)
            if p.startswith(".github/")
        ]
        aufruf += _grep(d, KLON_MUSTER)
        raw = _grep(d, RAW_MUSTER)
        if aufruf or raw:
            eintrag = treffer.setdefault(repo, {"aufruf": [], "raw": []})
            eintrag["aufruf"] = sorted(set(eintrag["aufruf"]) | set(aufruf))
            eintrag["raw"] = sorted(set(eintrag["raw"]) | set(raw))
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


def scanne_netz() -> dict[str, dict[str, list[str]]]:
    treffer: dict[str, dict[str, list[str]]] = {}
    for klasse, abfrage in (
        ("aufruf", "uses: achimdehnert/platform/.github"),
        ("aufruf", "repository: achimdehnert/platform"),
        ("raw", "raw.githubusercontent.com/achimdehnert/platform"),
    ):
        for repo, pfad in suche_code(abfrage):
            if repo == SELBST:
                continue
            # Ein `uses:` in Doku (Realfall mcp-hub docs/ADR-160) ist kein Aufrufer.
            if klasse == "aufruf" and not pfad.startswith(".github/"):
                continue
            e = treffer.setdefault(repo, {"aufruf": [], "raw": []})
            if pfad not in e[klasse]:
                e[klasse].append(pfad)
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
    ges: dict[str, dict[str, list[str]]] = {}
    for q in quellen:
        for repo, e in q.items():
            z = ges.setdefault(repo, {"aufruf": [], "raw": []})
            for k in ("aufruf", "raw"):
                z[k] = sorted(set(z[k]) | set(e[k]))
    return ges


def bewerte(
    konsumenten: dict[str, dict[str, list[str]]],
    kopien: list[str] | None,
    fristen: list[str],
    sichtbar: str | None,
) -> dict:
    aufrufer = sorted(r for r, e in konsumenten.items() if e["aufruf"])
    raw = sorted(r for r, e in konsumenten.items() if e["raw"])
    laufzeit = {
        r: [p for p in e["raw"] if not NICHT_LAUFZEIT.search(p)]
        for r, e in konsumenten.items()
    }
    laufzeit = {r: p for r, p in laufzeit.items() if p}
    zaehler = {
        "aufrufer": len(aufrufer),
        "raw": len(raw),
        "laufzeit": len(laufzeit),
        "kopien": None if kopien is None else len(kopien),
        "fristen": len(fristen),
    }
    ueber_ziel = [k for k, v in zaehler.items() if v is not None and v > ZIEL[k]]
    messbar = kopien is not None and sichtbar is not None
    status = "WARN" if ueber_ziel else ("PASS" if messbar else "UNKLAR")
    return {
        "status": status,
        "sichtbarkeit": sichtbar,
        "zaehler": zaehler,
        "ziel": ZIEL,
        "ueber_ziel": ueber_ziel,
        "aufrufer": aufrufer,
        "raw": raw,
        "laufzeit": laufzeit,
        "kopien": kopien,
        "fristen": fristen,
    }


def kurzzeile(e: dict) -> str:
    z = e["zaehler"]
    kop = "◌" if z["kopien"] is None else str(z["kopien"])
    sicht = e["sichtbarkeit"] or "◌"
    stand = (
        f"Aufrufer {z['aufrufer']} · Raw {z['raw']} (Laufzeit {z['laufzeit']}) · "
        f"Kopien {kop} · Fristen {z['fristen']}"
    )
    if e["status"] == "PASS":
        rolle = (
            "kein Rueckfall"
            if sicht == "PRIVATE"
            else "Flip-Freigabe nach 7 Tagen (K5)"
        )
        return f"Sichtbarkeits-Drift: 0/0/1/0 erreicht — platform {sicht}, {rolle}"
    if e["status"] == "UNKLAR":
        return f"Sichtbarkeits-Drift: {stand} — Netz-Zaehler nicht messbar (offline)"
    laufzeit = ", ".join(sorted(e["laufzeit"])) or "–"
    return (
        f"Sichtbarkeits-Drift: {stand} — platform {sicht}, Ziel 0/0/1/0 ({AUFTRAG}); "
        f"Laufzeit: {laufzeit}"
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
    a = p.parse_args(argv)
    heute = date.fromisoformat(a.heute) if a.heute else date.today()

    lokal = scanne_lokal(Path(a.github_dir), fetch=a.fetch)
    netz = {} if a.offline else scanne_netz()
    kopien = None if a.offline else zaehle_kopien()
    sicht = None if a.offline else sichtbarkeit()
    konsumenten = vereinige(lokal, netz)
    archiviert: list[str] = []
    if not a.offline:
        konsumenten, archiviert = ohne_archivierte(konsumenten)
    ergebnis = bewerte(
        konsumenten,
        kopien,
        abgelaufene_fristen(Path(a.konzepte_dir), heute),
        sicht,
    )
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
        json.dump(ergebnis, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    if a.kurz:
        print(kurzzeile(ergebnis))
        return 0

    print(f"# Sichtbarkeits-Drift platform ({ergebnis['sichtbarkeit'] or 'offline'})\n")
    print(kurzzeile(ergebnis) + "\n")
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
    if ergebnis["kopien"]:
        print(f"## Kopien der Bausteine ({len(ergebnis['kopien'])}, Kanon {KANON})")
        for r in ergebnis["kopien"]:
            print(f"- {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
