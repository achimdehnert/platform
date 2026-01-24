"""
Test Compatibility Wrappers
============================

Verify that compatibility wrappers maintain backward compatibility
with existing code patterns.

Author: BF Agent Framework
Date: 2025-11-03
"""

from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
import pytest

from apps.bfagent.handlers.compatibility_wrappers import (
    regenerate_chapter_with_feedback,
    auto_illustrate_chapter_sync,
    auto_illustrate_chapter_task,
    is_using_v2_handlers,
    get_handler_version,
)


class TestRegenerateChapterWrapper(TestCase):
    """Test regenerate_chapter_with_feedback wrapper"""
    
    @patch('apps.bfagent.handlers.compatibility_wrappers.ChapterRegenerateHandlerV2')
    def test_wrapper_calls_new_handler(self, mock_handler_class):
        """Test wrapper properly calls new handler"""
        # Setup mock
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.return_value = {
            'success': True,
            'data': {
                'chapter_id': 5,
                'content': 'New content',
                'word_count': 100,
                'feedback_integrated': 2,
            },
            'message': 'Success'
        }
        
        # Setup legacy input
        project = Mock()
        project.id = 1
        context = {
            'chapter_id': 5,
            'parameters': {
                'style_notes': 'More suspenseful',
                'include_feedback_types': ['suggestion']
            }
        }
        
        # Execute wrapper
        result = regenerate_chapter_with_feedback(context, project)
        
        # Verify handler was called
        mock_handler_class.assert_called_once()
        mock_handler.execute.assert_called_once()
        
        # Verify call parameters
        call_args = mock_handler.execute.call_args[0][0]
        assert call_args['project_id'] == 1
        assert call_args['chapter_id'] == 5
        assert call_args['style_notes'] == 'More suspenseful'
        assert call_args['include_feedback_types'] == ['suggestion']
        
        # Verify legacy result format
        assert result['success'] is True
        assert result['action'] == 'regenerate_chapter_with_feedback'
        assert 'data' in result
        assert result['data']['chapter_id'] == 5
        assert result['data']['content'] == 'New content'
    
    @patch('apps.bfagent.handlers.compatibility_wrappers.ChapterRegenerateHandlerV2')
    def test_wrapper_handles_missing_chapter_id(self, mock_handler_class):
        """Test wrapper handles missing chapter_id"""
        project = Mock()
        context = {'parameters': {}}
        
        result = regenerate_chapter_with_feedback(context, project)
        
        assert result['success'] is False
        assert 'chapter_id is required' in result['message']
    
    @patch('apps.bfagent.handlers.compatibility_wrappers.ChapterRegenerateHandlerV2')
    def test_wrapper_handles_errors(self, mock_handler_class):
        """Test wrapper handles handler errors"""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.return_value = {
            'success': False,
            'message': 'Chapter not found',
            'error_type': 'processing_error'
        }
        
        project = Mock()
        project.id = 1
        context = {
            'chapter_id': 999,
            'parameters': {}
        }
        
        result = regenerate_chapter_with_feedback(context, project)
        
        assert result['success'] is False
        assert result['message'] == 'Chapter not found'
        assert result['error_type'] == 'processing_error'


class TestAutoIllustrateWrapper(TestCase):
    """Test auto_illustrate_chapter_sync wrapper"""
    
    @patch('apps.bfagent.handlers.compatibility_wrappers.ChapterAutoIllustrateHandlerV2')
    def test_wrapper_calls_new_handler(self, mock_handler_class):
        """Test wrapper properly calls new handler"""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.return_value = {
            'success': True,
            'chapter_id': 5,
            'images_generated': 3,
            'total_cost_usd': 0.15,
            'duration_seconds': 2.5,
            'mock_mode': True,
            'generated_images': [
                {'paragraph_index': 0, 'illustration_type': 'scene'},
                {'paragraph_index': 5, 'illustration_type': 'character'},
                {'paragraph_index': 10, 'illustration_type': 'scene'},
            ]
        }
        
        # Execute wrapper
        result = auto_illustrate_chapter_sync(
            chapter_id=5,
            chapter_text="Once upon a time...",
            max_illustrations=3,
            provider='mock'
        )
        
        # Verify handler was called
        mock_handler_class.assert_called_once()
        mock_handler.execute.assert_called_once()
        
        # Verify call parameters
        call_args = mock_handler.execute.call_args[0][0]
        assert call_args['chapter_id'] == 5
        assert call_args['max_illustrations'] == 3
        assert call_args['provider'] == 'mock'
        
        # Verify legacy result format
        assert result['status'] == 'success'
        assert result['chapter_id'] == 5
        assert result['images_generated'] == 3
        assert 'positions' in result
        assert len(result['positions']) == 3
    
    @patch('apps.bfagent.handlers.compatibility_wrappers.ChapterAutoIllustrateHandlerV2')
    def test_wrapper_handles_errors(self, mock_handler_class):
        """Test wrapper handles handler errors"""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.return_value = {
            'success': False,
            'message': 'Chapter not found',
            'error_type': 'processing_error'
        }
        
        result = auto_illustrate_chapter_sync(
            chapter_id=999,
            chapter_text="",
            max_illustrations=3,
            provider='mock'
        )
        
        assert result['status'] == 'error'
        assert result['error'] == 'Chapter not found'


class TestCeleryTaskWrapper(TestCase):
    """Test auto_illustrate_chapter_task wrapper"""
    
    @patch('apps.bfagent.models.BookChapters')
    @patch('apps.bfagent.handlers.compatibility_wrappers.ChapterAutoIllustrateHandlerV2')
    def test_task_wrapper_verifies_access(self, mock_handler_class, mock_chapters):
        """Test task wrapper verifies user access"""
        # Setup mock chapter
        mock_chapter = Mock()
        mock_chapter.id = 5
        mock_chapters.objects.select_related.return_value.get.return_value = mock_chapter
        
        # Setup mock handler
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.return_value = {
            'success': True,
            'chapter_id': 5,
            'images_generated': 2,
            'total_cost_usd': 0.10,
            'duration_seconds': 1.5,
            'generated_images': [
                {'paragraph_index': 0, 'illustration_type': 'scene'},
                {'paragraph_index': 5, 'illustration_type': 'character'},
            ]
        }
        
        # Execute wrapper
        result = auto_illustrate_chapter_task(
            chapter_id=5,
            user_id=1,
            max_illustrations=2,
            provider='mock'
        )
        
        # Verify access check
        mock_chapters.objects.select_related.assert_called_once_with('project__user')
        
        # Verify result
        assert result['status'] == 'SUCCESS'
        assert result['chapter_id'] == 5
        assert result['images_generated'] == 2
    
    @patch('apps.bfagent.models.BookChapters')
    def test_task_wrapper_handles_access_denied(self, mock_chapters):
        """Test task wrapper handles access denied"""
        from apps.bfagent.models import BookChapters as ChapterModel
        
        # Simulate chapter not found
        mock_chapters.DoesNotExist = ChapterModel.DoesNotExist
        mock_chapters.objects.select_related.return_value.get.side_effect = ChapterModel.DoesNotExist
        
        result = auto_illustrate_chapter_task(
            chapter_id=999,
            user_id=1,
            max_illustrations=2
        )
        
        assert result['status'] == 'FAILURE'
        assert 'error' in result  # Just verify error field exists


class TestHelperFunctions(TestCase):
    """Test helper functions"""
    
    def test_is_using_v2_handlers(self):
        """Test V2 handler detection"""
        # Should default to True
        result = is_using_v2_handlers()
        assert result is True
    
    def test_get_handler_version(self):
        """Test version retrieval"""
        version = get_handler_version()
        assert version == '2.0.0'


# ==================== INTEGRATION TESTS ====================

class TestEndToEndCompatibility(TestCase):
    """Test complete integration scenarios"""
    
    @patch('apps.bfagent.handlers.compatibility_wrappers.ChapterRegenerateHandlerV2')
    def test_complete_regeneration_flow(self, mock_handler_class):
        """Test complete chapter regeneration flow with wrapper"""
        # Setup
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.return_value = {
            'success': True,
            'data': {
                'chapter_id': 10,
                'content': 'Regenerated chapter content with feedback integrated',
                'word_count': 500,
                'feedback_integrated': 3,
                'saved_path': '/path/to/chapter_10.md',
                'metadata': {
                    'feedback_types': ['suggestion', 'concern'],
                    'conflicts_detected': 0
                }
            },
            'message': 'Chapter regenerated successfully'
        }
        
        # Execute like old code would
        project = Mock()
        project.id = 2
        context = {
            'chapter_id': 10,
            'agent_id': 'agent_123',
            'parameters': {
                'style_notes': 'Make it more dramatic',
                'include_feedback_types': ['suggestion', 'concern'],
                'target_word_count': 500,
                'detect_conflicts': True
            }
        }
        
        result = regenerate_chapter_with_feedback(context, project)
        
        # Verify old code expectations
        assert result['success'] is True
        assert result['action'] == 'regenerate_chapter_with_feedback'
        assert result['data']['chapter_id'] == 10
        assert result['data']['content'] == 'Regenerated chapter content with feedback integrated'
        assert result['data']['word_count'] == 500
        assert result['data']['feedback_integrated'] == 3
        assert 'saved_path' in result['data']
        assert 'metadata' in result['data']
