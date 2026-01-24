"""
Text-to-Speech Service
======================

Provides TTS capabilities for audiobook generation.
Supports multiple TTS engines: XTTS, Coqui, OpenAI TTS, ElevenLabs.
"""
import os
import json
import hashlib
import tempfile
import structlog
from pathlib import Path
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from django.conf import settings

logger = structlog.get_logger(__name__)


class TTSEngine(ABC):
    """Abstract base class for TTS engines."""
    
    @abstractmethod
    def synthesize(self, text: str, voice_id: str, **kwargs) -> bytes:
        """Synthesize speech from text. Returns audio bytes (WAV/MP3)."""
        pass
    
    @abstractmethod
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the engine is available."""
        pass


class XTTSEngine(TTSEngine):
    """
    XTTS (Coqui TTS) engine for high-quality voice cloning.
    Requires local XTTS server or Coqui API.
    """
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv('XTTS_URL', 'http://localhost:8020')
        self.log = logger.bind(engine="XTTS", url=self.base_url)
    
    def is_available(self) -> bool:
        """Check if XTTS server is running."""
        try:
            import requests
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available XTTS voices."""
        try:
            import requests
            resp = requests.get(f"{self.base_url}/voices", timeout=10)
            if resp.status_code == 200:
                return resp.json().get('voices', [])
        except Exception as e:
            self.log.warning("failed_to_get_voices", error=str(e))
        
        # Return default voices if API fails
        return [
            {'id': 'default_male', 'name': 'Default Male', 'language': 'en'},
            {'id': 'default_female', 'name': 'Default Female', 'language': 'en'},
        ]
    
    def synthesize(self, text: str, voice_id: str, 
                   language: str = 'en', 
                   speed: float = 1.0,
                   **kwargs) -> bytes:
        """Synthesize speech using XTTS."""
        import requests
        
        payload = {
            'text': text,
            'voice_id': voice_id,
            'language': language,
            'speed': speed,
        }
        
        self.log.info("synthesizing", text_length=len(text), voice=voice_id)
        
        try:
            resp = requests.post(
                f"{self.base_url}/tts",
                json=payload,
                timeout=120  # TTS can be slow
            )
            
            if resp.status_code == 200:
                return resp.content
            else:
                raise Exception(f"XTTS error: {resp.status_code} - {resp.text}")
                
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to XTTS server at {self.base_url}")


class OpenAITTSEngine(TTSEngine):
    """
    OpenAI TTS engine using their API.
    High quality but costs money.
    """
    
    VOICES = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.log = logger.bind(engine="OpenAI-TTS")
    
    def is_available(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.api_key)
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available OpenAI TTS voices."""
        return [
            {'id': v, 'name': v.title(), 'language': 'multi'}
            for v in self.VOICES
        ]
    
    def synthesize(self, text: str, voice_id: str,
                   model: str = 'tts-1',
                   speed: float = 1.0,
                   **kwargs) -> bytes:
        """Synthesize speech using OpenAI TTS."""
        try:
            from openai import OpenAI
        except ImportError:
            raise Exception("OpenAI package not installed. Run: pip install openai")
        
        if not self.api_key:
            raise Exception("OpenAI API key not configured")
        
        client = OpenAI(api_key=self.api_key)
        
        self.log.info("synthesizing", text_length=len(text), voice=voice_id, model=model)
        
        response = client.audio.speech.create(
            model=model,
            voice=voice_id if voice_id in self.VOICES else 'alloy',
            input=text,
            speed=speed
        )
        
        return response.content


class ElevenLabsEngine(TTSEngine):
    """
    ElevenLabs TTS engine for ultra-realistic voices.
    Premium quality, API key required.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"
        self.log = logger.bind(engine="ElevenLabs")
    
    def is_available(self) -> bool:
        """Check if ElevenLabs API key is configured."""
        return bool(self.api_key)
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available ElevenLabs voices."""
        if not self.api_key:
            return []
        
        try:
            import requests
            resp = requests.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key},
                timeout=10
            )
            if resp.status_code == 200:
                voices = resp.json().get('voices', [])
                return [
                    {'id': v['voice_id'], 'name': v['name'], 'language': 'multi'}
                    for v in voices
                ]
        except Exception as e:
            self.log.warning("failed_to_get_voices", error=str(e))
        
        return []
    
    def synthesize(self, text: str, voice_id: str,
                   model_id: str = 'eleven_monolingual_v1',
                   **kwargs) -> bytes:
        """Synthesize speech using ElevenLabs."""
        import requests
        
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured")
        
        self.log.info("synthesizing", text_length=len(text), voice=voice_id)
        
        resp = requests.post(
            f"{self.base_url}/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            },
            timeout=120
        )
        
        if resp.status_code == 200:
            return resp.content
        else:
            raise Exception(f"ElevenLabs error: {resp.status_code} - {resp.text}")


class MockTTSEngine(TTSEngine):
    """
    Mock TTS engine for testing without real TTS.
    Generates silence or test tone.
    """
    
    def __init__(self):
        self.log = logger.bind(engine="MockTTS")
    
    def is_available(self) -> bool:
        return True
    
    def get_voices(self) -> List[Dict[str, Any]]:
        return [
            {'id': 'mock_male', 'name': 'Mock Male', 'language': 'en'},
            {'id': 'mock_female', 'name': 'Mock Female', 'language': 'en'},
        ]
    
    def synthesize(self, text: str, voice_id: str, **kwargs) -> bytes:
        """Generate silent WAV file for testing."""
        import struct
        import wave
        import io
        
        # Generate silence (1 second per 100 chars, min 1 second)
        duration = max(1.0, len(text) / 100.0)
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        
        # Create WAV in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            # Write silence (zeros)
            wav.writeframes(b'\x00\x00' * num_samples)
        
        self.log.info("mock_synthesized", text_length=len(text), duration=duration)
        return buffer.getvalue()


class TTSService:
    """
    Main TTS service that manages multiple engines.
    """
    
    ENGINES = {
        'xtts': XTTSEngine,
        'openai': OpenAITTSEngine,
        'elevenlabs': ElevenLabsEngine,
        'mock': MockTTSEngine,
    }
    
    def __init__(self, default_engine: str = 'xtts'):
        self.default_engine = default_engine
        self.engines: Dict[str, TTSEngine] = {}
        self.output_dir = Path(settings.MEDIA_ROOT) / 'media_hub' / 'audio'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log = logger.bind(service="TTSService")
        
        # Initialize engines lazily
    
    def get_engine(self, engine_name: Optional[str] = None) -> TTSEngine:
        """Get a TTS engine by name."""
        name = engine_name or self.default_engine
        
        if name not in self.engines:
            if name not in self.ENGINES:
                raise ValueError(f"Unknown TTS engine: {name}")
            self.engines[name] = self.ENGINES[name]()
        
        return self.engines[name]
    
    def get_available_engines(self) -> List[str]:
        """Get list of available (working) engines."""
        available = []
        for name, cls in self.ENGINES.items():
            try:
                engine = cls()
                if engine.is_available():
                    available.append(name)
            except Exception:
                pass
        return available
    
    def synthesize_text(self, text: str, 
                        voice_preset_slug: Optional[str] = None,
                        engine: Optional[str] = None,
                        **kwargs) -> Dict[str, Any]:
        """
        Synthesize text to audio file.
        
        Returns dict with file_path, duration, file_size.
        """
        from django.db import connection
        
        # Get voice preset settings
        voice_id = kwargs.get('voice_id', 'default')
        language = kwargs.get('language', 'en')
        
        if voice_preset_slug:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT engine, voice_id, language, defaults
                    FROM media_hub_voice_preset
                    WHERE slug = %s AND is_active = true
                """, [voice_preset_slug])
                row = cursor.fetchone()
                if row:
                    engine = engine or row[0]
                    voice_id = row[1]
                    language = row[2]
                    defaults = json.loads(row[3]) if row[3] else {}
                    kwargs.update(defaults)
        
        # Get engine
        tts_engine = self.get_engine(engine)
        
        if not tts_engine.is_available():
            self.log.warning("engine_not_available", engine=engine)
            # Fallback to mock
            tts_engine = self.get_engine('mock')
        
        # Synthesize
        audio_bytes = tts_engine.synthesize(text, voice_id, language=language, **kwargs)
        
        # Save to file
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        filename = f"tts_{engine or 'default'}_{voice_id}_{text_hash}.wav"
        filepath = self.output_dir / filename
        filepath.write_bytes(audio_bytes)
        
        # Get duration (approximate for WAV)
        duration = len(audio_bytes) / (22050 * 2)  # Assuming 22050Hz, 16-bit mono
        
        return {
            'success': True,
            'file_path': str(filepath),
            'filename': filename,
            'file_size': len(audio_bytes),
            'duration': duration,
            'mime_type': 'audio/wav',
            'engine': engine or self.default_engine,
            'voice_id': voice_id,
        }
    
    def synthesize_chapter(self, chapter_text: str,
                           chapter_id: int,
                           voice_preset_slug: Optional[str] = None,
                           **kwargs) -> Dict[str, Any]:
        """
        Synthesize an entire chapter to audio.
        Handles chunking for long texts.
        """
        # Split into manageable chunks (most TTS has length limits)
        max_chunk_size = 5000  # characters
        chunks = self._split_text(chapter_text, max_chunk_size)
        
        self.log.info("synthesizing_chapter", 
                     chapter_id=chapter_id, 
                     chunks=len(chunks),
                     total_chars=len(chapter_text))
        
        audio_parts = []
        for i, chunk in enumerate(chunks):
            result = self.synthesize_text(
                chunk,
                voice_preset_slug=voice_preset_slug,
                **kwargs
            )
            audio_parts.append(result)
            self.log.debug("chunk_complete", chunk=i+1, total=len(chunks))
        
        # Concatenate audio files
        if len(audio_parts) == 1:
            return audio_parts[0]
        
        # Merge audio files
        merged_path = self._merge_audio_files(
            [p['file_path'] for p in audio_parts],
            f"chapter_{chapter_id}"
        )
        
        total_size = sum(p['file_size'] for p in audio_parts)
        total_duration = sum(p['duration'] for p in audio_parts)
        
        return {
            'success': True,
            'file_path': merged_path,
            'file_size': total_size,
            'duration': total_duration,
            'mime_type': 'audio/wav',
            'chunks': len(audio_parts),
        }
    
    def _split_text(self, text: str, max_size: int) -> List[str]:
        """Split text into chunks at sentence boundaries."""
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        current = ""
        
        # Split by sentences (simple approach)
        sentences = text.replace('\n', ' ').split('. ')
        
        for sentence in sentences:
            if len(current) + len(sentence) + 2 <= max_size:
                current += sentence + '. '
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence + '. '
        
        if current:
            chunks.append(current.strip())
        
        return chunks
    
    def _merge_audio_files(self, file_paths: List[str], output_name: str) -> str:
        """Merge multiple audio files into one."""
        import wave
        
        output_path = self.output_dir / f"{output_name}_merged.wav"
        
        # Read all WAV files
        data = []
        params = None
        
        for fp in file_paths:
            with wave.open(fp, 'rb') as wav:
                if params is None:
                    params = wav.getparams()
                data.append(wav.readframes(wav.getnframes()))
        
        # Write merged file
        with wave.open(str(output_path), 'wb') as output:
            output.setparams(params)
            for d in data:
                output.writeframes(d)
        
        return str(output_path)
