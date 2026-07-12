---
retro_schema: 1
date: 2026-07-11
repo_scope: [platform, mcp-hub, iil-adrfw, "~/.claude", platform-pinned]
session_id: d2522c-incr
footprint: full
footprint_reduction_reason: "Rule-B (≥3 Repos) sagt deep; Reduktion auf full per Increment-Regel 4: (a) kein Prod-Schritt im Increment (M1=Security-Config, explizit Owner-approved 'M1 approved'; #171 ungemergt=kein Auto-Deploy), (b) alle Änderungen reversibel, (c) Dichte-Schätzung ≤8 vor Lauf"
findings_total: 15
findings_survived: 9
refuted_rate: 0.40
phase3_refuted: 5
pre_refuted: 1
over_ask: 0
over_act: 0
scores:
  zielerreichung: 3
  architektur_design: 2
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 2
gate_candidates: [mcp-hub-review-deadlock-fix, push-hook-cd-parsing-fix, scanner-merge-carrier-gap, always-instruction-without-enforcement]
recurring_findings: [claim-before-cheapest-check, platform-pinned-perma-dirty-loop, always-instruction-without-enforcement]
---

# Session-Retro 2026-07-11 — Increment: Abarbeitung der d2522c-Maßnahmen M1–M8 / O1–O3

## 1. Executive Summary

- Alle 11 beauftragten Maßnahmen wurden geliefert — aber **zwei der drei neu gebauten Gates sind defekt**: Die mcp-hub-Review-Rule (M1) erzeugt einen **strukturellen Merge-Deadlock** (#2: einziger Collaborator = PR-Autor, Self-Approval verboten, `bypass_actors` leer, wirdigital hat `permission: none` → niemand kann approven), und der Pre-Push-ruff-Hook (O2) ist **im Hauptanwendungsfall funktionslos** (#3: `cd <repo> && git push` → silent-allow, weil das JSON-quote-adjazente erste `cd` den Boundary-Regex nie matcht).
- Der Hook-„Funktionstest" der Increment-Session war **Schein-Grün** (#3-Beleg): Die Test-Shell stand zufällig im Zielrepo, der Deny kam über den `$PWD`-Fallback statt über die getestete cd-Erkennung — Selbsttest teilte den Blindfleck mit dem Prüfling.
- Commit-Hygiene-Ausfall in ~/.claude (#4/#5): `fb4d0e2` bündelt unter einem Hook-Titel **9 unbenannte Sachänderungen** (Modellwechsel, 2× SSH-Permission, Hook-Wirings, Theme, env-Var) **plus einen rotierten Bearer-Token-Wert** — beide Token-Werte liegen jetzt in der lokalen Git-Historie (kein Remote; Alt-Wert war seit Erstimport committet); drei referenzierte Hook-Dateien sind untracked → die committete Config ist nicht self-contained.
- Wiederholungs-Muster im Increment: Das Symlink-Verwerfen (Item 24) wurde empfohlen und ausgeführt, **obwohl** die eigene, ältere Memory („NICHT von Hand verwerfen", 15:14Z) und der eigene PR-Body („Nach Merge nötig", 15:18Z) es untersagten (#7); die neue Tracking-Hausregel wiederholt das im selben Increment als unzureichend diagnostizierte Muster „Instruktion ohne Gate" (#8 — `always-instruction-without-enforcement` damit ×2 ⇒ gate-pflichtig).
- Positiv falsifiziert: „Issues zitieren ungemergte Quelle" traf nur 1 von 3 Issues, „0 Umsetzungen im Gate-Sprint" und „dangling Handoff" hielten dem Steelman nicht stand (Chat-Board ist die dokumentierte Handoff-Konvention).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Report-Erstpush ohne Meta-Korrektur (Quoting-Fehler), Korrektur 65 s später als Commit 2; die publish-before-check-Klasse via `git push` ist vom M7-Scanner strukturell ungedeckt (Scanner kennt nur gh-Carrier) | fehlende Validierung | mittel | SURVIVES | #1062 Commits 14:50:29Z/14:51:34Z; Scanner-grep: 0 Treffer git push | claim-before-cheapest-check (gate-pflichtig, weiteres Vorkommen) |
| 2 | **M1-Review-Rule = Merge-Deadlock:** mcp-hub hat nur achimdehnert als Collaborator (wirdigital `permission: none`), GitHub verbietet Self-Approval, `bypass_actors: []`/`can_bypass: never` → kein PR kann je approved werden; Erfolgsfall des Gates nie bewiesen, #171 seit 2 Tagen BLOCKED | fehlende Validierung / Werkzeug | **kritisch** | SURVIVES | Ruleset 17621473 (15:16:40Z); collaborators-API; #171 REVIEW_REQUIRED, reviews: [] | autonomous-no-human-review (technische Variante, Parent #4) |
| 3 | **O2-Push-Hook im Hauptfall funktionslos:** `cd <repo> && git push` → silent-allow (JSON-quote-adjazentes erstes `cd` matcht Boundary-Regex nie → `$PWD`-Fallback); ebenso pushd, `cd "$VAR"`, 3×-cd (nimmt mittleres/falsches Dir); Increment-Selbsttest war Schein-Grün (Test-CWD = Zielrepo) | fehlende Validierung / Werkzeug | hoch | SURVIVES | Live-Ausführungstests des Skeptikers gegen Fixture-Repo (deny/silent je Muster dokumentiert); hooks/block_unformatted_push.sh:20-26 | lint-failure-no-local-gate (Gate gebaut, aber unwirksam) |
| 4 | `fb4d0e2` bündelt unter „Pre-Push-ruff-Gate" 9 unbenannte Sachänderungen (model→fable, theme, 2× `Bash(ssh hetzner-prod:*)`, PreToolUse-Neuverdrahtung 3 Hooks, SessionStart/SessionEnd-Einträge, env-Var) + komplette Reformatierung; 3 referenzierte Hooks untracked (`??`) → Config nicht self-contained | Prozesslücke | hoch | SURVIVES | `git diff fb4d0e2~1 fb4d0e2 -- settings.json --ignore-all-space`; git status ?? | — |
| 5 | Bearer-Token-Rotation im selben Diff: alter (`nvyxLK…`, seit Erstimport 52255b8 in Historie) UND neuer Wert (`lL-qk-M…`) liegen nun beide in der ~/.claude-Historie; kein Remote (lokal begrenzt), aber unrotierter Alt-Wert + Klartext-Muster bleiben | Risiko/Secret-Hygiene | mittel | SURVIVES | `git log -S 'Bearer' --oneline -- settings.json` → 52255b8, fb4d0e2; `git remote -v` leer | secret-leak-via-safe-pattern-Familie (f4a546 ×1) |
| 6 | M7-Scanner deckt weniger als die eigene Memory behauptet: `gh pr merge` fehlt im Carrier-Regex, obwohl merge real `-b/--body`/`-F` trägt (live geprüft, gh 2.92); `$(< file)` und Backticks ungedeckt | fehlende Validierung | mittel | SURVIVES | evidence_claim_scanner.py:153; `gh pr merge --help`; Memory-Wortlaut Z. 21 | claim-before-cheapest-check-Familie (Memory-Claim > Code) |
| 7 | Symlink-Verwerfen (Item 24) empfohlen+ausgeführt GEGEN eigene ältere Memory („NICHT von Hand", 15:14Z) und eigenen PR-Body („Nach Merge nötig", #1064 15:18Z); Ist: 8 Symlinks wieder da | Prozesslücke | mittel | SURVIVES | Zeitreihe Memory-mtime < PR-createdAt < Verwerfen (Folgetag); status --short 8×T | platform-pinned-perma-dirty-loop (×2 im Längsschnitt) |
| 8 | Neue Tracking-Hausregel (21a7774) ist reine Instruktion ohne Gate — exakt das Muster, das `fb4d0e2` im selben Increment als „hielt nicht → hartes Gate" diagnostiziert; kein Gate-Ticket für die Regel selbst existiert | verfrühte Festlegung | mittel | SURVIVES | 21a7774 (reiner Text); Hook-Header Z. 6-8; Issue-Suche ohne Treffer (Skeptiker-Beleg korrigiert: iil-adrfw#62 gated planned-phase, nicht diese Regel) | always-instruction-without-enforcement (**×2 ⇒ gate-pflichtig**, f4a546 ×1 + hier) |
| 9 | Hook-default-branch-Fallback „main": bei Repo ohne origin/HEAD-Symref und Nicht-main-Default degradiert Diff auf HEAD~1 und übersieht frühere Commits desselben Pushes (empirisch bewiesen); Trigger in dieser Flotte aktuell latent (0×master/65 Repos, aber ~15 ohne Symref) | Werkzeug | niedrig | SURVIVES | Skeptiker-Fixture-Beweis; Flotten-Scan 65 Repos | — |
| 10 | Issues zitieren ungemergte Retro-Quelle (Parent-Muster-Wiederholung) | — | — | REFUTED | nur mcp-hub#170 zitiert den Pfad (1/3); #1081/#1082 nicht — Enumeration überzogen | — |
| 11 | Ruleset-Änderung verstößt gegen neue Tracking-Hausregel | — | — | REFUTED | Regel-Wortlaut deckt nur AUFGESCHOBENES, nicht vollzogene Config-Änderungen; Rest-Gap (M1-Boardzeile nie aktualisiert) real, aber kein Regelverstoß | — |
| 12 | Dangling PRs ohne Handoff-Kommentar in den PRs | — | — | REFUTED | Org-Konvention (CLAUDE.md) definiert Chat-Action-Board als Handoff-Fläche; keine PR-Kommentar-Pflicht dokumentiert | — |
| 13 | Gate-Sprint: 4 Issues, 0 Umsetzungen | — | — | REFUTED | 2 Sofort-Umsetzungen existieren (Scanner 534d021, Hook fb4d0e2); Issues waren beauftragte Spec-Artefakte | — |
| 14 | Gate-Sprint ließ 2 Slugs ungedeckt | — | — | REFUTED | stale-local-clone ist doppelt skill-gegated (session-retro v2.4 + send-mail v1.1); nur handover-stale-Hälfte ist echte Lücke (in §8 geführt) | — |
| 15 | #167-Close-Timing (Parent-Ereignis) | — | — | pre_refuted | Parent-Scope, Re-Litigation (Increment-Regel 2); Parent-Befund #3 deckt es | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | 11/11 Maßnahmen geliefert, aber M1 defekt (#2) und O2 im Kernfall wirkungslos (#3) — Ziel „Gates wirksam" teilverfehlt |
| architektur_design | 2 | Zwei von drei neuen Gates mit Konstruktionsfehlern, die Rework erzwingen (#2 Deadlock, #3 Parsing; #9 Fallback) |
| code_konventionstreue | 3 | #4 Commit-Scope-Bruch + untracked referenzierte Hooks; übrige Commits (Scanner, M8, Report) sauber und getestet |
| risiko_debt | 2 | #5 Token-Zweitwert in Historie, #4 nicht-self-contained Config, #2 unbemerkter Deadlock — neue unbeabsichtigte Risiken im Härtungs-Increment selbst |
| prozess_effizienz | 3 | Hoher Durchsatz (11 Maßnahmen, 3 Repos), wenig Increment-internes Rework (#1: 65 s); Abzug für Schein-Grün-Test (#3) |
| entscheidungsqualitaet | 2 | #7 Empfehlung gegen eigene dokumentierte Erkenntnis, #8 diagnostiziertes Anti-Muster selbst wiederholt — Selbstkonsistenz-Ausfälle trotz guter Einzelbegründungen |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Report per Skript editiert, Push lief trotz Skript-Syntaxfehler weiter (Commit 2 als Flick) | Edit-Skript + Commit/Push mit `set -e`-Semantik koppeln: Push nur bei Exit 0 des Edit-Schritts; nach jedem Publish Remote-Grep auf die neuen Marker | 1 |
| Review-Rule scharf geschaltet ohne Approver-Inventur | Vor jeder Review-Pflicht-Regel: `gh api …/collaborators` prüfen — existiert ≥1 approve-fähiger Nicht-Autor? Sonst `bypass_actors` (Admin-Rolle) setzen oder Zweitaccount einladen, DANN scharf schalten; Erfolgsfall (Review→Merge) einmal real durchspielen | 2 |
| Hook-Selbsttest aus CWD=Zielrepo → Fallback maskierte Parsing-Defekt | Gate-Selbsttests IMMER aus fremdem CWD fahren (Hook-Prozess-Realität) und je Erkennungszweig einen Negativtest (falsches CWD) mitführen | 3 |
| `json.dump` + `git add` über Datei mit fremden uncommitteten Änderungen | Config-Edits chirurgisch (nur Ziel-Key), vor Commit `git diff --ignore-all-space --staged` lesen; fremde pending-Änderungen stashen oder explizit benennen | 4 |
| Token-Wert-Änderung unbemerkt mitcommittet | settings.json-Commits durch den Secret-Scan mit Wert-Diff-Erkennung ziehen (`git diff -S`-Check auf Authorization-Zeilen), Header-Secrets perspektivisch in env/Secret-Datei auslagern | 5 |
| Memory behauptet merge-Carrier, Code hat ihn nicht | Beim Schreiben einer Memory über ein gebautes Gate: Geltungsliste 1:1 aus dem Code-Regex zitieren, nicht aus der Intention | 6 |
| Item-24-Empfehlung ohne Abgleich mit eigener Memory/PR-Body vom Vortag | Vor jeder Empfehlung eines manuellen Eingriffs: grep der eigenen Memories + offener PR-Bodies auf das Ziel-Artefakt (hier: „pinned") — Widerspruch ⇒ Empfehlung stoppen | 7 |
| Hausregel committet ohne Gate-Ticket, Muster im selben Increment als unzureichend diagnostiziert | Jede neue „immer/nie"-Hausregel bekommt im selben Commit entweder einen Gate-Verweis (Hook/CI/Issue) oder eine explizite „bewusst ungegated, weil Judgment"-Zeile | 8 |
| default-branch geraten („main") | `git symbolic-ref` -Fallback um `gh repo view --json defaultBranchRef` ergänzen (ein API-Call, deterministisch), erst dann HEAD~1 | 9 |

## 5. Längsschnitt (retro_kpis.py-Lauf vom 2026-07-11, Parent-Zähler + Increment)

- **`always-instruction-without-enforcement`: ×1 (f4a546) + #8 hier = ×2 ⇒ GATE-PFLICHT** (Increment-Regel 3: Parent-/Vortages-Slug wiederholt). Gate-Vorschlag in §6.
- `claim-before-cheapest-check` (bereits gate-pflichtig, ×14+): #1 und #6 sind weitere Vorkommen — der M7-Scanner deckt gh-Carrier, aber nicht `git push`-Publishes und nicht `gh pr merge`; Gate-Nachschärfung nötig statt neuem Memo.
- `platform-pinned-perma-dirty-loop` (Parent neu): #7 = Vorkommen 2, Gate existiert bereits als offener PR #1064 — wirksam erst nach Merge + einmaligem Cleanup in der DORT dokumentierten Reihenfolge.
- `secret-leak-via-safe-pattern` (f4a546 ×1): #5 ist ein verwandtes, nicht identisches Muster (Wert-Diff durch Scan gerutscht) — als Familie vermerkt, nicht als Zähler-Inkrement.

**5b. Autonomie-Kalibrierung:** `over_ask: 0`, `over_act: 0` — M1 war explizit approved (Security-Config-Gate eingehalten); der Defekt ist Ausführungs-, nicht Autonomie-Fehler. Kein Item wurde vorgelegt, das deterministisch war, und keines autonom vollzogen, das ein Gate war.

## 6. Verankerung (Vorschläge — Übernahme entscheidet der Mensch)

**memory_candidates:**

```markdown
---
name: gate-selftest-from-foreign-cwd
description: Gate-/Hook-Selbsttests aus fremdem CWD fahren + Negativtest je Erkennungszweig — ein Test, der den Fallback-Pfad trifft, beweist den Hauptpfad nicht (Push-Hook war im Kernfall funktionslos trotz „deny ✓"-Test)
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-11-pushhook-schein-gruen
---
Realfall (Retro d2522c-incr #3): block_unformatted_push.sh wurde mit `cd <repo> && git push`
getestet und lieferte deny — aber nur, weil die Test-Shell bereits im Zielrepo stand und der
`$PWD`-Fallback griff; die eigentlich getestete cd-Erkennung matcht das JSON-quote-adjazente
erste `cd` NIE (Boundary-Regex). In Prozess-Realität (Hook-CWD=Home) ist der Hauptfall
silent-allow. **How to apply:** Hook-Tests mit explizit fremdem CWD ausführen; je
Erkennungszweig (Parsing, Fallback) einen eigenen Positiv- UND Negativfall; „Gate grün" erst
behaupten, wenn der Test nachweislich den beabsichtigten Zweig traf (z. B. Debug-Ausgabe des
erkannten Verzeichnisses assertieren).
```

```markdown
---
name: review-rule-braucht-approver-inventur
description: Vor Scharfschalten einer required-review-Regel prüfen, ob ein approve-fähiger Nicht-Autor existiert (Collaborators + Self-Approval-Verbot) — sonst Deadlock; Erfolgsfall einmal real durchspielen
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-11-mcp-hub-review-deadlock
---
Realfall (Retro d2522c-incr #2): mcp-hub-Ruleset bekam required_approving_review_count=1 mit
bypass_actors=[] — einziger Collaborator ist der PR-Autor (achimdehnert), wirdigital hat dort
permission:none, GitHub verbietet Self-Approval ⇒ KEIN PR mehr mergebar (#171 seit Tagen
BLOCKED). **How to apply:** Vor jeder pull_request-Rule: `gh api repos/<r>/collaborators`
+ Frage „wer außer dem typischen Autor kann approven?"; wenn niemand: erst Zweitaccount
einladen ODER bypass_actors (Admin-Rolle) setzen; danach den Erfolgsfall (Review→Merge) an
einem Wegwerf-PR beweisen — ein Gate, dessen Erfolgsfall nie lief, gilt als nicht vorhanden.
```

**adr_candidates:** keiner (beides Ausführungs-Patterns, kein Architektur-Entscheid — adr-threshold).

**Gate-Vorschlag für `always-instruction-without-enforcement` (×2):** PreToolUse-Hook-Erweiterung oder CI-Check auf ~/.claude-Commits: Ein Commit, der in CLAUDE.md eine Zeile mit „IMMER/NIE/jede(r)/PFLICHT" hinzufügt, muss im selben Diff einen Gate-Verweis (`hooks/`, `Issue #`, „bewusst ungegated:") enthalten — sonst WARN im Stop-Hook. Deterministisch, ~30 Zeilen; als Issue zu tracken (siehe §7 N4).

## 7. Maßnahmen (Action-Board)

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| N1 | Deadlock M1 lösen | mcp-hub | [Ruleset](https://github.com/achimdehnert/mcp-hub/settings/rules) | 🟢 offen | Entscheid: bypass_actors=Admin ODER wirdigital einladen (du) |

### 🔵 Offen — ich kann sofort (nach Go)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| N2 | Push-Hook-Parsing fixen + Fremd-CWD-Tests | ~/.claude | [Hook](file:///home/devuser/.claude/hooks/block_unformatted_push.sh) | 🔵 ready | cd-Erkennung (letztes cd), pushd, gh-defaultBranch (#3/#9) (ich) |
| N3 | Scanner: merge-Carrier + $(<)-Variante | ~/.claude | [Scanner](file:///home/devuser/.claude/hooks/evidence_claim_scanner.py) | 🔵 ready | Regex + Memory angleichen (#6) (ich) |
| N4 | Gate-Issue instruction-without-enforcement | platform | §6-Spec | 🔵 ready | Issue anlegen (×2-Slug) (ich) |
| N5 | Untracked Hooks committen + Token-Hygiene | ~/.claude | `git status ??` | 🔵 ready | 3 Hooks committen; Token-Auslagerung vorschlagen (#4/#5) (ich) |

## 8. Nicht verifiziert (Restlücken)

- **handover-stale-vor-merge** bleibt ohne systemisches Gate (Skeptiker-bestätigt: `handover_prio_mirror.sh` deckt anderes Muster; M5 fixte nur die Einzelinstanz) — billigster nächster Schritt: Gate-Spec-Issue analog #1080-Familie.
- **Ob der Orchestrator-Alt-Token noch gültig ist** (Rotations-Bedarf über die Historie-Frage hinaus): billigster Check = ein Call mit Alt-Wert gegen `/readyz`-geschützten Endpoint — bewusst NICHT ausgeführt (Secret-Handling nur auf Owner-Wunsch).
- **M1-Boardzeile im Parent-Report** (sagt „🟢 offen … (du)", real wurde die Rule 26 min später gesetzt) — Doku-Staleness im ungemergten #1062; Korrektur lohnt nur, falls #1062 ohnehin angefasst wird.
- **Skeptiker-Beleg-Korrektur:** Ein Skeptiker prüfte für Befund #8 versehentlich mcp-hub#62 statt iil-adrfw#62; das Verdikt trägt unabhängig davon (auch iil-adrfw#62 gated die Tracking-Regel nicht — es gated planned-phase), im Beleg der Tabelle vermerkt.

## Self-Review

Phase-5-Meta-Review (2026-07-12): Alle 9 Checkliste-Punkte PASS — Frontmatter-Summen, Tabellenschema, Score-Anker, Soll/SURVIVES-Invariante (9==9), Sektionsreihenfolge, Recurring-Slug-Abdeckung, Verankerungsformat und Increment-Pfadkonvention wurden gegen den Report-Text geprüft. Einzige Beobachtung ohne Korrekturbedarf: refuted_rate (0,40, Nenner 15) und die im Fließtext zitierte „echte Falsifikationsquote" (0,357, Nenner 14 ohne pre_refuted) sind zwei bewusst unterschiedene Metriken, keine Inkonsistenz.
