# ACTION-FIRST Enrichment System

## 🎯 Overview

The ACTION-FIRST approach prioritizes **user intent** over technical implementation details. Users select **what they want to accomplish** (action), and the system automatically assigns the appropriate agent.

---

## 🔄 Architecture

```
User → Selects ACTION → System resolves Agent → LLM generates content → EnrichmentResponse
```

### **Key Components:**

1. **PhaseActionConfig** - Defines which actions are available in which workflow phase
2. **AgentAction** - Defines action metadata, target model, and allowed fields
3. **EnrichmentResponse** - Stores suggestions with edit-before-apply workflow
4. **Context Providers** - Resolves template variables from database

---

## 📊 Database Schema

```sql
-- Phase defines which actions are available
PhaseActionConfig:
  - phase (FK → WorkflowPhase)
  - action (FK → AgentAction)
  - is_required (Boolean)
  - order (Integer)

-- Action defines what can be done
AgentAction:
  - agent (FK → Agents)
  - name (String)
  - display_name (String)
  - target_model (String: 'project', 'chapter', etc.)
  - target_fields (JSON: ['outline', 'unique_elements'])
  - prompt_template (FK → PromptTemplate)

-- Response tracks suggestions
EnrichmentResponse:
  - project (FK → BookProjects)
  - agent (FK → Agents)
  - action (FK → AgentAction)
  - field_name (String)
  - suggested_value (Text)
  - edited_value (Text)
  - status (pending/edited/applied/rejected)
```

---

## 🔧 Implementation

### **1. View: Load Actions**

```python
def project_enrich_panel(request, pk):
    # Get actions from PhaseActionConfig
    action_configs = PhaseActionConfig.objects.filter(
        phase=current_phase
    ).select_related('action', 'action__agent')
    
    available_actions = []
    for config in action_configs:
        available_actions.append({
            'action': config.action,
            'agent': config.action.agent,
            'is_required': config.is_required,
        })
    
    return render(request, 'enrich_panel.html', {
        'available_actions': available_actions
    })
```

### **2. Template: Action Dropdown**

```html
<select name="action" onchange="setAgentId(this)">
  {% for item in available_actions %}
  <option value="{{ item.action.name }}" 
          data-agent-id="{{ item.agent.id }}">
    {{ item.action.display_name }} ({{ item.agent.name }})
  </option>
  {% endfor %}
</select>

<input type="hidden" name="agent_id" id="hidden_agent_id">

<script>
function setAgentId(select) {
  const agentId = select.options[select.selectedIndex].getAttribute('data-agent-id');
  document.getElementById('hidden_agent_id').value = agentId;
}
</script>
```

### **3. View: Run Enrichment**

```python
def project_enrich_run(request, pk):
    action = request.POST.get('action')
    agent_id = request.POST.get('agent_id')
    
    # Run LLM
    result = run_enrichment(
        project=project,
        agent=agent,
        action=action
    )
    
    # Save to EnrichmentResponse
    for suggestion in result['suggestions']:
        EnrichmentResponse.objects.create(
            project=project,
            agent=agent,
            action_name=action,
            field_name=suggestion['field_name'],
            suggested_value=suggestion['new_value'],
            confidence=suggestion['confidence'],
            rationale=suggestion['rationale'],
            status='pending'
        )
    
    return render('enrich_result.html', {'suggestions': suggestions})
```

### **4. View: Apply Suggestion**

```python
def project_enrich_apply(request, pk):
    response_id = request.POST.get('response_id')
    edited_value = request.POST.get('edited_value')
    
    response = EnrichmentResponse.objects.get(id=response_id)
    
    # Update if user edited
    if edited_value:
        response.edited_value = edited_value
        response.status = 'edited'
        response.save()
    
    # Apply to target model
    response.apply_to_target(user=request.user)
    
    return redirect('project-detail', pk=pk)
```

---

## 🎯 Benefits

### **For Users:**
- ✅ Task-oriented (not tool-oriented)
- ✅ Clear action names (not technical terms)
- ✅ Edit before apply workflow
- ✅ Full audit trail

### **For System:**
- ✅ Database-driven (no hardcoding)
- ✅ Field validation (target_fields)
- ✅ Extensible (add actions via admin)
- ✅ Context-aware (Context Providers)

---

## 📈 Next Steps

1. ✅ **Migration** - Add fields to AgentAction, create EnrichmentResponse table
2. ✅ **Field Config** - Populate target_model and target_fields for existing actions
3. ✅ **Edit View** - Implement EnrichmentResponse editing UI
4. ✅ **Context Integration** - Ensure next actions can read applied values

---

## 🔍 Example Flow

**Planning Phase → Generate Outline:**

1. User opens Enrichment Panel for Planning phase
2. System shows: "Generate Full Outline (Outline Agent)"
3. User clicks → LLM generates outline
4. System creates EnrichmentResponse (status=pending)
5. User reviews/edits suggestion
6. User clicks "Apply" → Saves to BookProjects.outline
7. Next action can now access outline via Context Provider

---

**Date:** 2025-10-13
**Version:** 2.0.0
