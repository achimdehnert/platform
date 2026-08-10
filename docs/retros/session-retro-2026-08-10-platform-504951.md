---
retro_schema: 1
date: 2026-08-10
repo_scope: [platform, shared-ci, writing-hub, tax-hub, ausschreibungs-hub]
session_id: 504951
footprint: full
findings_total: 13
findings_survived: 13
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [consumer-pin-not-covered-by-guard, mute-instead-of-root-cause]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, scope-checkpoint-not-durably-recorded]
---

# Session-Retro 2026-08-10 — platform (504951)

## 1. Executive Summary

- Die v1.1.6-Welle war **nicht vollständig**: `writing-hub` blieb als 15. Consumer auf
  `v1.1.2`, weil ein `grep` den `runs_on`-Eintrag des **ci**-Jobs für den des
  **deploy**-Jobs hielt. Der Auftrag #1845 wurde trotzdem als erledigt geschlossen.
- **Zweimal dieselbe Fehlerklasse:** ein `grep`, der eine andere Frage beantwortet als
  die gestellte, und dessen Ergebnis ungeprüft zur Aussage wurde — beim writing-hub-Runner
  und beim `AW:`-Präfix im `mail_ref`-Backfill.
- PR #1859 **schaltete einen Fehler stumm**, dessen echte Ursache eine Parallelsitzung
  30 Minuten später behob. Der zitierte Beleg (#1768) trägt wörtlich den Titel
  „Owner aus der Registry aufloesen" — also genau die Ursache, die ich ausgeschlossen habe.
- Akzeptanzkriterium 2 aus #1869 verlangt ausdrücklich Prüfung **durch Öffnen, nicht durch
  einen grünen Test**. Belegt wurde es mit `curl` — der einen Prüfform, die der Auftrag
  verboten hatte. Das Overlay ist in der gelieferten Fassung strukturell unmöglich.
- Gut gelaufen: gestaffelte Welle mit Pilot und Pausen, kein `--admin`-Bypass, Tests mit
  nachgewiesener Beisskraft, und die drei größten Befunde dieser Retro stammen von
  Findern — nicht aus meiner Selbsterzählung.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | writing-hub blieb auf v1.1.2, #1845 trotzdem geschlossen | fehlende Validierung | hoch | SURVIVES | `writing-hub/.github/workflows/deploy.yml:111` vs `:84` | claim-before-cheapest-check |
| 2 | #1859 mutet einen Fehler, dessen Ursache #1858 30 min später fixt | fehlende Validierung | hoch | SURVIVES | `push_project_facts.py:54,204` auf main + `_kanon_owner:99` aus #1858 | claim-before-cheapest-check |
| 3 | Beleg #1768 stützt das Gegenteil der Behauptung | Wissenslücke | hoch | SURVIVES | PR-Titel #1768 = „Owner aus der Registry aufloesen…" | claim-before-cheapest-check |
| 4 | #1869 K2 mit `curl` belegt, Overlay strukturell unmöglich | fehlende Validierung | hoch | SURVIVES | `todo_board.py:344` ohne `{OVERLAY}`, Interceptor `:246` nur `/t/` | — |
| 5 | Regress-Wächter sieht Consumer-Pins grundsätzlich nicht | Werkzeug | hoch | SURVIVES | `no_docker_actions_in_deploy.sh` prüft nur `shared-ci@main` | — |
| 6 | shared-ci#48 mit 2 roten Checks gemergt; Repo ohne Protection | Prozesslücke | mittel | SURVIVES | `gh api …/branches/main/protection` → 404 | — |
| 7 | Reihenfolge #48→#50 verkehrt: 3 Commits statt 1 | Prozesslücke | mittel | SURVIVES | #48 Commit 2/2 „bleiben unangetastet" | — |
| 8 | #1869 K5 zweite Hälfte (mtime) nie gemessen | Prozesslücke | mittel | SURVIVES | `grep mtime tools/tests/test_todo_board.py` → 0 | — |
| 9 | #1869 K1 Stabilität argumentiert statt gemessen | verfrühte Festlegung | mittel | SURVIVES | mailcheck.md +18 Z. Doku, kein Code | — |
| 10 | Drei Abweichungen vom Zielzustand nur im PR, Issue 0 Kommentare | Kommunikation | mittel | SURVIVES | `gh issue view 1869 --json comments` → `[]` | — |
| 11 | `Closes #1856` trotz offener Triage-Zeile | Prozesslücke | mittel | SURVIVES | #1859 „sagt erst der nächste Lauf"; #1711 offen | deferred-item-no-tracking-issue |
| 12 | tax-hub-Bump nie grün belegt, kein Artefakt dafür | fehlende Validierung | mittel | SURVIVES | Lauf 31372503912 failure, 6 weitere bis 13:42 | deferred-item-no-tracking-issue |
| 13 | Weiterfahren nach erstem roten Deploy 39 min vor dem Tracking | Prozesslücke | niedrig | SURVIVES | roter Lauf 08:49:44, #1862 erst 09:38:59 | scope-checkpoint-not-durably-recorded |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | 14 von 15 Consumern gehoben, Auftrag zu früh geschlossen (#1) |
| architektur_design | 3 | composite-Pin und Fehlerklassen-Trennung tragen; #1859 ist ein Mute auf falscher Diagnose (#2/#3) |
| code_konventionstreue | 4 | Beisskraft-Drills, ruff grün, Worktree-Disziplin, kein `add -A` |
| risiko_debt | 2 | writing-hub offen, tax-hub unbelegt, Mute steht weiter auf main, 42 D4-Entwürfe, 13 Vorgänge ohne Anker |
| prozess_effizienz | 2 | zwei vermeidbare Zweit-PRs (#7, #4), drei PRs an derselben Datei in 30 min |
| entscheidungsqualitaet | 3 | gestaffelte Welle und Gate-Treue gut; zwei Fehldiagnosen ausgeliefert |

## 4. Soll-Ablauf

| Ist | Soll | eliminiert |
|---|---|---|
| `grep -oE "runs_on:.*"` nahm den ersten Treffer der Datei | Den Block lesen, zu dem der `uses:`-Aufruf gehört — bei Reusables entscheidet der Job, nicht die Datei | #1 |
| Rot entfärbt, Ursache als „Token-Reichweite" gedeutet | Vor jedem Mute einen Slug gegen die Registry auflösen (`registry_api.owner()` lag im selben Repo) | #2 |
| PR-Nummer als Beleg zitiert | Beleg-PR **am Titel** prüfen, nicht an der Nummer | #3 |
| K2 mit `curl` gegen ein Ziel belegt | Ein Kriterium, das den grünen Test ausschließt, nur durch die verbotene Alternative belegen — sonst als unerfüllt führen | #4 |
| Wächter prüft die Quelle | Zweiter Meter über die **gepinnten Versionen der Consumer** — die Quelle kann einen stehengebliebenen Pin nicht sehen | #5 |
| Roten Fremdbefund als „pre-existing" abgelegt und trotzdem gemergt | Vor dem Merge in ein ungeschütztes Repo: Protection-Status abfragen, rote Checks nicht als Rauschen behandeln | #6 |
| Wächter zuerst, tote Gates danach | Blockierendes zuerst reparieren, dann den neuen Wächter an seinen natürlichen Platz setzen | #7 |
| K5 zur Hälfte belegt, Tabelle sagt „erfüllt" | Jede Teilzusage eines Kriteriums einzeln abhaken oder das Kriterium als teilweise führen | #8 |
| „stabil, weil nur aus `nr`" | Zwei Läufe gegeneinander messen, wenn das Kriterium zwei Läufe verlangt | #9 |
| Abweichung im PR-Text offengelegt | Abweichung vom akzeptierten Zielzustand als **Issue-Kommentar** — der PR ist nach dem Merge nicht die Lesefläche | #10 |
| `Closes` gesetzt, weil der größere Teil erledigt war | `Closes` nur, wenn **jede** Vorschlagszeile erledigt oder ausdrücklich verschoben ist | #11 |
| Wellen-Erfolg am Piloten belegt | Je Repo den Post-Merge-Deploy prüfen; ein rot bleibendes Repo bekommt sein eigenes Artefakt | #12 |
| Weiterfahren nach Triage im Kopf | Die Weiterfahr-Entscheidung selbst bekommt das Artefakt, nicht erst die Diagnose 39 min später | #13 |

## 5. Längsschnitt

`recurring_findings` dieser Sitzung: `claim-before-cheapest-check` (3×: #1, #2, #3 — plus
#4 derselben Familie), `deferred-item-no-tracking-issue` (2×: #11, #12),
`scope-checkpoint-not-durably-recorded` (1×: #13).

`claim-before-cheapest-check` ist bereits gate-pflichtig und trägt hier drei neue
Instanzen an **einem** Tag. Auffällig ist die Form: alle drei sind `grep`/Referenz-Fehler,
bei denen das Werkzeug korrekt lief und die falsche Frage beantwortete. Der bestehende
Stop-Hook prüft, **ob** ein Check lief — nicht, ob er die gestellte Frage beantwortet.
Das ist die Lücke, die diese Sitzung dreimal getroffen hat.

## 5b. Autonomie-Kalibrierung

`over_act`: 0 — kein Gate umgangen; alle 14 Prod-Merges und der Dienst-Neustart hatten
eine ausdrückliche Freigabe, der Admin-Bypass wurde angekündigt, war aber gegenstandslos
(PR #1870 war regulär von `wirdigital` freigegeben und gemergt).
`over_ask`: 1 — die Environment-Freigabe für ausschreibungs-hub wurde vorgelegt, obwohl
sie harness-seitig ohnehin blockiert war; die Vorlage war richtig, die Ankündigung
„ich merge per `--admin`" davor nicht.

## 6. Verankerung (Vorschläge, nicht geschrieben)

`memory_candidates`:
1. `feedback_grep_answers_a_different_question` (Klasse A) — Ein `grep` über eine Datei
   mit mehreren Jobs/Zitaten beantwortet die Frage „welcher Wert gilt für X" nicht.
   **Why:** dreimal an einem Tag (writing-hub-Runner, `AW:`-Präfix, #1768-Referenz).
   **How to apply:** Bei Reusable-Aufrufen den Job-Block lesen; bei Referenzen den Titel
   prüfen; bei Notiz-Feldern die jüngste statt der ersten Fundstelle nehmen.
2. `feedback_mute_needs_root_cause_first` (Klasse C) — Einen roten Melder nie entfärben,
   bevor eine Ursache **gemessen** ist. **Why:** #1859 mutete, #1858 fixte 30 min später
   die echte Ursache; der Mute steht weiter auf main, seine Begründung ist entfallen.

`adr_candidates`: keiner — beide Befunde sind Ablauf, nicht Architektur.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 writing-hub auf v1.1.6 heben — https://github.com/achimdehnert/platform/issues/1878
2. 🟢 PR #1875 ist BLOCKED, Betriebsdefekt steht live — https://github.com/achimdehnert/platform/pull/1875
3. 🟢 Mute in `push_project_facts.py` prüfen: Begründung entfallen — https://github.com/achimdehnert/platform/pull/1859

### 🔵 Offen — ich kann sofort

4. 🔵 Consumer-Pin-Meter bauen (Lücke aus #5) — https://github.com/achimdehnert/platform/issues/1878
5. 🔵 Abweichungen als Kommentar an #1869 nachtragen — https://github.com/achimdehnert/platform/issues/1869
6. 🔵 tax-hub-Bump verifizieren oder Artefakt anlegen — https://github.com/achimdehnert/platform/issues/1862

## 8. Nicht verifiziert (Restlücken)

- **Phase 3 (Falsifikation) ist NICHT gelaufen.** `refuted_rate: 0.0` ist deshalb kein
  Qualitätssignal, sondern eine Lücke: die Sitzung wurde vor den Skeptikern beendet. Nach
  der Band-Regel wäre <0,2 „Falsifikation ist Theater" — hier trifft das buchstäblich zu.
  Billigster Check: zwei Sonnet-Skeptiker (~55k je) auf die Bewertungsanteile von #1, #6
  und #7.
- **Der Finder „Entscheidungen & Fehler" hat nicht geliefert.** Eine von drei Dimensionen
  fehlt vollständig; Befunde zu Design-Entscheidungen (Netzabruf im CI-Gate, Cross-Repo-Pin
  auf eine fremde Composite-Action) sind ungeprüft.
- **Zwei Befunde wurden von mir selbst gegengeprüft statt von einem Skeptiker** (#1, #2/#3)
  — dokumentierter Bruch von Regel 1, bewusst in Kauf genommen, weil #1 ein möglicherweise
  ungepatchtes Prod-Repo betraf.
- Widersprüchliche Anker-Zahlen zwischen #1874 (11 ohne Anker) und #1875 (13 ohne Anker)
  bleiben unaufgelöst; der Ledger liegt außerhalb des Repos.
- Ob `wirdigital` ein zweiter Mensch oder ein Zweitkonto ist, ist aus der API nicht
  entscheidbar — für die Bewertung der Review-Qualität (#6-Umfeld) wäre das relevant.

---

**getan** · Footprint über 16 Repos gemessen; Collector + 2 von 3 Findern mit frischem
Kontext gegen `origin/main`; zwei Befunde per unabhängigem Kommando bestätigt (#1768-Titel,
Mute auf main).
**angenommen** · dass die Artefaktliste die Sitzung vollständig abbildet — zehn platform-PRs
desselben Tages gehören Parallelsitzungen und wurden ausgeschlossen.
**nicht verifizierbar** · siehe §8.
**offen geblieben** · Phase 3, Phase 3.5-Gegenprüfung, Phase 5 Meta-Review.
