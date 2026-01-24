# 🚀 Celery Setup Guide - 5 Minutes

## ✅ Was wir grade erstellt haben:

1. ✅ `config/celery.py` - Celery app configuration
2. ✅ `config/__init__.py` - Auto-load Celery with Django
3. ✅ `apps/bfagent/tasks.py` - Async task definitions

---

## 📦 Installation (5 Min)

### 1. Install Redis (Windows)

**Option A: WSL (Empfohlen)**
```powershell
wsl --install  # Falls noch nicht installiert
wsl
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
redis-cli ping  # Should return: PONG
```

**Option B: Windows Native (Memurai)**
```powershell
# Download: https://www.memurai.com/get-memurai
# Install and start service
```

### 2. Install Celery
```powershell
.venv\Scripts\Activate.ps1
pip install celery[redis]==5.3.4
pip install redis==5.0.1
```

### 3. Update settings.py
```python
# Add to config/settings.py

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Berlin'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
```

---

## 🚀 Usage

### Start Celery Worker (Terminal 1)
```powershell
celery -A config worker --loglevel=info --pool=solo
```

### Start Django Server (Terminal 2)
```powershell
python manage.py runserver
```

### Test Task from Django Shell
```python
python manage.py shell

from apps.bfagent.tasks import auto_illustrate_chapter_task

# Trigger async task
task = auto_illustrate_chapter_task.delay(
    chapter_id=1,
    user_id=1,
    max_illustrations=3
)

# Check status
task.status  # 'PENDING', 'ANALYZING', 'SUCCESS', etc.
task.result  # Result dict when done
```

---

## 📊 Monitoring (Optional)

### Flower - Web UI for Celery
```powershell
pip install flower
celery -A config flower
# Open: http://localhost:5555
```

---

## ✅ Next Steps

1. **Test MVP** (jetzt sofort):
   ```bash
   python test_auto_illustration.py
   ```

2. **Create View** (nächster Schritt):
   - Auto-Illustration Button in Chapter Detail View
   - AJAX call to start task
   - WebSocket or Polling for progress
   - Display generated images

3. **Production** (später):
   - Deploy Redis to production
   - Configure Celery workers as system service
   - Add monitoring (Sentry, Prometheus)
   - Implement retry strategies
   - Add rate limiting

---

## 🐛 Troubleshooting

**Redis not running:**
```bash
# WSL
sudo service redis-server status
sudo service redis-server start

# Windows (Memurai)
# Check Windows Services
```

**Celery import errors:**
```bash
# Make sure you're in project root
cd C:\Users\achim\github\bfagent
# Activate venv
.venv\Scripts\Activate.ps1
# Try again
celery -A config worker --loglevel=info --pool=solo
```

**Task not found:**
```python
# Make sure apps.bfagent is in INSTALLED_APPS
# Restart Celery worker after code changes
```

---

## 🎉 DONE!

You now have:
✅ Async task processing
✅ Background job queue
✅ Progress tracking
✅ Scalable architecture

**Test it:** `python test_auto_illustration.py`
