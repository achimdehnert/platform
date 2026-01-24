"""DNS Client for Hetzner DNS API."""

from datetime import datetime
from typing import Any

import httpx

from ..settings import settings


class DNSRecord:
    """DNS record representation."""

    def __init__(
        self,
        id: str,
        zone_id: str,
        name: str,
        type: str,
        value: str,
        ttl: int = 3600,
        created: datetime | None = None,
        modified: datetime | None = None,
    ):
        self.id = id
        self.zone_id = zone_id
        self.name = name
        self.type = type
        self.value = value
        self.ttl = ttl
        self.created = created
        self.modified = modified

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "zone_id": self.zone_id,
            "name": self.name,
            "type": self.type,
            "value": self.value,
            "ttl": self.ttl,
        }


class DNSZone:
    """DNS zone representation."""

    def __init__(
        self,
        id: str,
        name: str,
        ttl: int = 3600,
        ns: list[str] | None = None,
        records_count: int = 0,
        created: datetime | None = None,
        modified: datetime | None = None,
    ):
        self.id = id
        self.name = name
        self.ttl = ttl
        self.ns = ns or []
        self.records_count = records_count
        self.created = created
        self.modified = modified

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "ttl": self.ttl,
            "ns": self.ns,
            "records_count": self.records_count,
        }


class DNSClient:
    """Client for Hetzner DNS API."""

    BASE_URL = "https://dns.hetzner.com/api/v1"

    def __init__(self, api_token: str | None = None):
        """Initialize DNS client."""
        # Use Hetzner API token (same as cloud API or separate DNS token)
        self.api_token = api_token or settings.hetzner_api_token.get_secret_value()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Auth-API-Token": self.api_token,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # ZONE OPERATIONS
    # =========================================================================

    async def list_zones(self, name: str | None = None) -> list[DNSZone]:
        """List all DNS zones."""
        client = await self._get_client()
        params = {}
        if name:
            params["name"] = name

        response = await client.get("/zones", params=params)
        response.raise_for_status()
        data = response.json()

        return [self._parse_zone(z) for z in data.get("zones", [])]

    async def get_zone(self, zone_id: str) -> DNSZone:
        """Get zone by ID."""
        client = await self._get_client()
        response = await client.get(f"/zones/{zone_id}")
        response.raise_for_status()
        return self._parse_zone(response.json()["zone"])

    async def get_zone_by_name(self, name: str) -> DNSZone | None:
        """Get zone by name."""
        zones = await self.list_zones(name=name)
        for zone in zones:
            if zone.name == name:
                return zone
        return None

    async def create_zone(self, name: str, ttl: int = 3600) -> DNSZone:
        """Create a new DNS zone."""
        client = await self._get_client()
        response = await client.post(
            "/zones",
            json={"name": name, "ttl": ttl},
        )
        response.raise_for_status()
        return self._parse_zone(response.json()["zone"])

    async def delete_zone(self, zone_id: str) -> bool:
        """Delete a DNS zone."""
        client = await self._get_client()
        response = await client.delete(f"/zones/{zone_id}")
        response.raise_for_status()
        return True

    # =========================================================================
    # RECORD OPERATIONS
    # =========================================================================

    async def list_records(self, zone_id: str) -> list[DNSRecord]:
        """List all records in a zone."""
        client = await self._get_client()
        response = await client.get("/records", params={"zone_id": zone_id})
        response.raise_for_status()
        data = response.json()

        return [self._parse_record(r) for r in data.get("records", [])]

    async def get_record(self, record_id: str) -> DNSRecord:
        """Get record by ID."""
        client = await self._get_client()
        response = await client.get(f"/records/{record_id}")
        response.raise_for_status()
        return self._parse_record(response.json()["record"])

    async def create_record(
        self,
        zone_id: str,
        name: str,
        type: str,
        value: str,
        ttl: int = 3600,
    ) -> DNSRecord:
        """Create a new DNS record."""
        client = await self._get_client()
        response = await client.post(
            "/records",
            json={
                "zone_id": zone_id,
                "name": name,
                "type": type,
                "value": value,
                "ttl": ttl,
            },
        )
        response.raise_for_status()
        return self._parse_record(response.json()["record"])

    async def update_record(
        self,
        record_id: str,
        zone_id: str,
        name: str,
        type: str,
        value: str,
        ttl: int = 3600,
    ) -> DNSRecord:
        """Update a DNS record."""
        client = await self._get_client()
        response = await client.put(
            f"/records/{record_id}",
            json={
                "zone_id": zone_id,
                "name": name,
                "type": type,
                "value": value,
                "ttl": ttl,
            },
        )
        response.raise_for_status()
        return self._parse_record(response.json()["record"])

    async def delete_record(self, record_id: str) -> bool:
        """Delete a DNS record."""
        client = await self._get_client()
        response = await client.delete(f"/records/{record_id}")
        response.raise_for_status()
        return True

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    async def find_records(
        self,
        zone_id: str,
        name: str | None = None,
        record_type: str | None = None,
    ) -> list[DNSRecord]:
        """Find records by name and/or type."""
        records = await self.list_records(zone_id)

        if name:
            records = [r for r in records if r.name == name]
        if record_type:
            records = [r for r in records if r.type == record_type]

        return records

    async def upsert_record(
        self,
        zone_id: str,
        name: str,
        type: str,
        value: str,
        ttl: int = 3600,
    ) -> DNSRecord:
        """Create or update a DNS record."""
        existing = await self.find_records(zone_id, name=name, record_type=type)

        if existing:
            # Update first matching record
            return await self.update_record(
                record_id=existing[0].id,
                zone_id=zone_id,
                name=name,
                type=type,
                value=value,
                ttl=ttl,
            )
        else:
            # Create new record
            return await self.create_record(
                zone_id=zone_id,
                name=name,
                type=type,
                value=value,
                ttl=ttl,
            )

    async def set_a_record(
        self,
        domain: str,
        subdomain: str,
        ip: str,
        ttl: int = 3600,
    ) -> DNSRecord:
        """Set an A record for a subdomain."""
        zone = await self.get_zone_by_name(domain)
        if not zone:
            raise ValueError(f"Zone not found: {domain}")

        return await self.upsert_record(
            zone_id=zone.id,
            name=subdomain,
            type="A",
            value=ip,
            ttl=ttl,
        )

    async def set_cname_record(
        self,
        domain: str,
        subdomain: str,
        target: str,
        ttl: int = 3600,
    ) -> DNSRecord:
        """Set a CNAME record."""
        zone = await self.get_zone_by_name(domain)
        if not zone:
            raise ValueError(f"Zone not found: {domain}")

        return await self.upsert_record(
            zone_id=zone.id,
            name=subdomain,
            type="CNAME",
            value=target,
            ttl=ttl,
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _parse_zone(self, data: dict[str, Any]) -> DNSZone:
        """Parse zone from API response."""
        return DNSZone(
            id=data["id"],
            name=data["name"],
            ttl=data.get("ttl", 3600),
            ns=data.get("ns", []),
            records_count=data.get("records_count", 0),
            created=data.get("created"),
            modified=data.get("modified"),
        )

    def _parse_record(self, data: dict[str, Any]) -> DNSRecord:
        """Parse record from API response."""
        return DNSRecord(
            id=data["id"],
            zone_id=data["zone_id"],
            name=data["name"],
            type=data["type"],
            value=data["value"],
            ttl=data.get("ttl", 3600),
            created=data.get("created"),
            modified=data.get("modified"),
        )
