---
concept_id: KONZ-platform-062
title: Der Lotse im Gespräch — Vollduplex im Videocall, und warum die Messung zuerst kommt
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: Amendment   # ERLEDIGT 2026-09-22: ADR-249 ist angenommen (Rev 2) und grenzt in §2.0 ab — Produkt-Voice dort, Assistenten-Stimme im chat-hub. Ein Gespräch (Vollduplex) berührt G-4/G-9 und braucht beim Bau ein Amendment dort, nicht daran vorbei.
review_by: 2026-12-01
kill_criteria: "V1 BESTANDEN und Knoten benannt (gx10). V1 am 2026-09-22: P50 0,39 s, P95 0,94 s über 20 Turns bis zum ersten hörbaren Wort (Schwelle war 2,0 / 4,0 s). Das Vorhaben ist beendet, wenn V2 (Beitritt zu einem E2EE-Call mit nachweislich hörbarem Audio) nicht bis 2026-11-30 gelingt ODER der Gespraechs-Denker wieder an einem Knoten haengt, dessen Betrieb nicht zugesagt ist (die GPU-Box war nur der Messweg; gebaut wird gegen die gx10). Ausgangswert des heutigen Lotsen zum Vergleich: P50 45,5 s."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "Raum Achim / Lotse (chat.iil.pet)", commit_or_pr: "Messung 2026-09-22: 93 Antwortpaare Owner→Lotse aus 400 Ereignissen; P50 45,5 s · P90 119,6 s · P95 150,6 s · min 8,1 s · max 374,1 s; unter 1,5 s: 0; unter 5 s: 0; unter 15 s: 16", opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-249-telefonagent-produkt-swappable-ports.md, commit_or_pr: "Stand bei Konzeptschluss: status proposed, decision_date 2026-06-17 — seit Rev 2 accepted, siehe C10", opened_in_session: true}
  - {claim_id: C3, source_path: iil-voice-agent/src/voice_agent/ports/voice.py, commit_or_pr: "VoicePort: transcribe(audio: bytes) -> str, synthesize(text: str) -> bytes — Batch, keine Ströme, kein Abbruch", opened_in_session: true}
  - {claim_id: C4, source_path: chat-hub/deploy/livekit/livekit.yaml, commit_or_pr: "port 7880, udp_port 7882, tcp_port 7881, turn.enabled: false", opened_in_session: true}
  - {claim_id: C5, source_path: chat-hub/deploy/docker-compose.rtc.yml, commit_or_pr: "livekit/livekit-server + element-hq/lk-jwt-service + nginx, beide mit sha256-Pin; LIVEKIT_FULL_ACCESS_HOMESERVERS chat.iil.pet", opened_in_session: true}
  - {claim_id: C6, source_path: docs/konzepte/KONZ-platform-060-lotse-stimme-im-raum.md, commit_or_pr: "Sprachnachrichten-Pfad seit 2026-09-22 in Betrieb; TTS 15,2 s Audio in 2,0 s Rechenzeit auf CPU; gemessener Kreis 10:47:08 -> 10:47:22", opened_in_session: true}
  - {claim_id: C7, source_path: infra/hosts.yaml, commit_or_pr: "dev-desktop auflage.prod_container=false, Ausnahme lotse-raum bis 2026-12-01 (heute eingetragen)", opened_in_session: true}
  - {claim_id: C8, source_path: "Messung V1 (platform#3370)", commit_or_pr: "2026-09-22, 20 Turns werkzeugloser Denker qwen2.5:7b + Piper: P50 0,39 s, P95 0,94 s bis erstes hoerbares Wort; Kaltstart 32 s; localhost:11434 loest auf ::1 und tunnelt nach 10.99.0.2:11434 (GPU-Box), lokales ollama auf 127.0.0.1 ohne geladenes Modell", opened_in_session: true}
  - {claim_id: C9, source_path: infra/ports.yaml, commit_or_pr: "gpu-ollama: prod_host gpu-box, Ursprung 10.99.0.2:11434 ueber wg0, betriebsstatus: blockiert", opened_in_session: true}
  - {claim_id: C10, source_path: docs/adr/ADR-249-telefonagent-produkt-swappable-ports.md, commit_or_pr: "Rev 2, 2026-09-22: status accepted, §2.0 grenzt Produkt-Voice von der Assistenten-Stimme ab (Owner-Wort)", opened_in_session: true}
  - {claim_id: C11, source_path: "Messung gx10 (platform#3370)", commit_or_pr: "2026-09-22 ueber prod nach 10.99.0.4:11434: 6 Modelle inkl. qwen2.5:7b; kalt laden 3,74 s, danach 3 Laeufe 0,34/0,59/0,64 s gesamt. hosts.yaml: gx10 = wg0-Peer 10.99.0.4, Standort Owner-Buero", opened_in_session: true}
  - {claim_id: H1, source_path: "matrix-nio / LiveKit Agents SDK", commit_or_pr: "HYPOTHESE, nicht geprueft: MatrixRTC-Schluesselverteilung (Element Call E2EE) wird vom Python-SDK nicht implementiert; nio kennt m.call.member nicht", opened_in_session: false}
created: 2026-09-22
---

# KONZ-platform-062 — Der Lotse im Gespräch

> **Selbstbetreffend** (Charta Art. 3). Auftrag des Owners 2026-09-22: Konzept schreiben,
> nicht bauen. **Rev 2, noch am selben Tag:** V1 wurde ausgeführt und ist bestanden — die
> Latenz ist kein Ausschlussgrund mehr. Was unten als Hauptargument gegen den Bau stand,
> ist damit erledigt; an seine Stelle treten zwei andere Fragen (§1 Nachtrag).

## 1 Executive Summary

Der Lotse kann seit heute sprechen (KONZ-060, C6). Die nächste Stufe wäre das Gespräch:
Vollduplex im Element Call, unterbrechbar. Der Medienweg dafür läuft bereits produktiv
(LiveKit SFU + MatrixRTC-Auth, C5), und die Sprachbausteine sind schnell genug (TTS 7,6×
Echtzeit auf CPU, C6).

Der ursprüngliche Einwand war gemessen, nicht vermutet: Ein Gespräch verlangt eine Antwort
in rund anderthalb Sekunden, der Lotse antwortet im Median nach **45,5 Sekunden**, und von
93 echten Antworten lag **keine einzige** unter fünf (C1). Der Engpass ist nicht das Netz,
nicht die Sprachsynthese und nicht der Videostack — es ist der Denker dahinter, der Werkzeuge
benutzt, Dateien liest und Befunde prüft. Genau das macht den Lotsen nützlich und zugleich
gesprächsuntauglich.

**Nachtrag Rev 2 (V1 ausgeführt, C8):** Ein zweiter, **werkzeugloser** Denker antwortet über
dieselbe Sprachstrecke in **0,39 s** im Median (P95 0,94 s) bis zum ersten hörbaren Wort —
die Schwelle lag bei 2,0 s. Die Trennung aus §5 ist damit kein Entwurf mehr, sondern
gemessen. An die Stelle der Latenz treten zwei neue Fragen:

1. **Woran hängt die Antwort?** Der schnelle Weg läuft nicht auf der dev-desktop-CPU,
   sondern über einen SSH-Tunnel auf die **GPU-Box** — einen Knoten, der im Register als
   `betriebsstatus: blockiert` geführt wird (C8, C9). Eine Fähigkeit, die an einem nicht
   zugesagten Knoten hängt, ist keine Fähigkeit, sondern ein Gefallen.
2. **Kaltstart.** Nach fünf Minuten Stille kostet der erste Satz **32 s**. In der Messung
   per `keep_alive` im Aufruf umgangen; im Betrieb braucht es eine bewusste Entscheidung,
   ein Modell vorzuhalten.

Zweiter Befund des Ursprungs, ebenfalls erledigt: Die Fähigkeit war einem anderen Ort
zugesprochen. ADR-249 ist seit dem 2026-09-22 **angenommen** und grenzt in §2.0 ab —
Produkt-Voice dort, Assistenten-Stimme hier (C10). Sein Sprach-Port bleibt mit
`transcribe(bytes) -> str` / `synthesize(str) -> bytes` (C3) Batch; ein Vollduplex-Bau
braucht dort ein Amendment, nicht ein Vorbeibauen.

Es bleibt: **V2 (Call-Beitritt mit hörbarem Audio im E2EE-Call) zuerst**, dann die
Bauentscheidung — mit benanntem Knoten für den Gesprächs-Denker.

## 2 Scope & Evidenzbasis

**In Scope:** Der Lotse als Teilnehmer eines Element Calls, der zuhört und spricht, für den
Owner allein. **Out of Scope:** Telefonie/SIP, Mehrpersonen-Gespräche, Kundenpiloten — die
gehören zum Produkt `iil-assist-voice` (ADR-249).

Evidenz: C1–C11 in dieser Sitzung geöffnet und gemessen; H1 ausdrücklich Hypothese.

## 3 Infrastruktur-Fit

| Baustein | Relevant? | Wiederverwenden | Erweitern | Risiko | Kommentar |
|---|---:|---|---|---|---|
| LiveKit SFU + `lk-jwt-service` (prod-b) | ja | vollständig | — | niedrig | läuft produktiv, sha256-gepinnt (C5) |
| Netzweg dev-desktop → prod-b | ja | — | UDP 7882 prüfen | mittel | `turn.enabled: false` (C4): kein Fallback, wenn UDP blockiert |
| STT faster-whisper `small` (CPU) | ja | Modell | Streaming statt Batch | mittel | heute Datei-basiert, Gespräch braucht laufende Erkennung |
| TTS Piper (CPU) | ja | vollständig | Abbruch mitten im Satz | niedrig | 7,6× Echtzeit (C6) reicht |
| Lotse-Denker (Claude-Code-Sitzung) | ja | **nein** | — | **hoch** | P50 45,5 s (C1) — der Engpass, deshalb §5 zwei Denker |
| Gesprächs-Denker (`qwen2.5:7b`, ollama auf **gx10**) | ja | vorhanden | Systemsatz, Abbruch | mittel | V1 bestanden: P50 0,39 s bis hörbar (C8). Knoten ist die gx10 (C11): warm 0,34–0,64 s, kalt 3,7 s, aktiv deklariert. Die GPU-Box (`blockiert`, C9) war nur der Weg, über den gemessen wurde |
| Modell-Kaltstart | ja | — | Vorhalten | niedrig | Auf der GPU-Box 32 s nach Leerlauf, **auf der gx10 3,7 s** (C11) — dort ist der Kaltstart kein Gesprächsabbruch mehr, nur eine Pause. `keep_alive` im Aufruf senkt ihn weiter, ohne Host-Eingriff |
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
| RISK-2 | ~~Latenz~~ ~~blockierter Knoten~~ **beides erledigt**: V1 bestanden (C8), Knoten ist die gx10 (C11). Rest-Risiko: sie steht im Owner-Büro an einem Hausanschluss, nicht im Rechenzentrum | Gespräch fällt aus, wenn die Leitung dorthin fällt | Ausfall macht den Lotsen nicht stumm — Sprachnachrichten laufen ohne sie |
| RISK-3 | E2EE-Bruch erzwingt unverschlüsselte Calls | Verstoß gegen die eigene Grundregel | V2; bei Fehlschlag Ende |
| RISK-4 | Dritte werden unbemerkt transkribiert | Einwilligung verletzt | harter Austritt, kein Hinweis-Text |
| RISK-5 | Hostfrist läuft, Bindung wächst | Ausnahme wird still ewig | Zielhost benennen, Frist als Issue führen |

## 12 Empfehlungen

| # | Empfehlung | Owner | Aufwand |
|---|---|---|---|
| REC-1 | ✅ **erledigt 2026-09-22** — V1 gemessen: P50 0,39 s, P95 0,94 s über 20 Turns (Schwelle 2,0 / 4,0 s), C8 | — | — |
| REC-1b | ✅ **entschieden 2026-09-22 (Owner): die gx10.** Sie hält `qwen2.5:7b` bereits vor, antwortet warm in 0,34–0,64 s und lädt kalt in **3,7 s** statt 32 s; sie ist aktiv deklariert, nicht `blockiert`. Zu tun: zweiter SSH-Tunnel nach dem Muster des bestehenden (über prod nach `10.99.0.4:11434`) (C11) | ich | 0,25 Tag |
| REC-1c | **NEU aus V1:** Kaltstart abstellen (32 s nach Leerlauf). Billigster Weg ohne Host-Eingriff: `keep_alive` im Aufruf; dauerhaft: Modell vorhalten | ich | 0,5 Tag |
| REC-2 | **V2 Call-Vorprüfung**: mit `lk-jwt-service`-Token einem echten Element Call beitreten, 10 s Audio ziehen, Lautstärke messen (Stille = E2EE-Bruch, B5) und UDP 7882 vom dev-desktop prüfen (B4) | ich, nach V1 | 0,5 Tag |
| REC-3 | ✅ **erledigt 2026-09-22** — ADR-249 angenommen (Rev 2), §2.0 grenzt Produkt-Voice von der Assistenten-Stimme ab (C10). Offen bleibt die Zeile in beiden READMEs | ich | 0,25 Tag |
| REC-4 | ALT-1 (Halbduplex) — nach bestandenem V1 **kein** Rückfallplan mehr, sondern eine eigenständige Option: kommt ohne Echo- und Barge-in-Problem aus | ich | 1 Tag |
| REC-5 | Regel festschreiben: dritter Teilnehmer im Call → Lotse verlässt ihn sofort | Owner | Entscheidung |
| REC-6 | `OnFailure=` für alle vier `lotse-*`-Units + „letzter Erfolg"-Zeitstempel je Fähigkeit (B9) | ich | 0,5 Tag, unabhängig nützlich |
| REC-7 | Modell-Stückliste (Name, Version, URL, sha256, Zielpfad) + ein venv (B10) | ich | 0,5 Tag |
| REC-8 | Aufbewahrungsfrist für Audio und Transkripte festlegen, **bevor** der erste Call läuft (B11) | Owner | Entscheidung |

## 13 Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (Rev 3, 2026-09-22):** V1 ist bestanden, ADR-249 angenommen und abgegrenzt, der
Knoten ist benannt (gx10, C11). Damit steht **nur noch V2** zwischen diesem Konzept und einer
Bauentscheidung: Gelingt der Beitritt zu einem E2EE-Call mit hörbarem Audio, wird gebaut;
hört der Lotse Stille, endet S4 in dieser Form und ALT-1 (Halbduplex) rückt nach. Die Empfehlungen REC-6 bis REC-8 sind davon unabhängig und lohnen sich auch,
wenn S4 nie kommt.

> **Stand dieser Tabelle: 2026-09-22 Abend** (Rev 4). Sie ist der maßgebliche
> Statusträger — widerspricht ihr der Fließtext oben, gilt die Tabelle. Die
> Session-Retro fand genau diesen Widerspruch: Prosa und REC-1 meldeten V1 als
> bestanden, während hier noch „offen" mit dem Ausgangswert stand.

| Kriterium | Status | Beleg |
|---|---|---|
| V1: P50 < 2,0 s und P95 < 4,0 s über 20 Turns | ✅ **erfüllt** 2026-09-22 | P50 0,39 s, P95 0,94 s bis erstes hörbares Wort (C8) |
| V2: Bot hört im E2EE-Call echtes Audio | **offen** | noch kein Beitritt versucht; H1 (MatrixRTC-Schlüssel im SDK) unverändert ungeprüft |
| V2b: Medienstrecke dev-desktop → prod-b offen | ✅ **erfüllt** 2026-09-22 | Firewall-Regeln 7881/7882 ergänzt (#3374); Owner-Abnahme mit echtem Videoanruf, Bild und Ton (chat-hub#127) |
| ADR-249 entschieden (accepted oder abgelöst) | ✅ **erfüllt** 2026-09-22 | `status: accepted`, Rev 2 mit Abgrenzung §2.0 (C10) |
| Knoten für den Gesprächs-Denker benannt (REC-1b) | ✅ **erfüllt** 2026-09-22 | gx10, warm 0,34–0,64 s, kalt 3,7 s (C11) |
| Aufbewahrungsfrist für Audio festgelegt | **offen** | Owner-Entscheidung, REC-8 |

**Damit steht S4 auf zwei offenen Punkten: V2 und der Aufbewahrungsfrist.** Beide
sind Vorbedingung, nicht Begleitarbeit — vor ihnen wird nichts gebaut.

**30 Tage** (bis 2026-10-22): REC-6/7/8 erledigt; KONZ-060-Kill-Gate ausgewertet — nutzt der
Owner Sprachnachrichten überhaupt?
**60 Tage** (bis 2026-11-21): V1 gemessen. Reißt die Schwelle, wird ALT-1 bewertet und dieses
Konzept auf `sunset` gesetzt.
**90 Tage** (bis 2026-12-21): nur bei bestandenem V1/V2 — Bauentscheidung mit Zielhost (B8)
und entschiedenem ADR-249.
