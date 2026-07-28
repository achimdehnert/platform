---
retro_schema: 1
date: 2026-07-27
repo_scope: [iil-klickdummy, coach-hub, 137-hub, trading-hub, billing-hub, tax-hub, dev-hub, research-hub, pptx-hub, dms-hub, onboarding-hub, apo-hub, recruiting-hub, iil-pet-portal, django-lms-lite]
session_id: aa60bb
footprint: deep
findings_total: 14
findings_survived: 13
refuted_rate: 0.07
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [blast-radius-not-measured-against-own-manifest, required-check-red-merged-via-unenforced-admin, root-cause-published-without-route-check]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, ci-gate-maskiert-failure, rollout-completion-ignores-missing-deploy-path]
---

# Session-Retro 2026-07-27 — iil-klickdummy: Sitemap-Konsistenz + coach-hub-Entstörung

**Footprint:** 15 Repos · ~25 PRs · 2 PyPI-Releases + 1 neuer, dauerhaft belegter Paketname · ~20 Prod-Deploys · keine DB-Migration.
**Right-Sizing:** `deep`. Downscale auf `full` geprüft und verworfen — die Bedingung „voll rollback-fähig" scheitert am PyPI-Publish (ein belegter Paketname ist nicht zurücknehmbar).

**Methode:** 1 Collector (haiku) + 3 Finder + 3 Skeptiker + 1 Tie-Break (sonnet), alle mit frischem Kontext. Die Haupt-Session hat in Phase 4 keine eigenen `gh`/`git`-Befehle zur Befund-Prüfung ausgeführt.

---

## 1. Executive Summary

- Der wörtliche Auftrag — „die sitemap für **alle** apps funktioniert und fehlerfrei und konsistent" — ist **nicht erfüllt**. `frist-hub` rendert weiterhin `0 Wurzeln · 0 Knoten` mit totem `kd-nav.js`-Verweis und stand dabei seit dem 2026-07-22 in genau dem Manifest, das die Session am selben Tag selbst editierte.
- Die Abschlussmeldung „13 von 13 Repos konsistent" maß die **bearbeiteten** Repos, nicht die **betroffenen**. Der Blast-Radius wurde nie gegen `genesor-repos.yaml` gehalten: 13 von 21 aktiven Manifest-Einträgen.
- Der Schema-Fix aus #190 ist unvollständig: eine vierte Regex-Stelle (`genesor/validate.py`) blieb `^[a-z]`-gebunden, in einem lebenden Codepfad, ohne Testabdeckung.
- Ein **required** Check war beim Merge von coach-hub #47 seit über zwei Stunden rot — der Merge ging durch, weil `enforce_admins: false` steht. Bei allen anderen coach-hub-PRs waren die Required Checks grün.
- Drei bewusst aufgeschobene Themen bekamen kein Ticket, sondern nur einen Satz im PR-Text — genau die Form, die die Hausregel ausdrücklich nicht als Tracking gelten lässt.

---

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `frist-hub` Sitemap rendert `0 Wurzeln · 0 Knoten`, `_shared/kd-nav.js` fehlt (toter `<script src>`); Repo steht seit 2026-07-22 mit `enabled: true` im Manifest, wurde nie erfasst | fehlende Validierung | kritisch | SURVIVES | `git show origin/main:klickdummy/sitemap/index.html` (frist-hub @ `0ba0cc2`); `git ls-tree -r origin/main -- klickdummy/_shared/` zeigt nur kd-tree.js/.json; `genesor-repos.yaml` Z.21 via Commit `62493bf` (PR iil-pet-portal#30) | neu |
| 2 | Blast-Radius nie gegen das eigene SSoT-Manifest gemessen — 13 von 21 aktiven `kd_path`-Einträgen bearbeitet, Diskrepanz nirgends benannt | Prozesslücke | hoch | SURVIVES | `genesor-repos.yaml` @ origin/main: 22 Einträge (21 enabled); Commit-Suche nach der Rollout-Message findet 12 Repos + risk-hub | neu |
| 3 | `genesor/validate.py:13` `CROSS_REPO_REF_RE = ^[a-z][a-z0-9-]+:ADR-[0-9]{3}$` nicht mitgelockert; `137-hub:ADR-002` scheitert dort weiterhin mit `I4-MALFORMED-REF` (severity error) | fehlende Validierung | hoch | SURVIVES | origin/main:src/iil_klickdummy/genesor/validate.py:13; Import in `render_genesor.py` (Aufruf Z.1360/1367) + Re-Export in `lineage.py` — kein totes Modul; `tests/test_issue179_digit_prefixed_repo.py` deckt diesen Pfad nicht ab | `claim-before-cheapest-check` |
| 4 | `tax-hub`: Sitemap-Fix gemergt, aber `deploy / 🚀 Production` übersprungen — der Fix ist dort **nicht live**; kein späterer Deploy-Run auf main | fehlende Validierung | hoch | SURVIVES | PR #72 mergeCommit `a4d478f` = HEAD origin/main; Run 30250438310: Staging failed, Production skipped; `gh run list --branch main` zeigt keinen späteren Deploy | `rollout-completion-ignores-missing-deploy-path` (Vorkommen 2) |
| 5 | coach-hub #47 gemergt, obwohl der **required** Check `ci / Security Scan` seit 2h09min FAILURE war; möglich durch `enforce_admins: false`, Self-Merge | Prozesslücke | hoch | SURVIVES | `gh pr view 47`: Check completedAt 08:28:33Z / mergedAt 10:37:54Z / mergedBy achimdehnert; `branches/main/protection`: Check required, `enforce_admins.enabled: false`; #49/#51/#52/#53 hatten alle Required Checks grün | `ci-gate-maskiert-failure` |
| 6 | Root-Cause im PR-Text von coach-hub #51 ist falsch: die Views sind **nicht** unrouted, sondern unter `/billing/modules/` erreichbar — nur der Namespace `module_shop` existiert nicht | fehlende Validierung | mittel | SURVIVES | origin/main:config/urls.py bindet `module_catalogue`/`module_toggle` unter `path("billing/modules/", include([...]))` ein, ohne Namespace; repo-weite Suche nach `module_shop:` → 0 Treffer | neu |
| 7 | Wurzel-Fallback aus #192 versagt bei „kein `spec_role: root`" + gegenseitigem `kd_children`-Zyklus → wieder `roots=[]`, `order=[]` | fehlende Validierung | mittel | SURVIVES | Reproduziert gegen origin/main:`gen_sitemap._build_tree`: `roots: []`, `order: []`, `parents: {a: b, b: a}`; der vorhandene Zyklen-Test setzt bei beiden Knoten `spec_role: root` und trifft den Fallback-Pfad nie | neu |
| 8 | Waisen-Warnblock kann bei aktivem Fallback **nie** feuern — auch nicht bei kaputter `kd_children`-Referenz; die Mengen `roots` und „parentlos" sind dann per Konstruktion identisch | verfrühte Festlegung | mittel | SURVIVES | Reproduziert: dangling Ref `ghost-does-not-exist` → `roots: [a, b]`, orphans `[]`; Renderer rechnet `orphans = parent is None AND not in roots` | neu |
| 9 | GHCR-Kausalität in Handover/Memory/Outline **überdehnt**: gemeldet „5 rote Deploys, alle GHCR"; tatsächlich 6 von 9 rot, davon nur 3 mit GHCR-403 | Wissenslücke | mittel | SURVIVES | attempts/1-API je Repo: research-hub/pptx-hub/137-hub = `403 Forbidden` (GHCR); recruiting-hub = `docker-compose.prod.yml absent` (Host-Guard, exit 6); apo-hub = DNS; tax-hub = Migrate-Crashloop | `claim-before-cheapest-check` |
| 10 | Drei bewusst aufgeschobene Themen ohne Tracking-Issue: tote `PROJECT_PAT`-Verdrahtung in coach-hub `deploy.yml` (Z.52/72), Zukunft von `module_views.py` + `django_module_shop`, 80 ruff-Fehler in dms-hub | Prozesslücke | mittel | SURVIVES | `gh issue list --search` in beiden Repos: keine Treffer; `deploy.yml` @ origin/main enthält weiterhin 2× `PROJECT_PAT`; dms-hub Run 30250001918 zeigt exakt 80 `##[error] …py:`-Zeilen | `deferred-item-no-tracking-issue` |
| 11 | Session-Branches bleiben nach Merge stehen — kein „delete branch on merge"; systematisch über ≥2 Repos | Werkzeug | niedrig | SURVIVES | coach-hub `session/2026-07-27/…/test-suite-adr150` (PR #52 MERGED); illustration-hub: 7 von 8 `session/2026-07-27/*`-Branches gehören zu MERGED PRs | `worktree-midsession-accumulation` (verwandt) |
| 12 | Scope wuchs von beauftragten 11 auf 13 Repos + 5 zusätzliche coach-hub-PRs | Kommunikation | mittel | SURVIVES | Auftrag „Rollout in 11 Repos"; Abschluss-Commit `805e23a` nennt 13 Repos; coach-hub #47/#49/#51/#52/#53 | `scope-checkpoint-not-durably-recorded` (jede Stufe war einzeln freigegeben) |
| 13 | Der Handover dokumentiert die Symptom-Fixes, nicht die dadurch **neu entstandene** Altlast (tote PAT-Verdrahtung, verwaistes module_shop-Feature) | Prozesslücke | mittel | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` (iil-klickdummy): weder in der Narrative noch in der Prio-Tabelle erwähnt | `deferred-item-no-tracking-issue` |
| 14 | „Es gibt weitere Repos mit demselben Sitemap-Defekt (0 Wurzeln oder fehlendes kd-nav.js)" | — | — | **REFUTED** | Alle 22 `genesor-repos.yaml`-Einträge je einzeln `git fetch` + `git show origin/main:klickdummy/sitemap/index.html` + `git ls-tree -r origin/main -- klickdummy/_shared/`: 13 Repos mit Sitemap zeigen Wurzeln ≥1 und haben kd-nav.js (apo-hub 3, risk-hub 18, trading-hub 2, illustration-hub 2, je 1 bei tax/dev/dms/research/coach/pptx/onboarding/137/billing/recruiting); 6 Repos haben gar keine generierte Sitemap (ausschreibungs-hub, design-hub, nl2iot-hub, ttz-hub, pg-hub, meiki-hub); bahn-sqf-pg-hub ist der dokumentierte Phantom-Eintrag | — |

---

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **3** | Zwei Releases, 12+1 Repos, coach-hub wieder deploybar, neues Paket publiziert — aber der wörtliche Kern-Anspruch ist an zwei harten Stellen verfehlt (#1 frist-hub, #4 tax-hub nicht live) |
| architektur_design | **3** | Aggregat-Dedup, Paket-Asset-Auslieferung und OIDC-Publish mit Distributions-Guard sind strukturell richtig (Skeptiker: „solide, am echten publizierten Artefakt verifiziert"); dagegen #7/#8 zwei Randfall-Löcher im eigenen Fix und #3 eine vergessene vierte Stelle |
| code_konventionstreue | **4** | Tests zu jedem Fix, ruff/format sauber, Commit-Konvention eingehalten, A/B-Belege in den PR-Bodies; Abzug für #3 (unvollständiger Fix trotz Regressionstest) |
| risiko_debt | **2** | #10 drei ungetrackte Reste trotz expliziter Hausregel, #13 Handover verschweigt die neue Altlast, #11 verwaiste Branches — die schwächste Dimension, deckungsgleich mit dem Flotten-Mittel (Ø 2,61) |
| prozess_effizienz | **3** | Viel geliefert, aber 6 von 9 Batch-Deploys scheiterten in Attempt 1 und brauchten Reruns (#9); zusätzlich Rework durch die Reihenfolge Merge-vor-Fix bei coach-hub #47 |
| entscheidungsqualitaet | **3** | Gute, belegte Entscheidungen bei A-vs-B (Publish statt Vendoring), Scoring-Skala und `/healthz/` — dagegen #6 eine im PR-Text veröffentlichte Fehldiagnose und #5 ein Merge über einen roten Required Check |

---

## 4. Soll-Ablauf (Ist → Soll → eliminiert)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `frist-hub` blieb defekt, obwohl es im Manifest stand — Betroffenheit wurde aus der Erinnerung an den Vor-Rollout abgeleitet (PR #192 listet 8 Repos) | Vor dem Fix-Rollout die Betroffenen-Liste **aus `genesor-repos.yaml` generieren** und jeden Eintrag mit `kd_path` einzeln prüfen — das Manifest ist SSoT und lag in derselben Session offen | #1 |
| „13/13 korrekt" wurde gegen die bearbeiteten Repos gemessen, nicht gegen die Grundgesamtheit | Die Abschluss-Verifikation läuft über **alle** Manifest-Einträge; Repos ohne Sitemap explizit als „nicht anwendbar" ausweisen statt stillschweigend weglassen | #2 |
| Regex-Lockerung an den zwei im Issue genannten Dateien vorgenommen | Vor Abschluss ein `git grep -n '\[a-z\]\[a-z0-9'` über den ganzen Baum — die billigste Vollständigkeitsprüfung, die es hier gibt | #3 |
| „Deploy-Run grün" wurde als Rollout-Erfolg gebucht; bei tax-hub war Production skipped | Erfolgskriterium ist der **Production-Job**, nicht der Run-Gesamtstatus; `deploy / 🚀 Production` explizit auf `success` prüfen, `skipped` zählt als offen | #4 |
| PR #47 gemergt, während ein Required Check seit 2h rot war | Vor jedem Merge `gh pr view --json statusCheckRollup` gegen die **Required-Liste** der Branch-Protection halten — nicht gegen `mergeStateStatus`, das bei `enforce_admins: false` grünes Licht suggeriert | #5 |
| Root Cause „Views sind unrouted" aus einem `grep` nach dem Namespace-String geschlossen | Bei `NoReverseMatch` zusätzlich nach den **View-Funktionsnamen** in `urls.py` suchen, bevor die Ursache in den PR-Text geschrieben wird | #6 |
| Zyklen-Test mit `spec_role: root` für beide Knoten geschrieben | Testmatrix orthogonal durchzählen: (Root deklariert × nicht deklariert) × (Zyklus × kein Zyklus) — der Fallback-Pfad braucht eigene Fälle | #7 |
| Waisen-Block gegen `tree["roots"]` gerechnet, nachdem `roots` seine Bedeutung wechselt | Zwei getrennte Größen führen: `declared_roots` (aus `spec_role`) und `render_roots` (nach Fallback); der Waisen-Block rechnet gegen `declared_roots` | #8 |
| Fünf Fehlschläge unter einer Ursache subsumiert, nachdem drei Logs GHCR zeigten | Bei Mehrfach-Fehlschlägen **jeden** Lauf einzeln zuordnen, bevor eine gemeinsame Ursache benannt wird; Reruns überschreiben die Conclusion → `attempts/1` lesen | #9 |
| „Folge-PR" im PR-Text als Aufschub-Vermerk für drei Reste | Jeder Aufschub bekommt im selben Zug ein Issue mit Link; der PR-Text verweist auf das Issue, statt es zu ersetzen | #10 |
| Der Handover listet die behobenen Symptome, nicht die dabei neu entstandene Altlast | Am Session-Ende die **neu geschaffene** Schuld getrennt aufführen — was durch die Fixes tot/verwaist zurückblieb, gehört in die Prio-Tabelle, nicht nur das Erledigte | #13 |
| Branches blieben nach Merge stehen | `--delete-branch` beim Merge (wurde genutzt) **plus** repo-seitig `delete_branch_on_merge: true` setzen, damit auch fremd gemergte PRs aufräumen | #11 |
| Scope wuchs schrittweise, jede Stufe einzeln freigegeben, aber nie als Gesamtbild gespiegelt | Beim Überschreiten der beauftragten Menge einmal die **kumulierte** Bilanz zeigen („beauftragt 11, aktuell 13 + 5 Folge-PRs") statt nur die nächste Einzelstufe | #12 |

**Invariante geprüft:** 13 überlebende Befunde ↔ 13 Soll-Schritte. ✅

---

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 55 Reports vor diesem Lauf: **18 Slugs bereits ≥2 ⇒ gate-pflichtig**. Drei davon werden hier erneut instanziiert, ein vierter erreicht mit dieser Session die Schwelle:

| Slug | Instanz in dieser Session | Status |
|---|---|---|
| `claim-before-cheapest-check` | #3 (vergessene vierte Regex-Stelle — ein `git grep` hätte gereicht), #9 (Ursache verallgemeinert, bevor alle Logs gelesen waren) | bereits gate-pflichtig, **erneut** |
| `deferred-item-no-tracking-issue` | #10, #13 — drei Reste nur im PR-Text vermerkt | bereits gate-pflichtig, **erneut** |
| `ci-gate-maskiert-failure` | #5 — `ci / gate` grün, während ein Required Check rot war | bereits gate-pflichtig, **erneut** |
| `rollout-completion-ignores-missing-deploy-path` | #4 — tax-hub als „gemergt" gezählt, Production übersprungen | Erstvorkommen `c25d21` (2026-07-16, dort als Erstvorkommen deklariert) → hier **Vorkommen 2 ⇒ ab jetzt gate-pflichtig** |

**Neu, Vorkommen 1 (noch kein Gate):** `blast-radius-not-measured-against-own-manifest` (#1/#2), `required-check-red-merged-via-unenforced-admin` (#5), `root-cause-published-without-route-check` (#6).

Der `claim-before-cheapest-check`-Slug feuert in dieser Session **dreimal** (#3, #9, plus die während der Session selbst korrigierte PAT-Entwarnung). Das ist kein Notizzettel-Thema mehr.

---

## 5b. Autonomie-Kalibrierung

- **`over_act` = 1** — Merge von coach-hub #47 bei rotem Required Check (#5). Die Batch-Freigabe des Nutzers deckte den Rollout, nicht das Übergehen eines Pflicht-Gates.
- **`over_ask` = 0** — kein Fall gefunden, in dem etwas deterministisch/reversibles unnötig vorgelegt wurde. Die Rückfragen betrafen durchweg Prod/Publish/Produktentscheidungen.

Bemerkenswert in die andere Richtung: Bei Gate-2-Schritten wurde konsequent innegehalten (PyPI-Publish, jeder Prod-Merge, das Anlegen des OIDC-Publishers) — inklusive eines Stopps, nachdem der Nutzer bereits „nach deiner prio" gesagt hatte, weil ein neuer PR nicht von der ursprünglichen Freigabe gedeckt war.

---

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: blast-radius-from-manifest-not-memory
description: Fix-Rollout-Umfang aus dem SSoT-Manifest generieren, nicht aus der Erinnerung an den Vor-Rollout
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-27-frist-hub-missed
---
Bei einem Fix, der einen Generator betrifft, die Betroffenen-Liste **aus dem
Manifest generieren** (`iil-pet-portal/genesor-repos.yaml`), nicht aus der
Erinnerung an den vorigen Rollout.

**Why:** 2026-07-27 wurden 13 Repos regeneriert und als „13/13 korrekt"
verifiziert — gemessen an der Änderungsmenge, nicht an der Grundgesamtheit.
`frist-hub` stand seit dem 2026-07-22 mit `enabled: true` im selben Manifest,
das die Session am selben Tag editierte, und blieb defekt (`0 Wurzeln`, totes
`kd-nav.js`). Die Verifikation war methodisch zirkulär: sie prüfte, was
angefasst wurde.

**How to apply:** Vor dem Rollout `genesor-repos.yaml` lesen, je Eintrag mit
`kd_path` den Ist-Zustand ziehen, Repos ohne Artefakt ausdrücklich als „nicht
anwendbar" ausweisen. Die Abschluss-Verifikation läuft über dieselbe Liste.
Ergänzt [[rollout-count-ignores-deploy-path]].
```

```markdown
---
name: required-check-vs-mergestate
description: Vor dem Merge gegen die Required-Liste der Branch-Protection prüfen, nicht gegen mergeStateStatus
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-27-coach-hub-47
---
`mergeStateStatus` ist **kein** Beweis, dass die Pflicht-Checks grün sind.
Steht `enforce_admins: false`, lässt GitHub den Merge durch, obwohl ein
required Check rot ist.

**Why:** 2026-07-27 wurde coach-hub #47 gemergt, während
`ci / Security Scan (pip-audit + pip check)` seit 2h09min FAILURE war — der
Check ist required, aber `enforce_admins.enabled: false`. In derselben Session
wurde bei #49/#51 korrekt argumentiert, der rote `Test`-Job sei nicht required
— beim PR mit dem echten Bypass fiel es nicht auf.

**How to apply:** `gh api repos/<o>/<r>/branches/main/protection` einmal je Repo
lesen und die Required-Namen gegen `gh pr view --json statusCheckRollup`
halten. Bei `enforce_admins: false` zusätzlich prüfen, ob ein Required Check rot
ist. Verwandt: [[merge-over-red-ci-no-protection]].
```

### adr_candidates

Keiner. Alle Befunde sind Prozess- oder Implementierungslücken innerhalb bestehender Muster — die ADR-Schwelle (`adr-threshold.md`: neue Service-Grenze, Umkehr einer Entscheidung, Cross-Cutting-Trade-off) ist nicht erreicht. Der einzige Grenzfall wäre eine Registry für lokale Dev-DB-Ports; `infra/ports.yaml` schließt interne Ports aber ausdrücklich aus, und die Entscheidung ist dort bereits getroffen.

---

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 `enforce_admins` in coach-hub aktivieren oder bewusst dokumentieren — https://github.com/achimdehnert/coach-hub/settings/branches
2. 🟢 tax-hub Production-Deploy nachholen (Fix ist nicht live) — https://github.com/iilgmbh/tax-hub/issues/73

### 🔵 Offen — ich kann sofort

3. 🔵 frist-hub-Sitemap regenerieren + kd-nav.js — https://github.com/iilgmbh/iil-klickdummy/issues/176
4. 🔵 `genesor/validate.py` Regex nachziehen + Test — https://github.com/iilgmbh/iil-klickdummy/issues/179
5. 🔵 Drei Tracking-Issues nachlegen (PAT-Wiring, module_shop, dms-hub-ruff) — https://github.com/achimdehnert/coach-hub/issues/50
6. 🔵 Wurzel-Fallback: `declared_roots` von `render_roots` trennen — https://github.com/iilgmbh/iil-klickdummy/pull/192
7. 🔵 coach-hub #51 PR-Text korrigieren (Views sind geroutet) — https://github.com/achimdehnert/coach-hub/pull/51

---

## 8. Nicht verifiziert (Restlücken)

- **Divergenz beim tax-hub-Staging-Fehler.** Issue #73 nennt `tax_hub_staging_migrate im Zustand 'exited'`, ein Skeptiker las `PROJECT_PAT= is not a valid secret`, der Tie-Break wieder den Crashloop. Möglicherweise stehen beide im Log. Billigster Check: `gh run view 30250438310 --log-failed` vollständig lesen statt gefiltert.
- **recruiting-hubs Attempt-1-Fehler.** Während der Session zeigte ein Log-Grep `429`; der Tie-Break nennt `docker-compose.prod.yml absent` (Host-Guard). Nicht abschließend zugeordnet. Billigster Check: `gh run view 30250472036 --attempt 1 --log-failed` ungefiltert.
- **Live-Wirkung von coach-hub #51.** Dass der `NoReverseMatch` eingeloggte Seiten wirklich 500te, ist nie gegen Prod geprüft worden — anonym ist die Sidebar nicht erreichbar. Billigster Check: Login + eine Seite mit Sidebar öffnen, oder Prod-Logs nach `NoReverseMatch`.
- **Methoden-Auffälligkeit statt Befund:** Der Prozess-Skeptiker widerlegte die GHCR-Kausalität, weil er die **aktuelle** Run-Conclusion las — Reruns hatten sie überschrieben. Erst der Tie-Break über `attempts/1` stellte den Finder-Befund wieder her. Die Skill-Regel „Skeptiker zieht breiter neu" hat hier in die falsche Richtung gewirkt: breiter hieß nicht automatisch tiefer. **Vorschlag für die Skill:** in die Phase-3-Regel aufnehmen, dass bei Run-/Deploy-Behauptungen `attempts/1` gelesen wird, weil `gh run rerun` die `conclusion` überschreibt — ein Skeptiker, der nur den Endstand liest, widerlegt systematisch jeden gererunten Fehlschlag.

## Self-Review (Phase 5, Meta-Agent)

Der Meta-Reviewer prüfte ausschließlich den Report gegen die Skill-Regeln und fand **drei Verstöße**, alle vor dem Commit behoben:

1. **Invariante falsch ausgezählt** — der Report behauptete „13 ↔ 13", die Soll-Tabelle hatte 12 Zeilen (zwei Befund-Paare zusammengefasst). Aufgetrennt, jetzt 13 ↔ 13 maschinell nachgezählt.
2. **Phantom-Slug** — `rollout-count-ignores-deploy-path` existiert in keinem Report-Frontmatter; der reale Slug heißt `rollout-completion-ignores-missing-deploy-path` und war in `c25d21` selbst Erstvorkommen. Korrigiert; die Einstufung ändert sich damit von „bereits gate-pflichtig" zu „Vorkommen 2 ⇒ ab jetzt gate-pflichtig". Der gleichnamige `[[…]]`-Verweis im Memory-Kandidaten bleibt, weil die Memory-Datei unter diesem Namen tatsächlich existiert.
3. **Beleg-Schwäche in Zeile #14** (REFUTED) — zusammenfassende Aussage statt hartem Einzelbeleg. Durch die vollständige Repo-Aufzählung mit Kommando ersetzt.

Numerischer Band-Vergleich (`retro_kpis.py`): `refuted_rate` 0,07 gegen den Trend 0,08 · 0,20 · 0,00 · 0,11 · 0,35 · 0,21 · 0,13 · 0,22 — zweitniedrigster Wert der Reihe, unterhalb der 0,2-Marke. Kein automatischer Fail (nicht 3× in Folge), aber ein Hinweis, dass die Finder in diesem Lauf wenig Widerlegbares produziert haben. Echte Falsifikationsquote `phase3_refuted/(findings_total − pre_refuted)` = 1/14 = 0,07, deckungsgleich.
