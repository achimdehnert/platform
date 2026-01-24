"""
Generate PDF Extractor Handler with AI
Production-ready PDF text extraction with OCR support
"""

import os
import django
from pathlib import Path

# Load .env file from project root
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.agents.handler_generator.agent import generate_handler_from_description


def main():
    print("="*70)
    print("PDF EXTRACTOR HANDLER - AI GENERATION")
    print("="*70)
    
    # PDF Extractor Description
    description = """
    Create a production-ready PDF text extractor handler that:
    
    CORE FEATURES:
    - Extract text from PDF files (single and multi-page)
    - Support for both text-based and scanned PDFs
    - OCR support for image-based PDFs using Tesseract
    - Handle password-protected PDFs
    - Extract metadata (author, title, creation date, page count)
    
    TEXT EXTRACTION:
    - Preserve formatting and paragraph structure
    - Extract text by page or entire document
    - Support for tables and columns
    - Handle special characters and unicode
    - Option to include or exclude headers/footers
    
    CONFIGURATION:
    - Configurable OCR language (default: English)
    - Page range selection (e.g., pages 1-10)
    - Text cleaning options (remove extra whitespace, normalize)
    - Output format: plain text, markdown, or structured JSON
    
    ERROR HANDLING:
    - Graceful handling of corrupted PDFs
    - Clear error messages for unsupported formats
    - Timeout handling for large files
    - Memory-efficient processing for large documents
    
    OUTPUT:
    - Extracted text content
    - Page-by-page breakdown
    - Document metadata
    - Extraction confidence score (for OCR)
    - Processing statistics (pages processed, time taken)
    """
    
    print("\n📝 Handler Description:")
    print(description)
    
    print("\n🤖 Generating PDF Extractor Handler with AI...")
    print("   Provider: Anthropic Claude")
    print("   Mode: Test (auto_deploy=False)")
    print("   Estimated time: 15-25 seconds\n")
    
    try:
        # Generate handler (without auto-deploy for safety)
        result = generate_handler_from_description(
            description=description,
            auto_deploy=False  # Review before deploying
        )
        
        print("="*70)
        print("✅ PDF EXTRACTOR GENERATION SUCCESSFUL!")
        print("="*70)
        
        # Show requirements
        print("\n📋 Handler Requirements:")
        print(f"   ID: {result['requirements'].handler_id}")
        print(f"   Name: {result['requirements'].display_name}")
        print(f"   Category: {result['requirements'].category}")
        print(f"   Dependencies: {', '.join(result['requirements'].dependencies)}")
        
        # Show validation results
        print("\n🔍 Validation Results:")
        print(f"   Valid: {result['validation'].is_valid}")
        print(f"   Syntax Valid: {result['validation'].syntax_valid}")
        if result['validation'].syntax_errors:
            print(f"   Errors: {len(result['validation'].syntax_errors)}")
            for error in result['validation'].syntax_errors:
                print(f"      - {error}")
        if result['validation'].warnings:
            print(f"   Warnings: {len(result['validation'].warnings)}")
            for warning in result['validation'].warnings:
                print(f"      - {warning}")
        
        # Show generated code preview
        print("\n📄 Generated Handler Code (Preview - First 60 lines):")
        print("-"*70)
        handler_lines = result['generated'].handler_code.split('\n')
        for i, line in enumerate(handler_lines[:60], 1):
            print(f"{i:3d} | {line}")
        if len(handler_lines) > 60:
            print(f"... ({len(handler_lines) - 60} more lines)")
        print("-"*70)
        
        # Save generated code to files for review
        handler_id = result['requirements'].handler_id
        
        print(f"\n💾 Saving PDF Extractor code for review...")
        
        with open(f'generated_{handler_id}_handler.py', 'w', encoding='utf-8') as f:
            f.write(result['generated'].handler_code)
        print(f"   ✅ Handler: generated_{handler_id}_handler.py")
        
        with open(f'generated_{handler_id}_config.py', 'w', encoding='utf-8') as f:
            f.write(result['generated'].config_model_code)
        print(f"   ✅ Config: generated_{handler_id}_config.py")
        
        with open(f'generated_{handler_id}_test.py', 'w', encoding='utf-8') as f:
            f.write(result['generated'].test_code)
        print(f"   ✅ Tests: generated_{handler_id}_test.py")
        
        with open(f'generated_{handler_id}_docs.md', 'w', encoding='utf-8') as f:
            f.write(result['generated'].documentation)
        print(f"   ✅ Docs: generated_{handler_id}_docs.md")
        
        # Dependencies info
        print("\n📦 Required Dependencies:")
        for dep in result['requirements'].dependencies:
            print(f"   - {dep}")
        print("\n   Install with: pip install " + " ".join(result['requirements'].dependencies))
        
        # Next steps
        print("\n" + "="*70)
        print("🎯 NEXT STEPS:")
        print("="*70)
        print("\n1. Review the generated files:")
        print(f"   - generated_{handler_id}_handler.py")
        print(f"   - generated_{handler_id}_config.py")
        print(f"   - generated_{handler_id}_test.py")
        print(f"   - generated_{handler_id}_docs.md")
        
        print("\n2. Install required dependencies:")
        print("   pip install " + " ".join(result['requirements'].dependencies))
        
        print("\n3. Deploy the handler:")
        print("   python")
        print("   >>> from apps.bfagent.agents.handler_generator.agent import HandlerGeneratorAgent")
        print("   >>> agent = HandlerGeneratorAgent()")
        print(f"   >>> # Use the result object to deploy")
        
        print("\n4. Test the handler:")
        print(f"   pytest generated_{handler_id}_test.py -v")
        
        print("\n" + "="*70)
        print("✅ PDF EXTRACTOR HANDLER READY!")
        print("="*70)
        
        return result
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ GENERATION FAILED")
        print("="*70)
        print(f"\nError: {e}")
        print(f"Type: {type(e).__name__}")
        
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        
        return None


if __name__ == "__main__":
    result = main()
    
    if result:
        print("\n💡 PDF Extractor is ready for Book Factory!")
        print("   Perfect for extracting text from uploaded manuscripts.")
