from django.contrib.auth.models import User
from django.db import models


class Customer(models.Model):
    """Medical Translation Customer"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medtrans_customers")
    customer_id = models.CharField(
        max_length=100, unique=True, help_text="Unique customer identifier (e.g., MEDTECH_DE)"
    )
    customer_name = models.CharField(max_length=200, help_text="Customer display name")
    dashboard_access = models.BooleanField(default=True, help_text="Allow dashboard access")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "medtrans_customers"
        ordering = ["-created_at"]
        verbose_name = "Medical Translation Customer"
        verbose_name_plural = "Medical Translation Customers"

    def __str__(self):
        return f"{self.customer_name} ({self.customer_id})"


class Presentation(models.Model):
    """PowerPoint Presentation for Translation"""

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("extracting", "Extracting Texts"),
        ("translating", "Translating"),
        ("reviewing", "In Review"),
        ("completed", "Completed"),
    ]

    LANGUAGE_CHOICES = [
        ("de", "German"),
        ("en", "English"),
        ("fr", "French"),
        ("es", "Spanish"),
        ("it", "Italian"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="presentations")
    pptx_file = models.FileField(
        upload_to="medtrans/presentations/", help_text="PowerPoint file to translate"
    )
    source_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="de")
    target_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="en")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")

    # Progress tracking (like in MedTemp1)
    total_texts = models.IntegerField(default=0, help_text="Total number of extracted texts")
    translated_texts = models.IntegerField(default=0, help_text="Number of translated texts")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "medtrans_presentations"
        ordering = ["-created_at"]
        verbose_name = "Presentation"
        verbose_name_plural = "Presentations"

    def __str__(self):
        return f"{self.pptx_file.name} ({self.source_language} → {self.target_language})"

    @property
    def progress_percentage(self):
        """Calculate translation progress"""
        if self.total_texts == 0:
            return 0
        return int((self.translated_texts / self.total_texts) * 100)

    @property
    def filename(self):
        """Get filename without path"""
        import os

        return os.path.basename(self.pptx_file.name) if self.pptx_file else "No file"


class PresentationText(models.Model):
    """Individual text element from presentation (for editing)"""

    TRANSLATION_METHOD_CHOICES = [
        ("pending", "Pending"),
        ("deepl", "DeepL"),
        ("manual", "Manual"),
        ("error", "Error"),
    ]

    presentation = models.ForeignKey(
        Presentation, on_delete=models.CASCADE, related_name="texts"
    )
    slide_number = models.IntegerField(help_text="Slide number in presentation")
    text_id = models.CharField(
        max_length=100, help_text="Unique text identifier (e.g., slide_1_text_3)"
    )
    original_text = models.TextField(help_text="Original text from PowerPoint")
    translated_text = models.TextField(blank=True, help_text="Translated text")
    translation_method = models.CharField(
        max_length=20, choices=TRANSLATION_METHOD_CHOICES, default="pending"
    )
    manually_edited = models.BooleanField(default=False, help_text="Was manually edited")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "medtrans_presentation_texts"
        ordering = ["presentation", "slide_number", "text_id"]
        unique_together = [["presentation", "text_id"]]
        verbose_name = "Presentation Text"
        verbose_name_plural = "Presentation Texts"
        indexes = [
            models.Index(fields=["presentation", "slide_number"]),
            models.Index(fields=["presentation", "translation_method"]),
        ]

    def __str__(self):
        return f"{self.text_id}: {self.original_text[:50]}"
