#!/usr/bin/env python3
"""Generate staging-klickdummy.iil.pet Landing-Page (ADR-216).

Usage:
    python3 generate_landing.py <target-dir> <repos.yaml> > index.html

Discovers <target-dir>/<owner>/<repo>/<klickdummy>/<shell.html|chat-simulator.html>
and produces an authenticated landing page (SSO-User-Name aus
X-authentik-username Header wird per JS gerendert, falls vorhanden).
"""
from __future__ import annotations

import argparse
import html
import pathlib
import sys

try:
    import yaml
except ImportError:
    print("✗ pyyaml fehlt — apt install python3-yaml", file=sys.stderr)
    sys.exit(2)


def discover(target_dir: pathlib.Path) -> list[dict]:
    """Findet Klickdummies unter <target_dir>/<owner>/<repo>/<kd>/."""
    found = []
    for owner_dir in sorted(target_dir.iterdir()):
        if not owner_dir.is_dir() or owner_dir.name.startswith("."):
            continue
        for repo_dir in sorted(owner_dir.iterdir()):
            if not repo_dir.is_dir():
                continue
            for kd_dir in sorted(repo_dir.iterdir()):
                if not kd_dir.is_dir():
                    continue
                # Suche shell.html oder chat-simulator.html
                for entry in ("shell.html", "chat-simulator.html"):
                    if (kd_dir / entry).exists():
                        found.append({
                            "owner": owner_dir.name,
                            "repo": repo_dir.name,
                            "klickdummy": kd_dir.name,
                            "entry": entry,
                            "url": f"/{owner_dir.name}/{repo_dir.name}/{kd_dir.name}/{entry}",
                        })
                        break
    return found


def render(found: list[dict], repos_meta: dict) -> str:
    """HTML-Landing-Seite."""
    # Repo-Metadaten als Dict für schnellen Lookup
    meta_by_repo = {
        f"{r['owner']}/{r['name']}": r for r in repos_meta.get("repos", [])
    }

    rows = []
    by_owner: dict[str, list[dict]] = {}
    for f in found:
        by_owner.setdefault(f["owner"], []).append(f)

    for owner in sorted(by_owner):
        rows.append(f"<h2>{html.escape(owner)}</h2><ul>")
        for f in by_owner[owner]:
            repo_key = f"{f['owner']}/{f['repo']}"
            meta = meta_by_repo.get(repo_key, {})
            desc = html.escape(meta.get("description", ""))
            adr = html.escape(meta.get("adr", ""))
            rows.append(
                f"<li><a href='{html.escape(f['url'])}'>"
                f"<strong>{html.escape(f['repo'])}</strong> / "
                f"<code>{html.escape(f['klickdummy'])}</code></a>"
                f"<div class='meta'>{desc}{' · ADR: <code>' + adr + '</code>' if adr else ''}</div></li>"
            )
        rows.append("</ul>")

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>staging-klickdummy.iil.pet — Stakeholder-Demo</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a2230; }}
  h1 {{ color: #1a3a6c; }}
  h2 {{ color: #ec0016; margin-top: 30px; font-size: 18px; border-bottom: 1px solid #e5e9ef; padding-bottom: 6px; }}
  .user {{ float: right; background: #f0f3f7; padding: 4px 10px; border-radius: 12px; font-size: 12px; color: #475569; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ background: #fff; border: 1px solid #d8e0e8; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; }}
  li a {{ color: #1a3a6c; text-decoration: none; }}
  li a:hover {{ text-decoration: underline; }}
  .meta {{ color: #6a7888; font-size: 12px; margin-top: 4px; }}
  code {{ background: #f0f3f7; padding: 1px 5px; border-radius: 3px; font-size: 11px; }}
  .footer {{ color: #8a96a3; font-size: 11px; margin-top: 40px; border-top: 1px solid #e5e9ef; padding-top: 12px; line-height: 1.6; }}
</style>
</head>
<body>
<div class="user" id="user-chip">SSO · <span id="user-name">–</span></div>
<h1>🛠 staging-klickdummy.iil.pet</h1>
<p>Pre-Pilot-Klickdummy-Demos · alle <code>class: mock</code> · synthetische Daten · SSO via Authentik (ADR-142)</p>
{"".join(rows)}
<div class="footer">
  Konform zu <a href="https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-211-klickdummy-benutzeranforderungen-entwicklungsprozess.md"><code>platform:ADR-211</code></a> ·
  Hosting <a href="https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-216-klickdummy-hosting-iil-pet.md"><code>platform:ADR-216</code></a> ·
  Discovery <a href="https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-215-klickdummy-pgvector-discovery.md"><code>platform:ADR-215</code></a><br>
  DSFA 2026-05-21: nicht kritisch (synthetische Daten + Funktionsrollen-Labels)
</div>
<script>
  // Authentik liefert den User-Namen via Header zurück an Browser nicht direkt,
  // aber das Outpost setzt einen Cookie + JS kann via /outpost.goauthentik.io/api/v3/core/users/me/
  // abfragen, falls gewünscht. Hier vorerst Placeholder.
  fetch('/outpost.goauthentik.io/api/v3/core/users/me/', {{ credentials: 'include' }})
    .then(r => r.ok ? r.json() : null)
    .then(d => {{ if(d && d.user && d.user.username) document.getElementById('user-name').textContent = d.user.username; }})
    .catch(() => {{ document.getElementById('user-chip').style.display = 'none'; }});
</script>
</body>
</html>
"""


def render_json(found: list[dict], repos_meta: dict) -> str:
    """Discovery-API-Endpoint /api/list — same-origin-Konsumenten (Picker)."""
    import datetime
    import json as _json

    meta_by_repo = {
        f"{r['owner']}/{r['name']}": r for r in repos_meta.get("repos", [])
    }
    entries = []
    for f in found:
        repo_key = f"{f['owner']}/{f['repo']}"
        meta = meta_by_repo.get(repo_key, {})
        entries.append({
            "key": f"{f['owner']}/{f['klickdummy']}",
            "org": f["owner"],
            "repo": f["repo"],
            "name": f["klickdummy"],
            "url": f["url"],
            "entry_file": f["entry"],
            "description": meta.get("description"),
            "adr": meta.get("adr"),
            "source": "staging-klickdummy.iil.pet",
        })
    payload = {
        "entries": entries,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": "filesystem-scan",
        "adr": "platform:ADR-216",
    }
    return _json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("target_dir", help="z.B. /srv/klickdummy")
    ap.add_argument("repos_yaml", help="z.B. /opt/klickdummy/repos.yaml")
    ap.add_argument("--emit-json", help="Pfad für _index.json (Discovery-API)")
    ap.add_argument("--emit-html", help="Pfad für index.html (Landing)")
    args = ap.parse_args(argv)

    target = pathlib.Path(args.target_dir)
    repos_meta = yaml.safe_load(pathlib.Path(args.repos_yaml).read_text(encoding="utf-8"))

    found = discover(target)

    if args.emit_json:
        pathlib.Path(args.emit_json).write_text(
            render_json(found, repos_meta) + "\n", encoding="utf-8"
        )
    if args.emit_html:
        pathlib.Path(args.emit_html).write_text(
            render(found, repos_meta), encoding="utf-8"
        )
    if not args.emit_json and not args.emit_html:
        # Backward-compat: stdout
        print(render(found, repos_meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
