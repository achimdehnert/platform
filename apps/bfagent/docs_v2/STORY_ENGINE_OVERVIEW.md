# Story Engine - Executive Overview

> **Vision**: bfAgent Evolution zum AI-gestützten Roman-System  
> **Projekt**: Superintelligenz-Romanreihe (6 Stränge, 6 Bände)  
> **Tech**: Django + Handler + LangGraph + Database-First  
> **Status**: Planning  
> **Erstellt**: 2024-11-07

---

## 🎯 Kern-Ziele

### 1. bfAgent → Story Engine
- Integration statt Neustart
- Handler-Pattern + Agent-System kombinieren
- Database-First beibehalten
- Learning-Projekt (kein Zeitdruck)

### 2. Superintelligenz-Romane
- 6 Bände à 80k Wörter
- 6 parallele Handlungsstränge
- AI-generiert mit Human-in-Loop
- Genre: Sci-Fi + Thriller + Philosophy

### 3. PoC Teaser (15-20k Wörter)
- "Das Erwachen" Strang
- System-Test
- 4-6 Wochen Timeline

---

## ✅ Strategische Entscheidungen

### 1. Integration in bfAgent ⭐
- Nutzt bestehende Django-Infrastruktur
- Handler-Pattern kompatibel mit Agents
- Web UI bereits vorhanden

### 2. Database-First + Vector Store (Hybrid) ⭐
**Regel:**
- PostgreSQL = Source of Truth (PRIMARY)
- ChromaDB = Optional Search Index (SECONDARY)

### 3. Handler + Agent Collaboration ⭐
```
Phase → Action → Handler → LangGraph Agents
```
- Handler: State, DB, Errors
- Agents: Creative AI Work

### 4. LangGraph statt CrewAI ⭐
- State Management für lange Stories
- Flexibelät wichtiger als Speed

---

## 🏗️ Architektur

```
Django UI
  ↓
Workflow Layer (DB-driven)
  ↓
Handler Orchestration
  ↓
LangGraph Agent System
  ↓
Database (PostgreSQL) + Vector Store (ChromaDB optional)
```

---

## 📅 Roadmap

### Phase 1: Foundation (4-6 Wochen)
- Django Story Models
- LangGraph Setup
- Handler Integration
- **Deliverable:** 1-Chapter-Generator

### Phase 2: Agent System (6-8 Wochen)
- Multi-Agent Workflows
- Character Memory
- Quality Checks
- **Deliverable:** Full Pipeline

### Phase 3: PoC (2-4 Wochen)
- Story Bible Development
- Generate Teaser (8-10 Kapitel)
- **Deliverable:** Complete Teaser

---

## 📊 Success Metrics

**Technical:**
- Chapter Gen: <5 min
- Consistency: >90%
- Test Coverage: >80%

**Story Quality:**
- Readability: Flesch >60
- First Draft: 70% usable

**Cost:**
- <$5 per chapter
- <$150 per book

---

## 📚 Related Docs

- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - Technical details
- [STORY_ENGINE_DATABASE.md](./STORY_ENGINE_DATABASE.md) - Database schema
- [STORY_ENGINE_AGENTS.md](./STORY_ENGINE_AGENTS.md) - Agent design
- [STORY_ENGINE_IMPLEMENTATION.md](./STORY_ENGINE_IMPLEMENTATION.md) - Dev guide
- [Romanreihe_Superintelligenz_Projektplan.md](./Romanreihe_Superintelligenz_Projektplan.md) - Original concept
