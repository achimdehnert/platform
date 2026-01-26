#!/usr/bin/env python3
"""
Autonomer Hetzner Deployment Error Analyzer & Self-Healer

Verwendung:
    python hetzner_auto_healer.py --log deploy.log
    python hetzner_auto_healer.py --log deploy.log --auto-fix
    
    # Als GitHub Action:
    python hetzner_auto_healer.py --log $GITHUB_STEP_SUMMARY --ci-mode
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx  # oder: import anthropic


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Category(Enum):
    INFRASTRUCTURE = "INFRASTRUCTURE"
    BUILD = "BUILD"
    DEPLOY = "DEPLOY"
    RUNTIME = "RUNTIME"
    NETWORK = "NETWORK"
    PERMISSION = "PERMISSION"


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class ErrorAnalysis:
    category: Category
    severity: Severity
    confidence: int
    root_cause: str
    error_pattern: str


@dataclass
class ProposedFix:
    action: str  # AUTO-FIX or HUMAN_REVIEW
    risk: RiskLevel
    commands: list[str]
    rollback: list[str]
    validation: list[str]
    prevention: str


# ============================================================================
# HETZNER-SPEZIFISCHE ERROR PATTERNS
# ============================================================================

HETZNER_ERROR_PATTERNS = {
    # Terraform/Hetzner API Errors
    r"429 Too Many Requests": {
        "category": Category.INFRASTRUCTURE,
        "severity": Severity.MEDIUM,
        "confidence": 95,
        "root_cause": "Hetzner API Rate Limit erreicht",
        "fix": {
            "action": "AUTO-FIX",
            "risk": RiskLevel.LOW,
            "commands": [
                "sleep 60",
                "terraform apply -auto-approve",
            ],
            "rollback": ["terraform destroy -auto-approve"],
            "validation": ["terraform plan -detailed-exitcode"],
            "prevention": "Implementiere exponential backoff in CI/CD",
        },
    },
    r"server_type .* not available": {
        "category": Category.INFRASTRUCTURE,
        "severity": Severity.HIGH,
        "confidence": 90,
        "root_cause": "Gewünschter Server-Typ in Region nicht verfügbar",
        "fix": {
            "action": "HUMAN_REVIEW",
            "risk": RiskLevel.MEDIUM,
            "commands": [
                "# Alternative Server-Typen prüfen:",
                "hcloud server-type list",
                "# Oder Region wechseln: nbg1, fsn1, hel1",
            ],
            "rollback": [],
            "validation": ["hcloud server-type describe <type>"],
            "prevention": "Fallback Server-Typen in Terraform definieren",
        },
    },
    r"Error acquiring.*state lock": {
        "category": Category.INFRASTRUCTURE,
        "severity": Severity.MEDIUM,
        "confidence": 92,
        "root_cause": "Terraform State ist gesperrt (vorheriger Run abgebrochen?)",
        "fix": {
            "action": "AUTO-FIX",
            "risk": RiskLevel.LOW,
            "commands": [
                "# Lock ID aus Fehlermeldung extrahieren",
                "terraform force-unlock -force <LOCK_ID>",
                "terraform apply -auto-approve",
            ],
            "rollback": [],
            "validation": ["terraform state list"],
            "prevention": "Verwende Remote State mit Lock-Timeout",
        },
    },
    # Docker Errors
    r"manifest.*not found|manifest unknown": {
        "category": Category.BUILD,
        "severity": Severity.HIGH,
        "confidence": 95,
        "root_cause": "Docker Image Tag existiert nicht in Registry",
        "fix": {
            "action": "AUTO-FIX",
            "risk": RiskLevel.LOW,
            "commands": [
                "# Verfügbare Tags prüfen",
                "docker manifest inspect <image>:latest",
                "# Fallback auf latest oder vorheriges Tag",
                "sed -i 's/:v[0-9.]*/:latest/g' docker-compose.yml",
                "docker-compose pull && docker-compose up -d",
            ],
            "rollback": ["git checkout docker-compose.yml"],
            "validation": ["docker-compose ps", "curl -f localhost:8000/health"],
            "prevention": "Pre-deployment Image-Check hinzufügen",
        },
    },
    r"no space left on device": {
        "category": Category.RUNTIME,
        "severity": Severity.CRITICAL,
        "confidence": 98,
        "root_cause": "Festplatte voll",
        "fix": {
            "action": "AUTO-FIX",
            "risk": RiskLevel.LOW,
            "commands": [
                "docker system prune -af --volumes",
                "journalctl --vacuum-size=100M",
                "apt-get clean",
                "rm -rf /tmp/*",
            ],
            "rollback": [],
            "validation": ["df -h"],
            "prevention": "Disk-Space Monitoring mit Alerting einrichten",
        },
    },
    r"OOMKilled|out of memory": {
        "category": Category.RUNTIME,
        "severity": Severity.HIGH,
        "confidence": 90,
        "root_cause": "Container hat Memory-Limit überschritten",
        "fix": {
            "action": "HUMAN_REVIEW",
            "risk": RiskLevel.MEDIUM,
            "commands": [
                "# Memory-Limit in docker-compose.yml erhöhen:",
                "# deploy.resources.limits.memory: 2g",
                "docker stats --no-stream",
            ],
            "rollback": [],
            "validation": ["docker stats --no-stream"],
            "prevention": "Memory-Profiling durchführen, Limits anpassen",
        },
    },
    r"port.*already.*in use|address already in use": {
        "category": Category.DEPLOY,
        "severity": Severity.MEDIUM,
        "confidence": 95,
        "root_cause": "Port wird bereits von anderem Prozess verwendet",
        "fix": {
            "action": "AUTO-FIX",
            "risk": RiskLevel.LOW,
            "commands": [
                "# Prozess auf Port finden und stoppen",
                "lsof -i :<PORT> | awk 'NR>1 {print $2}' | xargs -r kill -9",
                "docker-compose down && docker-compose up -d",
            ],
            "rollback": [],
            "validation": ["docker-compose ps", "netstat -tlnp | grep <PORT>"],
            "prevention": "Health-Check vor Deployment, der alte Container stoppt",
        },
    },
    # SSH/Permission Errors
    r"Permission denied \(publickey\)": {
        "category": Category.PERMISSION,
        "severity": Severity.HIGH,
        "confidence": 88,
        "root_cause": "SSH-Key nicht akzeptiert (falscher Key oder Permissions)",
        "fix": {
            "action": "AUTO-FIX",
            "risk": RiskLevel.LOW,
            "commands": [
                "chmod 600 ~/.ssh/id_*",
                "chmod 700 ~/.ssh",
                "eval $(ssh-agent -s) && ssh-add ~/.ssh/id_ed25519",
                "ssh -vvv user@host  # Debug-Ausgabe",
            ],
            "rollback": [],
            "validation": ["ssh -T user@host echo 'OK'"],
            "prevention": "SSH-Key Deployment automatisieren (cloud-init)",
        },
    },
    r"Host key verification failed": {
        "category": Category.PERMISSION,
        "severity": Severity.MEDIUM,
        "confidence": 95,
        "root_cause": "Server Host-Key nicht in known_hosts",
        "fix": {
            "action": "AUTO-FIX",
            "risk": RiskLevel.LOW,
            "commands": [
                "ssh-keyscan -H <HOST> >> ~/.ssh/known_hosts",
                "# Oder für CI/CD:",
                "ssh -o StrictHostKeyChecking=accept-new user@host",
            ],
            "rollback": [],
            "validation": ["ssh user@host echo 'OK'"],
            "prevention": "Host-Keys im CI/CD Secret speichern",
        },
    },
    # Network Errors
    r"connection refused|ECONNREFUSED": {
        "category": Category.NETWORK,
        "severity": Severity.HIGH,
        "confidence": 75,
        "root_cause": "Service nicht erreichbar (nicht gestartet oder Firewall)",
        "fix": {
            "action": "HUMAN_REVIEW",
            "risk": RiskLevel.MEDIUM,
            "commands": [
                "# Service-Status prüfen",
                "docker-compose ps",
                "systemctl status <service>",
                "# Firewall prüfen",
                "ufw status",
                "hcloud firewall list",
            ],
            "rollback": [],
            "validation": ["curl -v localhost:<PORT>"],
            "prevention": "Health-Checks und Retry-Logic implementieren",
        },
    },
}


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """Du bist ein autonomer DevOps-Agent für Hetzner Cloud Deployments.
Analysiere den folgenden Fehler und generiere eine strukturierte Lösung.

## OUTPUT FORMAT (JSON)
{
  "analysis": {
    "category": "INFRASTRUCTURE|BUILD|DEPLOY|RUNTIME|NETWORK|PERMISSION",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW",
    "confidence": 0-100,
    "root_cause": "Beschreibung",
    "matched_pattern": "Falls bekanntes Pattern"
  },
  "fix": {
    "action": "AUTO-FIX|HUMAN_REVIEW",
    "risk": "LOW|MEDIUM|HIGH",
    "commands": ["cmd1", "cmd2"],
    "rollback": ["rollback_cmd"],
    "validation": ["check_cmd"],
    "prevention": "Empfehlung"
  }
}

## REGELN
1. NIEMALS Secrets/Credentials im Output
2. IMMER Rollback-Befehle angeben
3. Bei confidence < 85% → HUMAN_REVIEW
4. Konkrete, copy-paste-fähige Befehle

## KONTEXT
Plattform: Hetzner Cloud
Tools: Terraform (hcloud), Ansible, Docker Compose"""


# ============================================================================
# CORE LOGIC
# ============================================================================


def match_known_pattern(error_log: str) -> Optional[dict]:
    """Prüft ob der Fehler einem bekannten Pattern entspricht."""
    for pattern, config in HETZNER_ERROR_PATTERNS.items():
        if re.search(pattern, error_log, re.IGNORECASE):
            return {
                "pattern": pattern,
                **config,
            }
    return None


def analyze_with_llm(error_log: str, context: dict) -> dict:
    """Sendet Fehler an Claude für Analyse."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY nicht gesetzt")

    prompt = f"""Analysiere diesen Deployment-Fehler:

KONTEXT:
{json.dumps(context, indent=2)}

ERROR LOG:
{error_log}

Antworte NUR mit validem JSON."""

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2048,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60.0,
    )
    response.raise_for_status()

    content = response.json()["content"][0]["text"]

    # JSON aus Response extrahieren
    json_match = re.search(r"\{[\s\S]*\}", content)
    if json_match:
        return json.loads(json_match.group())
    raise ValueError(f"Konnte kein JSON aus Response extrahieren: {content}")


def execute_fix(fix: dict, dry_run: bool = True) -> bool:
    """Führt die Fix-Befehle aus."""
    if fix["action"] == "HUMAN_REVIEW":
        print("\n⚠️  HUMAN REVIEW ERFORDERLICH")
        print("Vorgeschlagene Befehle:")
        for cmd in fix["commands"]:
            print(f"  $ {cmd}")
        return False

    if fix["risk"] != "LOW":
        print(f"\n⚠️  Risk Level: {fix['risk']} - Manuelle Bestätigung erforderlich")
        return False

    print("\n🔧 Führe Auto-Fix aus...")
    for cmd in fix["commands"]:
        # Kommentare überspringen
        if cmd.strip().startswith("#"):
            print(f"  # {cmd}")
            continue

        print(f"  $ {cmd}")

        if dry_run:
            print("    [DRY RUN - nicht ausgeführt]")
            continue

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                print(f"    ❌ Fehler: {result.stderr}")
                return False
            print(f"    ✅ OK")
        except subprocess.TimeoutExpired:
            print(f"    ⏱️ Timeout")
            return False

    return True


def validate_fix(fix: dict) -> bool:
    """Validiert ob der Fix erfolgreich war."""
    print("\n🔍 Validiere Fix...")
    for cmd in fix.get("validation", []):
        print(f"  $ {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    ❌ Validierung fehlgeschlagen")
            return False
        print(f"    ✅ OK")
    return True


def format_output(analysis: dict, fix: dict, format_type: str = "console") -> str:
    """Formatiert die Ausgabe."""
    if format_type == "json":
        return json.dumps({"analysis": analysis, "fix": fix}, indent=2)

    if format_type == "markdown":
        return f"""## 🔍 Fehler-Analyse

| Feld | Wert |
|------|------|
| Kategorie | {analysis.get('category', 'UNKNOWN')} |
| Schweregrad | {analysis.get('severity', 'UNKNOWN')} |
| Confidence | {analysis.get('confidence', 0)}% |

**Root Cause:** {analysis.get('root_cause', 'Unbekannt')}

---

## 🔧 Reparatur-Vorschlag

**Aktion:** {fix.get('action', 'HUMAN_REVIEW')}
**Risiko:** {fix.get('risk', 'UNKNOWN')}

### Befehle
```bash
{chr(10).join(fix.get('commands', []))}
```

### Rollback
```bash
{chr(10).join(fix.get('rollback', ['# Kein Rollback definiert']))}
```

### Validierung
```bash
{chr(10).join(fix.get('validation', ['# Keine Validierung definiert']))}
```

---

## 📊 Prävention

{fix.get('prevention', 'Keine Empfehlung')}
"""

    # Console format
    output = []
    output.append("\n" + "=" * 60)
    output.append("🔍 FEHLER-ANALYSE")
    output.append("=" * 60)
    output.append(f"Kategorie:   {analysis.get('category', 'UNKNOWN')}")
    output.append(f"Schweregrad: {analysis.get('severity', 'UNKNOWN')}")
    output.append(f"Confidence:  {analysis.get('confidence', 0)}%")
    output.append(f"Root Cause:  {analysis.get('root_cause', 'Unbekannt')}")

    output.append("\n" + "-" * 60)
    output.append("🔧 REPARATUR-VORSCHLAG")
    output.append("-" * 60)
    output.append(f"Aktion: {fix.get('action', 'HUMAN_REVIEW')}")
    output.append(f"Risiko: {fix.get('risk', 'UNKNOWN')}")
    output.append("\nBefehle:")
    for cmd in fix.get("commands", []):
        output.append(f"  $ {cmd}")

    if fix.get("rollback"):
        output.append("\nRollback:")
        for cmd in fix["rollback"]:
            output.append(f"  $ {cmd}")

    output.append("\n" + "-" * 60)
    output.append(f"📊 Prävention: {fix.get('prevention', 'Keine Empfehlung')}")
    output.append("=" * 60 + "\n")

    return "\n".join(output)


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Autonomer Hetzner Deployment Error Analyzer"
    )
    parser.add_argument("--log", "-l", required=True, help="Pfad zur Log-Datei")
    parser.add_argument(
        "--auto-fix", action="store_true", help="Sichere Fixes automatisch ausführen"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Befehle nur anzeigen"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["console", "json", "markdown"],
        default="console",
        help="Ausgabe-Format",
    )
    parser.add_argument(
        "--ci-mode", action="store_true", help="CI/CD Modus (Exit-Code basierend)"
    )
    parser.add_argument("--project", help="Projekt-Name für Kontext")
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "production"],
        default="production",
        help="Environment",
    )

    args = parser.parse_args()

    # Log einlesen
    log_path = Path(args.log)
    if not log_path.exists():
        print(f"❌ Log-Datei nicht gefunden: {log_path}")
        sys.exit(1)

    error_log = log_path.read_text()

    # Kontext erstellen
    context = {
        "project": args.project or os.environ.get("PROJECT_NAME", "unknown"),
        "environment": args.env,
        "ci_run": os.environ.get("GITHUB_RUN_ID", os.environ.get("CI_JOB_ID", "local")),
    }

    print(f"🚀 Analysiere Fehler aus: {log_path}")

    # 1. Erst bekannte Patterns prüfen
    known_match = match_known_pattern(error_log)

    if known_match:
        print(f"✅ Bekanntes Pattern gefunden: {known_match['pattern']}")
        analysis = {
            "category": known_match["category"].value,
            "severity": known_match["severity"].value,
            "confidence": known_match["confidence"],
            "root_cause": known_match["root_cause"],
            "matched_pattern": known_match["pattern"],
        }
        fix = {
            "action": known_match["fix"]["action"],
            "risk": known_match["fix"]["risk"].value,
            "commands": known_match["fix"]["commands"],
            "rollback": known_match["fix"]["rollback"],
            "validation": known_match["fix"]["validation"],
            "prevention": known_match["fix"]["prevention"],
        }
    else:
        # 2. LLM-Analyse für unbekannte Fehler
        print("🤖 Kein bekanntes Pattern - LLM-Analyse...")
        try:
            result = analyze_with_llm(error_log, context)
            analysis = result.get("analysis", {})
            fix = result.get("fix", {})
        except Exception as e:
            print(f"❌ LLM-Analyse fehlgeschlagen: {e}")
            sys.exit(1)

    # Ausgabe formatieren
    output = format_output(analysis, fix, args.format)
    print(output)

    # Auto-Fix ausführen wenn gewünscht
    if args.auto_fix and not args.dry_run:
        if analysis.get("confidence", 0) >= 85 and fix.get("risk") == "LOW":
            success = execute_fix(fix, dry_run=False)
            if success:
                validate_fix(fix)
        else:
            print("\n⚠️  Auto-Fix nicht möglich (confidence < 85% oder risk > LOW)")

    # CI-Mode Exit-Code
    if args.ci_mode:
        if fix.get("action") == "AUTO-FIX" and analysis.get("confidence", 0) >= 85:
            sys.exit(0)  # Kann automatisch behoben werden
        else:
            sys.exit(1)  # Braucht Human Review


if __name__ == "__main__":
    main()
