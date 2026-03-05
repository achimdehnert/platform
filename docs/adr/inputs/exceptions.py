"""
aifw/exceptions.py — Exception hierarchy for aifw 0.6.0.

Design principle: ConfigurationError is a DEPLOYMENT defect, not a runtime user error.
It must never be caught silently. It indicates a missing AIActionType catch-all row.

AuthenticationError, ProviderError are runtime errors that MAY be caught.
"""
from __future__ import annotations


class AIFWError(Exception):
    """Base class for all aifw exceptions."""


class ConfigurationError(AIFWError):
    """
    Raised when no AIActionType row matches the given (code, quality_level, priority).

    This is a DEPLOYMENT DEFECT — a catch-all row (quality_level=NULL, priority=NULL)
    must exist for every action_code. If this exception reaches production, it means
    the DB seeding step was skipped or an action_code was added without a catch-all.

    Do NOT catch this in views — let it propagate as HTTP 500.
    Use 'python manage.py check_aifw_config' in CI to prevent this.
    """


class ProviderError(AIFWError):
    """
    Raised when the LLM provider returns an error (rate limit, server error, etc.).

    This is a runtime error that MAY be caught and handled with fallback logic.
    The fallback_model on AIActionType is used automatically before this is raised.
    """


class AuthenticationError(ProviderError):
    """API key missing or invalid for the configured provider."""


class TokenBudgetExceededError(AIFWError):
    """
    Raised when a request would exceed the budget_per_day limit on AIActionType.

    Consumer apps MAY catch this to show a user-facing message.
    """
