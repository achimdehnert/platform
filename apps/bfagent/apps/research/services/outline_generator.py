"""
Dynamic Outline Generator Service
==================================

AI-powered outline generation for books and scientific papers.

Features:
- Framework-based generation (IMRAD, Save the Cat, etc.)
- Template-based generation (author styles, paper types)
- Rule-based customization (via MCP tools)
- Context-aware adaptation
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from django.conf import settings

from .paper_frameworks import get_paper_framework, PAPER_FRAMEWORKS, PaperSection
from apps.bfagent.services.story_frameworks import get_framework, STORY_FRAMEWORKS

logger = logging.getLogger(__name__)


class ProjectType(Enum):
    """Types of projects for outline generation."""
    BOOK = "book"
    PAPER = "paper"
    ARTICLE = "article"
    BLOG = "blog"
    REPORT = "report"


class OutlineStatus(Enum):
    """Status of outline sections."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DRAFT = "draft"
    COMPLETE = "complete"


@dataclass
class OutlineSection:
    """A section in the generated outline."""
    number: int
    name: str
    section_type: str  # chapter, section, subsection, beat
    
    # Content guidance
    word_target: int = 0
    key_points: List[str] = field(default_factory=list)
    writing_guidance: str = ""
    questions_to_answer: List[str] = field(default_factory=list)
    
    # For creative writing
    beat: Optional[str] = None
    emotional_arc: Optional[str] = None
    pov_character: Optional[str] = None
    tension_level: Optional[float] = None  # 0.0 - 1.0
    
    # For scientific writing
    required_elements: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    
    # Nesting
    subsections: List['OutlineSection'] = field(default_factory=list)
    
    # Status tracking
    status: str = "pending"
    progress_percent: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['subsections'] = [s.to_dict() for s in self.subsections] if self.subsections else []
        return data


@dataclass
class GeneratedOutline:
    """A dynamically generated outline."""
    
    # Metadata
    id: str = ""
    title: str = ""
    project_type: str = "book"
    framework_used: str = ""
    template_used: Optional[str] = None
    
    # Targets
    total_word_target: int = 0
    total_sections: int = 0
    estimated_duration: str = ""
    
    # Structure
    sections: List[OutlineSection] = field(default_factory=list)
    
    # Generation info
    generated_at: str = ""
    rules_applied: List[str] = field(default_factory=list)
    context_used: Dict = field(default_factory=dict)
    
    # Validation
    completeness_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "project_type": self.project_type,
            "framework_used": self.framework_used,
            "template_used": self.template_used,
            "total_word_target": self.total_word_target,
            "total_sections": self.total_sections,
            "estimated_duration": self.estimated_duration,
            "sections": [s.to_dict() for s in self.sections],
            "generated_at": self.generated_at,
            "rules_applied": self.rules_applied,
            "context_used": self.context_used,
            "completeness_score": self.completeness_score,
            "warnings": self.warnings
        }
    
    def to_markdown(self) -> str:
        """Export as Markdown."""
        lines = [
            f"# {self.title}",
            "",
            f"**Framework:** {self.framework_used}",
            f"**Word Target:** {self.total_word_target:,}",
            f"**Sections:** {self.total_sections}",
            f"**Estimated Duration:** {self.estimated_duration}",
            "",
            "---",
            ""
        ]
        
        for section in self.sections:
            lines.extend(self._section_to_markdown(section, level=2))
        
        return "\n".join(lines)
    
    def _section_to_markdown(self, section: OutlineSection, level: int = 2) -> List[str]:
        """Convert section to Markdown lines."""
        lines = []
        prefix = "#" * level
        
        lines.append(f"{prefix} {section.number}. {section.name}")
        lines.append(f"*{section.word_target:,} words | {section.section_type}*")
        lines.append("")
        
        if section.beat:
            lines.append(f"**Beat:** {section.beat}")
        if section.emotional_arc:
            lines.append(f"**Emotional Arc:** {section.emotional_arc}")
        
        if section.key_points:
            lines.append("**Key Points:**")
            for point in section.key_points:
                lines.append(f"- {point}")
            lines.append("")
        
        if section.writing_guidance:
            lines.append(f"**Guidance:** {section.writing_guidance}")
            lines.append("")
        
        if section.questions_to_answer:
            lines.append("**Questions to Answer:**")
            for q in section.questions_to_answer:
                lines.append(f"- {q}")
            lines.append("")
        
        if section.subsections:
            for sub in section.subsections:
                lines.extend(self._section_to_markdown(sub, level + 1))
        
        lines.append("---")
        lines.append("")
        
        return lines


class OutlineGeneratorService:
    """
    Main service for generating dynamic outlines.
    
    Combines:
    - Static frameworks (IMRAD, Save the Cat)
    - AI-generated beats and guidance
    - Rule-based customization
    - Template-based adaptation
    """
    
    def __init__(self):
        self._llm_client = None
        self._agent = None
    
    @property
    def llm_client(self):
        """Lazy load LLM client."""
        if self._llm_client is None:
            try:
                from apps.bfagent.services.llm_client import get_llm_client
                self._llm_client = get_llm_client()
            except ImportError:
                logger.warning("LLM client not available, using mock mode")
                self._llm_client = None
        return self._llm_client
    
    @property
    def agent(self):
        """Get Django agent for outline generation."""
        if self._agent is None:
            try:
                from apps.core.models import Agent
                self._agent = Agent.objects.filter(
                    name__icontains="outline"
                ).first()
                if not self._agent:
                    # Fallback to research or general agent
                    self._agent = Agent.objects.filter(
                        name__icontains="research"
                    ).first()
            except Exception as e:
                logger.warning(f"Could not load agent: {e}")
        return self._agent
    
    async def generate(
        self,
        project_type: str,
        title: str = "",
        framework: str = None,
        source_template: str = None,
        context: Dict = None,
        constraints: Dict = None,
        rules: List[str] = None,
        use_ai: bool = True
    ) -> GeneratedOutline:
        """
        Generate a complete outline.
        
        Args:
            project_type: "book", "paper", "article", "report"
            title: Project title
            framework: Framework name (e.g., "imrad", "heros_journey")
            source_template: Template name or author style
            context: Context dict (genre, topic, characters, etc.)
            constraints: Constraints (word_count, chapters, etc.)
            rules: List of rule names to apply
            use_ai: Whether to use AI for enhancement
            
        Returns:
            GeneratedOutline with complete structure
        """
        import uuid
        
        context = context or {}
        constraints = constraints or {}
        rules = rules or []
        
        # Step 1: Determine base framework
        base_sections = await self._get_base_structure(
            project_type, framework, source_template
        )
        
        # Step 2: Calculate word targets
        total_words = constraints.get('word_count', self._default_word_count(project_type))
        sections_with_targets = self._distribute_word_counts(base_sections, total_words)
        
        # Step 3: AI Enhancement (if enabled)
        if use_ai and self.llm_client:
            sections_with_targets = await self._enhance_with_ai(
                sections_with_targets,
                project_type,
                context,
                title
            )
        else:
            # Add basic guidance without AI
            sections_with_targets = self._add_basic_guidance(
                sections_with_targets,
                project_type,
                context
            )
        
        # Step 4: Apply rules
        for rule in rules:
            sections_with_targets = await self._apply_rule(
                sections_with_targets, rule, context
            )
        
        # Step 5: Validate
        warnings = self._validate_outline(sections_with_targets, constraints)
        
        # Step 6: Build final outline
        outline = GeneratedOutline(
            id=str(uuid.uuid4()),
            title=title or f"Untitled {project_type.title()}",
            project_type=project_type,
            framework_used=framework or "auto",
            template_used=source_template,
            total_word_target=total_words,
            total_sections=len(sections_with_targets),
            estimated_duration=self._estimate_duration(total_words),
            sections=sections_with_targets,
            generated_at=datetime.now().isoformat(),
            rules_applied=rules,
            context_used=context,
            completeness_score=self._calculate_completeness(sections_with_targets),
            warnings=warnings
        )
        
        return outline
    
    def generate_sync(self, **kwargs) -> GeneratedOutline:
        """Synchronous wrapper for generate()."""
        import asyncio
        return asyncio.run(self.generate(**kwargs))
    
    async def _get_base_structure(
        self,
        project_type: str,
        framework: str = None,
        source_template: str = None
    ) -> List[OutlineSection]:
        """Get base structure from framework or template."""
        
        sections = []
        
        if project_type in ["paper", "article", "report"]:
            # Use paper framework
            fw_name = framework or "imrad"
            fw = get_paper_framework(fw_name)
            
            for i, section in enumerate(fw.sections, 1):
                sections.append(OutlineSection(
                    number=i,
                    name=section.name,
                    section_type="section",
                    word_target=0,  # Will be calculated
                    writing_guidance=section.guidance,
                    required_elements=section.subsections,
                    common_mistakes=section.common_mistakes if hasattr(section, 'common_mistakes') else ""
                ))
        
        elif project_type == "book":
            # Use story framework
            fw_name = framework or "three_act"
            fw = get_framework(fw_name)
            
            for i, beat in enumerate(fw.beats, 1):
                sections.append(OutlineSection(
                    number=i,
                    name=beat.name,
                    section_type="chapter",
                    beat=beat.name,
                    emotional_arc=beat.emotional_arc,
                    writing_guidance=beat.chapter_guidance,
                    tension_level=beat.typical_position
                ))
        
        else:
            # Generic structure
            sections = [
                OutlineSection(number=1, name="Introduction", section_type="section"),
                OutlineSection(number=2, name="Main Content", section_type="section"),
                OutlineSection(number=3, name="Conclusion", section_type="section"),
            ]
        
        return sections
    
    def _distribute_word_counts(
        self,
        sections: List[OutlineSection],
        total_words: int
    ) -> List[OutlineSection]:
        """Distribute word counts across sections."""
        
        if not sections:
            return sections
        
        # Default: equal distribution with adjustment for intro/conclusion
        num_sections = len(sections)
        base_per_section = total_words // num_sections
        
        for i, section in enumerate(sections):
            if i == 0:  # Introduction typically shorter
                section.word_target = int(base_per_section * 0.8)
            elif i == num_sections - 1:  # Conclusion shorter
                section.word_target = int(base_per_section * 0.6)
            else:
                section.word_target = base_per_section
        
        # Adjust to match total
        current_total = sum(s.word_target for s in sections)
        if current_total != total_words:
            # Add difference to middle sections
            diff = total_words - current_total
            middle = num_sections // 2
            sections[middle].word_target += diff
        
        return sections
    
    async def _enhance_with_ai(
        self,
        sections: List[OutlineSection],
        project_type: str,
        context: Dict,
        title: str
    ) -> List[OutlineSection]:
        """Enhance sections with AI-generated content."""
        
        try:
            from apps.bfagent.services.llm_client import generate_text
            
            for section in sections:
                prompt = self._build_enhancement_prompt(
                    section, project_type, context, title
                )
                
                response = await self._call_llm_async(prompt)
                
                if response:
                    enhancements = self._parse_enhancement_response(response)
                    
                    if enhancements.get('key_points'):
                        section.key_points = enhancements['key_points']
                    if enhancements.get('questions'):
                        section.questions_to_answer = enhancements['questions']
                    if enhancements.get('guidance'):
                        section.writing_guidance = enhancements['guidance']
            
        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}")
            # Fallback to basic guidance
            sections = self._add_basic_guidance(sections, project_type, context)
        
        return sections
    
    async def _call_llm_async(self, prompt: str) -> Optional[str]:
        """Call LLM asynchronously."""
        try:
            from apps.bfagent.services.llm_client import generate_text
            
            # Use agent if available
            agent = self.agent
            
            response = generate_text(
                prompt=prompt,
                agent=agent,
                max_tokens=1000,
                temperature=0.7
            )
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None
    
    def _build_enhancement_prompt(
        self,
        section: OutlineSection,
        project_type: str,
        context: Dict,
        title: str
    ) -> str:
        """Build prompt for AI enhancement."""
        
        context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
        
        prompt = f"""Generate outline details for a {project_type} section.

PROJECT: {title}
SECTION: {section.name} (#{section.number})
SECTION TYPE: {section.section_type}
WORD TARGET: {section.word_target}

CONTEXT:
{context_str}

{f"BEAT: {section.beat}" if section.beat else ""}
{f"EMOTIONAL ARC: {section.emotional_arc}" if section.emotional_arc else ""}

Please provide:
1. 3-5 key points this section should cover
2. 2-3 questions the section should answer
3. Specific writing guidance for this section

Respond in JSON format:
{{
    "key_points": ["point 1", "point 2", ...],
    "questions": ["question 1", "question 2", ...],
    "guidance": "specific guidance text"
}}
"""
        return prompt
    
    def _parse_enhancement_response(self, response: str) -> Dict:
        """Parse AI enhancement response."""
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
            else:
                return {}
            
            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse enhancement response: {e}")
            return {}
    
    def _add_basic_guidance(
        self,
        sections: List[OutlineSection],
        project_type: str,
        context: Dict
    ) -> List[OutlineSection]:
        """Add basic guidance without AI."""
        
        genre = context.get('genre', '')
        topic = context.get('topic', context.get('research_question', ''))
        
        for section in sections:
            # Add generic key points based on section type
            if section.section_type == "chapter":
                section.key_points = [
                    f"Advance the {genre} narrative",
                    f"Develop character arcs",
                    f"Build tension toward next beat"
                ]
            elif section.name.lower() == "introduction":
                section.key_points = [
                    "Establish context and background",
                    "State the problem/question",
                    "Preview the structure"
                ]
            elif section.name.lower() == "methods":
                section.key_points = [
                    "Describe research design",
                    "Detail data collection",
                    "Explain analysis approach"
                ]
            elif section.name.lower() == "results":
                section.key_points = [
                    "Present findings objectively",
                    "Use tables and figures",
                    "Report statistical significance"
                ]
            elif section.name.lower() == "discussion":
                section.key_points = [
                    "Interpret key findings",
                    "Compare with literature",
                    "Address limitations"
                ]
        
        return sections
    
    async def _apply_rule(
        self,
        sections: List[OutlineSection],
        rule: str,
        context: Dict
    ) -> List[OutlineSection]:
        """Apply a named rule to sections."""
        
        # Genre rules
        if rule == "fantasy":
            sections = self._apply_fantasy_rules(sections)
        elif rule == "thriller":
            sections = self._apply_thriller_rules(sections)
        elif rule == "romance":
            sections = self._apply_romance_rules(sections)
        elif rule == "horror":
            sections = self._apply_horror_rules(sections)
        
        # Paper rules
        elif rule == "nature_format":
            sections = self._apply_nature_rules(sections)
        elif rule == "apa_format":
            sections = self._apply_apa_rules(sections)
        
        return sections
    
    def _apply_fantasy_rules(self, sections: List[OutlineSection]) -> List[OutlineSection]:
        """Apply fantasy genre rules."""
        if sections:
            # Early worldbuilding
            sections[0].key_points.insert(0, "Establish magic system rules")
            sections[0].key_points.insert(1, "Introduce world's unique elements")
        return sections
    
    def _apply_thriller_rules(self, sections: List[OutlineSection]) -> List[OutlineSection]:
        """Apply thriller genre rules."""
        if sections:
            # Hook in first chapter
            sections[0].key_points.insert(0, "Open with immediate tension/threat")
            sections[0].key_points.insert(1, "Establish stakes early")
        return sections
    
    def _apply_romance_rules(self, sections: List[OutlineSection]) -> List[OutlineSection]:
        """Apply romance genre rules."""
        if len(sections) > 2:
            # Meet-cute by chapter 3
            sections[2].key_points.insert(0, "Meet-cute or significant first meeting")
        return sections
    
    def _apply_horror_rules(self, sections: List[OutlineSection]) -> List[OutlineSection]:
        """Apply horror genre rules."""
        if sections:
            sections[0].key_points.insert(0, "Establish normalcy before disruption")
            sections[0].key_points.insert(1, "Plant seeds of unease")
        return sections
    
    def _apply_nature_rules(self, sections: List[OutlineSection]) -> List[OutlineSection]:
        """Apply Nature journal format rules."""
        for section in sections:
            if section.name.lower() == "abstract":
                section.word_target = min(section.word_target, 150)
                section.key_points.append("Max 150 words (Nature requirement)")
        return sections
    
    def _apply_apa_rules(self, sections: List[OutlineSection]) -> List[OutlineSection]:
        """Apply APA format rules."""
        for section in sections:
            section.key_points.append("Follow APA 7th Edition formatting")
        return sections
    
    def _validate_outline(
        self,
        sections: List[OutlineSection],
        constraints: Dict
    ) -> List[str]:
        """Validate outline and return warnings."""
        warnings = []
        
        total_words = sum(s.word_target for s in sections)
        target_words = constraints.get('word_count', total_words)
        
        if abs(total_words - target_words) > target_words * 0.1:
            warnings.append(f"Word count mismatch: {total_words} vs target {target_words}")
        
        if constraints.get('min_sections') and len(sections) < constraints['min_sections']:
            warnings.append(f"Too few sections: {len(sections)} vs min {constraints['min_sections']}")
        
        # Check for empty sections
        empty = [s for s in sections if not s.key_points and not s.writing_guidance]
        if empty:
            warnings.append(f"{len(empty)} sections lack key points or guidance")
        
        return warnings
    
    def _calculate_completeness(self, sections: List[OutlineSection]) -> float:
        """Calculate outline completeness score (0-1)."""
        if not sections:
            return 0.0
        
        scores = []
        for section in sections:
            score = 0.0
            if section.name:
                score += 0.2
            if section.word_target > 0:
                score += 0.2
            if section.key_points:
                score += 0.3
            if section.writing_guidance:
                score += 0.3
            scores.append(score)
        
        return sum(scores) / len(scores)
    
    def _default_word_count(self, project_type: str) -> int:
        """Get default word count for project type."""
        defaults = {
            "book": 80000,
            "paper": 5000,
            "article": 3000,
            "blog": 1500,
            "report": 10000
        }
        return defaults.get(project_type, 5000)
    
    def _estimate_duration(self, word_count: int) -> str:
        """Estimate writing duration based on word count."""
        # Average: 500-1000 words/hour for first draft
        hours_min = word_count // 1000
        hours_max = word_count // 500
        
        if hours_max < 10:
            return f"{hours_min}-{hours_max} hours"
        elif hours_max < 40:
            days_min = hours_min // 8
            days_max = hours_max // 8
            return f"{days_min}-{days_max} days"
        else:
            weeks_min = hours_min // 40
            weeks_max = hours_max // 40
            return f"{weeks_min}-{weeks_max} weeks"


# Singleton instance
_outline_generator = None

def get_outline_generator() -> OutlineGeneratorService:
    """Get singleton instance of OutlineGeneratorService."""
    global _outline_generator
    if _outline_generator is None:
        _outline_generator = OutlineGeneratorService()
    return _outline_generator
