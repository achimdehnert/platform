"""
Workflow Template Library - Pre-built handler pipelines
"""
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class WorkflowTemplate:
    """Base workflow template combining handlers + prompt templates"""
    
    template_id: str
    name: str
    description: str
    input_handlers: List[Dict] = field(default_factory=list)
    processing_handlers: List[Dict] = field(default_factory=list)
    output_handlers: List[Dict] = field(default_factory=list)
    required_variables: List[str] = field(default_factory=list)
    
    def to_pipeline_config(self) -> Dict[str, Any]:
        return {
            "input": self.input_handlers,
            "processing": self.processing_handlers,
            "output": self.output_handlers[0] if self.output_handlers else {}
        }


# Chapter Generation Workflow
CHAPTER_WORKFLOW = WorkflowTemplate(
    template_id="chapter_gen",
    name="Chapter Generation",
    description="Generate complete chapter with outline",
    input_handlers=[
        {"handler": "project_fields", "config": {"fields": ["book_title", "genre"]}},
        {"handler": "chapter_data", "config": {"load_previous_chapters": True}}
    ],
    processing_handlers=[
        {"handler": "prompt_template_processor", "config": {"template_key": "chapter_outline"}},
        {"handler": "llm_processor", "config": {"temperature": 0.7, "max_tokens": 2000}}
    ],
    output_handlers=[
        {"handler": "chapter_creator", "config": {"auto_publish": False}}
    ],
    required_variables=["chapter_number", "chapter_title"]
)

# Character Development Workflow
CHARACTER_WORKFLOW = WorkflowTemplate(
    template_id="character_dev",
    name="Character Development",
    description="Generate character profile",
    processing_handlers=[
        {"handler": "prompt_template_processor", "config": {"template_key": "character_generation"}},
        {"handler": "llm_processor", "config": {"temperature": 0.8, "max_tokens": 3000}}
    ],
    required_variables=["character_name", "genre"]
)

# Workflow Registry
WORKFLOWS = {
    "chapter_gen": CHAPTER_WORKFLOW,
    "character_dev": CHARACTER_WORKFLOW
}
