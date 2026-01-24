# Handler System Usage Examples

## 📚 Complete Integration Example

### 1. Character Cast Generation (Complete Flow)

```python
# apps/bfagent/views/enrichment_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse

from apps.bfagent.handlers import HandlerRegistry
from apps.bfagent.handlers.input_handlers import ProjectInputHandler
from apps.bfagent.handlers.processing_handlers import EnrichmentHandler
from apps.bfagent.handlers.output_handlers import CharacterOutputHandler


@login_required
def generate_character_cast(request, project_id):
    """Generate character cast using handler system"""
    
    try:
        registry = HandlerRegistry()
        
        # 1. INPUT HANDLER - Prepare context
        input_handler = ProjectInputHandler()
        context = input_handler.prepare_enrichment_context(
            project_id=project_id,
            agent_id=request.POST.get('agent_id'),
            action='generate_character_cast',
            parameters={'count': request.POST.get('character_count', 4)}
        )
        
        # 2. PROCESSING HANDLER - Generate characters
        processing_handler = EnrichmentHandler()
        result = processing_handler.execute(context)
        
        # 3. OUTPUT HANDLER - Save to database
        output_handler = CharacterOutputHandler()
        
        if result['success']:
            characters = output_handler.bulk_create(result['characters'])
            
            return JsonResponse({
                'success': True,
                'message': f"Created {len(characters)} characters",
                'characters': [
                    {
                        'id': char.id,
                        'name': char.name,
                        'role': char.role
                    } for char in characters
                ]
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }, status=400)
            
    except Exception as e:
        logger.exception(f"Failed to generate character cast: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
```

### 2. Project CRUD with Handlers

```python
# apps/bfagent/views/project_views.py
from apps.bfagent.handlers.input_handlers import ProjectInputHandler
from apps.bfagent.handlers.output_handlers import ProjectOutputHandler


@login_required
def project_create(request):
    """Create new project using handlers"""
    
    if request.method == 'POST':
        try:
            # INPUT HANDLER
            input_handler = ProjectInputHandler()
            cleaned_data = input_handler.process(request.POST.dict())
            
            # OUTPUT HANDLER
            output_handler = ProjectOutputHandler()
            project = output_handler.save(cleaned_data)
            
            messages.success(request, f"Project '{project.title}' created!")
            return redirect('bfagent:project-detail', pk=project.id)
            
        except ValidationError as e:
            messages.error(request, f"Validation failed: {e}")
        except OutputError as e:
            messages.error(request, f"Failed to save: {e}")
    
    return render(request, 'bfagent/project_form.html')


@login_required
def project_update(request, pk):
    """Update project using handlers"""
    
    if request.method == 'POST':
        try:
            # INPUT HANDLER
            input_handler = ProjectInputHandler()
            data = request.POST.dict()
            data['id'] = pk  # Add ID for update
            cleaned_data = input_handler.process(data)
            
            # OUTPUT HANDLER
            output_handler = ProjectOutputHandler()
            project = output_handler.save(cleaned_data)
            
            messages.success(request, "Project updated!")
            return redirect('bfagent:project-detail', pk=project.id)
            
        except ValidationError as e:
            messages.error(request, f"Validation failed: {e}")
        except OutputError as e:
            messages.error(request, f"Failed to save: {e}")
    
    project = get_object_or_404(BookProjects, pk=pk)
    return render(request, 'bfagent/project_form.html', {'project': project})
```

### 3. Enrichment with Field Updates

```python
@login_required
def enrich_project_description(request, project_id):
    """Enhance project description using AI"""
    
    try:
        # INPUT HANDLER
        input_handler = ProjectInputHandler()
        context = input_handler.prepare_enrichment_context(
            project_id=project_id,
            agent_id=request.POST.get('agent_id'),
            action='enhance_description'
        )
        
        # PROCESSING HANDLER
        processing_handler = EnrichmentHandler()
        result = processing_handler.execute(context)
        
        # OUTPUT HANDLER - Update specific field
        if result['success']:
            output_handler = ProjectOutputHandler()
            append = request.POST.get('append', 'false') == 'true'
            
            project = output_handler.save_enrichment_result(
                project_id=project_id,
                field='description',
                value=result['enhanced_description'],
                append=append
            )
            
            return JsonResponse({
                'success': True,
                'description': project.description
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
```

### 4. Bulk Character Creation

```python
@login_required
def bulk_create_characters(request, project_id):
    """Create multiple characters at once"""
    
    import json
    
    try:
        characters_data = json.loads(request.body)
        
        # INPUT HANDLER - Validate bulk data
        input_handler = CharacterInputHandler()
        cleaned_characters = input_handler.prepare_bulk_creation(
            characters_data=characters_data,
            project_id=project_id
        )
        
        # OUTPUT HANDLER - Bulk create
        output_handler = CharacterOutputHandler()
        characters = output_handler.bulk_create(cleaned_characters)
        
        return JsonResponse({
            'success': True,
            'count': len(characters),
            'characters': [{'id': c.id, 'name': c.name} for c in characters]
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
```

## 🧪 Testing Handlers

### Unit Test Example

```python
# tests/test_handlers/test_project_input_handler.py
import pytest
from apps.bfagent.handlers.input_handlers import ProjectInputHandler
from apps.bfagent.handlers.base import ValidationError


def test_project_input_validation():
    """Test project input validation"""
    handler = ProjectInputHandler()
    
    # Valid data
    data = {
        'title': 'Test Project',
        'genre': 'Fantasy',
        'target_word_count': 50000,
        'status': 'planning'
    }
    assert handler.validate(data) is True
    
    # Invalid data - no title
    with pytest.raises(ValidationError):
        handler.validate({'genre': 'Fantasy'})


def test_project_input_processing():
    """Test project data processing"""
    handler = ProjectInputHandler()
    
    data = {
        'title': '  Test Project  ',  # Extra whitespace
        'genre': 'Fantasy',
        'target_word_count': '50000',  # String number
        'status': 'planning'
    }
    
    cleaned = handler.process(data)
    
    assert cleaned['title'] == 'Test Project'  # Trimmed
    assert cleaned['target_word_count'] == 50000  # Int
```

### Integration Test Example

```python
# tests/test_handlers/test_enrichment_flow.py
import pytest
from django.test import TestCase
from apps.bfagent.models import BookProjects, Characters
from apps.bfagent.handlers.input_handlers import ProjectInputHandler
from apps.bfagent.handlers.processing_handlers import EnrichmentHandler
from apps.bfagent.handlers.output_handlers import CharacterOutputHandler


class EnrichmentFlowTest(TestCase):
    """Test complete enrichment flow"""
    
    def setUp(self):
        self.project = BookProjects.objects.create(
            title='Test Project',
            genre='Fantasy',
            target_word_count=50000,
            status='planning'
        )
    
    def test_character_cast_generation(self):
        """Test full character cast generation flow"""
        
        # Input Handler
        input_handler = ProjectInputHandler()
        context = input_handler.prepare_enrichment_context(
            project_id=self.project.id,
            agent_id=1,
            action='generate_character_cast'
        )
        
        # Processing Handler
        processing_handler = EnrichmentHandler()
        result = processing_handler.execute(context)
        
        assert result['success'] is True
        assert len(result['characters']) > 0
        
        # Output Handler
        output_handler = CharacterOutputHandler()
        characters = output_handler.bulk_create(result['characters'])
        
        assert len(characters) > 0
        assert all(c.project_id == self.project.id for c in characters)
```

## 🎯 Best Practices

### 1. Always Use Handlers in This Order
```python
# 1. Input Handler - Validate & Prepare
# 2. Processing Handler - Execute Logic
# 3. Output Handler - Persist Results
```

### 2. Handle Exceptions Properly
```python
try:
    # Handler operations
except ValidationError as e:
    # User input error - show to user
except ProcessingError as e:
    # Business logic error - log and notify
except OutputError as e:
    # Database error - log and rollback
```

### 3. Use Registry for Handler Management
```python
registry = HandlerRegistry()
registry.register_processing_handler('my_handler', MyHandler())
handler = registry.get_processing_handler('my_handler')
```

### 4. Log Everything
```python
logger.info(f"Processing started: {context}")
logger.info(f"Processing completed: {result}")
logger.error(f"Processing failed: {error}")
```

## 📝 Migration Checklist

When converting existing views to handlers:

- [ ] Identify input validation logic → InputHandler
- [ ] Identify business logic → ProcessingHandler
- [ ] Identify database operations → OutputHandler
- [ ] Add error handling for all exceptions
- [ ] Add logging at key points
- [ ] Write unit tests for each handler
- [ ] Write integration test for flow
- [ ] Update view to use handlers
- [ ] Update documentation
