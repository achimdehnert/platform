#!/usr/bin/env python3
"""
platform/scripts/dev-portal.py — Lokale Dev-Kachel-Landingpage

Startet HTTP-Server auf Port 9000, zeigt alle Repos als Kacheln.
Grün = Port aktiv, Grau = nicht gestartet. Auto-Refresh alle 5s.

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
REPOS_BASE   = PLATFORM_DIR.parent

ICONS = {
    "risk-hub":        "🛡️",
    "writing-hub":     "✍️",
    "weltenhub":       "🌍",
    "trading-hub":     "📈",
    "travel-beat":     "✈️",
    "coach-hub":       "🎯",
    "billing-hub":     "💳",
    "pptx-hub":        "📊",
    "cad-hub":         "🔧",
    "research-hub":    "🔬",
    "learn-hub":       "📚",
    "wedding-hub":     "💍",
    "bfagent":         "🤖",
    "dev-hub":         "⚙️",
    "137-hub":         "💫",
    "illustration-hub":"🎨",
    "ausschreibungs-hub": "📋",
    "recruiting-hub":  "👥",
    "tax-hub":         "🧾",
    "dms-hub":         "📂",
}

COLORS = [
    "#6366f1","#8b5cf6","#ec4899","#f59e0b","#10b981",
    "#3b82f6","#ef4444","#14b8a6","#f97316","#84cc16",
]


def load_services() -> list[dict]:
    data = yaml.safe_load(PORTS_YAML.read_text())
    result = []
    for i, (name, svc) in enumerate(data.get("services", {}).items()):
        port = svc.get("dev")
        has_manage = (REPOS_BASE / name / "manage.py").exists() or \
                     (REPOS_BASE / name / "src" / "manage.py").exists()
        result.append({
            "name":       name,
            "port":       port,
            "domain":     svc.get("domain_prod", ""),
            "icon":       ICONS.get(name, "📦"),
            "color":      COLORS[i % len(COLORS)],
            "has_manage": has_manage,
        })
    return sorted(result, key=lambda s: s["port"] or 9999)


def is_open(port: int | None) -> bool:
    if not port:
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def build_html(services: list[dict]) -> str:
    cards = ""
    for svc in services:
        active  = is_open(svc["port"])
        status  = "🟢 aktiv" if active else "⚪ gestoppt"
        opacity = "1" if active else "0.55"
        port    = svc["port"] or "—"
        url     = f"http://127.0.0.1:{port}" if active else "#"
        target  = '_blank' if active else ''
        cmd     = f"make dev  # in {svc['name']}/" if svc["has_manage"] else "—"

        cards += f"""
        <a href="{url}" {f'target="{target}"' if target else ''} class="card" style="opacity:{opacity};border-top:4px solid {svc['color']}">
          <div class="card-icon">{svc['icon']}</div>
          <div class="card-name">{svc['name']}</div>
          <div class="card-port">:{port}</div>
          <div class="card-status">{status}</div>
          <div class="card-cmd">{cmd}</div>
          <div class="card-domain">{svc['domain']}</div>
        </a>"""

    active_count = sum(1 for s in services if is_open(s["port"]))

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="5">
  <title>IIL Dev Portal</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0f0f13;
      color: #e2e8f0;
      min-height: 100vh;
      padding: 2rem;
    }}
    header {{
      text-align: center;
      margin-bottom: 2.5rem;
    }}
    header h1 {{
      font-size: 2rem;
      font-weight: 700;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    header p {{
      color: #94a3b8;
      margin-top: 0.5rem;
      font-size: 0.875rem;
    }}
    .stats {{
      display: flex;
      justify-content: center;
      gap: 2rem;
      margin-bottom: 2rem;
    }}
    .stat {{
      text-align: center;
    }}
    .stat-value {{
      font-size: 1.75rem;
      font-weight: 700;
      color: #6366f1;
    }}
    .stat-label {{
      font-size: 0.75rem;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 1rem;
      max-width: 1400px;
      margin: 0 auto;
    }}
    .card {{
      background: #1e1e2e;
      border-radius: 12px;
      padding: 1.25rem;
      text-decoration: none;
      color: inherit;
      transition: transform 0.15s, box-shadow 0.15s;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }}
    .card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }}
    .card-icon {{ font-size: 1.75rem; }}
    .card-name {{ font-size: 0.95rem; font-weight: 600; color: #e2e8f0; }}
    .card-port {{ font-size: 0.8rem; color: #94a3b8; font-family: monospace; }}
    .card-status {{ font-size: 0.75rem; margin-top: 0.25rem; }}
    .card-cmd {{
      font-size: 0.7rem;
      font-family: monospace;
      background: #12121c;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      color: #7dd3fc;
      margin-top: 0.5rem;
    }}
    .card-domain {{ font-size: 0.7rem; color: #475569; margin-top: auto; padding-top: 0.5rem; }}
    footer {{
      text-align: center;
      margin-top: 3rem;
      color: #334155;
      font-size: 0.75rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>🚀 IIL Dev Portal</h1>
    <p>Lokale Entwicklungsumgebung — Auto-Refresh alle 5s</p>
  </header>
  <div class="stats">
    <div class="stat">
      <div class="stat-value">{active_count}</div>
      <div class="stat-label">Aktiv</div>
    </div>
    <div class="stat">
      <div class="stat-value">{len(services)}</div>
      <div class="stat-label">Gesamt</div>
    </div>
  </div>
  <div class="grid">
    {cards}
  </div>
  <footer>platform/scripts/dev-portal.py &nbsp;·&nbsp; Quellcode: ~/github/platform/scripts/</footer>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    services: list[dict] = []

    def do_GET(self):
        if self.path == "/api/status":
            data = [{"name": s["name"], "port": s["port"], "active": is_open(s["port"])} for s in self.services]
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            html = build_html(self.services).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

    def log_message(self, fmt, *args):
        pass  # Stille Logs


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    services = load_services()
    Handler.services = services

    print(f"\n🚀 IIL Dev Portal läuft auf http://127.0.0.1:{port}")
    print(f"   {len(services)} Services geladen aus ports.yaml")
    print(f"   Ctrl+C zum Beenden\n")

    with http.server.HTTPServer(("127.0.0.1", port), Handler) as srv:
        srv.serve_forever()


if __name__ == "__main__":
    main()
