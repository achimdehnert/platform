"""
Root Folder Cleanup & Organization Tool
Version: 1.0.0

Organizes root-level scripts, backups, reports into proper folders
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent

# Target folders
FOLDERS = {
    'backups_db': PROJECT_ROOT / 'backups' / 'database',
    'backups_logs': PROJECT_ROOT / 'backups' / 'logs',
    'reports_htmx': PROJECT_ROOT / 'reports' / 'htmx',
    'reports_screen': PROJECT_ROOT / 'reports' / 'screen',
    'scripts_helpers': PROJECT_ROOT / 'scripts' / 'helpers',
    'scripts_check': PROJECT_ROOT / 'scripts' / 'helpers' / 'check',
    'scripts_debug': PROJECT_ROOT / 'scripts' / 'helpers' / 'debug',
    'scripts_generate': PROJECT_ROOT / 'scripts' / 'helpers' / 'generate',
    'scripts_test': PROJECT_ROOT / 'scripts' / 'helpers' / 'test',
    # Documentation folders
    'docs_guides': PROJECT_ROOT / 'docs' / 'guides',
    'docs_planning': PROJECT_ROOT / 'docs' / 'planning',
    'docs_status': PROJECT_ROOT / 'docs' / 'status',
    'docs_sessions': PROJECT_ROOT / 'docs' / 'sessions',
    'docs_templates': PROJECT_ROOT / 'docs' / 'templates',
    'docs_testing': PROJECT_ROOT / 'docs' / 'testing',
    'docs_maintenance': PROJECT_ROOT / 'docs' / 'maintenance',
}

# File categorization
FILE_PATTERNS = {
    # Database Backups
    'backups_db': [
        'bfagent_backup_*.db',
        'bfagent_manual_backup.db',
    ],
    
    # Log Files
    'backups_logs': [
        'django.log',
        'error_log.txt',
        'error_full.txt',
    ],
    
    # HTMX Reports
    'reports_htmx': [
        'htmx_report_*.json',
        'htmx_conformity_report.json',
    ],
    
    # Screen Documentation
    'reports_screen': [
        'screen_documentation.json',
    ],
    
    # Check Scripts
    'scripts_check': [
        'check_agent_actions.py',
        'check_phases_status.py',
        'check_prompts.py',
        'check_tables.py',
        'check_workflow_consistency.py',
    ],
    
    # Debug Scripts
    'scripts_debug': [
        'debug_booktype_phases.py',
        'debug_enrichment_panel.py',
    ],
    
    # Generate Scripts
    'scripts_generate': [
        'generate_book.py',
        'generate_book_v2.py',
        'generate_outline.py',
    ],
    
    # Test Scripts
    'scripts_test': [
        'test_*.py',
    ],
    
    # Helper Scripts (root level)
    'scripts_helpers': [
        'analyze_db.py',
        'clean_phase_mappings.py',
        'complete_context_variables.py',
        'complete_phase_mappings.py',
        'show_current_mappings.py',
        'quick_status.py',
    ],
    
    # Documentation - Guides
    'docs_guides': [
        'BOOK_GENERATOR_README.md',
        'PHASE_AGENT_TOOL_GUIDE.md',
    ],
    
    # Documentation - Planning
    'docs_planning': [
        'INTEGRATION_PLAN.md',
        'SHOWCASE_IMPLEMENTATION_PLAN.md',
        'WORLDS_GENERATION_PLAN.md',
    ],
    
    # Documentation - Status & Achievements
    'docs_status': [
        'INTEGRATION_STATUS.md',
        'STANDARDIZATION_COMPLETE.md',
    ],
    
    # Documentation - Sessions
    'docs_sessions': [
        'SESSION_SUMMARY.md',
    ],
    
    # Documentation - Templates
    'docs_templates': [
        'COMMIT_MESSAGE.md',
    ],
    
    # Documentation - Testing
    'docs_testing': [
        'TEST_CHECKLIST_NEXT_SESSION.md',
    ],
    
    # Documentation - Maintenance
    'docs_maintenance': [
        'CHANGELOG_RECOVERY.md',
    ],
}


def create_folders():
    """Create target folders if they don't exist"""
    for folder_name, folder_path in FOLDERS.items():
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created/Verified: {folder_path}")


def get_files_to_move():
    """Scan root folder and categorize files"""
    files_to_move = {}
    
    for category, patterns in FILE_PATTERNS.items():
        files_to_move[category] = []
        
        for pattern in patterns:
            # Handle glob patterns
            if '*' in pattern:
                matches = list(PROJECT_ROOT.glob(pattern))
                files_to_move[category].extend(matches)
            else:
                # Exact match
                file_path = PROJECT_ROOT / pattern
                if file_path.exists():
                    files_to_move[category].append(file_path)
    
    return files_to_move


def print_summary(files_to_move):
    """Print summary of what will be moved"""
    print("\n" + "=" * 70)
    print("📋 ROOT FOLDER CLEANUP SUMMARY")
    print("=" * 70)
    
    total_count = 0
    total_size = 0
    
    for category, files in files_to_move.items():
        if not files:
            continue
        
        count = len(files)
        size = sum(f.stat().st_size for f in files if f.exists())
        total_count += count
        total_size += size
        
        target = FOLDERS[category]
        
        print(f"\n📂 {category.upper()}")
        print(f"   Target: {target}")
        print(f"   Files:  {count}")
        print(f"   Size:   {size / (1024*1024):.2f} MB")
        
        # Show first 5 files
        for i, file in enumerate(files[:5]):
            print(f"     • {file.name}")
        
        if len(files) > 5:
            print(f"     ... and {len(files) - 5} more")
    
    print("\n" + "=" * 70)
    print(f"📊 TOTAL: {total_count} files, {total_size / (1024*1024):.2f} MB")
    print("=" * 70)


def move_files(files_to_move, dry_run=True):
    """Move files to target folders"""
    moved_count = 0
    
    for category, files in files_to_move.items():
        if not files:
            continue
        
        target_dir = FOLDERS[category]
        
        for file in files:
            if not file.exists():
                print(f"⚠️  File not found: {file.name}")
                continue
            
            target_path = target_dir / file.name
            
            if dry_run:
                print(f"   Would move: {file.name} → {target_dir.name}/")
            else:
                try:
                    shutil.move(str(file), str(target_path))
                    print(f"✅ Moved: {file.name} → {target_dir.name}/")
                    moved_count += 1
                except Exception as e:
                    print(f"❌ Error moving {file.name}: {e}")
    
    return moved_count


def create_gitignore_entries():
    """Create/update .gitignore for backup folders"""
    gitignore_content = """
# Database Backups (keep only latest)
backups/database/*.db
!backups/database/.gitkeep

# Large Log Files
backups/logs/*.log
backups/logs/*.txt

# HTMX Reports (keep only latest)
reports/htmx/htmx_report_*.json
!reports/htmx/.gitkeep

# Screen Reports
reports/screen/*.json
!reports/screen/.gitkeep

# Documentation folders (keep structured)
!docs/guides/
!docs/planning/
!docs/status/
!docs/sessions/
!docs/templates/
!docs/testing/
!docs/maintenance/
"""
    
    gitignore_path = PROJECT_ROOT / '.gitignore'
    
    if gitignore_path.exists():
        current_content = gitignore_path.read_text()
        if '# Database Backups' not in current_content:
            print("\n📝 .gitignore needs updating")
            print("Add these lines to .gitignore:")
            print(gitignore_content)
    
    # Create .gitkeep files
    for folder in FOLDERS.values():
        gitkeep = folder / '.gitkeep'
        if not gitkeep.exists():
            gitkeep.touch()


def main(dry_run=True):
    """Main cleanup function"""
    print("🔄 Root Folder Cleanup Tool")
    print("=" * 70)
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No files will be moved")
    else:
        print("🚀 EXECUTING - Files WILL be moved")
    
    print("\n📁 Creating target folders...")
    create_folders()
    
    print("\n🔍 Scanning root folder...")
    files_to_move = get_files_to_move()
    
    print_summary(files_to_move)
    
    if not dry_run:
        print("\n🚀 Moving files...")
        moved = move_files(files_to_move, dry_run=False)
        print(f"\n✅ Successfully moved {moved} files")
        
        print("\n📝 Updating .gitignore...")
        create_gitignore_entries()
    else:
        print("\n💡 To execute: python scripts/cleanup_root_folder.py --execute")
    
    print("\n" + "=" * 70)
    print("✅ Cleanup analysis complete!")


if __name__ == "__main__":
    import sys
    
    if "--execute" in sys.argv:
        print("⚠️  WARNING: This will move files!")
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() == 'yes':
            main(dry_run=False)
        else:
            print("❌ Aborted by user")
    else:
        main(dry_run=True)
