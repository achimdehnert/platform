---
status: "accepted"
date: 2026-03-12
amended: 2026-03-12
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-131-shared-backend-services.md", "ADR-111-private-package-distribution.md", "ADR-109-multi-tenancy-platform-standard.md", "ADR-134-module-monetization-strategy.md"]
implementation_status: not_started
implementation_evidence: []
---

# ADR-139: Shared Learning Platform Package (iil-learnfw)

> **Amended 2026-03-12**: Offene Fragen entschieden — weasyprint, Gamification in-scope,
> SCORM-Support geplant, API-First (DRF), Video als Canvas-Erweiterung (post-v1),
> PyPI-Publish von Anfang an, optimale Dokumentation als Pflicht.

---

## 1. Kontext & Problemstellung

Mehrere IIL-Plattform-Projekte benötigen eine eingebettete Lernplattform mit vergleichbaren Anforderungen:

| Consumer | Domain | Lern-Kontext |
|---|---|---|
| **risk-hub** | kiohnerisiko.de / schutztat.de | Versicherungswissen, Risikomanagement, Compliance-Schulungen |
| **coach-hub** | bierterpilot.de | Coaching-Methodiken, Zertifizierungsprogramme |
| **weitere Hubs** | — | Onboarding, Produkt-Schulungen, Partner-Trainings |

### Gemeinsame Anforderungen

- **Lernmodule**: Strukturierte Kurse mit Kapiteln, Lektionen, Fortschrittstracking
- **Testmodule**: Quizzes, Multiple-Choice, Freitext-Aufgaben mit automatischer Bewertung
- **Onboarding**: Geführte Erstnutzer-Flows mit Pflicht-Modulen und Fortschrittsanzeige
- **Zertifikate**: PDF-Zertifikate nach bestandenen Prüfungen (mit Verifizierungs-URL)
- **Content-Formate**: PDF, Markdown, PPTX (via pptx-hub/iil-pptxfw Integration)

### Problemstellung

Ohne zentrales Package würde jedes Projekt diese Funktionalität eigenständig implementieren — mit den bekannten Nachteilen: Code-Duplikation, Inkonsistenz, erhöhter Wartungsaufwand (vgl. ADR-131).

**Entscheidungsfrage**: Wie wird die Lernplattform-Funktionalität so bereitgestellt, dass sie in beliebigen Django-Hubs wiederverwendbar, konfigurierbar und mandantenfähig ist?

---

## 2. Entscheidungskriterien

- **Multi-Tenancy**: Lerninhalte und Fortschritt müssen mandantenfähig sein (ADR-109, ADR-137 RLS)
- **Content-Flexibilität**: Lerninhalte aus verschiedenen Quellen (PDF, MD, PPTX, extern)
- **Konfigurierbarkeit**: Consumer definiert welche Module aktiv sind, eigenes Branding, eigene Zertifikat-Templates
- **Monetarisierung**: Module können an billing-hub Subscription gekoppelt werden (ADR-134)
- **Offline-fähig**: Lerninhalte als PDF/PPTX downloadbar
- **Testbarkeit**: Package hat eigene Test-Suite, Consumer-Tests mocken Interfaces
- **Minimale Dependencies**: Kern-Package ohne schwere Abhängigkeiten; optionale Extras

---

## 3. Bewertete Optionen

| Kriterium | A: PyPI Package (iil-learnfw) | B: Django App im Monorepo | C: Standalone SaaS |
|---|---|---|---|
| Wiederverwendbarkeit | ✅ pip install in jedem Hub | ⚠️ Nur platform-Monorepo | ❌ Separate Infrastruktur |
| Versionierung | ✅ semver, pip | ⚠️ Git-gebunden | ✅ API-Version |
| Multi-Tenancy | ✅ TenantManager-Integration | ✅ Direkt | ⚠️ Eigene Auth |
| Content-Integration | ✅ Pluggable Backends | ✅ Direkt | ⚠️ API-basiert |
| Deployment-Aufwand | ✅ pip upgrade | ⚠️ Monorepo-Deploy | ❌ Eigener Service |
| Kosten | ✅ Kein Extra-Hosting | ✅ Kein Extra-Hosting | ❌ Eigene Infrastruktur |

---

## 4. Entscheidung

**Gewählt: Option A — PyPI Package `iil-learnfw`**

Begründung: Bewährtes Pattern (vgl. ADR-131 iil-django-commons, iil-aifw, iil-authoringfw). Maximale Wiederverwendbarkeit über alle Hubs hinweg. Semantic Versioning ermöglicht kontrollierte Updates. Multi-Tenancy wird über das bestehende TenantManager-Pattern (ADR-137) unterstützt.

- **Package-Name**: `iil-learnfw`
- **Python-Import**: `iil_learnfw`
- **Repo**: `achimdehnert/learnfw` (eigenständig, PyPI-Publish)
- **Monorepo-Mirror**: `platform/packages/iil-learnfw/` (optional, für lokale Entwicklung)

---

## 5. Package-Architektur

### 5.1 Modul-Übersicht

| Modul | Verantwortung | Dependencies |
|---|---|---|
| **iil_learnfw.courses** | Kursstruktur: Course → Chapter → Lesson, Ordering, Publishing-Status | keine |
| **iil_learnfw.content** | Content-Backend-Abstraktion: MD-Renderer, PDF-Viewer-Meta, PPTX-Integration | `markdown` (optional) |
| **iil_learnfw.progress** | Fortschrittstracking: UserProgress, LessonCompletion, CourseCompletion | keine |
| **iil_learnfw.assessments** | Testmodule: Quiz, Question (MC/Freitext/Zuordnung), Attempt, Scoring | keine |
| **iil_learnfw.certificates** | Zertifikat-Generierung: WeasyPrint HTML→PDF, Verifizierungs-URL, QR-Code | `weasyprint` |
| **iil_learnfw.onboarding** | Onboarding-Flows: Pflicht-Kurse, Checklisten, First-Login-Detection | keine |
| **iil_learnfw.gamification** | Punkte, Badges, Streaks, Leaderboards, Achievement-System | keine |
| **iil_learnfw.scorm** | SCORM 1.2/2004 Import/Export, LMS-Interoperabilität (Enterprise) | `lxml` (optional) |
| **iil_learnfw.admin** | Django-Admin Integration: Kurs-Editor, Inhalts-Upload, Statistiken | keine |
| **iil_learnfw.api** | REST-API (Pflicht): DRF-Serializer + ViewSets, Tenant-scoped, OpenAPI-Doku | `djangorestframework`, `drf-spectacular` |

### 5.2 Projektstruktur

```
learnfw/
├── src/iil_learnfw/
│   ├── __init__.py              # __version__ = "0.1.0"
│   ├── apps.py                  # IilLearnfwConfig
│   ├── settings.py              # IIL_LEARNFW dict mit typed defaults
│   ├── models/
│   │   ├── __init__.py
│   │   ├── course.py            # Course, Chapter, Lesson
│   │   ├── content.py           # ContentBlock, ContentAttachment (PDF/MD/PPTX)
│   │   ├── progress.py          # UserProgress, LessonCompletion
│   │   ├── assessment.py        # Quiz, Question, Answer, Attempt, Score
│   │   ├── certificate.py       # CertificateTemplate, IssuedCertificate
│   │   └── onboarding.py        # OnboardingFlow, OnboardingStep, UserOnboardingState
│   ├── services/
│   │   ├── course_service.py    # Kurs-CRUD, Publishing, Ordering
│   │   ├── progress_service.py  # Fortschritt tracken, Completion berechnen
│   │   ├── scoring_service.py   # Quiz-Auswertung, Bestanden/Nicht-Bestanden
│   │   ├── certificate_service.py # PDF-Generierung, Verifizierungs-Token
│   │   ├── content_service.py   # Content-Rendering (MD→HTML, PPTX-Meta)
│   │   └── onboarding_service.py # Flow-Steuerung, Pflicht-Prüfung
│   ├── content_backends/
│   │   ├── base.py              # AbstractContentBackend
│   │   ├── markdown_backend.py  # MD → HTML Rendering
│   │   ├── pdf_backend.py       # PDF-Metadaten, Viewer-URL
│   │   └── pptx_backend.py      # PPTX-Integration (iil-pptxfw / pptx-hub API)
│   ├── gamification/
│   │   ├── models.py            # Points, Badge, UserBadge, Streak, Leaderboard
│   │   ├── services.py          # award_points(), check_badges(), update_streak()
│   │   └── signals.py           # Auto-Award on lesson_complete, quiz_passed
│   ├── scorm/
│   │   ├── importer.py          # SCORM 1.2/2004 ZIP → Course+Lessons
│   │   ├── exporter.py          # Course → SCORM Package
│   │   └── runtime.py           # SCORM API Adapter (cmi.core.*)
│   ├── api/
│   │   ├── serializers.py       # Course, Lesson, Progress, Quiz, Certificate
│   │   ├── viewsets.py          # ModelViewSets, Tenant-scoped
│   │   ├── permissions.py       # IsEnrolled, IsTenantMember
│   │   ├── filters.py           # Filterset (status, category, tenant)
│   │   └── urls.py              # DRF Router
│   ├── views/
│   │   ├── course_views.py      # Kurs-Liste, Detail, Lektion-Ansicht
│   │   ├── assessment_views.py  # Quiz starten, beantworten, Ergebnis
│   │   ├── certificate_views.py # Download, Verify-Endpoint
│   │   ├── onboarding_views.py  # Onboarding-Wizard, Fortschritt
│   │   └── gamification_views.py # Leaderboard, Badge-Übersicht, Profil
│   ├── templates/iil_learnfw/   # Default-Templates (überschreibbar)
│   │   ├── course_list.html
│   │   ├── course_detail.html
│   │   ├── lesson.html
│   │   ├── quiz.html
│   │   ├── quiz_result.html
│   │   ├── certificate.html
│   │   ├── certificate_pdf.html # WeasyPrint HTML→PDF Template
│   │   ├── leaderboard.html
│   │   ├── badges.html
│   │   └── onboarding/
│   │       ├── wizard.html
│   │       └── checklist.html
│   ├── urls.py                  # Drop-in URL patterns (Views + API)
│   ├── migrations/              # Django Migrations
│   └── templatetags/
│       └── learnfw_tags.py      # {% course_progress %}, {% certificate_badge %}, {% user_points %}
├── tests/
│   ├── test_course_service.py
│   ├── test_progress_service.py
│   ├── test_scoring_service.py
│   ├── test_certificate_service.py
│   ├── test_onboarding_service.py
│   ├── test_gamification_service.py
│   ├── test_scorm_importer.py
│   ├── test_content_backends.py
│   ├── test_api.py
│   └── test_views.py
├── docs/                        # Sphinx/MkDocs Dokumentation
│   ├── index.md
│   ├── quickstart.md
│   ├── configuration.md
│   ├── models.md
│   ├── api-reference.md
│   ├── content-backends.md
│   ├── scorm.md
│   ├── gamification.md
│   └── changelog.md
├── pyproject.toml               # PEP 621, optional extras, PyPI publish
├── README.md
└── CHANGELOG.md
```

### 5.3 Datenmodell (Kern)

```
Course
├── title, slug, description, thumbnail
├── status: draft | published | archived
├── is_mandatory: bool (für Onboarding)
├── required_for_certificate: bool
├── tenant_id (Multi-Tenancy via TenantManager, ADR-137)
├── ordering: int
└── metadata: JSONField (custom Consumer-Daten)

Chapter
├── course (FK)
├── title, ordering
└── description

Lesson
├── chapter (FK)
├── title, ordering
├── content_type: markdown | pdf | pptx | video | external_url
├── content_text: TextField (für MD)
├── content_file: FileField (für PDF/PPTX)
├── content_url: URLField (für externe Inhalte)
├── estimated_duration: DurationField
└── is_downloadable: bool

Quiz (Assessment)
├── course (FK, optional — kann kursübergreifend sein)
├── chapter (FK, optional)
├── title, passing_score (z.B. 80%)
├── max_attempts: int (0 = unbegrenzt)
├── time_limit: DurationField (optional)
└── shuffle_questions: bool

Question
├── quiz (FK)
├── question_type: multiple_choice | single_choice | free_text | matching
├── text, explanation (nach Beantwortung sichtbar)
├── points: int
└── ordering

Answer (für MC/SC)
├── question (FK)
├── text, is_correct: bool
└── ordering

Attempt
├── quiz (FK), user (FK)
├── started_at, completed_at
├── score, passed: bool
└── answers: JSONField

UserProgress
├── user (FK), lesson (FK)
├── status: not_started | in_progress | completed
├── completed_at, time_spent
└── tenant_id

CertificateTemplate
├── name, html_template (für PDF-Rendering)
├── logo, signature_image
├── valid_for: DurationField (optional, Ablaufdatum)
└── tenant_id

IssuedCertificate
├── user (FK), course (FK), template (FK)
├── issued_at, expires_at
├── verification_token: UUID (öffentlich prüfbar)
├── pdf_file: FileField (generiertes PDF)
└── tenant_id

OnboardingFlow
├── name, tenant_id
├── is_active: bool
└── trigger: first_login | role_change | manual

OnboardingStep
├── flow (FK), course (FK, optional), quiz (FK, optional)
├── title, description
├── is_required: bool
└── ordering

UserOnboardingState
├── user (FK), flow (FK), step (FK)
├── status: pending | in_progress | completed | skipped
└── completed_at

Badge (Gamification)
├── name, slug, icon, description
├── trigger: course_completed | quiz_passed | streak_reached | points_reached | custom
├── threshold: int (z.B. 5 Kurse, 100 Punkte, 7 Tage Streak)
└── tenant_id

UserBadge
├── user (FK), badge (FK)
├── awarded_at
└── tenant_id

UserPoints
├── user (FK), tenant_id
├── total_points: int
├── current_streak: int (Tage)
└── longest_streak: int

PointsTransaction
├── user (FK), tenant_id
├── points: int, reason: str
├── source_type: lesson | quiz | badge | manual
└── created_at

SCORMPackage
├── course (FK), tenant_id
├── scorm_version: 1.2 | 2004
├── package_file: FileField (ZIP)
├── manifest: JSONField (imsmanifest.xml parsed)
└── imported_at
```

---

## 6. Content-Backend-Architektur

Lerninhalte werden über ein pluggable Backend-System bereitgestellt:

```python
# Abstrakte Basis
class AbstractContentBackend:
    def render(self, lesson: Lesson) -> str:
        """Rendert Lesson-Content als HTML."""
        raise NotImplementedError

    def get_download_url(self, lesson: Lesson) -> str | None:
        """Download-URL für Offline-Nutzung."""
        return None

# Markdown-Backend
class MarkdownContentBackend(AbstractContentBackend):
    def render(self, lesson):
        return markdown.markdown(lesson.content_text, extensions=["tables", "fenced_code"])

# PDF-Backend
class PDFContentBackend(AbstractContentBackend):
    def render(self, lesson):
        return f'<iframe src="{lesson.content_file.url}" ...></iframe>'
    def get_download_url(self, lesson):
        return lesson.content_file.url

# PPTX-Backend (Integration mit pptx-hub)
class PPTXContentBackend(AbstractContentBackend):
    """Nutzt pptx-hub API oder iil-pptxfw für Slide-Rendering."""
    def render(self, lesson):
        # Option A: API-Call an pptx-hub für HTML-Slides
        # Option B: Lokales Rendering via python-pptx → Bilder
        ...
    def get_download_url(self, lesson):
        return lesson.content_file.url
```

### PPTX-Integration

Die PPTX-Integration bietet zwei Modi:

1. **Direkt**: Consumer hat `iil-pptxfw` installiert → lokales Rendering von PPTX zu HTML-Slides
2. **API**: pptx-hub stellt REST-API bereit → learnfw ruft Slide-Rendering per HTTP ab

```python
# settings.py Consumer
IIL_LEARNFW = {
    "PPTX_MODE": "direct",  # "direct" | "api"
    "PPTX_API_URL": "https://pptx.iil.pet/api/v1/render/",  # nur bei mode=api
}
```

---

## 7. Consumer-Integration

### Installation

```bash
# Minimal (Kurse + Fortschritt + Onboarding)
pip install iil-learnfw

# Mit Zertifikat-PDF-Generierung
pip install "iil-learnfw[certificates]"

# Mit PPTX-Rendering
pip install "iil-learnfw[pptx]"

# Vollausstattung
pip install "iil-learnfw[all]"
```

### Django-Settings (Consumer)

```python
INSTALLED_APPS = [
    "iil_learnfw",
    ...
]

# urls.py
urlpatterns = [
    path("learn/", include("iil_learnfw.urls")),
    ...
]

# Konfiguration (alle optional — sinnvolle Defaults)
IIL_LEARNFW = {
    "COURSE_MODEL": None,           # Custom Course-Model (optional Proxy)
    "CERTIFICATE_TEMPLATE_DIR": "certificates/",  # Consumer-eigene Templates
    "PASSING_SCORE_DEFAULT": 80,    # Prozent
    "MAX_ATTEMPTS_DEFAULT": 3,
    "CONTENT_BACKENDS": {
        "markdown": "iil_learnfw.content_backends.markdown_backend.MarkdownContentBackend",
        "pdf": "iil_learnfw.content_backends.pdf_backend.PDFContentBackend",
        "pptx": "iil_learnfw.content_backends.pptx_backend.PPTXContentBackend",
    },
    "PPTX_MODE": "direct",
    "ONBOARDING_ENABLED": True,
    "CERTIFICATE_VERIFY_URL": "/learn/verify/{token}/",
    "TENANT_AWARE": True,           # Multi-Tenancy aktivieren (ADR-137)
}
```

### Beispiel: risk-hub Integration

```python
# risk-hub/config/urls.py
urlpatterns = [
    path("schulungen/", include("iil_learnfw.urls")),
    ...
]

# risk-hub settings
IIL_LEARNFW = {
    "TENANT_AWARE": True,
    "ONBOARDING_ENABLED": True,
    "CERTIFICATE_TEMPLATE_DIR": "risk_hub/certificates/",
    "CONTENT_BACKENDS": {
        "markdown": "iil_learnfw.content_backends.markdown_backend.MarkdownContentBackend",
        "pdf": "iil_learnfw.content_backends.pdf_backend.PDFContentBackend",
    },
}
```

---

## 8. Rollout-Plan

| Phase | Scope | Deliverables |
|---|---|---|
| **Phase 1** | Courses + Content + Progress + API | v0.1.0 — Kursstruktur, MD/PDF-Backend, Fortschrittstracking, DRF-API, PyPI-Publish |
| **Phase 2** | Assessments + Scoring | v0.2.0 — Quizzes, MC/Freitext, Scoring, Attempt-Tracking, API-Endpoints |
| **Phase 3** | Certificates (WeasyPrint) | v0.3.0 — HTML→PDF-Zertifikate, Verifizierungs-URL, QR-Code |
| **Phase 4** | Onboarding | v0.4.0 — Onboarding-Flows, Pflicht-Kurse, Checklisten |
| **Phase 5** | Gamification | v0.5.0 — Punkte, Badges, Streaks, Leaderboards |
| **Phase 6** | PPTX-Integration | v0.6.0 — PPTX-Backend, pptx-hub API-Anbindung |
| **Phase 7** | SCORM | v0.7.0 — SCORM 1.2/2004 Import/Export (Enterprise) |
| **Phase 8** | Consumer-Integration | v1.0.0 — Erster Hub (risk-hub) LIVE, Templates, Admin, Doku komplett |

**Querschnitt (ab Phase 1):**
- PyPI-Publish bei jedem Minor-Release
- MkDocs-Dokumentation mitgeführt (docs/)
- OpenAPI-Schema via drf-spectacular
- CI: ruff + pytest + bandit (Python 3.11+3.12)

---

## 9. Risiken & Mitigationen

- **Over-Engineering**: YAGNI — Phase 1 startet minimal (Kurse + MD/PDF). Weitere Module nur bei konkretem Bedarf.
- **Multi-Tenancy-Komplexität**: Nutzung des bewährten TenantManager-Patterns (ADR-137). Tenant-Filter in allen QuerySets.
- **Content-Storage**: FileField für PDF/PPTX. Bei Bedarf S3-Backend via Django Storages. Kein eigener Object-Store.
- **Zertifikat-Fälschung**: Signierter Verification-Token (HMAC). Öffentliche Verify-URL. Optional QR-Code auf Zertifikat.
- **Performance**: Fortschrittstracking mit Bulk-Updates. Content-Rendering gecacht. Quiz-Scoring synchron (einfach genug).

---

## 10. Entschiedene Fragen

| # | Frage | Entscheidung | Begründung |
|---|---|---|---|
| 1 | **Zertifikat-PDF-Engine** | `weasyprint` | HTML→PDF, flexibel, Template-basiert, CSS-Support. Heavy Dependency akzeptabel als optional Extra. |
| 2 | **Video-Content** | Post-v1 — Canvas oder eigene Lösung | Video ist komplexes Thema (Hosting, Streaming, DRM). Später als Canvas-LTI-Integration oder eigenes Video-Backend. |
| 3 | **Gamification** | In-scope (Phase 5, v0.5.0) | Motivation + Engagement sind Kern-Feature einer Lernplattform. Punkte/Badges/Streaks als eigenes Submodul. |
| 4 | **SCORM** | Ja (Phase 7, v0.7.0) | Enterprise-Kunden (Firmen) erwarten SCORM-Kompatibilität. Import/Export für LMS-Interoperabilität. |
| 5 | **API-First** | Ja, DRF von Phase 1 an | Tenant-fähige API ermöglicht Headless-Consumer, Mobile-Apps, externe Integrationen. OpenAPI-Doku via drf-spectacular. |
| 6 | **Distribution** | PyPI von Anfang an | Jeder Minor-Release wird auf PyPI publiziert. CI/CD mit GitHub Actions. |
| 7 | **Dokumentation** | MkDocs, ab Phase 1 mitgeführt | Aktive Entwicklung erfordert optimale Doku: Quickstart, Config-Referenz, API-Doku, Content-Backend-Guide. |

---

## 11. Distribution & Dokumentation

### PyPI

```toml
# pyproject.toml
[project]
name = "iil-learnfw"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "Django>=5.0",
    "djangorestframework>=3.15",
    "drf-spectacular>=0.27",
]

[project.optional-dependencies]
certificates = ["weasyprint>=62", "qrcode>=7"]
pptx = ["python-pptx>=1.0"]
scorm = ["lxml>=5.0"]
markdown = ["markdown>=3.6", "pymdown-extensions>=10"]
all = ["iil-learnfw[certificates,pptx,scorm,markdown]"]
```

### Dokumentation (MkDocs)

- **Quickstart**: Installation, INSTALLED_APPS, URLs, erste Kurse anlegen
- **Configuration**: Alle IIL_LEARNFW Settings mit Defaults und Beispielen
- **Models**: ER-Diagramm, Feld-Referenz, Multi-Tenancy-Hinweise
- **API Reference**: OpenAPI-Schema, Auth, Pagination, Filtering
- **Content Backends**: Eigene Backends schreiben, PPTX-Integration
- **SCORM**: Import-Workflow, Export-Format, Einschränkungen
- **Gamification**: Badge-System konfigurieren, Custom-Trigger
- **Changelog**: Semantic Versioning, Migration Guides

---

## 12. Nächste Schritte

1. ~~ADR reviewen und Entscheidung treffen~~ ✅ accepted
2. Repo `achimdehnert/learnfw` anlegen (pyproject.toml, CI, MkDocs)
3. Phase 1 implementieren: Course/Chapter/Lesson Models, MD/PDF-Backend, Progress-Tracking, DRF-API
4. PyPI-Publish v0.1.0
5. Admin-Integration: Kurs-Editor mit Drag&Drop Ordering
6. Templates: Default-Templates mit HTMX-Interaktion (wo Consumer HTMX nutzt)
7. Ersten Consumer integrieren (risk-hub: Schulungsmodul)
8. Gamification + SCORM in späteren Phasen
