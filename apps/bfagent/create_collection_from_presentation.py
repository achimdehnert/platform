"""
Create TemplateCollection from existing Presentation
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.presentation_studio.models import Presentation, TemplateCollection
from apps.presentation_studio.services.template_analyzer import TemplateAnalyzer
from django.contrib.auth.models import User

# Get the presentation
presentation = Presentation.objects.order_by('-uploaded_at').first()

if not presentation:
    print("❌ No presentations found!")
    exit(1)

print(f"📊 Using Presentation: {presentation.title}")
print(f"   ID: {presentation.id}")
print(f"   Enhanced file: {presentation.enhanced_file}")

# Check if enhanced file exists
if not presentation.enhanced_file or not presentation.enhanced_file.path:
    print("❌ No enhanced file found! Using original file...")
    pptx_path = presentation.original_file.path
else:
    pptx_path = presentation.enhanced_file.path

print(f"   PPTX Path: {pptx_path}")

if not os.path.exists(pptx_path):
    print(f"❌ File not found: {pptx_path}")
    exit(1)

# Analyze templates
print("\n🔍 Analyzing templates...")
analyzer = TemplateAnalyzer()
templates = analyzer.analyze_presentation(pptx_path)

if not templates:
    print("❌ No templates found!")
    exit(1)

print(f"✅ Found {len(templates)} template types:")
for template_type in templates.keys():
    print(f"   - {template_type}")

# Get admin user
try:
    user = User.objects.get(username='admin')
except User.DoesNotExist:
    user = User.objects.first()
    print(f"⚠️  Admin user not found, using: {user.username}")

# Check if collection already exists
existing = TemplateCollection.objects.filter(name="Auto-Generated Template").first()
if existing:
    print(f"\n⚠️  Template Collection already exists: {existing.name}")
    print(f"   Updating existing collection...")
    existing.templates = templates
    existing.save()
    collection = existing
else:
    # Create collection
    print("\n📦 Creating TemplateCollection...")
    
    from django.core.files import File
    
    with open(pptx_path, 'rb') as f:
        collection = TemplateCollection.objects.create(
            name="Auto-Generated Template",
            description=f"Auto-generated from presentation: {presentation.title}",
            client="",
            project="",
            industry="other",
            templates=templates,
            created_by=user,
            is_default=True,  # Set as default
            is_active=True
        )
        
        # Save PPTX file
        collection.master_pptx.save(
            f'auto_template_{presentation.id}.pptx',
            File(f),
            save=True
        )

print(f"\n✅ Template Collection created!")
print(f"   ID: {collection.id}")
print(f"   Name: {collection.name}")
print(f"   Templates: {collection.template_count}")
print(f"   Is Default: {collection.is_default}")

# Link presentation to collection
print(f"\n🔗 Linking Presentation to Collection...")
presentation.template_collection = collection
presentation.save()

print(f"✅ Presentation linked to TemplateCollection!")
print(f"\n📊 Summary:")
print(f"   Presentation: {presentation.title}")
print(f"   Template Collection: {collection.name}")
print(f"   Templates Available: {list(templates.keys())}")
print(f"\n🎉 Ready to convert preview slides!")
print(f"\n📝 Next: Go to presentation and click 'Convert to PPTX'")
