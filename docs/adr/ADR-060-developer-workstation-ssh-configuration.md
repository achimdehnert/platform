---
status: "accepted"
date: 2026-02-21
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-021-unified-deployment-pattern.md", "ADR-022-repository-consistency.md"]
---

# ADR-060: Developer Workstation SSH Key Configuration Standard

**Status:** Accepted  
**Date:** 2026-02-21  
**Scope:** All platform repositories, all developer workstations (WSL2/Linux)  
**Supersedes:** —  
**Related:** ADR-021 (Unified Deployment Pattern), ADR-022 (Repository Consistency)

---

## Context

During CI/local development runs the following warning appeared:

```
Warning: Identity file /home/dehnert/.ssh/github_ed25519 not accessible: No such file or directory.
```

Investigation revealed **two separate root causes**:

1. `~/.ssh/config` GitHub block was missing `User git` and `HostName github.com`
2. **Repo-local `core.sshCommand`** in `.git/config` explicitly referenced `github_ed25519`:
   ```
   [core]
       sshCommand = ssh -i /home/dehnert/.ssh/github_ed25519 -o StrictHostKeyChecking=no
   ```
   This overrides the global `~/.ssh/config` entirely and was set when `github_ed25519` was the active key name.

---

## Decision

### 1. Canonical SSH Key Name: `id_ed25519`

```
~/.ssh/id_ed25519        (private key)
~/.ssh/id_ed25519.pub    (public key)
```

`id_ed25519` is the OpenSSH default — picked up automatically without any explicit config.

### 2. Canonical `~/.ssh/config` for GitHub

```sshconfig
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    AddKeysToAgent yes
```

- `User git` — **required**, without it SSH tries `$USER@github.com` which fails
- `HostName github.com` — explicit, avoids DNS/alias ambiguity
- `IdentitiesOnly yes` — prevents SSH from trying other keys
- `AddKeysToAgent yes` — no repeated passphrase prompts

### 3. No `core.sshCommand` in any repo

Repo-local `core.sshCommand` **must not** be set. It overrides the global SSH config and causes stale key references to persist even after `~/.ssh/config` is corrected.

```bash
# Remove from all repos (run once after migration)
for repo in ~/github/*/; do
  val=$(git -C "$repo" config --local core.sshCommand 2>/dev/null)
  if [ -n "$val" ]; then
    echo "Removing core.sshCommand from: $repo"
    git -C "$repo" config --unset core.sshCommand
  fi
done
```

### 4. Git URL Rewrite (global)

```bash
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

### 5. Verification

```bash
ssh -T git@github.com
# Expected: Hi achimdehnert! You've successfully authenticated...

git -C ~/github/travel-beat pull origin main
# Expected: no Warning lines
```

---

## Consequences

### Positive
- No more `Identity file not accessible` warnings
- Consistent setup across all developer machines
- `~/.ssh/config` is the single place for SSH key configuration

### Negative
- Requires one-time cleanup of `core.sshCommand` in existing repos

---

## Migration Checklist

```bash
# 1. Ensure id_ed25519 exists
ls -la ~/.ssh/id_ed25519

# 2. Fix ~/.ssh/config GitHub block
cat ~/.ssh/config | grep -A6 "Host github.com"
# Must contain: HostName, User git, IdentityFile ~/.ssh/id_ed25519

# 3. Remove core.sshCommand from all repos
for repo in ~/github/*/; do
  val=$(git -C "$repo" config --local core.sshCommand 2>/dev/null)
  if [ -n "$val" ]; then
    echo "Removing from: $repo"
    git -C "$repo" config --unset core.sshCommand
  fi
done

# 4. Verify no github_ed25519 references remain
grep -r "github_ed25519" ~/.gitconfig ~/.ssh/config ~/github/*/.git/config 2>/dev/null \
  || echo "clean"

# 5. Test
ssh -T git@github.com
git -C ~/github/travel-beat pull origin main
```

---

## Reference: Complete WSL2 Setup Sequence (new machine)

```bash
# 1. Generate key (skip if id_ed25519 already exists)
ssh-keygen -t ed25519 -C "achim.dehnert@iil.gmbh" -f ~/.ssh/id_ed25519

# 2. Add public key to GitHub
cat ~/.ssh/id_ed25519.pub
# → GitHub → Settings → SSH and GPG keys → New SSH key

# 3. Configure SSH
cat >> ~/.ssh/config << 'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    AddKeysToAgent yes
EOF
chmod 600 ~/.ssh/config

# 4. Git URL rewrite
git config --global url."git@github.com:".insteadOf "https://github.com/"

# 5. Verify
ssh -T git@github.com
```
