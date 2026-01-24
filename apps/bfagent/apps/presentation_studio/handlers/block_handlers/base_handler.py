"""Base Block Handler - Abstract base for all block handlers"""
from abc import ABC, abstractmethod
from pptx.util import Inches, Pt
import logging

logger = logging.getLogger(__name__)

# Slide dimensions (standard 10" x 7.5")
SLIDE_WIDTH = 10.0
SLIDE_HEIGHT = 7.5
MAX_Y = 7.0  # Leave 0.5" margin at bottom


class BaseBlockHandler(ABC):
    """Abstract base class for block handlers"""
    
    def __init__(self, slide, current_y=1.0):
        """
        Initialize block handler
        
        Args:
            slide: PPTX slide object
            current_y: Current Y position in inches
        """
        self.slide = slide
        self.current_y = current_y
    
    @abstractmethod
    def render(self, content, styling, layout):
        """
        Render the block on the slide
        
        Args:
            content: Block content dict
            styling: Styling parameters dict
            layout: Layout parameters dict
            
        Returns:
            float: New Y position after rendering
        """
        pass
    
    def estimate_height(self, content, styling, layout):
        """
        Estimate the height this block will need in inches
        
        Args:
            content: Block content dict
            styling: Styling parameters dict
            layout: Layout parameters dict
            
        Returns:
            float: Estimated height in inches
        """
        # Default implementation - subclasses can override for better estimates
        # This returns a conservative estimate
        return 2.0
    
    def _get_font_size(self, styling, key, default):
        """Helper to get font size from styling"""
        return Pt(styling.get(key, default))
    
    def _get_position(self, layout, default_x=0.5, default_y=None):
        """Helper to get position from layout"""
        if default_y is None:
            default_y = self.current_y
        
        position = layout.get('position', '')
        x = Inches(0.5 if 'left' in position else 5 if 'right' in position else default_x)
        y = Inches(layout.get('y', default_y))
        
        return x, y
    
    def _calculate_safe_height(self, desired_height):
        """
        Calculate safe height that doesn't exceed slide bounds
        
        Args:
            desired_height: Desired height in inches
            
        Returns:
            float: Safe height in inches that fits within slide
        """
        available_space = MAX_Y - self.current_y
        safe_height = min(desired_height, max(0.5, available_space))
        
        if safe_height < desired_height:
            logger.warning(
                f"Reduced height from {desired_height}\" to {safe_height}\" "
                f"to fit within slide (current_y={self.current_y}\")"
            )
        
        return safe_height
