---
status: proposed
decision_date: 2026-08-14
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-292, ADR-289, ADR-084, ADR-059]
implementation_status: none
last_reviewed: 2026-08-14
staleness_months: 6
tags: [gpu, lease-arbiter, illustration-hub, music-lab, writing-hub, aifw, medien-arbeitsflaeche, iil-gpufw]
---

# ADR-296: GPU-Box über Hub-seitigen Lease-Arbiter bewirtschaften — Medien-Arbeitsfläche und Client-Paket folgen dem Hub

> **Nummern-Hinweis:** 296 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).
>
> **Entstehung:** Synthese aus einem adversarialen Design-Panel (2026-08-14):
> 3 unabhängige Gesamtentwürfe (hub-zentriert, box-zentriert, minimal-inkrementell)
> × je 2 adversariale Prüfungen (Betriebsrealität, Nebenläufigkeit) × 3 Richter mit
> unterschiedlicher Treiber-Gewichtung. 2 von 3 Richtern kürten hub-zentriert; alle
> 24 Schwer-Befunde des Panels sind unten als Vertragseigenschaften bzw. Risiken
> eingearbeitet. Kein Entwurf trug einen unheilbaren Befund.

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform (cross-repo)                                                |
| **Erstellt**    | 2026-08-14                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-292 (Two-Lane-Deployment; illustration-hub-Ausnahme), ADR-289 (netcup-Offsite-Backup), ADR-084 (illustration-fw als PyPI-Paket), ADR-059 (Drift-Detector) |

## Repo-Zugehörigkeit

| Repo               | Rolle      | Betroffene Pfade / Komponenten                          |
|--------------------|------------|---------------------------------------------------------|
| `platform`         | Referenz   | `docs/adr/`                                             |
| `illustration-hub` | Primär     | `apps/jobs/` (Arbiter + Lease-API), NEU `apps/music/`   |
| `music-lab`        | Sekundär   | `box-setup/` (bleibt), CLI wird Client der Hub-API      |
| `writing-hub`      | Sekundär   | aifw-Routing Batch-Lane (Migrationsschritt 6)           |
| `aifw`             | Sekundär   | optionale Abhängigkeit `iil-gpufw` für Batch-Lane       |

---

## Decision Drivers

- **Kosten**: Lokale Auslagerung soll bezahlte LLM-/Bild-Calls ersetzen; der stille
  Bezahl-Rückfall bei belegter Karte (illustration-hub#179, 2× reproduziert) darf in
  keiner neuen Lane zurückkehren.
- **Owner-Last**: Die Box ist nicht agent-deploybar (kein SSH/RDP/WinRM; jede
  Installation = manuelles PS1 über `~/shared` mit Minuten-Latenz und der
  music-lab#2-Fehlerklasse). Jede Komponente auf der Box ist eine dauerhafte
  Wartungs-Hypothek des Owners.
- **Verlässlichkeit**: Kein Koordinations-Handgriff darf Render/Song/Text
  *verhindern* — das Best-effort-Prinzip aus `gpu_arbitrierung.py` hat sich bewährt.
  Die teuersten Fehler der Vergangenheit waren stille (fal-Bezahlung; 2 Wochen
  toter Deploy-Pfad).
- **Evolvierbarkeit**: Die 4090 wird ersetzt werden, ein vierter Konsument ist
  denkbar; das Client-Interface darf die Bewirtschaftungs-Strategie nicht einfrieren.
- **Arbeitsfläche**: Owner-Ziel (wörtlich 2026-08-14): Texte und Musik *intensiv*
  weiterentwickeln — Versionen, Varianten, Vergleich, Suche. Das ist
  Datenmodell-Arbeit, die lose Dateien (`songs/*.txt`, `out/*.wav`) nicht tragen.

---

## 1. Context and Problem Statement

Auf der Windows-GPU-Box (RTX 4090, 24 GB VRAM, WireGuard-Peer `10.99.0.2`) teilen
sich drei Modell-Dienste eine Karte: ComfyUI (Bild, Port 8000), Ollama (Text,
Port 11434), ACE-Step (Song, Port 7865). Wer zuerst lädt, hält den Speicher; die
anderen scheitern mit `CUDA out of memory`. Heute existieren dafür **zwei
widersprüchliche Strategien**: illustration-hub entlädt kooperativ und best-effort
(`apps/jobs/gpu_arbitrierung.py`: vor dem Render `keep_alive:0` an Ollama, danach
`POST /free` an ComfyUI — bewusst kein Scheduler, illustration-hub#187), music-lab
schaltet exklusiv um (`box-setup/gpu-dienst.ps1` stoppt die jeweils anderen Dienste).

Mit dem Owner-Ziel, auch writing-hub-Arbeit lokal auszulagern („aifw kann das"),
kommen **unvereinbare Nutzungsmuster** dazu: Bild und Song wollen die Karte
stoßweise ganz; Text will resident bleiben (Kaltstart kostet je Anfrage). Ohne
Koordination entlädt jeder Bild-Auftrag das Sprachmodell mitten in der Textarbeit —
und der bezahlte Rückfall (fal bei Bild, Groq/Frontier bei Text) gibt wieder still
Geld aus, exakt die #179-Klasse.

Gleichzeitig hängen die Kriterien 1/2/6 aus music-lab#3 (dauerhaft abrufbare
Song-Bibliothek, feste URLs, gesicherte Ablage) an der Frage, **wo** die
Medien-Arbeitsfläche lebt — der Dev-Server hat keine Sicherung, das einzige
Offsite-Backup (ADR-289) läuft auf dem Prod-Host.

### 1.1 Ist-Zustand

| Aspekt | Stand 2026-08-14 |
|---|---|
| Karten-Koordination | kooperativ (illustration-hub) **und** exklusiv (music-lab) parallel — Kollision strukturell angelegt |
| Vorrang interaktiv/Batch | existiert nicht |
| „belegt ≠ kaputt" + Bezahl-Gate | nur in der Bild-Lane (`BELEGT_MARKER`, `darf_bei_belegter_karte_bezahlen()`) |
| Dritter Verbraucher (z.B. LoRA-Training) | von außen unsichtbar und unentladbar; `/system_stats vram_free` ist Melde-Artefakt (#187) |
| Song-Arbeitsfläche | lose Dateien auf dem ungesicherten Dev-Server; 1 Song (69 MB WAV) existiert |
| writing-hub → Box | noch kein Konsument; aifw v0.12 hat Provider `ollama` (base_url localhost), Route zur Box fehlt |

### 1.2 Warum jetzt

Der dritte Konsument ist beauftragt (Owner-Go 2026-08-14), music-lab#3 blockiert
auf der Arbeitsflächen-Entscheidung, und jeder weitere Ausbau der beiden
widersprüchlichen Strategien erhöht die Rückbaukosten.

---

## 2. Considered Options

### Option A: Hub-zentrierter Lease-Arbiter + Medien-Arbeitsfläche in illustration-hub ✅

Zustand und Intelligenz auf dem agent-deploybaren Prod-Host (Django/Postgres in
illustration-hub); die Box bleibt dumm (nur die vorhandenen Dienst-APIs, kein
neuer Box-Dienst im Regelbetrieb). Neue Django-App `apps/music` als Arbeitsfläche.
Repariert um die Panel-Befunde (atomarer Grant, Grund-Taxonomie, Heartbeats,
asymmetrische Degradation, Evidenzquellen-Kennzeichnung — Details §4).

**Pros:**
- Iterationsfähigste Komponente (Arbiter, 0.x-Phase mit häufigen Interface-Änderungen)
  liegt auf der agent-deploybaren Seite der `~/shared`-Latenzgrenze
- Lease-Zustand in Postgres: reboot-fest, im Offsite-Backup (ADR-289), per
  Admin/API einsehbar; TTL räumt verwaiste Leases ohne Skript ab
- Arbeitsfläche erbt Prod-Infrastruktur gratis: ADR-292-WG-Ausnahme ist schon
  erkämpft, Backup schon verdrahtet (music-lab#3 Kriterium 6 damit gelöst)
- Wiederverwendet die bewährten Bausteine (`ollama_entladen`, `comfyui_freigeben`,
  `BELEGT_MARKER`, Bezahl-Gate) statt sie zu duplizieren

**Cons:**
- Blast-Radius: ein illustration-hub-Deploy-Fehler trifft Bild **und** Song
- Der Arbiter sieht nur die kooperativen Konsumenten — eine Lease ist ein
  Versprechen unter Freunden, keine Wahrheit über die Karte (Mitigation: §4.4)
- Repo-Name illustration-hub wird unehrlich (Mitigation: Umbenennungs-Tracking, §5)

### Option B: Box-zentrierter Arbiter (Dienst auf der Box)

Arbiter als Windows-Dienst auf der Box; nur dort ist `nvidia-smi` und damit der
dritte Verbraucher sichtbar.

**Pros:**
- Prinzipiell echte Evidenz statt Absichts-Register; sieht auch Fremd-Prozesse

**Cons:**
- Owner-Last-Score 3/10 bei allen drei Richtern: jede Iteration der instabilsten
  Komponente = manuelles Admin-PS1 in der music-lab#2-Fehlerklasse
  → **Abgelehnt weil:** die 0.x-Phase des Arbiters gehört auf die
  agent-deploybare Seite; Updates über `~/shared` skalieren nicht
- Kernversprechen steht auf unverifizierter WDDM-Annahme (Per-Prozess-VRAM unter
  Windows mutmaßlich N/A) und einer nicht existenten Lease↔PID-Zuordnung —
  heilbar, aber dann bleibt vom Kernvorteil wenig übrig
- Fail-open + TTL-Verfall macht den Arbiter zum aktiven Schadensverursacher
  (entlädt mitten in fremden Render)

### Option C: Minimal-inkrementell (Konvention vor Konstruktion)

Advisory-Lease-Endpunkt, null neue Dienste, Ausbau nur bei gemessenem Trigger.

**Pros:**
- Geringste Anfangsinvestition; Pflicht-Zähler + messbare Ausbau-Trigger
  (diese Idee wird in Option A übernommen, §4.6)

**Cons:**
- Liefert die Arbeitsfläche (Treiber 5, der eigentliche Owner-Zweck) nicht oder
  spät → **Abgelehnt weil:** der Auftrag ist nicht „Karte koordinieren", sondern
  „Texte/Musik intensiv weiterentwickeln" — D1 ist der Zweck, D2 die Bedingung
- Der eingefrorene 3-Endpunkte-Vertrag ohne Heartbeat/Renew hätte exakt das
  falsche Interface fixiert (TTL-Ablauf mitten im Lauf unbehandelt)
- Koresidenz-Modus fehlt: jede Song-Session hinterließe per Exklusiv-Umschalter
  eine tote Box

---

## 3. Decision Outcome

**Gewählte Option: Option A — Hub-zentrierter Lease-Arbiter, Medien-Arbeitsfläche
in illustration-hub, `iil-gpufw` als schmaler Client (Extraktion terminiert).**

Die Entscheidung folgt aus den zwei härtesten Constraints: die Box ist nicht
agent-deploybar, und kein Handgriff darf Wertschöpfung verhindern. Beides zwingt
Zustand und Strategie auf den Hub und lässt die Box dumm. Option B legt die am
häufigsten iterierende Komponente auf die falsche Seite der Latenzgrenze; Option C
verfehlt den Owner-Zweck (Arbeitsfläche) und friert das falsche Interface ein.
Die Stärken der Verlierer werden übernommen: messbare Ausbau-Trigger und
Sofortsicherung aus C, Grund-Taxonomie, Außen-Abnahme und Eskalationspfad aus B.

---

## 4. Implementation Details

### 4.1 D1 — Medien-Arbeitsfläche: `apps/music` in illustration-hub

- **Schritt 0 (sofort, vor allem anderen):** vorhandene Songs vom ungesicherten
  Dev-Server per rsync in ein ADR-289-backupfähiges Volume auf prod
  (Namensmuster `media`) — jeder bis dahin erzeugte Song ist ungesichert.
- Datenmodell: `Song` (Titel, Prompt, Tags) → `SongVersion` (WAV-Original,
  MP3-Transkodat via ffmpeg im Hub-Container, Dauer, Seed, ACE-Step-Parameter,
  erzeugender Job). Feste URLs `/music/song/<id>/`, MP3 fürs Abspielen, WAV bleibt
  Original. Suche/Vergleich über Postgres.
- Song-Render ruft ACE-Step direkt über WG (`10.99.0.2:7865`) — der
  Dev-Server-Tunnel-Umweg entfällt.
- music-lab bleibt als Box-Setup-Repo (PS1-Skripte, `gpu-dienst.ps1` als
  **dokumentierter Owner-Override** für den Havariefall — wird nicht verdrängt);
  die CLI wird Client der Hub-API oder entfällt.
- Text-Arbeitsfläche (writing-hub) ist **nicht** Teil von D1 — writing-hub hat
  sein eigenes Datenmodell; es konsumiert nur die Batch-Lane (§4.3).
- Umbenennung illustration-hub → media-hub: bewusst vertagt, Tracking siehe §5.

### 4.2 D2 — Lease-Arbiter in `apps/jobs` (Vertragseigenschaften)

Tabelle `gpu_lease`: `verbraucher` (bild|song|text-batch), `klasse`
(interaktiv|batch), `status` (aktiv|verdraengt|abgelaufen|freigegeben), `zweck`,
`gueltig_bis` (TTL), `letzter_heartbeat`. Die folgenden Eigenschaften sind
**zugesicherte Vertragsbestandteile**, nicht Implementierungszufall — jede
adressiert einen konkreten Panel-Befund:

1. **Atomarer Grant:** partieller Unique-Index (`status='aktiv'`) + Transaktion —
   zwei gleichzeitige Anforderungen können nie beide gewinnen.
2. **Dreiwertiges Ergebnis:** `GRANTED` / `BELEGT{von, klasse, grund}` /
   `ARBITER_DOWN` — niemals auf einen Wert kollabiert. Bei `ARBITER_DOWN`
   degradiert der Client auf heutiges direktes kooperatives Entladen (fail-open),
   stampft aber **nie** einen laufenden fremden Job.
3. **Grund-Taxonomie in jeder Belegt-Antwort:**
   `fremd | eigener_batch_weicht(retry_after_s) | interaktiver_halter`.
   Interaktive Anforderung bei weichendem eigenem Batch → `202 reserviert
   {frei_in_max_s}` statt hartem 409.
4. **Heartbeat/Renew für ALLE Leases** (auch interaktive): kurze TTL +
   idempotentes Re-acquire — schließt beide TTL-Lücken (Ablauf mitten im Lauf;
   Geister-Lease bis volle TTL).
5. **Asymmetrische Degradation:** interaktiv fail-open (weiter wie heute), Batch
   fail-closed (jeder Heartbeat-/Netzfehler → sofort pausieren, weiter erst nach
   neuem Grant). Verhindert Doppelbelegungs-Races und lease-loses
   Batch-Weiterlaufen während Hub-Deploys.
6. **Vorrang:** interaktiv verdrängt Batch sofort (Lease → `verdraengt`,
   physisch via `ollama_entladen()`); Batch bekommt die Karte nur in Lücken
   (keine interaktive Lease + Karenz seit letzter interaktiver Aktivität,
   Startwert 10 min — wird gemessen, nicht geglaubt) und arbeitet chunk-weise.
7. **Interaktive Text-Einzel-Calls bleiben lease-frei**, aber nicht blind:
   billiger `GET /api/gpu/zustand`-Pre-Check vor jedem Ollama-Call; bei aktiver
   Bild/Song-Lease wird der Call zu Groq umgeleitet (T1a, llm-routing) statt das
   Modell mitten in den Render zu laden. Kaltstart nach einem Grant ist der
   akzeptierte Preis dafür, dass Textarbeit nie blockiert.
8. **Starvation sichtbar:** maximales Batch-Wartealter ist Pflicht-Metrik in
   `GET /api/gpu/zustand` — stilles Batch-Verhungern bekommt denselben Alarm wie
   stiller Degrade.

### 4.3 Bezahl-Gate (Erweiterung des Bestands, gilt in ALLEN Lanes)

- `karte_belegt()` + `darf_bei_belegter_karte_bezahlen()` werden von der
  Bild-Lane auf Song- und Text-Batch-Lane ausgedehnt; **aifw-Failover
  (default→fallback) muss das Gate respektieren** — sonst kehrt #179 in der
  Text-Lane zurück.
- Bei `eigener_batch_weicht` wird **nie** bezahlt (retry_after abwarten).
- **Evidenzquellen-Kennzeichnung:** jede Belegt-Einschätzung trägt ihre Quelle
  (`melder` | `heuristik`); auf Heuristik-Evidenz zahlt das Gate höchstens so
  großzügig wie heute. `nicht_erreichbar` (Box down) ist eine **eigene Klasse**
  — weder belegt noch kaputt — und umgeht das Gate nicht still.
- **Eskalationspfad gegen Blockade-Härte:** Fremd-Belegung > N Stunden + M lokale
  Fehlversuche → Bezahl-Fallback **mit Alarm und Kosten-Log**. Verhindert das
  Szenario „Gate blockiert 2 Wochen härter als der frühere Blindflug".

### 4.4 Grenzen (ehrlich dokumentiert)

- Der Arbiter koordiniert nur die Kooperativen. Der dritte Verbraucher
  (z.B. LoRA-Training) bleibt unsichtbar; die Verteidigung dagegen ist die
  Fehlerklassifikation + das Gate, nicht die Lease. „Keine Auskunft ist nicht
  Entwarnung" bleibt Doktrin.
- Box-Ausfall bei Owner-Abwesenheit ist strukturell unheilbar (kein Fernzugriff)
  und trifft jede denkbare Architektur — akzeptiertes Restrisiko, §7.
- Der optionale read-only `gpu-melder` (nvidia-smi-Endpunkt auf der Box) ist
  **der eine** erlaubte neue Box-Dienst — er wird ehrlich mit vollem Preisschild
  deklariert (Port, Firewall, Autostart, Update-Weg) oder gestrichen; §5 Phase 4.

### 4.5 D3 — `iil-gpufw`: schmaler Client, terminierte Extraktion

- Inhalt: Lease-Protokoll-Client (`lease_anfordern` → dreiwertig,
  `lease_heartbeat`, `lease_freigeben`), Fehlerklassifikation
  (`BELEGT_MARKER`/`karte_belegt`), Bezahl-Gate. Kein Django-Import (der eine
  `_setting`-Helfer wird durch injizierte Config ersetzt); reines HTTP.
- **Die Einfrier-Grenze ist der HTTP-Vertrag, nicht die Python-API** — mit
  Versionsfeld ab v0; Server tolerant-liberal, Brüche werden client-seitig
  abgefedert (nur Agent-Deploys nötig). Einfrieren als 1.0 erst nach drei
  realen Konsumenten. Die Strategie (Vorrang, Karenz, Räum-Reihenfolge) bleibt
  serverseitig und wird nicht ins Paket eingefroren.
- **Extraktionszeitpunkt terminiert:** beim zweiten CODE-Konsumenten = wenn
  writing-hub/aifw die Batch-Lane bekommt (§5 Phase 6). Bis dahin leben Arbiter
  und Client-Funktionen in `illustration-hub/apps/jobs`; `apps/music` ruft
  in-process auf und ist bewusst kein Extraktionsanlass. Release dann über den
  etablierten `/release`-Weg (Präzedenz: ADR-084 / iil-illustrationfw).

### 4.6 Messen statt glauben (aus Option C übernommen, Pflichtteil der ersten PR)

Pflicht-Zähler: fal-Calls trotz belegt · Failover-Calls je Grund (inkl. Groq) ·
Batch-Backlog-Alter · Lease-Konflikte je Taxonomie-Grund · Kaltstartdauer ·
Batch-Fenster-Ausbeute. **Auswertungs-Ritual:** monatlicher Eintrag ins
`/briefing` mit hartem Schwellen-Vergleich — jeder Ausbau (Arbiter-Härtung,
music-hub-Split, media-hub-Umbenennung, gpu-melder) bekommt ein Go-/Kill-Kriterium
aus diesen Zählern statt Bauchgefühl.

### 4.7 Box-Handgriffe: Außen-Abnahme statt Selbsttest

Jeder Box-seitige Schritt (Firewall 7865, Autostart der drei Dienste) gilt erst
als „installiert", wenn er **von außen** verifiziert ist: curl vom Prod-Host über
WG + echter Reboot-Test mit Log-Rückgabe über `~/shared` — nie per
localhost-Selbsttest (Generalisierung der Lehre aus music-lab 375c171 /
music-lab#2). **Zwei billige Vorab-Checks vor jeder darauf bauenden Automatik:**
(1) ACE-Step-VRAM-Verhalten: ein Song + `nvidia-smi`-Ausgabe via `~/shared` —
hat ACE-Step keinen Entlade-Pfad, ändert das die Song-Räum-Reihenfolge;
(2) WDDM-Prüfzeile `nvidia-smi --query-compute-apps=...` einmal einsammeln —
verifiziert oder beerdigt die Prozess-Evidenz-Klasse (und damit den gpu-melder),
bevor sie geplant wird.

---

## 5. Migration Tracking

| Repo / Service | Phase | Inhalt | Status | Datum | Notizen |
|----------------|-------|--------|--------|-------|---------|
| `illustration-hub` | 0 | Sofortsicherung: Songs → prod-media-Volume (rsync); Vorab-Checks §4.7 (ACE-Step-VRAM, WDDM) | ⬜ Ausstehend | – | vor allem anderen |
| `illustration-hub` | 1 | Lease-Arbiter in `apps/jobs` (Vertrag §4.2) + Zähler §4.6 | ⬜ Ausstehend | – | Bild-Lane als erster Konsument |
| `illustration-hub` | 2 | `apps/music`: Datenmodell, MP3, feste URLs, Player | ⬜ Ausstehend | – | löst music-lab#3 Krit. 1/2/6 |
| `music-lab` | 3 | CLI → Hub-API; `gpu-dienst.ps1` als Owner-Override dokumentiert | ⬜ Ausstehend | – | Repo bleibt Box-Setup |
| Box (Owner) | 4 | Autostart 3 Dienste + Firewall 7865, Abnahme per §4.7; gpu-melder go/kill nach WDDM-Check | ⬜ Ausstehend | – | einmalig; Außen-Abnahme Pflicht |
| `writing-hub` / `aifw` | 5 | Batch-Lane: aifw-Failover ans Gate, Groq-Umleitung bei aktiver Lease | ⬜ Ausstehend | – | Trigger für Phase 6 |
| `aifw` / neu `iil-gpufw` | 6 | Extraktion Client-Paket (zweiter Code-Konsument erreicht) | ⬜ Ausstehend | – | Release via /release, ADR-084-Muster |
| `platform` | 7 | Umbenennungs-Entscheid illustration-hub → media-hub (Go/Kill aus §4.6-Zählern) | ⬜ Ausstehend | – | Tracking-Issue im selben Zug wie Phase 2 |

---

## 6. Consequences

### 6.1 Good

- Eine Bewirtschaftungs-Strategie statt zwei widersprüchlicher; Vorrang macht
  die lokale Auslagerung wirtschaftlich (Batch füllt Lücken statt zu konkurrieren)
- Arbeitsfläche mit Versionen/Varianten/Suche auf gesicherter, deployter
  Infrastruktur — music-lab#3 Kriterien 1/2/6 werden von der Plattform erfüllt
  statt einzeln nachgebaut
- „belegt ≠ kaputt" + Bezahl-Gate gelten in allen drei Lanes; stille
  Bezahl-Rückfälle sind in jeder Lane verschlossen
- Null neue Box-Dienste im Regelbetrieb; die Box-Wartungslast des Owners wächst
  nicht mit der Iterationsgeschwindigkeit des Arbiters

### 6.2 Bad

- Blast-Radius: illustration-hub wird Single Point of Failure für Bild UND Song
  (Text degradiert auf Groq und bleibt arbeitsfähig)
- Interaktive Text-Calls zahlen nach jedem Bild/Song-Grant einen
  Modell-Kaltstart — akzeptierter Preis für „Text blockiert nie"
- Eine Lease ist ein Absichts-Register, keine Karten-Wahrheit; gegen den dritten
  Verbraucher hilft nur die Fehlerklassifikation
- Repo-Name illustration-hub ist bis Phase 7 unehrlich

### 6.3 Nicht in Scope

- Text-Arbeitsfläche (writing-hub-Datenmodell) — eigenes Repo, eigene Hoheit
- Upload/Publish von Songs zu Dritten; Prod-Deploy der Musik nach iil.pet
  (Out-of-Scope-Grenzen aus music-lab#1 gelten fort)
- Multi-GPU / zweite Box; Nutzerverwaltung/Mehrbenutzerbetrieb
- Ersatz des `~/shared`-Musters durch Fernzugriff auf die Box

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Box-Ausfall bei Owner-Abwesenheit (strukturell: kein Fernzugriff) | Mittel | Hoch | Akzeptiert; Eskalationspfad §4.3 verhindert Doppelschaden „lokal tot + Gate blockiert bezahlt"; trifft jede Architektur gleich |
| ACE-Step ohne Entlade-Pfad (2 Entlade-Calls für 3 residente Dienste) | Mittel | Mittel | Vorab-Check §4.7(1) VOR jeder Song-Automatik; ggf. Räum-Reihenfolge ändern oder ACE-Step nur on-demand starten (Owner-Override) |
| aifw-Failover umgeht Gate (=#179 in Text-Lane) | Hoch ohne Fix | Mittel | Vertragspflicht §4.3; Zähler „Failover je Grund" macht Verstöße sichtbar |
| Zähler werden erhoben, aber nie gelesen („Melder ohne Leser") | Mittel | Mittel | Auswertungs-Ritual §4.6 ist Pflichtteil der ersten PR, nicht Folgearbeit |
| Autostart-Fehlschlag detoniert erst beim nächsten Reboot | Mittel | Mittel | Außen-Abnahme mit echtem Reboot-Test §4.7 |
| Interface friert zu früh ein (vor Konsument 3) | Niedrig | Mittel | Versionsfeld ab v0; 1.0 erst nach drei realen Konsumenten §4.5 |

---

## 8. Confirmation

1. **Vertrags-Tests im Arbiter (CI, illustration-hub):** Testfälle für die acht
   Vertragseigenschaften aus §4.2 — insbesondere Doppel-Grant-Race (zwei
   parallele Acquires, genau einer gewinnt), TTL-Ablauf + Re-acquire, Batch
   fail-closed bei Heartbeat-Fehler. Merge-Gate wie üblich.
2. **Gate-Abdeckungs-Grep (CI):** kein Aufruf eines Bezahl-Providers (fal,
   litellm-Failover) außerhalb eines Pfads, der `darf_bei_belegter_karte_bezahlen()`
   passiert — nachweisbar per Struktur-Test in illustration-hub bzw. aifw.
3. **Monatliches Zähler-Ritual (§4.6):** Briefing-Eintrag existiert und enthält
   die Schwellen-Vergleiche; ausbleibende Einträge sind selbst ein Befund.
4. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft —
   Staleness-Schwelle: 6 Monate.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **Lease** | Zeitlich befristete, verlängerbare Nutzungs-Zusage für die GPU — ein Absichts-Register, keine physische Sperre |
| **Arbiter** | Die eine Stelle, die Leases erteilt, verdrängt und einsehbar macht (hier: Modul + HTTP-API in illustration-hub) |
| **VRAM** | Grafikspeicher der GPU (hier 24 GB) — die knappe, umkämpfte Ressource |
| **TTL** | Time to live — Ablauffrist einer Lease; verwaiste Leases sterben dadurch ohne Aufräum-Skript |
| **WDDM** | Windows Display Driver Model — Windows-Treibermodus, unter dem `nvidia-smi` Prozess-Details oft nicht liefert (unverifizierte Annahme → Vorab-Check §4.7) |
| **WG / WireGuard** | VPN, über das Prod-Host und Box sich erreichen (`10.99.0.2`) |
| **fal** | Bezahlter Cloud-Bildanbieter — der Rückfallpfad, dessen stille Nutzung #179 auslöste |
| **aifw** | Haus-Framework für LLM-Routing (litellm-basiert); routet writing-hub-Calls auf Provider |
| **Batch / interaktiv** | Aufschiebbare Massenläufe vs. sofort erwartete Einzelaufträge — die zwei Vorrang-Klassen dieses ADR |
| **Kaltstart** | Neuladen eines entladenen Sprachmodells in den VRAM — Kostenfaktor der Verdrängung |
| **ADR** | Architecture Decision Record — dokumentierte Architektur-Entscheidung |

---

## 9. More Information

- illustration-hub#187 — „Eine 4090, zwei Verbraucher" (geschlossen; Vorarbeit
  kooperatives Muster + Melder-Idee)
- illustration-hub#179 — stiller fal-Bezahl-Rückfall (2× reproduziert; Ursprung
  der „belegt ≠ kaputt"-Doktrin)
- music-lab#1 — Erstauftrag Song-Generierung (Kriterien 1–4 belegt)
- music-lab#2 — PS1-Fehlerklassen-Gate (Grund für „null neue Box-Dienste")
- music-lab#3 — Song-Bibliothek + Vorschläge (Kriterien 1/2/6 werden durch
  dieses ADR erfüllt)
- ADR-084 — Präzedenz Paket-Extraktion (iil-illustrationfw)
- ADR-289 — Offsite-Backup prod→netcup (Backup-Verdrahtung der Arbeitsfläche)
- ADR-292 — Two-Lane-Deployment; dokumentierte illustration-hub-Ausnahme
  (WG-Route zur Box)
- Design-Panel-Dossier 2026-08-14 (3 Entwürfe × 2 Prüfungen × 3 Richter) —
  Session-Artefakt, Kernergebnisse in §2/§4 eingearbeitet

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-08-14 | Achim Dehnert | Initial: Status Proposed — Synthese aus adversarialem Design-Panel |
