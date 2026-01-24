"""
Custom template filters for markdown formatting.
"""
import re
import codecs
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


def decode_unicode_escapes(text):
    """
    Decode JSON-style unicode escapes like \\u000A to actual characters.
    """
    if not text:
        return text
    
    try:
        # Handle \\uXXXX patterns (JSON unicode escapes)
        return codecs.decode(text, 'unicode_escape')
    except (UnicodeDecodeError, ValueError):
        # If decoding fails, try regex replacement
        def replace_unicode(match):
            try:
                return chr(int(match.group(1), 16))
            except ValueError:
                return match.group(0)
        
        return re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)


@register.filter(name='render_markdown')
def render_markdown(value):
    """
    Simple markdown-to-HTML conversion for feedback content.
    Handles: **bold**, `code`, ```code blocks```, and newlines.
    Also decodes JSON-style unicode escapes.
    """
    if not value:
        return ''
    
    # First decode any unicode escapes
    text = decode_unicode_escapes(str(value))
    
    # Escape HTML
    text = escape(text)
    
    # Convert code blocks (```) - must be before inline code
    def replace_code_block(match):
        code = match.group(1)
        return f'<pre class="bg-dark text-light p-2 rounded"><code>{code}</code></pre>'
    
    text = re.sub(r'```(?:\w+)?\n?(.*?)```', replace_code_block, text, flags=re.DOTALL)
    
    # Convert inline code (`code`)
    text = re.sub(r'`([^`]+)`', r'<code class="bg-light px-1 rounded">\1</code>', text)
    
    # Convert bold (**text**)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    
    # Convert italic (*text*)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    
    # Convert --- to horizontal rule
    text = re.sub(r'\n---\n', '<hr class="my-2">', text)
    
    # Convert newlines to <br>
    text = text.replace('\n', '<br>')
    
    return mark_safe(text)


@register.filter(name='render_markdown_preview')
def render_markdown_preview(value, length=500):
    """
    Render markdown with truncation for previews.
    """
    if not value:
        return ''
    
    # Decode first, then truncate
    decoded = decode_unicode_escapes(str(value))
    truncated = decoded[:length]
    if len(decoded) > length:
        truncated += '...'
    
    return render_markdown(truncated)
