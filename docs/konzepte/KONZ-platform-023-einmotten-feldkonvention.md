---
concept_id: KONZ-platform-023
title: "Einmotten als Feld-Konvention — pausierte Themen mit Invalidatoren-Register und Wächter-Wiring statt neuem Skill"
pipeline_status: idea
tier: T1
owner: "Achim Dehnert"
spec_refs: []   # Prozess-/Dokumentations-Konvention ohne ADR-211-Spec-Bezug; SSoT-Ziel ist dieses KONZ-Template selbst
adr_threshold: "kein ADR — Ergänzung des bestehenden KONZ-Musters um optionale Felder, ein Repo, reversibel, keine neue Abhängigkeit; würde die Konvention CI-erzwungen oder org-weit verpflichtend, dann eigene Entscheidung (T2-Eskalation)"
review_by: "2026-10-31"
kill_criteria: "Bis 2026-10-31: mindestens 2 reale Nutzungen (Einmott-Register geschrieben ODER Wächter-Fund auf veraltet_wenn-Prädikat) mit mindestens einem Differenz-Fund — das Register fängt etwas, das die stehenden Regeln (fetch-first, cheapest-check, git-log-vor-Verlass) nicht ohnehin gefangen hätten. Sonst sunset: Felder deprecaten, bestehende Artefakte bleiben lesbar, kein Migrationszwang."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: E1, source_path: "~/shared/review-skill-einmotten-adaption-2026-07-17.md (AD-1..8, OOTB-1..4, Backtest-Ergebnis)", commit_or_pr: "Review + Blind-Backtest 2026-07-17", opened_in_session: true}
  - {claim_id: E2, source_path: "Quell-Skill: meilenstein-einmotten/SKILL.md (Ilja Lerch, per Mail 2026-07-17, 274 Zeilen)", commit_or_pr: "Mail-Anhang, reziprokes Audit-Feedback versendet 2026-07-17", opened_in_session: true}
  - {claim_id: E3, source_path: "Backtest-Fall: ADR-234 §11.2 Amendment A3 accepted-nie-umgesetzt (Memory feedback_accepted_adr_amendment_needs_execution_pr, Drift-Episode 2026-07-08)", commit_or_pr: "platform#994 (historische Auflösung)", opened_in_session: true}
created: "2026-07-17"
---

# KONZ-platform-023 — Einmotten als Feld-Konvention

> Herkunft: Skill „meilenstein-einmotten" von Ilja Lerch (per Mail, 2026-07-17), tief
> auditiert (Advocatus Diaboli + Out-of-the-Box, siehe E1). Owner-Entscheid 2026-07-17:
> Adaption **nicht** als Skill-Import, sondern als Feld-Konvention auf bestehenden
> Artefakten. **Tier T1** — ein Repo (platform), optionale Felder, reversibel; Rückbau-
> Kosten ≈ 0 by design (kein Skill, keine Distribution, kein CI-Gate im Pilot).

## Kernthese

Ein Thema, das Monate pausiert, scheitert bei Wiederaufnahme still an verschobener
Grundlage (Entscheid nie umgesetzt, Referenzen gewandert, Prämisse gekippt). Statt
eines neuen 274-Zeilen-Prozess-Skills bekommt das bestehende KONZ-Template **vier
optionale Felder** — `lebenszyklus`, `wiederaufnahme_trigger`, `veraltet_wenn`
(Invalidatoren-Register), `resume_acceptance_test` — und die maschinenprüfbaren
Prädikate laufen periodisch im bestehenden Kill-Gate-Wächter: aktive Drift-Detektion
statt Check-erst-bei-Wiederaufnahme. Übernommen wird nur der maschinenprüfbare Kern
des Quell-Skills; die Operator-Rituale (Generierungs-Zwang, Blind-Test-Gebot) entfallen
bewusst, weil sie in agentischen Sessions leerlaufen (E1, Befund AD-2).

## Annahmen-/Entscheidungs-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | Ein blind (ohne Vorfall-Wissen) geschriebenes Register fängt reale Drift-Vorfälle | Annahme | Blind-Backtest am Fall ADR-234-A3: 3/7 Prädikate hätten gefeuert, inkl. exaktem Fehlermodus + korrektem Wiedereinstieg (E1 §Backtest). Caveat: Briefing enthielt den historischen Hinweis „proposed bis PR-Merge" | bestätigt (1 Fall) |
| A2 | Mehrwert existiert nur, wo Standing Rules blind sind (fachliche Prämissen, Außenwelt, Entscheidungs-Wiederöffner) | Annahme | Differenz-Messung pro Nutzung (Ledger-Zeile: hätte Standing Rule denselben Fund geliefert?) — Kill-Kriterium | offen |
| A3 | Kill-Gate-Wächter (Cloud-Routine) kann Prädikat-Checks tragen | Annahme | Vor Wiring live verifizieren — Memory-Stand, kein Live-Beleg | offen |
| E-1 | Kein neuer Skill, keine Distribution | Entscheid | Skill-Sprawl: usage_sweep mit 37 Rückbau-Kandidaten; Fork von Iljas Skill = Regel-Kopie-Drift-Muster (E1, AD-5) | ratifiziert 2026-07-17 |
| E-2 | Präzedenz bei eingemotteten Themen: KONZ-Artefakt gewinnt; Memory-/Handover-Zeile degradiert zum Sperr-Verweis | Entscheid | lügender-Index-Muster (E1, AD-6) | ratifiziert 2026-07-17 |
| E-3 | Kein Sealed-Tag, keine pv-fact-Marker im Pilot | Entscheid | Ceremony erst nach bewährtem Muster; Rückbau-Kosten klein halten | ratifiziert 2026-07-17 |

## Feld-Konvention (das eigentliche Artefakt)

Optionale Frontmatter-/Abschnitts-Felder für KONZ-Dokumente pausierter Programme:

```yaml
lebenszyklus: eingemottet          # eingemottet | ausgemottet (fehlt = aktiv)
eingefroren_am: <JJJJ-MM-TT>
wiederaufnahme_trigger: "<ereignisbasiert: 'bevor du an X arbeitest' / 'wenn Y eintritt'>"
coverage_claim: non_exhaustive     # immer; Register ist Liste BEKANNTER Verwundbarkeiten
```

Dazu im Dokument ein Abschnitt `## Invalidatoren (veraltet_wenn)` mit 3–8 Prädikaten
nach dem Schema des Quell-Skills (id, locus, annahme, veraltet_wenn, pruefung
maschine|mensch, baseline, impact, bei_rot; genau eines als `strongest`) und ein
Abschnitt `## Wiederaufnahme-Akzeptanztest` (1 Ende-zu-Ende-Prozedur, ursachenunabhängig).

Sprachregeln aus dem Quell-Skill gelten: positivstes Prüfergebnis heißt
`no_known_break_found`; `unknown` ist nie `pass`.

## Umsetzungsschritte

1. **Dieses KONZ mergen** (Konvention dokumentiert). ← dieser PR
2. **Erste Forward-Anwendung** auf 1 real pausiertes Programm (Kandidaten:
   authentik-OIDC-Rollout, ADR-272 P2/P3, KONZ-018-Reste) — Register schreiben,
   Sperr-Verweis in Memory-Zeile setzen.
3. **Wächter-Wiring prüfen** (A3 verifizieren): Kill-Gate-Wächter führt die
   maschine-Prädikate eingemotteter KONZ periodisch aus; Fund → Issue.
4. **Pro Nutzung eine Ledger-Zeile** hier ins Dokument (Datum, was feuerte,
   Standing-Rule-Vergleich, Zeitkosten).
5. **Review gegen Kill-Kriterium** spätestens 2026-10-31.

## Nutzungs-Ledger

| Datum | Ereignis | Fund | Hätte Standing Rule gereicht? | Zeitkosten |
|---|---|---|---|---|
| 2026-07-17 | Blind-Backtest ADR-234-A3 (retrospektiv) | 3/7 Prädikate ROT auf realen Vorfall | Nein — Regel `git log vor Verlass` entstand erst AUS dem Vorfall | ~10 Min (Subagent) |

## Bewusste Auslassungen (Rückbau-freundlich)

- Kein Sealed-Tag/Commit-Zyklus, keine pv-fact-Marker, kein Warm-Log — erst bei
  bewährtem Muster und echtem Bedarf (dann Amendment hier, kein neues Konzept).
- Keine Skill-Datei, keine Verteilung in andere Repos — SSoT ist dieses Dokument.
- Operator-Rituale des Quell-Skills (Delta-Kernsätze selbst schreiben, Blind-Lesen)
  sind NICHT Teil der Konvention; wer sie will, macht sie freiwillig.
