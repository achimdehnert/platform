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

## ⚡ Aktueller Stand (2026-09-08 — Sitzung 136735: GX10 traegt zwei Rollen, zwei Konfigurationszeilen schlugen ein drittes Geraet)

**Kaufberatung Mini-PC gegen GX10:** nicht kaufen, der Knoten war nicht ausgereizt ([#2978](https://github.com/achimdehnert/platform/issues/2978)).

**Inferenz ([#2544](https://github.com/achimdehnert/platform/issues/2544)):** Ollama bediente mehrere Nutzer gar nicht parallel (1.906 tok/s bei 1 wie bei 8). Mit `OLLAMA_NUM_PARALLEL=4`: 2.632. vLLM laeuft seit heute als zweiter Dienst (Port 8000, wg0): 3.526, Skalierung 3,3x. Kein Verbraucher umgestellt — [mcp-hub#262](https://github.com/achimdehnert/mcp-hub/pull/262) blockiert, alle `ci-nonprod`-Runner offline.

**Training ([robo-lab#58](https://github.com/achimdehnert/robo-lab/issues/58)):** Bis 16.384 Umgebungen ist die 4090 3,3x schneller; bei 20.480 bricht sie am VRAM ab, der GX10 rechnet durch. Ihre WSL-Maschine durfte vorher nur 12 von 128 GB nutzen — jetzt 64.

**Retro 136735** ([#2975](https://github.com/achimdehnert/platform/pull/2975)): 14 Befunde, 11 ueberlebt, 7 ohne Artefakt in [#2982](https://github.com/achimdehnert/platform/issues/2982). Zwei Lehren: SoT zitiert statt gelesen (`hosts.yaml:166`); der Melder liest `ports.yaml` — drei Ausnahmen waren tot ([#2977](https://github.com/achimdehnert/platform/pull/2977)).

## ⚡ Aktueller Stand (2026-09-08 — Retro 61c35d: zwei Gates ausgeweitet; Eich-Bogen 15/15 unklar deckte drei Fehlurteile des Readiness-Bewerters auf, Basislinie 07.09. ungueltig)
**Zeitanker:** HEAD `9f26db88` · `rev-list --count` 4265 · geschrieben 2026-09-08


**Sitzung 8661c35d (HydraFusion-Auswertung, 2026-09-07/08):** nach [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md) ausgelagert (2026-09-08).

**Sitzung c1ba5d (Mail-Arbeitsliste + Retro, 2026-09-07):** nach [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md) ausgelagert (2026-09-08); Offenes als Faden 46-51.

**Sitzung 61952dd7 (2026-09-08, Scan-Strecke):** Aus der Owner-Frage nach acht Seiten in einem Dokument wurde ein Melder: ein Scan, der im Consume-Baum liegen bleibt, und einer, der daraus verschwindet, ohne ein Dokument zu werden, melden sich jetzt selbst ([#2966](https://github.com/achimdehnert/platform/pull/2966), [#2970](https://github.com/achimdehnert/platform/pull/2970); stuendlich auf dem prod-Runner, Alarm als zugewiesenes Issue `scan-haengt`), dazu `/scan` ([#2971](https://github.com/achimdehnert/platform/pull/2971)) und ein Gate, das beim Auslagern keine offenen Vorgaenge mehr verschlucken laesst ([#2980](https://github.com/achimdehnert/platform/pull/2980), Befund [#2974](https://github.com/achimdehnert/platform/issues/2974), sechs Faeden nachgetragen in [#2976](https://github.com/achimdehnert/platform/pull/2976)). Anlass war ein realer Verlust ([doc-hub#3](https://github.com/achimdehnert/doc-hub/issues/3)).

**Eigene Fehler (vier, alle gemessen widerlegt):** (1) Memory-Notiz „ScanSnap liefert per SFTP“ ungeprueft als Basis fuer einen sshd-Eingriff genommen — der Lieferweg ist Samba (592 Logzeilen, alle `smbd:`); Eingriff wirkungslos, zurueckgenommen, Notiz als drift korrigiert. (2) Protokoll auf die Freigabe `scans` gelegt, waehrend der Scanner `paperless-consume` benutzt. (3) Ordnerrechte uebersehen: rsyslog darf in `/var/log/samba` keine Datei anlegen. (4) **Vier `smbd`-Neustarts fuer ein Nebenziel** — der letzte legte die Freigabe des Owners lahm. **Samba-Schreibprotokoll vollstaendig zurueckgebaut** (`cmp -s` gegen die Sicherung gruen); danach Scan 2422 in 10 s aufgenommen. Der Melder haengt nicht daran und lief durchgehend. Verankert als Abbruchregel im Memory + Outline-Lesson `…-IFP1qb5KvO`.

**Doppelarbeit:** [#2972](https://github.com/achimdehnert/platform/pull/2972) lief parallel zu [#2967](https://github.com/achimdehnert/platform/pull/2967) an derselben Datei — geschlossen; zweiter Vorfall dieser Klasse in zwei Tagen.

**Abnahme 61952dd7, von zwei fremden Pruefern gegengelesen (0h):** *Zielzustand* (Owner-Frage, ad hoc): acht Seiten in ein Dokument scannen und dort suchen koennen — **erreicht**, aber erst nach Korrektur meines Belegs. Der 0d-Pruefer verwarf ihn zu Recht: ich hatte auf den 27-Seiten-Stapel vom 06.09. verwiesen, der im selben Zug als **13** Dokumente beschrieben ist — das Gegenteil der Behauptung. Nachgemessen: `pdfinfo` ueber die heutigen Dokumente zeigt 2417 und 2418 mit je **16 Seiten als EIN Dokument**; Volltextsuche `content__icontains` liefert 55 Treffer fuer „Meldebescheinigung“ und 0 fuer ein Unsinnswort (Positiv- und Negativkontrolle). K1 und K2 sind damit gemessen, nicht geschlossen. **K3 (Verluste werden bemerkt): teilweise** — Urteil des Pruefers, uebernommen: der Melder laeuft stuendlich und fand eine reale 0-Byte-Datei, die Verlust-Erkennung selbst ist aber nur an einer erfundenen Datei plus einem echten Gegenbeispiel gezeigt; der Ausloeserfall blieb verloren, weil er vor dem Bau verschwand. **Zweiter Pruefer-Befund, uebernommen:** die Owner-Bitte „Chat-Raum fuers Scannen“ wurde **nicht gebaut** — bewusst, weil Suche (docs.iil.pet) und Meldung (Issue) vorhanden sind und ein dritter Ort eine Dopplung waere; der Owner hat dem gefolgt (Punkte 33/59/83). Das stand bisher nur im Kapitaenskanal und ist hiermit verankert. **Verschoben mit Tracking:** lueckenloses Lieferprotokoll, gestoppt nach vier Anlaeufen (doc-hub#3). *0e (fremd geprueft):* alle drei Fragen NEIN, nichts lebt nur im Chat oder im Scratchpad. *SA-4:* 0 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen. *SA-M:* 5 eigene Merges (#2966, #2970, #2980, #2983 W1; #2984 bleibt offen — `docs/governance/` braucht Owner-Wort). *Runner:* `RESULT: OK`; `E.1`/`E.7` betreffen Parallelsitzungen, `E.5` `◌ SKIP` (3 PR-Texte von Hand gesichtet), `E.10` (#2974 offen) ist richtig so.

**SA-4:** 0 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen (alle Merges per SA-M-Mandat oder Owner-Bypass mit Wort am PR). **Clear-Haerte (0e, fremder Pruefer):** zwei Luecken geschlossen — wg0-Restschritte und Rohdaten-Verzicht in #2895 nachgetragen.

**Befunde:** M3 per Review auf eigenen PRs unerreichbar (GitHub verbietet Self-Approve) → (b) umgesetzt · Aufschub-Anker-Gate feuert auf „nicht ausgewertet"/„bewusst nicht" in Code-Kommentaren (3× heute, Fehlalarm-Klasse für #2606) · zwei PRs mergte der Owner, bevor die Nachbesserung drin war (#2803→#2805, #2804→#2809) · eigener Fehler: leere Worktree-Pfadvariable (Skript schreibt auf stderr) ließ einen Cherry-pick im Haupt-Tree laufen — sofort abgebrochen, HEAD unverändert (Memory 🌀).

**Nächster Schritt:** #2737 Owner-Fragen 1–3 (v2.4-Basislinie, leere Manifeste, D11.2 ohne Manifest) · #2799 K8: `--pruefe` nennt `kein_anker`-Vorgänge mit Anker-Kommando · #2875 Upload-Session + Entwurf beim Abbruch wegräumen · #2802 Speicher-Melder auf Helfer · travel-beat Runner.

**SA-4:** 0 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen. SA-M 2026-09-06: 3 Merges W1/M1 (#2871, #2874, #2877), 3 Sonnet-Subagenten nach Brief, Prüfung inline. SA-M 2026-09-04: 3 Merges per Mandat (#2805 W1/M1, #2808 W1/M1, beide nach Freigabe-Vermerk im Issue-Body #2737), 8 W3-Merges durch den Owner. Delegation: 7 Subagenten nach Brief (4 Sonnet, 3 Opus; Prüfung + Fixes inline), Session `ac4fb7c7`.

## Offene Fäden (über den Session-Stand hinaus)

Je eine Zeile mit Link, kein Verlauf. Frisches steht oben im Stand-Block, Historie in
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md). Jede Zeile zeigt auf ein
**offenes** Issue — ist es geschlossen, gehört sie ins Archiv, nicht hierher.

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
