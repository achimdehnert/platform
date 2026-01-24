# PDF Text Extractor Handler

## Purpose
The PDF Text Extractor Handler is an advanced document processing component that extracts text content from both text-based and scanned PDF documents. It provides comprehensive features including OCR support, metadata extraction, and multiple output formats while maintaining document structure and providing detailed processing statistics.

## Features
- Text extraction from regular PDFs
- OCR processing for scanned documents
- Multiple output formats (plain, markdown, JSON)
- Password-protected document support
- Document structure preservation
- Detailed extraction statistics
- Text cleaning and normalization
- Headers and footers handling
- Configurable timeout protection

## Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ocr_language | string | "eng" | Language for OCR processing (ISO 639-2 code) |
| page_range | string | "all" | Page range to process (e.g., '1-10', 'all') |
| pdf_password | string | null | Password for protected PDFs |
| output_format | string | "plain" | Output format (plain, markdown, json) |
| include_headers_footers | boolean | true | Whether to include headers and footers |
| clean_text | boolean | true | Apply text cleaning and normalization |
| timeout_seconds | integer | 300 | Processing timeout in seconds |

## Input Requirements
- `pdf_file_path`: Path to the PDF file
- `context_id`: Unique identifier for the processing context

## Output Format
```json
{
    "text_content": "Extracted text in specified format",
    "metadata": {
        "author": "Document author",
        "title": "Document title",
        "creation_date": "Creation date",
        "producer": "PDF producer"
    },
    "pages": ["Page 1 text", "Page 2 text", ...],
    "statistics": {
        "total_pages": 10,
        "processing_time": 25.5,
        "ocr_used": true
    },
    "ocr_confidence": 95.5,
    "success": true
}
```

## Error Handling
The handler provides comprehensive error handling for various scenarios:
- Corrupted PDF files
- Invalid passwords for protected documents
- OCR processing failures
- Memory constraints
- Timeout conditions
- Unsupported PDF features
- Missing or inaccessible files

## Dependencies
- pdfplumber: PDF text extraction
- pytesseract: OCR processing
- Pillow: Image processing
- nltk: Text processing and cleaning

## Best Practices
- Always specify appropriate timeout values for large documents
- Use specific page ranges for large documents when full processing isn't needed
- Consider memory usage when processing large files
- Test password-protected documents with correct credentials
- Monitor OCR confidence scores for quality assurance

## Performance Considerations
- OCR processing is significantly slower than regular text extraction
- Large documents may require increased timeout values
- Memory usage scales with document size and complexity
- Consider using page ranges for partial processing of large documents

## Security Notes
- Passwords are handled securely and not logged
- Temporary files are properly cleaned up
- Input validation prevents path traversal attacks
- Resource limits prevent denial of service scenarios