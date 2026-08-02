---
retro_schema: 1
date: 2026-08-02
repo_scope: [platform, dev-hub, research-hub, nl2cad, iil-enrichment]
session_id: 932035
footprint: full
footprint_reduction_reason: "deep-Trigger (5 Repos) erfüllt, aber alle drei Downscale-Bedingungen belegt: (a) jeder Merge + Token explizit owner-freigegeben (Chat + Commit-Texte 0339a60d/8fffa260), (b) voll reversibel, keine Migration, kein Prod-Deploy ([skip ci] belegt), (c) Dichte-Schätzung ≤10"
findings_total: 11
findings_survived: 6
refuted_rate: 0.45
phase3_refuted: 4
pre_refuted: 1
scores:
  zielerreichung: 5
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
over_ask: 0
over_act: 0
gate_candidates: [ci-gate-maskiert-failure, lint-failure-no-local-gate]
recurring_findings: [ci-gate-maskiert-failure, lint-failure-no-local-gate, claim-before-cheapest-check]
---

# Session-Retro 2026-08-02 — platform (Session 932035, „Megatest Prio 1")

Methode: full (1 Haiku-Collector, 3 Sonnet-Finder, 1 gebündelter Sonnet-Skeptiker auf die
4 Bewertungsbefunde, Sonnet-Meta-Review). Kommandobelegte Befunde ohne Skeptiker übernommen.

## 1. Executive Summary

- **Prio 1 vollständig erfüllt und belegt:** Megatest von `15 failed` auf `119 passed, 0 failed`
  (Run 30758611903); alle Unterpunkte a–d adressiert; 7 PRs gemergt, 2 Tracking-Issues.
- **Härtester Fund (Rezidiv, gate-pflichtige Klasse `ci-gate-maskiert-failure` ×7):** der
  Megatest-Step kann bei rotem pytest nie `failure` melden — `| tee` schluckt den Exit-Code,
  `exit_code` wird erfasst, aber nie ge-exitet. Der Failure-Issue-Melder ist tot; #1010 fixte
  nur das Symptom (python→python3). Lauf 30758541548 (3 failed) endete `success`, Issue-Step
  `skipped`. #1681 fasste die Datei 5× an, ohne es zu sehen.
- **Alle 4 Bewertungs-Selbstanklagen der Finder wurden vom Skeptiker widerlegt** (Budget-
  Anhebung, reset-hard-Risiko, #1679-Scope, PAT-Wechsel) — die Session-Entscheidungen
  hielten unabhängiger Prüfung stand; die Fehlerrichtung war erneut „zu streng", nicht „zu milde".
- **Sicherheits-Restfenster Enterprise-PAT:** Token steht während fetch/clone im Klartext in
  der Prozessliste (`/proc/<pid>/cmdline`) — der URL-Scrub deckt nur die Persistenz auf Platte.
- **klickdummy-Skip ist breiter als seine Begründung:** er unterdrückt auch V-SEC-Regeln —
  ein echtes Secret in `klickdummy/` wäre künftig unsichtbar (Risiko, kein Vorfall).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Megatest-Step meldet roten pytest nie als failure (tee schluckt Exit; `exit_code` erfasst, nie exitet) → Failure-Issue-Melder tot; #1010 nur Symptomfix; Folgefehler: Session behauptete gegenüber Owner „täglicher Lauf legt Regression-Issue an" ungeprüft | fehlende Validierung | hoch | SURVIVES | Run 30758541548: `3 failed` + conclusion `success` + Issue-Step `skipped`; megatest.yml Z.84 | ci-gate-maskiert-failure ×7 (gate-pflichtig); claim-before-cheapest-check ×36 |
| 2 | Enterprise-PAT im Klartext in Prozessliste während fetch/clone; URL-Scrub deckt nur Platten-Persistenz | verfrühte Festlegung | mittel | SURVIVES | Repro `ps aux`/cmdline (lokal; Runner nicht geprüft → §8); Owner-Freigabe + „Tausch optional" in #1682 | — |
| 3 | `klickdummy`-Skip in `_SKIP_DIRS` unterdrückt ALLE Regeln inkl. V-SEC-01/02/03 — Begründung deckt nur URL/Config | fehlende Validierung | mittel | SURVIVES | `_should_skip_path`-Aufruf vor jeder Regel (scan_repo); Kommentar nennt nur „harte hrefs" | — |
| 4 | nl2cad#61: roter Lint-Zyklus 14:44→17:16 durch zu lange Marker-Zeile; lokal in Sekunden prüfbar (3 Schwester-PRs erster Push grün) | Prozesslücke | mittel | SURVIVES | Runs 30752764196/-199 rot; Fix-Commit 034f7186 | lint-failure-no-local-gate ×6 (gate-pflichtig) |
| 5 | Zähl-Inkonsistenz: budgets.toml-Header „11", PR-Body „13", real 12 Neuaufnahmen + 1 Rename | fehlende Validierung | niedrig | SURVIVES | toml-Header Z.6 vs. `gh pr diff 1681` | — |
| 6 | V-CFG-02 erkennt f-String-Keys (`.get(f"…")`) nicht; Fall ungetestet | Wissenslücke | niedrig | SURVIVES | Regex-Repro gegen `scripts/check_hardcoded_urls.py`; kein Testfall in tools/tests | — |
| 7 | „Sechs Bestands-Budget-0-Repos unilateral angehoben, Zusage gebrochen" | verfrühte Festlegung | mittel | REFUTED | Zusage galt laut Handover 1(b) exakt den 5 genannten Repos — die blieben 0; Anhebungen offen im Diff + #1682 tabelliert; Funde real (hard-URLs nachgelesen) | — |
| 8 | „reset --hard gefährdet echte Arbeitskopien auf dem Runner (hoch)" | fehlende Validierung | hoch | REFUTED | Klone tragen CI-Signatur (x-access-token-URL), nur Workflow-erzeugt; kein Beleg menschlicher Arbeit in $HOME/github | — |
| 9 | „#1679 ist Scope-Creep" | Scope | niedrig | REFUTED | Fehler manifestierte sich live beim Session-Start; Owner mergte selbst; Nachfix zu #1674 | — |
| 10 | „PAT-Typ-Wechsel = verfrühte Festlegung des Agenten" | verfrühte Festlegung | niedrig | REFUTED | Beide Commits dokumentieren separate Owner-Entscheidungen (0339a60d „Owner-Freigabe", 8fffa260 „Owner-Entscheidung … Fremd-Org") | — |
| 11 | Merge-Reihenfolge (main-Lauf vor dev-hub#199) erzeugte Zwischen-Rot | Prozesslücke | niedrig | pre-refuted (Finder selbst: folgenlos — wegen #1 entstand nicht einmal Issue-Lärm) | Run 30758541548 vs. Merge 17:19 | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 5 | #Positiv F1-1: 0 failed belegt, a–d komplett; kein Survivor berührt das Ziel |
| architektur_design | 4 | #2, #3: zwei Design-Restfenster in sonst tragfähigem Checkout-/Regel-Umbau |
| code_konventionstreue | 4 | #4: ein CI-roter Format-Verstoß; sonst Marker nach Bestandskonvention (Skeptiker-belegt) |
| risiko_debt | 3 | #1 (tote Fehlermeldung blieb ungesehen), #2, #3 — Debt erkannt, aber erst durch dieses Retro getrackt |
| prozess_effizienz | 4 | #4 (2,5 h Rot-Zyklus) gegen sonst saubere PR-/Merge-Hygiene (Finder-3 #5/#6 positiv) |
| entscheidungsqualitaet | 4 | 4/4 Bewertungs-Anklagen REFUTED (#7–#10); Abzug für #1-Nebensatz (ungeprüfte Behauptung an Owner) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, Beleg) | Soll | eliminiert |
|---|---|---|
| Workflow-Datei 5× editiert, umgebende Step-Logik (tee/exit) ungelesen übernommen (Run 30758541548 grün trotz 3 failed) | Beim Anfassen eines CI-Steps dessen **Fehlerpfad einmal scharf beweisen**: absichtlich roten Testfall einspeisen und `outcome=failure` im Log belegen, bevor „Melder funktioniert" behauptet wird | #1 |
| Enterprise-PAT in Klon-URL eingebettet, Scrub nur auf `.git/config` | Token via `GIT_ASKPASS`/Credential-Helper oder `http.extraheader` je Aufruf injizieren — nie als URL-Bestandteil (dann kein ps/cmdline-Fenster) | #2 |
| `klickdummy` pauschal in `_SKIP_DIRS` | Skip **regelklassen-scharf** schneiden: V-TMPL/V-CFG skippen, V-SEC-Regeln in klickdummy/ weiter scannen (Ausnahme so fein wie die Begründung) | #3 |
| Marker-Kommentar gepusht ohne lokalen `ruff format --check` (nl2cad rot, Schwester-PRs grün) | Vor jedem Push in Repos ohne lokales Push-Gate: `ruff format --check <geänderte Dateien>` als fester Handgriff — oder das platform-Push-Gate in die App-Repos verteilen | #4 |
| toml-Header vor Endstand geschrieben, PR-Body separat formuliert, nie gegengezählt | Zahlen, die zweimal auftauchen, **einmal zählen, einmal referenzieren** — Diff-Zählung (`grep -c '^+'`) in den Text übernehmen statt erinnern | #5 |
| Regex-Präzisierung getestet für 3 Fallklassen, f-String nicht | Bei Regex-Änderungen die Fallmatrix aus der **Beschreibung** ableiten (jede Aufrufform je einmal) statt aus den gerade sichtbaren Treffern | #6 |

## 5. Längsschnitt (retro_kpis.py, gelaufen 2026-08-02)

- `ci-gate-maskiert-failure` (×7) und `lint-failure-no-local-gate` (×6) stehen **bereits auf der
  Gate-PR-Pflicht-Liste** — Befunde #1 und #4 sind neue Instanzen, kein neues Memo
  schreiben, sondern Gate bauen (Maßnahmen 1 und 4).
- `claim-before-cheapest-check` (×36, gate-pflichtig laut CLAUDE.md): Nebensatz von #1 — die
  Behauptung „täglicher Lauf legt Issues an" wäre mit einem `gh run view`-Blick auf den
  Issue-Step widerlegbar gewesen.
- refuted_rate 0.45: innerhalb des historischen Bands (Max 0.56), aber im oberen Bereich
  (Vorgänger-Mittel ≈0.27) — Lesart: Finder produzierten überdurchschnittlich viel
  widerlegbare Selbstanklage. Echte Falsifikations-Quote phase3 = 4/(11−1) = 0.40.
- 5b Autonomie: `over_ask=0, over_act=0` — alle Gates (Merges auf geschützte mains,
  Security-Config Token) wurden dem Owner vorgelegt, alles Reversible lief autonom.

## 6. Verankerung (Kandidaten — Entscheidung beim Menschen)

**memory_candidate 1 (CLAUDE.md-Zeile oder Memory, Klasse existiert als
`feedback_run_conclusion_not_tool_health` — dies wäre die Schärfung):**
> `cmd | tee out.txt` in einem CI-Step verschluckt den Exit-Code (Pipeline-Exit = tee), auch
> unter `bash -e`; ein danach erfasstes `PIPESTATUS[0]` ist wirkungslos, solange es nicht
> ge-`exit`et wird. Ein Step mit tee-Pipe ist erst dann ein Melder, wenn sein Fehlerpfad
> einmal scharf bewiesen wurde (absichtlich rot → outcome=failure im Log gesehen).

**adr_candidates:** keine — kein Architektur-Entscheid offen.

## 7. Maßnahmen (Action-Board, aus dem Soll-Ablauf)

### 🔵 Offen — ich kann sofort
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Issue Exit-Maskierung + Fix-Skizze | platform | folgt (dieser Turn) | 🔵 | Issue anlegen (ich) |
| M2 | Scanner-Punkte an #1682 anhängen | platform | #1682 | 🔵 | Kommentar (ich) |

### 🟢 Offen — dein Zug
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M3 | Gate-PR Exit-Fix freigeben | platform | M1-Issue | 🟢 | entscheiden (du) |
| M4 | memory_candidate 1 annehmen/ablehnen | — | §6 | 🟢 | entscheiden (du) |

M2 bündelt: klickdummy-Skip regelklassen-scharf (#3), Token via Credential-Helper statt URL (#2), f-String-Testfall (#6), Header-Zahl 11→12+1 korrigieren (#5). M4 deckt Soll-Zeile 1; die Gates zu #1/#4 existieren als Pflicht-Slugs bereits auf der KPI-Liste.

## 8. Nicht verifiziert (Restlücken)

- **ps-Token-Fenster auf dem echten Runner** (#2): Repro lief lokal; billigster Check:
  während eines Megatest-Laufs `ssh <runner-host> "cat /proc/\$(pgrep -f x-access-token)/cmdline"`.
- **Runner-$HOME wirklich nur CI-Scratch** (#8-Refutation stützt sich auf Indizien):
  billigster Check: `ls -la /root/github` + `git -C /root/github/<repo> log -3` auf dem Runner-Host.
- **Detail-Diffs der 4 App-Repo-PRs** wurden vom Soll-Ist-Finder nur klassifiziert, nicht
  gelesen; Entscheidungs-Finder hat sie separat geprüft — Restlücke: research-hub#53 nur von
  einem Finder gesichtet. Billigster Check: `gh pr diff 53 --repo achimdehnert/research-hub`.
- **Regel-1-Restlücke** (Konfliktsortierung + Synthese im Haupt-Kontext): skill-konform;
  billigster Check entfällt — strukturell, per Skill-Design akzeptiert.

**Vierer:** getan: Collect/Find/Falsifikation/Längsschnitt wie oben · angenommen: Chat-
Freigaben des Owners sind authentisch (nicht artefakt-prüfbar) · nicht verifizierbar: die
drei §8-Punkte · offen geblieben: M1–M4.

## Self-Review (Phase 5, Meta-Agent)

Meta-Review 9/10 PASS; korrigiert wurden: Recurrence-Zähler von Schwelle auf Ist-Wert
(×7/×6/×36 aus retro_kpis.py), Band-Einordnung der refuted_rate präzisiert (oberer
Bereich, kein Ausreißer), billigste Checks für §8 ergänzt.
