1. Gesamtbewertung (Executive Review)

Reifegrad: 🟢 Production-ready Architecture (nach Umsetzung der unten genannten Punkte)
Architekturqualität: ⭐⭐⭐⭐☆ (4.5/5)
Strategische Passung: ⭐⭐⭐⭐⭐
Governance-Konformität: ⭐⭐⭐⭐☆

Besonders stark:

Konsequente Separation Parser ↔ Domain

CADElement / CADQuantity als belastbares, auditierbares Kernmodell

Mengen inkl. Methode + Confidence → selten so sauber gelöst

Saubere Parallel-Migrationsstrategie (Feature-Flag, Diff-Tests)

Mapping-Profile als Configuration-over-Code

2. Zentrale Stärken (warum das Konzept richtig ist)
2.1 Plattform-Denke statt App-Denke

Das Package ist wirklich domain-agnostisch.
Kein Brandschutz-Leak, kein DIN-Leak → exakt richtig für Platform Layer.

➡️ Strategisch wichtig, da:

Risk-Hub, zukünftige AVA-Services, QS-Pipelines etc. sofort profitieren.

2.2 Mengenmodell (CADQuantity) – exzellent
(quantity_type, value, unit, method, confidence)


Das erfüllt:

Nachvollziehbarkeit

Revisionssicherheit

spätere Gewichtung / Heuristik-Verbesserung

➡️ Das ist besser als 90 % der kommerziellen BIM-Parser.

2.3 Mapping-Profile

JSON-basiert

Regex-fähig

kundenspezifisch

keine Code-Deployments nötig

➡️ Genau richtig für SaaS & Consulting-Reality.

3. Kritische Punkte & Optimierungen (wichtig!)
3.1 ❗ Fehlende explizite Invarianten im CADElement

Problem:
Aktuell sind wichtige Invarianten nur implizit dokumentiert.

Risiko:
Unterschiedliche Apps interpretieren das Modell unterschiedlich.

Empfehlung (hochprior):
Explizite Invarianten im Code erzwingen, z. B.:

class CADElement(BaseModel):
    ...

    @model_validator(mode="after")
    def validate_invariants(self):
        if self.source_format == "ifc" and not self.external_id:
            raise ValueError("IFC elements must have external_id (GUID)")
        if self.category == ElementCategory.SPACE and not self.geometry:
            raise ValueError("Spaces require geometry for area calculation")
        return self


➡️ Governance-konform (keine Silent-Fallbacks)

3.2 Parser liefern zu viel Verantwortung zurück

Beobachtung:
Parser:

extrahieren

klassifizieren

teilweise berechnen

Risiko:
Parser werden „intelligent“, schwer testbar, schwer ersetzbar.

Optimierung (Architektur-Feinschnitt):

Verantwortung	Soll
Parser	lesen + roh extrahieren
Extractor	normalisieren
Calculator	berechnen
Domain-App	bewerten

➡️ Empfehlung:

_extract_quantities() nur rohe IFC-Quantities

Geometrie-basierte Berechnung ausschließlich im calculators/

Das hält Parser dumm und stabil.

3.3 Fehlendes explizites Parsing-Resultat (Batch-Kontext)

Problem:
Iterator[CADElement] verliert Kontext:

Datei-Hash

Parser-Version

Warnings

Parsing-Zeit

Empfohlene Ergänzung:

class CADParseResult(BaseModel):
    file_hash: str
    source_format: SourceFormat
    parser_version: str
    elements: list[CADElement]
    warnings: list[str] = []
    statistics: dict = {}


➡️ Wichtig für:

Audit

Vergleich alt/neu

Caching

Debugging

3.4 DXF-Text-Regex im Parser = Governance-Risiko

Beobachtung:
Regex-Logik für Fachsemantik (FireRating, ExZone) ist im Parser.

Risiko:

Domain-Logik im Platform-Layer

schwer testbar, schwer abschaltbar

Optimierung:

Regex-Extraktion in Mapping-Profile oder Extractor-Hooks

Parser nur: TEXT → raw_text_property

➡️ Entspricht „keine implizite Businesslogik“

4. Performance & Skalierung (gezielte Vorschläge)
4.1 IFC Streaming – gut, aber ergänzen

Ihr nutzt bereits Iterator → 👍

Ergänzung:

Optionaler Element-Filter im Parser:

IFCParser(categories=[WALL, DOOR])


➡️ Spart massiv Zeit bei großen Modellen.

4.2 Caching bewusst nicht im Package

Richtige Entscheidung 👍
Aber: dokumentieren!

Empfehlung:
Explizit festhalten:

cad-services ist pure, zustandslos, kein Cache.

➡️ Caching gehört in:

Application Layer

Job Layer

Celery / Task Queue

5. Testing-Strategie – kleine Lücke

Stark:

Quantity-Method wird getestet

Integration in BFAgent klar

Fehlt (ergänzen):

Golden-Master-Tests

„gleiches IFC → gleiches Normalisat“

Schema-Stabilitätstest

JSON-Dump eines CADElements als Snapshot

➡️ Verhindert unbemerkte Breaking Changes.

6. MCP / Async / Server-Fragen (klare Empfehlung)
Thema	Empfehlung
MCP-Server	❌ Nein (noch nicht)
Async Parser	❌ (I/O gering, CPU-bound)
CLI Tool	✅ Sehr sinnvoll
Batch-API	⚠️ später

Begründung:
Das Package ist Library-first.
Server-Exposition erst, wenn mehrere Consumer außerhalb eures Monorepos existieren.

7. Zusammenfassung – klare Entscheidung

Mein Urteil als IT-Architekt:

✅ Das Konzept ist strategisch richtig,
✅ technisch sauber,
⚠️ benötigt kleine, aber wichtige Härtungen,
🚀 danach absolut plattform-fähig.

Top-5 Maßnahmen (konkret & priorisiert)

Invarianten im Modell erzwingen

Parsing-Result-Wrapper einführen

Domain-Regex aus Parser entfernen

Parser ↔ Calculator Verantwortungen schärfen

Golden-Master-Tests ergänzen



1) Sprint-fähige Roadmap (ausführlich)
Leitplanken (Definition of Done, gilt für alle Arbeitspakete)

Keine Silent-Fallbacks: Fehler/Warnungen explizit, keine „magischen Defaults“.

Invarianten sind testbar und enforced (Model Validator / explizite Checks).

Reproduzierbarkeit: gleiche Datei → gleiche Normalisierung (Golden Master / Snapshot).

Messbarkeit: Parser liefert Warnings + Stats (z. B. counts, timings).

Milestone 0 — Foundations (0.5–1 Sprint)

Ziel: Projektgrundgerüst, damit Folgearbeit nicht „frei dreht“.

M0.1 Package Skeleton & CI

Tasks

platform/packages/cad-services/ anlegen gemäß Struktur

pyproject.toml inkl. dependencies (IfcOpenShell, ezdxf, pydantic)

Test-Runner (pytest), Lint/Format (ruff/black), typing (mypy optional)

Minimal README + Versionierung/Changelog

Abnahme

pip install -e . funktioniert

pytest läuft grün (auch wenn nur smoke tests)

__version__ kommt aus zentraler Quelle (version.py)

Milestone 1 — Kernmodell & Contracts (1 Sprint)

Ziel: Stabiler Datenvertrag, bevor Parser migriert werden.

M1.1 Pydantic Models produktionshart machen

Tasks

CADElement/CADProperty/CADQuantity/CADGeometry implementieren

Invarianten ergänzen (Validatoren)

to_dict() / to_json() helper (stabiler Export)

cad_services/models/__init__.py sauberer Public Surface

Konkrete Invarianten (Beispiele)

external_id muss gesetzt sein

source_format konsistent

CADQuantity.unit muss zu quantity_type passen (z. B. area → m²)

confidence immer 0..1 (habt ihr schon)

Abnahme

Unit-Tests für alle Invarianten (positive + negative Pfade!)

Snapshot-Test: JSON Schema / Model Dump stabil

M1.2 ParseResult Wrapper (Kontext)

Tasks

CADParseResult einführen:

file_hash, parser_version, warnings, statistics, elements

Einheitliche Warning-Struktur (Code + message + element_ref optional)

Abnahme

jeder Parser gibt mindestens stats: element_count, parse_time_ms

warnings sind explizit (keine stillen Drops)

Milestone 2 — IFC Migration (1–2 Sprints)

Ziel: IFCParser v2 liefert vergleichbare Ergebnisse wie bestehend, aber sauberer.

M2.1 IFCParser: Roh-Extraktion + Normalisierung

Tasks

IFC öffnen, Unit Scale bestimmen (wie im Konzept)

Extractor-Schicht wirklich nutzen:

Parser: file reading + iterieren

Extractor: ifc element → CADElement

Properties/Quantities:

Properties: psets, attribute (klarer source)

Quantities: quantity sets als roh (method=IFC_QUANTITY)

Wichtig (Qualität)

Keine Geometrie defaultmäßig extrahieren (Performance)

Geometrie optional + messbar (timing)

Abnahme

Fixture IFC (klein) → erwartete Categories vorhanden

Quantity method/confidence gesetzt

CADParseResult vollständig

M2.2 Golden-Master / Diff-Test Harness

Tasks

Vergleich alte vs. neue Parsergebnisse:

Counts pro category

Stichproben: GUID → Name/Type/properties/quantities

tolerant gegenüber Reihenfolge (sort by external_id)

„Diff Report“ (Text/JSON)

Abnahme

automatisierter Diff-Test in CI

definierte Toleranzen dokumentiert (z. B. rounding)

Milestone 3 — DXF Migration (1–2 Sprints)

Ziel: DXF Parser stabil + Mapping Profile Engine als echte Konfiguration.

M3.1 MappingProfile Engine „richtig“ machen

Tasks

JSON Schema für Profile (Versionierung im Profil!)

Regex-Compilation caching (performance)

Property aliasing/normalization als eigener Schritt

Defaults: default_de als shipped profile

Abnahme

Profile Validation Test: ungültiges Profil → klarer Fehler

Profil-Version wird in CADParseResult angegeben

M3.2 DXFParser: Semantik raus aus Parser

Tasks

Parser extrahiert:

layer, entity type, raw geometry hints

TEXT/MTEXT als CADProperty(name="raw_text", source=DXF_TEXT, ...)

Semantik (FireRating/ExZone) wird als:

MappingProfile rule oder

optionaler „PropertyExtractor“-Plugin umgesetzt (konfigurierbar)

Abnahme

Tests: gleiche DXF + Profile → gleiche Categories

Parser droppt Entities nicht still (wenn ignoriert: warning)

Milestone 4 — Calculator Layer (1 Sprint)

Ziel: Mengen/Geometrie berechnen, ohne Parser zu „vermischen“.

M4.1 QuantityCalculator

Tasks

Einheitliche Unit-Konvertierung (m, mm, m² …)

Berechnungsmethoden:

COMPUTED_2D (DXF)

COMPUTED_GEOMETRY (IFC mit optionaler Geometrie)

Confidence-Scoring Regeln (transparent!)

IFC quantity: 1.0

computed geometry: z. B. 0.8

heuristic: z. B. 0.5 (konfigurierbar)

Abnahme

Tests: input geometry → expected area/length (inkl. units)

Jede computed quantity hat inputs + formula

Milestone 5 — BFAgent Integration & Parallelbetrieb (1–2 Sprints)

Ziel: Feature-Flag, Monitoring, Rollback-fähig.

M5.1 Integration wie im Konzept (Phase 1–3)

Tasks

Feature Flag USE_CAD_SERVICES_V2

Adapter-Layer, damit BFAgent API gleich bleibt (keine Breaking Changes)

Logging/metrics:

parse_duration

element_count

warning_count

diff_score (optional)

Abnahme

Shadow-Mode möglich (beide Parser laufen, nur einer wird verwendet)

Rollback: Flag aus → altes Verhalten sofort

Milestone 6 — Cleanup & Hardening (nach Stabilisierung)

Ziel: Alte Parser entfernen, API stabilisieren, Release.

Tasks

Deprecation Notice

MAJOR/MINOR Policy scharf stellen

Dokumentation, Beispiele, Migration Guide

Abnahme

Alte Parser entfernt oder klar deprecated

Version pinned in BFAgent wie geplant

2) PR-Checklist (ausführlich, merge-blocking)

Diese Checklist ist bewusst „hart“. Wenn ein Punkt nicht erfüllt ist: kein Merge.

A. Architektur & Grenzen

 Änderungen halten Parser / Extractor / Calculator Grenzen ein (keine Vermischung).

 Keine Domain-Logik im cad-services (keine Brandschutz-/DIN-/ATEX-Regeln).

 Public API Änderungen sind bewusst:

 Breaking change? → MAJOR + Migration Notes

 Backwards compatible? → MINOR/PATCH

B. Datenmodell & Invarianten

 Neue Felder haben klare Semantik + sind dokumentiert.

 Invarianten enforced (Validatoren oder explizite Checks).

 Kein „implicit default“, der fachliche Invarianten brechen kann.

 CADQuantity:

 method immer gesetzt

 confidence 0..1

 unit konsistent zum quantity_type

 computed quantities haben inputs + formula

C. Fehler, Warnings, Observability

 Keine Silent-Fallbacks (z. B. unbekannte Entities werden geloggt/als Warning gezählt).

 Parser liefern CADParseResult:

 warnings gefüllt, wenn etwas ignoriert/unklar

 statistics enthalten counts + duration

 Logs/Metriken wurden nicht entfernt oder „leiser“ gemacht.

D. Tests (Pflicht)

 Unit-Tests für neue/angepasste Logik vorhanden.

 Negative Tests vorhanden (invalid file, missing ids, bad profile).

 Golden-Master/Snapshot aktualisiert und geprüft:

 Änderungen sind erklärt (Changelog/PR description)

 Diff-Harness Test: alt vs. neu (wenn Parser betroffen)

E. Performance & Ressourcen

 Kein unnötiges O(N²) in hot paths (insbesondere DXF entity loops).

 Regex werden nicht pro entity neu kompiliert (compiled cache).

 Geometrie Extraktion ist optional und dokumentiert (perf impact).

 Memory: keine komplette IFC-Geometrie ohne need.

F. Versionierung & Release

 Version bump korrekt (SemVer)

 CHANGELOG Eintrag vorhanden (user-facing)

 Dependencies pinned/kompatibel dokumentiert (IfcOpenShell Version!)

G. Security & SaaS-Readiness (kurz, aber wichtig)

 Kein Pfad-Traversal / unsafe file handling

 Multi-Tenant: keine globalen Caches mit tenant-abhängigen Inhalten

 Keine sensitiven Daten in Logs

Optional: PR-Template (empfohlen)

Wenn ihr es richtig rund machen wollt, hängt ihr in GitHub/GitLab ein PR-Template dran mit:

Motivation

Scope

Risks

Tests

Rollback Plan

Performance Notes