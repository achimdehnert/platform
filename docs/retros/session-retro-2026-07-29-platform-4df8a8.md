---
retro_schema: 1
date: 2026-07-29
repo_scope: [platform]
session_id: 4df8a8
footprint: deep
findings_total: 9
findings_survived: 7
refuted_rate: 0.22
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates:
  - runbook-version-not-derived-from-compose
  - pr-body-stale-vs-merged-content
recurring_findings:
  - claim-before-cheapest-check
  - parallel-session-pr-collision
  - deferred-item-no-tracking-issue
  - untested-tool-module-green-gate
  - runbook-version-not-derived-from-compose
  - pr-body-stale-vs-merged-content
  - prod-change-no-durable-approval-note
---

# Session-Retro 2026-07-29 — platform (4df8a8)

**Strang:** doc-hub/Paperless-Upgrade · Backup-Sanierung · Cloudflare Access · sevdesk-Bankpositionen.
Vier PRs: #1526, #1528, #1534, #1537 — alle gemergt. Am selben Tag liefen mindestens zwei
weitere Sessions im selben Repo (18 Merges insgesamt); deren PRs sind **nicht** in-scope.
Die Strang-Abgrenzung wurde vom Skeptiker unabhängig über `gh pr view --json title,files`
bestätigt.

## 1. Executive Summary

- Der **einzige verifizierte Rollback-Pfad für ein Produktivsystem ist latent gebrochen**:
  die Rückspielprobe zeigt weiter auf Paperless 2.14, die Instanz läuft auf 3.0.4.
  Ausgerechnet der Weg, der morgens als „bewiesen tragfähig" gemeldet wurde.
- Eine ausdrücklich erklärte **ADR-142-Abweichung** wurde nirgends im ADR nachgezogen;
  dessen Frontmatter behauptet weiter, doc-hub nutze authentik-SSO erfolgreich.
- Der **PR-Body von #1528 widerspricht seinem eigenen Titel** und verschweigt die
  Auth-Umstellung — ein Reviewer, der nur die Zusammenfassung liest, sieht das Gegenteil
  dessen, was gemergt wurde.
- Beide neuen Werkzeuge haben **keine Tests**, obwohl die Repo-Konvention `make test =
  pytest tools/tests/` lautet und jedes Nachbarmodul ein Pendant hat.
- Vier der sieben überlebenden Befunde tragen Slugs, die **bereits gate-pflichtig** sind —
  das Muster ist bekannt, die Verankerung fehlt.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `restore-test.sh` hardcodet `paperless-ngx:2.14`, Produktivinstanz läuft seit #1528 auf `3.0.4` — der `document_importer`-Weg der Rückspielprobe ist für alle Backups ab 2026-07-29 nicht mehr lauffähig | fehlende Validierung | **kritisch** | SURVIVES | `git show origin/main:deployment/stacks/doc-hub/restore-test.sh` Z.17 vs. `docker-compose.yml` Z.21; `git grep` repo-weit: 4 Fundstellen der Version, keine abgeleitet | neu (`runbook-version-not-derived-from-compose`) |
| 2 | ADR-142 nicht nachgezogen trotz wörtlich erklärter Abweichung; `implementation_evidence` behauptet weiter „doc-hub … SSO Login tested ✓". Kein Issue, kein PR, kein Commit trackt die Nachpflege | Prozesslücke | **hoch** | SURVIVES | `git show origin/main:docs/adr/ADR-142-*.md`; `git log --all -- docs/adr/ADR-142*` → letzter Commit 2026-07-15; `gh issue/pr list --search "ADR-142"` → kein offenes Artefakt | `deferred-item-no-tracking-issue` ×4 → **5** |
| 3 | PR-Body #1528 nie aktualisiert: Titel nennt 3.0.4, Body argumentiert weiter „BEWUSST NICHT auf 3.0.x"; die Cloudflare-Access-Umstellung fehlt im Body vollständig | Kommunikation | mittel | SURVIVES | `gh pr view 1528 --json body \| grep -i cloudflare` → exit 1; `grep -i authentik` → exit 1; Titel/Body-Diskrepanz | neu (`pr-body-stale-vs-merged-content`) |
| 4 | Keine Tests für `tools/sevdesk/bankpositionen.py` und für die neue `/d/<name>`-Route; `test_mail_link_server.py` deckt nur die ältere `/a/`-Anker-Route ab | fehlende Validierung | mittel | SURVIVES | `gh api …/git/trees/main?recursive=1` gefiltert; kein Test referenziert `board_pfad`/`board_als_html`/`_board`; kein `test_bankpositionen.py` | `untested-tool-module-green-gate` ×2 → **3** |
| 5 | #1526 (Eingriff ins Produktiv-Backup-System) trägt keinerlei Freigabe-Vermerk — weder im Body noch im Commit | Prozesslücke | mittel | SURVIVES | `gh pr view 1526 --json body \| grep -in owner` → exit 1; Commit-Message ebenso | neu (`prod-change-no-durable-approval-note`) |
| 6 | #1534 musste wegen Kollision mit dem parallel gemergten #1535 an derselben Datei rebased und force-gepusht werden; keine Kollisionsprüfung vor Arbeitsbeginn dokumentiert | Prozesslücke | niedrig | SURVIVES | `gh api …/issues/1534/timeline` → `head_ref_force_pushed 11:53:56Z`; `git merge-base --is-ancestor 53cc5bb6 51c6616e` → YES; Gegenprobe: 5 andere PRs ohne Force-Push-Event | `parallel-session-pr-collision` ×4 → **5** |
| 7 | PayPal-Erkennungsmuster an einem einmaligen Bestand kalibriert („28 von 28"), keine Fixture für die drei dokumentierten Schreibweisen | verfrühte Festlegung | niedrig | SURVIVES | `tools/sevdesk/bankpositionen.py` Z.38–45; repo-weite Suche nach `PP_MUSTER`/`paypal_haendler` → nur Quelldatei | neu |
| 8 | „`AGENT_HANDOVER.md` veraltet, Korrektur in offenem PR" | — | — | **REFUTED** | Fakt stimmt, betrifft aber Strang 2 (#1540); keiner der vier Strang-1-PRs berührt die Datei, Strang 1 kommt darin nicht vor | — |
| 9 | „Kein Artefakt, in dem der gewachsene Scope gespiegelt wurde" | — | — | **REFUTED** | Zwei durable „Owner-Entscheid 2026-07-29"-Vermerke in den Commits `242e1893` und `dc4083f3` | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---:|---|
| zielerreichung | 4 | Alle vom Owner gestellten Aufgaben geliefert und belegt (Backup saniert + Rückspielprobe bestanden, Upgrade auf 3.0.4, Cloudflare Access mit Falsifikationstest, sevdesk-Liste mit 76/84 Zuordnung, Arbeitsstand eingefroren). Abzug: der Rollback-Pfad, den das Ziel „Backup fixen" eigentlich herstellen sollte, ist am Ende gebrochen (#1) |
| architektur_design | 4 | Sauberes Muster: personenbezogene Zuordnung außerhalb des Repos, schlüsselbasierter Schnappschuss statt gerenderter Ansicht, Zeitstempel als Argument statt Systemuhr, Board-Verzeichnis getrennt von der Secret-Schleuse. Abzug: Versionsangabe an vier Stellen verstreut, nirgends abgeleitet (#1) |
| code_konventionstreue | 3 | Worktree statt Haupt-Tree, konventionelle Commits, kein Direkt-Commit auf main. Aber: zwei neue Werkzeuge ohne Tests, obwohl jedes Nachbarmodul eins hat (#4) |
| risiko_debt | 2 | Ein kritischer Befund (#1) plus ein sachlich falsch gewordenes Governance-Artefakt (#2), beide ungetrackt bis zu diesem Retro. Die beiden bewusst offen gelassenen Punkte sind dagegen sauber als #1527/#1529 getrackt |
| prozess_effizienz | 3 | Spürbarer Rework: Rebase+Force-Push (#6), drei Anläufe für die Rückspielprobe, zweimal die eigene Shell per `pkill -f` beendet, ein Dienst-Neustart, den systemd zurückdrehte |
| entscheidungsqualitaet | 4 | Mehrere belegbar gute Entscheidungen: erst 2.20.15 als Zwischenstufe, Tunnel-only als Voraussetzung **vor** der Header-Anmeldung geprüft, Konten nicht geraten sondern gegen den echten Kontenrahmen abgeglichen, Buchungen gegated. Abzug: mehrere Behauptungen vor dem billigsten Check (#30 des Slugs) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `restore-test.sh` setzt `IMAGE=…:2.14` fest; `docker-compose.yml` wurde später auf `3.0.4` gehoben, die Probe nicht nachgezogen | Die Probe liest den Image-Tag **aus der Compose-Datei** (`grep image: docker-compose.yml`) statt ihn zu duplizieren; zusätzlich CI-Gate „Image-Tag in Runbook == Compose" | #1 |
| Commit sagt „Abweichung von ADR-142", ADR-Datei bleibt unverändert | Sobald eine Commit-Message eine ADR-Nummer mit Abweichungs-Wortlaut nennt, im **selben PR** entweder die ADR ergänzen oder ein Issue mit Link eröffnen — analog zum bestehenden Muster der PRs #201–203/#241 | #2 |
| PR-Titel wurde bei Scope-Zuwachs nachgezogen, der Body nicht | Vor dem Setzen von Auto-Merge den Body gegen die Commit-Liste prüfen: nennt der Body jeden Commit-Gegenstand? Wenn nein, Body ersetzen statt ergänzen | #3 |
| Zwei neue Werkzeuge live gegen die laufende Instanz belegt, ohne Testdatei | Für jede neue Datei unter `tools/` im selben PR ein `tools/tests/test_<name>.py`; ein CI-Gate lehnt neue `tools/`-Dateien ohne Pendant ab | #4 |
| PayPal-Muster gegen den Live-Bestand gezählt („28 von 28"), Ergebnis als Kommentar festgehalten | Die drei dokumentierten Schreibweisen als Fixture in den Test aufnehmen; die Zählung gegen den Live-Bestand bleibt Ergänzung, nicht Ersatz | #7 |
| Backup-System auf Prod umgebaut, kein Freigabe-Vermerk im Artefakt | Bei jedem Eingriff in ein laufendes Prod-System einen Satz „Freigabe: <wörtliches Zitat des Owners, Datum>" in die Commit-Message — wie es #1528 zweimal richtig macht | #5 |
| An `mail_link_server.py` gearbeitet, ohne zu prüfen, wer sonst daran arbeitet | Vor der ersten Zeile an einer Datei: `gh pr list --search "<datei>"` und `git log --oneline origin/main -- <datei> --since=1day`; bei Treffer entweder abwarten oder früh rebasen | #6 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (56 Reports) — vier meiner sieben Befunde sind Wiederholungen
auf bereits **gate-pflichtigen** Slugs:

| Slug | bisher | jetzt | mein Befund |
|---|---:|---:|---|
| `claim-before-cheapest-check` | ×29 | **30** | „Link live und getestet" für eine Anordnung, die konstruktionsbedingt vorübergehend war; zusätzlich „PayPal-Händler nur im Umsatzbericht" dreimal behauptet, dann selbst widerlegt |
| `parallel-session-pr-collision` | ×4 | **5** | #6 |
| `deferred-item-no-tracking-issue` | ×4 | **5** | #2 |
| `untested-tool-module-green-gate` | ×2 | **3** | #4 |

`risiko_debt` bleibt mit Ø 2,59 über 56 Retros die schwächste Dimension; dieser Lauf liegt
mit 2 darunter. `refuted_rate` 0,22 liegt im gesunden Band (Trend der letzten Läufe:
0,00 · 0,11 · 0,35 · 0,21 · 0,13 · 0,22 · 0,13 · 0,05).

### 5b. Autonomie-Kalibrierung

- **`over_act`: 1.** Der Dienst auf Port 8787 wurde per Hand gestoppt und aus einem Worktree
  neu gestartet, ohne vorher zu prüfen, dass eine systemd-Unit ihn verwaltet. Das ist ein
  Eingriff in einen verwalteten Dienst ohne Freigabe. Folge: systemd drehte die Änderung
  zurück, der dem Owner genannte Link war 404.
- **`over_ask`: 0.** Kein Fall gefunden, in dem etwas deterministisch Reversibles unnötig
  vorgelegt wurde. Die Vorlage der selbstbetreffenden Berechtigungserweiterung
  (`achim@dehnert.team`-Lesezugang) war charta-konform, kein `over_ask`.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

1. `feedback_runbook_version_must_derive_from_compose` — „Ein Runbook/Prüfskript, das eine
   Image- oder Paketversion **dupliziert** statt sie aus der Bereitstellungsdatei abzuleiten,
   ist nach dem nächsten Upgrade still kaputt. Realfall 2026-07-29: `restore-test.sh`
   (`:2.14`) gegen `docker-compose.yml` (`:3.0.4`) — der einzige verifizierte Rollback-Pfad
   für 826 Produktivdokumente. Version aus der Quelle lesen, nicht abschreiben."
2. `feedback_pr_body_must_match_merged_commits` — „Der PR-**Body** ist das, was ein Reviewer
   liest; Commit-Messages sind es nicht. Wächst der Scope innerhalb eines Branches, wird der
   Body **ersetzt**, nicht nur der Titel. Realfall 2026-07-29 #1528: Titel „auf 3.0.4", Body
   argumentiert dagegen, Auth-Umstellung im Body gar nicht erwähnt."
3. Ergänzung zu `feedback_check_service_manager_before_restart` (heute bereits angelegt) —
   als `over_act`-Beleg in der Autonomie-Kalibrierung referenzieren.

**adr_candidates** — keiner. Die Befunde sind Prozess- und Werkzeuglücken, keine
Architektur-Entscheidungen; nach `adr-threshold.md` genügen Memory + Gate.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Entscheiden, ob die Rückspielprobe sofort repariert wird (Prod-Rollback-Fähigkeit) — https://github.com/achimdehnert/platform/blob/main/deployment/stacks/doc-hub/restore-test.sh
2. 🟢 ADR-142 nachziehen oder Nachpflege als Issue eröffnen — https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-142-unified-identity-authentik-platform-idp.md

### 🔵 Offen — ich kann sofort

3. 🔵 `restore-test.sh` liest Image-Tag aus der Compose-Datei — https://github.com/achimdehnert/platform/blob/main/deployment/stacks/doc-hub/restore-test.sh
4. 🔵 Tests für `bankpositionen.py` und die `/d/`-Route nachziehen — https://github.com/achimdehnert/platform/blob/main/tools/sevdesk/bankpositionen.py
5. 🔵 PR-Body von #1528 nachträglich korrigieren (Historie ehrlich halten) — https://github.com/achimdehnert/platform/pull/1528

### ✅ Erledigt

6. ✅ Restarbeiten aus dem Umbau getrackt — https://github.com/achimdehnert/platform/issues/1527
7. ✅ GHCR-Befund getrackt — https://github.com/achimdehnert/platform/issues/1529

## 8. Nicht verifiziert (Restlücken)

- **Ob der Themenwechsel zu Paperless/Backup vom Owner angestoßen wurde**, ist aus
  Repo-Artefakten nicht feststellbar (kein Chat-Transkript für die Prüfer). Als Hypothese
  geführt, nicht als Befund. Billigster Check: Transkript.
- **Mailversand an eine dritte Person** (zwei Mails an `md@dehnert.team`) hinterlässt kein
  Git-Artefakt und war über das Repo nicht prüfbar. Billigster Check: IMAP-Gesendet-Ordner —
  für `ad@` möglich, für `achim@` erst seit heute.
- **Secrets-Scan** wurde nur für #1534 per CI bestätigt (`gitleaks: SUCCESS`); für #1526,
  #1528, #1537 im Rahmen dieses Retros nicht einzeln nachvollzogen. Billigster Check:
  `gh pr checks <N> --repo achimdehnert/platform | grep -i gitleaks` je PR.
- **Ob ein 3.0.4-Import mit dem 2.14-Image tatsächlich scheitert**, ist nicht empirisch
  belegt, sondern aus den dokumentierten Breaking Changes abgeleitet. Billigster Check:
  `restore-test.sh` einmal unverändert laufen lassen — er ist gefahrlos (Wegwerf-Container).

## Self-Review (Phase 5, Meta-Agent)

Ein separater Prüfer hat **nur diesen Report gegen die Skill-Regeln** gehalten, nicht die
Session. Zwei echte Verstöße, beide vor dem Commit behoben:

1. **Invariante verletzt** — die Soll-Ablauf-Tabelle hatte 6 Zeilen bei 7 überlebenden
   Befunden, weil eine Zeile zwei Befunde bündelte (`#4, #7`). Die Abdeckung war vollständig,
   die Regel verlangt aber Zeilengleichheit. Aufgetrennt.
2. **§8 unvollständig** — eine der vier Restlücken (Secrets-Scan) nannte keinen billigsten
   Check. Ergänzt.

Ohne Beanstandung: Frontmatter schema-valide, Scores ganzzahlig und je verankert,
Befund-Spalten in fester Reihenfolge, kein drittes Verdikt, `refuted_rate` = (2+0)/9 = 0,22
nachgerechnet, Executive Summary mit genau 5 Punkten, Abschnittsreihenfolge 1–8 eingehalten,
Report-Pfad kollisionsfrei.

Als schwächer markiert, aber nicht als Verstoß: die Belege der Befunde #4 und #8 nennen das
Werkzeug, aber nicht das exakte Filterkriterium bzw. keinen Befehl mit Ausgabe. Beide bleiben
prüfbar, sind aber weniger nachvollziehbar als die übrigen.

Bandvergleich `refuted_rate` (rein numerisch): 0,22 liegt innerhalb der Spannweite
[0,00; 0,35] der acht vorangehenden Läufe.
