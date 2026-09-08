#!/usr/bin/env python3
"""tools/adr_allocate.py — Merge-Time-Nummernvergabe fuer ADR-Entwuerfe (ADR-228).

ADR-228 verschiebt die ADR-Nummernvergabe von der Autorenzeit auf die Merge-Zeit:
Ein ADR-PR legt eine Entwurfsdatei `docs/adr/ADR-DRAFT-<slug>.md` mit dem Platzhalter
`id: ADR-000` an. Dieses Werkzeug vergibt kurz vor dem Merge (Autor-getrieben, siehe
ADR-228 OQ-1 — keine Merge-Queue im Repo) die naechste freie Nummer:

  1. findet alle `docs/adr/ADR-DRAFT-*.md`
  2. ermittelt die naechste freie Nummer ueber `scripts/adr_next_number.py`
     (EINE Quelle — die Logik wird hier nicht dupliziert)
  3. benennt die Datei per `git mv` um (Historie bleibt erhalten)
  4. ersetzt im Dateiinhalt `id: ADR-000` -> `id: ADR-NNN`, die H1
     `# ADR-DRAFT: ...` -> `# ADR-NNN: ...` und uebrige Selbstverweise
     (z.B. ein Kommentarblock "ADR-DRAFT — ...")
  5. regeneriert den Index (`scripts/gen_adr_index.py`)

Mehrere Entwuerfe in einem Lauf werden der Reihe nach abgearbeitet (sortiert
nach Dateiname = Slug, siehe ADR-228 REC-4) — jeder bekommt eine eigene, echte
freie Nummer, weil nach jeder Umbenennung neu gescannt wird.

Trockenlauf ist Vorgabe: ohne `--apply` wird NICHTS geschrieben, nur angezeigt,
was passieren wuerde. Kein Entwurf gefunden -> Exit 0 (kein Fehler).

Usage:
    python3 tools/adr_allocate.py                 # Trockenlauf
    python3 tools/adr_allocate.py --apply          # schreibt wirklich
    python3 tools/adr_allocate.py --adr-dir <pfad> --apply   # abweichendes ADR-Verzeichnis (Tests)
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR_DEFAULT = REPO_ROOT / "docs" / "adr"
NEXT_NUMBER_SCRIPT = REPO_ROOT / "scripts" / "adr_next_number.py"
GEN_INDEX_SCRIPT = REPO_ROOT / "scripts" / "gen_adr_index.py"

DRAFT_RE = re.compile(r"^ADR-DRAFT-(?P<slug>.+)\.md$")
ID_PLACEHOLDER_RE = re.compile(r"(?m)^id:\s*ADR-000\s*$")
H1_DRAFT_RE = re.compile(r"(?m)^#\s*ADR-DRAFT:")


@dataclass
class Allocation:
    """Ergebnis einer einzelnen Nummernvergabe."""

    slug: str
    old_path: Path
    new_path: Path
    number: int


def _load_next_number_module(script: Path = NEXT_NUMBER_SCRIPT) -> ModuleType:
    """Laedt scripts/adr_next_number.py als Modul (kein Package, daher spec-Loader).

    EINE Quelle fuer die Nummernlogik — wird hier bewusst importiert statt
    neu implementiert (Vorgabe des Auftrags).
    """
    spec = importlib.util.spec_from_file_location("adr_next_number", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Konnte {script} nicht als Modul laden.")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adr_next_number"] = mod
    spec.loader.exec_module(mod)
    return mod


def find_drafts(adr_dir: Path) -> list[Path]:
    """Findet alle Entwurfsdateien, deterministisch sortiert nach Dateiname/Slug."""
    return sorted(adr_dir.glob("ADR-DRAFT-*.md"))


def _rewrite_content(text: str, number: int) -> str:
    """Ersetzt id-Platzhalter, H1 und uebrige Selbstverweise ADR-DRAFT -> ADR-NNN."""
    num_str = f"ADR-{number:03d}"
    text = ID_PLACEHOLDER_RE.sub(f"id: {num_str}", text)
    text = H1_DRAFT_RE.sub(f"# {num_str}:", text)
    # Uebrige Selbstverweise (z.B. Kommentarblock "ADR-DRAFT — ...", Dateiname
    # in Prosa erwaehnt) — nach den spezifischeren Ersetzungen oben, damit die
    # bereits behandelten Stellen nicht doppelt getroffen werden.
    text = text.replace("ADR-DRAFT", num_str)
    return text


def _git_mv(old_path: Path, new_path: Path, repo_root: Path) -> None:
    """Umbenennen — per `git mv`, wenn moeglich, sonst schlicht per Rename.

    `git mv` haelt die Historie und ist deshalb der Normalfall. Es scheitert
    aber, sobald die Datei nicht unter Versionskontrolle steht: bei einem Lauf
    gegen ein Temp-Verzeichnis (`--adr-dir /tmp/...`) und bei einer Datei, die
    noch nicht `git add`-ed ist. Beides sind legitime Aufrufe — der erste ist
    genau der Ende-zu-Ende-Probelauf, mit dem dieses Werkzeug geprueft wird.

    Ohne den Rueckfall bricht der Allokator dort mit einem nackten
    CalledProcessError ab (real passiert am 2026-09-08). Ein Werkzeug, das nur
    im Idealfall laeuft, ist im Pruefpfad wertlos.
    """
    ergebnis = subprocess.run(
        ["git", "mv", str(old_path), str(new_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if ergebnis.returncode == 0:
        return
    # Kein git-Kontext oder Datei untracked: schlicht umbenennen. Der Inhalt
    # zaehlt, die Historie ist hier ein Nice-to-have.
    old_path.rename(new_path)


def allocate_drafts(
    adr_dir: Path,
    repo_root: Path | None = None,
    apply: bool = False,
    next_number_script: Path = NEXT_NUMBER_SCRIPT,
) -> list[Allocation]:
    """Vergibt Nummern an alle Entwuerfe in `adr_dir`.

    Trockenlauf (apply=False): liest nur, schreibt nichts, ruft kein `git mv` auf.
    Bei apply=True wird nach JEDER Umbenennung neu gescannt, damit zwei Entwuerfe
    im selben Lauf garantiert verschiedene, wirklich freie Nummern bekommen.
    """
    if repo_root is None:
        repo_root = adr_dir.parent.parent

    ann = _load_next_number_module(next_number_script)
    results: list[Allocation] = []

    for draft in find_drafts(adr_dir):
        m = DRAFT_RE.match(draft.name)
        if not m:
            continue  # kann nicht passieren (glob-Pattern deckt es ab), defensiv
        slug = m.group("slug")

        mapping = ann.scan_adr_dir(adr_dir)
        number = ann.get_next_free(mapping)
        new_path = draft.parent / f"ADR-{number:03d}-{slug}.md"

        if apply:
            _git_mv(draft, new_path, repo_root)
            text = new_path.read_text(encoding="utf-8")
            new_path.write_text(_rewrite_content(text, number), encoding="utf-8")

        results.append(
            Allocation(slug=slug, old_path=draft, new_path=new_path, number=number)
        )

    return results


def _run_gen_index(adr_dir: Path) -> None:
    """Regeneriert INDEX.md + index.json nach der Vergabe.

    Haerte ist hier kontextabhaengig, und das mit Absicht:

    * Laeuft der Allokator gegen das ECHTE `docs/adr` des Repos, ist ein
      fehlgeschlagener Index ein Fehler — ein vergebener ADR ohne Indexzeile
      faellt sonst gleich am naechsten Pflicht-Gate auf (`ADR index freshness`),
      und zwar dem naechsten Menschen, nicht dem Verursacher.
    * Laeuft er gegen ein fremdes Verzeichnis (`--adr-dir /tmp/...`, Tests,
      Ende-zu-Ende-Probelauf), fehlt dort die Repo-Struktur, die der
      Index-Erzeuger erwartet. Ein Abbruch macht dann genau den Pruefpfad
      unbenutzbar, fuer den das Werkzeug geprueft werden soll — real passiert
      am 2026-09-08.
    """
    ergebnis = subprocess.run(
        [sys.executable, str(GEN_INDEX_SCRIPT), "--adr-dir", str(adr_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode == 0:
        if ergebnis.stdout:
            print(ergebnis.stdout.rstrip())
        return
    if adr_dir.resolve() == ADR_DIR_DEFAULT.resolve():
        print(ergebnis.stdout or "", end="")
        print(ergebnis.stderr or "", end="", file=sys.stderr)
        raise SystemExit(
            "Index-Erzeugung fehlgeschlagen — die Nummer ist vergeben, der Index "
            "nicht nachgezogen. Fix: python3 scripts/gen_adr_index.py"
        )
    print(
        f"Hinweis: Index nicht erzeugt (fremdes ADR-Verzeichnis {adr_dir}) — "
        "Umbenennung und Inhalt sind trotzdem geschrieben."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adr-dir", default=str(ADR_DIR_DEFAULT), help="Pfad zu docs/adr")
    ap.add_argument(
        "--apply", action="store_true", help="Wirklich schreiben (sonst Trockenlauf)"
    )
    args = ap.parse_args()

    adr_dir = Path(args.adr_dir)
    if not adr_dir.is_dir():
        print(f"FEHLER: ADR-Verzeichnis nicht gefunden: {adr_dir}", file=sys.stderr)
        return 1

    drafts = find_drafts(adr_dir)
    if not drafts:
        print("Keine ADR-Entwuerfe (ADR-DRAFT-*.md) gefunden — nichts zu tun.")
        return 0

    mode = "APPLY" if args.apply else "TROCKENLAUF"
    print(f"=== ADR-Allokator ({mode}) ===")

    results = allocate_drafts(adr_dir, apply=args.apply)
    for r in results:
        arrow = "->" if args.apply else "-> (geplant, nicht geschrieben)"
        print(
            f"  {r.old_path.name} {arrow} {r.new_path.name}  (id: ADR-{r.number:03d})"
        )

    if args.apply:
        sys.stdout.flush()  # eigene Ausgabe vor dem Subprozess-Output sichtbar machen
        _run_gen_index(adr_dir)
        print(f"✓ {len(results)} Entwurf/Entwuerfe vergeben, Index regeneriert.")
    else:
        print(
            f"({len(results)} Entwurf/Entwuerfe wuerden vergeben — "
            "erneut mit --apply ausfuehren, um zu schreiben.)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
