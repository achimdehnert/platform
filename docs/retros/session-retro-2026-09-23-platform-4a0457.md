---
retro_schema: 1
date: 2026-09-23
repo_scope: [platform, cad-hub, ausschreibungs-hub, gaeb-toolkit]
session_id: 4a0457
footprint: full
footprint_reduction_reason: "Regel-B-Level wäre deep (4 Repos beschrieben). Reduktion auf full: (a) jede Repo-Erweiterung durch wörtliches Owner-Go gedeckt (Nutzer-Nachricht 09:42:45Z, vor Issue 09:43:56Z und Merges 09:54/09:57Z), (b) nur Docs/Kommentare/Build-Config, voll rollback-fähig, keine Migration, kein Prod/Publish, (c) Befund-Schätzung ≤10 (Ist: 13 gefunden, 7 überlebt)."
findings_total: 15
findings_survived: 10
refuted_rate: 0.33
phase3_refuted: 5   # 6 in Phase 3, davon 1 (#8) in Phase 3b zurück auf SURVIVES gekippt
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [deferred-item-no-tracking-issue, owner-gate-embedded-in-sa4-criterion]
recurring_findings: [deferred-item-no-tracking-issue, owner-gate-embedded-in-sa4-criterion, unbegruendete-festlegung-im-auftrag, kundenname-in-public-repo-artefakt, handover-stale-vor-merge]
gates_caught: [scope-checkpoint-not-durably-recorded]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: "In dieser Retro hat jede Phase ein Ergebnis verändert: 2.5 löste einen Finder-Widerspruch (B2), Phase 3 kippte 6 von 9 vorgelegten Behauptungen, der Stop-Hook fing den fehlenden Checkpoint-Text — kein Melder ohne Leser, keine Dublette belegt."
---

# Session-Retro 2026-09-23 · platform/cad-hub/ausschreibungs-hub/gaeb-toolkit · Sitzung 4a0457

**Session-Thema:** Zwei-Repo-Analyse nl2cad/cad-hub mit Merge-Verdikt gegen die Anforderung
„Vollständigkeitsprüfung Bauanträge" (Angebotsmail an ein Pilot-Landratsamt), danach `/prompt`-Auftrag
„cad-hub als Tool ausbauen" inkl. Preisspiegel-Anfrage eines Pilotkunden (SF-Bau) → Zielzustand-Issue
[cad-hub#72](https://github.com/achimdehnert/cad-hub/issues/72), KONZ-003-Sunset
[ausschreibungs-hub#313](https://github.com/iilgmbh/ausschreibungs-hub/pull/313), Paket-Anonymisierung
[gaeb-toolkit#31](https://github.com/achimdehnert/gaeb-toolkit/pull/31). Kein Prod-/Publish-Schritt.

**Pipeline:** Phase 0.0 `gate_wirkung.py` → kein Gate rückfällig. Footprint `full` (Budget: 3 Finder
Sonnet + 2 Skeptiker Sonnet = 5; 3b Opus; Meta Sonnet = 7). Phase 1 inline (git fetch × 4 Repos,
`retro_transkript_kennzahlen.py`: 64 Bash · 28 Edit · 12 Read · 0 Ablehnungen · 3 Fehlerläufe).

## 1 · Executive Summary

- Alle drei Owner-Aufträge geliefert; Merge-Verdikt (nein) und Anonymisierung sind vom Skeptiker unabhängig bestätigt (risk-hub-Dependency, `apps/avb`, sdist-Build mit 0 Namenstreffern).
- Der höchste Finder-Befund (Kill-Gate-Kollision KONZ-meiki-010 ↔ Kriterium 3) wurde vom Skeptiker gekippt und von der Widerlegungsbahn **wieder aufgerichtet**: KONZ-010 §13 „kein Bau bis M1/M2", REC-6 „Code nein"; der Skeptiker hatte REC-6 falsch als Delegation gelesen.
- Überlebt hat ein Muster in **vier** Ausprägungen: **owner-gegatete Vorbedingungen stehen als autonom erfüllbare SA-4-Kriterien im Issue** (ADR-012-Migration, nl2cad-core-Release, gaeb-toolkit-PyPI, Kill-Gate KONZ-010) — ohne Blocker-Markierung. Nachgezogen per Issue-Kommentar mit ⛔ je Kriterium.
- Neu aus der Widerlegungsbahn: das Issue nannte im **PUBLIC**-Repo Kunde, Kundenvorlage und Landratsamt — die Prämissen-Falle aus platform/CLAUDE.md (#1670); Body bereinigt, Edit-Historie bleibt sichtbar.
- Zweites überlebendes Muster: zwei bewusst ausgelassene Restarbeiten (Versionsbump, Trusted Publisher) und ein „nicht verifiziert"-Punkt haben nur Board-Zeilen, kein Issue — Slug `deferred-item-no-tracking-issue` steht bei ×43 **ohne Gate**.
- Der Scope-Checkpoint-Hook feuerte, obwohl der Scope vor Ausführung gespiegelt und freigegeben war (Items 19/20) — der Hook prüft das Textmuster, nicht die Substanz; die durable Notiz wurde nachgezogen (Gate hat gefangen).

## 2 · Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Kriterium 5 in cad-hub#72 führt „ADR-012-Migration abgeschlossen" als SA-4-autonom, obwohl `docs/AGENT_HANDOVER.md` (cad-hub, Z.106/114) die Migration als „pausiert, Owner-Bestätigung zum revidierten Scope ausstehend" führt; das Board derselben Sitzung (§4) nennt sie separat als „wartet auf Owner-Go" | verfrühte Festlegung / Gate-Vermischung | hoch | SURVIVES (Skeptiker B5) | `git show origin/main:docs/AGENT_HANDOVER.md` cad-hub Z.106–114; `gh issue view 72` K5 | `owner-gate-embedded-in-sa4-criterion` (neu) |
| 2 | Kriterium 2 verlangt „konsumiert gaeb-toolkit als Paket", Reihenfolge K2 zuerst — das Paket ist nicht auf PyPI (`git tag -l` nur v0.2.0, CHANGELOG „Unreleased"); Trusted-Publisher + Tag sind Owner-Schritte, im Issue nicht als Blocker markiert | Prozesslücke | mittel | SURVIVES (kommandobelegt) | gaeb-toolkit#31 Body „Release-Trigger bleibt Owner"; `git tag -l` | `owner-gate-embedded-in-sa4-criterion` |
| 3 | Kriterium 5 verlangt „nl2cad-core ≥ 0.5.0 (Release nachziehen)" — PyPI hat 0.4.0; Publish = Gate, Auslöser im Issue nicht benannt | verfrühte Festlegung | mittel | SURVIVES (kommandobelegt) | `pip index versions nl2cad-core` → 0.4.0/0.2.0/0.1.0 | `owner-gate-embedded-in-sa4-criterion` |
| 4 | Restarbeiten „Versionsbump gaeb-toolkit" und „Trusted Publisher registrieren" nur als Board-Fließtext; `gh issue list -R achimdehnert/gaeb-toolkit --state all --search "trusted publisher OR versionsbump OR pypi release"` → nur #7 (Juni, Infra). PR-Text zählt laut House Rule nicht | Prozesslücke | mittel | SURVIVES (Skeptiker B3) | Board §7; `gh issue list` (0 Treffer) | `deferred-item-no-tracking-issue` (×43) |
| 5 | „Nicht verifiziert: Prod-Endpunkt hinter Auth?" steht nur im lokalen Board, in keinem GitHub-Artefakt | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | Board „Nicht verifiziert" Z.2; `gh issue view 72` ohne Verweis | `deferred-item-no-tracking-issue` |
| 6 | Arbeitsmodus fixiert „K2 → K4 → K3 → K5 → K1" ohne Herleitung (nur K1 „als Abschlussnachweis" begründet); Board enthält keine Ableitung | verfrühte Festlegung | niedrig | SURVIVES (Skeptiker B7) | `gh issue view 72` Arbeitsmodus; grep Board → 0 Herleitung | `unbegruendete-festlegung-im-auftrag` (neu) |
| 7 | 3 Fehlerläufe: `grep -rliE … --exclude-dir` Exit 2 (vermeidbar), Edit vor Read (Regel griff), `make test` ohne Target (bestätigt gaeb-toolkit#23) — 1 von 3 vermeidbar | Werkzeug | niedrig | SURVIVES (kommandobelegt) | `kennzahlen.json` Z.6–8 | — |
| 8 | Kriterium 3 (Stufe-3-Ausbau: OCR, Konfidenz, Eval-Harness) kollidiert mit Kill-Gate KONZ-meiki-010 / meiki-hub#476 — Skeptiker B1 kippte, Widerlegungsbahn richtete wieder auf | verfrühte Festlegung / Gate-Vermischung | mittel | SURVIVES (3b) | KONZ-010 §13 „Entscheidung heute: kein Bau … bis M1 und M2"; REC-6 „Katalog ja, Code nein"; #476 „Kill-Gate … unverändert bis 30.11.2026"; #68 ist Befund, kein Bauauftrag | `owner-gate-embedded-in-sa4-criterion` |
| 14 | cad-hub#72 (PUBLIC) nannte den Kunden (Firmenname ×3), Kundenvorlagen-Dateiname und das Landratsamt als Versandziel — Kunden-/Vertriebsinformation ohne Freigabe öffentlich; Body am 23.09. bereinigt, Edit-Historie sichtbar | Konventionsverstoß (platform/CLAUDE.md „ÖFFENTLICH") | hoch | SURVIVES (3b, NEU) | `gh repo view achimdehnert/cad-hub` → PUBLIC; Issue-Body vor Edit; nach Edit `grep -c` = 0 | `kundenname-in-public-repo-artefakt` (neu; verwandt platform#1670) |
| 15 | ausschreibungs-hub `AGENT_HANDOVER.md` Z.793/881 führt „Preisspiegel-Projekt (gaeb-Strang) auf HOLD" weiter, obwohl #313 den Strang nach cad-hub verlagert; kein Handover-Commit in einem der drei Repos | Prozesslücke | niedrig | SURVIVES (3b, NEU) | `git show origin/main:AGENT_HANDOVER.md` Z.793; `git log --since=09:00 -- '*AGENT_HANDOVER*'` → 0 | `handover-stale-vor-merge` (×21, Gate vorhanden) |
| 9 | Scope-Checkpoint erst nach den Merges verfasst (Board §8) | Prozesslücke | niedrig | REFUTED (B2) | Owner-Go 09:42:45Z mit Items 19/20 (Repo-/Sichtbarkeitswechsel benannt) vor Issue 09:43:56Z und Merges 09:54/09:57Z | — |
| 10 | 64 Bash/28 Edit/12 Read für 2 kleine Merges unverhältnismäßig | Werkzeug | niedrig | REFUTED (B4) | Regel prüft „fällt die Aufgabe ohne ihn um?", nicht Stückzahl; Pre-Flight (gitleaks, sdist-Build) im PR-Body nachweisbar; 3/64 Fehlläufe | — |
| 11 | Management-Command-Namen in K1 = Implementierungsdetail statt Zielzustand | verfrühte Festlegung | niedrig | REFUTED (B6) | `~/.claude/commands/prompt.md` Auftrag-Modus verlangt „ein Einstiegskommando, zweimal identisch" als K1 | — |
| 12 | `/tests` und `/tests/**` in sdist-exclude redundant | Anti-Pattern | niedrig | REFUTED (B8) | Empirischer Build: nur `/tests` lässt `tests/fixtures/.gitkeep`, `real/.gitkeep`, `real/README.md` im sdist — Eintrag nötig | — |
| 13 | PR-Body #31 „identisch zur Baseline" bei 14 ≠ 21 errors | Beweiskraft | mittel | REFUTED (B9) | Beide Zahlenpaare stehen offen im selben Satz mit Ursache (#23); „identisch" bezieht sich auf failed 8=8; keine verdeckte Behauptung | — |

## 3 · Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle drei Aufträge geliefert; Mangel #2/#3: zwei Kriterien hängen an ungeplanten Owner-Schritten |
| architektur_design | 4 | Merge-Verdikt und Verortung Preisspiegel skeptiker-bestätigt (#8 REFUTED, B1); sdist-Excludes empirisch nötig (#12 REFUTED) |
| code_konventionstreue | 3 | #14: Kundennamen in ein PUBLIC-Repo-Issue geschrieben (platform/CLAUDE.md-Regel); daneben #7 ein vermeidbarer grep-Fehlläufer |
| risiko_debt | 3 | #4/#5/#15: drei bewusst ausgelassene Punkte ohne Issue plus veraltetes Handover — die org-weit schwächste Dimension erneut |
| prozess_effizienz | 4 | #10 REFUTED; Finder/Skeptiker je in einer Nachricht; 3 von 64 Bash-Läufen fehlerhaft |
| entscheidungsqualitaet | 3 | #1/#2/#3/#8/#6: vier Gate-Vermischungen im Auftrag plus eine unbegründete Reihenfolge |

## 4 · Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| K5 bündelt „ADR-012-Migration abgeschlossen" mit fünf anderen Teilpunkten, obwohl das cad-hub-Handover eine gesonderte Owner-Bestätigung verlangt | Beim Prompt-Bau jede Zeile gegen `AGENT_HANDOVER.md` des Ziel-Repos abgleichen; Punkte mit dokumentiertem „wartet auf Owner-Go" als **eigenes 🟢-Item** im HALT-Board vorlegen, nicht im Kriterium verstecken | #1 |
| K2 verlangt gaeb-toolkit als Paket, Reihenfolge K2 zuerst, PyPI-Release ist Owner-Schritt | Im Issue einen Abschnitt „Vorbedingungen (Owner)" mit Blocker-Markierung je Kriterium: `K2 ⛔ bis gaeb-toolkit auf PyPI` — der SA-4-Agent startet dann mit dem ersten ungeblockten Kriterium | #2 |
| K5 friert „nl2cad-core ≥ 0.5.0" ein, obwohl PyPI 0.4.0 hat und das Board den Stand als „nicht verifiziert" führt | Vor dem Einfrieren einer Versionszahl `pip index versions` laufen lassen; ungeprüfte Zahl → Kriterium formuliert „Release liegt vor (Owner-Tag)" statt einer Zahl | #3 |
| Versionsbump + Trusted Publisher stehen nur in Board §7 | Im selben Turn `gh issue create -R achimdehnert/gaeb-toolkit` für „Release 0.3.0: Bump + Trusted Publisher" — Board-Zeile bekommt den Issue-Link | #4 |
| „Endpunkt hinter Auth?" nur unter „Nicht verifiziert" im Board | Jede „nicht verifiziert"-Zeile mit Konsequenz für den Auftrag wird Kriteriums-Notiz oder Issue-Kommentar in cad-hub#72 | #5 |
| Reihenfolge K2→K4→K3→K5→K1 ohne Begründung | Eine Zeile Herleitung je Reihenfolge-Entscheidung („K2 zuerst: Material und Toolkit liegen vor; K4 vor K3: Vorgangsmodell trägt beide") oder Reihenfolge weglassen und dem Agenten überlassen | #6 |
| `grep -rliE … --exclude-dir` Exit 2 ohne Blick auf die Ursache | Bei Exit ≠ 0 eines Suchbefehls die stderr-Zeile lesen, bevor die Treffer verwendet werden (`2>&1 \| head -1`) | #7 |
| K3 fordert OCR/Konfidenz/Eval-Harness, obwohl KONZ-010 §13 „kein Bau bis M1/M2" sagt; Out-of-Scope nahm nur Stufe 1/2 aus | Beim Prompt-Bau jedes Kriterium gegen das Kill-Gate des Nachbar-Konzepts halten: Kriterium bekommt `⛔ bis Kill-Gate positiv`, erlaubt bleibt nur repo-interne Pflege (#68, ADR-089) | #8 |
| Issue in PUBLIC-Repo mit Kunde, Vorlagenname, Landratsamt angelegt | Vor `gh issue create`/`pr create` `gh repo view --json visibility` lesen; bei PUBLIC den Body durch die Namensliste der Sitzung (Mail-Absender, Kunden, Ämter) greppen — 0 Treffer als Bedingung, sonst „Pilotkunde/Pilot-Amt" | #14 |
| Konzept auf sunset gesetzt, Handover des Repos führt den Strang weiter als HOLD | Im selben PR wie der Sunset die Handover-Zeile mitziehen (Prio-Tabelle + Fließtext), sonst hält session-ende E.3 den Zug an | #15 |

## 5 · Längsschnitt (`retro_kpis.py`, 133 Reports)

- `deferred-item-no-tracking-issue` ×43 vor dieser Retro → ×44. **GATE-PFLICHT, kein Gate vorhanden** (`ls docs/governance/gates/gates/ \| grep -iE "track\|deferr"` → 0). Vorschlag §6.
- `owner-gate-embedded-in-sa4-criterion` — neuer Slug, Vorkommen 1; verwandt mit `dod-reinterpreted-only-in-pr-body` ×6 und `merge-bypass-without-explicit-word` ×5 (dort geht es um Umdeutung nach dem Merge, hier um Einbau vor dem Start).
- `unbegruendete-festlegung-im-auftrag` — neuer Slug, Vorkommen 1.
- `kundenname-in-public-repo-artefakt` — neuer Slug, Vorkommen 1; Vorläufer ist der Realfall platform#1670 (2026-08-02, Fixture mit Klarnamen), der in platform/CLAUDE.md als Regel steht, aber nicht als Retro-Slug gezählt wurde.
- `handover-stale-vor-merge` ×21 → ×22, Gate vorhanden (Rev 2, 2026-09-16) — Einordnung in 5a.
- Memory-Abgleich: `feedback_no_unnecessary_approval_when_solution_is_known.md` existiert (MEMORY.md) — deckt die Gegenrichtung (nicht zu viel fragen), nicht den Fall „Gate im Kriterium versteckt".

### 5a · Rückfall-Prüfung (`gate_wirkung.py`)

Lauf am Anfang der Retro: **kein Gate rückfällig.** Ein überlebender Slug trägt ein bestehendes Gate: `handover-stale-vor-merge` (#15). Das Gate ist `mode: process` und greift in session-ende E.3 („Commits nach dem Handover, kein Handover-PR offen") — session-ende ist für diese Sitzung noch nicht gelaufen, das Gate hatte seinen Messpunkt also noch nicht. **Kein Rückfall, keine Änderung am Eintrag.** Offen bleibt, ob E.3 alle vier Scope-Repos prüft oder nur das cwd-Repo (platform, dessen Handover nicht betroffen ist) — billigster Check: session-ende laufen lassen und sehen, ob E.3 ausschreibungs-hub meldet; meldet es nicht, ist das ein **Ausweiten**-Fall für die nächste Retro (Quelle: Gate sieht Fremd-Repos nicht). Der Handover wurde in dieser Retro nachgezogen (M9). Beobachtung zu `scope-checkpoint-not-durably-recorded` (Gate gebaut, Rev 5): der Stop-Hook feuerte Fehlerform C, obwohl der gewachsene Scope vor Ausführung gespiegelt und freigegeben war (#9 REFUTED, B2) — die Spiegelung stand als nummerierte Zug-Items mit Repo-Namen, nicht im Wortlaut der `CHECKPOINT_PATTERNS`. Das ist **kein Rückfall** (das Gate hat die fehlende durable Notiz korrekt eingefordert, `gates_caught`), aber ein Hinweis auf Musterschärfe: billigster Check ist `gate_namensdeckung.py` gegen einen Drill mit Zug-Item-Form („🟢 … statt ausschreibungs-hub … du"). Keine Änderung am Gate in dieser Retro.

### 5b · Autonomie-Kalibrierung

- `over_ask` = 0: die einzige Vorlage (HALT auf den Zielzustand-Prompt) ist Skill-Pflicht; Items 19/20 waren echte Gates (Repo-Verortung, Publish-Weg).
- `over_act` = 0: beide Merges (Docs/Kommentare) nach grünem `ci / gate`, ohne Prod-Wirkung, nach Owner-Go; kein Publish, kein Sichtbarkeitswechsel ausgeführt.
- Kandidaten-Klasse ohne Zähler: #1 beschreibt einen Vorgriff (pauschales Go als spezifische Freigabe), aber nichts wurde ausgeführt — keine `over_act`-Zählung.

## 6 · Verankerung (Vorschläge — Verankerung entscheidet der Owner)

**memory_candidates**

```markdown
---
name: feedback_owner_gate_nicht_in_sa4_kriterium_verstecken
description: "Zielzustand-Prompt: Punkte, die laut Handover/Policy ein Owner-Wort brauchen (Publish, Migration mit ausstehender Bestätigung), werden als eigenes 🟢-Item im HALT-Board vorgelegt oder als ⛔-Vorbedingung im Issue markiert — nie als autonom erfüllbares Kriterium gebündelt"
metadata:
  type: feedback
  rule_class: B
---
Realfall 2026-09-23 (Retro 4a0457): cad-hub#72 führte „ADR-012-Migration abgeschlossen" (Handover: wartet auf Owner-Go), „nl2cad-core ≥ 0.5.0" (nicht auf PyPI) und „gaeb-toolkit als Paket" (Release = Owner-Tag) als SA-4-Kriterien.
**Why:** Ein pauschales „go" auf einen 5-Kriterien-Text ersetzt keine spezifische Freigabe, die das Ziel-Repo selbst dokumentiert; der spätere autonome Agent liest das Kriterium als Mandat.
**How to apply:** Vor dem HALT jede Kriteriumszeile gegen `AGENT_HANDOVER.md` des Ziel-Repos und gegen die fünf Gates prüfen; Treffer → eigenes 🟢-Item oder `⛔ bis <Owner-Schritt>` im Issue. Verwandt: [[feedback_no_unnecessary_approval_when_solution_is_known]].
```

```markdown
---
name: feedback_public_repo_artefakte_ohne_kundennamen
description: "Vor gh issue/pr create in einem PUBLIC-Repo (cad-hub, platform) den Text gegen die Namensliste der Sitzung greppen — Kunden, Ämter, Vorlagen-Dateinamen werden zu Pilotkunde/Pilot-Amt; Edit-Historie eines Issues bleibt öffentlich, Bereinigung ist keine Rücknahme"
metadata:
  type: feedback
  rule_class: B
  drift: true
  drift_episode: 2026-09-23-kundenname-in-cadhub-issue
---
Realfall 2026-09-23 (Retro 4a0457, #14): cad-hub#72 nannte Kunde, Kundenvorlage und Landratsamt; cad-hub ist PUBLIC wie platform. Vorläufer platform#1670.
**Why:** Die Regel steht in platform/CLAUDE.md, aber cad-hub hat keine solche Zeile — die Prämisse „Hub-Repos sind privat" trug ins falsche Repo.
**How to apply:** `gh repo view <owner>/<repo> --json visibility` vor dem ersten Schreib-Artefakt einer Sitzung; PUBLIC → Namensliste (Mail-Absender, Firmen, Ämter, Dateinamen aus Anhängen) als grep-Muster gegen jeden Body. Verwandt: [[feedback_klarname_dritter_wird_im_selben_zug_redigiert]].
```

**gate_candidate `deferred-item-no-tracking-issue`** (×44, kein Gate): Stop-Hook, der im Transkript nach „bewusst nicht drin / bleibt Owner / später / Restarbeit / Nachziehen" im letzten Assistant-Text sucht und prüft, ob im selben Turn ein `gh issue create`/`gh issue comment`/Ledger-Write lief — sonst advisory „Ausgelassenes ohne Tracking: <Zitat>". Drill: dieser Report (§7 Board-Zeile „Versionsbump" ohne Issue).

**adr_candidates:** keiner — reine Prozessbefunde, kein Architekturentscheid (adr-threshold.md).

## 7 · Maßnahmen (Action Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Vorbedingungen ⛔ je Kriterium | cad-hub | [#72 Kommentar](https://github.com/achimdehnert/cad-hub/issues/72#issuecomment-5793109056) | ✅ | — |
| M2 | Release-Issue Bump + Trusted Publisher | gaeb-toolkit | [#32](https://github.com/achimdehnert/gaeb-toolkit/issues/32) | ✅ | Owner: Publisher + Tag |
| M3 | Auth-Status Endpunkte geprüft | cad-hub | [#72 Kommentar](https://github.com/achimdehnert/cad-hub/issues/72#issuecomment-5793109056) | ✅ | K4: Login-Test, Agent |
| M4 | Reihenfolge hergeleitet | cad-hub | [#72 Kommentar](https://github.com/achimdehnert/cad-hub/issues/72#issuecomment-5793109056) | ✅ | — |
| M5 | Zwei Memory-Kandidaten übernehmen | platform | [Retro](https://github.com/achimdehnert/platform/tree/main/docs/retros) | 🟢 | Owner entscheidet |
| M6 | Gate deferred-item bauen (×44) | platform | [#2234](https://github.com/achimdehnert/platform/issues/2234) | 🟢 | Owner-Wort, dann Hook |
| M7 | Streichbahn: kein Kandidat | platform | [Retro](https://github.com/achimdehnert/platform/tree/main/docs/retros) | ✅ | siehe § Streichbahn |
| M8 | Issue-Body ohne Kundennamen | cad-hub | [#72](https://github.com/achimdehnert/cad-hub/issues/72) | ✅ | Edit-Historie: Owner |
| M9 | Handover: HOLD → nach cad-hub | ausschreibungs-hub | [Repo](https://github.com/iilgmbh/ausschreibungs-hub) | 🟡 | PR + Merge, ich |
| M10 | K3 ⛔ bis Kill-Gate | cad-hub | [#72](https://github.com/achimdehnert/cad-hub/issues/72) | ✅ | Kommentar gesetzt |

## 8 · Nicht verifiziert (Restlücken)

- **getan:** 3 Finder + 2 Skeptiker + Widerlegungsbahn (Opus) + Meta in frischem Kontext; 9 Behauptungen falsifiziert (6 gekippt, 1 davon in 3b zurückgekippt); sdist-Redundanz empirisch gebaut; Merge-Verdikt und Anonymisierung gegen `origin/main` geprüft; `gate_wirkung.py`, `retro_kpis.py`, `retro_report_check.py` gelaufen; M1–M4, M8, M10 sofort umgesetzt.
- **angenommen:** Die cad-hub-Commits des Tages (#70, #71, #74) stammen aus einer parallelen Sitzung und sind out-of-scope (Brief-Setzung, nicht per Transkript-Vergleich belegt). Dass Firmennamen (#14) keine Personendaten sind, macht die Veröffentlichung nicht zulässig, nur weniger schwer.
- **nicht verifizierbar:** Ob der Owner beim „18 go" die ADR-012-Zeile in K5 bewusst als Migrations-Freigabe gelesen hat (B5 „unbelegt", kein Artefakt) — billigster Check: Owner-Satz. Ob `TenantRLSMiddleware` anonyme Uploads abweist (Views ohne LoginRequiredMixin, anonymer POST → 403 CSRF) — billigster Check: POST mit CSRF-Token ohne Session.
- **offen geblieben:** Trusted-Publisher-Stand auf PyPI für gaeb-toolkit (kein Zugriff, gaeb-toolkit#32); ob session-ende E.3 Fremd-Repo-Handover prüft (5a); Edit-Historie von cad-hub#72 mit den Kundennamen bleibt öffentlich einsehbar — Löschung der Historie ist ein Owner-/GitHub-Support-Schritt; Skeptiker-Zahl 141 vs. Board 139 gitleaks-Commits (2 spätere Commits, unkritisch).

## Widerlegung

Phase 3b, Opus, frischer Kontext (Report-Entwurf + Brief + Kennzahlen, ohne Session-Erzählung und Finder-Prompts).

| # | Befund | Verdikt | Beleg |
|---|---|---|---|
| 1 | K5 bündelt ADR-012-Migration als SA-4-autonom | hält | cad-hub `origin/main:docs/AGENT_HANDOVER.md` Z.106 „pausiert", Z.113 „Owner-Bestätigung … stand noch aus"; #72 K5 wörtlich |
| 2 | K2: gaeb-toolkit als Paket, Release gehört dem Owner, kein Blocker | hält | `git tag -l` → nur v0.2.0; #72 K2 ohne ⛔ |
| 3 | K5 legt nl2cad-core ≥ 0.5.0 fest | hält | `pip index versions nl2cad-core` → 0.4.0, 0.2.0, 0.1.0 |
| 4 | Versionsbump + Trusted Publisher ohne Issue | hält; Report war veraltet | gaeb-toolkit#32 angelegt 10:22:26Z, nach Retro-Start (10:06Z), nicht im selben Turn wie die Auslassung — Board M2 korrigiert auf ✅ #32 |
| 5 | Offene Auth-Frage nur im Board | hält | `gh issue view 72 --json comments` → zum Prüfzeitpunkt leer |
| 6 | Reihenfolge ohne Herleitung | hält | #72 „Arbeitsmodus": nur K1 begründet |
| 7 | 1 von 3 Fehlläufen vermeidbar | hält | kennzahlen.json |
| 8 | K3 kollidiert mit Kill-Gate KONZ-meiki-010 | **Widerlegung widerlegt — Befund hält** | KONZ-010 §13 „Entscheidung heute: kein Bau … bis M1 und M2 vorliegen"; REC-6 Z.209 „Katalog ja, Code nein"; §3.1 Z.97 „Der Code selbst wird nicht übernommen". Skeptiker-Begründung „REC-6 delegiert Handler-Code an cad-hub#68" gibt das falsch wieder: #68 ist ein Befund, kein Bauauftrag. #476 nennt „Codebasis cad-hub" und im selben Text „Kill-Gate … unverändert bis 30.11.2026". #72 nimmt nur Stufe 1/2 aus, K3 baut Stufe 3 |
| 9–12 | Checkpoint, Tool-Menge, Command-Namen, sdist | Widerlegung hält | Report-Belege in sich schlüssig, kein Gegenbeleg gefunden |
| 13 | PR #31 „identisch zur Baseline" | Widerlegung hält knapp | Wort sachlich falsch, beide Zahlen offen daneben mit Ursache #23; Lesart „bezieht sich auf failed" steht nicht im Text — höchstens niedriger Beweiskraft-Befund |

**Frage 1: BESTAETIGT.** Alle sieben SURVIVES halten; Korrektur: M2 nennt jetzt #32.
**Frage 2: GEKIPPT (#8).** #8 → SURVIVES, Severity mittel (nichts ausgeführt, nur im Auftrag festgelegt). Soll-Schritt: K3 `⛔ bis Kill-Gate positiv` oder auf „#68 schließen" zuschneiden — umgesetzt als Kommentar in #72 (M10). Muster #1–#3 damit vier Ausprägungen.
**Frage 3: NEU (Sichtbarkeit).** cad-hub#72 liegt in einem PUBLIC-Repo und nannte Kunde, Kundenvorlage und Landratsamt (#14). Nebenbefund Handover: ausschreibungs-hub `AGENT_HANDOVER.md` Z.793 führt den gaeb-Strang als HOLD weiter, kein Handover-Commit nach #313 in einem der drei Repos (#15).
**Geprüft:** KONZ-meiki-010 (§3.1, REC-6, §13), meiki-hub#469/#476 wörtlich, cad-hub#72 (Body + Kommentare), gaeb-toolkit#31/#32, cad-hub-Handover Z.104–116, ausschreibungs-hub-Handover, Sichtbarkeit von 3 Repos, PyPI nl2cad-core — alles auf `origin/main` nach `fetch`.

## Self-Review

Meta-Agent (Sonnet) auf den Entwurf vor 3b: alle Checkpunkte ✅ bis auf zwei Item-Zellen über 6 Wörtern (M1, M2) — behoben. `retro_report_check.py` Exit 0 („1 Report(s) regelkonform"). `refuted_rate` nach 3b: 5/15 = 0,33, innerhalb des Bands (0,2–0,8); Längsschnitt-Verwandtschaftsangaben in §5 stützen sich auf den `retro_kpis.py`-Lauf, nicht auf Einzelbefehle.

## Streichbahn

**Kein Kandidat.** Begründung: In dieser Retro veränderte jede Phase ein Ergebnis — Phase 2.5 löste einen Finder-Widerspruch (#9), Phase 3 kippte 6 von 9 vorgelegten Behauptungen, der Stop-Hook fing den fehlenden Checkpoint-Text und erzwang das durable Artefakt. Weder „kein Leser" noch „kein Effekt", „Dublette" oder „Liegezeit" ließen sich für eine Phase, einen Melder oder ein Gate belegen. Ratsche: der Kandidat aus früheren Retros (`retro-phase1-sammler`) ist bereits gestrichen (2026-09-16).
