"""
Domain Detection Utilities
Automatically detect domain from URL patterns
"""

from typing import Optional

from django.urls import Resolver404, resolve

from ..models_workflow_domains import WorkflowDomain


class DomainDetector:
    """
    Detects the current domain based on URL patterns
    """

    # URL pattern to domain mapping (use actual domain.code from database)
    URL_DOMAIN_MAP = {
        # Control Center Domain
        "control_center": "control_hub",
        "control-center": "control_hub",
        # Writing Hub Domain
        "writing_hub": "writing_hub",
        "writing-hub": "writing_hub",
        "bookwriting": "writing_hub",
        # Medical Translation Domain
        "medtrans": "medtrans",
        "med-trans": "medtrans",
        # GenAgent Domain
        "genagent": "genagent",
        "gen-agent": "genagent",
        # Default fallback
        "admin": "control_hub",
    }

    @classmethod
    def detect_from_url(cls, request) -> Optional[str]:
        """
        Detect domain from current request URL

        Args:
            request: Django request object

        Returns:
            Domain code string or None
        """
        try:
            # Get the current URL path
            path = request.path

            # Try to resolve the URL to get app/namespace info
            resolved = resolve(path)

            # Check namespace first (most reliable)
            if resolved.namespace:
                domain = cls._get_domain_from_namespace(resolved.namespace)
                if domain:
                    return domain

            # Check URL pattern name
            if resolved.url_name:
                domain = cls._get_domain_from_url_name(resolved.url_name)
                if domain:
                    return domain

            # Check path segments
            domain = cls._get_domain_from_path(path)
            if domain:
                return domain

        except (Resolver404, AttributeError):
            # Fallback to path-based detection
            return cls._get_domain_from_path(request.path)

        return None

    @classmethod
    def _get_domain_from_namespace(cls, namespace: str) -> Optional[str]:
        """Get domain from URL namespace"""
        return cls.URL_DOMAIN_MAP.get(namespace)

    @classmethod
    def _get_domain_from_url_name(cls, url_name: str) -> Optional[str]:
        """Get domain from URL name patterns"""
        for pattern, domain in cls.URL_DOMAIN_MAP.items():
            if pattern in url_name.lower():
                return domain
        return None

    @classmethod
    def _get_domain_from_path(cls, path: str) -> Optional[str]:
        """Get domain from URL path segments"""
        path_segments = [seg for seg in path.split("/") if seg]

        if not path_segments:
            return None

        # Check first path segment
        first_segment = path_segments[0].lower()

        # Direct mapping
        if first_segment in cls.URL_DOMAIN_MAP:
            return cls.URL_DOMAIN_MAP[first_segment]

        # Pattern matching
        for pattern, domain in cls.URL_DOMAIN_MAP.items():
            if pattern in first_segment:
                return domain

        return None

    @classmethod
    def get_domain_object(cls, domain_code: str) -> Optional[WorkflowDomain]:
        """
        Get WorkflowDomain object by code

        Args:
            domain_code: Domain code string

        Returns:
            WorkflowDomain object or None
        """
        try:
            return WorkflowDomain.objects.get(code=domain_code)
        except WorkflowDomain.DoesNotExist:
            return None

    @classmethod
    def get_current_domain(cls, request) -> Optional[WorkflowDomain]:
        """
        Get current domain object from request

        Args:
            request: Django request object

        Returns:
            WorkflowDomain object or None
        """
        domain_code = cls.detect_from_url(request)
        if domain_code:
            return cls.get_domain_object(domain_code)
        return None


def get_current_domain_code(request) -> Optional[str]:
    """
    Convenience function to get current domain code

    Args:
        request: Django request object

    Returns:
        Domain code string or None
    """
    return DomainDetector.detect_from_url(request)


def get_current_domain(request) -> Optional[WorkflowDomain]:
    """
    Convenience function to get current domain object

    Args:
        request: Django request object

    Returns:
        WorkflowDomain object or None
    """
    return DomainDetector.get_current_domain(request)
