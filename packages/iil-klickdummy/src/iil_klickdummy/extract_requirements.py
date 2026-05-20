#!/usr/bin/env python3
"""Klickdummy → Requirements-Skeleton (UC/FR/NFR/Lasten-/Pflichtenheft).

Parst eine Klickdummy-Spec (YAML) und generiert Markdown-Skelette für:
  - requirements/use-cases/UC-NN-<screen>.md       (1 UC pro Screen)
  - requirements/fr.md                              (Funktionale Requirements)
  - requirements/nfr.md                             (Nicht-funktionale)
  - requirements/schnittstellen.md                  (Adapter / Systemgrenzen)
  - requirements/lastenheft-skeleton.md             (high-level, Auftraggeber-Sicht)
  - requirements/pflichtenheft-skeleton.md          (concrete, Auftragnehmer-Sicht)

Output ist *Skelett* — Editieren erwartet. Drift gegen Spec via Re-Extract +
git-diff sichtbar. Eine Quelle wahr: die Spec (analog ADR-211 I1 Spec-first).

Aufruf:
    python3 scripts/klickdummy/extract_requirements.py <spec.yaml> [<out-dir>]

Exit: 0 ok, 1 Schema-Fehler, 2 Setup-Fehler.
"""
from __future__ import annotations

import pathlib
import re
import sys
from datetime import date

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)


# -- Helpers ------------------------------------------------------------------

def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")


def load_spec(path: pathlib.Path) -> dict:
    if not path.exists():
        print(f"FAIL: Spec fehlt: {path}")
        sys.exit(1)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write(out_root: pathlib.Path, rel: str, content: str) -> None:
    p = out_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  ✓ {rel}")


# -- Generators ---------------------------------------------------------------

def gen_uc(spec: dict, out: pathlib.Path) -> None:
    """1 UseCase pro Screen — als RUP/UML-Skelett.

    Räumt veraltete UC-Dateien (`UC-*.md` im Zielordner) vor dem Schreiben weg,
    damit Re-Extract bei Screen-Reihenfolge- oder Namensänderung nicht zwei
    parallele UC-Sets stehenlässt.
    """
    uc_dir = out / "requirements" / "use-cases"
    if uc_dir.exists():
        for stale in uc_dir.glob("UC-*.md"):
            stale.unlink()
    screens = spec.get("screens", []) or []
    spec_id = spec.get("spec_id", "spec")
    for i, sc in enumerate(screens, start=1):
        sid = sc.get("id", f"screen-{i}")
        title = sc.get("title", sid)
        personas = sc.get("personas", []) or []
        purpose = sc.get("purpose") or sc.get("title") or ""
        pa = sc.get("parity_acceptance", []) or []
        konzept = sc.get("konzept_ref", []) or []
        targets = sc.get("target_mocks", []) or []
        datafields = sc.get("datafields", []) or []
        body = f"""---
type: use-case
uc_id: UC-{i:02d}-{slug(sid)}
source_spec: {spec_id}
source_screen: {sid}
extracted_at: {date.today().isoformat()}
status: draft   # draft | reviewed | approved
---

# UC-{i:02d} · {title}

> Generiert aus Klickdummy-Spec (Screen `{sid}`). Skelett — bitte editieren.

## Akteure
{chr(10).join(f"- {a}" for a in personas) or "- _(noch nicht spezifiziert)_"}

## Zweck / Ziel
{purpose}

## Vorbedingung
- Aktor ist angemeldet, Persona-Sicht aktiv.
- _(weitere Vorbedingungen ergänzen — z. B. vorheriger Screen)_

## Hauptablauf
{chr(10).join(f"{j+1}. {p.get('check','')}" for j, p in enumerate(pa)) or "1. _(noch nicht spezifiziert)_"}

## Nachbedingung
- _(z. B. Folge-Screen erreicht, Zustand geändert, Audit-Eintrag erzeugt)_

## Beteiligte Systeme / Schnittstellen
{chr(10).join(f"- {t}" for t in targets) or "- _(keine externen Systeme deklariert)_"}

## Datenfelder
{chr(10).join(f"- `{d.get('name','?')}` ({d.get('type','?')}) — Quelle: {d.get('source','?')}" for d in datafields) or "- _(keine Datenfelder im Spec deklariert)_"}

## Konzept-Bezug
{chr(10).join(f"- {k}" for k in konzept) or "- _(kein Konzept-Bezug)_"}

## Abgeleitete FRs
{chr(10).join(f"- FR-{slug(sid)}-{j+1:02d}: {p.get('check','')}" for j, p in enumerate(pa)) or "- _(keine)_"}
"""
        write(out, f"requirements/use-cases/UC-{i:02d}-{slug(sid)}.md", body)


def gen_fr(spec: dict, out: pathlib.Path) -> None:
    rows = []
    for sc in spec.get("screens", []) or []:
        sid = sc.get("id", "?")
        for j, p in enumerate(sc.get("parity_acceptance", []) or [], start=1):
            rows.append(
                f"| FR-{slug(sid)}-{j:02d} | {sid} | {p.get('id','')} | {p.get('check','')} |"
            )
    body = f"""---
type: functional-requirements
source_spec: {spec.get('spec_id','spec')}
extracted_at: {date.today().isoformat()}
status: draft
---

# Funktionale Requirements (FR)

> Aus Klickdummy-Spec `{spec.get('spec_id','?')}` v{spec.get('spec_version','?')} abgeleitet.
> Jede Zeile entspricht einem `parity_acceptance`-Eintrag eines Screens (= platform:ADR-211 I1-Acceptance).
> Drift-Check: Re-Extract gegen committeten Stand → `git diff`.

| FR-ID | Screen | Anker | Anforderung |
|---|---|---|---|
{chr(10).join(rows) or "| — | — | — | _(keine parity_acceptance im Spec)_ |"}
"""
    write(out, "requirements/fr.md", body)


def gen_nfr(spec: dict, out: pathlib.Path) -> None:
    cls = spec.get("class", "?")
    ev = spec.get("class_evidence", {}) or {}
    off = spec.get("off_ramp", {}) or {}
    adr = spec.get("adr", {}) or {}

    nfrs: list[tuple[str, str, str]] = []  # (id, kategorie, anforderung)
    # Security / Prod-Sicherheit (I2)
    if cls == "mock":
        if ev.get("no_backend"):
            nfrs.append(("NFR-Sec-01", "Security", "Klickdummy darf keinen echten Backend-Code-Pfad enthalten (`class: mock`, `class_evidence.no_backend: true`)."))
        if ev.get("no_demo_param"):
            nfrs.append(("NFR-Sec-02", "Security", "Kein `?demo=`-Render in der echten App (`class_evidence.no_demo_param: true`)."))
        if ev.get("target_mocks_visible"):
            nfrs.append(("NFR-Sec-03", "Security", "Alle Systemgrenzen müssen als anklickbare Target-Mocks sichtbar sein (kein toter Link)."))
    elif cls == "spec-demo":
        pg = ev.get("prod_guard", {}) or {}
        nfrs.append(("NFR-Sec-01", "Security", f"`?demo=`-Render ist in Produktion nicht erreichbar (Guard: {pg.get('setting','?')} + DEBUG/TESTING; Response: {pg.get('response_in_prod','?')})."))
        nfrs.append(("NFR-Sec-02", "Security", "Guard ist durch automatisierten Test bewiesen (Demo-Tour-Tests mit `KLICKDUMMY_TOUR_ENABLED=False`)."))
    elif cls == "stub-demo":
        nfrs.append(("NFR-Sec-01", "Security", "Dedizierte Demo-Route ist in Produktion nicht erreichbar (404)."))
    elif cls == "story":
        nfrs.append(("NFR-Sec-01", "Security", "Component-Catalog (Storybook o. ä.) ist in Produktion nicht erreichbar (404)."))

    # Lifecycle (I3)
    if off.get("doppelquell_grenze"):
        nfrs.append(("NFR-Lifecycle-01", "Lifecycle", f"Doppelquellen-Pflege endet bei `{off['doppelquell_grenze']}`."))
    if off.get("ttl_days"):
        nfrs.append(("NFR-Lifecycle-02", "Lifecycle", f"Off-Ramp-TTL: max. {off['ttl_days']} Tage nach Parity-grün."))

    # Integration (Systemgrenzen)
    for i, s in enumerate(ev.get("systemgrenzen", []) or [], start=1):
        nfrs.append((f"NFR-Integ-{i:02d}", "Integration", f"Schnittstelle: `{s}` (generisch, mandantenkonfigurierbar)."))

    # Namensraum (I4)
    if adr.get("conforms_to"):
        nfrs.append(("NFR-Gov-01", "Governance", f"ADR-Konformität: `{adr['conforms_to']}` (Klickdummy-Cross-Repo-Rahmen)."))

    rows = "\n".join(f"| {n[0]} | {n[1]} | {n[2]} |" for n in nfrs) or "| — | — | _(keine NFRs ableitbar)_ |"
    body = f"""---
type: non-functional-requirements
source_spec: {spec.get('spec_id','spec')}
extracted_at: {date.today().isoformat()}
status: draft
---

# Nicht-funktionale Requirements (NFR)

> Aus `class`, `class_evidence`, `off_ramp` und `adr` der Klickdummy-Spec abgeleitet.
> **Asymmetrische Brücke:** NFRs *dürfen* über den Klickdummy hinausgehen — Performance, Skalierung, Audit etc.
> sind hier nicht erschöpft und müssen manuell ergänzt werden.

| NFR-ID | Kategorie | Anforderung |
|---|---|---|
{rows}

## Manuell zu ergänzen (typisch im Klickdummy nicht abgedeckt)

- **Performance:** Antwortzeiten, Durchsatz, Last-/Stresstest-Schwellen
- **Verfügbarkeit:** SLA, MTBF, MTTR
- **Datenschutz:** DSFA-Bezug, Aufbewahrungsfristen, Löschpflichten
- **Audit / Logging:** Auditpflichtige Aktionen, Retention
- **Barrierefreiheit:** WCAG-Level, Tastatur-Navigation
- **Internationalisierung:** Sprachen, Datumsformate, Kalender
"""
    write(out, "requirements/nfr.md", body)


def gen_schnittstellen(spec: dict, out: pathlib.Path) -> None:
    ev = spec.get("class_evidence", {}) or {}
    systemgrenzen = ev.get("systemgrenzen", []) or []
    # Sammle alle target_mocks aus Screens
    mocks: set[str] = set()
    for sc in spec.get("screens", []) or []:
        for t in sc.get("target_mocks", []) or []:
            mocks.add(t)
    body = f"""---
type: interfaces
source_spec: {spec.get('spec_id','spec')}
extracted_at: {date.today().isoformat()}
status: draft
---

# Schnittstellen (Adapter / Systemgrenzen)

> Aus `class_evidence.systemgrenzen` (Klassen-Liste) und `screens[].target_mocks` (Pro-Screen-Bezug) abgeleitet.

## Generische Adapter-Familien (aus `class_evidence.systemgrenzen`)

{chr(10).join(f"- **{s}**" for s in systemgrenzen) or "- _(keine deklariert)_"}

## Pro Screen verwendet (aus `screens[].target_mocks`)

{chr(10).join(f"- `{m}`" for m in sorted(mocks)) or "- _(keine deklariert)_"}

## Manuell zu konkretisieren (Pflichtenheft-Übergang)

Pro Adapter:
- API-Vertrag (Methoden, Payload-Format, Auth)
- SLA / Verfügbarkeit
- Fehlerfallverhalten (Timeout, Retry, Fallback)
- Daten-Mapping zu internem Modell
"""
    write(out, "requirements/schnittstellen.md", body)


def gen_lastenheft(spec: dict, out: pathlib.Path) -> None:
    title = spec.get("title", spec.get("spec_id", "Klickdummy"))
    personas = set()
    for sc in spec.get("screens", []) or []:
        for p in sc.get("personas", []) or []:
            personas.add(p)
    main_goals = [sc.get("title", "?") for sc in spec.get("screens", []) or []]
    body = f"""---
type: lastenheft
source_spec: {spec.get('spec_id','spec')}
extracted_at: {date.today().isoformat()}
status: skeleton
audience: auftraggeber
---

# Lastenheft (Skelett) · {title}

> *Was* der Auftraggeber will. Aus Klickdummy abgeleitet — high-level.
> Vor Verwendung: editieren, priorisieren, fachlich ergänzen.

## 1. Ausgangslage und Motivation

_(Manuell: Warum dieses Vorhaben? Welcher Schmerz wird beseitigt? Welche Strategie wird umgesetzt?)_

## 2. Zielgruppen

{chr(10).join(f"- {p}" for p in sorted(personas)) or "- _(keine Personas deklariert)_"}

## 3. Hauptziele (aus Screens abgeleitet)

{chr(10).join(f"{i+1}. {g}" for i, g in enumerate(main_goals)) or "1. _(keine)_"}

## 4. Funktionale Anforderungen (Übersicht)

Siehe [`fr.md`](fr.md). Jede Zeile dort = eine `parity_acceptance` aus dem Klickdummy.

## 5. Nicht-funktionale Anforderungen (Übersicht)

Siehe [`nfr.md`](nfr.md). **Klickdummy bildet nur Teil ab** — manuell ergänzen:
Performance, Verfügbarkeit, Datenschutz, Audit, Barrierefreiheit.

## 6. Schnittstellen

Siehe [`schnittstellen.md`](schnittstellen.md).

## 7. Abgrenzung / Out-of-Scope

_(Manuell: Was wird ausdrücklich NICHT geliefert?)_

## 8. Termine / Meilensteine

_(Manuell)_

## 9. Bezug

- Spec: `{spec.get('spec_id','?')}` v{spec.get('spec_version','?')}
- Klickdummy-Pfad: _(Repo-Pfad der Klickdummy-Implementierung)_
- ADR-Verankerung: {spec.get('adr',{}).get('local','?')} (`conforms_to: {spec.get('adr',{}).get('conforms_to','?')}`)
"""
    write(out, "requirements/lastenheft-skeleton.md", body)


def gen_pflichtenheft(spec: dict, out: pathlib.Path) -> None:
    title = spec.get("title", spec.get("spec_id", "Klickdummy"))
    body = f"""---
type: pflichtenheft
source_spec: {spec.get('spec_id','spec')}
extracted_at: {date.today().isoformat()}
status: skeleton
audience: auftragnehmer
---

# Pflichtenheft (Skelett) · {title}

> *Wie* der Auftragnehmer das Lastenheft umsetzt. Aus Klickdummy + Lastenheft abzuleiten.
> Vor Verwendung: technische Architektur ergänzen.

## 1. Bezug zum Lastenheft

Siehe [`lastenheft-skeleton.md`](lastenheft-skeleton.md). Diese Datei konkretisiert dessen Punkte 4–6.

## 2. Architektur-Skizze

_(Manuell: Container-/Component-Diagramm; Ports & Adapter; Datenflüsse.)_

Klickdummy-Klasse: `{spec.get('class','?')}` (platform:ADR-211 I2)
Off-Ramp-Strategie: `{spec.get('off_ramp',{}).get('doppelquell_grenze','?')}` (TTL {spec.get('off_ramp',{}).get('ttl_days','?')} d)

## 3. UseCases (Verzeichnis)

Siehe [`use-cases/`](use-cases/) — je UC ein Markdown mit Akteur/Ablauf/Nachbedingung/Daten.

## 4. Datenmodell

_(Manuell zu konkretisieren — die Klickdummy-`datafields` sind nur Anker.)_

Klickdummy-Datenfelder (je Screen) siehe `use-cases/`-Skelette unter „Datenfelder".

## 5. Schnittstellen-Verträge

Siehe [`schnittstellen.md`](schnittstellen.md). Pro Adapter zu ergänzen:
API-Methoden, Payload-Format, Auth-Mechanismus, SLA, Fehlerfallverhalten.

## 6. Nicht-funktionale Realisierung

Siehe [`nfr.md`](nfr.md). Mapping je NFR-ID → technische Maßnahme.

## 7. Test-/Abnahme-Konzept

- **I1 Spec ↔ Render** (platform:ADR-211): Spec-Konformität via `make klickdummy-i1`.
- **Parity-Test** (bei Demo-Render): Klickdummy ⊆ flow.md ⊆ App.
- **UC-Tests:** je UC ein E2E-Pfad (Browser/Playwright o. ä.).
- **NFR-Tests:** Performance/Last/Penetration je nach Kategorie.

## 8. Bezug

- Spec: `{spec.get('spec_id','?')}` v{spec.get('spec_version','?')}
- ADR (lokal): {spec.get('adr',{}).get('local','?')}
- ADR (Rahmen): {spec.get('adr',{}).get('conforms_to','?')}
- Schwester-Implementierungen: {', '.join(spec.get('adr',{}).get('sister_of',[]) or []) or '(keine)'}
"""
    write(out, "requirements/pflichtenheft-skeleton.md", body)


# -- Main ---------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: extract_requirements.py <spec.yaml> [<out-dir>]")
        return 2
    spec_path = pathlib.Path(argv[0])
    out_root = pathlib.Path(argv[1]) if len(argv) > 1 else spec_path.parent
    spec = load_spec(spec_path)
    print(f"== Extract Requirements ==")
    print(f"  Spec : {spec_path}")
    print(f"  Out  : {out_root}/requirements/")
    print()
    gen_uc(spec, out_root)
    gen_fr(spec, out_root)
    gen_nfr(spec, out_root)
    gen_schnittstellen(spec, out_root)
    gen_lastenheft(spec, out_root)
    gen_pflichtenheft(spec, out_root)
    print()
    print(f"  Hinweis: alle generierten Dateien tragen `status: draft|skeleton` —")
    print(f"  manuell editieren, dann committen. Drift gegen Spec via Re-Extract + git diff.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    import sys
    return main(sys.argv[1:])
