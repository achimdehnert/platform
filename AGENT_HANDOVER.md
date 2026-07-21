# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

<!-- Konvention: dieser Abschnitt hält NUR den "## ⚡ Aktueller Stand" + max. EINEN
     "## ⚡ Vorheriger Stand" (den jeweils jüngsten). Alles Ältere wandert nach
     AGENT_HANDOVER_ARCHIVE.md (siehe Verweis unten) — nicht hier anhäufen. -->

**Archiv älterer Session-Stände:** [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md)
(Blöcke älter als der aktuelle + 1 vorherige Stand).

## ⚡ Aktueller Stand (2026-07-21 — Skill-Lane-Konsolidierung: ADR-280 Rev 2 nach externem Sparring, ADR-281 Symlink-Verteilung, /adr-Skill + adr-threshold-Policy repariert)

**Auslöser war ein Nebenbefund**, kein geplanter Strang: beim Rebase von #1013 war nicht entscheidbar, in welche der zwei Skill-Lanes (`.windsurf/workflows/` → `~/.claude/commands/` vs. `skills/` → `~/.claude/skills/`) ein **neuer** Skill gehört. Owner-Weisung 2026-07-21: keine Parallelexistenz.

**Geliefert:**
- **#1290 gemergt** — Phase 1: 3 Piloten (`next`, `escalate`, `issues-offen`) nach `skills/`; `check_workflow_index.py` scannt jetzt **beide** Lanes, `tools-tests.yml` triggert auf `skills/**`, 5 neue Tests. Nebenbefund dabei: `antwort-modus-schablone` stand seit 2026-06-05 in **keinem** Index — die Lane war für den Vollständigkeits-Gate schlicht unsichtbar.
- **#1291 gemergt** — ADR-280 (Rev 1). **#1295 offen** — ADR-280 **Rev 2**, ergebnisoffene Neubewertung.
- **#1296 offen** — ADR-281: Skills als **Symlink** statt generierter Kopie (amendiert ADR-230 §2.2).
- **#1292 gemergt** — `/adr`-Skill: `gen_adr_index.py` als Pflichtschritt, Abschluss-Checkliste, Anti-Patterns, Changelog (alle drei fehlten).
- **#1293 auto-merge gequeued** — `policies/adr-threshold.md`.
- **#1294 offen** — Regression aus #1290 zurückgenommen.
- **#1118 geschlossen** — superseded, OIDC lag längst auf main.

**Der zentrale Befund — meine Prämisse war falsch:** Rev 1 behauptete, `$ARGUMENTS` entfalle unter Agent Skills. Geprüft gegen die laufende Umgebung (`claude --version` = **2.1.216**, Doku 2026-07-21): *„Custom commands **have been merged into skills** … both create `/deploy` and **work the same way**."* Skills unterstützen `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, benannte `$name`. Folgen: Migrationskosten von Option A waren zu hoch angesetzt, „Pilot zuerst" war eine Scheinbegründung, und im Pilot wurde funktionierendes `$ARGUMENTS` durch Prosa **ersetzt** (→ #1294). Zwei unabhängige externe Zweitmeinungen fanden das; beide empfahlen „überarbeiten".

**ADR-280 Rev 2 ruht jetzt auf EINEM geprüften Argument** statt auf vieren: nur die Verzeichnisform trägt **Supporting Files** — damit werden die drei `distribute: false`-Persona-Prompts (Typ 3) per Konstruktion zu Nicht-Skills, die lane-spezifische Sonderlogik entfällt. Nicht tragend und offen so benannt: kein Hersteller-Trend (nicht belegbar — die Doku sagt „keep working", `deprecat|legacy|sunset` liefert **keinen** Treffer), kein Kontextvorteil, keine Argument-Migration.

**Zwei Funde, die keine der Reviews hatte:**
- **Symlinks sind offiziell unterstützt** (`~/.claude/skills/<name>` darf ins Repo zeigen) → Drift wird **strukturell unmöglich** statt detektiert. Manifest, Content-Hash, MANAGED-Footer und Round-Trip-Gate würden für diese Lane entfallen. → ADR-281.
- **Cowork-/Cloud-Sessions inkl. Routinen lesen `~/.claude/skills/` NICHT.** Das gesamte Verteilmodell endet an der Maschinengrenze — unabhängig davon, welche Lane gewinnt. Getrackt als [#1298](https://github.com/achimdehnert/platform/issues/1298) + Option F in ADR-280 §10.

**ADR-281-Belege:** ADR-230 verwarf Symlinks wegen „volatilem Checkout" — der Einwand galt der Volatilität. **ADR-233 (`2026-06-01`) ist jünger als ADR-230 (`2026-05-30`)** und der Guard **erzwingt** nachweislich (`.git/iil-guard-events.log`: 2 `unauthorized_head_flip` vom 2026-07-21, beide zurückgesetzt — aus dieser Session, ich bin selbst hineingelaufen). Dazu: **ADR-230s Rollout-Gate hat 8 offene Checkboxen, 0 abgehakt** — inkl. „Rollback getestet". Es stehen sich zwei *unbelegte* Zusagen gegenüber; gewählt wurde die mit weniger beweglichen Teilen. Eigene Idee (gepinnter Worktree als Symlink-Ziel) an der Faktenprüfung gescheitert: `platform-pinned` ist 11 Commits hinter main und hat **kein** Pflege-Tooling.

**Zwei Werkzeug-Reparaturen, beide durch eigene Fehler ausgelöst:**
- `/adr` Step 3.3 sagte „INDEX.md ergänzen", die Datei trägt aber `AUTO-GENERATED … do not edit manually`. Wer der Anleitung folgt, landet im roten Gate — passiert bei ADR-280. Der Skill hatte **keine Abschluss-Checkliste**; genau die Lücke, durch die ein Pflichtschritt still überspringbar ist.
- `policies/adr-threshold.md` empfahl `ls docs/adr/ | sort | tail -1`. Real ausgeführt liefert das **`reviews`** (ein Unterverzeichnis) statt `ADR-281` — kein Fehler, sondern ein plausibel aussehendes falsches Ergebnis.

**Wissen gesichert (Outline).** Achtung: `search_knowledge` findet beide Dokumente **nicht** (leeres Ergebnis trotz erfolgreicher Anlage, per `get_document` mit Volltext verifiziert) — Discovery läuft daher über den Memory-Eintrag `lesson:platform:20260721-tool-semantics`, nicht über die Outline-Suche:
> - Lesson: `/doc/2026-07-21-werkzeug-semantik-behauptet-statt-in-der-doku-des-laufenden-werkzeugs-nachgeschlagen-vKYm65cvo7`
> - Konzept: `/doc/skill-verteilung-platform-lane-konsolidierung-auf-skills-symlink-statt-kopie-9gcVWVwDIv`

**⚠️ Live-Kopien dieser Maschine sind seit dieser Session von `main` abgewichen** (`doctor.py --kind commands`, 2026-07-21): `copy-stale=4` · `extra=3` · `fehlend=1`. Konkret: **`/adr` läuft live noch mit der kaputten Step-3.3-Anleitung** (`grep -c gen_adr_index.py ~/.claude/commands/adr.md` = **0**, Quelle = **11**); `escalate`/`next`/`issues-offen` liegen als Leichen im `commands`-Ziel, obwohl sie in #1290 nach `skills/` gewandert sind; `delete-repo.md` fehlt seit #1013. Behebung ist `generate.py --allow-live` — das ist der **gegatete** Live-Rollout aus ADR-230 §8, dessen Gate 8 offene Checkboxen hat. **Bewusst nicht ausgeführt** (Owner-Entscheid, verändert die Skill-Installation der Maschine). Bis dahin nutzt jede Session auf dieser Maschine die alte `/adr`-Anleitung.

**Nicht verifiziert:** kein Betriebsnachweis der migrierten Skills (ADR-280 §8.1, sechs Muss-Kriterien definiert, nicht durchlaufen) · kein Symlink-Ladetest (ADR-281 §8.1 — bewusst nicht vorweggenommen, er verändert die Live-Skill-Installation dieser Maschine).

### ⚡ Nachmittag-Session 2026-07-21 (Opus, reaktiv) — trading-hub Prod-Ausfall behoben, Host-Speicherlage getrackt

- **trading-hub war ~16 h mit HTTP 502 offline** ([#1282](https://github.com/achimdehnert/platform/issues/1282)) und ist wiederhergestellt: `https://trading-hub.iil.pet/livez/` **200**, Root **200**, alle fünf Container laufen. Behebung per `workflow_dispatch` auf dem gepinnten Image `main-9411bda` ([run 29829380875](https://github.com/achimdehnert/trading-hub/actions/runs/29829380875), `completed/success`) — bewusst über den ADR-021-Pfad (Compose-SHA-Manifest + atomarer Sync) statt per Hand-`docker compose up`, um die bekannte `-f`-Ketten-Falle zu meiden. Postgres-Volume `trading-hub_trading_hub_pgdata` durchgehend intakt, kein Zustandsverlust.
- **Ursache war kein Deploy-Fehler, sondern eine Speicher-Notlage auf hetzner-prod** am 2026-07-20 18:26–18:48 UTC: cgroup-OOM auf `python` und `gunicorn`, earlyoom bei `mem avail 5,82 %` und `swap free 0,02 %`. Der erste Canary-Alarm (18:42) liegt mitten in diesem Fenster. Der letzte reguläre Deploy lag am 07-16 — die Kiste ist also *von selbst* gestorben, nicht durch eine Änderung.
- **Offen und getrackt ([#1303](https://github.com/achimdehnert/platform/issues/1303)):** **warum die Container entfernt statt neu gestartet wurden, ist ungeklärt** — alle fünf tragen `restart: unless-stopped`, `docker compose ps -a` war trotzdem leer. Ausgeschlossen: `server-maintenance.sh` (prunet nur Builder/Images), `healthcheck.sh` (kein Docker), `docker-cleanup.sh` (So 03:00, vor dem Start am 19.07.), Actions (kein Worker-Log seit 19.07. 05:50), `deploy.sh` (kein Log seit 13.07.). Billigster nächster Check: dockerd-Journal des 20.07. **ohne** Namensfilter.
- **Restrisiko unverändert dünn:** nach dem Restart 3,4 GB verfügbar, **Swap 4095/4095 MB — 0 MB frei**. `swapoff -a` ist in dieser Lage keine Option (zöge 4 GB zurück ins RAM). Vorbereitetes Freimachen (Restart von `iil_authentik_worker` 485/512, `hub137_worker` 305/512, `dms_hub_worker` 137/512 — alle **unhealthy**) wurde **nicht** ausgeführt: der Permission-Classifier blockte den Container-Restart, Owner entschied „direkt deployen". Der Deploy gelang ohne, die Marge blieb damit unangetastet.
- **Handover-Kollision aufgelöst:** [#1299](https://github.com/achimdehnert/platform/pull/1299) und [#1300](https://github.com/achimdehnert/platform/pull/1300) entstanden 99 Sekunden auseinander aus zwei Parallel-Sessions, beide auf `AGENT_HANDOVER.md`. #1299 hatte den Vorab-Check korrekt ausgeführt und nichts gefunden — #1300 existierte da noch nicht. #1299 ist Träger (nur dort die Block-Rotation), #1300 geschlossen. Die strukturelle Lösung dazu liegt bereits als [#1301](https://github.com/achimdehnert/platform/pull/1301) (KONZ-027, Handover-Fragmente je Session) vor.

## ⚡ Vorheriger Stand (2026-07-20/21 — zwei Parallel-Sessions: Mail/Postfach-Strukturierung + Tools-Strang (estimate_job-Fehldiagnose, break-glass-meter, Parallel-Session-Fixes A1/C1))

**Zwei Sessions liefen am 2026-07-20 parallel im selben Repo** (bewusster Provokations-/Härtungstest der Parallel-Session-Mechanik). Beide Stränge hier zusammengeführt — genau der A2-Deckungs-Verlust, der dabei sichtbar wurde: #1283 (Mail-Session-Handover) entstalte nur die Nächste-Schritte-Liste, schrieb aber **keinen** neuen Aktueller-Stand; der Tools-Strang fehlte danach ganz. Dieser Block schließt die Lücke sequenziell (Mail-Session war fertig → kein Parallel-Konflikt mehr).

**Strang A — Mail/Postfach (eigene Session, Memory `session:platform:20260721:mail-struct-ollama-0720`):**
- Postfach achim.dehnert@iil.gmbh strukturiert: Posteingang 2.852 → 1.461, ~1.391 Mails in 4 verifizierten Wellen (Read-back je Welle) in 3-Ebenen-Ordnermodell (kunde/partner/altkunde, Top-Level-Präfix `IIL.*`).
- Ollama auf dev (88.99.38.75) installiert: systemd, bindet **nur** 127.0.0.1:11434, Modell qwen2.5:3b, CPU. Zugriff via SSH-Tunnel.
- **Dienst H (LLM ordnet Partner-Mail dem Kundenprojekt zu) FALSIFIZIERT:** qwen2.5:3b Betreff-Klassifikation 10/10 unklar, Kundendomain in To/CC nur 9% → Partnerordner bleiben Heimat, LLM-Routing verworfen.
- Kundenmail-Draft-Stil-Korrektur (Owner, „weniger KI-like"): erster Satz = Empfehlung, keine „Warum:"-Marker, Bestätigung eingebettet → Memory `feedback_client_mail_style_no_ai_preamble`.
- **Offen:** [#1281](https://github.com/achimdehnert/platform/issues/1281) (graph_mail: `--subject` als UND-Filter zu `--move` + `--draft`-Read-back). Rest-Posteingang ~1.461 schrittweise; 2 Fach-Entwürfe (AVV/Dillingen) als Draft, Owner sendet selbst. Kunden-/Ordner-Zuordnung liegt lokal (`~/.claude/mail-folders.env`, DSGVO, nicht im Repo).

**Strang B — Tools (diese Session, reaktiv aus Session-Start-Findings):**
- **ADR-156-Fehldiagnose korrigiert ([#1278](https://github.com/achimdehnert/platform/pull/1278) gemergt):** Commit `496a35c` (04-29) erklärte `estimate_job`/`discord_notify`/`deploy_check` fälschlich für „existiert nicht mehr (Issue #80)" — reine Prefix-Drift (`mcp2_` → `mcp__orchestrator__`), die Tools leben. `/ship`+`/backup` restauriert, ADR-156 §v3.6-Nachtrag. Live-Beleg: `estimate_job(deploy, risk-hub)` liefert 135s-Schätzung.
- **verify-adr156 falsch-grün gefixt ([mcp-hub#180](https://github.com/achimdehnert/mcp-hub/pull/180), OFFEN — braucht `--admin`):** der Check grepte den nackten String `estimate_job` und matchte damit den Verneinungssatz → `/ship`+`/backup` ~3 Monate falsch-grün. Assertion jetzt auf Aufruf-Form `^mcp__orchestrator__estimate_job:`. **Merge blockiert:** mcp-hub hat 1 Collaborator + Ruleset „1 Approval", GitHub verbietet Self-Approval → Sackgasse, Admin-Bypass nötig (`gh pr merge 180 --admin --squash`, `[skip ci]` da deploy.yml auf push:main triggert).
- **deploy_check-Defekt getrackt ([mcp-hub#181](https://github.com/achimdehnert/mcp-hub/issues/181)):** Tool existiert, scheitert aber server-seitig an fehlender `ports.yaml` — echter Defekt, Server-Pfad, nicht in dieser Session gefixt.
- **break-glass-meter gebaut ([#1279](https://github.com/achimdehnert/platform/pull/1279) gemergt):** KONZ-004 (branch-protection, prod, review_by 11 Tage überfällig) hatte für seine Kill-Gate-Hälfte „≥1 Break-Glass/Woche" **kein Messinstrument** — der bestehende Meter prüft nur Ruleset-Existenz, nicht Umgehungen (`rule-suites?result=bypass`). Zähler + Workflow-Step + Label `break-glass`; Erstmessung 0 Break-Glass (falsifiziert gegen `result=pass`=11). Grenze: rule-suites ist kein Vollarchiv.
- **KONZ-002 §16 (Owner-Entscheidungen 2026-07-20, im selben PR):** (a) Kostenneutralität **Owner-attestiert** (Kriterium verlangt schriftliche GitHub-Bestätigung — Abweichung vermerkt, nicht geglättet); (b) Souveränitäts-Sign-off ttz-lif/meiki-lra **ausgesetzt** bis erste echte Kundendaten (mündliche Zusage, zustandsgebundener Wiederaufnahme-Trigger); (c) Portabilität war seit 06-03 grün (§15). Sunset-Pfad greift nach heutigem Stand nicht.
- **Parallel-Session-Fixes A1+C1 ([#1280](https://github.com/achimdehnert/platform/pull/1280) gemergt):** A1 = `session-memory` überschreibt fremde Session nicht mehr (`--session-id` macht Key eindeutig, sonst Ausweichen auf `-2`); C1 = `tools/session-leases` zeigt im Session-Start-Runner, wer parallel arbeitet. **A1 unter echter Doppellast bewiesen:** die Mail-Session nutzte auf dem frisch gemergten Code das `--session-id`-Flag → eindeutiger Key, keine Kollision.
- **Ausführungstreue-Audit [#1167](https://github.com/achimdehnert/platform/issues/1167) triagiert (Kommentar):** ADR-Seite ohne Retrofit schließbar (kein aktives Doku belegt Umsetzung — 07-09-Datum war 194-Datei-Frontmatter-Sweep, kein Aktivitätssignal); KONZ-Seite verengt auf 4 fällige review_by-Termine (alle 26 haben `kill_criteria`, es fehlt nur Status je Bedingung — Muster #1275/#1169). [#1275](https://github.com/achimdehnert/platform/pull/1275) gemergt.

**Beobachtung Parallel-Session-Mechanik (für spätere solide Lösung, KONZ-Kandidat):** A1 (Memory-Key) hat funktioniert. A2 (Handover) verlor real Deckung — nicht durch konkurrierende PRs (die verhinderte die Disziplin), sondern durch **disjunkte Handover, keiner vollständig**. Das ist „signifikant" i.S. der Beobachtungs-Ansage → solide Lösung (Handover-Fragmente je Session, beim Lesen zusammengeführt) lohnt jetzt. B1 (Merge-Lease) weiter offen.

## Nächste Schritte (kompakt)

> **⚠️ Vor allem anderen — hetzner-prod Speicherlage ([#1303](https://github.com/achimdehnert/platform/issues/1303)):** Swap **4095/4095 MB belegt (0 frei)**, 3,4 GB RAM verfügbar. Der OOM vom 20.07. hat trading-hub 16 h offline genommen; der nächste trifft irgendein anderes Hub. Zusätzlich ungeklärt, **warum** die Container entfernt statt neu gestartet wurden (`restart: unless-stopped` griff nicht). Beides ist Prod-Risiko, kein Aufräumthema — die Nummerierung unten bleibt davon unberührt.

1. **Skill-Lane-Konsolidierung [#1287](https://github.com/achimdehnert/platform/issues/1287) — 4 PRs warten auf 2.-Owner-Review:** [#1294](https://github.com/achimdehnert/platform/pull/1294) (Regression zurück), [#1295](https://github.com/achimdehnert/platform/pull/1295) (ADR-280 Rev 2), [#1296](https://github.com/achimdehnert/platform/pull/1296) (ADR-281 Symlink), [#1293](https://github.com/achimdehnert/platform/pull/1293) (Policy, auto-merge gequeued). Alle CI-grün, 0 rot.
2. **Zwei Nachweise stehen aus, beide bewusst nicht vorweggenommen:** ADR-280 §8.1 Betriebsnachweis der migrierten Skills (6 binäre Muss-Kriterien, definiert nicht durchlaufen) · ADR-281 §8.1 Symlink-Ladetest (verändert die Live-Skill-Installation der Maschine → eigener, gegateter Schritt).
3. **Cloud-Reichweiten-Lücke ohne eigenes Artefakt:** Cowork-/Cloud-Sessions inkl. Routinen lesen `~/.claude/skills/` **nicht** — das gesamte Verteilmodell endet an der Maschinengrenze, unabhängig von der Lane-Entscheidung. Getrackt als [#1298](https://github.com/achimdehnert/platform/issues/1298) (+ Option F in ADR-280 §10).
4. **Print-Agent ruft bei JEDEM PDF einen externen US-LLM** ([#1297](https://github.com/achimdehnert/platform/issues/1297)) — Defaults `cerebras`/`groq` hart im Code (`print_agent.py:268/269`), kein Guard, kein Hinweis. Realer Abfluss am 2026-07-21: Kundenanschrift ging an Groq. Lokales Ollama gemessen ausreichend (3B: 18 s, valides JSON). Kein PR, weil Richtungsentscheid nötig (externe Anbieter künftig nur per Opt-in?).
5. **Review-Stau abgebaut — die 5 Reste sind ROT, nicht wartend:** nur noch [#892](https://github.com/achimdehnert/platform/pull/892)/[#893](https://github.com/achimdehnert/platform/pull/893)/[#986](https://github.com/achimdehnert/platform/pull/986)/[#1005](https://github.com/achimdehnert/platform/pull/1005)/[#1007](https://github.com/achimdehnert/platform/pull/1007) offen — **alle 5 `CONFLICTING`/`DIRTY`** (verifiziert 2026-07-21 via `gh pr view --json mergeable`; Achtung: liefert erst `UNKNOWN`, GitHub rechnet lazy — Re-Poll nötig). Sie brauchen **Rebase**, nicht Review. Ältester Stand 07-11.
6. trading-hub Branch-Protection [#1117](https://github.com/achimdehnert/platform/issues/1117) — bewusst zurückgestellt (App-Repo-Scope), weiterhin offen
7. Ausführungstreue-Audit [#1167](https://github.com/achimdehnert/platform/issues/1167): Nebenfund Namenskollision KONZ-platform-001 weiterhin offen
8. Gate für tote `implementation_evidence`-Pfade ([#1289](https://github.com/achimdehnert/platform/issues/1289)) — erst SUGGEST/non-gating, Baseline sichten vor Gating (sonst Alarm-Müdigkeit).
9. KONZ-018 W1: testkit-Dedup, Freshness-Pilot promptfw
10. Stub-Issues via Sonnet-Session (`/model sonnet` + `/issues-offen`)

> **Erledigt 2026-07-21 (Vormittag, Aufräum- + Infra-Session — Parallel-Session, nicht diese):** **Prio „lügender Index" abgeschlossen** ([#1288](https://github.com/achimdehnert/platform/pull/1288) GEMERGT) — ADR-158 `implementation_status` von `implemented` auf `partial` korrigiert (3 tote Evidence-Pfade unter `packages/docs-agent/`, seit 2026-04-23 in `_ARCHIVED/`), ADR-072-Rollout-Tabelle auf belegten Stand zurückgesetzt. **Bewusst nicht nachgemessen** (wäre Scope-Eskalation in 4 App-Repos) → ungemessene Repos tragen jetzt explizit `❔ nicht nachgemessen`. Gate-Lücke getrackt ([#1289](https://github.com/achimdehnert/platform/issues/1289)) · **Branch-Hygiene: 442 lokale Branches gelöscht (512 → 47)**, Restore-Manifest `~/shared/branch-cleanup-platform-2026-07-21.txt`. **Lehre:** der erste Durchlauf stufte 51 gemergte Branches falsch als „lokal voraus" ein — nicht wegen Divergenz, sondern weil der gemergte `headRefOid` lokal fehlte und der Ancestor-Check scheiterte. Nach `git fetch origin <oid>` waren alle 51 sauber entscheidbar; echte Divergenz lag bei 7, nicht 56.
> **Erledigt 2026-07-21 (Infra-Entscheid GPU, kein Code — Parallel-Session):** Recherche + eigene Messung → **kein GPU-Server gemietet**. illustration-hub läuft auf der vorhandenen RTX 4090, meiki-Pilot + Dokumentenlast auf CPU des Dev-Servers. Gemessen auf 88.99.38.75 (16 Kerne, geteilte Last), Print-Agent-Prompt: `qwen2.5:3b` 7,3 tok/s / 18 s · `7b` 3,6 tok/s / 51 s · `14b` 1,1 tok/s / 153 s — alle valides JSON. Gegenrechnung: Hetzner GEX44 hat **20 GB** (weniger als die 4090; Primärquelle, keine Mindestlaufzeit, FSN1), VRAM-gleicher Scaleway L4 kostet 575 €/Mon netto bei ~⅓ Speicherbandbreite. **Nicht belegt geblieben:** GEX44-Monatspreis (Seite rendert clientseitig), Stromkosten, Preisknick Consumer↔Datacenter — 14 von 25 Recherche-Claims adversarial verworfen. **Auflage für meiki:** gegen austauschbaren OpenAI-kompatiblen Endpunkt bauen, sonst wird der spätere Umzug ins LRA-RZ zum Umbau.
>
> **meiki-Datenklassifikation (Owner-Präzisierung 2026-07-21) — trägt den Entscheid oben:** Der meiki-**Pilot** auf IIL-Infrastruktur arbeitet mit **synthetischen** Daten. Echte Daten erst ab dem **Live-Prod-Testlauf**, und dieser Übergang wird **ausdrücklich kommuniziert**. **Entscheidungsregel: solange keine solche Mitteilung vorliegt, sind meiki-Daten synthetisch** — Abwesenheit einer Mitteilung heißt *synthetisch*, nicht *unklar*. Echte Bürgerdaten liegen im Zielzustand im **LRA-Rechenzentrum**, nicht bei uns. Daraus folgt für den Pilotzeitraum: kein AVV, keine Auftragsverarbeitung, freie Anbieterwahl. Ab dem kommunizierten Umschaltpunkt kippt das vollständig (Backup-Pflicht, AVV-Prüfung, Souveränitäts-Auflagen). Korrigiert die frühere Pauschal-Einordnung „meiki-* hält Prod-Daten" (Stand 06-11), die für den Pilotzeitraum zu streng war; `writing-hub`/`risk-hub` sind davon nicht berührt.
> **Erledigt 2026-07-21 (Skill-Lanes, diese Session):** [#1290](https://github.com/achimdehnert/platform/pull/1290) GEMERGT (Phase 1: 3 Piloten nach `skills/`, Gate + CI-Trigger auf beide Lanes, 5 Tests) · [#1291](https://github.com/achimdehnert/platform/pull/1291) GEMERGT (ADR-280 Rev 1) · [#1292](https://github.com/achimdehnert/platform/pull/1292) GEMERGT (`/adr`-Skill: `gen_adr_index.py` als Pflichtschritt + Abschluss-Checkliste + Anti-Patterns) · [#1118](https://github.com/achimdehnert/platform/pull/1118) GESCHLOSSEN (superseded). **Lehre:** meine tragende Prämisse („`$ARGUMENTS` entfällt unter Skills") war **falsch** — geprüft gegen `claude --version` 2.1.216 + Doku 2026-07-21; zwei externe Zweitmeinungen fanden es, beide empfahlen „überarbeiten". Verifikationsstand mit Versionspin ist seitdem Pflichtblock in ADR-280/281.
> **Erledigt 2026-07-21 (Parallel-Session, nicht diese):** [#1284](https://github.com/achimdehnert/platform/pull/1284) GEMERGT (Handover-Stand 07-20/21) · [#1013](https://github.com/achimdehnert/platform/pull/1013) + [#954](https://github.com/achimdehnert/platform/pull/954) GEMERGT.
> **Erledigt 2026-07-21 (Abend, ADR-Evidence-Strang — eigene Session, parallel zur Nachmittags-Session):** **PR-Stau der 5 DIRTY-PRs aufgelöst** — [#986](https://github.com/achimdehnert/platform/pull/986) / [#1005](https://github.com/achimdehnert/platform/pull/1005) / [#1007](https://github.com/achimdehnert/platform/pull/1007) rebased (alle grün), [#892](https://github.com/achimdehnert/platform/pull/892) + [#893](https://github.com/achimdehnert/platform/pull/893) als von `main` überholt geschlossen (Commit `3d71952` hatte beides bereits umgesetzt; #893 hätte eine scharfe Gate-Stufe zurückgedreht). Funde beim Rebase: Archiv-Namenskollision (zwei Generationen `generate_project_facts.py`), `.windsurf/workflows/onboarding-new-repo.md` via ADR-280 gelöscht. · **ADR-234 §11.3 präzisiert** ([#1007](https://github.com/achimdehnert/platform/pull/1007)): der „Dual-Generator"-Befund ist output-seitig widerlegt — die beiden Skripte schreiben verschiedene Artefakte, A3 war nie eine Deduplizierung; Beschluss bleibt, Begründung korrigiert. · **77 project-facts-Dateien archiviert** ([#1306](https://github.com/achimdehnert/platform/pull/1306), [#1304](https://github.com/achimdehnert/platform/issues/1304)) — 0 Leser verifiziert; der ursprünglich geplante Header-Sweep wäre **falsch** gewesen (anderes Ziel, anderes Format). · **#1289 erledigt** → Evidence-Pfad-Check [#1312](https://github.com/achimdehnert/platform/pull/1312) (SUGGEST, 23 Tests) + Bereinigung [#1318](https://github.com/achimdehnert/platform/pull/1318) ([#1311](https://github.com/achimdehnert/platform/issues/1311)): **16 Findings → 0 ohne einen Ignore-Eintrag**, 10 ADRs; 7 FPs verifiziert ausgeschlossen (`orchestrator_mcp` = Teilspiegel, `packages/django-tenancy` liegt in **risk-hub**, ADR-246 in **iil-pet-portal**). · **noop-Check** [#1322](https://github.com/achimdehnert/platform/pull/1322) aus eigenem Fehler: `ruff format tools/` + `git add -A` schleuste 95 Fremddateien in #1312 (repariert, 4 Dateien). **Lehren:** (a) ein Frontmatter-Parser-Bug ließ den Evidence-Check am eigenen Anlassfall ADR-158 vorbeilaufen — nur die Tests fanden es; (b) `git diff --name-only -w` wertet `-w` **nicht** aus (Blob-Hash-Vergleich), ein darauf gebauter Detektor meldet falsch-grün; (c) „alle Packages jetzt in eigenen Repos" (Commit `2cc7289`) stimmt nicht — 6 von 7 leben nur als PyPI-Dist. **Offen:** alle 7 PRs BLOCKED = warten auf 2.-Owner-Review; Gating-Promotion beider Checks erst nach Merge von #1318.
> **Erledigt 2026-07-21 (Nachmittag, Tools-Strang-Fortsetzung + KONZ-027 + Doppel-Retro, diese Session):** [mcp-hub#180](https://github.com/achimdehnert/mcp-hub/pull/180) GEMERGT (admin-Bypass, auditiert — verify-adr156 nicht mehr falsch-grün) · **KONZ-027 Handover-Fragmente** ([#1301](https://github.com/achimdehnert/platform/pull/1301) GEMERGT, `pipeline_status: pilot`) — 2 externe Cross-Provider-Reviews fanden unabhängig 3 fatale Design-Fehler → R1-Revision; **A/B-Pilot [#1302](https://github.com/achimdehnert/platform/issues/1302): merge=union (empirisch getestet, ~5 Z.) vs. Fragment-Maschinerie** (`model:sonnet-5`) · Retro-Follow-ups [#1309](https://github.com/achimdehnert/platform/pull/1309) GEMERGT (B1-Docstring-Overclaim, ADR-156↔#181-Link) · **Haupt-Retro [#1308](https://github.com/achimdehnert/platform/pull/1308) GEMERGT** (full, 8/11 survived) + **Increment-Retro [#1313](https://github.com/achimdehnert/platform/pull/1313)** (lean) + Skill-Schärfung [#1316](https://github.com/achimdehnert/platform/pull/1316) (stale-clone: nach fetch aus dem Ref lesen). **Offen (execution-ready, `model:sonnet-5`):** [#1302](https://github.com/achimdehnert/platform/issues/1302) A/B-Pilot · [#1310](https://github.com/achimdehnert/platform/issues/1310) verify-adr156-CI-Gate. **Gate-pflichtig rezidiv:** parallel-session-pr-collision (×3, KONZ-027-Pilot ist der Fix), stale-local-clone (×8).
> **Erledigt 2026-07-21 (Abend, #1302/#1310 in Umsetzung — an Sonnet delegiert):** [#1302](https://github.com/achimdehnert/platform/issues/1302) **Arm A gebaut** ([#1319](https://github.com/achimdehnert/platform/pull/1319), offen): `merge=union` auf AGENT_HANDOVER.md + append-only-Konvention; Pilot-Check 1 (server-side Squash ehrt merge=union?) offen bis echter Parallel-PR. · [#1310](https://github.com/achimdehnert/platform/issues/1310) **CI-Gate gebaut** ([#1320](https://github.com/achimdehnert/platform/pull/1320), offen): `workflow_tool_ref_check.py` — Golden-Test verifiziert (Verneinung→FAIL, Aufruf-Form→PASS). · [mcp-hub#182](https://github.com/achimdehnert/mcp-hub/pull/182) (offen, **braucht --admin**): 9 `.py`-Checks in verify-adr156 verschärft. **Nicht im Repo (DSGVO, lokal ~/shared/risk-hub/Feha/):** Feha↔MVZ-DLG TOM-DSB-Beratung — ausfüllbares AcroForm-PDF (188 Felder) + Begleitnotizen + Louzri-Antwort-Entwurf; Kern: TOM-Fragebogen ≠ C5 (separate Instrumente).
> **Erledigt 2026-07-20/21 (Tools-Strang + Mail, 2 Parallel-Sessions):** [#1278](https://github.com/achimdehnert/platform/pull/1278) (estimate_job-Fehldiagnose) · [#1279](https://github.com/achimdehnert/platform/pull/1279) (break-glass-meter, KONZ-004) · [#1280](https://github.com/achimdehnert/platform/pull/1280) (A1 Memory-Key + C1 Lease-Sicht) · [mcp-hub#181](https://github.com/achimdehnert/mcp-hub/issues/181) (deploy_check-Defekt getrackt) · Mail-Postfach strukturiert + Ollama-on-dev + Dienst-H falsifiziert ([#1281](https://github.com/achimdehnert/platform/issues/1281) offen).
> **Erledigt 2026-07-20:** [#1275](https://github.com/achimdehnert/platform/pull/1275) GEMERGT (Ausführungstreue-Umsetzung, KONZ-001+004 Kriterium→Status-Tabellen) · [#1115](https://github.com/achimdehnert/platform/issues/1115) GESCHLOSSEN (usage-sweep: Labels behalten, 36 Skills zurückgebaut via #1257, 3 sunset-reife Skills source- **und** dist-seitig entfernt; Kill-Kriterium *nicht* erfüllt → Sweep läuft weiter) · [#1271](https://github.com/achimdehnert/platform/issues/1271) GESCHLOSSEN (cc-skill-dist DRIFT-SCORE 44→0; alle 35 Orphans durch den einen Rückbau-Commit `cfa9c0f` erklärt, Zweitquellen-Hypothese falsifiziert). **Methodik-Auflage nächster Sweep:** „keine kanonische Source" ist **kein** Tot-Signal — trifft auch frisch zurückgebaute Skills; Status steckt im löschenden Commit (`doctor.py --kind commands` + Orphan↔Commit-Diff vor Teardown).
> **Erledigt 2026-07-19:** Owner-Block #1094 komplett + geschlossen (7/7 OIDC-Bindungen, 3 Pakete live, 4 Alt-Dubletten geyankt, 2. Owner) · ADR-278 accepted (#1266) · codeguard/ingest OIDC (#1267) · django-commons#12 + learnfw#9 Auth-Fixes · shared-ci publish-auth-guard v1.0.13 · #1265 zu, #1268 (Portfolio) ausgelagert · Handover-PR #1171 (stale) geschlossen · **Guard Block-Flip scharf** (shared-ci#33) + v1.0.14 fleet-weit gebumpt (promptfw#32/outlinefw#19) → ADR-278-Enforcement komplett.
> **Erledigt 2026-07-19 (Abend-Session):** #1167-Umsetzungsschritt geliefert (#1275: KONZ-001 + KONZ-004 Kriterium→Status-Tabellen; KONZ-016/018 begründet ausgelassen) · **#1276 GEMERGT** — systemischer ADR-Frontmatter-Blocker (6 ADRs, deprecated Keys) fleet-weit gefixt, `validate` 225/225 · ADR-272-Nummernkollision gelöst (#1077 → ADR-279 umnummeriert, #1086 behält 272) · **Review-Stau von 6 auf 0 rote PRs** (#1027/#1026 gemergt; #1112/#1231/#1141/#1086/#1077/#1225 grün gezogen). **Lehre:** „stale-Index" war bei #1231/#1141 die *falsche* Erst-Diagnose — echter Root-Cause war der repo-weite Schema-Verstoß; ein Log-Blob (base64-HTML) verdeckte bei #1225 einen simplen transienten 503.
> **Erledigt 2026-07-19 (Session-Start-Folgesession):** #1268 geschlossen (Portfolio: alle 6 Pakete behalten) · #1158 geschlossen (`secrets:inherit`: coach-hub bereits auf origin/main gefixt, risk-hub **False Positive** — same-org `iilgmbh` + keine private git-Dep) · #1115 Sweep-Entscheid (Labels behalten; Skill-„tot"-Signal via cc-skill-dist-Drift widerlegt → #1271) · #1167 Stichproben-Audit fortgesetzt (~8 Fix-Kandidaten). **Lehre:** #1 (Guard) + coach-hub-Teil von #2 waren bereits erledigt — nur sichtbar durch konsequente origin/main- statt lokale-Klon-Prüfung.
> **Erledigt 2026-07-18 (Session-Start-Reconciliation, keine neue Arbeit):** Orchestrator-MCP wieder funktional — „Invalid Bearer Token" nicht mehr reproduzierbar, live verifiziert per 3 erfolgreichen Tool-Calls (`agent_memory_search` + `check_recurring_errors` + Outline-Search) am 2026-07-18; Ursache des Wieder-Funktionierens unbekannt (nicht untersucht) · Haupt-Retro [#1162](https://github.com/achimdehnert/platform/pull/1162) ist MERGED + APPROVED (war als „offen" geführt, Handover war stale).
> **Erledigt 2026-07-15:** cad-hub#42 (war schon vor Session-Start gemergt, Handover war stale) · trading-hub#150 · coach-hub#40 · ADR-270-Vorbedingung (#1152) · Increment-Retro (#1165) · session-start-Checkliste-Nachbesserung (#1166).
> **Erledigt 2026-07-13 (nachgezogen, war nur in PR #1122 unmerged dokumentiert):** KONZ-017 W1 sync-drift-meter #998 (#1009 gemergt) · usage_sweep.py (#1116 gemergt) · trading-hub Deploy-403 (#1070 zu) · PyPI-OIDC-Readiness codeguard/ingest (#1118 gemergt) · trading-hub PR #130 (README-Fix, inzwischen gemergt).

> **Ältere Stände** (2026-07-10 Mail-Skill, 2026-06-20 F4/Wave-2 usw.) → [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md).

## 0. Aktuelle Prioritäten (2026-07-02 — verifiziert via API/Fleet-Scan)

| Prio | Task | Tier |
|---|---|---|
| 1 | **ADR-242 Wave 3** — Tracking **[#811](https://github.com/achimdehnert/platform/issues/811)**. **Realer Stand 2026-07-10 (gegen #811+Retro abgeglichen, weiter als der Issue selbst zeigt):** Phase 1 (learn-hub, recruiting-hub, travel-beat) komplett, gemergt UND live Wave-3-geschützt. Zusätzlich 3 Repos außerhalb der ursprünglichen Worklist live geschützt (weltenhub, illustration-hub, research-hub) — **nachträglich offiziell in #811 aufgenommen** (Entscheid Achim 07-10). Phase 2 (~23 Standalone-Libs): 13/23 verifiziert+gemergt; Rest-Kohorte in **[#987](https://github.com/achimdehnert/platform/issues/987)** (Task A: gaeb-toolkit/riskfw/weltenfw nur PR-Head-Verify; Task B: outlinefw/promptfw gated auf shared-ci#20); 5 strukturell exkludiert. Formales Phase-3-Apply-Artefakt (`wave3-repos.json` + `apply-branch-protection.yml wave=3` + Negativ-Test + Meter) **existiert noch nicht** — die 6 Live-Rulesets liefen ad-hoc außerhalb dieses Prozesses. | `[Sonnet, via #811]` |
| 2 | **Deploy-Health** (separates Programm, **nie autonom** — Owner/Infra). **Re-Check 2026-07-02: weitgehend geheilt** — onboarding-hub grün (seit 06-24), 137-hub grün (seit 06-21), weltenhub grün (07-01, cancelled=Concurrency benign); dms-hub weiter `cancelled` (benign, letzte Runs 06-09). **tax-hub „Issue Triage" 3× failure (07-01/02)** — Root-Cause `Input required and not supplied: github-token` (Repo hat 0 Secrets, `PROJECT_PAT` fehlt; risk-/coach-hub identisches Muster + PAT = grün). **Fix-PR iilgmbh/tax-hub#20 offen** (Fallback `PROJECT_PAT \|\| github.token`; Self-Approval-Block → wartet auf Owner-Merge; bei Merge `[skip ci]` beachten — deploy.yml feuert auf push:main ohne paths-Filter). Alternative: PROJECT_PAT als Secret setzen (Owner). | `[du/Owner]` |

> **Fortschritt 2026-07-03 (Session 54a76c):** Prio 1 (Wave 3): Scope +„Registry-Konsistenz required machen" (#811-Kommentar — Check ist heute NICHT required, nur `guardian`; Realfall #883/#884/#885 mergten rot). Prio 2 (Deploy-Health): **ADR-264 accepted** = strategischer Rahmen steht; travel-beat-Deploy wieder grün (#57); mcp-hub `/mcp` live; Rest-Item = shared-ci#17-Rollout.
>
> **Fortschritt 2026-07-06 (ERLEDIGT):** **Prio 1 — Wave-3 Phase 1 KOMPLETT** (alle 3 gemergt, `ci / gate` real grün verifiziert): learn-hub#25 (`name:"CI"`-Override raus) · recruiting-hub#13 + travel-beat#62 (**Option A1 = additiver `ci`-Job neben bestehender bespoke Test-CI**, kein Coverage-Verlust — der ursprüngliche #811-Befund „KEIN PR-getriggertes ci.yml" war für beide veraltet). recruiting#10/travel#55/learn#23 auto-closed. **Nächster Wave-3-Schritt = Phase 2** (~23 Standalone-Libs, Worklist in #811), dann Apply. **Prio 2 — Deploy-Health geheilt + live:** billing-hub 403 = **Package-`Manage Actions access` fehlte dem Repo** (NICHT Workflow — identische deploy.yml wie cad-hub, das grün pushte); Owner-Fix im Package-Setting → Rerun grün, `billing.iil.pet/healthz` 200. cad-hub = transienter GHA-Cache-Timeout → Rerun grün, `nl2cad.de/healthz` 200. **Neu: Runbook `docs/runbooks/ghcr-403-push-actions-access.md` (#967) + CC-Memory `reference_ghcr_403_push_package_actions_access`.**

> **Fortschritt 2026-07-08 (unmerged geblieben, PR #985, jetzt konsolidiert):** Phase 2 zu 13/23 verifiziert+gemergt; shared-ci#20-Blocker gefunden; Rest-Kohorte in #987 aufgeteilt (Task A/B). Details: s. Aktueller Stand.
>
> **Fortschritt 2026-07-09/10 (ABGEGLICHEN gegen #811 + Retro, 2026-07-10):** Wave-3-Ruleset live auf 6 Repos (nicht 9 — Memory-Zahl war falsch, korrigiert gegen Retro-Ground-Truth), davon 3 außerhalb der #811-Worklist (weltenhub/illustration-hub/research-hub, jetzt nachträglich aufgenommen) + Live-Incident selbst behoben; ADR-270 accepted. **Formales Phase-3-Apply-Artefakt fehlt weiterhin.** Details: s. Aktueller Stand + #811-Kommentar.
>
> **Fortschritt 2026-07-10 (NEU, offen):** weltenhub-Redis-Incident gelöst (s. Aktueller Stand). Drei Folge-Items offen, alle Human-Decision/Freigabe, keine autonome Ausführung: (1) `ausschreibungs-hub-staging` authentik-Provider/-Application vorbereitet (client_id/signing_key/scopes/redirect geklärt gegen risk-hub-Referenz-Pattern), Freigabe-Block gestellt, Session endete vor Bestätigung — nächste Session kann direkt ausführen, kein erneutes Research nötig. (2) `staging-demo.schutztat.de` DNS-Record (→178.104.184.168) — Entscheid offen. (3) "platform"-Governance-DB (`PLATFORM_DB_HOST=bfagent_db`, degradiert aifw-AI-Features) — Entscheid offen, braucht erst Konsumenten-Inventar. (4) KONZ-platform-015 liegt lokal in `platform` (untracked, main geschützt) — braucht Worktree+PR zum Mergen, dann User-Accept-Entscheid für die Empfehlungen REC-1..REC-7. (5) **Deploy-Health-Scan (session-start) fand 3 neue `failure`** auf coach-hub/trading-hub/pptx-hub, nicht triagiert — s. Aktueller Stand.

> **PR-Hygiene (erledigt 2026-07-02, Freigabe Achim):** #753 + #746 geschlossen (Duplikate von gemergtem #808) · **#760 gemergt** (Registry iil-adrfw/codeguard — Registry-Lücke zu) · **#759 gemergt** (gen_adr_index.py; Rebase-Konflikt in INDEX.md durch Generator-Lauf gelöst, 206 aktive + 48 archivierte ADRs indiziert).

> **✅ Retired/erledigt (2026-06-24, hart verifiziert — billigster Check gemacht):**
> - **F4 CI-grün** als Code-CI-Programm GESCHLOSSEN (Fleet-Scan: 0 Lint/Test/Coverage-Rot; alle Roten = Deploy-Stage). **Kein Sonnet-Material mehr** — nicht erneut als Sonnet-Queue listen.
> - **coach-hub #28** gemergt 2026-06-15 (+ Dep-Fix #31, PAT/Org-Transfer). Strang zu.
> - **ADR-242 Wave 1+2** live (11 Repos geschützt, `ci / gate`).
> - **F1 `.windsurf`-Nachzügler** gesweept (lastwar-bot, iil-voice-agent) — F1 ist KEIN Einmal-Endzustand, periodisch `tools/f1-windsurf-sweep.sh` (dry-run) gegen die API laufen lassen.

**✅ Erledigt (2026-06-10):** weltenhub#16 gemergt verifiziert → **ref-sweep 12/12 komplett** · **research-hub#6** gemergt (2 teardown-Bugs gefixt: async-ORM-Connection-Leak + flush-CASCADE vs django_tenancy-FK).

**✅ Erledigt (2026-06-09):** wedding-hub#19 · onboarding-hub#2 · weltenhub pytest-Fixes · F4-Fixes: weltenhub 5, wedding-hub 3, onboarding-hub 1 · **shared-ci `v1.0.2` + `v1.0.3`** · **mcp-hub#106** + **trading-hub#14** · 11/12 ref-sweep-PRs.

**✅ Erledigt (2026-06-08):** F4-acute (alle 6 `ai-assignable`-Issues closed) · ADR-212 Phase-1 (dev-hub#81 merged) · F1 .windsurf-Untrack vollständig (0 `.windsurf`-Files auf origin/main).

**KONZ-002 Enterprise-Konsolidierung:** Kill-Gate **(c) Portabilität ✅ erfüllt** (Feuerübung Runde 1, 2026-06-03; §15 D1-konform). Offen nur **extern**: (a) Kostenbestätigung + (b) Government-Sign-off, Frist **2026-08-15** — User-getrieben, keine Coding-Prio. Richtung ALT-D, Umsetzung gegated.

**CC-Skill-Dist** (platform): Drift-Score live prüfen — `python3 tools/cc-skill-dist/doctor.py` (Zahl driftet mit jedem neuen/geänderten Skill, hier nicht einfrieren)

---

## 1. MCP-Server & Tool-Calls

**Claude Code (aktuell, `mcp__<server>__<tool>` Format) — wichtigste Tool-Calls:**
- GitHub: `mcp__github__create_issue`, `mcp__github__get_pull_request`
- Memory: `mcp__orchestrator__agent_memory_context(task_description, top_k=5)`
- Deploy-Status: `mcp__orchestrator__deploy_check(action="health", repo=...)`
- Browser: `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`

**Server-Übersicht (7):**

| Server | Zweck |
|--------|-------|
| **deployment-mcp** | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx, CI/CD |
| **github** | Issues, PRs, Repos, Branches, Files, Reviews, Search |
| **orchestrator** | Memory (pgvector), Task-Analyse, Agent-Team, Tests, Lint |
| **outline-knowledge** | Wiki: Runbooks, Konzepte, Lessons, ADR-Suche |
| **paperless-docs** | Dokumente, Rechnungen, Archive |
| **platform-context** | Architektur-Regeln, ADR-Compliance, Banned Patterns |
| **playwright** | Browser-Automation, UI-Tests, Screenshots, Network |

### Windsurf-Legacy (kein Coding mehr, ADR-230)

Windsurf-Agents nutzten die o. g. Server über numerische Prefixe (`mcp0_`–`mcp6_` in
derselben Reihenfolge wie oben). Seit ADR-230 wird Windsurf **nicht mehr zum Coden**
eingesetzt (nur ADR-Review-Subset) — die Prefix-Tabelle ist nur noch für das Lesen
alter Sessions/Logs relevant, kein aktives Interface mehr.

---

## 2. Hetzner Infrastructure

| Rolle | IP | User |
|-------|-----|------|
| **Prod-Server** | `88.198.191.108` | `root` (via SSH-Key) |
| **Dev-Server (WSL)** | `localhost` | `devuser` |

**Kritische Regeln:**
- `devuser` hat **KEIN sudo-Passwort** → System-Pakete: `ssh root@localhost "apt-get install -y <pkg>"`
- PROD: nur read-only via MCP — Deploys über `scripts/ship.sh` oder CI/CD
- **NIEMALS** `ping` für Server-Check — Hetzner blockiert ICMP. TCP-Check stattdessen.

**Secrets:**
- Lokal: `~/.secrets/` (einzige Location seit 2026-05-30 — `~/shared/secrets/` konsolidiert + leer)
- Server: `/opt/shared-secrets/api-keys.env` (chmod 600, root-only)
- Repo-spezifisch: `.env.prod` (nie in Git)

---

## 3. Deploy Targets (Prod — 88.198.191.108)

| Repo | Domain | Health |
|------|--------|--------|
| `risk-hub` | schutztat.de | https://schutztat.de/healthz/ |
| `coach-hub` | kiohnerisiko.de | https://kiohnerisiko.de/healthz/ |
| `billing-hub` | billing.iil.pet | https://billing.iil.pet/healthz/ |
| `travel-beat` | travel-beat.iil.pet | https://travel-beat.iil.pet/healthz/ |
| `weltenhub` | weltenforger.com | https://weltenforger.com/healthz/ |
| `trading-hub` | trading-hub.iil.pet | https://trading-hub.iil.pet/healthz/ |
| `cad-hub` | nl2cad.de | https://nl2cad.de/healthz/ |
| `pptx-hub` | prezimo.com | https://prezimo.com/healthz/ |
| `ausschreibungs-hub` | bieterpilot.de | https://bieterpilot.de/healthz/ |
| `dms-hub` | dms.iil.pet | https://dms.iil.pet/healthz/ |
| `wedding-hub` | wedding-hub.iil.pet | https://wedding-hub.iil.pet/healthz/ |

**Deploy-Befehl:** `bash ~/github/platform/scripts/ship.sh <repo>`
**Health-Check:** `mcp2_deploy_check(action="health", repo="<repo>")`

---

## 4. Master Repo Identifier

**Alle Repos in einer Registry** (Anzahl live: `python3 -c "import yaml; print(len(yaml.safe_load(open('registry/canonical.yaml'))['repos']))"`):

```bash
# project-facts.md für alle Repos generieren (nur fehlende)
python3 ~/github/platform/scripts/gen_project_facts.py

# Alle neu generieren
python3 ~/github/platform/scripts/gen_project_facts.py --force

# Einzelnes Repo
python3 ~/github/platform/scripts/gen_project_facts.py risk-hub
```

- Registry: `platform/scripts/repo-registry.yaml`
- Output: `<repo>/.windsurf/rules/project-facts.md` (trigger: always_on)
- Läuft automatisch bei `/session-start` (Step 0.3b) und `/session-ende` (Phase 3.2)

---

## 5. CC-Skills & Windsurf Rules

**CC-Skills (primär, ADR-230):** Quelle `platform/.windsurf/workflows/` → verteilt nach `~/.claude/commands/` via `cc-skill-dist`:
```bash
python3 ~/github/platform/tools/cc-skill-dist/generate.py --target ~/.claude/commands --allow-live
python3 ~/github/platform/tools/cc-skill-dist/doctor.py   # Drift-Check
```

**Windsurf Rules** (nur ADR/Review-Subset, kein Coding mehr seit ADR-230):
- Quelle: `platform/.windsurf/rules/` + `platform/.windsurf/workflows/` (tool_targets: windsurf-review)
- Verteilen: `python3 tools/cc-skill-dist/windsurf-subset.py`

**project-facts.md** (repo-spezifisch, generiert):
```bash
python3 ~/github/platform/scripts/gen_project_facts.py          # nur fehlende
python3 ~/github/platform/scripts/gen_project_facts.py --force  # alle
```

---

## 6. GitHub

**Account:** `achimdehnert`
**MCP:** `mcp1_*` für alle GitHub-Operationen
**Reusable Workflows:** `achimdehnert/platform/.github/workflows/_ci-python.yml` etc.

**Repo-Kategorien:**
- **Django Hubs** (21): risk-hub, coach-hub, billing-hub, cad-hub, trading-hub, pptx-hub, travel-beat, weltenhub, wedding-hub, recruiting-hub, dms-hub, ausschreibungs-hub, illustration-hub, research-hub, writing-hub, learn-hub, dev-hub, odoo-hub, 137-hub, bfagent, tax-hub
- **Python Libraries** (14): aifw, authoringfw, promptfw, illustration-fw, learnfw, weltenfw, outlinefw, researchfw, testkit, iil-reflex, iil-ingest, iil-enrichment, iil-fieldprefill, nl2cad
- **Infra** (5): platform, mcp-hub, infra-deploy, iil-relaunch, lastwar-bot

(Diese Kategorien sind kein vollständiges Abbild von `registry/canonical.yaml` — Gesamtzahl
live siehe oben unter §4; bei Abweichung ist die Registry maßgeblich, nicht diese Liste.)

---

## 7. pgvector Memory (Orchestrator)

| Parameter | Wert |
|-----------|------|
| **Container** | `mcp_hub_db` (Image: `pgvector/pgvector:pg16`) |
| **Läuft auf** | Prod-Server `88.198.191.108` |
| **Port auf Prod** | `127.0.0.1:15435` (Host-Binding des Containers) |
| **Lokaler Zugriff** | `localhost:15435` via SSH-Tunnel |
| **systemd Service** | `ssh-tunnel-postgres` (dev desktop, User `adehnert`) |

```bash
# Status prüfen
ss -tlnp | grep 15435
systemctl is-active ssh-tunnel-postgres

# Manuell starten (ohne sudo)
ssh -N -L 15435:localhost:15435 -i ~/.ssh/id_ed25519 root@88.198.191.108 &

# Via systemd (empfohlen — Autostart bei Neustart)
sudo systemctl start ssh-tunnel-postgres
```

- **Kein Fallback auf Cascade Memory** — pgvector MUSS laufen
- Tunnel-Ziel: `remote:localhost:15435` (nicht `:5432` — der Container bindet auf 15435)
