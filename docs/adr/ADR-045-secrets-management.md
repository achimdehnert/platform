# ADR-045: Secrets & Environment Management

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-18 |
| **Author** | Achim Dehnert |
| **Reviewers** | ADR Board |
| **Supersedes** | — |
| **Related** | ADR-021 (Unified Deployment), ADR-022 (Platform Consistency), ADR-044 (MCP-Hub Architecture) |
| **Based on** | `konzept-env-secrets-management.md`, `review-secrets-management.md` |

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
  **Docker containers on Hetzner** (88.198.191.108). They read `.env.prod` at
  container start. Secrets change rarely (deploy-time).

- **MCP servers** (deployment_mcp, orchestrator_mcp, llm_mcp) run **locally in
  WSL** on the developer machine. They use subprocess SSH to manage remote
  infrastructure. They do NOT run on Hetzner.

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

### We adopt Variante C: Hybrid — SOPS for deployment secrets, PostgreSQL for runtime config only

### 2.1 Separation of Concerns

```text
SOPS + age (encrypted in Git, decrypted at deploy-time):
  → API keys, tokens, credentials (AMADEUS_CLIENT_SECRET, HCLOUD_TOKEN, HF_TOKEN)
  → SSH keys stay as FILES on host (chmod 600), never in DB or SOPS
  → Decrypted to /run/secrets/ at deploy-time via deploy script

PostgreSQL (existing bfagent_db, unencrypted):
  → Feature flags, log levels, non-sensitive config
  → Only for Django apps on Hetzner (not for local MCP servers)
  → Optional: runtime-changeable config without redeploy

Local MCP servers (WSL):
  → Read from ~/.config/mcp-hub/.env (gitignored)
  → No DB dependency, no remote calls for settings
  → pydantic-settings reads .env directly
```

### 2.2 SOPS + age for Secrets

```text
# Per-repo encrypted secrets file
mcp-hub/secrets.enc.env        # MCP server secrets
bfagent/secrets.enc.env        # bfagent production secrets
travel-beat/secrets.enc.env    # travel-beat production secrets
...

# .sops.yaml in each repo
creation_rules:
  - path_regex: secrets\.enc\.env$
    age: >-
      age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

```bash
# Deploy script decrypts to /run/secrets/
sops -d secrets.enc.env | while IFS='=' read -r key value; do
    echo "$value" > "/run/secrets/${key,,}"
    chmod 400 "/run/secrets/${key,,}"
done
```

### 2.3 pydantic-settings with secrets_dir

All Django apps and MCP servers adopt the same Settings pattern:

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRAVEL_MCP_",
        env_file=".env",                    # Local dev
        secrets_dir="/run/secrets",          # Production (SOPS-decrypted)
        secrets_dir_missing="warn",          # No crash in dev
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
1. Environment variables          ← docker-compose env_file, systemd
2. .env file                      ← local development
3. /run/secrets/ files            ← SOPS-decrypted production secrets
4. Default values                 ← code
```

This means `.env` in local dev overrides `/run/secrets/`, which is the correct
behavior: developers can override production-style secrets locally.

### 2.4 Standardized Prefix Convention

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

### 2.5 Rules

| Rule | Rationale |
|------|-----------|
| All credentials as `SecretStr` | Prevents accidental logging via `repr()` |
| No default value for required secrets | Forces explicit configuration, prevents empty production |
| `secrets_dir="/run/secrets"` in every Settings class | Native Docker Secrets compatible path |
| `env_file=".env"` in every Settings class | Consistent local dev |
| `extra="ignore"` | Prevents crash from unrelated env vars |
| SSH keys stay as host files (`chmod 600`) | Never in DB, never in SOPS |
| `.env.example` in every repo | Documents required variables |
| Never use `${VAR}` interpolation in compose `environment:` | Use `env_file:` exclusively (platform rule) |

---

## 3. Implementation Plan

### Phase 1: SOPS Setup (Day 1)

```bash
# Install age + sops on dev machine
brew install age sops    # or: apt install age, pip install sops

# Generate age keypair (once)
age-keygen -o ~/.config/sops/age/keys.txt
# Public key → .sops.yaml in each repo
# Private key → stays on dev machine + Hetzner host

# Create .sops.yaml in platform repo (template for all)
cat > .sops.yaml << 'EOF'
creation_rules:
  - path_regex: secrets\.enc\.env$
    age: >-
      age1<your-public-key-here>
EOF
```

### Phase 2: Migrate Existing Secrets (Day 1-2)

Per repo: extract current `.env.prod` secrets into `secrets.enc.env`:

```bash
# Example for travel-beat
cd /home/dehnert/github/travel-beat
echo "TRAVEL_MCP_AMADEUS_CLIENT_ID=actual_value" > secrets.env
echo "TRAVEL_MCP_AMADEUS_CLIENT_SECRET=actual_value" >> secrets.env
sops -e secrets.env > secrets.enc.env
rm secrets.env  # plaintext must not persist
git add secrets.enc.env .sops.yaml
```

### Phase 3: Update Settings Classes (Day 2)

Per MCP server: add `secrets_dir` to Settings, migrate to `SecretStr`:

```python
# Before (analytics_mcp)
api_key: str = ""

# After
api_key: SecretStr  # No default → fails fast if missing
```

### Phase 4: Deploy Script Update (Day 2-3)

Update `deploy-remote.sh` (ADR-022 pattern) to decrypt SOPS before container start:

```bash
# In deploy-remote.sh, before docker compose up:
if command -v sops &> /dev/null && [ -f secrets.enc.env ]; then
    mkdir -p /run/secrets
    sops -d secrets.enc.env | while IFS='=' read -r key value; do
        key_lower=$(echo "$key" | tr '[:upper:]' '[:lower:]')
        printf '%s' "$value" > "/run/secrets/${key_lower}"
        chmod 400 "/run/secrets/${key_lower}"
    done
    echo "Decrypted $(sops -d secrets.enc.env | wc -l) secrets to /run/secrets/"
fi
```

### Phase 5: Cleanup (Day 3)

```bash
# Remove .env.prod from Hetzner servers (replaced by /run/secrets/)
# Keep .env.example in repos
# Update .gitignore: secrets.env (plaintext), keep secrets.enc.env (encrypted)
```

### Phase 6: Optional — PostgreSQL Config Store (Week 2+)

Only if runtime-changeable config is needed (feature flags, log levels):

```sql
CREATE TABLE IF NOT EXISTS app_config (
    id          SERIAL PRIMARY KEY,
    app_name    VARCHAR(64) NOT NULL,
    key         VARCHAR(128) NOT NULL,
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_app_key UNIQUE (app_name, key)
);
```

This is **not** for secrets — only for non-sensitive config that should be
changeable without redeploy.

---

## 4. Consequences

### 4.1 What Changes

| Component | Before | After |
|-----------|--------|-------|
| **Secret storage** | `.env.prod` files on server | `secrets.enc.env` in Git (encrypted) |
| **Secret decryption** | N/A (plaintext files) | SOPS + age at deploy-time → `/run/secrets/` |
| **Settings classes** | Mixed `str`/`SecretStr`, no `secrets_dir` | All `SecretStr`, `secrets_dir="/run/secrets"` |
| **Prefix convention** | 6 different patterns | Unified `<SERVICE>_<KEY>` |
| **Local dev** | `.env` per repo | `.env` per repo (unchanged) |
| **MCP servers (WSL)** | `.env` in repo dir | `.env` in `~/.config/mcp-hub/` (unchanged) |
| **Rotation** | Manual, requires SSH + edit .env.prod | `sops -e`, git push, deploy |
| **Audit trail** | None | Git history on `secrets.enc.env` |

### 4.2 What Does NOT Change

- pydantic-settings remains the settings framework
- Local development workflow unchanged (`.env` files)
- MCP servers in WSL do NOT need DB access for secrets
- Docker Compose structure unchanged
- No new services to operate (no Vault, no extra DB)

### 4.3 Trade-offs

| Accepted | Rejected Alternative |
|----------|---------------------|
| No live rotation (redeploy needed) | PostgreSQL + LISTEN/NOTIFY (adds DB-SPOF, WSL latency) |
| Shared age key (no per-service isolation) | Per-service encryption keys (complexity for 8 servers) |
| Git-based audit trail | Custom audit_log table (overengineered for current scale) |

### 4.4 Migration Risk

- **Low**: Settings classes gain `secrets_dir` param (additive, non-breaking)
- **Low**: `AliasChoices` allows old + new env var names simultaneously
- **Medium**: Deploy scripts need SOPS decrypt step (testable in staging)
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
- **WSL architecture mismatch** — MCP servers run locally, not on Hetzner;
  persistent DB connection from WSL to remote PostgreSQL is fragile
- **Custom encryption** — Fernet is fine but unnecessary; SOPS/age is
  battle-tested, CNCF-adjacent, requires zero custom code
- **5 days effort** vs. 3 days for hybrid approach

### 5.2 HashiCorp Vault

Overkill for 8 servers. Requires operating a separate cluster. ~50€/month for
managed Vault. Revisit if the platform grows beyond 20 services.

### 5.3 Doppler / Infisical (SaaS)

Data sovereignty concern. Secrets leave our infrastructure. 20-100€/month.
Vendor lock-in.

---

## 6. Open Questions

1. **age key distribution**: How to securely distribute the age private key to
   the Hetzner server? Current answer: SCP once, store at
   `/root/.config/sops/age/keys.txt` with `chmod 600`.

2. **Rotation cadence**: Proposed 90 days for API tokens, annual for
   infrastructure credentials. Needs team agreement.

3. **Phase 6 (Config Store)**: Is runtime-changeable config actually needed, or
   is redeploy sufficient? Decision deferred to when a concrete use case arises.
