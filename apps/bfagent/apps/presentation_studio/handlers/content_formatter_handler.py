"""
Content Formatter Handler for PPTX Studio
Handles formatting of various content types for slides
"""

import logging
from typing import Dict, List, Optional
import re

logger = logging.getLogger(__name__)


class ContentFormatterHandler:
    """
    Formats content for PowerPoint slides
    
    Handles:
    - Text formatting
    - Bullet point creation
    - Paragraph splitting
    - Content truncation
    - Special character handling
    """
    
    def __init__(self):
        self.max_title_length = 100
        self.max_content_length = 1000
    
    def format_title(self, title: str, max_length: Optional[int] = None) -> str:
        """
        Format title text
        
        Args:
            title: Raw title text
            max_length: Optional max length override
            
        Returns:
            Formatted title
        """
        if not title:
            return "Untitled"
        
        # Clean title
        title = self._clean_text(title)
        
        # Truncate if needed
        max_len = max_length or self.max_title_length
        if len(title) > max_len:
            title = title[:max_len-3] + "..."
        
        return title
    
    def format_content(
        self,
        content: str,
        content_type: str = 'paragraph',
        max_length: Optional[int] = None
    ) -> str:
        """
        Format content text
        
        Args:
            content: Raw content text
            content_type: Type ('paragraph', 'bullet', 'numbered')
            max_length: Optional max length override
            
        Returns:
            Formatted content
        """
        if not content:
            return ""
        
        # Clean content
        content = self._clean_text(content)
        
        # Format based on type
        if content_type == 'bullet':
            content = self._format_as_bullets(content)
        elif content_type == 'numbered':
            content = self._format_as_numbered(content)
        
        # Truncate if needed
        max_len = max_length or self.max_content_length
        if len(content) > max_len:
            content = content[:max_len-3] + "..."
        
        return content
    
    def split_into_paragraphs(self, text: str, max_per_paragraph: int = 200) -> List[str]:
        """
        Split text into paragraphs
        
        Args:
            text: Input text
            max_per_paragraph: Max chars per paragraph
            
        Returns:
            List of paragraphs
        """
        # Split by double newline first
        paragraphs = text.split('\n\n')
        
        result = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If paragraph is too long, split by sentences
            if len(para) > max_per_paragraph:
                sentences = self._split_sentences(para)
                current = []
                current_length = 0
                
                for sentence in sentences:
                    if current_length + len(sentence) > max_per_paragraph:
                        if current:
                            result.append(' '.join(current))
                        current = [sentence]
                        current_length = len(sentence)
                    else:
                        current.append(sentence)
                        current_length += len(sentence)
                
                if current:
                    result.append(' '.join(current))
            else:
                result.append(para)
        
        return result
    
    def extract_bullet_points(self, text: str) -> List[str]:
        """
        Extract bullet points from text
        
        Args:
            text: Input text
            
        Returns:
            List of bullet points
        """
        bullets = []
        
        # Check if already has bullet markers
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove existing bullet markers
            line = re.sub(r'^[•\-\*]\s*', '', line)
            
            if line:
                bullets.append(line)
        
        return bullets
    
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
        bullets = self.extract_bullet_points(text)
        return '\n'.join(f"• {bullet}" for bullet in bullets)
    
    def _format_as_numbered(self, text: str) -> str:
        """Format text as numbered list"""
        items = self.extract_bullet_points(text)
        return '\n'.join(f"{i+1}. {item}" for i, item in enumerate(items))
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def create_summary(self, text: str, max_length: int = 200) -> str:
        """
        Create a summary of text
        
        Args:
            text: Input text
            max_length: Max summary length
            
        Returns:
            Summary text
        """
        text = self._clean_text(text)
        
        if len(text) <= max_length:
            return text
        
        # Try to cut at sentence boundary
        sentences = self._split_sentences(text)
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
            # If no sentences fit, just truncate
            return text[:max_length-3] + "..."
    
    def merge_contents(self, contents: List[str], separator: str = '\n\n') -> str:
        """
        Merge multiple content pieces
        
        Args:
            contents: List of content strings
            separator: Separator between contents
            
        Returns:
            Merged content
        """
        # Filter out empty contents
        valid_contents = [c.strip() for c in contents if c and c.strip()]
        return separator.join(valid_contents)
