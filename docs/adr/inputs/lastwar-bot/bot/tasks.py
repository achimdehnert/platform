"""
bot/tasks.py — Celery Tasks für Last War Bot
Zeitgesteuerte Ausführung aller 3 Bot-Instanzen
"""
from __future__ import annotations

import logging
from celery import Celery
from celery.schedules import crontab

from bot.core import BotConfig, LastWarBot

logger = logging.getLogger(__name__)

app = Celery(
    "lastwar_bot",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

app.conf.update(
    task_serializer="json",
    result_expires=3600,
    timezone="Europe/Berlin",
    enable_utc=True,
)

# ── Bot-Konfigurationen ────────────────────────────────────────────────────────

BOT_CONFIGS = [
    BotConfig(device_serial="emulator-5554", bot_id=1),
    BotConfig(device_serial="emulator-5556", bot_id=2),
    BotConfig(device_serial="emulator-5558", bot_id=3),
]

# ── Tasks ──────────────────────────────────────────────────────────────────────

@app.task(bind=True, max_retries=2, default_retry_delay=60)
def run_bot_daily(self, bot_id: int) -> dict:
    """Daily Routine für einen Bot."""
    config = BOT_CONFIGS[bot_id - 1]
    try:
        bot = LastWarBot(config)
        bot.run_daily_routine()
        return {"bot_id": bot_id, "status": "success"}
    except Exception as exc:
        logger.error("Bot %d: Fehler — %s", bot_id, exc)
        raise self.retry(exc=exc)


@app.task
def run_all_bots_daily() -> None:
    """Startet alle 3 Bots parallel."""
    for bot_id in [1, 2, 3]:
        run_bot_daily.delay(bot_id)


@app.task
def health_check() -> dict:
    """Prüft ADB-Verbindung aller 3 Emulatoren."""
    import subprocess
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    devices = [
        line.split("\t")[0]
        for line in result.stdout.strip().splitlines()[1:]
        if "device" in line
    ]
    status = {
        f"bot_{i+1}": (config.device_serial in devices)
        for i, config in enumerate(BOT_CONFIGS)
    }
    logger.info("Health Check: %s", status)
    return status


# ── Celery Beat Schedule ───────────────────────────────────────────────────────

app.conf.beat_schedule = {
    # Morgendliche Routine: 06:00 Uhr
    "daily-routine-morning": {
        "task": "bot.tasks.run_all_bots_daily",
        "schedule": crontab(hour=6, minute=0),
    },
    # Mittag-Routine: 12:30 Uhr (Ressourcen + Heilen)
    "daily-routine-midday": {
        "task": "bot.tasks.run_all_bots_daily",
        "schedule": crontab(hour=12, minute=30),
    },
    # Abend-Routine: 20:00 Uhr
    "daily-routine-evening": {
        "task": "bot.tasks.run_all_bots_daily",
        "schedule": crontab(hour=20, minute=0),
    },
    # Health Check alle 15 Minuten
    "health-check": {
        "task": "bot.tasks.health_check",
        "schedule": crontab(minute="*/15"),
    },
}
