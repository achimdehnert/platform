# @django-project-context.md - Django Professional Project Context

## 🎯 Project Overview

### Core Mission
Professional Django web application development with existing SQLite database integration, optimized for Windsurf development environment with comprehensive memory bank persistence.

### Technical Stack

- **Django 4.x+**: Latest stable Django framework
- **SQLite Database**: Existing database integration and management
- **Django REST Framework**: RESTful API development
- **Python 3.11+**: Modern Python with type hints
- **Windsurf IDE**: Optimized development environment
- **Memory Bank**: Persistent context and session management

## 🏗️ Project Architecture

### Django Project Structure

```text
django_project/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env                     # Environment variables
├── config/                  # Project configuration
│   ├── settings/            # Environment-based settings
│   ├── urls.py             # Root URL configuration
│   ├── wsgi.py & asgi.py   # Server configurations
├── apps/                    # Django applications
│   ├── core/               # Core functionality
│   ├── users/              # User management
│   ├── api/                # API endpoints
│   └── common/             # Shared utilities
├── static/                 # Static files (CSS, JS, images)
├── media/                  # User-uploaded media
├── templates/              # HTML templates
├── tests/                  # Test files
└── db.sqlite3              # SQLite database
```

### Key Components

#### 1. Database Integration
- **Existing SQLite**: Work with pre-existing database schema
- **Model Introspection**: Use `python manage.py inspectdb` for model generation
- **Migration Strategy**: Careful migration planning for existing data
- **Data Integrity**: Maintain referential integrity during development

#### 2. Django Applications
- **Core App**: Essential functionality and base models
- **Users App**: Authentication and user management
- **API App**: REST API endpoints with Django REST Framework
- **Common App**: Shared utilities, mixins, and base classes

#### 3. Development Workflow
- **Settings Management**: Environment-based configuration
- **URL Patterns**: RESTful routing with proper namespacing
- **Class-Based Views**: Modern Django view patterns
- **Template Inheritance**: DRY template structure
- **Form Handling**: Proper validation and error handling

## 🔧 Development Guidelines

### Django Best Practices

#### Models
- Use proper field types and relationships
- Implement `__str__` methods for all models
- Add Meta classes with appropriate options
- Use model managers for complex queries
- Implement custom validation methods

#### Views
- Prefer class-based views with mixins
- Use generic views where appropriate
- Implement proper permission checking
- Handle exceptions gracefully
- Use pagination for list views

#### Templates
- Follow Django template inheritance patterns
- Use template tags and filters appropriately
- Implement responsive design
- Optimize for performance and accessibility

#### Forms
- Use Django forms for data validation
- Implement custom form validation
- Handle form errors properly
- Use crispy forms for better styling

### Database Management

#### SQLite Integration
- Analyze existing schema before model creation
- Use database inspection tools
- Plan migration strategy carefully
- Backup database before major changes
- Test migrations on development copy

#### Performance Optimization
- Use select_related() and prefetch_related()
- Implement database indexing
- Optimize query patterns
- Use database connection pooling
- Monitor query performance

## 🧠 Memory Bank Integration

### Context Storage

```text
memory-bank/
├── @django-project-context.md    # This file - core project info
├── @database-schema.md           # SQLite database schema documentation
├── @api-endpoints.md             # REST API documentation
├── @model-relationships.md       # Django model relationships
├── @deployment-config.md         # Deployment and configuration
├── django-apps/                  # Individual app contexts
├── database-migrations/          # Migration history and notes
├── api-documentation/            # API specs and examples
└── testing-strategies/           # Test patterns and data
```

### Session Continuity
- Preserve development context across Windsurf sessions
- Track model changes and migration history
- Maintain API endpoint documentation
- Store testing data and scenarios

## 🚀 Development Workflow

### Initial Setup Process

1. **Project Analysis**: Examine existing SQLite database
2. **Django Initialization**: Create Django project structure
3. **Database Integration**: Generate models from existing schema
4. **App Creation**: Set up Django applications
5. **URL Configuration**: Define routing patterns
6. **View Implementation**: Create views and templates
7. **API Development**: Implement REST API endpoints
8. **Testing**: Write comprehensive tests
9. **Documentation**: Update memory bank with progress

### Database Integration Steps

1. **Schema Analysis**: `sqlite3 db.sqlite3 .schema`
2. **Model Generation**: `python manage.py inspectdb > models.py`
3. **Model Refinement**: Clean up generated models
4. **Initial Migration**: `python manage.py makemigrations`
5. **Migration Application**: `python manage.py migrate`
6. **Data Validation**: Verify data integrity

## 📋 Quality Standards

### Code Quality
- **Type Hints**: All functions include type annotations
- **Documentation**: Google-style docstrings
- **Testing**: Minimum 80% test coverage
- **Linting**: Use flake8, black, and mypy
- **Security**: Follow Django security best practices

### Performance Metrics
- **Response Time**: <200ms for typical requests
- **Database Queries**: Optimized to prevent N+1 queries
- **Template Rendering**: <50ms for template rendering
- **API Performance**: <100ms for API endpoints

### Security Considerations
- **CSRF Protection**: Enabled by default
- **SQL Injection**: Use Django ORM properly
- **XSS Protection**: Template auto-escaping enabled
- **Authentication**: Proper user authentication system
- **Authorization**: Permission-based access control

## 🎯 Success Criteria

### Technical Goals
- ✅ Professional Django project structure
- ✅ Successful SQLite database integration
- ✅ Functional Django admin interface
- ✅ REST API with proper documentation
- ✅ Comprehensive test suite
- ✅ Production-ready configuration

### Development Goals
- ✅ Windsurf IDE optimization
- ✅ Memory bank integration
- ✅ Cross-session context preservation
- ✅ Automated development workflow
- ✅ Documentation and knowledge base

---

*This context file is automatically updated as the Django project evolves*
*Current Focus: Professional Django setup with SQLite integration*
