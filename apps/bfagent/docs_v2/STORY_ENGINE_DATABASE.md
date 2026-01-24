# Story Engine - Database Schema

> **Focus**: Django Models, Database Design, Data Relationships  
> **Status**: Planning  
> **Updated**: 2024-11-07

---

## 📊 Core Models

### StoryBible
**Primary story universe document**

```python
class StoryBible(models.Model):
    # Basic Info
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    genre = models.CharField(max_length=100)
    target_word_count = models.IntegerField(default=80000)
    
    # Structured World Building
    scientific_concepts = models.JSONField(default=dict)
    world_rules = models.JSONField(default=list)
    technology_levels = models.JSONField(default=dict)
    
    # Timeline
    timeline = models.JSONField(default=list)
    timeline_start_year = models.IntegerField(null=True)
    timeline_end_year = models.IntegerField(null=True)
    
    # Style Guide
    prose_style = models.TextField()
    tone = models.CharField(max_length=100)
    pacing_profile = models.JSONField(default=dict)
    
    # Status
    status = models.CharField(max_length=20, default='planning')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Example Data:**
```json
{
  "title": "Superintelligenz: Die Transformation",
  "scientific_concepts": {
    "si_emergence": "Gradual cognitive enhancement via BCIs",
    "consciousness_transfer": "Limited, only memories not identity"
  },
  "world_rules": [
    {"rule": "No time travel", "established_in": "Chapter 1"},
    {"rule": "SI can't control humans directly", "established_in": "Chapter 3"}
  ],
  "timeline": [
    {"year": 2045, "event": "First successful BCI enhancement"},
    {"year": 2047, "event": "SI community emerges"}
  ]
}
```

---

### StoryStrand
**Individual story threads**

```python
class StoryStrand(models.Model):
    story_bible = models.ForeignKey(StoryBible, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # "Das Erwachen"
    order = models.IntegerField()  # 1-6
    
    focus = models.CharField(max_length=200)
    genre_weights = models.JSONField(default=dict)
    core_theme = models.TextField()
    
    primary_character = models.ForeignKey('Character', null=True)
    starts_in_book = models.IntegerField()
    ends_in_book = models.IntegerField()
```

**Example:**
```python
StoryStrand.objects.create(
    name="Das Erwachen",
    order=1,
    focus="Individual transformation",
    genre_weights={"thriller": 70, "philosophy": 30},
    core_theme="First signs of SI in individual",
    starts_in_book=1,
    ends_in_book=2
)
```

---

### Character
**Story characters with structured attributes**

```python
class Character(models.Model):
    story_bible = models.ForeignKey(StoryBible, on_delete=models.CASCADE)
    
    # Basic
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200)
    age = models.IntegerField(null=True)
    
    # Structured Attributes
    physical_traits = models.JSONField(default=dict)
    personality_traits = models.JSONField(default=list)
    skills = models.JSONField(default=list)
    
    # Relationships
    relationships = models.JSONField(default=dict)
    
    # Full descriptions (for Vector Store)
    biography = models.TextField()
    psychological_profile = models.TextField()
    
    # Arc Tracking
    character_arc = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Example:**
```python
Character.objects.create(
    name="Dr. Sarah Chen",
    age=34,
    physical_traits={
        "height": 165,
        "hair": "black",
        "eyes": "brown",
        "ethnicity": "Asian-American"
    },
    personality_traits=["intelligent", "cautious", "empathetic"],
    skills=["neuroscience", "programming", "meditation"],
    relationships={
        "colleague_of": [2, 5],  # Character IDs
        "mentor_to": [7]
    }
)
```

---

### Chapter
**Generated chapter content**

```python
class Chapter(models.Model):
    story_bible = models.ForeignKey(StoryBible, on_delete=models.CASCADE)
    strand = models.ForeignKey(StoryStrand, on_delete=models.CASCADE)
    
    # Chapter Info
    chapter_number = models.IntegerField()
    title = models.CharField(max_length=200)
    
    # Content
    content = models.TextField()
    summary = models.TextField()
    
    # Metadata
    word_count = models.IntegerField()
    pov_character = models.ForeignKey(Character, null=True)
    
    # Generation Metadata
    generation_method = models.CharField(max_length=50)
    quality_score = models.FloatField(null=True)
    consistency_score = models.FloatField(null=True)
    
    # Status
    status = models.CharField(max_length=20, default='draft')
    version = models.IntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

### ChapterBeat
**Plan for chapters before generation**

```python
class ChapterBeat(models.Model):
    story_bible = models.ForeignKey(StoryBible, on_delete=models.CASCADE)
    strand = models.ForeignKey(StoryStrand, on_delete=models.CASCADE)
    
    beat_number = models.IntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Story Elements
    key_events = models.JSONField(default=list)
    character_focus = models.ForeignKey(Character, null=True)
    emotional_tone = models.CharField(max_length=100)
    
    # Targets
    target_word_count = models.IntegerField(default=2000)
    tension_level = models.IntegerField(default=5)  # 1-10
    
    order = models.IntegerField()
```

---

## 🔗 Relationships

### Entity Relationship Diagram
```
StoryBible (1) ─────┬─── (N) StoryStrand
    │               │
    │               └─── (N) Chapter
    │
    └─── (N) Character
              │
              └─── (N) Chapter (as pov_character)

StoryStrand (1) ─── (N) ChapterBeat
                     │
                     └─── (0..1) Chapter (generated from beat)
```

---

## 📋 Example Queries

### Get all chapters for a story
```python
chapters = Chapter.objects.filter(
    story_bible=story_bible
).order_by('strand__order', 'chapter_number')
```

### Get character's chapters
```python
character_chapters = Chapter.objects.filter(
    pov_character=character
).select_related('strand')
```

### Get timeline events in year range
```python
story_bible = StoryBible.objects.get(id=1)
events = [e for e in story_bible.timeline 
          if 2045 <= e['year'] <= 2050]
```

### Character relationships
```python
character = Character.objects.get(name="Dr. Sarah Chen")
colleague_ids = character.relationships.get('colleague_of', [])
colleagues = Character.objects.filter(id__in=colleague_ids)
```

---

## 🔄 Optional: Vector Store Sync

**When to sync:**
- After Chapter save
- After Character update
- On demand

**What to embed:**
```python
class VectorStoreSync:
    def sync_chapter(self, chapter):
        self.vector_store.add_texts(
            texts=[chapter.content],
            metadatas=[{
                'chapter_id': chapter.id,
                'chapter_number': chapter.chapter_number,
                'strand': chapter.strand.name,
                'type': 'chapter_content'
            }]
        )
    
    def sync_character(self, character):
        self.vector_store.add_texts(
            texts=[character.biography],
            metadatas=[{
                'character_id': character.id,
                'name': character.name,
                'type': 'character_bio'
            }]
        )
```

**Remember:** Vector Store is READ-ONLY cache, DB is source of truth!

---

## 📚 See Also

- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System design
- [STORY_ENGINE_IMPLEMENTATION.md](./STORY_ENGINE_IMPLEMENTATION.md) - Implementation guide
