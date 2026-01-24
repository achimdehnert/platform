# Security Standards - Django Application Security

## 🛡️ CORE SECURITY PRINCIPLES

### 1. **Input Validation & Sanitization**
**Regel**: ALLE User-Inputs MÜSSEN validiert und sanitized werden
```python
# ✅ RICHTIG: Comprehensive Input Validation
def secure_view(request):
    # 1. Parameter Validation
    required_params = ['content', 'agent_type']
    for param in required_params:
        value = request.POST.get(param, '').strip()
        if not value:
            return JsonResponse({'error': f'Missing {param}'}, status=400)

    # 2. Content Sanitization
    from django.utils.html import escape
    content = escape(request.POST.get('content'))

    # 3. Length Validation
    if len(content) > 10000:
        return JsonResponse({'error': 'Content too long'}, status=400)

    # 4. Type Validation
    agent_type = request.POST.get('agent_type')
    if agent_type not in ALLOWED_AGENT_TYPES:
        return JsonResponse({'error': 'Invalid agent type'}, status=400)

# ❌ FALSCH: Keine Validation
def insecure_view(request):
    content = request.POST.get('content')  # Unvalidated!
    # Direct database insertion - SQL Injection risk!
```

### 2. **CSRF Protection**
**Regel**: Alle POST/PUT/DELETE Requests MÜSSEN CSRF-geschützt sein
```python
# ✅ RICHTIG: CSRF Protection
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token

@csrf_protect
@require_http_methods(["POST"])
def secure_post_view(request):
    # CSRF token automatically validated by decorator
    pass

# Template: CSRF Token in Forms
# {% csrf_token %}
<form method="post">
    {% csrf_token %}
    <input type="text" name="content">
    <button type="submit">Submit</button>
</form>

# HTMX: CSRF Token in Headers
<script>
document.addEventListener('DOMContentLoaded', function() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    htmx.config.requestHeaders = {'X-CSRFToken': csrfToken};
});
</script>
```

### 3. **XSS Prevention**
**Regel**: Alle User-Generated Content MUSS escaped werden
```python
# ✅ RICHTIG: Auto-escaping in Templates
# settings.py
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [...],
        'autoescape': True,  # ← CRITICAL!
    },
}]

# Template: Safe rendering
{{ user_content|escape }}  # Always escape
{{ trusted_html|safe }}    # Only for trusted content

# Python: Manual escaping
from django.utils.html import escape, format_html
safe_content = escape(user_input)
html_output = format_html('<div>{}</div>', safe_content)
```

### 4. **SQL Injection Prevention**
**Regel**: NIEMALS raw SQL mit User-Input, immer ORM oder Parameterized Queries
```python
# ✅ RICHTIG: Django ORM (Auto-escaped)
books = Book.objects.filter(title__icontains=user_search)
chapters = Chapter.objects.filter(book_id=book_id, status='published')

# ✅ RICHTIG: Parameterized Raw SQL (wenn nötig)
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM books WHERE title LIKE %s", [f"%{user_search}%"])

# ❌ FALSCH: String Concatenation (SQL Injection!)
query = f"SELECT * FROM books WHERE title LIKE '%{user_search}%'"
cursor.execute(query)  # NEVER DO THIS!
```

### 5. **Authentication & Authorization**
**Regel**: Sensitive Operations erfordern Authentication + Authorization
```python
# ✅ RICHTIG: Authentication Required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

@login_required
def edit_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # Authorization Check
    if book.author != request.user:
        raise PermissionDenied("You can only edit your own books")

    # Proceed with edit logic...

# ✅ RICHTIG: Permission-based Authorization
from django.contrib.auth.decorators import permission_required

@permission_required('books.change_book')
def admin_edit_book(request, book_id):
    # Only users with 'change_book' permission can access
```

### 6. **Environment Variable Security**
**Regel**: Sensitive Data NIEMALS im Code, immer in Environment Variables
```python
# ✅ RICHTIG: Environment Variables
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DATABASE_PASSWORD = os.getenv('DB_PASSWORD')

# .env (NEVER commit to git!)
DJANGO_SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=sk-your-openai-key
DB_PASSWORD=your-db-password

# ❌ FALSCH: Hardcoded Secrets
SECRET_KEY = 'hardcoded-secret-key'  # NEVER!
OPENAI_API_KEY = 'sk-hardcoded-key'  # NEVER!
```

## 🔒 SECURITY HEADERS

### Required Security Headers
```python
# settings.py - Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # Minimize unsafe-inline
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
```

## 🚨 SECURITY CHECKLIST

### Before Deployment:
- [ ] All user inputs validated and sanitized
- [ ] CSRF protection on all state-changing operations
- [ ] XSS prevention (auto-escaping enabled)
- [ ] SQL injection prevention (ORM only, no raw SQL)
- [ ] Authentication required for sensitive operations
- [ ] Authorization checks implemented
- [ ] Environment variables for all secrets
- [ ] Security headers configured
- [ ] HTTPS enforced in production
- [ ] Debug mode disabled in production

### Regular Security Audits:
- [ ] Review all user input handling
- [ ] Check for hardcoded secrets
- [ ] Validate permission checks
- [ ] Test for common vulnerabilities
- [ ] Update dependencies regularly
- [ ] Monitor security logs

## 🎯 CURRENT APPLICATION SECURITY GAPS

### Identified Issues:
1. **Missing CSRF validation** in some HTMX requests
2. **Insufficient input validation** in agent_edit_content
3. **Potential XSS** in AI-generated content display
4. **Missing authorization checks** in some views

### Immediate Actions Required:
1. Add CSRF tokens to all HTMX requests
2. Implement comprehensive input validation
3. Escape all AI-generated content before display
4. Add permission checks to sensitive operations
