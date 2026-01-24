"""
Complete MCP Stack Test
Tests all 3 MCP integrations: Sentry + Grafana + Chrome DevTools
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.bfagent.services.admin_diagnostics import get_admin_diagnostics
from apps.bfagent.services.chrome_devtools_integration import get_chrome_service
from apps.bfagent.services.grafana_integration import get_grafana_service
from apps.bfagent.services.sentry_integration import get_sentry_service


def print_header(title):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_sentry():
    """Test Sentry integration"""
    print_header("🐛 TESTING SENTRY INTEGRATION")

    sentry = get_sentry_service()

    stats = sentry.get_stats()
    print(f"✓ SDK Installed: {stats['sdk_installed']}")
    print(f"✓ DSN Configured: {stats['dsn_configured']}")
    print(f"✓ Enabled: {stats['enabled']}")

    if sentry.is_enabled():
        print("\n🎉 Sentry is ENABLED and ready!")
        print("   • Error tracking active")
        print("   • AI analysis (Seer) ready")
        print("   • Performance monitoring active")
    else:
        print("\n⚠️  Sentry is DISABLED")
        print("   To enable:")
        print("   1. Sign up: https://sentry.io/signup/")
        print("   2. Get DSN: Settings → Projects → Client Keys")
        print("   3. Add to .env: SENTRY_DSN=https://YOUR_KEY@sentry.io/PROJECT_ID")

    return sentry


def test_grafana():
    """Test Grafana integration"""
    print_header("📊 TESTING GRAFANA INTEGRATION")

    grafana = get_grafana_service()

    stats = grafana.get_stats()
    print(f"✓ Configured: {stats['configured']}")
    print(f"✓ Enabled: {stats['enabled']}")
    if stats.get("url"):
        print(f"✓ URL: {stats['url']}")

    if grafana.is_enabled():
        print("\n🎉 Grafana is ENABLED and ready!")
        print("   • Monitoring dashboards ready")
        print("   • Error pattern detection (Sift) active")
        print("   • Alerting & OnCall ready")
    else:
        print("\n⚠️  Grafana is DISABLED")
        print("   To enable:")
        print("   1. Sign up: https://grafana.com/signup/")
        print("   2. Create Service Account: Administration → Service Accounts")
        print("   3. Add to .env:")
        print("      GRAFANA_URL=https://YOUR_ORG.grafana.net")
        print("      GRAFANA_TOKEN=YOUR_TOKEN")

    return grafana


def test_chrome_devtools():
    """Test Chrome DevTools integration"""
    print_header("📸 TESTING CHROME DEVTOOLS INTEGRATION")

    chrome = get_chrome_service()

    stats = chrome.get_stats()
    print(f"✓ MCP Available: {stats['mcp_available']}")
    print(f"✓ Enabled: {stats['enabled']}")
    print(f"✓ Fallback Mode: {stats['fallback_mode']}")

    health = chrome.health_check()
    print(f"\nStatus: {health['status']}")
    print(f"Message: {health['message']}")

    if chrome.is_enabled():
        print("\n🎉 Chrome DevTools is ENABLED and ready!")
        print("   • Visual testing active")
        print("   • Screenshots available")
        print("   • Console monitoring active")
        print("   • Performance profiling ready")
    else:
        print("\n⚠️  Chrome DevTools is in FALLBACK MODE")
        print("   To enable full features:")
        print("   1. Install: npm install -g chrome-devtools-mcp@latest")
        print("   2. Configure MCP client (Claude, etc.)")
        print("   3. Restart")
        print("\n   ℹ️  Fallback mode uses HTTP-only testing (limited)")

    return chrome


def test_admin_diagnostics():
    """Test Admin Diagnostics with all integrations"""
    print_header("🔬 TESTING ADMIN DIAGNOSTICS")

    admin = get_admin_diagnostics()

    print("✓ Sentry integration:", "ACTIVE" if admin.sentry else "NONE")
    print("✓ Grafana integration:", "ACTIVE" if admin.grafana else "NONE")
    print("✓ Chrome DevTools integration:", "ACTIVE" if admin.chrome else "NONE")

    # Check which services are enabled
    services_enabled = 0
    if admin.sentry and admin.sentry.is_enabled():
        services_enabled += 1
    if admin.grafana and admin.grafana.is_enabled():
        services_enabled += 1
    if admin.chrome and admin.chrome.is_enabled():
        services_enabled += 1

    print(f"\nActive Services: {services_enabled}/3")

    if services_enabled == 3:
        print("\n🎊 ALL 3 SERVICES ACTIVE!")
        print("   Complete DevOps AI Stack ready!")
    elif services_enabled > 0:
        print(f"\n⚡ {services_enabled} service(s) active")
        print("   Partial observability enabled")
    else:
        print("\n⚠️  No services enabled")
        print("   Using fallback mode")

    return admin


def test_quick_health_check():
    """Run a quick health check"""
    print_header("💊 QUICK HEALTH CHECK")

    admin = get_admin_diagnostics()

    print("Running diagnostics on writing_hub...")
    results = admin.diagnose_schema_errors("writing_hub")

    print(f"\n✓ Missing tables: {len(results['missing_tables'])}")
    print(f"✓ Missing columns: {len(results['missing_columns'])}")

    if len(results["missing_tables"]) == 0 and len(results["missing_columns"]) == 0:
        print("\n✅ All schema checks passed!")
    else:
        print("\n⚠️  Schema issues found")
        print("   Run: python manage.py admin_diagnostics ultimate-check --app writing_hub")


def print_summary(sentry, grafana, chrome, admin):
    """Print final summary"""
    print_header("📊 INTEGRATION SUMMARY")

    print("Services Status:")
    print(f"  • Sentry:        {'✅ ENABLED' if sentry.is_enabled() else '⚠️  DISABLED'}")
    print(f"  • Grafana:       {'✅ ENABLED' if grafana.is_enabled() else '⚠️  DISABLED'}")
    print(f"  • Chrome DevTools: {'✅ ENABLED' if chrome.is_enabled() else '⚠️  FALLBACK'}")

    enabled_count = sum([sentry.is_enabled(), grafana.is_enabled(), chrome.is_enabled()])

    print(f"\nTotal Active: {enabled_count}/3")

    print("\n" + "=" * 80)

    if enabled_count == 3:
        print("🎊 COMPLETE DEVOPS AI STACK READY!")
        print("\nYou have:")
        print("  ✅ Visual Intelligence (Chrome DevTools)")
        print("  ✅ Reactive Intelligence (Sentry + Seer AI)")
        print("  ✅ Proactive Intelligence (Grafana + Sift)")
        print("\nRun ultimate health check:")
        print("  python manage.py admin_diagnostics ultimate-check --app writing_hub --visual")

    elif enabled_count > 0:
        print(f"⚡ {enabled_count}/3 SERVICES ACTIVE - PARTIAL OBSERVABILITY")
        print("\nTo enable missing services, see instructions above.")
        print("\nRun health check:")
        print("  python manage.py admin_diagnostics health-check --app writing_hub")

    else:
        print("⚠️  NO SERVICES ENABLED - FALLBACK MODE")
        print("\nYou're using basic HTTP testing.")
        print("To enable full features, configure at least one service.")
        print("\nQuick start:")
        print("  1. Get Sentry DSN: https://sentry.io/signup/ (FREE)")
        print("  2. Add to .env: SENTRY_DSN=https://...")
        print("  3. Restart: python manage.py runserver")

    print("=" * 80 + "\n")

    print("📚 Documentation:")
    print("  • SENTRY_GRAFANA_INTEGRATION_COMPLETE.md")
    print("  • CHROME_DEVTOOLS_MCP_ANALYSIS.md")
    print("  • MCP_INTEGRATION_ROADMAP.md")
    print("\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  🚀 COMPLETE MCP STACK INTEGRATION TEST")
    print("  Testing: Sentry + Grafana + Chrome DevTools")
    print("=" * 80)

    # Test each service
    sentry = test_sentry()
    grafana = test_grafana()
    chrome = test_chrome_devtools()
    admin = test_admin_diagnostics()

    # Quick health check
    test_quick_health_check()

    # Final summary
    print_summary(sentry, grafana, chrome, admin)

    print("🎉 Test complete!")


if __name__ == "__main__":
    main()
