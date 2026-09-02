---
status: proposed
decision_date: 2026-09-02
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-120, ADR-289, ADR-292]
implementation_status: not_started
last_reviewed: 2026-09-02
staleness_months: 6
---

<!--
  ADR-301 — Basis: docs/templates/adr-template.md v2.1
-->

# ADR-301: Ein eigener Registry-Spiegel auf netcup, damit ein Prod-Deploy nicht an der Erreichbarkeit von ghcr.io hängt

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform / Deploy-Kette                                              |
| **Erstellt**    | 2026-09-02                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-120 (Deploy-Kette), ADR-289 (netcup als Plattformdienst-Host), ADR-292 (Host-Topologie) |

## Repo-Zugehörigkeit

| Repo             | Rolle      | Betroffene Pfade / Komponenten                           |
|------------------|------------|-----------------------------------------------------------|
| `platform`       | Primär     | `scripts/deploy.sh`, `infra/`, dieser ADR                  |
| `shared-ci`      | Sekundär   | `_deploy-unified.yml` — Build-Push-Ziele                    |
| alle App-Hubs    | Betroffen  | `docker-compose.prod.yml` — die Abbild-Referenz             |

---

## Decision Drivers

- **Ein Deploy darf nicht an einem fremden Dienst hängen**, den wir weder messen noch
  reparieren können. Genau das ist am 2026-09-02 eingetreten.
- **Der Bauort ist nicht der Lieferort.** Gebaut wird auf netcup, ausgeliefert wird auf
  prod; das Abbild macht dazwischen einen Umweg über einen Dienst in fremder Hand.
- **Kein zweiter Single Point of Failure.** Ein Spiegel, ohne den nichts mehr deployt,
  tauscht ein fremdes Risiko gegen ein eigenes — das wäre kein Gewinn.
- **Die Abbild-Referenz steht in jedem Hub.** Was hier entschieden wird, fasst rund
  zwanzig `docker-compose.prod.yml` an; eine Rolle rückwärts ist teuer.
- **Right-Sizing:** Anlass ist **ein** gemessener Ausfall, kein Dauerzustand. Der ADR
  muss sagen, wann er sich selbst wieder abschafft.

---

## 1. Context and Problem Statement

Am 2026-09-02 scheiterten auf `prod` vier Produktions-Deploys nacheinander daran, dass
der Host das Abbild nicht von `ghcr.io` holen konnte. Der fünfte Versuch lief
unverändert durch.

### 1.1 Die Messung

Alle Werte am 2026-09-02 auf dem jeweiligen Host erhoben, TLS-Verbindungsaufbau gegen
`https://ghcr.io/v2/`:

| Host | ghcr.io | Kontrollarm | Bewertung |
|---|---|---|---|
| `prod` (Hetzner), 13:35 Uhr | **4 von 10** | `github.com` 10/10 | akuter Ausfall |
| `prod`, 14:10 Uhr | 10 von 12 | `github.com` 12/12 | abklingend |
| `prod`, 14:20 Uhr | 40 von 40 | – | vorbei |
| `prod-b` (Hetzner) | 11 von 12 | `github.com` 12/12 | Restrate |
| `netcup` | 12 von 12 | `github.com` 12/12 | unauffällig |
| `dev-desktop` (Hetzner) | 12 von 12 | – | unauffällig |

Ausgeschlossen wurden im selben Zug: Wegstörung (ICMP zum Ziel 20/20, Ø 4,4 ms), MTU
(`-M do -s 1472` kommt durch), DNS (2–7 ms, genau **ein** A-Record — es ist nicht „eine
von mehreren Adressen ist tot"), Proxy (weder in `daemon.json`, noch Runner-Umgebung,
noch `~/.docker/config.json`), Zugangsdaten (`Login Succeeded` in Lauf 2, danach brach
erst der Abruf) und der Docker-Dienst selbst (zog Docker Hub in 2,2 s).

**Was übrig bleibt:** die Gegenstelle nahm Verbindungen dieses Hosts zeitweise
überwiegend nicht an. Warum, ist von unserer Seite nicht bestimmbar — das bleibt eine
Hypothese und ist der Grund, warum dieser ADR nicht auf eine Reparatur der Ursache
setzt, sondern auf Unabhängigkeit von ihr.

### 1.2 Ist-Zustand der Kette

| Schritt | Wo | Abhängigkeit |
|---|---|---|
| Bauen + Push | netcup (`ci-nonprod`-Läufer) | netcup → ghcr.io |
| Abruf + Start | prod (`prod-server`-Läufer) | **prod → ghcr.io** |
| Abbild-Referenz | `docker-compose.prod.yml` je Hub | fest `ghcr.io/achimdehnert/<app>:${IMAGE_TAG}` |
| Schichten (Layer) | – | `pkg-containers.githubusercontent.com` (Fastly, andere Adressen) |

Bemerkenswert: das Abbild wird auf netcup gebaut und von prod wieder heruntergeladen —
über einen Dienst in fremder Hand, obwohl beide Hosts uns gehören.

### 1.3 Was bereits ohne diesen ADR behoben ist

platform#2704 macht den Deploy gegen kurze Aussetzer widerstandsfähig: Wiederholung mit
wachsendem Abstand an Anmeldung und Abruf, und das Rollback zielt nicht mehr auf einen
Stand aus der `.env`, sondern auf den laufenden Container — es braucht damit gar kein
Netz mehr. **Das deckt den kurzen Aussetzer ab, nicht den langen.** Ein Ausfallfenster
von einer halben Stunde übersteht auch ein vierfacher Versuch nicht.

---

## 2. Considered Options

### Option A — Transparente Umleitung auf einen Pull-Through-Cache

Ein zwischengeschalteter Cache beantwortet Anfragen an `ghcr.io`; die Abbild-Referenzen
bleiben unverändert.

- **Dafür:** kein Hub muss angefasst werden; ein Rückbau ist eine Konfigurationszeile.
- **Dagegen:** Docker Engines eingebauter `registry-mirrors` gilt nur für Docker Hub.
  Für andere Registries braucht es entweder containerd-Konfiguration unterhalb von
  Docker oder einen Proxy, der TLS aufbricht und dem eine eigene CA vertraut werden
  muss. **Ob das auf unserem Stand (Docker 29, containerd-Abbildspeicher) ohne
  Klimmzüge geht, ist ungeprüft** — das ist die offene technische Frage dieses ADR (Refs platform#2706).

### Option B — Eigene Registry als Abruf-Ziel, Referenz umschreiben *(gewählt)*

Der Build schiebt das Abbild wie bisher nach ghcr.io **und** zusätzlich in eine eigene
Registry auf netcup. Die Compose-Dateien der Hubs zeigen auf die eigene Registry.

- **Dafür:** funktioniert mit dem vorhandenen Docker ohne Eingriff in den Dienst und
  ohne fremde CA. Der Weg prod → netcup ist einer, den wir messen und reparieren können.
  netcup ist ohnehin der Bauort, off-provider (andere Fehlerdomäne als beide Hetzner-
  Hosts) und hat 884 GB frei.
- **Dagegen:** rund zwanzig Compose-Dateien ändern sich. Ohne Ausweichpfad wäre netcup
  der neue Engpass — deshalb ist der Ausweichpfad Teil der Entscheidung (§3.2).

### Option C — Direktübertragung ohne Registry

Der Build überträgt das Abbild per `docker save` → `ssh` → `docker load` direkt.

- **Dafür:** keine Registry im Deploy-Pfad, keine neue Komponente.
- **Dagegen:** verwirft die Registry als Ablage; jeder Deploy überträgt das volle Abbild
  ohne Schichten-Wiederverwendung; Rollback auf einen älteren Stand hat keine Quelle mehr.

### Option D — Nichts bauen, nur platform#2704

- **Dafür:** kostet nichts, deckt kurze Aussetzer bereits ab.
- **Dagegen:** beim nächsten längeren Fenster steht die Auslieferung wieder — und zwar
  für writing-hub **und** illustration-hub, die beide auf `prod` liegen.

---

## 3. Decision Outcome

**Gewählt: Option B** — eigene Registry auf netcup als Abruf-Ziel der Produktion,
ghcr.io bleibt Ablage und Ausweichpfad.

### 3.1 Warum nicht A, obwohl es eleganter wäre

A wäre der schönere Weg — keine Referenz ändert sich. Aber A steht und fällt mit einer
Frage, die wir noch nicht beantwortet haben, und ein ADR, dessen Umsetzbarkeit ungeprüft
ist, ist eine Absichtserklärung, keine Entscheidung. **Vorbehalt:** ergibt der Spike in
§5 (G1), dass die transparente Umleitung auf unserem Stand sauber funktioniert, ist A
der bessere Weg und dieser ADR wird vor der Umsetzung entsprechend geändert (Refs platform#2706).

### 3.2 Der Ausweichpfad ist Teil der Entscheidung

Die Registry-Adresse steht **einmal** als Variable, nicht zwanzigmal als Literal. Fällt
netcup aus, schaltet eine Umgebungsvariable die gesamte Flotte auf `ghcr.io` zurück; der
dort liegende Stand ist bitgleich, weil der Build weiterhin beide Ziele bedient. Ohne
diesen Ausweg wird der Spiegel zum Engpass — dann ist Option D die ehrlichere Wahl.

### 3.3 Abgrenzung zu ADR-289

ADR-289 weist netcup Plattformdienste zu und schließt App-Hubs dort ausdrücklich aus.
Eine Registry ist ein Plattformdienst, kein Hub — die Zuweisung ist konform. Der
Plattenbedarf (Schätzung: 20 Hubs × wenige Stände) ist gegen die 884 GB unkritisch,
gehört aber unter die Vorlaufmessung aus Session-Start 0.7.18.

---

## 4. Consequences

**Gut:**
- Ein Deploy hängt nicht mehr an einem Dienst, den wir nicht messen können.
- Das Rollback auf einen älteren Stand hat eine nahe Quelle statt einer fernen.
- Wiederholte Abrufe belasten die Außenleitung nicht mehr.

**Schlecht:**
- Ein Dienst mehr, der laufen, Platz belegen und überwacht werden muss — und der ohne
  eigenen Melder genau die Sorte stiller Ausfall wird, die diese Plattform schon
  mehrfach getroffen hat.
- Die Abbild-Referenz ist ab dann an zwei Orten wahr. Driftet der Push auf ein Ziel
  weg, deployt Prod klaglos einen anderen Stand als gedacht.

**Daraus folgende Pflicht:** der Spiegel bekommt im selben Zug einen
Erreichbarkeits-Melder (Session-Start 0.7.11) **und** einen Gleichstands-Check
Spiegel ↔ ghcr.io. Ein Spiegel ohne Melder ist ein Rückschritt, kein Fortschritt.

---

## 5. Offene Owner-Gates

| # | Gate | Warum es zuerst geklärt gehört |
|---|---|---|
| G1 | **Spike** (platform#2706): funktioniert die transparente Umleitung (Option A) auf Docker 29 mit containerd-Abbildspeicher? | Fällt er positiv aus, ist A besser als B und dieser ADR wird geändert. Kosten: ein halber Tag auf staging, kein Prod-Eingriff. |
| G2 | Registry-Software wählen (schlanke Registry vs. Harbor vs. Zot) | Bestimmt Betriebsaufwand und ob Authentifizierung/Aufräumen mitkommen. |
| G3 | Grundinstallation auf netcup freigeben | Neuer öffentlich erreichbarer Dienst; Zugangsschutz ist zu entscheiden, bevor er steht. |
| G4 | ADR-301 annehmen | Erst danach werden Compose-Dateien angefasst. |

---

## 6. Kill-Gate

Dieser ADR beschreibt eine Vorsorge gegen einen bislang **einmal** gemessenen Ausfall.
Er wird zurückgezogen, wenn bis zum **2026-12-02** gilt:

- kein weiterer Deploy ist an der Registry-Erreichbarkeit gescheitert (messbar an den
  Deploy-Läufen), **und**
- die Wiederholung aus platform#2704 hat jeden aufgetretenen Aussetzer aufgefangen.

Umgekehrt gilt er als bestätigt, sobald ein zweites Ausfallfenster einen Deploy trotz
Wiederholung kostet. **Bis zur Annahme (G4) wird nichts gebaut** — der Zustand nach
platform#2704 ist tragfähig genug, um diese Entscheidung in Ruhe zu treffen.
