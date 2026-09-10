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

## ⚡ Aktueller Stand (2026-09-10 nachmittags — Auftrag #3015: K1–K3 gebaut, drei Gates revidiert, Token nach ADR-238)

**Zeitanker:** HEAD `78900e91` · `rev-list --count` 4379 · geschrieben 2026-09-10

**Auftrag [#3015](https://github.com/achimdehnert/platform/issues/3015) (Mailcheck / To-do-Liste / Morgen-Zeitung selbstmessend):** K1 Betriebsakten fuer alle drei Anwendungen ([#3054](https://github.com/achimdehnert/platform/pull/3054), [news-hub#42](https://github.com/achimdehnert/news-hub/pull/42)); K2 Messjournal je Lauf mit Trend ([#3061](https://github.com/achimdehnert/platform/pull/3061)); K3 Verfallsmelder mit zehn Signalen, Schwellen und Positivkontrolle ([#3064](https://github.com/achimdehnert/platform/pull/3064), Fehlalarm-Fix [#3065](https://github.com/achimdehnert/platform/pull/3065)). Offen: K4 Pruefskript fuer Gegenrede, K5 Drill, Waisen-Zuordnung [#3050](https://github.com/achimdehnert/platform/issues/3050), Vorgang schliessen per Kommando [#3049](https://github.com/achimdehnert/platform/issues/3049). Sachstand mit 19 Punkten und Checkliste im Issue.

**Retro der Sitzung** ([#3048](https://github.com/achimdehnert/platform/pull/3048), Footprint full, 22 Befunde, 19 ueberlebt, 4 gekippt / 4 neu in der Widerlegungsbahn): drei Gates revidiert statt neu gebaut ([#3063](https://github.com/achimdehnert/platform/pull/3063)) — aufschub-anker liest Issue-Kommentare ([#3059](https://github.com/achimdehnert/platform/pull/3059)), repo-session start zeigt offene PRs des Tages ([#3057](https://github.com/achimdehnert/platform/pull/3057)), serielle-prs-Abgleich beim PR ([#3062](https://github.com/achimdehnert/platform/pull/3062)). Das Anker-Gate fing am selben Tag zwei eigene PRs. Token im Auslagerungs-Gate von PROJECT_PAT auf App-Token nach ADR-238 ([#3056](https://github.com/achimdehnert/platform/pull/3056)), Positivkontrolle gruen; Wirkungsnachweis im Echtfall bleibt [#3027](https://github.com/achimdehnert/platform/issues/3027).

**Eigene Fehler, korrigiert:** Alias statt Dienst (#3024→#3039), Betreff in Fixture (#3054), Melder-Fehlalarm (#3065).

**Offen (Owner):** nichts Neues — alle Governance-PRs des Tages sind approved und gemergt.

## ⚡ Stand (2026-09-10 nachmittags — Scan-Strecke geschlossen, Archiv aufgeraeumt)

**Scan-Strecke** ([doc-hub#3](https://github.com/achimdehnert/doc-hub/issues/3), geschlossen): der Melder deckt jetzt drei Faelle ab — liegt zu lange (Exit 1), verschwindet ohne Dokument (Exit 4), Aufnahme scheitert (Exit 5, [#3017](https://github.com/achimdehnert/platform/pull/3017)); eine Dublette meldet sichtbar, aber stumm ([#3029](https://github.com/achimdehnert/platform/pull/3029)). **Nicht** ueber `full_audit` auf der Samba-Freigabe — der Weg blieb nach der Vier-Neustarts-Episode zurueckgebaut. Exit 4 hat erstmals an einem echten Ereignis gefeuert ([#3026](https://github.com/achimdehnert/platform/issues/3026), aufgeklaert).

**Archiv aufgeraeumt** (Owner-Auftrag „Vorschlaege zur Optimierung"): ohne Besitzer 546 -> 0, ohne Absender 1149 -> 829, Titel nur Scannernummer 244 -> 91, Absender 30 -> 49, Stichwoerter 114 -> 99. Ursachen: das Ablage-Skript suchte ein Konto `achim`, das es nie gab; und 28 gepflegte Suchbegriffe standen auf „automatisch", wo der Klassifikator bei 30 Absendern auf 211 Beispielen nichts liefert (Gegenprobe ueber Stichwoerter liefert Treffer). Die Skript-Aenderungen liegen NUR auf prod (`/opt/doc-hub/scripts/auto-title.py`, Sicherung `.bak-20260910`) — bekannte Luecke.

**Zwei eigene Fehler, behoben:** `docker exec` ohne `-u paperless` legte 153 Dateien als root an (Suchindex + Ablage), danach scheiterte jeder Einzug und ein echter Scan blieb liegen. Und `scan-melder.yml` schrieb seinen Marker mit Leerzeichen, waehrend `cron_melder_check.py` exakt `ROT-IST-BEFUND` sucht — er wirkte dort nie. Beides in [#3055](https://github.com/achimdehnert/platform/pull/3055), zusammen mit dem woechentlichen Rueckstau-Melder (Posteingang 331, Pruefstapel 57, meldet nur Wachstum).

**Zugang:** Access-Liste fuer `docs.iil.pet` traegt jetzt Firmen- und Hochschul-Adresse plus zwei weitere Personen. Analysen und Rueckweg-Listen liegen in `~/shared/docs-hub/`; offen bleibt [doc-hub#18](https://github.com/achimdehnert/doc-hub/issues/18) (zwei Konten anderer Personen).

**Zielzustand:** erreicht fuer alle freigegebenen Punkte. **SA-4:** 0 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen.

## Offene Fäden (über den Session-Stand hinaus)

0. iil-assist Gateway MVP 1: Prod-Freigabe fuer PR #263 offen: https://github.com/achimdehnert/mcp-hub/issues/264

0. Auftrag #3015 (Mailcheck, To-do, Morgen-Zeitung selbstmessend) laeuft, Stand im Archiv vom 2026-09-10: https://github.com/achimdehnert/platform/issues/3015
0. iil-assist (KONZ-058): Rundlauf im Chat belegen (O5), dann MVP 2 Dokument-Suche; Nebenissues #3019 PyPI, #3020 Regelkreis, #3021 Routing, #3022 ADR-036: https://github.com/achimdehnert/platform/issues/3011
0. netcup antwortet mit fremdem Host-Key, Backup-Cron zielt weiter dorthin, Vertrag offen: https://github.com/achimdehnert/platform/issues/2950
0. dev-hub Staging-Deploy vorbestehend kaputt (Kein Compose-File): https://github.com/achimdehnert/dev-hub/issues/348
0. Paperless `PAPERLESS_FILENAME_DATE_ORDER` setzen: https://github.com/achimdehnert/doc-hub/issues/15
0. Stapel-Zerleger im Betrieb, Zielzustand-Issue noch offen: https://github.com/achimdehnert/doc-hub/issues/4 — Bauteile gemergt (doc-hub#5, doc-hub#13, doc-hub#14).
0. Freigabe-Zeile je Prod-Schritt als Regel bestaetigen — aus dem Stand vom 2026-09-09 abends gerettet (Owner-Entscheid).

- **[2982]** Retro 136735: sieben ueberlebende Befunde ohne Umsetzungsartefakt — beim Auslagern der Sektion vom 2026-09-08 hierher gerettet — https://github.com/achimdehnert/platform/issues/2982
- **[3015]** Auftrag Mailcheck/To-do/Zeitung selbstmessend (SA-4): Sachstand mit 12 Befunden im Issue; nach Merge von #3042 `mail-links.service` und `todo-board.service` neu starten (Owner) — https://github.com/achimdehnert/platform/issues/3015
- **[3027]** Auslagerungs-Gate liest Fremd-Repos jetzt per Flotten-Token; schliesst erst, wenn eine Auslagerung mit Fremd-Refs im Gate gruen laeuft — https://github.com/achimdehnert/platform/issues/3027
- **[news-hub#33]** Morgen-Zeitung: Themenauswahl kuert generische Woerter — beim Auslagern der Sektion vom 2026-09-09 vormittags hierher gerettet — https://github.com/achimdehnert/news-hub/issues/33
- **[news-hub#40]** Morgen-Zeitung: Smoke-Lauf im CI, Entwurf steht — beim Auslagern gerettet — https://github.com/achimdehnert/news-hub/issues/40
- **[news-hub#19]** Morgen-Zeitung: NIS2 und Voice Agents ohne Quelle, Robotik und IoT belegt — beim Auslagern gerettet — https://github.com/achimdehnert/news-hub/issues/19
- **[3001]** memory-link-guard meldet einen intakten Wikilink als tot (Lane-Verwechslung) — beim Auslagern der Sektion vom 2026-09-09 vormittags hierher gerettet — https://github.com/achimdehnert/platform/issues/3001
Je eine Zeile mit Link, kein Verlauf. Frisches steht oben im Stand-Block, Historie in
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md). Jede Zeile zeigt auf ein
**offenes** Issue — ist es geschlossen, gehört sie ins Archiv, nicht hierher.

0. Scan-Strecke: Melder deckt liegengeblieben, verschwunden und fehlgeschlagen ab; Restluecke benannt, Vorgang geschlossen: https://github.com/achimdehnert/doc-hub/issues/3
0. Auslagern verlor drei Faeden nach #2967 — Befund zum Gate selbst: https://github.com/achimdehnert/platform/issues/2974
0. Gate-Registry-Eintrag `handover-auslagerung-verschluckt-offenes` wartet auf Owner-Wort (`docs/governance/`): https://github.com/achimdehnert/platform/pull/2984
0. Morgen-Zeitung: Themenauswahl kuert generische Woerter, Smoke-Lauf offen: https://github.com/achimdehnert/news-hub/issues/33
1. KONZ-054 Systembild, Kill-Gate 2026-10-15; Owner-Punkte #2486/#2504/#2507, Reste #2480: https://github.com/achimdehnert/platform/issues/2516
2. KONZ-051 ux-review-agent, Kill-Gate 2026-09-30; K1 3/9, K3 offen: https://github.com/achimdehnert/writing-hub/issues/766
3. Volume-Deckung prod (40 Volumes), K2 = Owner-Gate, Löschliste #2258: https://github.com/achimdehnert/platform/issues/2300
4. KONZ-052-Rest: `PYPI_API_TOKEN` löschen (Owner-Wort, dann #1904 zu), Erstrelease iil-enrichment/gaeb-toolkit: https://github.com/achimdehnert/platform/issues/2380
5. PyPI-Konto `achimdehnert`: Org `iil` ist geloescht (404), die Kontoloeschung scheitert an PyPI selbst; Owner sendet den Support-Entwurf (Ledger 196), Wiedervorlage 14.09.: https://github.com/achimdehnert/platform/issues/2291#issuecomment-5573303982
6. Gate-Deckung: 11 Slugs gedeckt/Verzicht per #2909 (38 %), 4 Verzichte bestätigen: https://github.com/achimdehnert/platform/issues/2234
7. Wirksamkeits-Bilanz der Gates: 6 rückfällige per #2909 behandelt, Hook-Verdrahtung #2907: https://github.com/achimdehnert/platform/issues/2374
8. Concurrency je Ziel-Umgebung: 13 gleichlautende PRs in der Flotte offen: https://github.com/achimdehnert/platform/issues/2229
9. `deploy_wirkung`-Restbefunde; travel-beat weiter RUECKSTAND (gewollt), illustration-hub → illustration-hub#344; NEU: Route ohne Deklaration (molkerei.iil.pet lief undeklariert auf staging-dedicated) — Cloudflare-DNS gegen ports.yaml abgleichen: https://github.com/achimdehnert/platform/issues/2148
10. risk-hub: Staging grün nach litellm-OOM-Fix (#743), Prod-Gate des Dispatch-Laufs 34101567220 = Owner-Klick; Repo liegt in `iilgmbh`: https://github.com/iilgmbh/risk-hub/issues/729
11. Rollende Melder legen an statt zu aktualisieren, ~38 Kandidaten: https://github.com/achimdehnert/platform/issues/2140
12. shared-ci-Bänder: App-Repos v1.1.10 ×17 / v1.0.11 ×2, `ttz-lif`+`meiki-lra` ungemessen: https://github.com/achimdehnert/platform/issues/2087
13. ADR-Zweitmeinungen ohne Rückkanal, 19 von 24 ohne Antwort: https://github.com/achimdehnert/platform/issues/2088
14. `hygiene_melder.py` meldet invertiert (Footer mitgehasht), drei Phasen dieselbe Wurzel: https://github.com/achimdehnert/platform/issues/2054
15. Public→Private Welle 1: Owner-Freigabe fehlt, F entsperrt ADR-255: https://github.com/achimdehnert/platform/issues/2119
17. ADR-242 Wave 3: Phase-2-Rest, Apply-Artefakt fehlt: https://github.com/achimdehnert/platform/issues/811
18. CI-Runner `ci-gpu` auf eigenen Server (braucht keine GPU), Kosten = Owner-Wort: https://github.com/achimdehnert/platform/issues/2543
19. GX10: gemessen, `NUM_PARALLEL=4` + vLLM-Dienst stehen; offen: Verbraucher umhaengen (mcp-hub#262 blockiert): https://github.com/achimdehnert/platform/issues/2544
20. GX10-Training: 4090 bleibt fuehrend bis 16.384 Umgebungen, darueber traegt nur der GX10: https://github.com/achimdehnert/robo-lab/issues/58
52. Port-Register: drei Dienst-Ausnahmen waren ungelesen, PR offen: https://github.com/achimdehnert/platform/pull/2977
53. Kaufberatung zweites Geraet — Empfehlung abgelegt, Kenntnisnahme offen: https://github.com/achimdehnert/platform/issues/2978
21. Mail-Ansicht: leerer Körper braucht „Inhalt im Anhang": https://github.com/achimdehnert/platform/issues/2597
22. Owner: die 20 mechanisch gesetzten `frist_grund`-Texte auf `todo.iil.pet` sichten (Spalte Frist) — mechanisch je Bucket gesetzt, nicht redigiert.
23. Megatest-Erstlauf, 15 Befunde unbearbeitet und ohne Tracking-Issue ([Lauf 30619024656](https://github.com/achimdehnert/platform/actions/runs/30619024656), 2026-08-02) — vor Wiederaufnahme neu messen.
24. Gegenprobe Wochenlauf `ttz-hub`: beim nächsten Lauf, der ttz-hub wirklich ändert, müssen Checks am erzeugten PR erscheinen (kein Issue).
25. Session-Skills modellfest (#2690): Drill-Vorlage #2719, Backfill Positivkontrolle #2703, Ruleset-Entscheid bis 2026-10-02: https://github.com/achimdehnert/platform/issues/2690
26. #2750 K4/K5-Bilanz, sobald das Ledger 5 Fable-Sessions nach 2026-09-03 trägt (Stand 2); K5-Basisdefinition = Owner-Wort: https://github.com/achimdehnert/platform/issues/2750
27. Orchestrator-MCP-Schlüssel rotiert 2026-09-03: andere Maschinen prüfen, toter Block in settings.json: https://github.com/achimdehnert/platform/issues/2769
28. Future-Readiness: **Basislinie 07.09. (Median 55) ist UNGUELTIG** — der Bewerter urteilte an drei Stellen systematisch falsch (#2965 gemergt). Neu GERECHNET aus denselben 56 Evidenzpaketen, keine Neu-Erhebung noetig: Median 58, Deckung 0,439 (dev-hub#344, offen). Offen: zwei Querschnitts-Befunde aus dem Eich-Bogen — Erhebung liest `lifecycle` statt `deployed`/`archived`, und eine fehlende Agent-Datei zaehlt fuenfmal statt einmal (29 von 30 Repos gemessen): https://github.com/achimdehnert/platform/issues/2737
29. Evidenz-Generator-Rest (Rate-Limit-Vorabcheck, visibility-Check); Werkzeuge #2767 gemergt, #2782 offen: https://github.com/achimdehnert/platform/issues/2736
30. Mail-Signatur im HTML-Pfad von send_mail/graph_mail (draft_mail gefixt #2830; 3 HNU-Mails am 04.09. ohne Signatur): https://github.com/achimdehnert/platform/issues/2831
31. travel-beat: Gate #98 gemergt (App aus); staging-Runner-Unit `actions.runner.achimdehnert-travel-beat.travel-beat-staging-ci.service` (dev-desktop) braucht sudo-Start; #94 jetzt gefahrlos: https://github.com/achimdehnert/travel-beat/issues/95
32. ADR-262 Frontmatter nach Welle 1 (7 Repos umgesetzt, Status not-started): https://github.com/achimdehnert/platform/issues/2770
34. Speicher-Melder baut den Hop-Zugang noch selbst, Rest aus #2783: https://github.com/achimdehnert/platform/issues/2802
35. Mailcheck-Ablage: K8 gemergt (#2897, `--pruefe` nennt `kein_anker` mit Anker-Kommando); Rest: 146/167/172 (iil, keine UID) und 179 (hnu) verankern, IIL-Referenz in `eintrag_anker.py` (Hypothese Index-ID ≠ UID): https://github.com/achimdehnert/platform/issues/2799
36. Zug A 51/56 gemessen; ohne: coach-hub#70, bahn-hub#19, risk-hub#729, infra-deploy#7, dev-hub (44); Folgebefunde #2827, mcp-hub#251, meiki-dms#19: https://github.com/achimdehnert/platform/issues/2787
37. Aufschub-Anker-Gate: Fehlalarm-Klasse „nicht ausgewertet/bewusst nicht“ in Code-Kommentaren, 3× am 2026-09-04: https://github.com/achimdehnert/platform/issues/2606
38. Sitzung 6e320e79 (Mailcheck/DSGVO/EPIC): `load_credentials` beendet den Prozess statt zu werfen — Wurzel hinter #2755; Ledger #185–#188 offen, Papiere `~/shared/retentionsscanner/`: https://github.com/achimdehnert/platform/issues/2752
39. apo-hub ruhend, DEPLOY_ENABLED=false; Schluesselrotation erst bei Reaktivierung: https://github.com/achimdehnert/apo-hub/issues/82
40. `Bash(gh pr merge:*)` global in autoMode.allow — zurueckbauen oder als Gate verankern (Owner): https://github.com/achimdehnert/platform/issues/2834
41. shared-ci v1.1.15 gesetzt (#73 zu); 42 Konsumenten bumpen, writing-hub zuerst, Liste mit Versionen: https://github.com/iilgmbh/shared-ci/issues/77
45. molkerei-landing archiviert 2026-09-07, DELETE Human-Only ab 2026-10-07 (Kommando im Tombstone): https://github.com/achimdehnert/platform/issues/2914
44. memory-link-guard prüft alle Memory-Lanes und meldet fremde Sitzung als eigenen Zug: https://github.com/achimdehnert/platform/issues/2870
46. robo-lab Kill-Gate Zeile 1 ohne Zahl (Regler am symmetrischen Modell optimiert), Frist 2026-11-30: https://github.com/achimdehnert/robo-lab/issues/66
47. robo-lab Messjournal: 23 von 63 Eintraegen mit toten Herkunftszeigern: https://github.com/achimdehnert/robo-lab/issues/81
48. bahn-hub-Anker im Journal zeigt auf die falsche Nummer (richtig #2899): https://github.com/achimdehnert/platform/issues/2504
49. Clear-Haerte: wg0-Restschritte und Rohdaten-Verzicht nachtragen: https://github.com/achimdehnert/platform/issues/2895
50. Evidenz-Hook Rev 6: Mail-Entwuerfe per --body-file, advisory statt blockend: https://github.com/achimdehnert/platform/issues/2924
51. template-drift meldet 'kein Repo erreichbar', Ursache offen (gh api antwortet): https://github.com/achimdehnert/platform/issues/2940
54. Dependency-Update-Automation einschalten: https://github.com/achimdehnert/billing-hub/issues/52
55. Code Scanning per CodeQL einschalten: https://github.com/achimdehnert/odoo-hub/issues/32
56. ADR-228 accepted, aber nie gebaut — Regelfolger benennen: https://github.com/achimdehnert/platform/issues/2931
57. Future-Readiness an vorhandene Melder anschliessen: https://github.com/achimdehnert/platform/issues/2944
58. Vier Funktionen ohne Verwendung im Produktivpfad: https://github.com/achimdehnert/platform/issues/2961
59. 14 accepted-ADRs ohne Umsetzungsvermerk: https://github.com/achimdehnert/platform/issues/2962
60. Melder-Ergebnisdatei wird nicht uebergeben: https://github.com/achimdehnert/platform/issues/2969

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
