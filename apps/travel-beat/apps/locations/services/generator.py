"""
Location Generator - On-Demand Location Research

Generates location data using LLM when not in cache:
1. Check cache first
2. Generate via LLM if needed
3. Parse and structure response
4. Store in BaseLocation + LocationLayer
5. Cache raw data for future use
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import transaction

try:
    import anthropic
except ImportError:
    anthropic = None

from apps.locations.models import BaseLocation, LocationLayer, ResearchCache
from apps.stories.services.prompts import PromptBuilder
from .cache import LocationCache

logger = logging.getLogger(__name__)


@dataclass
class LocationResult:
    """Result of location generation."""
    success: bool
    base_location: Optional[BaseLocation] = None
    location_layer: Optional[LocationLayer] = None
    from_cache: bool = False
    error: str = ""


class LocationGenerator:
    """
    Generates location data on-demand using LLM.
    
    Flow:
    1. Check if BaseLocation exists
    2. Check if LocationLayer for genre exists
    3. Check cache for raw research data
    4. If not found, generate via LLM
    5. Parse, validate, and store
    """
    
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4000
    
    def __init__(self):
        self.client = self._get_client()
    
    def _get_client(self):
        """Get Anthropic client."""
        if anthropic is None:
            logger.error("Anthropic package not installed")
            return None
        
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not configured")
            return None
        
        return anthropic.Anthropic(api_key=api_key)
    
    def get_or_generate(self, city: str, country: str, genre: str) -> LocationResult:
        """
        Get location data, generating if necessary.
        
        Returns existing data if available, otherwise generates new.
        """
        
        # Step 1: Check for existing BaseLocation
        base_location = BaseLocation.objects.filter(
            city__iexact=city,
            country__iexact=country,
        ).first()
        
        if base_location:
            # Step 2: Check for genre layer
            layer = LocationLayer.objects.filter(
                base_location=base_location,
                genre=genre,
            ).first()
            
            if layer:
                return LocationResult(
                    success=True,
                    base_location=base_location,
                    location_layer=layer,
                    from_cache=True,
                )
        
        # Step 3: Check research cache
        cached_data = LocationCache.get(city, country, genre)
        
        if cached_data:
            # Create/update from cache
            result = self._create_from_data(city, country, genre, cached_data)
            result.from_cache = True
            return result
        
        # Step 4: Generate new data via LLM
        if not self.client:
            return LocationResult(success=False, error="LLM client not available")
        
        return self._generate_new(city, country, genre)
    
    def _generate_new(self, city: str, country: str, genre: str) -> LocationResult:
        """Generate new location data via LLM."""
        
        prompt = PromptBuilder.build_location_research_prompt(city, country, genre)
        
        try:
            message = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = message.content[0].text if message.content else ""
            
            # Parse response
            data = self._parse_response(content)
            
            if not data:
                return LocationResult(
                    success=False,
                    error="Failed to parse LLM response"
                )
            
            # Cache raw data
            LocationCache.set(city, country, genre, data, source='llm')
            
            # Create database entries
            return self._create_from_data(city, country, genre, data)
            
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return LocationResult(success=False, error=str(e))
        except Exception as e:
            logger.exception("Location generation failed")
            return LocationResult(success=False, error=str(e))
    
    def _parse_response(self, content: str) -> Optional[dict]:
        """Parse LLM response into structured data."""
        try:
            # Try to extract JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON parse failed: {e}")
        
        # Fallback: try to extract structured info
        return self._extract_from_text(content)
    
    def _extract_from_text(self, content: str) -> Optional[dict]:
        """Extract location info from unstructured text."""
        # Basic fallback extraction
        places = []
        lines = content.split('\n')
        
        current_place = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_place:
                    places.append(current_place)
                    current_place = {}
                continue
            
            # Try to identify place names (lines that look like headers)
            if line.endswith(':') or (len(line) < 50 and not line.startswith('-')):
                if current_place:
                    places.append(current_place)
                current_place = {'name': line.rstrip(':')}
            elif line.startswith('-'):
                # Detail line
                if 'details' not in current_place:
                    current_place['details'] = []
                current_place['details'].append(line[1:].strip())
        
        if current_place:
            places.append(current_place)
        
        if places:
            return {'places': places, 'raw_text': content}
        
        return None
    
    @transaction.atomic
    def _create_from_data(
        self,
        city: str,
        country: str,
        genre: str,
        data: dict
    ) -> LocationResult:
        """Create BaseLocation and LocationLayer from parsed data."""
        
        # Get or create BaseLocation
        base_location, created = BaseLocation.objects.get_or_create(
            city__iexact=city,
            country__iexact=country,
            defaults={
                'name': f"{city}, {country}",
                'city': city,
                'country': country,
                'location_type': BaseLocation.LocationType.CITY,
                'local_language': data.get('language', ''),
                'local_culture': data.get('culture', {}),
                'climate': data.get('climate', ''),
            }
        )
        
        # Extract genre-specific data
        places = data.get('places', [])
        atmosphere_tags = []
        story_hooks = []
        sensory_details = {}
        
        for place in places:
            if isinstance(place, dict):
                if place.get('atmosphere'):
                    if isinstance(place['atmosphere'], list):
                        atmosphere_tags.extend(place['atmosphere'])
                    else:
                        atmosphere_tags.append(place['atmosphere'])
                
                if place.get('story_potential'):
                    story_hooks.append({
                        'place': place.get('name', 'Unknown'),
                        'hook': place['story_potential'],
                    })
                
                if place.get('sensory'):
                    sensory_details[place.get('name', 'general')] = place['sensory']
        
        # Deduplicate atmosphere tags
        atmosphere_tags = list(set(atmosphere_tags))
        
        # Create or update LocationLayer
        location_layer, created = LocationLayer.objects.update_or_create(
            base_location=base_location,
            genre=genre,
            defaults={
                'atmosphere_tags': atmosphere_tags,
                'story_hooks': story_hooks,
                'sensory_details': sensory_details,
                'points_of_interest': [
                    {'name': p.get('name'), 'type': p.get('type', 'poi')}
                    for p in places if isinstance(p, dict)
                ],
            }
        )
        
        return LocationResult(
            success=True,
            base_location=base_location,
            location_layer=location_layer,
        )
    
    def refresh_location(self, city: str, country: str, genre: str) -> LocationResult:
        """
        Force refresh location data (ignores cache).
        
        Useful when data might be outdated or user requests refresh.
        """
        # Invalidate cache
        LocationCache.invalidate(city, country, genre)
        
        # Generate fresh
        return self._generate_new(city, country, genre)
