---
description: Automatisiertes Frontend UI Test — alle Views auf HTTP 200 + CSRF prüfen (Django writing-hub)
---

# Writing Hub — Automatisierter Frontend UI Test

Vollständiger HTTP-200-Check aller registrierten Project-Views.
Erstellt temporären Test-User + Test-Projekt (idempotent), testet alle URLs + CSRF.

## Voraussetzungen

- Dev-Server muss NICHT laufen (Django Test Client läuft direkt)
- Arbeitsverzeichnis: `${GITHUB_DIR:-$HOME/github}/writing-hub`

---

## Schritt 1: Test-Setup (User + Projekt sicherstellen)

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/writing-hub && python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.projects.models import BookProject, ContentTypeLookup, GenreLookup

U = get_user_model()
user, _ = U.objects.get_or_create(
    username='ui_testuser',
    defaults={'email': 'ui@test.de', 'is_staff': True}
)
user.set_password('uitest123')
user.save()

ct = ContentTypeLookup.objects.first()
genre = GenreLookup.objects.first()
p, created = BookProject.objects.get_or_create(
    title='__UI_TEST_PROJECT__',
    defaults={'owner': user, 'content_type_lookup': ct, 'genre_lookup': genre}
)
print(f'PROJECT_PK={p.pk}')
print(f'CREATED={created}')
"
```

---

## Schritt 2: URL-Reverse-Test (alle registrierten Routes)

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/writing-hub && python manage.py shell -c "
from django.urls import reverse
from apps.projects.models import BookProject

p = BookProject.objects.get(title='__UI_TEST_PROJECT__')
pk = str(p.pk)
dummy_uuid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'

routes = [
    ('projects:detail',             {'pk': pk}),
    ('projects:drama_dashboard',    {'pk': pk}),
    ('projects:health',             {'pk': pk}),
    ('projects:pitch_dashboard',    {'pk': pk}),
    ('projects:analysis',           {'pk': pk}),
    ('projects:budget',             {'pk': pk}),
    ('projects:research_dashboard', {'pk': pk}),
    ('projects:beta_dashboard',     {'pk': pk}),
    ('projects:beta_session',       {'pk': pk, 'session_pk': dummy_uuid}),
    ('projects:lektorat',           {'pk': pk}),
]
errors = []
for name, kwargs in routes:
    try:
        url = reverse(name, kwargs=kwargs)
        print(f'OK   {url}')
    except Exception as e:
        errors.append(f'ERR  {name}: {e}')
        print(f'ERR  {name}: {e}')

print()
print(f'=== {len(routes) - len(errors)}/{len(routes)} URL-Reverses OK ===')
"
```

---

## Schritt 3: HTTP 200 Test — alle Views

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/writing-hub && python manage.py shell -c "
from django.test import Client
from apps.projects.models import BookProject

p = BookProject.objects.get(title='__UI_TEST_PROJECT__')
pk = str(p.pk)

c = Client()
c.login(username='ui_testuser', password='uitest123')

urls = [
    f'/projects/{pk}/',
    f'/projects/{pk}/drama/',
    f'/projects/{pk}/health/',
    f'/projects/{pk}/pitch/',
    f'/projects/{pk}/analysis/',
    f'/projects/{pk}/budget/',
    f'/projects/{pk}/research/',
    f'/projects/{pk}/beta/',
    f'/projects/{pk}/lektorat/',
    f'/projects/{pk}/manuscript/',
]

ok_count = 0
errors = []
for url in urls:
    try:
        r = c.get(url)
        if r.status_code == 200:
            print(f'OK  200  {url}')
            ok_count += 1
        elif r.status_code == 302:
            print(f'OK  302  {url}  -> {r.get(\"Location\",\"\")}')
            ok_count += 1
        else:
            msg = f'ERR {r.status_code}  {url}'
            print(msg)
            errors.append(msg)
    except Exception as e:
        msg = f'EXC       {url}: {e}'
        print(msg)
        errors.append(msg)

print()
print(f'=== {ok_count}/{len(urls)} Views OK ===')
if errors:
    print('FEHLER:')
    for e in errors:
        print(f'  {e}')
else:
    print('Alle Views fehlerfrei.')
"
```

---

## Schritt 3b: CSRF POST-Test (enforce_csrf_checks=True)

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/writing-hub && python manage.py shell -c "
from django.test import Client
from apps.projects.models import BookProject, ResearchNote

p = BookProject.objects.get(title='__UI_TEST_PROJECT__')
pk = str(p.pk)

c = Client(enforce_csrf_checks=True)
c.login(username='ui_testuser', password='uitest123')

r_get = c.get(f'/projects/{pk}/research/')
csrf_token = r_get.cookies.get('csrftoken')
if not csrf_token:
    print('WARN: kein csrftoken Cookie')
else:
    print(f'OK   CSRF-Cookie vorhanden: {str(csrf_token)[:12]}...')

r_bad = c.post(f'/projects/{pk}/research/', {'action': 'add_note', 'title': 'x', 'content': 'x'})
if r_bad.status_code == 403:
    print('OK   POST ohne CSRF -> 403 (korrekt)')
else:
    print(f'WARN POST ohne CSRF -> {r_bad.status_code} (sollte 403 sein!)')

r_ok = c.post(
    f'/projects/{pk}/research/',
    {'action': 'add_note', 'title': 'CSRF-Test', 'content': 'Test',
     'csrfmiddlewaretoken': csrf_token.value},
    HTTP_X_CSRFTOKEN=csrf_token.value,
)
if r_ok.status_code in (200, 302):
    print(f'OK   POST mit CSRF -> {r_ok.status_code} (korrekt)')
    ResearchNote.objects.filter(project=p, title='CSRF-Test').delete()
else:
    print(f'ERR  POST mit CSRF -> {r_ok.status_code}')

print()
print('=== CSRF-Test abgeschlossen ===')
"
```

---

## Schritt 4: Aufräumen (optional)

```bash
cd ${GITHUB_DIR:-$HOME/github}/writing-hub && python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.projects.models import BookProject

BookProject.objects.filter(title='__UI_TEST_PROJECT__').delete()
get_user_model().objects.filter(username='ui_testuser').delete()
print('Test-Daten geloescht.')
"
```

---

## Erweiterung: Neue Views hinzufügen

In Schritt 2 `routes`-Liste und in Schritt 3 `urls`-Liste erweitern.

- `200` = View rendert korrekt
- `302` = Redirect nach POST — OK
- `403/404/500` = Fehler → beheben
