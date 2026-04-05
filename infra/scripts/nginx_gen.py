#!/usr/bin/env python3
"""Nginx Config Generator — erzeugt Configs aus ports.yaml.

Generiert konsistente Nginx-Server-Blocks für Prod und Staging
basierend auf ports.yaml (ADR-157 Phase 3).

Nutzung:
    # Alle Services (Dry-Run, stdout):
    python infra/scripts/nginx_gen.py

    # Einzelnen Service generieren:
    python infra/scripts/nginx_gen.py --service risk-hub

    # In Dateien schreiben:
    python infra/scripts/nginx_gen.py --output-dir /tmp/nginx

    # Nur Staging:
    python infra/scripts/nginx_gen.py --staging-only

    # Nur Prod:
    python infra/scripts/nginx_gen.py --prod-only

Referenz: ADR-157
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent

import yaml

PORTS_YAML = (
    Path(__file__).resolve().parent.parent / "ports.yaml"
)

# SSL-Zertifikat-Patterns nach Domain-Typ
SSL_PATTERNS = {
    "iil.pet": {
        "cert": (
            "/etc/nginx/ssl/cf-origin/iil-pet.crt"
        ),
        "key": (
            "/etc/nginx/ssl/cf-origin/iil-pet.key"
        ),
    },
    "letsencrypt": {
        "cert": (
            "/etc/letsencrypt/live/{domain}"
            "/fullchain.pem"
        ),
        "key": (
            "/etc/letsencrypt/live/{domain}"
            "/privkey.pem"
        ),
    },
}


def load_ports_yaml() -> tuple[dict, dict]:
    """Load services and servers from ports.yaml."""
    with open(PORTS_YAML) as f:
        data = yaml.safe_load(f)
    return (
        data.get("services", {}),
        data.get("servers", {}),
    )


def get_ssl_paths(domain: str) -> tuple[str, str]:
    """Determine SSL cert/key paths for a domain."""
    if domain.endswith(".iil.pet"):
        p = SSL_PATTERNS["iil.pet"]
        return p["cert"], p["key"]
    tpl = SSL_PATTERNS["letsencrypt"]
    return (
        tpl["cert"].format(domain=domain),
        tpl["key"].format(domain=domain),
    )


def validate_domain_depth(domain: str) -> None:
    """Reject two-level subdomains under iil.pet (CF Universal SSL limit).

    CF Universal SSL covers *.iil.pet but NOT *.*.iil.pet.
    Staging domains must use staging-{name}.iil.pet, not staging.{name}.iil.pet.
    """
    if not domain.endswith(".iil.pet"):
        return
    prefix = domain.removesuffix(".iil.pet")
    if "." in prefix:
        raise ValueError(
            f"BLOCKED: '{domain}' is a two-level subdomain under iil.pet. "
            f"CF Universal SSL only covers *.iil.pet, not *.*.iil.pet. "
            f"Use '{prefix.replace('.', '-')}.iil.pet' instead."
        )


def generate_prod_config(
    name: str,
    cfg: dict,
) -> str:
    """Generate production Nginx config."""
    domain = cfg.get("domain_prod")
    port = cfg.get("prod")
    aliases = cfg.get("domain_aliases", []) or []

    if not domain or not port:
        return ""

    validate_domain_depth(domain)
    cert, key = get_ssl_paths(domain)

    # All server_names for the main block
    all_names = [domain]
    # www redirect for custom domains
    has_www = not domain.endswith(".iil.pet")

    # HTTP → HTTPS redirect
    http_names = " ".join(all_names)
    if has_www:
        http_names += f" www.{domain}"

    lines = []
    lines.append(
        f"# Auto-generated from ports.yaml"
        f" — {name} (prod)"
    )
    lines.append(
        f"# Domain: {domain}, Port: {port}"
    )
    lines.append("")

    # HTTP redirect block
    lines.append("server {")
    lines.append("    listen 80;")
    lines.append("    listen [::]:80;")
    lines.append(f"    server_name {http_names};")
    lines.append(
        f"    return 301 https://{domain}"
        "$request_uri;"
    )
    lines.append("}")
    lines.append("")

    # www redirect (custom domains only)
    if has_www:
        lines.append("server {")
        lines.append("    listen 443 ssl http2;")
        lines.append("    listen [::]:443 ssl http2;")
        lines.append(
            f"    server_name www.{domain};"
        )
        lines.append(f"    ssl_certificate {cert};")
        lines.append(
            f"    ssl_certificate_key {key};"
        )
        lines.append(
            f"    return 301 https://{domain}"
            "$request_uri;"
        )
        lines.append("}")
        lines.append("")

    # Main HTTPS block
    main_names = " ".join(all_names)
    lines.append("server {")
    lines.append("    listen 443 ssl http2;")
    lines.append("    listen [::]:443 ssl http2;")
    lines.append(f"    server_name {main_names};")
    lines.append("")
    lines.append(f"    ssl_certificate {cert};")
    lines.append(f"    ssl_certificate_key {key};")
    lines.append(
        "    ssl_protocols TLSv1.2 TLSv1.3;"
    )
    lines.append("    ssl_ciphers HIGH:!aNULL:!MD5;")
    lines.append("")
    lines.append("    client_max_body_size 100M;")
    lines.append("")
    lines.append(_proxy_location(port))
    lines.append("}")

    # Alias domain redirect configs
    for alias in aliases:
        lines.append("")
        lines.append(
            _alias_redirect(alias, domain)
        )

    return "\n".join(lines)


def generate_staging_config(
    name: str,
    cfg: dict,
) -> str:
    """Generate staging Nginx config."""
    domain = cfg.get("domain_staging")
    port = cfg.get("staging")

    if not domain or not port:
        return ""

    validate_domain_depth(domain)
    cert, key = get_ssl_paths(domain)

    lines = []
    lines.append(
        f"# Auto-generated from ports.yaml"
        f" — {name} (staging)"
    )
    lines.append(
        f"# Domain: {domain}, Port: {port}"
    )
    lines.append("")

    # HTTP redirect
    lines.append("server {")
    lines.append("    listen 80;")
    lines.append("    listen [::]:80;")
    lines.append(f"    server_name {domain};")
    lines.append(
        "    return 301 https://$host$request_uri;"
    )
    lines.append("}")
    lines.append("")

    # HTTPS
    lines.append("server {")
    lines.append("    listen 443 ssl http2;")
    lines.append("    listen [::]:443 ssl http2;")
    lines.append(f"    server_name {domain};")
    lines.append("")
    lines.append(f"    ssl_certificate {cert};")
    lines.append(f"    ssl_certificate_key {key};")
    lines.append(
        "    ssl_protocols TLSv1.2 TLSv1.3;"
    )
    lines.append("    ssl_ciphers HIGH:!aNULL:!MD5;")
    lines.append("")
    lines.append("    client_max_body_size 100M;")
    lines.append("")
    lines.append(_proxy_location(port))
    lines.append("}")

    return "\n".join(lines)


def _proxy_location(port: int) -> str:
    """Generate standard proxy_pass location block."""
    return dedent(f"""\
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
    }}""")  # noqa: E501


def _alias_redirect(
    alias: str, target: str,
) -> str:
    """Generate alias domain redirect config."""
    cert, key = get_ssl_paths(alias)
    return dedent(f"""\
    # Alias redirect: {alias} → {target}
    server {{
        listen 80;
        listen [::]:80;
        server_name {alias} www.{alias};
        return 301 https://{target}$request_uri;
    }}

    server {{
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        server_name {alias} www.{alias};

        ssl_certificate {cert};
        ssl_certificate_key {key};

        return 301 https://{target}$request_uri;
    }}""")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Nginx Config Generator (ADR-157)"
        ),
    )
    parser.add_argument(
        "--service",
        help="Nur einen Service generieren",
    )
    parser.add_argument(
        "--output-dir",
        help="Configs in Verzeichnis schreiben",
    )
    parser.add_argument(
        "--prod-only", action="store_true",
        help="Nur Prod-Configs",
    )
    parser.add_argument(
        "--staging-only", action="store_true",
        help="Nur Staging-Configs",
    )
    args = parser.parse_args()

    services, _ = load_ports_yaml()

    if args.service:
        if args.service not in services:
            print(
                f"ERROR: '{args.service}'"
                " nicht in ports.yaml",
                file=sys.stderr,
            )
            sys.exit(1)
        targets = {
            args.service: services[args.service],
        }
    else:
        targets = {
            k: v for k, v in services.items()
            if v and v.get("domain_prod")
        }

    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for name, cfg in sorted(targets.items()):
        if cfg is None:
            continue

        configs: list[tuple[str, str]] = []

        if not args.staging_only:
            prod = generate_prod_config(name, cfg)
            if prod:
                domain = cfg.get("domain_prod", name)
                fname = f"{domain}.conf"
                configs.append((fname, prod))

        if not args.prod_only:
            stg = generate_staging_config(name, cfg)
            if stg:
                domain = cfg.get(
                    "domain_staging", name,
                )
                fname = f"{domain}.conf"
                configs.append((fname, stg))

        for fname, content in configs:
            if output_dir:
                path = output_dir / fname
                path.write_text(content + "\n")
                print(f"  Geschrieben: {path}")
            else:
                print(f"--- {fname} ---")
                print(content)
                print()
            generated += 1

    print(f"\n{generated} Configs generiert.")


if __name__ == "__main__":
    main()
