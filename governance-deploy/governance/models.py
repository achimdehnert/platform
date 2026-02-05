"""
DDL Governance Models - Standalone Deployment
Tables exist in platform schema - managed=False
"""
from django.db import models


class LookupDomain(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    name_de = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform"."lkp_domain'
        managed = False

    def __str__(self):
        return f"{self.code}: {self.name}"


class LookupChoice(models.Model):
    domain = models.ForeignKey(LookupDomain, on_delete=models.CASCADE, related_name="choices")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    name_de = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform"."lkp_choice'
        managed = False

    def __str__(self):
        return f"{self.domain.code}.{self.code}: {self.name}"


class BusinessCase(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    category = models.ForeignKey(LookupChoice, on_delete=models.PROTECT, related_name="business_cases_by_category")
    status = models.ForeignKey(LookupChoice, on_delete=models.PROTECT, related_name="business_cases_by_status")
    priority = models.ForeignKey(LookupChoice, on_delete=models.PROTECT, related_name="business_cases_by_priority", null=True, blank=True)
    problem_statement = models.TextField()
    target_audience = models.TextField(blank=True)
    expected_benefits = models.JSONField(default=list, blank=True)
    scope = models.TextField(blank=True)
    out_of_scope = models.JSONField(default=list, blank=True)
    success_criteria = models.JSONField(default=list, blank=True)
    assumptions = models.JSONField(default=list, blank=True)
    risks = models.JSONField(default=list, blank=True)
    requires_adr = models.BooleanField(default=False)
    adr_reason = models.TextField(blank=True)
    owner_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform"."dom_business_case'
        managed = False
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code}: {self.title}"


class UseCase(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    business_case = models.ForeignKey(BusinessCase, on_delete=models.CASCADE, related_name="use_cases")
    status = models.ForeignKey(LookupChoice, on_delete=models.PROTECT, related_name="use_cases_by_status")
    priority = models.ForeignKey(LookupChoice, on_delete=models.PROTECT, related_name="use_cases_by_priority", null=True, blank=True)
    actor = models.CharField(max_length=100)
    preconditions = models.JSONField(default=list, blank=True)
    postconditions = models.JSONField(default=list, blank=True)
    main_flow = models.JSONField(default=list, blank=True)
    alternative_flows = models.JSONField(default=list, blank=True)
    exception_flows = models.JSONField(default=list, blank=True)
    complexity = models.ForeignKey(LookupChoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="use_cases_by_complexity")
    estimated_effort = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform"."dom_use_case'
        managed = False
        ordering = ["business_case", "code"]

    def __str__(self):
        return f"{self.code}: {self.title}"
