"""
Generate First Handler with AI
Quick test script to generate a simple JSON validator handler
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
import json


def main():
    print("="*70)
    print("HANDLER GENERATOR - FIRST HANDLER TEST")
    print("="*70)
    
    # Description for our first handler
    description = """
    Create a JSON validator handler that:
    - Takes a JSON string as input
    - Validates if it's valid JSON syntax
    - Checks for required fields (configurable)
    - Returns validation result with detailed error messages
    - Supports nested object validation
    """
    
    print("\n📝 Handler Description:")
    print(description)
    
    print("\n🤖 Generating handler with AI...")
    print("   Provider: Anthropic Claude")
    print("   Mode: Test (auto_deploy=False)\n")
    
    try:
        # Generate handler (without auto-deploy for safety)
        result = generate_handler_from_description(
            description=description,
            auto_deploy=False  # We'll review first before deploying
        )
        
        print("="*70)
        print("✅ GENERATION SUCCESSFUL!")
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
        print("\n📄 Generated Handler Code (Preview - First 50 lines):")
        print("-"*70)
        handler_lines = result['generated'].handler_code.split('\n')
        for i, line in enumerate(handler_lines[:50], 1):
            print(f"{i:3d} | {line}")
        if len(handler_lines) > 50:
            print(f"... ({len(handler_lines) - 50} more lines)")
        print("-"*70)
        
        # Show config model preview
        print("\n⚙️  Generated Config Model (Preview - First 30 lines):")
        print("-"*70)
        config_lines = result['generated'].config_model_code.split('\n')
        for i, line in enumerate(config_lines[:30], 1):
            print(f"{i:3d} | {line}")
        if len(config_lines) > 30:
            print(f"... ({len(config_lines) - 30} more lines)")
        print("-"*70)
        
        # Show deployment status
        print("\n📦 Deployment Status:")
        print(f"   Deployed: {result['deployed']}")
        if result['handler']:
            print(f"   Handler ID: {result['handler'].handler_id}")
        else:
            print("   Handler not deployed (test mode)")
        
        # Save generated code to files for review
        handler_id = result['requirements'].handler_id
        
        print(f"\n💾 Saving generated code for review...")
        
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
        
        # Next steps
        print("\n" + "="*70)
        print("🎯 NEXT STEPS:")
        print("="*70)
        print("\n1. Review the generated files:")
        print(f"   - generated_{handler_id}_handler.py")
        print(f"   - generated_{handler_id}_config.py")
        print(f"   - generated_{handler_id}_test.py")
        print(f"   - generated_{handler_id}_docs.md")
        print("\n2. If satisfied, deploy the handler:")
        print("   python")
        print("   >>> from apps.bfagent.agents.handler_generator.agent import HandlerGeneratorAgent")
        print("   >>> agent = HandlerGeneratorAgent()")
        print(f"   >>> handler = agent.deploy_handler(requirements, generated)")
        print("\n3. Or regenerate with feedback:")
        print("   >>> improved = agent.regenerate_handler(requirements, 'Make it faster')")
        
        print("\n" + "="*70)
        print("✅ HANDLER GENERATION COMPLETE!")
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
        print("\n💡 TIP: Run this again to generate different handlers!")
        print("   Just change the description in the script.")
