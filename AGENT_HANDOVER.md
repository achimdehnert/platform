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

## ⚡ Aktueller Stand (2026-09-08 — Retro 61c35d: zwei Gates ausgeweitet; Eich-Bogen 15/15 unklar deckte drei Fehlurteile des Readiness-Bewerters auf, Basislinie 07.09. ungueltig)
**Zeitanker:** HEAD `9f26db88` · `rev-list --count` 4265 · geschrieben 2026-09-08


**Sitzung 8661c35d (2026-09-07/08, HydraFusion-Auswertung):** 15 Merges; Belege im [Kommentar auf #2750](https://github.com/achimdehnert/platform/issues/2750#issuecomment-5572290034). Kern: ADR-068 war der halb gebaute Zwilling → [ADR-302](https://github.com/achimdehnert/platform/pull/2930). Neu: Kosten/Qualitaet je Sitzung (#2939), Deckung neben der Readiness (#2943), D10 erhoben (#2945), Melder-Ablageform + 4 Melder (#2946, #2948), Rollback-Frage gemessen (#2947), **ADR-228 umgesetzt + Feueruebung bestanden** (#2954, #2931), implementation_status geprueft (#2957). mcp-hub: 3 Prod-Deploys.

**Retro + Eich-Bogen:** [Retro 61c35d](https://github.com/achimdehnert/platform/pull/2963) — 15 Befunde, 12 ueberlebt. Zwei Gates waren rueckfaellig und sind **ausgeweitet**: `claim-before-cheapest-check` Rev 7 (Wirkungs-Claim ueber ein Gate im PR-Text — nur ein Ruleset-Lesen entwaffnet, ein roter Check nicht) und `built-but-never-called` Rev 2 (`tools/aufruferlose_funktionen.py`, gatend im Pflicht-Job). Beide `zu-frueh`: gedrillt, im Feld unerprobt.
Der **Eich-Bogen kam 15/15 `unklar`** — Befund ueber den Bogen selbst (Suchschluessel statt Zustand; Gegenproben aus `unverified`-Fragen). Der Neubau legte **drei systematische Fehlurteile** offen (#2965): 34/56 `fail` fuers Lockfile ohne Manifest, 40/56 fuer Typpruefung im wiederverwendbaren Workflow, Absturz auf aelterem Bestand bei den 26 Paketen mit Agent-Datei. **Basislinie 07.09. (Median 55) ungueltig, neu GERECHNET in dev-hub#344: Median 58.** Belege und Nachrechenweg dort und in #2737.
**Externe Zweitmeinung** traf dreifach, alles uebernommen; die Hauptfrage fehlte: **welche Eingriffe waren fuer einen PRUEFauftrag noetig und gedeckt?**

**Abnahme (0d), von einem fremden Pruefer geurteilt — sein Urteil gilt:** **NICHT ERREICHT**, zwei von vier Kriterien gefallen. Erfuellt sind K1 (der Artikel wurde gegen den eigenen Bestand gehalten — ADR-302 vergleicht Zeile fuer Zeile) und K4 (Advocatus Diabolus — der Abschnitt „Grenzen, ehrlich mitgenommen" steht in der ADR selbst, nicht erst in der Retro). Nicht erfuellt sind K2 (Continuous Improvement) und K3 (Predictive Maintenance): kein Artefakt und keine ausdrueckliche Absage, in keiner der 15 gemergten PRs. Das ist STRENGER als mein eigenes Retro-Urteil, das nur K3 als Luecke fuehrte — der Pruefer verwirft meine „Blickwinkel statt Faehigkeit"-Deutung fuer K2 ausdruecklich, mit derselben Begruendung, die schon die externe Zweitmeinung gab: nachtraegliche Massstabsanpassung. Verschoben ist nichts; die Luecke bleibt offen und haengt an [#2737](https://github.com/achimdehnert/platform/issues/2737).

**SA-4: 0 Anwendungen · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.** Jede substanzielle Handlung dieser Sitzung lief entweder auf ein woertliches Owner-Go, auf eine Pflicht-Phase eines Skills oder auf eine ausdrueckliche Delegation („entscheide autonom die jeweils beste Handlungsvariante"). Zielzustand-Konvergenz als eigenstaendige Begruendung kam nicht vor.

**Offen (Owner):** 4 Funktionen ohne Verwendung (#2961) · 14 accepted-ADRs ohne Umsetzungsvermerk (#2962) · Melder schreiben, niemand liest; das Flag uebergibt 1 von 4 Aufrufern ([#2944](https://github.com/achimdehnert/platform/issues/2944)) · Fehlalarm „bewusst nicht X" 4. Vorkommen (#2606). Sechs PRs offen: #2967 #2969, dev-hub#344, shared-ci#79, odoo-hub#32, billing-hub#52.
**Eigene Fehler:** 12+ Ruecknahmen, fast alle „mein Filter, nicht die Welt". #2957 gemergt waehrend ich nachschob (2 Commits verloren, #2958; die Retro korrigierte spaeter mein „zweimal" auf einmal). Der erste Vergleich zu #2965 mass still 30 statt 56 Repos — dieselbe Falle, die der PR behebt.

**Clear-Haerte (0e), fremd geprueft:** F1 nein — alle Kernaussagen stehen durabel. F2/F3 ja und behoben: das Eich-Bogen-ERGEBNIS (15/15 `unklar`) lag nur im Verlauf und steht jetzt als Inhalt in #2737; der Nachrechenweg der Basislinie stand nur im Scratchpad und steht jetzt in dev-hub#344. Bewusst fluechtig bleibt der Schluessel des Bogens v2 in `~/shared/` — waere er abgelegt, misst der Bogen nichts mehr.

**Sitzung c1ba5d (2026-09-07 nachmittags, Owner-Kurzbefehle über die Mail-Arbeitsliste, dann `/session-retro`):** Elf Mail-Vorgänge bearbeitet, 7 Entwürfe draft-first, 6 vom Owner gesendet (Oke Kap. 1/4/5, Mattis-Exposé freigegeben, Tanyildiz-Nachfass, Terra-Anschrift+Kosten, Kanzlei Werner, FR-Beschwerdeführer); PyPI-Org `iil` gelöscht (404 belegt), vier Altnamen an `iildehnert`, Konto `achimdehnert` löschbar erst nach PyPI-seitigem Fehler ([#2291](https://github.com/achimdehnert/platform/issues/2291) offen). Retro `c1ba5d` (lean, 5 Befunde / 4 überlebt, [#2927](https://github.com/achimdehnert/platform/pull/2927) gemergt): **Gate rückfällig** — der Evidenz-Hook sah Mail-Entwürfe nie, eine falsche Seitenzahl („22 pages", tatsächlich 23) ging an einen Studierenden raus; Rev 6 weitet ihn auf `--body-file`-Entwürfe aus, advisory statt blockend ([#2932](https://github.com/achimdehnert/platform/pull/2932) gemergt, [#2924](https://github.com/achimdehnert/platform/issues/2924)). **Eigener Fehlschluss:** Phase 6 (Extern-Handoff) als Streichkandidat „kein Leser" geführt — falsch, der Owner nutzt ihn per Copy-and-paste; derselbe Fehlschluss lief schon am 02.09. gegen #2088. Statt Streichen ein Rückweg: externe Antworten als `~/shared/…-extern1.md`/`-extern2.md`, Pflichtlektüre der nächsten Retro ([#2935](https://github.com/achimdehnert/platform/pull/2935), [#2925](https://github.com/achimdehnert/platform/issues/2925) zu). Zwei Memories verankert (Zahl im Entwurf nur aus Kommando; ein Issue-Kommentar je Sachstand). Delegation: 2 Sonnet-Subagenten für Finder/Skeptiker, 1 für den Gate-Bau, Prüfung inline (Gegenprobe alt/neu selbst gefahren).

**Runner-Befunde dieser Sitzung:** `E.6 template-drift` meldete „kein Repo erreichbar (meist Drosselung)" — im selben Zug widerlegt (`gh api` antwortet, Rate-Limit 5000/5000), Ursache offen → [#2940](https://github.com/achimdehnert/platform/issues/2940). `E.5 zusagen` blieb `◌ NICHT PRUEFBAR` (Groq über urllib → HTTP 403 von Cloudflare, bekannte Klasse); ersatzweise die drei eigenen PR-Texte von Hand geprüft — die einzige Zusage („Redistribution nach dem Merge", #2935) ist eingelöst, `E.9` meldet alle Lanes synchron. `E.1` zeigt einen fehlgeschlagenen dev-hub-Deploy (Run 34131042204, `workflow_dispatch` 14:05 UTC) aus einer **Parallelsitzung** — nicht angefasst, gehört dorthin. `E.7` nennt dev-hub und meiki-hub dirty; beide Stände stammen nicht aus dieser Sitzung (dev-hub: CI-/Deploy-Workflows + `apps/core/frische.py`, meiki-hub: `buerger-fv.json`) — gemeldet, nicht eingesammelt. `E.4` bereinigt: der dms-hub-Erreichbarkeitsbefund war transient (Nachmessung 200, Melder meldet „antwortet"), Verzicht mit Beleg und Positivkontrolle abgelegt, ruht bis 07.10.

**Abnahme (fremder Pruefer, Phase 0d): NICHT ERREICHT.** Gemessen 16:15 UTC: 10 WARN statt 8 — bei 30 fremden Merges am Tag erzeugt jede Parallelsitzung neue Befunde. Erreicht ist der belastbare Teil: kein Melder-Defekt mehr offen, jede verbleibende Zeile mit Anker (neuer Slug `ci-gate-narrower-than-local-test` nachverankert in [#2234](https://github.com/achimdehnert/platform/issues/2234), 0.7.11 war transient und ist wieder gruen). Zwei Pruefer-Funde bestaetigt: bahn-hub-Anker #2504 aus dem Journal passt nicht (richtig: #2899); die Board-Nummern des Kanals stehen nicht im Issue, die Inhalte schon. **SA-4:** 0 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen (alle Merges per SA-M-Mandat oder Owner-Bypass mit Wort am PR). **Clear-Haerte (0e, fremder Pruefer):** zwei Luecken geschlossen — wg0-Restschritte und Rohdaten-Verzicht in #2895 nachgetragen.

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
19. GX10: Mehrbenutzer-Durchsatz ungemessen, beide gemessenen Motoren sind Einzelstrom: https://github.com/achimdehnert/platform/issues/2544
20. GX10 als zweites Trainingsgerät, K4 Vergleichslauf 4090 ↔ GX10: https://github.com/achimdehnert/robo-lab/issues/58
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
