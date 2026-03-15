# ADR-XXX: Last War Survival Bot Platform

## Status

Vorgeschlagen

## Kontext

Für das Spiel **Last War: Survival** sollen repetitive Spielaufgaben (Ressourcen sammeln, Zombie-Jagd, Truppen-Training, Rallyes) automatisiert werden. Es werden **3 parallele Bot-Instanzen** (3 Accounts) benötigt, die 24/7 laufen.

Der bestehende IIL-Platform-Stack (DEV CX32, PROD CPX32) darf durch diesen Workload **nicht belastet** werden. Die Automation ist privater Natur und kein Bestandteil der IIL-Geschäftsanwendungen.

### Rahmenbedingungen

- 3 Android-Emulatoren laufen parallel (headless)
- Jeder Emulator benötigt ~2,5 GB RAM + ~2 vCPUs
- Python-basierte Automation via ADB + OpenCV + uiautomator2
- Zeitgesteuerte Ausführung (Celery Beat)
- Vollständige Isolation vom IIL-Stack
- Budget: < €20/Monat

### Technische Anforderungen pro Emulator-Instanz

| Ressource | Bedarf | × 3 |
|---|---|---|
| RAM | ~2,5 GB | ~7,5 GB |
| vCPU | ~2 | ~6 |
| Disk (AVD) | ~10 GB | ~30 GB |
| Python Bot | ~200 MB | ~600 MB |

## Entscheidung

### Infrastruktur: Hetzner CX42 (dedizierter Bot-Server)

**Hetzner CX42** als separater Server:

| Spec | Wert |
|---|---|
| vCPUs | 8 |
| RAM | 16 GB |
| SSD | 160 GB |
| Traffic | 20 TB |
| Preis | €16,40/Monat |
| Betriebssystem | Ubuntu 22.04 LTS |

Begründung: CX32 (8 GB RAM) ist für 3 parallele Emulatoren (~9 GB Bedarf) zu knapp. CX42 bietet ausreichend Reserve für stabile 24/7-Laufzeit. CX52 (€32,40) wäre erst ab 5+ Instanzen sinnvoll.

### Software-Stack

```
┌─────────────────────────────────────────────────────┐
│  Celery Beat (zeitgesteuerte Tasks)                 │
│  Python 3.12 + uiautomator2 + OpenCV + Tesseract   │
├─────────────────────────────────────────────────────┤
│  ADB over TCP (Port 5555/5557/5559)                 │
├──────────────┬──────────────┬───────────────────────┤
│ AVD: bot-1   │ AVD: bot-2   │ AVD: bot-3            │
│ Port 5554    │ Port 5556    │ Port 5558             │
├──────────────┴──────────────┴───────────────────────┤
│  Android SDK Emulator (headless, swiftshader_indirect│
│  system-images;android-34;google_apis;x86_64        │
├─────────────────────────────────────────────────────┤
│  Ubuntu 22.04 LTS — Hetzner CX42 (BOT-Server)      │
│  Vollständig isoliert vom IIL-Stack                 │
└─────────────────────────────────────────────────────┘
```

### Python-Versionen

- **Python 3.12** für Bot-Stack (pyenv, isoliertes venv pro Bot)
- Kein Python 3.13 erforderlich — alle Dependencies stabil auf 3.12
- pyenv verhindert Konflikte zwischen Bot-Versionen

### Automation-Technologie

**ADB + OpenCV Template Matching** (kein uiautomator2-XML-Parsing):

- Robuster gegenüber Spiel-Updates
- Pixel-basierte Button-Erkennung via `cv2.matchTemplate`
- Tesseract OCR für Ressourcen-Werte auslesen
- Kein Root erforderlich

## Abgelehnte Alternativen

### A — DEV-Server (CX32) mitnutzen

Abgelehnt: 8 GB RAM reichen für 3 Emulatoren nicht. Swap-Nutzung destabilisiert den Django-Stack.

### B — Windows Server + BlueStacks

Abgelehnt: BlueStacks existiert nicht für Linux. Windows-Server sind teurer und nicht im bestehenden Hetzner-Workflow.

### C — Cloud-Bot-Dienste (GodLikeBots, lastwarbot.com)

Abgelehnt: Windows-only, monatliche Lizenzkosten (~$10–30), keine Anpassbarkeit, kein Linux-Server-Support.

### D — Waydroid

Abgelehnt: Erfordert Wayland-Compositor auf Headless-Server — erheblicher Setup-Aufwand ohne Mehrwert gegenüber Android SDK Emulator.

## Konsequenzen

### Positiv

- Vollständige Isolation vom IIL-Produktivstack
- Günstig (€16,40/Monat für 3 Bots = ~€5,47/Bot)
- Volle Kontrolle und Anpassbarkeit
- Passt in bestehende Hetzner/GitHub-Infrastruktur
- Erweiterbar auf 5 Bots ohne Server-Upgrade

### Negativ / Risiken

- ⚠️ Verstoß gegen Last War ToS — Account-Ban-Risiko (privat akzeptiert)
- Maintenance-Aufwand bei Spiel-Updates (neue Templates nötig)
- KVM-Verfügbarkeit auf Hetzner CX42 muss beim Provisioning geprüft werden

## Implementierungsplan

### Phase 0 — Server-Provisioning (Tag 1)

- [ ] Hetzner CX42 erstellen (Ubuntu 22.04)
- [ ] SSH-Key hinterlegen, Firewall konfigurieren
- [ ] KVM-Support prüfen (`kvm-ok`)
- [ ] pyenv + Python 3.12 installieren
- [ ] Android SDK + Emulator installieren
- [ ] 3 AVDs erstellen (bot-1, bot-2, bot-3)

### Phase 1 — Emulator-Management (Tag 1–2)

- [ ] `start_emulators.sh` — startet alle 3 headless, wartet auf Boot
- [ ] `stop_emulators.sh` — sauberes Beenden
- [ ] `health_check.sh` — prüft ADB-Verbindung aller 3 Instanzen
- [ ] Systemd-Service für Auto-Start nach Reboot
- [ ] Last War APK auf alle 3 AVDs installieren + Accounts einrichten

### Phase 2 — Bot-Framework (Tag 2–4)

- [ ] `bot/core.py` — `LastWarBot` Klasse (ADB + OpenCV)
- [ ] `bot/actions.py` — Einzelaktionen (click, swipe, wait_for, find_template)
- [ ] `bot/tasks.py` — Daily Routine (collect, gather, hunt, train)
- [ ] `bot/scheduler.py` — Celery Beat Tasks
- [ ] `templates/` — PNG-Screenshots aller UI-Elemente

### Phase 3 — Templates & Kalibrierung (Tag 4–6)

- [ ] Screenshots aller relevanten Buttons via ADB
- [ ] Template-Matching-Schwellwerte kalibrieren
- [ ] OCR für Ressourcen-Werte (Stamina, Queue-Status)
- [ ] Fehlerbehandlung (Dialoge, Verbindungsabbrüche, Game-Updates)

### Phase 4 — Monitoring (Tag 6–7)

- [ ] Log-Rotation via logrotate
- [ ] Heartbeat-Check (Celery Task prüft ob alle 3 Bots laufen)
- [ ] Telegram-Benachrichtigung bei Bot-Absturz (optional)
- [ ] Screenshot-Archiv für Debugging

## Referenzen

- [steeljardas/Last-War-Bot](https://github.com/steeljardas/Last-War-Bot-Hunting-Gathering-Power-Account-Growth) — Python ADB + OpenCV Referenzimplementierung
- [quackadillyblip/bot](https://github.com/quackadillyblip/bot) — OpenCV Template Matching für Last War
- Hetzner CX42: €16,40/Monat, 8 vCPU, 16 GB RAM, 160 GB SSD
- ADR-009 (Reusable GitHub Actions) — nicht anwendbar (privater Bot-Server)
