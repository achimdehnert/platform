---
concept_id: KONZ-platform-065
title: ADR-Evidenzvertrag — maschinenprüfbare Belege statt Prosa-Confirmation, Fälligkeit statt Alter
pipeline_status: idea
tier: T2                   # bedingt — T3, sobald das iil-adrfw-Schema geändert oder die Flotte (32 Repos) verpflichtet wird
owner: Achim Dehnert
spec_refs: []              # kein Klickdummy/Spec-Bezug — Governance-Werkzeug, keine ADR-211-Anwendung
adr_threshold: Amendment   # ADR-138 §2.4 definiert das Belegformat heute als Prosa-Muster; der Vertrag ist dessen typisierter Nachfolger
review_by: 2026-12-31
kill_criteria: "Bis 2026-11-30 tragen weniger als 8 der 10 Pilot-ADRs je mindestens zwei ECHTE typisierte Belege, ODER der Prüfer meldet auf dem Pilot mehr als 10 % Falsch-Positive — dann bleibt implementation_evidence Prosa nach ADR-138, keine Flotten-Ausweitung."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "https://github.com/achimdehnert/dev-hub/issues/374", commit_or_pr: "dev-hub#374", opened_in_session: true}
  - {claim_id: C2, source_path: "https://github.com/achimdehnert/platform/issues/2962", commit_or_pr: "#2962", opened_in_session: true}
  - {claim_id: C3, source_path: "tools/adr_evidence_paths.py", commit_or_pr: "a7aeedf2", opened_in_session: true}
  - {claim_id: C4, source_path: ".github/workflows/adr-validate.yml", commit_or_pr: "a7aeedf2 (Z. 140–160)", opened_in_session: true}
  - {claim_id: C5, source_path: "iil-adrfw:src/iil_adrfw/schemas/adr_frontmatter.schema.json", commit_or_pr: "iil-adrfw@5c31912", opened_in_session: true}
  - {claim_id: C6, source_path: "docs/templates/adr-template.md", commit_or_pr: "a7aeedf2", opened_in_session: true}
  - {claim_id: C7, source_path: "docs/adr/ADR-138-implementation-tracking-standard.md", commit_or_pr: "a7aeedf2 (§2.1, §2.4, §2.5)", opened_in_session: true}
  - {claim_id: C8, source_path: "docs/adr/ADR-059-adr-drift-detector.md", commit_or_pr: "a7aeedf2 (§3, §4 Kriterium 5, §6)", opened_in_session: true}
  - {claim_id: C9, source_path: "docs/governance/gates/ (README.md, _meta.json, gates/claim-before-cheapest-check.json)", commit_or_pr: "a7aeedf2", opened_in_session: true}
  - {claim_id: C10, source_path: "docs/adr/ADR-*.md Frontmatter (Zählung über origin/main)", commit_or_pr: "Messung 2026-09-23 @ a7aeedf2", opened_in_session: true}
  - {claim_id: C11, source_path: "tools/adr_evidence_paths.py --format human (Lauf im Worktree)", commit_or_pr: "Messung 2026-09-23 @ a7aeedf2", opened_in_session: true}
  - {claim_id: C12, source_path: "tools/adr_umsetzungsstand_check.py (Lauf im Worktree)", commit_or_pr: "Messung 2026-09-23 @ a7aeedf2", opened_in_session: true}
created: 2026-09-23
---

# KONZ-platform-065 — ADR-Evidenzvertrag statt Prosa-Confirmation

> Auftrag: Owner-Wort 2026-09-23 „A7 ja" zu
> [dev-hub#374](https://github.com/achimdehnert/dev-hub/issues/374) §6 Schritt 5 (OOTB-1 + OOTB-3).
> **Tier T2, bedingt.** T2, weil das Konzept eine neue lokale Konvention in einem Repo
> (platform) setzt und ein persistentes Artefakt ändert (Frontmatter von 10 ADRs) — beides
> Auto-Eskalations-Trigger, also mindestens T2. **Nicht T3, solange** kein Schlüssel im
> iil-adrfw-Schema hinzukommt und kein zweites Repo verpflichtet wird. Beide Schwellen
> stehen unten als eigene Entscheidung (D4); wer sie überschreitet, hebt sichtbar auf T3.

## Kernthese

Ein ADR, dessen Nachweis nur als Absatz existiert, kann nicht brechen — und genau deshalb
merkt niemand, wenn er gebrochen ist; der Nachweis gehört als Liste prüfbarer Zeiger ins
Frontmatter, die Prüfung ist eine Existenzfrage, nie eine Ausführung, und fällig wird ein
ADR nach Kalender, nicht nach dem Datum des letzten Detektor-Laufs.

## Steelman — warum der heutige Zustand gut ist

Die Bausteine sind alle da, und sie sind nicht schlecht. ADR-138 verlangt seit März 2026
`implementation_status` für jedes accepted ADR und gibt fünf Belegmuster vor (C7). ADR-059
hat den Detektor beschlossen, der die Belege lesen soll, samt `drift_check_paths` und
`staleness_months` (C8). Das Schema von iil-adrfw kennt beide Felder plus `last_reviewed`
und `implementation_done_when` (C5). `tools/adr_evidence_paths.py` prüft seit Juli, ob
Belegpfade existieren, mit 0 bekannten Falsch-Positiven (C3, C4). In platform tragen 102
von 191 accepted ADRs `implementation_evidence`, 52 ein `staleness_months`, 50 ein
`last_reviewed` (C10).

Wer hier „alles Prosa" ruft, übersieht, dass ein Drittel der Flotte bereits typisierbare
Zeiger führt und die Prüfung für Pfade läuft. Die ehrliche Gegenposition: **das Problem ist
nicht das Fehlen eines Vertrags, sondern dass die vorhandenen Felder von niemandem gelesen
werden** — der dev-hub-Detektor ignoriert `implementation_status`, `implementation_evidence`
und `drift_check_paths` vollständig (C1 B5), und der platform-Prüfer läuft `exit 0` (C4).

Der Punkt, an dem sie kippt: ein Leser kann die vorhandenen Belege nicht *maschinell*
unterscheiden. „all hubs: static asset versioning active" (ADR-031) und
„.github/workflows/_ci-python.yml" (ADR-226) stehen im selben Feld, im selben Format — der
erste ist unprüfbar, der zweite ist prüfbar und **falsch** (C11). Ohne Typ weiß kein Prüfer,
welche Zeile er anfassen darf.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | 406 von 463 ADRs (32 Repos) tragen `review_needed`; 374 davon **nur** wegen `missing_confirmation`; bereinigt bleiben 21 echte Drift-Fälle; 280 accepted ADRs in aktiven Repos ohne Confirmation | Annahme→belegt | C1 B1, B8 (Prod-DB-Abfragen dort dokumentiert; hier nicht neu gemessen) | belegt, fremd |
| L2 | Die Confirmation-Prüfung ist eine Stilprüfung: `"## Confirmation" in content`; die eigene Vorlage schreibt `## 8. Confirmation` und fällt durch | Annahme→belegt | C1 B2; C6 Z. 212; C8 §4 Z. 241 | belegt |
| L3 | Das Veraltet-Signal ist tot: der Detektor überschreibt `updated_at` bei jedem Lauf (458/463 = 2026-09-21) | Annahme→belegt | C1 B4 | belegt, fremd |
| L4 | platform: 191 accepted ADRs — 80 implemented, 46 partial, 5 in_progress, 4 verified, 3 complete, 14 none, **39 ohne das Feld** trotz ADR-138 „MUST" | Annahme→belegt | C10; C12 listet die 14 `none` (#2962 offen seit Retro 61c35d) | belegt |
| L5 | Belegformat heute: Prosa-Muster nach ADR-138 §2.4 — fünf Arten, keine davon maschinell unterscheidbar | Annahme→belegt | C7 §2.4: „aifw/tests/test_lookup_cascade.py: 9 test cases" neben „all 29 repos: catalog-info.yaml present" | belegt |
| L6 | Der vorhandene Prüfer deckt nur **Pfade**, nur platform-lokal, nur SUGGEST: 161 Kandidaten → 39 geprüft, 43 cross-repo übersprungen, 71 fremder Root, 8 Teilspiegel; 2 Findings | Annahme→belegt | C11: ADR-174 Z. 9 und ADR-226 Z. 15 zeigen beide auf `_ci-python.yml`, das nicht existiert; C4: `set +e … exit 0` | belegt |
| L7 | Ein neuer Frontmatter-Schlüssel (`confirmation:`, `review_by:`) macht **jede** ADR-PR der Flotte rot: Schema ist `additionalProperties: false` | Annahme→belegt | C5; Memory `reference_adr_frontmatter_schema_strict` (Realfall 2026-07-19, 6 ADRs blockierten 2 PRs) | belegt |
| L8 | Fälligkeit existiert im Schema bereits: `staleness_months` („used to compute next_review_date") + `last_reviewed`; in platform 52 bzw. 50 ADRs | Annahme→belegt | C5; C10; C8 §6 („Template v2: staleness_months + drift_check_paths") | belegt — `review_by` wäre zweite Wahrheit |
| L9 | Die Gate-Registry ist eine prüfbare Menge: 49 Gates als `gates/<slug>.json` mit `module`, `drill`, `positivkontrolle`; gelesen über `tools/gate_registry.py` | Annahme→belegt | C9 | belegt |
| L10 | Der Prüfer darf nichts ausführen: ADR-Texte aus 32 Repos wären sonst ein Lieferketten-Einfallstor | Entscheidung | C1 OOTB-1; Alternative wäre „Testdatei ausführen" — verworfen, s. Befund B3 | gesetzt |
| L11 | Kein neues Feld, kein neuer Prüfer, kein neues Scoreboard — der Vertrag lebt im vorhandenen `implementation_evidence`, geprüft vom vorhandenen `adr_evidence_paths.py`, gemeldet im vorhandenen Job | Entscheidung | SSoT-Prüfung gegen L5–L9; Alternative A1 (Schema-Objekt) s. unten | gesetzt |
| L12 | Der Aufwand je ADR ist **unbekannt**; ohne Zahl ist jede Backfill-Aussage über 280 ADRs eine Vermutung | Risiko | keine Messung vorhanden; **Hypothese** 20–40 min/ADR → 280 × 30 min ≈ 140 h | offen → Pilot misst |
| L13 | Belege rotten: der Pfad stimmt am Tag des Eintrags und drei Monate später nicht mehr (ADR-158, `_ARCHIVED/`, unbemerkt) | Risiko | C3 Docstring (platform#1289) | offen → genau das soll der Vertrag sichtbar machen |

## MVC — kleinster tragfähiger Schnitt

**Ausführungsform** (Step 2a): Frage 1 — braucht es mehrere Schritte? Nein. Ein Skriptlauf
über `docs/adr/`, eine Ausgabe. **Ein Aufruf, keine Kette, keine Schleife.** Der
dev-hub-Detektor ist ein *zweiter Konsument* desselben Aufrufs, kein zweiter Schritt (D4).

### 1. Vertragsform — typisierte Zeilen im vorhandenen Feld (kein Schema-Change, L7/L11)

`implementation_evidence` bleibt `array[string]`. Neu ist nur eine Zeilenkonvention, die
ADR-138 §2.4 als Amendment ergänzt:

```yaml
implementation_evidence:
  - "path: tools/adr_evidence_paths.py"                                  # existiert im Repo
  - "path: dev-hub:apps/adr_lifecycle/services.py"                        # cross-repo: Repo-Präfix, prüft nur dessen CI
  - "gate: claim-before-cheapest-check"                                   # Slug in docs/governance/gates/gates/
  - "test: tools/claude-hooks/tests/test_evidence_claim_scanner.py"       # Datei existiert — wird NIE ausgeführt
  - "pr: platform#1643"                                                   # Formatprüfung, kein API-Aufruf
  - "Base pipeline in production on the Hetzner VM since 2026-02"         # untypisiert: erlaubt, zählt als Prosa
```

Vier Typen im Pilot: `path`, `gate`, `test`, `pr`. **`metric:` bewusst nicht** — es gibt
in platform keine Registry von Melder-Ergebnissen, gegen die eine Existenz geprüft werden
könnte; das käme als Stufe 2, wenn `gate_wirkung.py` ein maschinenlesbares Ergebnis ablegt.
Untypisierte Zeilen bleiben gültig (Bestandsschutz für 102 ADRs) und werden als **Prosa**
gezählt — das ist die Form-Quote aus dev-hub#374 §2, ohne neues Flag.

### 2. Prüfer — `tools/adr_evidence_paths.py` erweitern, nicht ersetzen

Drei neue Finding-Kategorien neben `dead_path`/`archived_path`: `unknown_gate` (Slug nicht
in `gates/`, `declined/`, `widerrufen/`), `missing_test` (Datei fehlt), `malformed_pr`
(kein `owner/repo#N`- oder `repo#N`-Muster). Dazu je ADR die Zählung `typisiert / prosa`.
Weiterhin **SUGGEST** im bestehenden Job (C4) — mit einer Ausnahme: `--gate` gilt für
die Pilotliste (Datei `docs/adr/.adr-evidence-pilot`, ein ADR je Zeile). Dort ist ein
Finding rot. Das ist dieselbe Promotion-Logik, die der Job-Kommentar seit Juli
vorsieht („erst nach sauberer Baseline"), nur auf zehn Dateien begrenzt.

### 3. Fälligkeit — rechnen statt neu erfinden (OOTB-3, L8)

Kein `review_by` im ADR. Fällig = `last_reviewed` (Rückfall `decision_date`) +
`staleness_months` (Rückfall nach Typ, s. D3). Der Prüfer gibt je ADR „fällig am" aus und
markiert `T-30`. Der Detektor in dev-hub übernimmt dieselbe Formel und speist sie aus dem
Git-Datum der Datei, nicht aus `updated_at` (C1 §6 Schritt 0a) — das ist dev-hub#374,
nicht dieses Konzept.

### 4. Pilot — 10 accepted ADRs in platform, echte Belege

Auswahlregel: `status: accepted`, `implementation_status ∈ {implemented, complete,
verified}`, Belege überwiegend platform-lokal. Gesetzt sind: **ADR-174** und **ADR-226**
(die zwei offenen Findings, C11 — zuerst reparieren, dann typisieren), **ADR-059**
(der Detektor selbst), **ADR-138** (der Standard, den der Vertrag ergänzt), **ADR-190**
(iil-adrfw), **ADR-239** (nennt ein Gate). Vier weitere nach Regel aus den 71 Kandidaten
(C10), Entscheid im Pilot-PR. Je ADR wird die Umstellzeit in Minuten in den PR-Text
geschrieben — das ist die einzige Quelle für L12.

Bewusst **nicht** im MVC: Backfill der 280 (D2), Schema-Objekt statt Zeilenkonvention (A1),
Flotten-Rollout, LLM-generierte Belege, Ausführen irgendeiner referenzierten Datei,
Umbau des dev-hub-Detektors (läuft unter dev-hub#374).

## Befunde inkl. Advocatus Diabolus und Maintainer 2028

| # | Befund | Herkunft | Antwort |
|---|---|---|---|
| B1 | **Evidenz rottet.** Ein Pfad stimmt beim Eintragen und nach dem nächsten Refactor nicht mehr; der Vertrag erzeugt damit *mehr* rote Meldungen, nicht weniger | Diabolus, stärkster Einwand | Anerkannt — und gewollt. Heute rottet die Evidenz **unsichtbar** (ADR-158: drei Monate, C3). Ein Finding „Beleg bricht" ist genau das Drift-Signal, das der Detektor nicht hat. Die Schwelle steht im Kill-Gate: > 10 % Falsch-Positive im Pilot, und der Vertrag ist gescheitert, nicht die ADRs |
| B2 | **Wer pflegt 280 Backfills?** Niemand. 39 platform-ADRs haben nach sechs Monaten ADR-138 nicht einmal das Pflichtfeld (L4) | Diabolus | Deshalb **kein Backfill-Mandat** (D2). Vertrag gilt für den Pilot, für neue ADRs (Draft-Guard) und für ADRs, die ohnehin angefasst werden. Der Rest bleibt Prosa und wird als Quote sichtbar — dieselbe Herabstufung, die #374 §2 für `missing_confirmation` vorsieht |
| B3 | Warum die Testdatei nicht laufen lassen? Existenz beweist nichts | Diabolus | Weil ein Prüfer, der Dateien aus 32 Repos ausführt, ein Lieferketten-Einfallstor ist (L10). Existenz beweist wenig, aber sie *bricht* — und Bruch ist das gesuchte Signal. Ob der Test grün ist, prüft die CI des Repos, nicht der ADR-Prüfer |
| B4 | Zweite Wahrheit: `gate:` im ADR neben `ref` im Gate-JSON — welche gilt bei Widerspruch? | SSoT-Prüfung | Die Registry (C9). Das ADR *zeigt* auf den Slug, es beschreibt ihn nicht. Verschwindet der Slug, wird das ADR rot, nicht die Registry |
| B5 | `review_by` je ADR-Typ klingt sauberer als eine Rechenformel | Diabolus | Klingt so, ist aber ein zweites Feld für dieselbe Aussage (L8). `staleness_months` ist genau dafür da, in 52 ADRs gesetzt und im Schema als Rechengrundlage beschrieben. Neues Feld = Schema-Change = Flotten-Rot (L7) |
| B6 | Maintainer 2028 findet zwei Belegformate im selben Feld — typisiert und Prosa — und weiß nicht, welches gilt | Maintainer-2028 | Beide gelten; die Zählung `typisiert / prosa` je ADR sagt ihm auf einen Blick, wie belastbar das ADR ist. Ohne diese Zählung wäre der Einwand richtig — sie ist deshalb Teil des MVC, nicht Kür |
| B7 | Die Zeilenkonvention ist eine Bitte, keine Schranke: wer `path:` vergisst, schreibt Prosa und ist formal in Ordnung | Diabolus | Richtig, und im Pilot bewusst so: erzwungen wird nur auf der Pilotliste (`--gate`). Ob Zwang für neue ADRs folgt, entscheidet das Kill-Gate — vorher wäre es ein Melder, der immer feuert |
| B8 | Der Prüfer sieht 43 cross-repo-Belege nicht (L6); der Vertrag ist damit für fleet-weite ADRs halb blind | Befund | Stimmt, und bleibt so, bis jedes Repo den Prüfer in seiner eigenen CI laufen lässt — das ist der Flotten-Schritt (D4, T3), nicht der Pilot. Das Repo-Präfix in `path:` macht die Blindstelle wenigstens zählbar |
| B9 | Vorlage sagt „§9 Confirmation" in den Pflichtfeldern und `## 8. Confirmation` als Überschrift (C6 Z. 26 vs. 212) | Befund, nebenbei | Nummernfehler in der Vorlage; gehört in den Pilot-PR als Einzeiler, kein eigener Vorgang |

## Alternativen

| # | Alternative | Warum nicht (jetzt) |
|---|---|---|
| A1 | Neuer Schema-Schlüssel `confirmation:` als Objekt (`{path:[], gate:[], test:[], metric:[]}`) in iil-adrfw | Sauberer, aber T3: Schema-Release, Flotten-Validate, jede ADR-PR in 32 Repos betroffen (L7). Erst sinnvoll, wenn der Pilot zeigt, dass typisierte Belege überhaupt gepflegt werden. Als Stufe 2 nach bestandenem Kill-Gate vorgesehen |
| A2 | Nur dev-hub#374 Schritt 0 (Regex auf `## 8. Confirmation`, `missing_confirmation` ohne Flag) und sonst nichts | Macht die Liste ehrlich (406 → ≈ 21), liefert aber weiterhin keinen Beleg, der brechen kann. Löst das Lärmproblem, nicht das Nachweisproblem. Läuft ohnehin, unabhängig von diesem Konzept |

## Top-3-Risiken

| # | Risiko | Eintritt erkennbar an | Gegenmittel |
|---|---|---|---|
| R1 | Belege werden typisiert, aber erfunden — „test: …" zeigt auf eine Datei, die den ADR nicht prüft | Pilot-Review findet eine typisierte Zeile ohne inhaltlichen Bezug | Im Pilot liest der Owner jede Zeile; danach: `gate:` muss in `faengt`/`drill` des Gates auftauchen (C9 `_faengt_doc`), sonst Finding `gate_unrelated` (Stufe 2) |
| R2 | Der Prüfer wird zum Dauerrot auf der Pilotliste, weil Pfade sich bewegen (B1) | > 1 Finding je Lauf über 30 Tage ohne Fix | Kill-Gate-Schwelle 10 % Falsch-Positive; echte Bewegungen sind kein Falsch-Positiv, sondern der Zweck |
| R3 | Der Pilot bleibt ein platform-Sonderweg; dev-hub baut in #374 eine eigene Regel und die Formate driften (G3 in C1) | dev-hub prüft `implementation_evidence` mit anderem Parser | D4: der Parser lebt in platform (`adr_evidence_paths.py`) oder iil-adrfw, dev-hub ruft ihn — Entscheidung vor dem Flotten-Schritt, nicht danach |

## Kill-Gate

**Schwelle:** Bis **2026-11-30** tragen weniger als **8 der 10** Pilot-ADRs je mindestens
**zwei echte** typisierte Belege (`path`/`gate`/`test`, vom Owner im PR gelesen), **oder**
der Prüfer meldet auf dem Pilot über 30 Tage mehr als **10 %** Falsch-Positive (Findings,
die beim Nachsehen keinen Bruch zeigen, geteilt durch typisierte Zeilen).

**Dann:** `implementation_evidence` bleibt Prosa nach ADR-138 §2.4, die Pilotliste wird
gelöscht, `--gate` bleibt aus, keine Flotten-Ausweitung, kein Schema-Change. Begründung im
Voraus: wenn zehn ausgesuchte ADRs mit realen Belegen die Umstellung nicht tragen, tragen
280 sie erst recht nicht — und ein Vertrag, den niemand pflegt, ist die Prosa mit
Zusatzkosten.

**Exception-Budget:** einmalig 30 Tage bis **2026-12-31**, falls die Pilot-PRs auf
Owner-Klick warten (W3-Merges laut Regel 2026-09-16 nicht autonom). Datiert, nicht wiederholbar.

| Kriterium | Status | Beleg |
|---|---|---|
| Zeilenkonvention als Amendment in ADR-138 §2.4 eingetragen | offen | — |
| `adr_evidence_paths.py` kennt `gate`/`test`/`pr` + Zählung `typisiert / prosa` | offen | — |
| Pilotliste `docs/adr/.adr-evidence-pilot` mit 10 ADRs, `--gate` darauf aktiv | offen | — |
| ADR-174 und ADR-226: `_ci-python.yml`-Beleg repariert | offen | C11 |
| ≥ 8 von 10 Pilot-ADRs mit ≥ 2 echten typisierten Belegen bis 2026-11-30 | offen | Pilot-PRs |
| Falsch-Positiv-Quote auf dem Pilot ≤ 10 % über 30 Tage | offen | Job-Ausgabe |
| Umstellzeit je ADR gemessen (L12) | offen | Pilot-PR-Texte |

## Entscheidungen für den Owner

| # | Entscheidung | Empfehlung | Was sonst |
|---|---|---|---|
| D1 | Vertrag als **Zeilenkonvention im vorhandenen Feld** (kein Schema-Change) und Pilot mit 10 platform-ADRs starten | **ja** | A2: nur dev-hub#374 Schritt 0, kein Vertrag |
| D2 | **Kein Backfill-Mandat** für die 280 — Vertrag nur für Pilot, neue ADRs und „beim Anfassen"; Rest als Prosa-Quote sichtbar | **ja** | LLM-Entwurf mit Belegpflicht (#374 G2) — im Pilot ausdrücklich nicht |
| D3 | Fälligkeit aus `staleness_months` + `last_reviewed` statt neuem `review_by`; **Typ-Defaults** für ADRs ohne `staleness_months`: Infra/Deploy 6 Monate, Konvention/Governance 12 — Zuordnung über `domains` | **ja**, Defaults wie vorgeschlagen | fester Default 12 für alle (einfacher, stumpfer) |
| D4 | **Flotten-Schritt vertagen** bis Kill-Gate bestanden: Schema-Objekt (A1), Prüfer in jeder Repo-CI, dev-hub ruft den platform-Parser (G3) — das ist T3 und bekommt dann ein eigenes ADR | **vertagen** | sofort T3 — dann ist dieses Konzept falsch eingestuft und wird hochgestuft |

## Abgrenzung zu laufenden Vorgängen

| Vorgang | Gegenstand | Verhältnis |
|---|---|---|
| [dev-hub#374](https://github.com/achimdehnert/dev-hub/issues/374) | Detektor in drei Klassen, Schritt 0 Sofortmaßnahme, Regelbibliothek | Dieses Konzept ist dessen Schritt 5 (OOTB-1/3). Schritte 0–4 laufen dort, unabhängig |
| [#2962](https://github.com/achimdehnert/platform/issues/2962) | 14 accepted ADRs mit `implementation_status: none` brauchen je ein Urteil | Bleibt Einzelfall-Urteil; der Vertrag ändert daran nichts. Die 39 ADRs **ohne** das Feld (L4) sind dort nicht erfasst — Hinweis an #2962, kein neuer Vorgang |
| [ADR-138](../adr/ADR-138-implementation-tracking-standard.md) | Belegformat §2.4 | Amendment-Ziel dieses Konzepts |
| [ADR-059](../adr/ADR-059-adr-drift-detector.md) | Detektor, Kriterium 5 | Bleibt gültig; Kriterium 5 wird in #374 zur Form-Quote, der Vertrag liefert dem Detektor die Drift-Klasse `dead_evidence` |
| [platform#1289](https://github.com/achimdehnert/platform/issues/1289) / [#1318](https://github.com/achimdehnert/platform/pull/1318) | Anlass und Baseline von `adr_evidence_paths.py` | Der Prüfer, der hier erweitert wird; seine Promotion-Bedingung („saubere Baseline") wird auf die Pilotliste verengt |
