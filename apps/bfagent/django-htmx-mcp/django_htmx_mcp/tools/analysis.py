"""
Analysis & Refactoring Tools.

Tools zur Analyse und Verbesserung von Django Code.
"""

import os
import re
from pathlib import Path
from typing import Literal

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case, pascal_case


@mcp.tool()
def find_duplicate_templates(
    project_root: str,
    template_path: str | None = None,
) -> dict:
    """
    Findet duplizierte Django Templates und zeigt welches Django lädt.
    
    Django lädt Templates in dieser Reihenfolge:
    1. DIRS in TEMPLATES setting (meist 'templates/' im Root)
    2. APP_DIRS: templates/ Ordner in jeder App
    
    Args:
        project_root: Pfad zum Django Projekt Root
        template_path: Optional: Spezifischer Template-Pfad zu prüfen (z.B. "bfagent/controlling/dashboard.html")
        
    Returns:
        Dict mit gefundenen Duplikaten und welches aktiv ist
    """
    logger.info(f"Scanning for duplicate templates in {project_root}")
    
    root = Path(project_root)
    
    # Finde alle Template-Verzeichnisse
    template_dirs = []
    
    # 1. Root templates/ (höchste Priorität)
    root_templates = root / "templates"
    if root_templates.exists():
        template_dirs.append(("ROOT (DIRS)", root_templates))
    
    # 2. App templates/ (niedrigere Priorität)
    apps_dir = root / "apps"
    if apps_dir.exists():
        for app_dir in apps_dir.iterdir():
            if app_dir.is_dir():
                app_templates = app_dir / "templates"
                if app_templates.exists():
                    template_dirs.append((f"APP ({app_dir.name})", app_templates))
    
    # Sammle alle Templates
    all_templates = {}  # relative_path -> [(priority, source, full_path)]
    
    for priority, (source, base_dir) in enumerate(template_dirs):
        for template_file in base_dir.rglob("*.html"):
            rel_path = template_file.relative_to(base_dir)
            rel_str = str(rel_path).replace("\\", "/")
            
            if rel_str not in all_templates:
                all_templates[rel_str] = []
            
            all_templates[rel_str].append({
                "priority": priority,
                "source": source,
                "full_path": str(template_file),
                "size": template_file.stat().st_size,
                "modified": template_file.stat().st_mtime,
            })
    
    # Finde Duplikate
    duplicates = {k: v for k, v in all_templates.items() if len(v) > 1}
    
    # Wenn spezifischer Pfad angegeben
    if template_path:
        template_path = template_path.replace("\\", "/")
        if template_path in all_templates:
            locations = all_templates[template_path]
            active = min(locations, key=lambda x: x["priority"])
            return {
                "template_path": template_path,
                "is_duplicate": len(locations) > 1,
                "active_template": {
                    "source": active["source"],
                    "path": active["full_path"],
                },
                "all_locations": locations,
                "warning": f"⚠️ DUPLIKAT! Django lädt '{active['source']}', andere werden ignoriert!" if len(locations) > 1 else None,
                "fix_suggestion": "Lösche oder benenne die duplizierten Templates um." if len(locations) > 1 else None,
            }
        else:
            return {
                "template_path": template_path,
                "error": f"Template '{template_path}' nicht gefunden",
                "searched_dirs": [str(d[1]) for d in template_dirs],
            }
    
    # Allgemeine Duplikat-Analyse
    results = {
        "total_templates": len(all_templates),
        "duplicate_count": len(duplicates),
        "template_dirs": [{"source": s, "path": str(p)} for s, p in template_dirs],
        "duplicates": {},
    }
    
    for rel_path, locations in duplicates.items():
        active = min(locations, key=lambda x: x["priority"])
        results["duplicates"][rel_path] = {
            "active": {
                "source": active["source"],
                "path": active["full_path"],
            },
            "ignored": [
                {"source": loc["source"], "path": loc["full_path"]}
                for loc in locations if loc["priority"] != active["priority"]
            ],
        }
    
    if duplicates:
        results["summary"] = f"⚠️ {len(duplicates)} duplizierte Templates gefunden! Diese können zu Verwirrung führen."
        results["fix_suggestion"] = "Konsolidiere Templates: Behalte nur eine Version pro Pfad."
    else:
        results["summary"] = "✅ Keine duplizierten Templates gefunden."
    
    return results


@mcp.tool()
def analyze_template_loading_order(
    project_root: str,
) -> dict:
    """
    Analysiert die Template-Lade-Reihenfolge eines Django Projekts.
    
    Args:
        project_root: Pfad zum Django Projekt Root
        
    Returns:
        Dict mit Template-Verzeichnissen in Lade-Reihenfolge
    """
    logger.info(f"Analyzing template loading order for {project_root}")
    
    root = Path(project_root)
    loading_order = []
    
    # 1. Check for templates/ in root (DIRS)
    root_templates = root / "templates"
    if root_templates.exists():
        template_count = len(list(root_templates.rglob("*.html")))
        loading_order.append({
            "priority": 1,
            "type": "DIRS (settings.TEMPLATES)",
            "path": str(root_templates),
            "template_count": template_count,
            "note": "⚡ Höchste Priorität - wird zuerst durchsucht",
        })
    
    # 2. Check for app templates (APP_DIRS)
    apps_dir = root / "apps"
    if apps_dir.exists():
        for app_dir in sorted(apps_dir.iterdir()):
            if app_dir.is_dir():
                app_templates = app_dir / "templates"
                if app_templates.exists():
                    template_count = len(list(app_templates.rglob("*.html")))
                    loading_order.append({
                        "priority": 2,
                        "type": f"APP_DIRS ({app_dir.name})",
                        "path": str(app_templates),
                        "template_count": template_count,
                        "note": "Apps werden alphabetisch durchsucht",
                    })
    
    # Check settings.py for TEMPLATES config
    settings_files = list(root.rglob("settings*.py"))
    templates_config = None
    
    for settings_file in settings_files:
        try:
            content = settings_file.read_text(encoding="utf-8", errors="ignore")
            if "TEMPLATES" in content and "DIRS" in content:
                templates_config = str(settings_file)
                break
        except Exception:
            pass
    
    return {
        "loading_order": loading_order,
        "settings_file": templates_config,
        "explanation": """
Django Template Loading Order:
1. TEMPLATES['DIRS'] - Verzeichnisse aus Settings (meist 'templates/')
2. APP_DIRS=True - 'templates/' in jeder installierten App (INSTALLED_APPS Reihenfolge)

Wenn ein Template in mehreren Orten existiert, wird das ERSTE gefunden genutzt!
        """.strip(),
        "best_practices": [
            "Vermeide duplizierte Template-Pfade",
            "Nutze App-spezifische Präfixe: 'myapp/list.html' statt 'list.html'",
            "Root templates/ für projekt-weite Overrides (z.B. admin/)",
            "App templates/ für app-spezifische Templates",
        ],
    }


@mcp.tool()
def analyze_view_for_htmx(
    view_code: str,
) -> dict:
    """
    Analysiert eine Django View und schlägt HTMX-Optimierungen vor.
    
    Args:
        view_code: Python Code der View
        
    Returns:
        Dict mit Analyse und Verbesserungsvorschlägen
    """
    logger.info("Analyzing view for HTMX optimization")
    
    suggestions = []
    issues = []
    
    # Check for redirect after POST
    if "HttpResponseRedirect" in view_code or "redirect(" in view_code:
        suggestions.append({
            "type": "htmx_response",
            "issue": "View verwendet Redirect nach POST",
            "suggestion": "Für HTMX: Partial Template zurückgeben statt Redirect",
            "code": '''if request.headers.get("HX-Request"):
    return render(request, "partial.html", context)
return redirect(success_url)'''
        })
    
    # Check for full page render
    if "render(" in view_code and "partial" not in view_code.lower():
        suggestions.append({
            "type": "partial_template",
            "issue": "View rendert immer volles Template",
            "suggestion": "Separates Partial Template für HTMX Requests",
            "code": '''def get_template_names(self):
    if self.request.headers.get("HX-Request"):
        return ["app/partials/item_partial.html"]
    return ["app/item_full.html"]'''
        })
    
    # Check for JsonResponse
    if "JsonResponse" in view_code:
        suggestions.append({
            "type": "html_response",
            "issue": "View gibt JSON zurück",
            "suggestion": "HTMX erwartet HTML, nicht JSON",
            "code": '''# Statt JsonResponse:
from django.template.loader import render_to_string
html = render_to_string("partial.html", data)
return HttpResponse(html)'''
        })
    
    # Check for missing HTMX headers
    if "HX-Trigger" not in view_code:
        suggestions.append({
            "type": "htmx_trigger",
            "issue": "Keine HX-Trigger Header",
            "suggestion": "HX-Trigger für Event-basierte Updates",
            "code": '''response["HX-Trigger"] = "itemUpdated"
# Oder mit Daten:
response["HX-Trigger"] = json.dumps({"itemUpdated": {"id": item.pk}})'''
        })
    
    # Check for form handling
    if "form.is_valid()" in view_code:
        if "422" not in view_code and "form_invalid" not in view_code:
            suggestions.append({
                "type": "form_validation",
                "issue": "Form Errors ohne HTMX Status Code",
                "suggestion": "422 Status für HTMX Form Errors",
                "code": '''def form_invalid(self, form):
    response = super().form_invalid(form)
    if self.request.headers.get("HX-Request"):
        response.status_code = 422
    return response'''
            })
    
    # Check for Class-Based vs Function-Based
    is_cbv = "class " in view_code and ("View" in view_code or "Mixin" in view_code)
    is_fbv = "def " in view_code and ("request" in view_code) and not is_cbv
    
    if is_fbv:
        suggestions.append({
            "type": "convert_to_cbv",
            "issue": "Function-Based View",
            "suggestion": "CBV bietet bessere Wiederverwendbarkeit und Mixin-Support",
            "code": "Nutze convert_fbv_to_cbv() Tool"
        })
    
    # Check for pagination
    if "paginate" not in view_code.lower() and ("objects.all()" in view_code or "objects.filter(" in view_code):
        suggestions.append({
            "type": "pagination",
            "issue": "Keine Pagination",
            "suggestion": "Pagination für große Listen",
            "code": '''# In CBV:
paginate_by = 25

# Oder für HTMX Infinite Scroll:
hx-get="?page={{ page_obj.next_page_number }}"
hx-trigger="revealed"
hx-swap="afterend"'''
        })
    
    return {
        "is_cbv": is_cbv,
        "is_fbv": is_fbv,
        "htmx_ready": "HX-Request" in view_code,
        "suggestions": suggestions,
        "issues": issues,
        "summary": f"{len(suggestions)} Verbesserungsvorschläge gefunden"
    }


@mcp.tool()
def convert_fbv_to_cbv(
    function_view_code: str,
    view_name: str | None = None,
) -> str:
    """
    Konvertiert eine Function-Based View zu einer Class-Based View.
    
    Args:
        function_view_code: Python Code der FBV
        view_name: Name für die neue CBV (optional)
        
    Returns:
        Python Code der CBV
    """
    logger.info("Converting FBV to CBV")
    
    # Extract function name
    func_match = re.search(r'def\s+(\w+)\s*\(', function_view_code)
    func_name = func_match.group(1) if func_match else "my_view"
    
    if not view_name:
        view_name = pascal_case(func_name) + "View"
    
    # Detect view type
    has_get = "request.method" in function_view_code and "'GET'" in function_view_code
    has_post = "request.method" in function_view_code and "'POST'" in function_view_code
    has_form = "form" in function_view_code.lower()
    has_pk = "pk" in function_view_code or "id" in function_view_code
    has_queryset = "objects.all()" in function_view_code or "objects.filter(" in function_view_code
    
    # Determine best CBV type
    if has_form and has_pk:
        base_view = "UpdateView"
        imports = "from django.views.generic.edit import UpdateView"
    elif has_form:
        base_view = "CreateView"
        imports = "from django.views.generic.edit import CreateView"
    elif has_queryset and not has_pk:
        base_view = "ListView"
        imports = "from django.views.generic import ListView"
    elif has_pk:
        base_view = "DetailView"
        imports = "from django.views.generic import DetailView"
    else:
        base_view = "View"
        imports = "from django.views import View"
    
    # Generate CBV
    lines = [
        imports,
        "",
        "",
        f"class {view_name}({base_view}):",
        f'    """Converted from {func_name}."""',
        "",
    ]
    
    if base_view == "View":
        # Generic View with get/post methods
        if has_get or not has_post:
            lines.extend([
                "    def get(self, request, *args, **kwargs):",
                "        # TODO: Implement GET logic",
                '        return render(request, "template.html", {})',
                "",
            ])
        if has_post:
            lines.extend([
                "    def post(self, request, *args, **kwargs):",
                "        # TODO: Implement POST logic",
                "        pass",
            ])
    else:
        # Specialized CBV
        lines.extend([
            "    model = None  # TODO: Set model",
            '    template_name = "template.html"  # TODO: Set template',
        ])
        
        if base_view in ("CreateView", "UpdateView"):
            lines.append('    fields = ["__all__"]  # TODO: Set fields')
            lines.append('    success_url = "/"  # TODO: Set success URL')
    
    # Add HTMX support hint
    lines.extend([
        "",
        "    # HTMX Support:",
        '    # def get_template_names(self):',
        '    #     if self.request.headers.get("HX-Request"):',
        '    #         return ["partial.html"]',
        '    #     return super().get_template_names()',
    ])
    
    return "\n".join(lines)


@mcp.tool()
def extract_htmx_partial(
    template_code: str,
    element_id: str | None = None,
    block_name: str | None = None,
) -> dict:
    """
    Extrahiert einen Teil eines Templates als HTMX Partial.
    
    Args:
        template_code: HTML/Django Template Code
        element_id: CSS ID des zu extrahierenden Elements
        block_name: Django Block Name
        
    Returns:
        Dict mit partial_template, updated_main_template, include_statement
    """
    logger.info(f"Extracting partial for element_id={element_id}, block={block_name}")
    
    partial_content = ""
    updated_template = template_code
    
    if block_name:
        # Extract Django block
        block_pattern = rf'{{% block {block_name} %}}(.*?){{% endblock %}}'
        match = re.search(block_pattern, template_code, re.DOTALL)
        
        if match:
            partial_content = match.group(1).strip()
            include_stmt = f'{{% include "partials/{block_name}_partial.html" %}}'
            updated_template = re.sub(
                block_pattern,
                f'{{% block {block_name} %}}\n    {include_stmt}\n{{% endblock %}}',
                template_code,
                flags=re.DOTALL
            )
    
    elif element_id:
        # Extract by ID (simple regex, not perfect HTML parsing)
        # Pattern for div with id
        id_pattern = rf'(<div[^>]*id="{element_id}"[^>]*>)(.*?)(</div>)'
        match = re.search(id_pattern, template_code, re.DOTALL)
        
        if match:
            opening_tag = match.group(1)
            content = match.group(2).strip()
            closing_tag = match.group(3)
            
            partial_content = content
            include_stmt = f'{{% include "partials/{element_id}_partial.html" %}}'
            updated_template = template_code.replace(
                match.group(0),
                f'{opening_tag}\n    {include_stmt}\n{closing_tag}'
            )
    
    if not partial_content:
        return {
            "error": "Could not extract content. Check element_id or block_name.",
            "partial_template": "",
            "updated_main_template": template_code,
            "include_statement": "",
        }
    
    return {
        "partial_template": partial_content,
        "partial_path": f"partials/{element_id or block_name}_partial.html",
        "updated_main_template": updated_template,
        "include_statement": f'{{% include "partials/{element_id or block_name}_partial.html" %}}',
        "htmx_usage": f'''<!-- In main template -->
<div id="{element_id or block_name}"
     hx-get="{{{{ url 'app:partial_view' }}}}"
     hx-trigger="load, customEvent from:body"
     hx-swap="innerHTML">
    {{% include "partials/{element_id or block_name}_partial.html" %}}
</div>'''
    }


@mcp.tool()
def analyze_template_for_htmx(
    template_code: str,
) -> dict:
    """
    Analysiert ein Django Template für HTMX-Optimierungen.
    
    Args:
        template_code: HTML/Django Template Code
        
    Returns:
        Analyse-Ergebnisse und Vorschläge
    """
    logger.info("Analyzing template for HTMX")
    
    suggestions = []
    
    # Check for forms without HTMX
    form_pattern = r'<form[^>]*>'
    forms = re.findall(form_pattern, template_code)
    
    for form in forms:
        if 'hx-post' not in form and 'hx-get' not in form:
            suggestions.append({
                "type": "htmx_form",
                "issue": "Form ohne HTMX Attribute",
                "current": form,
                "suggestion": f'{form.replace(">", "")} hx-post="{{{{ request.path }}}}" hx-target="this" hx-swap="outerHTML">'
            })
    
    # Check for links that could be HTMX
    link_pattern = r'<a[^>]*href="[^"]*"[^>]*>'
    links = re.findall(link_pattern, template_code)
    
    for link in links:
        if 'hx-' not in link and 'mailto:' not in link and 'http' not in link:
            suggestions.append({
                "type": "htmx_link",
                "issue": "Interner Link ohne HTMX",
                "current": link,
                "suggestion": "Erwäge hx-get für Partial-Loading"
            })
    
    # Check for pagination
    if 'page_obj' in template_code or 'paginator' in template_code:
        if 'hx-get' not in template_code:
            suggestions.append({
                "type": "htmx_pagination",
                "issue": "Pagination ohne HTMX",
                "suggestion": '''<a hx-get="?page={{ page_obj.next_page_number }}"
   hx-target="#list-container"
   hx-swap="innerHTML">Next</a>'''
            })
    
    # Check for loading indicators
    if 'hx-' in template_code and 'htmx-indicator' not in template_code:
        suggestions.append({
            "type": "loading_indicator",
            "issue": "HTMX ohne Loading Indicator",
            "suggestion": '''<span class="htmx-indicator loading loading-spinner"></span>

<!-- CSS: -->
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator { display: inline; }'''
        })
    
    # Check for error handling
    if 'hx-post' in template_code and 'hx-target-error' not in template_code:
        suggestions.append({
            "type": "error_handling",
            "issue": "Kein HTMX Error Handling",
            "suggestion": '''<!-- Error Target definieren -->
<div id="errors"></div>

<!-- Im Form -->
hx-target-error="#errors"'''
        })
    
    # Detect potential partials
    div_ids = re.findall(r'<div[^>]*id="([^"]+)"', template_code)
    potential_partials = [
        did for did in div_ids 
        if any(kw in did.lower() for kw in ['list', 'content', 'results', 'items', 'table'])
    ]
    
    return {
        "has_htmx": 'hx-' in template_code,
        "form_count": len(forms),
        "htmx_forms": sum(1 for f in forms if 'hx-' in f),
        "potential_partials": potential_partials,
        "suggestions": suggestions,
        "summary": f"{len(suggestions)} Verbesserungsvorschläge"
    }


@mcp.tool()
def generate_htmx_migration_plan(
    app_name: str,
    views: list[str],
    templates: list[str],
) -> str:
    """
    Generiert einen Migrationsplan für HTMX-Umstellung einer Django App.
    
    Args:
        app_name: Name der Django App
        views: Liste der View-Namen
        templates: Liste der Template-Namen
        
    Returns:
        Markdown Migrationsplan
    """
    logger.info(f"Generating HTMX migration plan for {app_name}")
    
    plan = f"""# HTMX Migration Plan: {app_name}

## Übersicht

Migration von {len(views)} Views und {len(templates)} Templates zu HTMX.

## Phase 1: Vorbereitung

### 1.1 Dependencies

```bash
pip install django-htmx
```

### 1.2 Settings

```python
INSTALLED_APPS = [
    ...
    'django_htmx',
]

MIDDLEWARE = [
    ...
    'django_htmx.middleware.HtmxMiddleware',
]
```

### 1.3 Base Template

```html
<!-- base.html -->
<script src="https://unpkg.com/htmx.org@2.0.0"></script>
<script>
document.body.addEventListener('htmx:configRequest', (event) => {{
    event.detail.headers['X-CSRFToken'] = '{{{{ csrf_token }}}}';
}});
</script>
```

## Phase 2: Template-Struktur

### 2.1 Partials-Verzeichnis erstellen

```
{app_name}/
└── templates/
    └── {app_name}/
        ├── partials/           # NEU
        │   ├── _list.html
        │   ├── _form.html
        │   └── _detail.html
        ├── list.html
        └── detail.html
```

## Phase 3: Views migrieren

"""
    
    for view in views:
        plan += f"""### {view}

1. HTMX Request Detection hinzufügen
2. Partial Template erstellen
3. HX-Trigger für Events

```python
def get_template_names(self):
    if self.request.htmx:
        return ["{app_name}/partials/_{snake_case(view)}.html"]
    return super().get_template_names()
```

"""
    
    plan += """## Phase 4: Templates migrieren

"""
    
    for template in templates:
        plan += f"""### {template}

1. Extrahiere Content-Bereich als Partial
2. Füge hx-* Attribute zu interaktiven Elementen
3. Implementiere Loading States

"""
    
    plan += """## Phase 5: Testing

- [ ] Alle Forms funktionieren mit und ohne JavaScript
- [ ] Pagination lädt Partials korrekt
- [ ] Error States werden angezeigt
- [ ] Loading Indicators erscheinen
- [ ] Browser Back/Forward funktioniert (hx-push-url)

## Phase 6: Optimierung

1. **Caching**: Partial Templates cachen
2. **Debouncing**: Bei Suche/Filter hx-trigger="keyup changed delay:300ms"
3. **OOB Updates**: Out-of-Band Swaps für zusammenhängende Updates
"""
    
    return plan


@mcp.tool()
def suggest_htmx_pattern(
    use_case: Literal[
        "infinite_scroll",
        "live_search", 
        "modal_form",
        "inline_edit",
        "dependent_dropdown",
        "bulk_actions",
        "optimistic_ui",
        "polling",
        "sse",
    ],
) -> dict:
    """
    Gibt Best-Practice HTMX Pattern für einen Use Case zurück.
    
    Args:
        use_case: Der gewünschte Use Case
        
    Returns:
        Dict mit template, view, explanation
    """
    patterns = {
        "infinite_scroll": {
            "template": '''<!-- List Container -->
<div id="items">
    {% for item in items %}
    <div class="item">{{ item }}</div>
    {% endfor %}
    
    {% if page_obj.has_next %}
    <div hx-get="?page={{ page_obj.next_page_number }}"
         hx-trigger="revealed"
         hx-swap="afterend"
         hx-select="#items > *">
        <span class="loading loading-spinner"></span>
    </div>
    {% endif %}
</div>''',
            "view": '''class ItemListView(ListView):
    paginate_by = 20
    
    def get_template_names(self):
        if self.request.htmx:
            return ["partials/_items.html"]
        return ["items.html"]''',
            "explanation": "Infinite Scroll lädt neue Items wenn der Trigger sichtbar wird (revealed). hx-select extrahiert nur die Items, nicht den Container."
        },
        
        "live_search": {
            "template": '''<input type="search"
       name="q"
       hx-get="{% url 'search' %}"
       hx-trigger="input changed delay:300ms, search"
       hx-target="#results"
       hx-indicator=".search-spinner">

<span class="search-spinner htmx-indicator">🔄</span>
<div id="results"></div>''',
            "view": '''class SearchView(View):
    def get(self, request):
        q = request.GET.get('q', '')
        if len(q) < 2:
            return HttpResponse('')
        
        results = Model.objects.filter(name__icontains=q)[:20]
        return render(request, 'partials/_results.html', {'results': results})''',
            "explanation": "delay:300ms debounced die Suche. 'search' Event für Enter-Taste. Minimum 2 Zeichen verhindert zu viele Requests."
        },
        
        "modal_form": {
            "template": '''<!-- Trigger Button -->
<button hx-get="{% url 'item_create' %}"
        hx-target="#modal-container"
        hx-swap="innerHTML">
    + New Item
</button>

<!-- Modal Container -->
<div id="modal-container"></div>

<!-- Modal Template (partials/_modal_form.html) -->
<div class="modal modal-open">
    <div class="modal-box">
        <form hx-post="{% url 'item_create' %}"
              hx-target="#modal-container"
              hx-swap="innerHTML">
            {% csrf_token %}
            {{ form.as_p }}
            <button type="submit">Save</button>
            <button type="button" onclick="this.closest('.modal').remove()">Cancel</button>
        </form>
    </div>
    <div class="modal-backdrop" onclick="this.parentElement.remove()"></div>
</div>''',
            "view": '''class ItemCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save()
        if self.request.htmx:
            response = HttpResponse()
            response['HX-Trigger'] = 'itemCreated'
            return response
        return super().form_valid(form)
    
    def form_invalid(self, form):
        response = render(self.request, 'partials/_modal_form.html', {'form': form})
        response.status_code = 422
        return response''',
            "explanation": "Modal wird per HTMX geladen. Nach erfolgreichem Submit wird ein Event getriggert und das Modal geleert. Bei Fehler wird das Form mit Errors neu gerendert."
        },
        
        "inline_edit": {
            "template": '''<!-- Display Mode -->
<span id="field-{{ item.pk }}"
      hx-get="{% url 'item_edit_field' item.pk %}"
      hx-trigger="click"
      hx-swap="outerHTML"
      class="cursor-pointer hover:bg-gray-100 px-2 py-1 rounded">
    {{ item.name }}
</span>

<!-- Edit Mode (partials/_inline_edit.html) -->
<form hx-post="{% url 'item_edit_field' item.pk %}"
      hx-swap="outerHTML"
      class="inline-flex gap-2">
    {% csrf_token %}
    <input name="name" value="{{ item.name }}" class="input input-sm" autofocus>
    <button type="submit" class="btn btn-sm btn-primary">✓</button>
    <button type="button" 
            hx-get="{% url 'item_detail' item.pk %}"
            hx-target="#field-{{ item.pk }}"
            hx-swap="outerHTML"
            class="btn btn-sm">✕</button>
</form>''',
            "view": '''class InlineEditView(View):
    def get(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        return render(request, 'partials/_inline_edit.html', {'item': item})
    
    def post(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        item.name = request.POST.get('name')
        item.save()
        return render(request, 'partials/_inline_display.html', {'item': item})''',
            "explanation": "Click auf Feld zeigt Edit-Form. Save ersetzt Form mit Display. Cancel lädt ursprüngliches Display."
        },
        
        "dependent_dropdown": {
            "template": '''<select name="category"
        hx-get="{% url 'get_subcategories' %}"
        hx-target="#subcategory-select"
        hx-trigger="change"
        hx-include="this">
    <option value="">Select Category</option>
    {% for cat in categories %}
    <option value="{{ cat.pk }}">{{ cat.name }}</option>
    {% endfor %}
</select>

<select name="subcategory" id="subcategory-select">
    <option value="">Select Category first</option>
</select>''',
            "view": '''class SubcategoryView(View):
    def get(self, request):
        category_id = request.GET.get('category')
        if not category_id:
            return HttpResponse('<option value="">Select Category first</option>')
        
        subs = Subcategory.objects.filter(category_id=category_id)
        html = ''.join(f'<option value="{s.pk}">{s.name}</option>' for s in subs)
        return HttpResponse(html)''',
            "explanation": "hx-include='this' sendet den aktuellen Select-Wert mit. Das Target-Select wird mit neuen Options ersetzt."
        },
        
        "bulk_actions": {
            "template": '''<form id="bulk-form">
    <select name="action" hx-trigger="change" hx-post="{% url 'bulk_action' %}" hx-include="#bulk-form">
        <option value="">Bulk Actions</option>
        <option value="delete">Delete Selected</option>
        <option value="archive">Archive Selected</option>
    </select>
    
    <table>
        {% for item in items %}
        <tr id="item-{{ item.pk }}">
            <td><input type="checkbox" name="ids" value="{{ item.pk }}"></td>
            <td>{{ item.name }}</td>
        </tr>
        {% endfor %}
    </table>
</form>''',
            "view": '''class BulkActionView(View):
    def post(self, request):
        ids = request.POST.getlist('ids')
        action = request.POST.get('action')
        
        if action == 'delete':
            Item.objects.filter(pk__in=ids).delete()
        elif action == 'archive':
            Item.objects.filter(pk__in=ids).update(archived=True)
        
        response = HttpResponse()
        response['HX-Trigger'] = 'bulkActionComplete'
        return response''',
            "explanation": "hx-include sammelt alle Checkboxes im Form. Nach Action wird Event getriggert für List-Refresh."
        },
        
        "optimistic_ui": {
            "template": '''<button hx-post="{% url 'toggle_like' item.pk %}"
        hx-swap="outerHTML"
        hx-indicator="this"
        class="like-btn {% if liked %}liked{% endif %}"
        onclick="this.classList.toggle('liked')">
    ❤️ {{ item.likes }}
</button>''',
            "view": '''class ToggleLikeView(View):
    def post(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        liked = item.toggle_like(request.user)
        return render(request, 'partials/_like_button.html', {
            'item': item,
            'liked': liked
        })''',
            "explanation": "onclick ändert den Zustand sofort (optimistic). Der Server-Response ersetzt dann mit dem echten Zustand."
        },
        
        "polling": {
            "template": '''<div hx-get="{% url 'notifications_count' %}"
     hx-trigger="every 30s"
     hx-swap="innerHTML">
    {{ unread_count }}
</div>

<!-- Oder: Stop bei 0 -->
<div hx-get="{% url 'job_status' job.pk %}"
     hx-trigger="every 2s [status != 'complete']"
     hx-swap="outerHTML">
    Status: {{ job.status }}
</div>''',
            "view": '''class JobStatusView(View):
    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        return render(request, 'partials/_job_status.html', {'job': job})''',
            "explanation": "every Xs pollt regelmäßig. Condition [expr] stoppt Polling wenn Bedingung false. Für Echtzeit besser SSE nutzen."
        },
        
        "sse": {
            "template": '''<div hx-ext="sse"
     sse-connect="{% url 'notifications_stream' %}"
     sse-swap="message">
    <!-- Updates erscheinen hier -->
</div>

<!-- Oder für verschiedene Event-Typen -->
<div hx-ext="sse" sse-connect="/stream/">
    <div sse-swap="notification"></div>
    <div sse-swap="alert"></div>
</div>''',
            "view": '''from django.http import StreamingHttpResponse

def notifications_stream(request):
    def event_stream():
        while True:
            # Check for new notifications
            if has_new:
                yield f'event: message\\ndata: {html}\\n\\n'
            time.sleep(1)
    
    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )''',
            "explanation": "SSE (Server-Sent Events) für Echtzeit-Updates. Benötigt ASGI oder separate Worker. Besser für Chat, Notifications als Polling."
        },
    }
    
    return patterns.get(use_case, {"error": f"Unknown use case: {use_case}"})
