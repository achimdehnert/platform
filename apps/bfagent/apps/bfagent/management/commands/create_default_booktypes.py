"""
Django Management Command to create default BookTypes
Provides standard book types for the system
"""

from django.core.management.base import BaseCommand

from apps.bfagent.models import BookTypes


class Command(BaseCommand):
    help = "Create default BookTypes for the system"

    def handle(self, *args, **options):
        default_book_types = [
            {
                "name": "Novel",
                "description": "Full-length fiction work, typically 80,000+ words",
                "complexity": "intermediate",
                "estimated_duration_hours": 500,
                "target_word_count_min": 80000,
                "target_word_count_max": 120000,
                "is_active": True,
            },
            {
                "name": "Novella",
                "description": "Medium-length fiction work, typically 17,500-40,000 words",
                "complexity": "beginner",
                "estimated_duration_hours": 150,
                "target_word_count_min": 17500,
                "target_word_count_max": 40000,
                "is_active": True,
            },
            {
                "name": "Short Story",
                "description": "Brief fiction work, typically under 7,500 words",
                "complexity": "beginner",
                "estimated_duration_hours": 20,
                "target_word_count_min": 1000,
                "target_word_count_max": 7500,
                "is_active": True,
            },
            {
                "name": "Non-Fiction Book",
                "description": "Factual book covering real topics and information",
                "complexity": "intermediate",
                "estimated_duration_hours": 400,
                "target_word_count_min": 50000,
                "target_word_count_max": 80000,
                "is_active": True,
            },
            {
                "name": "Poetry Collection",
                "description": "Collection of poems organized by theme or style",
                "complexity": "advanced",
                "estimated_duration_hours": 100,
                "target_word_count_min": 5000,
                "target_word_count_max": 15000,
                "is_active": True,
            },
            {
                "name": "Memoir",
                "description": "Personal account of specific life experiences",
                "complexity": "intermediate",
                "estimated_duration_hours": 300,
                "target_word_count_min": 60000,
                "target_word_count_max": 90000,
                "is_active": True,
            },
            {
                "name": "Children's Book",
                "description": "Book written specifically for young readers",
                "complexity": "beginner",
                "estimated_duration_hours": 50,
                "target_word_count_min": 500,
                "target_word_count_max": 3000,
                "is_active": True,
            },
            {
                "name": "Young Adult",
                "description": "Fiction targeted at teenage readers",
                "complexity": "intermediate",
                "estimated_duration_hours": 400,
                "target_word_count_min": 70000,
                "target_word_count_max": 100000,
                "is_active": True,
            },
        ]

        created_count = 0
        updated_count = 0

        for book_type_data in default_book_types:
            book_type, created = BookTypes.objects.get_or_create(
                name=book_type_data["name"], defaults=book_type_data
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created: {book_type.name}"))
            else:
                # Update existing if needed
                updated = False
                for field, value in book_type_data.items():
                    if getattr(book_type, field) != value:
                        setattr(book_type, field, value)
                        updated = True

                if updated:
                    book_type.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"🔄 Updated: {book_type.name}"))
                else:
                    self.stdout.write(self.style.NOTICE(f"ℹ️  Exists: {book_type.name}"))

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                "📚 BookTypes Summary:\n"
                f"   Created: {created_count}\n"
                f"   Updated: {updated_count}\n"
                f"   Total: {BookTypes.objects.count()}"
            )
        )

        if created_count > 0 or updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS("\n🎉 BookType dropdown will now be populated dynamically!")
            )
