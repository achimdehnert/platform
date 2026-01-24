"""
Slide Editor for PPTX Studio
XML-based editing that preserves formatting and design
Based on medtrans XMLDirectTranslator approach
"""

import logging
import zipfile
import tempfile
import shutil
from typing import Dict, List, Any
from pathlib import Path
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class SlideEditor:
    """Edit slide text content while preserving all formatting"""
    
    def __init__(self):
        self.namespace_map = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }
    
    def update_slide_texts(
        self,
        pptx_path: str,
        output_path: str,
        slide_number: int,
        text_updates: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Update texts in a specific slide
        
        Args:
            pptx_path: Path to original PPTX
            output_path: Path to save updated PPTX
            slide_number: Which slide to edit
            text_updates: List of {
                'shape_id': 'shape_1',
                'paragraph_index': 0,
                'new_text': 'Updated text'
            }
        
        Returns:
            {'success': bool, 'updated_count': int, 'errors': []}
        """
        results = {
            'success': False,
            'updated_count': 0,
            'errors': []
        }
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract PPTX
                with zipfile.ZipFile(pptx_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Find the slide file
                slide_file = temp_path / "ppt" / "slides" / f"slide{slide_number}.xml"
                
                if not slide_file.exists():
                    results['errors'].append(f"Slide {slide_number} not found")
                    return results
                
                # Parse and update slide
                updated_count = self._update_slide_xml(slide_file, text_updates)
                results['updated_count'] = updated_count
                
                # Repackage PPTX
                self._repackage_pptx(temp_path, output_path)
                
                results['success'] = True
                logger.info(f"Updated {updated_count} texts in slide {slide_number}")
                
        except Exception as e:
            error_msg = f"Failed to update slide: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def _update_slide_xml(self, slide_file: Path, text_updates: List[Dict]) -> int:
        """Update texts in slide XML"""
        
        # Register namespaces
        for prefix, uri in self.namespace_map.items():
            ET.register_namespace(prefix, uri)
        
        # Parse XML
        tree = ET.parse(slide_file)
        root = tree.getroot()
        
        updated_count = 0
        
        # Find all shapes
        shapes = root.findall('.//p:sp', self.namespace_map)
        
        for update in text_updates:
            shape_idx = int(update['shape_id'].split('_')[1]) - 1
            para_idx = update['paragraph_index']
            new_text = update['new_text']
            
            if shape_idx < len(shapes):
                shape = shapes[shape_idx]
                
                # Find text frame
                txBody = shape.find('.//p:txBody', self.namespace_map)
                if txBody is not None:
                    paragraphs = txBody.findall('.//a:p', self.namespace_map)
                    
                    if para_idx < len(paragraphs):
                        paragraph = paragraphs[para_idx]
                        
                        # Update text
                        if self._update_paragraph_text(paragraph, new_text):
                            updated_count += 1
        
        # Save updated XML
        tree.write(slide_file, encoding='utf-8', xml_declaration=True)
        
        return updated_count
    
    def _update_paragraph_text(self, paragraph, new_text: str) -> bool:
        """Update text in a paragraph while preserving formatting"""
        
        try:
            # Find all text runs
            runs = paragraph.findall('.//a:r', self.namespace_map)
            
            if runs:
                # Update first run, remove others
                first_run = runs[0]
                text_elem = first_run.find('.//a:t', self.namespace_map)
                
                if text_elem is not None:
                    text_elem.text = new_text
                    
                    # Remove other runs
                    for run in runs[1:]:
                        paragraph.remove(run)
                    
                    return True
            else:
                # No runs, check for direct text elements
                text_elems = paragraph.findall('.//a:t', self.namespace_map)
                if text_elems:
                    text_elems[0].text = new_text
                    
                    # Remove other text elements
                    for elem in text_elems[1:]:
                        parent = paragraph.find(f'.//*[a:t="{elem.text}"]/..',
                                               self.namespace_map)
                        if parent is not None:
                            paragraph.remove(parent)
                    
                    return True
        
        except Exception as e:
            logger.error(f"Error updating paragraph text: {str(e)}")
        
        return False
    
    def _repackage_pptx(self, temp_path: Path, output_path: str):
        """Repackage modified files into PPTX"""
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_path)
                    zipf.write(file_path, arcname)
