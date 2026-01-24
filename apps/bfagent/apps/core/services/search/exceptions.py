"""
Core Search Service - Exceptions

Custom exceptions for search operations.
"""


class SearchException(Exception):
    """Base exception for search errors"""

    pass


class SearchBackendNotAvailable(SearchException):
    """Search backend dependencies not installed"""

    def __init__(self, backend: str, dependencies: list):
        self.backend = backend
        self.dependencies = dependencies
        super().__init__(
            f"Search backend '{backend}' not available. "
            f"Install: pip install {' '.join(dependencies)}"
        )


class SearchIndexNotBuilt(SearchException):
    """Search index not built yet"""

    def __init__(self, namespace: str = None):
        msg = f"Search index not built"
        if namespace:
            msg += f" for namespace '{namespace}'"
        msg += ". Call build_index() first."
        super().__init__(msg)


class SearchIndexCorrupted(SearchException):
    """Search index corrupted or invalid"""

    pass


class InvalidSearchQuery(SearchException):
    """Invalid search query"""

    pass


class NamespaceNotFound(SearchException):
    """Namespace not found"""

    def __init__(self, namespace: str):
        super().__init__(f"Search namespace '{namespace}' not found")


__all__ = [
    "SearchException",
    "SearchBackendNotAvailable",
    "SearchIndexNotBuilt",
    "SearchIndexCorrupted",
    "InvalidSearchQuery",
    "NamespaceNotFound",
]
