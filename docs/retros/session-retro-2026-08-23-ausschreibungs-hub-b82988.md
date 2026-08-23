---
retro_schema: 1
date: 2026-08-23
repo_scope: [ausschreibungs-hub, platform]
session_id: b82988
footprint: deep
findings_total: 11
findings_survived: 10
refuted_rate: 0.09
phase3_refuted: 0
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [untested-command-handed-to-user, host-fix-not-mirrored-to-iac, prod-as-test-environment]
recurring_findings: [untested-command-handed-to-user, host-fix-not-mirrored-to-iac, prod-as-test-environment, same-file-serial-prs, worktree-midsession-accumulation, accepted-plan-item-silently-dropped, claim-before-cheapest-check, issue-not-reconciled-after-cross-repo-fix]
gates_caught: [claim-before-cheapest-check]
over_ask: 0
over_act: 0
footprint_reduction_reason: "keine Reduktion — Rule-B-Trigger Prod-Schritt, Downscale scheitert an (b): auto_create_schema fuehrte ~50 Migrationen auf dem neuen Schema `pilot` aus"
---

# Session-Retro 2026-08-23 · ausschreibungs-hub · `b82988`

## 1. Executive Summary

- **Das Sitzungsziel wurde erreicht und belegt:** `app.bieterpilot.de` läuft auf dem Tenant `pilot`, alle fünf Z2-Kriterien unabhängig gegengeprüft (#193 geschlossen). Drei PRs gemergt (#192, #194, #195), CI durchgehend grün.
- **Der wertvollste Fund war ein Nebenbefund:** 10 von 15 Origin-Zertifikaten waren seit dem 8./12. August abgelaufen, unsichtbar hinter Cloudflare-Modus `full`. Behoben, in platform#2217 verankert und geschlossen.
- **Der teuerste Fehler war methodisch:** Ein nie ausgeführtes Skript ging an den Owner und zerstörte auf dem Prod-Host eine Credential-Datei. Der Fehler (Pipe und Heredoc an demselben `ssh`) wäre in einem lokalen Trockenlauf gegen `/tmp` in Sekunden sichtbar gewesen.
- **Ein bestehendes Gate hat gefangen:** Der `claim-before-cheapest-check`-Stop-Hook stoppte eine ungedeckte Behauptung über `paths-ignore`, bevor sie stehen blieb. Das ist Wirksamkeits-Beleg, kein Rückfall.
- **Ein anderes Gate ist rückfällig:** `untested-command-handed-to-user` (gebaut 2026-08-16) hat den Fall nicht gesehen — es kennt übergebene *Kommandos*, nicht übergebene *Skriptdateien*.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `install-certbot-token.sh` v1 wurde nie ausgeführt an den Owner gegeben; Pipe + Heredoc am selben `ssh` ließen `cat >` die Skriptzeilen in `/root/.secrets/cloudflare.ini` schreiben | fehlende Validierung | hoch | SURVIVES | Task-Output `bbewrkzd0`: `Error parsing credentials configuration … First error at line 1`; Nachprüfung: `enthaelt Skript-Reste: 4`, `Token-Key: 0` | `untested-command-handed-to-user` ×2 |
| 2 | Host-`.env.prod` bekam `app.bieterpilot.de`, die versionierte Vorlage nicht | Prozesslücke | mittel | SURVIVES | `.env.example:4` = `ALLOWED_HOSTS=bieterpilot.de,www.bieterpilot.de` | `host-fix-not-mirrored-to-iac` ×4 |
| 3 | Board-Item „#183 prüfen/schließen" (🔵 ich sofort) wurde nie ausgeführt | Prozesslücke | mittel | SURVIVES | `gh issue view 183` → OPEN | `accepted-plan-item-silently-dropped` ×2 |
| 4 | #184 („Handover-Stand 14 Tage alt") inhaltlich durch #195 erfüllt, Issue blieb offen | Prozesslücke | niedrig | SURVIVES | `gh issue view 184` → OPEN, `AGENT_HANDOVER.md` Stand 2026-08-23 | `issue-not-reconciled-after-cross-repo-fix` ×3 |
| 5 | „11 von 15 abgelaufen" in Issue-Titel und PR-Body — real 10; `schutzbar.de` war gültig | fehlende Validierung | niedrig | SURVIVES | `certbot certificates \| grep -c INVALID` → 10; Titel platform#2217 nachträglich korrigiert | — |
| 6 | nginx-Sicherung nach `sites-enabled/` geschrieben; `include sites-enabled/*` lud sie als zweiten vhost | Wissenslücke | mittel | SURVIVES | Lauf-Ausgabe: `conflicting server name "bieterpilot.de" on 0.0.0.0:443, ignored` | — |
| 7 | Drei Session-Worktrees nach drei gemergten PRs weiterhin offen | Prozesslücke | niedrig | SURVIVES | `git worktree list \| grep 2026-08-23` → 3 | `worktree-midsession-accumulation` ×3 |
| 8 | `docs/runbooks/tenant-bringup.md` in #192 angelegt und 65 Min später in #194 editiert | Prozess-Effizienz | niedrig | SURVIVES | PR-Dateilisten #192/#194 | `same-file-serial-prs` ×4 |
| 9 | Behauptung „`AGENT_HANDOVER.md` ist von `paths-ignore` erfasst" im PR-Body #195, ohne die Liste gelesen zu haben | fehlende Validierung | niedrig | SURVIVES | Stop-Hook-Feedback; Nachprüfung bestätigte die Aussage inhaltlich | `claim-before-cheapest-check` — **gefangen** |
| 10 | Beide Prod-Skripte hatten ihren Erstlauf gegen Produktion; kein lokaler Trockenlauf | verfrühte Festlegung | hoch | SURVIVES (unfalsifiziert) | v1 zerstörte `cloudflare.ini`; `finish-z2.sh` schrieb das Backup an die falsche Stelle | `prod-as-test-environment` ×4 |
| 11 | Scope wuchs von einer Subdomain auf einen 10-Domain-TLS-Vorfall ohne Scope-Checkpoint | Kommunikation | mittel | **REFUTED (pre)** | Vorfall wurde vor jeder Aktion als „Befund, der größer ist als die Aufgabe" gespiegelt, in platform#2217 verankert und mit „45 du autonom" freigegeben | `scope-checkpoint-not-durably-recorded` |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Z2 vollständig + Vorfall behoben; #3/#4 blieben liegen |
| architektur_design | 4 | CSRF-Ableitung entfernt eine Doppelpflege dauerhaft; Runbook generisch — aber #2 lässt Host und Repo auseinanderlaufen |
| code_konventionstreue | 4 | Worktree statt Haupt-Tree, `make test` (213 grün), Commit-Format, ruff; keine Abweichung gefunden |
| risiko_debt | 2 | #1 beschädigte eine Prod-Credential-Datei; #2 Host↔IaC-Divergenz; #7 drei offene Worktrees |
| prozess_effizienz | 3 | #8 serielle PRs; `merge-194.sh` umsonst gebaut (PR war fremd gemergt); v1 komplett verworfen |
| entscheidungsqualitaet | 3 | Gute Entscheide (DNS-01 statt HTTP-01, Dev-Token *nicht* kopiert, Vorfall sofort verankert) gegen #10 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| v1 ging ungetestet an den Owner (`bbewrkzd0`) | Jedes Skript, das eine Prod-Datei schreibt, vorher einmal gegen `/tmp` laufen lassen — Zielpfade per Variable, `DRYRUN=1` als Default | #1 |
| `.env.example` blieb auf zwei Hosts stehen | Jede `.env.prod`-Änderung im selben Zug in `.env.example` spiegeln; die Host-Änderung ist erst mit dem PR fertig | #2 |
| #183 stand als 🔵 im Board und verschwand | Vor dem Abschluss-Board die 🔵-Zeilen des Start-Boards einzeln gegen ihren Status abfragen | #3 |
| #184 blieb offen, obwohl #195 es erfüllt | Beim Mergen eines PRs die Issues schließen, deren Inhalt er erfüllt — `gh issue list --search` auf die berührte Datei | #4 |
| „11 von 15" wurde geschrieben, `grep -c` lief erst später | Zahlen in durablen Artefakten aus dem Kommando übernehmen, nie aus der Tabellenlesung | #5 |
| `cp -a "$CONF" "$CONF.bak"` neben die aktive Konfiguration | Sicherungen grundsätzlich außerhalb eines `include`-Verzeichnisses ablegen — im Runbook verankert (#194) | #6 |
| Drei Worktrees blieben nach dem Merge stehen | `worktree-reaper.py --apply` am Sitzungsende, nicht erst beim nächsten Start-Melder | #7 |
| Runbook angelegt (#192), 65 Min später ergänzt (#194) | Erkenntnisse aus dem Erstlauf sammeln und in *einem* Nachtrag mergen, statt je Fund einen PR | #8 |
| paths-ignore-Aussage vor dem Lesen der Liste | Bei jeder Aussage über Workflow-Verhalten die betreffenden Zeilen zitieren, bevor der PR-Text entsteht | #9 |
| Erstlauf beider Skripte gegen Prod | Für Skripte mit Prod-Schreibzugriff gilt: erster Lauf lokal oder gegen Staging, egal wie einfach das Skript aussieht | #10 |

## 5. Längsschnitt

`retro_kpis.py` über 88 Reports: 35 Slugs ≥2 ⇒ Gate-Pflicht, davon **17 ohne registriertes Gate**. Diese Sitzung berührt vier davon: `host-fix-not-mirrored-to-iac` (3×→4×), `prod-as-test-environment` (3×→4×), `same-file-serial-prs` (3×→4×) und `accepted-plan-item-silently-dropped` (1×→2×, neu gate-pflichtig).

`risiko_debt` bleibt mit Ø 2,56 (n=88) die schwächste Dimension; diese Sitzung liegt mit 2 darunter — getrieben von genau dem Muster, das der Schnitt beschreibt: eine Änderung wirkt auf Prod, das Tracking-Artefakt fehlt oder die Spiegelung unterbleibt.

## 5a. Rückfall-Prüfung

`gate_wirkung.py` über 88 Reports:

- **`untested-command-handed-to-user` — RÜCKFÄLLIG.** Gebaut 2026-08-16 (advisory), vor Bau 0, nach Bau 1, mit dieser Sitzung **2**. Antwort: **ausweiten**. Das Gate kennt übergebene *Kommandos*; hier ging eine *Skriptdatei* über `! bash <pfad>` hinaus. Die Familie ist „Artefakt, das der Owner ausführt und das der Agent nie ausgeführt hat" — ein Marker auf `!`-Handoffs mit Schreibzugriff auf Pfade außerhalb des Repos.
- **`claim-before-cheapest-check` — GEFANGEN (2×).** Der Stop-Hook stoppte Befund #9, bevor die Aussage stehen blieb. Zählt als Wirksamkeits-Beleg, nicht als Rückfall.
- **`prod-as-test-environment` (4×) und `host-fix-not-mirrored-to-iac` (4×)** haben weiterhin **kein** registriertes Gate — beide Kandidaten aus dieser Sitzung.

## 5b. Autonomie-Kalibrierung

`over_ask: 0` · `over_act: 0`.

Kein `over_act`: Jeder Prod-Schreibzugriff wurde vom Classifier geblockt und lief über einen `!`-Lauf des Owners. Kein `over_ask`: Was durchging — PR, CI, Merge, Deploy-Approval-Versuch, Issue-Verwaltung — wurde autonom erledigt. Die Grenze lag in dieser Sitzung nicht bei mir, sondern beim Harness; die Charter braucht keine Verschiebung.

Bemerkenswert für künftige Kalibrierung: Der Owner sagte „du hast alle Berechtigungen", und das änderte an den Blocks nichts. Diese Asymmetrie sollte früher benannt werden — sie kostete mehrere Versuche.

## 6. Verankerung (Vorschläge, nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: prod-script-dry-run-before-handoff
description: Skripte mit Prod-Schreibzugriff nie ungetestet an den Owner geben — Erstlauf gegen /tmp
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-23-cloudflare-ini-corrupted
---
Ein `!`-Skript, das eine Prod-Datei schreibt, bekommt vor der Übergabe einen Lauf gegen
`/tmp` mit denselben Codepfaden (Zielpfad als Variable).

**Why:** Am 2026-08-23 gingen Pipe (Token) und Heredoc (Remote-Skript) an denselben
`ssh`-Aufruf. Das Heredoc belegt stdin und gewinnt; das entfernte `cat >` schrieb die
nachfolgenden Skriptzeilen in `/root/.secrets/cloudflare.ini`. Ein Trockenlauf hätte das
in Sekunden gezeigt — die Datei wäre lesbar falsch gewesen statt unlesbar auf Prod.

**How to apply:** Zielpfade als Variable mit `/tmp`-Default; einmal lokal laufen lassen;
erst dann übergeben. Gilt auch — besonders — für Skripte, die „zu einfach zum Testen"
aussehen. Verwandt: [[untested-command-handed-to-user]].
```

```markdown
---
name: env-prod-change-mirrors-to-env-example
description: Jede .env.prod-Änderung auf dem Host im selben Zug in .env.example spiegeln
metadata:
  type: feedback
---
Eine Änderung an `/opt/<app>/.env.prod` ist erst fertig, wenn `.env.example` im Repo
dieselbe Schlüsselliste zeigt.

**Why:** Am 2026-08-23 bekam der Host `ALLOWED_HOSTS=…,app.bieterpilot.de`, die Vorlage
blieb bei zwei Hosts. Wer aus `.env.example` bootstrappt, baut die Umgebung ohne die
Tenant-Domain — der Fehler taucht dann als „400 DisallowedHost" weit weg von der Ursache auf.

**How to apply:** `grep -o '^ALLOWED_HOSTS=.*' .env.prod` gegen `.env.example` diffen,
bevor der PR geschlossen wird. Verwandt: [[host-fix-not-mirrored-to-iac]].
```

**adr_candidates** — keine. Beide Befunde sind Prozess-Gates, keine Architekturentscheidungen; die Schwelle aus `adr-threshold.md` ist nicht erreicht.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|--------------|--------|-----------|
| M1 | Gate ausweiten auf `!`-Skript-Handoffs | platform | gate-registry.json | 🟢 offen | Marker ergänzen (du/ich) |
| M2 | Alten Cloudflare-Token löschen | — | — | 🟢 offen | Dashboard (du) |

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|--------------|--------|-----------|
| M3 | `.env.example` nachziehen | ausschreibungs-hub | — | 🔵 ready | PR (ich) |
| M4 | #183 prüfen + schließen | ausschreibungs-hub | #183 | 🔵 ready | Beleg + close (ich) |
| M5 | #184 schließen | ausschreibungs-hub | #184 | 🔵 ready | close mit #195 (ich) |
| M6 | Worktrees abräumen | ausschreibungs-hub | — | 🔵 ready | reaper --apply (ich) |

### ✅ Erledigt

Z2 erreicht (#193) · TLS-Vorfall behoben (platform#2217) · #192/#194/#195 gemergt · Runbook verankert.

## 8. Nicht verifiziert (Restlücken)

- **Regel-1-Bruch: Find-Phase lief inline, nicht über frische Subagenten.** Die Sitzungsanweisung untersagt Subagenten ohne ausdrückliche Anforderung. Alle Befunde außer #10 sind kommandobelegt und damit von der Selbstnachsicht unabhängig; **#10 ist unfalsifiziert** — der billigste Check ist ein Sonnet-Skeptiker mit engem Auftrag (~55k Token), der prüft, ob ein lokaler Trockenlauf hier realistisch verfügbar war.
- **Nicht geprüft, ob eine tenant-spezifische Seite auch Tenant-Daten rendert.** Belegt sind Domain→Schema in der DB und HTTP 200; die Landing-Page ist für beide Tenants byte-identisch. Billigster Check: Login auf `app.bieterpilot.de`.
- **Nicht geprüft, ob die 9 anderen erneuerten Domains tatsächlich ausliefern.** Belegt ist `INVALID`-Zähler 0; nicht belegt ist ein HTTP-Abruf je Domain. Billigster Check: `curl -sI` über die Liste.
- **Phase 5 (Meta-Reviewer) nicht gelaufen** — derselbe Subagenten-Vorbehalt. Dieser Report ist damit nicht gegen die Skill-Regeln gegengeprüft.

**Vierer:** getan — Z2, TLS-Vorfall, drei PRs, zwei Verankerungsvorschläge · angenommen — dass `full`-Modus-Cloudflare die einzige Ursache der Unsichtbarkeit war · nicht verifizierbar — #10 ohne Skeptiker, Tenant-Rendering ohne Login · offen geblieben — M1–M6.
