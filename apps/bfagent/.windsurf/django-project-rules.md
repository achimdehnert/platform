# Django Professional Project - Development Rules

## 🎯 Project Overview

### Core Mission
- **Professional Django Development**: Enterprise-grade web application development
- **SQLite Database Integration**: Working with existing SQLite databases
- **Modern Django Practices**: Following Django 4.x+ best practices
- **Windsurf Integration**: Optimized for Windsurf development environment
- **Memory Bank Persistence**: Cross-session continuity and context preservation

## 🏗️ Django Architecture Overview

### Project Structure
```text
django_project/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env                     # Environment variables
├── config/                  # Project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py         # Base settings
│   │   ├── development.py  # Development settings
│   │   ├── production.py   # Production settings
│   │   └── testing.py      # Testing settings
│   ├── urls.py             # Root URL configuration
│   ├── wsgi.py             # WSGI configuration
│   └── asgi.py             # ASGI configuration
├── apps/                    # Django applications
│   ├── core/               # Core functionality
│   ├── users/              # User management
│   ├── api/                # API endpoints
│   └── common/             # Shared utilities
├── static/                 # Static files
├── media/                  # Media files
├── templates/              # HTML templates
├── locale/                 # Internationalization
├── tests/                  # Test files
├── docs/                   # Documentation
└── db.sqlite3              # SQLite database
```

### Key Components
- **Django 4.x+**: Latest stable Django version
- **SQLite Database**: Existing database integration
- **Django REST Framework**: API development
- **Django Admin**: Administrative interface
- **Class-Based Views**: Modern view patterns
- **Model-View-Template**: Django MVC pattern

## 🤖 AI Agent Instructions

### Context Priority
1. **Django Best Practices**: Follow Django conventions and patterns
2. **Database Integration**: Respect existing SQLite schema
3. **Memory Bank**: Utilize persistent memory for cross-session continuity
4. **User Intent**: Focus on professional web application development
5. **Technical Stack**: Django, SQLite, DRF, HTML/CSS/JS

### Agent Behavior Guidelines

#### Django Development Standards
- **Models**: Use Django ORM with proper field types and relationships
- **Views**: Prefer class-based views with mixins
- **Templates**: Use Django template language with proper inheritance
- **Forms**: Django forms with validation and error handling
- **URLs**: RESTful URL patterns with namespacing
- **Admin**: Customize Django admin for data management

#### Database Integration
- **Existing SQLite**: Inspect and integrate with existing database
- **Migrations**: Create proper Django migrations
- **Model Introspection**: Use `inspectdb` for existing tables
- **Data Integrity**: Maintain referential integrity
- **Backup Strategy**: Implement database backup procedures

### Code Standards
- **Python 3.11+**: Primary development language
- **Type Hints**: All functions must include type annotations
- **Django Models**: Proper model definitions with Meta classes
- **Error Handling**: Comprehensive exception management
- **Documentation**: Google-style docstrings
- **Testing**: Minimum 80% test coverage with Django TestCase

## 📚 Development Workflow

### Django Setup Process
1. **Project Initialization**: `django-admin startproject`
2. **App Creation**: `python manage.py startapp`
3. **Database Integration**: Inspect existing SQLite database
4. **Model Generation**: Create Django models from existing schema
5. **Migration Creation**: Generate and apply migrations
6. **Admin Configuration**: Set up Django admin interface
7. **URL Configuration**: Define URL patterns
8. **View Implementation**: Create views and templates
9. **Testing**: Write comprehensive tests

### Database Integration Workflow
1. **Database Inspection**: Analyze existing SQLite schema
2. **Model Introspection**: Use `python manage.py inspectdb`
3. **Model Refinement**: Clean up generated models
4. **Migration Strategy**: Plan migration approach
5. **Data Migration**: Handle existing data
6. **Validation**: Ensure data integrity

## 🧠 Memory Bank Optimization

### Structure
```text
memory-bank/
├── @django-project-context.md    # Core Django project information
├── @database-schema.md           # SQLite database schema
├── @api-endpoints.md             # API documentation
├── @model-relationships.md       # Django model relationships
├── @deployment-config.md         # Deployment configuration
├── django-apps/                  # Individual app contexts
├── database-migrations/          # Migration history
├── api-documentation/            # API specs and docs
└── testing-strategies/           # Test patterns and data
```

### Performance Guidelines
- **File Size Limit**: Maximum 10KB per memory file
- **Lazy Loading**: Load memory content on demand
- **Database Caching**: Cache database queries appropriately
- **Static Files**: Optimize static file serving
- **Template Caching**: Cache compiled templates

## 🚀 Development Guidelines

### Windsurf Integration
- **Config**: Use `.windsurf/config.json` for Django environment setup
- **Serve Mode**: Optimize for Django development server
- **Memory Bank**: Leverage Windsurf's persistent memory features
- **Database Tools**: Integrate database inspection tools

### Django Best Practices
- **Settings Management**: Environment-based settings
- **Security**: Proper security configurations
- **Performance**: Database query optimization
- **Scalability**: Prepare for horizontal scaling
- **Maintainability**: Clean, readable code structure

## 🔧 Technical Requirements

### Dependencies
```text
Core Framework:
- Django>=4.2.0
- djangorestframework>=3.14.0
- django-environ>=0.10.0
- django-cors-headers>=4.0.0

Database:
- sqlite3 (built-in)
- django-extensions>=3.2.0

Development:
- python>=3.11
- pip-tools (dependency management)
- pytest-django (testing)
- black (formatting)
- mypy (type checking)
- flake8 (linting)

Optional:
- celery (task queue)
- redis (caching)
- gunicorn (WSGI server)
```

### Environment Variables
```bash
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Windsurf Integration
WINDSURF_MEMORY_BANK_PATH=./memory-bank
WINDSURF_PROJECT_PATH=./
```

### Startup Commands
```bash
# Quick start
python manage.py runserver 8000

# Development setup
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runserver
```

## 📋 Quality Standards

### Django Code Quality
- **Models**: Proper field types, relationships, and Meta options
- **Views**: Class-based views with proper mixins
- **Templates**: DRY template inheritance
- **Forms**: Proper validation and error handling
- **URLs**: RESTful patterns with proper namespacing

### Testing Strategy
- **Unit Tests**: Test models, views, and forms
- **Integration Tests**: Test complete workflows
- **API Tests**: Test REST API endpoints
- **Database Tests**: Test model relationships and queries

### Security Considerations
- **CSRF Protection**: Enabled by default
- **SQL Injection**: Use Django ORM properly
- **XSS Protection**: Template auto-escaping
- **Authentication**: Proper user authentication
- **Authorization**: Permission-based access control

## 🎯 Success Metrics

### Development KPIs
- **Code Coverage**: Minimum 80%
- **Response Time**: <200ms for typical requests
- **Database Queries**: Optimized N+1 query prevention
- **Error Rate**: <1% for application errors

### Django Specific Metrics
- **Migration Success**: 100% successful migrations
- **Admin Interface**: Fully functional admin
- **API Performance**: <100ms API response times
- **Template Rendering**: <50ms template rendering

---

**Note**: This file defines Django-specific development rules for professional web application development with SQLite database integration.
