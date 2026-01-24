"""
Repackage PPTX Handler
Creates translated PowerPoint file from database translations
"""

import logging
from typing import Dict, Any
from pathlib import Path
from apps.genagent.handlers import BaseHandler
from . import register_medtrans_handler

logger = logging.getLogger(__name__)


@register_medtrans_handler
class RepackagePPTXHandler(BaseHandler):
    """
    Create translated PowerPoint file using XML Direct Translation
    
    Input Context:
        - pptx_file: Path to original PowerPoint file
        - output_file: Path for translated PowerPoint file
        - presentation_id: Database presentation ID
        
    Output:
        - success: bool
        - output: Path to translated file
        - slides_processed: Number of slides processed
        - texts_applied: Number of translations applied
    """
    
    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """Execute PPTX repackaging with translations"""
        
        try:
            # Validate required context
            required = ['pptx_file', 'output_file', 'presentation_id']
            missing = [f for f in required if f not in context]
            if missing:
                return {
                    'success': False,
                    'error': f"Missing required fields: {', '.join(missing)}"
                }
            
            pptx_file = context['pptx_file']
            output_file = context['output_file']
            presentation_id = context['presentation_id']
            
            logger.info(f"Repackaging {pptx_file} with translations")
            
            if test_mode:
                # Test mode: Return mock data
                return {
                    'success': True,
                    'output': output_file,
                    'slides_processed': 1,
                    'texts_applied': 1,
                    'test_mode': True
                }
            
            # Check if translations exist
            from apps.medtrans.models import PresentationText
            
            translations_count = PresentationText.objects.filter(
                presentation_id=presentation_id,
                translation_method='deepl'
            ).count()
            
            if translations_count == 0:
                return {
                    'success': False,
                    'error': 'No translations found. Please translate texts first.'
                }
            
            # Import XML Direct Translator
            from apps.medtrans.services.xml_direct_translator import XMLDirectTranslator
            from apps.medtrans.services.translation_providers import DeepLProvider
            
            # Get source/target languages from presentation
            from apps.medtrans.models import Presentation
            presentation = Presentation.objects.get(id=presentation_id)
            
            # Initialize translator (needed for XML processing)
            deepl_api_key = context.get('deepl_api_key')
            translator_provider = DeepLProvider(
                presentation.source_language,
                presentation.target_language,
                deepl_api_key=deepl_api_key
            )
            
            xml_translator = XMLDirectTranslator(translator_provider)
            
            # Translate using database translations
            result = xml_translator.translate_presentation_xml_from_db(
                str(pptx_file),
                str(output_file),
                presentation_id
            )
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': 'XML translation failed',
                    'details': result.get('errors', [])
                }
            
            # Update presentation status
            presentation.status = 'completed'
            presentation.save()
            
            logger.info(f"Created translated PPTX: {output_file}")
            
            return {
                'success': True,
                'output': str(output_file),
                'slides_processed': result.get('slides_processed', 0),
                'texts_applied': result.get('texts_translated', 0)
            }
            
        except Exception as e:
            logger.error(f"Repackage PPTX handler failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema"""
        return {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["pptx", "pdf"],
                    "default": "pptx",
                    "description": "Output file format"
                },
                "preserve_original": {
                    "type": "boolean",
                    "default": False,
                    "description": "Keep original text alongside translation"
                }
            }
        }
