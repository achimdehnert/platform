from typing import Optional, Literal
from pydantic import BaseModel, Field, validator
from apps.bfagent.services.handlers.config_models import BaseHandlerConfig

class PdfTextExtractorHandlerConfig(BaseHandlerConfig):
    """
    Configuration model for PDF Text Extractor Handler.
    
    Attributes:
        ocr_language (str): Language for OCR processing (ISO 639-2 code)
        page_range (str): Page range to process (e.g., '1-10', 'all')
        pdf_password (Optional[str]): Password for protected PDFs
        output_format (str): Output format (plain, markdown, json)
        include_headers_footers (bool): Whether to include headers and footers
        clean_text (bool): Apply text cleaning and normalization
        timeout_seconds (int): Processing timeout in seconds
    """
    
    ocr_language: str = Field(
        default="eng",
        description="Language for OCR processing (ISO 639-2 code)",
        min_length=3,
        max_length=3
    )
    
    page_range: str = Field(
        default="all",
        description="Page range to process (e.g., '1-10', 'all')"
    )
    
    pdf_password: Optional[str] = Field(
        default=None,
        description="Password for protected PDFs"
    )
    
    output_format: Literal["plain", "markdown", "json"] = Field(
        default="plain",
        description="Output format (plain, markdown, json)"
    )
    
    include_headers_footers: bool = Field(
        default=True,
        description="Whether to include headers and footers in extraction"
    )
    
    clean_text: bool = Field(
        default=True,
        description="Apply text cleaning and normalization"
    )
    
    timeout_seconds: int = Field(
        default=300,
        description="Processing timeout in seconds",
        ge=1
    )
    
    @validator('page_range')
    def validate_page_range(cls, v: str) -> str:
        """Validate page range format."""
        if v == 'all':
            return v
        
        try:
            if '-' in v:
                start, end = map(int, v.split('-'))
                if start < 1 or end < start:
                    raise ValueError()
            else:
                page = int(v)
                if page < 1:
                    raise ValueError()
        except ValueError:
            raise ValueError("Invalid page range format. Use 'all' or 'start-end' or single page number")
        
        return v

    class Config:
        schema_extra = {
            "example": {
                "ocr_language": "eng",
                "page_range": "1-10",
                "pdf_password": None,
                "output_format": "plain",
                "include_headers_footers": True,
                "clean_text": True,
                "timeout_seconds": 300
            }
        }