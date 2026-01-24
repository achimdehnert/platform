"""DNS Management Tools for MCP (Hetzner DNS API)."""

from typing import Any

from ..clients.dns_client import DNSClient
from ..settings import settings


# =============================================================================
# DNS ZONE OPERATIONS
# =============================================================================


async def dns_zone_list() -> dict[str, Any]:
    """List all DNS zones."""
    client = DNSClient()
    try:
        zones = await client.list_zones()
        return {
            "success": True,
            "count": len(zones),
            "zones": [zone.to_dict() for zone in zones],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_zone_get(
    zone_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """
    Get DNS zone details.

    Args:
        zone_id: Zone ID
        name: Zone name (domain)
    """
    client = DNSClient()
    try:
        if zone_id:
            zone = await client.get_zone(zone_id)
        elif name:
            zone = await client.get_zone_by_name(name)
            if not zone:
                return {"success": False, "error": f"Zone not found: {name}"}
        else:
            return {"success": False, "error": "Either zone_id or name required"}

        return {
            "success": True,
            "zone": zone.to_dict(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_zone_create(
    name: str,
    ttl: int = 3600,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Create a new DNS zone.

    Args:
        name: Zone name (domain)
        ttl: Default TTL in seconds
        confirm: Must be True to execute
    """
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to create zone.",
            "would_create": name,
        }

    client = DNSClient()
    try:
        zone = await client.create_zone(name, ttl)
        return {
            "success": True,
            "zone": zone.to_dict(),
            "message": f"Zone '{name}' created successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_zone_delete(
    zone_id: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Delete a DNS zone.

    Args:
        zone_id: Zone ID to delete
        confirm: Must be True to execute
    """
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to delete zone.",
        }

    client = DNSClient()
    try:
        await client.delete_zone(zone_id)
        return {
            "success": True,
            "message": f"Zone {zone_id} deleted successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


# =============================================================================
# DNS RECORD OPERATIONS
# =============================================================================


async def dns_record_list(
    zone_id: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """
    List DNS records in a zone.

    Args:
        zone_id: Zone ID
        domain: Domain name (alternative to zone_id)
    """
    client = DNSClient()
    try:
        if not zone_id and domain:
            zone = await client.get_zone_by_name(domain)
            if not zone:
                return {"success": False, "error": f"Zone not found: {domain}"}
            zone_id = zone.id
        elif not zone_id:
            return {"success": False, "error": "Either zone_id or domain required"}

        records = await client.list_records(zone_id)
        return {
            "success": True,
            "count": len(records),
            "records": [record.to_dict() for record in records],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_record_get(record_id: str) -> dict[str, Any]:
    """
    Get DNS record details.

    Args:
        record_id: Record ID
    """
    client = DNSClient()
    try:
        record = await client.get_record(record_id)
        return {
            "success": True,
            "record": record.to_dict(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_record_create(
    zone_id: str | None = None,
    domain: str | None = None,
    name: str = "@",
    type: str = "A",
    value: str = "",
    ttl: int = 3600,
) -> dict[str, Any]:
    """
    Create a new DNS record.

    Args:
        zone_id: Zone ID
        domain: Domain name (alternative to zone_id)
        name: Record name (@ for root, subdomain otherwise)
        type: Record type (A, AAAA, CNAME, MX, TXT, etc.)
        value: Record value
        ttl: TTL in seconds
    """
    if not value:
        return {"success": False, "error": "Value is required"}

    client = DNSClient()
    try:
        if not zone_id and domain:
            zone = await client.get_zone_by_name(domain)
            if not zone:
                return {"success": False, "error": f"Zone not found: {domain}"}
            zone_id = zone.id
        elif not zone_id:
            return {"success": False, "error": "Either zone_id or domain required"}

        record = await client.create_record(
            zone_id=zone_id,
            name=name,
            type=type,
            value=value,
            ttl=ttl,
        )

        return {
            "success": True,
            "record": record.to_dict(),
            "message": f"Record '{name}' ({type}) created successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_record_update(
    record_id: str,
    zone_id: str,
    name: str,
    type: str,
    value: str,
    ttl: int = 3600,
) -> dict[str, Any]:
    """
    Update a DNS record.

    Args:
        record_id: Record ID to update
        zone_id: Zone ID
        name: Record name
        type: Record type
        value: New record value
        ttl: TTL in seconds
    """
    client = DNSClient()
    try:
        record = await client.update_record(
            record_id=record_id,
            zone_id=zone_id,
            name=name,
            type=type,
            value=value,
            ttl=ttl,
        )

        return {
            "success": True,
            "record": record.to_dict(),
            "message": f"Record '{name}' updated successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_record_delete(
    record_id: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Delete a DNS record.

    Args:
        record_id: Record ID to delete
        confirm: Must be True to execute
    """
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to delete record.",
        }

    client = DNSClient()
    try:
        await client.delete_record(record_id)
        return {
            "success": True,
            "message": f"Record {record_id} deleted successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


# =============================================================================
# CONVENIENCE OPERATIONS
# =============================================================================


async def dns_set_a_record(
    domain: str,
    subdomain: str,
    ip: str,
    ttl: int = 3600,
) -> dict[str, Any]:
    """
    Set an A record (create or update).

    Args:
        domain: Domain name (zone)
        subdomain: Subdomain name (@ for root)
        ip: IP address
        ttl: TTL in seconds
    """
    client = DNSClient()
    try:
        record = await client.set_a_record(
            domain=domain,
            subdomain=subdomain,
            ip=ip,
            ttl=ttl,
        )

        return {
            "success": True,
            "record": record.to_dict(),
            "message": f"A record for {subdomain}.{domain} set to {ip}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_set_cname_record(
    domain: str,
    subdomain: str,
    target: str,
    ttl: int = 3600,
) -> dict[str, Any]:
    """
    Set a CNAME record (create or update).

    Args:
        domain: Domain name (zone)
        subdomain: Subdomain name
        target: Target hostname
        ttl: TTL in seconds
    """
    client = DNSClient()
    try:
        record = await client.set_cname_record(
            domain=domain,
            subdomain=subdomain,
            target=target,
            ttl=ttl,
        )

        return {
            "success": True,
            "record": record.to_dict(),
            "message": f"CNAME record for {subdomain}.{domain} set to {target}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def dns_find_records(
    domain: str,
    name: str | None = None,
    record_type: str | None = None,
) -> dict[str, Any]:
    """
    Find DNS records by name and/or type.

    Args:
        domain: Domain name (zone)
        name: Record name to filter by
        record_type: Record type to filter by (A, CNAME, etc.)
    """
    client = DNSClient()
    try:
        zone = await client.get_zone_by_name(domain)
        if not zone:
            return {"success": False, "error": f"Zone not found: {domain}"}

        records = await client.find_records(
            zone_id=zone.id,
            name=name,
            record_type=record_type,
        )

        return {
            "success": True,
            "count": len(records),
            "records": [record.to_dict() for record in records],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()
