"""
DXF Viewer Views for CAD Hub
"""
import json
import logging
import tempfile
from pathlib import Path

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from .services import (
    DXFParserService,
    DXFRendererService,
    NL2DXFGenerator,
    DWGConverterService,
    CADLoaderService,
    get_dwg_converter_status,
    parse_dxf,
)

logger = logging.getLogger(__name__)


class DXFViewerView(TemplateView):
    """Main DXF Viewer page with upload and viewer."""
    template_name = "cad_hub/dxf/viewer.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "DXF Viewer"
        return context


class DXFUploadView(View):
    """Handle DXF/DWG file upload and return JSON data for viewer."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        uploaded_file = request.FILES["file"]
        filename_lower = uploaded_file.name.lower()
        
        if not (filename_lower.endswith(".dxf") or filename_lower.endswith(".dwg")):
            return JsonResponse({"error": "Only DXF/DWG files allowed"}, status=400)
        
        try:
            # Read file content
            content = uploaded_file.read()
            
            # Handle DWG conversion
            if filename_lower.endswith(".dwg"):
                logger.info(f"Converting DWG file: {uploaded_file.name}")
                converter = DWGConverterService()
                available = converter.get_available_methods()
                
                # Check if any local converter is available
                if not any(m in available for m in ['oda', 'libredwg']):
                    return JsonResponse({
                        "error": (
                            "DWG-Konvertierung nicht verfügbar.\n\n"
                            "Bitte installieren Sie ODA File Converter:\n"
                            "https://www.opendesign.com/guestfiles/oda_file_converter\n\n"
                            "Oder konvertieren Sie die Datei vorher zu DXF."
                        ),
                        "hint": "DXF-Dateien werden direkt unterstützt"
                    }, status=400)
                
                conversion_result = converter.convert_bytes_to_dxf(content, uploaded_file.name)
                
                if not conversion_result.success:
                    return JsonResponse({
                        "error": f"DWG-Konvertierung fehlgeschlagen: {conversion_result.error}"
                    }, status=400)
                
                content = conversion_result.dxf_content
                logger.info(f"DWG converted using method: {conversion_result.method}")
            
            # Render to JSON for viewer
            renderer = DXFRendererService()
            if not renderer.load_bytes(content):
                return JsonResponse({"error": "Could not parse DXF file"}, status=400)
            
            # Get Three.js optimized export
            viewer_data = renderer.export_for_threejs()
            
            if not viewer_data:
                return JsonResponse({"error": "Could not extract geometry"}, status=400)
            
            # Also get SVG thumbnail
            svg_thumbnail = renderer.get_thumbnail_svg(max_size=300)
            
            return JsonResponse({
                "success": True,
                "filename": uploaded_file.name,
                "data": viewer_data,
                "thumbnail_svg": svg_thumbnail
            })
            
        except Exception as e:
            logger.error(f"DXF/DWG upload failed: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class DXFRenderSVGView(View):
    """Render uploaded DXF to SVG."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        uploaded_file = request.FILES["file"]
        content = uploaded_file.read()
        
        renderer = DXFRendererService()
        if not renderer.load_bytes(content):
            return HttpResponse("Could not parse DXF", status=400)
        
        svg_content = renderer.render_to_svg(width=1200, height=900)
        
        if svg_content:
            return HttpResponse(svg_content, content_type="image/svg+xml")
        else:
            return HttpResponse("Rendering failed", status=500)


class DXFParseView(View):
    """Parse DXF and return structured data."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        uploaded_file = request.FILES["file"]
        content = uploaded_file.read()
        
        parser = DXFParserService()
        try:
            result = parser.parse_bytes(content, uploaded_file.name)
            
            # Extract room candidates
            rooms = parser.extract_room_candidates(result)
            
            return JsonResponse({
                "success": True,
                "filename": uploaded_file.name,
                "statistics": {
                    "lines": len(result.lines),
                    "circles": len(result.circles),
                    "arcs": len(result.arcs),
                    "polylines": len(result.polylines),
                    "texts": len(result.texts),
                    "layers": len(result.layers),
                    "total": result.total_entities
                },
                "layers": [l.to_dict() for l in result.layers],
                "extents": result.extents,
                "rooms": rooms[:20]  # Top 20 room candidates
            })
            
        except Exception as e:
            logger.error(f"DXF parse failed: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class NL2DXFView(TemplateView):
    """Natural Language to DXF generator page."""
    template_name = "cad_hub/dxf/nl2dxf.html"


class NL2DXFGenerateView(View):
    """Generate DXF from natural language description."""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            description = data.get("description", "")
            use_llm = data.get("use_llm", False)
            
            if not description:
                return JsonResponse({"error": "Description required"}, status=400)
            
            generator = NL2DXFGenerator()
            result = generator.generate(description, use_llm=use_llm)
            
            if not result.success:
                return JsonResponse({"error": result.error}, status=400)
            
            # Read the generated DXF and convert to viewer format
            renderer = DXFRendererService()
            if renderer.load_file(result.filepath):
                viewer_data = renderer.export_for_threejs()
                svg_thumbnail = renderer.get_thumbnail_svg(max_size=300)
                
                # Read DXF content for download
                with open(result.filepath, 'r') as f:
                    dxf_content = f.read()
                
                return JsonResponse({
                    "success": True,
                    "commands": [cmd.command for cmd in result.commands],
                    "data": viewer_data,
                    "thumbnail_svg": svg_thumbnail,
                    "dxf_content": dxf_content
                })
            else:
                return JsonResponse({"error": "Could not read generated DXF"}, status=500)
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"NL2DXF generation failed: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class DXFDownloadView(View):
    """Download generated DXF file."""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            dxf_content = data.get("dxf_content", "")
            filename = data.get("filename", "generated.dxf")
            
            if not dxf_content:
                return JsonResponse({"error": "No DXF content"}, status=400)
            
            response = HttpResponse(dxf_content, content_type="application/dxf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# =============================================================================
# ANALYSE VIEWS (using CADLoaderService)
# =============================================================================

class DXFAnalysisView(TemplateView):
    """DXF Analysis Dashboard."""
    template_name = "cad_hub/dxf/analysis.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "DXF Analyse"
        context["dwg_status"] = get_dwg_converter_status()
        return context


class DXFAnalyzeUploadView(View):
    """Analyze uploaded DXF/DWG file."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        uploaded_file = request.FILES["file"]
        filename_lower = uploaded_file.name.lower()
        
        if not (filename_lower.endswith(".dxf") or filename_lower.endswith(".dwg")):
            return JsonResponse({"error": "Only DXF/DWG files allowed"}, status=400)
        
        try:
            content = uploaded_file.read()
            loader = CADLoaderService.from_bytes(content, uploaded_file.name)
            
            # Full analysis
            analysis = loader.get_analysis_dict()
            
            # Viewer data for 3D preview
            viewer_data = loader.get_viewer_data()
            
            # Floor plan specific
            rooms = loader.get_rooms()
            room_areas = loader.get_room_areas()
            doors = loader.get_doors()
            windows = loader.get_windows()
            
            # Quality check
            quality_issues = loader.check_quality()
            
            # Thumbnail
            thumbnail = loader.get_thumbnail(max_size=400)
            
            return JsonResponse({
                "success": True,
                "filename": uploaded_file.name,
                "analysis": analysis,
                "viewer_data": viewer_data,
                "floor_plan": {
                    "rooms": rooms,
                    "room_areas": room_areas[:20],
                    "doors": doors,
                    "windows": windows,
                },
                "quality": quality_issues,
                "thumbnail_svg": thumbnail,
            })
            
        except Exception as e:
            logger.error(f"DXF analysis failed: {e}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=500)


class DXFLayersAPIView(View):
    """API: Get layer information."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            loader = CADLoaderService.from_bytes(content, request.FILES["file"].name)
            
            return JsonResponse({
                "success": True,
                "layers": loader.get_layers()
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class DXFBlocksAPIView(View):
    """API: Get block information."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            loader = CADLoaderService.from_bytes(content, request.FILES["file"].name)
            
            return JsonResponse({
                "success": True,
                "blocks": loader.get_blocks()
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class DXFTextsAPIView(View):
    """API: Get text information."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            loader = CADLoaderService.from_bytes(content, request.FILES["file"].name)
            
            return JsonResponse({
                "success": True,
                "texts": loader.get_texts()
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class DXFDimensionsAPIView(View):
    """API: Get dimension information."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            loader = CADLoaderService.from_bytes(content, request.FILES["file"].name)
            
            return JsonResponse({
                "success": True,
                "dimensions": loader.get_dimensions()
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class DXFRoomsAPIView(View):
    """API: Get room information (floor plan analysis)."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            loader = CADLoaderService.from_bytes(content, request.FILES["file"].name)
            
            return JsonResponse({
                "success": True,
                "rooms": loader.get_rooms(),
                "room_areas": loader.get_room_areas(),
                "doors": loader.get_doors(),
                "windows": loader.get_windows(),
                "furniture": loader.get_furniture(),
                "sanitary": loader.get_sanitary(),
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class DXFExportJSONView(View):
    """Export full analysis as JSON download."""
    
    def post(self, request):
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        try:
            content = request.FILES["file"].read()
            loader = CADLoaderService.from_bytes(content, request.FILES["file"].name)
            
            analysis = loader.get_analysis_dict()
            
            response = HttpResponse(
                json.dumps(analysis, indent=2, default=str, ensure_ascii=False),
                content_type="application/json"
            )
            filename = Path(request.FILES["file"].name).stem + "_analysis.json"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class DWGStatusView(View):
    """Check DWG converter status."""
    
    def get(self, request):
        return JsonResponse(get_dwg_converter_status())
