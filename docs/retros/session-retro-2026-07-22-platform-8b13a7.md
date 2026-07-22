---
retro_schema: 1
date: 2026-07-22
repo_scope: [platform]
session_id: 8b13a7
footprint: lean
findings_total: 5
findings_survived: 4
refuted_rate: 0.20
phase3_refuted: 0
pre_refuted: 1
scores:
  zielerreichung: 5
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [untested-tool-module-green-gate, workaround-without-tracking-anchor]
recurring_findings: [untested-tool-module-green-gate, workaround-without-tracking-anchor]
footprint_reduction_reason: "git-Footprint = 2 PRs / 1 Repo / kein Code-Deploy/Migration/ADR → lean. Die irreversiblen Mail-Löschungen (expunge) waren je explizit menschlich freigegeben ('papierkörbe leeren', 'a+b+c'); der Großteil der Session (Postfach-Ops) hinterlässt KEIN git-Artefakt → nicht fresh-agent-erdbar, als Hypothese geführt."
---

# Session-Retro 2026-07-22 — Postfach-Großaufräumen (3 Konten) + 2 mail_agent-Tool-PRs

> **Erdungs-Grenze (wichtig):** Der Großteil dieser Session waren **Postfach-Operationen**
> (ad@dehnert.team · achim.dehnert@hnu.de · achim.dehnert@iil.gmbh) — Löschen, Verschieben,
> Archivieren, Junk-Bereinigung. Diese hinterlassen **kein git-Artefakt**; ein frischer Richter
> (Regel 1) kann sie nicht artefakt-erden. Nur die 2 Tool-PRs sind git-geerdet. Mail-Op-Befunde
> sind daher **Hypothesen** (Transkript-Beleg), nicht SURVIVES. `lean`, Inline-Pass.

## 1. Executive Summary
- Alle User-Aufträge geliefert **und je unabhängig nachgezählt** (3 Postfächer strukturiert,
  Sent+INBOX-Archive nach Jahr, IIL-Junk security-aware bereinigt).
- **Kern-Befund (git-geerdet):** organize_mail.py `_matches` verschob auf Exchange **still 0** Mails
  und meldete trotzdem „OK: 11 verschoben" — der Move-Pfad hatte **null Testabdeckung**, der Bug kam
  durch den grünen Gate. Nur der unabhängige Nachzähl-Reflex fing es (#1305).
- **Muster (Transkript):** Massen-Mail-Ops liefern **still unvollständig** (github-Move „1503", 373
  blieben; Expunge-Timeout bei 30s) — nur Loop-until-zero + unabhängiger Re-Scan deckte es auf.
- Irreversible Löschungen (expunge ~674 ad@, ~1611 Sent, Ordner-Deletes) alle **explizit
  freigegeben** + vor/nach verifiziert → `over_act = 0`.
- #1337 als „wartet auf Review" berichtet, ist real **APPROVED + CLEAN** (mergebar).

## 2. Befund-Tabelle
| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `organize_mail._matches` gab Sequenz-Nrn an `UID MOVE` → auf Exchange 0 verschoben, Tool meldete „OK: N"; Move-Pfad ohne Test | fehlende Validierung / Werkzeug | hoch | SURVIVES | PR #1305 (`_matches` UID-Fix); test_organize_mail.py deckt nur Parsing/Trash/Decode | `untested-tool-module-green-gate` ×2 (mit f4a546) |
| 2 | Massen-Mail-Ops still unvollständig: github-Move meldete 1503, 373 blieben (Graph-Paginierung-während-Mutation); Sent-Expunge Timeout@30s partiell | Werkzeug / fehlende Validierung | mittel | SURVIVES (Hypothese, Transkript) | Bash-Outputs b178d8y6o (373 Nachzügler in 3 Pässen); Sent-Expunge 1611→331→75→0 | neu |
| 3 | PR #1337 +297/-91 für ~10-Zeilen-Change — `ruff format` reformatierte die ganze unformatierte Datei, mischt Kosmetik + Feature | Konventionstreue / Prozess | niedrig | SURVIVES | `gh pr view 1337 --json additions,deletions` = +297/-91 | neu |
| 4 | #1337 als „wartet auf 2.-Owner-Review" berichtet, real APPROVED+CLEAN | Kommunikation | niedrig | SURVIVES | `gh pr view 1337 reviewDecision=APPROVED mergeStateStatus=CLEAN` | `claim-before-cheapest-check`-Familie (Status ohne Re-Check) |
| 5 | Über-autonom bei irreversiblem Expunge? | verfrühte Festlegung | — | REFUTED | Jeder Expunge/Delete hatte explizites User-Wort („papierkörbe leeren", „a+b+c"); vor/nach verifiziert | over_act=0 |

## 3. Scorecard (Anker aus Befunden)
| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 5 | Alle Aufträge geliefert + je nachgezählt (98/152/25509-Reconciles stimmen exakt) |
| architektur_design | 4 | `--config`/`--source`-Erweiterungen minimal + rückwärtskompatibel; Jahres-Archiv-Struktur konsistent — kleine Mängel (#3) |
| code_konventionstreue | 3 | Noisy #1337-Diff (#3); `_decode unknown-8bit` nicht gefixt, nur umgangen |
| risiko_debt | 3 | Irreversible Deletes sicher + gegated + verifiziert; ABER Move-Pfad auch nach #1305 ohne Test (#1), `_decode`-Bug aufgeschoben, #1337 offen |
| prozess_effizienz | 3 | Viele Mid-Flight-Überraschungen → Rework: 4-Pass-github, 3-Pass-Expunge, 2× Timeout-Retry, LIST-Parsing-Bugs |
| entscheidungsqualitaet | 4 | Verify-first · Trash-vor-Expunge · Pilot-vor-Rollout · kein Auto-cron ohne Gate — stark; kleiner Abzug: initial „OK" vertraut (#1) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert)
| Ist (beobachtet, Beleg) | Soll | eliminiert |
|---|---|---|
| „OK: 11 verschoben" vertraut; 0-Move nur per unabhängiger Nachzählung entdeckt (#1305) | Tool-Erfolgsmeldung NIE als Wahrheit nehmen → nach jeder Massen-Mail-Mutation Zielordner+Quelle unabhängig re-zählen (war Reflex, jetzt Regel); Move-Pfad-Unit-Test in mail_agent | #1 |
| github-Move meldete 1503, 373 blieben; Expunge Timeout@30s (Bash b178d8y6o) | Massen-Ops immer Loop-until-zero + Re-Scan; Mutations-Timeout von Beginn an 180s, nicht 30s | #2 |
| #1337 +297/-91 durch Ganzdatei-`ruff format` | Bei unformatierter Zieldatei: Format als **separater** Prep-Commit, dann bleibt der Feature-Diff klein | #3 |
| „#1337 wartet auf Review" trotz APPROVED+CLEAN | Vor Status-Aussage `gh pr view --json reviewDecision,mergeStateStatus` neu ziehen | #4 |

## 5. Längsschnitt (retro_kpis.py, PFLICHT)
`python3 tools/retro_kpis.py` gelaufen (46 Reports). Relevante Treffer:
- **`untested-tool-module-green-gate`**: bisher ×1 [f4a546] → mit Befund #1 **×2 ⇒ GATE-PFLICHT**.
  Konkreter Gate: mail_agent-Tools brauchen **Move-/Mutations-Pfad-Testabdeckung** (nicht nur
  Parser-Tests), sonst rutscht ein UID/MOVE-Bug erneut durch den grünen Gate.
- **`workaround-without-tracking-anchor`** (bereits ≥2, gate-pflichtig): der `_decode`-`unknown-8bit`-
  Bug wurde 2× inline umgangen, nur in Memory/PR-Body notiert, **kein GitHub-Issue** → Tracking-Issue fällig.
- `refuted_rate` 0.20: unterste Bandkante — bei `lean` gibt es **keinen** Phase-3-Skeptiker
  (0 Subagenten), daher ist das hier kein Skill-KPI-Signal, sondern strukturell (1 Inline-pre_refuted/5).

## 5b. Autonomie-Kalibrierung
- `over_act = 0` — jede irreversible Aktion (expunge, Ordner-Delete) hatte explizites User-Wort.
- `over_ask = 0` — Pilot-vor-Rollout-Rückfragen waren bei irreversiblen Massen-Ops angemessen, nicht Über-Fragen.
- Keine Charter-Schärfung nötig (kein ≥2-Muster in eine Richtung).

## 6. Verankerung (Vorschläge — Mensch entscheidet)
**memory_candidates:**
- `feedback_tool_success_message_not_ground_truth` (type feedback): „Erfolgsmeldung eines Mail-/CI-
  Tools (`OK: N verschoben`, `run success`) ist KEIN Beleg — nach jeder Massen-Mutation Ziel+Quelle
  unabhängig re-zählen. Realfall 2026-07-22: organize_mail meldete OK bei 0 Moves (seq-vs-UID, #1305);
  github-Move meldete 1503 bei 373 Rest. Familie [[feedback_run_conclusion_not_tool_health]] /
  [[feedback_deploy_green_not_change_live]]." (Bereits teils in feedback_mailbox_archiving_convention.)

**adr_candidates:** keine (reine Ergänzung nach Muster, kein Architektur-Entscheid).

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf)

### 🔵 Ich sofort (deterministisch, reversibel)
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | #1337 mergen | platform | [#1337](https://github.com/achimdehnert/platform/pull/1337) | 🔵 ready | approved+clean → squash-merge |
| 2 | `_decode unknown-8bit` Tracking-Issue | platform | file://—noch keins | 🔵 ready | gh issue create (Bug + Fix-Skizze) |

### 🟢 Dein Zug (Entscheidung/Gate)
| # | Item | Repo | Status | Next Step |
|---|---|---|---|---|
| 3 | Gate: mail_agent Move-Pfad-Test-Pflicht (untested-tool-module ×2) | platform | 🟢 offen | Test + CI-Gate-PR autorisieren |
| 4 | Safe-Sender github/betterstack in OWA (iil.gmbh) | — | 🟢 offen | nur via Outlook/OWA (kein Graph) |
| 5 | `Archivieren`-Leerordner (HNU) via OWA löschen | — | 🟢 offen | Exchange verweigert IMAP-Delete |

## 8. Nicht verifiziert (Restlücken)
- **Mail-Op-Endzustände** (INBOX/Archiv/Junk-Zahlen) sind nur **transkript**-geerdet (Bash-Outputs
  dieser Session), nicht von einem fremden Richter re-geprüft. Billigster Check: die jeweiligen
  `--scan-senders`/IMAP-Counts erneut ziehen.
- **Befund #2 (Paginierungs-/Timeout-Unvollständigkeit)** ist Hypothese aus Tool-Verhalten, nicht
  aus einem Repro-Test. Billigster Check: instrumentierter Re-Run mit Vorher/Nachher-Count.
- **Github-Ordner-Count 1784 vs. erwartet ~1975** (iil.gmbh) — Graph `totalItemCount` hinkt nach
  Massen-Move; maßgeblich war „Junk github=0". Billigster Check: Count nach Sync-Settle erneut.
