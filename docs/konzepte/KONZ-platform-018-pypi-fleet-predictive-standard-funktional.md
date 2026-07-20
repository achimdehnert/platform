---
concept_id: KONZ-platform-018
title: "PyPI-Fleet: Predictive statt Repair · Standard statt Exception · Funktionales Portfolio"
pipeline_status: idea
tier: T3
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "kein neues ADR — Vollzug des ADR-266-Backlogs; einzige ADR-Berührung: ein ADR-266-Amendment NUR falls der Publish-Reusable-Entscheid (W2-E1) pro Reusable ausgeht (§5.4)"
review_by: "2026-10-12"
kill_criteria: "T+90 (2026-10-12): (a) Stub-Kohorte (Legacy-Name `aifw>=0.5.0`) nicht auf 0, MASCHINELL gemessen (Stub-Grep-Step, Handmessung zählt nicht) ODER (b) shared-ci `_ci-pypi.yml` weiterhin OHNE gate-Job (Doppelquelle ungelöst, shared-ci#20 offen) ODER (c) Consumer-Canary-Skript (ADR-266 3a) ohne dokumentierten Rot-Lauf gegen den Regressions-Korpus ODER (d) Portfolio-Entscheidungssession nicht stattgefunden (datiertes Protokoll fehlt) → Konzept-Rückbau: neue Artefakte entfernen, Rest-Items zurück in den ADR-266-Backlog, Befund als 🌀-Memory."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "registry/pypi-fleet.yaml (generated_at 2026-07-04T09:18Z, 21 Pakete)", commit_or_pr: "main, subagent-gelesen + Haupt-Session-Querchecks", opened_in_session: true}
  - {claim_id: C2, source_path: "docs/adr/ADR-266-pypi-fleet-lifecycle-und-publishing-konvergenz.md (K1–K7, Stufen, §owner_actions, Z.125 'Zentraler Publish: verworfen')", commit_or_pr: "accepted 2026-07-04, partial", opened_in_session: true}
  - {claim_id: C3, source_path: "docs/adr/ADR-226 (Pre-Publish-gitleaks bindend; deferred: _publish-pypi.yml 'consolidation target — separate ADR when scoped')", commit_or_pr: "accepted 2026-05-18, partial", opened_in_session: true}
  - {claim_id: C4, source_path: "docs/adr/ADR-222 (api-diff/Semver D4; status proposed, implementation none, eingefroren auf platform-doctor-Daten; platform_doctor.py läuft in keinem Workflow)", commit_or_pr: "proposed, Rev 4", opened_in_session: true}
  - {claim_id: C5, source_path: "shared-ci/.github/actions/install-iil-packages/action.yml Z.33-73 (Stub-Warnung wörtlich) + Z.157-185 (aifw-Freshness-Probe) + Z.102 (learn-hub#9-Breakage-Korpus)", commit_or_pr: "lokal + platform-Kopie, subagent-geöffnet", opened_in_session: true}
  - {claim_id: C6, source_path: "Stub-Pins: cad-hub/requirements.txt:36, 137-hub/requirements.txt:20, trading-hub/requirements.txt:56 (`aifw>=0.5.0,<1`)", commit_or_pr: "subagent-geöffnet; ttz-hub auf origin/main OHNE aifw-Pin (Haupt-Session git show) — Kohorte = 3, nicht 4", opened_in_session: true}
  - {claim_id: C7, source_path: "researchfw origin/main .github/workflows/publish.yml (needs: test + pytest — Gate VORHANDEN seit #7, 2026-06-30)", commit_or_pr: "Haupt-Session git show (Diabolus-AD-2-Falsifikation gegengeprüft)", opened_in_session: true}
  - {claim_id: C8, source_path: "Doppelquelle _ci-pypi.yml: platform-Kopie MIT gate-Job (Z.340, Commit 192b265) vs. iilgmbh/shared-ci-Kopie OHNE (endet bandit Z.302); promptfw konsumiert shared-ci@v1.0.8", commit_or_pr: "subagent-geöffnet (Diabolus AD-1)", opened_in_session: true}
  - {claim_id: C9, source_path: "aifw/CHANGELOG.md: Breaking Change bei 0.6.0 (AIActionType.code unique→db_index); 0.11.x ohne Breaking", commit_or_pr: "subagent-gegrept (Diabolus AD-7)", opened_in_session: true}
  - {claim_id: C10, source_path: "Konsumenten-Karte: iil-aifw ~18, iil-testkit ~16, iil-promptfw ~14, iil-platform-context ~13, iil-authoringfw ~10; riskfw 0 (auch risk-hub nicht), gaeb-toolkit 0, iil-django-commons 1, shared_contracts 0 cross-repo; writing-hub git+@main ×2 (outlinefw, researchfw)", commit_or_pr: "subagent-Sweep requirements*/pyproject über ~/github/*", opened_in_session: true}
  - {claim_id: C11, source_path: "Meter-Alterungs-Empirie: Issue #188 (ADR-Staleness rolling) Flagged-Count 12→32 über 7 Wochen, 0 menschliche Kommentare; #968 (pypi-fleet-health) 1 Lauf, 0 Kommentare; #752 (gate-backlog) leer", commit_or_pr: "subagent via gh issue view (M28-5)", opened_in_session: true}
  - {claim_id: C12, source_path: "ADR-266 §owner_actions K2-Backlog 'Stand 2026-06-30': alle 4 gelisteten Issues waren bei ADR-Accept bereits CLOSED", commit_or_pr: "subagent via gh (M28-7)", opened_in_session: true}
  - {claim_id: C13, source_path: "outlinefw: pyproject 0.3.2 vs PyPI 0.3.1, Tags bei v0.1.1 — 0.3.2 unreleased; weltenfw 0.4.1 unreleased; 5 Publisher ohne git-Tags", commit_or_pr: "Inventar-Subagent + pypi-fleet.yaml", opened_in_session: true}
created: "2026-07-12"
---

# KONZ-platform-018 — PyPI-Fleet: Predictive · Standard · Funktional

> Auftrag (Achim, 2026-07-12): *"scanne ALLE repos, die pypi packages 'bedienen', analysiere deren
> stand und mach strategische Entwicklungsvorschläge: 1. predictive statt repair, 2. standard statt
> exception, 3. funktionale weiterentwicklung mit adv diabolus und ootb denken."*
> Tier: **T3** (21 Package-Repos + ~25 Konsumenten-Repos, org-weit). Adversariat: Steelman+OOTB /
> Advocatus Diabolus / Maintainer-2028 als drei blinde Agenten + Fable-Synthese mit Konfliktmatrix.
> Schwester-Dokumente: KONZ-017 (Fleet-Konvergenz allgemein), ADR-266 (PyPI-Programm-ADR — dieses
> Konzept ist dessen Vollzugs- und Weiterentwicklungs-Plan, kein Konkurrenz-Rahmen).

## 1. Executive Summary

**Empfehlung: als MVP annehmen — als Vollzugs-Offensive für den ADR-266-Backlog plus drei gezielte
Weiterentwicklungen, NICHT als neues Programm.** Die Erdung über 21 Package-Repos und ~25
Konsumenten ergab: Das Zielraster existiert (ADR-266 K1–K7, accepted), zwei Meter laufen (täglich
Gate-Backlog, wöchentlich Fleet-Health), die CI-Konvergenz ist bei 18/19. Die echten Defizite
liegen woanders — und zwei davon hat erst das Adversariat dieses Konzepts freigelegt:

**(1) Funktional (dringendster Fund):** Drei Prod-Hubs (cad-hub, 137-hub, trading-hub) pinnen den
Legacy-Namen `aifw>=0.5.0` und laufen damit auf einem dokumentierten **STALE-STUB** — 8 Monate
Funktionsrückstand gegenüber iil-aifw 0.11.5, live, heute (C5, C6). Die Migration ist **kein
1-Zeilen-Fix**: dazwischen liegt ein dokumentierter Breaking Change (0.6.0, C9) — je Hub ein
execution-ready Issue mit Smoke-Plan. **(2) Standard:** Die Reusable-CI der Package-Fleet existiert
als **divergierte Doppelquelle** — die platform-Kopie von `_ci-pypi.yml` hat den gate-Job, die
shared-ci-Kopie nicht, und promptfw konsumiert bereits die schwächere (C8, shared-ci#20). Bevor
irgendein neuer Standard gebaut wird, muss diese eine Wahrheit wiederhergestellt sein — sonst
multipliziert jeder weitere Baustein die Divergenz. **(3) Predictive:** Der billigste echte
Prädiktions-Hebel ist schon in Produktion und wird nur nicht genutzt: die aifw-Freshness-Probe in
der install-Action (sie hat den Stub-Fund überhaupt erst ermöglicht) lässt sich zum generischen
Pattern heben — statt den Consumer-Canary (ADR-266 3a, seit Accept liegen geblieben) als schweren
CI-Umbau anzugehen, startet er als lokales Skript mit einem Regressions-Korpus aus den drei
dokumentierten Real-Breakages.

Das Adversariat hat den Erstentwurf substanziell korrigiert — vier Elemente gestrichen oder
umgebaut (§6.4): der „researchfw ohne Gate"-Fund war **falsch** (stale lokaler Klon — derselbe
🌀-Fehler, vor dem die eigene Memory warnt, zweimal in dieser Analyse passiert: auch die
ttz-hub-Zuschreibung fiel so), der geplante `_publish-pypi.yml`-Reusable kollidiert scheinbar mit
einer expliziten ADR-266-Verwerfung und wird zum sauber gerahmten **Entscheid** statt zur
Bau-Zusage, das api-diff-Gate ist ein unfinanziertes Versprechen (ADR-222 eingefroren an einer nie
gebauten Vorbedingung) und fliegt raus, und die Portfolio-Frage (riskfw mit **0 Konsumenten** —
nicht einmal risk-hub nutzt es; gaeb-toolkit 0; iil-enrichment tot; iil-django-commons 1) bekommt
eine **datierte Entscheidungssession** statt einer weiteren Zeile im wöchentlichen Meter-Issue,
dessen Gattung nachweislich ungelesen wächst (#188: 12→32 Findings in 7 Wochen, 0 menschliche
Kommentare — C11).

## 2. Scope & Evidenzbasis

**Erdung:** 3 parallele Agenten (Inventar über pypi-fleet.yaml + 21 lokale Repos; Governance-Extrakt
ADR-266/226/222/255 + Meter; Konsumenten-Karte über requirements*/pyproject aller Hubs). Adversariat:
3 blinde Agenten. **Haupt-Session-Gegenchecks gegen origin (nach zwei Stale-Clone-Fängen):**
researchfw-Gate (C7), ttz-hub-Pin (C6).

**Selbstkorrektur-Protokoll (Härtungs-Lektion dieser Analyse):** Zwei Erdungs-Befunde zerfielen am
origin-Check — „researchfw publiziert gate-los" (lokal 5 Commits behind; auf origin seit 30.06.
gefixt) und „4 Stub-Hubs" (ttz-hub hatte den Pin nur im stale Working-Tree; origin/main nutzt
litellm direkt). Konsequenz für alle W-Maßnahmen dieses Konzepts: **jeder Repo-Zustands-Claim wird
vor Umsetzung gegen origin/main re-verifiziert** (🌀 `feedback_stale_local_clone_never_ground_truth`
— hier empirisch doppelt bestätigt). Die Konsumenten-Zahlen (C10) tragen denselben Caveat.

**Als Hypothese markiert:** (H1) Konsumenten-Counts aus lokalen Klonen (±1 möglich). (H2) PyPI-seitige
Trusted-Publisher-Bindings sind headless nicht prüfbar (ADR-266-Grenze) — alle Auth-Aussagen betreffen
Workflow-Deklarationen, nicht PyPI-Serverzustand.

## 3. Infrastruktur-Fit (Wiederverwenden vor Erfinden)

| Baustein | Status | Rolle hier |
|---|---|---|
| ADR-266 K1–K7 + Stufenplan | accepted, partial | **Der Rahmen.** Dieses Konzept exekutiert dessen offene Punkte (3a Canary, Testkit-Dedup, owner_actions) und ergänzt drei Hebel — es ersetzt nichts |
| pypi-fleet-health.yml (wö.) + pypi-gate-meter (tägl.) | live | Detektionslinie bleibt; **kein neuer Meter** (M28-5: Gattung wächst ungelesen — #188-Empirie C11) |
| install-iil-packages Freshness-Probe (aifw-spezifisch) | **läuft produktiv** (C5) | Vorlage für den generischen Prädiktions-Hebel W1-3 — bewährter Mechanismus, kein Neubau |
| platform `_ci-pypi.yml` (MIT gate) vs. shared-ci-Kopie (OHNE) | **divergiert** (C8) | W1-1: Kanonizität wiederherstellen ist Vorbedingung für alles Weitere |
| shared-ci#20 | offen, Owner-gated | Der konkrete Fix für W1-1; blockiert Wave-3 Task B (outlinefw, promptfw) |
| ADR-226 Pre-Publish-gitleaks | bindend, live | bleibt unangetastet; `_publish-pypi.yml` ist dort als „consolidation target — separate ADR when scoped" vorgemerkt (C3) — Grundlage für Entscheid W2-E1 |
| ADR-222 api-diff (D4) | proposed/none, **eingefroren an nie gebauter Vorbedingung** (C4) | gestrichen als Zusage; bleibt Option nach funktionierendem Canary |
| ADR-255 Org-Migration | accepted, partial, owner-gated | Nicht-Ziel hier; W-Maßnahmen prüfen je Repo den Transfer-Status (AD-10: OIDC-Bindings sind owner-gebunden, „throwaway" bei Transfer) |
| Regressions-Korpus: learn-hub#9, platform#413/#416/#419 | dokumentiert in der install-Action (C5) | Testfälle für den Canary W2-1 — reale Breakages statt synthetischer Tests |

## 4. Steelman (kondensiert)

Die Faktenbasis hielt der adversarialen Prüfung in den tragenden Teilen stand: Stub-Pins wörtlich in
drei requirements.txt verifiziert, die Stub-Warnung steht als Klartext-Kommentar in der geteilten
install-Action, der Doppel-Publisher (testkit/iil-testkit) exakt im Registry-File, shared-ci#20
beschreibt den gate-Job-Mangel wortgleich. Der stärkste strukturelle Zug: Das Konzept **erfindet
nichts** — `_publish-pypi.yml` ist ein 2 Monate alter, in ADR-226 benannter Konsolidierungs-Auftrag;
Canary ist ADR-266 3a; die Portfolio-Kandidaten stehen im ADR-266-Handover. Es macht aus einem
liegen gebliebenen Backlog einen terminierten Plan mit Beweispflichten. Und der Prädiktions-Kern
(Freshness-Probe generalisieren) hebt einen Mechanismus, der seinen Wert bereits bewiesen hat — er
fand den wichtigsten Bug dieser Analyse.

## 5. Konzeptdefinition

### 5.1 Kernthese (entlang der drei Auftrags-Achsen)

**Predictive statt Repair** heißt hier: Fehler dort abfangen, wo sie entstehen — Freshness-Probe im
Install-Pfad jedes Consumers (generalisiert aus dem produktiven aifw-Muster), Stub-Namen-Warnung im
PR-Pfad, Consumer-Canary vor dem Release (als lokales Skript beginnend, gegen den realen
Regressions-Korpus) — und **nicht**: mehr wöchentliche Meter, deren Gattung nachweislich ungelesen
wächst. **Standard statt Exception** heißt: erst die EINE Wahrheit der Reusable-CI wiederherstellen
(shared-ci#20 + Job-Katalog-Diff), dann Ausnahmen abbauen (Stub-Namen, git+@main-Pins,
Doppel-Publisher, Tag-lose Releases) — in dieser Reihenfolge, weil jeder auf der Doppelquelle
gebaute Standard die Divergenz multipliziert. **Funktionale Weiterentwicklung** heißt:
Portfolio-Disziplin — die fünf Kern-Pakete (>10 Konsumenten) bekommen die Investitionen (Canary,
Freshness, saubere Releases), der 0/1-Konsumenten-Schwanz bekommt eine datierte
Sunset-or-Merge-Entscheidung, und die drei Stub-Hubs bekommen die überfällige 0.5→0.11-Migration
als konkrete Funktions-Nachrüstung.

### 5.2 Problem (nach Adversariat, korrigiert)

1. **3 Hubs auf 8 Monate altem Stub** (C6), Migration kreuzt Breaking 0.6.0 (C9).
2. **Reusable-CI-Doppelquelle** mit Gate-Regression in der konsumierten Kopie (C8).
3. **Prävention existiert nur als Design:** ADR-266 3a seit Accept unangefasst (M28-8); api-diff in
   eingefrorenem ADR (C4); der einzige produktive Prädiktor (Freshness-Probe) ist ein aifw-Einzelfall.
4. **Portfolio ungesteuert:** riskfw/gaeb-toolkit 0 Konsumenten, iil-enrichment tot,
   iil-django-commons 1, shared_contracts 0 (C10) — Signale laufen in ein Meter-Issue-Muster, dessen
   Gattung empirisch nicht gelesen wird (C11); Entscheide fallen nicht.
5. **Release-Hygiene lückenhaft:** 5 Publisher ohne git-Tags, outlinefw/weltenfw mit unreleased
   Versionen (C13), writing-hub zieht 2 Frameworks ungepinnt via git+@main (C10).
6. **Owner-Action-Stau:** PyPI-Org 2. Owner, 7 Trusted-Publisher-Bindings, shared-ci#20 — alles
   menschgebunden, nichts terminiert (M28-3/4/6); ADR-266s eigene Backlog-Liste war schon bei
   Accept stale (C12).

### 5.3 Zielbild (T+90)

Kein Prod-Hub referenziert einen Legacy-Stub-Namen (maschinell bewiesen durch den PR-Warning-Step).
Es gibt genau EINE `_ci-pypi.yml`-Wahrheit mit gate-Job, konsumiert von Task-B-Repos. Die
Freshness-Probe ist für die Top-3-Pakete generisch; der Canary läuft als Skript mit dokumentiertem
Rot-Beweis gegen den Regressions-Korpus. Das Portfolio hat gefallene, protokollierte Entscheide
über die 0/1-Konsumenten-Pakete. Alle Owner-Aktionen stehen in EINEM datierten Block.

### 5.4 Nicht-Ziele

- **Kein `_publish-pypi.yml`-BAU in diesem Konzept.** ADR-266 verwirft „Zentraler Publish in
  shared-ci" (C2 Z.125); ADR-226 benennt den Reusable als Konsolidierungsziel (C3). Diese Spannung
  ist eine echte Definitionsfrage (Reusable-per-Repo-Aufruf ≠ zentrales Publishing — das Gate bliebe
  unmittelbar vor dem Upload, der Publish bliebe pro Repo), aber sie zu entscheiden gebührt einem
  **expliziten ADR-266-Amendment** (W2-E1), nicht einem stillen Konzept-Nebensatz (AD-9/M28-9).
- **Kein api-diff-Gate** (M28: doppelt unfinanziert — eingefrorene ADR-222-Vorbedingung
  `platform-doctor` läuft in keinem Workflow). Option nach Canary-Beweis.
- **Kein neuer Meter, kein neues Rolling-Issue** (C11-Empirie).
- **Keine PyPI-Org-/Repo-Transfers vorziehen** (ADR-255 owner-gated); vor jeder OIDC-Änderung je
  Repo Transfer-Status prüfen (AD-10).
- **Keine Token-Entfernung ohne Trusted-Publisher-Binding-Beweis** (🌀 ADR-266-Memory).
- **Kein Anfassen der install-Action-Legacy-Fallbacks, BEVOR die 3 Hubs migriert sind** (AD-5) —
  Reihenfolge: Consumer zuerst, dann Fallback-Rückbau (sonst bricht deren CI).

### 5.5 Maßnahmen

**W0 — sofort (alle origin-verifiziert, gate-frei bzw. Sonnet-delegierbar):**

| # | Maßnahme | Mechanik |
|---|---|---|
| W0-1 | Stub-Migration als 3 execution-ready Issues (cad-hub, 137-hub, trading-hub) | je Issue: Pin `aifw>=0.5.0,<1` → `iil-aifw>=0.11.4,<1`, **Breaking-Hinweis 0.6.0** (AIActionType.code), Smoke-Plan (App-Import + betroffene Model-Pfade), Label `model:sonnet-5` (Prep-for-Sonnet-Muster). KEIN „1-Zeilen-PR"-Framing (AD-7) |
| W0-2 | Stub-Grep als non-blocking Warning-Step in `_ci-python.yml` (OOTB C) | warnt bei `^aifw>=`/bekannten Legacy-Dists in requirements-Diffs; nach 2 Wochen 0-FP → blocking. Liefert zugleich die Kill-Gate-(a)-Messung |
| W0-3 | Owner-Actions-Block konsolidieren | EIN Kommentar/Issue-Update mit allen menschgebundenen Punkten + Datum: shared-ci#20-Merge, PyPI-Org 2. Owner, 7 Bindings, outlinefw/weltenfw-Release-Tags (C13), aifw-0.5.0-Yank-Entscheid (OOTB B, Publish-Gate) |

**W1 — 30 Tage:**

| # | Maßnahme | Mechanik |
|---|---|---|
| W1-1 | Reusable-Kanonizität: shared-ci#20 mergen (Owner) + **Job-Katalog-Diff** platform-Kopie ↔ shared-ci-Kopie (🌀 `feedback_ci_replace_requires_job_catalog_diff`) | Ergebnis: EINE `_ci-pypi.yml`-Wahrheit mit gate-Job; danach Task B (outlinefw, promptfw) per PR-Head-Verifikation |
| W1-2 | testkit-Dedup exekutieren (ADR-266-K5-Item) | kanonisch = registrierter `iil-testkit`-Pfad; zweiten Publisher stilllegen; vorher `gh pr view --json files`-artige Abdeckungs-Prüfung (Evidence-Policy Punkt 6) |
| W1-3 | Freshness-Probe generalisieren (OOTB A) — Pilot iil-promptfw | `[tool.iil-fleet] freshness_symbols` in pyproject + generischer Probe-Step in install-iil-packages; Pilot am 2.-größten Paket (14 Konsumenten); die aifw-Sonderlogik bleibt bis Pilot grün |
| W1-4 | Registry-Vollständigkeit über den **Regenerator** (AD-11) | unregistrierte Publisher (testkit, ggf. weitere) via kanonische Registry-`type: library`-Einträge + `pypi_fleet_inventory.py`-Lauf; **plus** Entscheid: pypi-fleet.yaml wird wöchentlich zurückcommittet ODER trägt einen Snapshot-Disclaimer (M28-1 — Datei behauptet Ground-Truth, ist seit 07-04 eingefroren) |

**W2 — 60–90 Tage (gegatet auf W1-1):**

| # | Maßnahme | Mechanik |
|---|---|---|
| W2-1 | Consumer-Canary = **ADR-266 3a ausführen** (nicht neu erfinden, M28-8) — als lokales Skript zuerst (OOTB D) | `tools/consumer_canary.py <paket> <consumer>`: Release-Kandidat-Wheel gegen Consumer-Testsuite; Erstziel iil-aifw→risk-hub; **Rot-Beweis Pflicht** gegen den Regressions-Korpus (learn-hub#9, platform#413/416/419 — C5); Matrix-Ausbau (2–3 strukturell verschiedene Consumer) nach erstem Beweis (Steelman-Unterambitions-Fund); CI-Integration erst danach |
| W2-2 | **Entscheid E1** (ADR-266-Amendment, Owner): `_publish-pypi.yml`-Reusable ja/nein | Vorlage klärt: Reusable-per-Repo vs. verworfener Zentral-Publish (Definitionen), Kanonizitäts-Vorbedingung (W1-1 erfüllt), ADR-255-Transfer-Kollisionen je Zielrepo (AD-10). Erst Entscheid, dann ggf. Bau — außerhalb dieses Konzepts |
| W2-3 | **Portfolio-Entscheidungssession** (datiert, protokolliert — M28-Streichungsauflage 4) | Kandidaten NAMENTLICH: riskfw (0 Konsumenten), gaeb-toolkit (0), iil-enrichment (tot), iil-django-commons (1 — in tax-hub mergen?), shared_contracts (0 seit Entscheid A), iil-klickdummy-Vertriebsform (nur vendored). Je Kandidat: weiterentwickeln / einfrieren / sunset / mergen — mit Datum und Tracking-Issue je Entscheid |
| W2-4 | writing-hub git+@main → Versions-Pins | **nachgelagert hinter Release-Tags** (Owner-Action W0-3: outlinefw 0.3.2 muss erst released sein, C13); bis dahin mindestens git+@`<tag>` statt @main |
| W2-5 | T+90-Reminder-Issue bei Annahme (M28-Streichungsauflage 5) | trägt die Kill-Gate-Checkliste + die W0-3-Owner-Liste; verhindert das dokumentierte `review_by`-Verfalls-Muster |

### 5.6 Enforcement-Modell (ehrlich)

| Regel | Level | Grenze |
|---|---|---|
| Stub-Namen-Warnung im PR-Pfad | erst warn, dann blocking | greift nur in Repos auf Reusable-CI; Außenseiter-Repos sieht nur der Fleet-Grep |
| Freshness-Probe | hart im Install-Pfad des Consumers (fail loud in dessen CI) | schützt nur deklarierte Symbole; Symbol-Liste ist Paket-Owner-Pflege |
| Canary vor Release | zunächst prozessual (Skript-Aufruf vor Tag) | CI-Erzwingung erst nach E1/Reusable-Entscheid; bis dahin Disziplin + Reminder |
| Portfolio-Entscheide | prozessual, aber DATIERT mit Protokoll-Pflicht | kein technisches Gate möglich — deshalb Session statt Meter-Zeile |
| Trusted-Publisher/Yank/Org-Owner | Owner-only (PyPI-UI, headless unprüfbar — H2) | einzige Absicherung: gebündelter, terminierter Block (W0-3) + Reminder (W2-5) |

## 6. Adversariale Analyse

### 6.1 Advocatus Diabolus (12 Befunde, konserviert — Kernauswahl)

**AD-1 (kritisch, Kipp-Angriff):** `_ci-pypi.yml`-Doppelquelle, shared-ci-Kopie ohne gate-Job,
promptfw konsumiert sie bereits — ein neuer Publish-Reusable dort würde die Gate-Regression auf den
Publish-Pfad ausweiten. **AD-2 (schwer):** „researchfw gate-los" falsch — stale Klon; auf origin
seit 30.06. gefixt (#7). **AD-3:** „5 handgerollte publish-*.yml" ist stale ADR-226-Zahl; real 3.
**AD-4/AD-12:** Portfolio-Signal und testkit-Dedup existieren bereits als ADR-266-Items — Konzept
darf sie nur exekutieren, nicht neu erfinden. **AD-5:** Legacy-Fallback in der install-Action bleibt
nach Consumer-Migration bestehen — Abbau-Reihenfolge nötig. **AD-6:** ttz-hub-Pin nicht in
Top-Level-requirements (→ in Synthese gegen origin aufgelöst: gar nicht mehr vorhanden, Kohorte=3).
**AD-7:** aifw 0.5→0.11 kreuzt Breaking 0.6.0 — „1-Zeilen-PR" war Scheinkonkretheit. **AD-8:**
Kill-Gate hing an fremdgegatetem shared-ci#20 ohne das zu benennen. **AD-9:** Reusable-Publish
kollidiert mit ADR-266-Verwerfung „Zentraler Publish". **AD-10:** OIDC-Bindings sind
repository_owner-gebunden — ADR-255-Transfers machen sie „throwaway". **AD-11:** pypi-fleet.yaml
ist generiert („nie von Hand editieren") — Registry-Fixes müssen durch den Regenerator.

### 6.2 Maintainer-2028 (9 Befunde, konserviert — Kernauswahl)

**M28-1 (hoch):** pypi-fleet.yaml behauptet Ground-Truth, ist seit Erstellung eingefroren — kein
Workflow schreibt zurück. **M28-2 (hoch):** ADR-222-Freeze-Bedingung (platform-doctor-Daten) ist
strukturell unerfüllbar — das Skript läuft in keinem Workflow. **M28-3/4 (hoch):** PyPI-Org-Owner
und 7 Bindings sind unbeaufsichtigte UI-Klick-Schulden ohne Alarm. **M28-5 (hoch, stärkster
Beleg):** Rolling-Meter-Issues werden nicht gelesen — #188 wuchs 12→32 in 7 Wochen bei 0
menschlichen Kommentaren; #968 startet im selben Muster. **M28-7:** ADR-266s Backlog-Liste war bei
Accept bereits stale (alle 4 Issues geschlossen) — Listen altern schneller als ADRs. **M28-8:**
Canary als „neue" Maßnahme recycelt einen liegengebliebenen Punkt ohne neuen Hebel. **M28-9 (hoch):**
Reusable-Publish widerspricht getroffener Entscheidung ohne Revisions-Kennzeichnung.
**Streichungsauflagen:** Reusable-Bau raus (→ Entscheid), api-diff raus, Canary als 3a-Vollzug mit
neuem Hebel, Portfolio nur mit Namen+Termin, Kill-Gate braucht Trigger-Artefakt. **Alle fünf
übernommen** (§5.4, §5.5).

### 6.3 Steelman + OOTB (konserviert — Kernauswahl)

Faktenbasis in den tragenden Teilen datei-verifiziert (Stub-Pins, Doppel-Publisher, shared-ci#20,
Meter-Frequenzen). **OOTB übernommen:** (A) Freshness-Probe generalisieren — bewährter produktiver
Mechanismus statt Neubau (→ W1-3); (C) Stub-Grep als PR-Gate statt Wochen-Report (→ W0-2);
(D) Canary als lokales Skript, entkoppelt vom Reusable-Streit (→ W2-1); Regressions-Korpus aus den
dokumentierten Real-Breakages (→ W2-1). **OOTB als Owner-Entscheid geparkt:** (B) aifw-0.5.0-Yank
auf PyPI (Tombstone — schließt die Klasse an der Quelle, aber Publish-Gate → W0-3-Block).
**Unterambitions-Fund übernommen:** Einzel-Consumer-Canary ist Stichprobe — Matrix-Ausbau nach
erstem Beweis (→ W2-1).

### 6.4 Konfliktmatrix (Pflicht bei T3)

| # | Konflikt | Positionen | Auflösung |
|---|---|---|---|
| K1 | researchfw-Gate | Erdung/Entwurf: „gate-los" vs. AD-2: falsch (stale Klon) | AD-2 gewinnt; Haupt-Session-Gegencheck bestätigt (C7); Maßnahme gestrichen; Selbstkorrektur-Protokoll §2 |
| K2 | Stub-Kohorte 3 oder 4 | Steelman: 4/4 verifiziert (ttz via Service-Subdir) vs. AD-6: kein Treffer | Beide sahen verschiedene Dateien; origin-Check der Haupt-Session entscheidet: ttz-hub hat auf origin/main KEINEN aifw-Pin → **Kohorte = 3** (C6) |
| K3 | Publish-Reusable | Steelman: ADR-226-Auftrag, stärkster Standard-Hebel vs. AD-9/M28-9: verworfen in ADR-266 + Doppelquellen-Risiko (AD-1) | Diabolus/M28 gewinnen prozedural: kein Bau, sondern expliziter Amendment-Entscheid E1 mit Kanonizitäts-Vorbedingung; Steelmans Definitions-Argument (Reusable-per-Repo ≠ Zentral-Publish) wird der Entscheidungsvorlage mitgegeben |
| K4 | Canary-Gewicht | Entwurf: W2-CI-Bau vs. M28-8: recyceltes Waisen-Item vs. OOTB D: Skript zuerst | OOTB D gewinnt: 3a-Vollzug mit neuem Hebel (Skript + Regressions-Korpus + Rot-Beweis-Pflicht), CI später |
| K5 | Migration trivial? | Entwurf: „1-Zeilen-PR" vs. AD-7: Breaking 0.6.0 dazwischen | AD-7 gewinnt: execution-ready Issues mit Smoke-Plan (W0-1) |
| K6 | Portfolio-Mechanik | Entwurf: W2-Entscheide vs. AD-4/M28-5: Signal existiert, Meter-Issues ungelesen | Synthese: nicht das Signal ist das Defizit, sondern der fehlende Entscheidungs-TERMIN — datierte Session mit Protokoll (W2-3) |
| — | Konvergenz aller drei | Freshness-Generalisierung, Stub-Grep, Owner-Block-Bündelung, Reminder-Artefakt | übernommen (W0-2/W0-3/W1-3/W2-5) |

## 7. Deep-Dive: die drei Achsen

**Predictive:** Die Plattform hat für Packages bereits drei Detektions-Schichten (Gate-Meter,
Fleet-Health, Adoption-Gate) — aber nur EINEN präventiven Mechanismus, und der ist ein Einzelfall
(aifw-Freshness-Probe). Die Empirie (C11) zeigt: mehr Detektion wird nicht gelesen; Prävention im
Pfad (Install-Step, PR-Step, Pre-Release-Skript) failt dagegen dort, wo jemand ohnehin hinschaut —
in der eigenen CI. Deshalb investiert dieses Konzept ausschließlich in Pfad-Prävention und keinen
Cent in neue Reports.

**Standard:** Die Ausnahmen-Liste ist endlich und klein: 3 Stub-Pins, 2 git+@main, 1
Doppel-Publisher, 3 handgerollte Publisher, 5 Tag-lose Repos, 1 divergierte Reusable-Kopie. Alles
davon ist einzeln adressiert (W0-1, W2-4, W1-2, E1, W0-3, W1-1). Die Reihenfolge ist das
Architektur-Statement: **Kanonizität vor Konsolidierung** — der Diabolus hat gezeigt, was passiert,
wenn man sie umdreht (promptfw konsumiert heute die gate-lose Kopie).

**Funktional:** Die Konsumenten-Karte macht das Portfolio erstmals entscheidbar: 5 Kern-Pakete
tragen die Fleet (aifw/testkit/promptfw/platform-context/authoringfw, je 10–18 Konsumenten), 6
Pakete haben 0–1 Konsumenten. Funktionale Weiterentwicklung heißt beides: Die Kern-Pakete bekommen
Release-Sicherheit (Canary, Freshness, Tags), damit Weiterentwicklung nicht mehr Breakage-Angst
bedeutet (drei dokumentierte Realfälle im Korpus) — und der Schwanz bekommt Klarheit, damit keine
Pflege-Kapazität mehr in Konsumentenlose fließt. Der Stub-Fund zeigt den Preis des Status quo: drei
Hubs sind von 8 Monaten aifw-Entwicklung (0.5→0.11: Governance-Router, Quality-Levels,
Action-Configs laut CHANGELOG) schlicht abgeschnitten.

## 8. Alternativen

**A1 — Nur Stub-Fix, kein Konzept:** behebt den akuten Funktionsverlust, lässt Doppelquelle,
Canary-Lücke und Portfolio ungelöst — der vierte Stub entsteht beim nächsten Copy-Paste (kein
PR-Warning-Step). Teilmenge von W0.

**A2 — ADR-266 einfach „weiterlaufen lassen":** Die Empirie dagegen steht in ADR-266 selbst — 3a
seit Accept unangetastet, owner_actions-Stau, stale Backlog-Liste bei Accept (C12). Ohne Termine und
Beweispflichten wiederholt sich das Muster. Dieses Konzept IST ADR-266-Vollzug, nur terminiert.

**A3 — Groß-Konsolidierung zuerst (Reusable-Publish + Org-Migration + OIDC in einem Zug):**
maximal sauber, aber dreifach owner-gated (ADR-255-Transfers, PyPI-Bindings, shared-ci-Merges) und
gegen AD-1/AD-10 gebaut — höchstes Risiko, monatelange Blockade. Verworfen; E1 entkoppelt die
Entscheidungsfrage davon.

## 9. Out-of-the-Box (übernommene siehe §6.3; zusätzlich bewusst NICHT übernommen)

- **PyPI-Downloads als Sunset-Automatik:** verworfen — ADR-266 3c sagt zu Recht „nie Auto-Aktion";
  Downloads sind bei internen Paketen kein Nutzungs-Proxy (CI-Installs dominieren).
- **Monorepo für alle iil-Packages:** nicht geprüft, bewusst außerhalb — wäre ein eigenes T3 mit
  ADR-Pflicht (Reversal mehrerer Entscheidungen); nichts in der Evidenz erzwingt es.

## 10. Befunde (Kern-Tabelle)

| ID | Kategorie | Befund | Evidenz | Schwere |
|---|---|---|---|---|
| F-1 | Funktional | 3 Prod-Hubs auf aifw-0.5.0-Stub (8 Monate Rückstand); Migration kreuzt Breaking 0.6.0 | C5, C6, C9 | kritisch |
| F-2 | Standard | `_ci-pypi.yml`-Doppelquelle, konsumierte Kopie ohne gate-Job | C8 | kritisch |
| F-3 | Predictive | Einziger produktiver Prädiktor ist aifw-Einzelfall; 3a/api-diff nur Papier | C4, C5, M28-8 | hoch |
| F-4 | Portfolio | 6 Pakete mit 0–1 Konsumenten; Entscheide fallen nicht (Meter-Gattung ungelesen, C11) | C10, C11 | hoch |
| F-5 | Release-Hygiene | 5 Tag-lose Publisher; outlinefw/weltenfw unreleased; git+@main ×2 | C13, C10 | mittel |
| F-6 | Governance-Alterung | owner_actions unbeaufsichtigt; ADR-266-Backlog bei Accept stale; fleet.yaml eingefroren | M28-1/3/4, C12 | mittel |
| F-7 | Methode (Selbstbefund) | 2 Erdungs-Claims zerfielen am origin-Check (researchfw, ttz-hub) — Stale-Clone-Klasse ×2 in einer Analyse | C6, C7 | hoch (als Prozess-Lektion) |

## 11. Top-5-Risiken

**R1 — Stub-Migration bricht einen Hub funktional (AD-7).** *Fix:* Smoke-Plan im Issue + Canary-Skript
(W2-1) vorziehen für cad-hub falls Unsicherheit; Rollback = Pin-Revert (reversibel). *Rest:* 0.6.0-
Migrationseffekte in App-Code sind erst im Smoke sichtbar.

**R2 — shared-ci#20 bleibt liegen → Kill-Gate (b) reißt fremdverschuldet (AD-8).** *Fix:* ehrlich
benannt: (b) ist bewusst so gebaut — die Doppelquelle IST das Risiko, ihr Fortbestehen SOLL das
Konzept killen; der Owner-Block (W0-3) + Reminder (W2-5) terminieren die Anfrage. *Rest:* Owner-Kapazität.

**R3 — Freshness-Generalisierung erzeugt False-Positives in Consumer-CI.** *Fix:* Pilot auf EINEM
Paket (promptfw), Symbole konservativ (nur stabile Top-Level-API), aifw-Sonderlogik bleibt parallel
bis grün. *Rest:* Symbol-Listen-Pflege ist neue kleine Dauerpflicht der Paket-Owner.

**R4 — Portfolio-Session findet statt, Entscheide versanden trotzdem.** *Fix:* Protokoll-Pflicht +
je Entscheid ein Tracking-Issue mit Datum (House-Rule „Bewusst Ausgelassenes braucht Artefakt");
Kill-Gate (d) prüft die Session, das Reminder-Issue die Folge-Issues. *Rest:* Entscheidungsqualität
ist nicht erzwingbar.

**R5 — Dieses Konzept konkurriert mit KONZ-017-W-Wellen um dieselben 2 Personen.** *Fix:* W0 ist
Sonnet-delegierbar (execution-ready Issues), W1-1 ist ein Owner-Merge + ein Diff, W2 ist gegatet —
Netto-Neulast für Menschen: 1 Merge, 1 Entscheidungsvorlage, 1 Session. *Rest:* real verfügbare
Kapazität unbekannt (identisch KONZ-017 R5).

## 12. Empfehlungen

- **REC-1 (ich, sofort):** 3 execution-ready Stub-Migrations-Issues (W0-1) + Stub-Grep-Warning-PR (W0-2).
- **REC-2 (ich, sofort):** Owner-Actions-Block als datiertes Issue (W0-3) — bündelt shared-ci#20,
  PyPI-Org-Owner, 7 Bindings, Release-Tags outlinefw/weltenfw, Yank-Entscheid.
- **REC-3 (du, 30d):** shared-ci#20 mergen; ich liefere den Job-Katalog-Diff davor (W1-1).
- **REC-4 (ich, 30d):** testkit-Dedup-Vorlage mit Abdeckungs-Beweis (W1-2); Freshness-Pilot promptfw
  (W1-3); Registry-/Snapshot-Entscheidungsvorlage (W1-4).
- **REC-5 (ich, 60–90d, gegatet):** Canary-Skript + Rot-Beweis (W2-1); E1-Entscheidungsvorlage (W2-2).
- **REC-6 (du+ich, 60–90d):** Portfolio-Session terminieren (W2-3) — Kandidatenliste steht in §5.5.
- **REC-7 (ich, bei Annahme):** T+90-Reminder-Issue (W2-5) — trägt Kill-Gate-Checkliste,
  Owner-Block-Verweis und die bewusst geparkten Optionen (api-diff, Reusable-Bau, Yank, Matrix-Canary).

## 13. Entscheidung + Kill-Gate + 30/60/90

**Empfehlung: als MVP annehmen.** Nicht „Vollkonzept" — der Erstentwurf verlor vier Elemente an das
Adversariat (researchfw-Maßnahme falsifiziert, Reusable-Bau → Entscheid, api-diff gestrichen,
„4 Hubs" → 3) und dieses Dokument macht das transparent statt es zu glätten. Nicht „ablehnen" — drei
Prod-Hubs auf einem 8-Monate-Stub und eine gate-regressive Reusable-Doppelquelle sind belegte,
laufende Kosten. Nicht „nur A1" — ohne Stub-Grep, Kanonizität und Portfolio-Termin wächst die
Ausnahmen-Liste nach.

**Kill-Gate:** Frontmatter `kill_criteria`; Trigger-Artefakt = REC-7-Reminder (M28-Auflage).

**30 Tage (bis 2026-08-11):** W0 komplett (3 Issues erstellt, ≥1 gemergt; Warning-Step live;
Owner-Block datiert); W1-1 Job-Katalog-Diff geliefert, shared-ci#20-Merge angefragt.

**60 Tage (bis 2026-09-10):** Stub-Kohorte 0 (maschinell); Task B verifiziert (falls #20 gemergt);
testkit-Dedup exekutiert; Freshness-Pilot grün; fleet.yaml-Entscheid umgesetzt.

**90 Tage (bis 2026-10-12):** Kill-Gate-Review am Reminder; Canary-Rot-Beweis dokumentiert;
E1-Vorlage beim Owner; Portfolio-Session protokolliert; Konzept-Status-Flip.
