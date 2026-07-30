---
status: proposed
decision_date: 2026-07-30
deciders: Achim Dehnert
consulted: Claude Code
informed: –
supersedes: []
amends: [ADR-241]
ai_sparring_by:
  - tool: other
    date: 2026-07-30
    role: adversarial-review
    summary: "Externes LLM (Runde 1) auf ADR-289: Verdikt ueberarbeiten. Kern: Option A ist nicht entschieden (R2 ungeordnet, R3 kann entfallen, R4 spaetere Entscheidung); falsifizierte 16-h-Behauptung wirkt in Paragraph 3/6.1 fort; CI-Runner ist ein Rechte-, nicht nur ein Speicherproblem; R2 ist vom AVV doch betroffen (Loki-Logs); Negativ-Regel als Allowlist statt Denylist. Tag-Tabelle Paragraph 11."
  - tool: other
    date: 2026-07-30
    role: adversarial-review
    summary: "Externes LLM (Runde 2) auf ADR-289: Verdikt ueberarbeiten. Kern: das ADR wiederholt den Fehler, den es an ADR-241 diagnostiziert (eine belegte Entscheidung an drei unfertige gebunden); ungestellte Frage warum ADR-241 sechs Wochen nicht gebaut wurde; Kapazitaetsargument gegen Option B und D gegenlaeufig verwendet; ADR-257-Lehre nur auf R3 statt auch auf R2 angewandt; Append-only ist unterverkauft (SFTP kann es nicht erzwingen, rest-server schon). Tag-Tabelle Paragraph 11."
related: [ADR-059, ADR-098, ADR-142, ADR-157, ADR-164, ADR-248, ADR-257]
implementation_status: none
last_reviewed: 2026-07-30
staleness_months: 6
tags: [infrastructure, hosts, backup, disaster-recovery, provider-diversity, netcup]
---

# ADR-289: Adopt netcup as Off-Provider Backup Target — Further Platform Roles Deferred

## Metadaten

| Attribut          | Wert                                                                  |
|-------------------|-----------------------------------------------------------------------|
| **Status**        | Proposed                                                              |
| **Scope**         | platform                                                              |
| **Erstellt**      | 2026-07-30                                                            |
| **Autor**         | Achim Dehnert                                                         |
| **Reviewer**      | – (zwei externe KI-Reviews, §11 — nicht accountable)                  |
| **Supersedes**    | –                                                                     |
| **Superseded by** | –                                                                     |
| **Amends**        | ADR-241 (Backup- & Disaster-Recovery-Baseline) — Offsite-Ziel + Status |
| **Relates to**    | ADR-059 (Drift-Detector), ADR-098 (Infrastructure Tuning), ADR-142 (Stack-Backups), ADR-157 (3-Server-Architektur), ADR-164 (Port-Strategie), ADR-248 (COMPOSE_PROJECT_NAME), ADR-257 (CI-Host-Isolation) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                        |
|----------------|------------|-------------------------------------------------------|
| `platform`     | Primär     | `infra/hosts.yaml`, `docs/adr/ADR-241`, `deployment/scripts/offsite-backup.sh`, `.github/workflows/backup-meter.yml` |
| `risk-hub`     | Sekundär   | MinIO-Volume (Kundendokumente) — erster Konsument      |
| `mcp-hub`      | Sekundär   | `mcp_hub_pgdata` (Orchestrator-pgvector) — zweiter Konsument |

---

## Decision Drivers

- **Das Offsite-Backup ist zu 80 % gebaut und hängt an genau einem fehlenden Stück.** ADR-241
  wurde am Accept-Tag (2026-06-21) weitgehend umgesetzt: `deployment/scripts/offsite-backup.sh`
  (restic-Wrapper), `tools/backup_meter.py`, `governance/backup/expected-apps.json` und
  `.github/workflows/backup-meter.yml` existieren und laufen. Was fehlt, ist die
  **Provisionierung des Repositories** — `restic` ist auf `prod` nicht installiert,
  `RESTIC_REPOSITORY` ist nirgends gesetzt. Und dieses Stück war **durch das Ziel blockiert**:
  eine Umgebungsvariable kann nicht auf einen Beschluss zeigen, nur auf ein existierendes
  Repository. Die Storage Box wurde nie bestellt (§1.2).
- **Das beschlossene Ziel liegt beim selben Anbieter.** ADR-241 wählte eine Hetzner Storage
  Box BX11. Alle fünf Bestandshosts sind Hetzner — ein Ziel im selben Konto isoliert weder
  Konto-, Abrechnungs- noch anbieterweite Störungen.
- **Kundendokumente sind ungesichert.** Das MinIO-Volume von risk-hub und `mcp_hub_pgdata`
  (Orchestrator-pgvector) haben bis heute keine Offsite-Kopie.
- **Der Ausfall dieser Sicherung wird nicht gemeldet.** Der Backup-Meter läuft täglich und
  meldet grün — im Scaffold-Modus, der „noch nicht provisioniert" nicht von „gesichert"
  unterscheidet. Sechs Wochen lang hat das niemand bemerkt ([#1567](https://github.com/achimdehnert/platform/issues/1567)).
- **Die Maschine ist bereits bezahlt und ungenutzt.** netcup läuft seit 113 Tagen mit
  Load 0,00 und 1 GiB Monatstraffic. Die Alternative zur Nutzung ist Leerlauf, nicht Ersparnis.

---

## 1. Context and Problem Statement

Zum Bestand ist eine sechste Maschine hinzugekommen: ein netcup-Server in Nürnberg,
12 vCPU / 31 GiB RAM / 1007 GB Disk, seit 113 Tagen bezahlt und faktisch unbenutzt. Sie ist
der **erste und einzige Host außerhalb der Hetzner-Fehlerdomäne** und hat mit 1 TB die größte
Disk im Bestand.

Gleichzeitig wartet ein fertig gebautes Offsite-Backup auf ein Ziel, das es beim bisher
beschlossenen Anbieter nicht sinnvoll geben kann.

### 1.1 Ist-Zustand

Alle Werte per SSH-Probe am 2026-07-30 erhoben und in `infra/hosts.yaml` festgehalten:

| Host | Anbieter / Ort | CPU | RAM belegt | Swap | Disk | Container |
|---|---|---|---|---|---|---|
| `prod` | Hetzner nbg1 (DE) | 12 | 10,7 / 23,5 GB (46 %) | 1,8 / 4,0 GB | `/` 65 %, Vol 32 % | 46 |
| `prod-b` | Hetzner hel1 (FI) | 8 | 1,1 / 15,6 GB (**7 %**) | – | 2 % | 4 |
| `staging` | Hetzner fsn1 (DE) | 16 | 17 / 30 GB | **8,0 / 8,0 GB (100 %)** | 28 % | 43 |
| `staging-dedicated` | Hetzner fsn1 (DE) | 8 | 3,7 / 15,6 GB (**23 %**) | – | 3 % | 12 |
| `odoo` | Hetzner, eigenes Konto | 4 | 1,5 / 7,7 GB (19 %) | – | 21 % | 10 |
| `netcup` | **netcup, Nürnberg (DE)** | 12 | 0,55 / 31 GB (**2 %**) | 8 GB (2026-07-30) | 1 % | **0** |

### 1.2 Warum jetzt — und warum ADR-241 sechs Wochen lag

Die naheliegende Erklärung („keine Zeit") ist **falsch**, und das ist entscheidungsrelevant.
Belegt aus der Historie:

| Was | Stand |
|---|---|
| `offsite-backup.sh` (restic-Wrapper) | ✅ gebaut 2026-06-21 (#620) |
| `backup_meter.py` + Tests + `expected-apps.json` | ✅ gebaut 2026-06-21 (#620/#622) |
| `backup-meter.yml` (täglich 05:00) | ✅ läuft, letzte 5 Läufe `success` |
| `restic` auf `prod` installiert | ❌ nein |
| `RESTIC_REPOSITORY` gesetzt, Cron aktiv | ❌ nein (nur `authentik-backup`, `outline-backup` aus ADR-142) |

ADR-241 wurde am Tag seines Accepts weitgehend umgesetzt. Es fehlt **ein** Schritt, und der
hängt am Ziel: `RESTIC_REPOSITORY` braucht ein existierendes Repository. Die Storage Box
wurde nie bestellt, also gab es nichts, worauf die Variable hätte zeigen können.

Dass dieser eine fehlende Schritt sechs Wochen unbemerkt blieb, liegt am grün meldenden
Meter (#1567) — nicht an fehlender Aufmerksamkeit für das Thema.

**Folge für dieses ADR:** Der Zielwechsel ist kein Umweg, sondern genau das fehlende Stück.
R1 ist damit **kein Neubau, sondern die Provisionierung eines seit sechs Wochen fertigen
Wrappers** — eine Sache von Stunden.

### 1.3 Falsifizierte eigene Begründung (adversariales Review 2026-07-30)

Die erste Fassung dieses ADR trug als Treiber: „`prod` hat kein Monitoring, deshalb blieb der
OOM-Ausfall am 2026-07-20 16 Stunden unbemerkt." **Beide Hälften sind widerlegt:**

| Behauptung | Befund |
|---|---|
| „kein Monitoring" | `.github/workflows/prod-uptime-canary.yml` läuft seit 2026-06-17 alle 15 min über 41 URLs — darunter der betroffene Hub — und legt automatisch Issues an |
| „16 Stunden unbemerkt" | OOM begann 18:26, Canary-Issue #1282 wurde **18:42** angelegt — nach 16 **Minuten** |

Dieselbe Fehlerklasse steht als Drift-Memory `error:writing-hub:20260722-absence-claim` fest
— dort wurde aus „kein Betterstack-Monitor" ein „kein Monitoring", obwohl **genau diese
Canary-Datei** den Hub abdeckte. Die vorgeschriebene Gegenprobe
(`grep -rl '<domain>' .github/workflows/`) war nicht gefahren worden.

**Was daraus folgt:** Der Engpass ist die **Zustellung**, nicht die Erkennung. Ein
GitHub-Issue ist ein Protokoll, kein Alarm; #1282 lag 18 Stunden offen, und der Backup-Meter
meldet seit sechs Wochen grün über einer leeren Sicherung. Beides zusammen ist ein Argument
für **einen Kanal, der einen Menschen erreicht** — und der ist netcup-**unabhängig**
(§4.5). Die Monitoring-Rolle verliert damit ihren dringlichsten Treiber und ist in dieser
Fassung **zurückgestellt** (§3.2).

---

## 2. Considered Options

### Option A: netcup als Off-Provider-Backup-Ziel, App-Hubs ausgeschlossen ✅

Der Host wird **ausschließlich** Ziel des bereits gebauten restic-Wrappers. Weitere Rollen
sind erwogen und zurückgestellt (§3.2).

**Pros:**
- Liefert exakt das fehlende Stück von ADR-241 — kein Neubau, nur Provisionierung.
- Erster Ort außerhalb der Hetzner-Fehlerdomäne; erfüllt die Absicht von ADR-241 tatsächlich
  statt nur formal.
- netcup ist ein **Server**, keine Ablage: `rest-server --append-only` erzwingt
  Append-only **technisch** — eine Storage Box über SFTP kann das nicht (§4.2). Damit werden
  serverseitige Retention und lokale Restore-Übungen überhaupt erst möglich.
- 0 € Mehrkosten statt ~5 €/Monat.
- Schmaler Schnitt: in Stunden abschließbar, nicht in Quartalen.

**Cons:**
- Neuer Auftragsverarbeiter → AVV vor dem ersten Backup mit Personenbezug.
- Sechster Host im Betrieb (Patching, Firewall).
- Kosten und Restlaufzeit der Maschine sind **unbekannt** (§7).

### Option B: netcup als sechster App-Hub-Host

**Cons:** → **Abgelehnt weil:** `prod-b` steht zu 93 %, `staging-dedicated` zu 77 % leer —
freie Kapazität liegt bereits auf NVMe bereit. Ein weiterer Hub-tragender Host erhöht die
Betriebslast einer einzelnen Person und verbraucht den einzigen Off-Provider-Ort für eine
Aufgabe, die andere Hosts erledigen können.

### Option C: netcup kündigen, bei der Hetzner Storage Box BX11 bleiben

**Cons:** → **Abgelehnt weil:** Das Ziel bliebe beim selben Anbieter — eine Storage Box ist
ein zweites Rechenzentrum, keine zweite Fehlerdomäne. Zusätzlich kann sie
restic-Append-only **nicht erzwingen** (SFTP-Backend) und keine Restore-Übung fahren; die
Feuerübung G3 aus ADR-241 bliebe Theorie.

### Option D: netcup nur als Blob-Ablage, sonst nichts

Faktisch identisch mit Option A in dieser Fassung. Die frühere Ablehnung („verschenkt 12
Kerne und 30 GB RAM") ist **zurückgezogen**: ungenutzte CPU ist kein Schaden, und dasselbe
Kapazitätsargument gegen Option B zu verwenden und für Option D gegen sich selbst zu wenden,
war ein Widerspruch (Review-Befund B2). Eine bewusst kleine Angriffsfläche ist im
Ein-Personen-Betrieb ein Vorteil, kein Verzicht.

### Option E: Objektspeicher eines dritten Anbieters (S3 + Object Lock)

**Pros:** Anbieter- **und** geografische Unabhängigkeit; Object Lock ist härter als ein
Append-only-Schlüssel; kein sechster Host im Dauerbetrieb.

**Cons:** Laufende Kosten und Egress-Gebühren bei `check --read-data`; ein zweiter AVV
ebenso nötig; nutzt die bereits bezahlte Maschine nicht. → **Abgelehnt weil:** Die
vorhandene, bezahlte Maschine erfüllt denselben Zweck zu 0 €, und sie kann zusätzlich als
Restore-Rechner dienen. **Bleibt die erste Alternative**, falls Kosten/Laufzeit von netcup
ungünstig ausfallen (§7).

### Option F: Host-Zahl senken statt Rolle vergeben

netcup könnte `staging` und `staging-dedicated` absorbieren und die bekannte
Staging-Doppelung auflösen. → **Abgelehnt weil:** Der Migrationsaufwand ist unter
Ein-Personen-Betrieb selbst zu teuer, und das Offsite-Problem bliebe offen. Dokumentiert,
damit die Frage nicht in zwei Jahren neu erfunden wird.

---

## 3. Decision Outcome

### 3.1 Beschlossen

**netcup wird Off-Provider-Ziel des bestehenden restic-Backups, und auf ihm laufen keine
App-Hub-Stacks.** Das ist der gesamte Entscheidungsinhalt dieses ADR.

Als **Amendment zu ADR-241** wird das dort gewählte Offsite-Ziel („Hetzner Storage Box
BX11") durch netcup ersetzt und `implementation_status` von `none` auf `partial` korrigiert
— der Code steht, es fehlt die Provisionierung. Alle übrigen Festlegungen von ADR-241
(restic, Verschlüsselung, Retention, Backup-Meter, Feuerübung G3) bleiben unverändert gültig.

Der Zuschnitt folgt einem Befund, den zwei externe Reviews unabhängig fanden (§11): die
erste Fassung band diese eine belegte Entscheidung an drei Rollen ohne tragenden Treiber und
machte sich damit un-fertigstellbar — genau der Fehler, den dieses ADR an ADR-241 diagnostiziert.

### 3.2 Erwogen und zurückgestellt — je mit auslösendem Treiber

Diese Rollen sind **nicht beschlossen**. Jede bekommt ein eigenes ADR, sobald ihr Treiber
belegt ist. Bis dahin dürfen sie nicht als geplante Fähigkeit zitiert werden.

| Rolle | Zurückgestellt, weil | Auslösender Treiber für ein eigenes ADR |
|---|---|---|
| **Unabhängiges Monitoring** | Der dringlichste Treiber ist falsifiziert (§1.3); Endpoint-Uptime ist abgedeckt. Der verbleibende Rest — Host-Metriken und Beobachter-Domäne — ist real, aber nicht dringend. **Vorher** ist die Alarm-Zustellung zu bauen (§4.5), die netcup-unabhängig ist. | Ein Vorfall, den Host-Metriken **früher** sichtbar gemacht hätten als der Endpoint-Check — oder eine belegte Datenmenge, die die Speicherfrage entscheidet |
| **CI-/Build-Runner** | Zwei ungelöste Vorbedingungen: der Build-Wall-Clock-Vergleich fehlt, und ein CI-Runner neben dem Backup ist ein **Rechte**-, nicht nur ein Speicherproblem (§7) | Bestandener Build-Vergleich **und** eine Isolation, die dem Runner den Zugriff auf Backup-Daten und -Zugangsdaten technisch verwehrt |
| **DR-Standby** | Weder Dienste, Kapazität, RTO/RPO noch ein getesteter Wiederanlauf sind bestimmt | Bestandene Feuerübung G3 **und** ein bezifferter RTO/RPO-Bedarf |

---

## 4. Implementation Details

### 4.1 Grundlage: Messung statt Anbieterangabe

Das netcup-Panel führt das Startlaufwerk als **„HDD"**, `lsblk` meldet `ROTA=1`. Beides ist
durch Messung widerlegt (2026-07-30):

| Metrik | netcup | `staging-dedicated` (NVMe) | Verhältnis |
|---|---|---|---|
| Sequenziell schreiben, 2 GB, `oflag=direct` | 633 MB/s | 879 MB/s | 0,72 × |
| fsync-Latenz, 1000 × 4 K, `oflag=dsync` | 1,44 ms/Commit | 1,24 ms | 0,88 × |
| Sequenziell lesen, cache-frei | 653 MB/s | 1,7 GB/s | 0,38 × |
| `randwrite` 4 K, iodepth 32, 30 s | **43,3k IOPS**, 169 MiB/s, p99 5,5 ms | – | – |
| `randread` 4 K, 45 s | **94,0k IOPS** | – | – |

Eine rotierende Platte liefert 150–200 MB/s sequenziell und 100–200 IOPS. Die Speicherklasse
ist damit geklärt: **SSD-gestützt**; `ROTA=1` ist virtio-Voreinstellung ohne Aussagewert.
Für die Backup-Rolle ist das mit großer Reserve ausreichend.

**Nicht gemessen:** Verhalten unter Dauerlast über Wochen (geteilter Speicher, „noisy
neighbour"). Für R1 unkritisch — restic schreibt in Schüben, nicht dauerhaft.

### 4.2 Repository-Provisionierung (der fehlende Schritt aus ADR-241)

1. `rest-server` auf netcup mit **`--append-only`** — das ist der Punkt, an dem netcup einer
   Storage Box technisch überlegen ist: über SFTP lässt sich Append-only nicht erzwingen,
   ein kompromittierter Quell-Host könnte seine eigenen Sicherungen löschen. Mit
   `rest-server --append-only` kann er es nicht.
2. `restic` auf `prod` installieren, `RESTIC_REPOSITORY` und `RESTIC_PASSWORD_FILE` setzen,
   `offsite-backup.sh` per Cron aktivieren — das Skript existiert seit 2026-06-21.
3. Der administrative **Prune-/Retention-Pfad** läuft mit einem **getrennten** Zugang direkt
   auf netcup, nie über den Append-only-Schlüssel der Quell-Hosts.
4. Reihenfolge nach Dringlichkeit: risk-hub inkl. **MinIO-Volume**, dann `mcp_hub_pgdata`,
   dann `pg_dumpall` der übrigen Hubs.

**Offen zu spezifizieren, bevor Schritt 1 läuft:** Ablage des Repository-Schlüssels
(ADR-045), Verhalten bei Kompromittierung des Zielhosts selbst, und die Frage, ob der
Meter den Append-only-Zustand verifizieren kann.

### 4.3 Speicherbudget — offen, und deshalb hier benannt

Es existiert **kein** bezifferter Wert für Backup-Volumen, Wachstum oder Retention-Größe.
Damit ist auch die Aussage „diese Rolle braucht den 1-TB-Host" **unbelegt** — sie ist
plausibel (37 GB Images + 21 GB Volumes auf `prod`), aber nicht gemessen.

**Vor** der Provisionierung sind drei Zahlen zu erheben: erwartetes Repository-Volumen nach
erstem Vollbackup, monatliches Wachstum, Retention-Ziel aus ADR-241. Das restic-Repository
bekommt ein **eigenes Dateisystem oder Logical Volume mit fester Größe** — bevor irgendein
zweiter Dienst auf den Host kommt. Grund: ADR-257 hat belegt, dass Co-Tenant-Churn eine
geteilte Disk füllt; diese Lehre gilt für **jeden** späteren Mitbewohner, nicht nur für CI.

### 4.4 Negativ-Regel: keine App-Hubs — als Allowlist

Auf netcup laufen **keine** App-Hub-Stacks. Wandernde Hubs gehen nach `prod-b` oder
`staging-dedicated`.

Die Prüfung ist eine **Allowlist**, keine Suche nach bekannten Hub-Namen: erlaubt ist genau,
was in einer gepflegten Liste steht (derzeit `rest-server`); alles andere ist ein Verstoß.
Eine Denylist gegen Namen aus `ports.yaml` würde Umbenennungen, unregistrierte Anwendungen
und nicht per Compose gestartete Dienste übersehen.

### 4.5 Alarm-Zustellung — netcup-unabhängig, vorrangig

Aus §1.3 folgt der wirksamste Einzelschritt, und er braucht **keinen** neuen Host: der
bestehende `prod-uptime-canary` hat am 2026-07-20 funktioniert, ihm fehlt nur ein Empfänger,
der einen Menschen erreicht. Zwei Ergänzungen an einer laufenden Datei:

1. ein Zustellkanal (Push/Mail/Discord) statt eines Issues, das 18 Stunden liegen bleibt;
2. eine Probe **„letzter restic-Snapshot älter als 26 h"** — sie liefert zugleich den
   Dead-Man's-Switch für R1 aus einer **dritten** Domäne (GitHub), denn ein Wächter **auf**
   netcup kann netcups eigenen Ausfall nicht melden.

Nach der ADR-Schwelle ist das vermutlich kein eigenes ADR, sondern ein Changelog-Eintrag.
Es ist hier verzeichnet, weil es die Reihenfolge bestimmt: **erst dieser Kanal, dann R1s
Feuerübung** — sonst gilt für das neue Backup dieselbe Blindheit wie für das alte (#1567).

---

## 5. Migration Tracking

| Phase | Status | Datum | Notizen |
|---|---|---|---|
| 0 — Host in SoT | ✅ Abgeschlossen | 2026-07-30 | `infra/hosts.yaml`, PR #1560 |
| 1 — Grundinstallation | ✅ Abgeschlossen | 2026-07-30 | `netcup-bootstrap.sh`; rollenneutral, greift der Entscheidung nicht vor |
| 2 — **AVV mit netcup** | ⬜ Ausstehend | – | **Vorbedingung für Phase 5.** Braucht Datum + Aufwandsschätzung, sonst Platzhalter vor offener Datenlücke |
| 3 — Kosten/Laufzeit offenlegen | ⬜ Ausstehend | – | ⚠ Phase 1 lief bereits vorher — zulässig, weil rollenneutral, aber vor Phase 5 zwingend (Option E bleibt sonst nicht vergleichbar) |
| 4 — Speicherbudget erheben (§4.3) | ⬜ Ausstehend | – | drei Zahlen; danach eigenes Dateisystem für das Repository |
| 5 — `rest-server --append-only` + Provisionierung | ⬜ Ausstehend | – | der fehlende Schritt aus ADR-241 |
| 6 — risk-hub inkl. MinIO sichern | ⬜ Ausstehend | – | dringlichster Einzelfix |
| 7 — `mcp_hub_pgdata` sichern | ⬜ Ausstehend | – | kein Backup-Skript vorhanden |
| 8 — Alarm-Zustellung + Snapshot-Frische (§4.5) | ⬜ Ausstehend | – | **vor** Phase 9; netcup-unabhängig, in Stunden baubar |
| 9 — Feuerübung G3 (Cross-Host) | ⬜ Ausstehend | – | erst danach gilt R1 als belegt |
| 10 — ADR-241 Statuszeile | ⬜ Ausstehend | – | `amended_by: ADR-289` + `implementation_status: partial`, sobald dieses ADR `accepted` ist |
| 11 — ADR-157 amendieren | ⬜ Ausstehend | – | 3-Server-Architektur vs. sechs reale Hosts — eigener Vorgang, [#1564](https://github.com/achimdehnert/platform/issues/1564) |

---

## 6. Consequences

### 6.1 Good

- Das seit sechs Wochen fertige Offsite-Backup bekommt sein Ziel; die dringlichste Datenlücke
  (Kundendokumente) wird schließbar — in Stunden, nicht Quartalen.
- Erstmals ein Sicherungsziel außerhalb der Hetzner-Fehlerdomäne.
- Append-only wird **technisch erzwingbar** statt nur vereinbart.
- Restore-Übungen werden praktikabel, weil das Ziel ein Server ist.
- 0 € Mehrkosten; die geplanten ~5 €/Monat entfallen.
- Der schmale Schnitt hält R2/R3/R4 aus dem kritischen Pfad des Dringlichen.

### 6.2 Bad

- Neue Anbieterbeziehung mit eigener Vertrags-, AVV- und Patch-Verantwortung.
- Sechster Host im Betrieb.
- Abhängigkeit von einer Maschine, deren Kosten und Restlaufzeit **unbekannt** sind.
- **Anbieter- ist nicht geografische Unabhängigkeit:** `prod` (nbg1) und netcup liegen beide
  in Nürnberg. Regionale Ereignisse (Strom, Netz, Naturereignis, behördlicher Zugriff)
  bleiben eine gemeinsame Achse. Eine zweite restic-Kopie nach `prod-b` (Helsinki, 2 %
  Disk-Belegung) könnte sie später schließen — dieses ADR entscheidet das nicht.

### 6.3 Nicht in Scope

- App-Hubs auf netcup (§4.4).
- Gov-/Sozialdaten-Workloads (meiki-lra, frist-hub) — eigener Auftragsverarbeiter, eigene
  Entscheidung.
- Die Staging-Doppelung zwischen `staging` und `staging-dedicated`.
- Monitoring, CI-Runner, DR-Standby — zurückgestellt mit Treibern (§3.2).

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| AVV fehlt, Backups mit Personenbezug landen trotzdem dort | Niedrig | **Kritisch** | Phase 2 ist Vorbedingung von Phase 5, nicht Parallelarbeit. **Auch Metriken und Logs können personenbezogen sein** (IP-Adressen, Nutzerkennungen in Loki) — die frühere Aussage „nur Backups betroffen" war eine Annahme und ist zurückgezogen |
| Kompromittierter Quell-Host löscht die Sicherungen | Niedrig | Hoch | `rest-server --append-only`; getrennter administrativer Prune-Pfad (§4.2) |
| Kompromittierung des **Ziel**-Hosts | Niedrig | Hoch | **Offen** — §4.2 nennt es als zu spezifizieren; Append-only schützt nicht gegen root auf netcup selbst |
| Speicher läuft voll, Backup-Reserve wird von Mitbewohnern aufgebraucht | Mittel | Hoch | Eigenes Dateisystem für das Repository **vor** jedem zweiten Dienst (§4.3), nicht erst vor CI |
| Ein Wächter auf netcup kann netcups Ausfall nicht melden | Mittel | Hoch | Snapshot-Frische-Probe im GitHub-Canary — dritte Domäne (§4.5) |
| Backup existiert, ist aber nicht wiederherstellbar | Mittel | **Kritisch** | Feuerübung G3 als **Cross-Host**-Restore mit Anwendungsstart, Secrets, DNS und fachlicher Datenprüfung — ein Restore auf dem Repository-Host selbst beweist nur Lesbarkeit (§8) |
| Kosten/Laufzeit ungünstiger als Option E oder BX11 | Niedrig | Mittel | Phase 3 vor Phase 5; bis dahin ist nichts Irreversibles geschehen. Eine auslaufende Vertragsperiode würde das einzige Offsite-Ziel in ein Migrationsprojekt verwandeln |
| Schleichende Umnutzung zum Hub-Host | Mittel | Mittel | Allowlist-Prüfung (§4.4, §8) |

---

## 8. Confirmation

1. **Host-SoT-Gate** — `infra/scripts/hosts_audit.py` im bestehenden CI-Gate; der
   `netcup`-Eintrag muss die beschlossene Rolle tragen.
2. **Allowlist maschinell** — auf netcup läuft **kein** Container außerhalb der Allowlist
   (§4.4). Ein Einzeiler, kein Ermessen.
3. **R1 gilt erst als erfüllt, wenn ein Restore lief** — `restic snapshots` zeigt
   Sicherungen für risk-hub (inkl. MinIO) und `mcp_hub_pgdata`, **und** die Feuerübung G3 ist
   als **Cross-Host**-Restore bestanden: Rückspielen auf einen anderen Rechner, Anwendung
   startet, Secrets und DNS greifen, fachliche Stichprobe stimmt, Wiederherstellungszeit
   gemessen. Ein vorhandenes Repository ohne bestandenen Restore gilt nicht.
4. **Append-only ist nachgewiesen, nicht behauptet** — ein Löschversuch mit dem
   Quell-Host-Schlüssel muss fehlschlagen.
5. **Die Sicherung meldet sich selbst** — die Snapshot-Frische-Probe (§4.5) läuft in der
   dritten Domäne und ist einmal scharf ausgelöst worden. Solange sie fehlt, gilt R1 als
   unbeobachtet, unabhängig davon, ob Snapshots existieren (#1567).
6. **Drift-Detector**: geprüft nach ADR-059 — Staleness-Schwelle **6 Monate**.

---

## Glossar

| Begriff | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — festgehaltene Architekturentscheidung samt Begründung und verworfenen Alternativen. |
| **AVV** | Auftragsverarbeitungsvertrag — nach DSGVO nötig, wenn ein Dienstleister personenbezogene Daten für uns speichert oder verarbeitet. |
| **Fehlerdomäne** | Bereich, der gemeinsam ausfällt. Zwei Rechenzentren eines Anbieters teilen Konto und Abrechnung und sind darin **eine** Domäne — geografisch können sie trotzdem getrennt sein, und umgekehrt (§6.2). |
| **restic** | Sicherungswerkzeug mit Verschlüsselung, Deduplizierung und Append-only-Betrieb. |
| **`rest-server --append-only`** | Der zu restic gehörende Server, der Löschen **technisch** verweigert — im Unterschied zu einem SFTP-Ziel, das darauf vertrauen muss, dass der Client nichts löscht. |
| **Dead-Man's-Switch** | Umgekehrter Alarm: gemeldet wird das *Ausbleiben* eines Lebenszeichens, damit ein ausgefallener Wächter nicht als „alles ruhig" erscheint. |
| **RTO / RPO** | Zulässige Wiederanlaufzeit / zulässiger Datenverlust — beide für den Notfall-Standby unbestimmt, weshalb er zurückgestellt ist. |

---

## 9. More Information

- **ADR-241** (Backup-/DR-Baseline) — wird hier im Offsite-Ziel und im
  `implementation_status` geändert; alles Übrige bleibt gültig.
- **ADR-257** (CI-Host-Isolation) — Quelle der Lehre, dass Co-Tenant-Churn geteilte Disks
  füllt; in §4.3 auf **jeden** Mitbewohner verallgemeinert, nicht nur auf CI.
- **ADR-098** — Kernel- und Daemon-Vorgaben der Grundinstallation.
- **ADR-142/143/144** — die heute real laufenden Stack-Backups (`authentik-backup`,
  `outline-backup`); sie bleiben als lokale Kopie bestehen, R1 ersetzt sie nicht.
- **ADR-157** (3-Server-Architektur) — durch sechs reale Hosts überholt; Amendment offen
  ([#1564](https://github.com/achimdehnert/platform/issues/1564)).
- [#1567](https://github.com/achimdehnert/platform/issues/1567) — Backup-Meter meldet grün
  über leerer Sicherung; der Grund, warum das fehlende Stück sechs Wochen unbemerkt blieb.
- [#1282](https://github.com/achimdehnert/platform/issues/1282) — Canary-Issue zum OOM vom
  2026-07-20, 16 Minuten nach Beginn angelegt, 18 Stunden offen.
- `infra/hosts.yaml` — Ist-Zustand aller sechs Hosts mit Messwerten und Vorbehalten.

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-30 | Achim Dehnert | Initial: Status Proposed. Rollenzuschnitt R1–R4 für netcup; Amendment zu ADR-241. Grundlage: SSH-Inventur aller sechs Hosts und I/O-Messung, die die Panel-Angabe „HDD" widerlegt. |
| 2026-07-30 | Achim Dehnert | Phase 1 + Random-IOPS-Messung abgeschlossen; Grundinstallation als `netcup-bootstrap.sh` ins IaC gespiegelt. |
| 2026-07-30 | Achim Dehnert | **Interner adversarialer Review:** R2-Treiber falsifiziert (§1.3) — der Prod-Uptime-Canary existierte und meldete nach 16 Minuten. |
| 2026-07-30 | Achim Dehnert | **Zwei externe Reviews (§11) → Zusammenschnitt.** Entscheidungsinhalt auf **R1 + Negativ-Regel** reduziert; Monitoring, CI-Runner und DR-Standby als „erwogen, zurückgestellt" mit auslösendem Treiber (§3.2). Acht Sachfehler korrigiert (u.a. die nicht propagierte Falsifikation in §3/§6.1, das gegenläufig verwendete Kapazitätsargument, die unbelegte AVV-Ausnahme für Metriken/Logs, fehlende Mengenwerte, Nürnberg als gemeinsame Region). Zehn fachlich stärkere Lösungen übernommen (Allowlist statt Denylist, Disk-Trennung vor **jedem** Mitbewohner, Dead-Man's-Switch in dritter Domäne, `rest-server --append-only` als eigentliches Argument, Cross-Host-Restore). Optionen E und F ergänzt, Option D rehabilitiert. |
| 2026-07-30 | Achim Dehnert | **§1.2 neu — die entscheidende Ursachenklärung.** Recherche auf die Review-Frage „warum lag ADR-241 sechs Wochen?" ergab: es lag **nicht** brach. Der restic-Wrapper, der Meter und die Soll-Liste wurden am Accept-Tag gebaut (#620/#622); es fehlt allein die Repository-Provisionierung — und die war **durch das Ziel blockiert**. Das widerlegt den stärksten externen Einwand (AD-8: „kein Bestandteil war durch das Ziel blockiert") und macht R1 zur Provisionierung statt zum Neubau. Zugleich Anlass für #1567: der Meter meldete sechs Wochen grün über leerer Sicherung. |

---

## 11. External Review Audit (2026-07-30)

Zwei externe Zweitmeinungen von **zwei verschiedenen Fremdanbieter-Modellen**, beide ohne
Repo-, ADR- oder Memory-Zugriff (Briefing redigiert: keine IPs, Hostnamen, Credentials,
Personennamen). **Beide Verdikte: „überarbeiten".** 67 Befunde nach dem Rückfluss-Gate
getaggt: **21 Cluster `[valid]`**, 2 `[missversteht-Kontext]`, 3 `[out-of-scope]`,
11 Zustimmungen. Der Zusammenschnitt in §3 ist die Umsetzung des Hauptbefunds.

### 11.1 Umgesetzt in dieser Fassung

| ID | Befund | Wo eingearbeitet |
|---|---|---|
| A1 | ADR bindet **eine** belegte Entscheidung an **drei** ohne Treiber — un-fertigstellbar; „Wiederholung des Fehlers, den dieses ADR an ADR-241 diagnostiziert" | §3.1 / §3.2 |
| A2 | Alarm-Zustellung vor Monitoring priorisieren | §4.5, Phase 8 |
| A4 | Option D nach der Falsifikation neu bewerten | §2 Option D (rehabilitiert) |
| B1 | Falsifikation aus §1.3 nicht nach §3/§6.1 propagiert | §3, §6 neu geschrieben |
| B2 | Kapazitätsargument gegen Option B und D **gegenläufig** verwendet | §2 Option D |
| B3 | §7 sagt „0c vor Phase 1", §5 führt Phase 1 als erledigt | Phase 3 mit ⚠-Vermerk |
| B4 | §4.5 nannte die falsche Phase als R3-Gate | entfällt mit §3.2 |
| B5 | „Metriken/Logs vom AVV nicht betroffen" war eine Annahme | §7 Zeile 1 |
| B6 | Kein Mengenwert im ADR → „braucht 1 TB" unbelegt | §4.3 |
| B7 | Nürnberg: Anbieter- ≠ Geo-Unabhängigkeit | §6.2, Glossar |
| B8 | ADR-157 nur `related` statt amendiert | §9, Phase 11, #1564 |
| C1 | Disk-Trennung vor **jedem** Mitbewohner, nicht nur CI | §4.3 |
| C2 | CI-Runner ist ein **Rechte**-, nicht nur Speicherproblem | §3.2 Treiber |
| C3 | Dead-Man's-Switch braucht dritte Domäne — der GitHub-Canary ist sie | §4.5, §8.5 |
| C4 | Append-only unterverkauft: SFTP kann es nicht erzwingen, `rest-server` schon | §2 Option A/C, §4.2 |
| C5 | Append-only-Spezifikation zu ungenau | §4.2 (als offen markiert) |
| C6 | Restore auf demselben Host beweist nur Lesbarkeit | §8.3 (Cross-Host) |
| C7 | Negativ-Regel als **Allowlist** statt Denylist | §4.4 |
| C8 | Fünfte Option fehlt: Objektspeicher mit Object Lock | §2 Option E |
| C9 | Frage „sollten es sechs Hosts sein?" fehlt | §2 Option F |
| C10 | Automation-first statt Monitoring-first | §3.2, §4.5 |

### 11.2 Nicht eingeflossen (mit Grund)

| ID | Verdikt | Grund |
|---|---|---|
| E1 | `[missversteht-Kontext]` | „Vorgezogene Grundinstallation greift der Entscheidung vor" — sie ist rollenneutral; jede erwogene Rolle **und** Option D braucht Swap, Container-Laufzeit und Kernel-Parameter |
| E2 | `[missversteht-Kontext]` | Drei isolierte VMs auf dem Host — unter Ein-Personen-Betrieb unverhältnismäßig; der Kern (Isolation für CI) ist als Treiber in §3.2 übernommen |
| E3 | `[out-of-scope]` | Managed-Observability als Regelfall — eigene Entscheidung; der Alarm-Kanal-Teil ist in §4.5 |
| E4 | `[out-of-scope]` | Vollständige RTO/RPO-Festlegung für den Standby — er ist zurückgestellt; der berechtigte Kern (nicht als geplante Fähigkeit zitieren) steht in §3.2 |

### 11.3 Ein externer Befund wurde seinerseits widerlegt

Der stärkste Einwand aus Runde 2 (AD-8) lautete: „Kein Bestandteil von ADR-241 war durch das
Ziel blockiert — wenn die Ursache Owner-Zeit ist, ändert ein Zielwechsel nichts." Die
Recherche, die dieser Einwand ausgelöst hat, ergab das Gegenteil (§1.2): der letzte fehlende
Schritt **war** durch das nie bestellte Ziel blockiert. Der Einwand war falsch — und trotzdem
der wertvollste des ganzen Reviews, weil erst die Frage die Ursachenklärung erzwang.

> **`ai_sparring_by` ist bewusst non-accountable** und erfüllt **nicht** `reviewed_by`: zwei
> externe KI-Reviews ersetzen keine menschliche Owner-Review. Sie haben hier allerdings zwei
> Selbstwidersprüche und eine gegenläufige Argumentation gefunden, die drei interne Durchgänge
> — Autor, `/adr-challenger` und CI — nicht gefunden hatten.
