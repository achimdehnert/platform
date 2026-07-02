"""DDL Governance Admin - Simplified"""
from django.contrib import admin
from .models import LookupDomain, LookupChoice, BusinessCase, UseCase


@admin.register(LookupDomain)
class LookupDomainAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    search_fields = ["code", "name"]


@admin.register(LookupChoice)
class LookupChoiceAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "domain", "sort_order", "is_active"]
    list_filter = ["domain", "is_active"]
    search_fields = ["code", "name"]


@admin.register(BusinessCase)
class BusinessCaseAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "status", "category"]
    list_filter = ["status", "category"]
    search_fields = ["code", "title"]


@admin.register(UseCase)
class UseCaseAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "business_case", "status"]
    list_filter = ["status"]
    search_fields = ["code", "title"]
