"""
CAD Loader Service - Unified interface for DXF/DWG loading, rendering and analysis.

Combines:
- DXFAnalyzer (from toolkit) - Full analysis capabilities
- DXFRendererService - SVG/PNG/JSON rendering for viewers
- DWGConverter - Automatic DWG→DXF conversion
"""
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Union
import tempfile

from .dxf_analyzer import (
    DXFAnalyzer,
    FloorPlanAnalyzer,
    TechnicalDrawingAnalyzer,
    AnalysisReport,
    DWGConverter,
    load_cad_file,
)
from .dxf_renderer import DXFRendererService

logger = logging.getLogger(__name__)


class CADLoaderService:
    """
    Unified CAD loading service with analysis and rendering capabilities.
    
    Automatically handles:
    - DXF files (native support)
    - DWG files (automatic conversion via ODA)
    
    Usage:
        # From file path
        loader = CADLoaderService.from_file("drawing.dxf")
        
        # From uploaded bytes
        loader = CADLoaderService.from_bytes(content, "drawing.dxf")
        
        # Get viewer data for Three.js
        viewer_data = loader.get_viewer_data()
        
        # Get full analysis
        analysis = loader.get_analysis()
        
        # Get SVG thumbnail
        svg = loader.get_thumbnail()
    """
    
    def __init__(self, filepath: Union[str, Path]):
        """
        Initialize loader with a file path.
        
        Args:
            filepath: Path to DXF or DWG file
        """
        self.filepath = Path(filepath)
        self._analyzer: Optional[DXFAnalyzer] = None
        self._renderer: Optional[DXFRendererService] = None
        self._floor_analyzer: Optional[FloorPlanAnalyzer] = None
        self._tech_analyzer: Optional[TechnicalDrawingAnalyzer] = None
        
    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> "CADLoaderService":
        """Create loader from file path."""
        return cls(filepath)
    
    @classmethod
    def from_bytes(cls, content: bytes, filename: str = "upload.dxf") -> "CADLoaderService":
        """
        Create loader from file content bytes.
        
        Args:
            content: File content as bytes
            filename: Original filename (for format detection)
        """
        # Write to temp file
        suffix = Path(filename).suffix.lower() or ".dxf"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        loader = cls(temp_path)
        loader._is_temp = True
        loader._original_filename = filename
        return loader
    
    @property
    def analyzer(self) -> DXFAnalyzer:
        """Get or create analyzer instance (lazy loading)."""
        if self._analyzer is None:
            self._analyzer = DXFAnalyzer(self.filepath)
        return self._analyzer
    
    @property
    def renderer(self) -> DXFRendererService:
        """Get or create renderer instance (lazy loading)."""
        if self._renderer is None:
            self._renderer = DXFRendererService()
            self._renderer.load_file(self.filepath)
        return self._renderer
    
    @property
    def floor_analyzer(self) -> FloorPlanAnalyzer:
        """Get floor plan analyzer (lazy loading)."""
        if self._floor_analyzer is None:
            self._floor_analyzer = FloorPlanAnalyzer(self.filepath)
        return self._floor_analyzer
    
    @property
    def tech_analyzer(self) -> TechnicalDrawingAnalyzer:
        """Get technical drawing analyzer (lazy loading)."""
        if self._tech_analyzer is None:
            self._tech_analyzer = TechnicalDrawingAnalyzer(self.filepath)
        return self._tech_analyzer
    
    # -------------------------------------------------------------------------
    # VIEWER DATA
    # -------------------------------------------------------------------------
    
    def get_viewer_data(self) -> dict:
        """
        Get data optimized for Three.js viewer.
        
        Returns:
            dict with grouped entities, layers, bounds, stats
        """
        return self.renderer.export_for_threejs()
    
    def get_thumbnail(self, max_size: int = 300) -> Optional[str]:
        """
        Get SVG thumbnail.
        
        Args:
            max_size: Maximum dimension in pixels
            
        Returns:
            SVG string or None
        """
        return self.renderer.get_thumbnail_svg(max_size)
    
    def render_svg(self, width: int = 800, height: int = 600) -> Optional[str]:
        """Render full SVG."""
        return self.renderer.render_to_svg(width=width, height=height)
    
    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------
    
    def get_analysis(self) -> AnalysisReport:
        """
        Get full analysis report.
        
        Returns:
            AnalysisReport dataclass with all analysis data
        """
        return self.analyzer.full_analysis()
    
    def get_analysis_dict(self) -> dict:
        """Get analysis as dictionary (JSON-serializable)."""
        report = self.get_analysis()
        return asdict(report)
    
    def get_statistics(self) -> dict:
        """Get quick statistics."""
        return {
            "total_entities": len(self.analyzer.entities),
            "entity_counts": self.analyzer.count_entities(),
            "category_counts": self.analyzer.count_by_category(),
            "layer_count": len(self.analyzer.get_layer_names()),
            "bounding_box": self.analyzer.calculate_bounding_box(),
        }
    
    def get_layers(self) -> list[dict]:
        """Get layer information."""
        layers = self.analyzer.analyze_layers()
        return [asdict(l) for l in layers]
    
    def get_blocks(self) -> list[dict]:
        """Get block information."""
        blocks = self.analyzer.analyze_blocks()
        return [asdict(b) for b in blocks]
    
    def get_texts(self) -> list[dict]:
        """Get all texts."""
        texts = self.analyzer.extract_texts()
        return [asdict(t) for t in texts]
    
    def get_dimensions(self) -> list[dict]:
        """Get all dimensions."""
        dims = self.analyzer.extract_dimensions()
        return [asdict(d) for d in dims]
    
    def check_quality(self) -> list[dict]:
        """Run quality checks."""
        return self.analyzer.check_quality()
    
    # -------------------------------------------------------------------------
    # FLOOR PLAN ANALYSIS
    # -------------------------------------------------------------------------
    
    def get_rooms(self) -> list[dict]:
        """
        Identify rooms in floor plan.
        
        Uses text-based room identification.
        """
        return self.floor_analyzer.identify_rooms()
    
    def get_room_areas(self) -> list[dict]:
        """
        Calculate room areas from closed polylines.
        """
        return self.floor_analyzer.calculate_room_areas()
    
    def get_doors(self) -> list[dict]:
        """Find door blocks."""
        return self.floor_analyzer.find_doors()
    
    def get_windows(self) -> list[dict]:
        """Find window blocks."""
        return self.floor_analyzer.find_windows()
    
    def get_furniture(self) -> list[dict]:
        """Find furniture blocks."""
        return self.floor_analyzer.find_furniture()
    
    def get_sanitary(self) -> list[dict]:
        """Find sanitary equipment blocks."""
        return self.floor_analyzer.find_sanitary()
    
    # -------------------------------------------------------------------------
    # TECHNICAL DRAWING ANALYSIS
    # -------------------------------------------------------------------------
    
    def get_holes(self) -> list[dict]:
        """Extract holes/circles from technical drawing."""
        return self.tech_analyzer.extract_holes()
    
    def get_tolerances(self) -> list[dict]:
        """Extract tolerance information."""
        return self.tech_analyzer.extract_tolerances()
    
    def get_centerlines(self) -> list[dict]:
        """Find centerlines."""
        return self.tech_analyzer.analyze_centerlines()
    
    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------
    
    def export_json(self, filepath: str) -> str:
        """Export full analysis to JSON file."""
        return self.analyzer.export_json(filepath)
    
    def export_texts_csv(self, filepath: str) -> str:
        """Export texts to CSV."""
        return self.analyzer.export_texts_csv(filepath)
    
    def export_entities_csv(self, filepath: str) -> str:
        """Export entities to CSV."""
        return self.analyzer.export_entities_csv(filepath)
    
    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------
    
    @property
    def source_format(self) -> str:
        """Get original file format (DXF or DWG)."""
        return self.analyzer.source_format
    
    @property
    def was_converted(self) -> bool:
        """Check if file was converted from DWG."""
        return self.analyzer.was_converted
    
    @property
    def filename(self) -> str:
        """Get filename."""
        if hasattr(self, '_original_filename'):
            return self._original_filename
        return self.filepath.name
    
    def cleanup(self):
        """Clean up temporary files."""
        if hasattr(self, '_is_temp') and self._is_temp:
            try:
                self.filepath.unlink(missing_ok=True)
            except:
                pass
    
    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()


# Convenience functions
def load_and_analyze(filepath: Union[str, Path]) -> dict:
    """Quick function to load and analyze a CAD file."""
    loader = CADLoaderService.from_file(filepath)
    return loader.get_analysis_dict()


def get_dwg_converter_status() -> dict:
    """Check DWG converter availability."""
    converter = DWGConverter()
    return converter.get_status()
