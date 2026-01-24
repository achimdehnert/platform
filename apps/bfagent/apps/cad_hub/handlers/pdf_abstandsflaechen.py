"""
PDF Abstandsflächenplan Handler.

Extrahiert Informationen aus Abstandsflächenplänen im PDF-Format:
- Wandhöhen pro Fassade
- Abstandsflächen-Tiefen (0.4H / 0.5H nach BayBO)
- Überschreitungen auf Nachbargrundstücke
- Überdeckungen eigener Abstandsflächen
- Compliance-Status

Verwendet:
- PyMuPDF für Text-Extraktion
- Optional: Vision LLM für Geometrie-Interpretation
"""
import io
import re
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from .base import (
    BaseCADHandler,
    CADHandlerResult,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


class Himmelsrichtung(Enum):
    """Himmelsrichtungen für Fassaden."""
    NORD = "nord"
    NORDOST = "nordost"
    OST = "ost"
    SUEDOST = "südost"
    SUED = "süd"
    SUEDWEST = "südwest"
    WEST = "west"
    NORDWEST = "nordwest"


class ComplianceStatus(Enum):
    """Status der Abstandsflächenprüfung."""
    ERFUELLT = "erfüllt"
    NICHT_ERFUELLT = "nicht_erfüllt"
    TEILWEISE = "teilweise"
    UNBEKANNT = "unbekannt"


@dataclass
class Fassade:
    """Fassadendaten für Abstandsflächen."""
    bezeichnung: str = ""
    richtung: str = ""  # Nord, Süd, Ost, West
    wandhoehe_m: float = 0.0
    wandlaenge_m: float = 0.0
    faktor: float = 0.4  # 0.4H oder 0.5H (Kerngebiet)
    abstandsflaeche_tiefe_m: float = 0.0  # = wandhoehe * faktor
    mindestabstand_m: float = 3.0  # Mindestens 3m nach BayBO
    
    def berechne_tiefe(self) -> float:
        """Berechnet Abstandsflächen-Tiefe."""
        berechnet = self.wandhoehe_m * self.faktor
        return max(berechnet, self.mindestabstand_m)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["berechnet_tiefe_m"] = self.berechne_tiefe()
        return d


@dataclass
class Ueberschreitung:
    """Überschreitung auf Nachbargrundstück."""
    fassade: str = ""
    flaeche_m2: float = 0.0
    tiefe_m: float = 0.0
    nachbar_flurstueck: str = ""
    zustimmung_erforderlich: bool = True
    zustimmung_vorhanden: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AbstandsflaechenInfo:
    """Gesamtinformationen aus Abstandsflächenplan."""
    fassaden: list[Fassade] = field(default_factory=list)
    ueberschreitungen: list[Ueberschreitung] = field(default_factory=list)
    ueberdeckungen: list[dict] = field(default_factory=list)  # Eigene AF überdecken sich
    
    # Prüfergebnis
    status: str = ComplianceStatus.UNBEKANNT.value
    pruef_bemerkungen: list[str] = field(default_factory=list)
    
    # Rechtliche Grundlage
    rechtsgrundlage: str = "BayBO Art. 6"  # Default Bayern
    faktor_standard: float = 0.4  # 0.4H Standard, 0.5H im Kerngebiet
    mindestabstand: float = 3.0  # Meter
    
    # Metadaten
    massstab: str = ""
    raw_text: str = ""
    
    def to_dict(self) -> dict:
        return {
            "fassaden": [f.to_dict() for f in self.fassaden],
            "ueberschreitungen": [u.to_dict() for u in self.ueberschreitungen],
            "ueberdeckungen": self.ueberdeckungen,
            "status": self.status,
            "pruef_bemerkungen": self.pruef_bemerkungen,
            "rechtsgrundlage": self.rechtsgrundlage,
            "faktor_standard": self.faktor_standard,
            "mindestabstand": self.mindestabstand,
            "massstab": self.massstab,
        }
    
    def gesamt_ueberschreitung_m2(self) -> float:
        """Summe aller Überschreitungen."""
        return sum(u.flaeche_m2 for u in self.ueberschreitungen)
    
    def pruefe_compliance(self) -> str:
        """Prüft Gesamtstatus."""
        if not self.ueberschreitungen:
            return ComplianceStatus.ERFUELLT.value
        
        alle_mit_zustimmung = all(
            u.zustimmung_vorhanden for u in self.ueberschreitungen
        )
        if alle_mit_zustimmung:
            return ComplianceStatus.ERFUELLT.value
        
        return ComplianceStatus.NICHT_ERFUELLT.value


class PDFAbstandsflaechenHandler(BaseCADHandler):
    """
    Handler für Abstandsflächenplan-Extraktion aus PDF.
    
    Funktionen:
    - Text-Extraktion für Wandhöhen und Maße
    - Berechnung der Abstandsflächen nach BayBO
    - Prüfung auf Überschreitungen
    - Optional: LLM für komplexe Interpretation
    
    Input:
        pdf_content: bytes - PDF-Datei als Bytes
        pdf_path: str - Pfad zur PDF-Datei
        use_llm: bool - LLM für Interpretation verwenden
        bundesland: str - Für korrekte Bauordnung (default: Bayern)
    
    Output:
        abstandsflaechen: AbstandsflaechenInfo mit allen extrahierten Daten
    """
    
    name = "PDFAbstandsflaechenHandler"
    description = "Extrahiert Daten aus Abstandsflächenplan-PDFs"
    required_inputs = []
    optional_inputs = ["pdf_content", "pdf_path", "use_llm", "bundesland"]
    
    # Bauordnungs-Faktoren nach Bundesland
    LANDESBAUORDNUNG = {
        "bayern": {"faktor": 0.4, "kerngebiet": 0.5, "mindest": 3.0, "name": "BayBO Art. 6"},
        "bw": {"faktor": 0.4, "kerngebiet": 0.5, "mindest": 2.5, "name": "LBO BW §5"},
        "nrw": {"faktor": 0.4, "kerngebiet": 0.5, "mindest": 3.0, "name": "BauO NRW §6"},
        "hessen": {"faktor": 0.4, "kerngebiet": 0.5, "mindest": 3.0, "name": "HBO §6"},
        "default": {"faktor": 0.4, "kerngebiet": 0.5, "mindest": 3.0, "name": "LBO §6"},
    }
    
    # Regex-Patterns
    PATTERNS = {
        "wandhoehe": [
            r"(?:Wand)?[Hh](?:öhe)?[\s:=]*(\d+[.,]\d+)\s*m",
            r"H\s*=\s*(\d+[.,]\d+)",
            r"(\d+[.,]\d+)\s*m\s*(?:Wandhöhe|Traufhöhe|Firsthöhe)",
        ],
        "abstandsflaeche": [
            r"(?:Abstandsfläche|AF)[\s:=]*(\d+[.,]\d+)\s*m",
            r"(\d+[.,]\d+)\s*m\s*(?:Abstandsfläche|AF)",
            r"0[,.]4\s*[×xX*]\s*H\s*=\s*(\d+[.,]\d+)",
            r"0[,.]5\s*[×xX*]\s*H\s*=\s*(\d+[.,]\d+)",
        ],
        "richtung": [
            r"(Nord|Süd|Ost|West|NO|NW|SO|SW)(?:seite|fassade|wand)?",
        ],
        "ueberschreitung": [
            r"(?:Überschreitung|überschreitet)[\s:]*(\d+[.,]\d+)\s*(?:m²|qm)",
            r"(\d+[.,]\d+)\s*(?:m²|qm)\s*(?:Überschreitung|auf Nachbar)",
        ],
        "faktor": [
            r"(0[,.]4)\s*[×xX*]\s*H",
            r"(0[,.]5)\s*[×xX*]\s*H",
            r"Faktor[\s:]*(\d+[.,]\d+)",
        ],
        "massstab": [
            r"(?:Maßstab|M\.?|1\s*:)\s*(\d+)",
            r"1\s*:\s*(\d+)",
        ],
    }
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Extrahiert Abstandsflächen-Informationen aus PDF."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        pdf_content = input_data.get("pdf_content")
        pdf_path = input_data.get("pdf_path")
        use_llm = input_data.get("use_llm", True)
        bundesland = input_data.get("bundesland", "bayern").lower()
        
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
        
        # Landesbauordnung
        lbo = self.LANDESBAUORDNUNG.get(bundesland, self.LANDESBAUORDNUNG["default"])
        
        # AbstandsflaechenInfo erstellen
        af_info = AbstandsflaechenInfo(
            raw_text=full_text[:2000],
            rechtsgrundlage=lbo["name"],
            faktor_standard=lbo["faktor"],
            mindestabstand=lbo["mindest"],
        )
        
        # 1. Pattern-basierte Extraktion
        af_info = self._extract_with_patterns(full_text, af_info, lbo)
        
        # 2. LLM-basierte Extraktion (falls aktiviert)
        if use_llm:
            af_info = self._extract_with_llm(full_text, af_info, lbo)
        
        # 3. Berechnungen und Prüfung
        af_info = self._calculate_and_check(af_info, lbo)
        
        # Ergebnis
        result.data["abstandsflaechen"] = af_info.to_dict()
        result.data["compliance_status"] = af_info.status
        result.data["gesamt_ueberschreitung_m2"] = af_info.gesamt_ueberschreitung_m2()
        result.data["raw_text_preview"] = full_text[:500]
        result.data["bundesland"] = bundesland
        result.data["rechtsgrundlage"] = lbo["name"]
        
        result.status = HandlerStatus.SUCCESS
        logger.info(f"[{self.name}] Abstandsflächen: {len(af_info.fassaden)} Fassaden, Status: {af_info.status}")
        
        return result
    
    def _extract_with_patterns(self, text: str, af_info: AbstandsflaechenInfo, lbo: dict) -> AbstandsflaechenInfo:
        """Extrahiert Daten mit Regex-Patterns."""
        
        # Maßstab
        for pattern in self.PATTERNS["massstab"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                af_info.massstab = f"1:{match.group(1)}"
                break
        
        # Wandhöhen finden und Fassaden erstellen
        richtungen_gefunden = []
        for pattern in self.PATTERNS["richtung"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            richtungen_gefunden.extend(matches)
        
        # Wandhöhen extrahieren
        hoehen = []
        for pattern in self.PATTERNS["wandhoehe"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            hoehen.extend([float(h.replace(",", ".")) for h in matches])
        
        # Faktoren extrahieren
        faktoren = []
        for pattern in self.PATTERNS["faktor"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            faktoren.extend([float(f.replace(",", ".")) for f in matches])
        
        # Fassaden erstellen
        default_richtungen = ["Nord", "Ost", "Süd", "West"]
        for i, hoehe in enumerate(hoehen[:4]):  # Max 4 Fassaden
            richtung = richtungen_gefunden[i] if i < len(richtungen_gefunden) else default_richtungen[i % 4]
            faktor = faktoren[i] if i < len(faktoren) else lbo["faktor"]
            
            fassade = Fassade(
                bezeichnung=f"Fassade {richtung}",
                richtung=richtung,
                wandhoehe_m=hoehe,
                faktor=faktor,
                mindestabstand_m=lbo["mindest"],
            )
            fassade.abstandsflaeche_tiefe_m = fassade.berechne_tiefe()
            af_info.fassaden.append(fassade)
        
        # Überschreitungen
        for pattern in self.PATTERNS["ueberschreitung"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                ueberschreitung = Ueberschreitung(
                    flaeche_m2=float(m.replace(",", ".")),
                    zustimmung_erforderlich=True,
                )
                af_info.ueberschreitungen.append(ueberschreitung)
        
        return af_info
    
    def _extract_with_llm(self, text: str, af_info: AbstandsflaechenInfo, lbo: dict) -> AbstandsflaechenInfo:
        """Extrahiert komplexe Informationen mit LLM."""
        try:
            try:
                from apps.bfagent.services.llm_client import generate_text
            except ImportError:
                import os
                import openai
                
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    return af_info
                
                client = openai.OpenAI(api_key=api_key)
                
                def generate_text(prompt, max_tokens=500):
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=0.1,
                    )
                    return response.choices[0].message.content
            
            prompt = f"""Analysiere diesen Abstandsflächenplan-Text und extrahiere die Informationen.

Text (Auszug):
{text[:3000]}

Extrahiere als JSON:
- fassaden: Liste mit {{richtung, wandhoehe_m, faktor}}
- ueberschreitungen: Liste mit {{flaeche_m2, nachbar}}
- status: "erfüllt" oder "nicht_erfüllt"
- bemerkungen: Wichtige Hinweise

Rechtsgrundlage: {lbo['name']} (Faktor {lbo['faktor']}H, mind. {lbo['mindest']}m)

Antworte NUR mit JSON."""

            response = generate_text(prompt, max_tokens=500)
            if response:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        
                        # Fassaden ergänzen falls nicht vorhanden
                        if not af_info.fassaden and data.get("fassaden"):
                            for f in data["fassaden"]:
                                fassade = Fassade(
                                    richtung=f.get("richtung", ""),
                                    wandhoehe_m=float(f.get("wandhoehe_m", 0)),
                                    faktor=float(f.get("faktor", lbo["faktor"])),
                                    mindestabstand_m=lbo["mindest"],
                                )
                                fassade.abstandsflaeche_tiefe_m = fassade.berechne_tiefe()
                                af_info.fassaden.append(fassade)
                        
                        # Status
                        if data.get("status"):
                            af_info.status = data["status"]
                        
                        # Bemerkungen
                        if data.get("bemerkungen"):
                            if isinstance(data["bemerkungen"], list):
                                af_info.pruef_bemerkungen.extend(data["bemerkungen"])
                            else:
                                af_info.pruef_bemerkungen.append(str(data["bemerkungen"]))
                        
                        logger.info(f"[{self.name}] LLM extraction successful")
                    except json.JSONDecodeError:
                        pass
                    
        except Exception as e:
            logger.warning(f"[{self.name}] LLM extraction failed: {e}")
        
        return af_info
    
    def _calculate_and_check(self, af_info: AbstandsflaechenInfo, lbo: dict) -> AbstandsflaechenInfo:
        """Berechnet Abstandsflächen und prüft Compliance."""
        
        # Abstandsflächen-Tiefen berechnen
        for fassade in af_info.fassaden:
            if fassade.abstandsflaeche_tiefe_m == 0:
                fassade.abstandsflaeche_tiefe_m = fassade.berechne_tiefe()
        
        # Compliance prüfen
        if af_info.status == ComplianceStatus.UNBEKANNT.value:
            af_info.status = af_info.pruefe_compliance()
        
        # Prüfbemerkungen ergänzen
        if af_info.ueberschreitungen:
            gesamt = af_info.gesamt_ueberschreitung_m2()
            af_info.pruef_bemerkungen.append(
                f"Gesamt-Überschreitung: {gesamt:.1f} m² auf Nachbargrundstück(e)"
            )
        
        for fassade in af_info.fassaden:
            if fassade.wandhoehe_m > 0:
                tiefe = fassade.berechne_tiefe()
                af_info.pruef_bemerkungen.append(
                    f"{fassade.richtung}: H={fassade.wandhoehe_m}m → AF={tiefe:.2f}m"
                )
        
        return af_info
