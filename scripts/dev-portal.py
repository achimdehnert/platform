#!/usr/bin/env python3
"""
platform/scripts/dev-portal.py — Lokale Dev-Kachel-Landingpage

Serviert dieselbe index.html wie iil.pet, aber mit lokalen URLs.
Generiert apps.json dynamisch aus ports.yaml + registry/repos.yaml.
Grüner "Live"-Badge wenn Port aktiv, grauer "gestoppt" wenn nicht.

Usage:
    python3 dev-portal.py          # Port 9000
    python3 dev-portal.py 9001     # Alternativer Port

Voraussetzung: pyyaml (pip3 install pyyaml)
"""

from __future__ import annotations

import http.server
import json
import pathlib
import socket
import sys

try:
    import yaml
except ImportError:
    sys.exit("Fehler: pyyaml fehlt — pip3 install pyyaml")

PLATFORM_DIR = pathlib.Path(__file__).parent.parent
PORTS_YAML   = PLATFORM_DIR / "infra" / "ports.yaml"
REPOS_YAML   = PLATFORM_DIR / "registry" / "repos.yaml"
INDEX_HTML   = PLATFORM_DIR / "static-sites" / "iil.pet" / "index.html"

# Icon + Color Mapping (erweiterbar)
META = {
    "risk-hub":        {"icon": "⚠️",  "color": "red"},
    "writing-hub":     {"icon": "✍️",  "color": "purple"},
    "weltenhub":       {"icon": "🌍",  "color": "pink"},
    "trading-hub":     {"icon": "📈",  "color": "green"},
    "travel-beat":     {"icon": "✈️",  "color": "cyan"},
    "coach-hub":       {"icon": "🎯",  "color": "orange"},
    "billing-hub":     {"icon": "💳",  "color": "amber"},
    "pptx-hub":        {"icon": "📊",  "color": "amber"},
    "cad-hub":         {"icon": "🔧",  "color": "accent"},
    "research-hub":    {"icon": "🔬",  "color": "cyan"},
    "learn-hub":       {"icon": "📚",  "color": "accent"},
    "wedding-hub":     {"icon": "💍",  "color": "pink"},
    "bfagent":         {"icon": "🤖",  "color": "purple"},
    "dev-hub":         {"icon": "⚙️",  "color": "muted"},
    "137-hub":         {"icon": "💫",  "color": "purple"},
    "illustration-hub":{"icon": "🎨",  "color": "pink"},
    "ausschreibungs-hub":{"icon": "📋","color": "accent"},
    "recruiting-hub":  {"icon": "👥",  "color": "green"},
    "tax-hub":         {"icon": "🧾",  "color": "muted"},
    "dms-hub":         {"icon": "📂",  "color": "amber"},
    "odoo":            {"icon": "🏢",  "color": "muted"},
}


def load_descriptions() -> dict[str, str]:
    """Beschreibungen aus registry/repos.yaml laden."""
    if not REPOS_YAML.exists():
        return {}
    data = yaml.safe_load(REPOS_YAML.read_text())
    result = {}
    for domain in data.get("domains", []):
        for sys_ in domain.get("systems", []):
            name = sys_.get("repo") or sys_.get("name", "")
            result[name] = sys_.get("description", "")
    return result


def is_open(port: int | None) -> bool:
    if not port:
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def build_apps_json() -> list[dict]:
    ports_data  = yaml.safe_load(PORTS_YAML.read_text())
    descriptions = load_descriptions()
    apps = []

    for name, svc in ports_data.get("services", {}).items():
        port = svc.get("dev")
        if not port:
            continue

        active  = is_open(port)
        meta    = META.get(name, {"icon": "📦", "color": "accent"})
        local_url = f"http://127.0.0.1:{port}"
        desc = descriptions.get(name) or svc.get("domain_prod", name)

        apps.append({
            "name":        name,
            "url":         local_url if active else "#",
            "admin_url":   f"{local_url}/admin/" if active else "",
            "description": desc,
            "icon":        meta["icon"],
            "color":       meta["color"],
            "tags":        [f":{port}"],
            "status":      "live" if active else "gestoppt",
        })

    return sorted(apps, key=lambda a: int(a["tags"][0][1:]) if a["tags"] else 9999)


def build_index_html() -> str:
    """Bestehende index.html lesen und Titel anpassen."""
    html = INDEX_HTML.read_text()
    html = html.replace("<title>IIL Platform</title>",
                        "<title>IIL Dev Portal — Lokal</title>")
    html = html.replace("<h1>IIL Platform</h1>",
                        "<h1>IIL Dev Portal</h1>")
    html = html.replace("Integrated Intelligence Layer &mdash; App Ecosystem",
                        "Lokale Entwicklungsumgebung &mdash; Auto-Refresh alle 10s")
    # Auto-Refresh hinzufügen
    html = html.replace(
        '<meta name="viewport"',
        '<meta http-equiv="refresh" content="10">\n    <meta name="viewport"'
    )
    # apps.json relativ laden (bleibt gleich, kein Änderungsbedarf)
    return html


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/apps.json"):
            body = json.dumps(build_apps_json(), ensure_ascii=False).encode()
            self._respond(200, "application/json", body)
        elif self.path in ("/", "/index.html"):
            body = build_index_html().encode()
            self._respond(200, "text/html; charset=utf-8", body)
        else:
            self._respond(404, "text/plain", b"Not found")

    def _respond(self, code: int, ctype: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # Stille Logs


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    print(f"\n🚀 IIL Dev Portal — http://127.0.0.1:{port}")
    print(f"   apps.json dynamisch aus ports.yaml ({len(yaml.safe_load(PORTS_YAML.read_text()).get('services', {}))} Services)")
    print(f"   Auto-Refresh alle 10s  |  Ctrl+C zum Beenden\n")
    with http.server.HTTPServer(("127.0.0.1", port), Handler) as srv:
        srv.serve_forever()


if __name__ == "__main__":
    main()
