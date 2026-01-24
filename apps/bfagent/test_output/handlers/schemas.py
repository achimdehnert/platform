"""
Pydantic schemas for handler data validation
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Any, Literal
from decimal import Decimal


class HandlerConfig(BaseModel):
    """Base configuration for handlers"""
    handler: str
    config: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "forbid"


class ChapterDataConfig(BaseModel):
    """Configuration for ChapterDataHandler"""
    include_outline: bool = False
    include_characters: bool = False
    include_content: bool = False
    include_ai_content: bool = False
    chapter_ids: Optional[List[int]] = None
    limit: Optional[int] = Field(None, gt=0, le=100)
    order_by: str = "chapter_number"
    
    @validator('order_by')
    def validate_order_by(cls, v):
        allowed = ['chapter_number', '-chapter_number', 'title', 'created_at']
        if v not in allowed:
            raise ValueError(f"order_by must be one of {allowed}")
        return v


class LLMProcessorConfig(BaseModel):
    """Configuration for LLMProcessingHandler"""
    llm_id: Optional[int] = None
    llm_name: Optional[str] = None
    fallback_llm_id: Optional[int] = None
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4000, ge=1, le=100000)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    stream: bool = False
    
    @root_validator
    def validate_llm_selection(cls, values):
        if not values.get('llm_id') and not values.get('llm_name'):
            raise ValueError("Must specify either 'llm_id' or 'llm_name'")
        return values


class SimpleTextFieldConfig(BaseModel):
    """Configuration for SimpleTextFieldHandler"""
    target_model: Literal["BookProjects", "BookChapters", "Characters"]
    target_field: str = Field(..., min_length=1)
    target_instance: Literal["current", "specific"] = "current"
    target_instance_id: Optional[int] = None
    action_name: str = "text_generation"
    min_length: int = Field(0, ge=0)
    max_length: int = Field(100000, ge=1)


# Add more schemas as needed...
