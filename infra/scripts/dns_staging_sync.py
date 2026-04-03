#!/usr/bin/env python3
"""DNS Staging Sync — Alle staging.* DNS-Records auf Dev Desktop zeigen lassen.

Liest ports.yaml und stellt sicher, dass alle staging-DNS-Records
auf den Staging-Server (Dev Desktop) zeigen. Nutzt die Cloudflare REST API
direkt (kein MCP-Dependency).

Nutzung:
    # Dry-Run (Standard): zeigt was geändert würde
    python infra/scripts/dns_staging_sync.py

    # Änderungen anwenden:
    python infra/scripts/dns_staging_sync.py --apply

    # Nur Leichen löschen:
    python infra/scripts/dns_staging_sync.py --apply --delete-only

    # Nur Updates (keine Löschungen):
    python infra/scripts/dns_staging_sync.py --apply --update-only

Voraussetzungen:
    export CLOUDFLARE_API_TOKEN="<your-token>"

Referenz: ADR-157 Phase 1

Exit-Codes:
    0 = alles OK / dry-run erfolgreich
    1 = Fehler bei API-Calls
    2 = CLOUDFLARE_API_TOKEN nicht gesetzt
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

import yaml

# --- Konstanten ---

PORTS_YAML = Path(__file__).resolve().parent.parent / "ports.yaml"
CF_API = "https://api.cloudflare.com/client/v4"
STAGING_IP = "88.99.38.75"
PROD_IP = "88.198.191.108"

# Bekannte alte/tote IPs die auf keinen aktiven Server zeigen
DEAD_IPS = frozenset({
    "46.225.113.1",    # alter dev-server (nicht mehr existent)
    "46.225.127.211",  # alter odoo-server
})

# DNS-Leichen: Records in falscher Zone oder veraltet (aus Audit 2026-04-02)
KNOWN_ORPHANS = [
    # (zone_domain, record_id, name, reason)
    (
        "iil.pet", "6d186ce5d8195093a58c990b8982f92c",
        "staging.ai-trades.de.iil.pet",
        "Falsche Zone",
    ),
    (
        "iil.pet", "67aa09ae437d9c6e62901267d833edea",
        "grafana-stagingv18-odoo.iil.pet",
        "Odoo Staging v18 veraltet",
    ),
    (
        "iil.pet", "a4fec1561fea4c009d06320e6918a0aa",
        "grafana-stagingv19-odoo.iil.pet",
        "Odoo Staging v19 veraltet",
    ),
    (
        "iil.pet", "fb7aafee2670efee0ecd8a6d4d72dd4e",
        "stagingv18-odoo.iil.pet",
        "Odoo Staging v18 veraltet",
    ),
    (
        "iil.pet", "09bc0bbd426c1c2aae9260bced98d122",
        "stagingv19-odoo.iil.pet",
        "Odoo Staging v19 veraltet",
    ),
]


def get_token() -> str:
    """Token via zentralen Secret-Resolver laden."""
    # infra/lib/secrets.py ist der Single Source of Truth
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent.parent),
    )
    try:
        from infra.lib.secrets import require_secret
        return require_secret("cloudflare")
    except (ImportError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)


def cf_request(
    method: str,
    path: str,
    token: str,
    data: dict | None = None,
) -> dict:
    """Cloudflare API Request mit urllib (keine requests-Dependency)."""
    url = f"{CF_API}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(
            f"  CF API Error {e.code}: {error_body}",
            file=sys.stderr,
        )
        return {
            "success": False,
            "errors": [{"message": error_body}],
        }


def get_zone_id(domain: str, token: str) -> str | None:
    """Zone-ID für eine Domain ermitteln."""
    resp = cf_request(
        "GET", f"/zones?name={domain}", token,
    )
    if resp.get("success") and resp.get("result"):
        return resp["result"][0]["id"]
    return None


def list_staging_records(zone_id: str, token: str) -> list[dict]:
    """Alle A-Records in einer Zone die 'staging' enthalten."""
    path = f"/zones/{zone_id}/dns_records?type=A&per_page=100"
    resp = cf_request("GET", path, token)
    if not resp.get("success"):
        return []
    return [
        r for r in resp.get("result", [])
        if "staging" in r["name"].lower()
    ]


def update_record(
    zone_id: str, record_id: str,
    name: str, ip: str, token: str,
) -> bool:
    """DNS-Record auf neue IP updaten."""
    path = f"/zones/{zone_id}/dns_records/{record_id}"
    resp = cf_request("PATCH", path, token, {
        "content": ip,
        "proxied": False,
        "ttl": 120,
        "comment": "ADR-157: Staging on Dev Desktop",
    },
    )
    return resp.get("success", False)


def delete_record(zone_id: str, record_id: str, token: str) -> bool:
    """DNS-Record löschen."""
    path = f"/zones/{zone_id}/dns_records/{record_id}"
    resp = cf_request("DELETE", path, token)
    return resp.get("success", False)


def load_staging_domains() -> list[str]:
    """Alle staging-Domains aus ports.yaml laden."""
    with open(PORTS_YAML) as f:
        data = yaml.safe_load(f)
    domains = []
    for _name, cfg in data.get("services", {}).items():
        if cfg and cfg.get("domain_staging"):
            domains.append(cfg["domain_staging"])
    return domains


def extract_zone_from_domain(domain: str) -> str:
    """Extract base zone from staging domain.

    coach-hub.iil.pet → iil.pet
    drifttales.com → drifttales.com
    """
    parts = domain.split(".")
    if len(parts) >= 3:
        return ".".join(parts[-2:])
    return domain


def run_audit(token: str) -> list[dict]:
    """Scanne alle Zonen, finde Records mit falscher IP."""
    staging_domains = load_staging_domains()
    zones_needed = {
        extract_zone_from_domain(d)
        for d in staging_domains
    }

    issues = []
    zone_cache: dict[str, str] = {}

    for zone_domain in sorted(zones_needed):
        zone_id = get_zone_id(
            zone_domain, token,
        )
        if not zone_id:
            print(
                f"  WARN: Zone {zone_domain}"
                " nicht gefunden",
            )
            continue
        zone_cache[zone_domain] = zone_id

        records = list_staging_records(zone_id, token)
        for rec in records:
            if rec["content"] != STAGING_IP:
                issues.append({
                    "zone": zone_domain,
                    "zone_id": zone_id,
                    "record_id": rec["id"],
                    "name": rec["name"],
                    "current_ip": rec["content"],
                    "target_ip": STAGING_IP,
                    "action": "UPDATE",
                })

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DNS Staging Sync (ADR-157)",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Änderungen wirklich anwenden",
    )
    parser.add_argument(
        "--delete-only", action="store_true",
        help="Nur Leichen löschen",
    )
    parser.add_argument(
        "--update-only", action="store_true",
        help="Nur Updates, keine Löschungen",
    )
    args = parser.parse_args()

    token = get_token()
    errors = 0

    print("=" * 60)
    print("DNS Staging Sync — ADR-157 Phase 1")
    print(f"Staging-Server: {STAGING_IP}")
    print(f"Modus: {'APPLY' if args.apply else 'DRY-RUN'}")
    print("=" * 60)

    # --- Teil 1: Staging-Records updaten ---
    if not args.delete_only:
        print("\n--- Staging DNS-Records prüfen ---\n")
        issues = run_audit(token)
        if not issues:
            print("  ✅ Alle staging-Records zeigen bereits auf", STAGING_IP)
        for issue in issues:
            print(f"  {'→' if args.apply else '⚠'} {issue['name']}")
            print(f"    {issue['current_ip']} → {issue['target_ip']}")
            if args.apply:
                ok = update_record(
                    issue["zone_id"],
                    issue["record_id"],
                    issue["name"],
                    issue["target_ip"],
                    token,
                )
                print(f"    {'✅ Updated' if ok else '❌ FAILED'}")
                if not ok:
                    errors += 1

    # --- Teil 2: DNS-Leichen löschen ---
    if not args.update_only:
        print("\n--- DNS-Leichen prüfen ---\n")
        zone_cache: dict[str, str] = {}
        for zone_domain, record_id, name, reason in KNOWN_ORPHANS:
            if zone_domain not in zone_cache:
                zid = get_zone_id(zone_domain, token)
                if zid:
                    zone_cache[zone_domain] = zid
            zone_id = zone_cache.get(zone_domain)
            if not zone_id:
                print(f"  WARN: Zone {zone_domain} nicht gefunden")
                continue

            print(f"  {'🗑' if args.apply else '⚠'} {name}")
            print(f"    Grund: {reason}")
            if args.apply:
                ok = delete_record(zone_id, record_id, token)
                msg = "✅ Deleted" if ok else "❌ FAILED"
                print(f"    {msg}")
                if not ok:
                    errors += 1

    # --- Zusammenfassung ---
    print("\n" + "=" * 60)
    if not args.apply:
        print("DRY-RUN abgeschlossen. Zum Anwenden: --apply")
    elif errors:
        print(f"⚠ Abgeschlossen mit {errors} Fehler(n)")
    else:
        print("✅ Alle Änderungen erfolgreich angewendet")
    print("=" * 60)

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
