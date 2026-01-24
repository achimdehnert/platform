"""
JSON to Slides Handler - Orchestrator for modular block handlers
"""
import logging
from .block_handlers import (
    TitleHandler,
    QuoteHandler,
    TextBoxHandler,
    BulletListHandler,
    ObjectivesBoxHandler,
    TwoColumnComparisonHandler,
    DefinitionBoxHandler,
    VerticalBoxesHandler,
    FunctionListHandler,
    FallbackHandler,
)
from .block_handlers.base_handler import MAX_Y

logger = logging.getLogger(__name__)


class JsonToSlidesHandler:
    """Orchestrator for converting JSON structure to PPTX slides using modular handlers"""
    
    def __init__(self, prs, template_collection=None):
        self.prs = prs
        self.template_collection = template_collection
        self.current_y = 1.0  # Track Y position for dynamic positioning
        
        # Map block types to handler classes
        self.handler_map = {
            'title_block': TitleHandler,
            'quote_block': QuoteHandler,
            'text_box': TextBoxHandler,
            'bullet_list': BulletListHandler,
            'objectives_box': ObjectivesBoxHandler,
            'two_column_comparison': TwoColumnComparisonHandler,
            'definition_box': DefinitionBoxHandler,
            'vertical_boxes': VerticalBoxesHandler,
            'function_list': FunctionListHandler,
        }
    
    def create_slides_from_json(self, json_data):
        """Create slides from JSON"""
        slides = json_data.get('slides', [json_data]) if 'slides' in json_data or 'slide' in json_data else []
        created = []
        
        for slide_data in slides:
            try:
                idx = self._create_slide(slide_data)
                created.append(idx)
            except Exception as e:
                logger.error(f"Error creating slide: {e}")
        
        return created
    
    def _create_slide(self, data):
        """Create single slide with automatic pagination"""
        slide_info = data.get('slide', data)
        layout = self.prs.slide_layouts[6]  # Blank
        slide = self.prs.slides.add_slide(layout)
        
        # Reset Y position for each slide
        self.current_y = 1.0
        current_slide = slide
        
        # Add content blocks with automatic pagination
        for block in sorted(slide_info.get('content_blocks', []), key=lambda x: x.get('order', 999)):
            # Check if we need a new slide
            current_slide = self._check_and_create_new_slide_if_needed(
                current_slide, block
            )
            self._add_block(current_slide, block)
        
        return len(self.prs.slides) - 1
    
    def _check_and_create_new_slide_if_needed(self, current_slide, block):
        """
        Check if there's enough space for the next block, create new slide if needed
        
        Args:
            current_slide: Current slide object
            block: Block data to be rendered
            
        Returns:
            slide: Slide to use (current or new)
        """
        block_type = block.get('type')
        content = block.get('content', {})
        styling = block.get('styling', {})
        layout = block.get('layout', {})
        
        # Get handler to estimate height
        handler_class = self.handler_map.get(block_type, FallbackHandler)
        temp_handler = handler_class(current_slide, current_y=self.current_y)
        
        # Estimate height needed
        estimated_height = temp_handler.estimate_height(content, styling, layout)
        available_space = MAX_Y - self.current_y
        
        # If not enough space (less than 1" or less than estimated), create new slide
        min_required_space = min(1.0, estimated_height)
        
        if available_space < min_required_space:
            logger.info(
                f"Creating new slide for {block_type}: "
                f"needed ~{estimated_height:.1f}\", available {available_space:.1f}\", "
                f"at Y={self.current_y:.1f}"
            )
            layout_obj = self.prs.slide_layouts[6]  # Blank
            new_slide = self.prs.slides.add_slide(layout_obj)
            self.current_y = 1.0  # Reset Y position for new slide
            return new_slide
        
        return current_slide
    
    def _add_block(self, slide, block):
        """Add content block using appropriate handler"""
        block_type = block.get('type')
        content = block.get('content', {})
        styling = block.get('styling', {})
        layout = block.get('layout', {})
        
        # Get handler class for this block type
        handler_class = self.handler_map.get(block_type)
        
        if handler_class:
            # Use specialized handler
            handler = handler_class(slide, current_y=self.current_y)
            try:
                self.current_y = handler.render(content, styling, layout)
                logger.debug(f"Rendered {block_type} at Y={self.current_y:.2f}")
            except Exception as e:
                logger.error(f"Error rendering {block_type}: {e}", exc_info=True)
                # Fallback on error
                self._use_fallback(slide, block_type, content, styling, layout)
        else:
            # Unknown block type - use fallback
            logger.warning(f"Unknown block type: {block_type}, using fallback")
            self._use_fallback(slide, block_type, content, styling, layout)
    
    def _use_fallback(self, slide, block_type, content, styling, layout):
        """Use fallback handler for unknown or failed blocks"""
        handler = FallbackHandler(slide, current_y=self.current_y)
        self.current_y = handler.render(content, styling, layout, block_type=block_type)
    
    def _add_title(self, slide, content, styling):
        """Add title"""
        box = slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(9), Inches(1.5))
        box.text_frame.text = content.get('main_title', '')
        if box.text_frame.paragraphs:
            p = box.text_frame.paragraphs[0]
            p.font.size = Pt(styling.get('title_size', 44))
            p.font.bold = True
    
    def _add_quote(self, slide, content, styling):
        """Add quote"""
        box = slide.shapes.add_textbox(Inches(2), Inches(2), Inches(6), Inches(2))
        box.text_frame.text = f'"{content.get("quote", "")}"'
        if box.text_frame.paragraphs:
            p = box.text_frame.paragraphs[0]
            p.font.size = Pt(styling.get('quote_size', 22))
            p.font.italic = True
    
    def _add_textbox(self, slide, content, styling, layout):
        """Add text box"""
        width = Inches(4.5)
        left = Inches(0.5 if 'left' in layout.get('position', '') else 5)
        box = slide.shapes.add_textbox(left, Inches(2), width, Inches(4))
        
        # Heading
        if 'heading' in content:
            p = box.text_frame.paragraphs[0]
            p.text = content['heading']
            p.font.size = Pt(styling.get('heading_size', 24))
            p.font.bold = True
        
        # Body
        if 'body' in content:
            p = box.text_frame.add_paragraph()
            p.text = content['body']
            p.font.size = Pt(styling.get('body_size', 16))
    
    def _add_vertical_boxes(self, slide, content, styling, layout):
        """Add vertical boxes (e.g., 3 systems)"""
        title = content.get('title', '')
        boxes = content.get('boxes', [])
        
        # Title
        if title:
            title_box = slide.shapes.add_textbox(Inches(5), Inches(1), Inches(4.5), Inches(0.5))
            title_box.text_frame.text = title
            if title_box.text_frame.paragraphs:
                p = title_box.text_frame.paragraphs[0]
                p.font.size = Pt(styling.get('title_size', 22))
                p.font.bold = True
        
        # Boxes
        top = 2
        for box_data in boxes:
            box = slide.shapes.add_textbox(Inches(5), Inches(top), Inches(4.5), Inches(1))
            icon = box_data.get('icon', '')
            system = box_data.get('system', '')
            outcome = box_data.get('outcome', '')
            
            text = f"{icon} {system} → {outcome}"
            box.text_frame.text = text
            if box.text_frame.paragraphs:
                p = box.text_frame.paragraphs[0]
                p.font.size = Pt(styling.get('system_size', 16))
            
            top += 1.2
    
    def _add_objectives_box(self, slide, content, styling, layout):
        """Add objectives box"""
        heading = content.get('heading', '')
        objectives = content.get('objectives', [])
        
        box = slide.shapes.add_textbox(Inches(0.5), Inches(5), Inches(9), Inches(2))
        
        # Heading
        if heading:
            p = box.text_frame.paragraphs[0]
            p.text = heading
            p.font.size = Pt(styling.get('heading_size', 18))
            p.font.bold = True
        
        # Objectives
        for obj in objectives:
            p = box.text_frame.add_paragraph()
            checkmark = styling.get('checkmark', '✓')
            p.text = f"{checkmark} {obj}"
            p.font.size = Pt(styling.get('objective_size', 14))
            p.level = 1
    
    def _add_bullet_list(self, slide, content, styling, layout):
        """Add bullet list"""
        title = content.get('title', '')
        items = content.get('items', [])
        
        width = Inches(layout.get('width_percent', 80) / 10)
        left = Inches((10 - width.inches) / 2)
        box = slide.shapes.add_textbox(left, Inches(2), width, Inches(4))
        
        # Title
        if title:
            p = box.text_frame.paragraphs[0]
            p.text = title
            p.font.size = Pt(styling.get('title_size', 22))
            p.font.bold = True
        
        # Items
        for item in items:
            p = box.text_frame.add_paragraph()
            p.text = item
            p.font.size = Pt(styling.get('item_size', 16))
            p.level = 1
    
    def _add_definition_box(self, slide, content, styling, layout):
        """Add definition box"""
        term = content.get('term', '')
        definition = content.get('definition', '')
        metaphor = content.get('metaphor', '')
        
        box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(3))
        
        # Term
        if term:
            p = box.text_frame.paragraphs[0]
            p.text = term
            p.font.size = Pt(styling.get('term_size', 28))
            p.font.bold = True
        
        # Definition
        if definition:
            p = box.text_frame.add_paragraph()
            p.text = definition
            p.font.size = Pt(styling.get('definition_size', 16))
        
        # Metaphor
        if metaphor:
            p = box.text_frame.add_paragraph()
            p.text = f"\n{metaphor}"
            p.font.size = Pt(styling.get('metaphor_size', 18))
            p.font.italic = True
    
    def _add_two_column_comparison(self, slide, content, styling, layout):
        """Add two column comparison"""
        title = content.get('title', '')
        col_left = content.get('column_left', {})
        col_right = content.get('column_right', {})
        
        # Title
        if title:
            title_box = slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(9), Inches(0.5))
            title_box.text_frame.text = title
            if title_box.text_frame.paragraphs:
                p = title_box.text_frame.paragraphs[0]
                p.font.size = Pt(styling.get('title_size', 22))
                p.font.bold = True
        
        # Left column
        left_box = slide.shapes.add_textbox(Inches(0.5), Inches(2), Inches(4.5), Inches(4.5))
        left_frame = left_box.text_frame
        left_frame.word_wrap = True
        
        # Left heading
        if 'heading' in col_left:
            p = left_frame.paragraphs[0]
            p.text = col_left['heading']
            p.font.size = Pt(styling.get('heading_size', 18))
            p.font.bold = True
        
        # Left items (simplified)
        items_left = col_left.get('items', [])
        for item in items_left[:3]:  # Limit to 3 items
            p = left_frame.add_paragraph()
            term = item.get('term', '')
            desc = item.get('description', '')
            p.text = f"• {term}: {desc}"
            p.font.size = Pt(14)
            p.level = 1
        
        # Right column
        right_box = slide.shapes.add_textbox(Inches(5.5), Inches(2), Inches(4.5), Inches(4.5))
        right_frame = right_box.text_frame
        right_frame.word_wrap = True
        
        # Right heading
        if 'heading' in col_right:
            p = right_frame.paragraphs[0]
            p.text = col_right['heading']
            p.font.size = Pt(styling.get('heading_size', 18))
            p.font.bold = True
        
        # Right items (simplified)
        items_right = col_right.get('items', [])
        for item in items_right[:3]:  # Limit to 3 items
            p = right_frame.add_paragraph()
            term = item.get('term', '')
            desc = item.get('description', '')
            p.text = f"• {term}: {desc}"
            p.font.size = Pt(14)
            p.level = 1
    
    def _add_function_list(self, slide, content, styling, layout):
        """Add function list (e.g., 6 Kernfunktionen)"""
        title = content.get('title', '')
        functions = content.get('functions', [])
        
        # Title
        if title:
            title_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(0.5))
            title_box.text_frame.text = title
            if title_box.text_frame.paragraphs:
                p = title_box.text_frame.paragraphs[0]
                p.font.size = Pt(styling.get('title_size', 22))
                p.font.bold = True
        
        # Functions in 2 columns
        col_width = Inches(4.5)
        row_height = 1.2
        items_per_col = 3
        
        for idx, func in enumerate(functions[:6]):  # Max 6 items
            col = idx // items_per_col
            row = idx % items_per_col
            
            left = Inches(0.5 + col * 5)
            top = Inches(2.5 + row * row_height)
            
            box = slide.shapes.add_textbox(left, top, col_width, Inches(row_height))
            frame = box.text_frame
            frame.word_wrap = True
            
            icon = func.get('icon', '')
            number = func.get('number', idx + 1)
            name = func.get('name', '')
            desc = func.get('description', '')
            
            text = f"{icon} {number}. {name}: {desc}"
            frame.text = text
            
            if frame.paragraphs:
                p = frame.paragraphs[0]
                p.font.size = Pt(14)
    
    def _add_text_fallback(self, slide, block_type, content, styling, layout):
        """
        Fallback: Extract all text from complex block types
        """
        left = Inches(0.5)
        top = Inches(3)
        width = Inches(9)
        height = Inches(3.5)
        
        box = slide.shapes.add_textbox(left, top, width, height)
        frame = box.text_frame
        frame.word_wrap = True
        
        # Add block type indicator
        p = frame.paragraphs[0]
        p.text = f"[{block_type.upper().replace('_', ' ')}]"
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.italic = True
        
        # Extract all text from content recursively
        texts = self._extract_all_text(content)
        
        for text in texts[:20]:
            p = frame.add_paragraph()
            p.text = f"• {text}"
            p.font.size = Pt(12)
            p.level = 1
        
        if len(texts) > 20:
            p = frame.add_paragraph()
            p.text = f"... (+{len(texts) - 20} more items)"
            p.font.size = Pt(10)
            p.font.italic = True
    
    def _extract_all_text(self, obj, texts=None):
        """Recursively extract all text strings from nested dict/list"""
        if texts is None:
            texts = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Skip certain keys
                if key in ['styling', 'layout', 'animation', 'position', 'color', 'size']:
                    continue
                self._extract_all_text(value, texts)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_all_text(item, texts)
        elif isinstance(obj, str) and obj.strip() and len(obj) > 2:
            # Only add meaningful strings
            if not obj.startswith('#') and not obj.startswith('http'):
                texts.append(obj.strip())
        
        return texts
