"""SSL Certificate Tools for MCP."""

from typing import Any

from ..clients.ssl_client import SSLClient
from ..clients.ssh_client import SSHClient
from ..settings import settings


def _get_ssl_client(host: str | None = None) -> tuple[SSHClient, SSLClient]:
    """Get SSH and SSL clients."""
    ssh = SSHClient(host=host or settings.ssh_host)
    ssl = SSLClient(ssh)
    return ssh, ssl


# =============================================================================
# SSL CERTIFICATE STATUS
# =============================================================================


async def ssl_status(
    domain: str | None = None,
    host: str | None = None,
) -> dict[str, Any]:
    """
    Get SSL certificate status.

    Args:
        domain: Specific domain to check (optional, lists all if not provided)
        host: SSH host to connect to
    """
    ssh, ssl = _get_ssl_client(host)
    try:
        await ssh.connect()

        if domain:
            # Get specific domain
            cert = await ssl.get_certificate_info(domain)
            if not cert:
                return {
                    "success": False,
                    "error": f"No certificate found for {domain}",
                }

            return {
                "success": True,
                "certificate": {
                    "domain": cert.domain,
                    "issuer": cert.issuer,
                    "valid_from": cert.valid_from.isoformat() if cert.valid_from else None,
                    "valid_until": cert.valid_until.isoformat() if cert.valid_until else None,
                    "days_remaining": cert.days_remaining,
                    "is_valid": cert.is_valid,
                    "serial_number": cert.serial_number,
                },
            }
        else:
            # List all certificates
            certificates = await ssl.list_certificates()
            return {
                "success": True,
                "count": len(certificates),
                "certificates": [
                    {
                        "domain": cert.domain,
                        "issuer": cert.issuer,
                        "valid_until": cert.valid_until.isoformat() if cert.valid_until else None,
                        "days_remaining": cert.days_remaining,
                        "is_valid": cert.is_valid,
                    }
                    for cert in certificates
                ],
            }
    finally:
        await ssh.disconnect()


async def ssl_expiring(
    days: int = 30,
    host: str | None = None,
) -> dict[str, Any]:
    """
    Get certificates expiring within specified days.

    Args:
        days: Number of days to check (default 30)
        host: SSH host to connect to
    """
    ssh, ssl = _get_ssl_client(host)
    try:
        await ssh.connect()
        certificates = await ssl.check_expiring_soon(days)

        return {
            "success": True,
            "days_threshold": days,
            "count": len(certificates),
            "expiring_certificates": [
                {
                    "domain": cert.domain,
                    "valid_until": cert.valid_until.isoformat() if cert.valid_until else None,
                    "days_remaining": cert.days_remaining,
                }
                for cert in certificates
            ],
        }
    finally:
        await ssh.disconnect()


# =============================================================================
# SSL CERTIFICATE MANAGEMENT
# =============================================================================


async def ssl_renew(
    domain: str | None = None,
    force: bool = False,
    host: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Renew SSL certificate using certbot.

    Args:
        domain: Specific domain to renew (optional, renews all if not provided)
        force: Force renewal even if not expiring soon
        host: SSH host to connect to
        confirm: Must be True to execute
    """
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to renew certificate.",
            "would_renew": domain or "all certificates",
        }

    ssh, ssl = _get_ssl_client(host)
    try:
        await ssh.connect()

        # Check if certbot is installed
        if not await ssl.is_certbot_installed():
            return {
                "success": False,
                "error": "Certbot is not installed on the server",
            }

        result = await ssl.renew_certificate(domain, force)

        return {
            "success": result.success,
            "message": result.message[:500] if len(result.message) > 500 else result.message,
            "domains": result.domains,
        }
    finally:
        await ssh.disconnect()


async def ssl_obtain(
    domains: list[str],
    email: str,
    webroot_path: str | None = None,
    standalone: bool = False,
    dry_run: bool = False,
    host: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Obtain a new SSL certificate.

    Args:
        domains: List of domains to include in certificate
        email: Email for Let's Encrypt notifications
        webroot_path: Path to webroot for webroot authentication
        standalone: Use standalone mode (stops web server temporarily)
        dry_run: Test without actually obtaining certificate
        host: SSH host to connect to
        confirm: Must be True to execute
    """
    if not dry_run and settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to obtain certificate.",
            "would_obtain_for": domains,
        }

    ssh, ssl = _get_ssl_client(host)
    try:
        await ssh.connect()

        if not await ssl.is_certbot_installed():
            return {
                "success": False,
                "error": "Certbot is not installed on the server",
            }

        result = await ssl.obtain_certificate(
            domains=domains,
            email=email,
            webroot_path=webroot_path,
            standalone=standalone,
            dry_run=dry_run,
        )

        return {
            "success": result.success,
            "message": result.message[:500] if len(result.message) > 500 else result.message,
            "domains": result.domains,
            "certificate_path": result.certificate_path,
            "key_path": result.key_path,
            "dry_run": dry_run,
        }
    finally:
        await ssh.disconnect()


async def ssl_revoke(
    domain: str,
    reason: str = "unspecified",
    host: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Revoke an SSL certificate.

    Args:
        domain: Domain whose certificate to revoke
        reason: Reason for revocation
        host: SSH host to connect to
        confirm: Must be True to execute
    """
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to revoke certificate.",
            "would_revoke": domain,
        }

    ssh, ssl = _get_ssl_client(host)
    try:
        await ssh.connect()
        result = await ssl.revoke_certificate(domain, reason)

        return {
            "success": result.success,
            "message": result.message[:500] if len(result.message) > 500 else result.message,
            "domain": domain,
        }
    finally:
        await ssh.disconnect()


async def ssl_delete(
    domain: str,
    host: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Delete a certificate from certbot.

    Args:
        domain: Domain whose certificate to delete
        host: SSH host to connect to
        confirm: Must be True to execute
    """
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to delete certificate.",
            "would_delete": domain,
        }

    ssh, ssl = _get_ssl_client(host)
    try:
        await ssh.connect()
        result = await ssl.delete_certificate(domain)

        return {
            "success": result.success,
            "message": result.message,
            "domain": domain,
        }
    finally:
        await ssh.disconnect()


# =============================================================================
# CERTBOT STATUS
# =============================================================================


async def ssl_certbot_info(host: str | None = None) -> dict[str, Any]:
    """
    Get certbot installation info.

    Args:
        host: SSH host to connect to
    """
    ssh, ssl = _get_ssl_client(host)
    try:
        await ssh.connect()

        installed = await ssl.is_certbot_installed()
        version = await ssl.get_certbot_version() if installed else None
        certs_info = await ssl.get_certbot_certificates() if installed else ""

        return {
            "success": True,
            "installed": installed,
            "version": version,
            "certificates_info": certs_info[:2000] if len(certs_info) > 2000 else certs_info,
        }
    finally:
        await ssh.disconnect()
