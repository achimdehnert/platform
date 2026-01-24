# MANDATORY AGENT ARCHITECTURE RULES

## Hybrid Agent Architecture - MANDATORY COMPLIANCE

### RULE 1: Two-Tier Agent Classification
**ALL agents MUST be classified as either System Agent or Database Agent**

#### System Agents (Code-based)
**Location**: `core/agents/specialized/`
**Criteria** (ANY of these = System Agent):
- Complex API integrations (Web Search, External Services)
- Multi-layered data processing
- Performance-critical operations
- Complex algorithms or business logic
- Core infrastructure functionality
- Workflow orchestration
- Security-critical operations
- System monitoring/health checks
- Version control required
- Code reviews necessary

**Examples**: DatabaseAgent, ResearchAgent, SecurityAgent, WorkflowAgent, BackupAgent

#### Database Agents (UI-configurable)
**Location**: Database (`agents` table)
**Criteria** (ANY of these = Database Agent):
- User prompt engineering
- Project-specific configuration
- Creative writing tasks
- Genre-specific adaptations
- Style variations
- Character-specific dialogues
- Experimental settings
- A/B testing variants
- Frequent prompt optimization
- User feedback integration

**Examples**: PlotAgent, CharacterAgent, StyleAgent, DialogueAgent, GenreSpecialistAgent

### RULE 2: Agent Creation Decision Process
**MANDATORY**: Before creating ANY new agent, MUST determine classification:

1. **Analyze Requirements** against criteria above
2. **Make Classification Recommendation** with reasoning
3. **Get User Confirmation** before implementation
4. **Document Decision** in agent creation commit/PR

### RULE 3: No Duplication Policy
- System Agents exist ONLY in code
- Database Agents exist ONLY in database
- NO agent exists in both locations
- NO synchronization between tiers

### RULE 4: UI Behavior Rules
- Database Agents: Fully editable/deletable via UI
- System Agents: Visible but read-only, NOT deletable via UI
- Clear visual distinction between agent types
- System agents marked with 🔒 icon

### RULE 5: Agent Registry Implementation
**MANDATORY**: All agent access MUST go through AgentRegistry:
```python
class AgentRegistry:
    def get_all_agents(self):
        database_agents = self.load_from_database()
        system_agents = self.load_system_agents()

        # Mark system agents as read-only
        for agent in system_agents:
            agent.is_system_agent = True
            agent.deletable = False

        return database_agents + system_agents
```

### RULE 6: Decision Matrix
```
Complex + Stable + System-critical = System Agent
Simple + Flexible + User-customizable = Database Agent
```

### RULE 7: Migration Strategy
When moving existing agents:
1. Analyze against criteria
2. Classify appropriately
3. Move to correct location
4. Update all imports
5. Test thoroughly

## ENFORCEMENT
- All agent-related PRs MUST reference these rules
- Classification decisions MUST be documented
- Code reviews MUST verify compliance
- No exceptions without architectural review

## VIOLATION CONSEQUENCES
- PR rejection
- Refactoring requirement
- Architecture review escalation

---
**Last Updated**: 2025-09-24
**Status**: MANDATORY - NO EXCEPTIONS
