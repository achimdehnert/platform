"""
AI Summary Service
==================

Generate AI-powered summaries of research results using LLM.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AISummaryService:
    """
    Generate intelligent summaries using LLM.
    
    Usage:
        service = AISummaryService()
        summary = service.summarize_findings(findings)
        key_points = service.extract_key_points(text)
    """
    
    def __init__(self):
        self._llm_client = None
    
    @property
    def llm_client(self):
        """Lazy-load LLM client."""
        if self._llm_client is None:
            try:
                from apps.bfagent.services.llm_client import generate_text
                self._llm_client = generate_text
            except ImportError:
                logger.warning("LLM client not available, using mock")
                self._llm_client = self._mock_generate
        return self._llm_client
    
    def _mock_generate(self, prompt: str, **kwargs) -> str:
        """Mock LLM generation for testing."""
        return f"[AI Summary] Based on the provided content, the key findings indicate significant developments in this research area. Further investigation is recommended to validate these results."
    
    def summarize_findings(
        self,
        findings: List[Dict],
        max_length: int = 500,
        style: str = 'academic'
    ) -> Dict:
        """
        Generate a summary of research findings.
        
        Args:
            findings: List of finding dicts with 'title' and 'content'
            max_length: Maximum summary length
            style: Summary style ('academic', 'executive', 'bullet_points')
            
        Returns:
            Dict with summary and metadata
        """
        if not findings:
            return {
                'summary': 'No findings to summarize.',
                'key_points': [],
                'word_count': 0
            }
        
        # Build context from findings
        findings_text = "\n\n".join([
            f"**{f.get('title', 'Finding')}**\n{f.get('content', '')}"
            for f in findings
        ])
        
        # Build prompt based on style
        style_instructions = {
            'academic': "Write in formal academic style with proper citations references.",
            'executive': "Write a concise executive summary focusing on actionable insights.",
            'bullet_points': "Format as bullet points highlighting key takeaways.",
        }
        
        prompt = f"""Summarize the following research findings in approximately {max_length} words.
{style_instructions.get(style, '')}

Research Findings:
{findings_text}

Summary:"""
        
        try:
            summary = self.llm_client(prompt, max_tokens=max_length * 2)
            key_points = self._extract_key_points_from_summary(summary)
            
            return {
                'summary': summary.strip(),
                'key_points': key_points,
                'word_count': len(summary.split()),
                'style': style,
                'ai_generated': True
            }
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            return self._fallback_summary(findings)
    
    def summarize_sources(
        self,
        sources: List[Dict],
        query: str = ''
    ) -> Dict:
        """
        Generate a summary of search results/sources.
        
        Args:
            sources: List of source dicts with 'title', 'snippet', 'url'
            query: Original search query for context
            
        Returns:
            Dict with summary and source analysis
        """
        if not sources:
            return {
                'summary': 'No sources to analyze.',
                'themes': [],
                'source_count': 0
            }
        
        # Build context from sources
        sources_text = "\n".join([
            f"- {s.get('title', 'Untitled')}: {s.get('snippet', '')[:200]}"
            for s in sources[:10]  # Limit to 10 sources
        ])
        
        prompt = f"""Analyze and summarize the following search results for the query: "{query}"

Sources:
{sources_text}

Provide:
1. A brief summary of what these sources collectively tell us
2. Main themes across sources
3. Any contradictions or gaps in information

Analysis:"""
        
        try:
            analysis = self.llm_client(prompt, max_tokens=600)
            themes = self._extract_themes(analysis)
            
            return {
                'summary': analysis.strip(),
                'themes': themes,
                'source_count': len(sources),
                'ai_generated': True
            }
        except Exception as e:
            logger.error(f"Source summary failed: {e}")
            return {
                'summary': f"Found {len(sources)} sources related to '{query}'.",
                'themes': [],
                'source_count': len(sources),
                'ai_generated': False
            }
    
    def extract_key_points(
        self,
        text: str,
        num_points: int = 5
    ) -> List[str]:
        """
        Extract key points from text.
        
        Args:
            text: Input text to analyze
            num_points: Number of key points to extract
            
        Returns:
            List of key point strings
        """
        if not text or len(text) < 50:
            return []
        
        prompt = f"""Extract exactly {num_points} key points from the following text.
Return each point on a new line, starting with a dash (-).

Text:
{text[:2000]}

Key Points:"""
        
        try:
            result = self.llm_client(prompt, max_tokens=300)
            points = [
                line.strip().lstrip('-').strip()
                for line in result.split('\n')
                if line.strip().startswith('-') or (line.strip() and len(line) > 10)
            ]
            return points[:num_points]
        except Exception as e:
            logger.error(f"Key point extraction failed: {e}")
            return self._fallback_key_points(text, num_points)
    
    def generate_research_questions(
        self,
        topic: str,
        num_questions: int = 5
    ) -> List[str]:
        """
        Generate research questions for a topic.
        
        Args:
            topic: Research topic
            num_questions: Number of questions to generate
            
        Returns:
            List of research question strings
        """
        prompt = f"""Generate {num_questions} insightful research questions about: "{topic}"

The questions should:
- Be specific and answerable through research
- Cover different aspects of the topic
- Progress from basic to more complex

Questions:"""
        
        try:
            result = self.llm_client(prompt, max_tokens=400)
            questions = [
                line.strip().lstrip('0123456789.)-').strip()
                for line in result.split('\n')
                if '?' in line
            ]
            return questions[:num_questions]
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            return [
                f"What are the key aspects of {topic}?",
                f"What recent developments have occurred in {topic}?",
                f"What challenges exist in {topic}?",
            ]
    
    def _extract_key_points_from_summary(self, summary: str) -> List[str]:
        """Extract key points from a summary text."""
        sentences = summary.replace('\n', ' ').split('.')
        key_points = [
            s.strip() + '.'
            for s in sentences
            if len(s.strip()) > 30
        ][:5]
        return key_points
    
    def _extract_themes(self, analysis: str) -> List[str]:
        """Extract themes from analysis text."""
        # Simple extraction - look for common theme indicators
        themes = []
        for line in analysis.split('\n'):
            line = line.strip()
            if any(indicator in line.lower() for indicator in ['theme:', 'topic:', '•', '-']):
                theme = line.lstrip('-•').strip()
                if len(theme) > 5 and len(theme) < 100:
                    themes.append(theme)
        return themes[:5]
    
    def _fallback_summary(self, findings: List[Dict]) -> Dict:
        """Generate fallback summary without AI."""
        titles = [f.get('title', '') for f in findings if f.get('title')]
        
        summary = f"This research covers {len(findings)} findings"
        if titles:
            summary += f" including: {', '.join(titles[:3])}"
            if len(titles) > 3:
                summary += f" and {len(titles) - 3} more"
        summary += "."
        
        return {
            'summary': summary,
            'key_points': titles[:5],
            'word_count': len(summary.split()),
            'ai_generated': False
        }
    
    def _fallback_key_points(self, text: str, num_points: int) -> List[str]:
        """Extract key points using simple heuristics."""
        sentences = text.replace('\n', ' ').split('.')
        # Score sentences by length and position
        scored = []
        for i, s in enumerate(sentences):
            s = s.strip()
            if len(s) > 30:
                score = len(s) - (i * 5)  # Prefer longer, earlier sentences
                scored.append((score, s + '.'))
        
        scored.sort(reverse=True)
        return [s for _, s in scored[:num_points]]


# Singleton instance
_ai_summary_service = None

def get_ai_summary_service() -> AISummaryService:
    """Get singleton instance of AISummaryService."""
    global _ai_summary_service
    if _ai_summary_service is None:
        _ai_summary_service = AISummaryService()
    return _ai_summary_service
