# MCP Server Quality Scorecard Template

> Based on ADR-012: MCP Server Quality Standards

## Server Information

| Field | Value |
|-------|-------|
| **Server Name** | `[server_name]` |
| **Version** | `[version]` |
| **Repository** | `[repo_path]` |
| **Review Date** | `[YYYY-MM-DD]` |
| **Reviewer** | `[name]` |

---

## 📊 Score Summary

| Category | Weight | Raw Score | Weighted | Notes |
|----------|--------|-----------|----------|-------|
| 🔧 Tool Design | 20% | /10 | /20 | |
| 🛡️ Error Handling | 15% | /10 | /15 | |
| 📝 Documentation | 15% | /10 | /15 | |
| 🧪 Test Coverage | 20% | /10 | /20 | |
| 🔒 Security | 15% | /10 | /15 | |
| 📊 Observability | 10% | /10 | /10 | |
| 🏗️ Architecture | 5% | /10 | /5 | |
| **TOTAL** | **100%** | | **/100** | |

### Grade

| Score | Grade | Status |
|-------|-------|--------|
| 90-100 | A | ✅ Excellent |
| 80-89 | B | ✅ Good |
| 70-79 | C | ✅ Acceptable |
| 60-69 | D | ⚠️ Needs Work |
| 50-59 | E | ⚠️ Minimum |
| <50 | F | ❌ Failing |

**This Server: Grade [X] ([score]/100)**

---

## 🔧 Tool Design (20%)

| Criterion | Score (0-2) | Evidence |
|-----------|-------------|----------|
| Naming Convention | | snake_case, descriptive |
| Parameter Design | | sensible defaults, optional params |
| Type Hints | | complete typing |
| Docstrings | | Args, Returns, Raises documented |
| Semantic Clarity | | one tool = one purpose |
| **Subtotal** | **/10** | |

### Tools Reviewed

| Tool Name | Naming | Params | Types | Docs | Clarity |
|-----------|--------|--------|-------|------|---------|
| `tool_1` | ✅/⚠️/❌ | ✅/⚠️/❌ | ✅/⚠️/❌ | ✅/⚠️/❌ | ✅/⚠️/❌ |
| `tool_2` | | | | | |

---

## 🛡️ Error Handling (15%)

| Criterion | Score (0-2) | Evidence |
|-----------|-------------|----------|
| Try/Catch Coverage | | external calls protected |
| Error Classification | | client vs server vs external |
| Structured Responses | | consistent error format |
| Graceful Degradation | | fallbacks on partial failures |
| Error Logging | | sufficient context |
| **Subtotal** | **/10** | |

### Error Patterns Found

```python
# Example of good/bad patterns found
```

---

## 📝 Documentation (15%)

| Criterion | Score (0-2) | Evidence |
|-----------|-------------|----------|
| README.md | | installation, config, quick start |
| Tool Documentation | | all tools with examples |
| Configuration Guide | | env vars, config files |
| Changelog | | CHANGELOG.md maintained |
| Troubleshooting | | common issues documented |
| **Subtotal** | **/10** | |

### Missing Documentation

- [ ] Item 1
- [ ] Item 2

---

## 🧪 Test Coverage (20%)

| Criterion | Score (0-3/2) | Evidence |
|-----------|---------------|----------|
| Unit Tests | /3 | isolated tool tests |
| Integration Tests | /3 | MCP protocol tests |
| Coverage % | /2 | ≥80%=2, ≥60%=1, <60%=0 |
| Edge Cases | /2 | error paths, boundaries |
| **Subtotal** | **/10** | |

### Test Metrics

- **Coverage**: [X]%
- **Unit Tests**: [X] tests
- **Integration Tests**: [X] tests
- **E2E Tests**: [X] tests

---

## 🔒 Security (15%)

| Criterion | Score (0-3/2) | Evidence |
|-----------|---------------|----------|
| Input Validation | /3 | all inputs validated |
| Secrets Management | /3 | no hardcoded secrets |
| Rate Limiting | /2 | abuse protection |
| Output Sanitization | /2 | no sensitive data leaked |
| **Subtotal** | **/10** | |

### Security Issues Found

| Severity | Issue | Location |
|----------|-------|----------|
| 🔴 Critical | | |
| 🟠 High | | |
| 🟡 Medium | | |

---

## 📊 Observability (10%)

| Criterion | Score (0-3/2) | Evidence |
|-----------|---------------|----------|
| Structured Logging | /3 | JSON format, context, levels |
| Metrics | /3 | counters, histograms |
| Request Tracing | /2 | request IDs, correlation |
| Health Endpoint | /2 | readiness, liveness |
| **Subtotal** | **/10** | |

---

## 🏗️ Architecture (5%)

| Criterion | Score (0-2) | Evidence |
|-----------|-------------|----------|
| Single Responsibility | | one server, one purpose |
| Dependency Management | | pinned versions, minimal |
| Code Organization | | clear structure, modules |
| Configuration | | externalized, validated |
| Async Best Practices | | no blocking calls |
| **Subtotal** | **/10** | |

---

## 🚨 Issues Summary

### Critical (P0) - Must Fix

| ID | Issue | Location | Owner |
|----|-------|----------|-------|
| | | | |

### High (P1) - Should Fix

| ID | Issue | Location | Owner |
|----|-------|----------|-------|
| | | | |

### Medium (P2) - Nice to Fix

| ID | Issue | Location | Owner |
|----|-------|----------|-------|
| | | | |

---

## 💡 Recommendations

1. **Immediate**: 
2. **Short-term**: 
3. **Long-term**: 

---

## 📋 Action Items

| Priority | Action | Owner | Due |
|----------|--------|-------|-----|
| P0 | | | |
| P1 | | | |
| P2 | | | |

---

## Changelog

| Date | Reviewer | Change |
|------|----------|--------|
| | | Initial review |
