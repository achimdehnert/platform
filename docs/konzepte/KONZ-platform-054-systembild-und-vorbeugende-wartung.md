---
concept_id: KONZ-platform-054
title: Systembild und vorbeugende Wartung über den gesamten Knoten-Bestand
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: Amendment an ADR-289 (Rollen R2/R3) + Amendment an ADR-241 (Deckung); kein neuer org-weiter ADR
review_by: 2026-10-15
kill_criteria: "Am 2026-10-15 gilt: (1) jede scharfgeschaltete Befundklasse hat >=3 Urteile und >=0,6 Präzision (tools/befund_journal.py --praezision), (2) >=90 % der offenen platform-Befunde tragen eine Wiedervorlage, (3) kein Melder-Workflow wertet eine Scope-Lücke als grün. Verfehlt eine der drei Bedingungen ihr Ziel, wird die betroffene Stufe abgeschaltet statt nachgebessert."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: tools/reconcile_registry_live.py, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C2, source_path: .github/workflows/registry-live-reconcile.yml, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C3, source_path: tools/speicher_melder.py, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C4, source_path: tools/befund_journal.py, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C5, source_path: .github/workflows/backup-deckung.yml, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C6, source_path: infra/hosts.yaml, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C7, source_path: infra/ports.yaml, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C8, source_path: docs/adr/ADR-289-netcup-off-provider-platform-services-host.md, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C9, source_path: docs/adr/ADR-241-backup-disaster-recovery-baseline.md, commit_or_pr: "#2483", opened_in_session: true}
  - {claim_id: C10, source_path: tools/erreichbarkeit_melder.py, commit_or_pr: "#2483", opened_in_session: true}
created: 2026-08-30
---

# KONZ-platform-054 — Systembild und vorbeugende Wartung über den gesamten Knoten-Bestand

## 1 Executive Summary

**Tier T3.** Das Konzept verschiebt eine SSoT-Rolle, berührt den Sicherheits-Perimeter (flottenweiter
SSH-Fan-out) und wirkt über mehrere Repos. Damit sind drei der nicht verhandelbaren
Auto-Eskalations-Trigger erfüllt; eine kleinere Einstufung wäre falsch.

Der Auftrag (#2483) fragte nach vorausschauender Wartung. Die Erhebung dazu ergab, dass die
Flotte **kein Melde-Problem** hat: gemessen wurden 33 Session-Start-Phasen, 28 geplante
GitHub-Workflows und 16 Host-Cron-/Timer-Stellen. Sie hat drei andere Probleme, und alle drei
liegen **hinter** der Messung:

1. **Kein Empfänger.** Befunde landen in einem maschinengebundenen Journal
   (`~/.claude/befund-journal.json`); Stand der Messung: 17 Einträge, 17 offen, 0 verankert,
   12 ohne Wiedervorlage. `tools/befund_journal.py` überspringt beim einzigen Zwangsmittel
   Befunde des eigenen Repos — genau die Infra-Befunde, um die es hier geht.
2. **Kein Nenner.** Melder melden grün über ungemessenes Gebiet. `backup-deckung.yml` läuft
   ausdrücklich mit `--nur prod`, wertet die Scope-Lücke als bekannt und bleibt grün.
3. **Kein Alarmweg.** Der lauteste Host-Melder meldet seit 177 Tagen zu 100 % FAIL an einen
   Kanal, den es nicht gibt (`| mail` ohne MTA). Ein abgelaufener Prod-PAT stand 20 Tage
   unbemerkt in einer Datei.

Die naheliegende Antwort — ein neuer, flottenweiter Erheber — ist **falsch**, aus zwei belegten
Gründen. Erstens existiert die Erhebung bereits und läuft täglich (`reconcile_registry_live.py`,
`speicher_melder.py`). Zweitens hängt jeder nächtliche Fan-out an einer Berechtigung, die der
einzige geplante Ausführungsort nachweislich **nicht hat** und die ausdrücklich als Owner- und
Security-Entscheidung geführt wird (#2284).

Deshalb schlägt dieses Konzept **Verhindern vor Melden** vor: Der teuerste Befund des gesamten
Laufs — ein als stillgelegt deklarierter Dienst, der auf dem falschen Knoten neu deployt wurde und
25 Stunden in einer Fehlerschleife lief — wäre durch **einen Preflight-Schritt im Deploy-Workflow**
gar nicht erst entstanden. Nicht durch einen Melder, der ihn nachts findet.

## 2 Scope und Evidenzbasis

**Gegenstand:** die acht Knoten aus `infra/hosts.yaml` — prod, prod-b, staging-dedicated,
dev-desktop, odoo, netcup, gpu-box, gx10.

**Evidenzbasis:** ein Lauf mit 13 Agenten am 2026-08-30, read-only, sieben Knoten erreicht
(gx10 existiert noch nicht). Ergebnis: 109 Befunde aus dem Knoten-Inventar, 55 aus vier
Querschnitts-Dimensionen. Anschließend drei unabhängige adversariale Rollen (Steelman,
Advocatus Diabolus, Maintainer-2028) gegen den ersten Entwurf.

**Bekannte Schwäche der eigenen Erhebung, ehrlich benannt:** Der zusammenfassende Befundkatalog
erhielt die Rohdaten **gekürzt** und deckt darum nur vier Knoten und drei Dimensionen ab
(86 Einträge). Odoo, netcup, GPU-Box und die Perimeter-Dimension fehlen darin, obwohl ihre
Rohdaten vorliegen. Der Katalog ist vor der Umsetzung mit vollständiger Eingabe neu zu bauen;
bis dahin gilt der Rohdatensatz, nicht der Katalog.

**Evidenzklassen in diesem Dokument:** `E2s` = Datei in dieser Sitzung von mir selbst geöffnet ·
`E2a` = von einem Agenten dieser Sitzung geöffnet und mit Zeilenbeleg berichtet · `E3` =
Issue/PR/CI · `H` = Hypothese.

## 3 Infrastruktur-Fit

| Baustein | Zustand | Beleg |
|---|---|---|
| `infra/hosts.yaml` | Knoten-Wahrheit für alles, was zum Knoten geht — 5 Werkzeuge lösen daraus ein SSH-Ziel auf | E2a |
| `infra/ports.yaml` `servers:` | 3 von 8 Knoten; 3 Werkzeuge lösen daraus einen Knoten auf | E2s |
| `tools/reconcile_registry_live.py` | liest live `docker ps` je zuständigem `prod_host`, täglich 05:17 UTC | E2s (C1, C2) |
| `tools/speicher_melder.py` | Tagespunkt-Zeitreihe je Host, 8-Tage-Fenster, Median-Rate mit Vorlauf | E2s (C3) |
| `tools/befund_journal.py` | Fristen 14/30 Tage, `MIN_URTEILE=3`, `PRAEZISION_SCHWELLE=0.6` | E2s (C4) |
| `tools/backup_meter.py` | Snapshot-Frische je Soll-App — Soll-Liste ist der Defekt, nicht der Code | E2a |
| `tools/decommission_check.py` | existiert, in keinem Workflow verdrahtet | E2a |
| `tools/blindstellen.py` | existiert, in keinem Workflow verdrahtet (Gegenprobe: derselbe Grep findet andere Werkzeuge) | E2s |

**Fazit des Fit:** Die teure Hälfte ist gebaut. Was fehlt, ist billig — und liegt hinter der Messung.

## 4 Steelman

Die stärkste Fassung des Vorhabens lautet nicht „wir brauchen ein Systembild", sondern:

> *Die Wahrheitsseite ist weitgehend gebaut und läuft täglich; es fehlt ausschließlich ein
> Empfänger mit Frist und ein mitgemeldeter Nenner — belegbar daran, dass die vier lautesten
> Signale der Flotte bereits rot waren und niemanden erreichten.*

Vier Signale, die rot standen und folgenlos blieben: ein seit dem 2026-08-10 abgelaufener
Prod-PAT (drei 401-Läufe, Alarm ist eine Datei ohne Leser); ein Zertifikats-Melder, dessen
Webhook auskommentiert und dessen Fehler mit `|| true` verschluckt ist; ein Host-Healthcheck mit
177 Tagen 100 % FAIL an einen nicht existierenden Mailkanal; node_exporter und cadvisor, die auf
prod und prod-b laufen, während der einzige Prometheus der Flotte ausschließlich sich selbst
scrapet. (alle E2a)

Daraus folgt der Zuschnitt: **kein neues Auge, sondern ein Ohr und eine Frist.**

## 5 Konzeptdefinition

Fünf Eingriffe, in dieser Reihenfolge. Jeder ist für sich nützlich; keiner setzt einen neuen
privilegierten Pfad voraus.

### E1 — Preflight im Deploy-Gate (verhindert Klasse a und die halbe Klasse f)

Ein Schritt in `.github/workflows/_deploy-hetzner.yml`, der vor dem Deploy zwei Felder liest, die
heute kein Deploy-Pfad liest: `betriebsstatus` (Abbruch, wenn nicht `aktiv`) und `prod_host`
(Abbruch, wenn der ausführende Runner-Host ein anderer ist). Das tötet den teuersten Befund des
Laufs an der Quelle: coach-hub wurde am 2026-08-29 auf prod deployt, obwohl es seit dem
2026-08-23 als stillgelegt geführt wird und sein `prod_host` prod-b lautet.

### E2 — Empfänger reparieren (K4)

Drei Änderungen an `tools/befund_journal.py` und seinem Gate: die Ausnahme für das eigene Repo
fällt für Infra-Phasen; jeder Befund trägt verpflichtend eine Wiedervorlage; der Datensatz bekommt
die Felder `kommando`, `ausgabe`, `knoten` und `positivkontrolle` — ohne sie muss der Leser jeden
Befund selbst nachmessen, und dann spart der Melder nichts.

### E3 — Nenner als Meldegröße (K1)

Jeder Melder meldet „geprüft N von M Knoten"; eine Scope-Lücke ist ein eigener Zustand und nie
grün. Betrifft konkret `backup-deckung.yml` (heute `--nur prod` plus `continue-on-error`) und
`backup_meter.py` (Soll-Liste mit 8 von 10 Einträgen auf `deferred`).

### E4 — Alarmweg als prüfbares Artefakt (K4)

Ein Kanal gilt nur als vorhanden, wenn er in den letzten N Tagen **einmal erfolgreich benutzt**
wurde. Das ist der einzige genuin neue Baustein dieses Konzepts und die Antwort auf die zwei
belegten Fälle (Webhook auskommentiert, Mailkanal ohne MTA).

### E5 — Aufnahme-Vorgang für Knoten (K5)

`docs/runbooks/neuer-knoten.md` mit fester Reihenfolge, ein maschinenlesbares `auflage:`-Feld in
`hosts.yaml` (heute steht die Auflage als Fließtext im `role:`-Feld und wird von keinem Werkzeug
gelesen), eine **Frist** für `verified: false` statt der heutigen Dauerausnahme, und ein Gate auf
`arch:` gegen die amd64-Flotten-Images. Der GX10 ist der erste Fall.

### Bewusst NICHT Teil des Konzepts

- **Kein `tools/systembild.py`.** Die Erhebung existiert und läuft geplant.
- **Kein nächtlicher SSH-Fan-out über acht Knoten.** Das ist eine Security-Config-Entscheidung
  (#2284), keine Implementierung — siehe §6.
- **Keine Ist-Zeitreihe im Repo.** `platform` ist öffentlich.

### Ausführungsform (Step 2a)

Mehrere Schritte: ja. Feste Reihenfolge: ja → **Kette**, keine Router-Logik. Unabhängig: E1–E4
schon, sie laufen in getrennten Workflows. Barriere: nein. Verzweigung: nein. Schleife: nein —
und damit auch kein Abbruchkriterium für eine Schleife nötig. Die kleinste tragfähige Form ist
eine Kette aus vier unabhängigen Pull Requests.

## 6 Adversariale Analyse

### 6.1 Konfliktmatrix (Pflicht bei T3)

| # | Frage | Steelman | Advocatus Diabolus | Maintainer-2028 | Auflösung |
|---|---|---|---|---|---|
| D1 | Ist E2/S3 der größte Hebel? | ja, wirkt klassenunabhängig auf alle Befunde | nein — legt Befunde in den Eimer, den kein Gate liest | nein — Datensatz ohne Kommando/Knoten ist für den Leser wertlos | **Diabolus + Maintainer gewinnen.** E2 bleibt, aber mit Feldern und ohne Eigen-Repo-Ausnahme; der größte Hebel ist E1 |
| D2 | Ersetzt `reconcile_registry_live.py` einen neuen Erheber? | ja, vollständig | nur teilweise — 2 von 8 Knoten haben kein `ssh`-Feld, der Runner erreicht prod-b gar nicht | — | **Diabolus präzisiert.** Neubau entfällt trotzdem; die Reichweitenlücke wird als Owner-Gate geführt, nicht umgangen |
| D3 | Ist der Exit-3-Nenner der stärkste Einzelhebel? | ja, eine Workflow-Zeile | Symptom, nicht Ursache | „der Ausfallmodus dieser Flotte ist Stille" | **Teilkonsens.** E3 bleibt, aber als dritter Schritt, nicht als erster |
| D4 | Trägt `hosts.yaml` die SSoT-Rolle? | implizit ja | nein — kein `ssh` für odoo und gx10, `verified:` darf 120 Tage alt sein, Audit-Workflow ohne `schedule:` | nein — Datei schleppt Geisterknoten und tote Label mit | **Beide gegen den Entwurf.** Die Krönung von `hosts.yaml` wird zur Bedingung: erst reparieren, dann berufen |

Kein Punkt blieb ohne Dissens — die drei Rollen haben sich nicht bestätigt, sondern korrigiert.

### 6.2 Der teuerste Einwand

Der Diabolus hat die Annahme widerlegt, auf der die ganze Treppe stand: *„agentless über SSH aus
der Knotenliste" ist verfügbar*. Sie ist es doppelt nicht. `backup-deckung.yml` hält im Kommentar
fest, dass der self-hosted Runner als root auf prod läuft und **keinen** SSH-Zugang zu sich selbst
oder prod-b hat (gemessen 2026-08-25, Permission denied), und dass die Autorisierung des
Runner-Keys auf prod-b Security-Config und Owner-Sache ist (#2284). Ein Schlüssel mit Reichweite
über acht Knoten hebt die heutige Segmentierung auf — auf einem Host, dessen Journal 7 Tage
zurückreicht und dessen Swap dauerhaft am Anschlag steht.

### 6.3 Zweite Wahrheit und öffentliches Repo

Ein persistierter Ist-Schnappschuss kippt in dem Moment von Messung zu Deklaration, in dem der
erste Leser ihn statt des Knotens fragt. Erschwerend: `platform` ist öffentlich. Ein Schnappschuss
trägt IPs, Containernamen, Portbelegung, vhosts und Tunnel-Routen. Der erste Entwurf nannte
keinen Ablageort — das war sein gefährlichster blinder Fleck. **Setzung:** die Zeitreihe bleibt
außerhalb dieses Repos; wohin, ist eine eigene Entscheidung (Alternative: nicht persistieren und
K3 aufgeben).

### 6.4 Was das Konzept mitschleppen würde

Der Maintainer-2028 hat sieben Altlasten benannt, die der erste Entwurf **neben** sich stehen
ließ statt sie zu beseitigen: die maschinengebundene Lesefläche, ein Geisterknoten und tote
Runner-Label in der SSoT selbst, zwei hart verdrahtete Knoten in `server_probe.py` (ausgerechnet
das Werkzeug, das `hosts.yaml` als sein Verifikationsmittel benennt), ein Host-Healthcheck ohne
Empfänger, ein Wartungs-Melder für einen Container, den es nicht gibt, acht verwaiste
Runner-Verzeichnisse und die Regel, die kleine Nenner belohnt. **Konsequenz:** §12 bekommt einen
Rückbau-Block; ohne ihn ist jeder neue Melder der 78.

## 7 Deep-Dive: die sechs Befundklassen und ihr richtiger Ort

| Klasse | Heute abgedeckt | Richtiger Ort | Warum nicht Melder |
|---|---|---|---|
| a — Container trotz stillgelegt | keine Code-Stelle | **E1 Deploy-Preflight** | verhindert statt gemeldet; Realfall coach-hub |
| b — Healthcheck > 7 Tage rot | kein Werkzeug liest `.State.Health` | Melder, aber erst nach Kalibrierung | 3 von 6 heutigen Fällen sind kaputte Healthchecks, nicht kaputte Dienste |
| c — Host über Schwelle | Platte ja, RAM/Swap/Load nein | Erweiterung `speicher_melder.py` | Zeitreihe existiert, drei Kennzahlen fehlen |
| d — Route ohne Backend | nur von der Deklaration her | Erweiterung, Ingress-seitig | >80 reale Ingress-Einträge gegen 23 deklarierte Ziele |
| e — Name überlebt Stilllegung | nur `domain_prod` | **DNS-Schreiber verweigert Pflege für nicht-aktive Dienste** | verhindert statt gemeldet |
| f — Workload gegen Auflage | keine Code-Stelle, Auflage ist Fließtext | **E5 `auflage:`-Feld** + E1-Hostprüfung | ohne Feld ist die Klasse nicht maschinell prüfbar |

## 8 Alternativen

| # | Alternative | Warum nicht gewählt |
|---|---|---|
| A1 | Neuer flottenweiter Erheber (`tools/systembild.py`) | doppelt vorhandene Erhebung, verlangt einen neuen privilegierten Pfad, verletzt die eigene Randbedingung |
| A2 | Fremdlösung anmelden (Prometheus/Alertmanager auf odoo, node_exporter existiert bereits auf prod und prod-b) | **ernstzunehmend** — deckt Klasse c vollständig und billig ab. Nachteil: löst a/e/f nicht, und der odoo-Prometheus scrapet heute nur sich selbst. Empfehlung: als Ergänzung zu E1–E5 prüfen, nicht als Ersatz |
| A3 | Nichts tun, Befunde weiter von Hand finden | der heutige Lauf kostete 13 Agenten für einen Stichtag; die Befunde altern schneller, als Hand-Läufe stattfinden |

## 9 Out of the Box

Der Bestand belohnt kleine Nenner: wer wenig prüft, ist grün. Ein **Deckungs-Grad als einzige
Kennzahl über alle Melder** („dieser Melder sieht N von M") würde diesen Anreiz umkehren, ohne
einen einzigen neuen Melder zu bauen. Das ist E3, größer gedacht — und der billigste Kandidat für
eine spätere Ausbaustufe.

## 10 Befunde

Vollständig im Rohdatensatz zu #2483. Die fünf mit Sicherheits- oder Datenschutzbezug sind
herausgelöst und liegen als #2486 beim Owner. Die Sammelstellen für den Rest:

| Bereich | Kern |
|---|---|
| Deklarations-Drift | zwei Dienste laufen doppelt mit identischem `container_name`; vier als aktiv geführte Dienste laufen nirgends |
| Melder-Landschaft | 2 von 6 Klassen ohne Code-Stelle; Befunde ohne Frist; Präzision mangels Urteilen nicht bewertbar |
| Backup/DR | keine Konfiguration gesichert, keine Rückspielprobe belegt, Retention läuft nirgends |
| Perimeter | Auflagen sind Fließtext; `verified: false` ist eine Dauerausnahme |

## 11 Top-5-Risiken

| # | Risiko | Wirkung | Gegenmaßnahme im Konzept |
|---|---|---|---|
| R1 | E1 blockiert einen legitimen Deploy (falsch gepflegtes `betriebsstatus`) | Deploy steht | Abbruch mit Klartext und dem Feld, das ihn auslöste; Pflege ist ein Einzeiler |
| R2 | E2 erzeugt Frist-Rauschen, das wieder niemand liest | dritter toter Melder | Kill-Gate misst Präzision je Klasse; unter 0,6 wird abgeschaltet, nicht nachgebessert |
| R3 | Der SSH-Fan-out wird doch gebaut, weil er bequem ist | neuer privilegierter Pfad über acht Knoten | ausdrücklich außerhalb des Konzepts, Owner-Gate #2284 |
| R4 | Ist-Zeitreihe landet doch im öffentlichen Repo | Offenlegung von Topologie | Setzung §6.3; ohne Ablageort keine Persistenz |
| R5 | `hosts.yaml` wird zur SSoT erklärt, bleibt aber lückenhaft | Erheber misst zwei Knoten und meldet grün | Krönung erst nach Reparatur (`ssh` für odoo/gx10, Frist für `verified`) |

## 12 Empfehlungen

**Bauen (je ein PR, verlinkt auf #2483 und das Kriterium):**

1. E1 Deploy-Preflight in `_deploy-hetzner.yml` — liest `betriebsstatus` und `prod_host`.
2. E2 `befund_journal.py`: Eigen-Repo-Ausnahme für Infra-Phasen entfernen, Wiedervorlage
   verpflichtend, Datensatz um `kommando`/`ausgabe`/`knoten`/`positivkontrolle` erweitern.
3. E3 Nenner: `backup-deckung.yml` und `backup_meter.py` melden Deckung; Scope-Lücke nie grün.
4. E4 Alarmweg-Artefakt: „Kanal in den letzten N Tagen erfolgreich benutzt".
5. E5 `docs/runbooks/neuer-knoten.md`, `auflage:`-Feld, Frist für `verified: false`,
   `arch:`-Gate — vor der GX10-Aufnahme.

**Zurückbauen (gleicher Zug, sonst wächst nur die Zahl der Melder):**

6. `healthcheck.sh` ohne Empfänger, der Wartungs-Melder für den nicht existierenden Container,
   die zwei hart verdrahteten Knoten in `server_probe.py`, Geisterknoten und tote Runner-Label
   in `hosts.yaml`, die acht verwaisten Runner-Verzeichnisse.

**Entscheiden lassen (Owner):**

7. Reichweite des Erhebers (#2284), Ablageort der Zeitreihe, die fünf Punkte aus #2486,
   und ob A2 (Prometheus/Alertmanager) als Ergänzung kommt.

## 13 Entscheidung, Kill-Gate, 30/60/90

**Entscheidung:** Umsetzung in der Reihenfolge E1 → E2 → E3 → E4 → E5, jeweils ein PR. Kein
neuer Erheber, kein neuer privilegierter Pfad, keine Persistenz im öffentlichen Repo.

**Kill-Gate am 2026-10-15**, gemessen an drei Kommandos:

| Kriterium | Messung | Status | Beleg |
|---|---|---|---|
| K-a Präzision je scharfer Klasse ≥ 0,6 bei ≥ 3 Urteilen | `python3 tools/befund_journal.py --praezision` | offen | 2026-08-30: 8 Urteile gesamt, je Phase < 3 — nicht bewertbar; E2 (#2495) liefert Frist und Belegfelder, Urteile kommen aus /session-ende |
| K-b ≥ 90 % der offenen platform-Befunde mit Wiedervorlage | `python3 tools/befund_journal.py --bericht --json` | offen | Ausgangswert 0 von 17; seit E2 (#2495) trägt jeder neue Befund `entscheiden_bis`, 6 von 17 stehen im Gate (vorher 0) |
| K-c kein Melder-Workflow wertet eine Scope-Lücke als grün | `grep -n "Exit 3" .github/workflows/*.yml` | **erfüllt (gebaut)**, Wirkung im geplanten Lauf offen | E3 (#2498): backup-deckung und backup-meter färben Exit 3 rot ohne Issue; `backup_meter.py` meldet „Geprüft N von M". Erster geplanter Lauf 2026-08-31 05:00/05:30 UTC zu prüfen |
| K-d GX10 nach Runbook aufgenommen, ohne Sonderregel | Diff der Aufnahme gegen `docs/runbooks/neuer-knoten.md` | offen | E5 (#2493): Runbook, `auflage:`-Feld, `verified_bis` für gx10 (2026-09-30) stehen; Aufnahme selbst KW 37 |

**Umsetzungsstand 2026-08-30:** E1 #2488 · E2 #2495 · E3 #2498 · E4 #2500 · E5 #2493 — alle fünf
Stufen gemergt am Tag des Konzepts; Rückbau R1 (#2506), S1 (#2508), R2a und die Wiederanlauf-
Punkte 118/125–127/144 (#2503, #2505, odoo-hub#22) ebenfalls. Offen bei Owner: #2486, #2504, #2507.

Verfehlt ein Kriterium am Stichtag sein Ziel, wird die zugehörige Stufe **abgeschaltet**, nicht
nachgebessert. Exception-Budget: einmalige Verlängerung bis 2026-11-15, danach ersatzlos.

**30/60/90:**

- **30 Tage (bis 2026-09-29):** E1 und E2 gebaut und gemergt; erste 3 Urteile je scharfer Klasse.
- **60 Tage (bis 2026-10-29):** E3 und E4 wirksam; Deckungsgrad in jedem Melder-Bericht sichtbar.
- **90 Tage (bis 2026-11-28):** E5 durch die GX10-Aufnahme belegt; Rückbau-Liste aus §12.6 leer.
