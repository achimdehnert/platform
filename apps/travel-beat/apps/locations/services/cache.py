"""
Location Cache - Manages research cache with TTL
"""

import json
import hashlib
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from django.db import models

from apps.locations.models import ResearchCache


class LocationCache:
    """
    Manages cached location research data.
    
    Uses ResearchCache model with TTL to avoid repeated LLM calls
    for the same location/genre combinations.
    """
    
    DEFAULT_TTL_DAYS = 30
    
    @classmethod
    def get_cache_key(cls, city: str, country: str, genre: str) -> str:
        """Generate cache key for location research."""
        raw = f"{city.lower()}|{country.lower()}|{genre.lower()}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    @classmethod
    def get(cls, city: str, country: str, genre: str) -> Optional[dict]:
        """
        Get cached location data if available and not expired.
        
        Returns None if cache miss or expired.
        """
        cache_key = cls.get_cache_key(city, country, genre)
        
        try:
            cache_entry = ResearchCache.objects.get(cache_key=cache_key)
            
            # Check if expired
            if cache_entry.is_expired:
                cache_entry.delete()
                return None
            
            # Update access stats
            cache_entry.access_count += 1
            cache_entry.last_accessed = timezone.now()
            cache_entry.save(update_fields=['access_count', 'last_accessed'])
            
            return cache_entry.raw_data
            
        except ResearchCache.DoesNotExist:
            return None
    
    @classmethod
    def set(
        cls,
        city: str,
        country: str,
        genre: str,
        data: dict,
        source: str = 'llm',
        ttl_days: int = None,
    ) -> ResearchCache:
        """
        Store location data in cache.
        
        Args:
            city: City name
            country: Country name
            genre: Story genre
            data: Research data to cache
            source: Data source ('llm', 'manual', 'api')
            ttl_days: Time to live in days (default: 30)
        """
        cache_key = cls.get_cache_key(city, country, genre)
        ttl = ttl_days or cls.DEFAULT_TTL_DAYS
        expires = timezone.now() + timedelta(days=ttl)
        
        cache_entry, created = ResearchCache.objects.update_or_create(
            cache_key=cache_key,
            defaults={
                'query_city': city,
                'query_country': country,
                'query_genre': genre,
                'raw_data': data,
                'source': source,
                'expires_at': expires,
                'access_count': 1 if created else ResearchCache.objects.get(cache_key=cache_key).access_count + 1,
                'last_accessed': timezone.now(),
            }
        )
        
        return cache_entry
    
    @classmethod
    def invalidate(cls, city: str, country: str, genre: str = None) -> int:
        """
        Invalidate cache entries.
        
        If genre is None, invalidates all genres for the city/country.
        Returns number of entries deleted.
        """
        if genre:
            cache_key = cls.get_cache_key(city, country, genre)
            deleted, _ = ResearchCache.objects.filter(cache_key=cache_key).delete()
        else:
            deleted, _ = ResearchCache.objects.filter(
                query_city__iexact=city,
                query_country__iexact=country,
            ).delete()
        
        return deleted
    
    @classmethod
    def cleanup_expired(cls) -> int:
        """Remove all expired cache entries. Returns count deleted."""
        deleted, _ = ResearchCache.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()
        return deleted
    
    @classmethod
    def get_stats(cls) -> dict:
        """Get cache statistics."""
        total = ResearchCache.objects.count()
        expired = ResearchCache.objects.filter(expires_at__lt=timezone.now()).count()
        by_genre = {}
        
        for entry in ResearchCache.objects.values('query_genre').annotate(
            count=models.Count('id')
        ):
            by_genre[entry['query_genre']] = entry['count']
        
        return {
            'total_entries': total,
            'expired_entries': expired,
            'active_entries': total - expired,
            'by_genre': by_genre,
        }
