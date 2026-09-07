#!/usr/bin/env python3
"""kosten_qualitaet.py — Kosten-/Qualitäts-Tabelle je Claude-Code-Sitzung.

Read-only Auswertungswerkzeug: führt drei bereits vorhandene, aber nie
verbundene Datenquellen je Sitzung zusammen. Schreibt NICHTS ausser seiner
Ausgabe, ruft KEINE Datenbank und KEIN Netzwerk auf.

Datenquellen
------------
1. Sitzungs-Mitschriften (`~/.claude/projects/<slug>/<session_id>.jsonl` +
   `.../<session_id>/subagents/agent-*.jsonl`) — Kosten, Modellmix,
   Nachbesserung. Das Zeilen-Parsing (kaputte Zeilen still überspringen,
   Subagenten-Pfad `<session_id>/subagents/agent-*.jsonl`) folgt den
   Konventionen aus `tools/claude-hooks/session_modellmix.py`;
   `_iter_records` und `DEFAULT_PROJECTS_DIR` werden von dort importiert
   statt kopiert. `WRITING_TOOLS` aus demselben Modul bleibt aussen vor:
   es misst eine andere Kennzahl (Schreibanteil je Modell), waehrend die
   Nachbesserungs-Deckung Dateipfade braucht, keine Werkzeug-Anteile.
2. Preistabelle `tools/claude-hooks/llm_pricing.py` (ausgelagert aus
   `log_llm_call.py`, siehe dortigen Kommentar — ein reiner Import der
   Konstanten darf keine DB-URL auflösen).
3. Ledger `~/.claude/hooks/state/modellmix-ledger.tsv` — Delegationsanteil
   Token, bereits vorberechnet vom SessionEnd-Hook.
4. Retro-Qualitätsnoten `docs/retros/session-retro-*.md` (Frontmatter,
   `-extern-`-Briefings ausgeschlossen wie in `tools/retro_kpis.py`).

Der Verbindungsschlüssel
-------------------------
Dieselbe Sitzung erscheint in drei Längen: Mitschrift = volle UUID,
Ledger = 8 Zeichen, Retro = 6 Zeichen (teils mit Suffix wie `-incr`, das
KEIN Teil der Sitzungs-ID ist und vor dem Präfix-Vergleich abgeschnitten
wird). Verbunden wird per Präfix gegen die Menge aller im Auswertungs-
zeitraum gefundenen vollen UUIDs. Passt ein Präfix auf MEHR ALS EINE volle
UUID, wird die Zeile NICHT still zugeordnet, sondern als `mehrdeutig`
gezählt und aus der Auswertung ausgeschlossen.

Kostenrechnung
--------------
WAS DIE ZAHL IST — und was nicht: `Kosten$` ist ein **Listenpreis-Äquivalent**,
also was dieselben Token über die Anthropic-API gekostet hätten. Es ist NICHT
die Rechnung: Claude Code läuft über ein Abonnement, dessen Preis nicht an der
Tokenzahl hängt. Die Spalte taugt zum Vergleich von Sitzungen und Modellen
gegeneinander, nicht als Ausgabenbeleg.

Zweite Einordnung: in langen Sitzungen entfallen regelmässig über 90 % der
Token auf `cache_read_input_tokens` (gemessen 2026-09-07 an einer Sitzung:
98 %). Cache-Lesungen wachsen mit der Länge des Verlaufs, nicht mit der
geleisteten Arbeit — eine hohe Zahl heisst zuerst "lange Sitzung", nicht
"teure Arbeit".

Cache-Token sind eine Näherung: `cache_read_input_tokens` kostet ca. 10 %
des Input-Preises, `cache_creation_input_tokens` ca. 125 % — das entspricht
dem 5-Minuten-Schreib-Tarif; ein Teil der echten Cache-Writes läuft auf dem
1-Stunden-Tarif (200 %) und wird dadurch leicht unterschätzt. Für eine
Sitzungs-Übersicht ist das ausreichend genau; `log_llm_call.py` rechnet für
einzelne API-Calls exakter (kennt `cache_creation.ephemeral_{5m,1h}_...`).

Nachbesserungs-Deckung
----------------------
Eine Nachbesserung liegt vor, wenn eine Datei zuerst von einem Subagenten
geschrieben und danach in derselben Sitzung vom Hauptmodell erneut
geschrieben wird. Dateipfade sind nur aus strukturierten Schreibaufrufen
sicher ablesbar (`tool_use` mit `input["file_path"]`, Werkzeuge Write/Edit/
NotebookEdit). Läuft eine Sitzung im Bash-Modus (`sed -i`, Heredoc, `tee`,
...), ist dort kein `file_path` sichtbar — eine naive Zählung ergäbe 0
Nachbesserungen, was wie „alles gut" aussieht, aber nur der eigene Filter
ist. Deshalb wird je Sitzung eine Deckung mitgeführt
(`schreibaufrufe_mit_pfad` / `schreibaufrufe_gesamt`, letzteres inkl. der
Bash-Aufrufe, deren Kommando ein Schreib-Muster enthält) — die Quote wird
NUR ausgegeben, wenn die Deckung >= 50 % beträgt, sonst erscheint
`ungedeckt (Deckung X%)`, NIEMALS `0`.

CLI
---
    kosten_qualitaet.py [--seit YYYY-MM-DD] [--projekt SLUG] [--json]
                        [--projects-dir DIR] [--ledger PFAD] [--retros-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import collections
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_TOOLS_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _TOOLS_DIR / "claude-hooks"
for _p in (_TOOLS_DIR, _HOOKS_DIR):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from llm_pricing import price_for  # noqa: E402
from retro_kpis import SCORE_KEYS, load_reports  # noqa: E402
from session_modellmix import DEFAULT_PROJECTS_DIR, _iter_records  # noqa: E402

#: Bash-Kommando-Muster, die auf einen Schreibvorgang OHNE erkennbaren
#: `file_path` hindeuten (Näherung, s. Docstring "Nachbesserungs-Deckung").
BASH_WRITE_PATTERNS = (
    ">",
    ">>",
    "sed -i",
    "tee",
    "mv",
    "cp",
    "install",
    "git apply",
    "patch",
)

#: Werkzeuge, deren `input["file_path"]` einen Schreibvorgang sicher belegt.
PATH_WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}

DEFAULT_LEDGER = Path(
    os.environ.get("MODELLMIX_LEDGER")
    or (Path.home() / ".claude" / "hooks" / "state" / "modellmix-ledger.tsv")
)
DEFAULT_RETRO_DIRS = [str(_TOOLS_DIR.parent / "docs" / "retros")]


# ---------------------------------------------------------------------------
# Datentypen
# ---------------------------------------------------------------------------


@dataclass
class ModellBucket:
    """Token je Modell, aufgeschlüsselt nach Preis-relevanten Feldern."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_creation: int = 0

    def gesamt(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read
            + self.cache_creation
        )

    def kosten_usd(self, model: str) -> float:
        p = price_for(model)
        return (
            self.input_tokens * p["input"]
            + self.cache_read * p["input"] * 0.1
            + self.cache_creation * p["input"] * 1.25
            + self.output_tokens * p["output"]
        ) / 1_000_000.0


@dataclass
class SchreibSpur:
    """Ein Schreibaufruf mit erkennbarem Pfad, für die Nachbesserungs-Erkennung."""

    writer: str  # "haupt" oder Subagenten-Dateiname
    file_path: str
    timestamp: str  # ISO8601, leer wenn nicht vorhanden


@dataclass
class SessionAggregat:
    """Alles, was aus den Mitschriften EINER Sitzung gezogen wurde."""

    session_id: str
    projekt: str
    datum: str = ""
    hauptmodell: str = ""
    modelle: dict[str, ModellBucket] = field(default_factory=dict)
    n_subagenten: int = 0
    schreibaufrufe_mit_pfad: int = 0
    schreibaufrufe_gesamt: int = 0
    schreib_spuren: list[SchreibSpur] = field(default_factory=list)
    kaputte_zeilen: int = 0

    def gesamt_tokens(self) -> int:
        return sum(b.gesamt() for b in self.modelle.values())

    def gesamt_kosten_usd(self) -> float:
        return sum(b.kosten_usd(model) for model, b in self.modelle.items())

    def haupt_kosten_usd(self) -> float:
        b = self.modelle.get(self.hauptmodell)
        return b.kosten_usd(self.hauptmodell) if b else 0.0

    def nicht_haupt_kosten_pct(self) -> float | None:
        gesamt = self.gesamt_kosten_usd()
        if gesamt <= 0:
            return None
        return round((gesamt - self.haupt_kosten_usd()) / gesamt * 100, 1)


def _is_bash_write(command: str) -> bool:
    return any(pat in command for pat in BASH_WRITE_PATTERNS)


def _raw_nonblank_zeilen(path: Path) -> int:
    """Nicht-leere Zeilen roh zählen — Vergleichsbasis für kaputte JSONL-Zeilen."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines() if line.strip())


def _accumulate_session(
    main_path: Path, session_id: str, projekt: str
) -> SessionAggregat:
    """Haupt-Transkript + Subagenten EINER Sitzung einlesen und aggregieren.

    Kaputte JSONL-Zeilen werden nicht einzeln geworfen (`_iter_records`
    überspringt sie still, wie in `session_modellmix.py` dokumentiert) —
    hier wird die Differenz aus roh gezählten nicht-leeren Zeilen und
    tatsächlich geparsten Records je Datei nachgezogen und in
    `agg.kaputte_zeilen` aufsummiert, statt den Fehler unbemerkt zu lassen.
    """
    agg = SessionAggregat(session_id=session_id, projekt=projekt)
    main_counts: dict[str, int] = {}

    def _lauf(path: Path, writer: str, ist_haupt: bool) -> None:
        nonlocal agg
        valide = 0
        for rec in _iter_records(path):
            valide += 1
            if rec.get("type") != "assistant":
                continue
            message = rec.get("message") or {}
            model = message.get("model")
            if not model:
                continue
            if ist_haupt:
                main_counts[model] = main_counts.get(model, 0) + 1
                if not agg.datum:
                    ts = rec.get("timestamp") or ""
                    if ts:
                        agg.datum = ts[:10]
            usage = message.get("usage") or {}
            bucket = agg.modelle.setdefault(model, ModellBucket())
            bucket.input_tokens += int(usage.get("input_tokens") or 0)
            bucket.output_tokens += int(usage.get("output_tokens") or 0)
            bucket.cache_read += int(usage.get("cache_read_input_tokens") or 0)
            bucket.cache_creation += int(usage.get("cache_creation_input_tokens") or 0)
            ts = rec.get("timestamp") or ""
            for block in message.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name")
                tool_input = block.get("input")
                if not isinstance(tool_input, dict):
                    tool_input = {}
                if name in PATH_WRITE_TOOLS:
                    fp = tool_input.get("file_path")
                    if isinstance(fp, str) and fp:
                        agg.schreibaufrufe_mit_pfad += 1
                        agg.schreibaufrufe_gesamt += 1
                        agg.schreib_spuren.append(
                            SchreibSpur(writer=writer, file_path=fp, timestamp=ts)
                        )
                elif name == "Bash":
                    cmd = tool_input.get("command")
                    if isinstance(cmd, str) and _is_bash_write(cmd):
                        agg.schreibaufrufe_gesamt += 1
                # Werkzeugname sonst irrelevant für die Deckung. WRITING_TOOLS
                # (aus session_modellmix) passt hier nicht: es misst den
                # Modellmix-Schreibanteil, eine andere Kennzahl als die Deckung.
        agg.kaputte_zeilen += max(_raw_nonblank_zeilen(path) - valide, 0)

    try:
        _lauf(main_path, "haupt", True)
    except OSError:
        pass

    subagents_dir = main_path.parent / main_path.stem / "subagents"
    if subagents_dir.is_dir():
        for sub_path in sorted(subagents_dir.glob("agent-*.jsonl")):
            agg.n_subagenten += 1
            _lauf(sub_path, sub_path.stem, False)

    if main_counts:
        agg.hauptmodell = min(main_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]

    return agg


def nachbesserungsquote(agg: SessionAggregat) -> tuple[float | None, float]:
    """(Quote in %, Deckung in %) — Quote ist None, wenn die Deckung < 50 %.

    Quote = Anteil der von Subagenten geschriebenen Dateien, die danach vom
    Hauptmodell erneut geschrieben wurden.
    """
    if agg.schreibaufrufe_gesamt == 0:
        deckung = 100.0
    else:
        deckung = round(
            agg.schreibaufrufe_mit_pfad / agg.schreibaufrufe_gesamt * 100, 1
        )

    if deckung < 50.0:
        return None, deckung

    sub_first: dict[str, str] = {}
    haupt_writes: dict[str, list[str]] = {}
    for spur in agg.schreib_spuren:
        if spur.writer == "haupt":
            haupt_writes.setdefault(spur.file_path, []).append(spur.timestamp)
        else:
            prev = sub_first.get(spur.file_path)
            if prev is None or (spur.timestamp and spur.timestamp < prev):
                sub_first[spur.file_path] = spur.timestamp

    if not sub_first:
        return 0.0, deckung

    nachbesserte = 0
    for pfad, sub_ts in sub_first.items():
        for haupt_ts in haupt_writes.get(pfad, []):
            if not sub_ts or not haupt_ts or haupt_ts > sub_ts:
                nachbesserte += 1
                break

    quote = round(nachbesserte / len(sub_first) * 100, 1)
    return quote, deckung


# ---------------------------------------------------------------------------
# Sitzungs-Entdeckung
# ---------------------------------------------------------------------------


def discover_sessions(
    projects_dir: Path, projekt: str | None
) -> list[tuple[Path, str, str]]:
    """Alle Haupt-Transkripte finden: (pfad, volle_session_id, projekt_slug).

    Das Datum steht erst NACH dem Parsen der Mitschrift fest (aus dem ersten
    Assistant-Record) — der `--seit`-Filter greift deshalb erst in `run()`,
    nicht schon hier bei der reinen Datei-Entdeckung.
    """
    out = []
    if not projects_dir.is_dir():
        return out
    project_dirs = (
        [projects_dir / projekt] if projekt else sorted(projects_dir.iterdir())
    )
    for pdir in project_dirs:
        if not pdir.is_dir():
            continue
        for jf in sorted(pdir.glob("*.jsonl")):
            out.append((jf, jf.stem, pdir.name))
    return out


# ---------------------------------------------------------------------------
# Präfix-Verbindung (Ledger, Retro) gegen die Menge voller UUIDs
# ---------------------------------------------------------------------------


def resolve_prefix(prefix: str, full_ids: list[str]) -> tuple[str | None, bool]:
    """(volle_id_oder_None, mehrdeutig) für ein Präfix gegen `full_ids`.

    Ohne vorindizierten Cache (Aufruf ist klein: <=~200 Sitzungen je Lauf).
    """
    treffer = [full for full in full_ids if full.startswith(prefix)]
    if len(treffer) == 1:
        return treffer[0], False
    if len(treffer) > 1:
        return None, True
    return None, False


_RETRO_SUFFIX_RE = re.compile(r"^([0-9a-f]{4,})(?:-.*)?$")


def normalize_retro_session_id(raw: str) -> str:
    """`0181a7-incr` -> `0181a7`; alles nach dem ersten `-` ist kein ID-Teil."""
    m = _RETRO_SUFFIX_RE.match(raw.strip())
    return m.group(1) if m else raw.strip()


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def load_ledger(path: Path) -> list[dict[str, str]]:
    """TSV lesen; fehlende Datei -> leere Liste (kein Absturz)."""
    if not path.is_file():
        return []
    rows = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != len(header):
            continue
        rows.append(dict(zip(header, parts)))
    return rows


# ---------------------------------------------------------------------------
# Retros
# ---------------------------------------------------------------------------


def retro_qualitaet(fm: dict) -> float | None:
    scores = fm.get("scores") or {}
    werte = [scores[k] for k in SCORE_KEYS if k in scores]
    if not werte:
        return None
    return round(statistics.mean(werte), 2)


# ---------------------------------------------------------------------------
# Verbindung — eine Zeile je Sitzung
# ---------------------------------------------------------------------------


@dataclass
class Zeile:
    datum: str
    session_kurz: str
    hauptmodell: str
    kosten_usd: float
    kostenanteil_nicht_haupt_pct: float | None
    delegation_pct: float | None
    qualitaet: float | None
    nachbesserung_pct: float | None
    nachbesserung_deckung_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "datum": self.datum,
            "session": self.session_kurz,
            "hauptmodell": self.hauptmodell,
            "kosten_usd": round(self.kosten_usd, 4),
            "kostenanteil_nicht_hauptmodell_pct": self.kostenanteil_nicht_haupt_pct,
            "delegationsanteil_token_pct": self.delegation_pct,
            "qualitaet": self.qualitaet,
            "nachbesserung_pct": self.nachbesserung_pct,
            "nachbesserung_deckung_pct": self.nachbesserung_deckung_pct,
        }


def build_zeilen(
    aggregate: list[SessionAggregat],
    ledger_rows: list[dict[str, str]],
    retro_reports: list[dict],
) -> tuple[list[Zeile], dict[str, int]]:
    """Aggregate + Ledger + Retros zu Zeilen verbinden. Gibt (Zeilen, Warnungen)."""
    full_ids = [a.session_id for a in aggregate]
    warnungen = {"mehrdeutig_ledger": 0, "mehrdeutig_retro": 0}

    ledger_by_full: dict[str, dict[str, str]] = {}
    for row in ledger_rows:
        prefix = (row.get("session_id") or "").strip()
        if not prefix:
            continue
        full, mehrdeutig = resolve_prefix(prefix, full_ids)
        if mehrdeutig:
            warnungen["mehrdeutig_ledger"] += 1
            continue
        if full:
            ledger_by_full[full] = row

    retro_by_full: dict[str, dict] = {}
    for fm in retro_reports:
        raw = (fm.get("session_id") or "").strip()
        if not raw:
            continue
        prefix = normalize_retro_session_id(raw)
        full, mehrdeutig = resolve_prefix(prefix, full_ids)
        if mehrdeutig:
            warnungen["mehrdeutig_retro"] += 1
            continue
        if full:
            retro_by_full[full] = fm

    zeilen = []
    for agg in aggregate:
        ledger_row = ledger_by_full.get(agg.session_id)
        delegation_pct = None
        if ledger_row and ledger_row.get("anteil_tokens_nicht_hauptmodell"):
            try:
                delegation_pct = float(ledger_row["anteil_tokens_nicht_hauptmodell"])
            except ValueError:
                delegation_pct = None

        fm = retro_by_full.get(agg.session_id)
        qualitaet = retro_qualitaet(fm) if fm else None

        nachbesserung_pct, deckung = nachbesserungsquote(agg)

        zeilen.append(
            Zeile(
                datum=agg.datum,
                session_kurz=agg.session_id[:8],
                hauptmodell=agg.hauptmodell,
                kosten_usd=agg.gesamt_kosten_usd(),
                kostenanteil_nicht_haupt_pct=agg.nicht_haupt_kosten_pct(),
                delegation_pct=delegation_pct,
                qualitaet=qualitaet,
                nachbesserung_pct=nachbesserung_pct,
                nachbesserung_deckung_pct=deckung,
            )
        )
    return zeilen, warnungen


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------


def _fmt_pct(v: float | None) -> str:
    return "" if v is None else f"{v:.1f}"


def _fmt_usd(v: float) -> str:
    return f"{v:.4f}"


def _fmt_qual(v: float | None) -> str:
    return "" if v is None else f"{v:.2f}"


def _fmt_nachbesserung(pct: float | None, deckung: float) -> str:
    if pct is None:
        return f"ungedeckt (Deckung {deckung:.0f}%)"
    return f"{pct:.1f}%"


def render_text(zeilen: list[Zeile], warnungen: dict[str, int], kaputt: int) -> str:
    header = (
        "Kosten$ = Listenpreis-Aequivalent der Token, NICHT die Abo-Rechnung.\n"
        "In langen Sitzungen sind >90 % davon Cache-Lesungen (waechst mit der\n"
        "Verlaufslaenge, nicht mit der Arbeit).\n\n"
        f"{'Datum':<11}{'Sitzung':<10}{'Hauptmodell':<20}{'Kosten$':>9}"
        f"  {'NichtHaupt%':>11}  {'Deleg%':>7}  {'Qualität':>8}  Nachbesserung"
    )
    lines = [header, "-" * len(header)]
    gesamt_kosten = 0.0
    mit_delegation: list[float] = []
    ohne_delegation: list[float] = []
    for z in zeilen:
        lines.append(
            f"{z.datum:<11}{z.session_kurz:<10}{z.hauptmodell:<20}"
            f"{_fmt_usd(z.kosten_usd):>9}  {_fmt_pct(z.kostenanteil_nicht_haupt_pct):>11}  "
            f"{_fmt_pct(z.delegation_pct):>7}  {_fmt_qual(z.qualitaet):>8}  "
            f"{_fmt_nachbesserung(z.nachbesserung_pct, z.nachbesserung_deckung_pct)}"
        )
        gesamt_kosten += z.kosten_usd
        if z.delegation_pct is not None and z.delegation_pct > 0:
            mit_delegation.append((z.kosten_usd, z.hauptmodell))
        else:
            ohne_delegation.append((z.kosten_usd, z.hauptmodell))

    lines.append("-" * len(header))
    lines.append(f"{'SUMME':<11}{'':<10}{'':<20}{_fmt_usd(gesamt_kosten):>9}")
    lines.append("")

    def _bilanz(name: str, werte: list[tuple[float, str]]) -> str:
        """Bilanzzeile mit Hauptmodell-Verteilung.

        Die Verteilung steht bewusst dabei: die Kosten haengen viel staerker
        am Hauptmodell als an der Delegation. Ohne sie liest sich ein
        Gruppenunterschied als Delegations-Effekt, obwohl er meist nur die
        Modellverteilung der Gruppe spiegelt.
        """
        if len(werte) < 3:
            return f"{name}: zu wenige Daten (n={len(werte)})"
        kosten = [k for k, _ in werte]
        verteilung = collections.Counter(m or "unbekannt" for _, m in werte)
        top = ", ".join(f"{m} {n}x" for m, n in verteilung.most_common(3))
        return (
            f"{name}: n={len(werte)}, Ø {_fmt_usd(statistics.mean(kosten))} USD/Sitzung"
            f"  [Hauptmodell: {top}]"
        )

    lines.append(_bilanz("mit Delegation", mit_delegation))
    lines.append(_bilanz("ohne Delegation", ohne_delegation))
    lines.append(
        "Achtung: die beiden Gruppen sind nur vergleichbar, wenn ihre "
        "Hauptmodell-Verteilung\nvergleichbar ist — sonst misst der Unterschied "
        "das Modell, nicht die Delegation."
    )

    warn_bits = []
    if kaputt:
        warn_bits.append(f"{kaputt} kaputte JSONL-Zeile(n) übersprungen")
    if warnungen.get("mehrdeutig_ledger"):
        warn_bits.append(
            f"{warnungen['mehrdeutig_ledger']} mehrdeutige Ledger-Präfixe ausgeschlossen"
        )
    if warnungen.get("mehrdeutig_retro"):
        warn_bits.append(
            f"{warnungen['mehrdeutig_retro']} mehrdeutige Retro-Präfixe ausgeschlossen"
        )
    if warn_bits:
        lines.append("")
        lines.append("Warnungen: " + "; ".join(warn_bits))

    return "\n".join(lines)


def render_json(zeilen: list[Zeile], warnungen: dict[str, int], kaputt: int) -> str:
    gesamt_kosten = sum(z.kosten_usd for z in zeilen)
    mit_delegation = [
        z.kosten_usd for z in zeilen if z.delegation_pct and z.delegation_pct > 0
    ]
    ohne_delegation = [
        z.kosten_usd for z in zeilen if not (z.delegation_pct and z.delegation_pct > 0)
    ]

    def _bilanz(werte: list[float]) -> dict[str, Any]:
        if len(werte) < 3:
            return {"n": len(werte), "hinweis": f"zu wenige Daten (n={len(werte)})"}
        return {"n": len(werte), "durchschnitt_usd": round(statistics.mean(werte), 4)}

    payload = {
        "zeilen": [z.to_dict() for z in zeilen],
        "summe_kosten_usd": round(gesamt_kosten, 4),
        "bilanz": {
            "mit_delegation": _bilanz(mit_delegation),
            "ohne_delegation": _bilanz(ohne_delegation),
        },
        "warnungen": {
            "kaputte_jsonl_zeilen": kaputt,
            **warnungen,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--seit", default=None, help="Nur Sitzungen ab diesem Datum (YYYY-MM-DD)"
    )
    p.add_argument("--projekt", default=None, help="Nur dieser Projekt-Slug")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    p.add_argument("--projects-dir", default=str(DEFAULT_PROJECTS_DIR))
    p.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p.add_argument("--retros-dir", action="append", default=None)
    return p


def run(args: argparse.Namespace) -> int:
    projects_dir = Path(args.projects_dir).expanduser()
    sessions = discover_sessions(projects_dir, args.projekt)

    aggregate = []
    kaputt = 0
    for main_path, session_id, projekt in sessions:
        agg = _accumulate_session(main_path, session_id, projekt)
        # Kaputte-Zeilen-Zählung gilt für JEDE gelesene Sitzung, auch wenn sie
        # gleich danach per --seit wieder ausgeschlossen wird — sonst würde ein
        # Datumsfilter Lesefehler unsichtbar machen.
        kaputt += agg.kaputte_zeilen
        if args.seit and agg.datum and agg.datum < args.seit:
            continue
        if args.seit and not agg.datum:
            # Kein Datum ermittelbar (keine Assistant-Records) -> nicht einordenbar,
            # konservativ ausschliessen statt raten.
            continue
        aggregate.append(agg)

    ledger_rows = load_ledger(Path(args.ledger).expanduser())
    retros_dirs = args.retros_dir or DEFAULT_RETRO_DIRS
    retro_reports = load_reports(retros_dirs)

    zeilen, warnungen = build_zeilen(aggregate, ledger_rows, retro_reports)
    zeilen.sort(key=lambda z: (z.datum, z.session_kurz))

    if args.json:
        print(render_json(zeilen, warnungen, kaputt))
    else:
        print(render_text(zeilen, warnungen, kaputt))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
