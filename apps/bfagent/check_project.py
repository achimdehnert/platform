#!/usr/bin/env python
"""Quick check of Project 3 data for testing"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import BookProjects, Characters

print("=" * 80)
print("📊 PROJECT 3 DATA CHECK")
print("=" * 80)

# Get project
project = BookProjects.objects.get(id=3)

print(f"\n✅ PROJECT BASICS:")
print(f"   Title: {project.title}")
print(f"   Genre: {project.genre}")
print(f"   Target Audience: {project.target_audience or 'Not set'}")

print(f"\n✅ STORY DATA:")
print(f"   Premise Length: {len(project.story_premise) if project.story_premise else 0} chars")
print(f"   Has Beat Sheet: {'Yes' if project.story_premise and 'Chapter 1:' in project.story_premise else 'No'}")
print(f"   Themes: {project.story_themes or 'Not set'}")

print(f"\n✅ SETTING:")
print(f"   Time: {project.setting_time or 'Not set'}")
print(f"   Location: {project.setting_location or 'Not set'}")
print(f"   Tone: {project.atmosphere_tone or 'Not set'}")

# Check characters
chars = Characters.objects.filter(project_id=3)
print(f"\n✅ CHARACTERS: {chars.count()} total")
for char in chars:
    print(f"   - {char.name}: {char.role or 'no role'}")

# Check if premise contains beats
if project.story_premise:
    beat_count = project.story_premise.count('## Chapter')
    print(f"\n✅ BEAT SHEET:")
    print(f"   Chapters defined: {beat_count}")
    
print("\n" + "=" * 80)
print("✅ DATA CHECK COMPLETE!")
print("=" * 80)
