# 🏗️ Domain-Aware Visual Workflow Builder
## Integration mit BF Agent Domain System

## 🎯 PROBLEM STATEMENT

Der aktuelle Visual Workflow Builder PoC ist **zu generisch** für BF Agents **Domain-Driven Architecture**.

### Mismatch:
- **PoC:** Generic Input→Processing→Output Pipeline
- **BF Agent:** Domain-Specific Phases → Actions → Handlers

---

## ✅ LÖSUNG: DOMAIN-AWARE VISUAL BUILDER

### Architektur-Anpassung

```typescript
// Statt Generic Workflow
interface GenericWorkflow {
  input_handlers: Handler[];
  processing_handlers: Handler[];
  output_handlers: Handler[];
}

// NEU: Domain-Aware Workflow
interface DomainWorkflow {
  domain: DomainTemplate;        // Forensic, Academic, Creative
  phases: PhaseNode[];           // Fachliche Phasen
  actions: ActionNode[];         // Domain-Handler
  metadata: DomainMetadata;
}

interface DomainTemplate {
  domain_id: string;             // 'explosion', 'thesis'
  display_name: string;          // 'Forensic Report'
  category: string;              // 'expert_reports'
  icon: string;
  color: string;
  phases: PhaseTemplate[];
}

interface PhaseNode {
  phase_id: string;
  name: string;                  // "Data Collection"
  order: number;
  color: string;
  actions: ActionNode[];
  execution_mode: 'sequential' | 'parallel' | 'conditional';
}

interface ActionNode {
  action_id: string;
  name: string;                  // "Photo Analysis"
  handler_class: string;         // 'apps.forensic.handlers.PhotoAnalysisHandler'
  config: Record<string, any>;
  order: number;
  dependencies: string[];
  required_fields: string[];
}
```

---

## 🎨 VISUAL DESIGN

### Domain Selection Screen
```
┌────────────────────────────────────────────────┐
│  Choose Your Domain                             │
├────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────┐           │
│  │ 💥 Forensic   │  │ 🎓 Academic  │           │
│  │  Reports      │  │  Papers      │           │
│  └──────────────┘  └──────────────┘           │
│                                                 │
│  ┌──────────────┐  ┌──────────────┐           │
│  │ ⚕️  Medical   │  │ ✍️  Creative  │           │
│  │  Diagnostics  │  │  Writing     │           │
│  └──────────────┘  └──────────────┘           │
└────────────────────────────────────────────────┘
```

### Phase-Based Canvas
```
┌────────────────────────────────────────────────┐
│  🔷 Forensic Explosion Report                   │
├────────────────────────────────────────────────┤
│                                                 │
│  📦 PHASE 1: Data Collection                    │
│  ┌─────────────────────────────────────────┐  │
│  │  📸 Photo Analysis                       │  │
│  │  Input: case_photos                      │  │
│  │  Output: analyzed_images                 │  │
│  └─────────────────────────────────────────┘  │
│           ↓                                     │
│  ┌─────────────────────────────────────────┐  │
│  │  👥 Witness Interview                    │  │
│  │  Input: witness_list                     │  │
│  │  Output: interview_transcripts           │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  🔬 PHASE 2: Technical Analysis                 │
│  ┌─────────────────────────────────────────┐  │
│  │  💥 Explosive Mass Calculation           │  │
│  │  Input: crater_dimensions                │  │
│  │  Output: tnt_equivalent                  │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  📝 PHASE 3: Documentation                      │
│  ┌─────────────────────────────────────────┐  │
│  │  📄 Expert Report Generator              │  │
│  │  Input: analysis_results                 │  │
│  │  Output: report.pdf                      │  │
│  └─────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

---

## 🔧 BACKEND INTEGRATION

### API Endpoints (Angepasst)

```python
# apps/genagent/api/domain_workflow_api.py

@api_view(['GET'])
def list_domains(request):
    """List all available domain templates"""
    return JsonResponse({
        "domains": [
            {
                "domain_id": "explosion",
                "display_name": "Forensic Explosion Report",
                "category": "expert_reports",
                "icon": "💥",
                "phases_count": 3
            },
            {
                "domain_id": "thesis",
                "display_name": "Academic Thesis",
                "category": "academic",
                "icon": "🎓",
                "phases_count": 5
            }
        ]
    })

@api_view(['GET'])
def domain_detail(request, domain_id):
    """Get complete domain template"""
    # Load DomainTemplate from your system
    domain = DomainRegistry.get(domain_id)
    
    return JsonResponse({
        "domain_id": domain.domain_id,
        "display_name": domain.display_name,
        "description": domain.description,
        "phases": [
            {
                "name": phase.name,
                "order": phase.order,
                "color": phase.color,
                "icon": phase.icon,
                "actions": [
                    {
                        "name": action.name,
                        "handler_class": action.handler_class,
                        "config": action.config,
                        "order": action.order
                    }
                    for action in phase.actions
                ]
            }
            for phase in domain.phases
        ]
    })

@api_view(['POST'])
def execute_domain_workflow(request):
    """Execute a domain workflow"""
    domain_id = request.data.get('domain_id')
    context = request.data.get('context', {})
    
    # Use DomainInstaller to execute
    installer = DomainInstaller(domain_id)
    result = installer.execute(context)
    
    return JsonResponse(result)
```

---

## 🎯 HANDLER CATALOG (Domain-Aware)

### Statt Generic Handler

```json
{
  "handlers": [
    {
      "id": "project_fields",
      "name": "Project Fields Input",
      "category": "input"
    }
  ]
}
```

### NEU: Domain-Specific Handler

```json
{
  "domains": {
    "explosion": {
      "display_name": "Forensic Explosion Report",
      "handlers": [
        {
          "id": "photo_analysis",
          "name": "Photo & Video Analysis",
          "handler_class": "apps.forensic.handlers.PhotoAnalysisHandler",
          "category": "data_collection",
          "icon": "📸",
          "input_schema": {
            "case_photos": "list[str]",
            "analysis_type": "enum[crater|debris|damage]"
          },
          "output_schema": {
            "analyzed_images": "list[dict]",
            "crater_measurements": "dict"
          }
        },
        {
          "id": "explosive_mass",
          "name": "Explosive Mass Calculation",
          "handler_class": "apps.forensic.handlers.ExplosiveMassHandler",
          "category": "analysis",
          "icon": "💥"
        }
      ]
    },
    "thesis": {
      "display_name": "Academic Thesis",
      "handlers": [
        {
          "id": "literature_search",
          "name": "Literature Research",
          "handler_class": "apps.academic.handlers.LiteratureSearchHandler",
          "category": "research",
          "icon": "📚"
        }
      ]
    }
  }
}
```

---

## 📊 VORTEILE

### ✅ Domain-Driven
- Workflows sind fachlich, nicht technisch
- Handler sind Domain-Specific
- Validierung nach Fach-Regeln

### ✅ Visual + Code
- Visuelles Editing für Fach-Experten
- Code-Level Power für Entwickler
- Beide Welten kombiniert

### ✅ BF Agent Native
- Nutzt existierende DomainTemplate-Struktur
- Zero Breaking Changes
- Erweitert, ersetzt nicht

---

## 🚀 IMPLEMENTATION ROADMAP

### Phase 1: Backend Adaption (1 Woche)
- [ ] Domain-Aware API Endpoints
- [ ] DomainTemplate → React Flow Converter
- [ ] Handler Catalog per Domain

### Phase 2: Frontend Adaption (2 Wochen)
- [ ] Domain Selection Screen
- [ ] Phase-Based Canvas
- [ ] Domain-Specific Node Types
- [ ] Validation Rules UI

### Phase 3: Integration (1 Woche)
- [ ] DomainInstaller Integration
- [ ] Execution Tracking
- [ ] Error Handling
- [ ] Testing

---

## 💡 BEISPIEL WORKFLOW

### Forensic Report Creation

```typescript
const forensicWorkflow = {
  domain_id: "explosion",
  display_name: "Hamburg Port Explosion Analysis",
  phases: [
    {
      name: "Data Collection",
      actions: [
        {
          handler: "PhotoAnalysisHandler",
          config: {
            analysis_type: "crater",
            min_resolution: "4K"
          }
        },
        {
          handler: "WitnessInterviewHandler",
          config: {
            interview_method: "structured"
          }
        }
      ]
    },
    {
      name: "Technical Analysis",
      actions: [
        {
          handler: "ExplosiveMassHandler",
          config: {
            method: "crater_scaling"
          },
          dependencies: ["photo_analysis"]  // Needs crater data
        }
      ]
    }
  ]
};
```

---

## 🎯 FAZIT

**Visual Workflow Builder JA, ABER:**
- ✅ Domain-Aware, nicht generisch
- ✅ Phase-Based, nicht Pipeline-Based
- ✅ Fach-Handler, nicht Generic Handler
- ✅ BF Agent Native Integration

**Der PoC ist ein guter START, aber braucht Domain-Adaption!**
