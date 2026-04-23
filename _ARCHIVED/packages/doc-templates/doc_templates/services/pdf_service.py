"""PDF extraction and structure building service."""

import logging
import re

logger = logging.getLogger(__name__)

# concept_templates package (optional — graceful fallback)
try:
    from concept_templates.pdf_structure_extractor import (
        extract_structure_from_text as _pkg_extract,
    )
    _HAS_PKG = True
except ImportError:
    _HAS_PKG = False


def extract_pdf_text(pdf_file) -> str:
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


def text_to_structure(text: str) -> dict:
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


def import_text_into_template(text: str, structure: dict) -> dict:
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
                            rf"^{re.escape(next_num.group(1))}\.?\s+",
                            re.MULTILINE,
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
