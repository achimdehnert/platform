---
retro_schema: 1
date: 2026-07-08
repo_scope: [platform]
session_id: 31348f
footprint: full
findings_total: 7
findings_survived: 6
refuted_rate: 0.14
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [parallel-session-pr-collision, planned-phase-no-issue]
recurring_findings: [parallel-session-pr-collision, planned-phase-no-issue]
new_findings: [settings-model-default-fragile-anchor, veto-needs-durable-artifact]
over_ask: 0
over_act: 0
footprint_reduction_reason: "kein Prod-Deploy/keine Migration durch diese Session; full statt deep, weil 1 Repo und alle Aktionen reversibel/PR-gegated"
---

# Session-Retro 2026-07-08 — platform (31348f)

> Methode: Richter≠Angeklagter. 1 Collector (haiku) + 3 Finder (sonnet, je Dimension) +
> 2 Skeptiker (sonnet, binär). Alle Befunde artefakt-geerdet; Survivors sind skeptiker-verifiziert.

## 1. Executive Summary
- Session lieferte einen vollen `/repo-optimize` runB-Lauf (8 Finder + 6 Skeptiker) + 6 an Sonnet delegierte Umsetzungs-PRs, jede mit **unabhängiger Orchestrator-Abnahme** — methodisch die Stärke der Session (2 eigene Prämissen dabei selbst korrigiert).
- **Kern-Schwäche: durable Entscheidungs-Spur.** Zwei Survivors (SI-13, SI-8b) sind beide „Entscheidung getroffen, aber nicht in ein auffindbares Artefakt zurückgeschrieben" — und beide mappen auf **bereits gate-pflichtige** Längsschnitt-Slugs (`parallel-session-pr-collision`, `planned-phase-no-issue` je ≥2).
- Eine eigene frühere Aussage relativiert: **Option A („Default-Modell = Sonnet in settings.json") ist kein stabiler Anker** — jedes `/model` überschreibt das Feld (Skeptiker-bestätigt).
- 1 Finder-Befund hart refuted (EF-1 ttz-hub-Redaktion: kein Leak, 67 Fundstellen im Repo, Repo privat).
- Konventions-/Worktree-/Commit-Disziplin durchgängig sauber (EF-8/EF-9/PK-7); 1 Rework von Ruff vor Merge gefangen (PK-6).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| SI-13 | #1012 (delete-repo-Vorfrage) auf User-Anweisung **gelöscht** statt wontfix+close → keine durable Entscheidungs-Spur; Parallel-Session baute in PR #1013 genau den vetoed Skill | Prozesslücke | hoch | **SURVIVES** | `gh api issues/1012`→410; PR #1013 „Closes #1012"; kein Ersatz-Artefakt (grep memory leer) | 🔴 `parallel-session-pr-collision` ≥2 (Gate-Pflicht) |
| SI-8b | Owner-Freigabe „9 (b)" für #999 nie ins Issue zurückgeschrieben; #999 verlangt „Entscheid a/b/c dokumentiert (Kommentar hier)" selbst | Kommunikation | mittel | **SURVIVES** | `gh issue view 999`→`comments:[]`, OPEN; 3/3 Akzeptanz-Checkboxen offen | 🔴 `planned-phase-no-issue` ≥2 (Gate-Pflicht) |
| SI-3 | Frühere Aussage „A verankert T-1" über-behauptet: `settings.json:model` ist volatiler Startwert, kein Anker (jedes `/model` überschreibt) | verfrühte Festlegung | mittel | **SURVIVES** (reframed) | `git -C ~/.claude`: nur 1 Commit (06-01, Wert `opus`); Live `opus[1m]`; Root-Cause „nie gegrept" **REFUTED** (Volatilität plausibler) | 🟡 `settings-model-default-fragile-anchor` neu ×1 |
| PK-2 | `sync-drift-meter.yml` von #1001 (+timeout) UND #1009 (+Pfad-Fix) geändert; disjunkte Hunks, aber **Probe-Merge nicht getestet** | fehlende Validierung | niedrig-mittel | **SURVIVES** (geerdet, nicht skeptiker-geprüft) | `gh pr diff 1001/1009` disjunkt; kein Draft-Merge-Lauf | ×1 |
| EF-10 | PR #1007 (1655 Z. > Guardian-Limit 600, „G-004"-Warnung) ohne Split/Begründung in der Abnahme adressiert | Prozesslücke | niedrig | **SURVIVES** | Guardian-Kommentar „G-004 … Auto-Warning (Gate 1)"; Abnahme-Kommentar erwähnt es nicht; Gate advisory-only | ×1 |
| EF-3 | `git mv` überschrieb ältere gleichnamige Archiv-Datei (386 vs 552 Z.) | Werkzeug | niedrig | **SURVIVES** (geerdet) | kein Datenverlust (`git log --all` beide abrufbar); unterscheidbarer Name wäre sauberer | ×1 |
| EF-1 | Gov-Redaktion #992 ließ Repo-Name „ttz-hub" stehen | unklares Ziel | (mittel→) | **REFUTED** | 67 Repo-Fundstellen inkl. accepted ADR-189 (offener Kundenname); Repo privat; Gov-Regel = Detail/PII, nicht Namens-Anonymität; Finder-Zahl „6×" falsch (real 9/11) | — |

## 3. Scorecard (1–5, an Befunden verankert)
- **zielerreichung 4** — alle 12 Anfragen artefaktisch erfüllt (SI-1/2/5/6/7/8a/10/12); kleine Mängel: #999-Rückschrieb (SI-8b), A-Anker über-behauptet (SI-3).
- **architektur_design 4** — Delegations-Muster (Fable orchestriert → Sonnet-Delegate → unabhängige Abnahme) trug; Policy-Split #1002 sauber begründet (N=1 offen benannt, EF-6).
- **code_konventionstreue 4** — Commits schema-konform, keine Backticks (EF-8), ADR-233-Worktrees durchgängig (EF-9), `test_should_*` eingehalten; einziger Makel: EF-10 Soft-Gate unadressiert.
- **risiko_debt 4** — Session **reduzierte** Debt netto (Guards+Tests+Gov-Redaktion); neue Rest-Debt klein + benannt (Fleet-Ø 2.79, hier besser).
- **prozess_effizienz 3** — hoher Durchsatz (6 parallele Delegate, 1 Ruff-Rework vor Merge), aber 2 Doku-Spur-Lücken (SI-8b/SI-13) + 1 ungetesteter Cross-PR-Overlap (PK-2), alle auf gate-pflichtige Wiederholmuster mappend.
- **entscheidungsqualitaet 4** — #999 korrekt gestoppt statt autonom Ruleset geändert (EF-7); 0-Consumer-Prämisse selbst korrigiert (EF-5); „Ref" statt „Closes" (EF-4); Minus: #1012-Löschung ohne durables Nein.

## 4. Soll-Ablauf (Ist → Soll → eliminiert)

| Ist (beobachtet) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| #1012 auf „issue löschen" gelöscht → Spur weg, Parallel-Session baute #1013 | Bei „delete issue"-Anweisung 1× spiegeln: „Löschen tilgt die Entscheidungsspur — wontfix+close ODER 1-Zeilen-Memory als durables Nein?"; mind. 1 durables Artefakt behalten | #SI-13 |
| „9 (b)"-Freigabe für #999 nur im Chat | Jede erhaltene Owner-Entscheidung **sofort** als Issue-Kommentar zurückschreiben (Zielartefakt verlangt es explizit) | #SI-8b |
| „A verankert T-1" behauptet, settings.json=sonnet gesetzt | Option A als **Startwert, kein Anker** framen + Volatilität (`/model` überschreibt) mitnennen; robusten Anker = Delegations-Reflex (B) betonen | #SI-3 |
| #1001+#1009 fassen dieselbe Datei an, kein Probe-Merge | Vor Parallel-Dispatch Cross-PR-Datei-Overlap-Scan; bei Treffer Merge-Reihenfolge im PR-Body notieren ODER 1 Draft-Merge testen | #PK-2 |
| #1007 1655 Z. > 600, Guardian-Warnung unadressiert | Soft-Gate-Warnung in der Abnahme explizit quittieren (split ODER begründet „bewusst nicht") | #EF-10 |
| `git mv` überschrieb Archiv-Datei blind | Vor `git mv` Ziel `test -e` prüfen; bei Kollision unterscheidbaren Namen (`-legacy-<datum>`) | #EF-3 |

Invariante erfüllt: 6 Soll-Schritte == 6 Survivors.

## 5. Längsschnitt (retro_kpis.py, 19 Retros)
- **10 Slugs ≥2 ⇒ Gate-Pflicht**, davon **2 direkt von dieser Session belegt** (exakte Zähler aus retro_kpis.py-Output): `planned-phase-no-issue` **×3** (`73003f, a50bc6, 0b46ee`) — SI-8b ist Vorkommen 4; `parallel-session-pr-collision` **×2** (`17c08c, 44240f`) — SI-13/PK-4 ist Vorkommen 3. Beide sind damit **nicht** „noch ein Befund", sondern erneute Wiederholung eines überfälligen Gates.
- `refuted_rate` 0.14 — Trend-Band der Vor-Retros: 0.20/0.40/0.12/0.29/0.00/0.33/0.38/0.50; 0.14 liegt innerhalb (Vergleichswert 0.12 existiert), keine 3× konsekutiv <0.2 oder >0.8. Rein numerische Band-Einordnung; keine Aussage über einzelne Verdikte.
- `risiko_debt`-Fleet-Ø 2.79 bleibt die schwächste Dimension fleet-weit — diese Session lag darüber (4).

## 5b. Autonomie-Kalibrierung
- `over_ask` = 0: #999 (Security-Config-Gate) + #1012-Löschung (irreversibel) + PR #1002-Merge (2. Owner-Review-Pflicht) waren **echte** Gates — korrekt vorgelegt, kein Über-Fragen.
- `over_act` = 0: keine autonome Prod/Publish/Merge-auto-deploy/3.-Repo/irreversible Aktion ohne Freigabe. Die 6 Delegate-PRs blieben OPEN (kein Self-Merge). Charter gehalten.

## 6. Verankerung (Mensch entscheidet)

**memory_candidates:**
1. `feedback_settings_model_default_fragile_anchor` (neu): `~/.claude/settings.json:model` ist volatiler Startwert, kein Anker — jedes `/model` überschreibt ihn session-los. „Default auf X setzen" nie als durablen Mechanismus verkaufen; robuster T-1-Hebel ist per-Subagent-Delegation (`Agent(model:…)`), nicht der Default-Wert.
2. `feedback_veto_needs_durable_artifact` (neu, drift): Ein „Nein/Wontfix" durch **Löschen** eines Issues tilgt die Entscheidungsspur; Parallel-/Folge-Sessions kennen das Veto nicht (Realfall #1012-gelöscht → #1013 baute es). Bei „delete issue" spiegeln + mind. 1 durables Nein-Artefakt (wontfix-close/Memory). Verwandt [[feedback_shared_worktree_multisession_git_collision]].

**adr_candidates:** keine — beide Survivors sind Prozess/Gate-Themen (Hook/Skill), keine Architektur-Entscheidung (adr-threshold).

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf abgeleitet)

🟢 Dein Zug
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | #999-Freigabe „(b)" als Kommentar nachtragen (SI-8b) — deine Entscheidung, mein Rückschrieb | platform | [#999](https://github.com/achimdehnert/platform/issues/999) | 🟢 offen | du: „schreib (b) rein" → ich kommentiere |
| 2 | Gate `parallel-session-pr-collision` (≥2, überfällig) bauen — Cross-Session-Claim/Lock-Mechanik | platform | Gate-PR-Kandidat | 🟢 offen | du: Priorität freigeben |
| 3 | Gate `planned-phase-no-issue` (≥2, überfällig) — Entscheid-im-Chat-nicht-im-Artefakt | platform | Gate-PR-Kandidat | 🟢 offen | du: Priorität freigeben |

🔵 Ich sofort (gate-frei, auf Zuruf)
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 4 | 2 memory_candidates verankern (settings-anchor + veto-durable-artifact) | lokal | — | 🔵 ready | ich: nach deinem OK schreiben |
| 5 | PK-2: Merge-Reihenfolge #1001/#1009 im jeweiligen PR-Body notieren | platform | [#1001](https://github.com/achimdehnert/platform/pull/1001) · [#1009](https://github.com/achimdehnert/platform/pull/1009) | 🔵 ready | ich: 1 Kommentar je PR |

## 8. Nicht verifiziert (Restlücken)
- **SI-13 „Veto"-Framing:** #1012-Text ist nach Löschung nicht rekonstruierbar (API 410, kein Cache) → ob es ein Veto oder eine offene a/b/c-Frage war, ist **nicht** beweisbar. Verifiziert ist nur: gelöscht + kein Ersatz-Artefakt. Billigster Check existiert nicht mehr (Issue weg).
- **SI-3 „sonnet je gesetzt?":** kein durables Artefakt (settings.json-Commit von 06-01 zeigt `opus`); die In-Session-`jq`-Verifikation ist Session-Log, kein unabhängiger Beleg → als Hypothese geführt, nicht als SURVIVES-Fakt.
- **PK-2 Merge-Sauberkeit:** disjunkte Hunks belegt, aber echter 3-Way-Merge nicht ausgeführt → „mergt sauber" bleibt Annahme bis zum ersten realen Merge.
- **KONZ-014 / PR #1011 + 2 externe Reviews:** bewusst außerhalb Retro-Scope (Parallel-Session); nicht bewertet.

---
Fußzeile: HEAD-Basis `3b726a0` · 1 Collector (haiku) + 3 Finder + 2 Skeptiker (sonnet) · Falsifikation 6 SURVIVES / 1 REFUTED · Coverage: Einzel-Lauf, nicht erschöpfend.
