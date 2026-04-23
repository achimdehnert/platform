---
description: Pre-Release Frontend Test — alle Views, Templates, URLs, DNS und Health prüfen bevor eine Website zum Testen freigegeben wird
---

# Pre-Release Frontend Test

**PFLICHT vor jeder Freigabe einer Website zum Testen.**
Prüft Views, Templates, URLs, DNS, Health — repo-agnostisch für alle Django-Hub-Repos.

## Wann verwenden?

- User sagt "ich möchte das Frontend testen"
- Vor jedem Deploy der zum Testen freigegeben wird
- Nach größeren Migrations oder Template-Änderungen

## Voraussetzungen

- Repo-Pfad bekannt (z.B. `${GITHUB_DIR:-$HOME/github}/trading-hub`)
- Production-URL bekannt (z.B. `https://trading-hub.iil.pet`)
- `mcp5_get_project_facts` für repo-spezifische Infos aufrufen

---

## Phase 1: Statische Code-Analyse (kein Server nötig)

### 1.1 Alle Views → Templates Mapping prüfen

Suche alle Views mit `template_name` oder `render()`:

```bash
grep -rn "template_name\|render(" <REPO>/src/ --include="*.py" | grep -v __pycache__ | grep -v ".pyc"
```

Für jedes gefundene Template prüfen ob die Datei existiert:

```bash
# Alle referenzierten Templates extrahieren und prüfen
grep -rhoP "template_name\s*=\s*['\"]([^'\"]+)['\"]" <REPO>/src/ --include="*.py" | sort -u | while read tpl; do
  tpl=$(echo "$tpl" | grep -oP "['\"]([^'\"]+)['\"]" | tr -d "'\"")
  if [ -f "<REPO>/src/templates/$tpl" ] || [ -f "<REPO>/templates/$tpl" ]; then
    echo "OK   $tpl"
  else
    echo "MISS $tpl"
  fi
done
```

**Gate: Alle Templates müssen existieren. MISS = blockiert Release.**

### 1.2 URL-Patterns Konsistenz

```bash
grep -rn "path(" <REPO>/src/ --include="urls.py" | grep -v __pycache__
```

Prüfe:
- Kein `path()` ohne zugehörige View
- Keine doppelten URL-Patterns
- Alle `namespace=` korrekt referenziert

### 1.3 Import-Check

```bash
cd <REPO> && python -c "
import django; django.setup()
from django.urls import reverse, get_resolver
resolver = get_resolver()
all_patterns = []
def collect(resolver, prefix=''):
    for p in resolver.url_patterns:
        if hasattr(p, 'url_patterns'):
            collect(p, prefix + str(p.pattern))
        else:
            all_patterns.append(prefix + str(p.pattern))
collect(resolver)
print(f'Total URL patterns: {len(all_patterns)}')
for u in sorted(all_patterns):
    print(f'  {u}')
"
```

**Gate: Import darf nicht fehlschlagen. ImportError/SyntaxError = blockiert Release.**

---

## Phase 2: Django Test Client (lokaler Test, kein Deploy nötig)

### 2.1 Automatischer View-Test

Führe im Container oder lokal aus:

```python
# Dieses Script testet ALLE registrierten URL-Patterns auf HTTP 200/302
import django; django.setup()
from django.test import Client, RequestFactory
from django.urls import get_resolver
from django.contrib.auth import get_user_model

User = get_user_model()

# Test-User erstellen
user, _ = User.objects.get_or_create(
    username='__pre_release_test__',
    defaults={'email': 'test@test.de', 'is_staff': True, 'is_superuser': True}
)
user.set_password('test123')
user.save()

c = Client()
c.login(username='__pre_release_test__', password='test123')

# Alle URL-Patterns sammeln
resolver = get_resolver()
results = {'ok': [], 'redirect': [], 'error': [], 'skip': []}

def test_url(url):
    try:
        r = c.get(url, follow=False)
        if r.status_code == 200:
            results['ok'].append(url)
            return f'OK   200  {url}'
        elif r.status_code in (301, 302):
            results['redirect'].append(url)
            return f'OK   {r.status_code}  {url} -> {r.get("Location","")}'
        else:
            results['error'].append((url, r.status_code))
            return f'ERR  {r.status_code}  {url}'
    except Exception as e:
        results['error'].append((url, str(e)))
        return f'EXC  {url}: {e}'

# Test statische URLs (ohne Parameter)
static_urls = ['/livez/', '/healthz/', '/admin/login/', '/accounts/login/']
for url in static_urls:
    print(test_url(url))

# Zusammenfassung
total = len(results['ok']) + len(results['redirect']) + len(results['error'])
print(f'\n=== {len(results["ok"])}/{total} OK, {len(results["redirect"])} Redirects, {len(results["error"])} Errors ===')
if results['error']:
    print('FEHLER:')
    for url, code in results['error']:
        print(f'  {code}  {url}')

# Cleanup
User.objects.filter(username='__pre_release_test__').delete()
```

**Gate: 0 Errors bei statischen URLs. Errors bei parametrisierten URLs einzeln prüfen.**

---

## Phase 3: DNS + SSL Verification

### 3.1 DNS-Record prüfen

```bash
# Cloudflare DNS Check
curl -s -H "Authorization: Bearer $(cat ~/.secrets/cloudflare_write_token)" \
  "https://api.cloudflare.com/client/v4/zones/94737a5dbcb949de48bbbbd9fcc9910f/dns_records?name=<SUBDOMAIN>.iil.pet" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Records: {len(d[\"result\"])}'); [print(f'  {r[\"type\"]} {r[\"name\"]} -> {r[\"content\"]}') for r in d['result']]"
```

Falls kein Record vorhanden → erstellen:

```bash
curl -s -X POST -H "Authorization: Bearer $(cat ~/.secrets/cloudflare_write_token)" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/94737a5dbcb949de48bbbbd9fcc9910f/dns_records" \
  -d '{"type":"A","name":"<SUBDOMAIN>","content":"88.198.191.108","proxied":true,"ttl":1}'
```

### 3.2 Nginx-Config prüfen

```bash
# Via SSH oder MCP
ssh root@88.198.191.108 "ls /etc/nginx/sites-enabled/<DOMAIN>.conf && nginx -t"
```

**Gate: DNS-Record muss existieren + Nginx config muss valid sein.**

---

## Phase 4: Production Health Check (nach Deploy)

### 4.1 Health Endpoints

```bash
curl -sf --max-time 10 https://<DOMAIN>/livez/ && echo " OK" || echo " FAIL"
curl -sf --max-time 10 https://<DOMAIN>/healthz/ || echo "FAIL"
```

### 4.2 Frontend Smoke Test

```bash
# Hauptseite muss HTTP 200 oder 302 (Login-Redirect) zurückgeben
HTTP=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "https://<DOMAIN>/")
if [ "$HTTP" = "200" ] || [ "$HTTP" = "302" ]; then
  echo "OK  Homepage: HTTP $HTTP"
else
  echo "FAIL  Homepage: HTTP $HTTP"
fi

# Login-Seite
HTTP=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "https://<DOMAIN>/accounts/login/")
echo "Login: HTTP $HTTP"

# Static Files
HTTP=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "https://<DOMAIN>/static/css/style.css" 2>/dev/null || echo "000")
echo "Static: HTTP $HTTP"
```

### 4.3 Container Health

```bash
# Docker Container Status
ssh root@88.198.191.108 "cd /opt/<APP_PATH> && docker compose -f docker-compose.prod.yml ps --format 'table {{.Name}}\t{{.Status}}'"
```

**Gate: /livez/ = 200, /healthz/ = 200, Homepage = 200|302, alle Container healthy.**

---

## Checkliste (Zusammenfassung)

| # | Check | Gate | Blockiert Release? |
|---|-------|------|--------------------|
| 1 | Alle Templates existieren | 0 MISS | JA |
| 2 | Kein ImportError/SyntaxError | 0 Errors | JA |
| 3 | URL-Patterns konsistent | 0 doppelte | JA |
| 4 | Static URLs HTTP 200/302 | 0 Errors | JA |
| 5 | DNS-Record vorhanden | Record exists | JA |
| 6 | Nginx config valid | nginx -t OK | JA |
| 7 | /livez/ = 200 | HTTP 200 | JA |
| 8 | /healthz/ = 200 | HTTP 200 | JA |
| 9 | Homepage erreichbar | HTTP 200/302 | JA |
| 10 | Container healthy | Alle running | JA |

**Alle 10 Checks müssen bestanden sein bevor der User den Test-Link bekommt.**
