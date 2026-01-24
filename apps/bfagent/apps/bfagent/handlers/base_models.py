"""
Handler Input/Output Pydantic Models
Strict validation for handler execution
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class HandlerInput(BaseModel):
    """Base input model for all handlers"""
    workflow_id: Optional[int] = None
    user_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        frozen = True  # Immutable
        validate_assignment = True


class HandlerOutput(BaseModel):
    """Base output model for all handlers"""
    success: bool
    data: Dict[str, Any]
    errors: list[str] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        frozen = True


class EnrichmentInput(HandlerInput):
    """Input for enrichment handlers"""
    project_id: int = Field(..., gt=0, description="Project ID")
    action: str = Field(..., pattern=r'^[a-z_]+$', description="Action name")
    agent_id: Optional[int] = Field(None, gt=0, description="Agent ID")
    requirements: str = Field("", max_length=5000, description="User requirements")
    
    @validator('action')
    def validate_action(cls, v):
        """Validate action is in allowed list"""
        allowed_actions = [
            'enhance_description',
            'generate_character_cast',
            'generate_outline',
            'create_world',
        ]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of: {', '.join(allowed_actions)}")
        return v
    
    class Config:
        frozen = True
        schema_extra = {
            "example": {
                "project_id": 1,
                "action": "enhance_description",
                "requirements": "Make it more dramatic"
            }
        }


class EnrichmentOutput(HandlerOutput):
    """Output from enrichment handlers"""
    enriched_text: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    suggestions: list[str] = Field(default_factory=list)
    
    class Config:
        frozen = True
