"""DLM Hub Analyzer Service - Wrapper for Local LLM Analyzer."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.utils import timezone

from ..models import AnalysisRun, AnalysisIssue
from .similarity import validate_redundancy_group, get_similarity_label

logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """Service for running documentation analysis using local LLM."""
    
    def __init__(self, docs_path: Optional[str] = None, model: str = "llama3:8b"):
        self.docs_path = docs_path or str(Path(settings.BASE_DIR) / "docs")
        self.model = model
        
        # Add local_llm_mcp to path
        packages_path = Path(settings.BASE_DIR) / "packages"
        if str(packages_path) not in sys.path:
            sys.path.insert(0, str(packages_path))
    
    def run_redundancy_scan(
        self,
        max_files: int = 100,
        user=None
    ) -> AnalysisRun:
        """Run redundancy analysis and store results in DB."""
        
        # Create run record
        run = AnalysisRun.objects.create(
            scan_path=self.docs_path,
            scan_type="redundancy",
            model_used=self.model,
            status="running",
            triggered_by=user
        )
        
        try:
            from local_llm_mcp.server import analyze_docs_for_redundancy_sync
            
            result = analyze_docs_for_redundancy_sync(
                docs_path=self.docs_path,
                model=self.model,
                max_files=max_files
            )
            
            # Check for errors in result
            if "error" in result:
                run.status = "failed"
                run.error_message = result["error"]
                run.save()
                return run
            
            # Update run with results
            meta = result.get("_metadata", {})
            run.files_scanned = meta.get("files_scanned", 0)
            run.files_total = meta.get("files_total", 0)
            run.result_json = result
            run.status = "completed"
            run.completed_at = timezone.now()
            run.save()
            
            # Create issues from results
            self._create_issues_from_result(run, result)
            
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.save()
        
        return run
    
    def _create_issues_from_result(self, run: AnalysisRun, result: dict):
        """Create AnalysisIssue records from analysis result."""
        
        # Redundancy candidates - validate with similarity scoring
        docs_root = Path(self.docs_path)
        
        for group in result.get("redundancy_candidates", []):
            files = group.get("files", [])
            
            # Clean up file names (remove "name: " prefix if present)
            cleaned_files = []
            for f in files:
                if isinstance(f, str):
                    if f.startswith("name: "):
                        f = f[6:]
                    cleaned_files.append(f)
            
            # Skip single-file groups - not a valid redundancy case
            if len(cleaned_files) < 2:
                logger.debug(f"Skipping group '{group.get('group_name')}': only {len(cleaned_files)} file(s)")
                continue
            
            # Validate similarity with semantic embeddings
            is_valid, similarity_score, validation_msg = validate_redundancy_group(
                docs_root, cleaned_files, threshold=0.4
            )
            
            if not is_valid:
                logger.info(f"Rejected group '{group.get('group_name')}': {validation_msg}")
                continue
            
            primary_file = cleaned_files[0]
            similarity_label = get_similarity_label(similarity_score)
            
            # Enhanced reason with similarity score
            llm_reason = group.get("similarity_reason", "")
            enhanced_reason = f"{llm_reason} [Similarity: {similarity_score:.0%} ({similarity_label})]"
            
            AnalysisIssue.objects.create(
                analysis_run=run,
                issue_type="redundancy",
                severity=self._map_priority(group.get("priority", "medium")),
                file_path=primary_file,
                group_name=group.get("group_name"),
                related_files=cleaned_files[1:],
                reason=enhanced_reason,
                suggestion=group.get("suggestion", "review")
            )
            logger.info(f"Created redundancy issue: {group.get('group_name')} (similarity: {similarity_score:.0%})")
        
        # Outdated candidates
        for item in result.get("outdated_candidates", []):
            file_path = item.get("file", "")
            
            # Clean up file name
            if file_path.startswith("name: "):
                file_path = file_path[6:]
            
            AnalysisIssue.objects.create(
                analysis_run=run,
                issue_type="outdated",
                severity=self._map_priority(item.get("priority", "low")),
                file_path=file_path,
                reason=item.get("reason", ""),
                suggestion=item.get("suggestion", "archive")
            )
        
        # Structure issues
        for issue in result.get("structure_issues", []):
            affected = issue.get("affected_files", [])
            primary_file = affected[0] if affected else "unknown"
            
            AnalysisIssue.objects.create(
                analysis_run=run,
                issue_type="structure",
                severity="low",
                file_path=primary_file,
                related_files=affected[1:] if len(affected) > 1 else [],
                reason=issue.get("issue", ""),
                suggestion="review"
            )
    
    def _map_priority(self, priority: str) -> str:
        """Map priority string to severity."""
        return {
            "high": "high",
            "medium": "medium",
            "low": "low",
        }.get(priority.lower(), "medium")
    
    @staticmethod
    def load_from_json(json_path: str, user=None) -> Optional[AnalysisRun]:
        """Load analysis results from existing JSON file."""
        path = Path(json_path)
        
        if not path.exists():
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                result = json.load(f)
            
            meta = result.get("_metadata", {})
            
            run = AnalysisRun.objects.create(
                scan_path=meta.get("scan_path", str(path.parent)),
                scan_type="redundancy",
                model_used=meta.get("model_used", "unknown"),
                status="completed",
                files_scanned=meta.get("files_scanned", 0),
                files_total=meta.get("files_total", 0),
                result_json=result,
                completed_at=timezone.now(),
                triggered_by=user
            )
            
            analyzer = DocumentAnalyzer()
            analyzer._create_issues_from_result(run, result)
            
            return run
            
        except Exception:
            return None
