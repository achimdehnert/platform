"""
PDF Text Extraction Service für Sicherheitsdatenblätter (SDB)
==============================================================

Extrahiert strukturierte Daten aus Sicherheitsdatenblättern:
- Stoffidentifikation
- Explosionsgrenzen (UEG, OEG)
- Flammpunkt
- Zündtemperatur
- Gefahrenhinweise (H-Sätze)
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


@dataclass
class ExtractedSDBData:
    """Extrahierte Daten aus einem Sicherheitsdatenblatt."""
    
    # Stoffidentifikation
    product_name: str = ""
    cas_number: str = ""
    ec_number: str = ""
    
    # Explosionsdaten
    lower_explosion_limit: Optional[float] = None  # UEG in Vol.-%
    upper_explosion_limit: Optional[float] = None  # OEG in Vol.-%
    flash_point: Optional[float] = None  # Flammpunkt in °C
    ignition_temperature: Optional[float] = None  # Zündtemperatur in °C
    vapor_pressure: Optional[float] = None  # Dampfdruck in hPa/mbar
    
    # Klassifizierung
    hazard_statements: List[str] = field(default_factory=list)  # H-Sätze
    precautionary_statements: List[str] = field(default_factory=list)  # P-Sätze
    ghs_symbols: List[str] = field(default_factory=list)
    
    # Metadaten
    extraction_confidence: float = 0.0
    raw_text: str = ""
    warnings: List[str] = field(default_factory=list)


class SDSPDFExtractor:
    """Extrahiert Sicherheitsdatenblatt-Informationen aus PDFs."""
    
    # Regex-Patterns für SDB-Daten
    PATTERNS = {
        'cas_number': r'CAS[:\s\-]*(\d{2,7}-\d{2}-\d)',
        'ec_number': r'(?:EC|EINECS)[:\s\-]*(\d{3}-\d{3}-\d)',
        'ueg': r'(?:UEG|LEL|Untere\s*Explosionsgrenze)[:\s]*(\d+[,.]?\d*)\s*(?:Vol\.?[-%]|%)',
        'oeg': r'(?:OEG|UEL|Obere\s*Explosionsgrenze)[:\s]*(\d+[,.]?\d*)\s*(?:Vol\.?[-%]|%)',
        'flash_point': r'(?:Flammpunkt|Flash\s*point)[:\s]*([<>]?\s*-?\d+[,.]?\d*)\s*°?C',
        'ignition_temp': r'(?:Zündtemperatur|Ignition\s*temperature|Selbstentzündung)[:\s]*(\d+[,.]?\d*)\s*°?C',
        'vapor_pressure': r'(?:Dampfdruck|Vapor\s*pressure)[:\s]*(\d+[,.]?\d*)\s*(?:hPa|mbar|kPa|Pa)',
        'h_statements': r'(H\d{3}[A-Za-z]?)',
        'p_statements': r'(P\d{3}(?:\+P\d{3})*)',
        'product_name': r'(?:Produktname|Product\s*name|Handelsname|Trade\s*name)[:\s]*([^\n]+)',
    }
    
    def __init__(self):
        self.use_pdfplumber = PDFPLUMBER_AVAILABLE
        self.use_pypdf2 = PYPDF2_AVAILABLE
        
        if not self.use_pdfplumber and not self.use_pypdf2:
            raise ImportError(
                "Keine PDF-Bibliothek verfügbar. "
                "Bitte installieren: pip install pdfplumber oder pip install PyPDF2"
            )
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extrahiert Text aus PDF-Datei."""
        text = ""
        
        if self.use_pdfplumber:
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                if self.use_pypdf2:
                    return self._extract_with_pypdf2(file_path)
                raise e
        elif self.use_pypdf2:
            return self._extract_with_pypdf2(file_path)
        
        return text
    
    def _extract_with_pypdf2(self, file_path: str) -> str:
        """Fallback: Extrahiert Text mit PyPDF2."""
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def extract_sdb_data(self, file_path: str) -> ExtractedSDBData:
        """
        Extrahiert strukturierte Daten aus einem Sicherheitsdatenblatt.
        
        Args:
            file_path: Pfad zur PDF-Datei
            
        Returns:
            ExtractedSDBData mit extrahierten Informationen
        """
        data = ExtractedSDBData()
        
        try:
            text = self.extract_text_from_pdf(file_path)
            data.raw_text = text[:5000]  # Ersten 5000 Zeichen für Debugging
            
            if not text.strip():
                data.warnings.append("PDF enthält keinen extrahierbaren Text")
                return data
            
            # Produktname
            match = re.search(self.PATTERNS['product_name'], text, re.IGNORECASE)
            if match:
                data.product_name = match.group(1).strip()
            
            # CAS-Nummer
            match = re.search(self.PATTERNS['cas_number'], text, re.IGNORECASE)
            if match:
                data.cas_number = match.group(1)
            
            # EC-Nummer
            match = re.search(self.PATTERNS['ec_number'], text, re.IGNORECASE)
            if match:
                data.ec_number = match.group(1)
            
            # UEG (Untere Explosionsgrenze)
            match = re.search(self.PATTERNS['ueg'], text, re.IGNORECASE)
            if match:
                try:
                    data.lower_explosion_limit = float(match.group(1).replace(',', '.'))
                except ValueError:
                    data.warnings.append(f"UEG nicht parsbar: {match.group(1)}")
            
            # OEG (Obere Explosionsgrenze)
            match = re.search(self.PATTERNS['oeg'], text, re.IGNORECASE)
            if match:
                try:
                    data.upper_explosion_limit = float(match.group(1).replace(',', '.'))
                except ValueError:
                    data.warnings.append(f"OEG nicht parsbar: {match.group(1)}")
            
            # Flammpunkt
            match = re.search(self.PATTERNS['flash_point'], text, re.IGNORECASE)
            if match:
                try:
                    val = match.group(1).replace(',', '.').replace('<', '').replace('>', '').strip()
                    data.flash_point = float(val)
                except ValueError:
                    data.warnings.append(f"Flammpunkt nicht parsbar: {match.group(1)}")
            
            # Zündtemperatur
            match = re.search(self.PATTERNS['ignition_temp'], text, re.IGNORECASE)
            if match:
                try:
                    data.ignition_temperature = float(match.group(1).replace(',', '.'))
                except ValueError:
                    data.warnings.append(f"Zündtemperatur nicht parsbar: {match.group(1)}")
            
            # Dampfdruck
            match = re.search(self.PATTERNS['vapor_pressure'], text, re.IGNORECASE)
            if match:
                try:
                    data.vapor_pressure = float(match.group(1).replace(',', '.'))
                except ValueError:
                    data.warnings.append(f"Dampfdruck nicht parsbar: {match.group(1)}")
            
            # H-Sätze
            h_matches = re.findall(self.PATTERNS['h_statements'], text)
            data.hazard_statements = list(set(h_matches))
            
            # P-Sätze
            p_matches = re.findall(self.PATTERNS['p_statements'], text)
            data.precautionary_statements = list(set(p_matches))
            
            # Confidence berechnen
            data.extraction_confidence = self._calculate_confidence(data)
            
        except Exception as e:
            data.warnings.append(f"Fehler bei Extraktion: {str(e)}")
        
        return data
    
    def _calculate_confidence(self, data: ExtractedSDBData) -> float:
        """Berechnet Konfidenz-Score basierend auf extrahierten Daten."""
        score = 0.0
        max_score = 10.0
        
        if data.product_name:
            score += 1.0
        if data.cas_number:
            score += 2.0
        if data.lower_explosion_limit is not None:
            score += 2.0
        if data.upper_explosion_limit is not None:
            score += 1.5
        if data.flash_point is not None:
            score += 1.5
        if data.ignition_temperature is not None:
            score += 1.0
        if data.hazard_statements:
            score += 1.0
        
        return min(score / max_score, 1.0)
    
    def format_for_phase5(self, data: ExtractedSDBData) -> str:
        """
        Formatiert extrahierte Daten für Phase 5 (Stoffdaten).
        
        Returns:
            Markdown-formatierter Text für Einfügen in Phase 5
        """
        lines = []
        
        if data.product_name:
            lines.append(f"### {data.product_name}")
        
        lines.append("")
        lines.append("| Eigenschaft | Wert |")
        lines.append("|-------------|------|")
        
        if data.cas_number:
            lines.append(f"| CAS-Nr. | {data.cas_number} |")
        if data.ec_number:
            lines.append(f"| EC-Nr. | {data.ec_number} |")
        if data.lower_explosion_limit is not None:
            lines.append(f"| UEG | {data.lower_explosion_limit} Vol.-% |")
        if data.upper_explosion_limit is not None:
            lines.append(f"| OEG | {data.upper_explosion_limit} Vol.-% |")
        if data.flash_point is not None:
            lines.append(f"| Flammpunkt | {data.flash_point} °C |")
        if data.ignition_temperature is not None:
            lines.append(f"| Zündtemperatur | {data.ignition_temperature} °C |")
        if data.vapor_pressure is not None:
            lines.append(f"| Dampfdruck | {data.vapor_pressure} hPa |")
        
        if data.hazard_statements:
            lines.append("")
            lines.append(f"**H-Sätze:** {', '.join(sorted(data.hazard_statements))}")
        
        if data.extraction_confidence < 0.5:
            lines.append("")
            lines.append(f"> ⚠️ Niedrige Extraktions-Konfidenz ({data.extraction_confidence:.0%}). Bitte manuell prüfen.")
        
        return "\n".join(lines)


def extract_sdb_from_document(document) -> Optional[ExtractedSDBData]:
    """
    Convenience-Funktion für Django-Modell.
    
    Args:
        document: ExSessionDocument Instanz
        
    Returns:
        ExtractedSDBData oder None bei Fehler
    """
    if not document.file:
        return None
    
    file_path = document.file.path
    if not file_path.lower().endswith('.pdf'):
        return None
    
    try:
        extractor = SDSPDFExtractor()
        return extractor.extract_sdb_data(file_path)
    except ImportError:
        return None
    except Exception:
        return None


# Alias für Abwärtskompatibilität
extract_sds_data = extract_sdb_from_document
