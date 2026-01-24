"""
NL2CAD Views - Natural Language to CAD Analysis.

Integriert die Handler-Pipeline für:
- CAD-Datei-Upload (IFC/DXF/DWG)
- Natural Language Queries
- Raum-Analyse & DIN 277
- Massenberechnung & GAEB
"""
import json
import logging

from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from .handlers import (
    CADFileInputHandler,
    NLQueryHandler,
    RoomAnalysisHandler,
    MassenHandler,
)
from .handlers.base import CADHandlerPipeline
from .handlers.nl_learning import get_learning_store
from .handlers.use_case_tracker import get_use_case_tracker
from .handlers.area_classifier import get_area_classifier, AreaCategory

logger = logging.getLogger(__name__)


class NL2CADView(TemplateView):
    """NL2CAD Hauptseite mit Chat-Interface."""
    template_name = "cad_hub/nl2cad/index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "NL2CAD - Natural Language CAD Analysis"
        return context


class NL2CADUploadView(View):
    """
    Upload und vollständige Analyse einer CAD-Datei.
    
    Führt die komplette Pipeline aus:
    1. CADFileInputHandler - Format-Erkennung & Konvertierung
    2. RoomAnalysisHandler - Raum-Extraktion & DIN 277
    3. MassenHandler - Flächen, Volumina, GAEB
    """
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "Keine Datei hochgeladen"}, status=400)
        
        uploaded_file = request.FILES["file"]
        filename = uploaded_file.name.lower()
        
        # Validate extension
        valid_extensions = [".ifc", ".dxf", ".dwg"]
        if not any(filename.endswith(ext) for ext in valid_extensions):
            return JsonResponse({
                "error": f"Ungültiges Format. Erlaubt: {', '.join(valid_extensions)}"
            }, status=400)
        
        try:
            content = uploaded_file.read()
            
            # Run pipeline
            pipeline = CADHandlerPipeline()
            pipeline.add(CADFileInputHandler())
            pipeline.add(RoomAnalysisHandler())
            pipeline.add(MassenHandler())
            
            results = pipeline.run({
                "file_content": content,
                "filename": uploaded_file.name,
                "classify_din277": True,
                "include_gaeb": True,
            })
            
            final = pipeline.get_final_result()
            
            return JsonResponse({
                "success": final["success"],
                "filename": uploaded_file.name,
                "data": final["data"],
                "handlers": final["handlers"],
                "errors": final["errors"],
                "warnings": final["warnings"],
            })
            
        except Exception as e:
            logger.exception(f"NL2CAD upload failed: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class NL2CADQueryView(View):
    """
    Natural Language Query auf geladene CAD-Daten.
    
    Erwartet:
    - query: Natürlichsprachliche Anfrage
    - file: Optional - CAD-Datei
    - use_llm: Optional - LLM für komplexe Queries
    """
    
    def post(self, request):
        try:
            # Get query from JSON body or form
            if request.content_type == "application/json":
                data = json.loads(request.body)
                query = data.get("query", "")
                use_llm = data.get("use_llm", False)
            else:
                query = request.POST.get("query", "")
                use_llm = request.POST.get("use_llm", "false").lower() == "true"
            
            if not query:
                return JsonResponse({"error": "Keine Anfrage angegeben"}, status=400)
            
            # Check for file
            file_content = None
            filename = None
            if "file" in request.FILES:
                file_content = request.FILES["file"].read()
                filename = request.FILES["file"].name
            
            # Build context
            context = {
                "query": query,
                "use_llm": use_llm,
            }
            
            # If file provided, run full pipeline
            if file_content:
                pipeline = CADHandlerPipeline()
                pipeline.add(CADFileInputHandler())
                pipeline.add(NLQueryHandler())
                
                results = pipeline.run({
                    "file_content": file_content,
                    "filename": filename,
                    "query": query,
                    "use_llm": use_llm,
                })
                
                final = pipeline.get_final_result()
                
                return JsonResponse({
                    "success": final["success"],
                    "query": query,
                    "response": final["data"].get("response", ""),
                    "intent": final["data"].get("intent", "unknown"),
                    "data": final["data"],
                })
            
            # Query only (no file)
            handler = NLQueryHandler(context=context)
            result = handler.run({"query": query, "use_llm": use_llm})
            
            return JsonResponse({
                "success": result.success,
                "query": query,
                "response": result.data.get("response", ""),
                "intent": result.data.get("intent", "unknown"),
                "confidence": result.data.get("confidence", 0),
                "next_handler": result.data.get("next_handler", ""),
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Ungültiges JSON"}, status=400)
        except Exception as e:
            logger.exception(f"NL2CAD query failed: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class NL2CADRoomsView(View):
    """Raum-Analyse API."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "Keine Datei"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            filename = request.FILES["file"].name
            
            pipeline = CADHandlerPipeline()
            pipeline.add(CADFileInputHandler())
            pipeline.add(RoomAnalysisHandler())
            
            pipeline.run({
                "file_content": content,
                "filename": filename,
                "classify_din277": True,
            })
            
            final = pipeline.get_final_result()
            
            return JsonResponse({
                "success": final["success"],
                "rooms": final["data"].get("rooms", []),
                "room_count": final["data"].get("room_count", 0),
                "total_area": final["data"].get("total_area", 0),
                "din277_summary": final["data"].get("din277_summary", {}),
                "doors": final["data"].get("doors", []),
                "windows": final["data"].get("windows", []),
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class NL2CADMassenView(View):
    """Massenberechnung API."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "Keine Datei"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            filename = request.FILES["file"].name
            wall_height = float(request.POST.get("wall_height", 2.5))
            
            pipeline = CADHandlerPipeline()
            pipeline.add(CADFileInputHandler())
            pipeline.add(RoomAnalysisHandler())
            pipeline.add(MassenHandler())
            
            pipeline.run({
                "file_content": content,
                "filename": filename,
                "wall_height": wall_height,
                "include_gaeb": True,
            })
            
            final = pipeline.get_final_result()
            
            return JsonResponse({
                "success": final["success"],
                "categories": final["data"].get("categories", {}),
                "summary": final["data"].get("summary", {}),
                "gaeb_positions": final["data"].get("gaeb_positions", []),
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class NL2CADGAEBExportView(View):
    """GAEB X84 Export."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "Keine Datei"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            filename = request.FILES["file"].name
            
            pipeline = CADHandlerPipeline()
            pipeline.add(CADFileInputHandler())
            pipeline.add(RoomAnalysisHandler())
            pipeline.add(MassenHandler())
            
            pipeline.run({
                "file_content": content,
                "filename": filename,
                "include_gaeb": True,
            })
            
            final = pipeline.get_final_result()
            gaeb_positions = final["data"].get("gaeb_positions", [])
            
            # Generate simple GAEB-like structure
            gaeb_data = {
                "header": {
                    "project": filename,
                    "format": "GAEB X84 (simplified)",
                },
                "positions": gaeb_positions,
                "summary": final["data"].get("summary", {}),
            }
            
            return JsonResponse({
                "success": True,
                "gaeb": gaeb_data,
                "position_count": len(gaeb_positions),
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class NL2CADUseCasesView(View):
    """
    Use Case Tracking API - Erfasst Feature Requests.
    
    POST: Neuen Feature Request melden
    GET: Use Cases und Statistiken abrufen
    """
    
    def post(self, request):
        """Meldet neuen Feature Request."""
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = request.POST
            
            title = data.get("title", "").strip()
            description = data.get("description", "").strip()
            query = data.get("query", "").strip()
            tags = data.get("tags", [])
            
            if not title:
                return JsonResponse({"error": "Titel erforderlich"}, status=400)
            
            tracker = get_use_case_tracker()
            uc = tracker.report_feature_request(
                title=title,
                description=description or f"Feature Request: {title}",
                query=query,
                tags=tags if isinstance(tags, list) else [tags] if tags else []
            )
            
            return JsonResponse({
                "success": True,
                "message": f"Feature Request erfasst: {title}",
                "use_case": uc.to_dict(),
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    def get(self, request):
        """Gibt Use Cases und Statistiken zurück."""
        try:
            tracker = get_use_case_tracker()
            stats = tracker.get_stats()
            
            status_filter = request.GET.get("status")
            priority_filter = request.GET.get("priority")
            
            use_cases = tracker.list_use_cases(
                status=status_filter,
                priority=priority_filter,
                limit=20
            )
            
            return JsonResponse({
                "success": True,
                "stats": stats,
                "use_cases": [uc.to_dict() for uc in use_cases],
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class NL2CADClassifierView(View):
    """
    Area Classifier API - Layer-Klassifizierung und Lernen.
    
    POST: Klassifizierung korrigieren/lernen
    GET: Klassifizierung testen + Statistiken
    """
    
    def post(self, request):
        """Lernt neue Layer-Klassifizierung."""
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = request.POST
            
            layer_name = data.get("layer_name", "").strip()
            category = data.get("category", "").strip()
            
            if not layer_name or not category:
                return JsonResponse({"error": "layer_name und category erforderlich"}, status=400)
            
            valid_categories = [c.value for c in AreaCategory]
            if category not in valid_categories:
                return JsonResponse({
                    "error": f"Ungültige Kategorie. Erlaubt: {', '.join(valid_categories)}"
                }, status=400)
            
            classifier = get_area_classifier()
            classifier.learn(layer_name, category, confidence=1.0, source="user")
            
            return JsonResponse({
                "success": True,
                "message": f"Gelernt: '{layer_name}' → {category}",
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    def get(self, request):
        """Klassifiziert Layer oder gibt Statistiken zurück."""
        try:
            classifier = get_area_classifier()
            layer_name = request.GET.get("layer")
            
            if layer_name:
                category, confidence = classifier.classify(layer_name)
                return JsonResponse({
                    "layer_name": layer_name,
                    "category": category.value,
                    "confidence": confidence,
                })
            
            # Statistiken
            stats = classifier.get_stats()
            return JsonResponse({
                "success": True,
                "stats": stats,
                "categories": [c.value for c in AreaCategory],
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class NL2CADLearnView(View):
    """
    Learning API - Speichert Query-Intent Paare.
    
    POST: Neues Pattern lernen
    GET: Statistiken und gelernte Patterns
    """
    
    def post(self, request):
        """Lernt neues Query-Intent Paar."""
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = request.POST
            
            query = data.get("query", "").strip()
            intent = data.get("intent", "").strip()
            
            if not query or not intent:
                return JsonResponse({
                    "error": "query und intent erforderlich"
                }, status=400)
            
            # Valid intents
            valid_intents = [
                "room_list", "room_area", "total_area", "layer_info",
                "entity_count", "dimension_info", "door_count", 
                "window_count", "quality_check", "export"
            ]
            
            if intent not in valid_intents:
                return JsonResponse({
                    "error": f"Ungültiger Intent. Erlaubt: {', '.join(valid_intents)}"
                }, status=400)
            
            store = get_learning_store()
            pattern = store.learn(query, intent, source="user_feedback")
            
            return JsonResponse({
                "success": True,
                "message": f"Gelernt: '{query}' → {intent}",
                "pattern": pattern.to_dict(),
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    def get(self, request):
        """Gibt Lern-Statistiken zurück."""
        try:
            store = get_learning_store()
            stats = store.get_stats()
            
            return JsonResponse({
                "success": True,
                "stats": {
                    "total_patterns": stats["total_patterns"],
                    "intents": stats["intents"],
                },
                "recent_patterns": [
                    p.to_dict() for p in stats.get("most_used", [])[:10]
                ],
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
