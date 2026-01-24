#!/usr/bin/env python3
"""
Translation Cache Implementation for V6.5 Pipeline
Simple JSON-based caching system for translation results
"""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
import os

logger = logging.getLogger(__name__)


class TranslationCache:
    """
    Simple translation cache using JSON storage for translation memory.
    Provides caching, consistency, and cost reduction for translation operations.
    """
    
    def __init__(self, cache_file: str = "translation_cache.json", cache_dir: str = None):
        """
        Initialize translation cache
        
        Args:
            cache_file: Name of the cache file
            cache_dir: Directory to store cache files (auto-detected if None)
        """
        if cache_dir is None:
            # Auto-detect cache directory relative to current working environment
            current_dir = Path.cwd()
            
            # Check if we're in a project folder (develop/stable/etc)
            if current_dir.name in ["develop", "stable"] and current_dir.parent.exists():
                # We're in a project subfolder, use cache in current folder
                self.cache_dir = current_dir / "cache"
            elif any(folder.exists() for folder in [current_dir / "develop", current_dir / "stable"]):
                # We're in project root, detect which environment to use
                if (current_dir / "develop").exists():
                    self.cache_dir = current_dir / "develop" / "cache"
                elif (current_dir / "stable").exists():
                    self.cache_dir = current_dir / "stable" / "cache"
                else:
                    self.cache_dir = current_dir / "cache"
            else:
                # Fallback: create cache in current directory
                self.cache_dir = current_dir / "cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / cache_file
        self.cache = self._load_cache()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0
        }
        
        logger.info(f"Translation cache initialized: {self.cache_file}")
        logger.info(f"Cache entries loaded: {len(self.cache)}")
    
    def _generate_key(self, source_text: str, source_lang: str, target_lang: str) -> str:
        """Generate unique key for translation pair"""
        # Normalize text for consistent hashing
        normalized_text = source_text.strip().replace('\n', ' ').replace('\r', '')
        content = f"{source_lang}:{target_lang}:{normalized_text}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from JSON file"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    logger.info(f"Loaded {len(cache_data)} cached translations")
                    return cache_data
        except Exception as e:
            logger.warning(f"Could not load cache file: {e}")
        
        return {}
    
    def _save_cache(self) -> None:
        """Save cache to JSON file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cache saved with {len(self.cache)} entries")
        except Exception as e:
            logger.error(f"Could not save cache file: {e}")
    
    def get_translation(self, source_text: str, source_lang: str, target_lang: str) -> Optional[Dict[str, Any]]:
        """
        Get cached translation if available
        
        Args:
            source_text: Original text to translate
            source_lang: Source language code (e.g., 'de')
            target_lang: Target language code (e.g., 'en')
            
        Returns:
            Cached translation data or None if not found
        """
        key = self._generate_key(source_text, source_lang, target_lang)
        
        if key in self.cache:
            self.stats['hits'] += 1
            cached_entry = self.cache[key]
            logger.debug(f"Cache HIT: '{source_text[:30]}...' → '{cached_entry['target_text'][:30]}...'")
            return cached_entry
        
        self.stats['misses'] += 1
        logger.debug(f"Cache MISS: '{source_text[:30]}...'")
        return None
    
    def save_translation(self, 
                        source_text: str, 
                        target_text: str, 
                        source_lang: str, 
                        target_lang: str, 
                        provider: str = "deepl",
                        confidence: float = 1.0,
                        manual_edit: bool = False) -> None:
        """
        Save translation to cache
        
        Args:
            source_text: Original text
            target_text: Translated text
            source_lang: Source language code
            target_lang: Target language code
            provider: Translation provider used
            confidence: Translation confidence score
            manual_edit: Whether this is a manual edit
        """
        key = self._generate_key(source_text, source_lang, target_lang)
        
        self.cache[key] = {
            'source_text': source_text,
            'target_text': target_text,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'provider': provider,
            'confidence': confidence,
            'manual_edit': manual_edit,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.stats['saves'] += 1
        self._save_cache()
        
        logger.debug(f"Cache SAVE: '{source_text[:30]}...' → '{target_text[:30]}...' (manual: {manual_edit})")
    
    def update_translation(self, 
                          source_text: str, 
                          target_text: str, 
                          source_lang: str, 
                          target_lang: str,
                          manual_edit: bool = True) -> None:
        """
        Update existing translation (typically for manual edits)
        
        Args:
            source_text: Original text
            target_text: Updated translated text
            source_lang: Source language code
            target_lang: Target language code
            manual_edit: Whether this is a manual edit
        """
        key = self._generate_key(source_text, source_lang, target_lang)
        
        if key in self.cache:
            self.cache[key]['target_text'] = target_text
            self.cache[key]['manual_edit'] = manual_edit
            self.cache[key]['updated_at'] = datetime.now().isoformat()
            self._save_cache()
            
            logger.info(f"Cache UPDATE: '{source_text[:30]}...' → '{target_text[:30]}...' (manual: {manual_edit})")
        else:
            # Create new entry if not exists
            self.save_translation(source_text, target_text, source_lang, target_lang, 
                                manual_edit=manual_edit)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0
        
        return {
            'total_entries': len(self.cache),
            'cache_hits': self.stats['hits'],
            'cache_misses': self.stats['misses'],
            'cache_saves': self.stats['saves'],
            'hit_rate': f"{hit_rate:.2%}",
            'cache_file': str(self.cache_file),
            'file_size_kb': self.cache_file.stat().st_size // 1024 if self.cache_file.exists() else 0
        }
    
    def clear_cache(self) -> None:
        """Clear all cached translations"""
        self.cache.clear()
        self._save_cache()
        logger.info("Translation cache cleared")
    
    def export_translations(self, output_file: str) -> None:
        """Export translations to a different file"""
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
        logger.info(f"Translations exported to: {output_path}")
    
    def get_translations_by_language_pair(self, source_lang: str, target_lang: str) -> Dict[str, str]:
        """Get all translations for a specific language pair"""
        translations = {}
        for entry in self.cache.values():
            if entry['source_lang'] == source_lang and entry['target_lang'] == target_lang:
                translations[entry['source_text']] = entry['target_text']
        return translations
    
    def get_manual_edits(self) -> Dict[str, Any]:
        """Get all manual edits from cache"""
        manual_edits = {}
        for key, entry in self.cache.items():
            if entry.get('manual_edit', False):
                manual_edits[key] = entry
        return manual_edits


# Global cache instance
_global_cache = None

def get_translation_cache(cache_file: str = "translation_cache.json", cache_dir: str = None) -> TranslationCache:
    """Get global translation cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = TranslationCache(cache_file, cache_dir)
    return _global_cache


if __name__ == "__main__":
    # Test the translation cache
    logging.basicConfig(level=logging.DEBUG)
    
    cache = TranslationCache()
    
    # Test saving and retrieving
    cache.save_translation("Hallo Welt", "Hello World", "de", "en", manual_edit=False)
    cache.save_translation("Guten Tag", "Good Day", "de", "en", manual_edit=True)
    
    # Test retrieval
    result = cache.get_translation("Hallo Welt", "de", "en")
    print(f"Retrieved: {result}")
    
    # Test stats
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")
    
    # Test language pair export
    de_en_translations = cache.get_translations_by_language_pair("de", "en")
    print(f"DE→EN translations: {de_en_translations}")
