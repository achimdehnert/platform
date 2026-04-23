# django-module-shop

Reusable Django app for module catalogue & subscription management.

## Installation

```
django-module-shop @ git+https://github.com/achimdehnert/platform.git#subdirectory=packages/django-module-shop
```

## Setup

1. Add `django_module_shop` to `INSTALLED_APPS`
2. Add URL pattern: `path("billing/modules/", include("django_module_shop.urls"))`
3. Define `MODULE_SHOP_CATALOGUE` in settings:

```python
MODULE_SHOP_CATALOGUE = {
    "my_module": {
        "name": "My Module",
        "description": "Does something useful",
        "icon": "box",
        "price_month": 9.0,
        "price_year": 90.0,
        "category": "core",
    }
}
```

## Notes

- `ModuleToggleView` requires `django_tenancy` for tenant-aware activation.
- Without `django_tenancy`, all modules are shown as available but toggle is disabled.
- Templates extend `base.html` — override `catalogue.html` in your project if needed.
