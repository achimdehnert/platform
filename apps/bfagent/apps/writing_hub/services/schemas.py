"""
Pydantic Schemas für Creative Agent
====================================

Robuste Output-Validierung mit Pydantic für garantierte Korrektheit.
Diese Schemas definieren exakt, was der LLM zurückgeben muss.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, model_validator
import json
import re
import logging

logger = logging.getLogger(__name__)


class CharacterSchema(BaseModel):
    """Schema für einen Charakter."""
    name: str = Field(..., min_length=1, description="Name des Charakters")
    role: str = Field(default="Nebencharakter", description="Rolle: Protagonist, Antagonist, Nebencharakter")
    description: str = Field(default="", description="Beschreibung des Charakters")
    motivation: str = Field(default="", description="Motivation des Charakters")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = ['Protagonist', 'Antagonist', 'Nebencharakter', 'protagonist', 'antagonist', 'nebencharakter']
        if v.lower() not in [r.lower() for r in valid_roles]:
            return 'Nebencharakter'
        return v.capitalize() if v.lower() in ['protagonist', 'antagonist', 'nebencharakter'] else v


class WorldSchema(BaseModel):
    """Schema für eine Welt."""
    name: str = Field(default="", description="Name der Welt")
    description: str = Field(default="", description="Beschreibung der Welt")
    key_features: List[str] = Field(default_factory=list, description="Schlüsselmerkmale")
    atmosphere: str = Field(default="", description="Atmosphäre der Welt")


class IdeaSchema(BaseModel):
    """Schema für eine Buchidee - garantiert valide Struktur."""
    title_sketch: str = Field(..., min_length=1, description="Arbeitstitel der Idee")
    hook: str = Field(..., min_length=10, description="Hook/Logline (mind. 10 Zeichen)")
    genre: str = Field(default="", description="Genre der Geschichte")
    setting_sketch: str = Field(default="", description="Setting-Beschreibung")
    protagonist_sketch: str = Field(default="", description="Protagonist-Beschreibung")
    conflict_sketch: str = Field(default="", description="Konflikt-Beschreibung")
    characters: List[CharacterSchema] = Field(default_factory=list, description="Charaktere")
    world: Optional[WorldSchema] = Field(default=None, description="Weltenbau")
    
    @field_validator('title_sketch')
    @classmethod
    def clean_title(cls, v: str) -> str:
        # Entferne führende/trailing Whitespace und Anführungszeichen
        return v.strip().strip('"\'')
    
    @field_validator('hook')
    @classmethod
    def clean_hook(cls, v: str) -> str:
        return v.strip()
    
    @model_validator(mode='before')
    @classmethod
    def handle_alternative_keys(cls, data: Any) -> Any:
        """Mappe alternative Feldnamen auf Standard-Feldnamen."""
        if isinstance(data, dict):
            # title -> title_sketch
            if 'title' in data and 'title_sketch' not in data:
                data['title_sketch'] = data.pop('title')
            # logline -> hook
            if 'logline' in data and 'hook' not in data:
                data['hook'] = data.pop('logline')
            # setting -> setting_sketch
            if 'setting' in data and 'setting_sketch' not in data:
                data['setting_sketch'] = data.pop('setting')
            # protagonist -> protagonist_sketch
            if 'protagonist' in data and 'protagonist_sketch' not in data:
                data['protagonist_sketch'] = data.pop('protagonist')
            # conflict -> conflict_sketch
            if 'conflict' in data and 'conflict_sketch' not in data:
                data['conflict_sketch'] = data.pop('conflict')
        return data


class IdeasListSchema(BaseModel):
    """Schema für eine Liste von Ideen."""
    ideas: List[IdeaSchema] = Field(..., min_length=1, description="Liste von Buchideen")


class PremiseSchema(BaseModel):
    """Schema für eine vollständige Premise."""
    premise: str = Field(..., min_length=50, description="Die vollständige Premise")
    themes: List[str] = Field(default_factory=list, description="Zentrale Themen")
    unique_selling_points: List[str] = Field(default_factory=list, description="USPs")
    protagonist_detail: str = Field(default="", description="Detaillierte Protagonisten-Beschreibung")
    antagonist_sketch: str = Field(default="", description="Antagonist-Skizze")
    stakes: str = Field(default="", description="Was steht auf dem Spiel")


class LLMResponseParser:
    """
    Robuster Parser für LLM-Antworten.
    
    Garantiert korrektes Output durch:
    1. Mehrere Extraktionsstrategien
    2. Pydantic-Validierung
    3. Detailliertes Error Reporting
    """
    
    @staticmethod
    def extract_json(content: str) -> Optional[Any]:
        """
        Extrahiert JSON aus LLM-Antwort mit mehreren Strategien.
        
        Returns:
            Parsed JSON oder None bei Fehler
        """
        if not content:
            return None
        
        # 1. Entferne <think>...</think> Blöcke (Reasoning Models)
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        
        # 2. Versuche JSON aus Code-Block zu extrahieren
        code_block_patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
            r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
        ]
        
        for pattern in code_block_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        
        # 3. Finde balanciertes JSON-Array ZUERST (wichtig bei [{},...])
        result = LLMResponseParser._find_balanced_json(content, '[', ']')
        if result:
            return result
        
        # 4. Finde balanciertes JSON-Objekt
        result = LLMResponseParser._find_balanced_json(content, '{', '}')
        if result:
            return result
        
        # 5. Versuche direktes Parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        return None
    
    @staticmethod
    def _find_balanced_json(content: str, open_char: str, close_char: str) -> Optional[Any]:
        """Findet und parst balanciertes JSON."""
        start = content.find(open_char)
        if start == -1:
            return None
        
        depth = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(content[start:], start):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(content[start:i+1])
                    except json.JSONDecodeError:
                        return None
        
        return None
    
    @classmethod
    def parse_idea(cls, content: str) -> tuple[Optional[IdeaSchema], Optional[str]]:
        """
        Parst eine einzelne Idee aus LLM-Antwort.
        
        Returns:
            (IdeaSchema, None) bei Erfolg
            (None, error_message) bei Fehler
        """
        data = cls.extract_json(content)
        if data is None:
            return None, "Konnte kein JSON aus der Antwort extrahieren"
        
        try:
            # Direkt als Idee parsen
            if isinstance(data, dict):
                # Check ob es eine einzelne Idee ist
                if 'title_sketch' in data or 'title' in data or 'hook' in data:
                    idea = IdeaSchema.model_validate(data)
                    return idea, None
                
                # Check ob ideas-Liste enthalten
                if 'ideas' in data and data['ideas']:
                    idea = IdeaSchema.model_validate(data['ideas'][0])
                    return idea, None
            
            return None, f"Unerwartetes Datenformat: {type(data)}"
            
        except Exception as e:
            return None, f"Validierungsfehler: {str(e)}"
    
    @classmethod
    def parse_ideas_list(cls, content: str) -> tuple[List[IdeaSchema], Optional[str]]:
        """
        Parst eine Liste von Ideen aus LLM-Antwort.
        
        Returns:
            ([IdeaSchema, ...], None) bei Erfolg
            ([], error_message) bei Fehler
        """
        data = cls.extract_json(content)
        if data is None:
            return [], "Konnte kein JSON aus der Antwort extrahieren"
        
        ideas = []
        errors = []
        
        try:
            # Array von Ideen
            if isinstance(data, list):
                for i, item in enumerate(data):
                    try:
                        idea = IdeaSchema.model_validate(item)
                        ideas.append(idea)
                    except Exception as e:
                        errors.append(f"Idee {i+1}: {str(e)}")
            
            # Objekt mit ideas-Key
            elif isinstance(data, dict):
                items = data.get('ideas') or data.get('book_ideas') or data.get('buchideen') or []
                if items:
                    for i, item in enumerate(items):
                        try:
                            idea = IdeaSchema.model_validate(item)
                            ideas.append(idea)
                        except Exception as e:
                            errors.append(f"Idee {i+1}: {str(e)}")
                # Einzelne Idee
                elif 'title_sketch' in data or 'title' in data:
                    try:
                        idea = IdeaSchema.model_validate(data)
                        ideas.append(idea)
                    except Exception as e:
                        errors.append(f"Einzelidee: {str(e)}")
            
            if ideas:
                return ideas, None
            elif errors:
                return [], f"Validierungsfehler: {'; '.join(errors)}"
            else:
                return [], "Keine Ideen im Response gefunden"
                
        except Exception as e:
            return [], f"Parse-Fehler: {str(e)}"
    
    @classmethod
    def parse_premise(cls, content: str) -> tuple[Optional[PremiseSchema], Optional[str]]:
        """
        Parst eine Premise aus LLM-Antwort.
        
        Returns:
            (PremiseSchema, None) bei Erfolg
            (None, error_message) bei Fehler
        """
        data = cls.extract_json(content)
        if data is None:
            return None, "Konnte kein JSON aus der Antwort extrahieren"
        
        try:
            if isinstance(data, dict):
                premise = PremiseSchema.model_validate(data)
                return premise, None
            return None, f"Unerwartetes Datenformat: {type(data)}"
        except Exception as e:
            return None, f"Validierungsfehler: {str(e)}"


def get_idea_json_schema() -> dict:
    """Gibt das JSON Schema für eine Idee zurück (für LLM-Prompts)."""
    return IdeaSchema.model_json_schema()


def get_ideas_list_json_schema() -> dict:
    """Gibt das JSON Schema für eine Ideenliste zurück."""
    return IdeasListSchema.model_json_schema()


def get_premise_json_schema() -> dict:
    """Gibt das JSON Schema für eine Premise zurück."""
    return PremiseSchema.model_json_schema()
