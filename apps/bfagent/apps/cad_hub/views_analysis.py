# apps/cad_hub/views_analysis.py
"""
CAD Analysis Views - Datenfluss-Szenarien
==========================================

Implementiert die 4 Hauptanwendungsszenarien:
1. Format-Analyse Dashboard (IFC-Upload mit Auto-Analyse)
2. DXF Qualitätsprüfung (Maßketten + Schnitte)
3. NL2CAD Query (Natural Language)
4. Batch-Analyse (Multi-Format)
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from asgiref.sync import async_to_sync
from django.conf import settings


def run_async(coro):
    """
    Führt eine Coroutine synchron aus.
    Funktioniert auch in Django's Thread-Umgebung.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Event loop läuft bereits - neuen erstellen
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # Kein Event Loop vorhanden - neuen erstellen
        return asyncio.run(coro)


from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView, DetailView, FormView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .models import IFCModel, Room, Door, Window, Floor
from .services.mcp_bridge import (
    get_mcp_bridge,
    CADFormat,
    AnalysisResult,
    DXFQualityResult,
    NLQueryResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Szenario 1: Format-Analyse Dashboard
# =============================================================================

class FormatAnalyzerView(LoginRequiredMixin, TemplateView):
    """
    Format-Analyse Dashboard
    
    URL: /cad-hub/analyze/
    
    Features:
    - Datei-Upload (Drag & Drop)
    - Auto-Format-Erkennung
    - Analyse-Ergebnis anzeigen
    - Historie der letzten Analysen
    """
    template_name = "cad_hub/analysis/format_analyzer.html"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Unterstützte Formate
        bridge = get_mcp_bridge()
        ctx["supported_formats"] = run_async(bridge.get_supported_formats())
        
        # Letzte Analysen aus Session
        ctx["recent_analyses"] = self.request.session.get("recent_analyses", [])[:5]
        
        return ctx


class FormatAnalyzeAPIView(LoginRequiredMixin, View):
    """
    API Endpoint für Datei-Analyse
    
    URL: /cad-hub/analyze/api/
    
    POST: Datei hochladen und analysieren
    """
    
    def post(self, request):
        """Datei analysieren"""
        uploaded_file = request.FILES.get("file")
        
        if not uploaded_file:
            return JsonResponse({"success": False, "error": "Keine Datei hochgeladen"}, status=400)
        
        # Datei temporär speichern
        file_path = default_storage.save(
            f"cad_uploads/{uploaded_file.name}",
            ContentFile(uploaded_file.read())
        )
        full_path = Path(default_storage.path(file_path))
        
        try:
            # Analyse durchführen
            bridge = get_mcp_bridge()
            result = run_async(bridge.analyze_file(str(full_path)))
            
            # In Session speichern für Historie
            recent = request.session.get("recent_analyses", [])
            recent.insert(0, {
                "file_name": uploaded_file.name,
                "format": result.format.value,
                "success": result.success,
                "timestamp": str(asyncio.get_event_loop().time()),
            })
            request.session["recent_analyses"] = recent[:10]
            
            return JsonResponse({
                "success": result.success,
                "file_name": uploaded_file.name,
                "format": result.format.value,
                "data": result.data,
                "markdown_report": result.markdown_report,
                "errors": result.errors,
                "warnings": result.warnings,
            })
            
        except Exception as e:
            logger.exception(f"Analyse fehlgeschlagen: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)
        
        finally:
            # Temporäre Datei löschen
            if full_path.exists():
                full_path.unlink()


# =============================================================================
# Szenario 2: DXF Qualitätsprüfung
# =============================================================================

class DXFQualityView(LoginRequiredMixin, TemplateView):
    """
    DXF Qualitätsprüfung Dashboard
    
    URL: /cad-hub/dxf-quality/
    
    Features:
    - DXF-Upload
    - Maßketten-Analyse
    - Schnittdarstellungen
    - Qualitäts-Score
    """
    template_name = "cad_hub/analysis/dxf_quality.html"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["quality_checks"] = [
            {"name": "Maßketten", "description": "Prüft Kettenbemaßung auf Vollständigkeit und Überbestimmung"},
            {"name": "Schnittdarstellungen", "description": "Erkennt Schnitte und ordnet Materialien zu"},
            {"name": "Layer-Struktur", "description": "Prüft Namenskonventionen und Organisation"},
        ]
        
        # Prüfe ob DWG-Konvertierung verfügbar ist
        ctx["dwg_supported"] = self._check_dwg_support()
        
        return ctx
    
    def _check_dwg_support(self) -> bool:
        """Prüft ob DWG-Dateien konvertiert werden können."""
        try:
            # Prüfe ezdxf odafc addon
            from ezdxf.addons import odafc
            return True
        except ImportError:
            pass
        
        # Prüfe ODA File Converter
        import shutil
        if shutil.which("ODAFileConverter"):
            return True
        
        # Prüfe bekannte Pfade
        from pathlib import Path
        known_paths = [
            r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
            r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
        ]
        for path in known_paths:
            if Path(path).exists():
                return True
        
        return False


class DXFQualityAPIView(LoginRequiredMixin, View):
    """
    API für DXF-Qualitätsprüfung
    
    URL: /cad-hub/dxf-quality/api/
    """
    
    def post(self, request):
        """DXF-Qualität prüfen"""
        uploaded_file = request.FILES.get("file")
        
        if not uploaded_file:
            return JsonResponse({"success": False, "error": "Keine DXF-Datei hochgeladen"}, status=400)
        
        if not uploaded_file.name.lower().endswith((".dxf", ".dwg")):
            return JsonResponse({"success": False, "error": "Nur DXF/DWG-Dateien erlaubt"}, status=400)
        
        # Datei temporär speichern
        file_path = default_storage.save(
            f"cad_uploads/{uploaded_file.name}",
            ContentFile(uploaded_file.read())
        )
        full_path = Path(default_storage.path(file_path))
        
        try:
            bridge = get_mcp_bridge()
            result = run_async(bridge.check_dxf_quality(str(full_path)))
            
            return JsonResponse({
                "success": result.success,
                "file_name": uploaded_file.name,
                "quality_score": result.quality_score,
                "dimension_chains": result.dimension_chains,
                "section_views": result.section_views,
                "issues": result.issues,
            })
            
        except Exception as e:
            logger.exception(f"DXF-Qualitätsprüfung fehlgeschlagen: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)
        
        finally:
            if full_path.exists():
                full_path.unlink()


class DXFQualityModelView(LoginRequiredMixin, DetailView):
    """
    DXF-Qualitätsprüfung für ein existierendes Modell
    
    URL: /cad-hub/model/<uuid>/dxf-quality/
    """
    model = IFCModel
    template_name = "cad_hub/analysis/dxf_quality_model.html"
    context_object_name = "model"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Hier könnte man bereits gespeicherte DXF-Analysen laden
        ctx["has_dxf"] = False  # Prüfen ob DXF verfügbar
        return ctx


# =============================================================================
# Szenario 3: Natural Language Query
# =============================================================================

class NL2CADQueryView(LoginRequiredMixin, TemplateView):
    """
    NL2CAD Query Interface
    
    URL: /cad-hub/nl-query/
    
    Features:
    - Freitext-Eingabe
    - Modell-Auswahl
    - Chat-ähnliche Antworten
    - Beispiel-Fragen
    """
    template_name = "cad_hub/analysis/nl_query.html"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Verfügbare Modelle
        ctx["models"] = IFCModel.objects.select_related("project").order_by("-created_at")[:20]
        
        # Beispiel-Fragen
        ctx["example_questions"] = [
            "Welcher Raum ist am größten?",
            "Wie viele Türen gibt es?",
            "Gesamtfläche aller Räume?",
            "Liste alle Räume im 1. OG",
            "Welcher Raum ist am kleinsten?",
            "Wie viele Fenster hat das Gebäude?",
        ]
        
        # Chat-Historie aus Session
        ctx["chat_history"] = self.request.session.get("nl_chat_history", [])[-10:]
        
        return ctx


class NL2CADQueryAPIView(LoginRequiredMixin, View):
    """
    API für NL2CAD Queries
    
    URL: /cad-hub/nl-query/api/
    """
    
    def post(self, request):
        """Natural Language Query ausführen"""
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST
        
        question = data.get("question", "").strip()
        model_id = data.get("model_id")
        
        if not question:
            return JsonResponse({"success": False, "error": "Keine Frage gestellt"}, status=400)
        
        try:
            bridge = get_mcp_bridge()
            
            # Model ID in UUID konvertieren
            model_uuid = UUID(model_id) if model_id else None
            
            result = run_async(bridge.query_natural_language(
                question=question,
                model_id=model_uuid
            ))
            
            # Chat-Historie aktualisieren
            history = request.session.get("nl_chat_history", [])
            history.append({
                "question": question,
                "answer": result.answer,
                "success": result.success,
                "model_id": model_id,
            })
            request.session["nl_chat_history"] = history[-20:]
            
            return JsonResponse({
                "success": result.success,
                "question": result.query,
                "answer": result.answer,
                "data": result.data,
                "confidence": result.confidence,
            })
            
        except Exception as e:
            logger.exception(f"NL Query fehlgeschlagen: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)


class NL2CADModelQueryView(LoginRequiredMixin, DetailView):
    """
    NL Query für spezifisches Modell
    
    URL: /cad-hub/model/<uuid>/query/
    """
    model = IFCModel
    template_name = "cad_hub/analysis/nl_query_model.html"
    context_object_name = "model"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Modell-Statistiken für Kontext
        model = self.object
        ctx["stats"] = {
            "room_count": Room.objects.filter(ifc_model=model).count(),
            "door_count": Door.objects.filter(ifc_model=model).count(),
            "window_count": Window.objects.filter(ifc_model=model).count(),
            "floor_count": Floor.objects.filter(ifc_model=model).count(),
        }
        
        # Beispiel-Fragen
        ctx["example_questions"] = [
            "Welcher Raum ist am größten?",
            "Wie viele Türen gibt es?",
            "Gesamtfläche aller Räume?",
            "Liste alle Räume",
        ]
        
        return ctx


# =============================================================================
# Szenario 4: Batch-Analyse
# =============================================================================

class BatchAnalyzeView(LoginRequiredMixin, TemplateView):
    """
    Batch-Analyse Dashboard
    
    URL: /cad-hub/batch-analyze/
    
    Features:
    - Verzeichnis-Auswahl
    - Multi-File Upload
    - Format-Filter
    - Zusammenfassung
    """
    template_name = "cad_hub/analysis/batch_analyze.html"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        ctx["supported_extensions"] = [
            ".ifc", ".dxf", ".dwg", ".igs", ".iges", 
            ".fbx", ".gltf", ".glb", ".3mf", ".ply"
        ]
        
        # Letzte Batch-Jobs
        ctx["recent_batches"] = self.request.session.get("recent_batches", [])[:5]
        
        return ctx


class BatchAnalyzeAPIView(LoginRequiredMixin, View):
    """
    API für Batch-Analyse
    
    URL: /cad-hub/batch-analyze/api/
    """
    
    def post(self, request):
        """Batch-Analyse durchführen"""
        files = request.FILES.getlist("files")
        
        if not files:
            return JsonResponse({"success": False, "error": "Keine Dateien hochgeladen"}, status=400)
        
        results = []
        bridge = get_mcp_bridge()
        
        for uploaded_file in files:
            # Datei temporär speichern
            file_path = default_storage.save(
                f"cad_uploads/batch/{uploaded_file.name}",
                ContentFile(uploaded_file.read())
            )
            full_path = Path(default_storage.path(file_path))
            
            try:
                result = run_async(bridge.analyze_file(str(full_path)))
                results.append({
                    "file_name": uploaded_file.name,
                    "success": result.success,
                    "format": result.format.value,
                    "data": result.data,
                    "errors": result.errors,
                })
            except Exception as e:
                results.append({
                    "file_name": uploaded_file.name,
                    "success": False,
                    "error": str(e),
                })
            finally:
                if full_path.exists():
                    full_path.unlink()
        
        # Zusammenfassung
        successful = len([r for r in results if r.get("success")])
        failed = len(results) - successful
        
        # In Session speichern
        batches = request.session.get("recent_batches", [])
        batches.insert(0, {
            "total": len(results),
            "successful": successful,
            "failed": failed,
        })
        request.session["recent_batches"] = batches[:10]
        
        return JsonResponse({
            "success": failed == 0,
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "results": results,
        })


# =============================================================================
# Utility Views
# =============================================================================

class SupportedFormatsView(View):
    """
    API: Liste aller unterstützten Formate
    
    URL: /cad-hub/formats/
    """
    
    def get(self, request):
        bridge = get_mcp_bridge()
        formats = run_async(bridge.get_supported_formats())
        return JsonResponse(formats)


class AnalysisDashboardView(LoginRequiredMixin, TemplateView):
    """
    Haupt-Dashboard für alle Analyse-Funktionen
    
    URL: /cad-hub/analysis/
    """
    template_name = "cad_hub/analysis/dashboard.html"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        ctx["scenarios"] = [
            {
                "name": "Format-Analyse",
                "description": "CAD-Dateien analysieren (IFC, DXF, IGES, FBX, ...)",
                "icon": "bi-file-earmark-code",
                "url": "cad_hub:format_analyzer",
                "color": "primary",
            },
            {
                "name": "DXF Qualität",
                "description": "Maßketten und Schnittdarstellungen prüfen",
                "icon": "bi-rulers",
                "url": "cad_hub:dxf_quality",
                "color": "warning",
            },
            {
                "name": "CAD Assistent",
                "description": "Fragen in natürlicher Sprache stellen",
                "icon": "bi-chat-dots",
                "url": "cad_hub:nl_query",
                "color": "success",
            },
            {
                "name": "Batch-Analyse",
                "description": "Mehrere Dateien gleichzeitig analysieren",
                "icon": "bi-collection",
                "url": "cad_hub:batch_analyze",
                "color": "info",
            },
        ]
        
        # Statistiken
        ctx["stats"] = {
            "total_models": IFCModel.objects.count(),
            "total_rooms": Room.objects.count(),
            "recent_analyses": len(self.request.session.get("recent_analyses", [])),
        }
        
        return ctx
