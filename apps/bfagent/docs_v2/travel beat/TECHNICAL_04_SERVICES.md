# Travel Story - Technische Dokumentation

## Teil 4: Services, Celery & Setup

---

## Inhaltsverzeichnis

1. [Services](#1-services)
2. [Celery Tasks](#2-celery-tasks)
3. [LLM Integration](#3-llm-integration)
4. [Projekt-Setup](#4-projekt-setup)
5. [Deployment](#5-deployment)
6. [Konfiguration](#6-konfiguration)

---

## 1. Services

### ReadingTimeCalculator

```python
# services/calculator.py
from dataclasses import dataclass
from typing import List
from datetime import date, timedelta

from trips.models import Trip, Stop, Transport


@dataclass
class DaySchedule:
    """Lesezeit für einen Tag"""
    date: date
    location: str
    morning_minutes: int = 0
    transport_minutes: int = 0
    pool_minutes: int = 0
    evening_minutes: int = 0
    
    @property
    def total_minutes(self) -> int:
        return (
            self.morning_minutes + 
            self.transport_minutes + 
            self.pool_minutes + 
            self.evening_minutes
        )


@dataclass
class CalculationResult:
    """Ergebnis der Lesezeit-Berechnung"""
    total_minutes: int
    total_words: int
    recommended_chapters: int
    daily_schedule: List[DaySchedule]
    
    @property
    def hours(self) -> float:
        return self.total_minutes / 60


class ReadingTimeCalculator:
    """Berechnet verfügbare Lesezeit für eine Reise"""
    
    # Konstanten
    WORDS_PER_MINUTE = 250  # Durchschnittliche Lesegeschwindigkeit
    WORDS_PER_CHAPTER = 3500  # Durchschnitt
    MAX_CHAPTERS = 30
    
    # Transport-Effizienz (% der Reisezeit = Lesezeit)
    TRANSPORT_EFFICIENCY = {
        'flight': 0.55,      # 55% (Boarding, Turbulenz, etc.)
        'train': 0.80,       # 80% (sehr lesefreundlich)
        'bus': 0.50,         # 50% (Bewegung, enger)
        'car_passenger': 0.40,  # 40% (Übelkeit möglich)
        'car_driver': 0.0,   # 0% (Fahrer!)
        'ferry': 0.60,       # 60%
    }
    
    # Abend-Lesezeit nach Unterkunft (Minuten)
    EVENING_READING = {
        'hotel': 45,
        'airbnb': 50,
        'hostel': 30,
        'camping': 20,
        'friends': 25,
        'other': 30,
    }
    
    # Pool/Strand-Zeit nach Reisetyp (Minuten)
    POOL_READING = {
        'beach': 90,
        'wellness': 75,
        'city': 0,
        'backpacking': 15,
        'business': 0,
        'family': 30,
    }
    
    def calculate(self, trip: Trip, reading_speed: str = 'normal') -> CalculationResult:
        """
        Berechne Lesezeit für eine Reise.
        
        Args:
            trip: Trip Model
            reading_speed: 'slow', 'normal', 'fast'
        
        Returns:
            CalculationResult mit Zeitplan
        """
        # Lesegeschwindigkeit anpassen
        wpm_multiplier = {'slow': 0.8, 'normal': 1.0, 'fast': 1.2}
        wpm = self.WORDS_PER_MINUTE * wpm_multiplier.get(reading_speed, 1.0)
        
        daily_schedules = []
        current_date = trip.start_date
        
        while current_date <= trip.end_date:
            schedule = self._calculate_day(trip, current_date)
            daily_schedules.append(schedule)
            current_date += timedelta(days=1)
        
        total_minutes = sum(d.total_minutes for d in daily_schedules)
        total_words = int(total_minutes * wpm)
        recommended_chapters = min(
            self.MAX_CHAPTERS,
            max(1, total_words // self.WORDS_PER_CHAPTER)
        )
        
        return CalculationResult(
            total_minutes=total_minutes,
            total_words=total_words,
            recommended_chapters=recommended_chapters,
            daily_schedule=daily_schedules,
        )
    
    def _calculate_day(self, trip: Trip, day: date) -> DaySchedule:
        """Berechne Lesezeit für einen Tag"""
        
        # Aktueller Stopp finden
        stop = trip.stops.filter(
            arrival_date__lte=day,
            departure_date__gte=day
        ).first()
        
        if not stop:
            return DaySchedule(date=day, location="Transit")
        
        schedule = DaySchedule(date=day, location=stop.city)
        
        # Erster Tag: Kein Morgen-Lesen
        if day != stop.arrival_date:
            schedule.morning_minutes = 15
        
        # Letzter Tag: Abreise-Transport
        if day == stop.departure_date:
            transport = trip.transports.filter(from_stop=stop).first()
            if transport:
                efficiency = self.TRANSPORT_EFFICIENCY.get(
                    transport.transport_type, 0.5
                )
                schedule.transport_minutes = int(
                    transport.duration_minutes * efficiency
                )
        
        # Pool/Strand je nach Reisetyp
        schedule.pool_minutes = self.POOL_READING.get(trip.trip_type, 0)
        
        # Abend-Lesezeit (nicht am letzten Abend)
        if day != stop.departure_date:
            schedule.evening_minutes = self.EVENING_READING.get(
                stop.accommodation_type, 30
            )
        
        return schedule
```

### StoryMapper

```python
# services/story_mapper.py
from dataclasses import dataclass
from typing import List
from enum import Enum


class StoryBeat(Enum):
    """Story-Beats nach klassischer Struktur"""
    HOOK = "hook"
    SETUP = "setup"
    INCITING_INCIDENT = "inciting_incident"
    FIRST_PLOT_POINT = "first_plot_point"
    RISING_ACTION = "rising_action"
    MIDPOINT = "midpoint"
    COMPLICATIONS = "complications"
    DARK_NIGHT = "dark_night"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


@dataclass
class ChapterOutline:
    """Outline für ein Kapitel"""
    chapter_number: int
    beat: StoryBeat
    beat_description: str
    target_words: int
    story_location: str
    reader_location: str
    reading_date: str
    pacing: str  # action, emotional, reflective, atmospheric
    emotional_tone: str
    special_instructions: List[str]


class StoryMapper:
    """Mappt Lesezeit-Slots zu Story-Beats"""
    
    # Beat-Verteilung (relativ)
    BEAT_WEIGHTS = {
        StoryBeat.HOOK: 1,
        StoryBeat.SETUP: 2,
        StoryBeat.INCITING_INCIDENT: 1,
        StoryBeat.FIRST_PLOT_POINT: 1,
        StoryBeat.RISING_ACTION: 3,
        StoryBeat.MIDPOINT: 1,
        StoryBeat.COMPLICATIONS: 3,
        StoryBeat.DARK_NIGHT: 1,
        StoryBeat.CLIMAX: 1,
        StoryBeat.RESOLUTION: 1,
    }
    
    BEAT_DESCRIPTIONS = {
        StoryBeat.HOOK: "Fesselnder Einstieg, der den Leser sofort packt",
        StoryBeat.SETUP: "Einführung der Welt, Charaktere und Status Quo",
        StoryBeat.INCITING_INCIDENT: "Das Ereignis, das alles verändert",
        StoryBeat.FIRST_PLOT_POINT: "Protagonist betritt die neue Welt",
        StoryBeat.RISING_ACTION: "Konflikte eskalieren, Stakes steigen",
        StoryBeat.MIDPOINT: "Wendepunkt - alles ändert sich",
        StoryBeat.COMPLICATIONS: "Alles wird schwieriger, Rückschläge",
        StoryBeat.DARK_NIGHT: "Tiefpunkt - alles scheint verloren",
        StoryBeat.CLIMAX: "Finale Konfrontation",
        StoryBeat.RESOLUTION: "Auflösung und neuer Status Quo",
    }
    
    def generate_outline(
        self,
        total_words: int,
        num_chapters: int,
        daily_schedule: List,
        genre: str,
    ) -> List[ChapterOutline]:
        """
        Generiere Story-Outline basierend auf Lesezeit.
        
        Args:
            total_words: Gesamte Wortzahl
            num_chapters: Anzahl Kapitel
            daily_schedule: DaySchedule Liste
            genre: Story-Genre
        
        Returns:
            Liste von ChapterOutline
        """
        # Beats zu Kapiteln zuordnen
        beats = self._distribute_beats(num_chapters)
        
        # Wörter pro Kapitel
        words_per_chapter = total_words // num_chapters
        
        # Slots flattenen
        slots = self._flatten_schedule(daily_schedule)
        
        outlines = []
        for i, beat in enumerate(beats):
            slot = slots[i] if i < len(slots) else slots[-1]
            
            outline = ChapterOutline(
                chapter_number=i + 1,
                beat=beat,
                beat_description=self.BEAT_DESCRIPTIONS[beat],
                target_words=words_per_chapter,
                story_location=slot.location,
                reader_location=slot.location,
                reading_date=str(slot.date),
                pacing=self._get_pacing(beat, genre),
                emotional_tone=self._get_tone(beat),
                special_instructions=self._get_instructions(beat, genre),
            )
            outlines.append(outline)
        
        return outlines
    
    def _distribute_beats(self, num_chapters: int) -> List[StoryBeat]:
        """Verteile Beats auf Kapitel"""
        beats = list(StoryBeat)
        
        if num_chapters <= len(beats):
            # Weniger Kapitel als Beats: Wichtigste auswählen
            essential = [
                StoryBeat.HOOK,
                StoryBeat.INCITING_INCIDENT,
                StoryBeat.MIDPOINT,
                StoryBeat.DARK_NIGHT,
                StoryBeat.CLIMAX,
                StoryBeat.RESOLUTION,
            ]
            return essential[:num_chapters]
        
        # Mehr Kapitel: Beats wiederholen nach Gewicht
        result = []
        total_weight = sum(self.BEAT_WEIGHTS.values())
        
        for beat in beats:
            weight = self.BEAT_WEIGHTS[beat]
            count = max(1, int(num_chapters * weight / total_weight))
            result.extend([beat] * count)
        
        # Auf exakte Länge anpassen
        while len(result) < num_chapters:
            result.insert(-2, StoryBeat.COMPLICATIONS)
        
        return result[:num_chapters]
    
    def _get_pacing(self, beat: StoryBeat, genre: str) -> str:
        """Bestimme Pacing für Beat"""
        action_beats = {
            StoryBeat.INCITING_INCIDENT,
            StoryBeat.FIRST_PLOT_POINT,
            StoryBeat.CLIMAX,
        }
        
        emotional_beats = {
            StoryBeat.DARK_NIGHT,
            StoryBeat.RESOLUTION,
        }
        
        if beat in action_beats:
            return "action"
        elif beat in emotional_beats:
            return "emotional"
        elif genre == "romance":
            return "atmospheric"
        else:
            return "balanced"
    
    def _get_tone(self, beat: StoryBeat) -> str:
        """Bestimme emotionalen Ton"""
        tones = {
            StoryBeat.HOOK: "neugierig, fesselnd",
            StoryBeat.SETUP: "einladend, atmosphärisch",
            StoryBeat.INCITING_INCIDENT: "überraschend, aufregend",
            StoryBeat.FIRST_PLOT_POINT: "entschlossen, mutig",
            StoryBeat.RISING_ACTION: "angespannt, hoffnungsvoll",
            StoryBeat.MIDPOINT: "erschütternd, transformativ",
            StoryBeat.COMPLICATIONS: "frustriert, kämpferisch",
            StoryBeat.DARK_NIGHT: "verzweifelt, verletzlich",
            StoryBeat.CLIMAX: "intensiv, entscheidend",
            StoryBeat.RESOLUTION: "erleichtert, hoffnungsvoll",
        }
        return tones.get(beat, "neutral")
    
    def _get_instructions(self, beat: StoryBeat, genre: str) -> List[str]:
        """Spezielle Anweisungen für Beat"""
        instructions = []
        
        if beat == StoryBeat.HOOK:
            instructions.append("Beginne mitten in der Handlung")
            instructions.append("Stelle eine Frage, die der Leser beantwortet haben will")
        
        if beat == StoryBeat.CLIMAX and genre in ['thriller', 'romantic_suspense']:
            instructions.append("Maximale Spannung")
            instructions.append("Kurze, dynamische Sätze")
        
        if beat == StoryBeat.DARK_NIGHT and genre == 'romance':
            instructions.append("Emotionale Tiefe zeigen")
            instructions.append("Verwundbarkeit der Charaktere")
        
        return instructions
    
    def _flatten_schedule(self, schedule: List) -> List:
        """Flatten Schedule zu Slot-Liste"""
        return [s for s in schedule if s.total_minutes > 0]
```

---

## 2. Celery Tasks

### Celery Konfiguration

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('travel_story')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


# config/settings.py (Celery Settings)
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Berlin'

# Task-spezifische Settings
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 Minuten
CELERY_TASK_TIME_LIMIT = 600       # 10 Minuten hard limit
```

### Story Generation Task

```python
# stories/tasks.py
from celery import shared_task
from django.utils import timezone

from .models import Story, Chapter
from .generator import IntegratedStoryGenerator
from services.calculator import ReadingTimeCalculator
from services.story_mapper import StoryMapper
from worlds.models import UserWorld


@shared_task(bind=True, max_retries=3)
def generate_story_task(self, story_id: int):
    """
    Celery Task für Story-Generierung.
    
    Workflow:
    1. Trip laden, Lesezeit berechnen
    2. Story-Outline erstellen
    3. Kapitel generieren (sequentiell)
    4. Story als complete markieren
    """
    try:
        story = Story.objects.get(pk=story_id)
        trip = story.trip
        user = story.user
        
        # User World laden
        user_world = getattr(user, 'world', None)
        
        # 1. Lesezeit berechnen
        calculator = ReadingTimeCalculator()
        calc_result = calculator.calculate(trip)
        
        # 2. Story-Outline erstellen
        mapper = StoryMapper()
        outlines = mapper.generate_outline(
            total_words=calc_result.total_words,
            num_chapters=calc_result.recommended_chapters,
            daily_schedule=calc_result.daily_schedule,
            genre=story.genre,
        )
        
        story.total_chapters = len(outlines)
        story.save()
        
        # 3. Generator initialisieren
        generator = IntegratedStoryGenerator(
            use_real_llm=True
        )
        
        # 4. Kapitel generieren
        total_words = 0
        for outline in outlines:
            chapter = generator.generate_chapter(
                chapter_spec=outline,
                story_context=story.context,
                user_world=user_world,
            )
            
            # Chapter speichern
            Chapter.objects.create(
                story=story,
                number=outline.chapter_number,
                title=chapter.title,
                content=chapter.content,
                word_count=chapter.word_count,
                story_location=outline.story_location,
                reader_location=outline.reader_location,
                reading_date=outline.reading_date,
                beat_info={
                    'beat_name': outline.beat.value,
                    'pacing': outline.pacing,
                    'emotional_tone': outline.emotional_tone,
                },
                model_used=chapter.model_used,
                generated_at=timezone.now(),
            )
            
            total_words += chapter.word_count
            
            # Progress Update (für Polling)
            story.total_words = total_words
            story.save(update_fields=['total_words', 'updated_at'])
        
        # 5. Story als complete markieren
        story.status = Story.Status.COMPLETE
        story.completed_at = timezone.now()
        story.save()
        
        # User World Stats aktualisieren
        if user_world:
            user_world.stories_generated += 1
            user_world.save()
        
        return {'status': 'success', 'story_id': story_id}
    
    except Exception as exc:
        # Fehler loggen und Story als error markieren
        story = Story.objects.get(pk=story_id)
        story.status = Story.Status.ERROR
        story.context['error_message'] = str(exc)
        story.save()
        
        # Retry bei transienten Fehlern
        if 'rate limit' in str(exc).lower():
            raise self.retry(exc=exc, countdown=60)
        
        raise


@shared_task
def cleanup_expired_cache():
    """Periodischer Task: Abgelaufenen Cache löschen"""
    from locations.models import ResearchCache
    
    deleted, _ = ResearchCache.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
    
    return {'deleted': deleted}


# Periodic Tasks (celery beat)
# config/settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-cache-daily': {
        'task': 'stories.tasks.cleanup_expired_cache',
        'schedule': crontab(hour=3, minute=0),  # 3:00 Uhr
    },
}
```

---

## 3. LLM Integration

### AnthropicClient

```python
# services/llm_client.py
import os
import json
from typing import Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response vom LLM"""
    content: str
    model: str
    input_tokens: int
    output_tokens: int


class AnthropicClient:
    """
    Wrapper für Anthropic Claude API.
    Verwendet für Location- und Story-Generierung.
    """
    
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    
    def __init__(self, model: str = None):
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY nicht gesetzt")
        
        self.model = model or self.DEFAULT_MODEL
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Client"""
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client
    
    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Generiere Text mit Claude.
        
        Args:
            prompt: User-Prompt
            system: System-Prompt
            max_tokens: Max Output Tokens
            temperature: Kreativität (0.0 - 1.0)
        
        Returns:
            LLMResponse
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
    
    def generate_json(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
    ) -> dict:
        """
        Generiere JSON-Output.
        Bereinigt Markdown-Codeblocks automatisch.
        """
        response = self.generate(
            prompt=prompt,
            system=system + "\n\nAntworte NUR mit validem JSON.",
            max_tokens=max_tokens,
            temperature=0.3,  # Niedriger für strukturierte Outputs
        )
        
        text = response.content.strip()
        
        # Markdown bereinigen
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return json.loads(text.strip())
```

---

## 4. Projekt-Setup

### Projekt-Struktur

```
travel_story/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/
│   ├── trips/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── templates/
│   │
│   ├── locations/
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── generator.py
│   │   └── management/commands/
│   │
│   ├── worlds/
│   │   ├── models.py
│   │   ├── views.py
│   │   └── forms.py
│   │
│   ├── stories/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── tasks.py
│   │   ├── generator.py
│   │   └── prompts.py
│   │
│   └── users/
│       ├── models.py
│       └── views.py
│
├── services/
│   ├── calculator.py
│   ├── story_mapper.py
│   ├── llm_client.py
│   └── exporters/
│
├── templates/
│   ├── base.html
│   ├── components/
│   └── partials/
│
├── static/
│   ├── css/
│   └── js/
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── manage.py
└── README.md
```

### Requirements

```txt
# requirements/base.txt
Django>=5.0,<5.1
psycopg2-binary>=2.9.9
redis>=5.0
celery>=5.3
anthropic>=0.18.0

# HTMX (via CDN oder)
django-htmx>=1.17

# Forms
django-crispy-forms>=2.1
crispy-tailwind>=1.0

# Auth
django-allauth>=0.60

# Utils
python-dotenv>=1.0
whitenoise>=6.6

# requirements/development.txt
-r base.txt
django-debug-toolbar>=4.2
pytest-django>=4.7

# requirements/production.txt
-r base.txt
gunicorn>=21.0
sentry-sdk>=1.39
```

### Settings

```python
# config/settings/base.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third Party
    'django_htmx',
    'crispy_forms',
    'crispy_tailwind',
    'allauth',
    'allauth.account',
    
    # Local Apps
    'apps.users',
    'apps.trips',
    'apps.locations',
    'apps.worlds',
    'apps.stories',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django_htmx.middleware.HtmxMiddleware',  # HTMX
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'travel_story'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Celery
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# Anthropic
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
```

---

## 5. Deployment

### Docker Compose

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  web:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - SECRET_KEY=${SECRET_KEY}
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_HOST=db
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: celery -A config worker -l info
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - SECRET_KEY=${SECRET_KEY}
      - POSTGRES_HOST=db
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery-beat:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: celery -A config beat -l info
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - SECRET_KEY=${SECRET_KEY}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### Dockerfile

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# System Dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements/production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App Code
COPY . .

# Static Files
RUN python manage.py collectstatic --noinput

# User
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
```

---

## 6. Konfiguration

### Environment Variables

```bash
# .env.example

# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=travel-story.app,www.travel-story.app

# Database
POSTGRES_DB=travel_story
POSTGRES_USER=travel_story
POSTGRES_PASSWORD=secure-password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Email (optional)
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-key

# Sentry (optional)
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### Management Commands

```bash
# Initiales Setup
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

# Location Seed
python manage.py seed_locations --cities barcelona,rom,paris

# Cache Management
python manage.py clear_expired_cache
python manage.py warmup_cache --cities barcelona,rom

# Celery
celery -A config worker -l info
celery -A config beat -l info
```

---

## Zusammenfassung

### Architektur-Entscheidungen

| Entscheidung | Begründung |
|--------------|------------|
| **Django + HTMX** | Server-rendered, kein JS-Framework nötig |
| **PostgreSQL JSONB** | Flexible Schemas für Location-Daten |
| **Celery** | Story-Generierung kann lang dauern |
| **3-Schichten Locations** | Effizienz durch Sharing |
| **Redis** | Cache + Celery Broker |

### Kostenschätzung (pro Story)

| Komponente | Tokens | Kosten |
|------------|--------|--------|
| Location Base | ~1.500 | $0.005 |
| Location Layer | ~2.000 | $0.007 |
| 10 Kapitel | ~40.000 | $0.15 |
| **Gesamt** | ~45.000 | **~$0.17** |

---

*Ende der technischen Dokumentation*
