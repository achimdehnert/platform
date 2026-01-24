#!/usr/bin/env python3
"""
XML Direct Translator
Direct XML-based PowerPoint translation by manipulating slide XML files
Much more efficient and preserves formatting perfectly
"""

import logging
import zipfile
import tempfile
import shutil
from typing import Dict, List, Any, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
import re
from datetime import datetime


class XMLDirectTranslator:
    """Direct XML-based PowerPoint translator - preserves all formatting"""
    
    def __init__(self, translator_provider):
        self.logger = logging.getLogger(__name__)
        self.translator = translator_provider
        self.namespace_map = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }
        
    def translate_presentation_xml_from_db(self, pptx_path: str, output_path: str, presentation_id: Optional[int] = None) -> Dict[str, Any]:
        """Translate PowerPoint using existing translations from database"""
        
        results = {
            'success': False,
            'slides_processed': 0,
            'texts_translated': 0,
            'errors': [],
            'translated_texts': {},
            'method': 'xml_direct_translation_from_db'
        }
        
        if not presentation_id:
            self.logger.warning("No presentation_id provided - falling back to regular translation")
            return self.translate_presentation_xml(pptx_path, output_path)
        
        try:
            # Get existing translations from database using Django ORM
            from apps.medtrans.models import PresentationText
            
            translations = PresentationText.objects.filter(
                presentation_id=presentation_id
            ).values('slide_number', 'text_id', 'translated_text', 'original_text', 'translation_method')
            
            if not translations:
                self.logger.warning(f"No translations found for presentation {presentation_id} - falling back to regular translation")
                return self.translate_presentation_xml(pptx_path, output_path)
            
            # Create translation lookup by slide and text_id
            # Also track pending translations that need to be translated
            translation_lookup = {}
            pending_translations = {}
            
            for trans in translations:
                slide_key = f"slide_{trans['slide_number']}"
                if slide_key not in translation_lookup:
                    translation_lookup[slide_key] = {}
                    pending_translations[slide_key] = {}
                
                # Store existing translations
                translation_lookup[slide_key][trans['text_id']] = trans['translated_text']
                
                # Track pending translations that need to be translated
                if trans['translated_text'] is None or trans['translation_method'] == 'pending':
                    pending_translations[slide_key][trans['text_id']] = {
                        'original_text': trans['original_text'],
                        'presentation_id': presentation_id,
                        'slide_number': trans['slide_number'],
                        'customer_id': trans['customer_id']
                    }
            
            # Count pending translations
            total_pending = sum(len(pending_translations[slide_key]) for slide_key in pending_translations)
            self.logger.info(f"Using {len(translations)} existing translations from database")
            self.logger.info(f"Found {total_pending} pending translations that need to be translated")
            
            # Step 1: Extract PPTX as ZIP to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract PPTX
                with zipfile.ZipFile(pptx_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Step 2: Process slide XML files
                slides_dir = temp_path / "ppt" / "slides"
                if not slides_dir.exists():
                    results['errors'].append("No slides directory found in PPTX")
                    return results
                
                slide_files = sorted(slides_dir.glob("slide*.xml"))
                self.logger.info(f"Found {len(slide_files)} slide files to process")
                
                for slide_file in slide_files:
                    try:
                        slide_number = int(re.search(r'slide(\d+)', slide_file.name).group(1))
                        slide_key = f"slide_{slide_number}"
                        
                        if slide_key in translation_lookup:
                            slide_translations = translation_lookup[slide_key]
                            slide_pending = pending_translations.get(slide_key, {})
                            
                            # Translate pending texts first and update database
                            if slide_pending:
                                self.logger.info(f"Translating {len(slide_pending)} pending texts for slide {slide_number}")
                                for text_id, pending_info in slide_pending.items():
                                    try:
                                        original_text = pending_info['original_text']
                                        translated_text = self.translator.translate(original_text.strip()).translated_text
                                        
                                        if translated_text:
                                            # Update translation lookup
                                            slide_translations[text_id] = translated_text
                                            
                                            # Update database using Django ORM
                                            PresentationText.objects.filter(
                                                presentation_id=pending_info['presentation_id'],
                                                text_id=text_id
                                            ).update(
                                                translated_text=translated_text,
                                                translation_method='deepl'
                                            )
                                            
                                            self.logger.debug(f"Translated pending text {text_id}: '{original_text}' → '{translated_text}'")
                                        
                                    except Exception as e:
                                        self.logger.error(f"Failed to translate pending text {text_id}: {e}")
                            
                            # Apply all translations (existing + newly translated)
                            texts_translated = self._translate_slide_xml_from_lookup(
                                slide_file, slide_translations
                            )
                            results['texts_translated'] += texts_translated
                            self.logger.info(f"Applied {texts_translated} translations to slide {slide_number}")
                        else:
                            self.logger.info(f"No translations found for slide {slide_number}")
                        
                        results['slides_processed'] += 1
                        
                    except Exception as e:
                        error_msg = f"Error processing slide {slide_file.name}: {str(e)}"
                        results['errors'].append(error_msg)
                        self.logger.error(error_msg)
                
                # Step 3: Repackage as PPTX
                self._repackage_pptx(temp_path, output_path)
                results['success'] = True
                
                self.logger.info(f"Translation completed: {results['slides_processed']} slides, {results['texts_translated']} texts")
                
        except Exception as e:
            error_msg = f"XML Direct Translation failed: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def translate_presentation_xml(self, pptx_path: str, output_path: str) -> Dict[str, Any]:
        """Translate PowerPoint presentation by directly modifying XML files"""
        
        results = {
            'success': False,
            'slides_processed': 0,
            'texts_translated': 0,
            'errors': [],
            'translated_texts': {},  # Store actual translated texts by ID
            'method': 'xml_direct_translation'
        }
        
        try:
            # Step 1: Extract PPTX as ZIP to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract PPTX
                with zipfile.ZipFile(pptx_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                self.logger.info(f"Extracted PPTX to: {temp_path}")
                
                # Step 2: Find all slide XML files
                slides_dir = temp_path / "ppt" / "slides"
                slide_files = list(slides_dir.glob("slide*.xml"))
                
                self.logger.info(f"Found {len(slide_files)} slide XML files")
                
                # Step 3: Process each slide XML file
                for slide_file in sorted(slide_files):
                    try:
                        slide_result = self._translate_slide_xml(slide_file, results['translated_texts'])
                        results['slides_processed'] += 1
                        results['texts_translated'] += slide_result['texts_translated']
                        
                        self.logger.info(f"Processed {slide_file.name}: {slide_result['texts_translated']} texts translated")
                        
                    except Exception as e:
                        error_msg = f"Failed to process {slide_file.name}: {e}"
                        results['errors'].append(error_msg)
                        self.logger.error(f"ERROR: {error_msg}")
                
                # Step 4: Repackage as PPTX
                self._repackage_pptx(temp_path, output_path)
                
                results['success'] = results['slides_processed'] > 0
                self.logger.info(f"XML Direct Translation completed: {results['texts_translated']} texts translated")
                
        except Exception as e:
            results['errors'].append(f"XML Direct Translation failed: {e}")
            self.logger.error(f"XML Direct Translation failed: {e}")
            
        return results
    
    def _translate_slide_xml(self, slide_file: Path, translated_texts_dict: Dict[str, str]) -> Dict[str, Any]:
        """Translate all <a:t> tags in a single slide XML file"""
        
        result = {'texts_translated': 0, 'errors': []}
        
        try:
            # Register namespaces
            for prefix, uri in self.namespace_map.items():
                ET.register_namespace(prefix, uri)
            
            # Parse XML
            tree = ET.parse(slide_file)
            root = tree.getroot()
            
            # Find all <a:t> elements (text content)
            text_elements = root.findall('.//a:t', self.namespace_map)
            
            self.logger.debug(f"Found {len(text_elements)} <a:t> elements in {slide_file.name}")
            
            # Translate each text element
            for idx, text_elem in enumerate(text_elements):
                if text_elem.text:
                    original_text = text_elem.text
                    
                    # Skip if text is too short or contains only special characters (check stripped version)
                    if len(original_text.strip()) < 2 or not re.search(r'[a-zA-ZäöüÄÖÜß]', original_text.strip()):
                        continue
                    
                    try:
                        # Translate only the stripped text content
                        stripped_text = original_text.strip()
                        translated_text = self.translator.translate(stripped_text).translated_text
                        
                        if translated_text and translated_text != stripped_text:
                            # Preserve original spacing: extract leading/trailing spaces
                            leading_spaces = original_text[:len(original_text) - len(original_text.lstrip())]
                            trailing_spaces = original_text[len(original_text.rstrip()):]
                            
                            # Reconstruct with preserved spacing
                            final_translated_text = f"{leading_spaces}{translated_text}{trailing_spaces}"
                            text_elem.text = final_translated_text
                            result['texts_translated'] += 1
                            
                            # Store translated text with unique ID matching extractor format
                            slide_number = int(slide_file.stem.replace('slide', ''))
                            slide_key = f"slide_{slide_number}"
                            text_id = f"text_{idx + 1}"
                            
                            # Create nested structure for database storage
                            if slide_key not in translated_texts_dict:
                                translated_texts_dict[slide_key] = {}
                            
                            translated_texts_dict[slide_key][text_id] = {
                                'original': original_text.strip(),
                                'translated': translated_text
                            }
                            
                            self.logger.debug(f"Translated: '{original_text}' → '{final_translated_text}'")
                        
                    except Exception as e:
                        error_msg = f"Translation failed for '{original_text}': {e}"
                        result['errors'].append(error_msg)
                        self.logger.warning(f"WARNING: {error_msg}")
            
            # Save modified XML
            tree.write(slide_file, encoding='utf-8', xml_declaration=True)
            
        except Exception as e:
            error_msg = f"Failed to process slide XML {slide_file}: {e}"
            result['errors'].append(error_msg)
            self.logger.error(f"❌ {error_msg}")
        
        return result
    
    def _translate_slide_xml_from_lookup(self, slide_file: Path, translation_lookup: Dict[str, str]) -> int:
        """Apply translations from lookup dictionary to slide XML"""
        
        texts_translated = 0
        
        try:
            # Parse XML
            tree = ET.parse(slide_file)
            root = tree.getroot()
            
            # Register namespaces
            for prefix, uri in self.namespace_map.items():
                ET.register_namespace(prefix, uri)
            
            # Find all text elements
            text_elements = root.findall('.//a:t', self.namespace_map)
            
            for idx, text_elem in enumerate(text_elements):
                if text_elem.text:
                    original_text = text_elem.text
                    
                    # Skip empty or whitespace-only text
                    if not original_text.strip():
                        continue
                    
                    # Generate text_id matching the format used in database
                    slide_number = int(slide_file.stem.replace('slide', ''))
                    text_id = f"slide_{slide_number}_text_{idx + 1}"
                    
                    # Look up translation in the dictionary
                    if text_id in translation_lookup:
                        translated_text = translation_lookup[text_id]
                        
                        if translated_text and translated_text.strip():
                            # Preserve original spacing
                            leading_spaces = original_text[:len(original_text) - len(original_text.lstrip())]
                            trailing_spaces = original_text[len(original_text.rstrip()):]
                            
                            # Apply translation with preserved spacing
                            final_translated_text = f"{leading_spaces}{translated_text.strip()}{trailing_spaces}"
                            text_elem.text = final_translated_text
                            texts_translated += 1
                            
                            self.logger.debug(f"Applied translation for {text_id}: '{original_text}' → '{final_translated_text}'")
                        else:
                            self.logger.debug(f"Empty translation found for {text_id}, keeping original")
                    else:
                        self.logger.debug(f"No translation found for {text_id}: '{original_text}'")
            
            # Save modified XML
            tree.write(slide_file, encoding='utf-8', xml_declaration=True)
            
        except Exception as e:
            self.logger.error(f"Failed to apply translations to slide {slide_file}: {e}")
        
        return texts_translated
    
    def _repackage_pptx(self, temp_dir: Path, output_path: str):
        """Repackage the modified XML files back into PPTX"""
        
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                # Add all files from temp directory back to ZIP
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        # Calculate relative path within ZIP
                        arcname = file_path.relative_to(temp_dir)
                        zip_out.write(file_path, arcname)
            
            self.logger.info(f"Repackaged PPTX: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to repackage PPTX: {e}")
            raise
    
    def analyze_xml_structure(self, pptx_path: str) -> Dict[str, Any]:
        """Analyze PowerPoint XML structure for debugging"""
        
        analysis = {
            'slides_found': 0,
            'text_elements_per_slide': {},
            'sample_texts': [],
            'xml_structure': {}
        }
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract PPTX
                with zipfile.ZipFile(pptx_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Analyze slides
                slides_dir = temp_path / "ppt" / "slides"
                slide_files = list(slides_dir.glob("slide*.xml"))
                analysis['slides_found'] = len(slide_files)
                
                for slide_file in sorted(slide_files):
                    slide_name = slide_file.name
                    
                    # Parse XML
                    tree = ET.parse(slide_file)
                    root = tree.getroot()
                    
                    # Find text elements
                    text_elements = root.findall('.//a:t', self.namespace_map)
                    analysis['text_elements_per_slide'][slide_name] = len(text_elements)
                    
                    # Collect sample texts
                    for text_elem in text_elements[:3]:  # First 3 texts per slide
                        if text_elem.text and text_elem.text.strip():
                            analysis['sample_texts'].append({
                                'slide': slide_name,
                                'text': text_elem.text.strip()[:100]  # First 100 chars
                            })
                
                self.logger.info(f"XML Analysis completed: {analysis['slides_found']} slides analyzed")
                
        except Exception as e:
            self.logger.error(f"XML Analysis failed: {e}")
            analysis['error'] = str(e)
        
        return analysis


class XMLDirectTranslationPipeline:
    """Complete pipeline using XML Direct Translation approach"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def run_xml_direct_pipeline(self, pptx_file: str, source_lang: str, target_lang: str, output_dir: str = "output") -> Dict[str, Any]:
        """Run complete XML-based translation pipeline"""
        
        try:
            # Initialize translator
            from core.translation_providers import MultiProviderTranslationEngine
            translator = MultiProviderTranslationEngine(source_lang, target_lang)
            
            # Initialize XML translator
            xml_translator = XMLDirectTranslator(translator)
            
            # Create output path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path(output_dir) / f"{Path(pptx_file).stem}_translated_{timestamp}.pptx"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Starting XML Direct Translation Pipeline")
            self.logger.info(f"Input: {pptx_file}")
            self.logger.info(f"Output: {output_path}")
            self.logger.info(f"Translation: {source_lang} -> {target_lang}")
            
            # Run XML analysis first
            self.logger.info(f"Analyzing PowerPoint XML structure...")
            analysis = xml_translator.analyze_xml_structure(pptx_file)
            
            self.logger.info(f"Analysis results:")
            self.logger.info(f"   - Slides found: {analysis['slides_found']}")
            self.logger.info(f"   - Total text elements: {sum(analysis['text_elements_per_slide'].values())}")
            self.logger.info(f"   - Sample texts: {len(analysis['sample_texts'])}")
            
            # Run XML direct translation
            self.logger.info(f"Running XML Direct Translation...")
            translation_result = xml_translator.translate_presentation_xml(pptx_file, str(output_path))
            
            if translation_result['success']:
                self.logger.info("XML Direct Translation SUCCESSFUL!")
                self.logger.info(f"   - Slides processed: {translation_result['slides_processed']}")
                self.logger.info(f"   - Texts translated: {translation_result['texts_translated']}")
                self.logger.info(f"   - Output file: {output_path}")
                
                return {
                    'success': True,
                    'method': 'xml_direct_translation',
                    'output_file': str(output_path),
                    'analysis': analysis,
                    'translation_result': translation_result,
                    'slides_processed': translation_result['slides_processed'],
                    'texts_translated': translation_result['texts_translated'],
                    'translated_texts': translation_result.get('translated_texts', {})
                }
            else:
                self.logger.error("XML Direct Translation failed")
                return {
                    'success': False,
                    'method': 'xml_direct_translation',
                    'errors': translation_result['errors']
                }
                
        except Exception as e:
            self.logger.error(f"XML Direct Translation Pipeline failed: {e}")
            return {
                'success': False,
                'method': 'xml_direct_translation',
                'error': str(e)
            }


if __name__ == '__main__':
    # Test the XML Direct Translation approach
    logging.basicConfig(level=logging.INFO)
    
    pipeline = XMLDirectTranslationPipeline()
    result = pipeline.run_xml_direct_pipeline(
        pptx_file="uploads/medAIfuson_T0.pptx",
        source_lang="de",
        target_lang="en"
    )
    
    print(f"Result: {result}")
