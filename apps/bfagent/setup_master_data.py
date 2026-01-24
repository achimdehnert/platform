#!/usr/bin/env python
"""Setup Master Data for Project 3"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import TargetAudience, BookProjects, Characters

print("=" * 80)
print("📊 SETTING UP MASTER DATA & PROJECT 3")
print("=" * 80)

# 1. Create Target Audiences
print("\n✅ CREATING TARGET AUDIENCES...")
audiences = [
    {"name": "Children", "age_range": "6-12", "sort_order": 1},
    {"name": "Young Adult", "age_range": "13-18", "sort_order": 2},
    {"name": "New Adult", "age_range": "18-25", "sort_order": 3},
    {"name": "Adult", "age_range": "18+", "sort_order": 4},
    {"name": "All Ages", "age_range": "", "sort_order": 5},
]

for aud_data in audiences:
    aud, created = TargetAudience.objects.get_or_create(
        name=aud_data["name"],
        defaults={
            "age_range": aud_data["age_range"],
            "sort_order": aud_data["sort_order"],
            "is_active": True,
        }
    )
    status = "Created" if created else "Exists"
    print(f"   {status}: {aud}")

print(f"\n✅ Total Target Audiences: {TargetAudience.objects.count()}")

# 2. Update Project 3
print("\n✅ UPDATING PROJECT 3...")
project = BookProjects.objects.get(id=3)

# Update fields
project.target_audience = "Adult (18+)"
project.story_themes = "Love across social classes, Family expectations, Social barriers, Personal growth"
project.setting_time = "Contemporary (2020s)"
project.setting_location = "Germany, fictional town"
project.atmosphere_tone = "Romantic, emotional, hopeful with realistic challenges"
project.save()

print(f"   Title: {project.title}")
print(f"   Target Audience: {project.target_audience}")
print(f"   Themes: {project.story_themes}")
print(f"   Setting: {project.setting_time} / {project.setting_location}")
print(f"   Tone: {project.atmosphere_tone}")

# 3. Create Characters
print("\n✅ CREATING CHARACTERS...")

# Hugo (Protagonist)
hugo, created = Characters.objects.get_or_create(
    project_id=3,
    name="Hugo",
    defaults={
        "role": "protagonist",
        "age": 28,
        "description": "A kind-hearted, hardworking young man from a poor background who works multiple jobs to support himself.",
        "personality": "Warm, genuine, optimistic despite hardships, deeply romantic, believes in love conquering all obstacles",
        "background": "Grew up in a working-class family, lost his parents young, had to work from a young age. Dreams of a better life but never loses his humanity.",
        "motivation": "To prove that love and character matter more than wealth and status. To win Luise's heart and build a life together.",
        "conflict": "Social class differences, lack of financial means, opposition from Luise's wealthy family",
        "arc": "Learns that true love requires not just passion but courage to stand up for what he believes in, even against societal pressure",
    }
)
status = "Created" if created else "Updated"
print(f"   {status}: {hugo.name} ({hugo.role})")

# Luise (Love Interest / Secondary Protagonist)
luise, created = Characters.objects.get_or_create(
    project_id=3,
    name="Luise",
    defaults={
        "role": "deuteragonist",
        "age": 25,
        "description": "A beautiful, intelligent young woman from a wealthy family who feels trapped by her privileged life.",
        "personality": "Cultured, independent-minded, yearning for authenticity, torn between duty and desire",
        "background": "Daughter of a successful businessman, raised with every privilege but feels emotionally empty. Expected to marry within her social circle.",
        "motivation": "To find real love and meaning beyond material wealth. To break free from family expectations.",
        "conflict": "Family pressure, fear of losing her inheritance and security, society's judgment",
        "arc": "Discovers her own strength and learns that happiness comes from following her heart, not societal expectations",
    }
)
status = "Created" if created else "Updated"
print(f"   {status}: {luise.name} ({luise.role})")

# Luise's Father (Antagonist)
father, created = Characters.objects.get_or_create(
    project_id=3,
    name="Herr Richter",
    defaults={
        "role": "antagonist",
        "age": 58,
        "description": "Luise's stern, traditional father who built his wealth from nothing and is obsessed with maintaining status.",
        "personality": "Authoritarian, pragmatic, protective but controlling, believes money and status ensure security",
        "background": "Self-made businessman who clawed his way up from poverty. Determined his daughter won't suffer as he did.",
        "motivation": "To protect his daughter from what he sees as the misery of poverty. To secure her future through a 'proper' marriage.",
        "conflict": "Sees Hugo as a threat to Luise's security and the family's reputation",
        "arc": "May eventually realize that he's projecting his own fears onto Luise and that true security comes from love",
    }
)
status = "Created" if created else "Updated"
print(f"   {status}: {father.name} ({father.role})")

print(f"\n✅ Total Characters for Project 3: {Characters.objects.filter(project_id=3).count()}")

print("\n" + "=" * 80)
print("✅ SETUP COMPLETE!")
print("=" * 80)
print("\n📝 NEXT STEP: Run test command")
print("   python manage.py test_handler_enrichment --project-id 3 --chapter-number 1")
