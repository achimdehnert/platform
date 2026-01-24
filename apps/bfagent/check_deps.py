"""Quick dependency check"""
try:
    import ebooklib
    print("✅ ebooklib OK")
except ImportError as e:
    print(f"❌ ebooklib MISSING: {e}")

try:
    import reportlab
    print("✅ reportlab OK")
except ImportError as e:
    print(f"❌ reportlab MISSING: {e}")

try:
    import docx
    print("✅ python-docx OK")
except ImportError as e:
    print(f"❌ python-docx MISSING: {e}")

try:
    import openai
    print("✅ openai OK")
except ImportError as e:
    print(f"❌ openai MISSING: {e}")

try:
    import replicate
    print("✅ replicate OK")
except ImportError as e:
    print(f"❌ replicate MISSING: {e}")

print("\n✅ All critical dependencies are installed!")
