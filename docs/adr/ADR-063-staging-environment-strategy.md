# ADR-063: Staging Environment Strategy

## Status

Accepted

## Context and Problem Statement

ADR-061 (Hardcoding Elimination Strategy) identifiziert fehlende Staging-Environments als Hauptursache für Hardcoding-Probleme: Ohne Staging werden Konfigurationswerte direkt in Code geschrieben, weil kein separates Environment existiert, das die Trennung erzwingt.

Aktuell läuft jede App direkt von `main` → Prod (dev-server). Es gibt keine Möglichkeit, Änderungen vor dem Prod-Deploy zu validieren. Dies führt zu:

- Hardcoded Prod-IPs und -URLs in Code (→ ADR-061)
- Keine Möglichkeit, Breaking Changes zu testen
- Rollbacks als einzige Fehler-Recovery-Strategie
- Fehlende 12-Factor-App-Compliance (Factor III: Config)

## Decision Drivers

- **Sicherheit**: Kein direktes Deployment ungetesteter Änderungen in Prod
- **12-Factor Compliance**: Config vollständig aus Umgebungsvariablen (Factor III)
- **Kosten**: Minimaler Infrastruktur-Overhead (kein zweiter Server)
- **Einfachheit**: Staging soll kein Full-Clone von Prod sein
- **ADR-061-Abhängigkeit**: Staging ist Voraussetzung für vollständige Hardcoding-Elimination

## Considered Options

1. **Separater Staging-Server** (zweite Hetzner-VM)
2. **Docker-basiertes Staging auf dev-server** (andere Ports, gleicher Host)
3. **Branch-basiertes Staging** (`staging`-Branch → separater Docker-Stack)
4. **Kein Staging** (Status quo — nur Rollback)

## Decision Outcome

Chosen option: **Option 3 — Branch-basiertes Staging auf dev-server**, weil:

- Kein zusätzlicher Server-Kosten (dev-server hat ausreichend Kapazität)
- Erzwingt Config-Trennung durch separate `.env.staging`-Dateien
- Nutzt bestehende Platform-Workflows (`_ci-python.yml`, `_deploy-hetzner.yml`)
- Staging-Ports sind klar von Prod-Ports getrennt (Offset +100)

### Consequences

- **Positiv**: Vollständige 12-Factor-Compliance nach Migration
- **Positiv**: Hardcoding-Probleme werden strukturell verhindert
- **Positiv**: Kein Mehraufwand für neue Repos (Workflow-Template)
- **Negativ**: Staging-Ports müssen pro App reserviert werden
- **Negativ**: `staging`-Branch-Pflege erfordert Disziplin (kein Force-Push auf `main`)

## Implementation

### Port-Konvention

| App | Prod-Port | Staging-Port |
|-----|-----------|--------------|
| bfagent | 8080 | 8180 |
| dev-hub | 8081 | 8181 |
| travel-beat | 8082 | 8182 |
| weltenhub | 8085 | 8185 |
| trading-hub | 8088 | 8188 |
| risk-hub | 8090 | 8190 |
| cad-hub | 8094 | 8194 |
| pptx-hub | 8095 | 8195 |
| coach-hub | 8007 | 8107 |
| wedding-hub | 8096 | 8196 |

### Branch-Strategie

```
main ──────────────────────────────────► Prod-Deploy
  └── staging ──────────────────────────► Staging-Deploy
        └── feature/* ──► PR → staging ──► PR → main
```

### Workflow-Erweiterung

```yaml
# .github/workflows/ci-cd.yml (Ergänzung)
deploy-staging:
  if: github.ref == 'refs/heads/staging'
  uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
  with:
    deploy_path: /opt/<app>-staging/
    compose_file: docker-compose.staging.yml
    port: <staging-port>
  secrets: inherit
```

### Config-Trennung

```
/opt/<app>/           → Prod  (.env.prod)
/opt/<app>-staging/   → Staging (.env.staging)
```

### Nginx-Routing

Staging-Domains folgen dem Muster `staging.<app-domain>`:

```nginx
server {
    server_name staging.bfagent.iil.pet;
    location / {
        proxy_pass http://46.225.113.1:<staging-port>;
    }
}
```

## Migration Tracking

### Phase 1 — Infrastruktur (Q2 2026)

| Task | Status |
|------|--------|
| Port-Reservierung dokumentieren | ☐ Pending |
| `staging`-Branch in allen Repos anlegen | ☐ Pending |
| `/opt/<app>-staging/` Verzeichnisse anlegen | ☐ Pending |
| `.env.staging` Templates erstellen | ☐ Pending |

### Phase 2 — Workflow-Integration (Q3 2026)

| Task | Status |
|------|--------|
| `_deploy-hetzner.yml` um Staging-Support erweitern | ☐ Pending |
| `docker-compose.staging.yml` pro App | ☐ Pending |
| Nginx-Staging-Configs auf Prod-Server | ☐ Pending |
| SSL-Zertifikate für `staging.*`-Domains | ☐ Pending |

### Phase 3 — Vollbetrieb (Q4 2026)

| Task | Status |
|------|--------|
| Alle Apps auf Staging-Workflow migriert | ☐ Pending |
| Hardcode-Scanner in Staging-CI integriert | ☐ Pending |
| ADR-061 Phase 3 (vollständige Env-Var-Migration) | ☐ Pending |

## More Information

- **ADR-061**: Hardcoding Elimination Strategy (Voraussetzung)
- **ADR-056**: Deployment Readiness Checklist (Staging-Erweiterung nötig)
- **12-Factor App**: https://12factor.net/config
- **Platform Reusable Workflows**: `.github/workflows/_deploy-hetzner.yml`
