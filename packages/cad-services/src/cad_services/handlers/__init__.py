"""
CAD Services Handlers - Application Layer.

Handler Pattern mit Pydantic Commands/Results.
"""

from cad_services.handlers.commands import (
    CalculateDIN277Command,
    CalculateDIN277Result,
    CalculateWoFlVCommand,
    CalculateWoFlVResult,
    ListRoomsCommand,
    ListRoomsResult,
    ListWindowsCommand,
    ListWindowsResult,
    ParseIFCCommand,
    ParseIFCResult,
)
from cad_services.handlers.parse_ifc import ParseIFCHandler


__all__ = [
    "ParseIFCCommand",
    "ParseIFCResult",
    "ListRoomsCommand",
    "ListRoomsResult",
    "ListWindowsCommand",
    "ListWindowsResult",
    "CalculateDIN277Command",
    "CalculateDIN277Result",
    "CalculateWoFlVCommand",
    "CalculateWoFlVResult",
    "ParseIFCHandler",
]
