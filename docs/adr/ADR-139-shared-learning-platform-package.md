---
status: "accepted"
date: 2026-03-12
amended: 2026-03-12
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-131-shared-backend-services.md", "ADR-111-private-package-distribution.md", "ADR-109-multi-tenancy-platform-standard.md", "ADR-134-module-monetization-strategy.md", "ADR-137-tenant-manager-rls.md"]
implementation_status: not_started
implementation_evidence: []
---

# ADR-139: Shared Learning Platform Package (iil-learnfw)

> **Amended 2026-03-12**: Offene Fragen entschieden — weasyprint, Gamification in-scope,
> SCORM-Support geplant, API-First (DRF), Video als Canvas-Erweiterung (post-v1),
> PyPI-Publish von Anfang an, optimale Dokumentation als Pflicht.
>
> **Review 2026-03-12**: DB-001 JSONField-Verstöße behoben (Attempt.answers → AttemptAnswer Model,
> Course.metadata entfernt), Enrollment-Model + Category-Model ergänzt, Monorepo-Mirror
> gestrichen (ADR-111 deprecated), Strukturinkonsistenz bereinigt, DRF als optional Extra,
> video content_type als reserved markiert. Content-Produktionsprozess ergänzt (Section 7):
> Authoring-Workflow, PPTX-Pipeline, Bulk-Import, Content-Versionierung.
>
> **Update 2026-03-12**: Authoring-Frontend (Section 8) und detaillierte Consumer-Integration
> (Section 9) ergänzt. Eigenes Authoring-UI mit HTMX (kein reines Django-Admin). Template-Override,
> Dashboard-Widgets, Auth-/Enrollment-Integration, vollständiges risk-hub Beispiel.
>
> **Tenant-Review 2026-03-12**: tenant_id (UUIDField, nullable, indexed) auf ALLE 22 Models
> durchgezogen (RLS-Pflicht, ADR-137). FileField upload_to mit Tenant-Prefix. is_global für
> plattformweite Kurse. Celery-Propagation via @with_tenant. django-tenancy als optionale Dep.
> Permission-Klassen mit Tenant-Check. Template-Tags tenant-aware. AUTH_USER_MODEL überall.

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

---

## 5. Package-Architektur

### 5.1 Modul-Übersicht

| Modul | Verantwortung | Dependencies |
|---|---|---|
| **iil_learnfw.courses** | Kursstruktur: Course → Chapter → Lesson, Category, Enrollment, Ordering | keine |
| **iil_learnfw.content** | Content-Backend-Abstraktion: MD-Renderer, PDF-Viewer-Meta, PPTX-Integration | `markdown` (optional) |
| **iil_learnfw.progress** | Fortschrittstracking: UserProgress, LessonCompletion, CourseCompletion | keine |
| **iil_learnfw.assessments** | Testmodule: Quiz, Question (MC/Freitext/Zuordnung), Attempt, Scoring | keine |
| **iil_learnfw.certificates** | Zertifikat-Generierung: WeasyPrint HTML→PDF, Verifizierungs-URL, QR-Code | `weasyprint` |
| **iil_learnfw.onboarding** | Onboarding-Flows: Pflicht-Kurse, Checklisten, First-Login-Detection | keine |
| **iil_learnfw.gamification** | Punkte, Badges, Streaks, Leaderboards, Achievement-System | keine |
| **iil_learnfw.scorm** | SCORM 1.2/2004 Import/Export, LMS-Interoperabilität (Enterprise) | `lxml` (optional) |
| **iil_learnfw.admin** | Django-Admin Integration: Kurs-Editor, Inhalts-Upload, Statistiken | keine |
| **iil_learnfw.api** | REST-API: DRF-Serializer + ViewSets, Tenant-scoped, OpenAPI-Doku | `djangorestframework`, `drf-spectacular` (optional Extra `api`) |

> **Hinweis**: Alle Module laufen unter einer einzigen Django-AppConfig (`IilLearnfwConfig`).
> Die Modul-Bezeichnungen sind logische Gruppierungen innerhalb der App, keine separaten Django-Apps.

### 5.2 Projektstruktur

```
learnfw/
├── src/iil_learnfw/
│   ├── __init__.py              # __version__ = "0.1.0"
│   ├── apps.py                  # IilLearnfwConfig
│   ├── settings.py              # IIL_LEARNFW dict mit typed defaults
│   ├── models/
│   │   ├── __init__.py
│   │   ├── course.py            # Category, Course, Chapter, Lesson, Enrollment
│   │   ├── content.py           # ContentBlock, ContentAttachment (PDF/MD/PPTX)
│   │   ├── progress.py          # UserProgress, LessonCompletion
│   │   ├── assessment.py        # Quiz, Question, Answer, Attempt, AttemptAnswer
│   │   ├── certificate.py       # CertificateTemplate, IssuedCertificate
│   │   ├── onboarding.py        # OnboardingFlow, OnboardingStep, UserOnboardingState
│   │   ├── gamification.py      # Badge, UserBadge, UserPoints, PointsTransaction
│   │   └── scorm.py             # SCORMPackage
│   ├── services/
│   │   ├── course_service.py    # Kurs-CRUD, Publishing, Ordering
│   │   ├── enrollment_service.py # enroll(), withdraw(), is_enrolled()
│   │   ├── progress_service.py  # Fortschritt tracken, Completion berechnen
│   │   ├── scoring_service.py   # Quiz-Auswertung, Bestanden/Nicht-Bestanden
│   │   ├── certificate_service.py # PDF-Generierung, Verifizierungs-Token
│   │   ├── content_service.py   # Content-Rendering (MD→HTML, PPTX-Meta)
│   │   ├── onboarding_service.py # Flow-Steuerung, Pflicht-Prüfung
│   │   └── gamification_service.py # award_points(), check_badges(), update_streak()
│   ├── content_backends/
│   │   ├── base.py              # AbstractContentBackend
│   │   ├── markdown_backend.py  # MD → HTML Rendering
│   │   ├── pdf_backend.py       # PDF-Metadaten, Viewer-URL
│   │   └── pptx_backend.py      # PPTX-Integration (iil-pptxfw / pptx-hub API)
│   ├── signals.py               # Auto-Award on lesson_complete, quiz_passed
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
│   │   ├── course_views.py      # Kurs-Liste, Detail, Lektion-Ansicht (Lernende)
│   │   ├── assessment_views.py  # Quiz starten, beantworten, Ergebnis
│   │   ├── certificate_views.py # Download, Verify-Endpoint
│   │   ├── onboarding_views.py  # Onboarding-Wizard, Fortschritt
│   │   ├── gamification_views.py # Leaderboard, Badge-Übersicht, Profil
│   │   └── authoring/           # Authoring-Frontend (Content-Erstellung)
│   │       ├── dashboard.py     # Autoren-Dashboard: Meine Kurse, Statistiken
│   │       ├── course_editor.py # Kursstruktur: Chapters/Lessons Drag&Drop
│   │       ├── lesson_editor.py # Lektion bearbeiten: MD-Editor, PDF/PPTX-Upload
│   │       ├── quiz_editor.py   # Quiz-Builder: Fragen, Antworten, Scoring
│   │       ├── review_views.py  # Review-Workflow: Approve/Reject mit Kommentar
│   │       ├── bulk_import.py   # Bulk-Upload UI mit Fortschrittsanzeige
│   │       └── analytics.py     # Kurs-Statistiken: Completion-Rate, Quiz-Ergebnisse
│   ├── templates/iil_learnfw/   # Default-Templates (überschreibbar)
│   │   ├── learn/               # Lernende-Templates
│   │   │   ├── course_list.html
│   │   │   ├── course_detail.html
│   │   │   ├── lesson.html
│   │   │   ├── quiz.html
│   │   │   ├── quiz_result.html
│   │   │   ├── certificate.html
│   │   │   ├── leaderboard.html
│   │   │   ├── badges.html
│   │   │   └── onboarding/
│   │   │       ├── wizard.html
│   │   │       └── checklist.html
│   │   ├── authoring/           # Autoren-Templates
│   │   │   ├── dashboard.html
│   │   │   ├── course_editor.html
│   │   │   ├── lesson_editor.html   # MD-WYSIWYG, PDF/PPTX-Upload
│   │   │   ├── quiz_editor.html
│   │   │   ├── review_detail.html
│   │   │   ├── review_list.html
│   │   │   ├── bulk_import.html
│   │   │   └── analytics.html
│   │   ├── certificate_pdf.html # WeasyPrint HTML→PDF Template
│   │   ├── widgets/             # Einbettbare Widgets für Consumer-Dashboards
│   │   │   ├── progress_card.html   # Fortschritts-Widget
│   │   │   ├── next_lesson.html     # Nächste Lektion Widget
│   │   │   └── badge_showcase.html  # Letzte Badges Widget
│   │   └── _base.html           # Basis-Template (Consumer überschreibt dieses)
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
│   ├── test_enrollment_service.py
│   ├── test_gamification_service.py
│   ├── test_scorm_importer.py
│   ├── test_content_backends.py
│   ├── test_api.py
│   └── test_views.py
├── docs/                        # MkDocs Dokumentation
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

> **Tenant-Konvention (ADR-137)**:
> - **Alle** Models haben `tenant_id: UUIDField(null=True, blank=True, db_index=True)`
> - Nullable für Single-Tenant-Consumer (`TENANT_AWARE=False` → tenant_id bleibt NULL)
> - Multi-Tenant-Consumer: Middleware setzt tenant_id automatisch via TenantManager
> - PostgreSQL RLS erfordert `tenant_id` auf **jeder Tabelle** — keine FK-Traversals
> - `user`-FKs referenzieren immer `settings.AUTH_USER_MODEL`
> - FileFields nutzen `upload_to=tenant_upload_path` für Storage-Isolation

```python
# Tenant-isolierter Upload-Pfad (alle FileFields)
def tenant_upload_path(instance, filename):
    tid = instance.tenant_id or "shared"
    return f"tenants/{tid}/learnfw/{instance.__class__.__name__.lower()}/{filename}"
```

```
Category
├── name, slug, icon
├── parent (FK self, optional — Baumstruktur)
└── tenant_id

Course
├── title, slug, description, thumbnail
├── category (FK Category, optional)
├── status: draft | published | archived
├── is_mandatory: bool (für Onboarding)
├── required_for_certificate: bool
├── is_global: bool (default=False — True = sichtbar für ALLE Tenants)
├── created_by (FK User)
├── ordering: int
└── tenant_id

Chapter
├── course (FK)
├── title, ordering, description
└── tenant_id

Enrollment
├── user (FK), course (FK)
├── enrolled_at, enrolled_by (FK User, optional — Admin-Zuweisung)
├── status: active | completed | withdrawn
└── tenant_id

Lesson
├── chapter (FK)
├── title, ordering
├── content_type: markdown | pdf | pptx | external_url (video: reserved, post-v1)
├── content_text: TextField (für MD)
├── content_file: FileField (upload_to=tenant_upload_path)
├── content_url: URLField (für externe Inhalte)
├── estimated_duration: DurationField
├── is_downloadable: bool
└── tenant_id

Quiz (Assessment)
├── course (FK, optional — kann kursübergreifend sein)
├── chapter (FK, optional)
├── title, passing_score (z.B. 80%)
├── max_attempts: int (0 = unbegrenzt)
├── time_limit: DurationField (optional)
├── shuffle_questions: bool
└── tenant_id

Question
├── quiz (FK)
├── question_type: multiple_choice | single_choice | free_text | matching
├── text, explanation (nach Beantwortung sichtbar)
├── points: int, ordering
└── tenant_id

Answer (für MC/SC)
├── question (FK)
├── text, is_correct: bool, ordering
└── tenant_id

Attempt
├── quiz (FK), user (FK)
├── started_at, completed_at
├── score, passed: bool
└── tenant_id

AttemptAnswer
├── attempt (FK), question (FK)
├── selected_answer (FK Answer, nullable — für MC/SC)
├── free_text: TextField (für Freitext-Antworten)
├── is_correct: bool, points_awarded: int
└── tenant_id

UserProgress
├── user (FK), lesson (FK)
├── status: not_started | in_progress | completed
├── completed_at, time_spent
└── tenant_id

CertificateTemplate
├── name, html_template (für PDF-Rendering)
├── logo: FileField (upload_to=tenant_upload_path)
├── signature_image: FileField (upload_to=tenant_upload_path)
├── valid_for: DurationField (optional, Ablaufdatum)
└── tenant_id

IssuedCertificate
├── PK: BigAutoField (DB-001)
├── user (FK), course (FK), template (FK)
├── issued_at, expires_at
├── verification_token: UUIDField (indexed, unique — Non-PK, für öffentliche Verifizierung)
├── pdf_file: FileField (upload_to=tenant_upload_path)
└── tenant_id

OnboardingFlow
├── name, is_active: bool
├── trigger: first_login | role_change | manual
└── tenant_id

OnboardingStep
├── flow (FK), course (FK, optional), quiz (FK, optional)
├── title, description
├── is_required: bool, ordering
└── tenant_id

UserOnboardingState
├── user (FK), flow (FK), step (FK)
├── status: pending | in_progress | completed | skipped
├── completed_at
└── tenant_id

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
├── user (FK)
├── total_points: int
├── current_streak: int (Tage), longest_streak: int
└── tenant_id

PointsTransaction
├── user (FK)
├── points: int, reason: str
├── source_type: lesson | quiz | badge | manual
├── created_at
└── tenant_id

SCORMPackage
├── course (FK)
├── scorm_version: 1.2 | 2004
├── package_file: FileField (upload_to=tenant_upload_path, ZIP)
├── manifest: JSONField (DB-001 Ausnahme: genuinely unstructured external XML payload)
├── imported_at
└── tenant_id
```

> **is_global-Logik**: Kurse mit `is_global=True` sind für alle Tenants sichtbar.
> QuerySet: `Course.objects.filter(Q(tenant_id=ctx.tenant_id) | Q(is_global=True))`
> Globale Kurse werden zentral gepflegt (tenant_id=NULL oder Plattform-Tenant).

> **Verify-Endpoint**: `/learn/verify/{token}/` ist öffentlich (kein Tenant-Middleware).
> Response enthält nur: Zertifikat gültig/ungültig, Ausstellungsdatum, Name. Keine internen Tenant-Daten.

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

## 7. Content-Produktionsprozess

Der Produktionsprozess beschreibt, wie Lerninhalte erstellt, geprüft, versioniert und veröffentlicht werden.

### 7.1 Authoring-Workflow (Content Lifecycle)

Jede Lesson und jeder Kurs durchläuft einen definierten Lifecycle:

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌───────────┐
│  DRAFT  │────▶│ IN_REVIEW│────▶│ APPROVED │────▶│ PUBLISHED │
└─────────┘     └──────────┘     └──────────┘     └───────────┘
     ▲               │                                   │
     │               ▼                                   ▼
     │          ┌──────────┐                      ┌───────────┐
     └──────────│ REJECTED │                      │ ARCHIVED  │
                └──────────┘                      └───────────┘
```

| Status | Beschreibung | Sichtbarkeit |
|---|---|---|
| **draft** | Autor erstellt/bearbeitet Content | Nur Autor + Admin |
| **in_review** | Zur Prüfung eingereicht | Autor + Reviewer + Admin |
| **rejected** | Reviewer hat Änderungen angefordert → zurück an Autor | Nur Autor + Admin |
| **approved** | Inhaltlich freigegeben, bereit zur Veröffentlichung | Admin |
| **published** | Live für Lernende sichtbar | Alle (Enrollment-abhängig) |
| **archived** | Nicht mehr aktiv, historisch erhalten | Admin |

#### Rollen im Authoring

| Rolle | Rechte |
|---|---|
| **Content-Autor** | Erstellen, bearbeiten (draft/rejected), zur Review einreichen |
| **Content-Reviewer** | Approve/Reject mit Kommentar, Vorschau |
| **Kurs-Admin** | Alle Rechte + Publish/Archive, Kursstruktur, Enrollment |
| **Tenant-Admin** | Alle Rechte + Benutzerverwaltung, Reporting |

### 7.2 Content-Quellen & Produktionspipelines

```
                    ┌──────────────────────────────┐
                    │     Content-Quellen           │
                    └──────────────────────────────┘
                         │         │         │
                ┌────────┘         │         └────────┐
                ▼                  ▼                   ▼
        ┌──────────────┐  ┌──────────────┐   ┌──────────────┐
        │   Markdown    │  │  PDF-Upload   │   │  PPTX-Hub    │
        │   (Editor)    │  │  (Datei)      │   │  (Pipeline)  │
        └──────┬───────┘  └──────┬───────┘   └──────┬───────┘
               │                  │                   │
               ▼                  ▼                   ▼
        ┌──────────────────────────────────────────────────┐
        │              Lesson (content_type)                │
        │   markdown | pdf | pptx | external_url           │
        └──────────────────────────────────────────────────┘
               │                  │                   │
               ▼                  ▼                   ▼
        ┌──────────────────────────────────────────────────┐
        │           Content-Backend (Rendering)            │
        └──────────────────────────────────────────────────┘
```

#### a) Markdown-Produktion

- **Inline-Editor**: Rich-Text-Editor im Admin/Frontend (z.B. django-markdownx oder SimpleMDE)
- **Import**: MD-Dateien hochladen → `content_text` befüllen
- **Rendering**: `MarkdownContentBackend` → HTML mit Tables, Code-Blöcken, Bildern

#### b) PDF-Produktion

- **Direkter Upload**: PDF-Dateien per Admin oder API hochladen → `content_file`
- **Generierung aus MD**: `weasyprint` rendert Markdown/HTML → PDF (für Offline-Download)
- **Externe Quellen**: URL zu bestehenden PDFs (Handbücher, Normen, Richtlinien)

#### c) PPTX-Produktionspipeline (pptx-hub Integration)

Die zentrale Pipeline für PPTX-basierte Lerninhalte:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ PPTX-Vorlage│────▶│  pptx-hub   │────▶│  learnfw    │────▶│  Lesson     │
│ (Template)  │     │  Rendering  │     │  Import     │     │ (published) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                          │
                    ┌─────┴─────┐
                    ▼           ▼
              HTML-Slides   PDF-Export
              (pro Slide)   (Handout)
```

1. **PPTX erstellen**: Autor erstellt Präsentation (PowerPoint, Google Slides, iil-pptxfw)
2. **Upload**: PPTX-Datei wird in learnfw hochgeladen (Admin oder API)
3. **Auto-Processing** (Celery-Task):
   - Slide-Count ermitteln, Thumbnail generieren
   - Optional: Jeder Slide → eigene Lektion (Auto-Split)
   - Optional: Speaker Notes → Markdown-Begleittext
   - PDF-Handout generieren (via pptx-hub oder weasyprint)
4. **Review**: Content-Reviewer prüft generierte Lektionen
5. **Publish**: Freigabe → Lernende sehen Slides als interaktive Präsentation

```python
# settings.py
IIL_LEARNFW = {
    "PPTX_AUTO_SPLIT": True,       # Jeder Slide → eigene Lektion
    "PPTX_EXTRACT_NOTES": True,    # Speaker Notes → lesson.content_text
    "PPTX_GENERATE_PDF": True,     # Auto-PDF-Handout
    "PPTX_THUMBNAIL_SLIDE": 1,     # Slide-Nr. für Kurs-Thumbnail
}
```

### 7.3 Bulk-Import

Für große Content-Mengen (z.B. bestehende Schulungsunterlagen migrieren):

```python
# Management Command (--tenant ist Pflicht bei TENANT_AWARE=True)
python manage.py import_lessons \
    --tenant "org-uuid-or-slug" \  # Pflicht: Ziel-Tenant (UUID oder Slug)
    --course "Versicherungsgrundlagen" \
    --source /path/to/content/ \
    --format auto \               # auto-detect: .md, .pdf, .pptx
    --chapter-per-folder \         # Unterordner → Chapters
    --status draft                 # Alle als Draft importieren

# API-Endpoint (POST /api/v1/courses/{id}/bulk-import/)
# tenant_id wird automatisch aus Request-Context (Middleware) gesetzt
{
    "files": [...],                # Multipart Upload
    "chapter_strategy": "per_folder",
    "auto_detect_format": true,
    "initial_status": "draft"
}
```

> **Celery-Tasks**: Async-Processing (PPTX Auto-Split, Bulk-Import, PDF-Generierung) propagiert
> den Tenant-Context via `@with_tenant`-Decorator (django-tenancy, ADR-137). Der Decorator
> setzt `set_tenant()` + `set_db_tenant()` vor Task-Ausführung und `clear_context()` danach.

**Unterstützte Formate:**

| Format | Erkennung | Verarbeitung |
|---|---|---|
| `.md` | Extension | → `content_text`, content_type=markdown |
| `.pdf` | Extension + Magic Bytes | → `content_file`, content_type=pdf |
| `.pptx` | Extension + Magic Bytes | → `content_file`, content_type=pptx, Auto-Processing |
| Ordner | Directory | → Chapter (mit Dateien als Lektionen, sortiert nach Dateiname) |

### 7.4 Content-Versionierung

Wenn Content aktualisiert wird, muss der Lernfortschritt konsistent bleiben:

```
ContentVersion
├── lesson (FK)
├── version: int (auto-increment)
├── content_text: TextField (Snapshot)
├── content_file: FileField (Snapshot)
├── created_at, created_by (FK User)
├── change_summary: CharField
└── is_current: bool
```

**Regeln:**

- **Minor-Update** (Tippfehler, Formulierung): Bestehender Fortschritt bleibt erhalten
- **Major-Update** (inhaltliche Änderung): Admin entscheidet ob Fortschritt zurückgesetzt wird
- **Quiz-Änderung**: Wenn Fragen geändert werden, werden bestehende Attempts **nicht** invalidiert — nur neue Attempts nutzen die neue Version
- **Rollback**: Admin kann auf vorherige Version zurücksetzen

```python
IIL_LEARNFW = {
    "CONTENT_VERSIONING": True,           # Versionierung aktivieren
    "KEEP_VERSIONS": 10,                  # Max. Anzahl Versionen pro Lesson
    "MAJOR_UPDATE_RESETS_PROGRESS": False, # Default: Fortschritt beibehalten
}
```

### 7.5 Ergänzende Datenmodell-Erweiterungen

```
ContentVersion (Versionierung)
├── lesson (FK)
├── version: int
├── content_text, content_file (Snapshot, upload_to=tenant_upload_path)
├── created_at, created_by (FK User)
├── change_summary: CharField
├── is_current: bool
└── tenant_id

ContentReview (Authoring-Workflow)
├── lesson (FK) oder course (FK)
├── reviewer (FK User)
├── status: pending | approved | rejected
├── comment: TextField
├── reviewed_at
└── tenant_id

BulkImportJob (Async-Import)
├── course (FK), tenant_id
├── status: pending | processing | completed | failed
├── source_description: CharField
├── total_files, processed_files, failed_files: int
├── error_log: TextField
├── created_at, created_by (FK User)
└── completed_at
```

---

## 8. Authoring-Frontend (Content-Management-UI)

Das Package liefert ein eigenes Authoring-Frontend mit — kein reines Django-Admin, sondern
eine dedizierte UI für Content-Autoren, Reviewer und Kurs-Admins.

### 8.1 URL-Struktur (Authoring)

```
/learn/authoring/                          # Autoren-Dashboard
/learn/authoring/kurse/                    # Meine Kurse (Autor-gefiltert)
/learn/authoring/kurse/neu/                # Neuen Kurs anlegen
/learn/authoring/kurse/<slug>/edit/        # Kursstruktur-Editor (Chapters, Lessons)
/learn/authoring/kurse/<slug>/analytics/   # Kurs-Statistiken
/learn/authoring/lektion/<id>/edit/        # Lektion bearbeiten (MD-Editor / Upload)
/learn/authoring/quiz/<id>/edit/           # Quiz-Builder
/learn/authoring/review/                   # Review-Queue (offene Reviews)
/learn/authoring/review/<id>/              # Review-Detail mit Approve/Reject
/learn/authoring/import/                   # Bulk-Import UI
```

### 8.2 Autoren-Dashboard

Das Dashboard zeigt dem eingeloggten Autor:

```
┌─────────────────────────────────────────────────────────────┐
│  📚 Meine Kurse                              [+ Neuer Kurs] │
├─────────────────────────────────────────────────────────────┤
│  Versicherungsrecht       │ 12 Lektionen │ published  │ ✏️  │
│  Risikomanagement Basics  │  8 Lektionen │ draft      │ ✏️  │
│  Compliance 2026          │  0 Lektionen │ draft      │ ✏️  │
├─────────────────────────────────────────────────────────────┤
│  📋 Offene Reviews (3)                                      │
│  → "Schadensregulierung" von M. Müller — wartet auf Review  │
│  → "Datenschutz-Update" von S. Schmidt — wartet auf Review  │
├─────────────────────────────────────────────────────────────┤
│  📊 Statistiken                                             │
│  Aktive Lernende: 142  │  Ø Completion: 67%  │  Ø Score: 78%│
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Kursstruktur-Editor

Drag&Drop-Editor für die Kursstruktur mit HTMX-Interaktion:

```
┌─────────────────────────────────────────────────────────────┐
│  Kurs: Versicherungsrecht                    [Vorschau] [⚙] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📁 Kapitel 1: Grundlagen                          [↕] [+] │
│    ├── 📄 1.1 Einführung (Markdown)        draft    [✏] [↕] │
│    ├── 📄 1.2 Vertragstypen (PDF)          published[✏] [↕] │
│    └── 📄 1.3 Pflichtversicherung (PPTX)   in_review[✏] [↕] │
│                                                             │
│  📁 Kapitel 2: Schadenregulierung                  [↕] [+] │
│    ├── 📄 2.1 Schadenmeldung (Markdown)    draft    [✏] [↕] │
│    └── 📝 Quiz: Grundlagen-Check (5 Fragen) draft  [✏] [↕] │
│                                                             │
│  [+ Kapitel hinzufügen]                                     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Status: draft  │  [Zur Review einreichen]  │  [Publizieren]│
└─────────────────────────────────────────────────────────────┘
```

### 8.4 Lektions-Editor

Je nach `content_type` unterschiedliche Editoren:

| Content-Type | Editor | Funktionen |
|---|---|---|
| **markdown** | WYSIWYG + Raw-MD Toggle | Formatierung, Bilder, Tabellen, Code-Blöcke, Live-Preview |
| **pdf** | Datei-Upload + Metadaten | PDF hochladen, Titel/Beschreibung, Seitenzahl-Anzeige |
| **pptx** | Datei-Upload + Auto-Processing | PPTX hochladen, Slide-Preview, Auto-Split-Option, Notes-Extraktion |
| **external_url** | URL-Input + Preview | URL eingeben, Embed-Preview, Beschreibung |

```
┌─────────────────────────────────────────────────────────────┐
│  Lektion bearbeiten: 1.1 Einführung          [Markdown ▼]  │
├─────────────────────────────────────────────────────────────┤
│  Titel: [Einführung in das Versicherungsrecht            ]  │
│  Geschätzte Dauer: [15 Min ▼]    Downloadbar: [✓]          │
├─────────────────────────────────────────────────────────────┤
│  ┌─── Editor ──────────────┐  ┌─── Preview ──────────────┐ │
│  │ # Einführung             │  │ Einführung               │ │
│  │                          │  │                          │ │
│  │ Das Versicherungsrecht   │  │ Das Versicherungsrecht   │ │
│  │ regelt die **Rechte**    │  │ regelt die Rechte und    │ │
│  │ und **Pflichten** ...    │  │ Pflichten ...            │ │
│  │                          │  │                          │ │
│  │ [B] [I] [H] [📷] [📎]   │  │                          │ │
│  └──────────────────────────┘  └──────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [Speichern (Draft)]  [Zur Review einreichen]  [Abbrechen] │
└─────────────────────────────────────────────────────────────┘
```

### 8.5 Quiz-Builder

Visueller Quiz-Editor mit Fragen-Typen:

- **Multiple Choice**: Mehrere Antworten, korrekte markieren, Erklärung pro Antwort
- **Single Choice**: Eine korrekte Antwort
- **Freitext**: Musterantwort + Schlüsselwörter für Auto-Scoring
- **Zuordnung**: Drag&Drop Paare bilden

```
┌─────────────────────────────────────────────────────────────┐
│  Quiz: Grundlagen-Check                  Bestehensgrenze: 80%│
├─────────────────────────────────────────────────────────────┤
│  Frage 1/5 [Multiple Choice ▼]                 [2 Punkte]  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Welche Versicherungen sind Pflichtversicherungen?    │   │
│  └──────────────────────────────────────────────────────┘   │
│  [✓] Kfz-Haftpflicht                                       │
│  [ ] Hausratversicherung                                    │
│  [✓] Krankenversicherung                                    │
│  [ ] Reiseversicherung                         [+ Antwort]  │
│                                                             │
│  Erklärung: [Kfz-Haftpflicht und Krankenversicherung ...]  │
├─────────────────────────────────────────────────────────────┤
│  [+ Frage hinzufügen]   │   [Vorschau]   │   [Speichern]  │
└─────────────────────────────────────────────────────────────┘
```

### 8.6 Technische Umsetzung

- **HTMX**: Alle Interaktionen (Drag&Drop, Save, Status-Wechsel) per HTMX — kein SPA, kein React
- **Markdown-Editor**: [EasyMDE](https://github.com/Ionaru/easy-markdown-editor) oder django-markdownx
- **Drag&Drop**: [SortableJS](https://sortablejs.github.io/Sortable/) für Kapitel/Lektions-Reihenfolge
- **Datei-Upload**: Dropzone.js oder nativer HTMX File-Upload mit Fortschrittsanzeige
- **Permissions**: Eigene Permission-Klassen (`IsAuthor`, `IsReviewer`, `IsCourseAdmin`)
- **Basis-Template**: `_base.html` — Consumer überschreibt dieses für eigenes Branding/Layout

```python
# Permissions in views/authoring/
from django_tenancy.context import get_context

class IsAuthorOrAdmin(permissions.BasePermission):
    """Nur Autoren (eigene Kurse) oder Kurs-Admins — mit Tenant-Check."""
    def has_object_permission(self, request, view, obj):
        # Tenant-Isolation: Objekt muss zum aktuellen Tenant gehören
        ctx = get_context()
        if ctx.tenant_id and hasattr(obj, 'tenant_id') and obj.tenant_id != ctx.tenant_id:
            return False
        return obj.created_by == request.user or request.user.has_perm("iil_learnfw.manage_courses")
```

### 8.7 Authoring-Settings

```python
IIL_LEARNFW = {
    "AUTHORING_ENABLED": True,              # Authoring-Frontend aktivieren
    "AUTHORING_URL_PREFIX": "authoring/",   # URL-Prefix innerhalb des learn-Pfads
    "AUTHORING_ROLES": {
        "author": "iil_learnfw.author",     # Django Permission
        "reviewer": "iil_learnfw.reviewer",
        "course_admin": "iil_learnfw.manage_courses",
    },
    "MARKDOWN_EDITOR": "easymde",           # "easymde" | "markdownx" | "textarea"
    "ENABLE_REVIEW_WORKFLOW": True,         # False = direkt Draft→Published (kein Review)
    "AUTO_SAVE_INTERVAL": 30,              # Auto-Save alle 30 Sekunden (HTMX)
}
```

---

## 9. Consumer-Integration

### 9.1 Installation

```bash
# Minimal (Kurse + Fortschritt — nur Template-Views)
pip install iil-learnfw

# Mit REST-API (DRF + OpenAPI)
pip install "iil-learnfw[api]"

# Mit Zertifikat-PDF-Generierung
pip install "iil-learnfw[certificates]"

# Mit PPTX-Rendering
pip install "iil-learnfw[pptx]"

# Vollausstattung
pip install "iil-learnfw[all]"
```

### 9.2 Django-Settings (Consumer)

```python
INSTALLED_APPS = [
    "iil_learnfw",
    ...
]

# urls.py
urlpatterns = [
    path("schulungen/", include("iil_learnfw.urls")),
    ...
]

# Konfiguration (alle optional — sinnvolle Defaults)
IIL_LEARNFW = {
    "COURSE_MODEL": None,           # Custom Course-Model (optional Proxy)
    "CERTIFICATE_TEMPLATE_DIR": "certificates/",
    "PASSING_SCORE_DEFAULT": 80,
    "MAX_ATTEMPTS_DEFAULT": 3,
    "CONTENT_BACKENDS": {
        "markdown": "iil_learnfw.content_backends.markdown_backend.MarkdownContentBackend",
        "pdf": "iil_learnfw.content_backends.pdf_backend.PDFContentBackend",
        "pptx": "iil_learnfw.content_backends.pptx_backend.PPTXContentBackend",
    },
    "PPTX_MODE": "direct",
    "ONBOARDING_ENABLED": True,
    "AUTHORING_ENABLED": True,
    "CERTIFICATE_VERIFY_URL": "/schulungen/verify/{token}/",
    "TENANT_AWARE": True,
}
```

### 9.3 URL-Struktur im Consumer (Beispiel: kiohnerisiko.de)

```
kiohnerisiko.de (risk-hub)
│
├── /                                    # risk-hub Startseite
│   └── [Fortschritts-Widget]            # {% learnfw_progress_card %}
│   └── [Nächste Lektion Widget]         # {% learnfw_next_lesson %}
│
├── /schulungen/                         # ← iil_learnfw.urls
│   ├── /schulungen/kurse/               # Kursübersicht (Tenant-gefiltert)
│   ├── /schulungen/kurse/versicherungsrecht/  # Kursdetail + Kapitelstruktur
│   ├── /schulungen/lektion/3/           # Lektion lesen (MD/PDF/PPTX gerendert)
│   ├── /schulungen/quiz/5/              # Quiz bearbeiten
│   ├── /schulungen/quiz/5/ergebnis/     # Quiz-Ergebnis
│   ├── /schulungen/fortschritt/         # Persönlicher Fortschritt
│   ├── /schulungen/zertifikate/         # Meine Zertifikate
│   ├── /schulungen/verify/<token>/      # Öffentliche Zertifikat-Verifizierung
│   ├── /schulungen/rangliste/           # Leaderboard (Gamification)
│   ├── /schulungen/badges/              # Badge-Übersicht
│   │
│   ├── /schulungen/authoring/           # Autoren-Frontend (nur mit Berechtigung)
│   │   ├── .../kurse/                   # Kurs-Management
│   │   ├── .../lektion/<id>/edit/       # Lektions-Editor
│   │   ├── .../review/                  # Review-Queue
│   │   └── .../import/                  # Bulk-Import
│   │
│   └── /schulungen/api/v1/             # REST-API (optional, mit [api] Extra)
│       ├── /courses/
│       ├── /lessons/
│       ├── /progress/
│       └── /certificates/
│
└── /admin/                              # Django Admin (Superuser)
```

### 9.4 Template-Override & Branding

learnfw liefert ein `_base.html`, das der Consumer **überschreibt** um eigenes Layout/Branding einzubinden:

```html
{# risk-hub/templates/iil_learnfw/_base.html #}
{# Überschreibt das Default-Template aus dem Package #}
{% extends "base.html" %}
{# base.html ist das risk-hub Haupt-Layout mit Navigation, Footer, CSS #}

{% block content %}
  <div class="container mx-auto px-4 py-8">
    {% block learnfw_content %}{% endblock %}
  </div>
{% endblock %}
```

Damit erbt jede learnfw-Seite automatisch das **risk-hub Design** (Navbar, Footer, CSS, Branding).

### 9.5 Dashboard-Widgets (Template-Tags)

learnfw stellt Template-Tags bereit, die der Consumer auf seiner Startseite einbetten kann.
Alle Tags sind **tenant-aware**: Sie lesen den Tenant-Context aus der Middleware und filtern
automatisch — auch wenn ein User Mitglied mehrerer Tenants ist.

```html
{# risk-hub/templates/dashboard.html #}
{% load learnfw_tags %}

<div class="grid grid-cols-3 gap-4">
  {# Fortschritts-Karte: "3 von 12 Kursen abgeschlossen" (aktueller Tenant) #}
  {% learnfw_progress_card user=request.user %}

  {# Nächste Lektion: "Weiter mit: Schadensregulierung, Kapitel 3" (aktueller Tenant) #}
  {% learnfw_next_lesson user=request.user %}

  {# Badge-Showcase: Letzte 3 verdiente Badges (aktueller Tenant) #}
  {% learnfw_badge_showcase user=request.user limit=3 %}
</div>
```

> **Tenant-Scoping in Tags**: Intern nutzen alle Tags `TenantManager.get_queryset()` —
> der auto-filter greift über den Request-Context der Middleware. Kein explizites
> `tenant_id`-Argument nötig.

### 9.6 Navigation-Integration

Der Consumer bindet "Schulungen" in seine Hauptnavigation ein:

```html
{# risk-hub/templates/includes/navbar.html #}
{% load learnfw_tags %}
<nav>
  <a href="{% url 'iil_learnfw:course_list' %}">
    Schulungen
    {% learnfw_unread_count user=request.user as unread %}
    {% if unread %}<span class="badge">{{ unread }}</span>{% endif %}
  </a>
</nav>
```

### 9.7 Auth-Integration

- **Kein separater Login**: learnfw nutzt `request.user` (`settings.AUTH_USER_MODEL`) des Consumer-Projekts
- **Permissions**: Über Django-Permissions (`iil_learnfw.author`, `iil_learnfw.reviewer`, `iil_learnfw.manage_courses`)
- **Tenant-Scoping**: Automatisch via TenantManager (ADR-137) — Lernende sehen nur Kurse ihres Mandanten
- **Leaderboard-Isolation**: Rangliste zeigt nur Ranking **innerhalb des eigenen Mandanten** (UserPoints.tenant_id)
- **Enrollment**: Offene Kurse vs. Zuweisung durch Admin vs. Selbst-Einschreibung (konfigurierbar)

```python
IIL_LEARNFW = {
    "ENROLLMENT_MODE": "open",  # "open" | "admin_only" | "self_enroll"
    # open: Alle veröffentlichten Kurse sichtbar, kein Enrollment nötig
    # admin_only: Nur Admin kann Benutzer zu Kursen zuweisen
    # self_enroll: Benutzer können sich selbst einschreiben (Button auf Kursseite)
}
```

### 9.8 Vollständiges Beispiel: risk-hub (kiohnerisiko.de)

```python
# risk-hub/config/settings/base.py
INSTALLED_APPS = [
    ...
    "iil_learnfw",
]

IIL_LEARNFW = {
    "TENANT_AWARE": True,
    "ONBOARDING_ENABLED": True,
    "AUTHORING_ENABLED": True,
    "ENROLLMENT_MODE": "admin_only",        # Versicherungskurse werden zugewiesen
    "CERTIFICATE_TEMPLATE_DIR": "risk_hub/certificates/",
    "CONTENT_BACKENDS": {
        "markdown": "iil_learnfw.content_backends.markdown_backend.MarkdownContentBackend",
        "pdf": "iil_learnfw.content_backends.pdf_backend.PDFContentBackend",
    },
    "PPTX_AUTO_SPLIT": True,
    "ENABLE_REVIEW_WORKFLOW": True,         # 4-Augen-Prinzip für Versicherungsinhalte
}

# risk-hub/config/urls.py
urlpatterns = [
    path("schulungen/", include("iil_learnfw.urls")),
    ...
]
```

```html
{# risk-hub/templates/iil_learnfw/_base.html #}
{% extends "base.html" %}
{% block content %}
  <div class="container mx-auto px-4 py-8">
    <nav class="text-sm text-gray-500 mb-4">
      <a href="/">Start</a> › <a href="{% url 'iil_learnfw:course_list' %}">Schulungen</a>
      {% block learnfw_breadcrumb %}{% endblock %}
    </nav>
    {% block learnfw_content %}{% endblock %}
  </div>
{% endblock %}
```

---

## 10. Rollout-Plan

| Phase | Scope | Deliverables |
|---|---|---|
| **Phase 1** | Courses + Content + Progress + API | v0.1.0 — Kursstruktur, MD/PDF-Backend, Fortschrittstracking, API, PyPI-Publish |
| **Phase 2** | Assessments + Scoring | v0.2.0 — Quizzes, MC/Freitext, Scoring, Attempt-Tracking |
| **Phase 3** | Authoring-Frontend | v0.3.0 — Kurs-Editor, Lektions-Editor, Quiz-Builder, Review-Workflow, Bulk-Import |
| **Phase 4** | Certificates (WeasyPrint) | v0.4.0 — HTML→PDF-Zertifikate, Verifizierungs-URL, QR-Code |
| **Phase 5** | Onboarding | v0.5.0 — Onboarding-Flows, Pflicht-Kurse, Checklisten |
| **Phase 6** | Gamification | v0.6.0 — Punkte, Badges, Streaks, Leaderboards |
| **Phase 7** | PPTX-Integration | v0.7.0 — PPTX-Backend, pptx-hub API-Anbindung, Auto-Processing |
| **Phase 8** | SCORM | v0.8.0 — SCORM 1.2/2004 Import/Export (Enterprise) |
| **Phase 9** | Consumer-Integration | v1.0.0 — Erster Hub (risk-hub) LIVE, Templates, Widgets, Doku komplett |

**Querschnitt (ab Phase 1):**
- PyPI-Publish bei jedem Minor-Release
- MkDocs-Dokumentation mitgeführt (docs/)
- OpenAPI-Schema via drf-spectacular
- CI: ruff + pytest + bandit (Python 3.11+3.12)

---

## 11. Risiken & Mitigationen

- **Over-Engineering**: YAGNI — Phase 1 startet minimal (Kurse + MD/PDF). Weitere Module nur bei konkretem Bedarf.
- **Multi-Tenancy-Komplexität**: Nutzung des bewährten TenantManager-Patterns (ADR-137). `tenant_id` auf **allen** 22 Models (RLS-Pflicht). Nullable für Single-Tenant-Consumer.
- **Celery-Tenant-Propagation**: Async-Tasks (PPTX-Processing, Bulk-Import, PDF-Generierung) nutzen `@with_tenant`-Decorator aus django-tenancy. Der Decorator propagiert `tenant_id` + `set_db_tenant()` in den Worker-Context und ruft `clear_context()` nach Abschluss auf. Ohne diesen Decorator wäre der Tenant-Context im Worker nicht gesetzt → unscoped QuerySets.
- **Content-Storage**: FileField mit `upload_to=tenant_upload_path` für Tenant-isolierte Pfade (`tenants/{tid}/learnfw/...`). Bei Bedarf S3-Backend via Django Storages. URL-Guessing-Schutz durch Tenant-Prefix.
- **Zertifikat-Fälschung**: Signierter Verification-Token (HMAC). Öffentliche Verify-URL exponiert nur: gültig/ungültig, Datum, Name — keine internen Tenant-Daten.
- **Performance**: Fortschrittstracking mit Bulk-Updates. Content-Rendering gecacht. Quiz-Scoring synchron (einfach genug).

---

## 12. Entschiedene Fragen

| # | Frage | Entscheidung | Begründung |
|---|---|---|---|
| 1 | **Zertifikat-PDF-Engine** | `weasyprint` | HTML→PDF, flexibel, Template-basiert, CSS-Support. Heavy Dependency akzeptabel als optional Extra. |
| 2 | **Video-Content** | Post-v1 — Canvas oder eigene Lösung | Video ist komplexes Thema (Hosting, Streaming, DRM). Später als Canvas-LTI-Integration oder eigenes Video-Backend. |
| 3 | **Gamification** | In-scope (Phase 5, v0.5.0) | Motivation + Engagement sind Kern-Feature einer Lernplattform. Punkte/Badges/Streaks als eigenes Submodul. |
| 4 | **SCORM** | Ja (Phase 7, v0.7.0) | Enterprise-Kunden (Firmen) erwarten SCORM-Kompatibilität. Import/Export für LMS-Interoperabilität. |
| 5 | **API-First** | Ja, DRF von Phase 1 an | Tenant-fähige API ermöglicht Headless-Consumer, Mobile-Apps, externe Integrationen. OpenAPI-Doku via drf-spectacular. |
| 6 | **Distribution** | PyPI von Anfang an | Jeder Minor-Release wird auf PyPI publiziert. CI/CD mit GitHub Actions. |
| 7 | **Dokumentation** | MkDocs, ab Phase 1 mitgeführt | Aktive Entwicklung erfordert optimale Doku: Quickstart, Config-Referenz, API-Doku, Content-Backend-Guide. |
| 8 | **Authoring-UI** | Eigenes Frontend (HTMX-basiert) | Dedizierte Autoren-UI mit Kurs-Editor, Lektions-Editor, Quiz-Builder, Review-Workflow. Kein reines Django-Admin. |
| 9 | **tenant_id Feldtyp** | `UUIDField(null=True, blank=True, db_index=True)` | UUID wie in django-tenancy (ADR-137). Nullable für Single-Tenant-Consumer (TENANT_AWARE=False). Indexed für RLS-Performance. |
| 10 | **Celery-Propagation** | `@with_tenant`-Decorator (django-tenancy) | Alle async Tasks (PPTX-Processing, Bulk-Import, PDF-Gen) propagieren Tenant-Context. `set_tenant()` + `set_db_tenant()` → Task → `clear_context()`. |
| 11 | **Single-Tenant-Modus** | `TENANT_AWARE=False` → tenant_id bleibt NULL | Consumer ohne Multi-Tenancy braucht kein django-tenancy. Models haben tenant_id=NULL, TenantManager wird nicht aktiviert, normaler Django-Manager greift. |

---

## 13. Distribution & Dokumentation

### PyPI

```toml
# pyproject.toml
[project]
name = "iil-learnfw"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "Django>=5.0",
]

[project.optional-dependencies]
api = ["djangorestframework>=3.15", "drf-spectacular>=0.27"]
tenancy = ["django-tenancy>=0.2"]          # Multi-Tenancy (ADR-137, TenantManager + RLS)
certificates = ["weasyprint>=62", "qrcode>=7"]
pptx = ["python-pptx>=1.0"]
scorm = ["lxml>=5.0"]
markdown = ["markdown>=3.6", "pymdown-extensions>=10"]
all = ["iil-learnfw[api,tenancy,certificates,pptx,scorm,markdown]"]
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

## 14. Nächste Schritte

1. ~~ADR reviewen und Entscheidung treffen~~ ✅ accepted
2. Repo `achimdehnert/learnfw` anlegen (pyproject.toml, CI, MkDocs)
3. Phase 1 implementieren: Course/Chapter/Lesson Models, MD/PDF-Backend, Progress-Tracking, DRF-API
4. PyPI-Publish v0.1.0
5. Admin-Integration: Kurs-Editor mit Drag&Drop Ordering
6. Templates: Default-Templates mit HTMX-Interaktion (wo Consumer HTMX nutzt)
7. Ersten Consumer integrieren (risk-hub: Schulungsmodul)
8. Gamification + SCORM in späteren Phasen
