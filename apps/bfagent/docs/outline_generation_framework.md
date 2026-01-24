# Outline-Generierungs-Framework
## Flexibles System für Struktur-Lernen und -Anwendung

---

## 1. VISION

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   BEISPIEL HOCHLADEN          →    STRUKTUR EXTRAHIEREN             │
│   (Buch, Outline, Drehbuch)        (LLM analysiert Pattern)         │
│                                                                      │
│            ↓                                                         │
│                                                                      │
│   OUTLINE-TEMPLATE GENERIEREN  →   AUF PROJEKT ANWENDEN             │
│   (Wiederverwendbar)               (Verschiedene Formate)           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. USE CASES

### Use Case 1: Bekannte Struktur lernen
```
User lädt hoch: "Save the Cat" Beispiel-Outline
System extrahiert: 15 Beats mit Timing (%)
System generiert: OutlineTemplate "Save the Cat (Custom)"
User wendet an: Auf eigenes Projekt "Brennpunkt"
```

### Use Case 2: Eigene Struktur aus Erfolgs-Buch
```
User lädt hoch: Fitzgerald "Der große Gatsby" (Kapitelstruktur)
System extrahiert: 9 Kapitel, Akt-Aufteilung, Wendepunkte
System generiert: OutlineTemplate "Gatsby-Struktur"
User wendet an: Auf eigenes Romance-Projekt
```

### Use Case 3: Genre-spezifische Struktur
```
User lädt hoch: 5 Dark Romance Bücher (Strukturen)
System lernt: Gemeinsame Patterns (Tropes, Beats)
System generiert: OutlineTemplate "Dark Romance Standard"
User wendet an: Auf neues Dark Romance Projekt
```

### Use Case 4: Format-Konvertierung
```
User hat: Outline in "3-Akt" Format
User will: Dieselbe Story in "Hero's Journey" sehen
System mapped: 3-Akt Beats → 12 Hero's Journey Steps
```

---

## 3. ARCHITEKTUR

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OUTLINE GENERATION FRAMEWORK                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐  │
│  │   EXTRACTOR    │     │   GENERATOR    │     │    ADAPTER     │  │
│  │                │     │                │     │                │  │
│  │ Beispiel → LLM │────▶│ Pattern → TPL  │────▶│ TPL → Projekt  │  │
│  │ → Struktur     │     │ → Template     │     │ → Kapitel      │  │
│  └────────────────┘     └────────────────┘     └────────────────┘  │
│          │                      │                      │           │
│          ▼                      ▼                      ▼           │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    OUTLINE TEMPLATE LIBRARY                 │   │
│  │                                                             │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │   │
│  │  │ 3-Akt       │ │ Hero's      │ │ Save the    │           │   │
│  │  │ (Built-in)  │ │ Journey     │ │ Cat         │           │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘           │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │   │
│  │  │ 7-Point     │ │ Dan Harmon  │ │ Custom:     │           │   │
│  │  │ Structure   │ │ Story Circle│ │ "Gatsby"    │           │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘           │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. DATENMODELL

```python
# ========================================
# OUTLINE TEMPLATE (Die Struktur-Vorlage)
# ========================================

class OutlineTemplate(models.Model):
    """Wiederverwendbare Outline-Struktur"""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    
    # Kategorisierung
    category = models.CharField(choices=[
        ('classic', 'Klassische Strukturen'),      # 3-Akt, 5-Akt
        ('modern', 'Moderne Methoden'),            # Save the Cat, Story Circle
        ('genre', 'Genre-spezifisch'),             # Romance Beat Sheet
        ('custom', 'Benutzerdefiniert'),           # Aus Beispiel gelernt
    ])
    
    # Die Struktur selbst
    structure = models.JSONField()
    # Beispiel:
    # {
    #   "type": "beat_sheet",
    #   "total_beats": 15,
    #   "beats": [
    #     {"id": 1, "name": "Opening Image", "position": 0.01, "description": "..."},
    #     {"id": 2, "name": "Theme Stated", "position": 0.05, "description": "..."},
    #     ...
    #   ],
    #   "acts": [
    #     {"number": 1, "name": "Setup", "start": 0, "end": 0.25, "beats": [1,2,3,4]},
    #     ...
    #   ]
    # }
    
    # Metadaten
    source_type = models.CharField(choices=[
        ('builtin', 'System-vordefiniert'),
        ('extracted', 'Aus Beispiel extrahiert'),
        ('manual', 'Manuell erstellt'),
        ('learned', 'Aus mehreren Beispielen gelernt'),
    ])
    source_document = models.TextField(blank=True)  # Original wenn extracted
    
    # Anwendbarkeit
    recommended_genres = models.JSONField(default=list)  # ["thriller", "romance"]
    recommended_lengths = models.JSONField(default=dict)  # {"min": 50000, "max": 120000}
    
    # Versionierung
    version = models.IntegerField(default=1)
    parent = models.ForeignKey('self', null=True, on_delete=models.SET_NULL)
    
    is_public = models.BooleanField(default=False)  # Für andere User sichtbar
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)


# ========================================
# OUTLINE BEAT (Ein Element der Struktur)
# ========================================

class OutlineBeat(models.Model):
    """Ein Beat/Step innerhalb eines Templates"""
    
    template = models.ForeignKey(OutlineTemplate, related_name='beats')
    
    # Position
    order = models.IntegerField()
    position_percent = models.FloatField()  # 0.0 - 1.0 (wo im Buch)
    
    # Definition
    name = models.CharField(max_length=200)
    name_de = models.CharField(max_length=200)  # Deutsche Übersetzung
    description = models.TextField()
    
    # Funktion
    function = models.CharField(choices=[
        ('hook', 'Hook / Einstieg'),
        ('setup', 'Setup / Exposition'),
        ('catalyst', 'Katalysator / Auslöser'),
        ('debate', 'Debatte / Zögern'),
        ('break_into_2', 'Übergang zu Akt 2'),
        ('b_story', 'B-Story / Nebenhandlung'),
        ('fun_and_games', 'Fun & Games / Versprechen'),
        ('midpoint', 'Midpoint / Wendepunkt'),
        ('bad_guys_close_in', 'Gegner schlagen zu'),
        ('all_is_lost', 'Alles verloren'),
        ('dark_night', 'Dunkle Nacht der Seele'),
        ('break_into_3', 'Übergang zu Akt 3'),
        ('finale', 'Finale'),
        ('final_image', 'Schlussbild'),
        ('custom', 'Benutzerdefiniert'),
    ])
    
    # Akt-Zuordnung
    act = models.IntegerField()
    
    # Tipps
    writing_tips = models.TextField(blank=True)
    examples = models.JSONField(default=list)  # Beispiele aus bekannten Werken


# ========================================
# PROJEKT-OUTLINE (Anwendung auf Projekt)
# ========================================

class ProjectOutline(models.Model):
    """Konkretes Outline für ein Buchprojekt"""
    
    project = models.OneToOneField(BookProjects, related_name='outline')
    template = models.ForeignKey(OutlineTemplate, on_delete=models.PROTECT)
    
    # Anpassungen
    customizations = models.JSONField(default=dict)
    # {
    #   "renamed_beats": {"midpoint": "Die große Enthüllung"},
    #   "added_beats": [...],
    #   "removed_beats": [5, 7],
    # }
    
    # Status
    completion_status = models.JSONField(default=dict)
    # {
    #   "beat_1": {"status": "complete", "chapters": [1, 2]},
    #   "beat_2": {"status": "in_progress", "chapters": [3]},
    #   "beat_3": {"status": "planned", "chapters": []},
    # }


# ========================================
# KAPITEL-BEAT-ZUORDNUNG
# ========================================

class ChapterBeatAssignment(models.Model):
    """Zuordnung: Kapitel → Beat"""
    
    chapter = models.ForeignKey(BookChapters, related_name='beat_assignments')
    beat = models.ForeignKey(OutlineBeat, related_name='chapter_assignments')
    
    # Position innerhalb des Beats
    position_in_beat = models.IntegerField(default=0)  # Falls mehrere Kapitel pro Beat
    
    # Notizen
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['chapter', 'beat']
```

---

## 5. EXTRACTOR SERVICE

```python
class OutlineExtractorService:
    """Extrahiert Outline-Struktur aus Beispieldokumenten"""
    
    LLM_GATEWAY = "http://127.0.0.1:8100"
    
    async def extract_from_document(
        self, 
        content: str, 
        document_type: str = "auto"
    ) -> OutlineTemplate:
        """
        Analysiert ein Dokument und extrahiert die Struktur.
        
        document_type: 
            - "outline": Bereits strukturiertes Outline
            - "manuscript": Fertiger Text → Reverse Engineering
            - "beat_sheet": Beat Sheet Format
            - "auto": LLM erkennt Format
        """
        
        # Step 1: Dokument-Typ erkennen
        if document_type == "auto":
            document_type = await self._detect_document_type(content)
        
        # Step 2: Struktur extrahieren
        structure = await self._extract_structure(content, document_type)
        
        # Step 3: Normalisieren
        normalized = self._normalize_structure(structure)
        
        # Step 4: Template erstellen
        template = OutlineTemplate.objects.create(
            name=f"Extracted: {structure.get('title', 'Unknown')}",
            category='custom',
            structure=normalized,
            source_type='extracted',
            source_document=content[:5000],
        )
        
        return template
    
    async def _extract_structure(self, content: str, doc_type: str) -> dict:
        """LLM-basierte Struktur-Extraktion"""
        
        prompt = f"""
        Analysiere dieses {doc_type} und extrahiere die narrative Struktur.
        
        DOKUMENT:
        ---
        {content}
        ---
        
        Extrahiere:
        1. Anzahl der Akte
        2. Alle Beats/Wendepunkte mit:
           - Name
           - Position (% des Gesamtwerks)
           - Funktion (hook, catalyst, midpoint, climax, etc.)
           - Beschreibung was passiert
        3. Kapitelstruktur falls vorhanden
        4. Besondere Muster (Dual POV, Zeitsprünge, etc.)
        
        JSON-Format:
        {{
            "title": "Erkannter Titel",
            "structure_type": "three_act|five_act|beat_sheet|custom",
            "total_acts": 3,
            "acts": [
                {{
                    "number": 1,
                    "name": "Setup",
                    "start_percent": 0,
                    "end_percent": 25,
                    "description": "..."
                }}
            ],
            "beats": [
                {{
                    "name": "Opening Image",
                    "position_percent": 1,
                    "function": "hook",
                    "description": "...",
                    "act": 1
                }}
            ],
            "special_patterns": ["dual_pov", "flashbacks", ...],
            "recommended_chapter_count": 20,
            "confidence": 0.85
        }}
        """
        
        response = await self._call_llm(prompt)
        return response
    
    async def learn_from_multiple(
        self, 
        documents: List[str], 
        genre: str = None
    ) -> OutlineTemplate:
        """
        Lernt gemeinsame Muster aus mehreren Dokumenten.
        
        Beispiel: 5 Romance-Bücher → "Romance Standard Pattern"
        """
        
        # Extrahiere Struktur aus jedem Dokument
        structures = []
        for doc in documents:
            structure = await self._extract_structure(doc, "manuscript")
            structures.append(structure)
        
        # Finde gemeinsame Patterns
        common_pattern = await self._find_common_patterns(structures)
        
        # Generiere Template
        template = OutlineTemplate.objects.create(
            name=f"Learned: {genre or 'Mixed'} Pattern ({len(documents)} sources)",
            category='learned',
            structure=common_pattern,
            source_type='learned',
            recommended_genres=[genre] if genre else [],
        )
        
        return template
```

---

## 6. ADAPTER SERVICE

```python
class OutlineAdapterService:
    """Wendet Outline-Templates auf Projekte an und konvertiert zwischen Formaten"""
    
    async def apply_template_to_project(
        self,
        project: BookProjects,
        template: OutlineTemplate,
        auto_assign_chapters: bool = True
    ) -> ProjectOutline:
        """Wendet ein Template auf ein Projekt an"""
        
        # Erstelle ProjectOutline
        outline = ProjectOutline.objects.create(
            project=project,
            template=template,
        )
        
        # Auto-Zuordnung von Kapiteln zu Beats
        if auto_assign_chapters and project.chapters.exists():
            await self._auto_assign_chapters(project, outline)
        
        return outline
    
    async def convert_outline(
        self,
        project: BookProjects,
        from_template: OutlineTemplate,
        to_template: OutlineTemplate
    ) -> ProjectOutline:
        """
        Konvertiert ein Outline von einem Format in ein anderes.
        
        Beispiel: 3-Akt → Hero's Journey
        """
        
        # Hole aktuelle Kapitel-Zuordnungen
        current_assignments = ChapterBeatAssignment.objects.filter(
            chapter__project=project
        )
        
        # LLM: Mappe alte Beats auf neue
        mapping = await self._map_beats(from_template, to_template)
        
        # Wende Mapping an
        new_outline = await self.apply_template_to_project(
            project, 
            to_template,
            auto_assign_chapters=False
        )
        
        # Übertrage Zuordnungen mit Mapping
        for old_assignment in current_assignments:
            old_beat_id = old_assignment.beat_id
            new_beat_id = mapping.get(old_beat_id)
            
            if new_beat_id:
                ChapterBeatAssignment.objects.create(
                    chapter=old_assignment.chapter,
                    beat_id=new_beat_id,
                    notes=f"Konvertiert von {from_template.name}"
                )
        
        return new_outline
    
    async def _map_beats(
        self, 
        from_tpl: OutlineTemplate, 
        to_tpl: OutlineTemplate
    ) -> dict:
        """LLM-basiertes Beat-Mapping"""
        
        prompt = f"""
        Mappe die Beats von Struktur A auf Struktur B.
        
        STRUKTUR A ({from_tpl.name}):
        {json.dumps(from_tpl.structure['beats'], indent=2)}
        
        STRUKTUR B ({to_tpl.name}):
        {json.dumps(to_tpl.structure['beats'], indent=2)}
        
        Erstelle ein Mapping im Format:
        {{
            "beat_id_from_A": "beat_id_from_B",
            ...
        }}
        
        Mappe basierend auf Funktion und Position.
        Manche Beats haben kein direktes Äquivalent - markiere diese mit null.
        """
        
        return await self._call_llm(prompt)
```

---

## 7. EXPORT-FORMATE

```python
class OutlineExportService:
    """Exportiert Outlines in verschiedene Formate"""
    
    FORMATS = {
        'markdown': 'Markdown mit Überschriften',
        'scrivener': 'Scrivener-kompatibel',
        'notion': 'Notion-Import (CSV)',
        'json': 'JSON (für andere Tools)',
        'pdf': 'PDF mit Visualisierung',
        'timeline': 'Visuelle Timeline (SVG)',
    }
    
    def export(self, project_outline: ProjectOutline, format: str) -> str:
        """Exportiert Outline in gewünschtes Format"""
        
        if format == 'markdown':
            return self._export_markdown(project_outline)
        elif format == 'scrivener':
            return self._export_scrivener(project_outline)
        # ...
    
    def _export_markdown(self, outline: ProjectOutline) -> str:
        """Markdown-Export"""
        
        md = f"# Outline: {outline.project.title}\n\n"
        md += f"**Struktur:** {outline.template.name}\n\n"
        
        for beat in outline.template.beats.all():
            md += f"## {beat.name}\n"
            md += f"*Position: {beat.position_percent}% | Akt {beat.act}*\n\n"
            
            chapters = ChapterBeatAssignment.objects.filter(
                chapter__project=outline.project,
                beat=beat
            )
            
            if chapters:
                md += "**Kapitel:**\n"
                for ca in chapters:
                    md += f"- Kapitel {ca.chapter.chapter_number}: {ca.chapter.title}\n"
            
            md += "\n"
        
        return md
```

---

## 8. UI-WORKFLOW

```
┌─────────────────────────────────────────────────────────────────┐
│  OUTLINE STUDIO                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Tab: Bibliothek] [Tab: Aus Beispiel lernen] [Tab: Anwenden]   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ TEMPLATE BIBLIOTHEK                                      │    │
│  │                                                          │    │
│  │ ⭐ KLASSIKER                                             │    │
│  │   ├── 3-Akt-Struktur                    [Anwenden]      │    │
│  │   ├── 5-Akt-Struktur (Shakespeare)      [Anwenden]      │    │
│  │   └── Hero's Journey (Campbell)         [Anwenden]      │    │
│  │                                                          │    │
│  │ 📚 MODERNE METHODEN                                      │    │
│  │   ├── Save the Cat (15 Beats)           [Anwenden]      │    │
│  │   ├── Story Circle (Dan Harmon)         [Anwenden]      │    │
│  │   └── 7-Point Structure                 [Anwenden]      │    │
│  │                                                          │    │
│  │ 🎭 GENRE-SPEZIFISCH                                      │    │
│  │   ├── Romance Beat Sheet                [Anwenden]      │    │
│  │   ├── Thriller Tension Curve            [Anwenden]      │    │
│  │   └── Mystery Structure                 [Anwenden]      │    │
│  │                                                          │    │
│  │ ✨ MEINE TEMPLATES                                       │    │
│  │   └── "Gatsby-Struktur" (custom)        [Anwenden]      │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [+ Neues Template aus Beispiel erstellen]                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. ZUSAMMENFASSUNG

| Feature | Beschreibung |
|---------|--------------|
| **Beispiel hochladen** | Jedes Format (Outline, Manuskript, Beat Sheet) |
| **Struktur extrahieren** | LLM analysiert und normalisiert |
| **Template speichern** | Wiederverwendbar für alle Projekte |
| **Template anwenden** | Auf bestehendes Projekt mit Auto-Zuordnung |
| **Format wechseln** | 3-Akt → Hero's Journey mit Beat-Mapping |
| **Exportieren** | Markdown, Scrivener, Notion, PDF, Timeline |
| **Lernen** | Aus mehreren Beispielen gemeinsame Patterns |

**Kernprinzip:** Inhalt und Struktur sind getrennt → maximale Flexibilität.

---

## 10. OUTLINE-EMPFEHLUNGS-ENGINE

### Konzept: LLM schlägt optimales Outline vor

```
┌─────────────────────────────────────────────────────────────────┐
│                    OUTLINE RECOMMENDER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   INPUT                        ANALYSE                          │
│   ┌─────────────┐             ┌─────────────────────────┐       │
│   │ Projekt:    │             │ LLM analysiert:         │       │
│   │ - Genre     │────────────▶│ - Genre-Patterns        │       │
│   │ - Premise   │             │ - Charakterkomplexität  │       │
│   │ - Charaktere│             │ - Plot-Anforderungen    │       │
│   │ - Themen    │             │ - Zielgruppe            │       │
│   │ - Länge     │             │ - Erzählperspektive     │       │
│   └─────────────┘             └─────────────────────────┘       │
│                                         │                        │
│                                         ▼                        │
│   OUTPUT                      ┌─────────────────────────┐       │
│   ┌─────────────┐             │ EMPFEHLUNG:             │       │
│   │ Top 3       │◀────────────│                         │       │
│   │ Outlines    │             │ 1. Save the Cat (92%)   │       │
│   │ mit Score   │             │    "Ideal für Romance   │       │
│   │ + Begründung│             │     mit Clear Arc"      │       │
│   └─────────────┘             │                         │       │
│                               │ 2. Hero's Journey (78%) │       │
│                               │    "Gut für epische     │       │
│                               │     Transformation"     │       │
│                               │                         │       │
│                               │ 3. 3-Akt (71%)          │       │
│                               │    "Klassisch, flexibel"│       │
│                               └─────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Service Implementation

```python
class OutlineRecommenderService:
    """LLM-basierte Outline-Empfehlung für Projekte"""
    
    LLM_GATEWAY = "http://127.0.0.1:8100"
    
    async def recommend_outline(
        self,
        project: BookProjects,
        available_templates: List[OutlineTemplate] = None
    ) -> List[OutlineRecommendation]:
        """
        Analysiert Projekt und empfiehlt passende Outline-Strukturen.
        
        Returns: Liste von Empfehlungen mit Score und Begründung
        """
        
        # Sammle Projekt-Kontext
        context = self._gather_project_context(project)
        
        # Hole verfügbare Templates
        if not available_templates:
            available_templates = OutlineTemplate.objects.filter(is_active=True)
        
        # LLM-Analyse
        recommendations = await self._analyze_and_recommend(context, available_templates)
        
        return recommendations
    
    def _gather_project_context(self, project: BookProjects) -> dict:
        """Sammelt alle relevanten Projekt-Informationen"""
        
        characters = project.characters.all()
        
        return {
            "title": project.title,
            "genre": project.genre,
            "subgenres": project.subgenres or [],
            "premise": project.story_premise,
            "logline": project.tagline,
            "themes": project.themes or [],
            "target_word_count": project.target_word_count,
            "pov_style": project.pov_style,  # dual_pov, first_person, etc.
            
            "character_analysis": {
                "total_count": characters.count(),
                "protagonists": characters.filter(role='protagonist').count(),
                "antagonists": characters.filter(role='antagonist').count(),
                "has_love_interest": characters.filter(role='love_interest').exists(),
                "has_mentor": characters.filter(role='mentor').exists(),
                "complexity": self._assess_character_complexity(characters),
            },
            
            "plot_hints": {
                "has_romance_subplot": 'romance' in str(project.themes).lower(),
                "has_mystery": 'mystery' in project.genre.lower() if project.genre else False,
                "is_series": project.is_series,
                "book_number": project.book_number or 1,
            },
            
            "existing_chapters": project.chapters.count(),
        }
    
    async def _analyze_and_recommend(
        self, 
        context: dict, 
        templates: List[OutlineTemplate]
    ) -> List[OutlineRecommendation]:
        """LLM analysiert und empfiehlt"""
        
        # Bereite Template-Beschreibungen vor
        template_descriptions = [
            {
                "id": t.id,
                "name": t.name,
                "type": t.structure.get('type'),
                "beats_count": len(t.structure.get('beats', [])),
                "description": t.description,
                "recommended_genres": t.recommended_genres,
                "strengths": t.structure.get('strengths', []),
            }
            for t in templates
        ]
        
        prompt = f"""
        Analysiere dieses Buchprojekt und empfehle die 3 besten Outline-Strukturen.
        
        PROJEKT-KONTEXT:
        {json.dumps(context, indent=2, ensure_ascii=False)}
        
        VERFÜGBARE OUTLINE-TEMPLATES:
        {json.dumps(template_descriptions, indent=2, ensure_ascii=False)}
        
        Analysiere:
        1. Genre-Anforderungen (Romance braucht Beat Sheet, Thriller braucht Tension Curve)
        2. Charakterkomplexität (Viele Charaktere → komplexere Struktur)
        3. POV-Stil (Dual POV → Struktur mit Perspektivwechsel-Beats)
        4. Serien-Position (Buch 1 → Setup-fokussiert, Buch 3 → Climax-fokussiert)
        5. Thematische Tiefe (Schwere Themen → mehr "Reflektion"-Beats)
        
        Antworte als JSON:
        {{
            "analysis": {{
                "genre_needs": "Kurze Genre-Analyse",
                "complexity_level": "low|medium|high",
                "recommended_structure_type": "beat_sheet|three_act|heroes_journey|...",
                "key_considerations": ["Punkt 1", "Punkt 2"]
            }},
            "recommendations": [
                {{
                    "template_id": 1,
                    "template_name": "Save the Cat",
                    "match_score": 92,
                    "reasoning": "Warum dieses Template passt",
                    "strengths_for_project": ["Stärke 1", "Stärke 2"],
                    "potential_challenges": ["Herausforderung 1"],
                    "customization_tips": ["Tipp für Anpassung"]
                }},
                // ... 2 weitere
            ]
        }}
        """
        
        response = await self._call_llm(prompt)
        
        # Parse und erstelle Recommendation-Objekte
        recommendations = []
        for rec in response.get('recommendations', []):
            template = next(
                (t for t in templates if t.id == rec['template_id']), 
                None
            )
            if template:
                recommendations.append(OutlineRecommendation(
                    template=template,
                    score=rec['match_score'],
                    reasoning=rec['reasoning'],
                    strengths=rec['strengths_for_project'],
                    challenges=rec['potential_challenges'],
                    tips=rec['customization_tips'],
                ))
        
        return sorted(recommendations, key=lambda r: r.score, reverse=True)
    
    async def suggest_custom_outline(
        self,
        project: BookProjects
    ) -> OutlineTemplate:
        """
        Generiert ein komplett neues, maßgeschneidertes Outline.
        
        Wenn kein bestehendes Template passt, erstellt LLM ein neues.
        """
        
        context = self._gather_project_context(project)
        
        prompt = f"""
        Erstelle ein maßgeschneidertes Outline-Template für dieses Projekt.
        
        PROJEKT:
        {json.dumps(context, indent=2, ensure_ascii=False)}
        
        Erstelle ein optimales Outline mit:
        1. Passender Akt-Struktur
        2. Genre-spezifischen Beats
        3. Charakterbogen-Integration
        4. Thematischen Meilensteinen
        
        JSON-Format:
        {{
            "name": "Custom: [Projektname] Outline",
            "description": "Maßgeschneidert für...",
            "structure_type": "custom",
            "total_acts": 3,
            "acts": [...],
            "beats": [
                {{
                    "name": "Beat-Name",
                    "position_percent": 5,
                    "function": "hook|catalyst|midpoint|...",
                    "description": "Was hier passieren sollte",
                    "character_focus": "protagonist|antagonist|both",
                    "tips": ["Spezifischer Tipp für dieses Projekt"]
                }}
            ],
            "special_features": ["dual_pov_alternation", "flashback_integration", ...],
            "reasoning": "Warum diese Struktur optimal ist"
        }}
        """
        
        response = await self._call_llm(prompt)
        
        # Erstelle neues Template
        template = OutlineTemplate.objects.create(
            name=response.get('name', f'Custom: {project.title}'),
            category='custom',
            structure=response,
            source_type='generated',
            recommended_genres=[project.genre] if project.genre else [],
            created_by=project.created_by,
        )
        
        return template


# Datenklasse für Empfehlung
@dataclass
class OutlineRecommendation:
    template: OutlineTemplate
    score: int  # 0-100
    reasoning: str
    strengths: List[str]
    challenges: List[str]
    tips: List[str]
```

### UI-Integration

```
┌─────────────────────────────────────────────────────────────────┐
│  PROJEKT: BRENNPUNKT                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🎯 OUTLINE-EMPFEHLUNG                    [Neu analysieren]     │
│                                                                  │
│  Basierend auf: Domestic Thriller, Dual POV, 2 Protagonisten    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🥇 SAVE THE CAT (92% Match)                             │    │
│  │                                                          │    │
│  │ ✓ Perfekt für Character-driven Thriller                 │    │
│  │ ✓ Klare Beat-Struktur für Spannungskurve               │    │
│  │ ✓ "All is Lost" Beat passt zu Ehe-Krise                │    │
│  │                                                          │    │
│  │ ⚠️ Dual POV erfordert Beat-Verdopplung                  │    │
│  │                                                          │    │
│  │ 💡 Tipp: Alterniere Mira/Tobias pro Beat                │    │
│  │                                                          │    │
│  │              [Dieses Template anwenden]                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🥈 3-AKT-STRUKTUR (78% Match)                           │    │
│  │    Klassisch und flexibel...            [Details]       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🥉 THRILLER TENSION CURVE (71% Match)                   │    │
│  │    Genre-spezifisch, aber weniger...    [Details]       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  🔮 [Maßgeschneidertes Outline generieren lassen]               │
│     LLM erstellt ein komplett neues Template nur für dich       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Empfehlungs-Faktoren

| Faktor | Einfluss auf Empfehlung |
|--------|------------------------|
| **Genre** | Romance → Beat Sheet, Thriller → Tension Curve |
| **POV** | Dual POV → Strukturen mit Perspektivwechsel |
| **Länge** | Kurz → 3-Akt, Lang → 5-Akt oder Beat Sheet |
| **Charaktere** | Viele → Episodische Struktur |
| **Serie** | Buch 1 → Setup, Finale → Climax-fokussiert |
| **Themen** | Schwer → Mehr Reflexions-Beats |
| **Subplots** | Viele → Verwobene Struktur |
