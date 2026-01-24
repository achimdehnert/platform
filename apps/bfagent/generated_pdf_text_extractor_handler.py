from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import time
import logging
from datetime import datetime

import pdfplumber
from PIL import Image
import pytesseract
import nltk
from nltk.tokenize import sent_tokenize
from apps.bfagent.services.handlers.base import BaseProcessingHandler
from apps.bfagent.services.handlers.exceptions import (
    HandlerExecutionError,
    HandlerTimeoutError,
    HandlerValidationError
)

logger = logging.getLogger(__name__)

class PdfTextExtractorHandler(BaseProcessingHandler):
    """
    Advanced PDF text extraction handler that processes both text-based and scanned PDFs.
    
    This handler provides comprehensive PDF text extraction capabilities including:
    - Text extraction from regular PDFs
    - OCR processing for scanned documents
    - Metadata extraction
    - Multiple output formats (plain, markdown, json)
    - Password-protected document support
    - Document structure preservation
    - Detailed extraction statistics
    
    Attributes:
        display_name (str): Display name for the handler
        description (str): Detailed description of handler functionality
        version (str): Handler version number
    """
    
    display_name = "PDF Text Extractor"
    description = "Advanced PDF text extraction handler that processes both text-based and scanned PDFs"
    version = "1.0.0"
    
    def __init__(self) -> None:
        """Initialize the handler and download required NLTK data."""
        super().__init__()
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

    def execute(self, context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the PDF text extraction process.
        
        Args:
            context (Dict[str, Any]): Execution context containing pdf_file_path and context_id
            config (Dict[str, Any]): Configuration parameters for the extraction process
            
        Returns:
            Dict[str, Any]: Extraction results containing:
                - text_content: Extracted text in specified format
                - metadata: Document metadata
                - pages: Array of page-wise text
                - statistics: Processing statistics
                - ocr_confidence: OCR confidence scores
                - success: Processing status
                
        Raises:
            HandlerExecutionError: For processing failures
            HandlerTimeoutError: When processing exceeds timeout
            HandlerValidationError: For invalid inputs
        """
        start_time = time.time()
        
        # Validate inputs
        self._validate_inputs(context)
        pdf_path = Path(context['pdf_file_path'])
        
        try:
            # Initialize results
            results = {
                'text_content': '',
                'metadata': {},
                'pages': [],
                'statistics': {},
                'ocr_confidence': None,
                'success': False
            }
            
            # Process PDF with timeout
            self._process_with_timeout(pdf_path, config, results, start_time)
            
            # Format output
            results['text_content'] = self._format_output(
                results['pages'],
                config['output_format']
            )
            
            # Calculate statistics
            results['statistics'] = {
                'total_pages': len(results['pages']),
                'processing_time': time.time() - start_time,
                'ocr_used': results['ocr_confidence'] is not None
            }
            
            results['success'] = True
            return results
            
        except TimeoutError:
            raise HandlerTimeoutError(
                f"Processing timed out after {config['timeout_seconds']} seconds"
            )
        except Exception as e:
            raise HandlerExecutionError(f"PDF processing failed: {str(e)}")

    def _validate_inputs(self, context: Dict[str, Any]) -> None:
        """Validate input parameters."""
        if 'pdf_file_path' not in context:
            raise HandlerValidationError("Missing required pdf_file_path in context")
        if 'context_id' not in context:
            raise HandlerValidationError("Missing required context_id in context")
        
        pdf_path = Path(context['pdf_file_path'])
        if not pdf_path.exists():
            raise HandlerValidationError(f"PDF file not found: {pdf_path}")

    def _process_with_timeout(
        self,
        pdf_path: Path,
        config: Dict[str, Any],
        results: Dict[str, Any],
        start_time: float
    ) -> None:
        """Process PDF with timeout control."""
        timeout = config['timeout_seconds']
        
        with pdfplumber.open(
            pdf_path,
            password=config['pdf_password']
        ) as pdf:
            # Extract metadata
            results['metadata'] = self._extract_metadata(pdf)
            
            # Process pages
            page_range = self._parse_page_range(config['page_range'], len(pdf.pages))
            ocr_scores = []
            
            for page_num in page_range:
                if time.time() - start_time > timeout:
                    raise TimeoutError()
                
                page = pdf.pages[page_num]
                text, ocr_score = self._process_page(
                    page,
                    config['ocr_language'],
                    config['include_headers_footers']
                )
                
                if config['clean_text']:
                    text = self._clean_text(text)
                
                results['pages'].append(text)
                if ocr_score is not None:
                    ocr_scores.append(ocr_score)
            
            if ocr_scores:
                results['ocr_confidence'] = sum(ocr_scores) / len(ocr_scores)

    def _extract_metadata(self, pdf: Any) -> Dict[str, Any]:
        """Extract PDF metadata."""
        metadata = pdf.metadata
        return {
            'author': metadata.get('Author'),
            'title': metadata.get('Title'),
            'creation_date': metadata.get('CreationDate'),
            'producer': metadata.get('Producer')
        }

    def _process_page(
        self,
        page: Any,
        ocr_language: str,
        include_headers_footers: bool
    ) -> Tuple[str, Optional[float]]:
        """Process a single PDF page."""
        # Try regular text extraction first
        text = page.extract_text(
            x_tolerance=3,
            y_tolerance=3
        )
        
        # If no text found, try OCR
        if not text.strip():
            return self._process_page_ocr(page, ocr_language)
        
        # Handle headers/footers
        if not include_headers_footers:
            text = self._remove_headers_footers(text)
        
        return text, None

    def _process_page_ocr(
        self,
        page: Any,
        language: str
    ) -> Tuple[str, float]:
        """Process a page using OCR."""
        image = page.to_image()
        pil_image = image.original
        
        # OCR processing
        ocr_data = pytesseract.image_to_data(
            pil_image,
            lang=language,
            output_type=pytesseract.Output.DICT
        )
        
        # Calculate confidence
        confidences = [float(conf) for conf in ocr_data['conf'] if conf != '-1']
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        text = pytesseract.image_to_string(pil_image, lang=language)
        return text, avg_confidence

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Basic cleaning
        text = text.replace('\x00', '')
        text = ' '.join(text.split())
        
        # Sentence normalization
        sentences = sent_tokenize(text)
        text = ' '.join(sentences)
        
        return text

    def _remove_headers_footers(self, text: str) -> str:
        """Remove headers and footers from text."""
        lines = text.split('\n')
        if len(lines) <= 2:
            return text
        
        # Remove first and last lines if they appear to be headers/footers
        return '\n'.join(lines[1:-1])

    def _parse_page_range(self, page_range: str, total_pages: int) -> List[int]:
        """Parse page range string into list of page numbers."""
        if page_range == 'all':
            return list(range(total_pages))
        
        try:
            if '-' in page_range:
                start, end = map(int, page_range.split('-'))
                end = min(end, total_pages)
                return list(range(start - 1, end))
            return [int(page_range) - 1]
        except ValueError:
            raise HandlerValidationError(f"Invalid page range format: {page_range}")

    def _format_output(self, pages: List[str], output_format: str) -> str:
        """Format extracted text according to specified output format."""
        if output_format == 'plain':
            return '\n\n'.join(pages)
        
        if output_format == 'markdown':
            return '\n\n'.join(f'## Page {i+1}\n\n{text}' 
                             for i, text in enumerate(pages))
        
        if output_format == 'json':
            return {
                'pages': pages,
                'total_pages': len(pages)
            }
        
        raise HandlerValidationError(f"Unsupported output format: {output_format}")