# @database-migration-strategy.md - Sichere SQLite zu Django Migration

## 🛡️ Risikominimierung bei Datenbank-Migrationen

### Grundprinzipien der sicheren Migration

#### 1. **Nie ohne Backup arbeiten**
```bash
# Automatisiertes Backup-System
#!/bin/bash
# create_backup.sh
DB_FILE="db.sqlite3"
BACKUP_DIR="db_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sqlite3"

# Backup-Verzeichnis erstellen
mkdir -p $BACKUP_DIR

# Datenbank kopieren (während sie läuft)
sqlite3 $DB_FILE ".backup $BACKUP_FILE"

# Integrität prüfen
sqlite3 $BACKUP_FILE "PRAGMA integrity_check;" | grep -q "ok"
if [ $? -eq 0 ]; then
    echo "✅ Backup erfolgreich: $BACKUP_FILE"
    echo $BACKUP_FILE > $BACKUP_DIR/latest_backup.txt
else
    echo "❌ Backup fehlgeschlagen!"
    exit 1
fi
```

#### 2. **Read-Only First Ansatz**
```python
# Schritt 1: Alle Models mit managed=False
class ExistingTable(models.Model):
    field1 = models.CharField(max_length=100)
    field2 = models.IntegerField()

    class Meta:
        managed = False  # Django verwaltet Tabelle NICHT
        db_table = 'existing_table'  # Exakter Tabellenname

# Schritt 2: Fake-Initial Migration
# python manage.py makemigrations --empty your_app
# python manage.py migrate --fake-initial
```

#### 3. **Schrittweise Aktivierung**
```python
# Phase 1: Nur Lesen (managed=False)
# Phase 2: Neue Felder hinzufügen (managed=True, nur neue Felder)
# Phase 3: Bestehende Felder modifizieren (nach Tests)

# Beispiel für sichere Feld-Erweiterung:
class ExistingTable(models.Model):
    # Bestehende Felder (nicht ändern)
    old_field = models.CharField(max_length=100)

    # Neue Felder (sicher hinzufügbar)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    # Django 5.2 Features (nach Validierung)
    calculated_field = models.GeneratedField(
        expression=F("old_field") + Value(" - processed"),
        output_field=models.CharField(max_length=150),
        db_persist=False  # Erst mal nicht persistent
    )

    class Meta:
        managed = True  # Nur nach erfolgreichen Tests
        db_table = 'existing_table'
```

### Migration-Validierung in Echtzeit

#### Datenintegrität prüfen
```python
# management/commands/validate_data_integrity.py
from django.core.management.base import BaseCommand
from django.db import connection
import sqlite3

class Command(BaseCommand):
    help = 'Validiert Datenintegrität vor und nach Migrationen'

    def add_arguments(self, parser):
        parser.add_argument('--backup-file', type=str, help='Backup-Datei zum Vergleich')

    def handle(self, *args, **options):
        backup_file = options.get('backup_file')

        # 1. SQLite Integrität prüfen
        self.check_sqlite_integrity()

        # 2. Tabellen-Schema vergleichen
        if backup_file:
            self.compare_schemas(backup_file)

        # 3. Daten-Konsistenz prüfen
        self.check_data_consistency(backup_file)

        # 4. Django Model-Validierung
        self.validate_django_models()

    def check_sqlite_integrity(self):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

        if result[0] == 'ok':
            self.stdout.write(self.style.SUCCESS('✅ SQLite Integrität: OK'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ SQLite Integrität: {result[0]}'))
            raise Exception('Database integrity check failed')

    def compare_schemas(self, backup_file):
        # Aktuelles Schema
        with connection.cursor() as cursor:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
            current_schema = {row[0] for row in cursor.fetchall() if row[0]}

        # Backup Schema
        backup_conn = sqlite3.connect(backup_file)
        backup_cursor = backup_conn.cursor()
        backup_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        backup_schema = {row[0] for row in backup_cursor.fetchall() if row[0]}
        backup_conn.close()

        # Unterschiede finden
        added_tables = current_schema - backup_schema
        removed_tables = backup_schema - current_schema

        if added_tables:
            self.stdout.write(self.style.WARNING(f'➕ Neue Tabellen: {len(added_tables)}'))
        if removed_tables:
            self.stdout.write(self.style.ERROR(f'➖ Entfernte Tabellen: {len(removed_tables)}'))

        self.stdout.write(self.style.SUCCESS('✅ Schema-Vergleich abgeschlossen'))

    def check_data_consistency(self, backup_file):
        if not backup_file:
            return

        # Beispiel: Anzahl Datensätze vergleichen
        from your_app.models import ExistingTable

        current_count = ExistingTable.objects.count()

        # Backup-Datenbank abfragen
        backup_conn = sqlite3.connect(backup_file)
        backup_cursor = backup_conn.cursor()
        backup_cursor.execute(f"SELECT COUNT(*) FROM {ExistingTable._meta.db_table}")
        backup_count = backup_cursor.fetchone()[0]
        backup_conn.close()

        if current_count == backup_count:
            self.stdout.write(self.style.SUCCESS(f'✅ Datensatz-Anzahl konsistent: {current_count}'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Datensatz-Anzahl unterschiedlich: {current_count} vs {backup_count}'))

    def validate_django_models(self):
        from django.core.management import call_command
        from io import StringIO

        # Django Model-Validierung
        output = StringIO()
        try:
            call_command('check', '--database', 'default', stdout=output)
            self.stdout.write(self.style.SUCCESS('✅ Django Models: Validierung erfolgreich'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Django Models: {e}'))
```

### Automatisierte Rollback-Mechanismen

#### Smart Rollback System
```python
# management/commands/smart_rollback.py
from django.core.management.base import BaseCommand
from django.db import connection
import os
import shutil
import sqlite3

class Command(BaseCommand):
    help = 'Intelligenter Rollback mit Validierung'

    def add_arguments(self, parser):
        parser.add_argument('--backup-file', type=str, required=True)
        parser.add_argument('--force', action='store_true', help='Rollback ohne Bestätigung')

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        force = options['force']

        if not os.path.exists(backup_file):
            self.stdout.write(self.style.ERROR(f'❌ Backup-Datei nicht gefunden: {backup_file}'))
            return

        # 1. Backup validieren
        if not self.validate_backup(backup_file):
            return

        # 2. Bestätigung (außer --force)
        if not force:
            confirm = input('Rollback durchführen? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Rollback abgebrochen.')
                return

        # 3. Aktuellen Zustand sichern
        emergency_backup = self.create_emergency_backup()

        # 4. Rollback durchführen
        try:
            self.perform_rollback(backup_file)
            self.stdout.write(self.style.SUCCESS('✅ Rollback erfolgreich'))

            # 5. Validierung nach Rollback
            self.validate_after_rollback()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Rollback fehlgeschlagen: {e}'))
            # Notfall-Wiederherstellung
            self.perform_rollback(emergency_backup)

    def validate_backup(self, backup_file):
        try:
            conn = sqlite3.connect(backup_file)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            if result[0] == 'ok':
                self.stdout.write(self.style.SUCCESS('✅ Backup-Datei ist gültig'))
                return True
            else:
                self.stdout.write(self.style.ERROR(f'❌ Backup-Datei beschädigt: {result[0]}'))
                return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Backup-Validierung fehlgeschlagen: {e}'))
            return False

    def create_emergency_backup(self):
        emergency_file = f"emergency_backup_{int(time.time())}.sqlite3"
        shutil.copy2('db.sqlite3', emergency_file)
        self.stdout.write(f'🚨 Notfall-Backup erstellt: {emergency_file}')
        return emergency_file

    def perform_rollback(self, backup_file):
        # Django-Verbindungen schließen
        connection.close()

        # Datei ersetzen
        shutil.copy2(backup_file, 'db.sqlite3')

        # Verbindung neu aufbauen
        connection.connect()

    def validate_after_rollback(self):
        from django.core.management import call_command
        call_command('validate_data_integrity')
```

### Kontinuierliche Überwachung

#### Migration-Monitor
```python
# monitoring/migration_monitor.py
import logging
import time
from django.db import connection
from django.core.management.base import BaseCommand

class MigrationMonitor:
    def __init__(self):
        self.logger = logging.getLogger('migration_monitor')

    def monitor_migration(self, migration_func):
        """Überwacht eine Migration in Echtzeit"""

        # Vor-Migration Status
        pre_stats = self.get_database_stats()
        start_time = time.time()

        try:
            # Migration ausführen
            result = migration_func()

            # Nach-Migration Status
            post_stats = self.get_database_stats()
            duration = time.time() - start_time

            # Analyse
            self.analyze_migration_impact(pre_stats, post_stats, duration)

            return result

        except Exception as e:
            self.logger.error(f"Migration fehlgeschlagen: {e}")
            # Automatischer Rollback-Trigger
            self.trigger_emergency_rollback()
            raise

    def get_database_stats(self):
        with connection.cursor() as cursor:
            # Tabellen-Anzahl
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            # Datenbank-Größe
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size = page_count * page_size

            return {
                'table_count': table_count,
                'db_size': db_size,
                'timestamp': time.time()
            }

    def analyze_migration_impact(self, pre_stats, post_stats, duration):
        table_diff = post_stats['table_count'] - pre_stats['table_count']
        size_diff = post_stats['db_size'] - pre_stats['db_size']

        self.logger.info(f"Migration abgeschlossen in {duration:.2f}s")
        self.logger.info(f"Tabellen: {pre_stats['table_count']} → {post_stats['table_count']} ({table_diff:+d})")
        self.logger.info(f"Größe: {pre_stats['db_size']} → {post_stats['db_size']} ({size_diff:+d} Bytes)")

        # Warnung bei großen Änderungen
        if abs(table_diff) > 5:
            self.logger.warning(f"Große Anzahl Tabellen-Änderungen: {table_diff}")

        if abs(size_diff) > 10 * 1024 * 1024:  # 10MB
            self.logger.warning(f"Große Datenbank-Größenänderung: {size_diff} Bytes")
```

## 🎯 Zusammenfassung der Sicherheitsstrategie

### Kernprinzipien
1. **Immer Backup vor Änderungen**
2. **managed=False für bestehende Tabellen**
3. **Schrittweise Aktivierung neuer Features**
4. **Kontinuierliche Validierung**
5. **Automatische Rollback-Mechanismen**

### Checkpoint-System
- **Pre-Migration**: Backup + Validierung
- **During-Migration**: Monitoring + Logging
- **Post-Migration**: Integrität + Funktionalität
- **Emergency**: Automatischer Rollback

Diese Strategie gewährleistet, dass Ihre bestehenden Daten während der gesamten Django-Migration sicher bleiben und jederzeit ein Rollback möglich ist.
