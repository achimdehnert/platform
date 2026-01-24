# WSL Passwort zurücksetzen

## Schnelle Lösung (PowerShell als Administrator):

```powershell
# 1. Exit WSL
exit

# 2. In PowerShell (NICHT WSL):
wsl -u root

# 3. Jetzt bist du root in WSL, setze neues Passwort:
passwd dehnert

# 4. Gib neues Passwort ein (2x zur Bestätigung)

# 5. Exit und zurück zu normalem User:
exit
wsl
```

## Alternative: Redis ohne sudo

Statt Redis system-wide zu installieren, nutze **Docker** oder **Memurai** (Windows-nativ):

### Option A: Memurai (Empfohlen für Windows)
```powershell
# Download: https://www.memurai.com/get-memurai
# Installiert Redis-kompatiblen Server für Windows
# Läuft als Windows Service, kein WSL nötig!
```

### Option B: Docker Desktop
```powershell
docker run -d -p 6379:6379 redis:alpine
```

### Option C: Redis im User Space (ohne sudo)
```bash
# In WSL als normaler User:
cd ~
wget http://download.redis.io/redis-stable.tar.gz
tar xvzf redis-stable.tar.gz
cd redis-stable
make
src/redis-server &  # Startet im Hintergrund
```

## Schnelltest ohne Redis/Celery

Alternativ: MVP erst mal **OHNE** Celery testen (synchron):

```python
# In Django View direkt aufrufen (für Testing)
# Später dann mit Celery async machen
```
