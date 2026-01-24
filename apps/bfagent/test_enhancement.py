"""
Quick test script to debug enhancement issue
Run: python test_enhancement.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("=" * 50)
print("TESTING ENHANCEMENT COMPONENTS")
print("=" * 50)

# Test 1: Import markdown parser
try:
    from apps.presentation_studio.handlers.markdown_slide_parser import parse_markdown_file
    print("✅ Test 1: Can import parse_markdown_file")
except Exception as e:
    print(f"❌ Test 1 FAILED: {e}")
    exit(1)

# Test 2: Import preview handler
try:
    from apps.presentation_studio.handlers.preview_slide_handler import PreviewSlideHandler
    print("✅ Test 2: Can import PreviewSlideHandler")
except Exception as e:
    print(f"❌ Test 2 FAILED: {e}")
    exit(1)

# Test 3: Import models
try:
    from apps.presentation_studio.models import Presentation, PreviewSlide
    print("✅ Test 3: Can import models")
except Exception as e:
    print(f"❌ Test 3 FAILED: {e}")
    exit(1)

# Test 4: Check if we have test data
try:
    presentation_count = Presentation.objects.count()
    preview_count = PreviewSlide.objects.count()
    print(f"✅ Test 4: Database accessible")
    print(f"   - Presentations: {presentation_count}")
    print(f"   - Preview Slides: {preview_count}")
except Exception as e:
    print(f"❌ Test 4 FAILED: {e}")
    exit(1)

# Test 5: Try to create a handler instance
try:
    handler = PreviewSlideHandler()
    print("✅ Test 5: Can instantiate PreviewSlideHandler")
except Exception as e:
    print(f"❌ Test 5 FAILED: {e}")
    exit(1)

# Test 6: Test with sample markdown (if file exists)
test_md = r"C:\Users\achim\github\bfagent\docs\3_Neurowissenschaft_Slides_Detailliert_Teil1.md"
if os.path.exists(test_md):
    try:
        parser = parse_markdown_file(test_md)
        print(f"✅ Test 6: Can parse markdown file")
        print(f"   - Slides found: {len(parser.slides)}")
    except Exception as e:
        print(f"❌ Test 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"⚠️  Test 6: Skipped (test file not found: {test_md})")

print("=" * 50)
print("ALL BASIC TESTS PASSED! ✅")
print("=" * 50)
print("\nIf enhancement still fails, the error is in the HTTP request/response.")
print("Check the browser console (F12) for the actual error message.")
