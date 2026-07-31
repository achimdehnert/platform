---
retro_schema: 1
date: 2026-07-31
repo_scope: [platform, dev-hub]
session_id: ec0588a8
footprint: deep
findings_total: 13
findings_survived: 10
refuted_rate: 0.23
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 2
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [wordboundary-missing-in-text-heuristic, skip-ci-literal-blocks-required-checks, merge-race-loses-commits]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, branch-cleanup-missing-after-merge]
---

# Session-Retro 2026-07-31 — platform + dev-hub (Mail-Werkzeug, Prod-Ingest, ~/.claude-Schaden)

## 1. Executive Summary

- **Die Ziele wurden erreicht, das Handwerk hat gelitten.** Mail-Ingestion läuft auf Produktion (Runbook-Schritte 1–7, eine aktive Generation), Antwort-Entwürfe zitieren, der Link-Dienst ist veröffentlicht — aber drei der sechs Score-Dimensionen liegen bei 2.
- **Ein gemergter Bug löscht stillschweigend Text aus Mails.** `_ohne_doppelten_namen` (#1568) entfernt die Zeile nach jedem Satz, der mit „Grüße…" beginnt — reproduziert an „Grüße deine Frau von mir." Der PR-Text behauptete ausdrücklich das Gegenteil.
- **Der Guard aus #1558 ist blind gegen sein eigenes Unfall-Residuum.** Er erlaubt den Swap, sobald `MANAGED_BY`/`manifest.json` im Ziel liegen — genau das, was der Unfall dort hinterlässt. Auf dieser Maschine derzeit dormant (Marker wurden entfernt), die Logiklücke bleibt.
- **Zwei Prozessfehler traten je zweimal auf**, bevor die Lehre griff: `[skip ci]` im Kopf-Commit (37 h 56 min bzw. 12 min blockiert) und Merge während laufendem Push (zwei Folge-PRs).
- **Die Falsifikation hat drei von dreizehn Anklagen kassiert** — darunter zwei, die den Autor entlastet haben. Genau dafür ist Richter ≠ Angeklagter da.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `_ohne_doppelten_namen` löscht Fließtext: `startswith(GRUSSFORMELN)` prüft keine Wortgrenze, „Grüße deine Frau von mir." matcht | fehlende Validierung | **kritisch** | SURVIVES | `roles.py:298` (origin/main); reproduziert: Namenszeile verschwindet | neu |
| 2 | Guard `pruefe_swap_ziel` lässt den Wiederholungsfall durch, wenn das Unfall-Residuum im Ziel liegt | fehlende Validierung | hoch | SURVIVES | `generate.py:106` `return` statt `sys.exit`; keine Testdatei in `tools/cc-skill-dist/` | neu |
| 3 | `[skip ci]` im Kopf-Commit blockierte #1503 37 h 56 min, danach #1559 erneut (12 min) | Werkzeug | hoch | SURVIVES | `dae483be` → 1 Check-Run; `8ed8c96e` → 7 Check-Runs | 2× in Session |
| 4 | Kein struktureller Schutz gegen literales `[skip ci]` im Repo | Prozesslücke | mittel | SURVIVES | 4 pre-commit-Hooks, keiner prüft Commit-Messages; `check-commit-msg.sh` liegt in `_archive/` | neu |
| 5 | Merge während laufendem Push verlor Commits → Folge-PR #1556 | Prozesslücke | hoch | SURVIVES | #1555 merged 07:29:48Z, Commit `41ad9d08` authored 07:37:10Z | 2× (29.07./30.07.) |
| 6 | dev-hub#172 koppelt Prod-Celery an `/opt/platform`-Bind-Mount ohne Tracking-Issue für die Wheel-Migration | Prozesslücke | mittel | SURVIVES | PR-Diff; Runbook nennt Weg (a) als sauberer; Issue-Suche in beiden Repos leer | ×6 org-weit |
| 7 | Ziel „acht Mails" ist aus keinem Artefakt verifizierbar — belegt sind 3 Entwürfe | fehlende Validierung | mittel | SURVIVES | `git grep -niE "acht mail\|8 mail"` → 0 Treffer im ganzen Baum | neu |
| 8 | `mail.iil.pet` war ~20 s ohne Auth erreichbar; Verifikation prüft nur einen Vantage Point | fehlende Validierung | mittel | SURVIVES | Runbook dokumentiert das Fenster selbst; `status()` ist ein einzelner lokaler `curl` | neu |
| 9 | 5 von 10 Session-Branches nach dem Merge nicht gelöscht | Prozesslücke | niedrig | SURVIVES | `git ls-remote --heads origin` aktuell geprüft | Memory existiert |
| 10 | Handover-Notiz „zweites Mal am selben Tag" ist faktisch falsch (29.07. vs. 30.07.) | fehlende Validierung | niedrig | SURVIVES | PR-Zeitstempel #1545/#1546 vs. #1555/#1556, ~19 h Abstand | ×31 org-weit |
| — | #1558 verstecke Security-Tooling hinter irreführendem Titel | — | — | **REFUTED** | Titel nennt `cf_access-Werkzeug` wörtlich; Body hat eigenen Abschnitt mit Risiko | — |
| — | MEiKI-Folgearbeit ohne Tracking-Artefakt | — | — | **REFUTED** | Handover nennt Board mit Pfad; Verzicht auf Issue folgt der LRA-Daten-Regel | — |
| — | #1503 gehört nicht zur Session | — | — | **REFUTED** | #1503 war der Ursprungsfall des `[skip ci]`-Befunds, der in derselben Session rezidivierte | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Ziele 1–3 belegt erreicht; Ziel 4 nicht verifizierbar (#7), Ziel 5 bewusst außerhalb des Repos |
| architektur_design | **3** | SSoT-Konsolidierung (#1562) und Stufen-Trennung gut; Guard-Logik lückenhaft (#2), Bind-Mount-Kopplung ungetrackt (#6) |
| code_konventionstreue | **2** | #1 ist ein Bug in gemergtem Prod-Code, dessen Pfad ungetestet blieb — obwohl der PR-Text die Absicherung ausdrücklich behauptete |
| risiko_debt | **2** | #2 dormant statt geschlossen, #6 ungetrackt, #8 Restrisiko, #9 Branchen offen |
| prozess_effizienz | **2** | #3 (37 h Blockade) und #5 (Merge-Race) erzeugten zwei Folge-PRs und einen Fix-Commit rein aus Koordinationsfehlern |
| entscheidungsqualitaet | **3** | Design-Rückzug nach Kundenrückmeldung war schnell und richtig; Stufen-Trennung bei MEiKI stark; aber die Schutzbehauptung in #1568 war ungeprüft |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `startswith(GRUSSFORMELN)` ohne Wortgrenze; Tests prüften nur plausible Grußsätze | Präfix-Heuristiken auf Wortgrenze matchen (`re.match(r"^(…)\b")`) **und** je Heuristik einen Test mit einem Wort schreiben, das mit dem Muster *beginnt*, aber es nicht *ist* | #1 |
| Guard erlaubt Swap bei vorhandenem `MANAGED_BY`, egal woher es stammt | Marker-Inhalt gegen die aufrufende Lane prüfen (`kind=`-Zeile), nicht nur den Dateinamen; Test mit kontaminiertem Zielverzeichnis | #2 |
| Marker `[skip ci]` im Commit-Body zitiert → keine Läufe, PR blockiert ohne rot zu werden | Beim Schreiben ÜBER einen CI-Steuermarker den Wortlaut in der Commit-Message vermeiden — umschreiben statt zitieren | #3 |
| Kein Repo-Schutz gegen literales `[skip ci]`: vier pre-commit-Hooks, keiner prüft Messages | Pre-commit-Hook ergänzen, der den literalen Marker in der Commit-Message ablehnt, außer der Commit trägt einen ausdrücklichen Opt-in-Trailer | #4 |
| Merge erfolgte, während noch Commits gepusht wurden | Vor jedem Merge-Vorschlag den Branch-Head nennen (`fertig gepusht, N Commits, Head <sha>`) — und beim Review-Handoff explizit bestätigen lassen | #5 |
| Bind-Mount gewählt, Alternative nur im Runbook-Fließtext erwähnt | Beim Wählen der schnelleren von zwei dokumentierten Optionen im selben Zug ein Issue für die sauberere anlegen — Runbook-Prosa ist kein Tracking | #6 |
| Ziel „acht Mails" nur im Gesprächsverlauf, in keinem Artefakt | Mail-Batch-Ziele mit Stückzahl im Mail-Board als Zähler führen (`n/m erledigt`), damit Zielerreichung ohne Postfachzugriff prüfbar ist | #7 |
| Access-Durchsetzung von genau der Maschine geprüft, die den Tunnel hostet | Gegenprobe zusätzlich von einem zweiten Netzpfad (z. B. `curl` über einen anderen Host oder Cloudflare-Worker), bevor „Fertig" gemeldet wird | #8 |
| Merges ohne `--delete-branch`, Reaper räumt nur lokale Worktrees | Repo-weit „Delete branch on merge" aktivieren, damit Hygiene nicht an der Aufrufform hängt | #9 |
| „Zweites Mal am selben Tag" geschrieben, ohne die Daten der Vorkommen zu prüfen | Bei jeder Wiederholungs-Behauptung die Zeitstempel beider Vorkommen ziehen, bevor der Satz steht — genau der Check, den `claim-before-cheapest-check` fordert | #10 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` ausgeführt. Relevante Treffer für diese Session:

| Slug | Zähler | Status |
|---|---|---|
| `claim-before-cheapest-check` | ×30 → **×31** | 🚨 GATE-PFLICHT, Befund #10 ist das nächste Vorkommen |
| `deferred-item-no-tracking-issue` | ×5 → **×6** | 🚨 GATE-PFLICHT, Befund #6 ist das nächste Vorkommen |
| `branch-cleanup-missing-after-merge` | Memory belegt vorhanden | Befund #9; `feedback_branch_cleanup_squash_worktree.md` per `ls` verifiziert |

`refuted_rate`-Band: 0,23 liegt im gesunden Korridor (Vorgänger 0,35 · 0,21 · 0,13 · 0,22 · 0,07 · 0,13 · 0,05 · 0,22).

**Der eigentliche Befund des Längsschnitts:** `claim-before-cheapest-check` steht bei 31 Vorkommen und ist seit Langem gate-pflichtig — es gibt einen Stop-Hook (`evidence_claim_scanner.py`), der Verifikations- und Deploy-Marker fängt. Befund #10 ist eine Variante, die er nicht fängt: eine **Wiederholungs-Behauptung über zwei Zeitpunkte** („zweites Mal am selben Tag"). Das ist dieselbe Familie wie die 2026-07-02-Erweiterung um Punkt 5 (Verifikations-Query ≠ Implementierungs-Query) und die 2026-07-15-Erweiterung um Root-Cause-Labels: ein drittes Muster, das der Marker-Scanner strukturell nicht sieht.

## 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | 0 | Kein Fall gefunden, in dem etwas Deterministisch-Reversibles vorgelegt statt getan wurde. Die drei Stopps (Secret auf Prod, Prod-Compose-Edit, Merge in Deploy-on-push-Repo) waren Classifier-Blocks, keine freiwillige Vorlage |
| `over_act` | 0 | Alle Prod-Schritte hatten ausdrückliche Freigabe: Ingest-Aktivierung („ja"), `--admin`-Merge (URL + „--admin"), `mail.iil.pet` (per `!` selbst ausgeführt) |

Die Gate-Liste in `feedback_autonomy_charter` braucht aus dieser Session keine Verschiebung. **Anmerkung zur Kalibrierung:** Der `~/.claude`-Verlust war kein Autonomie-Fehler — die Aktion lag unterhalb aller fünf Gates (lokales Verzeichnis, kein Prod, reversibel). Er war ein Sorgfaltsfehler. Die Gate-Liste vor solchen Fällen zu erweitern, wäre die falsche Lehre; der Guard im Werkzeug ist die richtige.

## 6. Verankerung

### memory_candidates

```markdown
---
name: feedback-prefix-heuristic-needs-word-boundary
description: "startswith() auf Grußformeln/Präfixlisten ohne Wortgrenze löscht Fließtext — 'Grüße deine Frau' matcht 'grüße' (2026-07-31)"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-grussformel-praefix
---

Eine Präfix-Heuristik über natürlichsprachliche Marker (`str.startswith(GRUSSFORMELN)`)
prüft **keine Wortgrenze**. `"grüße deine frau von mir".startswith("grüße")` ist `True` —
und in `roles._ohne_doppelten_namen` löschte das die Folgezeile aus einer versandfertigen
Mail. Reproduziert am 2026-07-31 gegen `origin/main`.

**Der Fehler lag nicht in der Idee, sondern in der Testauswahl:** die sechs Tests prüften
plausible Grußsätze („Herzliche Grüße", „Viele Grüße") und einen Fließtext-Fall ohne
Grußformel davor. Kein Test prüfte ein Wort, das mit dem Muster **beginnt**, aber es nicht
**ist**. Genau dieser Fall ist der einzige, der die Heuristik falsifizieren kann.

**Regel:** Zu jeder Präfix-/Substring-Heuristik gehört ein Test mit einem Wort, das das
Muster als echtes Präfix enthält. Und: `re.match(r"^(…)\b")` statt `startswith`.

Verwandt: [[feedback_dry_run_does_not_cover_write_path]]
```

```markdown
---
name: feedback-guard-blind-to-own-residue
description: "Ein Guard, der auf Marker-Dateien prüft, ist blind gegen den Unfall, der genau diese Marker hinterlässt (2026-07-31)"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-guard-residuum
---

`pruefe_swap_ziel` (platform#1558) erlaubt einen Verzeichnis-Swap, sobald `MANAGED_BY`
oder `manifest.json` im Ziel liegen — „stammt aus einem früheren Lauf". Der Unfall, gegen
den der Guard gebaut wurde, schreibt genau diese zwei Dateien in das falsche Verzeichnis.
Bleiben sie liegen, winkt der Guard denselben Tippfehler beim zweiten Mal durch.

**Merksatz:** Ein Guard, dessen Erkennungsmerkmal vom Fehler selbst erzeugt wird, schützt
nur beim ersten Mal. Prüfe den **Inhalt** (gehört der Marker zu dieser Lane?), nicht die
Existenz des Dateinamens.

Auf der betroffenen Maschine derzeit dormant — die Marker wurden bei der Wiederherstellung
entfernt (per `ls` verifiziert). Die Logiklücke besteht fort.

Verwandt: [[feedback_generate_target_swaps_whole_directory]]
```

```markdown
---
name: feedback-skip-ci-literal-in-message-blocks-checks
description: "Wer über [skip ci] schreibt, darf ihn nicht in der Commit-Message zitieren — GitHub liest den Wortlaut (2026-07-31)"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-skip-ci-zitat
---

Ein Commit, dessen Message den Marker `[skip ci]` **zitiert** (weil der Text über ihn
schreibt), löst denselben Effekt aus wie einer, der ihn setzt: GitHub startet keinen
`pull_request`-Lauf, die Required Checks melden nie, der PR bleibt `BLOCKED` — **ohne rot
zu werden**. Kein Fehlsignal, nur Stillstand.

Belegt am 2026-07-31 an zwei Vorfällen: platform#1503 blieb 37 h 56 min blockiert
(Kopf-Commit `dae483be`: 1 Check-Run; Folgecommit `8ed8c96e`: 7 Check-Runs), platform#1559
12 Minuten. Beide Male war der Marker reiner Fließtext.

**Regel:** Über den Marker schreiben ist im Dateitext harmlos, in der Commit-Message nicht.
Ein Repo-Schutz dagegen existiert nicht (4 pre-commit-Hooks, keiner prüft Messages).

Verwandt: [[feedback_required_check_paths_filter_blocks]], [[feedback_blocked_without_any_pull_request_run]]
```

### adr_candidates

Keine. Alle Befunde sind Werkzeug- oder Prozessfehler ohne Architektur-Entscheidung — nach
`adr-threshold.md` genügen Fix-PR und CHANGELOG/Memory.

## 7. Maßnahmen

### 🔵 Sofort umsetzbar

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Wortgrenze in `_ohne_doppelten_namen` | platform | — | 🔵 ready | Fix + Test (ich) |
| 2 | Guard prüft Marker-Inhalt | platform | — | 🔵 ready | `kind=`-Abgleich (ich) |
| 3 | Pre-commit-Hook gegen literales `[skip ci]` | platform | — | 🔵 ready | Hook + Opt-in-Trailer (ich) |
| 4 | Issue für Wheel-Migration | dev-hub | — | 🔵 ready | anlegen (ich) |

### 🟢 Owner-Entscheidung

| # | Item | Repo | Status | Next Step |
|---|---|---|---|---|
| 5 | „Delete branch on merge" repo-weit | platform | 🟢 offen | Setting aktivieren (du) |
| 6 | Zweiter Vantage Point für Access-Proben | platform | 🟢 offen | Weg festlegen (du) |

## 8. Nicht verifiziert (Restlücken)

| Was | Warum offen | Billigster Check |
|---|---|---|
| Ob der Prod-Ingest-Lauf am 31.07. 03:30 tatsächlich sauber durchlief | Retro-Scope ist git-only; Prod-DB/Logs nicht geprüft | `ssh hetzner-prod "docker logs devhub_celery --since 8h \| grep mail_ingest"` |
| Ob die drei versendeten Mails beim Empfänger korrekt gerendert ankamen | Nur das erzeugte HTML wurde gemessen, nicht das Rendering | Empfänger fragen oder Testmail an ein Zweitkonto |
| Ob Befund #1 bereits eine reale Mail beschädigt hat | Die drei versendeten Mails wurden vor dem Merge von #1568 erzeugt | Gesendet-Ordner gegen die Entwurfstexte diffen |
| Ob `claim-before-cheapest-check` ×31 den Stop-Hook erweitern sollte | Hook-Logik nicht gelesen | `~/.claude/hooks/evidence_claim_scanner.py` lesen |
