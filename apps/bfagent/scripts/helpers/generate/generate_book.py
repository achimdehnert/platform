"""
Complete Book Generator Script

Generates a full book from title and outline using the Pipeline System.
Each chapter is written separately and compiled into a final markdown book.

Usage:
    python generate_book.py --title "My Book" --outline "Chapter 1: ...\nChapter 2: ..." --llm-id 1
    
    # Interactive mode
    python generate_book.py --interactive
    
    # From file
    python generate_book.py --title "My Book" --outline-file outline.txt --llm-id 1
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

from apps.bfagent.models import BookProjects, Llms, Agents
from apps.bfagent.services.project_enrichment import run_enrichment


class BookGenerator:
    """
    Complete Book Generator using Pipeline System
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
        self.chapters_per_run = options.get('chapters_per_run', 1)
        self.words_per_chapter = options.get('words_per_chapter', 3000)
        self.temperature = options.get('temperature', 0.8)
        self.genre = options.get('genre', 'Fiction')
        self.style = options.get('style', 'engaging and descriptive')
        
        # Parse outline into chapters
        self.chapters = self._parse_outline(outline)
        
        # Get LLM
        try:
            self.llm = Llms.objects.get(id=llm_id, is_active=True)
        except Llms.DoesNotExist:
            raise ValueError(f"LLM with id {llm_id} not found or inactive")
        
        # Get or create a Writer Agent for book generation
        self.agent = self._get_or_create_writer_agent()
        
        print(f"📚 Book Generator Initialized")
        print(f"   Title: {self.title}")
        print(f"   Chapters: {len(self.chapters)}")
        print(f"   LLM: {self.llm.llm_name} ({self.llm.provider})")
        print(f"   Agent: {self.agent.name}")
        print()
    
    def _get_or_create_writer_agent(self) -> Agents:
        """
        Get or create a Writer Agent for book generation
        
        Returns:
            Agents: Writer agent instance
        """
        # Try to find existing writer agent
        agent = Agents.objects.filter(
            agent_type='writer_agent',
            is_active=True
        ).first()
        
        if not agent:
            # Create a basic writer agent
            agent = Agents.objects.create(
                name="Book Writer Agent",
                agent_type="writer_agent",
                system_prompt="You are a professional author. Write engaging, vivid prose with good pacing and character development.",
                description="Automated agent for book chapter generation",
                is_active=True,
                llm_model_id=self.llm.id
            )
            print(f"   ✅ Created new Writer Agent: {agent.name}")
        
        return agent
    
    def _parse_outline(self, outline: str) -> list:
        """
        Parse outline into chapter list
        
        Args:
            outline: Outline text
            
        Returns:
            list: List of chapter dicts with title and description
        """
        chapters = []
        lines = outline.strip().split('\n')
        
        current_chapter = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a chapter heading
            if line.lower().startswith('chapter') or line.startswith('#'):
                # Save previous chapter
                if current_chapter:
                    chapters.append(current_chapter)
                
                # Start new chapter
                chapter_title = line.replace('#', '').strip()
                current_chapter = {
                    'title': chapter_title,
                    'description': ''
                }
            elif current_chapter:
                # Add to current chapter description
                current_chapter['description'] += line + ' '
        
        # Add last chapter
        if current_chapter:
            chapters.append(current_chapter)
        
        # If no chapters found, create single chapter
        if not chapters:
            chapters = [{
                'title': 'Chapter 1',
                'description': outline
            }]
        
        return chapters
    
    def _generate_chapter_prompt(self, chapter_num: int, chapter: dict) -> str:
        """
        Generate prompt for chapter writing
        
        Args:
            chapter_num: Chapter number
            chapter: Chapter dict
            
        Returns:
            str: Prompt for LLM
        """
        prompt = f"""You are a professional author writing a book titled "{self.title}".

**Book Information:**
- Title: {self.title}
- Genre: {self.genre}
- Writing Style: {self.style}
- Target Length: {self.words_per_chapter} words per chapter

**Full Book Outline:**
{self._format_outline()}

**Current Chapter to Write:**
Chapter {chapter_num}: {chapter['title']}
Description: {chapter['description']}

**Instructions:**
1. Write Chapter {chapter_num} with approximately {self.words_per_chapter} words
2. Use vivid descriptions and engaging prose
3. Include dialogue where appropriate
4. Maintain consistency with the overall story arc
5. End with a hook to the next chapter (if not the last chapter)
6. Format as markdown with proper headings

**Previous Context:**
{self._get_previous_context(chapter_num)}

Write the complete chapter now:
"""
        return prompt
    
    def _format_outline(self) -> str:
        """Format outline for context"""
        lines = []
        for i, chapter in enumerate(self.chapters, 1):
            lines.append(f"Chapter {i}: {chapter['title']}")
            if chapter['description']:
                lines.append(f"  → {chapter['description'][:100]}...")
        return '\n'.join(lines)
    
    def _get_previous_context(self, chapter_num: int) -> str:
        """Get context from previous chapters"""
        if chapter_num == 1:
            return "This is the first chapter. Set the scene and introduce main characters."
        elif chapter_num == len(self.chapters):
            return "This is the final chapter. Bring the story to a satisfying conclusion."
        else:
            return f"This is chapter {chapter_num} of {len(self.chapters)}. Continue the story arc."
    
    def generate_chapter(self, chapter_num: int, chapter: dict) -> dict:
        """
        Generate a single chapter
        
        Args:
            chapter_num: Chapter number
            chapter: Chapter dict
            
        Returns:
            dict: Generated chapter data
        """
        print(f"📝 Generating Chapter {chapter_num}/{len(self.chapters)}: {chapter['title']}")
        print(f"   Estimated words: {self.words_per_chapter}")
        
        # Create prompt
        prompt = self._generate_chapter_prompt(chapter_num, chapter)
        
        # Get LLM handler
        LLMHandler = ProcessingHandlerRegistry.get("llm_processor")
        llm_handler = LLMHandler(config={
            "llm_id": self.llm_id,
            "temperature": self.temperature,
            "max_tokens": self.words_per_chapter * 2  # Roughly 2 tokens per word
        })
        
        # Process
        try:
            result = llm_handler.process(
                data={"prompt": prompt},
                context={"chapter_num": chapter_num}
            )
            
            print(f"   ✅ Generated: {result['tokens_used']} tokens, ${result['generation_cost']:.4f}")
            print(f"   ⏱️  Time: {result['execution_time_ms']}ms")
            print()
            
            return {
                'chapter_num': chapter_num,
                'title': chapter['title'],
                'content': result['generated_content'],
                'tokens': result['tokens_used'],
                'cost': result['generation_cost'],
                'time_ms': result['execution_time_ms']
            }
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def save_chapter(self, chapter_data: dict) -> str:
        """
        Save chapter to file
        
        Args:
            chapter_data: Chapter data
            
        Returns:
            str: File path
        """
        # Get Markdown handler
        MDHandler = OutputHandlerRegistry.get("markdown_file_writer")
        md_handler = MDHandler(config={
            "output_dir": f"{self.output_dir}/{self._sanitize_title(self.title)}/chapters",
            "filename_template": f"chapter_{chapter_data['chapter_num']:02d}_{{timestamp}}.md",
            "create_backup": False,
            "add_frontmatter": True
        })
        
        # Prepare data
        processed_data = {
            'generated_content': chapter_data['content'],
            'llm_name': self.llm.llm_name,
            'tokens_used': chapter_data['tokens'],
            'generation_cost': chapter_data['cost']
        }
        
        context = {
            'project': None,
            'action_name': 'book_generation'
        }
        
        # Save
        result = md_handler.handle(processed_data, context)
        
        print(f"   💾 Saved: {result['filename']}")
        return result['file_path']
    
    def compile_book(self, chapter_files: list) -> str:
        """
        Compile all chapters into complete book
        
        Args:
            chapter_files: List of chapter file paths
            
        Returns:
            str: Path to complete book file
        """
        print()
        print("📖 Compiling complete book...")
        
        # Create output directory
        output_dir = Path(self.output_dir) / self._sanitize_title(self.title)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create complete book file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        book_file = output_dir / f"{self._sanitize_title(self.title)}_complete_{timestamp}.md"
        
        # Compile content
        with open(book_file, 'w', encoding='utf-8') as f:
            # Write title page
            f.write(f"# {self.title}\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**LLM:** {self.llm.llm_name}\n")
            f.write(f"**Chapters:** {len(chapter_files)}\n\n")
            f.write("---\n\n")
            
            # Write table of contents
            f.write("## Table of Contents\n\n")
            for i, chapter in enumerate(self.chapters, 1):
                f.write(f"{i}. {chapter['title']}\n")
            f.write("\n---\n\n")
            
            # Write chapters
            for i, chapter_file in enumerate(chapter_files, 1):
                chapter_path = Path(chapter_file)
                if chapter_path.exists():
                    content = chapter_path.read_text(encoding='utf-8')
                    
                    # Remove frontmatter
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            content = parts[2].strip()
                    
                    f.write(f"\n\n{content}\n\n")
                    
                    if i < len(chapter_files):
                        f.write("---\n\n")
        
        print(f"   ✅ Complete book saved: {book_file}")
        return str(book_file)
    
    def _sanitize_title(self, title: str) -> str:
        """Sanitize title for filename"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '_')
        return title.replace(' ', '_').strip('_')[:50]
    
    def generate_book(self) -> dict:
        """
        Generate complete book
        
        Returns:
            dict: Generation results with statistics
        """
        print("=" * 70)
        print(f"🚀 STARTING BOOK GENERATION: {self.title}")
        print("=" * 70)
        print()
        
        chapter_files = []
        total_tokens = 0
        total_cost = 0.0
        total_time_ms = 0
        
        # Generate each chapter
        for i, chapter in enumerate(self.chapters, 1):
            chapter_data = self.generate_chapter(i, chapter)
            
            if chapter_data:
                # Save chapter
                file_path = self.save_chapter(chapter_data)
                chapter_files.append(file_path)
                
                # Update stats
                total_tokens += chapter_data['tokens']
                total_cost += float(chapter_data['cost'])
                total_time_ms += chapter_data['time_ms']
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
        print(f"   🪙 Total Tokens: {total_tokens:,}")
        print(f"   💰 Total Cost: ${total_cost:.4f}")
        print(f"   ⏱️  Total Time: {total_time_ms/1000:.1f}s")
        print(f"   📁 Book File: {book_file}")
        print()
        
        return {
            'title': self.title,
            'chapters_generated': len(chapter_files),
            'total_chapters': len(self.chapters),
            'book_file': book_file,
            'chapter_files': chapter_files,
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'total_time_ms': total_time_ms
        }


def interactive_mode():
    """Interactive mode for book generation"""
    print("📚 Interactive Book Generator")
    print("=" * 70)
    print()
    
    # Get title
    title = input("📖 Book Title: ").strip()
    if not title:
        print("❌ Title is required")
        return
    
    # Get genre
    genre = input("🎭 Genre (default: Fiction): ").strip() or "Fiction"
    
    # Get outline
    print()
    print("📝 Enter book outline (one chapter per line, press Ctrl+Z then Enter when done):")
    print("   Example:")
    print("   Chapter 1: The Beginning - Hero discovers their power")
    print("   Chapter 2: The Challenge - First obstacle appears")
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
    
    # Options
    words = input("Words per chapter (default: 3000): ").strip() or "3000"
    words = int(words)
    
    temp = input("Temperature (default: 0.8): ").strip() or "0.8"
    temp = float(temp)
    
    # Generate
    print()
    generator = BookGenerator(
        title=title,
        outline=outline,
        llm_id=llm_id,
        genre=genre,
        words_per_chapter=words,
        temperature=temp
    )
    
    result = generator.generate_book()
    return result


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate a complete book from title and outline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--title', type=str, help='Book title')
    parser.add_argument('--outline', type=str, help='Book outline (chapter structure)')
    parser.add_argument('--outline-file', type=str, help='Path to outline file')
    parser.add_argument('--llm-id', type=int, help='LLM ID to use')
    parser.add_argument('--genre', type=str, default='Fiction', help='Book genre')
    parser.add_argument('--words-per-chapter', type=int, default=3000, help='Target words per chapter')
    parser.add_argument('--temperature', type=float, default=0.8, help='LLM temperature')
    parser.add_argument('--output-dir', type=str, default='books/generated', help='Output directory')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    # Interactive mode
    if args.interactive or (not args.title and not args.outline):
        result = interactive_mode()
        return
    
    # Validate arguments
    if not args.title:
        print("❌ Error: --title is required")
        sys.exit(1)
    
    if not args.outline and not args.outline_file:
        print("❌ Error: Either --outline or --outline-file is required")
        sys.exit(1)
    
    if not args.llm_id:
        print("❌ Error: --llm-id is required")
        sys.exit(1)
    
    # Load outline from file if specified
    outline = args.outline
    if args.outline_file:
        outline_path = Path(args.outline_file)
        if not outline_path.exists():
            print(f"❌ Error: Outline file not found: {args.outline_file}")
            sys.exit(1)
        outline = outline_path.read_text(encoding='utf-8')
    
    # Generate book
    generator = BookGenerator(
        title=args.title,
        outline=outline,
        llm_id=args.llm_id,
        genre=args.genre,
        words_per_chapter=args.words_per_chapter,
        temperature=args.temperature,
        output_dir=args.output_dir
    )
    
    result = generator.generate_book()


if __name__ == "__main__":
    main()
