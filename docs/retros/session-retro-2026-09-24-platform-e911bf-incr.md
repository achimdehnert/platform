---
retro_schema: 1
date: 2026-09-24
repo_scope: [platform]
session_id: e911bf-incr
footprint: full
footprint_reduction_reason: "deep → full: (a) Prod-Schritt Restore-Drill per Owner-Wort „10 go“ freigegeben (#3475 Kommentar), (b) voll rückbaubar — Wegwerf-Container per trap entfernt, keine Migration, (c) Befund-Schätzung ≤10 (Ist 9)"
findings_total: 10
findings_survived: 5
refuted_rate: 0.5
phase3_refuted: 5
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [korrektur-nur-im-chat]
recurring_findings: [worktree-midsession-accumulation, tracking-doc-stale-after-new-occurrence, claim-before-cheapest-check]
gates_caught: [claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 0 neu"
streichkandidaten: []
streich_begruendung: Jede Bahn wirkte — der Skeptiker widerlegte 4 von 5 Bewertungsbefunden per Direktmessung, die Widerlegungsbahn kippte einen SURVIVES mit Subagent-Transkript-Beleg; keine Phase lief ohne Effekt.
---

# Session-Retro 2026-09-24 — platform (Sitzung e911bf49, Increment)

Increment zur Retro [#3543](https://github.com/achimdehnert/platform/pull/3543) derselben Sitzung,
Fenster 2026-09-24 17:00Z bis 2026-09-25 05:45Z. In Scope sind nur die neuen Artefakte:
Nachtrags-Fragment #3544, die drei Gate-PRs #3546/#3547/#3548 (Owner-Wort „8 9 go“), die
Hook-Verteilung und der Restore-Drill #3551 („18 go 10 go“), die K4-/E7-Nachweise („21 22 go“)
und Issue #3549. Parent-Befunde werden nicht neu verhandelt; ihre Slugs zählen als Vorkommen 1.
Parallelsitzungen desselben Tages (#3545, #3552, #3553, #3557) sind ausgeschlossen.

**Agenten:** 3 Finder (sonnet) · 1 Skeptiker (sonnet, gebündelt, nur die 5 Bewertungsbefunde) ·
1 Widerlegungsbahn (opus) · 1 Meta (sonnet) = 6, im Budget `full`. Laut Nutzungsmeldung der
Läufe 88k–123k Token je Finder/Skeptiker.

## 1. Executive Summary

- Alle Owner-Freigaben des Increments sind geliefert: drei Gate-Revisionen gemergt, Hooks
  verteilt, Restore-Drill gegen die Storage Box bestanden (352 = 352 Zeilen, 30 s), K4 und
  der erste Box-Snapshot belegt.
- Der Push-Hook schützt trotzdem noch nicht: Nach dem Owner-Wort „17 done“ fand sich die
  Registrierung in keiner Konfigurationsdatei. Die Korrektur stand nur im Chat, nicht im Issue.
- Der Evidenz-Hook hat zweimal eine vorschnelle Meldung gefangen („alle drei PRs grün“,
  „Aufräumlauf fehlt“); beide wurden binnen Minuten korrigiert.
- Die Sitzung hinterließ vier Worktrees gemergter PRs und ließ die Fortschritts-Tabelle in
  ADR-289 auf dem Mittagsstand, obwohl K4 und E7 Teil 1 im Issue belegt sind.
- Vier Bewertungsvorwürfe hielten nicht: Rev 8 erzeugt kein Rauschen für bereits gedeckte
  Repos, E.3-❌ ist begründet, der CODEOWNERS-Perimeter war erfüllt, und Subagenten tragen
  dieselbe Sitzungs-ID wie die Hauptsitzung (direkt gemessen).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Vier Worktrees gemergter Sitzungs-PRs blieben liegen; kein `reap` im Fenster | Prozesslücke | mittel | SURVIVES | `ls ~/.repo-session/worktrees/platform \| grep 2026-09-2` → 9 Worktrees, darunter die zu #3546/#3547/#3548/#3551 (gemergt 22:26–22:31Z); `gate_wirkung.py`: `worktree-midsession-accumulation … RUECKFAELLIG 2026-09-24` | Gate `worktree-midsession-accumulation` rückfällig (×9) |
| 2 | Board-Meldung vor dem billigsten Check geschrieben, zweimal: „alle drei PRs grün“ (20:36Z, aus Subagent-Berichten) und „Aufräumlauf fehlt“ (05:42Z) | fehlende Validierung | niedrig | SURVIVES | Stop-Hook 20:36:51Z → Selbstcheck `#3548 OPEN BLOCKED … offen=2`; Stop-Hook 05:42:36Z → `forget` läuft nächtlich auf beiden Hosts, nur `prune` fehlt ([#3475-Kommentar](https://github.com/achimdehnert/platform/issues/3475#issuecomment-5827451396)) | Gate `claim-before-cheapest-check` hat beide Male gefangen |
| 3 | Push-Hook nach „17 done“ nicht registriert; die Korrektur ging nur in den Chat, nicht in #2234 oder die Gate-Registry | Kommunikation | mittel | SURVIVES | `grep -l block_push_to_merged_branch ~/.claude/settings*.json` → 0; derselbe grep trifft `~/.claude/hooks/.cc-skill-dist-manifest.json` (Positivkontrolle); letzter #2234-Kommentar 22:28Z; Registry `zustand: ohne-traeger` | neu (`korrektur-nur-im-chat`) |
| 4 | ADR-289 §5 (E6/E7) nicht nachgeführt, obwohl der Drill (#3551) und E7 Teil 1 in #3475 belegt wurden | Prozesslücke | mittel | SURVIVES | letzter ADR-289-Commit `7779d5e9` 2026-09-24T12:57Z; Zeilen 477–478 zeigen E6/E7 „⬜“; #3551 gemergt 22:30Z, #3475-Kommentar 05:42Z (E7 Teil 1 ✅). Die E5-Zeile nennt „prod 0 / prod-b 0 UNGEDECKT“ bereits korrekt — Finder-Detail dort zu breit | `tracking-doc-stale-after-new-occurrence` (×9) |
| 5 | Rev 8 (#3546) strich die Schwelle 2 ersatzlos und erzeugt Fehlalarm-Rauschen | verfrühte Festlegung | mittel | REFUTED | Registry `mode: advisory`; gedeckt ist jedes beim Checkpoint beschriebene oder genannte Repo (Alltagsfall platform gedeckt); 5 gedrillte Fälle inkl. Gegenproben | — |
| 6 | E.3 stuft den neuen Fall (PRs nach dem jüngsten Fragment) an nur einem Realfall als ❌ ein | verfrühte Festlegung | niedrig | REFUTED | `handover-stale-vor-merge` ×24 über Retros; PR-Body begründet ❌ als dieselbe Fehlform wie das fehlende Fragment, Heilung `fragments.py neu`; Unmessbares → SKIP | — |
| 7 | #3548 änderte `.windsurf/` ohne die volle CODEOWNERS-Zwei-Augen-Prüfung | Prozesslücke | mittel | REFUTED | CODEOWNERS-Zeile mit mehreren Ownern verlangt EIN Approval aus der Menge; IIL-Lotse (gelistet) approved; Ruleset `require_code_owner_review: true`, erfüllt | — |
| 8 | Subagenten sehen eine andere `CLAUDE_CODE_SESSION_ID`; ihre PRs fallen aus E.3/E.10 | Wissenslücke | mittel | REFUTED | Direktmessung im Subagenten: `e911bf49 child=1` — gleiche ID, nur Flag `CLAUDE_CODE_CHILD_SESSION`; `tools/sitzungs_branches.py` matcht die ersten 8 Zeichen | — |
| 9 | Ein Subagent löschte bei der Diagnose eine Zeile aus dem Gate-Treffer-Journal und verfälschte damit die Messgrundlage | Werkzeug | niedrig | REFUTED (3b) | Subagent-Transkript: Hook-Start mit `session_id: "diag-rev8-…"` 20:06:35Z schrieb Zeile 1736; `grep -c '"diag-'` = 1; Entfernen nur dieser Zeile per `os.replace` 20:06:50Z — eigenes Testdatum bereinigt, Messung wiederhergestellt | — |
| 10 | Ein Diagnoselauf eines Hooks schreibt in das Live-Journal `gate-hits.jsonl`, weil `gate_hits` keinen Diagnose- oder Scratch-Schalter hat | Werkzeug | niedrig | SURVIVES (aus 3b) | `tools/gate_wirkung.py:375` liest das Journal als Messgrundlage; Diagnose-Nachspiel 20:06:35Z erzeugte dort einen Treffer, der per Hand entfernt werden musste | neu |

Positiv, ohne Befund-Nummer: Die Klassifizierer-Ablehnung „Merge Without Review“ (20:16Z) wurde
nicht umgangen; der Owner mergte #3546–#3548 selbst.

## 3. Scorecard

| Dimension | Score | Verankert an |
|---|---|---|
| zielerreichung | 4 | alle Go-Items geliefert; Hook wirkt noch nicht (#3), E7 Teil 2 an Owner-Gate |
| architektur_design | 4 | drei Design-Vorwürfe widerlegt (#5, #6, #8) |
| code_konventionstreue | 4 | keine Commit-, Testnamen- oder Heredoc-Verstöße; Werkzeug-Lücke Diagnose-Journal (#10) |
| risiko_debt | 3 | liegende Worktrees (#1), veraltete ADR-Tabelle (#4), ungeschützter Push (#3) |
| prozess_effizienz | 3 | zwei vorschnelle Meldungen (#2), Korrektur nur im Chat (#3) |
| entscheidungsqualitaet | 4 | Ablehnung nicht umgangen, Security-Config (E7 Teil 2) an Owner gegeben; #7 widerlegt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Worktrees von #3546–#3551 blieben nach dem Merge auf Platte | Nach jedem bestätigten Merge eines eigenen PRs `repo-session.sh reap` im selben Zug; strukturell: Stop-Hook räumt gemergte, saubere Worktrees mit eigenem `claude_session` | #1 |
| „Alle drei PRs grün“ aus Subagent-Berichten übernommen | Subagent-Status vor jeder Board-Zeile per `gh pr view --json state,mergeStateStatus,statusCheckRollup` selbst ziehen | #2 |
| „Hook nicht registriert“ schon um 22:28Z selbst gemessen und um 05:38Z erneut — beide Male nur im Chat | Bei jeder Übergabe „dein Zug“ den gemessenen Stand im selben Zug ins Tracking-Issue (hier #2234 um 22:31Z); jede Korrektur einer Owner-Aussage ebenso | #3 |
| K4/E7-Fortschritt nur in #3475, ADR-Tabelle blieb stehen | Beim Abhaken eines K-/E-Kriteriums im Issue dieselbe Zeile im ADR-§5 per PR nachziehen | #4 |
| Diagnose-Nachspiel eines Hooks schrieb ins Live-Journal, Bereinigung per Hand | `gate_hits` bekommt einen Journalpfad-Schalter (z. B. `GATE_HITS_FILE`) für Diagnosen auf das Scratchpad | #10 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand 2026-09-25, nach `git fetch`):

| Slug | Zähler | Status |
|---|---|---|
| `claim-before-cheapest-check` | ×94 | GATE-PFLICHT, Gate existiert und fing heute zweimal (#2) |
| `worktree-midsession-accumulation` | ×9 | GATE-PFLICHT, Gate existiert, `gate_wirkung.py`: RUECKFAELLIG |
| `tracking-doc-stale-after-new-occurrence` | ×9 | GATE-PFLICHT; `covers`-Eintrag im Gate `aufschub-anker` |
| `push-to-merged-branch-silently-lost` | ×1 | Gate seit #3547 gebaut, `zustand: ohne-traeger` bis zur Registrierung (#3) |
| `korrektur-nur-im-chat` | neu | Kandidat |

Memory-Abgleich: `feedback_push_auf_gemergten_branch_geht_verloren.md` existiert (Index
`reference_github_ci_merge_index.md`); zu #3 und #10 gibt es keine Memory-Datei.

Befund #1 wurde erst durch diese Retro geheilt (Worktrees geräumt 2026-09-25 05:58Z); im
Sitzungsfenster selbst lief kein `reap`.

### 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` (Phase 0.0) meldete 7 Gates RUECKFAELLIG. Sechs davon hat die
Parent-Retro behandelt (R5/R6 dort). Neu im Increment:

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| `worktree-midsession-accumulation` | ≥2, zuletzt 2026-09-24 (#1) | Quelle, zu spät: der Reaper läuft beim Sitzungsstart und auf Zuruf, nicht nach dem Merge in einer laufenden Sitzung | **umbauen**: Räumen nach bestätigtem Merge (Stop-Hook oder `hygiene_melder`), abgegrenzt über das neue Lease-Feld `claude_session` aus #3548 |
| `aufschub-anker` (deckt `tracking-doc-stale-after-new-occurrence`) | heute +1 (#4) | Quelle: das Gate liest Aufschub-Formulierungen in PR-Texten; eine nicht nachgeführte ADR-Tabelle enthält keine | **herabstufen der Deckungsaussage**: `covers`-Eintrag streichen (Gate behauptet mehr als es prüft) und den Slug als eigenen Kandidaten führen |
| `claim-before-cheapest-check` | 3 nach Bau laut Bilanz; verwandt `gate-claim-before-cheapest-check-wirkungslos` ×3 | Quelle, zu spät: der Stop-Hook fängt die Aussage erst, nachdem der Owner sie gelesen hat; Fall 1 von #2 kam aus ungeprüft weitergereichten Subagent-Berichten | **umbauen**: zusätzlicher Prüfpunkt beim Weiterreichen — Board-Zeilen mit PR-/CI-Status aus Subagent-Berichten verlangen im selben Zug einen `gh pr view`-Lauf, sonst Meldung |

### 5b. Autonomie-Kalibrierung

- `over_act`: keins. Der Prod-Schritt (Restore-Drill) lief auf „10 go“; die Security-Config
  (ZFS-Sichtbarkeit) und der Prune-Cron gingen als Entscheid an den Owner.
- `over_ask`: keins belegt. Alle Owner-Züge waren Merge nach Klassifizierer-Ablehnung,
  CODEOWNERS-Review, eigene Konfiguration oder Security-Config.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates** (kopierfertig):

```markdown
---
name: korrektur-einer-owner-aussage-gehoert-ins-issue
description: Widerlegt ein Check eine Owner-Aussage („done“), kommt die Korrektur im selben Zug ins Tracking-Issue, nicht nur in den Chat
metadata:
  type: feedback
---
Realfall 2026-09-24/25 (Retro e911bf-incr #3): Owner „17 done“, grep fand den Hook in keiner Konfiguration, Korrektur stand nur im Chat.
**Why:** Chat überlebt den Kontext nicht; das Gate blieb `ohne-traeger`, ohne dass #2234 es zeigte.
**How to apply:** Korrektur + Beleg-Kommando als Issue-Kommentar, Registry-Notiz im selben Zug.
```

```markdown
---
name: diagnose-nie-gegen-live-gate-journal
description: Hook-Diagnosen schreiben in ein Kopie-Journal; das Live-Journal gate-hits.jsonl wird nie editiert
metadata:
  type: feedback
---
Realfall Retro e911bf-incr #10: Nachspiel eines Alt-Transkripts schrieb einen Treffer ins Live-Journal; der Subagent entfernte genau diese markierte Zeile wieder.
**Why:** `gate_wirkung.py` misst daraus die Gate-Wirkung; Handbereinigung ist fehleranfällig.
**How to apply:** Diagnose-Läufe mit markierter `session_id` und umgelenktem Journalpfad fahren.
```

**adr_candidates**: keine.

## 7. Maßnahmen

- **[I1]** ✅ Vier gemergte Worktrees per `repo-session.sh end` geräumt (2026-09-25) · platform — https://github.com/achimdehnert/platform/issues/2234
- **[I2]** ✅ Hook-Korrektur mit Recheck in #2234 · platform — https://github.com/achimdehnert/platform/issues/2234#issuecomment-5827597324
- **[I3]** 🟡 ADR-289 §5 E6/E7 nachziehen · platform · Merge nach CI — https://github.com/achimdehnert/platform/pull/3560
- **[I4]** 🟢 Push-Hook registrieren · platform · du — https://github.com/achimdehnert/platform/pull/3547
- **[I5]** 🟢 Gate-Umbau Worktree-Räumen nach Merge freigeben · platform · du — https://github.com/achimdehnert/platform/issues/2234
- **[I6]** 🟢 `covers`-Eintrag im Anker-Gate streichen · platform · du — https://github.com/achimdehnert/platform/issues/2234
- **[I7]** 🔵 Diagnose-Journalpfad umlenkbar machen · platform · Umsetzung nach Go — https://github.com/achimdehnert/platform/issues/2234
- **[I8]** 🟢 Evidenz-Gate um Prüfpunkt beim Weiterreichen erweitern · platform · du — https://github.com/achimdehnert/platform/issues/2234

## 8. Nicht verifiziert (Restlücken)

- **Getan:** Wirkungsbilanz zuerst, Artefaktliste über PR-Nummern und Branch-Namen der Sitzung
  (Parallelsitzungen ausgeschlossen), Kennzahlen per Skript (Selbsttest grün), 3 Finder in einer
  Nachricht, 1 Skeptiker auf die 5 Bewertungsbefunde, Längsschnitt, Widerlegungsbahn, Meta-Prüfung.
- **Angenommen:** Die Zeitpunkte der Chat-Meldungen zu #3 (22:28Z, 05:38Z) stammen aus dem
  Transkript-Abgleich der Widerlegungsbahn, nicht aus einem eigenen Lauf.
- **Nicht verifizierbar:** Ob die nächtlichen `restic forget`-Läufe auf der Box gelingen — das
  Skript loggt Fehlschläge und läuft weiter. Billigster Check: `grep -n forget
  /var/log/offsite-backup.log | tail -3` auf beiden Hosts.
- **Offen geblieben:** Hook-Registrierung (I4), E7 Teil 2 und Prune-Cron (Owner-Entscheide in
  #3475), ADR-289 E6 Cross-Host-Drill, Gate-Umbau Worktree (I5).

## Widerlegung

Ein Opus-Subagent mit frischem Kontext, nur Entwurf, Artefaktliste und Transkripte (Haupt- und
Subagent-Sitzungen), `git fetch` vor jedem Lesen. Ergebnis `1 gekippt, 0 neu`. Die Kippung von
#9 ist im Frontmatter unter `phase3_refuted` mitgezählt (4 Skeptiker + 1 Widerlegungsbahn),
damit `findings_survived + phase3_refuted + pre_refuted = findings_total` aufgeht.

| Befund | Verdikt | Beleg |
|---|---|---|
| #1 | BESTAETIGT | Worktrees lagen 22:31Z bis nach Fensterende; geräumt erst durch die Retro 05:58Z |
| #2 | BESTAETIGT | kein Gegenbeleg; zweite Meldung in #3475 präzisiert |
| #3 | BESTAETIGT | Stand „nicht registriert“ schon 22:28Z gemessen, nur im Chat; #2234-Kommentar erst 05:58Z |
| #4 | BESTAETIGT | letzter ADR-289-Commit `7779d5e9` 12:57Z; K4/E7-Kommentare liegen später |
| #9 | **GEKIPPT** | Subagent-Transkript: nur die eigene, als `diag-rev8-` markierte Zeile entfernt; neu gefasst als #10 |
| #5–#8 (REFUTED) | BESTAETIGT | kein Gegenbeleg; bei #7 kam das Approval nicht aus der Sitzung |
| Dimension | kein NEU | geprüft: Drill-Zeitpunkt und Last auf Prod, `--allow-live` mit Backup, Secret-Werte in Ausgaben, neue Infra-Details im öffentlichen Repo — alle sauber oder von #3542 gedeckt |

Randnotiz der Bahn, ohne Befund-Nummer: Das Drill-Protokoll trägt im Kopf „#2284 K4“, zitiert
wird es als K5 aus #3475; der Kommentar im Offsite-Skript zu „append-only“ ist veraltet. Beides
gehört zu `tracking-doc-stale-after-new-occurrence` (#4).

## Streichbahn

Kein Streichkandidat. Der Skeptiker widerlegte 4 von 5 Bewertungsbefunden, einen davon per
Direktmessung, die nur ein Subagent liefern konnte (#8). Die Widerlegungsbahn kippte einen
SURVIVES mit Beleg aus einem Subagent-Transkript, das der Hauptsitzung nicht vorlag (#9).
Keine Bahn lief ohne Effekt.
