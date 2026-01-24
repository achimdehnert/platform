"""
Database Configuration - UTF-8 Safe Settings

This module provides UTF-8 safe database configurations to prevent
UnicodeDecodeError issues with PostgreSQL connections.

CRITICAL: Forces UTF-8 encoding system-wide on Windows!
"""

import locale
import os
import sys

# CRITICAL: Force UTF-8 Mode (Python 3.7+)
os.environ["PYTHONUTF8"] = "1"

# Force UTF-8 for all file operations
if sys.platform == "win32":
    # Windows-specific: Force UTF-8 console encoding
    try:
        # Set console to UTF-8
        os.system("chcp 65001 > nul")
    except:
        pass

    # Try to set locale to UTF-8
    try:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    except:
        try:
            locale.setlocale(locale.LC_ALL, "C.UTF-8")
        except:
            pass


def get_postgres_config(config_func):
    """
    Get PostgreSQL configuration with enforced UTF-8 encoding.

    This prevents UnicodeDecodeError: 'utf-8' codec can't decode byte 0xfc

    Args:
        config_func: decouple.config function

    Returns:
        dict: PostgreSQL database configuration
    """
    # Force UTF-8 encoding in environment (CRITICAL!)
    os.environ.setdefault("PGCLIENTENCODING", "UTF8")
    os.environ.setdefault("LANG", "en_US.UTF-8")
    os.environ.setdefault("LC_ALL", "en_US.UTF-8")

    # Get values from .env with explicit UTF-8 handling
    # CRITICAL: Ensure strings are properly decoded
    def safe_config(key, default=None):
        value = config_func(key, default=default)
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    return {
        "default": {
            # CRITICAL: Use custom backend with UTF-8 safety for Windows
            "ENGINE": "db_backends.postgresql_utf8",
            "NAME": safe_config("POSTGRES_DB", default="bfagent_dev"),
            "USER": safe_config("POSTGRES_USER", default="bfagent"),
            "PASSWORD": safe_config("POSTGRES_PASSWORD", default="bfagent_dev_2024"),
            "HOST": safe_config("POSTGRES_HOST", default="localhost"),
            "PORT": safe_config("POSTGRES_PORT", default="5432"),
            "CONN_MAX_AGE": 600,
            "OPTIONS": {
                "connect_timeout": 10,
                # CRITICAL: Force UTF-8 encoding on connection
                "client_encoding": "UTF8",
                # CRITICAL FIX: Force English error messages (not German with Latin-1 ü)
                # This prevents: UnicodeDecodeError from "für Benutzer" (0xfc byte)
                "options": "-c lc_messages=C -c client_encoding=UTF8",
            },
            # Atomic requests for data integrity
            "ATOMIC_REQUESTS": True,
            # Connection pooling
            "CONN_HEALTH_CHECKS": True,
        }
    }


def get_sqlite_config(base_dir):
    """
    Get SQLite configuration.

    Args:
        base_dir: Project base directory

    Returns:
        dict: SQLite database configuration
    """
    sqlite_path = os.environ.get("SQLITE_PATH")
    if sqlite_path:
        db_name = sqlite_path
    else:
        db_name = base_dir / "db.sqlite3"

    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": db_name,
            "OPTIONS": {
                # SQLite doesn't need encoding options
            },
        }
    }
