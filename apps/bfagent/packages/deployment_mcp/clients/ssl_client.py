"""SSL Client for Let's Encrypt certificate management via SSH."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .ssh_client import SSHClient


@dataclass
class SSLCertificate:
    """SSL certificate information."""

    domain: str
    issuer: str
    valid_from: datetime | None
    valid_until: datetime | None
    days_remaining: int
    is_valid: bool
    serial_number: str | None = None
    subject_alt_names: list[str] | None = None


@dataclass
class CertbotResult:
    """Result from certbot operation."""

    success: bool
    message: str
    domains: list[str]
    certificate_path: str | None = None
    key_path: str | None = None


class SSLClient:
    """Client for SSL certificate management via SSH."""

    def __init__(self, ssh_client: SSHClient):
        """Initialize SSL client."""
        self.ssh = ssh_client

    # =========================================================================
    # CERTIFICATE STATUS
    # =========================================================================

    async def get_certificate_info(self, domain: str) -> SSLCertificate | None:
        """Get SSL certificate information for a domain."""
        # Try to get cert info using openssl
        cmd = f"echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null | openssl x509 -noout -dates -issuer -serial -subject 2>/dev/null"

        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=30)

        if exit_code != 0 or not stdout.strip():
            # Try local certificate file
            return await self._get_local_cert_info(domain)

        return self._parse_cert_info(domain, stdout)

    async def _get_local_cert_info(self, domain: str) -> SSLCertificate | None:
        """Get certificate info from local Let's Encrypt directory."""
        cert_path = f"/etc/letsencrypt/live/{domain}/cert.pem"

        if not await self.ssh.file_exists(cert_path):
            return None

        cmd = f"openssl x509 -in {cert_path} -noout -dates -issuer -serial -subject"
        stdout, _, exit_code = await self.ssh.run(cmd)

        if exit_code != 0:
            return None

        return self._parse_cert_info(domain, stdout)

    def _parse_cert_info(self, domain: str, output: str) -> SSLCertificate:
        """Parse certificate information from openssl output."""
        lines = output.strip().split("\n")

        valid_from = None
        valid_until = None
        issuer = "Unknown"
        serial = None

        for line in lines:
            line = line.strip()
            if line.startswith("notBefore="):
                date_str = line.replace("notBefore=", "")
                valid_from = self._parse_date(date_str)
            elif line.startswith("notAfter="):
                date_str = line.replace("notAfter=", "")
                valid_until = self._parse_date(date_str)
            elif line.startswith("issuer="):
                issuer = line.replace("issuer=", "").strip()
            elif line.startswith("serial="):
                serial = line.replace("serial=", "").strip()

        days_remaining = 0
        is_valid = False

        if valid_until:
            delta = valid_until - datetime.now()
            days_remaining = max(0, delta.days)
            is_valid = days_remaining > 0

        return SSLCertificate(
            domain=domain,
            issuer=issuer,
            valid_from=valid_from,
            valid_until=valid_until,
            days_remaining=days_remaining,
            is_valid=is_valid,
            serial_number=serial,
        )

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date from openssl format."""
        formats = [
            "%b %d %H:%M:%S %Y %Z",
            "%b  %d %H:%M:%S %Y %Z",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    async def list_certificates(self) -> list[SSLCertificate]:
        """List all Let's Encrypt certificates."""
        cmd = "ls -1 /etc/letsencrypt/live/ 2>/dev/null | grep -v README"
        stdout, _, exit_code = await self.ssh.run(cmd)

        if exit_code != 0 or not stdout.strip():
            return []

        certificates = []
        for domain in stdout.strip().split("\n"):
            domain = domain.strip()
            if domain:
                cert_info = await self._get_local_cert_info(domain)
                if cert_info:
                    certificates.append(cert_info)

        return certificates

    async def check_expiring_soon(self, days: int = 30) -> list[SSLCertificate]:
        """Get certificates expiring within specified days."""
        certificates = await self.list_certificates()
        return [cert for cert in certificates if cert.days_remaining <= days]

    # =========================================================================
    # CERTIFICATE MANAGEMENT
    # =========================================================================

    async def renew_certificate(
        self,
        domain: str | None = None,
        force: bool = False,
    ) -> CertbotResult:
        """Renew SSL certificate using certbot."""
        if domain:
            cmd = f"certbot renew --cert-name {domain}"
            if force:
                cmd += " --force-renewal"
        else:
            cmd = "certbot renew"
            if force:
                cmd += " --force-renewal"

        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=300)
        output = stdout or stderr

        success = exit_code == 0 and "Congratulations" in output or "No renewals were attempted" in output

        # Extract renewed domains
        domains = []
        if domain:
            domains = [domain]
        else:
            for line in output.split("\n"):
                if "renewed" in line.lower() and "certificate" in line.lower():
                    # Try to extract domain from line
                    parts = line.split()
                    for part in parts:
                        if "." in part and not part.startswith("/"):
                            domains.append(part.strip("()"))

        return CertbotResult(
            success=success,
            message=output,
            domains=domains,
        )

    async def obtain_certificate(
        self,
        domains: list[str],
        email: str,
        webroot_path: str | None = None,
        standalone: bool = False,
        dry_run: bool = False,
    ) -> CertbotResult:
        """Obtain a new SSL certificate."""
        domain_args = " ".join([f"-d {d}" for d in domains])

        if standalone:
            cmd = f"certbot certonly --standalone {domain_args} --email {email} --agree-tos --non-interactive"
        elif webroot_path:
            cmd = f"certbot certonly --webroot -w {webroot_path} {domain_args} --email {email} --agree-tos --non-interactive"
        else:
            # Default to nginx plugin if available
            cmd = f"certbot --nginx {domain_args} --email {email} --agree-tos --non-interactive"

        if dry_run:
            cmd += " --dry-run"

        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=300)
        output = stdout or stderr

        success = exit_code == 0

        cert_path = None
        key_path = None

        if success and domains:
            primary_domain = domains[0]
            cert_path = f"/etc/letsencrypt/live/{primary_domain}/fullchain.pem"
            key_path = f"/etc/letsencrypt/live/{primary_domain}/privkey.pem"

        return CertbotResult(
            success=success,
            message=output,
            domains=domains,
            certificate_path=cert_path,
            key_path=key_path,
        )

    async def revoke_certificate(
        self,
        domain: str,
        reason: str = "unspecified",
    ) -> CertbotResult:
        """Revoke an SSL certificate."""
        cert_path = f"/etc/letsencrypt/live/{domain}/cert.pem"

        cmd = f"certbot revoke --cert-path {cert_path} --reason {reason} --non-interactive"
        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=120)

        return CertbotResult(
            success=exit_code == 0,
            message=stdout or stderr,
            domains=[domain],
        )

    async def delete_certificate(self, domain: str) -> CertbotResult:
        """Delete a certificate from certbot."""
        cmd = f"certbot delete --cert-name {domain} --non-interactive"
        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=60)

        return CertbotResult(
            success=exit_code == 0,
            message=stdout or stderr,
            domains=[domain],
        )

    # =========================================================================
    # CERTBOT STATUS
    # =========================================================================

    async def get_certbot_version(self) -> str | None:
        """Get certbot version."""
        stdout, _, exit_code = await self.ssh.run("certbot --version")
        if exit_code == 0:
            return stdout.strip()
        return None

    async def is_certbot_installed(self) -> bool:
        """Check if certbot is installed."""
        _, _, exit_code = await self.ssh.run("which certbot")
        return exit_code == 0

    async def get_certbot_certificates(self) -> str:
        """Get certbot certificates list."""
        stdout, stderr, _ = await self.ssh.run("certbot certificates")
        return stdout or stderr
