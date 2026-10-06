---
retro_schema: 1
date: 2026-09-15
repo_scope: [writing-hub, decks-hub]
session_id: gFYTX3
footprint: deep
findings_total: 16
findings_survived: 13
refuted_rate: 0.19
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [run-result-not-anchored, local-prod-copy-without-teardown]
recurring_findings: [accepted-plan-item-silently-dropped, deferred-item-no-tracking-issue, built-but-never-called, same-file-serial-prs, test-asserts-the-case-in-mind-not-the-harmful-one, run-result-not-anchored]
gates_caught: []
over_ask_klassen: []
over_act_klassen: []
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "Keine Phase ohne Leser oder Effekt belegbar: der Sammler lieferte drei falsche Einzelfakten, die Finder korrigierten sie — das ist die vorgesehene Arbeitsteilung, keine Dublette."
---

# Session-Retro 2026-09-15 · writing-hub + decks-hub · gFYTX3

Sitzung 2026-09-14 11:25 UTC – 2026-09-15 06:20 UTC. Artefakte: writing-hub #1148, #1151, #1155 (gemergt, je Prod-Deploy), Issues #1146 (geschlossen), #1152 (ux-review, geschlossen), #1158 (Folge, offen); decks-hub #101 (gemergt, Deploy). Prod-Datenschritt: Modulversion v9 `0af61a11` auf writing-hub-Prod angelegt, vorher Dump + Medien unter `/opt/backups/writing-hub/vor-teststrang-20260914T1756Z*`.

Footprint `deep` (Prod-Schritte; Reduktion auf `full` nicht zulässig, weil die Prod-Freigabe nur im Chat stand — kein PR-Body-Warnhinweis, keine `AskUserQuestion`). Agenten: 1 Sammler (Haiku), 3 Finder, 3 Skeptiker, 1 Widerlegung (Opus), 1 Meta (Sonnet) = 9.

## 1. Executive Summary

- Geliefert und live: Editor mit Werkzeugen und KI je Abschnitt, Modulseite mit Reitern, Decks aus der Datenbank, v9-Inhalte auf Prod, 14 Decks in decks-hub. Drei vorbestehende Fehler im Test gefunden und behoben (doppeltes Bootstrap seit 28.08., Diagramm-Text mit `opacity` im PDF abgeschnitten, Notizen überlagern volle Folien).
- Abnahme unvollständig geschlossen: #1146 wurde geschlossen, obwohl der zugesagte ux-review an der Pilot-Vorlesung nicht lief (#1) und der verlangte Prod-KI-Beleg fehlt (#2); #1158 trägt beide Lücken nicht.
- Rework am Anfang: derselbe Lösch-Fehler brauchte zwei PRs und zwei Deploys (#10) — danach Wechsel auf lokalen Teststrang mit einem Sammel-PR.
- Tech-Debt aus dem Umbau: Service `enrich_section` ohne produktiven Aufrufer und ohne Tracking (#9); Regressionstest für Bootstrap zählt nur Text (#8); kleinere Vertrags- und Konventionsmängel (#4–#7).
- Datenhygiene und Nachvollziehbarkeit: lokale Prod-Kopie läuft weiter als Container mit `trust`-Auth (#13); der Prod-Datenschritt (v9 angelegt, Sicherungspfad) steht in keinem Artefakt (#16, aus der Widerlegung).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | #1146-Nachtrag sagte ux-review an Pilot `28fb6121` und `ceb0f389` zu; #1152 testete `0e6c178e`/`b137c3c1`; #1146 trotzdem geschlossen. Mildernd: `0e6c178e` ist v9-Nachfolgerin von `ceb0f389` (gleiches Thema), für den Pilot bleibt die Lücke | fehlende Validierung | hoch | SURVIVES | `gh issue view 1146 --comments` (Nachtrag), `gh issue view 1152` Stationen 5/10; DB-Kette v7 `28fb6121` → v8 `ceb0f389` → v9 `0e6c178e` | accepted-plan-item-silently-dropped (×2; Gate zusage-ohne-verankerung unerprobt) |
| 2 | K2 von #1146 verlangt „echten KI-Lauf auf Prod (Revision `llm_*`, Modellname im Log)“; beim Schließen kein solcher Beleg, #1158 führt die Lücke nicht | fehlende Validierung | hoch | SURVIVES | `gh issue view 1146 --json body` (K2-Text); keine `llm_*`-Fundstelle in #1146/#1149/#1152/#1155; `gh issue view 1158` ohne K2 | deferred-item-no-tracking-issue (×41; Gate aufschub-anker zu-frueh) |
| 3 | PR-#1155-Body nennt „Lokal: … 2572 grün“ — durch kein Artefakt belegt (CI-Summen 4535/83/78, keine ergibt 2572) | fehlende Validierung | niedrig | kommandobelegt | `gh pr view 1155 --json body`; `gh run view 34877852792 --log` | neu: pr-body-local-number-without-artifact |
| 4 | `_ExerciseViewMixin` („Übungs-Views“) wird von 7 Views geerbt, darunter 4 Nicht-Übungs-Views — Name/Docstring nicht nachgezogen | Konventionsverstoß | niedrig | kommandobelegt | `apps/lectures/views.py:415f.`, Erben Z. 668/718/748/830 | neu |
| 5 | `nach` widersprüchlich: `add_section` wirft bei negativ, `ki_abschnitt_vorschlag` clampt still; `KopfteilEditView` nutzt `nach=-1` als undokumentierten Sentinel | fehlende Validierung | mittel | SURVIVES | `services.py:957f.` vs. `:990`; `views.py:782` | neu |
| 6 | `KopfteilEditView.post` fängt `SectionNotFoundError` aus `apply_kopfteil_edit` nicht (praktisch durch `_stand()`-404 vorab gesperrt) | fehlende Validierung | niedrig | kommandobelegt | `services.py:1021-1023`, `views.py:803-827` | neu |
| 7 | `# noqa: E402` in `llm.py:44` ohne Grund (ruff E402 ohne noqa grün, RUF100 meldet unused noqa; RUF nicht selektiert) | Werkzeug | niedrig | kommandobelegt | `ruff check --select E402,RUF100` auf Ref-Kopie | neu |
| 8 | Bootstrap doppelt geladen 28.08.–14.09. (`db40231` → `3cbca0b`), 12 Templates mit `data-bs-toggle` betroffen; Regressionstest zählt nur Text, kein UX-Test klickt Dropdown/Collapse | fehlende Validierung | mittel | SURVIVES | `git log -S"bootstrap.bundle.min.js" origin/main -- templates`; `tests/test_deck_pdf_notizen_und_diagramme.py:69-72`; `git grep "data-bs-toggle\|dropdown\|collapse" origin/main -- tests/ux` = 0 | test-asserts-the-case-in-mind-not-the-harmful-one (×7, declined platform#2234) |
| 9 | Service `enrich_section` nach Rückbau der Route ohne produktiven Aufrufer (nur Tests), kein Tracking-Artefakt | Prozesslücke | mittel | SURVIVES | `git grep -n enrich_section origin/main -- apps templates`; Commit `0b0862b`; keine offene Issue | built-but-never-called (Gate blocking) |
| 10 | #1148 behob den 500, ließ den wirkungslosen Löschen-Knopf stehen; #1151 korrigierte 50 min später (zwei Merges, zwei Deploys). Mildernd: #1148-Body nannte den Rest „bewusst“, #1151 folgte einem neuen Owner-Entscheid | verfrühte Festlegung | mittel | SURVIVES | #1151 ersetzt in `apps/lectures/services.py` (Z. 1419–1426) den `gruende`-Block, den #1148 in `delete_lehrinhalt` eingefügt hatte; überlappende Hunks in `tests/test_lectures_lehrinhalt_views.py` (#1148 Z. 63–78, #1151 Z. 76–92); #1151 ergänzt die Sichtbarkeitsregel in `module_detail.html` | same-file-serial-prs (Gate advisory) |
| 11 | Docs-only-Merge #1150 löste Prod-Deploy 17 s vor #1149 aus | Prozesslücke | hoch | REFUTED | #1150 aus fremder Session; Deploy-Job `skipped` (Run 34844833792) | — |
| 12 | Kaskade #1154 → #1156 → #1157 nach der Owner-Beschwerde | Prozesslücke | hoch | REFUTED | alle drei aus Session `01UTffus…`, themenfremd | — |
| 13 | Lokale Prod-Kopie läuft weiter: Container `writing_hub_db_kopie` (127.0.0.1:5445, `HOST_AUTH_METHOD=trust`), Dump + Medien in `~/.cache/writing-hub-prodkopie/`, kein Teardown-Schritt | Datenhygiene/Prozesslücke | hoch | SURVIVES | `docker ps`; `docker inspect … grep -c trust` = 1; `holen.sh` ohne Nach-Aufräumen; kein Handover-/Issue-Eintrag | neu: local-prod-copy-without-teardown |
| 14 | Übergabedatei `~/shared/writing-teststrang-tunnel.txt` liegt weiter (kein Secret) | Prozesslücke | niedrig | kommandobelegt | `ls -la ~/shared/writing-teststrang-tunnel.txt` | neu |
| 15 | ~54 min Stille während Deploy #1155 | Kommunikation | mittel | REFUTED | Pipeline lückenlos belegt (Build 39 min 31 s), keine Meldepflicht | — |
| 16 | Prod-Datenschritt ohne Artefakt: v9 `0af61a11` per `neue_modul_version` + `apply_human_edit` auf Prod angelegt, Sicherung `/opt/backups/writing-hub/vor-teststrang-20260914T1756Z*` — beides nur im Transkript, kein Skript im Repo, kein Issue-Kommentar, Handover zuletzt 12:26 UTC | Prozesslücke | hoch | NEU (3b) | Repo-Suche `0af61a11` und `vor-teststrang` je 0; #1146/#1152/#1155-Texte ohne Prod-Schritt; `AGENT_HANDOVER.md` letzte Änderung `868fe64` 12:26 UTC | run-result-not-anchored (×1 → ×2) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | alles live; Abnahme-Lücken #1, #2 |
| architektur_design | 4 | Deck-Erzeugung als eine Quelle (dai_decks), Service-Layer eingehalten; Mängel #5, #9 |
| code_konventionstreue | 3 | #4, #6, #7 |
| risiko_debt | 3 | #9 ungetrackt, #13 Prod-Kopie mit trust-Auth, #16 Prod-Schritt ohne Anker |
| prozess_effizienz | 3 | #10 Rework, danach ein Sammel-PR |
| entscheidungsqualitaet | 4 | #5 fragiler Sentinel, #10 enger Scope |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #1146 geschlossen mit „ux-review ohne offenen Fehler“, Pilot `28fb6121` nie getestet | Vor dem Schließen eines Auftrags-Issues jede zugesagte Abnahme-ID gegen den Review-Bericht greppen; fehlt eine, Station nachholen oder als Zeile ins Folge-Issue | #1 |
| K2 „echter KI-Lauf auf Prod“ nicht belegt, #1158 ohne K2 | Schließ-Kommentar als Tabelle K1…Kn mit Beleg-Link je Kriterium; jede Zeile ohne Beleg wandert wortgleich ins Folge-Issue | #2 |
| PR-Body nennt lokale Testzahl ohne Artefakt | Lokale Zahl im PR-Body mit Kommando und Hinweis „lokal, nicht CI“ oder weglassen und auf den CI-Lauf verlinken | #3 |
| Mixin „Übungs-Views“ von 4 fremden Views geerbt | Beim Wiederverwenden eines Mixins für eine andere Familie umbenennen (`_SchreibViewMixin`) und Docstring anpassen, im selben PR | #4 |
| `nach=-1` als Sentinel nur am Aufrufer kommentiert | Expliziten Parameter (`vorn=True`) oder Vertrag im Service-Docstring + Test für negativen Wert | #5 |
| `SectionNotFoundError` in `KopfteilEditView.post` nicht gefangen | Alle Service-Ausnahmen des Aufrufs im View spiegeln (wie in den Geschwister-Views), auch wenn vorab gesperrt | #6 |
| `noqa: E402` ohne Grund gesetzt | `ruff check` vor dem Setzen eines `noqa`; RUF100 in die Repo-Ruff-Auswahl aufnehmen | #7 |
| Bootstrap-Doppelung 17 Tage unentdeckt, Test zählt Text | UX-Test klickt ein `data-bs-toggle`-Element und prüft `aria-expanded=true` | #8 |
| Service `enrich_section` ohne Aufrufer, ungetrackt | Beim Rückbau einer Route im selben PR entweder Service entfernen (Tests auf den neuen Pfad umziehen) oder Tracking-Issue anlegen | #9 |
| #1148 ließ wirkungslosen Knopf stehen, #1151 folgte | Bei einem 500-Fix die UI-Folge (Knopf, der nie wirken kann) im selben PR mitlösen oder als offene Frage vor dem Merge vorlegen | #10 |
| Prod-Kopie mit trust-Container läuft nach Arbeitsende | Kopierskript liefert ein Gegenstück `aufraeumen.sh`; Session-Ende-Checkliste fragt nach lokalen Prod-Kopien | #13 |
| Übergabedatei in `~/shared/` liegen gelassen | Schleusen-Dateien beim Abschluss des Strangs löschen oder in `/session-ende` aufräumen | #14 |
| v9 auf Prod angelegt, Sicherung erstellt — nur im Transkript | Jeder Prod-Datenschritt bekommt im selben Zug einen Kommentar am Auftrags-Issue: Objekt-ID, Sicherungspfad, ausgeführtes Skript (oder Skript im Repo) | #16 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (platform, origin/main 2026-09-15): 45 Slugs ≥2. Zuordnung dieser Retro (Zähler vor dieser Retro; `oqu6Z6` ist in einzelnen Zählern doppelt enthalten):

| Slug | Zähler | Gate in Registry | Einordnung |
|---|---|---|---|
| accepted-plan-item-silently-dropped | ×2 | zusage-ohne-verankerung — Klasse `restarbeit` läuft noch nicht (wartet auf platform#2214), `urteil: unerprobt` | kein Rückfall; Datenpunkt an platform#2214 (#1) |
| deferred-item-no-tracking-issue | ×41 | aufschub-anker — umgebaut 2026-09-10, `urteil: zu-frueh` | kein Rückfall (Ehrlichkeits-Sperre), beobachten (#2) |
| built-but-never-called | ×5 | built-but-never-called — `urteil: wirksam`, Prüfbereich nur ausschreibungs-hub + platform `tools/` | Rückfall außerhalb des Prüfbereichs (#9) |
| same-file-serial-prs | ×14 | serielle-prs-auf-derselben-datei — revidiert 2026-09-14, `zu-frueh` | beobachten (#10) |
| test-asserts-the-case-in-mind-not-the-harmful-one | ×7 | declined 2026-08-23 (platform#2234: kein mechanisches Signal, Positivkontrolle vor dem Verdrahten) | kein Rückfall, bewusst ohne Gate; #8 bleibt Befund (#8) |
| run-result-not-anchored | ×1 → ×2 | keins | GATE-PFLICHT neu (#16) |

Memory-Abgleich: `drift-ui-action-suggests-effect-none.md` existiert und beschreibt die Klasse von #10. Hinweis: `gate_wirkung.py` wertet `covers` nicht aus — die Slug↔Gate-Zuordnung oben ist Zuordnung der Retro, nicht Messung des Werkzeugs.

### 5a. Rückfall-Prüfung

`gate_wirkung.py` (Phase 0.0): kein Gate rückfällig vor dieser Retro. Einzige tragfähige Rückfall-Konsequenz aus dieser Retro:

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| built-but-never-called | 1 (#9) | Quelle: writing-hub liegt nicht im Prüfbereich (nur ausschreibungs-hub + platform `tools/`) | ausweiten: writing-hub `apps/` in den Prüfbereich (Eintrag `revised`, neue `positivkontrolle` mit `services.enrich_section`) |

`zusage-ohne-verankerung` (unerprobt), `aufschub-anker` und `serielle-prs-auf-derselben-datei` (zu-frueh) sind kein Rückfall — gekippt in der Widerlegung.

### 5b. Autonomie-Kalibrierung

`over_ask`: kein artefaktbelegter Fall. `over_act`: kein artefaktbelegter Fall — #1146 erteilt SA-4 inkl. Merge für kriterienbezogene PRs; decks-hub-Deploy im Auftrag vorab erlaubt (Finder Prozess, Nullbefund 7).

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**

```markdown
---
name: auftrag-schliessen-kriterium-fuer-kriterium
description: Auftrags-Issue nur mit Kriterium→Beleg-Tabelle schließen; jede Zeile ohne Beleg wortgleich ins Folge-Issue
metadata:
  type: feedback
---
Ein Issue mit Akzeptanzkriterien wird nicht mit „live / ux-review ohne Fehler“ geschlossen, sondern mit einer Tabelle K1…Kn → Beleg-Link. Zugesagte Abnahme-Objekte (IDs) werden gegen den Review-Bericht gegrept.
**Why:** #1146 geschlossen, obwohl Pilot-ux-review und Prod-KI-Beleg (K2) fehlten; #1158 trug beides nicht (Retro gFYTX3 #1, #2).
**How to apply:** vor `gh issue close` Kriterientext Zeile für Zeile abgleichen; fehlende Zeilen ins Folge-Issue.
```

```markdown
---
name: lokale-prodkopie-aufraeumen
description: Lokale Prod-Datenkopie (Container + Dump) hat ein Aufräumskript und wird am Strangende gelöscht
metadata:
  type: feedback
---
Wer Prod-Daten lokal kopiert, legt im selben Zug das Gegenstück zum Aufräumen an und löscht Container, Volume und Dump, sobald der Strang live ist.
**Why:** `writing_hub_db_kopie` (trust-Auth) und `~/.cache/writing-hub-prodkopie/` lagen nach Arbeitsende weiter (Retro gFYTX3 #13).
**How to apply:** `holen.sh` + `aufraeumen.sh`; `/session-ende` fragt nach lokalen Prod-Kopien.
```

**adr_candidates:** keine — die Befunde betreffen Ablauf und Tests, keine Architekturentscheidung.

## 7. Maßnahmen

**Stand (in dieser Retro erledigt)**

- **[M2+M9]** ✅ K2-Lücke, Pilot-Lücke und Prod-Datenschritt v9 an #1158 — https://github.com/achimdehnert/writing-hub/issues/1158#issuecomment-5676061231
- **[M6]** ✅ #1 als Datenpunkt Klasse `restarbeit` — https://github.com/achimdehnert/platform/issues/2214#issuecomment-5676063894
- **[M3+M4+M5]** ✅ ein Folge-Issue: toter Service, Dropdown-UX-Test, Kleinmängel — https://github.com/achimdehnert/writing-hub/issues/1160

**Zug**

- **[M1]** 🔵 Prod-Kopie (Container, Dump, Medien) und Schleusendatei löschen, in /session-ende — file:///home/devuser/.cache/writing-hub-prodkopie
- **[M7]** 🟢 Gate built-but-never-called auf writing-hub `apps/` ausweiten — file:///home/devuser/github/platform/docs/governance/gate-registry.json
- **[M8]** 🟢 Memory-Kandidaten aus §6 freigeben — file:///home/devuser/.claude/projects/-home-devuser-github-writing-hub/memory/MEMORY.md
- **[M10]** ✅ Streichbahn: keiner (Begründung §Streichbahn) — file:///home/devuser/github/platform/docs/retros/session-retro-2026-09-15-writing-hub-gFYTX3.md

## 8. Nicht verifiziert (Restlücken)

- „2572 grün“ (#3): lokal gemessene Zahl nur in Transkript belegt, nicht als Artefakt — billigster Check: Befehl im PR-Body nennen.
- Ob `apply_kopfteil_edit`-Fehlerpfad (#6) je erreichbar ist — billigster Check: Test mit gelöschter Orientierung zwischen GET und POST.
- Ob `zusage-ohne-verankerung` die Klasse von #1 überhaupt sehen kann — billigster Check: Gate-Modul gegen den #1146-Nachtrag laufen lassen.
- Transkript-Kennzahlen (24 Fehlerläufe, 41 Reminder) nur als Skript-Ausgabe übernommen, nicht einzeln bewertet.

## Widerlegung

Opus, frischer Kontext, mit gh/git. Ergebnis `2 gekippt, 1 neu`.

- **BESTAETIGT:** #1, #2, #5, #8, #9, #10 (Beleg getauscht: #1148 berührte `module_detail.html` nicht; tragfähig ist die Überlappung in `services.py` und im Test), #13, #14. REFUTED #11, #12 zu Recht verworfen; #15 nicht erneut geprüft.
- **GEKIPPT (a):** §5a `zusage-ohne-verankerung` — Klasse `restarbeit` läuft noch nicht (platform#2214 offen), `urteil: unerprobt` ⇒ kein Rückfall, Konsequenz „nachschärfen“ war falsch.
- **GEKIPPT (b):** §5a `aufschub-anker` — umgebaut 2026-09-10, `urteil: zu-frueh` ⇒ Ehrlichkeits-Sperre, „beobachten“.
- **NEU:** #16 Prod-Datenschritt ohne Artefakt (`run-result-not-anchored` ×2).
- Präzisierung: `accepted-plan-item-silently-dropped` exakt ×2; einzelne Zähler enthalten `oqu6Z6` doppelt; `built-but-never-called`-Gate prüft writing-hub nicht.
- Nicht erneut geprüft: #3, #4, #6, #7, #15.

## Streichbahn

Frage: welche Phase / welcher Melder / welche Skill-Sektion / welches Gate gehört weg? Antwort (b): **keiner**, weil keine Phase dieser Retro ohne Leser oder Effekt belegbar ist — der Sammler (Phase 1) lieferte drei falsche Einzelfakten (Befundzahl in #1152, „Freigabe nachträglich“, Schließzeit relativ zu einem fremden Commit), die Finder korrigierten; die Widerlegung kippte zwei Rückfall-Zeilen und fand einen Befund, den kein Finder hatte.

## Self-Review

Meta-Agent (Sonnet, nur Report gegen Skill): Belegpflicht (Stichprobe #2, #3, #9 unabhängig bestätigt), Scorecard, Invariante 13 = 13 und Frontmatter sauber. Korrigiert nach Meta: §5-Zeile `test-asserts-…` (declined platform#2234 statt „GATE-PFLICHT ohne Gate“), Links im Action-Board. Numerisch: `refuted_rate` 0,19 = echte Falsifikationsquote 3/16 = 0,19, knapp unter dem 0,2-Band — als Einzelwert kein Alarm (Längsschnitt 0,06–0,41), die Widerlegung kippte zusätzlich 2 Einordnungen.

**getan:** 9 Agenten (Sammler, 3 Finder, 3 Skeptiker, Widerlegung, Meta), 16 Befunde, 13 halten; K2-/Pilot-Lücke und Prod-Datenschritt an #1158 verankert; Datenpunkt an platform#2214; ein Folge-Issue #1160. · **angenommen:** Transkript-Kennzahlen aus dem Skript ohne Einzelprüfung. · **nicht verifizierbar:** „2572 grün“ nur lokal (Transkript). · **offen geblieben:** M1 Aufräumen der Prod-Kopie (/session-ende), M7 Gate-Ausweitung und M8 Memory (Owner).
