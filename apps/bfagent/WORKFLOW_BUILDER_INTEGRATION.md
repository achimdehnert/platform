# 🚀 Workflow Builder Integration Guide

## ✅ WAS WIR GEBAUT HABEN

### Phase 1: Foundation (FERTIG ✅)
```
✅ workflow_templates.py - Workflow Template Library
✅ execute_workflow() - Handler + Template Integration
✅ 2 Pre-built Workflows (Chapter, Character)
```

### Phase 2: Backend API (FERTIG ✅)
```
✅ workflow_api.py - REST API Views
✅ urls.py - URL Configuration
✅ 8 API Endpoints ready
```

---

## 📝 INTEGRATION SCHRITTE

### 1. URL Configuration (2 Min)

Füge zu deiner Haupt-URLs hinzu:

**File:** `config/urls.py` oder deine main urls.py

```python
from django.urls import path, include

urlpatterns = [
    # ... existing urls
    
    # Workflow Builder API
    path('api/workflow/', include('apps.bfagent.api.urls')),
]
```

### 2. CORS Setup für Development (3 Min)

**File:** `config/settings/development.py`

```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
    # ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Add at top
    # ... other middleware
]

# Allow React dev server
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",  # React default
]
```

### 3. Install CORS Headers (1 Min)

```bash
pip install django-cors-headers
```

### 4. Test API Endpoints (5 Min)

```bash
# Start Django
python manage.py runserver

# Test Handler Catalog
curl http://localhost:8000/api/workflow/handlers/

# Test Workflow Templates
curl http://localhost:8000/api/workflow/workflows/templates/

# Test Specific Template
curl http://localhost:8000/api/workflow/workflows/templates/chapter_gen/
```

---

## 🎨 FRONTEND INTEGRATION

### Option A: Use PoC Files (Quick)

```bash
# 1. Navigate to PoC folder
cd docs/vis_workflow

# 2. Install dependencies
npm install

# 3. Update API endpoint in src/WorkflowBuilder.tsx
# Change: const API_BASE = 'http://localhost:8000/api/workflow'

# 4. Start frontend
npm run dev
# → Opens at http://localhost:5173
```

### Option B: Custom Frontend

Minimal React Flow Setup:

```bash
npm create vite@latest workflow-builder -- --template react-ts
cd workflow-builder
npm install @xyflow/react lucide-react
```

Basic Integration:

```typescript
// src/App.tsx
import { ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

function App() {
  const [workflows, setWorkflows] = useState([]);
  
  useEffect(() => {
    fetch('http://localhost:8000/api/workflow/workflows/templates/')
      .then(r => r.json())
      .then(data => setWorkflows(data.templates));
  }, []);
  
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ReactFlow />
    </div>
  );
}
```

---

## 🧪 API TESTING

### Test Suite Created

```bash
python test_workflow_api.py
```

Expected Output:
```
✅ Handler Catalog API
✅ Workflow Templates API
✅ Workflow Execution API
✅ React Flow Converter API
```

---

## 📊 AVAILABLE ENDPOINTS

### Handler Catalog
```
GET  /api/workflow/handlers/
     → List all handlers (input, processing, output)
     
GET  /api/workflow/handlers/<handler_id>/
     → Get handler details, schema, examples
```

### Workflow Templates
```
GET  /api/workflow/workflows/templates/
     → List all workflow templates
     
GET  /api/workflow/workflows/templates/<template_id>/
     → Get template details with full pipeline config
```

### Workflow Execution
```
POST /api/workflow/workflows/execute/
     Body: {
       "workflow_id": "chapter_gen",
       "variables": {...},
       "context": {...}
     }
     → Execute workflow and return results
     
POST /api/workflow/workflows/save/
     Body: {
       "name": "My Workflow",
       "pipeline_config": {...}
     }
     → Save custom workflow
```

### Converters
```
POST /api/workflow/convert/to-pipeline/
     Body: { "nodes": [...], "edges": [...] }
     → Convert React Flow JSON to Pipeline Config
     
POST /api/workflow/convert/to-reactflow/
     Body: { "input": [...], "processing": [...], "output": {...} }
     → Convert Pipeline Config to React Flow JSON
```

---

## 🎯 NEXT STEPS

### Immediate (Today)
1. ✅ URL Integration (2 min)
2. ✅ CORS Setup (3 min)
3. ✅ Test API (5 min)
4. 🔄 Start Frontend (10 min)

### Short-term (This Week)
1. Visual Editor Demo
2. First Workflow Created Visually
3. Execute Workflow from UI
4. Save Custom Workflow

### Mid-term (Next Week)
1. Handler Config UI
2. Variable Input Forms
3. Execution Monitor
4. Template Library UI

---

## 💡 BEISPIEL WORKFLOW

### 1. Load Template via API

```bash
curl http://localhost:8000/api/workflow/workflows/templates/chapter_gen/
```

Response:
```json
{
  "template_id": "chapter_gen",
  "name": "Chapter Generation",
  "pipeline": {
    "input": [
      {"handler": "project_fields", "config": {...}},
      {"handler": "chapter_data", "config": {...}}
    ],
    "processing": [
      {"handler": "prompt_template_processor", "config": {...}},
      {"handler": "llm_processor", "config": {...}}
    ],
    "output": [
      {"handler": "chapter_creator", "config": {...}}
    ]
  }
}
```

### 2. Convert to React Flow

```bash
curl -X POST http://localhost:8000/api/workflow/convert/to-reactflow/ \
  -H "Content-Type: application/json" \
  -d '{
    "input": [...],
    "processing": [...],
    "output": {...}
  }'
```

Response:
```json
{
  "nodes": [
    {"id": "node-1", "type": "input", "data": {...}},
    {"id": "node-2", "type": "processing", "data": {...}},
    ...
  ],
  "edges": [
    {"id": "edge-1-2", "source": "node-1", "target": "node-2"},
    ...
  ]
}
```

### 3. Display in React Flow

```typescript
const [nodes, setNodes] = useState([]);
const [edges, setEdges] = useState([]);

// Load from API
useEffect(() => {
  loadWorkflow('chapter_gen').then(data => {
    setNodes(data.nodes);
    setEdges(data.edges);
  });
}, []);

return <ReactFlow nodes={nodes} edges={edges} />;
```

---

## 🎉 STATUS

```
✅ Backend API Complete
✅ URL Configuration Ready
✅ Converters Implemented
✅ Integration Guide Written
🔄 Frontend Setup (Next)
```

**Time to Visual Editor: ~10 Minutes** 🚀

---

## 🐛 TROUBLESHOOTING

### API Returns 404
```bash
# Check URL configuration
python manage.py show_urls | grep workflow
```

### CORS Errors
```python
# Add to settings
CORS_ALLOW_ALL_ORIGINS = True  # Dev only!
```

### Handler Not Found
```python
# Check handler registry
from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
print(ProcessingHandlerRegistry._handlers.keys())
```

---

**Ready for Visual Workflow Builder! 🎨**
