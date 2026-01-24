# ⚡ Quick Start: Scene Model

**Status:** ✅ IMPLEMENTED & READY!  
**Time:** 5 Minuten Setup

---

## 🚀 SETUP (3 Schritte)

### **1. Migration erstellen & ausführen:**

```bash
# Create migration
python manage.py makemigrations writing_hub

# Apply migration  
python manage.py migrate
```

**Erstellt:**
- 4 Lookup Tables (emotional_tones, conflict_levels, beat_types, scene_connection_types)
- 6 Story Element Tables (scenes, beats, locations, plot_threads, scene_connections, timeline_events)

---

### **2. Lookup Tables initialisieren:**

```bash
python manage.py init_story_lookups
```

**Output:**
```
🎭 Initializing Story Element Lookup Tables
================================================================================

📊 Initializing Emotional Tones...
  ✅ Created: Hopeful
  ✅ Created: Joyful
  ✅ Created: Peaceful
  ✅ Created: Mysterious
  ✅ Created: Tense
  ✅ Created: Fearful
  ✅ Created: Angry
  ✅ Created: Melancholic
  ✅ Created: Desperate
  ✅ Created: Triumphant

⚔️  Initializing Conflict Levels...
  ✅ Created: None (intensity: 0)
  ✅ Created: Low (intensity: 2)
  ✅ Created: Medium (intensity: 5)
  ✅ Created: High (intensity: 8)
  ✅ Created: Climax (intensity: 10)

🎬 Initializing Beat Types...
  ✅ Created: Action
  ✅ Created: Dialogue
  ✅ Created: Description
  ✅ Created: Emotion
  ✅ Created: Revelation
  ✅ Created: Decision
  ✅ Created: Conflict
  ✅ Created: Reflection

🔗 Initializing Scene Connection Types...
  ✅ Created: Foreshadowing
  ✅ Created: Callback
  ✅ Created: Parallel
  ✅ Created: Contrast
  ✅ Created: Cause & Effect
  ✅ Created: Mirror

================================================================================
✅ Done! Created: 10 emotional tones, 5 conflict levels, 8 beat types, 6 connection types
```

---

### **3. Test in Django Admin:**

```bash
python manage.py runserver
```

**Open:** http://localhost:8000/admin

**You'll see new sections:**
- Writing Hub → Emotional Tones ✅
- Writing Hub → Conflict Levels ✅
- Writing Hub → Beat Types ✅
- Writing Hub → Scene Connection Types ✅
- Writing Hub → Scenes ✅
- Writing Hub → Beats ✅
- Writing Hub → Locations ✅
- Writing Hub → Plot Threads ✅
- Writing Hub → Scene Connections ✅
- Writing Hub → Timeline Events ✅

---

## 💡 QUICK EXAMPLE

### **Create a Scene in Python:**

```python
from apps.writing_hub.models import (
    Scene, Beat, 
    EmotionalTone, ConflictLevel, BeatType
)
from apps.bfagent.models import BookProjects, BookChapters

# Get project & chapter
project = BookProjects.objects.first()
chapter = project.chapters.first()

# Get lookups
hopeful = EmotionalTone.objects.get(code='hopeful')
tense = EmotionalTone.objects.get(code='tense')
high = ConflictLevel.objects.get(code='high')

# Create scene
scene = Scene.objects.create(
    chapter=chapter,
    order=1,
    title="The Call to Adventure",
    summary="Hero discovers mysterious letter",
    
    # Emotional arc
    emotional_start=hopeful,
    emotional_end=tense,
    
    # Conflict
    conflict_level=high,
    
    # Scene method
    goal="Ignore the call and stay safe",
    disaster="Mentor forces confrontation",
    
    # Target
    word_count_target=2000
)

# Add beats
action = BeatType.objects.get(code='action')
dialogue = BeatType.objects.get(code='dialogue')

Beat.objects.create(
    scene=scene,
    order=1,
    beat_type=action,
    description="Hero walks through marketplace"
)

Beat.objects.create(
    scene=scene,
    order=2,
    beat_type=dialogue,
    description="Mysterious stranger calls out"
)

print(f"✅ Created scene: {scene.title}")
print(f"   Emotional arc: {scene.get_emotional_arc()}")
print(f"   Beats: {scene.beats.count()}")
```

---

## 🎯 KEY FEATURES

### **1. Emotional Arc Tracking:**
```python
# Get all scenes from hopeful to desperate
arc_scenes = Scene.objects.filter(
    emotional_start__code='hopeful',
    emotional_end__code='desperate'
)

for scene in arc_scenes:
    print(f"{scene.title}: Hopeful → Desperate")
```

### **2. Conflict/Pacing Analysis:**
```python
# Get high-intensity scenes
intense = Scene.objects.filter(
    conflict_level__intensity__gte=8
).order_by('chapter__order', 'order')

for scene in intense:
    print(f"Chapter {scene.chapter.number}: {scene.title} (intensity: {scene.conflict_level.intensity})")
```

### **3. Plot Thread Tracking:**
```python
# Create plot thread
from apps.writing_hub.models import PlotThread

main_plot = PlotThread.objects.create(
    project=project,
    name="Main Quest",
    thread_type='main',
    description="Hero must save the kingdom"
)

# Add scenes to thread
scene.plot_threads.add(main_plot)

# Get all scenes in thread
thread_scenes = main_plot.scenes.all()
```

### **4. Character Presence:**
```python
from apps.bfagent.models import BookCharacters

# Create characters
hero = BookCharacters.objects.create(
    project=project,
    name="Aldric the Brave"
)

# Set POV
scene.pov_character = hero
scene.save()

# Add to scene
scene.characters.add(hero)

# Find all hero scenes
hero_scenes = hero.scenes.all()
hero_pov = hero.pov_scenes.all()
```

---

## 📊 WHAT YOU GET

### **Lookup Tables (Master Data):**
- **10 Emotional Tones** (hopeful, tense, joyful, etc.)
- **5 Conflict Levels** (none → climax, with 0-10 intensity)
- **8 Beat Types** (action, dialogue, revelation, etc.)
- **6 Scene Connections** (foreshadowing, callback, etc.)

### **Story Elements:**
- **Scenes** with POV, emotional arc, conflict level
- **Beats** (smallest story unit)
- **Locations** (settings)
- **Plot Threads** (parallel storylines)
- **Scene Connections** (foreshadowing, callbacks)
- **Timeline Events** (story chronology)

### **Analysis Capabilities:**
- Pacing analysis (conflict over time)
- Emotional journey tracking
- Character presence matrix
- Plot thread coverage
- Word count tracking

---

## 🎨 VISUALIZATION READY

**Data is structured for:**
- Mermaid.js charts (emotional arc, pacing)
- Timeline diagrams
- Character-scene matrix
- Plot thread gantt charts

---

## 🔗 INTEGRATION

### **Works With:**
- ✅ Existing Book Projects
- ✅ Existing Chapters
- ✅ Existing Characters
- ✅ OutlineHandlers (can create scenes!)
- ✅ Visualization Service

### **No Breaking Changes:**
- 100% new tables
- Doesn't affect existing code
- Optional enhancement

---

## ⚡ THAT'S IT!

**3 Commands:**
```bash
python manage.py makemigrations writing_hub
python manage.py migrate
python manage.py init_story_lookups
```

**Result:**
- Professional scene-based planning
- 10 lookup tables
- 6 story element types
- Full Django admin
- Analysis ready

**Time:** 5 minutes  
**Value:** 🔥 Professional story tool!

---

## 📚 FULL DOCS

- **Implementation:** `SCENE_MODEL_IMPLEMENTATION_COMPLETE.md`
- **Source Analysis:** `STORY_OUTLINE_TOOL_SOURCE_ANALYSIS.md`
- **Integration Plan:** `STORY_OUTLINE_INTEGRATION_PLAN.md`

---

**Ready to plan stories like a pro! 🎬✨**
