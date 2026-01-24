"""
Core Review Framework Components

Based on Chain-of-Responsibility pattern for extensible code review.
"""

import logging
import structlog
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


logger = structlog.get_logger(__name__)


class ReviewSeverity(Enum):
    """Severity levels for review findings"""
    CRITICAL = "critical"  # Security issues, blockers
    ERROR = "error"        # Bugs, anti-patterns
    WARNING = "warning"    # Improvements needed
    INFO = "info"          # Best practices
    STYLE = "style"        # Formatting issues


class ReviewCategory(Enum):
    """Categories for review findings"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    BEST_PRACTICES = "best_practices"
    DJANGO_SPECIFIC = "django_specific"


@dataclass
class ReviewFinding:
    """A single review finding"""
    id: str
    category: ReviewCategory
    severity: ReviewSeverity
    title: str
    description: str
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'category': self.category.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'file_path': str(self.file_path) if self.file_path else None,
            'line_number': self.line_number,
            'code_snippet': self.code_snippet,
            'suggestion': self.suggestion,
            'auto_fixable': self.auto_fixable,
            'metadata': self.metadata,
        }


@dataclass
class ReviewResult:
    """Result of a review process"""
    findings: List[ReviewFinding] = field(default_factory=list)
    duration_seconds: float = 0.0
    files_reviewed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_finding(self, finding: ReviewFinding) -> None:
        """Add a finding to results"""
        self.findings.append(finding)
    
    def get_by_severity(self, severity: ReviewSeverity) -> List[ReviewFinding]:
        """Get findings by severity"""
        return [f for f in self.findings if f.severity == severity]
    
    def get_by_category(self, category: ReviewCategory) -> List[ReviewFinding]:
        """Get findings by category"""
        return [f for f in self.findings if f.category == category]
    
    def has_critical(self) -> bool:
        """Check if has critical findings"""
        return any(f.severity == ReviewSeverity.CRITICAL for f in self.findings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'findings': [f.to_dict() for f in self.findings],
            'duration_seconds': self.duration_seconds,
            'files_reviewed': self.files_reviewed,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'stats': {
                'total': len(self.findings),
                'critical': len(self.get_by_severity(ReviewSeverity.CRITICAL)),
                'error': len(self.get_by_severity(ReviewSeverity.ERROR)),
                'warning': len(self.get_by_severity(ReviewSeverity.WARNING)),
                'info': len(self.get_by_severity(ReviewSeverity.INFO)),
                'style': len(self.get_by_severity(ReviewSeverity.STYLE)),
            },
            'metadata': self.metadata,
        }


class BaseReviewHandler(ABC):
    """Base class for review handlers"""
    
    def __init__(self, name: str):
        self.name = name
        self.log = structlog.get_logger(__name__).bind(handler=name)
        self._next_handler: Optional['BaseReviewHandler'] = None
    
    def set_next(self, handler: 'BaseReviewHandler') -> 'BaseReviewHandler':
        """Set next handler in chain"""
        self._next_handler = handler
        return handler
    
    def handle(self, target: Path, context: Dict[str, Any], result: ReviewResult) -> ReviewResult:
        """Handle review request"""
        self.log.info("processing", target=str(target))
        
        # Process this handler
        result = self._review(target, context, result)
        
        # Pass to next handler
        if self._next_handler:
            result = self._next_handler.handle(target, context, result)
        
        return result
    
    @abstractmethod
    def _review(self, target: Path, context: Dict[str, Any], result: ReviewResult) -> ReviewResult:
        """Implement review logic"""
        pass
    
    def add_finding(
        self,
        result: ReviewResult,
        category: ReviewCategory,
        severity: ReviewSeverity,
        title: str,
        description: str,
        file_path: Optional[Path] = None,
        line_number: Optional[int] = None,
        code_snippet: Optional[str] = None,
        suggestion: Optional[str] = None,
        auto_fixable: bool = False,
        **metadata
    ) -> None:
        """Helper to add finding"""
        finding_id = f"{self.name}_{len(result.findings)}"
        finding = ReviewFinding(
            id=finding_id,
            category=category,
            severity=severity,
            title=title,
            description=description,
            file_path=file_path,
            line_number=line_number,
            code_snippet=code_snippet,
            suggestion=suggestion,
            auto_fixable=auto_fixable,
            metadata=metadata,
        )
        result.add_finding(finding)


class BaseFixHandler(ABC):
    """Base class for auto-fix handlers"""
    
    def __init__(self, name: str):
        self.name = name
        self.log = structlog.get_logger(__name__).bind(fixer=name)
    
    @abstractmethod
    def can_fix(self, finding: ReviewFinding) -> bool:
        """Check if this fixer can handle the finding"""
        pass
    
    @abstractmethod
    def apply_fix(self, finding: ReviewFinding, context: Dict[str, Any]) -> bool:
        """Apply the fix, return True if successful"""
        pass


class ReviewOrchestrator:
    """Orchestrates the review process"""
    
    def __init__(self):
        self.log = structlog.get_logger(__name__).bind(component="orchestrator")
        self.review_handlers: List[BaseReviewHandler] = []
        self.fix_handlers: List[BaseFixHandler] = []
    
    def register_review_handler(self, handler: BaseReviewHandler) -> None:
        """Register a review handler"""
        self.review_handlers.append(handler)
        self.log.info("handler_registered", handler=handler.name)
    
    def register_fix_handler(self, fixer: BaseFixHandler) -> None:
        """Register a fix handler"""
        self.fix_handlers.append(fixer)
        self.log.info("fixer_registered", fixer=fixer.name)
    
    def review(
        self,
        target_path: Path,
        context: Optional[Dict[str, Any]] = None,
        auto_fix: bool = False
    ) -> ReviewResult:
        """Execute review process"""
        context = context or {}
        result = ReviewResult(start_time=datetime.now())
        
        self.log.info("review_started", target=str(target_path), auto_fix=auto_fix)
        
        # Build handler chain
        if self.review_handlers:
            for i, handler in enumerate(self.review_handlers[:-1]):
                handler.set_next(self.review_handlers[i + 1])
            
            # Execute chain
            if target_path.is_file():
                result.files_reviewed = 1
                result = self.review_handlers[0].handle(target_path, context, result)
            elif target_path.is_dir():
                for py_file in target_path.rglob('*.py'):
                    result.files_reviewed += 1
                    result = self.review_handlers[0].handle(py_file, context, result)
        
        result.end_time = datetime.now()
        result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        
        # Auto-fix if requested
        if auto_fix and self.fix_handlers:
            self._apply_fixes(result, context)
        
        self.log.info(
            "review_completed",
            findings=len(result.findings),
            duration=result.duration_seconds,
            files=result.files_reviewed
        )
        
        return result
    
    def _apply_fixes(self, result: ReviewResult, context: Dict[str, Any]) -> None:
        """Apply automatic fixes"""
        fixable = [f for f in result.findings if f.auto_fixable]
        self.log.info("applying_fixes", count=len(fixable))
        
        for finding in fixable:
            for fixer in self.fix_handlers:
                if fixer.can_fix(finding):
                    try:
                        success = fixer.apply_fix(finding, context)
                        if success:
                            finding.metadata['fixed'] = True
                            self.log.info("fix_applied", finding=finding.id, fixer=fixer.name)
                        break
                    except Exception as e:
                        self.log.error("fix_failed", finding=finding.id, error=str(e))
