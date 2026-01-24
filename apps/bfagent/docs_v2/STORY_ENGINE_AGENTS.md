# Story Engine - Agent System Design

> **Focus**: LangGraph Agents, Multi-Agent Workflows, Agent Roles  
> **Status**: Planning  
> **Updated**: 2024-11-07

---

## 🤖 Agent Roles

### 1. Story Architect Agent
**Role**: Strategic Planning & Structure

**Responsibilities:**
- Plan chapter structure before writing
- Ensure story beats are hit
- Maintain plot consistency
- Check timeline coherence

**Input:**
- Chapter beat description
- Story Bible (world rules, timeline)
- Previous chapters summary
- Character states

**Output:**
```json
{
  "chapter_plan": {
    "opening_scene": "Sarah wakes with splitting headache...",
    "plot_points": [
      "Discovery of enhanced perception",
      "First contact attempt fails",
      "Decision to hide changes"
    ],
    "character_moments": [
      "Sarah's fear of losing humanity",
      "Internal conflict about reporting"
    ],
    "closing_hook": "Encrypted message appears in her vision",
    "estimated_word_count": 2500
  }
}
```

**Example Code:**
```python
class StoryArchitectAgent(BaseStoryAgent):
    async def plan_chapter(self, beat: Dict, context: Dict) -> Dict:
        prompt = self._build_planning_prompt(beat, context)
        response = await self.llm.ainvoke(prompt)
        return self._parse_plan(response.content)
```

---

### 2. Writer Agent
**Role**: Prose Generation

**Responsibilities:**
- Generate actual prose from chapter plan
- Maintain consistent voice and style
- Create vivid descriptions
- Write compelling dialogue

**Input:**
- Chapter plan from Architect
- Style guide from Story Bible
- Character voice profiles

**Output:**
```
Sarah Chen pressed her fingertips to her temples, 
willing the splitting pain to subside. Three days 
since the procedure, and the headaches were getting 
worse, not better.

But that wasn't the worst part.

The worst part was the *knowing*—that inexplicable 
certainty that her colleague Dr. Martinez would walk 
through the lab door in exactly forty-three seconds...
```

**Specialization:**
- **Dialogue Writer**: Focuses on conversations
- **Scene Writer**: Descriptive prose
- **Action Writer**: High-tension sequences

**Example Code:**
```python
class WriterAgent(BaseStoryAgent):
    def __init__(self, style="balanced"):
        super().__init__()
        self.style = style  # "dialogue_heavy", "descriptive", "action"
    
    async def write_prose(self, plan: Dict, context: Dict) -> str:
        prompt = f"""
Write compelling prose following this plan:
{plan}

Style: {context['prose_style']}
Tone: {context['tone']}
POV: {context['pov']}

Generate 2000-2500 words.
"""
        response = await self.llm.ainvoke(prompt)
        return response.content
```

---

### 3. Continuity Checker Agent
**Role**: Consistency & Quality Assurance

**Responsibilities:**
- Check for contradictions with previous chapters
- Verify character consistency
- Validate timeline
- Ensure world rules are followed

**Input:**
- Newly generated chapter
- Story Bible (all established facts)
- Previous chapters
- Character dossiers

**Output:**
```json
{
  "consistency_score": 0.92,
  "issues": [
    {
      "severity": "critical",
      "type": "character_contradiction",
      "description": "Sarah's eye color changed from brown to blue",
      "location": "Chapter 3, paragraph 5",
      "previous_reference": "Chapter 1: 'her brown eyes'"
    },
    {
      "severity": "minor",
      "type": "timeline_inconsistency",
      "description": "Event timing off by 2 days",
      "suggestion": "Change 'five days ago' to 'three days ago'"
    }
  ],
  "strengths": [
    "Character voice consistent",
    "Plot progression logical",
    "No world rule violations"
  ]
}
```

**Example Code:**
```python
class ContinuityCheckerAgent(BaseStoryAgent):
    async def check_consistency(
        self, 
        chapter: str, 
        story_bible: Dict,
        previous_chapters: List[str]
    ) -> Dict:
        # Build context from story bible
        facts = self._extract_established_facts(story_bible, previous_chapters)
        
        prompt = f"""
Check this chapter for consistency:

{chapter}

Established facts:
{facts}

Return JSON with:
- consistency_score (0-1)
- issues (list with severity, type, description)
- strengths (list)
"""
        
        response = await self.llm.ainvoke(prompt)
        return json.loads(response.content)
```

---

### 4. Editor Agent
**Role**: Refinement & Polish

**Responsibilities:**
- Improve prose quality
- Fix pacing issues
- Enhance readability
- Tighten dialogue

**Input:**
- Draft chapter
- Continuity check results
- Style guidelines

**Output:**
- Polished chapter text
- List of changes made
- Quality metrics

**Example Code:**
```python
class EditorAgent(BaseStoryAgent):
    async def edit_chapter(
        self,
        draft: str,
        issues: List[Dict],
        style_guide: Dict
    ) -> Dict:
        prompt = f"""
Edit this chapter draft:

{draft}

Fix these issues:
{issues}

Style guide:
{style_guide}

Improve:
1. Pacing
2. Readability
3. Dialogue naturalness
4. Description vividness

Return edited text + change summary.
"""
        
        response = await self.llm.ainvoke(prompt)
        return self._parse_edit_result(response.content)
```

---

## 🔄 Multi-Agent Workflows

### Workflow 1: Sequential Generation (Simple)
```
1. Story Architect
   ↓ (chapter plan)
2. Writer Agent
   ↓ (draft)
3. Continuity Checker
   ↓ (issues found)
4. Editor Agent
   ↓ (polished chapter)
5. Save to Database
```

**LangGraph Implementation:**
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class ChapterState(TypedDict):
    beat: Dict
    plan: Dict
    draft: str
    issues: List[Dict]
    final_text: str
    context: Dict

# Define workflow
graph = StateGraph(ChapterState)

# Add nodes (agents)
graph.add_node("architect", architect_agent.plan_chapter)
graph.add_node("writer", writer_agent.write_prose)
graph.add_node("checker", continuity_agent.check)
graph.add_node("editor", editor_agent.edit)

# Define flow
graph.add_edge("architect", "writer")
graph.add_edge("writer", "checker")
graph.add_edge("checker", "editor")
graph.add_edge("editor", END)

# Set entry point
graph.set_entry_point("architect")

# Compile
chapter_workflow = graph.compile()
```

---

### Workflow 2: Iterative Refinement (Advanced)
```
1. Story Architect
   ↓
2. Writer Agent
   ↓
3. Continuity Checker
   ↓
   ├─ If critical issues → back to Writer (max 3 iterations)
   └─ If OK → Editor Agent
   ↓
4. Editor Agent
   ↓
   ├─ If quality < threshold → back to Writer
   └─ If OK → Human Review?
   ↓
5. Save to Database
```

**LangGraph with Conditional Edges:**
```python
def should_revise(state: ChapterState) -> str:
    """Decide if chapter needs revision"""
    critical_issues = [i for i in state["issues"] 
                      if i["severity"] == "critical"]
    
    if critical_issues and state.get("iteration", 0) < 3:
        return "revise"
    return "edit"

def needs_human_review(state: ChapterState) -> str:
    """Decide if human should review"""
    if state.get("quality_score", 1.0) < 0.7:
        return "human_review"
    return "save"

# Add conditional edges
graph.add_conditional_edge(
    "checker",
    should_revise,
    {
        "revise": "writer",  # Loop back
        "edit": "editor"     # Continue
    }
)

graph.add_conditional_edge(
    "editor",
    needs_human_review,
    {
        "human_review": "human_review",
        "save": END
    }
)
```

---

### Workflow 3: Parallel Specialization
```
1. Story Architect
   ↓ (splits chapter into scenes)
   ├─ Scene Writer Agent 1 → Scene 1
   ├─ Scene Writer Agent 2 → Scene 2
   └─ Scene Writer Agent 3 → Scene 3
   ↓ (merge)
2. Continuity Checker
   ↓
3. Editor Agent
   ↓
4. Save
```

---

## 🎯 Agent Collaboration Patterns

### Pattern 1: Sequential Pipeline
**Use Case**: Standard chapter generation
**Agents**: Architect → Writer → Checker → Editor
**State Management**: Each agent adds to state

### Pattern 2: Feedback Loop
**Use Case**: Quality-critical content
**Agents**: Writer ↔ Checker (iterate until quality threshold)

### Pattern 3: Hierarchical
**Use Case**: Complex multi-scene chapters
**Agents**: Architect (coordinator) → Multiple Writers (parallel) → Merger

### Pattern 4: Human-in-Loop
**Use Case**: Creative decisions
**Flow**: Agent → Human Approval → Continue/Revise

**Implementation:**
```python
class HumanReviewNode:
    async def __call__(self, state: ChapterState) -> ChapterState:
        # Save to DB with status='pending_review'
        chapter = Chapter.objects.create(
            content=state["draft"],
            status="pending_review"
        )
        
        # Wait for human input (via UI)
        approval = await self.wait_for_approval(chapter.id)
        
        if approval.approved:
            state["final_text"] = approval.edited_text or state["draft"]
        else:
            # Feedback for revision
            state["human_feedback"] = approval.comments
            # Graph will route back to writer
        
        return state
```

---

## 📊 Agent Performance Metrics

### Per-Agent Metrics
```python
class AgentMetrics(models.Model):
    agent_name = models.CharField(max_length=100)
    
    # Performance
    avg_execution_time = models.FloatField()  # seconds
    avg_token_usage = models.IntegerField()
    avg_cost = models.DecimalField(max_digits=10, decimal_places=4)
    
    # Quality
    avg_quality_score = models.FloatField()  # 0-1
    success_rate = models.FloatField()  # % without errors
    
    # Usage
    total_executions = models.IntegerField()
    last_executed = models.DateTimeField()
```

### Tracking Example
```python
class MetricsCollector:
    async def track_agent_execution(
        self,
        agent_name: str,
        execution_time: float,
        tokens: int,
        quality_score: float
    ):
        metrics, _ = AgentMetrics.objects.get_or_create(agent_name=agent_name)
        
        # Update averages
        total = metrics.total_executions
        metrics.avg_execution_time = (
            (metrics.avg_execution_time * total + execution_time) / (total + 1)
        )
        metrics.avg_token_usage = (
            (metrics.avg_token_usage * total + tokens) / (total + 1)
        )
        metrics.avg_quality_score = (
            (metrics.avg_quality_score * total + quality_score) / (total + 1)
        )
        
        metrics.total_executions += 1
        metrics.last_executed = timezone.now()
        metrics.save()
```

---

## 🔧 Configuration

### Agent Config (YAML)
```yaml
# config/agents.yaml
agents:
  story_architect:
    model: claude-sonnet-4.5
    temperature: 0.3  # More deterministic for planning
    max_tokens: 2000
    timeout: 30
  
  writer:
    model: claude-sonnet-4.5
    temperature: 0.7  # More creative for prose
    max_tokens: 8000
    timeout: 120
  
  continuity_checker:
    model: claude-sonnet-4.5
    temperature: 0.1  # Very deterministic for analysis
    max_tokens: 3000
    timeout: 60
  
  editor:
    model: gpt-4-turbo  # Can use different model
    temperature: 0.5
    max_tokens: 8000
    timeout: 90

workflows:
  standard_chapter:
    agents: [story_architect, writer, continuity_checker, editor]
    max_iterations: 3
    quality_threshold: 0.8
    human_review_required: false
  
  quality_chapter:
    agents: [story_architect, writer, continuity_checker, editor]
    max_iterations: 5
    quality_threshold: 0.9
    human_review_required: true
```

---

## 🧪 Testing Agents

### Unit Test
```python
@pytest.mark.asyncio
async def test_story_architect_planning():
    agent = StoryArchitectAgent()
    
    beat = {
        "description": "Sarah discovers enhanced abilities",
        "emotional_tone": "tense",
        "key_events": ["perception anomaly", "test results"]
    }
    
    plan = await agent.plan_chapter(beat, context={})
    
    assert "opening_scene" in plan
    assert "plot_points" in plan
    assert len(plan["plot_points"]) >= 2
```

### Integration Test
```python
@pytest.mark.asyncio
async def test_full_agent_workflow():
    workflow = ChapterGenerationWorkflow()
    
    state = ChapterState(
        beat={"description": "Test beat"},
        context={"story_bible": test_bible}
    )
    
    result = await workflow.execute(state)
    
    assert result["final_text"] is not None
    assert len(result["final_text"]) > 1000
    assert result.get("quality_score", 0) > 0.7
```

---

## 📚 See Also

- [STORY_ENGINE_OVERVIEW.md](./STORY_ENGINE_OVERVIEW.md) - Project overview
- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System architecture
- [STORY_ENGINE_IMPLEMENTATION.md](./STORY_ENGINE_IMPLEMENTATION.md) - Implementation guide
- [STORY_ENGINE_DATABASE.md](./STORY_ENGINE_DATABASE.md) - Database schema
