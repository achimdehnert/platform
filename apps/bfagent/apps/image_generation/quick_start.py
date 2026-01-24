#!/usr/bin/env python3
"""
Quick Start Example for BF Agent Image Generation System
=========================================================

This script demonstrates how to quickly get started with the system.

Prerequisites:
1. Set environment variables: OPENAI_API_KEY, STABILITY_API_KEY
2. Install dependencies: pip install -r requirements.txt

Author: BF Agent Team
"""

import os
import sys
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load .env file
try:
    from dotenv import load_dotenv
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from .env\n")
    else:
        print(f"⚠️  .env file not found at {env_file}\n")
except ImportError:
    print("⚠️  python-dotenv not installed. Run: pip install python-dotenv\n")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

try:
    import django
    django.setup()
except ImportError:
    print("⚠️  Django not available, using standalone mode")

# Import from apps.image_generation
from apps.image_generation.config import get_config
from apps.image_generation.providers import (
    OpenAIProvider,
    StabilityAIProvider,
    ProviderManager,
    ProviderConfig,
    SelectionStrategy
)
from apps.image_generation.handlers import (
    SingleImageHandler, 
    BatchImageHandler, 
    IllustrationGenerationHandler
)


def check_environment():
    """Check if API keys are set"""
    openai_key = os.getenv('OPENAI_API_KEY')
    stability_key = os.getenv('STABILITY_API_KEY')
    
    if not openai_key and not stability_key:
        print("❌ ERROR: No API keys found!")
        print("\nPlease set at least one API key:")
        print("  export OPENAI_API_KEY='sk-...'")
        print("  export STABILITY_API_KEY='sk-...'")
        sys.exit(1)
    
    providers = []
    if openai_key:
        providers.append("OpenAI DALL-E 3")
    if stability_key:
        providers.append("Stability AI SD3")
    
    print(f"✅ Found API keys for: {', '.join(providers)}\n")
    return openai_key, stability_key


def setup_providers(openai_key, stability_key):
    """Setup providers and manager"""
    print("🔧 Setting up providers...")
    
    providers = []
    
    if openai_key:
        openai_config = ProviderConfig(
            api_key=openai_key,
            model="dall-e-3",
            default_size="1024x1024",
            default_quality="standard"
        )
        providers.append(OpenAIProvider(openai_config))
        print("  ✅ OpenAI Provider configured")
    
    if stability_key:
        stability_config = ProviderConfig(
            api_key=stability_key,
            model="sd3",
            default_size="1:1"
        )
        providers.append(StabilityAIProvider(stability_config))
        print("  ✅ Stability AI Provider configured")
    
    # Create manager
    manager = ProviderManager(
        providers=providers,
        strategy=SelectionStrategy.CHEAPEST,
        enable_fallback=True
    )
    
    print(f"  ✅ Provider Manager created ({len(providers)} providers)\n")
    return manager


def example_single_image(manager):
    """Example 1: Generate a single image"""
    print("=" * 60)
    print("EXAMPLE 1: Single Image Generation")
    print("=" * 60)
    
    handler = SingleImageHandler(provider_manager=manager)
    
    print("\n📸 Generating image: 'A beautiful sunset over mountains'")
    
    result = handler.handle({
        'prompt': 'A beautiful sunset over mountains',
        'provider': 'auto',
        'size': '1024x1024',
        'quality': 'standard',
        'save_to_path': './output_single_image.png'
    })
    
    if result['status'] == 'success':
        print(f"✅ Success!")
        print(f"  Provider: {result['image']['provider']}")
        print(f"  Cost: ${result['total_cost_cents']/100:.3f}")
        print(f"  Time: {result['total_time_seconds']:.1f}s")
        print(f"  URL: {result['image']['url']}")
        if result['image']['revised_prompt']:
            print(f"  Revised prompt: {result['image']['revised_prompt'][:80]}...")
    else:
        print(f"❌ Failed: {result['image']['error_message']}")
    
    print()


def example_batch_images(manager):
    """Example 2: Generate multiple images"""
    print("=" * 60)
    print("EXAMPLE 2: Batch Image Generation")
    print("=" * 60)
    
    handler = BatchImageHandler(provider_manager=manager)
    
    prompts = [
        'A red apple on a wooden table',
        'A blue ocean with waves',
        'A green forest in autumn'
    ]
    
    print(f"\n📸 Generating {len(prompts)} images:")
    for i, prompt in enumerate(prompts, 1):
        print(f"  {i}. {prompt}")
    
    result = handler.handle({
        'prompts': prompts,
        'distribute_load': True,
        'provider': 'auto',
        'quality': 'standard',
        'save_to_directory': './output_batch',
        'naming_pattern': 'image_{index:02d}.png'
    })
    
    print(f"\n✅ Batch completed!")
    print(f"  Success rate: {result['success_rate']:.1f}%")
    print(f"  Successful: {result['total_successful']}/{result['total_requested']}")
    print(f"  Total cost: ${result['total_cost_cents']/100:.3f}")
    print(f"  Total time: {result['total_time_seconds']:.1f}s")
    print(f"  Avg per image: {result['average_time_per_image']:.1f}s")
    
    print("\n  Provider distribution:")
    for provider, count in result['provider_distribution'].items():
        print(f"    {provider}: {count} images")
    
    print()


def example_cost_estimation(manager):
    """Example 3: Cost estimation"""
    print("=" * 60)
    print("EXAMPLE 3: Cost Estimation")
    print("=" * 60)
    
    print("\n💰 Estimating costs for different scenarios:")
    
    # Single image
    cost_single = manager.estimate_cost(num_images=1)
    print(f"  1 image: ${cost_single/100:.3f}")
    
    # Book illustrations (36 images)
    cost_book = manager.estimate_cost(num_images=36)
    print(f"  36 images (book): ${cost_book/100:.2f}")
    
    # Large batch
    cost_large = manager.estimate_cost(num_images=100)
    print(f"  100 images: ${cost_large/100:.2f}")
    
    print()


def example_illustration_handler(manager):
    """Example 4: Educational book illustrations"""
    print("=" * 60)
    print("EXAMPLE 4: Educational Book Illustrations")
    print("=" * 60)
    
    handler = IllustrationGenerationHandler(
        provider_manager=manager,
        config={'save_images': True}
    )
    
    # Estimate cost first
    cost = handler.estimate_cost(num_illustrations=3)
    print(f"\n💰 Estimated cost for 3 illustrations: ${cost/100:.3f}")
    
    print("\n📚 Generating illustrations for 'Brain Island Adventure':")
    print("  - Scene 1: Max and Mia arriving at Brain Island")
    print("  - Scene 2: Solving a colorful puzzle together")
    print("  - Scene 3: Celebration with Brainy the owl")
    
    # Note: This would actually generate images, so we'll skip in example
    print("\n⏭️  Skipped actual generation (would cost money)")
    print("   To run: Remove the return statement in this function")
    
    return  # Remove this line to actually generate
    
    result = handler.handle({
        'book_id': 1,
        'chapter_id': 1,
        'scene_descriptions': [
            'Max and Mia, two children, arriving at a magical island shaped like a brain, watercolor style',
            'Children solving a colorful jigsaw puzzle together, showing teamwork, watercolor style',
            'Happy celebration scene with a friendly blue owl wearing glasses, watercolor style'
        ],
        'illustration_style': 'watercolor children\'s book illustration',
        'character_descriptions': {
            'Max': 'boy with brown hair, blue shirt, curious expression',
            'Mia': 'girl with blonde hair, red dress, excited smile',
            'Brainy': 'friendly blue owl with large glasses'
        },
        'aspect_ratio': '16:9',
        'save_to_directory': './output_illustrations',
        'provider': 'openai',
        'ensure_consistency': True
    })
    
    print(f"\n✅ Illustrations generated!")
    print(f"  Success: {result['successful_illustrations']}/{result['total_scenes']}")
    print(f"  Cost: ${result['total_cost_cents']/100:.2f}")
    print(f"  Time: {result['total_time_seconds']:.1f}s")
    print(f"  Saved to: {result['illustration_directory']}")
    
    print()


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("🎨 BF Agent Image Generation System - Quick Start")
    print("=" * 60 + "\n")
    
    # Check environment
    openai_key, stability_key = check_environment()
    
    # Setup providers
    manager = setup_providers(openai_key, stability_key)
    
    # Check provider health
    print("🏥 Checking provider health...")
    statuses = manager.health_check()
    for provider, status in statuses.items():
        icon = "✅" if status.value == "available" else "❌"
        print(f"  {icon} {provider}: {status.value}")
    print()
    
    # Run examples
    try:
        # Example 1: Single image
        example_single_image(manager)
        
        # Example 2: Batch images
        example_batch_images(manager)
        
        # Example 3: Cost estimation
        example_cost_estimation(manager)
        
        # Example 4: Illustration handler
        example_illustration_handler(manager)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Show final metrics
    print("=" * 60)
    print("📊 Session Metrics")
    print("=" * 60)
    
    metrics = manager.get_metrics()
    print(f"\nTotal requests: {metrics['total_requests']}")
    print(f"Total successful: {metrics['total_successful']}")
    print(f"Total failed: {metrics['total_failed']}")
    print(f"Total cost: ${metrics['total_cost_cents']/100:.2f}")
    
    print("\nProvider breakdown:")
    for provider, stats in metrics['providers'].items():
        print(f"  {provider}:")
        print(f"    Requests: {stats['requests']}")
        print(f"    Success rate: {stats['success_rate']}%")
        print(f"    Avg time: {stats['avg_time']:.1f}s")
        print(f"    Cost: ${stats['total_cost_cents']/100:.2f}")
    
    print("\n" + "=" * 60)
    print("✅ Quick Start completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
