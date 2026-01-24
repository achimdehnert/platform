"""
Control Center - AI Configuration Views
LLMs and Agents management for system administrators
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages

from apps.bfagent.models import Llms, Agents
from apps.bfagent.services.llm_client import LlmRequest, generate_text


@login_required
def llms_list(request):
    """List all configured LLMs"""
    llms = Llms.objects.all().order_by('-is_active', 'name')
    return render(request, 'control_center/ai_config/llms_list.html', {
        'llms': llms,
        'active_count': llms.filter(is_active=True).count(),
        'total_count': llms.count(),
    })


@login_required
def llm_detail(request, pk):
    """LLM detail view with live test capability"""
    llm = get_object_or_404(Llms, pk=pk)
    return render(request, 'control_center/ai_config/llm_detail.html', {
        'llm': llm,
    })


@login_required
@require_http_methods(["GET", "POST"])
def llm_edit(request, pk):
    """Edit LLM configuration"""
    llm = get_object_or_404(Llms, pk=pk)
    
    if request.method == "POST":
        llm.name = request.POST.get('name', llm.name)
        llm.provider = request.POST.get('provider', llm.provider)
        llm.api_endpoint = request.POST.get('api_endpoint', llm.api_endpoint)
        llm.llm_name = request.POST.get('llm_name', llm.llm_name)
        
        # Only update API key if provided (not empty)
        new_api_key = request.POST.get('api_key', '').strip()
        if new_api_key:
            llm.api_key = new_api_key
            
        llm.temperature = float(request.POST.get('temperature', llm.temperature or 0.7))
        llm.max_tokens = int(request.POST.get('max_tokens', llm.max_tokens or 500))
        llm.top_p = float(request.POST.get('top_p', llm.top_p or 0.9))
        llm.cost_per_1k_tokens = float(request.POST.get('cost_per_1k_tokens', llm.cost_per_1k_tokens or 0))
        llm.description = request.POST.get('description', llm.description or '')
        llm.is_active = request.POST.get('is_active') == 'on'
        llm.updated_at = timezone.now()
        llm.save()
        
        messages.success(request, f'LLM "{llm.name}" wurde aktualisiert.')
        return redirect('control_center:llm-detail', pk=pk)
    
    return render(request, 'control_center/ai_config/llm_edit.html', {
        'llm': llm,
    })


@login_required
@require_http_methods(["POST"])
def llm_live_test(request, pk):
    """Live test an LLM with a custom prompt"""
    llm = get_object_or_404(Llms, pk=pk)
    
    try:
        data = json.loads(request.body)
        prompt = data.get("prompt", "").strip()
    except json.JSONDecodeError:
        prompt = request.POST.get("prompt", "").strip()
    
    if not prompt:
        return JsonResponse({
            'success': False,
            'error': 'Prompt ist erforderlich'
        }, status=400)
    
    try:
        llm_request = LlmRequest(
            provider=llm.provider,
            api_endpoint=llm.api_endpoint,
            api_key=llm.api_key,
            model=llm.llm_name,
            system="Du bist ein hilfreicher Assistent.",
            prompt=prompt,
            temperature=llm.temperature or 0.7,
            max_tokens=llm.max_tokens or 500,
        )
        
        response_data = generate_text(llm_request)
        
        if response_data.get("ok"):
            return JsonResponse({
                'success': True,
                'response': response_data.get("text", ""),
                'model': llm.llm_name,
                'latency_ms': response_data.get("latency_ms"),
                'timestamp': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            return JsonResponse({
                'success': False,
                'error': response_data.get("error", "Unbekannter Fehler"),
                'model': llm.llm_name,
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'model': llm.llm_name,
        })


@login_required
@require_http_methods(["POST"])
def llm_toggle_active(request, pk):
    """Toggle LLM active status"""
    llm = get_object_or_404(Llms, pk=pk)
    llm.is_active = not llm.is_active
    llm.save()
    
    status = "aktiviert" if llm.is_active else "deaktiviert"
    messages.success(request, f'LLM "{llm.name}" wurde {status}.')
    
    return redirect('control_center:llm-detail', pk=pk)


@login_required
def agents_list(request):
    """List all configured Agents"""
    agents = Agents.objects.all().order_by('-status', 'name')
    return render(request, 'control_center/ai_config/agents_list.html', {
        'agents': agents,
        'active_count': agents.filter(status='active').count(),
        'total_count': agents.count(),
    })


@login_required
def agent_detail(request, pk):
    """Agent detail view with live test capability"""
    agent = get_object_or_404(Agents, pk=pk)
    # Get associated LLM if any
    llm = None
    if agent.llm_id:
        llm = Llms.objects.filter(pk=agent.llm_id).first()
    
    return render(request, 'control_center/ai_config/agent_detail.html', {
        'agent': agent,
        'llm': llm,
    })


@login_required
@require_http_methods(["POST"])
def agent_live_test(request, pk):
    """Live test an Agent with a custom prompt"""
    agent = get_object_or_404(Agents, pk=pk)
    
    try:
        data = json.loads(request.body)
        prompt = data.get("prompt", "").strip()
    except json.JSONDecodeError:
        prompt = request.POST.get("prompt", "").strip()
    
    if not prompt:
        return JsonResponse({
            'success': False,
            'error': 'Prompt ist erforderlich'
        }, status=400)
    
    # Get the LLM for this agent
    llm = None
    if agent.llm_id:
        llm = Llms.objects.filter(pk=agent.llm_id, is_active=True).first()
    
    if not llm:
        llm = Llms.objects.filter(is_active=True).first()
    
    if not llm:
        return JsonResponse({
            'success': False,
            'error': 'Kein aktives LLM konfiguriert',
        })
    
    try:
        # Build system prompt from agent config
        system_prompt = agent.system_prompt or "Du bist ein hilfreicher Assistent."
        
        llm_request = LlmRequest(
            provider=llm.provider,
            api_endpoint=llm.api_endpoint,
            api_key=llm.api_key,
            model=llm.llm_name,
            system=system_prompt,
            prompt=prompt,
            temperature=agent.temperature or llm.temperature or 0.7,
            max_tokens=agent.max_tokens or llm.max_tokens or 500,
        )
        
        response_data = generate_text(llm_request)
        
        if response_data.get("ok"):
            return JsonResponse({
                'success': True,
                'response': response_data.get("text", ""),
                'agent': agent.name,
                'model': llm.llm_name,
                'latency_ms': response_data.get("latency_ms"),
                'timestamp': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            return JsonResponse({
                'success': False,
                'error': response_data.get("error", "Unbekannter Fehler"),
                'agent': agent.name,
                'model': llm.llm_name,
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'agent': agent.name,
        })


@login_required
@require_http_methods(["GET", "POST"])
def llm_delete(request, pk):
    """Delete an LLM"""
    llm = get_object_or_404(Llms, pk=pk)
    
    if request.method == "POST":
        name = llm.name
        llm.delete()
        messages.success(request, f'LLM "{name}" wurde gelöscht.')
        return redirect('control_center:llms-list')
    
    return render(request, 'control_center/ai_config/llm_delete.html', {
        'llm': llm,
    })


@login_required
@require_http_methods(["GET", "POST"])
def agent_create(request):
    """Create a new Agent"""
    llms = Llms.objects.filter(is_active=True).order_by('name')
    
    if request.method == "POST":
        agent = Agents()
        agent.name = request.POST.get('name', '')
        agent.description = request.POST.get('description', '')
        agent.system_prompt = request.POST.get('system_prompt', '')
        agent.temperature = float(request.POST.get('temperature', 0.7))
        agent.max_tokens = int(request.POST.get('max_tokens', 500))
        agent.status = 'active' if request.POST.get('is_active') == 'on' else 'inactive'
        
        llm_id = request.POST.get('llm_id')
        if llm_id:
            agent.llm_id = int(llm_id)
        
        agent.save()
        messages.success(request, f'Agent "{agent.name}" wurde erstellt.')
        return redirect('control_center:agent-detail', pk=agent.pk)
    
    return render(request, 'control_center/ai_config/agent_create.html', {
        'llms': llms,
    })


@login_required
@require_http_methods(["GET", "POST"])
def agent_edit(request, pk):
    """Edit an Agent"""
    agent = get_object_or_404(Agents, pk=pk)
    llms = Llms.objects.filter(is_active=True).order_by('name')
    
    if request.method == "POST":
        agent.name = request.POST.get('name', agent.name)
        agent.description = request.POST.get('description', agent.description)
        agent.system_prompt = request.POST.get('system_prompt', agent.system_prompt)
        agent.temperature = float(request.POST.get('temperature', agent.temperature or 0.7))
        agent.max_tokens = int(request.POST.get('max_tokens', agent.max_tokens or 500))
        agent.status = 'active' if request.POST.get('is_active') == 'on' else 'inactive'
        
        llm_id = request.POST.get('llm_id')
        agent.llm_id = int(llm_id) if llm_id else None
        
        agent.save()
        messages.success(request, f'Agent "{agent.name}" wurde aktualisiert.')
        return redirect('control_center:agent-detail', pk=pk)
    
    return render(request, 'control_center/ai_config/agent_edit.html', {
        'agent': agent,
        'llms': llms,
    })


@login_required
@require_http_methods(["GET", "POST"])
def agent_delete(request, pk):
    """Delete an Agent"""
    agent = get_object_or_404(Agents, pk=pk)
    
    if request.method == "POST":
        name = agent.name
        agent.delete()
        messages.success(request, f'Agent "{name}" wurde gelöscht.')
        return redirect('control_center:agents-list')
    
    return render(request, 'control_center/ai_config/agent_delete.html', {
        'agent': agent,
    })


@login_required
def llm_create_gemini(request):
    """One-click create Gemini LLM"""
    if Llms.objects.filter(name='Gemini Flash').exists():
        messages.info(request, 'Gemini Flash LLM existiert bereits.')
        llm = Llms.objects.get(name='Gemini Flash')
        return redirect('control_center:llm-detail', pk=llm.pk)
    
    llm = Llms()
    llm.name = 'Gemini Flash'
    llm.provider = 'gemini'
    llm.api_endpoint = 'https://generativelanguage.googleapis.com'
    llm.llm_name = 'gemini-1.5-flash'
    llm.api_key = 'AIzaSyBE0dEjZSZeog4xZKqh3zvTSZXvwBASW28'
    llm.temperature = 0.7
    llm.max_tokens = 1000
    llm.is_active = True
    llm.save()
    
    messages.success(request, f'Gemini Flash LLM wurde erstellt (ID: {llm.pk})!')
    return redirect('control_center:llm-detail', pk=llm.pk)


@login_required
def llm_create_groq(request):
    """One-click create Groq LLM"""
    if Llms.objects.filter(name='Groq Llama 3.3').exists():
        messages.info(request, 'Groq Llama 3.3 LLM existiert bereits.')
        llm = Llms.objects.get(name='Groq Llama 3.3')
        return redirect('control_center:llm-detail', pk=llm.pk)
    
    llm = Llms()
    llm.name = 'Groq Llama 3.3'
    llm.provider = 'groq'
    llm.api_endpoint = 'https://api.groq.com/openai/v1/chat/completions'
    llm.llm_name = 'llama-3.3-70b-versatile'
    llm.api_key = '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'
    llm.temperature = 0.7
    llm.max_tokens = 1000
    llm.is_active = True
    llm.save()
    
    messages.success(request, f'Groq Llama 3.3 LLM wurde erstellt (ID: {llm.pk})!')
    return redirect('control_center:llm-detail', pk=llm.pk)


@login_required
def llm_create_anthropic(request):
    """One-click create Anthropic Claude LLM"""
    if Llms.objects.filter(name='Claude 3.5 Sonnet').exists():
        messages.info(request, 'Claude 3.5 Sonnet LLM existiert bereits.')
        llm = Llms.objects.get(name='Claude 3.5 Sonnet')
        return redirect('control_center:llm-detail', pk=llm.pk)
    
    llm = Llms()
    llm.name = 'Claude 3.5 Sonnet'
    llm.provider = 'anthropic'
    llm.api_endpoint = 'https://api.anthropic.com/v1/messages'
    llm.llm_name = 'claude-3-5-sonnet-20241022'
    llm.api_key = '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'
    llm.temperature = 0.7
    llm.max_tokens = 1000
    llm.is_active = True
    llm.save()
    
    messages.success(request, f'Claude 3.5 Sonnet LLM wurde erstellt (ID: {llm.pk})!')
    return redirect('control_center:llm-detail', pk=llm.pk)


@login_required
def llm_create_all(request):
    """Create all pre-configured LLMs at once"""
    created = []
    
    # Groq
    if not Llms.objects.filter(name='Groq Llama 3.3').exists():
        llm = Llms.objects.create(
            name='Groq Llama 3.3',
            provider='groq',
            api_endpoint='https://api.groq.com/openai/v1/chat/completions',
            llm_name='llama-3.3-70b-versatile',
            api_key='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',
            temperature=0.7,
            max_tokens=1000,
            is_active=True
        )
        created.append(llm.name)
    
    # Anthropic Claude
    if not Llms.objects.filter(name='Claude 3.5 Sonnet').exists():
        llm = Llms.objects.create(
            name='Claude 3.5 Sonnet',
            provider='anthropic',
            api_endpoint='https://api.anthropic.com/v1/messages',
            llm_name='claude-3-5-sonnet-20241022',
            api_key='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',
            temperature=0.7,
            max_tokens=1000,
            is_active=True
        )
        created.append(llm.name)
    
    # Gemini
    if not Llms.objects.filter(name='Gemini Flash').exists():
        llm = Llms.objects.create(
            name='Gemini Flash',
            provider='gemini',
            api_endpoint='https://generativelanguage.googleapis.com',
            llm_name='gemini-1.5-flash',
            api_key='AIzaSyDujqZ7rd_0iu7nfNRhNlLFwSeZhsekPvw',
            temperature=0.7,
            max_tokens=1000,
            is_active=True
        )
        created.append(llm.name)
    
    if created:
        messages.success(request, f'{len(created)} LLMs erstellt: {", ".join(created)}')
    else:
        messages.info(request, 'Alle LLMs existieren bereits.')
    
    return redirect('control_center:llms-list')


@login_required
@require_http_methods(["GET", "POST"])
def llm_create(request):
    """Create a new LLM configuration"""
    if request.method == "POST":
        llm = Llms()
        llm.name = request.POST.get('name', '')
        llm.provider = request.POST.get('provider', 'openai')
        llm.api_endpoint = request.POST.get('api_endpoint', '')
        llm.llm_name = request.POST.get('llm_name', '')
        llm.api_key = request.POST.get('api_key', '')
        llm.temperature = float(request.POST.get('temperature', 0.7))
        llm.max_tokens = int(request.POST.get('max_tokens', 500))
        llm.is_active = request.POST.get('is_active') == 'on'
        # Required fields with defaults
        llm.top_p = float(request.POST.get('top_p', 1.0))
        llm.frequency_penalty = float(request.POST.get('frequency_penalty', 0.0))
        llm.presence_penalty = float(request.POST.get('presence_penalty', 0.0))
        llm.total_tokens_used = 0
        llm.total_requests = 0
        llm.total_cost = 0.0
        llm.cost_per_1k_tokens = float(request.POST.get('cost_per_1k_tokens', 0.0))
        llm.created_at = timezone.now()
        llm.updated_at = timezone.now()
        llm.save()
        
        messages.success(request, f'LLM "{llm.name}" wurde erstellt.')
        return redirect('control_center:llm-detail', pk=llm.pk)
    
    return render(request, 'control_center/ai_config/llm_create.html', {})


@login_required
def ai_config_dashboard(request):
    """AI Configuration Dashboard - Overview of LLMs and Agents"""
    llms = Llms.objects.all()
    agents = Agents.objects.all()
    
    return render(request, 'control_center/ai_config/dashboard.html', {
        'llms_active': llms.filter(is_active=True).count(),
        'llms_total': llms.count(),
        'agents_active': agents.filter(status='active').count(),
        'agents_total': agents.count(),
        'recent_llms': llms.order_by('-id')[:5],
        'recent_agents': agents.order_by('-id')[:5],
    })
