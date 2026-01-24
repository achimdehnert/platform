"""
Test script for Writing Hub Admin
Checks all admin registrations and potential errors
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from apps.writing_hub.models import (  # Lookups; Story Elements
    ArcType,
    Beat,
    BeatType,
    ConflictLevel,
    ContentRating,
    EmotionalTone,
    ErrorStrategy,
    HandlerCategory,
    HandlerPhase,
    ImportanceLevel,
    Location,
    PlotThread,
    Scene,
    SceneConnection,
    SceneConnectionType,
    TimelineEvent,
    WritingStage,
)


def test_admin_registrations():
    """Check all models are properly registered in admin"""
    print("\n" + "=" * 80)
    print("🔍 TESTING WRITING HUB ADMIN REGISTRATIONS")
    print("=" * 80 + "\n")

    models_to_check = [
        # Old Lookups
        ("ContentRating", ContentRating),
        ("WritingStage", WritingStage),
        ("ArcType", ArcType),
        ("ImportanceLevel", ImportanceLevel),
        ("HandlerCategory", HandlerCategory),
        ("HandlerPhase", HandlerPhase),
        ("ErrorStrategy", ErrorStrategy),
        # New Story Lookups
        ("EmotionalTone", EmotionalTone),
        ("ConflictLevel", ConflictLevel),
        ("BeatType", BeatType),
        ("SceneConnectionType", SceneConnectionType),
        # Story Elements
        ("Scene", Scene),
        ("Beat", Beat),
        ("Location", Location),
        ("PlotThread", PlotThread),
        ("SceneConnection", SceneConnection),
        ("TimelineEvent", TimelineEvent),
    ]

    registered = []
    not_registered = []
    errors = []

    for name, model in models_to_check:
        try:
            if admin.site.is_registered(model):
                admin_class = admin.site._registry[model]
                registered.append((name, model, admin_class))
                print(f"✅ {name:30s} - Registered as {admin_class.__class__.__name__}")
            else:
                not_registered.append(name)
                print(f"⚠️  {name:30s} - NOT registered in admin")
        except Exception as e:
            errors.append((name, str(e)))
            print(f"❌ {name:30s} - ERROR: {e}")

    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Registered:     {len(registered)}")
    print(f"⚠️  Not Registered: {len(not_registered)}")
    print(f"❌ Errors:         {len(errors)}")

    if errors:
        print("\n" + "=" * 80)
        print("❌ ERRORS FOUND:")
        print("=" * 80)
        for name, error in errors:
            print(f"\n{name}:")
            print(f"  {error}")

    return len(errors) == 0


def test_admin_list_displays():
    """Check admin list_display configurations"""
    print("\n" + "=" * 80)
    print("🔍 TESTING ADMIN LIST DISPLAYS")
    print("=" * 80 + "\n")

    models = [
        EmotionalTone,
        ConflictLevel,
        BeatType,
        SceneConnectionType,
        Scene,
        Beat,
        Location,
        PlotThread,
        SceneConnection,
        TimelineEvent,
    ]

    errors = []

    for model in models:
        if not admin.site.is_registered(model):
            continue

        admin_class = admin.site._registry[model]
        model_name = model.__name__

        # Check list_display
        if hasattr(admin_class, "list_display"):
            list_display = admin_class.list_display
            print(f"✅ {model_name:30s} - list_display: {list_display}")

            # Verify all fields exist
            for field_name in list_display:
                if field_name == "__str__":
                    continue

                # Check if it's a model field or method
                try:
                    if hasattr(model, field_name):
                        pass  # Field exists
                    elif hasattr(admin_class, field_name):
                        pass  # Admin method exists
                    else:
                        errors.append(f"{model_name}.{field_name} - field not found")
                        print(f"   ⚠️  Field '{field_name}' not found on model or admin")
                except Exception as e:
                    errors.append(f"{model_name}.{field_name} - {str(e)}")
        else:
            print(f"⚠️  {model_name:30s} - No list_display configured")

    if errors:
        print("\n❌ List Display Errors:")
        for error in errors:
            print(f"  - {error}")

    return len(errors) == 0


def test_lookup_data():
    """Check if lookup tables have data"""
    print("\n" + "=" * 80)
    print("🔍 TESTING LOOKUP TABLE DATA")
    print("=" * 80 + "\n")

    lookups = [
        ("EmotionalTone", EmotionalTone, 10),
        ("ConflictLevel", ConflictLevel, 5),
        ("BeatType", BeatType, 8),
        ("SceneConnectionType", SceneConnectionType, 6),
    ]

    all_good = True

    for name, model, expected_count in lookups:
        try:
            count = model.objects.count()
            if count == expected_count:
                print(f"✅ {name:30s} - {count}/{expected_count} entries")
            elif count > 0:
                print(f"⚠️  {name:30s} - {count}/{expected_count} entries (unexpected count)")
                all_good = False
            else:
                print(f"❌ {name:30s} - {count}/{expected_count} entries (EMPTY!)")
                all_good = False
        except Exception as e:
            print(f"❌ {name:30s} - ERROR: {e}")
            all_good = False

    return all_good


def test_model_relationships():
    """Test ForeignKey and M2M relationships"""
    print("\n" + "=" * 80)
    print("🔍 TESTING MODEL RELATIONSHIPS")
    print("=" * 80 + "\n")

    tests = [
        ("Scene.emotional_start", lambda: Scene._meta.get_field("emotional_start")),
        ("Scene.emotional_end", lambda: Scene._meta.get_field("emotional_end")),
        ("Scene.conflict_level", lambda: Scene._meta.get_field("conflict_level")),
        ("Scene.pov_character", lambda: Scene._meta.get_field("pov_character")),
        ("Scene.characters", lambda: Scene._meta.get_field("characters")),
        ("Scene.plot_threads", lambda: Scene._meta.get_field("plot_threads")),
        ("Beat.beat_type", lambda: Beat._meta.get_field("beat_type")),
        ("Beat.scene", lambda: Beat._meta.get_field("scene")),
        (
            "SceneConnection.connection_type",
            lambda: SceneConnection._meta.get_field("connection_type"),
        ),
    ]

    errors = []

    for name, test_func in tests:
        try:
            field = test_func()
            related_model = field.related_model if hasattr(field, "related_model") else None
            if related_model:
                print(f"✅ {name:40s} → {related_model.__name__}")
            else:
                print(f"✅ {name:40s} (no related model)")
        except Exception as e:
            print(f"❌ {name:40s} - ERROR: {e}")
            errors.append((name, str(e)))

    return len(errors) == 0


def main():
    """Run all tests"""
    print("\n" + "🎯 WRITING HUB ADMIN TEST SUITE")
    print("=" * 80)

    results = []

    # Test 1: Admin Registrations
    results.append(("Admin Registrations", test_admin_registrations()))

    # Test 2: List Displays
    results.append(("List Displays", test_admin_list_displays()))

    # Test 3: Lookup Data
    results.append(("Lookup Data", test_lookup_data()))

    # Test 4: Model Relationships
    results.append(("Model Relationships", test_model_relationships()))

    # Final Summary
    print("\n" + "=" * 80)
    print("🏁 FINAL RESULTS")
    print("=" * 80)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Admin is ready to use!")
    else:
        print("⚠️  SOME TESTS FAILED - Check errors above")
    print("=" * 80 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
