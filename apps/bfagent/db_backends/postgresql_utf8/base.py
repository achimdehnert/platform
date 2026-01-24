"""
Custom PostgreSQL Database Backend with UTF-8 Safety

CRITICAL FIX for Windows: Ensures ALL connection parameters are UTF-8 encoded
before being passed to psycopg2.

This fixes: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xfc in position 97
"""

import logging

from django.db.backends.postgresql import base

logger = logging.getLogger(__name__)


class DatabaseWrapper(base.DatabaseWrapper):
    """
    Custom PostgreSQL wrapper that ensures UTF-8 encoding for all connection parameters.

    This is necessary on Windows where system paths, usernames, or computer names
    may contain non-ASCII characters (ü, ö, ä, ß) that psycopg2 can't handle
    in the default system encoding.
    """

    def get_connection_params(self):
        """
        Get connection parameters with UTF-8 safety.

        Override parent method to ensure ALL parameters are properly UTF-8 encoded
        before being passed to psycopg2.
        """
        # Get original parameters from parent
        conn_params = super().get_connection_params()

        # CRITICAL: Ensure all string parameters are UTF-8 encoded
        safe_params = {}
        for key, value in conn_params.items():
            if isinstance(value, str):
                # Ensure string is UTF-8 safe
                try:
                    # Try to encode/decode to catch any encoding issues
                    value = value.encode("utf-8", errors="replace").decode("utf-8")
                except (UnicodeDecodeError, UnicodeEncodeError):
                    # If that fails, use ASCII with replacements
                    value = value.encode("ascii", errors="replace").decode("ascii")
            elif isinstance(value, bytes):
                # Convert bytes to UTF-8 string
                try:
                    value = value.decode("utf-8", errors="replace")
                except UnicodeDecodeError:
                    value = value.decode("ascii", errors="replace")
            elif isinstance(value, dict):
                # Recursively handle nested dictionaries (like OPTIONS)
                value = self._sanitize_dict(value)

            safe_params[key] = value

        # Force UTF-8 client encoding in options
        if "options" not in safe_params:
            safe_params["options"] = {}

        if isinstance(safe_params["options"], str):
            # If options is a string, append UTF-8 encoding
            safe_params["options"] = f"{safe_params['options']} -c client_encoding=UTF8"
        elif isinstance(safe_params["options"], dict):
            safe_params["options"]["client_encoding"] = "UTF8"

        return safe_params

    def get_new_connection(self, conn_params):
        """
        Override to ensure DSN string is UTF-8 safe.

        The problem: psycopg2 builds a DSN string internally from conn_params,
        and this DSN string can contain non-UTF-8 bytes from Windows environment.

        Solution: Aggressively sanitize ALL parameters before passing to psycopg2.
        """
        # CRITICAL: Strip any non-ASCII characters from ALL parameters
        safe_params = {}

        for key, value in conn_params.items():
            if value is None:
                safe_params[key] = value
                continue

            if isinstance(value, str):
                # AGGRESSIVE: Only keep ASCII characters, replace all others
                try:
                    # First try: encode as UTF-8, then decode back
                    clean_value = value.encode("utf-8", errors="ignore").decode("utf-8")
                    # Second try: ensure it's ASCII-safe for DSN
                    clean_value = clean_value.encode("ascii", errors="ignore").decode("ascii")
                    safe_params[key] = clean_value if clean_value else value

                    if clean_value != value:
                        logger.warning(
                            f"Sanitized connection param '{key}': "
                            f"'{value[:50]}' -> '{clean_value[:50]}'"
                        )
                except Exception as e:
                    logger.error(f"Failed to sanitize param '{key}': {e}")
                    # Last resort: remove the parameter entirely
                    safe_params[key] = ""
            elif isinstance(value, dict):
                safe_params[key] = self._sanitize_dict(value)
            else:
                safe_params[key] = value

        # Log final params for debugging
        logger.info(f"Connecting to PostgreSQL with sanitized params: {list(safe_params.keys())}")

        # Call parent with cleaned parameters
        return super().get_new_connection(safe_params)

    def _sanitize_dict(self, d):
        """
        Recursively sanitize all strings in a dictionary to UTF-8.

        Args:
            d: Dictionary to sanitize

        Returns:
            Sanitized dictionary with all strings as UTF-8
        """
        result = {}
        for key, value in d.items():
            if isinstance(value, str):
                try:
                    value = value.encode("utf-8", errors="replace").decode("utf-8")
                except (UnicodeDecodeError, UnicodeEncodeError):
                    value = value.encode("ascii", errors="replace").decode("ascii")
            elif isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="replace")
                except UnicodeDecodeError:
                    value = value.decode("ascii", errors="replace")
            elif isinstance(value, dict):
                value = self._sanitize_dict(value)

            result[key] = value

        return result
