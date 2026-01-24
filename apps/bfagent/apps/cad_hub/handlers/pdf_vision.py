"""
Vision LLM Handler für PDF-Plan-Analyse.

Verwendet GPT-4V oder Claude Vision zur Analyse von:
- Gescannten Plänen
- Handskizzen
- Brandschutzplänen mit Symbolen
- Fluchtwegsymbolen und Schildern

Extrahiert:
- Symbol-Positionen und -Typen
- Fluchtweg-Verläufe
- Beschriftungen und Maße
- Raumzuordnungen
"""
import base64
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .base import (
    BaseCADHandler,
    CADHandlerResult,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ErkannteSymbol:
    """Ein erkanntes Symbol aus der Vision-Analyse."""
    typ: str = ""
    beschreibung: str = ""
    position_beschreibung: str = ""  # z.B. "oben links", "Flur Mitte"
    position_x_prozent: float = 0.0  # 0-100% von links
    position_y_prozent: float = 0.0  # 0-100% von oben
    konfidenz: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ErkannterFluchtweg:
    """Ein erkannter Fluchtweg aus der Vision-Analyse."""
    start: str = ""
    ende: str = ""
    laenge_geschaetzt: str = ""
    breite_geschaetzt: str = ""
    bemerkung: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VisionAnalyseErgebnis:
    """Ergebnis der Vision-Analyse."""
    erkannte_symbole: list[ErkannteSymbol] = field(default_factory=list)
    erkannte_fluchtwege: list[ErkannterFluchtweg] = field(default_factory=list)
    erkannte_raeume: list[dict] = field(default_factory=list)
    erkannte_tueren: list[dict] = field(default_factory=list)
    erkannte_texte: list[str] = field(default_factory=list)
    
    # Zusammenfassung
    zusammenfassung: str = ""
    warnungen: list[str] = field(default_factory=list)
    empfehlungen: list[str] = field(default_factory=list)
    
    # Rohdaten
    raw_response: str = ""
    
    def to_dict(self) -> dict:
        return {
            "erkannte_symbole": [s.to_dict() for s in self.erkannte_symbole],
            "erkannte_fluchtwege": [f.to_dict() for f in self.erkannte_fluchtwege],
            "erkannte_raeume": self.erkannte_raeume,
            "erkannte_tueren": self.erkannte_tueren,
            "erkannte_texte": self.erkannte_texte,
            "zusammenfassung": self.zusammenfassung,
            "warnungen": self.warnungen,
            "empfehlungen": self.empfehlungen,
        }


class PDFVisionHandler(BaseCADHandler):
    """
    Handler für Vision-LLM-basierte PDF-Analyse.
    
    Verwendet GPT-4V oder Claude Vision für:
    - Brandschutzplan-Analyse
    - Fluchtweg-Erkennung
    - Symbol-Identifikation
    
    Input:
        pdf_content: bytes - PDF als Bytes
        pdf_path: str - Pfad zur PDF
        image_content: bytes - Bild als Bytes (alternativ)
        analyse_typ: str - "brandschutz", "fluchtweg", "allgemein"
        llm_provider: str - "openai" oder "anthropic"
    
    Output:
        vision_analyse: VisionAnalyseErgebnis
    """
    
    name = "PDFVisionHandler"
    description = "Analysiert PDFs/Bilder mit Vision LLM"
    required_inputs = []
    optional_inputs = ["pdf_content", "pdf_path", "image_content", "analyse_typ", "llm_provider"]
    
    # Prompts für verschiedene Analyse-Typen
    PROMPTS = {
        "brandschutz": """Analysiere diesen Brandschutzplan und identifiziere:

1. **Brandschutz-Symbole** (Feuerlöscher, Rauchmelder, Notausgänge, Hydranten, etc.)
   - Typ des Symbols
   - Ungefähre Position (z.B. "Flur links", "Treppenhaus")
   - Position in Prozent (0-100% von links, 0-100% von oben)

2. **Fluchtwege**
   - Start und Ziel
   - Geschätzte Länge
   - Besonderheiten

3. **Brandabschnitte**
   - Feuerwiderstandsklasse (F30, F60, F90)
   - Ungefähre Fläche

4. **Mängel oder Probleme**
   - Fehlende Symbole
   - Zu lange Fluchtwege
   - Unklare Kennzeichnung

Antworte als JSON:
{
  "symbole": [{"typ": "...", "position": "...", "x_prozent": 50, "y_prozent": 30}],
  "fluchtwege": [{"start": "...", "ende": "...", "laenge": "..."}],
  "raeume": [{"name": "...", "flaeche_geschaetzt": "..."}],
  "warnungen": ["..."],
  "empfehlungen": ["..."],
  "zusammenfassung": "..."
}""",

        "fluchtweg": """Analysiere diesen Plan auf Fluchtwege und Notausgänge:

1. **Fluchtwege**
   - Verlauf (Start → Ziel)
   - Geschätzte Länge in Metern
   - Breite (falls erkennbar)
   - Hindernisse oder Engstellen

2. **Notausgänge**
   - Position
   - Typ (Tür, Fenster, Treppe)
   - Kennzeichnung vorhanden?

3. **Richtungspfeile**
   - Position
   - Richtung

4. **Prüfung nach ASR A2.3**
   - Max. 35m Fluchtweglänge eingehalten?
   - Zweiter Rettungsweg vorhanden?
   - Kennzeichnung ausreichend?

Antworte als JSON mit Struktur wie oben.""",

        "allgemein": """Analysiere diesen Bauplan und extrahiere:

1. **Räume**
   - Name/Nutzung
   - Ungefähre Fläche
   - Position

2. **Türen**
   - Position
   - Typ (Eingangstür, Innentür, Notausgang)

3. **Fenster**
   - Anzahl und Position

4. **Besonderheiten**
   - Treppen
   - Aufzüge
   - Technische Räume

5. **Erkennbare Texte**
   - Raumnamen
   - Maße
   - Beschriftungen

Antworte als JSON.""",

        "ex_zonen": """Analysiere diesen Plan auf explosionsgefährdete Bereiche:

1. **Ex-Zonen**
   - Zone (0, 1, 2, 20, 21, 22)
   - Fläche und Position
   - Medium (Gas, Staub)

2. **Gefahrenbereiche**
   - Lagerräume für Gefahrstoffe
   - Produktionsbereiche
   - Tankbereiche

3. **Schutzmaßnahmen**
   - Lüftung
   - Ex-geschützte Geräte
   - Zonengrenzen

Antworte als JSON.""",
    }
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Führt Vision-Analyse durch."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        pdf_content = input_data.get("pdf_content")
        pdf_path = input_data.get("pdf_path")
        image_content = input_data.get("image_content")
        analyse_typ = input_data.get("analyse_typ", "brandschutz")
        llm_provider = input_data.get("llm_provider", "openai")
        
        # Bild aus PDF extrahieren oder direkt verwenden
        image_base64 = None
        
        if image_content:
            image_base64 = base64.b64encode(image_content).decode("utf-8")
        elif pdf_content or pdf_path:
            image_base64 = self._extract_image_from_pdf(pdf_content, pdf_path)
        
        if not image_base64:
            result.add_error("Kein Bild oder PDF zum Analysieren")
            return result
        
        # Vision-LLM aufrufen
        try:
            prompt = self.PROMPTS.get(analyse_typ, self.PROMPTS["allgemein"])
            
            if llm_provider == "openai":
                raw_response = self._analyze_with_openai(image_base64, prompt)
            elif llm_provider == "anthropic":
                raw_response = self._analyze_with_anthropic(image_base64, prompt)
            else:
                result.add_error(f"Unbekannter LLM-Provider: {llm_provider}")
                return result
            
            if not raw_response:
                result.add_error("Keine Antwort vom Vision-LLM")
                return result
            
            # Antwort parsen
            analyse = self._parse_response(raw_response)
            
        except Exception as e:
            result.add_error(f"Vision-Analyse fehlgeschlagen: {e}")
            logger.exception(f"[{self.name}] Fehler bei Vision-Analyse")
            return result
        
        # Ergebnis
        result.data["vision_analyse"] = analyse.to_dict()
        result.data["analyse_typ"] = analyse_typ
        result.data["llm_provider"] = llm_provider
        result.data["anzahl_symbole"] = len(analyse.erkannte_symbole)
        result.data["anzahl_fluchtwege"] = len(analyse.erkannte_fluchtwege)
        
        result.status = HandlerStatus.SUCCESS
        logger.info(f"[{self.name}] Vision-Analyse abgeschlossen: "
                   f"{len(analyse.erkannte_symbole)} Symbole, "
                   f"{len(analyse.erkannte_fluchtwege)} Fluchtwege")
        
        return result
    
    def _extract_image_from_pdf(self, pdf_content: bytes = None, pdf_path: str = None) -> Optional[str]:
        """Extrahiert erste Seite als Bild aus PDF."""
        try:
            import fitz  # PyMuPDF
            
            if pdf_path:
                doc = fitz.open(pdf_path)
            else:
                doc = fitz.open(stream=pdf_content, filetype="pdf")
            
            # Erste Seite als Bild rendern
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x Zoom für bessere Qualität
            
            # Als PNG-Bytes
            image_bytes = pix.tobytes("png")
            doc.close()
            
            return base64.b64encode(image_bytes).decode("utf-8")
            
        except ImportError:
            logger.warning(f"[{self.name}] PyMuPDF nicht installiert")
            return None
        except Exception as e:
            logger.warning(f"[{self.name}] PDF-Extraktion fehlgeschlagen: {e}")
            return None
    
    def _analyze_with_openai(self, image_base64: str, prompt: str) -> Optional[str]:
        """Analysiert Bild mit OpenAI GPT-4V."""
        try:
            import os
            import openai
            
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning(f"[{self.name}] Kein OpenAI API Key")
                return None
            
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",  # oder gpt-4-vision-preview
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=4000,
                temperature=0.1,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"[{self.name}] OpenAI Vision fehlgeschlagen: {e}")
            return None
    
    def _analyze_with_anthropic(self, image_base64: str, prompt: str) -> Optional[str]:
        """Analysiert Bild mit Anthropic Claude Vision."""
        try:
            import os
            import anthropic
            
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning(f"[{self.name}] Kein Anthropic API Key")
                return None
            
            client = anthropic.Anthropic(api_key=api_key)
            
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.warning(f"[{self.name}] Anthropic Vision fehlgeschlagen: {e}")
            return None
    
    def _parse_response(self, raw_response: str) -> VisionAnalyseErgebnis:
        """Parst die LLM-Antwort in strukturierte Daten."""
        analyse = VisionAnalyseErgebnis(raw_response=raw_response)
        
        # JSON aus Antwort extrahieren
        try:
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # Symbole
                for s in data.get("symbole", []):
                    analyse.erkannte_symbole.append(ErkannteSymbol(
                        typ=s.get("typ", ""),
                        position_beschreibung=s.get("position", ""),
                        position_x_prozent=float(s.get("x_prozent", 0)),
                        position_y_prozent=float(s.get("y_prozent", 0)),
                    ))
                
                # Fluchtwege
                for f in data.get("fluchtwege", []):
                    analyse.erkannte_fluchtwege.append(ErkannterFluchtweg(
                        start=f.get("start", ""),
                        ende=f.get("ende", ""),
                        laenge_geschaetzt=f.get("laenge", ""),
                    ))
                
                # Räume
                analyse.erkannte_raeume = data.get("raeume", [])
                
                # Türen
                analyse.erkannte_tueren = data.get("tueren", [])
                
                # Texte
                analyse.erkannte_texte = data.get("texte", [])
                
                # Zusammenfassung
                analyse.zusammenfassung = data.get("zusammenfassung", "")
                analyse.warnungen = data.get("warnungen", [])
                analyse.empfehlungen = data.get("empfehlungen", [])
                
        except json.JSONDecodeError:
            # Wenn kein JSON, Rohtext als Zusammenfassung
            analyse.zusammenfassung = raw_response
        
        return analyse


# Singleton
_vision_handler: Optional[PDFVisionHandler] = None

def get_pdf_vision_handler() -> PDFVisionHandler:
    """Gibt PDFVisionHandler-Instanz zurück."""
    global _vision_handler
    if _vision_handler is None:
        _vision_handler = PDFVisionHandler()
    return _vision_handler
