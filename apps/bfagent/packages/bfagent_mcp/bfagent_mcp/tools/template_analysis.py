"""
Template Analysis Tools for BF Agent MCP.

Tools zur Analyse von Django Templates:
- Duplikat-Erkennung
- Template-Lade-Reihenfolge
- Cleanup mit Backup
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..server import mcp, logger

# Project root detection
def _get_project_root() -> Path:
    """Find Django project root."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "manage.py").exists():
            return parent
    return Path.cwd()


@mcp.tool()
def find_duplicate_templates(
    template_path: Optional[str] = None,
) -> dict:
    """
    Findet duplizierte Django Templates und zeigt welches Django lädt.
    
    Django lädt Templates in dieser Reihenfolge:
    1. DIRS in TEMPLATES setting (meist 'templates/' im Root)
    2. APP_DIRS: templates/ Ordner in jeder App
    
    Args:
        template_path: Optional: Spezifischer Template-Pfad zu prüfen 
                      (z.B. "bfagent/controlling/dashboard.html")
        
    Returns:
        Dict mit gefundenen Duplikaten und welches aktiv ist
    """
    logger.info(f"Scanning for duplicate templates")
    
    root = _get_project_root()
    
    # Finde alle Template-Verzeichnisse
    template_dirs = []
    
    # 1. Root templates/ (höchste Priorität)
    root_templates = root / "templates"
    if root_templates.exists():
        template_dirs.append(("ROOT (DIRS)", root_templates))
    
    # 2. App templates/ (niedrigere Priorität)
    apps_dir = root / "apps"
    if apps_dir.exists():
        for app_dir in sorted(apps_dir.iterdir()):
            if app_dir.is_dir():
                app_templates = app_dir / "templates"
                if app_templates.exists():
                    template_dirs.append((f"APP ({app_dir.name})", app_templates))
    
    # Sammle alle Templates
    all_templates = {}
    
    for priority, (source, base_dir) in enumerate(template_dirs):
        for template_file in base_dir.rglob("*.html"):
            rel_path = template_file.relative_to(base_dir)
            rel_str = str(rel_path).replace("\\", "/")
            
            if rel_str not in all_templates:
                all_templates[rel_str] = []
            
            all_templates[rel_str].append({
                "priority": priority,
                "source": source,
                "full_path": str(template_file),
                "size": template_file.stat().st_size,
            })
    
    # Finde Duplikate
    duplicates = {k: v for k, v in all_templates.items() if len(v) > 1}
    
    # Wenn spezifischer Pfad angegeben
    if template_path:
        template_path = template_path.replace("\\", "/")
        if template_path in all_templates:
            locations = all_templates[template_path]
            active = min(locations, key=lambda x: x["priority"])
            return {
                "template_path": template_path,
                "is_duplicate": len(locations) > 1,
                "active_template": {
                    "source": active["source"],
                    "path": active["full_path"],
                },
                "all_locations": locations,
                "warning": f"⚠️ DUPLIKAT! Django lädt '{active['source']}', andere werden ignoriert!" if len(locations) > 1 else None,
            }
        else:
            return {
                "template_path": template_path,
                "error": f"Template '{template_path}' nicht gefunden",
            }
    
    # Allgemeine Duplikat-Analyse
    results = {
        "total_templates": len(all_templates),
        "duplicate_count": len(duplicates),
        "duplicates": {},
    }
    
    for rel_path, locations in duplicates.items():
        active = min(locations, key=lambda x: x["priority"])
        results["duplicates"][rel_path] = {
            "active": active["source"],
            "ignored": [loc["source"] for loc in locations if loc["priority"] != active["priority"]],
        }
    
    if duplicates:
        results["summary"] = f"⚠️ {len(duplicates)} duplizierte Templates gefunden!"
    else:
        results["summary"] = "✅ Keine duplizierten Templates."
    
    return results


@mcp.tool()
def cleanup_duplicate_templates(
    dry_run: bool = True,
    keep_source: str = "ROOT",
) -> dict:
    """
    Bereinigt duplizierte Templates mit Backup.
    
    SICHERHEIT:
    - Erstellt automatisch Backup vor dem Löschen
    - dry_run=True zeigt nur was gelöscht würde
    - Backup-Ordner: .template_backup_YYYYMMDD_HHMMSS/
    
    Args:
        dry_run: True = nur anzeigen, False = wirklich löschen
        keep_source: Welche Quelle behalten ("ROOT" oder "APP")
        
    Returns:
        Dict mit Aktionen und Backup-Pfad
    """
    logger.info(f"Cleanup duplicate templates (dry_run={dry_run}, keep={keep_source})")
    
    root = _get_project_root()
    
    # Finde Duplikate
    dup_result = find_duplicate_templates()
    duplicates = dup_result.get("duplicates", {})
    
    if not duplicates:
        return {"message": "Keine Duplikate zum Bereinigen.", "actions": []}
    
    # Backup-Verzeichnis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / f".template_backup_{timestamp}"
    
    actions = []
    files_to_delete = []
    
    for rel_path, info in duplicates.items():
        # Bestimme welche Version gelöscht wird
        active_source = info["active"]
        ignored_sources = info["ignored"]
        
        if keep_source == "ROOT" and "ROOT" in active_source:
            # ROOT behalten, APP löschen
            for ignored in ignored_sources:
                if "APP" in ignored:
                    app_name = ignored.replace("APP (", "").replace(")", "")
                    full_path = root / "apps" / app_name / "templates" / rel_path
                    if full_path.exists():
                        files_to_delete.append(full_path)
                        actions.append({
                            "action": "DELETE",
                            "file": str(full_path),
                            "reason": f"Duplikat von ROOT, wird ignoriert",
                        })
        elif keep_source == "APP":
            # APP behalten, ROOT löschen (selten gewünscht)
            if "ROOT" in active_source:
                full_path = root / "templates" / rel_path
                if full_path.exists():
                    files_to_delete.append(full_path)
                    actions.append({
                        "action": "DELETE", 
                        "file": str(full_path),
                        "reason": f"Duplikat, APP-Version bevorzugt",
                    })
    
    result = {
        "dry_run": dry_run,
        "files_to_delete": len(files_to_delete),
        "actions": actions,
    }
    
    if not dry_run and files_to_delete:
        # Backup erstellen
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backed_up = []
        deleted = []
        
        for file_path in files_to_delete:
            try:
                # Backup
                rel = file_path.relative_to(root)
                backup_path = backup_dir / rel
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)
                backed_up.append(str(backup_path))
                
                # Löschen
                file_path.unlink()
                deleted.append(str(file_path))
            except Exception as e:
                result["errors"] = result.get("errors", [])
                result["errors"].append(f"Fehler bei {file_path}: {e}")
        
        result["backup_dir"] = str(backup_dir)
        result["backed_up"] = backed_up
        result["deleted"] = deleted
        result["message"] = f"✅ {len(deleted)} Dateien gelöscht, Backup in {backup_dir}"
    else:
        result["message"] = f"🔍 Dry-Run: {len(files_to_delete)} Dateien würden gelöscht"
        result["hint"] = "Setze dry_run=False um wirklich zu löschen"
    
    return result


@mcp.tool()
def restore_template_backup(
    backup_dir: str,
) -> dict:
    """
    Stellt Templates aus einem Backup wieder her.
    
    Args:
        backup_dir: Pfad zum Backup-Verzeichnis (z.B. ".template_backup_20260116_143000")
        
    Returns:
        Dict mit wiederhergestellten Dateien
    """
    logger.info(f"Restoring templates from {backup_dir}")
    
    root = _get_project_root()
    backup_path = Path(backup_dir)
    
    if not backup_path.is_absolute():
        backup_path = root / backup_dir
    
    if not backup_path.exists():
        return {"error": f"Backup-Verzeichnis nicht gefunden: {backup_path}"}
    
    restored = []
    errors = []
    
    for backup_file in backup_path.rglob("*.html"):
        try:
            rel = backup_file.relative_to(backup_path)
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file, target)
            restored.append(str(target))
        except Exception as e:
            errors.append(f"Fehler bei {backup_file}: {e}")
    
    return {
        "restored": restored,
        "count": len(restored),
        "errors": errors if errors else None,
        "message": f"✅ {len(restored)} Dateien wiederhergestellt",
    }
