---
status: proposed
date: 2026-05-14
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-205]
---

# ADR-206: Migration `*.iil.pet` von Konfig A (nginx + CF Origin Cert) nach Konfig C (cloudflared Tunnel)

## Status

**Proposed — Stub.** Konkretisiert nach erfolgreichem Pilot-Tunnel (siehe ADR-205 → "Tunnel-Migration: konkreter Trigger").

Existiert als ADR-Nummer um Phantom-Referenz aus ADR-205 zu vermeiden.

## Context

ADR-205 etabliert drei Konfigurationen (A/B/C) und benennt Konfig C (cloudflared Tunnel) als präferierten Endzustand für `*.iil.pet`. ADR-205 hat Konfig A (nginx + CF Origin Cert) als grandfathered, nicht-aktiv-zu-migrieren markiert — diese ADR plant die aktive Migration, sobald Voraussetzungen erfüllt.

## Trigger zur Konkretisierung (aus ADR-205)

- CF-Key-Backup-Workflow läuft (`/etc/nginx/ssl/cf-origin/*` regelmäßig nach `/root/backups/cf-origin/` mit GPG)
- Tunnel-Routing für mindestens einen niedrig-Risk Vhost als Pilot (Kandidat: `docs.iil.pet` oder `learn.iil.pet`)

Wenn beide bis 2026-05-28 nicht angefangen sind → ADR-205 + diese ADR re-reviewen.

## Open Questions (zu beantworten beim Konkretisieren)

1. Welcher Vhost als Pilot? (Nutzungs-Daten + Risk-Profile)
2. Performance-Baseline messen: aktuelle nginx-direkt-Termination vs. Tunnel-Termination (Latency, Throughput, p99)
3. Tunnel-Routing-Topologie: Single Tunnel mit Pfad-Matching oder Tunnel-pro-Service?
4. Rollback-Plan: was passiert wenn Tunnel mid-Migration crashed?
5. Auth-Modell: Cloudflare Access für intern-only Vhosts?

## Decision (placeholder)

TBD — diese ADR wird gefüllt sobald Trigger erfüllt sind.
