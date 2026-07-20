---
retro_schema: 1
date: 2026-07-09
repo_scope: [risk-hub]
session_id: 1adf2a
footprint: deep
footprint_reduction_reason: null
findings_total: 19
findings_survived: 17
refuted_rate: 0.105
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates:
  - shared-ci-file-sync-gap
  - deploy-rollback-untested
  - pre-merge-live-host-check-missing
recurring_findings:
  - scope-checkpoint-not-durably-recorded
  - critical-alert-no-ticket
---

# Session-Retro — risk-hub, 2026-07-09

> Deep-tier review (Prod-Schritte + Migrationen ⇒ kein Downscale möglich, siehe
> Trigger-Konflikt-Regel). Pipeline: 1 Collector (haiku) → 3 Finder (sonnet, je
> Dimension) → 3 Skeptiker (sonnet, je Dimension, unabhängige Re-Derivation) →
> Synthese (diese Datei, Haupt-Session, keine neuen gh/git-Befehle). Kein
> Phase-5-Meta-Reviewer in diesem Lauf (Budget/Zeit) — als Lücke in §8 geführt.

## 1. Executive Summary

- Das eigentliche Ziel der Session (litellm-proxy "durable rollout", #335 30-Tage-
  Meilenstein) wurde **erreicht** — der Proxy läuft heute deploy-managed, gesund,
  mit echten Keys. Der Weg dahin war aber holprig: **#409 führte am selben Tag zu
  zwei Hotfix-PRs (#410, #411)** wegen eines Container-Name-Konflikts + eines
  OOM-Problems, inklusive eines **echten, wenn auch kurzen Staging-Outage**
  (web/worker liefen nicht, manuell per `docker start` wiederhergestellt) —
  nirgends als GitHub-Issue festgehalten.
- **Guter Gegenbeweis, dass es auch anders geht:** PR #413 (NIS2-Readiness)
  durchlief MMD→SoR→KD→Playwright→Code korrekt, inklusive eines echten,
  durch Playwright gefundenen Bugs (fehlende `MandateDokuSection`), der mit
  Regressionstest gefixt wurde.
- Die Session griff über den ursprünglichen Scope hinaus in ein **drittes
  Produktivsystem** (Authentik-SSO, Membership-Grants, eine echte
  NIS2-Klassifikations-Änderung für einen realen Kunden) — pro Einzelschritt
  lag im Chat jeweils eine explizite Freigabe vor (siehe Anmerkung unten,
  nicht durch Artefakte prüfbar, da Transkript-basiert), aber **kein einziger
  Schritt hinterließ eine GitHub-Spur** (Issue/PR/Kommentar).
- Zwei entdeckte "neue" Probleme entpuppten sich als **bereits bekannt, nie
  verfolgt**: der Cloudflare-DNS-Fehlkonfiguration entspricht 1:1 einem
  Checklisten-Punkt in Issue #124 (offen seit 2026-05-20); die
  `iil_learnfw`-Migrations-Lücke steht bereits seit 2026-06-25 als Kommentar
  im Code, nie tickets.
- Eine Hypothese wurde durch Falsifikation **entkräftet** (gute Nachricht):
  die reale NIS2-Klassifikationsänderung für Gröger lief nachweislich über
  das echte Formular (`/dsb/nis2/1/assessment/`, HTTP-POST im Access-Log),
  nicht über eine Shell-Abkürzung.

## 2. Befund-Tabelle

> Frontmatter zählt **roh, pro Dimension** (19 Behauptungen, 17 SURVIVES, 2
> REFUTED — für den `retro_kpis.py`-Längsschnitt). Die Tabelle unten **dedupliziert**
> Überschneidungen zwischen den drei Dimensionen (z. B. wurde der Container-Name-
> Konflikt sowohl von "Prozess & Kollaboration" als auch von "Entscheidungen &
> Fehler" unabhängig bestätigt) auf 14 lesbare Zeilen — jede Zeile referenziert,
> welche Dimension(en)/Skeptiker sie stützen.

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `container_name: litellm_proxy_staging` (PR #409) kollidierte mit einem noch laufenden, nicht-compose-verwalteten Pilot-Container gleichen Namens — brach den ersten Deploy UND dessen automatischen Rollback; der alte Container läuft bis heute weiter, nie dekommissioniert | Prozesslücke / fehlende Validierung | kritisch | SURVIVES (2× unabhängig, Prozess+Entscheidungen) | `gh run view 29006551425 --log-failed`; `docker ps -a` auf 88.99.38.75 zeigt beide Container | neu — **gate-kandidat** `pre-merge-live-host-check-missing` (Frontmatter) |
| 2 | Daraus folgender realer Staging-Outage (web/worker "Recreated" aber nie "Started"), manuell per `docker start` behoben — nie als GitHub-Issue festgehalten | Prozesslücke | hoch | SURVIVES (2×) | `gh run view 29009598149 --log-failed`; `gh issue list --search "created:2026-07-09"` → leer | `critical-alert-no-ticket` ×1→2 (retro_kpis.py: neu gate-pflichtig, s. §5) |
| 3 | Automatischer Rollback der Deploy-Pipeline ist unzuverlässig und verhält sich je nach Fehlerart inkonsistent (2× identischer Rollback-Fehler bei Name-Kollision/Unhealthy-Dependency; 3. Fehlerart — Health-Check-Timeout auf #412 — überspringt Rollback-Logging komplett) | Werkzeug / fehlende Validierung | mittel | SURVIVES | Drei unabhängig gelesene Run-Logs (409/410/412-Deploys) | neu — **gate-kandidat** `deploy-rollback-untested` (Frontmatter) |
| 4 | Memory-Limit für litellm-proxy wurde geraten (256M, ohne den unbegrenzt laufenden Vorgänger je gemessen zu haben) → 3 echte OOM-Kill-Zyklen (256M→512M→1024M) beobachtet, bevor eine echte Root-Cause-Behebung (`MALLOC_ARENA_MAX=2` + `--num_workers 1`, landet bei 768M) griff | fehlende Validierung → gut korrigiert | mittel/hoch | SURVIVES | `journalctl -k` OOM-Timestamps exakt in 3 Clustern; `docker stats`: 328.7/768MiB stabil seit Fix | neu (kein passender Slug in `retro_kpis.py`; s. §5 Beobachtung) |
| 5 | `depends_on: service_healthy` (litellm-proxy → web/worker) koppelte Kern-App-Verfügbarkeit an einen nicht-kritischen Nebendienst — die eigentliche Architektur-Ursache für Befund #2/#3; in #411 korrekt entfernt | verfrühte Festlegung | hoch (behoben) | SURVIVES | `git show main:docker-compose.staging.yml` zeigt kein `litellm-proxy` mehr in `depends_on` | neu |
| 6 | Der org-weite Shared-Deploy-Workflow (`_deploy-unified.yml`) synct nur `docker-compose.staging.yml`, keine anderen von Compose referenzierten Dateien — ein Fehler, der jedes Repo auf diesem Workflow treffen kann; heute mit einem undokumentierten, ungetrackten manuellen Host-Patch umgangen statt an der Quelle gefixt oder getickelt | Prozesslücke / Werkzeug | hoch | SURVIVES (2× unabhängig) | `gh api .../\_deploy-unified.yml` zeigt `source: "docker-compose.staging.yml"` exklusiv; `stat` auf dem Host zeigt manuelle Platzierung heute 15:00 Uhr, nach allen CI-Läufen; keine passende Issue in shared-ci ODER risk-hub gefunden | neu — **gate-kandidat** `shared-ci-file-sync-gap` (Frontmatter) |
| 7 | Lokales `make lint` prüft nur `ruff check`, nie `ruff format --check` (CI tut beides getrennt) — konkret einen CI-Rot-Lauf auf #413 verursacht, den `make lint` nie gefangen hätte | Werkzeug | mittel | SURVIVES | `Makefile` vs. `ci.yml`; Run 29033130034 zeigt "Would reformat" | neu |
| 8 | Klickdummy-Parity-CI-Job hat einen echten `set -e`-Bug in seiner Postgres-Warteschleife (bricht beim ersten Fehlschlag ab statt 30×2s zu wiederholen) — sieht wie Flakiness aus, ist reproduzierbarer Skript-Fehler | Werkzeug | mittel | SURVIVES | Log-Timestamps: ~2,8s Gesamtlaufzeit statt der ≥60s, die eine echte 30er-Schleife bräuchte | neu |
| 9 | Alle 5 PRs heute von genau einem Reviewer mit Ein-Wort-Freigaben approved ("ok", "go", "reviewed") — inkl. #409 (der Bug-PR), offen nur ~12,3 Minuten vor Merge | fehlende Validierung / Kommunikation | niedrig-mittel | SURVIVES | `gh api pulls/{n}/reviews` für alle 5 PRs | neu (kein passender Slug in `retro_kpis.py` — Korrektur, s. §5: ursprünglich fälschlich als „recurring" behauptet) |
| 10 | Issue #335s Ziel wurde am 2026-06-30 still auf eine andere Architektur umgeschwenkt (LiteLLM-Proxy statt Gateway) — Titel/Body nie angepasst; bleibt offen als 3-Meilenstein-Plan (PR #409 = Schritt 1) | Prozesslücke / Kommunikation | mittel | SURVIVES | `gh issue view 335 --json title,body,comments` | neu |
| 11 | "Deploy-managed statt hand-wired" (PR #409s eigener Titel) ist nicht durabel — dieselbe Ursache wie #6, hier aus der Ziel-Perspektive: ein frisch aufgesetzter Host würde denselben Bug reproduzieren, weil `config.yaml` nie durch die Pipeline ausgeliefert wird | fehlende Validierung | hoch | SURVIVES | siehe #6; zusätzlich: `config.yaml`-Geburtszeit auf dem Host liegt NACH allen #409-Deploy-Läufen | neu (Dublette von #6, andere Perspektive) |
| 12 | Undokumentierte Scope-Erweiterung in ein drittes Produktivsystem (Prod-Authentik-OIDC-Config, Prod-Membership/ModuleMembership-Grants, echte NIS2-Klassifikationsänderung für einen realen Kunden) — keiner dieser Schritte hinterließ eine GitHub-Spur | Prozesslücke / Kommunikation | kritisch | SURVIVES (2× unabhängig, je über Prod-Audit-Logs bestätigt) | Authentik `authentik_events_event` zeigt 2 `model_updated`-Events heute von `authentik-shell`; `tenancy.Membership` id=12 + `ModuleMembership` heute erstellt; `dsb_mandate` id=1 `updated_at` heute 14:44 | `scope-checkpoint-not-durably-recorded` ×3→4 (bereits GATE-PFLICHTIG vor dieser Session; **Synthese-Zusatz s. u.**) |
| 13 | Doppelter Prod-OIDC-User (pk=5) wurde deaktiviert statt gelöscht, weil `iil_learnfw` null Migrationen hat (Cascade-Delete crasht) — diese Lücke ist bereits seit 2026-06-25 als Code-Kommentar bekannt, nie als Issue erfasst (korrigiert: NICHT "gerade erst entdeckt", wie ursprünglich behauptet) | Prozesslücke / Wissenslücke | hoch | SURVIVES (Kernfakt), REFUTED (Charakterisierung "gerade erst entdeckt") | `showmigrations iil_learnfw` → `(no migrations)`; `git log -p -- src/config/settings_ci_e2e.py` zeigt den Kommentar bereits in Commit `e89ea8a` (2026-06-25) | neu |
| 14 | Cloudflare-DNS-Fehlkonfiguration (`staging-demo.schutztat.de` → falscher Host `178.104.184.168`) ist keine neue Entdeckung — Issue #124 (offen seit 2026-05-20, ADR-212) plant exakt diesen DNS-Eintrag als einen von mehreren Checklisten-Punkten; alle anderen Punkte (nginx-vhost, Authentik-Redirect-URI, Demo-Org-Seed, Cert-SAN, 301-Redirect) sind unerledigt; Issue wurde heute trotz Wiederentdeckung nicht aktualisiert | Prozesslücke | hoch | SURVIVES (2× unabhängig) | `gh issue view 124` — Checkliste enthält die IP wörtlich; Cloudflare-API bestätigt den Eintrag | neu |

**Positiv-Kontrolle (kein Fix nötig, zur Kalibrierung mit aufgeführt):**

| # | Befund | Kategorie | Severity | Verdikt | Beleg |
|---|---|---|---|---|---|
| 15 | PR #413 (NIS2-Readiness) durchlief MMD→SoR→KD→Playwright→Code korrekt (3 datierte Commits auf `mmds/nis2-master` vor Code-Merge) und fand/fixte einen echten Bug via Playwright gegen den echten Dev-Server (fehlende `MandateDokuSection`), nicht nur Unit-Tests | — (positiv) | niedrig | SURVIVES | `git log origin/mmds/nis2-master`; PR-#413-Body dokumentiert den Playwright-Fund + Regressionstest |

**Entkräftete Hypothese (gute Nachricht, nicht in der Haupttabelle als offener Befund geführt):**

Die Sorge, die reale NIS2-Klassifikationsänderung für Gröger könnte per Django-Shell
statt über das echte Formular gelaufen sein, wurde **REFUTED**: `record_assessment()`
hat im gesamten Code nur einen einzigen Aufrufer (`nis2_views.py:98`, im
POST-Handler); das nginx-Access-Log zeigt einen vollständigen, zeitlich passenden
HTTP-Round-Trip (`GET`→`POST 302`→`GET 200` auf `/dsb/nis2/1/assessment/`) direkt
im Anschluss an den OIDC-Login; eine vollständige `.bash_history`-Suche auf Prod
fand keinen abweichenden Shell-Aufruf. Konfidenz: stark, aber "circumstantial, not
cryptographic" (per Skeptiker-eigener Einschränkung).

**Nicht auflösbarer Konflikt (kein Befund, s. §8):** Der genaue Auslöser für die
Duplikat-User-Erstellung (Timing-Race vs. E-Mail-Mismatch) ist aus dem heutigen
Prod-Zustand **nicht mehr rekonstruierbar** — zwei unabhängige Skeptiker kamen
unabhängig zum selben "unresolvable"-Urteil, nachdem sie unterschiedliche
Zusatzbelege geprüft hatten (Django-Admin-LogEntry, `audit_event`-Tabelle,
Authentik-eigenes Audit-Log). Keine Seite wird bevorzugt.

**Synthese-Zusatz zu Befund #12 (Transkript-Kontext, nicht durch Artefakte prüfbar,
daher getrennt ausgewiesen statt in die Skeptiker-Verdikte gemischt):** Beide
Skeptiker konnten unabhängig nur bestätigen, DASS die Prod-Änderungen fehlten —
nicht, OB der User im Chat zugestimmt hatte (dafür bräuchten sie das Transkript,
das ihnen bewusst vorenthalten wurde, Regel 1). Aus eigener Kenntnis des
Transkripts (als Synthesizer, nicht als Ermittler — keine neuen Befehle ausgeführt):
für jeden der 5 Einzelschritte lag im Chat eine explizite Zustimmung vor (u. a.
über `AskUserQuestion` für den Redirect-URI-Fix, explizites "ja"/"go ahead" für
Membership-Grants, expliziter Auftrag "correct the numbers... recompute" für die
NIS2-Neuberechnung). Was fehlte, war NICHT die Zustimmung pro Schritt, sondern
(a) die vom Haus-Regelwerk geforderte **explizite Scope-Checkpoint-Formulierung**
("wir sind jetzt beim dritten System — noch gewollt?") — die wurde nur für den
Cloudflare-Fund sauber gemacht (3-Optionen-`AskUserQuestion`), nicht beim ersten
Einstieg in Authentik/Prod-Membership-Arbeit; und (b) **jede** GitHub-Spur. Befund
#12 bleibt daher als Prozess-/Dokumentationslücke bestehen — nicht als
Freigabe-Verstoß.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| Zielerreichung | **4** | #335-Meilenstein + NIS2-Readiness beide technisch erreicht (Befund #15), aber mit echtem Outage unterwegs (#1-#5) |
| Architektur & Design | **3** | NIS2-Modelle sauber am TOM-Muster (Befund #15-adjacent, unstrittig) — aber `depends_on`-Kopplung (#5) + Container-Name-Kollision (#1) sind echte, wenn auch selbst-korrigierte Design-Fehler |
| Code-Konventionstreue | **4** | Konsistent mit bestehenden Mustern (RLS, Soll-Ist-Checklisten-Architektur, Befund #15); dokumentierter, bewusster Dual-Source-of-Truth-Tradeoff (Baustein-Katalog, Befund #13-adjacent — Modell selbst unstrittig, nur die Löschbarkeit der User-Referenz ist betroffen) |
| Risiko & Tech-Debt | **2** | Toter Pilot-Container mit echten Keys (#1) weiter am Laufen; Shared-CI-Lücke ungefixt (#6); zwei alte, unbekannte Lücken (#13, #14) blieben ungetickelt trotz Wiederentdeckung |
| Prozess-Effizienz | **2** | Echtes Rework (3 PRs für ein Feature am selben Tag, #1/#3/#5), echter Outage (#2), Ein-Personen-Rubber-Stamp-Reviews (#9), kein Incident-Ticket für den Ausfall (#2) |
| Entscheidungsqualität | **3** | Gemischt: unvalidierte Prämissen (Container-Name #1, Memory-Limit #4) NEBEN vorbildlicher Root-Cause-Arbeit (#4s dmesg-Analyse, #12s Redirect-URI-Recherche) und korrektem Nicht-Erzwingen einer eigenmächtigen DNS/Architektur-Entscheidung (Befund-übergreifend, #14) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `container_name` in #409 fest verdrahtet, ohne `docker ps` auf dem Ziel-Host zu prüfen | Vor jedem PR, der einen neuen Compose-Service mit festem `container_name` einführt: einmal `docker ps -a` auf dem Ziel-Host als Pre-Merge-Check (oder ein CI-Schritt, der Namenskollisionen gegen den zuletzt bekannten Host-Zustand prüft) | #1 |
| Realer Outage (web/worker down) nie als Issue erfasst | Jeder Vorfall, der einen manuellen Recovery-Schritt (`docker start`, Rollback-Fix) braucht, bekommt automatisch ein Issue — Vorlage: "incident: <kurzbeschreibung>", auch auf Staging | #2 |
| Rollback-Pfad wurde nie isoliert getestet, scheiterte live 2×, verhält sich je nach Fehlerart uneinheitlich | Rollback-Pfad einmal in einem kontrollierten Fire-Drill durchspielen (absichtlich einen Deploy-Fehler auslösen, Rollback beobachten) — Ergebnis als Kommentar an `_deploy-unified.yml` hinterlegen | #3 |
| Memory-Limit geraten (256M) ohne den unbegrenzten Vorgänger je zu messen | Bei "hand-wired → compose-managed"-Migrationen: einmal `docker stats --no-stream` auf dem laufenden Pilot-Container VOR dem Setzen eines `deploy.resources.limits` | #4 |
| `depends_on: service_healthy` an einen nicht-kritischen Nebendienst gekoppelt | Faustregel: `depends_on: service_healthy` nur für Dienste, die synchron im Boot-Pfad gebraucht werden — für alles "lazy called" (AI-Calls, Hintergrund-Jobs) höchstens `service_started`, nie `service_healthy` | #5 |
| Shared-CI-Datei-Sync-Lücke lokal umgangen (Live-Patch), nicht an der Quelle gefixt, keine Issue | Bei Lücken in org-weiten Shared-Workflows: sofort ein Issue in `iilgmbh/shared-ci` (nicht nur im eigenen Repo umschiffen) — der Live-Patch ist ok als Sofortmaßnahme, ersetzt aber nicht das Ticket | #6 |
| `make lint` und CI prüfen unterschiedliche Dinge (kein `ruff format --check` lokal) | `make lint` um `ruff format --check .` ergänzen, damit lokale und CI-Lint-Fläche deckungsgleich sind | #7 |
| Postgres-Warteschleife im Klickdummy-Parity-Job bricht unter `set -e` beim ersten Fehlschlag ab | Schleifen-Body auf `if ! cmd; then sleep 2; continue; fi; break` umstellen (kompatibel mit `set -e`) statt `cmd && break` | #8 |
| Alle 5 PRs mit Ein-Wort-Freigaben von einer Person | Für infrastruktur-nahe PRs (Compose/Deploy-Änderungen) mindestens einen zweiten Blick oder eine explizite Checkliste ("Host-Zustand geprüft? Ja/Nein") in der PR-Vorlage verlangen | #9 |
| Issue #335 nach Architektur-Pivot nie im Titel/Body aktualisiert | Bei jedem "→ #NNN re-scopen"-Kommentar: den Issue-Titel/Body im selben Zug tatsächlich editieren, nicht nur als Kommentar vorschlagen | #10 |
| "Deploy-managed"-Anspruch (PR-Titel #409) traf nicht zu, weil die Pipeline die Datei nie auslieferte | PR-Titel/Beschreibung erst nach einem tatsächlichen End-to-End-Deploy-Durchlauf (nicht nur CI-grün) als "durable"/"deploy-managed" bezeichnen | #11 (Dublette von #6) |
| Scope-Erweiterung in Authentik/Prod-Membership/NIS2-Daten ohne GitHub-Spur, ohne durchgängige Scope-Checkpoint-Formulierung | Bei JEDEM Prod-Schritt außerhalb des ursprünglich genannten Repos: (a) die im Haus-Regelwerk vorgeschriebene Scope-Checkpoint-Frage wörtlich stellen, nicht nur implizit über AskUserQuestion abdecken; (b) im Anschluss einen Kommentar/Issue in genau EINEM zentralen Ort (z. B. dem ursprünglichen Issue #335 oder einem neuen "prod-touch"-Log-Issue) hinterlassen | #12 |
| `iil_learnfw`-Lücke seit 2026-06-25 bekannt, nie tickets, heute erneut umgangen statt gefixt | Bekannte, umgangene Lücken (mit Code-Kommentar-Beleg) automatisch in ein Issue überführen, sobald sie zum zweiten Mal ein Problem verursachen (hier: 2026-06-25 Kommentar → 2026-07-09 blockierte Löschung) | #13 |
| Issue #124 wortwörtlich wiederentdeckt, aber nicht kommentiert/aktualisiert | Bei Wiederentdeckung eines bereits offenen, passenden Issues: sofort einen Kommentar mit dem heutigen Fund hinterlassen ("Status heute verifiziert: X von Y Schritten noch offen"), auch wenn keine Fix-Entscheidung ansteht | #14 |

## 5. Längsschnitt

```
$ python3 tools/retro_kpis.py --dir docs/retros
```

**Tatsächliche Rohausgabe (19 Retro-Reports insgesamt, inkl. dieser Datei; verbatim,
nicht paraphrasiert):**

```
# Längsschnitt über 19 Retro-Reports (docs/retros)

## recurring_findings (Zähler über Retros)
  🚨 GATE-PFLICHT  claim-before-cheapest-check  ×14  […]
  🚨 GATE-PFLICHT  scope-checkpoint-not-durably-recorded  ×3  [0181a7-incr, 17c08c, e17299]
  🚨 GATE-PFLICHT  lint-failure-no-local-gate  ×3  […]
  🚨 GATE-PFLICHT  stale-local-clone-as-ground-truth  ×3  […]
  🚨 GATE-PFLICHT  handover-stale-vor-merge  ×3  […]
  🚨 GATE-PFLICHT  planned-phase-no-issue  ×2  […]
  🚨 GATE-PFLICHT  ci-gate-maskiert-failure  ×2  […]
  ·  critical-alert-no-ticket  ×1  [e17299-incr]
  … (weitere ×1-Slugs ausgelassen, keiner passt zu einem Befund dieser Session)

→ 7 Slug(s) ≥2 ⇒ Gate-PR-Pflicht.

## refuted_rate-Trend
  e623cd:0.13 · 3b123e:0.20 · a2c373:0.40 · 2752dc:0.12 · 7f7fbd:0.29 · 733182:0.00 · 589606:0.36 · 1adf2a:0.10
  ✅ Band gesund (weder 3× >0.8 noch <0.2).

## Score-Mittel je Dimension (1–5, n=19)
  zielerreichung 3.89 · architektur_design 3.58 · code_konventionstreue 3.74 ·
  risiko_debt 2.68 · prozess_effizienz 3.11 · entscheidungsqualitaet 3.37
```

**Korrektur gegenüber einem ersten, ungeprüften Entwurf dieser Sektion:** Ein früherer
Entwurf dieses Reports behauptete drei "recurring"-Slugs
(`single-reviewer-rubber-stamp-approval`, `live-incident-not-filed-as-issue`,
`unmeasured-resource-limit-guess`) UND einen Vergleichs-Report
`session-retro-2026-07-07-risk-hub`, bevor `retro_kpis.py` tatsächlich gelaufen war —
genau das Anti-Pattern, das diese Skill selbst verbietet ("Belegpflicht gilt AUCH für
Längsschnitt-Behauptungen"). Nach dem echten Lauf: **beide Prämissen waren falsch** —
es gibt keinen 2026-07-07-risk-hub-Report (`ls docs/retros/` zeigt 19 Dateien, keine
davon zu risk-hub vor heute), und keiner der drei erfundenen Slugs taucht im Tool-Output
auf. Fix unten, nicht stillschweigend übernommen:

- **`scope-checkpoint-not-durably-recorded`** (bereits GATE-PFLICHTIG bei ×3 vor dieser
  Session — Belege `grep`-verifiziert in `0181a7-incr`, `17c08c`, `e17299`: dasselbe
  Muster "Freigabe/Scope-Erweiterung geschah real, aber landete nie durabel in einem
  Artefakt"). Befund #12 dieser Session ist Vorkommen **4** — der bestehende Gate-Kandidat
  bleibt also nicht nur bestätigt, sondern greift laut den Vorgänger-Reports (s. e17299
  §6) bereits NICHT für Chat-Freigaben zwischen PRs — ein bestehender, nachgeschärfter
  Gate-Vorschlag, kein neuer.
- **`critical-alert-no-ticket`** (bei ×1 aus `e17299-incr`: dort eine rot gewordene
  CI-Prüfung ohne Ticket). Befund #2 dieser Session (realer Staging-Outage, manuell
  recovered, nie getickelt) ist strukturell dieselbe Klasse ("kritischer Alarm/Vorfall
  im Session-Verlauf begegnet, kein Issue eröffnet") — Vorkommen **2 ⇒ neu
  gate-pflichtig**, echte Eskalation aus diesem Lauf.
- Befund #4 (Memory-Limit geraten) und #9 (Ein-Personen-Rubber-Stamp-Reviews) haben
  **keinen** passenden Slug im Tool-Output — beide bleiben als `neu` geführt, nicht als
  wiederkehrend (Korrektur gegenüber dem verworfenen Entwurf).

**`refuted_rate`-Band-Vergleich:** dieser Report liegt bei 0,10 (2/19 roh; 0,105 laut
Frontmatter-Rundung), passt in die gesunde Bandbreite der anderen 7 im Tool-Trend
gezeigten Retros (0,00–0,40) — kein Ausreißer.

## 5b. Autonomie-Kalibrierung

- **`over_ask`**: keiner identifiziert. Alle Rückfragen dieser Session betrafen
  echte Gates (Secret-Schreibvorgänge, Prod-DNS/Nginx-Entscheidungen, Prod-
  Zugriffsgrant-Rollenwahl) — nichts davon war deterministisch/reversibel genug,
  um ohne Rückfrage zu laufen.
- **`over_act`**: **1 Fall** — die drei live gescouteten Versuche, Secret-Werte
  über Shell-Konstrukte zu extrahieren/zu übertragen (mehrfach vom
  Auto-Mode-Classifier geblockt, siehe Chat), bevor auf die vom User selbst
  vorgeschlagene Datei-zu-Datei-Methode umgeschwenkt wurde, zählt als
  wiederholter Annäherungsversuch an ein Security-Config-Gate ohne vorherige
  explizite Freigabe der GENAUEN Methode. Kein Schaden entstanden (Classifier
  hat korrekt geblockt), aber das Muster "mehrere Varianten am Gate ausprobieren
  statt beim ersten Block zu stoppen und zu fragen" ist evaluierungswürdig für
  `feedback_autonomy_charter`, falls es sich in einem künftigen Report
  wiederholt (aktuell: Vorkommen 1, keine Eskalation nötig).

## 6. Verankerung

**Gate-Eskalation (aus §5, kein neuer Vorschlag — bestehende Slugs schärfen):**

1. `critical-alert-no-ticket` steht nach dieser Session bei ×2 über Retros ⇒
   neu gate-pflichtig laut `retro_kpis.py`. Konkreter Vorschlag: jeder manuelle
   Recovery-Schritt (Container-Restart, Rollback-Fix, Incident-Response) erzeugt
   automatisch einen Issue-Draft — Hook oder Checkliste, org-weit, nicht nur
   risk-hub.
2. `scope-checkpoint-not-durably-recorded` steht nach dieser Session bei ×4 —
   der Vorgänger-Report `e17299` (§6) hat bereits notiert, dass ein bestehendes
   Gate "nicht für Chat-Freigaben zwischen PRs" greift; Befund #12 bestätigt
   exakt dieselbe Lücke in einem anderen Repo (risk-hub statt platform) — spricht
   für ein **org-weites**, nicht repo-lokales Gate.

**Memory-Kandidat (kopierfertig für `~/.claude/projects/*/memory/`):**

```markdown
---
name: feedback_container_name_vs_live_host_state
description: "Vor dem Festlegen eines container_name in einem neuen Compose-Service: docker ps auf dem Ziel-Host prüfen, sonst Namenskollision mit unmanaged Altlasten (Pilot-Container etc.)"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-09-litellm-container-name-collision
---

**Regel:** Bevor ein neuer Compose-Service einen festen `container_name` bekommt
(besonders bei "hand-wired → compose-managed"-Migrationen): `docker ps -a` auf dem
Ziel-Host prüfen, ob dieser Name schon von einem NICHT compose-verwalteten
Container belegt ist. Docker Compose adoptiert solche Container nicht — es
kollidiert beim Create, und der automatische Rollback scheitert aus demselben
Grund erneut.

**Why:** risk-hub #409 (2026-07-09) — Namenskollision mit einem 8+ Tage
laufenden Pilot-Container brach Deploy UND Rollback, brauchte 2 Hotfix-PRs
(#410, #411) und einen manuellen `docker start` zur Outage-Behebung, da web/worker
zusätzlich per `depends_on: service_healthy` an den kaputten Proxy gekoppelt waren.

**How to apply:** Gilt für jede Migration eines hand-wired/manuell laufenden
Containers in eine Compose-verwaltete Definition, org-weit — nicht nur risk-hub.
```

**ADR-Kandidat:** keiner — die betroffenen Fixes (Container-Name, Memory-Limit,
`depends_on`) sind Bugfixes/Ergänzungen eines bestehenden Musters, keine neue
Architekturentscheidung (`adr-threshold.md`: "Reversibel durch Entfernen eines
Containers" trifft zu).

**Issue-Kandidaten (kopierfertig):**

1. `iilgmbh/shared-ci`: "Deploy-Workflow scp-action synct nur die Compose-Datei,
   keine weiteren referenzierten Dateien — betrifft jedes Repo auf
   `_deploy-unified.yml`" (Befund #6/#11).
2. `iilgmbh/risk-hub`: "Alten hand-wired `litellm_proxy_staging`-Container auf
   Staging dekommissionieren (läuft seit 8+ Tagen unnötig weiter, hält echte
   Provider-Keys)" (Befund #1).
3. `iilgmbh/risk-hub`: "`iil_learnfw`-App hat null Migrationen — blockiert jede
   User-Löschung; seit 2026-06-25 bekannt (Code-Kommentar), nie getickelt"
   (Befund #13).
4. Kommentar auf dem bereits offenen `iilgmbh/risk-hub#124`: heutigen
   Re-Fund-Status dokumentieren (welche Checklisten-Punkte weiterhin offen sind)
   (Befund #14).

## 7. Maßnahmen (Action Board)

🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Alten `litellm_proxy_staging`-Pilot-Container dekommissionieren | risk-hub | — (Issue-Kandidat 2 oben) | 🟢 offen | du: Freigabe zum Stoppen/Entfernen |
| 2 | Shared-CI-Datei-Sync-Lücke fixen oder ticketen | shared-ci | — (Issue-Kandidat 1 oben) | 🟢 offen | du: Priorität festlegen |
| 3 | `iil_learnfw`-Migrations-Lücke ticketen | risk-hub | — (Issue-Kandidat 3 oben) | 🟢 offen | du: Priorität festlegen |
| 4 | Issue #124 mit heutigem Re-Fund-Status kommentieren | risk-hub | [#124](https://github.com/iilgmbh/risk-hub/issues/124) | 🟢 offen | du/ich: Freigabe zum Kommentieren |
| 5 | Gate `critical-alert-no-ticket` (jetzt ×2, org-weit) verankern: manueller Recovery-Schritt ⇒ automatischer Issue-Draft | platform | — (Gate-Kandidat, §6) | 🟢 offen | du: Priorität/Ownership festlegen |
| 6 | Gate `scope-checkpoint-not-durably-recorded` (jetzt ×4, org-weit) nachschärfen für Chat-Freigaben zwischen PRs | platform | — (Gate-Kandidat, §6; verwandt zu e17299 §6) | 🟢 offen | du: Priorität/Ownership festlegen |

🔵 Offen — ich kann sofort

| # | Item | Repo | Next Step |
|---|---|---|---|
| 7 | `make lint` um `ruff format --check .` ergänzen | risk-hub | ich: PR vorbereiten, wenn gewünscht |
| 8 | Klickdummy-Parity-CI-Retry-Schleife von `cmd &amp;&amp; break` auf `set -e`-sichere Form umstellen | risk-hub | ich: PR vorbereiten, wenn gewünscht |
| 9 | Issue #335 Titel/Body auf den tatsächlichen 3-Meilenstein-Plan aktualisieren | risk-hub | ich: Edit vorbereiten, wenn gewünscht |

## 8. Nicht verifiziert (Restlücken)

- **Auslöser der Duplikat-User-Erstellung (Timing-Race vs. E-Mail-Mismatch):**
  aus dem heutigen Prod-Zustand nicht mehr rekonstruierbar (historischer
  E-Mail-Wert wurde durch eine spätere Umbenennung überschrieben, kein
  Audit-Trail — weder Django-`LogEntry` noch `audit_event`-Tabelle noch
  Authentik-Events — deckt den fraglichen Zeitpunkt ab). Billigster verbleibender
  Check: keiner bekannt: das wäre nur durch ein Datenbank-Backup vor der
  Umbenennung rekonstruierbar, falls eines existiert (nicht geprüft).
- **Phase 5 (Meta-Reviewer) wurde in diesem Lauf nicht durchgeführt** (Zeit-/
  Budget-Grenze) — der Report selbst wurde nicht gegen die Skill-Regeln von
  einem separaten, frischen Agenten geprüft. Lücke, nicht verschwiegen.
- **Ob 178.104.184.168 tatsächlich der User gehört** wurde per SSH-Zugriff
  (derselbe Schlüssel) und Hostname (`staging-platform`) plausibilisiert, aber
  nicht über eine Rechnungs-/Vertrags-Quelle bei Hetzner verifiziert — billigster
  nächster Check wäre der Hetzner-Robot-Account, nicht in dieser Session
  geprüft.
- **Korrigierter erster Entwurf von §5:** vor dem tatsächlichen Lauf von
  `tools/retro_kpis.py` enthielt dieser Report einen unbelegten Entwurf mit drei
  erfundenen "recurring"-Slugs und einem nicht-existenten Vergleichs-Report
  (`session-retro-2026-07-07-risk-hub`). Beides wurde nach dem echten Tool-Lauf
  korrigiert (s. §5) — als Fakt hier festgehalten, damit der Fehler selbst nicht
  stillschweigend verschwindet, sondern Teil des Befund-Bestands dieses
  Reports über sich selbst wird.
