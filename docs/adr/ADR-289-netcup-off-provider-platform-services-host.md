---
status: proposed
decision_date: 2026-07-30
deciders: Achim Dehnert
consulted: Claude Code
informed: –
supersedes: []
amends: [ADR-241]
related: [ADR-059, ADR-098, ADR-157, ADR-164, ADR-248, ADR-257]
implementation_status: none
last_reviewed: 2026-07-30
staleness_months: 6
tags: [infrastructure, hosts, backup, disaster-recovery, monitoring, ci, provider-diversity, netcup]
---

# ADR-289: Adopt netcup as Off-Provider Host for Platform Services, Not for App Hubs

## Metadaten

| Attribut          | Wert                                                                  |
|-------------------|-----------------------------------------------------------------------|
| **Status**        | Proposed                                                              |
| **Scope**         | platform                                                              |
| **Erstellt**      | 2026-07-30                                                            |
| **Autor**         | Achim Dehnert                                                         |
| **Reviewer**      | –                                                                     |
| **Supersedes**    | –                                                                     |
| **Superseded by** | –                                                                     |
| **Amends**        | ADR-241 (Backup- & Disaster-Recovery-Baseline) — Offsite-Ziel          |
| **Relates to**    | ADR-059 (Drift-Detector), ADR-098 (Infrastructure Tuning), ADR-157 (Staging/Prod-Split), ADR-164 (Port-Strategie), ADR-248 (COMPOSE_PROJECT_NAME), ADR-257 (CI-Host-Isolation) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                        |
|----------------|------------|-------------------------------------------------------|
| `platform`     | Primär     | `infra/hosts.yaml`, `docs/adr/ADR-241`, `infra/scripts/hosts_audit.py` |
| `risk-hub`     | Sekundär   | `scripts/backup.sh` — erster Konsument von R1 (MinIO-Volume) |
| `mcp-hub`      | Sekundär   | `mcp_hub_pgdata` (Orchestrator-pgvector) — zweiter Konsument von R1 |
| `dev-hub`      | Referenz   | TechDocs-Sync der Host-Topologie                      |

---

## Decision Drivers

- **Es existiert kein Offsite-Backup.** ADR-241 ist seit 2026-06-21 `accepted`, aber
  `implementation_status: none`. Konkret ungesichert: das MinIO-Volume von risk-hub
  (Kundendokumente) und `mcp_hub_pgdata` (Orchestrator-pgvector, gar kein Backup-Skript).
- **Das beschlossene Offsite-Ziel liegt beim selben Anbieter.** ADR-241 wählte eine Hetzner
  Storage Box BX11. Alle fünf Bestandshosts sind Hetzner — ein Ziel im selben Konto und
  beim selben Anbieter isoliert weder Konto-, Abrechnungs- noch anbieterweite Störungen.
- **`prod` hat kein Monitoring.** Das einzige Stack-Monitoring der Plattform läuft auf
  `odoo` (46.225.127.211) in einem separaten Hetzner-Konto. Deshalb blieb der OOM-Ausfall
  am 2026-07-20 **16 Stunden** unbemerkt. Ein Beobachter innerhalb der beobachteten
  Fehlerdomäne ist ohnehin kein Monitoring.
- **Der CI-Host sitzt im Swap-Anschlag.** `staging` (88.99.38.75) trägt laut ADR-257 den
  `ci-nonprod`-Runner und gleichzeitig 30 Sitzungen, Windsurf-Remote und
  Desktop-Streaming: gemessen 2026-07-30 Swap **8,0 / 8,0 GB = 100 %**, 2,3 GB RAM frei.
- **Die Maschine ist bereits bezahlt und ungenutzt.** netcup läuft seit 113 Tagen mit
  Load 0,00 und 1 GiB Monatstraffic. Die Rollen kosten 0 € Mehrausgaben — dasselbe Muster,
  das beim `lastwar-bot`-Rebuild zu `prod-b` geführt hat.
- **Kein Kapazitätsmangel im Bestand.** `prod-b` nutzt 7 %, `staging-dedicated` 23 % ihres
  RAM; zusammen liegen ~26 GB brach. Wer netcup mit „mehr Kapazität" begründet, löst ein
  Verteilungsproblem durch Zukauf.

---

## 1. Context and Problem Statement

Zum Bestand ist eine sechste Maschine hinzugekommen: ein netcup-Server in Nürnberg
(152.53.136.219), 12 vCPU / 31 GiB RAM / 1007 GB Disk, seit 113 Tagen bezahlt und faktisch
unbenutzt. Die Frage ist nicht, *ob* er integriert wird, sondern **als was** — und die
falsche Antwort ist teuer: ein sechster Host mit eigenen Hub-Stacks vergrößert die
Betriebslast, ohne einen belegten Mangel zu beheben.

Gleichzeitig hat die Plattform zwei belegte Lücken, die **kein** Bestandshost schließen
kann, weil sie nicht an Kapazität hängen, sondern an **Unabhängigkeit**: ein Backup-Ziel
außerhalb der Hetzner-Fehlerdomäne und ein Beobachter außerhalb der beobachteten Domäne.

### 1.1 Ist-Zustand

Alle Werte per SSH-Probe am 2026-07-30 erhoben und in `infra/hosts.yaml` festgehalten:

| Host | Anbieter / Ort | CPU | RAM belegt | Swap | Disk | Container |
|---|---|---|---|---|---|---|
| `prod` | Hetzner nbg1 (DE) | 12 | 10,7 / 23,5 GB (46 %) | 1,8 / 4,0 GB | `/` 65 %, Vol 32 % | 46 |
| `prod-b` | Hetzner hel1 (FI) | 8 | 1,1 / 15,6 GB (**7 %**) | – | 2 % | 4 |
| `staging` | Hetzner fsn1 (DE) | 16 | 17 / 30 GB | **8,0 / 8,0 GB (100 %)** | 28 % | 43 |
| `staging-dedicated` | Hetzner fsn1 (DE) | 8 | 3,7 / 15,6 GB (**23 %**) | – | 3 % | 12 |
| `odoo` | Hetzner, eigenes Konto | 4 | 1,5 / 7,7 GB (19 %) | – | 21 % | 10 |
| `netcup` | **netcup, Nürnberg (DE)** | 12 | 0,55 / 31 GB (**2 %**) | **0 (keiner)** | 1 % | **0** |

Vier Hosts liegen im gemeinsamen Hetzner-Cloud-Projekt, `odoo` in einem separaten
Hetzner-Konto. **netcup ist der erste und einzige Host außerhalb der Hetzner-Domäne** und
hat mit 1 TB die größte Disk im Bestand — dreifach jede andere.

### 1.2 Warum jetzt

Drei Dinge treffen zusammen. Erstens ist ADR-241 seit sechs Wochen beschlossen und nicht
umgesetzt; das dringlichste Einzelstück (risk-hub MinIO) ist weiter ungesichert. Zweitens
liegt seit dem 2026-07-20 ein konkreter Schadensfall vor, dessen Ursache nicht der OOM
selbst war, sondern dass ihn 16 Stunden niemand bemerkte. Drittens ist die Maschine da,
bezahlt und leer — die Alternative zur Nutzung ist nicht Ersparnis, sondern Leerlauf.

Hinzu kommt eine Falsifikation, die den Entscheidungsraum erst geöffnet hat: die
Panel-Angabe „Startlaufwerk HDD" (siehe §2, Option D und §4.1) hätte netcup auf reine
Archivrollen beschränkt. Die Messung widerlegt sie.

---

## 2. Considered Options

### Option A: netcup als Off-Provider-Host für Plattformdienste, keine App-Hubs ✅

Vier Rollen in dieser Reihenfolge: **R1** Off-Provider-Backup- und DR-Ziel, **R2**
unabhängiger Monitoring-/Alerting-Host, **R3** CI-/Build-Runner, **R4** DR-Standby als
Ausbaustufe. App-Hubs bleiben ausdrücklich außen vor.

**Pros:**
- Schließt beide Lücken, die kein Bestandshost schließen kann (Anbieter- und
  Domänen-Unabhängigkeit) — nicht durch Kapazität, sondern durch Lage.
- 0 € Mehrkosten; ersetzt zugleich die noch nicht bestellte Storage Box (~5 €/Monat).
- netcup ist ein **vollwertiger Server**, keine Ablage: `restic check --read-data`,
  serverseitige Retention und lokale Restore-Tests sind möglich. Damit wird die
  Feuerübung G3 aus ADR-241 überhaupt erst praktikabel.
- Verhindert die naheliegende Fehlnutzung (Hubs dorthin schieben) durch eine explizite
  Negativ-Regel, die per `docker ps` prüfbar ist (§8).

**Cons:**
- Konzentriert Backup, Monitoring und CI auf **einem** Host — Ausfall trifft drei Funktionen
  gleichzeitig (Mitigation §7).
- Sechster Host = zusätzliche Betriebslast (Patching, Firewall, Runner-Registrierung).
- Setzt einen AVV mit netcup voraus, bevor R1 Daten mit Personenbezug aufnimmt.

### Option B: netcup als sechster App-Hub-Host (Long Tail dorthin)

**Pros:**
- Nutzt 31 GB RAM sofort für sichtbare Produktlast.
- Standort Nürnberg/DE — anders als `prod-b` (Helsinki) auch für DE-Anforderungen offen.

**Cons:**
- Behebt keinen belegten Mangel: `prod-b` steht zu 93 %, `staging-dedicated` zu 77 % leer.
  → **Abgelehnt weil:** Der Bestand hat ein Verteilungs-, kein Kapazitätsproblem. Der
  Zukauf von Kapazität, während 26 GB brachliegen, verschiebt das Problem und
  vergrößert es: sieben Hub-tragende Engines statt fünf.
- Ließe beide Lücken (Offsite-Backup, unabhängiges Monitoring) offen — und **verbraucht**
  den einzigen Host, der sie schließen könnte.

### Option C: netcup kündigen, bei der Hetzner Storage Box BX11 bleiben

**Pros:**
- Keine neue Anbieterbeziehung, kein AVV, kein sechster Host im Betrieb.
- ADR-241 bleibt unverändert.

**Cons:**
- Das Offsite-Ziel bliebe beim selben Anbieter → **Abgelehnt weil:** Genau die
  Fehlerklasse, gegen die ein Offsite-Backup schützen soll (Konto-, Abrechnungs-,
  anbieterweite Störung), bliebe ungedeckt. Eine Storage Box ist ein zweites
  Rechenzentrum, keine zweite Fehlerdomäne.
- Eine Storage Box kann keine Restore-Tests fahren — G3 bliebe Theorie.
- Das Monitoring-Problem bliebe vollständig offen.

### Option D: netcup nur als reines Backup-Ziel (nur R1)

Die konservative Variante — netcup als Blob-Ablage, Monitoring bleibt auf `odoo`, CI bleibt
auf `staging`.

**Pros:**
- Minimaler Betriebsaufwand, kleinste Angriffsfläche.
- Hätte auch unter der ursprünglichen HDD-Annahme funktioniert.

**Cons:**
- Verschenkt 12 Kerne und 30 GB RAM für eine Aufgabe, die 60 GB Disk und kaum CPU braucht.
- Lässt das Monitoring in der falschen Domäne (`odoo`, fremdes Konto) → **Abgelehnt weil:**
  Der belegte Schadensfall vom 2026-07-20 (16 h unbemerkt) bleibt ungedeckt, obwohl der
  Host dafür bereitsteht. Die HDD-Annahme, die diese Beschränkung getragen hätte, ist
  widerlegt (§4.1).

---

## 3. Decision Outcome

**Gewählte Option: Option A — Off-Provider-Host für Plattformdienste, keine App-Hubs.**

netcups Wert ist seine **Lage**, nicht seine Größe: er ist der einzige Host außerhalb der
Hetzner-Fehlerdomäne und hat die größte Disk im Bestand. Genau das brauchen die zwei
offenen Lücken (Offsite-Backup nach ADR-241, unabhängiges Monitoring), und genau das kann
kein Bestandshost liefern — unabhängig davon, wie viel RAM dort frei ist. Option B würde
diesen Vorteil für eine Aufgabe verbrauchen, die `prod-b` und `staging-dedicated` bereits
erledigen könnten; Option C ließe die Anbieter-Monokultur bestehen; Option D verschenkt
Kapazität für eine Beschränkung, deren technische Begründung widerlegt ist.

Die Reihenfolge R1 → R2 → R3 → R4 folgt dem belegten Schmerz, nicht der technischen
Attraktivität: R1 deckt ungesicherte Kundendokumente, R2 einen eingetretenen 16-h-Ausfall,
R3 einen Host im Swap-Anschlag, R4 ist Ausbau ohne akuten Anlass.

**Als Amendment zu ADR-241** wird das dort beschlossene Offsite-Ziel „Hetzner Storage Box
BX11" durch netcup ersetzt. Die übrigen Entscheidungen von ADR-241 (Offsite by
construction, restic, Retention, Feuerübung G3) bleiben unverändert gültig — es wechselt
nur das Ziel, und zwar zu einem, das die Absicht von ADR-241 besser erfüllt als das
ursprünglich gewählte.

---

## 4. Implementation Details

### 4.1 Grundlage: I/O-Messung (widerlegt die Panel-Angabe)

Das netcup-Panel führt das Startlaufwerk als **„HDD"**; `lsblk` meldet `ROTA=1`. Beides
hätte netcup auf Archivrollen beschränkt. Messung am 2026-07-30 gegen
`staging-dedicated` als NVMe-Referenz — bewusst nicht gegen `prod`, um dort keine I/O-Last
zu erzeugen:

| Metrik | netcup | staging-dedicated (NVMe) | Verhältnis |
|---|---|---|---|
| Sequenziell schreiben, 2 GB, `oflag=direct` | 633 MB/s | 879 MB/s | 0,72 × |
| fsync-Latenz, 1000 × 4 K, `oflag=dsync` | 2,9 MB/s ≈ **1,44 ms/Commit** | 3,3 MB/s ≈ 1,24 ms | **0,88 ×** |
| Sequenziell lesen, cache-frei | 653 MB/s | 1,7 GB/s | 0,38 × |

Eine 7200-RPM-Platte liefert 150–200 MB/s. netcup führt seinen großen Speicher-Tier nur
nominell als „HDD"; `ROTA=1` ist virtio-Voreinstellung und trägt keine Aussage. Maßgeblich
ist die **fsync-Commit-Latenz** — die für Postgres bestimmende Größe — und die liegt bei
88 % der NVMe-Referenz. Nur beim sequenziellen Lesen fällt netcup ab (0,38 ×); das betrifft
Image-Pulls und Cache-Aufwärmung, nicht den Datenbankbetrieb (Gegenmittel: §4.4).

### 4.1.1 Nachmessung Random-IOPS (Phase 5, 2026-07-30 — bestanden)

Die erste Fassung dieses ADR führte Random-IOPS als offen und machte die Nachmessung zur
Vorbedingung von R3. Sie ist erfolgt (`fio` 3.39, `--direct=1 --bs=4k --iodepth=32
--ioengine=libaio`, zeitbasiert):

| Profil | Ergebnis |
|---|---|
| `randwrite` 4 K, 30 s | **43,3k IOPS**, 169 MiB/s, Latenz Ø 730 µs, p99 **5,5 ms** |
| `randread` 4 K, 45 s | **94,0k IOPS** |

Eine rotierende Platte liefert 100–200 IOPS — der Abstand ist Faktor 200 bis 400. Damit ist
die Speicherklasse endgültig geklärt: **SSD/NVMe-gestützt**, nicht rotierend. Für
Docker-Builds, Prometheus-Blöcke und restic-Läufe ist das mit Reserve ausreichend.

Die p99-Latenz von 5,5 ms bei Warteschlangentiefe 32 (gegen Ø 730 µs) zeigt die erwartete
Streuung geteilten Speichers — bemerkbar unter Last, aber weit von einer Blockade entfernt.

**Was damit NICHT belegt ist:** dass ein echter Docker-Build hier genauso schnell läuft.
Die Messung deckt die *Speicher*-Vorbedingung, nicht die Wall-Clock eines Builds, in die
auch die schwächere Leseleistung (0,38 × bei sequenziellem Lesen, §4.1) über Image-Pulls
eingeht. Der Build-Vergleich ist deshalb als eigene Phase 5b geführt und bleibt die
Bedingung für R3 — die IOPS-Zahl allein reicht dafür ausdrücklich nicht.

### 4.2 Grundinstallation (Vorbedingung aller Rollen)

Auf netcup fehlt heute alles: kein Docker, kein Swap, Firewall im Panel „Aktiv (0)" —
eingeschaltet, aber **ohne Regel**. Nach dem Muster von `prod-b`:

- Docker + Compose, `daemon.json` nach ADR-098 §1 (live-restore, log-limits, BuildKit GC)
- `sysctl` nach ADR-098 §2 (`vm.overcommit_memory=1`, `net.core.somaxconn=65535`)
- Swap-Bereich anlegen (die anderen Hosts fahren 4–8 GB; hier 8 GB bei 31 GB RAM)
- Firewall-Regeln nach dem Muster der Hetzner-Policy `prod-b-web`: SSH + die für R2
  benötigten Ports, kein offenes 80/443 solange keine Web-Rolle beschlossen ist
- `COMPOSE_PROJECT_NAME` pro Stack pinnen (ADR-248) — auch hier, obwohl vorerst nur
  Plattformdienste laufen

### 4.3 R1 — Off-Provider-Backup und DR-Ziel

restic-Repository auf netcup, gespeist von den Hetzner-Hosts. Reihenfolge nach
Dringlichkeit aus ADR-241 §Kontext:

1. **risk-hub inkl. MinIO-Volume** (Kundendokumente — heute vollständig ungesichert, und
   der vorhandene `backup.sh` zeigt laut ADR-241 auf einen falschen Pfad)
2. **`mcp_hub_pgdata`** (Orchestrator-pgvector — kein Backup-Skript vorhanden)
3. `pg_dumpall` aller übrigen Hubs
4. **Restore-Feuerübung (G3 aus ADR-241)** — auf netcup selbst durchführbar, ohne die
   Daten erst zurückzuziehen

Retention und Verschlüsselung wie in ADR-241 festgelegt. Der `restic`-Zugang wird als
Append-only-Schlüssel eingerichtet, damit ein kompromittierter Quell-Host die Sicherungen
nicht löschen kann.

### 4.4 R2 — unabhängiger Monitoring-Host

Prometheus + Loki + Grafana + Alertmanager auf netcup; `node_exporter` und `cadvisor` auf
allen fünf Hetzner-Hosts. Der bestehende Stack auf `odoo` ist die Vorlage — er wird
gespiegelt, nicht neu erfunden, und verlässt damit das fremde Hetzner-Konto, in dem er
organisatorisch fehl am Platz liegt. Zeitreihen und Logs sind der Grund, warum diese Rolle
den 1-TB-Host braucht und nicht auf einen der 301-GB-Hosts gehört.

Pflicht-Alarme zum Start, abgeleitet aus den Vorfällen: Host-RAM/Swap-Sättigung (der
20.07.-OOM), Container-Restart-Schleifen (`onboarding_hub_beat` mit ~23k Neustarts,
`aifw_service` auf `odoo`), Disk-Füllstand, und ein **Heartbeat/Dead-Man's-Switch**, der
den Ausfall des Monitorings selbst meldet (§7).

### 4.5 R3 — CI-/Build-Runner

Ein `ci-nonprod`-Runner nach dem Muster aus ADR-257, damit `staging` (88.99.38.75)
entlastet wird. Wegen der schwächeren Leseleistung (§4.1) gehört ein lokaler
Registry-Pull-Through-Cache dazu. Vorbedingung ist die Nachmessung in §5 — nicht die
Annahme, dass 88 % fsync auch 88 % Build-Wall-Clock bedeuten.

Host-gebundene Deploys bleiben unverändert auf `prod-server` (ADR-156/ADR-257).

### 4.6 Negativ-Regel: keine App-Hubs

Auf netcup laufen **keine** App-Hub-Stacks. Wandernde Hubs gehen nach `prod-b` oder
`staging-dedicated` (7 % bzw. 23 % RAM-Belegung). Die Regel ist keine Stilfrage, sondern
der Kern von Option A: würde netcup Hubs tragen, wäre er ein sechster Produktionshost und
kein unabhängiger Beobachter/Sicherungsort mehr. Prüfmechanismus in §8.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform` | 0 — Host in SoT | ✅ Abgeschlossen | 2026-07-30 | `infra/hosts.yaml`, PR #1560 (gemergt) |
| — | 0b — AVV mit netcup | ⬜ Ausstehend | – | **Vorbedingung für R1**; Owner, netcup-Panel |
| — | 0c — Kosten/Laufzeit offenlegen | ⬜ Ausstehend | – | fehlt für den Vergleich gegen BX11 |
| `platform` | 1 — Grundinstallation | ✅ Abgeschlossen | 2026-07-30 | Owner-Freigabe erteilt; `infra/host-maintenance/netcup-bootstrap.sh` gelaufen — Swap 8 G, Docker 29.6.2, Compose 5.3.1, fio 3.39, sysctl nach ADR-098. Firewall bewusst ausgenommen (§4.2) |
| `risk-hub` | 2 — R1 inkl. MinIO | ⬜ Ausstehend | – | dringlichster Einzelfix aus ADR-241 |
| `mcp-hub` | 2 — R1 pgvector | ⬜ Ausstehend | – | kein Backup-Skript vorhanden |
| `platform` | 3 — R1 Feuerübung G3 | ⬜ Ausstehend | – | erst danach gilt R1 als belegt |
| `platform` | 4 — R2 Monitoring | ⬜ Ausstehend | – | §4.4 inkl. Dead-Man's-Switch |
| — | 5 — `fio randwrite` nachmessen | ✅ Abgeschlossen | 2026-07-30 | **bestanden**, Werte in §4.1.1. Deckt die I/O-Vorbedingung; der Build-Wall-Clock-Vergleich bleibt offen (Phase 5b) |
| — | 5b — Build-Wall-Clock vergleichen | ⬜ Ausstehend | – | derselbe Docker-Build auf netcup und `staging`; das ist der eigentliche R3-Nachweis, nicht die IOPS-Zahl |
| `platform` | 6 — R3 Runner | ⬜ Ausstehend | – | nur wenn Phase 5b bestanden |
| — | 7 — R4 DR-Standby | ➖ Out of Scope | – | eigene Entscheidung nach Phase 3 |
| `platform` | 8 — ADR-241 Statuszeile | ⬜ Ausstehend | – | **aufgeschobener Statuswechsel**: ADR-241 erhält `amended_by: ADR-289` erst, wenn dieses ADR `accepted` ist |

---

## 6. Consequences

### 6.1 Good

- Erstmals ein Backup-Ziel außerhalb der Hetzner-Fehlerdomäne — die Absicht von ADR-241
  („Offsite by construction") wird tatsächlich erfüllt, nicht nur formal.
- Die dringlichste Datenlücke (risk-hub MinIO, Kundendokumente) bekommt einen Zielort.
- Ein Beobachter außerhalb der beobachteten Domäne; die Wiederholung eines 16-stündigen
  unbemerkten Ausfalls wird unwahrscheinlich.
- Restore-Tests werden praktikabel, weil das Ziel ein Server ist und keine Ablage.
- 0 € Mehrkosten, und die geplanten ~5 €/Monat für BX11 entfallen.
- Entlastung von `staging` (Swap 100 %) ohne Beschaffung.
- Die Negativ-Regel §4.6 hält den Druck dort, wo er hingehört: auf die Verteilung der
  brachliegenden 26 GB in `prod-b`/`staging-dedicated`.

### 6.2 Bad

- **Funktionskonzentration:** Backup, Monitoring und CI auf einem Host (Mitigation §7).
- Neue Anbieterbeziehung mit eigener Vertrags-, AVV- und Patch-Verantwortung.
- Sechster Host im Betrieb — Patching, Firewall, Runner-Registrierung, Monitoring des
  Monitorings.
- Abhängigkeit von einer Maschine, deren Kosten und Laufzeit derzeit **nicht bekannt** sind.
- Die Leseleistung (0,38 × NVMe) macht Image-Pulls langsamer; ohne Pull-Through-Cache
  wäre R3 spürbar träger.

### 6.3 Nicht in Scope

- **App-Hubs auf netcup** — ausdrücklich ausgeschlossen (§4.6).
- **Gov-/Sozialdaten-Workloads** (meiki-lra, frist-hub). Nürnberg ist Deutschland, anders
  als `prod-b` in Helsinki — aber ein neuer Auftragsverarbeiter ist eine eigene
  Entscheidung und keine Standortfrage. Dieses ADR entscheidet sie nicht.
- **Die Konsolidierung der Staging-Doppelung** (risk-hub- und dev-hub-Staging existieren auf
  `staging` und `staging-dedicated`) — bekannt, offen, eigener Vorgang.
- **Die Ursache der 93 GB auf `prod:/`** — nicht verifiziert, kein Notstand (51 GB frei).

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| netcup fällt aus → Backup-Ziel **und** Monitoring gleichzeitig weg | Niedrig | Hoch | Die deploy-getriggerten Pre-Deploy-Backups auf `prod` (ADR-241) bleiben als zweite, lokale Kopie bestehen — R1 ersetzt sie nicht. Monitoring-Ausfall wird durch Heartbeat/Dead-Man's-Switch (§4.4) sichtbar, nicht durch Stille. |
| „Noisy neighbour" auf geteiltem Speicher | Mittel | Niedrig | **Teilweise entschärft** (§4.1.1, 2026-07-30): 43,3k Write-/94,0k Read-IOPS gemessen, p99 5,5 ms — Streuung sichtbar, Reserve groß. Random-IOPS sind damit **nicht** mehr unbekannt. Offen bleibt das Verhalten über Wochen; R1/R2 sind gegen I/O-Schwankungen ohnehin tolerant. |
| AVV fehlt, Backups mit Personenbezug landen trotzdem dort | Niedrig | **Kritisch** | Phase 0b ist Vorbedingung von Phase 2, nicht Parallelarbeit. R2 (Metriken/Logs) und R3 (Builds) sind davon nicht betroffen und können vorher laufen. |
| Kompromittierter Quell-Host löscht die Sicherungen | Niedrig | Hoch | `restic`-Zugang als Append-only-Schlüssel (§4.3). |
| Schleichende Umnutzung zum sechsten Hub-Host | **Mittel** | Mittel | Negativ-Regel §4.6 mit maschineller Prüfung (§8.2) — nicht nur als Absichtserklärung. |
| Kosten/Laufzeit ungünstiger als die 5 €/Monat für BX11 | Niedrig | Niedrig | Phase 0c klärt das vor Phase 1; fällt der Vergleich negativ aus, bleibt Option C erreichbar, weil bis dahin nichts Irreversibles geschehen ist. |

---

## 8. Confirmation

1. **Host-SoT-Gate** — `python3 infra/scripts/hosts_audit.py` läuft im CI-Gate
   „hosts.yaml Schema + Frische + Runner-Label-Pins". Der `netcup`-Eintrag trägt heute
   ausdrücklich „NOCH KEINE ROLLE ZUGEWIESEN"; mit Annahme dieses ADR muss dort die
   beschlossene Rolle stehen. Prüfbar: Diff gegen `infra/hosts.yaml`.
2. **Negativ-Regel maschinell** — `docker ps` auf netcup enthält **keinen** Container, dessen
   `COMPOSE_PROJECT_NAME` (ADR-248) einem App-Hub aus `infra/ports.yaml` entspricht.
   Verletzung ist ein einzeiliger Check, kein Ermessen.
3. **R1 ist erst belegt, wenn ein Restore lief** — `restic snapshots` auf netcup zeigt
   Sicherungen für risk-hub (inkl. MinIO) und `mcp_hub_pgdata`, **und** die Feuerübung G3
   aus ADR-241 ist einmal bestanden. Ein vorhandenes Repository ohne bestandenen Restore
   gilt nicht als Erfüllung (Lehre aus ADR-241: `accepted` ≠ umgesetzt).
4. **R2 ist erst belegt, wenn ein Alarm ausgelöst hat** — ein bewusst herbeigeführter
   Testfall (Container-Stop auf einem Nicht-Prod-Host) erzeugt binnen 5 Minuten eine
   Benachrichtigung. Ein installierter Prometheus ohne zugestellten Alarm gilt nicht.
5. **R3 nur nach Messung** — Phase 5 (`fio randwrite`) ist **erfüllt** (§4.1.1, 2026-07-30).
   Bevor ein Runner registriert wird, muss zusätzlich Phase 5b vorliegen: derselbe
   Docker-Build auf netcup und auf `staging`, verglichen nach Wall-Clock. Eine bestandene
   IOPS-Messung allein gilt ausdrücklich **nicht** als Nachweis der Build-Eignung.
6. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft —
   Staleness-Schwelle: **6 Monate** (kurz gewählt, weil die Rollen gestaffelt umgesetzt
   werden und ein halbjährlicher Abgleich Phasen-Stillstand sichtbar macht).

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — festgehaltene Architekturentscheidung samt Begründung und verworfenen Alternativen. |
| **AVV** | Auftragsverarbeitungsvertrag — nach DSGVO nötig, wenn ein Dienstleister personenbezogene Daten für uns verarbeitet oder speichert. |
| **DR** | Disaster Recovery — Wiederanlauf nach einem Totalausfall, im Unterschied zum reinen Vorhandensein einer Sicherung. |
| **Fehlerdomäne** | Bereich, der gemeinsam ausfällt. Zwei Rechenzentren eines Anbieters teilen Konto und Abrechnung und sind daher **eine** Domäne. |
| **fsync** | Betriebssystem-Aufruf, der Daten garantiert auf den Datenträger schreibt. Seine Dauer bestimmt, wie schnell eine Datenbank Transaktionen bestätigen kann. |
| **IOPS** | Input/Output Operations Per Second — Anzahl einzelner Speicherzugriffe pro Sekunde; bei kleinen, verstreuten Zugriffen aussagekräftiger als die Datenrate. |
| **restic** | Sicherungswerkzeug mit Verschlüsselung, Deduplizierung und Append-only-Betrieb. |
| **Append-only-Schlüssel** | Zugang, der nur hinzufügen, nicht löschen darf — verhindert, dass ein übernommener Quell-Server die Sicherungen mitvernichtet. |
| **Dead-Man's-Switch** | Umgekehrter Alarm: es wird das *Ausbleiben* eines regelmäßigen Lebenszeichens gemeldet, damit ein ausgefallenes Monitoring nicht als „alles ruhig" erscheint. |
| **Noisy Neighbour** | Leistungseinbruch, weil ein anderer Kunde auf derselben physischen Maschine viel Last erzeugt. |
| **Pull-Through-Cache** | Lokaler Zwischenspeicher für Container-Images; jedes Image wird nur beim ersten Abruf aus dem Internet geladen. |

---

## 9. More Information

- ADR-241: Platform-weite Backup- & Disaster-Recovery-Baseline — **wird durch dieses ADR
  im Punkt Offsite-Ziel geändert** (Storage Box BX11 → netcup); alle übrigen Festlegungen
  bleiben gültig.
- ADR-257: CI-Host-Isolation / Non-Prod-Runner — Grundlage für R3; `staging` ist der heute
  belastete Runner-Host.
- ADR-098: Production Infrastructure Tuning Standard — `daemon.json`/`sysctl`-Vorgaben für
  die Grundinstallation (§4.2).
- ADR-248: `COMPOSE_PROJECT_NAME` pro Hub — Grundlage der maschinellen Negativ-Prüfung (§8.2).
- ADR-157 / ADR-164: Host- und Port-Governance — netcup führt keine App-Ports und ist
  deshalb kein Fall für `infra/ports.yaml`.
- `infra/hosts.yaml` — Ist-Zustand aller sechs Hosts, Messwerte und Vorbehalte
  (platform PR #1560, gemergt 2026-07-30).
- Vorfall 2026-07-20: Host-OOM auf `prod`, 16 h unbemerkt — platform#1303, Freeze #1314.

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-30 | Achim Dehnert | Initial: Status Proposed. Rollenzuschnitt R1–R4 für netcup; Amendment zu ADR-241 (Offsite-Ziel). Grundlage: SSH-Inventur aller sechs Hosts und I/O-Messung, die die Panel-Angabe „HDD" widerlegt. |
| 2026-07-30 | Achim Dehnert | **Phase 1 + Phase 5 abgeschlossen.** Grundinstallation gelaufen (Owner-Freigabe erteilt): Swap 8 G, Docker 29.6.2, Compose 5.3.1, fio 3.39, sysctl nach ADR-098 — als idempotentes Skript `infra/host-maintenance/netcup-bootstrap.sh` ins IaC gespiegelt, nicht per Handarbeit. Random-IOPS nachgemessen (§4.1.1): 43,3k write / 94,0k read, p99 5,5 ms → SSD-Klasse bestätigt, Risiko-Zeile „Random-IOPS unbekannt" entschärft. **Neue Phase 5b** eingezogen: der Build-Wall-Clock-Vergleich ist der eigentliche R3-Nachweis; die IOPS-Messung deckt ihn nicht. Status bleibt `proposed` — die Freigabe betraf die rollenneutrale Grundinstallation, nicht die Annahme der Rollen R1–R4. |
