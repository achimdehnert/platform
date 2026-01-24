"""
Story Outline Generator using proven Story Frameworks

Generates structured outlines based on:
- Hero's Journey
- Save the Cat Beat Sheet
- Three-Act Structure

Usage:
    python generate_outline.py --framework heros_journey --title "My Story" --genre Fantasy --chapters 12
"""

import os
import sys
import django
import argparse

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.services.story_frameworks import (
    list_frameworks,
    generate_outline_from_framework,
    get_framework
)


def main():
    parser = argparse.ArgumentParser(
        description='Generate story outline using proven frameworks'
    )
    
    parser.add_argument('--framework', type=str, 
                       choices=['heros_journey', 'save_the_cat', 'three_act'],
                       default='heros_journey',
                       help='Story framework to use')
    parser.add_argument('--title', type=str, required=True, help='Story title')
    parser.add_argument('--genre', type=str, default='Fiction', help='Story genre')
    parser.add_argument('--premise', type=str, default='', help='Story premise/logline')
    parser.add_argument('--chapters', type=int, default=12, help='Number of chapters')
    parser.add_argument('--list', action='store_true', help='List available frameworks')
    parser.add_argument('--output', type=str, help='Save to file')
    
    args = parser.parse_args()
    
    # List frameworks
    if args.list:
        print("📚 Available Story Frameworks:")
        print()
        for framework in list_frameworks():
            print(f"🎭 {framework['name']} ({framework['id']})")
            print(f"   {framework['description']}")
            print(f"   Beats: {framework['beats']}")
            print()
        return
    
    # Generate outline
    print("=" * 70)
    print(f"📖 GENERATING STORY OUTLINE")
    print("=" * 70)
    print()
    
    framework = get_framework(args.framework)
    print(f"🎭 Framework: {framework.name}")
    print(f"📚 Title: {args.title}")
    print(f"🎬 Genre: {args.genre}")
    print(f"📖 Chapters: {args.chapters}")
    print()
    
    outline = generate_outline_from_framework(
        framework_name=args.framework,
        title=args.title,
        genre=args.genre,
        premise=args.premise or f"A {args.genre} story",
        num_chapters=args.chapters
    )
    
    print("=" * 70)
    print("GENERATED OUTLINE")
    print("=" * 70)
    print()
    print(outline)
    print()
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(f"# {args.title}\n\n")
            f.write(f"**Genre:** {args.genre}\n")
            f.write(f"**Framework:** {framework.name}\n")
            f.write(f"**Chapters:** {args.chapters}\n\n")
            f.write("---\n\n")
            f.write(outline)
        print(f"💾 Saved to: {args.output}")
        print()
    
    print("=" * 70)
    print("💡 NEXT STEPS")
    print("=" * 70)
    print()
    print("Use this outline to generate your book:")
    print(f"python generate_book_v2.py \\")
    print(f"    --title \"{args.title}\" \\")
    print(f"    --outline-file {args.output or 'outline.txt'} \\")
    print(f"    --llm-id 1 \\")
    print(f"    --genre {args.genre}")
    print()


if __name__ == "__main__":
    main()
