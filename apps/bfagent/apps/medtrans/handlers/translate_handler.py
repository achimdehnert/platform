"""
Translate Texts Handler
Translates texts using DeepL API
"""

import logging
from typing import Dict, Any, List
from apps.genagent.handlers import BaseHandler
from . import register_medtrans_handler

logger = logging.getLogger(__name__)


@register_medtrans_handler
class TranslateTextsHandler(BaseHandler):
    """
    Translate texts using DeepL API
    
    Input Context:
        - presentation_id: Database presentation ID
        - source_lang: Source language code (de, en, fr, es, it)
        - target_lang: Target language code
        - deepl_api_key: DeepL API key (optional, uses settings)
        
    Output:
        - success: bool
        - output: Translation results
        - texts_translated: Number of texts translated
    """
    
    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """Execute text translation"""
        
        try:
            # Validate required context
            required = ['presentation_id', 'source_lang', 'target_lang']
            missing = [f for f in required if f not in context]
            if missing:
                return {
                    'success': False,
                    'error': f"Missing required fields: {', '.join(missing)}"
                }
            
            presentation_id = context['presentation_id']
            source_lang = context['source_lang']
            target_lang = context['target_lang']
            
            logger.info(f"Translating texts for presentation {presentation_id}: {source_lang} → {target_lang}")
            
            if test_mode:
                # Test mode: Return mock data
                return {
                    'success': True,
                    'output': {'translations': []},
                    'texts_translated': 0,
                    'test_mode': True
                }
            
            # Get pending translations from database
            texts_to_translate = self._get_pending_translations(presentation_id)
            
            if not texts_to_translate:
                logger.info("No pending translations found")
                return {
                    'success': True,
                    'output': {'message': 'No texts to translate'},
                    'texts_translated': 0
                }
            
            # Import DeepL provider
            from apps.medtrans.services.translation_providers import DeepLProvider
            
            deepl_api_key = context.get('deepl_api_key')
            translator = DeepLProvider(source_lang, target_lang, deepl_api_key=deepl_api_key)
            
            # Translate texts
            translations = []
            for text_data in texts_to_translate:
                try:
                    original = text_data['original_text']
                    result = translator.translate(original)
                    
                    translations.append({
                        'text_id': text_data['text_id'],
                        'original': original,
                        'translated': result.translated_text,
                        'slide_number': text_data['slide_number']
                    })
                    
                except Exception as e:
                    logger.error(f"Translation failed for text_id {text_data['text_id']}: {e}")
                    translations.append({
                        'text_id': text_data['text_id'],
                        'original': text_data['original_text'],
                        'translated': text_data['original_text'],  # Fallback
                        'error': str(e)
                    })
            
            # Store translations in database
            self._store_translations(translations, presentation_id)
            
            logger.info(f"Translated {len(translations)} texts")
            
            return {
                'success': True,
                'output': {'translations': translations},
                'texts_translated': len(translations)
            }
            
        except Exception as e:
            logger.error(f"Translate texts handler failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_pending_translations(self, presentation_id: int) -> List[Dict[str, Any]]:
        """Get texts that need translation"""
        
        from apps.medtrans.models import PresentationText
        
        texts = PresentationText.objects.filter(
            presentation_id=presentation_id,
            translation_method='pending'
        ).values('id', 'text_id', 'slide_number', 'original_text')
        
        return list(texts)
    
    def _store_translations(self, translations: List[Dict[str, Any]], presentation_id: int):
        """Store translated texts in database"""
        
        from apps.medtrans.models import PresentationText, Presentation
        
        try:
            for trans in translations:
                PresentationText.objects.filter(
                    presentation_id=presentation_id,
                    text_id=trans['text_id']
                ).update(
                    translated_text=trans['translated'],
                    translation_method='deepl' if 'error' not in trans else 'error'
                )
            
            # Update presentation stats
            presentation = Presentation.objects.get(id=presentation_id)
            presentation.translated_texts = PresentationText.objects.filter(
                presentation=presentation,
                translation_method='deepl'
            ).count()
            presentation.save()
            
            logger.info(f"Stored {len(translations)} translations")
            
        except Exception as e:
            logger.error(f"Failed to store translations: {e}")
            raise
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema"""
        return {
            "type": "object",
            "properties": {
                "batch_size": {
                    "type": "integer",
                    "default": 50,
                    "description": "Number of texts to translate in one batch"
                },
                "preserve_formatting": {
                    "type": "boolean",
                    "default": True,
                    "description": "Preserve text formatting (spacing, line breaks)"
                }
            }
        }
