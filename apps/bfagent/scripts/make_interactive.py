#!/usr/bin/env python
"""
BF Agent - Interactive Makefile Command Center
Hierarchical menu system for easy command execution

Usage:
    make menu              # Interactive menu
    python scripts/make_interactive.py
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

# Django setup for potential integration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")


@dataclass
class MakeCommand:
    """Represents a Makefile command"""
    name: str
    description: str
    category: str = "other"
    subcategory: str = ""
    file: str = ""


class MakefileInteractive:
    """Interactive menu system for Makefile commands"""
    
    # Category metadata with icons and colors
    CATEGORIES = {
        "project": {"icon": "📦", "name": "Project Management", "color": "\033[34m"},
        "dev": {"icon": "🚀", "name": "Development", "color": "\033[32m"},
        "test": {"icon": "🧪", "name": "Testing & Quality", "color": "\033[35m"},
        "db": {"icon": "🗄️", "name": "Database", "color": "\033[36m"},
        "frontend": {"icon": "🎨", "name": "Frontend & Design", "color": "\033[33m"},
        "agent": {"icon": "🤖", "name": "AI & Agents", "color": "\033[95m"},
        "monitor": {"icon": "📊", "name": "Monitoring & Logs", "color": "\033[93m"},
        "maintenance": {"icon": "🔧", "name": "Maintenance", "color": "\033[91m"},
        "other": {"icon": "📋", "name": "Other Commands", "color": "\033[37m"}
    }
    
    COLOR_RESET = "\033[0m"
    COLOR_HEADER = "\033[1;96m"
    COLOR_SUCCESS = "\033[92m"
    COLOR_WARNING = "\033[93m"
    COLOR_ERROR = "\033[91m"
    COLOR_INFO = "\033[94m"
    
    def __init__(self):
        self.commands: List[MakeCommand] = []
        self.makefiles = [
            Path("Makefile"),
            Path("Makefile.quick"),
            Path("Makefile.agents")
        ]
        self._scan_makefiles()
    
    def _scan_makefiles(self) -> None:
        """Scan all Makefiles for documented commands"""
        import re
        
        for makefile in self.makefiles:
            if not makefile.exists():
                continue
            
            try:
                content = makefile.read_text(encoding="utf-8")
            except Exception:
                continue
            
            # Pattern: command: ## description @category:cat @sub:subcat
            pattern = r'^([a-zA-Z_-]+):\s*##\s*(?:.*?)\s*(.+?)(?:\s+@category:(\w+))?(?:\s+@sub:([\w\s&]+))?$'
            
            for line in content.split('\n'):
                match = re.match(pattern, line)
                if match:
                    # Extract description without emoji
                    desc = match.group(2).strip()
                    # Remove emoji at start if present
                    desc = re.sub(r'^[\U0001F000-\U0001F9FF]\s*', '', desc)
                    
                    cmd = MakeCommand(
                        name=match.group(1),
                        description=desc,
                        category=match.group(3) or "other",
                        subcategory=match.group(4).strip() if match.group(4) else "",
                        file=makefile.name
                    )
                    self.commands.append(cmd)
        
        # Sort by category and name
        self.commands.sort(key=lambda x: (x.category, x.subcategory, x.name))
    
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
    
    def _clear_screen(self) -> None:
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _print_header(self, text: str) -> None:
        """Print formatted header"""
        print(f"\n{self.COLOR_HEADER}{'=' * 70}")
        print(f"  {text}")
        print(f"{'=' * 70}{self.COLOR_RESET}\n")
    
    def _get_command_parameters(self, command_name: str) -> str:
        """Ask for command parameters if needed"""
        # Commands that commonly need PORT parameter
        port_commands = ["dev", "runserver", "reset-server", "kill-server"]
        
        # Commands that need custom parameters
        search_commands = ["help-search"]
        
        # Git commands that need MSG parameter
        git_msg_commands = ["qc", "qcp", "sync", "quick-sync"]
        
        # Git commands that need NO parameters (read-only)
        git_readonly_commands = ["git-status", "sync-no-push"]
        
        params = ""
        
        if command_name in git_readonly_commands:
            # No parameters needed - just execute
            print(f"\n{self.COLOR_INFO}ℹ️  Command benötigt keine Parameter{self.COLOR_RESET}")
            return ""
        
        elif command_name in port_commands:
            print(f"\n{self.COLOR_INFO}📝 Parameter eingeben (optional):{self.COLOR_RESET}")
            port = input("   PORT (Enter für default 8000): ").strip()
            if port and port.isdigit():
                params = f"PORT={port}"
                print(f"{self.COLOR_SUCCESS}   ✓ Port gesetzt: {port}{self.COLOR_RESET}")
        
        elif command_name in search_commands:
            print(f"\n{self.COLOR_INFO}📝 Parameter eingeben:{self.COLOR_RESET}")
            query = input("   Suchbegriff (Q): ").strip()
            if query:
                params = f'Q="{query}"'
                print(f"{self.COLOR_SUCCESS}   ✓ Suche nach: {query}{self.COLOR_RESET}")
        
        elif command_name in git_msg_commands:
            # Check if commit message file exists
            msg_file = Path("docs/COMMIT_MESSAGE_PHASE3.txt")
            use_file = False
            
            if msg_file.exists():
                print(f"\n{self.COLOR_SUCCESS}📄 Commit Message Datei gefunden:{self.COLOR_RESET}")
                print(f"   {msg_file}")
                print(f"\n   {self.COLOR_WARNING}Vorschau:{self.COLOR_RESET}")
                try:
                    preview = msg_file.read_text(encoding="utf-8").strip().split('\n')[:5]
                    for line in preview:
                        print(f"   {self.COLOR_INFO}{line}{self.COLOR_RESET}")
                    if len(msg_file.read_text(encoding="utf-8").strip().split('\n')) > 5:
                        print(f"   {self.COLOR_INFO}...{self.COLOR_RESET}")
                except Exception:
                    print(f"   {self.COLOR_ERROR}(Vorschau fehlgeschlagen){self.COLOR_RESET}")
                
                print(f"\n   {self.COLOR_INFO}Möchtest du diese Message verwenden?{self.COLOR_RESET}")
                choice = input("   (j/n oder Enter für ja): ").strip().lower()
                use_file = choice in ['', 'j', 'y', 'yes', 'ja']
            
            if use_file:
                try:
                    # Verwende F Parameter für Makefile (Datei-Pfad)
                    params = f'F="{msg_file}"'
                    print(f"{self.COLOR_SUCCESS}   ✓ Verwende Message aus Datei{self.COLOR_RESET}")
                except Exception as e:
                    print(f"{self.COLOR_ERROR}   ❌ Fehler: {e}{self.COLOR_RESET}")
                    print(f"{self.COLOR_WARNING}   Fallback: Manuelle Eingabe{self.COLOR_RESET}")
                    use_file = False
            
            if not use_file:
                print(f"\n{self.COLOR_INFO}💬 Commit Message eingeben:{self.COLOR_RESET}")
                print(f"   {self.COLOR_WARNING}(Enter = Auto-generierte Message){self.COLOR_RESET}")
                msg = input("   Message: ").strip()
                if msg:
                    # Escape quotes for shell
                    msg_escaped = msg.replace('"', '\\"')
                    params = f'MSG="{msg_escaped}"'
                    print(f"{self.COLOR_SUCCESS}   ✓ Message: {msg}{self.COLOR_RESET}")
                else:
                    print(f"{self.COLOR_INFO}   ℹ️  Verwende auto-generierte Message{self.COLOR_RESET}")
        
        else:
            # Generic parameter input
            print(f"\n{self.COLOR_INFO}📝 Zusätzliche Parameter? (Enter für keine):{self.COLOR_RESET}")
            print("   Format: KEY=value oder KEY=\"value with spaces\"")
            custom = input("   Parameter: ").strip()
            if custom:
                params = custom
                print(f"{self.COLOR_SUCCESS}   ✓ Parameter: {custom}{self.COLOR_RESET}")
        
        return params
    
    def _execute_command(self, command_name: str) -> None:
        """Execute a make command with optional parameters"""
        # Get parameters if needed
        params = self._get_command_parameters(command_name)
        
        # Build command
        cmd_str = f"make {command_name}"
        if params:
            cmd_str += f" {params}"
        
        print(f"\n{self.COLOR_INFO}🚀 Executing: {cmd_str}{self.COLOR_RESET}\n")
        print("=" * 70)
        
        try:
            result = subprocess.run(
                cmd_str,
                cwd=Path.cwd(),
                shell=True,
                encoding='utf-8',
                errors='replace'
            )
            
            print("\n" + "=" * 70)
            if result.returncode == 0:
                print(f"{self.COLOR_SUCCESS}✅ Command completed successfully!{self.COLOR_RESET}")
            else:
                print(f"{self.COLOR_ERROR}❌ Command failed with exit code {result.returncode}{self.COLOR_RESET}")
            
        except KeyboardInterrupt:
            print(f"\n{self.COLOR_WARNING}⚠️  Command interrupted by user{self.COLOR_RESET}")
        except Exception as e:
            print(f"{self.COLOR_ERROR}❌ Error executing command: {e}{self.COLOR_RESET}")
        
        input(f"\n{self.COLOR_INFO}Drücke Enter um fortzufahren...{self.COLOR_RESET}")
    
    def _show_category_menu(self, category: str, commands: List[MakeCommand]) -> Optional[str]:
        """Show commands in a category and return selected command"""
        cat_info = self.CATEGORIES.get(category, {"icon": "📋", "name": category, "color": self.COLOR_RESET})
        
        while True:
            self._clear_screen()
            self._print_header(f"{cat_info['icon']} {cat_info['name'].upper()}")
            
            # Group by subcategory
            subcats = self._group_by_subcategory(commands)
            
            # Build menu
            menu_items = []
            current_num = 1
            
            for subcat_name, subcat_commands in sorted(subcats.items()):
                if subcat_name:
                    print(f"{cat_info['color']}  [{subcat_name}]{self.COLOR_RESET}")
                
                for cmd in subcat_commands:
                    menu_items.append(cmd.name)
                    print(f"    {current_num}. {cmd.name:<25} - {cmd.description}")
                    current_num += 1
                
                print()
            
            print(f"    0. {self.COLOR_WARNING}← Zurück zum Hauptmenü{self.COLOR_RESET}")
            print("\n" + "=" * 70)
            
            choice = input(f"\n{self.COLOR_INFO}Deine Wahl (0-{len(menu_items)}): {self.COLOR_RESET}").strip()
            
            if choice == "0":
                return None
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(menu_items):
                    return menu_items[choice_num - 1]
                else:
                    print(f"{self.COLOR_ERROR}❌ Ungültige Auswahl!{self.COLOR_RESET}")
                    input("Drücke Enter um fortzufahren...")
            except ValueError:
                print(f"{self.COLOR_ERROR}❌ Bitte eine Zahl eingeben!{self.COLOR_RESET}")
                input("Drücke Enter um fortzufahren...")
    
    def _show_main_menu(self) -> Optional[str]:
        """Show main category menu and return selected category"""
        self._clear_screen()
        self._print_header("🎛️  BF AGENT - INTERACTIVE COMMAND CENTER")
        
        categories = self._group_by_category()
        available_cats = []
        current_num = 1
        
        print(f"{self.COLOR_INFO}Verfügbare Kategorien:{self.COLOR_RESET}\n")
        
        for cat_key in self.CATEGORIES.keys():
            if cat_key not in categories:
                continue
            
            cat_info = self.CATEGORIES[cat_key]
            cmd_count = len(categories[cat_key])
            available_cats.append(cat_key)
            
            print(f"  {current_num}. {cat_info['icon']} {cat_info['name']:<30} ({cmd_count} commands)")
            current_num += 1
        
        print(f"\n  {current_num}. 🔍 Suche nach Commands")
        print(f"  {current_num + 1}. 📊 Zeige alle Commands")
        print(f"\n  0. {self.COLOR_ERROR}❌ Beenden{self.COLOR_RESET}")
        print("\n" + "=" * 70)
        
        choice = input(f"\n{self.COLOR_INFO}Deine Wahl (0-{current_num + 1}): {self.COLOR_RESET}").strip()
        
        if choice == "0":
            return "exit"
        elif choice == str(current_num):
            return "search"
        elif choice == str(current_num + 1):
            return "show_all"
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(available_cats):
                return available_cats[choice_num - 1]
        except ValueError:
            pass
        
        print(f"{self.COLOR_ERROR}❌ Ungültige Auswahl!{self.COLOR_RESET}")
        input("Drücke Enter um fortzufahren...")
        return None
    
    def _search_commands(self) -> Optional[str]:
        """Search for commands and return selected"""
        self._clear_screen()
        self._print_header("🔍 COMMAND SUCHE")
        
        query = input(f"{self.COLOR_INFO}Suchbegriff (oder Enter für Abbruch): {self.COLOR_RESET}").strip()
        
        if not query:
            return None
        
        results = [
            cmd for cmd in self.commands
            if query.lower() in cmd.name.lower() or query.lower() in cmd.description.lower()
        ]
        
        if not results:
            print(f"\n{self.COLOR_WARNING}❌ Keine Commands gefunden für '{query}'{self.COLOR_RESET}")
            input("\nDrücke Enter um fortzufahren...")
            return None
        
        self._clear_screen()
        self._print_header(f"🔍 SUCHERGEBNISSE für '{query}'")
        
        print(f"{self.COLOR_SUCCESS}Gefunden: {len(results)} Commands{self.COLOR_RESET}\n")
        
        for i, cmd in enumerate(results, 1):
            cat_info = self.CATEGORIES.get(cmd.category, {"icon": "📋"})
            print(f"  {i}. {cat_info['icon']} {cmd.name:<25} - {cmd.description}")
            print(f"     {self.COLOR_INFO}[{cmd.category}]{self.COLOR_RESET}")
        
        print(f"\n  0. {self.COLOR_WARNING}← Zurück{self.COLOR_RESET}")
        print("\n" + "=" * 70)
        
        choice = input(f"\n{self.COLOR_INFO}Deine Wahl (0-{len(results)}): {self.COLOR_RESET}").strip()
        
        if choice == "0":
            return None
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(results):
                return results[choice_num - 1].name
        except ValueError:
            pass
        
        return None
    
    def _show_all_commands(self) -> Optional[str]:
        """Show all commands in one list"""
        self._clear_screen()
        self._print_header("📋 ALLE COMMANDS")
        
        print(f"{self.COLOR_INFO}Gesamt: {len(self.commands)} Commands{self.COLOR_RESET}\n")
        
        for i, cmd in enumerate(self.commands, 1):
            cat_info = self.CATEGORIES.get(cmd.category, {"icon": "📋"})
            print(f"  {i:2}. {cat_info['icon']} {cmd.name:<25} - {cmd.description}")
        
        print(f"\n  0. {self.COLOR_WARNING}← Zurück{self.COLOR_RESET}")
        print("\n" + "=" * 70)
        
        choice = input(f"\n{self.COLOR_INFO}Deine Wahl (0-{len(self.commands)}): {self.COLOR_RESET}").strip()
        
        if choice == "0":
            return None
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(self.commands):
                return self.commands[choice_num - 1].name
        except ValueError:
            pass
        
        return None
    
    def run(self) -> None:
        """Main interactive loop"""
        if not self.commands:
            print(f"\n{self.COLOR_ERROR}❌ Keine dokumentierten Commands gefunden!{self.COLOR_RESET}")
            print("Füge Dokumentation zu Makefile-Commands hinzu mit:")
            print("  command: ## Description @category:cat @sub:Subcat\n")
            return
        
        while True:
            # Show main menu
            category = self._show_main_menu()
            
            if category == "exit":
                self._clear_screen()
                print(f"\n{self.COLOR_SUCCESS}👋 Auf Wiedersehen!{self.COLOR_RESET}\n")
                break
            elif category == "search":
                command = self._search_commands()
                if command:
                    self._execute_command(command)
            elif category == "show_all":
                command = self._show_all_commands()
                if command:
                    self._execute_command(command)
            elif category:
                # Show category menu
                categories = self._group_by_category()
                if category in categories:
                    command = self._show_category_menu(category, categories[category])
                    if command:
                        self._execute_command(command)


def main():
    """Main entry point"""
    try:
        menu = MakefileInteractive()
        menu.run()
    except KeyboardInterrupt:
        print("\n\n👋 Auf Wiedersehen!\n")
        return 0
    except Exception as e:
        print(f"\n❌ Fehler: {e}\n")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
