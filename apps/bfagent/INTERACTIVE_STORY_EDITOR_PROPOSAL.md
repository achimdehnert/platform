# 🎨 Interactive Story Editor - Vollständige Architektur

**Datum:** 2025-12-09  
**Use Case:** Text → Visualisierung → Bearbeitung → n8n Integration

---

## 🎯 USER FLOW

```
1. User schreibt Text:
   "Opening Image -> Catalyst -> All is Lost -> Finale"
   
2. System parsed & visualisiert:
   [Grafische Timeline mit Beats]
   
3. User bearbeitet interaktiv:
   - Drag & Drop Beats verschieben
   - Beats hinzufügen/löschen
   - Text direkt bearbeiten
   - Timeline anpassen
   
4. User speichert:
   - In Datenbank
   - Als JSON/Text Export
   
5. Optional: An n8n senden:
   → Generate chapters
   → Send notifications
   → Export to Google Docs
```

**Das ist absolut realistisch und eine EXCELLENTE Idee!** 🚀

---

## 🏗️ VOLLSTÄNDIGE ARCHITEKTUR

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React/Vue)                     │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │  TEXT INPUT COMPONENT                                  ││
│  │                                                        ││
│  │  ┌────────────────────────────────────┐              ││
│  │  │ Textarea / Monaco Editor           │              ││
│  │  │                                     │              ││
│  │  │ 1. Opening Image                   │              ││
│  │  │ 2. Catalyst                        │  [Parse]    ││
│  │  │ 3. All is Lost                     │  ─────►     ││
│  │  │ 4. Finale                          │              ││
│  │  │                                     │              ││
│  │  └────────────────────────────────────┘              ││
│  └────────────────────────────────────────────────────────┘│
│                           │                                 │
│                           ▼                                 │
│  ┌────────────────────────────────────────────────────────┐│
│  │  VISUALIZATION COMPONENT                               ││
│  │                                                        ││
│  │  ┌──────────────────────────────────────────────────┐ ││
│  │  │ React Flow / Excalidraw / Tldraw                 │ ││
│  │  │                                                  │ ││
│  │  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    │ ││
│  │  │  │Opening  │───►│Catalyst │───►│All Lost │    │ ││
│  │  │  │Image    │    │         │    │         │    │ ││
│  │  │  └────┬────┘    └─────────┘    └─────────┘    │ ││
│  │  │       │                                        │ ││
│  │  │       │ Drag & Drop • Edit • Add • Delete     │ ││
│  │  │       ▼                                        │ ││
│  │  │  ┌─────────┐                                  │ ││
│  │  │  │Finale   │                                  │ ││
│  │  │  └─────────┘                                  │ ││
│  │  │                                                  │ ││
│  │  └──────────────────────────────────────────────────┘ ││
│  └────────────────────────────────────────────────────────┘│
│                           │                                 │
│                           ▼                                 │
│  ┌────────────────────────────────────────────────────────┐│
│  │  ACTIONS BAR                                           ││
│  │  [Save] [Export JSON] [Export PNG] [Send to n8n]     ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ REST API
┌─────────────────────────────────────────────────────────────┐
│                   DJANGO BACKEND                            │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │ REST API ENDPOINTS                                     ││
│  │                                                        ││
│  │ POST   /api/outline/parse          ← Parse text       ││
│  │ POST   /api/outline/create         ← Save new         ││
│  │ GET    /api/outline/{id}           ← Load existing    ││
│  │ PUT    /api/outline/{id}           ← Update           ││
│  │ DELETE /api/outline/{id}           ← Delete           ││
│  │ POST   /api/outline/{id}/visualize ← Generate viz     ││
│  │ POST   /api/outline/{id}/export    ← Export formats   ││
│  │ POST   /api/outline/{id}/to-n8n    ← Trigger n8n     ││
│  └────────────────────────────────────────────────────────┘│
│                           │                                 │
│                           ▼                                 │
│  ┌────────────────────────────────────────────────────────┐│
│  │ SERVICES                                               ││
│  │                                                        ││
│  │ • OutlineParser      ← Parse text to JSON             ││
│  │ • OutlineVisualizer  ← Generate Mermaid/HTML          ││
│  │ • OutlineValidator   ← Check structure                ││
│  │ • N8NIntegration     ← Send to n8n                    ││
│  └────────────────────────────────────────────────────────┘│
│                           │                                 │
│                           ▼                                 │
│  ┌────────────────────────────────────────────────────────┐│
│  │ DATABASE (PostgreSQL)                                  ││
│  │                                                        ││
│  │ Table: story_outlines                                 ││
│  │ - id                                                  ││
│  │ - project_id (FK)                                     ││
│  │ - framework (Save Cat, Hero, 3-Act, Custom)          ││
│  │ - beats_json (JSON)                                   ││
│  │ - text_format (text)                                  ││
│  │ - visual_data (JSON) ← React Flow state              ││
│  │ - created_at, updated_at                              ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ Webhook
┌─────────────────────────────────────────────────────────────┐
│                        n8n                                  │
│                                                             │
│  Workflow: "Process Story Outline"                         │
│  1. Receive outline data                                   │
│  2. Generate chapters from beats                           │
│  3. Create character profiles                              │
│  4. Send email notification                                │
│  5. Export to Google Docs                                  │
│  6. Post to Slack                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ TECHNOLOGIE-STACK

### **Frontend:**
```javascript
// React + React Flow (EMPFOHLEN!)
- React 18
- React Flow (https://reactflow.dev/)
- Tailwind CSS
- Monaco Editor (für Text-Input)
- Axios (REST API calls)
```

**Warum React Flow?**
- ✅ Perfekt für Story-Beats (Nodes + Edges)
- ✅ Drag & Drop out-of-the-box
- ✅ Auto-Layout Algorithmen
- ✅ Edit in Place
- ✅ Export PNG/SVG
- ✅ Custom Node Types (Beat, Act, Character)

### **Backend:**
```python
# Django REST Framework
- Django 4.2+
- Django REST Framework
- PostgreSQL
- Celery (für async n8n calls)
```

### **Services (bereits erstellt!):**
- ✅ `OutlineParser` - Parse text formats
- ✅ `OutlineVisualizer` - Generate visuals
- ⏸️ `OutlineValidator` - Validate structure (TODO)
- ⏸️ `N8NIntegration` - n8n webhooks (TODO)

---

## 📝 BEISPIEL-IMPLEMENTATION

### **1. Frontend Component (React)**

```jsx
// components/StoryOutlineEditor.jsx
import { useState } from 'react';
import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';

function StoryOutlineEditor() {
  const [textInput, setTextInput] = useState('');
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  
  const parseAndVisualize = async () => {
    // Call Django API to parse
    const response = await fetch('/api/outline/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        text: textInput,
        framework: 'Save the Cat' 
      })
    });
    
    const data = await response.json();
    
    // Convert to React Flow nodes
    const newNodes = data.beats.map((beat, i) => ({
      id: `beat-${i}`,
      type: 'beatNode',
      position: { x: 0, y: i * 150 },
      data: { 
        label: beat.name,
        description: beat.description,
        number: beat.number
      }
    }));
    
    // Create edges (connections)
    const newEdges = newNodes.slice(0, -1).map((node, i) => ({
      id: `edge-${i}`,
      source: node.id,
      target: newNodes[i + 1].id,
      animated: true
    }));
    
    setNodes(newNodes);
    setEdges(newEdges);
  };
  
  const saveToBackend = async () => {
    // Save both text and visual state
    await fetch('/api/outline/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text_format: textInput,
        visual_data: { nodes, edges }
      })
    });
  };
  
  const sendToN8N = async () => {
    await fetch('/api/outline/to-n8n', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nodes, edges })
    });
  };
  
  return (
    <div className="editor-container">
      {/* Text Input */}
      <div className="text-panel">
        <h2>Story Outline (Text)</h2>
        <textarea
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="1. Opening Image&#10;2. Catalyst&#10;3. All is Lost&#10;..."
          rows={15}
        />
        <button onClick={parseAndVisualize}>
          Visualize
        </button>
      </div>
      
      {/* Visualization */}
      <div className="visual-panel">
        <h2>Interactive Timeline</h2>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={setNodes}
          onEdgesChange={setEdges}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
        
        <div className="actions">
          <button onClick={saveToBackend}>Save</button>
          <button onClick={sendToN8N}>Send to n8n</button>
        </div>
      </div>
    </div>
  );
}
```

### **2. Custom Beat Node**

```jsx
// components/BeatNode.jsx
function BeatNode({ data }) {
  const [editing, setEditing] = useState(false);
  
  return (
    <div className="beat-node">
      <div className="beat-header">
        <span className="beat-number">#{data.number}</span>
        <h3>{data.label}</h3>
      </div>
      
      {editing ? (
        <textarea
          value={data.description}
          onChange={(e) => updateBeat(e.target.value)}
          onBlur={() => setEditing(false)}
        />
      ) : (
        <p onClick={() => setEditing(true)}>
          {data.description || 'Click to add description...'}
        </p>
      )}
    </div>
  );
}
```

### **3. Backend API (Django)**

```python
# apps/writing_hub/views/outline_api.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.writing_hub.services.outline_parser import parse_outline

@api_view(['POST'])
def parse_outline_text(request):
    """Parse text into structured outline"""
    text = request.data.get('text', '')
    framework = request.data.get('framework', 'Custom')
    
    result = parse_outline(text, framework)
    
    return Response(result)

@api_view(['POST'])
def create_outline(request):
    """Save outline to database"""
    project_id = request.data.get('project_id')
    text_format = request.data.get('text_format')
    visual_data = request.data.get('visual_data', {})
    
    outline = StoryOutline.objects.create(
        project_id=project_id,
        text_format=text_format,
        visual_data=visual_data,
        beats_json=parse_outline(text_format)
    )
    
    return Response({'id': outline.id, 'status': 'created'})

@api_view(['POST'])
def send_to_n8n(request, outline_id):
    """Send outline to n8n for processing"""
    outline = StoryOutline.objects.get(id=outline_id)
    
    # Trigger n8n webhook
    n8n_url = settings.N8N_WEBHOOK_URL
    response = requests.post(n8n_url, json={
        'outline_id': outline.id,
        'beats': outline.beats_json,
        'project_id': outline.project_id
    })
    
    return Response({'status': 'sent', 'n8n_response': response.json()})
```

### **4. Django Model**

```python
# apps/writing_hub/models.py
from django.db import models

class StoryOutline(models.Model):
    """Store story outlines with text and visual representations"""
    
    project = models.ForeignKey('BookProjects', on_delete=models.CASCADE)
    framework = models.CharField(
        max_length=50,
        choices=[
            ('save_the_cat', 'Save the Cat'),
            ('heros_journey', "Hero's Journey"),
            ('three_act', 'Three-Act Structure'),
            ('custom', 'Custom'),
        ],
        default='custom'
    )
    
    # Text representation
    text_format = models.TextField(
        help_text="Original text input from user"
    )
    
    # Structured data
    beats_json = models.JSONField(
        help_text="Parsed beat structure as JSON"
    )
    
    # Visual representation
    visual_data = models.JSONField(
        default=dict,
        help_text="React Flow nodes/edges or Excalidraw elements"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
```

---

## 🔄 TEXT INPUT FORMATS (Unterstützt!)

### **Format 1: Numbered List**
```
1. Opening Image
2. Theme Stated
3. Catalyst
4. All is Lost
5. Finale
```

### **Format 2: Arrow Notation**
```
Opening Image -> Catalyst -> All is Lost -> Finale
```

### **Format 3: Markdown**
```markdown
# Act 1
## Beat 1: Opening Image
Hero in normal world, unaware of adventure ahead.

## Beat 2: Catalyst
Life-changing event occurs.
```

### **Format 4: YAML-style**
```yaml
Beat 1:
  name: Opening Image
  description: Hero in normal world
  
Beat 2:
  name: Catalyst
  description: Life-changing event
```

### **Format 5: JSON**
```json
{
  "framework": "Save the Cat",
  "beats": [
    {"number": 1, "name": "Opening Image", "description": "..."},
    {"number": 2, "name": "Catalyst", "description": "..."}
  ]
}
```

**Alle Formate werden automatisch erkannt und geparst!** ✅

---

## 🎨 VISUALISIERUNGS-OPTIONEN

### **Option A: React Flow (Timeline + Flowchart)**
```
Opening ──► Catalyst ──► All Lost ──► Finale
  │
  └──► Act 1 (25%)
  
  [Drag to rearrange]
  [Click to edit]
  [Add new beat]
```

### **Option B: Gantt Chart (Timeline View)**
```
Act 1 |████████░░░░░░░░░░░░░░░░░░░░| 25%
Act 2 |░░░░░░░░████████████████░░░░| 50%
Act 3 |░░░░░░░░░░░░░░░░░░░░████████| 25%
```

### **Option C: Excalidraw (Freeform)**
```
  ┌──────────┐
  │ Opening  │
  │  Image   │
  └────┬─────┘
       │
  ┌────▼─────┐
  │ Catalyst │
  └────┬─────┘
       │
      ...
```

---

## 🚀 FEATURES

### **Must-Have (MVP):**
- ✅ Text Input (Monaco Editor)
- ✅ Auto-Parse (OutlineParser)
- ✅ Visualisierung (React Flow)
- ✅ Drag & Drop Beats
- ✅ Save to DB
- ✅ Export JSON

### **Nice-to-Have:**
- ⚠️ Edit in Place (direkt im Node)
- ⚠️ Multiple Views (Timeline, Flowchart, Gantt)
- ⚠️ Auto-Layout Algorithmen
- ⚠️ Undo/Redo
- ⚠️ Real-time collaboration

### **Advanced:**
- ⏸️ AI Suggestions (LLM vorschlägt Beats)
- ⏸️ Template Library (Save Cat, Hero, etc.)
- ⏸️ Export PNG/SVG/PDF
- ⏸️ n8n Integration (Webhook)

---

## 💰 AUFWAND-SCHÄTZUNG

### **Phase 1: MVP (1-2 Wochen)**
- Backend API (3 Tage)
  - REST endpoints ✅
  - OutlineParser integration ✅
  - Database model
- Frontend (5 Tage)
  - React app setup
  - Text input component
  - React Flow integration
  - Basic styling
- Testing (2 Tage)

### **Phase 2: Polish (1 Woche)**
- Edit in Place
- Multiple views
- Better styling
- Export functions

### **Phase 3: n8n Integration (2-3 Tage)**
- Webhook endpoint
- n8n workflow templates
- Testing

**Total: 2-4 Wochen für vollständige Implementation**

---

## ✅ IST DAS REALISTISCH?

### **JA, absolut!** 🎉

**Warum:**
1. ✅ **Services fertig:** OutlineParser + OutlineVisualizer bereits erstellt!
2. ✅ **Tech bewährt:** React Flow ist production-ready
3. ✅ **Django REST:** Standard-Technologie
4. ✅ **n8n Integration:** Einfach via Webhooks
5. ✅ **Keine komplexe AI:** Parsing ist regelbasiert

**Ähnliche erfolgreiche Projekte:**
- **Miro:** Whiteboard mit Drag & Drop
- **Lucidchart:** Diagramm-Editor
- **Notion:** Block-based editor
- **Obsidian Canvas:** Note connections

**Alle nutzen ähnliche Technologien!**

---

## 🎯 NÄCHSTE SCHRITTE

### **Sofort möglich:**
1. ✅ **OutlineParser testen:**
   ```python
   from apps.writing_hub.services.outline_parser import parse_outline
   
   result = parse_outline("1. Opening\n2. Catalyst\n3. Finale")
   print(result)
   ```

2. ⏸️ **Django Model erstellen:**
   - `StoryOutline` model
   - Migration

3. ⏸️ **REST API bauen:**
   - Parse endpoint
   - CRUD endpoints
   - n8n endpoint

4. ⏸️ **React Frontend:**
   - Setup React app
   - Integrate React Flow
   - Connect to API

---

## 💡 ALTERNATIVE: QUICK PROTOTYPE

### **Wenn du schnell testen willst:**

**Option A: Streamlit (Python-only, 1 Tag!)**
```python
import streamlit as st
from apps.writing_hub.services.outline_parser import parse_outline

st.title("Story Outline Editor")

text = st.text_area("Enter outline:")
if st.button("Parse"):
    result = parse_outline(text)
    st.json(result)
    
    # Simple visualization
    for beat in result['beats']:
        st.write(f"{beat['number']}. {beat['name']}")
```

**Option B: Django + Mermaid (2-3 Tage)**
- Django form für Text input
- Parse on submit
- Display Mermaid.js visualization
- Keine Drag & Drop, aber funktional!

**Option C: Vollständige React App (2-4 Wochen)**
- Beste UX
- Volle Flexibilität
- Production-ready

---

## 🏆 EMPFEHLUNG

### **Für BF Agent:**

**Start mit:** Quick Prototype (Streamlit oder Django + Mermaid)  
**Warum:** Konzept validieren, User-Feedback sammeln

**Dann:** Vollständige React Flow Implementation  
**Warum:** Beste UX, production-ready, skalierbar

**n8n Integration:** Phase 2 (nach MVP)  
**Warum:** Erst User Flow perfektionieren, dann automatisieren

---

## ✨ FAZIT

**Deine Idee ist:**
- ✅ **Sinnvoll:** Genau was Story-Planer brauchen!
- ✅ **Realistisch:** 2-4 Wochen Implementation
- ✅ **Wertvoll:** Unique Feature für BF Agent
- ✅ **Skalierbar:** Kann später erweitert werden

**Services bereits fertig:**
- ✅ OutlineParser (alle Formate)
- ✅ OutlineVisualizer (Mermaid)

**Nächster Schritt:**
- Django Model + REST API
- React Frontend (oder Streamlit Prototype)

---

## ❓ FRAGEN

**Soll ich erstellen:**
1. ✅ Django Model für `StoryOutline`?
2. ✅ REST API Endpoints?
3. ✅ Streamlit Prototype für Quick Test?
4. ⏸️ React Frontend Boilerplate?

**Oder erstmal nur testen mit bestehendem OutlineParser?** 😊

---

**Das ist eine EXCELLENTE Idee! Lass uns das bauen!** 🚀
