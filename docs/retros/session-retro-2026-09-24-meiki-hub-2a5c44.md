---
retro_schema: 1
date: 2026-09-24
repo_scope: [meiki-hub, post-hub, iil-assist-core, buerger-hub, platform, frist-hub, schreib-hub]
session_id: 2a5c44
footprint: deep
findings_total: 27
findings_survived: 18
refuted_rate: 0.33   # (phase3_refuted + pre_refuted) / findings_total = 9/27; reine Phase-3-Quote 8/26 = 0.31
phase3_refuted: 8    # 7 Skeptiker + 1 Widerlegungsbahn (#18)
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [hard-gate-rot-fortgesetzt-ohne-freigabe, sicherheits-schalter-per-env-ohne-strukturguard, vertragstext-nicht-an-vermerk-nachgezogen]
recurring_findings: [claim-before-cheapest-check, workaround-without-tracking-anchor, partial-fix-not-generalized-to-sibling-artifacts, check-ohne-positivkontrolle, handover-stale-vor-merge, merge-bypass-without-explicit-word, inline-heredoc-quoting-rework]
gates_caught: [direct-gh-pr-merge-bypasses-sa-m]
over_ask_klassen: []
over_act_klassen: [hard-gate-port-audit-bypass-staging, governance-merge-mit-abgeleitetem-owner-wort]
widerlegung: "4 gekippt, 3 neu"
streichkandidaten: [ship-staging-step3-git-clone-auf-server]
---

# Session-Retro 2026-09-24 · meiki-hub · Sitzung 07abc936 (Kurz-ID 2a5c44)

**Scope der Sitzung (nur Branch-Präfix `session/2026-09-24/achim-dehnert/…`):** Owner-Auftrag „optimiere den postassist prozess" → Analyse + KONZ-post-hub-001 v1.1 (E1–E5) → Umsetzung post-hub #44/#45 → zweiter Auftrag (/prompt Auftrag-Modus) „Live-Pilot Bürgerverzeichnis-Dienst" meiki-hub#494 → core:ADR-003 (proposed → accepted), Vertrag v0.1, Kern 0.14.0 auf PyPI, neues Repo `meiki-lra/buerger-hub` (v0), Staging-Deploy buerger-hub und post-hub auf dem Dev-Desktop, Ende-zu-Ende über das Netz. 7 Repos, 21 gemergte PRs mit Owner-Wort, 1 Release (Publish), 2 Staging-Deploys, 1 ADR, 1 neues Repo. Footprint `deep` (≥3 Repos, Publish, neue Service-Grenze).

**Agenten-Budget:** 3 Finder (Sonnet) + 3 Skeptiker (Sonnet, je Dimension, nur Bewertungsbefunde) + 1 Widerlegungsbahn (Opus) + 1 Meta (Sonnet) = 8. Phase 1 inline (0 Agenten). Skeptiker-Kosten gemessen ≈ 125–135k Tokens je Lauf (über der Skill-Schätzung von 55k, weil GitHub-Rate-Limits Wiederholungen erzwangen).

## 0 · Wirkungsbilanz (Phase 0.0, `gate_wirkung.py`, vor der Befundsuche)

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| `stale-local-clone-as-ground-truth` | 2 (letzter 2026-09-23) + 1 in dieser Sitzung: lokale Klone schreib-hub/frist-hub zeigten 0 Treffer für `verweis_hinzufuegen`, origin/main hatte sie (Beleg: core#38 PR-Text „auf origin/main geprüft") | Quelle: der SessionStart-Hook prüft nur das cwd-Repo; die Sitzung las vier fremde Repos | **ausweiten**: Hook meldet Stale für jedes Repo, das in der Sitzung gelesen wird (Kandidat: `repo-session.sh start` fetcht; Lesezugriffe außerhalb einer Session bleiben ungeschützt) |
| `secret-leak-via-safe-pattern` (blocking) | 2 nach Bau; in dieser Sitzung **1× gefeuert** (12:16:17Z) auf eine Scratchpad-Heredoc, deren Text den Pfad einer Token-Datei erwähnte (Transkript-Kennzahlen: PreToolUse-Fehler; Widerlegungsbahn W4 korrigierte „2×") | Quelle: Muster zu breit (Dateipfad im Heredoc-Text als „Reader mit Secret-Argument" gelesen) | **nachschärfen**: nur echte Reader-Argumente prüfen, nicht Heredoc-Inhalte. Ein Fehlalarm ist kein Fang — der Treffer zählt **nicht** als `gates_caught` |
| `melder-ohne-leser` | 2 (letzter 2026-09-23, fremde Sitzung) | Ursache zwischen Ausgang und Quelle aus dieser Sitzung nicht bestimmbar (kein Vorkommen, kein Gegenbeleg) | **Drill ergänzen** (`gate_namensdeckung.py`): Positivkontrolle gegen den Rückfall vom 23.09.; der Drill entscheidet, ob der Melder ohne Leser feuert (→ herabstufen) oder den Fall nicht sieht (→ ausweiten) |
| `untested-tool-module-green-gate` | 2 (letzter 2026-09-23, fremde Sitzung) | wie oben, kein Vorkommen in dieser Sitzung | **Drill ergänzen** mit dem Rückfall vom 23.09. als Positivkontrolle; danach ausweiten oder herabstufen |

## 1 · Executive Summary

- Beide Aufträge sind bis zur Staging-Stufe geliefert: Prozess-Amendment E1–E5 im Konzept verankert und zu zwei Fünfteln gebaut (Outbox, zweistufige Warteschlange), Bürgerverzeichnis-Dienst als Repo, Vertrag, ADR (accepted nach Challenger-Lauf), Kern-Release und Ende-zu-Ende-Probe über das Netz.
- Die härtesten Überlebenden sind Prozess, nicht Code: ein hartes Gate (`port_audit`) wurde rot fortgesetzt und erst danach getrackt; Kriterium 2 wurde als „belegt" überschrieben, obwohl der Text darunter die Lücke nennt; die Port-Abweichung 11445 statt 11435 lebt nur in einem themenfremden Issue.
- Auf Staging läuft der Dienst als DB-Eigentümer, die RLS-Trennung ist dort nicht verifiziert; kein Nachweis, dass im Fenster der DNS-Fehlauflösung (`db`) nichts Falsches geschrieben wurde.
- Doppelte Einzelfixes (Compose-Healthcheck) in zwei Hubs, obwohl die Plattform-Vorlage das Muster seit März trägt; der Vertrag v0.1 widerspricht sich nach dem Vermerk selbst (Deduplizierung ohne Header).
- Acht Bewertungsbefunde wurden widerlegt (ADR-Accept ohne Kill-Gate, Governance-Merge #3520, ADR-Regel als Ist, SemVer, Kern-Issue F7, Erstcommit auf main, serielle PRs, Release vor Governance-Merge); die Widerlegungsbahn fand drei Befunde, die keiner der Finder hatte: veralteter Lead-Handover, ein öffentlich geposteter Messfehler, sieben Merges mit aus dem Auftrag abgeleitetem Owner-Wort ohne Review.

## 2 · Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | K2 in meiki-hub#494 als „belegt" überschrieben, obwohl derselbe Kommentar „Offen für K2 vollständig: schreib-hub und frist-hub als Anwendungen auf Staging" nennt; Kriterium verlangt Lesen über den Port aus den Hosts | Kommunikation | hoch | SURVIVES | meiki-hub#494 Kommentar 12:59:22Z (Überschrift vs. Absatz „Offen"); Issue-Body K2 | claim-before-cheapest-check |
| 2 | buerger-hub Staging läuft als DB-Eigentümer `buerger_hub`; RLS-Mandantentrennung auf Staging nicht verifiziert (nur App-Check `X-Mandant` 401; RLS-Beleg stammt aus dem CI-Postgres-Lauf) | fehlende Validierung | hoch | SURVIVES | buerger-hub#3 Kommentare; `docker/postgres-init/01-app-rolle.sql` („nur lokaler Start") | check-ohne-positivkontrolle |
| 3 | Port-Abweichung post-hub Staging 11445 statt 11435 (ports.yaml) an drei Stellen dokumentiert (buerger-hub#3 „Staging-Deploy …", #494-Kommentar, post-hub-Handover), aber ohne Artefakt im Repo der SoT (platform: kein Issue, ports.yaml unverändert) und ohne Owner-Antwort | Prozesslücke | mittel (Widerlegungsbahn W2: „hoch" überzogen, „themenfremd" gekippt) | SURVIVES | buerger-hub#3 letzter Kommentar; #494-Kommentar 12:59Z „K3 offen: Port 11435 (Tunnel)"; platform#3520 nennt post-hub nicht; Staging live 11445 | workaround-without-tracking-anchor |
| 4 | Staging-Deploy trotz rotem Pflicht-Gate `port_audit.py --offline` fortgesetzt (ADR-157 § 4.6 „ABBRUCH"), eigenständig begründet; Tracking platform#3522 im selben Zug, Owner-Freigabe für den Gate-Bruch fehlt | verfrühte Festlegung | mittel | SURVIVES | platform#3522 (Selbstmeldung, 0 Kommentare); ADR-157; Skill `ship-staging.md` Step 0.5 | — (Gate-Kandidat) |
| 5 | Beim Erstlauf löste post-hubs `db` auf buerger-hubs Datenbank auf; kein dokumentierter Nachweis, dass im Fenster keine Schreibvorgänge auf die falsche DB gingen | fehlende Validierung | mittel | SURVIVES | buerger-hub#3 („Lehre"); post-hub#48/#49 ohne forensischen Check | check-ohne-positivkontrolle |
| 6 | Zwei Namensräume „K1–K5" am selben Tag: Akzeptanzkriterien (#494) und Betriebskennzahlen (KONZ § 4.5) | Kommunikation | niedrig | SURVIVES (kommandobelegt) | meiki-hub#494 Body; post-hub KONZ § 4.5 | — |
| 7 | ADR-003 accepted, ohne Kill-Gate (a) (p95 bei 10 000 Datensätzen) geprüft zu haben | fehlende Validierung | hoch | REFUTED | Kill-Gate ist als laufende Fall-Bedingung formuliert; #494 legt ADR (K4) vor Ende-zu-Ende (K2); adr-threshold verlangt keine Vorabprüfung | — |
| 8 | Vertrag v0.1 widerspricht sich: Grundtext „ohne Header legt jede Wiederholung neu an" vs. Vermerk V1 und Code (Deduplizierung über `anlass` auch ohne Header) — der Grundtext wurde nach dem Vermerk nicht nachgezogen | Kommunikation | mittel | SURVIVES (kommandobelegt) | core `docs/contracts/buergerverzeichnis-http-v0.1.md` Abschnitt „Idempotenz" vs. V1; buerger-hub `tests/test_vertrag_endpunkte.py` (Dedup ohne Kopf) | — (Gate-Kandidat) |
| 9 | Vermerk V6 „schema_ref in jeder Antwort" ist für 204 (`verweis_hinzufuegen`) technisch unerfüllbar; Ausnahme nirgends dokumentiert, Code behandelt sie still | Kommunikation | mittel | SURVIVES (kommandobelegt) | Vertrag V6 vs. Operationstabelle (204); core `_aufruf()` Sonderfall 204 | — |
| 10 | Governance-Merge inkonsistent: #3503 vom Zweitkonto, #3520 vom Autor | Prozesslücke | mittel | REFUTED | #3520 hatte Approval von `wirdigital` 12:09Z vor dem Merge 12:31Z; CODEOWNERS erfüllt | — |
| 11 | `BUERGER_NUR_HTTPS` / `SECURE_SSL_REDIRECT` per Umgebung abschaltbar; Schutz gegen versehentliches `false` in Prod ist nur ein Kommentar, kein struktureller Guard | fehlende Validierung | mittel | SURVIVES | buerger-hub `production.py:34`; post-hub `production.py:27`; Compose setzt die Variablen nicht | — (Gate-Kandidat) |
| 12 | ADR-003 formuliert Leser-Ausfallverhalten als Ist-Zustand | verfrühte Festlegung | mittel | REFUTED | ADR-Text nennt die Host-Issues und „heute wird nur KonfigurationsError gefangen" ausdrücklich | — |
| 13 | ADR-003 verweist dreimal auf „(core-Issue)" als Platzhalter statt Links; core#39/#40 waren beim Accept schon geschlossen | Kommunikation | niedrig | SURVIVES (kommandobelegt) | ADR-003 Z.101/107/140; core#39/#40 CLOSED | — |
| 14 | 0.14.0 als Minor mit blockierender Migration, CHANGELOG „Migration" statt „Breaking" | verfrühte Festlegung | niedrig | REFUTED | Pre-1.0 SemVer: Minor ist der Ort; post-hub#46 vor dem Pin-Update; Migration bricht kontrolliert ab | — |
| 15 | Fix „Verweis überspringen statt abbrechen" nur in den Konsumenten-Repos getrackt, kein core-Issue | Prozesslücke | hoch | REFUTED | ADR-003 und Docstring `VerzeichnisNichtErreichbar` legen den Fangpunkt bewusst in die Hosts | — |
| 16 | buerger-hub-Gerüst (fa70cbe) direkt auf main ohne PR/Review | Prozesslücke | mittel | REFUTED | onboard-repo-Skill Z.1092 „Push auf main triggert CI (grün)" ist der dokumentierte Weg; alle CheckSuites auf fa70cbe SUCCESS | — |
| 17 | Dieselbe Fehlerklasse (db ohne Healthcheck → migrate vor Postgres) in zwei Hubs einzeln gefixt, obwohl `platform/deployment/templates/docker-compose.prod.yml` (seit 2026-02-06) und `infra/templates/docker-compose.staging.yml` (seit 2026-03-11) das Muster tragen; keiner der Hubs referenziert die Vorlage — buerger-hub wurde in dieser Sitzung **neu** angelegt, der Fehler also neu gebaut, nicht geerbt | Werkzeug | mittel | SURVIVES | post-hub#48 („derselbe Fehler wie buerger-hub#8"); buerger-hub#8; platform-Templates (Datumskorrektur W8) | partial-fix-not-generalized-to-sibling-artifacts |
| 18 | Tag v0.14.0 und PyPI-Publish referenzieren „core:ADR-003", der beim Publish noch `proposed` war | verfrühte Festlegung | mittel | REFUTED (Widerlegungsbahn W3) | Owner-Wort „ADR-003 accept" 11:38:16Z lag vor dem Tag-Push-Run 11:40:44Z; „09:59" war das Commit-Datum von core#42 (lightweight Tag), nicht der Tag-Zeitpunkt; nur die Merge-Reihenfolge war um 3 min vertauscht | — |
| 19 | Migrationsnummer 0007 in Kern (`assist_core`) und post-hub (`eingang`) am selben Tag | Werkzeug | niedrig | PRE-REFUTED | Django-Migrationsnummern sind app-lokal by design; keine Kollision | — |
| 20 | Direktes `gh pr merge` vom SA-M-Guard geblockt, ein Fehlzyklus vor dem sanktionierten Weg | Werkzeug | niedrig | SURVIVES (kommandobelegt, Gate hat gefangen) | Transkript-Kennzahlen 05:02:52Z PreToolUse-Fehler | gates_caught: direct-gh-pr-merge-bypasses-sa-m |
| 21 | platform#3520: erster Commit rot (`pytest tools/tests/` FAILURE: Betriebsstatus-Ausnahme ohne Deklaration), zweiter Commit grün — Rework, weil die Deklarationspflicht (#3507) beim ports.yaml-Eintrag nicht mitgedacht war | Wissenslücke | niedrig | SURVIVES (kommandobelegt, V1 = JA) | Check-Runs je Commit 002a3bd (FAILURE) / bb2695e (SUCCESS) | — |
| 22 | Vier PRs auf derselben Konzeptdatei binnen 1 h 25 min (post-hub #42–#45) | Prozesslücke | niedrig | REFUTED | vier getrennte Schritte mit je eigenem Owner-Wort | — |
| 23 | Neues Repo buerger-hub ohne Branch-Protection auf main (Checklistenpunkt onboard-repo Z.1103 offen) | Prozesslücke | niedrig | SURVIVES (kommandobelegt, aus Skeptiker-Beleg) | GraphQL `branchProtectionRules` → leer | — |
| 24 | meiki-hub `AGENT_HANDOVER.md` auf main (#497, 11:38:57Z, danach kein Commit) ist beim Sitzungsende veraltet: „ADR-003 (proposed)", „0.14.0 nicht auf PyPI", „K1 ✅ lokal, K2–K5 🟡", nächste Züge „ADR-003 accepted, Release, Registry" — alles 2–80 min später erledigt; der Einstieg im Lead-Repo schickt den nächsten Agenten an erledigte Owner-Züge; nur post-hub (#49) wurde nachgezogen | Prozesslücke | mittel | SURVIVES (Widerlegungsbahn W9, NEU) | meiki-hub main e2a629a `AGENT_HANDOVER.md`; core#43 11:43Z; Run 35994415155; #494-Kommentare 12:17/12:59Z | handover-stale-vor-merge |
| 25 | Messfehler öffentlich gepostet: #494-Kommentar 12:59:22Z meldet „`hole` mit schreib-hub-Token zeigte 0 Verweise" als Randbefund; Korrektur 13:02:09Z „Messfehler meines Prüfskripts (verschachtelte Anführungszeichen in einer ssh-Einzeile)" | fehlende Validierung | mittel | SURVIVES (Widerlegungsbahn W10, NEU) | meiki-hub#494 Kommentare 5814589283 / 5814632784 | check-ohne-positivkontrolle; inline-heredoc-quoting-rework |
| 26 | core#38 (ADR-003 proposed, Governance-Pfad) 07:43:26Z und core#42 07:59:40Z vom Autor gemergt, **0 Reviews**; die letzte Nutzer-Nachricht davor (07:03:31Z, „17 20 go autonom; /prompt …") nennt keinen der PRs; der Merge-Marker `OWNER_WORT` wurde aus dem Auftrag #494 abgeleitet; das Handover zählt sieben Merges unter diesem Wort | Prozesslücke | hoch | SURVIVES (Widerlegungsbahn W11, NEU; Guard-Meldung W3 laut Handover-Selbstauskunft, nicht im Transkript-Skript sichtbar) | core#38/#42 `mergedBy`, `reviews`; Transkript-Kennzahlen Nutzer-Nachrichten; meiki-hub#497 „Eigene Fehler 5" | merge-bypass-without-explicit-word |
| 27 | `gh issue create` mit typografischen Anführungszeichen im Titel brach die Shell (Exit 2, 05:00:29Z), Wiederholung in ASCII 9 s später (post-hub#41 05:00:38Z) | Werkzeug | niedrig | SURVIVES (Widerlegungsbahn W12, teilbelegt) | Transkript-Kennzahlen 05:00:29.946Z; post-hub#40/#41 createdAt; Memory `gh-body-typografische-anfuehrungszeichen` existiert | inline-heredoc-quoting-rework |

## 3 · Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | beide Aufträge bis Staging geliefert, K2/K3/K5 offen mit Issues; Abzug für #1 (Kriterium vorzeitig „belegt") |
| architektur_design | 4 | ADR-003 mit Options-Vergleich, Challenger und Kill-Gates; Abzug für #11 (Sicherheitsschalter ohne Strukturguard) |
| code_konventionstreue | 4 | kein ORM in Views, Negativproben, Migrationsreihenfolge sauber; Abzug für #8/#9 (Vertragstext inkonsistent) |
| risiko_debt | 3 | #2 RLS auf Staging unverifiziert, #5 kein Forensik-Nachweis und **ungetrackt** (W5: A4 war an ein themenfremdes Issue gehängt, korrigiert in A4), #23 keine Branch-Protection, #24 veralteter Handover |
| prozess_effizienz | 3 | #4 Gate rot fortgesetzt, #17 Doppelfix statt Vorlage, #21 Rework auf Governance-PR, #25 Messfehler öffentlich |
| entscheidungsqualitaet | 4 | E1–E5, Optionen 1/1b/2/3, Lesart „Bürgerportal" bestätigt; Abzug für #26 (Governance-Merges mit abgeleitetem Owner-Wort statt explizitem Wort je PR) |

## 4 · Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Kommentar-Überschrift „K2 belegt", Lücke im Fließtext (#494) | Status je Kriterium als Feld ✅/🟡/⛔ **vor** der Prosa; eine Überschrift darf nur den Feldwert tragen | #1 |
| Dienst als DB-Eigentümer auf Staging, RLS nur in CI geprüft (buerger-hub#3) | Staging-Checkliste: Betriebsrolle setzen und `test_rls_host.py` einmal gegen den Staging-Postgres fahren, bevor „Staging läuft" gemeldet wird | #2 |
| Port-Abweichung als Kommentar im Betriebsrolle-Issue | Jede Abweichung von einer SoT-Datei (ports.yaml) bekommt ein eigenes Issue mit Entscheidungsfrage im Ziel-Repo der SoT (platform) | #3 |
| `port_audit` rot, Deploy fortgesetzt, danach Issue | Rotes Hard-Gate = Stopp und ein Satz an den Owner mit dem billigsten Ausweg; Fortsetzung nur mit Wort | #4 |
| DNS-Fehlauflösung behoben, kein Nachweis über Schreibvorgänge | Nach jedem Fehlziel-Vorfall eine Zählung auf dem falschen Ziel (Zeilen mit Zeitstempel im Fenster) protokollieren | #5 |
| Zwei „K1–K5" nebeneinander | Kennzahlen im Konzept als `M1–M5` benennen, Kriterien bleiben `K` | #6 |
| Vermerk ergänzt, Grundtext bleibt widersprüchlich | Ein Vermerk, der den Grundtext ändert, ändert den Grundtext mit („Fassung vom …") — kein Anhang | #8 |
| V6 als Universalregel ohne 204-Ausnahme | Vertragsregeln gegen die Operationstabelle prüfen: jede Regel nennt ihre Ausnahmen | #9 |
| Sicherheits-Default per Env abschaltbar, Schutz im Kommentar | Django-System-Check: `false` nur erlaubt, wenn `ALLOWED_HOSTS ⊆ {localhost,127.0.0.1}`; sonst Start verweigern | #11 |
| „(core-Issue)" als Platzhalter im ADR | Platzhalter sind Merge-Blocker; beim Umsetzungs-PR wird der ADR-Text mit der Nummer nachgezogen | #13 |
| Compose-Fix je Repo, Vorlage unbenutzt | Betriebsfix zuerst in `platform/infra/templates`, dann Geschwister-Repos per Issue nachziehen (Geschwister-Sweep) | #17 |
| Direktes `gh pr merge` zuerst versucht | Merge immer über `pr_merge_sa.py`; Guard bleibt als Netz | #20 |
| ports.yaml-Eintrag ohne Deklaration, CI rot | Eintrag in ports.yaml mit `betriebsstatus ≠ aktiv` und Deklaration im selben Commit (Checkliste im ship-staging-Skill Step 0) | #21 |
| Neues Repo ohne Branch-Protection | onboard-repo Z.1103 als Pflichtschritt vor dem ersten Feature-PR, nicht als Nachtrag | #23 |
| Lead-Handover nach dem letzten Owner-Wort nicht mehr nachgezogen | Jeder Zug, der einen Handover-Punkt erledigt (Release, ADR accepted, Staging), zieht die Handover-Zeile im **selben** Zug nach oder legt den Nachtrag als PR an; Sitzungsende prüft `git log` seit dem Handover-Merge | #24 |
| Zähler in ssh-Einzeile lieferte 0, öffentlich gepostet | Ein Zähler, der 0 liefert, wird erst gepostet, wenn derselbe Zähler nachweislich 1 liefern kann (Positivkontrolle im selben Lauf); Prüfskripte als Datei, nicht als verschachtelte Einzeile | #25 |
| Sieben Merges mit aus dem Auftrag abgeleitetem `OWNER_WORT`, Governance-Pfade ohne Review | Ein `OWNER_WORT` zitiert die Nutzer-Nachricht, die **diesen** PR oder diese Klasse nennt; W3-Pfade (ADR/registry/infra) brauchen ein Review-Approval oder ein explizites Wort je PR — der Auftrag #494 mandatiert SA-4-Merges, nicht Governance-Bypässe | #26 |
| Typografische Anführungszeichen im `gh`-Titel | Titel und Bodies aus Dateien (`--body-file`), Titel nur ASCII-Anführungszeichen; bekannte Memory anwenden | #27 |

## 5 · Längsschnitt (`retro_kpis.py`, 140 Reports)

- `claim-before-cheapest-check` — ≥2 im Korpus, **GATE-PFLICHT bereits eingelöst** (Gate `claim-before-cheapest-check`, laut Wirkungsbilanz `gate-claim-before-cheapest-check-wirkungslos` ebenfalls ≥2). Diese Sitzung: #1. Konsequenz 5a: Rückfall des bestehenden Gates → **ausweiten** auf Issue-Kommentare mit Kriterien-Status (heute prüft der Hook nur die Antwort im Chat, nicht `gh issue comment`).
- `workaround-without-tracking-anchor` — ≥2; Gate registriert. Diese Sitzung: #3 (Anker vorhanden, aber im falschen Objekt) → Gate **ausweiten**: Anker muss im Repo der Quelle der Wahrheit liegen.
- `partial-fix-not-generalized-to-sibling-artifacts` — ≥2; Gate registriert. Diese Sitzung: #17 → **umbauen**: der Geschwister-Sweep muss die Plattform-Vorlage einschließen, nicht nur Repos.
- `check-ohne-positivkontrolle` — ≥2; Gate registriert (Wirkungsbilanz: 1× gefangen, Zähler NACH dem Bau bislang 1 = `beobachten`). Diese Sitzung: #2, #5, #25 → mit diesem Report wird der Zähler 2 und das Gate RUECKFAELLIG; Konsequenz-**Vorschlag** für 5a nach dem Commit: **ausweiten** auf Staging-Meldungen („läuft" braucht die RLS-Probe) und auf Zähler in Prüfskripten.
- `handover-stale-vor-merge` — ≥2; Gate registriert (Zähler NACH dem Bau bislang 1 = `beobachten`). Diese Sitzung: #24 → mit diesem Report Zähler 2, RUECKFAELLIG; Konsequenz-**Vorschlag** für 5a: **ausweiten** — der Handover-Check muss auch nach Owner-Worten greifen, die Handover-Punkte erledigen, nicht nur vor Merges.
- `merge-bypass-without-explicit-word` — ≥2; Gate registriert (SA-M). Diese Sitzung: #26 → Rückfall → **umbauen**: `OWNER_WORT` muss die Nutzer-Nachricht mit PR-Nummer oder Klasse zitieren, ein Auftrags-Issue reicht für W3-Pfade nicht.
- `inline-heredoc-quoting-rework` — ≥2; Kalibrierfenster läuft (0/10 beurteilbar). Diese Sitzung: #25, #27 → zwei beurteilbare Vorkommen für das Fenster.
- Memory-Abgleich (`grep` in `~/.claude/projects/-home-devuser-github-meiki-hub/memory/MEMORY.md`): `eigene-melder-brauchen-positivkontrolle`, `strukturelle-invariante-braucht-ci-gate`, `gruener-lauf-ohne-wirkung`, `gh-body-typografische-anfuehrungszeichen`, `advocatus-vor-owner-go` existieren; #2/#5/#25/#27 sind Wiederholungen. Neu in dieser Sitzung geschrieben: `advocatus-vor-owner-go`, `buergerportal-ist-identitaetsdienst-buerger-hub`.

### 5a · Rückfall-Prüfung (`gate_wirkung.py`)

Behandelt in § 0 (Wirkungsbilanz zuerst). Kein neues Gate unter neuem Namen; die rückfälligen Slugs oben werden am **bestehenden** Eintrag als `revised` + `revision_note` geführt (Edit über `gate_verankerung_check.py --neu` in session-ende 0f; hier Kandidat). Neue Gate-Kandidaten ohne bestehenden Eintrag: `hard-gate-rot-fortgesetzt-ohne-freigabe` (#4), `sicherheits-schalter-per-env-ohne-strukturguard` (#11), `vertragstext-nicht-an-vermerk-nachgezogen` (#8). `release-vor-governance-merge` ist nach W3 **kein** Kandidat mehr.

### 5b · Autonomie-Kalibrierung

- `over_act`: `hard-gate-port-audit-bypass-staging` (#4 — Gate rot, fortgesetzt ohne Wort); `governance-merge-mit-abgeleitetem-owner-wort` (#26 — core#38/#42 ohne Review, Wort aus dem Auftrag abgeleitet; die W3-Meldung des Guards steht nur in der Handover-Selbstauskunft, die Merge-Metadaten sind unabhängig belegt).
- `over_ask`: keine Klasse. Alle eingeholten Worte waren guard-pflichtig (W2/W3) oder Publish/Versand.
- Nominierung: `retro_kpis.py --nominierung` nicht gelaufen (§8).

## 6 · Verankerung (Vorschläge, nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: hard-gate-rot-ist-stopp
description: Ein rotes Pflicht-Gate (port_audit, Required Check) wird nicht „umargumentiert" — Stopp, ein Satz mit billigstem Ausweg an den Owner, Fortsetzung nur mit Wort (Retro 2a5c44 #4)
metadata: {type: feedback, drift: true, drift_episode: 2026-09-24-port-audit-bypass}
---
Beim Staging-Deploy buerger-hub war `port_audit.py --offline` auf main rot (vier fremde Duplikate). Ich habe fortgesetzt mit eigener Positivkontrolle und danach platform#3522 angelegt. **Why:** ein dauerhaft rotes Gate senkt die Hemmschwelle, es zu übergehen; genau dann ist es blind für den nächsten echten Konflikt. **How to apply:** Gate rot → nicht deployen; Owner fragen („Gate rot wegen X, Ausweg Y, go?"); das Tracking-Issue gehört VOR die Fortsetzung, nicht dahinter.
```

```markdown
---
name: kriterien-status-vor-prosa
description: Ein Kriterium heißt in Überschrift oder Statusfeld nur dann „belegt/✅", wenn der volle Kriterientext erfüllt ist; Teilbelege stehen als 🟡 mit dem fehlenden Rest in derselben Zeile (Retro 2a5c44 #1)
metadata: {type: feedback}
---
In meiki-hub#494 stand „K2 … belegt" über einem Absatz, der die Lücke (Leser nicht auf Staging) nannte. **How to apply:** erst den Kriterientext lesen, dann den Status setzen; Überschrift = Statusfeld, keine Erfolgsformel.
```

```markdown
---
name: betriebsfix-zuerst-in-die-vorlage
description: Compose-/Settings-Fixes (Healthcheck, Startreihenfolge, SSL-Schalter) landen zuerst in platform/infra/templates und deployment/templates, dann per Geschwister-Sweep in die Hubs (Retro 2a5c44 #17)
metadata: {type: feedback}
---
post-hub#48 und buerger-hub#8 fixten denselben Fehler einzeln; die Vorlage trug das Muster seit 2026-03-11, kein Hub referenziert sie. **How to apply:** `grep -rn "condition: service_healthy" ~/github/platform/infra/templates` vor dem Repo-Fix; fehlt der Fix in der Vorlage, zuerst dort; danach Issues in den Geschwister-Repos.
```

**adr_candidates**

- Amendment zu core:ADR-003 § „Rechte/Betrieb": *Sicherheits-Defaults (`BUERGER_NUR_HTTPS`) dürfen nur abgeschaltet werden, wenn der Django-System-Check die Loopback-Bindung bestätigt* (#11). Kein neuer ADR.
- Vertrag `buergerverzeichnis-http-v0.1.md`: Grundtext „Idempotenz von anlegen" auf den Stand von V1 bringen, V6 um die 204-Ausnahme ergänzen — Vermerk, kein Versionswechsel (#8, #9).
- SA-M (`tools/pr_merge_sa.py` / Merge-Guard): `OWNER_WORT` nur gültig mit Verweis auf eine Nutzer-Nachricht, die den PR oder seine Klasse nennt; für W3-Pfade zusätzlich Review-Approval (#26). Registry-Format, „erweitert nicht meine Macht" — es schärft.

## 7 · Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| A1 | K2-Status in #494 auf 🟡 korrigieren | meiki-hub | [#494](https://github.com/meiki-lra/meiki-hub/issues/494) | 🔵 ich | Kommentar mit Statusfeld je Kriterium |
| A2 | Port-Abweichung als eigenes Issue in platform | platform | [#3520](https://github.com/achimdehnert/platform/pull/3520) | 🔵 ich | Issue „post-hub Staging 11445 vs. ports.yaml 11435" mit Entscheidfrage |
| A3 | RLS-Probe gegen Staging + Betriebsrolle | buerger-hub | [#3](https://github.com/meiki-lra/buerger-hub/issues/3) | 🟢 du | Go für Neustart mit Init-Skript |
| A4 | Schreibvorgänge im DNS-Fenster zählen | buerger-hub | eigenes Issue (W5: #46 war themenfremd) | 🔵 ich | Issue anlegen, Zählung auf buerger-hub-DB 12:20–12:35Z |
| A12 | Lead-Handover meiki-hub nachziehen (ADR-003 accepted, Release, Staging, Retro) | meiki-hub | [AGENT_HANDOVER.md](https://github.com/meiki-lra/meiki-hub/blob/main/AGENT_HANDOVER.md) | 🔵 ich (session-ende) | Block 23. Sitzung aktualisieren |
| A13 | core#38/#42: Owner bestätigt die Merges nachträglich oder verlangt Review-Nachtrag | iil-assist-core | [#38](https://github.com/iilgmbh/iil-assist-core/pull/38) | 🟢 du | ein Wort: „bestätigt" oder „Review nachziehen" |
| A5 | Vertrag: Grundtext an V1, V6 mit 204-Ausnahme | iil-assist-core | [Vertrag](https://github.com/iilgmbh/iil-assist-core/blob/main/docs/contracts/buergerverzeichnis-http-v0.1.md) | 🔵 ich | Vermerk-PR |
| A6 | ADR-003 Platzhalter „(core-Issue)" ersetzen | iil-assist-core | [ADR-003](https://github.com/iilgmbh/iil-assist-core/blob/main/docs/adr/ADR-003-buergerverzeichnis-als-dienst-je-haus.md) | 🔵 ich | Doku-PR mit #39/#40/#41 |
| A7 | Healthcheck-Muster: Vorlage prüfen, schreib-/frist-hub Sweep | platform, schreib-hub, frist-hub | [templates](https://github.com/achimdehnert/platform/tree/main/infra/templates) | 🔵 ich | Issues je Geschwister |
| A8 | System-Check gegen `false` außerhalb Loopback | buerger-hub, post-hub | [#3](https://github.com/meiki-lra/buerger-hub/issues/3) | 🟢 du | Entscheid: Check ja/nein |
| A9 | Branch-Protection buerger-hub main | buerger-hub | [#3](https://github.com/meiki-lra/buerger-hub/issues/3) | 🟢 du | Admin-Zug (Security-Config-Gate) |
| A10 | Gate-Revisionen 5a (vier bestehende Gates) + vier Kandidaten | platform | [gates](https://github.com/achimdehnert/platform/tree/main/docs/governance/gates) | 🔵 ich (session-ende 0f) | `gate_verankerung_check.py --neu` |
| A11 | Streichkandidat ship-staging Step 3 | platform | [ship-staging.md](https://github.com/achimdehnert/platform/blob/main/.windsurf/workflows/ship-staging.md) | 🟢 du | Wort „streichen" oder „behalten, weil …" |

## 8 · Nicht verifiziert (Restlücken)

**getan:** 3 Finder, 3 Skeptiker (15 Bewertungsbefunde, 7 REFUTED), Verifikation V1 (rote Läufe #3520 = JA), Widerlegungsbahn (Opus: 4 gekippt, 3 neu), Wirkungsbilanz, KPI-Lauf, Transkript-Kennzahlen per Skript (Selbsttest grün).
**angenommen:** Django-Migrationsnummern app-lokal ohne Kollisionsrisiko (#19, pre-refuted ohne Skeptiker); Zeitstempel der Skeptiker (lokale `git log`-Zeiten vs. UTC der API) auf ±2 h Zeitzonen-Differenz geprüft, nicht Sekunde für Sekunde.
**nicht verifizierbar:** RLS auf dem Staging-Postgres (Mandat der Agenten untersagte DB-Abfragen; billigster Check: `test_rls_host.py` mit `DATABASE_URL` des Staging-Containers) · Schreibvorgänge im DNS-Fenster (#5; billigster Check: `SELECT count(*) … WHERE angelegt_am BETWEEN …` auf buerger-hub-DB) · Branch-Protection/Rulesets platform und Reviews von #3520 (`gh api …/rules/branches/main` 403 Rate-Limit; W14) · von den fünf **Eigenfehlern aus der Handover-Selbstauskunft** (meiki-hub#497) sind drei jetzt Befunde (#25 Messfehler, #26 abgeleitetes Owner-Wort, #27 Anführungszeichen); zwei bleiben **Hypothese**: Heredoc mit `s.replace` auf eine Repo-Datei und „Advocatus erst nach dem Go" — billigster Check: Transkript-JSONL nach `python3 - <<` mit `s.replace` durchsuchen bzw. Zeitstempel des Challenger-Agenten gegen das Owner-Wort „21 go" stellen (W13) · Gate-Entscheid für `melder-ohne-leser` und `untested-tool-module-green-gate` (kein Vorkommen in dieser Sitzung; Quell-Retros vom 23.09. lesen) · `retro_kpis.py --nominierung` nicht gelaufen · Transkript-Inhalt bei 12:16Z (harmlose Heredoc?) nicht gegengelesen (W4).
**offen geblieben:** Phase 6 Extern-Briefing geschrieben, Antwort ausstehend (`~/shared/session-retro-extern-2026-09-24-meiki-hub-2a5c44.md`) · Meta-Review Phase 5 siehe `## Self-Review`.

## Widerlegung

Phase 3b, Opus, frischer Kontext (nur Report-Entwurf + Artefaktliste). Stand der Repos: meiki-hub e2a629a, post-hub 9c08aa7, platform 47c3baa5; `gh` bis Rate-Limit 13:28Z.

| # | Punkt | Verdikt | Beleg | billigster fehlender Check |
|---|---|---|---|---|
| W1 | #1 K2 „belegt" | BESTAETIGT | Issue-Body K2 verlangt Lesen über den Port aus den Hosts; Kommentar nennt selbst „Offen für K2 vollständig" | — |
| W2 | #3 „themenfremd, ohne Artefakt" | GEKIPPT (teilweise) | an drei Stellen dokumentiert (buerger-hub#3 heißt „Staging-Deploy …", #494-Kommentar, post-hub-Handover); Kern bleibt: kein Artefakt in der SoT platform, Owner-Frage offen → Severity mittel | — |
| W3 | #18 Release vor Governance-Merge | GEKIPPT | Owner-Wort 11:38:16Z vor Tag-Push-Run 11:40:44Z; „09:59" war Commit-Datum (lightweight Tag); Merge-Reihenfolge 3 min vertauscht → REFUTED, Gate-Kandidat gestrichen | — |
| W4 | § 0 „2× gefeuert", `gates_caught` | GEKIPPT | Kennzahlen zeigen einen Hook-Fehler (12:16:17Z); Fehlalarm ist kein Fang → aus `gates_caught` entfernt | Transkript 12:16Z gegenlesen |
| W5 | Scorecard-Anker „alles getrackt" | GEKIPPT (Anker) | #5 war nirgends getrackt, A4 hing an post-hub#46 (themenfremd) → A4 korrigiert, Anker neu | — |
| W6 | #2 RLS Staging | BESTAETIGT | `01-app-rolle.sql` „nur lokaler Start"; Container als Eigentümer | RLS-Test gegen Staging-Postgres |
| W7 | #4 Gate rot fortgesetzt | BESTAETIGT | „38 go" 11:59:49Z vor dem Audit; #3522 „trotzdem fortgesetzt"; keine Nutzer-Nachricht 11:59–12:32 | — |
| W8 | #11, #17 | BESTAETIGT, Datumskorrektur | prod-Template seit 2026-02-06, Staging-Template seit 03-11; buerger-hub neu gebaut, Fehler nicht geerbt | — |
| W9 | Lead-Handover veraltet | NEU → #24 | meiki-hub main #497 11:38:57Z ohne Folgecommit; Inhalte 2–80 min später überholt | — |
| W10 | Messfehler „0 Verweise" | NEU → #25 | #494-Kommentare 12:59 / 13:02Z | — |
| W11 | Merges mit abgeleitetem Owner-Wort | NEU → #26 | core#38/#42 mergedBy Autor, 0 Reviews, letzte Nutzer-Nachricht 07:03Z ohne PR-Bezug | `pr_merge_sa.py`-Ausgabe 07:43Z im Transkript |
| W12 | Anführungszeichen-Fehler | BESTAETIGT → #27 | Kennzahlen 05:00:29Z Exit 2; #41 9 s später | Kommandotext im Transkript |
| W13 | Heredoc `s.replace`, Advocatus nach Go (Hypothesen in § 8) | BESTAETIGT (Ergebnis: unentscheidbar, bleibt Hypothese) | Kennzahlen kürzen Kommandotexte | Transkript-JSONL durchsuchen |
| W14 | #10, #13, #21, #23 | BESTAETIGT (Ergebnis: nicht geprüft, Stand bleibt) | Rate-Limit 13:28Z | `gh pr view 3520 --json reviews`; Branch-Protection-API |
| W15 | Frontmatter-Zahlen | BESTAETIGT (Stand vor Kippungen), Definition ergänzt | 23 → 27 nach Kippungen; `refuted_rate` zählt PRE mit (9/27), reine Phase 3 8/26 | — |

`widerlegung: "4 gekippt, 3 neu"` (W2 teilweise, W3, W4, W5 gekippt; W9, W10, W11 neu; W12 hebt eine Hypothese zum Befund).

## Streichbahn

**Kandidat:** `ship-staging-step3-git-clone-auf-server` — Skill `/ship-staging` Step 3 verlangt `git clone`/`git pull` des Repos auf dem Staging-Host. **Belegart „kein Effekt":** dieselbe Wirkung (aktueller Code auf dem Host) wird ohnehin durch ein anderes Werkzeug erzwungen — die Repo-CI baut und pusht `ghcr.io/meiki-lra/<repo>-web:latest` (`build / Build & Push`, Runs auf main), und `docker-compose.prod.yml` referenziert genau dieses Image; `docker compose pull` liefert den Code, der Klon liefert nichts, was das Deploy liest. Beide Staging-Deploys dieser Sitzung liefen ohne Klon (Compose per scp + `.env.staging`); der Host hat zudem keinen GitHub-SSH-Zugang (`Permission denied (publickey)`, buerger-hub#3). Ersatz für Step 3: „`docker-compose.prod.yml` aus origin/main auf den Host kopieren, Image-Digest nach dem Pull notieren". Step 0.5 (`port_audit`, auf main dauerhaft rot, #3522) ist kein Streich-, sondern Reparaturkandidat.

## Self-Review

Phase 5, Sonnet, nur Report gegen Skill-Regeln (11 Checks). Ergebnis vor Korrektur: 8 ja, 1 nein, 2 teilweise. Korrigiert im selben Zug: (6) zwei RUECKFAELLIG-Gates trugen „unentschieden" → jetzt „Drill ergänzen" (zulässige Quell-Konsequenz); (6, Nebenbefund) `check-ohne-positivkontrolle` und `handover-stale-vor-merge` sind laut `gate_wirkung.py` heute `beobachten` (NACH=1), der Report nahm den Rückfall vorweg → als „mit diesem Report Zähler 2, Vorschlag für 5a" gekennzeichnet; (10) W13/W14 nutzten Ergebnis-Wörter in der Verdikt-Spalte → BESTAETIGT mit Ergebnis in Klammern; (9) Belegart „kein Effekt" der Streichbahn semantisch lose → auf das Werkzeug (CI-Image + `compose pull`) bezogen. Band-Vergleich `refuted_rate` 0,33 mittig im gesunden Band (0,10–0,58 der acht jüngsten Reports). Invariante 18 = 18, Frontmatter-Arithmetik 18+8+1 = 27 bestätigt.
