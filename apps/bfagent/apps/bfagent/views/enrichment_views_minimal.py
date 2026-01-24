"""
MINIMAL Handler-Based Enrichment View
Pure handler-first architecture - NO database lookups for actions
"""

import json
import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from pydantic import ValidationError as PydanticValidationError

from apps.bfagent.handlers import EnrichmentHandler, ProjectInputHandler, ValidationError, ProcessingError
from apps.bfagent.handlers.base_models import EnrichmentInput, EnrichmentOutput
from apps.bfagent.models import BookProjects

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def minimal_enrich_run(request, pk):
    """
    MINIMAL: Test handler-based enrichment WITH PYDANTIC VALIDATION
    
    This view demonstrates pure handler-first architecture:
    - ✅ Pydantic input validation
    - ✅ NO AgentAction database lookups
    - ✅ NO PromptTemplate database lookups
    - ✅ Direct handler invocation
    - ✅ Performance tracking
    """
    import time
    start_time = time.time()
    
    try:
        # Step 1: Validate project exists
        project = get_object_or_404(BookProjects, pk=pk)
        
        # Step 2: Validate input with Pydantic
        try:
            input_data = EnrichmentInput(
                project_id=pk,
                action=request.POST.get('action'),
                agent_id=request.POST.get('agent_id', 1),
                requirements=request.POST.get('requirements', '')
            )
            logger.info(f"✅ Input validated: {input_data.action}")
        except PydanticValidationError as e:
            logger.warning(f"❌ Validation failed: {e}")
            errors = []
            for error in e.errors():
                field = error['loc'][0]
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            return HttpResponse(
                f"<div class='alert alert-danger'><strong>Validation Error:</strong><br>{'<br>'.join(errors)}</div>",
                status=400
            )
        
        # Step 3: Prepare context using validated input
        input_handler = ProjectInputHandler()
        context = input_handler.prepare_enrichment_context(
            project_id=input_data.project_id,
            agent_id=input_data.agent_id,
            action=input_data.action,
            parameters={'requirements': input_data.requirements}
        )
        
        logger.info(f"✅ Context prepared for action: {input_data.action}")
        
        # Step 4: Execute via EnrichmentHandler
        enrichment_handler = EnrichmentHandler()
        result = enrichment_handler.execute(context)
        
        # Step 5: Track performance
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"✅ Handler executed in {duration_ms:.2f}ms")
        
        # Step 6: Return enhanced HTML response with performance metrics
        return HttpResponse(f"""
            <div class='alert alert-success'>
                <h4>✅ Handler Execution Successful!</h4>
                <p><strong>Action:</strong> {input_data.action}</p>
                <p><strong>Project:</strong> {project.title}</p>
                <p><strong>Performance:</strong> {duration_ms:.2f}ms</p>
                <p><strong>Validated Input:</strong></p>
                <ul>
                    <li>Project ID: {input_data.project_id}</li>
                    <li>Agent ID: {input_data.agent_id}</li>
                    <li>Requirements: {input_data.requirements[:50]}...</li>
                </ul>
                <p><strong>Result:</strong></p>
                <pre>{json.dumps(result, indent=2)}</pre>
            </div>
        """)
        
    except ValidationError as e:
        logger.warning(f"⚠️ Validation error: {e}")
        return HttpResponse(
            f"<div class='alert alert-danger'>Validation Error: {e}</div>",
            status=400
        )
    
    except ProcessingError as e:
        logger.error(f"❌ Processing error: {e}")
        return HttpResponse(
            f"<div class='alert alert-danger'>Processing Error: {e}</div>",
            status=500
        )
    
    except Exception as e:
        logger.exception(f"💥 Unexpected error: {e}")
        return HttpResponse(
            f"<div class='alert alert-danger'>Error: {e}</div>",
            status=500
        )


@require_http_methods(["POST"])
def minimal_enrich_execute(request, pk):
    """
    MINIMAL: Apply enrichment results
    
    For now, just echoes back what would be applied
    """
    try:
        project = get_object_or_404(BookProjects, pk=pk)
        
        action = request.POST.get('action')
        result_data = request.POST.get('result_data', '{}')
        
        logger.info(f"📝 Would apply results for: {action}")
        
        return HttpResponse(f"""
            <div class='alert alert-info'>
                <h4>📝 Execute Handler (Placeholder)</h4>
                <p>Would apply results for action: {action}</p>
                <p>Project: {project.title}</p>
                <p>This is a minimal implementation - actual persistence coming next!</p>
            </div>
        """)
        
    except Exception as e:
        logger.exception(f"Error in execute: {e}")
        return HttpResponse(
            f"<div class='alert alert-danger'>Error: {e}</div>",
            status=500
        )
