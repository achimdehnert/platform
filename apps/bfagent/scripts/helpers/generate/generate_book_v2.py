"""
Complete Book Generator V2 - Uses existing BF Agent run_enrichment system

Generates a full book from title and outline using the existing Agent/LLM infrastructure.

Usage:
    python generate_book_v2.py --interactive
"""

import os
import sys
import django
import argparse
from pathlib import Path
from datetime import datetime

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import Llms
from apps.bfagent.services.llm_client import LlmRequest, generate_text


class BookGeneratorV2:
    """
    Complete Book Generator using existing BF Agent system
    """
    
    def __init__(self, title: str, outline: str, llm_id: int, **options):
        """
        Initialize book generator
        
        Args:
            title: Book title
            outline: Book outline (chapter structure)
            llm_id: LLM to use for generation
            **options: Additional options
        """
        self.title = title
        self.outline = outline
        self.llm_id = llm_id
        self.output_dir = options.get('output_dir', 'books/generated')
        self.words_per_chapter = options.get('words_per_chapter', 3000)
        self.genre = options.get('genre', 'Fiction')
        self.style = options.get('style', 'engaging and descriptive')
        
        # Parse outline into chapters
        self.chapters = self._parse_outline(outline)
        
        # Get LLM
        try:
            self.llm = Llms.objects.get(id=llm_id, is_active=True)
        except Llms.DoesNotExist:
            raise ValueError(f"LLM with id {llm_id} not found or inactive")
        
        print(f"📚 Book Generator V2 Initialized (using llm_client)")
        print(f"   Title: {self.title}")
        print(f"   Chapters: {len(self.chapters)}")
        print(f"   LLM: {self.llm.llm_name} ({self.llm.provider})")
        print()
    
    def _parse_outline(self, outline: str) -> list:
        """Parse outline into chapter list"""
        chapters = []
        lines = outline.strip().split('\n')
        
        current_chapter = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a chapter heading
            if line.lower().startswith('chapter') or line.startswith('#'):
                if current_chapter:
                    chapters.append(current_chapter)
                
                chapter_title = line.replace('#', '').strip()
                current_chapter = {
                    'title': chapter_title,
                    'description': ''
                }
            elif current_chapter:
                current_chapter['description'] += line + ' '
        
        if current_chapter:
            chapters.append(current_chapter)
        
        if not chapters:
            chapters = [{'title': 'Chapter 1', 'description': outline}]
        
        return chapters
    
    def generate_chapter(self, chapter_num: int, chapter: dict) -> dict:
        """
        Generate a single chapter using run_enrichment
        
        Args:
            chapter_num: Chapter number
            chapter: Chapter dict
            
        Returns:
            dict: Generated chapter data
        """
        print(f"📝 Generating Chapter {chapter_num}/{len(self.chapters)}: {chapter['title']}")
        print(f"   Using llm_client.generate_text()")
        
        # Build prompt for this chapter
        system_prompt = "You are a professional author. Write engaging, vivid prose with good pacing, rich descriptions, and natural dialogue."
        
        user_prompt = f"""Generate a complete chapter for the book "{self.title}".

**Chapter Information:**
Chapter {chapter_num}: {chapter['title']}
Description: {chapter['description']}

**Book Context:**
- Genre: {self.genre}
- Style: {self.style}
- Target Length: {self.words_per_chapter} words

**Full Outline:**
{self._format_outline()}

**Instructions:**
Write Chapter {chapter_num} with approximately {self.words_per_chapter} words. 
Use vivid descriptions, engaging prose, and natural dialogue.
Format as markdown with proper headings.

Previous Context: {self._get_previous_context(chapter_num)}

Write the complete chapter now:
"""
        
        try:
            # Create LLM request
            llm_request = LlmRequest(
                provider=self.llm.provider,
                api_endpoint=self.llm.api_endpoint,
                api_key=self.llm.api_key,
                model=self.llm.llm_name,
                system=system_prompt,
                prompt=user_prompt,
                temperature=self.llm.temperature or 0.8,
                top_p=self.llm.top_p or 1.0,
                max_tokens=self.llm.max_tokens or (self.words_per_chapter * 2)
            )
            
            # Call LLM
            response = generate_text(llm_request)
            
            # Check if successful
            if not response.get('ok'):
                error_msg = response.get('error', 'Unknown error')
                print(f"   ❌ Error: {error_msg}")
                return None
            
            generated_content = response.get('text', '')
            latency_ms = response.get('latency_ms', 0)
            
            # Estimate tokens and cost
            tokens = len(generated_content.split()) * 1.3
            cost = tokens * (self.llm.cost_per_1k_tokens / 1000)
            
            print(f"   ✅ Generated: ~{int(tokens)} tokens, ${cost:.4f}")
            print(f"   ⏱️  Time: {latency_ms}ms")
            print()
            
            return {
                'chapter_num': chapter_num,
                'title': chapter['title'],
                'content': generated_content,
                'tokens': int(tokens),
                'cost': cost,
                'time_ms': latency_ms
            }
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_outline(self) -> str:
        """Format outline for context"""
        lines = []
        for i, chapter in enumerate(self.chapters, 1):
            lines.append(f"Chapter {i}: {chapter['title']}")
            if chapter['description']:
                lines.append(f"  → {chapter['description'][:100]}...")
        return '\n'.join(lines)
    
    def _get_previous_context(self, chapter_num: int) -> str:
        """Get context based on chapter position"""
        if chapter_num == 1:
            return "This is the first chapter. Set the scene and introduce main characters."
        elif chapter_num == len(self.chapters):
            return "This is the final chapter. Bring the story to a satisfying conclusion."
        else:
            return f"This is chapter {chapter_num} of {len(self.chapters)}. Continue the story arc."
    
    def save_chapter(self, chapter_data: dict) -> str:
        """Save chapter to markdown file"""
        output_dir = Path(self.output_dir) / self._sanitize_title(self.title) / 'chapters'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chapter_{chapter_data['chapter_num']:02d}_{timestamp}.md"
        file_path = output_dir / filename
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# {chapter_data['title']}\n\n")
            f.write(chapter_data['content'])
        
        print(f"   💾 Saved: {filename}")
        return str(file_path)
    
    def compile_book(self, chapter_files: list) -> str:
        """Compile all chapters into complete book"""
        print()
        print("📖 Compiling complete book...")
        
        output_dir = Path(self.output_dir) / self._sanitize_title(self.title)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        book_file = output_dir / f"{self._sanitize_title(self.title)}_complete_{timestamp}.md"
        
        # Compile content
        with open(book_file, 'w', encoding='utf-8') as f:
            # Title page
            f.write(f"# {self.title}\n\n")
            f.write(f"**Genre:** {self.genre}\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**LLM:** {self.llm.llm_name}\n")
            f.write(f"**Chapters:** {len(chapter_files)}\n\n")
            f.write("---\n\n")
            
            # Table of contents
            f.write("## Table of Contents\n\n")
            for i, chapter in enumerate(self.chapters, 1):
                f.write(f"{i}. {chapter['title']}\n")
            f.write("\n---\n\n")
            
            # Write chapters
            for i, chapter_file in enumerate(chapter_files, 1):
                chapter_path = Path(chapter_file)
                if chapter_path.exists():
                    content = chapter_path.read_text(encoding='utf-8')
                    f.write(f"\n\n{content}\n\n")
                    
                    if i < len(chapter_files):
                        f.write("---\n\n")
        
        print(f"   ✅ Complete book saved: {book_file.name}")
        return str(book_file)
    
    def _sanitize_title(self, title: str) -> str:
        """Sanitize title for filename"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '_')
        return title.replace(' ', '_').strip('_')[:50]
    
    def generate_book(self) -> dict:
        """Generate complete book"""
        print("=" * 70)
        print(f"🚀 STARTING BOOK GENERATION: {self.title}")
        print("=" * 70)
        print()
        
        chapter_files = []
        total_tokens = 0
        total_cost = 0.0
        
        # Generate each chapter
        for i, chapter in enumerate(self.chapters, 1):
            chapter_data = self.generate_chapter(i, chapter)
            
            if chapter_data:
                file_path = self.save_chapter(chapter_data)
                chapter_files.append(file_path)
                
                total_tokens += chapter_data['tokens']
                total_cost += float(chapter_data['cost'])
            else:
                print(f"   ⚠️  Skipping chapter {i} due to error")
        
        # Compile complete book
        book_file = self.compile_book(chapter_files)
        
        # Print summary
        print()
        print("=" * 70)
        print("✅ BOOK GENERATION COMPLETE!")
        print("=" * 70)
        print(f"   📚 Title: {self.title}")
        print(f"   📖 Chapters: {len(chapter_files)}/{len(self.chapters)}")
        print(f"   🪙 Total Tokens: ~{total_tokens:,}")
        print(f"   💰 Total Cost: ~${total_cost:.4f}")
        print(f"   📁 Book File: {book_file}")
        print()
        
        return {
            'title': self.title,
            'chapters_generated': len(chapter_files),
            'total_chapters': len(self.chapters),
            'book_file': book_file,
            'chapter_files': chapter_files,
            'total_tokens': total_tokens,
            'total_cost': total_cost
        }


def interactive_mode():
    """Interactive mode"""
    print("📚 Interactive Book Generator V2 (Using BF Agent System)")
    print("=" * 70)
    print()
    
    title = input("📖 Book Title: ").strip()
    if not title:
        print("❌ Title is required")
        return
    
    genre = input("🎭 Genre (default: Fiction): ").strip() or "Fiction"
    
    print()
    print("📝 Enter book outline (one chapter per line, press Ctrl+Z then Enter when done):")
    print()
    
    outline_lines = []
    try:
        while True:
            line = input()
            outline_lines.append(line)
    except EOFError:
        pass
    
    outline = '\n'.join(outline_lines)
    
    if not outline.strip():
        print("❌ Outline is required")
        return
    
    # Get LLM
    print()
    print("🤖 Available LLMs:")
    llms = Llms.objects.filter(is_active=True)
    for llm in llms:
        print(f"   {llm.id}. {llm.llm_name} ({llm.provider})")
    
    llm_id = input("\nSelect LLM ID (default: 1): ").strip() or "1"
    llm_id = int(llm_id)
    
    words = input("Words per chapter (default: 3000): ").strip() or "3000"
    words = int(words)
    
    # Generate
    print()
    generator = BookGeneratorV2(
        title=title,
        outline=outline,
        llm_id=llm_id,
        genre=genre,
        words_per_chapter=words
    )
    
    result = generator.generate_book()
    return result


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate a complete book using BF Agent system'
    )
    
    parser.add_argument('--title', type=str, help='Book title')
    parser.add_argument('--outline', type=str, help='Book outline')
    parser.add_argument('--outline-file', type=str, help='Path to outline file')
    parser.add_argument('--llm-id', type=int, help='LLM ID')
    parser.add_argument('--genre', type=str, default='Fiction', help='Genre')
    parser.add_argument('--words-per-chapter', type=int, default=3000, help='Words per chapter')
    parser.add_argument('--output-dir', type=str, default='books/generated', help='Output directory')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    if args.interactive or (not args.title and not args.outline):
        interactive_mode()
        return
    
    if not args.title or not (args.outline or args.outline_file) or not args.llm_id:
        print("❌ Error: --title, (--outline or --outline-file), and --llm-id are required")
        sys.exit(1)
    
    outline = args.outline
    if args.outline_file:
        outline_path = Path(args.outline_file)
        if not outline_path.exists():
            print(f"❌ Error: Outline file not found: {args.outline_file}")
            sys.exit(1)
        outline = outline_path.read_text(encoding='utf-8')
    
    generator = BookGeneratorV2(
        title=args.title,
        outline=outline,
        llm_id=args.llm_id,
        genre=args.genre,
        words_per_chapter=args.words_per_chapter,
        output_dir=args.output_dir
    )
    
    result = generator.generate_book()


if __name__ == "__main__":
    main()
