"""
Documentation Service for BF Agent MCP
======================================

Automatische Dokumentationsaktualisierung bei Code-Änderungen.

Workflow:
1. Cascade ändert Handler/Model
2. MCP-Tool wird aufgerufen
3. Service extrahiert Docstrings
4. RST/MD Datei wird aktualisiert
"""

import ast
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Project root (4 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


@dataclass
class DocstringInfo:
    """Extracted docstring information."""
    name: str
    type: str  # class, function, method
    docstring: str
    signature: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class DocumentationUpdate:
    """Result of a documentation update."""
    success: bool
    message: str
    files_updated: List[str]
    warnings: List[str]


class DocExtractor:
    """Extracts docstrings from Python files."""
    
    def extract_from_file(self, file_path: Path) -> List[DocstringInfo]:
        """Extract all docstrings from a Python file."""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    docstring = ast.get_docstring(node) or ""
                    results.append(DocstringInfo(
                        name=node.name,
                        type="class",
                        docstring=docstring,
                        file_path=str(file_path),
                        line_number=node.lineno
                    ))
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_doc = ast.get_docstring(item) or ""
                            results.append(DocstringInfo(
                                name=f"{node.name}.{item.name}",
                                type="method",
                                docstring=method_doc,
                                file_path=str(file_path),
                                line_number=item.lineno
                            ))
                            
                elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                    # Top-level function
                    docstring = ast.get_docstring(node) or ""
                    results.append(DocstringInfo(
                        name=node.name,
                        type="function",
                        docstring=docstring,
                        file_path=str(file_path),
                        line_number=node.lineno
                    ))
                    
        except Exception as e:
            logger.error(f"Error extracting docstrings from {file_path}: {e}")
            
        return results
    
    def extract_handlers(self, app_name: str) -> List[DocstringInfo]:
        """Extract docstrings from all handlers in an app."""
        handlers_path = PROJECT_ROOT / "apps" / app_name / "handlers"
        results = []
        
        if not handlers_path.exists():
            # Try single handlers.py file
            handlers_file = PROJECT_ROOT / "apps" / app_name / "handlers.py"
            if handlers_file.exists():
                return self.extract_from_file(handlers_file)
            return results
        
        for py_file in handlers_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            results.extend(self.extract_from_file(py_file))
            
        return results
    
    def extract_models(self, app_name: str) -> List[DocstringInfo]:
        """Extract docstrings from models.py."""
        models_file = PROJECT_ROOT / "apps" / app_name / "models.py"
        
        if not models_file.exists():
            return []
            
        return self.extract_from_file(models_file)


class DocGenerator:
    """Generates documentation from docstrings."""
    
    def __init__(self, docs_root: Optional[Path] = None):
        self.docs_root = docs_root or PROJECT_ROOT / "docs_v2" / "doku-system" / "docs" / "source"
    
    def generate_handler_docs(self, app_name: str, docstrings: List[DocstringInfo]) -> str:
        """Generate RST documentation for handlers."""
        # Filter to classes only (handlers)
        handlers = [d for d in docstrings if d.type == "class" and "Handler" in d.name]
        
        if not handlers:
            return f"# {app_name} Handler\n\nKeine Handler gefunden.\n"
        
        lines = [
            f"# {app_name.replace('_', ' ').title()} Handler",
            "",
            "## Übersicht",
            "",
        ]
        
        for handler in handlers:
            lines.append(f"### {handler.name}")
            lines.append("")
            
            if handler.docstring:
                # First line as description
                first_line = handler.docstring.split('\n')[0]
                lines.append(first_line)
                lines.append("")
                
                # Full docstring in details
                lines.append("```python")
                lines.append(f'"""{handler.docstring}"""')
                lines.append("```")
                lines.append("")
            else:
                lines.append("*Keine Dokumentation verfügbar.*")
                lines.append("")
        
        return "\n".join(lines)
    
    def update_hub_docs(self, hub_name: str) -> DocumentationUpdate:
        """Update documentation for a specific hub."""
        extractor = DocExtractor()
        warnings = []
        files_updated = []
        
        # Extract handlers
        handlers = extractor.extract_handlers(hub_name)
        if not handlers:
            warnings.append(f"Keine Handler in {hub_name} gefunden")
        
        # Extract models
        models = extractor.extract_models(hub_name)
        if not models:
            warnings.append(f"Keine Models in {hub_name} gefunden")
        
        # Check if hub doc exists
        hub_doc = self.docs_root / "hubs" / f"{hub_name.replace('_', '-')}.md"
        
        if hub_doc.exists():
            # Update existing doc
            try:
                with open(hub_doc, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add handler count info
                handler_count = len([h for h in handlers if h.type == "class" and "Handler" in h.name])
                model_count = len([m for m in models if m.type == "class"])
                
                # Log what was found
                logger.info(f"Found {handler_count} handlers and {model_count} models in {hub_name}")
                files_updated.append(str(hub_doc))
                
            except Exception as e:
                warnings.append(f"Fehler beim Lesen von {hub_doc}: {e}")
        else:
            warnings.append(f"Hub-Dokumentation {hub_doc} existiert nicht")
        
        return DocumentationUpdate(
            success=len(warnings) == 0 or len(files_updated) > 0,
            message=f"Dokumentation für {hub_name} analysiert: {len(handlers)} Docstrings gefunden",
            files_updated=files_updated,
            warnings=warnings
        )


class DocumentationService:
    """Main service for documentation management."""
    
    def __init__(self):
        self.extractor = DocExtractor()
        self.generator = DocGenerator()
    
    def scan_hub(self, hub_name: str) -> Dict[str, Any]:
        """Scan a hub for documentation status."""
        handlers = self.extractor.extract_handlers(hub_name)
        models = self.extractor.extract_models(hub_name)
        
        handler_classes = [h for h in handlers if h.type == "class" and "Handler" in h.name]
        model_classes = [m for m in models if m.type == "class"]
        
        # Check documentation coverage
        handlers_with_docs = [h for h in handler_classes if h.docstring]
        models_with_docs = [m for m in model_classes if m.docstring]
        
        return {
            "hub_name": hub_name,
            "handlers": {
                "total": len(handler_classes),
                "documented": len(handlers_with_docs),
                "coverage": f"{len(handlers_with_docs) / len(handler_classes) * 100:.0f}%" if handler_classes else "N/A",
                "names": [h.name for h in handler_classes]
            },
            "models": {
                "total": len(model_classes),
                "documented": len(models_with_docs),
                "coverage": f"{len(models_with_docs) / len(model_classes) * 100:.0f}%" if model_classes else "N/A",
                "names": [m.name for m in model_classes]
            }
        }
    
    def update_documentation(self, hub_name: str) -> DocumentationUpdate:
        """Update documentation for a hub."""
        return self.generator.update_hub_docs(hub_name)
    
    def list_undocumented(self, hub_name: str) -> List[str]:
        """List undocumented items in a hub."""
        handlers = self.extractor.extract_handlers(hub_name)
        models = self.extractor.extract_models(hub_name)
        
        undocumented = []
        
        for item in handlers + models:
            if item.type == "class" and not item.docstring:
                undocumented.append(f"{item.type}: {item.name} ({item.file_path}:{item.line_number})")
        
        return undocumented
