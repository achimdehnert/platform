---
retro_schema: 1
date: 2026-07-10
repo_scope: [platform]
session_id: f4a546-incr
footprint: full
findings_total: 7
findings_survived: 6
refuted_rate: 0.14
phase3_refuted: 1
pre_refuted: 0
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [local-test-gate-narrower-than-ci, security-hook-unversioned]
recurring_findings: [local-test-gate-narrower-than-ci, lint-failure-no-local-gate, ci-gate-maskiert-failure, security-hook-unversioned, workaround-without-tracking-anchor, hook-coverage-gap-and-doctrine-drift, credential-rotation-first-match-untested, machine-config-no-registry]
---

# Session-Retro 2026-07-10 — platform (f4a546-incr): Abarbeitung der f4a546-Maßnahmen

Increment-Retro auf dem Anchor des Parent-Retros
[f4a546](session-retro-2026-07-10-platform-f4a546.md): Scope ist NUR das Zeitfenster ab 12:00Z —
Hook-Patch M3, PRs [#1050](https://github.com/achimdehnert/platform/pull/1050) (Skill v1.1 + Tests)
und [#1051](https://github.com/achimdehnert/platform/pull/1051) (Policy) und
[#1048](https://github.com/achimdehnert/platform/pull/1048) (Report), alle 12:47Z gemergt
(wirdigital-Review, kein Bypass), 2 Drift-Memories, Cleanup. Right-Sizing: `full`
(3 PRs > lean-Grenze; kein Prod-Schritt).

## 1. Executive Summary

- **Alle Maßnahmen M1–M7 sind umgesetzt und gemergt**; der Merge-Weg war diesmal vorbildlich (normal → `--auto` armiert → echtes Review; Parent-Befund #2 wiederholte sich nicht, `over_act=0`).
- **Härtester Befund:** Das frisch verankerte Review-Gate 5b prüft lokal 388 Tests, CI prüft 486 — der Makefile-Kommentar „identisch zu tools-tests.yml" ist falsch; die M7-Maßnahme kodifiziert damit eine Lücke, die sie schließen sollte (#1).
- **Governance-Lücke:** Der sicherheitskritischste Fix der Session (Hook-Patch M3) ist als einziger unversioniert — untracked in `~/.claude`, kein Log, keine Konvention (#3).
- **Skeptiker widerlegte 1 von 7:** Die stale Live-Kopie war — anders als vom Finder behauptet — explizit als offenes Gate-Item N1 im Abschluss-Board geführt (REFUTED auf den Streitpunkt; Staleness selbst ist Fakt und via N1 getrackt).
- refuted_rate 0.14 — Falsifikation wieder im gesunden Band (Parent-Lauf: 0.00).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Review-Gate 5b/`make test` deckt CI-Scope nicht: lokal 388 vs. CI 486 passed (tools-tests.yml fährt 4 zusätzliche Testorte); Makefile-Kommentar „identisch zu tools-tests.yml" objektiv falsch; Differenz in der Session nie bemerkt | fehlende Validierung | hoch | SURVIVES | Makefile Z.124-125 vs. `.github/workflows/tools-tests.yml`; beide pytest-Läufe reproduziert (388/486); Transkript-Scan: 0 Erwähnungen | local-test-gate-narrower-than-ci ×1 (Familie: lint-failure-no-local-gate ≥2 + ci-gate-maskiert-failure ≥2, beide bereits gate-pflichtig) |
| 2 | Live-Kopie `~/.claude/commands/send-mail.md` nach M4/M5-Merge stale und „an keiner Stelle als offen geführt" | Prozesslücke | hoch | REFUTED | Phase-2.5-Konfliktpaar: Finder A behauptete „nirgends offen geführt", Finder C referenzierte das Abschluss-Board Z.689 — Skeptiker zog das Transkript unabhängig: Staleness bestätigt (source_commit b02981a < 8711993), ABER Board Z.689 führt sie explizit als Gate-Item N1 („du: go rollout sagen") inkl. ADR-230-§8-Begründung | — |
| 3 | M3-Hook-Patch (block_env_cat.sh) unversioniert: untracked (`??`) im `~/.claude`-git-Repo, kein Log-Eintrag; keine dokumentierte Commit-Konvention für sicherheitsrelevante Hooks (andere Hooks werden nachweislich committet) | Prozesslücke | hoch | SURVIVES | `git -C ~/.claude status --porcelain` (`?? hooks/block_env_cat.sh`), `git log -- hooks/block_env_cat.sh` leer; Steelman notiert: kein Remote → kein PR möglich, mildert, widerlegt nicht | security-hook-unversioned ×1 (neu) |
| 4 | Guard-Falsch-Positiv (12:38Z: legitimer commit+push+`gh pr create` geblockt durch `\| tail` + Secret-Pfad-ERWÄHNUNG im Prosa-Body) still per `--body-file` umgangen; „kein Handlungsbedarf"-Randnotiz ohne Tracking-Anker, im letzten Board nicht mehr geführt | Prozesslücke | mittel | SURVIVES | Transkript Z.594/595 (Deny) → Z.601 (Workaround); Randnotiz Z.621 („kein Handlungsbedarf"); kein Issue/Memory/Hook-Fix existiert | workaround-without-tracking-anchor ×1 (neu) |
| 5 | Hook-Patch mit empirisch nachgewiesenen Coverage-Lücken (`sed`, `python3 -c open(…)`, Redirect-in-Nicht-Reader bypassen) + Doktrin-Widerspruch im File (Kopf: „bei Parse-Zweifel ALLOW" vs. neuer Block: „nicht verifizierbar → deny") | Werkzeug | mittel | SURVIVES | Skeptiker-Bypass-Tests gegen den Live-Hook (3× ALLOW auf Non-KV-Secret); Hook Z.8 vs. Z.25/42 | hook-coverage-gap-and-doctrine-drift ×1 (neu) |
| 6 | `load_credentials` liefert bei zwei Paaren mit identischem user still den ERSTEN (=veralteten) Wert (Passwort-Rotation ohne Löschen); Fall ungetestet — reproduziert | fehlende Validierung | niedrig | SURVIVES | Skeptiker-Repro: `('ad@d.team','OLD_STALE')`; test_send_mail.py deckt nur parse_env-Duplikate | credential-rotation-first-match-untested ×1 (Familie: untested-tool-module-green-gate ×1 Parent) |
| 7 | Maschinen-Config-Ausnahme verlangt nur Changelog-Prosa, keine strukturierte Registry der `~/.claude/*.env` — kein abfragbarer Index für künftige Sessions | verfrühte Festlegung | niedrig | SURVIVES | `ls ~/.claude/*.env` → 1 Datei; kein Registry-Analogon; Steelman: YAGNI bei n=1, mindert Priorität | machine-config-no-registry ×1 (neu) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | M1–M7 vollständig geliefert + gemergt + verifiziert; Abzug: M7 erreicht sein Ziel nur teilweise (#1) |
| architektur_design | 3 | Gate-Design #1 (Scope-Lücke kodifiziert), Hook-Doktrin-Widerspruch #5, Registry-Frage #7 |
| code_konventionstreue | 3 | PRs/Commits/F-H-Trennung sauber; signifikante Abweichung: unversionierter Security-Hook #3 |
| risiko_debt | 3 | Kein neuer Leak; Rest-Risiko: Hook-Bypässe #5 + unversionierter Fix #3 + Rotation-Falle #6 |
| prozess_effizienz | 4 | Zügig (Merges 12:47Z, Cleanup 12:58Z, alles verifiziert); Reibung: 1 Falsch-Positiv-Umweg #4 |
| entscheidungsqualitaet | 4 | Merge-Weg vorbildlich (kein `--admin`, `--auto` + echtes Review); Abzug: „kein Handlungsbedarf"-Entscheid ohne Anker #4 |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `make test` (388) als CI-Äquivalent behandelt; Makefile-Kommentar behauptet Identität mit tools-tests.yml (486) | Makefile-`test`-Target auf die CI-Testorte-Liste angleichen (SSoT: eine Stelle, aus der beide lesen) + Policy-5b-Wortlaut danach präzisieren | #1 |
| Hook 12:34 direkt in der Live-Datei editiert, nie `git -C ~/.claude add/commit` | Sicherheitsrelevante Hook-Änderung endet erst mit Commit ins `~/.claude`-Repo (Message mit Retro-/Incident-Referenz); als Konvention in `~/.claude/CLAUDE.md` verankern | #3 |
| Falsch-Positiv per `--body-file` umgangen, Randnotiz „kein Handlungsbedarf", im letzten Board nicht mehr geführt | Jeder Guard-Falsch-Positiv bekommt einen Anker (Board-Item oder Memory) — „kein Handlungsbedarf" ist eine Entscheidung, die trackbar sein muss, sonst unauffindbar bei Wiederholung | #4 |
| Neuer deny-bei-Zweifel-Block eingefügt, Kopfdoktrin „ALLOW bei Zweifel" unverändert; sed/python-Bypässe unbehandelt | Beim Hook-Edit Kopfdoktrin mitziehen (Sonderfall dokumentieren) + bekannte Nicht-Abdeckungen explizit als Grenzen im Header listen (ehrlicher Scope statt implizite Vollständigkeit) | #5 |
| Testdatei deckt parse_env-Duplikate, nicht load_credentials-Duplikate | Beim Testen eines Auswahl-Contracts immer auch den Mehrdeutigkeits-Fall spezifizieren (first-match dokumentieren ODER last-match implementieren + Test) | #6 |
| Ausnahme mit Changelog-Prosa verankert, kein Index | Schwelle in die Policy-Zeile aufnehmen: „ab der 2. Maschinen-Config wird eine Registry-Datei angelegt" — YAGNI-bewusst, aber mit definiertem Kipp-Punkt | #7 |

## 5. Längsschnitt (retro_kpis.py, Lauf 13:19Z)

- Parent-Slugs (`f4a546`) sind jetzt maschinell gezählt: `stale-local-clone-as-ground-truth` ×4 🚨 (Gate = M4-Freshness-Zeile, in #1050 geliefert); die 6 übrigen Parent-Slugs stehen auf ×1.
- **Kein Parent-Slug wiederholte sich im Increment wörtlich** (keine same-day Gate-Pflicht ausgelöst). #1 gehört laut **manueller Durchsicht** (nicht `retro_kpis.py` — das Tool zählt nur wörtliche Slugs, keine Familien) zu zwei Slug-Familien, die bereits ≥2 zählen und gate-pflichtig sind (`lint-failure-no-local-gate`, `ci-gate-maskiert-failure`); beide sind deshalb zusätzlich ins Frontmatter-`recurring_findings` aufgenommen, damit der nächste Tool-Lauf sie mitzählt. Das Soll-1-Item (Makefile↔CI-Angleich) IST der fällige Gate-Fix dieser Familien, kein weiteres Memo.
- Neue Slugs (×1, beobachten): `security-hook-unversioned`, `workaround-without-tracking-anchor`, `hook-coverage-gap-and-doctrine-drift`, `credential-rotation-first-match-untested`, `machine-config-no-registry`.

### 5b. Autonomie-Kalibrierung

- `over_act = 0`: Merge-Weg diesmal korrekt (normal → `--auto` → menschliches Review; Finder und Skeptiker bestätigten unabhängig „kein Bypass").
- `over_ask = 0`: N1 (Live-Rollout) als User-Gate zu führen ist ADR-230 §8, kein Over-Ask.
- Parent-`over_act=1` (Bypass-Klasse) hat sich nicht wiederholt — die frisch geschriebene Memory `no-escalation-flag-after-policy-block` wurde im selben Zeitfenster real befolgt.

## 6. Verankerung (kopierfertige Kandidaten — Entscheidung beim Menschen)

**memory_candidates:**

```markdown
---
name: hooks-repo-commit-pflicht
description: "Sicherheitsrelevante ~/.claude/hooks-Änderungen sofort im ~/.claude-Repo committen (Message mit Incident-/Retro-Referenz)"
metadata:
  type: feedback
---
~/.claude ist ein git-Repo (lokal, ohne Remote) — Hook-/Guard-Änderungen sind erst fertig, wenn
committet (Realfall 2026-07-10: der kritischste Fix der Session, block_env_cat.sh cut-Leak-Patch,
lag als einzige Maßnahme untracked ohne Log-Spur; andere Hooks werden nachweislich committet).
**Why:** Ohne Commit keine Review-Spur, kein Diff bei Regression, Verlustrisiko.
**How to apply:** Nach jedem Hook-Edit: git -C ~/.claude add <hook> && commit mit Referenz
(z. B. "retro f4a546 #1"). Gilt auch für settings.json-Änderungen an Hook-Registrierung.
```

**adr_candidates:** keiner — Maßnahmen sind Makefile-/Hook-/Test-/Policy-Edits nach bestehendem Muster.

## 7. Maßnahmen (Action-Board)

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| I1 | Memory hooks-repo-commit-pflicht? | — | [report](file:///home/devuser/.repo-session/worktrees/platform/2026-07-10-achim-dehnert-retro-f4a546-incr-131916/docs/retros/session-retro-2026-07-10-platform-f4a546-incr.md) | 🟢 offen | du: §6 freigeben |
| I2 | Live-Rollout v1.1 (=N1, unverändert) | — | [commands](file:///home/devuser/.claude/commands/send-mail.md) | 🟢 offen | du: „go rollout" |

### 🔵 Offen — ich kann sofort (auf Zuruf)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| I3 | Makefile test = CI-Scope | platform | [Makefile](file:///home/devuser/github/platform/Makefile) | 🔵 ready | ich: Fix-PR (#1) |
| I4 | Hook committen + Doktrin/Grenzen | — | [hook](file:///home/devuser/.claude/hooks/block_env_cat.sh) | 🔵 ready | ich: commit (#3,#5) |
| I5 | Rotation-Test + first-match-Doku | platform | [tests](file:///home/devuser/github/platform/tools/tests/test_send_mail.py) | 🔵 ready | ich: mit I3 (#6) |
| I6 | Falsch-Positiv-Anker anlegen | — | [hook](file:///home/devuser/.claude/hooks/block_env_cat.sh) | 🔵 ready | ich: Memory (#4) |
| I7 | Registry-Schwelle in Policy-Zeile | platform | [policy](file:///home/devuser/github/platform/policies/claude-skills.md) | 🔵 ready | ich: mit I3 (#7) |

## 8. Nicht verifiziert (Restlücken)

- **Skeptiker-Bypass-Tests (#5):** Ob die 3 ALLOW-Nachweise per Hook-Payload-Simulation oder realem Kommando-Lauf erfolgten, ist aus dem Skeptiker-Bericht nicht eindeutig — im zweiten Fall läge der Token nun auch im Subagenten-Transkript. Billigster Check: Subagenten-Transkript nach dem Secret-Dateinamen greppen.
- **`Prod-Uptime-Canary`-Lauf (13:01Z):** conclusion stand beim Collect noch aus. Billigster Check: `gh run list --repo achimdehnert/platform --limit 3`.
- **Parent-§8-Lücken** (Auto-Scaffold-Failure 11:53Z, Transkript-Retention) blieben unbearbeitet offen — bewusst nicht re-litigiert (Increment-Scope), aber auch nicht geschlossen. Billigster Check: `gh run view <auto-scaffold-run-id> --log-failed` bzw. `ls -la ~/.claude/projects/-home-devuser/*.jsonl`.

## Self-Review (Phase 5)

Meta-Review (separater Agent, nur Report vs. Skill): 6 PASS, 4 Beanstandungen. Übernommen: (a) §5-Familien-
Behauptung war als Tool-Output verkleidet, obwohl `retro_kpis.py` keine Familien-Logik hat → als manuelle
Durchsicht gekennzeichnet + beide Familien-Slugs ins Frontmatter (damit der Zähler sie ab jetzt führt);
(b) Beleg-Zelle #2 um das Phase-2.5-Konfliktpaar ergänzt; (c) fehlender billigster Check in §8 Bullet 3.
**Zurückgewiesen mit Begründung:** die Beanstandung „`file://`-URL niemals in die Tabellenzelle" — die
kanonische `~/.claude/CLAUDE.md` (Action-Board Regel 4) verlangt exakt das Gegenteil (jede Zeile trägt
einen klickbaren `[label](file://…)`-Link); die vom Meta-Reviewer zitierte Gegenregel stammt aus einer
Repo-Memory, und CLAUDE.md deklariert Repo-Memories in diesem Konflikt ausdrücklich als „Log, nicht
Quelle". Der REFUTED-Befund #2 bleibt mit eigener Nummer in der Tabelle (Phase-2.5-Konfliktfund:
„Nur die skeptiker-verifizierte Version geht in den Report — mit eigener Befund-Nummer").

**refuted_rate-Band:** Der gemeldete Wert 0.14 liegt am unteren Ende der Serie
(0.33 · 0.13 · 0.20 · 0.40 · 0.12 · 0.29 · 0.00 · 0.36 · 0.00 · [0.14]); echte Falsifikationsquote =
1/7 ≈ 0.14 (pre_refuted=0, identisch). Letzte drei Läufe: 0.36 · 0.00 · 0.14 — zwei von drei bei oder
unter 0.2, numerisch unteres Band, mechanisch kein 3er-Block unter der Schwelle; keine Aussage über die
inhaltliche Richtigkeit der Einzelverdikte.
