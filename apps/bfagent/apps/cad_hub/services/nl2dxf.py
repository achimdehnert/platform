"""
NL2DXF - Natural Language to DXF Generator
Converts natural language descriptions into DXF drawings using LLM.

Example:
    generator = NL2DXFGenerator()
    dxf_path = generator.generate("Ein Rechteck 5m x 3m mit einer Tür an der Südseite")
"""
import json
import logging
import math
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import ezdxf
from ezdxf import units
from ezdxf.document import Drawing

logger = logging.getLogger(__name__)


@dataclass
class CADCommand:
    """Parsed CAD command from LLM response."""
    command: str  # LINE, RECT, CIRCLE, ARC, TEXT, DOOR, WINDOW, WALL
    params: dict = field(default_factory=dict)
    layer: str = "0"


@dataclass
class NL2DXFResult:
    """Result of NL2DXF generation."""
    success: bool
    filepath: Optional[Path] = None
    commands: list[CADCommand] = field(default_factory=list)
    error: Optional[str] = None
    llm_response: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "filepath": str(self.filepath) if self.filepath else None,
            "commands_count": len(self.commands),
            "error": self.error
        }


class NL2DXFGenerator:
    """
    Generate DXF files from natural language descriptions.
    
    Uses LLM to interpret the description and generate CAD commands,
    then converts those commands into actual DXF geometry.
    
    Usage:
        generator = NL2DXFGenerator()
        
        # With LLM
        result = generator.generate("Ein Raum 5m x 4m mit Fenster an der Nordseite")
        
        # Without LLM (direct commands)
        result = generator.generate_from_commands([
            CADCommand("RECT", {"x": 0, "y": 0, "width": 5, "height": 4}),
            CADCommand("WINDOW", {"wall": "north", "width": 1.2, "position": 0.5})
        ])
    """
    
    SYSTEM_PROMPT = """Du bist ein CAD-Assistent, der natürliche Sprache in CAD-Befehle umwandelt.

Antworte NUR mit einem JSON-Array von CAD-Befehlen. Keine Erklärungen.

Verfügbare Befehle:
- LINE: {"command": "LINE", "params": {"x1": 0, "y1": 0, "x2": 5, "y2": 0}, "layer": "Walls"}
- RECT: {"command": "RECT", "params": {"x": 0, "y": 0, "width": 5, "height": 4}, "layer": "Rooms"}
- CIRCLE: {"command": "CIRCLE", "params": {"cx": 2, "cy": 2, "radius": 1}, "layer": "Objects"}
- ARC: {"command": "ARC", "params": {"cx": 0, "cy": 0, "radius": 1, "start": 0, "end": 90}, "layer": "Objects"}
- TEXT: {"command": "TEXT", "params": {"x": 1, "y": 1, "text": "Raum 1", "height": 0.2}, "layer": "Text"}
- DOOR: {"command": "DOOR", "params": {"wall": "south", "width": 0.9, "position": 0.5}, "layer": "Doors"}
- WINDOW: {"command": "WINDOW", "params": {"wall": "north", "width": 1.2, "position": 0.3}, "layer": "Windows"}
- WALL: {"command": "WALL", "params": {"x1": 0, "y1": 0, "x2": 5, "y2": 0, "thickness": 0.24}, "layer": "Walls"}
- ROOM: {"command": "ROOM", "params": {"x": 0, "y": 0, "width": 5, "height": 4, "name": "Wohnzimmer"}, "layer": "Rooms"}

Einheiten: Alle Maße in Metern.
Koordinatensystem: X = Ost-West, Y = Nord-Süd.
Wände: north=oben, south=unten, east=rechts, west=links.
Position bei Türen/Fenstern: 0.0 = links/unten, 1.0 = rechts/oben (relativ zur Wand).

Beispiel Input: "Ein Rechteck 5m x 3m"
Beispiel Output: [{"command": "RECT", "params": {"x": 0, "y": 0, "width": 5, "height": 3}, "layer": "Rooms"}]
"""
    
    def __init__(self, llm_client=None):
        """
        Initialize generator.
        
        Args:
            llm_client: Optional LLM client. If None, uses apps.bfagent.services.llm_client
        """
        self.llm_client = llm_client
        self.doc: Optional[Drawing] = None
        self.current_room: Optional[dict] = None  # Track current room for relative positioning
    
    def generate(self, description: str, output_path: Optional[Path] = None,
                 use_llm: bool = True) -> NL2DXFResult:
        """
        Generate DXF from natural language description.
        
        Args:
            description: Natural language description of the drawing
            output_path: Where to save the DXF. If None, uses temp file.
            use_llm: If True, use LLM to interpret. If False, try simple parsing.
        
        Returns:
            NL2DXFResult with filepath and status
        """
        logger.info(f"NL2DXF: Generating from description: {description[:100]}...")
        
        try:
            if use_llm:
                commands = self._interpret_with_llm(description)
            else:
                commands = self._simple_parse(description)
            
            if not commands:
                return NL2DXFResult(
                    success=False,
                    error="Keine CAD-Befehle erkannt"
                )
            
            return self.generate_from_commands(commands, output_path)
            
        except Exception as e:
            logger.error(f"NL2DXF generation failed: {e}")
            return NL2DXFResult(success=False, error=str(e))
    
    def generate_from_commands(self, commands: list[CADCommand], 
                                output_path: Optional[Path] = None) -> NL2DXFResult:
        """Generate DXF from list of CAD commands."""
        # Create new document
        self.doc = ezdxf.new(dxfversion="R2010")
        self.doc.units = units.M  # Meters
        
        # Setup layers
        self._setup_layers()
        
        msp = self.doc.modelspace()
        
        # Execute commands
        for cmd in commands:
            self._execute_command(cmd, msp)
        
        # Save
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".dxf"))
        
        self.doc.saveas(str(output_path))
        logger.info(f"NL2DXF: Saved to {output_path}")
        
        return NL2DXFResult(
            success=True,
            filepath=output_path,
            commands=commands
        )
    
    def _setup_layers(self):
        """Create standard layers."""
        layers = [
            ("Walls", 1),      # Red
            ("Rooms", 3),      # Green
            ("Doors", 4),      # Cyan
            ("Windows", 5),    # Blue
            ("Text", 7),       # White
            ("Objects", 6),    # Magenta
            ("Dimensions", 2), # Yellow
        ]
        
        for name, color in layers:
            self.doc.layers.add(name, color=color)
    
    def _interpret_with_llm(self, description: str) -> list[CADCommand]:
        """Use LLM to interpret description into commands."""
        try:
            # Try to use the bfagent LLM client
            if self.llm_client is None:
                from apps.bfagent.services.llm_client import generate_text
                response = generate_text(
                    prompt=description,
                    system_prompt=self.SYSTEM_PROMPT,
                    max_tokens=2000
                )
            else:
                response = self.llm_client.generate(
                    prompt=description,
                    system_prompt=self.SYSTEM_PROMPT
                )
            
            return self._parse_llm_response(response)
            
        except ImportError:
            logger.warning("LLM client not available, falling back to simple parse")
            return self._simple_parse(description)
        except Exception as e:
            logger.error(f"LLM interpretation failed: {e}")
            return self._simple_parse(description)
    
    def _parse_llm_response(self, response: str) -> list[CADCommand]:
        """Parse LLM JSON response into CAD commands."""
        # Extract JSON array from response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if not json_match:
            logger.warning(f"No JSON array found in LLM response: {response[:200]}")
            return []
        
        try:
            data = json.loads(json_match.group())
            commands = []
            
            for item in data:
                cmd = CADCommand(
                    command=item.get("command", "").upper(),
                    params=item.get("params", {}),
                    layer=item.get("layer", "0")
                )
                commands.append(cmd)
            
            return commands
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return []
    
    def _simple_parse(self, description: str) -> list[CADCommand]:
        """
        Simple rule-based parsing without LLM.
        Handles common patterns like "Rechteck 5m x 3m", "Kreis r=2m".
        """
        commands = []
        desc_lower = description.lower()
        
        # Rectangle pattern: "rechteck 5m x 3m" or "raum 5x4"
        rect_match = re.search(r'(?:rechteck|raum|zimmer|fläche)\s*(\d+(?:[.,]\d+)?)\s*[mx×]\s*(\d+(?:[.,]\d+)?)', desc_lower)
        if rect_match:
            width = float(rect_match.group(1).replace(',', '.'))
            height = float(rect_match.group(2).replace(',', '.'))
            commands.append(CADCommand(
                command="RECT",
                params={"x": 0, "y": 0, "width": width, "height": height},
                layer="Rooms"
            ))
            self.current_room = {"width": width, "height": height}
        
        # Circle pattern: "kreis r=2m" or "kreis 2m"
        circle_match = re.search(r'kreis\s*(?:r\s*=\s*)?(\d+(?:[.,]\d+)?)', desc_lower)
        if circle_match:
            radius = float(circle_match.group(1).replace(',', '.'))
            commands.append(CADCommand(
                command="CIRCLE",
                params={"cx": radius, "cy": radius, "radius": radius},
                layer="Objects"
            ))
        
        # Door pattern: "tür" or "tür 0.9m"
        door_match = re.search(r'tür(?:e)?\s*(?:(\d+(?:[.,]\d+)?)\s*m)?', desc_lower)
        if door_match:
            width = float(door_match.group(1).replace(',', '.')) if door_match.group(1) else 0.9
            wall = "south"  # Default
            if "nord" in desc_lower:
                wall = "north"
            elif "ost" in desc_lower:
                wall = "east"
            elif "west" in desc_lower:
                wall = "west"
            commands.append(CADCommand(
                command="DOOR",
                params={"wall": wall, "width": width, "position": 0.5},
                layer="Doors"
            ))
        
        # Window pattern: "fenster" or "fenster 1.2m"
        window_match = re.search(r'fenster\s*(?:(\d+(?:[.,]\d+)?)\s*m)?', desc_lower)
        if window_match:
            width = float(window_match.group(1).replace(',', '.')) if window_match.group(1) else 1.2
            wall = "north"  # Default
            if "süd" in desc_lower:
                wall = "south"
            elif "ost" in desc_lower:
                wall = "east"
            elif "west" in desc_lower:
                wall = "west"
            commands.append(CADCommand(
                command="WINDOW",
                params={"wall": wall, "width": width, "position": 0.5},
                layer="Windows"
            ))
        
        return commands
    
    def _execute_command(self, cmd: CADCommand, msp):
        """Execute a single CAD command."""
        try:
            handler = getattr(self, f"_cmd_{cmd.command.lower()}", None)
            if handler:
                handler(cmd.params, cmd.layer, msp)
            else:
                logger.warning(f"Unknown command: {cmd.command}")
        except Exception as e:
            logger.error(f"Error executing {cmd.command}: {e}")
    
    def _cmd_line(self, params: dict, layer: str, msp):
        """Draw a line."""
        msp.add_line(
            (params["x1"], params["y1"]),
            (params["x2"], params["y2"]),
            dxfattribs={"layer": layer}
        )
    
    def _cmd_rect(self, params: dict, layer: str, msp):
        """Draw a rectangle."""
        x, y = params.get("x", 0), params.get("y", 0)
        w, h = params["width"], params["height"]
        
        points = [
            (x, y),
            (x + w, y),
            (x + w, y + h),
            (x, y + h),
            (x, y)  # Close
        ]
        msp.add_lwpolyline(points, dxfattribs={"layer": layer})
        
        # Store for relative positioning
        self.current_room = {"x": x, "y": y, "width": w, "height": h}
    
    def _cmd_room(self, params: dict, layer: str, msp):
        """Draw a room with label."""
        self._cmd_rect(params, layer, msp)
        
        # Add room name
        if "name" in params:
            x = params.get("x", 0) + params["width"] / 2
            y = params.get("y", 0) + params["height"] / 2
            msp.add_text(
                params["name"],
                dxfattribs={"layer": "Text", "height": 0.2}
            ).set_placement((x, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    
    def _cmd_circle(self, params: dict, layer: str, msp):
        """Draw a circle."""
        msp.add_circle(
            (params["cx"], params["cy"]),
            params["radius"],
            dxfattribs={"layer": layer}
        )
    
    def _cmd_arc(self, params: dict, layer: str, msp):
        """Draw an arc."""
        msp.add_arc(
            (params["cx"], params["cy"]),
            params["radius"],
            params["start"],
            params["end"],
            dxfattribs={"layer": layer}
        )
    
    def _cmd_text(self, params: dict, layer: str, msp):
        """Add text."""
        msp.add_text(
            params["text"],
            dxfattribs={"layer": layer, "height": params.get("height", 0.25)}
        ).set_placement((params["x"], params["y"]))
    
    def _cmd_door(self, params: dict, layer: str, msp):
        """Draw a door symbol on a wall."""
        if not self.current_room:
            logger.warning("No room context for door placement")
            return
        
        room = self.current_room
        wall = params.get("wall", "south")
        width = params.get("width", 0.9)
        pos = params.get("position", 0.5)  # 0-1 relative position
        
        # Calculate door position based on wall
        if wall == "south":
            x = room["x"] + (room["width"] - width) * pos
            y = room["y"]
            # Door swing arc
            msp.add_arc((x, y), width, 0, 90, dxfattribs={"layer": layer})
            msp.add_line((x, y), (x + width, y), dxfattribs={"layer": layer})
        elif wall == "north":
            x = room["x"] + (room["width"] - width) * pos
            y = room["y"] + room["height"]
            msp.add_arc((x + width, y), width, 90, 180, dxfattribs={"layer": layer})
            msp.add_line((x, y), (x + width, y), dxfattribs={"layer": layer})
        elif wall == "west":
            x = room["x"]
            y = room["y"] + (room["height"] - width) * pos
            msp.add_arc((x, y + width), width, 270, 360, dxfattribs={"layer": layer})
            msp.add_line((x, y), (x, y + width), dxfattribs={"layer": layer})
        elif wall == "east":
            x = room["x"] + room["width"]
            y = room["y"] + (room["height"] - width) * pos
            msp.add_arc((x, y), width, 180, 270, dxfattribs={"layer": layer})
            msp.add_line((x, y), (x, y + width), dxfattribs={"layer": layer})
    
    def _cmd_window(self, params: dict, layer: str, msp):
        """Draw a window symbol on a wall."""
        if not self.current_room:
            logger.warning("No room context for window placement")
            return
        
        room = self.current_room
        wall = params.get("wall", "north")
        width = params.get("width", 1.2)
        pos = params.get("position", 0.5)
        
        # Window is represented as parallel lines
        offset = 0.05  # Window depth
        
        if wall == "south":
            x = room["x"] + (room["width"] - width) * pos
            y = room["y"]
            msp.add_line((x, y - offset), (x + width, y - offset), dxfattribs={"layer": layer})
            msp.add_line((x, y + offset), (x + width, y + offset), dxfattribs={"layer": layer})
            msp.add_line((x, y - offset), (x, y + offset), dxfattribs={"layer": layer})
            msp.add_line((x + width, y - offset), (x + width, y + offset), dxfattribs={"layer": layer})
        elif wall == "north":
            x = room["x"] + (room["width"] - width) * pos
            y = room["y"] + room["height"]
            msp.add_line((x, y - offset), (x + width, y - offset), dxfattribs={"layer": layer})
            msp.add_line((x, y + offset), (x + width, y + offset), dxfattribs={"layer": layer})
            msp.add_line((x, y - offset), (x, y + offset), dxfattribs={"layer": layer})
            msp.add_line((x + width, y - offset), (x + width, y + offset), dxfattribs={"layer": layer})
        elif wall == "west":
            x = room["x"]
            y = room["y"] + (room["height"] - width) * pos
            msp.add_line((x - offset, y), (x - offset, y + width), dxfattribs={"layer": layer})
            msp.add_line((x + offset, y), (x + offset, y + width), dxfattribs={"layer": layer})
            msp.add_line((x - offset, y), (x + offset, y), dxfattribs={"layer": layer})
            msp.add_line((x - offset, y + width), (x + offset, y + width), dxfattribs={"layer": layer})
        elif wall == "east":
            x = room["x"] + room["width"]
            y = room["y"] + (room["height"] - width) * pos
            msp.add_line((x - offset, y), (x - offset, y + width), dxfattribs={"layer": layer})
            msp.add_line((x + offset, y), (x + offset, y + width), dxfattribs={"layer": layer})
            msp.add_line((x - offset, y), (x + offset, y), dxfattribs={"layer": layer})
            msp.add_line((x - offset, y + width), (x + offset, y + width), dxfattribs={"layer": layer})
    
    def _cmd_wall(self, params: dict, layer: str, msp):
        """Draw a wall with thickness."""
        x1, y1 = params["x1"], params["y1"]
        x2, y2 = params["x2"], params["y2"]
        thickness = params.get("thickness", 0.24)
        
        # Calculate perpendicular offset
        length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        if length == 0:
            return
        
        nx = -(y2-y1) / length * thickness / 2
        ny = (x2-x1) / length * thickness / 2
        
        # Draw wall as closed polyline
        points = [
            (x1 + nx, y1 + ny),
            (x2 + nx, y2 + ny),
            (x2 - nx, y2 - ny),
            (x1 - nx, y1 - ny),
            (x1 + nx, y1 + ny)
        ]
        msp.add_lwpolyline(points, dxfattribs={"layer": layer})


# Convenience function
def nl2dxf(description: str, output_path: Optional[Path] = None, 
           use_llm: bool = True) -> NL2DXFResult:
    """Quick generate function."""
    generator = NL2DXFGenerator()
    return generator.generate(description, output_path, use_llm)
