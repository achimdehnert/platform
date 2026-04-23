"""Document template views (generalized from explosionsschutz.doc_template_views).

UC1: PDF hochladen → Template erstellen → editieren → akzeptieren
UC2: Template auswählen → Inhalte erstellen
UC3: Template + Dokument hochladen → Inhalte einlesen → editieren

Uses concept_templates package for PDF structure extraction.
Architecture: views → services → models (ADR-041).
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .constants import AI_SOURCE_TYPES_JS
from .models import DocumentInstance, DocumentTemplate
from .services.llm_service import (
    build_prefill_prompt,
    execute_llm_prefill,
    parse_table_response,
)
from .services.pdf_service import (
    extract_pdf_text,
    import_text_into_template,
    text_to_structure,
)
from .services.template_service import (
    get_ai_enabled_fields,
    merge_values_into_structure,
    parse_form_values,
)

logger = logging.getLogger(__name__)

TPL_DIR = "doc_templates"


def _tenant_id(request: HttpRequest) -> str:
    return str(getattr(request, "tenant_id", ""))


# ─── Template List ───────────────────────────────────────────


@login_required
def template_list(request: HttpRequest) -> HttpResponse:
    """Alle Dokumentvorlagen anzeigen."""
    tid = _tenant_id(request)
    templates = DocumentTemplate.objects.filter(
        tenant_id=tid,
    ).order_by("-updated_at")
    instances = DocumentInstance.objects.filter(
        tenant_id=tid,
    ).select_related("template").order_by("-updated_at")[:20]

    return render(request, f"{TPL_DIR}/list.html", {
        "templates": templates,
        "instances": instances,
    })


# ─── Template Create (manual) ───────────────────────────────


@login_required
def template_create(request: HttpRequest) -> HttpResponse:
    """Neue leere Dokumentvorlage erstellen."""
    if request.method == "GET":
        return render(request, f"{TPL_DIR}/create.html")

    tid = _tenant_id(request)
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Name ist Pflichtfeld.")
        return render(request, f"{TPL_DIR}/create.html")

    desc = request.POST.get("description", "").strip()
    scope = request.POST.get("scope", "").strip()
    structure = {
        "sections": [{
            "key": "section_1",
            "label": "1. Allgemeines",
            "fields": [{
                "key": "inhalt", "label": "Inhalt",
                "type": "textarea", "required": False,
            }],
        }],
    }

    tmpl = DocumentTemplate.objects.create(
        tenant_id=tid, name=name, description=desc, scope=scope,
        structure_json=json.dumps(structure, ensure_ascii=False),
    )
    messages.success(request, f"Vorlage '{name}' erstellt.")
    return redirect("doc_templates:template-edit", pk=tmpl.pk)


# ─── Template Create from Upload (UC1) ──────────────────────


@login_required
def template_upload(request: HttpRequest) -> HttpResponse:
    """PDF hochladen → Text extrahieren → Template erstellen."""
    if request.method == "GET":
        return render(request, f"{TPL_DIR}/upload.html")

    tid = _tenant_id(request)
    pdf_file = request.FILES.get("pdf_file")
    if not pdf_file:
        messages.error(request, "Keine Datei ausgewählt.")
        return render(request, f"{TPL_DIR}/upload.html")

    name = request.POST.get("name", "").strip()
    if not name:
        name = pdf_file.name.replace(".pdf", "").replace("_", " ")
    scope = request.POST.get("scope", "").strip()

    text = extract_pdf_text(pdf_file)
    if not text:
        messages.warning(
            request,
            "Kein Text aus PDF extrahiert. Leere Vorlage erstellt.",
        )

    structure = text_to_structure(text) if text else {"sections": []}

    tmpl = DocumentTemplate.objects.create(
        tenant_id=tid, name=name, scope=scope,
        description=request.POST.get("description", ""),
        structure_json=json.dumps(structure, ensure_ascii=False),
        source_filename=pdf_file.name,
        source_text=text[:50000],
    )
    messages.success(
        request,
        f"Vorlage '{name}' aus PDF erstellt ({tmpl.section_count} Abschnitte).",
    )
    return redirect("doc_templates:template-edit", pk=tmpl.pk)


# ─── Template Edit ───────────────────────────────────────────


@login_required
def template_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Template-Struktur bearbeiten."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(DocumentTemplate, pk=pk, tenant_id=tid)

    if request.method == "GET":
        try:
            structure = json.loads(tmpl.structure_json)
        except (json.JSONDecodeError, TypeError):
            structure = {"sections": []}

        return render(request, f"{TPL_DIR}/edit.html", {
            "tmpl": tmpl,
            "structure": structure,
            "structure_json": json.dumps(structure, ensure_ascii=False, indent=2),
        })

    # POST: Struktur speichern
    raw_json = request.POST.get("structure_json", "")
    try:
        structure = json.loads(raw_json)
        if "sections" not in structure:
            raise ValueError("Missing 'sections' key")
    except (json.JSONDecodeError, ValueError) as exc:
        messages.error(request, f"Ungültiges JSON: {exc}")
        return render(request, f"{TPL_DIR}/edit.html", {
            "tmpl": tmpl,
            "structure": {"sections": []},
            "structure_json": raw_json,
        })

    tmpl.structure_json = json.dumps(structure, ensure_ascii=False)
    tmpl.name = request.POST.get("name", tmpl.name)
    tmpl.description = request.POST.get("description", tmpl.description)
    new_status = request.POST.get("status", tmpl.status)
    if new_status in dict(DocumentTemplate.Status.choices):
        tmpl.status = new_status
    tmpl.save()

    messages.success(request, "Vorlage gespeichert.")
    return redirect("doc_templates:template-list")


# ─── Template Delete ─────────────────────────────────────────


@login_required
@require_POST
def template_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Dokumentvorlage löschen."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(DocumentTemplate, pk=pk, tenant_id=tid)
    name = tmpl.name
    try:
        tmpl.delete()
    except models.ProtectedError:
        count = tmpl.instances.count()
        messages.error(
            request,
            f"Vorlage '{name}' kann nicht gelöscht werden — "
            f"es gibt noch {count} Dokument(e) die darauf basieren.",
        )
        return redirect("doc_templates:template-list")
    messages.success(request, f"Vorlage '{name}' gelöscht.")
    return redirect("doc_templates:template-list")


# ─── Instance Create (UC2 + UC3) ────────────────────────────


@login_required
def instance_create(request: HttpRequest, template_pk: int) -> HttpResponse:
    """Neues Dokument aus Template erstellen (leer oder Import)."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(DocumentTemplate, pk=template_pk, tenant_id=tid)

    if request.method == "GET":
        return render(request, f"{TPL_DIR}/instance_create.html", {"tmpl": tmpl})

    name = request.POST.get("name", "").strip()
    if not name:
        name = f"{tmpl.name} — Neu"

    try:
        structure = json.loads(tmpl.structure_json)
    except (json.JSONDecodeError, TypeError):
        structure = {"sections": []}

    # UC3: Dokument hochladen → Inhalte einlesen
    pdf_file = request.FILES.get("pdf_file")
    values = {}
    source_filename = ""

    if pdf_file:
        text = extract_pdf_text(pdf_file)
        if text:
            values = import_text_into_template(text, structure)
            source_filename = pdf_file.name
            messages.info(request, f"Inhalte aus '{pdf_file.name}' importiert.")
        else:
            messages.warning(request, "Kein Text aus PDF extrahiert.")

    instance = DocumentInstance.objects.create(
        tenant_id=tid, template=tmpl, name=name,
        values_json=json.dumps(values, ensure_ascii=False),
        source_filename=source_filename,
    )
    return redirect("doc_templates:instance-edit", pk=instance.pk)


# ─── Instance Edit ───────────────────────────────────────────


@login_required
def instance_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Dokument-Inhalte bearbeiten."""
    tid = _tenant_id(request)
    instance = get_object_or_404(
        DocumentInstance.objects.select_related("template"),
        pk=pk, tenant_id=tid,
    )

    try:
        structure = json.loads(instance.template.structure_json)
    except (json.JSONDecodeError, TypeError):
        structure = {"sections": []}

    if request.method == "GET":
        values = instance.get_values()
        merge_values_into_structure(structure, values)
        ai_fields = get_ai_enabled_fields(structure)

        return render(request, f"{TPL_DIR}/instance_edit.html", {
            "instance": instance,
            "structure": structure,
            "ai_fields_json": json.dumps(ai_fields, ensure_ascii=False),
        })

    # POST: Werte speichern
    values = parse_form_values(request.POST, structure)

    new_status = request.POST.get("status", instance.status)
    if new_status in dict(DocumentInstance.Status.choices):
        instance.status = new_status

    instance.values_json = json.dumps(values, ensure_ascii=False)
    instance.name = request.POST.get("name", instance.name)
    instance.save()

    messages.success(request, "Dokument gespeichert.")
    return redirect("doc_templates:instance-edit", pk=instance.pk)


# ─── Instance Delete ─────────────────────────────────────────


@login_required
@require_POST
def instance_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Dokument löschen."""
    tid = _tenant_id(request)
    instance = get_object_or_404(DocumentInstance, pk=pk, tenant_id=tid)
    name = instance.name
    instance.delete()
    messages.success(request, f"Dokument '{name}' gelöscht.")
    return redirect("doc_templates:template-list")


# ─── Instance LLM Prefill ────────────────────────────────────


@login_required
@require_POST
def instance_llm_prefill(request: HttpRequest, pk: int) -> HttpResponse:
    """HTMX endpoint: KI-Prefill für ein einzelnes Feld."""
    tid = _tenant_id(request)
    instance = get_object_or_404(
        DocumentInstance.objects.select_related("template"),
        pk=pk, tenant_id=tid,
    )

    field_key = request.POST.get("field_key", "")
    llm_hint = request.POST.get("llm_hint", "")
    ai_sources_raw = request.POST.get("ai_sources", "")
    field_type = request.POST.get("field_type", "textarea")

    if not field_key or not llm_hint:
        return HttpResponse(
            "field_key und llm_hint erforderlich", status=400,
        )

    ai_sources = [
        s.strip() for s in ai_sources_raw.split(",") if s.strip()
    ]

    # Find table columns from structure if needed
    table_columns = []
    if field_type == "table":
        structure = instance.template.get_structure()
        for sec in structure.get("sections", []):
            for fld in sec.get("fields", []):
                if fld["key"] == field_key.split("__")[-1]:
                    table_columns = fld.get("columns", [])
                    break

    system_prompt, user_prompt, max_tokens = build_prefill_prompt(
        field_key=field_key,
        field_type=field_type,
        llm_hint=llm_hint,
        ai_sources=ai_sources,
        scope=instance.template.scope or "Fachbereich",
        existing_values=instance.get_values(),
        source_text=instance.template.source_text or "",
        tenant_id=tid,
        instance=instance,
        table_columns=table_columns,
    )

    try:
        value = execute_llm_prefill(
            system_prompt, user_prompt, max_tokens,
        )
    except ImportError:
        return HttpResponse(
            '<span class="text-red-500 text-sm">'
            "LLM nicht verfügbar (iil-aifw benötigt)</span>",
        )
    except Exception as exc:
        logger.warning("LLM prefill failed: %s", exc)
        return HttpResponse(
            f'<span class="text-red-500 text-sm">'
            f"Fehler: {exc}</span>",
        )

    from django.utils.html import escape

    # Table fields: parse JSON response into rows (#7)
    if field_type == "table" and table_columns:
        rows = parse_table_response(value, len(table_columns))
        return JsonResponse({"rows": rows, "field_key": field_key})

    safe_val = escape(value)
    return HttpResponse(
        f'<textarea name="{field_key}" rows="4" '
        f'class="w-full px-3 py-2 border border-green-300 '
        f'rounded-lg bg-green-50 focus:ring-2 '
        f'focus:ring-orange-500">{safe_val}</textarea>',
    )


# ─── Instance Bulk Prefill (#4) ──────────────────────────────


@login_required
@require_POST
def instance_bulk_prefill(request: HttpRequest, pk: int) -> JsonResponse:
    """Bulk-Prefill: alle KI-Felder auf einmal füllen."""
    tid = _tenant_id(request)
    instance = get_object_or_404(
        DocumentInstance.objects.select_related("template"),
        pk=pk, tenant_id=tid,
    )

    structure = instance.template.get_structure()
    ai_fields = get_ai_enabled_fields(structure)
    existing_values = instance.get_values()
    source_text = instance.template.source_text or ""
    scope = instance.template.scope or "Fachbereich"

    results = {}
    errors = {}

    for af in ai_fields:
        fk = af["form_key"]
        try:
            sys_p, usr_p, max_tok = build_prefill_prompt(
                field_key=af["field_key"],
                field_type=af["field_type"],
                llm_hint=af["ai_prompt"],
                ai_sources=af["ai_sources"],
                scope=scope,
                existing_values=existing_values,
                source_text=source_text,
                tenant_id=tid,
                instance=instance,
                table_columns=af.get("columns", []),
            )
            value = execute_llm_prefill(sys_p, usr_p, max_tok)

            if af["field_type"] == "table" and af.get("columns"):
                rows = parse_table_response(
                    value, len(af["columns"]),
                )
                results[fk] = {"type": "table", "rows": rows}
            else:
                results[fk] = {"type": "text", "value": value}

        except Exception as exc:
            logger.warning("Bulk prefill '%s' failed: %s", fk, exc)
            errors[fk] = str(exc)

    return JsonResponse({
        "results": results,
        "errors": errors,
        "total": len(ai_fields),
        "success": len(results),
        "failed": len(errors),
    })


# ─── Instance PDF Export ──────────────────────────────────────


@login_required
def instance_pdf_export(request: HttpRequest, pk: int) -> HttpResponse:
    """PDF-Export eines ausgefüllten Dokuments."""
    tid = _tenant_id(request)
    instance = get_object_or_404(
        DocumentInstance.objects.select_related("template"),
        pk=pk, tenant_id=tid,
    )

    try:
        from concept_templates.document_renderer import render_pdf
        from concept_templates.schemas import (
            ConceptTemplate,
            FieldType,
            TemplateField,
            TemplateSection,
        )
    except ImportError:
        messages.error(request, "PDF-Export benötigt concept_templates[render].")
        return redirect("doc_templates:instance-edit", pk=instance.pk)

    structure = json.loads(instance.template.structure_json)
    values = instance.get_values()

    sections = []
    for i, s in enumerate(structure.get("sections", [])):
        fields = []
        for f in s.get("fields", []):
            ft = FieldType.TEXTAREA
            if f.get("type") == "text":
                ft = FieldType.TEXT
            elif f.get("type") == "table":
                ft = FieldType.TABLE
            fields.append(TemplateField(
                name=f["key"],
                label=f.get("label", f["key"]),
                field_type=ft,
            ))
        sections.append(TemplateSection(
            name=s["key"],
            title=s.get("label", f"Abschnitt {i + 1}"),
            order=i + 1,
            fields=fields,
        ))

    ct = ConceptTemplate(
        name=instance.template.name,
        scope=instance.template.scope or "general",
        version="1.0",
        sections=sections,
    )

    pdf_bytes = render_pdf(template=ct, values=values, title=instance.name)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    safe_name = instance.name.replace(" ", "_")[:80]
    response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'
    return response
