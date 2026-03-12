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

> **Amended 2026-03-12**: Review-Fixes — Shared Auth in learnfw-DB (Entscheidung 2E löst
> User-FK-Kollision), CourseManager mit is_global-Support, docker-compose mit migrate-Service
> und Shared-DB Port-Exposure, DATABASE_ROUTERS für auth + learnfw, Package-Map korrigiert
> (python-pptx statt fiktivem iil-pptxfw), alle Extensions als [PROPOSED] markiert.

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
│  │ python-pptx │  │ iil-testkit │                                   │
│  │ (via       │  │ (dev only)  │                                   │
│  │ learnfw    │  │             │                                   │
│  │  [pptx])   │  │ Test-       │                                   │
│  │            │  │ Fixtures    │                                   │
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
| **python-pptx** | 1.0+ | PPTX lesen/schreiben (via `iil-learnfw[pptx]` Extra). Slide-Split, Notes-Extract, PPTX→HTML in learnfw-Backends. Roadmap: `iil-pptxfw` bei Bedarf (wenn pptx-hub gleiche Logik braucht). | — |
| **iil-testkit** | 0.1+ | pytest-Fixtures, Factories für learnfw-Models (**dev only** — gehört in requirements/test.txt) | `LearnfwFactories` [PROPOSED] (siehe 4.8) |

### 4.3 iil-aifw — Erweiterung: `learning`-Modul [PROPOSED]

Vorgeschlagene Erweiterung von iil-aifw für learn-hub-spezifische AI-Features.
Diese APIs existieren **noch nicht** und werden in Phase 2 implementiert:

```python
# iil_aifw.learning (neues Submodul)

class QuizGenerator:
    """Generiert Quiz-Fragen aus Lesson-Content via LLM."""
    async def generate(self, lesson_content: str, num_questions: int = 5,
                       question_types: tuple = ("mc", "sc", "freetext"),
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

### 4.4 iil-authoringfw — Erweiterung: Learning-Configs [PROPOSED]

Vorgeschlagene neue `FieldConfig`-Typen für strukturiertes Authoring von Lerninhalten.
Diese Configs existieren **noch nicht** und werden in Phase 1–2 implementiert:

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

### 4.5 iil-promptfw — Learning-Prompt-Collection [PROPOSED]

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

### 4.6 iil-illustration-fw — Lesson-Illustration [PROPOSED]

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

### 4.7 iil-researchfw — Content-Enrichment [PROPOSED]

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

### 4.8 iil-testkit — LearnfwFactories [PROPOSED]

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
# iil_learnfw/managers.py — CourseManager überschreibt TenantManager auto-filter
# BLOCK-2 Fix: TenantManager filtert tenant_id=NULL (is_global) raus!
class CourseManager(TenantManager):
    """Erweitert TenantManager um is_global-Support."""
    def get_queryset(self):
        qs = CourseQuerySet(self.model, using=self._db)
        from django_tenancy.context import get_context
        ctx = get_context()
        if ctx.tenant_id is not None:
            return qs.filter(
                Q(tenant_id=ctx.tenant_id) | Q(is_global=True)
            )
        return qs

class CourseQuerySet(TenantQuerySet):
    def visible_for_tenant(self, tenant_id):
        """Kurse die für einen Tenant sichtbar sind (inkl. Marketplace)."""
        return self.filter(
            Q(tenant_id=tenant_id) |          # Tenant-eigene Kurse
            Q(is_global=True) |               # Plattform-Kurse
            Q(marketplace_enabled=True,        # Marketplace-Kurse (SUGGEST-2 Fix)
              module_code__in=ModuleSubscription.objects
                  .filter(tenant_id=tenant_id, status="active")
                  .values_list("module", flat=True))
        ).filter(status="published")
```

> **Hinweis**: `CourseManager` muss in `iil-learnfw` implementiert werden (ADR-139 Amendment).
> Course erhält ein `module_code: CharField` für die Verknüpfung mit billing-hub `ModuleSubscription`.

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
│   │   │   ├── ai_tools.py         # AI-Tools UI (Quiz-Gen, Summary, Grading)
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
# python-pptx kommt via iil-learnfw[pptx] Extra

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

# Datenbank (learn-hub = Migrations-Owner der Shared DB)
# learn-hub hat nur EINE DB — diese IS die Shared learnfw-DB.
# Auth-Tabellen (auth_user, auth_group) leben ebenfalls hier (Entscheidung 2E).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DATABASE_NAME", default="learn_hub"),
        "USER": config("DATABASE_USER", default="learn_hub_app"),
        "PASSWORD": config("DATABASE_PASSWORD"),
        "HOST": config("DATABASE_HOST", default="db"),
        "PORT": config("DATABASE_PORT", default="5432"),
    },
}
# Kein DATABASE_ROUTERS nötig — alles in default DB.
# Consumer-Hubs brauchen DATABASE_ROUTERS (siehe 9.2).

# Plattform-Admin: Bypass TenantManager für Cross-Tenant-Zugriff
# SUGGEST-4: Plattform-Admins haben is_platform_admin=True im User-Model.
# TenantMiddleware setzt keinen tenant_id → TenantManager liefert unscoped.
# Für tenant-spezifische Aktionen: Admin wählt Tenant im Dashboard → set_context(tenant_id).
PLATFORM_ADMIN_PERMISSION = "core.is_platform_admin"
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
  migrate:
    image: ghcr.io/achimdehnert/learn-hub:latest
    command: python manage.py migrate --noinput
    env_file: .env.prod
    depends_on:
      db: { condition: service_healthy }

  web:
    image: ghcr.io/achimdehnert/learn-hub:latest
    env_file: .env.prod
    ports:
      - "8099:8000"
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
      migrate: { condition: service_completed_successfully }
    deploy:
      resources:
        limits: { memory: 512M }
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"]
      interval: 30s
      timeout: 5s
      retries: 3

  worker:
    image: ghcr.io/achimdehnert/learn-hub:latest
    command: celery -A config.celery worker -l info
    env_file: .env.prod
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
      migrate: { condition: service_completed_successfully }
    deploy:
      resources:
        limits: { memory: 384M }

  db:
    image: postgres:16-alpine
    env_file: .env.db
    ports:
      - "5499:5432"           # Exposed für Consumer-Hubs (Shared DB)
    volumes:
      - learn_hub_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits: { memory: 512M }

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    deploy:
      resources:
        limits: { memory: 128M }

volumes:
  learn_hub_data:
```

> **Shared DB**: Port 5499 ist für Consumer-Hubs exponiert. Consumer-Hubs setzen
> `LEARNFW_DATABASE_HOST=88.198.191.108` und `LEARNFW_DATABASE_PORT=5499` in ihrer `.env.prod`.
> Zugriff wird per `pg_hba.conf` und Firewall auf bekannte Container-Netzwerke beschränkt.

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
| **User-Auth** | **Shared Auth** (auth_user in Shared DB, Entscheidung 2E) | Shared Auth (auth_user in Shared DB, Sessions lokal) |
| **Datenbank** | **Eine DB** = Shared DB (auth + learnfw, Migrations-Owner) | Shared DB (R/W, auth + learnfw) + eigene Hub-DB |
| **Deployment** | learn.iil.pet (eigener Hub) | Embedded via `iil-learnfw` |
| **Dependencies** | `iil-learnfw[all]` + aifw + authoringfw + alle | `iil-learnfw` (minimal) |

> **Authoring-Split (Entscheidung C)**: learn-hub ist zuständig für plattformweite Kurse
> (`is_global=True`) und hat alle AI-Tools. Consumer-Hubs erstellen nur eigene Tenant-Kurse
> mit dem Basis-Authoring-Frontend aus `iil-learnfw`. Beide schreiben in die **selbe learnfw-DB**.

### 9.1 Shared-DB Architektur (Entscheidung 2E + 3C)

learn-hub hat **eine einzige DB** — diese ist gleichzeitig die Shared DB. Sie enthält:
- `auth_user`, `auth_group`, `auth_permission` (Shared Auth — Entscheidung 2E)
- `iil_learnfw_*` (alle 22 learnfw-Models mit tenant_id + RLS)
- `django_session`, `django_admin_log` (learn-hub-spezifisch)

Consumer-Hubs verbinden sich zur Shared DB für `auth.*` + `iil_learnfw.*` und haben
zusätzlich eine eigene DB für hub-spezifische Models (risk-models, coaching-models etc.).

```
┌──────────────────────────────────────────────────────────────────┐
│                     DATENBANK-TOPOLOGIE                          │
│                    (Entscheidung 2E + 3C)                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │      learn-hub DB = Shared DB (PostgreSQL: learn_hub)     │    │
│  │      Port 5499 (exposed für Consumer-Hubs)                │    │
│  │                                                           │    │
│  │  auth_user, auth_group, auth_permission  ← Shared Auth    │    │
│  │  iil_learnfw_course, iil_learnfw_lesson, ...              │    │
│  │  iil_learnfw_quiz, iil_learnfw_progress, ...              │    │
│  │  (22 learnfw-Models + RLS)                                │    │
│  │  django_session, django_admin_log (learn-hub)             │    │
│  │                                                           │    │
│  └──────┬─────────────────┬─────────────────┬────────────────┘    │
│         │                 │                 │                     │
│         ▼                 ▼                 ▼                     │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐              │
│  │ learn-hub  │    │  risk-hub  │    │ coach-hub  │  ...         │
│  │ default DB │    │ "learnfw"  │    │ "learnfw"  │              │
│  │ (= Shared) │    │ DB-Alias   │    │ DB-Alias   │              │
│  │ R/W + Migr │    │ R/W        │    │ R/W        │              │
│  └────────────┘    └─────┬──────┘    └─────┬──────┘              │
│                          │                 │                     │
│                          ▼                 ▼                     │
│                   ┌────────────┐    ┌────────────┐               │
│                   │  risk-hub  │    │ coach-hub  │               │
│                   │ default DB │    │ default DB │               │
│                   │ (sessions, │    │ (sessions, │               │
│                   │  risk-     │    │  coaching- │               │
│                   │  models)   │    │  models)   │               │
│                   └────────────┘    └────────────┘               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Regeln:**

- **learn-hub = Migrations-Owner**: Einziger Hub der `makemigrations` + `migrate` für auth + learnfw ausführt
- **Consumer-Hubs**: Verbinden sich R/W zur Shared DB, führen **keine** auth/learnfw-Migrations aus
- **Shared Auth**: Alle Hubs teilen `auth_user` — ein User registriert sich einmal, kann in allen Hubs arbeiten
- **Sessions bleiben lokal**: Jeder Hub hat eigene `django_session`-Tabelle in seiner `default`-DB
- **RLS**: Jeder Hub setzt `SET app.tenant_id` via django-tenancy Middleware — Consumer sehen nur eigene Daten
- **learn-hub Plattform-Admin**: Nutzt `unscoped()` für Cross-Tenant-Zugriff
- **User-Registration**: Primär in learn-hub (Content-Autoren) oder Consumer-Hub (Lernende)

### 9.2 Django DATABASE_ROUTERS (Consumer-Hub)

```python
# risk-hub/config/db_routers.py
class SharedDBRouter:
    """Routes auth + iil_learnfw to shared learn-hub DB (Entscheidung 2E + 3C)."""
    shared_labels = {"auth", "iil_learnfw"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.shared_labels:
            return "learnfw"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.shared_labels:
            return "learnfw"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        labels = {obj1._meta.app_label, obj2._meta.app_label}
        if labels & self.shared_labels:
            return True
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label in self.shared_labels:
            return False  # Migrations NUR in learn-hub, nie in Consumer-Hubs
        if app_label in {"sessions", "admin"}:
            return db == "default"  # Sessions + Admin bleiben lokal
        return db == "default"

# risk-hub/config/settings/base.py
DATABASES = {
    "default": {  # Hub-eigene DB (sessions, admin, risk-models)
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DATABASE_NAME"),
        ...
    },
    "learnfw": {  # Shared DB = learn-hub DB (auth + learnfw)
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("LEARNFW_DATABASE_NAME", default="learn_hub"),
        "HOST": config("LEARNFW_DATABASE_HOST"),
        "PORT": config("LEARNFW_DATABASE_PORT", default="5499"),
        "USER": config("LEARNFW_DATABASE_USER"),
        "PASSWORD": config("LEARNFW_DATABASE_PASSWORD"),
    },
}
DATABASE_ROUTERS = ["config.db_routers.SharedDBRouter"]
```

> **Wichtig**: Consumer-Hubs führen **keine** Migrations für `auth` oder `iil_learnfw` aus.
> Nur learn-hub managed diese Tabellen. Consumer-Hubs müssen `LEARNFW_DATABASE_*` Secrets
> in ihrer `.env.prod` konfigurieren (Zugang zur learn-hub DB via Port 5499).

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
- **Shared-DB Ausfall**: learn-hub DB ist Single Point of Failure für alle Consumer-Hubs. Mitigation: PostgreSQL Streaming Replication (Read-Replica), regelmäßige Backups, Monitoring via iil-django-commons Health-Check. Consumer-Hubs sollten graceful degradation implementieren (Learning-Features deaktiviert, Hub läuft weiter).
- **Shared Auth Migration**: Bestehende Consumer-Hubs (risk-hub) haben eigene auth_user-Tabellen. Migration zur Shared DB erfordert User-Merge-Strategie (Phase 6). Neue Hubs starten direkt mit SharedDBRouter.

---

## 13. Entschiedene Fragen

| # | Frage | Entscheidung | Begründung |
|---|---|---|---|
| 1 | **Authoring-Split** | **C: Aufgeteilt** — learn-hub für globale Kurse + AI-Tools, Consumer-Hubs für eigene Tenant-Kurse | Klare Zuständigkeit. Plattform-Content zentral, Tenant-Content dezentral. learn-hub hat AI-Tools, Consumer-Hubs haben Basis-Authoring (AUTHORING_ENABLED). |
| 2 | **User-Auth** | **E: Shared Auth in learnfw-DB** — auth_user + auth_group in der Shared DB | Löst User-FK-Kollision (BigAutoField-PKs wären sonst mehrdeutig über Hub-Grenzen). Consumer-Hubs routen auth.* + iil_learnfw.* zur Shared DB. Sessions + Admin bleiben hub-lokal. |
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
