#!/usr/bin/env python3
"""platform#2374 Ziel A — Wirksamkeits-Bilanz der Gates, unabhaengig nachgerechnet.

Drei Teile, vorab festgelegt (Issue-Text vom 2026-08-27, Owner-Kommentar zum Tier-Zuschnitt):

1. RUECKWAERTS — je Gate die Vorkommen NACH `built` in den Retros. Bewusst NICHT ueber
   `tools/gate_wirkung.py` (das liest die Frontmatter-Liste `recurring_findings`),
   sondern ueber die Befund-Tabelle (§2) jeder Retro: eine Zeile zaehlt, wenn ihr
   Verdikt SURVIVES enthaelt und die Recurrence-Spalte den Slug (oder einen `covers`-Alias)
   nennt. Die Frontmatter wird daneben mit eigenem Parser gelesen — die Differenz der
   beiden Quellen ist selbst ein Befund ueber die Retro-Qualitaet. Dritte Quelle:
   `~/.claude/hooks/gate-hits.jsonl`, die realen Feuerungen der Hook-Gates.

   Datumsvariante des Kill-Gates ist `built` (Issue-Wortlaut); `revised or built` (so
   rechnet gate_wirkung.py) wird daneben ausgewiesen. Der Bau-Tag selbst zaehlt in keiner
   Variante (Retro beefc148 Befund 2).

2. VORWAERTS — Zerfallsrangliste aus Registry-Merkmalen ALLEIN: Alter seit `built`,
   fehlendes `kalibrierfenster`, `mode` != blocking, keine reale Feuerung im Hit-Log.
   Gleichgewichtete Merkmale, keine Anpassung an die Messung aus Teil 1 (die Gewichte
   stehen im Issue, nicht im Ergebnis). Ehrlichkeitsvermerk: der Autor hatte die
   gate_wirkung-Ausgabe gesehen, bevor er dieses Skript schrieb — der Advocatus Diabolus
   bekam diesen Punkt ausdruecklich.

   Abgrenzung zu platform#2253 (declined 2026-08-28, "Rueckfall aus Retro-Daten nicht
   vorhersagbar"): dort waren die Merkmale Text des Erstauftritts. Hier sind es Bau-
   Eigenschaften des Gates. Ein zweites Negativergebnis waere ein Ergebnis, kein Umweg.

   KILL-GATE (vorab, Issue-Wortlaut): die Rangliste muss die Grundlinie "nach Alter
   sortiert" auf den ersten fuenf Plaetzen schlagen. Mass: Anzahl der Top-5, die in
   Teil 1 mindestens einen Rueckfall zeigen (Variante `built`, inkl. covers, Tie-Break
   Slug aufsteigend). Gleichstand = nicht geschlagen = verworfen. Die uebrigen
   Wahrheits- und Tie-Break-Varianten werden mitberichtet, entscheiden aber nicht.

3. PRUEFDATENSATZ — `declined` (8) und `widerrufen` (2) aus der Registry: Vorkommen in
   SURVIVES-Zeilen NACH dem Entscheidungsdatum (strikt, symmetrisch zum Bau-Tag-
   Ausschluss); Vorkommen AM Entscheidungstag stehen daneben. Ein Verfahren, das die
   zwei Widerrufe nicht rueckwirkend als "Verzicht war falsch" zeigt, ist disqualifiziert.

REV 2 (2026-09-02, nach Advocatus Diabolus auf T4 Opus und T5 Fable, identischer Auftrag,
frischer Kontext): Rev 1 zaehlte Retros und nannte es Zeilen; zog Retros mit
`gates_caught`-Markierung pauschal ab (entfernte 15 belegte Rueckfaelle) und nutzte eine
Text-Heuristik, die Negationen traf; legte `covers`-Aliase rueckwirkend auf den ganzen
Korpus; brach Gleichstaende still alphabetisch; zaehlte den Entscheidungstag im
Pruefdatensatz mit, den Bau-Tag aber nicht. Alle fuenf Punkte sind hier ausgewiesen statt
versteckt. Das Verdikt "Instrument verworfen" haelt unter jeder Variante; die tragende
Begruendung ist nicht der Top-5-Abstand (Deckeneffekt: Grundlinie 5/5), sondern die
Rangkorrelation (Instrument ~0, Alter ~0,55) und die Gittersuche des T4-Diabolus (kein
Gewicht der vier Merkmale erreicht die Grundlinie).

Aufruf:
    python3 tools/messungen/gate_bilanz_2374.py            # Markdown-Bericht
    python3 tools/messungen/gate_bilanz_2374.py --json     # Rohdaten

stdlib-only. Exit 0 immer (Messung, kein Enforcer).
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGISTRY = os.path.join(REPO, "docs", "governance", "gate-registry.json")
RETROS = os.path.join(REPO, "docs", "retros")
HITS = os.path.expanduser("~/.claude/hooks/gate-hits.jsonl")
HEUTE = dt.date(2026, 9, 2)
TOP_N = 5

_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")
_DATUM = re.compile(r"session-retro-(\d{4}-\d{2}-\d{2})-")
_VERDIKT = re.compile(r"SURVIVES|REFUTED|WIDERLEGT")
_PIPE = re.compile(r"(?<!\\)\|")


def _fm_liste(fm: str, key: str) -> list[str]:
    m = re.search(rf"^{key}:\s*\[(.*?)\]", fm, re.M | re.S)
    if m:
        return [s for s in _SLUG.findall(m.group(1).replace("\n", " ")) if len(s) > 3]
    m = re.search(rf"^{key}:\s*\n((?:[ \t]+-[^\n]*\n)+)", fm, re.M)
    if m:
        return [
            s
            for line in m.group(1).splitlines()
            for s in _SLUG.findall(line.split("#", 1)[0])
        ]
    return []


def lies_retros() -> list[dict]:
    out = []
    for pfad in sorted(glob.glob(os.path.join(RETROS, "session-retro-*.md"))):
        name = os.path.basename(pfad)
        if "-extern-" in name:
            continue
        m = _DATUM.match(name)
        if not m:
            continue
        text = open(pfad, encoding="utf-8", errors="replace").read()
        fm = ""
        if text.startswith("---"):
            teile = text.split("---", 2)
            if len(teile) >= 3:
                fm = teile[1]
        zeilen = []
        for line in text.splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in _PIPE.split(line)]
            v_idx = next((i for i, c in enumerate(cells) if _VERDIKT.search(c)), None)
            if v_idx is None or v_idx < 2:
                continue
            rest = [c for c in cells[v_idx + 1 :] if c]
            if not rest:
                continue
            recurrence = rest[-1]
            zeilen.append(
                {
                    "survives": "SURVIVES" in cells[v_idx],
                    "slugs": sorted(set(_SLUG.findall(recurrence))),
                }
            )
        out.append(
            {
                "name": name,
                "datum": dt.date.fromisoformat(m.group(1)),
                "fm_recurring": _fm_liste(fm, "recurring_findings"),
                "fm_caught": _fm_liste(fm, "gates_caught"),
                "zeilen": zeilen,
            }
        )
    return out


def lies_hits() -> dict[str, list[dt.date]]:
    hits: dict[str, list[dt.date]] = {}
    if not os.path.exists(HITS):
        return hits
    for line in open(HITS, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        z = str(r.get("zeit", ""))[:10]
        try:
            hits.setdefault(r.get("slug", ""), []).append(dt.date.fromisoformat(z))
        except ValueError:
            continue
    return hits


def _d(s: str | None) -> dt.date | None:
    return dt.date.fromisoformat(s) if s else None


def rueckwaerts(gates: list[dict], retros: list[dict], hits: dict) -> list[dict]:
    """Je Gate: Vorkommen nach built / nach revised, Frontmatter-Vergleich, Hits.

    Zwei Zaehleinheiten, beide ausgewiesen: `zeilen` (SURVIVES-Zeilen) und `retros`
    (Retros mit >=1 solcher Zeile). Rev 2 nach Diabolus T5: die Erstfassung zaehlte
    Retros und nannte es Zeilen.

    `gefangen` wird NICHT mehr abgezogen. Die Erstfassung schluckte jede Zeile eines
    Slugs, sobald die Frontmatter `gates_caught` ihn nannte — und die Retros markieren
    gefangene Zeilen nicht einzeln; eine Text-Heuristik (`nicht gefangen`) traf
    Negationen. Beides entfernte belegte Rueckfaelle (cc4e11 2026-09-01, a84f71 Z. 43).
    Die Frontmatter-Markierung steht daneben als eigene Spalte.

    `eigen` zaehlt nur den Slug selbst, `alias` schliesst `covers` ein. Aliase koennen
    anachronistisch sein (covers erst nach dem Vorkommen gesetzt, Realfall
    `no-checks-reported-read-as-green`, covers seit 2026-08-31 fuer Zeilen vom 26./28.08.).
    """
    ergebnis = []
    for g in gates:
        slug = g["slug"]
        aliase = {slug, *(g.get("covers") or [])}
        built = _d(g.get("built"))
        revised = _d(g.get("revised")) or built
        z_eigen: list[dt.date] = []  # eine Eintragung je Zeile
        z_alias: list[dt.date] = []
        r_alias: set[str] = set()
        r_eigen_namen: set[str] = set()
        r_revised: set[str] = set()
        r_before: set[str] = set()
        fm_after: set[str] = set()
        fm_caught: set[str] = set()
        for r in retros:
            d = r["datum"]
            zeilen = [z for z in r["zeilen"] if z["survives"]]
            eigen = [z for z in zeilen if slug in z["slugs"]]
            alias = [z for z in zeilen if aliase & set(z["slugs"])]
            if built and d > built:
                z_eigen.extend([d] * len(eigen))
                z_alias.extend([d] * len(alias))
                if eigen:
                    r_eigen_namen.add(r["name"])
                if alias:
                    r_alias.add(r["name"])
                if aliase & set(r["fm_recurring"]):
                    fm_after.add(r["name"])
                if aliase & set(r["fm_caught"]):
                    fm_caught.add(r["name"])
            if built and d < built and alias:
                r_before.add(r["name"])
            if revised and d > revised and alias:
                r_revised.add(r["name"])
        h_after = [x for x in hits.get(slug, []) if built and x > built]
        fenster = sum(1 for r in retros if built and r["datum"] > built)
        ergebnis.append(
            {
                "slug": slug,
                "mode": g.get("mode"),
                "built": g.get("built"),
                "revised": g.get("revised"),
                "covers": g.get("covers") or [],
                "fenster_retros": fenster,
                "vor_built_retros": len(r_before),
                "nach_built_zeilen_eigen": len(z_eigen),
                "nach_built_zeilen_alias": len(z_alias),
                "nach_built_retros_eigen": len(r_eigen_namen),
                "nach_built_retros_alias": len(r_alias),
                "nach_revised_retros_alias": len(r_revised),
                "nach_built_frontmatter_retros": len(fm_after),
                "frontmatter_gefangen_retros": len(fm_caught),
                "hits_nach_built": len(h_after),
                "hits_gesamt": len(hits.get(slug, [])),
                "letzter_rueckfall": max(z_alias).isoformat() if z_alias else None,
                # Drei Wahrheiten fuer das Kill-Gate — vorregistriert war "alias, ohne
                # gefangen"; die Abzugsregel ist widerlegt, daher alias brutto als
                # Hauptvariante, eigen und netto (Retros ohne gates_caught-Markierung)
                # daneben.
                "rueckfaellig_alias": len(r_alias) >= 1,
                "rueckfaellig_eigen": len(r_eigen_namen) >= 1,
                "rueckfaellig_netto": len(r_alias - fm_caught) >= 1,
                "rueckfaellig_revised": len(r_revised) >= 1,
                "rueckfall_retros_alias": len(r_alias),
            }
        )
    return ergebnis


def zerfall(gates: list[dict], hits: dict) -> list[dict]:
    """Rangliste aus Registry-Merkmalen, gleichgewichtet; Grundlinie = Alter."""
    rows = []
    for g in gates:
        built = _d(g.get("built"))
        alter = (HEUTE - built).days if built else 0
        m_alter = (
            alter / 30.0
        )  # Monate; stetiges Merkmal, damit die Rangliste nicht nur aus Bits besteht
        m_kf = 0 if g.get("kalibrierfenster") else 1
        m_mode = 0 if g.get("mode") == "blocking" else 1
        # Diabolus T5: das Hit-Log kennt nur die fuenf Hook-Gates. Fuer die uebrigen 28
        # heisst dieses Bit "hat keinen Hook", nicht "nie gefeuert" — ein Typ-Merkmal.
        m_hit = 0 if hits.get(g["slug"]) else 1
        rows.append(
            {
                "slug": g["slug"],
                "alter_tage": alter,
                "ohne_kalibrierfenster": m_kf,
                "nicht_blockierend": m_mode,
                "nie_gefeuert": m_hit,
                "score": round(m_alter + m_kf + m_mode + m_hit, 3),
            }
        )
    rang = sorted(rows, key=lambda r: (-r["score"], r["slug"]))
    basis = sorted(rows, key=lambda r: (-r["alter_tage"], r["slug"]))
    for i, r in enumerate(rang, 1):
        r["rang"] = i
    for i, r in enumerate(basis, 1):
        r["rang_basis"] = i
    return rang


def _spearman(a: list[float], b: list[float]) -> float:
    """Rangkorrelation (mittlere Raenge bei Bindungen), stdlib."""

    def raenge(x):
        s = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and x[s[j + 1]] == x[s[i]]:
                j += 1
            for k in range(i, j + 1):
                r[s[k]] = (i + j) / 2 + 1
            i = j + 1
        return r

    ra, rb = raenge(a), raenge(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5
    vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


def kill_gate(
    rang: list[dict], rueck: list[dict], wahrheit: str = "alias", tie: str = "az"
) -> dict:
    """Top-5-Vergleich gegen die Alters-Grundlinie; `wahrheit` waehlt die Rueckfall-Definition.

    Zusatz (post hoc, Diabolus T5): Spearman zwischen Rang und Rueckfall-Retros ueber alle
    Gates — die Top-5-Zaehlung hat einen Deckeneffekt, sobald die fuenf aeltesten Gates
    alle rueckfaellig sind (dann ist "schlagen" unerfuellbar).
    """
    key = f"rueckfaellig_{wahrheit}"
    wahr = {r["slug"] for r in rueck if r[key]}
    # Tie-Break DEKLARIERT (Diabolus T4: der stille alphabetische Break setzte die
    # Grundlinie auf ihr Maximum und das Instrument auf sein Minimum): "az" = Slug
    # aufsteigend, "za" = absteigend; beide werden berichtet.
    rev = tie == "za"
    top = [
        r["slug"]
        for r in sorted(
            sorted(rang, key=lambda r: r["slug"], reverse=rev),
            key=lambda r: -r["score"],
        )
    ][:TOP_N]
    basis = [
        r["slug"]
        for r in sorted(
            sorted(rang, key=lambda r: r["slug"], reverse=rev),
            key=lambda r: -r["alter_tage"],
        )
    ][:TOP_N]
    t_inst = len(wahr & set(top))
    t_basis = len(wahr & set(basis))
    zaehler = {r["slug"]: r["rueckfall_retros_alias"] for r in rueck}
    slugs = [r["slug"] for r in rang]
    y = [float(zaehler[s]) for s in slugs]
    return {
        "wahrheit": wahrheit,
        "tie": tie,
        "rueckfaellige_gates": sorted(wahr),
        "top5_instrument": top,
        "top5_treffer_instrument": t_inst,
        "top5_grundlinie": basis,
        "top5_treffer_grundlinie": t_basis,
        "instrument_schlaegt_grundlinie": t_inst > t_basis,
        "deckeneffekt": t_basis == TOP_N,
        "spearman_instrument": round(
            _spearman([-r["score"] for r in rang], [-v for v in y]), 3
        ),
        "spearman_alter": round(
            _spearman([-r["alter_tage"] for r in rang], [-v for v in y]), 3
        ),
    }


def pruefdatensatz(reg: dict, retros: list[dict]) -> list[dict]:
    out = []
    for kind in ("declined", "widerrufen"):
        for e in reg.get(kind, []):
            slug = e["slug"]
            datum = _d(e.get("decided") or e.get("declined_am") or e.get("built"))
            nach = []
            vor = []
            am_tag = []
            for r in retros:
                rows = [z for z in r["zeilen"] if z["survives"] and slug in z["slugs"]]
                if not rows or not datum:
                    continue
                if r["datum"] > datum:
                    nach.append(r["datum"])
                elif r["datum"] == datum:
                    # Der Entscheidungs-Tag zaehlt hier MIT — anders als der Bau-Tag eines
                    # Gates: ein Verzicht kann noch am selben Tag widerlegt werden (Realfall
                    # a84f71, 2026-08-23), und genau das soll dieser Datensatz zeigen.
                    am_tag.append(r["datum"])
                else:
                    vor.append(r["datum"])
            out.append(
                {
                    "slug": slug,
                    "klasse": kind,
                    "entschieden": datum.isoformat() if datum else None,
                    "vor_entscheidung": len(vor),
                    "am_tag": len(am_tag),
                    "nach_entscheidung": len(nach),
                    "ab_entscheidung": len(am_tag) + len(nach),
                    "letztes": max(nach + am_tag).isoformat()
                    if nach or am_tag
                    else None,
                }
            )
    out.sort(key=lambda r: (-r["ab_entscheidung"], r["slug"]))
    return out


def bericht(rueck, rang, kgs, pd, n_retros, n_zeilen) -> str:
    L = [
        f"# Gate-Bilanz #2374 Ziel A — Stand {HEUTE}, {n_retros} Retros, {n_zeilen} Befund-Zeilen mit Verdikt, {len(rueck)} Gates",
        "",
        "Rev 2 nach Advocatus Diabolus (T4 Opus + T5 Fable, 2026-09-02): Zaehleinheit Retros UND Zeilen, "
        "kein Gefangen-Abzug, Aliase getrennt, Tie-Break deklariert, Kill-Gate unter allen Varianten.",
        "",
        "## 1. Rueckwaerts (SURVIVES-Zeilen der Befund-Tabellen nach `built`; Bau-Tag ausgeschlossen)",
        "",
        "| Gate | mode | built | revised | Fenster | vor | Retros eigen | Retros alias | Zeilen eigen | Zeilen alias | Retros nach revised | FM | FM gefangen | Hits | letzter |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(
        rueck,
        key=lambda r: (
            -r["nach_built_retros_alias"],
            -r["nach_built_zeilen_alias"],
            r["slug"],
        ),
    ):
        L.append(
            f"| `{r['slug']}` | {r['mode']} | {r['built']} | {r['revised'] or '—'} | {r['fenster_retros']} | "
            f"{r['vor_built_retros']} | **{r['nach_built_retros_eigen']}** | {r['nach_built_retros_alias']} | "
            f"{r['nach_built_zeilen_eigen']} | {r['nach_built_zeilen_alias']} | {r['nach_revised_retros_alias']} | "
            f"{r['nach_built_frontmatter_retros']} | {r['frontmatter_gefangen_retros']} | {r['hits_nach_built']} | {r['letzter_rueckfall'] or '—'} |"
        )
    L.append("")
    nur_alias = [
        r["slug"]
        for r in rueck
        if r["rueckfaellig_alias"] and not r["rueckfaellig_eigen"]
    ]
    L.append(
        f"Rueckfaellig (>=1 Retro nach built): eigener Slug **{sum(r['rueckfaellig_eigen'] for r in rueck)}**, "
        f"inkl. covers **{sum(r['rueckfaellig_alias'] for r in rueck)}**, ohne gates_caught-Retros "
        f"{sum(r['rueckfaellig_netto'] for r in rueck)}, nach revised {sum(r['rueckfaellig_revised'] for r in rueck)} von {len(rueck)}. "
        f"Nur ueber Aliase rueckfaellig: " + ", ".join(f"`{s}`" for s in nur_alias)
    )
    diff = [
        r
        for r in rueck
        if r["nach_built_retros_alias"] != r["nach_built_frontmatter_retros"]
    ]
    L.append("")
    L.append(
        f"Quellen-Differenz Tabelle vs. Frontmatter (Retros nach built): {len(diff)} Gate(s): "
        + ", ".join(
            f"`{r['slug']}` {r['nach_built_retros_alias']}/{r['nach_built_frontmatter_retros']}"
            for r in diff
        )
    )
    L.append("")
    L.append("## 2. Vorwaerts — Zerfallsrangliste (Registry-Merkmale, gleichgewichtet)")
    L.append("")
    L.append(
        "| Rang | Gate | Alter (d) | ohne KF | nicht blockierend | nie gefeuert | Score | Rang Grundlinie |"
    )
    L.append("|---|---|---|---|---|---|---|---|")
    for r in rang:
        L.append(
            f"| {r['rang']} | `{r['slug']}` | {r['alter_tage']} | {r['ohne_kalibrierfenster']} | {r['nicht_blockierend']} | {r['nie_gefeuert']} | {r['score']} | {r['rang_basis']} |"
        )
    L.append("")
    L.append(
        "Merkmals-Guete: `ohne KF` ist bei 32/33 = 1, `nie gefeuert` bei 28/33 = 1 (Hit-Log kennt fuenf Hook-Gates) — beide tragen kaum zur Ordnung bei."
    )
    L.append("")
    L.append("## 3. Kill-Gate (Top-5 gegen Alters-Grundlinie)")
    L.append("")
    L.append(
        "| Wahrheit | Tie-Break | rueckfaellig | Instrument | Grundlinie | schlaegt | Deckeneffekt |"
    )
    L.append("|---|---|---|---|---|---|---|")
    for kg in kgs:
        L.append(
            f"| {kg['wahrheit']} | {kg['tie']} | {len(kg['rueckfaellige_gates'])} | {kg['top5_treffer_instrument']} | "
            f"{kg['top5_treffer_grundlinie']} | {'JA' if kg['instrument_schlaegt_grundlinie'] else 'nein'} | {'ja' if kg['deckeneffekt'] else '—'} |"
        )
    k0 = kgs[0]
    L.append("")
    L.append(
        f"Vorregistrierte Variante = erste Zeile (alias, az): Instrument {k0['top5_treffer_instrument']} vs. Grundlinie "
        f"{k0['top5_treffer_grundlinie']} → **{'schlaegt' if k0['instrument_schlaegt_grundlinie'] else 'verworfen'}**. "
        f"Spearman Rang↔Rueckfall-Retros ueber alle Gates: Instrument {k0['spearman_instrument']}, Alter {k0['spearman_alter']}."
    )
    L.append("")
    L.append("## 4. Pruefdatensatz declined / widerrufen (SURVIVES-Zeilen, Retros)")
    L.append("")
    L.append("| Slug | Klasse | entschieden | vor | am Tag | nach | letztes |")
    L.append("|---|---|---|---|---|---|---|")
    for r in pd:
        L.append(
            f"| `{r['slug']}` | {r['klasse']} | {r['entschieden']} | {r['vor_entscheidung']} | {r['am_tag']} | **{r['nach_entscheidung']}** | {r['letztes'] or '—'} |"
        )
    wid = [r for r in pd if r["klasse"] == "widerrufen"]
    nach = [r["slug"] for r in wid if r["nach_entscheidung"] >= 1]
    ab = [r["slug"] for r in wid if r["ab_entscheidung"] >= 1]
    L.append("")
    L.append(
        f"Widerrufe mit Vorkommen strikt NACH dem Entscheidungstag: {len(nach)}/{len(wid)}; ab Entscheidungstag: {len(ab)}/{len(wid)}. "
        "Symmetrisch zum Bau-Tag-Ausschluss zaehlt nur 'nach' — damit ist das Kriterium des Issues bei "
        f"{'beiden' if len(nach) == len(wid) else 'einem'} Widerruf{'en' if len(nach) == len(wid) else ''} erfuellt. "
        "Fuer `gate-matches-spelling-not-substance` ist der einzige Treffer der Befund, aus dem der Widerruf entstand (a84f71 Befund 5)."
    )
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    reg = json.load(open(REGISTRY, encoding="utf-8"))
    retros = lies_retros()
    hits = lies_hits()
    rueck = rueckwaerts(reg["gates"], retros, hits)
    rang = zerfall(reg["gates"], hits)
    kgs = [
        kill_gate(rang, rueck, w, t)
        for w in ("alias", "eigen", "netto", "revised")
        for t in ("az", "za")
    ]
    pd = pruefdatensatz(reg, retros)
    n_zeilen = sum(len(r["zeilen"]) for r in retros)
    if a.json:
        json.dump(
            {
                "retros": len(retros),
                "zeilen": n_zeilen,
                "rueckwaerts": rueck,
                "zerfall": rang,
                "kill_gate": kgs,
                "pruefdatensatz": pd,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=1,
            default=str,
        )
    else:
        print(bericht(rueck, rang, kgs, pd, len(retros), n_zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
