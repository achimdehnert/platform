from django.contrib import admin
from .models import Plan, Subscription, UsageQuota, Payment


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'price_monthly', 'stories_per_month', 'is_active']
    list_filter = ['tier', 'is_active']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'billing_cycle', 'current_period_end']
    list_filter = ['status', 'plan', 'billing_cycle']
    search_fields = ['user__email', 'stripe_customer_id']
    raw_id_fields = ['user']


@admin.register(UsageQuota)
class UsageQuotaAdmin(admin.ModelAdmin):
    list_display = ['user', 'period_start', 'stories_created', 'tokens_used', 'generation_cost_usd']
    list_filter = ['period_start']
    search_fields = ['user__email']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency']
    search_fields = ['user__email', 'stripe_payment_intent_id']
