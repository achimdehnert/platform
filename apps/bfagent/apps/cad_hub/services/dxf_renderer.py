"""
DXF Renderer Service
Renders DXF files to SVG, PNG, or provides data for web viewers.
"""
import io
import json
import logging
import tempfile
from pathlib import Path
from typing import Optional

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

logger = logging.getLogger(__name__)


class DXFRendererService:
    """
    Service for rendering DXF files to various formats.
    
    Supports:
    - SVG export (for thumbnails and web display)
    - PNG export (for previews)
    - JSON export (for JavaScript viewers like dxf-viewer, three-dxf)
    """
    
    def __init__(self):
        self.doc = None
    
    def load_file(self, filepath: str | Path) -> bool:
        """Load a DXF file."""
        try:
            self.doc = ezdxf.readfile(str(filepath))
            return True
        except Exception as e:
            logger.error(f"Failed to load DXF: {e}")
            return False
    
    def load_bytes(self, content: bytes) -> bool:
        """Load DXF from bytes (handles both ASCII and binary DXF)."""
        import tempfile
        
        try:
            # Write to temp file - ezdxf handles binary/ASCII detection
            with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                self.doc = ezdxf.readfile(temp_path)
                return True
            finally:
                # Cleanup temp file
                import os
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Failed to load DXF from bytes: {e}")
            return False
    
    def render_to_svg(self, output_path: Optional[Path] = None, 
                      width: int = 800, height: int = 600,
                      background: str = "#ffffff") -> Optional[str]:
        """
        Render DXF to SVG.
        
        Args:
            output_path: Where to save SVG. If None, returns SVG string.
            width: SVG width in pixels
            height: SVG height in pixels
            background: Background color
        
        Returns:
            SVG string if output_path is None, else the output path
        """
        if not self.doc:
            logger.error("No document loaded")
            return None
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            
            fig = plt.figure(figsize=(width/100, height/100), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_facecolor(background)
            
            ctx = RenderContext(self.doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(self.doc.modelspace())
            
            ax.autoscale()
            ax.set_aspect('equal')
            ax.axis('off')
            
            if output_path:
                fig.savefig(str(output_path), format='svg', 
                           bbox_inches='tight', pad_inches=0,
                           facecolor=background)
                plt.close(fig)
                return str(output_path)
            else:
                # Return SVG as string
                buffer = io.BytesIO()
                fig.savefig(buffer, format='svg', 
                           bbox_inches='tight', pad_inches=0,
                           facecolor=background)
                plt.close(fig)
                buffer.seek(0)
                return buffer.read().decode('utf-8')
                
        except Exception as e:
            logger.error(f"SVG rendering failed: {e}")
            return None
    
    def render_to_png(self, output_path: Path, 
                      width: int = 800, height: int = 600,
                      dpi: int = 150,
                      background: str = "#ffffff") -> Optional[str]:
        """Render DXF to PNG."""
        if not self.doc:
            return None
        
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_facecolor(background)
            
            ctx = RenderContext(self.doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(self.doc.modelspace())
            
            ax.autoscale()
            ax.set_aspect('equal')
            ax.axis('off')
            
            fig.savefig(str(output_path), format='png',
                       bbox_inches='tight', pad_inches=0,
                       facecolor=background, dpi=dpi)
            plt.close(fig)
            return str(output_path)
            
        except Exception as e:
            logger.error(f"PNG rendering failed: {e}")
            return None
    
    def export_to_json(self) -> Optional[dict]:
        """
        Export DXF geometry as JSON for JavaScript viewers.
        
        Returns a dict with:
        - entities: List of geometric entities
        - layers: List of layers
        - bounds: Bounding box
        """
        if not self.doc:
            return None
        
        try:
            from ezdxf import bbox
            
            msp = self.doc.modelspace()
            entities = []
            
            for entity in msp:
                ent_data = self._entity_to_dict(entity)
                if ent_data:
                    entities.append(ent_data)
            
            # Calculate bounds
            cache = bbox.Cache()
            extents = bbox.extents(msp, cache=cache)
            
            bounds = None
            if extents.has_data:
                bounds = {
                    "min": [extents.extmin[0], extents.extmin[1], extents.extmin[2]],
                    "max": [extents.extmax[0], extents.extmax[1], extents.extmax[2]]
                }
            
            # Layers
            layers = []
            for layer in self.doc.layers:
                layers.append({
                    "name": layer.dxf.name,
                    "color": layer.dxf.color,
                    "visible": layer.is_on()
                })
            
            return {
                "entities": entities,
                "layers": layers,
                "bounds": bounds,
                "units": self.doc.header.get("$INSUNITS", 0)
            }
            
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return None
    
    def _entity_to_dict(self, entity) -> Optional[dict]:
        """Convert a DXF entity to a dict for JSON export."""
        etype = entity.dxftype()
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else "0"
        color = entity.dxf.color if hasattr(entity.dxf, 'color') else 256
        
        try:
            if etype == "LINE":
                return {
                    "type": "line",
                    "layer": layer,
                    "color": color,
                    "start": list(entity.dxf.start),
                    "end": list(entity.dxf.end)
                }
            
            elif etype == "CIRCLE":
                return {
                    "type": "circle",
                    "layer": layer,
                    "color": color,
                    "center": list(entity.dxf.center),
                    "radius": entity.dxf.radius
                }
            
            elif etype == "ARC":
                return {
                    "type": "arc",
                    "layer": layer,
                    "color": color,
                    "center": list(entity.dxf.center),
                    "radius": entity.dxf.radius,
                    "startAngle": entity.dxf.start_angle,
                    "endAngle": entity.dxf.end_angle
                }
            
            elif etype == "LWPOLYLINE":
                points = [[p[0], p[1], 0] for p in entity.get_points()]
                return {
                    "type": "polyline",
                    "layer": layer,
                    "color": color,
                    "points": points,
                    "closed": entity.closed
                }
            
            elif etype == "POLYLINE":
                points = [list(v.dxf.location) for v in entity.vertices]
                return {
                    "type": "polyline",
                    "layer": layer,
                    "color": color,
                    "points": points,
                    "closed": entity.is_closed
                }
            
            elif etype == "TEXT":
                return {
                    "type": "text",
                    "layer": layer,
                    "color": color,
                    "text": entity.dxf.text,
                    "position": list(entity.dxf.insert),
                    "height": entity.dxf.height,
                    "rotation": getattr(entity.dxf, 'rotation', 0)
                }
            
            elif etype == "MTEXT":
                return {
                    "type": "text",
                    "layer": layer,
                    "color": color,
                    "text": entity.plain_text(),
                    "position": list(entity.dxf.insert),
                    "height": entity.dxf.char_height,
                    "rotation": getattr(entity.dxf, 'rotation', 0)
                }
            
            elif etype == "3DFACE":
                return {
                    "type": "3dface",
                    "layer": layer,
                    "color": color,
                    "vertices": [
                        list(entity.dxf.vtx0),
                        list(entity.dxf.vtx1),
                        list(entity.dxf.vtx2),
                        list(entity.dxf.vtx3)
                    ]
                }
            
            elif etype == "SOLID":
                return {
                    "type": "solid",
                    "layer": layer,
                    "color": color,
                    "vertices": [
                        list(entity.dxf.vtx0),
                        list(entity.dxf.vtx1),
                        list(entity.dxf.vtx2),
                        list(entity.dxf.vtx3) if hasattr(entity.dxf, 'vtx3') else list(entity.dxf.vtx2)
                    ]
                }
            
            elif etype == "POINT":
                return {
                    "type": "point",
                    "layer": layer,
                    "color": color,
                    "position": list(entity.dxf.location)
                }
            
            elif etype == "SPLINE":
                # Approximate spline with points
                try:
                    points = [list(p) for p in entity.flattening(0.1)]
                    return {
                        "type": "spline",
                        "layer": layer,
                        "color": color,
                        "points": points
                    }
                except:
                    return None
            
            elif etype == "ELLIPSE":
                return {
                    "type": "ellipse",
                    "layer": layer,
                    "color": color,
                    "center": list(entity.dxf.center),
                    "majorAxis": list(entity.dxf.major_axis),
                    "ratio": entity.dxf.ratio,
                    "startParam": entity.dxf.start_param,
                    "endParam": entity.dxf.end_param
                }
            
            elif etype == "INSERT":
                return {
                    "type": "insert",
                    "layer": layer,
                    "color": color,
                    "blockName": entity.dxf.name,
                    "position": list(entity.dxf.insert),
                    "scale": [entity.dxf.xscale, entity.dxf.yscale, entity.dxf.zscale],
                    "rotation": getattr(entity.dxf, 'rotation', 0)
                }
            
        except Exception as e:
            logger.debug(f"Could not convert {etype}: {e}")
        
        return None
    
    def get_thumbnail_svg(self, max_size: int = 200) -> Optional[str]:
        """Generate a small SVG thumbnail."""
        return self.render_to_svg(width=max_size, height=max_size)
    
    def export_for_threejs(self) -> Optional[dict]:
        """
        Export DXF in a format optimized for Three.js rendering.
        
        Groups entities by type for efficient batch rendering.
        """
        json_data = self.export_to_json()
        if not json_data:
            return None
        
        # Group by type for Three.js
        grouped = {
            "lines": [],
            "circles": [],
            "arcs": [],
            "polylines": [],
            "texts": [],
            "faces": [],
            "points": []
        }
        
        for ent in json_data["entities"]:
            etype = ent["type"]
            if etype == "line":
                grouped["lines"].append(ent)
            elif etype == "circle":
                grouped["circles"].append(ent)
            elif etype == "arc":
                grouped["arcs"].append(ent)
            elif etype in ("polyline", "spline"):
                grouped["polylines"].append(ent)
            elif etype == "text":
                grouped["texts"].append(ent)
            elif etype in ("3dface", "solid"):
                grouped["faces"].append(ent)
            elif etype == "point":
                grouped["points"].append(ent)
        
        return {
            "grouped": grouped,
            "layers": json_data["layers"],
            "bounds": json_data["bounds"],
            "units": json_data["units"],
            "stats": {
                "lines": len(grouped["lines"]),
                "circles": len(grouped["circles"]),
                "arcs": len(grouped["arcs"]),
                "polylines": len(grouped["polylines"]),
                "texts": len(grouped["texts"]),
                "faces": len(grouped["faces"]),
                "points": len(grouped["points"])
            }
        }


def render_dxf_to_svg(filepath: str | Path, output: Optional[Path] = None) -> Optional[str]:
    """Quick render function."""
    renderer = DXFRendererService()
    if renderer.load_file(filepath):
        return renderer.render_to_svg(output)
    return None


def dxf_to_json(filepath: str | Path) -> Optional[dict]:
    """Quick JSON export function."""
    renderer = DXFRendererService()
    if renderer.load_file(filepath):
        return renderer.export_to_json()
    return None
