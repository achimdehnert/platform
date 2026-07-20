---
concept_id: KONZ-platform-011
title: Deployment-Green-Program — strukturierte, sich selbst verbessernde Staging→Prod-Methode
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: org-weiter ADR
review_by: 2026-08-15
kill_criteria: "Wenn nach 60 Tagen weder (a) ein Konsolidierungs-ADR mit erzwungenem supersedes-Gate gemergt ist NOCH (b) ein einziges Repo eine gegatete Staging→Prod-Promotion mit Required-Check fährt — dann ist das Programm gescheitert (Sprawl-Beitrag #7) und wird sunset gesetzt."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-021-unified-deployment-pattern.md, commit_or_pr: "status=accepted date=2026-02-10 (kein supersedes-Feld)", opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-120-unified-deployment-pipeline.md, commit_or_pr: "status=accepted date=2026-03-11 supersedes=[]", opened_in_session: true}
  - {claim_id: C3, source_path: docs/adr/ADR-156-reliable-deployment-pipeline.md, commit_or_pr: "status=proposed date=2026-04-02 (3 Monate offen)", opened_in_session: true}
  - {claim_id: C4, source_path: docs/adr/ADR-210-local-staging-prod-architecture.md, commit_or_pr: "status=proposed date=2026-05-19 (1,5 Monate offen)", opened_in_session: true}
  - {claim_id: C5, source_path: ".github/workflows/prod-uptime-canary.yml", commit_or_pr: "Issue #857: travel-beat.iil.pet/livez → HTTP 502, stündlich neues Issue (30 offen)", opened_in_session: true}
  - {claim_id: C6, source_path: .windsurf/workflows/ci-green-program.md, commit_or_pr: "Zeilen 69-73: messbares Exit-Kriterium (≥90% uses:, Red-Rate <10%/30d); v1 per Self-Red-Team verworfen", opened_in_session: true}
  - {claim_id: C7, source_path: ".github/workflows/", commit_or_pr: "_deploy-hetzner.yml + _deploy-unified.yml (2 Deploy-Reusables); risk-hub deploy.yml on:push[main], needs:[ci], STAGING_* Secrets vorhanden", opened_in_session: true}
  - {claim_id: C8, source_path: .windsurf/workflows/hotfix.md, commit_or_pr: "hotfix.md + incident.md existieren (bewusst leichtgewichtige Umgehungspfade)", opened_in_session: true}
created: 2026-07-02
---

# KONZ-platform-011 — Deployment-Green-Program

## 1 Executive Summary

- **Das Gefühl des Owners ist belegt, nicht nur Gefühl.** Die Deployment-Strategie ist
  evolutionär akkretiert: ~15 Deploy/Staging-Strategie-ADRs, davon **zwei mit „unified" im
  Titel, beide `accepted`, keiner supersedet den anderen** (ADR-021 `date=2026-02-10`,
  ADR-120 `supersedes=[]`), und **zwei seit Monaten `proposed`** (ADR-156 seit 2026-04-02,
  ADR-210 seit 2026-05-19). Zwei Deploy-Reusables (`_deploy-hetzner` + `_deploy-unified`).
- **Es ist aber nicht Chaos, sondern fragmentierte Struktur** — Reusables, config-lint,
  failure-monitor, uptime-canary, Staging-Port-Governance existieren alle. Es fehlt der
  *Rahmen*, der sie bindet, plus die *Zwangsentscheidung*, die Alt-Pfade abschaltet.
- **Der Kern-Bug ist `supersedes: []`, nicht die ADR-Anzahl** (unabhängig von zwei
  Kritik-Agenten verifiziert). Ein 7. Konsolidierungs-ADR ohne erzwungene Supersession
  ist strukturell nur Sprawl-Beitrag #7.
- **Der Deploy-Fluss ist merge=Prod** (`on: push [main]`); Staging existiert als
  Parallelspur, **nicht als Gate**. Der `prod-uptime-canary` erkennt `travel-beat 502`
  **korrekt**, feuert aber **stündlich ein neues Issue** (30 offen) — Detektion funktioniert,
  **Remediation ist der Engpass**, der Loop ist offen.
- **Empfehlung: kein monolithisches Programm, sondern drei hart entkoppelte Tracks** —
  (T0) Sofort-Incident travel-beat, (T-A) ADR-Konsolidierung *mit CI-erzwungener
  Supersession*, (T-B) gegatete Promotion-Pipeline *mit Required-Check + Rollback-Vorbedingung*.
  Die naive „CI-green-Program-Kopie" trägt **nicht 1:1**, weil Deploy-Failures im Gegensatz
  zu CI-Failures nicht idempotent/replaybar sind.

## 2 Scope & Evidenzbasis

**In-Scope:** die org-weite Methode, wie Änderungen Richtung Staging und Prod gelangen —
ADR-Landschaft, Trigger-Modell (push vs. Promotion), Gating, Monitoring→Remediation-Loop.
**Out-of-Scope:** die konkrete Hetzner/Traefik-Infra-Topologie (ADR-157/198/212 bleiben
gültig), einzelne Repo-Deploybugs außer als Beleg.

Alle mit `E`-Grad belegten Aussagen stammen aus in dieser Session geöffneten Artefakten
(siehe `evidence_manifest`). Der Adversariat lief als **drei unabhängige Agenten**
(Steelman / Advocatus Diabolus / Maintainer-2028), die sich gegenseitig nicht sahen; zwei
davon zogen die ADR-Zählung unabhängig neu (Diabolus: „15+", Maintainer: „9 accepted + 2
proposed") — die präzise dateiname-basierte Zahl ist **28 Treffer, davon ~15 echte
Deploy/Staging-Strategie-ADRs** (Rest sind Content-/Research-„pipelines").

## 3 Infrastruktur-Fit

| Baustein | Zustand (verifiziert) | Grad |
|---|---|---|
| ADR-Landschaft | ~15 Deploy/Staging-ADRs; 2× „unified" accepted ohne Supersession; 2× proposed seit Monaten | E1 |
| Deploy-Reusables | `_deploy-hetzner.yml` + `_deploy-unified.yml` (zwei parallele) | E3 |
| Trigger | `on: push [main]`, `needs: [ci]`; Staging-Secrets vorhanden, aber kein Promotion-`needs` | E3 |
| Staging | 53 ports.yaml-Einträge, STAGING_*-Secrets — existiert, aber Parallelspur | E3 |
| Monitoring | `prod-uptime-canary.yml` (erkennt 502 korrekt), `deploy-failure-monitor.yml` | E3 |
| Loop | **offen** — 30 stündliche Canary-Issues auf 1 Vorfall, kein Upsert, keine Eskalation | E3 |
| Blaupause | `ci-green-program` (ADR-209): Prävention/Gates-als-Code/Selbstabschaltung, messbares Exit | E1 |
| Umgehungspfade | `/hotfix` + `/incident` (bewusst ohne vollen Flow) | E3 |

**Fit-Urteil:** Der teure Teil (Staging-Infra) ist bezahlt und läuft; es fehlt die billige
Verdrahtung (Gate) plus die teure Governance-Entscheidung (Alt-ADRs/-Pfade abschalten).

## 4 Steelman (stärkste Version des Vorschlags)

Jeder `git merge` nach main ist heute ein Prod-Deploy ohne Gate — production-by-accident
statt production-by-decision. Gleichzeitig belügt das Monitoring sich selbst: es sieht den
travel-beat-502 korrekt, erzeugt aber 30 Issues statt einer Handlung — Beobachtung ohne
Wirkung ist so gut wie keine Beobachtung. Drei Argumente tragen den Umbau:

1. **Die ADR-Landschaft beweist Staffversagen, nicht Unordnung.** Zwei ADRs beanspruchen
   „unified", beide accepted, keiner supersedet — der lebende Beweis, dass zweimal dasselbe
   gelöst wurde, ohne die erste Lösung abzulösen. Konsolidierung behebt die Ursache, warum
   es keine prüfbare SSoT gibt.
2. **Die Lösungsinfrastruktur existiert schon** (Staging, 53 Ports, Secrets) — nur der Gate
   fehlt. Der teure Teil ist abgeschrieben, der billige fehlt.
3. **Das Muster ist im Haus bewiesen** (ci-green-program/ADR-209) — kein Experiment, sondern
   Übertragung eines validierten Rezepts auf die Nachbardomäne.

**Stärkster Einzel-Hebel (Steelman):** den Loop zuerst schließen — travel-beat blutet *jetzt*,
und ein geschlossener Canary-Loop ist der lebende Beweis für die übrigen Schichten.

## 5 Konzeptdefinition

**Kernthese:** Deployment wird von *merge=Prod + offener Beobachtung* zu *gegateter
Staging→Prod-Promotion + geschlossenem Signal→Gate-Loop*, verankert in **einer** kanonischen
ADR, die ihre Vorgänger **CI-erzwungen** supersedet. Drei **hart entkoppelte** Tracks statt
eines Monolithen:

- **T0 — Sofort-Incident (entkoppelt, kein Governance-Artefakt):** travel-beat 502 wird als
  Incident behandelt (Owner/Infra, `/incident`), **bevor** irgendeine Governance startet.
  Kein Programm-Meilenstein darf abgehakt werden, während ein bekannter Prod-Endpoint tot ist.
- **T-A — Konsolidierung mit erzwungener Supersession:** eine kanonische Deployment-ADR mit
  `supersedes: [ADR-021, ADR-075, ADR-120, ADR-156, ADR-166, ADR-193, ADR-210]` (tatsächliche
  Teilmenge im ADR zu bestimmen) **plus** ein CI-Check (analog ADR-Frontmatter-Validator), der
  ein neues Deploy-ADR ohne `supersedes:`-Eintrag auf die Vorgänger **blockt**. Ohne diesen
  Check ist T-A wertlos.
- **T-B — Promotion-Pipeline mit Required-Check + Rollback-Vorbedingung:** merge→Staging (auto),
  gegatete Promotion Staging→Prod als **GitHub Required-Status-Check** (nicht nur informativ),
  mit **Rollback-Fähigkeit als harter Vorbedingung** (kein Gate ohne definierten Rückrollpfad).
  Der Canary-Loop wird geschlossen: (a) Upsert-Dedup (Ein-Funktion-Fix, sofort), (b)
  Schwellwert-Eskalation (N Wiederholungen → Deploy-Block oder Canary-Stummschaltung mit Owner).

**SSoT-Prüfung:** Erzeugt T-A eine zweite Wahrheit? Nein — im Gegenteil, es *reduziert* von
~15 auf 1, und der CI-Check verhindert die Wiederentstehung. **Boundary-Threshold:** T-B führt
einen neuen erzwungenen Schritt (Promotion-Gate) ein — gerechtfertigt, weil merge=Prod die
teuerste latente Klasse (unverifizierte Prod-State-Änderung) darstellt.

## 6 Adversariale Analyse (drei unabhängige Agenten)

### 6.1 Konfliktmatrix (belegter Dissens)

| # | Frage | Steelman | Advocatus Diabolus | Maintainer-2028 | Auflösung |
|---|---|---|---|---|---|
| K1 | Was zuerst? | Loop schließen (Schicht 3) | Sofort-Track (502) HART entkoppeln, dann Upsert-Fix | Supersedes + CI-Gate (Schicht 1) | **Alle drei, in Reihenfolge T0→T-A→T-B**; Dissens ist Sequenz, nicht Substanz |
| K2 | 30-Issue-Problem | „Loop erstickt im Rauschen" | **>80% nur Upsert-Bug** (1-Fn-Fix), kein Programm nötig | „Alert-Fatigue-Schuld, Remediation-Pfad fehlt" | Diabolus gewinnt für (a); (b) Eskalation bleibt echtes Gate-Thema |
| K3 | CI→Deploy-Analogie | „validiertes Rezept, 1:1 übertragbar" | **Trägt NICHT 1:1** — Deploy nicht idempotent/replaybar; „Selbstabschaltung" = ungegateter Prod-Merge | (implizit: Exit-Kriterium ja, aber Mechanik anders) | **Diabolus gewinnt** — Rollback-Fähigkeit wird harte Vorbedingung (in §5 T-B aufgenommen) |
| K4 | Was macht es durabel? | „Best-Case: SSoT + geschlossener Loop" | „CI-erzwungene Supersession + Referenz-Pflicht" | **`supersedes:` + CI-Gate + datiertes Exit mit Träger** | **Maintainer gewinnt** — die JETZT-Festlegung (§13) |

**Kein-Dissens-Vermerk:** Alle drei konvergieren unabhängig darauf, dass (i) `supersedes: []`
der eigentliche Bug ist, (ii) ein Gate ohne GitHub-Required-Check ein Rubber-Stamp ist, und
(iii) travel-beat von keiner der Schichten gelöst wird.

### 6.2 Advocatus-Diabolus-Pflichtfragen

- **Doppelquelle?** T-A reduziert sie; Gefahr nur, wenn das ADR nur `related:` statt
  `supersedes:` setzt → §13-Klausel 1 verhindert es per CI.
- **SSoT nur behauptet?** Ja, solange kein Lint PRs gegen `deploy*.yml` auf die kanonische
  ADR-ID zwingt (Diabolus-Einwand 6). → aufgenommen als REC-4.
- **„Tool" wird zur Boundary?** Das Promotion-Gate ist bewusst eine Boundary (§5-Threshold).
- **Manuelle Pflicht ohne Enforcement?** Der Hauptfehler jeder Vorgänger-ADR. → alle RECs
  sind als CI-Check/Required-Status formuliert, nicht als Konvention.
- **„Sichtbar machen" schwächer als „verhindern"?** Ja — der Canary macht sichtbar, verhindert
  nichts. T-B (b) macht daraus Verhinderung (Schwellwert→Block).
- **Formal erfüllen, praktisch umgehen?** `/hotfix` + `/incident` sind die institutionalisierte
  Umgehung (Diabolus-Einwand 7). → REC-5: Hotfix/Incident-Deploys unterliegen **demselben**
  Gate oder einer bewusst separaten, ebenso erzwungenen Eskalationsstufe.

## 7 Deep-Dive: warum das CI-Rezept nicht 1:1 trägt

`ci-green-program` funktioniert, weil ein CI-Failure **idempotent, seiteneffektfrei,
beliebig replaybar** ist: Lint rot → Regel-als-Code → nächster Lauf grün, kein Schaden.
Ein Deploy-Failure ist das nicht: DB-Migrationen sind oft nicht rückstandsfrei rollbar, ein
502 hat echte Nutzer getroffen. „Selbstabschaltung" eines Deploy-Gates heißt **nicht** „Regel
weg, Test bleibt grün", sondern **„nächster Merge geht ungegatet nach Prod"** — das Gegenteil
der Absicherung. Konsequenz für das Design: die Selbstabschaltung des Deploy-Green-Programs
darf **nur** Standing-Automatik zurückziehen, **nie** das Promotion-Gate selbst; und jede
Gates-als-Code-Regel braucht eine **Rollback-Fähigkeit als Vorbedingung**, sonst schützt sie
das exakte Symptom (502) und nicht die Risikoklasse (unverifizierte Prod-State-Änderung).

## 8 Alternativen

| Alt | Beschreibung | Warum nicht (allein) |
|---|---|---|
| **A0 — Nichts tun** | Status quo: merge=Prod, Canary spammt | Verschleppt travel-beat + wachsenden ADR-Sprawl; der Schmerz ist belegt real |
| **A1 — Nur Canary-Upsert-Fix** | 1-Funktion-Dedup, sonst nichts (Diabolus-Minimal) | Löst das sichtbare Symptom, nicht merge=Prod noch den ADR-Sprawl; ehrlicher Quick-Win, aber kein „optimale Methode" |
| **A2 — Nur ADR-Konsolidierung** | T-A ohne T-B | SSoT auf Papier, Fluss bleibt merge=Prod; ohne Gate kein Verhaltensänderung |
| **A3 — Vollprogramm (empfohlen)** | T0+T-A+T-B, entkoppelt, mit Enforcement + Exit | Höchster Aufwand, aber einziger, der *strukturell* + *self-improving* ist |
| **A4 — Managed PaaS** (z.B. externes CD) | Deploy-Governance auslagern | Widerspricht Hetzner/Single-Tenant-Souveränität (ADR-157/198); Owner-Exit-Risiko |

## 9 Out-of-the-Box

- **Deploy-Gate als „Progressive Delivery":** statt binärem Staging→Prod ein Canary-Rollout
  (1%→100%) mit automatischem Rückroll bei Health-Abfall — macht die Rollback-Vorbedingung
  aus §7 zur Laufzeit-Eigenschaft statt zur Doku.
- **Der Canary als Gate-Input, nicht nur Alarm:** dieselbe `prod-uptime-canary`-Prüfung, die
  heute Issues erzeugt, wird der Post-Promotion-Health-Check — ein Signal, zwei Zwecke, keine
  zweite Wahrheit.
- **ADR-Sprawl-Gate generalisieren:** der CI-Check „neues X-ADR muss Vorgänger supersedieren"
  ist nicht deploy-spezifisch — als allgemeiner ADR-Lint verhindert er künftigen Sprawl in
  *jeder* Domäne (auth, secrets, ports).

## 10 Befunde

| # | Befund | Beleg | Schwere |
|---|---|---|---|
| B1 | 2× „unified" ADR accepted, keiner supersedet; 2× proposed seit Monaten | C1–C4 | hoch |
| B2 | merge=Prod (`on: push`); Staging ist Parallelspur, kein Gate | C7 | hoch |
| B3 | Canary-Loop offen: erkennt 502 korrekt, 30 Issues/1 Vorfall, kein Upsert | C5 | hoch |
| B4 | travel-beat.iil.pet 502 — **laufender realer Prod-Ausfall** | C5 | kritisch |
| B5 | 2 Deploy-Reusables parallel (`_deploy-hetzner` + `_deploy-unified`) | C7 | mittel |
| B6 | `/hotfix` + `/incident` = institutionalisierte Gate-Umgehung | C8 | mittel |
| B7 | CI-green-Blaupause hat messbares Exit, aber es hat nie gefeuert (kein Träger) | C6 | mittel |

## 11 Top-5-Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R1 | Konsolidierungs-ADR wird Sprawl-Beitrag #7 (nur `related:`, kein Gate) | **CI-erzwungene Supersession** als Definition-of-Done (§13-Klausel 1) — nicht verhandelbar |
| R2 | Promotion-Gate bleibt Rubber-Stamp (kein Required-Check, `/hotfix`-Bypass) | GitHub Required-Status-Check pro Repo + Hotfix unterliegt demselben Gate (REC-5) |
| R3 | „Selbstabschaltung" wird zum ungegateten Prod-Merge (falsche CI-Analogie) | Selbstabschaltung zieht nur Standing-Automatik zurück, nie das Gate (§7) |
| R4 | Programm läuft, travel-beat bleibt 502 (Governance statt Remediation) | T0 hart entkoppelt; kein Meilenstein bei totem Endpoint (§5) |
| R5 | Exit-Kriterium wird Zombie (nie gemessen, wie ci-green heute) | Datiertes Wiedervorlage-Issue mit benanntem Prüf-Owner (§13-Klausel 2) |

## 12 Empfehlungen (konkret, verifizierbar)

- **REC-1 (T0):** travel-beat 502 als `/incident` behandeln — Owner/Infra, **vor** T-A/T-B.
  *Nicht* Teil dieses Konzepts, aber Vorbedingung für seinen Start.
- **REC-2 (T-A):** Kanonische Deployment-ADR entwerfen mit `supersedes:`-Liste + einem
  CI-Check in `tools/` (analog `reference_adr_frontmatter_schema_strict`), der ein neues
  Deploy-ADR ohne Supersession-Eintrag blockt.
- **REC-3 (T-B):** In **einem** Pilot-Repo (Vorschlag: ein nicht-kundenkritisches wie
  travel-beat nach REC-1) merge→Staging + Required-Status-Promotion→Prod verdrahten, mit
  definiertem Rollback-Pfad. Erst nach grünem Pilot ausrollen.
- **REC-4:** Lint „PR gegen `deploy*.yml`/`_deploy-*.yml` muss kanonische ADR-ID referenzieren"
  (Soft-Fail mit Hinweis), damit SSoT beim nächsten Deploy-Change konsultiert wird.
- **REC-5:** `/hotfix` + `/incident`-Deploys demselben Promotion-Gate unterwerfen ODER einer
  bewusst separaten, ebenso erzwungenen Eskalationsstufe — kein by-Konvention-Bypass.
- **REC-6:** Canary-Upsert-Dedup (find-or-update by title/label) als **eigenständiges,
  sofort umsetzbares Ticket** — nicht im Programm verstecken (Diabolus K2).

## 13 Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (Owner):** Ist das ein org-weiter ADR wert (mein Urteil: **ja** — SSoT-Reversal
+ neuer erzwungener Prod-Schritt + Cross-Repo = ADR-Schwelle klar überschritten), oder erst der
Minimal-Pfad A1+REC-2 als Vorstufe?

**Die eine dringendste JETZT-Festlegung (Maintainer-2028), zwei erzwingbare Klauseln im
kanonischen ADR:**
1. `supersedes: [...]` im Frontmatter **plus** CI-Check, der künftige „unified/reliable/final"
   Deploy-ADRs ohne Supersession blockt. **Der einzige Hebel, der Anlauf 7 von Anlauf 8 trennt.**
2. Datiertes, gemessenes Exit-Kriterium nach ci-green-Vorbild (z.B. „≥90% Repos auf
   Promotion-Pipeline UND alte Reusables 0 aktive Consumer über 30 Tage → Alt-Pfade löschen,
   Gate-Doku retired") **mit konkretem Wiedervorlage-Issue + Prüf-Owner** — nicht nur Text.

**Kill-Gate (messbar):** siehe Frontmatter `kill_criteria` — 60 Tage, keine der zwei
Mindest-Bewegungen (T-A-Gate gemergt ODER 1 Repo mit Required-Promotion) → sunset.
**Exception-Budget:** eine 30-Tage-Verlängerung, datiert dokumentiert, danach hart sunset.

**30/60/90:**
- **30 Tage:** REC-1 (travel-beat grün) erledigt; REC-6 (Canary-Upsert) gemergt; kanonische
  Deployment-ADR als *proposed* mit `supersedes:`-Liste + Supersession-CI-Check als Draft-PR.
- **60 Tage:** ADR *accepted*, Supersession-Gate live; T-B-Pilot in 1 Repo grün (Required-Check
  + Rollback-Pfad verifiziert).
- **90 Tage:** Rollout-Plan mit Cutover-Terminen für die Alt-Reusables; Exit-Kriterium als
  Wiedervorlage-Issue mit Owner + Datum angelegt.

---

*Adversariat: 3 unabhängige Agenten (Steelman/Diabolus/Maintainer-2028), blind zueinander,
Synthese mit Konfliktmatrix §6.1. Belege: `evidence_manifest`. Dieses Konzept ist die Stufe
vor ADR — es entscheidet nichts, es macht entscheidungsreif.*
