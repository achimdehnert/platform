---
concept_id: KONZ-platform-004
title: Branch-Protection-Enforcement schließen — ADR-174-Drift via ADR-234 R2
pipeline_status: prod
tier: T3
owner: achimdehnert
spec_refs: []   # kein Klickdummy/Spec-Bezug (ADR-211) — reine CI-Governance; bewusst leer
adr_threshold: kein neuer ADR — Mechanismus = ADR-234 R2; ggf. kleines Amendment (G1/G2); ADR-174 implementation_done_when schließen
review_by: 2026-07-09
kill_criteria: "Nach 2 Wochen Pilot (Prod-Subset) mehr legitime grün-werdende Merges blockiert als rote Merges verhindert, ODER ≥1 Break-Glass/Woche nötig → zurück auf Konvention + nur Audit-Meter"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "gh api repos/achimdehnert/<hub>/branches/main/protection", commit_or_pr: "404 ×14", opened_in_session: true}
  - {claim_id: C2, source_path: "platform PR #522 (mergeStateStatus)", commit_or_pr: "#522 BLOCKED→CLEAN", opened_in_session: true}
  - {claim_id: C3, source_path: "gh api .../commits/<sha>/check-runs (9 Hubs)", commit_or_pr: "ci/* Namen uniform", opened_in_session: true}
  - {claim_id: C4, source_path: "docs/adr/ADR-174-workflow-enforcement-ci-gate.md", commit_or_pr: "status accepted / implementation_status partial", opened_in_session: true}
  - {claim_id: C5, source_path: "docs/adr/ADR-234-clean-state-invariant.md §2.1/R2", commit_or_pr: "R2 Reconciler + quarantine + kein Flotten-Freeze", opened_in_session: true}
  - {claim_id: C6, source_path: "gh pr view 13 --repo achimdehnert/trading-hub", commit_or_pr: "mergedBy achimdehnert, red CI, ddb7071 startup_failure", opened_in_session: true}
  - {claim_id: C7, source_path: "gh api cad-hub check-runs", commit_or_pr: "ci / Coverage Gate (≥80%) vs (≥${{…}}%)", opened_in_session: true}
created: 2026-06-09
---

# KONZ-platform-004 — Branch-Protection-Enforcement schließen

> **Status-Update (2026-07-08):** Realisiert durch ADR-242 (Wave 1+2 live) + ADR-257
> (Ebene A gemergt); `review_by 2026-07-09` gegenstandslos.

## 1. Executive Summary

Branch Protection ist **bereits entschieden** (ADR-174, `accepted`) und der **Mechanismus
existiert auf Papier** (ADR-234 **R2** — „Branch-Protection-as-Code-Reconciler"). Was fehlt,
ist **Lieferung** und **Sichtbarkeit der Lücke**: ADR-174 `implementation_done_when` verlangt
„qm-gate als required status check in Branch Protection aller aktiven Repos" — die Realität ist
**0/14 Hubs geschützt** (C1). Die Drift war bis heute unsichtbar; sie kostete am 2026-06-09 einen
realen Prod-Deploy: **trading-hub#13** wurde manuell mit roter CI gemergt (C6) und brach den
Deploy. Dieses Konzept fordert **keinen neuen ADR**, sondern: (a) die ADR-174-Drift benennen und
schließen, (b) ADR-234 R2 **ungaten** (interim-Pilot vor dem Voll-Reconciler), (c) zwei
Implementierungsdetails ergänzen, die R2s Vertrag noch nicht nennt (G1/G2).

## 2. Scope & Evidenzbasis

| ID | Claim | Evidenz |
|---|---|---|
| C1 | 0/14 Hubs haben Branch-Protection auf `main` | E3 (gh api → 404 ×14, diese Session) |
| C2 | platform-Repo **ist** geschützt (4 required checks) | E3 (#522 war `BLOCKED` bis grün) |
| C3 | `ci/*`-Check-Namen flottenweit uniform (Quelle: shared-ci `_ci-python.yml`) | E3 (check-runs, 9 Hubs) |
| C4 | ADR-174 `accepted`, verlangt required-check in Protection, `implementation_status: partial` | E1/E2 (ADR-174-Frontmatter) |
| C5 | ADR-234 R2 = Reconciler mit Quorum + `quarantine`-Lane + „kein Flotten-Freeze" | E1/E2 (ADR-234 §R2) |
| C6 | trading-hub#13 manuell rot gemergt → Prod-Deploy startup_failure | E3 (gh pr view) |
| C7 | Coverage-Gate-Name instabil (`≥80%` vs `≥${{…}}%`) | E3 (cad-hub check-runs) |

## 3. Infrastruktur-Fit (was schon da ist — Root-Cause-Tiefe)

- **Entscheidung:** ADR-174 (Option 3+4: CI-Gate erzeugt Status-Check, Branch Protection erzwingt
  ihn; ohne Protection ist `--admin`-Bypass möglich). **Nicht offen — entschieden.**
- **Mechanismus:** ADR-234 **R2** mit Mindestvertrag (`plan/apply/rollback`, idempotenter Diff,
  Audit-Log/Repo, minimaler Token-Scope, Schutz gegen ungeprüfte Massenänderung an 41 Repos),
  Frische-Quorum vor `required`, **`quarantine`-Lane** statt Flotten-Freeze. **Nicht neu zu erfinden.**
- **Onboarding-Pfad:** ADR-174-impl nennt `onboard-repo.md Step 6.9 Branch Protection` — d. h. für
  *neue* Repos existiert der Schritt; der **Bestand** (14 laufende Hubs) wurde nie nachgezogen.
- **Tooling-Lücke:** `grep` fand **kein** Skript, das Protection setzt (R2 ist unimplementiert).

→ Konsequenz: Dies ist **Implementierung + Drift-Schließung**, kein Architektur-Neuentwurf.

## 4. Steelman (stärkste Form des Status quo „Konvention reicht")

Im klein besetzten Org (faktisch ein aktiver Merger) ist *Disziplin* billiger als Enforcement:
keine `enforce_admins`-Friktion, kein Break-Glass-Runbook, Hotfixes gehen sofort. Die rote Flotte
(F4, ~34 Repos) sofort merge-blockend zu schalten **friert die Flotte ein** und erzeugt
Goodhart-Druck (Gate-Senkung) — genau das warnt ADR-234 ab. Solange ein Mensch die einzige
Merge-Quelle ist, fängt Review-Disziplin 95 % der Fälle.

## 5. Konzeptdefinition

**Kernthese (ein Satz):** Schließe die ADR-174-Drift, indem ADR-234 R2 als **schmaler
Fail-Closed-Ring auf dem deploy-on-push-Prod-Subset** scharf gestellt wird (interim manuell,
dann reconciler-as-code), während die rote Flotte in der `quarantine`-Lane bleibt — Aktivierung
pro Repo **erst nach F4-grün**.

**Required-Check-Set (konservativer Start, aus shared-ci, C3):**
`ci / Lint & Format` · `ci / Unit Tests` · `ci / Secret Detection (gitleaks)` ·
`ci / Security Scan (pip-audit + pip check)`. **Nie** `deploy / *` (G1). Coverage erst nach G2-Fix.

## 6. Adversariale Analyse

> **Tier-Ehrlichkeit:** T3 verlangt formal einen 3-Agenten-Fan-out. Hier **bewusst nicht**
> ausgeführt, weil die *Entscheidung* pre-owned ist (ADR-174/234) — ein „sollen wir Branch
> Protection?"-Trialog wäre Theater (alle drei sagen ja). Der Fan-out gehört an die **offenen
> Implementierungs-Toggles** (s. §13), falls die zur ADR-234-R2-Härtung eskalieren.

**Advocatus Diabolus:**
- *Doppelquelle?* Interim **manuelle** Protection auf dem Prod-Subset erzeugt eine zweite Wahrheit
  neben dem geplanten R2-Reconciler — was R2 später wieder einsammeln muss. **Risiko real.**
  Gegenmittel: interim-Protection minimal + dokumentiert als „pre-R2, wird von Reconciler übernommen",
  Audit-Log von Hand führen; KEIN paralleles Dauer-Skript bauen, das mit R2 konkurriert.
- *„Sichtbar machen" < „verhindern"?* Ein reiner Audit-Meter (R5) *meldet* rote Merges, *verhindert*
  sie nicht. trading-hub#13 wäre gemeldet, nicht gestoppt worden. → Für den Prod-Subset ist
  **`enforce_admins`** die einzige Stufe, die „no-bypass" real macht (Steelman akzeptiert Friktion).
- *Formal erfüllen, praktisch umgehen?* `push:[main]`-Deploy umgeht Protection ohnehin (Protection
  gatet Merge, nicht Push). Manuelle SSH-/Fast-Deploys (ADR-021 §Fast-Deploy) bleiben ein Loch —
  Protection ist **notwendig, nicht hinreichend**; ehrlich benennen.

**Maintainer-2028:** Wenn die Frische-Quorum-Logik (R2) nie gebaut wird und nur die interim-manuelle
Protection bleibt, ist in 2 Jahren „Branch Protection" ein handgepflegtes 14-Zeilen-`gh api`-Ritual
ohne Reconcile → driftet erneut. Kill-Gate muss den interim-Zustand TTL-en.

## 7. Deep-Dive — die drei Gotchas

| # | Gotcha | Status | Aktion |
|---|---|---|---|
| **G1** | `deploy/*`-Jobs als required = Deadlock (laufen post-merge auf `push`) | **neu** (R2-Vertrag nennt es nicht) | Required-Set hart auf `ci/*` begrenzen; als R2-Amendment notieren |
| **G2** | Coverage-Gate-Name instabil (`≥80%` vs `≥${{…}}%`, Exact-String-Match) (C7) | **neu** | Coverage aus Start-Set raus; ODER shared-ci `_ci-python.yml` Job-Namen stabilisieren (kleiner PR) |
| **G3** | required `ci/Lint` friert F4-rote Repos ein | **schon in ADR-234** („kein Flotten-Freeze" + quarantine) | Aktivierung pro Repo an F4-grün koppeln; rote → `quarantine` |

## 8. Alternativen

| Alt | Beschreibung | Warum nicht |
|---|---|---|
| **A** | Required Checks, **kein** `enforce_admins`, flottenweit | Verhindert Versehen, nicht Absicht (trading-hub#13 war Absicht/manuell) — für Prod-Subset zu schwach |
| **B** (empf.) | A als Default + `enforce_admins` **nur** Prod-Subset | Macht „no-bypass" real wo der Schaden entsteht; Friktion begrenzt auf wenige Repos |
| **C** | + required Review (1 Approval) | Im Ein-Merger-Org unpraktikabel → blockiert Solo-Arbeit; verworfen |

## 9. Out-of-the-Box

`enforce_admins` braucht einen zweiten „Account", um Break-Glass *ohne* Protection-Abschaltung zu
erlauben → die **Profil-B GitHub-App** (`iilgmbh-admin`, App 3971306, schon vorhanden) könnte als
zugelassener Bypass-Identity dienen, statt Protection von Hand aus/einzuschalten. Prüfen, ob
App-Token in der required-check-Liste als zulässiger Override konfigurierbar ist (sonst bleibt
Break-Glass = Protection temporär DELETE + Audit-Log).

## 10. Befunde

| ID | Befund | Schwere | Evidenz |
|---|---|---|---|
| B1 | ADR-174 `implementation_done_when` 0/14 erfüllt — accepted-aber-undelivered, Drift unsichtbar | hoch | C1+C4 |
| B2 | „no-bypass" der ref-sweep-Gates ist unenforced; ein realer Prod-Bruch belegt (trading-hub#13) | hoch | C6 |
| B3 | Mechanismus (R2) entschieden aber ungebaut; kein Protection-Tooling im Repo | mittel | C5 + grep |
| B4 | G1/G2 sind im R2-Vertrag nicht adressiert (Deadlock-/Name-Stabilitäts-Falle) | mittel | E2/C7 |

## 11. Top-5-Risiken

1. **Flotten-Freeze** bei vorschnellem required-Schalten roter Repos → quarantine-Lane Pflicht (G3).
2. **Zweite Wahrheit** durch interim-manuelle Protection vs R2-Reconciler → minimal halten, TTL.
3. **Scheinsicherheit:** Protection gatet Merge, nicht `push`-Deploy/Fast-Deploy → ehrlich als
   notwendig-nicht-hinreichend benennen; Fast-Deploy-Loch separat (ADR-021) tracken.
4. **Break-Glass-Friktion** bei `enforce_admins` ohne zweite Identity → OOTB Profil-B prüfen.
5. **Runner-Queue:** `ci`-Jobs hingen heute >7 min `queued`; mit required-checks warten Merges so
   lange → Kapazität VOR `enforce_admins` adressieren, sonst sieht das Gate kaputt aus.

## 12. Empfehlungen (konkret)

- **REC-1:** ADR-174 `implementation_evidence` um „Bestand 0/14, Drift 2026-06-09 (trading-hub#13)"
  ergänzen; Drift damit sichtbar machen (1 Edit, sofort).
- **REC-2:** **Interim-Pilot** — `enforce_admins: true` + Start-Set (Lint, Unit, gitleaks, Security)
  auf den Prod-Subset (mcp-hub, trading-hub, risk-hub), **nur** Repos die schon F4-grün sind. Via
  `gh api -X PUT …/branches/main/protection`, Audit-Log nach `~/shared/`.
- **REC-3:** G2-Fix — `_ci-python.yml` Coverage-Job auf stabilen Namen; dann Coverage ins Set.
- **REC-4:** ADR-234 R2 um **G1** („`deploy/*` nie required") + **G2** als Vertragsdetail amenden.
- **REC-5:** R2-Reconciler (`plan/apply/rollback`) bauen, der den Interim-Pilot **übernimmt** und auf
  quarantine-fähige Hubs ausweitet — gekoppelt an F4-Konvergenz (`/ci-green-program`).

## 13. Entscheidung + Kill-Gate + 30/60/90

**Offene Toggles (User-Entscheidung — kippen die Umsetzung, nicht das Konzept):**
1. `enforce_admins` für Prod-Subset — **ja/nein**? (empf. ja; ohne ihn nur Versehensschutz)
2. Scope — alle 14 (A-Default) oder nur Prod-Subset starten? (empf. Prod-Subset zuerst)
3. Runner-Queue-Kapazität **vor** `enforce_admins` lösen? (empf. ja — sonst Friktion = Pseudo-Defekt)

**Kill-Gate (messbar):** Nach 2 Wochen Interim-Pilot: blockiert das Gate **mehr legitime
(grün-werdende) Merges als es rote Merges verhindert**, ODER ist **≥1 Break-Glass/Woche** nötig →
Pilot zurückrollen (`DELETE protection`), zurück auf Konvention + reiner Audit-Meter (R5).
Exception-Budget: 1 dokumentiertes Break-Glass im Pilotfenster, danach Re-Evaluation.

**30/60/90:**
- **30 d:** REC-1 (Drift sichtbar) + REC-2 (Interim-Pilot Prod-Subset) live; Kill-Gate-Messung läuft.
- **60 d:** G2-Fix (REC-3) + R2-Amendment (REC-4); Pilot-Auswertung gegen Kill-Gate.
- **90 d:** Entscheidung R2-Reconciler bauen (REC-5) oder Interim als dauerhaftes Minimum mit TTL.

> **Ehrliche Enforcement-Grenze:** Dieses Konzept *schreibt* Felder, *erzwingt* sie nicht.
> `review_by`/`kill_criteria` wirken erst, wenn ein Lifecycle-Gate sie liest. Bis dahin = Review-Gate.

## 14. Kill-Gate-Messung — Instrument nachgerüstet (2026-07-20)

**Befund beim überfälligen Review (`review_by` war 2026-07-09, 11 Tage überschritten):**
Die Break-Glass-Hälfte des Kill-Gates (`≥1 Break-Glass/Woche`) hatte **kein Messinstrument**.
`tools/branch_protection_meter.py` prüft, ob das Ruleset *existiert und aktiv* ist — also
Break-Glass in der Form „Schutz abgeschaltet". Der Regelfall ist aber die andere Form: ein
aktives Ruleset wird für einen einzelnen Merge **umgangen** (`gh pr merge --admin` bzw.
`bypass_actor`). Diese Ereignisse wurden nirgends gezählt. Das Kill-Gate konnte also seit
Pilotbeginn nicht feuern — nicht weil alles gut lief, sondern weil niemand maß.

**Instrument:** `tools/break_glass_meter.py`, verdrahtet als eigener Step in
`.github/workflows/branch-protection-meter.yml` (montags, gleicher Lauf wie der Soll/Ist-Meter,
aber eigenes Label `break-glass` — ein umgangenes Ruleset ist ein Kill-Gate-Signal, keine
Ruleset-Verletzung). Datenquelle: `GET /repos/{owner}/{repo}/rulesets/rule-suites` mit
`rule_suite_result=bypass`; gezählt wird über Wave 1+2, Fenster 2 Wochen, Schwelle 1/Woche.

**Erstmessung 2026-07-20 (Echtlauf, nicht simuliert):** 11 Repos gelesen, **0 Break-Glass**
in 2 Wochen → Kill-Gate feuert nicht. Der Nullwert ist falsifiziert: derselbe Filter liefert
mit `rule_suite_result=pass` 11 Treffer für `platform`, ungefiltert sind alle 11 Suites `pass`.

**Grenzen (bewusst nicht behauptet):**
- Die `rule-suites`-Historie ist **kein Vollarchiv seit Pilotbeginn**. 11 Suites für `platform`
  sind wenig für die Repo-Lebenszeit — das Ergebnis heißt „0 im gelesenen Fenster", nicht
  „seit Pilotstart nie ein Break-Glass". Die Retention des Endpoints ist ungeprüft.
- Gemessen wird **nur** die Break-Glass-Hälfte des Kill-Gates. Die erste Hälfte („mehr legitime
  grün-werdende Merges blockiert als rote verhindert") hat weiterhin **kein** Instrument und
  bleibt ein manuelles Urteil.
- Am 2026-07-20 entstand ein realer Break-Glass-Bedarf außerhalb der Messmenge: `mcp-hub` PR #180
  war strukturell nicht mergebar (1 Collaborator, Ruleset verlangt 1 Approval, GitHub verbietet
  Self-Approval). Sobald dieser Merge per `--admin` erfolgt, sollte ihn der nächste Lauf zählen —
  das ist zugleich der erste echte Funktionsbeweis des Zählers.
