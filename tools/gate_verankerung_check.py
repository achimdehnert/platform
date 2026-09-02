#!/usr/bin/env python3
"""gate_verankerung_check.py — darf dieses Gate ueberhaupt verankert werden?

Ein Gate, das in `docs/governance/gate-registry.json` steht, gilt im ganzen Loop
als **gebaut**: `retro_kpis.py` nimmt seinen Slug aus der GATE-PFLICHT-Liste,
`gate_wirkung.py` fuehrt ihn im Laengsschnitt, der Session-Start meldet ihn als
Schranke. Der Eintrag ist damit eine Behauptung ueber Wirkung — und bis heute
konnte sie jeder aufstellen, der eine Zeile JSON schreibt.

**Gemessene Ausgangslage (platform#2374, #2678, Stand 2026-09-02): 14 von 33
Gates sind rueckfaellig.** Ein Gate ohne Positivkontrolle ist ein Melder, der nie
beweisen musste, dass er etwas finden kann; ein Gate ohne Messpunkt ist eine
Behauptung, deren Widerlegung niemand einsammelt. Dieser Pruefer verlangt vor der
Verankerung drei Dinge — und nur diese drei:

  **Drill**          `drill` zeigt auf eine existierende Testdatei (fremd
                     verankerte Gates: `drill` + `ref`, weil der Lauf in der CI
                     des Ziel-Repos stattfindet — dieselbe Grenze wie in
                     `gate_drill_check.ist_fremd`).
  **Positivkontrolle** `positivkontrolle: {ref, datum}` — der Beleg, dass das Gate
                     den Fall, den es verhindern soll, auch WIRKLICH getroffen
                     hat (roter Lauf am Realfall, gefangener Fixture-Fall).
  **Messpunkt**      `slug` in der Form, die `gate_wirkung.py` in Retro-Tabellen
                     und Frontmatter wiederfindet, plus ein ISO-Datum in `built`
                     (bzw. `revised`) als Nullpunkt der Messung.

**Warum `positivkontrolle` ein neues Feld ist und `faengt` nicht reicht.** Die
Registry kennt bereits `faengt` (Faelle + `probe`), ausgewertet von
`gate_namensdeckung.py`. Dessen eigener Kopf zieht die Grenze woertlich: „Er misst
NICHT, ob der Test den Fall wirklich abfaengt — dafuer braeuchte es einen
Mutationstest." `faengt` belegt, dass der namensgebende Fall im Drill VORKOMMT;
die Positivkontrolle belegt, dass das Gate bei diesem Fall ROT wurde. Das sind
zwei verschiedene Aussagen, und die zweite fehlte im Schema.

**Warum der Messpunkt KEIN neues Feld bekommt.** `gate_wirkung.py` misst je Gate
auf genau zwei Feldern: `slug` (gesucht in `recurring_findings`, `gates_caught`
und den SURVIVES-Zeilen der Befund-Tabelle) und `revised or built` als
Bau-Datum-Nullpunkt. Ein drittes Feld waere eine zweite Wahrheit ueber denselben
Messpunkt — genau die Drift-Falle, gegen die die Registry ihr `_faengt_doc`
geschrieben hat. Gepruef wird deshalb, ob die beiden vorhandenen Felder die Form
haben, in der das Werkzeug sie WIEDERFINDET: ein Slug mit Grossbuchstaben oder
ohne Bindestrich faellt aus `_SLUG_TOKEN`, ein Datum wie `08/2026` aus dem
String-Vergleich `d > gebaut` — beides still.

Aufrufe:
  gate_verankerung_check.py --alle
      Bilanz ueber alle Eintraege (Ist-Messung). Exit 0 immer.
  gate_verankerung_check.py --neu [--basis origin/main]
      Nur Eintraege, die gegenueber der Basis NEU oder GEAENDERT sind.
      Exit 1, wenn einem davon etwas fehlt. Das ist das Verankerungs-Gate.
      Exit 2 = Werkzeugfehler (Basis nicht lesbar) — ein Melder, der beim
      Ausfall gruen meldet, ist schlimmer als keiner.

`--basis` nimmt eine Git-Ref (`git show <ref>:<pfad>`) ODER einen Dateipfad;
letzteres macht den Pruefer ohne Wegwerf-Repo testbar.

Slug: `gate-anchored-without-drill-or-control` (platform#2690 K4). stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

GATE_HEADER = {
    "slug": "gate-anchored-without-drill-or-control",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-09-02",
    "evidence": "tools/tests/test_gate_verankerung_check.py",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO_ROOT, "docs", "governance", "gate-registry.json")

#: Das Repo, dessen Drill-Pfade dieser Pruefer wirklich aufloesen kann —
#: identisch zu `gate_drill_check.EIGENES_REPO` (bewusst dupliziert statt
#: importiert: beide Werkzeuge laufen als eigenstaendige Skripte in Hooks und CI).
EIGENES_REPO = "platform"

#: Exakt das Token, mit dem `gate_wirkung._SLUG_TOKEN` Slugs aus den
#: SURVIVES-Zeilen der Retro-Befundtabellen zieht — hier verankert (`fullmatch`),
#: weil ein Slug, den dieses Muster nicht ganz trifft, im Laengsschnitt unsichtbar
#: bleibt, ohne dass irgendwo etwas rot wird.
SLUG_FORM = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")

ISO_DATUM = re.compile(r"\d{4}-\d{2}-\d{2}")

#: Felder, deren Aenderung KEINE Neu-Verankerung ist: Prosa, Protokoll,
#: Kalibrier-Notizen. Ohne diese Abgrenzung wuerde eine Tippfehler-Korrektur im
#: `note` eines Alt-Gates den PR blockieren — das Gate soll die Verankerung
#: pruefen, nicht das Redigieren bestrafen. `built`, `revised`, `drill`, `module`,
#: `mode` und `repo` sind bewusst NICHT dabei: wer die anfasst, verankert neu.
PROSA_FELDER = frozenset(
    {
        "note",
        "revision_note",
        "expires_note",
        "zustand_note",
        "last_drill_pass",
        "kalibrierfenster",
    }
)


def ist_fremd(gate: dict) -> bool:
    """Lebt das Gate in einem anderen Repo als platform? (wie gate_drill_check)"""
    return (gate.get("repo") or EIGENES_REPO).strip() != EIGENES_REPO


def pruefe_drill(gate: dict, repo: str = REPO_ROOT) -> str | None:
    """Mangel-Text oder None. Fehlende Datei = Mangel (K4: nicht belegbar = nicht gebaut)."""
    drill = (gate.get("drill") or "").strip()
    if not drill:
        return "kein `drill` — der Testpfad fehlt"
    if ist_fremd(gate):
        # Der Pfad liegt nicht in diesem Arbeitsbaum; belegen muss ihn die `ref`.
        if not (gate.get("ref") or "").strip():
            return f"fremd verankert ({gate.get('repo')}) ohne `ref` — Drill nicht belegbar"
        return None
    pfad = drill if os.path.isabs(drill) else os.path.join(repo, drill)
    if not os.path.isfile(pfad):
        return f"Drill-Datei fehlt: {drill}"
    return None


def pruefe_positivkontrolle(gate: dict, repo: str = REPO_ROOT) -> str | None:
    """Mangel-Text oder None (`repo` ungenutzt — einheitliche Signatur, s. PRUEFUNGEN).

    Verlangt `positivkontrolle: {ref, datum}`. `faengt` ist ausdruecklich KEIN
    Ersatz (siehe Modulkopf) — es belegt Vorkommen im Drill, nicht einen Treffer.
    """
    del repo
    pk = gate.get("positivkontrolle")
    if not pk:
        return (
            "keine `positivkontrolle` — kein Beleg, dass das Gate den Fall trifft, "
            "gegen den es gebaut wurde"
        )
    if not isinstance(pk, dict):
        return "`positivkontrolle` ist kein Objekt {ref, datum}"
    maengel = []
    if not (pk.get("ref") or "").strip():
        maengel.append("ohne `ref` (PR/Issue/Datei mit dem roten Lauf)")
    datum = (pk.get("datum") or "").strip()
    if not datum:
        maengel.append("ohne `datum`")
    elif not ISO_DATUM.fullmatch(datum):
        maengel.append(f"`datum` ist kein ISO-Datum: {datum}")
    if maengel:
        return "`positivkontrolle` " + " und ".join(maengel)
    return None


def pruefe_messpunkt(gate: dict, repo: str = REPO_ROOT) -> str | None:
    """Mangel-Text oder None — Form, in der `gate_wirkung.py` das Gate wiederfindet."""
    del repo
    slug = (gate.get("slug") or "").strip()
    if not slug:
        return "kein `slug` — der Rueckfall ist nicht messbar"
    if not SLUG_FORM.fullmatch(slug):
        return (
            f"`slug` ausserhalb der Slug-Form: {slug} — `gate_wirkung.py` findet ihn "
            "in keiner Retro-Tabelle wieder"
        )
    gebaut = (gate.get("revised") or gate.get("built") or "").strip()
    if not gebaut:
        return (
            "weder `built` noch `revised` — kein Nullpunkt fuer die Rueckfall-Messung"
        )
    if not ISO_DATUM.fullmatch(gebaut):
        return f"Bau-Datum ist kein ISO-Datum: {gebaut}"
    return None


PRUEFUNGEN = (
    ("Drill", pruefe_drill),
    ("Positivkontrolle", pruefe_positivkontrolle),
    ("Messpunkt", pruefe_messpunkt),
)


def pruefe_gate(gate: dict, repo: str = REPO_ROOT) -> dict:
    """→ {slug, maengel: [(kriterium, text), …]}"""
    maengel = []
    for name, fn in PRUEFUNGEN:
        text = fn(gate, repo)
        if text:
            maengel.append((name, text))
    return {"slug": gate.get("slug", "?"), "maengel": maengel}


def _kern(gate: dict) -> dict:
    """Der Teil des Eintrags, dessen Aenderung eine Neu-Verankerung ist."""
    return {k: v for k, v in gate.items() if k not in PROSA_FELDER}


def lade_registry(pfad: str) -> list[dict]:
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh).get("gates", [])


def lade_basis(basis: str, registry_pfad: str, repo: str = REPO_ROOT) -> list[dict]:
    """Gates der Vergleichsbasis. Datei-Pfad ODER Git-Ref.

    Wirft `RuntimeError`, wenn die Basis nicht lesbar ist — der Aufrufer macht
    daraus Exit 2. Ein Pruefer, der ohne Basis stillschweigend „nichts neu"
    meldet, waere genau der blinde Melder, den dieses Gate verhindern soll.
    """
    if os.path.isfile(basis):
        with open(basis, encoding="utf-8") as fh:
            return json.load(fh).get("gates", [])
    rel = os.path.relpath(registry_pfad, repo)
    try:
        out = subprocess.run(
            ["git", "show", f"{basis}:{rel}"],
            capture_output=True,
            text=True,
            cwd=repo,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"`git show {basis}:{rel}` fehlgeschlagen: {exc}") from exc
    if out.returncode != 0:
        raise RuntimeError(
            f"Basis nicht lesbar: `git show {basis}:{rel}` → {out.stderr.strip()}"
        )
    try:
        return json.loads(out.stdout).get("gates", [])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Basis-Registry nicht parsebar: {exc}") from exc


def neue_oder_geaenderte(
    jetzt: list[dict], basis: list[dict]
) -> list[tuple[str, dict]]:
    """→ [(grund, gate), …] mit grund ∈ {neu, geaendert}, Reihenfolge wie in der Registry."""
    vorher = {g.get("slug"): _kern(g) for g in basis}
    treffer = []
    for gate in jetzt:
        slug = gate.get("slug")
        if slug not in vorher:
            treffer.append(("neu", gate))
        elif _kern(gate) != vorher[slug]:
            treffer.append(("geaendert", gate))
    return treffer


def _melde(ergebnis: dict, grund: str = "", knapp: bool = False) -> None:
    marke = f" ({grund})" if grund else ""
    if not ergebnis["maengel"]:
        print(f"  ✓ {ergebnis['slug']}{marke} — Drill, Positivkontrolle, Messpunkt")
        return
    if knapp:
        # Bilanz-Modus: die Begruendung ist ueber 31 Zeilen identisch und
        # verdeckt dann die Kriterien-Spalte, um die es geht.
        print(
            f"  ✗ {ergebnis['slug']}{marke} — ohne {', '.join(n for n, _ in ergebnis['maengel'])}"
        )
        return
    print(f"  ✗ {ergebnis['slug']}{marke}")
    for name, text in ergebnis["maengel"]:
        print(f"      {name}: {text}")


def lauf_alle(gates: list[dict], repo: str) -> int:
    print(f"## Verankerungs-Bilanz ({len(gates)} registrierte Gates)")
    fehlt = {name: 0 for name, _ in PRUEFUNGEN}
    vollstaendig = 0
    unvollstaendig = []
    for gate in gates:
        ergebnis = pruefe_gate(gate, repo)
        if ergebnis["maengel"]:
            unvollstaendig.append(ergebnis)
            for name, _ in ergebnis["maengel"]:
                fehlt[name] += 1
        else:
            vollstaendig += 1

    print(f"\n  vollstaendig verankert : {vollstaendig}/{len(gates)}")
    for name, _ in PRUEFUNGEN:
        print(f"  ohne {name:<16}: {fehlt[name]}")

    if unvollstaendig:
        print(f"\n### Unvollstaendig verankert ({len(unvollstaendig)})")
        for ergebnis in unvollstaendig:
            _melde(ergebnis, knapp=True)
        print(
            "\n→ Bestandsschutz: `--alle` ist eine Messung, kein Urteil ueber die "
            "Wirksamkeit dieser Gates. Gefordert wird die Nachruestung erst beim "
            "naechsten Anfassen — dann greift `--neu`."
        )
    else:
        print("\n→ jedes Gate traegt Drill, Positivkontrolle und Messpunkt.")
    return 0


def lauf_neu(gates: list[dict], basis: list[dict], repo: str) -> int:
    treffer = neue_oder_geaenderte(gates, basis)
    if not treffer:
        print("## Verankerungs-Gate — kein neuer oder geaenderter Gate-Eintrag.")
        return 0

    print(f"## Verankerungs-Gate ({len(treffer)} neu/geaendert)")
    rot = 0
    for grund, gate in treffer:
        ergebnis = pruefe_gate(gate, repo)
        if ergebnis["maengel"]:
            rot += 1
        _melde(ergebnis, grund)

    if rot:
        print(
            f"\n→ {rot} Eintrag/Eintraege NICHT verankerungsfaehig. Ein Gate ohne "
            "Drill, Positivkontrolle oder Messpunkt wird nicht eingetragen, sondern "
            "als Kandidat in platform#2234 vermerkt (`kandidaten`-Liste der Registry)."
        )
        return 1
    print(
        "\n→ alle neuen/geaenderten Eintraege tragen Drill, Positivkontrolle, Messpunkt."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Gate-Verankerung pruefen: Drill, Positivkontrolle, Messpunkt (platform#2690 K4)"
    )
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument(
        "--repo", default=REPO_ROOT, help="Wurzel fuer relative Drill-Pfade"
    )
    modus = ap.add_mutually_exclusive_group(required=True)
    modus.add_argument("--alle", action="store_true", help="Bilanz ueber alle Gates")
    modus.add_argument(
        "--neu",
        action="store_true",
        help="nur neue/geaenderte Eintraege (Exit 1 bei Mangel)",
    )
    ap.add_argument(
        "--basis",
        default="origin/main",
        help="Vergleichsbasis fuer --neu: Git-Ref oder Dateipfad",
    )
    args = ap.parse_args(argv)

    try:
        gates = lade_registry(args.registry)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"⚠ Gate-Registry nicht lesbar ({exc}) — kein Verdikt.")
        return 2

    if args.alle:
        return lauf_alle(gates, args.repo)

    try:
        basis = lade_basis(args.basis, args.registry, args.repo)
    except RuntimeError as exc:
        print(f"⚠ {exc}")
        return 2
    return lauf_neu(gates, basis, args.repo)


if __name__ == "__main__":
    sys.exit(main())
