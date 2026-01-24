"""
Test Sentry & Grafana Integration
Quick verification script
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.bfagent.services.admin_diagnostics import get_admin_diagnostics
from apps.bfagent.services.grafana_integration import get_grafana_service
from apps.bfagent.services.sentry_integration import get_sentry_service


def test_sentry_integration():
    """Test Sentry service"""
    print("\n" + "=" * 80)
    print("🐛 TESTING SENTRY INTEGRATION")
    print("=" * 80 + "\n")

    sentry = get_sentry_service()

    # Check status
    stats = sentry.get_stats()
    print(f"Enabled: {stats['enabled']}")
    print(f"SDK Installed: {stats['sdk_installed']}")
    print(f"DSN Configured: {stats['dsn_configured']}")

    if sentry.is_enabled():
        print("\n✅ Sentry is ENABLED and ready!")

        # Test message capture
        event_id = sentry.capture_message(
            "Test message from bfagent integration test", level="info", tags={"test": "true"}
        )

        if event_id:
            print(f"✅ Test message sent: {event_id}")
            print("   Check Sentry UI: https://sentry.io/issues/")

    else:
        print("\n⚠️  Sentry is DISABLED")
        print("   To enable:")
        print("   1. Sign up: https://sentry.io/signup/")
        print("   2. Get DSN from: Settings → Projects → Client Keys")
        print("   3. Add to .env: SENTRY_DSN=https://YOUR_KEY@sentry.io/PROJECT_ID")


def test_grafana_integration():
    """Test Grafana service"""
    print("\n" + "=" * 80)
    print("📊 TESTING GRAFANA INTEGRATION")
    print("=" * 80 + "\n")

    grafana = get_grafana_service()

    # Check status
    stats = grafana.get_stats()
    print(f"Enabled: {stats['enabled']}")
    print(f"Configured: {stats['configured']}")
    if stats.get("url"):
        print(f"URL: {stats['url']}")

    if grafana.is_enabled():
        print("\n✅ Grafana is ENABLED and ready!")

        # Test dashboard creation
        dashboard = grafana.create_bfagent_monitoring_dashboard()
        print(f"✅ Dashboard creation: {dashboard['status']}")

        # Test alerts
        alerts = grafana.get_default_alerts()
        print(f"✅ Default alerts defined: {len(alerts)}")
        for alert in alerts:
            print(f"   - {alert['name']} ({alert['severity']})")

    else:
        print("\n⚠️  Grafana is DISABLED")
        print("   To enable:")
        print("   1. Sign up: https://grafana.com/signup/")
        print("   2. Create Service Account: Administration → Service Accounts")
        print("   3. Add to .env:")
        print("      GRAFANA_URL=https://YOUR_ORG.grafana.net")
        print("      GRAFANA_TOKEN=YOUR_TOKEN")


def test_admin_diagnostics_with_sentry():
    """Test Admin Diagnostics with Sentry integration"""
    print("\n" + "=" * 80)
    print("🧪 TESTING ADMIN DIAGNOSTICS + SENTRY")
    print("=" * 80 + "\n")

    admin = get_admin_diagnostics()

    # Check if Sentry is integrated
    if admin.sentry:
        print("✅ Sentry integrated with Admin Diagnostics")
        print(f"   Sentry enabled: {admin.sentry.is_enabled()}")
    else:
        print("⚠️  Sentry not integrated")

    # Run a quick test
    print("\nRunning quick admin test...")
    results = admin.diagnose_schema_errors("writing_hub")

    print(f"\n📊 Results:")
    print(f"   Missing tables: {len(results['missing_tables'])}")
    print(f"   Missing columns: {len(results['missing_columns'])}")

    if admin.sentry and admin.sentry.is_enabled():
        print("\n✅ Errors will be automatically sent to Sentry")
        print("   Run: python manage.py admin_diagnostics test-admin --app writing_hub")
        print("   Then check: https://sentry.io/issues/")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🚀 SENTRY & GRAFANA INTEGRATION TEST")
    print("=" * 80)

    test_sentry_integration()
    test_grafana_integration()
    test_admin_diagnostics_with_sentry()

    print("\n" + "=" * 80)
    print("✅ INTEGRATION TEST COMPLETE!")
    print("=" * 80 + "\n")

    print("📝 Next Steps:")
    print("   1. Configure Sentry DSN in .env (if not done)")
    print("   2. Configure Grafana URL/TOKEN in .env (optional)")
    print("   3. Run: python manage.py admin_diagnostics test-admin --app writing_hub")
    print("   4. Check Sentry UI for captured events")
    print("\n")


if __name__ == "__main__":
    main()
