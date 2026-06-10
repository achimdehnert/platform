---
status: draft
date: 2026-06-10
decision-makers: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-045, ADR-072, ADR-090, ADR-142, ADR-143, ADR-144, ADR-157, ADR-218, ADR-234, ADR-236]
implementation_status: none
last_reviewed: 2026-06-10
staleness_months: 3
tags: [backup, disaster-recovery, offsite, restore-test, enterprise-core, governance]
---

# ADR-241: Platform-weite Backup- & Disaster-Recovery-Baseline (Offsite by construction)

> **Nummern-Hinweis:** 241 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).

## Status-Hinweis

`draft` — entscheidungsreif bis auf zwei Owner-Gates (§7: Offsite-Ziel-Wahl, Prod-Verifikation).
Kandidat für den `enterprise-core`-Subset (Enterprise-Basis-Entscheidung E3/E4, 2026-06-10).

## Kontext & Problemstellung

Die Backup-/DR-Lage wurde am 2026-06-10 vollständig aus Datei-Evidenz inventarisiert
(kein Server-Zugriff; Prod-Verifikation ist Gate G2 in §7). Befund:

**Was existiert (verifiziert):**

| Mechanismus | Pfad | Eigenschaften |
|---|---|---|
| Pre-Deploy-Backup | `deployment/scripts/deploy-remote.sh:133-146` | `pg_dumpall \| gzip`, keep-last-10 — **einziger by-construction erzwungener Pfad**, aber deploy-getriggert (nicht zeitgesteuert) und **non-blocking bei Fehler** |
| Stack-Backups | `deployment/stacks/{outline,authentik,doc-hub}/backup.sh` | tägliche pg_dump-Crons (ADR-142/143/144), Retention 7/7/30 d — Installation **manuell** per scp + cp nach `/etc/cron.daily/` |
| risk-hub | `risk-hub/scripts/backup.sh` | pg_dump + Media-tar; **Cron-Header zeigt auf falschen Pfad** (`/home/deploy/projects/` statt `/opt/risk-hub`, ADR-022), nichts installiert ihn; **MinIO-Volume (Kundendokumente) nicht abgedeckt** |
| dev-hub | `dev-hub/scripts/backup.sh` | pg_dump + Disk-Guard, Cron-Kommentar, 14 d Retention — Installation ebenfalls manuell |
| mcp-hub | — | **kein Backup-Skript**; `mcp_hub_pgdata` enthält den Orchestrator-pgvector-Shared-Memory |
| `/backup`-Skill | `.windsurf/workflows/backup.md` | interaktiv, on-demand, 5 Apps, keine Retention/kein Scheduling |

**Was fehlt (verifiziert):**

1. **Null Offsite-Kopien.** Alle Backup-Ziele (`/opt/backups/*`, `${DEPLOY_DIR}/backups/`)
   liegen auf **demselben Host wie die Daten** (CPX52, ein Prod-Server, ADR-157).
   Disk-/Host-Verlust = Totalverlust **inklusive aller Backups**. Offsite wurde genau
   einmal konzipiert (ADR-008: restic + Hetzner Storage Box) — deprecated, „never
   implemented", ohne Nachfolger. Die ADR-030-Checkbox „Off-Server Backup Copy" ist
   seit 2026-02 offen.
2. **Kein einziges DB-Restore-Runbook und kein Restore-Test** im gesamten Bestand
   (einzige Ausnahme: CF-Origin-Certs, `docs/runbooks/cf-origin-cert-restore.md`).
   Ein Backup ohne geprobten Restore ist eine Hypothese, kein Backup.
3. **Keine erzwungene Installation/Verifikation.** Alle Daily-Backups hängen an
   manuell kopierten cron.daily-Dateien; kein IaC, kein „backup ran"-Alert, kein Meter.
   Ob die Crons auf Prod laufen, ist Stand heute **Hypothese** (Gate G2).
4. **Keine RPO/RTO-Definitionen** (nur ADR-218 erwähnt RPO/RTO als Doku-Pflichtfeld).

Das Ökosystem betreibt ein zahlendes Live-Kundenprodukt (risk-hub / schutztat.de,
Multi-Tenant) und plant die Enterprise-Konsolidierung (ADR-236, KONZ-002). Eine
Enterprise-Basis ohne Offsite-Backup und ohne Restore-Beweis ist nicht tragfähig.

## Entscheidungstreiber

- **Ein-Host-Klumpenrisiko** (ADR-157: ein Prod-Server) ist der dominante DR-Fall —
  nicht einzelne DB-Korruption.
- **Derived-Invariant-Philosophie** (ADR-234/235): Backup-Gesundheit muss *gemessen
  und erzwungen* werden, nicht dokumentiert — Prosa-Crons sind nachweislich gedriftet.
- **Zwei-Personen-Kapazität:** Lösung muss wartungsarm sein; kein neues Framework,
  vorhandene Bausteine (pg_dump-Skripte, GitHub Actions, Hetzner) weiterverwenden.
- **Datenhoheit:** Government-Workloads (ttz-lif/meiki-lra) erzeugen perspektivisch
  eigene Anforderungen an Backup-Standort — Baseline muss das nicht lösen, darf es
  aber nicht verbauen (EU-Storage genügt für die Baseline).
- **Kosten:** Offsite-Speicher muss im Budget einer kleinen GmbH liegen (~5 €/Monat-Klasse).

## Betrachtete Optionen

### Option A — Status quo formalisieren (nur Crons reparieren + dokumentieren)

Crons korrekt installieren, Runbooks schreiben, sonst nichts.

- Pro: minimaler Aufwand
- Contra: löst das dominante Risiko (Ein-Host) **nicht**; Backups bleiben auf dem
  Daten-Host; Drift kehrt ohne Enforcement zurück (bewiesen durch risk-hub-Pfad-Drift)

### Option B — Offsite by construction: Hetzner Storage Box + restic + Backup-Meter ✅ (vorgeschlagen)

Ein nächtlicher Backup-Pfad pro Host: bestehende pg_dump-Skripte bleiben Erzeuger;
ein einheitlicher `restic`-Push verschlüsselt nach **Hetzner Storage Box** (BX11,
~4 €/Monat, EU). Gesundheit wird **gemessen, nicht behauptet**: ein scheduled
GitHub-Actions-Job (`backup-meter`) prüft täglich Offsite-Snapshot-Alter + -Anzahl
je App gegen die Soll-Tabelle (§5) und schlägt bei Verletzung Alarm (Issue + Discord).
Restore wird **geprobt**: quartalsweise Restore-Feuerübung gegen Wegwerf-Container
(analog Exit-Feuerübung KONZ-002).

- Pro: adressiert Ein-Host-Risiko direkt; verschlüsselt (Zero-Knowledge gegenüber
  Storage); Dedup hält Kosten flach; Enforcement statt Doku; nutzt vorhandene Skripte
- Contra: neue Komponente (restic) + Storage-Box-Vertrag; Restore-Übung kostet
  ~1 h/Quartal

### Option C — Hetzner Server-Snapshots als Primärmechanismus

Tägliche Host-Snapshots via Hetzner API (`HCLOUD_TOKEN` existiert, ADR-045).

- Pro: trivial zu aktivieren, ganzer Host inkl. Volumes
- Contra: Snapshots liegen im selben Hetzner-Projekt (Account-Kompromittierung =
  Backups weg); kein applikationskonsistentes DB-Backup (Crash-Konsistenz);
  Restore-Granularität nur „ganzer Host"; Kosten skalieren mit Disk-Größe
- Verdikt: **Ergänzung** (Layer 2, wöchentlich), nicht Ersatz für Option B

### Option D — Managed Backup-Service / externes Tooling (Borgmatic-SaaS, Velero, …)

- Contra: neue Vendor-Beziehung + Lernkurve für 2-Personen-Team; Overkill für
  Single-Host-Docker-Compose-Flotte. Abgelehnt (right-sizing).

## Entscheidung (vorgeschlagen)

**Option B als Pflicht-Baseline, Option C als wöchentlicher Layer 2.** Konkret:

1. **Backup-Erzeugung (bleibt dezentral):** pro App das vorhandene pg_dump-Skript;
   Lücken schließen: mcp-hub-Skript neu, risk-hub um MinIO-Volume erweitern,
   risk-hub-Cron-Pfad fixen.
2. **Offsite-Transport (neu, einheitlich):** ein `restic`-Wrapper pro Host
   (`platform/deployment/scripts/offsite-backup.sh`), nächtlich, Ziel Hetzner
   Storage Box (separater Credential-Satz in `~/.secrets`, **nicht** der
   Hetzner-Cloud-Token — Blast-Radius-Trennung). Retention: 7 daily / 4 weekly /
   6 monthly (restic forget policy).
3. **Installation by construction:** Cron-Installation wandert in das bestehende
   Deploy-Tooling (deploy-remote.sh bzw. Stack-Setup) — kein manueller scp-Schritt mehr.
4. **Backup-Meter (Enforcement):** scheduled Workflow in platform prüft täglich
   via restic-API: jüngster Snapshot je App < 26 h alt, Anzahl ≥ Soll. Verletzung →
   GitHub-Issue (label `backup-violation`) + Discord. Der Meter ist die
   *Confirmation* dieses ADRs — ohne grünen Meter gilt das ADR als nicht implementiert.
5. **Restore-Beweis:** ein Restore-Runbook je App-Klasse
   (`docs/runbooks/db-restore.md`) + **quartalsweise Feuerübung**: jüngstes
   risk-hub-Backup in Wegwerf-Postgres restoren, Smoke-Query, Protokoll nach
   `~/shared/`. Erste Übung ist Akzeptanzkriterium (§7 G3).
6. **Pre-Deploy-Backup wird blocking** für Prod-Deploys (deploy-remote.sh:
   `continuing` → hard fail), Bypass nur via explizitem `skip_backup`-Input.

### RPO/RTO-Soll (Baseline)

| Klasse | Apps | RPO | RTO | Mechanismus |
|---|---|---|---|---|
| Kundenprodukt | risk-hub (inkl. MinIO) | 24 h | 4 h | daily pg_dump+tar → restic offsite |
| Plattform-kritisch | dev-hub, mcp-hub (pgvector), Authentik, Outline, doc-hub | 24 h | 1 Arbeitstag | daily → restic offsite |
| Übrige Prod-Hubs | travel-beat, weltenhub, pptx-hub, … | 24 h | best effort | daily → restic offsite |
| Host-Ebene (Layer 2) | ganzer CPX52 | 7 d | 1 Arbeitstag | wöchentl. Hetzner-Snapshot, keep 2 |

## Konsequenzen

**Positiv:** Ein-Host-Totalverlust verliert seinen Schrecken (RPO 24 h offsite);
Backup-Gesundheit wird erstmals messbar; Restore ist bewiesen statt behauptet;
ADR-142/143/144 behalten Gültigkeit (werden Erzeuger-Schicht, dieses ADR ergänzt
Transport+Enforcement — Amendment-Verweise nachtragen).

**Negativ:** ~4 €/Monat Storage Box + Snapshot-Kosten; restic als neue Komponente;
quartalsweise Übungs-Aufwand (~1 h); blocking Pre-Deploy-Backup kann Deploys
verzögern (bewusster Trade-off).

**Neutral:** Per-Tenant-Restore (ADR-072-Trade-off) bleibt ungelöst — bewusst out
of scope; Government-spezifische Standortanforderungen folgen ggf. als eigenes
Amendment, wenn ttz-lif/meiki-lra-Workloads produktiv werden.

## Confirmation (maschinell prüfbar)

1. `backup-meter`-Workflow existiert in platform, läuft täglich, Status grün
   (jüngster Offsite-Snapshot je Soll-App < 26 h).
2. `restic snapshots` listet ≥ 1 Snapshot je App der Soll-Tabelle.
3. deploy-remote.sh schlägt bei fehlgeschlagenem Pre-Deploy-Backup hart fehl
   (Testcase im Repo).
4. Restore-Feuerübungs-Protokoll < 100 Tage alt in `~/shared/`
   (Meter prüft Datei-Existenz + Datum via Checkliste im Quartals-Issue).

## Offene Gates vor Accept (§7)

| Gate | Inhalt | Owner | billigster Check |
|---|---|---|---|
| G1 | Offsite-Ziel bestätigen (Storage Box BX11 vs. Alternativen; Kostenfreigabe ~5 €/M) | Achim | Hetzner-Bestellseite |
| G2 | Prod-Realität verifizieren: laufen die cron.daily-Backups heute? Ist `/opt/backups/*` befüllt? | Achim/ich | 1× `ssh hetzner-prod 'ls -la /etc/cron.daily/ /opt/backups/'` |
| G3 | Erste Restore-Feuerübung grün (risk-hub-Dump → Wegwerf-Postgres) | ich (gated) | — |

## Rollout (nach Accept)

| Phase | Inhalt | Aufwand |
|---|---|---|
| 1 | G2-Verifikation + risk-hub-Fixes (Cron-Pfad, MinIO, mcp-hub-Skript) | 2 h |
| 2 | Storage Box + restic-Wrapper + Cron-Installation via Deploy-Tooling | 3 h |
| 3 | backup-meter-Workflow + Discord-Alert | 2 h |
| 4 | Restore-Runbook + erste Feuerübung (G3) | 2 h |
| 5 | Pre-Deploy-Backup blocking + wöchentl. Hetzner-Snapshot (Layer 2) | 1 h |

## References

- ADR-008 (archiviert): restic + Storage Box — konzipiert, nie implementiert
- ADR-045: Secrets-Management (Credential-Ablage für restic-Repo-Key)
- ADR-072: shared-schema Trade-off „kein per-Tenant-Backup"
- ADR-090 v4: „DB-Backup vor jeder Migration" (Pre-Deploy-Pfad)
- ADR-142/143/144: Stack-Backups Authentik/Outline/doc-hub (werden Erzeuger-Schicht)
- ADR-157: Ein-Prod-Host-Topologie (CPX52)
- ADR-218: RPO/RTO als Doku-Pflichtfeld (KRITIS-Profil)
- ADR-234/235: Derived-Invariant-/Meter-Philosophie
- Inventar-Evidenz: 3-Repo-ADR-Analyse + Backup-Inventur 2026-06-10 (Session-Protokoll)
