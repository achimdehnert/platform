"""
bot/core.py — Last War: Survival Bot Core
Stack: ADB + OpenCV Template Matching + Tesseract OCR
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image
import uiautomator2 as u2

logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    device_serial: str          # z.B. "emulator-5554"
    bot_id: int                 # 1, 2, oder 3
    package: str = "com.fun.lastwar.gp"
    templates_dir: Path = Path("templates")
    screenshot_dir: Path = Path("screenshots")
    match_threshold: float = 0.85
    action_delay: float = 1.5   # Sekunden zwischen Aktionen


@dataclass
class MatchResult:
    found: bool
    confidence: float = 0.0
    x: int = 0
    y: int = 0


class LastWarBot:
    """
    Last War: Survival Automation Bot

    Verwendet OpenCV Template Matching für robuste Button-Erkennung,
    die unabhängig von Android UI-Baum-Strukturen ist.
    """

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.config.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._connect()

    # ── Verbindung ────────────────────────────────────────────────────────────

    def _connect(self) -> None:
        logger.info("Bot %d: Verbinde mit %s", self.config.bot_id, self.config.device_serial)
        self.d = u2.connect(self.config.device_serial)
        self.d.implicitly_wait(10)
        info = self.d.device_info
        logger.info("Bot %d: Verbunden — %s", self.config.bot_id, info.get("model", "unknown"))

    def ensure_game_running(self) -> None:
        """Spiel starten falls nicht im Vordergrund."""
        current = self.d.app_current()
        if current.get("package") != self.config.package:
            logger.info("Bot %d: Starte Last War...", self.config.bot_id)
            self.d.app_start(self.config.package)
            time.sleep(8)  # Ladezeit

    # ── Screenshot & Template Matching ────────────────────────────────────────

    def screenshot(self) -> np.ndarray:
        """Aktuellen Screen als OpenCV-Array."""
        img = self.d.screenshot(format="opencv")
        return img

    def save_screenshot(self, name: str) -> Path:
        """Screenshot für Debugging speichern."""
        path = self.config.screenshot_dir / f"bot{self.config.bot_id}_{name}_{int(time.time())}.png"
        cv2.imwrite(str(path), self.screenshot())
        return path

    def find_template(
        self,
        template_name: str,
        threshold: Optional[float] = None,
        region: Optional[tuple[int, int, int, int]] = None,
    ) -> MatchResult:
        """
        Template auf Screen suchen.

        Args:
            template_name: Dateiname ohne .png
            threshold: Mindest-Konfidenz (default: config.match_threshold)
            region: (x, y, w, h) — nur in diesem Bereich suchen

        Returns:
            MatchResult mit found, confidence, x, y (Mittelpunkt)
        """
        threshold = threshold or self.config.match_threshold
        template_path = self.config.templates_dir / f"{template_name}.png"

        if not template_path.exists():
            raise FileNotFoundError(f"Template nicht gefunden: {template_path}")

        template = cv2.imread(str(template_path))
        screen = self.screenshot()

        if region:
            x, y, w, h = region
            search_area = screen[y:y+h, x:x+w]
        else:
            search_area = screen
            x, y = 0, 0

        result = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            th, tw = template.shape[:2]
            cx = x + max_loc[0] + tw // 2
            cy = y + max_loc[1] + th // 2
            logger.debug("Bot %d: Template '%s' gefunden (%.2f) @ %d,%d",
                        self.config.bot_id, template_name, max_val, cx, cy)
            return MatchResult(found=True, confidence=max_val, x=cx, y=cy)

        return MatchResult(found=False, confidence=max_val)

    def wait_for_template(
        self,
        template_name: str,
        timeout: int = 30,
        interval: float = 2.0,
    ) -> MatchResult:
        """Warten bis Template erscheint."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self.find_template(template_name)
            if result.found:
                return result
            time.sleep(interval)
        logger.warning("Bot %d: Timeout warten auf '%s'", self.config.bot_id, template_name)
        return MatchResult(found=False)

    # ── Aktionen ──────────────────────────────────────────────────────────────

    def click_template(
        self,
        template_name: str,
        timeout: int = 10,
    ) -> bool:
        """Template finden und klicken."""
        result = self.wait_for_template(template_name, timeout=timeout)
        if result.found:
            self.d.click(result.x, result.y)
            time.sleep(self.config.action_delay)
            return True
        logger.warning("Bot %d: Klick fehlgeschlagen — '%s' nicht gefunden",
                      self.config.bot_id, template_name)
        return False

    def click_xy(self, x: int, y: int) -> None:
        """Direkter Klick auf Koordinaten."""
        self.d.click(x, y)
        time.sleep(self.config.action_delay)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
        self.d.swipe(x1, y1, x2, y2, duration=duration)
        time.sleep(self.config.action_delay)

    def back(self) -> None:
        self.d.press("back")
        time.sleep(1.0)

    def home(self) -> None:
        """Zurück zur Base."""
        self.click_template("btn_home", timeout=5)

    # ── OCR ───────────────────────────────────────────────────────────────────

    def read_text_region(
        self,
        x: int, y: int, w: int, h: int,
        digits_only: bool = False,
    ) -> str:
        """OCR auf Bildausschnitt — z.B. für Stamina, Queue-Countdown."""
        screen = self.screenshot()
        region = screen[y:y+h, x:x+w]

        # Kontrast erhöhen für bessere OCR
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        config = "--psm 7 -c tessedit_char_whitelist=0123456789" if digits_only else "--psm 7"
        text = pytesseract.image_to_string(Image.fromarray(thresh), config=config)
        return text.strip()

    # ── Daily Tasks ───────────────────────────────────────────────────────────

    def collect_resources(self) -> None:
        """Zurückgekehrte Sammel-Trupps einsammeln."""
        logger.info("Bot %d: Sammle Ressourcen...", self.config.bot_id)
        self.home()
        if self.click_template("btn_collect_all", timeout=5):
            self.click_template("btn_confirm", timeout=3)
        self.save_screenshot("collect_done")

    def send_gathering(self, max_marches: int = 3) -> None:
        """Ressourcen-Felder auf der Weltkarte besetzen."""
        logger.info("Bot %d: Sende Sammel-Märsche (%d)...", self.config.bot_id, max_marches)
        self.click_template("btn_world_map")
        time.sleep(2)
        for i in range(max_marches):
            if not self.click_template("icon_resource_tile", timeout=5):
                logger.info("Bot %d: Keine Ressourcen-Felder mehr gefunden", self.config.bot_id)
                break
            self.click_template("btn_gather")
            self.click_template("btn_march")
            logger.debug("Bot %d: Marsch %d gesendet", self.config.bot_id, i + 1)
        self.home()

    def hunt_zombies(self, stamina_to_spend: int = 80) -> None:
        """Zombie-Jagd bis Stamina-Limit."""
        logger.info("Bot %d: Zombie-Jagd (Stamina: %d)...", self.config.bot_id, stamina_to_spend)
        self.click_template("btn_world_map")
        time.sleep(2)
        spent = 0
        while spent < stamina_to_spend:
            if not self.click_template("icon_zombie", timeout=5):
                logger.info("Bot %d: Keine Zombies mehr sichtbar", self.config.bot_id)
                break
            self.click_template("btn_attack")
            if self.wait_for_template("result_victory", timeout=30).found:
                spent += 10  # Stamina-Kosten pro Hunt
                logger.debug("Bot %d: Hunt erfolgreich (spent=%d)", self.config.bot_id, spent)
            else:
                break
        self.home()

    def train_troops(self) -> None:
        """Truppen-Training Queue auffüllen."""
        logger.info("Bot %d: Trainiere Truppen...", self.config.bot_id)
        self.home()
        self.click_template("btn_barracks")
        self.click_template("btn_train_max", timeout=5)
        self.click_template("btn_confirm", timeout=3)
        self.home()

    def collect_daily_rewards(self) -> None:
        """Tages-Belohnungen, VIP-Punkte, Alliance Gifts."""
        logger.info("Bot %d: Sammle Daily Rewards...", self.config.bot_id)
        self.home()
        self.click_template("btn_daily_tasks", timeout=5)
        self.click_template("btn_collect_rewards", timeout=5)
        self.back()

    def heal_troops(self) -> None:
        """Verwundete Truppen heilen."""
        logger.info("Bot %d: Heile Truppen...", self.config.bot_id)
        self.home()
        if self.find_template("icon_wounded_indicator").found:
            self.click_template("btn_hospital")
            self.click_template("btn_heal_all", timeout=5)
            self.click_template("btn_confirm", timeout=3)
            self.home()

    # ── Komplette Daily Routine ───────────────────────────────────────────────

    def run_daily_routine(self) -> None:
        """
        Vollständige Tages-Routine.
        Entspricht BlueStacks Makro-Sequenz.
        """
        logger.info("Bot %d: === Starte Daily Routine ===", self.config.bot_id)
        self.ensure_game_running()

        steps = [
            ("Daily Rewards", self.collect_daily_rewards),
            ("Ressourcen sammeln", self.collect_resources),
            ("Truppen heilen", self.heal_troops),
            ("Truppen trainieren", self.train_troops),
            ("Sammel-Märsche senden", self.send_gathering),
            ("Zombie-Jagd", lambda: self.hunt_zombies(stamina_to_spend=80)),
        ]

        for step_name, step_fn in steps:
            try:
                step_fn()
                logger.info("Bot %d: ✓ %s", self.config.bot_id, step_name)
            except Exception as exc:
                logger.error("Bot %d: ✗ %s — %s", self.config.bot_id, step_name, exc)
                self.save_screenshot(f"error_{step_name.replace(' ', '_')}")
                self.home()  # Recovery: zurück zur Base

        logger.info("Bot %d: === Daily Routine abgeschlossen ===", self.config.bot_id)
