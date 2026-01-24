"""Hetzner Server Tools for MCP."""

from typing import Any

from ..clients.hetzner_client import HetznerClient
from ..models import (
    PowerAction,
    ServerCreateRequest,
    FirewallCreateRequest,
    FirewallRule,
    FirewallDirection,
    FirewallProtocol,
    SSHKeyCreateRequest,
)
from ..settings import settings


# =============================================================================
# PHASE 1.1: BASIC SERVER TOOLS
# =============================================================================


async def server_list(label_selector: str | None = None) -> dict[str, Any]:
    """List all Hetzner servers."""
    client = HetznerClient()
    try:
        servers = await client.list_servers(label_selector)
        return {
            "success": True,
            "count": len(servers),
            "servers": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status.value,
                    "ip": s.public_net.ipv4,
                    "type": s.server_type,
                    "datacenter": s.datacenter,
                    "labels": s.labels,
                }
                for s in servers
            ],
        }
    finally:
        await client.close()


async def server_status(server_id: int | None = None, name: str | None = None) -> dict[str, Any]:
    """Get server status by ID or name."""
    client = HetznerClient()
    try:
        if server_id:
            server = await client.get_server(server_id)
        elif name:
            server = await client.get_server_by_name(name)
            if not server:
                return {"success": False, "error": f"Server '{name}' not found"}
        else:
            return {"success": False, "error": "Either server_id or name required"}

        return {
            "success": True,
            "server": {
                "id": server.id,
                "name": server.name,
                "status": server.status.value,
                "ipv4": server.public_net.ipv4,
                "ipv6": server.public_net.ipv6,
                "type": server.server_type,
                "datacenter": server.datacenter,
                "image": server.image,
                "labels": server.labels,
            },
        }
    finally:
        await client.close()


async def server_power(
    server_id: int,
    action: str,  # poweron, poweroff, reboot, reset, shutdown
) -> dict[str, Any]:
    """Execute power action on server."""
    try:
        power_action = PowerAction(action)
    except ValueError:
        return {"success": False, "error": f"Invalid action: {action}"}

    client = HetznerClient()
    try:
        result = await client.server_action(server_id, power_action)
        return {
            "success": True,
            "action": {
                "id": result.id,
                "command": result.command,
                "status": result.status,
                "progress": result.progress,
            },
        }
    finally:
        await client.close()


# =============================================================================
# PHASE 3.1: SERVER PROVISIONING TOOLS
# =============================================================================


async def server_create(
    name: str,
    server_type: str | None = None,
    image: str | None = None,
    location: str | None = None,
    ssh_keys: list[str] | None = None,
    labels: dict[str, str] | None = None,
    user_data: str | None = None,
    start_after_create: bool = True,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Create a new Hetzner server.

    Args:
        name: Server name
        server_type: Server type (cx22, cx32, cpx11, etc.)
        image: OS image (ubuntu-24.04, debian-12, etc.)
        location: Datacenter (fsn1, nbg1, hel1, ash, hil)
        ssh_keys: List of SSH key names or IDs
        labels: Labels for the server
        user_data: Cloud-init user data
        start_after_create: Start server after creation
        confirm: Must be True to execute (safety)
    """
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to create server.",
            "would_create": {
                "name": name,
                "type": server_type or settings.default_server_type,
                "image": image or settings.default_image,
                "location": location or settings.default_location,
            },
        }

    request = ServerCreateRequest(
        name=name,
        server_type=server_type or settings.default_server_type,
        image=image or settings.default_image,
        location=location or settings.default_location,
        ssh_keys=ssh_keys or [],
        labels=labels or {},
        user_data=user_data,
        start_after_create=start_after_create,
    )

    client = HetznerClient()
    try:
        result = await client.create_server(request)
        return {
            "success": True,
            "server": {
                "id": result.server.id,
                "name": result.server.name,
                "status": result.server.status.value,
                "ipv4": result.server.public_net.ipv4,
                "type": result.server.server_type,
                "datacenter": result.server.datacenter,
            },
            "root_password": result.root_password,
            "action_id": result.action_id,
            "message": f"Server '{name}' created successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def server_delete(
    server_id: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Delete a Hetzner server.

    Args:
        server_id: Server ID to delete
        confirm: Must be True to execute (safety)
    """
    client = HetznerClient()
    try:
        # Get server info first
        server = await client.get_server(server_id)

        if settings.require_confirmation and not confirm:
            return {
                "success": False,
                "error": "Confirmation required. Set confirm=True to delete server.",
                "would_delete": {
                    "id": server.id,
                    "name": server.name,
                    "ip": server.public_net.ipv4,
                },
            }

        result = await client.delete_server(server_id)
        return {
            "success": True,
            "action": {
                "id": result.id,
                "command": result.command,
                "status": result.status,
            },
            "message": f"Server '{server.name}' (ID: {server_id}) deletion initiated",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def server_rebuild(
    server_id: int,
    image: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Rebuild server with new image (destroys all data).

    Args:
        server_id: Server ID to rebuild
        image: New OS image
        confirm: Must be True to execute (safety)
    """
    client = HetznerClient()
    try:
        server = await client.get_server(server_id)

        if settings.require_confirmation and not confirm:
            return {
                "success": False,
                "error": "Confirmation required. Set confirm=True to rebuild. WARNING: All data will be lost!",
                "would_rebuild": {
                    "id": server.id,
                    "name": server.name,
                    "current_image": server.image,
                    "new_image": image,
                },
            }

        result = await client.rebuild_server(server_id, image)
        return {
            "success": True,
            "action": {
                "id": result.id,
                "command": result.command,
                "status": result.status,
            },
            "message": f"Server '{server.name}' rebuild initiated with image '{image}'",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def server_types_list() -> dict[str, Any]:
    """List available server types."""
    client = HetznerClient()
    try:
        types = await client.list_server_types()
        return {
            "success": True,
            "count": len(types),
            "server_types": [
                {
                    "name": t.name,
                    "description": t.description,
                    "cores": t.cores,
                    "memory_gb": t.memory,
                    "disk_gb": t.disk,
                }
                for t in types
            ],
        }
    finally:
        await client.close()


async def images_list(type_filter: str | None = None) -> dict[str, Any]:
    """List available images."""
    client = HetznerClient()
    try:
        images = await client.list_images(type_filter)
        return {
            "success": True,
            "count": len(images),
            "images": [
                {
                    "id": i.id,
                    "name": i.name,
                    "description": i.description,
                    "type": i.type,
                    "os_flavor": i.os_flavor,
                    "os_version": i.os_version,
                }
                for i in images
            ],
        }
    finally:
        await client.close()


async def locations_list() -> dict[str, Any]:
    """List available datacenter locations."""
    client = HetznerClient()
    try:
        locations = await client.list_locations()
        return {
            "success": True,
            "count": len(locations),
            "locations": [
                {
                    "name": loc.name,
                    "description": loc.description,
                    "country": loc.country,
                    "city": loc.city,
                    "network_zone": loc.network_zone,
                }
                for loc in locations
            ],
        }
    finally:
        await client.close()


# =============================================================================
# PHASE 3.1: FIREWALL TOOLS
# =============================================================================


async def firewall_list(label_selector: str | None = None) -> dict[str, Any]:
    """List all firewalls."""
    client = HetznerClient()
    try:
        firewalls = await client.list_firewalls(label_selector)
        return {
            "success": True,
            "count": len(firewalls),
            "firewalls": [
                {
                    "id": fw.id,
                    "name": fw.name,
                    "rules_count": len(fw.rules),
                    "applied_to_count": len(fw.applied_to),
                    "labels": fw.labels,
                }
                for fw in firewalls
            ],
        }
    finally:
        await client.close()


async def firewall_get(firewall_id: int) -> dict[str, Any]:
    """Get firewall details."""
    client = HetznerClient()
    try:
        fw = await client.get_firewall(firewall_id)
        return {
            "success": True,
            "firewall": {
                "id": fw.id,
                "name": fw.name,
                "rules": [
                    {
                        "direction": r.direction.value,
                        "protocol": r.protocol.value,
                        "port": r.port,
                        "source_ips": r.source_ips,
                        "destination_ips": r.destination_ips,
                        "description": r.description,
                    }
                    for r in fw.rules
                ],
                "applied_to": fw.applied_to,
                "labels": fw.labels,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def firewall_create(
    name: str,
    rules: list[dict[str, Any]] | None = None,
    labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create a new firewall.

    Args:
        name: Firewall name
        rules: List of rule dicts with direction, protocol, port, source_ips
        labels: Labels for the firewall

    Example rule:
        {"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["0.0.0.0/0"]}
    """
    parsed_rules = []
    for rule in rules or []:
        try:
            parsed_rules.append(
                FirewallRule(
                    direction=FirewallDirection(rule.get("direction", "in")),
                    protocol=FirewallProtocol(rule.get("protocol", "tcp")),
                    port=rule.get("port"),
                    source_ips=rule.get("source_ips", []),
                    destination_ips=rule.get("destination_ips", []),
                    description=rule.get("description"),
                )
            )
        except Exception as e:
            return {"success": False, "error": f"Invalid rule: {e}"}

    request = FirewallCreateRequest(
        name=name,
        rules=parsed_rules,
        labels=labels or {},
    )

    client = HetznerClient()
    try:
        fw = await client.create_firewall(request)
        return {
            "success": True,
            "firewall": {
                "id": fw.id,
                "name": fw.name,
                "rules_count": len(fw.rules),
            },
            "message": f"Firewall '{name}' created successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def firewall_delete(
    firewall_id: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete a firewall."""
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to delete firewall.",
        }

    client = HetznerClient()
    try:
        await client.delete_firewall(firewall_id)
        return {
            "success": True,
            "message": f"Firewall {firewall_id} deleted successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def firewall_set_rules(
    firewall_id: int,
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """Set firewall rules (replaces all existing rules)."""
    parsed_rules = []
    for rule in rules:
        try:
            parsed_rules.append(
                FirewallRule(
                    direction=FirewallDirection(rule.get("direction", "in")),
                    protocol=FirewallProtocol(rule.get("protocol", "tcp")),
                    port=rule.get("port"),
                    source_ips=rule.get("source_ips", []),
                    destination_ips=rule.get("destination_ips", []),
                    description=rule.get("description"),
                )
            )
        except Exception as e:
            return {"success": False, "error": f"Invalid rule: {e}"}

    client = HetznerClient()
    try:
        actions = await client.set_firewall_rules(firewall_id, parsed_rules)
        return {
            "success": True,
            "actions_count": len(actions),
            "message": f"Set {len(parsed_rules)} rules on firewall {firewall_id}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def firewall_apply(
    firewall_id: int,
    server_ids: list[int],
) -> dict[str, Any]:
    """Apply firewall to servers."""
    client = HetznerClient()
    try:
        actions = await client.apply_firewall_to_servers(firewall_id, server_ids)
        return {
            "success": True,
            "actions_count": len(actions),
            "message": f"Firewall {firewall_id} applied to {len(server_ids)} server(s)",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def firewall_remove(
    firewall_id: int,
    server_ids: list[int],
) -> dict[str, Any]:
    """Remove firewall from servers."""
    client = HetznerClient()
    try:
        actions = await client.remove_firewall_from_servers(firewall_id, server_ids)
        return {
            "success": True,
            "actions_count": len(actions),
            "message": f"Firewall {firewall_id} removed from {len(server_ids)} server(s)",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


# =============================================================================
# PHASE 3.1: SSH KEY TOOLS
# =============================================================================


async def ssh_key_list(label_selector: str | None = None) -> dict[str, Any]:
    """List all SSH keys."""
    client = HetznerClient()
    try:
        keys = await client.list_ssh_keys(label_selector)
        return {
            "success": True,
            "count": len(keys),
            "ssh_keys": [
                {
                    "id": k.id,
                    "name": k.name,
                    "fingerprint": k.fingerprint,
                    "labels": k.labels,
                }
                for k in keys
            ],
        }
    finally:
        await client.close()


async def ssh_key_create(
    name: str,
    public_key: str,
    labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a new SSH key."""
    request = SSHKeyCreateRequest(
        name=name,
        public_key=public_key,
        labels=labels or {},
    )

    client = HetznerClient()
    try:
        key = await client.create_ssh_key(request)
        return {
            "success": True,
            "ssh_key": {
                "id": key.id,
                "name": key.name,
                "fingerprint": key.fingerprint,
            },
            "message": f"SSH key '{name}' created successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def ssh_key_delete(
    key_id: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete an SSH key."""
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to delete SSH key.",
        }

    client = HetznerClient()
    try:
        await client.delete_ssh_key(key_id)
        return {
            "success": True,
            "message": f"SSH key {key_id} deleted successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await client.close()
