"""
Fact Check Handler
==================

Handler for verifying claims and statements.
"""

import logging
import time
from typing import Dict, Any, Optional, List

from ..services import get_brave_search
from ..models import ResearchProject, ResearchFinding, ResearchResult

logger = logging.getLogger(__name__)


class FactCheckHandler:
    """
    Handler for fact-checking claims and statements.
    
    Verifies claims by searching for supporting/contradicting evidence.
    
    Usage:
        handler = FactCheckHandler()
        result = handler.execute(
            project_id=1,
            claims=["The Earth is round", "Water boils at 100°C"]
        )
    """
    
    name = "FactCheckHandler"
    description = "Verifies claims and statements against web sources"
    phase = "analyse"
    
    def __init__(self):
        """Initialize handler."""
        self.search_service = get_brave_search()
    
    def execute(
        self,
        project_id: int,
        claims: Optional[List[str]] = None,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Verify claims for a research project.
        
        Args:
            project_id: ID of the research project
            claims: List of claims to verify (uses project findings if not provided)
            options: Additional options
                - min_confidence: Minimum confidence threshold (default: 0.5)
                - sources_per_claim: Number of sources to check (default: 3)
                
        Returns:
            Dict with verification results
        """
        start_time = time.time()
        options = options or {}
        
        try:
            # Get project
            project = ResearchProject.objects.get(id=project_id)
            
            # Get claims to verify
            if claims is None:
                # Use existing findings from project
                claims = list(
                    project.findings.filter(is_verified=False)
                    .values_list('content', flat=True)[:10]
                )
            
            if not claims:
                return {
                    'success': True,
                    'handler': self.name,
                    'message': 'No claims to verify',
                    'verified': []
                }
            
            # Verify each claim
            verified_claims = []
            for claim in claims:
                result = self._verify_claim(
                    claim,
                    sources_count=options.get('sources_per_claim', 3)
                )
                verified_claims.append(result)
                
                # Update finding if exists
                finding = project.findings.filter(content=claim).first()
                if finding and result.get('confidence', 0) >= options.get('min_confidence', 0.5):
                    finding.is_verified = result.get('verified', False) or False
                    finding.verification_notes = result.get('notes', '')
                    finding.save()
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Store result
            ResearchResult.objects.create(
                project=project,
                handler_name=self.name,
                phase=self.phase,
                success=True,
                result_data={
                    'claims_checked': len(verified_claims),
                    'results': verified_claims
                },
                execution_time_ms=execution_time
            )
            
            # Summary stats
            verified_true = sum(1 for v in verified_claims if v.get('verified') is True)
            verified_false = sum(1 for v in verified_claims if v.get('verified') is False)
            unknown = sum(1 for v in verified_claims if v.get('verified') is None)
            
            return {
                'success': True,
                'handler': self.name,
                'claims_checked': len(verified_claims),
                'verified_true': verified_true,
                'verified_false': verified_false,
                'unknown': unknown,
                'results': verified_claims,
                'execution_time_ms': execution_time
            }
            
        except ResearchProject.DoesNotExist:
            return {
                'success': False,
                'error': f'Project {project_id} not found',
                'handler': self.name
            }
        except Exception as e:
            logger.error(f"FactCheckHandler error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'handler': self.name
            }
    
    def _verify_claim(self, claim: str, sources_count: int = 3) -> Dict:
        """
        Verify a single claim.
        
        Args:
            claim: The claim to verify
            sources_count: Number of sources to search
            
        Returns:
            Dict with verification result
        """
        # Search for evidence
        search_query = f'fact check: {claim}'
        search_result = self.search_service.search(search_query, count=sources_count)
        
        sources = search_result.get('results', [])
        
        verification = {
            'claim': claim,
            'verified': None,
            'confidence': 0.0,
            'sources': [],
            'notes': ''
        }
        
        if not sources:
            verification['notes'] = 'No sources found'
            return verification
        
        # Analyze sources
        claim_terms = set(claim.lower().split())
        supporting = 0
        contradicting = 0
        
        for source in sources:
            title = source.get('title', '').lower()
            desc = source.get('description', '').lower()
            combined = f"{title} {desc}"
            
            # Check for supporting/contradicting indicators
            if any(word in combined for word in ['true', 'correct', 'verified', 'confirmed', 'yes']):
                supporting += 1
            elif any(word in combined for word in ['false', 'incorrect', 'debunked', 'myth', 'no']):
                contradicting += 1
            
            # Check term overlap
            term_matches = sum(1 for term in claim_terms if term in combined)
            if term_matches > len(claim_terms) * 0.3:
                supporting += 0.5
            
            verification['sources'].append({
                'title': source.get('title', ''),
                'url': source.get('url', '')
            })
        
        # Determine verification status
        total_evidence = supporting + contradicting
        if total_evidence > 0:
            support_ratio = supporting / total_evidence
            
            if support_ratio > 0.7:
                verification['verified'] = True
                verification['confidence'] = min(0.9, 0.5 + support_ratio * 0.4)
            elif support_ratio < 0.3:
                verification['verified'] = False
                verification['confidence'] = min(0.9, 0.5 + (1 - support_ratio) * 0.4)
            else:
                verification['verified'] = None
                verification['confidence'] = 0.4
        
        verification['notes'] = (
            f"Supporting: {supporting:.1f}, Contradicting: {contradicting:.1f}, "
            f"Sources checked: {len(sources)}"
        )
        
        return verification
