from __future__ import annotations


class CADError(Exception):
    def __init__(self, code: str, message: str, *, suggestion: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.suggestion = suggestion


class CADParseError(CADError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        file_path: str | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(code, message, suggestion=suggestion)
        self.file_path = file_path


class CADSecurityError(CADError):
    pass


class CADResourceError(CADError):
    pass
