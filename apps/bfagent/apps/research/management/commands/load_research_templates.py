"""
Management command to load default system Research Templates.
"""

from django.core.management.base import BaseCommand
from apps.research.models import ResearchTemplate


SYSTEM_TEMPLATES = [
    {
        'name': 'Literature Review',
        'slug': 'literature-review',
        'description': 'Comprehensive academic literature review with peer-reviewed sources and proper citations.',
        'category': 'literature_review',
        'research_type': 'academic',
        'output_format': 'latex',
        'citation_style': 'apa',
        'require_peer_reviewed': True,
        'default_query_template': '{topic} academic research peer-reviewed',
        'min_sources': 10,
        'max_sources': 30,
        'sections': [
            {'id': 'abstract', 'title': 'Abstract', 'query_template': '{topic} abstract overview'},
            {'id': 'introduction', 'title': 'Introduction', 'query_template': '{topic} introduction background'},
            {'id': 'methodology', 'title': 'Methodology', 'query_template': '{topic} research methodology'},
            {'id': 'findings', 'title': 'Key Findings', 'query_template': '{topic} research findings results'},
            {'id': 'discussion', 'title': 'Discussion', 'query_template': '{topic} analysis discussion'},
            {'id': 'conclusion', 'title': 'Conclusion', 'query_template': '{topic} conclusion implications'},
        ],
    },
    {
        'name': 'Market Research',
        'slug': 'market-research',
        'description': 'Market analysis including trends, competitors, and opportunities.',
        'category': 'market_research',
        'research_type': 'deep_dive',
        'output_format': 'markdown',
        'citation_style': 'apa',
        'require_peer_reviewed': False,
        'default_query_template': '{topic} market research trends 2024',
        'min_sources': 8,
        'max_sources': 20,
        'sections': [
            {'id': 'overview', 'title': 'Market Overview', 'query_template': '{topic} market size overview'},
            {'id': 'trends', 'title': 'Current Trends', 'query_template': '{topic} market trends 2024'},
            {'id': 'competitors', 'title': 'Competitive Landscape', 'query_template': '{topic} competitors market share'},
            {'id': 'opportunities', 'title': 'Opportunities', 'query_template': '{topic} market opportunities growth'},
            {'id': 'challenges', 'title': 'Challenges', 'query_template': '{topic} market challenges risks'},
            {'id': 'forecast', 'title': 'Market Forecast', 'query_template': '{topic} market forecast prediction'},
        ],
    },
    {
        'name': 'Competitive Analysis',
        'slug': 'competitive-analysis',
        'description': 'Deep dive into competitor strategies, strengths, and weaknesses.',
        'category': 'competitive_analysis',
        'research_type': 'deep_dive',
        'output_format': 'markdown',
        'citation_style': 'apa',
        'require_peer_reviewed': False,
        'default_query_template': '{topic} competitor analysis comparison',
        'min_sources': 5,
        'max_sources': 15,
        'sections': [
            {'id': 'overview', 'title': 'Competitor Overview', 'query_template': '{topic} competitors list'},
            {'id': 'strengths', 'title': 'Competitor Strengths', 'query_template': '{topic} competitor strengths advantages'},
            {'id': 'weaknesses', 'title': 'Competitor Weaknesses', 'query_template': '{topic} competitor weaknesses problems'},
            {'id': 'strategies', 'title': 'Competitive Strategies', 'query_template': '{topic} competitive strategy'},
            {'id': 'differentiation', 'title': 'Differentiation', 'query_template': '{topic} differentiation unique value'},
        ],
    },
    {
        'name': 'Fact Checking Report',
        'slug': 'fact-checking',
        'description': 'Verify claims and statements with multiple sources.',
        'category': 'fact_checking',
        'research_type': 'quick_facts',
        'output_format': 'markdown',
        'citation_style': 'apa',
        'require_peer_reviewed': False,
        'default_query_template': 'fact check {topic}',
        'min_sources': 3,
        'max_sources': 10,
        'sections': [
            {'id': 'claim', 'title': 'Claim Analysis', 'query_template': 'verify {topic}'},
            {'id': 'evidence', 'title': 'Supporting Evidence', 'query_template': '{topic} evidence proof'},
            {'id': 'counter', 'title': 'Counter Evidence', 'query_template': '{topic} debunk false'},
            {'id': 'verdict', 'title': 'Verdict', 'query_template': '{topic} fact check conclusion'},
        ],
    },
    {
        'name': 'Technical Research',
        'slug': 'technical-research',
        'description': 'Technical deep dive with documentation and implementation details.',
        'category': 'technical_research',
        'research_type': 'deep_dive',
        'output_format': 'markdown',
        'citation_style': 'ieee',
        'require_peer_reviewed': False,
        'default_query_template': '{topic} technical documentation tutorial',
        'min_sources': 5,
        'max_sources': 15,
        'source_filters': {'domains': ['github.com', 'stackoverflow.com', 'docs.']},
        'sections': [
            {'id': 'overview', 'title': 'Technical Overview', 'query_template': '{topic} what is how works'},
            {'id': 'architecture', 'title': 'Architecture', 'query_template': '{topic} architecture design'},
            {'id': 'implementation', 'title': 'Implementation', 'query_template': '{topic} implementation guide tutorial'},
            {'id': 'best_practices', 'title': 'Best Practices', 'query_template': '{topic} best practices patterns'},
            {'id': 'examples', 'title': 'Examples', 'query_template': '{topic} examples code samples'},
        ],
    },
    {
        'name': 'Quick Facts',
        'slug': 'quick-facts',
        'description': 'Fast fact-finding for quick answers.',
        'category': 'general',
        'research_type': 'quick_facts',
        'output_format': 'markdown',
        'citation_style': 'apa',
        'require_peer_reviewed': False,
        'default_query_template': '{topic}',
        'min_sources': 3,
        'max_sources': 5,
        'sections': [
            {'id': 'facts', 'title': 'Key Facts', 'query_template': '{topic} facts'},
            {'id': 'summary', 'title': 'Summary', 'query_template': '{topic} summary overview'},
        ],
    },
]


class Command(BaseCommand):
    help = 'Load default system Research Templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing templates',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        created = 0
        updated = 0
        skipped = 0

        for template_data in SYSTEM_TEMPLATES:
            slug = template_data['slug']
            
            try:
                existing = ResearchTemplate.objects.get(slug=slug)
                if force:
                    for key, value in template_data.items():
                        setattr(existing, key, value)
                    existing.is_system = True
                    existing.is_public = True
                    existing.save()
                    updated += 1
                    self.stdout.write(f"  ✓ Updated: {template_data['name']}")
                else:
                    skipped += 1
                    self.stdout.write(f"  - Skipped: {template_data['name']} (exists)")
            except ResearchTemplate.DoesNotExist:
                ResearchTemplate.objects.create(
                    is_system=True,
                    is_public=True,
                    **template_data
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {template_data['name']}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done! Created: {created}, Updated: {updated}, Skipped: {skipped}"
        ))
