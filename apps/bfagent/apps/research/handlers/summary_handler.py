"""
Summary Handler
===============

Handler for generating research summaries.
"""

import logging
import time
from typing import Dict, Any, Optional, List

from ..models import ResearchProject, ResearchFinding, ResearchResult

logger = logging.getLogger(__name__)


class SummaryHandler:
    """
    Handler for generating research summaries.
    
    Creates structured summaries from collected sources and findings.
    
    Usage:
        handler = SummaryHandler()
        result = handler.execute(project_id=1)
    """
    
    name = "SummaryHandler"
    description = "Generates comprehensive research summaries"
    phase = "zusammenfassung"
    
    def __init__(self):
        """Initialize handler."""
        self._llm_client = None  # TODO: Add LLM integration
    
    def execute(
        self,
        project_id: int,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate summary for a research project.
        
        Args:
            project_id: ID of the research project
            options: Additional options
                - format: Output format ('text', 'markdown', 'json')
                - max_length: Maximum summary length
                - include_sources: Include source citations
                - use_ai: Use AI for summary generation
                
        Returns:
            Dict with generated summary
        """
        start_time = time.time()
        options = options or {}
        
        try:
            # Get project with related data
            project = ResearchProject.objects.prefetch_related(
                'sources', 'findings'
            ).get(id=project_id)
            
            # Gather data
            sources = list(project.sources.all()[:20])
            findings = list(project.findings.order_by('-importance')[:20])
            
            # Generate summary
            output_format = options.get('format', 'markdown')
            use_ai = options.get('use_ai', False)
            
            if use_ai and self._llm_client:
                summary = self._generate_ai_summary(project, sources, findings, options)
            else:
                summary = self._generate_rule_based_summary(project, sources, findings, options)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Store result
            ResearchResult.objects.create(
                project=project,
                handler_name=self.name,
                phase=self.phase,
                success=True,
                result_data={
                    'summary': summary,
                    'format': output_format,
                    'sources_used': len(sources),
                    'findings_used': len(findings)
                },
                execution_time_ms=execution_time
            )
            
            # Update project metadata
            project.metadata['last_summary'] = summary[:500]
            project.metadata['summary_generated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            project.save(update_fields=['metadata', 'updated_at'])
            
            return {
                'success': True,
                'handler': self.name,
                'summary': summary,
                'format': output_format,
                'sources_used': len(sources),
                'findings_used': len(findings),
                'execution_time_ms': execution_time
            }
            
        except ResearchProject.DoesNotExist:
            return {
                'success': False,
                'error': f'Project {project_id} not found',
                'handler': self.name
            }
        except Exception as e:
            logger.error(f"SummaryHandler error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'handler': self.name
            }
    
    def _generate_rule_based_summary(
        self,
        project: ResearchProject,
        sources: List,
        findings: List,
        options: Dict
    ) -> str:
        """Generate summary using rule-based approach."""
        output_format = options.get('format', 'markdown')
        include_sources = options.get('include_sources', True)
        
        if output_format == 'markdown':
            return self._format_markdown_summary(project, sources, findings, include_sources)
        elif output_format == 'json':
            return self._format_json_summary(project, sources, findings)
        else:
            return self._format_text_summary(project, sources, findings, include_sources)
    
    def _format_markdown_summary(
        self,
        project: ResearchProject,
        sources: List,
        findings: List,
        include_sources: bool
    ) -> str:
        """Format summary as Markdown."""
        lines = [
            f"# Research Summary: {project.name}",
            "",
            f"**Query:** {project.query or project.description}",
            f"**Status:** {project.get_status_display()}",
            f"**Sources:** {len(sources)} | **Findings:** {len(findings)}",
            "",
            "---",
            "",
            "## Key Findings",
            ""
        ]
        
        if findings:
            # Group by type
            facts = [f for f in findings if f.finding_type == 'fact']
            statistics = [f for f in findings if f.finding_type == 'statistic']
            quotes = [f for f in findings if f.finding_type == 'quote']
            other = [f for f in findings if f.finding_type not in ('fact', 'statistic', 'quote')]
            
            if facts:
                lines.append("### Facts")
                for i, finding in enumerate(facts[:5], 1):
                    verified = "✓" if finding.is_verified else "○"
                    lines.append(f"{i}. {verified} {finding.content}")
                lines.append("")
            
            if statistics:
                lines.append("### Statistics")
                for finding in statistics[:3]:
                    lines.append(f"- {finding.content}")
                lines.append("")
            
            if quotes:
                lines.append("### Notable Quotes")
                for finding in quotes[:3]:
                    lines.append(f"> {finding.content}")
                lines.append("")
            
            if other:
                lines.append("### Other Findings")
                for finding in other[:5]:
                    lines.append(f"- {finding.content}")
                lines.append("")
        else:
            lines.append("*No findings recorded yet.*")
            lines.append("")
        
        if include_sources and sources:
            lines.extend([
                "---",
                "",
                "## Sources",
                ""
            ])
            for i, source in enumerate(sources[:10], 1):
                if source.url:
                    lines.append(f"{i}. [{source.title[:60]}]({source.url})")
                else:
                    lines.append(f"{i}. {source.title[:60]}")
        
        lines.extend([
            "",
            "---",
            f"*Generated: {time.strftime('%Y-%m-%d %H:%M')}*"
        ])
        
        return "\n".join(lines)
    
    def _format_text_summary(
        self,
        project: ResearchProject,
        sources: List,
        findings: List,
        include_sources: bool
    ) -> str:
        """Format summary as plain text."""
        lines = [
            f"RESEARCH SUMMARY: {project.name}",
            "=" * 50,
            "",
            f"Query: {project.query or project.description}",
            f"Status: {project.get_status_display()}",
            f"Sources: {len(sources)} | Findings: {len(findings)}",
            "",
            "KEY FINDINGS:",
            "-" * 30,
        ]
        
        for i, finding in enumerate(findings[:10], 1):
            verified = "[✓]" if finding.is_verified else "[ ]"
            lines.append(f"  {i}. {verified} {finding.content}")
        
        if include_sources and sources:
            lines.extend([
                "",
                "SOURCES:",
                "-" * 30,
            ])
            for i, source in enumerate(sources[:10], 1):
                lines.append(f"  {i}. {source.title[:50]}")
                if source.url:
                    lines.append(f"     URL: {source.url}")
        
        return "\n".join(lines)
    
    def _format_json_summary(
        self,
        project: ResearchProject,
        sources: List,
        findings: List
    ) -> str:
        """Format summary as JSON string."""
        import json
        
        data = {
            'project': {
                'id': project.id,
                'name': project.name,
                'query': project.query,
                'status': project.status
            },
            'statistics': {
                'sources': len(sources),
                'findings': len(findings),
                'verified_findings': sum(1 for f in findings if f.is_verified)
            },
            'findings': [
                {
                    'content': f.content,
                    'type': f.finding_type,
                    'verified': f.is_verified,
                    'importance': f.importance
                }
                for f in findings[:20]
            ],
            'sources': [
                {
                    'title': s.title,
                    'url': s.url,
                    'type': s.source_type,
                    'relevance': s.relevance_score
                }
                for s in sources[:20]
            ]
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _generate_ai_summary(
        self,
        project: ResearchProject,
        sources: List,
        findings: List,
        options: Dict
    ) -> str:
        """Generate summary using AI/LLM."""
        # TODO: Implement LLM-based summary generation
        # For now, fall back to rule-based
        logger.info("AI summary not yet implemented, using rule-based")
        return self._generate_rule_based_summary(project, sources, findings, options)
