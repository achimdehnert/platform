# `iil-klickdummy` — Shared Infrastructure for platform:ADR-211

> **Versioniertes Python-Paket mit Schemas + Skripten für Klickdummy-Konformität
> nach `platform:ADR-211` (Rev 12, accepted) und Plattform-Heimat-Mechanik nach
> `platform:ADR-214`.**

## Install

```bash
pip install iil-klickdummy>=1.0,<2.0
```

Workspace-Pattern (vor PyPI-Release):

```bash
pip install -e ../platform/packages/iil-klickdummy
```

## CLI

Alle Targets als Console-Scripts verfügbar:

```bash
klickdummy-i1 docs/.../spec.yaml:docs/.../spec.schema.json
klickdummy-i2 docs/.../spec.yaml:docs/.../spec.schema.json
klickdummy-i3 docs/.../spec.yaml:docs/.../spec.schema.json
klickdummy-i4 docs/                      # rekursiver Cross-Repo-Ref-Lint
klickdummy-extract-requirements docs/.../spec.yaml
klickdummy-inventory                     # S11 Cross-Repo Legacy-Inventur
```

Repo-Makefile kann wahlweise via `python3 -m` oder direkt aufrufen:

```makefile
klickdummy-i1:
	klickdummy-i1 docs/01-architektur/mockups/<klickdummy>/spec.yaml:docs/.../spec.schema.json
```

## Schemas

Verfügbar via `importlib.resources`:

```python
from importlib.resources import files
import json

schema_text = files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text()
schema = json.loads(schema_text)
```

Oder in `spec.yaml`:

```yaml
$schema: https://raw.githubusercontent.com/achimdehnert/platform/main/packages/iil-klickdummy/src/iil_klickdummy/schemas/screens-spec.schema.json
```

## Versionierung

`semver`. Breaking Changes (z. B. Pattern-Set ändern) → Major-Bump → Migrations-
Cookbook im ADR-Update (analog ADR-211 Rev 12 §Migration).

| Version | Datum | Highlights |
|---|---|---|
| 1.0.0 | 2026-05-20 | Initial. Rev-11 4-Pattern strict, S11-Inventur, Requirements-Bridge. |

## Bezug

- `platform:ADR-211` Rev 12 — Konvention (was die Skripte prüfen)
- `platform:ADR-214` — Mechanik (warum das Paket existiert)
- `platform:ADR-213` — Cross-Repo-Ref-Format (was check_i4 prüft)
