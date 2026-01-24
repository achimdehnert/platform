# Medical Translation System - MedTrans

🎉 **Production-Ready PowerPoint Translation Pipeline with DeepL Integration**

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Handlers](#handlers)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

MedTrans is a comprehensive Django application for managing professional medical translations of PowerPoint presentations using DeepL API. It provides a complete end-to-end pipeline from upload to translated output, with professional editing capabilities.

### Key Capabilities

- **Upload & Manage** PowerPoint files with customer tracking
- **Automatic Translation** via DeepL API with caching
- **Professional Editing** interface for manual refinements
- **PPTX Regeneration** with edited translations
- **Multi-language Support** (DE, EN, FR, ES, IT)
- **Progress Tracking** with real-time status updates

---

## ✨ Features

### 1. Customer Management
- Create and manage translation customers
- Dashboard access control
- User-scoped data isolation

### 2. Translation Pipeline
- **Extract**: XML-based text extraction from PPTX files
- **Translate**: Batch translation via DeepL API
- **Repackage**: PPTX file regeneration with translations

### 3. Edit & Refinement
- Slide-by-slide text editing interface
- Manual edit tracking
- Save and regenerate workflow
- Multiple PPTX versions with timestamps

### 4. Status Management
- **uploaded** → **extracting** → **translating** → **reviewing** → **completed**
- Re-translate capability
- Delete (including hanging processes)
- Progress tracking (percentage & counts)

---

## 🏗️ Architecture

### Django App Structure
```
apps/medtrans/
├── handlers/              # GenAgent Handler System
│   ├── extract_handler.py       # Text extraction
│   ├── translate_handler.py     # Translation orchestration
│   └── repackage_handler.py     # PPTX regeneration
├── services/              # Core Services
│   ├── xml_text_extractor.py    # XML parsing
│   ├── xml_direct_translator.py # Translation logic
│   ├── translation_providers.py # DeepL API client
│   └── translation_cache.py     # Cache system
├── models.py              # Data models
├── views.py               # View logic
├── urls.py                # URL routing
├── forms.py               # Django forms
├── admin.py               # Admin interface
└── README.md              # This file

templates/medtrans/
├── presentation_list.html       # Main dashboard
├── presentation_upload.html     # Upload form
├── presentation_edit.html       # Edit interface
├── customer_list.html           # Customer management
└── customer_form.html           # Customer creation
```

### Handler System (GenAgent)
- **ExtractTextsHandler**: Extracts text from PPTX XML structure
- **TranslateTextsHandler**: Orchestrates DeepL API calls
- **RepackagePPTXHandler**: Regenerates PPTX with translations

---

## 🚀 Installation

### 1. Prerequisites
```bash
# Python packages (add to requirements.txt)
python-decouple>=3.8
requests>=2.31.0
```

### 2. Database Migration
```bash
python manage.py makemigrations medtrans
python manage.py migrate medtrans
```

### 3. Create Superuser
```bash
python manage.py createsuperuser
```

---

## ⚙️ Configuration

### 1. Environment Variables (.env)
```bash
# DeepL API Configuration
DEEPL_API_KEY=your_deepl_api_key_here

# Optional Translation Settings
TRANSLATION_CACHE_ENABLED=True
TRANSLATION_MAX_RETRIES=3
```

### 2. Django Settings (config/settings/base.py)
```python
# Medical Translation Settings
DEEPL_API_KEY = config("DEEPL_API_KEY", default="")
DEEPL_API_URL = "https://api-free.deepl.com/v2"  # Use api.deepl.com for Pro

# Translation Settings
TRANSLATION_CACHE_ENABLED = config("TRANSLATION_CACHE_ENABLED", default=True, cast=bool)
TRANSLATION_MAX_RETRIES = config("TRANSLATION_MAX_RETRIES", default=3, cast=int)
```

### 3. Directory Structure
```bash
# Create required directories
mkdir -p media/medtrans/presentations
mkdir -p media/medtrans/output
mkdir -p cache
```

---

## 📖 Usage

### User Workflow

1. **Create Customer**
   - Navigate to `/medtrans/customers/create/`
   - Fill in customer details
   - Submit form

2. **Upload Presentation**
   - Click "Upload New Presentation"
   - Select PPTX file
   - Choose customer, source language, and target language
   - Submit

3. **Start Translation**
   - Click "Translate" button
   - Pipeline executes automatically:
     - Extract texts from PPTX
     - Translate via DeepL API
     - Repackage into new PPTX
   - Watch status updates

4. **Edit Translations** (Optional)
   - Click "Edit" button
   - Review and modify translations
   - Click "Save Changes"

5. **Regenerate PPTX** (After editing)
   - Click "Regenerate PPTX"
   - New file created with timestamp
   - Download from media/medtrans/output/

6. **Alternative Actions**
   - **Re-translate**: Reset and translate again
   - **Delete**: Remove presentation (even if hanging)

---

## 🌐 API Endpoints

### Presentation Management
```
GET  /medtrans/                                 # List presentations
GET  /medtrans/upload/                          # Upload form
POST /medtrans/upload/                          # Handle upload

POST /medtrans/presentations/<id>/translate/    # Start translation
POST /medtrans/presentations/<id>/delete/       # Delete presentation
POST /medtrans/presentations/<id>/reset/        # Reset for re-translation

GET  /medtrans/presentations/<id>/edit/         # Edit interface
POST /medtrans/presentations/<id>/update/       # Save changes
POST /medtrans/presentations/<id>/regenerate/   # Regenerate PPTX
```

### Customer Management
```
GET  /medtrans/customers/                       # List customers
GET  /medtrans/customers/create/                # Create form
POST /medtrans/customers/create/                # Handle creation
```

---

## 🗄️ Database Schema

### Presentation Model
```python
class Presentation(models.Model):
    customer = ForeignKey(Customer)
    pptx_file = FileField()
    source_language = CharField(max_length=5)
    target_language = CharField(max_length=5)
    status = CharField(choices=STATUS_CHOICES)
    total_texts = IntegerField()
    translated_texts = IntegerField()
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### PresentationText Model
```python
class PresentationText(models.Model):
    presentation = ForeignKey(Presentation)
    slide_number = IntegerField()
    text_id = CharField(max_length=100, unique=True)
    original_text = TextField()
    translated_text = TextField()
    translation_method = CharField(choices=['pending', 'deepl', 'manual', 'error'])
    manually_edited = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### Customer Model
```python
class Customer(models.Model):
    user = ForeignKey(User)
    customer_id = CharField(max_length=50, unique=True)
    customer_name = CharField(max_length=200)
    dashboard_access = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

---

## 🔧 Handlers

### ExtractTextsHandler
**Purpose**: Extract all text elements from PPTX XML structure

**Input**:
```python
{
    'pptx_file': '/path/to/file.pptx',
    'presentation_id': 1
}
```

**Output**:
```python
{
    'success': True,
    'texts_extracted': 42,
    'texts': [
        {
            'text_id': 'slide_1_text_1',
            'slide_number': 1,
            'original_text': 'Hello World',
            'translated_text': ''
        },
        ...
    ]
}
```

### TranslateTextsHandler
**Purpose**: Orchestrate DeepL API translation with caching

**Input**:
```python
{
    'presentation_id': 1,
    'deepl_api_key': 'your_key'
}
```

**Output**:
```python
{
    'success': True,
    'texts_translated': 42,
    'cached': 10,
    'api_calls': 32
}
```

### RepackagePPTXHandler
**Purpose**: Regenerate PPTX file with translated texts

**Input**:
```python
{
    'pptx_file': '/path/to/original.pptx',
    'output_file': '/path/to/output.pptx',
    'presentation_id': 1,
    'deepl_api_key': 'your_key'
}
```

**Output**:
```python
{
    'success': True,
    'output_file': '/path/to/output.pptx',
    'texts_applied': 42
}
```

---

## 🧪 Testing

### Manual Testing
```bash
# 1. Reset cache and presentation status
python clear_cache_and_reset.py

# 2. Start development server
python manage.py runserver

# 3. Navigate to http://localhost:8000/medtrans/

# 4. Upload test PPTX file

# 5. Run translation pipeline

# 6. Verify output in media/medtrans/output/
```

### Unit Testing (Future)
```bash
# Run medtrans tests
python manage.py test apps.medtrans

# Run with coverage
coverage run --source='apps.medtrans' manage.py test apps.medtrans
coverage report
```

---

## 🐛 Troubleshooting

### DeepL API Issues

**Problem**: "Invalid API Key"
```
Solution: Check .env file, ensure DEEPL_API_KEY is set correctly
Verify: https://www.deepl.com/account/usage
```

**Problem**: "Translation failed"
```
Solution: Check DeepL API quota
Check logs: tail -f logs/django.log
```

### File Upload Issues

**Problem**: "File upload failed"
```
Solution: Check MEDIA_ROOT permissions
Verify: ls -la media/medtrans/presentations/
```

**Problem**: "PPTX extraction failed"
```
Solution: Verify PPTX file is not corrupted
Test: unzip -t file.pptx
```

### Database Issues

**Problem**: "PresentationText not found"
```
Solution: Run migrations
Command: python manage.py migrate medtrans
```

### Edit Not Saving

**Problem**: "Changes not persisting"
```
Solution: Check browser console for errors
Verify: Form uses primary key (text_{{ text.id }})
```

---

## 📊 Performance Tips

### Translation Cache
- Cache stored in: `cache/translation_cache.json`
- Clear cache: Delete file or use `clear_cache_and_reset.py`
- Reduces API calls by ~70% on re-translations

### Batch Processing
- DeepL API limits: 500,000 characters/month (Free)
- Large presentations: Split into smaller batches
- Monitor usage: Check DeepL dashboard

### File Storage
- Use cloud storage (S3) for production
- Implement cleanup job for old translations
- Archive completed projects

---

## 🔐 Security Considerations

### User Access Control
- All views decorated with `@login_required`
- User-scoped queries (customer__user=request.user)
- CSRF protection on all forms

### API Key Management
- Never commit `.env` file
- Use environment variables in production
- Rotate keys regularly

### File Upload Security
- MIME type validation
- File extension whitelist (.pptx only)
- File size limits (adjust in forms.py)

---

## 📝 Future Enhancements

### Planned Features
- [ ] Bulk upload (multiple PPTX files)
- [ ] Translation memory integration
- [ ] Quality assurance scoring
- [ ] Export translations to TMX format
- [ ] API for external integrations
- [ ] Async task queue (Celery)
- [ ] Real-time progress via WebSockets
- [ ] Advanced terminology management

### Performance Improvements
- [ ] Redis cache for translations
- [ ] S3 storage for files
- [ ] CDN for static assets
- [ ] Database query optimization
- [ ] Lazy loading for large lists

---

## 📚 Additional Resources

### DeepL API Documentation
- [DeepL API Docs](https://www.deepl.com/docs-api)
- [Supported Languages](https://www.deepl.com/docs-api/translating-text/)
- [Error Codes](https://www.deepl.com/docs-api/api-access/error-handling/)

### Django Documentation
- [File Uploads](https://docs.djangoproject.com/en/stable/topics/http/file-uploads/)
- [Forms](https://docs.djangoproject.com/en/stable/topics/forms/)
- [Model Relationships](https://docs.djangoproject.com/en/stable/topics/db/models/)

### BF Agent Architecture
- GenAgent Handler System
- HTMX Integration Patterns
- Bootstrap 5 UI Components

---

## 🤝 Support

For issues and questions:
1. Check troubleshooting section above
2. Review Django logs: `logs/django.log`
3. Check DeepL API status
4. Contact development team

---

## 📄 License

This module is part of the BF Agent project.

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-27  
**Status**: Production Ready ✅
