# 🚀 SQLite → PostgreSQL Migration

## 📋 Übersicht

Dieses Dokument beschreibt die Migration von SQLite (Development) zu PostgreSQL (Production) auf dem Hetzner VPS.

## ✅ Vorteile dieses Ansatzes

- **Keine Migration-Konflikte**: Umgeht alle circular dependency Probleme
- **Sauberer Start**: Frische PostgreSQL Datenbank mit korrekten Migrationen
- **Einfach**: Ein Script macht alles

## 📦 Dateien

### Auf deinem PC erstellt:
- `deployment/scripts/migrate-to-postgres.sh` - Komplettes Migration-Script
- `deployment/MIGRATION_README.md` - Diese Anleitung
- `deployment/initial_data.json` - (Optional) Daten-Export aus SQLite

## 🔧 Anleitung
.\.venv\scripts\activate
Leite Naming-Regeln für Code ab (Packages, Klassen, Methoden, Variablen, Tests). Liefere klare Muster + Beispiele. Ziel: maximale Lesbarkeit für Citizen-Developer.
### Option 1: Fresh Start (EMPFOHLEN)

**Wenn du OHNE existierende Daten starten willst:**

```bash
# 1. Upload mit WinSCP:
# - deployment/scripts/migrate-to-postgres.sh → /opt/bfagent/deployment/scripts/

# 2. Auf dem Server:
ssh root@88.198.191.108

cd /opt/bfagent/deployment
chmod +x scripts/migrate-to-postgres.sh
./scripts/migrate-to-postgres.sh
```

**Das war's!** 🎉

### Option 2: Mit Daten-Import

**Wenn du existierende Daten migrieren willst:**

#### Schritt 1: Auf deinem PC (Windows)

```powershell
# Aktiviere venv
cd C:\Users\achim\github\bfagent
.venv\Scripts\activate

# Exportiere nur User-Daten (sicher)
python manage.py dumpdata auth.user --natural-foreign --indent 2 > deployment/initial_data.json

# ODER: Exportiere alles (riskanter, aber vollständiger)
# python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude sessions.session --indent 2 > deployment/initial_data.json
```

#### Schritt 2: Upload & Deploy

```bash
# 1. Upload mit WinSCP:
# - deployment/scripts/migrate-to-postgres.sh → /opt/bfagent/deployment/scripts/
# - deployment/initial_data.json → /opt/bfagent/deployment/

# 2. Auf dem Server:
ssh root@88.198.191.108

cd /opt/bfagent/deployment
chmod +x scripts/migrate-to-postgres.sh
./scripts/migrate-to-postgres.sh
```

## 🎯 Was das Script macht

1. **Stop** - Stoppt alle Container
2. **Clean** - Löscht alte Volumes (PostgreSQL, Redis, Static, Media)
3. **Rebuild** - Baut Web-Image neu (mit aktuellem Code)
4. **Start DB** - Startet PostgreSQL & Redis
5. **Migrate** - Führt alle Django Migrationen aus (erstellt Tabellen)
6. **Superuser** - Erstellt admin User (admin/admin123)
7. **Load Data** - Lädt initial_data.json (wenn vorhanden)
8. **Start All** - Startet alle Services (Web, Celery, Nginx)
9. **Check** - Testet Health-Endpoints

## ✅ Erfolgs-Kriterien

Nach dem Script solltest du sehen:

```
✅ MIGRATION COMPLETE!

Login credentials:
  URL:      http://88.198.191.108/admin/
  Username: admin
  Password: admin123
```

### Testen:

```bash
# Container Status
docker-compose --env-file .env.production ps
# Alle sollten "Up (healthy)" sein

# Test Homepage
curl http://88.198.191.108/
# Sollte HTML zurückgeben (kein 502)

# Test Admin
curl -I http://88.198.191.108/admin/
# Sollte 302 redirect zurückgeben
```

## 🔍 Troubleshooting

### Container crasht weiter?

```bash
# Logs anschauen
docker-compose --env-file .env.production logs --tail=100 web

# Manuell testen
docker-compose --env-file .env.production run --rm web python manage.py check
```

### Migration schlägt fehl?

```bash
# Fake migrations (nur wenn nötig!)
docker-compose --env-file .env.production run --rm web python manage.py migrate --fake-initial

# Oder: Komplett neu
cd /opt/bfagent/deployment
docker-compose --env-file .env.production down -v
./scripts/migrate-to-postgres.sh
```

### Daten-Import schlägt fehl?

```bash
# Lade nur User-Daten:
docker-compose --env-file .env.production run --rm web python manage.py loaddata /app/deployment/initial_data.json --exclude sessions --exclude contenttypes

# Oder: Manuell Superuser erstellen
docker-compose --env-file .env.production run --rm web python manage.py createsuperuser
```

## 🔒 Security

Nach erfolgreicher Migration:

1. **Admin-Passwort ändern:**
   ```bash
   docker-compose --env-file .env.production run --rm web python manage.py changepassword admin
   ```

2. **SECRET_KEY ändern** in `.env.production`

3. **SSL einrichten** (Let's Encrypt)

## 📝 Nächste Schritte

1. ✅ Migration ausführen
2. ✅ Login testen (http://88.198.191.108/admin/)
3. ✅ Admin-Passwort ändern
4. 🔐 SSL mit Certbot einrichten
5. 🎨 Custom Daten importieren (falls nötig)

## 🆘 Support

Bei Problemen:
1. Logs checken: `docker-compose --env-file .env.production logs`
2. Container status: `docker-compose --env-file .env.production ps`
3. Django check: `docker-compose --env-file .env.production run --rm web python manage.py check`
