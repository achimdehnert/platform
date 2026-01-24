# CRUD Frontend Rules (HTMX + Django)

These rules are mandatory for all CRUD UIs (Projects, Agents, Chapters, Characters, LLMs).

## Baseline

- HTMX form contract
  - Use `hx-post` on forms and set an explicit container `hx-target` (e.g., `#llm-content`).
  - On success (HTMX), return the updated list partial. Do not redirect; if you must, use `HX-Redirect` with 204.
- Pagination contract
  - List partials must receive `page_obj` (Django `Paginator`). Controllers must paginate before rendering list partials.
- Error visibility
  - Render `form.non_field_errors` at the top and field-specific errors under each input.
  - On invalid POST, add a non-field error in the view.
- Input normalization
  - In `Form.__init__`: normalize comma decimals and ensure URL schemes (auto prepend `https://`).
  - In `clean()`: repeat normalization and set sensible defaults for omitted numeric fields.
- Secrets handling
  - Secret fields are not required on edit; preserve existing value if blank.
  - Service resolves secrets by priority: DB > Django settings (.env via decouple) > environment.
- Service safety
  - Validate endpoint presence and scheme at request time; return friendly errors; never crash views.

## 422 Flow

- Invalid HTMX POST must return the form partial with HTTP 422.
- Templates use `hx-ext="response-targets"`, `hx-target-422="this"`, and `hx-swap="outerHTML"` so the form replaces itself with validation errors.
- Base template loads `response-targets` extension.

## Success Path

- On success (HTMX): return the corresponding list partial with `page_obj` into the target container, optionally highlight the updated record.
- On success (non-HTMX): use `redirect()` to list/detail as appropriate.

## Developer Checklist (per form change)

1) HTMX wiring: `hx-post`, `hx-target`, `hx-swap`, `hx-ext`, `hx-target-422`.
2) Views: return paginated list on success; return 422 with form on invalid.
3) Partials: render non-field and field errors.
4) Forms: normalization + sensible defaults; preserve secrets.
5) Services: endpoint safety + friendly errors.
