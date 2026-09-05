# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents** — MCP-Tool-Mappings,
Infra-Zugänge, Deploy-Targets, Scripting-Referenz (jetzt in `docs/AGENT_HANDOVER_REFERENZ.md`). **Arbeitsstand, nicht Archiv:**
jedes Byte hier kostet Kontext in *jeder* Sitzung.

<!-- KONVENTION — gilt fuer JEDE H2-Sektion, nicht nur fuer "## ⚡"-Bloecke:
     Stand-Bloecke: aktueller + hoechstens EIN vorheriger, soweit der Deckel es traegt.
     Jede andere Sektion haelt nur, was heute handlungsleitend ist; sobald sie Verlauf
     ansammelt (erledigte Punkte, "Fortschritt <Datum>", Reconciliation-Vermerke),
     wandert sie als GANZES nach AGENT_HANDOVER_ARCHIVE.md — dort ANHAENGEN mit
     Datumsmarke und Herkunftszeile, nichts loeschen, und Offenes vorher als Kurzzeile
     nach "## Offene Fäden" retten. Details unten: "## Konventionen dieser Datei". -->

**Archiv älterer Stände und ausgelagerter Sektionen:**
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md).

## ⚡ Aktueller Stand (2026-09-04 früh — Mailcheck-Ablage wieder scharf (#2799 K7: 18 Mails), Zug A Welle gemergt, Future-Readiness v2.4 + Neulauf, SA-M Deploy-Vermerk)

**Zeitanker:** HEAD `4c36b81e` · `rev-list --count` 4122 · geschrieben 2026-09-04

**Zielzustand (Owner-Worte 2026-09-04 „21 bis 28 go" — Board-Nummern der Sitzung: 21 writing-hub#1008 · 22 #2784 · 23 #2783 · 24 #2737 v2.4 · 25 Zug-A-Welle · 26 dev-hub#325 · 27 Repos ohne Prod-Deploy · 28 Mailcheck-Archiv; später „24 30 go, 37a ja" = #2803 mergen, Neulauf, Schwelle · „37 (b)" = #2812 — + Ziel 28: „mailcheck verschiebt erledigte Mails ins Archiv und bleibt trotzdem mit allen Referenzen auf Mails aktuell; der Posteingang hat keine erledigten Mails mehr" → [#2799](https://github.com/achimdehnert/platform/issues/2799)): K1–K6 **erreicht** ([#2804](https://github.com/achimdehnert/platform/pull/2804) + Nachzug [#2809](https://github.com/achimdehnert/platform/pull/2809)), K7 **teilweise → verschoben mit Anker** (Fremdabnahme 0h: scharfer Lauf 18 Mails, Quelle/Ziel beidseitig gezählt, 15 Anker nachgezogen, 0 tot, 0 neue tote Links — aber Melder danach hnu 1 / iil 0, nicht 0/0; Rest 3 Vorgänge ohne Anker, 1 ohne Strang, 1 hnu-Mail → Faden 35, nächster /mailcheck). Wurzel: seit 27.08. lief die Ablage nie, weil die Ordnerliste ein Pflichtargument war, das der Skill nicht mitgab (dritter Vorfall).**

**Gemergt (11 PRs, 3 Repos + Flotte).** writing-hub Doku-Filter ohne `gh`, fail-closed bei Konfigurationslücken ([writing-hub#1009](https://github.com/achimdehnert/writing-hub/pull/1009)); Gegenprobe bestanden: Doku-Merge [#1012](https://github.com/achimdehnert/writing-hub/pull/1012) → „kein Prod-Deploy", Production skipped · `pr_merge_sa` jüngster Lauf je Check ([#2798](https://github.com/achimdehnert/platform/pull/2798)) · Hop-Helfer `tools/hostzugang.{py,sh}` ([#2801](https://github.com/achimdehnert/platform/pull/2801), Rest [#2802](https://github.com/achimdehnert/platform/issues/2802)) · Future-Readiness v2.4 Regelbilanz 39 Zeilen + Phase-C-Portfolio ([#2803](https://github.com/achimdehnert/platform/pull/2803)), 37a-Schwelle ([#2805](https://github.com/achimdehnert/platform/pull/2805)), Neulauf 56/56 Rubrik 2.4 ([dev-hub#326](https://github.com/achimdehnert/dev-hub/pull/326): Median 53, 53 P1 in 34 Repos, 27 Repos verschoben) + Portfolio v2.4 ([#2808](https://github.com/achimdehnert/platform/pull/2808)) · SA-M: Deploy-Vermerk je PR-Nummer deckt W3 als M3 ([#2814](https://github.com/achimdehnert/platform/pull/2814), Owner-Entscheid (b) in [#2812](https://github.com/achimdehnert/platform/issues/2812)).

**Zug A Welle:** 8 von 9 Push-Deploy-PRs gemergt (Owner-Klick), 7 Deploys grün, tax-hub Staging grün/Production vor Prod-Gate; travel-beat#96 wartet auf Runner. 36 Repos ohne Prod-Deploy hatte eine Parallelsitzung schon bearbeitet (Kommentare 04:19/04:28 in #2787); 9 CI-rote Repos für den Nachzug dort gelistet.

**Befunde:** M3 per Review auf eigenen PRs unerreichbar (GitHub verbietet Self-Approve) → (b) umgesetzt · Aufschub-Anker-Gate feuert auf „nicht ausgewertet"/„bewusst nicht" in Code-Kommentaren (3× heute, Fehlalarm-Klasse für #2606) · zwei PRs mergte der Owner, bevor die Nachbesserung drin war (#2803→#2805, #2804→#2809) · eigener Fehler: leere Worktree-Pfadvariable (Skript schreibt auf stderr) ließ einen Cherry-pick im Haupt-Tree laufen — sofort abgebrochen, HEAD unverändert (Memory 🌀).

**Nächster Schritt:** /mailcheck mit Schritt 7a scharf (Melder `--pruefe` 0/0 anstreben; hnu-Restmail sichten); #2737: K5-Bilanz Vorher/Nachher aus dem v2.4-Stand, Owner-Fragen zu v2.4-Neulauf-Deltas; #2802 Speicher-Melder auf Helfer; travel-beat Runner.

**SA-4:** 0 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen. SA-M: 3 Merges per Mandat (#2805 W1/M1, #2808 W1/M1, beide nach Freigabe-Vermerk im Issue-Body #2737), 8 W3-Merges durch den Owner. Delegation: 7 Subagenten nach Brief (4 Sonnet, 3 Opus; Prüfung + Fixes inline), Session `ac4fb7c7`.

**0h Fremdabnahme (Fortsetzung 01Lob9, 2026-09-04):** Zug-A-Rest + 171 **erreicht** (51/56 selbst gezaehlt, Staffelung ≤ 2/h, Deploys success, Vorfall zurueckgesetzt, Tag = #76, Bypass mit Freigabe); Z7 teilweise — zwei Anker im #2787-Text falsch, korrigiert (bahn-hub#19, risk-hub#729). 0e: drei JA, hier nachgezogen (Faeden 31/36/39/40); Faden 38 = Parallelsitzung. Runner: E.1 coach-hub#70, E.5/E.6 Luecke.

**Parallelsitzung e412c7f5 (Lotsen-Tagesbetrieb, 2026-09-04):** MEiKI-Angebotseinholung prodactive über HNU (Maier; Liefergegenstand = Konzept zur Entwicklung der App „Fristenmanagement", 5 PT, max 1.300 €/Tag; Konzept-PDF als Anhang raus) · Omnia Suite (EGovC) vs. Bürgerportal analysiert ([meiki-hub#237](https://github.com/meiki-lra/meiki-hub/pull/237)), fünf Prüffragen an LRA GZ vor Termin 11./14.09. · Ledger: 175 Hoffmann-Löschung komplett (risk-hub prod DR 2 → closed, ohne Mail; Lehre: RLS ohne `set_db_tenant` = 0 Zeilen), 156/168/124/177 gesendet bzw. zu, 185 Anhang 3 fehlt im Postfach (Schmalberger erbeten), 190 Fiverr-Gigs (6 Vorschläge, Owner recherchiert) · Schreibstil-Regel Angebotsanfrage ([#2811](https://github.com/achimdehnert/platform/pull/2811)) · draft_mail-Signatur-Bug ([#2830](https://github.com/achimdehnert/platform/pull/2830), Rest Faden 30) · Paperless: Tag Sozialversicherung als Keyword-Regel, 22 Dokumente nachgetaggt; Dok 2350 auf 2026, Duplikat 2353 gelöscht. 0d fremd: 8/8 erfüllt. Runner: E.1 coach-hub 33237648563 (fremd), E.6 13 Drift-Errors (vorbestehend), E.3 sucht `docs/AGENT_HANDOVER.md` — platform hat sie im Root (Runner-Lücke).

## Offene Fäden (über den Session-Stand hinaus)

Je eine Zeile mit Link, kein Verlauf. Frisches steht oben im Stand-Block, Historie in
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md). Jede Zeile zeigt auf ein
**offenes** Issue — ist es geschlossen, gehört sie ins Archiv, nicht hierher.

1. KONZ-054 Systembild, Kill-Gate 2026-10-15; Owner-Punkte #2486/#2504/#2507, Reste #2480: https://github.com/achimdehnert/platform/issues/2516
2. KONZ-051 ux-review-agent, Kill-Gate 2026-09-30; K1 3/9, K3 offen: https://github.com/achimdehnert/writing-hub/issues/766
3. Volume-Deckung prod (40 Volumes), K2 = Owner-Gate, Löschliste #2258: https://github.com/achimdehnert/platform/issues/2300
4. KONZ-052-Rest: `PYPI_API_TOKEN` löschen (Owner-Wort, dann #1904 zu), Erstrelease iil-enrichment/gaeb-toolkit: https://github.com/achimdehnert/platform/issues/2380
5. PyPI-Org `iil`: Support-Antwort, Frist 2026-09-08, danach Konto härten: https://github.com/achimdehnert/platform/issues/2291
6. Gate-Deckung: 11 ungedeckte Slugs, 28 %: https://github.com/achimdehnert/platform/issues/2234
7. Wirksamkeits-Bilanz der Gates: gemessen, Konsequenz je Gate offen: https://github.com/achimdehnert/platform/issues/2374
8. Concurrency je Ziel-Umgebung: 13 gleichlautende PRs in der Flotte offen: https://github.com/achimdehnert/platform/issues/2229
9. `deploy_wirkung`-Restbefunde: https://github.com/achimdehnert/platform/issues/2148
10. risk-hub hängt >26 Commits zurück (DSB-Tätigkeitsnachweis), Migrationen additiv geprüft — deployen, sobald auf `main` nicht mehr gearbeitet wird; Repo liegt in `iilgmbh`.
11. Rollende Melder legen an statt zu aktualisieren, ~38 Kandidaten: https://github.com/achimdehnert/platform/issues/2140
12. shared-ci-Bänder: App-Repos v1.1.10 ×17 / v1.0.11 ×2, `ttz-lif`+`meiki-lra` ungemessen: https://github.com/achimdehnert/platform/issues/2087
13. ADR-Zweitmeinungen ohne Rückkanal, 19 von 24 ohne Antwort: https://github.com/achimdehnert/platform/issues/2088
14. `hygiene_melder.py` meldet invertiert (Footer mitgehasht), drei Phasen dieselbe Wurzel: https://github.com/achimdehnert/platform/issues/2054
15. Public→Private Welle 1: Owner-Freigabe fehlt, F entsperrt ADR-255: https://github.com/achimdehnert/platform/issues/2119
17. ADR-242 Wave 3: Phase-2-Rest, Apply-Artefakt fehlt: https://github.com/achimdehnert/platform/issues/811
18. CI-Runner `ci-gpu` auf eigenen Server (braucht keine GPU), Kosten = Owner-Wort: https://github.com/achimdehnert/platform/issues/2543
19. GX10: Mehrbenutzer-Durchsatz ungemessen, beide gemessenen Motoren sind Einzelstrom: https://github.com/achimdehnert/platform/issues/2544
20. GX10 als zweites Trainingsgerät, K4 Vergleichslauf 4090 ↔ GX10: https://github.com/achimdehnert/robo-lab/issues/58
21. Mail-Ansicht: leerer Körper braucht „Inhalt im Anhang": https://github.com/achimdehnert/platform/issues/2597
22. Owner: die 20 mechanisch gesetzten `frist_grund`-Texte auf `todo.iil.pet` sichten (Spalte Frist) — mechanisch je Bucket gesetzt, nicht redigiert.
23. Megatest-Erstlauf, 15 Befunde unbearbeitet und ohne Tracking-Issue ([Lauf 30619024656](https://github.com/achimdehnert/platform/actions/runs/30619024656), 2026-08-02) — vor Wiederaufnahme neu messen.
24. Gegenprobe Wochenlauf `ttz-hub`: beim nächsten Lauf, der ttz-hub wirklich ändert, müssen Checks am erzeugten PR erscheinen (kein Issue).
25. Session-Skills modellfest (#2690): Drill-Vorlage #2719, Backfill Positivkontrolle #2703, Ruleset-Entscheid bis 2026-10-02: https://github.com/achimdehnert/platform/issues/2690
26. #2750 K4/K5-Bilanz, sobald das Ledger 5 Fable-Sessions nach 2026-09-03 trägt (Stand 2); K5-Basisdefinition = Owner-Wort: https://github.com/achimdehnert/platform/issues/2750
27. Orchestrator-MCP-Schlüssel rotiert 2026-09-03: andere Maschinen prüfen, toter Block in settings.json: https://github.com/achimdehnert/platform/issues/2769
28. Future-Readiness: K5-Bilanz aus v2.4-Neulauf (dev-hub#326), Deltas 27 Repos = Owner-Fragen: https://github.com/achimdehnert/platform/issues/2737
29. Evidenz-Generator-Rest (Rate-Limit-Vorabcheck, visibility-Check); Werkzeuge #2767 gemergt, #2782 offen: https://github.com/achimdehnert/platform/issues/2736
30. Mail-Signatur im HTML-Pfad von send_mail/graph_mail (draft_mail gefixt #2830; 3 HNU-Mails am 04.09. ohne Signatur): https://github.com/achimdehnert/platform/issues/2831
31. travel-beat: Gate #98 gemergt (App aus); staging-Runner-Unit `actions.runner.achimdehnert-travel-beat.travel-beat-staging-ci.service` (dev-desktop) braucht sudo-Start; #94 jetzt gefahrlos: https://github.com/achimdehnert/travel-beat/issues/95
32. ADR-262 Frontmatter nach Welle 1 (7 Repos umgesetzt, Status not-started): https://github.com/achimdehnert/platform/issues/2770
33. session_ende_checks.sh E.3/E.5 blind für platform (Pfad statt Repo-Name): https://github.com/achimdehnert/platform/issues/2773
34. Speicher-Melder baut den Hop-Zugang noch selbst, Rest aus #2783: https://github.com/achimdehnert/platform/issues/2802
35. Mailcheck-Ablage: Rest 3 Vorgänge ohne Anker, 1 ohne Strang, hnu 1 offene Mail; Melder `--pruefe` in `make boards`: https://github.com/achimdehnert/platform/issues/2799
36. Zug A 51/56 gemessen; ohne: coach-hub#70, bahn-hub#19, risk-hub#729, infra-deploy#7, dev-hub (44); Folgebefunde #2827, mcp-hub#251, meiki-dms#19: https://github.com/achimdehnert/platform/issues/2787
37. Aufschub-Anker-Gate: Fehlalarm-Klasse „nicht ausgewertet/bewusst nicht“ in Code-Kommentaren, 3× am 2026-09-04: https://github.com/achimdehnert/platform/issues/2606
38. Sitzung 6e320e79 (Mailcheck/DSGVO/EPIC): `load_credentials` beendet den Prozess statt zu werfen — Wurzel hinter #2755; Ledger #185–#188 offen, Papiere `~/shared/retentionsscanner/`: https://github.com/achimdehnert/platform/issues/2752
39. apo-hub ruhend, DEPLOY_ENABLED=false; Schluesselrotation erst bei Reaktivierung: https://github.com/achimdehnert/apo-hub/issues/82
40. `Bash(gh pr merge:*)` global in autoMode.allow — zurueckbauen oder als Gate verankern (Owner): https://github.com/achimdehnert/platform/issues/2834
41. shared-ci v1.1.15 gesetzt (#73 zu); 42 Konsumenten bumpen, writing-hub zuerst, Liste mit Versionen: https://github.com/iilgmbh/shared-ci/issues/77

## Konventionen dieser Datei

**Rotation:** aktueller Stand + höchstens ein vorheriger; jede andere H2-Sektion nur,
solange sie handlungsleitend ist. Verlauf wandert als Ganzes ins Archiv (anhängen,
Datumsmarke, Herkunftszeile), Offenes vorher nach „## Offene Fäden" retten. In der
Praxis trägt der Deckel meist nur **einen** Stand-Block: wer einen neuen schreibt,
lagert den alten im selben Zug aus.

**Byte-Deckel 20.000** — `python3 scripts/checks/handover_byte_cap.py`, als Gate im
Workflow `handover-append-only` an jedem PR. Reißt er, wird ausgelagert, nicht der
Deckel angehoben. Anlass: am 2026-09-02 war die Datei 116.116 B, davon 85 % nie
ausgelagerte Historie ([#2606](https://github.com/achimdehnert/platform/issues/2606)).

### Zeitanker — Pflicht je Stand-Block

Jeder `## ⚡ Aktueller Stand`-Block trägt **als erste Zeile** einen Zeitanker: die
Werte, gegen die eine frische Instanz in **einem** Kommando prüfen kann, ob dieser
Text noch den Stand beschreibt oder hinterherhinkt.

```
**Zeitanker:** HEAD `<sha7>` · `rev-list --count` <n> · geschrieben <YYYY-MM-DD>
```

Prüfen (ein Kommando, read-only):

```bash
git fetch -q origin && echo "ist: $(git rev-parse --short origin/main) / $(git rev-list --count origin/main)"
```

**Weicht der Ist-Wert ab, ist der Block veraltet — nicht falsch, aber überholt.** Das ist
die einzige Aussage, die der Anker trägt; er ersetzt kein Lesen. Fehlt ein Wert, wird
`nicht erhoben` eingetragen — **nie** ein geschätzter.

Warum: Ohne Anker war „hinkt der Handover nach?" nur durch Lesen beantwortbar, und das
unterblieb — Realfall 2026-07-15, drei konkurrierende Handover-PRs nebeneinander
(`session-retro-2026-07-15-platform-c494a2`). Übernommen aus dem Fremdsystem SB-Neu, wo
derselbe Anker eine Sechs-Commit-Drift in einer Sekunde sichtbar machte.

## Referenz (ausgelagert)

Die statischen Nachschlage-Abschnitte 1–7 (MCP-Server & Tool-Calls, Hetzner-Infrastruktur, Deploy-Targets, Master-Repo-Kennungen, CC-Skills & Windsurf-Rules, GitHub, pgvector-Memory) stehen seit 2026-09-04 in [`docs/AGENT_HANDOVER_REFERENZ.md`](docs/AGENT_HANDOVER_REFERENZ.md) (Owner-Entscheid, platform#2606). Hier bleibt nur Arbeitsstand.
