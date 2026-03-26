---
status: "proposed"
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related:
  - ADR-146  # risk-hub → DMS Audit Trail (Vorgänger-Integration)
  - ADR-144  # Paperless-ngx doc-hub
  - ADR-045  # Secrets Management
  - ADR-072  # Multi-Tenancy
staleness_months: 12
drift_check_paths:
  - src/dms_inbound/
  - scripts/samba/
---

# ADR-149: Adopt SMB-over-WireGuard als Inbound-Scan-Kanal für d.velop DMS mit HP PageWide E58650 und Fujitsu iX1600

## Metadaten

| Attribut          | Wert                                                                                              |
|-------------------|---------------------------------------------------------------------------------------------------|
| **Status**        | Proposed                                                                                          |
| **Scope**         | service + infrastructure                                                                          |
| **Erstellt**      | 2026-03-25                                                                                        |
| **Autor**         | Achim Dehnert                                                                                     |
| **Reviewer**      | –                                                                                                 |
| **Supersedes**    | –                                                                                                 |
| **Superseded by** | –                                                                                                 |
| **Relates to**    | ADR-146 (risk-hub DMS Audit Trail), ADR-144 (Paperless-ngx), ADR-045 (Secrets), ADR-072 (Tenancy) |

## Repo-Zugehörigkeit

| Repo       | Rolle    | Betroffene Pfade / Komponenten                                           |
|------------|----------|--------------------------------------------------------------------------|
| `dms-hub`  | Primär   | `src/dms_inbound/` (neu), `docker-compose.yml` (Samba-Container)         |
| `platform` | Referenz | `docs/adr/`, WireGuard-Konfiguration (`/etc/wireguard/wg0.conf`)         |
| `mcp-hub`  | Sekundär | zukünftiger `dvelop_mcp.py` kann Inbound-Status abfragen (ADR-147)       |

---

## Decision Drivers

- **Zwei physisch unterschiedliche Scanner** am Landratsamt: MFP HP PageWide Color Flow
  E58650 (Büroetage, Netz-gebunden) und Fujitsu iX1600 (Dokumentenscanner, USB/Netz,
  Akteneinscannen). Beide müssen in **denselben** d.velop-Inbound-Kanal einspeisen.
- **WireGuard bereits installiert** auf der Hetzner-Produktionsinfrastruktur und der
  Fritzbox des Landratsamts — kein neuer VPN-Stack nötig.
- **SMB ist der gemeinsame Nenner**: HP EWS und d.velop Inbound Scan sprechen beide
  nativ SMB/CIFS für Netzordner-Zugriff; der iX1600 kann ebenfalls in SMB-Freigaben
  schreiben (PaperStream NX Manager oder Hot-Folder-Profil).
- **d.velop Inbound Scan** ist die native Importschnittstelle von d.velop DMS für
  dateibasierte Dokumenteneinlieferung mit Metadaten-Mapping und OCR-Nachbearbeitung.
- **Kein eigenständiger Scan-PC** am Scanner erforderlich: HP E58650 ist netzwerkfähig
  und schreibt selbst in den SMB-Ordner; iX1600 kann über PaperStream NX Manager
  headless betrieben werden.
- **Sicherheit**: Kein Scanner-Traffic über offenes Internet; ausschließlich
  VPN-verschlüsselt über WireGuard-Tunnel (kein SMBv1, kein open share).

---

## 1. Context and Problem Statement

### 1.1 Scanner-Inventar am Landratsamt

| Gerät | Typ | Interface | Max. Scangeschwindigkeit | Besonderheiten |
|-------|-----|-----------|--------------------------|----------------|
| **HP PageWide Color Flow E58650z** | MFP (Druck/Kopie/Scan/Fax) | Gigabit Ethernet | bis zu 70 ipm (A4, beidseitig) | 100-Blatt ADF, 8"-Touchscreen, eingebettetes OCR, EWS-Konfiguration |
| **Fujitsu iX1600** | Dedizierter Dokumentenscanner | USB 3.2 / WLAN (optional) | bis zu 40 ppm / 80 ipm | PaperStream IP, ABBYY FineReader Engine, Ultraschall-Doppeleinzugserkennung |

### 1.2 Ist-Situation

Das Landratsamt scannt derzeit in lokale Windows-Freigaben. Von dort erfolgt
keine automatische Weiterleitung in das d.velop DMS — Mitarbeitende müssen
Dokumente manuell in d.velop hochladen. Dies ist fehleranfällig, zeitintensiv
und erzeugt eine Unterbrechung der Revisionskette.

### 1.3 Zielarchitektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LANDRATSAMT (on-premises)                                                  │
│                                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐                      │
│  │ HP PageWide E58650   │    │ Fujitsu iX1600        │                      │
│  │ (MFP, Gigabit LAN)   │    │ (USB → Scan-PC oder  │                      │
│  │                      │    │  PaperStream NX Mgr)  │                      │
│  │ EWS → Save to        │    │ Hot-Folder-Profil     │                      │
│  │ Network Folder       │    │ → SMB-Freigabe        │                      │
│  └──────────┬───────────┘    └──────────┬────────────┘                      │
│             │  SMBv2/v3                 │  SMBv2/v3                         │
│             └──────────────┬────────────┘                                   │
│                            ▼                                                │
│               ┌────────────────────────┐                                   │
│               │  Samba-Server (Linux)  │                                   │
│               │  oder Windows-Share    │                                   │
│               │  \\<ip>\scan-inbound\  │                                   │
│               └────────────┬───────────┘                                   │
│                            │  WireGuard Tunnel (UDP 51820)                 │
└────────────────────────────┼────────────────────────────────────────────────┘
                             │
                    [Fritzbox → Hetzner VM]
                             │
┌────────────────────────────┼────────────────────────────────────────────────┐
│  HETZNER CLOUD (iil-Platform-Stack)                                         │
│                            ▼                                                │
│               ┌────────────────────────┐                                   │
│               │  dms-hub               │                                   │
│               │  Samba-Client-Mount    │                                   │
│               │  /mnt/scan-inbound/    │  ← oder: Samba auf dms-hub selbst │
│               └────────────┬───────────┘                                   │
│                            │                                                │
│                            ▼  (Celery Beat alle 30s)                        │
│               ┌────────────────────────┐                                   │
│               │  InboundScanProcessor  │                                   │
│               │  (dms_inbound app)     │                                   │
│               │  - Datei-Hash prüfen   │                                   │
│               │  - Metadaten ableiten  │                                   │
│               │  - d.velop Upload      │                                   │
│               │  - Datei archivieren   │                                   │
│               └────────────────────────┘                                   │
│                            │  REST API                                      │
│                            ▼                                                │
│               ┌────────────────────────┐                                   │
│               │  d.velop Cloud         │                                   │
│               │  https://iil.d-velop.cloud/                                │
│               │  Kategorie: INBOUND_SCAN                                   │
│               └────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Hardware-Technische Rahmenbedingungen

#### HP PageWide Color Flow E58650z

Das Gerät verfügt über einen 100-Blatt ADF mit Single-Pass-beidseitigem Scannen, ein 8-Zoll-Farb-Touchdisplay, einen Flachbett-Scanner bis DIN A4+, sowie einen eingebetteten OCR-Prozessor für Searchable-PDF-Ausgabe.

Unterstützte Ausgabeformate: PDF, JPEG, TIFF, MTIFF, XPS, PDF/A sowie (E58650z) Searchable PDF, Searchable PDF/A, TEXT (OCR), RTF (OCR), HTML (OCR), CSV (OCR) bei Auflösungen von 75 bis 600 dpi.

**SMB-Konfiguration über EWS (Embedded Web Server):**

Der Drucker verfügt über eine "Save to Network Folder"-Funktion, die über den Embedded Web Server (EWS) konfiguriert wird. Die Funktion erfordert eine aktive Netzwerkverbindung und unterstützt einen Basic Setup Wizard sowie eine erweiterte Konfiguration.

HP deaktiviert SMBv1 standardmäßig und unterstützt SMBv2 und SMBv3 — dies ist sicherheitstechnisch korrekt und kompatibel mit einem modernen Samba-Server auf Linux.

**Kritische Konfigurationshinweise (aus Community-Erfahrungen):**

Empfohlene Konfiguration: nur SMBv3 im EWS aktivieren (`NETWORK → Advanced Settings → SMB`), Firmware auf aktuellsten Stand bringen. Benutzername im UPN-Format (`user@domain`) statt `domain\user` verwenden. Benutzername darf maximal 6 Zeichen lang sein (bekannte EWS-Limitation bei älteren Firmware-Versionen).

#### Fujitsu iX1600

- **Interface**: USB 3.2 Gen 1 (primär) + WLAN 802.11ac (optional, für PaperStream NX Manager)
- **Scangeschwindigkeit**: 40 ppm einseitig / 80 ipm beidseitig bei 300 dpi (A4 Farbe)
- **ADF-Kapazität**: 50 Blatt
- **OCR-Engine**: ABBYY FineReader Engine 12 (in PaperStream IP integriert)
- **Software**: PaperStream IP (TWAIN/ISIS-Treiber) + PaperStream Capture / PaperStream NX Manager
- **SMB-Integration**: Über PaperStream Capture "Destination: Network Folder" oder
  PaperStream NX Manager Hot-Folder → automatischer Upload in SMB-Freigabe

**Unterschied zum HP**: Der iX1600 ist kein netzwerkfähiger Scanner im EWS-Sinne.
Er benötigt einen verbundenen PC (oder PaperStream NX Manager auf einem Server),
der den Scan entgegennimmt und in den SMB-Zielordner schreibt.

---

## 2. Considered Options

### Option A — SMB-over-WireGuard + Samba + d.velop Inbound Scan (empfohlen)

Beide Scanner schreiben in eine gemeinsame SMB-Freigabe, die über den bestehenden
WireGuard-Tunnel zum Hetzner-Server erreichbar ist. Ein Celery-Beat-Task prüft
das Eingangsverzeichnis alle 30 Sekunden, überträgt neue Dateien per REST an
d.velop und archiviert verarbeitete Dateien.

### Option B — d.velop FTP-Eingang

HP E58650 und iX1600 senden direkt per FTP an einen FTP-Server (d.velop Inbound
FTP-Connector). Kein SMB nötig.

### Option C — E-Mail-basierter Eingang (Scan-to-Email → d.velop Inbound Mail)

Scanner senden PDFs per SMTP. d.velop Inbound E-Mail verarbeitet den Anhang.

### Option D — HP EWS direkt mit d.velop Cloud verbinden (SharePoint-Connector)

Der HP E58650z unterstützt neben Network Folder auch "Save to SharePoint". Da d.velop einen SharePoint-Connector anbietet, könnte der HP direkt in SharePoint Online ablegen und d.velop holt von dort. Der iX1600 müsste separat integriert werden.

### Option E — Paperless-ngx als Zwischenstufe (bestehende ADR-144-Integration)

Beide Scanner → Paperless-ngx (bestehende Infrastruktur, SMB-Consume) →
manueller oder automatisierter Export aus Paperless → d.velop. Zweistufiger Prozess.

---

## 3. Decision Outcome

**Gewählt: Option A** — SMB-over-WireGuard + Samba + dms-hub InboundScanProcessor.

### 3.1 Begründung

**Option A** ist die einzige Lösung, die beide Scanner unter einem einheitlichen
Pfad ohne Sonderlösungen integriert:

| Kriterium | Option A (SMB+WG) | Option B (FTP) | Option C (E-Mail) | Option D (SharePoint) | Option E (Paperless) |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Beide Scanner einheitlich | ✅ | ✅ | ✅ | ❌ (iX1600 extra) | ✅ |
| WireGuard bereits vorhanden | ✅ | ❌ neu | ❌ neu | ❌ neu | ⚠️ teil |
| Keine offenen Ports nötig | ✅ | ❌ | ❌ | ❌ | ✅ |
| d.velop-native Integration | ✅ Inbound Scan | ✅ FTP | ✅ Mail | ⚠️ Umweg | ❌ doppelt |
| Metadaten-Steuerung | ✅ Ordner-basiert | ⚠️ begrenzt | ❌ schlecht | ⚠️ begrenzt | ❌ verloren |
| Kein Mailserver nötig | ✅ | ✅ | ❌ SMTP | ✅ | ✅ |
| Plattform-Kontrolle über Verarbeitungsstatus | ✅ Celery + DB | ❌ kein Feedback | ❌ kein Feedback | ❌ kein Feedback | ⚠️ indirekt |
| Revisionssicherer Audit-Trail | ✅ InboundRecord | ❌ | ❌ | ❌ | ❌ |

**Option B (FTP)** scheidet aus: FTP ist unverschlüsselt (ohne FTPS), benötigt
einen offenen eingehenden Port auf der Hetzner-VM und ist deutlich schwieriger
abzusichern als WireGuard-SMB.

**Option C (E-Mail)** ist unzuverlässig für Produktionsbetrieb: SMTP-Grenzgrößen
(typisch 10–25 MB), keine Verarbeitungsbestätigung, schlechte Metadaten-Steuerung.

**Option D (SharePoint)** erfordert eine Microsoft 365-Lizenz und ist nur für
den HP E58650z verfügbar — der iX1600 müsste separat integriert werden. Außerdem
entsteht eine externe SaaS-Abhängigkeit außerhalb der Plattform-Governance.

**Option E (Paperless)** wäre ein Zwei-Schritt-Prozess mit manuellem Eingriff
oder komplexer Automatisierung. Paperless-ngx ist für IIL-interne Zwecke
(ADR-144) — Behördendokumente sollten nicht durch ein internes System laufen.

### 3.2 Scanner-spezifische Integrationswege

```
HP PageWide E58650z                    Fujitsu iX1600
        │                                     │
        │  EWS → Save to Network Folder       │  PaperStream Capture
        │  SMBv2/v3                           │  (auf Scan-PC oder
        │  Target: \\<wg-ip>\scan-inbound\   │  NX Manager Server)
        │  Subfolder: hp-e58650\             │  Hot-Folder → SMBv2/v3
        │                                     │  Subfolder: ix1600\
        └──────────────────┬──────────────────┘
                           ▼
              \\<wg-server-ip>\scan-inbound\
              (Samba auf dms-hub oder separatem Mount)
```

**Wichtig: Separate Unterordner** je Scanner ermöglichen Quellentracking
im `InboundScanRecord` (Feld `scanner_source`).

---

## 4. Pros and Cons of the Options

### Option A — SMB-over-WireGuard ✅

**Pro:**
- WireGuard bereits auf Fritzbox und Hetzner-VM installiert und betrieben
  (kein neuer VPN-Stack, nur neue Peer-Konfiguration für Landratsamt-Client)
- SMBv2/v3: kein veraltetes Protokoll, keine Sicherheitskompromisse
- Samba auf Linux: vollständig konfigurierbar, kein Windows-License-Overhead
- Einheitlicher Eingangskanal für beide Scanner — Metadaten-Ableitung aus
  Ordnerstruktur (`/<kategorie>/<scanner>/`)
- `InboundScanRecord` bietet vollständigen Audit-Trail: Dateiname, SHA-256-Hash,
  Erkannte Kategorie, d.velop-Dokument-ID, Verarbeitungszeitpunkt
- Celery-Beat alle 30s: kein Polling-Overhead, zuverlässig
- Verarbeitete Dateien werden in `processed/` verschoben (nicht gelöscht) —
  Fallback bei d.velop-Fehler immer möglich

**Con:**
- Samba-Konfiguration auf Linux erfordert einmaligen Einrichtungsaufwand
- WireGuard Peer-Konfiguration für Landratsamt-Client muss manuell angelegt werden
- PaperStream NX Manager für iX1600 benötigt Windows-Rechner oder VM
  am Landratsamt (Alternative: PaperStream Capture auf bestehendem PC)
- SMB über WireGuard fügt ~2–5 ms Latenz hinzu (irrelevant für Scanner-Workflows)

### Option B — FTP ❌

**Pro:** Einfaches Protokoll, direkt von HP EWS unterstützt.

**Con:**
- Benötigt offenen eingehenden Port auf Hetzner-VM (Sicherheitsrisiko)
- Ohne FTPS: Klartext-Übertragung von Behördendokumenten (DSGVO-Problem)
- FTPS-Zertifikatsverwaltung auf dem HP EWS ist komplex
- Kein Audit-Trail auf Platform-Seite

### Option C — E-Mail ❌

**Con:**
- Dateigrößenlimit typisch 10–25 MB: für mehrseitige Farb-PDFs unzureichend
- SMTP-Relay-Konfiguration erforderlich
- d.velop Inbound Mail ist asynchron mit unbekannter Verarbeitungszeit
- Kein strukturiertes Metadaten-Mapping über E-Mail-Header möglich

### Option D — SharePoint Connector ❌

**Con:**
- Microsoft 365-Lizenz + SharePoint Online erforderlich
- Fujitsu iX1600 unterstützt keinen direkten SharePoint-Upload
- Externe SaaS-Abhängigkeit außerhalb der Plattform-Governance
- d.velop SharePoint-Connector muss separat lizenziert werden

### Option E — Paperless-ngx als Zwischenstufe ❌

**Con:**
- Behördendokumente durchlaufen IIL-interne Infrastruktur (Datenschutzproblem)
- Zweistufiger Prozess: Paperless-Import → Export → d.velop
- Kein nativer d.velop-Metadaten-Mapping in Paperless
- Doppelte Datenhaltung auf IIL-Servern

---

## 5. Technische Spezifikation

### 5.1 WireGuard-Tunnel-Erweiterung (Fritzbox als nativer WireGuard-Gateway)

**Voraussetzung bereits erfüllt**: Die Fritzbox am Landratsamt hat WireGuard
nativ konfiguriert (FRITZ!OS ≥ 7.50). Die Fritzbox fungiert als WireGuard-Router-Gateway
für das gesamte lokale Netz des Landratsamts — alle Geräte im Fritzbox-Subnetz
(beide Scanner, iX1600-PC) sind automatisch über den Tunnel erreichbar.
**Kein separater WireGuard-Client auf einem PC nötig.**

```
Landratsamt (lokales Fritzbox-Netz, z.B. 192.168.178.0/24)
  HP E58650  (192.168.178.x) ──┐
  iX1600-PC  (192.168.178.x) ──┼── Fritzbox (WG-Peer, RouterOS-Gateway)
  Scan-PC    (192.168.178.x) ──┘        │
                                    WireGuard UDP 51820
                                         │
                                   Hetzner-VM wg0
                                   (dms-hub Samba erreichbar)
```

**Hetzner-VM — neuer Peer in `wg0.conf`:**

```ini
# /etc/wireguard/wg0.conf (Hetzner-VM — Ergänzung)
[Peer]
# Fritzbox Landratsamt — Router-Gateway für Scanner-Netz
PublicKey = <fritzbox-wg-pubkey>           # aus Fritzbox-GUI exportieren
AllowedIPs = 192.168.178.0/24             # lokales Fritzbox-Subnetz
PersistentKeepalive = 25

# wg set wg0 peer <pubkey> allowed-ips 192.168.178.0/24 persistent-keepalive 25
# systemctl reload wg-quick@wg0
```

**Fritzbox-GUI-Konfiguration** (`Internet → Freigaben → VPN (WireGuard)`):

```
Neuer WireGuard-Tunnel:
  Name:              IIL Platform DMS
  Gegenstelle-IP:    <hetzner-vm-public-ip>
  Gegenstelle-Port:  51820
  Eigene IP (WG):    z.B. 10.100.50.2/32
  Peer-PublicKey:    <hetzner-wg-pubkey>
  AllowedIPs:        10.100.10.0/24     ← Hetzner-WG-Subnetz (Samba erreichbar)
  PersistentKeepalive: 25s
```

**Firewall-Regeln auf Hetzner-VM (idempotentes Shell-Script):**

```bash
#!/bin/bash
set -euo pipefail

# SMB nur aus WireGuard-Tunnel erlauben — niemals öffentlich
iptables -A INPUT -p tcp --dport 445 -s 192.168.178.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 445 -j DROP   # alle anderen → DROP

# WireGuard-Port öffentlich (Fritzbox muss Tunnel aufbauen können)
iptables -A INPUT -p udp --dport 51820 -j ACCEPT

# Regeln persistent machen
iptables-save > /etc/iptables/rules.v4
```

**Sicherheitsanforderungen:**
- WireGuard-PublicKey der Fritzbox sicher übermitteln (nicht per E-Mail)
- SMB (445/TCP) ausschließlich aus WireGuard-Subnetz erreichbar — niemals öffentlich
- Fritzbox-Firmware aktuell halten (WireGuard-Fixes in FRITZ!OS-Updates)

### 5.2 Samba-Konfiguration auf dms-hub

```ini
# /etc/samba/smb.conf (dms-hub Container oder dedizierter Samba-Container)

[global]
   workgroup = IILPLATFORM
   server string = IIL DMS Inbound Scanner
   security = user
   min protocol = SMB2          # SMBv1 explizit verboten
   max protocol = SMB3
   smb encrypt = required       # Verschlüsselung erzwingen (innerhalb WG-Tunnel)
   log level = 1

[scan-inbound]
   path = /mnt/scan-inbound
   valid users = scanuser
   read only = no
   browsable = no
   create mask = 0640
   directory mask = 0750
   # Unterordner-Struktur:
   # /mnt/scan-inbound/hp-e58650/     ← HP PageWide Eingang
   # /mnt/scan-inbound/ix1600/        ← Fujitsu iX1600 Eingang
   # /mnt/scan-inbound/processed/     ← verarbeitete Dateien
   # /mnt/scan-inbound/failed/        ← fehlgeschlagene Dateien
```

```yaml
# docker-compose.yml (Ergänzung in dms-hub)
dms-samba:
  image: dperson/samba:latest          # oder ghcr.io/servercontainers/samba
  container_name: dms-hub-samba
  environment:
    USERID: "1000"
    GROUPID: "1000"
  volumes:
    - scan_inbound:/mnt/scan-inbound
    - ./samba/smb.conf:/etc/samba/smb.conf:ro
    - ./samba/secrets:/run/secrets:ro  # scanuser-Passwort als Secret
  ports:
    - "445:445"                        # NUR innerhalb WireGuard erreichbar
  healthcheck:
    test: ["CMD-SHELL", "smbstatus -n || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
  restart: unless-stopped

volumes:
  scan_inbound:
```

### 5.3 HP PageWide E58650 — EWS-Konfiguration

**Zugang:** `http://<drucker-ip>/` → "Scannen" → "In Netzwerkordner speichern"

```
Einrichtungsparameter:
  Anzeigename:    IIL DMS Eingang
  Netzwerkpfad:  \\10.100.10.1\scan-inbound\hp-e58650
  Authentifizierung:
    Benutzername: scanuser          ← max. 6 Zeichen (EWS-Limitation!)
    Kennwort:     <read_secret("SMB_SCAN_PASSWORD")>
    Domäne:       (leer)

SMB-Protokoll (EWS → Network → Advanced Settings → SMB):
    SMBv1: DEAKTIVIERT
    SMBv2: DEAKTIVIERT
    SMBv3: AKTIVIERT               ← nur v3, höchste Sicherheit

Scan-Schnelleinstellungen (HP Quick Sets):
  "Eingehende Post":
    Format: Searchable PDF (OCR)   ← eingebettetes OCR nutzen
    Auflösung: 300 dpi
    Farbmodus: Farbe
    Beidseitig: Ja
    Dateiname: SCAN_{DATE}_{TIME}.pdf
    Zielordner: hp-e58650/
```

### 5.4 Fujitsu iX1600 — PaperStream Capture Profil

```
Profil-Konfiguration (PaperStream Capture):
  Profilname: IIL DMS Eingang
  Scan-Einstellungen:
    Modus:          Farbe (24-bit)
    Auflösung:      300 dpi
    Papierformat:   Automatisch erkennen
    Beidseitig:     Ja
    Leerseiten:     Automatisch entfernen
    Bildoptimierung: PaperStream IP (automatisch)

  Ausgabe:
    Format:   PDF (Searchable)        ← ABBYY-OCR aktiviert
    Dateiname: {SCAN_DATE}_{SCAN_TIME}.pdf

  Ziel:
    Typ:            Netzwerkordner (SMB)
    Pfad:          \\10.100.10.1\scan-inbound\ix1600
    Benutzername:  scanuser
    Passwort:      <SMB_SCAN_PASSWORD>
```

### 5.5 Django-App `dms_inbound` — Kernkomponenten

```python
# src/dms_inbound/models.py

class InboundScanRecord(models.Model):
    """Audit-Trail für jede gescannte Datei. Unveränderlich nach Anlage."""

    class ScannerSource(models.TextChoices):
        HP_E58650 = "HP_E58650", "HP PageWide Color Flow E58650"
        IX1600    = "IX1600",    "Fujitsu iX1600"
        UNKNOWN   = "UNKNOWN",   "Unbekannter Scanner"

    class ProcessingStatus(models.TextChoices):
        PENDING   = "PENDING",   "Ausstehend"
        PROCESSING = "PROCESSING", "In Bearbeitung"
        SUCCESS   = "SUCCESS",   "Erfolgreich importiert"
        FAILED    = "FAILED",    "Fehlgeschlagen"
        DUPLICATE = "DUPLICATE", "Duplikat (bereits verarbeitet)"

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id       = models.UUIDField(db_index=True)

    # Datei-Informationen
    original_filename = models.CharField(max_length=500)
    file_size_bytes   = models.BigIntegerField()
    sha256_hash       = models.CharField(max_length=64, db_index=True,
                          help_text="SHA-256 des Rohdatei-Inhalts — Duplikaterkennung")
    scanner_source    = models.CharField(max_length=10, choices=ScannerSource.choices)
    scan_timestamp    = models.DateTimeField(help_text="Aus Datei-Metadaten oder Filename")

    # Verarbeitungsstatus
    status            = models.CharField(max_length=12, choices=ProcessingStatus.choices,
                          default=ProcessingStatus.PENDING, db_index=True)
    error_message     = models.TextField(blank=True)
    retry_count       = models.PositiveSmallIntegerField(default=0)
    celery_task_id    = models.CharField(max_length=255, blank=True)

    # d.velop-Ergebnis
    dms_document_id   = models.CharField(max_length=255, blank=True, db_index=True)
    dms_category      = models.CharField(max_length=100, blank=True)
    dms_repository_id = models.CharField(max_length=255, blank=True)

    created_at        = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dms_inbound_record"
        indexes = [
            models.Index(fields=["tenant_id", "scanner_source", "status"]),
            models.Index(fields=["sha256_hash"]),
        ]
        constraints = [
            # Duplikaterkennung: gleicher Hash = gleiche Datei → kein Doppelimport
            models.UniqueConstraint(
                fields=["tenant_id", "sha256_hash"],
                condition=models.Q(status="SUCCESS"),
                name="uq_inbound_no_duplicate_success",
            )
        ]
```

### 5.6 Inbound-Scan-Processor (Celery-Beat-Task)

```python
# src/dms_inbound/tasks.py

@shared_task(bind=True, max_retries=3, queue="dms",
             name="dms_inbound.process_scan_directory",
             acks_late=True)
def process_scan_directory(self, *, tenant_id: str) -> dict:
    """
    Läuft via Celery Beat alle 30 Sekunden.
    Verarbeitet alle neuen Dateien in /mnt/scan-inbound/{hp-e58650,ix1600}/
    """
    import hashlib
    from pathlib import Path

    base_path = Path("/mnt/scan-inbound")
    source_dirs = {
        "HP_E58650": base_path / "hp-e58650",
        "IX1600":    base_path / "ix1600",
    }
    processed = 0

    for scanner_source, scan_dir in source_dirs.items():
        if not scan_dir.exists():
            continue
        for pdf_file in sorted(scan_dir.glob("*.pdf")):
            # SHA-256 berechnen
            sha256 = hashlib.sha256(pdf_file.read_bytes()).hexdigest()

            # Duplikat-Check
            if InboundScanRecord.objects.filter(
                tenant_id=tenant_id, sha256_hash=sha256, status="SUCCESS"
            ).exists():
                pdf_file.rename(base_path / "processed" / f"DUPLICATE_{pdf_file.name}")
                continue

            # InboundScanRecord anlegen + Task dispatchen
            record = InboundScanRecord.objects.create(
                tenant_id       = tenant_id,
                original_filename = pdf_file.name,
                file_size_bytes = pdf_file.stat().st_size,
                sha256_hash     = sha256,
                scanner_source  = scanner_source,
                scan_timestamp  = _extract_scan_timestamp(pdf_file),
            )
            import_single_scan.apply_async(
                kwargs={"record_id": str(record.id), "file_path": str(pdf_file)},
                queue="dms",
            )
            processed += 1

    return {"processed": processed, "tenant_id": tenant_id}


def _extract_scan_timestamp(pdf_file) -> datetime:
    """Timestamp aus Dateiname (SCAN_YYYYMMDD_HHMMSS.pdf) oder mtime."""
    import re
    from datetime import datetime
    from django.utils import timezone

    match = re.search(r"(\d{8})_(\d{6})", pdf_file.name)
    if match:
        try:
            return datetime.strptime(
                f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(pdf_file.stat().st_mtime, tz=timezone.utc)
```

---

## 6. Sicherheitsanalyse

### 6.1 Netzwerk-Angriffsfläche

| Protokoll | Port | Erreichbar von | Schutz |
|-----------|------|----------------|--------|
| WireGuard | UDP 51820 | Internet (Fritzbox-Endpoint) | Öffentlich nur für WireGuard; Pre-Shared-Key optional |
| SMB | TCP 445 | **NUR** innerhalb WireGuard (10.100.x.x) | Firewall-Regel: `iptables -A INPUT -p tcp --dport 445 -s 10.100.0.0/16 -j ACCEPT` |
| SMB | TCP 445 | Öffentliches Internet | **BLOCKED** — Firewall-Regel: DROP alle anderen 445-Requests |

### 6.2 SMB-Protokoll-Sicherheit

- **SMBv1 verboten** — auf Samba-Seite (`min protocol = SMB2`) und HP EWS (v3 only)
- **Encryption required** im Samba-Global-Config (`smb encrypt = required`)
- WireGuard verschlüsselt den gesamten Tunnel zusätzlich (ChaCha20-Poly1305)
- Ergebnis: **doppelte Verschlüsselung** (WireGuard + SMB-Encryption)

### 6.3 Zugangsdaten

- Samba-Benutzer `scanuser` ist ein Minimal-Account ohne Login-Shell
  (`/sbin/nologin`), nur für den Scan-Share
- Passwort via `read_secret("SMB_SCAN_PASSWORD")` — nie in Konfigurationsdateien
- HP EWS und PaperStream Capture: Passwort einmalig eingeben, wird intern
  verschlüsselt gespeichert (kein Klartext im EWS-Export)

### 6.4 DSGVO-Konformität

Alle gescannten Dokumente enthalten potenziell personenbezogene Daten.
Der Transportpfad ist vollständig verschlüsselt (WireGuard + SMB).
Die temporäre Ablage auf `/mnt/scan-inbound/` auf dem Hetzner-Server
liegt im selben Sicherheitsperimeter wie die übrigen Platform-Daten.
Verarbeitete Dateien werden nach erfolgreichem d.velop-Upload in
`processed/` archiviert und nach 7 Tagen automatisch gelöscht
(Celery-Beat-Cleanup-Task).

---

## 7. Scanner-Vergleich und Use-Case-Zuordnung

| Aspekt | HP PageWide E58650z | Fujitsu iX1600 |
|--------|--------------------|-----------------|
| **Primärer Use Case** | Abteilungs-Scanner (Büroetage): Eingehende Post, Großformat-Dokumente, Farbdokumente | Dedizierter Akten-Scanner: Massendigitalisierung, Altakten, dünne Dokumente |
| **ADF-Kapazität** | 100 Blatt | 50 Blatt |
| **Beidseitig** | Ja, Single-Pass (E58650z) | Ja, Single-Pass |
| **Scangeschwindigkeit** | bis 70 ipm (A4) | bis 80 ipm (A4) |
| **OCR** | Embedded (für gelegentliche Nutzung) | ABBYY FineReader (hochwertig, für Massenverarbeitung) |
| **Format** | A4 bis A3 (Flatbed), A4 (ADF) | max. A4 (ADF), kein Flatbed |
| **Netzwerk** | Gigabit Ethernet (direkt) | USB + WLAN (via Scan-PC/NX Manager) |
| **Scan-Trigger** | Benutzer am 8"-Touchscreen | Benutzer drückt Taste oder wählt Profil |
| **d.velop-Kategorie** | `INBOUND_POST` (Eingehende Post), `INBOUND_BESCHEID` (Bescheide) | `INBOUND_AKTE` (Aktendigitalisierung), `INBOUND_ALTBESTAND` |
| **Samba-Unterordner** | `hp-e58650/` | `ix1600/` |

---

## 8. Konsequenzen

### 8.1 Positiv

- Ein einziger SMB-Eingangsordner für beide Scanner — gleicher Verarbeitungspfad,
  gleiche d.velop-Integration, keine Sonderlösungen
- Kein neuer VPN-Stack: WireGuard ist bereits installiert und stabil
- Vollständiger Audit-Trail: `InboundScanRecord` dokumentiert jeden Scan,
  SHA-256-Duplikaterkennung verhindert Doppelimporte
- `scanner_source`-Feld ermöglicht Statistiken pro Gerät (Scan-Volumen,
  Fehlerrate per Scanner)
- Celery-Beat alle 30s: niedrige Latenz ohne Echtzeit-Infrastruktur
- SMBv3 + WireGuard: DSGVO-konformer Transport ohne Kompromisse
- Skalierbar: zusätzliche Scanner benötigen nur neuen Unterordner und
  einen Eintrag in `ScannerSource.choices`

### 8.2 Negativ

- Fujitsu iX1600 benötigt PaperStream Capture oder NX Manager auf einem
  Windows-Rechner am Landratsamt — kein eigenständiger Netzwerkbetrieb
- Samba-Container erhöht Container-Anzahl in dms-hub um 1
- WireGuard-Peer-Konfiguration für jeden neuen Standort manuell — kein
  automatisches Enrollment

### 8.3 Risiken

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| HP EWS SMBv3-Kompatibilitätsprobleme (bekanntes Firmware-Issue) | Mittel | Hoch | Firmware auf aktuellsten Stand; Fallback auf SMBv2 falls nötig; Benutzername ≤ 6 Zeichen |
| WireGuard-Tunnel unterbrochen | Niedrig | Mittel | PersistentKeepalive=25; Monitoring-Alert wenn Tunnel > 5 min inaktiv |
| Scan-Ordner läuft voll (kein Platz) | Niedrig | Hoch | Cleanup-Task nach 7 Tagen; Volume-Monitoring in Grafana |
| Duplikat-Scan durch Benutzer | Hoch | Niedrig | SHA-256-Hash-Prüfung verhindert Doppelimport automatisch |
| iX1600-PC am Landratsamt offline | Mittel | Mittel | PaperStream NX Manager als Dienst installieren; Watchdog-Script |

---

## 9. Confirmation

Diese ADR gilt als implementiert, wenn:

1. `docker-compose.yml` in dms-hub enthält `dms-samba` mit Healthcheck (ADR-078)
2. WireGuard-Peer für Landratsamt aktiv: `wg show wg0` zeigt handshake < 5 min
3. HP E58650z kann erfolgreich in `\\<wg-ip>\scan-inbound\hp-e58650\` scannen
   (EWS-Test: "Test-Verbindung" gibt grünes Häkchen)
4. iX1600 kann über PaperStream Capture in `\\<wg-ip>\scan-inbound\ix1600\` schreiben
5. `process_scan_directory` Task: Testdatei in Eingangsordner → `InboundScanRecord(status=SUCCESS)` in DB
6. d.velop-Dokument nach Verarbeitung in `https://iil.d-velop.cloud` abrufbar
7. Duplikat-Test: gleiche Datei zweimal einlegen → zweiter Eintrag mit `status=DUPLICATE`
8. Samba-Konfiguration: `testparm -s` ohne Fehler; `smbclient -L localhost -U scanuser` erfolgreich
9. `min protocol = SMB2` und `smb encrypt = required` in `smb.conf` — verifiziert via `smbstatus`
10. `SMB_SCAN_PASSWORD` ausschließlich via `read_secret()` — kein Klartext in Config-Dateien

---

## 10. More Information

### Externe Quellen

| Quelle | Relevanz |
|--------|----------|
| HP PageWide E58650 Datasheet | SMB-Konfiguration, Scan-Formate, OCR-Fähigkeiten |
| HP EWS Benutzerhandbuch (S. 108) | Save-to-Network-Folder-Einrichtung |
| HP Community: SMB Troubleshooting | Firmware-Anforderungen, Benutzername-Länge ≤ 6 Zeichen |
| Fujitsu PaperStream NX Manager Docs | Headless-Betrieb, Hot-Folder-Konfiguration |
| Samba-Dokumentation (smb.conf(5)) | `min protocol`, `smb encrypt`, Share-Permissions |
| WireGuard Whitepapers | Tunnel-Konfiguration, PersistentKeepalive |

### Verwandte ADRs

| ADR | Titel | Relevanz |
|-----|-------|----------|
| ADR-146 | risk-hub → DMS Audit Trail | Nutzt denselben d.velop REST API Client |
| ADR-144 | Paperless-ngx doc-hub | Abgrenzung: Paperless für IIL-intern, d.velop für Behörde |
| ADR-045 | Secrets Management | `read_secret("SMB_SCAN_PASSWORD")`, `read_secret("DVELOP_API_KEY")` |
| ADR-072 | Multi-Tenancy | `tenant_id` auf `InboundScanRecord` |
| ADR-078 | Docker Healthcheck | `dms-samba` Container-Healthcheck |

### Zukünftige ADRs

- **ADR-147**: `dvelop_mcp.py` — FastMCP für agentic DMS-Zugriff
- **ADR-150**: Erweiterung Inbound-Scan auf weiteren Mandanten (zweiter Standort)

---

## 11. Migration Tracking

| Schritt | Status | Datum | Notiz |
|---------|--------|-------|-------|
| ADR-149 erstellt | ✅ Done | 2026-03-25 | HP E58650 + iX1600 |
| ADR-149 Review | ⏳ Pending | – | – |
| Samba-Container Konfiguration | ⏳ Pending | – | `dms-hub/samba/smb.conf` |
| WireGuard Peer Landratsamt | ⏳ Pending | – | Key-Exchange sicher durchführen |
| `dms_inbound` App-Skeleton | ⏳ Pending | – | Modell + Task + Migration |
| HP E58650 EWS-Konfiguration | ⏳ Pending | – | vor Ort oder remote via EWS |
| iX1600 PaperStream Profil | ⏳ Pending | – | Vor-Ort-Einrichtung Landratsamt |
| End-to-End-Test (beide Scanner) | ⏳ Pending | – | Testdokument → d.velop |
| ADR-149 Status → Accepted | ⏳ Pending | – | Nach E2E-Test |

---

*Erstellt: 2026-03-25 · Autor: Achim Dehnert · Review: ausstehend*
