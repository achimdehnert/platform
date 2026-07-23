---
concept_id: KONZ-platform-028
title: Generischer Fach-/Experten-Reviewer (persona-parametrisierter Domänen-Kritiker)
pipeline_status: idea
tier: T2
owner: Achim Dehnert (pg@dehnert.team)
spec_refs: []                 # keine KD-Spec — Reviewer-Capability, kein Klickdummy
adr_threshold: kein ADR für den Pilot (1 Skill, `distribute:false`, reversibel) · org-weite Distribution ⇒ EIGENER ADR (Cross-Repo + Datensouveränität + Security-Perimeter, adr-threshold.md), NICHT bloß Amendment
review_by: 2026-10-23
kill_criteria: "Nach den 3 Realläufen (inkl. Pflicht-Ablation, s. §Kill-Gate): wenn im verblindeten A/B (mit vs. ohne Persona+Kontrakt vs. Ad-hoc-Prompt) kein signifikanter Vorsprung ODER die menschlich bestätigte belegt-Präzision (bestätigt / (bestätigt+widerlegt), Null-Finding-Läufe separat) < 50 % ODER ≥1 falsch-autoritatives P1 ohne Locator ⇒ verworfen. Verbindliche Ja/Nein-Auswertung am review_by-Termin."
superseded_by_spec: null
external_sparring_by: "extern, 2 unabhängige LLM-Anbieter @2026-07-23 (Meinung 1 + Meinung 2) — Verdikt beide: Überarbeiten; Tag-Tabelle s. §Externe Zweitmeinung"
created: 2026-07-23
evidence_manifest:
  - {claim_id: C1, source_path: "platform/.windsurf/workflows/{kd-review,agent-review,adr-review}.md + ls workflows/*review*", commit_or_pr: "grep 2026-07-23", opened_in_session: true}
  - {claim_id: C2, source_path: "~/.claude/agents/ (leer) + ~/.claude/skills/", commit_or_pr: "ls 2026-07-23", opened_in_session: true}
  - {claim_id: C3, source_path: "frist-hub Fachaudit Wohngeld-Handout (Opus-Subagent, dieselbe Session)", commit_or_pr: "meiki-lra/frist-hub#74", opened_in_session: true}
---

# KONZ-platform-028 — Generischer Fach-/Experten-Reviewer

> **Cross-cutting Reviewer-Capability · Heimat platform** (Org `achimdehnert`). Geerdet am
> frist-hub-Fachaudit des Wohngeld-Handouts (`meiki-lra/frist-hub#74`). Externe Zweitmeinung
> eingeholt (2 Anbieter, beide „Überarbeiten") und eingearbeitet — s. §Externe Zweitmeinung.

## Kernthese

Ein einziger, **read-only, persona-parametrisierter** Reviewer-Mechanismus — *Persona × Artefakt ×
Maßstab* variabel, *Evidenz-Ausgabe-Kontrakt fix* — schließt die fehlende **Fachlichkeits-Achse** im
Reviewer-Ökosystem und **komponiert** mit den bestehenden achsen-spezifischen Reviewern, statt sie zu ersetzen.

## Assumption-/Decision-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|-------------------------|--------|
| A1 | Es gibt keine *Fachlichkeits-/Domänen*-Reviewachse — alle bestehenden Reviewer sind achsen-spezifisch | Annahme | C1: `kd-review`=UX, `agent-review`=PR/ADR (ADR-100), `adr-review`, `security-review`, `platform-audit` — kein Domänen-Persona-Reviewer | belegt |
| A2 | LLM-Fachkritik liefert **Hypothesen**, keine Ratifizierung; final entscheidet die Fachstelle | Annahme | C3: Fachaudit trennte belegt/Hypothese; Finding #2 ging an Rechtsamt (PR #5) | belegt |
| A3 | Der Mehrwert entsteht aus **Persona + fixem Kontrakt**, nicht aus Modellstärke/Einzelprompt | Annahme | 3-Wege-Ablation 2026-07-23 (§Ablation): **Persona = aktiver Wirkstoff** — nur-Kontrakt verfehlte das Rechts-P1 (Scope-Drift), Ad-hoc fing es gehedged/ohne Tiefe; Persona+Kontrakt am tiefsten | **gestützt (n=1 Domäne)** |
| D1 | **Read-only**, ratifiziert nie; Output ephemer; **kein neues Scoreboard/SSoT** | Entscheidung | SSoT-Prüfung: keine zweite Wahrheitsquelle | gesetzt |
| D2 | Ausgabe-Kontrakt: Findings **P1/P2/P3 · belegt‖Hypothese · verify-against**. **„belegt" nur mit überprüfbarem Quellen-Locator + Anwendbarkeits-Begründung; fehlt/ungültig ⇒ Auto-Downgrade auf Hypothese. „belegt" ≠ ratifiziert.** | Entscheidung | extern M1-AD-3/M2-AD-3: sonst vergibt dasselbe Modell sich selbst „Wahrheit" | gesetzt (verschärft) |
| D3 | Form = **Skill** (`distribute:false` bis ADR), spawnt pro Lauf einen **Sub-Agenten** mit Persona + Modell. **Persona-Library verpflichtend für Recht/Security/Datenschutz** (versioniert: owner, Geltung, Nicht-Geltung, zugelassene Quellen, verbotene Autoritätsbehauptungen, Ablauf); freie `--persona` nur für explizit explorative Niedrigrisiko-Läufe | Entscheidung | C2 (`agents/` leer); extern M1-AD-5/M2-AD-13/M28-1 (Persona-Wildwuchs) | gesetzt (verschärft) |
| D4 | Modell-Parameter als **abstrakte Klassen** `standard`/`frontier`, aufgelöst über zentrale Policy zu **zugelassenen Endpoints**. **Fail-closed:** souveräner Artefakt-*Inhalt* (nicht nur Skill-Standort) auf nicht-souveränitätskonformer Route ⇒ Abbruch ohne Override | Entscheidung | extern M1-AD-7/M2-AD-4/AD-15: Standort ≠ Daten; Provider-Namen im CLI-Vertrag vermeiden | gesetzt (verschärft) |
| D5 | Org-weite Distribution ⇒ **eigener ADR** (nicht Amendment): Cross-Repo-Scope, Daten-/Egress-Grenzen, Modellrouting, Ownership, Evaluations-Anforderungen, Rollback/Abschaltung. Pilot-Skill bleibt bis dahin `distribute:false` | Entscheidung | adr-threshold.md (Cross-Repo+Souveränität+Security); extern M1-AD-6 (cc-skill-dist verteilt sonst sofort org-weit) | **NEU** |
| D6 | **Komposition:** feste Abgrenzungsregel (fach-review kommentiert NUR fachlich-inhaltliche Korrektheit, nicht Code/ADR-Schema/Security); ephemerer **Review-Plan** je Artefakt (1 primärer Reviewer default, weitere nur per expliziten Trigger, Laufbudget); Findings-Schema `Achse · Artefakt-Locator · Claim · Evidenz-Locator · verify-against` für Dedup; Widersprüche als **ungelöste Konfliktgruppe** (kein Auto-LLM-Schiedsspruch) | Entscheidung | extern M1-AD-9/M2-AD-10..12/M28-5 (R2 war benannt, nicht geregelt) | **NEU** |
| D7 | **Run-Manifest** je Output: Skill-/Vertragsversion, Persona-Version, Modellklasse+Endpoint, Hash/Snapshot der geprüften Artefakte+Standards, Zeitpunkt — **ohne** separates Scoreboard | Entscheidung | extern M2-AD-14/M28-6/M28-3 (Reproduzierbarkeit/Provenienz) | **NEU** |
| D8 | **P1-Governance:** regulatorische/rechtliche/Security-P1 werden als „dringend, unratifiziert" ausgegeben und erfordern eine benannte menschliche Fachstelle **oder** einen unabhängigen zweiten Prüfpfad | Entscheidung | extern M2-M28-8/REC-13 (falsch-autoritatives P1 verbrennt Vertrauen) | **NEU** |
| R1 | Scheinkompetenz — klingt autoritativ, liegt falsch | Risiko | Mitigation D2/D8; Rest → Kill-Gate misst Präzision + Quarantäne bei falsch-P1 | offen |
| R2 | Overlap/Reviewer-Müdigkeit | Risiko | Mitigation D6 (Abgrenzung + Review-Plan + Budget) | offen (gemildert) |
| R3 | Prompt-Injection aus Artefakt/Quellen trotz read-only | Risiko | Mitigation: strikte Kanaltrennung Instruktion/Artefakt/Quelle für Hochrisiko (D3/D6); extern M2-AD-6 | **NEU** |

## MVC (Minimal Viable Concept — konkret)

- **1 Skill** `/fach-review` in `platform/.windsurf/workflows/`, **`distribute:false`** bis zum ADR (D5).
- **Parameter:** `--persona-lib <name@version>` (Pflicht für Hochrisiko) bzw. `--persona <lens>` (nur explorativ) · `--artefakt <pfad|url>` (mit Snapshot/Hash) · `--standard <ADR/Norm/Quellen>` (versionsgebunden) · `--modell <standard|frontier>` (Policy→Endpoint, fail-closed) · `--achse fach` (fix).
- **Ablauf:** Skill spawnt Agenten, System-Prompt = Persona + 4 Prüf-Dimensionen (Tiefe/Vollständigkeit · Korrektheit · Verständlichkeit · Konventionen) + fixer Kontrakt (D2) + read-only; strikte Kanaltrennung (R3). Rückgabe = Findings-Liste (D6-Schema) + Run-Manifest (D7); bei ≥3 Findings Issue-Vorschlag.
- **Ownership (extern M2-AD-7/M28-7):** Code-Heimat platform, aber **je Pilotdomäne eine benannte Fach-Owner-Rolle** (verantwortet Persona, Quellenpaket, Ergebnisbewertung, Ausmusterung).
- **Abgrenzung (D6):** Fachlichkeit — nicht UX (`/kd-review`), nicht Code/PR-vs-ADR (`/agent-review`), nicht ADR-Schema (`/adr-review`), nicht Security-Perimeter (`/security-review`).

## Kill-Gate (verschärft nach externer Zweitmeinung)

- **Lauf 1 (erfolgt):** Wohngeld-Handout — belegtes P1 (§66 Abs.3 SGB I) gefunden. Trägt allein **nicht** die Generalisierung (extern M1-AD-1).
- **Pflicht-Ablation VOR Lauf 2/3:** verblindeter A/B am selben Artefakt — (i) Persona+Kontrakt, (ii) nur Kontrakt ohne Persona, (iii) Ad-hoc-Einzelprompt. Ohne signifikanten Vorsprung von (i) ⇒ A3 falsifiziert ⇒ verworfen.
- **Lauf 2 (Datenschutz-Artefakt) — Vorbedingung:** dokumentierte Souveränitäts-Klärung des Artefakt-*Inhalts* (D4 fail-closed) **bevor** der Lauf startet (extern M1-AD-7/M2-AD-4).
- **Metriken (extern M2-AD-2):** `bestätigte Findings`, `falsch-P1`, `nützliche Findings/Lauf`, `Null-Finding-Läufe`, Kosten, Laufzeit — getrennt. Menschliche Bestätigung mit definiertem Verfahren (auch Teil-/Grauzone).
- **Verbindliche Entscheidung** am `review_by`-Termin 2026-10-23 (Ja/Nein, nicht implizit verstreichen — extern M2-M28-... / M1-M28-2).

| Kriterium | Status | Beleg |
|-----------|--------|-------|
| Ablation zeigt Persona-Vorsprung (Wohngeld) | ✅ erfüllt (n=1 Domäne) | 3-Wege-Ablation 2026-07-23, §Ablation |
| belegt-Präzision ≥ 50 % (menschlich bestätigt) | offen | nach 3 Läufen |
| kein falsch-autoritatives P1 ohne Locator | offen | laufend |
| Souveränitäts-Klärung Lauf 2 dokumentiert | offen | vor Lauf 2 |

## Ablation (Kill-Gate Lauf 1b, 2026-07-23)

Drei Varianten, **gleiches Artefakt** (Vor-Audit-Wohngeld-Handout), **gleiches Modell** (Opus),
read-only — isoliert Persona+Kontrakt gegen Modellstärke:

| Variante | §66 Abs.3-P1 (Ground Truth) | Tiefe |
|----------|------------------------------|-------|
| (i) Persona + Kontrakt | ✅ gefunden + 5 weitere tiefe [belegt] (Wiedereinsetzung=falsches Instrument bei behördl. Frist, §66 Abs.1 Kausalität/§20 Amtsermittlung, RBB→1-Jahres-Frist, §16 Abs.2 Weiterleitung, §7/§8 WoGG) | am tiefsten, P1 zuerst, sauber kalibriert |
| (ii) nur Kontrakt (keine Persona) | ❌ verfehlt — Scope-Drift auf Konsistenz/Hosting (falsche Achse) | flach/generisch |
| (iii) Ad-hoc (nichts) | ⚠️ gefunden, aber gehedged, mit Oberfläche vermischt | mittel, ohne Priorisierung |

**Verdikt: A3 gestützt (n=1 Domäne).** Die **Persona** ist der aktive Wirkstoff der Fachlichkeits-Achse:
der Kontrakt allein (ii) genügt nicht (verfehlte das Rechts-P1, prüfte die falsche Achse); Modellstärke
allein (iii) fängt Teile, aber ohne Tiefe/Kalibrierung. **Caveats (Ehrlichkeit):** nur 1 Domäne; je 1
Lauf (LLM-Varianz nicht gemittelt); (ii) hatte einen Scope-Drift-Confound (las das Repo-KD statt nur
den Handout-Text) — der Kernbefund (P1 verfehlt) hält aber. Cross-Domain-Läufe (2/3) bleiben offen.

## Adversariale Analyse (T2)

**Steelman:** Der fixe Kontrakt (D2) ist die eigentliche Invariante, billig über Domänen wiederverwendbar; es *komponiert* statt zu ersetzen; geerdet an einem realen Lauf, der einen belegten P1-Rechtsfehler fand, den die UX-Prüfung strukturell nicht finden konnte.

**Verworfene/ergänzende Alternativen (inkl. externer OOTB):**

| Alt | Idee | Rolle |
|-----|------|-------|
| Ad-hoc-Subagent-Prompts (Status quo) | Pro Bedarf ein Prompt | Baseline im Ablationstest; kein Kontrakt, driftet |
| N Domänen-Spezial-Skills | je Domäne ein Reviewer | Achsen-Explosion; nur bei dauerhaft hoher Frequenz; Re-Check falls generisch stark domänenabhängige Fehlerraten |
| **Evidenz-first-Prüfer** (extern) | Anforderungen aus freigegebenen Normen extrahieren, LLM lokalisiert/vergleicht nur | **Challenger im Ablationstest** + bevorzugt für wiederkehrende Hochrisiko-Prüfungen |
| **Regel-as-Code + LLM-Erklärung** (extern) | harte Regeln deterministisch, LLM nur Kontext/Erklärung | für stabile Muss-Kriterien kombinieren |
| **Menschliche Fach-Review-Queue** (extern) | LLM sortiert vor, Mensch entscheidet | **Pflicht-Eskalationsweg für regulatorische P1** (D8) |

## Empfehlung & Entscheidung

**Überarbeiten (extern bestätigt) + T2-Pilot durchführen** — mit den oben eingearbeiteten Verschärfungen: Pflicht-Ablation, „belegt"-Locator (D2), fail-closed Modellrouting (D4), Persona-Registry (D3), Review-Plan (D6), Run-Manifest (D7), P1-Governance (D8). **Org-weite Distribution NICHT freigeben** bis eigener ADR (D5); Pilot-Skill `distribute:false`. Die durchgängige, erzwingbare Vertrauensgrenze (zugelassene Quelle → souveränes Routing → menschliche Bestätigung) ist die eine Bedingung, die vor der Verbreitung stehen muss.

## Externe Zweitmeinung — Rückfluss (Step 5)

Zwei unabhängige LLM-Anbieter, 2026-07-23. Beide Verdikt: **Überarbeiten**. Refutation ≈ 0 (Briefing war vollständig) — die Befunde sind Schärfungen unterspezifizierter Achsen, keine Widerlegungen der Kernthese. Konsolidiert (Finding-/REC-IDs beider Meinungen → Verdikt → Aktion):

| Thema | IDs (M1 / M2) | Verdikt | Eingearbeitet als |
|-------|---------------|---------|-------------------|
| Ablation/blind A/B vor Lauf 2/3 | AD-2,REC-1 / AD-1,REC-1,M28-4 | [valid] | Kill-Gate (Pflicht-Ablation) + A3=unbelegt |
| „belegt" braucht Locator, sonst Hypothese | AD-3,REC-3 / AD-3,REC-2,M28-8 | [valid] | D2 verschärft |
| Kill-Gate-Metriken + verbindlicher Termin | AD-4,REC-7 / AD-2,REC-1 | [valid] | Kill-Gate + kill_criteria |
| Souveränität Artefakt-*Daten* bei Routing, fail-closed | AD-7,REC-2 / AD-4,REC-3 | [valid] | D4 verschärft + Lauf-2-Vorbedingung |
| Persona versioniert/registriert, Pflicht bei Hochrisiko | AD-5,REC-4 / AD-13,REC-9,M28-1 | [valid] | D3 verschärft |
| Org-weit = eigener ADR; `distribute:false` | AD-6,REC-6 / AD-9,REC-6 | [valid] | D5 (neu) |
| Komposition: Abgrenzung+Review-Plan+Budget+Dedup | AD-9,REC-5 / AD-10..12,REC-7/8,M28-5 | [valid] | D6 (neu) |
| Abstrakte Modellklassen statt Provider-Namen | — / AD-15,REC-3,M28-2 | [valid] | D4 |
| Prompt-Injection / Kanaltrennung | — / AD-6,REC-10 | [valid] | R3 (neu) + D3/D6 |
| Run-Provenienz/Manifest | — / AD-14,M28-6,M28-3,REC-11 | [valid] | D7 (neu) |
| P1-Governance (Eskalationspfad) | — / M28-8,REC-13 | [valid] | D8 (neu) |
| Fach-Owner je Domäne (Placement platform bleibt) | M28-5 / AD-7,M28-7,REC-4,PRO-5 | [valid] | MVC-Ownership; (a)-Placement bestätigt |
| Vertrag tool-neutral vom CC-Shell trennen | — / AD-8,REC-5 | [valid, Design-Prinzip] | D6/Portabilität (Pilotform D3 bleibt) |
| Kontinuierliche Kalibrierung/Quarantäne | — / REC-12,M28-4 | [valid, post-pilot] | Lifecycle/Kill-Gate-Quarantäne |
| OOTB-Alternativen als Komplemente | OOTB / OOTB | [valid] | Alternativen-Tabelle erweitert |

Kein Befund als `[missversteht-Kontext]`/`[out-of-scope]` getaggt — beide Meinungen waren kontext-treu (vollständiges Briefing). Genau das ist der Grund, das Konzept vor jedem weiteren Lauf zu härten.
