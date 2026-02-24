---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-045: Secrets & Environment Management

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-18 |
| **Last Reviewed** | 2026-02-21 |
| **Author** | Achim Dehnert |
| **Reviewers** | ADR Board |
| **Supersedes** | — |
| **Related** | ADR-021 (Unified Deployment), ADR-022 (Platform Consistency), ADR-044 (MCP-Hub Architecture), ADR-056 (Multi-Tenancy) |
| **Based on** | `konzept-env-secrets-management.md`, `review-secrets-management.md` |
| **Version** | 3 (2026-02-21: implementation status review, ADR-056 gap added) |

---

## Implementation Status (as of 2026-02-23)

> **Status: In Progress — Phases 1, 3, 5, 6 abgeschlossen. Phase 2 wartet auf age-Key. Phase 4, 7 ausstehend.**

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | SOPS + age keypair setup | ✅ `age` 1.1.1 + `sops` 3.9.4 auf dev-server installiert. age-Key auf Entwicklermaschine prüfen + `SOPS_AGE_KEY` in GitHub Secrets setzen |
| Phase 2 | Encrypt existing secrets into `secrets.enc.env` per repo | ⏳ `scripts/create-secrets.sh` fertig — User muss mit age-Key ausführen |
| Phase 3 | `config/secrets.py` + `read_secret()` in Django apps | ✅ `bfagent` + `dev-hub` production.py umgestellt. Fallback: `/run/secrets/` → env var |
| Phase 4 | MCP server Settings: `SecretStr` + `secrets_dir` | ❌ Pending |
| Phase 5 | CI/CD pipeline: SOPS decrypt step + `/run/secrets/` push | ✅ `_deploy-hetzner.yml`: `secrets` Job vor `deploy`, skipped wenn `SOPS_AGE_KEY` nicht gesetzt |
| Phase 6 | Reboot resilience: systemd `secrets-check.service` | ✅ `deployment/systemd/secrets-check.service` committed — noch nicht auf Server installiert |
| Phase 7 | Cleanup: remove `.env.prod` from server | ❌ Pending — nach erstem erfolgreichen SOPS-Deploy |

### What IS done

| Item | Status |
|------|--------|
| `.sops.yaml` in `platform` repo with 2 age recipients | ✅ Committed (`platform/.sops.yaml`) |
| Decision accepted (Variante C: Hybrid SOPS + file-based) | ✅ |
| `deploy-remote.sh` uses `env_file:` not `${VAR}` interpolation | ✅ (platform rule already enforced) |

### Current Production Reality (legacy, to be migrated)

All apps currently use `.env.prod` files on the Hetzner server (`88.198.191.108`):

```text
/opt/travel-beat/.env.prod     ← active
/opt/bfagent-app/.env.prod     ← active
/opt/weltenhub/.env.prod       ← active
/opt/risk-hub/.env.prod        ← active (if deployed)
```

`age` 1.1.1 und `sops` 3.9.4 sind auf dem dev-server (46.225.113.1) installiert.
`/run/secrets/` existiert noch nicht — wird beim ersten SOPS-Deploy erstellt.
`.env.prod` bleibt als Fallback aktiv bis Phase 7 abgeschlossen ist.

### Gap: ADR-056 Multi-Tenancy (travel-beat)

ADR-056 introduced `apps.tenants` with `Client` and `Domain` models in travel-beat.
The tenant provisioning step (creating the default `drifttales` tenant) currently runs
as an inline `manage.py shell` command in `deploy-remote.sh`. This is acceptable for
Phase 1 but must be revisited in ADR-045 Phase 5:

- The tenant provisioning command must run **after** `/run/secrets/` is populated
- The `DATABASE_URL` secret must be available before `migrate_schemas` runs
- Future: per-tenant secrets (e.g., tenant-specific API keys) are out of scope for ADR-045

---

## 1. Context

### 1.1 Current State

The platform ecosystem runs 8 MCP servers and 7 Django applications, each with
independent secrets management. Every service defines its own `env_prefix`,
reads from its own `.env` file, and has no rotation or audit capability.

| Problem | Impact |
|---------|--------|
| 6 different `env_prefix` conventions, 3 servers without Settings class | No single source of truth for required env vars |
| Secrets stored as `str` in some servers, `SecretStr` in others | Inconsistent protection against accidental logging |
| 8 manual `.env.prod` files on Hetzner server | Drift, no audit trail, no rotation |
| No expiry or rotation mechanism | Stale API keys accumulate risk |
| Hardcoded paths (`C:\Users\achim\...`) in 8 files | Breaks on any environment change |

### 1.2 Architecture Constraint: WSL vs. Hetzner

**Critical distinction** that the original concept did not address:

- **Django apps** (bfagent, travel-beat, weltenhub, risk-hub, pptx-hub) run as
  **Docker containers on Hetzner** (88.198.191.108). They use `django.conf.settings`
  with `os.environ.get()` or `python-decouple`. Secrets change rarely (deploy-time).

- **MCP servers** (deployment_mcp, orchestrator_mcp, llm_mcp) run **locally in
  WSL** on the developer machine. They use `pydantic-settings` with `env_prefix`.
  They do NOT run on Hetzner.

This means a PostgreSQL-based secrets provider on Hetzner would require the
local MCP servers to maintain a persistent remote DB connection just to load
their settings — adding latency, VPN dependency, and a single point of failure
for local tooling.

### 1.3 Evaluated Approaches

Three approaches were evaluated in the review phase:

| Approach | Complexity | Runtime Rotation | Service Isolation | SPOF Risk |
|----------|-----------|-----------------|-------------------|-----------|
| **A: PostgreSQL + secrets_dir** | ~5 days | Yes (LISTEN/NOTIFY) | Yes (per-service query) | DB down = no secrets |
| **B: SOPS + age** | ~2 days | No (redeploy needed) | No (shared age key) | None |
| **C: Hybrid** | ~3 days | Config only | Yes for DB config | Minimal |

---

## 2. Decision

### We adopt Variante C: Hybrid — SOPS for deployment secrets, file-based secrets for runtime

### 2.1 Separation of Concerns

```text
SOPS + age (encrypted in Git, decrypted at deploy-time):
  -> API keys, tokens, credentials (AMADEUS_CLIENT_SECRET, HCLOUD_TOKEN, HF_TOKEN)
  -> SSH keys stay as FILES on host (chmod 600), never in DB or SOPS
  -> Decrypted in CI/CD pipeline, pushed to /run/secrets/ via SSH

Django apps (Hetzner Docker containers):
  -> Read from /run/secrets/ via read_secret() helper (see 2.4)
  -> Fallback to environment variables for backward compatibility
  -> No pydantic-settings dependency

MCP servers (pydantic-settings, WSL):
  -> Read from ~/.config/mcp-hub/.env (gitignored)
  -> secrets_dir="/run/secrets" for production (unused in WSL)
  -> No DB dependency, no remote calls for settings
```

### 2.2 SOPS + age for Secrets

```yaml
# .sops.yaml — MUST have at least 2 recipients (bus factor)
creation_rules:
  - path_regex: secrets\.enc\.env$
    age: >-
      age1<primary-developer-key>,
      age1<backup-key-stored-in-safe>
```

```text
# Per-repo encrypted secrets file
mcp-hub/secrets.enc.env        # MCP server secrets
bfagent/secrets.enc.env        # bfagent production secrets
travel-beat/secrets.enc.env    # travel-beat production secrets
```

**Key management rule:** Minimum 2 age recipients in every `.sops.yaml`:
one primary (developer machine) and one backup (physically separate storage,
e.g., USB key in a safe). Loss of primary key does not cause irrecoverable
secret loss.

### 2.3 Secret-Zero: Decrypt in CI/CD, Not on Server

The age private key **never** resides on the Hetzner production server.
Decryption happens in the GitHub Actions CI/CD pipeline, which pushes
the plaintext files to `/run/secrets/` via SSH.

```text
+-----------------------------------------------------+
|  GitHub Actions Runner (ephemeral)                   |
|                                                      |
|  1. Checkout repo (includes secrets.enc.env)         |
|  2. Decrypt: SOPS_AGE_KEY=${{ secrets.SOPS_AGE_KEY }}|
|     sops -d secrets.enc.env -> plaintext in memory   |
|  3. SSH to Hetzner: write each secret to             |
|     /run/secrets/<key> (chmod 400, root:root)        |
|  4. Verify: required secrets exist and are non-empty |
|  5. docker compose up --force-recreate               |
+-----------------------------------------------------+

Consequence:
  - age private key exists ONLY in GitHub Secrets (encrypted at rest)
  - Hetzner server never has the age key -> cannot decrypt Git history
  - Compromised server exposes current /run/secrets/ only, not historical
```

**GitHub Secret required:** `SOPS_AGE_KEY` — the full contents of the age
private key file (starts with `AGE-SECRET-KEY-1...`).

### 2.4 Settings Patterns (Two Worlds)

#### Pattern A: Django Apps (bfagent, travel-beat, weltenhub, risk-hub)

Django apps use `django.conf.settings`, not pydantic-settings. A shared
utility function reads from `/run/secrets/` with env var fallback:

```python
"""config/secrets.py — Shared across all Django apps."""

import os
from pathlib import Path

SECRETS_DIR = Path(os.environ.get("SECRETS_DIR", "/run/secrets"))


def read_secret(
    key: str,
    default: str = "",
    required: bool = False,
) -> str:
    """Read secret from /run/secrets/ file, fall back to env var.

    Priority: /run/secrets/<key_lower> -> os.environ[KEY] -> default.
    Raises ValueError in production if required=True and no value found.
    """
    secret_file = SECRETS_DIR / key.lower()
    if secret_file.is_file():
        value = secret_file.read_text().strip()
        if value:
            return value

    value = os.environ.get(key, "")
    if value:
        return value

    if required and os.environ.get(
        "DJANGO_SETTINGS_MODULE", ""
    ).endswith("production"):
        raise ValueError(
            f"Required secret {key!r} not found in "
            f"{SECRETS_DIR} or environment"
        )

    return default
```

Usage in `config/settings/production.py`:

```python
from config.secrets import read_secret

SECRET_KEY = read_secret("DJANGO_SECRET_KEY", required=True)
DATABASE_URL = read_secret("DATABASE_URL", required=True)
AMADEUS_CLIENT_SECRET = read_secret("AMADEUS_CLIENT_SECRET", required=True)
```

Usage in `config/settings/development.py`:

```python
# No /run/secrets/ needed — reads from environment or .env via decouple
from decouple import config

SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-insecure-key")
```

#### Pattern B: MCP Servers (pydantic-settings)

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRAVEL_MCP_",
        env_file=".env",                    # Local dev
        secrets_dir="/run/secrets",          # Production (CI/CD-decrypted)
        secrets_dir_missing="warn",          # No crash in dev (WSL)
        extra="ignore",
        case_sensitive=False,
    )

    # Secrets: always SecretStr, no default value
    amadeus_client_id: SecretStr
    amadeus_client_secret: SecretStr

    # Config: normal types, with defaults
    log_level: str = Field(default="INFO")
    max_results: int = Field(default=50)
```

**Priority chain (pydantic-settings native):**

```text
1. Environment variables          <- docker-compose env_file, systemd
2. .env file                      <- local development
3. /run/secrets/ files            <- CI/CD-decrypted production secrets
4. Default values                 <- code
```

### 2.5 Standardized Prefix Convention

```text
Format: <SERVICE>_<KEY>

TRAVEL_MCP_AMADEUS_CLIENT_ID=abc
TRAVEL_MCP_AMADEUS_CLIENT_SECRET=xyz
ANALYTICS_MCP_MINDSDB_API_KEY=abc
ILLUSTRATION_MCP_HF_TOKEN=hf_xxx
DEPLOYMENT_MCP_HCLOUD_TOKEN=abc
GERMAN_TAX_MCP_OLDP_API_KEY=abc
```

**Migration for existing non-prefixed vars** (e.g., `AMADEUS_CLIENT_ID`):

```python
from pydantic import AliasChoices, Field, SecretStr

class AmadeusSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRAVEL_MCP_AMADEUS_")

    client_id: SecretStr = Field(
        validation_alias=AliasChoices(
            "TRAVEL_MCP_AMADEUS_CLIENT_ID",  # New format
            "AMADEUS_CLIENT_ID",              # Legacy compat
        )
    )
```

### 2.6 Rules

| Rule | Rationale |
|------|-----------|
| All credentials as `SecretStr` (MCP) or `read_secret(required=True)` (Django) | Prevents accidental logging, fail-fast in production |
| No default value for required secrets | Forces explicit configuration, prevents empty production |
| `secrets_dir="/run/secrets"` in every MCP Settings class | Native Docker Secrets compatible path |
| `config/secrets.py` with `read_secret()` in every Django app | Consistent pattern, no pydantic dependency |
| `env_file=".env"` in every MCP Settings class | Consistent local dev |
| `extra="ignore"` | Prevents crash from unrelated env vars |
| SSH keys stay as host files (`chmod 600`) | Never in DB, never in SOPS |
| `.env.example` in every repo | Documents required variables |
| Never use `${VAR}` interpolation in compose `environment:` | Use `env_file:` exclusively (platform rule) |
| Minimum 2 age recipients in `.sops.yaml` | Bus factor — backup key in physically separate storage |
| `secrets.env` in `.gitignore` AND Gitleaks patterns | Prevents accidental plaintext commit |
| age private key ONLY in GitHub Secrets | Never on Hetzner server, never in Git |

---

## 3. Implementation Plan

### Phase 1: SOPS + age Setup (Day 1)

```bash
# Install age + sops on dev machine (WSL)
sudo apt install age
pip install sops  # or: wget from GitHub releases

# Generate PRIMARY age keypair
age-keygen -o ~/.config/sops/age/keys.txt
# Output: public key: age1abc...
# -> Save public key for .sops.yaml

# Generate BACKUP age keypair (store on USB / password manager)
age-keygen -o /tmp/backup-age-key.txt
# -> Copy to physically separate storage, then:
shred -u /tmp/backup-age-key.txt

# Create .sops.yaml template in platform repo
cat > .sops.yaml << 'EOF'
creation_rules:
  - path_regex: secrets\.enc\.env$
    age: >-
      age1<primary-key>,
      age1<backup-key>
EOF
```

### Phase 2: Migrate Existing Secrets (Day 1-2)

Per repo: encrypt current secrets directly via pipe (no plaintext on disk):

```bash
# Example for travel-beat — secrets piped, never written to disk
sops -e --input-type dotenv --output-type dotenv /dev/stdin \
    <<< "DJANGO_SECRET_KEY=actual_value
DATABASE_URL=postgresql://...
AMADEUS_CLIENT_SECRET=xyz" \
    > secrets.enc.env

# Verify encryption worked
sops -d secrets.enc.env  # should show plaintext

# Commit encrypted file
git add secrets.enc.env .sops.yaml
git commit -m "feat: add SOPS-encrypted secrets (ADR-045)"
```

Update `.gitignore` in every repo:

```text
# Secrets — NEVER commit plaintext
secrets.env
.env.prod
.env.local

# Encrypted secrets — safe to commit
!secrets.enc.env
```

### Phase 3: Add read_secret() to Django Apps (Day 2)

Create `config/secrets.py` in each Django app (see Pattern A in section 2.4).
Update `config/settings/production.py` to use `read_secret()`.
Keep `config/settings/development.py` unchanged (uses `decouple`).

### Phase 4: Update MCP Server Settings (Day 2)

Per MCP server: add `secrets_dir` to Settings, migrate to `SecretStr`:

```python
# Before (analytics_mcp)
api_key: str = ""

# After
api_key: SecretStr  # No default -> fails fast if missing
```

### Phase 5: CI/CD Pipeline Update (Day 2-3)

Add SOPS decrypt step to GitHub Actions deploy workflow (`_deploy-hetzner.yml`):

```yaml
- name: Decrypt and deploy secrets
  env:
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
  run: |
    # Decrypt secrets in runner memory (single call)
    decrypted=$(sops -d secrets.enc.env)
    count=0

    # Write each secret to /run/secrets/ on remote host via SSH
    while IFS='=' read -r key value; do
      [ -z "$key" ] && continue
      key_lower=$(echo "$key" | tr '[:upper:]' '[:lower:]')
      # printf prevents trailing newline (critical for API keys)
      ssh $DEPLOY_HOST "mkdir -p /run/secrets && \
        printf '%s' '${value}' > /run/secrets/${key_lower} && \
        chmod 400 /run/secrets/${key_lower}"
      count=$((count + 1))
    done <<< "$decrypted"

    echo "Deployed ${count} secrets to /run/secrets/"

- name: Verify required secrets
  run: |
    ssh $DEPLOY_HOST 'for f in django_secret_key database_url; do
      if [ ! -s "/run/secrets/$f" ]; then
        echo "FATAL: Missing or empty secret: $f" >&2
        exit 1
      fi
    done
    echo "All required secrets verified."'
```

**Note (ADR-056 interaction):** For travel-beat, the SOPS decrypt step must run
**before** `migrate_schemas`, as the DB connection requires `DATABASE_URL` from
`/run/secrets/`. The tenant provisioning step in `deploy-remote.sh` is unaffected
(it runs after container start, which reads from `/run/secrets/` via `read_secret()`).

### Phase 6: Reboot Resilience (Day 3)

`/run/` is tmpfs — cleared on reboot. Secrets must be re-deployed after any
server restart. Install a systemd service that blocks Docker startup until
secrets are present:

```ini
# /etc/systemd/system/secrets-check.service
[Unit]
Description=Verify /run/secrets/ populated before Docker
Before=docker.service
ConditionPathExists=/run/secrets

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'test -s /run/secrets/django_secret_key || exit 1'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

After a reboot, Docker will not start containers until the next CI/CD deploy
pushes secrets. This is intentional: **no secrets = no service**, preventing
silent startup with missing credentials.

### Phase 7: Cleanup (Day 3)

```bash
# Remove .env.prod from Hetzner server (replaced by /run/secrets/)
# Keep .env.example in repos (documents required variables)
# Verify Gitleaks catches secrets.env if accidentally staged
```

---

## 4. Consequences

### 4.1 What Changes

| Component | Before | After |
|-----------|--------|-------|
| **Secret storage** | `.env.prod` files on server | `secrets.enc.env` in Git (encrypted) |
| **Secret decryption** | N/A (plaintext files) | SOPS + age in CI/CD, SSH to `/run/secrets/` |
| **Django settings** | `os.environ.get()` / decouple | `read_secret()` with `/run/secrets/` + env fallback |
| **MCP settings** | Mixed `str`/`SecretStr`, no `secrets_dir` | All `SecretStr`, `secrets_dir="/run/secrets"` |
| **Prefix convention** | 6 different patterns | Unified `<SERVICE>_<KEY>` |
| **Local dev** | `.env` per repo | `.env` per repo (unchanged) |
| **MCP servers (WSL)** | `.env` in repo dir | `.env` in `~/.config/mcp-hub/` (unchanged) |
| **Rotation** | Manual SSH + edit .env.prod | Update `secrets.enc.env`, git push, deploy |
| **Audit trail** | None | Git history on `secrets.enc.env` |
| **Reboot behavior** | Containers restart with .env.prod | Containers blocked until CI/CD re-deploys secrets |

### 4.2 What Does NOT Change

- Django settings framework (`django.conf.settings`) remains primary for Django apps
- pydantic-settings remains primary for MCP servers
- Local development workflow unchanged (`.env` files, `decouple`)
- MCP servers in WSL do NOT need DB access for secrets
- Docker Compose structure unchanged
- No new services to operate (no Vault, no extra DB)

### 4.3 Trade-offs

| Accepted | Rejected Alternative |
|----------|---------------------|
| No live rotation (redeploy needed) | PostgreSQL + LISTEN/NOTIFY (adds DB-SPOF, WSL latency) |
| Shared age key (no per-service isolation) | Per-service encryption keys (complexity for 8 servers) |
| Git-based audit trail | Custom audit_log table (overengineered for current scale) |
| Reboot requires re-deploy | Persistent secrets on disk (defeats tmpfs security benefit) |
| CI/CD dependency for secrets | age key on server (secret-zero: server compromise exposes all history) |

### 4.4 Migration Risk

- **Low**: Settings classes gain `secrets_dir` param (additive, non-breaking)
- **Low**: `AliasChoices` allows old + new env var names simultaneously
- **Low**: `read_secret()` falls back to `os.environ`, no behavior change if `/run/secrets/` absent
- **Medium**: Deploy pipeline needs SOPS decrypt step (testable with `--dry-run`)
- **Zero**: Local dev workflow unchanged

---

## 5. Rejected Alternatives

### 5.1 Full PostgreSQL + Fernet (Original Concept)

The original `konzept-env-secrets-management.md` proposed a PostgreSQL-based
secrets store with Fernet encryption, `os.environ` injection, and polling-based
rotation. Rejected because:

- **`os.environ` injection is process-global** — not thread-safe, no isolation
  between services, race conditions during rotation (K-01 from review)
- **pydantic-settings fallback chain violated** — DB injection at priority 2
  would override `.env` files, breaking local dev override (K-03)
- **Django apps ignored** — the concept only addressed pydantic-settings;
  Django apps use `django.conf.settings` which has no `secrets_dir` (R-01)
- **WSL architecture mismatch** — MCP servers run locally, not on Hetzner;
  persistent DB connection from WSL to remote PostgreSQL is fragile
- **Secret-zero unsolved** — age key on server means server compromise
  exposes all historical secrets from Git, worse than current state (R-02)
- **Custom encryption** — Fernet is fine but unnecessary; SOPS/age is
  battle-tested, CNCF-adjacent, requires zero custom code
- **5 days effort** vs. 3 days for hybrid approach

### 5.2 HashiCorp Vault

Overkill for 8 servers. Requires operating a separate cluster. ~50 EUR/month
for managed Vault. Revisit if the platform grows beyond 20 services.

### 5.3 Doppler / Infisical (SaaS)

Data sovereignty concern. Secrets leave our infrastructure. 20-100 EUR/month.
Vendor lock-in.

### 5.4 PostgreSQL Config Store (Deferred)

Runtime-changeable config (feature flags, log levels) via a PostgreSQL
`app_config` table was considered as Phase 6. Deferred to a separate ADR
when a concrete use case arises. This ADR focuses strictly on secrets.

---

## 6. Open Questions

1. **Rotation cadence**: Proposed 90 days for API tokens, annual for
   infrastructure credentials. Needs team agreement.

2. **Gitleaks rule**: Exact pattern for detecting unencrypted `secrets.env`
   files in pre-commit hooks. To be defined during Phase 2 implementation.

3. **Per-app required secrets list**: Each Django app and MCP server should
   declare its required secrets (for Phase 5 verification step). Format TBD
   (e.g., `REQUIRED_SECRETS` list in `config/secrets.py` or `.secrets-manifest`).

4. **ADR-056 interaction**: travel-beat uses `django-tenants` — the `DATABASE_URL`
   secret must be available before `migrate_schemas --shared` runs. The ordering
   in `_deploy-hetzner.yml` (SOPS decrypt → migrate → tenant provision) must be
   validated when Phase 5 is implemented.

---

## 7. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-02-18 | Initial draft |
| 2 | 2026-02-18 | Incorporates critical review R-01 through A-06 |
| 3 | 2026-02-21 | Implementation status review: all phases still pending. `.sops.yaml` committed to `platform`. ADR-056 gap documented. Open Question 4 added. |
