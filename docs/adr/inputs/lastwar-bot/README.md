# Last War: Survival Bot Platform

3 parallele Bot-Instanzen auf Hetzner CX42 (€16,40/Monat).

## Architektur

```
Celery Beat (3× täglich)
    └── run_all_bots_daily()
            ├── Bot 1 → emulator-5554 (AVD: lastwar-bot-1)
            ├── Bot 2 → emulator-5556 (AVD: lastwar-bot-2)
            └── Bot 3 → emulator-5558 (AVD: lastwar-bot-3)
```

## Schnellstart

```bash
# 1. Server einrichten (einmalig)
bash scripts/00_setup_server.sh

# 2. Emulatoren starten
bash scripts/start_emulators.sh

# 3. Last War APKs installieren
adb -s emulator-5554 install lastwar.apk
adb -s emulator-5556 install lastwar.apk
adb -s emulator-5558 install lastwar.apk

# 4. Accounts manuell einrichten (einmalig per scrcpy)
scrcpy -s emulator-5554

# 5. Bot starten
source .venv/bin/activate
celery -A bot.tasks worker --loglevel=info &
celery -A bot.tasks beat --loglevel=info &
```

## Templates erstellen

```bash
# Screenshot eines laufenden Emulators
adb -s emulator-5554 exec-out screencap -p > screen.png

# Button ausschneiden und als Template speichern
# z.B. templates/btn_collect_all.png
```

## Phasenplan

- **Phase 0** — Server-Provisioning (Tag 1)
- **Phase 1** — Emulator-Management + Systemd (Tag 1–2)
- **Phase 2** — Bot-Framework (Tag 2–4)
- **Phase 3** — Templates & Kalibrierung (Tag 4–6)
- **Phase 4** — Monitoring & Alerting (Tag 6–7)
