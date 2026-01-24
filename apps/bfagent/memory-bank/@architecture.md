# @architecture.md - BookFactory Technical Architecture

## 🏗️ System Architecture

### High-Level Overview
```text
BookFactory AI Book Development Platform
├── develop/             # Development branch
│   ├── app/            # Streamlit application
│   ├── api/            # API services & database
│   └── agents/         # Agent implementations
├── stable/             # Stable production branch
├── .windsurf/          # Configuration & rules
└── memory-bank/        # Optimized memory system
```

### Core Components

#### 1. AI Framework Stack
- **AutoGen**: Conversational agent system
- **L2MAC**: Unlimited text generation
- **CrewAI**: Workflow orchestration (Phase 2)
- **Windsurf**: Development environment integration

#### 2. Agent Management System
- **Agent CRUD Operations**: Interactive st.data_editor interface
- **LLM Integration**: Model assignment and testing
- **Character Agents**: Specialized character development
- **Plot Agents**: Story structure and development
- **Navigation System**: Optimized UI routing

#### 3. Memory System
- **Memory Bank**: Windsurf-optimized persistent storage
- **File Store**: L2MAC chapter and context storage
- **Session State**: Streamlit session management
- **Context Sharing**: Cross-agent memory sharing

#### 4. Web Interface
- **Streamlit App**: Main user interface (app/main.py)
- **Agent Management**: CRUD operations and configuration
- **Character Interface**: Character development tools
- **Book Workspace**: Interactive writing environment
- **Direct Access**: Standalone agent management (run_agents.py)

## 🔄 Book Development Flow

1. **Project Creation** → Project Manager Interface
2. **Research Phase** → Researcher Agent
3. **Structure Planning** → Outliner Agent
4. **Content Generation** → L2MAC Writer Agent
5. **Editing & Polish** → Editor Agent
6. **Memory Persistence** → Memory Bank System
7. **Output Generation** → Book Formatter

## 📊 Technology Stack

- **Python 3.11+**: Core language
- **AutoGen**: Agent conversations
- **L2MAC**: Long text generation
- **CrewAI**: Workflow orchestration
- **Streamlit**: Web interface
- **Windsurf**: Development environment
- **OpenAI**: LLM provider

### Design Principles
- **Modular Architecture**: Simplified and maintainable design
- **YAML Config:** Maintainable configuration
- **Defensive Programming:** Error handling
- **Performance First:** Memory optimization
