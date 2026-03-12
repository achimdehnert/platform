---
status: "accepted"
date: 2026-03-12
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-139-shared-learning-platform-package.md", "ADR-137-tenant-manager-rls.md", "ADR-131-shared-backend-services.md", "ADR-134-module-monetization-strategy.md", "ADR-120-ci-cd-reusable-workflows.md"]
implementation_status: not_started
implementation_evidence: []
---

# ADR-140: Learn-Hub — Zentrales Learning Management Hub

---

## 1. Kontext & Problemstellung

ADR-139 definiert `iil-learnfw` als wiederverwendbares PyPI-Package für Lernplattform-Funktionalität.
Das Package liefert Models, Services, API und Basis-Templates — aber **kein eigenständiges Deployment**.

### Fehlende Komponenten

| Aspekt | ADR-139 (Package) | Benötigt (Hub) |
|---|---|---|
| **Deployment** | Kein eigenes | Docker, CI/CD, Domain |
| **Cross-Tenant Admin** | Nur Tenant-scoped | Plattformweites Content-Management |
| **AI-Integration** | Nicht vorgesehen | Quiz-Generierung, Grading, Empfehlungen |
| **Authoring-Pipeline** | Basis-Editor | Strukturierte Content-Produktion via authoringfw |
| **Illustration** | Nicht vorgesehen | Auto-Illustrierung via illustration-fw |
| **Research** | Nicht vorgesehen | Faktencheck, Quellenangaben via researchfw |
| **Monetarisierung** | Nur Setting | billing-hub Integration, Modul-Shop |

### Entscheidungsfrage

Wie wird die zentrale Lernplattform als eigenständiges Produkt bereitgestellt, das alle
IIL-Platform-Packages maximal integriert und als Content-Hub für alle Consumer-Hubs dient?

---

## 2. Entscheidungskriterien

- **Package-Maximierung**: Alle bestehenden PyPI-Packages nutzen, nicht neu erfinden
- **Cross-Tenant**: Plattformweite und mandantenspezifische Module in einem System
- **Prozessmodell**: Vollständiger Content-Lifecycle von Idee bis Lernender
- **AI-First**: KI-gestützte Content-Erstellung, Quiz-Generierung, Bewertung, Empfehlungen
- **Monetarisierung**: Module als Produkt, koppelbar an billing-hub Subscriptions
- **Platform-Standards**: ADR-120 CI/CD, ADR-137 Multi-Tenancy, ADR-041 Service-Layer

---

## 3. Entscheidung

**Learn-Hub als eigenständiger Django-Hub** (`achimdehnert/learn-hub`) mit maximaler
Integration aller IIL-Platform-Packages.

- **Domain**: `learn.iil.pet`
- **Repo**: `achimdehnert/learn-hub`
- **Stack**: Django 5.x, PostgreSQL 16 + pgvector, Redis, Celery, Docker
- **Rolle**: Zentrales Learning Management System + Content-Hub für alle Consumer

---

## 4. Package-Ökosystem-Integration

### 4.1 Vollständige Package-Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        learn-hub                                     │
│                     learn.iil.pet                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ iil-learnfw │  │ iil-aifw    │  │iil-authoring│  │iil-prompt │  │
│  │   [all]     │  │  v0.8+      │  │   fw v0.8+  │  │  fw       │  │
│  │             │  │             │  │             │  │           │  │
│  │ Models      │  │ LLM-Routing │  │ Authoring-  │  │ Prompt-   │  │
│  │ Services    │  │ NL2SQL      │  │ Pipeline    │  │ Templates │  │
│  │ API         │  │ Streaming   │  │ Planning    │  │ Versioning│  │
│  │ Backends    │  │ Quality     │  │ Configs     │  │           │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │iil-illustra-│  │iil-research │  │ iil-django- │  │ django-   │  │
│  │  tion-fw    │  │   fw        │  │  commons    │  │ tenancy   │  │
│  │             │  │             │  │             │  │           │  │
│  │ Bild-Gen    │  │ Recherche   │  │ Health      │  │ Tenant-   │  │
│  │ Diagramme   │  │ Faktencheck │  │ Logging     │  │ Manager   │  │
│  │ Visuals     │  │ Quellen     │  │ Cache       │  │ RLS       │  │
│  │             │  │             │  │ Security    │  │ Middleware│  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐                                   │
│  │ iil-pptxfw  │  │ iil-testkit │                                   │
│  │             │  │             │                                   │
│  │ PPTX-Render │  │ Test-       │                                   │
│  │ Slide-Split │  │ Fixtures    │                                   │
│  │ PDF-Export  │  │ Factories   │                                   │
│  └─────────────┘  └─────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Package-Integrationstabelle

| Package | Version | Rolle in learn-hub | Neue Features (vorgeschlagen) |
|---|---|---|---|
| **iil-learnfw** | 0.1+ | Kern — Models, Services, API, Authoring-Frontend | — (neues Package) |
| **iil-aifw** | 0.8+ | AI-Engine für Quiz-Gen, Grading, Empfehlungen, Zusammenfassungen | `learning`-Modul (siehe 4.3) |
| **iil-authoringfw** | 0.8+ | Strukturierte Content-Produktion (Lesson-Pläne, Kurs-Outlines) | `LessonPlanConfig`, `CourseOutlineConfig` (siehe 4.4) |
| **iil-promptfw** | latest | Prompt-Templates für AI-Features (Quiz-Gen, Grading, Summary) | Learning-Prompt-Collection (siehe 4.5) |
| **iil-illustration-fw** | latest | Auto-Illustrierung von Lektionen, Header-Bilder, Diagramme | `lesson_illustration` Style (siehe 4.6) |
| **iil-researchfw** | latest | Faktencheck für Lerninhalte, Auto-Quellenangaben | `fact_check` + `enrich_sources` (siehe 4.7) |
| **iil-django-commons** | 0.3+ | Health-Endpoints, Logging, Caching, Rate-Limiting, Security | — |
| **django-tenancy** | 0.2+ | TenantManager, RLS, Middleware, Celery-Propagation | — |
| **iil-pptxfw** | latest | PPTX→HTML Slide-Rendering, Auto-Split, PDF-Handout | — |
| **iil-testkit** | 0.1+ | pytest-Fixtures, Factories für learnfw-Models | `LearnfwFactories` (siehe 4.8) |

### 4.3 iil-aifw — Erweiterung: `learning`-Modul

Vorgeschlagene Erweiterung von iil-aifw für learn-hub-spezifische AI-Features:

```python
# iil_aifw.learning (neues Submodul)

class QuizGenerator:
    """Generiert Quiz-Fragen aus Lesson-Content via LLM."""
    async def generate(self, lesson_content: str, num_questions: int = 5,
                       question_types: list = ["mc", "sc", "freetext"],
                       difficulty: str = "medium") -> list[GeneratedQuestion]:
        ...

class FreetextGrader:
    """Bewertet Freitext-Antworten gegen Rubrik/Musterantwort."""
    async def grade(self, answer: str, rubric: str,
                    max_points: int) -> GradeResult:
        ...

class LearningPathRecommender:
    """Empfiehlt nächste Lektionen basierend auf Fortschritt + Schwächen."""
    async def recommend(self, user_progress: UserProgress,
                        available_courses: QuerySet) -> list[Recommendation]:
        ...

class ContentSummarizer:
    """Generiert Zusammenfassungen und Abstracts für Lektionen."""
    async def summarize(self, content: str,
                        style: str = "abstract") -> str:  # "abstract" | "key_points" | "tldr"
        ...

class DifficultyAnalyzer:
    """Schätzt Schwierigkeitsgrad von Content (Flesch-Index + LLM-Analyse)."""
    async def analyze(self, content: str) -> DifficultyResult:
        ...
```

**Integration in learn-hub**:
```python
# learn-hub/apps/learning/services/ai_service.py
from iil_aifw.learning import QuizGenerator, FreetextGrader, LearningPathRecommender

class LearningAIService:
    """Orchestriert AI-Features für learn-hub."""

    def __init__(self):
        self.quiz_gen = QuizGenerator()
        self.grader = FreetextGrader()
        self.recommender = LearningPathRecommender()

    async def auto_generate_quiz(self, lesson_id: int) -> Quiz:
        """Generiert Quiz aus Lektion und speichert als Draft."""
        lesson = await Lesson.objects.aget(pk=lesson_id)
        content = await content_service.render(lesson)
        questions = await self.quiz_gen.generate(content, num_questions=5)
        return await quiz_service.create_from_generated(lesson, questions, status="draft")

    async def ai_grade_attempt(self, attempt_id: int) -> None:
        """Bewertet Freitext-Antworten eines Attempts via AI."""
        ...
```

### 4.4 iil-authoringfw — Erweiterung: Learning-Configs

Vorgeschlagene neue `FieldConfig`-Typen für strukturiertes Authoring von Lerninhalten:

```python
# iil_authoringfw.configs.learning (neues Submodul)

LessonPlanConfig = PlanningFieldConfig(
    name="lesson_plan",
    fields=[
        "title",                    # Lektionstitel
        "learning_objectives",      # Lernziele (3-5 Bullet Points)
        "prerequisites",            # Voraussetzungen
        "content_outline",          # Gliederung (H2/H3-Struktur)
        "key_concepts",             # Kernbegriffe mit Definitionen
        "practical_exercises",      # Übungsaufgaben
        "assessment_criteria",      # Prüfungskriterien
        "estimated_duration",       # Geschätzte Bearbeitungszeit
        "difficulty_level",         # Schwierigkeitsgrad
    ],
    ai_provider="iil_aifw",        # Nutzt aifw für Generierung
)

CourseOutlineConfig = PlanningFieldConfig(
    name="course_outline",
    fields=[
        "course_title",
        "target_audience",          # Zielgruppe
        "learning_goals",           # Übergeordnete Lernziele
        "chapter_structure",        # Kapitel mit Lektionen
        "assessment_strategy",      # Quiz-Strategie (nach jedem Kapitel? Final?)
        "certification_criteria",   # Zertifizierungsbedingungen
        "estimated_total_duration",
    ],
    ai_provider="iil_aifw",
)

QuizDesignConfig = PlanningFieldConfig(
    name="quiz_design",
    fields=[
        "quiz_title",
        "covered_lessons",          # Welche Lektionen werden geprüft
        "question_distribution",    # MC: 60%, SC: 20%, Freitext: 20%
        "difficulty_curve",         # Einfach→Schwer oder gemischt
        "passing_score",
        "time_limit",
        "feedback_strategy",        # Sofort | Nach Abgabe | Mit Erklärung
    ],
    ai_provider="iil_aifw",
)
```

**Workflow in learn-hub**:
```
Autor → CourseOutlineConfig (AI-generiert) → Review → Approve
     → LessonPlanConfig pro Lektion (AI-generiert) → Markdown-Content
     → QuizDesignConfig → QuizGenerator (aifw) → Quiz-Fragen
     → DifficultyAnalyzer → Schwierigkeitsgrad-Labels
     → ContentSummarizer → Abstract für Kursübersicht
```

### 4.5 iil-promptfw — Learning-Prompt-Collection

```python
# Neue Prompt-Templates für learn-hub (in promptfw oder learn-hub lokal)
LEARNING_PROMPTS = {
    "quiz_generation": "Generiere {num} {types}-Fragen zum folgenden Lerninhalt...",
    "freetext_grading": "Bewerte die folgende Antwort gegen die Musterlösung...",
    "lesson_summary": "Fasse den folgenden Lerninhalt zusammen...",
    "course_outline": "Erstelle eine Kursstruktur für das Thema {topic}...",
    "difficulty_assessment": "Bewerte den Schwierigkeitsgrad des folgenden Textes...",
    "learning_objectives": "Leite 3-5 Lernziele aus folgendem Content ab...",
    "prerequisite_check": "Welche Vorkenntnisse werden für diesen Inhalt benötigt?...",
}
```

### 4.6 iil-illustration-fw — Lesson-Illustration

```python
# Integration in learn-hub
from iil_illustration_fw import IllustrationService

class LessonIllustrationService:
    """Auto-generiert Bilder für Lektionen."""

    async def generate_header(self, lesson: Lesson) -> str:
        """Generiert Header-Bild aus Lektionstitel + Kontext."""
        ...

    async def generate_diagram(self, lesson: Lesson, diagram_type: str) -> str:
        """Generiert Erklär-Diagramm aus Lesson-Content."""
        # diagram_type: "flowchart" | "mindmap" | "timeline" | "comparison"
        ...

    async def generate_slide_visuals(self, pptx_lesson: Lesson) -> list[str]:
        """Ergänzt PPTX-Slides mit generierten Visuals."""
        ...
```

### 4.7 iil-researchfw — Content-Enrichment

```python
# Integration in learn-hub
from iil_researchfw import ResearchService

class ContentEnrichmentService:
    """Faktencheck und Quellenanreicherung für Lerninhalte."""

    async def fact_check(self, lesson_content: str) -> FactCheckResult:
        """Prüft Fakten im Lerninhalt gegen Quellen."""
        ...

    async def enrich_sources(self, lesson: Lesson) -> list[Source]:
        """Findet und verknüpft relevante Quellen/Referenzen."""
        ...

    async def suggest_further_reading(self, course: Course) -> list[Resource]:
        """Empfiehlt weiterführende Literatur/Quellen zum Kursthema."""
        ...
```

### 4.8 iil-testkit — LearnfwFactories

```python
# Vorgeschlagene Erweiterung von iil-testkit
from iil_testkit.factories import LearnfwFactory

class CourseFactory(LearnfwFactory):
    title = factory.Faker("sentence", nb_words=4)
    status = "published"
    tenant_id = factory.LazyAttribute(lambda o: uuid.uuid4())

class LessonFactory(LearnfwFactory):
    title = factory.Faker("sentence", nb_words=6)
    content_type = "markdown"
    content_text = factory.Faker("paragraphs", nb=3)

class QuizFactory(LearnfwFactory):
    title = factory.Faker("sentence", nb_words=4)
    passing_score = 80
```

---

## 5. Prozessmodell — Content-Lifecycle

### 5.1 Vollständiger Prozess: Idee → Lernender

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONTENT-PRODUKTIONSPROZESS                        │
│                         (learn-hub)                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Phase 1: PLANUNG                                                    │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │ Kurs-Idee │───▶│ authoringfw  │───▶│ Kurs-Outline │              │
│  │ (Mensch)  │    │ CourseOutline│    │ (AI-Draft)   │              │
│  └──────────┘    │ Config       │    └──────┬───────┘              │
│                  └──────────────┘           │                       │
│                                             ▼                       │
│  Phase 2: CONTENT-ERSTELLUNG                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ authoringfw  │───▶│ Markdown /   │───▶│ illustration │          │
│  │ LessonPlan   │    │ PDF / PPTX   │    │ -fw Header   │          │
│  │ Config       │    │ Content      │    │ + Diagramme  │          │
│  └──────────────┘    └──────┬───────┘    └──────────────┘          │
│                              │                                      │
│                              ▼                                      │
│  Phase 3: QUALITÄTSSICHERUNG                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ researchfw   │───▶│ aifw         │───▶│ Review       │          │
│  │ Faktencheck  │    │ Difficulty   │    │ Workflow     │          │
│  │ + Quellen    │    │ Analyzer     │    │ (4-Augen)    │          │
│  └──────────────┘    └──────────────┘    └──────┬───────┘          │
│                                                  │                  │
│                                                  ▼                  │
│  Phase 4: ASSESSMENT-ERSTELLUNG                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ authoringfw  │───▶│ aifw Quiz-   │───▶│ Quiz-Review  │          │
│  │ QuizDesign   │    │ Generator    │    │ + Anpassung  │          │
│  │ Config       │    │ (auto MC/SC) │    │ (Mensch)     │          │
│  └──────────────┘    └──────────────┘    └──────┬───────┘          │
│                                                  │                  │
│                                                  ▼                  │
│  Phase 5: VERÖFFENTLICHUNG                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ Publish      │───▶│ Tenant-      │───▶│ Consumer-    │          │
│  │ (Freigabe)   │    │ Zuweisung    │    │ Hubs sehen   │          │
│  │              │    │ oder Global  │    │ den Content  │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                      │
│  Phase 6: LERN-PHASE & FEEDBACK                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ Lernende     │───▶│ aifw         │───▶│ Analytics &  │          │
│  │ bearbeiten   │    │ Freetext-    │    │ Empfehlungen │          │
│  │ Lektionen    │    │ Grading      │    │ (aifw Path)  │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Rollen im Prozess

| Rolle | Arbeitsort | Verantwortung |
|---|---|---|
| **Plattform-Admin** | learn-hub | Globale Kurse, Cross-Tenant Reporting, Package-Konfiguration |
| **Content-Autor** | learn-hub | Content erstellen, AI-Tools nutzen, Kurse strukturieren |
| **Content-Reviewer** | learn-hub | Qualitätssicherung, Faktencheck, Freigabe |
| **Tenant-Admin** | learn-hub ODER Consumer-Hub | Tenant-spezifische Kurse, Enrollment, Konfiguration |
| **Lernender** | Consumer-Hub (risk-hub etc.) | Kurse bearbeiten, Quizzes, Zertifikate |

### 5.3 AI-gestützter Workflow (Detailfluss)

```
Autor klickt "Neuen Kurs erstellen"
    │
    ▼
authoringfw.CourseOutlineConfig
    │  Autor gibt Thema, Zielgruppe, Umfang ein
    │  AI (aifw) generiert Kursstruktur als Draft
    ▼
Autor überprüft + passt an
    │
    ▼
Für jede Lektion:
    │
    ├── authoringfw.LessonPlanConfig
    │   │  AI generiert Lernziele, Gliederung, Kernbegriffe
    │   ▼
    ├── Autor schreibt Content (MD-Editor) ODER
    │   ├── Uploadet PDF / PPTX
    │   └── AI generiert Draft-Text aus LessonPlan
    │
    ├── illustration-fw: Auto-generiert Header-Bild
    │
    ├── researchfw: Faktencheck + Quellenvorschläge
    │
    ├── aifw.DifficultyAnalyzer: Schwierigkeitsgrad-Label
    │
    └── aifw.ContentSummarizer: Abstract für Kursübersicht
    │
    ▼
authoringfw.QuizDesignConfig
    │  AI schlägt Quiz-Strategie vor
    ▼
aifw.QuizGenerator
    │  Generiert MC/SC/Freitext-Fragen aus Lesson-Content
    ▼
Autor reviewed + passt Fragen an
    │
    ▼
Review-Workflow (learnfw)
    │  Reviewer prüft Content + Quiz
    │  researchfw.fact_check() als Hilfe
    ▼
Publish → Tenant-Zuweisung
    │
    ├── is_global=True → alle Consumer-Hubs
    └── tenant_id=X → nur spezifischer Hub
```

---

## 6. Modul-Konzept: Tenantfähig + Tenantübergreifend

### 6.1 Modul-Typen

```
┌─────────────────────────────────────────────────────────────┐
│                    MODUL-HIERARCHIE                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────┐                             │
│  │  PLATTFORM-MODULE            │  is_global=True             │
│  │  (tenant_id=NULL)            │  Sichtbar für ALLE Tenants  │
│  │                              │  Erstellt in: learn-hub     │
│  │  • Datenschutz-Grundlagen    │  Beispiel: Compliance       │
│  │  • Onboarding Plattform      │                             │
│  │  • Sicherheitsschulung       │                             │
│  └─────────────────────────────┘                             │
│                                                              │
│  ┌─────────────────────────────┐                             │
│  │  TENANT-MODULE               │  is_global=False            │
│  │  (tenant_id=UUID)            │  Sichtbar NUR für Tenant    │
│  │                              │  Erstellt in: learn-hub     │
│  │  • Versicherungsrecht        │  ODER Consumer-Hub          │
│  │    (→ risk-hub Tenant)       │                             │
│  │  • Coaching-Methodik         │                             │
│  │    (→ coach-hub Tenant)      │                             │
│  └─────────────────────────────┘                             │
│                                                              │
│  ┌─────────────────────────────┐                             │
│  │  MARKETPLACE-MODULE          │  is_global=False            │
│  │  (billing-hub gekoppelt)     │  Sichtbar nach Kauf/Sub     │
│  │                              │  ADR-134 Monetarisierung    │
│  │  • Premium: Risikomanagement │                             │
│  │  • Premium: Zertifizierung   │  billing-hub Subscription   │
│  │    Professional              │  → ModuleSubscription       │
│  └─────────────────────────────┘                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Modul-Sichtbarkeit im Consumer-Hub

```python
# iil_learnfw QuerySet-Logik (in learnfw, genutzt von learn-hub + Consumer)
class CourseQuerySet(TenantQuerySet):
    def visible_for_tenant(self, tenant_id):
        """Kurse die für einen Tenant sichtbar sind."""
        return self.filter(
            Q(tenant_id=tenant_id) |          # Tenant-eigene Kurse
            Q(is_global=True) |               # Plattform-Kurse
            Q(marketplace_enabled=True,        # Marketplace-Kurse
              course__module_subscriptions__tenant_id=tenant_id,
              course__module_subscriptions__status="active")
        ).filter(status="published")
```

### 6.3 billing-hub Integration (ADR-134)

```
Tenant-Admin in risk-hub
    │
    ├── Sieht Plattform-Module (kostenlos, is_global)
    ├── Sieht eigene Tenant-Module
    └── Sieht Marketplace → "Premium: Risikomanagement"
         │
         ▼
    Klick "Freischalten" → billing-hub Checkout
         │
         ▼
    billing-hub erstellt ModuleSubscription
         │
         ▼
    Kurs wird für Tenant sichtbar (visible_for_tenant)
```

---

## 7. learn-hub Architektur

### 7.1 App-Struktur

```
learn-hub/
├── config/
│   ├── settings/
│   │   ├── base.py              # Alle Package-Integrations
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   └── celery.py
├── apps/
│   ├── learning/                # Kern-App (nutzt iil-learnfw)
│   │   ├── services/
│   │   │   ├── ai_service.py    # aifw Integration (Quiz-Gen, Grading, Empfehlungen)
│   │   │   ├── authoring_service.py  # authoringfw Integration (Lesson/Course Plans)
│   │   │   ├── illustration_service.py  # illustration-fw Integration
│   │   │   ├── research_service.py  # researchfw Integration (Faktencheck)
│   │   │   └── marketplace_service.py  # billing-hub Integration
│   │   ├── views/
│   │   │   ├── platform_admin.py    # Cross-Tenant Admin Dashboard
│   │   │   ├── analytics.py        # Plattformweites Reporting
│   │   │   └── marketplace.py      # Modul-Marketplace
│   │   ├── tasks.py             # Celery: AI-Processing, Bulk-Import
│   │   └── urls.py
│   └── core/                    # Hub-spezifisch (User, Health, etc.)
│       ├── views.py             # /livez/, /healthz/
│       └── middleware.py
├── templates/
│   ├── base.html                # learn-hub eigenes Layout
│   └── iil_learnfw/
│       └── _base.html           # Override für learnfw-Templates
├── static/
├── docker-compose.prod.yml
├── Dockerfile
├── .github/workflows/
│   └── ci-cd.yml               # ADR-120 Reusable Workflows
├── scripts/
│   └── ship.sh
└── requirements/
    ├── base.txt
    └── production.txt
```

### 7.2 Dependencies (requirements/base.txt)

```
# Kern
Django>=5.0
gunicorn>=22

# IIL Platform Packages
iil-learnfw[all]                # Lernplattform-Kern (alle Extras)
iil-aifw>=0.8                   # AI-Engine (Quiz-Gen, Grading, Empfehlungen)
iil-authoringfw>=0.8            # Strukturierte Content-Produktion
iil-promptfw                    # Prompt-Templates
iil-illustration-fw             # Auto-Illustrierung
iil-researchfw                  # Faktencheck, Quellen
iil-django-commons>=0.3         # Health, Logging, Cache, Security
iil-testkit>=0.1                # Testing (dev only)

# Multi-Tenancy
django-tenancy>=0.2             # TenantManager, RLS, Middleware

# Infrastructure
celery[redis]>=5.3
redis>=5.0
psycopg[binary]>=3.1
```

### 7.3 Django-Settings (Auszug)

```python
# config/settings/base.py

INSTALLED_APPS = [
    # IIL Packages
    "iil_learnfw",
    "iil_django_commons",

    # learn-hub Apps
    "apps.learning",
    "apps.core",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    ...
]

# iil-learnfw Konfiguration (maximale Features)
IIL_LEARNFW = {
    "TENANT_AWARE": True,
    "AUTHORING_ENABLED": True,
    "ONBOARDING_ENABLED": True,
    "ENROLLMENT_MODE": "self_enroll",
    "ENABLE_REVIEW_WORKFLOW": True,
    "CONTENT_VERSIONING": True,
    "PPTX_AUTO_SPLIT": True,
    "PPTX_EXTRACT_NOTES": True,
    "PPTX_GENERATE_PDF": True,
    "MARKDOWN_EDITOR": "easymde",
    "AUTO_SAVE_INTERVAL": 30,
}

# iil-aifw Konfiguration
IIL_AIFW = {
    "DEFAULT_PROVIDER": "openai",
    "QUALITY_TIER": "high",          # Lerninhalt-Qualität = hoch
}

# iil-django-commons
IIL_COMMONS = {
    "HEALTH_PATHS": frozenset({"/livez/", "/healthz/"}),
    "LOGGING_LEVEL": "INFO",
}
```

### 7.4 URL-Struktur (learn.iil.pet)

```
learn.iil.pet
│
├── /                                    # Dashboard (rollenabhängig)
│
├── /kurse/                              # Kursübersicht (public, tenant-scoped)
│   ├── /kurse/<slug>/                   # Kursdetail + Lektionen
│   ├── /lektion/<id>/                   # Lektion bearbeiten
│   ├── /quiz/<id>/                      # Quiz
│   ├── /fortschritt/                    # Mein Fortschritt
│   ├── /zertifikate/                    # Meine Zertifikate
│   └── /rangliste/                      # Leaderboard (tenant-scoped)
│
├── /authoring/                          # Content-Erstellung (Autoren)
│   ├── /authoring/dashboard/            # Autoren-Dashboard
│   ├── /authoring/kurse/                # Kurs-Management
│   ├── /authoring/ai/                   # AI-Tools (Quiz-Gen, Summary, etc.)
│   ├── /authoring/review/               # Review-Queue
│   └── /authoring/import/               # Bulk-Import
│
├── /admin-dashboard/                    # Plattform-Admin (Cross-Tenant)
│   ├── /admin-dashboard/tenants/        # Tenant-Übersicht
│   ├── /admin-dashboard/analytics/      # Cross-Tenant Statistiken
│   ├── /admin-dashboard/global-kurse/   # Plattformweite Kurse verwalten
│   └── /admin-dashboard/marketplace/    # Marketplace-Module verwalten
│
├── /marketplace/                        # Modul-Marketplace
│   ├── /marketplace/browse/             # Verfügbare Module
│   └── /marketplace/subscriptions/      # Aktive Subscriptions
│
├── /api/v1/                             # REST-API (DRF)
│
├── /livez/                              # Health-Check (iil-django-commons)
├── /healthz/                            # Readiness-Check
└── /admin/                              # Django Admin (Superuser)
```

---

## 8. Deployment

### 8.1 Infrastruktur

| Aspekt | Wert |
|---|---|
| **Server** | Hetzner 88.198.191.108 |
| **Domain** | learn.iil.pet |
| **Port** | 8099 (intern) |
| **Container** | learn-hub-web, learn-hub-worker (Celery), learn-hub-db, learn-hub-redis |
| **Image** | ghcr.io/achimdehnert/learn-hub:latest |
| **CI/CD** | ADR-120 Reusable Workflows (`_ci-python` → `_build-docker` → `_deploy-hetzner`) |

### 8.2 docker-compose.prod.yml (Auszug)

```yaml
services:
  web:
    image: ghcr.io/achimdehnert/learn-hub:latest
    env_file: .env.prod
    ports:
      - "8099:8000"
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    deploy:
      resources:
        limits: { memory: 512M }
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"]

  worker:
    image: ghcr.io/achimdehnert/learn-hub:latest
    command: celery -A config.celery worker -l info
    env_file: .env.prod
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }

  db:
    image: postgres:16-alpine
    volumes:
      - learn_hub_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
```

---

## 9. Abgrenzung: learn-hub vs. Consumer-Hub

| Aspekt | learn-hub | Consumer-Hub (z.B. risk-hub) |
|---|---|---|
| **Primärer Nutzer** | Content-Autoren, Plattform-Admins | Lernende, Tenant-Admins |
| **Authoring** | **Globale Kurse** + AI-Tools (is_global=True) | **Eigene Tenant-Kurse** (AUTHORING_ENABLED, Basis-Editor) |
| **Cross-Tenant** | Ja (Plattform-Admin Dashboard) | Nein (nur eigener Tenant) |
| **AI-Features** | Quiz-Gen, Grading, Empfehlungen, Illustration | Nur Grading + Empfehlungen (embedded) |
| **Marketplace** | Modul-Management + Pricing | Modul-Katalog + Kauf |
| **Analytics** | Plattformweit (alle Tenants) | Nur eigener Tenant |
| **User-Auth** | **Eigene User-DB** (Standard Django auth) | Eigene User-DB (unabhängig) |
| **Datenbank** | **Shared learnfw-DB** (Migrations-Owner) | Shared learnfw-DB (Reader/Writer) + eigene Hub-DB |
| **Deployment** | learn.iil.pet (eigener Hub) | Embedded via `iil-learnfw` |
| **Dependencies** | `iil-learnfw[all]` + aifw + authoringfw + alle | `iil-learnfw` (minimal) |

> **Authoring-Split (Entscheidung C)**: learn-hub ist zuständig für plattformweite Kurse
> (`is_global=True`) und hat alle AI-Tools. Consumer-Hubs erstellen nur eigene Tenant-Kurse
> mit dem Basis-Authoring-Frontend aus `iil-learnfw`. Beide schreiben in die **selbe learnfw-DB**.

### 9.1 Shared learnfw-DB Architektur (Entscheidung 3C)

learn-hub und Consumer-Hubs teilen sich eine gemeinsame PostgreSQL-Datenbank für alle
`iil_learnfw_*`-Tabellen. Jeder Hub hat zusätzlich seine eigene DB für hub-spezifische Daten.

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATENBANK-TOPOLOGIE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────┐           │
│  │         learnfw-DB (Shared)                          │           │
│  │  PostgreSQL: learn_hub_content                       │           │
│  │                                                      │           │
│  │  iil_learnfw_course, iil_learnfw_lesson,             │           │
│  │  iil_learnfw_quiz, iil_learnfw_progress, ...         │           │
│  │  (alle 22 learnfw-Models mit tenant_id + RLS)        │           │
│  │                                                      │           │
│  └────────┬────────────────┬─────────────────┬────────┘           │
│           │                │                 │                      │
│           ▼                ▼                 ▼                      │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐              │
│  │ learn-hub  │  │  risk-hub   │  │  coach-hub   │              │
│  │ R/W + Migr.│  │  R/W        │  │  R/W         │  ...         │
│  └─────┬──────┘  └────┬───────┘  └─────┬───────┘              │
│        │               │                │                       │
│        ▼               ▼                ▼                       │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐              │
│  │ learn-hub  │  │  risk-hub   │  │  coach-hub   │              │
│  │ eigene DB  │  │  eigene DB  │  │  eigene DB   │              │
│  │ (auth,     │  │ (auth,      │  │ (auth,       │              │
│  │  sessions, │  │  risk-      │  │  coaching-   │              │
│  │  admin)    │  │  models)    │  │  models)     │              │
│  └────────────┘  └────────────┘  └─────────────┘              │
│                                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Regeln:**

- **Migrations-Owner**: Nur learn-hub führt `makemigrations` + `migrate` für learnfw-Tabellen aus
- **Consumer-Hubs**: Verbinden sich read/write zur learnfw-DB, führen aber **keine** learnfw-Migrations aus
- **RLS**: Jeder Hub setzt `SET app.tenant_id` via django-tenancy Middleware — Consumer sehen nur eigene Daten
- **learn-hub Plattform-Admin**: Nutzt `unscoped()` für Cross-Tenant-Zugriff

### 9.2 Django DATABASE_ROUTERS (Consumer-Hub)

```python
# risk-hub/config/db_routers.py
class LearnfwRouter:
    """Routes iil_learnfw models to shared learnfw-DB."""
    learnfw_labels = {"iil_learnfw"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.learnfw_labels:
            return "learnfw"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.learnfw_labels:
            return "learnfw"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        labels = {obj1._meta.app_label, obj2._meta.app_label}
        if labels & self.learnfw_labels:
            return True
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label in self.learnfw_labels:
            return db == "learnfw"  # Nur in learnfw-DB migrieren
        return db == "default"      # Alles andere in default

# risk-hub/config/settings/base.py
DATABASES = {
    "default": {  # Hub-eigene DB (auth, sessions, risk-models)
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DATABASE_NAME"),
        ...
    },
    "learnfw": {  # Shared learnfw-DB (Content, Progress, Quizzes)
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("LEARNFW_DATABASE_NAME"),  # = learn_hub_content
        "HOST": config("LEARNFW_DATABASE_HOST"),
        ...
    },
}
DATABASE_ROUTERS = ["config.db_routers.LearnfwRouter"]
```

---

## 10. Vorgeschlagene Package-Erweiterungen (Zusammenfassung)

| Package | Erweiterung | Aufwand | Priorität |
|---|---|---|---|
| **iil-aifw** | `learning`-Modul: QuizGenerator, FreetextGrader, LearningPathRecommender, ContentSummarizer, DifficultyAnalyzer | Mittel | Phase 2 |
| **iil-authoringfw** | `LessonPlanConfig`, `CourseOutlineConfig`, `QuizDesignConfig` | Gering | Phase 1 |
| **iil-promptfw** | Learning-Prompt-Collection (7 Templates) | Gering | Phase 1 |
| **iil-illustration-fw** | `lesson_illustration` Style, Diagramm-Generator | Mittel | Phase 3 |
| **iil-researchfw** | `fact_check()`, `enrich_sources()`, `suggest_further_reading()` | Mittel | Phase 3 |
| **iil-testkit** | `LearnfwFactories` (Course, Lesson, Quiz, etc.) | Gering | Phase 1 |

---

## 11. Rollout-Plan

| Phase | Scope | Deliverables |
|---|---|---|
| **Phase 1** | learn-hub Repo + Basis-Setup | Repo, Docker, CI/CD, iil-learnfw[all] integriert, learn.iil.pet LIVE |
| **Phase 2** | Authoring + AI | authoringfw Configs, aifw QuizGenerator, Content-Pipeline |
| **Phase 3** | Cross-Tenant Admin | Plattform-Admin Dashboard, Analytics, Globale Kurse |
| **Phase 4** | Marketplace | billing-hub Integration, Modul-Marketplace, Subscriptions |
| **Phase 5** | AI-Erweiterungen | FreetextGrader, LearningPath, Illustration, Research |
| **Phase 6** | Erster Consumer | risk-hub nutzt learn-hub Content (embedded via learnfw) |

---

## 12. Risiken & Mitigationen

- **Package-Versionskonflikt**: learn-hub pinnt alle Package-Versionen. Renovate/Dependabot für Updates.
- **AI-Kosten**: Quiz-Generierung und Grading verbrauchen LLM-Tokens. Rate-Limiting via aifw Quality-Tiers. Caching für wiederholte Requests.
- **Scope Creep**: Strenge Phasentrennung. Phase 1 = Basis-Hub ohne AI. AI erst ab Phase 2.
- **Cross-Tenant Security**: Plattform-Admin erfordert spezielle Permissions (`is_platform_admin`). TenantManager + RLS als Sicherheitsnetz.
- **Performance**: Celery für alle AI-Tasks (async). Content-Rendering gecacht. pgvector für Embedding-basierte Empfehlungen.

---

## 13. Entschiedene Fragen

| # | Frage | Entscheidung | Begründung |
|---|---|---|---|
| 1 | **Authoring-Split** | **C: Aufgeteilt** — learn-hub für globale Kurse + AI-Tools, Consumer-Hubs für eigene Tenant-Kurse | Klare Zuständigkeit. Plattform-Content zentral, Tenant-Content dezentral. learn-hub hat AI-Tools, Consumer-Hubs haben Basis-Authoring (AUTHORING_ENABLED). |
| 2 | **User-Auth** | **A: Eigene User-DB** — Standard Django auth_user | Schnellster Start, unabhängig von Consumer-Hubs. SSO als separates ADR bei Bedarf nachrüstbar. Autoren brauchen separaten learn-hub Account. |
| 3 | **Content-Sync** | **C: Shared learnfw-DB** — learn-hub + Consumer-Hubs verbinden sich zur selben DB für iil_learnfw_*-Tabellen | Kein Sync nötig, Content instant verfügbar. Django DATABASE_ROUTERS trennen learnfw-DB von hub-eigener DB. Migrations nur in learn-hub, Consumer-Hubs lesen/schreiben. |

---

## 14. Nächste Schritte

1. ~~ADR-140 reviewen und entscheiden~~ ✅ accepted
2. ADR-139 Repo `achimdehnert/learnfw` anlegen (Package zuerst — Basis für learn-hub)
3. Repo `achimdehnert/learn-hub` anlegen (Docker, CI/CD, Shared learnfw-DB)
4. Phase 1: Basis-Setup mit `iil-learnfw[all]`, learn.iil.pet LIVE
5. authoringfw erweitern: LessonPlanConfig, CourseOutlineConfig
6. Phase 2: AI-Integration (aifw.learning Submodul)
7. Phase 3: Cross-Tenant Admin, globale Kurse, Analytics
8. Phase 6: risk-hub als erster Consumer (Shared learnfw-DB anbinden)
