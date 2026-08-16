---
status: accepted
decision_date: 2026-08-14
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-292, ADR-289, ADR-084, ADR-059]
implementation_status: partial
last_reviewed: 2026-08-14
staleness_months: 6
tags: [gpu, lease-arbiter, illustration-hub, music-lab, writing-hub, aifw, medien-arbeitsflaeche, iil-gpufw]
ai_sparring_by:
  - tool: other
    date: 2026-08-14
    role: adversarial-review
    summary: "Extern R1 (Anbieter nicht benannt): überarbeiten→annehmen; 7 RECs, alle [valid] eingearbeitet — Tag-Tabelle §Review-Rückfluss"
  - tool: other
    date: 2026-08-14
    role: adversarial-review
    summary: "Extern R2 (Anbieter nicht benannt): überarbeiten (Zustandsmaschine); 14 RECs, alle [valid] eingearbeitet — Tag-Tabelle §Review-Rückfluss"
---

# ADR-296: GPU-Box über Hub-seitigen Lease-Arbiter bewirtschaften — Medien-Arbeitsfläche und Client-Paket folgen dem Hub

> **Nummern-Hinweis:** 296 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).
>
> **Entstehung:** Synthese aus einem adversarialen Design-Panel (2026-08-14):
> 3 unabhängige Gesamtentwürfe (hub-zentriert, box-zentriert, minimal-inkrementell)
> × je 2 adversariale Prüfungen (Betriebsrealität, Nebenläufigkeit) × 3 Richter mit
> unterschiedlicher Treiber-Gewichtung; anschließend **zwei externe
> Cross-Provider-Zweitmeinungen** (21 Empfehlungen, alle valid, Rev 2 —
> Tag-Tabelle in §Review-Rückfluss). Kein Entwurf trug einen unheilbaren Befund.

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Accepted                                                             |
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
| `platform`         | Referenz   | `docs/adr/`, `infra/ports.yaml` (writing-hub-Pin, Phase 6) |
| `illustration-hub` | Primär     | `apps/jobs/` (Arbiter + Lease-API), NEU `apps/music/`   |
| `music-lab`        | Sekundär   | `box-setup/` (bleibt), CLI wird Client der Hub-API      |
| `writing-hub`      | Sekundär   | aifw-Routing Batch-Lane (Phase 6; **braucht prod-Pin**) |
| `aifw`             | Sekundär   | optionale Abhängigkeit `iil-gpufw` für Batch-Lane       |

---

## Decision Drivers

- **Kosten**: Lokale Auslagerung soll bezahlte LLM-/Bild-Calls ersetzen; der stille
  Bezahl-Rückfall bei belegter Karte (illustration-hub#179, 2× reproduziert) darf in
  keiner neuen Lane zurückkehren — auch nicht als „harmlose" Groq-Umleitung ohne
  Sichtbarkeit und Budget.
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
| writing-hub → Box | noch kein Konsument; aifw v0.12 hat Provider `ollama` (base_url localhost), Route zur Box fehlt. writing-hub läuft heute auf Host `prod` (ports.yaml-Default, kein `prod_host`-Eintrag) — dem einzigen Host mit WG-Route |

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
Repariert um die Panel- und Extern-Review-Befunde (Zustandsmaschine, atomarer
Grant, Identitäten, Grund-Taxonomie, Heartbeats, asymmetrische Degradation,
Bezahlmatrix, Ereignisjournal — Details §4).

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
  (Mitigation + benannter Evolutionspfad: §6.2, §7)
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

**Phasenschnitt (aus dem externen Review, R1-REC-2):** Die gewählte Umsetzung
beginnt faktisch als die im Panel nie einzeln bewertete Hybride „Arbeitsfläche auf
dem Hub + interaktiver Minimal-Arbiter": Phase 1 baut **nur den interaktiven
Vertragsteil**; die Batch-Klasse ist spezifiziert, wird aber erst gebaut, wenn ihr
realer Konsument ansteht und der Kosten-Nachweis (§4.6) Go sagt.

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
  Dev-Server-Tunnel-Umweg entfällt. **Vorbedingung:** die Box-Abnahme aus §4.7
  (Firewall 7865 von prod aus verifiziert) ist Phase 2 und liegt VOR der
  Musik-Aktivierung (R2-REC-8).
- music-lab bleibt als Box-Setup-Repo; `gpu-dienst.ps1` bleibt als
  **Break-glass-Werkzeug** erhalten — mit Protokoll (§4.4), nicht als stiller
  Parallel-Steuerpfad.
- **Netzpfad der Text-Lane (R1-REC-1):** writing-hub läuft heute auf Host `prod`
  (ports.yaml-Default) — dem einzigen Host mit WG-Route zur Box. Das ist
  Zufall, keine Zusicherung: die ADR-292-Long-Tail-Migration verschiebt Repos
  laufend nach prod-b. **Vor Phase 6 wird writing-hub explizit gepinnt**
  (`prod_host: prod` mit Verweis auf ADR-296) — eine zweite, deklarativ billige
  ADR-292-Ausnahme derselben Begründungsklasse wie illustration-hub (WG-Route
  nötig). Ein Hub-Proxy wird verworfen: er machte illustration-hub zum
  Durchlauferhitzer fremder Text-Calls (Blast-Radius ↑, §6.2).
- Text-Arbeitsfläche (writing-hub-Datenmodell) ist **nicht** Teil von D1.
- Umbenennung illustration-hub → media-hub: bewusst vertagt, Tracking siehe §5.

### 4.2 D2 — Lease-Arbiter in `apps/jobs` (Vertragseigenschaften)

Tabelle `gpu_lease` — Identitäten und Zustandsmaschine sind Vertragsbestandteil
(R2-REC-2/-4):

- **Identität:** `lease_id`, opakes `lease_token` (nicht erratbar), monoton
  steigende `generation` je Ressource, `holder_instance`, `job_id`,
  `idempotency_key`, `issued_at` (nur Serverzeit). Heartbeat/Release wirken nur
  mit passender `lease_id` + `token` + `generation`.
- **Verbraucher:** erweiterbarer Schlüssel (`bild`, `song`, `text-batch`, …) —
  bewusst KEIN geschlossenes Enum (R2-REC-11; Treiber Evolvierbarkeit).
  `klasse` ∈ {interaktiv, batch}.
- **Zustände:** `reserviert` → `verdraengung_laeuft` → `aktiv` →
  {`freigegeben` | `abgelaufen` | `verdraengt`}; dazu Client-seitig `ungewiss`
  (Arbiter nicht erreichbar). `reserviert` ist **persistent** und blockiert
  konkurrierende Grants (R2-REC-5).
- **Ereignisjournal:** jede Zustandsänderung append-only in `gpu_lease_event`
  (wer, wann, warum, Auslöser) — aggregierte Zähler ersetzen keine
  Ursachenanalyse (R2-REC-14).

Die folgenden Eigenschaften sind **zugesicherte Vertragsbestandteile**, nicht
Implementierungszufall:

1. **Normativer Grant-Algorithmus (R2-REC-1):** ausschließlich Serverzeit;
   Expire abgelaufener aktiver Leases und der neue Grant laufen in **derselben
   serialisierten Transaktion**; der partielle Unique-Index (`status='aktiv'`)
   ist letzte Integritätssicherung, nicht der Mechanismus.
2. **Dreiwertiges Ergebnis:** `GRANTED` / `BELEGT{von, klasse, grund}` /
   `ARBITER_DOWN` — niemals auf einen Wert kollabiert. `ARBITER_DOWN`-Zusage
   präzise (R1-REC-5): der degradierte Client **stampft keine eigenen
   koordinierten Jobs** (Batch pausiert fail-closed); über *fremde* Jobs kann
   und wird nichts versprochen. Fail-open-Pfade **je Lane** (R2-REC-6):
   Bild = heutiges direktes kooperatives Entladen; Song = Abbruch mit Meldung
   (KEIN Rückgriff auf den Exklusiv-Umschalter — der ist Break-glass, §4.4);
   Text = direkt zur Groq-Route (sichtbar, §4.3).
3. **Grund-Taxonomie in jeder Belegt-Antwort:**
   `fremd | eigener_batch_weicht(retry_after_s) | interaktiver_halter`.
   Interaktive Anforderung bei weichendem eigenem Batch → `202 reserviert
   {frei_in_max_s}`; `GRANTED` erst, wenn der bisherige Halter die Pause
   bestätigt hat ODER der definierte Timeout-Pfad abgeschlossen ist (R2-REC-5) —
   dazwischen `verdraengung_laeuft`.
4. **Heartbeat/Renew für ALLE Leases** (auch interaktive): kurze TTL +
   idempotentes Re-acquire (via `idempotency_key`). **Deploy-Toleranz
   (R1-REC-6):** Batch pausiert erst nach N verpassten Heartbeats
   (Startwert N=3), damit kurze Hub-Deploy-Fenster nicht jeden Batch abbrechen;
   deploy-bedingte Abbrüche sind eigener Zähler (§4.6).
5. **Asymmetrische Degradation:** interaktiv fail-open (weiter wie heute), Batch
   fail-closed (nach N verpassten Heartbeats → pausieren, weiter erst nach
   neuem Grant).
6. **Vorrang:** interaktiv verdrängt Batch sofort (Zustand `verdraengung_laeuft`,
   physisch via `ollama_entladen()`); Batch bekommt die Karte nur in Lücken
   (keine interaktive Lease + Karenz seit letzter interaktiver Aktivität,
   Startwert 10 min — wird gemessen) und arbeitet chunk-weise.
   **Batch-Warte-SLO (R2-REC-11):** überschreitet das Batch-Wartealter die
   SLO-Schwelle (Startwert 24 h), reagiert das System definiert — Owner-Hinweis
   mit Wahl: manuelles Batch-Fenster ODER expliziter Verwurf; niemals stilles
   Dauerverhungern.
7. **Interaktive Text-Einzel-Calls bleiben lease-frei**, aber nicht blind:
   billiger `GET /api/gpu/zustand`-Pre-Check vor jedem Ollama-Call; bei aktiver
   Bild/Song-Lease Umleitung zur Groq-Route. **Der Pre-Check ist ein
   dokumentiertes TOCTOU-Fenster (R2-REC-4, bewusst akzeptiert):** eine
   Bild/Song-Lease kann zwischen Check und Modell-Laden entstehen; die Kollision
   endet dann in einem OOM, das als `belegt` (nicht `kaputt`) klassifiziert wird
   und gate-geschützt zur Groq-Route führt — begrenzter Schaden (ein Kaltstart),
   kein stilles Geld. Eine Pflicht-Lease je Text-Call würde die Text-Latenz
   für den Normalfall verteuern, um einen bereits gutartig endenden Randfall
   zu verhindern — verworfen, Begründung hier festgehalten.
8. **Starvation sichtbar:** maximales Batch-Wartealter ist Pflicht-Metrik in
   `GET /api/gpu/zustand` — gekoppelt an die SLO-Reaktion aus (6).
9. **Fehlermatrix (R2-REC-3)** — die Vertrags-Haltung je Störfall, statt
   unvereinbarer Einzelversprechen:

   | Störfall | Alte Operation | Neuer Grant | Auflösung |
   |---|---|---|---|
   | Heartbeat-Verlust interaktiv | darf weiterlaufen (fail-open) | nach TTL möglich | Doppelbelegung MÖGLICH und akzeptiert: die Karte arbitriert physisch; Verlierer scheitert mit `belegt`-Klassifikation, Gate zahlt nicht; Journal macht den Hergang rekonstruierbar |
   | Heartbeat-Verlust Batch | pausiert nach N misses (fail-closed) | ja | keine Doppelbelegung durch eigene Batches |
   | Hub-Restart/Deploy | interaktiv läuft weiter; Batch pausiert nach N misses | nach Rückkehr per Postgres-Stand | abgelaufene Leases sind tot; Journal lückenlos |
   | Netzpartition Client↔Hub | Client-Zustand `ungewiss`; interaktiv weiter, Batch pausiert | ja | wie Zeile 1 |

   Die Lease behauptet nie Karten-Wahrheit (§4.4) — deshalb ist „alte Operation
   darf weiterlaufen UND neuer Grant möglich" kein Widerspruch, sondern die
   dokumentierte Konsequenz, mit der Karte selbst als letzter Schiedsrichterin.

### 4.3 Bezahl-Gate (Erweiterung des Bestands, gilt in ALLEN Lanes)

- `karte_belegt()` + `darf_bei_belegter_karte_bezahlen()` werden von der
  Bild-Lane auf Song- und Text-Batch-Lane ausgedehnt; **aifw-Failover
  (default→fallback) muss das Gate respektieren** — sonst kehrt #179 in der
  Text-Lane zurück.
- **Zentraler deny-by-default Provider-Wrapper (R2-REC-10):** jeder bezahlte
  Call läuft durch genau eine Wrapper-Funktion, die das Gate erzwingt; ein
  bezahlter Aufruf trotz belegter/unklarer Karte löst einen **Sofort-Alarm**
  aus (Lane, Grund, Evidenzquelle, geschätzte Kosten) — nicht erst das
  Monats-Ritual (R2-REC-10 gegen AD-12).
- **Normative Bezahlmatrix (R2-REC-7)** — Startwerte, per §4.6 nachjustiert:

  | Belegt-Grund | Evidenz | Aktion |
  |---|---|---|
  | `eigener_batch_weicht` | arbiter | **nie zahlen**; `retry_after_s` abwarten |
  | `interaktiver_halter` | arbiter | warten oder Nutzerhinweis; zahlen nur auf expliziten Nutzer-Klick |
  | `fremd` | heuristik | warten + Hinweis; Eskalation: > **N=4 h** UND ≥ **M=3** lokale Fehlversuche → zahlen MIT Sofort-Alarm + Kosten-Log |
  | `nicht_erreichbar` (Box down) | – | eigene Klasse, weder belegt noch kaputt; zahlen erlaubt MIT Sofort-Alarm; niemals still |
  | Groq-Umleitung interaktiver Text (§4.2 Nr. 7) | arbiter | erlaubt, aber **sichtbar**: eigener Zähler + Monatsbudget-Schwelle (Startwert 5 $/Monat, Alarm bei Überschreitung) |

- **Evidenzquellen-Kennzeichnung:** jede Belegt-Einschätzung trägt ihre Quelle
  (`arbiter` | `melder` | `heuristik`); auf Heuristik-Evidenz zahlt das Gate
  höchstens so großzügig wie heute.

### 4.4 Grenzen und Break-glass (ehrlich dokumentiert)

- Der Arbiter koordiniert nur die Kooperativen. Der dritte Verbraucher
  (z.B. LoRA-Training) bleibt unsichtbar; die Verteidigung dagegen ist die
  Fehlerklassifikation + das Gate, nicht die Lease. „Keine Auskunft ist nicht
  Entwarnung" bleibt Doktrin.
- **Break-glass-Protokoll für `gpu-dienst.ps1` (R2-REC-9):** Der Owner-Override
  bleibt für den Havariefall — mit Vertrag statt als stiller Parallel-Pfad:
  (1) VOR der Nutzung Wartungsmodus im Arbiter setzen (ein Flag, sperrt neue
  Grants); (2) bestehende Leases werden sichtbar invalidiert (Zustand
  `verdraengt`, Journal-Eintrag `grund=break_glass`); (3) NACH dem Eingriff
  Außen-Abnahme (§4.7) und explizite Rückkehr in den Normalbetrieb
  (Flag zurück). Ist der Hub selbst down, gilt: Override nutzen, Abnahme +
  Journal-Nachtrag bei Rückkehr — der Vertrag fordert die Nachvollziehbarkeit,
  nicht die Unmöglichkeit des Eingriffs.
- Box-Ausfall bei Owner-Abwesenheit ist strukturell unheilbar (kein Fernzugriff)
  und trifft jede denkbare Architektur — akzeptiertes Restrisiko, §7.
- Der optionale read-only `gpu-melder` (nvidia-smi-Endpunkt auf der Box) ist
  **der eine** erlaubte neue Box-Dienst — er wird ehrlich mit vollem Preisschild
  deklariert (Port, Firewall, Autostart, Update-Weg) oder gestrichen;
  Go/Kill nach dem WDDM-Check (§4.7).

### 4.5 D3 — `iil-gpufw`: schmaler Client, terminierte Extraktion

- Inhalt: Lease-Protokoll-Client (`lease_anfordern` → dreiwertig,
  `lease_heartbeat`, `lease_freigeben`), Fehlerklassifikation
  (`BELEGT_MARKER`/`karte_belegt`), Bezahl-Gate-Wrapper. Kein Django-Import
  (der eine `_setting`-Helfer wird durch injizierte Config ersetzt); reines HTTP.
- **Die Einfrier-Grenze ist der HTTP-Vertrag, nicht die Python-API** — als
  **versioniertes Schema-Dokument** in `illustration-hub/docs/`
  (R2-REC-13): Endpunkte, Statuscodes, Fehlerobjekte, Timeout-Semantik,
  Idempotenzregeln, unterstütztes Versionsfenster (Server trägt
  `min_client_version`), leichtgewichtiger Deprecation-Prozess (angekündigt im
  Schema-Doc, ein Release Vorlauf). Versionsfeld ab v0; Server tolerant-liberal,
  Brüche werden client-seitig abgefedert. Einfrieren als 1.0 erst nach drei
  realen Konsumenten. Die Strategie (Vorrang, Karenz, Räum-Reihenfolge) bleibt
  serverseitig.
- **Extraktions-Reihenfolge (R2-REC-8):** Die Extraktion erfolgt **vor** der
  Aktivierung des zweiten Code-Konsumenten — Phase 5 extrahiert `iil-gpufw`
  (Quelle: die in illustration-hub gereiften Client-Funktionen), Phase 6 lässt
  writing-hub/aifw das fertige Paket konsumieren. Damit entsteht weder eine
  temporär unmögliche Abhängigkeit noch duplizierte Gate-Logik. Auslöser der
  Extraktion bleibt der **committete** zweite Konsument (Kosten-Go aus §4.6),
  nicht sein Deployment. Release über den etablierten `/release`-Weg
  (Präzedenz: ADR-084 / iil-illustrationfw).

### 4.6 Messen statt glauben (aus Option C übernommen, Pflichtteil der ersten PR)

Pflicht-Zähler: fal-Calls trotz belegt · Failover-Calls je Grund (inkl. Groq) ·
Groq-Umleitungs-Calls interaktiver Text (mit Budget-Schwelle, §4.3) ·
deploy-bedingte Batch-Abbrüche (R1-REC-6) · Batch-Backlog-Alter vs. SLO ·
Lease-Konflikte je Taxonomie-Grund · Kaltstartdauer · Batch-Fenster-Ausbeute.

**Auswertungs-Ritual:** monatlicher Eintrag ins `/briefing` mit hartem
Schwellen-Vergleich. Das Ritual trägt die *Trend*-Entscheidungen; die
*akuten* Fehlerklassen (bezahlt trotz belegt/unklar, Budget-Überschreitung)
haben Sofort-Alarme (§4.3) und hängen NICHT am Ritual (gegen R2-AD-12 /
R1-M28-2).

**Kosten-Go/Kill vor der Batch-Lane (R1-REC-3):** Vor Phase 5/6 wird gerechnet:
erwartetes Text-Batch-Tokenvolumen/Monat × T1a-Preis (heute 0,59/0,79 $ pro 1M)
vs. Arbitrierungs- und Kaltstart-Kosten. Liegt die Groq-Alternative unter
**10 $/Monat**, ist die lokale Batch-Lane ökonomisch nicht begründbar und
Phase 5/6 werden vertagt (Kill) — das Owner-Ziel „Unabhängigkeit" kann das
überstimmen, aber dann steht die Begründung im Journal, nicht im Bauchgefühl.

Jeder Ausbau (Batch-Lane, music-hub-Split, media-hub-Umbenennung, gpu-melder,
Control-Plane-Split §6.2) bekommt ein Go-/Kill-Kriterium aus diesen Zählern.

### 4.7 Box-Handgriffe: Außen-Abnahme statt Selbsttest

Jeder Box-seitige Schritt (Firewall 7865, Autostart) gilt erst als „installiert",
wenn er **von außen** verifiziert ist: curl vom Prod-Host über WG + echter
Reboot-Test mit Log-Rückgabe über `~/shared` — nie per localhost-Selbsttest
(Generalisierung der Lehre aus music-lab 375c171 / music-lab#2).

**Drei billige Vorab-Checks vor jeder darauf bauenden Automatik:**

1. **ACE-Step-VRAM-Verhalten — hartes Go/No-Go-Gate der Song-Lane (R2-REC-6):**
   ein Song + `nvidia-smi`-Ausgabe via `~/shared`. **Negativ-Fall ausformuliert
   (R1-REC-7):** hat ACE-Step keinen Entlade-Pfad, dann (a) ACE-Step kommt NICHT
   in den Phase-2-Autostart (der umfasst dann nur ComfyUI + Ollama), (b) die
   Song-Lane startet ACE-Step on-demand je Song-Session über einen dokumentierten
   Owner-Handgriff (Verknüpfung auf dem Desktop; bewusst ein manueller Schritt
   je Session statt einer dauerhaft belegten Karte), (c) die Räum-Reihenfolge
   der Song-Lane beginnt mit „ACE-Step-Prozess beenden" als Teil des
   Owner-Handgriffs. Die Song-Lane wird erst aktiviert, wenn einer der beiden
   Pfade (entladbar ODER on-demand-Protokoll abgenommen) steht.
2. **WDDM-Prüfzeile** `nvidia-smi --query-compute-apps=...` einmal einsammeln —
   verifiziert oder beerdigt die Prozess-Evidenz-Klasse (und damit den
   gpu-melder), bevor sie geplant wird.
3. **Koresidenz-Check Klein-LLM (R1-REC-4):** VRAM-Fußabdruck eines residenten
   quantisierten 7–8B-Modells parallel zu einem realen Bild-Render messen.
   Reicht das Budget, koexistiert interaktiver Text dauerhaft neben Bild —
   Vorrangregeln §4.2(6/7) vereinfachen sich erheblich (kein Kaltstart, keine
   Groq-Umleitung im Normalfall). Ergebnis fließt VOR dem Bau der
   Verdrängungs-Mechanik ein.

---

## 5. Migration Tracking

Reihenfolge nach R1-REC-2 + R2-REC-8 umgeschnitten: interaktiv vor Batch,
Box-Abnahme vor Musik-Aktivierung, Extraktion vor zweitem Konsumenten.

| Repo / Service | Phase | Inhalt | Status | Datum | Notizen |
|----------------|-------|--------|--------|-------|---------|
| `illustration-hub` | 0 | Sofortsicherung Songs → prod-media-Volume; 3 Vorab-Checks §4.7 | 🟡 Teilweise | 2026-08-14/15 | 0a **erledigt**: Volume `music_media`, Song md5-identisch, Restore-Stichprobe aus restic bestanden (§8 Nr. 3, [music-lab#3](https://github.com/achimdehnert/music-lab/issues/3#issuecomment-5301622757)). 0b **offen**: `vorab-checks.ps1` liegt in `~/shared`, auf der Box noch nicht gelaufen. Ergänzt 2026-08-15: `make sichern` (music-lab) bringt Songs, MP3s **und** Song-Texte wiederholbar ins Volume, mit md5-Gegenprobe je Datei — vorher lagen dort nur WAV+JSON, die MP3 fehlte. Damit music-lab#3 Krit. 6 vollständig |
| `illustration-hub` | 1 | Arbiter **interaktiver Vertragsteil** (§4.2 ohne Batch-Bau) + Zähler + Sofort-Alarme + Journal | ✅ Erledigt | 2026-08-15 | Arbiter [#240](https://github.com/achimdehnert/illustration-hub/pull/240) **gemergt**, live auf Prod seit Tag `v1.0.0` (Code + Migration 0005 im laufenden Container verifiziert). Bild-Lane als Konsument [#242](https://github.com/achimdehnert/illustration-hub/pull/242) **gemergt** (CI grün nach Re-run; der erste Lauf scheiterte an einer Runner-Portkollision 5432, nicht am Code), live mit Tag `v1.1.0`. Batch bleibt spezifiziert, ungebaut |
| Box (Owner) | 2 | Firewall 7865 + Autostart (ACE-Step nur bei positivem Check 1), Außen-Abnahme §4.7 | ⬜ Ausstehend | – | VOR Musik-Aktivierung (R2-REC-8); **wartet auf 0b** — Check 1 ist das Go/No-Go |
| `illustration-hub` | 3 | `apps/music`: Datenmodell, MP3, feste URLs, Player | 🟡 Teilweise | 2026-08-15 | **Reihenfolge bewusst abgewichen** (Owner-Entscheid 2026-08-15, s. Notiz unter der Tabelle): box-freier Teil [#243](https://github.com/achimdehnert/illustration-hub/pull/243) **gemergt und live** mit Tag `v1.1.0` — Datenmodell, `songs_einlesen`, feste URLs `/musik/song/<id>/`, Player, Volume read-only gemountet. Bestandsprobe auf Prod bestanden: Song vom 14.08. eingelesen, Titel/Datum/Dauer/Seed/Prompt vollständig, MP3 (4,3 MB) registriert. Damit music-lab#3 Krit. 2 belegt; Krit. 1 als Dienst erfüllt, aber hinter Login + Cloudflare Access (anonymer `curl` liefert 302, nicht 200 — bewusst, Repo-Konvention). Die **Generierungs-Lane** (Arbiter → Box) bleibt draußen und setzt Phase 2 weiterhin voraus |
| `music-lab` | 4 | CLI → Hub-API; `gpu-dienst.ps1` als Break-glass mit Protokoll §4.4 | 🟡 Teilweise | 2026-08-16 | Auftrag [platform#2020](https://github.com/achimdehnert/platform/issues/2020) (SA-4). Client-Seite gebaut: HTTP-Vertrag v0 als Schema-Doc ([illustration-hub#258](https://github.com/achimdehnert/illustration-hub/pull/258), R2-REC-13-Nachzug — fehlte seit Phase 1), CLI-Lease-Client + `generate.py`-Integration + Break-glass-Protokoll ([music-lab#15](https://github.com/achimdehnert/music-lab/pull/15)); Selbsttest gegen Stub-Arbiter (4 Pfade) grün. **Offen:** End-to-End-Beleg mit Journal-Event (wartet auf Box 0b/2), Auth-Einrichtung (Owner-Befehlsdatei `~/gpu_lease_token_einrichten.sh` liegt bereit), §4.4-Wartungsmodus-Flag serverseitig ([illustration-hub#257](https://github.com/achimdehnert/illustration-hub/issues/257)) |
| `aifw` / neu `iil-gpufw` | 5 | Kosten-Go/Kill (§4.6); bei Go: Extraktion Client-Paket | 🟡 Teilweise | 2026-08-16 | **Kosten-Go/Kill gerechnet** ([Beleg](https://github.com/achimdehnert/platform/issues/2020#issuecomment-5308713540)): writing-hub-Volumen ≈ 0,57 $/Monat zu T1a-Preisen — ökonomisch **Kill** (Faktor ~17 unter der 10-$-Schwelle). Owner-Override nach §4.6 dokumentiert: Begründung ist Content-Souveränität (unzensierte Modelle — keine Cloud-Alternative), nicht Kosten. Konsequenz: Phase 5/6 auf das Minimum geschnitten, das platform#2020-K4 erfüllt; Extraktion selbst noch offen |
| `writing-hub` / `platform` | 6 | Batch-Vertragsteil bauen; writing-hub-Batch-Lane via iil-gpufw. **Vorbedingung:** `prod_host: prod`-Pin in ports.yaml (Netzpfad §4.1) | ⬜ Ausstehend | – | zweite ADR-292-Ausnahme, deklarativ |
| `platform` | 7 | Umbenennungs-Entscheid illustration-hub → media-hub (Go/Kill aus §4.6-Zählern) | ⬜ Ausstehend | – | Tracking-Issue [platform#2019](https://github.com/achimdehnert/platform/issues/2019) (Nachzug 2026-08-16 — war beim Phase-3-Zug entgegen der Zusage hier nicht angelegt worden) |

**Korrektur (2026-08-15): „Merge = Prod-Deploy" war für `illustration-hub` falsch.**
Eine frühere Fassung dieser Tabelle führte den Merge nach `main` als Prod-Schritt
und damit als freigabepflichtig. Das trifft hier nicht zu:
`.github/workflows/deploy.yml` hat in diesem Repo ausdrücklich **keinen**
`main`-Trigger — Prod wird nur über einen `v*`-Tag oder `workflow_dispatch`
aktualisiert, und der Workflow-Kommentar sagt genau das. Die Aussage stand hier,
ohne dass die Workflow-Datei geöffnet wurde. Der tatsächliche Prod-Schritt dieser
Sitzung war der Tag `v1.1.0`; er ist gelaufen und verifiziert (Image `v1.1.0` im
Container, Volume gemountet, Migration `music.0001_initial` angewandt).

**Notiz zur Reihenfolge Phase 2 → Phase 3 (2026-08-15).** R2-REC-8 ordnet die
Box-Abnahme vor die Musik-Aktivierung. Beim Umsetzen fiel auf, dass Phase 3 zwei
Dinge bündelt, die verschieden abhängig sind: die **Bibliothek** (Datenmodell,
feste URLs, Player über das bereits gesicherte Volume) braucht die GPU an keiner
Stelle, die **Generierungs-Lane** (Arbiter → Box) dagegen vollständig. Nur der
zweite Teil trägt das Risiko, das die Reihenfolge abfangen soll — die Bibliothek
liest Dateien, die seit Phase 0a ohnehin auf Prod liegen.

Entscheid des Owners: den box-freien Teil vorziehen, die Generierungs-Lane hinter
Phase 2 belassen. Damit werden music-lab#3 Kriterien 1+2 erreichbar, ohne die
Abnahme vorwegzunehmen. Die Abweichung steht hier, damit die Reihenfolge nicht
still driftet; R2-REC-8 bleibt für den GPU-abhängigen Teil unverändert gültig.

---

## 6. Consequences

### 6.1 Good

- Eine Bewirtschaftungs-Strategie statt zwei widersprüchlicher; Vorrang macht
  die lokale Auslagerung wirtschaftlich (Batch füllt Lücken statt zu konkurrieren)
- Arbeitsfläche mit Versionen/Varianten/Suche auf gesicherter, deployter
  Infrastruktur — music-lab#3 Kriterien 1/2/6 werden von der Plattform erfüllt
  statt einzeln nachgebaut
- „belegt ≠ kaputt" + Bezahl-Gate gelten in allen drei Lanes; jeder bezahlte
  Ausweich-Call ist sichtbar, budgetiert und alarmiert — stille Rückfälle sind
  in jeder Lane verschlossen
- Null neue Box-Dienste im Regelbetrieb; die Box-Wartungslast des Owners wächst
  nicht mit der Iterationsgeschwindigkeit des Arbiters
- Ereignisjournal macht jede Verdrängung/Doppelbelegung nachträglich
  rekonstruierbar

### 6.2 Bad

- Blast-Radius: illustration-hub wird Single Point of Failure für Bild UND Song
  (Text degradiert auf Groq und bleibt arbeitsfähig). Mitigation im Repo:
  Arbiter-Endpunkte hängen am bestehenden Health-Gate (`/readyz`), Rollback-Ziel
  = letztes grünes Image (dokumentierter Standard-Weg). **Benannter
  Evolutionspfad (R2-REC-12):** zeigt der Zähler „deploy-bedingte
  Batch-Abbrüche/Grant-Ausfälle" über 3 Monate wiederholt Störungen, wird der
  Arbiter als eigenständiges Mini-Control-Plane auf dem Prod-Host
  herausgelöst — bewusst NICHT vorab gebaut (ein zusätzlicher Dienst mit
  eigener Auth/Monitoring/Rollback für einen Einzel-Owner ist heute nicht
  begründbar).
- Interaktive Text-Calls zahlen nach jedem Bild/Song-Grant einen
  Modell-Kaltstart — akzeptierter Preis für „Text blockiert nie"
  (entfällt ggf. per Koresidenz-Check §4.7(3))
- Eine Lease ist ein Absichts-Register, keine Karten-Wahrheit; gegen den dritten
  Verbraucher hilft nur die Fehlerklassifikation. Unter Partition ist
  Doppelbelegung möglich und dokumentiert (§4.2 Nr. 9) — die Karte arbitriert
  physisch, das Gate verhindert Folgekosten
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
| Box-Ausfall bei Owner-Abwesenheit (strukturell: kein Fernzugriff) | Mittel | Hoch | Akzeptiert; Bezahlmatrix §4.3 (`nicht_erreichbar` zahlt sichtbar statt gar nicht oder still); trifft jede Architektur gleich |
| ACE-Step ohne Entlade-Pfad | Mittel | Mittel | Hartes Go/No-Go-Gate §4.7(1) mit ausformuliertem Negativ-Pfad (on-demand-Start, kein Autostart) VOR Aktivierung der Song-Lane |
| aifw-Failover umgeht Gate (=#179 in Text-Lane) | Hoch ohne Fix | Mittel | deny-by-default Provider-Wrapper §4.3 + Sofort-Alarm; Zähler machen Verstöße sichtbar |
| Doppelbelegung unter Partition (interaktiv fail-open + TTL-Ablauf) | Niedrig | Niedrig | Dokumentiert als akzeptiert (§4.2 Nr. 9): Karte arbitriert physisch, Verlierer endet gate-geschützt; Journal rekonstruiert Hergang |
| Zähler werden erhoben, aber nie gelesen („Melder ohne Leser") | Mittel | Mittel | Akute Klassen haben Sofort-Alarme (ritualunabhängig, §4.3); Ritual trägt nur Trends; ausbleibende Briefing-Einträge sind selbst Befund (§8) |
| Autostart-Fehlschlag detoniert erst beim nächsten Reboot | Mittel | Mittel | Außen-Abnahme mit echtem Reboot-Test §4.7 |
| Interface friert zu früh ein (vor Konsument 3) | Niedrig | Mittel | Versioniertes Schema-Doc + Kompatibilitätsfenster §4.5; 1.0 erst nach drei realen Konsumenten |
| Phasen 5–7 treten nie ein; Batch-Vertrag bleibt totes Versprechen | Mittel | Niedrig | Phasenschnitt §3: Batch wird erst GEBAUT beim committeten Konsumenten + Kosten-Go; bis dahin existiert nur Spezifikation, kein toter Code |
| writing-hub wandert per Long-Tail-Migration nach prod-b → Text-Lane bricht still | Mittel ohne Pin | Mittel | `prod_host: prod`-Pin als Phase-6-Vorbedingung (§4.1, §5) |

---

## 8. Confirmation

1. **Vertrags-Tests im Arbiter (CI, illustration-hub):** Testfälle für die
   Vertragseigenschaften aus §4.2 — insbesondere Doppel-Grant-Race (zwei
   parallele Acquires, genau einer gewinnt), Expire+Grant in einer Transaktion,
   `reserviert`-Persistenz, Heartbeat-Toleranz (N misses), Batch fail-closed,
   Journal-Vollständigkeit je Zustandswechsel. Merge-Gate wie üblich.
2. **Gate-Abdeckung strukturell (CI):** Bezahl-Provider-Aufrufe sind NUR über
   den deny-by-default-Wrapper (§4.3) möglich; CI prüft, dass außerhalb des
   Wrappers kein Provider-SDK importiert/aufgerufen wird, UND der Wrapper hat
   eigene Tests (Gate-Verweigerung, Sofort-Alarm-Pfad). Reiner Grep allein gilt
   nicht als Nachweis (R2-M28-2).
3. **Automatisierter Restore-Test (R2-REC-14):** periodisch (mind. je Quartal)
   eine Stichprobe aus dem ADR-289-Backup zurückholen und Konsistenz prüfen:
   DB-Datensatz ↔ WAV-Original ↔ MP3-Derivat ↔ feste URL antwortet 200.
   Ergebnis ins Briefing; „Backup existiert" allein zählt nicht.
4. **Monatliches Zähler-Ritual (§4.6):** Briefing-Eintrag existiert und enthält
   die Schwellen-Vergleiche; ausbleibende Einträge sind selbst ein Befund.
5. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft —
   Staleness-Schwelle: 6 Monate.

---

## Externer Review-Rückfluss (Rev 2, 2026-08-14)

Zwei externe Cross-Provider-Runden (Transport: `~/shared/adr-handoff-ADR-296-…`,
Anbieter vom Owner nicht benannt). Verdikt-Bilanz: **21 Empfehlungen, 21 valid,
21 eingearbeitet** (0 missversteht-Kontext, 0 out-of-scope) — Zählprobe R1: 7/7,
R2: 14/14. Befund-IDs sind über die REC-Spalte referenziert; PRO-Befunde beider
Runden: `[valid]`, bestätigend, keine Aktion.

| ID | Verdikt | Aktion |
|---|---|---|
| R1-REC-1 | [valid] | Netzpfad Text-Lane entschieden: prod-Pin writing-hub als Phase-6-Vorbedingung; Hub-Proxy verworfen (§4.1). Fakten-Check: writing-hub läuft heute per Default auf prod |
| R1-REC-2 | [valid] | Phasen umgeschnitten: Phase 1 = nur interaktiver Vertragsteil; Batch spezifiziert, ungebaut bis Kosten-Go (§3, §5) |
| R1-REC-3 | [valid] | Kosten-Go/Kill-Zahl vor Batch-Lane in §4.6 (Schwelle 10 $/Monat Groq-Äquivalent) |
| R1-REC-4 | [valid] | Dritter Vorab-Check Koresidenz Klein-LLM in §4.7(3); Ergebnis kann §4.2(6/7) vereinfachen |
| R1-REC-5 | [valid] | `ARBITER_DOWN`-Zusage präzisiert: nur eigene koordinierte Jobs; nichts über fremde (§4.2 Nr. 2) |
| R1-REC-6 | [valid] | Heartbeat-Toleranz N=3 misses + Zähler deploy-bedingte Batch-Abbrüche (§4.2 Nr. 4, §4.6) |
| R1-REC-7 | [valid] | Negativ-Fall ACE-Step ausformuliert: kein Autostart, on-demand-Protokoll je Session (§4.7(1)); s. a. R2-REC-6 |
| R2-REC-1 | [valid] | Normativer Grant-Algorithmus: Serverzeit, Expire+Grant in einer serialisierten Transaktion, Index als Backstop (§4.2 Nr. 1) |
| R2-REC-2 | [valid] | Identitäten in Vertrag: lease_id, Token, generation, holder_instance, job_id, idempotency_key, issued_at (§4.2) |
| R2-REC-3 | [valid] | Fehlermatrix §4.2 Nr. 9; Haltung explizit: Doppelbelegung unter Partition möglich, Karte arbitriert, Gate schützt |
| R2-REC-4 | [valid] | Zustände `reserviert`/`verdraengung_laeuft`/`ungewiss` übernommen; Pre-Check-Ersatz durch Pflicht-Lease bewusst NICHT übernommen — TOCTOU als begrenzt-gutartig dokumentiert, Begründung in §4.2 Nr. 7 |
| R2-REC-5 | [valid] | `GRANTED` erst nach Pause-Bestätigung/Timeout; `reserviert` persistent, blockiert konkurrierende Grants (§4.2 Nr. 3) |
| R2-REC-6 | [valid] | ACE-Step-Check = hartes Go/No-Go der Song-Lane; `ARBITER_DOWN`-Pfade je Lane benannt, Song-Fallback ≠ Exklusiv-Umschalter (§4.2 Nr. 2, §4.7(1)) |
| R2-REC-7 | [valid] | Normative Bezahlmatrix mit Startwerten N=4 h, M=3, Groq-Budget 5 $/Monat; `nicht_erreichbar` als eigene sichtbare Klasse (§4.3) |
| R2-REC-8 | [valid] | Migration umgeordnet: Box-Abnahme (Phase 2) vor Musik (Phase 3); Extraktion (Phase 5) vor writing-hub-Aktivierung (Phase 6) (§4.5, §5) |
| R2-REC-9 | [valid] | Break-glass-Protokoll: Wartungsmodus-Flag, sichtbare Invalidierung, Außen-Abnahme, explizite Rückkehr (§4.4) |
| R2-REC-10 | [valid] | deny-by-default Provider-Wrapper + Sofort-Alarm je bezahltem Call trotz belegt/unklar; ritualunabhängig (§4.3, §8 Nr. 2) |
| R2-REC-11 | [valid] | Verbraucher als erweiterbarer Schlüssel; Batch-Warte-SLO (24 h) mit definierter Reaktion statt Dauer-Alarm (§4.2) |
| R2-REC-12 | [valid] | Control-Plane-Split NICHT vorab gebaut, aber als benannter Evolutionspfad mit messbarem Auslöser; in-Repo-Mitigation Health-Gate + Rollback-Ziel (§6.2) |
| R2-REC-13 | [valid] | HTTP-Vertrag als versioniertes Schema-Doc mit Fehlerobjekten, Timeout-/Idempotenz-Semantik, Kompatibilitätsfenster, leichtem Deprecation-Prozess (§4.5) |
| R2-REC-14 | [valid] | Append-only `gpu_lease_event`-Journal (§4.2) + automatisierter Restore-Konsistenztest als Confirmation-Mechanismus (§8 Nr. 3) |

Nicht REC-gebundene Befunde: R1-AD-2 → adressiert über Phasenschnitt-Absatz in §3
`[valid]` · R1-M28-1 → §7 Risiko „Phasen treten nie ein" `[valid]` · R1-M28-2 /
R2-AD-12 → Sofort-Alarme entkoppeln Akutes vom Ritual `[valid]` · R2-AD-14 /
M28-7 → §6.2 Evolutionspfad `[valid]` · R2-M28-1 → §4.5 Schema-Doc `[valid]` ·
R2-M28-2 → §8 Nr. 2 strukturell statt Grep `[valid]` · R2-M28-3/M28-5 →
Journal + Restore-Test `[valid]` · R2-M28-4 → SLO §4.2 `[valid]` · R2-M28-6 /
AD-11 → Break-glass §4.4 `[valid]` · R2-AD-15 → Lane-Pfade §4.2 Nr. 2 `[valid]`.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **Lease** | Zeitlich befristete, verlängerbare Nutzungs-Zusage für die GPU — ein Absichts-Register, keine physische Sperre |
| **Arbiter** | Die eine Stelle, die Leases erteilt, verdrängt und einsehbar macht (hier: Modul + HTTP-API in illustration-hub) |
| **VRAM** | Grafikspeicher der GPU (hier 24 GB) — die knappe, umkämpfte Ressource |
| **TTL** | Time to live — Ablauffrist einer Lease; verwaiste Leases sterben dadurch ohne Aufräum-Skript |
| **TOCTOU** | Time-of-check-to-time-of-use — Lücke zwischen Prüfung und Nutzung, in der sich der Zustand ändern kann (§4.2 Nr. 7) |
| **WDDM** | Windows Display Driver Model — Windows-Treibermodus, unter dem `nvidia-smi` Prozess-Details oft nicht liefert (unverifizierte Annahme → Vorab-Check §4.7) |
| **WG / WireGuard** | VPN, über das Prod-Host und Box sich erreichen (`10.99.0.2`) |
| **fal** | Bezahlter Cloud-Bildanbieter — der Rückfallpfad, dessen stille Nutzung #179 auslöste |
| **aifw** | Haus-Framework für LLM-Routing (litellm-basiert); routet writing-hub-Calls auf Provider |
| **Batch / interaktiv** | Aufschiebbare Massenläufe vs. sofort erwartete Einzelaufträge — die zwei Vorrang-Klassen dieses ADR |
| **Kaltstart** | Neuladen eines entladenen Sprachmodells in den VRAM — Kostenfaktor der Verdrängung |
| **Break-glass** | Dokumentierter Not-Eingriff am Regelmechanismus vorbei — erlaubt, aber protokolliert (§4.4) |
| **SLO** | Service Level Objective — hier: maximal akzeptiertes Batch-Wartealter mit definierter Reaktion |
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
- ADR-292 — Two-Lane-Deployment; illustration-hub-Ausnahme (WG-Route zur Box);
  writing-hub-Pin wird zweite Ausnahme derselben Klasse (Phase 6)
- Design-Panel-Dossier 2026-08-14 (3 Entwürfe × 2 Prüfungen × 3 Richter) —
  Session-Artefakt, Kernergebnisse in §2/§4 eingearbeitet
- Externe Zweitmeinungen R1+R2 2026-08-14 — Transport `~/shared/` (ephemer),
  durabler Nachweis: Frontmatter `ai_sparring_by` + §Review-Rückfluss

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-08-14 | Achim Dehnert | Initial: Status Proposed — Synthese aus adversarialem Design-Panel |
| 2026-08-14 | Achim Dehnert | Rev 2: 21 externe REC-Empfehlungen (2 Runden) eingearbeitet — Zustandsmaschine + Identitäten + Fehlermatrix (§4.2), Bezahlmatrix + Wrapper + Sofort-Alarm (§4.3), Break-glass (§4.4), Schema-Doc + Extraktions-Reihenfolge (§4.5), Kosten-Go/Kill (§4.6), 3. Vorab-Check + ACE-Step-Negativ-Pfad (§4.7), Phasen umgeschnitten (§5), Netzpfad Text-Lane entschieden (§4.1); Tag-Tabelle §Review-Rückfluss |
| 2026-08-14 | Achim Dehnert | Accepted — Owner-Review nach 2 externen Runden, Merge platform#1979, Go im Kapitäns-Kanal |
