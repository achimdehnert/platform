"""
Management command to update the MCP Transparency Initiative with analysis content.
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models_testing import Initiative, TestRequirement


class Command(BaseCommand):
    help = 'Update the MCP Transparency Initiative with analysis and requirements'

    def handle(self, *args, **options):
        initiative_id = '6d95844a-ad84-43c4-b0a9-88e6623197e6'
        
        try:
            init = Initiative.objects.get(pk=initiative_id)
        except Initiative.DoesNotExist:
            self.stderr.write(f'Initiative {initiative_id} not found!')
            return
        
        self.stdout.write(f'Updating Initiative: {init.title}')
        
        # =====================================================================
        # ANALYSE
        # =====================================================================
        init.analysis = """## Ist-Stand Analyse

### Vorhandene MCP-Tools (bfagent_mcp Server)

| Kategorie | Tools | Status |
|-----------|-------|--------|
| **Domain Management** | `list_domains`, `get_domain`, `search_handlers` | ✅ Produktiv |
| **Code Generation** | `generate_handler`, `scaffold_domain`, `validate_handler` | ✅ Produktiv |
| **Refactoring** | `get_refactor_options`, `check_path_protection`, `start/end_refactor_session` | ✅ Produktiv |
| **Naming** | `get_naming_convention`, `list_naming_conventions`, `list_component_types` | ✅ Produktiv |
| **DevOps** | `sentry_capture_error`, `grafana_*`, `chrome_*`, `admin_ultimate_check` | ✅ Produktiv |
| **Requirements** | `update_requirement_status`, `record_task_result`, `add_feedback`, `get_requirement` | ✅ Produktiv |
| **Initiatives** | `create`, `get`, `list`, `update`, `start`, `log_activity` | ✅ NEU |
| **Task Delegation** | `delegate_task`, `estimate_complexity`, `rate_task_result` | ✅ Produktiv |

### Auto-Router Implementation

**Datei:** `apps/bfagent/services/llm_router.py`

- **ComplexityLevel:** AUTO, LOW, MEDIUM, HIGH
- **TaskType:** coding, writing, analysis, translation, other
- **Routing Rules:** Pro (complexity, task_type) → Provider Category
- **Provider Categories:** ollama_small, ollama_coder, ollama_large, api_small, api_large, cascade

### Vorhandenes Tracking (DelegatedTask Model)

| Feld | Zweck | Status |
|------|-------|--------|
| `tokens_used` | Token-Verbrauch | ✅ |
| `estimated_cost` | Geschätzte Kosten | ✅ |
| `latency_ms` | Antwortzeit | ✅ |
| `routing_reason` | Warum dieser LLM | ✅ |
| `requires_cascade` | Ob Cascade nötig | ✅ |

### Identifizierte Lücken

1. **Kein zentrales MCP-Tool-Usage-Tracking** - Tool-Aufrufe werden nicht systematisch geloggt
2. **Kein Dashboard für MCP/LLM-Statistiken** - Keine UI für Übersicht über Nutzung
3. **Keine Kosten-Aggregation** - Keine Summen pro Initiative/Session/User
4. **Keine Cascade-Token-Tracking** - Nur lokale LLMs werden getrackt, nicht Cascade selbst
5. **Keine Qualitäts-Metriken** - Erfolgsrate von Routing-Entscheidungen nicht sichtbar

### Relevante Dateien

- `packages/bfagent_mcp/bfagent_mcp/server.py` - MCP Server mit allen Tools
- `apps/bfagent/services/llm_router.py` - Auto-Router Logic
- `apps/bfagent/services/task_executor.py` - Task Execution
- `apps/bfagent/models_tasks.py` - DelegatedTask, RoutingAnalytics
- `apps/bfagent/models_testing.py` - Initiative, InitiativeActivity
"""

        # =====================================================================
        # KONZEPT
        # =====================================================================
        init.concept = """## Lösungskonzept: Transparente MCP/LLM-Nutzung

### 1. MCP Tool Usage Tracker (Middleware)

**Zweck:** Jeden MCP-Tool-Aufruf loggen

```python
class MCPUsageLog(models.Model):
    tool_name = CharField(max_length=100)
    arguments = JSONField()
    result_summary = TextField()
    duration_ms = IntegerField()
    tokens_used = IntegerField(null=True)
    initiative = ForeignKey(Initiative, null=True)
    requirement = ForeignKey(TestRequirement, null=True)
    user = ForeignKey(User, null=True)
    created_at = DateTimeField(auto_now_add=True)
```

### 2. MCP Usage Dashboard

**Features:**
- Tool-Aufrufe pro Tag/Woche/Monat
- Häufigste Tools (Top 10)
- Durchschnittliche Latenz pro Tool
- Kosten-Übersicht (wenn LLM involviert)
- Filter nach Initiative/User/Domain

### 3. LLM Router Analytics Dashboard

**Features:**
- Routing-Entscheidungen visualisieren
- Erfolgsrate pro Routing-Pfad
- Token-Savings durch lokale LLMs
- Kosten-Vergleich: Cascade vs. Lokal
- Misrouted Tasks identifizieren

### 4. Initiative Cost Tracking

**Erweiterung InitiativeActivity:**
- Summe tokens_used pro Initiative
- Summe estimated_cost pro Initiative
- Aufschlüsselung nach MCP-Tool/LLM

### 5. Cascade Token Estimation

**Ansatz:**
- Prompt-Länge schätzen (Zeichen → Tokens)
- Response-Länge schätzen
- Kosten berechnen (Claude Pricing)
- In InitiativeActivity loggen

### Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    Control Center UI                         │
├─────────────────────────────────────────────────────────────┤
│  MCP Dashboard  │  LLM Analytics  │  Initiative Costs       │
├─────────────────────────────────────────────────────────────┤
│                    MCPUsageLog Model                         │
├─────────────────────────────────────────────────────────────┤
│  bfagent_mcp    │   llm_router    │   task_executor         │
│  (Tool Calls)   │   (Routing)     │   (Execution)           │
└─────────────────────────────────────────────────────────────┘
```
"""

        # =====================================================================
        # WORKFLOW & DOCUMENTATION
        # =====================================================================
        init.workflow_phase = 'analysis'
        init.status = 'concept'
        
        init.next_steps = """1. MCPUsageLog Model erstellen + Migration
2. MCP-Server mit Logging-Middleware erweitern
3. Dashboard View + Template erstellen
4. LLM Router Analytics implementieren
5. Initiative Cost Aggregation hinzufügen"""

        init.related_files = [
            'packages/bfagent_mcp/bfagent_mcp/server.py',
            'apps/bfagent/services/llm_router.py',
            'apps/bfagent/services/task_executor.py',
            'apps/bfagent/models_tasks.py',
            'apps/bfagent/models_testing.py',
            'apps/control_center/views_initiatives.py',
            'docs/workflows/initiative_workflow.md',
        ]
        
        init.save()
        self.stdout.write(self.style.SUCCESS('✅ Initiative analysis and concept updated!'))
        
        # =====================================================================
        # REQUIREMENTS ERSTELLEN
        # =====================================================================
        requirements_data = [
            {
                'name': 'MCPUsageLog Model + Migration',
                'description': 'Neues Model zum Tracken aller MCP-Tool-Aufrufe mit Argumenten, Dauer, Tokens, und Verknüpfung zu Initiative/Requirement.',
                'category': 'feature',
                'priority': 'high',
            },
            {
                'name': 'MCP Tool Usage Dashboard',
                'description': 'Dashboard im Control Center mit Statistiken zu Tool-Aufrufen: Häufigkeit, Latenz, Top-Tools, Filter nach Zeit/Domain.',
                'category': 'feature',
                'priority': 'high',
            },
            {
                'name': 'MCP Server Logging Middleware',
                'description': 'Middleware im bfagent_mcp Server die jeden Tool-Aufruf automatisch in MCPUsageLog speichert.',
                'category': 'feature',
                'priority': 'high',
            },
            {
                'name': 'InitiativeActivity Token/Cost Integration',
                'description': 'Erweiterung der Activity-Logs um automatische Token/Cost-Erfassung bei MCP-Tool-Nutzung.',
                'category': 'enhancement',
                'priority': 'medium',
            },
            {
                'name': 'Cascade Token Estimation',
                'description': 'Schätzung der verbrauchten Tokens bei Cascade-Aufrufen basierend auf Prompt/Response-Länge.',
                'category': 'feature',
                'priority': 'medium',
            },
            {
                'name': 'LLM Router Analytics Dashboard',
                'description': 'Visualisierung der Routing-Entscheidungen: Erfolgsrate, Token-Savings, Kosten-Vergleich Cascade vs. Lokal.',
                'category': 'feature',
                'priority': 'low',
            },
        ]
        
        created_count = 0
        for req_data in requirements_data:
            req, created = TestRequirement.objects.get_or_create(
                name=req_data['name'],
                initiative=init,
                defaults={
                    'description': req_data['description'],
                    'category': req_data['category'],
                    'priority': req_data['priority'],
                    'domain': init.domain,
                    'status': 'draft',
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✅ Created: {req.name}')
            else:
                self.stdout.write(f'  ⏭️  Exists: {req.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ {created_count} new requirements created!'))
        
        # Log activity
        if hasattr(init, 'log_activity'):
            init.log_activity(
                action='analysis_completed',
                details=f'Analyse abgeschlossen. {created_count} Requirements erstellt. Konzept dokumentiert.',
                actor='cascade'
            )
            self.stdout.write(self.style.SUCCESS('✅ Activity logged!'))
