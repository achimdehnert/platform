"""
src/dms_archive/integration.py
================================
Fertige Integrations-Snippets für bestehende risk-hub services.py-Dateien.

ANLEITUNG:
  Diese Datei zeigt die genauen Code-Änderungen, die in den
  bestehenden Services ergänzt werden müssen.
  Keine neue Datei anlegen — direkt in die jeweiligen services.py einfügen.

Betroffene Dateien:
  1. src/dsb/services/audit_service.py   → finalize_audit()
  2. src/dsb/services/breach_service.py  → submit_to_authority()
  3. src/dsb/services/report_service.py  → generate_jahresbericht()
  4. src/risk/services/assessment_service.py → finalize_assessment()
"""

# ════════════════════════════════════════════════════════════════════════════
# 1. src/dsb/services/audit_service.py
#    Ergänzung in: finalize_audit(audit_id, tenant_id, performed_by)
# ════════════════════════════════════════════════════════════════════════════

AUDIT_SERVICE_PATCH = '''
# --- DMS-Archivierung (am Ende von finalize_audit, nach emit_audit_event) ---
from src.dms_archive.services import DmsArchiveService, ArchiveRequest
from src.dms_archive.models import DmsArchiveRecord

DmsArchiveService.schedule_archival(ArchiveRequest(
    tenant_id    = audit.tenant_id,
    source_type  = DmsArchiveRecord.DocumentType.PRIVACY_AUDIT,
    source_id    = audit.id,
    source_label = f"Datenschutz-Audit {audit.mandate.name} {audit.audit_date:%Y-%m-%d}",
    performed_by = performed_by,
    dms_category = "DSGVO_AUDIT",
    dms_properties = {
        "Mandant":      audit.mandate.name,
        "Audit-Datum":  audit.audit_date.isoformat(),
        "Auditor":      audit.auditor or "",
        "Befunde":      str(audit.findings.count()),
    },
))
# --- Ende DMS-Archivierung ---
'''

# ════════════════════════════════════════════════════════════════════════════
# 2. src/dsb/services/breach_service.py
#    Ergänzung in: submit_breach_to_authority(breach_id, tenant_id, performed_by)
# ════════════════════════════════════════════════════════════════════════════

BREACH_SERVICE_PATCH = '''
# --- DMS-Archivierung (nach Meldung an Behörde) ---
from src.dms_archive.services import DmsArchiveService, ArchiveRequest
from src.dms_archive.models import DmsArchiveRecord

DmsArchiveService.schedule_archival(ArchiveRequest(
    tenant_id    = breach.tenant_id,
    source_type  = DmsArchiveRecord.DocumentType.DATA_BREACH,
    source_id    = breach.id,
    source_label = f"Datenpanne {breach.mandate.name} {breach.discovered_at:%Y-%m-%d}",
    performed_by = performed_by,
    dms_category = "DSGVO_PANNE",
    dms_properties = {
        "Mandant":           breach.mandate.name,
        "Entdeckt-am":       breach.discovered_at.isoformat(),
        "Gemeldet-am":       breach.reported_at.isoformat() if breach.reported_at else "",
        "Schweregrad":       breach.severity,
        "Betroffene-Daten":  breach.affected_data_types_display,
    },
))
# --- Ende DMS-Archivierung ---
'''

# ════════════════════════════════════════════════════════════════════════════
# 3. src/dsb/services/report_service.py
#    Ergänzung in: generate_jahresbericht(mandate_id, year, tenant_id, performed_by)
# ════════════════════════════════════════════════════════════════════════════

REPORT_SERVICE_PATCH = '''
# --- DMS-Archivierung des Jahresberichts ---
from src.dms_archive.services import DmsArchiveService, ArchiveRequest
from src.dms_archive.models import DmsArchiveRecord

DmsArchiveService.schedule_archival(ArchiveRequest(
    tenant_id    = mandate.tenant_id,
    source_type  = DmsArchiveRecord.DocumentType.JAHRESBERICHT,
    source_id    = report_record.id,    # UUID des gespeicherten Berichts
    source_label = f"DSB-Jahresbericht {year} {mandate.name}",
    performed_by = performed_by,
    dms_category = "DSGVO_JAHRESBERICHT",
    dms_properties = {
        "Mandant":   mandate.name,
        "Jahr":      str(year),
        "Erstellt":  timezone.now().isoformat(),
    },
))
# --- Ende DMS-Archivierung ---
'''

# ════════════════════════════════════════════════════════════════════════════
# 4. src/risk/services/assessment_service.py
#    Ergänzung in: finalize_assessment(assessment_id, tenant_id, performed_by)
# ════════════════════════════════════════════════════════════════════════════

ASSESSMENT_SERVICE_PATCH = '''
# --- DMS-Archivierung (nach Freigabe der Gefährdungsbeurteilung) ---
from src.dms_archive.services import DmsArchiveService, ArchiveRequest
from src.dms_archive.models import DmsArchiveRecord

DmsArchiveService.schedule_archival(ArchiveRequest(
    tenant_id    = assessment.tenant_id,
    source_type  = DmsArchiveRecord.DocumentType.RISK_ASSESSMENT,
    source_id    = assessment.id,
    source_label = f"Gefährdungsbeurteilung {assessment.title}",
    performed_by = performed_by,
    dms_category = "GB_BERICHT",
    dms_properties = {
        "Titel":       assessment.title,
        "Freigabe-am": assessment.finalized_at.isoformat(),
        "Bereich":     assessment.area or "",
        "Risiko-Stufe": assessment.risk_level,
    },
))
# --- Ende DMS-Archivierung ---
'''
