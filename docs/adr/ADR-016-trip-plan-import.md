---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-016: Import von Reiseplänen als Trip-Stops

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-03 |
| **Author** | Achim Dehnert |
| **Scope** | travel-beat |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-013 (Team Organization), ADR-015 (Governance) |

---

## 1. Executive Summary

Dieses ADR definiert einen **KI-gestützten Import-Workflow** für Reisepläne in Travel-Beat. Nutzer können Dokumente (PDF, XML, Bilder, etc.) hochladen, die durch LLM-Verarbeitung in strukturierte Trip-Stops konvertiert werden.

**Kernprinzip:** *"Dokument → KI-Extraktion → CSV/JSON → Validierung → Import"*

---

## 2. Context

### 2.1 Aktuelle Situation

Travel-Beat ermöglicht die manuelle Erstellung von Reisen mit Stops. Nutzer haben jedoch oft bereits:
- PDF-Reisepläne von Reisebüros
- XML-Exporte aus Buchungssystemen  
- Screenshots/Fotos von Reiserouten
- E-Mail-Bestätigungen mit Reisedaten

### 2.2 Unterstützte Eingabeformate

| Format | Quelle | Komplexität |
|--------|--------|-------------|
| **PDF** | Reisebüro-Dokumente, Buchungsbestätigungen | Mittel |
| **XML** | Booking-Systeme, Word-Export | Niedrig |
| **Bilder** (JPG, PNG) | Screenshots, Fotos von Plänen | Hoch |
| **TXT/Markdown** | Manuelle Notizen, E-Mails | Niedrig |
| **ICS** | Kalender-Exporte | Niedrig |

### 2.3 Beispiel-Inputs

Referenz-Dateien in `platform/docs/adr/inputs/`:
- `V01.00 - Reiseplan Aitutaki.pdf` - PDF-Reiseplan
- `V01.00 - Reiseplan Aitutaki.xml` - Word-XML-Export
- `Reiseverlauf.jpg` - Foto eines Reiseplans

### 2.4 Anforderungen

| ID | Anforderung | Priorität |
|----|-------------|-----------|
| R1 | Multi-Format-Upload (PDF, XML, Bilder) | CRITICAL |
| R2 | KI-gestützte Datenextraktion | CRITICAL |
| R3 | Strukturierte Zwischenrepräsentation (JSON/CSV) | HIGH |
| R4 | Benutzer-Validierung vor Import | HIGH |
| R5 | Fehlertoleranz bei unvollständigen Daten | MEDIUM |
| R6 | Batch-Import mehrerer Stops | MEDIUM |
| R7 | Undo/Rollback nach Import | LOW |

---

## 3. Decision

### 3.1 Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                        IMPORT WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────────┐    ┌──────────┐    ┌─────────┐ │
│  │ Upload  │───▶│ AI Extract  │───▶│ Validate │───▶│ Import  │ │
│  │ (Files) │    │ (LLM)       │    │ (User)   │    │ (DB)    │ │
│  └─────────┘    └─────────────┘    └──────────┘    └─────────┘ │
│       │               │                  │               │      │
│       ▼               ▼                  ▼               ▼      │
│   PDF/XML/IMG    JSON/CSV           Preview UI      Trip.stops  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Komponenten

#### 3.2.1 Document Processor

Verantwortlich für Format-spezifische Vorverarbeitung:

```python
class DocumentProcessor:
    """Konvertiert verschiedene Formate zu Text für LLM."""
    
    PROCESSORS = {
        'pdf': PDFProcessor,      # PyMuPDF / pdfplumber
        'xml': XMLProcessor,      # lxml / BeautifulSoup
        'image': ImageProcessor,  # Pillow + OCR (optional)
        'ics': ICSProcessor,      # icalendar
        'txt': TextProcessor,     # Direct passthrough
    }
    
    def process(self, file: UploadedFile) -> str:
        """Extrahiert Text-Content aus Dokument."""
        processor = self.PROCESSORS.get(file.extension)
        return processor.extract_text(file)
```

#### 3.2.2 AI Extraction Service

Nutzt LLM zur strukturierten Datenextraktion:

```python
class TripExtractor:
    """Extrahiert Trip-Stops via LLM."""
    
    EXTRACTION_PROMPT = """
    Analysiere den folgenden Reiseplan und extrahiere alle Stops.
    
    Für jeden Stop erfasse:
    - date: Datum (ISO 8601)
    - city: Stadt
    - country: Land
    - accommodation: Unterkunft (optional)
    - transport: Anreiseart (optional)
    - notes: Zusätzliche Infos (optional)
    
    Ausgabe als JSON-Array.
    
    DOKUMENT:
    {document_text}
    """
    
    def extract(self, document_text: str) -> list[TripStop]:
        result = llm_client.generate_text(
            LlmRequest(
                provider="openai",
                model="gpt-4o-mini",
                system="Du bist ein Reiseplan-Parser.",
                prompt=self.EXTRACTION_PROMPT.format(
                    document_text=document_text
                ),
                response_format="json",
            )
        )
        return self._parse_stops(result["text"])
```

#### 3.2.3 Datenmodell für Import

```python
@dataclass
class ImportedStop:
    """Zwischenrepräsentation eines extrahierten Stops."""
    date: Optional[date]
    city: str
    country: str
    accommodation: Optional[str] = None
    transport: Optional[str] = None
    notes: Optional[str] = None
    confidence: float = 1.0  # LLM-Konfidenz
    
    def to_trip_stop(self, trip: Trip) -> TripStop:
        """Konvertiert zu persistentem TripStop."""
        return TripStop(
            trip=trip,
            date=self.date,
            location_city=self.city,
            location_country=self.country,
            accommodation_name=self.accommodation,
            transport_type=self.transport,
            notes=self.notes,
        )


class ImportSession(models.Model):
    """Tracking für Import-Vorgänge."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    source_file = models.FileField(upload_to='imports/')
    extracted_data = models.JSONField()  # ImportedStop[]
    status = models.CharField(choices=ImportStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 3.3 User Interface Flow

```
1. UPLOAD
   ┌──────────────────────────────────────┐
   │  📁 Reiseplan hochladen              │
   │  ┌────────────────────────────────┐  │
   │  │  Drop files here or click     │  │
   │  │  PDF, XML, JPG, PNG, TXT      │  │
   │  └────────────────────────────────┘  │
   │  [Analysieren]                       │
   └──────────────────────────────────────┘

2. PREVIEW & VALIDATE
   ┌──────────────────────────────────────┐
   │  ✅ 12 Stops erkannt                 │
   │                                      │
   │  │ Datum      │ Ort          │ ✓ │  │
   │  │ 15.03.2026 │ Auckland, NZ │ ☑ │  │
   │  │ 17.03.2026 │ Aitutaki, CK │ ☑ │  │
   │  │ 20.03.2026 │ Rarotonga    │ ☐ │  │ ← Benutzer kann deselektieren
   │  │ ...        │ ...          │   │  │
   │                                      │
   │  [Bearbeiten] [Alle importieren]     │
   └──────────────────────────────────────┘

3. CONFIRM
   ┌──────────────────────────────────────┐
   │  ✅ 11 Stops importiert              │
   │                                      │
   │  [Zur Reise] [Weitere importieren]   │
   └──────────────────────────────────────┘
```

### 3.4 API Endpoints

```python
# apps/trips/urls.py

urlpatterns = [
    # Import API
    path('api/trips/<int:trip_id>/import/', TripImportView.as_view(), name='trip-import'),
    path('api/trips/<int:trip_id>/import/preview/', TripImportPreviewView.as_view(), name='trip-import-preview'),
    path('api/trips/<int:trip_id>/import/confirm/', TripImportConfirmView.as_view(), name='trip-import-confirm'),
]


class TripImportView(APIView):
    """Upload und Extraktion."""
    
    def post(self, request, trip_id):
        file = request.FILES['document']
        
        # 1. Process document
        processor = DocumentProcessor()
        text = processor.process(file)
        
        # 2. Extract via LLM
        extractor = TripExtractor()
        stops = extractor.extract(text)
        
        # 3. Create import session
        session = ImportSession.objects.create(
            user=request.user,
            trip_id=trip_id,
            source_file=file,
            extracted_data=[s.to_dict() for s in stops],
            status=ImportStatus.PENDING,
        )
        
        return Response({
            'session_id': session.id,
            'stops': [s.to_dict() for s in stops],
            'count': len(stops),
        })
```

### 3.5 Security

#### 3.5.1 File Upload Validation

```python
class FileValidator:
    """Validates uploaded files before processing."""
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MIME_TYPES = {
        'application/pdf': 'pdf',
        'text/xml': 'xml',
        'application/xml': 'xml',
        'image/jpeg': 'image',
        'image/png': 'image',
        'text/plain': 'txt',
        'text/calendar': 'ics',
    }
    
    def validate(self, file: UploadedFile) -> ValidationResult:
        errors = []
        
        # Size check
        if file.size > self.MAX_FILE_SIZE:
            errors.append(f"File too large: {file.size} > {self.MAX_FILE_SIZE}")
        
        # MIME type check (magic bytes, not extension)
        import magic
        mime = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)
        
        if mime not in self.ALLOWED_MIME_TYPES:
            errors.append(f"Invalid file type: {mime}")
        
        # Malware scan (ClamAV integration)
        if settings.CLAMAV_ENABLED:
            scan_result = self._scan_for_malware(file)
            if not scan_result.clean:
                errors.append("File failed malware scan")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

#### 3.5.2 Rate Limiting

```python
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests

class ImportRateLimiter:
    """Prevents abuse and cost overruns."""
    
    LIMITS = {
        'per_user_per_hour': 20,
        'per_user_per_day': 100,
        'global_per_hour': 500,
    }
    
    def check_limit(self, user: User) -> bool:
        key_hour = f"import_limit:{user.id}:hour"
        key_day = f"import_limit:{user.id}:day"
        
        hour_count = cache.get(key_hour, 0)
        day_count = cache.get(key_day, 0)
        
        if hour_count >= self.LIMITS['per_user_per_hour']:
            return False
        if day_count >= self.LIMITS['per_user_per_day']:
            return False
        
        return True
    
    def increment(self, user: User):
        # Increment with TTL
        cache.incr(f"import_limit:{user.id}:hour", 1)
        cache.expire(f"import_limit:{user.id}:hour", 3600)
```

#### 3.5.3 Authorization

```python
class TripImportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        
        # Owner or collaborator check
        if not trip.can_edit(request.user):
            raise PermissionDenied("No permission to import to this trip")
        
        # Rate limit check
        if not ImportRateLimiter().check_limit(request.user):
            return HttpResponseTooManyRequests("Import limit exceeded")
        
        # Continue with import...
```

### 3.6 Async Processing

#### 3.6.1 Celery Task

```python
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

@shared_task(
    bind=True,
    soft_time_limit=120,
    time_limit=180,
    max_retries=2,
    default_retry_delay=30,
)
def process_import_task(self, session_id: int):
    """Async import processing with timeout and retry."""
    session = ImportSession.objects.get(id=session_id)
    
    try:
        session.status = ImportStatus.PROCESSING
        session.save()
        
        # 1. Process document
        processor = DocumentProcessor()
        text = processor.process(session.source_file)
        
        # 2. Extract via LLM
        extractor = TripExtractor()
        stops = extractor.extract(text)
        
        # 3. Store results
        session.extracted_data = [s.to_dict() for s in stops]
        session.status = ImportStatus.PENDING_REVIEW
        session.save()
        
        # 4. Notify user (WebSocket or email)
        notify_import_complete(session)
        
    except SoftTimeLimitExceeded:
        session.status = ImportStatus.TIMEOUT
        session.error_message = "Processing timed out after 120s"
        session.save()
        
    except Exception as e:
        session.status = ImportStatus.FAILED
        session.error_message = str(e)
        session.save()
        raise self.retry(exc=e)
```

#### 3.6.2 Progress Tracking

```python
class ImportProgressTracker:
    """Real-time progress updates via Redis."""
    
    def __init__(self, session_id: int):
        self.key = f"import_progress:{session_id}"
    
    def update(self, step: str, percent: int, message: str = ""):
        cache.set(self.key, {
            'step': step,
            'percent': percent,
            'message': message,
            'updated_at': timezone.now().isoformat(),
        }, timeout=300)
    
    @classmethod
    def get(cls, session_id: int) -> dict:
        return cache.get(f"import_progress:{session_id}", {
            'step': 'waiting',
            'percent': 0,
        })


# In task:
tracker = ImportProgressTracker(session_id)
tracker.update('extracting', 30, 'Analyzing document...')
tracker.update('parsing', 60, 'Extracting stops...')
tracker.update('validating', 90, 'Validating data...')
```

### 3.7 Error Handling

#### 3.7.1 Error Categories

```python
class ImportError(Exception):
    """Base import error."""
    user_message: str = "Ein Fehler ist aufgetreten"
    recoverable: bool = True


class FileValidationError(ImportError):
    user_message = "Datei konnte nicht validiert werden"


class ExtractionError(ImportError):
    user_message = "Daten konnten nicht extrahiert werden"


class LLMTimeoutError(ImportError):
    user_message = "Verarbeitung hat zu lange gedauert"
    recoverable = True  # Can retry


class LLMQuotaError(ImportError):
    user_message = "API-Limit erreicht, bitte später erneut versuchen"
    recoverable = False
```

#### 3.7.2 Graceful Degradation

```python
class TripExtractor:
    def extract_with_fallback(self, document_text: str) -> ExtractResult:
        """Try extraction with fallbacks."""
        
        # Strategy 1: Full LLM extraction
        try:
            stops = self._extract_llm(document_text)
            return ExtractResult(stops=stops, method='llm', confidence=0.9)
        except LLMTimeoutError:
            pass
        
        # Strategy 2: Regex-based extraction (for structured docs)
        try:
            stops = self._extract_regex(document_text)
            if stops:
                return ExtractResult(stops=stops, method='regex', confidence=0.6)
        except Exception:
            pass
        
        # Strategy 3: Return raw text for manual parsing
        return ExtractResult(
            stops=[],
            method='manual',
            raw_text=document_text,
            confidence=0.0,
            user_message="Automatische Extraktion fehlgeschlagen. Bitte manuell eingeben."
        )
```

### 3.8 Caching Strategy

```python
class ImportCache:
    """Cache extracted data by document hash."""
    
    TTL = 7 * 24 * 3600  # 7 days
    
    @staticmethod
    def get_document_hash(file: UploadedFile) -> str:
        """SHA-256 hash of document content."""
        import hashlib
        hasher = hashlib.sha256()
        for chunk in file.chunks():
            hasher.update(chunk)
        file.seek(0)
        return hasher.hexdigest()
    
    def get_cached_extraction(self, file: UploadedFile) -> Optional[list]:
        """Return cached extraction if exists."""
        doc_hash = self.get_document_hash(file)
        cached = cache.get(f"import_extract:{doc_hash}")
        if cached:
            logger.info(f"Cache hit for document {doc_hash[:8]}")
        return cached
    
    def cache_extraction(self, file: UploadedFile, stops: list):
        """Cache extraction result."""
        doc_hash = self.get_document_hash(file)
        cache.set(f"import_extract:{doc_hash}", stops, timeout=self.TTL)
```

---

## 4. Alternatives Considered

### 4.1 Direkt-Import ohne KI

| Aspekt | Bewertung |
|--------|-----------|
| **Pro** | Schneller, keine API-Kosten |
| **Contra** | Nur für strukturierte Formate (CSV, ICS) |
| **Entscheidung** | Abgelehnt - zu eingeschränkt |

### 4.2 Nur CSV-Import

| Aspekt | Bewertung |
|--------|-----------|
| **Pro** | Einfache Implementierung |
| **Contra** | Nutzer müssten Daten manuell konvertieren |
| **Entscheidung** | Als Fallback behalten |

### 4.3 OCR-First für Bilder

| Aspekt | Bewertung |
|--------|-----------|
| **Pro** | Günstiger als Vision-LLM |
| **Contra** | Zwei-Schritt-Prozess, schlechtere Qualität |
| **Entscheidung** | Optional für Kostenoptimierung |

---

## 5. Implementation

### 5.1 Phasen

| Phase | Scope | Timeline |
|-------|-------|----------|
| **Phase 1** | PDF + TXT Import via LLM | 1 Woche |
| **Phase 2** | XML/ICS strukturierter Import | 3 Tage |
| **Phase 3** | Bild-Import (Vision API) | 1 Woche |
| **Phase 4** | UI-Polish, Batch-Import | 3 Tage |

### 5.2 Dependencies

```python
# requirements.txt additions
pdfplumber>=0.10.0      # PDF text extraction
python-docx>=1.0.0      # Word/XML processing
icalendar>=5.0.0        # ICS calendar parsing
Pillow>=10.0.0          # Image processing
```

### 5.3 Kosten-Schätzung

| Operation | Tokens (avg) | Kosten/Import |
|-----------|--------------|---------------|
| PDF-Extraktion | ~2000 input, ~500 output | ~$0.003 |
| Bild (Vision) | ~1000 input, ~500 output | ~$0.01 |

Bei 100 Imports/Tag: **~$1/Tag**

---

## 6. Risks & Mitigations

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| LLM halluziniert Daten | Mittel | Mittel | User-Validierung vor Import, Pydantic Schema |
| PDF-Parsing fehlerhaft | Niedrig | Niedrig | Fallback zu Raw-Text, multiple Parser |
| Hohe API-Kosten | Niedrig | Mittel | Caching, Rate Limiting, gpt-4o-mini |
| Langsame Verarbeitung | Mittel | Niedrig | Async Task, Progress-Indicator |
| **Malware Upload** | Niedrig | Hoch | File Validation, MIME Check, ClamAV |
| **Doppelte Imports** | Mittel | Niedrig | Duplikat-Erkennung (date+city+country) |
| **Überlast durch Abuse** | Niedrig | Mittel | Rate Limiting per User/Global |
| **Daten-Inkonsistenz** | Niedrig | Mittel | Transactional Import, Rollback |

### 6.1 Duplikat-Erkennung

```python
class DuplicateChecker:
    """Prevents importing duplicate stops."""
    
    def find_duplicates(
        self, 
        trip: Trip, 
        new_stops: list[ImportedStop]
    ) -> list[DuplicateMatch]:
        existing = trip.stops.all()
        duplicates = []
        
        for new_stop in new_stops:
            for existing_stop in existing:
                if self._is_duplicate(new_stop, existing_stop):
                    duplicates.append(DuplicateMatch(
                        new=new_stop,
                        existing=existing_stop,
                        confidence=self._calculate_similarity(new_stop, existing_stop)
                    ))
        
        return duplicates
    
    def _is_duplicate(self, a: ImportedStop, b: TripStop) -> bool:
        # Same date and city = likely duplicate
        if a.date == b.date and a.city.lower() == b.location_city.lower():
            return True
        return False
```

### 6.2 Schema Validation (Pydantic)

```python
from pydantic import BaseModel, Field, validator
from datetime import date
from typing import Optional

class ExtractedStopSchema(BaseModel):
    """Validates LLM-extracted stop data."""
    
    date: Optional[date] = None
    city: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    accommodation: Optional[str] = Field(None, max_length=200)
    transport: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)
    
    @validator('city', 'country')
    def strip_whitespace(cls, v):
        return v.strip() if v else v
    
    @validator('country')
    def validate_country(cls, v):
        # Could validate against country list
        if len(v) < 2:
            raise ValueError('Country name too short')
        return v
    
    class Config:
        extra = 'ignore'  # Ignore extra LLM fields


def parse_llm_response(response_text: str) -> list[ExtractedStopSchema]:
    """Parse and validate LLM JSON response."""
    import json
    
    try:
        data = json.loads(response_text)
        stops = []
        
        for item in data:
            try:
                stop = ExtractedStopSchema(**item)
                stops.append(stop)
            except ValidationError as e:
                logger.warning(f"Skipping invalid stop: {e}")
                continue
        
        return stops
    
    except json.JSONDecodeError as e:
        raise ExtractionError(f"Invalid JSON from LLM: {e}")
```

---

## 7. Success Metrics

| Metrik | Target | Messung |
|--------|--------|---------|
| Import-Erfolgsrate | >90% | Imports ohne manueller Korrektur |
| Durchschnittszeit | <10s | Upload bis Preview |
| User-Adoption | >30% | Trips mit importierten Stops |
| Kosten pro Trip | <$0.05 | LLM API Kosten |
| **Error Rate** | <5% | Fehlgeschlagene Imports |
| **Cache Hit Rate** | >20% | Wiederholte Dokumente |
| **Security Blocks** | <1% | Blockierte Uploads |

---

## 8. Testing Strategy

### 8.1 Test Categories

| Kategorie | Scope | Tooling |
|-----------|-------|---------|
| Unit Tests | Parser, Validator, Cache | pytest |
| Integration Tests | API Endpoints, Celery Tasks | pytest-django |
| E2E Tests | Full Import Flow | Playwright |
| Load Tests | Rate Limiting, Performance | locust |

### 8.2 LLM Response Mocking

```python
import pytest
from unittest.mock import patch, MagicMock

# Fixture: Sample LLM responses for different document types
MOCK_LLM_RESPONSES = {
    'pdf_travel_plan': '''[
        {"date": "2026-03-15", "city": "Auckland", "country": "New Zealand"},
        {"date": "2026-03-17", "city": "Aitutaki", "country": "Cook Islands"},
        {"date": "2026-03-20", "city": "Rarotonga", "country": "Cook Islands"}
    ]''',
    'malformed_response': '{"invalid": json',
    'empty_response': '[]',
    'partial_data': '[{"city": "Berlin"}]',  # Missing required fields
}


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for deterministic testing."""
    with patch('apps.trips.services.extractor.generate_text') as mock:
        def side_effect(request):
            # Return based on prompt content
            if 'Aitutaki' in request.prompt:
                return {'ok': True, 'text': MOCK_LLM_RESPONSES['pdf_travel_plan']}
            return {'ok': True, 'text': MOCK_LLM_RESPONSES['empty_response']}
        
        mock.side_effect = side_effect
        yield mock


class TestTripExtractor:
    def test_extract_valid_pdf(self, mock_llm_client):
        """Test extraction from valid travel plan."""
        extractor = TripExtractor()
        stops = extractor.extract("Sample travel plan to Aitutaki...")
        
        assert len(stops) == 3
        assert stops[0].city == "Auckland"
        assert stops[1].country == "Cook Islands"
    
    def test_extract_handles_malformed_json(self, mock_llm_client):
        """Test graceful handling of malformed LLM response."""
        mock_llm_client.return_value = {
            'ok': True, 
            'text': MOCK_LLM_RESPONSES['malformed_response']
        }
        
        extractor = TripExtractor()
        with pytest.raises(ExtractionError):
            extractor.extract("Some document...")
    
    def test_pydantic_validation_filters_invalid(self):
        """Test that Pydantic filters out invalid stops."""
        response = MOCK_LLM_RESPONSES['partial_data']
        
        # Should skip invalid entry, not raise
        stops = parse_llm_response(response)
        assert len(stops) == 0  # Missing required 'country'
```

### 8.3 Fixture Files

```
tests/
└── fixtures/
    └── import/
        ├── valid_travel_plan.pdf
        ├── valid_calendar.ics
        ├── corrupted_pdf.pdf
        ├── oversized_file.pdf  # >10MB
        ├── malware_test.pdf    # EICAR test file
        └── expected_outputs/
            ├── travel_plan_stops.json
            └── calendar_stops.json
```

### 8.4 Integration Test Example

```python
@pytest.mark.django_db
class TestImportAPI:
    def test_full_import_flow(self, client, user, trip, mock_llm_client):
        """Test complete import: upload → extract → confirm → verify."""
        client.force_login(user)
        
        # 1. Upload
        with open('tests/fixtures/import/valid_travel_plan.pdf', 'rb') as f:
            response = client.post(
                f'/api/trips/{trip.id}/import/',
                {'document': f},
                format='multipart'
            )
        
        assert response.status_code == 200
        session_id = response.json()['session_id']
        assert response.json()['count'] == 3
        
        # 2. Confirm import
        response = client.post(
            f'/api/trips/{trip.id}/import/confirm/',
            {'session_id': session_id, 'selected_stops': [0, 1, 2]}
        )
        
        assert response.status_code == 200
        
        # 3. Verify stops created
        assert trip.stops.count() == 3
        assert trip.stops.filter(location_city='Auckland').exists()
    
    def test_rate_limit_enforced(self, client, user, trip):
        """Test that rate limiting blocks excessive requests."""
        client.force_login(user)
        
        # Exhaust rate limit
        for i in range(25):  # Over hourly limit of 20
            cache.set(f"import_limit:{user.id}:hour", i)
        
        with open('tests/fixtures/import/valid_travel_plan.pdf', 'rb') as f:
            response = client.post(
                f'/api/trips/{trip.id}/import/',
                {'document': f}
            )
        
        assert response.status_code == 429  # Too Many Requests
```

---

## 9. Observability

### 9.1 Metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge

# Counters
import_total = Counter(
    'trip_import_total', 
    'Total import attempts',
    ['status', 'format']
)

# Histograms
import_duration = Histogram(
    'trip_import_duration_seconds',
    'Import processing time',
    buckets=[1, 5, 10, 30, 60, 120]
)

llm_tokens_used = Counter(
    'trip_import_llm_tokens',
    'LLM tokens consumed',
    ['provider', 'operation']
)

# Gauges
active_imports = Gauge(
    'trip_import_active',
    'Currently processing imports'
)
```

### 9.2 Structured Logging

```python
import structlog

logger = structlog.get_logger()

# In import task:
logger.info(
    "import_started",
    session_id=session.id,
    user_id=session.user_id,
    file_type=file_type,
    file_size=file_size,
)

logger.info(
    "import_completed",
    session_id=session.id,
    stops_extracted=len(stops),
    duration_seconds=duration,
    cache_hit=cache_hit,
)
```

### 9.3 Alerting Rules

```yaml
# prometheus/alerts/import.yml
groups:
  - name: trip-import
    rules:
      - alert: ImportErrorRateHigh
        expr: rate(trip_import_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High import error rate"
          
      - alert: ImportLatencyHigh
        expr: histogram_quantile(0.95, trip_import_duration_seconds) > 30
        for: 10m
        labels:
          severity: warning
          
      - alert: LLMCostSpike
        expr: increase(trip_import_llm_tokens[1h]) > 100000
        labels:
          severity: critical
```

---

## 10. Open Questions

- [ ] Soll der Import auch Unterkünfte direkt verlinken (Location-Lookup)?
- [ ] Integration mit Buchungs-APIs (Booking.com, Airbnb) für direkten Import?
- [ ] Multi-Trip-Import aus einem Dokument?
- [ ] Geo-Koordinaten automatisch via Geocoding API ergänzen?
- [ ] Rollback-Mechanismus bei fehlerhaftem Batch-Import?

---

## 11. References

- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)
- Beispiel-Inputs: `platform/docs/adr/inputs/`
