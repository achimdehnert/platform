# 🚀 Celery Quick Start Guide

## ✅ Installation Complete!

- ✅ Celery 5.3.4 installed
- ✅ Redis 4.6.0 installed
- ✅ Django settings configured
- ✅ Redis server running in WSL

---

## 🎯 TWO WAYS TO TEST AUTO-ILLUSTRATION:

### **Option A: MVP (Synchronous) - NO CELERY NEEDED** ⚡

**Best for:** Quick testing, development, mock mode

```powershell
# Just start Django server
python manage.py runserver

# Navigate to:
http://localhost:8000/illustrations/chapter/1/gallery/

# Click "Auto-Illustrate" → Works instantly!
# Mock Mode = FREE testing (no API calls)
```

**Pros:**
- ✅ Works immediately
- ✅ No background services
- ✅ Simple setup
- ✅ Great for testing

**Cons:**
- ❌ Blocks UI during generation
- ❌ Not suitable for production
- ❌ No progress updates

---

### **Option B: Production (Async with Celery)** 🔥

**Best for:** Production, real API calls, background processing

#### **Step 1: Start Redis (in WSL)**

```bash
# In WSL terminal:
sudo service redis-server start

# Test Redis:
redis-cli ping
# Should return: PONG
```

#### **Step 2: Start Celery Worker (New PowerShell Terminal)**

```powershell
# Terminal 1 - Celery Worker:
cd C:\Users\achim\github\bfagent
.venv\Scripts\Activate.ps1
celery -A config worker -l info --pool=solo

# Keep this running!
# You should see:
# - celery@DESKTOP ready.
# - mingle: all alone
# - celery@DESKTOP has started.
```

**Note:** `--pool=solo` is required for Windows!

#### **Step 3: Start Django Server (Another Terminal)**

```powershell
# Terminal 2 - Django Server:
cd C:\Users\achim\github\bfagent
.venv\Scripts\Activate.ps1
python manage.py runserver
```

#### **Step 4: Update View to Use Async**

In `auto_illustration_views.py`, update the template to call:
- **Current:** `auto_illustrate_chapter_sync` (MVP - immediate)
- **Production:** `auto_illustrate_chapter_async` (with Celery)

Change template URL from:
```javascript
'{% url "bfagent:illustration:auto-illustrate-chapter" chapter.pk %}'
```

To:
```javascript
'{% url "bfagent:illustration:auto-illustrate-chapter-async" chapter.pk %}'
```

#### **Step 5: Test Async Auto-Illustration**

```
1. Navigate to: http://localhost:8000/illustrations/chapter/1/gallery/
2. Click "Auto-Illustrate"
3. Modal opens with options
4. Click "Start Auto-Illustration"
5. Watch progress bar (polls task status every 2 seconds)
6. See results when complete!
```

**Pros:**
- ✅ Non-blocking UI
- ✅ Background processing
- ✅ Real-time progress updates
- ✅ Production-ready

**Cons:**
- ❌ Requires Redis + Celery running
- ❌ More complex setup
- ❌ Windows requires `--pool=solo`

---

## 🔧 CONFIGURATION

### **Mock Mode vs Real API Calls**

**File:** `apps/bfagent/views/auto_illustration_views.py`

```python
# Line 52 - Toggle Mock Mode:
mock_mode = True   # FREE - No API calls (current)
mock_mode = False  # PAID - Real DALL-E/Stable Diffusion calls
```

### **API Keys (for Production)**

Create `.env` file in project root:

```env
# OpenAI API Key (for DALL-E)
OPENAI_API_KEY=sk-...

# Stable Diffusion API Key (if using)
STABLE_DIFFUSION_API_KEY=your_key_here
```

### **Cost Estimates (Real API Calls)**

**DALL-E 3:**
- Standard: $0.04 per image
- HD: $0.08 per image
- 3 images = $0.12 - $0.24

**Stable Diffusion:**
- ~$0.002 per image
- 3 images = $0.006

---

## 🐛 TROUBLESHOOTING

### **Issue: Celery worker won't start**

**Error:** `ModuleNotFoundError: No module named 'celery'`

**Fix:**
```powershell
pip install celery[redis]==5.3.4
```

---

### **Issue: Redis connection refused**

**Error:** `redis.exceptions.ConnectionError: Error 10061`

**Fix:**
```bash
# In WSL:
sudo service redis-server start
redis-cli ping  # Should return PONG
```

---

### **Issue: Task not executing**

**Check Celery Worker Terminal:**
- Should show: `Received task: apps.bfagent.tasks.auto_illustrate_chapter_task`
- Should show progress: `Task ... started`

**Check Redis:**
```bash
redis-cli
127.0.0.1:6379> KEYS *
# Should show celery keys
```

---

### **Issue: "PermissionError" on Windows**

**Error:** `PermissionError: [WinError 5] Access is denied`

**Fix:** Use `--pool=solo` flag:
```powershell
celery -A config worker -l info --pool=solo
```

---

## 📊 MONITORING

### **Watch Celery Tasks**

In Celery Worker terminal, you'll see:
```
[INFO/MainProcess] Task apps.bfagent.tasks.auto_illustrate_chapter_task[id] received
[INFO/MainProcess] Task started: ANALYZING
[INFO/MainProcess] Task started: GENERATING_PROMPTS
[INFO/MainProcess] Task started: GENERATING_IMAGES
[INFO/MainProcess] Task succeeded: SUCCESS
```

### **Check Task Results in Django**

```python
from celery.result import AsyncResult

task_id = 'your-task-id-here'
result = AsyncResult(task_id)

print(f"State: {result.state}")
print(f"Info: {result.info}")
```

---

## 🎉 SUCCESS CRITERIA

**MVP Working:**
- ✅ Django server starts without errors
- ✅ Auto-Illustrate button visible in gallery
- ✅ Click button → Modal opens
- ✅ Start → Progress bar → Results (instant in mock mode)
- ✅ Mock warning displayed

**Production Working:**
- ✅ Redis running: `redis-cli ping` returns `PONG`
- ✅ Celery worker shows: `celery@DESKTOP ready`
- ✅ Django server running
- ✅ Task appears in Celery terminal
- ✅ Progress bar updates (30% → 50% → 75% → 100%)
- ✅ Results display cost and duration
- ✅ Images saved to database

---

## 🚀 RECOMMENDED WORKFLOW

**Development:**
1. Use **MVP (Sync)** for fast iteration
2. Mock Mode enabled (no API costs)
3. Test UI and logic

**Staging:**
1. Use **Production (Async)** 
2. Mock Mode enabled (no API costs)
3. Test Celery infrastructure

**Production:**
1. Use **Production (Async)**
2. Mock Mode disabled
3. Real API keys in `.env`
4. Monitor costs!

---

## 📝 NEXT STEPS

1. **Test MVP now** - Works immediately!
2. **Set up Celery** - When ready for production
3. **Add API keys** - When ready for real image generation
4. **Monitor costs** - Track API usage
5. **Scale workers** - Add more Celery workers if needed

---

## 💡 TIPS

- **Start with MVP** - Fastest way to test
- **Mock Mode First** - Don't waste money during development
- **Monitor Celery** - Keep worker terminal visible
- **Check Logs** - Django console shows errors
- **Test Small** - 1-2 images first, not 10!

---

**System Ready! Start testing now!** 🎉
