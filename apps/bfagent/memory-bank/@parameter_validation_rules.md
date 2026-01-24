# Parameter Validation Rules - Proactive Bug Prevention

## 🛡️ VALIDATION PATTERN
**Regel**: Jede Django View MUSS Parameter-Validierung implementieren

## 📋 STANDARD TEMPLATE
```python
def view_function(request, **kwargs):
    """View with mandatory parameter validation"""
    try:
        # 1. REQUIRED PARAMETERS CHECK
        required_params = ['param1', 'param2', 'param3']
        missing_params = []

        for param in required_params:
            if request.method == 'POST':
                value = request.POST.get(param)
            else:
                value = request.GET.get(param)

            if not value:
                missing_params.append(param)

        if missing_params:
            return JsonResponse({
                'success': False,
                'error': f'Missing required parameters: {", ".join(missing_params)}',
                'required': required_params
            }, status=400)

        # 2. PARAMETER TYPE VALIDATION
        # Add type checks here

        # 3. BUSINESS LOGIC
        # Main function logic here

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
```

## 🎯 IMPLEMENTATION EXAMPLE
**File**: `agents_ui/views.py` - `agent_edit_content`
```python
# 1. REQUIRED PARAMETERS CHECK (following Memory-Bank validation pattern)
required_params = ['key', 'selected_agent', 'instructions', 'current_content']
missing_params = []
param_values = {
    'key': key,
    'selected_agent': selected_agent,
    'instructions': instructions,
    'current_content': current_content
}

for param in required_params:
    if not param_values[param]:
        missing_params.append(param)

if missing_params:
    return JsonResponse({
        'success': False,
        'error': f'Missing required parameters: {", ".join(missing_params)}',
        'required': required_params,
        'received': {k: bool(v) for k, v in param_values.items()}
    }, status=400)
```

## 🔍 VALIDATION CHECKLIST
- [ ] All POST/GET parameters validated
- [ ] Clear error messages with missing parameter names
- [ ] HTTP status codes (400 for validation, 500 for server errors)
- [ ] Consistent error response format
- [ ] Traceback for debugging in development

## 📈 BENEFITS
- Proactive bug prevention
- Better user experience with clear error messages
- Easier debugging with parameter lists
- Consistent error handling across all views

## 🚨 COMMON PATTERNS
### HTMX Views
```python
if request.htmx:
    return render(request, 'template.html', context)  # ✅ Direct HTML
    # NOT: return JsonResponse({'html': html})        # ❌ JSON-wrapped
```

### Agent Execution Views
```python
required_params = ['book_id', 'agent_type', 'content']
# Always validate agent_type against AVAILABLE_AGENTS
if agent_type not in AVAILABLE_AGENTS:
    return JsonResponse({
        'success': False,
        'error': f'Invalid agent type: {agent_type}',
        'available_agents': list(AVAILABLE_AGENTS.keys())
    }, status=400)
```

## 🎯 ENFORCEMENT
**Memory-Bank-Regel**: Jede neue Django View MUSS dieses Pattern implementieren
**Code Review**: Parameter-Validierung ist Pflicht vor Deployment
