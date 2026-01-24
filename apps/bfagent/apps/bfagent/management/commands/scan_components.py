"""
Management Command: Scan and register components
Scans Python files for handlers, views, models, etc. and registers them
"""
from django.core.management.base import BaseCommand, CommandError
from pathlib import Path
import ast
import importlib.util
from typing import List, Dict, Optional
from apps.bfagent.models_registry import ComponentRegistry, ComponentType, ComponentStatus


class ComponentScanner:
    """Scans Python files for components"""
    
    @staticmethod
    def scan_file(file_path: Path) -> List[Dict]:
        """Scan a Python file for components"""
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    component = ComponentScanner._analyze_class(node, file_path, content)
                    if component:
                        components.append(component)
        
        except Exception as e:
            print(f"⚠️  Error scanning {file_path}: {e}")
        
        return components
    
    @staticmethod
    def _analyze_class(node: ast.ClassDef, file_path: Path, content: str) -> Optional[Dict]:
        """Analyze a class node"""
        class_name = node.name
        
        # Detect component type
        component_type = ComponentScanner._detect_type(class_name, node)
        
        if not component_type:
            return None
        
        # Extract docstring
        docstring = ast.get_docstring(node) or ""
        
        # Build identifier
        module_path = str(file_path).replace('\\', '.').replace('/', '.')
        module_path = module_path.replace('.py', '').replace('..', '')
        if module_path.startswith('apps.'):
            module_path = module_path
        else:
            module_path = f"apps.{module_path}"
        
        identifier = f"{module_path}.{class_name}"
        
        # Extract metadata
        metadata = {
            'line_number': node.lineno,
            'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
            'base_classes': [ComponentScanner._get_base_name(base) for base in node.bases]
        }
        
        return {
            'identifier': identifier,
            'name': class_name,
            'component_type': component_type,
            'module_path': module_path,
            'file_path': str(file_path),
            'class_name': class_name,
            'docstring': docstring,
            'description': docstring.split('\n')[0] if docstring else "",
            'metadata': metadata,
            'tags': ComponentScanner._extract_tags(class_name, docstring),
            'status': ComponentStatus.ACTIVE
        }
    
    @staticmethod
    def _detect_type(class_name: str, node: ast.ClassDef) -> Optional[str]:
        """Detect component type from class name and bases"""
        name_lower = class_name.lower()
        
        # Check base classes
        bases = [ComponentScanner._get_base_name(base) for base in node.bases]
        
        if any('Handler' in base for base in bases) or class_name.endswith('Handler'):
            return ComponentType.HANDLER
        
        if any('View' in base for base in bases) or name_lower.endswith('view'):
            return ComponentType.VIEW
        
        if any('Model' in base for base in bases) or 'models.Model' in str(bases):
            return ComponentType.MODEL
        
        if any('Form' in base for base in bases) or name_lower.endswith('form'):
            return ComponentType.FORM
        
        if any('Serializer' in base for base in bases):
            return ComponentType.SERIALIZER
        
        if 'Service' in class_name:
            return ComponentType.SERVICE
        
        return None
    
    @staticmethod
    def _get_base_name(base) -> str:
        """Get base class name from AST node"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return base.attr
        return ""
    
    @staticmethod
    def _extract_tags(class_name: str, docstring: str) -> List[str]:
        """Extract searchable tags"""
        tags = []
        
        # From class name
        name_parts = class_name.replace('Handler', '').replace('View', '').replace('Service', '')
        for part in [name_parts[i:i+4] for i in range(0, len(name_parts), 4)]:
            if part.lower() not in ['hand', 'ler', 'view', 'serv', 'ice']:
                tags.append(part.lower())
        
        # Common keywords
        keywords = ['character', 'world', 'chapter', 'outline', 'generation', 'llm', 'ai']
        text = (class_name + ' ' + docstring).lower()
        tags.extend([kw for kw in keywords if kw in text])
        
        return list(set(tags))[:10]  # Limit to 10 unique tags


class Command(BaseCommand):
    help = 'Scan and register components from Python files'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            help='Path to scan (e.g., apps/bfagent/domains/book_writing)'
        )
        parser.add_argument(
            '--domain',
            type=str,
            default='',
            help='Domain name (e.g., book, explosion, shared)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Scan but do not save to database'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing components'
        )
    
    def handle(self, *args, **options):
        path_str = options.get('path')
        domain = options.get('domain')
        dry_run = options.get('dry_run')
        update = options.get('update')
        
        if not path_str:
            raise CommandError('--path is required')
        
        base_path = Path(path_str)
        
        if not base_path.exists():
            raise CommandError(f'Path does not exist: {base_path}')
        
        self.stdout.write(self.style.SUCCESS(f'\n🔍 Scanning: {base_path}\n'))
        
        # Scan files
        files_scanned = 0
        components_found = []
        
        if base_path.is_file():
            files = [base_path]
        else:
            files = list(base_path.rglob('*.py'))
        
        scanner = ComponentScanner()
        
        for file_path in files:
            if '__pycache__' in str(file_path) or 'migrations' in str(file_path):
                continue
            
            files_scanned += 1
            components = scanner.scan_file(file_path)
            
            for comp in components:
                if domain:
                    comp['domain'] = domain
                components_found.append(comp)
                self.stdout.write(f"  ✓ Found: {comp['name']} ({comp['component_type']})")
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 SCAN SUMMARY'))
        self.stdout.write(f"Files scanned:      {files_scanned}")
        self.stdout.write(f"Components found:   {len(components_found)}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No changes saved\n'))
            return
        
        # Save to database
        registered = 0
        updated_count = 0
        skipped = 0
        
        for comp_data in components_found:
            identifier = comp_data['identifier']
            
            try:
                existing = ComponentRegistry.objects.filter(identifier=identifier).first()
                
                if existing:
                    if update:
                        for key, value in comp_data.items():
                            setattr(existing, key, value)
                        existing.save()
                        updated_count += 1
                        self.stdout.write(f"  ↻ Updated: {comp_data['name']}")
                    else:
                        skipped += 1
                else:
                    ComponentRegistry.objects.create(**comp_data)
                    registered += 1
                    self.stdout.write(f"  ✅ Registered: {comp_data['name']}")
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error registering {comp_data['name']}: {e}")
                )
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ REGISTRATION COMPLETE'))
        self.stdout.write(f"Registered:  {registered}")
        self.stdout.write(f"Updated:     {updated_count}")
        self.stdout.write(f"Skipped:     {skipped}")
        self.stdout.write(f"\n")
