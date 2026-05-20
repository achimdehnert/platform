# `iil-klickdummy` — Shared Infrastructure for `platform:ADR-211` (Rev 13)

> Versioniertes pip-Paket mit allem, was Klickdummy-Konformität braucht:
> Schemas, Konformitäts-Checks (I1–I4), Requirements-Bridge, S11-Inventur,
> **und** das Feedback-Widget v0.5 (Co-Creation-Loop, GitHub-Direkt-API).

## Install

```bash
pip install "iil-klickdummy @ git+https://github.com/achimdehnert/platform.git@v1.0.0#subdirectory=packages/iil-klickdummy"
```

Privates PyPI (sobald aufgesetzt):

```bash
pip install "iil-klickdummy>=1.0,<2.0"
```

## Console-Scripts

```bash
klickdummy-i1 <spec>:<schema> ...          # Spec ↔ Route Coverage
klickdummy-i2 <spec>:<schema> ...          # 4-Pattern (strict-mode)
klickdummy-i3 <spec>:<schema> ...          # Off-Ramp + Sunset
klickdummy-i4 docs/                        # Cross-Repo-Ref-Format
klickdummy-extract-requirements <spec>     # Spec → UC/FR/NFR/Lasten/Pflicht
klickdummy-inventory                       # S11 cross-repo legacy class scan
klickdummy-install-snippets [--symlink]    # HTML+JS+templates in <repo>/platform-snippets/
```

## Feedback-Widget (v0.5)

Browser-side, opt-in via `?feedback=on`. Submit-Modes:

| Mode | Was passiert |
|---|---|
| `download` | Markdown-Datei (offline-fähig, kein GitHub-Token nötig) |
| `clipboard` | navigator.clipboard.writeText |
| `github` | **POST direkt an `api.github.com/repos/.../issues`** mit User-PAT aus `localStorage.klickdummy_github_token`; Issue-Author = realer GitHub-User; Audit native |

**Konfiguration im Host (vor Widget-Script-Tag):**

```html
<script>
  window.KLICKDUMMY_SPEC = { id: "repo:klickdummy-spec-<name>", version: "0.1", klickdummy_class: "mock" };
  window.KLICKDUMMY_FEEDBACK_REPO = "owner/repo";        // GitHub-Zielrepo
  // optional Plugin-Hooks:
  window.KLICKDUMMY_CATEGORIES = [...];                  // override default 5
  window.KLICKDUMMY_PERSONA_HOOK = () => '...';
  window.KLICKDUMMY_VERFAHREN_HOOK = () => '...';
</script>
<script src="platform-snippets/klickdummy/feedback-widget/widget.js" defer></script>
```

## Schemas (importlib.resources)

```python
from importlib.resources import files
import json
schema = json.loads(files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text())
```

## Bezug

- `platform:ADR-211` Rev 13 — Konvention + Distribution + Co-Creation-Pfade
- `platform:ADR-212` — Traefik-Ingress (für künftige PyPI-Selbsthost)
- `platform:ADR-213` — Cross-Repo-Ref-Format (was `klickdummy-i4` prüft)
