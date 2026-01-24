"""
User Model - Custom User with Profile
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User Model for Travel Beat.
    Uses email as primary identifier.
    """
    
    class SubscriptionTier(models.TextChoices):
        FREE = 'free', 'Free'
        PREMIUM = 'premium', 'Premium'
        UNLIMITED = 'unlimited', 'Unlimited'
    
    email = models.EmailField('Email', unique=True)
    
    # Profile
    display_name = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # Subscription (for future payment integration)
    subscription_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
    )
    subscription_expires = models.DateTimeField(null=True, blank=True)
    
    # Reading preferences
    reading_speed = models.CharField(
        max_length=20,
        choices=[
            ('slow', 'Langsam (200 WpM)'),
            ('normal', 'Normal (250 WpM)'),
            ('fast', 'Schnell (300 WpM)'),
        ],
        default='normal',
    )
    preferred_genre = models.CharField(max_length=50, blank=True)
    
    # Stats
    stories_generated = models.PositiveIntegerField(default=0)
    total_words_read = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.display_name or self.email
    
    @property
    def can_generate_story(self) -> bool:
        """Check if user can generate more stories based on tier."""
        from django.conf import settings
        
        features = settings.TRAVEL_BEAT_FEATURES
        
        if self.subscription_tier == self.SubscriptionTier.UNLIMITED:
            return True
        
        if self.subscription_tier == self.SubscriptionTier.PREMIUM:
            max_stories = features.get('MAX_STORIES_PREMIUM', 50)
        else:
            max_stories = features.get('MAX_STORIES_FREE', 3)
        
        return self.stories_generated < max_stories
    
    @property
    def stories_remaining(self) -> int:
        """Get number of stories remaining."""
        from django.conf import settings
        
        features = settings.TRAVEL_BEAT_FEATURES
        
        if self.subscription_tier == self.SubscriptionTier.UNLIMITED:
            return 999
        
        if self.subscription_tier == self.SubscriptionTier.PREMIUM:
            max_stories = features.get('MAX_STORIES_PREMIUM', 50)
        else:
            max_stories = features.get('MAX_STORIES_FREE', 3)
        
        return max(0, max_stories - self.stories_generated)
