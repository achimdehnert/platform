#!/usr/bin/env python
"""
Migration Quick Fix Scripts - Common scenarios
Enterprise-Grade utilities for Django migration issues
"""
import os
import sys
from pathlib import Path

import django
from fix_migrations import MigrationFixer

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")


django.setup()

# Import the main fixer


class QuickFixes:
    """Collection of quick fix methods for common scenarios"""

    @staticmethod
    def fix_textfield_issue(app_name="bfagent", migration="0007_fix_text_fields"):
        """Fix the TextField max_length issue - OUR CURRENT PROBLEM"""
        print("🔧 Fixing TextField max_length issue...")
        print("=" * 50)

        fixer = MigrationFixer(quiet=False, dry_run=False)

        # Create backup first
        backup_path = fixer.create_backup()
        print(f"✅ Database backup created: {backup_path}")

        # Fix the specific migration
        print(f"\n🎯 Fixing migration: {app_name}.{migration}")
        success = fixer.fix_specific_migration(app_name, migration, fake=True)

        if success:
            # Verify the fix
            print("\n🧪 Verifying fix...")
            if fixer.verify_textfield_fix():
                print("\n🎉 SUCCESS: TextField issue completely resolved!")
                print("✅ You can now save projects with long text!")
                return True
            else:
                print("\n❌ Fix applied but verification failed")
                return False
        else:
            print("\n❌ Failed to apply fix")
            return False

    @staticmethod
    def diagnose_current_issue():
        """Diagnose the current migration issue"""
        print("🔍 DIAGNOSING CURRENT MIGRATION ISSUE")
        print("=" * 50)

        fixer = MigrationFixer(quiet=False, dry_run=False)
        issues = fixer.diagnose()

        if issues:
            print(f"\n⚠️ Found {len(issues)} migration issues:")
            for i, issue in enumerate(issues, 1):
                print(f"\n{i}. {issue.get('type', 'unknown').upper()}")
                print(f"   App: {issue.get('app', 'unknown')}")
                print(f"   Migration: {issue.get('migration', 'unknown')}")
                print(f"   Message: {issue['message']}")
                if "fix" in issue:
                    print(f"   Suggested Fix: {issue['fix']}")
        else:
            print("✅ No migration issues found!")

        return issues

    @staticmethod
    def emergency_fix_all():
        """Emergency fix for all current issues"""
        print("🚨 EMERGENCY FIX - ALL ISSUES")
        print("=" * 50)

        # First diagnose
        issues = QuickFixes.diagnose_current_issue()

        if not issues:
            print("✅ No issues to fix!")
            return True

        print(f"\n🔧 Attempting to fix {len(issues)} issues...")

        fixer = MigrationFixer(quiet=False, dry_run=False)

        # Create backup
        backup_path = fixer.create_backup()
        print(f"✅ Backup created: {backup_path}")

        success_count = 0
        for issue in issues:
            issue_type = issue.get("type")
            app_name = issue.get("app")
            migration_name = issue.get("migration")

            if issue_type == "unapplied_migration" and app_name and migration_name:
                print(f"\n🔧 Fixing: {app_name}.{migration_name}")
                if fixer.fix_specific_migration(app_name, migration_name, fake=True):
                    success_count += 1
                    print("   ✅ Fixed!")
                else:
                    print("   ❌ Failed!")

        print(f"\n📊 Results: {success_count}/{len(issues)} issues fixed")

        if success_count == len(issues):
            print("🎉 ALL ISSUES RESOLVED!")
            return True
        else:
            print("⚠️ Some issues remain - manual intervention may be needed")
            return False

    @staticmethod
    def test_project_save():
        """Test if project save works after fix"""
        print("🧪 TESTING PROJECT SAVE FUNCTIONALITY")
        print("=" * 50)

        try:
            from apps.bfagent.forms import BookProjectForm
            from apps.bfagent.models import BookProjects

            # Get test project
            project = BookProjects.objects.get(pk=16)
            print(f"📋 Testing with project: {project.title}")

            # Create test data with long strings (the original problem)
            test_data = {
                "title": project.title,
                "genre": project.genre or "FICTION",
                "content_rating": project.content_rating or "GENERAL",
                "status": project.status or "draft",
                "target_word_count": project.target_word_count or 50000,
                "current_word_count": project.current_word_count or 0,
                "unique_elements": "A" * 4000,  # 4000 chars - was causing error
                "genre_settings": "B" * 4000,  # 4000 chars - was causing error
                "book_type_id": project.book_type_id or "",
                "description": project.description or "",
                "tagline": project.tagline or "",
                "story_premise": project.story_premise or "",
                "target_audience": project.target_audience or "",
                "story_themes": project.story_themes or "",
                "setting_time": project.setting_time or "",
                "setting_location": project.setting_location or "",
                "atmosphere_tone": project.atmosphere_tone or "",
                "main_conflict": project.main_conflict or "",
                "stakes": project.stakes or "",
                "protagonist_concept": project.protagonist_concept or "",
                "antagonist_concept": project.antagonist_concept or "",
                "inspiration_sources": project.inspiration_sources or "",
            }

            print("🔍 Testing form validation with long text...")
            form = BookProjectForm(test_data, instance=project)

            if form.is_valid():
                print("✅ Form validation PASSED!")
                print("🎯 Attempting to save...")

                # Try to save
                saved_project = form.save()
                print("✅ Project saved successfully!")
                print(f"   • unique_elements length: {len(saved_project.unique_elements)}")
                print(f"   • genre_settings length: {len(saved_project.genre_settings)}")
                print("\n🎉 PROJECT SAVE TEST SUCCESSFUL!")
                return True
            else:
                print("❌ Form validation FAILED:")
                for field, errors in form.errors.items():
                    print(f"   • {field}: {errors}")
                return False

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False

    @staticmethod
    def show_menu():
        """Show interactive menu for our specific problem"""
        print("\n" + "=" * 60)
        print("BF Agent Migration Fix Tool - Enterprise Edition".center(60))
        print("=" * 60)
        print("\n🎯 CURRENT ISSUE: TextField max_length validation error")
        print("   • unique_elements: 3572 chars (max: 500)")
        print("   • genre_settings: 3218 chars (max: 500)")
        print("\n📋 Available Actions:")
        print("1. 🔍 Diagnose current migration issues")
        print("2. 🔧 Fix TextField issue (recommended)")
        print("3. 🚨 Emergency fix all issues")
        print("4. 🧪 Test project save functionality")
        print("5. 📊 Generate detailed report")
        print("6. 🚀 Complete fix and test workflow")
        print("7. ❌ Exit")

        choice = input("\nSelect option (1-7): ").strip()

        if choice == "1":
            QuickFixes.diagnose_current_issue()
        elif choice == "2":
            QuickFixes.fix_textfield_issue()
        elif choice == "3":
            QuickFixes.emergency_fix_all()
        elif choice == "4":
            QuickFixes.test_project_save()
        elif choice == "5":
            fixer = MigrationFixer(quiet=False, dry_run=False)
            fixer.create_report()
        elif choice == "6":
            QuickFixes.complete_workflow()
        elif choice == "7":
            print("👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice")

        # Show menu again
        if input("\nPress Enter to continue or 'q' to quit: ").lower() != "q":
            QuickFixes.show_menu()

    @staticmethod
    def complete_workflow():
        """Complete workflow: diagnose, fix, test, verify"""
        print("\n🚀 COMPLETE MIGRATION FIX WORKFLOW")
        print("=" * 60)

        # Step 1: Diagnose
        print("\n📋 STEP 1: Diagnosis")
        issues = QuickFixes.diagnose_current_issue()

        if not issues:
            print("✅ No issues found - testing project save...")
            QuickFixes.test_project_save()
            return

        # Step 2: Fix
        print("\n🔧 STEP 2: Fix Issues")
        fix_success = QuickFixes.fix_textfield_issue()

        if not fix_success:
            print("❌ Fix failed - aborting workflow")
            return

        # Step 3: Test
        print("\n🧪 STEP 3: Test Project Save")
        test_success = QuickFixes.test_project_save()

        if test_success:
            print("\n🎉 WORKFLOW COMPLETE - ALL TESTS PASSED!")
            print("✅ Your project save issue is now resolved!")
        else:
            print("\n⚠️ Fix applied but tests failed - manual check needed")


def main():
    """Main entry point for quick fixes"""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "textfield":
            QuickFixes.fix_textfield_issue()
        elif command == "diagnose":
            QuickFixes.diagnose_current_issue()
        elif command == "fix-all":
            QuickFixes.emergency_fix_all()
        elif command == "test":
            QuickFixes.test_project_save()
        elif command == "workflow":
            QuickFixes.complete_workflow()
        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  textfield  - Fix TextField max_length issue")
            print("  diagnose   - Diagnose current issues")
            print("  fix-all    - Emergency fix all issues")
            print("  test       - Test project save")
            print("  workflow   - Complete fix workflow")
    else:
        # Show interactive menu
        QuickFixes.show_menu()


if __name__ == "__main__":
    main()
