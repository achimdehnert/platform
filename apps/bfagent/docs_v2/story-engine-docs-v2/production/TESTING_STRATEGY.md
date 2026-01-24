# Story Engine - Testing Strategy

> **Focus**: Comprehensive Testing, Quality Assurance, CI/CD  
> **Status**: Production Planning  
> **Updated**: 2025-11-09

---

## 📋 Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Levels](#test-levels)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [E2E Testing](#e2e-testing)
6. [Performance Testing](#performance-testing)
7. [CI/CD Pipeline](#cicd-pipeline)

---

## 🎯 Testing Philosophy

### Principles

```yaml
1. Test Pyramid:
   - 70% Unit Tests (fast, isolated)
   - 20% Integration Tests (realistic)
   - 10% E2E Tests (expensive)

2. Test What Matters:
   - Business logic (critical)
   - Edge cases (important)
   - Happy path (baseline)
   - NOT: getters/setters, trivial code

3. Tests as Documentation:
   - Clear test names
   - Describe expected behavior
   - Provide examples

4. Fast Feedback:
   - Unit tests < 1s total
   - Integration tests < 30s
   - E2E tests < 5min
```

---

## 📊 Test Levels

### Coverage Goals

```python
# .coveragerc
[run]
source = apps/story_engine, apps/bfagent
omit =
    */migrations/*
    */tests/*
    */admin.py
    */__init__.py

[report]
precision = 2
show_missing = True
skip_covered = False

# Minimum coverage
fail_under = 80
```

---

## 🧪 Unit Testing

### Agent Tests

```python
# tests/test_agents/test_story_architect.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from apps.story_engine.agents.story_architect import StoryArchitectAgent
from apps.story_engine.state import ChapterState, ChapterPlan

@pytest.fixture
def architect_agent():
    """Create test agent with mocked LLM"""
    agent = StoryArchitectAgent()
    agent.llm = AsyncMock()
    return agent

@pytest.fixture
def sample_state():
    """Create sample chapter state"""
    return ChapterState(
        beat_id=1,
        story_bible_id=1,
        beat_description="Sarah discovers anomalies",
        beat_title="Discovery",
        target_word_count=2500,
        world_rules=[
            {"rule": "No time travel", "established_in": "Ch1"}
        ],
        character_profiles=[
            {
                "name": "Sarah Chen",
                "traits": ["intelligent", "cautious"],
                "bio_snippet": "Neuroscientist studying BCIs"
            }
        ],
        previous_summaries=[],
        prose_style={
            "voice": "third_limited",
            "tone": "tense",
            "pacing": "medium",
            "description_density": "balanced"
        }
    )

@pytest.mark.asyncio
async def test_architect_creates_valid_plan(architect_agent, sample_state):
    """Test that architect creates a valid chapter plan"""
    
    # Mock LLM response
    mock_plan = {
        "opening_scene": "Sarah wakes with a headache...",
        "plot_points": [
            "Discovery of enhanced perception",
            "First anomaly detected"
        ],
        "character_moments": [
            "Sarah's fear of losing humanity"
        ],
        "closing_hook": "Message appears in her vision",
        "estimated_word_count": 2500
    }
    
    architect_agent.llm.ainvoke = AsyncMock(
        return_value=MagicMock(content=json.dumps(mock_plan))
    )
    
    # Execute
    result_state = await architect_agent.execute(sample_state)
    
    # Assert
    assert result_state.plan is not None
    assert isinstance(result_state.plan, ChapterPlan)
    assert len(result_state.plan.plot_points) >= 2
    assert result_state.plan.estimated_word_count == 2500

@pytest.mark.asyncio
async def test_architect_handles_invalid_json(architect_agent, sample_state):
    """Test error handling for invalid LLM response"""
    
    # Mock invalid JSON response
    architect_agent.llm.ainvoke = AsyncMock(
        return_value=MagicMock(content="Not valid JSON")
    )
    
    # Should raise AgentError
    with pytest.raises(AgentError):
        await architect_agent.execute(sample_state)

@pytest.mark.asyncio
async def test_architect_validates_input(architect_agent):
    """Test input validation"""
    
    # Invalid state (no beat_description)
    invalid_state = ChapterState(
        beat_id=1,
        story_bible_id=1,
        beat_description="",  # Empty!
        beat_title="Test",
        target_word_count=2500,
        world_rules=[],
        character_profiles=[],
        previous_summaries=[],
        prose_style={}
    )
    
    # Should fail validation
    is_valid = await architect_agent.validate_input(invalid_state)
    assert is_valid is False

@pytest.mark.asyncio
async def test_architect_retry_on_rate_limit(architect_agent, sample_state):
    """Test retry behavior on rate limit"""
    
    # Mock rate limit then success
    architect_agent.llm.ainvoke = AsyncMock(
        side_effect=[
            RateLimitError(retry_after=1),
            MagicMock(content=json.dumps(valid_plan))
        ]
    )
    
    # Should succeed after retry
    result_state = await architect_agent.execute(sample_state)
    assert result_state.plan is not None

def test_architect_performance_tracking(architect_agent, sample_state):
    """Test that performance metrics are tracked"""
    
    # Before execution
    initial_count = architect_agent._execution_count
    
    # Execute
    await architect_agent.execute(sample_state)
    
    # After execution
    assert architect_agent._execution_count == initial_count + 1
    assert architect_agent._total_time > 0
```

### Handler Tests

```python
# tests/test_handlers/test_story_handlers.py
import pytest
from unittest.mock import AsyncMock, patch
from apps.bfagent.handlers.story_handlers import ChapterGenerationHandler
from apps.bfagent.models_story import ChapterBeat, StoryBible, Chapter

@pytest.fixture
def test_database(db):
    """Setup test database with sample data"""
    
    # Create story bible
    bible = StoryBible.objects.create(
        title="Test Story",
        genre="Sci-Fi",
        world_rules=[{"rule": "No time travel"}],
        prose_style="Third person limited",
        tone="Tense"
    )
    
    # Create beat
    beat = ChapterBeat.objects.create(
        story_bible=bible,
        beat_number=1,
        title="Discovery",
        description="Sarah discovers anomalies",
        target_word_count=2500
    )
    
    return {'bible': bible, 'beat': beat}

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handler_generates_chapter(test_database):
    """Test complete chapter generation flow"""
    
    handler = ChapterGenerationHandler()
    beat = test_database['beat']
    
    # Mock workflow to avoid actual LLM calls
    with patch.object(handler, 'workflow') as mock_workflow:
        mock_workflow.run = AsyncMock(
            return_value=ChapterState(
                beat_id=beat.id,
                story_bible_id=beat.story_bible_id,
                final_text="Generated chapter content...",
                quality_score=0.85,
                consistency_score=0.90
            )
        )
        
        # Execute
        result = await handler.generate_chapter(beat.id)
        
        # Assert
        assert result['status'] == 'success'
        assert 'chapter_id' in result
        
        # Check database
        chapter = Chapter.objects.get(id=result['chapter_id'])
        assert chapter.content == "Generated chapter content..."
        assert chapter.quality_score == 0.85

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handler_handles_validation_error(test_database):
    """Test handler handles validation errors gracefully"""
    
    handler = ChapterGenerationHandler()
    beat = test_database['beat']
    
    # Mock workflow to raise validation error
    with patch.object(handler, 'workflow') as mock_workflow:
        mock_workflow.run = AsyncMock(
            side_effect=ValidationError(
                errors=[{'field': 'content', 'error': 'Too short'}],
                message="Validation failed"
            )
        )
        
        # Execute
        result = await handler.generate_chapter(beat.id)
        
        # Should return error result (not raise)
        assert result['status'] == 'validation_error'
        assert 'errors' in result

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handler_saves_partial_on_error(test_database):
    """Test that partial results are saved on error"""
    
    handler = ChapterGenerationHandler()
    beat = test_database['beat']
    
    # Mock workflow to fail after draft
    with patch.object(handler, 'workflow') as mock_workflow:
        mock_workflow.run = AsyncMock(
            side_effect=ValidationError(
                errors=[],
                message="Failed",
                context={'draft': 'Partial content...'}
            )
        )
        
        # Execute
        result = await handler.generate_chapter(beat.id)
        
        # Should save partial
        assert result['status'] == 'validation_error'
        chapter = Chapter.objects.get(id=result['chapter_id'])
        assert chapter.content == 'Partial content...'
        assert chapter.status == 'needs_review'
```

### State Tests

```python
# tests/test_state/test_chapter_state.py
import pytest
from pydantic import ValidationError
from apps.story_engine.state import ChapterState, ChapterPlan

def test_state_immutable_inputs():
    """Test that input fields are frozen"""
    
    state = ChapterState(
        beat_id=1,
        story_bible_id=1,
        beat_description="Test",
        beat_title="Test",
        target_word_count=2500,
        world_rules=[],
        character_profiles=[],
        previous_summaries=[],
        prose_style={}
    )
    
    # Should not be able to modify frozen fields
    with pytest.raises(ValidationError):
        state.beat_id = 2

def test_state_validation():
    """Test state validation rules"""
    
    # Test minimum word count for draft
    with pytest.raises(ValidationError):
        ChapterState(
            beat_id=1,
            story_bible_id=1,
            beat_description="Test",
            beat_title="Test",
            target_word_count=2500,
            draft="Too short",  # < 1000 words
            world_rules=[],
            character_profiles=[],
            previous_summaries=[],
            prose_style={}
        )

def test_state_helper_methods():
    """Test state helper methods"""
    
    state = ChapterState(
        beat_id=1,
        story_bible_id=1,
        beat_description="Test",
        beat_title="Test",
        target_word_count=2500,
        plan=ChapterPlan(
            opening_scene="Opening",
            plot_points=["P1", "P2"],
            closing_hook="Hook",
            estimated_word_count=2500
        ),
        world_rules=[{"rule": "Test"}],
        character_profiles=[{"name": "Test"}],
        previous_summaries=[],
        prose_style={}
    )
    
    # Test is_ready_for_writer
    assert state.is_ready_for_writer() is True
    
    # Test has_critical_issues
    assert state.has_critical_issues() is False
```

---

## 🔗 Integration Testing

### Workflow Tests

```python
# tests/test_integration/test_chapter_workflow.py
import pytest
from apps.story_engine.workflows.chapter_workflow import ChapterWorkflow
from apps.story_engine.state import ChapterState

@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_workflow():
    """Test complete agent workflow"""
    
    workflow = ChapterWorkflow()
    
    initial_state = ChapterState(
        beat_id=1,
        story_bible_id=1,
        beat_description="Sarah discovers enhanced abilities",
        beat_title="Discovery",
        target_word_count=2500,
        world_rules=[{"rule": "No time travel"}],
        character_profiles=[{
            "name": "Sarah Chen",
            "traits": ["intelligent"],
            "bio_snippet": "Neuroscientist"
        }],
        previous_summaries=[],
        prose_style={
            "voice": "third_limited",
            "tone": "tense",
            "pacing": "medium",
            "description_density": "balanced"
        }
    )
    
    config = {
        "configurable": {
            "thread_id": "test-thread-1"
        }
    }
    
    # Execute workflow
    final_state = await workflow.run(initial_state, config)
    
    # Assertions
    assert final_state.plan is not None, "Plan should be created"
    assert final_state.draft is not None, "Draft should be created"
    assert final_state.final_text is not None, "Final text should be created"
    assert final_state.quality_score is not None, "Quality score should be set"
    assert final_state.quality_score >= 0.7, "Quality should meet threshold"
    
    # Check word count
    word_count = len(final_state.final_text.split())
    assert 2000 <= word_count <= 3000, f"Word count {word_count} out of range"

@pytest.mark.asyncio
@pytest.mark.integration
async def test_workflow_retry_logic():
    """Test that workflow retries on critical issues"""
    
    workflow = ChapterWorkflow()
    
    # State will have critical issues first iteration
    initial_state = ChapterState(
        beat_id=1,
        story_bible_id=1,
        beat_description="Contradictory scenario",
        beat_title="Test",
        target_word_count=2500,
        world_rules=[],
        character_profiles=[],
        previous_summaries=[],
        prose_style={}
    )
    
    config = {"configurable": {"thread_id": "test-retry"}}
    
    final_state = await workflow.run(initial_state, config)
    
    # Should have iterated
    assert final_state.iteration > 0, "Should have retried"
    assert final_state.iteration <= 3, "Should respect max iterations"
```

### Database Integration Tests

```python
# tests/test_integration/test_database.py
import pytest
from django.db import transaction
from apps.bfagent.models_story import StoryBible, Chapter, ChapterBeat

@pytest.mark.django_db
def test_story_bible_validation():
    """Test database-level validation"""
    
    bible = StoryBible.objects.create(
        title="Test",
        genre="Sci-Fi",
        world_rules=[
            {"rule": "No time travel"},
            {"rule": "Invalid"}  # Missing established_in
        ]
    )
    
    errors = bible.validate_business_rules()
    assert len(errors) > 0

@pytest.mark.django_db
def test_chapter_unique_constraint():
    """Test unique constraint on chapter numbers"""
    
    bible = StoryBible.objects.create(
        title="Test",
        genre="Sci-Fi"
    )
    
    Chapter.objects.create(
        story_bible=bible,
        chapter_number=1,
        title="Ch1",
        content="Content",
        word_count=100
    )
    
    # Duplicate chapter_number should fail
    with pytest.raises(IntegrityError):
        Chapter.objects.create(
            story_bible=bible,
            chapter_number=1,
            title="Ch1 Duplicate",
            content="Content",
            word_count=100
        )

@pytest.mark.django_db
def test_transaction_rollback():
    """Test that errors rollback transactions"""
    
    bible = StoryBible.objects.create(
        title="Test",
        genre="Sci-Fi"
    )
    
    try:
        with transaction.atomic():
            Chapter.objects.create(
                story_bible=bible,
                chapter_number=1,
                title="Ch1",
                content="Content",
                word_count=100
            )
            
            # Force error
            raise Exception("Test error")
    
    except Exception:
        pass
    
    # Chapter should not exist
    assert Chapter.objects.count() == 0
```

---

## 🌐 E2E Testing

### Browser Tests (Playwright)

```python
# tests/test_e2e/test_chapter_generation.py
import pytest
from playwright.async_api import async_playwright

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_user_generates_chapter():
    """Test complete user journey for chapter generation"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Login
        await page.goto("http://localhost:8000/login/")
        await page.fill("#id_username", "testuser")
        await page.fill("#id_password", "testpass")
        await page.click("button[type=submit]")
        
        # Navigate to chapter generation
        await page.goto("http://localhost:8000/story/beats/")
        await page.click("text=Generate Chapter")
        
        # Fill form
        await page.select_option("#id_beat", "1")
        await page.click("button:has-text('Generate')")
        
        # Wait for generation (poll for completion)
        await page.wait_for_selector("text=Generation Complete", timeout=120000)
        
        # Verify chapter was created
        await page.click("text=View Chapter")
        content = await page.text_content(".chapter-content")
        assert len(content) > 1000, "Chapter should have content"
        
        await browser.close()
```

---

## ⚡ Performance Testing

### Load Testing (Locust)

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class StoryEngineUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login"""
        self.client.post("/login/", {
            "username": "testuser",
            "password": "testpass"
        })
    
    @task(3)
    def view_chapters(self):
        """View chapter list"""
        self.client.get("/story/chapters/")
    
    @task(1)
    def generate_chapter(self):
        """Generate chapter"""
        response = self.client.post("/api/chapters/generate/", json={
            "beat_id": 1
        })
        
        if response.status_code == 200:
            task_id = response.json()['task_id']
            
            # Poll for completion
            for _ in range(30):
                status = self.client.get(f"/api/chapters/status/{task_id}/")
                if status.json()['state'] == 'completed':
                    break
                self.wait()
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_storyengine
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-django pytest-asyncio pytest-cov
      
      - name: Run migrations
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/test_storyengine
        run: python manage.py migrate
      
      - name: Run unit tests
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/test_storyengine
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/ \
            -v \
            --cov=apps/story_engine \
            --cov=apps/bfagent \
            --cov-report=xml \
            --cov-report=term \
            -m "not integration and not e2e"
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
  
  integration:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run integration tests
        run: |
          pytest tests/ \
            -v \
            -m integration \
            --maxfail=1
```

---

## 📚 See Also

- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System architecture
- [ERROR_HANDLING.md](./ERROR_HANDLING.md) - Error handling
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Deployment

---

**Testing Strategy Version**: 1.0  
**Last Updated**: 2025-11-09  
**Status**: Production-Ready Strategy
