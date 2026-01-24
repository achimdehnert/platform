"""
PDF Lageplan (Site Plan) Handler.

Extrahiert Informationen aus Lageplänen im PDF-Format:
- Grundstücksdaten (Flurstück, Gemarkung, Fläche)
- Gebäudedaten (Grundfläche, Position)
- Abstände (Grenzabstände)
- Kennzahlen (GRZ, GFZ)
- Orientierung und Maßstab

Verwendet:
- PyMuPDF für Text-Extraktion
- Optional: Vision LLM für komplexe Interpretation
"""
import io
import re
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import (
    BaseCADHandler,
    CADHandlerResult,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class Grundstueck:
    """Grundstücksdaten."""
    flurstueck: str = ""
    gemarkung: str = ""
    flaeche_m2: float = 0.0
    gemeinde: str = ""
    strasse: str = ""
    hausnummer: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Gebaeude:
    """Gebäudedaten aus Lageplan."""
    bezeichnung: str = ""
    grundflaeche_m2: float = 0.0
    geschossflaeche_m2: float = 0.0
    hoehe_m: float = 0.0
    geschosse: int = 0
    nutzung: str = ""  # Wohnen, Gewerbe, etc.
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Kennzahlen:
    """Bauliche Kennzahlen."""
    grz: float = 0.0  # Grundflächenzahl
    grz_zulaessig: float = 0.0
    gfz: float = 0.0  # Geschossflächenzahl
    gfz_zulaessig: float = 0.0
    bmz: float = 0.0  # Baumassenzahl
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LageplanInfo:
    """Gesamtinformationen aus Lageplan."""
    grundstueck: Grundstueck = field(default_factory=Grundstueck)
    gebaeude: list[Gebaeude] = field(default_factory=list)
    kennzahlen: Kennzahlen = field(default_factory=Kennzahlen)
    massstab: str = ""
    nordrichtung: str = ""
    grenzabstaende: dict = field(default_factory=dict)  # {"nord": 3.0, "sued": 5.0, ...}
    stellplaetze: int = 0
    raw_text: str = ""
    
    def to_dict(self) -> dict:
        return {
            "grundstueck": self.grundstueck.to_dict(),
            "gebaeude": [g.to_dict() for g in self.gebaeude],
            "kennzahlen": self.kennzahlen.to_dict(),
            "massstab": self.massstab,
            "nordrichtung": self.nordrichtung,
            "grenzabstaende": self.grenzabstaende,
            "stellplaetze": self.stellplaetze,
        }


class PDFLageplanHandler(BaseCADHandler):
    """
    Handler für Lageplan-Extraktion aus PDF.
    
    Funktionen:
    - Text-Extraktion mit PyMuPDF
    - Pattern-Matching für Standardfelder
    - Optional: LLM für komplexe Interpretation
    
    Input:
        pdf_content: bytes - PDF-Datei als Bytes
        pdf_path: str - Pfad zur PDF-Datei
        use_llm: bool - LLM für Interpretation verwenden
    
    Output:
        lageplan: LageplanInfo mit allen extrahierten Daten
    """
    
    name = "PDFLageplanHandler"
    description = "Extrahiert Daten aus Lageplan-PDFs"
    required_inputs = []
    optional_inputs = ["pdf_content", "pdf_path", "use_llm"]
    
    # Regex-Patterns für Extraktion
    PATTERNS = {
        "flurstueck": [
            r"Fl(?:ur)?st(?:ück)?[:\s]*(\d+(?:/\d+)?)",
            r"Flst\.?\s*(?:Nr\.?)?\s*(\d+(?:/\d+)?)",
        ],
        "gemarkung": [
            r"Gemarkung[:\s]*([A-Za-zäöüÄÖÜß\s\-]+?)(?:\s*,|\s*$|\s*\n)",
            r"Gmkg\.?\s*([A-Za-zäöüÄÖÜß\s\-]+)",
        ],
        "flaeche": [
            r"(?:Grundstücks?)?[Ff]läche[:\s]*(\d+(?:[.,]\d+)?)\s*m²",
            r"(\d+(?:[.,]\d+)?)\s*m²\s*(?:Grundstück|Fläche)",
        ],
        "grz": [
            r"GRZ[:\s]*(\d+[.,]\d+)",
            r"Grundflächenzahl[:\s]*(\d+[.,]\d+)",
        ],
        "gfz": [
            r"GFZ[:\s]*(\d+[.,]\d+)",
            r"Geschossflächenzahl[:\s]*(\d+[.,]\d+)",
        ],
        "massstab": [
            r"(?:Maßstab|M\.?|1\s*:)\s*(\d+(?:\s*:\s*\d+)?)",
            r"1\s*:\s*(\d+)",
        ],
        "stellplaetze": [
            r"(\d+)\s*(?:Stell)?[Pp]l(?:ä|ae)tz",
            r"Stellplätze[:\s]*(\d+)",
        ],
        "hoehe": [
            r"(?:Wand)?[Hh]öhe[:\s]*(\d+[.,]\d+)\s*m",
            r"H\s*=\s*(\d+[.,]\d+)\s*m",
        ],
        "abstand": [
            r"(?:Grenz)?[Aa]bstand[:\s]*(\d+[.,]\d+)\s*m",
            r"(\d+[.,]\d+)\s*m\s*(?:zur\s+)?(?:Grenze|Nachbar)",
        ],
    }
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Extrahiert Lageplan-Informationen aus PDF."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        pdf_content = input_data.get("pdf_content")
        pdf_path = input_data.get("pdf_path")
        use_llm = input_data.get("use_llm", True)
        
        if not pdf_content and not pdf_path:
            result.add_error("Keine PDF-Daten (pdf_content oder pdf_path)")
            return result
        
        # PDF laden
        try:
            import fitz  # PyMuPDF
        except ImportError:
            result.add_error("PyMuPDF nicht installiert: pip install pymupdf")
            return result
        
        try:
            if pdf_path:
                doc = fitz.open(pdf_path)
            else:
                doc = fitz.open(stream=pdf_content, filetype="pdf")
            
            # Text aus allen Seiten extrahieren
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            
            doc.close()
            
        except Exception as e:
            result.add_error(f"PDF konnte nicht gelesen werden: {e}")
            return result
        
        # Lageplan-Info extrahieren
        lageplan = LageplanInfo(raw_text=full_text[:2000])
        
        # 1. Pattern-basierte Extraktion
        lageplan = self._extract_with_patterns(full_text, lageplan)
        
        # 2. LLM-basierte Extraktion (falls aktiviert und Lücken)
        if use_llm and self._has_gaps(lageplan):
            lageplan = self._extract_with_llm(full_text, lageplan)
        
        # Ergebnis
        result.data["lageplan"] = lageplan.to_dict()
        result.data["raw_text_preview"] = full_text[:500]
        result.data["extraction_complete"] = not self._has_gaps(lageplan)
        
        result.status = HandlerStatus.SUCCESS
        logger.info(f"[{self.name}] Lageplan extrahiert: {lageplan.grundstueck.flurstueck}")
        
        return result
    
    def _extract_with_patterns(self, text: str, lageplan: LageplanInfo) -> LageplanInfo:
        """Extrahiert Daten mit Regex-Patterns."""
        
        # Flurstück
        for pattern in self.PATTERNS["flurstueck"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lageplan.grundstueck.flurstueck = match.group(1)
                break
        
        # Gemarkung
        for pattern in self.PATTERNS["gemarkung"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lageplan.grundstueck.gemarkung = match.group(1).strip()
                break
        
        # Fläche
        for pattern in self.PATTERNS["flaeche"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lageplan.grundstueck.flaeche_m2 = float(match.group(1).replace(",", "."))
                break
        
        # GRZ
        for pattern in self.PATTERNS["grz"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lageplan.kennzahlen.grz = float(match.group(1).replace(",", "."))
                break
        
        # GFZ
        for pattern in self.PATTERNS["gfz"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lageplan.kennzahlen.gfz = float(match.group(1).replace(",", "."))
                break
        
        # Maßstab
        for pattern in self.PATTERNS["massstab"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lageplan.massstab = f"1:{match.group(1)}"
                break
        
        # Stellplätze
        for pattern in self.PATTERNS["stellplaetze"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lageplan.stellplaetze = int(match.group(1))
                break
        
        # Abstände (alle finden)
        for pattern in self.PATTERNS["abstand"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for i, m in enumerate(matches[:4]):  # Max 4 Abstände
                key = ["nord", "ost", "sued", "west"][i] if i < 4 else f"abstand_{i}"
                lageplan.grenzabstaende[key] = float(m.replace(",", "."))
        
        return lageplan
    
    def _has_gaps(self, lageplan: LageplanInfo) -> bool:
        """Prüft ob wichtige Felder fehlen."""
        return (
            not lageplan.grundstueck.flurstueck or
            lageplan.grundstueck.flaeche_m2 == 0 or
            lageplan.kennzahlen.grz == 0
        )
    
    def _extract_with_llm(self, text: str, lageplan: LageplanInfo) -> LageplanInfo:
        """Extrahiert fehlende Daten mit LLM."""
        try:
            try:
                from apps.bfagent.services.llm_client import generate_text
            except ImportError:
                import os
                import openai
                
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    return lageplan
                
                client = openai.OpenAI(api_key=api_key)
                
                def generate_text(prompt, max_tokens=500):
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=0.1,
                    )
                    return response.choices[0].message.content
            
            prompt = f"""Analysiere diesen Lageplan-Text und extrahiere die Informationen als JSON.

Text (Auszug):
{text[:3000]}

Extrahiere folgende Felder (nur wenn im Text vorhanden):
- flurstueck: Flurstücknummer
- gemarkung: Name der Gemarkung
- flaeche_m2: Grundstücksfläche in m²
- grz: Grundflächenzahl (z.B. 0.4)
- gfz: Geschossflächenzahl (z.B. 0.8)
- massstab: z.B. "1:500"
- stellplaetze: Anzahl
- gebaeude_grundflaeche_m2: Grundfläche des Gebäudes

Antworte NUR mit JSON, z.B.:
{{"flurstueck": "123/4", "flaeche_m2": 850.0, "grz": 0.4}}"""

            response = generate_text(prompt, max_tokens=300)
            if response:
                # JSON aus Antwort extrahieren
                json_match = re.search(r'\{[^{}]+\}', response)
                if json_match:
                    data = json.loads(json_match.group())
                    
                    # Felder übernehmen wenn leer
                    if not lageplan.grundstueck.flurstueck and data.get("flurstueck"):
                        lageplan.grundstueck.flurstueck = data["flurstueck"]
                    if not lageplan.grundstueck.gemarkung and data.get("gemarkung"):
                        lageplan.grundstueck.gemarkung = data["gemarkung"]
                    if lageplan.grundstueck.flaeche_m2 == 0 and data.get("flaeche_m2"):
                        lageplan.grundstueck.flaeche_m2 = float(data["flaeche_m2"])
                    if lageplan.kennzahlen.grz == 0 and data.get("grz"):
                        lageplan.kennzahlen.grz = float(data["grz"])
                    if lageplan.kennzahlen.gfz == 0 and data.get("gfz"):
                        lageplan.kennzahlen.gfz = float(data["gfz"])
                    
                    logger.info(f"[{self.name}] LLM extraction successful")
                    
        except Exception as e:
            logger.warning(f"[{self.name}] LLM extraction failed: {e}")
        
        return lageplan
