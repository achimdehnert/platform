# Service Layer Naming Conventions

## Problem
Inkonsistente Methodennamen in Service-Klassen führen zu:
- Import-Fehlern in Tests und Components
- Schwer zu debuggende AttributeError-Exceptions
- Zeitverlust bei der Entwicklung
- Inkonsistente API-Nutzung

## Lösung: Einheitliche Naming-Konventionen

### 1. CRUD-Operationen (Standard Pattern)

#### Create Operations
```python
def create_{entity}(data: Dict[str, Any], session: Optional[Session] = None) -> {Entity}
```
**Beispiele:**
- `create_project()`
- `create_chapter()`
- `create_character()`

#### Read Operations - Single Entity
```python
def get_{entity}_by_id(id: int, session: Optional[Session] = None) -> Optional[{Entity}]
```
**Beispiele:**
- `get_project_by_id()`
- `get_chapter_by_id()`
- `get_character_by_id()`

#### Read Operations - Multiple Entities
```python
def get_{entities}_by_{relation}(relation_id: int, session: Optional[Session] = None) -> List[{Entity}]
```
**Beispiele:**
- `get_chapters_by_project(project_id)` ✅
- `get_characters_by_project(project_id)` ✅
- `get_agents_by_type(agent_type)` ✅

**NICHT:**
- ❌ `get_chapters_by_project_id()` (redundant "_id" suffix)
- ❌ `get_characters_by_project_id()` (redundant "_id" suffix)

#### Update Operations
```python
def update_{entity}(id: int, data: Dict[str, Any], session: Optional[Session] = None) -> {Entity}
```
**Beispiele:**
- `update_project()`
- `update_chapter()`
- `update_character()`

#### Delete Operations
```python
def delete_{entity}(id: int, session: Optional[Session] = None) -> bool
```
**Beispiele:**
- `delete_project()`
- `delete_chapter()`
- `delete_character()`

### 2. Spezielle Query-Operationen

#### Filtering/Search
```python
def get_{entities}_by_{criteria}({criteria}_value, session: Optional[Session] = None) -> List[{Entity}]
```
**Beispiele:**
- `get_characters_by_role(role)`
- `get_chapters_by_status(status)`
- `get_projects_by_genre(genre)`

#### Aggregation/Statistics
```python
def get_{entity}_{metric}(id: int, session: Optional[Session] = None) -> Union[int, float]
```
**Beispiele:**
- `get_project_word_count()`
- `get_chapter_progress()`

### 3. Business Logic Operations

#### Action-Based Methods
```python
def {action}_{entity}_{context}({params}, session: Optional[Session] = None) -> {ReturnType}
```
**Beispiele:**
- `update_word_count(project_id)`
- `reorder_chapters(project_id, chapter_ids)`
- `archive_project(project_id)`

### 4. Validation Rules

#### Parameter Naming
- **ID Parameters:** Immer `{entity}_id` (z.B. `project_id`, `chapter_id`)
- **Entity Objects:** Singular form (z.B. `project`, `chapter`)
- **Entity Lists:** Plural form (z.B. `projects`, `chapters`)

#### Method Naming
- **Verben:** `get`, `create`, `update`, `delete`, `archive`, `restore`
- **Prepositions:** `by` für Filterkriterien
- **NO redundant suffixes:** Nicht `by_project_id` sondern `by_project`

### 5. Aktuelle Korrekturen Erforderlich

#### BookService (core/services/book_service.py)
```python
# ✅ KORREKT - Bereits implementiert
ChapterService.get_chapters_by_project(project_id)
CharacterService.get_characters_by_project(project_id)

# ❌ FALSCH - In Components verwendet
ChapterService.get_chapters_by_project_id(project_id)  # Nicht existent
CharacterService.get_characters_by_project_id(project_id)  # Nicht existent
```

#### Betroffene Dateien korrigiert:
- ✅ `app/components/story_context.py` - Fixed method calls
- ✅ `app/components/chapter_writer.py` - Fixed method calls
- ✅ `tests/test_coverage_analysis.py` - Fixed mock patches

### 6. Enforcement Strategy

#### Development Rules
1. **Code Reviews:** Alle Service-Methoden müssen Naming-Konventionen folgen
2. **Tests:** Mock-Patches müssen exakte Methodennamen verwenden
3. **Documentation:** Alle Service-APIs dokumentieren
4. **IDE Integration:** Type hints für bessere Auto-completion

#### Automated Checks
```python
# Beispiel: Automated naming validation
def validate_service_method_names():
    """Validate service method names follow conventions."""
    forbidden_patterns = [
        r".*_by_.*_id$",  # No redundant _id suffixes
        r"get.*s$",       # Plural get methods should be get_{entities}_by_*
    ]
    # Implementation...
```

### 7. Migration Strategy

#### Phase 1: Documentation ✅
- Naming-Konventionen definiert
- Windsurf Rules aktualisiert

#### Phase 2: Current Codebase ✅
- Service-Methoden bereits korrekt benannt
- Component-Aufrufe korrigiert
- Tests angepasst

#### Phase 3: Future Development
- Neue Service-Methoden müssen Konventionen folgen
- Code-Reviews prüfen Naming-Compliance
- Automated tests für Naming-Validation

## Zusammenfassung

**Kernprinzip:** Methodennamen sollen selbsterklärend und konsistent sein.

**Hauptregeln:**
1. `get_{entities}_by_{relation}` NICHT `get_{entities}_by_{relation}_id`
2. Parameter heißen `{entity}_id` aber Methoden verwenden `by_{entity}`
3. Konsistente CRUD-Verben: `create`, `get`, `update`, `delete`
4. Business-Logic-Methoden: `{action}_{entity}_{context}`

**Nutzen:**
- Weniger Debugging-Zeit
- Bessere Developer Experience
- Konsistente API
- Einfachere Tests und Mocks
