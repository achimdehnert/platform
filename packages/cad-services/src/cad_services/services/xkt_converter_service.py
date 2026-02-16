"""Model Converter Service for xeokit 3D Viewer

Converts IFC files to optimized formats:
- XGF: New recommended format (xeokit SDK v3+)
- XKT: Legacy format (still supported)
- glTF: Intermediate format

Pipelines (from xeokit docs):
- Small IFC (<50MB): Direct IFCLoader (no conversion needed)
- Large IFC: IFC → XGF via xeoconvert
- Legacy: IFC → XKT via xeokit-convert

External tools:
- xeoconvert (npm): npm install -g @xeokit/xeoconvert
- xeokit-convert (npm): npm install -g @xeokit/xeokit-convert (legacy)
- ifc2gltf (IfcOpenShell): For glTF intermediate
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of model conversion."""

    success: bool
    output_path: Path | None = None
    metadata_path: Path | None = None
    format: str = "xkt"
    error: str | None = None
    stats: dict[str, Any] | None = None

    # Legacy alias
    @property
    def xkt_path(self) -> Path | None:
        return self.output_path


class XKTConverterService:
    """Service for converting IFC to XKT format.

    Uses ifc2gltf or ifcconvert for conversion pipeline:
    IFC -> glTF -> XKT

    Requires external tools:
    - ifc2gltf (from IfcOpenShell) or
    - xeokit-convert CLI
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        xeokit_convert_path: str = "xeokit-convert",
        ifc2gltf_path: str = "ifc2gltf",
    ):
        """Initialize converter.

        Args:
            output_dir: Directory for output files
            xeokit_convert_path: Path to xeokit-convert CLI
            ifc2gltf_path: Path to ifc2gltf tool
        """
        self.output_dir = output_dir or Path("./xkt_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.xeokit_convert_path = xeokit_convert_path
        self.ifc2gltf_path = ifc2gltf_path

    def convert_ifc_to_xkt(
        self,
        ifc_path: Path,
        output_name: str | None = None,
    ) -> ConversionResult:
        """Convert IFC file to XKT format.

        Args:
            ifc_path: Path to IFC file
            output_name: Optional output filename (without extension)

        Returns:
            ConversionResult with paths and status
        """
        if not ifc_path.exists():
            return ConversionResult(
                success=False,
                error=f"IFC file not found: {ifc_path}",
            )

        output_name = output_name or ifc_path.stem
        xkt_path = self.output_dir / f"{output_name}.xkt"
        metadata_path = self.output_dir / f"{output_name}.json"

        # Try xeokit-convert first (direct IFC -> XKT)
        result = self._convert_with_xeokit(ifc_path, xkt_path, metadata_path)
        if result.success:
            return result

        # Fallback: IFC -> glTF -> XKT
        gltf_path = self.output_dir / f"{output_name}.gltf"
        gltf_result = self._convert_ifc_to_gltf(ifc_path, gltf_path)
        if not gltf_result.success:
            return gltf_result

        return self._convert_gltf_to_xkt(gltf_path, xkt_path, metadata_path)

    def _convert_with_xeokit(
        self,
        ifc_path: Path,
        xkt_path: Path,
        metadata_path: Path,
    ) -> ConversionResult:
        """Convert using xeokit-convert CLI."""
        try:
            cmd = [
                self.xeokit_convert_path,
                "-s", str(ifc_path),
                "-o", str(xkt_path),
                "-m", str(metadata_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0 and xkt_path.exists():
                stats = self._get_file_stats(xkt_path, metadata_path)
                return ConversionResult(
                    success=True,
                    output_path=xkt_path,
                    metadata_path=metadata_path if metadata_path.exists() else None,
                    stats=stats,
                )
            else:
                return ConversionResult(
                    success=False,
                    error=result.stderr or "xeokit-convert failed",
                )

        except FileNotFoundError:
            return ConversionResult(
                success=False,
                error="xeokit-convert not found. Install with: npm i -g @xeokit/xeokit-convert",
            )
        except subprocess.TimeoutExpired:
            return ConversionResult(
                success=False,
                error="Conversion timeout (>5 minutes)",
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                error=str(e),
            )

    def _convert_ifc_to_gltf(
        self,
        ifc_path: Path,
        gltf_path: Path,
    ) -> ConversionResult:
        """Convert IFC to glTF using ifc2gltf."""
        try:
            cmd = [
                self.ifc2gltf_path,
                str(ifc_path),
                str(gltf_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0 and gltf_path.exists():
                return ConversionResult(success=True, output_path=gltf_path)
            else:
                return ConversionResult(
                    success=False,
                    error=result.stderr or "ifc2gltf failed",
                )

        except FileNotFoundError:
            return ConversionResult(
                success=False,
                error="ifc2gltf not found. Install IfcOpenShell.",
            )
        except Exception as e:
            return ConversionResult(success=False, error=str(e))

    def _convert_gltf_to_xkt(
        self,
        gltf_path: Path,
        xkt_path: Path,
        metadata_path: Path,
    ) -> ConversionResult:
        """Convert glTF to XKT."""
        try:
            cmd = [
                self.xeokit_convert_path,
                "-s", str(gltf_path),
                "-o", str(xkt_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0 and xkt_path.exists():
                stats = self._get_file_stats(xkt_path, metadata_path)
                return ConversionResult(
                    success=True,
                    output_path=xkt_path,
                    metadata_path=metadata_path if metadata_path.exists() else None,
                    stats=stats,
                )
            else:
                return ConversionResult(
                    success=False,
                    error=result.stderr or "glTF to XKT conversion failed",
                )

        except Exception as e:
            return ConversionResult(success=False, error=str(e))

    def _get_file_stats(
        self,
        xkt_path: Path,
        metadata_path: Path,
    ) -> dict[str, Any]:
        """Get stats about converted files."""
        stats = {
            "xkt_size_mb": round(xkt_path.stat().st_size / 1024 / 1024, 2),
        }

        if metadata_path.exists():
            import json
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                stats["object_count"] = len(metadata.get("metaObjects", []))
                stats["property_sets"] = len(metadata.get("propertySets", []))
            except (json.JSONDecodeError, KeyError):
                pass

        return stats

    def get_xkt_url(self, model_id: int) -> str:
        """Get URL for XKT file (for frontend).

        Args:
            model_id: Model database ID

        Returns:
            URL path to XKT file
        """
        return f"/media/xkt/model_{model_id}.xkt"

    def get_metadata_url(self, model_id: int) -> str:
        """Get URL for metadata JSON.

        Args:
            model_id: Model database ID

        Returns:
            URL path to metadata file
        """
        return f"/media/xkt/model_{model_id}.json"

    # ========== XGF CONVERSION (SDK v3+) ==========

    def convert_ifc_to_xgf(
        self,
        ifc_path: Path,
        output_name: str | None = None,
    ) -> ConversionResult:
        """Convert IFC file to XGF format (recommended for large files).

        Args:
            ifc_path: Path to IFC file
            output_name: Optional output filename (without extension)

        Returns:
            ConversionResult with paths and status
        """
        if not ifc_path.exists():
            return ConversionResult(
                success=False,
                error=f"IFC file not found: {ifc_path}",
            )

        output_name = output_name or ifc_path.stem
        xgf_path = self.output_dir / f"{output_name}.xgf"
        metadata_path = self.output_dir / f"{output_name}.json"

        try:
            # Use xeoconvert CLI (SDK v3)
            cmd = [
                "xeoconvert",
                "-i", str(ifc_path),
                "-o", str(xgf_path),
                "-f", "xgf",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 min for large files
            )

            if result.returncode == 0 and xgf_path.exists():
                stats = {
                    "xgf_size_mb": round(
                        xgf_path.stat().st_size / 1024 / 1024, 2
                    ),
                }
                return ConversionResult(
                    success=True,
                    output_path=xgf_path,
                    metadata_path=metadata_path if metadata_path.exists() else None,
                    format="xgf",
                    stats=stats,
                )
            else:
                return ConversionResult(
                    success=False,
                    error=result.stderr or "xeoconvert failed",
                )

        except FileNotFoundError:
            return ConversionResult(
                success=False,
                error="xeoconvert not found. Install: npm i -g @xeokit/xeoconvert",
            )
        except subprocess.TimeoutExpired:
            return ConversionResult(
                success=False,
                error="Conversion timeout (>10 minutes)",
            )
        except Exception as e:
            return ConversionResult(success=False, error=str(e))

    def get_xgf_url(self, model_id: int) -> str:
        """Get URL for XGF file."""
        return f"/media/xgf/model_{model_id}.xgf"

    def should_convert(self, file_size_bytes: int) -> str:
        """Recommend conversion strategy based on file size.

        Args:
            file_size_bytes: Size of IFC file

        Returns:
            'direct' for IFCLoader, 'xgf' for XGF conversion
        """
        mb = file_size_bytes / 1024 / 1024
        if mb < 50:
            return "direct"  # Use IFCLoader in browser
        return "xgf"  # Convert to XGF for streaming
