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

## ⚡ Aktueller Stand (2026-09-09 abends — Stapel-Zerleger im Betrieb; Retro kippte zwei eigene Urteile)

**Zielzustand erreicht** ([doc-hub#4](https://github.com/achimdehnert/doc-hub/issues/4)): Ein Scan mit mehreren Dokumenten wird auf dem Weg in Paperless automatisch zerlegt, verschlagwortet und abgelegt; das Original wandert aus dem Eingang, wird aber nie geloescht. Code `/opt/doc-hub/splitter/` auf hetzner-prod, eigenes venv, Timer `doc-hub-splitter.timer` alle 3 Minuten (aktiviert nach Owner-Wort). Eingang `/opt/paperless-consume/schleuse/scan-eingang` — den ignoriert Paperless ohnehin, deshalb war kein Samba-Eingriff noetig. Personen-Muster `/etc/doc-hub/zuordnung.json` (0640, nicht im Repo).

**Zwei echte Betriebsscans, beide auf die Owner-Zahl gebracht:** 18 Seiten → 4 Dokumente, 26 Seiten → 5 Dokumente. Zehn PRs in doc-hub ([#5](https://github.com/achimdehnert/doc-hub/pull/5)–[#14](https://github.com/achimdehnert/doc-hub/pull/14)), einer in platform ([#2999](https://github.com/achimdehnert/platform/pull/2999), Waechter sieht den neuen Eingang). Der teuerste gefundene Fehler: eine Parkhaus-Quittung wurde als Leerseite verworfen — ein kleiner Beleg auf A4 traegt weniger Tinte als eine leere Rueckseite mit Falzkante; die *Form* trennt sie, nicht die Menge ([#13](https://github.com/achimdehnert/doc-hub/pull/13)).

**Retro** (`docs/retros/session-retro-2026-09-09-doc-hub-a6edc6.md`, Footprint `full`): 16 Befunde, 15 ueberlebt. Die Widerlegungsbahn kippte **zwei eigene Urteile** — eine Severity war zu hoch (der Waechter sah den Ordner damals gar nicht), und ein verworfener Befund musste zurueck (A5 nennt vier Merkmale, nicht zwei). **Drei Gates haben gefangen** und je eine Handlung ausgeloest. Rueckfaellig war `scope-checkpoint-not-durably-recorded`: sein Muster kannte nur das Abschalten von Diensten — als hier einer scharfgeschaltet wurde, schwieg es. Ausgeweitet in diesem PR.

**Offen und dein Zug:** (1) Freigabe-Zeile je Prod-Schritt als Regel bestaetigen — drei Eingriffe dieser Sitzung haben keinen eigenen Vermerk. (2) Traeger fuer den Host-Eingriff-Hook entscheiden ([#2907](https://github.com/achimdehnert/platform/issues/2907)); der Zerleger braucht `tesseract-ocr-deu`, das nur von Hand auf prod liegt. (3) `PAPERLESS_FILENAME_DATE_ORDER` setzen ([doc-hub#15](https://github.com/achimdehnert/doc-hub/issues/15)).

**Zielzustand:** erreicht mit einer Einschraenkung — **Urteil des fremden Abnahme-Agenten, nicht meines**: A1, A3, A4, A6 sind durch Code und Tests belegt; A5 im Kern erfuellt, aber ohne Test fuer Korrespondent/Dokumenttyp; **A2 ist aus den Artefakten NICHT PRUEFBAR**, weil der Beleg nur auf dem Server lebt (billigster Check: Trockenlauf dort gegen die Owner-Liste). Ich hatte „A1 bis A6 geprueft" geschrieben — das war zu weit.

**Clear-Haerte (fremder Blick):** Drei Prod-Freigaben stehen nur als Frage und Ergebnis im Verlauf, die Zustimmung in keinem Artefakt. Acht der zehn Retro-Massnahmen hatten kein Tracking-Issue (nachgeholt). Der README-Beispielpfad wich vom echten Prod-Pfad ab (behoben).
**SA-4:** 11 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.

## ⚡ Stand (2026-09-09 vormittags — die Morgen-Zeitung laeuft; Retro kippte zwei eigene Urteile)

**Morgen-Zeitung live** ([KONZ-platform-057](docs/konzepte/KONZ-platform-057-morgenzeitung-aus-dem-hot-topics-letter.md)): `news.iil.pet` bedient, Timer 06:15 UTC, Ausgabe erscheint als aufklappbare Artikel im Matrix-Raum `#news:chat.iil.pet` (Oberflaeche: **app-chat.iil.pet**). Kette: `mail_lesenaht` (devhub_web) → `digest_taeglich` (news_hub_web) → Chat. Betriebs-Runbook in Outline („Morgen-Zeitung … Betrieb auf news.iil.pet").

**Was der Tag ergab:** Aus einem Mailcheck wurden sieben Owner-Zurufe und 21 gemergte PRs in zwei Repos — [#2987](https://github.com/achimdehnert/platform/pull/2987) (Board-Kopfzeile, Bucket `kenntnis`), [#2991](https://github.com/achimdehnert/platform/pull/2991) (Konzept), [#2993](https://github.com/achimdehnert/platform/pull/2993) (Deklaration), [#2998](https://github.com/achimdehnert/platform/pull/2998), [#3002](https://github.com/achimdehnert/platform/pull/3002) (Retro) sowie news-hub [#24](https://github.com/achimdehnert/news-hub/pull/24)–[#41](https://github.com/achimdehnert/news-hub/pull/41).

**Retro** ([#3002](https://github.com/achimdehnert/platform/pull/3002), Footprint `deep`): 20 Befunde, 13 ueberlebt. Die Widerlegungsbahn kippte **zwei eigene Urteile** — die Rework-Quote (50 % → 21 %, vier PRs korrigierten Arbeit vom 29.08.) und den Staging-Befund (news-hub hat gar kein Staging, es war eine Dublette). Ein verworfener Befund kehrte zurueck: KONZ-057 traegt eine Ledger-Zeile `belegt`, deren Beleg derselbe Tag umschrieb. **Neu und keinem Finder aufgefallen:** ein Ausfall des Tageslaufs war unsichtbar — behoben in [news-hub#41](https://github.com/achimdehnert/news-hub/pull/41) (`digest_frische`, Units im Repo, `OnFailure` meldet in den Chat-Raum).

**Eigene Fehler:** Ein Filter ohne Untergrenze leerte das Blatt, und der zugehoerige Test schrieb genau dieses Verhalten als richtig fest (Outline-Lesson, [news-hub#36](https://github.com/achimdehnert/news-hub/pull/36)). Ich meldete 14 selbst geschriebene Freigabe-Zeilen als Regelverstoss — der Owner wies das zurueck („kein Regelverstoss, sondern sinnvolles miteinander arbeiten"); die Memory-Regel ist ersetzt. Eine PR-Nummer war erfunden (#3001 statt #3002).

**Offen (Owner):** Themenauswahl kuert weiter generische Woerter ([news-hub#33](https://github.com/achimdehnert/news-hub/issues/33)) · Smoke-Lauf im CI, Entwurf steht ([news-hub#40](https://github.com/achimdehnert/news-hub/issues/40)) · NIS2 und Voice Agents ohne Quelle, Robotik und IoT belegt ([news-hub#19](https://github.com/achimdehnert/news-hub/issues/19)) · drei Memory-Kandidaten aus der Retro.

**Clear-Haerte (0e):** F1 nein — Betrieb im Outline-Runbook, Befunde im Retro-Bericht, Restarbeit in Issues. F2 nein. F3 nein.

## ⚡ Aktueller Stand (2026-09-08 — Sitzung 136735: GX10 traegt zwei Rollen, zwei Konfigurationszeilen schlugen ein drittes Geraet)

**Kaufberatung Mini-PC gegen GX10:** nicht kaufen, der Knoten war nicht ausgereizt ([#2978](https://github.com/achimdehnert/platform/issues/2978)).

**Inferenz ([#2544](https://github.com/achimdehnert/platform/issues/2544)):** Ollama bediente mehrere Nutzer gar nicht parallel (1.906 tok/s bei 1 wie bei 8). Mit `OLLAMA_NUM_PARALLEL=4`: 2.632. vLLM laeuft seit heute als zweiter Dienst (Port 8000, wg0): 3.526, Skalierung 3,3x. Kein Verbraucher umgestellt — [mcp-hub#262](https://github.com/achimdehnert/mcp-hub/pull/262) blockiert, alle `ci-nonprod`-Runner offline.

**Training ([robo-lab#58](https://github.com/achimdehnert/robo-lab/issues/58)):** Bis 16.384 Umgebungen ist die 4090 3,3x schneller; bei 20.480 bricht sie am VRAM ab, der GX10 rechnet durch. Ihre WSL-Maschine durfte vorher nur 12 von 128 GB nutzen — jetzt 64.

**Retro 136735** ([#2975](https://github.com/achimdehnert/platform/pull/2975)): 14 Befunde, 11 ueberlebt, 7 ohne Artefakt in [#2982](https://github.com/achimdehnert/platform/issues/2982). Zwei Lehren: SoT zitiert statt gelesen (`hosts.yaml:166`); der Melder liest `ports.yaml` — drei Ausnahmen waren tot ([#2977](https://github.com/achimdehnert/platform/pull/2977)).

## Offene Fäden (über den Session-Stand hinaus)

Je eine Zeile mit Link, kein Verlauf. Frisches steht oben im Stand-Block, Historie in
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md). Jede Zeile zeigt auf ein
**offenes** Issue — ist es geschlossen, gehört sie ins Archiv, nicht hierher.

0. Scan-Strecke: lueckenloses Lieferprotokoll offen, nach vier Anlaeufen gestoppt: https://github.com/achimdehnert/doc-hub/issues/3
0. Auslagern verlor drei Faeden nach #2967 — Befund zum Gate selbst: https://github.com/achimdehnert/platform/issues/2974
0. Gate-Registry-Eintrag `handover-auslagerung-verschluckt-offenes` wartet auf Owner-Wort (`docs/governance/`): https://github.com/achimdehnert/platform/pull/2984
0. Morgen-Zeitung: Themenauswahl kuert generische Woerter, Smoke-Lauf offen: https://github.com/achimdehnert/news-hub/issues/33
1. KONZ-054 Systembild, Kill-Gate 2026-10-15; Owner-Punkte #2486/#2504/#2507, Reste #2480: https://github.com/achimdehnert/platform/issues/2516
2. KONZ-051 ux-review-agent, Kill-Gate 2026-09-30; K1 3/9, K3 offen: https://github.com/achimdehnert/writing-hub/issues/766
3. Volume-Deckung prod (40 Volumes), K2 = Owner-Gate, Löschliste #2258: https://github.com/achimdehnert/platform/issues/2300
4. KONZ-052-Rest: `PYPI_API_TOKEN` löschen (Owner-Wort, dann #1904 zu), Erstrelease iil-enrichment/gaeb-toolkit: https://github.com/achimdehnert/platform/issues/2380
5. PyPI-Org `iil`: nur noch Owner-Klicks (Org löschen, `iildehnert` härten, Konto `achimdehnert` prüfen); Org antwortete 07.09. noch 200, Ledger 152 Wiedervorlage 14.09.: https://github.com/achimdehnert/platform/issues/2291
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
