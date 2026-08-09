#!/usr/bin/env python3
"""retro-kpis.py — Längsschnitt-Hebel für /session-retro (ADR-light, kein Dep).

Liest die YAML-Frontmatter aller `session-retro-*.md` (außer den
`-extern-`-Briefings) aus `<repo>/docs/retros/` (git-durable, KONZ-platform-010)
UND `~/shared/` (Skill-Schreibpfad) — dedupliziert nach Dateiname —, zählt
`recurring_findings`-Slugs ÜBER Retros hinweg und
eskaliert jeden Slug mit **Zähler ≥2 → GATE-PFLICHT**. Trendet zusätzlich
`refuted_rate` gegen das Skill-KPI-Band (>0.8 Finder zu lasch · <0.2 Falsifikation
Theater) und die 6 Score-Dimensionen.

Bewusst stdlib-only (Frontmatter-Mini-Parser statt PyYAML) — das Tool muss in
jeder session-retro-Phase-4 ohne Setup laufen.

Aufruf:
    python3 tools/retro_kpis.py                 # Default: docs/retros/ + ~/shared/
    python3 tools/retro_kpis.py --dir <pfad>    # nur dies(e) Verzeichnis(se), mehrfach angebbar
    python3 tools/retro_kpis.py --min-band 3    # refuted_rate-Band erst ab N Retros werten
    python3 tools/retro_kpis.py --file-issues   # GATE-PFLICHT-Slugs (>=2) als GH-Issue anlegen/aktualisieren
    python3 tools/retro_kpis.py --since 2026-09-03 --until 2026-09-16 --k1
                                                # K1-Ausgang gegen die eingefrorene Baseline

--k1 (KONZ-038 D6): rechnet den vorregistrierten K1-Ausgang statt ihn von Hand zu
behaupten. Liest `docs/governance/k1-baseline/slug-woerterbuch.yaml`, vergleicht den
eigenen sha256 gegen den dort eingefrorenen Pin (Abweichung = Instrumentenwechsel ⇒
Ausgang "nicht bewertbar", Baseline neu berechnen), mappt Aliase auf die kanonischen
Baseline-Slugs und weist Slugs AUSSERHALB des Wörterbuchs getrennt als "nicht
bewertbar" aus — nie als "neu bei null" (Goodhart-Schutz EXT2-AD-2).

--file-issues (Retro d80d23/2026-07-16 — "Verankerung entscheidet der Mensch" landete
bisher nur als Prosa im Report; niemand kam zuverlässig zurück, um sie in ein
durables Artefakt zu überführen — `handover-stale-vor-merge` blieb laut
`d2522c-incr` "ohne systemisches Gate", obwohl schon ×4 GATE-PFLICHT):
für jeden Slug mit Zähler ≥2 wird per `gh issue list --search` geprüft, ob bereits
ein Issue mit Titel "Gate: <slug>" existiert (offen ODER geschlossen — ein
geschlossenes Gate-Issue heißt "schon gebaut", nicht "bitte neu anlegen"). Fehlt
es, wird es per `gh issue create` angelegt (Body = Vorkommen-Liste + Retro-Links).
Fail-open wie der Rest des Tools: kein `gh`/kein Repo-Zugriff → Hinweis, Exit 0.

Exit-Code 0 immer (Report-Tool, kein Gate-Enforcer — das Gate ist der gemeldete
GATE-PFLICHT-Block, den der Mensch — oder mit --file-issues das Tool selbst als
durables Issue — in einen PR überführt).
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
from collections import Counter, defaultdict

# `repo_scope` steht hier BEWUSST NICHT (platform#1840, Owner-Entscheid B): das Feld
# wurde geparst und formgeprüft, aber von keinem Konsumenten gelesen — der Schlüssel
# kam in ganz platform nur in dieser Menge und in einer Test-Fixture vor. Die Warnung
# "nicht slug-förmig — NICHT gezählt" war damit trivial wahr und verlangte trotzdem
# Edits an historischen Reports (Trockenlauf 2026-08-08, drei Reports). Ein Prüfer, der
# Arbeit auslöst ohne zu messen, wird zurückgebaut, nicht kalibriert. Das Feld bleibt
# als menschenlesbare Doku im Frontmatter — es hat nur keinen Wächter mehr.
LIST_KEYS = {"recurring_findings", "gate_candidates"}
# D6-Härtung (KONZ-038, EXT2-AD-2/M-1): Listeneinträge müssen slug-förmig sein.
# Realfall a50bc6: ein Inline-Kommentar HINTER der Liste wurde mitgesplittet und
# erzeugte 3 Phantom-Slugs im Zähler — strip("[]") erwischt nur String-Enden.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,}$")
KNOWN_SCHEMAS = {"", "1"}  # fehlend (Altbestand) oder retro_schema: 1
SCALAR_KEYS = {
    "date",
    "session_id",
    "footprint",
    "refuted_rate",
    "findings_total",
    "findings_survived",
    "phase3_refuted",
    "pre_refuted",
}
SCORE_KEYS = [
    "zielerreichung",
    "architektur_design",
    "code_konventionstreue",
    "risiko_debt",
    "prozess_effizienz",
    "entscheidungsqualitaet",
]


def parse_frontmatter(text: str) -> dict | None:
    """Minimaler Frontmatter-Parser: erstes ---...----Block, flache keys + scores-Block."""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    body = m.group(1)
    out: dict = {"scores": {}}
    in_scores = False
    for raw in body.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw[0] in " \t"
        line = raw.strip()
        if line.rstrip(":") == "scores" and line.endswith(":"):
            in_scores = True
            continue
        if in_scores and indented and ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k in SCORE_KEYS:
                try:
                    out["scores"][k] = int(v)
                except ValueError:
                    pass
            continue
        in_scores = False
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k in LIST_KEYS:
            # Nur den Klammer-Inhalt nehmen — Inline-Kommentare nach "]" bleiben draußen.
            m_list = re.search(r"\[(.*?)\]", v)
            inner = m_list.group(1) if m_list else v.split("#", 1)[0].strip("[]")
            items = [s.strip().strip("'\"") for s in inner.split(",") if s.strip()]
            good = [it for it in items if SLUG_RE.match(it)]
            bad = [it for it in items if not SLUG_RE.match(it)]
            out[k] = good
            if bad:
                out.setdefault("_parse_warnings", []).extend(
                    f"{k}: {b!r} (nicht slug-förmig — NICHT gezählt)" for b in bad
                )
        elif k == "retro_schema":
            out["retro_schema"] = v.strip("'\"")
        elif k in SCALAR_KEYS:
            out[k] = v.strip("'\"")
    return out


def load_reports(directories) -> list[dict]:
    """Load retro frontmatter from one or more directories.

    Accepts a single dir (str) or a list of dirs. Reports are deduplicated by
    filename across dirs (first dir wins) so the git-durable ``docs/retros/``
    home (KONZ-platform-010) and the skill's ``~/shared/`` write path can both
    be scanned without double-counting a report that lives in both.
    """
    if isinstance(directories, str):
        directories = [directories]
    reports = []
    seen: set[str] = set()
    for directory in directories:
        pattern = os.path.join(directory, "session-retro-*.md")
        for path in sorted(glob.glob(pattern)):
            base = os.path.basename(path)
            if "-extern-" in base:
                continue  # Phase-6-Briefings sind keine Retros
            if base in seen:
                continue  # gleicher Report in beiden Dirs → nur einmal zählen
            try:
                fm = parse_frontmatter(open(path, encoding="utf-8").read())
            except OSError:
                continue
            if fm is None:
                continue
            fm["_path"] = base
            seen.add(base)
            reports.append(fm)
    return reports


def _gate_issue_title(slug: str) -> str:
    return f"Gate: {slug}"


def _existing_gate_issue(repo: str, slug: str) -> dict | None:
    """Search repo for an existing (open OR closed) 'Gate: <slug>' issue. None if gh/repo unavailable."""
    title = _gate_issue_title(slug)
    try:
        out = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                repo,
                "--state",
                "all",
                "--search",
                f'"{title}" in:title',
                "--json",
                "number,title,state,url",
                "--limit",
                "10",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        candidates = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return None
    for c in candidates:
        if c.get("title") == title:
            return c
    return None


def _create_gate_issue(
    repo: str, slug: str, sessions: list[str], reports_by_path: dict
) -> str | None:
    """Create a 'Gate: <slug>' issue. Returns the new issue URL, or None on failure."""
    title = _gate_issue_title(slug)
    lines = [
        f"`{slug}` ist über `tools/retro_kpis.py` mit Zähler **×{len(sessions)}** als "
        "GATE-PFLICHT eskaliert (Schwelle: ≥2 Vorkommen über Session-Retros).",
        "",
        "Bisheriges Muster: dieselbe Erkenntnis wird Retro für Retro neu entdeckt, "
        "bleibt aber Prosa im Report statt in ein durables Gate (Hook/CI/Skill-Edit) "
        "überführt zu werden. Dieses Issue ist genau dafür — es bleibt offen, bis ein "
        "echtes Gate existiert, nicht bis der nächste Report es erwähnt.",
        "",
        "**Vorkommen:**",
    ]
    for sid in sessions:
        path = reports_by_path.get(sid)
        if path:
            lines.append(
                f"- `{sid}` — [{path}](https://github.com/{repo}/blob/main/docs/retros/{path})"
            )
        else:
            lines.append(f"- `{sid}`")
    lines += ["", "_Automatisch angelegt von `tools/retro_kpis.py --file-issues`._"]
    body = "\n".join(lines)
    try:
        out = subprocess.run(
            ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip().splitlines()[-1] if out.stdout.strip() else None


def file_gate_issues(gated: dict, reports: list[dict], repo: str) -> None:
    """For each GATE-PFLICHT slug, ensure a durable tracking issue exists (create if missing)."""
    reports_by_session = {r.get("session_id", r["_path"]): r["_path"] for r in reports}
    print(f"\n## --file-issues (Repo: {repo})")
    try:
        who = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        who = None
    if who is None or who.returncode != 0:
        print("  (gh nicht verfügbar/nicht eingeloggt — übersprungen, fail-open)")
        return
    for slug, sessions in sorted(gated.items()):
        existing = _existing_gate_issue(repo, slug)
        if existing is not None:
            print(
                f"  · {slug}: bereits vorhanden — {existing['state']} {existing['url']}"
            )
            continue
        url = _create_gate_issue(repo, slug, sessions, reports_by_session)
        if url:
            print(f"  ✓ {slug}: neu angelegt — {url}")
        else:
            print(
                f"  ✗ {slug}: Issue-Erstellung fehlgeschlagen (fail-open, kein Retry)"
            )


# --- K1-Auswertung gegen die eingefrorene Baseline (KONZ-038 D6) ----------------
# Bis hierher war das Slug-Wörterbuch ein Dokument OHNE Konsument: die Regel
# "unmappbare neue Slugs = nicht bewertbar, NIE neu bei null" (EXT2-AD-2) und die
# Pflicht "Instrumentenwechsel ⇒ Baseline-Neuberechnung" (EXT2-AD-3) standen nur
# als Prosa im YAML-Kopf. Beides rechnet jetzt das Tool — sonst entscheidet den
# K1-Ausgang am 2026-09-16 eine Handzählung gegen ein Wörterbuch, das nichts liest.

K1_WOERTERBUCH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "governance",
    "k1-baseline",
    "slug-woerterbuch.yaml",
)


def tool_sha256(path: str | None = None) -> str:
    """sha256 des Zählwerks selbst — der Pin, gegen den die Baseline eingefroren ist."""
    with open(path or os.path.abspath(__file__), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_woerterbuch(path: str) -> dict | None:
    """Mini-Parser für slug-woerterbuch.yaml (stdlib-only wie der Rest des Tools).

    Liest genau die eingefrorene Struktur: flache Skalare, den ``top3:``-Block
    (``- canonical:`` + ``aliases: [...]``) und den ``schwellen:``-Block. Fehlt
    eine Pflichtangabe, wird None geliefert — die Auswertung sagt dann "nicht
    bewertbar" statt gegen halbe Daten zu rechnen.
    """
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return None
    out: dict = {"top3": [], "schwellen": {}}
    section = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if not line[0].isspace() and stripped.endswith(":") and ":" in stripped:
            section = stripped[:-1]
            continue
        if section == "top3" and stripped.startswith("- canonical:"):
            out["top3"].append(
                {
                    "canonical": stripped.split(":", 1)[1].strip().strip("'\""),
                    "aliases": [],
                }
            )
            continue
        if section == "top3" and stripped.startswith("aliases:") and out["top3"]:
            m = re.search(r"\[(.*?)\]", stripped)
            inner = m.group(1) if m else ""
            out["top3"][-1]["aliases"] = [
                s.strip().strip("'\"") for s in inner.split(",") if s.strip()
            ]
            continue
        if section == "schwellen" and ":" in stripped:
            k, v = stripped.split(":", 1)
            try:
                out["schwellen"][k.strip()] = float(v.strip())
            except ValueError:
                pass
            continue
        if not line[0].isspace() and ":" in stripped:
            section = None
            k, v = stripped.split(":", 1)
            out[k.strip()] = v.strip().strip("'\"")
    if not out["top3"] or "tool_sha256" not in out:
        return None
    return out


def k1_auswertung(reports: list[dict], wb: dict, ist_sha: str) -> list[str]:
    """Rechnet den K1-Ausgang gegen die vorregistrierten Schwellen.

    Drei Wege in "nicht bewertbar", alle laut: Instrumentenwechsel (sha-Mismatch),
    zu wenige Retros im Fenster, oder ein leeres Fenster. Unmappbare Slugs werden
    getrennt ausgewiesen und gehen NIE in die Rate ein.
    """
    lines = ["\n## K1-Auswertung (KONZ-038 §13, eingefrorene Baseline)"]
    lines.append(f"  Wörterbuch: {os.path.relpath(K1_WOERTERBUCH, os.getcwd())}")

    instrument_ok = ist_sha == wb.get("tool_sha256")
    if instrument_ok:
        lines.append(
            f"  Instrument: sha256 {ist_sha[:16]}… ✅ identisch mit Baseline-Pin"
        )
    else:
        lines.append(
            f"  Instrument: sha256 {ist_sha[:16]}… ⚠️ INSTRUMENTENWECHSEL — "
            f"Pin ist {str(wb.get('tool_sha256'))[:16]}…"
        )
        lines.append(
            "    → Baseline mit dieser Tool-Version NEU berechnen und den Pin "
            "nachziehen (KONZ-038 D6/EXT2-AD-3). Bis dahin ist der Ausgang nicht bewertbar."
        )

    alias_map: dict[str, str] = {}
    for eintrag in wb["top3"]:
        kanon = eintrag["canonical"]
        alias_map[kanon] = kanon
        for alias in eintrag.get("aliases", []):
            alias_map[alias] = kanon

    treffer: Counter = Counter()
    unmappbar: Counter = Counter()
    for r in reports:
        for slug in r.get("recurring_findings", []):
            kanon = alias_map.get(slug)
            if kanon:
                treffer[kanon] += 1
            else:
                unmappbar[slug] += 1

    n = len(reports)
    min_retros = int(wb["schwellen"].get("min_retros", 8))
    lines.append(
        f"  Retros im Fenster: {n} (Input-Bedingung ≥{min_retros}: "
        f"{'erfüllt' if n >= min_retros else 'NICHT erfüllt'})"
    )
    lines.append("")
    summe = 0
    for eintrag in wb["top3"]:
        kanon = eintrag["canonical"]
        cnt = treffer[kanon]
        summe += cnt
        rate = cnt / n if n else 0.0
        lines.append(f"    {kanon:38} ×{cnt:<3} Rate {rate:.3f}")
    summen_rate = summe / n if n else 0.0
    lines.append(f"    {'Summe Top-3':38} ×{summe:<3} Rate {summen_rate:.3f}")

    if unmappbar:
        lines.append("")
        lines.append(
            f"  Nicht bewertbar — {len(unmappbar)} Slug(s) außerhalb des Wörterbuchs "
            "(zählen NICHT als „neu bei null“, EXT2-AD-2):"
        )
        for slug, cnt in sorted(unmappbar.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"    · {slug} ×{cnt}")
        lines.append(
            "    → Semantisch deckungsgleiche Slugs VOR der Auswertung als Alias "
            "ins Wörterbuch mappen (per PR, mit Begründung)."
        )

    wirksam_max = wb["schwellen"].get("wirksam_max", 0.700)
    kill_ueber = wb["schwellen"].get("kill_ueber", 1.000)
    if not instrument_ok:
        ausgang = "nicht bewertbar (Instrumentenwechsel — Baseline neu berechnen)"
    elif n < min_retros:
        ausgang = f"nicht bewertbar (nur {n} Retros im Fenster, Schwelle {min_retros})"
    elif summen_rate <= wirksam_max:
        ausgang = f"wirksam (Rate {summen_rate:.3f} ≤ {wirksam_max:.3f})"
    elif summen_rate > kill_ueber:
        ausgang = f"Kill (Rate {summen_rate:.3f} > {kill_ueber:.3f})"
    else:
        ausgang = (
            f"unentschieden ({wirksam_max:.3f} < Rate {summen_rate:.3f} "
            f"≤ {kill_ueber:.3f})"
        )
    lines.append(f"\n  → Ausgang: {ausgang}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Längsschnitt-KPIs über session-retro-Reports"
    )
    # KONZ-platform-010: durable Heimat = git docs/retros/ (nicht ~/shared, ungebackupt).
    # Default liest BEIDE — docs/retros/ (git-durable, KONZ-010) UND ~/shared/ (der Pfad,
    # nach dem die /session-retro-Skill schreibt) — dedupliziert nach Dateiname, damit ein
    # frisch nach ~/shared geschriebener Report nicht durch die Pfad-Drift unsichtbar bleibt.
    _repo_retros = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "retros"
    )
    _shared = os.path.expanduser("~/shared")
    ap.add_argument(
        "--dir",
        action="append",
        default=None,
        help="Verzeichnis(se) mit session-retro-*.md; mehrfach angebbar. "
        "Default: <repo>/docs/retros (KONZ-010) + ~/shared (Skill-Schreibpfad).",
    )
    ap.add_argument(
        "--since",
        default=None,
        help="YYYY-MM-DD inklusiv — filtert nach Dateinamens-Datum "
        "(Fallback: date-Frontmatter). Für K1-Fenster-Auswertungen (KONZ-038).",
    )
    ap.add_argument(
        "--until",
        default=None,
        help="YYYY-MM-DD inklusiv — Gegenstück zu --since.",
    )
    ap.add_argument(
        "--min-band",
        type=int,
        default=3,
        help="refuted_rate-Band erst ab N Retros bewerten (default 3)",
    )
    ap.add_argument(
        "--k1",
        action="store_true",
        help="K1-Ausgang gegen die eingefrorene Baseline rechnen (Slug-Wörterbuch, "
        "Instrument-Pin, vorregistrierte Schwellen — KONZ-038 D6).",
    )
    ap.add_argument(
        "--k1-woerterbuch",
        default=K1_WOERTERBUCH,
        help=f"Pfad zum Slug-Wörterbuch (default: {K1_WOERTERBUCH})",
    )
    ap.add_argument(
        "--file-issues",
        action="store_true",
        help="GATE-PFLICHT-Slugs (Zaehler >=2) als 'Gate: <slug>'-Issue in "
        "--issues-repo anlegen, falls noch keins existiert (offen oder "
        "geschlossen). Fail-open ohne gh/Login.",
    )
    ap.add_argument(
        "--issues-repo",
        default="achimdehnert/platform",
        help="Ziel-Repo fuer --file-issues (default: achimdehnert/platform)",
    )
    args = ap.parse_args()

    dirs = args.dir if args.dir else [_repo_retros, _shared]
    reports = load_reports(dirs)

    # D6: Fenster-Filter (Dateinamens-Datum, Fallback Frontmatter-date; ISO-Stringvergleich)
    def _rdate(r: dict) -> str:
        m = re.search(r"session-retro-(\d{4}-\d{2}-\d{2})", r["_path"])
        return m.group(1) if m else str(r.get("date", ""))

    if args.since:
        reports = [r for r in reports if _rdate(r) >= args.since]
    if args.until:
        reports = [r for r in reports if _rdate(r) <= args.until]

    # D6/M-1: unbekannte Schema-Version wird NICHT still mitgezählt — laut
    # ausschließen statt leise Phantomdaten liefern (Exit bleibt 0, Report-Tool).
    schema_bad = [
        r for r in reports if str(r.get("retro_schema", "")) not in KNOWN_SCHEMAS
    ]
    reports = [r for r in reports if str(r.get("retro_schema", "")) in KNOWN_SCHEMAS]

    if not reports:
        print(f"Keine (zählbaren) session-retro-Reports in {', '.join(dirs)} gefunden.")
        for r in schema_bad:
            print(f"  ⚠ ausgeschlossen (retro_schema unbekannt): {r['_path']}")
        return 0

    window = ""
    if args.since or args.until:
        window = f" · Fenster {args.since or '…'}..{args.until or '…'}"
    print(
        f"# Längsschnitt über {len(reports)} Retro-Reports ({', '.join(dirs)}){window}\n"
    )

    parse_warn = [
        (r["_path"], w) for r in reports for w in r.get("_parse_warnings", [])
    ]
    if parse_warn or schema_bad:
        print("## ⚠ Parse-Warnungen (NICHT gezählt — Quelldatei fixen)")
        for path, w in parse_warn:
            print(f"  {path}: {w}")
        for r in schema_bad:
            print(
                f"  {r['_path']}: retro_schema={r.get('retro_schema')!r} unbekannt — Report ausgeschlossen"
            )
        print()

    # --- Recurring-Findings-Zähler über Retros → Gate-Eskalation ---
    slug_reports: dict[str, list[str]] = defaultdict(list)
    for r in reports:
        for slug in r.get("recurring_findings", []):
            slug_reports[slug].append(r.get("session_id", r["_path"]))
    gated = {s: v for s, v in slug_reports.items() if len(v) >= 2}

    print("## recurring_findings (Zähler über Retros)")
    if not slug_reports:
        print("(keine recurring_findings deklariert)")
    for slug, where in sorted(slug_reports.items(), key=lambda kv: -len(kv[1])):
        mark = "🚨 GATE-PFLICHT" if len(where) >= 2 else "·"
        print(f"  {mark}  {slug}  ×{len(where)}  [{', '.join(where)}]")
    if gated:
        print(
            f"\n→ {len(gated)} Slug(s) ≥2 ⇒ Gate-PR-Pflicht: "
            f"{', '.join(sorted(gated))}. Als Gate (Hook/CI/Skill) verankern, "
            f"nicht als N-tes Memo."
        )

    # --- refuted_rate-Band ---
    rates = []
    for r in reports:
        try:
            rates.append((r.get("session_id", r["_path"]), float(r["refuted_rate"])))
        except (KeyError, ValueError):
            pass
    print("\n## refuted_rate-Trend (Skill-KPI)")
    if rates:
        print("  " + " · ".join(f"{sid}:{val:.2f}" for sid, val in rates[-8:]))
        n = len(rates)
        if n >= args.min_band:
            recent = [v for _, v in rates[-args.min_band :]]
            if all(v > 0.8 for v in recent):
                print(
                    f"  ⚠️  letzte {args.min_band} >0.8 → Finder zu lasch (widerlegbares Stroh)."
                )
            elif all(v < 0.2 for v in recent):
                print(
                    f"  ⚠️  letzte {args.min_band} <0.2 → Falsifikation ist Theater (widerlegt nie)."
                )
            else:
                print(f"  ✅ Band gesund (weder {args.min_band}× >0.8 noch <0.2).")
        else:
            print(f"  (erst ab {args.min_band} Retros als Band gewertet — bisher {n})")
    else:
        print("  (keine refuted_rate-Werte parsebar)")

    # --- Score-Mittel je Dimension ---
    print("\n## Score-Mittel je Dimension (1–5)")
    sums: Counter = Counter()
    cnts: Counter = Counter()
    for r in reports:
        for k, v in r.get("scores", {}).items():
            sums[k] += v
            cnts[k] += 1
    for k in SCORE_KEYS:
        if cnts[k]:
            print(f"  {k:24} {sums[k] / cnts[k]:.2f}  (n={cnts[k]})")

    if args.k1:
        wb = load_woerterbuch(args.k1_woerterbuch)
        if wb is None:
            print(
                f"\n## K1-Auswertung\n  ⚠️ Wörterbuch nicht lesbar/unvollständig: "
                f"{args.k1_woerterbuch}\n  → nicht bewertbar (nie als ok werten)."
            )
        else:
            print("\n".join(k1_auswertung(reports, wb, tool_sha256())))

    if args.file_issues:
        file_gate_issues(gated, reports, args.issues_repo)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
