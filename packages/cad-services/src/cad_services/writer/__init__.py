from .base import BaseWriter, WriteResult

__all__ = [
    "BaseWriter",
    "WriteResult",
]

try:
    from .postgres import PostgresWriter

    __all__.append("PostgresWriter")
except ImportError:
    pass
