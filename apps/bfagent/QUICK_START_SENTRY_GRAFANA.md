# Quick Start: Sentry & Grafana MCP Integration

**Get started in 30 minutes!**

---

## 🚀 Phase 1: Sentry Setup (15 min)

### Step 1: Create Sentry Account
```bash
# Free tier: 5,000 events/month
https://sentry.io/signup/
```

### Step 2: Install Sentry SDK
```bash
pip install sentry-sdk
```

### Step 3: Basic Integration
```python
# In settings.py or settings_development.py
import sentry_sdk

sentry_sdk.init(
    dsn="https://YOUR_DSN@sentry.io/PROJECT_ID",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    environment="development"
)
```

### Step 4: Test It
```python
# Test error capture
sentry_sdk.capture_message("bfagent Sentry integration test!")
```

**Check:** https://sentry.io → Issues → Should see test message

---

## 🚀 Phase 2: Sentry MCP (10 min)

### Step 1: Install MCP
```bash
npm install -g @getsentry/sentry-mcp
```

### Step 2: Get Auth Token
```bash
# In Sentry UI:
# Settings → Account → API → Auth Tokens
# Scopes: project:read, event:read, org:read
```

### Step 3: Configure MCP
```json
// In Claude Desktop config or similar
{
  "mcpServers": {
    "sentry": {
      "command": "sentry-mcp",
      "args": ["--token", "YOUR_TOKEN", "--org", "YOUR_ORG"]
    }
  }
}
```

### Step 4: Test MCP
```bash
# Use Claude or another MCP client
"List Sentry issues for project bfagent"
```

---

## 🚀 Phase 3: Admin Diagnostics + Sentry (5 min)

### Extend AdminDiagnosticsService

```python
# apps/bfagent/services/admin_diagnostics.py
import sentry_sdk

class AdminDiagnosticsService:
    def test_admin_urls(self, app_label=None, auto_fix=False):
        results = {
            'tested': [],
            'errors': [],
            'fixed': []
        }
        
        # ... existing code ...
        
        # NEW: Send errors to Sentry
        for error in results['errors']:
            sentry_sdk.capture_message(
                f"Admin Error: {error['model']}",
                level='error',
                extras={
                    'url': error['url'],
                    'error': error.get('error'),
                    'model': error['model']
                }
            )
        
        return results
```

---

## 🎯 Phase 4: Grafana Setup (Optional, 15 min)

### Step 1: Grafana Cloud Account
```bash
# Free tier: 10k metrics, 50GB logs
https://grafana.com/auth/sign-up/create-user
```

### Step 2: Install Grafana MCP
```bash
npm install -g @grafana/mcp-grafana
```

### Step 3: Get Service Account Token
```bash
# In Grafana UI:
# Administration → Service Accounts → Add service account
# Role: Admin
# Add token
```

### Step 4: Configure MCP
```json
{
  "mcpServers": {
    "grafana": {
      "command": "mcp-grafana",
      "args": [
        "--url", "https://YOUR_ORG.grafana.net",
        "--token", "YOUR_TOKEN"
      ]
    }
  }
}
```

---

## ✅ VERIFICATION

### Test Sentry
```python
# Run admin diagnostics
python manage.py admin_diagnostics test-admin --app writing_hub

# Check Sentry:
# - Should see captured errors
# - Should have full context
# - Should have breadcrumbs
```

### Test Sentry MCP
```bash
# In Claude or MCP client:
"Show me the latest errors in bfagent project"
"Analyze issue #123 and suggest a fix"
```

### Test Grafana MCP (Optional)
```bash
# In Claude or MCP client:
"Create a dashboard for bfagent monitoring"
"Query error rate for the last hour"
```

---

## 🎊 SUCCESS!

You now have:
- ✅ Automatic error tracking (Sentry)
- ✅ AI-powered error analysis (Sentry MCP)
- ✅ Admin diagnostics integration
- ✅ Optional: Monitoring dashboards (Grafana)

---

## 🚀 NEXT STEPS

### Week 1: Seer Integration
```python
# Use Sentry's AI for auto-fixes
from sentry_mcp import invoke_seer

# When error detected:
analysis = invoke_seer(issue_id)
if analysis.has_fix and analysis.confidence > 0.9:
    apply_fix(analysis.fix)
```

### Week 2: Advanced Monitoring
```python
# Create performance dashboard
from grafana_mcp import create_dashboard

create_dashboard({
    "title": "bfagent Performance",
    "panels": [
        {"title": "Response Times", "query": "..."},
        {"title": "Error Rates", "query": "..."}
    ]
})
```

---

## 📚 Resources

- **Sentry Docs:** https://docs.sentry.io/
- **Sentry MCP:** https://docs.sentry.io/product/sentry-mcp/
- **Grafana Docs:** https://grafana.com/docs/
- **Grafana MCP:** https://github.com/grafana/mcp-grafana

---

**Status:** 🎉 Ready to use!  
**Time:** ~30 minutes  
**Value:** Infinite! 🚀
