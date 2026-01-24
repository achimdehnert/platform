"""
Markdown Slide Parser for PPTX Studio
Parses structured Markdown files with slide definitions
"""

import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SlideContent:
    """Represents a single slide's content"""
    slide_number: int
    title: str
    navigation: Optional[str] = None
    headline: Optional[str] = None
    quote: Optional[str] = None
    quote_author: Optional[str] = None
    content_blocks: List[Dict[str, any]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    visual_notes: List[str] = field(default_factory=list)
    
    def __repr__(self):
        return f"Slide {self.slide_number}: {self.title}"


class MarkdownSlideParser:
    """
    Parser for structured Markdown files containing slide definitions
    
    Expected structure:
    ## SLIDE X: Title
    ### Navigation: ...
    ### Headline: ...
    ### Quote/Einstieg: ...
    ### Content: ...
    ### Quellen: ...
    """
    
    def __init__(self, markdown_content: str):
        self.content = markdown_content
        self.slides: List[SlideContent] = []
        
    def parse(self) -> List[SlideContent]:
        """Parse the markdown content and extract all slides"""
        # Split by slide markers
        slide_sections = self._split_into_slides()
        
        for section in slide_sections:
            slide = self._parse_slide_section(section)
            if slide:
                self.slides.append(slide)
        
        logger.info(f"Parsed {len(self.slides)} slides from markdown")
        return self.slides
    
    def _split_into_slides(self) -> List[str]:
        """Split markdown into individual slide sections"""
        # Split on "## SLIDE X:" pattern
        pattern = r'(?=^## SLIDE \d+:)'
        sections = re.split(pattern, self.content, flags=re.MULTILINE)
        # Remove empty sections and chapter title
        return [s.strip() for s in sections if s.strip() and 'SLIDE' in s]
    
    def _parse_slide_section(self, section: str) -> Optional[SlideContent]:
        """Parse a single slide section"""
        lines = section.split('\n')
        
        # Extract slide number and title from first line
        first_line = lines[0]
        slide_match = re.match(r'## SLIDE (\d+): (.+)', first_line)
        if not slide_match:
            logger.warning(f"Could not parse slide header: {first_line}")
            return None
        
        slide_num = int(slide_match.group(1))
        title = slide_match.group(2).strip()
        
        slide = SlideContent(slide_number=slide_num, title=title)
        
        # Parse sections
        current_section = None
        current_content = []
        in_code_block = False
        code_block_content = []
        
        for line in lines[1:]:
            # Check for section headers
            if line.startswith('### Navigation:'):
                current_section = 'navigation'
                continue
            elif line.startswith('### Headline:'):
                current_section = 'headline'
                continue
            elif line.startswith('### Quote') or line.startswith('### Einstieg'):
                current_section = 'quote'
                continue
            elif line.startswith('### Content:'):
                current_section = 'content'
                continue
            elif line.startswith('### Quellen:') or line.startswith('### Quellen'):
                current_section = 'sources'
                continue
            elif line.startswith('### Visueller Ansatz:') or line.startswith('### Visueller'):
                current_section = 'visual'
                continue
            elif line.startswith('---'):
                # End of slide
                break
            
            # Handle code blocks
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_block_content = []
                else:
                    # End of code block
                    in_code_block = False
                    if current_section == 'content':
                        slide.content_blocks.append({
                            'type': 'code_block',
                            'content': '\n'.join(code_block_content)
                        })
                    code_block_content = []
                continue
            
            if in_code_block:
                code_block_content.append(line)
                continue
            
            # Process based on current section
            if current_section == 'navigation' and line.strip():
                slide.navigation = line.strip().strip('`')
            
            elif current_section == 'headline':
                if line.strip().startswith('**') and line.strip().endswith('**'):
                    slide.headline = line.strip().strip('**')
                elif line.strip():
                    slide.headline = line.strip()
            
            elif current_section == 'quote':
                if line.strip().startswith('>'):
                    # Quote text
                    quote_text = line.strip().lstrip('> ').strip()
                    if quote_text.startswith('**') and quote_text.endswith('**'):
                        # Author
                        slide.quote_author = quote_text.strip('**')
                    else:
                        # Quote content
                        if slide.quote:
                            slide.quote += ' ' + quote_text
                        else:
                            slide.quote = quote_text
            
            elif current_section == 'content':
                if line.strip():
                    # Determine content type
                    if line.startswith('####'):
                        # Subheading
                        slide.content_blocks.append({
                            'type': 'subheading',
                            'content': line.strip('#').strip()
                        })
                    elif line.strip().startswith('**') and ':' in line:
                        # Bold label (like "Definition:")
                        slide.content_blocks.append({
                            'type': 'label',
                            'content': line.strip()
                        })
                    elif line.strip().startswith(('- ', '* ', '+ ')):
                        # Bullet point
                        slide.content_blocks.append({
                            'type': 'bullet',
                            'content': line.strip()[2:].strip()
                        })
                    elif line.strip().startswith(('✓', '□', '❌', '✅', '→')):
                        # Special list item
                        slide.content_blocks.append({
                            'type': 'bullet',
                            'content': line.strip()
                        })
                    elif line.strip().startswith('>'):
                        # Quote in content
                        slide.content_blocks.append({
                            'type': 'quote',
                            'content': line.strip().lstrip('> ')
                        })
                    else:
                        # Regular paragraph
                        slide.content_blocks.append({
                            'type': 'paragraph',
                            'content': line.strip()
                        })
            
            elif current_section == 'sources':
                if line.strip().startswith('-'):
                    slide.sources.append(line.strip()[1:].strip())
            
            elif current_section == 'visual':
                if line.strip().startswith('-'):
                    slide.visual_notes.append(line.strip()[1:].strip())
        
        return slide
    
    def get_slide(self, slide_number: int) -> Optional[SlideContent]:
        """Get a specific slide by number"""
        for slide in self.slides:
            if slide.slide_number == slide_number:
                return slide
        return None
    
    def get_slide_count(self) -> int:
        """Get total number of slides"""
        return len(self.slides)
    
    def export_summary(self) -> str:
        """Export a summary of all slides"""
        summary = []
        summary.append(f"Total Slides: {len(self.slides)}\n")
        summary.append("=" * 60)
        
        for slide in self.slides:
            summary.append(f"\nSlide {slide.slide_number}: {slide.title}")
            if slide.headline:
                summary.append(f"  Headline: {slide.headline}")
            summary.append(f"  Content Blocks: {len(slide.content_blocks)}")
            if slide.sources:
                summary.append(f"  Sources: {len(slide.sources)}")
        
        return '\n'.join(summary)


def parse_markdown_file(file_path: str) -> MarkdownSlideParser:
    """
    Parse a markdown file and return parser with slides
    
    Args:
        file_path: Path to markdown file
        
    Returns:
        MarkdownSlideParser with parsed slides
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parser = MarkdownSlideParser(content)
        parser.parse()
        return parser
    
    except FileNotFoundError:
        logger.error(f"Markdown file not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error parsing markdown file: {e}")
        raise
