# BF Agent MCP - Refactoring Tools

**Status:** ✅ PRODUCTION READY - Alle Tools implementiert und getestet!

## 🎯 Refactoring Tools (7 Tools)

### Übersicht

| Tool | Beschreibung |
|------|--------------|
| `bfagent_get_refactor_options` | Zeigt was in einer Domain refactored werden kann |
| `bfagent_check_path_protection` | Prüft ob ein Pfad geschützt ist |
| `bfagent_get_naming_convention` | Naming Convention für eine App |
| `bfagent_list_naming_conventions` | Alle Naming Conventions |
| `bfagent_list_component_types` | Handler, Service, Model, etc. |
| `bfagent_start_refactor_session` | Startet Tracking-Session |
| `bfagent_end_refactor_session` | Beendet Session mit Stats |

## 📁 Implementierung

```
packages/bfagent_mcp/bfagent_mcp/
├── server.py              # MCP Server mit Tool Definitions (615 Zeilen)
├── refactor_service.py    # Refactoring Service Layer (648 Zeilen)
└── models_mcp.py          # MCP Domain Models (MCPDomainConfig, etc.)
```

## 🚀 Installation & Test

```powershell
# 1. Package neu installieren
cd packages\bfagent_mcp
pip install -e . --force-reinstall --no-deps
cd ..\..

# 2. Test im Django Shell
python manage.py shell

# 3. Service testen
from bfagent_mcp.refactor_service import MCPRefactorService
import asyncio

service = MCPRefactorService()
result = asyncio.run(service.get_refactor_options("writing_hub"))
print(result)
```

## 💬 Beispiel-Prompts für Windsurf

### Naming Conventions abfragen
```
"Welche Naming Conventions gibt es?"
→ bfagent_list_naming_conventions()

"Naming Convention für genagent?"
→ bfagent_get_naming_convention(app_label="genagent")

"Zeige mir alle Component Types"
→ bfagent_list_component_types()
```

### Vor dem Refactoring
```
"Was kann ich im writing_hub Domain refactoren?"
→ bfagent_get_refactor_options(domain_id="writing_hub")

"Ist packages/bfagent_mcp/server.py geschützt?"
→ bfagent_check_path_protection(file_path="packages/bfagent_mcp/server.py")

"Welche Naming Convention gilt für medtrans?"
→ bfagent_get_naming_convention(app_label="medtrans")
```

### Session starten
```
"Starte Refactoring-Session für books handlers"
→ bfagent_start_refactor_session(domain_id="books", components=["handler"])
```

### Nach dem Refactoring
```
"Beende die Session, 5 Dateien geändert"
→ bfagent_end_refactor_session(session_id=1, files_changed=5, summary="Handler refactored")
```

## � TECHNISCHE DETAILS

### Django Integration
- **Models:** `MCPDomainConfig`, `MCPProtectedPath`, `TableNamingConvention`
- **Database:** Tabellen `bfagent_mcp_domain`, `bfagent_mcp_handler`, `bfagent_mcp_phase`
- **Service:** `MCPRefactorService` mit async/await Support
- **Fallback:** Mock-Daten wenn Django nicht konfiguriert

### MCP Server Integration
- **Tools:** Alle 7 Tools in `get_tool_definitions()` registriert
- **Dispatcher:** `_dispatch_tool()` ruft Service-Methoden auf
- **Format:** Markdown (default) oder JSON
- **Error Handling:** Graceful degradation bei fehlenden Daten

## �📊 Tool Output Beispiele

### bfagent_get_refactor_options

```markdown
# Refactor Options: books

**Status:** ✓ Ready
**Base Path:** `apps/books/`
**Risk:** 🟡 Medium (Score: 50/100)
**Order:** #10

## Dependencies

Refactor these first: `core`

## Available Components

| Component | Path | Icon |
|-----------|------|------|
| Handler | `apps/books/handlers/` | 🔧 |
| Service | `apps/books/services/` | ⚙️ |
| Model | `apps/books/models.py` | 📊 |
```

### bfagent_check_path_protection

```markdown
# Path Check: `packages/bfagent_mcp/server.py`

🔒 **BLOCKED** - This path is protected!

## Matching Rules

### 🔒 Absolute

- **Pattern:** `packages/bfagent_mcp/**`
- **Category:** MCP Package
- **Reason:** MCP Server - Self-Protection

## ❌ Action Required

**DO NOT MODIFY this file!** It is absolutely protected.
```

## 🔗 Windsurf Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        REFACTORING WORKFLOW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. PLAN                                                                │
│     ├── bfagent_get_refactor_options("books")                          │
│     └── bfagent_list_component_types()                                 │
│                                                                         │
│  2. CHECK                                                               │
│     └── bfagent_check_path_protection("apps/books/handlers/x.py")      │
│                                                                         │
│  3. START                                                               │
│     └── bfagent_start_refactor_session("books", ["handler"])           │
│         → Returns: session_id=42                                        │
│                                                                         │
│  4. REFACTOR                                                            │
│     └── (Claude/Windsurf macht die eigentliche Arbeit)                 │
│                                                                         │
│  5. END                                                                 │
│     └── bfagent_end_refactor_session(42, files_changed=5)              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🎓 BEST PRACTICES

### Workflow Guidelines
1. **Immer ZUERST prüfen:**
   - `bfagent_get_refactor_options()` → Was kann refactored werden?
   - `bfagent_check_path_protection()` → Ist Pfad geschützt?

2. **Session Management:**
   - `start_refactor_session()` BEVOR du Änderungen machst
   - `end_refactor_session()` NACHDEM alle Änderungen gemacht sind

3. **Naming Conventions:**
   - `bfagent_get_naming_convention()` für spezifische App
   - `bfagent_list_naming_conventions()` für Übersicht

### Sicherheit
- ✅ IMMER Path Protection checken vor Datei-Änderungen
- ✅ IMMER Dependencies beachten (refactor depends_on first)
- ✅ NIEMALS Absolute-Protected Pfade ändern
- ✅ Session ID tracken für Audit Trail

## 🚀 PRODUCTION STATUS

| Komponente | Status | Details |
|-----------|--------|----------|
| **Server.py** | ✅ READY | 7 Tools definiert, Dispatcher implementiert |
| **Refactor Service** | ✅ READY | Alle 7 Methoden funktional |
| **Django Models** | ✅ READY | MCPDomainConfig, MCPProtectedPath vorhanden |
| **Database Tables** | ✅ READY | 11 MCP Tabellen erstellt (siehe create_mcp_tables.py) |
| **Naming Conventions** | ✅ READY | 17 Apps integriert (siehe NAMING_CONVENTIONS_COMPLETE.md) |
| **Component Types** | ✅ READY | 6 Types: Handler, Service, Model, View, Admin, Test |
| **Risk Levels** | ✅ READY | 4 Levels: low, medium, high, critical |
| **Protection Levels** | ✅ READY | 4 Levels: none, read_only, protected, absolute |
| **Documentation** | ✅ READY | README, Beispiele, Workflow |
| **Testing** | ✅ READY | All tools tested successfully |

---

**Erstellt:** Dezember 2025  
**Version:** 2.0.0.dev0  
**Package:** `bfagent-mcp`
