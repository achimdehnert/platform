"""
Outline Generation Agents
==========================

AI agents for dynamic outline generation.

Agents:
- OutlineStructureAgent: Determines overall structure
- OutlineBeatAgent: Generates detailed beats/sections
- OutlineGuidanceAgent: Generates writing guidance
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentInput:
    """Base input for outline agents."""
    project_type: str
    title: str
    context: Dict = field(default_factory=dict)
    constraints: Dict = field(default_factory=dict)


@dataclass
class AgentOutput:
    """Base output from outline agents."""
    success: bool
    data: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class BaseOutlineAgent:
    """Base class for outline agents."""
    
    AGENT_NAME = "base_outline_agent"
    
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
                logger.warning("LLM client not available")
        return self._llm_client
    
    def get_agent(self):
        """Get Django agent for this outline agent."""
        if self._agent is None:
            try:
                from apps.core.models import Agent
                # Try to find specific agent first
                self._agent = Agent.objects.filter(
                    name__icontains=self.AGENT_NAME.replace("_", " ")
                ).first()
                # Fallback to outline or research agent
                if not self._agent:
                    self._agent = Agent.objects.filter(
                        name__icontains="outline"
                    ).first()
                if not self._agent:
                    self._agent = Agent.objects.filter(
                        name__icontains="research"
                    ).first()
            except Exception as e:
                logger.warning(f"Could not load agent: {e}")
        return self._agent
    
    async def execute(self, inputs: Dict) -> AgentOutput:
        """Execute agent logic. Override in subclasses."""
        raise NotImplementedError
    
    def execute_sync(self, inputs: Dict) -> AgentOutput:
        """Synchronous wrapper."""
        import asyncio
        return asyncio.run(self.execute(inputs))
    
    def _call_llm(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """Call LLM synchronously."""
        try:
            from apps.bfagent.services.llm_client import generate_text
            
            agent = self.get_agent()
            response = generate_text(
                prompt=prompt,
                agent=agent,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None
    
    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response."""
        if not response:
            return {}
        
        try:
            # Try to extract JSON
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
            logger.warning(f"Failed to parse JSON: {e}")
            return {}


class OutlineStructureAgent(BaseOutlineAgent):
    """
    Determines overall structure based on inputs.
    
    Takes project type, genre, and context to suggest:
    - Number of sections/chapters
    - Overall arc/flow
    - Key structural elements
    """
    
    AGENT_NAME = "outline_structure"
    
    INPUT_SCHEMA = {
        "project_type": str,  # book, paper, article
        "framework": str,  # optional framework name
        "genre": str,  # optional genre
        "context": dict,  # topic, characters, etc.
        "constraints": dict  # word count, chapters, etc.
    }
    
    async def execute(self, inputs: Dict) -> AgentOutput:
        """Generate high-level structure."""
        
        project_type = inputs.get("project_type", "book")
        framework = inputs.get("framework", "")
        genre = inputs.get("genre", "")
        context = inputs.get("context", {})
        constraints = inputs.get("constraints", {})
        
        prompt = self._build_prompt(project_type, framework, genre, context, constraints)
        response = self._call_llm(prompt)
        
        if not response:
            return AgentOutput(
                success=False,
                errors=["LLM call failed"]
            )
        
        structure = self._parse_json_response(response)
        
        if not structure:
            return AgentOutput(
                success=False,
                errors=["Failed to parse structure response"]
            )
        
        return AgentOutput(
            success=True,
            data=structure
        )
    
    def _build_prompt(
        self,
        project_type: str,
        framework: str,
        genre: str,
        context: Dict,
        constraints: Dict
    ) -> str:
        """Build prompt for structure generation."""
        
        context_str = "\n".join(f"  - {k}: {v}" for k, v in context.items())
        constraints_str = "\n".join(f"  - {k}: {v}" for k, v in constraints.items())
        
        return f"""You are an expert outline architect. Generate a structure for a {project_type}.

PROJECT TYPE: {project_type}
{f"FRAMEWORK: {framework}" if framework else ""}
{f"GENRE: {genre}" if genre else ""}

CONTEXT:
{context_str if context_str else "  (none provided)"}

CONSTRAINTS:
{constraints_str if constraints_str else "  (none provided)"}

Generate a complete structure with sections/chapters. For each section provide:
- name: Section/chapter name
- purpose: What this section achieves
- position: Where in the arc (beginning, rising, climax, falling, end)
- word_percentage: Approximate percentage of total word count

Respond in JSON format:
{{
    "total_sections": <number>,
    "structure_type": "<linear|circular|parallel|nested>",
    "arc_description": "<description of overall narrative/logical arc>",
    "sections": [
        {{
            "number": 1,
            "name": "<section name>",
            "purpose": "<purpose>",
            "position": "<position in arc>",
            "word_percentage": <0.0-1.0>
        }},
        ...
    ]
}}
"""


class OutlineBeatAgent(BaseOutlineAgent):
    """
    Generates detailed beats for each section.
    
    Takes structure and expands each section with:
    - Key points to cover
    - Narrative beats or logical steps
    - Subsections if needed
    """
    
    AGENT_NAME = "outline_beat"
    
    async def execute(self, inputs: Dict) -> AgentOutput:
        """Add detailed beats to structure."""
        
        structure = inputs.get("structure", {})
        project_type = inputs.get("project_type", "book")
        context = inputs.get("context", {})
        
        if not structure.get("sections"):
            return AgentOutput(
                success=False,
                errors=["No sections in structure"]
            )
        
        enhanced_sections = []
        
        for section in structure["sections"]:
            prompt = self._build_beat_prompt(section, project_type, context)
            response = self._call_llm(prompt, max_tokens=1000)
            
            beats = self._parse_json_response(response)
            
            if beats:
                section.update(beats)
            
            enhanced_sections.append(section)
        
        return AgentOutput(
            success=True,
            data={
                **structure,
                "sections": enhanced_sections
            }
        )
    
    def _build_beat_prompt(
        self,
        section: Dict,
        project_type: str,
        context: Dict
    ) -> str:
        """Build prompt for beat generation."""
        
        context_str = "\n".join(f"  - {k}: {v}" for k, v in context.items())
        
        return f"""Generate detailed beats for this {project_type} section.

SECTION: {section.get('name', 'Untitled')}
PURPOSE: {section.get('purpose', '')}
POSITION: {section.get('position', '')}

CONTEXT:
{context_str if context_str else "  (none)"}

Generate specific beats/points this section should cover.

Respond in JSON format:
{{
    "key_points": ["<point 1>", "<point 2>", "<point 3>"],
    "beats": [
        {{
            "name": "<beat name>",
            "description": "<what happens>",
            "emotional_tone": "<tone>"
        }}
    ],
    "questions_to_answer": ["<question 1>", "<question 2>"],
    "subsections": [
        {{"name": "<subsection name>", "purpose": "<purpose>"}}
    ]
}}
"""


class OutlineGuidanceAgent(BaseOutlineAgent):
    """
    Generates specific writing guidance for each section.
    
    Provides:
    - Opening suggestions
    - Tone and style guidance
    - Things to avoid
    - Examples or references
    """
    
    AGENT_NAME = "outline_guidance"
    
    async def execute(self, inputs: Dict) -> AgentOutput:
        """Add writing guidance to sections."""
        
        structure = inputs.get("structure", {})
        project_type = inputs.get("project_type", "book")
        context = inputs.get("context", {})
        style = context.get("style", "")
        
        if not structure.get("sections"):
            return AgentOutput(
                success=False,
                errors=["No sections in structure"]
            )
        
        guided_sections = []
        
        for section in structure["sections"]:
            prompt = self._build_guidance_prompt(section, project_type, style, context)
            response = self._call_llm(prompt, max_tokens=800)
            
            guidance = self._parse_json_response(response)
            
            if guidance:
                section.update(guidance)
            
            guided_sections.append(section)
        
        return AgentOutput(
            success=True,
            data={
                **structure,
                "sections": guided_sections
            }
        )
    
    def _build_guidance_prompt(
        self,
        section: Dict,
        project_type: str,
        style: str,
        context: Dict
    ) -> str:
        """Build prompt for guidance generation."""
        
        return f"""Generate writing guidance for this {project_type} section.

SECTION: {section.get('name', 'Untitled')}
KEY POINTS: {section.get('key_points', [])}
{f"STYLE: {style}" if style else ""}

Provide specific, actionable writing guidance.

Respond in JSON format:
{{
    "writing_guidance": "<detailed guidance>",
    "opening_suggestion": "<how to start this section>",
    "tone": "<recommended tone>",
    "things_to_avoid": ["<avoid 1>", "<avoid 2>"],
    "pro_tips": ["<tip 1>", "<tip 2>"]
}}
"""


class OutlineTemplateAnalyzer(BaseOutlineAgent):
    """
    Analyzes existing works to create templates.
    
    Extracts:
    - Chapter/section structure
    - Pacing patterns
    - Beat distribution
    - Style characteristics
    """
    
    AGENT_NAME = "outline_analyzer"
    
    async def analyze_text(self, text: str, source_type: str = "book") -> AgentOutput:
        """Analyze text to extract outline template."""
        
        # For long texts, analyze structure from TOC or chapter markers
        chapters = self._extract_chapters(text)
        
        if not chapters:
            return AgentOutput(
                success=False,
                errors=["Could not extract chapters from text"]
            )
        
        # Analyze each chapter
        prompt = self._build_analysis_prompt(chapters, source_type)
        response = self._call_llm(prompt, max_tokens=2000)
        
        template = self._parse_json_response(response)
        
        if not template:
            return AgentOutput(
                success=False,
                errors=["Failed to analyze structure"]
            )
        
        return AgentOutput(
            success=True,
            data=template
        )
    
    def _extract_chapters(self, text: str) -> List[Dict]:
        """Extract chapters from text."""
        import re
        
        chapters = []
        
        # Try common chapter patterns
        patterns = [
            r"Chapter\s+(\d+)[:\s]+([^\n]+)",
            r"CHAPTER\s+(\d+)[:\s]+([^\n]+)",
            r"(\d+)\.\s+([^\n]+)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                for num, title in matches:
                    chapters.append({
                        "number": int(num),
                        "title": title.strip()
                    })
                break
        
        # Estimate word count per chapter
        if chapters:
            words_per_chapter = len(text.split()) // len(chapters)
            for ch in chapters:
                ch["estimated_words"] = words_per_chapter
        
        return chapters
    
    def _build_analysis_prompt(self, chapters: List[Dict], source_type: str) -> str:
        """Build prompt for structure analysis."""
        
        chapter_list = "\n".join(
            f"  {ch['number']}. {ch['title']} (~{ch.get('estimated_words', 0)} words)"
            for ch in chapters
        )
        
        return f"""Analyze this {source_type} structure to create a reusable template.

CHAPTERS:
{chapter_list}

Extract the structural pattern:
1. How are chapters organized?
2. What's the pacing pattern?
3. What beats/elements repeat?

Respond in JSON format:
{{
    "template_name": "<descriptive name>",
    "structure_pattern": "<pattern description>",
    "typical_chapter_count": <number>,
    "pacing_curve": "<description of pacing>",
    "characteristic_beats": [
        {{"position": <0.0-1.0>, "beat_type": "<type>", "description": "<desc>"}}
    ],
    "style_notes": "<notes on style>"
}}
"""


# Factory function to get all agents
def get_outline_agents() -> Dict[str, BaseOutlineAgent]:
    """Get all outline agents."""
    return {
        "structure": OutlineStructureAgent(),
        "beat": OutlineBeatAgent(),
        "guidance": OutlineGuidanceAgent(),
        "analyzer": OutlineTemplateAnalyzer()
    }
