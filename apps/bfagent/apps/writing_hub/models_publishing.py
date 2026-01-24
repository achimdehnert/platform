"""
Publishing Models for E-Book/EPUB Publication

Contains metadata, cover, and front/backmatter definitions needed for
professional e-book publishing on platforms like Amazon KDP, Apple Books, etc.
"""

from django.db import models
from django.core.validators import RegexValidator


class PublishingMetadata(models.Model):
    """
    Publishing metadata required for e-book stores.
    One-to-one relationship with BookProjects.
    """
    
    class PublishingStatus(models.TextChoices):
        DRAFT = 'draft', '📝 Entwurf'
        READY = 'ready', '✅ Bereit zur Publikation'
        PUBLISHED = 'published', '📚 Veröffentlicht'
        ARCHIVED = 'archived', '📦 Archiviert'
    
    class ContentRating(models.TextChoices):
        GENERAL = 'general', '👨‍👩‍👧 Allgemein (ab 0)'
        TEEN = 'teen', '🧒 Jugendliche (ab 12)'
        YOUNG_ADULT = 'young_adult', '👤 Junge Erwachsene (ab 16)'
        ADULT = 'adult', '🔞 Erwachsene (ab 18)'
    
    project = models.OneToOneField(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='publishing_metadata'
    )
    
    # Identifiers
    isbn = models.CharField(
        max_length=17,
        blank=True,
        validators=[RegexValidator(
            regex=r'^(?:\d{10}|\d{13}|978-\d-\d{2}-\d{6}-\d)$',
            message='Ungültige ISBN (10 oder 13 Ziffern)'
        )],
        help_text="ISBN-10 oder ISBN-13"
    )
    asin = models.CharField(
        max_length=10,
        blank=True,
        help_text="Amazon Standard Identification Number"
    )
    
    # Publisher Info
    publisher_name = models.CharField(
        max_length=200,
        blank=True,
        default="Selbstverlag",
        help_text="Verlagsname"
    )
    imprint = models.CharField(
        max_length=200,
        blank=True,
        help_text="Impressum/Imprint"
    )
    
    # Copyright
    copyright_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Copyright-Jahr"
    )
    copyright_holder = models.CharField(
        max_length=200,
        blank=True,
        help_text="Copyright-Inhaber (Name des Autors)"
    )
    all_rights_reserved = models.BooleanField(
        default=True,
        help_text="Alle Rechte vorbehalten"
    )
    
    # Language
    language = models.CharField(
        max_length=5,
        default='de',
        help_text="Sprache (ISO 639-1, z.B. 'de', 'en')"
    )
    
    # Categories (BISAC)
    primary_bisac = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primäre BISAC-Kategorie (z.B. 'FIC009000')"
    )
    secondary_bisac = models.CharField(
        max_length=100,
        blank=True,
        help_text="Sekundäre BISAC-Kategorie"
    )
    
    # Keywords for discoverability
    keywords = models.TextField(
        blank=True,
        help_text="Komma-getrennte Keywords für Suchmaschinen (max. 7)"
    )
    
    # Content rating
    content_rating = models.CharField(
        max_length=20,
        choices=ContentRating.choices,
        default=ContentRating.GENERAL
    )
    
    # Publication dates
    first_published = models.DateField(
        null=True,
        blank=True,
        help_text="Erstveröffentlichung"
    )
    this_edition = models.DateField(
        null=True,
        blank=True,
        help_text="Diese Ausgabe"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=PublishingStatus.choices,
        default=PublishingStatus.DRAFT
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_publishing_metadata'
        verbose_name = 'Publishing-Metadaten'
        verbose_name_plural = 'Publishing-Metadaten'
    
    def __str__(self):
        return f"Publishing: {self.project.title}"
    
    def get_keywords_list(self):
        """Return keywords as list"""
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(',')]


class BookCover(models.Model):
    """
    Book cover images for different platforms.
    """
    
    class CoverType(models.TextChoices):
        EBOOK = 'ebook', '📱 E-Book Cover'
        PRINT = 'print', '📖 Print Cover'
        AUDIOBOOK = 'audiobook', '🎧 Hörbuch Cover'
        SOCIAL = 'social', '📣 Social Media'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='covers'
    )
    
    cover_type = models.CharField(
        max_length=20,
        choices=CoverType.choices,
        default=CoverType.EBOOK
    )
    
    # Image
    image = models.ImageField(
        upload_to='book_covers/',
        help_text="Cover-Bild (min. 1600x2560 für E-Book)"
    )
    
    # AI Generation
    prompt_used = models.TextField(
        blank=True,
        help_text="KI-Prompt für Generierung"
    )
    is_ai_generated = models.BooleanField(
        default=False
    )
    
    # Dimensions
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Status
    is_primary = models.BooleanField(
        default=False,
        help_text="Haupt-Cover für diese Art"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_book_covers'
        verbose_name = 'Buchcover'
        verbose_name_plural = 'Buchcover'
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        return f"{self.project.title} - {self.get_cover_type_display()}"


class FrontMatter(models.Model):
    """
    Front matter pages (before main content).
    """
    
    class PageType(models.TextChoices):
        HALF_TITLE = 'half_title', '📄 Schmutztitel'
        TITLE = 'title', '📖 Titelseite'
        COPYRIGHT = 'copyright', '©️ Impressum'
        DEDICATION = 'dedication', '💝 Widmung'
        EPIGRAPH = 'epigraph', '✨ Motto/Zitat'
        TOC = 'toc', '📑 Inhaltsverzeichnis'
        FOREWORD = 'foreword', '📝 Vorwort'
        PREFACE = 'preface', '📋 Einleitung'
        ACKNOWLEDGMENTS = 'acknowledgments', '🙏 Danksagung'
        PROLOGUE = 'prologue', '🎬 Prolog'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='front_matter'
    )
    
    page_type = models.CharField(
        max_length=20,
        choices=PageType.choices
    )
    
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Seitentitel (optional)"
    )
    
    content = models.TextField(
        blank=True,
        help_text="Seiteninhalt (Markdown)"
    )
    
    # For auto-generation
    auto_generate = models.BooleanField(
        default=True,
        help_text="Automatisch aus Metadaten generieren"
    )
    
    # Display order
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_front_matter'
        verbose_name = 'Frontmatter'
        verbose_name_plural = 'Frontmatter'
        ordering = ['sort_order']
        unique_together = ['project', 'page_type']
    
    def __str__(self):
        return f"{self.project.title} - {self.get_page_type_display()}"


class BackMatter(models.Model):
    """
    Back matter pages (after main content).
    """
    
    class PageType(models.TextChoices):
        EPILOGUE = 'epilogue', '🎭 Epilog'
        AFTERWORD = 'afterword', '📝 Nachwort'
        APPENDIX = 'appendix', '📎 Anhang'
        GLOSSARY = 'glossary', '📖 Glossar'
        BIBLIOGRAPHY = 'bibliography', '📚 Literaturverzeichnis'
        INDEX = 'index', '🔍 Index'
        ABOUT_AUTHOR = 'about_author', '👤 Über den Autor'
        ALSO_BY = 'also_by', '📚 Weitere Bücher'
        ACKNOWLEDGMENTS = 'acknowledgments', '🙏 Danksagung'
        COLOPHON = 'colophon', '🖨️ Kolophon'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='back_matter'
    )
    
    page_type = models.CharField(
        max_length=20,
        choices=PageType.choices
    )
    
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Seitentitel (optional)"
    )
    
    content = models.TextField(
        blank=True,
        help_text="Seiteninhalt (Markdown)"
    )
    
    # For auto-generation
    auto_generate = models.BooleanField(
        default=False,
        help_text="Automatisch generieren"
    )
    
    # Display order
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_back_matter'
        verbose_name = 'Backmatter'
        verbose_name_plural = 'Backmatter'
        ordering = ['sort_order']
        unique_together = ['project', 'page_type']
    
    def __str__(self):
        return f"{self.project.title} - {self.get_page_type_display()}"


class AuthorProfile(models.Model):
    """
    Author profile for "About the Author" section.
    Reusable across multiple projects.
    """
    
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='author_profile'
    )
    
    # Display name
    pen_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Pseudonym / Künstlername"
    )
    
    # Bio
    bio_short = models.TextField(
        blank=True,
        help_text="Kurze Bio (1-2 Sätze)"
    )
    bio_long = models.TextField(
        blank=True,
        help_text="Ausführliche Bio"
    )
    
    # Photo
    photo = models.ImageField(
        upload_to='author_photos/',
        null=True,
        blank=True
    )
    
    # Social Media / Contact
    website = models.URLField(blank=True)
    email_public = models.EmailField(blank=True)
    twitter = models.CharField(max_length=50, blank=True)
    instagram = models.CharField(max_length=50, blank=True)
    facebook = models.CharField(max_length=100, blank=True)
    goodreads = models.URLField(blank=True)
    amazon_author_page = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_author_profiles'
        verbose_name = 'Autorenprofil'
        verbose_name_plural = 'Autorenprofile'
    
    def __str__(self):
        return self.pen_name or self.user.get_full_name() or self.user.username
    
    def get_display_name(self):
        """Get the name to display in the book"""
        return self.pen_name or self.user.get_full_name() or self.user.username
