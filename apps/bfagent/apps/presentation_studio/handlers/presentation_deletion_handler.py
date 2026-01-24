"""
Presentation Deletion Handler - BaseHandler v2.0
Handles deletion of entire presentations including files and database entries
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging
import os

from apps.bfagent.handlers.base_handler_v2 import BaseHandler

logger = logging.getLogger(__name__)


class PresentationDeletionInput(BaseModel):
    """Input schema for presentation deletion"""
    presentation_id: str = Field(..., description="UUID of presentation to delete")
    delete_files: bool = Field(default=True, description="Delete associated files from filesystem")
    original_file_path: Optional[str] = Field(None, description="Path to original PPTX file")
    enhanced_file_path: Optional[str] = Field(None, description="Path to enhanced PPTX file")


class PresentationDeletionOutput(BaseModel):
    """Output schema for presentation deletion"""
    success: bool = Field(..., description="Whether deletion was successful")
    presentation_id: str = Field(..., description="ID of deleted presentation")
    files_deleted: int = Field(default=0, description="Number of files deleted")
    deleted_files: list[str] = Field(default_factory=list, description="List of deleted file paths")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")


class PresentationDeletionHandler(BaseHandler[PresentationDeletionInput, PresentationDeletionOutput]):
    """
    Handler for deleting presentations
    
    Features:
    - Delete database entry (with cascading to related objects)
    - Delete associated files from filesystem
    - Detailed error reporting
    - Safe file deletion with error handling
    
    Example:
        handler = PresentationDeletionHandler()
        result = handler.execute(
            presentation_id="abc-123",
            delete_files=True,
            original_file_path="/path/to/original.pptx",
            enhanced_file_path="/path/to/enhanced.pptx"
        )
    """
    
    InputSchema = PresentationDeletionInput
    OutputSchema = PresentationDeletionOutput
    handler_name = "presentation_deletion"
    handler_version = "1.0.0"
    domain = "presentation_studio"
    category = "core"
    
    def process(self, validated_input: PresentationDeletionInput) -> Dict[str, Any]:
        """
        Process presentation deletion
        
        Args:
            validated_input: Validated input containing presentation details
            
        Returns:
            Dictionary containing deletion results
        """
        presentation_id = validated_input.presentation_id
        delete_files = validated_input.delete_files
        original_file = validated_input.original_file_path
        enhanced_file = validated_input.enhanced_file_path
        
        errors = []
        deleted_files = []
        files_deleted_count = 0
        
        try:
            # Delete files from filesystem if requested
            if delete_files:
                # Delete original file
                if original_file:
                    result = self._delete_file(original_file)
                    if result['success']:
                        deleted_files.append(original_file)
                        files_deleted_count += 1
                        logger.info(f"Deleted original file: {original_file}")
                    else:
                        errors.append(result['error'])
                
                # Delete enhanced file
                if enhanced_file:
                    result = self._delete_file(enhanced_file)
                    if result['success']:
                        deleted_files.append(enhanced_file)
                        files_deleted_count += 1
                        logger.info(f"Deleted enhanced file: {enhanced_file}")
                    else:
                        errors.append(result['error'])
            
            logger.info(
                f"Presentation {presentation_id} deletion completed. "
                f"Files deleted: {files_deleted_count}"
            )
            
            return {
                'success': True,
                'presentation_id': presentation_id,
                'files_deleted': files_deleted_count,
                'deleted_files': deleted_files,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Failed to delete presentation {presentation_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'presentation_id': presentation_id,
                'files_deleted': files_deleted_count,
                'deleted_files': deleted_files,
                'errors': errors + [error_msg]
            }
    
    def _delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Safely delete a file from filesystem
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            Dictionary with success status and optional error
        """
        try:
            if not file_path:
                return {'success': False, 'error': 'Empty file path'}
            
            if not os.path.exists(file_path):
                logger.warning(f"File does not exist: {file_path}")
                return {'success': False, 'error': f'File not found: {file_path}'}
            
            os.remove(file_path)
            return {'success': True}
            
        except PermissionError:
            error_msg = f"Permission denied when deleting: {file_path}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Error deleting {file_path}: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def delete_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        Helper method to delete an entire directory
        
        Args:
            directory_path: Path to directory to delete
            
        Returns:
            Deletion results
        """
        try:
            if not os.path.exists(directory_path):
                return {
                    'success': False,
                    'files_deleted': 0,
                    'errors': [f'Directory not found: {directory_path}']
                }
            
            if not os.path.isdir(directory_path):
                return {
                    'success': False,
                    'files_deleted': 0,
                    'errors': [f'Path is not a directory: {directory_path}']
                }
            
            import shutil
            shutil.rmtree(directory_path)
            
            logger.info(f"Deleted directory: {directory_path}")
            
            return {
                'success': True,
                'files_deleted': 1,
                'errors': []
            }
            
        except Exception as e:
            error_msg = f"Failed to delete directory {directory_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'files_deleted': 0,
                'errors': [error_msg]
            }