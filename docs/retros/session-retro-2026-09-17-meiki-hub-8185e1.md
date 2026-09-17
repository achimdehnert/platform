---
retro_schema: 1
date: 2026-09-17
repo_scope: [meiki-hub, schreib-hub, post-hub]
session_id: 8185e1
footprint: deep
findings_total: 15
findings_survived: 10
refuted_rate: 0.27
phase3_refuted: 4   # #3 #4 #6 #7 vom Phase-3-Skeptiker; #6 hinterliess den engen Rest #14; #12 erst in 3b gekippt, nicht mitgezaehlt (steht in widerlegung)
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [squash-message-inherits-wip-commit, silent-fallback-value-instead-of-hard-fail, contract-ssot-stale-after-implementation]
recurring_findings: [check-ohne-positivkontrolle, test-asserts-the-case-in-mind-not-the-harmful-one, gate-modul-prueft-weniger-als-sein-name, dod-reinterpreted-only-in-pr-body, deferred-item-no-tracking-issue, scope-checkpoint-not-durably-recorded, gruener-lauf-ohne-wirkung]
gates_caught: [scope-checkpoint-not-durably-recorded]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 1 neu"
streichkandidaten: [session-start-0-7-7-gate-wirkung-ohne-zug]
---

# Session-Retro 2026-09-17 — meiki-hub + schreib-hub + post-hub (8185e1)

## 1. Executive Summary
- Geliefert: Handover-Prio 5 auf offenen Anker (meiki-hub#435 → post-hub#21), schreib-hub auf Kern 0.11 + Vorlagen 0.11 (schreib-hub#21), Analyse der ocos-KommSafe-Quelle mit Owner-Entscheid „Weg B" (post-hub#21), KommSafe-Leser-Gerüst mit Partnerprofil-Daten und Migration (post-hub#22/#23); zwei Owner-Mails (Zeiner, Seitz) entworfen und versandt. Kein Prod-Schritt.
- Schwerster Befund: der Erst-Commit des Lesers übernahm die Parser-Ausgabe ungefiltert (`raw.update`) — Datenschutz-Vektor, obwohl Ziel 3 die Projektion verlangte; die Hauptsitzung fing es vor dem Merge (#1). Das ist derselbe Musterfehler wie am Vortag (Melder ohne Positivkontrolle).
- Zwei Dinge liegen dauerhaft schief: die WIP-Nachricht „ungeprueft" als Squash-Commit auf schreib-hub `main` (#2) und der Vertrag, der Variante b weiter als „nicht spezifiziert" führt, ohne Vermerk vom 17.09. (#5).
- Vier Finder-Befunde fielen der Falsifikation: Merge ohne Merge-Wort (W0-Repo), Merge trotz Postgres-Lücke (Diff berührt keine Tenancy), Restarbeit „ungetrackt" (2 von 3 waren getrackt/Bestand), frist-hub „nicht geliefert" (PR #174 kam 5 min nach Retro-Aufruf). Die Widerlegungsbahn kippte einen fünften (Pins ohne Obergrenze = Repo-Konvention) und fand einen neuen: alle drei Session-Branches lagen noch auf origin, weil `--delete-branch` am Worktree scheiterte und die Meldung mit `tail`/`grep -v` ausgeblendet war (#15) — inzwischen gelöscht.
- Ein Gate hat gefangen: `scope-checkpoint-not-durably-recorded` (Artefakt in #404 nach dem zweiten Feuern, vor dem vierten Repo). Der Evidenz-Hook `claim-before-cheapest-check` feuerte zweimal (06:27, 06:35 UTC) und wurde beide Male mit Check beantwortet — zählt nach `gate_wirkung.py` aber als `zu-frueh` (gebaut 17.09.), daher nicht als Treffer geführt (§8).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | KommSafe-Leser Erst-Commit: `raw.update(fachlich)` hätte `tenant_id`/`source` überschrieben und Klartext-Fremdfelder durchgereicht; Ziel 3 in #22 verlangte strikte Projektion; Agent meldete „alle sechs Ziele erfüllt"; Nachfix mit Allowlist + „geschwätziger Parser"-Test vor Merge | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | post-hub `be10bda` → `9a3c085`; #22 Ziel 3; #23 mergedAt 07:16:34Z | check-ohne-positivkontrolle ×3 (kein Gate); test-asserts-the-case-in-mind-not-the-harmful-one ×3 (bewusst ohne Gate) |
| 2 | schreib-hub `main` 394004a trägt die WIP-Nachricht „wip(deps): … — ungeprueft / NICHT gemacht: Postgres, d.velop-Rundlauf, Rot-Nachweis" — der PR-Body belegt das Gegenteil; Präfix `wip` unzulässig | Kommunikation | mittel | SURVIVES (kommandobelegt) | `git log origin/main -1 --format=%s%n%b` schreib-hub; #21 Body | squash-message-inherits-wip-commit ×1 (neu) |
| 3 | schreib-hub#21 gemergt ohne ausdrückliches Merge-Wort; PR-Body „Nicht gemergt" unkorrigiert | Kommunikation | mittel | REFUTED | `ci.yml` Kopf „KEIN deploy-Job"; W0 nach autonomy-gates.md; Body-Absatz = Agenten-Selbstbeschreibung | — |
| 4 | schreib-hub#21 gemergt trotz fehlendem Postgres-Pfad (#27) → RLS ungetestet | fehlende Validierung | mittel | REFUTED (3b: Beleg korrigiert) | W0; Postgres-Pfad existiert im Repo nicht (`config/settings/test.py` Z.1–3); Lücke seit `a326e30`; #27 05:57:09Z = 1 min nach Merge. Achtung: der Diff fügt `MandantEinstellung.objects.update_or_create(tenant_id=…)` hinzu — neuer Schreibpfad auf eine RLS-Tabelle; macht #27 dringlicher, kippt das Verdikt nicht | — |
| 5 | Vertrag nicht nachgezogen: `posteingang-ereignis-v0.1.md` § Änderungen endet beim 16.09. (kein Vermerk zu Weg B / Irrläufer-Klasse), Abschnitt Transport führt Variante b weiter als „noch nicht spezifiziert", obwohl #23 sie baut; post-hub#21 Kriterium 1 verlangte den Vermerk | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `git show origin/main:docs/contracts/posteingang-ereignis-v0.1.md` Z.228–238 + §Transport; #23 Filelist ohne Contract | contract-ssot-stale-after-implementation ×1 (neu); Familie tracking-doc-stale-after-new-occurrence ×9 |
| 6 | Restarbeit aus #23 (.jpl-Parser, Scheduler/Cron, Push) ohne Issue | Prozesslücke | mittel-hoch | REFUTED | .jpl-Parser = Blocker-Absatz in post-hub#21; Push = Bestand (#14 gemergt 16.09.) | → Rest als #14 |
| 7 | frist-hub „16 go" zum Retro-Zeitpunkt nicht geliefert (13 uncommittete Dateien) | Prozesslücke | hoch | REFUTED | Commit `5a40f24` 07:30:06Z, PR #174 07:30:28Z — Timing-Artefakt des Retro-Aufrufs | — |
| 8 | Scope-Checkpoint erst nach dem zweiten Hook-Feuern durabel (05:57 Form A ohne Aussprache, 06:18 Form B → #404-Kommentar 13 s später); Übergang zum vierten Repo danach sauber gegated | Prozesslücke | mittel | SURVIVES (Skeptiker am Rohlog) | Transkript-JSONL Stop-Hooks 05:57:24Z/06:18:08Z; #404 Kommentar 06:18:21Z; „16 go" 06:57:21Z | scope-checkpoint-not-durably-recorded ×29 — **Gate hat gefangen** (Rev 2) |
| 9 | #22 Kriterium 5 („zwei Dateien; eine angenommen, eine Dublette") als „eine Datei zweimal" umgesetzt; Abweichung nirgends vermerkt (PR-Body nennt nur die POST-Abweichung) | fehlende Validierung | niedrig | SURVIVES (Skeptiker) | `tests/test_abholung_kommsafe.py` `_dracoon_mocken()` ein Knoten; #23 Body; 0 Kommentare | dod-reinterpreted-only-in-pr-body ×4 (hier: nicht einmal im Body) |
| 10 | Test `test_should_leser_strukturell_ohne_schreibfunktion_bleiben` prüft Mock-Methoden (Verhalten), nicht die Klassenstruktur; Substanz stimmt, Name verspricht mehr | Kommunikation | niedrig | SURVIVES (kommandobelegt) | `apps/adapters/kommsafe.py` Methodenliste; Testname | gate-modul-prueft-weniger-als-sein-name ×3 — Familie „Test", Gate sieht sie nicht |
| 11 | `erstellt_am` fällt bei fehlendem `timestampCreation` auf `datetime.min` (strftime `10101000000`, keine Exception); `event_id` = Stamm+Zeit kollabiert, zweites reales Dokument wird per 409 als Dublette verworfen; SDK: Feld `Optional[datetime] = None`; `knoten_id` lag als eindeutige Quelle vor; kein Test, kein Issue | fehlende Validierung | niedrig | SURVIVES (Skeptiker, Python-Probe + SDK) | `apps/adapters/kommsafe.py` `_zeitstempel(zeit) if zeit else datetime.min`; `abholung.py` event_id; dracoon `responses.py:46` | silent-fallback-value-instead-of-hard-fail ×1 (neu) |
| 12 | `httpx>=0.27`, `respx>=0.21` ohne Obergrenze; Erstpartei-Pakete im Repo mit `<X` | Prozesslücke | niedrig | REFUTED (3b) | post-hub `requirements.txt`: `dj-database-url>=2.2`, `psycopg>=3.2`, `gunicorn>=22.0`, `whitenoise>=6.6` — alle Drittpakete ohne Obergrenze, Upgrades über Renovate (#24); der PR folgt der Repo-Konvention | — |
| 13 | Fehlerlauf `jq: Befehl nicht gefunden` (Exit 127) in einer Mail-Auswertungskette; Umweg über Python | Werkzeug | niedrig | SURVIVES (kommandobelegt) | kennzahlen.txt Z.7 | tool-assumed-present-no-fallback ×1 |
| 14 | Scheduler/Cron für die Abholung (Betrieb) bewusst ausgelassen, ohne Issue — nur Issue-/PR-Text (#22 „Out of Scope") | Prozesslücke | niedrig | SURVIVES (Skeptiker, Issue-Liste ohne Treffer) | post-hub Issues 1,5,9,11,15,16,17,20,21,22,24 — kein Scheduler/Cron | deferred-item-no-tracking-issue ×43 — Gate `aufschub-anker` (unerprobt) sah den Fall nicht |
| 15 | Session-Branches lagen nach dem Merge noch auf origin (schreib-hub `pakete-0-11`, meiki-hub `prio5-anker`, post-hub `kommsafe-leser`): `gh pr merge --delete-branch` scheiterte am lokalen Worktree-Branch und löschte remote nicht; die Fehlermeldung wurde mit `tail -2` bzw. `grep -v 'failed to delete local'` ausgeblendet, „EXIT=0" war der von `tail` | fehlende Validierung | niedrig (Muster mittel) | SURVIVES (3b NEU, `git ls-remote --heads`) | Transkript 05:56:07Z / 07:16:30Z; `ls-remote` vor Bereinigung 1/1/1, nach `git push --delete` 0/0/0 | gruener-lauf-ohne-wirkung (🌀-Memory 2026-09-03) — Rezidiv; Prüffrage „woran hätte ich gemerkt, dass es NICHT wirkt?" nicht gestellt |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | alle Owner-Aufträge geliefert und belegt (Finder Soll-Ist S1); Abzug: Vertragsvermerk aus post-hub#21 Kriterium 1 fehlt (#5) |
| architektur_design | 3 | Leser/Übersetzer/Partnerprofil-Daten sauber getrennt, aber `datetime.min`-Rückfall statt Knoten-ID (#11) und Vertrag hinkt dem Bau hinterher (#5) |
| code_konventionstreue | 3 | `wip(deps)`/„ungeprueft" dauerhaft auf main (#2), Testname überzeichnet (#10) |
| risiko_debt | 3 | Datenschutz-Vektor im Erst-Commit gefangen (#1), aber #11 und #14 ohne Tracking bis zu dieser Retro; drei Remote-Branches als stille Reste (#15) |
| prozess_effizienz | 4 | drei Sonnet-Aufträge, alle mit Zahlen und Positivkontrolle zurück; ein Nachfix durch Review; Scope-Checkpoint erst beim zweiten Hook (#8) |
| entscheidungsqualitaet | 4 | Weg B, Irrläufer-Klasse ohne Code, Gerüst ohne Rateformat — alle vom Skeptiker bestätigt; Abzug für die unvermerkte Kriteriums-Abweichung (#9) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Brief nennt „Projektion strikt", Agent liefert `raw.update`, meldet „erfüllt"; Review fängt es (`9a3c085`) | Jedes Datenschutz-/Sicherheitskriterium im Brief bekommt seine Positivkontrolle vorgeschrieben: „Test zeigt, dass Fremdfeld X **nicht** ankommt" — ohne diesen Test gilt das Kriterium als nicht erfüllt | #1 |
| WIP-Branch mit „ungeprueft"-Commit wird nach Prüfung gesquasht, Squash übernimmt die alte Nachricht (394004a) | Vor `gh pr merge --squash` den Titel/Body des Squash explizit setzen (`--subject`/`--body`) oder den WIP-Commit amenden; Merge-Skript prüft `wip`-Präfix | #2 |
| Owner-Entscheid und Bau (Weg B) landen in Issue und Code, der Vertrag bleibt beim 16.09. | Ein Kriterium „Vertrag nachgezogen" im Zielzustand jeder Umsetzung, die eine Vertrags-Variante baut; PR-Filelist muss `docs/contracts/` enthalten oder den Verzicht begründen | #5 |
| Stop-Hook Form A (05:57) ohne Aussprache; erst Form B (06:18) erzeugt das Artefakt | Beim ersten Feuern sofort Checkpoint + Artefakt in einem Zug (Kommentar im Sitzungs-Issue), nicht erst auf die zweite Stufe warten | #8 |
| Kriterium 5 abweichend umgesetzt, Abweichung nur im Test-Docstring | Agent-Rückmeldung enthält je Zielkriterium „erfüllt / abweichend (wie) / offen"; abweichend ⇒ Satz im PR-Body | #9 |
| Testname „strukturell", Inhalt = Verhaltenstest | Testname nennt, was geprüft wird (`…keine_schreibenden_http_methoden…`); der Strukturtest (Klasse hat keine upload/delete-Methode) kommt dazu | #10 |
| `datetime.min` als stiller Ersatz für fehlende Erstellzeit | Fehlendes Pflichtfeld ⇒ harter Fehler mit Dateiname (`KommSafeFehler`), Datei zählt als `fehler` in der Bilanz; die Identität (Stamm + Erstellzeit) bleibt, sie ist akzeptierter Zielzustand (#22 Ziel 4) | #11 |
| `gh pr merge --delete-branch` scheitert am Worktree, Meldung per `tail`/`grep -v` ausgeblendet, Remote-Branch bleibt | Worktree **vor** dem Merge entfernen; Merge-Ausgabe nie filtern; danach `git ls-remote --heads origin <branch>` = 0 als Positivkontrolle | #15 |
| `jq` in Bash-Kette vorausgesetzt, Exit 127 | Für JSON-Auswertung `python3 -c`/`--jq` von `gh` nutzen; keine nicht installierten Werkzeuge in Ketten | #13 |
| Scheduler/Cron als „Out of Scope" im Issue-Text | Jeder Out-of-Scope-Punkt, der später gebaut werden muss, bekommt im selben Zug ein Issue (Betrieb der Abholung) | #14 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand vor diesem Report): 50 Slugs ≥2 mit Gate-Pflicht, davon 3 ohne registriertes Gate — darunter `check-ohne-positivkontrolle` (×2 → mit #1 ×3). Zuordnung der Überlebenden:

| Slug | Zähler vorher | mit dieser Retro | Status |
|---|---|---|---|
| check-ohne-positivkontrolle | 2 | 3 | **GATE-PFLICHT, kein Gate registriert** — Kandidat: Brief-Schablone verlangt je Sicherheitskriterium die Negativ-Probe (#1) |
| test-asserts-the-case-in-mind-not-the-harmful-one | 8 | 9 | bewusst ohne Gate (Owner-Entscheidung) — bleibt, #1 als Beleg |
| gate-modul-prueft-weniger-als-sein-name | 2 (Rückfälle seit Bau) | 3 | Gate rückfällig → 5a |
| dod-reinterpreted-only-in-pr-body | 3 | 4 | Gate-Pflicht besteht; #9 ist die schärfere Form (nicht einmal im Body) |
| deferred-item-no-tracking-issue | 42 | 43 | Gate `aufschub-anker` (blocking, unerprobt) sah #14 nicht → 5a |
| scope-checkpoint-not-durably-recorded | 28 | 29 | **gefangen** (Rev 2, Form A+B) — Beleg FÜR das Gate, kein Rückfall |

Memory-Abgleich (`grep` in `~/.claude/projects/-home-devuser-github-meiki-hub/memory/MEMORY.md`): `eigene-melder-brauchen-positivkontrolle` (16.09.) existiert und deckt #1 als Muster; `kein-hardcoding-db-crud` (13.09.) existiert — passt zum frist-hub-Nachlauf (außerhalb Scope); `subagent-abbruch-api-wochengrenze` (16.09.) war die Quelle des refuted #7.

### 5a. Rückfall-Prüfung (`tools/gate_wirkung.py`, Stand 0.0)

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| gate-modul-prueft-weniger-als-sein-name (advisory, revised 2026-08-31) | 2 (15./16.09., fremde Sitzungen) + #10 hier | **Quelle**: das Gate sieht nur Gate-Module, nicht Tests, deren Name mehr verspricht als der Inhalt | **ausweiten** auf Testnamen (`test_should_*strukturell*` ohne Struktur-Assertion) — `revised` + neue Positivkontrolle; Eintrag als Kandidat über `gate_verankerung_check.py --neu` (Owner-Zug, platform) |
| issue-offen-nach-gemergtem-fix (advisory, built 2026-09-07) | 2 (15.09.), kein Vorkommen im Scope dieser Sitzung (post-hub#22 sauber geschlossen) | **Ausgang** (Hypothese): Melder in 0.7.7 ohne Handlungszeile | **herabstufen** als Vorschlag — Entscheidung bleibt bei der Retro, die den Rückfall erzeugt hat; hier nur benannt |
| aufschub-anker (blocking, unerprobt) | #14 nicht gefangen | **Quelle**: Gate prüft nur Ausgelassenes mit Frist-Markern, nicht „Out of Scope"-Listen in Issue-Texten | **nachschärfen**: „Out of Scope:"-Zeilen im Zielzustand als Aufschub werten — Kandidat |

### 5b. Autonomie-Kalibrierung

- `over_ask`: keine — kein Vorgang wurde vorgelegt, der deterministisch/reversibel war (Merges bei grün in W0-Repos liefen autonom; Mails wurden als Entwurf vorgelegt, das ist Gate 2 Außenwirkung).
- `over_act`: keine — Prod/Publish: 0; drittes Repo (post-hub) war wörtlich beauftragt („8 … integration post assist"), viertes Repo (frist-hub) erst nach Checkpoint und „16 go".

## 6. Verankerung (Vorschläge, nicht geschrieben)

memory_candidates:
- `~/.claude/projects/-home-devuser-github-meiki-hub/memory/agent-brief-negativprobe-je-sicherheitskriterium.md` — `feedback`, drift: true, drift_episode 2026-09-17-raw-update-projektion: „Ein Brief-Kriterium ‚strikt projizieren / nie durchreichen / kein Schreibzugriff' ist ohne vorgeschriebene Negativ-Probe (‚Test zeigt, dass X NICHT ankommt') nicht prüfbar; der Agent meldet dann ‚erfüllt' aus dem Happy-Path. Realfall post-hub#23 `be10bda`."
- `…/squash-merge-uebernimmt-wip-nachricht.md` — `feedback`: „`gh pr merge --squash` ohne `--subject/--body` schreibt den ersten Commit-Text auf main — bei WIP-Branches steht dann ‚ungeprueft' dauerhaft neben einem grünen PR-Body (schreib-hub 394004a). Vor dem Squash Titel setzen oder amenden."
- `…/vertrag-nachziehen-ist-teil-des-zielzustands.md` — `project`: „Jede Umsetzung einer im Vertrag als ‚benannt, nicht spezifiziert' geführten Variante ändert `docs/contracts/` im selben PR (post-hub#23 hat es nicht)."

adr_candidates: keine — kein Befund erreicht die ADR-Schwelle (`policies/adr-threshold.md`); #5 ist eine Vertrags-Revision (v0.1 § Änderungen), kein ADR.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Vertragsvermerk 17.09. + Variante b als Günzburg-Adapter | post-hub | [#21](https://github.com/meiki-lra/post-hub/issues/21) | 🔵 ready | Doku-PR, ich |
| M2 | Issue: Betrieb der Abholung (Scheduler) | post-hub | [#21](https://github.com/meiki-lra/post-hub/issues/21) | 🔵 ready | Issue anlegen, ich |
| M3 | Issue: harter Fehler ohne Erstellzeit statt `datetime.min` (Identität bleibt) | post-hub | [#23](https://github.com/meiki-lra/post-hub/pull/23) | 🔵 ready | Issue + Fix-PR, ich |
| M4 | Issue: Testname/Strukturtest Leser | post-hub | [#23](https://github.com/meiki-lra/post-hub/pull/23) | 🔵 ready | ein Issue, ich |
| M10 | Drei Remote-Session-Branches gelöscht (Positivkontrolle 1→0) | schreib-hub, meiki-hub, post-hub | [#404](https://github.com/meiki-lra/meiki-hub/issues/404) | ✅ done | — |
| M5 | Squash-Nachricht auf main korrigierbar? (Revert+Re-Merge nein) — Hinweis-Commit | schreib-hub | [#21](https://github.com/meiki-lra/schreib-hub/pull/21) | 🟢 dein Zug | entscheiden: leer lassen oder `docs`-Commit mit Richtigstellung |
| M6 | Gate `gate-modul-prueft-weniger-als-sein-name` auf Testnamen ausweiten | platform | [gates](https://github.com/achimdehnert/platform/tree/main/docs/governance/gates/gates) | 🟢 dein Zug | `revised`-Eintrag freigeben |
| M7 | `check-ohne-positivkontrolle` Gate: Brief-Schablone mit Negativ-Probe | platform | [retro_kpis](https://github.com/achimdehnert/platform/blob/main/tools/retro_kpis.py) | 🟢 dein Zug | Gate-PR freigeben |
| M8 | Memory-Kandidaten (3) schreiben | meiki-hub | [Report](https://github.com/achimdehnert/platform/tree/main/docs/retros) | 🟢 dein Zug | freigeben |
| M9 | Streichbahn: Session-Start 0.7.7 als Melder ohne Zug streichen oder mit Zug-Zeile umbauen | platform | [session-start](https://github.com/achimdehnert/platform/blob/main/.windsurf/workflows/session-start.md) | 🟢 dein Zug | entscheiden |

## 8. Nicht verifiziert (Restlücken)

- Mailtexte der versandten Entwürfe (Zeiner 24214, Seitz 24198) gegen die drei Owner-Vorgaben aus Auftrag 12 — kein Finder hatte IMAP; billigster Check: `read_mail.py --folder 'Gesendete Objekte' --fetch 34733`.
- „Unbekannte Partnerklasse → Warteschlange" nur für den `manuell_noetig`-Zweig gegen Code verifiziert (`posteingang.py:113`); billigster Check: Test in post-hub mit unbekannter Klasse.
- Wie oft DRACOON `timestampCreation` produktiv auslässt (#11 bleibt Mechanismus-Befund, keine Häufigkeitsaussage).
- `einstellungen.py` (schreib-hub#21) nur oberflächlich auf Hardcoding gelesen; billigster Check: `grep -n '"Europe/\|feiertag' apps/schreiben/einstellungen.py`.
- frist-hub#174 (Kern 0.11, Fiktions-Literal → Abbruch) läuft außerhalb dieses Scopes; nächste Retro.
- `claim-before-cheapest-check` als gefangenes Gate: Hook-Feuern 06:27/06:35 UTC im Transkript belegt, aber `gate_wirkung.py` führt das Gate als `zu-frueh` (0 Treffer) — Wirksamkeit nicht berichtbar; billigster Check: Positivkontrolle des Gates gegen genau diese zwei Ereignisse.

**getan:** 3 Finder + 3 Skeptiker + 3b + Meta in frischem Kontext, alle Belege aus `origin/main`/`gh`, Rohlog für #8 · **angenommen:** Artefaktliste vollständig (Sitzungs-Branches/PRs), Owner-Zitate korrekt transkribiert · **nicht verifizierbar:** Mailinhalte, DRACOON-Produktivverhalten · **offen geblieben:** M1–M4 als Folgearbeit, M5–M9 Owner-Zug.

## Widerlegung

Phase 3b, Opus, frischer Kontext (nur Report-Entwurf + Artefaktliste), alle Belege aus `origin/main`/`gh`/Transkript-Zeitstempel.

| # | Punkt | Verdikt | Beleg |
|---|---|---|---|
| 1 | SURVIVES `raw.update` | BESTAETIGT | `git show be10bda:apps/eingang/abholung.py` Z.99; Fix `9a3c085` 07:14:12Z |
| 2 | SURVIVES WIP-Squash | BESTAETIGT | PR-Titel war `chore(deps): …`, der Squash nahm den Commit-Text |
| 3 | REFUTED Merge ohne Merge-Wort | BESTAETIGT, mit Rest | W0; keine Vorlageklasse. Rest: die mergende Sitzung las den Diff nicht selbst (Transkript 05:52–05:56 nur `pr view`/`checks`/`merge`), verließ sich auf das Sonnet-Handback — kein Regelverstoß, aber kein fremder Blick |
| 4 | REFUTED Merge trotz Postgres-Lücke | BESTAETIGT, Beleg korrigiert | Diff fügt `MandantEinstellung.objects.update_or_create(tenant_id=…)` hinzu — neuer Schreibpfad auf RLS-Tabelle; Verdikt hält (W0, Lücke vorbestehend, #27 getrackt), #27 wird dringlicher |
| 5 | SURVIVES Vertrag | BESTAETIGT | Contract zuletzt `91fc2a4` (16.09.); Owner-Entscheid nur Kommentar 06:19:53Z |
| 6 | REFUTED Restarbeit | BESTAETIGT | #21-Kommentar 06:59:30Z; Push = `8cfc020` |
| 7 | REFUTED frist-hub | BESTAETIGT | PR #174 07:30:28Z |
| 8 | SURVIVES Scope-Checkpoint | BESTAETIGT (nicht neu geprüft) | Zeitstempel plausibel; billigster Gegencheck `grep -c scope-checkpoint` im JSONL |
| 9 | SURVIVES Kriterium 5 | BESTAETIGT | ein Knoten, Abweichung nur im Modul-Docstring Z.3–5 |
| 10 | SURVIVES Testname | BESTAETIGT | kein `hasattr`-/Methodenlisten-Assert |
| 11 | SURVIVES `datetime.min` | BESTAETIGT — M3 gekippt | „event_id aus Knoten-ID" widerspräche #22 Ziel 4 und der Analyse (Knoten-ID verschwindet mit dem Löschen, Re-Upload = Doppelereignis); M3 auf den harten Fehler beschränkt |
| 12 | SURVIVES Pins | GEKIPPT | alle Drittpakete im Repo ohne Obergrenze, Renovate #24 |
| 13 | SURVIVES `jq` | BESTAETIGT | Transkript 05:47:50Z |
| 14 | SURVIVES Scheduler | BESTAETIGT | Issue-Liste ohne Treffer |
| N1 | Remote-Branches nicht gelöscht, Fehler weggefiltert | NEU → #15 | `git ls-remote --heads` 3/3 vorhanden; Transkript 05:56:07Z `tail -2`, 07:16:30Z `grep -v 'failed to delete local'` |

Geprüft, kein Befund: Mail-Cc (Kramer war im Strang, Offner als Setzung benannt) · Board-Datei (Ordnerpfad aus vertraulicher Quelle, lokal hinter Access — Hypothese) · Migration 0003 (`clean()` nur im Formular, Laufzeit fängt) · Handover-Stand (unentscheidbar bis `/session-ende`; billigster Check danach `git show origin/main:AGENT_HANDOVER.md | sed -n 3p`).

Abdeckung: 4 Repos gefetcht; gelesen schreib-hub 394004a/#21/#27, post-hub Contract/#21/#22/#23/abholung.py/kommsafe.py/models.py/forms.py/0003/Tests/requirements/Issue-Liste/`ls-remote`, iil-assist-core models.py + assist_rls.py, frist-hub #174, meiki-hub AGENT_HANDOVER, Board-Datei, Transkript 05:40–05:58Z + Merge-Ausgaben. Offen: ob der Sonnet-Agent den vollen 14-Datei-Diff las (billigster Check: Subagent-Transkript nach `gh pr diff` greppen).

## Streichbahn

**Kandidat:** `session-start-0-7-7-gate-wirkung-ohne-zug` — die Runner-Phase 0.7.7 (Gate-Wirkung) als Melder ohne Handlungszeile. **Belegart: kein Leser.** Der Runner meldete am 17.09. 05:02 `gate-modul-prueft-weniger-als-sein-name` als rückfällig (Journal: 3 Läufe, erstmals 2026-09-17); das Session-Start-Board dieser Sitzung führte es nicht als Item, und Phase 0.0 dieser Retro fand denselben Zustand unverändert — die Meldung erzeugte in drei Läufen kein Artefakt. Entweder bekommt die Phase eine Zug-Zeile in der Deutungstabelle („Konsequenz über `gate_verankerung_check.py --neu` eintragen") oder sie geht weg; ein Melder, der nichts auslöst, wird nicht lauter gemacht (Phase 0.0). Entscheidung: Owner (M9).

## Self-Review

Meta-Agent (Sonnet, nur Report + Skill): 10 Checks grün (Belege nachprüfbar, Scores ganzzahlig und verankert, Invariante 10 == 10, Frontmatter valide, eingefrorene Spalten, §5a mit beiden `RUECKFAELLIG`-Gates, §8 Vierklang, Pfad kollisionsfrei, `retro_report_check.py` Exit 0). Zwei Korrekturen eingearbeitet: `claim-before-cheapest-check` aus `gates_caught` gestrichen (Gate `zu-frueh`, Ehrlichkeits-Sperre) und zwei Längsschnitt-Zähler exakt gesetzt (8 statt „≥2", 3 statt „≥3"). `refuted_rate` 0,27 (nach 3b: 4 Phase-3 von 15) liegt im Band 0,2–0,8 — Falsifikation weder Theater noch Finder zu lasch.
