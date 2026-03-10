"""
stripe_setup_coach_hub.py
─────────────────────────
Legt alle 5 coach-hub Module als Stripe Products an,
je mit Monthly + Yearly recurring Price.

Voraussetzungen:
    pip install stripe python-dotenv

Verwendung:
    export STRIPE_SECRET_KEY=sk_test_...   # oder in .env
    python stripe_setup_coach_hub.py

    # Dry-run (zeigt nur was angelegt würde, kein API-Call):
    python stripe_setup_coach_hub.py --dry-run

    # Gegen Live-Umgebung:
    python stripe_setup_coach_hub.py --live
"""

import argparse
import os
import sys
from dataclasses import dataclass, field

try:
    import stripe
except ImportError:
    sys.exit("stripe fehlt — bitte: pip install stripe")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional


# ── Konfiguration ────────────────────────────────────────────────────────────

@dataclass
class Module:
    key: str            # wird als metadata.module_key gespeichert
    name: str           # Stripe Product Name
    description: str
    price_monthly: int  # in Cent (Euro)
    price_yearly: int   # in Cent (Euro)
    # wird nach dem Anlegen befüllt:
    price_id_monthly: str = field(default="", init=False)
    price_id_yearly: str  = field(default="", init=False)
    product_id: str       = field(default="", init=False)


MODULES: list[Module] = [
    Module(
        key="coaching_basic",
        name="Coach-Hub — Coaching Basic",
        description="Basis-Coaching-Modul: Sitzungsplanung, Klientenverwaltung, einfache Notizen",
        price_monthly=2900,
        price_yearly=29000,
    ),
    Module(
        key="coaching_pro",
        name="Coach-Hub — Coaching Pro",
        description="Pro-Coaching-Modul: erweitertes Sitzungsmanagement, Zieltracking, Templates",
        price_monthly=5900,
        price_yearly=59000,
    ),
    Module(
        key="assessments",
        name="Coach-Hub — Assessments",
        description="Assessment-Modul: Persönlichkeitsprofile, Kompetenzanalysen, Fragebögen",
        price_monthly=1900,
        price_yearly=19000,
    ),
    Module(
        key="learning",
        name="Coach-Hub — Learning",
        description="Learning-Modul: Lernpfade, Ressourcenbibliothek, Fortschrittstracking",
        price_monthly=1900,
        price_yearly=19000,
    ),
    Module(
        key="reports",
        name="Coach-Hub — Reports",
        description="Reports-Modul: Fortschrittsberichte, Analyse-Dashboards, PDF-Export",
        price_monthly=1500,
        price_yearly=15000,
    ),
]


# ── Core-Logik ───────────────────────────────────────────────────────────────

def create_product(module: Module, dry_run: bool) -> str:
    """Legt ein Stripe Product an und gibt die product_id zurück."""
    if dry_run:
        fake_id = f"prod_DRY_{module.key}"
        print(f"  [DRY-RUN] Product: {module.name!r} → {fake_id}")
        return fake_id

    product = stripe.Product.create(
        name=module.name,
        description=module.description,
        metadata={
            "module_key": module.key,
            "platform": "coach-hub",
        },
    )
    print(f"  ✅ Product: {module.name!r} → {product.id}")
    return product.id


def create_price(
    product_id: str,
    module_key: str,
    amount: int,
    interval: str,       # "month" | "year"
    dry_run: bool,
) -> str:
    """Legt einen recurring Price an und gibt die price_id zurück."""
    if dry_run:
        fake_id = f"price_DRY_{module_key}_{interval}"
        print(f"    [DRY-RUN] Price ({interval}): {amount/100:.2f} € → {fake_id}")
        return fake_id

    price = stripe.Price.create(
        product=product_id,
        unit_amount=amount,
        currency="eur",
        recurring={"interval": interval},
        metadata={
            "module_key": module_key,
            "billing_period": interval,
        },
    )
    label = f"{amount/100:.2f} €/{interval}"
    print(f"    ✅ Price ({interval}): {label} → {price.id}")
    return price.id


def setup_all_modules(dry_run: bool) -> list[Module]:
    """Hauptfunktion: legt alle Module + Prices an."""
    for module in MODULES:
        print(f"\n📦 {module.name}")

        module.product_id      = create_product(module, dry_run)
        module.price_id_monthly = create_price(
            module.product_id, module.key, module.price_monthly, "month", dry_run
        )
        module.price_id_yearly = create_price(
            module.product_id, module.key, module.price_yearly, "year", dry_run
        )

    return MODULES


# ── Output ───────────────────────────────────────────────────────────────────

def print_summary(modules: list[Module], dry_run: bool) -> None:
    tag = " [DRY-RUN]" if dry_run else ""
    print(f"\n{'─'*60}")
    print(f"  coach-hub Price-IDs{tag}")
    print(f"{'─'*60}")

    # Django settings.py Format
    print("\n# settings.py / .env — direkt verwendbar:\n")
    for m in modules:
        key = m.key.upper()
        print(f"STRIPE_PRICE_{key}_MONTHLY = \"{m.price_id_monthly}\"")
        print(f"STRIPE_PRICE_{key}_YEARLY  = \"{m.price_id_yearly}\"")

    # Tabellen-Übersicht
    print(f"\n{'─'*60}")
    print(f"  {'Modul':<20} {'Monthly':<30} {'Yearly'}")
    print(f"{'─'*60}")
    for m in modules:
        print(f"  {m.key:<20} {m.price_id_monthly:<30} {m.price_id_yearly}")
    print(f"{'─'*60}\n")


# ── Entry-Point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="coach-hub Stripe Setup")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Zeigt was angelegt würde ohne API-Calls",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Verwendet STRIPE_LIVE_SECRET_KEY statt STRIPE_SECRET_KEY",
    )
    args = parser.parse_args()

    # API-Key auflösen
    if args.live:
        key_name = "STRIPE_LIVE_SECRET_KEY"
    else:
        key_name = "STRIPE_SECRET_KEY"

    api_key = os.environ.get(key_name, "")

    if not args.dry_run:
        if not api_key:
            sys.exit(
                f"❌ {key_name} nicht gesetzt.\n"
                f"   export {key_name}=sk_{'live' if args.live else 'test'}_..."
            )
        if args.live and not api_key.startswith("sk_live_"):
            sys.exit("❌ --live erfordert einen sk_live_... Key")
        if not args.live and not api_key.startswith("sk_test_"):
            print("⚠️  Warnung: Key sieht nicht nach Test-Key aus (sk_test_...)")

        stripe.api_key = api_key

    env = "LIVE 🔴" if args.live else "TEST 🟡"
    mode = "DRY-RUN" if args.dry_run else f"LIVE API ({env})"
    print(f"\n🚀 coach-hub Stripe Setup — Modus: {mode}")
    print(f"   {len(MODULES)} Module × 2 Prices = {len(MODULES) * 2} API-Calls\n")

    modules = setup_all_modules(dry_run=args.dry_run)
    print_summary(modules, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
