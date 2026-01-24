"""
Translation Provider Abstraction Layer
Unterstützt DeepL und Google Translate mit einheitlicher API
"""

import os
import logging
import time
from typing import Optional, Dict, Any, List, Tuple, Union
from abc import ABC, abstractmethod
import deepl
from .translation_cache import get_translation_cache
from enum import Enum
from dataclasses import dataclass

# DeepL Import
try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False

# Google Translate removed - using DeepL only
GOOGLE_TRANSLATE_AVAILABLE = False


class TranslationProvider(Enum):
    """Verfügbare Übersetzungsanbieter"""
    DEEPL = "deepl"
    GOOGLE = "google"


@dataclass
class TranslationResult:
    """Ergebnis einer Übersetzung"""
    translated_text: str
    source_language: str
    target_language: str
    provider: TranslationProvider
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None


class BaseTranslationProvider(ABC):
    """Abstrakte Basisklasse für Übersetzungsanbieter"""
    
    def __init__(self, source_language: str, target_language: str):
        self.source_language = source_language
        self.target_language = target_language
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def is_available(self) -> bool:
        """Prüft ob der Provider verfügbar ist"""
        pass
    
    @abstractmethod
    def translate(self, text: str) -> TranslationResult:
        """Übersetzt den gegebenen Text"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Gibt unterstützte Sprachen zurück"""
        pass


class DeepLProvider(BaseTranslationProvider):
    """DeepL Übersetzungsanbieter mit Translation Cache"""
    
    def __init__(self, source_language: str, target_language: str, 
                 deepl_api_key: Optional[str] = None, deepl_server_url: Optional[str] = None,
                 use_cache: bool = True):
        super().__init__(source_language, target_language)
        
        # CRITICAL FIX: Ensure source_language is never None
        if source_language is None:
            self.source_language = 'auto'
            self.logger.warning("⚠️ DEEPL FIX: source_language was None, setting to 'auto'")
        elif not source_language.strip():
            self.source_language = 'auto'
            self.logger.warning("⚠️ DEEPL FIX: source_language was empty, setting to 'auto'")
        
        # API-Key aus Environment oder Parameter
        # Django loads .env via decouple, so we just use the parameter or fallback to os.getenv
        self.api_key = deepl_api_key or os.getenv('DEEPL_API_KEY')
        self.server_url = deepl_server_url or os.getenv('DEEPL_SERVER_URL')
        
        # Translation cache
        self.use_cache = use_cache
        self.cache = get_translation_cache() if use_cache else None
        
        self.translator = None
        self.setup_client()
    
    def setup_client(self):
        """Initialisiert DeepL Client"""
        print(f"🔍 DEEPL SETUP DEBUG: DEEPL_AVAILABLE={DEEPL_AVAILABLE}")
        print(f"🔍 DEEPL SETUP DEBUG: api_key present={bool(self.api_key)}")
        print(f"🔍 DEEPL SETUP DEBUG: api_key length={len(self.api_key) if self.api_key else 0}")
        
        if not DEEPL_AVAILABLE:
            self.logger.warning("DeepL library not available")
            print("❌ DEEPL SETUP: Library not available")
            return
        
        if not self.api_key:
            self.logger.warning("DeepL API key not provided")
            print("❌ DEEPL SETUP: API key not provided")
            return
        
        try:
            # Test API key format first (removed warning as it's not always required)
            
            # Server URL berücksichtigen (für Free vs Pro API)
            if self.server_url:
                self.translator = deepl.Translator(
                    auth_key=self.api_key,
                    server_url=self.server_url
                )
                print(f"✅ DEEPL SETUP: Client initialized with server_url={self.server_url}")
            else:
                self.translator = deepl.Translator(self.api_key)
                print("✅ DEEPL SETUP: Client initialized with default server")
            
            # Test the connection with a simple request
            try:
                usage = self.translator.get_usage()
                print(f"✅ DEEPL CONNECTION TEST: Usage check successful - {usage.character.count}/{usage.character.limit} characters used")
            except Exception as test_e:
                print(f"⚠️ DEEPL CONNECTION TEST FAILED: {test_e}")
                # Don't fail initialization, just warn
            
            self.logger.info("DeepL client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize DeepL client: {e}")
            print(f"❌ DEEPL SETUP ERROR: {e}")
            print(f"❌ DEEPL SETUP ERROR TYPE: {type(e)}")
            import traceback
            print(f"❌ DEEPL SETUP TRACEBACK: {traceback.format_exc()}")
            self.translator = None
    
    def is_available(self) -> bool:
        """Prüft DeepL Verfügbarkeit"""
        return DEEPL_AVAILABLE and self.translator is not None
    
    def get_supported_languages(self) -> List[str]:
        """DeepL unterstützte Sprachen"""
        return [
            'bg', 'cs', 'da', 'de', 'el', 'en', 'es', 'et', 'fi', 'fr',
            'hu', 'id', 'it', 'ja', 'ko', 'lt', 'lv', 'nb', 'nl', 'pl',
            'pt', 'ro', 'ru', 'sk', 'sl', 'sv', 'tr', 'uk', 'zh'
        ]
    
    def _map_source_language_code(self, lang_code: str) -> Optional[str]:
        """Map language code for SOURCE language (DeepL source codes)"""
        if not lang_code or lang_code.lower().strip() in ['auto', 'none', '']:
            return None  # Use auto-detection
            
        source_mappings = {
            'en': 'EN',      # English source
            'de': 'DE',      # German
            'fr': 'FR',      # French
            'es': 'ES',      # Spanish
            'it': 'IT',      # Italian
            'ja': 'JA',      # Japanese
            'ko': 'KO',      # Korean
            'nl': 'NL',      # Dutch
            'pl': 'PL',      # Polish
            'pt': 'PT',      # Portuguese
            'ru': 'RU',      # Russian
            'zh': 'ZH',      # Chinese
            'sv': 'SV',      # Swedish
            'da': 'DA',      # Danish
            'fi': 'FI',      # Finnish
            'no': 'NB',      # Norwegian
        }
        
        normalized = lang_code.lower().strip()
        mapped = source_mappings.get(normalized)
        if mapped:
            return mapped
        
        # If not in mapping, return None for auto-detection
        self.logger.warning(f"Unknown source language '{lang_code}', using auto-detection")
        return None
    
    def _map_target_language_code(self, lang_code: str) -> str:
        """Map language code for TARGET language (DeepL target codes)"""
        target_mappings = {
            'en': 'EN-US',   # English target (US variant)
            'en-us': 'EN-US', # English US
            'en-gb': 'EN-GB', # English GB
            'pt': 'PT-PT',   # Portuguese (Portugal)
            'pt-br': 'PT-BR', # Portuguese (Brazil)
            'zh': 'ZH',      # Chinese (simplified) - Fixed: was ZH-CN
            'de': 'DE',      # German
            'fr': 'FR',      # French
            'es': 'ES',      # Spanish
            'it': 'IT',      # Italian
            'ja': 'JA',      # Japanese
            'ko': 'KO',      # Korean
            'nl': 'NL',      # Dutch
            'pl': 'PL',      # Polish
            'ru': 'RU',      # Russian
            'sv': 'SV',      # Swedish
            'da': 'DA',      # Danish
            'fi': 'FI',      # Finnish
            'no': 'NB',      # Norwegian
            'nb': 'NB',      # Norwegian Bokmål
            'bg': 'BG',      # Bulgarian
            'cs': 'CS',      # Czech
            'el': 'EL',      # Greek
            'et': 'ET',      # Estonian
            'hu': 'HU',      # Hungarian
            'id': 'ID',      # Indonesian
            'lt': 'LT',      # Lithuanian
            'lv': 'LV',      # Latvian
            'ro': 'RO',      # Romanian
            'sk': 'SK',      # Slovak
            'sl': 'SL',      # Slovenian
            'tr': 'TR',      # Turkish
            'uk': 'UK',      # Ukrainian
        }
        
        normalized = lang_code.lower().strip()
        mapped = target_mappings.get(normalized)
        if mapped:
            return mapped
        
        # Fallback: handle deprecated codes and unknown languages
        fallback = lang_code.upper().strip()
        
        # Handle deprecated DeepL codes
        if fallback == 'EN':
            fallback = 'EN-US'  # Default to US English
            self.logger.info(f"Deprecated target language 'EN' mapped to 'EN-US'")
        elif fallback == 'PT':
            fallback = 'PT-PT'  # Default to Portugal Portuguese
            self.logger.info(f"Ambiguous target language 'PT' mapped to 'PT-PT'")
        
        self.logger.warning(f"Unknown target language '{lang_code}', using fallback '{fallback}'")
        return fallback
        
    def translate(self, text: str) -> TranslationResult:
        """Übersetzt mit DeepL und Translation Cache"""
        print(f"🔍 DEEPL TRANSLATE DEBUG: is_available()={self.is_available()}")
        print(f"🔍 DEEPL TRANSLATE DEBUG: translator object={self.translator}")
        print(f"🔍 DEEPL TRANSLATE DEBUG: DEEPL_AVAILABLE={DEEPL_AVAILABLE}")
        
        # Check cache first if enabled
        if self.use_cache and self.cache:
            cached_result = self.cache.get_translation(text, self.source_language, self.target_language)
            if cached_result:
                print(f"🔍 CACHE HIT: Using cached translation for '{text[:30]}...'")
                return TranslationResult(
                    translated_text=cached_result['target_text'],
                    source_language=self.source_language,
                    target_language=self.target_language,
                    provider=TranslationProvider.DEEPL,
                    confidence=cached_result.get('confidence', 1.0)
                )
        
        if not self.is_available():
            error_msg = f"DeepL not available - DEEPL_AVAILABLE={DEEPL_AVAILABLE}, translator={self.translator}"
            print(f"❌ DEEPL TRANSLATE: {error_msg}")
            return TranslationResult(
                translated_text=text,
                source_language=self.source_language,
                target_language=self.target_language,
                provider=TranslationProvider.DEEPL,
                error=error_msg
            )
        
        if not text.strip():
            return TranslationResult(
                translated_text=text,
                source_language=self.source_language,
                target_language=self.target_language,
                provider=TranslationProvider.DEEPL
            )
        
        start_time = time.time()
        
        try:
            # Sprachcodes für DeepL mapppen (separate source/target mappings)
            source_lang = self._map_source_language_code(self.source_language)
            target_lang = self._map_target_language_code(self.target_language)
                
            # CRITICAL DEBUG: Log what we're sending to DeepL
            self.logger.info(f"DEEPL DEBUG: Original languages: source='{self.source_language}', target='{self.target_language}'")
            self.logger.info(f"DEEPL DEBUG: Mapped languages: source='{source_lang}', target='{target_lang}'")
            self.logger.info(f"DEEPL DEBUG: Text length: {len(text)}, First 50 chars: '{text[:50]}'")
            
            # DeepL Übersetzung with conditional source_lang
            if source_lang is None:
                result = self.translator.translate_text(
                    text=text,
                    target_lang=target_lang
                )
            else:
                result = self.translator.translate_text(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
            
            processing_time = time.time() - start_time
            
            # CRITICAL DEBUG: Log actual DeepL response
            self.logger.error(f"DEEPL SUCCESS: Original='{text[:50]}' -> Translated='{result.text[:50]}'")
            # Safely access detected_source_language if available
            detected_lang = getattr(result, 'detected_source_language', 'unknown')
            self.logger.error(f"DEEPL SUCCESS: Source={detected_lang}, Time={processing_time:.3f}s")
            
            translation_result = TranslationResult(
                translated_text=result.text,
                source_language=self.source_language,
                target_language=self.target_language,
                provider=TranslationProvider.DEEPL,
                processing_time=processing_time
            )
            
            # Save to cache if enabled
            if self.use_cache and self.cache:
                self.cache.save_translation(
                    source_text=text,
                    target_text=result.text,
                    source_lang=self.source_language,
                    target_lang=self.target_language,
                    provider="deepl",
                    confidence=1.0,
                    manual_edit=False
                )
                print(f"🔍 CACHE SAVE: Cached translation for '{text[:30]}...'")
            
            return translation_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"DeepL translation failed: {str(e)}"
            self.logger.error(error_msg)
            
            return TranslationResult(
                translated_text=text,
                source_language=self.source_language,
                target_language=self.target_language,
                provider=TranslationProvider.DEEPL,
                processing_time=processing_time,
                error=error_msg
            )


# GoogleTranslateProvider removed - using DeepL only

class MultiProviderTranslationEngine:
    """Multi-Provider Übersetzungsengine mit Fallback"""
    
    def __init__(self, source_language: str, target_language: str,
                 preferred_provider: TranslationProvider = TranslationProvider.DEEPL,
                 deepl_api_key: Optional[str] = None, 
                 deepl_server_url: Optional[str] = None):
        
        self.source_language = source_language
        self.target_language = target_language
        self.preferred_provider = preferred_provider
        self.logger = logging.getLogger(__name__)
        
        # Provider initialisieren
        self.providers = {}
        
        # DeepL Provider
        if DEEPL_AVAILABLE:
            self.providers[TranslationProvider.DEEPL] = DeepLProvider(
                source_language, target_language, deepl_api_key, deepl_server_url
            )
        
        # Google Provider removed - using DeepL only
        
        # Statistiken
        self.stats = {
            'total_translations': 0,
            'successful_translations': 0,
            'failed_translations': 0,
            'provider_usage': {provider: 0 for provider in TranslationProvider},
            'fallback_usage': 0
        }
    
    def get_available_providers(self) -> List[TranslationProvider]:
        """Gibt verfügbare Provider zurück"""
        return [provider for provider, engine in self.providers.items() if engine.is_available()]
    
    def translate(self, text: str, use_fallback: bool = True) -> TranslationResult:
        """Übersetzt mit bevorzugtem Provider und Fallback"""
        if not text.strip():
            return TranslationResult(
                translated_text=text,
                source_language=self.source_language,
                target_language=self.target_language,
                provider=self.preferred_provider
            )
        
        self.stats['total_translations'] += 1
        
        # Zuerst bevorzugten Provider versuchen
        if self.preferred_provider in self.providers:
            provider = self.providers[self.preferred_provider]
            result = provider.translate(text)
            
            if result.error is None:
                self.stats['successful_translations'] += 1
                self.stats['provider_usage'][self.preferred_provider] += 1
                return result
        
        # Fallback zu anderen verfügbaren Providern
        if use_fallback:
            for provider_type, provider in self.providers.items():
                if provider_type != self.preferred_provider and provider.is_available():
                    result = provider.translate(text)
                    
                    if result.error is None:
                        self.stats['successful_translations'] += 1
                        self.stats['provider_usage'][provider_type] += 1
                        self.stats['fallback_usage'] += 1
                        return result
        
        # Alle Provider fehlgeschlagen
        self.stats['failed_translations'] += 1
        return TranslationResult(
            translated_text=text,
            source_language=self.source_language,
            target_language=self.target_language,
            provider=self.preferred_provider,
            error="Alle Übersetzungsanbieter fehlgeschlagen"
        )
    
    def translate_text(self, text: str) -> str:
        """Convenience method for simple text translation"""
        result = self.translate(text)
        return result.translated_text
    
    def get_stats(self) -> Dict:
        """Gibt Übersetzungsstatistiken zurück"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Setzt Statistiken zurück"""
        self.stats = {
            'total_translations': 0,
            'successful_translations': 0,
            'failed_translations': 0,
            'provider_usage': {provider: 0 for provider in TranslationProvider},
            'fallback_usage': 0
        }
