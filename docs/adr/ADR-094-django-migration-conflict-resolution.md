---
status: accepted
date: 2026-03-02
implemented: 2026-03-02
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-056 (Deployment Preflight)
related: ADR-056, ADR-090, ADR-022
implementation_status: implemented
implementation_evidence:
  - "all hubs: migration conflict resolution pattern adopted"
---

# ADR-094: Django Migration Conflict Resolution Pattern

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | **Accepted**                                                         |
| **Scope**      | Platform-wide — alle Django-Repos                                    |
| **Repos**      | bfagent, risk-hub, travel-beat, weltenhub, pptx-hub                  |
| **Erstellt**   | 2026-03-02                                                           |
| **Autor**      | Achim Dehnert                                                        |
| **Amends**     | ADR-056 (Deployment Preflight)                                       |

---

## 1. Context

In der Session vom 2026-03-02 crashte `bfagent_web` beim Container-Start mit:

```text
django.db.migrations.exceptions.NodeNotFoundError:
  Migration writing_hub.0039_outline_category_content_domain
  dependencies reference nonexistent parent node
  ('bfagent', '0073_outline_category_content_domain')
```

**Root Causes:**

1. **Fehlende Stub-Migration:** Eine Migration referenzierte `bfagent.0073_outline_category_content_domain`
   als Dependency, diese Migration existierte aber nicht (anderer Name: `0073_remove_...`).
2. **Mehrfach-Leaf-Nodes:** 4 Migrations mit Nummer `0039_*` in `writing_hub` existierten
   parallel ohne Merge-Migration.
3. **Duplizierte Operationen:** `writing_hub.0039_outline_category_content_domain` enthielt
   `RemoveField`/`DeleteModel`-Operationen die bereits durch andere `0039_*` Migrations
   ausgeführt wurden → `KeyError: ('writing_hub', 'backmatter')`.
4. **Deploy-Tag-Mismatch:** Das Docker-Image wurde mit falschem Tag gebaut
   (`ghcr.io/achimdehnert/bfagent/bfagent-web:latest` statt
   `ghcr.io/achimdehnert/bfagent-web:latest`) — `compose up --force-recreate`
   verwendete daher das alte Image.

---

## 2. Decision

### 2.1 Migration-Konflikt-Prävention (MANDATORY)

**Vor jedem Commit mit neuen Migrations:**

```bash
# Check auf Konflikte
python manage.py migrate --check
python manage.py showmigrations | grep -v "\[X\]" | grep "^\s" | sort

# Bei Konflikten: automatische Merge-Migration erzeugen
python manage.py makemigrations --merge --no-input
```

**Vor jedem Docker-Build:**

```bash
# Im Projekt-Root auf dem Server oder in WSL
python manage.py showmigrations 2>&1 | grep -c "Conflicting" || echo "OK"
```

### 2.2 Stub-Migrations-Pattern

Wenn eine Migration eine Dependency referenziert die nicht existiert
(z.B. nach Umbenennung), MUSS eine leere Stub-Migration erstellt werden:

```python
# apps/{app}/migrations/{nummer}_{original_name}.py
# Stub migration -- created to satisfy {consumer}.{nummer}_{name} dependency.
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('{app}', '{letzte_existierende_migration}'),
    ]
    operations = []
```

Danach **sofort** eine Merge-Migration erstellen die den Stub und den
bisherigen Leaf zusammenführt:

```python
# apps/{app}/migrations/{nummer+1}_merge_{stub}_{leaf}.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('{app}', '{stub_name}'),
        ('{app}', '{original_leaf}'),
    ]
    operations = []
```

### 2.3 Fake-Apply für bereits-ausgeführte Migrations

Wenn eine Migration Operationen auf bereits gelöschte/geänderte Models
enthält (wegen paralleler Branches), MUSS sie entweder:

**Option A — Migration bereinigen (bevorzugt):**
Operations die bereits durch andere Migrations ausgeführt wurden entfernen.
Die Migration wird auf eine leere `operations = []` reduziert.

**Option B — Fake-Apply via psql (Notfall-Prod):**

```sql
INSERT INTO django_migrations (app, name, applied)
VALUES ('{app}', '{name}', NOW())
ON CONFLICT DO NOTHING;
```

Option B ist NUR für Prod-Notfälle zulässig. Die Migration muss danach
bereinigt (Option A) und committed werden.

### 2.4 Docker-Image-Tag-Matching (CRITICAL)

Das Image-Tag im Build-Befehl MUSS exakt mit dem `image:`-Feld in
`docker-compose.prod.yml` übereinstimmen:

```bash
# SCHRITT 1: Tag aus compose-File lesen
IMAGE=$(grep "image:" docker-compose.prod.yml | grep "web" | awk '{print $2}' | sed 's/${IMAGE_TAG:-latest}/latest/')
echo "Image: $IMAGE"

# SCHRITT 2: Mit exakt diesem Tag bauen
docker build -t "$IMAGE" .

# SCHRITT 3: Force-recreate mit stop/rm (nicht nur --force-recreate!)
docker stop {container} && docker rm {container}
docker compose -f docker-compose.prod.yml up -d {service}

# SCHRITT 4: Image-ID verifizieren
RUNNING=$(docker inspect {container} --format '{{.Image}}')
BUILT=$(docker images "$IMAGE" --format '{{.ID}}')
[ "$RUNNING" = "sha256:${BUILT}" ] && echo "OK" || echo "MISMATCH!"
```

**BANNED Pattern:**

```bash
# FALSCH: Anderer Tag als in compose-File
docker build -t ghcr.io/achimdehnert/bfagent/bfagent-web:latest .
# wenn compose-File hat: image: ghcr.io/achimdehnert/bfagent-web:latest

# FALSCH: force-recreate ohne stop/rm zieht altes Image
docker compose up -d --force-recreate  # nutzt gecachtes Image
```

---

## 3. Pre-Deploy Checklist (MANDATORY)

Vor jedem `docker build` auf dem Server:

```bash
# 1. Migration-Konflikte prüfen
cd /opt/{app}-app
docker run --rm --env-file .env.prod {image} \
  python manage.py migrate --check 2>&1 | grep -E "Conflict|Error|OK"

# 2. Image-Tag aus compose-File extrahieren und bauen
IMAGE=$(grep "image:" docker-compose.prod.yml | grep "web" | awk '{print $2}')
IMAGE=${IMAGE/\$\{IMAGE_TAG:-latest\}/latest}
docker build -t "$IMAGE" .

# 3. Deploy
docker stop {container} && docker rm {container}
docker compose -f docker-compose.prod.yml up -d {service}

# 4. Health-Check
sleep 20
docker inspect {container} --format '{{.State.Health.Status}}'
```

---

## 4. Windsurf-Integration

Diese Regeln sind in `platform/windsurf-rules/docker-deployment.md`
und `platform/windsurf-rules/django-models-views.md` als BANNED-Patterns
eingetragen. Cascade prüft sie automatisch via `check_violations`.

---

## 5. Lessons Learned (2026-03-02)

| Problem | Root Cause | Fix | Praevention |
|---------|------------|-----|-------------|
| `NodeNotFoundError` | Migration mit falschem Dependency-Name | Stub-Migration erstellen | `migrate --check` vor Build |
| Multiple Leaf-Nodes | Parallele Branches ohne Merge-Migration | `makemigrations --merge` | Pre-commit hook |
| `KeyError: backmatter` | Duplizierte Ops in parallel entstandener Migration | Operations leeren | Branch-Merge-Policy |
| Altes Image trotz Rebuild | Tag-Mismatch + `force-recreate` reicht nicht | `stop/rm` + `up` | Tag aus compose lesen |
| Container crasht im Restart-Loop | Migration-Fehler blockiert `manage.py migrate` | Fake-Apply via psql | Pre-flight Migration-Check |
