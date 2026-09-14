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

## ⚡ Aktueller Stand (2026-09-14 nachmittags — Räume zusammengelegt, Zeitungs-Vertiefung live; Sitzung d8da3b26)

**Erledigt:** Räume Mail/Briefing/Aufträge → „Achim / Lotse" ([chat-hub#90](https://github.com/iilgmbh/chat-hub/issues/90)), Auffangnetz `auftragsraum_sync.sh` (#3154), Sperre eine Session je Raum ([chat-hub#94](https://github.com/iilgmbh/chat-hub/issues/94)). news.iil.pet hinter Cloudflare Access (news-hub#54); Vertiefung je Thema per Knopf und Chat-Zuruf in Prod ([news-hub#52](https://github.com/achimdehnert/news-hub/issues/52)). Zurufe #3150/#3151 und Kapitel-Feedback (Ledger #138) gesendet.

**Zielzustand:** #90, #94, news-hub#52/#54/#55 erreicht. **SA-4:** 5 eigene Merges unter Mandat (#3153, #3154, news-hub#56/#58/#59) · 2 unnötige Rückfragen · 0 Fehlanwendungen; eigene Fehler außerhalb SA-4 im Log, als Outline-Lessons 2026-09-14 verankert. **0h:** Abnahme 20/22 belegt, 2 nur Selbstauskunft (Briefing-Erstlauf, Bestätigung im Raum); Clear-Härte: SA-4 präzisiert, Checklisten abgehakt. **Offen:** laufende Raum-Session hält noch keine Sperre (vor #96 gestartet) — nächster Neustart vorher „Lotse stopp"; Sortierer-Lücken #3152.

## ⚡ Aktueller Stand (2026-09-14 — Secret-Leser Fleet, Groq rotiert, Gate-Revisionen, Räume; Sitzung 0117JBQX)

**Zeitanker:** HEAD `226e41c7` · `rev-list --count` 4468 · geschrieben 2026-09-14

**Auftrag [#3149](https://github.com/achimdehnert/platform/issues/3149) geschlossen:** Groq rotiert und verteilt, Zeitung liefert (news-hub#46); Schlüsseldateien bare 56 → 0 über toleranten Leser (#3141 + 10 Fleet-PRs, [#3129](https://github.com/achimdehnert/platform/issues/3129)); Fixture #3157 + 9 Kopien (#3155); Staging-Gate fing risk-hub#753/#754, Prod unberührt; Retro #3156, Gate-Revisionen #3160; Kalender-Löschen #3163; Termine in „Achim / Lotse" (chat-hub#93). Eigene Fehler gemeldet und verankert (Sourcing-Leck, Deploy vor Build, Worktree-Aufräumen per Datum → #3164). Älterer Stand 2026-09-12/13 im Archiv; der Referenz-Parser liest dort news-hub#44/chat-hub#88 als achimdehnert/hub#88 und chat-hub#88 ohne Org (#3165).

**Zielzustand #3149:** K1–K6 erfüllt (fremder Blick 0d: K2 „teilweise", Gegenprobe über PR-Text und Issue-Body: vollständig). **SA-4:** 27 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen. **0h:** beide Agenten gelaufen, Lücken aus 0e geschlossen. Anker: pgvector `session:platform:20260914:0117jbqx`.

## Offene Fäden (über den Session-Stand hinaus)

- **Auftragsraum Stufe 1** ([#3079](https://github.com/achimdehnert/platform/issues/3079)): fertig; Kill-Gate-Zahlen 2026-10-08 (KONZ-059). **sevdesk-Routinen** ([#3102](https://github.com/achimdehnert/platform/issues/3102)): K4 in PR, K1–K3/K5 und K6 in Bau.

0. iil-assist Gateway: Transport (D2) nicht begehbar — drei Ursachen belegt, Fix haengt an der Transport-Entscheidung: https://github.com/achimdehnert/mcp-hub/issues/264

0. Auftrag #3102 (sevdesk-Routinen, SA-4) laeuft: https://github.com/achimdehnert/platform/issues/3102
0. iil-assist (KONZ-058): O5 gemessen (negativ); Transport-Entscheidung Weg 1–3 = Owner-Wort, dann MVP 2 Dokument-Suche; Nebenissues #3019 PyPI, #3020 Regelkreis, #3021 Routing, #3022 ADR-036: https://github.com/achimdehnert/platform/issues/3011
0. netcup gekuendigt (Owner 2026-09-10): hosts.yaml-PR #3093 offen; Offsite-Cron via #2968: https://github.com/achimdehnert/platform/issues/2950
0. dev-hub Staging-Deploy vorbestehend kaputt (Kein Compose-File): https://github.com/achimdehnert/dev-hub/issues/348
0. Paperless `PAPERLESS_FILENAME_DATE_ORDER` setzen: https://github.com/achimdehnert/doc-hub/issues/15
0. Stapel-Zerleger im Betrieb, Zielzustand-Issue noch offen: https://github.com/achimdehnert/doc-hub/issues/4 — Bauteile gemergt (doc-hub#5, doc-hub#13, doc-hub#14).
0. Freigabe-Zeile je Prod-Schritt als Regel bestaetigen — aus dem Stand vom 2026-09-09 abends gerettet (Owner-Entscheid).

- **[3164]** Retro-Restlücken: Anker-Gate-Fehlläufe, weitere Roh-Leser (6 Repos ohne Stufe-2-PR), Rettungs-Branch — https://github.com/achimdehnert/platform/issues/3164
- **[chat-hub#94]** Raum-Session: zweiter Start muss mechanisch scheitern (Sperre in lotse_session.sh) — https://github.com/iilgmbh/chat-hub/issues/94
- **[3158]** Stop-Hook `deferred_item_scanner` aus `~/.claude/settings.json` austragen (Owner, nach Sunset in #3160) — https://github.com/achimdehnert/platform/issues/3158
- **[3129]** Melder `secrets_pruefen --alle`: `gemischt` als eigene Stufe statt Exit 1 — https://github.com/achimdehnert/platform/issues/3129
- **[3050]** Waisen-Melder: Repo→Host-Zuordnung kippt still (Rest aus dem geschlossenen #3015) — https://github.com/achimdehnert/platform/issues/3050
- **[news-hub#45]** Web-Naht fav0: zweite Lieferquelle, Freigabe-Tracking offen (aus Stand 2026-09-12 gerettet) — https://github.com/achimdehnert/news-hub/issues/45
- **[3112]** sevdesk: ältere Werkzeuge auf `--mandant` umstellen (aus Stand 2026-09-13 gerettet) — https://github.com/achimdehnert/platform/issues/3112
- **[3115]** origin-tls: gpu-ollama nicht messbar (aus Stand 2026-09-13 gerettet) — https://github.com/achimdehnert/platform/issues/3115
- **[3116]** Auftragsraum: Satzzeichen zählt als Wort (aus Stand 2026-09-13 gerettet) — https://github.com/achimdehnert/platform/issues/3116
- **[3135]** test_kostenabgleich schreibt Buchungslog ins echte Home (aus Stand 2026-09-13 gerettet) — https://github.com/achimdehnert/platform/issues/3135
- **[2982]** Retro 136735: sieben ueberlebende Befunde ohne Umsetzungsartefakt — beim Auslagern der Sektion vom 2026-09-08 hierher gerettet — https://github.com/achimdehnert/platform/issues/2982
- **[2507]** dev-desktop: 10 undeklarierte Container / 4 oeffentliche Hostnamen gegen die Auflage; todo-board-Befund blockte #3093 — https://github.com/achimdehnert/platform/issues/2507
- **[2908]** gate_namensdeckung lief nie durch — Drill-Luecken; 8 Gates nennen Faelle ohne Drill (Start 0.7.15) — https://github.com/achimdehnert/platform/issues/2908
- **[2990]** ci_deckung: shared-ci-Workflows aufloesen statt NICHT PRUEFBAR (24 Ziele) — https://github.com/achimdehnert/platform/issues/2990
- **[3102]** sevdesk-Routinen: K9 im Echtlauf, Owner-Reste (RE-1028, GitHub/Microsoft-Belege, 20.000 hin/zurueck) im Kommentar — https://github.com/achimdehnert/platform/issues/3102
- **[3027]** Auslagerungs-Gate liest Fremd-Repos jetzt per Flotten-Token; schliesst erst, wenn eine Auslagerung mit Fremd-Refs im Gate gruen laeuft — https://github.com/achimdehnert/platform/issues/3027
- **[3079]** Auftragsraum Stufe 1 fertig; naechster Schritt Kill-Gate-Auswertung 2026-10-08 — https://github.com/achimdehnert/platform/issues/3079
- **[3080]** Backlog-Check zaehlt nacktes offen als Anker — https://github.com/achimdehnert/platform/issues/3080
- **[3073]** 20 Dateien Format-Schuld (ruff format) — https://github.com/achimdehnert/platform/issues/3073
- **[doc-hub#18]** Access-Liste docs.iil.pet: zwei fremde Konten; `auto-title.py` nur auf prod geaendert — https://github.com/achimdehnert/doc-hub/issues/18
- **[news-hub#33]** Morgen-Zeitung: Themenauswahl kuert generische Woerter — beim Auslagern der Sektion vom 2026-09-09 vormittags hierher gerettet — https://github.com/achimdehnert/news-hub/issues/33
- **[news-hub#40]** Morgen-Zeitung: Smoke-Lauf im CI, Entwurf steht — beim Auslagern gerettet — https://github.com/achimdehnert/news-hub/issues/40
- **[news-hub#19]** Morgen-Zeitung: NIS2 und Voice Agents ohne Quelle, Robotik und IoT belegt — beim Auslagern gerettet — https://github.com/achimdehnert/news-hub/issues/19
- **[3001]** memory-link-guard meldet einen intakten Wikilink als tot (Lane-Verwechslung) — beim Auslagern der Sektion vom 2026-09-09 vormittags hierher gerettet — https://github.com/achimdehnert/platform/issues/3001
Je eine Zeile mit Link, kein Verlauf. Frisches steht oben im Stand-Block, Historie in
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md). Jede Zeile zeigt auf ein
**offenes** Issue — ist es geschlossen, gehört sie ins Archiv, nicht hierher.

0. Auslagern verlor drei Faeden nach #2967 — Befund zum Gate selbst: https://github.com/achimdehnert/platform/issues/2974
1. KONZ-054 Systembild, Kill-Gate 2026-10-15; Owner-Punkte #2486/#2504/#2507, Reste #2480: https://github.com/achimdehnert/platform/issues/2516
2. KONZ-051 ux-review-agent, Kill-Gate 2026-09-30; K1 3/9, K3 offen: https://github.com/achimdehnert/writing-hub/issues/766
3. Volume-Deckung prod (40 Volumes), K2 = Owner-Gate, Löschliste #2258: https://github.com/achimdehnert/platform/issues/2300
4. KONZ-052-Rest: `PYPI_API_TOKEN` löschen (Owner-Wort, dann #1904 zu), Erstrelease iil-enrichment/gaeb-toolkit: https://github.com/achimdehnert/platform/issues/2380
6. Gate-Deckung: 11 Slugs gedeckt/Verzicht per #2909 (38 %), 4 Verzichte bestätigen: https://github.com/achimdehnert/platform/issues/2234
7. Wirksamkeits-Bilanz der Gates: 6 rückfällige per #2909 behandelt, Hook-Verdrahtung #2907: https://github.com/achimdehnert/platform/issues/2374
8. Concurrency je Ziel-Umgebung: 13 gleichlautende PRs in der Flotte offen: https://github.com/achimdehnert/platform/issues/2229
9. `deploy_wirkung`-Restbefunde; travel-beat weiter RUECKSTAND (gewollt), illustration-hub → illustration-hub#344; NEU: Route ohne Deklaration (molkerei.iil.pet lief undeklariert auf staging-dedicated) — Cloudflare-DNS gegen ports.yaml abgleichen: https://github.com/achimdehnert/platform/issues/2148
10. risk-hub: Prod auf `main` seit 2026-09-11 (Dispatch + Owner-Klick); Rest im Issue, Repo liegt in `iilgmbh`: https://github.com/iilgmbh/risk-hub/issues/729
11. Rollende Melder legen an statt zu aktualisieren, ~38 Kandidaten: https://github.com/achimdehnert/platform/issues/2140
12. shared-ci-Bänder: App-Repos v1.1.10 ×17 / v1.0.11 ×2, `ttz-lif`+`meiki-lra` ungemessen: https://github.com/achimdehnert/platform/issues/2087
13. ADR-Zweitmeinungen ohne Rückkanal, 19 von 24 ohne Antwort: https://github.com/achimdehnert/platform/issues/2088
14. `hygiene_melder.py` meldet invertiert (Footer mitgehasht), drei Phasen dieselbe Wurzel: https://github.com/achimdehnert/platform/issues/2054
15. Public→Private Welle 1: Owner-Freigabe fehlt, F entsperrt ADR-255: https://github.com/achimdehnert/platform/issues/2119
17. ADR-242 Wave 3: Phase-2-Rest, Apply-Artefakt fehlt: https://github.com/achimdehnert/platform/issues/811
18. CI-Runner `ci-gpu` auf eigenen Server (braucht keine GPU), Kosten = Owner-Wort: https://github.com/achimdehnert/platform/issues/2543
19. GX10: gemessen, `NUM_PARALLEL=4` + vLLM-Dienst stehen; offen: Verbraucher umhaengen (mcp-hub#262 blockiert): https://github.com/achimdehnert/platform/issues/2544
20. GX10-Training: 4090 bleibt fuehrend bis 16.384 Umgebungen, darueber traegt nur der GX10: https://github.com/achimdehnert/robo-lab/issues/58
53. Kaufberatung zweites Geraet — Empfehlung abgelegt, Kenntnisnahme offen: https://github.com/achimdehnert/platform/issues/2978
21. Mail-Ansicht: leerer Körper braucht „Inhalt im Anhang": https://github.com/achimdehnert/platform/issues/2597
22. Owner: die 20 mechanisch gesetzten `frist_grund`-Texte auf `todo.iil.pet` sichten (Spalte Frist) — mechanisch je Bucket gesetzt, nicht redigiert: https://github.com/achimdehnert/platform/issues/3015
23. Megatest-Erstlauf, 15 Befunde unbearbeitet und ohne Tracking-Issue ([Lauf 30619024656](https://github.com/achimdehnert/platform/actions/runs/30619024656), 2026-08-02) — vor Wiederaufnahme neu messen.
24. Gegenprobe Wochenlauf `ttz-hub`: beim nächsten Lauf, der ttz-hub wirklich ändert, müssen Checks am erzeugten PR erscheinen: https://github.com/achimdehnert/platform/issues/3090
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
