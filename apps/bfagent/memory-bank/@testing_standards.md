# Testing Standards - Comprehensive Test Strategy

## 🎯 TESTING PRINCIPLES

### 1. **Test Coverage Requirements**
**Regel**: Minimum 80% Code Coverage für alle kritischen Komponenten
```python
# ✅ RICHTIG: Comprehensive test coverage
# tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from books.models import Book, Chapter

class BookModelTest(TestCase):
    """Test Book model functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.book = Book.objects.create(
            title='Test Book',
            author=self.user,
            status='draft'
        )

    def test_book_creation(self):
        """Test book creation with valid data"""
        self.assertEqual(self.book.title, 'Test Book')
        self.assertEqual(self.book.author, self.user)
        self.assertEqual(self.book.status, 'draft')
        self.assertTrue(self.book.created_at)

    def test_book_str_representation(self):
        """Test book string representation"""
        expected = f"{self.book.title} by {self.user.username}"
        self.assertEqual(str(self.book), expected)

    def test_book_absolute_url(self):
        """Test book absolute URL generation"""
        expected_url = f'/books/{self.book.pk}/'
        self.assertEqual(self.book.get_absolute_url(), expected_url)

    def test_is_published_property(self):
        """Test is_published property"""
        self.assertFalse(self.book.is_published)

        self.book.status = 'published'
        self.book.save()
        self.assertTrue(self.book.is_published)
```

### 2. **Test Naming Conventions**
**Regel**: Test-Namen beschreiben das erwartete Verhalten
```python
# ✅ RICHTIG: Descriptive test names
class AgentEditContentTest(TestCase):
    """Test agent content editing functionality"""

    def test_should_edit_content_when_valid_parameters_provided(self):
        """Agent should successfully edit content with valid parameters"""
        pass

    def test_should_return_400_when_missing_required_parameters(self):
        """Agent should return 400 error when required parameters are missing"""
        pass

    def test_should_return_403_when_user_not_authorized(self):
        """Agent should return 403 error when user lacks permissions"""
        pass

    def test_should_sanitize_content_before_processing(self):
        """Agent should sanitize user input before AI processing"""
        pass

# ❌ FALSCH: Generic test names
class BadTest(TestCase):
    def test_agent(self):  # What about the agent?
        pass

    def test_edit(self):  # What kind of edit?
        pass

    def test_error(self):  # What error condition?
        pass
```

### 3. **Test Data Management**
**Regel**: Verwende Fixtures und Factory Pattern für konsistente Test-Daten
```python
# ✅ RICHTIG: Factory pattern for test data
# tests/factories.py
import factory
from django.contrib.auth.models import User
from books.models import Book, Chapter

class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating test users"""
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

class BookFactory(factory.django.DjangoModelFactory):
    """Factory for creating test books"""
    class Meta:
        model = Book

    title = factory.Faker('sentence', nb_words=3)
    author = factory.SubFactory(UserFactory)
    status = 'draft'
    genre = factory.SubFactory('tests.factories.GenreFactory')

class ChapterFactory(factory.django.DjangoModelFactory):
    """Factory for creating test chapters"""
    class Meta:
        model = Chapter

    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text', max_nb_chars=1000)
    book = factory.SubFactory(BookFactory)
    order = factory.Sequence(lambda n: n)

# Usage in tests
class BookViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.book = BookFactory(author=self.user)
        self.chapters = ChapterFactory.create_batch(3, book=self.book)
```

### 4. **Mocking & External Dependencies**
**Regel**: Alle externen APIs und Services müssen gemockt werden
```python
# ✅ RICHTIG: Proper mocking of external services
from unittest.mock import patch, Mock
from django.test import TestCase
from agents_ui.views import agent_edit_content

class AgentEditContentTest(TestCase):
    """Test agent content editing with mocked OpenAI API"""

    def setUp(self):
        self.user = UserFactory()
        self.book = BookFactory(author=self.user)
        self.client.force_login(self.user)

    @patch('agents_ui.views.openai.ChatCompletion.create')
    def test_should_process_content_with_openai_api(self, mock_openai):
        """Test successful content processing with OpenAI API"""
        # Arrange
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Improved content here"
        mock_openai.return_value = mock_response

        # Act
        response = self.client.post(f'/books/{self.book.id}/agents/edit/', {
            'key': 'test_key',
            'selected_agent': 'writer',
            'instructions': 'Improve the writing style',
            'current_content': 'Original content'
        })

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Improved content', data['edited_content'])

        # Verify API was called correctly
        mock_openai.assert_called_once()
        call_args = mock_openai.call_args
        self.assertIn('Improve the writing style', str(call_args))

    @patch('agents_ui.views.openai.ChatCompletion.create')
    def test_should_handle_openai_api_error_gracefully(self, mock_openai):
        """Test graceful handling of OpenAI API errors"""
        # Arrange
        mock_openai.side_effect = Exception("API Error")

        # Act
        response = self.client.post(f'/books/{self.book.id}/agents/edit/', {
            'key': 'test_key',
            'selected_agent': 'writer',
            'instructions': 'Improve the writing style',
            'current_content': 'Original content'
        })

        # Assert
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('API Error', data['error'])
```

### 5. **Integration Testing**
**Regel**: Kritische User Journeys müssen als Integration Tests abgedeckt sein
```python
# ✅ RICHTIG: End-to-end integration test
from django.test import TransactionTestCase
from django.test.utils import override_settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@override_settings(DEBUG=True)
class BookCreationIntegrationTest(TransactionTestCase):
    """Integration test for complete book creation workflow"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = webdriver.Chrome()  # Or Firefox()
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        self.user = UserFactory()

    def test_complete_book_creation_workflow(self):
        """Test complete book creation from login to first chapter"""
        # 1. Login
        self.selenium.get(f'{self.live_server_url}/login/')
        username_input = self.selenium.find_element(By.NAME, "username")
        password_input = self.selenium.find_element(By.NAME, "password")
        username_input.send_keys(self.user.username)
        password_input.send_keys('testpass123')
        self.selenium.find_element(By.XPATH, '//button[@type="submit"]').click()

        # 2. Create new book
        self.selenium.get(f'{self.live_server_url}/books/create/')
        title_input = self.selenium.find_element(By.NAME, "title")
        title_input.send_keys("My Test Book")
        self.selenium.find_element(By.XPATH, '//button[@type="submit"]').click()

        # 3. Verify book was created
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "book-detail"))
        )

        # 4. Create first chapter
        create_chapter_btn = self.selenium.find_element(By.ID, "create-chapter-btn")
        create_chapter_btn.click()

        chapter_title = self.selenium.find_element(By.NAME, "title")
        chapter_content = self.selenium.find_element(By.NAME, "content")
        chapter_title.send_keys("Chapter 1: Introduction")
        chapter_content.send_keys("This is the first chapter content.")

        self.selenium.find_element(By.XPATH, '//button[@type="submit"]').click()

        # 5. Verify chapter was created
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "chapter-item"))
        )

        chapter_element = self.selenium.find_element(By.CLASS_NAME, "chapter-item")
        self.assertIn("Chapter 1: Introduction", chapter_element.text)
```

## 🔧 TEST ORGANIZATION

### Directory Structure
```
tests/
├── __init__.py
├── factories.py          # Test data factories
├── fixtures/             # JSON fixtures
│   ├── users.json
│   └── books.json
├── unit/                 # Unit tests
│   ├── test_models.py
│   ├── test_views.py
│   └── test_utils.py
├── integration/          # Integration tests
│   ├── test_workflows.py
│   └── test_api.py
└── selenium/             # Browser tests
    ├── test_user_journey.py
    └── test_admin_workflow.py
```

### Test Configuration
```python
# settings/test.py
from .base import *

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Faster for tests
]

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously
```

## 📋 TESTING CHECKLIST

### Unit Tests:
- [ ] All models tested (creation, validation, methods)
- [ ] All views tested (GET, POST, permissions)
- [ ] All utility functions tested
- [ ] Edge cases and error conditions covered
- [ ] Minimum 80% code coverage achieved

### Integration Tests:
- [ ] Critical user workflows tested end-to-end
- [ ] API endpoints tested with real HTTP requests
- [ ] Database transactions tested
- [ ] External service integrations mocked

### Performance Tests:
- [ ] Database query performance tested
- [ ] View response times measured
- [ ] Memory usage monitored
- [ ] Concurrent user scenarios tested

### Security Tests:
- [ ] Authentication and authorization tested
- [ ] Input validation tested
- [ ] CSRF protection tested
- [ ] XSS prevention tested

## 🚀 CONTINUOUS TESTING

### Pre-commit Hooks
```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: django-tests
        name: Django Tests
        entry: python manage.py test
        language: system
        pass_filenames: false

      - id: coverage-check
        name: Coverage Check
        entry: coverage run --source='.' manage.py test && coverage report --fail-under=80
        language: system
        pass_filenames: false
```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install coverage

      - name: Run tests with coverage
        run: |
          coverage run --source='.' manage.py test
          coverage report --fail-under=80
          coverage xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v1
```
