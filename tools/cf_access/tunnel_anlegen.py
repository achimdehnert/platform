#!/usr/bin/env python3
"""Eigenen cloudflared-Tunnel anlegen, Ingress-Config schreiben, DNS setzen.

Bewusst ein EIGENER Tunnel je Dienst statt eines Eintrags im Prod-Tunnel: dort
hängen rund 40 Hostnamen an einer root-Config, ein Fehler nimmt alles mit.

Umgebung:
  HOST         Pflicht, z.B. mail.iil.pet
  PORT         Pflicht, der Loopback-Port des Dienstes
  TUNNEL_NAME  Default: erster Namensteil von HOST
  ORIGIN       Optional, Ursprung hinter dem Tunnel. Default `127.0.0.1:PORT`.
               Fuer einen Dienst auf einer ANDEREN Maschine, die nur ueber ein
               privates Netz erreichbar ist (z.B. `10.99.0.2:11434` ueber wg0):
               der Tunnel laeuft dann auf dem Gateway, nicht beim Dienst.

Ohne `cert.pem`: Tunnel und Zugangsdatei entstehen über die API, `cloudflared`
braucht danach nur noch die Datei. Das Tunnel-Geheimnis wird geschrieben, nie
ausgegeben — und ist nach dem Anlegen nicht wiederherstellbar.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cf import api, umgebung, zone_und_konto  # noqa: E402

CF_DIR = Path.home() / ".cloudflared"


def main() -> None:
    host, port = umgebung("HOST", "PORT")
    name = os.environ.get("TUNNEL_NAME") or host.split(".")[0]
    origin = os.environ.get("ORIGIN", "").strip() or f"127.0.0.1:{port}"
    zone, konto = zone_und_konto(host)
    CF_DIR.mkdir(mode=stat.S_IRWXU, exist_ok=True)
    kdatei = CF_DIR / f"{name}.json"

    tunnel = [
        t
        for t in api(
            "GET", f"/accounts/{konto}/cfd_tunnel?is_deleted=false&per_page=100"
        )["result"]
        or []
        if t["name"] == name
    ]
    if tunnel:
        tid = tunnel[0]["id"]
        print(f"Tunnel '{name}' existiert bereits: {tid}")
        if not kdatei.exists():
            sys.exit(
                f"FEHLER: Tunnel existiert, aber {kdatei} fehlt — das Geheimnis ist "
                "nicht wiederherstellbar. Tunnel in Cloudflare löschen und neu anlegen."
            )
    else:
        geheimnis = base64.b64encode(secrets.token_bytes(32)).decode()
        tid = api(
            "POST",
            f"/accounts/{konto}/cfd_tunnel",
            {"name": name, "tunnel_secret": geheimnis, "config_src": "local"},
        )["result"]["id"]
        kdatei.write_text(
            json.dumps(
                {"AccountTag": konto, "TunnelID": tid, "TunnelSecret": geheimnis}
            )
        )
        kdatei.chmod(stat.S_IRUSR | stat.S_IWUSR)
        print(f"Tunnel '{name}' angelegt: {tid} (Zugangsdatei {kdatei}, Modus 0600)")

    cfg = CF_DIR / f"{name}.yml"
    cfg.write_text(
        f"""# Tunnel für {host} → {origin}. Eigener Tunnel, NICHT der Prod-Tunnel.
tunnel: {tid}
credentials-file: {kdatei}
no-autoupdate: true
ingress:
  - hostname: {host}
    service: http://{origin}
  # Alles andere prallt ab: der Tunnel ist kein allgemeiner Zugang zur Maschine.
  - service: http_status:404
"""
    )
    print(f"Config geschrieben: {cfg}")

    ziel = f"{tid}.cfargotunnel.com"
    vorhanden = api("GET", f"/zones/{zone}/dns_records?name={host}")["result"] or []
    if vorhanden:
        r = vorhanden[0]
        if r["content"] == ziel and r.get("proxied"):
            print(f"DNS {host} zeigt schon richtig auf den Tunnel.")
        else:
            api(
                "PATCH",
                f"/zones/{zone}/dns_records/{r['id']}",
                {"type": "CNAME", "name": host, "content": ziel, "proxied": True},
            )
            print(f"DNS {host} umgestellt (war: {r['type']} {r['content'][:40]}).")
    else:
        api(
            "POST",
            f"/zones/{zone}/dns_records",
            {
                "type": "CNAME",
                "name": host,
                "content": ziel,
                "proxied": True,
                "comment": "Zugang nur über Cloudflare Access",
            },
        )
        print(f"DNS {host} -> {ziel} (proxied) angelegt.")
    print(f"TUNNEL_ID={tid}")


if __name__ == "__main__":
    main()
