"""
Chapter Creator Output Handler

Creates new chapter records from processed data.
"""

from typing import Any, Dict, List
from django.utils import timezone
import structlog

from ..base.output import BaseOutputHandler
from ..exceptions import OutputHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import ChapterCreatorConfig

logger = structlog.get_logger()


class ChapterCreatorHandler(BaseOutputHandler):
    """
    Creates new chapter records.
    
    Useful for actions that generate multiple chapters like:
    - Bulk chapter creation from outline
    - Chapter drafts generation
    - Chapter structure setup
    
    Configuration:
        target_model (str): Model name. Defaults to "BookChapters".
        fields (dict): Field mappings from processed data
        auto_number (bool): Auto-assign chapter numbers. Defaults to True.
        start_number (int): Starting chapter number. Defaults to 1.
        action_name (str): Action name for tracking
        default_status (str): Default chapter status. Defaults to "draft".
    
    Example:
        >>> handler = ChapterCreatorHandler({
        ...     "target_model": "BookChapters",
        ...     "fields": {
        ...         "title": "chapter_title",
        ...         "outline": "chapter_outline"
        ...     },
        ...     "auto_number": True
        ... })
    """
    
    handler_name = "chapter_creator"
    handler_version = "1.0.0"
    description = "Creates new chapter records from processed data"
    supports_multiple_objects = True
    supports_rollback = True
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            ChapterCreatorConfig(**self.config)
        except Exception as e:
            raise OutputHandlerException(
                message="Invalid configuration for ChapterCreatorHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    @with_logging
    @with_performance_monitoring
    def parse(self, processed_data: Any) -> List[Dict[str, Any]]:
        """
        Parse processed data into chapter format.
        
        Args:
            processed_data: Can be:
                - List of chapter dicts
                - Dict with chapters list
                - String with structured chapter data (markdown/json)
            
        Returns:
            List of chapter data dicts
        """
        if isinstance(processed_data, list):
            # Already in list format
            return processed_data
        
        if isinstance(processed_data, dict):
            # Check if dict contains chapters list
            if "chapters" in processed_data:
                return processed_data["chapters"]
            # Single chapter dict
            return [processed_data]
        
        if isinstance(processed_data, str):
            # Try to parse structured string data
            chapters = self._parse_string_data(processed_data)
            if chapters:
                return chapters
        
        raise ValueError(f"Cannot parse data of type {type(processed_data)}")
    
    def _parse_string_data(self, data: str) -> List[Dict[str, Any]]:
        """Parse string data (markdown or JSON) into chapter dicts."""
        import json
        import re
        
        # Try JSON first
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict) and "chapters" in parsed:
                return parsed["chapters"]
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Try markdown parsing
        chapters = []
        chapter_pattern = r'## Chapter (\d+):\s*(.+?)(?=\n##|\Z)'
        matches = re.finditer(chapter_pattern, data, re.DOTALL)
        
        for match in matches:
            chapter_num = int(match.group(1))
            chapter_content = match.group(2).strip()
            
            # Extract title (first line)
            lines = chapter_content.split('\n')
            title = lines[0].strip()
            
            # Extract outline/description
            outline_lines = []
            for line in lines[1:]:
                if line.strip().startswith('**') or line.strip().startswith('*'):
                    outline_lines.append(line.strip())
            
            chapters.append({
                "number": chapter_num,
                "title": title,
                "outline": '\n'.join(outline_lines)
            })
        
        return chapters
    
    def validate(self, parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate parsed chapter data."""
        errors = []
        warnings = []
        
        if not parsed_data:
            errors.append("No chapters to create")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        required_fields = self.config.get("required_fields", ["title"])
        
        for idx, chapter in enumerate(parsed_data, 1):
            # Check required fields
            for field in required_fields:
                source_field = self.config["fields"].get(field, field)
                if source_field not in chapter:
                    errors.append(f"Chapter {idx} missing required field: {source_field}")
            
            # Validate chapter number if present
            if "number" in chapter:
                if not isinstance(chapter["number"], int) or chapter["number"] < 1:
                    errors.append(f"Chapter {idx} has invalid number: {chapter['number']}")
        
        # Check for duplicate numbers
        numbers = [ch.get("number") for ch in parsed_data if "number" in ch]
        if len(numbers) != len(set(numbers)):
            warnings.append("Duplicate chapter numbers detected")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "chapter_count": len(parsed_data)
        }
    
    def create_enrichment_responses(
        self,
        parsed_data: List[Dict[str, Any]],
        project: Any,
        agent: Any
    ) -> List[Any]:
        """Create EnrichmentResponse for each chapter."""
        from ....models import EnrichmentResponse
        
        auto_number = self.config.get("auto_number", True)
        start_number = self.config.get("start_number", 1)
        
        # Get next chapter number if auto-numbering
        if auto_number:
            last_chapter = project.book_chapters.order_by("-chapter_number").first()
            next_number = (last_chapter.chapter_number + 1) if last_chapter else start_number
        
        responses = []
        for idx, chapter_data in enumerate(parsed_data):
            # Auto-assign number if needed
            if auto_number and "number" not in chapter_data:
                chapter_data["number"] = next_number + idx
            
            # Map fields
            mapped_data = {}
            for target_field, source_field in self.config["fields"].items():
                if source_field in chapter_data:
                    mapped_data[target_field] = chapter_data[source_field]
            
            # Add default fields
            if "status" not in mapped_data:
                mapped_data["status"] = self.config.get("default_status", "draft")
            
            if "chapter_number" not in mapped_data and "number" in chapter_data:
                mapped_data["chapter_number"] = chapter_data["number"]
            
            # Create enrichment response
            response = EnrichmentResponse.objects.create(
                project=project,
                agent=agent,
                action_name=self.config.get("action_name", "create_chapters"),
                response_data=mapped_data,
                field_mappings=self._build_field_mappings(mapped_data),
                status="pending",
                metadata={
                    "handler": self.handler_name,
                    "handler_version": self.handler_version,
                    "target_model": self.config.get("target_model", "BookChapters"),
                    "chapter_number": mapped_data.get("chapter_number"),
                    "auto_numbered": auto_number
                }
            )
            
            responses.append(response)
        
        return responses
    
    def _build_field_mappings(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Build field mappings for enrichment response."""
        target_model = self.config.get("target_model", "BookChapters")
        mappings = {}
        
        for field_name in data.keys():
            mappings[field_name] = f"{target_model}.{field_name}"
        
        return mappings
    
    def apply(self, enrichment_response: Any) -> Any:
        """
        Apply enrichment response - create chapter record.
        
        Args:
            enrichment_response: EnrichmentResponse to apply
            
        Returns:
            Created BookChapter instance
        """
        from django.apps import apps
        
        # Get model
        target_model = enrichment_response.metadata["target_model"]
        Model = apps.get_model("bfagent", target_model)
        
        # Create chapter
        chapter_data = enrichment_response.response_data.copy()
        chapter_data["project"] = enrichment_response.project
        
        chapter = Model.objects.create(**chapter_data)
        
        # Update response status
        enrichment_response.status = "applied"
        enrichment_response.applied_at = timezone.now()
        enrichment_response.metadata["created_chapter_id"] = chapter.id
        enrichment_response.save()
        
        return chapter
    
    def _generate_summary(self, enrichment_response: Any) -> str:
        """Generate summary."""
        chapter_num = enrichment_response.metadata.get("chapter_number", "?")
        title = enrichment_response.response_data.get("title", "Untitled")
        return f"Create Chapter {chapter_num}: {title}"
    
    def rollback(self, enrichment_response: Any) -> None:
        """Rollback changes - delete created chapter."""
        from django.apps import apps
        
        chapter_id = enrichment_response.metadata.get("created_chapter_id")
        if not chapter_id:
            raise ValueError("Cannot rollback: no created_chapter_id")
        
        # Get model and delete chapter
        target_model = enrichment_response.metadata["target_model"]
        Model = apps.get_model("bfagent", target_model)
        
        try:
            chapter = Model.objects.get(id=chapter_id)
            chapter.delete()
        except Model.DoesNotExist:
            pass  # Already deleted
        
        # Update response
        enrichment_response.status = "rejected"
        enrichment_response.save()
