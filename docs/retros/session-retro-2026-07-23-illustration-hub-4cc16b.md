---
retro_schema: 1
date: 2026-07-23
repo_scope: [illustration-hub, writing-hub, iil-reflex]
session_id: 4cc16b
footprint: deep
findings_total: 17
findings_survived: 8
findings_unverified: 3
refuted_rate: 0.35
phase3_refuted: 4
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
over_ask: 0
over_act: 0
gate_candidates:
  - deploy-green-not-prod-healthy
  - idempotency-contract-without-db-constraint
  - integration-verified-only-after-merge
recurring_findings:
  - deferred-item-no-tracking-issue
  - handover-stale-vor-merge
  - deploy-green-not-prod-healthy
  - autonomous-no-human-review
  - scope-checkpoint-not-durably-recorded
---

# Session-Retro 2026-07-23 — illustration-hub / writing-hub / iil-reflex

**Footprint:** deep (3 Repos · 29 gemergte PRs · 5 Migrationen · 1 neues ADR · mehrere
Prod-Deploys + manuelle Prod-Eingriffe). Kein Downscale: DB-Migrationen schließen die
Reduktionsregel aus.

**Pipeline:** 1 Collector (haiku) · 3 Finder (sonnet) · 3 Skeptiker (sonnet) · Synthese inline
· 1 Meta-Reviewer (sonnet).

**Zählbasis `findings_total: 17`** (explizit, weil der Meta-Review hier einen Zählfehler fand):
15 Finder-Befunde (3 Soll-Ist + 5 Code + 7 Prozess) **plus** 2 Collector-Hypothesen, die
schon vor Phase 3 fielen. Davon 12 zur Falsifikation geroutet → 8 SURVIVES, 4 REFUTED;
**3 Finder-Befunde wurden nicht geroutet** (mein Phase-2.5-Fehler) und stehen unten mit
Verdikt `NICHT GEPRÜFT` — sie zählen weder als überlebend noch als widerlegt.
`refuted_rate = (4+2)/17 = 0.35`. Echte Falsifikations-Quote (Skeptiker-Schärfe):
`phase3_refuted / (findings_total − pre_refuted − unverified) = 4/12 = 0.33`.

## 1. Executive Summary

- **Das Kernziel wurde erreicht und ist live verifiziert.** Die Funktionalität „Buch mit
  Bildern illustrieren" existierte in drei getrennten, unverbundenen Ständen; am Ende
  läuft eine durchgängige Kette writing-hub → illustration-hub in Prod (Panel-Smoke 200).
- **Der teuerste Fehler war nicht im Code, sondern in der Reihenfolge:** drei
  Infrastruktur-Blocker (Cloudflare-403, Django-Unterstrich-Host, SSL-Redirect) wurden
  einzeln *nach* je einem Prod-Merge entdeckt — vier PRs für eine Verbindung.
- **Ein Deploy-Failure lief unbemerkt durch** (PR #55, containerd-Snapshot-Fehler,
  automatischer Rollback). Kein Issue, kein Re-Run — der Commit war 8 Minuten nicht live
  und wurde nur zufällig vom nächsten, inhaltlich unabhängigen Deploy nachgezogen.
- **Die zentrale Idempotenz-Behauptung ist nicht strukturell gedeckt:** `source_ref`
  trägt keinen (partiellen) Unique-Constraint — „kein Duplikat" hängt an Client-Disziplin.
- **Falsifikation hat gearbeitet:** 4 von 12 *geprüften* Befunden wurden widerlegt (3 weitere blieben ungeprüft, s. §8), darunter
  zwei, die als „hoch" eingestuft waren. Zwei weitere Collector-Hypothesen fielen schon
  vor Phase 3.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | ADR-201 §5 verpflichtet zu Tracking-Issues M1+M6 „bei Slice-4-Merge (selber Turn)" — keins existiert; PR #357 schreibt selbst „bleiben in §5 getrackt" | Prozesslücke | hoch | SURVIVES | ADR-201 §5 (`origin/main`); Slice 4 = writing-hub#356 merged 15:58:47; 115 Issues über 3 Repos durchsucht → 0 Treffer | `deferred-item-no-tracking-issue` ×3→**4** (Gate aktiv) |
| 2 | Deploy-Run zu PR #55 (`5f7c613`) `failure` + Auto-Rollback; kein Issue, kein Re-Run (`attempt:1`), 8 Min 6 Sek nicht live; Gate eskaliert erst ab 2 konsekutiven Failures | Werkzeug / Observability | hoch | SURVIVES | Run 30017877081 Log `failed to prepare extraction snapshot`; Deploy-Failure-Gate-Log `Consecutive deploy failures on main: 1`; nächster Erfolg Run 30018585596 (PR #60, inhaltlich unabhängig) | `deploy-green-not-prod-healthy` ×1→**2** ⇒ NEU gate-pflichtig |
| 3 | `IllustrationJob.source_ref` ohne Unique-Schutz — Outbox-Lite-Idempotenz nur durch Client-Disziplin garantiert; `find_job` liefert `results[0]`, ältere Duplikate würden unsichtbar | Datenintegrität | hoch | SURVIVES | `origin/main:apps/jobs/models.py` (kein `unique`, `Meta` ohne `constraints`); `0001_initial.py` + Folge-Migrationen ohne Constraint; `perform_create` ohne Dedup-Check | neu: `idempotency-contract-without-db-constraint` |
| 4 | Vier-PR-Rework-Kette für EINE Verbindung; jeder Fehler erst nach Prod-Merge entdeckt. Fehler 1 (Cloudflare) und 2 (Unterstrich) waren *nicht* voneinander abhängig | Verifikationsreihenfolge | mittel-hoch | SURVIVES | writing-hub#348 → illustration-hub#60 → #61 → writing-hub#350; PR-Body #61 wörtlich: „Die naheliegende Erklärung (ALLOWED_HOSTS) war **falsch**"; Sequenz-Abhängigkeit nur 2→3 (SecurityMiddleware ruft `get_host()`) | neu: `integration-verified-only-after-merge` |
| 5 | `AGENT_HANDOVER.md` (writing-hub) enthält auf `origin/main` den falschen Unterstrich-Wert `http://illustration_web:8000` — 13 Zeilen über der Erklärung, warum genau dieser Wert scheitert. Auch der offene PR #357 korrigiert ihn nicht | Kommunikation | mittel | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` Z.26 vs. Z.37-39; PR #357 lässt Z.26 unangetastet | `handover-stale-vor-merge` ×11→**12** (Gate aktiv) |
| 6 | 11 PRs mit „⚠️ Merge löst Prod-Deploy aus" im eigenen Body, alle ohne Review-/Approval-**Artefakt** gemergt. Ob eine Chat-Freigabe vorlag, ist aus Artefakten **nicht** entscheidbar | Kommunikation | mittel | SURVIVES | `gh pr view` je PR: `reviewDecision:""`, `reviews:[]`, `comments:[]` (illustration-hub #55/57/58/60/61; writing-hub #98/345/346/348/350/356) | `scope-checkpoint-not-durably-recorded` (Gate aktiv) · `autonomous-no-human-review` (Gate aktiv) |
| 7 | View ruft private `service._mark()` — einziger externer Aufrufer einer als intern markierten Methode; keine öffentliche Alternative vorhanden | Kapselung | mittel | SURVIVES | `origin/main:apps/illustration/views.py:39` vs. `services/service.py:163` (`staticmethod`, Abschnitt „-- intern --") | neu |
| 8 | `get_or_create_slot()` ohne `full_clean()` — Kapitel-Invariante nur durch den einen Call-Pfad geschützt, keine DB-`CheckConstraint`; künftiger bfagent-Import (M6) hätte kein Netz | Invarianten-Design | niedrig-mittel | SURVIVES | `services/service.py` (`get_or_create` ohne `full_clean`) vs. `select_candidate` (mit); `models.py` `Meta.constraints` nur `unique_slot_placement`; `git grep` → 1 Caller | neu |
| 9 | „Prio 1 (#18 panel_review) komplett unbearbeitet, kein Commit/PR referenziert #18" | — | — | **REFUTED** | PR #55 = Slice 2 desselben Zwei-Screen-Blockers; `screens-spec.yaml:196` + ADR-002 + Handover nennen #18 explizit | — |
| 10 | „ADR-Frontmatter `partial` trotz gemergtem Slice 4 = Doku-Drift" | — | — | **REFUTED** | Korrektur-PR #357 kam 10 Min nach Slice-4-Merge, CI grün; Body zitiert `claim-before-cheapest-check` — regelkonformes Sequencing, nicht Vergessen | — |
| 11 | „iil-reflex PR #34 ohne Regressionstest" | — | — | **REFUTED** | Finder-Glob filterte Dateinamen auf `adr`; Test liegt in `tests/test_review_plugins.py` (`test_should_accept_decision_date_as_date`), im selben PR (+26 Z.) | — |
| 12 | „illustration-hub `main` hat GAR KEINEN Branch-Schutz (404)" | — | — | **REFUTED** | 404 nur auf dem Legacy-Endpoint; Ruleset `main-required-checks` (id 18711447) aktiv, `ci / gate` required, `current_user_can_bypass: never` | — |
| 13 | `resolve_unknown` hat keinen automatischen Trigger, nur ein Management-Command — `unknown`-Kandidaten bleiben bis zum manuellen Lauf hängen | Operational Gap | mittel | **NICHT GEPRÜFT** | Finder-Beleg: `illustration_reconcile.py` Docstring „kein Cron-Zwang"; kein Skeptiker-Pass geroutet | — |
| 14 | Branch `session-ende-handover` für drei inhaltlich verschiedene PRs (#59/#60/#61) wiederverwendet | Branch-Hygiene | niedrig-mittel | **NICHT GEPRÜFT** | Finder-Beleg: identischer `headRefName` bei #59/#60/#61; kein Skeptiker-Pass geroutet | — |
| 15 | Anbieter→Konsument-Reihenfolge (ADR-201 §4.1) nur mit 16 s Puffer eingehalten, ohne Gate | Prozessdisziplin | niedrig | **NICHT GEPRÜFT** | Finder-Beleg: illustration-hub#58 merged 13:49:47 vs. writing-hub#346 merged 13:50:03; kein Skeptiker-Pass geroutet | — |
| — | *(pre-refuted, vor Phase 3)* Concurrency-Kollision Run #237/#238 | — | — | REFUTED | Production-Jobs überlappen zeitlich nicht (14:53:26 vs. 14:56:11) | — |
| — | *(pre-refuted, vor Phase 3)* Force-Push auf writing-hub PR #344 | — | — | REFUTED | `issues/344/events` ohne `head_ref_force_pushed`; kein solches Event im ganzen Repo an dem Tag | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Cross-Repo-Ziel end-to-end live + Prod-Smoke belegt; Abzug: PR #357 blieb zum Sessionende offen, #18 weiterhin offen (Schwenk aber owner-legitimiert, Befund 9 REFUTED) |
| architektur_design | **3** | Schnitt B′ von zwei externen Reviews bestätigt; aber drei reale Lücken: Idempotenz ohne DB-Deckung (#3), Invariante ohne Constraint (#8), Kapselungsbruch (#7) |
| code_konventionstreue | **4** | Kein `except:`/`print()`, `test_should_*` durchgehend, Migrationen additiv, kein Tenant-Leck; Abzug: #7 bricht die eigene Service-Layer-Konvention |
| risiko_debt | **2** | Drei offene Risiken zum Sessionende: fehlende Tracking-Issues (#1), unbemerkter Deploy-Failure ohne Nachverfolgung (#2), falscher Befehl steht weiter im Handover (#5) |
| prozess_effizienz | **3** | Vier PRs + vier Prod-Deploys für eine Verbindung (#4); Reihenfolge-Disziplin Anbieter→Konsument nur mit 16 s Puffer und ohne Gate |
| entscheidungsqualitaet | **4** | ADR-201 mit zwei externen Reviews, vollständiger Tag-Tabelle, right-sized Ablehnungen; Statuswechsel erst nach Prod-Evidenz (Befund 10 REFUTED bestätigt die Disziplin) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (konkreter besserer Schritt) | eliminiert |
|---|---|---|
| ADR-201 §5 sagt „Issue bei Slice-4-Merge (selber Turn)"; #356 wurde gemergt, kein Issue folgte; #357 schrieb stattdessen „bleiben in §5 getrackt" | Beim Anlegen einer §5-Zeile mit Termin-Zusage **sofort** das Issue eröffnen und die Zeile mit der Issue-Nummer schreiben — eine Zusage ohne Nummer ist kein Tracking. Für ADRs mit `M<n>`-Tabelle: CI-Check, der jede Zeile mit „Issue bei …" gegen eine tatsächlich existierende Issue-Referenz prüft | #1 |
| Nach `gh pr merge` wurde der Deploy-Status nur am Sessionende und nur für den *letzten* Run geprüft; Run #238 fiel durchs Raster | Nach **jedem** Merge in ein Auto-Deploy-Repo: `gh run watch <deploy-run-id> --exit-status` für **genau diesen** SHA, bevor der nächste Merge folgt. Zusätzlich Deploy-Failure-Gate von „≥2 konsekutiv" auf „1× Failure ⇒ Kommentar-Artefakt am auslösenden PR" nachschärfen | #2 |
| `source_ref` wurde als Idempotenz-Anker eingeführt, ohne die Eindeutigkeit in der DB zu verankern | Beim Einführen eines Idempotenz-Ankers im selben PR einen **partiellen** `UniqueConstraint` (`condition=Q(source_ref__gt='')`) + einen Test „zweiter Job mit gleichem source_ref wird abgelehnt" mitliefern | #3 |
| Die Integration wurde gebaut, gemergt, und *dann* in Prod erprobt — dreimal hintereinander | **Vor** dem ersten Integrations-Merge einen Live-Call aus dem Zielcontainer gegen den laufenden Anbieter fahren (Netz/Env manuell vorbereiten, `curl` absetzen, Ergebnis in den PR-Body). Erst danach Code committen | #4 |
| PR #353 ergänzte den Fix-Kontext im Handover, ohne den widersprechenden älteren Absatz (Z.26) zu korrigieren | Beim Handover-Update: neue Aussage gegen bestehende Aussagen **derselben Datei** prüfen („widerspricht das einer Zeile weiter oben?") und Widersprüche im selben Commit auflösen, statt additiv anzuhängen | #5 |
| 11 Prod-wirksame Merges tragen die Prod-Warnung im Body, aber keinen Freigabe-Vermerk im Artefakt | Bei erteilter Freigabe für einen Prod-Merge **im selben Zug** einen Einzeiler in den PR-Body/Kommentar schreiben („Freigabe Owner, <Datum>, Wortlaut: …") — die Chat-Freigabe wird sonst beim Audit unsichtbar | #6 |
| Die View brauchte „Kandidat als failed markieren" und griff auf `service._mark()` zu | Wenn eine View eine interne Service-Operation braucht: eine **öffentliche** Methode dafür ergänzen (`mark_failed()`), nicht die private aufrufen — der Bedarf ist das Signal, dass die Service-API unvollständig ist | #7 |
| `get_or_create_slot()` verlässt sich darauf, dass der einzige Caller vorfiltert | Invarianten, die im Modell als `clean()` stehen, in der Service-Methode per `full_clean()` **oder** als DB-`CheckConstraint` erzwingen — spätestens dann, wenn im selben ADR ein zweiter Schreibpfad (M6-Import) angekündigt ist | #8 |

Invariante erfüllt: 8 Soll-Schritte für 8 überlebende Befunde.

## 5. Längsschnitt

**Quelle (reproduzierbar):** `cd ~/github/platform && python3 tools/retro_kpis.py` —
Lauf vom 2026-07-23 über 51 Reports in `docs/retros/`. Alle Zahlen unten stammen aus
dessen stdout, nicht aus Erinnerung.

| Slug | Zähler | Status |
|---|---|---|
| `deferred-item-no-tracking-issue` | ×3 → **×4** | Gate bereits pflichtig — Befund #1 ist das vierte Vorkommen |
| `handover-stale-vor-merge` | ×11 → **×12** | Gate bereits pflichtig — Befund #5 ist das zwölfte Vorkommen |
| `deploy-green-not-prod-healthy` | ×1 → **×2** | **NEU gate-pflichtig** durch Befund #2 |
| `autonomous-no-human-review` | gate-pflichtig | Befund #6 |
| `scope-checkpoint-not-durably-recorded` | gate-pflichtig | Befund #6 |

`refuted_rate`-Trend (stdout-Zeile „refuted_rate-Trend"): `11feac:0.25 · 8d663b-incr:0.00 ·
8d663b:0.27 · 8b6a14:0.08 · 8b13a7:0.20 · 20ef83-incr:0.00 · 20ef83:0.11 · 830d27:0.21`
→ **0.35** heute.
Band gesund; der Anstieg kommt daher, dass zwei „hoch"-Befunde und ein Governance-Befund
widerlegt wurden — die Skeptiker haben real gearbeitet, nicht abgenickt.

**Score-Vergleich zum Fleet-Mittel** (stdout-Block „Score-Mittel je Dimension", n=51):
`risiko_debt` **2** vs. Ø **2.65** — schwächer als der ohnehin schwächste Fleet-Wert
(zum Vergleich: zielerreichung Ø 3.88, architektur_design Ø 3.67, prozess_effizienz Ø 3.06). Das ist konsistent mit den drei offen gebliebenen Risiken.

## 5b. Autonomie-Kalibrierung

`over_ask: 0` · `over_act: 0` — **beide nicht aus Artefakten bestimmbar.**

Der Prozess-Skeptiker hat das explizit benannt: aus PR-Artefakten allein lässt sich nicht
unterscheiden zwischen „keine Freigabe erfolgte" und „Freigabe erfolgte im Chat, wurde
nicht ins Artefakt geschrieben". Der Merge-Akteur ist der menschliche GitHub-Account.

**Der belastbare Befund ist deshalb nicht `over_act`, sondern die fehlende Durabilität der
Freigabe** (Befund #6) — und genau dafür existiert bereits der gate-pflichtige Slug
`scope-checkpoint-not-durably-recorded`. Die Charter-Schärfung sollte an dieser Stelle
ansetzen: nicht „weniger autonom mergen", sondern „erteilte Freigabe im selben Zug
durabel vermerken".

## 6. Verankerung (Vorschläge — nicht von mir geschrieben)

### memory_candidates

```markdown
---
name: feedback-deploy-status-per-merge-not-per-session
description: Nach JEDEM Merge in ein Auto-Deploy-Repo den Deploy-Run für genau diesen SHA prüfen — nicht nur den letzten Run am Sessionende
metadata:
  type: feedback
drift: true
drift_episode: 2026-07-23-deploy-238-unbemerkt
---

Ein Deploy-Failure blieb unbemerkt, weil der Deploy-Check am Sessionende nur den
*letzten* Run ansah — der war grün, weil ein späterer, inhaltlich unabhängiger Merge
zufällig durchlief.

**Why:** illustration-hub Run 30017877081 (PR #55, SHA 5f7c613) scheiterte an einem
containerd-Snapshot-Fehler und rollte automatisch zurück. Das Deploy-Failure-Gate
eskaliert erst ab 2 konsekutiven Failures (Log: „Consecutive deploy failures on main: 1"),
Discord-Notify ist ephemer. Ergebnis: 8 Min nicht live, kein Issue, kein Re-Run,
Selbstheilung durch Zufall.

**How to apply:** Nach `gh pr merge` in einem Auto-Deploy-Repo sofort
`gh run watch <run-id> --exit-status` für den **eigenen** SHA, bevor der nächste Merge
folgt. „main grün" und „letzter Run grün" sind beide **kein** Beleg, dass der eigene
Commit live ist. Siehe [[feedback-terse-solution-output]] für die Berichtsform.
```

```markdown
---
name: feedback-integration-probe-before-first-merge
description: Cross-Service-Integration vor dem ersten Merge live sondieren, nicht danach in Prod debuggen
metadata:
  type: feedback
drift: true
drift_episode: 2026-07-23-vier-pr-kette
---

Vier PRs über zwei Repos, jeder mit eigenem Prod-Deploy, waren nötig, um eine einzige
Service-Verbindung zum Laufen zu bringen — jeder Blocker wurde erst *nach* einem Merge
sichtbar.

**Why:** Cloudflare antwortet Container-Requests mit 403 (Host: 200) · Django lehnt
Hostnamen mit Unterstrich ab, *unabhängig* von ALLOWED_HOSTS · SECURE_SSL_REDIRECT
schickt interne http-Calls auf https ohne TLS. Nur Fehler 2→3 hingen sequenziell
zusammen; Fehler 1 und 2 wären in einer einzigen Sondierung gemeinsam gefunden worden.

**How to apply:** Vor dem ersten Integrations-Merge Netz/Env manuell herstellen und
**einen echten Call aus dem Zielcontainer** absetzen (`docker exec <consumer> curl …`).
Das Ergebnis in den PR-Body. Erst danach Code schreiben. Kosten: 2 Minuten gegen hier
vier Deploy-Zyklen.
```

### adr_candidates

Kein neues ADR nötig. Die drei Code-Befunde (#3, #7, #8) sind Umsetzungslücken *innerhalb*
von ADR-201, kein Architektur-Reversal — sie gehören als Issues in writing-hub bzw.
illustration-hub, plus eine Präzisierung in ADR-201 §8 (Confirmation), dass der
Idempotenz-Anker eine DB-Constraint braucht.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 PR #357 mergen (ADR-201 → `implemented`), dabei Handover-Z.26 mitkorrigieren — https://github.com/achimdehnert/writing-hub/pull/357
2. 🟢 Gate-Entscheid: Deploy-Failure-Gate auf „1× Failure ⇒ PR-Kommentar" nachschärfen (neu gate-pflichtig) — file:///home/devuser/github/illustration-hub/.github/workflows/

### 🔵 Offen — ich kann sofort

3. 🔵 Issues M1 + M6 anlegen und ADR-201 §5 mit Nummern nachziehen — Befund #1
4. 🔵 Issue: partieller `UniqueConstraint` auf `source_ref` + Dedup-Test — Befund #3
5. 🔵 Issue: öffentliche `mark_failed()` statt `_mark()` aus der View — Befund #7
6. 🔵 Issue: `full_clean()` in `get_or_create_slot()` oder DB-CheckConstraint — Befund #8
7. 🔵 Handover-Z.26 (Unterstrich-Wert) korrigieren — Befund #5

### ✅ Erledigt

| # | Item | Status |
|---|---|---|
| 8 | ADR-201 accepted + Slices 0/0b/1/2/3/4 in Prod, Panel-Smoke 200 | ✅ |
| 9 | iil-reflex-Fehlalarm behoben (228→0 falsche BLOCKs) | ✅ |

## 8. Nicht verifiziert (Restlücken)

| Lücke | Billigster Check |
|---|---|
| **Drei Finder-Befunde wurden nicht zur Falsifikation geroutet** (mein Fehler in Phase 2.5) — jetzt als #13/#14/#15 mit Verdikt `NICHT GEPRÜFT` in §2 geführt, in `findings_total` gezählt, aber weder als SURVIVES noch als REFUTED | Je ein Skeptiker-Pass mit unabhängig gezogenem Beleg |
| Ob die 11 Prod-Merges eine Chat-Freigabe hatten, ist artefaktseitig unentscheidbar (Befund #6) | Nur über das Session-Transkript — daher als Hypothese geführt, nicht als `over_act` gewertet |
| Ursache des containerd-Snapshot-Fehlers (Hypothese des Finders: paralleler Build/Pull auf demselben self-hosted Host) ist **nicht** bewiesen | `gh run view` beider Runs mit Job-Timestamps + Runner-Auslastung zum Zeitpunkt |
| 17 writing-hub-PRs und 21 platform-PRs desselben Tages sind vermutlich **fremde Parallel-Sessions** und wurden nicht bewertet | Abgleich gegen die Turn-Historie der jeweiligen Session |
| Phase 6 (anbieter-fremder Extern-Handoff) wurde nicht durchgeführt | Briefing nach `~/shared/` schreiben, extern einholen |
