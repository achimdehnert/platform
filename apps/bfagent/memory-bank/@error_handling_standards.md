# Error Handling Standards - Robust Exception Management

## 🎯 ERROR HANDLING PRINCIPLES

### 1. **Exception Hierarchy & Classification**
**Regel**: Verwende spezifische Exception-Typen für verschiedene Fehlerklassen
```python
# ✅ RICHTIG: Custom exception hierarchy
# exceptions.py
class BookFactoryException(Exception):
    """Base exception for BookFactory application"""
    pass

class ValidationError(BookFactoryException):
    """Raised when input validation fails"""
    def __init__(self, message, field=None, code=None):
        super().__init__(message)
        self.field = field
        self.code = code

class AuthorizationError(BookFactoryException):
    """Raised when user lacks required permissions"""
    pass

class ExternalServiceError(BookFactoryException):
    """Raised when external service (OpenAI, etc.) fails"""
    def __init__(self, message, service_name=None, status_code=None):
        super().__init__(message)
        self.service_name = service_name
        self.status_code = status_code

class ContentProcessingError(BookFactoryException):
    """Raised when content processing fails"""
    pass

# Usage in views
from .exceptions import ValidationError, AuthorizationError

def agent_edit_content(request, book_id):
    try:
        # Validation
        if not request.POST.get('content'):
            raise ValidationError("Content is required", field='content', code='required')

        # Authorization
        book = get_object_or_404(Book, id=book_id)
        if book.author != request.user:
            raise AuthorizationError(f"User {request.user.id} cannot edit book {book_id}")

        # Process content...

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'field': e.field,
            'code': e.code
        }, status=400)

    except AuthorizationError as e:
        return JsonResponse({
            'success': False,
            'error': 'Permission denied',
            'details': str(e)
        }, status=403)
```

### 2. **Centralized Error Handling**
**Regel**: Verwende Decorators und Middleware für einheitliches Error Handling
```python
# ✅ RICHTIG: Error handling decorator
# decorators.py
import functools
import logging
import traceback
from django.http import JsonResponse
from .exceptions import BookFactoryException

logger = logging.getLogger(__name__)

def handle_api_errors(func):
    """Decorator for consistent API error handling"""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)

        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e),
                'error_type': 'validation_error',
                'field': getattr(e, 'field', None),
                'code': getattr(e, 'code', None)
            }, status=400)

        except AuthorizationError as e:
            logger.warning(f"Authorization error in {func.__name__}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Permission denied',
                'error_type': 'authorization_error'
            }, status=403)

        except ExternalServiceError as e:
            logger.error(f"External service error in {func.__name__}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'External service temporarily unavailable',
                'error_type': 'service_error',
                'service': getattr(e, 'service_name', 'unknown')
            }, status=503)

        except BookFactoryException as e:
            logger.error(f"Application error in {func.__name__}: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e),
                'error_type': 'application_error'
            }, status=500)

        except Exception as e:
            logger.critical(f"Unexpected error in {func.__name__}: {e}")
            logger.critical(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred',
                'error_type': 'system_error',
                'request_id': getattr(request, 'id', None)
            }, status=500)

    return wrapper

# Usage
@handle_api_errors
@require_http_methods(["POST"])
def agent_edit_content(request, book_id):
    """AI agent-assisted content editing with comprehensive error handling"""
    # Business logic here - exceptions are automatically handled
    pass
```

### 3. **Logging Standards**
**Regel**: Strukturiertes Logging mit verschiedenen Log-Levels
```python
# ✅ RICHTIG: Structured logging configuration
# settings.py
import os

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            'formatter': 'json',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'books': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'agents_ui': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Usage in views
import logging

logger = logging.getLogger(__name__)

def agent_edit_content(request, book_id):
    logger.info(f"Agent edit request for book {book_id} by user {request.user.id}")

    try:
        # Process content
        logger.debug(f"Processing content with agent {selected_agent}")
        result = process_with_ai(content, agent_config)
        logger.info(f"Successfully processed content for book {book_id}")
        return JsonResponse({'success': True, 'result': result})

    except ExternalServiceError as e:
        logger.error(f"OpenAI API failed for book {book_id}: {e}")
        raise

    except Exception as e:
        logger.critical(f"Unexpected error processing book {book_id}: {e}")
        logger.critical(traceback.format_exc())
        raise
```

### 4. **User-Friendly Error Messages**
**Regel**: Zeige technische Details nur in Development, benutzerfreundliche Nachrichten in Production
```python
# ✅ RICHTIG: Environment-aware error messages
# utils.py
from django.conf import settings

def format_error_response(error, request=None):
    """Format error response based on environment"""
    base_response = {
        'success': False,
        'error': str(error),
        'timestamp': timezone.now().isoformat()
    }

    if settings.DEBUG:
        # Development: Show detailed information
        base_response.update({
            'traceback': traceback.format_exc(),
            'request_data': {
                'method': request.method if request else None,
                'path': request.path if request else None,
                'user': request.user.id if request and request.user.is_authenticated else None
            }
        })
    else:
        # Production: Show user-friendly messages
        user_friendly_messages = {
            'ValidationError': 'Please check your input and try again.',
            'AuthorizationError': 'You do not have permission to perform this action.',
            'ExternalServiceError': 'Our AI service is temporarily unavailable. Please try again later.',
            'ContentProcessingError': 'There was an issue processing your content. Please try again.',
        }

        error_type = type(error).__name__
        if error_type in user_friendly_messages:
            base_response['error'] = user_friendly_messages[error_type]
        else:
            base_response['error'] = 'An unexpected error occurred. Please try again.'

    return base_response
```

### 5. **Error Monitoring & Alerting**
**Regel**: Kritische Fehler müssen automatisch gemeldet werden
```python
# ✅ RICHTIG: Error monitoring integration
# monitoring.py
import logging
from django.core.mail import mail_admins
from django.conf import settings

class CriticalErrorHandler(logging.Handler):
    """Custom handler for critical errors"""

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            # Send email to admins
            subject = f"Critical Error in {settings.PROJECT_NAME}"
            message = self.format(record)
            mail_admins(subject, message, fail_silently=True)

            # Log to external monitoring service (e.g., Sentry)
            if hasattr(settings, 'SENTRY_DSN'):
                import sentry_sdk
                sentry_sdk.capture_exception()

# Middleware for request tracking
class ErrorTrackingMiddleware:
    """Middleware to track errors with request context"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add unique request ID
        import uuid
        request.id = str(uuid.uuid4())

        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        logger = logging.getLogger(__name__)
        logger.error(
            f"Unhandled exception in request {getattr(request, 'id', 'unknown')}: {exception}",
            extra={
                'request_id': getattr(request, 'id', None),
                'user_id': request.user.id if request.user.is_authenticated else None,
                'path': request.path,
                'method': request.method,
            }
        )
        return None
```

## 🔧 ERROR HANDLING PATTERNS

### API Error Responses
```python
# ✅ RICHTIG: Consistent API error format
def standardized_error_response(error_type, message, status_code, **kwargs):
    """Generate standardized error response"""
    response_data = {
        'success': False,
        'error': {
            'type': error_type,
            'message': message,
            'code': status_code,
            'timestamp': timezone.now().isoformat()
        }
    }

    # Add additional context
    response_data['error'].update(kwargs)

    return JsonResponse(response_data, status=status_code)

# Usage examples
return standardized_error_response(
    'validation_error',
    'Missing required parameters',
    400,
    missing_fields=['content', 'agent_type']
)

return standardized_error_response(
    'authorization_error',
    'Insufficient permissions',
    403,
    required_permission='books.change_book'
)
```

### Database Error Handling
```python
# ✅ RICHTIG: Database transaction error handling
from django.db import transaction, IntegrityError

def create_book_with_chapters(book_data, chapters_data):
    """Create book with chapters in atomic transaction"""
    try:
        with transaction.atomic():
            book = Book.objects.create(**book_data)

            for chapter_data in chapters_data:
                Chapter.objects.create(book=book, **chapter_data)

            logger.info(f"Successfully created book {book.id} with {len(chapters_data)} chapters")
            return book

    except IntegrityError as e:
        logger.error(f"Database integrity error creating book: {e}")
        raise ValidationError("Book with this title already exists")

    except Exception as e:
        logger.error(f"Unexpected error creating book: {e}")
        raise ContentProcessingError("Failed to create book and chapters")
```

## 📋 ERROR HANDLING CHECKLIST

### Exception Management:
- [ ] Custom exception hierarchy defined
- [ ] Specific exceptions for different error types
- [ ] Consistent exception handling across views
- [ ] Proper exception chaining and context

### Logging:
- [ ] Structured logging configuration
- [ ] Appropriate log levels used
- [ ] Sensitive data excluded from logs
- [ ] Log rotation and retention configured

### User Experience:
- [ ] User-friendly error messages in production
- [ ] Detailed error info in development
- [ ] Consistent error response format
- [ ] Graceful degradation for service failures

### Monitoring:
- [ ] Critical errors automatically reported
- [ ] Error tracking with request context
- [ ] Performance impact monitoring
- [ ] Error rate alerting configured

## 🚨 CURRENT APPLICATION ERROR GAPS

### Identified Issues:
1. **Inconsistent error responses** across different views
2. **Missing error logging** in critical paths
3. **Generic exception handling** without proper classification
4. **No monitoring** for external service failures

### Immediate Actions Required:
1. Implement custom exception hierarchy
2. Add error handling decorators to all API views
3. Configure structured logging
4. Set up error monitoring and alerting
