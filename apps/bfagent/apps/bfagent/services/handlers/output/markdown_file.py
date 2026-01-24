"""
Markdown File Output Handler - Export to Markdown Files
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import structlog

from ..base.output import BaseOutputHandler
from ..decorators import with_logging, with_performance_monitoring
from ..exceptions import OutputHandlerException
from ..schemas import MarkdownFileConfig

logger = structlog.get_logger()


class MarkdownExporter(BaseOutputHandler):
    """
    Exports data to markdown files with frontmatter support.

    Creates markdown files with YAML frontmatter for metadata.
    Useful for exporting chapters, outlines, or other content
    to markdown format for external tools.

    Configuration (MarkdownFileConfig):
        output_dir (str): Output directory path. Required.
        filename_template (str): Template for filename. Required.
            Supports: {title}, {number}, {date}, {id}
        create_backup (bool): Backup existing files. Default: True
        add_frontmatter (bool): Add YAML frontmatter. Default: True
        overwrite (bool): Overwrite existing files. Default: False
        frontmatter_fields (list): Fields to include in frontmatter.
            Default: ["title", "author", "date"]

    Example:
        >>> handler = MarkdownExporter({
        ...     "output_dir": "/path/to/output",
        ...     "filename_template": "chapter_{number}_{title}.md",
        ...     "create_backup": True,
        ...     "add_frontmatter": True
        ... })
    """

    handler_name = "markdown_file"
    handler_version = "2.0.0"
    description = "Exports data to markdown files with frontmatter"

    supports_multiple_objects = True
    supports_rollback = True

    def validate_config(self) -> None:
        """Validate configuration using Pydantic"""
        try:
            self.validated_config = MarkdownFileConfig(**self.config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")

    @with_logging
    @with_performance_monitoring
    def parse(self, processed_data: Any) -> List[Dict[str, Any]]:
        """
        Parse processed data for markdown export.

        Args:
            processed_data: Text, dict, or list of dicts

        Returns:
            List of dicts with markdown content and metadata
        """
        try:
            if isinstance(processed_data, str):
                # Single text content
                return [
                    {
                        "content": processed_data,
                        "title": "Untitled",
                        "date": datetime.now().isoformat(),
                    }
                ]

            elif isinstance(processed_data, dict):
                # Single structured content
                return [self._normalize_content_dict(processed_data)]

            elif isinstance(processed_data, list):
                # Multiple contents
                return [self._normalize_content_dict(item) for item in processed_data]

            else:
                raise ValueError(f"Unsupported data type: {type(processed_data).__name__}")

        except Exception as e:
            raise OutputHandlerException(
                f"Failed to parse markdown data: {e}",
                handler_name=self.handler_name,
                original_error=e,
            )

    def _normalize_content_dict(self, data: Any) -> Dict[str, Any]:
        """Normalize content dict to standard format"""
        if isinstance(data, str):
            return {"content": data, "title": "Untitled", "date": datetime.now().isoformat()}

        normalized = {
            "content": data.get("content", data.get("text", "")),
            "title": data.get("title", "Untitled"),
            "date": data.get("date", datetime.now().isoformat()),
        }

        # Preserve additional metadata
        for key, value in data.items():
            if key not in normalized:
                normalized[key] = value

        return normalized

    def validate(self, parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate parsed markdown data.

        Args:
            parsed_data: List of content dicts

        Returns:
            Validation results
        """
        errors = []
        warnings = []

        if not parsed_data:
            errors.append("No content to export")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Validate output directory
        output_dir = Path(self.validated_config.output_dir)

        if output_dir.exists() and not output_dir.is_dir():
            errors.append(f"Output path exists but is not a directory: {output_dir}")

        # Check content
        for idx, item in enumerate(parsed_data, 1):
            if not item.get("content"):
                warnings.append(f"Item {idx} has no content")

            if len(item.get("content", "")) < 10:
                warnings.append(f"Item {idx} has very short content")

        # Check for filename conflicts
        if not self.validated_config.overwrite:
            conflicts = self._check_filename_conflicts(parsed_data)
            if conflicts:
                warnings.append(f"Filename conflicts detected: {len(conflicts)} files")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "file_count": len(parsed_data),
        }

    def _check_filename_conflicts(self, parsed_data: List[Dict[str, Any]]) -> List[str]:
        """Check for filename conflicts with existing files"""
        output_dir = Path(self.validated_config.output_dir)
        conflicts = []

        if not output_dir.exists():
            return conflicts

        for item in parsed_data:
            filename = self._generate_filename(item)
            file_path = output_dir / filename

            if file_path.exists():
                conflicts.append(str(file_path))

        return conflicts

    @with_logging
    def create_enrichment_responses(
        self, parsed_data: List[Dict[str, Any]], project: Any, agent: Any
    ) -> List[Any]:
        """
        Create EnrichmentResponse for each file.

        Args:
            parsed_data: List of validated content dicts
            project: BookProjects instance
            agent: Agents instance

        Returns:
            List of EnrichmentResponse objects
        """
        from apps.bfagent.models import EnrichmentResponse

        responses = []

        try:
            for idx, content_data in enumerate(parsed_data):
                filename = self._generate_filename(content_data)

                response = EnrichmentResponse.objects.create(
                    project=project,
                    agent=agent,
                    action_name=f"export_markdown_{idx}",
                    response_data=content_data,
                    field_mappings={"content": f"file:{filename}"},
                    status="pending",
                    metadata={
                        "handler": self.handler_name,
                        "handler_version": self.handler_version,
                        "filename": filename,
                        "output_dir": self.validated_config.output_dir,
                        "batch_index": idx,
                        "batch_total": len(parsed_data),
                    },
                )

                responses.append(response)

            self.logger.info("enrichment_responses_created", response_count=len(responses))

            return responses

        except Exception as e:
            raise OutputHandlerException(
                f"Failed to create enrichment responses: {e}",
                handler_name=self.handler_name,
                original_error=e,
            )

    def _generate_filename(self, content_data: Dict[str, Any]) -> str:
        """Generate filename from template"""
        template = self.validated_config.filename_template

        # Sanitize values for filename
        def sanitize(value: str) -> str:
            # Remove invalid filename characters
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                value = value.replace(char, "_")
            return value.strip()

        # Replace placeholders
        filename = template

        replacements = {
            "{title}": sanitize(content_data.get("title", "untitled")),
            "{number}": str(content_data.get("number", content_data.get("chapter_number", 1))),
            "{date}": datetime.now().strftime("%Y%m%d"),
            "{id}": str(content_data.get("id", "")),
        }

        for placeholder, value in replacements.items():
            filename = filename.replace(placeholder, value)

        # Ensure .md extension
        if not filename.endswith(".md"):
            filename += ".md"

        return filename

    @with_logging
    @with_performance_monitoring
    def apply(self, enrichment_response: Any) -> Any:
        """
        Apply enrichment response - write markdown file.

        Args:
            enrichment_response: EnrichmentResponse to apply

        Returns:
            Path to created file
        """
        filename = enrichment_response.metadata["filename"]
        output_dir = Path(enrichment_response.metadata["output_dir"])
        file_path = output_dir / filename

        self.logger.info(
            "applying_markdown_export", enrichment_id=enrichment_response.id, filename=filename
        )

        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Backup existing file
            if file_path.exists() and self.validated_config.create_backup:
                backup_path = self._create_backup(file_path)
                self.logger.info("file_backed_up", backup_path=str(backup_path))

            # Check overwrite
            if file_path.exists() and not self.validated_config.overwrite:
                raise OutputHandlerException(
                    f"File exists and overwrite=False: {file_path}",
                    handler_name=self.handler_name,
                    context={"file_path": str(file_path)},
                )

            # Generate markdown content
            content_data = enrichment_response.response_data
            markdown_content = self._generate_markdown(content_data)

            # Write file
            file_path.write_text(markdown_content, encoding="utf-8")

            # Update response
            enrichment_response.status = "applied"
            enrichment_response.applied_at = datetime.now()
            enrichment_response.metadata["file_path"] = str(file_path)
            enrichment_response.metadata["file_size"] = len(markdown_content)
            enrichment_response.save()

            self.logger.info(
                "markdown_file_created", file_path=str(file_path), size_bytes=len(markdown_content)
            )

            return file_path

        except Exception as e:
            raise OutputHandlerException(
                f"Failed to create markdown file: {e}",
                handler_name=self.handler_name,
                context={"filename": filename},
                original_error=e,
            )

    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of existing file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _generate_markdown(self, content_data: Dict[str, Any]) -> str:
        """Generate markdown content with optional frontmatter"""
        lines = []

        # Add frontmatter
        if self.validated_config.add_frontmatter:
            lines.append("---")

            for field in self.validated_config.frontmatter_fields:
                if field in content_data:
                    value = content_data[field]
                    # Quote strings with special chars
                    if isinstance(value, str) and any(c in value for c in [":", "#", "|"]):
                        value = f'"{value}"'
                    lines.append(f"{field}: {value}")

            lines.append("---")
            lines.append("")

        # Add content
        content = content_data.get("content", "")
        lines.append(content)

        return "\n".join(lines)

    def _generate_summary(self, enrichment_response: Any) -> str:
        """Generate user-friendly summary"""
        filename = enrichment_response.metadata["filename"]
        return f"Export to: {filename}"

    @with_logging
    def rollback(self, enrichment_response: Any) -> None:
        """
        Rollback - delete created file.

        Args:
            enrichment_response: EnrichmentResponse to rollback
        """
        file_path_str = enrichment_response.metadata.get("file_path")

        if not file_path_str:
            raise OutputHandlerException(
                "Cannot rollback: no file_path in metadata",
                handler_name=self.handler_name,
                context={"enrichment_id": enrichment_response.id},
            )

        file_path = Path(file_path_str)

        self.logger.info(
            "rolling_back_markdown_file",
            enrichment_id=enrichment_response.id,
            file_path=str(file_path),
        )

        try:
            if file_path.exists():
                file_path.unlink()
                self.logger.info("file_deleted", file_path=str(file_path))
            else:
                self.logger.warning("file_already_deleted", file_path=str(file_path))

            # Update response
            enrichment_response.status = "rejected"
            enrichment_response.metadata["rolled_back_at"] = datetime.now().isoformat()
            enrichment_response.save()

        except Exception as e:
            raise OutputHandlerException(
                f"Rollback failed: {e}",
                handler_name=self.handler_name,
                context={"file_path": str(file_path)},
                original_error=e,
            )
