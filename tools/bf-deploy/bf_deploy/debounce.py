"""Debounce logic to prevent excessive deploy triggers.

NOTE: No file-locking — acceptable for single-developer use.
Parallel bf deploy calls may cause double-triggers.
"""
from __future__ import annotations

import json
import time

from .config import DEBOUNCE_FILE, DEBOUNCE_SECONDS


def _load() -> dict:
    """Load debounce state from disk."""
    if DEBOUNCE_FILE.exists():
        return json.loads(DEBOUNCE_FILE.read_text())
    return {}


def _save(data: dict) -> None:
    """Persist debounce state to disk."""
    DEBOUNCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEBOUNCE_FILE.write_text(json.dumps(data))


def is_debounced(app: str) -> bool:
    """Return True if app was triggered within DEBOUNCE_SECONDS."""
    data = _load()
    last = data.get(app, 0)
    return (time.time() - last) < DEBOUNCE_SECONDS


def mark_triggered(app: str) -> None:
    """Record that app was just triggered."""
    data = _load()
    data[app] = time.time()
    _save(data)
