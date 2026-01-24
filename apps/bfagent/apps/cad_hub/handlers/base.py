"""
Base Handler für CAD Hub NL2CAD Integration.

Alle CAD Handler erben von BaseCADHandler und implementieren
die execute() Methode für ihre spezifische Logik.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class CADFormat(Enum):
    """Unterstützte CAD-Formate."""
    IFC = "ifc"
    DXF = "dxf"
    DWG = "dwg"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_extension(cls, filepath: Union[str, Path]) -> "CADFormat":
        """Erkennt Format aus Dateiendung."""
        ext = Path(filepath).suffix.lower()
        mapping = {
            ".ifc": cls.IFC,
            ".dxf": cls.DXF,
            ".dwg": cls.DWG,
        }
        return mapping.get(ext, cls.UNKNOWN)


class HandlerStatus(Enum):
    """Handler-Ausführungsstatus."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class CADHandlerResult:
    """Ergebnis eines Handler-Aufrufs."""
    success: bool
    handler_name: str
    status: HandlerStatus = HandlerStatus.SUCCESS
    data: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary (JSON-serialisierbar)."""
        # Filter out non-serializable objects (keys starting with _)
        serializable_data = {
            k: v for k, v in self.data.items() 
            if not k.startswith("_")
        }
        return {
            "success": self.success,
            "handler": self.handler_name,
            "status": self.status.value,
            "data": serializable_data,
            "errors": self.errors,
            "warnings": self.warnings,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp,
        }
    
    def add_error(self, message: str):
        """Fügt Fehlermeldung hinzu."""
        self.errors.append(message)
        self.success = False
        self.status = HandlerStatus.ERROR
    
    def add_warning(self, message: str):
        """Fügt Warnung hinzu."""
        self.warnings.append(message)


class CADHandlerError(Exception):
    """Exception für Handler-Fehler."""
    
    def __init__(self, message: str, handler_name: str = "", details: dict = None):
        self.message = message
        self.handler_name = handler_name
        self.details = details or {}
        super().__init__(message)


class BaseCADHandler(ABC):
    """
    Basisklasse für alle CAD Handler.
    
    Handler verarbeiten CAD-Daten in einer Pipeline:
    INPUT → PROCESSING → OUTPUT
    
    Jeder Handler:
    - Validiert seine Eingaben
    - Führt seine spezifische Logik aus
    - Gibt ein CADHandlerResult zurück
    - Kann den Kontext für nachfolgende Handler erweitern
    
    Usage:
        handler = MyHandler(context={"file_path": "drawing.dxf"})
        result = handler.execute(input_data)
    """
    
    name: str = "BaseHandler"
    description: str = "Basisklasse für CAD Handler"
    required_inputs: list = []
    optional_inputs: list = []
    
    def __init__(self, context: dict = None):
        """
        Initialisiert Handler mit optionalem Kontext.
        
        Args:
            context: Geteilter Kontext zwischen Handlern in der Pipeline
        """
        self.context = context or {}
        self._start_time: Optional[datetime] = None
        self._result: Optional[CADHandlerResult] = None
    
    @abstractmethod
    def execute(self, input_data: dict) -> CADHandlerResult:
        """
        Führt Handler-Logik aus.
        
        Args:
            input_data: Eingabedaten für diesen Handler
            
        Returns:
            CADHandlerResult mit Ergebnis oder Fehlern
        """
        pass
    
    def validate_input(self, input_data: dict) -> tuple[bool, list[str]]:
        """
        Validiert Eingabedaten gegen required_inputs.
        
        Args:
            input_data: Zu validierende Daten
            
        Returns:
            Tuple (valid: bool, errors: list[str])
        """
        errors = []
        for required in self.required_inputs:
            if required not in input_data and required not in self.context:
                errors.append(f"Pflichtfeld fehlt: {required}")
        
        return len(errors) == 0, errors
    
    def run(self, input_data: dict) -> CADHandlerResult:
        """
        Führt Handler mit Validierung und Timing aus.
        
        Args:
            input_data: Eingabedaten
            
        Returns:
            CADHandlerResult
        """
        self._start_time = datetime.now()
        
        # Merge context into input
        merged_input = {**self.context, **input_data}
        
        # Validate
        valid, errors = self.validate_input(merged_input)
        if not valid:
            return CADHandlerResult(
                success=False,
                handler_name=self.name,
                status=HandlerStatus.ERROR,
                errors=errors,
            )
        
        try:
            # Execute
            logger.info(f"[{self.name}] Starting execution...")
            result = self.execute(merged_input)
            
            # Calculate execution time
            elapsed = (datetime.now() - self._start_time).total_seconds() * 1000
            result.execution_time_ms = elapsed
            
            logger.info(f"[{self.name}] Completed in {elapsed:.1f}ms")
            return result
            
        except CADHandlerError as e:
            logger.error(f"[{self.name}] Handler error: {e.message}")
            return CADHandlerResult(
                success=False,
                handler_name=self.name,
                status=HandlerStatus.ERROR,
                errors=[e.message],
            )
        except Exception as e:
            logger.exception(f"[{self.name}] Unexpected error: {e}")
            return CADHandlerResult(
                success=False,
                handler_name=self.name,
                status=HandlerStatus.ERROR,
                errors=[f"Unerwarteter Fehler: {str(e)}"],
            )
    
    def update_context(self, key: str, value: Any):
        """Aktualisiert geteilten Kontext."""
        self.context[key] = value
    
    def get_from_context(self, key: str, default: Any = None) -> Any:
        """Liest aus Kontext."""
        return self.context.get(key, default)
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name})>"


class CADHandlerPipeline:
    """
    Pipeline für sequentielle Handler-Ausführung.
    
    Usage:
        pipeline = CADHandlerPipeline()
        pipeline.add(CADFileInputHandler())
        pipeline.add(RoomAnalysisHandler())
        results = pipeline.run({"file_path": "drawing.dxf"})
    """
    
    def __init__(self, context: dict = None):
        self.handlers: list[BaseCADHandler] = []
        self.context = context or {}
        self.results: list[CADHandlerResult] = []
    
    def add(self, handler: BaseCADHandler) -> "CADHandlerPipeline":
        """Fügt Handler zur Pipeline hinzu."""
        handler.context = self.context
        self.handlers.append(handler)
        return self
    
    def run(self, input_data: dict) -> list[CADHandlerResult]:
        """
        Führt alle Handler sequentiell aus.
        
        Bei Fehler wird Pipeline abgebrochen.
        """
        self.results = []
        current_data = {**self.context, **input_data}
        
        for handler in self.handlers:
            handler.context = current_data
            result = handler.run(current_data)
            self.results.append(result)
            
            if not result.success:
                logger.warning(f"Pipeline stopped at {handler.name}: {result.errors}")
                break
            
            # Merge result data into context for next handler
            current_data.update(result.data)
        
        return self.results
    
    def get_final_result(self) -> dict:
        """Kombiniert alle Ergebnisse (JSON-serialisierbar)."""
        combined = {
            "success": all(r.success for r in self.results),
            "handlers": [r.to_dict() for r in self.results],
            "data": {},
            "errors": [],
            "warnings": [],
        }
        
        for result in self.results:
            # Filter out non-serializable objects (keys starting with _)
            serializable_data = {
                k: v for k, v in result.data.items() 
                if not k.startswith("_")
            }
            combined["data"].update(serializable_data)
            combined["errors"].extend(result.errors)
            combined["warnings"].extend(result.warnings)
        
        return combined
