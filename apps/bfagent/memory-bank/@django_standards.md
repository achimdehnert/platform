# Django Standards - Best Practices & Patterns

## 🎯 DJANGO CORE PRINCIPLES

### 1. **Model Design Patterns**
**Regel**: Models sind die Single Source of Truth für Datenstruktur
```python
# ✅ RICHTIG: Well-structured Model
class Book(models.Model):
    """Book model with proper field types and constraints"""
    title = models.CharField(max_length=200, db_index=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='books')
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('review', 'Under Review'),
            ('published', 'Published'),
        ],
        default='draft',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', 'status']),
            models.Index(fields=['genre', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author.username}"

    def get_absolute_url(self):
        return reverse('book_detail', kwargs={'pk': self.pk})

    @property
    def is_published(self):
        return self.status == 'published'

# ❌ FALSCH: Poor Model Design
class BadBook(models.Model):
    title = models.TextField()  # Should be CharField with max_length
    author_name = models.CharField(max_length=100)  # Should be ForeignKey
    data = models.JSONField()  # Avoid generic data fields
    # Missing created_at, updated_at, proper indexes
```

### 2. **View Organization & Patterns**
**Regel**: Views sind dünn, Business Logic in Models/Services
```python
# ✅ RICHTIG: Class-Based Views with proper structure
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

class BookListView(LoginRequiredMixin, ListView):
    """List user's books with filtering and pagination"""
    model = Book
    template_name = 'books/book_list.html'
    context_object_name = 'books'
    paginate_by = 20

    def get_queryset(self):
        return Book.objects.filter(author=self.request.user).select_related('genre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_books'] = self.get_queryset().count()
        return context

class BookDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Book detail with permission checking"""
    model = Book
    template_name = 'books/book_detail.html'

    def test_func(self):
        book = self.get_object()
        return book.author == self.request.user or self.request.user.is_staff

# ✅ RICHTIG: Function-Based View with proper structure
@login_required
@require_http_methods(["POST"])
def create_chapter(request, book_id):
    """Create new chapter with validation"""
    book = get_object_or_404(Book, id=book_id, author=request.user)

    # Parameter validation (following @parameter_validation_rules.md)
    required_params = ['title', 'content']
    missing_params = []
    for param in required_params:
        if not request.POST.get(param, '').strip():
            missing_params.append(param)

    if missing_params:
        return JsonResponse({
            'success': False,
            'error': f'Missing required parameters: {", ".join(missing_params)}'
        }, status=400)

    # Business logic
    chapter = Chapter.objects.create(
        book=book,
        title=request.POST['title'].strip(),
        content=request.POST['content'].strip(),
        order=book.chapters.count() + 1
    )

    return JsonResponse({
        'success': True,
        'chapter_id': chapter.id,
        'redirect_url': chapter.get_absolute_url()
    })
```

### 3. **URL Naming Conventions**
**Regel**: URLs sind RESTful und aussagekräftig benannt
```python
# ✅ RICHTIG: RESTful URL patterns
# urls.py
from django.urls import path, include

app_name = 'books'

urlpatterns = [
    # Book URLs
    path('', BookListView.as_view(), name='book_list'),
    path('create/', BookCreateView.as_view(), name='book_create'),
    path('<int:pk>/', BookDetailView.as_view(), name='book_detail'),
    path('<int:pk>/edit/', BookUpdateView.as_view(), name='book_edit'),
    path('<int:pk>/delete/', BookDeleteView.as_view(), name='book_delete'),

    # Chapter URLs (nested under book)
    path('<int:book_id>/chapters/', ChapterListView.as_view(), name='chapter_list'),
    path('<int:book_id>/chapters/create/', create_chapter, name='chapter_create'),
    path('<int:book_id>/chapters/<int:pk>/', ChapterDetailView.as_view(), name='chapter_detail'),

    # Agent URLs (nested under book)
    path('<int:book_id>/agents/', include('agents_ui.urls')),
]

# ❌ FALSCH: Poor URL structure
urlpatterns = [
    path('book_list/', BookListView.as_view()),  # No name
    path('book/<int:id>/', BookDetailView.as_view()),  # Use pk, not id
    path('edit_book/<int:pk>/', BookUpdateView.as_view()),  # Inconsistent naming
    path('agents/<int:book_id>/<str:action>/', agent_view),  # Too generic
]
```

### 4. **Template Structure & Organization**
**Regel**: Templates sind modular und wiederverwendbar
```html
<!-- ✅ RICHTIG: Structured template hierarchy -->
<!-- base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="csrf-token" content="{{ csrf_token }}">
    <title>{% block title %}BookFactory{% endblock %}</title>
    {% load static %}
    <link rel="stylesheet" href="{% static 'css/base.css' %}">
</head>
<body>
    <nav>{% include 'partials/navigation.html' %}</nav>

    <main>
        {% if messages %}
            {% include 'partials/messages.html' %}
        {% endif %}

        {% block content %}{% endblock %}
    </main>

    <footer>{% include 'partials/footer.html' %}</footer>

    {% block scripts %}{% endblock %}
</body>
</html>

<!-- books/book_detail.html -->
{% extends 'base.html' %}
{% load book_tags %}

{% block title %}{{ book.title }} - BookFactory{% endblock %}

{% block content %}
<div class="book-detail">
    <header class="book-header">
        <h1>{{ book.title|escape }}</h1>
        <p class="book-meta">
            by {{ book.author.get_full_name|default:book.author.username }}
            | {{ book.created_at|date:"M d, Y" }}
        </p>
    </header>

    {% include 'books/partials/book_actions.html' %}
    {% include 'chapters/partials/chapter_list.html' %}
</div>
{% endblock %}
```

### 5. **Settings Management**
**Regel**: Settings sind umgebungsbasiert und sicher konfiguriert
```python
# ✅ RICHTIG: Environment-based settings structure
# settings/base.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# settings/development.py
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Development-specific settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# settings/production.py
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS').split(',')

# Production security settings
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### 6. **Migration Best Practices**
**Regel**: Migrations sind atomic und rückwärts kompatibel
```python
# ✅ RICHTIG: Safe migration with data migration
from django.db import migrations, models

def populate_book_slugs(apps, schema_editor):
    """Data migration to populate slug field"""
    Book = apps.get_model('books', 'Book')
    for book in Book.objects.all():
        book.slug = book.title.lower().replace(' ', '-')
        book.save()

def reverse_populate_book_slugs(apps, schema_editor):
    """Reverse data migration"""
    pass  # Slugs can be left as-is

class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ('books', '0001_initial'),
    ]

    operations = [
        # 1. Add field (nullable first)
        migrations.AddField(
            model_name='book',
            name='slug',
            field=models.SlugField(max_length=200, null=True, blank=True),
        ),
        # 2. Populate data
        migrations.RunPython(
            populate_book_slugs,
            reverse_populate_book_slugs,
        ),
        # 3. Make field non-nullable
        migrations.AlterField(
            model_name='book',
            name='slug',
            field=models.SlugField(max_length=200, unique=True),
        ),
    ]
```

## 🔧 DJANGO PERFORMANCE PATTERNS

### Database Optimization
```python
# ✅ RICHTIG: Optimized queries
# Use select_related for ForeignKey
books = Book.objects.select_related('author', 'genre').all()

# Use prefetch_related for ManyToMany/reverse ForeignKey
books = Book.objects.prefetch_related('chapters', 'tags').all()

# Avoid N+1 queries
chapters = Chapter.objects.select_related('book__author').all()

# Use only() and defer() for large models
books = Book.objects.only('title', 'author__username').all()
```

### Caching Strategies
```python
# ✅ RICHTIG: Strategic caching
from django.core.cache import cache
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def book_list_public(request):
    return render(request, 'books/public_list.html')

# Model-level caching
class Book(models.Model):
    def get_chapter_count(self):
        cache_key = f'book_{self.id}_chapter_count'
        count = cache.get(cache_key)
        if count is None:
            count = self.chapters.count()
            cache.set(cache_key, count, 60 * 30)  # 30 minutes
        return count
```

## 📋 DJANGO CHECKLIST

### Model Design:
- [ ] Proper field types and constraints
- [ ] Database indexes on frequently queried fields
- [ ] Proper relationships (ForeignKey, ManyToMany)
- [ ] Meta options (ordering, indexes)
- [ ] __str__ and get_absolute_url methods

### View Design:
- [ ] Proper authentication and authorization
- [ ] Parameter validation
- [ ] Efficient database queries
- [ ] Proper error handling
- [ ] Clear separation of concerns

### URL Design:
- [ ] RESTful URL patterns
- [ ] Named URL patterns
- [ ] Proper namespacing
- [ ] Consistent parameter naming

### Template Design:
- [ ] Template inheritance
- [ ] Proper escaping of user content
- [ ] Modular template structure
- [ ] Custom template tags where appropriate

### Settings:
- [ ] Environment-based configuration
- [ ] Secure settings for production
- [ ] Proper static/media file handling
- [ ] Database optimization settings
