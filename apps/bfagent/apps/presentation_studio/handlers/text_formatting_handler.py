"""
Text Formatting Handler for PPTX Studio
Uses BaseHandler Framework V2
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from apps.bfagent.handlers.base_handler_v2 import BaseHandler
import re


class TextFormattingInput(BaseModel):
    """Input schema for text formatting"""
    text: str = Field(..., description="Text to format")
    format_type: str = Field(default='clean', description="Format type: clean, bullet, numbered, summary")
    max_length: Optional[int] = Field(default=None, description="Maximum text length")
    
    class Config:
        frozen = True


class TextFormattingOutput(BaseModel):
    """Output schema for text formatting"""
    formatted_text: str
    original_length: int
    formatted_length: int
    truncated: bool
    
    class Config:
        frozen = True


class TextFormattingHandler(BaseHandler[TextFormattingInput, TextFormattingOutput]):
    """
    Formats text for PowerPoint slides
    
    Capabilities:
    - Clean text (remove unwanted chars)
    - Create bullet points
    - Create numbered lists  
    - Generate summaries
    - Truncate to length
    """
    
    InputSchema = TextFormattingInput
    OutputSchema = TextFormattingOutput
    
    handler_name = "text_formatting"
    handler_version = "1.0.0"
    domain = "presentation_studio"
    category = "processing"
    
    def process(self, validated_input: TextFormattingInput) -> Dict[str, Any]:
        """
        Process text formatting
        
        Args:
            validated_input: Validated input
            
        Returns:
            Processing result dict
        """
        text = validated_input.text
        format_type = validated_input.format_type
        max_length = validated_input.max_length
        
        original_length = len(text)
        
        # Clean text first
        text = self._clean_text(text)
        
        # Apply format type
        if format_type == 'bullet':
            text = self._format_as_bullets(text)
        elif format_type == 'numbered':
            text = self._format_as_numbered(text)
        elif format_type == 'summary':
            text = self._create_summary(text, max_length or 200)
        
        # Truncate if needed
        truncated = False
        if max_length and len(text) > max_length:
            text = text[:max_length-3] + "..."
            truncated = True
        
        return {
            'formatted_text': text,
            'original_length': original_length,
            'formatted_length': len(text),
            'truncated': truncated
        }
    
    def _clean_text(self, text: str) -> str:
        """Remove unwanted characters and normalize whitespace"""
        if not text:
            return ""
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _format_as_bullets(self, text: str) -> str:
        """Format text as bullet points"""
        bullets = self._extract_lines(text)
        return '\n'.join(f"• {bullet}" for bullet in bullets if bullet)
    
    def _format_as_numbered(self, text: str) -> str:
        """Format text as numbered list"""
        items = self._extract_lines(text)
        return '\n'.join(f"{i+1}. {item}" for i, item in enumerate(items) if item)
    
    def _extract_lines(self, text: str) -> List[str]:
        """Extract meaningful lines from text"""
        lines = text.split('\n')
        result = []
        
        for line in lines:
            line = line.strip()
            # Remove existing bullet markers
            line = re.sub(r'^[•\-\*\d+\.]\s*', '', line)
            if line:
                result.append(line)
        
        return result
    
    def _create_summary(self, text: str, max_length: int) -> str:
        """Create a summary of text"""
        if len(text) <= max_length:
            return text
        
        # Try to cut at sentence boundary
        sentences = re.split(r'(?<=[.!?])\s+', text)
        summary = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) > max_length:
                break
            summary.append(sentence)
            current_length += len(sentence)
        
        if summary:
            return ' '.join(summary)
        else:
            return text[:max_length-3] + "..."
