#!/usr/bin/env python
"""Quick test of export functionality"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import BookProjects
from apps.bfagent.services.book_export import BookExportService

print("=" * 80)
print("🧪 TESTING EXPORT FUNCTIONS")
print("=" * 80)

project = BookProjects.objects.get(id=3)
exporter = BookExportService()

print(f"\n📚 Project: {project.title}")
print(f"   Genre: {project.genre}")

# Test DOCX
print("\n📄 Exporting to DOCX...")
try:
    docx_path = exporter.export_to_docx(project)
    print(f"   ✅ Success: {docx_path}")
    print(f"   Size: {docx_path.stat().st_size / 1024:.1f} KB")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test PDF
print("\n📑 Exporting to PDF...")
try:
    pdf_path = exporter.export_to_pdf(project)
    print(f"   ✅ Success: {pdf_path}")
    print(f"   Size: {pdf_path.stat().st_size / 1024:.1f} KB")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test EPUB
print("\n📚 Exporting to EPUB...")
try:
    epub_path = exporter.export_to_epub(project)
    print(f"   ✅ Success: {epub_path}")
    print(f"   Size: {epub_path.stat().st_size / 1024:.1f} KB")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 80)
print("✅ Export Test Complete!")
print("=" * 80)
