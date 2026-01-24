"""
Deep Dive Research Handler
===========================

Handler for comprehensive, in-depth research on a topic.
Generates structured reports with multiple sections.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional, List
from datetime import datetime

from ..models import ResearchProject, ResearchSource, ResearchFinding, ResearchResult
from ..services import get_brave_search, get_research_service

logger = logging.getLogger(__name__)


@dataclass
class DeepDiveSection:
    """A section in the deep dive report."""
    title: str
    content: str
    sources: List[int] = field(default_factory=list)
    findings: List[int] = field(default_factory=list)


@dataclass
class DeepDiveReport:
    """Complete deep dive research report."""
    title: str
    executive_summary: str
    sections: List[DeepDiveSection]
    key_findings: List[str]
    recommendations: List[str]
    sources_count: int
    generated_at: str


class DeepDiveHandler:
    """
    Handler for comprehensive topic research.
    
    Features:
    - Multi-query search strategy
    - Automatic subtopic discovery
    - Structured report generation
    - Key findings extraction
    - Recommendations synthesis
    """
    
    handler_id = "deep_dive"
    version = "1.0.0"
    domains = ["research"]
    
    # Default sections for deep dive report
    DEFAULT_SECTIONS = [
        ('overview', 'Overview', '{topic}'),
        ('history', 'Historical Context', '{topic} history background'),
        ('current_state', 'Current State', '{topic} current trends 2024'),
        ('challenges', 'Challenges & Problems', '{topic} challenges problems issues'),
        ('solutions', 'Solutions & Approaches', '{topic} solutions approaches methods'),
        ('future', 'Future Outlook', '{topic} future trends predictions'),
    ]
    
    def __init__(self):
        self.brave_search = get_brave_search()
    
    def execute(
        self,
        project_id: int,
        query: str = "",
        options: dict = None
    ) -> dict:
        """
        Execute deep dive research for a topic.
        
        Args:
            project_id: ID of the research project
            query: Main topic (uses project.query if not provided)
            options: Additional options
        
        Returns:
            Dictionary with research report
        """
        options = options or {}
        start_time = datetime.now()
        
        try:
            project = ResearchProject.objects.get(pk=project_id)
            
            # Use project query if not provided
            topic = query or project.query
            if not topic:
                return self._error_result("No research topic provided")
            
            # Get custom sections or use defaults
            sections_config = options.get('sections', self.DEFAULT_SECTIONS)
            
            # Research each section
            report_sections = []
            total_sources = 0
            all_findings = []
            
            for section_id, section_title, query_template in sections_config:
                section_query = query_template.format(topic=topic)
                
                # Search for this section
                search_results = self.brave_search.search(
                    section_query,
                    count=options.get('sources_per_section', 5)
                )
                
                if search_results.get('success'):
                    # Process results for this section
                    section_sources = []
                    section_content_parts = []
                    
                    for result in search_results.get('results', []):
                        source = self._create_source(project, result, section_id)
                        if source:
                            section_sources.append(source.pk)
                            total_sources += 1
                            
                            # Extract key points from snippet
                            if result.get('description'):
                                section_content_parts.append(result['description'])
                    
                    # Generate section content
                    section_content = self._synthesize_section(
                        section_title,
                        section_content_parts
                    )
                    
                    # Extract findings for this section
                    section_findings = self._extract_section_findings(
                        project, section_id, section_content_parts
                    )
                    all_findings.extend(section_findings)
                    
                    report_sections.append(DeepDiveSection(
                        title=section_title,
                        content=section_content,
                        sources=section_sources,
                        findings=[f.pk for f in section_findings]
                    ))
            
            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                topic, report_sections
            )
            
            # Extract key findings
            key_findings = self._compile_key_findings(all_findings)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                topic, report_sections, all_findings
            )
            
            # Build report
            report = DeepDiveReport(
                title=f"Deep Dive: {topic}",
                executive_summary=executive_summary,
                sections=report_sections,
                key_findings=key_findings,
                recommendations=recommendations,
                sources_count=total_sources,
                generated_at=datetime.now().isoformat()
            )
            
            # Store as markdown
            markdown_report = self._report_to_markdown(report)
            
            # Store result
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result_data = {
                'topic': topic,
                'report_title': report.title,
                'executive_summary': report.executive_summary,
                'sections_count': len(report_sections),
                'sources_count': total_sources,
                'findings_count': len(all_findings),
                'key_findings': key_findings,
                'recommendations': recommendations,
                'markdown_report': markdown_report,
            }
            
            # Store in project metadata
            project.metadata['last_deep_dive'] = markdown_report
            project.metadata['deep_dive_generated_at'] = datetime.now().isoformat()
            project.save()
            
            ResearchResult.objects.create(
                project=project,
                handler_name=self.handler_id,
                phase='analyse',
                result_data=result_data,
                success=True,
                execution_time_ms=int(execution_time)
            )
            
            # Update project
            if project.current_phase in ['thema_definieren', 'quellen_sammeln']:
                project.current_phase = 'analyse'
                project.status = ResearchProject.Status.IN_PROGRESS
                project.save()
            
            return {
                'success': True,
                **result_data
            }
            
        except ResearchProject.DoesNotExist:
            return self._error_result(f"Project {project_id} not found")
        except Exception as e:
            logger.error(f"Deep dive error: {e}", exc_info=True)
            return self._error_result(str(e))
    
    def _create_source(
        self,
        project: ResearchProject,
        result: dict,
        section_id: str
    ) -> Optional[ResearchSource]:
        """Create a research source from search result."""
        try:
            return ResearchSource.objects.create(
                project=project,
                title=result.get('title', 'Unknown'),
                url=result.get('url', ''),
                source_type=ResearchSource.SourceType.WEB,
                snippet=result.get('description', ''),
                relevance_score=result.get('relevance_score', 0.5),
                metadata={
                    'section': section_id,
                    'search_position': result.get('position', 0),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to create source: {e}")
            return None
    
    def _synthesize_section(
        self,
        title: str,
        content_parts: List[str]
    ) -> str:
        """Synthesize section content from multiple sources."""
        if not content_parts:
            return f"No information found for {title}."
        
        # Simple synthesis: combine unique information
        unique_parts = []
        seen = set()
        
        for part in content_parts:
            # Normalize and check for duplicates
            normalized = part.lower().strip()[:100]
            if normalized not in seen:
                seen.add(normalized)
                unique_parts.append(part)
        
        return "\n\n".join(unique_parts[:5])
    
    def _extract_section_findings(
        self,
        project: ResearchProject,
        section_id: str,
        content_parts: List[str]
    ) -> List[ResearchFinding]:
        """Extract key findings from section content."""
        findings = []
        
        for i, content in enumerate(content_parts[:3]):
            if len(content) > 50:  # Only meaningful content
                finding = ResearchFinding.objects.create(
                    project=project,
                    content=content[:500],
                    finding_type=ResearchFinding.FindingType.FACT,
                    importance=max(5, 8 - i),  # Higher importance for earlier findings
                    tags=[section_id]
                )
                findings.append(finding)
        
        return findings
    
    def _generate_executive_summary(
        self,
        topic: str,
        sections: List[DeepDiveSection]
    ) -> str:
        """Generate executive summary from all sections."""
        summary_parts = [f"This report provides a comprehensive analysis of **{topic}**."]
        
        for section in sections:
            if section.content and len(section.content) > 100:
                # Take first sentence of each section
                first_sentence = section.content.split('.')[0] + '.'
                if len(first_sentence) > 30:
                    summary_parts.append(first_sentence)
        
        return " ".join(summary_parts[:5])
    
    def _compile_key_findings(
        self,
        findings: List[ResearchFinding]
    ) -> List[str]:
        """Compile list of key findings."""
        # Sort by importance and take top 5
        sorted_findings = sorted(
            findings,
            key=lambda f: f.importance,
            reverse=True
        )
        
        return [f.content[:200] for f in sorted_findings[:5]]
    
    def _generate_recommendations(
        self,
        topic: str,
        sections: List[DeepDiveSection],
        findings: List[ResearchFinding]
    ) -> List[str]:
        """Generate recommendations based on findings."""
        recommendations = []
        
        # Find challenges section
        challenge_section = next(
            (s for s in sections if 'challenge' in s.title.lower()),
            None
        )
        
        if challenge_section and challenge_section.content:
            recommendations.append(
                f"Address identified challenges in {topic} through targeted interventions."
            )
        
        # Find solutions section
        solution_section = next(
            (s for s in sections if 'solution' in s.title.lower()),
            None
        )
        
        if solution_section and solution_section.content:
            recommendations.append(
                f"Implement proven solutions and best practices from the research."
            )
        
        # Generic recommendations based on findings
        if len(findings) > 0:
            recommendations.append(
                "Continue monitoring developments in this area for emerging trends."
            )
        
        recommendations.append(
            f"Further research recommended to deepen understanding of specific aspects."
        )
        
        return recommendations
    
    def _report_to_markdown(self, report: DeepDiveReport) -> str:
        """Convert report to markdown format."""
        lines = [
            f"# {report.title}",
            "",
            f"*Generated: {report.generated_at}*",
            "",
            "## Executive Summary",
            "",
            report.executive_summary,
            "",
        ]
        
        # Add sections
        for section in report.sections:
            lines.extend([
                f"## {section.title}",
                "",
                section.content,
                "",
            ])
        
        # Key findings
        lines.extend([
            "## Key Findings",
            "",
        ])
        for i, finding in enumerate(report.key_findings, 1):
            lines.append(f"{i}. {finding}")
        lines.append("")
        
        # Recommendations
        lines.extend([
            "## Recommendations",
            "",
        ])
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        # Footer
        lines.extend([
            "---",
            f"*Sources analyzed: {report.sources_count}*",
        ])
        
        return "\n".join(lines)
    
    def _error_result(self, error: str) -> dict:
        """Return error result."""
        return {
            'success': False,
            'error': error,
        }
