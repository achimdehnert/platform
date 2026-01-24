import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from apps.bfagent.services.handlers.processing.pdf_text_extractor import PdfTextExtractorHandler
from apps.bfagent.services.handlers.exceptions import (
    HandlerExecutionError,
    HandlerTimeoutError,
    HandlerValidationError
)

class TestPdfTextExtractorHandler:
    @pytest.fixture
    def handler(self):
        return PdfTextExtractorHandler()
    
    @pytest.fixture
    def mock_pdf(self):
        mock = MagicMock()
        mock.metadata = {
            'Author': 'Test Author',
            'Title': 'Test Document',
            'CreationDate': '2023-01-01',
            'Producer': 'Test Producer'
        }
        mock.pages = [MagicMock() for _ in range(3)]
        return mock
    
    @pytest.fixture
    def context(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'%PDF-test')  # Minimal PDF content
        return {
            'pdf_file_path': str(pdf_path),
            'context_id': 'test-context'
        }
    
    @pytest.fixture
    def config(self):
        return {
            'ocr_language': 'eng',
            'page_range': 'all',
            'pdf_password': None,
            'output_format': 'plain',
            'include_headers_footers': True,
            'clean_text': True,
            'timeout_seconds': 300
        }
    
    def test_init(self, handler):
        """Test handler initialization."""
        assert handler.display_name == "PDF Text Extractor"
        assert handler.version == "1.0.0"
    
    @patch('pdfplumber.open')
    def test_execute_success(self, mock_open, handler, context, config, mock_pdf):
        """Test successful execution with text-based PDF."""
        mock_open.return_value.__enter__.return_value = mock_pdf
        mock_pdf.pages[0].extract_text.return_value = "Page 1 content"
        mock_pdf.pages[1].extract_text.return_value = "Page 2 content"
        
        result = handler.execute(context, config)
        
        assert result['success'] is True
        assert len(result['pages']) == 3
        assert isinstance(result['statistics'], dict)
        assert result['metadata']['author'] == 'Test Author'
    
    def test_execute_missing_file(self, handler, config):
        """Test execution with missing PDF file."""
        context = {
            'pdf_file_path': '/nonexistent/path.pdf',
            'context_id': 'test'
        }
        
        with pytest.raises(HandlerValidationError):
            handler.execute(context, config)
    
    @patch('pdfplumber.open')
    def test_execute_timeout(self, mock_open, handler, context, config, mock_pdf):
        """Test execution timeout."""
        config['timeout_seconds'] = 1
        mock_open.return_value.__enter__.return_value = mock_pdf
        mock_pdf.pages[0].extract_text.side_effect = lambda: time.sleep(2)
        
        with pytest.raises(HandlerTimeoutError):
            handler.execute(context, config)
    
    @patch('pdfplumber.open')
    def test_execute_password_protected(self, mock_open, handler, context, config):
        """Test handling of password-protected PDF."""
        mock_open.side_effect = Exception("Password required")
        
        with pytest.raises(HandlerExecutionError):
            handler.execute(context, config)
    
    @patch('pdfplumber.open')
    @patch('pytesseract.image_to_string')
    def test_execute_ocr_fallback(
        self,
        mock_ocr,
        mock_open,
        handler,
        context,
        config,
        mock_pdf
    ):
        """Test OCR fallback for scanned pages."""
        mock_pdf.pages[0].extract_text.return_value = ""
        mock_ocr.return_value = "OCR extracted text"
        mock_open.return_value.__enter__.return_value = mock_pdf
        
        result = handler.execute(context, config)
        
        assert result['success'] is True
        assert result['ocr_confidence'] is not None
    
    def test_page_range_validation(self, handler, context, config):
        """Test page range validation."""
        invalid_ranges = ['0-5', '5-3', 'invalid', '-1']
        
        for invalid_range in invalid_ranges:
            config['page_range'] = invalid_range
            with pytest.raises(HandlerValidationError):
                handler.execute(context, config)
    
    @patch('pdfplumber.open')
    def test_output_formats(self, mock_open, handler, context, config, mock_pdf):
        """Test different output formats."""
        mock_open.return_value.__enter__.return_value = mock_pdf
        mock_pdf.pages[0].extract_text.return_value = "Test content"
        
        for output_format in ['plain', 'markdown', 'json']:
            config['output_format'] = output_format
            result = handler.execute(context, config)
            assert result['success'] is True
            
            if output_format == 'json':
                assert isinstance(result['text_content'], dict)
            else:
                assert isinstance(result['text_content'], str)
    
    @patch('pdfplumber.open')
    def test_clean_text(self, mock_open, handler, context, config, mock_pdf):
        """Test text cleaning functionality."""
        mock_open.return_value.__enter__.return_value = mock_pdf
        mock_pdf.pages[0].extract_text.return_value = "Text  with\x00multiple    spaces"
        
        config['clean_text'] = True
        result = handler.execute(context, config)
        
        assert "  " not in result['pages'][0]
        assert "\x00" not in result['pages'][0]