"""Template and instance business logic service."""

from ..constants import AI_SOURCE_SHORT_LABELS


def merge_values_into_structure(
    structure: dict,
    values: dict,
) -> dict:
    """Merge saved values into template structure for rendering.

    Mutates structure in-place and returns it.
    """
    for section in structure.get("sections", []):
        skey = section["key"]
        svals = values.get(skey, {})
        for field in section.get("fields", []):
            fkey = field["key"]
            ftype = field.get("type", "textarea")
            val = svals.get(fkey, "")
            if ftype == "table":
                field["table_rows"] = (
                    val if isinstance(val, list)
                    else field.get("default_rows", [])
                )
                cols = field.get("columns", [])
                while len(field["table_rows"]) < 3:
                    field["table_rows"].append([""] * len(cols))
            else:
                field["field_value"] = val or field.get("default", "")

            # AI config for template rendering
            ai_src = field.get("ai_sources", [])
            if ai_src:
                field["ai_sources_csv"] = ",".join(ai_src)
                field["ai_sources_labels"] = ", ".join(
                    AI_SOURCE_SHORT_LABELS.get(s, s) for s in ai_src
                )
    return structure


def parse_form_values(request_post, structure: dict) -> dict:
    """Parse form POST data into values dict matching structure."""
    values = {}
    for section in structure.get("sections", []):
        skey = section["key"]
        values[skey] = {}
        for field in section.get("fields", []):
            fkey = field["key"]
            ftype = field.get("type", "textarea")
            form_key = f"{skey}__{fkey}"

            if ftype == "table":
                columns = field.get("columns", [])
                rows = []
                row_idx = 0
                while True:
                    row_key = f"{form_key}__row_{row_idx}"
                    first_col = request_post.get(
                        f"{row_key}__col_0", None,
                    )
                    if first_col is None:
                        break
                    row = []
                    for ci in range(len(columns)):
                        cell = request_post.get(
                            f"{row_key}__col_{ci}", "",
                        )
                        row.append(cell)
                    if any(c.strip() for c in row):
                        rows.append(row)
                    row_idx += 1
                values[skey][fkey] = rows
            elif ftype == "boolean":
                vals = request_post.getlist(form_key)
                values[skey][fkey] = (
                    "true" if "true" in vals else "false"
                )
            else:
                values[skey][fkey] = request_post.get(form_key, "")

    return values


def get_ai_enabled_fields(structure: dict) -> list[dict]:
    """Return list of all ai_enabled fields with section context.

    Each item: {section_key, field_key, field_type, ai_prompt,
                ai_sources, ai_prompt_visible, label, columns}
    """
    fields = []
    for section in structure.get("sections", []):
        skey = section["key"]
        for field in section.get("fields", []):
            if not field.get("ai_enabled"):
                continue
            fields.append({
                "section_key": skey,
                "field_key": field["key"],
                "form_key": f"{skey}__{field['key']}",
                "field_type": field.get("type", "textarea"),
                "ai_prompt": field.get("ai_prompt", field.get("label", "")),
                "ai_sources": field.get("ai_sources", []),
                "ai_sources_csv": ",".join(field.get("ai_sources", [])),
                "ai_prompt_visible": field.get("ai_prompt_visible", True),
                "label": field.get("label", field["key"]),
                "columns": field.get("columns", []),
            })
    return fields
