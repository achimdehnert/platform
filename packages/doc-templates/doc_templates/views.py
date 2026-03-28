"""Document template views (generalized from explosionsschutz.doc_template_views).

UC1: PDF hochladen → Template erstellen → editieren → akzeptieren
UC2: Template auswählen → Inhalte erstellen
UC3: Template + Dokument hochladen → Inhalte einlesen → editieren

Uses concept_templates package for PDF structure extraction.
"""

import json
import logging
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import DocumentInstance, DocumentTemplate

logger = logging.getLogger(__name__)

TPL_DIR = "doc_templates"

# concept_templates package (optional — graceful fallback)
try:
    from concept_templates.pdf_structure_extractor import (
        extract_structure_from_text as _pkg_extract,
    )
    _HAS_PKG = True
except ImportError:
    _HAS_PKG = False


def _tenant_id(request: HttpRequest) -> str:
    return str(getattr(request, "tenant_id", ""))


# ─── PDF Extraction Helpers ──────────────────────────────────


def _extract_pdf_text(pdf_file) -> str:
    """PDF-Text extrahieren (pdfplumber oder PyPDF2)."""
    try:
        import pdfplumber
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)
        parts = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        return "\n".join(parts)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("pdfplumber failed: %s", exc)

    try:
        import PyPDF2
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)
        reader = PyPDF2.PdfReader(pdf_file)
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("PyPDF2 failed: %s", exc)

    return ""


def _template_to_dict(ct) -> dict:
    """ConceptTemplate → JSON-kompatibles dict für DB."""
    sections = []
    for s in ct.sections:
        fields = []
        for f in s.fields:
            fd = {
                "key": f.name,
                "label": f.label,
                "type": str(f.field_type.value),
                "required": f.required,
            }
            if f.default:
                fd["default"] = f.default
            if f.columns:
                fd["columns"] = f.columns
            if f.default_rows:
                fd["default_rows"] = f.default_rows
            fields.append(fd)
        sections.append({
            "key": s.name,
            "label": s.title,
            "fields": fields,
        })
    return {"sections": sections}


def _text_to_structure(text: str) -> dict:
    """Convert extracted PDF text to template structure.

    Delegates to concept_templates package if available.
    Fallback: simple heading detection.
    """
    if _HAS_PKG:
        ct = _pkg_extract(text)
        return _template_to_dict(ct)

    # Fallback: heading detection
    sections = []
    num_pat = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+(.+)$", re.MULTILINE)
    matches = list(num_pat.finditer(text))

    for i, m in enumerate(matches):
        num = m.group(1).rstrip(".")
        title = m.group(2).strip()
        try:
            top = int(num.split(".")[0])
            if top > 30:
                continue
        except ValueError:
            continue
        if sum(1 for c in title if c.isalpha()) < 2:
            continue

        key = f"section_{num.replace('.', '_')}"
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()[:3000]

        fields = [{
            "key": "inhalt", "label": "Inhalt",
            "type": "textarea", "required": False,
        }]
        if content:
            fields[0]["default"] = content

        sections.append({
            "key": key, "label": f"{num}. {title}", "fields": fields,
        })

    if not sections:
        sections = [{
            "key": "section_1",
            "label": "1. Dokumentinhalt",
            "fields": [{
                "key": "inhalt", "label": "Inhalt",
                "type": "textarea", "required": False,
                "default": text[:5000],
            }],
        }]

    return {"sections": sections}


def _import_text_into_template(text: str, structure: dict) -> dict:
    """Import text from document into template values."""
    values = {}
    sections = structure.get("sections", [])

    for i, section in enumerate(sections):
        skey = section["key"]
        label = section.get("label", "")
        fields = section.get("fields", [])

        content = ""
        num_match = re.match(r"(\d+(?:\.\d+)*)", label)
        if num_match:
            num = num_match.group(1)
            pat = re.compile(rf"^{re.escape(num)}\.?\s+", re.MULTILINE)
            match = pat.search(text)
            if match:
                start = match.end()
                next_section = sections[i + 1] if i + 1 < len(sections) else None
                if next_section:
                    next_label = next_section.get("label", "")
                    next_num = re.match(r"(\d+(?:\.\d+)*)", next_label)
                    if next_num:
                        next_pat = re.compile(
                            rf"^{re.escape(next_num.group(1))}\.?\s+", re.MULTILINE,
                        )
                        next_m = next_pat.search(text, start)
                        end = next_m.start() if next_m else len(text)
                    else:
                        end = len(text)
                else:
                    end = len(text)
                content = text[start:end].strip()

        values[skey] = {}
        for field in fields:
            fkey = field["key"]
            ftype = field.get("type", "textarea")
            if ftype == "table":
                values[skey][fkey] = []
            else:
                values[skey][fkey] = content[:5000]

    return values


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

    text = _extract_pdf_text(pdf_file)
    if not text:
        messages.warning(request, "Kein Text aus PDF extrahiert. Leere Vorlage erstellt.")

    structure = _text_to_structure(text) if text else {"sections": []}

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
        text = _extract_pdf_text(pdf_file)
        if text:
            values = _import_text_into_template(text, structure)
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
        try:
            values = json.loads(instance.values_json)
        except (json.JSONDecodeError, TypeError):
            values = {}

        # AI source label mapping
        _ai_src_labels = {
            "sds": "SDS", "bedienungsanleitung": "Bedienungsanl.",
            "standortdaten": "Standortdaten", "cad": "CAD",
            "zonenplan": "Zonenpl\u00e4ne",
            "gefaehrdungsbeurteilung": "GBU",
            "betriebsanweisung": "Betriebsanw.",
            "pruefbericht": "Pr\u00fcfberichte",
            "rechtliche_grundlagen": "Normen",
            "wartungsplan": "Wartungsplan",
            "risikobewertung": "Risikobew.",
            "brandschutz": "Brandschutz",
        }

        # Merge values into structure for easy rendering
        for section in structure.get("sections", []):
            skey = section["key"]
            svals = values.get(skey, {})
            for field in section.get("fields", []):
                fkey = field["key"]
                ftype = field.get("type", "textarea")
                val = svals.get(fkey, "")
                if ftype == "table":
                    field["table_rows"] = (
                        val if isinstance(val, list) else field.get("default_rows", [])
                    )
                    cols = field.get("columns", [])
                    while len(field["table_rows"]) < 3:
                        field["table_rows"].append(["" ] * len(cols))
                else:
                    field["field_value"] = val or field.get("default", "")

                # AI config for template rendering
                ai_src = field.get("ai_sources", [])
                if ai_src:
                    field["ai_sources_csv"] = ",".join(ai_src)
                    field["ai_sources_labels"] = ", ".join(
                        _ai_src_labels.get(s, s) for s in ai_src
                    )

        return render(request, f"{TPL_DIR}/instance_edit.html", {
            "instance": instance,
            "structure": structure,
        })

    # POST: Werte speichern
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
                    first_col = request.POST.get(f"{row_key}__col_0", None)
                    if first_col is None:
                        break
                    row = []
                    for ci in range(len(columns)):
                        cell = request.POST.get(f"{row_key}__col_{ci}", "")
                        row.append(cell)
                    if any(c.strip() for c in row):
                        rows.append(row)
                    row_idx += 1
                values[skey][fkey] = rows
            elif ftype == "boolean":
                vals = request.POST.getlist(form_key)
                values[skey][fkey] = "true" if "true" in vals else "false"
            else:
                values[skey][fkey] = request.POST.get(form_key, "")

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

    if not field_key or not llm_hint:
        return HttpResponse("field_key und llm_hint erforderlich", status=400)

    # Parse requested AI source types
    ai_sources = [
        s.strip() for s in ai_sources_raw.split(",") if s.strip()
    ]

    # Build context from existing values
    context_parts = []
    if instance.values_json and instance.values_json != "{}":
        try:
            vals = json.loads(instance.values_json)
            for skey, svals in vals.items():
                for fkey, fval in svals.items():
                    if isinstance(fval, str) and fval.strip():
                        context_parts.append(f"{fkey}: {fval[:300]}")
        except (json.JSONDecodeError, AttributeError):
            pass

    # Source text from template as reference
    extracted_texts = []
    if instance.template.source_text:
        extracted_texts = [instance.template.source_text[:5000]]

    # AI source type labels for prompt context
    _src_labels = {
        "sds": "Sicherheitsdatenblätter",
        "bedienungsanleitung": "Bedienungsanleitungen",
        "standortdaten": "Standort- und Gebäudedaten",
        "cad": "CAD-Zeichnungen und Anlagenpläne",
        "zonenplan": "Zonenpläne und Ex-Zonen-Einteilung",
        "gefaehrdungsbeurteilung": "Gefährdungsbeurteilungen",
        "betriebsanweisung": "Betriebsanweisungen",
        "pruefbericht": "Prüfberichte und Protokolle",
        "rechtliche_grundlagen": "Rechtliche Grundlagen",
        "wartungsplan": "Wartungs-/Instandhaltungspläne",
        "risikobewertung": "Risikobewertungen",
        "brandschutz": "Brandschutzkonzepte",
    }

    scope = instance.template.scope or "Fachbereich"
    system_prompt = (
        f"Du bist ein Experte für {scope} und technische Dokumentation. "
        "Schreibe fachlich korrekte, präzise Texte auf Deutsch. "
        "Antworte NUR mit dem Feldinhalt, keine Erklärungen."
    )

    # Use template-defined prompt as primary instruction
    user_prompt = f"Aufgabe: {llm_hint}\n"

    # Add source type instructions
    if ai_sources:
        src_names = [_src_labels.get(s, s) for s in ai_sources]
        user_prompt += (
            "\nBerücksichtige folgende Dokumenttypen "
            "als fachliche Grundlage:\n- "
            + "\n- ".join(src_names) + "\n"
        )

    if context_parts:
        user_prompt += "\nBereits ausgefüllte Felder:\n" + "\n".join(context_parts[:10]) + "\n"
    if extracted_texts:
        joined = "\n---\n".join(t[:3000] for t in extracted_texts)
        user_prompt += f"\nReferenz-Dokument(e):\n{joined}\n"
    user_prompt += f"\nSchreibe den Inhalt für das Feld '{field_key}'."

    try:
        from aifw.service import sync_completion
        value = sync_completion(
            prompt=user_prompt,
            system=system_prompt,
            action_code="doc_template_prefill",
            temperature=0.3,
            max_tokens=500,
        )
    except ImportError:
        try:
            from ai_analysis.llm_client import llm_complete_sync
            value = llm_complete_sync(
                prompt=user_prompt,
                system=system_prompt,
                action_code="doc_template_prefill",
                temperature=0.3,
                max_tokens=500,
            )
        except ImportError:
            return HttpResponse(
                '<span class="text-red-500 text-sm">LLM nicht verfügbar '
                '(iil-aifw oder ai_analysis benötigt)</span>',
            )
    except Exception as exc:
        logger.warning("LLM prefill failed: %s", exc)
        return HttpResponse(f'<span class="text-red-500 text-sm">Fehler: {exc}</span>')

    from django.utils.html import escape
    safe_val = escape(value)
    return HttpResponse(
        f'<textarea name="{field_key}" rows="4" '
        f'class="w-full px-3 py-2 border border-green-300 '
        f'rounded-lg bg-green-50 focus:ring-2 '
        f'focus:ring-orange-500">{safe_val}</textarea>',
    )


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
