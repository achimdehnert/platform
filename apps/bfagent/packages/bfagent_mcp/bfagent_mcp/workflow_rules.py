"""
Workflow Rules Engine for BF Agent MCP.

Defines and enforces rules for Initiatives and Requirements workflow.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class RuleSeverity(Enum):
    """Severity levels for rule violations."""
    ERROR = "error"      # Must fix before proceeding
    WARNING = "warning"  # Should fix, but can proceed
    INFO = "info"        # Suggestion for improvement


class RuleCategory(Enum):
    """Categories of workflow rules."""
    WORKFLOW = "workflow"
    DOCUMENTATION = "documentation"
    NAMING = "naming"
    ACTIVITY = "activity"


@dataclass
class RuleViolation:
    """A single rule violation."""
    rule_id: str
    rule_name: str
    category: RuleCategory
    severity: RuleSeverity
    message: str
    suggestion: str
    field: Optional[str] = None


@dataclass
class RuleCheckResult:
    """Result of checking all rules."""
    passed: bool
    violations: List[RuleViolation] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    infos: int = 0
    
    def add_violation(self, violation: RuleViolation):
        self.violations.append(violation)
        if violation.severity == RuleSeverity.ERROR:
            self.errors += 1
            self.passed = False
        elif violation.severity == RuleSeverity.WARNING:
            self.warnings += 1
        else:
            self.infos += 1


# =============================================================================
# RULE DEFINITIONS
# =============================================================================

WORKFLOW_RULES = {
    # Initiative Workflow Rules
    "INIT_001": {
        "name": "analysis_before_concept",
        "category": RuleCategory.WORKFLOW,
        "severity": RuleSeverity.ERROR,
        "description": "Analyse muss ausgefüllt sein bevor Konzept-Phase",
        "check_field": "analysis",
        "applies_to": "initiative",
        "when_status": ["concept", "planning", "in_progress"],
    },
    "INIT_002": {
        "name": "concept_before_planning",
        "category": RuleCategory.WORKFLOW,
        "severity": RuleSeverity.ERROR,
        "description": "Konzept muss ausgefüllt sein bevor Planning-Phase",
        "check_field": "concept",
        "applies_to": "initiative",
        "when_status": ["planning", "in_progress"],
    },
    "INIT_003": {
        "name": "requirements_before_progress",
        "category": RuleCategory.WORKFLOW,
        "severity": RuleSeverity.WARNING,
        "description": "Requirements sollten existieren bevor in_progress",
        "check_field": "requirements_count",
        "min_value": 1,
        "applies_to": "initiative",
        "when_status": ["in_progress"],
    },
    "INIT_004": {
        "name": "lessons_on_complete",
        "category": RuleCategory.DOCUMENTATION,
        "severity": RuleSeverity.WARNING,
        "description": "Lessons Learned sollte bei Abschluss dokumentiert sein",
        "check_field": "lessons_learned",
        "applies_to": "initiative",
        "when_status": ["completed"],
    },
    
    # Documentation Rules
    "DOC_001": {
        "name": "description_min_length",
        "category": RuleCategory.DOCUMENTATION,
        "severity": RuleSeverity.WARNING,
        "description": "Beschreibung sollte aussagekräftig sein (mind. 50 Zeichen)",
        "check_field": "description",
        "min_length": 50,
        "applies_to": "both",
    },
    "DOC_002": {
        "name": "next_steps_when_in_progress",
        "category": RuleCategory.DOCUMENTATION,
        "severity": RuleSeverity.INFO,
        "description": "Nächste Schritte sollten dokumentiert sein während Bearbeitung",
        "check_field": "next_steps",
        "applies_to": "initiative",
        "when_status": ["in_progress"],
    },
    "DOC_003": {
        "name": "blockers_documented",
        "category": RuleCategory.DOCUMENTATION,
        "severity": RuleSeverity.INFO,
        "description": "Blocker sollten dokumentiert werden wenn vorhanden",
        "check_field": "blockers",
        "applies_to": "initiative",
        "when_status": ["blocked"],
    },
    
    # Naming Rules
    "NAME_001": {
        "name": "title_not_generic",
        "category": RuleCategory.NAMING,
        "severity": RuleSeverity.WARNING,
        "description": "Titel sollte spezifisch sein (nicht 'Test', 'TODO', etc.)",
        "check_field": "title",
        "forbidden_values": ["test", "todo", "fix", "bug", "feature", "task"],
        "applies_to": "both",
    },
    "NAME_002": {
        "name": "title_min_length",
        "category": RuleCategory.NAMING,
        "severity": RuleSeverity.WARNING,
        "description": "Titel sollte aussagekräftig sein (mind. 10 Zeichen)",
        "check_field": "title",
        "min_length": 10,
        "applies_to": "both",
    },
    
    # Activity Rules
    "ACT_001": {
        "name": "activity_on_status_change",
        "category": RuleCategory.ACTIVITY,
        "severity": RuleSeverity.INFO,
        "description": "Statusänderungen sollten als Activity geloggt werden",
        "check_field": "activities_count",
        "min_value": 1,
        "applies_to": "initiative",
        "when_status": ["concept", "planning", "in_progress", "review", "completed"],
    },
    
    # Requirement-specific Rules
    "REQ_001": {
        "name": "requirement_description",
        "category": RuleCategory.DOCUMENTATION,
        "severity": RuleSeverity.WARNING,
        "description": "Requirement sollte eine Beschreibung haben",
        "check_field": "description",
        "min_length": 20,
        "applies_to": "requirement",
    },
    "REQ_002": {
        "name": "requirement_acceptance_criteria",
        "category": RuleCategory.DOCUMENTATION,
        "severity": RuleSeverity.INFO,
        "description": "Requirement sollte Akzeptanzkriterien definieren",
        "check_field": "acceptance_criteria",
        "applies_to": "requirement",
        "when_status": ["ready", "in_progress"],
    },
}


class WorkflowRulesEngine:
    """Engine for checking workflow rules."""
    
    def __init__(self):
        self.rules = WORKFLOW_RULES
    
    def check_initiative(self, initiative, target_status: str = None) -> RuleCheckResult:
        """Check all rules for an Initiative."""
        result = RuleCheckResult(passed=True)
        
        # Determine which status to check against
        check_status = target_status or initiative.status
        
        for rule_id, rule in self.rules.items():
            if rule["applies_to"] not in ["initiative", "both"]:
                continue
            
            # Check if rule applies to current/target status
            if "when_status" in rule and check_status not in rule["when_status"]:
                continue
            
            violation = self._check_rule(initiative, rule_id, rule)
            if violation:
                result.add_violation(violation)
        
        return result
    
    def check_requirement(self, requirement, target_status: str = None) -> RuleCheckResult:
        """Check all rules for a Requirement."""
        result = RuleCheckResult(passed=True)
        
        check_status = target_status or requirement.status
        
        for rule_id, rule in self.rules.items():
            if rule["applies_to"] not in ["requirement", "both"]:
                continue
            
            if "when_status" in rule and check_status not in rule["when_status"]:
                continue
            
            violation = self._check_rule(requirement, rule_id, rule)
            if violation:
                result.add_violation(violation)
        
        return result
    
    def _check_rule(self, obj, rule_id: str, rule: dict) -> Optional[RuleViolation]:
        """Check a single rule against an object."""
        field_name = rule.get("check_field")
        if not field_name:
            return None
        
        # Get field value
        if field_name == "requirements_count":
            value = obj.requirements.count() if hasattr(obj, 'requirements') else 0
        elif field_name == "activities_count":
            value = obj.activities.count() if hasattr(obj, 'activities') else 0
        else:
            value = getattr(obj, field_name, None)
        
        # Check min_length
        if "min_length" in rule:
            if not value or len(str(value)) < rule["min_length"]:
                return RuleViolation(
                    rule_id=rule_id,
                    rule_name=rule["name"],
                    category=rule["category"],
                    severity=rule["severity"],
                    message=rule["description"],
                    suggestion=f"Feld '{field_name}' sollte mind. {rule['min_length']} Zeichen haben",
                    field=field_name
                )
        
        # Check min_value
        if "min_value" in rule:
            if value is None or value < rule["min_value"]:
                return RuleViolation(
                    rule_id=rule_id,
                    rule_name=rule["name"],
                    category=rule["category"],
                    severity=rule["severity"],
                    message=rule["description"],
                    suggestion=f"Feld '{field_name}' sollte mind. {rule['min_value']} sein",
                    field=field_name
                )
        
        # Check forbidden_values
        if "forbidden_values" in rule:
            if value and str(value).lower().strip() in rule["forbidden_values"]:
                return RuleViolation(
                    rule_id=rule_id,
                    rule_name=rule["name"],
                    category=rule["category"],
                    severity=rule["severity"],
                    message=rule["description"],
                    suggestion=f"Titel sollte spezifischer sein als '{value}'",
                    field=field_name
                )
        
        # Check if field is empty (for required fields)
        if "min_length" not in rule and "min_value" not in rule and "forbidden_values" not in rule:
            if not value or (isinstance(value, str) and not value.strip()):
                return RuleViolation(
                    rule_id=rule_id,
                    rule_name=rule["name"],
                    category=rule["category"],
                    severity=rule["severity"],
                    message=rule["description"],
                    suggestion=f"Feld '{field_name}' sollte ausgefüllt sein",
                    field=field_name
                )
        
        return None
    
    def get_rules_for_category(self, category: str) -> Dict[str, dict]:
        """Get all rules for a specific category."""
        if category == "all":
            return self.rules
        
        return {
            rule_id: rule 
            for rule_id, rule in self.rules.items()
            if rule["category"].value == category
        }
    
    def format_rules_markdown(self, category: str = "all") -> str:
        """Format rules as Markdown documentation."""
        rules = self.get_rules_for_category(category)
        
        lines = ["# Workflow Rules\n"]
        
        # Group by category
        by_category = {}
        for rule_id, rule in rules.items():
            cat = rule["category"].value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append((rule_id, rule))
        
        for cat, cat_rules in by_category.items():
            lines.append(f"\n## {cat.title()}\n")
            lines.append("| ID | Name | Severity | Description |")
            lines.append("|-----|------|----------|-------------|")
            
            for rule_id, rule in cat_rules:
                severity_icon = {
                    RuleSeverity.ERROR: "🔴",
                    RuleSeverity.WARNING: "🟡",
                    RuleSeverity.INFO: "🔵"
                }.get(rule["severity"], "")
                
                lines.append(
                    f"| `{rule_id}` | {rule['name']} | {severity_icon} {rule['severity'].value} | {rule['description']} |"
                )
        
        return "\n".join(lines)
    
    def format_result_markdown(self, result: RuleCheckResult) -> str:
        """Format check result as Markdown."""
        lines = []
        
        if result.passed:
            lines.append("## ✅ Alle Regeln erfüllt\n")
        else:
            lines.append("## ❌ Regelverletzungen gefunden\n")
        
        lines.append(f"**Ergebnis:** {result.errors} Fehler, {result.warnings} Warnungen, {result.infos} Hinweise\n")
        
        if result.violations:
            lines.append("\n### Violations\n")
            
            for v in result.violations:
                icon = {
                    RuleSeverity.ERROR: "🔴",
                    RuleSeverity.WARNING: "🟡",
                    RuleSeverity.INFO: "🔵"
                }.get(v.severity, "")
                
                lines.append(f"#### {icon} {v.rule_id}: {v.rule_name}")
                lines.append(f"- **Kategorie:** {v.category.value}")
                lines.append(f"- **Meldung:** {v.message}")
                lines.append(f"- **Vorschlag:** {v.suggestion}")
                if v.field:
                    lines.append(f"- **Feld:** `{v.field}`")
                lines.append("")
        
        return "\n".join(lines)
