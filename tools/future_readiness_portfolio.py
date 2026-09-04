#!/usr/bin/env python3
"""future_readiness_portfolio.py — Phase-C-Berichte (Schema 2.3) → Portfolio-Auswertung.

Vierter Baustein neben future_readiness_evidence.py (Paket), future_readiness_score.py
(Bewertung) und future_readiness_render.py (Repo-Bericht): aggregiert die je Repo abgelegten
result.json zu einer Flottensicht, damit die Portfolio-Tabellen nicht von Hand gezaehlt werden.

    python3 tools/future_readiness_portfolio.py RUN_DIR --out portfolio.md [--json portfolio.json]

RUN_DIR ist entweder das Lauf-Verzeichnis (mit Unterordner ``repositories/``) oder direkt der
Ordner mit den Ergebnisdateien. Nur ``*.json`` mit den Pflichtfeldern ``repo`` und ``readiness``
zaehlen. Je Repo genau ein Ergebnis: liegt neben ``<repo>.json`` ein ``<repo>.phase-c.json``,
gewinnt die Phase-C-Datei (deterministischer Bewerter) und die verdraengte Datei wird im Bericht
namentlich ausgewiesen — ebenso Dateien ohne Ergebnisfelder. Nichts wird stillschweigend
verschluckt.

Alle Zahlen stammen aus den Berichten. Fehlt einem Bericht ein Feld, wird das als eigene Zeile
ausgewiesen (Abschnitt „Feldabdeckung") und der Bericht faellt aus genau der Kennzahl heraus,
nicht aus allen.

Anlass: platform#2737 (Phase C, 56 Repos) — die Auswertung soll reproduzierbar sein.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter

BANDS = [
    ("0-24", 0, 24),
    ("25-49", 25, 49),
    ("50-69", 50, 69),
    ("70-84", 70, 84),
    ("85-100", 85, 100),
]

# Felder, deren Abdeckung ueber die Berichte ausgewiesen wird.
TRACKED_FIELDS = [
    "readiness",
    "evidence_coverage",
    "readiness_class",
    "archetype",
    "findings",
    "scores",
    "controls",
    "rubric_version",
    "depth",
    "calculation",
]

SEVERITIES = ["P0", "P1", "P2", "P3"]


def quantil(werte: list[int], p: float) -> float | None:
    """Quantil mit linearer Interpolation (inclusive, wie statistics.quantiles).

    Position = p * (n - 1), 0-basiert auf der aufsteigend sortierten Liste; liegt sie
    zwischen zwei Werten, wird linear interpoliert. Damit ist der Median bei geradem n
    das Mittel der beiden mittleren Werte. Verfahren steht so auch im Bericht.
    """
    if not werte:
        return None
    s = sorted(werte)
    if len(s) == 1:
        return float(s[0])
    pos = p * (len(s) - 1)
    unten = math.floor(pos)
    oben = math.ceil(pos)
    return (
        float(s[unten])
        if unten == oben
        else s[unten] + (pos - unten) * (s[oben] - s[unten])
    )


def zahl(x: float | None) -> str:
    """Ganze Zahlen ohne Nachkomma, interpolierte mit einer Stelle."""
    if x is None:
        return "—"
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def lade(run_dir: str) -> tuple[list[dict], list[str], list[str]]:
    """(Ergebnisse, verdraengte Dateien, uebersprungene Nicht-Ergebnisse).

    Je Repo genau ein Ergebnis. Liegt neben ``<repo>.json`` ein ``<repo>.phase-c.json``,
    gewinnt die Phase-C-Datei (deterministischer Bewerter); die verdraengte Datei ist der
    aeltere Canary-Lauf desselben Repos und wird im Bericht namentlich ausgewiesen.
    """
    basis = os.path.join(run_dir, "repositories")
    if not os.path.isdir(basis):
        basis = run_dir
    kandidaten: dict[str, str] = {}
    verdraengt: list[str] = []
    fremd: list[str] = []
    for name in sorted(os.listdir(basis)):
        if not name.endswith(".json"):
            continue
        if name.endswith(".phase-c.json"):
            stamm = name[: -len(".phase-c.json")]
            alt_name = kandidaten.get(stamm)
            if alt_name and alt_name != name:
                verdraengt.append(alt_name)
            kandidaten[stamm] = name
        else:
            stamm = name[: -len(".json")]
            if stamm in kandidaten:
                verdraengt.append(name)
            else:
                kandidaten[stamm] = name
    ergebnisse: list[dict] = []
    for _stamm, name in sorted(kandidaten.items()):
        try:
            with open(os.path.join(basis, name), encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, json.JSONDecodeError):
            fremd.append(name)
            continue
        if not isinstance(d, dict) or "repo" not in d or "readiness" not in d:
            fremd.append(name)
            continue
        ergebnisse.append(d)
    return ergebnisse, sorted(verdraengt), fremd


def auswerten(ergebnisse: list[dict]) -> dict:
    readiness = [
        d["readiness"] for d in ergebnisse if isinstance(d.get("readiness"), int)
    ]
    baender: dict[str, list[str]] = {b[0]: [] for b in BANDS}
    ohne_band: list[str] = []
    for d in ergebnisse:
        r = d.get("readiness")
        if not isinstance(r, int):
            ohne_band.append(d["repo"])
            continue
        for name, lo, hi in BANDS:
            if lo <= r <= hi:
                baender[name].append(d["repo"])
                break
        else:
            ohne_band.append(d["repo"])

    klassen = Counter(d.get("readiness_class", "(fehlt)") for d in ergebnisse)
    archetypen = Counter(d.get("archetype", "(fehlt)") for d in ergebnisse)

    sev = Counter()
    p1_dim_findings = Counter()
    p1_dim_repos: dict[str, set[str]] = {}
    schluessel_repos: dict[str, set[str]] = {}
    schluessel_findings = Counter()
    ohne_findings: list[str] = []
    p1_repos: set[str] = set()
    findings_gesamt = 0
    for d in ergebnisse:
        fs = d.get("findings")
        if not isinstance(fs, list):
            ohne_findings.append(d["repo"])
            continue
        findings_gesamt += len(fs)
        for f in fs:
            s = f.get("severity", "(fehlt)")
            sev[s] += 1
            dim = f.get("dimension") or (f.get("question_id") or "")[:3] or "(fehlt)"
            if s == "P1":
                p1_repos.add(d["repo"])
                p1_dim_findings[dim] += 1
                p1_dim_repos.setdefault(dim, set()).add(d["repo"])
            key = f"{f.get('question_id', '?')}|{f.get('finding_type', '?')}"
            schluessel_findings[key] += 1
            schluessel_repos.setdefault(key, set()).add(d["repo"])

    feldabdeckung = {
        feld: sum(1 for d in ergebnisse if d.get(feld) is not None)
        for feld in TRACKED_FIELDS
    }

    return {
        "repos": len(ergebnisse),
        "readiness_n": len(readiness),
        "readiness_ohne_feld": len(ergebnisse) - len(readiness),
        "readiness": {
            "min": min(readiness) if readiness else None,
            "q1": quantil(readiness, 0.25),
            "median": quantil(readiness, 0.5),
            "q3": quantil(readiness, 0.75),
            "max": max(readiness) if readiness else None,
        },
        "baender": baender,
        "ohne_band": sorted(ohne_band),
        "klassen": dict(klassen.most_common()),
        "archetypen": dict(archetypen.most_common()),
        "findings_gesamt": findings_gesamt,
        "findings_ohne_feld": sorted(ohne_findings),
        "severity": {s: sev.get(s, 0) for s in SEVERITIES if sev.get(s)},
        "p1_repos": len(p1_repos),
        "p1_nach_dimension": [
            {
                "dimension": dim,
                "findings": n,
                "repos": len(p1_dim_repos.get(dim, ())),
            }
            for dim, n in sorted(
                p1_dim_findings.items(), key=lambda kv: (-kv[1], kv[0])
            )[:10]
        ],
        "top_schluessel": [
            {
                "schluessel": k,
                "findings": schluessel_findings[k],
                "repos": len(schluessel_repos[k]),
            }
            for k in sorted(
                schluessel_findings,
                key=lambda k: (-len(schluessel_repos[k]), -schluessel_findings[k], k),
            )[:5]
        ],
        "feldabdeckung": feldabdeckung,
    }


def _tab(kopf: list[str], zeilen: list[list[object]]) -> list[str]:
    out = ["| " + " | ".join(kopf) + " |", "|" + "---|" * len(kopf)]
    out += ["| " + " | ".join(str(z) for z in zeile) + " |" for zeile in zeilen]
    out.append("")
    return out


def markdown(
    a: dict,
    run_dir: str,
    varianten: list[str],
    fremd: list[str],
    hinweise: list[str] | None = None,
) -> str:
    r = a["readiness"]
    z = [
        "# Future-Readiness Phase C — Portfolio-Auswertung (2026-09-04)",
        "",
        f"Quelle: `tools/future_readiness_portfolio.py {run_dir}` über die je Repo abgelegten "
        "Ergebnisdateien des Phase-C-Laufs (dev-hub, privat). Auftrag "
        "[platform#2737](https://github.com/achimdehnert/platform/issues/2737).",
        "",
        "Diese Datei enthält nur Aggregate, Repo-Namen und Readiness-Bänder — keine "
        "Personendaten, keine Secrets, keine Einstellungswerte einzelner privater Repos "
        "(platform ist öffentlich; Regel 11* der Regelbilanz).",
        "",
        "## Grundmenge",
        "",
    ]
    z += _tab(
        ["Kennzahl", "Wert"],
        [
            ["Ergebnisdateien gewertet", a["repos"]],
            ["ältere Läufe desselben Repos verdrängt", len(varianten)],
            ["Nicht-Ergebnisse übersprungen", len(fremd)],
            ["davon mit Feld `readiness`", a["readiness_n"]],
            ["ohne Feld `readiness`", a["readiness_ohne_feld"]],
        ],
    )
    z += ["## Verteilung Readiness", ""]
    z += _tab(
        ["Kennzahl", "Wert"],
        [
            ["Minimum", zahl(r["min"])],
            ["Q1 (25 %)", zahl(r["q1"])],
            ["Median", zahl(r["median"])],
            ["Q3 (75 %)", zahl(r["q3"])],
            ["Maximum", zahl(r["max"])],
        ],
    )
    z += [
        "Quantile mit linearer Interpolation (Position = p·(n−1) auf der sortierten Liste, "
        'wie `statistics.quantiles(..., method="inclusive")`); bei geradem n ist der Median '
        "das Mittel der beiden mittleren Werte.",
        "",
        "## Repos nach Readiness-Band",
        "",
    ]
    z += _tab(
        ["Band", "Repos", "Namen"],
        [
            [
                name,
                len(a["baender"][name]),
                ", ".join(sorted(a["baender"][name])) or "—",
            ]
            for name, _, _ in BANDS
        ],
    )
    if a["ohne_band"]:
        z += [f"Ohne Band (Feld fehlt): {', '.join(a['ohne_band'])}", ""]
    z += ["## Klassen und Archetypen", ""]
    z += _tab(["readiness_class", "Repos"], [[k, v] for k, v in a["klassen"].items()])
    z += _tab(["Archetyp", "Repos"], [[k, v] for k, v in a["archetypen"].items()])
    z += ["## Findings", ""]
    z += _tab(
        ["Kennzahl", "Wert"],
        [["Findings gesamt", a["findings_gesamt"]]]
        + [[f"davon {s}", n] for s, n in a["severity"].items()]
        + [["Repos mit mindestens einem P1", a["p1_repos"]]],
    )
    if a["findings_ohne_feld"]:
        z += [
            f"Ohne Feld `findings`: {', '.join(a['findings_ohne_feld'])}",
            "",
        ]
    z += ["### P1-Findings nach Dimension (Top 10)", ""]
    z += _tab(
        ["#", "Dimension", "P1-Findings", "Repos"],
        [
            [i, e["dimension"], e["findings"], e["repos"]]
            for i, e in enumerate(a["p1_nach_dimension"], 1)
        ]
        or [["—", "keine P1-Findings", 0, 0]],
    )
    z += [
        "### Häufigste Finding-Schlüssel (Top 5)",
        "",
        "Schlüssel normalisiert als `question_id` + `finding_type` (im `locator` mit `|` "
        "getrennt, in der Tabelle wegen der Pipe als `·`) — der repo-unabhängige Teil "
        "des `locator`; der volle `key` trägt zusätzlich Org/Repo und den Locator-Hash und "
        "ist damit je Repo einmalig.",
        "",
    ]
    z += _tab(
        ["#", "Schlüssel", "Repos", "Findings"],
        [
            [i, e["schluessel"].replace("|", " · "), e["repos"], e["findings"]]
            for i, e in enumerate(a["top_schluessel"], 1)
        ]
        or [["—", "keine Findings", 0, 0]],
    )
    z += ["## Feldabdeckung über die Berichte", ""]
    z += _tab(
        ["Feld", "Berichte mit Feld", "ohne Feld"],
        [
            [feld, a["feldabdeckung"][feld], a["repos"] - a["feldabdeckung"][feld]]
            for feld in TRACKED_FIELDS
        ],
    )
    if varianten:
        z += [
            "## Verdrängte Dateien",
            "",
            "Von einer `*.phase-c.json` desselben Repos verdrängt (älterer Canary-Lauf): "
            + ", ".join(varianten),
            "",
        ]
    if fremd:
        z += ["Nicht-Ergebnisse: " + ", ".join(fremd), ""]
    if hinweise:
        z += ["## Anmerkungen", ""] + [f"- {h}" for h in hinweise] + [""]
    return "\n".join(z) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("run_dir", help="Lauf-Verzeichnis oder Ordner mit den result.json")
    ap.add_argument("--out", help="Markdown-Ziel (Default: stdout)")
    ap.add_argument("--json", dest="json_out", help="Aggregat zusaetzlich als JSON")
    ap.add_argument(
        "--hinweis",
        action="append",
        default=[],
        help="Anmerkung unter den Tabellen (mehrfach moeglich)",
    )
    ap.add_argument(
        "--quelle",
        help="Quellenangabe im Bericht (Default: run_dir) — fuer Ablagen, deren "
        "lokaler Pfad nicht in den Bericht gehoert",
    )
    a = ap.parse_args()
    ergebnisse, varianten, fremd = lade(a.run_dir)
    if not ergebnisse:
        print(f"keine Ergebnisdateien in {a.run_dir}")
        return 1
    agg = auswerten(ergebnisse)
    md = markdown(agg, a.quelle or a.run_dir, varianten, fremd, a.hinweis)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"{agg['repos']} Berichte -> {a.out}")
    else:
        print(md, end="")
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as fh:
            json.dump(
                agg, fh, ensure_ascii=False, indent=1, sort_keys=True, default=list
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
