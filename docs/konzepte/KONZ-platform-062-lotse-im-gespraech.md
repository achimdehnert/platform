---
concept_id: KONZ-platform-062
title: Der Lotse im Gespräch — Vollduplex im Videocall, und warum die Messung zuerst kommt
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: Amendment   # ADR-249 (status: proposed) beansprucht diese Fähigkeit für ein eigenes Produkt und definiert einen Batch-Port, der Vollduplex strukturell ausschließt. Wer im chat-hub baut, braucht entweder ein Amendment an ADR-249 oder dessen Annahme mit klarer Abgrenzung — nicht beides offen lassen.
review_by: 2026-12-01
kill_criteria: "Das Vorhaben ist beendet, wenn Vorprüfung V1 (Antwortlatenz) nicht bis 2026-11-30 einen Antwortpfad mit P50 unter 2,0 s und P95 unter 4,0 s zum ersten hörbaren Wort belegt, gemessen an 20 echten Turns. Bis dahin wird kein LiveKit-Agent gebaut und keine Abhängigkeit aufgenommen. Gemessener Ausgangswert 2026-09-22: P50 45,5 s, P95 150,6 s, 0 von 93 Antworten unter 5 s."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "Raum Achim / Lotse (chat.iil.pet)", commit_or_pr: "Messung 2026-09-22: 93 Antwortpaare Owner→Lotse aus 400 Ereignissen; P50 45,5 s · P90 119,6 s · P95 150,6 s · min 8,1 s · max 374,1 s; unter 1,5 s: 0; unter 5 s: 0; unter 15 s: 16", opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-249-voice-agent-architektur.md, commit_or_pr: "status: proposed, decision_date 2026-06-17 — NICHT accepted", opened_in_session: true}
  - {claim_id: C3, source_path: iil-voice-agent/src/voice_agent/ports/voice.py, commit_or_pr: "VoicePort: transcribe(audio: bytes) -> str, synthesize(text: str) -> bytes — Batch, keine Ströme, kein Abbruch", opened_in_session: true}
  - {claim_id: C4, source_path: chat-hub/deploy/livekit/livekit.yaml, commit_or_pr: "port 7880, udp_port 7882, tcp_port 7881, turn.enabled: false", opened_in_session: true}
  - {claim_id: C5, source_path: chat-hub/deploy/docker-compose.rtc.yml, commit_or_pr: "livekit/livekit-server + element-hq/lk-jwt-service + nginx, beide mit sha256-Pin; LIVEKIT_FULL_ACCESS_HOMESERVERS chat.iil.pet", opened_in_session: true}
  - {claim_id: C6, source_path: docs/konzepte/KONZ-platform-060-lotse-stimme-im-raum.md, commit_or_pr: "Sprachnachrichten-Pfad seit 2026-09-22 in Betrieb; TTS 15,2 s Audio in 2,0 s Rechenzeit auf CPU; gemessener Kreis 10:47:08 -> 10:47:22", opened_in_session: true}
  - {claim_id: C7, source_path: infra/hosts.yaml, commit_or_pr: "dev-desktop auflage.prod_container=false, Ausnahme lotse-raum bis 2026-12-01 (heute eingetragen)", opened_in_session: true}
  - {claim_id: H1, source_path: "matrix-nio / LiveKit Agents SDK", commit_or_pr: "HYPOTHESE, nicht geprueft: MatrixRTC-Schluesselverteilung (Element Call E2EE) wird vom Python-SDK nicht implementiert; nio kennt m.call.member nicht", opened_in_session: false}
created: 2026-09-22
---

# KONZ-platform-062 — Der Lotse im Gespräch

> **Selbstbetreffend** (Charta Art. 3). Auftrag des Owners 2026-09-22: Konzept schreiben,
> nicht bauen. Dieses Konzept empfiehlt ausdrücklich, **zunächst nicht zu bauen** — und
> nennt die eine Messung, die darüber entscheidet.

## 1 Executive Summary

Der Lotse kann seit heute sprechen (KONZ-060, C6). Die nächste Stufe wäre das Gespräch:
Vollduplex im Element Call, unterbrechbar. Der Medienweg dafür läuft bereits produktiv
(LiveKit SFU + MatrixRTC-Auth, C5), und die Sprachbausteine sind schnell genug (TTS 7,6×
Echtzeit auf CPU, C6). Trotzdem lautet die Empfehlung: **heute nicht bauen.**

Der Grund ist gemessen, nicht vermutet. Ein Gespräch verlangt eine Antwort in rund
anderthalb Sekunden. Der Lotse antwortet heute im Median nach **45,5 Sekunden**; von 93
echten Antworten lag **keine einzige** unter fünf Sekunden (C1). Der Engpass ist nicht das
Netz, nicht die Sprachsynthese und nicht der Videostack — es ist der Denker dahinter, der
Werkzeuge benutzt, Dateien liest und Befunde prüft. Genau das macht den Lotsen nützlich; es
macht ihn zugleich gesprächsuntauglich. Ein Vollduplex-Kanal auf einen 45-Sekunden-Denker
erzeugt entweder Dauerpausen oder Füllwort-Theater.

Zweiter Befund: Die Fähigkeit ist bereits einem anderen Ort zugesprochen. ADR-249 steht auf
`proposed` (C2), und sein Sprach-Port ist mit `transcribe(bytes) -> str` /
`synthesize(str) -> bytes` (C3) strukturell Batch — Vollduplex bräuchte Ströme und Abbruch.
Wer im chat-hub baut, baut entweder am Kanon vorbei oder ändert ihn; beides offen zu lassen
ist die teuerste Variante.

Deshalb: eine Vorprüfung (V1) mit klarer Schwelle, ein zweiter billiger Test (V2, E2EE), und
erst danach die Bauentscheidung. Kosten der Vorprüfung: Stunden. Kosten des Irrtums ohne sie:
Wochen für eine Fähigkeit, die nach der Demo nicht benutzt wird.

## 2 Scope & Evidenzbasis

**In Scope:** Der Lotse als Teilnehmer eines Element Calls, der zuhört und spricht, für den
Owner allein. **Out of Scope:** Telefonie/SIP, Mehrpersonen-Gespräche, Kundenpiloten — die
gehören zum Produkt `iil-assist-voice` (ADR-249).

Evidenz: C1–C7 in dieser Sitzung geöffnet und gemessen; H1 ausdrücklich Hypothese.

## 3 Infrastruktur-Fit

| Baustein | Relevant? | Wiederverwenden | Erweitern | Risiko | Kommentar |
|---|---:|---|---|---|---|
| LiveKit SFU + `lk-jwt-service` (prod-b) | ja | vollständig | — | niedrig | läuft produktiv, sha256-gepinnt (C5) |
| Netzweg dev-desktop → prod-b | ja | — | UDP 7882 prüfen | mittel | `turn.enabled: false` (C4): kein Fallback, wenn UDP blockiert |
| STT faster-whisper `small` (CPU) | ja | Modell | Streaming statt Batch | mittel | heute Datei-basiert, Gespräch braucht laufende Erkennung |
| TTS Piper (CPU) | ja | vollständig | Abbruch mitten im Satz | niedrig | 7,6× Echtzeit (C6) reicht |
| Lotse-Denker (Claude-Code-Sitzung) | ja | **nein** | — | **hoch** | P50 45,5 s (C1) — der Engpass |
| Krypto-Store / E2EE | ja | — | MatrixRTC-Schlüssel | **hoch** | H1: SDK-Unterstützung ungeprüft |
| Host dev-desktop | ja | — | zweiter Dauerprozess | mittel | Ausnahme endet 2026-12-01 (C7) |

## 4 Steelman

Vollduplex ist kein schnelleres Sprachmemo, sondern eine andere Form: Eine Sprachnachricht
zwingt den Sprecher, den Auftrag vollständig zu formulieren, bevor irgendetwas passiert; steckt
im ersten Satz der Antwort ein Missverständnis, kostet die Korrektur einen ganzen Zyklus. Im
Gespräch kostet sie zwei Sekunden. Aufträge an den Lotsen sind selten beim ersten Anlauf
präzise — Repo, Scope, Gate, Ausnahme —, und ein Medium, das jede Rückfrage mit einem vollen
Zyklus bestraft, erzieht zu unpräzisen Großaufträgen. Der Bestand trägt das Vorhaben zudem
weitgehend: Der schwierigste Teil, der Echtzeit-Medienpfad, läuft produktiv (C5), die
Sprachbausteine sind vermessen (C6), es fehlt Klebearbeit statt eines Subsystems. Und ein
interner Gesprächsfall wäre der erste echte Lastfall für ADR-249 — ausgerechnet in der Variante
`sovereignty: strict`, die am schwersten zu belegen ist: lokal, verschlüsselt, ohne Cloud.

## 5 Konzeptdefinition

**Zielbild:** Der Owner startet im Raum einen Call; der Lotse tritt bei, hört zu, antwortet
gesprochen, lässt sich unterbrechen und schweigt, wenn er nichts beizutragen hat. Er tut im
Gespräch **nichts Wirksames** — keine Issues, keine PRs, keine Prod-Schritte; er nimmt
Aufträge auf und legt sie nach dem Gespräch als Entwurf in den Raum (Charta Art. 2, und die
Freigabe bleibt bei KONZ-061).

**Zwei Denker statt einem.** Die Messung (C1) erzwingt die Trennung:

| Rolle | Aufgabe | Latenzbudget | Modell |
|---|---|---|---|
| Gesprächs-Denker | zuhören, antworten, nachfragen, notieren | < 1,5 s bis erstes Wort | kleines lokales Modell, keine Werkzeuge |
| Arbeits-Denker | prüfen, bauen, Entwürfe schreiben | heute 45,5 s (C1), unverändert | heutige Lotse-Sitzung |

Der Gesprächs-Denker sagt „das notiere ich" und reicht weiter; er behauptet nie ein Ergebnis,
das er nicht hat. Ohne diese Trennung ist Vollduplex nicht erreichbar — das ist der Kern
dieses Konzepts.

## 6 Adversariale Analyse

**Konfliktmatrix** (drei unabhängige Prüfer, die sich nicht gesehen haben):

| # | Dissens | Steelman | Diabolus | Maintainer 2028 | Auflösung |
|---|---|---|---|---|---|
| K1 | Ist der Bestand tragend oder trügerisch? | Medienpfad läuft produktiv, es fehlt Klebearbeit | SDK bringt eigenes Sitzungsmodell mit und wird zur Architektur-Grenze | zwei Hosts, zwei Lebenszyklen, Versionen müssen zusammenpassen | Beide recht: der **Medienpfad** trägt, die **Gesprächssemantik** nicht. Deshalb V2 vor jeder Abhängigkeit |
| K2 | Latenz | 14 s Kreis, TTS nicht der Engpass | Engpass ist das LLM; Log-Auswertung entscheidet alles | — | **Gemessen (C1): Diabolus bestätigt.** P50 45,5 s. Steelmans 14 s waren ein Einzelfall, nicht der Median |
| K3 | Verhältnis zu ADR-249 | interner Fall validiert das Produkt | ADR ist `proposed`, Port ist Batch — dritte Implementierung droht | zwei Repos, eine Fähigkeit; 2028 fasse ich das falsche an | **Gemessen (C2/C3): Diabolus bestätigt.** Vor dem Bau: ADR-249 annehmen oder ablösen, je eine Zeile in beiden READMEs |
| K4 | Nutzung nach der Demo | Risiko additiv, Rückfall auf heutigen Stand | Prognose: Call-Anbindung wird gebaut und nicht benutzt | ungenutzt = unbemerkt kaputt, kostet trotzdem | Kill-Gate mit Nutzungszähler **vor** dem Bau festschreiben |
| K5 | Kein Dissens | — | dev-desktop-Ausnahme läuft 2026-12-01 aus | dieselbe Frist, unabhängig genannt | Zielhost benennen, bevor ein zweiter Dauerprozess dort entsteht |

**Diabolus-Pflichtfragen:** Doppelquelle → K3, belegt. SSoT nur behauptet → C2, ein
`proposed`-ADR kann nichts durchsetzen. Werkzeug wird Grenze → K1. Manuelle Pflicht ohne
Durchsetzung → C7, die Frist steht im Text, nicht in einem Melder. „Sichtbar machen" schwächer
als „verhindern" → B9 unten (Dritte im Call).

## 7 Deep-Dive: die vier harten Stellen

1. **Latenz (entschieden, C1).** Gespräch verlangt ~1,5 s; gemessen sind 45,5 s im Median.
   Ohne zweiten, werkzeuglosen Denker ist das Vorhaben tot. Das ist kein Optimierungsthema.
2. **E2EE (H1, ungeprüft).** Element Call verteilt Per-Teilnehmer-Schlüssel über den Matrix-Raum.
   Implementiert das Agent-SDK das nicht, hört der Bot Rauschen — oder der Call müsste
   unverschlüsselt laufen, was der serverseitigen Raumverschlüsselung widerspricht.
3. **Echo und Unterbrechung.** Der Bot hat kein Gerätepaar, also kein Geräte-Echo. Das Echo
   entsteht beim Owner: Bot-Stimme aus dem Lautsprecher, zurück ins Mikrofon, der Bot
   transkribiert sich selbst und hält es für eine Unterbrechung. Kopfhörer sind eine
   Bedienregel, keine Lösung.
4. **Dritte im Call.** Sobald jemand Drittes beitritt, läuft dessen Stimme durch die
   Spracherkennung, bevor irgendeine Einwilligung vorliegt. Anzeigen reicht nicht —
   der Bot verlässt den Call hart (siehe §12 REC-5).

## 8 Alternativen

| # | Alternative | Bewertung |
|---|---|---|
| ALT-1 | **Halbduplex-Call** („Push to talk"): Owner spricht, gibt frei, Lotse antwortet | Kommt ohne Gesprächs-Denker aus, löst Echo und Barge-in per Bauart. Deutlich billiger, deckt den Rückfrage-Nutzen aus §4 zu großen Teilen. **Stärkster Gegenkandidat** |
| ALT-2 | Bau in `iil-assist-voice` statt chat-hub | Architektonisch sauber (C2/C3), aber dort fehlt alles: kein Deploy, kein Matrix-Client, kein Krypto-Store. Erst nach ADR-249-Annahme sinnvoll |
| ALT-3 | Sprachnachrichten schneller machen (kleineres Modell, sofort sprechen) | Senkt die 14 s spürbar, ändert die Form nicht. Billig, sofort machbar, schließt Vollduplex nicht aus |
| ALT-4 | Gar nichts tun | Der heutige Stand ist seit einem Tag in Betrieb und noch nicht ausgemessen. Bis zum Kill-Gate von KONZ-060 (2026-10-20) ist Warten ein vertretbarer Zug |

## 9 Out-of-the-Box

Der Gesprächs-Denker muss nicht klug sein, sondern **schnell und ehrlich**: Er darf fast nur
drei Dinge sagen — „verstanden, notiert", „meinst du X oder Y?", „das schaue ich nach, ich
melde mich im Raum". Ein solcher Agent ist mit einem kleinen lokalen Modell erreichbar und
wäre zugleich der ehrlichste Umgang mit der Latenz: nicht verstecken, sondern benennen.

## 10 Befunde

| # | Befund | Evidenz | Konsequenz |
|---|---|---|---|
| B1 | ADR-249 ist `proposed`, nicht beschlossen — der beanspruchte Kanon kann nichts durchsetzen | C2 | Vor dem Bau annehmen oder ablösen (REC-3) |
| B2 | Der Sprach-Port ist Batch (`bytes -> str`), Vollduplex bräuchte Ströme mit Abbruch | C3 | Amendment nötig, sonst dritte Implementierung |
| B3 | **Antwortlatenz P50 45,5 s, P95 150,6 s, 0 von 93 unter 5 s** | C1 | Vorprüfung V1 ist das Kill-Gate |
| B4 | `turn.enabled: false` — kein TURN-Fallback, wenn UDP 7882 blockiert ist | C4 | V2 misst den Netzweg mit |
| B5 | E2EE-Schlüsselverteilung im Agent-SDK ungeprüft | H1 | V2, vor jeder Abhängigkeit |
| B6 | Echo entsteht beim Owner, nicht am Bot | §7.3 | Kopfhörer-Regel + Selbsthör-Test |
| B7 | Dritte im Call laufen durch die Spracherkennung | §7.4 | REC-5: harter Austritt |
| B8 | dev-desktop-Ausnahme endet 2026-12-01, das Vorhaben verdoppelt die Bindung an den Host | C7 | Zielhost vor dem Bau benennen |
| B9 | Keine der Lotse-Units hat `OnFailure=`/`Restart=`; ein stiller Ausfall bleibt still | Maintainer M3 | REC-6, unabhängig von diesem Vorhaben nützlich |
| B10 | Modelle ohne Stückliste (Version, Prüfsumme, Quelle), Piper in zwei venvs | Maintainer M5 | REC-7 |
| B11 | Gespräche erzeugen Audio und Transkripte ohne Aufbewahrungsfrist | Maintainer M10 | REC-8, **vor** dem ersten Call festlegen |

## 11 Top-5-Risiken

| # | Risiko | Wirkung | Gegenmittel |
|---|---|---|---|
| RISK-1 | Gebaut, dann nicht benutzt (Präzedenz: `iil-assist-voice` als Gerüst) | Wochen verloren | Kill-Gate mit Nutzungszähler vor dem Bau |
| RISK-2 | Latenz lässt sich nicht drücken | Vorhaben tot nach dem Bau statt davor | V1 ist Vorbedingung, nicht Begleitmessung |
| RISK-3 | E2EE-Bruch erzwingt unverschlüsselte Calls | Verstoß gegen die eigene Grundregel | V2; bei Fehlschlag Ende |
| RISK-4 | Dritte werden unbemerkt transkribiert | Einwilligung verletzt | harter Austritt, kein Hinweis-Text |
| RISK-5 | Hostfrist läuft, Bindung wächst | Ausnahme wird still ewig | Zielhost benennen, Frist als Issue führen |

## 12 Empfehlungen

| # | Empfehlung | Owner | Aufwand |
|---|---|---|---|
| REC-1 | **V1 Latenz-Vorprüfung**: werkzeugloser Gesprächs-Denker (kleines lokales Modell) an den bestehenden Sprachnachrichten-Pfad hängen und 20 echte Turns messen. Schwelle: P50 < 2,0 s, P95 < 4,0 s bis erstes hörbares Wort | ich, nach Owner-Wort | 1–2 Tage |
| REC-2 | **V2 Call-Vorprüfung**: mit `lk-jwt-service`-Token einem echten Element Call beitreten, 10 s Audio ziehen, Lautstärke messen (Stille = E2EE-Bruch, B5) und UDP 7882 vom dev-desktop prüfen (B4) | ich, nach V1 | 0,5 Tag |
| REC-3 | ADR-249 annehmen oder als abgelöst markieren; je eine Zeile in beiden READMEs, wo die Fähigkeit lebt | Owner + ich | 0,5 Tag |
| REC-4 | ALT-1 (Halbduplex) als billigen Zwischenschritt bewerten, falls V1 scheitert | ich | 1 Tag |
| REC-5 | Regel festschreiben: dritter Teilnehmer im Call → Lotse verlässt ihn sofort | Owner | Entscheidung |
| REC-6 | `OnFailure=` für alle vier `lotse-*`-Units + „letzter Erfolg"-Zeitstempel je Fähigkeit (B9) | ich | 0,5 Tag, unabhängig nützlich |
| REC-7 | Modell-Stückliste (Name, Version, URL, sha256, Zielpfad) + ein venv (B10) | ich | 0,5 Tag |
| REC-8 | Aufbewahrungsfrist für Audio und Transkripte festlegen, **bevor** der erste Call läuft (B11) | Owner | Entscheidung |

## 13 Entscheidung + Kill-Gate + 30/60/90

**Entscheidung:** Kein Bau, keine neue Abhängigkeit, kein LiveKit-Agent — bis V1 und V2
bestanden sind. Die Empfehlungen REC-6 bis REC-8 sind davon unabhängig und lohnen sich auch,
wenn S4 nie kommt.

| Kriterium | Status | Beleg |
|---|---|---|
| V1: P50 < 2,0 s und P95 < 4,0 s über 20 Turns bis 2026-11-30 | offen | Ausgangswert 45,5 s / 150,6 s (C1) |
| V2: Bot hört im E2EE-Call echtes Audio (RMS > Rauschgrenze) | offen | — |
| V2b: UDP 7882 dev-desktop → prod-b offen | offen | `turn.enabled: false` (C4) |
| ADR-249 entschieden (accepted oder abgelöst) | offen | `status: proposed` (C2) |
| Aufbewahrungsfrist für Audio festgelegt | offen | — |

**30 Tage** (bis 2026-10-22): REC-6/7/8 erledigt; KONZ-060-Kill-Gate ausgewertet — nutzt der
Owner Sprachnachrichten überhaupt?
**60 Tage** (bis 2026-11-21): V1 gemessen. Reißt die Schwelle, wird ALT-1 bewertet und dieses
Konzept auf `sunset` gesetzt.
**90 Tage** (bis 2026-12-21): nur bei bestandenem V1/V2 — Bauentscheidung mit Zielhost (B8)
und entschiedenem ADR-249.
