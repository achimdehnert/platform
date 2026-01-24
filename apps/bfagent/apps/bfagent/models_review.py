"""
Review System Models
Collaborative Beta-Reader & Feedback Management
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class ReviewRound(models.Model):
    """Review-Runde für ein Buch"""

    # Zuordnung
    project = models.ForeignKey(
        'BookProjects',
        on_delete=models.CASCADE,
        related_name='review_rounds'
    )

    # Basic Info
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Timeline
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Settings
    allow_comments = models.BooleanField(default=True)
    allow_ratings = models.BooleanField(default=True)
    comments_visible_to_others = models.BooleanField(default=True)

    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_review_rounds'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Denormalized stats (for performance)
    total_comments = models.IntegerField(default=0)
    unread_comments = models.IntegerField(default=0)
    total_participants = models.IntegerField(default=0)
    total_ratings = models.IntegerField(default=0)
    average_rating = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review Round'
        verbose_name_plural = 'Review Rounds'

    def __str__(self):
        return f"{self.title} - {self.project.title}"

    def get_progress(self):
        """Calculate review round progress"""
        if self.total_participants == 0:
            return 0

        active_participants = self.participants.filter(status='active').count()
        completed_participants = self.participants.filter(
            status='active',
            last_activity_at__isnull=False
        ).count()

        if active_participants == 0:
            return 0

        return int((completed_participants / active_participants) * 100)

    def update_stats(self):
        """Update denormalized statistics"""
        self.total_comments = self.comments.count()
        self.unread_comments = self.comments.filter(
            status='open',
            author_reply=''
        ).count()
        self.total_participants = self.participants.count()
        self.total_ratings = ChapterRating.objects.filter(
            review_round=self
        ).count()

        # Calculate average rating
        avg = ChapterRating.objects.filter(
            review_round=self
        ).aggregate(models.Avg('overall_rating'))
        self.average_rating = avg['overall_rating__avg']

        self.save()


class ReviewParticipant(models.Model):
    """Teilnehmer einer Review-Runde"""

    # Zuordnung
    review_round = models.ForeignKey(
        ReviewRound,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_participations'
    )

    # Role
    ROLE_CHOICES = [
        ('author', 'Author'),
        ('reader', 'Beta-Reader'),
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='reader'
    )

    # Permissions
    can_comment = models.BooleanField(default=True)
    can_rate = models.BooleanField(default=True)
    can_see_other_comments = models.BooleanField(default=True)

    # Status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Activity Tracking
    joined_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    # Stats
    comments_count = models.IntegerField(default=0)
    ratings_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ['review_round', 'user']
        ordering = ['-joined_at']
        verbose_name = 'Review Participant'
        verbose_name_plural = 'Review Participants'

    def __str__(self):
        return f"{self.user.username} - {self.review_round.title} ({self.role})"

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])

    def update_stats(self):
        """Update participation statistics"""
        self.comments_count = Comment.objects.filter(
            review_round=self.review_round,
            author=self.user
        ).count()

        self.ratings_count = ChapterRating.objects.filter(
            review_round=self.review_round,
            reviewer=self.user
        ).count()

        self.save(update_fields=['comments_count', 'ratings_count'])


class Comment(models.Model):
    """Kommentar zu einem Kapitel"""

    # Zuordnung
    review_round = models.ForeignKey(
        ReviewRound,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    chapter = models.ForeignKey(
        'BookChapters',
        on_delete=models.CASCADE,
        related_name='review_comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authored_comments'
    )

    # Content
    text = models.TextField()

    # Type
    TYPE_CHOICES = [
        ('general', 'General Comment'),
        ('suggestion', 'Suggestion'),
        ('question', 'Question'),
        ('praise', 'Praise'),
        ('concern', 'Concern'),
        ('typo', 'Typo/Grammar'),
    ]
    comment_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='general'
    )

    # Status
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('acknowledged', 'Acknowledged'),
        ('addressed', 'Addressed'),
        ('resolved', 'Resolved'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open'
    )

    # Author Response
    author_reply = models.TextField(blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_comments'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    # Helpful votes (optional)
    helpful_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['chapter__chapter_number', 'created_at']
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'

    def __str__(self):
        return f"Comment by {self.author.username} on {self.chapter.title}"

    def mark_as_resolved(self, user, reply=''):
        """Mark comment as resolved"""
        self.status = 'resolved'
        self.resolved_by = user
        self.resolved_at = timezone.now()

        if reply:
            self.author_reply = reply
            self.replied_at = timezone.now()

        self.save()

        # Update review round stats
        self.review_round.update_stats()

    def add_reply(self, reply_text, user):
        """Add author reply to comment"""
        self.author_reply = reply_text
        self.replied_at = timezone.now()

        if self.status == 'open':
            self.status = 'acknowledged'

        self.save()

        # Update review round stats
        self.review_round.update_stats()


class ChapterRating(models.Model):
    """Bewertung eines Kapitels"""

    # Zuordnung
    review_round = models.ForeignKey(
        ReviewRound,
        on_delete=models.CASCADE,
        related_name='chapter_ratings'
    )
    chapter = models.ForeignKey(
        'BookChapters',
        on_delete=models.CASCADE,
        related_name='review_ratings'
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chapter_ratings'
    )

    # Rating (1-5 stars)
    overall_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Rate from 1 (poor) to 5 (excellent)'
    )

    # Optional Feedback
    feedback_text = models.TextField(
        blank=True,
        help_text='Optional: Explain your rating'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['review_round', 'chapter', 'reviewer']
        ordering = ['chapter__chapter_number']
        verbose_name = 'Chapter Rating'
        verbose_name_plural = 'Chapter Ratings'

    def __str__(self):
        return f"{self.reviewer.username}: {self.overall_rating}★ for {self.chapter.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update review round stats
        self.review_round.update_stats()

        # Update participant stats
        try:
            participant = ReviewParticipant.objects.get(
                review_round=self.review_round,
                user=self.reviewer
            )
            participant.update_stats()
            participant.update_activity()
        except ReviewParticipant.DoesNotExist:
            pass
