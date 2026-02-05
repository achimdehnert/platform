"""
XGF Converter Service

Converts IFC/glTF models to XGF format using xeoconvert CLI.
XGF is the optimized format for xeokit SDK v3+.

Usage:
    converter = XGFConverterService(output_dir=Path('./media/xgf'))
    result = converter.convert_ifc(ifc_path)
    
    if result.success:
        print(f"XGF: {result.xgf_path}")
        print(f"DataModel: {result.datamodel_path}")
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConversionPipeline(Enum):
    """Available conversion pipelines in xeoconvert."""
    
    IFC2XGF = "ifc2xgf"
    GLTF2XGF = "gltf2xgf"
    LAS2XGF = "las2xgf"
    CITYJSON2XGF = "cityjson2xgf"
    DOTBIM2XGF = "dotbim2xgf"


@dataclass
class XGFConversionResult:
    """Result of XGF conversion."""
    
    success: bool
    xgf_path: Path | None = None
    datamodel_path: Path | None = None
    error: str | None = None
    stats: dict[str, Any] | None = None
    pipeline: str | None = None


class XGFConverterService:
    """Service for converting models to XGF format.
    
    Uses xeoconvert CLI from @xeokit/xeoconvert package.
    
    Installation:
        npm install -g @xeokit/xeoconvert
    """
    
    def __init__(
        self,
        output_dir: Path | None = None,
        xeoconvert_path: str = "xeoconvert",
    ):
        """Initialize converter.
        
        Args:
            output_dir: Directory for output files
            xeoconvert_path: Path to xeoconvert CLI
        """
        self.output_dir = output_dir or Path("./media/xgf")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.xeoconvert_path = xeoconvert_path
    
    def convert_ifc(
        self,
        ifc_path: Path,
        output_name: str | None = None,
        include_datamodel: bool = True,
    ) -> XGFConversionResult:
        """Convert IFC file to XGF format.
        
        Args:
            ifc_path: Path to source IFC file
            output_name: Output filename (without extension)
            include_datamodel: Generate DataModelParams JSON
            
        Returns:
            XGFConversionResult with paths and status
        """
        return self._convert(
            pipeline=ConversionPipeline.IFC2XGF,
            source_path=ifc_path,
            source_arg="--ifc",
            output_name=output_name,
            include_datamodel=include_datamodel,
        )
    
    def convert_gltf(
        self,
        gltf_path: Path,
        output_name: str | None = None,
    ) -> XGFConversionResult:
        """Convert glTF file to XGF format.
        
        Args:
            gltf_path: Path to source glTF/GLB file
            output_name: Output filename (without extension)
            
        Returns:
            XGFConversionResult with paths and status
        """
        return self._convert(
            pipeline=ConversionPipeline.GLTF2XGF,
            source_path=gltf_path,
            source_arg="--gltf",
            output_name=output_name,
            include_datamodel=False,
        )
    
    def convert_las(
        self,
        las_path: Path,
        output_name: str | None = None,
    ) -> XGFConversionResult:
        """Convert LAS/LAZ point cloud to XGF format.
        
        Args:
            las_path: Path to source LAS/LAZ file
            output_name: Output filename (without extension)
            
        Returns:
            XGFConversionResult with paths and status
        """
        return self._convert(
            pipeline=ConversionPipeline.LAS2XGF,
            source_path=las_path,
            source_arg="--las",
            output_name=output_name,
            include_datamodel=False,
        )
    
    def _convert(
        self,
        pipeline: ConversionPipeline,
        source_path: Path,
        source_arg: str,
        output_name: str | None = None,
        include_datamodel: bool = True,
    ) -> XGFConversionResult:
        """Internal conversion method.
        
        Args:
            pipeline: Conversion pipeline to use
            source_path: Path to source file
            source_arg: CLI argument for source (e.g., --ifc)
            output_name: Output filename
            include_datamodel: Generate DataModelParams JSON
            
        Returns:
            XGFConversionResult
        """
        if not source_path.exists():
            return XGFConversionResult(
                success=False,
                error=f"Source file not found: {source_path}",
                pipeline=pipeline.value,
            )
        
        output_name = output_name or source_path.stem
        xgf_path = self.output_dir / f"{output_name}.xgf"
        datamodel_path = self.output_dir / f"{output_name}.json"
        
        # Build command
        cmd = [
            self.xeoconvert_path,
            "--pipeline", pipeline.value,
            source_arg, str(source_path),
            "--xgf", str(xgf_path),
        ]
        
        if include_datamodel:
            cmd.extend(["--datamodel", str(datamodel_path)])
        
        logger.info(f"Converting {source_path} to XGF...")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes for large files
            )
            
            if result.returncode == 0 and xgf_path.exists():
                stats = self._get_stats(xgf_path, datamodel_path)
                
                logger.info(
                    f"Conversion successful: {xgf_path.name} "
                    f"({stats.get('xgf_size_mb', '?')} MB)"
                )
                
                return XGFConversionResult(
                    success=True,
                    xgf_path=xgf_path,
                    datamodel_path=datamodel_path if datamodel_path.exists() else None,
                    stats=stats,
                    pipeline=pipeline.value,
                )
            else:
                error = result.stderr or result.stdout or "Unknown error"
                logger.error(f"Conversion failed: {error}")
                
                return XGFConversionResult(
                    success=False,
                    error=error,
                    pipeline=pipeline.value,
                )
        
        except FileNotFoundError:
            error = (
                "xeoconvert not found. "
                "Install with: npm install -g @xeokit/xeoconvert"
            )
            logger.error(error)
            return XGFConversionResult(
                success=False,
                error=error,
                pipeline=pipeline.value,
            )
        
        except subprocess.TimeoutExpired:
            error = "Conversion timeout (>10 minutes)"
            logger.error(error)
            return XGFConversionResult(
                success=False,
                error=error,
                pipeline=pipeline.value,
            )
        
        except Exception as e:
            logger.exception("Conversion failed")
            return XGFConversionResult(
                success=False,
                error=str(e),
                pipeline=pipeline.value,
            )
    
    def _get_stats(
        self,
        xgf_path: Path,
        datamodel_path: Path,
    ) -> dict[str, Any]:
        """Get statistics about converted files."""
        stats = {
            "xgf_size_mb": round(xgf_path.stat().st_size / 1024 / 1024, 2),
        }
        
        if datamodel_path.exists():
            stats["datamodel_size_kb"] = round(
                datamodel_path.stat().st_size / 1024, 2
            )
            
            try:
                with open(datamodel_path) as f:
                    datamodel = json.load(f)
                
                if "objects" in datamodel:
                    stats["object_count"] = len(datamodel["objects"])
                if "propertySets" in datamodel:
                    stats["property_set_count"] = len(datamodel["propertySets"])
            except (json.JSONDecodeError, KeyError):
                pass
        
        return stats
    
    # ========== URL HELPERS ==========
    
    def get_xgf_url(self, model_id: int | str) -> str:
        """Get URL path for XGF file."""
        return f"/media/xgf/model_{model_id}.xgf"
    
    def get_datamodel_url(self, model_id: int | str) -> str:
        """Get URL path for DataModel JSON."""
        return f"/media/xgf/model_{model_id}.json"
    
    # ========== STRATEGY HELPERS ==========
    
    @staticmethod
    def should_convert(file_size_bytes: int) -> bool:
        """Determine if file should be converted to XGF.
        
        Files < 20MB can be loaded directly with IFCLoader.
        Larger files benefit from XGF conversion.
        
        Args:
            file_size_bytes: Size of source file
            
        Returns:
            True if conversion recommended
        """
        mb = file_size_bytes / 1024 / 1024
        return mb >= 20
    
    @staticmethod
    def get_recommended_strategy(file_size_bytes: int) -> str:
        """Get recommended loading strategy.
        
        Args:
            file_size_bytes: Size of source file
            
        Returns:
            'direct' for IFCLoader, 'xgf' for XGFLoader
        """
        mb = file_size_bytes / 1024 / 1024
        if mb < 20:
            return "direct"
        return "xgf"
    
    # ========== BATCH CONVERSION ==========
    
    def convert_batch(
        self,
        source_files: list[Path],
        pipeline: ConversionPipeline = ConversionPipeline.IFC2XGF,
    ) -> list[XGFConversionResult]:
        """Convert multiple files.
        
        Args:
            source_files: List of source file paths
            pipeline: Conversion pipeline to use
            
        Returns:
            List of conversion results
        """
        results = []
        source_arg = {
            ConversionPipeline.IFC2XGF: "--ifc",
            ConversionPipeline.GLTF2XGF: "--gltf",
            ConversionPipeline.LAS2XGF: "--las",
        }.get(pipeline, "--ifc")
        
        for source_path in source_files:
            result = self._convert(
                pipeline=pipeline,
                source_path=source_path,
                source_arg=source_arg,
            )
            results.append(result)
        
        return results
