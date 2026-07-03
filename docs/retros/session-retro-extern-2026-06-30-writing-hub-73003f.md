# Externer Methoden-Review-Auftrag — Session-Retro 2026-06-30 (writing-hub)

_Du bist ein anbieter-fremder Falsifikator. Du hast **KEIN Repo-Zugriff** (kein gh/git). Kritisiere **Methode / Struktur / Blindflecken / Score-Logik / Soll-Ablauf** dieses Retros — behaupte **keine** Evidenz-Fakten (die prüft die Pipeline mit gh/git). Advocatus Diabolus + Out-of-the-Box: was hat dieser Retro übersehen oder falsch bewertet?_

## Die 4 Eisernen Regeln, gegen die dieser Retro lief
1. **Richter ≠ Angeklagter:** jeder Befund von einem frischen Subagenten (nur Artefakte, nicht die Session-Erzählung). Hier: 1 Collector + 3 Finder + 3 Skeptiker, je frischer Kontext.
2. **Evidenz vor Behauptung:** jeder Befund = harter Artefakt-Beleg (PR#/Datei:Zeile/CI-Run).
3. **Falsifikation:** jeder Befund binär SURVIVES/REFUTED durch einen unabhängigen Skeptiker, der den Beleg neu zieht.
4. **Geschlossener Loop:** Lessons als kopierfertige Memory-/Gate-Vorschläge.

## Output-Schema (zur Orientierung)
Frontmatter-KPIs (findings_total/survived, refuted_rate, 6 Integer-Scores), Befund-Tabelle (frozen columns), Scorecard, Soll-Ablauf (|Soll|==|Survivors|), Längsschnitt (retro_kpis.py ≥2 ⇒ Gate), Verankerung, Action-Board, Nicht-verifiziert.

## Kontext der Session (1 Absatz)
Eine Coding-Agent-Session schloss Epic #11 (Adversarial-Review F13–F22) in writing-hub ab: F16 (Revision-DAG, DB-Migration 0011 mit Triggern) + F18 (Multi-Owner-Authz, Migration 0012) implementiert+deployt; ADR-182/183 akzeptiert; F22→neues platform-ADR-259. 10 PRs gemergt, 6 Prod-Deploys, 2 DB-Migrationen, 2 ADRs mit externer LLM-Zweitmeinung. Footprint: **deep**.

## Ergebnis dieses Retros (16 Befunde, ALLE SURVIVED, refuted_rate 0.0)
**Höchste Severity:**
- **A-F1 (hoch):** ADR-259 — die Anti-Kollisions-ADR (repo-scoped IDs) — kollidiert selbst mit einem OFFENEN platform-PR #708, der dieselbe Nummer 259 beansprucht. Der Agent prüfte nur gemergte ADRs (`ls`), nicht den offenen PR-Queue.
- **A-F2 (hoch):** ADR-182 (erstes Authz-/Security-Modell) wurde same-session akzeptiert+deployt **ohne** externen Review; der Agent behauptete fälschlich „each ADR went through 2 external reviews".
- **A-F3 (hoch):** ADR-183 Proposed→Accepted→Prod in 3h10min, 1 Review-Runde.
- **B-F1 (mittel):** Migration 0011 reaktivierte `session_replication_role=replica`, das die Codebase (db.py §B15) als SUPERUSER-pflichtig explizit verworfen hatte.
- **B-F3/B-F4 (mittel):** Sole-Owner-Guard-Signal tot während Deprecation-Karenz; GDPR-Purge filtert auf die zu-droppende `owner`-Spalte.
- Plus 10 weitere (Test-Naming-Drift ×20, toter Code, Authz-Matrix-Lücke, Deploy-Churn, ADR-Amendment-nach-Accept, Epic nicht geschlossen).

**Scores:** zielerreichung 4 · architektur_design 3 · code_konventionstreue 3 · risiko_debt 2 · prozess_effizienz 3 · entscheidungsqualitaet 3.

**Längsschnitt:** 3 Survivors sind Wiederholungen bereits gate-pflichtiger Slugs (`lint-failure-no-local-gate`, `claim-before-cheapest-check`, `planned-phase-no-issue`).

## Deine Aufgabe (Methoden-Kritik, keine Evidenz-Behauptung)
1. **Blindflecken:** Welche Dimension/Befund-Klasse hat dieser Retro **strukturell** nicht abgedeckt? (z. B. Sicherheits-Modell-Korrektheit über Coverage hinaus? Performance der neuen Trigger/Migrationen unter Last? Daten-Migrations-Rollback-Realismus?)
2. **Score-Logik:** Ist „zielerreichung 4 trotz risiko_debt 2 + Security-ADR-ohne-Review" konsistent? Sollte A-F2 (Security-ohne-Review) die zielerreichung stärker drücken? Ist die 16-Survivors-bei-0-Refuted-Konstellation ein Zeichen für zu-lasche Finder-Falsifikation ODER für eine ehrlich problembehaftete Session — und woran würde man das **methodisch** unterscheiden?
3. **Soll-Ablauf:** Sind die 16 Soll-Schritte echte Prozess-Fixes oder teils Plattitüden? Welcher ist der schwächste?
4. **Out-of-the-Box:** Ein Ansatz, den der Retro gar nicht erwägt (anderes Framing der ganzen Session — z. B. „war die Same-Session-Geschwindigkeit selbst das Kernproblem, das alle Einzelbefunde erzeugt?").
5. **refuted_rate 0.0:** liegt im „theater"-Band (<0.2). Ist das hier ein KPI-Artefakt (scharfe Finder + reale Schuld) oder ein echtes Methoden-Signal (Skeptiker zu nachsichtig)? Wie würde man es **ohne** Session-Urteil entscheiden?

Antworte als Prosa; nummeriere deine Kernpunkte. Keine gh/git-Fakten-Behauptungen.
