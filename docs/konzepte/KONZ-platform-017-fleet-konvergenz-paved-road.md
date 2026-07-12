---
concept_id: KONZ-platform-017
title: "Fleet-Konvergenz: Paved Road statt Insellösungen (Vollzug vor Neubau)"
pipeline_status: idea
tier: T3
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "kein neues ADR — ausschließlich Vollzug/Amendments bestehender Entscheide (ADR-257, ADR-021 §2.17, ADR-242/270, KONZ-003); begründet in §5.4/§12"
review_by: "2026-10-12"
kill_criteria: "T+90 (2026-10-12): (a) shared-ci-Versions-Streuung wird nicht MASCHINELL gemessen (kein grüner Meter-Lauf-Beleg, Handmessung zählt nicht) ODER (b) maschinell gemessene Streuung nicht ≤3 Versionen ODER (c) ≥1 nach W0 neu onboardetes Repo mit floating @main-CI geboren (Zufluss nicht gestoppt) ODER (d) ≥1 neuer Prod-Incident der drei Lücken-Klassen (Runner-OOM, Secret-not-found, GHCR-403), den der jeweils zuständige Mechanismus nicht detektiert hat → Rückbau auf Einzelmaßnahmen, Meter-Erweiterung entfernen, Befund als 🌀-Memory."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "docs/konzepte/KONZ-platform-015-transparente-stabile-infra-dev-staging-prod.md", commit_or_pr: "main, vollständig gelesen", opened_in_session: true}
  - {claim_id: C2, source_path: "docs/adr/ADR-257-ci-host-isolation-non-prod-runner.md", commit_or_pr: "accepted 2026-06-26, in-progress, §Status+Kontext gelesen", opened_in_session: true}
  - {claim_id: C3, source_path: "docs/konzepte/KONZ-platform-003-sops-secret-migration.md", commit_or_pr: "idea, review_by 2026-07-15 (Frontmatter gelesen)", opened_in_session: true}
  - {claim_id: C4, source_path: "iilgmbh/shared-ci .github/workflows/ (7 Reusables) + _deploy-unified.yml PROJECT_PAT-Pfad Z.86-210", commit_or_pr: "lokaler Klon + Tag v1.0.8 via git show", opened_in_session: true}
  - {claim_id: C5, source_path: "Prod-Host-Kapazität: nproc=12, 22GB RAM (19GB belegt, Swap voll), 25 /opt/actions-runner-*", commit_or_pr: "SSH root@88.198.191.108, 2026-07-12", opened_in_session: true}
  - {claim_id: C6, source_path: "cad-hub Run 29101278323 (xdist 'node down' gw8/gw3, INTERNALERROR) + Fix-PR cad-hub#39 (gemergt)", commit_or_pr: "Log via gh api gelesen; PR selbst erstellt", opened_in_session: true}
  - {claim_id: C7, source_path: "coach-hub Run 28778482259 ('secret PROJECT_PAT: not found', Dockerfile:28) / trading-hub 28871146456 + pptx-hub 29014009002 (GHCR 403)", commit_or_pr: "Logs via gh api gelesen", opened_in_session: true}
  - {claim_id: C8, source_path: "Fleet-Scan 62 Repos: 22 App-Hubs auf shared-ci, 6 Versionen v1.0.1–v1.0.9 gleichzeitig, In-Repo-Drift learn-hub/travel-beat, 2 Reusable-Quellen, 5 Deploy-Außenseiter", commit_or_pr: "Subagent-Scan lokaler Klone 2026-07-12 (Caveat: lokal, nicht origin/main)", opened_in_session: true}
  - {claim_id: C9, source_path: ".windsurf/workflows/onboard-repo.md:453 — pinnt neue Repos auf achimdehnert/platform/_ci-python.yml@main", commit_or_pr: "Subagent-verifiziert (Diabolus AD-3), Zeile geöffnet", opened_in_session: true}
  - {claim_id: C10, source_path: "scripts/drift_check.py (check_shared_ci_tag_drift, Z.436) — einziger Workflow-Aufrufer ist tools-tests.yml (Unit-Test)", commit_or_pr: "Subagent-verifiziert (AD-2), grep über .github/workflows/", opened_in_session: true}
  - {claim_id: C11, source_path: "Issue #998 (sync-drift-meter seit Merge #951 ohne validen Lauf, Pfad-Mismatch) + Issue #1076 (Entbürokratisierung, Owner-Entscheid 2026-07-11) + Issue #1065 (rollendes Fleet-Drift-Issue)", commit_or_pr: "Subagent-verifiziert (M28) via gh issue view", opened_in_session: true}
  - {claim_id: C12, source_path: "docs/adr/ADR-268-projekt-assurance-tiers.md — Policy-Funktion f 'unimplementiert/dormant'", commit_or_pr: "Subagent-verifiziert (AD-8), Z.161-191", opened_in_session: true}
  - {claim_id: C13, source_path: "docs/runbooks/ghcr-403-push-actions-access.md (PR #967, gemergt)", commit_or_pr: "Subagent-verifiziert (Steelman), Datei existiert", opened_in_session: true}
  - {claim_id: C14, source_path: "AGENT_HANDOVER.md §0 Prioritäten-Tabelle als existierendes Rollout-Tracking", commit_or_pr: "Subagent-verifiziert (AD-4), Z.42-49", opened_in_session: true}
created: "2026-07-12"
---

# KONZ-platform-017 — Fleet-Konvergenz: Paved Road statt Insellösungen

> Auftrag (Achim, 2026-07-12): *"strategisches Ziel: eine strategisch ausgerichtete, stabile
> Infrastruktur über alle Repos hinweg. Ablösung von individuellen Lösungen (z.B. beim Deployment,
> Testing, ...) hin zu geplanter, architektonisch sauberer Infra. Prädiktiv statt reaktiv."*
> Tier: **T3** (Cross-Repo, org-weit, berührt SSoT-Fragen — Auto-Eskalation greift dreifach).
> Adversariat: Steelman / Advocatus Diabolus / Maintainer-2028 als drei blinde Agenten +
> Fable-5-Synthese mit Konfliktmatrix (§6.4). Schwester-Dokument: KONZ-015 (Drift-Achse, pilot).

## 1. Executive Summary

**Empfehlung: als MVP annehmen — mit einem Zuschnitt, der nach dem Adversariat bewusst kleiner
ist als der Erstentwurf.** Die tiefe Analyse ergab einen Befund, der den Charakter des Konzepts
bestimmt: Diese Plattform hat **kein Normen- und kein Tooling-Defizit, sondern ein
Vollzugs-Defizit plus drei echte Regelungslücken.** Die Normen existieren (ADR-264 kanonischer
Deploy, ADR-268 Assurance-Tiers, ADR-242 Required Checks, ADR-270 Merge-Automation, ADR-057/058
Testing, ADR-021 §2.17 Compose-Vertrag, ADR-257 CI-Host-Isolation) — aber fast alle sind
*accepted-but-not-rolled-out*. Das Tooling existiert (~40 Mechanismen, 15+ automatisierte Sweeps
und Meter) — aber der jüngste Meter dieser Klasse lief seit Geburt kein einziges Mal valide
(Issue #998). Die Konvergenz auf die Paved Road ist bereits Mehrheit (22 von 29 App-Hubs auf
shared-ci) — aber mit **6 gleichzeitig lebenden Versionen** (v1.0.1–v1.0.9), zwei parallelen
Reusable-Quellen und einem Onboarding-Skill, der neue Repos **auf der falschen Quelle gebiert**
(`onboard-repo.md:453` pinnt auf floating `platform@main` — der stärkste Einzelfund des
Adversariats: der Zufluss von Insellösungen war nie gestoppt, nur der Bestand poliert). Die drei
Regelungslücken sind keine Theorie, sondern die Root Causes der Prod-Incidents **dieser Woche**:
Runner-Kapazität (25 Runner auf einem 12-Core/22-GB-Host → xdist-OOM in cad-hub und weltenhub),
Secrets-Lifecycle (coach-hub `secret PROJECT_PAT: not found`), Package-/GHCR-Governance
(trading-hub + pptx-hub 403). „Prädiktiv statt reaktiv" heißt deshalb hier nicht „mehr Scanner"
— es heißt: **zentrale Defaults statt Per-Repo-Pflaster, Zufluss-Stopp vor Bestands-Sanierung,
Vollzug vor Neubeschluss, und jede neue Detektion nur als Erweiterung eines bewiesenen Meters.**
Das MVP besteht aus drei Sofortmaßnahmen (W0, je ein PR bzw. ein Entscheid), einer 30-Tage-Welle
(W1) und einer gegateten 60/90-Tage-Welle (W2). Ausdrücklich gestrichen nach Adversariat: das
Rollout-Schulden-Board als neues Artefakt (existiert als `AGENT_HANDOVER.md` §0), der
Auto-Bump-Bot vor bewiesener Meter-Klasse (M28-1), und jede Kopplung an die dormante
ADR-268-Policy-Funktion (AD-8). Dieses Konzept erzeugt **kein neues ADR** und **keinen neuen
Standing-Service** — es ist ein Vollzugs- und Härtungsprogramm im Geist des
Entbürokratisierungs-Entscheids #1076.

## 2. Scope & Evidenzbasis

**In dieser Session direkt verifiziert (Haupt-Session):** KONZ-015 vollständig (C1); ADR-257
Status+Kontext (C2); KONZ-003-Frontmatter mit `review_by: 2026-07-15` (C3); shared-ci-Katalog +
`_deploy-unified.yml`-Secret-Pfad (C4); Prod-Host-Kapazität live per SSH — 12 Cores, 22 GB
(19 GB belegt, Swap voll), **25 Runner-Verzeichnisse** unter `/opt/actions-runner-*` (C5); die
vier Incident-Logs dieser Woche im Wortlaut (C6, C7).

**Durch Erdungs-Agenten verifiziert (Dateien real geöffnet, Pfade im Manifest):** Fleet-Scan über
62 lokale Repo-Klone (C8, Caveat: lokale Klone ≠ origin/main); Tooling-Inventar (~40 Mechanismen,
Cron-Katalog); Normen-Extrakt der 10 Governance-Dokumente inkl. Lückenliste.

**Durch adversariale Agenten verifiziert:** C9–C14 (onboard-repo-Zeile, drift_check-Verdrahtung,
Issues #998/#1065/#1076, ADR-268-f-Status, GHCR-Runbook, Handover-Board).

**Als Hypothese markiert (nicht verifiziert):** (H1) Die Versionsstände aus dem lokalen
Fleet-Scan entsprechen origin/main — billigster Check: der Meter aus W1 misst gegen Remote.
(H2) Die beiden bereits per-repo gepatchten Hubs (cad-hub, weltenhub) sind die einzigen mit
`pytest_workers`-Override — der Default-Flip W0-3 wirkt auf alle anderen; Zählung liefert der
Meter. (H3) GHCR-„Manage Actions access" bleibt API-unlesbar (🌀-Memory + Runbook sagen ja) —
falls GitHub das ändert, wird P4 härtbar.

## 3. Infrastruktur-Fit (Wiederverwenden vor Erfinden)

| Baustein | Status | Rolle in diesem Konzept |
|---|---|---|
| shared-ci (`iilgmbh/shared-ci`, 7 Reusables, v1.0.x) | live, 22 Consumer | **Die** Paved Road — einzige Quelle nach W1; Träger der zentralen Defaults (W0-3) |
| ADR-257 (CI runter vom Prod-Host) | accepted, in-progress, Pilot travel-beat | Der strukturelle Kapazitätsfix; W2 = Pilot abschließen, nicht neu entscheiden |
| KONZ-003 (SOPS-Secret-Migration) | idea, **review_by 2026-07-15** | Secrets-Achse existiert als Konzept — W0-1 erzwingt den Entscheid vor Ablauf |
| sync-drift-meter (ADR-265 REC-3) | live-aber-kaputt seit Geburt (#998) | Einziger Meter der benötigten Klasse — W1-Reparatur ist der Existenzbeweis, DANN Erweiterung um Versions-Spread (statt viertem Parallel-Meter) |
| `drift_check.py::check_shared_ci_tag_drift` | existiert, läuft nirgends (C10) | Wird als **Bibliothek** vom reparierten Meter importiert — nicht separat verdrahtet |
| GHCR-Runbook (PR #967) | gemergt | W1: Verweis als Pflichtschritt in onboard-repo; ehrliche Grenze: nicht präventiv erzwingbar (H3) |
| onboard-repo-Skill | aktiv, **gebiert Repos auf @main** (C9) | W0-2: Template-Fix — Zufluss-Stopp |
| Deploy-Health-Scan (session-start 0.7) + deploy-failure-monitor (6h-Cron) | live | Bleibt die Detektionslinie für die GHCR-/Secrets-Klasse — keine Neuerfindung |
| AGENT_HANDOVER.md §0 + Issue-Labels | live (C14) | **Ist** das Rollout-Schulden-Board — kein neues Artefakt (Streichung nach AD-4/M28-4) |
| KONZ-015 Reconcile-Sweep | pilot, täglich | Schwester-Achse (deklariert↔real); dieses Konzept ergänzt die Achse Quelle↔Konsument (Versionen), keine Überlappung |

## 4. Steelman (kondensiert)

Die Kernthese ist im Repo bereits zweimal unabhängig repliziert, bevor dieses Konzept existierte:
ADR-264 diagnostiziert den Deploy-Sprawl explizit als Governance-Lücke („der Bug ist das leere
`supersedes:`-Feld, nicht die ADR-Anzahl"), und ADR-270 bewies live, dass **ein** zentraler
Default-Wechsel (`strict=false`) einen fleet-weiten Stau sofort auflöste. „Zentrale Defaults
schlagen Per-Repo-Reparatur" ist hier also keine Hypothese, sondern Replikation. Der stärkste
Hebel des Pakets ist mechanisch verifiziert: `pytest_workers` ist ein bestehender Input der
Reusable-Workflows — ein Default-Flip in der Quelle wirkt auf alle Consumer ohne
Consumer-Koordination und ist trivial revertierbar. Die GHCR-Maßnahme kostet fast nichts (Runbook
existiert fertig). Und die Rollout-Schulden-These ist ADR-eigen dokumentiert (ADR-268 nennt seine
eigene Enforcement-Grenze; ADR-270 steht drei Tage nach Accept auf `not-started`) — das Konzept
erfindet die Diagnose nicht, es zitiert sie.

## 5. Konzeptdefinition

### 5.1 Kernthese

Fleet-Stabilität entsteht hier durch **Vollzug und Härtung des Bestehenden**: (1) Der Zufluss
neuer Insellösungen wird an der Geburtsstelle gestoppt (Onboarding-Template auf die versionierte
Paved Road), **bevor** der Bestand saniert wird; (2) die drei belegten Regelungslücken (Kapazität,
Secrets, Packages) werden über zentrale Defaults und erzwungene Entscheide geschlossen, nicht über
weitere Per-Repo-Pflaster; (3) neue Detektion entsteht ausschließlich als Erweiterung eines
nachweislich funktionierenden Meters (wire-before-extend, KONZ-015-Doktrin — angewandt auch auf
dieses Konzept selbst); (4) es wird nichts Neues beschlossen, solange der Beschluss-Bestand nicht
vollzogen ist — dieses Konzept erzeugt darum kein neues ADR und keinen neuen Standing-Service.

### 5.2 Problem (verifiziert)

1. **Versions-Fragmentierung der Paved Road:** 22/29 App-Hubs nutzen shared-ci — aber in 6
   gleichzeitigen Versionen (v1.0.1–v1.0.9); zwei Repos fahren CI und Deploy im selben Repo auf
   verschiedenen Versionen (learn-hub, travel-beat); 8 Repos hängen an der zweiten, floating
   Quelle `platform@main` (C8).
2. **Zufluss ungestoppt:** Der Onboarding-Skill selbst pinnt neue Repos auf `platform@main`
   (C9) — jede Neuanlage vergrößert die Divergenz, die saniert werden soll.
3. **Kapazität ungeregelt:** 25 Runner teilen sich einen 12-Core/22-GB-Host (C5); `pytest -n auto`
   spawnt dort 12 Worker je Job → OOM-Crashes (C6), bisher zweimal per-repo gepflastert.
4. **Secrets-Lifecycle ungeregelt:** PAT-Klasse-Secrets scheitern lautlos (C7); die konzipierte
   Lösung (KONZ-003/SOPS) verfällt in drei Tagen ungenutzt (C3).
5. **Package-Governance ungeregelt:** GHCR-Zugriff ist Owner-UI-only, nicht API-prüfbar; zwei
   403-Incidents diese Woche (C7); einzige Verteidigung ist nachlaufende Detektion.
6. **Vollzugs-Defizit als Median:** ADR-270 `not-started`, ADR-242 Wave 3 bei 16/23, ADR-264 D2
   unimplementiert, ADR-021 §2.17 pending, ADR-268-f dormant (C12), 13/17 KONZ-Dokumente über
   `review_by` hinaus in `idea` (M28-5).

### 5.3 Zielbild (T+90)

Ein neues Repo wird **konvergiert geboren** (versionierte shared-ci-Referenz aus dem Template).
Die Versions-Streuung der Paved Road wird **maschinell gemessen** (reparierter sync-drift-meter)
und liegt bei ≤3 gleichzeitigen Versionen mit Korridor-Regel „max 2 Minor hinter latest". Die
Runner-OOM-Klasse ist durch den zentralen Worker-Default strukturell entschärft und die CI-Last
verlässt den Prod-Host (ADR-257-Pilot abgeschlossen). Die Secrets-Frage hat einen gefallenen
Entscheid (KONZ-003 accept/reject/rescope — nicht verrottet). Kein neuer Standing-Service, kein
neues Board, kein neues ADR.

### 5.4 Nicht-Ziele

- **Kein neues Standardisierungs-ADR.** Alles hier ist Vollzug/Amendment bestehender Entscheide.
  (Die Erstentwurfs-Regel „kein neues ADR solange >N offen" wurde nach AD-12 gestrichen —
  unenforced und selbstwidersprüchlich; die ehrlichere Form ist, dass dieses Konzept selbst mit
  gutem Beispiel vorangeht.)
- **Keine Registry-SSoT-Entscheidung** — das ist ADR-273-Kandidat (ADR-272 §6.3). Der
  Konvergenz-Meter nimmt als Nenner die deploy-relevanten Repos aus `canonical.yaml` und
  deklariert diese Grenze im Report (AD-6-Mitigation), statt auf die Registry-Konsolidierung zu
  warten oder sie implizit zu präjudizieren.
- **Keine Kopplung an ADR-268-Tiers in diesem Programm** — die Policy-Funktion `f` ist dormant
  (C12); Kopplung wird Option nach deren Bau, nicht Abhängigkeit davor (AD-8-Mitigation).
- **Keine Zwangskonvergenz der Souveränitäts- und Sonderfälle** (ttz-hub, meiki-*, odoo-hub
  SOPS-Deploy, bahn-hub; bfagent ist eingefroren) — sie werden als dokumentierte Ausnahmen mit
  Begründung im Meter-Report geführt, nicht als Verstoß gezählt.
- **Kein Auto-Bump-Bot in diesem Zuschnitt** (M28-1: die Mechanik-Klasse ist unbewiesen, solange
  #998 offen ist; ein Bot mit PR-Rechten über 25 Repos hat höheres Schadenspotential als sein
  Vorläufer). Bump-Wellen laufen manuell/als Sonnet-Sessions, bis der Meter 4 Wochen grün lief.

### 5.5 Maßnahmen (drei Wellen, jede Zeile = ein PR oder ein Entscheid)

**W0 — Sofort (diese Woche; stoppt Zufluss + entschärft die akute Klasse):**

| # | Maßnahme | Mechanik | Warum zuerst |
|---|---|---|---|
| W0-1 | KONZ-003-Entscheid erzwingen | Human-Decision accept/reject/rescope vor 2026-07-15 (Ablauf `review_by`) | AD-11: sonst verfällt die einzige konzipierte Secrets-Lösung während dieses Programm läuft |
| W0-2 | Onboarding-Template auf Paved Road | `onboard-repo.md:453`: `platform/_ci-python.yml@main` → `iilgmbh/shared-ci/_ci-python.yml@v<latest>`; gleiches für Deploy-Vorlage | AD-3 (Killshot): Zufluss-Stopp ist Vorbedingung dafür, dass Kill-Gate (b) überhaupt erreichbar ist |
| W0-3 | Zentraler Worker-Default | `pytest_workers`-Default `'auto'` → `'4'` in `iilgmbh/shared-ci/_ci-python.yml` **und** der platform-Kopie; Consumer-Verifikation vor Tag (Memory-Lektion Reusable-WF) | Steelman-Hebel, präzisiert per AD-9: schützt die ungepatchte Mehrheit; die 2 gepatchten Repos behalten ihre Overrides |

**W1 — 30 Tage (beweist die Messklasse, dann erst erweitern):**

| # | Maßnahme | Mechanik |
|---|---|---|
| W1-1 | sync-drift-meter reparieren (#998) | Pfad-Mismatch fixen; **Existenzbeweis**: 2 aufeinanderfolgende valide Läufe mit dokumentiertem Output — Vorbedingung für W1-2 |
| W1-2 | Meter um Versions-Spread erweitern | `check_shared_ci_tag_drift()` aus `drift_check.py` als Import in den reparierten Meter (AD-1/AD-2-Auflösung: Konsolidierung statt viertem Meter, Bibliothek statt Zweitverdrahtung); Output: Spread-Zahl + Korridor-Verstöße (max 2 Minor hinter latest) + In-Repo-Drift (ci.yml ≠ deploy.yml) als drei Zeilen im bestehenden Issue-Report |
| W1-3 | GHCR-Pflichtschritt + ehrliche Grenze | onboard-repo: „Package → Manage Actions access (Write)" als Schritt mit Runbook-Link (C13); im Runbook dokumentieren, dass Prävention konstruktionsbedingt unmöglich ist (H3) und Detektion = Deploy-Health-Scan bleibt (AD-7 akzeptiert statt beschönigt) |
| W1-4 | PROJECT_PAT-Klasse inventarisieren | Read-only-Sweep: welche Repos referenzieren PAT-Secrets in Workflows/Dockerfiles (grep, kein neuer Standing-Job); Ergebnis als Input für den KONZ-003-Folgeentscheid (GitHub-App vs. Org-Secrets) |

**W2 — 60–90 Tage (gegatet auf W1-Existenzbeweis):**

| # | Maßnahme | Gate |
|---|---|---|
| W2-1 | Bump-Welle Bestand: v1.0.1/v1.0.2-Nachzügler (pptx, dms, recruiting, tax + Deploy-Seiten learn/travel-beat) auf Korridor heben | manuell/Sonnet-Session je Repo; Meter (W1-2) misst Fortschritt |
| W2-2 | platform-family-Migration: 7 Framework-Repos `_ci-pypi@main` → versionierte shared-ci-Referenz (shared-ci#20-Gate beachten: `_ci-pypi` braucht erst den gate-Job) | erst wenn shared-ci#20 gemergt; bfagent bleibt frozen-Ausnahme |
| W2-3 | ADR-257-Pilot abschließen (travel-beat CI auf Non-Prod-Runner), dann Staffel-Migration per `runs_on`-Input | bestehender ADR, nur Vollzug; entlastet den 22-GB-Host strukturell |
| W2-4 | T+90-Review mit automatischem Reminder | datiertes Issue bei Annahme dieses Konzepts anlegen (M28-9: `review_by`-Felder allein verfallen nachweislich — 13/17 KONZ) |

### 5.6 Enforcement-Modell (ehrlich)

| Regel | Level | Mechanismus |
|---|---|---|
| Neue Repos nur auf versionierter shared-ci-Referenz | prozessual (Template) — ehrlich: onboard-repo ist Doku, kein CI-Gate; kompensiert durch Meter-Zeile „Repos auf @main" die neue Verstöße sichtbar macht | W0-2 + W1-2 |
| Worker-Default zentral | hart (Reusable-Default wirkt ohne Consumer-Zutun) | W0-3 |
| Versions-Korridor max 2 Minor | Meter-Report (Detektion) — bewusst KEIN Merge-Gate: ein hartes Gate auf Versionsstand würde 22 Repos gleichzeitig rot schalten (Alarm-Müdigkeits-Klasse) | W1-2 |
| Secrets-Entscheid vor Verfall | prozessual, einmalig, datiert | W0-1 |
| GHCR-Zugriff | nicht erzwingbar (H3) — dokumentierte Grenze, Detektionslinie bleibt | W1-3 |

## 6. Adversariale Analyse

### 6.1 Advocatus Diabolus (12 Befunde, konserviert)

Kernangriffe: **AD-1** P5-Wochenreport dupliziert den existierenden sync-drift-meter statt ihn zu
nennen (hoch). **AD-2** Die „kein neues Tool"-Erweiterungsbasis `drift_check.py` läuft selbst
nirgends — wire-before-extend verletzt, dieselbe Fehlerklasse, die KONZ-015 diagnostizierte
(kritisch). **AD-3** onboard-repo gebiert Repos auf `platform@main` — der Zufluss war nie
gestoppt; kippt Kernthesen-Säule 4 und macht Kill-Gate (a) strukturell unerreichbar (kritisch).
**AD-4** Rollout-Schulden-Register dupliziert `AGENT_HANDOVER.md` §0 (mittel-hoch). **AD-5**
Kernthese „nicht mehr Scanner" widerspricht drei eigenen Maßnahmen (mittel). **AD-6** Konvergenz-
KPI auf ungelöster Registry-Doppelquelle = Zahl auf tönernem Fundament (hoch). **AD-7** GHCR-
Maßnahme ist „sichtbar machen", nicht „verhindern" (mittel). **AD-8** Kopplung an dormante
ADR-268-f ist Scheinkonkretheit (hoch). **AD-9** „EIN PR fixt Fleet" überschätzt — Default wirkt
nur auf Repos ohne Override (mittel). **AD-10** Kill-Gate-Metrik hat keinen maschinellen Messpfad
(hoch). **AD-11** P3-Timing kollidiert mit KONZ-003-Ablauf 07-15 (mittel). **AD-12**
„kein neues ADR solange >N offen"-Regel ist selbstwidersprüchlich (mittel).

### 6.2 Maintainer-2028 (9 Befunde, konserviert)

**M28-1** Auto-Bump-Bot: die Mechanik-Klasse ist am lebenden Beispiel seit Geburt kaputt
(sync-drift-meter, #998 — 0 valide Läufe, extern entdeckt, 4 Tage unangefasst); ein Bot mit
PR-Rechten über 25 Repos wiederholt das mit größerem Blast-Radius (hoch). **M28-2** Rollende
Report-Issues akkumulieren, konvergieren nie (Beleg #1065) (hoch). **M28-3** „kein neues Tool"
verdeckt, dass die operative Fläche (Cron+Issue-Upsert) neu ist (mittel). **M28-4** Manuell
gepflegtes Board ohne Vorläufer-Artefakt stirbt nach 2–3 Zyklen (hoch). **M28-5** `review_by`
ist Deko: KONZ-004 bereits 3 Tage abgelaufen, 13/17 KONZ nie über `idea` hinaus (mittel).
**M28-6** „accepted ⇒ Vollzug" widerlegt sich live: ADR-270 3 Tage nach Accept `not-started`,
ADR-021 §2.17 41 Tage pending (hoch). **M28-7** Owner steuert aktiv GEGEN Dauerlast
(Entbürokratisierungs-Entscheid #1076 vom Vortag) — der Entwurf addiert 6 wiederkehrende
Verpflichtungen auf ein 2-Personen-Team (hoch). **M28-8** Meter ohne Abschalt-Bedingung laufen
ewig (mittel). **M28-9** T+90 ohne automatischen Reminder verfällt wie jedes `review_by` (mittel).

### 6.3 Steelman-Gegengewichte

Kernthese doppelt repliziert (ADR-264-Postmortem + ADR-270-Live-Beweis); W0-3-Mechanik durch
Dateibeleg verifiziert (Input existiert, Default-Flip wirkt via Reusable); GHCR-Runbook fertig;
Rollout-Schulden-Diagnose ADR-eigen; P2-Klasse (Ein-PR-Fixes) hat das beste
Aufwand/Wirkungs-Verhältnis des Programms und minimale Alterungsrisiken (M28 stimmt hier zu).

### 6.4 Konfliktmatrix (Pflicht bei T3)

| # | Konflikt | Positionen | Auflösung in diesem Dokument |
|---|---|---|---|
| K1 | Wirkung des Worker-Default-Flips | Steelman: „EIN PR fixt Fleet, bester Hebel" vs. AD-9: „wirkt nur auf Repos ohne Override" | Beide korrekt auf verschiedenen Mengen: Flip schützt die ungepatchte Mehrheit **prädiktiv**; Formulierung präzisiert (W0-3); Overrides bleiben. Zusätzliche Synthese-Korrektur: Flip muss in `iilgmbh/shared-ci` landen (Fleet-Quelle), Steelman hatte nur die platform-Kopie geöffnet |
| K2 | „Kein neues Tool" (P5) | Steelman: Erweiterungsziele existieren real vs. AD-2 + M28-3 (konvergent): Basis unverdrahtet, operative Fläche neu | Diabolus/M28 gewinnen: P5 umgebaut zu W1-1→W1-2 — erst Reparatur+Existenzbeweis des EINEN lebenden Meters, dann Erweiterung als Bibliotheks-Import; kein Parallel-Meter, kein separater Report |
| K3 | Dauerlast vs. Programm-Nutzen | M28-7: läuft #1076 entgegen vs. Steelman: Konvergenz spart Incident-Arbeit | M28 gewinnt strukturell: P6-Board gestrichen (AD-4 konvergent), Wochenkadenz → bestehende Meter-Kadenz, Auto-Bump-Bot raus aus dem Zuschnitt, Netto-Bilanz neuer Standing-Verpflichtungen = 0 (nur Erweiterung eines bestehenden Meters) |
| K4 | Kill-Gate-Messbarkeit | Kill-Gate-Entwurf (a) „6→≤3" vs. AD-10: keine Maschinenmessung | AD-10 gewinnt: Kill-Kriterium (a) verlangt jetzt zuerst den grünen Meter-Lauf; Handmessung disqualifiziert (Frontmatter) |
| K5 | Onboarding | Entwurf: „onboard-repo template-basiert" als 90d-Punkt vs. AD-3: aktive Gegenkraft, sofort | AD-3 gewinnt: W0-2, erste Maßnahme des Programms |
| — | Keine Divergenz | Alle drei Agenten konvergieren auf: Ein-PR-Fixes (W0-Klasse) behalten; GHCR ehrlich als Detektions-Grenze führen; KONZ-003-Frist ist real | übernommen |

## 7. Deep-Dive: die drei Regelungslücken

**Kapazität (Runner):** Die Architektur-Entscheidung existiert bereits — ADR-257 (accepted,
in-progress) trennt CI vom Prod-Host; der Migrationshebel (`runs_on`-Input) ist laut ADR-257
Rev 3 bereits in shared-ci vorhanden, pro Repo steuerbar ohne shared-ci-Änderung. Was fehlte, war
(a) der zentrale Ressourcen-Default (W0-3 — 12 xdist-Worker × N parallele Jobs auf 22 GB ist
arithmetisch nicht tragfähig) und (b) der Vollzug des Piloten (W2-3). Dieses Konzept fügt der
Kapazitäts-Achse bewusst **keine** neue Governance hinzu (kein Budget-Framework, keine
Runner-Gruppen-Neuordnung) — erst wenn nach ADR-257-Vollzug weiterhin OOM-Incidents auftreten,
ist das ein neues Architektur-Thema mit eigener Evidenz.

**Secrets:** Der coach-hub-Fall (C7) zeigt die Klasse: build-zeitliche Secret-Injektion
(`--mount=type=secret` + `secrets: inherit`-Kette) scheitert lautlos mit `not found` — die Kette
Repo-Secret → Caller-Workflow → Reusable → Buildx hat keinen Prüfpunkt. KONZ-003 (SOPS) adressiert
die Lagerungs-Frage, nicht die CI-Ketten-Frage; beide gehören in denselben Entscheid (W0-1), und
W1-4 liefert das Inventar als Entscheidungsgrundlage. Keine Vorwegnahme der Lösung hier — der
Entscheid gehört dem Owner (Security-Gate).

**Packages/GHCR:** Konstruktionsbedingt nicht präventiv prüfbar (die granulare
Actions-Access-Liste ist API-unlesbar, H3/🌀-Memory). Die ehrliche Architektur ist deshalb:
Konvention im Onboarding (W1-3) + schnelle Detektion (Deploy-Health-Scan, 6h-Monitor) + fertiges
Runbook für die Reparatur. „Verhindern" wäre hier Scheinsicherheit — das Konzept sagt das offen,
statt ein unprüfbares Gate zu versprechen (AD-7 akzeptiert).

## 8. Alternativen

**A1 — Nur die vier Incidents fixen, kein Programm.** Bereits teilweise geschehen (cad-hub#39
gemergt, weltenhub live). Kauft den fünften Incident: die Klasse (ungepatchte Repos mit `-n auto`
auf demselben Host) bleibt scharf. Als Teilmenge in W0 enthalten.

**A2 — Big-Bang-Konvergenz: alle 22 Repos in einer Welle auf v-latest + hartes Versions-Gate.**
Maximal sauber auf dem Papier; real: 22 gleichzeitige PRs × Consumer-Verifikations-Pflicht bei
einem 2-Personen-Team, und ein hartes Gate schaltet die Fleet rot, bevor die Bump-Wellen laufen —
exakt die Alarm-Müdigkeits-Klasse der 🌀-Memory (advisory-scanner). Verworfen zugunsten
Korridor+Meter+manuelle Wellen.

**A3 — Vollzeit-Fokus auf Rollout-Schulden ohne neue Maßnahmen (reines Abarbeiten von
ADR-242/270/264/021).** Ehrlich und billig, aber lässt die drei Regelungslücken offen, aus denen
die aktuellen Incidents stammen — und stoppt den Onboarding-Zufluss nicht. Die W0-Welle ist
gerade der Teil, den A3 nicht liefert; W2 IST im Wesentlichen A3.

## 9. Out-of-the-Box (bewusst klein gehalten)

1. **Konvergenz als Geburtsattribut statt Sanierungsziel:** Der nachhaltigste Punkt des Programms
   ist W0-2 — er kostet eine Zeile und wirkt auf jedes künftige Repo. Sanierung altert,
   Geburts-Defaults nicht.
2. **Meter-Konsolidierung als Prinzip:** Die Org hat 4 Meter + 7 Sweeps; jede neue Messgröße wird
   Zeile in einem bestehenden Meter, nie neuer Workflow. (Hier angewandt; als org-weite Konvention
   Kandidat für ein ADR-265-Amendment — bewusst NICHT Teil dieses Konzepts, nur benannt.)
3. **Selbst-Test des Programms:** Der erste Meter-Lauf nach W1-2 muss die bekannten Ist-Zahlen
   (6 Versionen, 2 In-Repo-Drifts, 8 @main-Repos) reproduzieren — sonst misst er falsch.
   Bekannter Ist-Zustand als Testfall ist billiger als jede synthetische Testinfrastruktur.

## 10. Befunde (Auswahl; vollständige Rohbefunde §6.1/§6.2)

| ID | Kategorie | Befund | Evidenz | Schwere |
|---|---|---|---|---|
| F-1 | Zufluss | onboard-repo gebiert Repos auf floating @main | C9 | kritisch |
| F-2 | Messbasis | Einziger lebender Meter der Klasse seit Geburt kaputt | C11 (#998) | kritisch |
| F-3 | Kapazität | 25 Runner / 12 Cores / 22 GB; `-n auto`=12 Worker je Job | C5, C6 | hoch |
| F-4 | Vollzug | ADR-270 not-started, §2.17 pending 41d, ADR-268-f dormant, 13/17 KONZ in idea | C12, M28-5/6 | hoch |
| F-5 | Fragmentierung | 6 shared-ci-Versionen, 2 Quellen, 2 In-Repo-Drifts, 5 Deploy-Außenseiter | C8 (H1-Caveat) | hoch |
| F-6 | Organisation | Owner-Richtung ist Entbürokratisierung (#1076); Dauerlast-Budget ist ~0 | C11 | hoch (als Constraint) |
| F-7 | Secrets | KONZ-003 verfällt 2026-07-15 ungenutzt | C3 | mittel (zeitkritisch) |
| F-8 | Packages | GHCR-Access nicht API-prüfbar — Prävention unmöglich, nur Detektion | H3, C13 | mittel (akzeptierte Grenze) |

## 11. Top-5-Risiken

**R1 — Der reparierte Meter stirbt erneut (F-2-Rezidiv).** *Szenario:* #998-Fix hält einen Lauf,
bricht wieder, niemand merkt es — Kill-Gate (a) wird zur Handmessung. *Kleinster Fix:* Der Meter
meldet auch eigene Lauf-Lücken (letzter valider Lauf > 8 Tage → eigene Warn-Zeile im Issue);
Existenzbeweis-Kriterium (2 valide Läufe) vor jeder Erweiterung. *Restunsicherheit:* self-hosted-
Runner-Umgebung bleibt fragil (🌀 stale-toolcache).

**R2 — Bump-Wellen versanden nach der ersten (M28-Empirie).** *Szenario:* W2-1 hebt 3 Repos, dann
kommt ein Incident dazwischen, Rest bleibt; Streuung pendelt bei 4–5. *Kleinster Fix:* Kill-Gate
(b) misst absolut (≤3), nicht „Fortschritt"; Bump-Wellen sind Sonnet-delegierbar (execution-ready
pro Repo, Prep-for-Sonnet-Muster). *Restunsicherheit:* Consumer-Verifikations-Aufwand je Repo
schwankt.

**R3 — W0-3 erzeugt neue Test-Flakiness statt sie zu beheben.** *Szenario:* Repos mit vielen
Tests werden mit 4 Workern langsamer; jemand setzt lokal wieder `auto`. *Kleinster Fix:*
Consumer-Verifikation vor Tag-Bump (Memory-Pflicht) auf dem test-reichsten Consumer (risk-hub);
Laufzeit-Delta im PR dokumentieren. *Gegenbeleg:* cad-hub lief mit 12 Workern 17,5 s — 4 Worker
kosten dort Sekunden, keine Minuten.

**R4 — Der Zufluss-Stopp (W0-2) wird beim nächsten onboard-repo-Update überschrieben.**
*Szenario:* Skill wird regeneriert/aus anderem Repo kopiert, @main kehrt zurück (Drift-Klasse aus
ADR-272). *Kleinster Fix:* Meter-Zeile „Repos auf @main" (W1-2) fängt jedes neu geborene
@main-Repo — Detektionsnetz unter dem Template-Fix. *Restunsicherheit:* Latenz bis zum nächsten
Meter-Lauf (≤7 Tage).

**R5 — Programm konkurriert um dieselben 2 Personen wie die bestehenden Programme.** *Szenario:*
W0 läuft, W1/W2 verhungern neben ADR-242-Wave-3 und KONZ-015-Rollout — dritter Zustand
„angenommen-aber-ruhend" (exakt M28-5-Klasse). *Kleinster Fix:* W2 ist explizit gegatet (kein
Verspechen), T+90-Reminder automatisiert (W2-4), und das Kill-Gate baut bei Nichterfüllung
ehrlich zurück statt weiterzuschleppen. *Restunsicherheit:* real verfügbare Kapazität unbekannt.

## 12. Empfehlungen (nummeriert, konkret, mit Owner)

- **REC-1 (du, bis 2026-07-15):** KONZ-003-Entscheid fällen (accept/reject/rescope). Input: W1-4-
  Inventar folgt, aber der Frist-Entscheid darf darauf nicht warten — notfalls `review_by`
  begründet verlängern statt still verfallen lassen.
- **REC-2 (ich/PR, diese Woche):** onboard-repo.md-Template-Fix (W0-2) — eine Zeile CI-, eine
  Zeile Deploy-Referenz auf `iilgmbh/shared-ci@v<latest>`.
- **REC-3 (ich/PR + du/Tag-Freigabe, diese Woche):** `pytest_workers`-Default-Flip in shared-ci +
  platform-Kopie; Consumer-Verifikation auf risk-hub (test-reichster Consumer) vor Tag-Bump.
- **REC-4 (ich/PR, 30d):** #998-Fix; nach 2 validen Läufen Erweiterung um die drei
  Konvergenz-Zeilen (Spread, Korridor-Verstöße, @main-Zufluss) via `check_shared_ci_tag_drift`-
  Import. Nenner: deploy-relevante Repos aus `canonical.yaml`, Grenze im Report deklariert.
- **REC-5 (ich, 30d):** GHCR-Pflichtschritt in onboard-repo + Grenz-Absatz im Runbook; PAT-
  Inventar-Sweep (einmalig, read-only) als KONZ-003-Entscheidungs-Input.
- **REC-6 (du+ich, 60–90d, gegatet):** Bump-Welle W2-1 (Sonnet-delegierbar je Repo);
  platform-family-Migration W2-2 (nach shared-ci#20); ADR-257-Pilot-Abschluss W2-3.
- **REC-7 (ich, bei Annahme):** T+90-Reminder-Issue mit Datum 2026-10-12 + Kill-Gate-Checkliste
  aus dem Frontmatter anlegen (M28-9-Fix). Dieses Issue ist zugleich das Tracking-Artefakt für
  alles hier bewusst Aufgeschobene (Auto-Bump-Bot, ADR-268-Kopplung, Runner-Gruppen-Governance,
  Meter-Konsolidierungs-Konvention als ADR-265-Amendment-Kandidat).

## 13. Entscheidung + Kill-Gate + 30/60/90

**Empfehlung: als MVP annehmen** (W0 sofort, W1 nach W0, W2 gegatet). Nicht „Vollkonzept
annehmen" — der Erstentwurf enthielt vier adversarial falsifizierte Elemente (P5-Parallel-Meter,
P6-Board, Auto-Bump-Bot, ADR-268-Kopplung), die gestrichen sind. Nicht „ablehnen" — vier
Incidents in einer Woche aus drei benannten Lücken plus ein aktiv laufender Zufluss non-
konformer Repos haben messbare Kosten. Nicht „nur A1 (Incident-Fixes)" — der Zufluss-Stopp und
der zentrale Default sind billiger als der nächste Incident.

**Kill-Gate:** siehe Frontmatter `kill_criteria` (maschinelle Messung ist Teil des Kriteriums,
nicht nur der Zielwert). **Reminder automatisiert** via REC-7-Issue.

**30 Tage (bis 2026-08-11):** W0 komplett (KONZ-003-Entscheid gefallen; onboard-repo gefixt;
Worker-Default live mit Consumer-Verifikations-Beleg); #998 gefixt mit 2 validen Läufen.

**60 Tage (bis 2026-09-10):** Meter-Erweiterung live (3 Konvergenz-Zeilen im Report, Ist-Zahlen-
Selbsttest bestanden); GHCR-Schritt + PAT-Inventar erledigt; erste Bump-Welle begonnen.

**90 Tage (bis 2026-10-12):** Kill-Gate-Review am Reminder-Issue; Streuung ≤3 (maschinell
belegt); ADR-257-Pilot-Status berichtet; Entscheid über W2-Rest und über die aufgeschobenen
Kandidaten (REC-7-Liste) auf Basis der Meter-Empirie.
