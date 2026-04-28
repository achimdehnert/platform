#!/usr/bin/env python3
"""gen_django_app.py — Neue Django-App mit ADR-konforme Boilerplate generieren.

Generiert eine vollständige App-Struktur (ADR-009 Service Layer):
  apps/{name}/models.py, views.py, services.py, urls.py, apps.py, admin.py
  apps/{name}/migrations/__init__.py
  tests/test_{name}_services.py
  tests/test_{name}_views.py

Verwendung:
    python3 scripts/gen_django_app.py <repo> <app_name>
    python3 scripts/gen_django_app.py <repo> <app_name> --dry-run
    python3 scripts/gen_django_app.py <repo> <app_name> --entity=Trip

SSoT: ADR-009 (Service Layer), ADR-048 (HTMX), ADR-057 (test_should_*)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PLATFORM_ROOT = Path(__file__).parent.parent


# ── Templates ─────────────────────────────────────────────────────────────────

def _apps_py(app_name: str, entity: str) -> str:
    return f'''\
from django.apps import AppConfig


class {entity}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.{app_name}"
    verbose_name = "{entity}"
'''


def _models_py(app_name: str, entity: str) -> str:
    return f'''\
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class {entity}(models.Model):
    """TODO: {entity}-Domain-Model."""

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="{app_name}s",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{entity}(id={{self.pk}})"
'''


def _services_py(app_name: str, entity: str) -> str:
    return f'''\
"""services.py — Business Logic für {app_name} (ADR-009).

Alle ORM-Zugriffe NUR hier. Views dürfen NICHT direkt auf Models zugreifen.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import {entity}

User = get_user_model()


def get_{app_name}_list(user: User) -> list[{entity}]:
    """Alle {entity}-Objekte des Users."""
    return list({entity}.objects.filter(user=user))


def get_{app_name}(pk: int, user: User) -> {entity}:
    """Einzelnen {entity} laden. Raises {entity}.DoesNotExist wenn nicht gefunden."""
    return {entity}.objects.get(pk=pk, user=user)


def create_{app_name}(user: User, **kwargs) -> {entity}:
    """Neuen {entity} anlegen."""
    return {entity}.objects.create(user=user, **kwargs)


def update_{app_name}(instance: {entity}, **kwargs) -> {entity}:
    """Bestehenden {entity} aktualisieren."""
    for field, value in kwargs.items():
        setattr(instance, field, value)
    instance.save(update_fields=list(kwargs.keys()) + ["updated_at"])
    return instance


def delete_{app_name}(instance: {entity}) -> None:
    """Löscht einen {entity}."""
    instance.delete()
'''


def _views_py(app_name: str, entity: str) -> str:
    return f'''\
"""views.py — HTTP-Layer für {app_name} (ADR-009).

Nur HTTP: Request empfangen, Service aufrufen, Response zurückgeben.
KEIN ORM, KEINE Business-Logik hier.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from . import services as {app_name}_service


@login_required
def {app_name}_list(request: HttpRequest) -> HttpResponse:
    items = {app_name}_service.get_{app_name}_list(request.user)
    return render(request, "{app_name}/{app_name}_list.html", {{"{app_name}s": items}})


@login_required
def {app_name}_detail(request: HttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(
        {app_name}_service.get_{app_name}.__wrapped__ if hasattr({app_name}_service.get_{app_name}, "__wrapped__") else type("_", (), {{}})(),
    )
    item = {app_name}_service.get_{app_name}(pk=pk, user=request.user)
    return render(request, "{app_name}/{app_name}_detail.html", {{"{app_name}": item}})
'''


def _urls_py(app_name: str) -> str:
    return f'''\
from django.urls import path

from . import views

app_name = "{app_name}"

urlpatterns = [
    path("", views.{app_name}_list, name="{app_name}_list"),
    path("<int:pk>/", views.{app_name}_detail, name="{app_name}_detail"),
]
'''


def _admin_py(app_name: str, entity: str) -> str:
    return f'''\
from django.contrib import admin

from .models import {entity}


@admin.register({entity})
class {entity}Admin(admin.ModelAdmin):
    list_display = ["pk", "user", "created_at"]
    list_filter = ["user"]
    readonly_fields = ["created_at", "updated_at"]
'''


def _test_services(app_name: str, entity: str) -> str:
    return f'''\
"""test_{app_name}_services.py — Service-Layer Tests (ADR-057: test_should_*)."""
import pytest

from apps.{app_name} import services as {app_name}_service
from apps.{app_name}.models import {entity}


@pytest.mark.django_db
def test_should_create_{app_name}(db_user):
    item = {app_name}_service.create_{app_name}(user=db_user)
    assert item.pk is not None
    assert item.user == db_user


@pytest.mark.django_db
def test_should_list_{app_name}_for_user(db_user):
    {app_name}_service.create_{app_name}(user=db_user)
    items = {app_name}_service.get_{app_name}_list(db_user)
    assert len(items) == 1


@pytest.mark.django_db
def test_should_not_return_{app_name}_of_other_user(db_user, staff_user):
    {app_name}_service.create_{app_name}(user=staff_user)
    items = {app_name}_service.get_{app_name}_list(db_user)
    assert len(items) == 0


@pytest.mark.django_db
def test_should_delete_{app_name}(db_user):
    item = {app_name}_service.create_{app_name}(user=db_user)
    {app_name}_service.delete_{app_name}(item)
    assert {entity}.objects.filter(pk=item.pk).count() == 0
'''


def _test_views(app_name: str) -> str:
    return f'''\
"""test_{app_name}_views.py — View-Layer Tests via Django Test Client (ADR-057)."""
import pytest


@pytest.mark.django_db
def test_should_list_view_require_login(api_client):
    response = api_client.get("/{app_name}/")
    assert response.status_code == 302
    assert "/login" in response.get("Location", "")


@pytest.mark.django_db
def test_should_list_view_return_200_for_authenticated(auth_client):
    response = auth_client.get("/{app_name}/")
    assert response.status_code == 200
'''


def _settings_installed_apps_hint(app_name: str) -> str:
    return f'    "apps.{app_name}",'


# ── Hauptlogik ────────────────────────────────────────────────────────────────

APP_FILES = {
    "apps/{name}/__init__.py":        lambda c: "",
    "apps/{name}/apps.py":            lambda c: _apps_py(c["app_name"], c["entity"]),
    "apps/{name}/models.py":          lambda c: _models_py(c["app_name"], c["entity"]),
    "apps/{name}/services.py":        lambda c: _services_py(c["app_name"], c["entity"]),
    "apps/{name}/views.py":           lambda c: _views_py(c["app_name"], c["entity"]),
    "apps/{name}/urls.py":            lambda c: _urls_py(c["app_name"]),
    "apps/{name}/admin.py":           lambda c: _admin_py(c["app_name"], c["entity"]),
    "apps/{name}/migrations/__init__.py": lambda c: "",
    "tests/test_{name}_services.py":  lambda c: _test_services(c["app_name"], c["entity"]),
    "tests/test_{name}_views.py":     lambda c: _test_views(c["app_name"]),
}


def to_entity(app_name: str) -> str:
    """trips → Trip, blog_posts → BlogPost"""
    return "".join(w.capitalize() for w in app_name.split("_")).rstrip("s")


def generate_app(
    repo_dir: Path,
    app_name: str,
    entity: str,
    dry_run: bool = False,
) -> dict[str, str]:
    ctx = {"app_name": app_name, "entity": entity, "repo_dir": repo_dir}
    results: dict[str, str] = {}

    for template_path, content_fn in APP_FILES.items():
        rel_path = template_path.replace("{name}", app_name)
        target = repo_dir / rel_path
        content = content_fn(ctx)

        if target.exists():
            results[rel_path] = "SKIP (exists)"
            continue

        if dry_run:
            results[rel_path] = "DRY-RUN"
            print(f"\n--- {rel_path} ---")
            print(content[:150] + ("..." if len(content) > 150 else ""))
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        results[rel_path] = "CREATED"

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Neue Django-App mit ADR-konformem Boilerplate generieren"
    )
    parser.add_argument("repo", help="Repo-Name oder absoluter Pfad")
    parser.add_argument("app_name", help="App-Name (snake_case, z.B. 'trips')")
    parser.add_argument("--entity", default=None,
                        help="Entity-Klassenname (PascalCase, default: aus app_name abgeleitet)")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen")
    args = parser.parse_args()

    repo_dir = Path(args.repo)
    if not repo_dir.is_absolute():
        github_dir = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
        repo_dir = github_dir / args.repo

    if not repo_dir.exists():
        print(f"❌ Repo nicht gefunden: {repo_dir}")
        return 1

    app_name = args.app_name.lower().replace("-", "_")
    entity = args.entity or to_entity(app_name)

    print(f"\n🔧  Generiere App '{app_name}' (Entity: {entity}) in {repo_dir.name}")
    print(f"    Modus: {'DRY-RUN' if args.dry_run else 'ERSTELLEN'}\n")

    results = generate_app(repo_dir, app_name, entity, dry_run=args.dry_run)

    print(f"\n{'='*55}")
    for path, status in results.items():
        icon = "✅" if "CREAT" in status or "DRY" in status else "⏭️ "
        print(f"  {icon}  {path:<45} {status}")
    print(f"{'='*55}")

    if not args.dry_run:
        print(f"\n⚠️  Manuelle Nacharbeiten für '{app_name}':")
        print(f"  1. INSTALLED_APPS in config/settings/base.py ergänzen:")
        print(f"     {_settings_installed_apps_hint(app_name)}")
        print(f"  2. config/urls.py: path('{app_name}/', include('apps.{app_name}.urls', namespace='{app_name}')),")
        print(f"  3. python manage.py makemigrations {app_name}")
        print(f"  4. Templates: templates/{app_name}/{app_name}_list.html + {app_name}_detail.html anlegen")
        print(f"  5. tests/test_{app_name}_views.py: URLs anpassen")

    return 0


if __name__ == "__main__":
    sys.exit(main())
