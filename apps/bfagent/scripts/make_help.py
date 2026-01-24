"""
BF Agent - Enterprise Makefile Documentation System
Scans Makefiles and generates beautiful CLI help documentation

Usage:
    python scripts/make_help.py              # Show tree view
    python scripts/make_help.py table        # Show table view
    python scripts/make_help.py search -q django  # Search commands
    python scripts/make_help.py category -c dev   # Show category
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class MakeCommand:
    """Represents a Makefile command with metadata"""
    name: str
    description: str
    category: str = "other"
    subcategory: str = ""
    file: str = ""
    line_number: int = 0


class MakefileDocGenerator:
    """Generates documentation from Makefile comments"""
    
    # Category definitions with icons and display names
    CATEGORIES = {
        "project": {"icon": "📦", "name": "PROJECT MANAGEMENT"},
        "dev": {"icon": "🚀", "name": "DEVELOPMENT"},
        "test": {"icon": "🧪", "name": "TESTING & QUALITY"},
        "db": {"icon": "🗄️", "name": "DATABASE"},
        "frontend": {"icon": "🎨", "name": "FRONTEND & DESIGN"},
        "agent": {"icon": "🤖", "name": "AI & AGENTS"},
        "monitor": {"icon": "📊", "name": "MONITORING & LOGS"},
        "maintenance": {"icon": "🔧", "name": "MAINTENANCE"},
        "other": {"icon": "📋", "name": "OTHER COMMANDS"}
    }
    
    # Subcategory definitions
    SUBCATEGORIES = {
        "project": ["Setup", "Quick Actions", "Cleanup"],
        "dev": ["Server", "Code Quality", "Analysis"],
        "test": ["Test Execution", "Quality Assurance", "Reports"],
        "db": ["Migrations", "Backup & Restore", "Management"],
        "frontend": ["Styling", "Validation"],
        "agent": ["Agent Management", "Actions"],
        "monitor": ["Performance", "Logs"],
        "maintenance": ["Updates", "Cleanup"]
    }
    
    def __init__(self):
        self.commands: List[MakeCommand] = []
        self.makefiles = [
            Path("Makefile"),
            Path("Makefile.quick"),
            Path("Makefile.agents")
        ]
    
    def scan_makefiles(self) -> None:
        """Scan all Makefiles for documented commands"""
        for makefile in self.makefiles:
            if makefile.exists():
                self._parse_makefile(makefile)
        
        # Sort commands by category and name
        self.commands.sort(key=lambda x: (x.category, x.subcategory, x.name))
    
    def _parse_makefile(self, path: Path) -> None:
        """Parse a single Makefile for commands"""
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: Could not read {path}: {e}")
            return
        
        # Pattern: command: ## description @category:cat @sub:subcat
        # Example: dev: ## Start development server @category:dev @sub:Server
        pattern = r'^([a-zA-Z_-]+):\s*##\s*(.+?)(?:\s+@category:(\w+))?(?:\s+@sub:([\w\s&]+))?$'
        
        for line_num, line in enumerate(content.split('\n'), 1):
            match = re.match(pattern, line)
            if match:
                cmd = MakeCommand(
                    name=match.group(1),
                    description=match.group(2).strip(),
                    category=match.group(3) or "other",
                    subcategory=match.group(4).strip() if match.group(4) else "",
                    file=path.name,
                    line_number=line_num
                )
                self.commands.append(cmd)
    
    def _group_by_category(self) -> Dict[str, List[MakeCommand]]:
        """Group commands by category"""
        grouped = defaultdict(list)
        for cmd in self.commands:
            grouped[cmd.category].append(cmd)
        return dict(grouped)
    
    def _group_by_subcategory(self, commands: List[MakeCommand]) -> Dict[str, List[MakeCommand]]:
        """Group commands by subcategory"""
        grouped = defaultdict(list)
        for cmd in commands:
            grouped[cmd.subcategory].append(cmd)
        return dict(grouped)
    
    def show_tree(self) -> None:
        """Display commands in hierarchical tree view"""
        print("\n" + "=" * 70)
        print("  📋 BF AGENT - MAKEFILE COMMAND REFERENCE")
        print("=" * 70 + "\n")
        
        categories = self._group_by_category()
        
        for cat_key in self.CATEGORIES.keys():
            if cat_key not in categories:
                continue
            
            cat_info = self.CATEGORIES[cat_key]
            print(f"{cat_info['icon']} {cat_info['name']}")
            
            # Group by subcategory
            subcats = self._group_by_subcategory(categories[cat_key])
            
            # Show commands organized by subcategory
            if any(subcats.keys()):
                for subcat_name, commands in sorted(subcats.items()):
                    if subcat_name:
                        print(f"  ├─ {subcat_name}")
                        for i, cmd in enumerate(commands):
                            prefix = "│   ├─" if i < len(commands) - 1 else "│   └─"
                            print(f"  {prefix} {cmd.name:20} {cmd.description}")
                    else:
                        for cmd in commands:
                            print(f"  ├─ {cmd.name:20} {cmd.description}")
            else:
                for cmd in categories[cat_key]:
                    print(f"  ├─ {cmd.name:20} {cmd.description}")
            print()
        
        print("=" * 70)
        print(f"Total Commands: {len(self.commands)}")
        print("\nUsage Examples:")
        print("  make help                    # Show this overview")
        print("  python scripts/make_help.py table           # Table view")
        print("  python scripts/make_help.py search -q test  # Search commands")
        print("  python scripts/make_help.py category -c dev # Show dev commands")
        print("=" * 70 + "\n")
    
    def show_table(self, category: Optional[str] = None) -> None:
        """Display commands in table format"""
        print("\n" + "=" * 90)
        print("  BF AGENT - MAKEFILE COMMANDS")
        print("=" * 90)
        
        # Filter by category if specified
        commands = self.commands
        if category:
            commands = [c for c in commands if c.category == category]
            cat_info = self.CATEGORIES.get(category, {"icon": "📋", "name": category.upper()})
            print(f"\nCategory: {cat_info['icon']} {cat_info['name']}\n")
        
        print(f"\n{'COMMAND':<25} {'DESCRIPTION':<40} {'CATEGORY':<15}")
        print("-" * 90)
        
        for cmd in commands:
            cat_icon = self.CATEGORIES.get(cmd.category, {}).get("icon", "📋")
            print(f"{cmd.name:<25} {cmd.description[:40]:<40} {cat_icon} {cmd.category:<12}")
        
        print("-" * 90)
        print(f"Total: {len(commands)} commands\n")
    
    def search(self, query: str) -> None:
        """Search commands by name or description"""
        query = query.lower()
        results = [
            cmd for cmd in self.commands
            if query in cmd.name.lower() or query in cmd.description.lower()
        ]
        
        print("\n" + "=" * 70)
        print(f"  SEARCH RESULTS for '{query}'")
        print("=" * 70 + "\n")
        
        if results:
            print(f"Found {len(results)} matching commands:\n")
            for cmd in results:
                cat_info = self.CATEGORIES.get(cmd.category, {})
                cat_icon = cat_info.get("icon", "📋")
                print(f"  {cat_icon} make {cmd.name:<25} # {cmd.description}")
                print(f"     Category: {cmd.category} | File: {cmd.file}")
                print()
        else:
            print(f"No commands found matching '{query}'\n")
        
        print("=" * 70 + "\n")
    
    def show_category(self, category: str) -> None:
        """Show all commands in a specific category"""
        if category not in self.CATEGORIES:
            print(f"\nError: Unknown category '{category}'")
            print(f"Available categories: {', '.join(self.CATEGORIES.keys())}\n")
            return
        
        cat_info = self.CATEGORIES[category]
        commands = [c for c in self.commands if c.category == category]
        
        print("\n" + "=" * 70)
        print(f"  {cat_info['icon']} {cat_info['name']}")
        print("=" * 70 + "\n")
        
        if not commands:
            print("  No commands found in this category.\n")
            return
        
        # Group by subcategory
        subcats = self._group_by_subcategory(commands)
        
        for subcat_name, subcat_commands in sorted(subcats.items()):
            if subcat_name:
                print(f"  {subcat_name}:")
            
            for cmd in subcat_commands:
                print(f"    make {cmd.name:<25} # {cmd.description}")
            print()
        
        print("=" * 70 + "\n")
    
    def show_stats(self) -> None:
        """Show statistics about Makefile commands"""
        print("\n" + "=" * 70)
        print("  MAKEFILE STATISTICS")
        print("=" * 70 + "\n")
        
        print(f"Total Commands: {len(self.commands)}")
        print(f"Makefiles Scanned: {sum(1 for mf in self.makefiles if mf.exists())}")
        print("\nCommands by Category:")
        
        categories = self._group_by_category()
        for cat_key in sorted(categories.keys()):
            cat_info = self.CATEGORIES.get(cat_key, {"icon": "📋", "name": cat_key})
            count = len(categories[cat_key])
            print(f"  {cat_info['icon']} {cat_info['name']:<30} {count:>3} commands")
        
        print("\n" + "=" * 70 + "\n")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="BF Agent Makefile Documentation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/make_help.py                  # Show tree view
  python scripts/make_help.py table            # Show table view  
  python scripts/make_help.py search -q test   # Search for 'test'
  python scripts/make_help.py category -c dev  # Show dev commands
  python scripts/make_help.py stats            # Show statistics
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        choices=["tree", "table", "search", "category", "stats"],
        default="tree",
        help="Display mode (default: tree)"
    )
    parser.add_argument(
        "-q", "--query",
        help="Search query for 'search' command"
    )
    parser.add_argument(
        "-c", "--category",
        choices=list(MakefileDocGenerator.CATEGORIES.keys()),
        help="Category filter for 'category' or 'table' command"
    )
    
    args = parser.parse_args()
    
    # Initialize and scan
    doc = MakefileDocGenerator()
    doc.scan_makefiles()
    
    if not doc.commands:
        print("\nWarning: No documented commands found!")
        print("Add documentation to Makefile commands using:")
        print("  command: ## Description @category:dev @sub:Server\n")
        return 1
    
    # Execute command
    if args.command == "tree":
        doc.show_tree()
    elif args.command == "table":
        doc.show_table(args.category)
    elif args.command == "search":
        if not args.query:
            print("\nError: Search requires -q/--query parameter\n")
            return 1
        doc.search(args.query)
    elif args.command == "category":
        if not args.category:
            print("\nError: Category command requires -c/--category parameter\n")
            return 1
        doc.show_category(args.category)
    elif args.command == "stats":
        doc.show_stats()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
