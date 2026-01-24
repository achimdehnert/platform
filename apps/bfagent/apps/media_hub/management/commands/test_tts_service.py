"""
Test TTS Service Command
========================

Test the Media Hub TTS service with sample text.

Usage:
    python manage.py test_tts_service
    python manage.py test_tts_service --engine openai --text "Hello world"
    python manage.py test_tts_service --voice de-male-standard
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test the Media Hub TTS service'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--engine',
            type=str,
            default='mock',
            choices=['xtts', 'openai', 'elevenlabs', 'mock'],
            help='TTS engine to use'
        )
        parser.add_argument(
            '--voice',
            type=str,
            help='Voice preset slug to use'
        )
        parser.add_argument(
            '--text',
            type=str,
            default='Dies ist ein Test der Text-zu-Sprache Funktion. Die Media Hub Audioausgabe funktioniert korrekt.',
            help='Text to synthesize'
        )
        parser.add_argument(
            '--list-engines',
            action='store_true',
            help='List available TTS engines'
        )
        parser.add_argument(
            '--list-voices',
            action='store_true',
            help='List available voice presets'
        )
    
    def handle(self, *args, **options):
        from apps.media_hub.services.tts_service import TTSService
        from django.db import connection
        
        tts = TTSService()
        
        if options['list_engines']:
            self.stdout.write("\n🔊 Available TTS Engines:")
            self.stdout.write("-" * 40)
            available = tts.get_available_engines()
            for name in ['xtts', 'openai', 'elevenlabs', 'mock']:
                status = "✅" if name in available else "❌"
                self.stdout.write(f"  {status} {name}")
            return
        
        if options['list_voices']:
            self.stdout.write("\n🎤 Available Voice Presets:")
            self.stdout.write("-" * 40)
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT slug, name, engine, language, gender
                    FROM media_hub_voice_preset WHERE is_active = true
                    ORDER BY language, name
                """)
                for row in cursor.fetchall():
                    self.stdout.write(f"  {row[0]}: {row[1]} ({row[2]}, {row[3]}, {row[4]})")
            return
        
        engine = options['engine']
        text = options['text']
        voice = options['voice']
        
        self.stdout.write("\n🔊 Testing TTS Service")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Engine: {engine}")
        self.stdout.write(f"Voice Preset: {voice or 'default'}")
        self.stdout.write(f"Text: {text[:50]}...")
        self.stdout.write("")
        
        # Check engine availability
        available = tts.get_available_engines()
        if engine not in available:
            self.stdout.write(self.style.WARNING(
                f"⚠️  Engine '{engine}' not available. Available: {available}"
            ))
            if engine != 'mock':
                self.stdout.write("   Falling back to 'mock' engine...")
                engine = 'mock'
        
        # Synthesize
        self.stdout.write("🎵 Synthesizing...")
        
        try:
            result = tts.synthesize_text(
                text,
                voice_preset_slug=voice,
                engine=engine
            )
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS("\n✅ TTS Synthesis Complete!"))
                self.stdout.write(f"   File: {result['file_path']}")
                self.stdout.write(f"   Size: {result['file_size']} bytes")
                self.stdout.write(f"   Duration: {result.get('duration', 0):.1f}s")
                self.stdout.write(f"   Engine: {result.get('engine')}")
                
                self.stdout.write("\n💡 To play the audio:")
                self.stdout.write(f"   open {result['file_path']}")
            else:
                self.stdout.write(self.style.ERROR(f"\n❌ TTS failed: {result}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}"))
        
        self.stdout.write("")
