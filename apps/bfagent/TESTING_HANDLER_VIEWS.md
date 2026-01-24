# 🧪 Handler-Views Testing Guide

## ✅ **STATUS: READY FOR TESTING!**

### **Branch:** `feature/handler-testing`
### **URLs:** Parallel zu alten Views (beide funktionieren)

---

## 🚀 **SCHRITT 1: Server starten**

```bash
# Im Terminal:
make dev

# Oder direkt:
python manage.py runserver
```

**Server startet auf:** `http://localhost:8000`

---

## 🧪 **SCHRITT 2: Test-URLs**

### **Alte Version (crud_views.py):**
```
POST /projects/projects/1/enrich/run/
POST /projects/projects/1/enrich/execute/
```

### **Neue Version (enrichment_views_handler.py):**
```
POST /projects/projects/1/enrich/run/handler/
POST /projects/projects/1/enrich/execute/handler/
```

**⚠️ WICHTIG:** Doppeltes `projects/` ist korrekt! (config + app URLs)

---

## 📝 **SCHRITT 3: Manuelles Testen**

### **Option A: Browser Console Test**

1. **Project öffnen:** `http://localhost:8000/projects/projects/1/`
2. **Browser Console öffnen:** F12
3. **Test-Fetch ausführen:**

```javascript
// Test Handler-Version
fetch('/projects/projects/1/enrich/run/handler/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    body: 'agent_id=1&action=enhance_description&context=test'
})
.then(r => r.text())
.then(html => console.log(html))
.catch(e => console.error(e));
```

### **Option B: cURL Test**

```bash
# Get CSRF Token first
curl -c cookies.txt http://localhost:8000/projects/projects/1/

# Test Handler Version
curl -b cookies.txt -X POST \
  http://localhost:8000/projects/projects/1/enrich/run/handler/ \
  -d "agent_id=1&action=enhance_description&context=test" \
  -H "X-CSRFToken: YOUR_TOKEN_HERE"
```

### **Option C: Python Test Script**

```python
import requests

# Session für Cookies
session = requests.Session()

# Get CSRF Token
r = session.get('http://localhost:8000/projects/projects/1/')
csrf_token = session.cookies['csrftoken']

# Test Handler Version
response = session.post(
    'http://localhost:8000/projects/projects/1/enrich/run/handler/',
    data={
        'agent_id': 1,
        'action': 'enhance_description',
        'context': 'test'
    },
    headers={'X-CSRFToken': csrf_token}
)

print(response.status_code)
print(response.text)
```

---

## 🔍 **SCHRITT 4: Logs checken**

```bash
# Server-Logs beobachten:
# Im Terminal wo der Server läuft

# Erwartete Handler-Logs:
# 🚀 project_enrich_run_handler - Project: 1
# ✅ Context prepared for action: enhance_description
# ✅ Enrichment executed successfully
```

---

## ✅ **ERFOLGSKRITERIEN:**

### **Handler-Version muss:**
- [ ] Ohne Fehler starten
- [ ] Context korrekt vorbereiten
- [ ] EnrichmentHandler ausführen
- [ ] Ergebnis-Template rendern
- [ ] Keine 500 Errors werfen

### **Vergleich Alt vs. Neu:**
- [ ] Gleiche Funktionalität
- [ ] Gleiche Templates
- [ ] Gleiche Responses
- [ ] Bessere Logs (Handler-Version)
- [ ] Saubererer Code (Handler-Version)

---

## 🐛 **BEKANNTE ISSUES:**

### **1. LLM-Integration noch nicht komplett**
- `EnrichmentHandler._enhance_description()` nutzt echtes LLM
- Andere Actions (character_cast) noch mit Sample Data
- **FIX:** Nicht kritisch für Testing

### **2. Template-Paths**
- Beide Versionen nutzen gleiche Templates
- Sollte funktionieren

### **3. Missing Request Context**
- **FIXED:** ✅ `_save_enrichment_results` bekommt jetzt `request`

---

## 📊 **TESTING CHECKLIST:**

### **Basis-Tests:**
- [ ] Server startet ohne Errors
- [ ] `django check` läuft durch
- [ ] Handler-URLs sind erreichbar
- [ ] CSRF Token wird akzeptiert

### **Functionality Tests:**
- [ ] Enrichment Preview wird angezeigt
- [ ] Execute ruft LLM auf
- [ ] Results werden korrekt gespeichert
- [ ] Templates rendern korrekt

### **Error Handling:**
- [ ] ValidationError wird korrekt behandelt
- [ ] ProcessingError zeigt Fehler an
- [ ] Fehlende Parameter werden abgefangen
- [ ] LLM-Fehler haben Fallback

### **Performance:**
- [ ] Response-Zeit < 2 Sekunden (ohne LLM)
- [ ] Keine N+1 Queries
- [ ] Logging funktioniert
- [ ] Keine Memory Leaks

---

## 🎯 **NACH ERFOLGREICHEM TEST:**

### **If All Green:**
```bash
# Commit Test-Änderungen
git add .
git commit -m "test: Handler views parallel testing setup"

# Merge zurück zu main
git checkout main
git merge feature/handler-testing

# Alte Views entfernen (optional)
# ... siehe MIGRATION_COMPARISON.md
```

### **If Issues Found:**
```bash
# Bleib im Branch
# Fixe Issues
# Re-test
# Dokumentiere Findings
```

---

## 💡 **DEBUGGING TIPPS:**

### **Django Shell Testing:**
```python
python manage.py shell

from apps.bfagent.handlers import EnrichmentHandler, ProjectInputHandler

# Test Input Handler
input_handler = ProjectInputHandler()
context = input_handler.prepare_enrichment_context(
    project_id=1,
    agent_id=1,
    action='enhance_description'
)
print(context)

# Test Processing Handler
processing_handler = EnrichmentHandler()
result = processing_handler.execute(context)
print(result)
```

### **Log-Level erhöhen:**
```python
# config/settings/development.py
LOGGING = {
    'loggers': {
        'apps.bfagent': {
            'level': 'DEBUG',
        }
    }
}
```

---

## 📞 **HELP:**

**Bei Problemen:**
1. Check Server Logs
2. Check Browser Console
3. Django Shell Testing
4. Review Handler Code
5. Compare mit alter Version

**Dokumentation:**
- `handlers/README.md` - Architecture
- `handlers/USAGE_EXAMPLE.md` - Code Examples
- `views/MIGRATION_COMPARISON.md` - Old vs New

---

## 🎉 **SUCCESS SCENARIO:**

**Wenn alles funktioniert:**
1. ✅ Handler-URLs funktionieren
2. ✅ Gleiche Functionality wie alte Version
3. ✅ Bessere Code-Qualität
4. ✅ Einfacher zu testen
5. ✅ Bereit für Production!

**Dann:** Merge & Deploy! 🚀
