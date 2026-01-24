"""
Project Output Handler
Persists BookProjects data to database
"""

import logging
from typing import Any, Dict

from django.db import transaction

from apps.bfagent.handlers.base import BaseOutputHandler, OutputError
from apps.bfagent.models import BookProjects

logger = logging.getLogger(__name__)


class ProjectOutputHandler(BaseOutputHandler):
    """Handler for BookProjects persistence"""

    def __init__(self):
        super().__init__(name="project_output", version="1.0.0")

    def save(self, data: Dict[str, Any]) -> BookProjects:
        """
        Save or update BookProjects

        Args:
            data: Cleaned project data from InputHandler
                  Must contain either 'id' for update or all required fields for create

        Returns:
            BookProjects instance
        """
        project_id = data.get('id')

        try:
            if project_id:
                # Update existing project
                project = self._update_project(project_id, data)
            else:
                # Create new project
                project = self._create_project(data)

            logger.info(f"Project saved successfully: {project.id}")
            return project

        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            raise OutputError(f"Failed to save project: {e}")

    def _create_project(self, data: Dict[str, Any]) -> BookProjects:
        """Create new project"""
        with transaction.atomic():
            # Remove 'id' if present
            data.pop('id', None)

            project = BookProjects.objects.create(**data)
            logger.info(f"Created new project: {project.id} - {project.title}")
            return project

    def _update_project(self, project_id: int, data: Dict[str, Any]) -> BookProjects:
        """Update existing project"""
        try:
            project = BookProjects.objects.get(pk=project_id)
        except BookProjects.DoesNotExist:
            raise OutputError(f"Project {project_id} not found")

        with transaction.atomic():
            # Update fields
            for field, value in data.items():
                if field != 'id' and hasattr(project, field):
                    setattr(project, field, value)

            project.save()
            logger.info(f"Updated project: {project.id} - {project.title}")
            return project

    def save_enrichment_result(
        self, project_id: int, field: str, value: str, append: bool = False
    ) -> BookProjects:
        """
        Save enrichment result to a specific field

        Args:
            project_id: BookProjects ID
            field: Field name to update
            value: New value
            append: If True, append to existing value instead of replace

        Returns:
            Updated BookProjects instance
        """
        try:
            project = BookProjects.objects.get(pk=project_id)
        except BookProjects.DoesNotExist:
            raise OutputError(f"Project {project_id} not found")

        if not hasattr(project, field):
            raise OutputError(f"Project has no field: {field}")

        with transaction.atomic():
            if append and getattr(project, field):
                # Append to existing value
                existing = getattr(project, field) or ""
                new_value = f"{existing}\n\n{value}".strip()
                setattr(project, field, new_value)
            else:
                # Replace value
                setattr(project, field, value)

            project.save()
            logger.info(
                f"Saved enrichment to project {project.id}, field: {field}, "
                f"append: {append}"
            )
            return project

    def bulk_update_fields(
        self, project_id: int, fields: Dict[str, Any]
    ) -> BookProjects:
        """
        Update multiple fields at once

        Args:
            project_id: BookProjects ID
            fields: Dict of field_name: value

        Returns:
            Updated BookProjects instance
        """
        try:
            project = BookProjects.objects.get(pk=project_id)
        except BookProjects.DoesNotExist:
            raise OutputError(f"Project {project_id} not found")

        with transaction.atomic():
            for field, value in fields.items():
                if hasattr(project, field):
                    setattr(project, field, value)
                else:
                    logger.warning(f"Skipping unknown field: {field}")

            project.save()
            logger.info(
                f"Bulk updated {len(fields)} fields for project {project.id}"
            )
            return project
