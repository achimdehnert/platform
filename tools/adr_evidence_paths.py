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

Typisierte Belegzeilen (KONZ-platform-065, Amendment zu ADR-138 §2.4):
  Eine Zeile, die mit einem der vier Typen beginnt, ist ein Vertrag — der Rest der
  Zeile (nach dem ersten Token) ist freier Kommentar:

      path: tools/adr_evidence_paths.py          existiert im Repo (dead_path/archived_path)
      path: dev-hub:apps/adr_lifecycle/tasks.py  Repo-Praefix = cross-repo, wird gezaehlt,
                                                 nie geprueft (prueft nur dessen CI)
      gate: claim-before-cheapest-check          Slug in docs/governance/gates/{gates,declined,
                                                 widerrufen}/<slug>.json (unknown_gate);
                                                 kandidaten/ zaehlt NICHT — ein Kandidat ist
                                                 noch kein Gate
      test: tools/tests/test_x.py                Datei existiert (missing_test) — wird NIE
                                                 ausgefuehrt (Lieferketten-Grenze, KONZ L10)
      pr: platform#1643                          Formatpruefung `#N`, `repo#N`, `owner/repo#N`
                                                 (malformed_pr) — kein API-Aufruf

  Untypisierte Zeilen bleiben gueltig (Bestandsschutz) und laufen weiter durch die
  Pfad-Heuristik oben; sie zaehlen als "prosa". Je ADR wird `typisiert / prosa`
  ausgewiesen — das ist die Form-Quote, die dem Leser sagt, wie belastbar das ADR ist.
  Ein typisierter Pfad umgeht Heuristik-Regel 4 (Top-Level-Existenz): wer `path:`
  schreibt, behauptet den Pfad — ein unbekannter Root ist dann ein toter Pfad, kein
  Skip. Regel 3 (Repo-Praefix ohne Doppelpunkt, `dev-hub/apps/...`) und Regel 5
  (Teilspiegel) gelten weiter.

Pilotliste: docs/adr/.adr-evidence-pilot — ein ADR je Zeile (`ADR-174`), `#`-Kommentare
  erlaubt. Auf der Pilotliste ist ein Finding ROT (`--gate-pilot` → Exit 1, im
  github-Format `::error`), und ein Pilot-ADR ohne typisierte Zeile ist selbst ein
  Finding (pilot_no_typed_evidence). Ausserhalb der Liste bleibt alles SUGGEST.

SUGGEST-Modus (Default, repo-health-rule-discipline): Exit-Code IMMER 0.
`--gate` ist fuer die spaetere Promotion vorgesehen (Exit 1 bei JEDEM Finding) — erst
aktivieren, wenn die Baseline sauber bzw. geparkt ist. `--gate-pilot` ist die auf die
Pilotliste verengte Promotion (KONZ-065 §2).

Usage:
    python3 tools/adr_evidence_paths.py [--adr-dir docs/adr] [--format human|github]
                                        [--gate] [--gate-pilot]
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

# Typisierte Belegzeilen (KONZ-065): `<typ>: <token> [freier Kommentar]`.
EVIDENCE_TYPES = ("path", "gate", "test", "pr")
TYPED_LINE_RE = re.compile(r"^(path|gate|test|pr):\s*(\S+)(?:\s+.*)?$", re.S)
# Repo-Praefix vor dem Pfad: `dev-hub:apps/x.py` oder `iilgmbh/shared-ci:.github/x.yml`.
CROSS_REPO_PREFIX_RE = re.compile(r"^((?:[A-Za-z0-9_.\-]+/)?[A-Za-z0-9_.\-]+):(.+)$")
PR_REF_RE = re.compile(r"^(?:(?:[A-Za-z0-9_.\-]+/)?[A-Za-z0-9_.\-]+)?#\d+$")
GATE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")  # wie tools/gate_registry.py
GATES_REL = pathlib.Path("docs") / "governance" / "gates"
# Abschnitte, in denen ein Slug als "existiert" gilt. `kandidaten/` gehoert nicht dazu:
# ein Kandidat ist noch kein Gate, ein ADR darf ihn nicht als Beleg fuehren.
GATE_SECTIONS = ("gates", "declined", "widerrufen")
PILOT_FILE = ".adr-evidence-pilot"
PILOT_LINE_RE = re.compile(r"^(ADR-\d{3})\b")

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
    category: (
        str  # dead_path | archived_path | unknown_gate | missing_test | malformed_pr
    )
    #                | pilot_no_typed_evidence
    candidate: str  # der geprueftete Pfad / Slug / PR-Verweis
    message: str
    pilot: bool = False  # ADR steht auf der Pilotliste → Finding ist rot (--gate-pilot)


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


def load_pilot(adr_dir: pathlib.Path) -> set[str]:
    """Liest .adr-evidence-pilot: {"ADR-174", ...}. Fehlt die Datei: kein Pilot."""
    pilot: set[str] = set()
    pilot_file = adr_dir / PILOT_FILE
    if not pilot_file.exists():
        return pilot
    for raw in pilot_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = PILOT_LINE_RE.match(line)
        if m:
            pilot.add(m.group(1))
    return pilot


def parse_typed(entry: str) -> tuple[str, str] | None:
    """`path: tools/x.py — Kommentar` → ("path", "tools/x.py"); Prosa → None.

    Nur das erste Token nach dem Typ ist Vertrag, der Rest freier Kommentar.
    Ein Typ ausserhalb der vier (`metric:`) ist keine typisierte Zeile — er zaehlt
    als Prosa, bis eine Stufe 2 ihn definiert (KONZ-065 §1).
    """
    m = TYPED_LINE_RE.match(entry.strip())
    if not m:
        return None
    return m.group(1), m.group(2).rstrip(",;.:)")


def gate_exists(slug: str, repo_root: pathlib.Path) -> bool:
    """Slug als Einzeldatei in einem der zaehlenden Registry-Abschnitte (B4: die
    Registry ist die Wahrheit, das ADR zeigt nur auf sie)."""
    if not GATE_SLUG_RE.match(slug):
        return False
    return any(
        (repo_root / GATES_REL / section / f"{slug}.json").is_file()
        for section in GATE_SECTIONS
    )


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
    candidate: str,
    repo_root: pathlib.Path,
    repo_names: set[str],
    *,
    typed: bool = False,
) -> tuple[str, str | None]:
    """→ (verdict, geprueftes_ziel). verdict ∈ {ok, dead, archived, skipped_cross_repo,
    skipped_unknown_root, skipped_partial_mirror}.

    `typed=True` (Zeile `path:`/`test:`): ein Repo-Praefix mit Doppelpunkt ist
    cross-repo; ein unbekannter Top-Level-Root ist KEIN Skip, sondern tot — der Autor
    hat den Pfad ausdruecklich behauptet.
    """
    if typed and CROSS_REPO_PREFIX_RE.match(candidate):
        return "skipped_cross_repo", None
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
    if not typed and not (repo_root / first).exists():
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


def _check_typed(
    kind: str,
    token: str,
    *,
    adr_rel: str,
    adr_num: str,
    line_no: int,
    repo_root: pathlib.Path,
    repo_names: set[str],
    ignore_pairs: set[tuple[str, str]],
    stats: dict,
) -> Finding | None:
    """Eine typisierte Zeile pruefen. Gibt das Finding zurueck oder None."""
    if kind == "pr":
        if PR_REF_RE.match(token):
            return None
        return Finding(
            path=adr_rel,
            line=line_no,
            category="malformed_pr",
            candidate=token,
            message=(
                f"implementation_evidence `pr: {token}` — erwartet `#N`, `repo#N` "
                f"oder `owner/repo#N`."
            ),
        )
    if kind == "gate":
        if gate_exists(token, repo_root):
            return None
        return Finding(
            path=adr_rel,
            line=line_no,
            category="unknown_gate",
            candidate=token,
            message=(
                f"implementation_evidence `gate: {token}` — kein Eintrag unter "
                f"{GATES_REL.as_posix()}/{{{','.join(GATE_SECTIONS)}}}/. "
                f"Slug pruefen (kandidaten/ zaehlt nicht)."
            ),
        )
    # path / test
    stats["candidates"] += 1
    verdict, target = resolve(token, repo_root, repo_names, typed=True)
    if verdict.startswith("skipped_"):
        stats[verdict] += 1
        if verdict == "skipped_cross_repo":
            stats["typed_cross_repo"] += 1
        return None
    stats["checked"] += 1
    if verdict == "ok":
        return None
    if (token, adr_num) in ignore_pairs or (token.rstrip("/"), adr_num) in ignore_pairs:
        stats["ignored"] += 1
        return None
    where = (
        f"existiert nicht mehr, liegt unter '{target}'"
        if verdict == "archived"
        else "im Repo nicht vorhanden"
    )
    if kind == "test":
        return Finding(
            path=adr_rel,
            line=line_no,
            category="missing_test",
            candidate=token,
            message=f"implementation_evidence `test: {token}` — {where}.",
        )
    return Finding(
        path=adr_rel,
        line=line_no,
        category="archived_path" if verdict == "archived" else "dead_path",
        candidate=token,
        message=(
            f"implementation_evidence `path: {token}` — {where}. "
            f"Evidence-Pfad oder implementation_status nachziehen."
        ),
    )


def run(adr_dir: pathlib.Path, repo_root: pathlib.Path) -> tuple[list[Finding], dict]:
    """→ (findings, stats). stats traegt neben den Zaehlern `per_adr`
    ({ADR-NNN: {"typed": n, "prosa": m}}) und `pilot` (sortierte Pilotliste)."""
    findings: list[Finding] = []
    stats: dict = {
        "adrs_with_evidence": 0,
        "entries": 0,
        "typed": 0,
        "prosa": 0,
        "typed_cross_repo": 0,
        "candidates": 0,
        "checked": 0,
        "skipped_cross_repo": 0,
        "skipped_unknown_root": 0,
        "skipped_partial_mirror": 0,
        "ignored": 0,
        "documented_archival": 0,
        "per_adr": {},
        "pilot": [],
    }
    repo_names = load_repo_names(repo_root)
    ignore_pairs = load_ignore_pairs(adr_dir)
    pilot = load_pilot(adr_dir)
    stats["pilot"] = sorted(pilot)

    for adr in sorted(adr_dir.glob("ADR-*.md")):
        text = adr.read_text(encoding="utf-8", errors="replace")
        entries = extract_evidence(text)
        adr_num = adr.name[:7]  # "ADR-158"
        adr_rel = str(adr.relative_to(repo_root))
        in_pilot = adr_num in pilot
        if not entries and not in_pilot:
            continue
        if entries:
            stats["adrs_with_evidence"] += 1
        counts = {"typed": 0, "prosa": 0}
        stats["per_adr"][adr_num] = counts
        for line_no, entry in entries:
            stats["entries"] += 1
            typed = parse_typed(entry)
            if typed:
                counts["typed"] += 1
                stats["typed"] += 1
                finding = _check_typed(
                    *typed,
                    adr_rel=adr_rel,
                    adr_num=adr_num,
                    line_no=line_no,
                    repo_root=repo_root,
                    repo_names=repo_names,
                    ignore_pairs=ignore_pairs,
                    stats=stats,
                )
                if finding:
                    finding.pilot = in_pilot
                    findings.append(finding)
                continue
            counts["prosa"] += 1
            stats["prosa"] += 1
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
                            path=adr_rel,
                            line=line_no,
                            category="archived_path",
                            candidate=candidate,
                            message=(
                                f"implementation_evidence verweist auf '{candidate}' — "
                                f"existiert nicht mehr, liegt unter '{target}'. "
                                f"Evidence-Pfad oder implementation_status nachziehen."
                            ),
                            pilot=in_pilot,
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            path=adr_rel,
                            line=line_no,
                            category="dead_path",
                            candidate=candidate,
                            message=(
                                f"implementation_evidence verweist auf '{candidate}' — "
                                f"im Repo nicht vorhanden."
                            ),
                            pilot=in_pilot,
                        )
                    )
        # Pilot-Vertrag: ein Pilot-ADR ohne eine einzige typisierte Zeile hat den
        # Vertrag nicht angenommen — das ist ein Finding, kein Zaehlerstand.
        if in_pilot and counts["typed"] == 0:
            findings.append(
                Finding(
                    path=adr_rel,
                    line=1,
                    category="pilot_no_typed_evidence",
                    candidate=adr_num,
                    message=(
                        f"{adr_num} steht in {PILOT_FILE}, traegt aber keine "
                        f"typisierte Belegzeile (path:/gate:/test:/pr:)."
                    ),
                    pilot=True,
                )
            )
    return findings, stats


def _pilot_quote(stats: dict) -> str:
    """`ADR-174 typisiert 5 / prosa 1 · ADR-226 ...` fuer die Pilotliste."""
    return " · ".join(
        f"{adr} typisiert {stats['per_adr'].get(adr, {}).get('typed', 0)}"
        f" / prosa {stats['per_adr'].get(adr, {}).get('prosa', 0)}"
        for adr in stats["pilot"]
    )


def emit(findings: list[Finding], stats: dict, fmt: str) -> None:
    pilot_findings = [f for f in findings if f.pilot]
    if fmt == "github":
        for f in findings:
            level = "error" if f.pilot else "warning"
            print(
                f"::{level} file={f.path},line={f.line},"
                f"title=adr-evidence-path ({f.category})::{f.message}"
            )
        if findings:
            counts: dict[str, int] = {}
            for f in findings:
                counts[f.category] = counts.get(f.category, 0) + 1
            summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            level = "error" if pilot_findings else "warning"
            print(
                f"::{level} title=adr-evidence-paths summary::"
                f"{len(findings)} Finding(s), davon {len(pilot_findings)} auf der "
                f"Pilotliste: {summary} "
                f"(geprueft: {stats['checked']} Pfade in {stats['adrs_with_evidence']} ADRs)"
            )
        else:
            print(
                f"✓ Keine toten Evidence-Pfade "
                f"({stats['checked']} geprueft, {stats['skipped_cross_repo']} cross-repo "
                f"uebersprungen)."
            )
        if stats["pilot"]:
            print(
                f"::notice title=adr-evidence-pilot (KONZ-065)::{_pilot_quote(stats)}"
            )
        return

    for f in findings:
        flag = " PILOT" if f.pilot else ""
        print(f"{f.path}:{f.line} [{f.category}]{flag} {f.message}")
    print(
        "\n"
        f"ADRs mit evidence : {stats['adrs_with_evidence']}\n"
        f"Eintraege         : {stats['entries']}\n"
        f"  typisiert       : {stats['typed']} (davon cross-repo {stats['typed_cross_repo']})\n"
        f"  prosa           : {stats['prosa']}\n"
        f"Pfad-Kandidaten   : {stats['candidates']}\n"
        f"  geprueft        : {stats['checked']}\n"
        f"  cross-repo skip : {stats['skipped_cross_repo']}\n"
        f"  fremder Root    : {stats['skipped_unknown_root']}\n"
        f"  Teilspiegel     : {stats['skipped_partial_mirror']}\n"
        f"  via ignore-Datei: {stats['ignored']}\n"
        f"Archiv dokumentiert: {stats['documented_archival']} Eintraege\n"
        f"Findings          : {len(findings)} (Pilot: {len(pilot_findings)})"
    )
    if stats["pilot"]:
        print(f"Pilotliste ({len(stats['pilot'])}): {_pilot_quote(stats)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adr-dir", default="docs/adr")
    ap.add_argument("--format", choices=["human", "github"], default="human")
    ap.add_argument(
        "--gate",
        action="store_true",
        help="Exit 1 bei Findings (Promotion; Default ist SUGGEST/immer 0)",
    )
    ap.add_argument(
        "--gate-pilot",
        action="store_true",
        help=(
            f"Exit 1 nur bei Findings in ADRs aus {PILOT_FILE} (KONZ-065 Pilot); "
            "alles andere bleibt SUGGEST"
        ),
    )
    args = ap.parse_args(argv)

    adr_dir = pathlib.Path(args.adr_dir).resolve()
    if not adr_dir.is_dir():
        print(f"ADR-Verzeichnis nicht gefunden: {adr_dir}", file=sys.stderr)
        return 2
    repo_root = pathlib.Path.cwd().resolve()

    findings, stats = run(adr_dir, repo_root)
    emit(findings, stats, args.format)
    if args.gate and findings:
        return 1
    if args.gate_pilot and any(f.pilot for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
