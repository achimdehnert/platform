"""
Research Agent Handler for PPTX Studio
Performs research based on prompts and generates slide content
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Single research result"""
    title: str
    content: str
    source: str
    relevance_score: float
    key_points: List[str]


class ResearchAgentHandler:
    """
    Research Agent for content discovery and slide generation
    
    Capabilities:
    - Web search via prompt
    - Content analysis and summarization
    - Key point extraction
    - Slide-ready content generation
    """
    
    def __init__(self):
        self.max_results = 10
        self.min_relevance_score = 0.5
    
    def research(self, prompt: str, options: Optional[Dict] = None) -> Dict:
        """
        Main research method
        
        Args:
            prompt: Research query/prompt
            options: Additional options (max_results, sources, etc.)
            
        Returns:
            Dict with research results and metadata
        """
        try:
            options = options or {}
            max_results = options.get('max_results', self.max_results)
            sources = options.get('sources', ['web', 'knowledge'])
            
            # Step 1: Perform search
            logger.info(f"Researching: {prompt}")
            search_results = self._perform_search(prompt, sources, max_results)
            
            # Step 2: Analyze and score results
            analyzed_results = self._analyze_results(search_results, prompt)
            
            # Step 3: Extract key points
            key_findings = self._extract_key_findings(analyzed_results)
            
            # Step 4: Generate slide concepts
            slide_concepts = self._generate_slide_concepts(key_findings, prompt)
            
            return {
                'success': True,
                'prompt': prompt,
                'total_results': len(analyzed_results),
                'key_findings': key_findings,
                'slide_concepts': slide_concepts,
                'raw_results': analyzed_results
            }
            
        except Exception as e:
            logger.error(f"Research error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'prompt': prompt
            }
    
    def _perform_search(
        self,
        prompt: str,
        sources: List[str],
        max_results: int
    ) -> List[Dict]:
        """
        Perform search across specified sources
        
        Args:
            prompt: Search query
            sources: List of sources to search
            max_results: Maximum results to return
            
        Returns:
            List of search results
        """
        results = []
        
        # Web search (placeholder - integrate with actual search API)
        if 'web' in sources:
            web_results = self._search_web(prompt, max_results)
            results.extend(web_results)
        
        # Knowledge base search
        if 'knowledge' in sources:
            kb_results = self._search_knowledge_base(prompt, max_results)
            results.extend(kb_results)
        
        return results[:max_results]
    
    def _search_web(self, prompt: str, max_results: int) -> List[Dict]:
        """
        Search web for content
        
        TODO: Integrate with actual search API (Google, Bing, etc.)
        For now, returns mock data
        """
        # Mock web search results with rich content
        return [
            {
                'title': f"Latest trend in {prompt}" if i == 0 else f"Result {i+1} for: {prompt}",
                'content': f"This is mock content about {prompt}. Key points include various aspects of the topic. "
                          f"The research covers important developments and future implications. "
                          f"Multiple perspectives are considered in this comprehensive analysis.",
                'summary': f"Comprehensive analysis of {prompt} covering key developments and trends.",
                'key_points': [
                    f"Key finding {i+1}-1: Important aspect of {prompt}",
                    f"Key finding {i+1}-2: Critical development in the field",
                    f"Key finding {i+1}-3: Future implications and recommendations"
                ],
                'source': f"https://example.com/result{i+1}",
                'type': 'web'
            }
            for i in range(min(3, max_results))
        ]
    
    def _search_knowledge_base(self, prompt: str, max_results: int) -> List[Dict]:
        """
        Search internal knowledge base
        
        TODO: Integrate with vector DB or document store
        """
        # Placeholder
        return []
    
    def _analyze_results(
        self,
        results: List[Dict],
        prompt: str
    ) -> List[ResearchResult]:
        """
        Analyze and score search results
        
        Args:
            results: Raw search results
            prompt: Original prompt for relevance scoring
            
        Returns:
            List of analyzed ResearchResult objects
        """
        analyzed = []
        
        for result in results:
            # Calculate relevance score
            relevance = self._calculate_relevance(result, prompt)
            
            # Extract key points
            key_points = self._extract_key_points(result['content'])
            
            if relevance >= self.min_relevance_score:
                analyzed.append(ResearchResult(
                    title=result['title'],
                    content=result['content'],
                    source=result.get('source', 'unknown'),
                    relevance_score=relevance,
                    key_points=key_points
                ))
        
        # Sort by relevance
        analyzed.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return analyzed
    
    def _calculate_relevance(self, result: Dict, prompt: str) -> float:
        """
        Calculate relevance score for a result
        
        Simple keyword-based scoring for now
        TODO: Use embeddings/semantic similarity
        """
        prompt_lower = prompt.lower()
        title_lower = result['title'].lower()
        content_lower = result['content'].lower()
        
        # Count keyword matches
        matches = 0
        keywords = prompt_lower.split()
        
        for keyword in keywords:
            if keyword in title_lower:
                matches += 2  # Title matches are more important
            if keyword in content_lower:
                matches += 1
        
        # Normalize to 0-1 range
        max_possible = len(keywords) * 3
        return min(1.0, matches / max_possible if max_possible > 0 else 0.0)
    
    def _extract_key_points(self, content: str) -> List[str]:
        """
        Extract key points from content
        
        Simple sentence extraction for now
        TODO: Use NLP/LLM for better extraction
        """
        # Split into sentences
        sentences = content.split('.')
        
        # Take first 3 non-empty sentences as key points
        key_points = []
        for sentence in sentences[:5]:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Ignore very short fragments
                key_points.append(sentence)
                if len(key_points) >= 3:
                    break
        
        return key_points
    
    def _extract_key_findings(
        self,
        results: List[ResearchResult]
    ) -> List[Dict]:
        """
        Extract overall key findings from all results
        
        Args:
            results: Analyzed research results
            
        Returns:
            List of key findings with aggregated information
        """
        findings = []
        
        # Group by topic/theme
        for i, result in enumerate(results[:5]):  # Top 5 results
            finding = {
                'id': i + 1,
                'title': result.title,
                'summary': result.content[:200] + '...',
                'key_points': result.key_points,
                'source': result.source,
                'relevance': result.relevance_score,
                'selected': i < 3  # Auto-select top 3
            }
            findings.append(finding)
        
        return findings
    
    def _generate_slide_concepts(
        self,
        findings: List[Dict],
        prompt: str
    ) -> List[Dict]:
        """
        Generate slide concepts from findings
        
        Args:
            findings: Key findings from research
            prompt: Original research prompt
            
        Returns:
            List of slide concept dicts ready for enhancement
        """
        concepts = []
        
        # Overview slide
        concepts.append({
            'title': f'Research Overview: {prompt}',
            'content': self._create_overview_content(findings),
            'type': 'overview',
            'slide_type': 'title_content'
        })
        
        # Individual finding slides
        for finding in findings[:5]:  # Max 5 content slides
            if finding.get('selected', False):
                concepts.append({
                    'title': finding['title'],
                    'content': self._format_finding_content(finding),
                    'type': 'finding',
                    'slide_type': 'bullet_list',
                    'source': finding.get('source', '')
                })
        
        # Summary slide
        if len(findings) > 0:
            concepts.append({
                'title': 'Key Takeaways',
                'content': self._create_summary_content(findings),
                'type': 'summary',
                'slide_type': 'bullet_list'
            })
        
        return concepts
    
    def _create_overview_content(self, findings: List[Dict]) -> str:
        """Create overview slide content"""
        if not findings:
            return "No significant findings from research."
        
        content_parts = [
            f"Research Analysis - {len(findings)} sources reviewed\n",
            "\nKey Areas Covered:"
        ]
        
        for i, finding in enumerate(findings[:5], 1):
            content_parts.append(f"\n{i}. {finding['title']}")
        
        return '\n'.join(content_parts)
    
    def _format_finding_content(self, finding: Dict) -> str:
        """Format finding content for slide"""
        parts = []
        
        # Add summary (try multiple fields)
        summary = finding.get('summary') or finding.get('content', '')
        if summary:
            parts.append(summary)
        
        # Add key points as bullets
        if finding.get('key_points'):
            parts.append("\n\nKey Points:")
            for point in finding['key_points']:
                parts.append(f"• {point}")
        
        # If no structured content, create bullets from content
        elif summary and not finding.get('key_points'):
            # Split content into sentences/lines for bullets
            lines = summary.split('. ')
            if len(lines) > 1:
                parts.append("\n\nKey Points:")
                for line in lines:
                    if line.strip():
                        parts.append(f"• {line.strip()}")
        
        return '\n'.join(parts)
    
    def _create_summary_content(self, findings: List[Dict]) -> str:
        """Create summary slide content"""
        selected = [f for f in findings if f.get('selected', False)]
        
        if not selected:
            return "No findings selected."
        
        parts = ["Key Takeaways:\n"]
        
        for finding in selected:
            if finding.get('key_points'):
                # Take first key point from each finding
                parts.append(f"• {finding['key_points'][0]}")
        
        return '\n'.join(parts)
    
    def filter_concepts(
        self,
        concepts: List[Dict],
        selected_ids: List[int]
    ) -> List[Dict]:
        """
        Filter slide concepts based on user selection
        
        Args:
            concepts: All generated concepts
            selected_ids: IDs of selected concepts
            
        Returns:
            Filtered list of concepts
        """
        # Overview and summary are always included
        filtered = [
            c for c in concepts
            if c['type'] in ['overview', 'summary']
        ]
        
        # Add selected findings
        findings = [c for c in concepts if c['type'] == 'finding']
        for i, finding in enumerate(findings):
            if i in selected_ids or i + 1 in selected_ids:
                filtered.append(finding)
        
        return filtered
