#!/usr/bin/env python
"""
Automatic Filter Generator for Django ListView Classes
Intelligently adds search and ForeignKey filters to all ListView classes.
"""
import os
import sys
import django
import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple

# Django Setup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.apps import apps


class FilterGenerator:
    """Generates filter code for Django ListViews"""
    
    def __init__(self, views_file: str):
        self.views_file = Path(views_file)
        self.model_info = {}
        
    def analyze_models(self):
        """Analyze all models to understand their structure"""
        for model in apps.get_app_config('bfagent').get_models():
            foreign_keys = []
            search_fields = []
            
            # Find ForeignKey fields
            for field in model._meta.get_fields():
                if field.many_to_one and not field.auto_created:
                    foreign_keys.append({
                        'name': field.name,
                        'related_model': field.related_model.__name__
                    })
                    
                # Find searchable text fields
                if hasattr(field, 'max_length') and field.max_length:
                    if field.name in ['name', 'title', 'description']:
                        search_fields.append(field.name)
            
            self.model_info[model.__name__] = {
                'foreign_keys': foreign_keys,
                'search_fields': search_fields or ['name']  # Default to name
            }
    
    def generate_get_queryset(self, model_name: str) -> str:
        """Generate get_queryset method code"""
        info = self.model_info.get(model_name, {})
        fks = info.get('foreign_keys', [])
        search_fields = info.get('search_fields', ['name'])
        
        # Build select_related clause
        select_related = ', '.join([f"'{fk['name']}'" for fk in fks]) if fks else ''
        
        code = []
        code.append("    def get_queryset(self):")
        
        if select_related:
            code.append(f"        queryset = {model_name}.objects.select_related({select_related}).all()")
        else:
            code.append(f"        queryset = {model_name}.objects.all()")
        code.append("        ")
        
        # Add ForeignKey filters
        for fk in fks:
            var_name = f"{fk['name']}_id"
            code.append(f"        # Filter by {fk['name']}")
            code.append(f"        {var_name} = self.request.GET.get('{fk['name']}', '').strip()")
            code.append(f"        if {var_name}:")
            code.append(f"            queryset = queryset.filter({fk['name']}_id={var_name})")
            code.append("        ")
        
        # Add search filter
        search_conditions = ' | '.join([
            f"models.Q({field}__icontains=search)" for field in search_fields
        ])
        
        code.append("        # Search")
        code.append("        search = self.request.GET.get('q', '').strip()")
        code.append("        if search:")
        code.append(f"            queryset = queryset.filter({search_conditions})")
        code.append("        ")
        
        # Order by
        order_field = search_fields[0] if search_fields else 'id'
        code.append(f"        return queryset.order_by('{order_field}')")
        
        return '\n'.join(code)
    
    def generate_get_context_data(self, model_name: str) -> str:
        """Generate get_context_data method code"""
        info = self.model_info.get(model_name, {})
        fks = info.get('foreign_keys', [])
        
        code = []
        code.append("    def get_context_data(self, **kwargs):")
        code.append("        context = super().get_context_data(**kwargs)")
        code.append(f"        context['title'] = '{model_name} List'")
        code.append("        ")
        
        # Add ForeignKey options
        for fk in fks:
            related_model = fk['related_model']
            code.append(f"        context['all_{fk['name']}s'] = {related_model}.objects.all().order_by('name')")
        
        # Add current filters
        filter_dict = {fk['name']: f"self.request.GET.get('{fk['name']}', '')" for fk in fks}
        filter_dict['q'] = "self.request.GET.get('q', '')"
        
        code.append("        context['current_filters'] = {")
        for key, value in filter_dict.items():
            code.append(f"            '{key}': {value},")
        code.append("        }")
        code.append("        return context")
        
        return '\n'.join(code)
    
    def find_listviews(self) -> List[Tuple[str, str]]:
        """Find all ListView classes and their models"""
        with open(self.views_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        listviews = []
        
        # Parse Python AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from ListView
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'ListView':
                        # Find model attribute
                        model_name = None
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and target.id == 'model':
                                        if isinstance(item.value, ast.Name):
                                            model_name = item.value.id
                        
                        if model_name:
                            listviews.append((node.name, model_name))
        
        return listviews
    
    def check_has_queryset_method(self, class_name: str) -> bool:
        """Check if class already has get_queryset method"""
        with open(self.views_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple regex check
        pattern = rf'class {class_name}\([^)]+\):.*?def get_queryset\(self\):'
        return bool(re.search(pattern, content, re.DOTALL))
    
    def generate_report(self):
        """Generate analysis report"""
        print("=" * 80)
        print("🔍 FILTER GENERATOR - ANALYSIS REPORT")
        print("=" * 80)
        print()
        
        self.analyze_models()
        listviews = self.find_listviews()
        
        print(f"📊 Found {len(listviews)} ListView classes")
        print()
        
        needs_filters = []
        has_filters = []
        
        for view_name, model_name in listviews:
            has_method = self.check_has_queryset_method(view_name)
            
            if has_method:
                has_filters.append((view_name, model_name))
                status = "✅ HAS FILTERS"
            else:
                needs_filters.append((view_name, model_name))
                status = "❌ NEEDS FILTERS"
            
            info = self.model_info.get(model_name, {})
            fks = info.get('foreign_keys', [])
            fk_names = ', '.join([fk['name'] for fk in fks]) if fks else 'None'
            
            print(f"{status:20} | {view_name:30} | Model: {model_name:20} | FKs: {fk_names}")
        
        print()
        print(f"✅ Already has filters: {len(has_filters)}")
        print(f"❌ Needs filters: {len(needs_filters)}")
        print()
        
        return needs_filters
    
    def generate_filter_code_for_view(self, view_name: str, model_name: str):
        """Generate complete filter code for a view"""
        print(f"\n{'=' * 80}")
        print(f"📝 Filter Code for: {view_name} (Model: {model_name})")
        print(f"{'=' * 80}\n")
        
        print("# Add this to the view class:")
        print()
        print(self.generate_get_queryset(model_name))
        print()
        print(self.generate_get_context_data(model_name))
        print()


def main():
    """Main execution"""
    views_file = Path(__file__).parent.parent / 'apps' / 'bfagent' / 'views' / 'main_views.py'
    
    generator = FilterGenerator(views_file)
    
    print("\n🚀 AUTOMATIC FILTER GENERATOR")
    print("=" * 80)
    print()
    
    # Generate report
    needs_filters = generator.generate_report()
    
    if not needs_filters:
        print("✅ All ListViews already have filters!")
        return
    
    print()
    print("📋 GENERATED FILTER CODE:")
    print()
    
    # Generate code for each view
    for view_name, model_name in needs_filters:
        generator.generate_filter_code_for_view(view_name, model_name)
    
    print()
    print("=" * 80)
    print("✅ FILTER CODE GENERATION COMPLETE")
    print("=" * 80)
    print()
    print("📝 Next Steps:")
    print("1. Review the generated code above")
    print("2. Copy the methods into the respective view classes")
    print("3. Update templates to include filter forms")
    print("4. Test the filters in the browser")


if __name__ == '__main__':
    main()
