Subscriptions API
=================

Travel Beat includes a SaaS subscription system for monetization.

Models
------

.. automodule:: apps.subscriptions.models
   :members:
   :undoc-members:
   :show-inheritance:

Plan Model
~~~~~~~~~~

Defines available subscription tiers.

**Fields:**

- ``name`` - Plan name (Free, Pro, Enterprise)
- ``slug`` - URL-safe identifier
- ``price_monthly`` - Monthly price in cents
- ``price_yearly`` - Yearly price in cents
- ``stories_per_month`` - Story generation quota
- ``max_chapters`` - Max chapters per story
- ``features`` - JSON field for feature flags
- ``is_active`` - Whether plan is available

**Default Plans:**

.. list-table::
   :header-rows: 1

   * - Plan
     - Price
     - Stories/Month
     - Max Chapters
   * - Free
     - $0
     - 2
     - 5
   * - Pro
     - $9.99
     - 20
     - 15
   * - Enterprise
     - $29.99
     - Unlimited
     - Unlimited

Subscription Model
~~~~~~~~~~~~~~~~~~

Tracks user subscriptions.

**Fields:**

- ``user`` - Subscriber (ForeignKey)
- ``plan`` - Selected plan (ForeignKey)
- ``status`` - active/cancelled/expired/past_due
- ``stripe_subscription_id`` - Stripe reference
- ``current_period_start`` - Billing period start
- ``current_period_end`` - Billing period end
- ``cancel_at_period_end`` - Cancellation scheduled

UsageQuota Model
~~~~~~~~~~~~~~~~

Tracks monthly usage against plan limits.

**Fields:**

- ``subscription`` - Related subscription
- ``month`` - Usage month (YYYY-MM)
- ``stories_generated`` - Count this month
- ``stories_limit`` - Limit from plan

**Methods:**

- ``can_generate_story()`` - Check if quota allows
- ``increment_usage()`` - Record story generation

Payment Model
~~~~~~~~~~~~~

Records payment history.

**Fields:**

- ``subscription`` - Related subscription
- ``amount`` - Payment amount in cents
- ``currency`` - Payment currency (default: USD)
- ``stripe_payment_id`` - Stripe reference
- ``status`` - succeeded/pending/failed
- ``created_at`` - Payment timestamp

Stripe Integration
------------------

Webhook handling for Stripe events:

.. code-block:: python

   # Handled webhook events
   - checkout.session.completed
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.payment_succeeded
   - invoice.payment_failed

Configuration:

.. code-block:: python

   STRIPE_PUBLIC_KEY = env('STRIPE_PUBLIC_KEY')
   STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY')
   STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET')
