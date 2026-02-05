# Konzept: Buchillustrations-System für Platform

**Version:** 1.0  
**Datum:** 29. Januar 2026  
**Status:** Phase 1 Complete - Schema Implementation  
**Abhängigkeit:** PROMPT_TEMPLATE_SYSTEM_CONCEPT.md

---

## 1. Executive Summary

Dieses Dokument beschreibt die **Erweiterung des Prompt-Template-Systems** um Bildgenerierungs-Fähigkeiten für Buchillustrationen. Das System ermöglicht konsistente, stilgetreue Illustrationen für verschiedene Buchtypen (Sci-Fi, Kinderbuch, Sachbuch, etc.) durch:

1. **Style-Manifeste als Pydantic-Schemas** — Strukturierte Stil-Definitionen statt Freitext
2. **Integration ins Prompt-Template-System** — Style als Partial, Content als Variable
3. **Validierung und Governance** — Automatische Prüfung gegen Stil-Regeln
4. **Execution Tracking** — Audit-Trail für alle generierten Bilder

### Architektur-Entscheidung

**Option C: Hybrid mit Prompt-Template-System** wurde gewählt weil:
- Wiederverwendung bestehender Infrastruktur
- Konsistente Patterns für Text- und Bild-Prompts
- Execution Tracking, A/B Testing "gratis" dabei
- Kein paralleles System zu maintainen

---

## 2. Implementierte Komponenten (Phase 1)

### 2.1 Schema-Erweiterungen

```
packages/creative_services/prompts/
├── schemas.py                    # ✅ Existiert
└── schemas_image.py              # 🆕 NEU (Phase 1)
    ├── OutputFormat.IMAGE        # Neuer Output-Typ
    ├── ColorSpec                 # Farbdefinition
    ├── ColorPalette              # Palette mit Primary/Accent/Forbidden
    ├── SDParameters              # Stable Diffusion Parameter
    ├── IllustrationStyleSpec     # Vollständige Stil-Spezifikation
    ├── ImageGenerationParams     # Image-Parameter für Templates
    ├── ImagePromptExecution      # Execution-Result
    ├── StyleSpecMigrator         # Schema-Versionierung
    └── PromptValidator           # Prompt-Validierung
```

### 2.2 Neue Enums

| Enum | Werte | Verwendung |
|------|-------|------------|
| `OutputFormat` | + `IMAGE` | Unterscheidet Text vs. Bild-Output |
| `TemplateType` | + `STYLE_PARTIAL` | Spezieller Typ für Style-Manifeste |
| `ImageFunction` | erzählend, erklärend, atmosphärisch, ikonisch | Funktion des Bildes |
| `LightingType` | soft, diffuse, dramatic, etc. | Beleuchtung |
| `ContrastLevel` | low, moderate, high, dramatic | Kontrast |
| `SDSampler` | DPM++ 2M Karras, Euler a, etc. | SD Sampler |

### 2.3 Kern-Schemas

#### IllustrationStyleSpec

```python
class IllustrationStyleSpec(BaseModel):
    """Vollständige Stil-Definition für Buchillustrationen."""
    
    schema_version: int = 1
    
    # Identity
    style_key: str          # "scifi_book_v1"
    version: str            # "1.0"
    name: str               # "Sci-Fi Buchillustration"
    status: StyleStatus     # draft, active, deprecated
    
    # Ziel & Wirkung
    emotion: list[str]      # ["ruhig", "fremd", "kontemplativ"]
    target_audience: str
    image_function: list[ImageFunction]
    
    # Medium & Technik
    medium: MediumSpec      # medium, line_character, color_application, texture
    
    # Farben
    colors: ColorPalette    # primary, accent, forbidden
    
    # Licht & Kontrast
    lighting: LightingSpec
    
    # Komposition
    composition: CompositionSpec
    
    # Verbotene Elemente
    forbidden_elements: list[str]
    
    # SD Parameter
    sd_params: Optional[SDParameters]
    
    # Derived Methods
    def build_style_block(self) -> str: ...
    def build_negative_prompt(self) -> str: ...
```

#### ColorPalette

```python
class ColorPalette(BaseModel):
    primary: list[ColorSpec]        # Dominante Farben
    accent: list[ColorSpec]         # Akzentfarben (sparsam)
    forbidden: list[ForbiddenColorSpec]  # Verbotene Farben/Patterns
    
    def get_all_hex_codes(self) -> list[str]: ...
    def get_forbidden_patterns(self) -> list[str]: ...
```

#### SDParameters

```python
class SDParameters(BaseModel):
    base_model: str         # "sd_xl_base_1.0"
    sampler: SDSampler      # DPM++ 2M Karras
    steps: int              # 30
    cfg_scale: float        # 5.5
    width: int              # 768 (multiple of 64)
    height: int             # 1024 (multiple of 64)
    lora_key: Optional[str] # "scifi_book_style_v1"
    lora_strength: float    # 1.0
    
    def get_lora_prompt_tag(self) -> str: ...
    # Returns: "<scifi_book_style_v1:1.0>"
```

---

## 3. Verwendungs-Workflow

### 3.1 Style-Manifest als YAML

```yaml
# prompts/illustration/styles/scifi_book_v1.yaml
key: illustration.style.scifi_book_v1
type: style_partial

style_spec:
  style_key: scifi_book_v1
  version: "1.0"
  emotion: ["ruhig", "fremd", "kontemplativ"]
  
  medium:
    medium: "ink and watercolor illustration"
    line_character: "thin, precise ink lines"
    # ...
  
  colors:
    primary:
      - hex_code: "#5B6E7A"
        name: dusty_blue
        role: primary
    forbidden:
      - pattern: "neon"
        reason: "Zu grell"
  
  forbidden_elements:
    - photorealistic
    - 3d render
    - anime
  
  sd_params:
    base_model: "sd_xl_base_1.0"
    lora_key: "scifi_book_style_v1"
    steps: 30
    cfg_scale: 5.5
```

### 3.2 Bildgenerierungs-Template

```yaml
# prompts/illustration/generate/chapter_image.yaml
key: illustration.generate.chapter_image
output_format: image

partials:
  style: illustration.style.scifi_book_v1

user_prompt: |
  {{ partial:style.style_block }}
  
  illustration of
  {{ subject }}
  {% if action %}{{ action }}{% endif %}
  {% if environment %}in {{ environment }}{% endif %},
  
  {{ mood }} atmosphere

variables:
  - name: subject
    required: true
    examples: ["a lone astronaut", "an ancient artifact"]
  - name: action
    required: false
  - name: environment
    required: false
  - name: mood
    default: "calm, contemplative"

image_params:
  style_partial_key: illustration.style.scifi_book_v1
  forbidden_terms: ["photorealistic", "anime", "dramatic"]
  required_terms: ["illustration"]
```

### 3.3 Execution

```python
# Python-Code zur Verwendung
from creative_services.prompts import PromptExecutor

executor = PromptExecutor(...)

result = await executor.execute(
    template_key="illustration.generate.chapter_image",
    variables={
        "subject": "a lone astronaut in a worn spacesuit",
        "action": "standing quietly",
        "environment": "an empty space station corridor",
        "mood": "contemplative, isolated",
    },
    app_name="bfagent",
)

# Result ist ImagePromptExecution
sd_request = result.to_sd_request()
# → Direkt an Stable Diffusion API senden
```

---

## 4. Validierung

### 4.1 Automatische Validierung

```python
from creative_services.prompts.schemas_image import PromptValidator

is_valid, errors = PromptValidator.validate_prompt(
    prompt=generated_prompt,
    image_params=template.image_params,
    style_spec=style.style_spec,
)

if not is_valid:
    for error in errors:
        print(f"❌ {error}")
    # z.B. "Verbotener Term gefunden: 'photorealistic'"
```

### 4.2 Validierte Aspekte

| Check | Beschreibung |
|-------|--------------|
| **Forbidden Terms** | Terme aus `forbidden_terms` dürfen nicht im Prompt sein |
| **Required Terms** | Terme aus `required_terms` müssen im Prompt sein |
| **Style Forbidden** | Terme aus `style_spec.forbidden_elements` werden geprüft |
| **Color Validation** | Hex-Codes werden normalisiert und validiert |
| **Resolution** | Width/Height müssen durch 64 teilbar sein |

---

## 5. Governance & Team-Workflow

### 5.1 Rollen

| Rolle | Verantwortung | Deliverable |
|-------|---------------|-------------|
| **Autor** | Szenen-Bedeutung, was gezeigt werden soll | Briefing (max 5 Zeilen) |
| **Art Director** | Style-Manifest, Stilkonstanz, Freigabe | YAML-Dateien, Stilanker |
| **KI-Operator** | Template-Ausführung, keine Stilinterpretation | Generierte Bilder |
| **Review** | Prüfung gegen Manifest | ✓/✗ Entscheidung |

### 5.2 Versionierung

```
illustration.style.scifi_book_v1     # Initial
illustration.style.scifi_book_v1.1   # Kleine Korrekturen
illustration.style.scifi_book_v2     # Neuer Look
```

**Regel:** Niemals bestehende Versionen überschreiben.

### 5.3 Stil-Regression-Tests

Alle 10-15 Bilder:
1. Testmotiv mit festem Seed generieren
2. Mit Baseline vergleichen
3. Bei >15% Drift: Stop, Ursache klären

---

## 6. Implementierungs-Roadmap

### ✅ Phase 1: Schema-Definition (Complete)

- [x] `OutputFormat.IMAGE` hinzufügen
- [x] `ColorSpec`, `ColorPalette` Schemas
- [x] `SDParameters` Schema
- [x] `IllustrationStyleSpec` Hauptschema
- [x] `ImageGenerationParams` für Templates
- [x] `ImagePromptExecution` Result-Schema
- [x] `PromptValidator` für Validierung
- [x] `StyleSpecMigrator` für Versionierung
- [x] Unit Tests

### Phase 2: Style-Partial-Typ (2-3 Tage)

- [ ] `StylePartialTemplate` als Template-Subtyp
- [ ] YAML-Loader für `style_spec`
- [ ] Partial-Resolution mit Style-Daten
- [ ] Negative-Prompt-Template Support

### Phase 3: Executor-Erweiterung (2 Tage)

- [ ] `_execute_image()` Methode in `PromptExecutor`
- [ ] Style-Block Rendering
- [ ] SD-Request Generation
- [ ] Prompt-Validierung vor Execution

### Phase 4: Erstes Style-Manifest (1-2 Tage)

- [ ] `scifi_book_v1.yaml` finalisieren
- [ ] `chapter_image.yaml` Template
- [ ] Stilanker-Bilder definieren
- [ ] Manuelle Tests mit SD

### Phase 5: Regression-Testing (2 Tage)

- [ ] 5 Testmotive definieren
- [ ] Baseline-Bilder generieren
- [ ] Automatisierter Stil-Drift-Check

---

## 7. Integration mit BFAgent

### 7.1 Migrations-Strategie

```
Phase 1: Adapter (0 Breaking Changes)
├── creative-services mit Image-Schemas installieren
├── Bestehender BFAgent Code funktioniert weiter
└── Neue Illustrationen nutzen neue Schemas

Phase 2: Graduelle Migration
├── Neue Buchprojekte nutzen Style-Manifeste
├── Alte Projekte weiter mit altem System
└── Parallelbetrieb

Phase 3: Vollständige Migration (optional)
├── Alle Stile als YAML-Manifeste
└── Alte Ad-hoc-Prompts deprecaten
```

### 7.2 Kompatibilitäts-Layer

```python
# apps/bfagent/services/illustration_adapter.py

def generate_chapter_image(
    book_project_id: int,
    chapter_number: int,
    subject: str,
    **kwargs,
) -> ImagePromptExecution:
    """
    BFAgent-Wrapper für Platform Illustration System.
    """
    from creative_services.prompts import executor
    
    # Style aus BookProject laden
    style_key = get_style_for_project(book_project_id)
    
    return executor.execute(
        template_key="illustration.generate.chapter_image",
        variables={
            "subject": subject,
            "chapter_number": chapter_number,
            **kwargs,
        },
        app_name="bfagent",
        user_id=str(book_project_id),
    )
```

---

## 8. Dateien in diesem Konzept

| Datei | Beschreibung |
|-------|--------------|
| `creative_services_prompts_image_schemas.py` | Haupt-Implementierung aller Schemas |
| `prompts_illustration_styles_scifi_book_v1.yaml` | Beispiel Style-Manifest |
| `prompts_illustration_generate_chapter_image.yaml` | Beispiel Generation-Template |
| `test_image_schemas.py` | Unit-Tests |

---

## 9. Offene Fragen

1. **LoRA-Training Integration**: Soll das System LoRA-Training-Parameter tracken?
2. **Image Storage**: Wo werden generierte Bilder gespeichert?
3. **ComfyUI vs. AUTOMATIC1111**: Welches Backend priorisieren?
4. **Stilanker-Verwaltung**: Wie werden Referenzbilder versioniert?

---

## 10. Nächste Schritte

1. **Review dieses Konzepts** durch Platform Architecture Team
2. **Phase 2 starten**: Style-Partial-Typ implementieren
3. **Erstes Real-World-Beispiel**: Sci-Fi Buchprojekt mit neuem System

---

**Ende des Konzeptpapiers**

*Zu reviewen in Verbindung mit PROMPT_TEMPLATE_SYSTEM_CONCEPT.md*
