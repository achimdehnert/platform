"""
DWG Converter Service
Converts DWG files to DXF for processing.

Supports multiple conversion methods:
1. ODA File Converter (recommended, best quality)
2. LibreDWG (open source alternative)
3. Cloud API fallback (ShareCAD)
"""
import io
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import requests

logger = logging.getLogger(__name__)


@dataclass
class DWGConversionResult:
    """Result of DWG to DXF conversion."""
    success: bool
    dxf_path: Optional[Path] = None
    dxf_content: Optional[bytes] = None
    error: Optional[str] = None
    method: Optional[str] = None


class DWGConverterService:
    """
    Service for converting DWG files to DXF.
    
    Conversion Methods (in order of preference):
    1. ODA File Converter - Best quality, requires installation
    2. LibreDWG - Open source, requires installation
    3. Cloud API - No installation, but uploads file
    
    Usage:
        converter = DWGConverterService()
        result = converter.convert_to_dxf("drawing.dwg")
        
        if result.success:
            # Use result.dxf_path or result.dxf_content
            pass
    """
    
    # ODA File Converter paths (check multiple locations)
    ODA_PATHS = [
        "/usr/bin/ODAFileConverter",
        "/opt/ODAFileConverter/ODAFileConverter",
        "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
        "C:\\ODAFileConverter\\ODAFileConverter.exe",
    ]
    
    # LibreDWG paths
    LIBREDWG_PATHS = [
        "/usr/bin/dwg2dxf",
        "/usr/local/bin/dwg2dxf",
    ]
    
    # Cloud APIs for DWG conversion
    CONVERTIO_API = "https://api.convertio.co/convert"
    ZAMZAR_API = "https://api.zamzar.com/v1/jobs"
    
    def __init__(self):
        self.oda_path = self._find_oda_converter()
        self.libredwg_path = self._find_libredwg()
    
    def _find_oda_converter(self) -> Optional[str]:
        """Find ODA File Converter installation."""
        for path in self.ODA_PATHS:
            if os.path.exists(path):
                logger.info(f"Found ODA File Converter at: {path}")
                return path
        
        # Try to find in PATH
        result = shutil.which("ODAFileConverter")
        if result:
            logger.info(f"Found ODA File Converter in PATH: {result}")
            return result
        
        return None
    
    def _find_libredwg(self) -> Optional[str]:
        """Find LibreDWG installation."""
        for path in self.LIBREDWG_PATHS:
            if os.path.exists(path):
                logger.info(f"Found LibreDWG at: {path}")
                return path
        
        # Try to find in PATH
        result = shutil.which("dwg2dxf")
        if result:
            logger.info(f"Found LibreDWG in PATH: {result}")
            return result
        
        return None
    
    def get_available_methods(self) -> list[str]:
        """Get list of available conversion methods."""
        methods = []
        if self.oda_path:
            methods.append("oda")
        if self.libredwg_path:
            methods.append("libredwg")
        methods.append("cloud")  # Always available
        return methods
    
    def convert_to_dxf(self, dwg_path: str | Path, 
                       method: Optional[str] = None,
                       output_path: Optional[Path] = None) -> DWGConversionResult:
        """
        Convert DWG file to DXF.
        
        Args:
            dwg_path: Path to DWG file
            method: Conversion method ('oda', 'libredwg', 'cloud'). Auto-selects if None.
            output_path: Where to save DXF. Uses temp file if None.
        
        Returns:
            DWGConversionResult with DXF path or content
        """
        dwg_path = Path(dwg_path)
        
        if not dwg_path.exists():
            return DWGConversionResult(success=False, error=f"File not found: {dwg_path}")
        
        if not dwg_path.suffix.lower() == ".dwg":
            return DWGConversionResult(success=False, error="Not a DWG file")
        
        # Auto-select method
        if method is None:
            if self.oda_path:
                method = "oda"
            elif self.libredwg_path:
                method = "libredwg"
            else:
                method = "cloud"
        
        logger.info(f"Converting {dwg_path.name} using method: {method}")
        
        # Dispatch to appropriate method
        if method == "oda":
            return self._convert_with_oda(dwg_path, output_path)
        elif method == "libredwg":
            return self._convert_with_libredwg(dwg_path, output_path)
        elif method == "cloud":
            return self._convert_with_cloud(dwg_path, output_path)
        else:
            return DWGConversionResult(success=False, error=f"Unknown method: {method}")
    
    def convert_bytes_to_dxf(self, dwg_content: bytes, 
                             filename: str = "upload.dwg",
                             method: Optional[str] = None) -> DWGConversionResult:
        """Convert DWG content from bytes to DXF."""
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as f:
            f.write(dwg_content)
            temp_path = Path(f.name)
        
        try:
            result = self.convert_to_dxf(temp_path, method=method)
            
            # Read DXF content if successful
            if result.success and result.dxf_path:
                with open(result.dxf_path, 'rb') as f:
                    result.dxf_content = f.read()
            
            return result
        finally:
            # Cleanup temp DWG
            temp_path.unlink(missing_ok=True)
    
    def _convert_with_oda(self, dwg_path: Path, 
                          output_path: Optional[Path]) -> DWGConversionResult:
        """Convert using ODA File Converter."""
        if not self.oda_path:
            return DWGConversionResult(
                success=False, 
                error="ODA File Converter not installed"
            )
        
        try:
            # Create temp output directory
            with tempfile.TemporaryDirectory() as temp_dir:
                input_dir = dwg_path.parent
                output_dir = temp_dir
                
                # ODA syntax: ODAFileConverter <input_folder> <output_folder> <output_version> <output_type> <recurse> <audit>
                # Output version: ACAD2018 (most compatible)
                # Output type: DXF
                cmd = [
                    self.oda_path,
                    str(input_dir),
                    output_dir,
                    "ACAD2018",
                    "DXF",
                    "0",  # No recurse
                    "1",  # Audit
                    str(dwg_path.name)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                # Find output file
                dxf_name = dwg_path.stem + ".dxf"
                temp_dxf = Path(output_dir) / dxf_name
                
                if temp_dxf.exists():
                    if output_path:
                        shutil.copy(temp_dxf, output_path)
                        final_path = output_path
                    else:
                        # Copy to new temp file that won't be deleted
                        final_path = Path(tempfile.mktemp(suffix=".dxf"))
                        shutil.copy(temp_dxf, final_path)
                    
                    return DWGConversionResult(
                        success=True,
                        dxf_path=final_path,
                        method="oda"
                    )
                else:
                    return DWGConversionResult(
                        success=False,
                        error=f"ODA conversion failed: {result.stderr}",
                        method="oda"
                    )
                    
        except subprocess.TimeoutExpired:
            return DWGConversionResult(
                success=False,
                error="ODA conversion timed out",
                method="oda"
            )
        except Exception as e:
            return DWGConversionResult(
                success=False,
                error=f"ODA conversion error: {e}",
                method="oda"
            )
    
    def _convert_with_libredwg(self, dwg_path: Path,
                                output_path: Optional[Path]) -> DWGConversionResult:
        """Convert using LibreDWG dwg2dxf."""
        if not self.libredwg_path:
            return DWGConversionResult(
                success=False,
                error="LibreDWG not installed"
            )
        
        try:
            if output_path is None:
                output_path = Path(tempfile.mktemp(suffix=".dxf"))
            
            # dwg2dxf syntax: dwg2dxf [-v] <input.dwg> [output.dxf]
            cmd = [self.libredwg_path, str(dwg_path), str(output_path)]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if output_path.exists():
                return DWGConversionResult(
                    success=True,
                    dxf_path=output_path,
                    method="libredwg"
                )
            else:
                return DWGConversionResult(
                    success=False,
                    error=f"LibreDWG conversion failed: {result.stderr}",
                    method="libredwg"
                )
                
        except subprocess.TimeoutExpired:
            return DWGConversionResult(
                success=False,
                error="LibreDWG conversion timed out",
                method="libredwg"
            )
        except Exception as e:
            return DWGConversionResult(
                success=False,
                error=f"LibreDWG conversion error: {e}",
                method="libredwg"
            )
    
    def _convert_with_cloud(self, dwg_path: Path,
                            output_path: Optional[Path]) -> DWGConversionResult:
        """
        Cloud conversion not available without API key.
        Returns instructions for installing local converters.
        """
        return DWGConversionResult(
            success=False,
            error=(
                "DWG-Konvertierung benötigt ODA File Converter oder LibreDWG.\n\n"
                "Installation ODA File Converter (empfohlen):\n"
                "1. Download: https://www.opendesign.com/guestfiles/oda_file_converter\n"
                "2. Installieren und Server neu starten\n\n"
                "Alternative: LibreDWG kompilieren:\n"
                "git clone https://github.com/LibreDWG/libredwg.git\n"
                "cd libredwg && ./autogen.sh && ./configure && make && sudo make install"
            ),
            method="cloud"
        )


# Install helper for LibreDWG
def install_libredwg_instructions() -> str:
    """Get installation instructions for LibreDWG."""
    return """
LibreDWG Installation:

Ubuntu/Debian:
    sudo apt-get install libredwg-tools

Arch Linux:
    sudo pacman -S libredwg

macOS (Homebrew):
    brew install libredwg

From Source:
    git clone https://github.com/LibreDWG/libredwg.git
    cd libredwg
    ./autogen.sh
    ./configure
    make
    sudo make install
"""


def install_oda_instructions() -> str:
    """Get installation instructions for ODA File Converter."""
    return """
ODA File Converter Installation:

1. Download from: https://www.opendesign.com/guestfiles/oda_file_converter
2. Choose your platform (Windows/Linux/macOS)
3. Install and note the installation path
4. Add to PATH or update ODA_PATHS in dwg_converter.py

Linux (Debian package):
    wget https://download.opendesign.com/guestfiles/Demo/ODAFileConverter_QT5_lnxX64_8.3dll_25.5.deb
    sudo dpkg -i ODAFileConverter_QT5_lnxX64_8.3dll_25.5.deb
"""


# Convenience function
def convert_dwg_to_dxf(dwg_path: str | Path) -> DWGConversionResult:
    """Quick conversion function."""
    converter = DWGConverterService()
    return converter.convert_to_dxf(dwg_path)
