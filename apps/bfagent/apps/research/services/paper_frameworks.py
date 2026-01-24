"""
Scientific Paper Structure Frameworks
======================================

Provides templates for academic/scientific paper structures:
- IMRAD (Introduction, Methods, Results, Discussion)
- Systematic Review (PRISMA)
- Case Study
- Literature Review
- Technical Report
- Thesis/Dissertation
- Lab Report
- Conference Paper

Analogous to story_frameworks.py for creative writing.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class PaperType(Enum):
    """Types of scientific papers."""
    RESEARCH_ARTICLE = "research_article"
    SYSTEMATIC_REVIEW = "systematic_review"
    CASE_STUDY = "case_study"
    LITERATURE_REVIEW = "literature_review"
    TECHNICAL_REPORT = "technical_report"
    THESIS = "thesis"
    LAB_REPORT = "lab_report"
    CONFERENCE_PAPER = "conference_paper"
    META_ANALYSIS = "meta_analysis"
    POSITION_PAPER = "position_paper"


@dataclass
class PaperSection:
    """A single section in a scientific paper structure."""
    name: str
    description: str
    typical_position: float  # 0.0 to 1.0 in paper
    word_count_percentage: float  # Typical % of total word count
    required: bool = True
    subsections: List[str] = field(default_factory=list)
    guidance: str = ""
    common_mistakes: str = ""
    
    def __post_init__(self):
        if not self.subsections:
            self.subsections = []


class PaperFramework:
    """Base class for paper frameworks."""
    
    name: str = ""
    description: str = ""
    paper_type: PaperType = PaperType.RESEARCH_ARTICLE
    sections: List[PaperSection] = []
    typical_word_count: tuple = (3000, 8000)  # (min, max)
    citation_style: str = "APA"  # Default
    
    def get_section_for_position(self, position: float) -> PaperSection:
        """Get the appropriate section for a position in the paper."""
        for section in self.sections:
            if abs(section.typical_position - position) < 0.1:
                return section
        return self.sections[0]
    
    def generate_outline(
        self, 
        title: str, 
        research_question: str,
        methodology: str = "",
        target_words: int = 5000
    ) -> str:
        """Generate a structured outline based on this framework."""
        outline_lines = [
            f"# {title}",
            "",
            f"**Research Question:** {research_question}",
            f"**Framework:** {self.name}",
            f"**Target Word Count:** {target_words:,}",
            "",
            "---",
            "",
        ]
        
        for section in self.sections:
            word_target = int(target_words * section.word_count_percentage)
            required_mark = "📌" if section.required else "📎"
            
            outline_lines.append(f"## {required_mark} {section.name}")
            outline_lines.append(f"*Position: {section.typical_position:.0%} | ~{word_target:,} words*")
            outline_lines.append("")
            outline_lines.append(f"**Purpose:** {section.description}")
            outline_lines.append("")
            
            if section.subsections:
                outline_lines.append("**Subsections:**")
                for sub in section.subsections:
                    outline_lines.append(f"  - {sub}")
                outline_lines.append("")
            
            if section.guidance:
                outline_lines.append(f"**Guidance:** {section.guidance}")
                outline_lines.append("")
            
            outline_lines.append("---")
            outline_lines.append("")
        
        return "\n".join(outline_lines)
    
    def to_dict(self) -> Dict:
        """Convert framework to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "paper_type": self.paper_type.value,
            "sections": [
                {
                    "name": s.name,
                    "description": s.description,
                    "position": s.typical_position,
                    "word_percentage": s.word_count_percentage,
                    "required": s.required,
                    "subsections": s.subsections,
                }
                for s in self.sections
            ],
            "word_count_range": self.typical_word_count,
        }


# =============================================================================
# IMRAD - Standard Research Article
# =============================================================================

class IMRADFramework(PaperFramework):
    """
    IMRAD Structure - Most common format for scientific research articles.
    
    Introduction, Methods, Results, And Discussion
    Used by: Nature, Science, PLOS, most biomedical journals
    """
    
    name = "IMRAD"
    description = "Standard structure for empirical research papers (Introduction, Methods, Results, Discussion)"
    paper_type = PaperType.RESEARCH_ARTICLE
    typical_word_count = (3000, 8000)
    
    sections = [
        PaperSection(
            name="Title",
            description="Concise, informative title that reflects the study",
            typical_position=0.0,
            word_count_percentage=0.01,
            required=True,
            guidance="Include key variables, population, and study type. Avoid jargon.",
            common_mistakes="Too long, too vague, or including abbreviations"
        ),
        PaperSection(
            name="Abstract",
            description="Structured summary of the entire paper",
            typical_position=0.02,
            word_count_percentage=0.05,
            required=True,
            subsections=[
                "Background/Objective",
                "Methods",
                "Results",
                "Conclusions"
            ],
            guidance="Write last. Stand-alone summary. Include key findings with numbers.",
            common_mistakes="Including citations, new info not in paper, too long"
        ),
        PaperSection(
            name="Introduction",
            description="Background, rationale, and research question",
            typical_position=0.10,
            word_count_percentage=0.15,
            required=True,
            subsections=[
                "Background context",
                "Literature gap",
                "Research question/hypothesis",
                "Study objectives"
            ],
            guidance="Funnel structure: broad → specific. End with clear objectives.",
            common_mistakes="Too long, reviewing all literature, burying the research question"
        ),
        PaperSection(
            name="Methods",
            description="Detailed description of how the study was conducted",
            typical_position=0.25,
            word_count_percentage=0.25,
            required=True,
            subsections=[
                "Study design",
                "Participants/Sample",
                "Materials/Instruments",
                "Procedure",
                "Data analysis",
                "Ethical considerations"
            ],
            guidance="Enough detail for replication. Past tense. Justify choices.",
            common_mistakes="Missing details, including results, not justifying methods"
        ),
        PaperSection(
            name="Results",
            description="Objective presentation of findings",
            typical_position=0.50,
            word_count_percentage=0.25,
            required=True,
            subsections=[
                "Descriptive statistics",
                "Main findings",
                "Secondary findings",
                "Tables and figures"
            ],
            guidance="Report what was found, not what it means. Use tables/figures effectively.",
            common_mistakes="Interpreting results, duplicating table data in text, p-value hunting"
        ),
        PaperSection(
            name="Discussion",
            description="Interpretation of results in context of existing literature",
            typical_position=0.75,
            word_count_percentage=0.25,
            required=True,
            subsections=[
                "Summary of key findings",
                "Comparison with literature",
                "Implications",
                "Limitations",
                "Future directions"
            ],
            guidance="Inverse funnel: specific findings → broader implications.",
            common_mistakes="Repeating results, overclaiming, ignoring limitations"
        ),
        PaperSection(
            name="Conclusion",
            description="Brief summary of main findings and significance",
            typical_position=0.95,
            word_count_percentage=0.04,
            required=True,
            guidance="1-2 paragraphs. Answer the research question. State practical implications.",
            common_mistakes="Introducing new information, repeating abstract"
        ),
        PaperSection(
            name="References",
            description="Complete list of cited sources",
            typical_position=1.0,
            word_count_percentage=0.0,
            required=True,
            guidance="Follow journal style guide exactly. Verify all citations.",
            common_mistakes="Missing citations, wrong format, outdated sources"
        ),
    ]


# =============================================================================
# Systematic Review (PRISMA)
# =============================================================================

class SystematicReviewFramework(PaperFramework):
    """
    Systematic Review following PRISMA guidelines.
    
    Preferred Reporting Items for Systematic Reviews and Meta-Analyses
    """
    
    name = "Systematic Review (PRISMA)"
    description = "Comprehensive review of literature following PRISMA guidelines"
    paper_type = PaperType.SYSTEMATIC_REVIEW
    typical_word_count = (5000, 15000)
    
    sections = [
        PaperSection(
            name="Title",
            description="Identify as systematic review/meta-analysis",
            typical_position=0.0,
            word_count_percentage=0.01,
            required=True,
            guidance="Include 'systematic review' or 'meta-analysis' in title"
        ),
        PaperSection(
            name="Abstract (Structured)",
            description="PRISMA abstract with specific elements",
            typical_position=0.02,
            word_count_percentage=0.04,
            required=True,
            subsections=[
                "Background",
                "Methods (protocol, eligibility, sources, selection, extraction, analysis)",
                "Results (studies found, synthesized results)",
                "Conclusions",
                "Registration number"
            ]
        ),
        PaperSection(
            name="Introduction",
            description="Rationale and objectives",
            typical_position=0.08,
            word_count_percentage=0.10,
            required=True,
            subsections=[
                "Rationale for the review",
                "PICO framework",
                "Specific objectives"
            ]
        ),
        PaperSection(
            name="Methods",
            description="Review protocol and search strategy",
            typical_position=0.18,
            word_count_percentage=0.25,
            required=True,
            subsections=[
                "Protocol and registration",
                "Eligibility criteria (PICO)",
                "Information sources",
                "Search strategy (full reproducible)",
                "Selection process",
                "Data extraction",
                "Risk of bias assessment",
                "Synthesis methods"
            ],
            guidance="Must be reproducible. Register protocol on PROSPERO."
        ),
        PaperSection(
            name="Results",
            description="Study selection and findings",
            typical_position=0.45,
            word_count_percentage=0.35,
            required=True,
            subsections=[
                "PRISMA flow diagram",
                "Study characteristics table",
                "Risk of bias results",
                "Individual study results",
                "Synthesis results",
                "Heterogeneity assessment",
                "Publication bias"
            ]
        ),
        PaperSection(
            name="Discussion",
            description="Summary and interpretation",
            typical_position=0.80,
            word_count_percentage=0.20,
            required=True,
            subsections=[
                "Summary of evidence",
                "Comparison with other reviews",
                "Certainty of evidence (GRADE)",
                "Limitations",
                "Implications"
            ]
        ),
        PaperSection(
            name="Conclusion",
            description="Key findings and recommendations",
            typical_position=0.95,
            word_count_percentage=0.03,
            required=True
        ),
        PaperSection(
            name="References + Appendices",
            description="Citations and supplementary materials",
            typical_position=1.0,
            word_count_percentage=0.02,
            required=True,
            subsections=["Full search strategy", "Excluded studies list", "Additional analyses"]
        ),
    ]


# =============================================================================
# Case Study
# =============================================================================

class CaseStudyFramework(PaperFramework):
    """
    Case Study/Case Report structure.
    
    Used for describing individual cases in medicine, business, social sciences.
    """
    
    name = "Case Study"
    description = "In-depth analysis of a specific case, event, or phenomenon"
    paper_type = PaperType.CASE_STUDY
    typical_word_count = (2000, 5000)
    
    sections = [
        PaperSection(
            name="Title",
            description="Descriptive title indicating case type",
            typical_position=0.0,
            word_count_percentage=0.01,
            required=True,
            guidance="Include key feature of the case"
        ),
        PaperSection(
            name="Abstract",
            description="Brief case summary",
            typical_position=0.02,
            word_count_percentage=0.05,
            required=True,
            subsections=["Background", "Case presentation", "Key findings", "Conclusion"]
        ),
        PaperSection(
            name="Introduction",
            description="Context and significance of the case",
            typical_position=0.08,
            word_count_percentage=0.12,
            required=True,
            subsections=[
                "Background on the condition/phenomenon",
                "Why this case is notable/instructive",
                "Objectives of presenting this case"
            ]
        ),
        PaperSection(
            name="Case Presentation",
            description="Detailed description of the case",
            typical_position=0.25,
            word_count_percentage=0.35,
            required=True,
            subsections=[
                "History/Background",
                "Initial findings/Assessment",
                "Investigations/Data collected",
                "Timeline of events",
                "Interventions/Actions taken",
                "Outcomes"
            ],
            guidance="Chronological narrative. Include relevant data. Protect privacy."
        ),
        PaperSection(
            name="Discussion",
            description="Analysis and comparison with literature",
            typical_position=0.65,
            word_count_percentage=0.35,
            required=True,
            subsections=[
                "Summary of key findings",
                "Comparison with similar cases",
                "Theoretical implications",
                "Practical lessons learned",
                "Limitations of the case"
            ]
        ),
        PaperSection(
            name="Conclusion",
            description="Key takeaways and recommendations",
            typical_position=0.95,
            word_count_percentage=0.07,
            required=True,
            guidance="What can others learn from this case?"
        ),
        PaperSection(
            name="References",
            description="Cited literature",
            typical_position=1.0,
            word_count_percentage=0.0,
            required=True
        ),
    ]


# =============================================================================
# Literature Review
# =============================================================================

class LiteratureReviewFramework(PaperFramework):
    """
    Narrative/Traditional Literature Review structure.
    
    Critical analysis and synthesis of existing research on a topic.
    """
    
    name = "Literature Review"
    description = "Critical synthesis of existing research on a topic"
    paper_type = PaperType.LITERATURE_REVIEW
    typical_word_count = (3000, 10000)
    
    sections = [
        PaperSection(
            name="Title",
            description="Topic-focused title",
            typical_position=0.0,
            word_count_percentage=0.01,
            required=True
        ),
        PaperSection(
            name="Abstract",
            description="Overview of the review scope and findings",
            typical_position=0.02,
            word_count_percentage=0.04,
            required=True
        ),
        PaperSection(
            name="Introduction",
            description="Topic introduction and review objectives",
            typical_position=0.07,
            word_count_percentage=0.12,
            required=True,
            subsections=[
                "Topic background",
                "Importance of the topic",
                "Scope and objectives",
                "Organization of the review"
            ]
        ),
        PaperSection(
            name="Literature Search Methods",
            description="How literature was identified",
            typical_position=0.15,
            word_count_percentage=0.08,
            required=False,
            subsections=[
                "Databases searched",
                "Search terms",
                "Inclusion/exclusion criteria",
                "Time period"
            ]
        ),
        PaperSection(
            name="Thematic Analysis",
            description="Main body organized by themes or chronology",
            typical_position=0.40,
            word_count_percentage=0.55,
            required=True,
            subsections=[
                "Theme 1: [Topic Area]",
                "Theme 2: [Topic Area]",
                "Theme 3: [Topic Area]",
                "Emerging trends",
                "Controversies and debates"
            ],
            guidance="Organize by themes, not by source. Synthesize, don't summarize."
        ),
        PaperSection(
            name="Discussion",
            description="Critical analysis and synthesis",
            typical_position=0.80,
            word_count_percentage=0.12,
            required=True,
            subsections=[
                "Key patterns identified",
                "Gaps in the literature",
                "Quality of existing research",
                "Theoretical implications"
            ]
        ),
        PaperSection(
            name="Conclusion & Future Directions",
            description="Summary and research agenda",
            typical_position=0.93,
            word_count_percentage=0.08,
            required=True,
            subsections=[
                "Key conclusions",
                "Recommended future research",
                "Practical implications"
            ]
        ),
        PaperSection(
            name="References",
            description="All cited sources",
            typical_position=1.0,
            word_count_percentage=0.0,
            required=True
        ),
    ]


# =============================================================================
# Thesis/Dissertation
# =============================================================================

class ThesisFramework(PaperFramework):
    """
    Thesis/Dissertation structure.
    
    Extended research document for graduate degrees.
    """
    
    name = "Thesis/Dissertation"
    description = "Extended academic work for graduate degree"
    paper_type = PaperType.THESIS
    typical_word_count = (20000, 100000)
    
    sections = [
        PaperSection(
            name="Title Page",
            description="Formal title page with degree info",
            typical_position=0.0,
            word_count_percentage=0.001,
            required=True
        ),
        PaperSection(
            name="Abstract",
            description="Comprehensive summary (typically 300-500 words)",
            typical_position=0.01,
            word_count_percentage=0.01,
            required=True
        ),
        PaperSection(
            name="Acknowledgments",
            description="Thanks to supporters",
            typical_position=0.015,
            word_count_percentage=0.005,
            required=False
        ),
        PaperSection(
            name="Table of Contents",
            description="Chapter and section listing",
            typical_position=0.02,
            word_count_percentage=0.005,
            required=True
        ),
        PaperSection(
            name="Chapter 1: Introduction",
            description="Research context and objectives",
            typical_position=0.05,
            word_count_percentage=0.10,
            required=True,
            subsections=[
                "Background and context",
                "Problem statement",
                "Research questions/hypotheses",
                "Significance of the study",
                "Scope and limitations",
                "Chapter outline"
            ]
        ),
        PaperSection(
            name="Chapter 2: Literature Review",
            description="Theoretical foundation and prior research",
            typical_position=0.18,
            word_count_percentage=0.20,
            required=True,
            subsections=[
                "Theoretical framework",
                "Key concepts and definitions",
                "Review of empirical studies",
                "Identification of gaps",
                "Conceptual model"
            ]
        ),
        PaperSection(
            name="Chapter 3: Methodology",
            description="Research design and methods",
            typical_position=0.35,
            word_count_percentage=0.15,
            required=True,
            subsections=[
                "Research philosophy",
                "Research design",
                "Population and sampling",
                "Data collection methods",
                "Data analysis procedures",
                "Validity and reliability",
                "Ethical considerations"
            ]
        ),
        PaperSection(
            name="Chapter 4: Results/Findings",
            description="Presentation of data and findings",
            typical_position=0.52,
            word_count_percentage=0.20,
            required=True,
            subsections=[
                "Data preparation",
                "Descriptive results",
                "Main analyses",
                "Additional analyses",
                "Summary of findings"
            ]
        ),
        PaperSection(
            name="Chapter 5: Discussion",
            description="Interpretation and implications",
            typical_position=0.72,
            word_count_percentage=0.15,
            required=True,
            subsections=[
                "Summary of key findings",
                "Interpretation of results",
                "Comparison with literature",
                "Theoretical implications",
                "Practical implications"
            ]
        ),
        PaperSection(
            name="Chapter 6: Conclusion",
            description="Final synthesis and recommendations",
            typical_position=0.88,
            word_count_percentage=0.08,
            required=True,
            subsections=[
                "Summary of the study",
                "Key contributions",
                "Limitations",
                "Recommendations",
                "Future research directions"
            ]
        ),
        PaperSection(
            name="References",
            description="Complete bibliography",
            typical_position=0.97,
            word_count_percentage=0.05,
            required=True
        ),
        PaperSection(
            name="Appendices",
            description="Supplementary materials",
            typical_position=1.0,
            word_count_percentage=0.01,
            required=False,
            subsections=[
                "Survey instruments",
                "Interview guides",
                "Additional data tables",
                "Consent forms"
            ]
        ),
    ]


# =============================================================================
# Technical Report
# =============================================================================

class TechnicalReportFramework(PaperFramework):
    """
    Technical Report structure.
    
    Detailed documentation of technical work, findings, or proposals.
    """
    
    name = "Technical Report"
    description = "Detailed documentation of technical research or development"
    paper_type = PaperType.TECHNICAL_REPORT
    typical_word_count = (5000, 20000)
    
    sections = [
        PaperSection(
            name="Title Page",
            description="Title, authors, organization, date, report number",
            typical_position=0.0,
            word_count_percentage=0.01,
            required=True
        ),
        PaperSection(
            name="Executive Summary",
            description="Brief overview for decision-makers",
            typical_position=0.02,
            word_count_percentage=0.05,
            required=True,
            guidance="1-2 pages. Key findings and recommendations. Standalone document."
        ),
        PaperSection(
            name="Table of Contents",
            description="Navigation structure",
            typical_position=0.04,
            word_count_percentage=0.01,
            required=True
        ),
        PaperSection(
            name="Introduction",
            description="Background and objectives",
            typical_position=0.08,
            word_count_percentage=0.10,
            required=True,
            subsections=[
                "Problem statement",
                "Scope of work",
                "Objectives",
                "Report structure"
            ]
        ),
        PaperSection(
            name="Background/Literature",
            description="Technical context and prior work",
            typical_position=0.18,
            word_count_percentage=0.15,
            required=True
        ),
        PaperSection(
            name="Methodology/Approach",
            description="Technical methods and procedures",
            typical_position=0.32,
            word_count_percentage=0.20,
            required=True,
            subsections=[
                "Technical approach",
                "Tools and technologies",
                "Experimental setup",
                "Data collection"
            ]
        ),
        PaperSection(
            name="Results/Findings",
            description="Technical results and data",
            typical_position=0.52,
            word_count_percentage=0.25,
            required=True,
            subsections=[
                "Main results",
                "Performance data",
                "Analysis",
                "Figures and tables"
            ]
        ),
        PaperSection(
            name="Discussion",
            description="Interpretation and implications",
            typical_position=0.75,
            word_count_percentage=0.12,
            required=True
        ),
        PaperSection(
            name="Conclusions & Recommendations",
            description="Summary and next steps",
            typical_position=0.88,
            word_count_percentage=0.08,
            required=True,
            subsections=[
                "Key conclusions",
                "Recommendations",
                "Future work"
            ]
        ),
        PaperSection(
            name="References",
            description="Cited sources",
            typical_position=0.96,
            word_count_percentage=0.02,
            required=True
        ),
        PaperSection(
            name="Appendices",
            description="Technical details, code, data",
            typical_position=1.0,
            word_count_percentage=0.01,
            required=False
        ),
    ]


# =============================================================================
# Conference Paper
# =============================================================================

class ConferencePaperFramework(PaperFramework):
    """
    Conference Paper structure.
    
    Shorter format for academic conferences.
    """
    
    name = "Conference Paper"
    description = "Concise research paper for academic conferences"
    paper_type = PaperType.CONFERENCE_PAPER
    typical_word_count = (4000, 8000)
    
    sections = [
        PaperSection(
            name="Title",
            description="Concise, informative title",
            typical_position=0.0,
            word_count_percentage=0.01,
            required=True
        ),
        PaperSection(
            name="Abstract",
            description="Brief summary (150-300 words typically)",
            typical_position=0.02,
            word_count_percentage=0.04,
            required=True
        ),
        PaperSection(
            name="Keywords",
            description="3-6 keywords for indexing",
            typical_position=0.03,
            word_count_percentage=0.005,
            required=True
        ),
        PaperSection(
            name="Introduction",
            description="Context and contribution",
            typical_position=0.08,
            word_count_percentage=0.15,
            required=True,
            subsections=[
                "Problem context",
                "Contribution statement",
                "Paper organization"
            ],
            guidance="Clearly state novelty and contribution upfront."
        ),
        PaperSection(
            name="Related Work",
            description="Brief literature positioning",
            typical_position=0.20,
            word_count_percentage=0.15,
            required=True,
            guidance="Focus on differentiation from prior work."
        ),
        PaperSection(
            name="Approach/Methodology",
            description="Proposed method or study design",
            typical_position=0.38,
            word_count_percentage=0.25,
            required=True
        ),
        PaperSection(
            name="Evaluation/Results",
            description="Experimental validation",
            typical_position=0.62,
            word_count_percentage=0.25,
            required=True,
            subsections=[
                "Experimental setup",
                "Results",
                "Comparison"
            ]
        ),
        PaperSection(
            name="Discussion",
            description="Analysis and limitations",
            typical_position=0.82,
            word_count_percentage=0.08,
            required=False
        ),
        PaperSection(
            name="Conclusion",
            description="Summary and future work",
            typical_position=0.92,
            word_count_percentage=0.06,
            required=True
        ),
        PaperSection(
            name="References",
            description="Cited works",
            typical_position=1.0,
            word_count_percentage=0.01,
            required=True
        ),
    ]


# =============================================================================
# Registry
# =============================================================================

PAPER_FRAMEWORKS = {
    "imrad": IMRADFramework(),
    "systematic_review": SystematicReviewFramework(),
    "case_study": CaseStudyFramework(),
    "literature_review": LiteratureReviewFramework(),
    "thesis": ThesisFramework(),
    "technical_report": TechnicalReportFramework(),
    "conference_paper": ConferencePaperFramework(),
}


def get_paper_framework(framework_name: str) -> PaperFramework:
    """Get a paper framework by name."""
    return PAPER_FRAMEWORKS.get(framework_name.lower(), IMRADFramework())


def list_paper_frameworks() -> List[Dict[str, Any]]:
    """List all available paper frameworks."""
    return [
        {
            "id": key,
            "name": framework.name,
            "description": framework.description,
            "paper_type": framework.paper_type.value,
            "sections": len(framework.sections),
            "word_count_range": framework.typical_word_count,
        }
        for key, framework in PAPER_FRAMEWORKS.items()
    ]


def generate_paper_outline(
    framework_name: str,
    title: str,
    research_question: str,
    methodology: str = "",
    target_words: int = 5000
) -> str:
    """Generate a structured outline based on a paper framework."""
    framework = get_paper_framework(framework_name)
    return framework.generate_outline(title, research_question, methodology, target_words)
