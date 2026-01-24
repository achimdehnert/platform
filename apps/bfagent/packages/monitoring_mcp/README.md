# BF Agent Monitoring MCP

**Model Context Protocol Server for BF Agent Auto-Healing & Error Monitoring**

## Features

- 🔍 **Real-time Monitoring** - Monitor auto-healing events across all apps
- 📊 **Statistics & Analytics** - Get detailed healing statistics and trends
- 🔧 **Manual Triggers** - Trigger healing checks for specific apps
- 🤖 **Pattern Analysis** - AI-powered error pattern detection
- 📈 **Predictive Monitoring** - Predict future errors before they occur
- 🎯 **Domain-specific** - Monitor domain-specific issues

## Tools

### 1. `monitor_auto_healing`
Monitor auto-healing events in real-time.

**Input:**
```json
{
  "time_range": "24h",
  "app_filter": "ui_hub"
}
```

### 2. `get_healing_stats`
Get comprehensive auto-healing statistics.

**Input:**
```json
{
  "period": "week",
  "group_by": "app"
}
```

### 3. `trigger_healing_check`
Manually trigger healing check for specific app.

**Input:**
```json
{
  "app_label": "ui_hub",
  "force": true
}
```

### 4. `analyze_error_pattern`
Analyze error patterns across apps.

**Input:**
```json
{
  "lookback_days": 7,
  "min_occurrences": 3
}
```

### 5. `get_monitoring_dashboard`
Get monitoring dashboard data.

**Input:**
```json
{
  "metrics": ["healing_rate", "error_rate", "performance"]
}
```

### 6. `list_recent_healings`
List recent auto-healing events.

**Input:**
```json
{
  "limit": 20,
  "app_filter": "ui_hub"
}
```

### 7. `predict_errors`
ML-based error prediction.

**Input:**
```json
{
  "app_label": "ui_hub",
  "horizon": "24h"
}
```

### 8. `export_healing_logs`
Export healing logs for analysis.

**Input:**
```json
{
  "format": "json",
  "time_range": "week"
}
```

## Installation

```bash
cd packages/monitoring_mcp
pip install -e .
```

## Usage

### In MCP Config:
```json
{
  "mcpServers": {
    "bfagent-monitoring": {
      "command": "python",
      "args": ["-m", "monitoring_mcp.server"],
      "env": {
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "PYTHONPATH": "/path/to/bfagent"
      }
    }
  }
}
```

### In Django:
```python
# Track healing events
from apps.core.middleware.auto_healing import track_healing_event

track_healing_event(
    app="ui_hub",
    error_type="ProgrammingError",
    table_name="ui_hub_categories",
    action="migrate",
    success=True
)
```

## Integration with Sentry

This MCP works seamlessly with Sentry MCP:

```
Sentry MCP (External) → Monitoring MCP (Internal) → Auto-Healing Middleware
```

## Architecture

```
┌─────────────────────────────────────┐
│   Windsurf / AI Assistant           │
│   (User Interface)                  │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│   Monitoring MCP Server             │
│   - Tools (8 monitoring tools)      │
│   - Django Integration              │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│   Auto-Healing Middleware           │
│   - Exception catching              │
│   - Auto-fix execution              │
│   - Event tracking                  │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│   Django Applications               │
│   (All apps with auto-healing)      │
└─────────────────────────────────────┘
```

## Status

**Phase 1:** ✅ Core monitoring tools implemented  
**Phase 2:** 🔄 ML predictions (in progress)  
**Phase 3:** 📋 Dashboard API (planned)

## License

Part of BF Agent System
