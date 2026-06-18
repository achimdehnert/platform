---
id: ADR-252
title: "comic-hub — Comic-Erstellung als Thin-Composer über bestehende Seams, gegated durch Konsistenz-Spike + Klickdummy"
status: proposed
date: 2026-06-18
deciders: [Achim Dehnert]
consulted: [Claude Code, externes LLM-Review (Reproduzierbarkeit/Datenmodell), externes LLM-Review (Konsistenz-Technologie/Reframe)]
informed: [iilgmbh, achimdehnert]
domains: [comic, illustration, authoring, architecture]
supersedes: []
amends: []
depends_on: [ADR-117, ADR-130, ADR-180, ADR-211]
related: [ADR-096, ADR-121, ADR-237, ADR-021, ADR-251]
tags: [comic, illustration, composer, ssot, consistency, klickdummy, gate]
scope:
  include_paths:
    - "docs/adr/ADR-252-*"
---

# ADR-252 — comic-hub als Thin-Composer, gegated durch Konsistenz-Spike + Klickdummy

> Nummer **252** provisorisch (Author-Time-Interim; ADR-228 merge-time-Allokation noch nicht
> implementiert) — bei Merge gegen den dann aktuellen Bestand re-validieren.

## Kontext und Problemstellung

Mehrere Bausteine, die zusammen einen Comic ergeben, existieren im Ökosystem bereits
**getrennt**, aber keiner deckt Comic-Erstellung als Ganzes ab:

- **weltenhub** + **weltenfw** — SSoT für Welt/Charakter/Szene (ADR-117); Consumer referenzieren
  per UUID, duplizieren nicht.
- **authoringfw** (ADR-096) + writing-hub `LLMRouter` — KI-Textproduktion (Dialog, Szenen-/
  Panel-Beschreibung), Free-Tier-first.
- **illustration-hub** + **illustration-fw** — provider-agnostische **Einzelbild**-Generierung
  (ComfyUI auf selbstgehosteter RTX 4090 primär, OpenAI/stability.ai Fallback), Asset-Storage,
  Versionierung, async Jobs, Tenant-Isolation.

**Lücke:** Niemand hält Comic-Spezifika — Panel/Page-Layout, Lese-Reihenfolge, **Lettering**
(Sprechblasen/Text) und vor allem **visuelle Charakter-Konsistenz über eine Panel-Sequenz**.
Heute ist Konsistenz nur Prompt-Engineering: kein Referenz-Anker, kein deterministischer Pfad.
Genau diese vier Dinge sind der einzige echte Neubau-Anteil.

Die zentrale Unsicherheit ist **nicht** „ob komponieren" (das ist klar billiger als ein dritter
Stack), sondern **(1)** auf welcher Konsistenz-Technologie das Vorhaben machbar ist und **(2)** wo
der erste Beweis stattfindet, bevor Betriebsfläche (Repo/Deployment/CI/Tenancy) entsteht.

## Entscheidungstreiber

- SSoT-Disziplin: referenzieren statt duplizieren (ADR-117) — keine zweite Wahrheit für
  Charaktere/Szenen.
- „Code vor ADR / erst in einer App stabilisieren, dann extrahieren" (ADR-121).
- Package-/Repo-Konsolidierung (ADR-180): keine neue Betriebsfläche ohne bewiesenen Bedarf;
  1-Consumer-Code bleibt im Consumer-Repo.
- Kostendisziplin: selbstgehostete GPU primär, bezahlte Bild-APIs nur als Fallback.
- Lizenz-Konformität für potenziell **kommerzielle** Comic-Ausgabe.
- Reproduzierbarkeit/Auditierbarkeit KI-generierter Artefakte (ADR-130 content_store).

## Betrachtete Optionen

### O1 — Verortung
- **(A) Greenfield comic-hub-Repo zuerst** — klare Domänengrenze, aber sofort volle Betriebslast
  für real kleine Neukomplexität; widerspricht ADR-121/ADR-180.
- **(B) Inkubation als Modul** (bild-domännah in illustration-hub oder hinter dem Klickdummy),
  Repo-Extraktion erst nach bewiesener Domäne+Bedarf. ✅ gewählt.
- **(C) Comic = reine View/Export-Schicht** über vorhandenen Seams (kein eigener Hub) —
  als gleichrangige Alternative offen gehalten, Entscheidung erst nach dem Spike.

### O2 — Konsistenz-Technologie (Kern-Risiko)
Ursprünglich vorgesehen: gestaffelte Leiter mit IP-Adapter/ControlNet als MVP-Ziel. **Verworfen** —
das ist 2024-Framing, und das Kern-Tooling (`cubiq/ComfyUI_IPAdapter_plus`) ist seit 14.04.2025
**maintenance-only** (verifiziert). Neue Leiter:

| Stufe | Technik | Rolle |
|---|---|---|
| (a) | Prompt-only (Style-DNA + Charakterbeschreibung) | markierter Entwurf / Fallback |
| **(e)** | **Referenz-Edit-Foundation-Model** (Qwen-Image-Edit 2509/2511, Flux Kontext dev) — EIN Referenzbild, kein Training | **MVP-Default** |
| (c) | IP-Adapter / ControlNet | nachrangige Spezialoption |
| (d) | Charakter-LoRA pro Charakter | separater späterer Beschluss, nur bei nachgewiesenem Bedarf |

### O3 — Konsistenz-Anker
- **Modellgewichte (LoRA)** — verworfen als Wahrheits-Anker: an Basismodell gebunden, bei
  Modellwechsel wertlos.
- **Durables Referenzbild** („Character Reference Sheet" als illustration-hub-Asset-UUID) —
  ✅ gewählt: überlebt Modellwechsel, SSoT-konform.

## Entscheidung

**comic-hub ist ein Thin-Composer**, der vorhandene Seams komponiert statt einen Stack neu zu
bauen, und der **erst nach zwei harten Gates** überhaupt als eigenständiges Repo materialisiert wird.

```
Comic-Komposition (Modul → später ggf. comic-hub)
  ├─ weltenfw       → Welt / Charakter / Szene  (SSoT, nur UUID-Referenzen)
  ├─ authoringfw    → Dialog- & Panel-Beschreibungstext (Sequenz REFERENZIERT outline/scene)
  └─ illustration-fw → Panel-Bilder via ConsistentSequenceAgent (Konsistenz dahinter gekapselt)
```

### Gate-Sequenz (entscheidet, ob/wie gebaut wird)
- **Gate 0 — Konsistenz-Spike (1–2 Tage, vor jeder Repo-/Datenmodell-Entscheidung):**
  Liefert ein Referenz-Edit-Foundation-Model (Qwen-Image-Edit 2509/2511, alternativ Flux Kontext
  dev) **akzeptable Cross-Panel-Identität @ Zielstil auf der vorhandenen RTX 4090, unter realer
  konkurrierender Last**? Repräsentativer Korpus, Qualitätsdimensionen (Identität, Kleidung/
  Requisiten, Stiltreue, Mehrpersonen-Verwechslung, schwierige Ansichten), Mindest-Bestehenswerte,
  zulässige manuelle Korrekturrate, Laufzeit-/VRAM-/Kostenbudget werden **vor** dem Test fixiert.
- **Gate 1 — Klickdummy (ADR-211):** Bestätigt einen eigenständigen Comic-Lifecycle und misst, ob
  assistiertes/manuelles Lettering für das MVP genügt.
- **Erst danach:** Entscheidung Hub (O1-B) vs. View/Export (O1-C) und ggf. Repo-Extraktion.
  Ein `comicfw`-Paket ist ausgeschlossen, solange < 2 Consumer (ADR-180).

### Jetzt geltende Prinzipien (capability-orientiert, gelten für Hub *und* View)
Diese Festlegungen sind **unabhängig vom Gate-0-Ausgang und von der Hub-vs-View-Wahl** — sie
benennen *Verantwortung*, nicht ein Repo:

1. **Komposition statt Stack:** Konsistenz wird **hinter der illustration-fw-Abstraktion** gekapselt
   (`ConsistentSequenceAgent`) — keine direkte IP-Adapter-Kopplung im Comic-Code.
2. **Konsistenz-Anker = durables Referenzbild** je Charakter (Asset-UUID), Engine = austauschbares
   Foundation-Model (Leiter oben). Eigentümer-Verantwortung: **semantische Charakter-Identität**
   liegt bei weltenhub (SSoT); **versionierte Referenz-Assets + Konditionierungsdaten** bei der
   Bild-Schicht (illustration-hub); die **Comic-Komposition** pinnt nur Character-UUID +
   Profilrevision + konkrete AssetRevision.
3. **SSoT-Referenz:** narrative Sequenz (Beat-/Szenenreihenfolge) **referenziert** outline/scene,
   keine Re-Derivation; Layout/Lettering ist lokal. Format-unabhängige Semantik von
   formatabhängiger Platzierung trennen.
4. **Reproduzierbarkeit:** jede Generierung erzeugt ein unveränderliches **Generation Manifest**,
   persistiert über content_store (ADR-130), ohne kanonische weltenhub-Daten zu duplizieren.
5. **Lizenz:** Modell-/Provider-Lizenz + Referenzherkunft gehören in die Asset-Provenienz; **vor
   Export** maschinenprüfbares Lizenz-Gate. Für kommerzielle Ausgabe **Qwen-Image-Edit
   (Apache-2.0) bevorzugen**; Flux Kontext [dev] erst nach BFL-Lizenzklärung (Gewichte
   non-commercial; Outputs frei, Modellbetrieb kommerziell nicht).
6. **Compositing-Prinzip:** semantische SpeechBubble/Caption-Daten sind die Wahrheit, **SVG** ist
   abgeleitetes versioniertes Renderartefakt.
7. **Multi-Tenancy** row-level `tenant_id` (ADR-237); GPU ist geteilter Engpass (Governance-Pflicht).

### Post-Gate-0 zu entscheiden (NICHT Teil dieser Entscheidung)
Bewusst **offen gelassen**, weil abhängig von Spike-Ergebnis und Hub-vs-View-Wahl — vorab-Festlegung
wäre verfrüht und würde nach dem Spike neu geschrieben:

- **Hub (O1-B) vs. View/Export (O1-C)** + konkreter Repo-/Service-Schnitt und Servicegrenze.
- **illustration-fw Capability-Vertrag** (Referenzanzahl/Masken/Seed/Workflow-Version) — hängt vom
  gewählten Foundation-Model ab; eigenes Tracking-Issue.
- **Generation-Manifest-Feldschema** (konkrete Felder).
- **Pipeline-State-Machine** (Entwurf→…→Export) + Pin-vs-Track-Politik + Zustände
  `stale`/`source_missing`/`access_revoked`.
- **Comic-Datenmodell-Detail** (Koordinatensystem, Panelgeometrie, Z-Order, Anschnitt,
  Doppelseiten, Layoutvarianten; Webtoon/Übersetzung/A11y).
- **Auto-Lettering** als eigenes Arbeitspaket (MVP = assistiert/manuell) mit eigener Schwelle.
- **GPU-Governance-Tuning** (Queue-Klassen/Quoten/Backpressure/Telemetrie) unter realer Last.

## Konsequenzen

**Positiv**
- Maximale Wiederverwendung; kein zweiter Text-/Bild-/Asset-/Tenant-Stack.
- Größtes Risiko (visuelle Konsistenz) wird **vor** Betriebsfläche empirisch entschieden.
- Konsistenz-Anker (Referenzbild) und Konsistenz-Engine (austauschbares Foundation-Model) sind
  entkoppelt → modell-überlebensfest.
- Reproduzierbarkeit/Audit by-construction (Generation Manifest).

**Negativ / Risiken**
- Referenz-Edit-Modelle (~Q8/FP8) sind VRAM-schwerer als SDXL; Sequenz-Batch konkurriert mit
  illustration-hub-Jobs — reale Kapazität ist im Spike zu messen, nicht anzunehmen.
- Auto-Lettering bleibt ein offener, potenziell teurer Produkt-Engpass (bewusst aus dem MVP
  herausgehalten).
- Bei dauerhaft niedrigem Comic-Volumen wäre selbst die Modul-Inkubation Aufwand — daher
  Gate-1 als Bedarfsnachweis.
- Foundation-Model-Layer bewegt sich schnell (Migrationspflege; daher hinter illustration-fw
  gekapselt).

## Implementierungs-Backlog (Detail-Specs, nachgelagert)
Ergänzend zu „Post-Gate-0 zu entscheiden": SVG-Renderdetail (Textfluss/Schweifanker/Kollisionen/
Unicode/RTL/Font-Lizenz, getrennte Web-/Druck-Profile, optionaler editierbarer Export);
Human-in-the-Loop (Casting/Referenzset-Lock/Panel-Lock/manuelle Abnahme); optional/nachrangig
Multi-Angle-Referenzframes via Video-Modell (Orbit→Frame-Extraktion).

## Verworfene Alternativen
- Greenfield-Repo zuerst (O1-A) — Widerspruch zu ADR-121/ADR-180.
- IP-Adapter/ControlNet als MVP-Ziel — veraltet, Kern-Tooling maintenance-only.
- Charakter-LoRA als MVP-Default oder Wahrheits-Anker — Trainings-/Lifecycle-Last, modell-fragil.
- Deterministische 2D/3D-Figuren + Stilisierung — kollidiert mit „kein zweiter Bild-Stack";
  späterer Forschungszweig, falls (e) und (d) scheitern.
- SaaS-Comic-Pipeline als Produktion — kollidiert mit Self-Hosting-/Kosten-/SSoT-Konventionen;
  nur als externe Qualitäts-Messlatte zulässig.

## Verifizierte Belege (Stand 2026-06-18)
- Qwen-Image-Edit-2509 (Apache-2.0, Charakter-Konsistenz, Multi-Image):
  https://huggingface.co/Qwen/Qwen-Image-Edit-2509 · Nachfolger 2511:
  https://qwen.ai/blog?id=qwen-image-edit-2511
- FLUX.1-Kontext-dev — Non-Commercial-Lizenz der Gewichte:
  https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/blob/main/LICENSE.md
- IP-Adapter maintenance-only (14.04.2025): https://github.com/cubiq/ComfyUI_IPAdapter_plus

## Nicht verifiziert (als Hypothese geführt)
- „Flux.1↔Flux.2-LoRA-Inkompatibilität" — das Prinzip „LoRA an Basismodell gebunden" wird
  übernommen, die konkrete Versionsbehauptung nicht.
- Konkrete VRAM-/`max_concurrent`-Werte — im Gate-0-Spike zu messen.
