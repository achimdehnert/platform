"""
Requirement Analyzer Service
============================

Analyzes requirements and logs MCP tool usage.
Used by Celery tasks for auto-processing.

Includes:
- analyze_requirement: Quality and feasibility check
- check_workflow_rules: Compliance validation
- generate_cascade_context: Enhanced context generation
- work_on_requirement: LLM-powered task execution
"""

from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import structlog

logger = structlog.get_logger(__name__)


def analyze_requirement(requirement) -> dict:
    """
    Analyze a requirement for quality, feasibility, and suggestions.
    
    Args:
        requirement: TestRequirement instance
        
    Returns:
        Dict with analysis results
    """
    from apps.bfagent.models_testing import MCPUsageLog
    
    start_time = timezone.now()
    
    try:
        analysis = {
            'quality_score': 0,
            'issues': [],
            'suggestions': [],
            'feasibility': 'unknown',
        }
        
        # Check name quality
        if len(requirement.name) < 10:
            analysis['issues'].append('Name ist zu kurz (< 10 Zeichen)')
        elif len(requirement.name) > 100:
            analysis['issues'].append('Name ist zu lang (> 100 Zeichen)')
        else:
            analysis['quality_score'] += 20
        
        # Check description
        if not requirement.description:
            analysis['issues'].append('Keine Beschreibung vorhanden')
        elif len(requirement.description) < 50:
            analysis['issues'].append('Beschreibung ist zu kurz (< 50 Zeichen)')
            analysis['quality_score'] += 10
        else:
            analysis['quality_score'] += 25
        
        # Check acceptance criteria
        if not requirement.acceptance_criteria:
            analysis['issues'].append('Keine Akzeptanzkriterien definiert')
            analysis['suggestions'].append('Füge mindestens 2-3 Akzeptanzkriterien hinzu')
        else:
            criteria_count = len(requirement.acceptance_criteria)
            if criteria_count < 2:
                analysis['issues'].append(f'Nur {criteria_count} Akzeptanzkriterium - mehr empfohlen')
                analysis['quality_score'] += 10
            else:
                analysis['quality_score'] += 25
        
        # Check domain
        if requirement.domain:
            analysis['quality_score'] += 10
        else:
            analysis['suggestions'].append('Domain zuweisen für bessere Kategorisierung')
        
        # Check priority
        if requirement.priority in ['critical', 'high']:
            analysis['suggestions'].append('Hohe Priorität - zeitnah bearbeiten')
        
        # Feasibility assessment
        if analysis['quality_score'] >= 70:
            analysis['feasibility'] = 'high'
        elif analysis['quality_score'] >= 40:
            analysis['feasibility'] = 'medium'
        else:
            analysis['feasibility'] = 'low'
        
        # Log MCP usage
        duration_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        MCPUsageLog.objects.create(
            tool_name='analyze_requirement',
            tool_category='bfagent',
            arguments={'requirement_id': str(requirement.pk)},
            result_summary=f"Score: {analysis['quality_score']}, Feasibility: {analysis['feasibility']}",
            status='success',
            duration_ms=duration_ms,
            requirement=requirement,
            initiative=requirement.initiative
        )
        
        logger.info(
            "requirement_analyzed",
            requirement_id=str(requirement.pk),
            quality_score=analysis['quality_score'],
            feasibility=analysis['feasibility']
        )
        
        return analysis
        
    except Exception as e:
        # Log error
        MCPUsageLog.objects.create(
            tool_name='analyze_requirement',
            tool_category='bfagent',
            arguments={'requirement_id': str(requirement.pk)},
            status='error',
            error_message=str(e),
            requirement=requirement
        )
        logger.error("requirement_analysis_failed", error=str(e))
        return {'error': str(e)}


def check_workflow_rules(requirement) -> dict:
    """
    Check if requirement follows workflow rules and best practices.
    
    Args:
        requirement: TestRequirement instance
        
    Returns:
        Dict with violations and suggestions
    """
    from apps.bfagent.models_testing import MCPUsageLog
    
    start_time = timezone.now()
    
    try:
        result = {
            'compliant': True,
            'violations': [],
            'warnings': [],
            'suggestions': [],
        }
        
        # Rule 1: Bug fixes need actual/expected behavior
        if requirement.category == 'bug_fix':
            if not requirement.actual_behavior:
                result['violations'].append('Bug-Fix ohne "Actual Behavior" Beschreibung')
                result['compliant'] = False
            if not requirement.expected_behavior:
                result['violations'].append('Bug-Fix ohne "Expected Behavior" Beschreibung')
                result['compliant'] = False
            if not requirement.url:
                result['warnings'].append('Bug-Fix ohne URL - wo tritt der Bug auf?')
        
        # Rule 2: Features should have acceptance criteria
        if requirement.category == 'feature':
            if not requirement.acceptance_criteria:
                result['violations'].append('Feature ohne Akzeptanzkriterien')
                result['compliant'] = False
        
        # Rule 3: High priority needs initiative
        if requirement.priority in ['critical', 'high'] and not requirement.initiative:
            result['warnings'].append('Hohe Priorität ohne Initiative-Zuordnung')
        
        # Rule 4: In-progress should have recent activity
        if requirement.status == 'in_progress':
            from datetime import timedelta
            stale_threshold = timezone.now() - timedelta(days=7)
            if requirement.updated_at < stale_threshold:
                result['warnings'].append('Requirement seit 7+ Tagen ohne Update')
        
        # Log MCP usage
        duration_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        MCPUsageLog.objects.create(
            tool_name='check_workflow_rules',
            tool_category='bfagent',
            arguments={'requirement_id': str(requirement.pk)},
            result_summary=f"Compliant: {result['compliant']}, Violations: {len(result['violations'])}",
            status='success',
            duration_ms=duration_ms,
            requirement=requirement,
            initiative=requirement.initiative
        )
        
        return result
        
    except Exception as e:
        MCPUsageLog.objects.create(
            tool_name='check_workflow_rules',
            tool_category='bfagent',
            arguments={'requirement_id': str(requirement.pk)},
            status='error',
            error_message=str(e),
            requirement=requirement
        )
        return {'error': str(e)}


def generate_cascade_context(requirement) -> str:
    """
    Generate enhanced context for Cascade autonomous work.
    
    Args:
        requirement: TestRequirement instance
        
    Returns:
        Formatted context string
    """
    from apps.bfagent.models_testing import MCPUsageLog
    
    start_time = timezone.now()
    
    # Run analysis
    analysis = analyze_requirement(requirement)
    rules = check_workflow_rules(requirement)
    
    context = f"""## 🎯 Cascade Task: {requirement.name}

**Requirement ID:** `{requirement.pk}`
**Domain:** {requirement.domain or 'Nicht zugewiesen'}
**Category:** {requirement.category}
**Priority:** {requirement.priority}
**Status:** {requirement.status}

### 📊 Requirement-Analyse (Score: {analysis.get('quality_score', 'N/A')}/100)

**Feasibility:** {analysis.get('feasibility', 'unknown').upper()}

"""
    
    if analysis.get('issues'):
        context += "**Issues:**\n"
        for issue in analysis['issues']:
            context += f"- ⚠️ {issue}\n"
        context += "\n"
    
    if analysis.get('suggestions'):
        context += "**Suggestions:**\n"
        for suggestion in analysis['suggestions']:
            context += f"- 💡 {suggestion}\n"
        context += "\n"
    
    if rules.get('violations'):
        context += "### ❌ Workflow Violations\n"
        for violation in rules['violations']:
            context += f"- {violation}\n"
        context += "\n"
    
    if rules.get('warnings'):
        context += "### ⚠️ Warnings\n"
        for warning in rules['warnings']:
            context += f"- {warning}\n"
        context += "\n"
    
    # Add requirement details
    if requirement.description:
        context += f"### Beschreibung\n{requirement.description}\n\n"
    
    if requirement.category == 'bug_fix':
        if requirement.url:
            context += f"**Bug URL:** {requirement.url}\n"
        if requirement.actual_behavior:
            context += f"**Actual Behavior:** {requirement.actual_behavior}\n"
        if requirement.expected_behavior:
            context += f"**Expected Behavior:** {requirement.expected_behavior}\n"
        context += "\n"
    
    if requirement.acceptance_criteria:
        context += "### Akzeptanzkriterien\n"
        for i, criterion in enumerate(requirement.acceptance_criteria, 1):
            text = criterion.get('text', criterion) if isinstance(criterion, dict) else criterion
            context += f"{i}. {text}\n"
        context += "\n"
    
    context += "---\n\n**Bitte arbeite autonom an diesem Requirement.**\n"
    
    # Log MCP usage
    duration_ms = int((timezone.now() - start_time).total_seconds() * 1000)
    MCPUsageLog.objects.create(
        tool_name='generate_cascade_context',
        tool_category='bfagent',
        arguments={'requirement_id': str(requirement.pk)},
        result_summary=f"Context generated ({len(context)} chars)",
        status='success',
        duration_ms=duration_ms,
        requirement=requirement,
        initiative=requirement.initiative
    )
    
    return context


def work_on_requirement(requirement, analysis: dict = None) -> dict:
    """
    Actually work on a requirement using an LLM.
    
    This function:
    1. Generates a prompt based on the requirement type (bug_fix, feature, etc.)
    2. Calls the configured LLM
    3. Returns the LLM's solution/analysis
    4. Logs token usage to MCPUsageLog
    
    Args:
        requirement: TestRequirement instance
        analysis: Optional pre-computed analysis from analyze_requirement()
        
    Returns:
        Dict with LLM response and metadata
    """
    from apps.bfagent.models_testing import MCPUsageLog
    from apps.bfagent.services.llm_client import generate_text, LlmRequest
    
    start_time = timezone.now()
    
    # Get LLM configuration from requirement or settings
    llm_config = None
    if requirement.llm_override:
        llm_config = requirement.llm_override
    
    # Fallback to default LLM settings
    if not llm_config:
        api_endpoint = getattr(settings, 'OPENAI_API_BASE', 'https://api.openai.com')
        api_key = getattr(settings, 'OPENAI_API_KEY', '')
        model = getattr(settings, 'DEFAULT_LLM_MODEL', 'gpt-4o-mini')
        provider = 'openai'
    else:
        api_endpoint = llm_config.api_endpoint
        api_key = llm_config.api_key
        model = llm_config.model_name
        provider = llm_config.provider
    
    # Build system prompt based on category
    if requirement.category == 'bug_fix':
        system_prompt = """Du bist ein erfahrener Software-Entwickler und Bug-Fixer.
Analysiere den beschriebenen Bug und liefere:
1. **Root Cause Analysis**: Was ist die wahrscheinliche Ursache?
2. **Fix-Strategie**: Wie würdest du den Bug beheben?
3. **Code-Vorschlag**: Konkreter Code oder Pseudo-Code für den Fix
4. **Test-Empfehlung**: Wie kann man verifizieren, dass der Bug behoben ist?

Antworte strukturiert und präzise auf Deutsch."""
    
    elif requirement.category == 'feature':
        system_prompt = """Du bist ein erfahrener Software-Architekt und Entwickler.
Analysiere das Feature-Requirement und liefere:
1. **Architektur-Vorschlag**: Wie würdest du das Feature strukturieren?
2. **Implementierungs-Plan**: Welche Schritte sind nötig?
3. **Code-Vorschlag**: Konkreter Code oder Pseudo-Code für Kernfunktionen
4. **Akzeptanzkriterien-Check**: Werden alle Kriterien erfüllt?

Antworte strukturiert und präzise auf Deutsch."""
    
    else:
        system_prompt = """Du bist ein erfahrener Software-Entwickler.
Analysiere das Requirement und liefere einen konkreten Lösungsvorschlag.
Antworte strukturiert und präzise auf Deutsch."""
    
    # Build user prompt with requirement details
    user_prompt = f"""## Requirement: {requirement.name}

**ID:** {requirement.pk}
**Kategorie:** {requirement.category}
**Priorität:** {requirement.priority}
**Domain:** {requirement.domain or 'Nicht zugewiesen'}

"""
    
    if requirement.description:
        user_prompt += f"### Beschreibung\n{requirement.description}\n\n"
    
    if requirement.category == 'bug_fix':
        if requirement.url:
            user_prompt += f"**Bug gefunden auf:** {requirement.url}\n"
        if requirement.actual_behavior:
            user_prompt += f"**Actual Behavior:** {requirement.actual_behavior}\n"
        if requirement.expected_behavior:
            user_prompt += f"**Expected Behavior:** {requirement.expected_behavior}\n"
        user_prompt += "\n"
    
    if requirement.acceptance_criteria:
        user_prompt += "### Akzeptanzkriterien\n"
        for i, criterion in enumerate(requirement.acceptance_criteria, 1):
            text = criterion.get('text', criterion) if isinstance(criterion, dict) else criterion
            user_prompt += f"{i}. {text}\n"
        user_prompt += "\n"
    
    # Add analysis if available
    if analysis:
        user_prompt += f"\n### Voranalyse\n"
        user_prompt += f"- Quality Score: {analysis.get('quality_score', 'N/A')}/100\n"
        user_prompt += f"- Feasibility: {analysis.get('feasibility', 'unknown')}\n"
        if analysis.get('issues'):
            user_prompt += f"- Issues: {', '.join(analysis['issues'][:3])}\n"
    
    user_prompt += "\n---\n\nBitte arbeite an diesem Requirement und liefere einen konkreten Lösungsvorschlag."
    
    try:
        # Call LLM
        llm_request = LlmRequest(
            provider=provider,
            api_endpoint=api_endpoint,
            api_key=api_key,
            model=model,
            system=system_prompt,
            prompt=user_prompt,
            temperature=0.7,
            max_tokens=2000
        )
        
        result = generate_text(llm_request)
        
        duration_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        
        # Extract token info from raw response if available
        tokens_input = 0
        tokens_output = 0
        if result.get('raw'):
            usage = result['raw'].get('usage', {})
            tokens_input = usage.get('prompt_tokens', 0)
            tokens_output = usage.get('completion_tokens', 0)
        
        # Log MCP usage with LLM details
        MCPUsageLog.objects.create(
            tool_name='work_on_requirement',
            tool_category='llm',
            arguments={
                'requirement_id': str(requirement.pk),
                'model': model,
                'category': requirement.category
            },
            result_summary=f"LLM response: {len(result.get('text', '') or '')} chars" if result.get('ok') else f"Error: {result.get('error', 'Unknown')}",
            status='success' if result.get('ok') else 'error',
            error_message=result.get('error') if not result.get('ok') else '',
            duration_ms=duration_ms,
            requirement=requirement,
            initiative=requirement.initiative,
            llm_model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_input + tokens_output
        )
        
        logger.info(
            "requirement_llm_work_completed",
            requirement_id=str(requirement.pk),
            model=model,
            ok=result.get('ok'),
            tokens=tokens_input + tokens_output,
            duration_ms=duration_ms
        )
        
        return {
            'ok': result.get('ok', False),
            'response': result.get('text'),
            'model': model,
            'tokens_input': tokens_input,
            'tokens_output': tokens_output,
            'duration_ms': duration_ms,
            'error': result.get('error')
        }
        
    except Exception as e:
        duration_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        
        MCPUsageLog.objects.create(
            tool_name='work_on_requirement',
            tool_category='llm',
            arguments={'requirement_id': str(requirement.pk)},
            status='error',
            error_message=str(e),
            duration_ms=duration_ms,
            requirement=requirement,
            initiative=requirement.initiative
        )
        
        logger.error("requirement_llm_work_failed", requirement_id=str(requirement.pk), error=str(e))
        
        return {
            'ok': False,
            'response': None,
            'error': str(e),
            'duration_ms': duration_ms
        }
