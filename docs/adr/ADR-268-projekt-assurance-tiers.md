---
id: ADR-268
title: Projekt-Assurance-Tiers — Projektart × Reife-Phase als plattformweite Risiko-Achse (Cross-Repo)
status: accepted
date: 2026-07-09
deciders: [achim]
informed: [all-repos]
domains: [governance, process, security, deployment, drift-prevention]
supersedes: []
amends: []
depends_on: [KONZ-platform-009]
consumed_by: [ADR-267]
external_sparring_by: two-external-llms@2026-07-09
tags: [assurance-tier, project-class, lifecycle, risk-based, registry, fail-closed, sovereignty]
scope:
  include_paths:
    - "platform/infra/**"
    - "**/project-facts.md"
---

# ADR-268: Projekt-Assurance-Tiers — Projektart × Reife-Phase als plattformweite Risiko-Achse (Cross-Repo)

- **Status:** accepted *(2026-07-09, Owner-Entscheidung. Enforcement-Grenze: die Achse ist definiert; scharf wird sie erst mit dem Registry-`tier`-Feld + dessen CI-Check.)*
- **Datum:** 2026-07-09
- **Entscheider:** Achim Dehnert
- **Verwandt:** KONZ-platform-009 (registry-unified-ssot), ADR-211 (Klickdummy = nie Prod), ADR-267 (Review-Requirement — erster Konsument dieser Achse)

## Zusammenfassung

Governance-Strenge (Review-Pflicht, später auch CI-Härte, Coverage-Schwellen, Deploy-Gates,
Datenhandling) darf **nicht** für alle Repos gleich sein — ein privates Wegwerf-Repo braucht nicht
die Government-Strenge, und **kein** Projekt darf in der frühen Prototyp-Phase durch Prod-Rigidität
ausgebremst werden. Dieses ADR definiert **eine** wiederverwendbare Risiko-Achse aus **zwei
Dimensionen** und macht sie **verbindlich pro Repo** hinterlegbar.

## Kontext & Problem

- Eine „one-size-fits-all"-Policy ist entweder zu lasch (für Government/Tenant) oder bremst zu stark
  (für private/PoC/Prototypen).
- Der erste Konsument (ADR-267, Review-Requirement) braucht eine **verbindliche** Antwort auf
  „wie streng ist *dieses* Repo?" — und zwar so, dass jeder Mensch und jede Automation es über
  **einen** Lookup kennt.
- Strenge hängt nicht nur an der *Projektart*, sondern am **realen Exposure**: ein Government-
  Projekt als Klickdummy hat keine echten Daten und kein Prod (ADR-211: KD ist nie Prod).

## Entscheidung

**Zwei Achsen; die effektive Strenge ist `f(Projektart, Reife-Phase)`.**

### Achse 1 — Projektart (Ziel-Assurance / Decke)

Legt die **Ziel-Strenge in Prod** + die **harten Constraints** fest (Souveränität/DSGVO). Sechs
Klassen, T0–T5:

| Projektart | Tier | Ziel-Strenge in Prod | Harte Constraints (ab Prod/echte Daten) |
|---|---|---|---|
| **privat** | T0 | minimal | — |
| **Proof of Concept** | T1 | niedrig | — |
| **MVP** | T2 | mittel | intern |
| **Kundenindividuelles Produkt** | T3 | hoch | Kundendaten: kein externer Egress |
| **Tenant-fähiges Produkt** | T4 | sehr hoch | Mandantentrennung, DSGVO |
| **Produkt für Government** | T5 | maximal | ttz-lif-Souveränität: on-prem, kein Egress, Datenklassifikation |
| *(nicht deklariert)* | **→ T5** | maximal | **fail-closed** |

### Achse 2 — Reife-Phase (aktive Strenge)

Reuse des bestehenden Genesor-`pipeline_status` (kein neues Statusmodell): **idea → klickdummy →
pilot → prod → sunset**. Die Phase **deckelt**, wie viel der Ziel-Strenge *jetzt* aktiv ist.

### Aktivierungsschwelle (der Kern)

Die volle Projektart-Rigidität greift **erst ab Prod-Deploy ODER echten/sensiblen Daten**. Davor
ist die Strenge für **alle** Klassen gedeckelt:

| Phase | Aktive Strenge (jede Klasse) |
|---|---|
| **Klickdummy / Prototyp** (kein Prod, keine echten Daten; ADR-211 Prod-Guard) | ≈ T1: großzügige Positivliste (Docs + App-Code + nicht-Deploy-Config), Zweit-Review **nicht** erzwungen |
| **Pilot / Staging** (synthetische/begrenzte Daten) | mittel: inerte Docs + nicht-ausführende Assets; Zweit-Review empfohlen |
| **Prod / echte Daten** | **volle** Projektart-Rigidität + harte Constraints |

### Positivliste — konkret als *inert vs. ausführend* (nicht schwammig)

- **Immer review-frei** (alle Klassen/Phasen): reine Prosa — `*.md`-Text, `CHANGELOG.md`,
  `LICENSE`, `.txt`, Bild-Assets *innerhalb* `docs/`.
- **Nie review-frei** (hart, endungsunabhängig): alles, was CI/Build/Deploy **liest oder ausführt**
  — `.github/**`, `Dockerfile`, `*.yml/*.yaml/*.toml/*.json` mit Build-/CI-Bezug, Migrationen,
  jeglicher Code, Secrets/Deploy-Config.
- **Phasen-/Tier-abhängig dazwischen:** App-Quellcode + nicht-Deploy-Config sind **vor Prod**
  (bzw. in T0/T1) review-frei; ab Prod (T2+) nicht mehr.

### Zweit-Review (Vier-Augen)

Genau **ein** Hebel: **wann ist `wirdigital` (der zweite Mensch) Pflicht?** Es gibt **kein**
Freigabe-Board/Gremium. Skala: nie (T0) → optional (T1) → Prod-Deploys (T2/T3) → Prod **+**
Migration/Config (T4) → immer-in-Prod (T5). In der Klickdummy-Phase: nie erzwungen.

### Kill-Reaktion (immer repo-lokal)

Ein Fail-open (etwas fälschlich review-frei durchgelaufen) ist **immer** ein protokolliertes
Ereignis; die *Reaktion* skaliert im **Blast-Radius**, nie global:

| Tier | Reaktion | Aufhebung |
|---|---|---|
| T0/T1 | Fast-Path *dieses* Repos aus + Log/Notiz | geprüfter PR behebt Ursache + reaktiviert Fast-Path |
| T2/T3 | + Root-Cause-Pflicht | wie oben |
| T4 | + Incident + Policy-Review | + Incident-Close |
| T5 | + Incident + `wirdigital`-Sign-off | + Incident-Close mit Sign-off |

**Kein** automatischer klassen-/plattformweiter Freeze. Kein globaler Schalter — Aufheben ist
immer ein sichtbarer, geprüfter PR pro Repo.

## Verbindliche Hinterlegung (SSoT)

- **Tier UND Phase** leben als Felder (`tier`, `phase`) in der **bestehenden zentralen Repo-Registry**
  (KONZ-platform-009, registry-unified-ssot) — **keine** neue Parallel-Datei (SSoT-Disziplin).
- **CI erzwingt Vollständigkeit für BEIDE Achsen:** fehlt `tier` **oder** `phase` → CI rot **und**
  fail-closed-Behandlung: fehlender/veralteter **`tier` → T5**, fehlende/unklare **`phase` → prod**
  (volle Rigidität). *(Externer Befund: `phase` deckelt die Strenge — wäre sie nicht fail-closed,
  würde „niedrige Phase halten" zum reibungsärmsten Governance-Bypass.)*
- **Repo = Projekt = ein Tier — mit Ausnahmen-Regel:** Repos, bei denen Repo-Grenze ≠ Exposure-Grenze
  (Monorepo, Shared Library, GitHub-Actions-/Reusable-Workflow-Repo, IaC, Template-Repo,
  Multi-Deploy) tragen den **strengsten anwendbaren** Tier ihrer enthaltenen Exposure (nie den
  laxesten); wo das zu grob ist, wird das Repo **gesplittet**. Keine Unter-Klassifizierung durch
  gemischte Inhalte.
- **Änderung:** hoch stufen (strenger) jederzeit; **runter** stufen (Kontrollen lockern) nur mit
  **minimalem Evidenz-Schema** (Anlass · vorher/nachher · betroffene Daten/Deploy-Ziele · Reviewer ·
  Datum · Reaktivierungs-/Rollback-Bedingung) — sonst wird Downgrade zur stillen Abkürzung.

## Operationalisierung — EINE Policy-as-Code-Funktion (kein Prosa-Nachbau)

Der externe Review war hier scharf: eine Matrix in ADR-Prosa erzeugt bei mehreren Konsumenten
mehrere leicht divergierende Implementierungen — genau auf der Sicherheitsgrenze.

- **Eine versionierte, getestete Policy-Funktion** `f(tier, phase, changed_paths, data_flags,
  deploy_target) → {zweitreview_pflicht, review_freie_pfadklassen, kill_reaktion, harte_constraints}`
  ist das **einzige** Auswertungs-Artefakt; **alle** Konsumenten (Deploy-Gate, Board-Badge, künftig
  CI/Coverage) **importieren** sie — kein frei nachimplementiertes `f` pro Repo/Workflow.
- **Semantik→Pfad-Brücke explizit:** die Pfadklassen (`inert` / `ausführend` / `build-ci-deploy` /
  `daten-schema` / `konfig-wirkung`) sind als **maschinenlesbares Mapping mit Tests inkl.
  Gegenbeispielen** hinterlegt (Generatoren, Package-Manifeste, IaC, Notebooks, Test-Fixtures,
  „harmlose Endung + ausführender Inhalt" sind explizit als *nicht* inert markiert).

## Review-Schuld beim Phasenübergang (Promotion-Review)

Vor Prod review-frei geschriebener App-Code darf **nicht** ungeprüft in Prod wandern. Beim
Übergang **pilot → prod** (bzw. Erst-Prod-Deploy) erzwingt ein **einmaliger Promotion-Review**:
der seit Projektbeginn review-frei akkumulierte Code wird als Ganzes gegen das dann geltende
Prod-Tier gereviewt. Ohne bestandenen Promotion-Review kein Prod-Deploy. Damit trägt keine
„Review-Schuld" unbesehen in den T5-Kontext.

## Konsequenzen

**Positiv:** eine wiederverwendbare Risiko-Achse (Review heute; CI/Coverage/Deploy morgen); kein
Ausbremsen früher Phasen; fail-closed by default (beide Achsen); Souveränität an T3–T5 gekoppelt.
**Negativ / Vorbehalte:**
- Registry-Pflege (CI erzwingt); `f(Klasse, Phase)` ist eine Matrix, kein Skalar.
- **Constraints-Ehrlichkeit (enforced vs. dokumentiert):** „kein externer Egress" u.ä. für T3–T5 sind
  nur so stark wie ihre Durchsetzung — pro Constraint markieren: **technisch enforced** ·
  **manuell geprüft** · **nur dokumentiert**. Sofort-Maßnahme mit hohem Wert: **Egress-Default-Block**
  in den Souveränitäts-Orgs (ttz-lif/meiki-lra) — billig, mechanisch, schließt die „echte-Daten"-
  Detektionslücke teilweise.
- **Klickdummy-Phasen-Lockerung ruht auf einem dormant Guard:** „Klickdummy = kein Prod" ist laut
  ADR-211 durch `klickdummy_prod_guard.sh` (F11) zu erzwingen — dieser ist **aktuell
  unimplementiert/dormant** (ADR-211 Rev 20). Bis zum Bau stützt sich die Lockerung auf
  **Selbstdeklaration**, nicht Enforcement — bewusst getragenes Übergangs-Risiko, hier benannt.

## Kill-Gate / Review

- **review_by:** 2026-10-09.
- **Instrumentierung (Pflicht, sonst Bauchentscheidung):** der Review misst **Verteilung je
  Tier/Phase**, Anzahl Runterstufungen, Fail-open-Fälle, manuelle Overrides und den **Anteil
  review-freier Deploys** — nicht nur die Extreme.
- **Kill (Extrem):** wenn die Matrix in der Praxis nur „alle = T5" oder „alle = T0" ergibt → auf
  „prod-vs-nonprod × sovereign-vs-nicht" (2×2) zusammenfalten.
- **Drift-Fall (wahrscheinlicher, extern ergänzt):** wenn fast alle Repos aus Bequemlichkeit in
  T1/T2 clustern oder dauerhaft in niedriger Phase gehalten werden → Phase-/Tier-Vergabe nachschärfen
  (nicht die Achse killen).
- **Fail-open-Behandlung präzise:** Erkennung (Stichproben-Diff-Audit), **Frist** zur Reaktion,
  **Mindest-Log** (Repo, Run, Diff-Ref, Policy-Version, handelnder Mensch), Verantwortlicher.
  **Wiederholungsregel:** wiederholte repo-lokale Fail-opens **desselben Musters** eskalieren zu
  einer **plattformweiten Policy-Review** — **ohne** automatischen globalen Freeze.
- **Sunset-Semantik:** in `sunset` sinkt die Strenge **nicht** — keine neue Feature-Entwicklung, aber
  **unveränderte oder erhöhte** Strenge für Daten/Secrets/Egress/Archivierung/Löschung.
- **Überlappungs-Tie-Breaker:** bei mehrdeutiger Projektart gewinnt das **höchste reale Exposure**
  (z.B. echte Kundendaten heben mindestens auf T3-aktive Constraints).

## Konsumenten

- **ADR-267** (Review-Requirement) ist der erste Konsument: Positivliste + `wirdigital`-Pflicht +
  Kill-Reaktion werden aus `f(Projektart, Phase)` dieses ADR bezogen.
- Künftig möglich (nicht Teil dieses ADR): CI-Härte, Coverage-Schwellen, Deploy-Gates,
  Datenhandling entlang derselben Achse.

## Externe Zweitmeinung (2026-07-09)

Zwei unabhängige externe LLM-Reviews (via `/adr-handoff-extern`). Beide: **„Überarbeiten"** — Kern
tragfähig, aber die operationale Härte auf der Sicherheitsgrenze schärfen. Befund-Tagging (nur
`[valid]` eingearbeitet; Review-A- und Review-B-IDs zusammengeführt):

| Thema | Review-IDs (A/B) | Verdikt | Eingearbeitet als |
|-------|------------------|---------|-------------------|
| **Phase auch fail-closed + CI-erzwungen** (kritisch) | B-AD-1, B-AD-5, B-M28-1, A-M28-2, A-REC-4 | ✅ valid (kritisch) | Verbindliche Hinterlegung (fehlende Phase → prod) |
| **Review-Schuld beim Prod-Übergang** (kritisch) | B-AD-4, B-M28-2 | ✅ valid (kritisch) | §Promotion-Review |
| **Eine zentrale Policy-as-Code-Funktion** (kein Prosa-Nachbau) | A-AD-8, A-M28-1, A-REC-1, A-REC-3, B-M28-4 | ✅ valid | §Operationalisierung |
| **Semantik→Pfad-Brücke + Klassen statt Endungen** | A-AD-3, A-REC-2, B-AD-7 | ✅ valid | §Operationalisierung (Mapping+Tests+Gegenbeispiele) |
| **Repo=1-Tier Ausnahmen** (Monorepo/Lib/Actions/IaC/Template/Multi-Deploy) | A-AD-2, A-REC-5, B-AD-6 | ✅ valid | Verbindliche Hinterlegung (strengster anwendbarer Tier / Split) |
| **Downgrade-Evidenz-Schema** | A-M28-3, A-REC-8 | ✅ valid | Verbindliche Hinterlegung |
| **Souveränität enforced-vs-manuell-vs-dokumentiert + Egress-Default-Block** | A-M28-4, A-REC-11, B-OOB-1 | ✅ valid | Konsequenzen |
| **Kill-Gate Instrumentierung + Drift-Fall** (nicht nur Extreme) | A-AD-7, A-REC-12, B-M28-5 | ✅ valid | Kill-Gate |
| **Fail-open Details (wer/Frist/Mindest-Log) + Wiederholungs-Eskalation** | A-AD-6, A-REC-9, A-M28-6, A-REC-10 | ✅ valid | Kill-Gate (ohne globalen Freeze) |
| **Sunset-Semantik: Strenge sinkt nicht** | A-M28-5, A-REC-13 | ✅ valid | Kill-Gate |
| **Überlappungs-Tie-Breaker (höchstes Exposure gewinnt)** | A-AD-5, A-REC-7 | ✅ valid | Kill-Gate |
| **Klickdummy technisch prüfen — F11-Prod-Guard dormant** | A-AD-4, A-REC-6 | ✅ valid | Konsequenzen (F11-Vorbehalt explizit) |
| **„echte Daten" mechanisch statt deklariert** | B-AD-1, B-OOB-1 | 🟡 teils valid | Egress-Default-Block ja; volle PII-Erkennung bewusst zurückgestellt (1+1-Infra) |
| **GitHub-native Enforcement bevorzugen** | B-OOB-2, A-OOB-3 | ✅ valid (Prinzip) | §Operationalisierung + Konsistenz mit ADR-267 (GitHub-nativ, Konsumenten importieren `f`) |
| **Über-Engineering / Start 2×2, Granularität verdienen** | A-AD-8, A-OOB-2, B-AD-3, B-M28-3, B-OOB-3 | 🟡 valid als **Owner-Entscheidung** | Kill-Gate misst Nutzung; 6-Klassen sind Owner-gesetzte *Decke* („pay per used cell"); 2×2-Fold als dokumentierter Kill-Ausgang. **Offen zur Owner-Wahl: jetzt 2×2 starten?** |
| **Auto-Freigabe statt review-freie Spur** | A-OOB-4 | ⛔ out-of-scope | für KD/T0/T1 zu schwergewichtig (Owner-Prämisse Prototyp-Speed) |

**Nicht eingearbeitet:** A-OOB-4 (`[out-of-scope]`). Proponent-Befunde (A/B-PRO-*) bestätigen die
Richtung. **Eine offene Owner-Entscheidung bleibt:** ob die 6×5-Granularität sofort gilt oder mit
2×2 (sovereign×prod) gestartet und die Granularität „verdient" wird (beide Reviews empfehlen letzteres
für den 1+1-Betrieb — bedingt darauf, dass noch keine echten T2–T4-Repos existieren).
