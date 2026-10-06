# Lehren & Historie — `/session-retro`

> Begleitdoku zu [`.windsurf/workflows/session-retro.md`](../../../.windsurf/workflows/session-retro.md).
> Entstanden bei der Kontext-Diät des Skills ([platform#2690](https://github.com/achimdehnert/platform/issues/2690) K5).
>
> **Arbeitsteilung:** Der Skill trägt die **Anweisung** — jede verlagerte Lehre hat dort
> eine imperative Zeile am Ort der Handlung behalten. Diese Datei trägt das **Warum**:
> Realfälle, Messungen, Begründungen und die Changelog-Historie, **wörtlich** so, wie sie
> bis 2026-09-02 im Skill standen. Nichts wurde gelöscht, alles hat eine Adresse.
> Ausnahme V2b (2026-10-06, [#3798](https://github.com/achimdehnert/platform/pull/3798)):
> Einige Passagen der Phasen 1, 3, 3b, 5 und 5a wurden im Skill umformuliert statt
> verschoben. Ihr alter Wortlaut steht in Git bei `35db40d1`, nicht hier.
>
> Changelog im Skill = **letzte drei Einträge** (Policy seit
> [platform#2696](https://github.com/achimdehnert/platform/pull/2696)); die Historie steht
> hier unten unter „Changelog-Historie".

---

## Phase 0.0 — 2026-09-02: warum die Wirkungsbilanz der erste Schritt ist

> **Die Retro hat eine eigene Wirkungsbilanz, und sie war bisher der letzte Schritt.**
> `gate_wirkung.py` lief in Phase 4 (Punkt 5a) — also erst, nachdem die Befunde dieser
> Sitzung schon standen. Gemessen am 2026-09-02: **14 von 33 Gates rückfällig** (#2374,
> #2678). Diese 14 sind keine Nebeninformation für den Schluss, sondern die stärkste
> vorliegende Aussage darüber, welche Regel als nächste bricht — sie gehören an den Anfang.

Die vier zulässigen Konsequenzen (nachschärfen · Drill ergänzen · Modus herabstufen ·
Sunset) und die Ehrlichkeits-Sperre stehen weiterhin im Skill — sie sind Anweisung,
nicht Begründung.

## Phase 0.1 — 2026-07-31: Skeptiker-Auswahl, Realfall `6bd412`

Realfall `session-retro-2026-07-31-meiki-hub-6bd412`: 5 Inline-Befunde, davon 3 kommandobelegt
und 2 Bewertungsbefunde. Zwei Sonnet-Skeptiker auf **nur die zwei Bewertungsbefunde**
(je ein Befund, benannte Dateipfade im Prompt, kein Repo-Sweep) widerlegten **beide** und
fanden dabei einen neuen Befund der Severity *hoch*, den der Inline-Pass übersehen hatte
(ein „Ersetzt"-Vermerk, der einen Adressaten stillschweigend fallen ließ). Die drei
kommandobelegten Befunde blieben ungeprüft — ohne Erkenntnisverlust.

**Die Richtung des Fehlers ist nicht vorhersagbar.** Der Inline-Pass hatte die zwei
Bewertungsbefunde als „nachsichtig verdächtig" markiert; real waren beide zu **streng** —
schlecht belegte Selbstanklagen, eine davon gestützt auf eine Versionsangabe ohne Artefakt.
Formuliere den Skeptiker-Auftrag deshalb neutral („widerlege, wenn du kannst"), nicht als
„prüfe, ob ich zu milde war".

**Kosten (gemessen, kein Schätzwert): ~55k Tokens pro eng geführtem Skeptiker** — enger
Auftrag, benannte Artefakte, Ausgabe ≤200 Wörter, ~6 Tool-Calls. Zwei Skeptiker = ~115k.
Ein Finder mit Repo-Sweep-Auftrag liegt deutlich darüber. Nenne diese Zahl, wenn du ein
Agenten-Budget zur Freigabe vorlegst — schätze sie nicht.

**Wenn die Umgebung Subagenten untersagt** (Repo-Memory, Capability-Profil, Systemanweisung):
Find-Phase inline fahren, die Befunde nach obiger Tabelle sortieren, und die Bewertungsbefunde
mit ihrer Zahl (~55k je) als Freigabe-Frage vorlegen — statt den Retro entweder ganz ohne
Falsifikation zu fahren oder ihn an der Budgetfrage scheitern zu lassen. Der Regel-1-Bruch der
Find-Phase bleibt dann in §8 als Restlücke stehen; die Falsifikation der weichen Befunde ist
nachträglich einholbar (Realfall oben: genau so gelaufen, mit Ertrag).

## Phase 1 / Phase 3 — 2026-07-16 und 2026-07-21: Instanz-Historie `stale-local-clone-as-ground-truth`

Diese
Pflicht galt bisher nur explizit für Phase 3 (Skeptiker); `stale-local-clone-as-ground-truth`
trat trotz „fetch first" ein 7. Mal (Phase 1, `session-retro-2026-07-16-iil-klickdummy-d80d23`:
4 gemergte PRs übersehen) und ein 8. Mal (`8d663b-incr` I2: `grep` auf lokalem mcp-hub-Tree HEAD
`c092cb8` zeigte alte Check-Zeilen, obwohl origin/main `15a1fc7` sie verankert hatte — nur durch
Content-Smell gefangen) auf — beide belegen: die Lücke ist die **Lesequelle**, nicht der Fetch.
Diese Zeile ersetzt das bloße Hoffen auf Einzelfall-Disziplin — exakt wie die Phase-3-Zeile es bereits für Skeptiker tut.

## Phase 1 — 2026-07-31: Session-Grenze ist die Konversation, nicht der Kalendertag

**Session-Grenze = die Konversation, NICHT der Kalendertag (Lehre 2026-07-31):**
Ein Datumsfilter sammelt an einem geteilten Arbeitstag auch fremde Sitzungen ein.
Realfall `36c670`: der Collector lieferte 30 PRs, von denen 23 anderen Sitzungen
gehörten — ungeprüft hätten die Finder fremde Arbeit beurteilt. Der Scope wird
über die **Branch-Präfixe/PR-Nummern der eigenen Sitzung** gezogen (bzw. über den
Transkript-Pfad, falls gegeben); das Datum ist nur der Vorfilter, nie das Kriterium.

## Phase 1 — 2026-07-31: `--since` braucht die Uhrzeit

> ⚠️ **`--since` braucht die Uhrzeit.** `--since=<datum>` ohne `00:00` liefert
> **null Treffer**, obwohl Commits an dem Tag existieren — gemessen 2026-07-31 in
> `~/.claude`: `--since=2026-07-31` → 0, `--since='2026-07-31 00:00'` → 3. Der
> Collector meldete daraufhin „keine Commits" als Faktum. Die Abfrage war korrekt
> ausgeführt und trotzdem falsch; eine stille Null ist hier der teuerste Fall.
> Alternativen mit demselben Ergebnis: `--after=<vortag>` oder `--since=1.day`.

## Phase 1 — 2026-06-17: warum die Infra-Topologie-Sonde Pflicht ist

**Infra-Topologie-Sonde (Pflicht, wenn die Session CI/Deploy/Runner/Hosts berührte —
Lehre 2026-06-17: fehlende Infra-Transparenz war wiederholt Outage- und Merge-Blocker-
Quelle):** die SoT `platform/infra/hosts.yaml` gegen die Realität abgleichen, nicht raten.
Ein Workflow auf einem Label, das kein Online-Runner trägt, hängt unbegrenzt und
blockiert Merges. Drift hier → Längsschnitt-Gate-Kandidat (Phase 4/5), kein Einzelfix.

## Phase 2 — 2026-07-04: Finder-Mandat, Realfall `e17299-incr`

(Realfall e17299-incr: ein Finder fuhr
eigenmächtig Collector+Skeptiker+Report und eröffnete PR #924 auf dem Report-Zielpfad des
Orchestrators — Partial-Report ohne die anderen Dimensionen, musste mit Coverage-Nachweis
geschlossen werden; zusätzlich hatte er die Datei im geteilten Haupt-Tree gestaged.)

## Phase 2.5 — 2026-06-14: Realfall pptx-hub — ein Finder verfiel in den Fehler, den er anklagte

(Realfall: zwei Finder
widersprachen sich über `pptx-hub origin/main`; **ein Finder verfiel selbst in den stale-local-Fehler,
den er anklagte** — genau dafür existiert Richter≠Angeklagter.)

## Phase 3 — 2026-06-04: Verify zieht den Beleg unabhängig neu

**Eiserne Verify-Regel (Lehre 2026-06-04):** Der Skeptiker bekommt **nur die Behauptung, NICHT
den Finder-Befehl** — und muss den Beleg **unabhängig neu ziehen**, breiter/rekursiv (`find -name`,
nicht `ls <dir>`; `grep -r`, nicht `grep <einzelne Datei>`). Wiederholt er den Finder-Glob, wandert
dessen False-Positive ungeprüft durch. (Realfall: Finder grepte `tools/`, übersah `tools/tests/`,
Verify wiederholte es → ein falscher Befund „kein Testfile" überlebte.)

**Belegpflicht gilt AUCH für Längsschnitt-/Wiederholungs-Behauptungen** (Phase 4): „wiederholt
Drift-Memory X" ist ein Befund → X muss per `ls`/`grep` existieren, sonst REFUTED. (Realfall:
Verweis auf nicht-existente Memory `claim-confidence-vs-cheapest-check`.)

## Phase 3 — 2026-07-06: Frisch-Checkout-Pflicht, 3. Vorkommen

`stale-local-clone-as-ground-truth`
war bereits ×2 gate-pflichtig (`e17299`, `a2c373`); beim Retro `3b123e` trat es ein drittes
Mal auf — diesmal INNERHALB der eigenen Skeptiker-Verifikation dieser Skill (ein Skeptiker
prüfte zunächst gegen einen veralteten lokalen `main`, in dem ein PR-Merge fehlte, und musste
nachträglich fetchen). Diese Zeile ersetzt das bloße Hoffen auf Einzelfall-Disziplin.

## Phase 4 — 2026-08-09: Form des Frontmatter-Felds `repo_scope`

```yaml
repo_scope: [<repo>, …]   # Konvention: bare Repo-Slugs (a-z0-9_-), kein Pfad, kein
                          # owner/repo — `~/.claude` → `dotclaude-memory`,
                          # `bahn-sqf/pg-hub` → `pg-hub`. Reine Lese-Hilfe: seit
                          # #1840 prüft retro_kpis.py das Feld NICHT mehr.
```

## Phase 4 — 2026-08-20: warum das Frontmatter-Feld `gates_caught` existiert

```yaml
gates_caught: [<slug>, …]        # Teilmenge von recurring_findings: Befunde, die ein
                                 # BESTEHENDES Gate in dieser Sitzung gefangen hat.
                                 # `retro_kpis.py` zaehlt sie weiter (der Befund trat auf),
                                 # `gate_wirkung.py` wertet sie als Beleg FUER das Gate
                                 # statt als Rueckfall. Ohne diese Trennung sammelt ein
                                 # Gate, das seine Arbeit tut, dieselben Ausrufezeichen
                                 # wie eines, das blind ist (Realfall 2026-08-20:
                                 # der Scope-Checkpoint-Hook feuerte, der Scope wurde
                                 # durabel abgelegt — und galt trotzdem als Wiederholung).
```

## Phase 4 Punkt 5 — 2026-06-14: warum der maschinelle Zähler das Erinnern ersetzt

Der maschinelle Zähler ersetzt das
manuelle Erinnern (Realfall 2026-06-14: `worktree-orphan-accumulation` ×2 erst vom Tool gefangen).

## Phase 4 Punkt 5a — 2026-08-20: warum die Klasse „Gate rückfällig" existiert

**Warum die Klasse existiert:** Am 2026-08-20 über 82 Retros gemessen — 8 von 20 Gates
waren rückfällig, `claim-before-cheapest-check` **16×** seit Bau am 2026-08-02, obwohl
als Stop-Hook verdrahtet und mit grünem Drill. Jede dieser 16 Retros buchte ihn als
Wiederholung des Befunds statt als Befund über das Gate — deshalb wuchs der Zähler und
nicht die Wirkung. `retro_kpis.py` konnte das nicht zeigen: es zählt Slugs, nicht Rückfälle.

## Phase 4 Punkt 5a — 2026-09-02: warum ein Rückfall den bestehenden Eintrag ändert

Ein neuer Slug für dieselbe Sache spaltet
den Längsschnitt: das alte Gate steht ab da für immer auf `RUECKFAELLIG`, das neue auf
`zu-frueh`, und keine der beiden Zeilen sagt noch, ob die Sache besser geworden ist.
Was in Phase 0.0 als Konsequenz entschieden wurde, wird hier eingetragen — der
Registry-Edit läuft durch `tools/gate_verankerung_check.py --neu` (session-ende
Phase 0f-verankerung), sonst ist er kein Eintrag, sondern ein Kandidat (#2234).

## Phase 4 Punkt 5b — 2026-07-03: Herkunft der Autonomie-Charter

So kalibriert sich die Autonomie-Grenze aus
gemessenen Fehlern statt aus einem Einmal-Entwurf (Realfall 2026-07-03: 3 Secrets + ein grüner
Nicht-Deploy-Merge als `over_ask` geparkt → Charter daraus entstanden).

## Phase 4 — 2026-06-04: Report-Pfad-Kollision bei Parallel-Sessions

**Durable Heimat = git `platform/docs/retros/…`** (zentral, versioniert, gebackupt —
`retro_kpis.py` liest den Längsschnitt von dort). **NICHT mehr
`~/shared/`** (ungetrackt/ungebackupt → war für diese benötigte Funktion nicht wegwerfbar; KONZ-010).
Der
bloße `…-<datum>.md`-Default ist verboten (Realfall 2026-06-04: Parallel-Session-Kollision).

## Phase 5 — 2026-06-14 und 2026-08-20: die zwei Werkzeuge des Längsschnitts

> **Längsschnitt der Skill selbst (PFLICHT in Phase 4, nicht optional):** `python3 tools/retro_kpis.py`
> liest die Frontmatter aller `platform/docs/retros/session-retro-*.md`, trendet `refuted_rate`/Scores und eskaliert
> jeden `recurring_finding` mit Zähler **≥2 über Retros** zum Gate-PR-Pflicht-Item. Stdlib-only, kein Setup.
>
> **Zweites Werkzeug, andere Frage (PFLICHT seit 2026-08-20):** `python3 tools/gate_wirkung.py`
> beantwortet nicht „wie oft kam der Slug?", sondern „wie oft kam er, **nachdem** sein Gate
> gebaut war?". Der Zähler von `retro_kpis.py` kann steigen, während das Gate wirkt (alte
> Vorkommen zählen mit) — und er kann ruhig aussehen, während ein Gate seit Wochen versagt.
> Erst beide zusammen sagen, ob der Loop besser wird oder nur länger protokolliert.

## Abschluss-Checkliste — 2026-09-02: warum die Tabelle entstand

> **Warum diese Tabelle 2026-09-02 überhaupt entstand:** diese Skill hatte als einzige der
> drei Session-Skills **keine** — 6 Phasen mit PFLICHT-Markern, aber kein Ort, an dem eine
> übersprungene Phase auffällt. Genau die Lücke, die der Realfall
> `session-retro-2026-07-15-platform-c494a2` (Befund #8) für `session-ende.md` belegt hat:
> eine neue Pflicht-Phase lag vor, wurde aber nicht ausgeführt, weil die Abschluss-Checkliste
> sie nicht abfragte. „Bewusst übersprungen, weil X" zählt als erfüllt — stillschweigend
> ausgelassen nicht.

## Header — 2026-09-02: gestrichene Phantom-Referenz „Deterministische Engine"

Bis 2026-09-02 nannte der Skill-Kopf einen alternativen Ausführungsweg:

> **Deterministische Engine (optional):** Für schwere Läufe den JS-Workflow
> `~/shared/session-retro.workflow.js` via Workflow-Tool starten (parallele Finder +
> pipeline-erzwungene Falsifikation). Dieser Command ist die portable Prosa-Variante mit
> identischer Methode.

**Gestrichen (platform#2690 K5).** Beleg: `ls -l ~/shared/session-retro.workflow.js` →
*Datei oder Verzeichnis nicht gefunden* (geprüft 2026-09-02). Der Skill verwies als
Alternativ-Ausführungsweg auf eine Datei, die es nicht gibt — genau die Klasse, die
Phase 3 selbst als REFUTED führt („Belegpflicht auch für Längsschnitt-Behauptungen —
Verweis auf nicht-existente Memory"). Der zweite Nennungsort war der Changelog-Eintrag
2026-06-04 (unten wörtlich erhalten, als Historie).

## Kontext-Diät V2b — 2026-10-06: was aus dem Skill hierher wanderte

Der Skill war seit der Diät vom 2026-09-02 von seiner damaligen Größe auf 38596 Bytes
gewachsen; die Ratsche `docs/governance/startlast-deckel.json` (platform#3785) verlangt
Senkung. Die folgenden Abschnitte standen bis 2026-10-06 **wörtlich** so im Skill; dort
blieb je eine Anweisungszeile mit Verweis hierher. Anweisungen, die im Skill nur knapper
formuliert wurden, behalten ihren alten Wortlaut in Git:
`git show 35db40d1:.windsurf/workflows/session-retro.md`.

<a id="v2b-kopf"></a>
### Skill-Kopf und Modell-Routing (Volltext)

> **Zweck:** Eine Arbeitssession schonungslos reviewen: Angeklagter≠Richter, Artefakt-Erdung
> statt Erinnerung, geschlossener Lessons-Loop, Falsifikation der eigenen Befunde.
> **Wann:** nach größeren Umbau-/Architektur-Sessions; am Sitzungsende. **Wann NICHT:**
> Trivial-Edits → höchstens `lean`.

Find/Verify durch **„du"** = Self-Review = Bruch von Regel 1. „Billiger" heißt
**Sonnet-Subagent**, nicht **kein** Subagent. Opus nur in 3b oder bei Nuance-Fail.

<a id="v2b-phase-3b"></a>
### Phase 3b — Abgrenzung zu Phase 3 und 5

Phase 3 widerlegt **einzelne Befunde**, Phase 5 prüft die **Form**; 3b widerlegt **das Urteil
dieser Retro**.

Phase 9 (Wortlaut bis 2026-10-06): Die Übergabe-Antwort ist eine Entscheidungsvorlage — der
Report liegt im Repo und wird nicht nacherzählt.

<a id="v2b-phase-0"></a>
### Phase 0.1 — Subagenten-Verbot, Trigger-Konflikt, Increment-Retro (Volltext)

Auftrag **neutral** („widerlege, wenn du kannst"), nie „prüfe, ob ich zu milde war".
**Kosten (gemessen): ~55k Tokens je Skeptiker** — bei einer Budget-Freigabe diese Zahl nennen.
**Untersagt die Umgebung Subagenten:** inline finden, nach der Tabelle sortieren,
Bewertungsbefunde mit ihrer Zahl zur Freigabe vorlegen; der Regel-1-Bruch bleibt in §8 als
Restlücke.

**Trigger-Konflikt (`deep` wegen Prod vs. Dichte):** bei `deep` starten; **eine** Stufe runter
(→ `full`) nur wenn **alle drei** zutreffen — (a) Prod-Schritt explizit freigegeben
(PR-Body-Warnung oder `AskUserQuestion`), (b) voll rollback-fähig (**keine** DB-Migration),
(c) findings_total-Schätzung ≤10. Mit Prod-Schritt **nie** `lean`. Reduktion + Begründungen als
`footprint_reduction_reason` ins Frontmatter.

**Increment-Retro (Anchor am selben Tag):** (1) `session_id`-Suffix `-incr`; (2) **nur neue
Artefakte** in-scope, Vor-Retro NICHT re-litigieren; (3) Parent-Slugs zählen als Vorkommen-1 ⇒
derselbe Slug im Increment = Vorkommen-2 ⇒ **Gate-Pflicht, auch same-day**; (4) mit
Prod-Schritt mindestens `full`.

<a id="v2b-phase-4"></a>
### Phase 4 Punkt 5a/5b — Zuschnitt, Handover-Fall, Nominierung (Volltext)

`positivkontrolle` (`gate_wirkung.py` liest `revised or built`). Der Edit läuft durch
`tools/gate_verankerung_check.py --neu` (session-ende 0f), sonst ist er Kandidat, kein Eintrag
(#2234). **Zuschnitt prüfen (#3734):** Konnte das Gate den Fall nach seinem Zuschnitt nicht
sehen, bekommt die Zeile `gates_verwandt: <Begründung>` (≥10 Zeichen in derselben Zelle) und
zählt nicht gegen das Gate; ohne Begründung zählt sie als Rückfall. Ab drei verwandten Fällen
meldet `gate_wirkung.py` `ZUSCHNITT-PRUEFEN` (#3754). Ein Handover-Befund vor dem Sitzungsende
ist nur dann Rückfall von `handover-stale-vor-merge`, wenn die Endprüfung trotzdem grün war,
sonst `gates_verwandt`.

**5b. Autonomie-Kalibrierung:** `over_ask` (vorgelegt, obwohl nachweislich
**deterministisch/reversibel**) und `over_act` (autonom getan, obwohl **Gate**:
Prod/Publish/Merge-auto-deploy/3.-Repo/irreversibel) gegen die Artefakte messen. Muster **≥2
über Retros** ⇒ Gate-Liste in `feedback_autonomy_charter` **schärfen**. **Klassen-Slugs
Pflicht (KONZ-025 Art. 2.1a)**, eng benannt (`pr-merge-nicht-deploy-repo`, nicht `merge`).
`retro_kpis.py --nominierung`: Klasse ≥2 ⇒ **NOMINIERT** (Vorschlag im Registry-Format, eine
Stufe, als „erweitert meine Macht" gekennzeichnet — Ratifikation bleibt Kapitäns-Zug);
`over_act` derselben Klasse im Fenster **sperrt** sie (Art. 2.2).

**Synthesizer-Grenze und Report-Pfad (Wortlaut bis 2026-10-06):**

**Synthesizer-Grenze:** Phase 4 ist **nur Zusammenführen** — **keine** neuen `gh`/`git`-Befehle.
Widerspruch oder ungedecktes Faktum → zurück nach 2.5/3 ODER als Lücke in §8. Nur durch
Session-Gedächtnis gedeckte Befunde sind **Hypothese**, nicht SURVIVES.

**Report-Pfad (KONZ-platform-010):**
`platform/docs/retros/session-retro-<datum>-<repo>-<session-id-kurz>.md`, committet — auch wenn
die Session ein anderes Repo betraf. `<session-id-kurz>` = letzte ~6 Zeichen. **Existiert der
Pfad → NICHT überschreiben**, Suffix anhängen; `…-<datum>.md` ohne Repo/ID ist verboten.

<a id="v2b-phase-5"></a>
### Phase 5 — `refuted_rate`-Band (Volltext)

`refuted_rate` **ausschließlich numerisch** als Band-Vergleich (`retro_kpis.py`), kein Urteil
über einzelne SURVIVES/REFUTED (das ist 3b). Band: dauerhaft **>0,8** → Finder zu lasch;
**<0,2** → Falsifikation ist Theater. Echte Falsifikations-Quote nur
`phase3_refuted/(findings_total − pre_refuted)`.

<a id="v2b-phase-1"></a>
### Phase 1 — Sammler-Subagent gestrichen, Transkript per Skript

**Kein Sammler-Subagent mehr (Streichbahn Retro 916eb7, Owner-Wort 2026-09-16, Belegart
„kein Effekt"):** Die Finder ziehen `gh pr view`/`gh issue view`/`git show origin/main` für
dieselben Artefakte ohnehin selbst neu (Eiserne Regel 2 verlangt es); der Sammler-Report war
Dublette mit eigenen Fehlern (falscher Issue-Titel, „ungeprüft" trotz vorliegendem Beleg).

**Transkript-Kennzahlen per Skript, nicht per Sammler (Owner-Entscheid 2026-09-14, Streichkandidat
`retro-phase1-sammler-transkriptauswertung`):** Ablehnungen, Fehlerläufe (auch ohne `is_error`),
Silent-Reminder mit Abstand zum nächsten sichtbaren Text und Nutzer-Nachrichten liefert
`python3 tools/retro_transkript_kennzahlen.py <transkript.jsonl> [--von ISO] [--bis ISO]`; vorher
einmal `--selbsttest` (Positivkontrolle je Klasse). Die Skript-Ausgabe geht als Datei an die
Finder — kein Agent wertet das JSONL selbst aus. Realfall kbiAvn-incr: ein Sammler-Agent
meldete „0 Ablehnungen, 0 Fehler", tatsächlich 4 und 10.

**Infra-Topologie-Sonde (Wortlaut bis 2026-10-06):** plus
`gh api repos/<owner>/<repo>/actions/runners` und `runs-on:` gegen lebende Runner (Label
ohne Online-Runner hängt unbegrenzt). Drift → Längsschnitt-Gate-Kandidat, kein Einzelfix.

<a id="v2b-phase-2"></a>
### Phase 2 — 2026-09-22: warum alle Finder in einer Nachricht starten

Die Dimensionen wissen nichts voneinander; nacheinander gestartet wartet die Retro dreimal
hintereinander auf denselben Schritt. Das Budget aus 0.1 bleibt unverändert — es zählt
Agenten, nicht Runden. Gleiches gilt für die Skeptiker in Phase 3: erst alle starten, dann
alle einsammeln. Wer einen Finder startet, sein Ergebnis liest und **dann** den nächsten
startet, hat die Prüftiefe nicht erhöht, nur die Wartezeit verdreifacht.

**Phase 2.5 (Wortlaut bis 2026-10-06):** Vor Phase 3 die Finder-Outputs auf
**widersprüchliche Fakt-Behauptungen über dasselbe Artefakt** scannen, jeden Widerspruch als
Paar markieren. **NICHT in Phase 4 auflösen** (verstecktes Verify aus dem Haupt-Kontext),
sondern als **zusätzlichen Skeptiker-Task**: der zieht das Artefakt **unabhängig aus
`origin/main`** und entscheidet binär. Nur die verifizierte Version geht in den Report — mit
eigener Befund-Nummer + Kategorie/Severity.

<a id="v2b-phase-6"></a>
### Phase 6 — 2026-09-07: Rückweg der Extern-Antwort, Fehlschluss „keine Datei = kein Leser"

**Briefing-Auftrag (Wortlaut):** Anbieter-**fremde** Zweitmeinung (fremde
Trainings-Blindflecken). (3) Auftrag: *„**Advocatus Diabolus + Out-of-the-Box:** finde, was
dieser Retro übersehen oder falsch bewertet hat. Du hast **KEIN Repo-Zugriff** → kritisiere
**Methode/Struktur/Blindflecken/Score-Logik/Soll-Ablauf**, behaupte **keine**
Evidenz-Fakten."* Der Evidenz-Recheck bleibt Phase 3/3b/5; wiederkehrende Methoden-Kritik
fließt in **diese Skill** (Changelog).

**Rückweg — der Kanal läuft manuell, also braucht die Antwort einen Ort (Owner-Vorgabe
2026-09-07):** Der Owner holt die Zweitmeinung über seine Flatrate-Oberfläche und kopiert sie
von Hand zurück; es gibt **keinen** automatischen Rückkanal.

⚠️ **Fehlende `-extern*.md` heißt NICHT „keine Antwort" und NIE „kein Leser".** Genau dieser
Fehlschluss lief zweimal: am 2026-09-02 gegen `adr-handoff-extern` (platform#2088, 19 von 24
angeblich „ohne Antwort" — tatsächlich alle beantwortet) und am 2026-09-07 in der Retro
`c1ba5d`, die Phase 6 deshalb als Streichkandidat führte. Owner-Korrektur beide Male: der
Handoff wird häufig genutzt, nur eben per Copy-and-paste. Die Abwesenheit einer Datei belegt
die Abwesenheit einer Handlung nur, wenn die Handlung diese Datei erzeugen **muss**.

<a id="v2b-phase-7"></a>
### Phase 7 — warum es die Streichbahn gibt

Ohne sie wächst der Loop monoton — jede Retro darf anbauen, keine muss abtragen.

**Ergebnis und Ratsche (Wortlaut bis 2026-10-06):** Ergebnis als
`streichkandidaten: [<slug>, …]` (leer ⇒ `streich_begruendung:` Pflicht), als Abschnitt
`## Streichbahn` und als Zeile im Action-Board. **Ratsche:** ein Kandidat, der zwei Retros
hintereinander auftaucht und nicht gestrichen wurde, ist selbst ein Befund.

<a id="v2b-phase-8"></a>
### Phase 8 — 2026-09-16: warum der Report-Prüfer eine eigene Phase bekam

**Warum das eine eigene Phase bekommt:** gemessen über die 16 Reports seit dem
2026-09-02 fehlte der Vierklang in **fünf**, darunter den zwei jüngsten. Regel 5
ist als „nicht verhandelbar" ausgewiesen; die Abschluss-Checkliste fragte sie nur
mittelbar ab (Punkt 11 verlangt „§8 gefüllt" — §8 war in allen 16 da). Eine Regel
ohne Zeile, die sie nachzählt, wird beim Lesen überflogen.

Der Prüfer läuft zusätzlich in der CI (`tools/tests/test_retro_report_check.py`,
Required Check) über jeden Report ab dem Stichtag — die fünf älteren Lücken
bleiben bewusst außerhalb, damit der erste Lauf nicht mit Altlasten rot wird.

<a id="v2b-anti-patterns"></a>
### Anti-Pattern-Katalog (bis 2026-10-06 im Skill)

Jeder Eintrag ist im Skill als Regel am Ort der Handlung formuliert; die Liste ist die
Gegenprobe beim Lesen eines Reports.

- ❌ Aus dem eigenen Session-Kontext urteilen (in-context self-review).
- ❌ Befund ohne harten Artefakt-Beleg.
- ❌ Befunde nicht falsifizieren — performative Kritik durchlassen.
- ❌ Memory/ADR/CLAUDE.md selbst schreiben statt nur vorschlagen.
- ❌ Wiederkehrendes Muster als „noch ein Memo" abtun statt als Gate-Kandidat eskalieren.
- ❌ Genannte Repos als „separaten Workstream" aus dem Scope kippen.
- ❌ **Verify wiederholt den Finder-Befehl** statt den Beleg breiter neu zu ziehen.
- ❌ **Drittes Verdikt „weakened/teilweise"** — Falsifikation ist binär.
- ❌ **Längsschnitt-Behauptung ohne Existenz-Check** des Artefakts (Phantom-Referenz).
- ❌ **Soll-Schritt ohne Befund-Referenz** ODER Überlebender ohne Soll-Schritt.
- ❌ **Default-Dateiname `…-<datum>.md`** → Kollision bei Parallel-Sessions.
- ❌ **Halbscores** (2.5) — brechen die Längsschnitt-Vergleichbarkeit.
- ❌ **Multi-Agent für `lean`** / Skeptiker je Befund statt je Dimension ab ~4 Befunden.
- ❌ **Skeptiker auf einen kommandobelegten Befund** — bezahlt wird eine Zweitausführung.
- ❌ **Agenten-Budget schätzen statt beziffern** (~55k je Skeptiker ist gemessen).
- ❌ Meta-Self-Review (Phase 5), der die **Session** statt den **Report** beurteilt.
- ❌ **3b aus dem Haupt-Kontext oder mit Session-Erzählung** — der Angeklagte widerlegt sich selbst.
- ❌ **3b „nichts gefunden" ohne Abdeckungsauskunft** (Eiserne Regel 5).
- ❌ **Phase 7 „keiner" ohne Grund-Satz** oder Kandidat ohne eine der vier Belegarten.
- ❌ Find/Verify durch **„du"** „zum Sparen" — Kosten-Fix ist Sonnet-Subagent, nicht **kein** Subagent.
- ❌ **Opus als Default** — Sonnet trägt Find/Verify/Meta; Opus nur in 3b.
- ❌ Extern-Handoff **Evidenz-Fakten** behaupten lassen — extern hat kein gh/git.
- ❌ **Finder-Widerspruch in Phase 4 per neuem git/gh auflösen** — verstecktes Verify.
- ❌ **Nummernlose Befund-Zeile** — bricht eingefrorene Spalten + `findings_total`.
- ❌ **`recurring_finding` ohne `retro_kpis.py`-Zähler-Check** — Längsschnitt als Dekoration.
- ❌ **`refuted_rate` ohne `pre_refuted`-Trennung** — Finder-Stroh bläht die Quote.
- ❌ **Collect ohne vorheriges `git fetch`** — gilt für JEDEN Collect-Schritt, auch `lean`.
- ❌ **Nach dem Fetch die Working-Tree-Datei greppen** statt aus dem Ref zu lesen.
- ❌ **Report abgeben, ohne `retro_report_check.py` darüber laufen zu lassen** (Phase 8).
- ❌ **§8 vorhanden als Beleg für Regel 5 werten** — der Abschnitt ist nicht der Vierklang.

---

## Changelog-Historie

Die letzten drei Einträge stehen im Skill selbst; alles Ältere steht hier — wörtlich.

- 2026-10-05: **Phase 9 Abschluss-Maßnahmen (PFLICHT) + Checklisten-Zeile 22** (Owner-Wort
  „dieses Vorgehen sollten wir etablieren", platform#3716). Die Übergabe nennt, was zu
  entscheiden ist, mit Empfehlung und Link, statt den Report nachzuerzählen.
- 2026-09-22: **Nebenläufig starten statt nacheinander warten** (platform#3373, Auftrag
  „Session-Skills auf Laufzeit optimieren"). Phase 1 bündelt ihre Sammel-Befehle, Phase 2 und
  Phase 3 starten alle Subagenten in EINER Nachricht; Checklisten-Zeile 21. Kein Budget, keine
  Dimension, keine Pflicht-Phase gestrichen — die Wartepunkte auf dem kritischen Pfad sinken
  bei `full` (3 Finder + 3 Skeptiker) von 6 auf 2. Zahlen und Messung:
  `docs/governance/session-skills-lehren/laufzeit.md`.

- 2026-09-16: **Phase 1 Sammler-Subagent gestrichen** (Streichbahn Retro 916eb7, platform#3238,
  Owner-Wort „R9 streichen"). Belegart „kein Effekt": alle drei Finder zogen dieselben
  Artefakte selbst, der Sammler-Report enthielt zwei eigene Fehler. Phase 1 ist jetzt inline
  (Artefaktliste + `retro_transkript_kennzahlen.py`), `full` = ≤5 Find/Verify, ≤6 mit 3b/Meta.

- 2026-09-16: **Phase 8 `retro_report_check.py` + Checklisten-Zeilen 19/20.** Gemessen über
  die 16 Reports seit 2026-09-02: der von Eiserner Regel 5 verlangte Vierklang fehlte in
  fünf, darunter den zwei jüngsten (apo-hub 40c069, platform b7822e). Die Checkliste fragte
  ihn nur mittelbar ab („§8 gefüllt" — §8 war überall da). Der Prüfer läuft in der CI über
  jeden Report ab dem Stichtag; die fünf Altlücken bleiben bewusst außerhalb.

- 2026-09-14: **Phase 1 Transkript-Kennzahlen per `tools/retro_transkript_kennzahlen.py`** (Owner-Entscheid
  aus Retro kbiAvn-incr, Streichkandidat umgesetzt). Der Sammler-Agent wertet das JSONL nicht mehr aus;
  das Skript fängt auch Fehler mit `is_error: False` und misst die Silent-Reminder-Lücken.
- 2026-09-07: **Phase 6 bekommt einen Rückweg** (Owner-Vorgabe, Retro `c1ba5d`). Externe
  Antworten liegen als `…-extern1.md`/`-extern2.md` in `~/shared/` und sind Pflichtlektüre der
  nächsten Retro desselben Scopes (Verdikt je Punkt, Abschnitt `## Extern-Auswertung`). Der
  Streichkandidat `retro-phase-6-extern-handoff` ist damit **erledigt, nicht gestrichen**: die
  Belegart „kein Leser" war falsch — der Kanal läuft manuell über den Owner.
- 2026-09-02: **Kontext-Diät + zwei neue Bahnen** (platform#2690 K5). Lehren, Realfälle und
  Changelog-Historie wörtlich in die Begleitdoku, je ein Verweis im Skill. **Neu:** Phase 3b
  Widerlegungsbahn (T4, PFLICHT ab `full`) + Phase 7 Streichbahn (PFLICHT, jeder Footprint).
- 2026-09-02: **Phase 0.0 Wirkungsbilanz zuerst + `revised`-Regel in Phase 4 + erste
  Abschluss-Checkliste** (platform#2690 K4). Drei zusammengehörige Änderungen:
  (1) `gate_wirkung.py` läuft als **erster** Schritt der Retro statt als vorletzter — bei
  14 von 33 rückfälligen Gates (#2374, #2678) ist die eigene Wirkungsbilanz die stärkste
  Aussage darüber, welche Regel als nächste bricht, und sie stand bisher hinter der
  Befund-Suche; jedes `RUECKFAELLIG`-Gate wird jetzt mit Ursache (am Ausgang oder an der
  Quelle) und einer von vier Konsequenzen behandelt, **bevor** ein neuer Befund aufgemacht
  wird. (2) Bei einem Rückfall wird der **bestehende** Registry-Eintrag geändert (`revised`),
  nie ein zweites Gate unter neuem Namen gebaut — ein neuer Slug spaltet den Längsschnitt
  in ein für immer rückfälliges und ein für immer unerprobtes Gate. (3) Diese Skill hatte
  als einzige der drei Session-Skills keine Abschluss-Checkliste; 6 Phasen mit
  PFLICHT-Markern ohne Abschluss-Abfrage sind genau die Ausführungstreue-Lücke aus Retro
  `c494a2` §8.
- 2026-08-20: **Phase 4 Punkt 5a — Rückfall-Prüfung** (`tools/gate_wirkung.py`) als PFLICHT
  ergänzt, plus Abfrage in der Meta-Agent-Checkliste (Phase 5). Kehrt ein Slug wieder, für den
  bereits ein Gate registriert ist, lautet der Befund **Gate rückfällig** — mit drei zulässigen
  Antworten (ausweiten/umbauen/herabstufen) statt des Slugs zum N-ten Mal. `retro_kpis.py`
  konnte das strukturell nicht zeigen: es zählt Slugs über die ganze Historie, ohne am
  Bau-Datum zu trennen.
- 2026-08-09: `repo_scope`-Form im Report-Skelett benannt (bare Slug, kein Pfad, kein
  `owner/repo`). Der Ritual-Trockenlauf vom 08.08. meldete drei Reports, deren
  Scope-Einträge `retro_kpis.py` als nicht slug-förmig verwarf (`~/.claude` ×2,
  `bahn-sqf/pg-hub`) — die Vorlage schrieb bis hierhin nur `[<repo>, …]` und ließ die
  Form offen. Quelldateien normalisiert (platform#1640-Vorbereitung Lauf 1).
- 2026-07-31 (v2.7): **Skeptiker-Auswahl nach Befund-Klasse** (Phase 0) + Folgeänderungen in
  Phase 3 und den Anti-Patterns. Bisher war das Agenten-Budget eine reine Mengenregel
  („≤5 Subagenten", „je Dimension, nicht je Befund") ohne Aussage darüber, **welche** Befunde
  eine Falsifikation überhaupt lohnen. Gemessen am Realfall
  `session-retro-2026-07-31-meiki-hub-6bd412`: von 5 Inline-Befunden waren 3 kommandobelegt
  (`grep -c`, Textvergleich, Draft-Feld) — ein Skeptiker hätte dort dieselbe Zahl geliefert,
  reiner Aufpreis. Zwei Sonnet-Skeptiker auf **nur** die 2 Bewertungsbefunde widerlegten beide
  und fanden zusätzlich einen übersehenen Befund der Severity *hoch*. Drei neue Festlegungen:
  (1) Klassentabelle kommandobelegt/Bewertungsbefund als Auswahlfilter vor Phase 3;
  (2) **gemessene** Kostengröße ~55k je eng geführtem Skeptiker statt Schätzung — die
  Vorab-Schätzung „deutlich unter 126k" war real 115k, also falsch, und ist als Anti-Pattern
  aufgenommen; (3) bei ≤2 Bewertungsbefunden ist je-Befund günstiger als die
  Dimensions-Bündelung, die Spend-Falle greift erst ab ~4. Ergänzt außerdem den Fall
  „Umgebung untersagt Subagenten": inline finden, sortieren, die weichen Befunde mit ihrer
  Zahl zur Freigabe vorlegen und nachträglich falsifizieren — statt Retro ohne Falsifikation
  oder Abbruch an der Budgetfrage. Nebenbefund derselben Messung: die Fehlerrichtung ist nicht
  vorhersagbar (erwartet wurde Selbstnachsicht, real waren beide Befunde zu streng) → der
  Skeptiker-Auftrag muss neutral formuliert sein.
- 2026-06-04: Initial. Aus einem Advocatus-Diabolus-Review des Paste-Prompt-Retros
  (`iil-prompts-retrospective`) hervorgegangen; die 4 Fixes + der Längsschnitt-Hebel sind die
  Lehren daraus. Deterministische Engine: `~/shared/session-retro.workflow.js`.
- 2026-06-04 (v2): Adversarialer Selbst-Review der Skill (Richter≠Angeklagter, geerdet am realen
  Output `session-retro-2026-06-04-platform.md`). **Fixes:** (1) **erzwungenes Report-Skelett** +
  YAML-Frontmatter + feste Spalten + Score-Rubrik (ganzzahlig, keine Halbwerte) + Action-Board →
  Längsschnitt maschinell auswertbar. (2) **Phase 3.5 Soll-Ablauf** (Ist→Soll→eliminiert-#, Invariante
  |Soll|==|Survivors|) → konstruktiv statt nur Anklage, plattitüdenfrei by construction. (3) **Phase 5
  Meta-Self-Review** (separater Agent, nur Output-Qualität) + `refuted_rate`-KPI → Selbstverbesserung
  ohne Meta-Richter≠Angeklagter-Bruch. (4) **kollisionsfreier Report-Pfad** `…-<datum>-<repo>-<session-id>.md`
  (Parallel-Sessions schreiben eigene Dateien; Default-Pfad verboten). **Methodenfixe:** Verify zieht
  Beleg unabhängig neu (nicht Finder-Befehl wiederholen — sonst überlebt False-Positive); binär
  SURVIVES/REFUTED (kein „weakened"); Belegpflicht auch für Längsschnitt-Behauptungen; Right-Sizing
  nach Befund-Dichte + harte Agenten-Budgets (lean=0 Subagenten, Skeptiker je Dimension).
- 2026-06-04 (v2.1): **Modell-Routing je Phase** (Kosten) — Subagenten auf billigstem tragenden
  Modell: Collect=haiku, Find/Verify/Meta=**sonnet** (frischer Kontext ≠ teures Opus → ~5× günstiger),
  Synthese/Report inline bei der Haupt-Session; „billiger" heißt Sonnet-Subagent, NICHT Self-Review.
  **Phase 6 Extern-Handoff** (optional, deep) — anbieter-fremde Methoden-Zweitmeinung (Muster
  `adr-handoff-extern`); harte Grenze: extern kritisiert Methode, prüft KEINE Evidenz (kein gh/git);
  wiederkehrende Kritik fließt zurück in die Skill (Self-Improvement-Loop mit externem Falsifikator).
- 2026-06-14 (v2.2): **Self-Improvement aus zwei realen Läufen am selben Tag** (Richter≠Angeklagter:
  frischer Skill-Kritiker gegen die zwei erzeugten Reports). **Fixes:** (1) **`tools/retro_kpis.py`
  gebaut** (war nur „falls vorhanden" referenziert → Längsschnitt-Hebel war fiktiv; 15 Reports lagen
  ungelesen). Stdlib-only, zählt `recurring_findings` über Retros, eskaliert ≥2 → GATE-PFLICHT; fing
  beim ersten Lauf `worktree-orphan-accumulation ×2`. Phase-4-Pflichtaufruf, „falls vorhanden"-Hedge
  entfernt. (2) **Phase 2.5 Finder-Konflikt-Erkennung** — widersprechen sich zwei Finder über einen
  Fakt, war die Auflösung still in Phase 4 (Haupt-Session zieht neues git/gh = Regel-1-Bruch; Realfall:
  ein Finder verfiel selbst in den stale-local-Fehler, den er anklagte). Jetzt: als Skeptiker-Task nach
  Phase 3, Synthesizer führt KEINE neuen Befehle aus. (3) **`refuted_rate` 3-Feld-Split** (`phase3_refuted`
  + `pre_refuted`) — Vor-Widerlegungen durch den Haupt-Kontext verfälschten das KPI. (4) **Trigger-Konflikt-
  Auflösung** (deep „Prod-Schritt" vs. Dichte-Downscale) + **Increment-Retro-Regeln** (same-day Anchor).
  (5) **Phase-5-Budget** geklärt (`full` ≤6 mit Meta) + Meta-Reviewer nur **numerisch** (kein Einzel-Befund-
  Urteil). Quelle: `~/shared/session-retro-2026-06-14-coach-hub-2d7cd9*.md` + adversarialer Skill-Kritiker.
- 2026-07-04 (v2.3): **Finder-Mandat-Satz** (Phase 2, hart): Finder/Skeptiker liefern NUR
  Befunde als Text — keine Dateien/Branches/Commits/PRs/eigene Pipelines. Realfall e17299-incr:
  ein Entscheidungs-Finder fuhr eigenmächtig Collector+Skeptiker+Report, eröffnete PR #924 auf
  dem Report-Zielpfad des Orchestrators (Partial ohne die anderen Dimensionen; mit Coverage-
  Nachweis geschlossen) und stagede die Datei im geteilten Haupt-Tree. Quelle:
  `docs/retros/session-retro-2026-07-04-platform-e17299-incr.md` §6.2/Self-Review.
- 2026-07-06 (v2.4): **Frisch-Checkout-Pflichtzeile** (Phase 3): jeder Skeptiker-Prompt beginnt
  jetzt zwingend mit `git fetch origin <default-branch>` + Prüfung gegen `origin/<branch>`.
  `stale-local-clone-as-ground-truth` war bereits ×2 gate-pflichtig (`e17299`, `a2c373`); im
  Retro `3b123e` trat es ein 3. Mal auf — diesmal innerhalb der eigenen Skeptiker-Verifikation
  dieser Skill. Quelle: `docs/retros/session-retro-2026-07-06-frist-hub-3b123e.md` Befund #8/§6.
- 2026-07-16 (v2.5): **Frisch-Checkout-Pflicht auf Phase 1 (Collect) ausgeweitet** — bisher galt
  die Zeile nur explizit für Phase-3-Skeptiker; ein lean-Footprint-Retro (kein Subagent, Inline-
  Collect) las `git log` gegen einen ungefetchten lokalen `main`, übersah 4 gemergte PRs und
  produzierte einen Befund, der beim späteren Merge-Versuch als REFUTED aufflog — 7. Instanz von
  `stale-local-clone-as-ground-truth`, diesmal in Phase 1 statt Phase 3. Quelle:
  `docs/retros/session-retro-2026-07-16-iil-klickdummy-d80d23.md` Befund #2.
- 2026-07-21 (v2.6): **Frisch-Checkout-Pflicht präzisiert (Phase 1 + Phase 3): „fetch first" reicht
  NICHT — nach dem Fetch aus dem REF lesen** (`git show origin/<branch>:<pfad>`), nicht die
  Working-Tree-Datei greppen. Fetch bewegt `origin/<branch>`, nicht den Tree; ein grep auf die lokale
  Datei liest danach weiter stale. 8. Instanz von `stale-local-clone-as-ground-truth`, diesmal INNERHALB
  eines lean-Increment-Retros dieser Skill (`8d663b-incr` I2): `grep` auf lokalem mcp-hub-Tree (HEAD
  `c092cb8`) zeigte alte Check-Zeilen trotz vorherigem `fetch`, weil origin/main (`15a1fc7`) nur den Ref
  bewegte — nur durch Content-Smell gefangen. Die bestehende Zeile („fetch first") war unvollständig:
  die Lücke ist die Lesequelle, nicht der Fetch. Memory `feedback_stale_clone_read_from_ref_not_tree_after_fetch`.
  Quelle: `docs/retros/session-retro-2026-07-21-platform-8d663b-incr.md` Befund I2.
