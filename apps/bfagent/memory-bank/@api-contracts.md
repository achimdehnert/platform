# BookFactory Agent Contracts

## Core Agents

### Researcher Agent
```python
# Request
{"agent": "researcher", "topic": "AI Literature", "depth": "comprehensive"}

# Response
{"success": True, "findings": {"summary": "...", "sources": [...], "citations": [...]}}
```

### Outliner Agent
```python
# Request
{"agent": "outliner", "book_type": "technical", "chapters": 12}

# Response
{"success": True, "outline": {"title": "...", "chapters": [...]}}
```

### L2MAC Writer Agent
```python
# Request
{"agent": "l2mac_writer", "chapter": 1, "outline": {...}, "context": "..."}

# Response
{"success": True, "content": "...", "word_count": 5000, "memory_saved": True}
```

### Editor Agent
```python
# Request
{"agent": "editor", "content": "...", "style": "academic"}

# Response
{"success": True, "edited_content": "...", "changes": [...], "quality_score": 0.95}
```

## Error Codes
- `AGENT_ERROR`: General agent failure
- `MEMORY_ERROR`: Memory storage/retrieval failed
- `CONTEXT_ERROR`: Insufficient context for task
- `API_TIMEOUT`: External API timeout

## Memory Bank Interface
```python
# Save to memory
memory_bank.save("project_config", data)

# Load from memory
data = memory_bank.load("project_config")

# List memories
memories = memory_bank.list_all()
```

## Windsurf Integration
- Memory persistence across sessions
- Context sharing between agents
- Web interface state management
- Real-time collaboration support
