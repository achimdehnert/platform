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

## ⚡ Aktueller Stand (2026-09-09 — die Morgen-Zeitung laeuft: news.iil.pet live, sieben Deploy-Anlaeufe fuer ein nie gestartetes Image)

**Mailcheck + Fremdvergleich:** Drei Konten, beide Richtungen. Der Inbox-Brief eines fremden Postfach-Assistenten empfahl zwei Schritte, die schon erledigt waren, und uebersah den einzigen Terminbruch des Tages — er liest nur den IIL-Posteingang, kein Gesendetes, kein HNU, und verwirft Abwesenheitsantworten. Uebernommen wurde die Form: Board-Kopfzeile und eine Spur „nur zur Kenntnis" ([#2987](https://github.com/achimdehnert/platform/pull/2987)).

**Morgen-Zeitung (KONZ-platform-057, [#2991](https://github.com/achimdehnert/platform/pull/2991)):** Die Idee existierte seit dem 29.08. als ADR-299 und war in `news-hub` fertig gebaut — es fehlte nur der Betrieb. Jetzt live: DNS, nginx-Vhost, drei Deploy-Secrets, eigener CI-Schluessel, Deploy-Lauf 34335818067 gruen, `https://news.iil.pet/livez/` = 200. Tageslauf `news-hub-tageslauf.timer` 06:15 UTC, erster echter Lauf `Result=success`, Ausgabe mit 5 Themen. Deklaration nachgezogen ([#2993](https://github.com/achimdehnert/platform/pull/2993)).

**Sieben Anlaeufe, fuenf echte Ursachen:** gesperrte Deklaration · `secrets: inherit` ueber die Org-Grenze · falsche Secret-Namen (`DEPLOY_*` → `HETZNER_*`, ADR-022) · fehlende `deployment/scripts/deploy-remote.sh` · fehlendes `gunicorn` (news-hub [#24](https://github.com/achimdehnert/news-hub/pull/24)–[#27](https://github.com/achimdehnert/news-hub/pull/27)). Lehre: CI baut das Image, sie startet es nicht.

**Eigene Fehler:** automerge nahm news-hub#24, waehrend ich noch einen Commit nachschob — der Push meldete Erfolg, der Stand fehlte auf `main`, zwei Deploy-Fehlschlaege. Und ich hielt den Team-Chat fuer Discord; `chat.iil.pet` ist Matrix/Synapse, die Melde-Schicht musste neu geschrieben werden.

**Offen (Owner):** Matrix-Bot-Konto + Raum, danach `DIGEST_CHAT_RAUM`/`DIGEST_CHAT_TOKEN` in der Umgebungsdatei auf dem Prod-Host — bis dahin meldet der Lauf „kein Chat-Token gesetzt". Keine Quelle fuer NIS2, Voice, Robotik ([news-hub#19](https://github.com/achimdehnert/news-hub/issues/19)). Governance-Luecke: automerge liess #24 ohne Approval durch, waehrend #25–#27 auf demselben Pfad ein Owner-Wort verlangten.

**Clear-Haerte (0e):** F1 nein — Betriebswissen steht im Outline-Runbook „Morgen-Zeitung … Betrieb auf news.iil.pet" und in news-hub#3. F2 nein — das Schluesselpaar in `/tmp` ist bewusst fluechtig. F3 nein.

## ⚡ Aktueller Stand (2026-09-08 — Sitzung 136735: GX10 traegt zwei Rollen, zwei Konfigurationszeilen schlugen ein drittes Geraet)

**Kaufberatung Mini-PC gegen GX10:** nicht kaufen, der Knoten war nicht ausgereizt ([#2978](https://github.com/achimdehnert/platform/issues/2978)).

**Inferenz ([#2544](https://github.com/achimdehnert/platform/issues/2544)):** Ollama bediente mehrere Nutzer gar nicht parallel (1.906 tok/s bei 1 wie bei 8). Mit `OLLAMA_NUM_PARALLEL=4`: 2.632. vLLM laeuft seit heute als zweiter Dienst (Port 8000, wg0): 3.526, Skalierung 3,3x. Kein Verbraucher umgestellt — [mcp-hub#262](https://github.com/achimdehnert/mcp-hub/pull/262) blockiert, alle `ci-nonprod`-Runner offline.

**Training ([robo-lab#58](https://github.com/achimdehnert/robo-lab/issues/58)):** Bis 16.384 Umgebungen ist die 4090 3,3x schneller; bei 20.480 bricht sie am VRAM ab, der GX10 rechnet durch. Ihre WSL-Maschine durfte vorher nur 12 von 128 GB nutzen — jetzt 64.

**Retro 136735** ([#2975](https://github.com/achimdehnert/platform/pull/2975)): 14 Befunde, 11 ueberlebt, 7 ohne Artefakt in [#2982](https://github.com/achimdehnert/platform/issues/2982). Zwei Lehren: SoT zitiert statt gelesen (`hosts.yaml:166`); der Melder liest `ports.yaml` — drei Ausnahmen waren tot ([#2977](https://github.com/achimdehnert/platform/pull/2977)).

## Offene Fäden (über den Session-Stand hinaus)

Je eine Zeile mit Link, kein Verlauf. Frisches steht oben im Stand-Block, Historie in
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md). Jede Zeile zeigt auf ein
**offenes** Issue — ist es geschlossen, gehört sie ins Archiv, nicht hierher.

0. Morgen-Zeitung laeuft, aber stumm: Matrix-Bot fehlt, NIS2/Voice/Robotik ohne Quelle: https://github.com/achimdehnert/news-hub/issues/19
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
