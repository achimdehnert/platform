---
concept_id: KONZ-platform-055
title: Betriebseinheit vs. Repo-Identität — den Flotten-Monitor aus dem Produktprojekt lösen
pipeline_status: pilot
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: org-weiter ADR
review_by: 2026-10-31
kill_criteria: "Am 2026-11-30 gilt: (1) grafana.iil.pet antwortet unter einem Compose-Projekt, dessen Name kein Produktprojekt nennt, und die Prometheus-Historie reicht nachweislich über den Umzugstag zurück; (2) ein Deploy des ttz/odoo-Projekts lässt alle Monitor-Container unberührt (gemessen an unveränderter Container-ID); (3) aifw_service existiert nur noch einmal in der Flotte. Verfehlt (1) oder (2) ihr Ziel, wird der Umzug zurückgerollt und der Stack bleibt bewusst in odoo-hub — mit dokumentierter Kopplung statt halbem Schnitt."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "~/github/odoo-hub/docker-compose.prod.yml", commit_or_pr: "lokal 2026-08-31", opened_in_session: true}
  - {claim_id: C2, source_path: "odoo-Host 46.225.127.211 · docker ps", commit_or_pr: "Messung 2026-08-31", opened_in_session: true}
  - {claim_id: C3, source_path: "odoo-Host · docker inspect aifw_service", commit_or_pr: "Messung 2026-08-31", opened_in_session: true}
  - {claim_id: C4, source_path: "infra/ports.yaml:126-131", commit_or_pr: "lokal 2026-08-31", opened_in_session: true}
  - {claim_id: C5, source_path: "diff services/aifw_service odoo-hub↔ttz-hub + git log", commit_or_pr: "#2546", opened_in_session: true}
  - {claim_id: C6, source_path: "docs/konzepte/KONZ-platform-054-systembild-und-vorbeugende-wartung.md:107,223", commit_or_pr: "lokal 2026-08-31", opened_in_session: true}
  - {claim_id: C7, source_path: "docs/adr/ADR-115-grafana-agent-controlling-dashboard.md", commit_or_pr: "accepted 2026-03-08", opened_in_session: true}
  - {claim_id: C8, source_path: "~/github/mcp-hub/docker-compose.llm-mcp.yml:55", commit_or_pr: "lokal 2026-08-31", opened_in_session: true}
  - {claim_id: C9, source_path: "~/github/ttz-hub/docker-compose.prod.yml:46", commit_or_pr: "lokal 2026-08-31", opened_in_session: true}
  - {claim_id: C10, source_path: "~/github/infra-deploy/ (Verzeichnislisting)", commit_or_pr: "lokal 2026-08-31", opened_in_session: true}
  - {claim_id: C11, source_path: "odoo_prometheus /api/v1/targets (7 aktive, alle up)", commit_or_pr: "Messung 2026-08-31", opened_in_session: true}
  - {claim_id: C12, source_path: "~/github/odoo-hub/grafana/provisioning/ + prometheus/prometheus.yml", commit_or_pr: "lokal 2026-08-31", opened_in_session: true}
created: 2026-08-31
---

# KONZ-platform-055 — Betriebseinheit vs. Repo-Identität

**Tier T3.** Nicht selbst gewählt: die Auto-Eskalation greift vierfach — Cross-Repo
(odoo-hub, ttz-hub, platform, potenziell ein neues Repo), SSoT-Verschiebung (wo lebt
Observability), neue Boundary, Security-Perimeter (Cloudflare-Tunnel-Route für
`grafana.iil.pet`). Jeder einzelne Trigger würde T2 erzwingen.

## 1 Executive Summary

Der Flotten-Monitor der Plattform — Prometheus, Grafana, Loki, Promtail, cadvisor,
node_exporter, postgres_exporter, traefik — liegt im Repo `odoo-hub` und erbt dessen
Lebenszyklus (C1). Auf dem odoo-Host laufen acht Container mit dem Präfix `odoo_`,
während `odoo_web` und `odoo_db` gestoppt sind (C2).

Der Anlass ist **nicht**, dass Odoo stirbt. Owner-Kontext vom 2026-08-31: odoo und
ttz-hub sind **eine gemeinsame Initiative**, ttz erzwingt Odoo, und das Vorhaben wird
aller Voraussicht nach größer. Genau das verschärft das Problem: ein wachsendes
Produktprojekt ist ein **schlechterer** Träger für Plattform-Infrastruktur als ein
sterbendes. Ein sterbendes Repo wird einmal abgeräumt; ein wachsendes deployt,
startet neu und baut um — und reißt bei jedem dieser Vorgänge den Monitor mit, auf
den sich KONZ-054 seit dem 2026-08-30 stützt.

Die Empfehlung ist ein Schnitt nach **gemeinsamem Lebensende**: was weiterleben muss,
wenn das ttz/odoo-Projekt eigene Wege geht, gehört nicht in dessen Repo. Für den
Monitor ist die Antwort ja. Für `aifw_service` ist sie **nein** — er ist die
NL→SQL-Brücke auf die Odoo-Datenbank und teilt das Lebensende des Projekts; sein
Problem ist ein anderes (Fork, #2546) und darf nicht mit diesem verwechselt werden.

Der teuerste Teil ist nicht der Schnitt, sondern die **blinde Phase**: der Monitor
zieht sich selbst um. In dem Fenster misst niemand die Flotte, und es ist der eine
Moment, in dem ein Ausfall anderswo unbemerkt bliebe.

## 2 Scope & Evidenzbasis

**Im Scope:** die Verortung des Flotten-Monitors; das Schnittkriterium als
wiederverwendbare Regel; die Reihenfolge; die Absicherung der blinden Phase.

**Nicht im Scope:** die Zukunft des ttz/odoo-Projekts selbst; ob Odoo wieder
hochgefahren wird; die Wahl der Monitoring-Technologie (Prometheus/Grafana bleiben);
die Auflösung des `aifw_service`-Forks (eigener Vorgang #2546, hier nur als
Reihenfolge-Abhängigkeit).

| Claim | Beleg | Klasse |
|---|---|---|
| Monitor liegt in odoo-hub | C1 — 12 Dienste in einer Compose-Datei | E2 |
| Odoo gestoppt, Monitor läuft | C2 — 8 `odoo_*` up, `odoo_web`/`odoo_db` exited | E2 |
| `grafana.iil.pet` zeigt auf den odoo-Host | C4 — `prod_host: odoo`, bis 2026-08-30 falsch auf `prod` | E2 |
| KONZ-054 stützt sich auf diesen Monitor | C6 | E1 |
| Es gibt ein **zweites** Grafana | C7 (ADR-115, LLM-Controlling) + C8 (mcp-hub, definiert) | E1/E2 |
| `aifw_service` ist ein Fork | C5 — ältere Fassung läuft, getestete liegt in ttz-hub | E3 |
| `infra-deploy` trägt keine Stacks | C10 — nur `scripts/`, `docs/`, kein Compose | E2 |

**Nachgemessen (REC-1, erledigt):** Der odoo-Prometheus scrapt **7 aktive Targets,
alle `up`** — und damit die Flotte, nicht nur sich selbst:

```
fleet-cadvisor   89.167.43.30:9338     up      (prod-b)
fleet-cadvisor   88.198.191.108:9338   up      (prod)
fleet-cadvisor   cadvisor:8080         up      (odoo)
fleet-node       89.167.43.30:9100     up      (prod-b)
node             odoo-prod             up
postgres         odoo-db               up
prometheus       localhost:9090        up
```

Die Aussage in KONZ-054 (C6, Zeilen 107/223), der Prometheus messe nur sich selbst,
ist damit **überholt** — sie stammt von vor dem 2026-08-30. Das ist keine Korrektur
an KONZ-054, sondern dessen Erfolg: die Umstellung war eines seiner Ergebnisse.

**Folge für dieses Konzept:** die blinde Phase wiegt **schwer**, nicht leicht. Zwei
von drei Prod-Hosts werden aktiv gemessen; während des Umzugs sind sie unbeobachtet.
Damit ist §7.1 keine Formalie, sondern die eigentliche Planungsaufgabe.

**Nebenbefund aus derselben Messung:** `prometheus.yml` trägt eine auskommentierte
Zeile `# - targets: ['88.198.191.108:9100'] # prod: ufw allow from 46.225.127.211
fehlt`. Der `node_exporter` von **prod** wird deshalb nicht gescrapt — prod ist nur
über cadvisor sichtbar, nicht über Node-Metriken. Die fehlende ufw-Regel ist in
[#2504](https://github.com/achimdehnert/platform/issues/2504) bereits getrackt.

## 3 Infrastruktur-Fit

`project-facts.md` im platform-Repo ist leer (geöffnet, kein Inhalt) — es liefert
für dieses Konzept keinen Kontext. Die tragenden Bezüge sind stattdessen:

- **KONZ-054** (aktiv, Kill-Gate 2026-10-15): baut das Systembild und nennt den
  odoo-Prometheus ausdrücklich als Ergänzungsoption A2 (C6). Dieses Konzept ist
  dessen Vorbedingung, nicht sein Konkurrent: A2 lässt sich nicht auf einen Stack
  stützen, der an einem Produktprojekt hängt.
- **ADR-115** (accepted, implemented): ein **anderes** Grafana — das
  Controlling-Dashboard für LLM-Kosten des Agent-Squads (C7). Es ist in mcp-hub
  definiert (C8) und läuft dort derzeit nicht auf prod. Wer „Grafana" sagt, muss ab
  jetzt sagen, welches.
- **ADR-292** (Two-Lane-Deployment, Six-Host-Standard): regelt Lanes und Hosts,
  trifft aber keine Aussage über die Repo-Zugehörigkeit von Infrastrukturdiensten.
  Genau diese Lücke füllt dieses Konzept.

## 4 Steelman — warum der heutige Zustand vernünftig ist

Er ist nicht aus Nachlässigkeit entstanden, sondern aus drei guten Gründen:

**Nähe zur Datenquelle.** `postgres_exporter` misst die Odoo-Datenbank; `cadvisor`
und `node_exporter` messen den Host, auf dem Odoo lief. Sie im selben Compose-Projekt
zu halten gibt ihnen ohne Zusatzaufwand dasselbe Netzwerk und dieselbe
Startreihenfolge.

**Ein Deploy statt zwei.** Ein Compose-Projekt heißt: ein `docker compose up`, ein
`.env.prod`, ein Traefik. Die Alternative kostet einen zweiten Deploy-Pfad, ein
zweites Secret-Set und eine Netzwerkbrücke zwischen den Projekten.

**Der Host war ohnehin da.** Als der Monitoring-Stack entstand, war der odoo-Host der
einzige Ort mit freier Kapazität und einem Traefik. Ihn dort aufzusetzen war die
billigste tragfähige Entscheidung — und sie hat funktioniert: der Stack läuft seit
Wochen (C2, `node_exporter` seit zwei Wochen up).

Wer diesen Zustand heute kritisiert, kritisiert eine Entscheidung, die zu ihrer Zeit
richtig war. Geändert hat sich nicht die Technik, sondern die **Rolle**: aus einem
Monitor für einen Host ist der Monitor für die Flotte geworden.

## 5 Konzeptdefinition

**Kernthese:** Ein Repo bündelt Dinge mit **gemeinsamem Lebensende**. Der Prüfsatz
lautet: *Muss A weiterleben, wenn B stirbt oder eigene Wege geht?* Ist die Antwort
ja, gehört A nicht in B.

Das Kriterium ist bewusst nicht „technische Zusammengehörigkeit" und nicht
„Team-Zuständigkeit". Beide sind unscharf und laden zum Verhandeln ein. Das
Lebensende ist ein Ereignis, über das man sich nicht streiten kann.

**Angewandt:**

| Komponente | Muss sie ttz/odoo überleben? | Folge |
|---|---|---|
| Prometheus, Grafana, Loki, Promtail | ja — misst die Flotte | ausgliedern |
| cadvisor, node_exporter | ja — misst den Host, nicht das Produkt | ausgliedern |
| `postgres_exporter` | **offen** — misst heute die Odoo-DB | siehe §7 |
| traefik | nein — Reverse Proxy des Projekts | bleibt |
| `aifw_service` | nein — NL→SQL auf Odoo-Daten | bleibt, Fork auflösen (#2546) |
| Odoo `web`, `db` | — | Kern des Projekts |

**Was das Konzept NICHT vorschlägt:** eine Regel „Infrastruktur gehört immer in ein
eigenes Repo". Das wäre die Über-Architektur, vor der Step 2a warnt. Der Prüfsatz
wird pro Komponente angewandt, und in vier von sieben Fällen fällt er heute zugunsten
des Verbleibs aus.

## 6 Adversariale Analyse

**Abweichung, bewusst und benannt:** Der Skill verlangt für T3 drei *unabhängige*
Agenten. Diese Sitzung arbeitet unter der Weisung, keine Subagenten ohne
ausdrücklichen Wunsch zu starten. Das Adversariat läuft deshalb inline in getrennten
Abschnitten. Das ist schwächer — ein Kritiker, der den Steelman gelesen hat, zieht
Schläge zurück. Wer das Konzept vor der Entscheidung härten will, sollte
`/adr-handoff-extern` für eine echte Zweitmeinung nutzen.

### 6.1 Advocatus Diabolus

**AD-1 — Der Umzug schafft die Doppelquelle, die er beseitigen will.** Nach dem
Schnitt gibt es zwei Compose-Projekte, die beide `traefik`-Regeln, Netzwerke und
Secrets brauchen. `grafana.iil.pet` muss auf das neue Projekt zeigen, während der
alte Traefik im ttz/odoo-Projekt weiterläuft. Wird die alte Route nicht entfernt,
existieren zwei Wege zu einem Namen — und der schnellere gewinnt.

**AD-2 — „Sichtbar machen" ist hier schwächer als „verhindern".** Das Konzept
verlagert Container. Nichts hindert die nächste Person daran, den nächsten
Infrastrukturdienst wieder ins nächstbeste Produkt-Repo zu legen. Ohne ein Gate, das
den Prüfsatz erzwingt, ist dies eine einmalige Aufräumaktion, kein Konzept.

**AD-3 — Die blinde Phase wird unterschätzt.** Prometheus' TSDB und Grafanas
Dashboards liegen in Volumes, die am Projektnamen hängen. Ein neues Projekt bekommt
**neue, leere** Volumes. Wer die Migration überspringt, verliert die Historie — und
merkt es erst, wenn er sie braucht: bei der ersten Frage „seit wann geht das schon so?".

**AD-4 — Das Kriterium ist zirkulär anwendbar.** „Muss A weiterleben, wenn B stirbt?"
lässt sich für fast jede geteilte Komponente mit ja beantworten. Konsequent
angewandt zerlegt es die Plattform in ein Dutzend Ein-Dienst-Repos. Das Konzept
braucht eine Untergrenze, sonst ist es ein Rezept für Fragmentierung.

**AD-5 — Es gibt zwei Grafanas, und das Konzept löst nur eines.** ADR-115 beschreibt
ein Controlling-Grafana in mcp-hub (C7/C8). Nach dem Umzug gibt es ein
Flotten-Grafana in einem neuen Repo und ein LLM-Grafana in mcp-hub — beide „Grafana",
beide Plattform-Infrastruktur. Wer den Prüfsatz ernst nimmt, müsste auch dieses
anfassen; wer es nicht tut, hat den Schnitt nur zur Hälfte gemacht.

**AD-6 — F-Item-Analogie: Wo wird formal erfüllt und praktisch umgangen?** Ein neues
Repo mit eigenem Compose-Projekt erfüllt das Kriterium formal. Läuft der Stack
weiterhin auf dem odoo-Host und wird über dessen Traefik geroutet, ist die Kopplung
technisch unverändert — nur die Datei liegt woanders. Das Kill-Gate muss deshalb an
der Container-Ebene messen, nicht an der Repo-Ebene.

### 6.2 Maintainer 2028

Wer in zwei Jahren `grafana.iil.pet` debuggt, findet: ein Repo `observability-*`,
dessen Container auf einem Host laufen, der nach einem ERP heißt, das dort vielleicht
nicht mehr läuft. Er wird fragen, warum — und die Antwort steht dann hoffentlich in
diesem Dokument und nicht nur in einem Chatverlauf.

Sein zweites Problem: die Prometheus-Historie hat entweder einen Bruch am Umzugstag
oder eine Lücke. Beides ist erklärbar, aber nur, wenn es **dokumentiert** ist. Ein
undokumentierter Bruch in Zeitreihen ist eine Falle für jede spätere Kapazitätsfrage.

Sein drittes: `postgres_exporter` misst heute eine gestoppte Datenbank (C2 — der
Exporter läuft, `odoo_db` nicht). Falls das so bleibt, findet er einen Exporter, der
seit Jahren nichts misst und trotzdem grün ist.

## 7 Deep-Dive: die drei harten Stellen

**7.1 Die blinde Phase.** Während der Monitor umzieht, misst er nicht. Das Fenster
ist so lang wie der Umzug, und es ist genau das Fenster, in dem ein Fehler
unbemerkt bliebe. Drei Umgangsweisen, aufsteigend nach Aufwand:

1. *Akzeptieren und terminieren* — Umzug in ein angekündigtes Fenster legen, davor
   und danach den Sitzungsstart als Ersatzmelder nutzen (Phasen 0.7.11/0.7.17/0.7.22
   messen ohne Prometheus). **Billigste tragfähige Option.**
2. *Parallelbetrieb* — neuer Stack hoch, beide scrapen, dann alten abschalten. Sauber,
   aber zwei Prometheus auf einem Host, doppelter Speicher, und die TSDB-Migration
   wird dadurch nicht einfacher.
3. *Fremdüberwachung* — externer Uptime-Dienst für die Dauer. `uptime-kuma` ist in
   ports.yaml deklariert (C4, Host staging) und könnte das Fenster abdecken.

**7.2 Die Daten (REC-2, erledigt).** Die Konfiguration ist **provisioniert und liegt
im Repo**: `odoo-hub/grafana/provisioning/{dashboards,datasources,alerting}/`, dazu
`grafana/prometheus/prometheus.yml` und `grafana/prometheus/rules/flotte.yml` (die
Schwellen aus KONZ-054). Damit ist der Umzug der Konfiguration ein Dateiumzug —
trivial, versioniert, nachvollziehbar.

Übrig bleibt genau **ein** Datenproblem: die Prometheus-TSDB im Volume. Sie ist die
einzige Quelle der Historie und wandert nicht mit einem neuen Compose-Projekt. Wer sie
nicht migriert, verliert alles vor dem Umzugstag — und merkt es erst bei der ersten
Frage „seit wann geht das schon so?". Der Aufwand ist damit klein und **benennbar**:
ein Volume, kein Datenbank-Export.

**7.3 `postgres_exporter`.** Er ist der einzige Fall, in dem der Prüfsatz nicht
eindeutig ausfällt. Er misst die Odoo-Datenbank — also Produkt, nicht Flotte. Läuft er
aber weiter, während `odoo_db` gestoppt ist (C2), misst er nichts und meldet trotzdem.
Entscheidung: er **bleibt** beim Produkt und wird mit ihm gestoppt. Der Flotten-Stack
bekommt eigene Exporter für die Datenbanken, die er wirklich überwacht.

## 8 Alternativen

| # | Alternative | Bewertung |
|---|---|---|
| A1 | Nur `COMPOSE_PROJECT_NAME` ändern, Datei bleibt in odoo-hub | **Scheinlösung.** Container heißen nicht mehr `odoo_*`, hängen aber weiter am Repo-Lebenszyklus. Löst AD-6 nicht, kostet dieselbe Volume-Migration. Abgelehnt |
| A2 | Stack nach `infra-deploy` | `infra-deploy` trägt heute keine Stacks — nur `scripts/`, `docs/` (C10). Es aufzunehmen wäre eine neue Rolle für ein Repo, das bisher Skripte hält. Vertretbar, aber es verschiebt die Frage nur |
| A3 | Eigenes Repo (`observability-hub` o. ä.) | **Empfohlen.** Klare Grenze, eigener Lebenszyklus, Platz für das ADR-115-Grafana in einem zweiten Schritt (AD-5). Kosten: ein Repo mehr, ein Deploy-Pfad mehr |
| A4 | Managed Monitoring (Grafana Cloud o. ä.) | Löst Betrieb und blinde Phase, verlagert aber Flottendaten zu einem Dritten. Bei einem Bestand mit Bürgerdaten-Repos ist das eine Datenschutzfrage, keine Betriebsfrage. Nicht ohne eigene Prüfung |
| A5 | Alles lassen, Kopplung dokumentieren | **Der ehrliche Nullfall.** Wenn der Umzug nicht sauber gelingt, ist eine dokumentierte Kopplung besser als ein halber Schnitt. Steht deshalb im Kill-Gate |

## 9 Out-of-the-Box

**Muss der Monitor auf dem odoo-Host liegen?** Er misst die Flotte, nicht diesen
Host. Der Umzug ins eigene Repo ist die Gelegenheit, auch den Ort zu prüfen — ein
Monitor, der auf dem am wenigsten belasteten Knoten liegt, überlebt den Ausfall des
am stärksten belasteten. Heute läge er auf demselben Host wie das Produkt, das er
überwachen soll.

**Der Prüfsatz taugt über diesen Fall hinaus.** „Gemeinsames Lebensende" ist auch die
Antwort auf die `aifw_service`-Frage (#2546) und auf die Frage, warum
`prod-offsite-daily.sh` in `platform/infra/host-maintenance/` liegt und nicht im
Repo des Dienstes, den es sichert. Wenn er sich hier bewährt, gehört er als
Amendment in ADR-292 — dort, wo Lanes und Hosts geregelt sind, fehlt genau diese
Achse.

## 10 Befunde

| ID | Befund | Klasse | Beleg |
|---|---|---|---|
| B1 | 8 Container mit Präfix `odoo_` tragen den Flotten-Monitor, während Odoo gestoppt ist | E2 | C2 |
| B2 | `grafana.iil.pet` war bis 2026-08-30 auf den falschen Host deklariert | E2 | C4 |
| B3 | Es existieren zwei Grafana-Kontexte in der Plattform | E1/E2 | C7, C8 |
| B4 | `postgres_exporter` läuft, seine Datenbank nicht | E2 | C2 |
| B5 | `aifw_service` ist ein Fork; die ältere Fassung läuft | E3 | C5, #2546 |
| B6 | `infra-deploy` trägt keine Stacks und ist kein fertiger Zielort | E2 | C10 |
| B7 | Prometheus scrapt 7 Targets, alle `up` — die Flotte, nicht nur sich selbst | E2 | §2, Messung 2026-08-31 |
| B8 | `node_exporter` von **prod** wird nicht gescrapt (ufw-Regel fehlt) | E2 | `prometheus.yml`, #2504 |
| B9 | Grafana-Konfiguration ist provisioniert; nur die TSDB ist echtes Migrationsgut | E2 | §7.2 |

## 11 Top-5-Risiken

| # | Risiko | Wirkung | Gegenmaßnahme |
|---|---|---|---|
| R1 | Blinde Phase während des Umzugs | ein Ausfall bleibt unbemerkt | Fenster ankündigen, Sitzungsstart-Phasen als Ersatzmelder, §7.1 |
| R2 | TSDB/Dashboards gehen verloren | Historie weg, Bruch unerklärt | §7.2 **vor** der Terminplanung klären; Volume-Migration ist Teil des Umzugs, nicht Nacharbeit |
| R3 | Zwei Wege zu `grafana.iil.pet` | der schnellere gewinnt, Debugging irreführend | alte Traefik-Regel im selben Zug entfernen, nicht danach |
| R4 | Formal umgezogen, faktisch gekoppelt | Konzept erfüllt, Problem bleibt | Kill-Gate misst Container-IDs bei einem Produkt-Deploy, nicht Repo-Pfade (AD-6) |
| R5 | Fragmentierung durch zirkuläres Kriterium | ein Dutzend Ein-Dienst-Repos | Untergrenze: nur Komponenten mit **eigenem öffentlichen Namen oder eigenem Datenbestand** werden ausgegliedert |

## 12 Empfehlungen

| # | Empfehlung | Konkret |
|---|---|---|
| REC-1 | ~~B7 klären~~ **erledigt 2026-08-31** | 7 Targets aktiv, 2 Prod-Hosts gemessen → R1 wiegt schwer, §7.1 ist Planungsaufgabe |
| REC-2 | ~~§7.2 beantworten~~ **erledigt 2026-08-31** | provisioniert im Repo; einziges Migrationsgut ist die Prometheus-TSDB |
| REC-3 | A3 umsetzen: eigenes Repo | Monitoring-Dienste aus `odoo-hub/docker-compose.prod.yml` herauslösen, ohne `traefik`, ohne `postgres_exporter` (§7.3) |
| REC-4 | Route atomar umhängen | Cloudflare-Tunnel-Route + `infra/ports.yaml` im selben Zug wie den Container-Start; alte Regel entfernen (R3) |
| REC-5 | Reihenfolge einhalten | #2546 (aifw-Fork) **vor** dem Umzug entscheiden — ein Umzug zementiert sonst den falschen Stand |
| REC-6 | Prüfsatz verankern | nach erfolgreichem Umzug als Amendment zu ADR-292 vorschlagen (§9), nicht vorher |

## 13 Entscheidung, Kill-Gate, 30/60/90

**Entscheidung (Owner, 2026-08-31): A3 — eigenes Repo.** Der Flotten-Monitor wird
aus `odoo-hub` herausgelöst; `aifw_service` und `traefik` bleiben beim Produkt, der
Schnitt folgt dem gemeinsamen Lebensende (§5).

Damit ist die Richtung entschieden, **nicht** der Termin. Zwei Dinge stehen zwischen
Entscheidung und Umzug, beide aus dem Konzept selbst:

1. **#2546 zuerst** (REC-5). Solange offen ist, welche `aifw_service`-Fassung die
   Wahrheit ist, würde der Umzug den älteren Stand zementieren.
2. **Das Umzugsfenster** (§7.1). Zwei von drei Prod-Hosts sind währenddessen
   unbeobachtet — belegt durch die 7 aktiven Targets (C11). Das Fenster gehört
   angekündigt, nicht beiläufig genommen.

Der Umsetzungspfad steht als eigenes Issue; dieses Dokument bleibt die Begründung,
nicht die Checkliste.

**Kill-Gate am 2026-11-30.** Verfehlt (1) oder (2) sein Ziel, wird zurückgerollt und
A5 gewählt — dokumentierte Kopplung statt halbem Schnitt.

| Kriterium | Status | Beleg |
|---|---|---|
| (1) `grafana.iil.pet` läuft unter einem Projektnamen ohne Produktbezug, Prometheus-Historie reicht über den Umzugstag zurück | offen | — |
| (2) Ein Produkt-Deploy lässt alle Monitor-Container unberührt (Container-ID unverändert) | offen | — |
| (3) `aifw_service` existiert nur noch einmal in der Flotte | offen | #2546 |

**30 Tage:** REC-1 und REC-2 beantwortet, #2546 entschieden, Zielrepo benannt.
**60 Tage:** Umzug durchgeführt, Route umgehängt, alte Regel entfernt.
**90 Tage:** Kill-Gate gemessen; bei Erfolg REC-6 als ADR-292-Amendment.

**Ehrliche Enforcement-Grenze:** `review_by` und `kill_criteria` in diesem Dokument
wirken erst, wenn ein Lifecycle-Gate sie liest. Ein solches Gate existiert nicht.
Bis dahin ist dieses Kill-Gate ein Review-Versprechen, kein Exit-Code.
