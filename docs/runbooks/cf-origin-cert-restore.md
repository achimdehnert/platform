# Runbook: CF Origin Cert Restore (`*.iil.pet`)

**Scope**: Wiederherstellung von `/etc/nginx/ssl/cf-origin/iil-pet.{crt,key}` auf prod nach Disk-Loss, Server-Migration oder versehentlicher Löschung. Bezieht sich auf ADR-205 Konfig A (23 `*.iil.pet` Vhosts).

**Wer kann das ausführen**: root auf prod **plus** Zugriff auf den Backup-Passphrase **plus** (im Worst Case) Zugriff auf den Cloudflare-Account `iil.pet`.

## Symptome (wann dieses Runbook?)

- `nginx -t` meldet "cannot load certificate /etc/nginx/ssl/cf-origin/iil-pet.crt: No such file"
- Alle `*.iil.pet` Vhosts liefern 502 / TLS-Handshake-Error
- Cloudflare zeigt "522 / 525" Errors für betroffene Subdomains
- Disk-Recovery nach Hetzner-Hardware-Failure

## Path 1: Restore aus tägl. Backup (Normalfall)

Backups liegen unter `/root/backups/cf-origin/cf-origin-YYYYMMDD.tar.gz.gpg` (täglich, 30 Tage Retention, GPG-symmetric).

```bash
# 1. Passphrase aus Passwort-Manager holen → temp file (NICHT git, NICHT logs)
cat > /root/.secrets/backup-passphrase  # paste, Ctrl-D
chmod 600 /root/.secrets/backup-passphrase

# 2. Latest backup wählen
LATEST=$(ls -t /root/backups/cf-origin/cf-origin-*.tar.gz.gpg | head -1)
echo "Restoring from $LATEST"

# 3. Decrypt + extract (zur Sicherheit erst in /tmp)
gpg --batch --passphrase-file /root/.secrets/backup-passphrase --decrypt "$LATEST" \
  | tar -xz -C /tmp

# 4. Verify content before deploying
ls -la /tmp/cf-origin/
openssl x509 -in /tmp/cf-origin/iil-pet.crt -noout -subject -dates -issuer
# expected: subject CN=*.iil.pet, issuer Cloudflare Origin CA

# 5. Deploy
mkdir -p /etc/nginx/ssl/cf-origin
cp -v /tmp/cf-origin/* /etc/nginx/ssl/cf-origin/
chmod 644 /etc/nginx/ssl/cf-origin/*.crt
chmod 600 /etc/nginx/ssl/cf-origin/*.key

# 6. Reload nginx
nginx -t && systemctl reload nginx

# 7. Cleanup
rm -rf /tmp/cf-origin

# 8. Verify a vhost
curl -sI https://devhub.iil.pet/ | head -3
```

**Erfolg**: alle `*.iil.pet` Vhosts antworten wieder HTTP 200/302/etc. (kein TLS-Error).

## Path 2: Re-Issue über Cloudflare Dashboard (Backup verloren)

Wenn weder Backup noch Passphrase verfügbar:

1. Login → `dash.cloudflare.com` → Zone **iil.pet**
2. Sidebar: **SSL/TLS → Origin Server**
3. Bestehender Cert "expired/lost" — entscheiden:
   - Wenn alter noch in der Liste: **Download** (gibt nur Cert, NICHT Key — der Key existiert nur einmal beim Issue)
   - Wenn Key weg: **muss neuer Cert** ausgestellt werden (alten in CF Dashboard löschen)
4. **Create Certificate**:
   - Hostnames: `iil.pet`, `*.iil.pet`
   - Validität: 15 Jahre (Default)
   - Private Key Type: ECDSA (gemäß aktueller Konvention)
5. Cloudflare zeigt einmalig:
   - **Origin Certificate** (PEM block)
   - **Private Key** (PEM block) — **wird nicht erneut anzeigbar**
6. Speichern auf prod:
   ```bash
   mkdir -p /etc/nginx/ssl/cf-origin
   # Paste cert
   cat > /etc/nginx/ssl/cf-origin/iil-pet.crt  # paste, Ctrl-D
   # Paste key
   cat > /etc/nginx/ssl/cf-origin/iil-pet.key  # paste, Ctrl-D
   chmod 644 /etc/nginx/ssl/cf-origin/iil-pet.crt
   chmod 600 /etc/nginx/ssl/cf-origin/iil-pet.key
   ```
7. `nginx -t && systemctl reload nginx`
8. **Sofort Backup-Script laufen lassen** damit der neue Key gesichert ist:
   ```bash
   /opt/scripts/cf-origin-key-backup.sh
   ```

## Post-Restore Checks

- [ ] `nginx -t` ohne Errors
- [ ] `systemctl status nginx` running
- [ ] Spot-check 3 Vhosts via curl (`devhub.iil.pet`, `writing.iil.pet`, `learn.iil.pet`)
- [ ] `/opt/scripts/cert-expiry-check.sh` zeigt CF-Origin/iil-pet OK
- [ ] CF Dashboard: alle Subdomains nicht mehr 522/525
- [ ] Backup wurde aktualisiert (`ls -t /root/backups/cf-origin/ | head -1` = heute)

## Häufige Fallstricke

- **Key falsch chmod**: nginx-Error "PEM_read_bio failed" wenn permissions zu lax sind. `chmod 600` für `.key`.
- **Alter Cert in Vhost-Configs gepfaded**: `grep -r "ssl_certificate" /etc/nginx/sites-enabled/ | grep cf-origin` — sollten alle auf `iil-pet.crt`/`iil-pet.key` zeigen.
- **CF Origin CA Issuer-Chain**: nginx warnt "ssl_stapling ignored, issuer certificate not found" — das ist OK (CF Origin Certs haben keine OCSP-URL und brauchen keine Chain).

## Related

- ADR-205 (cert strategy, DR-section)
- `/opt/scripts/cf-origin-key-backup.sh` (Backup-Script)
- `/opt/scripts/cert-expiry-check.sh` (Health-Monitoring)
