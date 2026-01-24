"""
Book Export Service
Exports manuscripts to PDF, EPUB, and other formats
"""

import io
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BookExporter:
    """
    Service for exporting books to various formats.
    
    Supported formats:
    - PDF (via reportlab or weasyprint)
    - EPUB (via ebooklib)
    - Markdown
    - HTML
    - Plain Text
    """
    
    def __init__(self, project):
        """Initialize with a BookProjects instance"""
        self.project = project
        self.chapters = []
        self.metadata = {}
        self._load_data()
    
    def _load_data(self):
        """Load project data and chapters"""
        from apps.bfagent.models import BookChapters
        
        self.chapters = list(
            BookChapters.objects.filter(project=self.project)
            .order_by('chapter_number')
        )
        
        # Try to load publishing metadata
        self.publishing_metadata = None
        self.front_matter = []
        self.back_matter = []
        self.cover = None
        
        try:
            from apps.writing_hub.models_publishing import (
                PublishingMetadata, FrontMatter, BackMatter, BookCover
            )
            self.publishing_metadata = PublishingMetadata.objects.filter(
                project=self.project
            ).first()
            self.front_matter = list(FrontMatter.objects.filter(
                project=self.project, is_active=True
            ).order_by('sort_order'))
            self.back_matter = list(BackMatter.objects.filter(
                project=self.project, is_active=True
            ).order_by('sort_order'))
            self.cover = BookCover.objects.filter(
                project=self.project, is_primary=True, cover_type='ebook'
            ).first()
        except Exception:
            pass  # Publishing models not available
        
        # Build metadata from project and publishing info
        pm = self.publishing_metadata
        self.metadata = {
            'title': self.project.title or 'Untitled',
            'author': getattr(self.project, 'author', 'Unknown Author'),
            'genre': self.project.genre or '',
            'description': self.project.description or '',
            'language': pm.language if pm else 'de',
            'total_words': sum(ch.word_count or 0 for ch in self.chapters),
            'chapter_count': len(self.chapters),
            'isbn': pm.isbn if pm else '',
            'publisher': pm.publisher_name if pm else 'Selbstverlag',
            'copyright_year': pm.copyright_year if pm else '',
            'copyright_holder': pm.copyright_holder if pm else '',
        }
    
    def get_full_manuscript(self, include_outline: bool = False) -> str:
        """Get the full manuscript as formatted text"""
        parts = []
        include_images = getattr(self, '_include_images', True)
        include_figure_index = getattr(self, '_include_figure_index', False)
        
        # Title page
        parts.append(f"# {self.metadata['title']}\n")
        if self.metadata.get('author'):
            parts.append(f"*von {self.metadata['author']}*\n")
        if self.metadata.get('description'):
            parts.append(f"\n{self.metadata['description']}\n")
        parts.append("\n---\n\n")
        
        # Table of contents
        parts.append("## Inhaltsverzeichnis\n\n")
        for ch in self.chapters:
            parts.append(f"- Kapitel {ch.chapter_number}: {ch.title}\n")
        parts.append("\n---\n\n")
        
        # Chapters
        for ch in self.chapters:
            parts.append(f"## Kapitel {ch.chapter_number}: {ch.title}\n\n")
            
            if include_outline and ch.outline:
                parts.append(f"*Outline: {ch.outline}*\n\n")
            
            content = ch.content or '[Kein Inhalt]'
            
            # Optionally strip images from content
            if not include_images:
                content = re.sub(r'!\[.*?\]\(.*?\)\n?\*.*?\*\n?', '', content)
                content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
            
            parts.append(f"{content}\n\n")
            parts.append("---\n\n")
        
        # Add figure index at the end if requested
        if include_figure_index:
            figure_index = self._get_figure_index()
            if figure_index:
                parts.append(figure_index)
        
        return "".join(parts)
    
    def export_markdown(self, include_outline: bool = False) -> bytes:
        """Export as Markdown"""
        content = self.get_full_manuscript(include_outline)
        return content.encode('utf-8')
    
    def export_html(self, include_outline: bool = False) -> bytes:
        """Export as HTML with styling"""
        import markdown
        
        md_content = self.get_full_manuscript(include_outline)
        html_body = markdown.markdown(md_content, extensions=['extra'])
        
        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.metadata['title']}</title>
    <style>
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.8;
            color: #333;
            background: #fafafa;
        }}
        h1 {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            color: #1a1a1a;
        }}
        h2 {{
            font-size: 1.5rem;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #ddd;
            color: #2a2a2a;
        }}
        p {{
            text-align: justify;
            margin-bottom: 1rem;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 2rem 0;
        }}
        em {{
            color: #666;
        }}
        .toc {{
            background: #f5f5f5;
            padding: 1rem 2rem;
            border-radius: 8px;
            margin: 2rem 0;
        }}
        .toc ul {{
            list-style: none;
            padding-left: 0;
        }}
        .toc li {{
            padding: 0.3rem 0;
        }}
        figure {{
            margin: 2rem 0;
            text-align: center;
        }}
        figure img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        figcaption {{
            font-size: 0.9rem;
            color: #666;
            font-style: italic;
            margin-top: 0.5rem;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        @media print {{
            body {{
                max-width: none;
                padding: 1cm;
            }}
            h2 {{
                page-break-before: always;
            }}
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""
        return html.encode('utf-8')
    
    def export_txt(self, include_outline: bool = False) -> bytes:
        """Export as plain text"""
        md_content = self.get_full_manuscript(include_outline)
        
        # Convert image markdown to plain text caption
        # ![Abb. 1: Caption](url) -> [Abbildung 1: Caption]
        txt = re.sub(r'!\[(Abb\. [^]]+)\]\([^)]+\)', r'[\1]', md_content)
        
        # Remove remaining markdown formatting
        txt = re.sub(r'[#*_`]', '', txt)
        txt = re.sub(r'\n{3,}', '\n\n', txt)
        return txt.encode('utf-8')
    
    def export_pdf(self, include_outline: bool = False) -> bytes:
        """Export as PDF using reportlab"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        except ImportError:
            logger.warning("reportlab not installed, using HTML-to-PDF fallback")
            return self._pdf_fallback(include_outline)
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'BookTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        
        chapter_style = ParagraphStyle(
            'ChapterTitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=30,
            spaceAfter=20,
        )
        
        body_style = ParagraphStyle(
            'BookBody',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceBefore=6,
            spaceAfter=6,
            leading=16,
        )
        
        story = []
        
        # Title page
        story.append(Spacer(1, 5*cm))
        story.append(Paragraph(self.metadata['title'], title_style))
        if self.metadata.get('author'):
            author_style = ParagraphStyle('Author', parent=styles['Normal'], alignment=TA_CENTER, fontSize=14)
            story.append(Paragraph(f"von {self.metadata['author']}", author_style))
        story.append(PageBreak())
        
        # Table of contents
        story.append(Paragraph("Inhaltsverzeichnis", chapter_style))
        for ch in self.chapters:
            toc_item = f"Kapitel {ch.chapter_number}: {ch.title}"
            story.append(Paragraph(toc_item, body_style))
        story.append(PageBreak())
        
        # Caption style for images
        caption_style = ParagraphStyle(
            'Caption',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor='gray',
            spaceBefore=6,
            spaceAfter=12,
        )
        
        include_images = getattr(self, '_include_images', True)
        
        # Chapters
        for ch in self.chapters:
            story.append(Paragraph(f"Kapitel {ch.chapter_number}: {ch.title}", chapter_style))
            
            if include_outline and ch.outline:
                outline_style = ParagraphStyle('Outline', parent=body_style, textColor='gray', fontSize=10)
                story.append(Paragraph(f"<i>{ch.outline}</i>", outline_style))
                story.append(Spacer(1, 12))
            
            content = ch.content or '[Kein Inhalt]'
            # Split into paragraphs
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Check for image markdown: ![caption](url)
                    img_match = re.search(r'!\[(.*?)\]\((.*?)\)', para)
                    if img_match and include_images:
                        caption = img_match.group(1)
                        img_url = img_match.group(2)
                        logger.info(f"[PDF Export] Found image: {img_url} with caption: {caption}")
                        # Try to add image to PDF
                        img_added = self._add_image_to_pdf(story, img_url, caption, caption_style)
                        if not img_added:
                            logger.warning(f"[PDF Export] Failed to add image: {img_url}")
                            # Fallback: show caption as text
                            story.append(Paragraph(f"<i>[Bild: {caption}]</i>", caption_style))
                        else:
                            logger.info(f"[PDF Export] Successfully added image: {img_url}")
                    elif para.startswith('*') and para.endswith('*') and 'Abb.' in para:
                        # This is a caption line, skip if image was already added with caption
                        continue
                    else:
                        # Escape HTML special chars
                        para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(para, body_style))
            
            story.append(PageBreak())
        
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    
    def _add_image_to_pdf(self, story: List, img_url: str, caption: str, caption_style) -> bool:
        """Download and add an image to the PDF story. Returns True if successful."""
        try:
            from reportlab.platypus import Image, Paragraph, Spacer
            from reportlab.lib.units import cm
            import requests
            from urllib.parse import urlparse
            import os
            from django.conf import settings
            
            img_data = None
            logger.info(f"[PDF Export] Processing image URL: {img_url}")
            
            # Check if it's a local file URL or external URL
            is_local = (
                img_url.startswith('/media/') or 
                img_url.startswith('media/') or
                img_url.startswith('/chapter_illustrations/') or
                img_url.startswith('/illustrations/') or
                'chapter_illustrations/' in img_url or
                'illustrations/' in img_url
            )
            
            if is_local:
                # Local file - read from disk
                # Remove leading slash and 'media/' prefix
                local_path = img_url.lstrip('/')
                if local_path.startswith('media/'):
                    local_path = local_path[6:]  # Remove 'media/'
                
                # Try multiple possible paths
                possible_paths = [
                    os.path.join(settings.MEDIA_ROOT, local_path),
                    os.path.join(settings.BASE_DIR, 'media', local_path),
                    os.path.join(settings.BASE_DIR, img_url.lstrip('/')),
                    # Direct path if already absolute-like
                    os.path.join(settings.MEDIA_ROOT, 'chapter_illustrations', os.path.basename(img_url)),
                    # ComfyUI saves to illustrations/ folder
                    os.path.join(settings.MEDIA_ROOT, 'illustrations', os.path.basename(img_url)),
                ]
                
                for full_path in possible_paths:
                    logger.debug(f"[PDF Export] Trying image path: {full_path}")
                    if os.path.exists(full_path):
                        logger.info(f"[PDF Export] Found image at: {full_path}")
                        img_data = io.BytesIO(open(full_path, 'rb').read())
                        break
                
                if not img_data:
                    logger.warning(f"[PDF Export] Image not found in any path for: {img_url}")
            elif img_url.startswith('http://') or img_url.startswith('https://'):
                # External URL - download
                try:
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        img_data = io.BytesIO(response.content)
                except Exception as e:
                    logger.warning(f"Failed to download image {img_url}: {e}")
            
            if img_data:
                # Add image to story with max width
                img = Image(img_data)
                # Scale to fit page width (max 14cm)
                max_width = 14 * cm
                max_height = 10 * cm
                aspect = img.imageWidth / img.imageHeight if img.imageHeight else 1
                
                if img.imageWidth > max_width:
                    img.drawWidth = max_width
                    img.drawHeight = max_width / aspect
                else:
                    img.drawWidth = img.imageWidth
                    img.drawHeight = img.imageHeight
                
                if img.drawHeight > max_height:
                    img.drawHeight = max_height
                    img.drawWidth = max_height * aspect
                
                story.append(Spacer(1, 12))
                story.append(img)
                story.append(Paragraph(f"<i>{caption}</i>", caption_style))
                return True
                
        except Exception as e:
            logger.warning(f"Failed to add image to PDF: {e}")
        
        return False
    
    def _download_image(self, img_url: str) -> tuple:
        """Download image from URL. Returns (image_data, image_type) or (None, None)."""
        import requests
        import os
        from django.conf import settings
        
        try:
            img_data = None
            img_type = 'png'  # Default type
            logger.info(f"[Download Image] Processing: {img_url}")
            
            # Check if it's a local file URL or external URL
            is_local = (
                img_url.startswith('/media/') or 
                img_url.startswith('media/') or
                img_url.startswith('/chapter_illustrations/') or
                img_url.startswith('/illustrations/') or
                'chapter_illustrations/' in img_url or
                'illustrations/' in img_url
            )
            
            if is_local:
                # Local file - read from disk
                local_path = img_url.lstrip('/')
                if local_path.startswith('media/'):
                    local_path = local_path[6:]  # Remove 'media/'
                
                # Try multiple possible paths
                possible_paths = [
                    os.path.join(settings.MEDIA_ROOT, local_path),
                    os.path.join(settings.BASE_DIR, 'media', local_path),
                    os.path.join(settings.BASE_DIR, img_url.lstrip('/')),
                    os.path.join(settings.MEDIA_ROOT, 'chapter_illustrations', os.path.basename(img_url)),
                    # ComfyUI saves to illustrations/ folder
                    os.path.join(settings.MEDIA_ROOT, 'illustrations', os.path.basename(img_url)),
                ]
                
                for full_path in possible_paths:
                    logger.debug(f"[Download Image] Trying: {full_path}")
                    if os.path.exists(full_path):
                        logger.info(f"[Download Image] Found at: {full_path}")
                        with open(full_path, 'rb') as f:
                            img_data = f.read()
                        # Detect type from extension
                        ext = os.path.splitext(full_path)[1].lower()
                        if ext in ['.jpg', '.jpeg']:
                            img_type = 'jpeg'
                        elif ext == '.gif':
                            img_type = 'gif'
                        elif ext == '.webp':
                            img_type = 'webp'
                        break
                
                if not img_data:
                    logger.warning(f"[Download Image] Not found in any path: {img_url}")
            elif img_url.startswith('http://') or img_url.startswith('https://'):
                # External URL - download
                response = requests.get(img_url, timeout=15)
                if response.status_code == 200:
                    img_data = response.content
                    # Detect type from content-type header or URL
                    content_type = response.headers.get('content-type', '')
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        img_type = 'jpeg'
                    elif 'gif' in content_type:
                        img_type = 'gif'
                    elif 'webp' in content_type:
                        img_type = 'webp'
                    elif '.jpg' in img_url or '.jpeg' in img_url:
                        img_type = 'jpeg'
            
            return (img_data, img_type)
            
        except Exception as e:
            logger.warning(f"Failed to download image {img_url}: {e}")
            return (None, None)
    
    def _pdf_fallback(self, include_outline: bool = False) -> bytes:
        """Fallback PDF generation using HTML"""
        # Return HTML with print-friendly styling
        return self.export_html(include_outline)
    
    def export_epub(self, include_outline: bool = False) -> bytes:
        """Export as EPUB"""
        try:
            from ebooklib import epub
        except ImportError:
            logger.error("ebooklib not installed. Install with: pip install ebooklib")
            raise ImportError("EPUB-Export benötigt ebooklib. Installation: pip install ebooklib")
        
        book = epub.EpubBook()
        
        # Set metadata
        book.set_identifier(f'bfagent-{self.project.id}')
        book.set_title(self.metadata['title'])
        book.set_language(self.metadata['language'])
        if self.metadata.get('author'):
            book.add_author(self.metadata['author'])
        if self.metadata.get('description'):
            book.add_metadata('DC', 'description', self.metadata['description'])
        
        # CSS for chapters including figure styles
        style = '''
        body { font-family: Georgia, serif; line-height: 1.6; }
        h1 { text-align: center; margin-bottom: 2em; }
        h2 { margin-top: 2em; }
        p { text-align: justify; margin-bottom: 1em; text-indent: 1.5em; }
        p:first-of-type { text-indent: 0; }
        .outline { color: #666; font-style: italic; margin-bottom: 1em; }
        figure { margin: 1.5em 0; text-align: center; }
        figure img { max-width: 100%; height: auto; }
        figcaption { font-size: 0.9em; color: #666; font-style: italic; margin-top: 0.5em; }
        .figure-index { margin-top: 2em; }
        .figure-index h2 { margin-bottom: 1em; }
        .figure-index p { text-indent: 0; }
        '''
        css = epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=style
        )
        book.add_item(css)
        
        # Create chapters
        epub_chapters = []
        
        # Title page
        title_content = f'''
        <html><head><link rel="stylesheet" href="style/main.css"/></head>
        <body>
        <h1>{self.metadata['title']}</h1>
        <p style="text-align: center;">{self.metadata.get('author', '')}</p>
        <p style="text-align: center; margin-top: 2em;">{self.metadata.get('description', '')}</p>
        </body></html>
        '''
        title_page = epub.EpubHtml(title='Titel', file_name='title.xhtml', lang='de')
        title_page.content = title_content
        title_page.add_item(css)
        book.add_item(title_page)
        epub_chapters.append(title_page)
        
        # Copyright page
        copyright_content = f'''
        <html><head><link rel="stylesheet" href="style/main.css"/></head>
        <body>
        <h2>Impressum</h2>
        <p><strong>{self.metadata['title']}</strong></p>
        <p>{self.metadata.get('author', '')}</p>
        <p style="margin-top: 2em;">© {self.metadata.get('copyright_year', '')} {self.metadata.get('copyright_holder', '')}</p>
        <p>Alle Rechte vorbehalten.</p>
        <p style="margin-top: 1em;">Verlag: {self.metadata.get('publisher', 'Selbstverlag')}</p>
        {'<p>ISBN: ' + self.metadata.get('isbn') + '</p>' if self.metadata.get('isbn') else ''}
        </body></html>
        '''
        copyright_page = epub.EpubHtml(title='Impressum', file_name='copyright.xhtml', lang='de')
        copyright_page.content = copyright_content
        copyright_page.add_item(css)
        book.add_item(copyright_page)
        epub_chapters.append(copyright_page)
        
        # Front matter pages
        for fm in self.front_matter:
            if fm.page_type in ['copyright', 'title', 'toc']:
                continue  # Skip auto-generated pages
            fm_content = fm.content or ''
            fm_html = f'''
            <html><head><link rel="stylesheet" href="style/main.css"/></head>
            <body>
            <h2>{fm.title or fm.get_page_type_display()}</h2>
            <div>{fm_content.replace(chr(10), '<br/>')}</div>
            </body></html>
            '''
            fm_page = epub.EpubHtml(
                title=fm.title or fm.get_page_type_display(),
                file_name=f'front_{fm.page_type}.xhtml',
                lang='de'
            )
            fm_page.content = fm_html
            fm_page.add_item(css)
            book.add_item(fm_page)
            epub_chapters.append(fm_page)
        
        # Track embedded images to add to EPUB
        epub_images = {}
        image_counter = 0
        include_images = getattr(self, '_include_images', True)
        
        # Content chapters
        for ch in self.chapters:
            chapter_file = epub.EpubHtml(
                title=f"Kapitel {ch.chapter_number}: {ch.title}",
                file_name=f'chapter_{ch.chapter_number}.xhtml',
                lang='de'
            )
            
            content_html = f"<h2>Kapitel {ch.chapter_number}: {ch.title}</h2>\n"
            
            if include_outline and ch.outline:
                content_html += f'<p class="outline">{ch.outline}</p>\n'
            
            chapter_content = ch.content or '[Kein Inhalt]'
            
            # Convert paragraphs
            paragraphs = chapter_content.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Check for image markdown: ![caption](url)
                    img_match = re.search(r'!\[(.*?)\]\((.*?)\)', para)
                    if img_match and include_images:
                        caption = img_match.group(1)
                        img_url = img_match.group(2)
                        logger.info(f"[EPUB Export] Found image: {img_url} with caption: {caption}")
                        
                        # Download and embed image
                        img_data, img_type = self._download_image(img_url)
                        if img_data:
                            image_counter += 1
                            img_filename = f"images/img_{image_counter}.{img_type}"
                            
                            # Add image to epub if not already added
                            if img_url not in epub_images:
                                epub_img = epub.EpubItem(
                                    uid=f"img_{image_counter}",
                                    file_name=img_filename,
                                    media_type=f"image/{img_type}",
                                    content=img_data
                                )
                                book.add_item(epub_img)
                                epub_images[img_url] = img_filename
                            
                            # Use embedded image path
                            content_html += f'''<figure>
                                <img src="{epub_images[img_url]}" alt="{caption}"/>
                                <figcaption>{caption}</figcaption>
                            </figure>\n'''
                        else:
                            # Fallback: show caption only
                            content_html += f'<p class="outline">[Bild: {caption}]</p>\n'
                    elif img_match and not include_images:
                        # Skip image if not including images
                        continue
                    elif para.startswith('*') and para.endswith('*') and 'Abb.' in para:
                        # Skip caption-only lines (already in figcaption)
                        continue
                    else:
                        para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        content_html += f"<p>{para}</p>\n"
            
            chapter_file.content = f'''
            <html><head><link rel="stylesheet" href="style/main.css"/></head>
            <body>{content_html}</body></html>
            '''
            chapter_file.add_item(css)
            book.add_item(chapter_file)
            epub_chapters.append(chapter_file)
        
        # Back matter pages
        for bm in self.back_matter:
            bm_content = bm.content or ''
            bm_html = f'''
            <html><head><link rel="stylesheet" href="style/main.css"/></head>
            <body>
            <h2>{bm.title or bm.get_page_type_display()}</h2>
            <div>{bm_content.replace(chr(10), '<br/>')}</div>
            </body></html>
            '''
            bm_page = epub.EpubHtml(
                title=bm.title or bm.get_page_type_display(),
                file_name=f'back_{bm.page_type}.xhtml',
                lang='de'
            )
            bm_page.content = bm_html
            bm_page.add_item(css)
            book.add_item(bm_page)
            epub_chapters.append(bm_page)
        
        # Add figure index if requested
        include_figure_index = getattr(self, '_include_figure_index', False)
        if include_figure_index:
            figure_index_html = self._get_figure_index_html()
            if figure_index_html:
                fig_chapter = epub.EpubHtml(
                    title='Abbildungsverzeichnis',
                    file_name='figure_index.xhtml',
                    lang='de'
                )
                fig_chapter.content = f'''
                <html><head><link rel="stylesheet" href="style/main.css"/></head>
                <body><div class="figure-index">{figure_index_html}</div></body></html>
                '''
                fig_chapter.add_item(css)
                book.add_item(fig_chapter)
                epub_chapters.append(fig_chapter)
        
        # Table of contents
        book.toc = [(epub.Section('Kapitel'), epub_chapters[1:])]  # Skip title page in TOC
        
        # Spine (reading order)
        book.spine = ['nav'] + epub_chapters
        
        # Navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # Write to buffer
        buffer = io.BytesIO()
        epub.write_epub(buffer, book, {})
        buffer.seek(0)
        return buffer.read()
    
    def _get_figure_index_html(self) -> str:
        """Generate figure index as HTML for EPUB"""
        from apps.writing_hub.models import ChapterIllustration
        
        numbering_style = getattr(self.project, 'figure_numbering_style', 'global')
        figures = []
        global_counter = 0
        
        for chapter in self.chapters:
            chapter_counter = 0
            illustrations = ChapterIllustration.objects.filter(
                chapter=chapter,
                is_selected=True,
                status='completed'
            ).order_by('position_index')
            
            for illust in illustrations:
                global_counter += 1
                chapter_counter += 1
                
                if numbering_style == 'per_chapter':
                    figure_num = f"{chapter.chapter_number}.{chapter_counter}"
                else:
                    figure_num = str(global_counter)
                
                caption = illust.caption or f"Szene {illust.position_index + 1}"
                figures.append(f"<p><strong>Abb. {figure_num}:</strong> {caption} (Kapitel {chapter.chapter_number})</p>")
        
        if not figures:
            return ""
        
        return "<h2>Abbildungsverzeichnis</h2>\n" + "\n".join(figures)
    
    def _get_figure_index(self) -> str:
        """Generate figure index (Abbildungsverzeichnis) as markdown"""
        from apps.writing_hub.models import ChapterIllustration
        
        numbering_style = getattr(self.project, 'figure_numbering_style', 'global')
        figures = []
        global_counter = 0
        
        for chapter in self.chapters:
            chapter_counter = 0
            illustrations = ChapterIllustration.objects.filter(
                chapter=chapter,
                is_selected=True,
                status='completed'
            ).order_by('position_index')
            
            for illust in illustrations:
                global_counter += 1
                chapter_counter += 1
                
                if numbering_style == 'per_chapter':
                    figure_num = f"{chapter.chapter_number}.{chapter_counter}"
                else:
                    figure_num = str(global_counter)
                
                caption = illust.caption or f"Szene {illust.position_index + 1}"
                figures.append(f"**Abb. {figure_num}:** {caption} (Kapitel {chapter.chapter_number})")
        
        if not figures:
            return ""
        
        return "## Abbildungsverzeichnis\n\n" + "\n\n".join(figures) + "\n\n---\n\n"
    
    def export(self, format_type: str, include_outline: bool = False, 
               include_images: bool = True, include_figure_index: bool = False) -> Dict[str, Any]:
        """
        Export manuscript in specified format.
        
        Args:
            format_type: 'pdf', 'epub', 'markdown', 'html', 'txt'
            include_outline: Include chapter outlines
            include_images: Include images in export
            include_figure_index: Include figure index (Abbildungsverzeichnis)
        
        Returns:
            Dict with 'content' (bytes), 'filename', 'content_type'
        """
        # Store options for use in export methods
        self._include_images = include_images
        self._include_figure_index = include_figure_index
        
        format_type = format_type.lower()
        title_safe = re.sub(r'[^\w\s-]', '', self.metadata['title']).strip()
        
        exporters = {
            'pdf': (self.export_pdf, 'application/pdf', 'pdf'),
            'epub': (self.export_epub, 'application/epub+zip', 'epub'),
            'markdown': (self.export_markdown, 'text/markdown', 'md'),
            'md': (self.export_markdown, 'text/markdown', 'md'),
            'html': (self.export_html, 'text/html', 'html'),
            'txt': (self.export_txt, 'text/plain', 'txt'),
            'text': (self.export_txt, 'text/plain', 'txt'),
        }
        
        if format_type not in exporters:
            raise ValueError(f"Unbekanntes Format: {format_type}. Unterstützt: {list(exporters.keys())}")
        
        export_func, content_type, extension = exporters[format_type]
        content = export_func(include_outline)
        
        return {
            'content': content,
            'filename': f"{title_safe}.{extension}",
            'content_type': content_type,
            'format': format_type,
            'size_bytes': len(content),
        }


def export_book(project_id: int, format_type: str = 'pdf', include_outline: bool = False) -> Dict[str, Any]:
    """
    Convenience function to export a book.
    
    Args:
        project_id: Project ID
        format_type: Export format
        include_outline: Include chapter outlines
    
    Returns:
        Export result dict
    """
    from apps.bfagent.models import BookProjects
    
    project = BookProjects.objects.get(id=project_id)
    exporter = BookExporter(project)
    return exporter.export(format_type, include_outline)
