# -*- coding: utf-8 -*-
"""
Tests für DjangoAgent.
"""
import pytest
from apps.bfagent.agents.django_agent import (
    DjangoAgent,
    validate_before_edit,
    validate_command,
)


class TestDjangoAgentUTF8:
    """Tests für UTF-8 Validierung."""
    
    def test_open_without_encoding_warning(self):
        """open() ohne encoding sollte Warnung geben."""
        code = '''
with open("file.txt", "r") as f:
    data = f.read()
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "test.py")
        
        assert any(e.rule == "utf8_file_open" for e in result.errors + result.warnings)
    
    def test_open_with_encoding_ok(self):
        """open() mit encoding='utf-8' sollte OK sein."""
        code = '''
with open("file.txt", "r", encoding="utf-8") as f:
    data = f.read()
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "test.py")
        
        assert not any(e.rule == "utf8_file_open" for e in result.errors)
    
    def test_json_dumps_without_ensure_ascii(self):
        """json.dumps ohne ensure_ascii sollte Warnung geben."""
        code = '''
import json
data = json.dumps({"name": "Müller"})
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "test.py")
        
        assert any(e.rule == "utf8_json_dumps" for e in result.errors + result.warnings)


class TestDjangoAgentPaths:
    """Tests für Windows-Pfad-Erkennung."""
    
    def test_windows_path_backslash(self):
        """Windows-Pfade mit Backslash sollten Fehler sein."""
        code = '''
path = "C:\\Users\\test\\file.py"
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "test.py")
        
        assert any(e.rule == "no_windows_paths" for e in result.errors)
    
    def test_windows_path_forward_slash(self):
        """Windows-Pfade mit Forward-Slash sollten Fehler sein."""
        code = '''
path = "U:/home/dehnert/github/bfagent"
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "test.py")
        
        assert any(e.rule == "no_windows_paths" for e in result.errors)
    
    def test_linux_path_ok(self):
        """Linux-Pfade sollten OK sein."""
        code = '''
path = "/home/dehnert/github/bfagent"
path2 = "~/github/bfagent"
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "test.py")
        
        assert not any(e.rule == "no_windows_paths" for e in result.errors)


class TestDjangoAgentURLs:
    """Tests für URL-Validierung."""
    
    def test_reverse_without_namespace(self):
        """reverse() ohne Namespace sollte Fehler sein."""
        code = '''
from django.urls import reverse
url = reverse('requirement-detail', kwargs={'pk': 1})
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "apps/test/views.py")
        
        assert any(e.rule == "url_namespace_required" for e in result.errors)
    
    def test_reverse_with_namespace_ok(self):
        """reverse() mit Namespace sollte OK sein."""
        code = '''
from django.urls import reverse
url = reverse('control_center:requirement-detail', kwargs={'pk': 1})
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "apps/test/views.py")
        
        assert not any(e.rule == "url_namespace_required" for e in result.errors)


class TestDjangoAgentTemplates:
    """Tests für Template-Validierung."""
    
    def test_static_without_load(self):
        """{% static %} ohne {% load static %} sollte Fehler sein."""
        html = '''
<html>
<head>
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
</head>
</html>
'''
        agent = DjangoAgent()
        result = agent.validate_template(html, "test.html")
        
        assert any(e.rule == "static_load_required" for e in result.errors)
    
    def test_static_with_load_ok(self):
        """{% static %} mit {% load static %} sollte OK sein."""
        html = '''
{% load static %}
<html>
<head>
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
</head>
</html>
'''
        agent = DjangoAgent()
        result = agent.validate_template(html, "test.html")
        
        assert not any(e.rule == "static_load_required" for e in result.errors)
    
    def test_url_without_namespace_in_template(self):
        """{% url 'name' %} ohne Namespace sollte Fehler sein."""
        html = '''
<a href="{% url 'requirement-detail' pk=obj.id %}">Link</a>
'''
        agent = DjangoAgent()
        result = agent.validate_template(html, "test.html")
        
        assert any(e.rule == "template_url_namespace" for e in result.errors)


class TestDjangoAgentCommands:
    """Tests für Command-Validierung."""
    
    def test_python_without_wsl(self):
        """Python-Commands ohne WSL sollten Fehler sein."""
        result = validate_command("python manage.py migrate")
        
        assert not result.valid
        assert any(e.rule == "wsl_required" for e in result.errors)
        assert result.errors[0].fix_suggestion is not None
    
    def test_python_with_wsl_ok(self):
        """Python-Commands mit WSL sollten OK sein."""
        result = validate_command('wsl bash -c "cd ~/github/bfagent && python manage.py migrate"')
        
        assert result.valid


class TestDjangoAgentNaming:
    """Tests für Naming-Convention-Validierung."""
    
    def test_model_naming_pascal_case(self):
        """Models sollten PascalCase sein."""
        code = '''
from django.db import models

class test_requirement(models.Model):
    name = models.CharField(max_length=100)
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "apps/test/models.py")
        
        assert any(e.rule == "model_naming" for e in result.errors + result.warnings)
    
    def test_view_class_naming(self):
        """View-Klassen sollten mit 'View' enden."""
        code = '''
from django.views.generic import DetailView

class RequirementDetail(DetailView):
    model = TestRequirement
'''
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "apps/test/views.py")
        
        assert any(e.rule == "view_class_naming" for e in result.errors + result.warnings)
