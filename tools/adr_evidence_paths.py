#!/usr/bin/env python3
"""adr_evidence_paths.py — prueft `implementation_evidence`-Pfade gegen das Dateisystem.

Hintergrund (platform#1289): ADR-158 trug `implementation_status: implemented` und vier
Evidence-Pfade unter `platform/packages/docs-agent/` — ein Verzeichnis, das seit
2026-04-23 in `_ARCHIVED/` liegt. Der ADR behauptete damit knapp drei Monate eine
Umsetzung, deren Belege ins Leere zeigten, ohne dass ein Check anschlug: `iil-adrfw
validate` prueft das Frontmatter-*Schema* (die Werte sind wohlgeformte Strings), das
ADR-264-Dead-Reference-Gate ist deployment-scoped, `adr_cross_repo_refs.sh` prueft das
Ref-*Format*.

Finding-Kategorien (deterministisch-strukturell, kein LLM):
  dead_path       Pfad-Kandidat, der im platform-Repo nicht existiert
  archived_path   dead_path, fuer den unter `_ARCHIVED/` ein Treffer liegt
                  (der haeufigste Fall — Datei wurde archiviert, ADR nicht nachgezogen)

Pfad-Heuristik — bewusst konservativ, Ziel sind 0 Falsch-Positive
(repo-health-rule-discipline). Ein Token wird nur geprueft, wenn ALLE gelten:

  1. Es enthaelt mindestens ein `/`. Nackte Dateinamen (`tasks.py`, `managers.py`)
     sind ohne Verzeichnis nicht aufloesbar und werden ignoriert.
  2. Es ist keine URL (`http://`, `https://`, `git@`) und kein Domain-artiges Token.
  3. Sein erstes Segment ist KEIN bekannter Repo-Name (`dev-hub/apps/...`,
     `promptfw/src/...`). Cross-Repo-Evidence ist im platform-CI nicht aufloesbar
     und ausdruecklich out-of-scope — sie wird gezaehlt und im Bericht ausgewiesen,
     nie als Finding gemeldet.
  4. Sein erstes Segment existiert als Top-Level-Eintrag im platform-Repo (bzw. der
     Pfad beginnt mit `platform/`, dann wird das Praefix gestrippt). Damit fallen
     Fremd-Repo-Pfade ohne Repo-Praefix (`src/authoringfw/analysis/`, `apps/billing/`)
     heraus, statt reihenweise Falsch-Positive zu erzeugen.
  5. Sein erstes Segment ist kein Teilspiegel-Verzeichnis (PARTIAL_MIRROR_ROOTS).
     `orchestrator_mcp/` liegt hier nur als Teilspiegel des extern laufenden Service
     (ADR-256); der vollstaendige Baum lebt in mcp-hub. Baseline-Lauf 2026-07-21:
     alle 5 Treffer dort (`agent_team/evaluator.py`, `audit_store.py`,
     `models/qa_log.py`, `models/cost_log.py`, `headless/`) existieren in
     mcp-hub@main — die Evidence stimmt, nur dieser Checkout kann sie nicht sehen.

Dokumentierter Rueckbau / dokumentierte Archivierung (kein Finding):
  Ein Eintrag, der neben dem alten Pfad ein EXISTIERENDES `_ARCHIVED/...`-Ziel nennt
  ("packages/docs-agent/ -> _ARCHIVED/packages/docs-agent/, seither Handpflege"), gilt
  als korrekt nachgezogen — der tote Pfad steht dort absichtlich als Historie. Zeigt
  der Archiv-Verweis selbst ins Leere, bleibt das Finding bestehen.

  Nicht jede Datei wird archiviert; manche werden geloescht. Dafuer greift dieselbe
  Logik ueber ein Marker-Wort (zurueckgebaut/entfernt/geloescht/TOT/...) plus einen
  belegenden Commit-Hash im selben Eintrag ("packages/platform-search/ am 2026-03-25
  als Orphan zurueckgebaut (4cd39b4)"). Beides zusammen ist der Beleg — ein Marker
  allein oder ein Hash allein genuegt nicht.

Whitelist fuer bekannte Alt-Funde:
  docs/adr/.adr-evidence-ignore — ein Eintrag pro Zeile, Format:

      packages/docs-agent/ in ADR-158

  (unterdrueckt Findings fuer diesen Pfad innerhalb dieses ADR; `#`-Kommentare und
  Leerzeilen erlaubt.)

SUGGEST-Modus (Default, repo-health-rule-discipline): Exit-Code IMMER 0.
`--gate` ist fuer die spaetere Promotion vorgesehen (Exit 1 bei Findings) — erst
aktivieren, wenn die Baseline sauber bzw. geparkt ist.

Usage:
    python3 tools/adr_evidence_paths.py [--adr-dir docs/adr] [--format human|github] [--gate]
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys
from dataclasses import dataclass

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
EVIDENCE_BLOCK_RE = re.compile(
    r"^implementation_evidence:\s*\n((?:[ \t]*-[ \t].*\n)+)", re.M
)
IGNORE_FILE_LINE_RE = re.compile(r"^(\S+)\s+in\s+(ADR-\d{3})\s*$")

# Ein Pfad-Kandidat: Zeichen, die in Pfaden vorkommen, mit mindestens einem "/".
PATH_CANDIDATE_RE = re.compile(r"[A-Za-z0-9_.@\-]*(?:/[A-Za-z0-9_.\-]+)+/?")
URL_PREFIXES = ("http://", "https://", "git@", "ssh://", "//")
# Tokens wie "schutztat.de/healthz" oder "iil.pet/kd/" sind URLs ohne Schema.
DOMAIN_RE = re.compile(r"\A[A-Za-z0-9\-]+\.(de|com|net|org|pet|io|dev|eu)(/|\Z)")

# Verzeichnisse, die in platform nur als Teilspiegel eines anderen Repos liegen.
# Ein fehlender Pfad darunter beweist nichts — die Quelle lebt woanders (ADR-256).
PARTIAL_MIRROR_ROOTS = {"orchestrator_mcp"}

# Dokumentierter Rueckbau: ein Marker-Wort UND ein belegender Commit-Hash im selben
# Eintrag. Nicht jede Datei wird archiviert — manche werden geloescht; dann gibt es
# kein _ARCHIVED/-Ziel, wohl aber den Commit. Bewusst KEINE git-Pruefung des Hashes:
# der CI-Checkout ist shallow (fetch-depth 1), eine cat-file-Pruefung wuerde dort
# anders ausfallen als lokal.
DOCUMENTED_REMOVAL_RE = re.compile(
    r"(?i)(zur(?:ü|ue|u)ckgebaut|entfernt|gel(?:ö|oe|o)scht|archiviert|TOT\b"
    r"|retired|removed)[^\n]*\b[0-9a-f]{7,40}\b"
)


@dataclass
class Finding:
    path: str  # repo-relativer Pfad der ADR-Datei
    line: int  # 1-basiert, Zeile des Evidence-Eintrags
    category: str  # dead_path | archived_path
    candidate: str  # der geprueftete Pfad
    message: str


def load_repo_names(repo_root: pathlib.Path) -> set[str]:
    """Bekannte Repo-Namen — erstes Pfad-Segment damit = Cross-Repo-Evidence.

    Quelle ist der kanonische Registry-Accessor `tools/registry_api.py` (ADR-234).
    Faellt er aus (fehlende View, Importfehler), bleibt die Menge leer und es filtert
    nur noch Regel 4 (Top-Level-Existenz) — das kostet die explizite Cross-Repo-
    Statistik, nicht die Korrektheit der Findings.

    Bewusst KEIN Fallback auf Geschwister-Verzeichnisse von `repo_root`: im CI-Checkout
    und in git-Worktrees zeigt der Parent nicht auf den github-Ordner, die Menge waere
    dort schlicht falsch (verifiziert 2026-07-21: lieferte Worktree-Namen).
    """
    api_path = pathlib.Path(__file__).resolve().parent / "registry_api.py"
    if not api_path.exists():
        return set()
    try:
        spec = importlib.util.spec_from_file_location("_registry_api", api_path)
        if spec is None or spec.loader is None:
            return set()
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_registry_api"] = mod
        spec.loader.exec_module(mod)
        names = {str(r) for r in mod.repos()}
    except Exception:  # Accessor ist optional — nie den Check daran scheitern lassen
        return set()
    # Der eigene Repo-Name ist KEIN Cross-Repo-Marker: "platform/..." wird gestrippt.
    names.discard(repo_root.name)
    return names


def load_ignore_pairs(adr_dir: pathlib.Path) -> set[tuple[str, str]]:
    """Liest .adr-evidence-ignore: {(Pfad, ADR-Nummer), ...}."""
    pairs: set[tuple[str, str]] = set()
    ignore_file = adr_dir / ".adr-evidence-ignore"
    if not ignore_file.exists():
        return pairs
    for raw in ignore_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = IGNORE_FILE_LINE_RE.match(line)
        if m:
            pairs.add((m.group(1), m.group(2)))
    return pairs


def extract_evidence(text: str) -> list[tuple[int, str]]:
    """(Zeilennummer, Eintragstext) je implementation_evidence-Listeneintrag."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return []
    # Trailing "\n" anfuegen: Gruppe 1 endet ohne Newline, sonst greift der
    # Listen-Block-Regex nicht, wenn implementation_evidence der letzte Key ist.
    fm = m.group(1) + "\n"
    block = EVIDENCE_BLOCK_RE.search(fm)
    if not block:
        return []
    # +2: die Frontmatter beginnt in Zeile 1 mit "---", fm-Zeile 1 ist Datei-Zeile 2.
    offset = fm[: block.start(1)].count("\n") + 2
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(block.group(1).splitlines()):
        entry = raw.strip()
        if not entry.startswith("-"):
            continue
        value = entry[1:].strip().strip('"').strip("'")
        if value:
            out.append((offset + i, value))
    return out


def expand_braces(entry: str) -> list[str]:
    """Brace-Listen aufloesen: `docs/x/{a,b}.md` → `docs/x/a.md`, `docs/x/b.md`.

    In dieser Codebase eine gaengige Kurzschreibweise (ADR-175 nutzt sie zweimal).
    Ohne Expansion bricht der Pfad-Kandidat vor der Klammer ab und der Check prueft
    nur das Elternverzeichnis — verifiziert 2026-07-21: drei tote Pfade unter
    `docs/governance/` blieben so unentdeckt. Nur eine Klammer-Ebene, das genuegt
    fuer alle real vorkommenden Faelle.
    """
    m = re.search(r"\{([^{}]+)\}", entry)
    if not m or "," not in m.group(1):
        return [entry]
    return [
        entry[: m.start()] + alt.strip() + entry[m.end() :]
        for alt in m.group(1).split(",")
        if alt.strip()
    ]


def path_candidates(entry: str) -> list[str]:
    """Pfad-artige Tokens eines Evidence-Eintrags (Heuristik-Regeln 1–2)."""
    found: list[str] = []
    tokens: list[str] = []
    for variant in expand_braces(entry):
        tokens.extend(PATH_CANDIDATE_RE.findall(variant))
    for raw in tokens:
        token = raw.strip().rstrip(",;.)")
        if not token or "/" not in token:
            continue
        if token.startswith(URL_PREFIXES) or DOMAIN_RE.match(token):
            continue
        if token.startswith("/"):  # absolute Server-Pfade sind nicht repo-relativ
            continue
        if token not in found:
            found.append(token)
    return found


def resolve(
    candidate: str, repo_root: pathlib.Path, repo_names: set[str]
) -> tuple[str, str | None]:
    """→ (verdict, geprueftes_ziel). verdict ∈ {ok, dead, archived, skipped_cross_repo,
    skipped_unknown_root, skipped_partial_mirror}."""
    rel = (
        candidate[len("platform/") :]
        if candidate.startswith("platform/")
        else candidate
    )
    rel = rel.strip("/")
    if not rel:
        return "skipped_unknown_root", None
    first = rel.split("/", 1)[0]
    if not candidate.startswith("platform/") and first in repo_names:
        return "skipped_cross_repo", None
    if first in PARTIAL_MIRROR_ROOTS:
        return "skipped_partial_mirror", None
    if not (repo_root / first).exists():
        return "skipped_unknown_root", None
    if (repo_root / rel).exists():
        return "ok", rel
    # ADR-Selbstverweise ohne vollen Dateinamen: "docs/adr/ADR-073" meint
    # docs/adr/ADR-073-repo-scope.md. Kein toter Pfad, sondern eine verkuerzte
    # Schreibweise — per Glob aufloesen statt als Finding melden.
    adr_ref = re.fullmatch(r"(.*/)?ADR-\d{3}", rel)
    if adr_ref:
        parent = (repo_root / rel).parent
        stem = rel.rsplit("/", 1)[-1]
        if parent.is_dir() and any(parent.glob(f"{stem}-*.md")):
            return "ok", rel
    archived = repo_root / "_ARCHIVED" / rel
    if archived.exists():
        return "archived", str(archived.relative_to(repo_root))
    # Auch _ARCHIVED/<rest> ohne fuehrendes Segment (packages/x → _ARCHIVED/packages/x
    # deckt der Fall oben ab; hier: docs/x → _ARCHIVED/x).
    tail = rel.split("/", 1)[1] if "/" in rel else rel
    archived_tail = repo_root / "_ARCHIVED" / tail
    if archived_tail.exists():
        return "archived", str(archived_tail.relative_to(repo_root))
    return "dead", rel


def run(
    adr_dir: pathlib.Path, repo_root: pathlib.Path
) -> tuple[list[Finding], dict[str, int]]:
    findings: list[Finding] = []
    stats = {
        "adrs_with_evidence": 0,
        "entries": 0,
        "candidates": 0,
        "checked": 0,
        "skipped_cross_repo": 0,
        "skipped_unknown_root": 0,
        "skipped_partial_mirror": 0,
        "ignored": 0,
        "documented_archival": 0,
    }
    repo_names = load_repo_names(repo_root)
    ignore_pairs = load_ignore_pairs(adr_dir)

    for adr in sorted(adr_dir.glob("ADR-*.md")):
        text = adr.read_text(encoding="utf-8", errors="replace")
        entries = extract_evidence(text)
        if not entries:
            continue
        stats["adrs_with_evidence"] += 1
        adr_num = adr.name[:7]  # "ADR-158"
        for line_no, entry in entries:
            stats["entries"] += 1
            candidates = path_candidates(entry)
            # Ein Eintrag, der die Archivierung selbst dokumentiert ("X → _ARCHIVED/X,
            # Commit abc, seither Handpflege"), ist kein Defekt, sondern die gewuenschte
            # Schreibweise — der tote Pfad steht dort absichtlich als Historie. Erkannt
            # an einem existierenden _ARCHIVED/-Ziel im selben Eintrag.
            if any(
                c.lstrip("/").startswith("_ARCHIVED/")
                and (repo_root / c.lstrip("/")).exists()
                for c in candidates
            ) or DOCUMENTED_REMOVAL_RE.search(entry):
                stats["documented_archival"] += 1
                continue
            for candidate in candidates:
                stats["candidates"] += 1
                verdict, target = resolve(candidate, repo_root, repo_names)
                if verdict.startswith("skipped_"):
                    stats[verdict] += 1
                    continue
                stats["checked"] += 1
                if verdict == "ok":
                    continue
                if (candidate, adr_num) in ignore_pairs or (
                    candidate.rstrip("/"),
                    adr_num,
                ) in ignore_pairs:
                    stats["ignored"] += 1
                    continue
                if verdict == "archived":
                    findings.append(
                        Finding(
                            path=str(adr.relative_to(repo_root)),
                            line=line_no,
                            category="archived_path",
                            candidate=candidate,
                            message=(
                                f"implementation_evidence verweist auf '{candidate}' — "
                                f"existiert nicht mehr, liegt unter '{target}'. "
                                f"Evidence-Pfad oder implementation_status nachziehen."
                            ),
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            path=str(adr.relative_to(repo_root)),
                            line=line_no,
                            category="dead_path",
                            candidate=candidate,
                            message=(
                                f"implementation_evidence verweist auf '{candidate}' — "
                                f"im Repo nicht vorhanden."
                            ),
                        )
                    )
    return findings, stats


def emit(findings: list[Finding], stats: dict[str, int], fmt: str) -> None:
    if fmt == "github":
        for f in findings:
            print(
                f"::warning file={f.path},line={f.line},"
                f"title=adr-evidence-path ({f.category})::{f.message}"
            )
        if findings:
            counts: dict[str, int] = {}
            for f in findings:
                counts[f.category] = counts.get(f.category, 0) + 1
            summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            print(
                f"::warning title=adr-evidence-paths summary::"
                f"{len(findings)} Finding(s): {summary} "
                f"(geprueft: {stats['checked']} Pfade in {stats['adrs_with_evidence']} ADRs)"
            )
        else:
            print(
                f"✓ Keine toten Evidence-Pfade "
                f"({stats['checked']} geprueft, {stats['skipped_cross_repo']} cross-repo "
                f"uebersprungen)."
            )
        return

    for f in findings:
        print(f"{f.path}:{f.line} [{f.category}] {f.message}")
    print(
        "\n"
        f"ADRs mit evidence : {stats['adrs_with_evidence']}\n"
        f"Eintraege         : {stats['entries']}\n"
        f"Pfad-Kandidaten   : {stats['candidates']}\n"
        f"  geprueft        : {stats['checked']}\n"
        f"  cross-repo skip : {stats['skipped_cross_repo']}\n"
        f"  fremder Root    : {stats['skipped_unknown_root']}\n"
        f"  Teilspiegel     : {stats['skipped_partial_mirror']}\n"
        f"  via ignore-Datei: {stats['ignored']}\n"
        f"Archiv dokumentiert: {stats['documented_archival']} Eintraege\n"
        f"Findings          : {len(findings)}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adr-dir", default="docs/adr")
    ap.add_argument("--format", choices=["human", "github"], default="human")
    ap.add_argument(
        "--gate",
        action="store_true",
        help="Exit 1 bei Findings (Promotion; Default ist SUGGEST/immer 0)",
    )
    args = ap.parse_args(argv)

    adr_dir = pathlib.Path(args.adr_dir).resolve()
    if not adr_dir.is_dir():
        print(f"ADR-Verzeichnis nicht gefunden: {adr_dir}", file=sys.stderr)
        return 2
    repo_root = pathlib.Path.cwd().resolve()

    findings, stats = run(adr_dir, repo_root)
    emit(findings, stats, args.format)
    return 1 if (args.gate and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
