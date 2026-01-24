"""
Admin Diagnostic Tools - Integrated into bfagent core functionality
Can be used standalone or registered with tool registry (Dec 9, 2025)
"""

from apps.bfagent.services.admin_diagnostics import get_admin_diagnostics

# Tools are available as standalone functions
# They can optionally be registered with tool_registry if needed


def diagnose_db_errors(app_label: str = None) -> dict:
    """
    Find schema mismatches between Django models and database tables

    Args:
        app_label: Optional app to limit diagnostics to (e.g., 'writing_hub')

    Returns:
        Dict with missing_tables, missing_columns, and recommendations

    Example:
        >>> results = diagnose_db_errors('writing_hub')
        >>> print(f"Missing tables: {len(results['missing_tables'])}")
        >>> print(f"Missing columns: {len(results['missing_columns'])}")
    """
    service = get_admin_diagnostics()
    return service.diagnose_schema_errors(app_label)


def fix_table_references(dry_run: bool = True) -> dict:
    """
    Auto-fix missing tables by creating VIEWs to similar tables

    Args:
        dry_run: If True, only show what would be done without applying changes

    Returns:
        Dict with fixes_applied and errors

    Example:
        >>> # Preview fixes
        >>> results = fix_table_references(dry_run=True)
        >>> # Apply fixes
        >>> results = fix_table_references(dry_run=False)
    """
    service = get_admin_diagnostics()
    return service.fix_table_references(dry_run)


def fix_all_views() -> dict:
    """
    Fix all known VIEW mappings with complete column sets

    Returns:
        Dict with fixed views and errors

    Example:
        >>> results = fix_all_views()
        >>> print(f"Fixed {len(results['fixed'])} views")
        >>> print(f"Errors: {len(results['errors'])}")
    """
    service = get_admin_diagnostics()
    return service.fix_all_views()


def test_admin_urls(app_label: str = None, auto_fix: bool = False) -> dict:
    """
    Test all admin URLs for a given app

    Args:
        app_label: App to test (e.g., 'writing_hub'). If None, tests all apps
        auto_fix: If True, attempt to auto-fix errors

    Returns:
        Dict with test results, errors, and fixes

    Example:
        >>> # Test without fixing
        >>> results = test_admin_urls('writing_hub')
        >>> print(f"Tested: {len(results['tested'])}")
        >>> print(f"Errors: {len(results['errors'])}")
        >>>
        >>> # Test with auto-fix
        >>> results = test_admin_urls('writing_hub', auto_fix=True)
        >>> print(f"Fixed: {len(results['fixed'])}")
    """
    service = get_admin_diagnostics()
    return service.test_admin_urls(app_label, auto_fix)


def find_unused_tables() -> dict:
    """
    Find database tables that are not referenced by any Django model

    Returns:
        Dict with used_tables, unused_tables, and statistics

    Example:
        >>> results = find_unused_tables()
        >>> print(f"Total tables: {results['statistics']['total_tables']}")
        >>> print(f"Unused: {results['statistics']['unused_tables']}")
        >>> print(f"Can cleanup {results['statistics']['unused_rows']} rows")
    """
    service = get_admin_diagnostics()
    return service.find_unused_tables()


def admin_health_check(app_label: str = None, auto_fix: bool = False) -> dict:
    """
    Run all admin diagnostic tools and generate comprehensive report

    Args:
        app_label: Optional app to focus on (e.g., 'writing_hub')
        auto_fix: If True, attempt to auto-fix issues

    Returns:
        Comprehensive health check report with all diagnostics

    Example:
        >>> report = admin_health_check('writing_hub', auto_fix=True)
        >>> print(report['summary'])
    """
    service = get_admin_diagnostics()

    report = {
        "schema_diagnostics": service.diagnose_schema_errors(app_label),
        "admin_urls_test": service.test_admin_urls(app_label, auto_fix),
        "unused_tables": service.find_unused_tables(),
        "summary": {},
    }

    # Generate summary
    schema = report["schema_diagnostics"]
    admin = report["admin_urls_test"]
    unused = report["unused_tables"]

    report["summary"] = {
        "missing_tables": len(schema["missing_tables"]),
        "missing_columns": len(schema["missing_columns"]),
        "admin_errors": len(admin["errors"]),
        "admin_tested": len(admin["tested"]),
        "admin_fixed": len(admin.get("fixed", [])),
        "unused_tables": len(unused["unused_tables"]),
        "unused_rows": unused["statistics"]["unused_rows"],
        "recommendations": schema["recommendations"],
    }

    return report
