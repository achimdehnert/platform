# orchestrator.iil.pet — Prod-nginx (IaC-Spiegel)

SoR für die Reverse-Proxy-Config von `orchestrator.iil.pet` (MCP/Orchestrator,
`mcp-hub`). Bisher war diese Config **nur host-lokal** auf `88.198.191.108`
(hetzner-prod) und damit unsichtbar/driftanfällig — dieser Spiegel schließt das.

## Topologie
Cloudflare-Tunnel (catch-all, s. `../cloudflared-tunnels.yaml`) → nginx auf
`88.198.191.108` (`server_name orchestrator.iil.pet`) → Container
`mcp_hub_orchestrator_http` auf `127.0.0.1:8000`.

## ⚠️ Pfad-Whitelist (Drift-Lehre 2026-06-01)
nginx leitet **nur die explizit deklarierten `location`-Pfade** an `:8000`. Eine
neue App-Route (`mcp-hub` `orchestrator_mcp/server.py`) ohne passenden
`location`-Block ⇒ **nginx-eigener 404**, der Request erreicht den Container nie.

Symptom-Falsifikation (billig, ohne SSH): 404-**Body** prüfen —
App-404 = JSON (`{"ok":false,...}`), nginx-404 = HTML mit `<hr><center>nginx</center>`.

Konkreter Vorfall: `/api/discovery/klickdummy/upsert` (platform:ADR-215) +
`/readyz`/`/livez` fehlten in der Whitelist → 404, fälschlich auf Image/Build-Cache
geschoben (mehrere Deploy-Zyklen verloren). Fix = `location /api/`, `= /readyz`,
`= /livez` ergänzt (am 2026-06-01 live).

## Apply auf dem Host
```bash
scp orchestrator.iil.pet.conf hetzner-prod:/tmp/
ssh hetzner-prod '
  sudo cp /etc/nginx/sites-available/orchestrator.iilpet.conf \
          /etc/nginx/sites-available/orchestrator.iilpet.conf.bak-$(date +%F)
  sudo cp /tmp/orchestrator.iil.pet.conf /etc/nginx/sites-available/orchestrator.iilpet.conf
  sudo nginx -t && sudo systemctl reload nginx'
```

## Checkliste „neue Orchestrator-Route geht live"
1. Route in `mcp-hub` `orchestrator_mcp/server.py` (`app = Starlette(routes=[...])`).
2. **Hier** einen `location`-Block ergänzen (sonst nginx-404).
3. `orchestrator.iil.pet.conf` auf den Host applyen (s.o.).
4. Verifizieren: `curl -i https://orchestrator.iil.pet/<route>` — App-Antwort, kein nginx-404.
