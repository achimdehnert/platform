#!/usr/bin/env python3
"""Repariert die Befunde von memory_link_check — Namensangleichung und tote Verweise.

Die beiden Fundklassen sind EINE Reparatur, nicht zwei: Verweise zeigen teils auf
den Frontmatter-Namen (`[[feedback-foo]]`), teils auf den Dateinamen
(`[[feedback_foo]]`). Wer nur `name:` angleicht, macht die Verweise auf den alten
Namen tot; wer nur Verweise umhaengt, laesst die Ursache stehen. Deshalb laeuft
beides in einem Durchgang und in dieser Reihenfolge:

  1. Umbenennungs-Karte bauen: Frontmatter-Name -> Dateiname-Slug
  2. ALLE `[[..]]`-Verweise aufloesen (Karte + Praefix-Ergaenzung)
  3. erst danach `name:` im Frontmatter angleichen

Aufgeloest wird nur, was eindeutig ist. Mehrdeutige oder zielsose Verweise bleiben
unangetastet und werden gemeldet — ein Rateschritt waere hier teurer als eine
Handentscheidung (Realfall 2026-07-31: 3 von 32 Verweisen hatten kein Ziel, zwei
davon nannten nie angelegte Memories).

Trockenlauf ist Standard. `--apply` schreibt. Exit 0 = nichts zu tun, 1 = Aenderungen
(bzw. anwendbar), 2 = Werkzeugfehler.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
NAME_LINE = re.compile(r"^(name:[ \t]*)(.+?)[ \t]*$", re.MULTILINE)
PRAEFIXE = ("feedback_", "project_", "reference_")

# Eine Quelle fuer beide Werkzeuge — der Pruefer definiert, was Code ist, und der
# Reparierer haelt sich daran. Beide liegen im selben Verzeichnis, das beim
# direkten Aufruf ohnehin auf sys.path steht.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_link_check import CODE_FENCE, INLINE_CODE  # noqa: E402


def _code_bereiche(text: str) -> list[tuple[int, int]]:
    """Start/Ende aller Code-Bereiche — Bloecke und Inline-Spans."""
    return [
        (m.start(), m.end())
        for regex in (CODE_FENCE, INLINE_CODE)
        for m in regex.finditer(text)
    ]


def _in_code(pos: int, bereiche: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in bereiche)

# Verweise auf Nicht-Memories (Policies) sind kein Fund und werden nie umgeschrieben.
NICHT_MEMORY = {"evidence-discipline", "session-routing", "llm-routing", "adr-threshold"}


@dataclass
class Aenderung:
    datei: str
    art: str
    alt: str
    neu: str


def _frontmatter_ende(text: str) -> int:
    """Index hinter dem schliessenden --- des Frontmatters, sonst -1."""
    if not text.startswith("---"):
        return -1
    m = re.search(r"\n---[ \t]*(\n|$)", text[3:])
    return 3 + m.end() if m else -1


def _norm(s: str) -> str:
    return s.replace("-", "_").lower()


def baue_karte(mem: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Liefert (frontmatter_name -> slug, slug -> frontmatter_name)."""
    nach_slug: dict[str, str] = {}
    slug_name: dict[str, str] = {}
    for p in sorted(mem.glob("*.md")):
        if p.name == "MEMORY.md":
            continue
        kopf = p.read_text(encoding="utf-8", errors="replace")[:1200]
        ende = _frontmatter_ende(kopf)
        m = NAME_LINE.search(kopf[:ende] if ende > 0 else "")
        if not m:
            continue
        name = m.group(2)
        slug_name[p.stem] = name
        if name != p.stem:
            # Kollision: zwei Dateien beanspruchen denselben Frontmatter-Namen.
            # Dann ist die Zuordnung nicht eindeutig -> gar nicht aufloesen.
            nach_slug[name] = "" if name in nach_slug else p.stem
    return {k: v for k, v in nach_slug.items() if v}, slug_name


def loese_verweis(ziel: str, slugs: set[str], karte: dict[str, str]) -> str | None:
    """Eindeutiges Ziel eines toten Verweises, sonst None."""
    if ziel in slugs or ziel in NICHT_MEMORY:
        return None  # nicht tot bzw. bewusst kein Memory
    if ziel in karte:
        return karte[ziel]
    n = _norm(ziel)
    if n in slugs:
        return n
    for pre in PRAEFIXE:
        if not n.startswith(pre) and pre + n in slugs:
            return pre + n
    treffer = [s for s in slugs if s.endswith("_" + n)]
    return treffer[0] if len(treffer) == 1 else None


def repariere(mem: Path, apply: bool) -> tuple[list[Aenderung], list[tuple[str, str]]]:
    karte, slug_name = baue_karte(mem)
    slugs = {p.stem for p in mem.glob("*.md")}
    aenderungen: list[Aenderung] = []
    offen: list[tuple[str, str]] = []

    for p in sorted(mem.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        code = _code_bereiche(text)

        # (2) Verweise zuerst — solange die alten Frontmatter-Namen noch gelten.
        #
        # Ein Durchlauf mit Positionspruefung statt str.replace je Ziel: replace
        # traefe auch Vorkommen in Code-Bereichen, und die dokumentieren
        # Makro-Syntax (`[[clause:…]]`), sind also keine Verweise. Ausserdem
        # bleiben die Positionen gueltig, weil sub auf dem Originaltext arbeitet.
        gesehen: set[str] = set()

        def ersetze(m: re.Match) -> str:
            ziel = m.group(1)
            if _in_code(m.start(), code):
                return m.group(0)
            treffer = loese_verweis(ziel, slugs, karte)
            if treffer:
                if ziel not in gesehen:
                    aenderungen.append(Aenderung(p.name, "verweis", ziel, treffer))
                    gesehen.add(ziel)
                return f"[[{treffer}]]"
            if ziel not in slugs and ziel not in NICHT_MEMORY and ziel not in gesehen:
                offen.append((p.name, ziel))
                gesehen.add(ziel)
            return m.group(0)

        neu_text = WIKILINK.sub(ersetze, text)

        # (3) danach der Frontmatter-Name.
        if p.name != "MEMORY.md" and slug_name.get(p.stem, p.stem) != p.stem:
            ende = _frontmatter_ende(neu_text)
            if ende > 0:
                kopf, rest = neu_text[:ende], neu_text[ende:]
                kopf, n = NAME_LINE.subn(lambda m: m.group(1) + p.stem, kopf, count=1)
                if n:
                    neu_text = kopf + rest
                    aenderungen.append(
                        Aenderung(p.name, "name", slug_name[p.stem], p.stem)
                    )

        if apply and neu_text != text:
            p.write_text(neu_text, encoding="utf-8")

    return aenderungen, offen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path.home() / ".claude" / "projects"))
    ap.add_argument("--apply", action="store_true", help="schreiben statt nur melden")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    wurzel = Path(args.root).expanduser()
    if not wurzel.is_dir():
        print(f"FEHLER: kein Verzeichnis: {wurzel}", file=sys.stderr)
        return 2

    if (wurzel / "MEMORY.md").exists() or wurzel.name == "memory":
        verzeichnisse = [wurzel]
    else:
        verzeichnisse = sorted(p for p in wurzel.glob("*/memory") if p.is_dir())
    if not verzeichnisse:
        print(f"FEHLER: keine Memory-Verzeichnisse unter {wurzel}", file=sys.stderr)
        return 2

    ges_aend, ges_offen = 0, 0
    for mem in verzeichnisse:
        aenderungen, offen = repariere(mem, args.apply)
        ges_aend += len(aenderungen)
        ges_offen += len(offen)
        if not args.quiet and (aenderungen or offen):
            print(f"\n{mem}")
            for a in aenderungen:
                print(f"  {a.art:<8} {a.datei:<58} {a.alt}  ->  {a.neu}")
            for datei, ziel in offen:
                print(f"  {'OFFEN':<8} {datei:<58} [[{ziel}]] — kein eindeutiges Ziel")

    verb = "angewendet" if args.apply else "anwendbar"
    print(f"\n{len(verzeichnisse)} Verzeichnisse · {ges_aend} Reparaturen {verb} · "
          f"{ges_offen} offen (Handentscheidung)")
    return 1 if (ges_aend or ges_offen) else 0


if __name__ == "__main__":
    sys.exit(main())
