# 🚀 MCP Quick Start

**TL;DR:** MCP Server is installed and ready to use!

---

## ✅ What's Installed

```bash
✅ bfagent-sqlite-mcp v2.0.0 (Core Package)
✅ bfagent.mcp (Django Integration)
✅ Cursor IDE Config (.cursor/mcp_config.json)
```

---

## 🎯 Use It NOW

### In Cursor IDE (Recommended)

1. **Restart Cursor**
2. **Ask natural questions:**
   - "Show all active domains"
   - "Get domain statistics"
   - "Search for writing domain"

### Via Command Line

```bash
python manage.py run_mcp_server
```

### In Python

```python
from bfagent.mcp.server import BFAgentMCPServer

server = BFAgentMCPServer()
domains = server.get_domains()
stats = server.get_domain_stats()
```

---

## 📋 Available Tools

### Django ORM Tools
- `get_domains()` - List all active domains
- `get_domain_by_slug(slug)` - Get specific domain  
- `get_domain_stats()` - Domain statistics
- `search_domains(query)` - Search domains

### Core SQLite Tools (from package)
- `execute_query(sql)` - Execute SQL
- `get_schema()` - Database schema
- `analyze_table(name)` - Table analysis

---

## ⚙️ Configuration

```python
# config/settings.py

MCP_READ_ONLY = False          # Development mode
MCP_POOL_SIZE = 10             # Connection pool
MCP_AUDIT_ENABLED = True       # Audit logging  
MCP_METRICS_ENABLED = True     # Metrics
```

---

## 📚 Documentation

- **Full Plan:** `docs/MCP_SQLITE_INTEGRATION_PLAN.md`
- **Success Report:** `docs/MCP_INTEGRATION_SUCCESS.md`
- **User Guide:** `docs/MCP_READY_TO_USE.md`
- **This File:** Quick reference

---

## 🎉 That's It!

MCP is ready. Just use it! 🚀
