"""DLM Hub views."""

import json
import os
import shutil
import threading
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from .models import AnalysisRun, AnalysisIssue, ActionLog
from .services.analyzer import DocumentAnalyzer
from .services.mcphub_client import fetch_dlm_report_overview


@login_required
def dashboard(request):
    base_url = os.environ.get("MCPHUB_API_BASE_URL", "http://mcphub-api:8080")

    try:
        report = fetch_dlm_report_overview(
            base_url=base_url,
            timeout_seconds=2.0,
            cache_ttl_seconds=10,
        )
        kpis = report.kpis
        repositories = report.repositories
    except Exception:
        kpis = {
            "repositories": 0,
            "documents": 0,
            "current": 0,
            "stale": 0,
            "outdated": 0,
        }
        repositories = []

    # Get latest completed analysis run
    latest_run = AnalysisRun.objects.filter(
        status="completed"
    ).order_by("-created_at").first()
    
    # Get issue counts from latest run
    latest_stats = None
    redundancy_issues = []
    outdated_issues = []
    
    if latest_run:
        redundancy_issues = AnalysisIssue.objects.filter(
            analysis_run=latest_run,
            issue_type="redundancy",
            status="open"
        )[:5]
        
        outdated_issues = AnalysisIssue.objects.filter(
            analysis_run=latest_run,
            issue_type="outdated",
            status="open"
        )[:5]
        
        latest_stats = {
            "run": latest_run,
            "redundancy_count": AnalysisIssue.objects.filter(
                analysis_run=latest_run, issue_type="redundancy", status="open"
            ).count(),
            "outdated_count": AnalysisIssue.objects.filter(
                analysis_run=latest_run, issue_type="outdated", status="open"
            ).count(),
            "total_issues": AnalysisIssue.objects.filter(
                analysis_run=latest_run, status="open"
            ).count(),
        }

    context = {
        "kpis": kpis,
        "repositories": repositories,
        "latest_run": latest_run,
        "latest_stats": latest_stats,
        "redundancy_issues": redundancy_issues,
        "outdated_issues": outdated_issues,
    }
    return render(request, "dlm_hub/dashboard.html", context)


@login_required
def local_analysis(request):
    """Display local documentation analysis results from LLM analyzer."""
    analysis_file = Path(settings.BASE_DIR) / "docs" / "_full_analysis.json"
    
    analysis = None
    error = None
    
    if analysis_file.exists():
        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                analysis = json.load(f)
        except Exception as e:
            error = f"Error reading analysis file: {e}"
    else:
        error = "No analysis file found. Run the local LLM analyzer first."
    
    # Calculate stats
    stats = {}
    if analysis:
        meta = analysis.get("_metadata", {})
        summary = analysis.get("analysis_summary", {})
        stats = {
            "files_scanned": meta.get("files_scanned", 0),
            "files_total": meta.get("files_total", 0),
            "scan_time": meta.get("scan_time", ""),
            "model_used": meta.get("model_used", ""),
            "redundant_groups": summary.get("redundant_groups_found", 0),
            "outdated_count": summary.get("outdated_candidates_found", 0),
        }
    
    context = {
        "analysis": analysis,
        "stats": stats,
        "error": error,
        "redundancy_candidates": analysis.get("redundancy_candidates", []) if analysis else [],
        "outdated_candidates": analysis.get("outdated_candidates", []) if analysis else [],
        "structure_issues": analysis.get("structure_issues", []) if analysis else [],
    }
    return render(request, "dlm_hub/local_analysis.html", context)


@login_required
@require_POST
def trigger_scan(request):
    """Trigger a new analysis scan."""
    scan_type = request.POST.get("scan_type", "redundancy")
    max_files = int(request.POST.get("max_files", 100))
    
    analyzer = DocumentAnalyzer()
    run = analyzer.run_redundancy_scan(max_files=max_files, user=request.user)
    
    if run.status == "failed":
        messages.error(request, f"Scan failed: {run.error_message}")
    else:
        messages.success(
            request,
            f"Scan completed! Found {run.issue_count} issues in {run.files_scanned} files."
        )
    
    return redirect("dlm_hub:analysis-history")


@login_required
def analysis_history(request):
    """Show history of analysis runs."""
    runs = AnalysisRun.objects.all()[:20]
    
    # Stats
    total_runs = AnalysisRun.objects.count()
    completed_runs = AnalysisRun.objects.filter(status="completed").count()
    open_issues = AnalysisIssue.objects.filter(status="open").count()
    
    context = {
        "runs": runs,
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "open_issues": open_issues,
    }
    return render(request, "dlm_hub/analysis_history.html", context)


@login_required
def run_detail(request, run_id):
    """Show details of a specific analysis run."""
    run = get_object_or_404(AnalysisRun, id=run_id)
    issues = run.issues.all()
    
    # Group issues by type
    redundancy_issues = issues.filter(issue_type="redundancy")
    outdated_issues = issues.filter(issue_type="outdated")
    structure_issues = issues.filter(issue_type="structure")
    
    context = {
        "run": run,
        "issues": issues,
        "redundancy_issues": redundancy_issues,
        "outdated_issues": outdated_issues,
        "structure_issues": structure_issues,
    }
    return render(request, "dlm_hub/run_detail.html", context)


@login_required
def issue_list(request):
    """List all open issues."""
    status_filter = request.GET.get("status", "open")
    type_filter = request.GET.get("type", "")
    
    issues = AnalysisIssue.objects.all()
    
    if status_filter:
        issues = issues.filter(status=status_filter)
    if type_filter:
        issues = issues.filter(issue_type=type_filter)
    
    issues = issues[:100]
    
    context = {
        "issues": issues,
        "status_filter": status_filter,
        "type_filter": type_filter,
        "status_choices": AnalysisIssue.STATUS_CHOICES,
        "type_choices": AnalysisIssue.ISSUE_TYPE_CHOICES,
    }
    return render(request, "dlm_hub/issue_list.html", context)


@login_required
@require_POST
def resolve_issue(request, issue_id):
    """Mark an issue as resolved or ignored."""
    issue = get_object_or_404(AnalysisIssue, id=issue_id)
    action = request.POST.get("action", "ignore")
    
    from django.utils import timezone
    
    if action == "ignore":
        issue.status = "ignored"
        issue.resolved_at = timezone.now()
        issue.resolved_by = request.user
        issue.save()
        
        ActionLog.objects.create(
            issue=issue,
            action_type="ignore",
            executed_by=request.user,
            details={"reason": request.POST.get("reason", "")},
            success=True
        )
        messages.success(request, f"Issue ignored: {issue.file_path}")
    
    elif action == "resolve":
        issue.status = "resolved"
        issue.resolved_at = timezone.now()
        issue.resolved_by = request.user
        issue.save()
        
        ActionLog.objects.create(
            issue=issue,
            action_type="archive",
            executed_by=request.user,
            details={"note": request.POST.get("note", "Manually resolved")},
            success=True
        )
        messages.success(request, f"Issue resolved: {issue.file_path}")
    
    # Return to referrer or issue list
    next_url = request.POST.get("next", request.META.get("HTTP_REFERER"))
    if next_url:
        return redirect(next_url)
    return redirect("dlm_hub:issue-list")


@login_required
def api_scan_status(request, run_id):
    """API endpoint for checking scan status (for HTMX polling)."""
    run = get_object_or_404(AnalysisRun, id=run_id)
    
    return JsonResponse({
        "id": str(run.id),
        "status": run.status,
        "files_scanned": run.files_scanned,
        "files_total": run.files_total,
        "issue_count": run.issue_count,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
    })


# =============================================================================
# Feature 1: HTMX Polling - Async Scan with Live Updates
# =============================================================================

def _run_scan_async(run_id, docs_path, model, max_files, user_id):
    """Background thread for running scan."""
    import django
    django.setup()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    run = AnalysisRun.objects.get(id=run_id)
    user = User.objects.get(id=user_id) if user_id else None
    
    try:
        analyzer = DocumentAnalyzer(docs_path=docs_path, model=model)
        
        # Import the sync function
        import sys
        packages_path = Path(settings.BASE_DIR) / "packages"
        if str(packages_path) not in sys.path:
            sys.path.insert(0, str(packages_path))
        
        from local_llm_mcp.server import analyze_docs_for_redundancy_sync
        
        result = analyze_docs_for_redundancy_sync(
            docs_path=docs_path,
            model=model,
            max_files=max_files
        )
        
        if "error" in result:
            run.status = "failed"
            run.error_message = result["error"]
        else:
            meta = result.get("_metadata", {})
            run.files_scanned = meta.get("files_scanned", 0)
            run.files_total = meta.get("files_total", 0)
            run.result_json = result
            run.status = "completed"
            run.completed_at = timezone.now()
            
            # Create issues
            analyzer._create_issues_from_result(run, result)
        
        run.save()
        
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.save()


@login_required
@require_POST
def trigger_scan_async(request):
    """Trigger async scan and redirect to status page."""
    max_files = int(request.POST.get("max_files", 100))
    docs_path = str(Path(settings.BASE_DIR) / "docs")
    model = "llama3:8b"
    
    # Create pending run
    run = AnalysisRun.objects.create(
        scan_path=docs_path,
        scan_type="redundancy",
        model_used=model,
        status="running",
        triggered_by=request.user
    )
    
    # Start background thread
    thread = threading.Thread(
        target=_run_scan_async,
        args=(run.id, docs_path, model, max_files, request.user.id)
    )
    thread.daemon = True
    thread.start()
    
    return redirect("dlm_hub:scan-progress", run_id=run.id)


@login_required
def scan_progress(request, run_id):
    """Show scan progress page with HTMX polling."""
    run = get_object_or_404(AnalysisRun, id=run_id)
    return render(request, "dlm_hub/scan_progress.html", {"run": run})


@login_required
def htmx_scan_status(request, run_id):
    """HTMX endpoint for scan status updates."""
    run = get_object_or_404(AnalysisRun, id=run_id)
    return render(request, "dlm_hub/partials/scan_status.html", {"run": run})


# =============================================================================
# Feature 2: File Preview
# =============================================================================

@login_required
def file_preview(request, issue_id):
    """Show file content preview in modal."""
    issue = get_object_or_404(AnalysisIssue, id=issue_id)
    
    # Find the file
    docs_path = Path(settings.BASE_DIR) / "docs"
    file_path = docs_path / issue.file_path
    
    content = None
    error = None
    
    if file_path.exists():
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            # Limit content for display
            if len(content) > 10000:
                content = content[:10000] + "\n\n... [truncated]"
        except Exception as e:
            error = str(e)
    else:
        error = f"File not found: {issue.file_path}"
    
    context = {
        "issue": issue,
        "content": content,
        "error": error,
        "file_path": issue.file_path,
    }
    
    # Return partial for HTMX
    if request.headers.get("HX-Request"):
        return render(request, "dlm_hub/partials/file_preview.html", context)
    
    return render(request, "dlm_hub/file_preview.html", context)


# =============================================================================
# Feature 3: Archive Action
# =============================================================================

@login_required
@require_POST
def archive_file(request, issue_id):
    """Archive a file to docs/_archive/ directory."""
    issue = get_object_or_404(AnalysisIssue, id=issue_id)
    
    docs_path = Path(settings.BASE_DIR) / "docs"
    archive_path = docs_path / "_archive"
    source_file = docs_path / issue.file_path
    
    # Create archive directory if needed
    archive_path.mkdir(exist_ok=True)
    
    success = False
    error_message = None
    
    if source_file.exists():
        try:
            # Generate archive filename with timestamp
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{source_file.stem}_{timestamp}{source_file.suffix}"
            dest_file = archive_path / archive_name
            
            # Move file
            shutil.move(str(source_file), str(dest_file))
            
            # Update issue status
            issue.status = "resolved"
            issue.resolved_at = timezone.now()
            issue.resolved_by = request.user
            issue.save()
            
            # Log action
            ActionLog.objects.create(
                issue=issue,
                action_type="archive",
                executed_by=request.user,
                details={
                    "source": str(source_file),
                    "destination": str(dest_file),
                },
                success=True
            )
            
            success = True
            messages.success(request, f"Archived: {issue.file_path} → _archive/{archive_name}")
            
        except Exception as e:
            error_message = str(e)
            ActionLog.objects.create(
                issue=issue,
                action_type="archive",
                executed_by=request.user,
                details={"error": error_message},
                success=False,
                error_message=error_message
            )
            messages.error(request, f"Archive failed: {error_message}")
    else:
        error_message = "File not found"
        messages.error(request, f"File not found: {issue.file_path}")
    
    # Return to referrer
    next_url = request.POST.get("next", request.META.get("HTTP_REFERER"))
    if next_url:
        return redirect(next_url)
    return redirect("dlm_hub:issue-list")


# =============================================================================
# Feature 4: Claude Review
# =============================================================================

@login_required
def claude_review(request, issue_id):
    """Request Claude to review an issue."""
    issue = get_object_or_404(AnalysisIssue, id=issue_id)
    
    docs_path = Path(settings.BASE_DIR) / "docs"
    file_path = docs_path / issue.file_path
    
    content = None
    review = None
    error = None
    
    if file_path.exists():
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")[:5000]
        except Exception as e:
            error = str(e)
    else:
        error = f"File not found: {issue.file_path}"
    
    # For now, generate a structured review prompt
    # In production, this would call Claude API
    if content and not error:
        review = {
            "status": "pending",
            "prompt": f"""Please review this documentation file for quality and relevance:

**File:** {issue.file_path}
**Issue Type:** {issue.issue_type}
**Reason:** {issue.reason}

**Content Preview:**
```
{content[:2000]}
```

**Questions to answer:**
1. Is this file still relevant and up-to-date?
2. Does it contain duplicate information found elsewhere?
3. Should it be archived, updated, or kept as-is?
4. What specific improvements would you recommend?
""",
            "recommendation": None,
        }
    
    context = {
        "issue": issue,
        "content": content,
        "review": review,
        "error": error,
    }
    
    if request.headers.get("HX-Request"):
        return render(request, "dlm_hub/partials/claude_review.html", context)
    
    return render(request, "dlm_hub/claude_review.html", context)


# =============================================================================
# Feature 5: Diff View
# =============================================================================

def _get_file_info_for_diff(file_path: Path, name: str, is_primary: bool) -> dict:
    """Get detailed file info for diff view."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        stat = file_path.stat()
        lines = content.split('\n')
        
        return {
            "name": name,
            "content": content,
            "lines": lines,
            "line_count": len(lines),
            "is_primary": is_primary,
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": stat.st_mtime,
            "modified_date": timezone.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "word_count": len(content.split()),
            "exists": True,
        }
    except Exception as e:
        return {
            "name": name,
            "content": "",
            "lines": [],
            "line_count": 0,
            "is_primary": is_primary,
            "exists": False,
            "error": str(e),
        }


def _find_file_in_docs(docs_path: Path, filename: str) -> Path:
    """Find a file in docs directory, checking multiple locations."""
    # Direct path
    direct = docs_path / filename
    if direct.exists():
        return direct
    
    # Just the filename in docs root
    name_only = docs_path / Path(filename).name
    if name_only.exists():
        return name_only
    
    # Search in subdirectories
    for subdir in docs_path.iterdir():
        if subdir.is_dir():
            candidate = subdir / Path(filename).name
            if candidate.exists():
                return candidate
    
    return direct  # Return original path even if not found


@login_required
def diff_view(request, issue_id):
    """Show side-by-side diff of related files."""
    issue = get_object_or_404(AnalysisIssue, id=issue_id)
    
    docs_path = Path(settings.BASE_DIR) / "docs"
    
    files = []
    seen_files = set()
    
    # Primary file
    primary_path = _find_file_in_docs(docs_path, issue.file_path)
    if primary_path.exists():
        files.append(_get_file_info_for_diff(primary_path, issue.file_path, True))
        seen_files.add(issue.file_path)
    
    # Related files from issue.related_files
    for related in issue.related_files or []:
        if related not in seen_files:
            related_path = _find_file_in_docs(docs_path, related)
            if related_path.exists():
                files.append(_get_file_info_for_diff(related_path, related, False))
                seen_files.add(related)
    
    # ALWAYS check for other issues in the same group (not just when files == 1)
    if issue.group_name:
        related_issues = AnalysisIssue.objects.filter(
            group_name=issue.group_name,
            analysis_run=issue.analysis_run
        ).exclude(id=issue.id)
        
        for rel_issue in related_issues:
            if rel_issue.file_path not in seen_files:
                rel_path = _find_file_in_docs(docs_path, rel_issue.file_path)
                if rel_path.exists():
                    files.append(_get_file_info_for_diff(rel_path, rel_issue.file_path, False))
                    seen_files.add(rel_issue.file_path)
            
            # Also check related_files of related issues
            for rf in rel_issue.related_files or []:
                if rf not in seen_files:
                    rf_path = _find_file_in_docs(docs_path, rf)
                    if rf_path.exists():
                        files.append(_get_file_info_for_diff(rf_path, rf, False))
                        seen_files.add(rf)
    
    # Build related_issue_ids for actions
    related_issue_ids = []
    if issue.group_name:
        related_issue_ids = list(
            AnalysisIssue.objects.filter(
                group_name=issue.group_name,
                analysis_run=issue.analysis_run
            ).exclude(id=issue.id).values_list('id', flat=True)
        )
    
    context = {
        "issue": issue,
        "files": files,
        "file_count": len(files),
        "related_issue_ids": related_issue_ids,
    }
    
    if request.headers.get("HX-Request"):
        return render(request, "dlm_hub/partials/diff_view.html", context)
    
    return render(request, "dlm_hub/diff_view.html", context)


# =============================================================================
# Feature 6: Keep Primary / Keep Secondary Actions
# =============================================================================

@login_required
@require_POST
def keep_primary(request, issue_id):
    """Keep primary file and archive all related files."""
    issue = get_object_or_404(AnalysisIssue, id=issue_id)
    docs_path = Path(settings.BASE_DIR) / "docs"
    archive_path = docs_path / "_archive"
    archive_path.mkdir(exist_ok=True)
    
    archived_files = []
    errors = []
    
    # Archive related files from issue
    for related in issue.related_files or []:
        related_path = docs_path / related
        if related_path.exists():
            try:
                dest = archive_path / related_path.name
                shutil.move(str(related_path), str(dest))
                archived_files.append(related)
            except Exception as e:
                errors.append(f"{related}: {e}")
    
    # Also archive files from related issues in same group
    if issue.group_name:
        related_issues = AnalysisIssue.objects.filter(
            group_name=issue.group_name,
            analysis_run=issue.analysis_run
        ).exclude(id=issue.id)
        
        for rel_issue in related_issues:
            rel_path = docs_path / rel_issue.file_path
            if rel_path.exists() and rel_issue.file_path not in archived_files:
                try:
                    dest = archive_path / rel_path.name
                    shutil.move(str(rel_path), str(dest))
                    archived_files.append(rel_issue.file_path)
                    # Mark related issue as resolved
                    rel_issue.status = "resolved"
                    rel_issue.resolved_at = timezone.now()
                    rel_issue.resolved_by = request.user
                    rel_issue.save()
                except Exception as e:
                    errors.append(f"{rel_issue.file_path}: {e}")
    
    # Mark primary issue as resolved
    issue.status = "resolved"
    issue.resolved_at = timezone.now()
    issue.resolved_by = request.user
    issue.save()
    
    # Log action
    ActionLog.objects.create(
        issue=issue,
        action_type="archive",
        executed_by=request.user,
        details={"archived_files": archived_files, "kept": issue.file_path},
        success=len(errors) == 0,
        error_message="; ".join(errors) if errors else None,
    )
    
    if errors:
        messages.warning(request, f"Kept primary, archived {len(archived_files)} files. Errors: {len(errors)}")
    else:
        messages.success(request, f"✅ Kept '{issue.file_path}', archived {len(archived_files)} related files.")
    
    return redirect("dlm_hub:run-detail", run_id=issue.analysis_run_id)


@login_required
@require_POST
def keep_secondary(request, issue_id):
    """Keep selected secondary file and archive the primary."""
    issue = get_object_or_404(AnalysisIssue, id=issue_id)
    keep_file = request.POST.get("keep_file")
    
    if not keep_file:
        messages.error(request, "No file selected to keep.")
        return redirect("dlm_hub:diff-view", issue_id=issue.id)
    
    docs_path = Path(settings.BASE_DIR) / "docs"
    archive_path = docs_path / "_archive"
    archive_path.mkdir(exist_ok=True)
    
    archived_files = []
    errors = []
    
    # Archive the primary file
    primary_path = docs_path / issue.file_path
    if primary_path.exists():
        try:
            dest = archive_path / primary_path.name
            shutil.move(str(primary_path), str(dest))
            archived_files.append(issue.file_path)
        except Exception as e:
            errors.append(f"{issue.file_path}: {e}")
    
    # Archive other related files (except the one to keep)
    for related in issue.related_files or []:
        if related != keep_file:
            related_path = docs_path / related
            if related_path.exists():
                try:
                    dest = archive_path / related_path.name
                    shutil.move(str(related_path), str(dest))
                    archived_files.append(related)
                except Exception as e:
                    errors.append(f"{related}: {e}")
    
    # Mark issue as resolved
    issue.status = "resolved"
    issue.resolved_at = timezone.now()
    issue.resolved_by = request.user
    issue.save()
    
    # Log action
    ActionLog.objects.create(
        issue=issue,
        action_type="archive",
        executed_by=request.user,
        details={"archived_files": archived_files, "kept": keep_file},
        success=len(errors) == 0,
        error_message="; ".join(errors) if errors else None,
    )
    
    if errors:
        messages.warning(request, f"Kept '{keep_file}', archived {len(archived_files)} files. Errors: {len(errors)}")
    else:
        messages.success(request, f"✅ Kept '{keep_file}', archived {len(archived_files)} files (including primary).")
    
    return redirect("dlm_hub:run-detail", run_id=issue.analysis_run_id)
