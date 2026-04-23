"""
Sphinx Export Views
===================

UI für Sphinx → Markdown Export.
"""

import os
from pathlib import Path
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods

from .services import get_sphinx_export_service, ExportResult
from .sync_service import get_sphinx_sync_service


def dashboard(request):
    """
    Sphinx Export Dashboard.
    Zeigt verfügbare Dokumentationsprojekte, Export-Optionen und Sync-Status.
    """
    service = get_sphinx_export_service()
    sync_service = get_sphinx_sync_service()
    
    # Bekannte Sphinx-Projekte im Repo
    projects = []
    
    # docs/source - Hauptdokumentation
    docs_path = settings.BASE_DIR / 'docs' / 'source'
    if docs_path.exists():
        valid, errors = service.validate_project(str(docs_path))
        doc_count = len(service.list_documents(str(docs_path))) if valid else 0
        projects.append({
            'name': 'BF Agent Documentation',
            'path': 'docs/source',
            'valid': valid,
            'errors': errors,
            'doc_count': doc_count,
            'description': 'Hauptdokumentation des BF Agent Frameworks',
        })
    
    # docs_v2 - falls vorhanden
    docs_v2_path = settings.BASE_DIR / 'docs_v2'
    if docs_v2_path.exists() and (docs_v2_path / 'source' / 'conf.py').exists():
        v2_source = docs_v2_path / 'source'
        valid, errors = service.validate_project(str(v2_source))
        doc_count = len(service.list_documents(str(v2_source))) if valid else 0
        projects.append({
            'name': 'Documentation V2',
            'path': 'docs_v2/source',
            'valid': valid,
            'errors': errors,
            'doc_count': doc_count,
            'description': 'Neue Dokumentationsstruktur',
        })
    
    # Letzte Exports (aus temp-Verzeichnis)
    recent_exports = []
    export_dir = Path('/tmp')
    for f in sorted(export_dir.glob('bf_*.md'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
        recent_exports.append({
            'name': f.name,
            'path': str(f),
            'size': f.stat().st_size,
            'modified': f.stat().st_mtime,
        })
    
    # Sync Status holen (schneller Check ohne Docstrings)
    sync_report = None
    try:
        sync_report = sync_service.check_changes(check_docstrings=False)
    except Exception:
        pass
    
    context = {
        'projects': projects,
        'recent_exports': recent_exports,
        'sync_report': sync_report,
        'page_title': 'Sphinx Export & Sync',
    }
    
    return render(request, 'sphinx_export/dashboard.html', context)


@require_http_methods(["POST"])
def export_project(request):
    """
    Exportiert ein Sphinx-Projekt zu Markdown.
    """
    source_path = request.POST.get('source_path', 'docs/source')
    title = request.POST.get('title', 'Documentation')
    include_toc = request.POST.get('include_toc', 'on') == 'on'
    include_api = request.POST.get('include_api', 'on') == 'on'
    
    # Generiere Ausgabepfad
    import time
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    output_filename = f"bf_export_{timestamp}.md"
    output_path = f"/tmp/{output_filename}"
    
    service = get_sphinx_export_service()
    result = service.export_to_markdown(
        source_path,
        output_path=output_path,
        title=title,
        include_toc=include_toc,
        include_api=include_api,
    )
    
    if result.success:
        messages.success(
            request,
            f"✅ Export erfolgreich: {result.metadata.pages_count} Seiten, "
            f"{result.metadata.word_count:,} Wörter in {result.metadata.duration_seconds:.1f}s"
        )
        
        # Redirect mit Download-Option
        return redirect(f'/sphinx-export/download/?file={output_filename}')
    else:
        messages.error(request, f"❌ Export fehlgeschlagen: {result.error}")
        return redirect('sphinx_export:dashboard')


def download_export(request):
    """
    Download einer exportierten Markdown-Datei.
    """
    filename = request.GET.get('file', '')
    
    # Sicherheitscheck: nur Dateien aus /tmp mit bf_ Prefix
    if not filename.startswith('bf_') or '..' in filename:
        messages.error(request, "Ungültige Datei")
        return redirect('sphinx_export:dashboard')
    
    filepath = Path('/tmp') / filename
    
    if not filepath.exists():
        messages.error(request, "Datei nicht gefunden")
        return redirect('sphinx_export:dashboard')
    
    # Zeige Download-Seite mit Preview
    content = filepath.read_text(encoding='utf-8')
    
    # Ersten 5000 Zeichen als Preview
    preview = content[:5000]
    if len(content) > 5000:
        preview += "\n\n... [Vorschau gekürzt] ..."
    
    context = {
        'filename': filename,
        'filepath': str(filepath),
        'filesize': filepath.stat().st_size,
        'preview': preview,
        'word_count': len(content.split()),
        'page_title': f'Download: {filename}',
    }
    
    return render(request, 'sphinx_export/download.html', context)


def download_file(request):
    """
    Direkter Datei-Download.
    """
    filename = request.GET.get('file', '')
    
    if not filename.startswith('bf_') or '..' in filename:
        return HttpResponse("Ungültige Datei", status=400)
    
    filepath = Path('/tmp') / filename
    
    if not filepath.exists():
        return HttpResponse("Datei nicht gefunden", status=404)
    
    response = FileResponse(
        open(filepath, 'rb'),
        content_type='text/markdown',
        as_attachment=True,
        filename=filename
    )
    return response


def list_documents(request):
    """
    API: Listet Dokumente eines Projekts.
    """
    source_path = request.GET.get('path', 'docs/source')
    
    service = get_sphinx_export_service()
    
    try:
        docs = service.list_documents(source_path)
        return JsonResponse({
            'success': True,
            'count': len(docs),
            'documents': docs[:50],  # Max 50
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=400)


def validate_project(request):
    """
    API: Validiert ein Sphinx-Projekt.
    """
    source_path = request.GET.get('path', 'docs/source')
    
    service = get_sphinx_export_service()
    valid, errors = service.validate_project(source_path)
    
    return JsonResponse({
        'valid': valid,
        'errors': errors,
    })


# ============================================================================
# SYNC VIEWS
# ============================================================================

def sync_status(request):
    """
    API: Holt aktuellen Sync-Status.
    """
    sync_service = get_sphinx_sync_service()
    
    try:
        check_docstrings = request.GET.get('docstrings', 'false') == 'true'
        report = sync_service.check_changes(check_docstrings=check_docstrings)
        
        return JsonResponse({
            'success': True,
            'has_changes': report.has_changes,
            'total_issues': report.total_issues,
            'python_changes': len(report.python_changes),
            'doc_changes': len(report.doc_changes),
            'missing_docs': len(report.missing_docs),
            'outdated_docs': len(report.outdated_docs),
            'undocumented': len(report.undocumented_items),
            'suggestions': report.suggestions,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@require_http_methods(["POST"])
def run_sync(request):
    """
    Führt Sphinx-Synchronisation aus.
    """
    action = request.POST.get('action', 'check')
    sync_service = get_sphinx_sync_service()
    
    try:
        if action == 'check':
            # Nur prüfen
            report = sync_service.check_changes(check_docstrings=True)
            messages.info(
                request,
                f"📊 Sync-Check: {report.total_issues} Issues gefunden "
                f"({len(report.python_changes)} Python, {len(report.missing_docs)} fehlende Doku)"
            )
            
        elif action == 'generate-stubs':
            # Stubs generieren
            generated = sync_service.generate_missing_stubs(dry_run=False)
            if generated:
                messages.success(request, f"✅ {len(generated)} autodoc-Stubs generiert")
            else:
                messages.info(request, "✅ Keine fehlenden Stubs gefunden")
                
        elif action == 'rebuild':
            # Dokumentation neu bauen
            success, output = sync_service.rebuild_docs()
            if success:
                messages.success(request, "✅ Sphinx-Dokumentation erfolgreich gebaut")
            else:
                messages.error(request, f"❌ Build fehlgeschlagen: {output[:200]}")
                
        elif action == 'full-sync':
            # Vollständige Sync
            report = sync_service.check_changes()
            
            # Stubs generieren wenn nötig
            stubs = []
            if report.missing_docs:
                stubs = sync_service.generate_missing_stubs(dry_run=False)
            
            # Rebuild
            success, _ = sync_service.rebuild_docs()
            
            messages.success(
                request,
                f"✅ Full Sync: {len(stubs)} Stubs generiert, "
                f"Build {'erfolgreich' if success else 'fehlgeschlagen'}"
            )
        
        return redirect('sphinx_export:dashboard')
        
    except Exception as e:
        messages.error(request, f"❌ Sync-Fehler: {str(e)}")
        return redirect('sphinx_export:dashboard')


def sync_report(request):
    """
    Zeigt detaillierten Sync-Report als Markdown.
    """
    sync_service = get_sphinx_sync_service()
    
    try:
        report = sync_service.check_changes(check_docstrings=True)
        markdown = report.to_markdown()
        
        context = {
            'report': report,
            'markdown': markdown,
            'page_title': 'Sphinx Sync Report',
        }
        
        return render(request, 'sphinx_export/sync_report.html', context)
        
    except Exception as e:
        messages.error(request, f"❌ Report-Fehler: {str(e)}")
        return redirect('sphinx_export:dashboard')
