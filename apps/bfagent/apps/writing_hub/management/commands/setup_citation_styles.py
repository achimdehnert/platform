"""
Setup Citation Styles
Creates pre-configured citation styles: APA, MLA, Chicago, IEEE, Harvard.
"""

from django.core.management.base import BaseCommand
from apps.writing_hub.models import CitationStyle


class Command(BaseCommand):
    help = "Setup standard citation styles for scientific writing"

    CITATION_STYLES = [
        {
            "code": "apa",
            "name": "APA 7th Edition",
            "description": "American Psychological Association style. Widely used in social sciences, education, and psychology.",
            "article_template": "{authors} ({year}). {title}. *{journal}*, {volume}({issue}), {pages}. {doi}",
            "book_template": "{authors} ({year}). *{title}* ({edition}). {publisher}.",
            "chapter_template": "{authors} ({year}). {chapter_title}. In {editors} (Eds.), *{book_title}* (pp. {pages}). {publisher}.",
            "website_template": "{authors} ({year}, {month} {day}). *{title}*. {site_name}. {url}",
            "inline_narrative_template": "{author} ({year})",
            "inline_parenthetical_template": "({author}, {year})",
            "hanging_indent": True,
            "sort_by": "author",
        },
        {
            "code": "mla",
            "name": "MLA 9th Edition",
            "description": "Modern Language Association style. Common in humanities, literature, and arts.",
            "article_template": '{authors}. "{title}." *{journal}*, vol. {volume}, no. {issue}, {year}, pp. {pages}.',
            "book_template": "{authors}. *{title}*. {publisher}, {year}.",
            "chapter_template": '{authors}. "{chapter_title}." *{book_title}*, edited by {editors}, {publisher}, {year}, pp. {pages}.',
            "website_template": '{authors}. "{title}." *{site_name}*, {publisher}, {day} {month} {year}, {url}.',
            "inline_narrative_template": "{author}",
            "inline_parenthetical_template": "({author} {page})",
            "hanging_indent": True,
            "sort_by": "author",
        },
        {
            "code": "chicago",
            "name": "Chicago 17th Edition",
            "description": "Chicago Manual of Style. Used in history, philosophy, and some social sciences.",
            "article_template": '{authors}. "{title}." *{journal}* {volume}, no. {issue} ({year}): {pages}. {doi}.',
            "book_template": "{authors}. *{title}*. {location}: {publisher}, {year}.",
            "chapter_template": '{authors}. "{chapter_title}." In *{book_title}*, edited by {editors}, {pages}. {location}: {publisher}, {year}.',
            "website_template": '{authors}. "{title}." {site_name}. Last modified {month} {day}, {year}. {url}.',
            "inline_narrative_template": "{author} ({year}, {page})",
            "inline_parenthetical_template": "({author} {year}, {page})",
            "hanging_indent": True,
            "sort_by": "author",
        },
        {
            "code": "ieee",
            "name": "IEEE",
            "description": "Institute of Electrical and Electronics Engineers style. Standard in engineering and computer science.",
            "article_template": '[{number}] {authors}, "{title}," *{journal}*, vol. {volume}, no. {issue}, pp. {pages}, {year}.',
            "book_template": "[{number}] {authors}, *{title}*. {location}: {publisher}, {year}.",
            "chapter_template": '[{number}] {authors}, "{chapter_title}," in *{book_title}*, {editors}, Eds. {location}: {publisher}, {year}, pp. {pages}.',
            "website_template": '[{number}] {authors}, "{title}," {site_name}. {url} (accessed {access_date}).',
            "inline_narrative_template": "[{number}]",
            "inline_parenthetical_template": "[{number}]",
            "hanging_indent": False,
            "sort_by": "citation_order",
        },
        {
            "code": "harvard",
            "name": "Harvard",
            "description": "Harvard referencing style. Popular in UK and Australian universities.",
            "article_template": "{authors} ({year}) '{title}', *{journal}*, {volume}({issue}), pp. {pages}.",
            "book_template": "{authors} ({year}) *{title}*. {edition}. {location}: {publisher}.",
            "chapter_template": "{authors} ({year}) '{chapter_title}', in {editors} (eds.) *{book_title}*. {location}: {publisher}, pp. {pages}.",
            "website_template": "{authors} ({year}) *{title}*. Available at: {url} (Accessed: {access_date}).",
            "inline_narrative_template": "{author} ({year})",
            "inline_parenthetical_template": "({author}, {year})",
            "hanging_indent": True,
            "sort_by": "author",
        },
        {
            "code": "vancouver",
            "name": "Vancouver",
            "description": "Vancouver style. Common in medical and scientific journals.",
            "article_template": "{authors}. {title}. {journal}. {year};{volume}({issue}):{pages}.",
            "book_template": "{authors}. {title}. {location}: {publisher}; {year}.",
            "chapter_template": "{authors}. {chapter_title}. In: {editors}, editors. {book_title}. {location}: {publisher}; {year}. p. {pages}.",
            "website_template": "{authors}. {title} [Internet]. {location}: {publisher}; {year} [cited {access_date}]. Available from: {url}",
            "inline_narrative_template": "{author} ({number})",
            "inline_parenthetical_template": "({number})",
            "hanging_indent": False,
            "sort_by": "citation_order",
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write("Setting up Citation Styles...")
        
        count = 0
        for style_data in self.CITATION_STYLES:
            style, created = CitationStyle.objects.update_or_create(
                code=style_data["code"],
                defaults={
                    "name": style_data["name"],
                    "description": style_data["description"],
                    "article_template": style_data["article_template"],
                    "book_template": style_data["book_template"],
                    "chapter_template": style_data["chapter_template"],
                    "website_template": style_data["website_template"],
                    "inline_narrative_template": style_data["inline_narrative_template"],
                    "inline_parenthetical_template": style_data["inline_parenthetical_template"],
                    "hanging_indent": style_data["hanging_indent"],
                    "sort_by": style_data["sort_by"],
                    "is_active": True,
                }
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {style_data['name']}")
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ {count} Citation Styles configured!"))
