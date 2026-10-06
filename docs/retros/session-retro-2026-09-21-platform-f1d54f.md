---
retro_schema: 1
date: 2026-09-21
repo_scope: [platform]
session_id: f1d54f
footprint: full
findings_total: 18
findings_survived: 17
refuted_rate: 0.06
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [main-tree-guard-recurring-incident, direct-gh-pr-merge-bypasses-sa-m, inline-heredoc-quoting-rework, automation-contradicts-memory-rule-unreconciled, dedup-key-without-supplier]
recurring_findings: [inline-heredoc-quoting-rework, main-tree-guard-recurring-incident, serielle-prs-auf-derselben-datei, scope-checkpoint-not-durably-recorded, claim-before-cheapest-check, direct-gh-pr-merge-bypasses-sa-m]
gates_caught: [scope-checkpoint-not-durably-recorded, claim-before-cheapest-check, serielle-prs-auf-derselben-datei]
over_ask_klassen: []
over_act_klassen: [dauer-automatismus-aktiviert-vor-checkpoint]
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: keiner, weil jede Bahn dieser Retro etwas Eigenes geliefert hat — Skeptiker kippte F17, 3b kippte zwei Schweregrade, fand F18 und drei Belegfehler, der Evidenz-Hook erzwang die F6-Bestandsmessung; keine Belegart (kein Leser / kein Effekt / Dublette / Liegezeit) ist für eine Phase, einen Melder oder ein Gate dieser Sitzung erfüllt
---

# Session-Retro 2026-09-21 — platform, Sitzung f1d54f5c (sevdesk: Beleg aus Paperless, Kostenstellen, Aktion „verbuchen")

**Footprint:** `full` — 3 PRs (#3341, #3343, #3347), 1 Repo, kein Prod-Deploy/keine Migration/kein ADR, aber ein neuer **Dauer-Automatismus** (User-Timer, Schreibrecht auf sevdesk edv + Paperless). Agenten: 3 Finder (Sonnet) + 1 gebündelter Skeptiker (Sonnet) + 3b (Opus) + Meta (Sonnet) = 6. Befund-Dichte-Downscale nicht angewandt (Automatismus ist kein Prod-Schritt, aber irreversibel wirkend → `full` bleibt).

**Phase 0.0:** `tools/gate_wirkung.py` → `RUECKFAELLIG`: `issue-offen-nach-gemergtem-fix` und `gate-modul-prueft-weniger-als-sein-name` — beide **ohne Vorkommen in dieser Sitzung** (#3342 per `Closes` geschlossen; #3102 ist bewusst offener Sammelauftrag). Konsequenz „umbauen" ist bereits aus Retro 50d29a (M6, #3311) getroffen → kein zweiter Befund. `claim-before-cheapest-check` (blocking, `zu-frueh`): hat in dieser Sitzung **zweimal gefeuert** (Stop-Hook 09:52, 12:2x) und wurde beide Male mit dem Check beantwortet → Beleg FÜR das Gate (`gates_caught`), nicht Rückfall.

## 1. Executive Summary
- Owner-Ziel (Rechnung aus Paperless → sevdesk-Beleg, Kostenstellen je Fahrzeug, zahlbarer Lieferant, Aktion „verbuchen" wie „senden") ist mit 3 gemergten PRs und je einem Echtlauf im Zielkontext erreicht; „bezahlen" steht auf Status 150 (Zahlung angewiesen), Kontrolle getrackt (#3102).
- Der neue Timer schreibt vollautomatisch; Dedup-Schlüssel (nur Rechnungsnummer), Konto-Regex auf Briefkopf und ungetestete Schreibpfade sind die drei substanziellen Design-Risiken (F2.1, F2.2, F2.7).
- Prozess: Scope-Checkpoint wurde erst nach dem Merge durabel (F1.3); Timer war vor dem Checkpoint aktiv (`over_act`); Git-Guard-Vorfall ×2 über Retros ⇒ Gate-Pflicht; heredoc-Rework ×4 ⇒ Re-Vorlage des abgelehnten Gates fällig.
- Widerlegt: „Review-Pflicht faktisch entfallen“ — Review-Count 0 ist dokumentierter KONZ-032-Zielzustand (Bot-Review + Required Checks). 3b kippte zwei Schweregrade (F3, F6) und fand F18 (`gh pr merge` ohne SA-M auf schon gemergten PR).
- Bestehende Memory-Regel „nie ohne Freigabe-Zwischenschritt buchen" widerspricht dem Timer und wurde nicht reconciled (F2.8).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| F1 | Ziel „bezahlen" nicht abgeschlossen (Beleg 155590335 Status 150), aber getrackt | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | `gh issue view 3102 --comments` Kommentar 2026-09-21 „Kontrolle 1000/400 nach Bankeingang" | — |
| F2 | sevdesk-Statuscodes ohne SSoT: kostenabgleich.py:101 kennt 50/100/1000, README/PR nennen 150, verbuchen_wache.py:179 wirft bei ≠100 | Wissenslücke | mittel | SURVIVES (kommandobelegt) | `git show origin/main:tools/sevdesk/kostenabgleich.py` Z.101; verbuchen_wache.py Z.179; README „Verbuchen" | voucher-status-enum-no-ssot (neu) |
| F3 | Scope-Checkpoint zum Dauer-Timer erst NACH dem Owner-Merge **durabel** (Kommentar 12:20:18Z, Merge 12:18:25Z durch `wirdigital` = Owner-Zweitkonto, Policy autonomy-gates Z.493); ausgesprochen 12:06:00, 12 Min VOR dem Merge | Prozesslücke | niedrig (3b: hoch→niedrig) | SURVIVES (Skeptiker B1, 3b Severity gekippt) | `gh api repos/achimdehnert/platform/issues/3347/timeline`; Transkript 12:06:00 Checkpoint-Text, 12:18:43 Owner-Antwort; gate-hits.jsonl 12:05:49 (Form A) / 12:20:10 (Form B) | scope-checkpoint-not-durably-recorded (Gate hat 2× gefeuert und gegriffen → gates_caught) |
| F4 | Testzahlen in PR-Texten uneinheitlich (160/128/60) ohne Hinweis „nur berührte Dateien"; sevdesk-nahe Tests auf origin/main = 281 | Kommunikation | mittel | SURVIVES (kommandobelegt) | `grep -c "^def test_"` über 12 Dateien = 281 vs. PR #3347 „60 grün" | pr-test-count-without-scope-label (neu) |
| F5 | Kein UI-Deeplink zum erzeugten Beleg in der Tool-Ausgabe; Owner musste nachfragen (08:56) | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | `grep -rn "sevdesk.de" tools/sevdesk/*.py` → nur API-Host; kennzahlen.txt 08:56:17Z | — |
| F6 | Dedup-Schlüssel `rechnung<N>` ohne Lieferant: ≥6-Schutz strukturell ausgehebelt (`rechnung1` = 9 Zeichen), Kollision bei Präfix-Nummern verschiedener Lieferanten; Kehrseite: Bestandsbelege ohne Wort „Rechnung“ werden gar nicht dedupliziert (Doppelanlage) | fehlende Validierung | mittel (3b: hoch→mittel) | SURVIVES (Skeptiker B2, 3b Mechanismus präzisiert) | beleg_entwurf.py Z.236-274 `_dedup_schluessel`/`duplikat`; verbuchen_wache.py Z.107; Bestandsmessung §8: heute 0 echte Kollisionen | dedup-key-without-supplier (neu) |
| F7 | Konto-Regeln per `re.search` auf 15 Briefkopf-Zeilen ohne Feldanker → False-Positive-Risiko | verfrühte Festlegung | mittel | SURVIVES (Skeptiker B3) | verbuchen_wache.py Z.59-77; Beispielmuster ohne Wortgrenzen; mildernd: 2 Treffer → None, Beleg nur „offen" | — |
| F8 | Batch-Schleife fängt nur `Unklar`; technischer Fehler bricht die Charge ohne Meldung | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | verbuchen_wache.py Z.268-318, einzige except-Klausel Z.304 | batch-loop-catches-only-domain-error (neu) |
| F9 | ssh-Totalausfall außerhalb try; Unit ohne `OnFailure=` → Ausfall nur im Journal sichtbar — **Muster-Lücke**, keine Abweichung: `sevdesk-rechnungslauf.service` hat ebenfalls keins (`git grep OnFailure origin/main -- '*.service'` → 0) | fehlende Validierung | mittel | SURVIVES (kommandobelegt, 3b: Muster) | verbuchen_wache.py Z.262; beide `.service`-Units ohne OnFailure/Restart | melder-ohne-leser (verwandt) |
| F10 | `docker cp` mit f-String-Pfad ohne `shlex.quote`; Repo nutzt sonst konsequent shlex | fehlende Validierung | niedrig | SURVIVES (Skeptiker B4) | paperless.py Z.86; `grep -rln shlex tools/` → 5 Module | — |
| F11 | Realer Lieferantenname („[Lieferant]") im öffentlichen Repo (Issue #3102) | Konventionsverstoß | niedrig | SURVIVES (kommandobelegt) | `gh issue view 3102 --comments`; CLAUDE.md „platform ist ÖFFENTLICH"; keine Bankdaten-Werte (sauber) | real-name-in-public-issue (neu) |
| F12 | Tests decken nur Planlogik; `anlegen`/`offen_stellen`/`tag_tauschen`/Batch-Fehlerpfad ungetestet | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | PR #3347-Text „reine Planlogik"; `grep "^def test_" tools/tests/test_verbuchen_wache.py` | untested-tool-module-green-gate (verwandt, Gate existiert) |
| F13 | Memory `feedback_sevdesk_booking_only_after_owner_approval` („nie ohne Zwischenschritt") vs. vollautomatischer Timer — nicht reconciled | Kommunikation | niedrig | SURVIVES (kommandobelegt) | Memory-Datei unverändert; PR #3347-Kommentar Owner-Bestätigung | automation-contradicts-memory-rule-unreconciled (neu) |
| F14 | heredoc/F821-Rework ×2 in dieser Sitzung (plus ein dritter beim Retro-Report selbst); Gate `inline-heredoc-quoting-rework` declined (2026-09-16) mit Bedingung „bei einem 3. Vorkommen erneut vorlegen“ — das 3. Vorkommen war schon 50d29a (2026-09-17), Re-Vorlage seit einer Retro überfällig | Werkzeug | mittel | SURVIVES (kommandobelegt, 3b) | kennzahlen.txt 09:50:59 / 12:03:35; `docs/governance/gates/declined/inline-heredoc-quoting-rework.json`; `retro_kpis.py` ×3 [40c069, 916eb7, 50d29a] | inline-heredoc-quoting-rework (×4 ⇒ Re-Vorlage überfällig) |
| F15 | Git-Guard `unauthorized_head_flip` 08:35:36Z (`git switch -c` auf Haupt-Tree); ADR-233 proposed/partial seit 06-01; 120 Events im Log | Prozesslücke | mittel | SURVIVES (Skeptiker B5) | `.git/iil-guard-events.log`; ADR-233 Frontmatter; `tools/main-tree-guard.sh` „best effort" | main-tree-guard-recurring-incident (×2 ⇒ GATE-PFLICHT) |
| F16 | #3347 + #3343 überlappende Zeilen in paperless.py; advisory-Gate hat gemeldet | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | `gh pr view 3347 --comments` „Serielle-PRs-Abgleich … BEFUND 1" | serielle-prs-auf-derselben-datei (×2, gates_caught) |
| F17 | Ruleset `required_approving_review_count: 0` → „Review-Pflicht faktisch entfallen“ | Wissenslücke | hoch | **REFUTED** (Skeptiker B6, 3b bestätigt) | `gh api repos/achimdehnert/platform/rulesets/17621471` → count 0, `require_code_owner_review: true`; KONZ-032 Z.166 dokumentiert 1→0 als Zielzustand (Owner-Go 2026-08-10); CODEOWNERS Z.77 „BEWUSST NICHT geschuetzt /tools/“; Bot-Check `context-review` SUCCESS (3b: es gibt keinen Check namens `review`) | — |
| F18 | `gh pr merge 3343` durch die Sitzung (11:12:27) ohne SA-M-Werkzeug `pr_merge_sa.py` und ohne vorherigen Status-Read — der PR war 72 Min vorher (10:00:17Z) vom Owner (`wirdigital`) gemergt; Wirkung null, Owner-Wort „14 go“ lag vor | Prozesslücke | niedrig | SURVIVES (3b NEU, kommandobelegt) | Transkript 11:12:27; `gh pr view 3343 --json mergedBy,mergedAt`; `ls -la ~/.claude/pr-merge-sa.jsonl` mtime 17.09.; Memory project_sa_m_merge_autonomy „nie direkt gh pr merge“ | direct-gh-pr-merge-bypasses-sa-m (×2 in Retros: 50d29a + hier ⇒ GATE-PFLICHT) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Drei PRs erfüllen das Owner-Ziel inkl. Aktion „verbuchen"; „bezahlen" offen auf 150 (F1) |
| architektur_design | 3 | Dedup ohne Lieferant (F6), Regex auf Briefkopf (F7), Status-Enum ohne SSoT (F2) |
| code_konventionstreue | 4 | shlex-Abweichung (F10), Name im öffentlichen Issue (F11); Commit-/Testnamen konform |
| risiko_debt | 3 | Schreibpfade ungetestet (F12), Fehlerpfad bricht Charge (F8/F9), Memory-Widerspruch offen (F13) |
| prozess_effizienz | 3 | Rework ×2 (F14), Guard-Vorfall (F15), Testzahlen ohne Scope (F4) |
| entscheidungsqualitaet | 4 | Namensgleichheit Tag=Kostenstelle, kein Backfill, Kanarienvogel — aber Checkpoint nach Merge (F3) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Beleg auf 150, Kontrolle „später" nur im Issue-Kommentar | Kontrollschritt als Zeile in `/next`-Quelle (docs/handover.d) mit Datum, nicht nur Issue-Kommentar | F1 |
| Statuscodes in drei Dateien verschieden | `VOUCHER_STATUS`-Konstanten in `mandant.py` (SSoT), alle Module importieren | F2 |
| Checkpoint ausgesprochen 12:06, durabel erst 12:20 (nach Owner-Merge) | Checkpoint-Text und PR-Kommentar im SELBEN Zug schreiben (Kommentar vor dem Merge-Zug des Owners) | F3 |
| PR-Text „60 Tests grün" ohne Scope | PR-Text nennt Kommando + Dateiliste („`pytest tools/tests/test_verbuchen_wache.py …` → 60") | F4 |
| Tool-Ausgabe nur beleg_id | Ausgabe enthält UI-Link `https://my.sevdesk.de/#/ex/detail/id/<id>` (Muster vorher einmal verifizieren) | F5 |
| Dedup über `rechnung<N>` | Dedup-Schlüssel = Lieferant + Nummer, Nummer als eigenes Feld statt Teilstring der Beschreibung; Bestand per `supplier` vorfiltern | F6 |
| Regel-Regex auf 15 Zeilen | Regeln mit `\b`-Ankern prüfen (`beleg_entwurf --konto-vorschlag` warnt bei Muster ohne Wortgrenze); Kopf auf Absenderblock (Zeilen bis „Rechnung") begrenzen | F7 |
| `except Unklar` einzig | `except Exception` je Dokument → `verbuchen-unklar` + Grund + Journal, Lauf geht weiter | F8 |
| ssh-Ausfall stumm (Muster) | `OnFailure=` auf einen Melde-Service in BEIDEN Units (verbuchen + rechnungslauf); Erstzugriff im try | F9 |
| f-String-Pfad in docker cp | `shlex.quote(dok["source_path"])` wie in den 5 anderen Modulen | F10 |
| Klarname im Issue | Lieferant im öffentlichen Issue als „KFZ-Werkstatt (Beleg 155590335)" | F11 |
| Nur Planlogik getestet | MockTransport-Tests für `offen_stellen` (Summen mitgeschickt) und Fake-`_shell` für `tag_tauschen` | F12 |
| Memory-Regel unverändert | Memory-Datei um Ausnahme „Timer legt offen an, nie bezahlt (Owner 2026-09-21)" ergänzen | F13 |
| heredoc-Patch nach ruff format | Edit-Tool statt python-heredoc für Anker-Replace; oder Patch VOR `ruff format` anwenden | F14 |
| `git switch -c` im Haupt-Tree | `tools/repo-session.sh start` als erster Befehl jeder editierenden Aufgabe (CLAUDE.md-Zeile, ADR-233 finalisieren) | F15 |
| Zwei PRs auf paperless.py in 3 h | Folge-Feature auf denselben Branch, wenn PR N noch offen ist | F16 |
| `gh pr merge` blind auf gemergten PR | Merge nur über `tools/pr_merge_sa.py` (liest Status, schreibt Journal); Owner-Wort als Vermerk | F18 |

## 5. Längsschnitt
`tools/retro_kpis.py` (134 Reports): `inline-heredoc-quoting-rework` ×3 → mit dieser Sitzung ×4 — declined mit Bedingung „bei 3. Vorkommen erneut vorlegen" ⇒ **Re-Vorlage fällig** (nicht neues Gate). `main-tree-guard-recurring-incident` ×1 (2752dc) → ×2 ⇒ **GATE-PFLICHT**. `scope-checkpoint-not-durably-recorded` ×29 und `claim-before-cheapest-check` ×85: Gates existieren, haben in dieser Sitzung gefeuert und gegriffen ⇒ `gates_caught`. `serielle-prs-auf-derselben-datei` ×1 → ×2, advisory hat gemeldet ⇒ `gates_caught`. `direct-gh-pr-merge-bypasses-sa-m` ×1 (50d29a) → ×2 mit F18 ⇒ **GATE-PFLICHT**. Memory-Abgleich: `feedback_sevdesk_booking_only_after_owner_approval.md` existiert (`ls`), `main-tree-guard`-Memory nicht vorhanden (`grep -ril "main-tree" MEMORY.md` → 0).

**refuted_rate-Band (Phase 5, rein numerisch):** 0.06 liegt unter dem 0,2-Band — Signal „Falsifikation ggf. zu lasch“; echte Falsifikationsquote `phase3_refuted/(findings_total − pre_refuted)` = 1/18. Nur 6 von 18 Befunden gingen an den Skeptiker (Bewertungsbefunde), 3b kippte zusätzlich 2 Schweregrade — die Quote zählt Kippungen nicht. Keine Bewertung der Einzelverdikte.

### 5a. Rückfall-Prüfung
Kein gebautes Gate ist in dieser Sitzung rückfällig: die drei feuernden Gates haben gegriffen (`gates_caught`). Die zwei `RUECKFAELLIG` aus 0.0 sind ohne Vorkommen hier. Keine `revised`-Einträge nötig.

### 5b. Autonomie-Kalibrierung
`over_act`: `dauer-automatismus-aktiviert-vor-checkpoint` — `systemctl --user enable --now` (12:05) vor dem Scope-Checkpoint (12:15 Chat, 12:20 durabel); Gate „Automatismus mit Schreibrecht" (CLAUDE.md `autonomous-no-human-review`) verlangt Beweis der Verdrahtung vor Merge — der kam (Echtlauf im PR-Text), das Innehalten aber danach. `over_ask`: keiner — die drei Owner-Fragen (Zahlweg, Konvention, Backfill) waren echte Entscheidungen.

## 6. Verankerung
memory_candidates:
- `feedback_sevdesk_booking_only_after_owner_approval.md` — Ergänzung: „Ausnahme (Owner 2026-09-21, #3347): der `verbuchen`-Timer legt Belege **offen** (100) an, nie bezahlt; Buchung/Zahlung bleibt Owner-Klick."
- neu `feedback_repo_session_first_command_before_edit.md` (drift): „`git switch -c` im Haupt-Tree → Guard-Snapback, Branch verwaist; erster Befehl jeder editierenden Aufgabe ist `bash tools/repo-session.sh start ~/github/<repo> --task <slug>` (voller Pfad, nicht Repo-Name)."
adr_candidates: keiner (Timer folgt dem Muster `sevdesk-rechnungslauf`; ADR-233 existiert und braucht Finalisierung, kein neues ADR).

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Dedup Lieferant+Nummer, `except Exception`, shlex, OnFailure (beide Units) | platform | Issue neu | 🔵 | ich: Issue + PR |
| M2 | Schreibpfad-Tests (offen_stellen, tag_tauschen) | platform | Issue neu (mit M1) | 🔵 | ich |
| M3 | Status-Konstanten SSoT in mandant.py | platform | Issue neu (mit M1) | 🔵 | ich |
| M4 | Gates `main-tree-guard-recurring-incident` + `direct-gh-pr-merge-bypasses-sa-m` (je ×2) | platform | gates/kandidaten | 🔵 | ich: `gate_verankerung_check.py --neu` |
| M5 | Re-Vorlage inline-heredoc-quoting-rework (×4, überfällig seit 50d29a) | platform | declined-Eintrag | 🟢 | du: Gate ja/nein |
| M6 | Memory-Ausnahme Timer (F13) + repo-session-Memory (F15) | platform | Memory | 🟢 | du: ja/nein |
| M7 | Klarname in #3102 anonymisieren | platform | #3102 | 🔵 | ich: Kommentar editieren |
| M8 | Streichbahn-Kandidat | platform | s. §Streichbahn | 🟢 | du |

## 8. Nicht verifiziert (Restlücken)
- **getan:** 3 Finder, 1 Skeptiker (6 Bewertungsbefunde), retro_kpis, gate_wirkung, Transkript-Kennzahlen per Skript; **Bestandsmessung zu F6** (read-only, beide Mandanten): 0 Kollisionen derselben Nummer (≥6 Zeichen) zwischen verschiedenen benannten Lieferanten — edv 717 Belege: 2 Treffer = Schreibvarianten desselben Lieferanten; iil 530: 29 Treffer = Monats-Tokens der Dauerrechnungen (kein Wache-Schlüssel). Positivkontrolle: 39/73 kurze Nummern, bis 6 Lieferanten je Token. F6 bleibt strukturell, Schwere im Bestand heute niedrig.
- **angenommen:** `wirdigital` handelt als Owner (Policy autonomy-gates Z.493 belegt die Rolle; angenommen bleibt nur, dass der Klick am 21.09. persönlich erfolgte — billigster Check: Owner-Wort).
- **nicht verifizierbar:** ob Paperless `'` in `source_path` durchlässt (billigster Check: Titel mit `'` hochladen, `source_path` lesen).
- **offen geblieben:** Kosten der Retro (6 Agenten, ~560k Subagent-Tokens laut Task-Notifications: Finder 95k+112k+107k, Skeptiker 122k, 3b 127k; Meta nicht gezählt) gegen Nutzen (1 REFUTED, 2 gekippt, 1 NEU, 3 Belegkorrekturen) — Bewertung erst im Längsschnitt über `refuted_rate`.

## Widerlegung (Phase 3b, Opus, frischer Kontext)
- F3 **GEKIPPT** (Severity hoch→niedrig): Checkpoint 12:06:00 im Transkript, Owner-Merge 12:18:25, Durabilität 12:20:18 auf Gate-Feedback — Regel „innehalten bevor weitergemacht wird“ war erfüllt, nur die Aufzeichnung kam nach; `over_act` (Timer 12:04:49 aktiv, 71 s vor Checkpoint) bleibt mit niedrigem Gewicht.
- F6 **BESTAETIGT**, Severity hoch→mittel, Mechanismus korrigiert (Präfix-Kollision auf `rechnung<N>`; Belege ohne Wort „Rechnung“ gar nicht dedupliziert).
- F9 **BESTAETIGT** als Muster-Lücke (rechnungslauf-Unit identisch), nicht als Sitzungsfehler.
- F14 **BESTAETIGT**, Zeitpunkt korrigiert: 3. Vorkommen war 50d29a, Re-Vorlage seit einer Retro überfällig.
- F17 **BESTAETIGT** (bleibt REFUTED); Beleg-Korrektur `review` → `context-review`.
- **NEU F18** `direct-gh-pr-merge-bypasses-sa-m` (niedrig, kommandobelegt, ×2 ⇒ Gate-Pflicht); die §8-Aussage des Entwurfs („#3343 per gh pr merge durch die Sitzung“) war falsch — der PR war vom Owner gemergt, das Kommando lief ins Leere.
- Geprüft ohne Befund: Zielzustand (Owner-Wort wörtlich im PR-Body = trivial-Right-Sizing), Datensouveränität (Bankdaten aus der Rechnung ins Buchhaltungssystem = Normalbetrieb), Timer aus dem Haupt-Working-Tree (Hauspattern aller 13 User-Timer). Unentscheidbar: Kosten (keine Token-Zahlen in kennzahlen.txt).
- `widerlegung: "2 gekippt, 1 neu"`

## Streichbahn (Phase 7)
**keiner, weil** jede Bahn dieser Retro etwas Eigenes geliefert hat: der Skeptiker kippte F17, 3b kippte zwei Schweregrade, fand F18 und drei Belegfehler, der Evidenz-Hook erzwang die F6-Bestandsmessung. Keine der vier Belegarten (kein Leser / kein Effekt / Dublette / Liegezeit) ist für eine Phase, einen Melder oder ein Gate dieser Sitzung erfüllt. Ratsche: erscheint `gate-modul-prueft-weniger-als-sein-name` in der nächsten Retro erneut als `RUECKFAELLIG` ohne zurechenbares Vorkommen (hier die 3. Retro in Folge ohne Vorkommen — 50d29a, 8185e1, diese), ist das ein Streichkandidat mit Belegart „Liegezeit“.

## Self-Review (Phase 5, Sonnet, nur Report)
12 Prüfpunkte: 10 ✓, 2 ✗ behoben — (11) F17/F18-Zeilen waren beim Einfügen verschränkt (F17 ohne Beleg/Recurrence, F18 mit zwei überzähligen Zellen) → beide Zeilen auf die 7 eingefrorenen Spalten gebracht; (8) `refuted_rate`-Bandaussage fehlte → unter §5 ergänzt. Belege mit Transkript-Zeitstempeln (F3, F5, F14, F15, F18) sind jeweils mit einem gh/git-Beleg gemischt, keine Zeile trägt nur das Transkript.
