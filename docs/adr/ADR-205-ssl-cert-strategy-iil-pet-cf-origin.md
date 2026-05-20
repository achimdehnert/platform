---
status: accepted-with-caveats
date: 2026-05-14
decision-makers: [Achim Dehnert]
review: "solo-decision — no independent review; same engineer who built the broken renewal pipeline (dns-hetzner-for-CF-zones, 14/14 failure on 2026-05-14) wrote this fix and this ADR"
implementation_status: partial
related: [ADR-198]
revision: v3 (zwei Devil's-Advocate-Pässe selber Tag)
---

# ADR-205: TLS-Termination & Cert-Strategie auf prod

## Kern-Prinzip

> **Die Cert-Chain MUSS verifizierbar sein durch jeden Client, der legitim ohne Proxy-Transformation auf den Endpunkt zugreift.**

Alles Operative leitet sich daraus ab:
- Externer Direct-Access erlaubt? → browser-trusted Cert nötig → Let's Encrypt (Konfig B)
- Nur via CF Proxy erreichbar? → CF Origin Cert akzeptabel (Konfig A) ODER kein Origin-Cert (Konfig C, Tunnel)
- Niemand soll direkt → CF Tunnel (Konfig C, präferiert)

## Status

**Accepted with caveats**. Implementation **partial** — Akut-Hotfix (Renewal-Pipeline funktional, Monitoring deployed) ist live, aber CF-Key-Backup und Tunnel-Migration sind offen. Status wechselt auf `accepted` wenn beide TODOs in "Implementation Status" geschlossen sind.

**Solo-decision** (Achim Dehnert, alleinig). Reviewer-Pool aktuell n=1. Diese ADR ist mein zweiter Devil's-Advocate-Pass über meine eigene v1 — wo kritische Schwachstellen geblieben sind, fängt sie das Verfahren strukturell nicht ab. Bei nächster Audit-Gelegenheit (externes Ohr) ist sie zu re-reviewen.

## Context

Am 2026-05-14 wurde `schutztat.de` als ablaufender Origin-Cert gemeldet. Discovery: 14 von ~30 LE-Certs auf prod hatten kaputte Renewal-Configs — `webroot/nginx/standalone` scheiterten hinter Cloudflare, `dns-hetzner` schrieb TXT-Records in den falschen DNS (Zonen liegen authoritativ bei Cloudflare). Drei TLS-Modelle liefen unkoordiniert: nginx+CF-Origin (23 Vhosts), nginx+LE (14), self-signed `default.crt` (3 — Bug, direct access nicht vertrauenswürdig).

Inkonsistenz erschwerte Debugging, sechs Wochen unentdeckte Renewal-Failures vor Ablauf-Notfall.

Diese ADR ist v3 derselben Datei am selben Tag: v1 (TLD-basierte Trennung) und v2 (Pseudo-orthogonale Drei-Layer) hatten beide strukturelle Schwächen — v3 baut auf einem klaren Kern-Prinzip auf statt Regelliste.

## Decision

Drei akzeptierte **Konfigurationen** (nicht "Layer" — sie sind exklusiv, nicht orthogonal kombinierbar):

| Konfig | Termination | Origin-Cert | Wann | Status |
|---|---|---|---|---|
| **A** | nginx auf prod:443 | CF Origin CA (`/etc/nginx/ssl/cf-origin/iil-pet.crt`, *managed dependency, CF-revocable*) | Bestehende `*.iil.pet` (23 Vhosts) | Grandfathered |
| **B** | nginx auf prod:443 | Let's Encrypt (browser-trusted, via dns-cloudflare) | Externe Domains mit Direct-Access (14 Vhosts) | Standard |
| **C** | Cloudflare Edge → cloudflared Tunnel → origin:non-public-port | CF Edge-Cert (browser-trusted, CF-managed); Origin braucht **keinen** eigenen Cert (mTLS via Tunnel) | NEUE Services + zukünftige Migration von A | Präferiert für greenfield |

### Konfig-Wahl-Algorithmus (für Code-Review, neue PRs)

```
1. Soll Direct-Origin-Access (kein CF Proxy) möglich sein?
   ja  → Konfig B (LE/dns-cloudflare)
   nein → weiter zu 2
2. Existiert der Service schon mit Konfig A?
   ja  → A bleibt, NICHT migrieren ohne explizite Tunnel-Migration-PR
   nein → Konfig C (Tunnel)
```

### Renewal-Mechanik (gilt nur für Konfig B)

- DNS-01 Authenticator MUSS authoritativem NS-Provider matchen (heute alle CF → `dns-cloudflare`)
- Propagation-Wait: **120s Default** in `/etc/letsencrypt/cli.ini` (war 60s in renewal/*.conf, hand-tuned mit N=1 — Puffer verdoppelt für Robustheit gegen CF-API-Latency-Spitzen)
- HTTP-01 hinter CF: **nicht akzeptiert** (auch nicht mit Configuration Rule — Komplexität nicht gerechtfertigt, DNS-01 funktioniert und supports Wildcards)

## Operative Constraints (abgeleitet aus Kern-Prinzip)

1. `authenticator = standalone` ist verboten — Port-Konflikt mit nginx, nicht recoverable im Renewal-Window.
2. Self-signed Certs nur als nginx `default_server` Catch-All mit `return 444` (Reject). Niemals named vhost.
3. Konfig-A-Vhost MUSS hinter orange-cloud (CF Proxy) hängen — externer Direct-Access würde Kern-Prinzip verletzen.
4. Konfig-C-Origin MUSS auf cloudflared Tunnel-Socket lauschen, nicht auf public:443.

## Monitoring — drei Signal-Klassen + Health-Check

`/opt/scripts/cert-expiry-check.sh` (cron 06:30, läuft als root):

1. **Trailing**: Cert <14d Restlaufzeit
2. **Leading (Cert-Logik)**: `letsencrypt.log` + rotierte `letsencrypt.log.{1,2,3}` zeigen "Failed to renew X" ohne nachfolgendes "Certificate is saved at .../X/fullchain.pem"; renewal/*.conf für X muss noch existieren
3. **Leading (Mechanik)**: `systemctl show certbot.timer -p LastTriggerUSec` — wenn LastTrigger >36h alt → Alert (Timer tot)
4. **Static**: CF Origin Cert-File existiert + ist (theoretisch) gültig

Alert via `DISCORD_WEBHOOK_URL` aus `/etc/cert-monitor.env` (cron sourced explicitly via shell line). Fallback: cron-mail (root mailbox).

## CF-Account Risk & Disaster Recovery

**Konzentriertes Risiko**: Modell A + C konzentrieren Trust auf einen Cloudflare-Account. Token-Kompromittierung → MITM für 23+ Services möglich. Modell B (externe Domains) bleibt unabhängig.

**Mitigation-Stand 2026-05-14**:
- ✅ `/root/.secrets/cloudflare.ini` chmod 600, root-only
- ✅ Token-Scope vermutlich Zone:DNS:Edit (NICHT verifiziert via `curl -H "Authorization: Bearer $TOKEN" https://api.cloudflare.com/client/v4/user/tokens/verify` — **TODO**)
- ⬜ **TODO**: 2FA-Status auf CF-Account verifizieren
- ⬜ **TODO**: `/etc/nginx/ssl/cf-origin/iil-pet.{crt,key}` Backup nach `/root/backups/cf-origin/cf-origin-key-YYYYMMDD.tar.gz.gpg` (GPG-symmetric, Passphrase im Passwort-Manager)
- ⬜ **TODO**: CF Origin Cert Re-Issue-Runbook unter `~/github/platform/docs/runbooks/cf-origin-cert-restore.md`
- ⬜ **TODO**: Tunnel-Token-Backup analog

## Implementation Status (2026-05-14, ehrlich)

### Done
- 18 LE-Certs auf `dns-cloudflare` migriert
- 6 `*.iil.pet` Vhosts auf CF Origin Cert (Konfig A) angeglichen
- 25 ungenutzte LE-Certs entfernt (`certbot delete`)
- `certbot renew --dry-run`: 14/14 success
- Monitoring v2 deployed mit Leading+Trailing+Timer-Check
- Backup geänderter Vhosts: `/etc/nginx/sites-enabled.bak-2026-05-14/`
- Discord-Webhook über `/etc/cert-monitor.env` von cron geladen
- Global propagation default 120s in `/etc/letsencrypt/cli.ini`

### Open (blockiert "implementation_status: implemented")
- ⬜ CF-Token-Scope verifizieren (`curl …/user/tokens/verify`)
- ⬜ 2FA-Audit auf CF-Account
- ⬜ Cert-Key-Backup-Cron für `/etc/nginx/ssl/cf-origin/`
- ⬜ Runbook `cf-origin-cert-restore.md`
- ⬜ Migrations-Plan-ADR für **Konfig A → Konfig C** (ADR-206 — wird gestubbed, siehe unten)

### Tunnel-Migration: konkreter Trigger statt vage
Modell-A → Modell-C-Migration startet sobald:
- CF-Key-Backup-Workflow läuft (oben), **UND**
- Tunnel-Routing für mindestens einen niedrig-Risk Vhost (`docs.iil.pet` oder `learn.iil.pet`) als Pilot verprobt ist

Wenn diese beiden zwei Wochen nach ADR-Datum (Deadline 2026-05-28) nicht angefangen sind, ADR re-reviewen — ist Konfig A dann doch der Dauer-Zustand?

## Alternatives Considered

### LE Wildcard `*.iil.pet`
Verworfen für Bestand (Konfig-A-Vhosts laufen, keine Trigger zur Migration). Falls Migration weg von A: direkt nach C (Tunnel löst Cert-Verwaltung + Surface-Reduktion gleichzeitig), nicht LE-Wildcard als Zwischenschritt.

### Caddy statt nginx (auto-LE)
Verworfen — disruptive Migration von ~30 Vhosts; Tunnel-Path adressiert dasselbe (Cert-Auto-Management) mit geringerem Blast-Radius.

### ACME-DNS (zentraler Challenge-Helper)
Verworfen für heute — gewinnt nur bei mehreren DNS-Providern parallel. Alle Zonen bei CF → Overkill.

### CF Origin Cert auch für externe Customer-Domains
Verworfen — verletzt Kern-Prinzip (Direct-Access nicht browser-trusted).

### Dual-Cert SNI-Selection (RSA via LE + CF Origin parallel, SNI-Auswahl)
Erwogen für Robustness gegen LE-Outage oder CF-Outage. Verworfen für jetzt — Komplexität in nginx-Config nicht durch echtes Risiko (LE und CF haben beide hohe SLAs) gerechtfertigt. Wieder aufnehmen wenn LE oder CF einen ≥4h Outage hat, der uns trifft.

### nginx ganz weglassen (Tailscale für intern, CF Workers für extern)
Erwogen, aber radikal — neue Plattform-Entscheidung, nicht Cert-ADR. Out-of-scope.

## Out-of-Scope (referenziert konkrete Folge-Arbeit, kein Phantom)

- **ADR-206**: Wird **als Stub angelegt** mit `status: proposed`, leerem Body — Existenz-Beweis dass das Thema getrackt ist, kein Phantom-Verweis. Konkretisiert nach Pilot-Tunnel-Migration.
- **CF-Account-Hardening Runbook**: Pfad `~/github/platform/docs/runbooks/cf-account-hardening.md` — wird mit den TODOs aus DR-Section gefüllt.
- **INDEX.md-Refresh**: "Next free ADR number: 189" ist stale (real ist 205→206). Separater Aufräum-Commit.

## Why This Could Still Be Wrong

Aufzählung der Annahmen, die ich nicht verifiziert habe und die diese ADR auf falscher Basis stellen würden:

- **CF Token-Scope** unbestätigt — falls breiter als Zone:DNS:Edit, ist Mitigation-Story falsch.
- **CF Origin CA Policy-Stabilität** — wenn CF die Origin CA deprecaten, müssen wir migrieren, egal was die ADR sagt.
- **Tunnel-Performance vs nginx-direkt** ungemessen — falls Tunnel-Latency unzumutbar, ist Konfig C nicht das strategische Ziel.
- **dns-cloudflare 120s Propagation** N=1+1, kein Long-Run-Sample — kann immer noch flaken.
- **letsencrypt.log Format** zwischen certbot-Versionen — Skript matched aktuelle Strings, kann durch certbot-Update brechen.
